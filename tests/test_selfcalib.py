"""Self-calibration: correct the GP's overconfidence from the campaign's OWN wells.

`results/e3.log` measures the fitted GP's LATENT coverage at nominal 0.95 as 0.8189
(d=6, sigma=0.25) and 0.7644 (d=8, sigma=0.25) -- miscalibrated in every cell, and worse
where the optimizer chose to look. The certificate is a latent-`f` claim computed from those
draws, so it inherits the error exactly (see `src/boec/resolution.py` for the volume law
this produces).

A calibration that references a FAMILY LIBRARY cannot be deployed: a lab has one unknown
landscape, not fifty draws from a known family. This module therefore estimates the
overconfidence from the campaign's own leave-one-out residuals, which is available at run
time on any landscape and never consults a family.

Standard prior art: leave-one-out cross-validation diagnostics for Gaussian process
emulators (Bastos & O'Hagan 2009). The closed-form LOO identity for an exact GP is used so
the estimate costs one Cholesky, not `n` refits.
"""

import numpy as np
import pytest

from boec.selfcalib import calibration_inflation, loo_residuals


# --------------------------------------------------------------------------- inflation

def test_perfectly_calibrated_residuals_give_unit_inflation():
    """Residuals exactly one predictive SD from the mean -> the GP is telling the truth."""
    y = np.array([1.0, -1.0, 1.0, -1.0])
    mu = np.zeros(4)
    sd = np.ones(4)
    assert calibration_inflation(y, mu, sd) == pytest.approx(1.0)


def test_overconfident_gp_gives_inflation_above_one():
    """Residuals twice as large as advertised -> SD must be doubled."""
    y = np.array([2.0, -2.0, 2.0, -2.0])
    assert calibration_inflation(y, np.zeros(4), np.ones(4)) == pytest.approx(2.0)


def test_underconfident_gp_gives_inflation_below_one():
    """Reported honestly rather than clamped -- the caller decides whether to shrink."""
    y = np.array([0.5, -0.5, 0.5, -0.5])
    assert calibration_inflation(y, np.zeros(4), np.ones(4)) == pytest.approx(0.5)


def test_inflation_uses_the_predictive_sd_pointwise_not_an_average():
    """Heteroskedastic case: a large residual at a point that ALREADY had a large SD is not
    evidence of overconfidence. Averaging SDs first would wrongly call this overconfident."""
    y = np.array([10.0, 1.0])
    mu = np.zeros(2)
    sd = np.array([10.0, 1.0])
    assert calibration_inflation(y, mu, sd) == pytest.approx(1.0)


def test_rejects_non_positive_predictive_sd():
    with pytest.raises(ValueError):
        calibration_inflation(np.array([1.0]), np.array([0.0]), np.array([0.0]))


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        calibration_inflation(np.array([1.0, 2.0]), np.zeros(2), np.ones(3))


def test_rejects_empty_input():
    with pytest.raises(ValueError):
        calibration_inflation(np.array([]), np.array([]), np.array([]))


# --------------------------------------------------------------------------- LOO identity

def test_loo_on_independent_observations_returns_the_prior():
    """K = I with no correlation: dropping point i tells you nothing about it, so the LOO
    mean is the prior mean (0) and the LOO variance is the prior variance (1)."""
    K = np.eye(3)
    y = np.array([1.0, 2.0, 3.0])
    mu, var = loo_residuals(K, y)
    assert mu == pytest.approx(np.zeros(3))
    assert var == pytest.approx(np.ones(3))


def test_loo_matches_brute_force_refit_on_a_correlated_matrix():
    """The closed form must equal the definition. This is the whole reason it is safe to
    use -- an identity that is only approximately right would bias every inflation factor."""
    rng = np.random.default_rng(0)
    n = 6
    A = rng.normal(size=(n, n))
    K = A @ A.T + n * np.eye(n)          # symmetric positive definite, well conditioned
    y = rng.normal(size=n)

    mu, var = loo_residuals(K, y)
    for i in range(n):
        idx = [j for j in range(n) if j != i]
        K_oo = K[np.ix_(idx, idx)]
        k_io = K[i, idx]
        mu_bf = k_io @ np.linalg.solve(K_oo, y[idx])
        var_bf = K[i, i] - k_io @ np.linalg.solve(K_oo, k_io)
        assert mu[i] == pytest.approx(mu_bf, rel=1e-8, abs=1e-10)
        assert var[i] == pytest.approx(var_bf, rel=1e-8, abs=1e-10)


def test_loo_rejects_a_non_square_matrix():
    with pytest.raises(ValueError):
        loo_residuals(np.ones((2, 3)), np.ones(2))


def test_loo_rejects_a_length_mismatch():
    with pytest.raises(ValueError):
        loo_residuals(np.eye(3), np.ones(2))
