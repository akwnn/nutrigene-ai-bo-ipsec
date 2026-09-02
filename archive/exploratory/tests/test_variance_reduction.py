"""Tests for greedy integrated latent-variance reduction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from boec.variance_reduction import greedy_ivr


class _CovarianceModel:
    """Small posterior double exposing exactly the IVR model contract."""

    def __init__(
        self,
        covariance: torch.Tensor,
        *,
        noise: float = 0.01,
        max_posterior_rows: int | None = None,
    ):
        self._covariance = covariance.double()
        self._max_posterior_rows = max_posterior_rows
        self.likelihood = SimpleNamespace(noise=torch.tensor(noise, dtype=torch.double))
        self.outcome_transform = SimpleNamespace(stdvs=torch.ones(1, dtype=torch.double))

    def eval(self):
        return self

    def posterior(self, X, *, observation_noise=False):
        assert observation_noise is False
        if (
            self._max_posterior_rows is not None
            and X.shape[0] > self._max_posterior_rows
        ):
            raise RuntimeError("posterior request exceeded the block-memory contract")
        indices = X[:, 0].long()
        covariance = self._covariance.index_select(0, indices).index_select(1, indices)
        return SimpleNamespace(
            mvn=SimpleNamespace(covariance_matrix=covariance.clone())
        )


def _points(n: int, *, offset: int = 0) -> torch.Tensor:
    return torch.arange(offset, offset + n, dtype=torch.double).unsqueeze(-1)


def _joint_covariance(cross: torch.Tensor, candidate_covariance: torch.Tensor) -> torch.Tensor:
    n_reference = cross.shape[0]
    reference_covariance = torch.eye(n_reference, dtype=torch.double) * 2.0
    return torch.cat(
        [
            torch.cat([reference_covariance, cross], dim=1),
            torch.cat([cross.T, candidate_covariance], dim=1),
        ],
        dim=0,
    )


def _dense_reference_indices(
    covariance: torch.Tensor,
    n_reference: int,
    q: int,
    noise: float,
    weights: torch.Tensor,
) -> list[int]:
    reference_cross = covariance[:n_reference, n_reference:].clone()
    candidate_covariance = covariance[n_reference:, n_reference:].clone()
    remaining = torch.arange(candidate_covariance.shape[0])
    normalized = weights / weights.max()
    normalized = normalized / normalized.mean()
    selected = []
    for _ in range(q):
        denominators = torch.diagonal(candidate_covariance) + noise
        scores = (normalized[:, None] * reference_cross.square()).sum(0) / denominators
        local = int(torch.argmax(scores))
        selected.append(int(remaining[local]))
        if len(selected) == q:
            break
        keep = torch.ones(remaining.shape[0], dtype=torch.bool)
        keep[local] = False
        denominator = denominators[local]
        row = candidate_covariance[local, keep].clone()
        column = candidate_covariance[keep, local].clone()
        reference_cross = (
            reference_cross[:, keep]
            - reference_cross[:, local, None] * row[None, :] / denominator
        )
        candidate_covariance = (
            candidate_covariance[keep][:, keep]
            - column[:, None] * row[None, :] / denominator
        )
        candidate_covariance = (
            candidate_covariance + candidate_covariance.transpose(-1, -2)
        ) / 2
        remaining = remaining[keep]
    return selected


def test_global_ivr_selects_point_with_greatest_reference_reduction():
    cross = torch.tensor([[0.60, 0.20], [0.50, 0.20]], dtype=torch.double)
    covariance = _joint_covariance(cross, torch.eye(2, dtype=torch.double))
    candidates = _points(2, offset=2)

    selected = greedy_ivr(_CovarianceModel(covariance), candidates, _points(2), q=1)

    assert torch.equal(selected, candidates[[0]])


def test_boundary_weights_change_selected_point():
    cross = torch.tensor([[0.80, 0.20], [0.10, 0.70]], dtype=torch.double)
    covariance = _joint_covariance(cross, torch.eye(2, dtype=torch.double))
    model = _CovarianceModel(covariance)
    candidates = _points(2, offset=2)

    global_pick = greedy_ivr(model, candidates, _points(2), q=1)
    boundary_pick = greedy_ivr(
        model,
        candidates,
        _points(2),
        q=1,
        weights=torch.tensor([0.05, 1.95], dtype=torch.double),
    )

    assert torch.equal(global_pick, candidates[[0]])
    assert torch.equal(boundary_pick, candidates[[1]])


def test_ivr_batch_uses_rank_one_schur_updates():
    cross = torch.tensor([[0.90, 0.85, 0.50]], dtype=torch.double)
    candidate_covariance = torch.tensor(
        [[1.0, 0.95, 0.0], [0.95, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=torch.double,
    )
    covariance = _joint_covariance(cross, candidate_covariance)
    candidates = _points(3, offset=1)

    selected = greedy_ivr(_CovarianceModel(covariance), candidates, _points(1), q=2)

    assert torch.equal(selected, candidates[[0, 2]])


def test_ivr_batch_is_unique_deterministic_and_ties_use_row_order():
    cross = torch.full((2, 3), 0.25, dtype=torch.double)
    covariance = _joint_covariance(cross, torch.eye(3, dtype=torch.double))
    model = _CovarianceModel(covariance)
    candidates = _points(3, offset=2)

    first = greedy_ivr(model, candidates, _points(2), q=2)
    second = greedy_ivr(model, candidates, _points(2), q=2)

    assert torch.equal(first, second)
    assert torch.equal(first, candidates[[0, 1]])
    assert torch.unique(first, dim=0).shape[0] == 2


def test_finite_huge_weights_normalize_without_overflow_and_stay_deterministic():
    cross = torch.tensor([[0.10, 0.80], [0.10, 0.70]], dtype=torch.double)
    covariance = _joint_covariance(cross, torch.eye(2, dtype=torch.double))
    model = _CovarianceModel(covariance)
    candidates = _points(2, offset=2)
    huge_equal_weights = torch.tensor([1e308, 1e308], dtype=torch.double)

    first = greedy_ivr(
        model, candidates, _points(2), q=1, weights=huge_equal_weights
    )
    second = greedy_ivr(
        model, candidates, _points(2), q=1, weights=huge_equal_weights
    )

    assert torch.equal(first, candidates[[1]])
    assert torch.equal(second, first)


@pytest.mark.parametrize(
    "weights, message",
    [
        (torch.tensor([1.0, -1.0]), "negative"),
        (torch.tensor([0.0, 0.0]), "all-zero"),
        (torch.tensor([1.0, float("nan")]), "finite"),
        (torch.tensor([1.0, float("inf")]), "finite"),
    ],
)
def test_invalid_ivr_weights_refuse(weights, message):
    covariance = _joint_covariance(
        torch.ones(2, 2, dtype=torch.double) * 0.1,
        torch.eye(2, dtype=torch.double),
    )

    with pytest.raises(ValueError, match=message):
        greedy_ivr(
            _CovarianceModel(covariance),
            _points(2, offset=2),
            _points(2),
            q=1,
            weights=weights,
        )


def test_ivr_rejects_duplicate_candidate_rows():
    covariance = _joint_covariance(
        torch.ones(1, 2, dtype=torch.double) * 0.1,
        torch.eye(2, dtype=torch.double),
    )
    duplicate_candidates = torch.zeros(2, 1, dtype=torch.double)

    with pytest.raises(ValueError, match="candidate rows must be unique"):
        greedy_ivr(
            _CovarianceModel(covariance), duplicate_candidates, _points(1), q=1
        )


def test_registered_scale_path_never_materializes_all_candidate_covariances():
    candidate_count = 1_025
    cross = torch.linspace(.9, .1, candidate_count, dtype=torch.double).reshape(1, -1)
    covariance = _joint_covariance(
        cross,
        torch.eye(candidate_count, dtype=torch.double),
    )
    model = _CovarianceModel(covariance, max_posterior_rows=1_025)
    candidates = _points(candidate_count, offset=1)

    selected = greedy_ivr(model, candidates, _points(1), q=2)

    assert torch.equal(selected, candidates[[0, 1]])


@pytest.mark.parametrize("seed", range(5))
def test_blockwise_ivr_matches_independent_dense_schur_reference(seed):
    generator = torch.Generator().manual_seed(seed)
    n_reference, n_candidates, q = 5, 9, 4
    factor = torch.randn(
        n_reference + n_candidates,
        n_reference + n_candidates,
        generator=generator,
        dtype=torch.double,
    )
    covariance = factor @ factor.T / factor.shape[0]
    covariance += torch.eye(covariance.shape[0], dtype=torch.double) * .2
    weights = torch.rand(n_reference, generator=generator, dtype=torch.double) + .1
    noise = .07
    candidates = _points(n_candidates, offset=n_reference)
    expected = _dense_reference_indices(
        covariance,
        n_reference,
        q,
        noise,
        weights,
    )

    selected = greedy_ivr(
        _CovarianceModel(covariance, noise=noise),
        candidates,
        _points(n_reference),
        q=q,
        weights=weights,
    )

    assert torch.equal(selected, candidates[expected])
