"""Deterministic greedy integrated latent-variance reduction."""

from __future__ import annotations

import torch
from torch import Tensor

from boec.surrogate import outcome_scale

__all__ = ["greedy_ivr"]


def greedy_ivr(
    model,
    candidates: Tensor,
    reference: Tensor,
    q: int,
    *,
    weights: Tensor | None = None,
) -> Tensor:
    """Select a unique batch by integrated posterior variance reduction.

    Scores use latent posterior covariance and the model's learned observation
    noise. After each choice, a rank-one Schur update conditions the remaining
    covariance on that prospective noisy observation before choosing again.
    """
    if candidates.ndim != 2:
        raise ValueError(f"candidates must be (k, d), got {tuple(candidates.shape)}")
    if reference.ndim != 2:
        raise ValueError(f"reference must be (r, d), got {tuple(reference.shape)}")
    if candidates.shape[1] != reference.shape[1]:
        raise ValueError(
            f"candidates have d={candidates.shape[1]}, reference has d={reference.shape[1]}"
        )
    if reference.shape[0] == 0:
        raise ValueError("reference must contain at least one point")
    if isinstance(q, bool) or not isinstance(q, int) or q < 1:
        raise ValueError(f"q must be a positive integer, got {q!r}")
    if q > candidates.shape[0]:
        raise ValueError(
            f"asked for q={q} but candidates has only {candidates.shape[0]} rows"
        )
    if not bool(torch.all(torch.isfinite(candidates))) or not bool(
        torch.all(torch.isfinite(reference))
    ):
        raise ValueError("candidate and reference coordinates must be finite")
    if torch.unique(candidates, dim=0).shape[0] != candidates.shape[0]:
        raise ValueError("candidate rows must be unique")

    n_reference = reference.shape[0]
    if weights is None:
        normalized_weights = torch.ones(
            n_reference,
            dtype=torch.double,
            device=reference.device,
        )
    else:
        normalized_weights = torch.as_tensor(
            weights,
            dtype=torch.double,
            device=reference.device,
        )
        if normalized_weights.ndim != 1 or normalized_weights.shape[0] != n_reference:
            raise ValueError(
                f"weights must be ({n_reference},), got {tuple(normalized_weights.shape)}"
            )
        if not bool(torch.all(torch.isfinite(normalized_weights))):
            raise ValueError("weights must be finite")
        if bool(torch.any(normalized_weights < 0)):
            raise ValueError("weights cannot contain negative values")
        if not bool(torch.any(normalized_weights > 0)):
            raise ValueError("weights cannot be all-zero")
        normalized_weights = normalized_weights / normalized_weights.mean()

    model.eval()
    joint = torch.cat([reference.double(), candidates.double()], dim=0)
    with torch.no_grad():
        posterior = model.posterior(joint, observation_noise=False)
        covariance = posterior.mvn.covariance_matrix.detach().double().clone()
    expected = n_reference + candidates.shape[0]
    if covariance.ndim != 2 or covariance.shape != (expected, expected):
        raise ValueError(
            "greedy_ivr requires a single-output latent covariance matrix of "
            f"shape ({expected}, {expected}); got {tuple(covariance.shape)}"
        )
    if not bool(torch.all(torch.isfinite(covariance))):
        raise RuntimeError("latent posterior covariance contains nonfinite values")

    likelihood_noise = model.likelihood.noise.detach().double().reshape(-1)
    scale = outcome_scale(model).double().reshape(-1)
    if likelihood_noise.numel() != 1 or scale.numel() != 1:
        raise ValueError("greedy_ivr currently requires one learned likelihood noise value")
    observation_noise = likelihood_noise[0] * scale[0].square()
    if not bool(torch.isfinite(observation_noise)) or float(observation_noise) <= 0:
        raise ValueError("learned likelihood noise must be positive and finite")

    reference_cross = covariance[:n_reference, n_reference:]
    candidate_covariance = covariance[n_reference:, n_reference:]
    remaining = torch.arange(candidates.shape[0], device=candidates.device)
    selected: list[int] = []

    for _ in range(q):
        denominators = torch.diagonal(candidate_covariance) + observation_noise
        if not bool(torch.all(torch.isfinite(denominators))) or bool(
            torch.any(denominators <= 0)
        ):
            raise RuntimeError("IVR conditional variances must be positive and finite")
        scores = (
            normalized_weights[:, None] * reference_cross.square()
        ).sum(dim=0) / denominators
        if not bool(torch.all(torch.isfinite(scores))):
            raise RuntimeError("IVR scores contain nonfinite values")

        local_index = int(torch.argmax(scores).item())
        selected.append(int(remaining[local_index].item()))
        if len(selected) == q:
            break

        keep = torch.ones(remaining.shape[0], dtype=torch.bool, device=remaining.device)
        keep[local_index] = False
        denominator = denominators[local_index]
        selected_reference_cross = reference_cross[:, local_index].clone()
        selected_candidate_cross = candidate_covariance[local_index, keep].clone()
        kept_to_selected = candidate_covariance[keep, local_index].clone()

        reference_cross = (
            reference_cross[:, keep]
            - selected_reference_cross[:, None]
            * selected_candidate_cross[None, :]
            / denominator
        )
        candidate_covariance = (
            candidate_covariance[keep][:, keep]
            - kept_to_selected[:, None]
            * selected_candidate_cross[None, :]
            / denominator
        )
        candidate_covariance = (
            candidate_covariance + candidate_covariance.transpose(-1, -2)
        ) / 2
        remaining = remaining[keep]

    return candidates[selected].clone()
