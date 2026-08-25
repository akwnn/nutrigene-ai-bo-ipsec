"""Design-space deliverables: probability maps, certified regions, inscribed boxes.

Amendment B2 makes Peterson's D_gamma (posterior PREDICTIVE) the primary object; the
latent map is secondary and the gap between them is itself a result (E3 measured latent
coverage 0.7644 against nominal 0.95 while predictive recovers to ~0.90-0.92).
"""

import math

import torch

from boec.designspace import (brier_and_auc, certified_mask, certified_volume_curve,
                              component_report, connected_components,
                              false_inclusion_rate, inscribed_box, iou,
                              inscribed_box_from_mask, predictive_probability_map,
                              probability_map, tau_max, tau_quantile)
from boec.norms import sobol_grid


class _Linear:
    """mu(x) = 1 - x0, constant sd. Analytic, so the box is checkable by hand."""

    def __init__(self, sd):
        self.sd = sd

    def posterior_mean_and_sd(self, X):
        mean = (1.0 - X[:, 0]).double()
        return mean, torch.full_like(mean, float(self.sd))


# --- the noise floor -------------------------------------------------------------

def test_tau_max_matches_the_closed_form():
    """tau_max = mu_max * (1 - z*sigma_rel).

    z is the EXACT inverse normal CDF (1.6448536...), not the textbook 1.645. The first
    version of this test hardcoded 1.645 and failed against a more accurate module; the
    test was wrong, not the code.
    """
    z = float(torch.distributions.Normal(0.0, 1.0).icdf(torch.tensor(0.95, dtype=torch.double)))
    assert tau_max(gamma=0.95, sigma_rel=0.25) == round(1 - z * 0.25, 10)
    assert abs(tau_max(0.95, 0.25) - 0.589) < 1e-3


def test_tau_max_falls_as_assurance_rises():
    assert tau_max(0.99, 0.25) < tau_max(0.95, 0.25) < tau_max(0.70, 0.25)


def test_tau_max_is_one_at_fifty_percent_assurance():
    """At gamma=0.5 the z-multiplier is 0, so the floor imposes no ceiling."""
    assert tau_max(0.50, 0.25) == 1.0


# --- per-family quantile tau (docs/SPADE-TAU-QUANTILE-SPEC.md) -------------------
#
# Registered fix for FINDINGS-SPADE.md §41's ackley/hartmann6 near-total emptiness:
# a fixed fraction of each family's MAX treats "60% of peak height" as the same
# question on every landscape, but peak sharpness varies enormously (ackley's true
# prevalence at tau_frac=0.60 is 0.0000; rosenbrock's is 0.9560). tau_quantile
# instead asks "the threshold whose TRUE superlevel-set covers fraction p of the
# box", which is comparable by construction across families.

def test_tau_quantile_of_a_uniform_zero_one_distribution_matches_1_minus_p():
    """For f ~ Uniform(0,1) over a dense grid, P(f >= tau) = p means tau = 1-p exactly."""
    torch.manual_seed(0)
    truth = torch.rand(200_000, dtype=torch.double)
    for p in (0.30, 0.10, 0.03, 0.01):
        tau = tau_quantile(truth, p)
        assert abs(tau - (1.0 - p)) < 5e-3


def test_tau_quantile_prevalence_matches_p_on_a_finite_grid():
    """The defining property, checked directly: fraction of truth >= tau equals p
    (up to the grid's discreteness), for any distribution -- not just uniform."""
    torch.manual_seed(1)
    truth = torch.randn(50_000, dtype=torch.double) ** 2  # a skewed, non-uniform shape
    for p in (0.30, 0.10, 0.03, 0.01):
        tau = tau_quantile(truth, p)
        prevalence = float((truth >= tau).double().mean())
        assert abs(prevalence - p) < 5e-3


def test_tau_quantile_is_monotone_decreasing_in_p():
    """Asking for a LARGER true region (bigger p) must give a LOWER threshold."""
    torch.manual_seed(2)
    truth = torch.rand(10_000, dtype=torch.double)
    taus = [tau_quantile(truth, p) for p in (0.30, 0.10, 0.03, 0.01)]
    assert taus == sorted(taus)


