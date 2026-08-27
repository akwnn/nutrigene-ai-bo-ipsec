"""Sealed thresholds, arm-neutral SPADE scoring, and deterministic study shards."""

from __future__ import annotations

import gzip
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
import tempfile
from dataclasses import asdict, dataclass
from numbers import Integral, Real
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import botorch
import gpytorch
import numpy as np
import scipy
import torch
from scipy.stats import norm, rankdata
from torch import Tensor

from boec.reliable_region import (
    ConservativeSetResult,
    conservative_set_split,
    empirical_set_containment,
    model_reliability_probability,
    reliable_set_draws,
    true_reliability_probability,
)
from boec.seedbook import derive_seed
from boec.selfcalib import calibration_inflation, calibration_tail, loo_residuals
from boec.surrogate import build_learned_noise_gp

__all__ = [
    "REGISTERED_SCORING_SETTINGS",
    "STUDY_ROW_SCHEMA",
    "ControlledThreshold",
    "ScoringExecutionSettings",
    "SealedOracleHarness",
    "StudyScore",
    "build_study_row",
    "collect_environment_provenance",
    "controlled_tau",
    "read_jsonl_gzip",
    "score_campaign",
    "sobol_grid",
    "write_jsonl_gzip",
]


STUDY_ROW_SCHEMA = "boec-spade-study-row-v1"
_EXECUTION_MODES = frozenset({"REGISTERED", "TEST_ONLY"})
_PRIMARY_DIM = 6
_PRIMARY_SIGMA_REL = 0.10
_PRIMARY_SIGMA_ADD = 0.01
_PRIMARY_GAMMA = 0.95
_PRIMARY_ALPHA = 0.95
_PRIMARY_Q_TAU = 0.75
_TRUTH_RANGE_CONTRACTS = frozenset({"strict_unit_interval", "legacy_unit_scaled"})


