"""Tests for the second-order response surface.

Covers the spec §9 rows:
  * "Polynomial correctness" — recovers known coefficients and prediction
    variance on a synthetic quadratic
  * "Hessian classification" — correct labels on constructed max/min/saddle/ridge
"""

from __future__ import annotations

import numpy as np
import pytest
import torch
from scipy import stats

from boec.rsm import (
    classify_stationary_point,
    fit_second_order,
    second_order_design_matrix,
    second_order_n_terms,
)

torch.manual_seed(0)


def test_term_counts_match_spec():
    # The spec's estimability argument depends on exactly these numbers.
    assert second_order_n_terms(6) == 28
    assert second_order_n_terms(8) == 45


def test_n_subbox_48_leaves_20_residual_df_at_d6():
    # Spec §6: "28 terms at d=6 with 20 residual df at n=48, workable".
    assert 48 - second_order_n_terms(6) == 20
    # And why d=8 is excluded from E4: only 3 residual df.
    assert 48 - second_order_n_terms(8) == 3


def test_design_matrix_column_order_is_stable():
    X = torch.tensor([[2.0, 3.0, 5.0]], dtype=torch.double)
    M = second_order_design_matrix(X)
    # [1, x0, x1, x2, x0^2, x1^2, x2^2, x0x1, x0x2, x1x2]
    expected = np.array([[1, 2, 3, 5, 4, 9, 25, 6, 10, 15]], dtype=np.float64)
    np.testing.assert_allclose(M, expected)


def test_recovers_known_coefficients_exactly_when_noiseless():
    d = 3
    rng = np.random.default_rng(0)
    beta_true = rng.normal(size=second_order_n_terms(d))

    X = torch.from_numpy(rng.uniform(0, 1, size=(60, d)))
    M = second_order_design_matrix(X)
    Y = torch.from_numpy((M @ beta_true).reshape(-1, 1))

    model = fit_second_order(X, Y)
    np.testing.assert_allclose(model.beta, beta_true, atol=1e-9)
    # Perfect fit -> essentially zero residual variance.
    assert model.sigma2 < 1e-18


def test_prediction_interval_matches_the_closed_form():
    """yhat +/- t * sigma * sqrt(1 + x0' (X'X)^-1 x0), computed independently."""
    d = 2
    rng = np.random.default_rng(1)
    X = torch.from_numpy(rng.uniform(0, 1, size=(40, d)))
    M = second_order_design_matrix(X)
    beta_true = rng.normal(size=M.shape[1])
    Y = torch.from_numpy((M @ beta_true + rng.normal(0, 0.1, 40)).reshape(-1, 1))

    model = fit_second_order(X, Y)
    X0 = torch.from_numpy(rng.uniform(0, 1, size=(5, d)))
    mean, lo, hi = model.prediction_interval(X0, alpha=0.05)

    M0 = second_order_design_matrix(X0)
    lev = np.einsum("ij,jk,ik->i", M0, model.XtX_inv, M0)
    t = stats.t.ppf(0.975, model.residual_df)
    half = t * np.sqrt(model.sigma2) * np.sqrt(1.0 + lev)

    np.testing.assert_allclose(mean.numpy().ravel(), M0 @ model.beta, atol=1e-12)
    np.testing.assert_allclose((hi - lo).numpy().ravel(), 2 * half, atol=1e-12)


def test_prediction_interval_includes_the_observation_term():
    """The '1 +' matters: a PI must be wider than a CI on the mean."""
    d = 2
    rng = np.random.default_rng(2)
    X = torch.from_numpy(rng.uniform(0, 1, size=(40, d)))
    M = second_order_design_matrix(X)
    Y = torch.from_numpy((M @ rng.normal(size=M.shape[1])).reshape(-1, 1) + 0.05)

    model = fit_second_order(X, Y)
    X0 = torch.tensor([[0.5, 0.5]], dtype=torch.double)
    width = model.prediction_interval_width(X0).item()

    M0 = second_order_design_matrix(X0)
    lev = float(np.einsum("ij,jk,ik->i", M0, model.XtX_inv, M0)[0])
    t = stats.t.ppf(0.975, model.residual_df)
    ci_width = 2 * t * np.sqrt(model.sigma2) * np.sqrt(lev)
    assert width > ci_width


