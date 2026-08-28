"""The unified, exactly-48-evaluation SPADE campaign protocol.

This module makes campaign decisions from observations only.  Oracle truth and all
scoring functions deliberately live outside its public interfaces.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from numbers import Integral, Real
from typing import Literal

import torch
from torch import Tensor

from boec.certstraddle import batch_lse_rho, certificate_straddle, rho_contour_offset
from boec.designspace import gp_adapter
from boec.optimizers import AcqConfig, make_acquisition, propose, sobol_design
from boec.reliable_region import _learned_noise_variance, model_reliability_probability
from boec.seedbook import derive_seed
from boec.surrogate import build_learned_noise_gp, outcome_scale
from boec.variance_reduction import greedy_ivr

__all__ = [
    "SpadeCampaignResult",
    "SpadeConfig",
    "SpadeExecutionSettings",
    "run_qlognei48",
    "run_sobol48",
    "run_spade",
]


Policy = Literal["staged", "fixed_hybrid", "validity_gated", "certificate_targeted"]
Objective = Literal[
    "sobol_opening", "sobol48", "qlognei", "global_ivr", "boundary_ivr",
    "certificate_straddle",
]

_BUDGET = 48
_BATCH_SIZE = 4
_CANDIDATE_MENU_SIZE = 16_384
_REFERENCE_GRID_SIZE = 2_048
_FIT_RESTARTS = 4
_QLOGNEI_MC_SAMPLES = 256
_GAMMA = 0.95
_BOUNDARY_ESS_MIN = 32
_OPENINGS = frozenset({32, 40, 44})
_POLICIES = frozenset(
    {"staged", "fixed_hybrid", "validity_gated", "certificate_targeted"}
)
#: Vorob'ev level whose contour ``certificate_targeted`` straddles.
_CERTIFICATE_RHO = 0.5
_EXECUTION_MODES = frozenset({"REGISTERED", "TEST_ONLY"})
_CPU_RNG_LOCK = threading.RLock()


def _reliability_contour(model: object, tau: float, gamma: float) -> float:
    """Latent ``theta`` with ``P(Y >= tau | f = theta) == gamma``."""
    variance = _learned_noise_variance(model)
    return float(tau) + rho_contour_offset(float(gamma)) * float(variance.sqrt())


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    return int(value)


def _positive_integer(value: object, name: str) -> int:
    result = _integer(value, name)
    if result < 1:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return result


def _nonnegative_seed(value: object, name: str = "root_seed") -> int:
    result = _integer(value, name)
    if result < 0 or result >= 2**63:
        raise ValueError(f"{name} must be an integer in [0, 2**63), got {value!r}")
    return result


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
    candidate_menu_size: int = _CANDIDATE_MENU_SIZE
    reference_grid_size: int = _REFERENCE_GRID_SIZE
    fit_restarts: int = _FIT_RESTARTS
    qlognei_mc_samples: int = _QLOGNEI_MC_SAMPLES
    gamma: float = _GAMMA
    boundary_ess_min: int = _BOUNDARY_ESS_MIN
    certificate_rho: float = _CERTIFICATE_RHO

    def __post_init__(self) -> None:
        opening = _integer(self.opening, "opening")
        budget = _integer(self.budget, "budget")
        batch_size = _integer(self.batch_size, "batch_size")
        menu_size = _integer(self.candidate_menu_size, "candidate_menu_size")
        reference_size = _integer(self.reference_grid_size, "reference_grid_size")
        fit_restarts = _integer(self.fit_restarts, "fit_restarts")
        mc_samples = _integer(self.qlognei_mc_samples, "qlognei_mc_samples")
        ess_min = _integer(self.boundary_ess_min, "boundary_ess_min")
        root_seed = _nonnegative_seed(self.root_seed)
        gamma = _finite_real(self.gamma, "gamma")
        certificate_rho = _finite_real(self.certificate_rho, "certificate_rho")
        if not 0.0 < certificate_rho < 1.0:
            raise ValueError(
                "certificate_rho must lie strictly between 0 and 1, got "
                f"{certificate_rho!r}"
            )

        if opening not in _OPENINGS:
            raise ValueError(
                f"opening must be one of {sorted(_OPENINGS)}, got {opening!r}"
            )
        if self.policy not in _POLICIES:
            raise ValueError(
                f"policy must be one of {sorted(_POLICIES)}, got {self.policy!r}"
            )
        if budget != _BUDGET:
            raise ValueError(f"budget is registered at exactly {_BUDGET}, got {budget!r}")
        if batch_size != _BATCH_SIZE:
            raise ValueError(
                f"batch_size is registered at exactly {_BATCH_SIZE}, got {batch_size!r}"
            )
        if menu_size != _CANDIDATE_MENU_SIZE:
            raise ValueError(
                "candidate_menu_size is registered at exactly "
                f"{_CANDIDATE_MENU_SIZE}, got {menu_size!r}"
            )
        if reference_size != _REFERENCE_GRID_SIZE:
            raise ValueError(
                "reference_grid_size is registered at exactly "
                f"{_REFERENCE_GRID_SIZE}, got {reference_size!r}"
            )
        if fit_restarts != _FIT_RESTARTS:
            raise ValueError(
                f"fit_restarts is registered at exactly {_FIT_RESTARTS}, "
                f"got {fit_restarts!r}"
            )
        if mc_samples != _QLOGNEI_MC_SAMPLES:
            raise ValueError(
                "qlognei_mc_samples is registered at exactly "
                f"{_QLOGNEI_MC_SAMPLES}, got {mc_samples!r}"
            )
        if gamma != _GAMMA:
            raise ValueError(f"gamma is registered at exactly {_GAMMA}, got {gamma!r}")
        if ess_min != _BOUNDARY_ESS_MIN:
            raise ValueError(
                "boundary_ess_min is registered at exactly "
                f"{_BOUNDARY_ESS_MIN}, got {ess_min!r}"
            )
        if (budget - opening) % batch_size:
            raise ValueError("opening must leave only complete adaptive batches")

        # Normalize non-bool Integral implementations before canonical JSON hashing.
        for field_name, value in (
            ("opening", opening),
            ("root_seed", root_seed),
            ("budget", budget),
            ("batch_size", batch_size),
            ("candidate_menu_size", menu_size),
            ("reference_grid_size", reference_size),
            ("fit_restarts", fit_restarts),
            ("qlognei_mc_samples", mc_samples),
            ("gamma", gamma),
            ("boundary_ess_min", ess_min),
            ("certificate_rho", certificate_rho),
        ):
            object.__setattr__(self, field_name, value)

    @property
    def canonical_json(self) -> str:
        """Canonical sorted representation used for audit and hashing."""
        payload = asdict(self)
        if self.policy != "certificate_targeted":
            payload.pop("certificate_rho", None)
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @property
    def protocol_digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SpadeExecutionSettings:
    """Effective numerical settings of one execution, registered or test-only."""

    candidate_menu_size: int
    reference_grid_size: int
    fit_restarts: int
    qlognei_mc_samples: int

    def __post_init__(self) -> None:
        for name in (
            "candidate_menu_size",
            "reference_grid_size",
            "fit_restarts",
            "qlognei_mc_samples",
        ):
            value = _positive_integer(getattr(self, name), name)
            object.__setattr__(self, name, value)


def _registered_settings() -> SpadeExecutionSettings:
    return SpadeExecutionSettings(
        candidate_menu_size=_CANDIDATE_MENU_SIZE,
        reference_grid_size=_REFERENCE_GRID_SIZE,
        fit_restarts=_FIT_RESTARTS,
        qlognei_mc_samples=_QLOGNEI_MC_SAMPLES,
    )


@dataclass(frozen=True)
class _RunIdentity:
    arm: str
    protocol_digest: str
    run_digest: str
    execution_mode: str
    registered: bool
    tau: float
    root_seed: int
    opening: int
    batch_schedule: tuple[int, ...]
    effective_settings: SpadeExecutionSettings


@dataclass(frozen=True)
class SpadeRoundLog:
    """Everything known when a batch was selected, before its outcomes existed."""

    arm: str
    protocol_digest: str
    run_digest: str
    execution_mode: str
    registered: bool
    tau: float
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
    run_digest: str
    execution_mode: str
    registered: bool
    tau: float
    root_seed: int
    opening: int
    batch_schedule: tuple[int, ...]
    effective_settings: SpadeExecutionSettings
    config: SpadeConfig | None
    X: Tensor
    Y: Tensor
    Yvar: Tensor
    round_logs: tuple[SpadeRoundLog, ...]
    terminal_model: object
    terminal_fit_seed: int
    terminal_fit_diagnostics: tuple[tuple[tuple[str, object], ...], ...]

    def __post_init__(self) -> None:
        if self.execution_mode not in _EXECUTION_MODES:
            raise ValueError(f"unknown execution_mode {self.execution_mode!r}")
        if not isinstance(self.registered, bool):
            raise ValueError("registered must be boolean")
        expected_registered = self.execution_mode == "REGISTERED"
        if self.registered is not expected_registered:
            raise ValueError("registered flag does not match execution_mode")
        registered_settings = _registered_settings()
        if self.registered and self.effective_settings != registered_settings:
            raise ValueError("REGISTERED result does not use all registered settings")
        if not self.registered and self.effective_settings == registered_settings:
            raise ValueError("TEST_ONLY result must expose its reduced effective settings")

        tau = _finite_real(self.tau, "tau")
        root_seed = _nonnegative_seed(self.root_seed)
        opening = _positive_integer(self.opening, "opening")
        schedule = _validate_schedule(self.batch_schedule, opening)
        expected_run_digest = _run_digest(
            protocol_digest=self.protocol_digest,
            arm=self.arm,
            tau=tau,
            opening=opening,
            batch_schedule=schedule,
            execution_mode=self.execution_mode,
            effective_settings=self.effective_settings,
        )
        if self.run_digest != expected_run_digest:
            raise ValueError("run_digest does not match immutable campaign identity")

        if self.arm == "spade":
            if self.config is None:
                raise ValueError("SPADE result must retain its SpadeConfig")
            if self.protocol_digest != self.config.protocol_digest:
                raise ValueError("SPADE result protocol_digest does not match config")
            if root_seed != self.config.root_seed or opening != self.config.opening:
                raise ValueError("SPADE result seed/opening does not match config")
        else:
            if self.config is not None:
                raise ValueError("comparator result cannot carry a SPADE config")
            expected_protocol = _common_protocol_digest(
                self.arm, root_seed, opening, schedule
            )
            if self.protocol_digest != expected_protocol:
                raise ValueError("comparator protocol_digest does not match arm schedule")

        if self.X.ndim != 2 or self.X.shape[0] != _BUDGET:
            raise ValueError(f"campaign result must contain exactly {_BUDGET} X rows")
        if self.Y.shape != (_BUDGET, 1) or self.Yvar.shape != (_BUDGET, 1):
            raise ValueError("campaign result outcomes must both have shape (48, 1)")
        if torch.unique(self.X, dim=0).shape[0] != _BUDGET:
            raise ValueError("campaign result contains duplicate evaluation rows")
        logged_evaluations = sum(log.X_proposed.shape[0] for log in self.round_logs)
        if not self.round_logs or logged_evaluations != _BUDGET:
            raise ValueError("round logs do not account for the exact 48-evaluation budget")
        for log in self.round_logs:
            if (
                log.arm != self.arm
                or log.protocol_digest != self.protocol_digest
                or log.run_digest != self.run_digest
                or log.execution_mode != self.execution_mode
                or log.registered is not self.registered
                or log.tau != tau
            ):
                raise ValueError("round log identity does not match campaign result")

    @property
    def rounds(self) -> int:
        return len(self.round_logs)


def _runtime(config: SpadeConfig, fast: bool) -> SpadeExecutionSettings:
    if not isinstance(fast, bool):
        raise ValueError(f"fast must be boolean, got {fast!r}")
    if not fast:
        return SpadeExecutionSettings(
            config.candidate_menu_size,
            config.reference_grid_size,
            config.fit_restarts,
            config.qlognei_mc_samples,
        )
    return SpadeExecutionSettings(
        64,
        64,
        1,
        16,
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


def _validate_schedule(schedule: object, opening: int) -> tuple[int, ...]:
    if not isinstance(schedule, tuple) or not schedule:
        raise ValueError("batch_schedule must be a non-empty tuple of integers")
    values = tuple(_positive_integer(value, "batch_schedule") for value in schedule)
    if values[0] != opening:
        raise ValueError("batch_schedule must begin with opening")
    if sum(values) != _BUDGET:
        raise ValueError("batch_schedule must total exactly 48 evaluations")
    return values


def _sha256_json(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _common_protocol_digest(
    arm: str,
    root_seed: int,
    opening: int,
    batch_schedule: tuple[int, ...],
) -> str:
    root_seed = _nonnegative_seed(root_seed)
    opening = _positive_integer(opening, "opening")
    schedule = _validate_schedule(batch_schedule, opening)
    if arm == "sobol48" and schedule != (_BUDGET,):
        raise ValueError("sobol48 protocol requires the one-batch (48,) schedule")
    if arm == "qlognei48" and schedule != (14, *([4] * 8), 2):
        raise ValueError("qlognei48 protocol requires the 14 + 8x4 + 2 schedule")
    if arm not in {"sobol48", "qlognei48"}:
        raise ValueError(f"unknown comparator arm {arm!r}")
    payload = {
        "schema": "boec-spade-comparator-protocol-v1",
        "arm": arm,
        "opening": opening,
        "batch_schedule": schedule,
        "batch_size": _BATCH_SIZE,
        "budget": _BUDGET,
        "candidate_menu_size": _CANDIDATE_MENU_SIZE,
        "fit_restarts": _FIT_RESTARTS,
        "model": "learned_noise_matern52_ard",
        "qlognei_mc_samples": _QLOGNEI_MC_SAMPLES,
        "reference_grid_size": _REFERENCE_GRID_SIZE,
        "root_seed": root_seed,
    }
    return _sha256_json(payload)


def _run_digest(
    *,
    protocol_digest: str,
    arm: str,
    tau: float,
    opening: int,
    batch_schedule: tuple[int, ...],
    execution_mode: str,
    effective_settings: SpadeExecutionSettings,
) -> str:
    if execution_mode not in _EXECUTION_MODES:
        raise ValueError(f"unknown execution_mode {execution_mode!r}")
    tau = _finite_real(tau, "tau")
    opening = _positive_integer(opening, "opening")
    schedule = _validate_schedule(batch_schedule, opening)
    return _sha256_json(
        {
            "schema": "boec-spade-run-v1",
            "protocol_digest": protocol_digest,
            "arm": arm,
            "tau_hex": tau.hex(),
            "opening": opening,
            "batch_schedule": schedule,
            "execution_mode": execution_mode,
            "registered": execution_mode == "REGISTERED",
            "effective_settings": asdict(effective_settings),
        }
    )


def _make_identity(
    *,
    arm: str,
    protocol_digest: str,
    tau: float,
    root_seed: int,
    opening: int,
    batch_schedule: tuple[int, ...],
    runtime: SpadeExecutionSettings,
    fast: bool,
) -> _RunIdentity:
    tau = _finite_real(tau, "tau")
    root_seed = _nonnegative_seed(root_seed)
    opening = _positive_integer(opening, "opening")
    schedule = _validate_schedule(batch_schedule, opening)
    execution_mode = "TEST_ONLY" if fast else "REGISTERED"
    return _RunIdentity(
        arm=arm,
        protocol_digest=protocol_digest,
        run_digest=_run_digest(
            protocol_digest=protocol_digest,
            arm=arm,
            tau=tau,
            opening=opening,
            batch_schedule=schedule,
            execution_mode=execution_mode,
            effective_settings=runtime,
        ),
        execution_mode=execution_mode,
        registered=not fast,
        tau=tau,
        root_seed=root_seed,
        opening=opening,
        batch_schedule=schedule,
        effective_settings=runtime,
    )


@contextmanager
def _preserve_ambient_cpu_rng():
    """Isolate CPU randomness without seeding any accelerator generator."""
    with _CPU_RNG_LOCK:
        state = torch.get_rng_state().clone()
        original_manual_seed = torch.manual_seed
        original_fork_rng = torch.random.fork_rng

        def cpu_only_manual_seed(seed: int):
            return torch.random.default_generator.manual_seed(int(seed))

        def cpu_only_fork_rng(
            devices=None,
            enabled=True,
            _caller="fork_rng",
            _devices_kw="devices",
            device_type=None,
        ):
            return original_fork_rng(
                devices=[],
                enabled=enabled,
                _caller=_caller,
                _devices_kw=_devices_kw,
                device_type=device_type,
            )

        torch.manual_seed = cpu_only_manual_seed
        torch.random.fork_rng = cpu_only_fork_rng
        try:
            yield
        finally:
            torch.random.fork_rng = original_fork_rng
            torch.manual_seed = original_manual_seed
            torch.set_rng_state(state)


class _CampaignEngine:
    def __init__(
        self,
        evaluator: object,
        bounds: Tensor,
        root_seed: int,
        runtime: SpadeExecutionSettings,
        identity: _RunIdentity,
    ) -> None:
        evaluate = getattr(evaluator, "evaluate", None)
        if not callable(evaluate):
            raise TypeError("evaluator must expose evaluate(X)")
        self.evaluator = evaluator
        self.bounds = _validate_bounds(bounds)
        self.root_seed = _nonnegative_seed(root_seed)
        self.runtime = runtime
        self.identity = identity
        if self.root_seed != identity.root_seed:
            raise ValueError("engine root_seed does not match run identity")
        if self.runtime != identity.effective_settings:
            raise ValueError("engine settings do not match run identity")
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
                arm=self.identity.arm,
                protocol_digest=self.identity.protocol_digest,
                run_digest=self.identity.run_digest,
                execution_mode=self.identity.execution_mode,
                registered=self.identity.registered,
                tau=self.identity.tau,
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
        config: SpadeConfig | None,
    ) -> SpadeCampaignResult:
        if self.n != _BUDGET:
            raise RuntimeError(f"campaign stopped at {self.n}, not the exact budget of 48")
        terminal_model, terminal_fit_seed = self.fit()
        return SpadeCampaignResult(
            arm=self.identity.arm,
            protocol_digest=self.identity.protocol_digest,
            run_digest=self.identity.run_digest,
            execution_mode=self.identity.execution_mode,
            registered=self.identity.registered,
            tau=self.identity.tau,
            root_seed=self.identity.root_seed,
            opening=self.identity.opening,
            batch_schedule=self.identity.batch_schedule,
            effective_settings=self.identity.effective_settings,
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
        arm=engine.identity.arm,
        protocol_digest=engine.identity.protocol_digest,
        run_digest=engine.identity.run_digest,
        execution_mode=engine.identity.execution_mode,
        registered=engine.identity.registered,
        tau=engine.identity.tau,
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


def _run_spade_impl(
    evaluator: object,
    bounds: Tensor,
    config: SpadeConfig,
    *,
    tau: float,
    fast: bool = False,
) -> SpadeCampaignResult:
    tau_f = _finite_real(tau, "tau")
    runtime = _runtime(config, fast)
    n_batches = (config.budget - config.opening) // config.batch_size
    schedule = (config.opening, *([config.batch_size] * n_batches))
    identity = _make_identity(
        arm="spade",
        protocol_digest=config.protocol_digest,
        tau=tau_f,
        root_seed=config.root_seed,
        opening=config.opening,
        batch_schedule=schedule,
        runtime=runtime,
        fast=fast,
    )
    engine = _CampaignEngine(
        evaluator, bounds, config.root_seed, runtime, identity
    )
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

    for batch_index in range(n_batches):
        model, fit_seed = engine.fit()
        if config.policy == "staged" or batch_index % 2 == 0:
            scheduled = "qlognei"
        elif config.policy == "fixed_hybrid":
            scheduled = "global_ivr"
        elif config.policy == "certificate_targeted":
            scheduled = "certificate_straddle"
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
        elif config.policy == "certificate_targeted":
            objective = "certificate_straddle"
            theta = _reliability_contour(model, tau_f, config.gamma)
            selected = batch_lse_rho(
                gp_adapter(model),
                menu,
                theta,
                config.batch_size,
                rho=config.certificate_rho,
            ).detach().double()
            mean_sel, sd_sel = gp_adapter(model).posterior_mean_and_sd(selected)
            objective_values = certificate_straddle(
                mean_sel, sd_sel, theta, config.certificate_rho
            ).detach().double()
        else:
            objective = "global_ivr"
            if config.policy == "validity_gated":
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

    return engine.result(config)


def run_sobol48(
    evaluator: object,
    bounds: Tensor,
    *,
    root_seed: int = 0,
    tau: float | None = None,
    fast: bool = False,
) -> SpadeCampaignResult:
    """Run the one-shot scrambled-Sobol specialist comparator."""
    if tau is None:
        raise ValueError("tau is required for campaign identity")
    with _preserve_ambient_cpu_rng():
        return _run_sobol48_impl(
            evaluator, bounds, root_seed=root_seed, tau=tau, fast=fast
        )


def run_spade(
    evaluator: object,
    bounds: Tensor,
    config: SpadeConfig,
    *,
    tau: float | None = None,
    fast: bool = False,
) -> SpadeCampaignResult:
    """Run one SPADE candidate without scoring truth or ambient RNG mutation."""
    if not isinstance(config, SpadeConfig):
        raise TypeError("config must be a SpadeConfig")
    if tau is None:
        raise ValueError("tau is required for campaign identity")
    with _preserve_ambient_cpu_rng():
        return _run_spade_impl(
            evaluator, bounds, config, tau=tau, fast=fast
        )


def _run_sobol48_impl(
    evaluator: object,
    bounds: Tensor,
    *,
    root_seed: int = 0,
    tau: float,
    fast: bool = False,
) -> SpadeCampaignResult:
    common = SpadeConfig(root_seed=_nonnegative_seed(root_seed))
    runtime = _runtime(common, fast)
    schedule = (_BUDGET,)
    protocol_digest = _common_protocol_digest(
        "sobol48", root_seed, _BUDGET, schedule
    )
    identity = _make_identity(
        arm="sobol48",
        protocol_digest=protocol_digest,
        tau=tau,
        root_seed=root_seed,
        opening=_BUDGET,
        batch_schedule=schedule,
        runtime=runtime,
        fast=fast,
    )
    engine = _CampaignEngine(evaluator, bounds, root_seed, runtime, identity)
    engine.opening(_BUDGET, "sobol48")
    return engine.result(None)


def run_qlognei48(
    evaluator: object,
    bounds: Tensor,
    *,
    root_seed: int = 0,
    tau: float | None = None,
    fast: bool = False,
) -> SpadeCampaignResult:
    """Run the registered 14 + 8x4 + 2 discrete qLogNEI comparator."""
    if tau is None:
        raise ValueError("tau is required for campaign identity")
    with _preserve_ambient_cpu_rng():
        return _run_qlognei48_impl(
            evaluator, bounds, root_seed=root_seed, tau=tau, fast=fast
        )


def _run_qlognei48_impl(
    evaluator: object,
    bounds: Tensor,
    *,
    root_seed: int = 0,
    tau: float,
    fast: bool = False,
) -> SpadeCampaignResult:
    common = SpadeConfig(root_seed=_nonnegative_seed(root_seed))
    runtime = _runtime(common, fast)
    schedule = (14, *([4] * 8), 2)
    protocol_digest = _common_protocol_digest(
        "qlognei48", root_seed, 14, schedule
    )
    identity = _make_identity(
        arm="qlognei48",
        protocol_digest=protocol_digest,
        tau=tau,
        root_seed=root_seed,
        opening=14,
        batch_schedule=schedule,
        runtime=runtime,
        fast=fast,
    )
    engine = _CampaignEngine(evaluator, bounds, root_seed, runtime, identity)
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

    return engine.result(None)
