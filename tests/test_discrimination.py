"""Tests for the discrimination test — E4's actual measurement."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.discrimination import (
    auc_against_threshold,
    discrimination_test,
    instance_bootstrap_ci,
    nearest_neighbour_distance,
    scorer_agreement,
)

N = 512  # the pre-registered candidate count


def _col(a) -> torch.Tensor:
    return torch.as_tensor(np.asarray(a, dtype=np.float64)).reshape(-1, 1)


# --------------------------------------------------------------------------
# Nearest-neighbour distance — the null that must be beaten
# --------------------------------------------------------------------------

def test_distance_is_zero_at_a_measured_point():
    train = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    d = nearest_neighbour_distance(train, train)
    assert torch.allclose(d, torch.zeros(2, 1, dtype=torch.double), atol=1e-12)


def test_distance_grows_as_you_move_away():
    train = torch.zeros(1, 2, dtype=torch.double)
    q = torch.tensor([[0.1, 0.0], [0.5, 0.0], [1.0, 0.0]], dtype=torch.double)
    d = nearest_neighbour_distance(q, train).ravel()
    assert float(d[0]) < float(d[1]) < float(d[2])


def test_nearest_not_centroid():
    """The reason we use nearest-neighbour: a point at the centre of a ring is
    close to the average but far from everything actually measured."""
    ring = torch.tensor(
        [[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]], dtype=torch.double
    )
    centre = torch.zeros(1, 2, dtype=torch.double)
    nn = float(nearest_neighbour_distance(centre, ring))
    centroid_dist = float(torch.norm(centre - ring.mean(0)))
    assert nn == pytest.approx(1.0, abs=1e-12)
    assert centroid_dist == pytest.approx(0.0, abs=1e-12)
    assert nn > centroid_dist


def test_distance_shape_and_validation():
    train = torch.zeros(3, 2, dtype=torch.double)
    assert nearest_neighbour_distance(torch.zeros(5, 2, dtype=torch.double), train).shape == (5, 1)
    with pytest.raises(ValueError, match="factors"):
        nearest_neighbour_distance(torch.zeros(5, 3, dtype=torch.double), train)
    with pytest.raises(ValueError, match="empty"):
        nearest_neighbour_distance(torch.zeros(5, 2, dtype=torch.double), torch.zeros(0, 2, dtype=torch.double))


# --------------------------------------------------------------------------
# The headroom check — reported before any result
# --------------------------------------------------------------------------

def test_identical_scorers_have_no_headroom():
    rng = np.random.default_rng(0)
    s = rng.normal(size=N)
    ag = scorer_agreement({"a": s, "b": s.copy(), "c": s * 2.0})
    assert ag.max_offdiagonal == pytest.approx(1.0, abs=1e-9)
    assert ag.has_headroom is False
    assert "NO HEADROOM" in ag.summary()


def test_independent_scorers_have_headroom():
    rng = np.random.default_rng(0)
    ag = scorer_agreement(
        {"a": rng.normal(size=N), "b": rng.normal(size=N), "c": rng.normal(size=N)}
    )
    assert ag.max_offdiagonal < 0.5
    assert ag.has_headroom is True
    assert "headroom present" in ag.summary()


def test_agreement_matrix_is_symmetric_with_unit_diagonal():
    rng = np.random.default_rng(1)
    ag = scorer_agreement({"a": rng.normal(size=N), "b": rng.normal(size=N)})
    np.testing.assert_allclose(np.diag(ag.matrix), 1.0)
    np.testing.assert_allclose(ag.matrix, ag.matrix.T)


def test_needs_two_scorers():
    with pytest.raises(ValueError, match="at least two"):
        scorer_agreement({"a": np.zeros(10)})


# --------------------------------------------------------------------------
# AUC
# --------------------------------------------------------------------------

def test_perfect_scorer_scores_one():
    err = np.linspace(0, 1, 100)
    assert auc_against_threshold(err.copy(), err, tau_quantile=0.8) == pytest.approx(1.0)


def test_inverted_scorer_scores_zero():
    err = np.linspace(0, 1, 100)
    assert auc_against_threshold(-err, err, tau_quantile=0.8) == pytest.approx(0.0)


def test_useless_scorer_scores_about_a_half():
    rng = np.random.default_rng(0)
    err = rng.random(4000)
    assert auc_against_threshold(rng.random(4000), err, tau_quantile=0.8) == pytest.approx(0.5, abs=0.05)


def test_threshold_is_a_within_instance_quantile():
    """Scale-free by construction: multiplying every error by 1000 changes
    nothing, which is what makes instances comparable."""
    rng = np.random.default_rng(2)
    score, err = rng.random(500), rng.random(500)
    a = auc_against_threshold(score, err, tau_quantile=0.8)
    b = auc_against_threshold(score, err * 1000.0, tau_quantile=0.8)
    assert a == pytest.approx(b)


def test_auc_handles_ties():
    err = np.linspace(0, 1, 100)
    assert 0.0 <= auc_against_threshold(np.ones(100), err, tau_quantile=0.8) <= 1.0


def test_auc_rejects_bad_quantile():
    with pytest.raises(ValueError, match="tau_quantile"):
        auc_against_threshold(np.zeros(10), np.zeros(10), tau_quantile=1.5)


# --------------------------------------------------------------------------
# The test as a whole
# --------------------------------------------------------------------------

def _scenario(seed=0, gp_beats_distance=True):
    """Errors driven by distance; the GP score optionally sharper than distance."""
    rng = np.random.default_rng(seed)
    dist = rng.random(N)
    err = dist**2 + rng.normal(0, 0.02, N)
    err = np.abs(err)
    gp = err + rng.normal(0, 0.02, N) if gp_beats_distance else rng.random(N)
    pi = dist + rng.normal(0, 0.3, N)
    return _col(gp), _col(pi), _col(dist), _col(err)


def test_returns_all_three_scorers():
    res = discrimination_test(*_scenario())
    assert set(res.spearman) == {
        "gp_predictive_sd", "second_order_pi_width", "nearest_neighbour_distance"
    }
    assert set(res.auc) == set(res.spearman)
    assert res.n_candidates == N


def test_detects_when_the_model_beats_plain_distance():
    res = discrimination_test(*_scenario(gp_beats_distance=True))
    assert res.beats_the_null()
    assert res.spearman["gp_predictive_sd"] > 0.9


def test_detects_when_the_model_does_not_beat_plain_distance():
    """**The result we must be able to report.** If plain distance does as well,
    the model is an expensive distance calculator and we say so."""
    res = discrimination_test(*_scenario(gp_beats_distance=False))
    assert not res.beats_the_null()


def test_headroom_is_computed_and_available_before_the_result():
    res = discrimination_test(*_scenario())
    assert res.agreement is not None
    assert isinstance(res.agreement.summary(), str)


def test_refuses_too_few_candidates():
    """Spec: 'Not one point per instance — with 10 points the AUC has no
    usable standard error.'"""
    with pytest.raises(ValueError, match="too few"):
        discrimination_test(
            _col(np.zeros(10)), _col(np.zeros(10)), _col(np.zeros(10)), _col(np.zeros(10))
        )


