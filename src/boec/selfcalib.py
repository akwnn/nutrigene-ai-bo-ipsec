"""Self-calibration: correct the GP's overconfidence from the campaign's OWN wells.

------------------------------------------------------------------------------
WHY A FAMILY-CALIBRATED RULE CANNOT BE DEPLOYED
------------------------------------------------------------------------------

Volume-conditional calibration of the excursion certificate repairs the guarantee when each
family is calibrated on itself (leave-one-family-out, gamma=0.95: levy 0.8958 -> 0.9730,
rosenbrock 0.8930 -> 0.9968, ackley+hartmann6 0.8284 -> 0.9452 on held-out seeds). But a cap
fitted on a family library needs the family to be known, and a laboratory has **one unknown
landscape**, not fifty draws from a named family. A rule that must be told which family it is
looking at is not a deployable rule.

This module takes the other route: estimate the overconfidence from the campaign's own
leave-one-out residuals. It never consults a family library, so it is family-agnostic **by
construction** rather than by empirical transfer.

------------------------------------------------------------------------------
WHAT IS BEING CORRECTED, AND THE ONE THING THIS CANNOT SEE
------------------------------------------------------------------------------

`results/e3.log` measures the fitted GP's coverage at nominal 0.95 in every registered cell:

    d=6 sigma=0.25   latent 0.8189   predictive 0.9156
    d=8 sigma=0.25   latent 0.7644   predictive 0.9087

and the selection-effect gap is NEGATIVE at three of four cells for the latent column --
coverage is worst exactly where the optimizer chose to look, which is where the certificate
is decided. The certificate is a **latent** claim, so it inherits the left column.

**LOO residuals live in the PREDICTIVE column, not the latent one.** They are computed
against observed `y`, which carries observation noise, and E3 shows predictive coverage
recovering to ~0.90-0.92 while latent sits at 0.76-0.82. So an inflation factor estimated
here is a lower bound on the latent correction needed, not the whole of it. That gap is a
property of the estimator and is stated rather than hidden; it is the reason this module is
registered as one route to a family-general certificate and not as a proof of one.

------------------------------------------------------------------------------
THE CLOSED FORM, AND WHY IT IS NOT AN APPROXIMATION
------------------------------------------------------------------------------

For an exact GP with covariance `K` (noise already included on the diagonal), the
leave-one-out predictive moments follow from the block inverse identity:

    mu_-i  =  y_i - [K^-1 y]_i / [K^-1]_ii
    var_-i =  1 / [K^-1]_ii

This is an identity, not a shortcut -- `test_loo_matches_brute_force_refit_on_a_correlated_
matrix` asserts it against `n` explicit refits. It costs one factorization instead of `n`.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

#: Reject the leave-one-out identity above this condition number. A noise-inclusive
#: covariance on 48 wells sits many orders below it; a noise-free kernel does not.
COND_MAX = 1e10

def conservative_inflation(y: ArrayLike, mu: ArrayLike, sd: ArrayLike) -> float:
    """Return a widening-only self-calibration factor (never below one)."""
    return max(1.0, calibration_inflation(y, mu, sd))


__all__ = ["calibration_inflation", "conservative_inflation", "calibration_tail",
           "loo_residuals", "COND_MAX"]


def loo_residuals(K: ArrayLike, y: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Leave-one-out predictive mean and variance for every training point.

    Args:
        K: ``(n, n)`` the training covariance **including the noise term on the diagonal**.
            Passing a noise-free kernel matrix reports the latent LOO variance instead and
            makes every residual look too large.
        y: ``(n,)`` the observations.

    Returns:
        ``(mu_loo, var_loo)``, each ``(n,)``.

    Raises:
        ValueError: if ``K`` is not square or its size does not match ``y``.
    """
    Km = np.asarray(K, dtype=float)
    yv = np.asarray(y, dtype=float).reshape(-1)
    if Km.ndim != 2 or Km.shape[0] != Km.shape[1]:
        raise ValueError(f"K must be square, got shape {Km.shape}")
    if Km.shape[0] != yv.size:
        raise ValueError(f"K is {Km.shape[0]}x{Km.shape[0]} but y has {yv.size} entries")

    # A noise-FREE kernel matrix on densely sampled inputs is near-singular, and
    # `1 / [K^-1]_ii` computed from it is numerical garbage rather than a LOO variance.
    # That is the exact mistake -- passing the kernel instead of the noise-inclusive
    # covariance -- that would inflate every standardised residual and manufacture a
    # calibration signal out of round-off. Refused loudly, not returned quietly.
    cond = float(np.linalg.cond(Km))
    if not np.isfinite(cond) or cond > COND_MAX:
        raise ValueError(
            f"K is too ill-conditioned for the leave-one-out identity (cond={cond:.3g} "
            f"> {COND_MAX:.0g}). Pass the covariance INCLUDING the noise diagonal, not "
            "the noise-free kernel.")

    Kinv = np.linalg.inv(Km)
    diag = np.diag(Kinv)
    var_loo = 1.0 / diag
    mu_loo = yv - (Kinv @ yv) / diag
    return mu_loo, var_loo