def test_tau_quantile_on_ackleys_own_shape_is_not_degenerate():
    """The whole point: ackley's true grid is what made tau_frac*tau_max useless
    (prevalence 0.0000 at tau_frac=0.60, FINDINGS-SPADE.md sec 5 / COVERAGE-MATRIX
    B1). A quantile-based tau must NOT return tau_max's degenerate near-zero value --
    it must return a threshold that actually carves off the requested fraction,
    however small ackley's true peak is."""
    from boec.replay import family_evaluator
    ev = family_evaluator("ackley", 6, 0.25, 0)
    grid = sobol_grid(6, 4096, seed=0)
    truth = ev.truth(grid).reshape(-1).double()
    for p in (0.30, 0.10, 0.03, 0.01):
        tau = tau_quantile(truth, p)
        prevalence = float((truth >= tau).double().mean())
        assert abs(prevalence - p) < 0.02, f"p={p} gave prevalence {prevalence}"


def test_tau_quantile_rejects_p_outside_zero_one():
    import pytest
    truth = torch.rand(100, dtype=torch.double)
    with pytest.raises(ValueError):
        tau_quantile(truth, 0.0)
    with pytest.raises(ValueError):
        tau_quantile(truth, 1.0)
    with pytest.raises(ValueError):
        tau_quantile(truth, 1.5)


# --- the two maps ----------------------------------------------------------------

def test_predictive_map_is_never_more_confident_than_the_latent_map():
    """D_gamma carries sigma^2 as well as s^2, so it must be the more conservative one."""
    grid = sobol_grid(3, 512, seed=0)
    m = _Linear(sd=0.05)
    latent = probability_map(m, grid, tau=0.5)
    pred = predictive_probability_map(m, grid, tau=0.5, sigma=0.25)
    above = latent > 0.5
    assert bool((pred[above] <= latent[above] + 1e-12).all())


def test_predictive_map_accepts_heteroscedastic_sigma():
    """This repo's noise is relative, so sigma varies over the grid. A scalar-only API
    would silently answer a homoscedastic question the campaigns never asked."""
    grid = sobol_grid(3, 256, seed=0)
    m = _Linear(sd=0.05)
    mean, _ = m.posterior_mean_and_sd(grid)
    p = predictive_probability_map(m, grid, tau=0.5, sigma=0.25 * mean)
    assert p.shape == (256,)
    assert bool(((p >= 0) & (p <= 1)).all())


# --- certification ---------------------------------------------------------------

def test_certified_mask_is_empty_when_uncertainty_swamps_the_signal():
    """The degenerate case K6 must report as a COUNT, never as a zero in a mean."""
    grid = sobol_grid(3, 2048, seed=0)
    assert certified_mask(_Linear(sd=1.0), grid, tau=0.9, z=1.96).sum() == 0


def test_certified_mask_grows_as_confidence_is_relaxed():
    grid = sobol_grid(3, 2048, seed=0)
    strict = certified_mask(_Linear(sd=0.05), grid, tau=0.8, z=2.58)
    loose = certified_mask(_Linear(sd=0.05), grid, tau=0.8, z=1.0)
    assert loose.sum() > strict.sum()


def test_certified_volume_curve_is_monotone_in_confidence():
    grid = sobol_grid(3, 2048, seed=0)
    curve = certified_volume_curve(_Linear(sd=0.05), grid, tau=0.8,
                                   z_values=[1.0, 1.28, 1.64, 1.96, 2.58])
    vols = [curve[z] for z in sorted(curve)]
    assert all(a >= b for a, b in zip(vols, vols[1:])), vols


def test_inscribed_box_is_contained_in_the_certified_region():
    grid = sobol_grid(3, 2048, seed=0)
    box, vol = inscribed_box(_Linear(sd=0.05), grid, tau=0.8, z=1.96)
    assert vol > 0.0
    inside = ((grid >= box[0]) & (grid <= box[1])).all(dim=1)
    mask = certified_mask(_Linear(sd=0.05), grid, tau=0.8, z=1.96)
    assert bool((mask | ~inside).all()), "box contains an uncertified grid point"


