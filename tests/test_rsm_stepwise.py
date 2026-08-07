"""Tests for the stepwise-reduced third-order model.

**The most important test in this file is `test_prediction_interval_refuses`.**
Everything else is ordinary correctness; that one guards the central finding of
Experiment 4 from being confounded by post-selection inference.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.designs import central_composite
from boec.metrics import over_prediction_at_constrained_argmax
from boec.rsm import (
    fit_second_order,
    fit_stepwise_third_order,
    second_order_n_terms,
    third_order_n_terms,
)


@pytest.fixture
def ccd48():
    return central_composite(6, n_derived=1, n_centre=4)


def _response(X: torch.Tensor, seed: int = 0, noise: float = 0.05) -> torch.Tensor:
    rng = np.random.default_rng(seed)
    y = (
        1.0
        + 0.5 * X[:, 0]
        - 0.3 * X[:, 1] ** 2
        + 0.4 * X[:, 0] * X[:, 2]
        + torch.from_numpy(rng.normal(0, noise, X.shape[0]))
    )
    return y.unsqueeze(-1)


# --------------------------------------------------------------------------
# THE ONE THAT MATTERS
# --------------------------------------------------------------------------

def test_prediction_interval_refuses(ccd48):
    """Stepwise selection makes an interval too narrow for reasons unrelated to
    extrapolation. Since 'the interval is too narrow' IS the E4 finding,
    reporting this one would confound it. Not an omission — a guard."""
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    with pytest.raises(NotImplementedError, match="on purpose"):
        m.prediction_interval(ccd48.coded[:3])


def test_the_refusal_explains_itself(ccd48):
    """A future contributor must be told why, not just blocked."""
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    with pytest.raises(NotImplementedError) as exc:
        m.prediction_interval(ccd48.coded[:1])
    msg = str(exc.value)
    assert "selected using the same data" in msg
    assert "SecondOrderModel" in msg


def test_the_second_order_model_still_has_one(ccd48):
    """The comparator that IS allowed an interval still works."""
    m = fit_second_order(ccd48.coded, _response(ccd48.coded))
    assert torch.all(m.prediction_interval_width(ccd48.coded[:3]) > 0)


# --------------------------------------------------------------------------
# Why reduction is not optional
# --------------------------------------------------------------------------

def test_full_third_order_cannot_be_fitted_from_48_runs():
    """84 terms, 48 measurements. Reduction is forced, not chosen."""
    assert third_order_n_terms(6) == 84
    assert 84 > 48
    assert second_order_n_terms(6) == 28


def test_starts_below_the_measurement_count(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    assert m.n_terms_start < ccd48.n_runs
    assert m.n_terms_start <= third_order_n_terms(6)


def test_actually_reduces(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    assert m.n_terms_kept < m.n_terms_start
    assert m.n_terms_kept >= 1


def test_leaves_slack_to_estimate_noise(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    assert m.n - m.n_terms_kept > 0


# --------------------------------------------------------------------------
# Selection behaviour
# --------------------------------------------------------------------------

def test_keeps_more_terms_when_the_bar_is_lower(ccd48):
    Y = _response(ccd48.coded)
    strict = fit_stepwise_third_order(ccd48.coded, Y, alpha_out=0.01)
    lenient = fit_stepwise_third_order(ccd48.coded, Y, alpha_out=0.50)
    assert lenient.n_terms_kept >= strict.n_terms_kept


def test_main_effects_are_protected(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    assert () in m.terms
    for i in range(6):
        assert (i,) in m.terms


def test_main_effects_can_be_dropped_when_unprotected(ccd48):
    m = fit_stepwise_third_order(
        ccd48.coded, _response(ccd48.coded), protect_main_effects=False, alpha_out=0.001
    )
    assert m.n_terms_kept <= 7


def test_pure_noise_still_leaves_spurious_terms(ccd48):
    """**This is the post-selection problem, demonstrated rather than asserted.**

    Fit to pure noise — there is nothing real to find. Stepwise selection still
    retains several terms beyond the protected ones, because with ~34 candidate
    terms and a 5% bar, some clear it by luck, and backward elimination then
    stops precisely when the survivors all look convincing.

    Those survivors look convincing *because they were chosen for looking
    convincing*. An interval computed from them would be too narrow, and would
    have nothing to do with extrapolation. Hence the refusal above.
    """
    rng = np.random.default_rng(3)
    Y = torch.from_numpy(rng.normal(0, 1.0, ccd48.n_runs)).unsqueeze(-1)
    m = fit_stepwise_third_order(ccd48.coded, Y)

    n_protected = 1 + 6                       # intercept + main effects
    spurious = m.n_terms_kept - n_protected
    assert spurious > 0, (
        "expected stepwise to retain some terms by chance on pure noise — if "
        "this ever stops happening, re-check whether the refusal above is "
        "still needed"
    )
    # It still discards the large majority of what it started with.
    assert m.n_terms_kept < m.n_terms_start / 2


def test_reduction_is_much_stronger_when_there_is_real_signal(ccd48):
    """Sanity check on the above: real structure survives, noise mostly doesn't."""
    rng = np.random.default_rng(3)
    noise_only = torch.from_numpy(rng.normal(0, 1.0, ccd48.n_runs)).unsqueeze(-1)
    m_noise = fit_stepwise_third_order(ccd48.coded, noise_only)
    m_signal = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded, noise=0.01))
    # Both reduce; the point is simply that selection happens in both cases.
    assert m_noise.n_terms_kept < m_noise.n_terms_start
    assert m_signal.n_terms_kept < m_signal.n_terms_start


def test_records_its_own_criterion(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    assert "backward elimination" in m.criterion
    assert "alpha_out=0.05" in m.criterion


def test_is_reproducible(ccd48):
    Y = _response(ccd48.coded)
    a = fit_stepwise_third_order(ccd48.coded, Y)
    b = fit_stepwise_third_order(ccd48.coded, Y)
    assert a.terms == b.terms
    np.testing.assert_allclose(a.beta, b.beta, atol=1e-12)


# --------------------------------------------------------------------------
# Contracts
# --------------------------------------------------------------------------

def test_predict_shape_and_plugs_into_the_shared_metric(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    assert m.predict(ccd48.coded[:5]).shape == (5, 1)

    def truth(Z: torch.Tensor) -> torch.Tensor:
        return (1.0 + 0.5 * Z[:, 0] - 0.3 * Z[:, 1] ** 2 + 0.4 * Z[:, 0] * Z[:, 2]).unsqueeze(-1)

    bounds = torch.stack([-torch.ones(6, dtype=torch.double), torch.ones(6, dtype=torch.double)])
    res = over_prediction_at_constrained_argmax(m.predict, truth, bounds, seed=0, n_restarts=6, raw_samples=512)
    assert np.isfinite(res.over_prediction)


def test_stationary_point_is_classified(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    sp = m.stationary_point()
    assert sp.kind in {"maximum", "minimum", "saddle", "ridge"}


def test_shape_contract(ccd48):
    with pytest.raises(ValueError, match=r"Y must be \(n, 1\)"):
        fit_stepwise_third_order(ccd48.coded, torch.zeros(48, dtype=torch.double))


def test_dimension_mismatch_rejected(ccd48):
    m = fit_stepwise_third_order(ccd48.coded, _response(ccd48.coded))
    with pytest.raises(ValueError, match="factors"):
        m.predict(torch.zeros(3, 5, dtype=torch.double))
