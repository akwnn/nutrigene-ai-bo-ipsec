"""Training-only calibration and acquisition helpers for the EC benchmark.

The functions in this module reject the prospective seed range by construction.
They are deliberately small: calibration selects from an explicit, finite set of
candidate settings and only accepts settings whose *per-family* one-sided
containment lower bound clears the registered 90% target.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import torch
from torch import Tensor

from boec.surrogate import predictive

TRAIN_SEEDS = tuple(range(64))
CONTAINMENT_TARGET = 0.90


@dataclass(frozen=True)
class ECTrainingCandidate:
    """One predeclared calibration setting considered on training campaigns."""

    inflation_by_cqa: tuple[float, float, float]
    candidate_density: int

    def __post_init__(self) -> None:
        if len(self.inflation_by_cqa) != 3 or any(
            not math.isfinite(float(value)) or float(value) < 1.0
            for value in self.inflation_by_cqa
        ):
            raise ValueError("inflation_by_cqa must contain three finite values >= 1")
        if isinstance(self.candidate_density, bool) or self.candidate_density < 8:
            raise ValueError("candidate_density must be an integer >= 8")


@dataclass(frozen=True)
class TrainingContainmentRecord:
    """Truth-only containment observed after one *training* certificate."""

    family: str
    seed: int
    contained_by_cqa: tuple[bool, bool, bool]

    def __post_init__(self) -> None:
        if int(self.seed) not in TRAIN_SEEDS:
            raise ValueError("EC calibration records may contain training seeds 0..63 only")
        if not self.family:
            raise ValueError("family must be non-empty")
        if len(self.contained_by_cqa) != 3 or any(
            not isinstance(value, bool) for value in self.contained_by_cqa
        ):
            raise ValueError("contained_by_cqa must contain three booleans")

    @property
    def joint_contained(self) -> bool:
        return all(self.contained_by_cqa)


@dataclass(frozen=True)
class SelectedTrainingCandidate:
    candidate: ECTrainingCandidate
    joint_lower_bound: float
    per_family_lower_bounds: dict[str, float]


def wilson_lower(successes: int, trials: int, z: float = 1.6448536269514722) -> float:
    """One-sided 95% Wilson lower bound used by the training gate."""
    if trials <= 0:
        return 0.0
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    centre = proportion + z * z / (2.0 * trials)
    half = z * math.sqrt(
        proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)
    )
    return (centre - half) / denominator


def choose_training_candidate(
    observations: Mapping[ECTrainingCandidate, Sequence[TrainingContainmentRecord]],
    *,
    containment_target: float = CONTAINMENT_TARGET,
) -> SelectedTrainingCandidate:
    """Choose the least-expanded setting that preserves per-family containment.

    This is a deliberately training-only tuning boundary: input records with an
    evaluation seed fail before any score can be computed.  The selected
    setting minimizes total CQA inflation, then candidate density, only among
    settings whose one-sided lower bound is at least ``containment_target`` for
    every observed family.
    """
    if not 0.0 < float(containment_target) < 1.0:
        raise ValueError("containment_target must lie strictly between zero and one")
    eligible: list[SelectedTrainingCandidate] = []
    for candidate, records_raw in observations.items():
        records = tuple(records_raw)
        if not records:
            continue
        by_family: dict[str, list[TrainingContainmentRecord]] = {}
        seen: set[tuple[str, int]] = set()
        for record in records:
            if not isinstance(record, TrainingContainmentRecord):
                raise ValueError("records must be TrainingContainmentRecord values")
            key = (record.family, record.seed)
            if key in seen:
                raise ValueError("duplicate training containment record")
            seen.add(key)
            by_family.setdefault(record.family, []).append(record)
        lower = {
            family: wilson_lower(sum(record.joint_contained for record in family_records), len(family_records))
            for family, family_records in by_family.items()
        }
        if lower and min(lower.values()) >= containment_target:
            eligible.append(SelectedTrainingCandidate(candidate, min(lower.values()), lower))
    if not eligible:
        raise ValueError("no training candidate preserves the 90% containment target")
    return min(
        eligible,
        key=lambda selected: (
            sum(selected.candidate.inflation_by_cqa),
            selected.candidate.candidate_density,
            selected.candidate.inflation_by_cqa,
        ),
    )


def _prediction(model, X: Tensor):
    # A tiny structural protocol lets focused unit tests use fixed predictions;
    # production models always take the sanctioned ``predictive`` path.
    if hasattr(model, "mean") and hasattr(model, "variance"):
        return model
    return predictive(model, X)


def per_cqa_lower_utility(
    models: Sequence[object],
    X: Tensor,
    *,
    thresholds: Sequence[float],
    inflation_by_cqa: Sequence[float],
    z: float = 1.0,
) -> Tensor:
    """Return the weakest calibrated, threshold-normalized CQA lower score."""
    if len(models) != len(thresholds) or len(models) != len(inflation_by_cqa) or len(models) < 2:
        raise ValueError("models, thresholds, and inflation_by_cqa must have the same length >= 2")
    if X.ndim != 2:
        raise ValueError("X must be a two-dimensional candidate matrix")
    columns: list[Tensor] = []
    for model, threshold, inflation in zip(models, thresholds, inflation_by_cqa):
        if float(threshold) <= 0.0 or float(inflation) < 1.0:
            raise ValueError("thresholds must be positive and inflations must be >= 1")
        posterior = _prediction(model, X)
        mean = torch.as_tensor(posterior.mean, dtype=torch.double).reshape(-1)
        variance = torch.as_tensor(posterior.variance, dtype=torch.double).reshape(-1)
        if mean.shape[0] != X.shape[0] or variance.shape != mean.shape or bool(torch.any(variance < 0)):
            raise ValueError("each CQA prediction must match the candidate count with nonnegative variance")
        columns.append((mean - float(z) * float(inflation) * variance.sqrt()) / float(threshold))
    return torch.stack(columns, dim=1).amin(dim=1, keepdim=True)


def per_cqa_acquisition_utility(
    models: Sequence[object],
    X: Tensor,
    *,
    thresholds: Sequence[float],
    beta: float = 1.0,
) -> Tensor:
    """Optimistic joint-CQA score used only for experimental placement.

    This is intentionally distinct from the conservative certificate: the
    acquisition uses ``mean + beta*sigma`` to explore unobserved peaks, while
    qualification continues to use simultaneous lower bounds.  A minimum over
    CQAs prevents exploration from sacrificing a required attribute.
    """
    if len(models) != len(thresholds) or len(models) < 2:
        raise ValueError("models and thresholds must have the same length >= 2")
    if float(beta) < 0.0 or not math.isfinite(float(beta)):
        raise ValueError("beta must be finite and nonnegative")
    columns: list[Tensor] = []
    for model, threshold in zip(models, thresholds):
        if float(threshold) <= 0.0:
            raise ValueError("thresholds must be positive")
        posterior = _prediction(model, X)
        mean = torch.as_tensor(posterior.mean, dtype=torch.double).reshape(-1)
        variance = torch.as_tensor(posterior.variance, dtype=torch.double).reshape(-1)
        if mean.shape[0] != X.shape[0] or variance.shape != mean.shape or bool(torch.any(variance < 0)):
            raise ValueError("each CQA prediction must match the candidate count with nonnegative variance")
        columns.append((mean + float(beta) * variance.sqrt()) / float(threshold))
    return torch.stack(columns, dim=1).amin(dim=1, keepdim=True)


def boundary_candidates(bounds: Tensor, *, n: int, seed: int) -> Tensor:
    """Deterministically return unique hypercube-boundary recipes."""
    if bounds.ndim != 2 or bounds.shape[0] != 2 or n < 1:
        raise ValueError("bounds must be (2, d) and n must be positive")
    if n > 2 ** bounds.shape[1]:
        raise ValueError("requested more boundary corners than are available")
    engine = torch.quasirandom.SobolEngine(bounds.shape[1], scramble=True, seed=int(seed))
    bits = (engine.draw(n).double() >= 0.5).double()
    # Sobol draws can repeat corners before covering all corners; enumerate in a
    # seed-rotated order instead, keeping boundary exploration exact and unique.
    start = int(seed) % (2 ** bounds.shape[1])
    codes = torch.arange(start, start + n, dtype=torch.long) % (2 ** bounds.shape[1])
    shifts = torch.arange(bounds.shape[1], dtype=torch.long)
    bits = ((codes[:, None] >> shifts) & 1).double()
    return bounds[0].double() + bits * (bounds[1].double() - bounds[0].double())


__all__ = [
    "CONTAINMENT_TARGET", "ECTrainingCandidate", "SelectedTrainingCandidate",
    "TRAIN_SEEDS", "TrainingContainmentRecord", "boundary_candidates",
    "choose_training_candidate", "per_cqa_acquisition_utility",
    "per_cqa_lower_utility", "wilson_lower",
]
