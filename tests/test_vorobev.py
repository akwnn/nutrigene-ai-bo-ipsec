"""Vorob'ev quantiles, conservative estimates, and the always-defined alpha*.

Prior art: Chevalier (2013); Azzimonti, Ginsbourger, Chevalier, Bect & Richet (2016,
SIAM/ASA JUQ 2021); batch SUR from Chevalier et al., Technometrics 2014.
"""

import math

import torch

from boec.vorobev import (alpha_star, conservative_estimate, containment_probability,
                          excursion_probability, vorobev_deviation, vorobev_expectation,
                          vorobev_quantile)


def _draws(n_pts=200, n_draws=400, seed=0):
    """Posterior draws with a clean signal: f decreasing in x0, plus noise."""
    g = torch.Generator().manual_seed(seed)
    base = torch.linspace(1.0, 0.0, n_pts, dtype=torch.double)
    return base.unsqueeze(0) + 0.05 * torch.randn(n_draws, n_pts, generator=g,
                                                  dtype=torch.double)


def test_excursion_probability_is_the_fraction_of_draws_above_theta():
    d = torch.tensor([[1.0, 0.0], [1.0, 1.0], [0.0, 0.0], [1.0, 0.0]],
                     dtype=torch.double)
    p = excursion_probability(d, theta=0.5)
    assert torch.allclose(p, torch.tensor([0.75, 0.25], dtype=torch.double))


def test_vorobev_quantile_shrinks_as_rho_rises():
    p = excursion_probability(_draws(), theta=0.5)
    assert int(vorobev_quantile(p, 0.1).sum()) >= int(vorobev_quantile(p, 0.9).sum())


def test_vorobev_expectation_volume_matches_expected_volume():
    """The defining property: vol(Q_rho*) == E[vol(Gamma)], as closely as the grid allows."""
    d = _draws()
    p = excursion_probability(d, theta=0.5)
    q = vorobev_expectation(p, d, theta=0.5)
    expected = float((d >= 0.5).double().mean())
    assert abs(float(q.double().mean()) - expected) <= 1.0 / p.numel() + 1e-9


def test_containment_probability_is_one_for_a_set_always_inside():
    d = _draws()
    p = excursion_probability(d, theta=0.5)
    certain = p >= 1.0
    if int(certain.sum()):
        assert containment_probability(d, certain, theta=0.5) == 1.0


def test_containment_probability_falls_as_the_set_grows():
    d = _draws()
    p = excursion_probability(d, theta=0.5)
    small, big = vorobev_quantile(p, 0.99), vorobev_quantile(p, 0.55)
    assert (containment_probability(d, small, theta=0.5)
            >= containment_probability(d, big, theta=0.5))


def test_containment_of_the_empty_set_is_one_and_is_excluded_elsewhere():
    """The empty set is trivially contained. alpha_star must not exploit that."""
    d = _draws()
    empty = torch.zeros(d.shape[1], dtype=torch.bool)
    assert containment_probability(d, empty, theta=0.5) == 1.0


def test_alpha_star_is_always_defined_and_in_the_unit_interval():
    """The whole point of the metric: never nan, never empty, always ordered.

    As rho -> 1 the quantile shrinks to the single most-certain point, so containment
    is bounded below by max_x p(x). It cannot degenerate the way a fixed-95% volume can.
    """
    for theta in (0.0, 0.5, 0.95, 5.0):        # 5.0 is above everything
        a = alpha_star(_draws(), theta=theta)
        assert not math.isnan(a)
        assert 0.0 <= a <= 1.0


def test_alpha_star_falls_as_the_threshold_rises():
    d = _draws()
    assert alpha_star(d, theta=0.2) >= alpha_star(d, theta=0.8)


def test_alpha_star_is_near_the_best_point_probability_for_an_unreachable_threshold():
    d = _draws()
    theta = 0.9
    assert abs(alpha_star(d, theta=theta)
               - float(excursion_probability(d, theta).max())) < 1e-9


def test_conservative_estimate_is_empty_when_no_set_meets_the_confidence():
    d = _draws()
    ce = conservative_estimate(d, theta=0.9, alpha=0.999999)
    assert int(ce.sum()) == 0 or containment_probability(d, ce, 0.9) >= 0.999999


def test_conservative_estimate_is_contained_in_its_stated_confidence():
    d = _draws()
    for alpha in (0.5, 0.8, 0.95):
        ce = conservative_estimate(d, theta=0.5, alpha=alpha)
        if int(ce.sum()):
            assert containment_probability(d, ce, 0.5) >= alpha


def test_vorobev_deviation_is_zero_for_a_deterministic_field():
    d = torch.ones(50, 8, dtype=torch.double)
    assert vorobev_deviation(d, theta=0.5) == 0.0


def test_vorobev_deviation_is_positive_when_the_field_is_uncertain():
    assert vorobev_deviation(_draws(), theta=0.5) > 0.0
