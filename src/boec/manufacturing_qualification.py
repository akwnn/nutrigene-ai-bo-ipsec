"""Multi-CQA manufacturing qualification for SPADE.

This module is an intentionally separate overlay around the scalar SPADE
certificate machinery.  Each quality attribute receives its own scalar GP and
certificate; release is allowed only in the exact intersection of those masks.
The implementation is computational/synthetic and does not ingest unsigned lab
measurements.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from numbers import Integral, Real
from typing import Sequence

import torch
from torch import Tensor

from boec.reliable_region import (
    ConservativeSetResult,
    conservative_set_split,
    empirical_set_containment,
    reliable_set_draws,
)
from boec.seedbook import derive_seed
from boec.surrogate import build_gp

__all__ = [
    "CqaDefinition",
    "EndpointQualification",
    "ManufacturingQualificationResult",
    "bonferroni_endpoint_alpha",
    "qualify_multi_cqa",
]


@dataclass(frozen=True)
class CqaDefinition:
    """Registered identity and release rule for one quality attribute."""

    name: str
    units: str
    threshold: float
    direction: str
    gamma: float
    assay_id: str
    assay_version: str
    sigma_rel: float | None
    sigma_add: float | None


@dataclass(frozen=True)
class EndpointQualification:
    """Certificate and diagnostics for one CQA endpoint."""

    definition: CqaDefinition
    mask: Tensor
    volume: float
    selection_containment: float | None
    crossfit_containment: float | None
    truth_containment: bool | None
    answer_rate: float
    seed: int

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def units(self) -> str:
        return self.definition.units

    @property
    def threshold(self) -> float:
        return float(self.definition.threshold)

    @property
    def direction(self) -> str:
        return self.definition.direction

    @property
    def gamma(self) -> float:
        return float(self.definition.gamma)


@dataclass(frozen=True)
class ManufacturingQualificationResult:
    """Joint manufacturing certificate and deterministic decision summary."""

    status: str
    grid: Tensor
    endpoint_results: tuple[EndpointQualification, ...]
    joint_mask: Tensor
    joint_volume: float
    limiting_cqa: str | None
    alpha: float
    alpha_endpoint: float
    setpoint_index: int | None
    setpoint: tuple[float, ...] | None
    utility_value: float | None
    joint_truth_containment: bool | None
    base_seed: int
    n_draws: int
    n_rho: int
    volume_rule: str
    protocol_digest: str


def _finite_scalar(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


def _open_probability(value: Real, name: str) -> float:
    result = _finite_scalar(value, name)
    if not 0.0 < result < 1.0:
        raise ValueError(f"{name} must lie strictly between 0 and 1, got {result}")
    return result


def _as_double_tensor(value, name: str) -> Tensor:
    try:
        tensor = torch.as_tensor(value, dtype=torch.double).clone()
    except (TypeError, ValueError, RuntimeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    return tensor


def _validate_grid(X: Tensor, bounds: Tensor) -> None:
    if X.ndim != 2 or X.shape[0] < 1 or X.shape[1] < 1:
        raise ValueError(f"X must have shape (n_grid, d), got {tuple(X.shape)}")
    if not bool(torch.isfinite(X).all()):
        raise ValueError("X must contain only finite coordinates")
    if bounds.ndim != 2 or tuple(bounds.shape) != (2, X.shape[1]):
        raise ValueError(
            f"bounds must have shape (2, d) matching X, got {tuple(bounds.shape)}"
        )
    if not bool(torch.isfinite(bounds).all()):
        raise ValueError("bounds must contain only finite values")
    if not bool(torch.all(bounds[1] > bounds[0])):
        raise ValueError("bounds upper values must be greater than lower values")


def _validate_definition(definition: CqaDefinition) -> None:
    if not isinstance(definition, CqaDefinition):
        raise ValueError("cqas must contain CqaDefinition values")
    for field in ("name", "units", "assay_id", "assay_version"):
        value = getattr(definition, field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"CQA {field} must be a non-empty string")
    _finite_scalar(definition.threshold, f"CQA {definition.name} threshold")
    if definition.direction not in {"greater_equal", "less_equal"}:
        raise ValueError(
            f"CQA {definition.name} direction must be 'greater_equal' or 'less_equal'"
        )
    _open_probability(definition.gamma, f"CQA {definition.name} gamma")
    if definition.sigma_rel is None or definition.sigma_add is None:
        raise ValueError(
            f"CQA {definition.name} noise requires sigma_rel and sigma_add together"
        )
    sigma_rel = _finite_scalar(definition.sigma_rel, f"CQA {definition.name} sigma_rel")
    sigma_add = _finite_scalar(definition.sigma_add, f"CQA {definition.name} sigma_add")
    if sigma_rel < 0.0 or sigma_add < 0.0 or (sigma_rel == 0.0 and sigma_add == 0.0):
        raise ValueError(
            f"CQA {definition.name} noise sigmas must be nonnegative and not both zero"
        )


def _validate_mask(mask, n_grid: int, name: str) -> Tensor:
    tensor = torch.as_tensor(mask).clone()
    if tensor.ndim != 1 or tensor.shape[0] != n_grid or tensor.dtype != torch.bool:
        raise ValueError(f"{name} must be a boolean vector of length {n_grid}")
    return tensor


def _validate_integer(value, name: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return result


def bonferroni_endpoint_alpha(alpha: Real, n_cqas: int) -> float:
    """Allocate a family-wise containment target across endpoint certificates."""
    alpha_f = _open_probability(alpha, "alpha")
    n = _validate_integer(n_cqas, "n_cqas", minimum=2)
    return 1.0 - (1.0 - alpha_f) / n


def _protocol_digest(
    definitions: Sequence[CqaDefinition],
    *,
    alpha: float,
    alpha_endpoint: float,
    n_draws: int,
    n_rho: int,
    base_seed: int,
    volume_rule: str,
    latent_inflation: Sequence[float],
    mean_marginalisation: bool,
) -> str:
    payload = {
        "schema": "boec-spade-multi-cqa-qualification-v1",
        "alpha": alpha,
        "alpha_endpoint": alpha_endpoint,
        "n_draws": n_draws,
        "n_rho": n_rho,
        "base_seed": base_seed,
        "volume_rule": volume_rule,
        "latent_inflation": list(latent_inflation),
        "mean_marginalisation": bool(mean_marginalisation),
        "cqas": [
            {
                "name": d.name,
                "units": d.units,
                "threshold": float(d.threshold),
                "direction": d.direction,
                "gamma": float(d.gamma),
                "assay_id": d.assay_id,
                "assay_version": d.assay_version,
                "sigma_rel": float(d.sigma_rel),
                "sigma_add": float(d.sigma_add),
            }
            for d in definitions
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def qualify_multi_cqa(
    X,
    Y,
    Yvar,
    bounds,
    cqas: Sequence[CqaDefinition],
    *,
    grid=None,
    alpha: Real = 0.95,
    n_draws: int = 512,
    n_rho: int = 64,
    base_seed: int = 270827,
    latent_inflation: Real | Sequence[Real] = 1.0,
    mean_marginalisation: bool = True,
    volume_rule: str = "smallest",
    utility=None,
    truth_masks: Sequence[Tensor] | None = None,
    cqa_names: Sequence[str] | None = None,
    fit_restarts: int = 1,
) -> ManufacturingQualificationResult:
    """Fit independent CQA GPs and return their conservative-mask intersection.

    ``X``/``Y``/``Yvar`` are observed training recipes and CQA measurements.
    ``grid`` is the shared candidate grid on which the operating-region masks are
    issued; when omitted, the observed recipes are used as the grid.
    ``mean_marginalisation`` enables ordinary-kriging covariance (see
    :mod:`boec.meanmarg`) so noise-dominated endpoints cannot collapse before
    inflation; it matches the registered scalar manufacturing recovery default.
    """
    X_t = _as_double_tensor(X, "X")
    grid_t = X_t if grid is None else _as_double_tensor(grid, "grid")
    Y_t = _as_double_tensor(Y, "Y")
    Yvar_t = _as_double_tensor(Yvar, "Yvar")
    bounds_t = _as_double_tensor(bounds, "bounds")
    _validate_grid(X_t, bounds_t)
    _validate_grid(grid_t, bounds_t)
    if Y_t.ndim != 2:
        raise ValueError(f"Y must have shape (n, m), got {tuple(Y_t.shape)}")
    if Yvar_t.ndim != 2:
        raise ValueError(f"Yvar must have shape (n, m), got {tuple(Yvar_t.shape)}")
    if Y_t.shape[0] != X_t.shape[0] or Yvar_t.shape != Y_t.shape:
        raise ValueError(
            f"Y and Yvar must have shape (n, m) matching X; got "
            f"X={tuple(X_t.shape)}, Y={tuple(Y_t.shape)}, Yvar={tuple(Yvar_t.shape)}"
        )
    if Y_t.shape[1] < 2:
        raise ValueError("multi-CQA qualification requires at least two CQA columns")
    if not bool(torch.isfinite(Y_t).all()):
        raise ValueError("Y must contain only finite values")
    if not bool(torch.isfinite(Yvar_t).all()) or bool(torch.any(Yvar_t <= 0.0)):
        raise ValueError("Yvar must contain finite, strictly positive variances")

    definitions = tuple(cqas)
    if len(definitions) != Y_t.shape[1]:
        raise ValueError(
            f"number of cqas ({len(definitions)}) must match Y columns ({Y_t.shape[1]})"
        )
    names = [definition.name for definition in definitions]
    if len(set(names)) != len(names):
        raise ValueError("CQA names must be unique")
    for definition in definitions:
        _validate_definition(definition)
    if cqa_names is not None:
        supplied_names = tuple(cqa_names)
        if supplied_names != tuple(names):
            raise ValueError("cqa_names must match the declared CQA registry order")

    alpha_f = _open_probability(alpha, "alpha")
    alpha_endpoint = bonferroni_endpoint_alpha(alpha_f, len(definitions))
    n_draws_i = _validate_integer(n_draws, "n_draws", minimum=2)
    if n_draws_i % 2:
        raise ValueError("n_draws must be even")
    n_rho_i = _validate_integer(n_rho, "n_rho", minimum=2)
    if volume_rule not in {"smallest", "largest"}:
        raise ValueError("volume_rule must be 'smallest' or 'largest'")
    if isinstance(latent_inflation, Real):
        latent_inflations = ( _finite_scalar(latent_inflation, "latent_inflation"), ) * len(definitions)
    else:
        try:
            latent_inflations = tuple(
                _finite_scalar(value, f"latent_inflation[{index}]")
                for index, value in enumerate(latent_inflation)
            )
        except TypeError as exc:
            raise ValueError("latent_inflation must be a scalar or one value per CQA") from exc
        if len(latent_inflations) != len(definitions):
            raise ValueError("latent_inflation sequence must contain one value per CQA")
    if any(value < 1.0 for value in latent_inflations):
        raise ValueError("latent_inflation must be >= 1")
    if not isinstance(mean_marginalisation, bool):
        raise ValueError(
            f"mean_marginalisation must be bool, got {mean_marginalisation!r}"
        )
    base_seed_i = _validate_integer(base_seed, "base_seed", minimum=0)
    fit_restarts_i = _validate_integer(fit_restarts, "fit_restarts", minimum=1)

    utility_t: Tensor | None = None
    if utility is not None:
        utility_t = _as_double_tensor(utility, "utility").reshape(-1)
        if utility_t.shape != (grid_t.shape[0],):
            raise ValueError(f"utility must have shape ({grid_t.shape[0]},)")
        if not bool(torch.isfinite(utility_t).all()):
            raise ValueError("utility must contain only finite values")

    truth_t: tuple[Tensor, ...] | None = None
    if truth_masks is not None:
        truth_t = tuple(
            _validate_mask(mask, grid_t.shape[0], f"truth_masks[{index}]")
            for index, mask in enumerate(truth_masks)
        )
        if len(truth_t) != len(definitions):
            raise ValueError("truth_masks must contain one mask per CQA")

    digest = _protocol_digest(
        definitions,
        alpha=alpha_f,
        alpha_endpoint=alpha_endpoint,
        n_draws=n_draws_i,
        n_rho=n_rho_i,
        base_seed=base_seed_i,
        volume_rule=volume_rule,
        latent_inflation=latent_inflations,
        mean_marginalisation=mean_marginalisation,
    )

    endpoint_results: list[EndpointQualification] = []
    joint_mask = torch.ones(grid_t.shape[0], dtype=torch.bool)
    for index, definition in enumerate(definitions):
        if definition.direction == "less_equal":
            train_y = -Y_t[:, index]
            transformed_threshold = -float(definition.threshold)
        else:
            train_y = Y_t[:, index]
            transformed_threshold = float(definition.threshold)
        model = build_gp(
            X_t,
            train_y.unsqueeze(-1),
            Yvar_t[:, index].unsqueeze(-1),
            bounds_t,
            fit=True,
            fit_restarts=fit_restarts_i,
        )
        seed = derive_seed(base_seed_i, "manufacturing-cqa", definition.name, index)
        draws = reliable_set_draws(
            model,
            grid_t,
            transformed_threshold,
            float(definition.gamma),
            n_draws_i,
            seed,
            sigma_rel=float(definition.sigma_rel),
            sigma_add=float(definition.sigma_add),
            latent_inflation=latent_inflations[index],
            mean_marginalisation=mean_marginalisation,
        )
        if draws.ndim != 2 or draws.shape[1] != grid_t.shape[0] or draws.dtype != torch.bool:
            raise ValueError(
                f"reliable-set draws for {definition.name} must have shape "
                f"(n_draws, {grid_t.shape[0]}) and boolean dtype"
            )
        certificate: ConservativeSetResult = conservative_set_split(
            draws,
            alpha_endpoint,
            n_rho=n_rho_i,
            volume_rule=volume_rule,
        )
        mask = _validate_mask(certificate.mask, grid_t.shape[0], f"certificate[{definition.name}]")
        truth_containment = (
            empirical_set_containment(mask, truth_t[index]) if truth_t is not None else None
        )
        answer_rate = float(draws.any(dim=1).double().mean())
        endpoint_results.append(
            EndpointQualification(
                definition=definition,
                mask=mask.clone(),
                volume=float(mask.double().mean()),
                selection_containment=certificate.selection_containment,
                crossfit_containment=certificate.crossfit_containment,
                truth_containment=truth_containment,
                answer_rate=answer_rate,
                seed=seed,
            )
        )
        joint_mask = torch.logical_and(joint_mask, mask)

    joint_volume = float(joint_mask.double().mean())
    if bool(joint_mask.any()):
        status = "QUALIFIED"
        limiting = min(endpoint_results, key=lambda result: (result.volume, result.name)).name
    else:
        status = "ABSTAIN_EMPTY_JOINT"
        limiting = None

    setpoint_index: int | None = None
    setpoint: tuple[float, ...] | None = None
    utility_value: float | None = None
    if utility_t is not None and bool(joint_mask.any()):
        candidate_indices = torch.nonzero(joint_mask, as_tuple=False).flatten()
        candidate_values = utility_t[candidate_indices]
        max_value = torch.max(candidate_values)
        tied = candidate_indices[candidate_values == max_value]
        setpoint_index = int(tied[0])
        setpoint = tuple(float(value) for value in grid_t[setpoint_index].tolist())
        utility_value = float(max_value)

    joint_truth_containment = None
    if truth_t is not None:
        truth_joint = torch.ones(grid_t.shape[0], dtype=torch.bool)
        for truth_mask in truth_t:
            truth_joint = torch.logical_and(truth_joint, truth_mask)
        joint_truth_containment = empirical_set_containment(joint_mask, truth_joint)

    return ManufacturingQualificationResult(
        status=status,
        grid=grid_t,
        endpoint_results=tuple(endpoint_results),
        joint_mask=joint_mask.clone(),
        joint_volume=joint_volume,
        limiting_cqa=limiting,
        alpha=alpha_f,
        alpha_endpoint=alpha_endpoint,
        setpoint_index=setpoint_index,
        setpoint=setpoint,
        utility_value=utility_value,
        joint_truth_containment=joint_truth_containment,
        base_seed=base_seed_i,
        n_draws=n_draws_i,
        n_rho=n_rho_i,
        volume_rule=volume_rule,
        protocol_digest=digest,
    )
