"""Batch level-set estimation: where plate 2 should spend its wells.

Plate 1 builds a map. Plate 2's job is not to confirm the peak -- Q58 measured that
confirming the peak *hurt* the classical arm, 0.0958 -> 0.1437, because its first reading
was already the trustworthy one. Plate 2's job is to resolve the **boundary of the
certified region**, because that boundary is what limits how large a region can be
certified at all.

CRITERION
---------
Bryan's (2005) straddle, ``1.96*sd(x) - |mean(x) - theta|``: high where the model is
uncertain *and* near the threshold. Batched greedily, which is the practical stand-in for
Chevalier et al.'s (Technometrics 2014) closed-form parallel SUR.

**The criterion is not boundary-only, and that is deliberate.** Azzimonti et al.'s own
figures place some optimal SUR points deep in the interior, to secure the classification
of regions a boundary-only rule would leave uncertain. The ``1.96*sd`` term is what allows
that: a far-from-threshold point with large enough uncertainty can outscore a
near-threshold point that is already well determined. Hard-coding "sample the boundary"
would be an approximation to this, not an implementation of it. There is a test asserting
the criterion can leave the boundary.

WHY EXCLUSION IS NOT OPTIONAL
------------------------------
The straddle surface is smooth, so a greedy batch takes ``q`` near-identical points --
eight wells at one location, which is a replicate dressed up as a design. Each pick
therefore masks a Chebyshev ball around itself. The radius is derived from the model's own
fitted lengthscale, never hardcoded, because a fixed radius means something different at
every noise level.

If exclusion empties the candidate pool, this returns **fewer points rather than
duplicates**: silently handing back repeats would spend wells while reporting a batch size
that was never achieved.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["batch_lse", "exclusion_radius", "straddle_score"]

#: Bryan's (2005) constant. The 1.96 is the 95% normal quantile, not a tuned knob.
STRADDLE_Z = 1.96
#: Fraction of the median fitted lengthscale used as the exclusion radius.
EXCLUSION_FRACTION = 0.25


def straddle_score(mean: Tensor, sd: Tensor, theta: float) -> Tensor:
    """``1.96*sd - |mean - theta|``. High where uncertain AND near the threshold."""
    return STRADDLE_Z * sd - (mean - theta).abs()


def exclusion_radius(model, fallback: float = 0.1) -> float:
    """A quarter of the median fitted ARD lengthscale, read off the live model.

    Read, never hardcoded: a fixed radius means something different at every noise level
    and dimension, and this repo has already documented (D8) what happens when a decision
    rule is anchored on a constant instead of on the object it is about.
    """
    try:
        ls = model.covar_module.base_kernel.lengthscale.detach().reshape(-1)
        return float(ls.median()) * EXCLUSION_FRACTION
    except AttributeError:
        return fallback


def batch_lse(model, X_cand: Tensor, theta: float, q: int,
              exclude: float = 0.1) -> Tensor:
    """``(<=q, d)`` batch of candidates maximising the straddle, greedily, with exclusion.

    Returns fewer than ``q`` points if exclusion empties the pool -- never duplicates.
    """
    mean, sd = model.posterior_mean_and_sd(X_cand)
    score = straddle_score(mean, sd, theta)
    available = torch.ones(X_cand.shape[0], dtype=torch.bool)
    picks: list[Tensor] = []

    for _ in range(q):
        if not bool(available.any()):
            break
        masked = torch.where(available, score, torch.tensor(float("-inf"),
                                                            dtype=score.dtype))
        idx = int(torch.argmax(masked))
        picks.append(X_cand[idx])
        far = (X_cand - X_cand[idx]).abs().max(dim=1).values >= exclude
        available = available & far

    return torch.stack(picks) if picks else X_cand[:0]
