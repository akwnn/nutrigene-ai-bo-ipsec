"""Running many campaigns and keeping the results.

OWNERSHIP: Person B. **Long-lived.**

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

One campaign tells you almost nothing. Any single run can get lucky. So the
experiment runs many: several different made-up landscapes, several different
random starting points on each, and several competing methods on every
combination — then compares.

This file runs that grid and writes the results down.

**The one feature that matters most in practice: it skips work already done.**
Not primarily for crash recovery — because during development you will
interrupt runs constantly, fix something, and start again. Without skipping,
every restart repeats everything. With it, you only pay for what changed.

**Why more landscapes beats more repeats.** Five random starts on ten different
landscapes tells you more than fifty starts on one, because landscapes differ
from each other more than repeats differ from each other. A method that wins on
one landscape fifty times has shown you very little.

**What gets written alongside every result.** The full settings that produced
it, and the exact versions of every library involved. Six months from now,
"which version produced this number" is a question someone will ask, and if the
answer isn't stored it cannot be reconstructed.

------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import os
import platform
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import Tensor

from boec.campaign import Campaign, CampaignConfig, Evaluator
from boec.optimizers import (
    ACQUISITION_CHOICES,
    initial_design,
    lhs_design,
    random_design,
    sobol_design,
)

#: Methods that choose all their points up front. Run through
#: :func:`run_static_baseline`, which averages over orderings.
STATIC_METHODS = ("random", "sobol", "lhs")

#: Methods known to :meth:`Runner.run_cell` but not implemented there yet.
#: Mapping name -> what to do instead. Kept explicit so an unimplemented arm
#: fails loudly rather than falling through to the adaptive branch: ``GridCell``
#: already documents ``"doe"`` as a valid method, and before this existed a
#: ``doe`` cell ran a **Bayesian optimization campaign** and wrote a
#: believable-looking parquet file under a ``method-doe`` filename.
UNWIRED_METHODS: dict[str, str] = {
    "doe": (
        "the sequential-DoE arm is implemented in boec.doe.run_doe_arm but is "
        "not wired into the Runner. Call it directly (see scripts/run_doe_arm.py), "
        "or add a branch here that converts DoEResult into a best-so-far curve. "
        "See docs/TASKS.md T8."
    ),
}

__all__ = [
    "PAIRING_EXEMPT",
    "STATIC_METHODS",
    "UNWIRED_METHODS",
    "GridCell",
    "Runner",
    "load_results",
    "run_static_baseline",
    "static_design",
    "set_single_threaded",
]


def set_single_threaded() -> None:
    """Keep each worker to one thread.

    **Must be called before torch is imported to be fully effective** — some
    builds fix their thread pool at import time and a later in-process call
    arrives too late. Scripts set the environment variable at the top; this
    function is the belt-and-braces half.

    Without it, several workers each spawn several threads, they fight over the
    same cores, and the whole grid runs slower than single-threaded.
    """
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    torch.set_num_threads(1)


@dataclass(frozen=True)
class GridCell:
    """One point in the grid: a landscape, a starting seed, and a method.

    Attributes:
        instance_id: which made-up landscape.
        seed: which random start. Varies the opening design and the noise draws.
        method: ``"qlogei"``, ``"random"``, ``"sobol"``, ``"lhs"``, ``"doe"``.
        dim: number of ingredients.
        sigma_rel: noise level.
        extra: anything else that distinguishes this cell.
    """

    instance_id: str
    seed: int
    method: str
    dim: int
    sigma_rel: float
    extra: dict = field(default_factory=dict)

    def key(self) -> str:
        """Filename-safe identifier. Two cells match iff their keys match."""
        bits = [
            f"inst-{self.instance_id}",
            f"seed-{self.seed}",
            f"method-{self.method}",
            f"d-{self.dim}",
            f"sig-{self.sigma_rel:g}",
        ]
        bits += [f"{k}-{v}" for k, v in sorted(self.extra.items())]
        return "__".join(bits)


#: Q18 (T9). Arms exempt from the paired opening batch, and why. A Latin
#: hypercube's stratification is a property of the WHOLE n-point set, so a Sobol
#: prefix plus a Latin-hypercube remainder is not a Latin hypercube. Pairing this
#: arm would leave it wearing the name of a baseline it no longer is.
PAIRING_EXEMPT: dict[str, str] = {
    "lhs": (
        "a Latin hypercube stratifies over all n points, so replacing its opening "
        "with the shared Sobol batch destroys the property the arm exists to test. "
        "Q18 exempts it: run it with share_opening=False and report it as the one "
        "unpaired arm, with its wider interval, rather than as a paired hybrid."
    ),
}


def static_design(
    bounds: Tensor,
    method: str,
    budget: int,
    seed: int,
    *,
    share_opening: bool | None = None,
) -> Tensor:
    """The full point set for a non-adaptive arm, opening batch included.

    **Q18 (T9), PRE-REGISTERED: every paired arm opens on the identical batch.**
    Spec §E2 requires the opening design to be identical across methods for a
    given seed — "paired comparison at n=50 is the difference between a
    significant and a non-significant result" — and it was not. Before this,
    ``run_static_baseline`` generated all ``budget`` points from the method's own
    generator and never called :func:`~boec.optimizers.initial_design`, so the
    random and LHS arms shared no opening with qLogEI whatsoever.

    The Sobol arm was already paired **for free** and nobody had noticed:
    ``initial_design`` IS ``sobol_design(bounds, 2d + 2, seed)``, and a Sobol
    prefix is stable, so the natural 48-point Sobol design already begins with
    exactly the shared opening. Pairing costs that arm nothing. It costs the
    random arm nothing either — random has no global structure to damage. It
    costs the LHS arm its defining property, which is why LHS is exempt; see
    :data:`PAIRING_EXEMPT`.

    Args:
        bounds: ``(2, d)``.
        method: ``"random"``, ``"sobol"`` or ``"lhs"``.
        budget: total measurements.
        seed: fixes the design.
        share_opening: ``None`` (the default) applies the registered policy — pair
            the arm unless it is in :data:`PAIRING_EXEMPT`. ``True`` **demands**
            pairing and raises on an exempt arm, so a caller who believes every arm
            is paired finds out rather than being quietly right for three arms and
            wrong for one. ``False`` opts out explicitly.

    Returns:
        ``(budget, d)``. When paired, rows ``[:2d + 2]`` are exactly
        ``initial_design(bounds, seed=seed)``.

    Raises:
        ValueError: on an unknown method, or when pairing is *demanded* of a
            registered-exempt arm. Silently returning a hybrid under the exempt
            arm's label would be the same defect class as the ``method``
            fall-through fixed in ``run_cell``.
    """
    makers: dict[str, Callable[..., Tensor]] = {
        "random": random_design, "sobol": sobol_design, "lhs": lhs_design,
    }
    if method not in makers:
        raise ValueError(f"unknown baseline {method!r}; choose from {sorted(makers)}")

    if share_opening and method in PAIRING_EXEMPT:
        raise ValueError(
            f"{method!r} is exempt from the Q18 paired opening — {PAIRING_EXEMPT[method]}"
        )
    pair = (method not in PAIRING_EXEMPT) if share_opening is None else share_opening

    full = makers[method](bounds, budget, seed=seed)
    if not pair:
        return full

    n_init = 2 * int(bounds.shape[1]) + 2
    if n_init >= budget:
        raise ValueError(
            f"budget {budget} cannot cover an opening design of {n_init} at "
            f"d={bounds.shape[1]}"
        )
    return torch.cat([initial_design(bounds, seed=seed), full[n_init:]], dim=0)


def run_static_baseline(
    evaluator: Evaluator,
    bounds: Tensor,
    method: str,
    budget: int,
    seed: int,
    *,
    n_orderings: int = 20,
    share_opening: bool | None = None,
) -> np.ndarray:
    """Run a non-adaptive baseline and produce a fair convergence curve.

    Random, Sobol and Latin-hypercube designs choose all their points **up
    front**, before seeing any result. So they have no natural running order,
    and the "best result so far" curve depends entirely on which arbitrary
    order you happen to list them in — put the winner first and the curve looks
    brilliant immediately.

    Comparing an adaptive method against that would be meaningless. So the
    points are shuffled many times and the curves averaged, which is the
    honest summary of "what would you expect from this design".

    Args:
        evaluator: supplies outcomes.
        bounds: ``(2, d)``.
        method: ``"random"``, ``"sobol"`` or ``"lhs"``.
        budget: how many measurements.
        seed: fixes the design and the shuffles.
        n_orderings: how many shuffles to average over.
        share_opening: Q18 (T9). Open on the shared batch and hold it fixed. The
            registered default; pass ``False`` only for a registered exemption.

    Returns:
        ``(budget,)`` the averaged best-so-far curve.

    Note:
        **The shared opening is not shuffled.** Q18's pairing has to survive
        scoring, not only design: this function previously permuted all ``budget``
        points, which scattered the opening batch through the curve and undid the
        pairing even on the Sobol arm, where it had been free all along. Only the
        method-specific remainder is shuffled, which is also the segment spec §E2
        computes AUC over — "computing AUC from evaluation 1 would include the
        shared initial design and dilute the between-method difference".
    """
    X = static_design(bounds, method, budget, seed, share_opening=share_opening)
    Y, Yvar = evaluator.evaluate(X)
    if Yvar is None:
        raise ValueError("evaluator returned no noise estimate — see contract item 5")

    paired = (method not in PAIRING_EXEMPT) if share_opening is None else share_opening
    y = Y.double().numpy().ravel()
    n_init = 2 * int(bounds.shape[1]) + 2 if paired else 0
    rng = np.random.default_rng(seed)
    curves = np.empty((n_orderings, budget), dtype=np.float64)
    for i in range(n_orderings):
        order = np.concatenate([
            np.arange(n_init),
            n_init + rng.permutation(budget - n_init),
        ])
        curves[i] = np.maximum.accumulate(y[order])
    return curves.mean(axis=0)


class Runner:
    """Runs a grid of campaigns, skipping anything already finished.

    Args:
        results_dir: where results land. One parquet file per cell, plus a
            settings sidecar.
        overwrite: if True, redo everything. Off by default, because the whole
            point is not redoing things.
    """

    def __init__(self, results_dir: str | Path, *, overwrite: bool = False) -> None:
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.overwrite = overwrite

    # -- bookkeeping -------------------------------------------------------

    def result_path(self, cell: GridCell) -> Path:
        return self.results_dir / f"{cell.key()}.parquet"

    def sidecar_path(self, cell: GridCell) -> Path:
        return self.results_dir / f"{cell.key()}.json"

    def is_done(self, cell: GridCell) -> bool:
        """Has this cell already been run? Skipping is the whole feature."""
        return (not self.overwrite) and self.result_path(cell).exists()

    def pending(self, cells: Iterable[GridCell]) -> list[GridCell]:
        return [c for c in cells if not self.is_done(c)]

    # -- running -----------------------------------------------------------

    def run_cell(
        self,
        cell: GridCell,
        evaluator: Evaluator,
        bounds: Tensor,
        config: CampaignConfig,
    ) -> pd.DataFrame | None:
        """Run one cell, or return ``None`` if it was already done."""
        if self.is_done(cell):
            return None

        set_single_threaded()
        started = time.perf_counter()

        if cell.method in STATIC_METHODS:
            curve = run_static_baseline(
                evaluator, bounds, cell.method, config.budget, cell.seed
            )
            frame = self._frame_from_curve(cell, config, curve)
        elif cell.method in ACQUISITION_CHOICES:
            campaign = Campaign(evaluator, bounds, config).run()
            frame = self._frame_from_campaign(cell, config, campaign)
        elif cell.method in UNWIRED_METHODS:
            raise NotImplementedError(
                f"method {cell.method!r} is not runnable here — {UNWIRED_METHODS[cell.method]}"
            )
        else:
            # Never fall through to the adaptive branch. An unrecognised name
            # used to silently become a BO campaign, so a typo in one arm of an
            # E2 grid would have been reported as that arm's result.
            raise ValueError(
                f"unknown method {cell.method!r}; choose from "
                f"{sorted((*STATIC_METHODS, *ACQUISITION_CHOICES, *UNWIRED_METHODS))}"
            )

        elapsed = time.perf_counter() - started
        frame["wall_clock_s"] = elapsed

        # Write the settings first: a results file that exists is taken as
        # proof the cell is done, so it must be the last thing to appear.
        self._write_sidecar(cell, config, elapsed)
        frame.to_parquet(self.result_path(cell), index=False)
        return frame

    def run_grid(
        self,
        cells: Iterable[GridCell],
        make_evaluator: Callable[[GridCell], Evaluator],
        make_bounds: Callable[[GridCell], Tensor],
        make_config: Callable[[GridCell], CampaignConfig],
        *,
        verbose: bool = True,
    ) -> Iterator[tuple[GridCell, pd.DataFrame | None]]:
        """Run every cell, yielding as it goes. Already-finished cells yield ``None``."""
        cells = list(cells)
        todo = self.pending(cells)
        if verbose:
            print(f"{len(cells)} cells; {len(todo)} to run, {len(cells) - len(todo)} already done")
        for i, cell in enumerate(cells, 1):
            if self.is_done(cell):
                yield cell, None
                continue
            if verbose:
                print(f"[{i}/{len(cells)}] {cell.key()}")
            yield cell, self.run_cell(
                cell, make_evaluator(cell), make_bounds(cell), make_config(cell)
            )

    # -- output ------------------------------------------------------------

    @staticmethod
    def _base_columns(cell: GridCell, config: CampaignConfig, n: int) -> dict:
        return {
            "instance_id": [cell.instance_id] * n,
            "seed": [cell.seed] * n,
            "method": [cell.method] * n,
            "dim": [cell.dim] * n,
            "sigma_rel": [cell.sigma_rel] * n,
            "evaluation": list(range(1, n + 1)),
            # Two ways of measuring the same biology give different numbers.
            # Carried on every row so they can never be silently mixed.
            "metric_name": [config.metric_name] * n,
            "metric_units": [config.metric_units] * n,
            "protocol_version": [config.protocol_version] * n,
        }

    def _frame_from_campaign(self, cell, config, campaign: Campaign) -> pd.DataFrame:
        y = campaign.train_Y.squeeze(-1).numpy()
        n = len(y)
        data = self._base_columns(cell, config, n)
        data["y_observed"] = y
        data["y_var"] = campaign.train_Yvar.squeeze(-1).numpy()
        data["best_so_far"] = campaign.best_so_far().numpy()
        for j in range(cell.dim):
            data[f"x_{j}"] = campaign.train_X[:, j].numpy()
        return pd.DataFrame(data)

    def _frame_from_curve(self, cell, config, curve: np.ndarray) -> pd.DataFrame:
        n = len(curve)
        data = self._base_columns(cell, config, n)
        data["y_observed"] = [float("nan")] * n   # averaged over orderings
        data["y_var"] = [float("nan")] * n
        data["best_so_far"] = curve
        return pd.DataFrame(data)

    def _write_sidecar(self, cell: GridCell, config: CampaignConfig, elapsed: float) -> None:
        import botorch
        payload = {
            "cell": asdict(cell),
            "config": _jsonable(asdict(config)),
            "wall_clock_s": elapsed,
            "versions": {
                "botorch": botorch.__version__,
                "torch": torch.__version__,
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
        }
        self.sidecar_path(cell).write_text(json.dumps(payload, indent=2, sort_keys=True))


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, torch.Tensor):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return repr(obj)


def load_results(results_dir: str | Path) -> pd.DataFrame:
    """Read every result back into one table.

    Returns:
        All cells concatenated, or an empty frame if there are none.
    """
    files = sorted(Path(results_dir).glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