def test_inscribed_box_returns_zero_volume_when_nothing_certifies():
    grid = sobol_grid(3, 1024, seed=0)
    _, vol = inscribed_box(_Linear(sd=1.0), grid, tau=0.9, z=1.96)
    assert vol == 0.0


def test_inscribed_box_respects_an_inactive_axis():
    """Amendment B3: an axis with no design variation must not be certified (policy a)."""
    grid = sobol_grid(3, 1024, seed=0)
    box, _ = inscribed_box(_Linear(sd=0.05), grid, tau=0.8, z=1.96,
                           active=torch.tensor([True, True, False]))
    assert box[0, 2] == box[1, 2], "inactive axis must have zero width"


# --- scoring ---------------------------------------------------------------------

def test_false_inclusion_rate_counts_certified_points_truly_below_tau():
    mask = torch.tensor([True, True, False])
    truth = torch.tensor([0.95, 0.50, 0.99], dtype=torch.double)
    assert false_inclusion_rate(mask, truth, tau=0.9) == 0.5


def test_false_inclusion_rate_is_nan_for_an_empty_region_not_zero():
    """An empty region has no false inclusions AND no true ones. 0.0 would read as safe."""
    mask = torch.tensor([False, False])
    truth = torch.tensor([0.95, 0.50], dtype=torch.double)
    assert math.isnan(false_inclusion_rate(mask, truth, tau=0.9))


def test_iou_is_one_for_a_perfect_region():
    truth = torch.tensor([0.95, 0.50, 0.99], dtype=torch.double)
    mask = torch.tensor([True, False, True])
    assert iou(mask, truth, tau=0.9) == 1.0


def test_iou_is_nan_when_both_sets_are_empty():
    truth = torch.tensor([0.1, 0.2], dtype=torch.double)
    mask = torch.tensor([False, False])
    assert math.isnan(iou(mask, truth, tau=0.9))


def test_brier_is_zero_for_a_perfect_forecast():
    p = torch.tensor([1.0, 0.0, 1.0], dtype=torch.double)
    truth = torch.tensor([0.95, 0.50, 0.99], dtype=torch.double)
    brier, auc = brier_and_auc(p, truth, tau=0.9)
    assert brier == 0.0
    assert auc == 1.0


def test_auc_is_nan_when_one_class_is_absent_not_half():
    """0.5 would read as 'no skill' when the truth is 'undefined'."""
    p = torch.tensor([0.3, 0.6], dtype=torch.double)
    truth = torch.tensor([0.95, 0.99], dtype=torch.double)   # all above tau
    _, auc = brier_and_auc(p, truth, tau=0.9)
    assert math.isnan(auc)


def test_inscribed_box_from_mask_serves_peterson_not_just_an_lcb():
    """The primary object is D_gamma. A box routine that could only inscribe into an LCB
    region would quietly hold the secondary object as the deliverable."""
    grid = sobol_grid(3, 2048, seed=0)
    m = _Linear(sd=0.05)
    d_gamma = predictive_probability_map(m, grid, tau=0.3, sigma=0.10) >= 0.90
    assert int(d_gamma.sum()) > 0
    box, vol = inscribed_box_from_mask(grid, d_gamma)
    assert vol > 0.0
    inside = ((grid >= box[0]) & (grid <= box[1])).all(dim=1)
    assert bool((d_gamma | ~inside).all()), "box escapes D_gamma"


def test_inscribed_box_from_mask_is_empty_for_an_empty_mask():
    grid = sobol_grid(3, 512, seed=0)
    _, vol = inscribed_box_from_mask(grid, torch.zeros(512, dtype=torch.bool))
    assert vol == 0.0


