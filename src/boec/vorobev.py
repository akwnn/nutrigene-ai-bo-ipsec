"""Vorob'ev quantiles, conservative excursion sets, and the always-defined ``alpha*``.

------------------------------------------------------------------------------
WHY POINTWISE CERTIFICATION IS THE WRONG OBJECT
------------------------------------------------------------------------------

``{x : LCB(x) >= tau}`` is twenty thousand **marginal** statements presented as one
**regional** statement. Under independence, twenty thousand pointwise 95% claims contain
a thousand expected false certifications; spatial correlation softens that but does not
repair the category error. What a batch record asserts is joint:

    P(CE_alpha  is a subset of  Gamma)  >=  alpha

-- the probability that **no** certified point is false. That is the conservative
estimate of Azzimonti, Ginsbourger, Chevalier, Bect & Richet (2016; SIAM/ASA JUQ 2021),
built on Chevalier's (2013) Vorob'ev machinery.

------------------------------------------------------------------------------
TWO MARGINS, SEPARATED
------------------------------------------------------------------------------

Peterson's ``P(Y >= tau | x) >= gamma`` mixes two different things inside one Phi:
**process** noise (irreducible -- what tomorrow's batch does) and **estimation**
uncertainty (reducible -- what these 48 wells did not tell you). Separating them:

* **Margin 1, process.** With perfect knowledge ``P(Y >= tau) >= gamma`` is exactly
  ``f >= tau + z_gamma * sigma``. So the manufacturing-relevant latent set is
  ``Gamma = {x : f(x) >= theta}`` with ``theta = tau + z_gamma*sigma``. **This margin is
  already swept by K6**: ``tau_max = mu_max(1 - z_gamma*sigma_rel)`` is that same algebra,
  and tau is registered as a fraction of it.
* **Margin 2, estimation.** Certify ``Gamma`` jointly at confidence ``alpha``. That is
  what this module adds.

The deliverable reads: *with confidence alpha, every recipe in this region has
batch-pass probability at least gamma* -- a ``(gamma, alpha)`` content-and-confidence
statement, which is the structure of a classical tolerance region.

------------------------------------------------------------------------------
WHY alpha* CANNOT DEGENERATE
------------------------------------------------------------------------------

A fixed-95% certified volume can be identically zero for every arm -- measured neighbour
density here is 0.49 points per lengthscale at n=48, d=6 -- and a table of zeros is not a
ranking. ``alpha*(theta)`` inverts the question: *the largest confidence at which a
non-empty conservative estimate exists.*

As ``rho -> 1`` the Vorob'ev quantile shrinks to the single most-certain point, so
containment tends to ``max_x p(x)``. **alpha* is therefore bounded below by the best
point's exceedance probability and is always defined, always in [0, 1], always ordered**
-- even when every 95% region is empty. A lab reads ``alpha*(tau) = 0.6`` as "this plate
supports 60%-confidence certification here; 95% needs another plate or a better assay."

------------------------------------------------------------------------------
SAMPLING, NOT ORTHANT PROBABILITIES
------------------------------------------------------------------------------

Azzimonti computes containment with orthant probabilities. This module uses **conditional
simulation**, which is a Monte Carlo approximation of the same object and is what the
grid size here forces: the joint covariance is 3.2 GB at 20,000 points, but on a
2,000-point subset the joint draw plus Cholesky plus 256 samples costs **0.14 s**
(measured). Callers draw on a subset and pass the draws in.

**Honest limit, and it must travel with the number:** conservative-given-the-model.
Hyperparameters are plug-in, so their uncertainty sits *outside* the guarantee. Azzimonti
et al. flag this themselves. Report the E3-style coverage check beside it to quantify the
cost.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["alpha_star", "conservative_estimate", "conservative_estimate_split",
           "containment_probability", "empirical_containment",
           "excursion_probability", "vorobev_deviation", "vorobev_expectation",
           "vorobev_quantile"]


def excursion_probability(draws: Tensor, theta: float) -> Tensor:
    """``p(x) = P(f(x) >= theta)``, the coverage function. ``(n_draws, n) -> (n,)``."""
    return (draws >= theta).double().mean(dim=0)


def vorobev_quantile(p: Tensor, rho: float) -> Tensor:
    """``Q_rho = {x : p(x) >= rho}``. ``(n,) -> (n,)`` bool."""
    return p >= rho


def vorobev_expectation(p: Tensor, draws: Tensor, theta: float) -> Tensor:
    """The Vorob'ev expectation: ``Q_rho*`` with ``vol(Q_rho*) == E[vol(Gamma)]``.

    The median-like summary of a random set. Chosen by scanning the achievable volumes,
    so the returned set is a genuine quantile rather than an interpolation between two.
    """
    target = float((draws >= theta).double().mean())
    order = torch.argsort(p, descending=True)
    k = int(round(target * p.numel()))
    mask = torch.zeros_like(p, dtype=torch.bool)
    if k > 0:
        mask[order[:k]] = True
    return mask


def containment_probability(draws: Tensor, mask: Tensor, theta: float) -> float:
    """``P(mask is a subset of {f >= theta})`` from the draws.

    The **joint** quantity: the fraction of posterior draws in which *every* point of
    ``mask`` clears ``theta``. Not the average of pointwise probabilities.

    The empty set is trivially contained and returns 1.0. Callers that would otherwise
    exploit that -- :func:`alpha_star`, :func:`conservative_estimate` -- exclude it
    explicitly.

    **THIS IS MODEL-INTERNAL, NOT VALIDATION.** :func:`conservative_estimate` selects on
    this quantity, so re-measuring it on the same draws is circular and cannot fall below
    ``alpha``. Use :func:`empirical_containment` against known truth to test the guarantee.
    """
    if int(mask.sum()) == 0:
        return 1.0
    return float((draws[:, mask] >= theta).all(dim=1).double().mean())


def alpha_star(draws: Tensor, theta: float, n_rho: int = 64) -> float:
    """The largest confidence at which a **non-empty** conservative estimate exists.

    Always defined: as ``rho -> 1`` the quantile shrinks to the most-certain point, so
    the supremum is bounded below by ``max_x p(x)``.
    """
    p = excursion_probability(draws, theta)
    best = 0.0
    for rho in torch.linspace(0.0, 1.0, n_rho, dtype=torch.double).tolist():
        mask = vorobev_quantile(p, rho)
        if int(mask.sum()) == 0:
            continue
        best = max(best, containment_probability(draws, mask, theta))
    # The single most-certain point is always an admissible non-empty set.
    return max(best, float(p.max()))


def conservative_estimate(draws: Tensor, theta: float, alpha: float,
                          n_rho: int = 64) -> Tensor:
    """``CE_alpha``: the **largest** Vorob'ev quantile with containment ``>= alpha``.

    Returns an all-false mask when no non-empty set reaches ``alpha`` -- which is a
    result (report it via :func:`alpha_star`), not a zero to be averaged.
    """
    p = excursion_probability(draws, theta)
    best = torch.zeros_like(p, dtype=torch.bool)
    for rho in torch.linspace(1.0, 0.0, n_rho, dtype=torch.double).tolist():
        mask = vorobev_quantile(p, rho)
        if int(mask.sum()) == 0:
            continue
        if containment_probability(draws, mask, theta) >= alpha:
            if int(mask.sum()) > int(best.sum()):
                best = mask
    return best


def conservative_estimate_split(draws: Tensor, theta: float, alpha: float,
                                n_rho: int = 64) -> tuple[Tensor, float]:
    """``CE_alpha`` **cross-fit**: selected on the first half of the draws, scored on the
    second. Returns ``(mask, containment on the held-out half)``.

    ------------------------------------------------------------------------------
    THE DEFECT THIS REMOVES, STATED EXACTLY
    ------------------------------------------------------------------------------

    :func:`conservative_estimate` scans ``n_rho`` Vorob'ev quantiles and keeps the
    largest whose containment -- **measured on the draws** -- reaches ``alpha``. That is a
    **maximum over 64 noisy estimates**, and it is then evaluated on *the same draws it
    was selected on*. The reported containment therefore cannot fall below ``alpha``
    (:func:`containment_probability` says so in its own docstring), and the number is
    biased upward by the winner's curse of the scan rather than merely circular.

    **The bias peaks when the candidates are near-tied**, because a maximum over 64
    estimates of one quantity is pure noise. That is the high-``gamma`` corner: at
    ``gamma = 0.99, tau_frac = 0.60`` the true set covers 0.99916 of the box, the
    quantiles collapse onto each other, and it is exactly where this repository's four
    sub-nominal containment cells sit.

    ------------------------------------------------------------------------------
    WHY A SPLIT RATHER THAN A CORRECTION
    ------------------------------------------------------------------------------

    Selection bias is removed **exactly** by never scoring on the draws that selected, not
    bounded by an analytic correction that would carry its own assumptions. The cost is
    2x draws and seconds of wall clock.

    The split is **the first half selects**, so at 1,024 draws the selection is
    bit-identical to :func:`conservative_estimate` on the committed 512 -- asserted in
    ``tests/test_vorobev.py``. The cross-fit changes what is *reported*, never what is
    *selected*, so a difference between this and the committed column is attributable to
    the estimator and to nothing else.

    ------------------------------------------------------------------------------
    WHAT THE RETURNED FLOAT IS, AND IS NOT
    ------------------------------------------------------------------------------

    It is an honest estimate of ``P(CE_alpha subset of Gamma)`` **under the model**. It is
    still conservative-given-the-model: hyperparameters are plug-in and their uncertainty
    sits outside the guarantee, exactly as for :func:`conservative_estimate`.
    :func:`empirical_containment` against known truth remains the only non-circular test
    of the guarantee itself, and this function does not replace it.

    ``nan`` for an empty selection. :func:`containment_probability` returns ``1.0`` there
    -- the empty set is vacuously contained -- and reporting that would put a perfect
    score in the column for a campaign that certified nothing, which is the inflation
    :func:`empirical_containment` already refuses to commit.

    Args:
        draws: ``(n_draws, n)`` joint posterior samples, ``n_draws`` **even** and at least
            2. An odd count raises rather than dropping a draw: a silently discarded draw
            makes the selection half differ from the committed estimator's by one sample,
            which is precisely the kind of unlogged arithmetic difference this project has
            had to catch five times.

    Raises:
        ValueError: on an odd or smaller-than-2 draw count.
    """
    n_draws = int(draws.shape[0])
    if n_draws < 2:
        raise ValueError(f"a cross-fit needs at least 2 draws to split, got {n_draws}")
    if n_draws % 2:
        raise ValueError(
            f"the draw count must be even so the halves are equal, got {n_draws}; "
            "dropping one would make the selection half differ from the committed "
            "estimator's by a sample")
    half = n_draws // 2
    mask = conservative_estimate(draws[:half], theta, alpha, n_rho=n_rho)
    if int(mask.sum()) == 0:
        return mask, float("nan")
    return mask, containment_probability(draws[half:], mask, theta)


def empirical_containment(mask: Tensor, truth: Tensor, theta: float) -> bool | None:
    """Is this set **actually** inside the true excursion set? The non-circular check.

    ``containment_probability`` is measured on the same draws that
    :func:`conservative_estimate` used to *select* the set, so it cannot fall below
    ``alpha`` -- it is a tautology and must never be reported as "the guarantee holds".
    Measured on this repo's K6b output: 0 of 1,390 non-empty cases fell below nominal,
    with minima of exactly 0.5000 / 0.8008 / 0.9512.

    This is the real test. Against one realisation of the truth a set is either wholly
    contained or it is not, so the guarantee is checked by the **fraction of campaigns**
    whose set is contained, which must be at least ``alpha``.

    Returns ``None`` for an empty set -- vacuously contained, and counting that as a
    success would inflate the measured rate with campaigns that certified nothing.
    """
    if int(mask.sum()) == 0:
        return None
    return bool((truth.reshape(-1)[mask] >= theta).all())


def vorobev_deviation(draws: Tensor, theta: float) -> float:
    """Expected symmetric-difference volume between the random set and its expectation.

    The set-valued analogue of posterior variance, and the natural map-quality scalar to
    report beside Brier and AUC. Zero for a deterministic field.
    """
    p = excursion_probability(draws, theta)
    q = vorobev_expectation(p, draws, theta)
    gamma = draws >= theta
    return float((gamma ^ q.unsqueeze(0)).double().mean())