def test_rank_deficient_design_raises_rather_than_pseudo_inverting():
    d = 6
    # 48 runs but all on a line -> nowhere near full rank for 28 terms.
    t = torch.linspace(0, 1, 48, dtype=torch.double).unsqueeze(-1)
    X = t.repeat(1, d)
    Y = torch.zeros(48, 1, dtype=torch.double)
    with pytest.raises(ValueError, match="rank-deficient"):
        fit_second_order(X, Y)


def test_too_few_runs_raises():
    d = 6
    X = torch.rand(20, d, dtype=torch.double)
    Y = torch.rand(20, 1, dtype=torch.double)
    with pytest.raises(ValueError, match="cannot fit"):
        fit_second_order(X, Y)


def test_Y_shape_contract_enforced():
    X = torch.rand(40, 2, dtype=torch.double)
    with pytest.raises(ValueError, match=r"Y must be \(n, 1\)"):
        fit_second_order(X, torch.rand(40, dtype=torch.double))


# --------------------------------------------------------------------------
# Hessian classification — constructed cases, spec §9.
# --------------------------------------------------------------------------

def _beta_from_quadratic(d, b, c, e=None):
    """Assemble a coefficient vector in design-matrix order."""
    beta = np.zeros(second_order_n_terms(d))
    beta[0] = 0.0
    beta[1 : 1 + d] = b
    beta[1 + d : 1 + 2 * d] = c
    if e is not None:
        beta[1 + 2 * d :] = e
    return beta


def test_classifies_a_maximum():
    # f = -(x0-0.5)^2 - (x1-0.25)^2 -> concave, max at (0.5, 0.25)
    beta = _beta_from_quadratic(2, b=[1.0, 0.5], c=[-1.0, -1.0], e=[0.0])
    sp = classify_stationary_point(beta, 2, torch.tensor([[0.0, 0.0], [1.0, 1.0]]))
    assert sp.kind == "maximum"
    np.testing.assert_allclose(sp.x.numpy(), [0.5, 0.25], atol=1e-12)
    assert sp.inside_box is True


def test_classifies_a_minimum():
    beta = _beta_from_quadratic(2, b=[-1.0, -0.5], c=[1.0, 1.0], e=[0.0])
    sp = classify_stationary_point(beta, 2, torch.tensor([[0.0, 0.0], [1.0, 1.0]]))
    assert sp.kind == "minimum"
    np.testing.assert_allclose(sp.x.numpy(), [0.5, 0.25], atol=1e-12)


def test_classifies_a_saddle():
    beta = _beta_from_quadratic(2, b=[0.0, 0.0], c=[1.0, -1.0], e=[0.0])
    sp = classify_stationary_point(beta, 2)
    assert sp.kind == "saddle"


def test_classifies_a_ridge():
    # Zero curvature in x1 -> a zero eigenvalue -> ridge, not max/min/saddle.
    beta = _beta_from_quadratic(2, b=[1.0, 0.0], c=[-1.0, 0.0], e=[0.0])
    sp = classify_stationary_point(beta, 2)
    assert sp.kind == "ridge"


def test_stationary_point_outside_box_is_flagged():
    # Max at x0 = 5.0, well outside the unit cube — the E4 narrative case.
    beta = _beta_from_quadratic(2, b=[10.0, 1.0], c=[-1.0, -1.0], e=[0.0])
    sp = classify_stationary_point(beta, 2, torch.tensor([[0.0, 0.0], [1.0, 1.0]]))
    assert sp.kind == "maximum"
    assert sp.inside_box is False
    assert sp.x[0].item() > 1.0


def test_hessian_uses_interaction_terms():
    # Pure interaction: f = x0*x1 -> H = [[0,1],[1,0]], eigenvalues -1, +1.
    beta = _beta_from_quadratic(2, b=[0.0, 0.0], c=[0.0, 0.0], e=[1.0])
    sp = classify_stationary_point(beta, 2)
    np.testing.assert_allclose(np.sort(sp.eigenvalues.numpy()), [-1.0, 1.0], atol=1e-12)