def test_gp_adapter_chunking_gives_the_same_answer_as_one_shot():
    """Chunking is for runtime, so it must be numerically invisible.

    model.posterior(X) builds the JOINT covariance, so it is quadratic in grid size while
    only marginals are used. Measured here: 0.06s at N=2,000 and 100.6s at N=20,000.
    """
    from boec.designspace import gp_adapter
    from boec.replay import unit_bounds
    from boec.surrogate import build_gp

    torch.manual_seed(0)
    X = torch.rand(16, 3, dtype=torch.double)
    Y = X.sum(dim=1, keepdim=True)
    Yvar = torch.full_like(Y, 0.01)
    model = build_gp(X, Y, Yvar, unit_bounds(3))
    grid = sobol_grid(3, 300, seed=0)

    m_small, s_small = gp_adapter(model, chunk=32).posterior_mean_and_sd(grid)
    m_big, s_big = gp_adapter(model, chunk=10_000).posterior_mean_and_sd(grid)
    assert torch.allclose(m_small, m_big, atol=1e-9)
    assert torch.allclose(s_small, s_big, atol=1e-9)


# --- P3-B2: tau_max omits sigma_add ------------------------------------------------

def test_tau_max_is_unchanged_by_the_p3_b2_amendment():
    """The registered decision is that `tau_max` is NOT fixed. This pins that.

    P3-B2 (`docs/OPEN-QUESTIONS.md`, commit 5c44e6a): correcting `tau_max` for the
    sigma=0.10 cells while the committed sigma=0.25 cells keep the old definition would
    confound the sigma axis with a definition change -- a far worse defect than 8e-4.
    """
    z = float(torch.distributions.Normal(0.0, 1.0)
              .icdf(torch.tensor(0.95, dtype=torch.double)))
    assert tau_max(0.95, 0.25) == round(1.0 - z * 0.25, 10)
    assert tau_max(0.95, 0.10) == round(1.0 - z * 0.10, 10)


def test_tau_max_exact_carries_the_additive_term():
    """`mu_max - z*sqrt((sigma_rel*mu_max)^2 + sigma_add^2)`."""
    from boec.designspace import tau_max_exact

    z = float(torch.distributions.Normal(0.0, 1.0)
              .icdf(torch.tensor(0.95, dtype=torch.double)))
    want = 1.0 - z * math.sqrt(0.25 ** 2 + 0.01 ** 2)
    assert tau_max_exact(0.95, 0.25, 0.01) == round(want, 10)


def test_tau_max_exact_reproduces_the_registered_error_magnitudes():
    """3.288e-04 at sigma_rel=0.25 and 8.204e-04 at 0.10, ratio 2.49 (NOT 10x).

    The repo default is `sigma_add = 0.01` (`boec.torch_oracle`, both oracle classes).
    An earlier audit quoted 7.4e-4 and "10x worse" using 0.015, which is not the default.
    """
    from boec.designspace import tau_max_exact

    err_25 = tau_max(0.95, 0.25) - tau_max_exact(0.95, 0.25, 0.01)
    err_10 = tau_max(0.95, 0.10) - tau_max_exact(0.95, 0.10, 0.01)
    assert abs(err_25 - 3.288e-04) < 1e-7
    assert abs(err_10 - 8.204e-04) < 1e-7
    assert abs(err_10 / err_25 - 2.49) < 5e-3


def test_tau_max_exact_is_never_above_tau_max():
    """The omitted term can only make the ceiling lower; a fix that raised it is wrong."""
    from boec.designspace import tau_max_exact

    for gamma in (0.50, 0.70, 0.80, 0.90, 0.95, 0.99):
        for sigma_rel in (0.25, 0.10):
            assert tau_max_exact(gamma, sigma_rel, 0.01) <= tau_max(gamma, sigma_rel)


def test_tau_max_exact_collapses_to_tau_max_with_no_additive_noise():
    from boec.designspace import tau_max_exact

    for gamma in (0.70, 0.95, 0.99):
        assert tau_max_exact(gamma, 0.25, 0.0) == tau_max(gamma, 0.25)


# ---------------------------------------------------------------------------
# Version C section 4 -- connected-component design spaces.
#
# `D_gamma` is already a mask. A multimodal process genuinely has SEVERAL acceptable
# operating windows and a batch record can name more than one, so a single-box metric
# structurally penalises a method for finding more than one good region -- which is
# precisely what spread designs are better at than clustered ones.
#
# The grid is a SCATTERED Sobol set, not a lattice, so `scipy.ndimage.label` does not
# apply and connectivity has to be defined by a neighbourhood graph. These tests pin
# that definition against the lattice case where the two provably agree.
# ---------------------------------------------------------------------------


