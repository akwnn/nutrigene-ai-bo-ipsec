"""Tests for the shared over-prediction metric.

This is the function Person A imports. If it is wrong, A's DoE confirmation run
and B's E4a are wrong in the same direction and nothing catches it — so the
tests here check against cases with analytically known answers.
"""

from __future__ import annotations

import math

import pytest
import torch

from boec.metrics import (
    OverPrediction,
    constrained_argmax,
    over_prediction_at_constrained_argmax,
)

UNIT_2D = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)


def test_argmax_finds_a_known_interior_optimum():
    # f = -(x0-0.3)^2 - (x1-0.7)^2, max at (0.3, 0.7), value 0.
    def f(X: torch.Tensor) -> torch.Tensor:
        return (-((X[:, 0] - 0.3) ** 2) - (X[:, 1] - 0.7) ** 2).unsqueeze(-1)

    x, y, n_ok = constrained_argmax(f, UNIT_2D, seed=0)
    assert torch.allclose(x, torch.tensor([0.3, 0.7], dtype=torch.double), atol=1e-5)
    assert y == pytest.approx(0.0, abs=1e-9)
    assert n_ok > 0


def test_argmax_respects_the_box_when_the_optimum_is_outside():
    # Monotone increasing -> constrained argmax must sit at the upper corner.
    def f(X: torch.Tensor) -> torch.Tensor:
        return X.sum(-1, keepdim=True)

    x, y, _ = constrained_argmax(f, UNIT_2D, seed=0)
    assert torch.allclose(x, torch.ones(2, dtype=torch.double), atol=1e-8)
    assert y == pytest.approx(2.0, abs=1e-8)


def test_argmax_is_deterministic_given_a_seed():
    """Both people must get the same number from the same inputs."""
    def f(X: torch.Tensor) -> torch.Tensor:
        return (torch.sin(6 * X[:, 0]) * torch.cos(5 * X[:, 1])).unsqueeze(-1)

    a = constrained_argmax(f, UNIT_2D, seed=7)
    b = constrained_argmax(f, UNIT_2D, seed=7)
    assert torch.equal(a[0], b[0])
    assert a[1] == b[1]


def test_over_prediction_is_predicted_minus_true():
    """The headline number, on a case where the answer is arithmetic.

    The 'model' is a plane that peaks at the corner and claims 10 there.
    The 'truth' is flat at 1. So over-prediction = 10 - 1 = 9.
    """
    def predict(X: torch.Tensor) -> torch.Tensor:
        return (10.0 * X.mean(-1)).unsqueeze(-1)

    def truth(X: torch.Tensor) -> torch.Tensor:
        return torch.ones(X.shape[0], 1, dtype=torch.double)

    res = over_prediction_at_constrained_argmax(predict, truth, UNIT_2D, seed=0)
    assert isinstance(res, OverPrediction)
    assert res.y_predicted == pytest.approx(10.0, abs=1e-6)
    assert res.y_true == pytest.approx(1.0, abs=1e-12)
    assert res.over_prediction == pytest.approx(9.0, abs=1e-6)


def test_no_over_prediction_when_the_model_is_the_truth():
    """A model fitted to the truth must not over-predict. Guards sign errors."""
    def f(X: torch.Tensor) -> torch.Tensor:
        return (-((X - 0.4) ** 2).sum(-1)).unsqueeze(-1)

    res = over_prediction_at_constrained_argmax(f, f, UNIT_2D, seed=0)
    assert res.over_prediction == pytest.approx(0.0, abs=1e-9)


def test_under_prediction_gives_a_negative_number():
    def predict(X: torch.Tensor) -> torch.Tensor:
        return torch.zeros(X.shape[0], 1, dtype=torch.double)

    def truth(X: torch.Tensor) -> torch.Tensor:
        return torch.full((X.shape[0], 1), 3.0, dtype=torch.double)

    res = over_prediction_at_constrained_argmax(predict, truth, UNIT_2D, seed=0)
    assert res.over_prediction == pytest.approx(-3.0, abs=1e-9)


def test_extrapolating_polynomial_over_predicts_a_saturating_truth():
    """The E4 mechanism in miniature, on a 1-D case checked by hand.

    Truth saturates at 1. A straight line fitted on [0, 0.3] keeps climbing and
    claims ~2.9 at x=1, where the truth is ~0.99. So over-prediction ~ +1.9.
    """
    def truth(X: torch.Tensor) -> torch.Tensor:
        return (1.0 - torch.exp(-8.0 * X[:, 0])).unsqueeze(-1)

    # Least-squares line through the truth on the sub-box, computed here so the
    # test does not depend on rsm.py.
    xs = torch.linspace(0.0, 0.3, 12, dtype=torch.double).unsqueeze(-1)
    ys = truth(xs)
    A = torch.cat([torch.ones_like(xs), xs], dim=1)
    coef = torch.linalg.lstsq(A, ys).solution.squeeze(-1)

    def predict(X: torch.Tensor) -> torch.Tensor:
        return (coef[0] + coef[1] * X[:, 0]).unsqueeze(-1)

    bounds = torch.tensor([[0.0], [1.0]], dtype=torch.double)
    res = over_prediction_at_constrained_argmax(predict, truth, bounds, seed=0)

    assert res.x_argmax.item() == pytest.approx(1.0, abs=1e-8)
    assert res.over_prediction > 1.5
    assert math.isfinite(res.over_prediction)


def test_predict_must_return_n_by_1():
    def bad(X: torch.Tensor) -> torch.Tensor:
        return X.sum(-1)  # (n,) not (n, 1)

    with pytest.raises(ValueError, match=r"\(n, 1\)"):
        constrained_argmax(bad, UNIT_2D, seed=0)


def test_bounds_shape_enforced():
    def f(X: torch.Tensor) -> torch.Tensor:
        return X.sum(-1, keepdim=True)

    with pytest.raises(ValueError, match=r"bounds must be \(2, d\)"):
        constrained_argmax(f, torch.tensor([0.0, 1.0], dtype=torch.double), seed=0)


def test_rsm_model_plugs_into_the_metric():
    """rsm.SecondOrderModel.predict must satisfy the PredictFn contract."""
    from boec.rsm import fit_second_order

    torch.manual_seed(0)
    X = torch.rand(60, 2, dtype=torch.double) * 0.3
    truth_fn = lambda Z: (1.0 - torch.exp(-6.0 * Z.sum(-1))).unsqueeze(-1)  # noqa: E731
    Y = truth_fn(X)

    model = fit_second_order(X, Y)
    res = over_prediction_at_constrained_argmax(model.predict, truth_fn, UNIT_2D, seed=0)
    # Fitted on [0, 0.3]^2, asked about [0, 1]^2 -> it should overshoot.
    assert res.over_prediction > 0.0


def test_sampled_region_is_the_axis_aligned_box_of_visited_wells():
    from boec.metrics import point_in_region, sampled_region_bounds

    X = torch.tensor([[0.1, 0.8], [0.4, 0.2]], dtype=torch.double)
    region = sampled_region_bounds(X)
    assert torch.allclose(region[0], torch.tensor([0.1, 0.2], dtype=torch.double))
    assert torch.allclose(region[1], torch.tensor([0.4, 0.8], dtype=torch.double))
    assert point_in_region(torch.tensor([0.2, 0.5], dtype=torch.double), region)
    assert not point_in_region(torch.tensor([0.9, 0.5], dtype=torch.double), region)
