"""Frozen randomized oracle families reserved for the SPADE lockbox.

These families are intentionally unrelated to the five development families.  A
generator key denotes one deterministic landscape instance, not one observation-noise
replicate.  All public responses are normalized to ``[0, 1]`` with an audited interior
maximum of one.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from numbers import Integral
from typing import Final

import numpy as np
import torch
from scipy.optimize import minimize
from scipy.special import logsumexp

from boec.seedbook import derive_seed

__all__ = [
    "LOCKBOX_FAMILIES",
    "LockboxInstanceRecord",
    "LockboxOptimumAudit",
    "LockboxOracle",
    "make_lockbox_oracle",
]


LOCKBOX_FAMILIES: Final[tuple[str, ...]] = (
    "toroidal_rastrigin",
    "gaussian_basin_mixture",
    "curved_ridge",
    "soft_plateau",
)
_DIM: Final = 6
_FIRST_KEY: Final = 0
_LAST_KEY: Final = 1999


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _rng(family: str, instance_seed: int) -> tuple[np.random.Generator, int]:
    parameter_seed = derive_seed(instance_seed, "lockbox_generator_parameters", family)
    return np.random.default_rng(parameter_seed), parameter_seed


def _orthogonal(rng: np.random.Generator) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(_DIM, _DIM)))
    signs = np.where(np.diag(r) < 0.0, -1.0, 1.0)
    q = q * signs[None, :]
    if np.linalg.det(q) < 0.0:
        q[:, 0] *= -1.0
    return q


def _sobol(n: int, seed: int) -> np.ndarray:
    engine = torch.quasirandom.SobolEngine(
        dimension=_DIM,
        scramble=True,
        seed=int(seed % (2**31 - 1)),
    )
    return engine.draw(n).double().numpy()


@dataclass(frozen=True)
class LockboxOptimumAudit:
    """Immutable evidence that the recorded normalized optimum is one."""

    method: str
    optimum_x: tuple[float, ...]
    optimum_value: float
    independent_x: tuple[float, ...]
    independent_value: float
    agreement: float
    challenge_points: int
    challenge_maximum: float
    passed: bool


@dataclass(frozen=True)
class LockboxInstanceRecord:
    """Complete immutable generator parameters and optimum audit for one key."""

    schema: str
    family: str
    dim: int
    instance_seed: int
    parameter_seed: int
    parameters_json: str
    parameter_digest: str
    audit: LockboxOptimumAudit


class LockboxOracle:
    """Numpy oracle with a torch-only scorer view and immutable public metadata."""

    __slots__ = ("_family", "_parameters_json", "_record")

    def __init__(
        self,
        family: str,
        parameters: dict[str, object],
        record: LockboxInstanceRecord,
    ) -> None:
        parameters_json = _canonical_json(_jsonable_parameters(parameters))
        expected_digest = hashlib.sha256(parameters_json.encode("utf-8")).hexdigest()
        if (
            record.schema != "boec-lockbox-instance-v1"
            or record.family != family
            or record.dim != _DIM
            or parameters_json != record.parameters_json
            or record.parameter_digest != expected_digest
        ):
            raise ValueError("oracle parameters do not match the immutable instance record")
        object.__setattr__(self, "_family", family)
        object.__setattr__(self, "_parameters_json", parameters_json)
        object.__setattr__(self, "_record", record)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("LockboxOracle state is immutable")

    @property
    def name(self) -> str:
        return self._family

    @property
    def dim(self) -> int:
        return _DIM

    @property
    def record(self) -> LockboxInstanceRecord:
        return self._record

    @property
    def optimum_x(self) -> np.ndarray:
        return np.asarray(self._record.audit.optimum_x, dtype=float).copy()

    @property
    def optimum_value(self) -> float:
        return 1.0

    def _check_X(self, X: np.ndarray) -> np.ndarray:
        values = np.asarray(X, dtype=float)
        if values.ndim != 2 or values.shape[1] != _DIM:
            raise ValueError(f"X must have shape (n, {_DIM}), got {values.shape}")
        if not np.isfinite(values).all():
            raise ValueError("X must be finite")
        if np.any(values < 0.0) or np.any(values > 1.0):
            raise ValueError("X must lie in the unit cube")
        return values

    def f(self, X: np.ndarray) -> np.ndarray:
        values = self._check_X(X)
        p = _runtime_parameters(self._parameters_json)
        if self._family == "toroidal_rastrigin":
            shift = p["shift"]
            delta = np.remainder(values - shift + 0.5, 1.0) - 0.5
            z = delta @ p["rotation"]
            penalty = (
                p["anisotropy"] * z**2
                + p["oscillation"]
                * (1.0 - np.cos(2.0 * np.pi * p["frequency"] * z))
            ).sum(axis=1)
            result = np.exp(-penalty / p["temperature"])
        elif self._family == "gaussian_basin_mixture":
            raw = _mixture_log_value(values, p)
            result = np.exp(raw - p["raw_optimum"])
        elif self._family == "curved_ridge":
            z = (values - p["shift"]) @ p["rotation"]
            along = z[:, 0]
            bent = z[:, 1:] - p["curvature"][None, :] * along[:, None] ** 2
            penalty = (along / p["along_scale"]) ** 2
            penalty += ((bent / p["ridge_width"][None, :]) ** 2).sum(axis=1)
            ridge = np.exp(-0.5 * penalty)
            background_penalty = (
                (z / p["background_scale"][None, :]) ** 2
            ).sum(axis=1)
            background = np.exp(-0.5 * background_penalty)
            weight = p["background_weight"]
            result = (1.0 - weight) * ridge + weight * background
        elif self._family == "soft_plateau":
            z = (values - p["shift"]) @ p["rotation"]
            radius = np.sqrt(((z / p["axis_scale"]) ** 2).sum(axis=1))
            logits = (p["plateau_radius"] - radius) / p["edge_width"]
            peak_logit = p["plateau_radius"] / p["edge_width"]
            result = _expit(logits) / _expit(peak_logit)
        else:  # pragma: no cover - constructor is private and validated
            raise RuntimeError(f"unsupported lockbox family {self._family!r}")
        return np.clip(np.asarray(result, dtype=float), 0.0, 1.0)

    def truth(self, X: torch.Tensor) -> torch.Tensor:
        if not isinstance(X, torch.Tensor):
            raise TypeError("scorer truth requires a torch tensor")
        result = self.f(X.detach().cpu().double().numpy())
        return torch.as_tensor(result, dtype=torch.double, device=X.device)


def _expit(value: np.ndarray | float) -> np.ndarray:
    x = np.asarray(value, dtype=float)
    result = np.empty_like(x)
    positive = x >= 0.0
    result[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
    exp_x = np.exp(x[~positive])
    result[~positive] = exp_x / (1.0 + exp_x)
    return result


def _mixture_log_value(X: np.ndarray, p: dict[str, object]) -> np.ndarray:
    delta = X[:, None, :] - p["centers"][None, :, :]
    rotated = np.einsum("nkd,kde->nke", delta, p["rotations"])
    quadratic = ((rotated / p["widths"][None, :, :]) ** 2).sum(axis=2)
    return logsumexp(p["log_weights"][None, :] - 0.5 * quadratic, axis=1)


def _jsonable_parameters(parameters: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in parameters.items():
        if isinstance(value, np.ndarray):
            result[key] = value.tolist()
        elif isinstance(value, np.generic):
            result[key] = value.item()
        else:
            result[key] = value
    return result


def _runtime_parameters(parameters_json: str) -> dict[str, object]:
    """Create disposable arrays from the canonical immutable parameter payload."""
    payload = json.loads(parameters_json)
    return {
        key: np.asarray(value, dtype=float) if isinstance(value, list) else value
        for key, value in payload.items()
    }


def _analytic_audit(
    family: str,
    parameters: dict[str, object],
    optimum: np.ndarray,
    instance_seed: int,
) -> LockboxOptimumAudit:
    serialized = _jsonable_parameters(parameters)
    parameters_json = _canonical_json(serialized)
    placeholder = LockboxInstanceRecord(
        schema="boec-lockbox-instance-v1",
        family=family,
        dim=_DIM,
        instance_seed=instance_seed,
        parameter_seed=0,
        parameters_json=parameters_json,
        parameter_digest=hashlib.sha256(parameters_json.encode("utf-8")).hexdigest(),
        audit=LockboxOptimumAudit("pending", tuple(optimum), 1.0, tuple(optimum), 1.0, 0.0, 0, 0.0, False),
    )
    oracle = LockboxOracle(family, parameters, placeholder)
    challenge = _sobol(4096, derive_seed(instance_seed, "lockbox_optimum_challenge", family))
    challenge_max = float(oracle.f(challenge).max())
    value = float(oracle.f(optimum[None, :])[0])
    agreement = abs(1.0 - value)
    passed = (
        bool(np.all((optimum >= 0.2) & (optimum <= 0.8)))
        and agreement <= 1e-12
        and challenge_max <= 1.0 + 1e-12
    )
    if not passed:
        raise RuntimeError(f"{family} key {instance_seed} failed analytic optimum audit")
    return LockboxOptimumAudit(
        method="analytic_unique_optimum_plus_4096_sobol_challenge",
        optimum_x=tuple(float(x) for x in optimum),
        optimum_value=value,
        independent_x=tuple(float(x) for x in optimum),
        independent_value=value,
        agreement=agreement,
        challenge_points=4096,
        challenge_maximum=challenge_max,
        passed=True,
    )


def _mixture_optimum_audit(
    parameters: dict[str, object],
    instance_seed: int,
) -> tuple[LockboxOptimumAudit, float]:
    def objective(x: np.ndarray) -> float:
        return -float(_mixture_log_value(np.asarray(x)[None, :], parameters)[0])

    bounds = [(0.0, 1.0)] * _DIM
    centers = np.asarray(parameters["centers"])
    audit_grid = _sobol(4096, derive_seed(instance_seed, "mixture_dense_audit"))
    raw_grid = _mixture_log_value(audit_grid, parameters)
    dense_starts = audit_grid[np.argsort(raw_grid)[-12:]]
    # The candidate set deliberately contains every planted basin centre and the
    # strongest points from an unrelated dense Sobol challenge.  Treating those as
    # two competing audits failed on key 84: a dense grid can miss a narrow but taller
    # basin.  One unioned multistart search is the actual global search; a different
    # solver then independently re-polishes its winner below.
    runs = [
        minimize(objective, x, method="L-BFGS-B", bounds=bounds)
        for x in np.vstack([centers, dense_starts])
    ]
    successful = [run for run in runs if run.success and math.isfinite(float(run.fun))]
    if not successful:
        raise RuntimeError(f"gaussian mixture key {instance_seed} optimum solver failed")
    multistart_best = min(successful, key=lambda run: float(run.fun))
    independent_best = minimize(
        objective,
        np.asarray(multistart_best.x, dtype=float),
        method="SLSQP",
        bounds=bounds,
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    if not independent_best.success or not math.isfinite(float(independent_best.fun)):
        raise RuntimeError(
            f"gaussian mixture key {instance_seed} independent optimum polish failed"
        )

    optimum_run = min(
        (multistart_best, independent_best), key=lambda run: float(run.fun)
    )
    optimum = np.asarray(optimum_run.x, dtype=float)
    independent = np.asarray(independent_best.x, dtype=float)
    raw_optimum = -float(optimum_run.fun)
    independent_raw = -float(independent_best.fun)
    agreement = abs(raw_optimum - independent_raw)
    normalized_independent = math.exp(independent_raw - raw_optimum)
    challenge_max = float(np.exp(raw_grid.max() - raw_optimum))
    passed = (
        bool(np.all((optimum >= 0.2) & (optimum <= 0.8)))
        and agreement <= 1e-6
        and normalized_independent <= 1.0 + 1e-6
        and challenge_max <= 1.0 + 1e-6
    )
    if not passed:
        raise RuntimeError(
            f"gaussian mixture key {instance_seed} failed independent optimum audit: "
            f"agreement={agreement:.3g}"
        )
    return (
        LockboxOptimumAudit(
            method="centers_plus_dense_sobol_multistart_with_slsqp_repolish",
            optimum_x=tuple(float(x) for x in optimum),
            optimum_value=1.0,
            independent_x=tuple(float(x) for x in independent),
            independent_value=normalized_independent,
            agreement=agreement,
            challenge_points=4096,
            challenge_maximum=challenge_max,
            passed=True,
        ),
        raw_optimum,
    )


def _separated_centers(rng: np.random.Generator, count: int) -> np.ndarray:
    centers: list[np.ndarray] = []
    attempts = 0
    while len(centers) < count and attempts < 20_000:
        attempts += 1
        proposed = rng.uniform(0.2, 0.8, size=_DIM)
        if all(np.linalg.norm(proposed - existing) >= 0.38 for existing in centers):
            centers.append(proposed)
    if len(centers) != count:
        raise RuntimeError("could not sample separated Gaussian-mixture centers")
    return np.stack(centers)


def _parameters(family: str, instance_seed: int) -> tuple[dict[str, object], int]:
    rng, parameter_seed = _rng(family, instance_seed)
    if family == "toroidal_rastrigin":
        parameters = {
            "shift": rng.uniform(0.2, 0.8, size=_DIM),
            "rotation": _orthogonal(rng),
            "frequency": rng.integers(2, 6, size=_DIM).astype(float),
            "anisotropy": rng.uniform(2.0, 7.0, size=_DIM),
            "oscillation": rng.uniform(0.15, 0.45, size=_DIM),
            "temperature": float(rng.uniform(1.2, 2.4)),
        }
    elif family == "gaussian_basin_mixture":
        count = int(rng.integers(3, 6))
        weights = np.sort(rng.uniform(0.35, 0.82, size=count))[::-1]
        weights[0] = 1.0
        parameters = {
            "component_count": count,
            "centers": _separated_centers(rng, count),
            "rotations": np.stack([_orthogonal(rng) for _ in range(count)]),
            "widths": rng.uniform(0.045, 0.13, size=(count, _DIM)),
            "log_weights": np.log(weights),
        }
    elif family == "curved_ridge":
        parameters = {
            "shift": rng.uniform(0.2, 0.8, size=_DIM),
            "rotation": _orthogonal(rng),
            "curvature": rng.uniform(-0.9, 0.9, size=_DIM - 1),
            "along_scale": float(rng.uniform(0.25, 0.42)),
            "ridge_width": rng.uniform(0.06, 0.13, size=_DIM - 1),
            "background_weight": float(rng.uniform(0.15, 0.22)),
            "background_scale": rng.uniform(0.48, 0.68, size=_DIM),
        }
    elif family == "soft_plateau":
        parameters = {
            "shift": rng.uniform(0.2, 0.8, size=_DIM),
            "rotation": _orthogonal(rng),
            "axis_scale": rng.uniform(0.16, 0.34, size=_DIM),
            "plateau_radius": float(rng.uniform(0.72, 1.18)),
            "edge_width": float(rng.uniform(0.055, 0.12)),
        }
    else:
        raise ValueError(
            f"unknown lockbox family {family!r}; expected one of {LOCKBOX_FAMILIES}"
        )
    return parameters, parameter_seed


def make_lockbox_oracle(family: str, instance_seed: int) -> LockboxOracle:
    """Create one deterministic, audited lockbox landscape from a reserved key."""
    if family not in LOCKBOX_FAMILIES:
        raise ValueError(
            f"unknown lockbox family {family!r}; expected one of {LOCKBOX_FAMILIES}"
        )
    if isinstance(instance_seed, bool) or not isinstance(instance_seed, Integral):
        raise ValueError("instance_seed must be an integer from 0 through 1999")
    key = int(instance_seed)
    if not _FIRST_KEY <= key <= _LAST_KEY:
        raise ValueError("instance_seed must be an integer from 0 through 1999")

    return _make_lockbox_oracle_cached(family, key)


@lru_cache(maxsize=None)
def _make_lockbox_oracle_cached(family: str, key: int) -> LockboxOracle:
    """Cache only after strict validation so bool/int key aliasing cannot bypass it."""

    parameters, parameter_seed = _parameters(family, key)
    if family == "gaussian_basin_mixture":
        audit, raw_optimum = _mixture_optimum_audit(parameters, key)
        parameters["raw_optimum"] = raw_optimum
    else:
        optimum = np.asarray(parameters["shift"], dtype=float)
        audit = _analytic_audit(family, parameters, optimum, key)

    serialized = _jsonable_parameters(parameters)
    parameters_json = _canonical_json(serialized)
    record = LockboxInstanceRecord(
        schema="boec-lockbox-instance-v1",
        family=family,
        dim=_DIM,
        instance_seed=key,
        parameter_seed=parameter_seed,
        parameters_json=parameters_json,
        parameter_digest=_digest(serialized),
        audit=audit,
    )
    return LockboxOracle(family, parameters, record)
