"""Registered synthetic benchmark for scalar versus joint CQA qualification."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from numbers import Integral
from typing import Sequence

import torch
from torch import Tensor

from boec.manufacturing_qualification import (
    CqaDefinition,
    qualify_multi_cqa,
)
from boec.reliable_region import (
    conservative_set_split,
    empirical_set_containment,
    reliable_set_draws,
    true_reliability_probability,
)
from boec.seedbook import IndexedGaussianNoise, derive_seed
from boec.surrogate import build_gp

__all__ = [
    "BenchmarkConfig",
    "BenchmarkRow",
    "SyntheticFamily",
    "aggregate_rows",
    "evaluate_family",
    "registered_families",
    "run_replicate",
]


@dataclass(frozen=True)
class SyntheticFamily:
    """One registered vector-valued synthetic manufacturing landscape."""

    name: str
    centers: tuple[tuple[float, ...], ...]
    widths: tuple[float, ...]
    dimension: int = 6


@dataclass(frozen=True)
class BenchmarkConfig:
    """Immutable protocol values for one benchmark run."""

    dimension: int = 6
    train_count: int = 48
    grid_count: int = 4096
    n_draws: int = 512
    n_rho: int = 64
    alpha: float = 0.95
    gamma: float = 0.95
    sigma_rel: float = 0.04
    sigma_add: float = 0.01
    threshold: float = 0.50
    volume_rule: str = "smallest"

    def __post_init__(self) -> None:
        integer_fields = ("dimension", "train_count", "grid_count", "n_draws", "n_rho")
        for field in integer_fields:
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 1:
                raise ValueError(f"{field} must be a positive integer")
        if self.dimension < 3:
            raise ValueError("dimension must be at least 3")
        if self.n_draws < 2 or self.n_draws % 2:
            raise ValueError("n_draws must be even and at least 2")
        if self.n_rho < 2:
            raise ValueError("n_rho must be at least 2")
        for field in ("alpha", "gamma"):
            value = float(getattr(self, field))
            if not math.isfinite(value) or not 0.0 < value < 1.0:
                raise ValueError(f"{field} must lie strictly between 0 and 1")
        for field in ("sigma_rel", "sigma_add"):
            value = float(getattr(self, field))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{field} must be finite and nonnegative")
        if self.sigma_rel == 0.0 and self.sigma_add == 0.0:
            raise ValueError("sigma_rel and sigma_add cannot both be zero")
        if not math.isfinite(float(self.threshold)):
            raise ValueError("threshold must be finite")
        if self.volume_rule not in {"smallest", "largest"}:
            raise ValueError("volume_rule must be 'smallest' or 'largest'")

    @property
    def digest(self) -> str:
        payload = {
            key: getattr(self, key)
            for key in (
                "dimension",
                "train_count",
                "grid_count",
                "n_draws",
                "n_rho",
                "alpha",
                "gamma",
                "sigma_rel",
                "sigma_add",
                "threshold",
                "volume_rule",
            )
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class BenchmarkRow:
    family: str
    replicate_seed: int
    algorithm_seed: int
    dimension: int
    train_count: int
    grid_count: int
    scalar_primary_volume: float
    scalar_primary_containment: bool | None
    scalar_joint_containment: bool | None
    scalar_unsafe_rate: float | None
    joint_status: str
    joint_volume: float
    joint_containment: bool | None
    joint_unsafe_rate: float | None
    scalar_answer: bool
    joint_answer: bool
    endpoint_volumes: dict[str, float]
    limiting_cqa: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "replicate_seed": self.replicate_seed,
            "algorithm_seed": self.algorithm_seed,
            "dimension": self.dimension,
            "train_count": self.train_count,
            "grid_count": self.grid_count,
            "scalar_primary_volume": self.scalar_primary_volume,
            "scalar_primary_containment": self.scalar_primary_containment,
            "scalar_joint_containment": self.scalar_joint_containment,
            "scalar_unsafe_rate": self.scalar_unsafe_rate,
            "joint_status": self.joint_status,
            "joint_volume": self.joint_volume,
            "joint_containment": self.joint_containment,
            "joint_unsafe_rate": self.joint_unsafe_rate,
            "scalar_answer": self.scalar_answer,
            "joint_answer": self.joint_answer,
            "endpoint_volumes": dict(self.endpoint_volumes),
            "limiting_cqa": self.limiting_cqa,
        }


def _validate_family(family: SyntheticFamily) -> None:
    if not isinstance(family, SyntheticFamily):
        raise ValueError("family must be a SyntheticFamily")
    if not family.name.strip():
        raise ValueError("family name must be non-empty")
    if family.dimension < 3:
        raise ValueError("family dimension must be at least 3")
    if len(family.centers) != 3 or len(family.widths) != 3:
        raise ValueError("family must define exactly three CQA centers and widths")
    for center in family.centers:
        if len(center) != 3 or not all(math.isfinite(float(v)) for v in center):
            raise ValueError("each CQA center must contain three finite values")
        if not all(0.0 <= float(v) <= 1.0 for v in center):
            raise ValueError("CQA centers must lie in [0, 1]")
    if not all(math.isfinite(float(width)) and float(width) > 0.0 for width in family.widths):
        raise ValueError("CQA widths must be finite and positive")


def registered_families(dimension: int = 6) -> tuple[SyntheticFamily, ...]:
    if isinstance(dimension, bool) or not isinstance(dimension, Integral) or int(dimension) < 3:
        raise ValueError("dimension must be an integer of at least 3")
    widths = (5.0, 5.0, 5.0)
    return (
        SyntheticFamily(
            "aligned",
            ((0.48, 0.50, 0.50), (0.50, 0.48, 0.52), (0.52, 0.50, 0.48)),
            widths,
            int(dimension),
        ),
        SyntheticFamily(
            "moderate_conflict",
            ((0.35, 0.40, 0.50), (0.60, 0.55, 0.45), (0.48, 0.35, 0.62)),
            widths,
            int(dimension),
        ),
        SyntheticFamily(
            "strong_conflict",
            ((0.18, 0.28, 0.40), (0.76, 0.70, 0.60), (0.45, 0.20, 0.82)),
            widths,
            int(dimension),
        ),
    )


def evaluate_family(family: SyntheticFamily, X: Tensor) -> Tensor:
    """Evaluate three bounded Gaussian-peak CQAs at finite recipe coordinates."""
    _validate_family(family)
    if not isinstance(X, Tensor) or X.ndim != 2 or X.shape[1] != family.dimension:
        shape = tuple(X.shape) if isinstance(X, Tensor) else type(X).__name__
        raise ValueError(
            f"X dimension must be {family.dimension}; expected shape "
            f"(n, {family.dimension}), got {shape}"
        )
    if X.shape[0] < 1 or not bool(torch.isfinite(X).all()):
        raise ValueError("X must contain at least one finite recipe")
    values = []
    active = X[:, :3].double()
    for center, width in zip(family.centers, family.widths):
        c = torch.tensor(center, dtype=torch.double, device=active.device)
        values.append(torch.exp(-float(width) * (active - c).square().sum(dim=1)))
    return torch.stack(values, dim=1)


def _definitions(family: SyntheticFamily, config: BenchmarkConfig) -> tuple[CqaDefinition, ...]:
    return tuple(
        CqaDefinition(
            name=name,
            units="synthetic_fraction",
            threshold=config.threshold,
            direction="greater_equal",
            gamma=config.gamma,
            assay_id=f"synthetic-{family.name}-{name}",
            assay_version="v1",
            sigma_rel=config.sigma_rel,
            sigma_add=config.sigma_add,
        )
        for name in ("identity", "viability", "yield")
    )


def _unsafe_rate(mask: Tensor, truth: Tensor) -> float | None:
    count = int(mask.sum())
    if count == 0:
        return None
    return float((mask & ~truth).double().sum() / count)


def run_replicate(
    family: SyntheticFamily,
    *,
    config: BenchmarkConfig,
    replicate_seed: int,
    algorithm_seed: int,
) -> BenchmarkRow:
    """Run one paired scalar-versus-joint qualification replicate."""
    _validate_family(family)
    if family.dimension != config.dimension:
        raise ValueError("family dimension must match benchmark configuration")
    for name, value in (("replicate_seed", replicate_seed), ("algorithm_seed", algorithm_seed)):
        if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    replicate_seed_i = int(replicate_seed)
    algorithm_seed_i = int(algorithm_seed)
    sobol_seed = derive_seed(replicate_seed_i, "manufacturing-benchmark-sobol", family.name) % (2**32)
    points = torch.quasirandom.SobolEngine(
        dimension=config.dimension, scramble=True, seed=sobol_seed
    ).draw(config.train_count + config.grid_count).double()
    train_X = points[: config.train_count].clone()
    grid = points[config.train_count :].clone()
    latent_train = evaluate_family(family, train_X)
    latent_grid = evaluate_family(family, grid)
    observations: list[Tensor] = []
    variances: list[Tensor] = []
    observation_indices = torch.arange(config.train_count, dtype=torch.long)
    for cqa_index in range(3):
        noise = IndexedGaussianNoise(
            root_seed=derive_seed(
                replicate_seed_i, "manufacturing-benchmark-noise", family.name, cqa_index
            ),
            sigma_rel=config.sigma_rel,
            sigma_add=config.sigma_add,
        )
        observed, variance = noise.observe(observation_indices, latent_train[:, cqa_index])
        observations.append(observed)
        variances.append(variance)
    Y = torch.stack(observations, dim=1)
    Yvar = torch.stack(variances, dim=1)
    bounds = torch.stack((torch.zeros(config.dimension), torch.ones(config.dimension)))
    definitions = _definitions(family, config)
    truth_masks = tuple(
        true_reliability_probability(
            latent_grid[:, index],
            config.threshold,
            config.sigma_rel,
            config.sigma_add,
        )
        >= config.gamma
        for index in range(3)
    )
    truth_joint = torch.logical_and(torch.logical_and(truth_masks[0], truth_masks[1]), truth_masks[2])

    scalar_model = build_gp(
        train_X,
        Y[:, :1],
        Yvar[:, :1],
        bounds,
        fit=True,
        fit_restarts=1,
    )
    scalar_draws = reliable_set_draws(
        scalar_model,
        grid,
        config.threshold,
        config.gamma,
        config.n_draws,
        derive_seed(algorithm_seed_i, "manufacturing-benchmark-scalar", family.name),
        sigma_rel=config.sigma_rel,
        sigma_add=config.sigma_add,
    )
    scalar_certificate = conservative_set_split(
        scalar_draws,
        config.alpha,
        n_rho=config.n_rho,
        volume_rule=config.volume_rule,
    )
    scalar_mask = scalar_certificate.mask
    joint_result = qualify_multi_cqa(
        train_X,
        Y,
        Yvar,
        bounds,
        definitions,
        grid=grid,
        alpha=config.alpha,
        n_draws=config.n_draws,
        n_rho=config.n_rho,
        base_seed=derive_seed(algorithm_seed_i, "manufacturing-benchmark-joint", family.name),
        volume_rule=config.volume_rule,
        truth_masks=truth_masks,
    )
    return BenchmarkRow(
        family=family.name,
        replicate_seed=replicate_seed_i,
        algorithm_seed=algorithm_seed_i,
        dimension=config.dimension,
        train_count=config.train_count,
        grid_count=config.grid_count,
        scalar_primary_volume=float(scalar_mask.double().mean()),
        scalar_primary_containment=empirical_set_containment(scalar_mask, truth_masks[0]),
        scalar_joint_containment=empirical_set_containment(scalar_mask, truth_joint),
        scalar_unsafe_rate=_unsafe_rate(scalar_mask, truth_joint),
        joint_status=joint_result.status,
        joint_volume=joint_result.joint_volume,
        joint_containment=joint_result.joint_truth_containment,
        joint_unsafe_rate=_unsafe_rate(joint_result.joint_mask, truth_joint),
        scalar_answer=bool(scalar_mask.any()),
        joint_answer=bool(joint_result.joint_mask.any()),
        endpoint_volumes={
            endpoint.name: float(endpoint.volume)
            for endpoint in joint_result.endpoint_results
        },
        limiting_cqa=joint_result.limiting_cqa,
    )


def _median_iqr(values: Sequence[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    tensor = torch.tensor(list(values), dtype=torch.double)
    median = float(torch.quantile(tensor, 0.5))
    q1 = float(torch.quantile(tensor, 0.25))
    q3 = float(torch.quantile(tensor, 0.75))
    return median, q3 - q1


def aggregate_rows(rows: Sequence[BenchmarkRow]) -> dict[str, object]:
    """Summarize replicate-level metrics without treating grid points as replicates."""
    if not rows:
        raise ValueError("rows must contain at least one BenchmarkRow")
    families = {row.family for row in rows}
    if len(families) != 1:
        raise ValueError("aggregate_rows requires rows from one family")
    scalar_unsafe = [row.scalar_unsafe_rate for row in rows if row.scalar_unsafe_rate is not None]
    joint_unsafe = [row.joint_unsafe_rate for row in rows if row.joint_unsafe_rate is not None]
    scalar_volume = [row.scalar_primary_volume for row in rows]
    joint_volume = [row.joint_volume for row in rows]
    scalar_median, scalar_iqr = _median_iqr(scalar_unsafe)
    joint_median, joint_iqr = _median_iqr(joint_unsafe)
    scalar_volume_median, scalar_volume_iqr = _median_iqr(scalar_volume)
    joint_volume_median, joint_volume_iqr = _median_iqr(joint_volume)
    return {
        "family": next(iter(families)),
        "replicate_count": len(rows),
        "grid_points_pooled": False,
        "scalar_nonempty_rate": sum(row.scalar_answer for row in rows) / len(rows),
        "joint_nonempty_rate": sum(row.joint_answer for row in rows) / len(rows),
        "scalar_unsafe_rate_nonempty_median": scalar_median,
        "scalar_unsafe_rate_nonempty_iqr": scalar_iqr,
        "joint_unsafe_rate_nonempty_median": joint_median,
        "joint_unsafe_rate_nonempty_iqr": joint_iqr,
        "median_scalar_primary_volume": scalar_volume_median,
        "iqr_scalar_primary_volume": scalar_volume_iqr,
        "median_joint_volume": joint_volume_median,
        "iqr_joint_volume": joint_volume_iqr,
        "scalar_joint_containment_rate": sum(
            row.scalar_joint_containment is True for row in rows
        ) / len(rows),
        "joint_containment_rate": sum(row.joint_containment is True for row in rows) / len(rows),
    }