def test_rejects_signed_error():
    gp, pi, dist, err = _scenario()
    with pytest.raises(ValueError, match="absolute error"):
        discrimination_test(gp, pi, dist, -err)


def test_rejects_mismatched_lengths():
    gp, pi, dist, err = _scenario()
    with pytest.raises(ValueError, match="rows"):
        discrimination_test(gp[:-1], pi, dist, err)


def test_uses_the_preregistered_threshold_by_default():
    res = discrimination_test(*_scenario())
    assert res.tau_quantile == 0.80
    assert res.agreement.threshold == 0.95


# --------------------------------------------------------------------------
# Bootstrap — instance level only
# --------------------------------------------------------------------------

def test_bootstrap_brackets_the_mean():
    rng = np.random.default_rng(0)
    vals = rng.normal(0.5, 0.1, 10).tolist()
    point, lo, hi = instance_bootstrap_ci(vals, seed=0)
    assert lo < point < hi
    assert point == pytest.approx(float(np.mean(vals)))


def test_bootstrap_is_reproducible():
    vals = [0.1, 0.4, 0.35, 0.6, 0.2]
    assert instance_bootstrap_ci(vals, seed=1) == instance_bootstrap_ci(vals, seed=1)


def test_bootstrap_narrows_with_more_instances():
    rng = np.random.default_rng(0)
    _, lo_s, hi_s = instance_bootstrap_ci(rng.normal(0.5, 0.1, 5).tolist(), seed=0)
    _, lo_l, hi_l = instance_bootstrap_ci(rng.normal(0.5, 0.1, 200).tolist(), seed=0)
    assert (hi_l - lo_l) < (hi_s - lo_s)


def test_bootstrap_handles_degenerate_input():
    assert all(np.isnan(v) for v in instance_bootstrap_ci([]))
    point, lo, hi = instance_bootstrap_ci([0.3])
    assert point == 0.3 and np.isnan(lo) and np.isnan(hi)


def test_bootstrap_ignores_non_finite_values():
    """NLS convergence failures produce nan; they must not poison the CI."""
    point, lo, hi = instance_bootstrap_ci([0.1, 0.2, np.nan, 0.3, np.inf], seed=0)
    assert point == pytest.approx(0.2)
    assert np.isfinite(lo) and np.isfinite(hi)
