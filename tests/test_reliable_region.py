"""Predictive reliable regions and positive-evidence certificate inference."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
from scipy.stats import beta

from boec.reliable_region import (
    ConservativeSetResult,
    clopper_pearson_lower,
    conservative_set_split,
    empirical_set_containment,
    model_reliability_probability,
    reliable_set_draws,
    true_reliability_probability,
)


class _JointGaussianPosterior:
    def __init__(self, mean: torch.Tensor, covariance: torch.Tensor):
        self.mean = mean.reshape(-1, 1)
        self.variance = covariance.diagonal().reshape(-1, 1)
        self._distribution = torch.distributions.MultivariateNormal(mean, covariance)

    def rsample(self, sample_shape: torch.Size = torch.Size()) -> torch.Tensor:
        return self._distribution.rsample(sample_shape).unsqueeze(-1)


class _JointGaussianModel:
    def __init__(
        self,
        mean: torch.Tensor,
        covariance: torch.Tensor,
        *,
        likelihood_noise: float = 0.25,
        outcome_scale: float = 2.0,
    ):
        self._posterior = _JointGaussianPosterior(mean, covariance)
        self.likelihood = SimpleNamespace(
            noise=torch.tensor(likelihood_noise, dtype=torch.double)
        )
        self.outcome_transform = SimpleNamespace(
            stdvs=torch.tensor([[outcome_scale]], dtype=torch.double)
        )

    def eval(self):
        return self

    def posterior(self, X, *, observation_noise=False):
        assert observation_noise is False
        return self._posterior


@pytest.fixture
def grid():
    return torch.linspace(0.0, 1.0, 4, dtype=torch.double).unsqueeze(-1)


@pytest.fixture
def model():
    mean = torch.tensor([0.3, 0.8, 1.3, 1.8], dtype=torch.double)
    covariance = torch.full((4, 4), 0.18, dtype=torch.double)
    covariance.diagonal().fill_(0.25)
    return _JointGaussianModel(mean, covariance)


def test_true_reliability_probability_uses_relative_and_additive_noise():
    f = torch.tensor([0.0, 1.0, 2.0], dtype=torch.double)
    got = true_reliability_probability(
        f, tau=0.5, sigma_rel=0.2, sigma_add=0.1
    )
    sd = torch.sqrt(0.2**2 * f.square() + 0.1**2)
    expected = 1.0 - torch.distributions.Normal(0.0, 1.0).cdf((0.5 - f) / sd)
    assert torch.allclose(got, expected)


def test_model_reliability_probability_includes_latent_and_learned_noise(model, grid):
    got = model_reliability_probability(model, grid, tau=0.9)
    # likelihood noise is standardized: 0.25 * outcome_scale**2 = 1.0.
    total_sd = torch.sqrt(torch.full((4,), 0.25 + 1.0, dtype=torch.double))
    expected = 1.0 - torch.distributions.Normal(0.0, 1.0).cdf(
        (0.9 - model._posterior.mean.flatten()) / total_sd
    )
    assert torch.allclose(got, expected)
    assert got.shape == (4,)


def test_gamma_changes_the_reliable_set_draws(model, grid):
    low = reliable_set_draws(model, grid, tau=0.5, gamma=0.5, n_draws=128, seed=1)
    high = reliable_set_draws(model, grid, tau=0.5, gamma=0.95, n_draws=128, seed=1)
    assert not torch.equal(low, high)
    assert int(high.sum()) <= int(low.sum())


def test_gamma_changes_the_issued_conservative_certificate(model, grid):
    low_draws = reliable_set_draws(
        model, grid, tau=0.5, gamma=0.5, n_draws=128, seed=1
    )
    high_draws = reliable_set_draws(
        model, grid, tau=0.5, gamma=0.95, n_draws=128, seed=1
    )
    low = conservative_set_split(low_draws, alpha=0.75)
    high = conservative_set_split(high_draws, alpha=0.75)
    assert low.volume > high.volume
    assert bool(torch.all(~high.mask | low.mask))


def test_reliable_set_draws_are_joint_boolean_seeded_and_rng_independent(model, grid):
    torch.manual_seed(8)
    first = reliable_set_draws(model, grid, tau=0.5, gamma=0.8, n_draws=128, seed=7)
    torch.manual_seed(999)
    second = reliable_set_draws(model, grid, tau=0.5, gamma=0.8, n_draws=128, seed=7)
    assert first.dtype == torch.bool
    assert first.shape == (128, 4)
    assert torch.equal(first, second)


@pytest.mark.parametrize("gamma", [0.0, 1.0, -0.1, 1.1, float("nan")])
def test_reliable_set_draws_reject_invalid_gamma(model, grid, gamma):
    with pytest.raises(ValueError, match="gamma"):
        reliable_set_draws(model, grid, tau=0.5, gamma=gamma, n_draws=8, seed=1)


@pytest.mark.parametrize("tau", [float("nan"), float("inf"), -float("inf")])
def test_probability_functions_reject_nonfinite_tau(model, grid, tau):
    with pytest.raises(ValueError, match="tau"):
        model_reliability_probability(model, grid, tau=tau)
    with pytest.raises(ValueError, match="tau"):
        true_reliability_probability(
            torch.ones(2, dtype=torch.double), tau, sigma_rel=0.1, sigma_add=0.1
        )


@pytest.mark.parametrize(
    ("sigma_rel", "sigma_add"),
    [(-0.1, 0.1), (0.1, -0.1), (float("nan"), 0.1), (0.0, 0.0)],
)
def test_true_reliability_probability_rejects_invalid_noise(sigma_rel, sigma_add):
    with pytest.raises(ValueError, match="noise|sigma"):
        true_reliability_probability(
            torch.tensor([0.0, 1.0], dtype=torch.double),
            tau=0.5,
            sigma_rel=sigma_rel,
            sigma_add=sigma_add,
        )


@pytest.mark.parametrize("likelihood_noise", [0.0, -0.1, float("nan"), float("inf")])
def test_model_functions_reject_nonpositive_or_nonfinite_learned_noise(
    grid, likelihood_noise
):
    model = _JointGaussianModel(
        torch.ones(4, dtype=torch.double),
        torch.eye(4, dtype=torch.double),
        likelihood_noise=likelihood_noise,
    )
    with pytest.raises(ValueError, match="noise"):
        model_reliability_probability(model, grid, tau=0.5)
    with pytest.raises(ValueError, match="noise"):
        reliable_set_draws(model, grid, tau=0.5, gamma=0.9, n_draws=8, seed=1)


@pytest.mark.parametrize("n_draws", [0, 1, 3, -2, 2.0, True])
def test_reliable_set_draws_reject_invalid_or_odd_draw_counts(model, grid, n_draws):
    with pytest.raises(ValueError, match="n_draws|even"):
        reliable_set_draws(
            model, grid, tau=0.5, gamma=0.9, n_draws=n_draws, seed=1
        )


def test_reliable_set_draws_rejects_bad_posterior_draw_shape(grid):
    class BadPosterior(_JointGaussianPosterior):
        def rsample(self, sample_shape=torch.Size()):
            return torch.zeros(sample_shape[0], 4, 2, dtype=torch.double)

    model = _JointGaussianModel(
        torch.ones(4, dtype=torch.double), torch.eye(4, dtype=torch.double)
    )
    model._posterior = BadPosterior(
        torch.ones(4, dtype=torch.double), torch.eye(4, dtype=torch.double)
    )
    with pytest.raises(ValueError, match="shape"):
        reliable_set_draws(model, grid, tau=0.5, gamma=0.9, n_draws=8, seed=1)


def _split_fixture() -> torch.Tensor:
    selection = torch.tensor(
        [
            [1, 1, 0, 0],
            [1, 1, 0, 0],
            [1, 1, 1, 0],
            [1, 0, 1, 0],
        ],
        dtype=torch.bool,
    )
    evaluation = torch.tensor(
        [
            [1, 1, 0, 0],
            [1, 0, 0, 0],
            [1, 1, 1, 0],
            [0, 1, 0, 0],
        ],
        dtype=torch.bool,
    )
    return torch.cat([selection, evaluation])


def test_conservative_set_split_selects_largest_jointly_contained_quantile():
    result = conservative_set_split(_split_fixture(), alpha=0.75, n_rho=5)
    assert isinstance(result, ConservativeSetResult)
    assert torch.equal(result.mask, torch.tensor([True, True, False, False]))
    assert result.selection_containment == 0.75
    assert result.crossfit_containment == 0.5
    assert result.volume == 0.5
    assert result.selection_draws == result.evaluation_draws == 4


def test_validation_half_cannot_change_selected_set_or_selection_score():
    draws = _split_fixture()
    first = conservative_set_split(draws, alpha=0.75, n_rho=5)
    perturbed = draws.clone()
    perturbed[4:] = ~perturbed[4:]
    second = conservative_set_split(perturbed, alpha=0.75, n_rho=5)
    assert torch.equal(first.mask, second.mask)
    assert first.selection_containment == second.selection_containment
    assert first.crossfit_containment != second.crossfit_containment


def test_crossfit_score_uses_only_frozen_mask_and_validation_half():
    draws = _split_fixture()
    perturbed = draws.clone()
    perturbed[:4] = True
    result = conservative_set_split(perturbed, alpha=0.75, n_rho=5)
    manual = float(draws[4:, result.mask].all(dim=1).double().mean())
    assert result.crossfit_containment == manual


def test_empty_conservative_set_has_no_containment_success():
    draws = torch.zeros(8, 4, dtype=torch.bool)
    result = conservative_set_split(draws, alpha=0.95)
    assert int(result.mask.sum()) == 0
    assert result.selection_containment is None
    assert result.crossfit_containment is None
    assert result.volume == 0.0


@pytest.mark.parametrize(
    "draws",
    [
        torch.zeros(3, 4, dtype=torch.bool),
        torch.zeros(1, 4, dtype=torch.bool),
        torch.zeros(4, dtype=torch.bool),
        torch.zeros(4, 4, dtype=torch.double),
        torch.zeros(4, 0, dtype=torch.bool),
    ],
)
def test_conservative_set_split_rejects_invalid_draw_arrays(draws):
    with pytest.raises(ValueError, match="draw|boolean|shape|grid"):
        conservative_set_split(draws, alpha=0.95)


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.1, float("nan")])
def test_conservative_set_split_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError, match="alpha"):
        conservative_set_split(_split_fixture(), alpha=alpha)


def test_empty_certificate_is_not_an_empirical_containment_success():
    assert empirical_set_containment(
        torch.zeros(4, dtype=torch.bool), torch.ones(4, dtype=torch.bool)
    ) is None


def test_empirical_set_containment_is_a_hard_subset_check():
    truth = torch.tensor([True, True, False, True])
    assert empirical_set_containment(torch.tensor([True, True, False, False]), truth)
    assert empirical_set_containment(torch.tensor([True, False, True, False]), truth) is False


def test_empirical_set_containment_rejects_shape_and_dtype_mismatches():
    with pytest.raises(ValueError, match="shape"):
        empirical_set_containment(torch.ones(3, dtype=torch.bool), torch.ones(4, dtype=torch.bool))
    with pytest.raises(ValueError, match="boolean"):
        empirical_set_containment(torch.ones(3), torch.ones(3, dtype=torch.bool))


def test_clopper_pearson_lower_is_exact_and_one_sided():
    assert clopper_pearson_lower(43, 50, confidence=0.95) == pytest.approx(
        float(beta.ppf(0.05, 43, 8))
    )
    assert clopper_pearson_lower(43, 50, confidence=0.95) < 0.90
    assert clopper_pearson_lower(50, 50, confidence=0.95) == pytest.approx(
        float(beta.ppf(0.05, 50, 1))
    )


def test_clopper_pearson_requires_positive_evidence():
    assert clopper_pearson_lower(0, 0, confidence=0.95) is None
    assert clopper_pearson_lower(0, 50, confidence=0.95) == 0.0


@pytest.mark.parametrize(
    ("successes", "total", "confidence"),
    [(-1, 4, 0.95), (5, 4, 0.95), (1, -1, 0.95), (1.0, 4, 0.95), (1, 4, 0.0), (1, 4, 1.0)],
)
def test_clopper_pearson_rejects_invalid_inputs(successes, total, confidence):
    with pytest.raises(ValueError):
        clopper_pearson_lower(successes, total, confidence)
