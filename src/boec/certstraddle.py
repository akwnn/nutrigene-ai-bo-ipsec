"""Certificate-targeted acquisition: aim at the contour the CERTIFICATE's frontier sits on.

------------------------------------------------------------------------------
THE MISMATCH THIS FIXES, MEASURED RATHER THAN ASSERTED
------------------------------------------------------------------------------

`boec.lse.straddle_score` is Bryan's ``1.96*sd - |mean - theta|``. Its target is ``mean =
theta`` -- the ``p = 0.5`` contour. That is exactly the right target for **map** loss, whose
symmetric-difference error is defined at that contour, and this session measured the
consequence on both deliverables:

* On map error, targeted plate 2 does **not** beat random placement: +0.0029 against a
  pre-declared SESOI of 0.02, at n=250 paired campaigns and MDE 0.0057 -- a well-powered null,
  consistent with KF-3/KF-3b/KF-3c.
* On **certificate** truth containment it does: **+0.0239, 95% CI [+0.0016, +0.0467]**,
  n=149 campaigns, p=0.019, independently replicated by `versionb_predictive` at p=0.0088 --
  while random placement of the same 8 wells is worth **+0.0003, p=0.95**.

So the adaptivity carries real value, on the certificate, while being aimed at a contour chosen
for the map.

------------------------------------------------------------------------------
WHERE THE CERTIFICATE'S FRONTIER ACTUALLY IS
------------------------------------------------------------------------------

`boec.vorobev.conservative_estimate` returns the largest Vorob'ev quantile
``{x : p(x) >= rho_alpha}`` whose **joint** containment reaches ``alpha``. For a joint claim
over many points, ``rho_alpha`` sits well above 0.5 -- the region is bounded by a
high-exceedance-probability contour, not the median one. Writing that contour in response units
with ``p(x) = Phi((mean - theta)/sd)``:

    p(x) = rho   <=>   mean(x) - z_rho * sd(x) = theta,      z_rho = Phi^-1(rho)

At ``rho = 0.5`` this is ``mean = theta``: **Bryan's straddle is the rho=0.5 special case**, not
a competitor. At ``rho = 0.95`` it is the LCB contour, displaced ``1.645*sd`` deeper into the
acceptable region. The generalisation is one parameter wide and is exact at the boundary case,
which is what makes it safe to adopt: at ``rho=0.5`` every committed number is unchanged.

------------------------------------------------------------------------------
WHAT IS NOT CLAIMED
------------------------------------------------------------------------------

That this **improves** the certificate is a hypothesis, not a result. The +0.0239 above is a
**post-hoc endpoint** (containment was examined after map error failed), it carries no Holm
correction across the endpoints examined that session, and no SESOI for containment has ever
been declared. Nothing here is adopted into an arm until a pre-registration with a declared
SESOI says so and a prospective run clears it. The rho=0.5 reduction test exists precisely so
that adopting this module cannot silently move a committed result.
"""

from __future__ import annotations

import math

import torch
from torch import Tensor

from boec.lse import STRADDLE_Z

__all__ = ["batch_lse_rho", "certificate_straddle", "rho_contour_offset"]


def rho_contour_offset(rho: float) -> float:
    """``z_rho = Phi^-1(rho)`` -- how far, in units of ``sd``, the ``rho``-contour sits from
    the posterior mean.

    Zero at ``rho = 0.5``, positive above it, symmetric below.

    Raises:
        ValueError: on ``rho`` outside the OPEN interval ``(0, 1)``, where the normal
            quantile is infinite and the contour is undefined.
    """
    r = float(rho)
    if not 0.0 < r < 1.0:
        raise ValueError(
            f"rho must be in the open interval (0, 1), got {r} -- at 0 or 1 the normal "
            "quantile is infinite and there is no contour to target")
    return float(math.sqrt(2.0) * torch.erfinv(torch.tensor(2.0 * r - 1.0,
                                                            dtype=torch.double)))


def certificate_straddle(mean: Tensor, sd: Tensor, theta: float, rho: float) -> Tensor:
    """``1.96*sd - |mean - z_rho*sd - theta|``: straddle the ``rho``-contour, not the median.

    High where the model is uncertain **and** near the contour that bounds the certified
    region at Vorob'ev level ``rho``.

    The ``1.96*sd`` term is kept exactly as `boec.lse.straddle_score` has it, and for the same
    documented reason: it lets a far-from-contour point with large enough uncertainty outscore
    a near-contour point that is already well determined. Azzimonti's own SUR points are
    sometimes deep in the interior, and hard-coding "sample the contour" would be an
    approximation to that rather than an implementation of it. There is a test asserting the
    criterion can still leave the contour.

    Args:
        mean: ``(N,)`` posterior mean on the candidate set.
        sd: ``(N,)`` posterior SD, non-negative.
        theta: the acceptability threshold, in response units.
        rho: the Vorob'ev level whose contour to target. ``0.5`` reproduces
            :func:`boec.lse.straddle_score` exactly.

    Raises:
        ValueError: on ``rho`` outside ``(0, 1)`` or any negative ``sd``.
    """
    z = rho_contour_offset(rho)
    if bool((sd < 0).any()):
        raise ValueError("sd must be non-negative; a negative posterior SD is a bug upstream")
    return STRADDLE_Z * sd - (mean - z * sd - theta).abs()


def batch_lse_rho(model, X_cand: Tensor, theta: float, q: int,
                  exclude: float = 0.1, rho: float = 0.5) -> Tensor:
    """`boec.lse.batch_lse` with the target contour moved to the Vorob'ev level ``rho``.

    ``rho = 0.5`` is **bit-identical** to :func:`boec.lse.batch_lse` with ``sigma=None`` --
    asserted by ``test_batch_lse_rho_at_one_half_is_bit_identical_to_the_committed_batch_lse``.
    That is the entire safety argument for introducing this: the adjudicated ``versionb``
    column depends on the committed selection, and a new parameter that could not reproduce it
    exactly would put every prior number in question.

    The greedy loop, the exclusion ball, the Chebyshev radius and the short-batch contract are
    `batch_lse`'s, unchanged and for its documented reasons: with no exclusion the loop
    re-selects its own argmax every iteration and returns ``q`` wells at one location, a
    replicate dressed up as a design.

    Args:
        rho: the Vorob'ev level whose contour to straddle. The certificate's frontier sits at
            ``rho_alpha``, which is well above 0.5 for a joint claim; 0.5 reproduces Bryan's
            published latent straddle.
    """
    mean, sd = model.posterior_mean_and_sd(X_cand)
    score = certificate_straddle(mean, sd, theta, rho)
    available = torch.ones(X_cand.shape[0], dtype=torch.bool)
    picks: list[Tensor] = []

    for _ in range(q):
        if not bool(available.any()):
            break
        masked = torch.where(available, score,
                             torch.tensor(float("-inf"), dtype=score.dtype))
        idx = int(torch.argmax(masked))
        picks.append(X_cand[idx])
        far = (X_cand - X_cand[idx]).abs().max(dim=1).values >= exclude
        available = available & far

    return torch.stack(picks) if picks else X_cand[:0]
