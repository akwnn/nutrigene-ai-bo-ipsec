"""SPADE's design threshold must be attainable on the landscape it is run on.

`multiround_design` fixed `theta = tau_frac * mu_max` once, before the loop, and every
runner passed `mu_max = float(getattr(orc, "mu_max", 1.0))`. No evaluator defines
`mu_max`, so that fallback made `theta = 0.80` on every family. Four families have a true
max of 0.92-0.999 so 0.80 is attainable; **ackley's max is 0.4102, so SPADE was targeting
a level set that does not exist** -- and ackley is SPADE's only regret loss
(+0.0652, p=0.004, docs/SPADE-ACKLEY-THETA-SPEC.md sec 1).

`mu_max=None` selects the threshold from the observed incumbent instead, per round.
"""
from __future__ import annotations

import torch

from boec.multiround import resolve_theta


def test_explicit_mu_max_is_unchanged():
    """The committed behaviour must be bit-identical, or LC and TAU stop reproducing."""
    Y = torch.tensor([[0.1], [0.4], [0.2]], dtype=torch.double)
    assert resolve_theta(mu_max=1.0, Y=Y, tau_frac=0.80) == 0.80
    assert resolve_theta(mu_max=0.5, Y=Y, tau_frac=0.80) == 0.40


def test_adaptive_theta_tracks_the_observed_incumbent():
    Y = torch.tensor([[0.1], [0.4102], [0.2]], dtype=torch.double)
    got = resolve_theta(mu_max=None, Y=Y, tau_frac=0.80)
    assert abs(got - 0.80 * 0.4102) < 1e-12


def test_adaptive_theta_is_always_attainable():
    """The bug in one line: a threshold above the best value ever seen is unreachable."""
    for best in (0.4102, 0.9211, 0.05):
        Y = torch.tensor([[0.0], [best]], dtype=torch.double)
        theta = resolve_theta(mu_max=None, Y=Y, tau_frac=0.80)
        assert theta <= best, f"theta {theta} exceeds the observed max {best}"


def test_adaptive_theta_rises_as_better_points_arrive():
    """Per-round recomputation is the point: round k must use rounds 1..k-1."""
    early = resolve_theta(mu_max=None, Y=torch.tensor([[0.10]], dtype=torch.double),
                          tau_frac=0.80)
    late = resolve_theta(mu_max=None,
                         Y=torch.tensor([[0.10], [0.41]], dtype=torch.double),
                         tau_frac=0.80)
    assert late > early


def test_ackley_fixed_theta_was_unreachable_but_adaptive_is_not():
    """Regression pinning the exact defect: ackley's true max is 0.4102."""
    ACKLEY_TRUE_MAX = 0.4102
    Y = torch.tensor([[0.0], [0.31]], dtype=torch.double)   # best ackley typically finds
    assert 0.80 * 1.0 > ACKLEY_TRUE_MAX          # the bug: 0.80 > 0.4102
    assert resolve_theta(mu_max=None, Y=Y, tau_frac=0.80) <= ACKLEY_TRUE_MAX


# ---------------------------------------------------------------------------
# theta must be able to BE the certification threshold.
#
# The acquisition targeted `tau_frac * mu_max` = 0.80 while the certificate was computed
# for {f >= tau}. Measured mismatch at p=0.30: ackley tau=0.0587 (theta 13.6x too high),
# hartmann6 tau=0.0774 (10.3x). SPADE was aiming at a contour unrelated to the region it
# certifies. tau is known to a practitioner -- it is their spec ("CD31+ >= 33.2%").
# ---------------------------------------------------------------------------


def test_explicit_theta_overrides_everything():
    Y = torch.tensor([[0.1], [0.9]], dtype=torch.double)
    assert resolve_theta(mu_max=1.0, Y=Y, tau_frac=0.80, theta=0.0587) == 0.0587
    assert resolve_theta(mu_max=None, Y=Y, tau_frac=0.80, theta=0.0587) == 0.0587


def test_theta_none_preserves_both_committed_paths():
    """Passing no theta must leave the two existing behaviours bit-identical."""
    Y = torch.tensor([[0.1], [0.4102]], dtype=torch.double)
    assert resolve_theta(mu_max=1.0, Y=Y, tau_frac=0.80, theta=None) == 0.80
    assert abs(resolve_theta(mu_max=None, Y=Y, tau_frac=0.80, theta=None)
               - 0.80 * 0.4102) < 1e-12


def test_targeting_the_certification_threshold_is_reachable_on_ackley():
    """The repair, pinned: theta=tau is far below the 0.80 the code used."""
    ACKLEY_TAU_P30 = 0.0587
    Y = torch.tensor([[0.0], [0.31]], dtype=torch.double)
    assert resolve_theta(mu_max=1.0, Y=Y, tau_frac=0.80) == 0.80   # the old target
    assert resolve_theta(mu_max=1.0, Y=Y, tau_frac=0.80,
                         theta=ACKLEY_TAU_P30) == ACKLEY_TAU_P30   # the repair
