"""Tests for experimental designs.

The load-bearing test is `test_e4_design_is_exactly_48_runs`: the whole
Experiment 4 budget arithmetic depends on 32 + 12 + 4 landing on 48, and the
resolution claim is checked from the generators rather than trusted from a
lookup table.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.designs import (
    central_composite,
    defining_relation_words,
    fractional_factorial,
    full_factorial,
    scale_to_box,
    screening_design,
    second_order_rank_ok,
    sub_box_bounds,
)
from boec.rsm import fit_second_order, second_order_n_terms


# --------------------------------------------------------------------------
# The budget arithmetic that E4 rests on
# --------------------------------------------------------------------------

def test_e4_design_is_exactly_48_runs():
    """32 corners + 12 axial + 4 centre = 48. The spec's n_subbox."""
    des = central_composite(6, n_derived=1, n_centre=4, face_centred=True)
    assert des.n_factorial == 32
    assert des.n_axial == 12
    assert des.n_centre == 4
    assert des.n_runs == 48


def test_full_factorial_would_blow_the_budget():
    """Why a fraction is forced, not chosen: 64 corners alone exceeds 48."""
    assert full_factorial(6).shape[0] == 64
    assert 64 > 48


def test_e4_design_supports_a_second_order_fit():
    des = central_composite(6, n_derived=1, n_centre=4)
    assert second_order_rank_ok(des.coded)
    # 28 terms, 48 runs -> 20 residual df, exactly as the spec claims.
    assert des.n_runs - second_order_n_terms(6) == 20


def test_e4_design_actually_fits_a_second_order_model():
    """End to end: the design must survive fit_second_order without complaint."""
    des = central_composite(6, n_derived=1, n_centre=4)
    rng = np.random.default_rng(0)
    Y = torch.from_numpy(rng.normal(size=(des.n_runs, 1)))
    model = fit_second_order(des.coded, Y)
    assert model.residual_df == 20
    # And the prediction interval — the E4 comparator — is computable.
    width = model.prediction_interval_width(des.coded[:3])
    assert torch.all(width > 0)


# --------------------------------------------------------------------------
# Fractional factorials
# --------------------------------------------------------------------------

def test_half_fraction_has_half_the_corners():
    pts, res = fractional_factorial(6, 1)
    assert pts.shape == (32, 6)
    assert res == 6


def test_all_points_are_corners():
    pts, _ = fractional_factorial(6, 1)
    assert set(torch.unique(pts).tolist()) == {-1.0, 1.0}


def test_no_duplicate_runs():
    pts, _ = fractional_factorial(6, 1)
    assert torch.unique(pts, dim=0).shape[0] == 32


def test_resolution_vi_verified_from_the_generator_not_the_table():
    """The shortest word in the defining relation IS the resolution."""
    words = defining_relation_words(6, 1)
    assert len(words) == 1
    assert words[0] == (0, 1, 2, 3, 4, 5)
    assert len(words[0]) == 6  # resolution VI


def test_columns_are_balanced_and_orthogonal():
    """Each factor high as often as low, and no two factors correlated."""
    pts, _ = fractional_factorial(6, 1)
    assert torch.allclose(pts.sum(0), torch.zeros(6, dtype=torch.double))
    gram = pts.T @ pts
    off_diagonal = gram - torch.diag(torch.diag(gram))
    assert torch.allclose(off_diagonal, torch.zeros_like(off_diagonal))


def test_unknown_fraction_raises_rather_than_inventing_a_generator():
    with pytest.raises(ValueError, match="no known minimum-aberration generator"):
        fractional_factorial(6, 3)


def test_n_derived_zero_gives_the_full_factorial():
    pts, res = fractional_factorial(4, 0)
    assert pts.shape == (16, 4)
    assert res == 0


# --------------------------------------------------------------------------
# Face-centred vs rotatable — why the default is what it is
# --------------------------------------------------------------------------

def test_face_centred_axial_points_stay_inside_the_cube():
    des = central_composite(6, n_derived=1, face_centred=True)
    assert des.alpha == 1.0
    assert bool(torch.all(des.coded.abs() <= 1.0 + 1e-12))


