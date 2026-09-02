"""Bagged certification: intersect certified regions across bootstrap refits.

WHY THIS IS DIFFERENT FROM EVERYTHING ELSE TRIED
------------------------------------------------
Every prior attempt tried to DETECT or CORRECT a single GP posterior's overconfidence:
`k_eff` (KR, failed), `kappa_tail` (KS, failed -- and measured to move the WRONG way, lower
for the overconfident arm), the 0/50 scope detector (failed), selection-blind covariance (KW,
running), inflation (KT-B, running). All of them still take the fitted posterior's variance as
the thing to reason about.

Bagging does not. Refit the GP on bootstrap resamples of the wells and INTERSECT the certified
regions. Variation ACROSS fits exposes exactly the model uncertainty a single posterior hides
-- including uncertainty in the fitted lengthscales and noise, which the posterior conditions
on as if they were known. An intersection of sets each claimed conservative is conservative.

No detector, no calibration family, no tuning parameter.
"""

import torch
import pytest

from boec.bagged import bagged_certificate


class _Draws:
    """Deterministic stand-in: k fixed draw matrices, so the intersection is checkable."""

    def __init__(self, mats):
        self.mats = mats
        self.calls = 0

    def __call__(self, b):
        self.calls += 1
        return self.mats[b]


def test_intersection_is_a_subset_of_every_member():
    """The defining property. If it is not a subset of each, it is not an intersection."""
    a = torch.tensor([[2.0, 2.0, 0.0]])          # clears theta at points 0,1
    b = torch.tensor([[2.0, 0.0, 2.0]])          # clears at 0,2
    out = bagged_certificate(_Draws([a, b]), n_bags=2, theta=1.0, alpha=0.5)
    assert out.tolist() == [True, False, False]


def test_a_single_bag_reduces_to_the_ordinary_conservative_estimate():
    """With one bag there is nothing to intersect, so bagging must be a no-op. This is the
    boundary case that makes the method safe to adopt."""
    from boec.vorobev import conservative_estimate
    d = torch.tensor([[2.0, 2.0, 0.0], [2.0, 1.5, 0.0], [2.0, 2.0, 0.5]])
    got = bagged_certificate(_Draws([d]), n_bags=1, theta=1.0, alpha=0.5)
    assert torch.equal(got, conservative_estimate(d, 1.0, 0.5))


def test_more_bags_can_only_shrink_the_region():
    """Monotone in `n_bags` -- an intersection over more sets cannot grow. That monotonicity
    is what makes `n_bags` a legitimate nested calibration parameter."""
    a = torch.tensor([[2.0, 2.0, 2.0]])
    b = torch.tensor([[2.0, 2.0, 0.0]])
    c = torch.tensor([[2.0, 0.0, 0.0]])
    two = bagged_certificate(_Draws([a, b]), n_bags=2, theta=1.0, alpha=0.5)
    three = bagged_certificate(_Draws([a, b, c]), n_bags=3, theta=1.0, alpha=0.5)
    assert bool((three <= two).all())
    assert int(three.sum()) <= int(two.sum())


def test_it_actually_calls_the_refit_once_per_bag():
    """Guards the failure mode this repo has three errata for: a 'bagged' arm that silently
    reuses one fit is the ordinary certificate wearing a different label."""
    d = torch.tensor([[2.0, 2.0, 0.0]])
    src = _Draws([d, d, d, d])
    bagged_certificate(src, n_bags=4, theta=1.0, alpha=0.5)
    assert src.calls == 4


def test_rejects_a_non_positive_bag_count():
    with pytest.raises(ValueError):
        bagged_certificate(_Draws([]), n_bags=0, theta=1.0, alpha=0.5)
