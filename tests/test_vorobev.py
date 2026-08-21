"""Vorob'ev quantiles, conservative estimates, and the always-defined alpha*.

Prior art: Chevalier (2013); Azzimonti, Ginsbourger, Chevalier, Bect & Richet (2016,
SIAM/ASA JUQ 2021); batch SUR from Chevalier et al., Technometrics 2014.
"""

import math

import torch

from boec.vorobev import (alpha_star, conservative_estimate,
                          conservative_estimate_split, containment_probability,
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


# --- the circularity fix -----------------------------------------------------------

def test_containment_probability_is_model_internal_not_validation():
    """Documents the defect. `conservative_estimate` SELECTS on containment measured from
    `draws`, so re-measuring containment on the SAME draws cannot fall below alpha. It is
    a tautology and must never be reported as 'the guarantee holds'."""
    d = _draws()
    for alpha in (0.5, 0.8, 0.95):
        ce = conservative_estimate(d, theta=0.5, alpha=alpha)
        if int(ce.sum()):
            assert containment_probability(d, ce, 0.5) >= alpha   # true BY CONSTRUCTION


def test_empirical_containment_is_a_hard_zero_or_one_against_truth():
    """The non-circular check: against one realisation a set is contained, or it is not."""
    import torch
    from boec.vorobev import empirical_containment
    truth = torch.tensor([0.9, 0.8, 0.2], dtype=torch.double)
    assert empirical_containment(torch.tensor([True, True, False]), truth, 0.5) is True
    assert empirical_containment(torch.tensor([True, False, True]), truth, 0.5) is False


def test_empirical_containment_of_an_empty_set_is_none_not_true():
    """An empty set is vacuously contained. Counting it as a success would inflate the
    measured rate with campaigns that certified nothing."""
    import torch
    from boec.vorobev import empirical_containment
    truth = torch.tensor([0.9, 0.2], dtype=torch.double)
    assert empirical_containment(torch.zeros(2, dtype=torch.bool), truth, 0.5) is None


# ---------------------------------------------------------------------------
# Version C section 1.2 -- the split-sample conservative estimate.
#
# `conservative_estimate` takes a MAXIMUM over 64 noisy containment estimates and is
# then evaluated on the same draws it selected on. That is anti-conservative by
# construction. These tests pin the cross-fit that removes it.
# ---------------------------------------------------------------------------


def _tied_draws(n_pts=120, n_draws=1024, seed=0):
    """Draws whose exceedance probabilities are NEARLY TIED, and **jointly correlated**.

    Two properties, both load-bearing:

    * **Near-tied.** The selection bias peaks when candidate quantiles are near-tied,
      because a maximum over 64 of them is then a maximum over 64 estimates of one
      quantity. That is the high-``gamma`` corner where section 14's four failures sit --
      at ``gamma = 0.99, tau_frac = 0.60`` the true set covers 0.99916 of the box.
    * **Correlated.** A per-draw common shift, which is what a GP's joint draw supplies
      and what makes joint containment reachable at all. An earlier version of this
      fixture drew every point independently; joint containment was then the product of
      120 marginals, nothing certified at ``alpha = 0.95``, and the fixture could not
      measure what it exists to measure. Independent draws are not a harder test case,
      they are a degenerate one.
    """
    g = torch.Generator().manual_seed(seed)
    base = torch.linspace(0.55, 0.75, n_pts, dtype=torch.double)
    common = 0.12 * torch.randn(n_draws, 1, generator=g, dtype=torch.double)
    independent = 0.02 * torch.randn(n_draws, n_pts, generator=g, dtype=torch.double)
    return base.unsqueeze(0) + common + independent


def test_split_selects_on_the_first_half_alone():
    """The returned set is exactly what the committed estimator gives the first half.

    Load-bearing: it makes the selection bit-identical to `conservative_estimate` at the
    committed 512 draws, so the cross-fit changes what is REPORTED without changing what
    is SELECTED. A different selection would confound the bias removal with a new set.
    """
    d = _tied_draws()
    mask, _ = conservative_estimate_split(d, theta=0.5, alpha=0.95)
    assert torch.equal(mask, conservative_estimate(d[:512], theta=0.5, alpha=0.95))


def test_split_reports_containment_on_the_second_half_alone():
    d = _tied_draws()
    mask, reported = conservative_estimate_split(d, theta=0.5, alpha=0.95)
    assert reported == containment_probability(d[512:], mask, theta=0.5)


def test_perturbing_the_validation_half_cannot_move_the_selected_set():
    """The half-way property. If it fails, the split leaks and the bias is still in."""
    d = _tied_draws()
    mask_a, _ = conservative_estimate_split(d, theta=0.5, alpha=0.95)
    perturbed = d.clone()
    perturbed[512:] += 1.0
    mask_b, _ = conservative_estimate_split(perturbed, theta=0.5, alpha=0.95)
    assert torch.equal(mask_a, mask_b)


def test_perturbing_the_selection_half_cannot_be_absorbed_by_the_report():
    """And the other half-way property: the report is measured, not re-selected."""
    d = _tied_draws()
    perturbed = d.clone()
    perturbed[:512] += 1.0
    mask, reported = conservative_estimate_split(perturbed, theta=0.5, alpha=0.95)
    assert reported == containment_probability(d[512:], mask, theta=0.5)


def test_an_empty_selection_reports_nan_rather_than_one():
    """`containment_probability` returns 1.0 for the empty set -- vacuously contained.

    Reporting that would put a 1.0 in the column for a campaign that certified NOTHING,
    which is the inflation `empirical_containment` already refuses to commit.
    """
    g = torch.Generator().manual_seed(1)
    d = torch.randn(1024, 40, generator=g, dtype=torch.double)
    mask, reported = conservative_estimate_split(d, theta=50.0, alpha=0.95)
    assert int(mask.sum()) == 0
    assert math.isnan(reported)


def test_an_odd_number_of_draws_raises_rather_than_dropping_one():
    d = _tied_draws(n_draws=1023)
    try:
        conservative_estimate_split(d, theta=0.5, alpha=0.95)
    except ValueError as e:
        assert "even" in str(e).lower()
    else:
        raise AssertionError("an odd draw count must raise, not silently drop a draw")


def test_two_draws_is_the_floor_and_one_raises():
    d = _tied_draws(n_draws=1)
    try:
        conservative_estimate_split(d, theta=0.5, alpha=0.95)
    except ValueError:
        pass
    else:
        raise AssertionError("a single draw cannot be split into two halves")


def test_in_sample_containment_exceeds_out_of_sample_at_high_alpha():
    """**The measurement this function exists for.**

    In-sample containment cannot fall below alpha -- `conservative_estimate` selects on
    it. Out-of-sample can, and on near-tied candidates it does. The gap is the selection
    bias, and it is what section 14's four sub-nominal cells are being re-read against.
    """
    in_sample, out_of_sample = [], []
    for seed in range(40):
        d = _tied_draws(seed=seed)
        mask, reported = conservative_estimate_split(d, theta=0.5, alpha=0.95)
        if int(mask.sum()) == 0:
            continue
        in_sample.append(containment_probability(d[:512], mask, theta=0.5))
        out_of_sample.append(reported)

    assert len(in_sample) >= 30, "fixture certified nothing; it cannot measure the bias"
    assert min(in_sample) >= 0.95, "selection is not meeting alpha in-sample"
    mean_in = sum(in_sample) / len(in_sample)
    mean_out = sum(out_of_sample) / len(out_of_sample)
    assert mean_out < mean_in, (
        f"no measurable selection bias on this fixture: in={mean_in:.4f} "
        f"out={mean_out:.4f} -- either the fixture is not near-tied or the split leaks")
