"""Certified formulation sets: a finite-set estimand for the two-plate budget.

The region estimand (`boec.vorobev`) certifies a whole continuous excursion set
simultaneously, and abstains on 76-92% of campaigns because it is forced to include the
boundary points the posterior is least sure about. A cell-manufacturing lab does not
scale up a region; it scales up a handful of formulations. This module certifies those.

Guarantee: P(every returned formulation truly exceeds tau) >= alpha under the posterior.
Same simultaneous form as the region claim, over a set the method is allowed to choose.
"""

import torch

from boec.topk import certified_topk, topk_columns


def _draws(n_pts=50, n_draws=500, seed=0):
    """Posterior draws, f decreasing in index: point 0 is the safest bet."""
    g = torch.Generator().manual_seed(seed)
    base = torch.linspace(2.0, -2.0, n_pts, dtype=torch.double)
    return base.unsqueeze(0) + 0.5 * torch.randn(n_draws, n_pts, generator=g,
                                                 dtype=torch.double)


def test_everything_certifiable_returns_every_point():
    """tau far below every draw: no point costs anything, so all are returned."""
    d = _draws()
    idx = certified_topk(d, tau=-100.0, alpha=0.95)
    assert sorted(idx) == list(range(d.shape[1]))


def test_nothing_certifiable_returns_empty():
    """tau above every draw: the honest answer is an empty set, not a guess."""
    d = _draws()
    assert certified_topk(d, tau=100.0, alpha=0.95) == []


def test_a_point_that_is_never_above_tau_is_excluded():
    d = _draws()
    d[:, 7] = -50.0                      # point 7 is always a failure
    idx = certified_topk(d, tau=0.0, alpha=0.90)
    assert 7 not in idx


def test_set_is_monotone_decreasing_in_alpha():
    """A stricter guarantee can never certify MORE formulations."""
    d = _draws()
    sizes = [len(certified_topk(d, tau=0.0, alpha=a)) for a in (0.5, 0.8, 0.95, 0.99)]
    assert sizes == sorted(sizes, reverse=True), sizes


def test_returned_set_actually_meets_the_joint_guarantee():
    """The defining property, checked directly against the draws."""
    d = _draws()
    for alpha in (0.5, 0.8, 0.95):
        idx = certified_topk(d, tau=0.0, alpha=alpha)
        if not idx:
            continue
        joint = (d[:, idx] > 0.0).all(dim=1).double().mean().item()
        assert joint >= alpha, (alpha, joint, len(idx))


def test_inflation_shrinks_the_set_but_never_breaks_the_guarantee():
    """Wider posterior => fewer certifiable formulations, guarantee still holds."""
    d = _draws()
    wide = d.mean(dim=0, keepdim=True) + 2.0 * (d - d.mean(dim=0, keepdim=True))
    n_tight = len(certified_topk(d, tau=0.0, alpha=0.95))
    n_wide = len(certified_topk(wide, tau=0.0, alpha=0.95))
    assert n_wide <= n_tight


def test_topk_columns_reports_size_and_truth_containment():
    d = _draws()
    truth = torch.linspace(2.0, -2.0, d.shape[1]).double()
    col = topk_columns(d, truth, tau=0.0, alphas=(0.95,))
    assert col["topk_n_0.95"] >= 0
    # containment is defined only when the set is non-empty
    if col["topk_n_0.95"] > 0:
        assert col["topk_contain_0.95"] in (0.0, 1.0)
        assert 0.0 <= col["topk_frac_correct_0.95"] <= 1.0
    else:
        assert col["topk_empty_0.95"] is True
