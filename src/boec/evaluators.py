"""Evaluators — the only thing that changes between project phases.

::

    while budget_remaining:
        X = optimizer.ask(q)                    # identical in all three phases
        Y, Yvar = evaluator.evaluate(X)         # only this changes
        optimizer.tell(X, Y, Yvar)              # identical in all three phases

Phase 1 calls a synthetic oracle. Phase 2 will index a digitized lookup table.
Phase 3 will write a CSV of proposed conditions, wait two weeks, and read results
back. The ABC matters more than any implementation behind it.

Outcome tensors are always ``(n, m)``, never ``(n,)``. ``m = 1`` throughout Phase 1,
but the multi-objective shape is the one that survives into Phase 3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import numpy as np

from .oracles import Oracle
from .space import MetricIdentity

YvarMode = Literal["plugin", "analytic"]


class Evaluator(ABC):
    """Supplies outcomes for proposed conditions.

    Implementations must not expose noiseless values through :meth:`evaluate`. The
    whole regret story depends on the optimizer never seeing ``y_true``.
    """

    metric: MetricIdentity

    @abstractmethod
    def evaluate(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """``(n, d)`` -> ``(Y, Yvar)``, both ``(n, m)`` in raw outcome units."""

    @property
    @abstractmethod
    def n_evaluations(self) -> int:
        """Total outcomes returned so far — the budget counter."""


@dataclass
class SyntheticEvaluator(Evaluator):
    """Phase 1 evaluator: calls an :class:`~boec.oracles.Oracle` and adds noise.

    Observation model ``y = f(x)*(1 + eps) + eta`` with ``eps ~ N(0, sigma_rel^2)``
    and ``eta ~ N(0, sigma_add^2)`` — multiplicative noise because assay CV, not
    absolute error, is what scales in this readout.

    The returned ``Yvar`` is the **plug-in** estimate ``yhat^2*sigma_rel^2 +
    sigma_add^2``, computed from the *observed* value. Not the analytic variance:
    that is a function of the noiseless ``f(x)``, from which ``|f(x)|`` is exactly
    recoverable, so returning it hands the model the truth at every training point
    and corrupts the calibration experiment. It also would not transfer — Phase 2
    has no variance and Phase 3 has replicate SEM.

    Known bias, recorded here so nobody debugs it twice: ``E[y_obs^2] =
    f^2*(1 + sigma_rel^2) + sigma_add^2``, so the plug-in over-estimates by ~1% at
    ``sigma_rel = 0.10`` and ~6% at 0.25, and a point that drew high noise gets a
    larger Yvar and is down-weighted. Real labs do exactly this, so it is the right
    default. If calibration shows mild over-coverage at the higher noise level, this
    is the first candidate, not a bug.
    """

    oracle: Oracle
    metric: MetricIdentity
    sigma_rel: float = 0.10
    sigma_add: float = 0.01
    yvar_mode: YvarMode = "plugin"
    seed: int = 0
    _n_eval: int = 0
    _rng: np.random.Generator | None = None

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    @property
    def n_evaluations(self) -> int:
        return self._n_eval

    def _f_true(self, X: np.ndarray) -> np.ndarray:
        """``(n, 1)`` noiseless values. Private on purpose — see :meth:`evaluate`."""
        return np.asarray(self.oracle.f(X), dtype=float).reshape(-1, 1)

    def evaluate(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be (n, d); got shape {X.shape}")
        assert self._rng is not None
        f = self._f_true(X)
        eps = self._rng.normal(0.0, self.sigma_rel, size=f.shape)
        eta = self._rng.normal(0.0, self.sigma_add, size=f.shape)
        y = f * (1.0 + eps) + eta

        if self.yvar_mode == "plugin":
            yvar = y**2 * self.sigma_rel**2 + self.sigma_add**2
        elif self.yvar_mode == "analytic":
            # Ablation only: an upper bound under perfect noise knowledge. Leaks |f|.
            yvar = f**2 * self.sigma_rel**2 + self.sigma_add**2
        else:
            raise ValueError(f"unknown yvar_mode {self.yvar_mode!r}")

        self._n_eval += X.shape[0]
        # Variance, not standard deviation, and in raw outcome units. Two separate
        # classic fixed-noise GP bugs, both of which produce plausible-looking but
        # systematically wrong calibration.
        return y, yvar

    def evaluate_true(self, X: np.ndarray) -> np.ndarray:
        """``(n, 1)`` noiseless values — for scoring regret, never for the optimizer.

        Deliberately not part of the :class:`Evaluator` interface. Phase 2 and Phase 3
        evaluators have no such method, and any code that reaches for it will fail to
        port, which is the intended signal.
        """
        return self._f_true(X)


@dataclass
class LookupEvaluator(Evaluator):
    """Phase 2: replays a digitized published study. **Discrete candidates only.**

    Forward-compatibility requirement 2, exercised against real data for the first
    time. Phase 1's evaluator answers anywhere in the box; a published study answers
    only at the conditions it actually ran. **A proposal that is not in the table is
    an error, not an interpolation** — silently returning the nearest condition would
    let the replay claim it found a recipe nobody ever measured.

    Args:
        X_table: ``(n, d)`` the coded design, one row per published condition.
        y_table: ``(n,)`` the response. ``nan`` marks a condition whose value could
            not be extracted; proposing it raises.
        sd_table: ``(n,)`` per-condition dispersion from the published box statistics,
            ``nan`` where unavailable.
        metric: what the number is (requirement 7). Travels on every row.
        sd_floor: variance floor for conditions with no dispersion estimate. Required
            rather than defaulted to zero: a zero-variance point tells the GP that
            condition is known exactly, which is the strongest possible claim and the
            least warranted one here.

    Raises:
        KeyError: on a proposal absent from the table, listing the offending row.
        ValueError: on a proposal whose response was never extractable.
    """

    X_table: np.ndarray
    y_table: np.ndarray
    sd_table: np.ndarray
    metric: MetricIdentity
    sd_floor: float = 0.05
    _n_eval: int = 0

    def __post_init__(self) -> None:
        self.X_table = np.asarray(self.X_table, dtype=float)
        self.y_table = np.asarray(self.y_table, dtype=float).ravel()
        self.sd_table = np.asarray(self.sd_table, dtype=float).ravel()
        if not (len(self.X_table) == len(self.y_table) == len(self.sd_table)):
            raise ValueError(
                f"table lengths disagree: X {len(self.X_table)}, y {len(self.y_table)}, "
                f"sd {len(self.sd_table)}"
            )
        if self.sd_floor <= 0:
            raise ValueError(
                f"sd_floor must be positive, got {self.sd_floor}. Zero would assert the "
                "response is known exactly at conditions with no dispersion estimate."
            )
        # Row lookup by exact coded tuple. The design is integer-valued in coded space,
        # so exact matching is right and float tolerance would be a bug waiting.
        self._index = {tuple(np.rint(row).astype(int)): i
                       for i, row in enumerate(self.X_table)}

    @property
    def n_evaluations(self) -> int:
        return self._n_eval

    @property
    def candidates(self) -> np.ndarray:
        """``(k, d)`` the conditions that can actually be proposed — those with a
        response. This is what the optimizer must choose from."""
        ok = ~np.isnan(self.y_table)
        return self.X_table[ok]

    def truth(self, X: np.ndarray) -> np.ndarray:
        """``(n, 1)`` the published value, for SCORING only.

        There is no noiseless ground truth in a replay — the published number *is* the
        measurement, noise included. This exists so the Q17 scoring rule has something
        to call, and it returns the same quantity :meth:`evaluate` does. Named
        ``truth`` for interface compatibility and no more than that; the limitation is
        real and belongs in the write-up.
        """
        return self._rows(X, "truth")[0].reshape(-1, 1)

    def _rows(self, X: np.ndarray, who: str) -> tuple[np.ndarray, np.ndarray]:
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be (n, d); got shape {X.shape}")
        y = np.empty(len(X))
        sd = np.empty(len(X))
        for k, row in enumerate(X):
            key = tuple(np.rint(row).astype(int))
            i = self._index.get(key)
            if i is None:
                raise KeyError(
                    f"{who}: condition {key} is not in the published table. A replay may "
                    f"only propose conditions the study actually ran; interpolating would "
                    f"claim a recipe nobody measured."
                )
            if np.isnan(self.y_table[i]):
                raise ValueError(
                    f"{who}: condition {key} is in the design but its response was not "
                    f"extractable, so it cannot be proposed. Use `candidates`."
                )
            y[k] = self.y_table[i]
            s = self.sd_table[i]
            sd[k] = self.sd_floor if np.isnan(s) else max(float(s), self.sd_floor)
        return y, sd

    def evaluate(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        y, sd = self._rows(X, "evaluate")
        self._n_eval += len(X)
        return y.reshape(-1, 1), (sd**2).reshape(-1, 1)


@dataclass
class ContinuousLookupEvaluator(Evaluator):
    """Phase 3 in-house replay: discrete candidates at **continuous** coded levels.

    :class:`LookupEvaluator` indexes by ``tuple(np.rint(row).astype(int))`` because the
    Hall/Ogle design is -1/0/+1 in coded space, where rounding is exact and float
    tolerance would be the bug. The in-house coating titration is not like that: its
    coded doses are 0, 0.0256, 0.1026, 0.2308, 0.4872, 1. ``np.rint`` collapses the
    first four to ``0`` and the design loses two thirds of its levels to a silent key
    collision. So this class matches with :func:`numpy.isclose` instead, and
    ``LookupEvaluator`` is left exactly as it is -- Phase 2 replay depends on it.

    A proposal that is not in the table is a :class:`KeyError`, not the nearest
    neighbour, for the same reason as Phase 2: interpolating would let the replay claim
    a coating nobody ran.

    Args:
        X_table: ``(n, d)`` coded design, one row per measured tube.
        y_table: ``(n,)`` response. ``nan`` marks a condition with no usable value;
            proposing it raises rather than returning ``nan`` into the GP.
        sd_table: ``(n,)`` dispersion, ``nan`` where unavailable. n = 1 per level in
            this drop, so it is ``nan`` throughout and ``sd_floor`` does the work.
        metric: what the number is. Requirement 7, travels on every row.
        sd_floor: variance floor. Required positive: zero would tell the GP the
            condition is known exactly, which is the least warranted claim available.
        atol: absolute tolerance for matching a proposal to a table row. The tightest
            gap in the coating design is 0.0256 coded, so 1e-9 is four orders of
            magnitude clear of ever merging two real levels.
    """

    X_table: np.ndarray
    y_table: np.ndarray
    sd_table: np.ndarray
    metric: MetricIdentity
    sd_floor: float = 0.05
    atol: float = 1e-9
    _n_eval: int = 0

    def __post_init__(self) -> None:
        self.X_table = np.asarray(self.X_table, dtype=float)
        self.y_table = np.asarray(self.y_table, dtype=float).ravel()
        self.sd_table = np.asarray(self.sd_table, dtype=float).ravel()
        if not (len(self.X_table) == len(self.y_table) == len(self.sd_table)):
            raise ValueError(
                f"table lengths disagree: X {len(self.X_table)}, y {len(self.y_table)}, "
                f"sd {len(self.sd_table)}"
            )
        if self.X_table.ndim != 2:
            raise ValueError(f"X_table must be (n, d); got shape {self.X_table.shape}")
        if self.sd_floor <= 0:
            raise ValueError(
                f"sd_floor must be positive, got {self.sd_floor}. Zero would assert the "
                "response is known exactly at conditions with no dispersion estimate."
            )
        self._check_rows_are_distinguishable()

    def _check_rows_are_distinguishable(self) -> None:
        """Two table rows within ``atol`` would make lookup order-dependent."""
        for i in range(len(self.X_table)):
            for j in range(i + 1, len(self.X_table)):
                if np.allclose(self.X_table[i], self.X_table[j], rtol=0.0, atol=self.atol):
                    raise ValueError(
                        f"rows {i} and {j} are identical within atol={self.atol}: "
                        f"{self.X_table[i].tolist()}. Lookup would silently pick one."
                    )

    @property
    def n_evaluations(self) -> int:
        return self._n_eval

    @property
    def candidates(self) -> np.ndarray:
        """``(k, d)`` conditions that can be proposed -- those with a response."""
        return self.X_table[~np.isnan(self.y_table)]

    def _rows(self, X: np.ndarray, who: str) -> tuple[np.ndarray, np.ndarray]:
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be (n, d); got shape {X.shape}")
        if X.shape[1] != self.X_table.shape[1]:
            raise ValueError(
                f"X has {X.shape[1]} columns; table has {self.X_table.shape[1]}"
            )
        y = np.empty(len(X))
        sd = np.empty(len(X))
        for k, row in enumerate(X):
            hits = np.where(
                np.all(np.isclose(self.X_table, row, rtol=0.0, atol=self.atol), axis=1)
            )[0]
            if hits.size == 0:
                raise KeyError(
                    f"{who}: condition {row.tolist()} is not in the lab table. A replay "
                    f"may only propose measured tubes; interpolating would claim a "
                    f"coating nobody ran. Use `candidates`."
                )
            i = int(hits[0])
            if np.isnan(self.y_table[i]):
                raise ValueError(
                    f"{who}: condition {row.tolist()} is in the design but has no "
                    f"response yet -- it is ungated. Use `candidates`."
                )
            y[k] = self.y_table[i]
            s = self.sd_table[i]
            sd[k] = self.sd_floor if np.isnan(s) else max(float(s), self.sd_floor)
        return y, sd

    def truth(self, X: np.ndarray) -> np.ndarray:
        """``(n, 1)`` the measured value, for SCORING only.

        Same caveat as :meth:`LookupEvaluator.truth`, and one more: there is no
        noiseless ground truth in a wet-lab replay, and with n = 1 per level there is
        not even a replicate mean. This returns exactly what :meth:`evaluate` returns.
        Present for interface parity with Phase 2 and no more than that.
        """
        return self._rows(X, "truth")[0].reshape(-1, 1)

    def evaluate(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        y, sd = self._rows(X, "evaluate")
        self._n_eval += len(X)
        return y.reshape(-1, 1), (sd**2).reshape(-1, 1)
