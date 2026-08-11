"""The loop — propose, measure, learn, repeat.

OWNERSHIP: Person B. **Long-lived, and the module the whole project rests on.**
Person A must be able to narrate what this does and why. That is the definition
of done here, not a review checkbox.

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

Everything else in the project is a component. This is the thing that actually
runs an optimisation campaign:

    while there is budget left:
        decide what to try next          <- the model and the proposal chooser
        find out what happens            <- somebody else entirely
        fold the result back in          <- update and repeat

**The critical detail is the middle line.** This file never finds out what
happens by itself. It asks something else, and that something else is swapped
out between project stages:

  * now — a made-up formula, answering instantly
  * later — a lookup table of published results, answering instantly
  * later still — a human with a pipette, answering in about two weeks

The first and last lines are *identical* in all three cases. That is the entire
reason this project can build on fake data now and still work on real data
later without a rewrite. It is the single most important design decision in the
codebase, and it is why this file is careful about the boundary.

------------------------------------------------------------------------------
THE THREE THINGS THAT MAKE IT SURVIVE CONTACT WITH REALITY
------------------------------------------------------------------------------

**1. Remembering what is already in flight.** When experiments take two weeks,
you propose a second batch while the first is still running. Without tracking
what has been proposed-but-not-yet-measured, the second batch would just
re-propose the same promising region — the model has no way to know it is
already being investigated. In stage 3 this is the normal case, not an edge
case.

**2. Saving its place properly.** A campaign spanning weeks will be
interrupted. So the whole state gets written down — the measurements, the
settings, and the exact state of the random number generators — and the model
is *rebuilt from scratch* on resume rather than being restored from a saved
copy. Saved model internals are fragile across library versions; measurements
are not. Rebuilding is slower and far more robust, and at these sizes the extra
time is seconds.

**3. Writing down its predictions before it learns the answer.** Every round,
before anything is measured, the model's expectations are recorded — both at
the recipes it just proposed and at a fixed set of reference points chosen once
at the start. Afterwards you can check how well those predictions held up.

The two sets answer different questions and the gap between them is itself
worth reporting. The proposed recipes are the decision-relevant ones, but they
were *chosen* for looking promising or uncertain, so they are a biased sample.
The fixed reference points were chosen before anything was known, so they give
an unbiased picture.

------------------------------------------------------------------------------
"""

from __future__ import annotations

import platform
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
import torch
from torch import Tensor

from boec.optimizers import AcqConfig, propose, sobol_design
from boec.surrogate import build_gp, predictive

__all__ = [
    "Campaign",
    "CampaignConfig",
    "Evaluator",
    "RoundLog",
    "batch_plan",
]


@runtime_checkable
class Evaluator(Protocol):
    """Whatever supplies outcomes. **Person A owns the implementations.**

    Deliberately a *structural* interface rather than a base class to inherit
    from: anything with a matching ``evaluate`` method works, so A's module and
    this one do not have to agree on a shared parent, and neither has to exist
    before the other. Nothing here needs changing when a lookup table or a
    human replaces the made-up formula.

    Shape contract, exactly as Doc 1 §2 states it:
        ``evaluate(X: (n, d)) -> (Y: (n, m), Yvar: (n, m) | None)``

    Returning ``None`` for the noise is permitted by the interface but **not**
    by this project — contract item 5 requires it always be supplied, because
    one model cannot mix known-noise and unknown-noise measurements. If it
    comes back ``None``, the campaign raises rather than guessing.
    """

    def evaluate(self, X: Tensor) -> tuple[Tensor, Tensor | None]: ...


