"""The identification floor: the regret no arm can beat at a given budget and noise.

**Why this exists before the budget-to-target grid rather than after it.** A
budget-to-target curve reports "evaluations needed to reach regret T". If T sits below
what the assay can resolve, the curve does not measure efficiency -- it measures
censoring, and every arm is censored together. That is worth an afternoon to find out
rather than a week of compute.

THE CONSTRUCTION
----------------
Plant the true optimum in the visited set and score normally. A method that has already
visited the best point in the space cannot be beaten by one that still has to find it,
so the surviving regret is **pure identification error** and is a lower bound for every
arm at that budget and noise. It is a loose bound in the sense that real arms also have
to search; it is a *valid* bound, which is what pruning targets requires.

THE TWO RULES MOVE IN OPPOSITE DIRECTIONS
------------------------------------------
* **Rule A (best-observed)** picks by observation, so every extra point is another
  chance for a mediocre one to draw lucky noise and displace the planted optimum. Its
  floor therefore **rises with n**. Spending more does not buy a tighter target under
  this rule; past a point it buys a looser one.
* **Rule C (posterior mean)** pools every observation into one fit, so its floor
  **falls with n**, limited by how well the surface can be estimated rather than by the
  luckiest single draw.

Reporting one floor for both rules would hide that crossing, which is why
:func:`rule_a_floor` is scoped to rule A by name. Rule C's floor needs a GP and lives in
the script that runs it, not here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import Tensor

from boec.optimizers import lhs_design

__all__ = ["FloorResult", "draw_observations", "planted_design", "rule_a_floor"]


@dataclass(frozen=True)
class FloorResult:
    """Args:
        regrets: ``(n_reps,)`` regret of the observed argmax on each noise draw.
        mean_regret: the floor itself.
        hit_rate: fraction of draws on which the assay named the planted optimum. The
            number a lab can act on -- a mean regret alone hides whether the failure is
            one catastrophe or steady drift.
    """

    regrets: np.ndarray
    mean_regret: float
    hit_rate: float


def planted_design(bounds: Tensor, n: int, x_star: Tensor, seed: int) -> Tensor:
    """``n - 1`` Latin-hypercube points plus the true optimum, planted exactly.

    Args:
        bounds: ``(2, d)``.
        n: total points, at least 2 -- a design with no competitor cannot misidentify.
        x_star: ``(d,)`` the true optimum, inside ``bounds``.
        seed: fixes the filler design.

    Returns:
        ``(n, d)`` with ``x_star`` as the final row, bit-identical to the input. A
        tolerance would plant a slightly worse point and lift the computed floor above
        the real one.

    Raises:
        ValueError: on ``n < 2``, or an optimum outside ``bounds`` -- which would plant
            a point no arm could visit and put the "floor" below anything achievable.
    """
    if n < 2:
        raise ValueError(f"a planted design needs at least 2 points, got {n}")
    x = torch.as_tensor(x_star, dtype=torch.double).reshape(-1)
    lo, hi = bounds[0].double(), bounds[1].double()
    if bool(((x < lo) | (x > hi)).any()):
        raise ValueError(f"the planted optimum {x.tolist()} lies outside the box")
    return torch.cat([lhs_design(bounds, n - 1, seed=seed), x.reshape(1, -1)], dim=0)


def draw_observations(truth: np.ndarray, *, sigma_rel: float, sigma_add: float,
                      rng: np.random.Generator, n_reps: int) -> np.ndarray:
    """``n_reps`` independent readouts of a fixed set of points.

    The model is the oracle's own: ``y = f(1 + eps) + eta``, so ``Var[y] = f^2
    sigma_rel^2 + sigma_add^2``. Drawn here rather than through ``BiphasicOracle``
    because the truth is held fixed across reps and only the assay is resampled -- but
    a floor computed under a different noise model bounds nothing, so the agreement is
    asserted in ``tests/test_floor.py``.

    Returns:
        ``(n_reps, len(truth))``.
    """
    t = np.asarray(truth, dtype=float).ravel()
    # No branch on sigma == 0: numpy returns exact zeros for a zero scale, and skipping
    # the draw instead would change the RNG stream, so a noiseless reference run would
    # not be the sigma -> 0 limit of the noisy ones.
    shape = (int(n_reps), t.size)
    eps = rng.normal(0.0, sigma_rel, size=shape)
    eta = rng.normal(0.0, sigma_add, size=shape)
    return t * (1.0 + eps) + eta


def rule_a_floor(truth: np.ndarray, *, optimum_value: float, sigma_rel: float,
                 sigma_add: float, n_reps: int, seed: int) -> FloorResult:
    """Expected regret of the observed argmax over a visited set containing the optimum.

    Args:
        truth: ``(n,)`` noiseless values at the visited points, one of which should be
            the optimum -- otherwise this is not a floor, just a regret.
        optimum_value: the instance's true maximum.
        sigma_rel, sigma_add: the assay.
        n_reps: independent readouts of the same points. Cheap -- no model is fitted --
            so this is where the precision comes from, not from more instances.
        seed: fixes the noise.
    """
    t = np.asarray(truth, dtype=float).ravel()
    Y = draw_observations(t, sigma_rel=sigma_rel, sigma_add=sigma_add,
                          rng=np.random.default_rng(seed), n_reps=n_reps)
    picked = t[np.argmax(Y, axis=1)]
    regrets = float(optimum_value) - picked
    return FloorResult(regrets=regrets, mean_regret=float(regrets.mean()),
                       hit_rate=float(np.mean(picked >= t.max())))
