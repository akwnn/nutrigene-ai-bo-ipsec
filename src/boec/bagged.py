"""Bagged certification: intersect certified regions across bootstrap refits.

------------------------------------------------------------------------------
WHY THIS IS STRUCTURALLY DIFFERENT FROM EVERY OTHER ATTEMPT
------------------------------------------------------------------------------

Every prior correction in this project reasons about a **single** fitted posterior's variance:

    k_eff          (KR)  FAILED  -- dispersion 1138x vs box volume's 370x, strictly dominated
    kappa_tail     (KS)  FAILED  -- separates at 0.19 SD vs volume's 1.22, and moves the WRONG
                                    way: significantly LOWER for the overconfident arm
                                    (-0.0869, 95% CI [-0.1385, -0.0380], p=3.5e-05)
    scope detector       FAILED  -- 0 of 50 correct on both held-out families
    selection-blind (KW) running -- still uses a fitted posterior, just a different design's
    inflation      (KT-B) running -- still scales a fitted posterior's variance

All of them take the GP's own variance as the object to reason about. **E3 measured that
object to be wrong**: latent coverage 0.7644-0.8189 against nominal 0.95, in every cell.

Bagging does not reason about it at all. Refit on bootstrap resamples of the wells and
**intersect** the certified regions. Variation ACROSS fits exposes the uncertainty a single
posterior structurally cannot show -- above all uncertainty in the fitted lengthscales and
noise, which the posterior conditions on **as if they were known**. That is precisely the
component E3's under-coverage is consistent with, and no rescaling of a single posterior can
recover it, because the single posterior has already committed to one hyperparameter estimate.

------------------------------------------------------------------------------
WHY THE INTERSECTION IS THE RIGHT COMBINATION
------------------------------------------------------------------------------

Each bag's `conservative_estimate` is a set claimed to sit inside the true excursion set. A
point survives only if **every** bag certifies it, so the bagged region is a subset of each
member and inherits the most cautious verdict pointwise. It is monotone in `n_bags` -- more
bags can only shrink it -- which makes `n_bags` a nested calibration parameter of the same
kind as `alpha` and the inflation factor `c`, rather than a free knob.

No detector, no calibration family, no tuning constant.

------------------------------------------------------------------------------
WHAT IS NOT CLAIMED
------------------------------------------------------------------------------

That it works. It is registered before it is run, like everything else here, and the
single-bag reduction test exists so that adopting it cannot silently move a committed number.
"""

from __future__ import annotations

import torch
from torch import Tensor

from boec.vorobev import conservative_estimate

__all__ = ["bagged_certificate"]


def bagged_certificate(draws_for_bag, n_bags: int, theta: float, alpha: float) -> Tensor:
    """Intersection of the per-bag conservative estimates.

    Args:
        draws_for_bag: callable ``b -> (n_draws, n)`` returning the joint posterior draws for
            bootstrap bag ``b``. Called **exactly once per bag**; a test asserts the count,
            because a "bagged" arm that silently reuses one fit is the ordinary certificate
            wearing a different label -- the failure mode this repository has three errata for.
        n_bags: number of bootstrap refits. ``1`` reduces exactly to
            :func:`boec.vorobev.conservative_estimate`.
        theta: acceptability threshold.
        alpha: per-bag joint confidence.

    Returns:
        ``(n,)`` boolean mask: the points every bag certifies.

    Raises:
        ValueError: if ``n_bags`` is not positive.
    """
    if int(n_bags) < 1:
        raise ValueError(f"n_bags must be >= 1, got {n_bags}")

    out: Tensor | None = None
    for b in range(int(n_bags)):
        mask = conservative_estimate(draws_for_bag(b), theta, alpha)
        out = mask if out is None else (out & mask)
    assert out is not None
    return out
