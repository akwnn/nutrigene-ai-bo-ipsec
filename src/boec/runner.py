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
from boec.optimizers import lhs_design, random_design, sobol_design

__all__ = [
    "GridCell",
    "Runner",
    "load_results",
    "run_static_baseline",
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


def run_static_baseline(
    evaluator: Evaluator,
    bounds: Tensor,
    method: str,
    budget: int,
    seed: int,
    *,
    n_orderings: int = 20,
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

    Returns:
        ``(budget,)`` the averaged best-so-far curve.
    """
    makers: dict[str, Callable[..., Tensor]] = {
        "random": random_design, "sobol": sobol_design, "lhs": lhs_design,
    }
    if method not in makers:
        raise ValueError(f"unknown baseline {method!r}; choose from {sorted(makers)}")

    X = makers[method](bounds, budget, seed=seed)
    Y, Yvar = evaluator.evaluate(X)
    if Yvar is None:
        raise ValueError("evaluator returned no noise estimate — see contract item 5")

    y = Y.double().numpy().ravel()
    rng = np.random.default_rng(seed)
    curves = np.empty((n_orderings, budget), dtype=np.float64)
    for i in range(n_orderings):
        curves[i] = np.maximum.accumulate(y[rng.permutation(budget)])
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

        if cell.method in {"random", "sobol", "lhs"}:
            curve = run_static_baseline(
                evaluator, bounds, cell.method, config.budget, cell.seed
            )
            frame = self._frame_from_curve(cell, config, curve)
        else:
            campaign = Campaign(evaluator, bounds, config).run()
            frame = self._frame_from_campaign(cell, config, campaign)

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
