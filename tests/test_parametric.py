"""Tests for the practitioner-form comparator."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.metrics import over_prediction_at_constrained_argmax
from boec.parametric import (
    biphasic_response,
    fit_practitioner_parametric,
)


# --------------------------------------------------------------------------
# The response shape itself
# --------------------------------------------------------------------------

def test_curve_peaks_at_exactly_one():
    """Peak normalization: without it, weights would not mean importance."""
    ec50 = np.array([0.2]); ic50 = np.array([0.8]); n = np.array([2.0])
    grid = np.linspace(1e-6, 1.0, 20001).reshape(-1, 1)
    vals = biphasic_response(grid, ec50, ic50, n)
    assert float(vals.max()) == pytest.approx(1.0, abs=1e-4)


def test_peak_sits_at_the_geometric_mean():
    """Closed form: the peak is at sqrt(ec50 * ic50)."""
    ec50 = np.array([0.2]); ic50 = np.array([0.8]); n = np.array([2.0])
    grid = np.linspace(1e-6, 1.0, 40001).reshape(-1, 1)
    vals = biphasic_response(grid, ec50, ic50, n).ravel()
    assert float(grid[int(np.argmax(vals)), 0]) == pytest.approx(np.sqrt(0.2 * 0.8), abs=1e-3)


def test_curve_really_does_rise_then_fall():
    """The 'biphasic' claim, not just asserted."""
    ec50 = np.array([0.2]); ic50 = np.array([0.8]); n = np.array([2.0])
    grid = np.linspace(1e-6, 1.0, 2001).reshape(-1, 1)
    vals = biphasic_response(grid, ec50, ic50, n).ravel()
    peak = int(np.argmax(vals))
    assert 0 < peak < len(vals) - 1
    assert np.all(np.diff(vals[:peak]) > 0)
    assert np.all(np.diff(vals[peak:]) < 0)


def test_curve_is_positive_everywhere():
    ec50 = np.array([0.3, 0.2]); ic50 = np.array([0.9, 1.1]); n = np.array([1.5, 2.5])
    grid = np.random.default_rng(0).uniform(0, 1, size=(500, 2))
    assert np.all(biphasic_response(grid, ec50, ic50, n) > 0)


def test_zero_concentration_gives_zero_response():
    ec50 = np.array([0.3]); ic50 = np.array([0.9]); n = np.array([2.0])
    assert biphasic_response(np.zeros((1, 1)), ec50, ic50, n)[0, 0] == pytest.approx(0.0, abs=1e-8)


# --------------------------------------------------------------------------
# Fitting
# --------------------------------------------------------------------------

def _make_data(d=2, n_obs=90, seed=0, noise=0.0):
    rng = np.random.default_rng(seed)
    ec50 = np.full(d, 0.20)
    ic50 = np.full(d, 0.90)
    n = np.full(d, 2.0)
    w = np.full(d, 1.0 / d)
    X = rng.uniform(0.01, 1.0, size=(n_obs, d))
    y = 0.1 + biphasic_response(X, ec50, ic50, n) @ w
    if noise:
        y = y + rng.normal(0, noise, size=y.shape)
    return (
        torch.from_numpy(X),
        torch.from_numpy(y.reshape(-1, 1)),
        (ec50, ic50, n, w),
    )


def test_recovers_the_shape_from_clean_data():
    X, Y, (ec50, ic50, n, w) = _make_data()
    fit = fit_practitioner_parametric(X, Y, n_restarts=10, seed=1)
    assert fit.converged
    pred = fit.predict(X).numpy().ravel()
    assert float(np.max(np.abs(pred - Y.numpy().ravel()))) < 0.02


def test_fits_acceptably_under_noise():
    X, Y, _ = _make_data(noise=0.02)
    fit = fit_practitioner_parametric(X, Y, n_restarts=10, seed=1)
    assert fit.converged
    resid = fit.predict(X).numpy().ravel() - Y.numpy().ravel()
    assert float(np.sqrt(np.mean(resid**2))) < 0.06


def test_fit_is_reproducible():
    X, Y, _ = _make_data()
    a = fit_practitioner_parametric(X, Y, n_restarts=6, seed=3)
    b = fit_practitioner_parametric(X, Y, n_restarts=6, seed=3)
    assert a.converged and b.converged
    np.testing.assert_allclose(a.ec50, b.ec50, atol=1e-10)
    assert a.residual_sum_squares == pytest.approx(b.residual_sum_squares)


def test_fitted_curve_stays_rise_then_fall():
    """ic50 > ec50 must hold, or the shape is not biphasic at all."""
    X, Y, _ = _make_data()
    fit = fit_practitioner_parametric(X, Y, n_restarts=10, seed=1)
    assert fit.converged
    assert np.all(fit.ic50 > fit.ec50)


# --------------------------------------------------------------------------
# Honest failure — the point of this file's design
# --------------------------------------------------------------------------

def test_too_little_data_is_recorded_not_raised():
    """Failures must be countable, so the failure RATE can be reported."""
    X = torch.rand(5, 3, dtype=torch.double)
    Y = torch.rand(5, 1, dtype=torch.double)
    fit = fit_practitioner_parametric(X, Y)
    assert fit.converged is False
    assert fit.n_restarts_converged == 0
    assert "cannot fit" in fit.message
    assert np.isinf(fit.residual_sum_squares)


def test_a_failed_fit_refuses_to_predict():
    """Silently predicting from a failed fit would poison the comparison."""
    X = torch.rand(5, 3, dtype=torch.double)
    Y = torch.rand(5, 1, dtype=torch.double)
    fit = fit_practitioner_parametric(X, Y)
    with pytest.raises(RuntimeError, match="did not converge"):
        fit.predict(X)


def test_convergence_count_is_reported():
    X, Y, _ = _make_data()
    fit = fit_practitioner_parametric(X, Y, n_restarts=6, seed=1)
    assert fit.converged
    assert 1 <= fit.n_restarts_converged <= 6


# --------------------------------------------------------------------------
# The deliberate handicap
# --------------------------------------------------------------------------

def test_no_interaction_terms_means_it_underfits_interacting_data():
    """The handicap is real and intentional.

    Data built WITH ingredient interactions cannot be fitted perfectly by a
    model that adds ingredients up independently. If this ever passed
    trivially, the comparator would have been handed the answer.
    """
    rng = np.random.default_rng(0)
    d = 2
    ec50 = np.full(d, 0.2); ic50 = np.full(d, 0.9); n = np.full(d, 2.0)
    X = rng.uniform(0.01, 1.0, size=(120, d))
    per = biphasic_response(X, ec50, ic50, n)
    additive = per @ np.full(d, 0.5)
    interacting = additive + 0.8 * per[:, 0] * per[:, 1]     # <- the extra term

    Xt = torch.from_numpy(X)
    fit_add = fit_practitioner_parametric(Xt, torch.from_numpy(additive.reshape(-1, 1)), n_restarts=8, seed=1)
    fit_int = fit_practitioner_parametric(Xt, torch.from_numpy(interacting.reshape(-1, 1)), n_restarts=8, seed=1)
    assert fit_add.converged and fit_int.converged
    assert fit_int.residual_sum_squares > fit_add.residual_sum_squares * 10


# --------------------------------------------------------------------------
# Plugs into the shared measurement
# --------------------------------------------------------------------------

def test_plugs_into_the_over_prediction_metric():
    """All four E4 models must satisfy the same predict contract."""
    X, Y, (ec50, ic50, n, w) = _make_data(d=2, n_obs=90)
    fit = fit_practitioner_parametric(X, Y, n_restarts=8, seed=1)
    assert fit.converged

    def truth(Z: torch.Tensor) -> torch.Tensor:
        vals = 0.1 + biphasic_response(Z.numpy(), ec50, ic50, n) @ w
        return torch.from_numpy(vals.reshape(-1, 1))

    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    res = over_prediction_at_constrained_argmax(fit.predict, truth, bounds, seed=0)
    # Fitted on the full box against the true shape: it should be close.
    assert abs(res.over_prediction) < 0.05


def test_shape_contract_enforced():
    X, _, _ = _make_data()
    with pytest.raises(ValueError, match=r"Y must be \(n, 1\)"):
        fit_practitioner_parametric(X, torch.rand(90, dtype=torch.double))
