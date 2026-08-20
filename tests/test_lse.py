"""Batch level-set estimation for plate 2. Bryan (2005) straddle; Chevalier (2014) batch."""

import pytest
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


# ---------------------------------------------------------------------------------
# Amendment E2: the exclusion mechanism, measured at the live operating point.
# ---------------------------------------------------------------------------------

import math

from boec.lse import EXCLUSION_FRACTION, min_pairwise_chebyshev
from boec.norms import sobol_grid
from boec.runner import static_design

#: The live operating point, measured over 50 plate-1 fits (d=6, sigma_rel=0.25, n=40):
#: median fitted ARD lengthscale 0.5982, median exclusion radius ell/4 = 0.1495.
LIVE_DIM, LIVE_Q, LIVE_ELL = 6, 8, 0.60
LIVE_RADIUS = LIVE_ELL * EXCLUSION_FRACTION


def _matern52(r):
    a = math.sqrt(5.0) * r
    return (1 + a + 5 * r ** 2 / 3) * torch.exp(-a)


class _PosteriorLike:
    """A fitted GP's geometry without the fit: Matern 5/2 marginal SD off 40 LHS wells.

    ``sd(x) = sqrt(1 - max_i k(x, D_i)^2)`` is the exact posterior SD of a unit-signal
    noiseless GP, and the mean is a kernel expansion, so this is the shape a real plate-1
    posterior has. Using it instead of ``build_gp`` keeps the test at milliseconds while
    holding dimension, design size, lengthscale and candidate grid at their live values --
    which is the whole point, because the mechanism's behaviour is dimension-dependent.
    """

    def __init__(self, design, seed, ell=LIVE_ELL):
        self.design, self.ell = design, ell
        g = torch.Generator().manual_seed(seed)
        self.w = torch.randn(design.shape[0], generator=g, dtype=torch.double)

    def posterior_mean_and_sd(self, Z):
        k = _matern52(torch.cdist(Z, self.design) / self.ell)
        sd = (1 - k.max(dim=1).values ** 2).clamp_min(1e-12).sqrt()
        return ((k @ self.w) / math.sqrt(self.design.shape[0])).double(), sd.double()


def _live_case(seed):
    """``(model, candidates, theta)`` at the live operating point."""
    bounds = torch.stack([torch.zeros(LIVE_DIM, dtype=torch.double),
                          torch.ones(LIVE_DIM, dtype=torch.double)])
    model = _PosteriorLike(static_design(bounds, "lhs", 40, seed), seed)
    cand = sobol_grid(LIVE_DIM, 4096, seed=seed)
    mean, _ = model.posterior_mean_and_sd(cand)
    return model, cand, float(mean.median())


def _top_q(model, cand, theta, q=LIVE_Q):
    """The batch ``batch_lse`` would return if the exclusion did nothing."""
    mean, sd = model.posterior_mean_and_sd(cand)
    return cand[torch.topk(straddle_score(mean, sd, theta), q).indices]


def test_min_pairwise_chebyshev_is_the_quantity_the_runner_logs():
    P = torch.tensor([[0.0, 0.0], [0.3, 0.9], [0.35, 0.1]], dtype=torch.double)
    # Chebyshev, not Euclidean: the pairs are 0.9, 0.35, 0.8 apart.
    assert min_pairwise_chebyshev(P) == pytest.approx(0.35)
    assert math.isinf(min_pairwise_chebyshev(P[:1]))


def test_exclusion_relocates_wells_at_the_live_operating_point():
    """**Amendment E2's alarm.** E2 concluded the radius never fires, from the median
    minimum pairwise Chebyshev distance of 8 *random* points in 6D (0.320, reproduced
    exactly). That is the wrong reference population: ``batch_lse`` takes a greedy argmax
    of a straddle surface whose high scores cluster on one contour, so its batch is about
    half as spread out. Measured over the 50 live plate-1 fits, the top-8-by-score batch
    violates its own radius in **22 of 50** campaigns and the exclusion relocates a mean
    of **0.56 of 8** wells.

    This test fails if the mechanism goes inert again -- whether by the radius shrinking,
    the masking being removed, or the candidate geometry drifting until the top-q batch
    is already separated. Any of those is a reason to re-read the docstring, and all
    three are silent otherwise.
    """
    binding = 0
    for seed in range(8):
        model, cand, theta = _live_case(seed)
        picks = batch_lse(model, cand, theta, LIVE_Q, exclude=LIVE_RADIUS)
        assert picks.shape == (LIVE_Q, LIVE_DIM)
        assert min_pairwise_chebyshev(picks) >= LIVE_RADIUS, (
            f"seed={seed}: the returned batch violates the radius it was given")
        if min_pairwise_chebyshev(_top_q(model, cand, theta)) < LIVE_RADIUS:
            binding += 1
    assert binding >= 4, (
        f"the exclusion had work to do in only {binding}/8 seeds. Either the mechanism "
        f"stopped operating or the operating point moved; the docstring's measured "
        f"22/50 no longer describes this code.")


def test_exclusion_changes_the_batch_it_returns():
    """Not merely 'the batch is separated' -- the batch is *different* from top-q."""
    model, cand, theta = _live_case(0)
    picks = batch_lse(model, cand, theta, LIVE_Q, exclude=LIVE_RADIUS)
    topq = _top_q(model, cand, theta)
    assert min_pairwise_chebyshev(topq) < LIVE_RADIUS < min_pairwise_chebyshev(picks)
    moved = LIVE_Q - sum(any(torch.equal(p, t) for t in topq) for p in picks)
    assert moved >= 1, "batch_lse returned exactly the top-q batch; exclusion is inert"


def test_a_zero_radius_is_what_inert_looks_like():
    """The counterfactual the docstring describes, asserted rather than argued.

    With no exclusion at all the greedy loop re-selects its own argmax every iteration:
    eight wells at one location, a replicate dressed up as a design. This is why the
    mechanism is not optional, and it is checked so the claim cannot rot.
    """
    model, cand, theta = _live_case(0)
    picks = batch_lse(model, cand, theta, LIVE_Q, exclude=0.0)
    assert min_pairwise_chebyshev(picks) == 0.0
    assert all(torch.equal(p, picks[0]) for p in picks)
