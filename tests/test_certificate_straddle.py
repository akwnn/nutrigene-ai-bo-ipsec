"""Certificate-targeted acquisition: aim at the contour the CERTIFICATE's frontier sits on.

Bryan's straddle targets `mean = theta` -- the p=0.5 contour. That is the right target for
MAP loss, whose symmetric-difference error is defined at exactly that contour, and it is
measured to be so: this session found targeted plate 2 barely moves map error (+0.0029 against
a SESOI of 0.02, a well-powered null at MDE 0.0057).

The certificate's frontier is somewhere else. `conservative_estimate` returns the largest
Vorob'ev quantile `{x : p(x) >= rho_alpha}` whose joint containment reaches `alpha`, and for a
joint claim `rho_alpha` sits far above 0.5. In response units that contour is

    mean(x) - z_rho * sd(x) = theta,     z_rho = Phi^-1(rho)

so at rho=0.5 it IS Bryan's straddle (z=0), and at rho=0.95 it is the LCB contour, deeper
inside the acceptable region. `certificate_straddle` is the one-parameter generalisation, and
the existing rule is its rho=0.5 special case rather than a competitor to it.

Motivation, measured this session: targeted plate 2 beats random plate 2 on certificate truth
containment by +0.0239 (95% CI [+0.0016, +0.0467], n=149 campaigns, replicated independently at
p=0.0088), while random placement buys nothing at all (+0.0003, p=0.95). The adaptivity is the
value -- and it is currently aimed at the wrong contour.
"""


import pytest
import torch

from boec.lse import straddle_score
from boec.certstraddle import certificate_straddle, rho_contour_offset


def test_at_rho_one_half_it_is_exactly_bryans_straddle():
    """The generalisation must REDUCE to prior art, not merely resemble it."""
    mean = torch.tensor([0.1, 0.5, 0.9, 1.3], dtype=torch.double)
    sd = torch.tensor([0.2, 0.4, 0.1, 0.3], dtype=torch.double)
    got = certificate_straddle(mean, sd, theta=0.7, rho=0.5)
    want = straddle_score(mean, sd, theta=0.7)
    assert torch.allclose(got, want)


def test_rho_offset_is_the_normal_quantile():
    assert rho_contour_offset(0.5) == pytest.approx(0.0)
    assert rho_contour_offset(0.95) == pytest.approx(1.6448536269514722, rel=1e-9)
    assert rho_contour_offset(0.05) == pytest.approx(-1.6448536269514722, rel=1e-9)


def test_high_rho_targets_a_point_deeper_inside_the_acceptable_region():
    """At rho=0.95 the targeted contour is `mean - 1.645*sd = theta`, so among points with
    equal sd the criterion peaks at a HIGHER mean than Bryan's straddle does."""
    mean = torch.linspace(0.0, 2.0, 201, dtype=torch.double)
    sd = torch.full_like(mean, 0.3)
    theta = 1.0

    peak_half = mean[int(certificate_straddle(mean, sd, theta, rho=0.5).argmax())]
    peak_high = mean[int(certificate_straddle(mean, sd, theta, rho=0.95).argmax())]

    assert peak_half == pytest.approx(theta, abs=0.02)
    assert peak_high > peak_half
    assert peak_high == pytest.approx(theta + 1.6448536269514722 * 0.3, abs=0.02)


def test_target_contour_moves_monotonically_with_rho():
    mean = torch.linspace(0.0, 3.0, 301, dtype=torch.double)
    sd = torch.full_like(mean, 0.4)
    peaks = [float(mean[int(certificate_straddle(mean, sd, 1.0, rho=r).argmax())])
             for r in (0.20, 0.50, 0.80, 0.95, 0.99)]
    assert all(b > a for a, b in zip(peaks, peaks[1:])), peaks


def test_uncertainty_term_can_still_pull_the_pick_off_the_contour():
    """`lse.py` asserts this property for the straddle and calls it deliberate: a
    far-from-contour point with large enough uncertainty must be able to outscore a
    near-contour point that is already well determined (Azzimonti's SUR points are sometimes
    deep in the interior). The generalisation must not quietly become boundary-only."""
    mean = torch.tensor([1.0, 2.5], dtype=torch.double)   # on-contour vs far away
    sd = torch.tensor([0.01, 3.0], dtype=torch.double)    # certain vs very uncertain
    s = certificate_straddle(mean, sd, theta=1.0, rho=0.95)
    assert int(s.argmax()) == 1


def test_rejects_a_rho_outside_the_open_unit_interval():
    mean = torch.zeros(3, dtype=torch.double)
    sd = torch.ones(3, dtype=torch.double)
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            certificate_straddle(mean, sd, theta=0.5, rho=bad)


def test_rejects_negative_sd():
    with pytest.raises(ValueError):
        certificate_straddle(torch.zeros(2, dtype=torch.double),
                             torch.tensor([1.0, -1.0], dtype=torch.double),
                             theta=0.5, rho=0.9)


def test_shape_and_dtype_are_preserved():
    mean = torch.rand(17, dtype=torch.double)
    sd = torch.rand(17, dtype=torch.double) + 0.1
    s = certificate_straddle(mean, sd, theta=0.5, rho=0.9)
    assert s.shape == mean.shape
    assert s.dtype == torch.double
    assert torch.isfinite(s).all()


def test_matches_hand_arithmetic():
    """One point, computed by hand: 1.96*0.5 - |1.2 - 1.6448536*0.5 - 0.7|."""
    mean = torch.tensor([1.2], dtype=torch.double)
    sd = torch.tensor([0.5], dtype=torch.double)
    want = 1.96 * 0.5 - abs(1.2 - 1.6448536269514722 * 0.5 - 0.7)
    assert float(certificate_straddle(mean, sd, 0.7, 0.95)[0]) == pytest.approx(want, rel=1e-9)
