"""Batch level-set estimation for plate 2. Bryan (2005) straddle; Chevalier (2014) batch."""

import torch

from boec.lse import batch_lse, straddle_score


class _Ramp:
    """mu = 1 - x0, constant sd. The theta contour is a known plane."""

    def __init__(self, sd=0.2):
        self.sd = sd

    def posterior_mean_and_sd(self, Z):
        m = (1.0 - Z[:, 0]).double()
        return m, torch.full_like(m, float(self.sd))


def test_straddle_peaks_at_the_threshold_when_uncertainty_is_equal():
    mean = torch.tensor([0.5, 0.9, 0.1], dtype=torch.double)
    sd = torch.full((3,), 0.1, dtype=torch.double)
    assert int(torch.argmax(straddle_score(mean, sd, theta=0.5))) == 0


def test_straddle_prefers_the_uncertain_point_at_equal_distance():
    mean = torch.tensor([0.6, 0.6], dtype=torch.double)
    sd = torch.tensor([0.05, 0.30], dtype=torch.double)
    assert int(torch.argmax(straddle_score(mean, sd, theta=0.5))) == 1


def test_batch_lse_returns_q_points_of_the_right_shape():
    torch.manual_seed(0)
    X = torch.rand(400, 3, dtype=torch.double)
    assert batch_lse(_Ramp(), X, theta=0.5, q=8, exclude=0.1).shape == (8, 3)


def test_batch_lse_does_not_collapse_onto_one_location():
    """A greedy batch on a smooth score picks q near-identical points unless excluded."""
    torch.manual_seed(0)
    X = torch.rand(600, 3, dtype=torch.double)
    picks = batch_lse(_Ramp(), X, theta=0.5, q=4, exclude=0.15)
    d = torch.cdist(picks, picks) + torch.eye(4, dtype=torch.double) * 9
    assert float(d.min()) >= 0.15


def test_batch_lse_can_place_points_off_the_boundary():
    """Azzimonti's figures put some SUR points in the interior. A boundary-only rule is an
    approximation and must not be hard-coded."""
    torch.manual_seed(0)
    X = torch.rand(600, 2, dtype=torch.double)

    class _Blob:
        def posterior_mean_and_sd(self, Z):
            m = (1.0 - Z[:, 0]).double()
            sd = torch.where(Z[:, 1] > 0.8, 0.9, 0.02).double()
            return m, sd

    picks = batch_lse(_Blob(), X, theta=0.5, q=4, exclude=0.15)
    assert bool((picks[:, 1] > 0.8).any()), "criterion never left the boundary"


def test_batch_lse_returns_fewer_points_rather_than_duplicates_when_exclusion_bites():
    """If exclusion empties the pool, returning duplicates would silently waste wells."""
    torch.manual_seed(0)
    X = torch.rand(30, 2, dtype=torch.double)
    picks = batch_lse(_Ramp(), X, theta=0.5, q=20, exclude=0.9)
    d = torch.cdist(picks, picks) + torch.eye(picks.shape[0], dtype=torch.double) * 9
    assert picks.shape[0] <= 20
    assert float(d.min()) >= 0.9 or picks.shape[0] == 1