def batch_plan(d: int, budget: int = 48, q: int = 4,
               n_init: int | None = None) -> tuple[int, list[int]]:
    """How the budget is split, enforced identically across every method.

    The spec fixes this: at 6 ingredients, 14 to start plus eight batches of
    four plus a final batch of two. At 8 ingredients, 18 plus seven fours plus
    a two. Both land on 48.

    **Every method being compared must spend its budget the same way**, or the
    comparison is measuring the schedule rather than the method.

    Args:
        d: number of ingredients.
        budget: total measurements.
        q: batch size after the opening.
        n_init: override the opening size. ``None`` keeps the ``2d + 2`` rule,
            which is what every experiment uses and what E2 is pre-registered
            on. The override exists for one purpose: Q26 needs d=6 run with
            d=8's 18-point opening to separate opening SIZE from dimension.
            Overriding does not buy evaluations — the budget is fixed, so a
            larger opening means correspondingly fewer adaptive rounds, and
            that trade-off is the point of the test rather than a side effect.

    Returns:
        ``(n_initial, [batch sizes])``.
    """
    n_init = 2 * d + 2 if n_init is None else int(n_init)
    remaining = budget - n_init
    if remaining < 0:
        raise ValueError(
            f"budget {budget} cannot cover an opening design of {n_init} at d={d}"
        )
    batches = [q] * (remaining // q)
    if remaining % q:
        batches.append(remaining % q)
    return n_init, batches


@dataclass
class CampaignConfig:
    """Everything needed to reproduce a run exactly.

    Attributes:
        d: number of ingredients.
        budget: total measurements.
        q: batch size after the opening.
        seed: fixes the opening design, the reference points, and every
            random draw made along the way.
        acq: how proposals are chosen.
        n_holdout: how many fixed reference points to score each round.
        metric_name: what is being measured, e.g. ``"cd31_area_over_dapi"``.
        metric_units: e.g. ``"ratio"``.
        protocol_version: which assay version produced the numbers.
        kernel_structure: how the surrogate decomposes the space; one of
            :data:`boec.surrogate.KERNEL_STRUCTURES`. **Default ``"product"``,
            which is what E2 ran and what every stored E2 number is.** The
            alternatives are Q29's arms and must be asked for explicitly — a
            campaign that silently changed its own model would make a stored row
            unattributable to a model.

    The last three exist because two different ways of measuring the same
    biology give different numbers that must never be mixed. Recording them on
    every row costs nothing now and prevents a silent, unrecoverable error
    later.
    """

    d: int
    budget: int = 48
    q: int = 4
    n_init: int | None = None
    seed: int = 0
    acq: AcqConfig = field(default_factory=AcqConfig)
    n_holdout: int = 64
    metric_name: str = "synthetic"
    metric_units: str = "coded"
    protocol_version: str = "phase1"
    kernel_structure: str = "product"


@dataclass
class RoundLog:
    """What the model believed at one round, recorded before it found out.

    Attributes:
        round_index: 0 is the opening design.
        X_proposed: ``(q, d)`` what was proposed.
        mean_proposed / var_proposed: beliefs at those recipes, before measuring.
        mean_holdout / var_holdout: beliefs at the fixed reference points.
        n_train_before: how many measurements the model had seen.
    """

    round_index: int
    X_proposed: Tensor
    mean_proposed: Tensor | None
    var_proposed: Tensor | None
    mean_holdout: Tensor | None
    var_holdout: Tensor | None
    n_train_before: int


class Campaign:
    """One optimisation run.

    Usage::

        c = Campaign(evaluator, bounds, CampaignConfig(d=6))
        c.run()                      # or drive ask()/tell() yourself
        c.save("run.pt")
        c2 = Campaign.load("run.pt", evaluator)   # picks up exactly where it left off
    """

    def __init__(
        self,
        evaluator: Evaluator,
        bounds: Tensor,
        config: CampaignConfig,
    ) -> None:
        if bounds.ndim != 2 or bounds.shape[0] != 2:
            raise ValueError(f"bounds must be (2, d), got {tuple(bounds.shape)}")
        if bounds.shape[1] != config.d:
            raise ValueError(
                f"bounds has {bounds.shape[1]} factors, config says d={config.d}"
            )
        self.evaluator = evaluator
        self.bounds = bounds.double()
        self.config = config

        self.train_X = torch.empty(0, config.d, dtype=torch.double)
        self.train_Y = torch.empty(0, 1, dtype=torch.double)
        self.train_Yvar = torch.empty(0, 1, dtype=torch.double)
        self.X_pending = torch.empty(0, config.d, dtype=torch.double)
        self.logs: list[RoundLog] = []
        self._round = 0

        self.seed_everything(config.seed)
        # Reference points, drawn once, never changed. Offsetting the seed keeps
        # them from coinciding with the opening design.
        self.holdout_X = sobol_design(self.bounds, config.n_holdout, seed=config.seed + 10_000)

    # -- reproducibility ---------------------------------------------------

    @staticmethod
    def seed_everything(seed: int) -> None:
        """Seed every generator that could affect a result."""
        random.seed(seed)
        np.random.seed(seed % (2**32))
        torch.manual_seed(seed)

    @staticmethod
    def _rng_state() -> dict:
        return {
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(),
        }

    @staticmethod
    def _set_rng_state(state: dict) -> None:
        random.setstate(state["python"])
        np.random.set_state(state["numpy"])
        torch.set_rng_state(state["torch"])

    # -- the model ---------------------------------------------------------

    @property
    def n_observed(self) -> int:
        return int(self.train_X.shape[0])

    def fit(self):
        """Rebuild the model from the measurements so far.

        Rebuilt every time rather than kept around, so that a resumed run and an
        uninterrupted one follow byte-identical paths.
        """
        if self.n_observed == 0:
            raise RuntimeError("nothing measured yet — call initialize() first")
        return build_gp(
            self.train_X, self.train_Y, self.train_Yvar, self.bounds,
            kernel_structure=self.config.kernel_structure,
        )

    # -- the loop ----------------------------------------------------------

    def initialize(self) -> None:
        """Run the opening design. No model involved — nothing is known yet."""
        if self.n_observed:
            raise RuntimeError("already initialized")
        n_init, _ = batch_plan(self.config.d, self.config.budget, self.config.q,
                               self.config.n_init)
        # Sobol is a sequence, so a larger draw shares its prefix with a smaller
        # one at the same seed: an overridden opening is the default opening
        # plus extra points, never a different design. Asserted in the suite.
        X = sobol_design(self.bounds, n_init, seed=self.config.seed)
        self.logs.append(
            RoundLog(
                round_index=0, X_proposed=X.clone(),
                mean_proposed=None, var_proposed=None,
                mean_holdout=None, var_holdout=None,
                n_train_before=0,
            )
        )
        self._round = 1
        self._record(X, *self._measure(X))

    def ask(self, q: int) -> Tensor:
        """Propose ``q`` recipes, and write down what we expect before finding out.

        The proposals are added to the in-flight list, so a further ``ask``
        before the matching ``tell`` will steer away from them rather than
        re-proposing the same region.
        """
        if self.n_observed == 0:
            raise RuntimeError("call initialize() before ask()")
        model = self.fit()

        X = propose(
            model, self.bounds, q, self.train_X, self.train_Y,
            config=self.config.acq,
            X_pending=self.X_pending if self.X_pending.shape[0] else None,
        )

        # Beliefs recorded BEFORE measurement — this is what A's calibration
        # work consumes, and it cannot be reconstructed afterwards.
        at_proposed = predictive(model, X)
        at_holdout = predictive(model, self.holdout_X)
        self.logs.append(
            RoundLog(
                round_index=self._round,
                X_proposed=X.clone(),
                mean_proposed=at_proposed.mean.clone(),
                var_proposed=at_proposed.variance.clone(),
                mean_holdout=at_holdout.mean.clone(),
                var_holdout=at_holdout.variance.clone(),
                n_train_before=self.n_observed,
            )
        )
        self._round += 1
        self.X_pending = torch.cat([self.X_pending, X])
        return X

    def tell(self, X: Tensor, Y: Tensor, Yvar: Tensor) -> None:
        """Fold measured results back in and clear them from the in-flight list."""
        self._record(X, Y, Yvar)
        self._drop_pending(X)

    def run(self) -> Campaign:
        """Run the whole thing to budget."""
        if self.n_observed == 0:
            self.initialize()
        _, batches = batch_plan(self.config.d, self.config.budget, self.config.q,
                                self.config.n_init)
        for q in batches:
            X = self.ask(q)
            Y, Yvar = self._measure(X)
            self.tell(X, Y, Yvar)
        return self

    # -- internals ---------------------------------------------------------

    def _measure(self, X: Tensor) -> tuple[Tensor, Tensor]:
        Y, Yvar = self.evaluator.evaluate(X)
        if Yvar is None:
            raise ValueError(
                "the evaluator returned no noise estimate. Contract item 5 "
                "requires it always be supplied — one model cannot mix "
                "known-noise and unknown-noise measurements. Impute it in the "
                "evaluator, where the imputation rule is visible, rather than "
                "silently here."
            )
        return Y, Yvar

    def _record(self, X: Tensor, Y: Tensor, Yvar: Tensor) -> None:
        if Y.ndim != 2 or Yvar.ndim != 2:
            raise ValueError(
                f"outcomes must be (n, m) even at m=1; got Y {tuple(Y.shape)} "
                f"and Yvar {tuple(Yvar.shape)}"
            )
        if not (X.shape[0] == Y.shape[0] == Yvar.shape[0]):
            raise ValueError(
                f"row mismatch: X {X.shape[0]}, Y {Y.shape[0]}, Yvar {Yvar.shape[0]}"
            )
        self.train_X = torch.cat([self.train_X, X.double()])
        self.train_Y = torch.cat([self.train_Y, Y.double()])
        self.train_Yvar = torch.cat([self.train_Yvar, Yvar.double()])

    def _drop_pending(self, X: Tensor) -> None:
        if self.X_pending.shape[0] == 0:
            return
        keep = [
            i for i in range(self.X_pending.shape[0])
            if not bool(torch.any(torch.all(torch.isclose(X, self.X_pending[i]), dim=1)))
        ]
        self.X_pending = self.X_pending[keep]

    # -- results -----------------------------------------------------------

    def best_so_far(self) -> Tensor:
        """``(n,)`` running best measurement — the convergence curve."""
        if self.n_observed == 0:
            return torch.empty(0, dtype=torch.double)
        return torch.cummax(self.train_Y.squeeze(-1), dim=0).values

    # -- saving and resuming -----------------------------------------------

    def state_dict(self) -> dict:
        """Everything needed to resume. **Measurements and settings, not model
        internals** — the model is rebuilt on resume.
        """
        import botorch
        return {
            "format_version": 1,
            "config": asdict(self.config),
            "bounds": self.bounds,
            "train_X": self.train_X,
            "train_Y": self.train_Y,
            "train_Yvar": self.train_Yvar,
            "X_pending": self.X_pending,
            "holdout_X": self.holdout_X,
            "logs": [asdict(log) for log in self.logs],
            "round": self._round,
            # Without this the identical-trace test cannot pass.
            "rng_state": self._rng_state(),
            "versions": {
                "botorch": botorch.__version__,
                "torch": torch.__version__,
                "numpy": np.__version__,
                "python": platform.python_version(),
            },
        }

    def save(self, path: str | Path) -> None:
        torch.save(self.state_dict(), Path(path))

    @classmethod
    def load(cls, path: str | Path, evaluator: Evaluator) -> Campaign:
        """Resume a saved campaign. The evaluator is supplied fresh — it may be
        a live instrument or a person, and is not something to pickle."""
        state = torch.load(Path(path), weights_only=False)
        return cls.from_state_dict(state, evaluator)

    @classmethod
    def from_state_dict(cls, state: dict, evaluator: Evaluator) -> Campaign:
        cfg_raw = dict(state["config"])
        cfg_raw["acq"] = AcqConfig(**cfg_raw["acq"])
        config = CampaignConfig(**cfg_raw)

        c = cls(evaluator, state["bounds"], config)
        c.train_X = state["train_X"]
        c.train_Y = state["train_Y"]
        c.train_Yvar = state["train_Yvar"]
        c.X_pending = state["X_pending"]
        c.holdout_X = state["holdout_X"]
        c.logs = [RoundLog(**log) for log in state["logs"]]
        c._round = state["round"]
        # Restored last: constructing the campaign above re-seeded, which would
        # otherwise overwrite the state we are trying to restore.
        cls._set_rng_state(state["rng_state"])
        return c
