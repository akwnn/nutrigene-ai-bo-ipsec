"""Certified formulation sets -- a finite-set estimand for a 48-well budget.

**Why this exists.** `boec.vorobev` certifies a whole continuous excursion set
simultaneously. Measured on this project's own campaigns, that abstains on 76-92% of
runs, and posterior inflation -- the fix that makes the region certificate honest --
makes the abstention *worse*, because a wider posterior shrinks the certified region.
A lab that runs 48 wells and is told "insufficient evidence" four times in five has not
been helped.

**The change.** A cell-manufacturing lab does not scale up a region; it scales up a
handful of formulations. So certify those instead:

    return the largest set S of candidate formulations such that
    P( every x in S truly exceeds tau ) >= alpha

This is the **same simultaneous form** as the region claim -- one joint probability over
the whole returned set, not a per-point rate -- but over a set the method is allowed to
choose. It is strictly easier to satisfy, because the region estimand is forced to
include the boundary points the posterior is least sure about and this one is not.

**Relation to the region certificate.** For any S contained in a certified region, the
region's guarantee implies this one; the converse does not hold. So this estimand is
weaker per-claim and far more often non-vacuous. That trade is the point, and it must be
stated whenever a result from this module is reported.

**What it does NOT do.** It does not rescue a miscalibrated posterior. If the GP is
overconfident, this is overconfident in exactly the same proportion, and it needs the
same inflation calibration (`SPADE-ASSURANCE-CALIBRATION-SPEC.md`) to be honest.
"""
from __future__ import annotations

import torch


def certified_topk(draws: torch.Tensor, tau: float, alpha: float,
                   k_max: int | None = None) -> list[int]:
    """Largest set of formulations jointly certifiable above ``tau`` at level ``alpha``.

    Args:
        draws: ``(n_draws, n_points)`` posterior draws over the candidate set.
        tau: the acceptability threshold.
        alpha: required joint probability that EVERY returned point exceeds ``tau``.
        k_max: optional cap on the returned set size.

    Returns:
        Indices into ``draws``'s second axis. Possibly empty, which is the honest
        answer when nothing is jointly certifiable.

    Greedy in descending marginal excursion probability. The scan does not stop at the
    first rejection: a point strongly correlated with those already chosen can be free
    to add even when a marginally-safer point was not, so rejecting one candidate must
    not end the search. Greedy is not guaranteed optimal for this set function, and the
    returned set is therefore a valid-but-possibly-not-maximal certificate -- which is
    the conservative direction, and is the only direction that keeps the guarantee.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1); got {alpha!r}")
    exceed = draws > tau                                     # (n_draws, n_points)
    p_point = exceed.double().mean(dim=0)
    order = torch.argsort(p_point, descending=True).tolist()

    joint = torch.ones(draws.shape[0], dtype=torch.bool)
    chosen: list[int] = []
    for i in order:
        if k_max is not None and len(chosen) >= k_max:
            break
        cand = joint & exceed[:, i]
        if cand.double().mean().item() >= alpha:
            joint = cand
            chosen.append(i)
    return chosen


def topk_columns(draws: torch.Tensor, truth: torch.Tensor, tau: float,
                 alphas=(0.5, 0.8, 0.95), k_max: int | None = None) -> dict:
    """Scoring columns for one campaign, mirroring `vorobev_columns`' shape.

    ``topk_contain`` is the honest analogue of the region certificate's truth
    containment: 1.0 only if EVERY returned formulation is genuinely above ``tau``.
    A single bad formulation in the set fails the whole claim, exactly as a single
    uncovered point fails the region claim.

    ``topk_frac_correct`` is reported alongside it and is NOT the guarantee -- it is the
    per-formulation hit rate, which is always at least as flattering. Both are emitted so
    that no later analysis can quote the easier number as though it were the claim.
    """
    out: dict = {}
    for a in alphas:
        idx = certified_topk(draws, tau, a, k_max=k_max)
        n = len(idx)
        out[f"topk_n_{a}"] = n
        out[f"topk_empty_{a}"] = (n == 0)
        if n == 0:
            out[f"topk_contain_{a}"] = float("nan")
            out[f"topk_frac_correct_{a}"] = float("nan")
        else:
            good = (truth[idx] > tau)
            out[f"topk_contain_{a}"] = float(bool(good.all()))
            out[f"topk_frac_correct_{a}"] = float(good.double().mean())
    return out