def calibration_inflation(y: ArrayLike, mu: ArrayLike, sd: ArrayLike) -> float:
    """How much the predictive SD must be multiplied by for the residuals to be honest.

    ``sqrt(mean(((y - mu) / sd)**2))``. Exactly 1 when the GP's uncertainty is calibrated,
    above 1 when it is overconfident, below 1 when it is too cautious.

    Standardisation is **pointwise**, before averaging: a large residual at a point that
    already advertised a large SD is not evidence of overconfidence, and averaging the SDs
    first would call the heteroskedastic case miscalibrated when it is not.

    The raw statistic is returned rather than clamped at 1. A conservative caller that only
    ever widens should use ``max(calibration_inflation(...), 1.0)`` and say so at the call
    site, so that the choice to discard the shrinking case is visible rather than buried
    here.

    Raises:
        ValueError: on empty input, mismatched lengths, or a non-positive ``sd``.
    """
    yv = np.asarray(y, dtype=float).reshape(-1)
    mv = np.asarray(mu, dtype=float).reshape(-1)
    sv = np.asarray(sd, dtype=float).reshape(-1)
    if yv.size == 0:
        raise ValueError("no residuals: calibration is undefined without observations")
    if not (yv.size == mv.size == sv.size):
        raise ValueError(f"length mismatch: y={yv.size}, mu={mv.size}, sd={sv.size}")
    if np.any(sv <= 0.0):
        raise ValueError("every predictive sd must be positive")

    z = (yv - mv) / sv
    return float(np.sqrt(np.mean(z ** 2)))


def calibration_tail(y: ArrayLike, mu: ArrayLike, sd: ArrayLike, q: float = 1.0) -> float:
    """The ``q``-quantile of ``|z|``, the worst-case counterpart to
    :func:`calibration_inflation`.

    **Why a tail statistic and not a mean, decided before any KS number existed.** The
    certificate is a *simultaneous* claim -- it fails if **any** point in the region is
    wrong -- so the diagnostic that matches it is worst-case, not average-case. A landscape
    whose structure the kernel cannot capture (ackley's narrow spikes) produces a few badly
    predicted wells while leaving the mean-square residual close to nominal, and
    ``test_calibration_tail_sees_localized_misspecification_that_the_mean_hides`` asserts
    exactly that case: two campaigns with identical ``calibration_inflation`` that this
    statistic separates.

    **Why the default is the MAX and not the 0.90 quantile.** The spec first registered
    ``q = 0.90``; a unit test written before any KS number existed showed that choice cannot
    detect the very case it was chosen for. With 2 badly-predicted wells in 20, the 0.90
    quantile interpolates to 0.47 -- *below* a uniformly-mediocre campaign's 1.5 -- because
    the spikes sit at the 90th percentile boundary. On 48 wells a handful of bad predictions
    is precisely the ackley signature, so ``q`` defaults to 1.0. Amended in
    ``docs/SPADE-SELF-CALIBRATION-SPEC.md`` §2a on the strength of the synthetic test alone,
    **before** any campaign was scored.

    Raises:
        ValueError: on ``q`` outside ``[0, 1]``, or anything
            :func:`calibration_inflation` would reject.
    """
    if not 0.0 <= float(q) <= 1.0:
        raise ValueError(f"q must be a quantile in [0, 1], got {q}")
    yv = np.asarray(y, dtype=float).reshape(-1)
    mv = np.asarray(mu, dtype=float).reshape(-1)
    sv = np.asarray(sd, dtype=float).reshape(-1)
    if yv.size == 0:
        raise ValueError("no residuals: calibration is undefined without observations")
    if not (yv.size == mv.size == sv.size):
        raise ValueError(f"length mismatch: y={yv.size}, mu={mv.size}, sd={sv.size}")
    if np.any(sv <= 0.0):
        raise ValueError("every predictive sd must be positive")
    return float(np.quantile(np.abs((yv - mv) / sv), float(q)))
