"""The unified, exactly-48-evaluation SPADE campaign protocol.

This module makes campaign decisions from observations only.  Oracle truth and all
scoring functions deliberately live outside its public interfaces.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from numbers import Integral, Real
from typing import Literal

import torch
from torch import Tensor

from boec.optimizers import AcqConfig, make_acquisition, propose, sobol_design
from boec.reliable_region import model_reliability_probability
from boec.seedbook import derive_seed
from boec.surrogate import build_learned_noise_gp, outcome_scale
from boec.variance_reduction import greedy_ivr

__all__ = [
    "SpadeCampaignResult",
    "SpadeConfig",
    "run_qlognei48",
    "run_sobol48",
    "run_spade",
]


Policy = Literal["staged", "fixed_hybrid", "validity_gated"]
Objective = Literal["sobol_opening", "sobol48", "qlognei", "global_ivr", "boundary_ivr"]

_BUDGET = 48
_BATCH_SIZE = 4
_OPENINGS = frozenset({32, 40, 44})
_POLICIES = frozenset({"staged", "fixed_hybrid", "validity_gated"})


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 1:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return int(value)


def _nonnegative_seed(value: object, name: str = "root_seed") -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, Integral)
        or int(value) < 0
        or int(value) >= 2**63
    ):
        raise ValueError(f"{name} must be an integer in [0, 2**63), got {value!r}")
    return int(value)


def _finite_real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result


@dataclass(frozen=True)
class SpadeConfig:
    """Complete, digestible configuration of one registered SPADE campaign."""

    opening: int = 40
    policy: Policy = "fixed_hybrid"
    root_seed: int = 0
    budget: int = _BUDGET
    batch_size: int = _BATCH_SIZE
    candidate_menu_size: int = 16_384
    reference_grid_size: int = 2_048
    fit_restarts: int = 4
    qlognei_mc_samples: int = 256
    gamma: float = 0.95
    boundary_ess_min: float = 32.0

    def __post_init__(self) -> None:
        if isinstance(self.opening, bool) or self.opening not in _OPENINGS:
            raise ValueError(
                f"opening must be one of {sorted(_OPENINGS)}, got {self.opening!r}"
            )
        if self.policy not in _POLICIES:
            raise ValueError(
                f"policy must be one of {sorted(_POLICIES)}, got {self.policy!r}"
            )
        if isinstance(self.budget, bool) or self.budget != _BUDGET:
            raise ValueError(f"budget is registered at exactly {_BUDGET}, got {self.budget!r}")
        if isinstance(self.batch_size, bool) or self.batch_size != _BATCH_SIZE:
            raise ValueError(
                f"batch_size is registered at exactly {_BATCH_SIZE}, got {self.batch_size!r}"
            )
        if (self.budget - self.opening) % self.batch_size:
            raise ValueError("opening must leave only complete adaptive batches")

        menu_size = _positive_integer(self.candidate_menu_size, "candidate_menu_size")
        reference_size = _positive_integer(self.reference_grid_size, "reference_grid_size")
        _positive_integer(self.fit_restarts, "fit_restarts")
        _positive_integer(self.qlognei_mc_samples, "qlognei_mc_samples")
        if menu_size < self.budget - min(_OPENINGS):
            raise ValueError("candidate_menu_size cannot cover the largest adaptive budget")
        gamma = _finite_real(self.gamma, "gamma")
        if not 0.0 < gamma < 1.0:
            raise ValueError(f"gamma must lie strictly between 0 and 1, got {gamma}")
        ess_min = _finite_real(self.boundary_ess_min, "boundary_ess_min")
        if ess_min <= 0:
            raise ValueError("boundary_ess_min must be positive")
        if ess_min > reference_size:
            raise ValueError("boundary_ess_min cannot exceed reference_grid_size")
        _nonnegative_seed(self.root_seed)

    @property
    def canonical_json(self) -> str:
        """Canonical sorted representation used for audit and hashing."""
        return json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @property
    def protocol_digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SpadeRoundLog:
    """Everything known when a batch was selected, before its outcomes existed."""

    round_index: int
    n_train_before: int
    scheduled_objective: str
    objective: Objective
    X_proposed: Tensor
    posterior_mean: Tensor | None
    posterior_variance: Tensor | None
    objective_values: tuple[float, ...] | None
    gp_fit_seed: int | None
    qmc_seed: int | None
    fit_diagnostics: tuple[tuple[tuple[str, object], ...], ...]
    reliable_count: int | None = None
    boundary_ess: float | None = None
    gate_eligible: bool | None = None
    Y_observed: None = None


@dataclass(frozen=True)
class SpadeCampaignResult:
    """Raw campaign observations plus its terminal common surrogate."""

    arm: str
    protocol_digest: str
    config: SpadeConfig | None
    X: Tensor
    Y: Tensor
    Yvar: Tensor
    round_logs: tuple[SpadeRoundLog, ...]
    terminal_model: object
    terminal_fit_seed: int
    terminal_fit_diagnostics: tuple[tuple[tuple[str, object], ...], ...]

    def __post_init__(self) -> None:
        if self.X.ndim != 2 or self.X.shape[0] != _BUDGET:
            raise ValueError(f"campaign result must contain exactly {_BUDGET} X rows")
        if self.Y.shape != (_BUDGET, 1) or self.Yvar.shape != (_BUDGET, 1):
            raise ValueError("campaign result outcomes must both have shape (48, 1)")
        if torch.unique(self.X, dim=0).shape[0] != _BUDGET:
            raise ValueError("campaign result contains duplicate evaluation rows")
        logged_evaluations = sum(log.X_proposed.shape[0] for log in self.round_logs)
        if not self.round_logs or logged_evaluations != _BUDGET:
            raise ValueError("round logs do not account for the exact 48-evaluation budget")

    @property
    def rounds(self) -> int:
        return len(self.round_logs)


@dataclass(frozen=True)
class _RuntimeConfig:
    candidate_menu_size: int
    reference_grid_size: int
    fit_restarts: int
    qlognei_mc_samples: int


def _runtime(config: SpadeConfig, fast: bool) -> _RuntimeConfig:
    if not isinstance(fast, bool):
        raise ValueError(f"fast must be boolean, got {fast!r}")
    if not fast:
        return _RuntimeConfig(
            config.candidate_menu_size,
            config.reference_grid_size,
            config.fit_restarts,
            config.qlognei_mc_samples,
        )
    return _RuntimeConfig(
        min(config.candidate_menu_size, 64),
        min(config.reference_grid_size, 64),
        1,
        min(config.qlognei_mc_samples, 16),
    )


def _validate_bounds(bounds: Tensor) -> Tensor:
    if not isinstance(bounds, Tensor) or bounds.ndim != 2 or bounds.shape[0] != 2:
        shape = tuple(bounds.shape) if isinstance(bounds, Tensor) else type(bounds).__name__
        raise ValueError(f"bounds must have shape (2, d), got {shape}")
    result = bounds.detach().double()
    if result.shape[1] < 1:
        raise ValueError("bounds must contain at least one factor")
    if not bool(torch.isfinite(result).all()) or not bool(torch.all(result[1] > result[0])):
        raise ValueError("bounds must be finite with every upper bound above its lower bound")
    return result


def _freeze_fit_diagnostics(model: object) -> tuple[tuple[tuple[str, object], ...], ...]:
    rows = getattr(model, "_boec_fit_diagnostics", ())
    return tuple(tuple(sorted(dict(row).items())) for row in rows)


def _posterior_diagnostics(model: object, X: Tensor) -> tuple[Tensor, Tensor]:
    model.eval()
    with torch.no_grad():
        posterior = model.posterior(X.double(), observation_noise=False)
        mean = posterior.mean.detach().double().clone()
        variance = posterior.variance.detach().double().clone()
    if mean.shape != (X.shape[0], 1) or variance.shape != (X.shape[0], 1):
        raise ValueError("common surrogate must return one posterior outcome per proposal")
    if not bool(torch.isfinite(mean).all()) or not bool(torch.isfinite(variance).all()):
        raise RuntimeError("pre-outcome posterior diagnostics contain nonfinite values")
    return mean, variance


def _remove_rows(menu: Tensor, rows: Tensor) -> Tensor:
    if rows.numel() == 0:
        return menu
    keep = torch.ones(menu.shape[0], dtype=torch.bool, device=menu.device)
    for row in rows:
        keep &= ~torch.all(menu == row.to(menu), dim=1)
    return menu[keep]


def _remove_selected(menu: Tensor, selected: Tensor) -> Tensor:
    if torch.unique(selected, dim=0).shape[0] != selected.shape[0]:
        raise RuntimeError("adaptive objective proposed duplicate rows within one batch")
    keep = torch.ones(menu.shape[0], dtype=torch.bool, device=menu.device)
    for row in selected:
        matched = torch.all(menu == row.to(menu), dim=1)
        if int(matched.sum()) != 1:
            raise RuntimeError("adaptive proposal was not a unique row of the locked menu")
        keep &= ~matched
    return menu[keep]


def _common_protocol_digest(arm: str, root_seed: int) -> str:
    payload = {
        "arm": arm,
        "batch_size": _BATCH_SIZE,
        "budget": _BUDGET,
        "candidate_menu_size": 16_384,
        "fit_restarts": 4,
        "model": "learned_noise_matern52_ard",
        "qlognei_mc_samples": 256,
        "reference_grid_size": 2_048,
        "root_seed": _nonnegative_seed(root_seed),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class _CampaignEngine:
    def __init__(
        self,
        evaluator: object,
        bounds: Tensor,
        root_seed: int,
        runtime: _RuntimeConfig,
    ) -> None:
        evaluate = getattr(evaluator, "evaluate", None)
        if not callable(evaluate):
            raise TypeError("evaluator must expose evaluate(X)")
        self.evaluator = evaluator
        self.bounds = _validate_bounds(bounds)
        self.root_seed = _nonnegative_seed(root_seed)
        self.runtime = runtime
        self.X = torch.empty((0, self.bounds.shape[1]), dtype=torch.double)
        self.Y = torch.empty((0, 1), dtype=torch.double)
        self.Yvar = torch.empty((0, 1), dtype=torch.double)
        self.logs: list[SpadeRoundLog] = []

    @property
    def n(self) -> int:
        return self.X.shape[0]

    def seed(self, label: str, *parts: object) -> int:
        return derive_seed(self.root_seed, label, *parts)

    def fit(self) -> tuple[object, int]:
        if self.n < 1:
            raise RuntimeError("cannot fit before the opening has been evaluated")
        fit_seed = self.seed("gp_fit", self.n)
        model = build_learned_noise_gp(
            self.X,
            self.Y,
            self.bounds,
            fit_restarts=self.runtime.fit_restarts,
            seed=fit_seed,
        )
        return model, fit_seed

    def evaluate(self, X: Tensor, log: SpadeRoundLog) -> None:
        proposed = X.detach().double().clone()
        if proposed.ndim != 2 or proposed.shape[1] != self.bounds.shape[1]:
            raise ValueError("proposed batch must have shape (q, d)")
        if proposed.shape[0] < 1 or self.n + proposed.shape[0] > _BUDGET:
            raise ValueError("proposed batch would violate the exact 48-evaluation budget")
        if not bool(torch.isfinite(proposed).all()):
            raise ValueError("proposed points must be finite")
        if bool(torch.any(proposed < self.bounds[0])) or bool(torch.any(proposed > self.bounds[1])):
            raise ValueError("proposed points must lie inside bounds")
        combined = torch.cat([self.X, proposed])
        if torch.unique(combined, dim=0).shape[0] != combined.shape[0]:
            raise ValueError("campaign cannot evaluate a duplicate point")

        # The complete decision record is frozen before the evaluator is called.
        self.logs.append(log)
        response = self.evaluator.evaluate(proposed)
        if not isinstance(response, tuple) or len(response) != 2:
            raise ValueError("evaluator must return the tuple (Y, Yvar)")
        Y, Yvar = response
        if not isinstance(Y, Tensor) or not isinstance(Yvar, Tensor):
            raise ValueError("evaluator Y and Yvar must both be tensors")
        Y = Y.detach().double()
        Yvar = Yvar.detach().double()
        expected = (proposed.shape[0], 1)
        if Y.shape != expected or Yvar.shape != expected:
            raise ValueError(
                f"evaluator outcomes must both have shape {expected}, got "
                f"{tuple(Y.shape)} and {tuple(Yvar.shape)}"
            )
        if not bool(torch.isfinite(Y).all()) or not bool(torch.isfinite(Yvar).all()):
            raise ValueError("evaluator outcomes must be finite")
        if bool(torch.any(Yvar < 0)):
            raise ValueError("evaluator Yvar cannot be negative")
        self.X = combined
        self.Y = torch.cat([self.Y, Y])
        self.Yvar = torch.cat([self.Yvar, Yvar])

    def opening(self, n: int, objective: Objective) -> None:
        X = sobol_design(self.bounds, n, seed=self.seed("opening_design"))
        self.evaluate(
            X,
            SpadeRoundLog(
                round_index=0,
                n_train_before=0,
                scheduled_objective=objective,
                objective=objective,
                X_proposed=X.clone(),
                posterior_mean=None,
                posterior_variance=None,
                objective_values=None,
                gp_fit_seed=None,
                qmc_seed=None,
                fit_diagnostics=(),
            ),
        )

    def result(
        self,
        arm: str,
        protocol_digest: str,
        config: SpadeConfig | None,
    ) -> SpadeCampaignResult:
        if self.n != _BUDGET:
            raise RuntimeError(f"campaign stopped at {self.n}, not the exact budget of 48")
        terminal_model, terminal_fit_seed = self.fit()
        return SpadeCampaignResult(
            arm=arm,
            protocol_digest=protocol_digest,
            config=config,
            X=self.X.clone(),
            Y=self.Y.clone(),
            Yvar=self.Yvar.clone(),
            round_logs=tuple(self.logs),
            terminal_model=terminal_model,
            terminal_fit_seed=terminal_fit_seed,
            terminal_fit_diagnostics=_freeze_fit_diagnostics(terminal_model),
        )


def _qlognei_batch(
    engine: _CampaignEngine,
    model: object,
    menu: Tensor,
    q: int,
) -> tuple[Tensor, tuple[float, ...], int]:
    qmc_seed = engine.seed("qlognei_qmc", engine.n)
    acq_config = AcqConfig(
        kind="qlognei",
        mc_samples=engine.runtime.qlognei_mc_samples,
        sampler_seed=qmc_seed,
    )
    selected = propose(
        model,
        engine.bounds,
        q,
        engine.X,
        engine.Y,
        config=acq_config,
        candidates=menu,
    ).detach().double()
    # One qLogNEI value describes the complete q-point batch objective.
    acquisition = make_acquisition(
        model, engine.X, engine.Y, config=acq_config
    )
    with torch.no_grad():
        objective = acquisition(selected.unsqueeze(0)).detach().double().reshape(-1)
    values = tuple(float(value) for value in objective)
    if not values or not all(math.isfinite(value) for value in values):
        raise RuntimeError("qLogNEI selected a batch with a nonfinite objective")
    return selected, values, qmc_seed


def _normalized_weights(reference: Tensor, weights: Tensor | None) -> Tensor:
    if weights is None:
        return torch.ones(reference.shape[0], dtype=torch.double, device=reference.device)
    result = weights.detach().double().to(reference)
    result = result / result.max()
    result = result / result.mean()
    return result


def _selected_ivr_values(
    model: object,
    selected: Tensor,
    reference: Tensor,
    weights: Tensor | None,
) -> tuple[float, ...]:
    """Exact sequential IVR scores for the already-selected batch."""
    model.eval()
    joint = torch.cat([reference.double(), selected.double()])
    with torch.no_grad():
        covariance = (
            model.posterior(joint, observation_noise=False)
            .mvn.covariance_matrix.detach().double().clone()
        )
    n_reference = reference.shape[0]
    cross = covariance[:n_reference, n_reference:]
    candidate_covariance = covariance[n_reference:, n_reference:]
    learned_noise = model.likelihood.noise.detach().double().reshape(-1)
    scale = outcome_scale(model).detach().double().reshape(-1)
    if learned_noise.numel() != 1 or scale.numel() != 1:
        raise ValueError("IVR logging requires one learned likelihood-noise value")
    observation_noise = learned_noise[0] * scale[0].square()
    normalized_weights = _normalized_weights(reference, weights)
    values: list[float] = []
    for _ in range(selected.shape[0]):
        denominator = candidate_covariance[0, 0] + observation_noise
        score = (normalized_weights * cross[:, 0].square()).sum() / denominator
        value = float(score)
        if not math.isfinite(value):
            raise RuntimeError("IVR selected a batch with a nonfinite objective")
        values.append(value)
        if candidate_covariance.shape[0] == 1:
            break
        selected_reference_cross = cross[:, 0].clone()
        selected_candidate_cross = candidate_covariance[0, 1:].clone()
        kept_to_selected = candidate_covariance[1:, 0].clone()
        cross = (
            cross[:, 1:]
            - selected_reference_cross[:, None]
            * selected_candidate_cross[None, :]
            / denominator
        )
        candidate_covariance = (
            candidate_covariance[1:, 1:]
            - kept_to_selected[:, None]
            * selected_candidate_cross[None, :]
            / denominator
        )
        candidate_covariance = (
            candidate_covariance + candidate_covariance.transpose(-1, -2)
        ) / 2
    return tuple(values)


def _adaptive_log(
    *,
    engine: _CampaignEngine,
    model: object,
    fit_seed: int,
    scheduled_objective: str,
    objective: Objective,
    selected: Tensor,
    objective_values: tuple[float, ...],
    qmc_seed: int | None,
    reliable_count: int | None = None,
    boundary_ess: float | None = None,
    gate_eligible: bool | None = None,
) -> SpadeRoundLog:
    mean, variance = _posterior_diagnostics(model, selected)
    return SpadeRoundLog(
        round_index=len(engine.logs),
        n_train_before=engine.n,
        scheduled_objective=scheduled_objective,
        objective=objective,
        X_proposed=selected.clone(),
        posterior_mean=mean,
        posterior_variance=variance,
        objective_values=objective_values,
        gp_fit_seed=fit_seed,
        qmc_seed=qmc_seed,
        fit_diagnostics=_freeze_fit_diagnostics(model),
        reliable_count=reliable_count,
        boundary_ess=boundary_ess,
        gate_eligible=gate_eligible,
    )


def run_spade(
    evaluator: object,
    bounds: Tensor,
    config: SpadeConfig,
    *,
    tau: float | None = None,
    fast: bool = False,
) -> SpadeCampaignResult:
    """Run one registered SPADE candidate without access to scoring truth."""
    if not isinstance(config, SpadeConfig):
        raise TypeError("config must be a SpadeConfig")
    if config.policy == "validity_gated" and tau is None:
        raise ValueError("tau is required for the validity_gated policy")
    tau_f = _finite_real(tau, "tau") if tau is not None else None
    runtime = _runtime(config, fast)
    engine = _CampaignEngine(evaluator, bounds, config.root_seed, runtime)
    engine.opening(config.opening, "sobol_opening")

    menu = sobol_design(
        engine.bounds,
        runtime.candidate_menu_size,
        seed=engine.seed("adaptive_candidate_menu"),
    )
    menu = _remove_rows(menu, engine.X)
    reference = sobol_design(
        engine.bounds,
        runtime.reference_grid_size,
        seed=engine.seed("ivr_reference_grid"),
    )

    n_batches = (config.budget - config.opening) // config.batch_size
    for batch_index in range(n_batches):
        model, fit_seed = engine.fit()
        if config.policy == "staged" or batch_index % 2 == 0:
            scheduled = "qlognei"
        elif config.policy == "fixed_hybrid":
            scheduled = "global_ivr"
        else:
            scheduled = "map"
        reliable_count: int | None = None
        boundary_ess: float | None = None
        gate_eligible: bool | None = None
        weights: Tensor | None = None
        qmc_seed: int | None = None

        if config.policy == "staged" or batch_index % 2 == 0:
            objective: Objective = "qlognei"
            selected, objective_values, qmc_seed = _qlognei_batch(
                engine, model, menu, config.batch_size
            )
        else:
            objective = "global_ivr"
            if config.policy == "validity_gated":
                assert tau_f is not None
                probability = model_reliability_probability(model, reference, tau_f)
                if probability.shape != (reference.shape[0],):
                    raise ValueError("reliability probability must have one value per reference")
                if not bool(torch.isfinite(probability).all()) or bool(
                    torch.any((probability < 0) | (probability > 1))
                ):
                    raise RuntimeError("reliability probabilities must be finite in [0, 1]")
                boundary_weights = probability * (1.0 - probability)
                sum_weights = boundary_weights.sum()
                sum_squares = boundary_weights.square().sum()
                boundary_ess = (
                    float(sum_weights.square() / sum_squares)
                    if float(sum_squares) > 0.0
                    else 0.0
                )
                reliable_count = int((probability >= config.gamma).sum())
                gate_eligible = (
                    reliable_count > 0 and boundary_ess >= config.boundary_ess_min
                )
                if gate_eligible:
                    objective = "boundary_ivr"
                    weights = boundary_weights
            selected = greedy_ivr(
                model,
                menu,
                reference,
                config.batch_size,
                weights=weights,
            ).detach().double()
            objective_values = _selected_ivr_values(
                model, selected, reference, weights
            )

        log = _adaptive_log(
            engine=engine,
            model=model,
            fit_seed=fit_seed,
            scheduled_objective=scheduled,
            objective=objective,
            selected=selected,
            objective_values=objective_values,
            qmc_seed=qmc_seed,
            reliable_count=reliable_count,
            boundary_ess=boundary_ess,
            gate_eligible=gate_eligible,
        )
        menu = _remove_selected(menu, selected)
        engine.evaluate(selected, log)

    return engine.result("spade", config.protocol_digest, config)


def run_sobol48(
    evaluator: object,
    bounds: Tensor,
    *,
    root_seed: int = 0,
    fast: bool = False,
) -> SpadeCampaignResult:
    """Run the one-shot scrambled-Sobol specialist comparator."""
    common = SpadeConfig(root_seed=_nonnegative_seed(root_seed))
    engine = _CampaignEngine(evaluator, bounds, root_seed, _runtime(common, fast))
    engine.opening(_BUDGET, "sobol48")
    return engine.result(
        "sobol48", _common_protocol_digest("sobol48", root_seed), None
    )


def run_qlognei48(
    evaluator: object,
    bounds: Tensor,
    *,
    root_seed: int = 0,
    fast: bool = False,
) -> SpadeCampaignResult:
    """Run the registered 14 + 8x4 + 2 discrete qLogNEI comparator."""
    common = SpadeConfig(root_seed=_nonnegative_seed(root_seed))
    runtime = _runtime(common, fast)
    engine = _CampaignEngine(evaluator, bounds, root_seed, runtime)
    engine.opening(14, "sobol_opening")
    menu = sobol_design(
        engine.bounds,
        runtime.candidate_menu_size,
        seed=engine.seed("adaptive_candidate_menu"),
    )
    menu = _remove_rows(menu, engine.X)

    for q in [4] * 8 + [2]:
        model, fit_seed = engine.fit()
        selected, objective_values, qmc_seed = _qlognei_batch(
            engine, model, menu, q
        )
        log = _adaptive_log(
            engine=engine,
            model=model,
            fit_seed=fit_seed,
            scheduled_objective="qlognei",
            objective="qlognei",
            selected=selected,
            objective_values=objective_values,
            qmc_seed=qmc_seed,
        )
        menu = _remove_selected(menu, selected)
        engine.evaluate(selected, log)

    return engine.result(
        "qlognei48", _common_protocol_digest("qlognei48", root_seed), None
    )
