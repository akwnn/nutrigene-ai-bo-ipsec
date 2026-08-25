"""Tests for greedy integrated latent-variance reduction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from boec.variance_reduction import greedy_ivr


class _CovarianceModel:
    """Small posterior double exposing exactly the IVR model contract."""

    def __init__(self, covariance: torch.Tensor, *, noise: float = 0.01):
        self._covariance = covariance.double()
        self.likelihood = SimpleNamespace(noise=torch.tensor(noise, dtype=torch.double))
        self.outcome_transform = SimpleNamespace(stdvs=torch.ones(1, dtype=torch.double))

    def eval(self):
        return self

    def posterior(self, X, *, observation_noise=False):
        assert observation_noise is False
        assert X.shape[0] == self._covariance.shape[0]
        return SimpleNamespace(
            mvn=SimpleNamespace(covariance_matrix=self._covariance.clone())
        )


def _points(n: int) -> torch.Tensor:
    return torch.arange(n, dtype=torch.double).unsqueeze(-1)


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


def test_global_ivr_selects_point_with_greatest_reference_reduction():
    cross = torch.tensor([[0.60, 0.20], [0.50, 0.20]], dtype=torch.double)
    covariance = _joint_covariance(cross, torch.eye(2, dtype=torch.double))
    candidates = _points(2)

    selected = greedy_ivr(_CovarianceModel(covariance), candidates, _points(2), q=1)

    assert torch.equal(selected, candidates[[0]])


def test_boundary_weights_change_selected_point():
    cross = torch.tensor([[0.80, 0.20], [0.10, 0.70]], dtype=torch.double)
    covariance = _joint_covariance(cross, torch.eye(2, dtype=torch.double))
    model = _CovarianceModel(covariance)
    candidates = _points(2)

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
    candidates = _points(3)

    selected = greedy_ivr(_CovarianceModel(covariance), candidates, _points(1), q=2)

    assert torch.equal(selected, candidates[[0, 2]])


def test_ivr_batch_is_unique_deterministic_and_ties_use_row_order():
    cross = torch.full((2, 3), 0.25, dtype=torch.double)
    covariance = _joint_covariance(cross, torch.eye(3, dtype=torch.double))
    model = _CovarianceModel(covariance)
    candidates = _points(3)

    first = greedy_ivr(model, candidates, _points(2), q=2)
    second = greedy_ivr(model, candidates, _points(2), q=2)

    assert torch.equal(first, second)
    assert torch.equal(first, candidates[[0, 1]])
    assert torch.unique(first, dim=0).shape[0] == 2


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
            _points(2),
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