def _lattice(side: int, dim: int = 2) -> torch.Tensor:
    """``(side**dim, dim)`` regular lattice on the unit box, C-ordered like numpy."""
    axis = (torch.arange(side, dtype=torch.double) + 0.5) / side
    return torch.cartesian_prod(*([axis] * dim)).reshape(-1, dim)


def test_an_empty_mask_has_no_components():
    X = _lattice(8)
    labels, n = connected_components(torch.zeros(X.shape[0], dtype=torch.bool), X)
    assert n == 0
    assert int(labels.sum()) == 0


def test_points_outside_the_mask_are_labelled_zero():
    X = _lattice(8)
    mask = torch.zeros(X.shape[0], dtype=torch.bool)
    mask[:5] = True
    labels, _ = connected_components(mask, X)
    assert bool((labels[~mask] == 0).all())
    assert bool((labels[mask] > 0).all())


def test_component_sizes_partition_the_mask():
    X = _lattice(10)
    mask = (X[:, 0] < 0.3) | (X[:, 0] > 0.7)
    labels, n = connected_components(mask, X)
    assert n == 2
    assert sum(int((labels == c).sum()) for c in range(1, n + 1)) == int(mask.sum())


def test_two_separated_blobs_are_two_components_one_blob_is_one():
    X = _lattice(12)
    left = (X[:, 0] < 0.25) & (X[:, 1] < 0.25)
    right = (X[:, 0] > 0.75) & (X[:, 1] > 0.75)
    assert connected_components(left | right, X)[1] == 2
    assert connected_components(left, X)[1] == 1


def test_labels_agree_with_scipy_ndimage_on_a_lattice():
    """**The correctness gate.** On a regular lattice with ``k = 2d`` the neighbourhood
    graph is face connectivity, which is what ``scipy.ndimage.label`` uses by default.

    The blobs are separated by more than one lattice spacing on purpose. At the box
    boundary a point's ``2d`` nearest neighbours include a diagonal -- there are fewer
    than ``2d`` face neighbours to find -- so the two definitions can disagree across a
    one-cell gap. They cannot disagree across a two-cell gap, and that is the regime the
    assertion is made in. The docstring of `connected_components` states the same limit.
    """
    from scipy import ndimage

    side = 16
    X = _lattice(side)
    img = torch.zeros(side, side, dtype=torch.bool)
    img[1:5, 1:6] = True
    img[9:14, 8:14] = True
    img[12:15, 2:4] = True
    mask = img.reshape(-1)

    ref, n_ref = ndimage.label(img.numpy())
    labels, n = connected_components(mask, X)
    assert n == n_ref == 3

    # Same partition, up to how the two number their components.
    ours = {frozenset(torch.nonzero(labels == c).reshape(-1).tolist())
            for c in range(1, n + 1)}
    theirs = {frozenset(torch.nonzero(torch.as_tensor(ref.reshape(-1)) == c)
                        .reshape(-1).tolist()) for c in range(1, n_ref + 1)}
    assert ours == theirs


def test_components_are_numbered_largest_first():
    """Stable numbering, so `component_report`'s first row is the dominant window.

    Without it the label of a component depends on grid order, and a per-component table
    could not be compared across campaigns at all.
    """
    X = _lattice(14)
    big = (X[:, 0] < 0.5) & (X[:, 1] < 0.5)
    small = (X[:, 0] > 0.85) & (X[:, 1] > 0.85)
    labels, n = connected_components(big | small, X)
    assert n == 2
    sizes = [int((labels == c).sum()) for c in range(1, n + 1)]
    assert sizes == sorted(sizes, reverse=True)


def _sobol_blobs(half_width: float):
    """Two Chebyshev balls at opposite corners of a 4D Sobol grid."""
    from boec.norms import sobol_grid

    X = sobol_grid(4, 4096, seed=0)
    a = torch.tensor([0.15, 0.15, 0.5, 0.5], dtype=torch.double)
    b = torch.tensor([0.85, 0.85, 0.5, 0.5], dtype=torch.double)
    mask = (((X - a).abs().max(dim=1).values < half_width)
            | ((X - b).abs().max(dim=1).values < half_width))
    return mask, X


