"""Identification error: what a design loses to the assay after it has found the answer.

**Why this exists before the budget-to-target grid rather than after it.** A
budget-to-target curve reports "evaluations needed to reach regret T". If T sits below
what the assay can resolve, the curve does not measure efficiency -- it measures
censoring. Whether that is true has to be settled before the grid runs, not after.

THE CONSTRUCTION
----------------
Plant the true optimum in the visited set -- exactly, not to a tolerance -- and score
normally. The surviving regret is then **pure identification error**: the design already
contains the best point in the space, so nothing it loses is a failure to search.

⚠️ THIS IS NOT A UNIVERSAL LOWER BOUND, AND IT WAS ORIGINALLY WRITTEN AS ONE
-----------------------------------------------------------------------------
The first version of this module claimed that a design containing the optimum cannot be
beaten by one that must find it. **That is false**, and the grid refuted it: at
d=6, sigma_rel=0.25 the space-filling planted design scores 0.129 at n=384 while a real
qLogEI campaign reports **0.049** at n=500.

The error was in what rule A actually costs. Rule A's penalty on a mis-pick is the true
value of *whichever point won by luck*, so the bound needs the runners-up to be **bad**.
Spread-out competitors are bad, and clustered ones are not:

    same n, same noise, optimum planted in both, 25 instances, d=6 sigma=0.25
        space-filling competitors   0.1226
        clustered competitors       0.0144      <- 8.5x lower

**Concentration is protective under rule A, independently of finding a better point.**
An adaptive arm concentrates, so it goes *below* this number. What the planted design
measures is therefore the identification penalty **of a space-filling design** -- a
bound for the static arms (random, Sobol, LHS, and the classical arm insofar as its
design spreads), and not for anything adaptive. See
``test_concentrating_the_competitors_lowers_rule_a_regret``.

THE TWO RULES MOVE IN OPPOSITE DIRECTIONS
------------------------------------------
* **Rule A (best-observed)** picks by observation, so every extra point is another
  chance for a mediocre one to draw lucky noise and displace the planted optimum. Its
  error therefore **rises with n**, for a fixed design family.
* **Rule C (posterior mean)** pools every observation into one fit, so it **falls with
  n**, limited by how well the surface can be estimated rather than by the luckiest
  single draw.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import Tensor

from boec.optimizers import lhs_design

__all__ = ["IdentificationResult", "draw_observations", "planted_design",
           "rule_a_identification_error"]


@dataclass(frozen=True)
class IdentificationResult:
    """Args:
        regrets: ``(n_reps,)`` regret of the observed argmax on each noise draw.
        mean_regret: the identification penalty for this design.
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
        tolerance would plant a slightly worse point, so the number would mix in a
        search failure and stop being pure identification error.

    Raises:
        ValueError: on ``n < 2``, or an optimum outside ``bounds`` -- which would plant
            a point no arm could visit, making the number unreachable rather than
            merely optimistic.
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
    a penalty computed under a different noise model describes a different assay, so the
    agreement is asserted in ``tests/test_identification.py``.

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


def rule_a_identification_error(truth: np.ndarray, *, optimum_value: float,
                                sigma_rel: float, sigma_add: float, n_reps: int,
                                seed: int) -> IdentificationResult:
    """Expected regret of the observed argmax over a visited set containing the optimum.

    **Scoped to the design it is given.** The result depends strongly on how good the
    *runners-up* are, not only on whether the optimum was visited -- see the module
    docstring. Passing a space-filling design gives the static arms' identification
    penalty; passing a clustered one gives a far smaller number.

    Args:
        truth: ``(n,)`` noiseless values at the visited points, one of which should be
            the optimum -- otherwise this is not identification error, just regret.
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
    return IdentificationResult(regrets=regrets, mean_regret=float(regrets.mean()),
                                hit_rate=float(np.mean(picked >= t.max())))