def test_rotatable_axial_points_fall_outside_the_sub_box():
    """This is why face-centred is the default for E4."""
    des = central_composite(6, n_derived=1, face_centred=False)
    assert des.alpha == pytest.approx(32 ** 0.25, rel=1e-9)
    assert des.alpha > 2.3
    assert bool(torch.any(des.coded.abs() > 1.0))


def test_centre_points_are_required():
    with pytest.raises(ValueError, match="at least one centre point"):
        central_composite(6, n_centre=0)


def test_centre_points_are_at_the_centre():
    des = central_composite(6, n_derived=1, n_centre=4)
    centres = des.coded[-4:]
    assert torch.allclose(centres, torch.zeros_like(centres))


# --------------------------------------------------------------------------
# Scaling into a real box
# --------------------------------------------------------------------------

def test_scale_maps_minus_one_to_lower_and_plus_one_to_upper():
    coded = torch.tensor([[-1.0, -1.0], [1.0, 1.0], [0.0, 0.0]], dtype=torch.double)
    bounds = torch.tensor([[0.0, 10.0], [2.0, 20.0]], dtype=torch.double)
    out = scale_to_box(coded, bounds)
    assert torch.allclose(out[0], torch.tensor([0.0, 10.0], dtype=torch.double))
    assert torch.allclose(out[1], torch.tensor([2.0, 20.0], dtype=torch.double))
    assert torch.allclose(out[2], torch.tensor([1.0, 15.0], dtype=torch.double))


def test_scale_rejects_inverted_bounds():
    coded = torch.zeros(3, 2, dtype=torch.double)
    with pytest.raises(ValueError, match="upper bound must exceed"):
        scale_to_box(coded, torch.tensor([[1.0, 1.0], [0.0, 0.0]], dtype=torch.double))


def test_scale_rejects_mismatched_dimension():
    with pytest.raises(ValueError, match="factors"):
        scale_to_box(
            torch.zeros(3, 2, dtype=torch.double),
            torch.tensor([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=torch.double),
        )


# --------------------------------------------------------------------------
# The E4 sub-box
# --------------------------------------------------------------------------

def test_sub_box_stops_short_of_the_peak():
    x_star = torch.tensor([0.4, 0.5, 0.3], dtype=torch.double)
    bounds = sub_box_bounds(x_star, kappa=0.6)
    assert torch.allclose(bounds[0], torch.zeros(3, dtype=torch.double))
    assert torch.allclose(bounds[1], 0.6 * x_star)
    # The mechanism: the peak is outside the training region, at every kappa < 1.
    assert bool(torch.all(bounds[1] < x_star))


def test_lower_kappa_means_more_extrapolation():
    x_star = torch.tensor([0.4, 0.5], dtype=torch.double)
    tight = sub_box_bounds(x_star, 0.6)
    loose = sub_box_bounds(x_star, 0.9)
    assert bool(torch.all(tight[1] < loose[1]))


def test_sub_box_is_per_dimension_not_a_fixed_box():
    """Spec §11: 'over-prediction near zero at all kappa -> check x* is being
    used per dimension rather than a fixed box.'"""
    x_star = torch.tensor([0.25, 0.55], dtype=torch.double)
    bounds = sub_box_bounds(x_star, 0.8)
    assert bounds[1][0].item() != pytest.approx(bounds[1][1].item())


def test_sub_box_rejects_bad_kappa():
    x_star = torch.tensor([0.4], dtype=torch.double)
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="kappa must be"):
            sub_box_bounds(x_star, bad)


def test_sub_box_rejects_nonpositive_peak():
    with pytest.raises(ValueError, match="positive"):
        sub_box_bounds(torch.tensor([0.0, 0.4], dtype=torch.double), 0.6)


# --------------------------------------------------------------------------
# Screening designs — A's DoE stage 1
# --------------------------------------------------------------------------

def test_screening_is_much_cheaper_than_a_ccd():
    screen = screening_design(6)
    ccd = central_composite(6, n_derived=1)
    assert screen.n_runs < ccd.n_runs
    assert screen.n_axial == 0