def test_a_scattered_sobol_grid_separates_two_genuine_blobs():
    """The case the lattice cannot exercise: irregular spacing, which is the real grid."""
    mask, X = _sobol_blobs(0.18)
    assert int(mask.sum()) > 100, "fixture is too sparse to be a connectivity test"
    assert connected_components(mask, X)[1] == 2


def test_a_region_sparser_than_the_grid_fragments_and_that_is_the_definition():
    """**A limit of the statistic, pinned rather than hidden.**

    Component count is resolution-dependent. At half-width 0.12 each blob holds 15 of
    4,096 points and its within-blob median nearest-neighbour distance is **0.1131**
    against the grid's own **0.0932** -- the "region" is sparser than the grid that is
    supposed to resolve it, so it is not one region at this resolution and reporting it
    as one would be the fiction.

    This matters beyond the metric: Version C section 3.2 offers the component count as a
    regime-detector statistic, so a count driven by grid resolution rather than by the
    landscape would be a detector reading its own grid. Any threshold fitted on it must be
    fitted at the grid the detector will run on.
    """
    sparse, X = _sobol_blobs(0.12)
    dense, _ = _sobol_blobs(0.18)
    assert int(sparse.sum()) < 40
    assert connected_components(sparse, X)[1] > 2
    assert connected_components(dense, X)[1] == 2


def test_component_report_rows_sum_to_the_whole_certified_volume():
    X = _lattice(12)
    left = (X[:, 0] < 0.25) & (X[:, 1] < 0.25)
    right = (X[:, 0] > 0.75) & (X[:, 1] > 0.75)
    mask = left | right
    truth = torch.where(mask, 1.0, 0.0).double()

    rows = component_report(mask, X, truth, tau=0.5)
    assert len(rows) == 2
    assert abs(sum(r["vol"] for r in rows) - float(mask.double().mean())) < 1e-12


def test_component_report_carries_the_single_box_number_alongside():
    """Section 4: report the single-box number always, so the committed comparison stays
    intact and the difference between the two is visible."""
    X = _lattice(12)
    left = (X[:, 0] < 0.25) & (X[:, 1] < 0.25)
    right = (X[:, 0] > 0.75) & (X[:, 1] > 0.75)
    mask = left | right
    truth = torch.where(mask, 1.0, 0.0).double()

    rows = component_report(mask, X, truth, tau=0.5)
    _, whole_box = inscribed_box_from_mask(X, mask, seed_score=truth)
    assert all(r["box_vol_all_components"] == whole_box for r in rows)
    # Each component's own box cannot exceed the box fitted to the union.
    assert all(r["box_vol"] <= whole_box + 1e-12 for r in rows)


def test_component_report_error_volume_is_the_symmetric_difference():
    """Type I read alone ranks silence first -- the repo has already been caught by that
    once. The per-component number is the symmetric difference, same as `error_volumes`."""
    X = _lattice(12)
    mask = (X[:, 0] < 0.25) & (X[:, 1] < 0.25)
    # Truth clears tau on HALF the certified blob, so there is a real type I error.
    truth = torch.where(mask & (X[:, 1] < 0.125), 1.0, 0.0).double()

    (row,) = component_report(mask, X, truth, tau=0.5)
    assert row["fi"] > 0.0
    assert row["total_error_vol"] == row["type_I_vol"] + row["type_II_vol"]


def test_component_report_empirical_containment_is_all_or_nothing():
    """Against one realisation of the truth a set is either wholly inside it or it is
    not -- the same convention `boec.vorobev.empirical_containment` holds."""
    X = _lattice(12)
    left = (X[:, 0] < 0.25) & (X[:, 1] < 0.25)
    right = (X[:, 0] > 0.75) & (X[:, 1] > 0.75)
    # Truth clears tau on the LEFT blob only.
    truth = torch.where(left, 1.0, 0.0).double()

    rows = component_report(left | right, X, truth, tau=0.5)
    contained = [r["empirical_containment"] for r in rows]
    assert sorted(contained) == [False, True]
