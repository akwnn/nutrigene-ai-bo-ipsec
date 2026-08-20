"""Design-space deliverables: probability maps, certified regions, inscribed boxes.

Amendment B2 makes Peterson's D_gamma (posterior PREDICTIVE) the primary object; the
latent map is secondary and the gap between them is itself a result (E3 measured latent
coverage 0.7644 against nominal 0.95 while predictive recovers to ~0.90-0.92).
"""

import math

import torch

from boec.designspace import (brier_and_auc, certified_mask, certified_volume_curve,
                              false_inclusion_rate, inscribed_box, iou,
                              predictive_probability_map, probability_map, tau_max)
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