def test_screening_keeps_resolution_iv_or_better():
    """Main effects must stay clean of two-factor interactions."""
    for d in (5, 6, 7, 8):
        des = screening_design(d)
        if des.resolution is not None:
            assert des.resolution >= 4, f"d={d} gave resolution {des.resolution}"


def test_screening_has_centre_points_for_a_noise_estimate():
    des = screening_design(6)
    assert des.n_centre >= 1
    assert torch.allclose(des.coded[-des.n_centre:], torch.zeros(des.n_centre, 6, dtype=torch.double))


# --------------------------------------------------------------------------
# Determinism — A and B must get identical designs
# --------------------------------------------------------------------------

def test_designs_are_deterministic():
    a = central_composite(6, n_derived=1, n_centre=4)
    b = central_composite(6, n_derived=1, n_centre=4)
    assert torch.equal(a.coded, b.coded)


def test_identical_points_for_all_four_models():
    """Spec §9: 'Identical design across models — all four E4 models fit the
    same points.' Guaranteed structurally: there is one design object."""
    des = central_composite(6, n_derived=1, n_centre=4)
    x_star = torch.full((6,), 0.4, dtype=torch.double)
    bounds = sub_box_bounds(x_star, 0.7)
    pts = scale_to_box(des.coded, bounds)
    assert pts.shape == (48, 6)
    assert bool(torch.all(pts >= 0.0))
    assert bool(torch.all(pts <= bounds[1] + 1e-12))


# --------------------------------------------------------------------------
# extended_box_bounds — built for OPEN-QUESTIONS Q12, decides nothing
# --------------------------------------------------------------------------

def test_default_reproduces_todays_behaviour_exactly():
    """**Nothing changes unless someone asks.** The default is the unit cube."""
    from boec.designs import extended_box_bounds

    x_star = torch.tensor([0.4, 0.5, 0.3], dtype=torch.double)
    b = extended_box_bounds(x_star, kappa=0.6)
    assert torch.allclose(b[0], torch.zeros(3, dtype=torch.double))
    assert torch.allclose(b[1], torch.ones(3, dtype=torch.double))


def test_rho_controls_how_far_past_the_corner_we_ask():
    from boec.designs import extended_box_bounds, sub_box_bounds

    x_star = torch.tensor([0.4, 0.5], dtype=torch.double)
    sub = sub_box_bounds(x_star, 0.6)
    for rho in (1.2, 1.5, 2.0):
        b = extended_box_bounds(x_star, 0.6, rho=rho)
        assert torch.allclose(b[1], rho * sub[1])
        # Always strictly outside the training corner — there is something to
        # extrapolate to.
        assert bool(torch.all(b[1] > sub[1]))


def test_larger_rho_asks_about_more_territory():
    from boec.designs import extended_box_bounds

    x_star = torch.tensor([0.4, 0.5], dtype=torch.double)
    near = extended_box_bounds(x_star, 0.6, rho=1.2)
    far = extended_box_bounds(x_star, 0.6, rho=2.0)
    assert bool(torch.all(near[1] < far[1]))


def test_never_leaves_the_unit_cube():
    from boec.designs import extended_box_bounds

    x_star = torch.tensor([0.55, 0.5], dtype=torch.double)
    b = extended_box_bounds(x_star, 0.9, rho=10.0)
    assert bool(torch.all(b[1] <= 1.0 + 1e-12))


def test_rho_below_one_is_refused():
    """It would put the scoring box inside the training corner — no
    extrapolation at all, which is not a regime, it is a mistake."""
    from boec.designs import extended_box_bounds

    with pytest.raises(ValueError, match="rho must be at least 1"):
        extended_box_bounds(torch.tensor([0.4], dtype=torch.double), 0.6, rho=0.8)


def test_rho_one_lands_exactly_on_the_corner_edge():
    from boec.designs import extended_box_bounds, sub_box_bounds

    x_star = torch.tensor([0.4, 0.5], dtype=torch.double)
    assert torch.allclose(
        extended_box_bounds(x_star, 0.6, rho=1.0)[1], sub_box_bounds(x_star, 0.6)[1]
    )