def _integer(value: object, name: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return result


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _probability(value: object, name: str) -> float:
    result = _finite(value, name)
    if not 0.0 < result < 1.0:
        raise ValueError(f"{name} must lie strictly between zero and one")
    return result


def _seed(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer in [0, 2**63)")
    result = int(value)
    if not 0 <= result < 2**63:
        raise ValueError(f"{name} must be an integer in [0, 2**63)")
    return result


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_json(payload: object) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _hex_digest(value: object, name: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length:
        raise ValueError(f"{name} must be a {length}-character hexadecimal digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value.lower()


@dataclass(frozen=True)
class ScoringExecutionSettings:
    calibration_grid_size: int
    terminal_grid_size: int
    map_grid_size: int
    certificate_grid_size: int
    certificate_draws: int
    certificate_rho_grid_size: int
    fit_restarts: int
    certificate_volume_rule: str = "smallest"
    predictive_observation_noise: str = "assay_relative_additive"
    latent_draw_inflation: str = "loo_calibration_tail"
    certificate_max_volume: float = 0.001
    latent_inflation_floor: float = 1.5

    def __post_init__(self) -> None:
        for field in (
            "calibration_grid_size",
            "terminal_grid_size",
            "map_grid_size",
            "certificate_grid_size",
            "certificate_draws",
            "certificate_rho_grid_size",
        ):
            object.__setattr__(self, field, _integer(getattr(self, field), field, minimum=2))
        object.__setattr__(
            self, "fit_restarts", _integer(self.fit_restarts, "fit_restarts", minimum=1)
        )
        if self.certificate_draws % 2:
            raise ValueError("certificate_draws must be even for the registered split")
        if self.certificate_volume_rule not in {"smallest", "largest"}:
            raise ValueError(
                "certificate_volume_rule must be 'smallest' or 'largest', "
                f"got {self.certificate_volume_rule!r}"
            )
        if self.predictive_observation_noise not in {
            "assay_relative_additive",
            "learned_homoskedastic",
        }:
            raise ValueError(
                "predictive_observation_noise must be 'assay_relative_additive' or "
                f"'learned_homoskedastic', got {self.predictive_observation_noise!r}"
            )
        if self.latent_draw_inflation not in {
            "none",
            "loo_calibration",
            "loo_calibration_tail",
        }:
            raise ValueError(
                "latent_draw_inflation must be 'none', 'loo_calibration', or "
                f"'loo_calibration_tail', got {self.latent_draw_inflation!r}"
            )
        max_vol = float(self.certificate_max_volume)
        if not math.isfinite(max_vol) or not 0.0 < max_vol <= 1.0:
            raise ValueError(
                "certificate_max_volume must lie in (0, 1], "
                f"got {self.certificate_max_volume!r}"
            )
        object.__setattr__(self, "certificate_max_volume", max_vol)
        floor = float(self.latent_inflation_floor)
        if not math.isfinite(floor) or floor < 1.0:
            raise ValueError(
                "latent_inflation_floor must be finite and >= 1, "
                f"got {self.latent_inflation_floor!r}"
            )
        object.__setattr__(self, "latent_inflation_floor", floor)

    @property
    def digest(self) -> str:
        return _sha256_json({"schema": "boec-scoring-settings-v1", **asdict(self)})


REGISTERED_SCORING_SETTINGS = ScoringExecutionSettings(
    calibration_grid_size=65_536,
    terminal_grid_size=16_384,
    map_grid_size=8_192,
    certificate_grid_size=2_048,
    certificate_draws=4_096,
    certificate_rho_grid_size=64,
    fit_restarts=4,
    certificate_volume_rule="smallest",
    predictive_observation_noise="assay_relative_additive",
    latent_draw_inflation="loo_calibration_tail",
    certificate_max_volume=0.001,
    latent_inflation_floor=1.5,
)


def _execution_settings(
    execution_mode: str,
    settings: ScoringExecutionSettings | None,
) -> ScoringExecutionSettings:
    if execution_mode not in _EXECUTION_MODES:
        raise ValueError(f"execution_mode must be one of {sorted(_EXECUTION_MODES)}")
    effective = REGISTERED_SCORING_SETTINGS if settings is None else settings
    if not isinstance(effective, ScoringExecutionSettings):
        raise TypeError("settings must be ScoringExecutionSettings")
    if execution_mode == "REGISTERED" and effective != REGISTERED_SCORING_SETTINGS:
        raise ValueError("REGISTERED scoring requires every frozen production setting")
    if execution_mode == "TEST_ONLY" and effective == REGISTERED_SCORING_SETTINGS:
        raise ValueError("TEST_ONLY scoring must expose reduced effective settings")
    return effective


def _registered_estimand(
    *,
    dimension: int,
    sigma_rel: float,
    sigma_add: float,
    gamma: float,
    q_tau: float,
    alpha: float | None = None,
) -> None:
    expected = {
        "dimension": (_integer(dimension, "dimension"), _PRIMARY_DIM),
        "sigma_rel": (sigma_rel, _PRIMARY_SIGMA_REL),
        "sigma_add": (sigma_add, _PRIMARY_SIGMA_ADD),
        "gamma": (gamma, _PRIMARY_GAMMA),
        "q_tau": (q_tau, _PRIMARY_Q_TAU),
    }
    if alpha is not None:
        expected["alpha"] = (alpha, _PRIMARY_ALPHA)
    wrong = [name for name, (actual, frozen) in expected.items() if actual != frozen]
    if wrong:
        raise ValueError(f"REGISTERED estimand changed frozen values: {', '.join(wrong)}")


def sobol_grid(dimension: int, size: int, seed: int) -> Tensor:
    """A deterministic scrambled-Sobol unit-cube grid."""
    dimension_i = _integer(dimension, "dimension")
    size_i = _integer(size, "size")
    seed_i = _seed(seed, "seed")
    engine = torch.quasirandom.SobolEngine(
        dimension=dimension_i,
        scramble=True,
        seed=seed_i % (2**31 - 1),
    )
    return engine.draw(size_i).double()


def _truth_adapter(
    oracle: object,
    *,
    truth_range_contract: str,
) -> Callable[[Tensor], Tensor]:
    if callable(oracle):
        function = oracle
    elif callable(getattr(oracle, "truth", None)):
        function = oracle.truth
    elif callable(getattr(oracle, "f", None)):
        def function(X: Tensor):
            return oracle.f(X.detach().cpu().double().numpy())
    else:
        raise TypeError("sealed oracle must be callable or expose truth(X) or f(X)")

    def truth(X: Tensor) -> Tensor:
        raw = function(X)
        result = raw if isinstance(raw, Tensor) else torch.as_tensor(raw)
        result = result.detach().double().to(X.device).reshape(-1)
        if result.shape != (X.shape[0],):
            raise ValueError(f"oracle truth must have shape ({X.shape[0]},)")
        if not bool(torch.isfinite(result).all()):
            raise ValueError("oracle truth must be finite")
        if truth_range_contract == "strict_unit_interval" and (
            bool(torch.any(result < 0.0)) or bool(torch.any(result > 1.0))
        ):
            raise ValueError("strict_unit_interval oracle truth must lie in [0, 1]")
        if truth_range_contract == "legacy_unit_scaled" and bool(
            torch.any(result > 1.0)
        ):
            raise ValueError("legacy_unit_scaled oracle truth must not exceed 1.0")
        return result

    return truth


@dataclass(frozen=True)
class ControlledThreshold:
    tau: float
    sigma_rel: float
    sigma_add: float
    gamma: float
    q_tau: float
    dimension: int
    grid_size: int
    grid_seed: int
    grid_digest: str
    truth_digest: str
    margin_digest: str
    reliable_fraction: float
    target_reliable_fraction: float
    prevalence_tolerance: float
    margin_tie_count: int
    tau_adjustment: str
    execution_mode: str
    settings_digest: str
    oracle_identity: str
    truth_range_contract: str
    record_digest: str


@dataclass(frozen=True)
class _FrozenScoreDecision:
    terminal_x: tuple[float, ...]
    certificate_mask_hex: str
    terminal_grid_seed: int
    map_grid_seed: int
    certificate_grid_seed: int
    certificate_draw_seed: int
    settings_digest: str
    digest: str


class _FrozenOracleView:
    __slots__ = ("_truth", "_decision_digest")

    def __init__(self, truth: Callable[[Tensor], Tensor], decision_digest: str) -> None:
        self._truth = truth
        self._decision_digest = decision_digest

    def evaluate(self, X: Tensor, decision_digest: str) -> Tensor:
        if decision_digest != self._decision_digest:
            raise RuntimeError("oracle score request does not match the frozen decision")
        return self._truth(X)


class ScorerOnlyOracle:
    """Oracle capability that becomes evaluable only after a score decision freezes."""

    __slots__ = ("_truth", "_optimum_value", "_threshold", "_event_log")

    def __init__(
        self,
        truth: Callable[[Tensor], Tensor],
        optimum_value: float,
        threshold: ControlledThreshold,
        event_log: list | None,
    ) -> None:
        self._truth = truth
        self._optimum_value = optimum_value
        self._threshold = threshold
        self._event_log = event_log

    @property
    def optimum_value(self) -> float:
        return self._optimum_value

    @property
    def threshold(self) -> ControlledThreshold:
        return self._threshold

    def _freeze_for_scoring(self, decision: _FrozenScoreDecision) -> _FrozenOracleView:
        if self._event_log is not None:
            self._event_log.append(("freeze", decision.digest))
        return _FrozenOracleView(self._truth, decision.digest)


class SealedOracleHarness:
    """Holds truth outside campaign interfaces and emits only threshold/scorer views."""

    __slots__ = (
        "_truth",
        "_optimum_value",
        "_oracle_identity",
        "_truth_range_contract",
        "_threshold",
    )

    def __init__(
        self,
        oracle: object,
        *,
        optimum_value: Real,
        oracle_identity: str,
        truth_range_contract: str = "strict_unit_interval",
    ) -> None:
        value = _finite(optimum_value, "optimum_value")
        if value != 1.0:
            raise ValueError("lockbox oracle optimum_value must be exactly 1.0")
        if not isinstance(oracle_identity, str) or not oracle_identity.strip():
            raise ValueError("oracle_identity must be a non-empty string")
        if truth_range_contract not in _TRUTH_RANGE_CONTRACTS:
            raise ValueError(
                "truth_range_contract must be 'strict_unit_interval' or "
                "'legacy_unit_scaled'"
            )
        self._truth = _truth_adapter(
            oracle,
            truth_range_contract=truth_range_contract,
        )
        self._optimum_value = value
        self._oracle_identity = oracle_identity
        self._truth_range_contract = truth_range_contract
        self._threshold: ControlledThreshold | None = None

    def _bind_threshold(self, threshold: ControlledThreshold) -> None:
        if self._threshold is not None and self._threshold != threshold:
            raise RuntimeError("sealed oracle threshold is already frozen")
        self._threshold = threshold

    def scorer(self, *, event_log: list | None = None) -> ScorerOnlyOracle:
        if self._threshold is None:
            raise RuntimeError("controlled threshold must freeze before creating a scorer")
        return ScorerOnlyOracle(
            self._truth,
            self._optimum_value,
            self._threshold,
            event_log,
        )


def controlled_tau(
    harness: SealedOracleHarness,
    *,
    sigma_rel: Real,
    sigma_add: Real,
    gamma: Real,
    q_tau: Real,
    root_seed: int,
    execution_mode: str = "REGISTERED",
    settings: ScoringExecutionSettings | None = None,
    dimension: int = _PRIMARY_DIM,
) -> ControlledThreshold:
    """Freeze the gamma-aware prevalence threshold inside the sealed truth harness."""
    if not isinstance(harness, SealedOracleHarness):
        raise TypeError("controlled_tau requires a SealedOracleHarness")
    effective = _execution_settings(execution_mode, settings)
    sigma_rel_f = _finite(sigma_rel, "sigma_rel")
    sigma_add_f = _finite(sigma_add, "sigma_add")
    gamma_f = _probability(gamma, "gamma")
    q_tau_f = _probability(q_tau, "q_tau")
    dimension_i = _integer(dimension, "dimension")
    if sigma_rel_f < 0.0 or sigma_add_f < 0.0:
        raise ValueError("noise sigmas must be nonnegative")
    if execution_mode == "REGISTERED":
        _registered_estimand(
            dimension=dimension_i,
            sigma_rel=sigma_rel_f,
            sigma_add=sigma_add_f,
            gamma=gamma_f,
            q_tau=q_tau_f,
        )
    root_seed_i = _seed(root_seed, "root_seed")
    grid_seed = derive_seed(root_seed_i, "controlled_tau_calibration_grid")
    grid = sobol_grid(dimension_i, effective.calibration_grid_size, grid_seed)
    truth = harness._truth(grid)
    z_gamma = float(norm.ppf(gamma_f))
    noise_sd = (sigma_rel_f**2 * truth.square() + sigma_add_f**2).sqrt()
    margin = truth - z_gamma * noise_sd
    quantile_tau = float(torch.quantile(margin, q_tau_f))
    target_reliable_fraction = 1.0 - q_tau_f
    prevalence_tolerance = 1.0 / effective.calibration_grid_size
    candidates = (
        ("quantile", quantile_tau),
        ("nextafter_up", float(np.nextafter(quantile_tau, math.inf))),
        ("nextafter_down", float(np.nextafter(quantile_tau, -math.inf))),
    )
    evaluated: list[tuple[float, str, float, float]] = []
    for adjustment, candidate_tau in candidates:
        probability = true_reliability_probability(
            truth, candidate_tau, sigma_rel_f, sigma_add_f
        )
        fraction = float((probability >= gamma_f).double().mean())
        evaluated.append(
            (
                abs(fraction - target_reliable_fraction),
                adjustment,
                candidate_tau,
                fraction,
            )
        )
    deviation, tau_adjustment, tau, reliable_fraction = min(
        evaluated, key=lambda row: (row[0], candidates.index((row[1], row[2])))
    )
    numerical_slack = 8.0 * np.finfo(float).eps
    if deviation > prevalence_tolerance + numerical_slack:
        raise RuntimeError(
            "controlled reliable prevalence is not achievable within one calibration "
            f"grid cell: target={target_reliable_fraction:.17g}, "
            f"best={reliable_fraction:.17g}, deviation={deviation:.17g}, "
            f"tolerance={prevalence_tolerance:.17g}"
        )
    margin_tie_count = int((margin == quantile_tau).sum())
    grid_digest = hashlib.sha256(grid.numpy().tobytes()).hexdigest()
    truth_digest = hashlib.sha256(truth.numpy().tobytes()).hexdigest()
    margin_digest = hashlib.sha256(margin.numpy().tobytes()).hexdigest()
    payload = {
        "schema": "boec-controlled-threshold-v1",
        "tau_hex": tau.hex(),
        "sigma_rel": sigma_rel_f,
        "sigma_add": sigma_add_f,
        "gamma": gamma_f,
        "q_tau": q_tau_f,
        "dimension": dimension_i,
        "grid_size": effective.calibration_grid_size,
        "grid_seed": grid_seed,
        "grid_digest": grid_digest,
        "truth_digest": truth_digest,
        "margin_digest": margin_digest,
        "reliable_fraction_hex": reliable_fraction.hex(),
        "target_reliable_fraction_hex": target_reliable_fraction.hex(),
        "prevalence_tolerance_hex": prevalence_tolerance.hex(),
        "margin_tie_count": margin_tie_count,
        "tau_adjustment": tau_adjustment,
        "execution_mode": execution_mode,
        "settings_digest": effective.digest,
        "oracle_identity": harness._oracle_identity,
        "truth_range_contract": harness._truth_range_contract,
    }
    record = ControlledThreshold(
        tau=tau,
        sigma_rel=sigma_rel_f,
        sigma_add=sigma_add_f,
        gamma=gamma_f,
        q_tau=q_tau_f,
        dimension=dimension_i,
        grid_size=effective.calibration_grid_size,
        grid_seed=grid_seed,
        grid_digest=grid_digest,
        truth_digest=truth_digest,
        margin_digest=margin_digest,
        reliable_fraction=reliable_fraction,
        target_reliable_fraction=target_reliable_fraction,
        prevalence_tolerance=prevalence_tolerance,
        margin_tie_count=margin_tie_count,
        tau_adjustment=tau_adjustment,
        execution_mode=execution_mode,
        settings_digest=effective.digest,
        oracle_identity=harness._oracle_identity,
        truth_range_contract=harness._truth_range_contract,
        record_digest=_sha256_json(payload),
    )
    harness._bind_threshold(record)
    return record


@dataclass(frozen=True)
class StudyScore:
    schema: str
    arm: str
    protocol_digest: str
    run_digest: str
    terminal_rule: str
    budget: int
    rounds: int
    execution_mode: str
    scoring_settings_digest: str
    threshold_record_digest: str
    scoring_seed: int
    terminal_fit_seed: int
    terminal_fit_restarts: int
    terminal_grid_seed: int
    map_grid_seed: int
    certificate_grid_seed: int
    certificate_draw_seed: int
    decision_digest: str
    tau: float
    sigma_rel: float
    sigma_add: float
    gamma: float
    alpha: float
    q_tau: float
    terminal_x: tuple[float, ...]
    terminal_truth: float
    regret_rule_p: float
    map_loss: float
    map_brier: float
    map_auc: float | None
    map_iou: float
    map_symmetric_difference: float
    certificate_nonempty: bool
    certificate_volume: float
    certificate_selection_containment: float | None
    certificate_crossfit_containment: float | None
    certificate_empirical_containment: bool | None
    certificate_selection_draws: int
    certificate_evaluation_draws: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _posterior_mean(model: object, X: Tensor) -> Tensor:
    model.eval()
    with torch.no_grad():
        mean = model.posterior(X.double(), observation_noise=False).mean.detach().double().reshape(-1)
    if mean.shape != (X.shape[0],) or not bool(torch.isfinite(mean).all()):
        raise ValueError("terminal model posterior mean must be finite with one value per point")
    return mean


def _latent_inflation_from_loo_residuals(
    y: np.ndarray, mu: np.ndarray, sd: np.ndarray, *, mode: str, floor: float = 1.0
) -> float:
    """Map LOO predictive residuals to a latent draw inflation ≥ ``floor``.

    ``loo_calibration`` uses RMS standardized residuals. ``loo_calibration_tail`` takes
    the max of that RMS and ``max|z| / z_{0.975}`` so localized misspecification that a
    mean-square statistic hides still widens the certificate draws. Dividing by the
    univariate 95% Gaussian quantile keeps a well-calibrated campaign near mild
    inflation rather than treating the extreme-order statistic as a raw multiplier.

    ``floor`` implements the registered KT-5-style fixed inflation
    ``c_eff = max(c_floor, loo_factor)`` (never a family detector).
    """
    if mode == "loo_calibration":
        kappa = float(calibration_inflation(y, mu, sd))
    elif mode == "loo_calibration_tail":
        rms = float(calibration_inflation(y, mu, sd))
        tail = float(calibration_tail(y, mu, sd))
        kappa = max(rms, tail / float(norm.ppf(0.975)))
    else:
        raise ValueError(f"unsupported LOO inflation mode: {mode!r}")
    if not math.isfinite(kappa):
        raise ValueError("LOO calibration inflation must be finite")
    floor_f = float(floor)
    if not math.isfinite(floor_f) or floor_f < 1.0:
        raise ValueError(f"latent inflation floor must be finite and >= 1, got {floor!r}")
    return max(floor_f, max(1.0, kappa))


def _loo_latent_inflation(
    model: object, *, mode: str = "loo_calibration_tail", floor: float = 1.5
) -> float:
    """Widen latent certificate draws using the campaign's own LOO residuals.

    LOO is predictive (noise-inclusive); treating it as a lower bound on the needed
    latent correction is intentional and documented in ``boec.selfcalib``.
    """
    try:
        train_x = model.train_inputs[0].detach().double()
        train_y = model.train_targets.detach().double().reshape(-1)
        with torch.no_grad():
            cov = model.covar_module(train_x).to_dense().double()
            noise = model.likelihood.noise.detach().double().reshape(-1)[0]
            cov = cov + noise * torch.eye(
                cov.shape[0], dtype=torch.double, device=cov.device
            )
    except (AttributeError, IndexError, RuntimeError, TypeError, ValueError) as exc:
        raise ValueError("model must support LOO residual self-calibration") from exc
    y = train_y.detach().cpu().numpy()
    mu, var = loo_residuals(cov.detach().cpu().numpy(), y)
    return _latent_inflation_from_loo_residuals(
        y, mu, np.sqrt(var), mode=mode, floor=floor
    )


def _binary_auc(labels: Tensor, probabilities: Tensor) -> float | None:
    y = labels.detach().cpu().numpy().astype(bool)
    score = probabilities.detach().cpu().numpy()
    n_positive = int(y.sum())
    n_negative = int((~y).sum())
    if n_positive == 0 or n_negative == 0:
        return None
    ranks = rankdata(score, method="average")
    statistic = float(ranks[y].sum() - n_positive * (n_positive + 1) / 2.0)
    return statistic / (n_positive * n_negative)


def _mask_hex(mask: Tensor) -> str:
    packed = np.packbits(mask.detach().cpu().numpy().astype(np.uint8), bitorder="little")
    return packed.tobytes().hex()


def score_campaign(
    campaign_result: object,
    tau: Real,
    scorer_oracle: ScorerOnlyOracle,
    *,
    sigma_rel: Real,
    sigma_add: Real,
    gamma: Real,
    alpha: Real,
    scoring_seed: int,
    execution_mode: str = "REGISTERED",
    settings: ScoringExecutionSettings | None = None,
) -> StudyScore:
    """Score one completed arm through the shared path, revealing truth only last."""
    effective = _execution_settings(execution_mode, settings)
    if not isinstance(scorer_oracle, ScorerOnlyOracle):
        raise TypeError("score_campaign requires a scorer-only oracle capability")
    tau_f = _finite(tau, "tau")
    sigma_rel_f = _finite(sigma_rel, "sigma_rel")
    sigma_add_f = _finite(sigma_add, "sigma_add")
    gamma_f = _probability(gamma, "gamma")
    alpha_f = _probability(alpha, "alpha")
    scoring_seed_i = _seed(scoring_seed, "scoring_seed")
    campaign_mode = getattr(campaign_result, "execution_mode", None)
    campaign_registered = getattr(campaign_result, "registered", None)
    if campaign_mode != execution_mode or campaign_registered is not (execution_mode == "REGISTERED"):
        raise ValueError("campaign execution mode does not match scoring execution mode")
    if scorer_oracle.threshold.execution_mode != execution_mode:
        raise ValueError("sealed-threshold execution mode does not match scoring execution mode")
    if scorer_oracle.threshold.tau != tau_f:
        raise ValueError("numeric tau does not match the sealed threshold")
    if (
        scorer_oracle.threshold.sigma_rel != sigma_rel_f
        or scorer_oracle.threshold.sigma_add != sigma_add_f
        or scorer_oracle.threshold.gamma != gamma_f
        or scorer_oracle.threshold.settings_digest != effective.digest
    ):
        raise ValueError("score estimand/settings do not match the sealed threshold")
    if execution_mode == "REGISTERED":
        _registered_estimand(
            dimension=scorer_oracle.threshold.dimension,
            sigma_rel=sigma_rel_f,
            sigma_add=sigma_add_f,
            gamma=gamma_f,
            q_tau=scorer_oracle.threshold.q_tau,
            alpha=alpha_f,
        )

    X = getattr(campaign_result, "X", None)
    if not isinstance(X, Tensor) or X.ndim != 2 or X.shape[0] != 48:
        raise ValueError("campaign result must contain exactly 48 evaluated rows")
    dimension = X.shape[1]
    if dimension != scorer_oracle.threshold.dimension:
        raise ValueError("campaign dimension does not match sealed threshold")
    campaign_tau = _finite(getattr(campaign_result, "tau", None), "campaign tau")
    if campaign_tau != tau_f:
        raise ValueError("campaign tau does not match the sealed numeric tau")
    Y = getattr(campaign_result, "Y", None)
    if not isinstance(Y, Tensor) or Y.shape != (48, 1) or not bool(torch.isfinite(Y).all()):
        raise ValueError("campaign result must contain 48 finite one-outcome observations")
    if not bool(torch.isfinite(X).all()) or torch.unique(X, dim=0).shape[0] != 48:
        raise ValueError("campaign evaluated rows must be finite and unique")
    arm_protocol_digest = _hex_digest(
        getattr(campaign_result, "protocol_digest"), "protocol_digest"
    )
    run_digest = _hex_digest(getattr(campaign_result, "run_digest"), "run_digest")
    terminal_fit_seed = derive_seed(
        scoring_seed_i,
        "score_terminal_common_gp",
        run_digest,
        effective.digest,
    )
    bounds = torch.stack(
        [
            torch.zeros(dimension, dtype=torch.double),
            torch.ones(dimension, dtype=torch.double),
        ]
    )
    model = build_learned_noise_gp(
        X.detach().double().clone(),
        Y.detach().double().clone(),
        bounds,
        fit_restarts=effective.fit_restarts,
        seed=terminal_fit_seed,
    )

    terminal_seed = derive_seed(scoring_seed_i, "terminal_rule_p_grid")
    map_seed = derive_seed(scoring_seed_i, "probability_map_grid")
    certificate_seed = derive_seed(scoring_seed_i, "certificate_grid")
    draw_seed = derive_seed(scoring_seed_i, "certificate_joint_draws")
    terminal_grid = sobol_grid(dimension, effective.terminal_grid_size, terminal_seed)
    map_grid = sobol_grid(dimension, effective.map_grid_size, map_seed)
    certificate_grid = sobol_grid(dimension, effective.certificate_grid_size, certificate_seed)

    # All model-only choices are fixed before the scorer-only oracle becomes callable.
    if effective.predictive_observation_noise == "assay_relative_additive":
        predictive_noise = {"sigma_rel": sigma_rel_f, "sigma_add": sigma_add_f}
    else:
        predictive_noise = {}
    if effective.latent_draw_inflation in {"loo_calibration", "loo_calibration_tail"}:
        latent_inflation = _loo_latent_inflation(
            model,
            mode=effective.latent_draw_inflation,
            floor=effective.latent_inflation_floor,
        )
    else:
        latent_inflation = 1.0
    terminal_mean = _posterior_mean(model, terminal_grid)
    terminal_x_tensor = terminal_grid[int(torch.argmax(terminal_mean))].clone()
    map_probability = model_reliability_probability(
        model, map_grid, tau_f, **predictive_noise
    ).detach().double()
    set_draws = reliable_set_draws(
        model,
        certificate_grid,
        tau_f,
        gamma_f,
        effective.certificate_draws,
        draw_seed,
        latent_inflation=latent_inflation,
        **predictive_noise,
    )
    certificate = conservative_set_split(
        set_draws,
        alpha_f,
        n_rho=effective.certificate_rho_grid_size,
        volume_rule=effective.certificate_volume_rule,
    )
    if certificate.volume > effective.certificate_max_volume:
        empty = torch.zeros_like(certificate.mask)
        certificate = ConservativeSetResult(
            mask=empty,
            crossfit_containment=None,
            selection_containment=None,
            volume=0.0,
            selection_draws=certificate.selection_draws,
            evaluation_draws=certificate.evaluation_draws,
        )
    decision_payload = {
        "schema": "boec-frozen-score-decision-v1",
        "terminal_x_hex": [float(x).hex() for x in terminal_x_tensor.tolist()],
        "certificate_mask_hex": _mask_hex(certificate.mask),
        "terminal_grid_seed": terminal_seed,
        "map_grid_seed": map_seed,
        "certificate_grid_seed": certificate_seed,
        "certificate_draw_seed": draw_seed,
        "terminal_fit_seed": terminal_fit_seed,
        "terminal_fit_restarts": effective.fit_restarts,
        "settings_digest": effective.digest,
    }
    decision_digest = _sha256_json(decision_payload)
    decision = _FrozenScoreDecision(
        terminal_x=tuple(float(x) for x in terminal_x_tensor.tolist()),
        certificate_mask_hex=decision_payload["certificate_mask_hex"],
        terminal_grid_seed=terminal_seed,
        map_grid_seed=map_seed,
        certificate_grid_seed=certificate_seed,
        certificate_draw_seed=draw_seed,
        settings_digest=effective.digest,
        digest=decision_digest,
    )
    truth_view = scorer_oracle._freeze_for_scoring(decision)

    # Truth is unavailable until the terminal point and issued set above are immutable.
    terminal_truth = float(
        truth_view.evaluate(terminal_x_tensor.reshape(1, -1), decision_digest)[0]
    )
    map_truth = truth_view.evaluate(map_grid, decision_digest)
    certificate_truth = truth_view.evaluate(certificate_grid, decision_digest)
    true_map_probability = true_reliability_probability(
        map_truth, tau_f, sigma_rel_f, sigma_add_f
    )
    true_map_mask = true_map_probability >= gamma_f
    predicted_map_mask = map_probability >= gamma_f
    map_loss = float((map_probability - true_map_probability).square().mean())
    map_brier = float((map_probability - true_map_mask.double()).square().mean())
    symmetric_difference = float((predicted_map_mask != true_map_mask).double().mean())
    union = int((predicted_map_mask | true_map_mask).sum())
    intersection = int((predicted_map_mask & true_map_mask).sum())
    map_iou = 1.0 if union == 0 else intersection / union
    true_certificate_probability = true_reliability_probability(
        certificate_truth, tau_f, sigma_rel_f, sigma_add_f
    )
    empirical = empirical_set_containment(
        certificate.mask,
        true_certificate_probability >= gamma_f,
    )
    regret = scorer_oracle.optimum_value - terminal_truth
    if regret < -1e-10:
        raise RuntimeError("oracle truth exceeded its frozen optimum")

    return StudyScore(
        schema="boec-spade-score-v1",
        arm=str(getattr(campaign_result, "arm")),
        protocol_digest=arm_protocol_digest,
        run_digest=run_digest,
        terminal_rule="P",
        budget=48,
        rounds=_integer(getattr(campaign_result, "rounds"), "rounds"),
        execution_mode=execution_mode,
        scoring_settings_digest=effective.digest,
        threshold_record_digest=scorer_oracle.threshold.record_digest,
        scoring_seed=scoring_seed_i,
        terminal_fit_seed=terminal_fit_seed,
        terminal_fit_restarts=effective.fit_restarts,
        terminal_grid_seed=terminal_seed,
        map_grid_seed=map_seed,
        certificate_grid_seed=certificate_seed,
        certificate_draw_seed=draw_seed,
        decision_digest=decision_digest,
        tau=tau_f,
        sigma_rel=sigma_rel_f,
        sigma_add=sigma_add_f,
        gamma=gamma_f,
        alpha=alpha_f,
        q_tau=scorer_oracle.threshold.q_tau,
        terminal_x=decision.terminal_x,
        terminal_truth=terminal_truth,
        regret_rule_p=max(0.0, regret),
        map_loss=map_loss,
        map_brier=map_brier,
        map_auc=_binary_auc(true_map_mask, map_probability),
        map_iou=map_iou,
        map_symmetric_difference=symmetric_difference,
        certificate_nonempty=bool(certificate.mask.any()),
        certificate_volume=certificate.volume,
        certificate_selection_containment=certificate.selection_containment,
        certificate_crossfit_containment=certificate.crossfit_containment,
        certificate_empirical_containment=empirical,
        certificate_selection_draws=certificate.selection_draws,
        certificate_evaluation_draws=certificate.evaluation_draws,
    )


def collect_environment_provenance() -> dict[str, object]:
    """Exact runtime and thread settings carried by every study row."""
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "torch": torch.__version__,
            "gpytorch": gpytorch.__version__,
            "botorch": botorch.__version__,
        },
        "threads": {
            "torch": torch.get_num_threads(),
            "torch_interop": torch.get_num_interop_threads(),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
            "mkl_num_threads": os.environ.get("MKL_NUM_THREADS"),
        },
        "executable": sys.executable,
        "boec_distribution": importlib.metadata.version("boec"),
    }


def build_study_row(
    score: StudyScore,
    *,
    study_protocol_digest: str,
    spec_digest: str,
    config_digest: str,
    source_commit: str,
    source_dirty: bool,
    command_args: Sequence[str],
    parent_artifacts: Mapping[str, str],
    family: str,
    instance_seed: int,
    campaign_seed: int,
    root_seed: int,
    derived_seeds: Mapping[str, int],
) -> dict[str, object]:
    """Construct the sole raw-row schema with complete provenance."""
    instance_seed_i = _seed(instance_seed, "instance_seed")
    campaign_seed_i = _seed(campaign_seed, "campaign_seed")
    root_seed_i = _seed(root_seed, "root_seed")
    arm_protocol_digest = _hex_digest(score.protocol_digest, "arm_protocol_digest")
    run_digest = _hex_digest(score.run_digest, "run_digest")
    campaign_key = {
        "family": family,
        "instance_seed": instance_seed_i,
        "campaign_seed": campaign_seed_i,
        "arm": score.arm,
        "arm_protocol_digest": arm_protocol_digest,
        "run_digest": run_digest,
    }
    score_payload = json.loads(_canonical_json(score.as_dict()))
    row = {
        "schema": STUDY_ROW_SCHEMA,
        "campaign_key": campaign_key,
        "protocol_digest": _hex_digest(study_protocol_digest, "study_protocol_digest"),
        "arm_protocol_digest": arm_protocol_digest,
        "run_digest": run_digest,
        "spec_digest": _hex_digest(spec_digest, "spec_digest"),
        "config_digest": _hex_digest(config_digest, "config_digest"),
        "source_commit": _hex_digest(source_commit, "source_commit", length=40),
        "source_dirty": source_dirty,
        "environment": collect_environment_provenance(),
        "command_args": list(command_args),
        "parent_artifacts": dict(parent_artifacts),
        "family": family,
        "instance_seed": instance_seed_i,
        "campaign_seed": campaign_seed_i,
        "root_seed": root_seed_i,
        "derived_seeds": dict(derived_seeds),
        "arm": score.arm,
        "budget": score.budget,
        "rounds": score.rounds,
        "terminal_rule": score.terminal_rule,
        "estimands": {
            "target": "future_response_reliability",
            "tau": score.tau,
            "sigma_rel": score.sigma_rel,
            "sigma_add": score.sigma_add,
            "gamma": score.gamma,
            "alpha": score.alpha,
            "q_tau": score.q_tau,
            "map_metric": "integrated_squared_probability_error",
            "terminal_rule": "P",
            "certificate_draws": {
                "total": score.certificate_selection_draws
                + score.certificate_evaluation_draws,
                "selection": score.certificate_selection_draws,
                "evaluation": score.certificate_evaluation_draws,
            },
        },
        "scores": score_payload,
    }
    _validate_rows([row], row["protocol_digest"])
    return row


_ROW_FIELDS = frozenset(
    {
        "schema", "campaign_key", "protocol_digest", "arm_protocol_digest",
        "run_digest", "spec_digest", "config_digest", "source_commit",
        "source_dirty", "environment", "command_args", "parent_artifacts",
        "family", "instance_seed", "campaign_seed", "root_seed",
        "derived_seeds", "arm", "budget", "rounds", "terminal_rule",
        "estimands", "scores",
    }
)
_CAMPAIGN_KEY_FIELDS = frozenset(
    {"family", "instance_seed", "campaign_seed", "arm", "arm_protocol_digest", "run_digest"}
)
_ENVIRONMENT_FIELDS = frozenset(
    {"python", "platform", "packages", "threads", "executable", "boec_distribution"}
)
_PACKAGE_FIELDS = frozenset({"numpy", "scipy", "torch", "gpytorch", "botorch"})
_THREAD_FIELDS = frozenset(
    {"torch", "torch_interop", "omp_num_threads", "mkl_num_threads"}
)
_ESTIMAND_FIELDS = frozenset(
    {
        "target", "tau", "sigma_rel", "sigma_add", "gamma", "alpha", "q_tau",
        "map_metric", "terminal_rule", "certificate_draws",
    }
)
_CERTIFICATE_DRAW_FIELDS = frozenset({"total", "selection", "evaluation"})
_SCORE_FIELDS = frozenset(
    {
        "schema", "arm", "protocol_digest", "run_digest", "terminal_rule",
        "budget", "rounds", "execution_mode", "scoring_settings_digest",
        "threshold_record_digest", "scoring_seed", "terminal_fit_seed",
        "terminal_fit_restarts", "terminal_grid_seed", "map_grid_seed",
        "certificate_grid_seed", "certificate_draw_seed", "decision_digest",
        "tau", "sigma_rel", "sigma_add", "gamma", "alpha", "q_tau",
        "terminal_x", "terminal_truth", "regret_rule_p", "map_loss",
        "map_brier", "map_auc", "map_iou", "map_symmetric_difference",
        "certificate_nonempty", "certificate_volume",
        "certificate_selection_containment", "certificate_crossfit_containment",
        "certificate_empirical_containment", "certificate_selection_draws",
        "certificate_evaluation_draws",
    }
)
_ARMS = frozenset({"spade", "sobol48", "qlognei48"})


def _exact_mapping(value: object, fields: frozenset[str], context: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    result = dict(value)
    missing = fields - result.keys()
    extra = result.keys() - fields
    if missing or extra:
        raise ValueError(
            f"{context} schema mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return result


def _strict_nonnegative_int(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise ValueError(f"{context} must be a nonnegative integer")
    return int(value)


def _finite_number(
    value: object,
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{context} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{context} must be finite")
    if minimum is not None and result < minimum:
        raise ValueError(f"{context} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{context} must be at most {maximum}")
    return result


def _nullable_probability(value: object, context: str) -> float | None:
    if value is None:
        return None
    return _finite_number(value, context, minimum=0.0, maximum=1.0)


def _validate_estimands(value: object, index: int) -> dict[str, object]:
    context = f"row {index} estimands"
    estimands = _exact_mapping(value, _ESTIMAND_FIELDS, context)
    if estimands["target"] != "future_response_reliability":
        raise ValueError(f"{context}.target drift")
    if estimands["map_metric"] != "integrated_squared_probability_error":
        raise ValueError(f"{context}.map_metric drift")
    if estimands["terminal_rule"] != "P":
        raise ValueError(f"{context}.terminal_rule drift")
    _finite_number(estimands["tau"], f"{context}.tau")
    for name in ("sigma_rel", "sigma_add"):
        _finite_number(estimands[name], f"{context}.{name}", minimum=0.0)
    for name in ("gamma", "alpha", "q_tau"):
        probability = _finite_number(
            estimands[name], f"{context}.{name}", minimum=0.0, maximum=1.0
        )
        if not 0.0 < probability < 1.0:
            raise ValueError(f"{context}.{name} must lie strictly between zero and one")
    draws = _exact_mapping(
        estimands["certificate_draws"], _CERTIFICATE_DRAW_FIELDS,
        f"{context}.certificate_draws",
    )
    draw_values = {
        name: _strict_nonnegative_int(draw, f"{context}.certificate_draws.{name}")
        for name, draw in draws.items()
    }
    if (
        min(draw_values.values()) < 1
        or draw_values["selection"] + draw_values["evaluation"] != draw_values["total"]
    ):
        raise ValueError(f"{context}.certificate_draws split is invalid")
    estimands["certificate_draws"] = draws
    return estimands


def _validate_score(score_value: object, row: Mapping[str, object], index: int) -> dict[str, object]:
    context = f"row {index} scores"
    score = _exact_mapping(score_value, _SCORE_FIELDS, context)
    if score["schema"] != "boec-spade-score-v1":
        raise ValueError(f"{context}.schema drift")
    if score["arm"] not in _ARMS:
        raise ValueError(f"{context}.arm is invalid")
    score_budget = _strict_nonnegative_int(score["budget"], f"{context}.budget")
    if score["terminal_rule"] != "P" or score_budget != 48:
        raise ValueError(f"{context} violates Rule P or exact budget")
    if score["execution_mode"] not in _EXECUTION_MODES:
        raise ValueError(f"{context}.execution_mode is invalid")
    for name in (
        "protocol_digest", "run_digest", "scoring_settings_digest",
        "threshold_record_digest", "decision_digest",
    ):
        _hex_digest(score[name], f"{context}.{name}")
    for name in (
        "scoring_seed", "terminal_fit_seed", "terminal_grid_seed", "map_grid_seed",
        "certificate_grid_seed", "certificate_draw_seed",
    ):
        _seed(score[name], f"{context}.{name}")
    rounds = _strict_nonnegative_int(score["rounds"], f"{context}.rounds")
    restarts = _strict_nonnegative_int(
        score["terminal_fit_restarts"], f"{context}.terminal_fit_restarts"
    )
    if rounds < 1 or restarts < 1:
        raise ValueError(f"{context} rounds and terminal fit restarts must be positive")
    numeric_estimands = {
        "tau": _finite_number(score["tau"], f"{context}.tau"),
        "sigma_rel": _finite_number(score["sigma_rel"], f"{context}.sigma_rel", minimum=0.0),
        "sigma_add": _finite_number(score["sigma_add"], f"{context}.sigma_add", minimum=0.0),
        "gamma": _finite_number(score["gamma"], f"{context}.gamma", minimum=0.0, maximum=1.0),
        "alpha": _finite_number(score["alpha"], f"{context}.alpha", minimum=0.0, maximum=1.0),
        "q_tau": _finite_number(score["q_tau"], f"{context}.q_tau", minimum=0.0, maximum=1.0),
    }
    if any(not 0.0 < numeric_estimands[name] < 1.0 for name in ("gamma", "alpha", "q_tau")):
        raise ValueError(f"{context} probability estimands must be strictly internal")
    terminal_x = score["terminal_x"]
    if (
        not isinstance(terminal_x, list)
        or len(terminal_x) != _PRIMARY_DIM
        or any(
            isinstance(coordinate, bool)
            or not isinstance(coordinate, Real)
            or not math.isfinite(float(coordinate))
            or not 0.0 <= float(coordinate) <= 1.0
            for coordinate in terminal_x
        )
    ):
        raise ValueError(f"{context}.terminal_x must be six finite unit-cube coordinates")
    for name in (
        "terminal_truth", "regret_rule_p", "map_loss", "map_brier", "map_iou",
        "map_symmetric_difference", "certificate_volume",
    ):
        _finite_number(score[name], f"{context}.{name}", minimum=0.0, maximum=1.0)
    _nullable_probability(score["map_auc"], f"{context}.map_auc")
    selection = _nullable_probability(
        score["certificate_selection_containment"],
        f"{context}.certificate_selection_containment",
    )
    crossfit = _nullable_probability(
        score["certificate_crossfit_containment"],
        f"{context}.certificate_crossfit_containment",
    )
    empirical = score["certificate_empirical_containment"]
    if empirical is not None and not isinstance(empirical, bool):
        raise ValueError(f"{context}.certificate_empirical_containment must be bool or null")
    nonempty = score["certificate_nonempty"]
    if not isinstance(nonempty, bool):
        raise ValueError(f"{context}.certificate_nonempty must be boolean")
    volume = float(score["certificate_volume"])
    if nonempty:
        if volume <= 0.0 or selection is None or crossfit is None or empirical is None:
            raise ValueError(f"{context} nonempty certificate has incomplete containment")
    elif volume != 0.0 or selection is not None or crossfit is not None or empirical is not None:
        raise ValueError(f"{context} empty certificate must have null containment and zero volume")
    selection_draws = _strict_nonnegative_int(
        score["certificate_selection_draws"], f"{context}.certificate_selection_draws"
    )
    evaluation_draws = _strict_nonnegative_int(
        score["certificate_evaluation_draws"], f"{context}.certificate_evaluation_draws"
    )
    if selection_draws < 1 or evaluation_draws < 1:
        raise ValueError(f"{context} certificate draw halves must be positive")
    if score["execution_mode"] == "REGISTERED" and (
        restarts, selection_draws, evaluation_draws
    ) != (4, 2048, 2048):
        raise ValueError(f"{context} REGISTERED numerical settings drift")
    if score["execution_mode"] == "REGISTERED":
        if score["scoring_settings_digest"] != REGISTERED_SCORING_SETTINGS.digest:
            raise ValueError(f"{context} REGISTERED settings digest drift")
        registered_values = (
            numeric_estimands["sigma_rel"], numeric_estimands["sigma_add"],
            numeric_estimands["gamma"], numeric_estimands["alpha"],
            numeric_estimands["q_tau"],
        )
        if registered_values != (
            _PRIMARY_SIGMA_REL, _PRIMARY_SIGMA_ADD, _PRIMARY_GAMMA,
            _PRIMARY_ALPHA, _PRIMARY_Q_TAU,
        ):
            raise ValueError(f"{context} REGISTERED estimand drift")
    elif score["scoring_settings_digest"] == REGISTERED_SCORING_SETTINGS.digest:
        raise ValueError(f"{context} TEST_ONLY row masquerades as REGISTERED settings")
    identities = {
        "arm": score["arm"], "protocol_digest": score["protocol_digest"],
        "run_digest": score["run_digest"], "budget": score["budget"],
        "rounds": score["rounds"], "terminal_rule": score["terminal_rule"],
    }
    expected = {
        "arm": row["arm"], "protocol_digest": row["arm_protocol_digest"],
        "run_digest": row["run_digest"], "budget": row["budget"],
        "rounds": row["rounds"], "terminal_rule": row["terminal_rule"],
    }
    if identities != expected:
        raise ValueError(f"{context} identity does not match its containing row")
    estimands = row["estimands"]
    if any(numeric_estimands[name] != estimands[name] for name in numeric_estimands):
        raise ValueError(f"{context} estimands do not match containing row")
    draws = estimands["certificate_draws"]
    if (
        selection_draws != draws["selection"]
        or evaluation_draws != draws["evaluation"]
        or selection_draws + evaluation_draws != draws["total"]
    ):
        raise ValueError(f"{context} certificate draws do not match row estimands")
    return score


def _validate_rows(
    rows: Iterable[Mapping[str, object]],
    protocol_digest: str,
) -> list[dict[str, object]]:
    expected_protocol = _hex_digest(protocol_digest, "protocol_digest")
    validated: list[dict[str, object]] = []
    keys: set[str] = set()
    for index, source in enumerate(rows):
        row = _exact_mapping(source, _ROW_FIELDS, f"row {index}")
        if row["schema"] != STUDY_ROW_SCHEMA:
            raise ValueError(f"row {index} schema drift")
        if row["protocol_digest"] != expected_protocol:
            raise ValueError(f"row {index} protocol drift")
        for digest_name in (
            "arm_protocol_digest", "run_digest", "spec_digest", "config_digest",
        ):
            _hex_digest(row[digest_name], f"row {index}.{digest_name}")
        _hex_digest(row["source_commit"], f"row {index}.source_commit", length=40)
        row_budget = _strict_nonnegative_int(row["budget"], f"row {index}.budget")
        row_rounds = _strict_nonnegative_int(row["rounds"], f"row {index}.rounds")
        if row_budget != 48 or row_rounds < 1 or row["terminal_rule"] != "P":
            raise ValueError(f"row {index} violates budget or terminal-rule contract")
        if not isinstance(row["source_dirty"], bool):
            raise ValueError(f"row {index} source_dirty must be boolean")
        family = row["family"]
        if not isinstance(family, str) or not family:
            raise ValueError(f"row {index}.family must be nonempty")
        instance_seed = _strict_nonnegative_int(row["instance_seed"], f"row {index}.instance_seed")
        campaign_seed = _strict_nonnegative_int(row["campaign_seed"], f"row {index}.campaign_seed")
        _seed(row["root_seed"], f"row {index}.root_seed")
        if row["arm"] not in _ARMS:
            raise ValueError(f"row {index}.arm is invalid")
        key = _exact_mapping(row["campaign_key"], _CAMPAIGN_KEY_FIELDS, f"row {index}.campaign_key")
        if not isinstance(key["family"], str) or not key["family"]:
            raise ValueError(f"row {index}.campaign_key.family must be nonempty")
        key_instance_seed = _strict_nonnegative_int(
            key["instance_seed"], f"row {index}.campaign_key.instance_seed"
        )
        key_campaign_seed = _strict_nonnegative_int(
            key["campaign_seed"], f"row {index}.campaign_key.campaign_seed"
        )
        if key["arm"] not in _ARMS:
            raise ValueError(f"row {index}.campaign_key.arm is invalid")
        _hex_digest(
            key["arm_protocol_digest"], f"row {index}.campaign_key.arm_protocol_digest"
        )
        _hex_digest(key["run_digest"], f"row {index}.campaign_key.run_digest")
        expected_key = {
            "family": family, "instance_seed": instance_seed,
            "campaign_seed": campaign_seed, "arm": row["arm"],
            "arm_protocol_digest": row["arm_protocol_digest"],
            "run_digest": row["run_digest"],
        }
        if key_instance_seed != instance_seed or key_campaign_seed != campaign_seed:
            raise ValueError(f"row {index}.campaign_key seed identity mismatch")
        if key != expected_key:
            raise ValueError(f"row {index}.campaign_key identity mismatch")
        canonical_key = _canonical_json(key)
        if canonical_key in keys:
            raise ValueError(f"duplicate campaign_key {canonical_key}")
        keys.add(canonical_key)
        environment = _exact_mapping(
            row["environment"], _ENVIRONMENT_FIELDS, f"row {index}.environment"
        )
        packages = _exact_mapping(
            environment["packages"], _PACKAGE_FIELDS, f"row {index}.environment.packages"
        )
        threads = _exact_mapping(
            environment["threads"], _THREAD_FIELDS, f"row {index}.environment.threads"
        )
        for name in ("python", "platform", "executable", "boec_distribution"):
            if not isinstance(environment[name], str) or not environment[name]:
                raise ValueError(f"row {index}.environment.{name} must be nonempty")
        if not all(isinstance(version, str) and version for version in packages.values()):
            raise ValueError(f"row {index}.environment package versions must be strings")
        for name in ("torch", "torch_interop"):
            if _strict_nonnegative_int(threads[name], f"row {index}.environment.threads.{name}") < 1:
                raise ValueError(f"row {index}.environment.threads.{name} must be positive")
        for name in ("omp_num_threads", "mkl_num_threads"):
            if threads[name] is not None and not isinstance(threads[name], str):
                raise ValueError(f"row {index}.environment.threads.{name} must be string or null")
        if not isinstance(row["command_args"], list) or not all(
            isinstance(arg, str) for arg in row["command_args"]
        ):
            raise ValueError(f"row {index} command_args must be a list of strings")
        if not isinstance(row["parent_artifacts"], Mapping):
            raise ValueError(f"row {index} parent_artifacts must be a mapping")
        for name, digest in row["parent_artifacts"].items():
            if not isinstance(name, str):
                raise ValueError(f"row {index} parent artifact names must be strings")
            _hex_digest(digest, f"row {index}.parent_artifacts[{name!r}]")
        if not isinstance(row["derived_seeds"], Mapping) or not row["derived_seeds"] or not all(
            isinstance(name, str) and name and not isinstance(seed, bool)
            and isinstance(seed, Integral) and 0 <= int(seed) < 2**63
            for name, seed in row["derived_seeds"].items()
        ):
            raise ValueError(f"row {index} derived_seeds are invalid")
        row["estimands"] = _validate_estimands(row["estimands"], index)
        row["scores"] = _validate_score(row["scores"], row, index)
        try:
            _canonical_json(row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"row {index} is not finite canonical JSON") from exc
        validated.append(row)
    if not validated:
        raise ValueError("a shard must contain at least one row")
    return validated


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_jsonl_gzip(
    path: str | Path,
    rows: Iterable[Mapping[str, object]],
    *,
    protocol_digest: str,
) -> str:
    """Atomically write deterministic gzip JSONL and its SHA-256 sidecar."""
    destination = Path(path)
    validated = _validate_rows(rows, protocol_digest)
    uncompressed = b"".join(
        (_canonical_json(row) + "\n").encode("utf-8") for row in validated
    )
    with tempfile.SpooledTemporaryFile() as buffer:
        with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as stream:
            stream.write(uncompressed)
        buffer.seek(0)
        compressed = buffer.read()
    digest = hashlib.sha256(compressed).hexdigest()
    _atomic_write(destination, compressed)
    sidecar = Path(str(destination) + ".sha256")
    _atomic_write(sidecar, f"{digest}  {destination.name}\n".encode("ascii"))
    return digest


def read_jsonl_gzip(
    path: str | Path,
    *,
    protocol_digest: str,
) -> list[dict[str, object]]:
    """Read a shard only after checksum, schema, key, and protocol validation."""
    source = Path(path)
    sidecar = Path(str(source) + ".sha256")
    if not source.is_file() or not sidecar.is_file():
        raise ValueError("gzip shard and SHA-256 sidecar must both exist")
    return read_jsonl_gzip_bytes(
        source.read_bytes(),
        sidecar.read_bytes(),
        source_name=source.name,
        protocol_digest=protocol_digest,
    )


def read_jsonl_gzip_bytes(
    compressed: bytes,
    sidecar_data: bytes,
    *,
    source_name: str,
    protocol_digest: str,
) -> list[dict[str, object]]:
    """Validate a shard from already-authenticated bytes without reopening its path."""
    if not isinstance(compressed, bytes) or not isinstance(sidecar_data, bytes):
        raise TypeError("gzip shard and sidecar inputs must be bytes")
    if not isinstance(source_name, str) or Path(source_name).name != source_name:
        raise ValueError("gzip shard source name must be a basename")
    try:
        expected = sidecar_data.decode("ascii").split()
    except UnicodeDecodeError as exc:
        raise ValueError("gzip shard SHA-256 sidecar must be ASCII") from exc
    if (
        len(expected) != 2
        or expected[0] != hashlib.sha256(compressed).hexdigest()
        or expected[1] != source_name
    ):
        raise ValueError("gzip shard SHA-256 mismatch")
    if len(compressed) < 10 or compressed[:2] != b"\x1f\x8b" or compressed[4:8] != b"\x00\x00\x00\x00":
        raise ValueError("gzip shard does not use the deterministic mtime=0 header")
    if compressed[3] & 0x08:
        raise ValueError("gzip shard embeds a filename and is not path-independent")
    try:
        text = gzip.decompress(compressed).decode("utf-8")
        if not text.endswith("\n"):
            raise ValueError("gzip JSONL must end with a newline")
        lines = text.splitlines()
        rows = [json.loads(line) for line in lines]
        if any(line != _canonical_json(row) for line, row in zip(lines, rows)):
            raise ValueError("gzip JSONL rows are not canonical sorted compact JSON")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("gzip shard is not valid UTF-8 JSONL") from exc
    return _validate_rows(rows, protocol_digest)
