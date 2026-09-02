"""Experiment 2 comparison arms that are Person A's rather than Person B's.

OWNERSHIP: Person A. Phase 1 only.

B's ``optimizers.py`` already supplies random, Sobol and Latin-hypercube designs, and
``runner.run_static_baseline`` averages them over random orderings. This file adds the
one arm those do not cover.

------------------------------------------------------------------------------
COORDINATE DESCENT, AND WHY IT IS HERE
------------------------------------------------------------------------------

Tune one ingredient at a time, keep the best setting, move to the next, repeat. It is
what a careful person does with no statistics training and no software, and it is a
genuinely strong strategy on a landscape where the ingredients do not interact much.

**It is in E2 to pre-empt an objection, not to be beaten.** The biphasic oracle is a sum
of terms each unimodal in its own coordinate, which is intrinsically easy for
coordinate-wise search — A measured the shortfall at 0-1% of achievable depth even at
double the chosen interaction strength. A reviewer will notice, and "your oracle is
separable, so of course your method wins" is a fair hit if we have not already said it.
Reporting this arm converts that from an objection into a stated limitation.

Genuine multivariate difficulty in E2 comes from **Hartmann6**, which is why that arm is
not optional.

------------------------------------------------------------------------------
SCORING
------------------------------------------------------------------------------

The returned curve is best-so-far of the **noiseless** value at the points visited, not
of the noisy measurements — OPEN-QUESTIONS Q17. Selection uses only what the method is
allowed to see; scoring uses ``truth()``, which no model ever sees. Scoring on
observations would let an arm win by drawing lucky noise, and the size of that advantage
scales with how many distinct points an arm visits, which differs by arm *by design*.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import Tensor

__all__ = ["CoordinateDescentResult", "coordinate_descent"]


@dataclass
class CoordinateDescentResult:
    """Attributes:
        curve: ``(budget,)`` best-so-far of the NOISELESS value, in visit order.
        X: ``(budget, d)`` every point measured, in order.
        Y: ``(budget, 1)`` the noisy measurements the method actually saw.
        n_sweeps: how many complete passes over the coordinates were made.
    """

    curve: np.ndarray
    X: Tensor
    Y: Tensor
    n_sweeps: int


def coordinate_descent(
    evaluator,
    bounds: Tensor,
    *,
    budget: int = 48,
    seed: int = 0,
    n_levels: int = 5,
) -> CoordinateDescentResult:
    """Sweep the coordinates one at a time, keeping the best setting found.

    Args:
        evaluator: anything with ``evaluate(X) -> (Y, Yvar)`` **and** ``truth(X)``.
            ``truth`` is used only for scoring and is never consulted when choosing
            where to go next.
        bounds: ``(2, d)``.
        budget: total measurements. Spent exactly, so the arm is comparable to every
            other E2 arm — the equal-budget rule is the whole basis of the comparison.
        seed: fixes the starting point.
        n_levels: how many settings of a coordinate to try per visit. Five gives a
            reasonable scan without exhausting the budget on one ingredient at d=6.

    Returns:
        A :class:`CoordinateDescentResult`.
    """
    if bounds.ndim != 2 or bounds.shape[0] != 2:
        raise ValueError(f"bounds must be (2, d), got {tuple(bounds.shape)}")
    if budget < 1:
        raise ValueError(f"budget must be positive, got {budget}")

    d = int(bounds.shape[1])
    lo, hi = bounds[0].double(), bounds[1].double()
    rng = np.random.default_rng(seed)

    # Start from a random interior point. A centre start would be a hidden advantage
    # on an oracle whose optimum sits near the middle.
    current = torch.from_numpy(rng.uniform(0, 1, d)) * (hi - lo) + lo

    visited: list[Tensor] = []
    observed: list[float] = []
    sweeps = 0

    while len(visited) < budget:
        sweeps += 1
        for i in range(d):
            if len(visited) >= budget:
                break
            levels = torch.linspace(float(lo[i]), float(hi[i]), n_levels,
                                    dtype=torch.double)
            best_level, best_here = float(current[i]), -np.inf
            for lvl in levels:
                if len(visited) >= budget:
                    break
                x = current.clone()
                x[i] = lvl
                y, _ = evaluator.evaluate(x.unsqueeze(0))
                visited.append(x)
                observed.append(float(y))
                # The method itself only ever compares OBSERVED values -- it has no
                # access to the truth, exactly like every other arm.
                if float(y) > best_here:
                    best_here, best_level = float(y), float(lvl)
            current[i] = best_level
        if sweeps > budget:            # cannot happen with n_levels >= 1; guard anyway
            break

    X = torch.stack(visited)
    Y = torch.tensor(observed, dtype=torch.double).reshape(-1, 1)
    truth = evaluator.truth(X).double().numpy().ravel()
    return CoordinateDescentResult(
        curve=np.maximum.accumulate(truth), X=X, Y=Y, n_sweeps=sweeps
    )
