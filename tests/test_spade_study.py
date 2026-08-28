from __future__ import annotations

import gzip
import hashlib
import json
import math
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
import yaml
import boec.spade_study as study_module

from boec.seedbook import derive_seed
from boec.spade_study import (
    REGISTERED_SCORING_SETTINGS,
    STUDY_ROW_SCHEMA,
    ScoringExecutionSettings,
    SealedOracleHarness,
    StudyScore,
    build_study_row,
    controlled_tau,
    read_jsonl_gzip,
    score_campaign,
    sobol_grid,
    write_jsonl_gzip,
)


ROOT = Path(__file__).resolve().parents[1]


class _Posterior:
    def __init__(self, X, mean_value=0.62, variance=0.04):
        self.mean = torch.full((X.shape[0], 1), mean_value, dtype=torch.double)
        self.variance = torch.full((X.shape[0], 1), variance, dtype=torch.double)
        self.base_sample_shape = torch.Size([X.shape[0], 1])

    def rsample_from_base_samples(self, sample_shape, base_samples):
        return self.mean + self.variance.sqrt() * base_samples


class _Model:
    def __init__(self, mean_value=0.62):
        self.mean_value = mean_value
        self.likelihood = SimpleNamespace(noise=torch.tensor([0.03], dtype=torch.double))
        self.outcome_transform = SimpleNamespace(stdvs=torch.tensor([[1.0]], dtype=torch.double))

    def eval(self):
        return self

    def posterior(self, X, observation_noise=False):
        assert observation_noise is False
        return _Posterior(X, self.mean_value)


def _campaign(arm="spade", tau=0.5):
    X = sobol_grid(6, 48, 29)
    return SimpleNamespace(
        arm=arm,
        protocol_digest="a" * 64,
        run_digest=("b" if arm == "spade" else "c") * 64,
        execution_mode="TEST_ONLY",
        registered=False,
        tau=tau,
        root_seed=91,
        X=X,
        Y=torch.linspace(0.1, 0.9, 48, dtype=torch.double).reshape(-1, 1),
        round_logs=(SimpleNamespace(), SimpleNamespace()),
        rounds=2,
        terminal_model=_Model(),
        terminal_fit_seed=3,
        terminal_fit_diagnostics=(),
    )


def _truth(X):
    return (1.0 - ((X.double() - 0.43) ** 2).mean(dim=1)).clamp(0.0, 1.0)


def _test_settings():
    return ScoringExecutionSettings(
        calibration_grid_size=256,
        terminal_grid_size=64,
        map_grid_size=48,
        certificate_grid_size=24,
        certificate_draws=32,
        certificate_rho_grid_size=8,
        fit_restarts=1,
        certificate_volume_rule="smallest",
        predictive_observation_noise="assay_relative_additive",
        latent_draw_inflation="none",
        certificate_max_volume=0.001,
        latent_inflation_floor=1.0,
        mean_marginalisation=False,
    )


@pytest.fixture(autouse=True)
def _capture_common_terminal_fits(monkeypatch):
    calls = []

    def fit(train_X, train_Y, bounds, *, fit_restarts, seed):
        calls.append(
            {
                "X": train_X.detach().clone(),
                "Y": train_Y.detach().clone(),
                "bounds": bounds.detach().clone(),
                "fit_restarts": fit_restarts,
                "seed": seed,
            }
        )
        return _Model()

    monkeypatch.setattr(study_module, "build_learned_noise_gp", fit, raising=False)
    return calls


def test_registered_scoring_sizes_are_exact_and_immutable():
    assert REGISTERED_SCORING_SETTINGS == ScoringExecutionSettings(
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
        latent_inflation_floor=2.0,
        mean_marginalisation=True,
    )


def test_scoring_settings_reject_unknown_latent_inflation_and_bad_max_volume():
    with pytest.raises(ValueError, match="latent_draw_inflation"):
        ScoringExecutionSettings(
            calibration_grid_size=256,
            terminal_grid_size=64,
            map_grid_size=48,
            certificate_grid_size=24,
            certificate_draws=32,
            certificate_rho_grid_size=8,
            fit_restarts=1,
            latent_draw_inflation="family_library",
        )
    with pytest.raises(ValueError, match="certificate_max_volume"):
        ScoringExecutionSettings(
            calibration_grid_size=256,
            terminal_grid_size=64,
            map_grid_size=48,
            certificate_grid_size=24,
            certificate_draws=32,
            certificate_rho_grid_size=8,
            fit_restarts=1,
            certificate_max_volume=0.0,
        )


def test_loo_tail_inflation_sees_localized_spike_that_rms_hides():
    """Mean-square LOO can look almost calibrated while one bad well ruins the CE."""
    import numpy as np
    from scipy.stats import norm

    y = np.array([1.0, -1.0, 1.0, -1.0, 4.0])
    mu = np.zeros(5)
    sd = np.ones(5)
    rms = study_module._latent_inflation_from_loo_residuals(
        y, mu, sd, mode="loo_calibration"
    )
    tail = study_module._latent_inflation_from_loo_residuals(
        y, mu, sd, mode="loo_calibration_tail"
    )
    assert rms == pytest.approx(math.sqrt((1 + 1 + 1 + 1 + 16) / 5))
    assert tail == pytest.approx(max(rms, 4.0 / float(norm.ppf(0.975))))
    assert tail > rms


def test_fixed_floor_raises_mild_loo_tail_to_registered_c_floor():
    """KT-5 style floor: c_eff = max(1.5, loo_tail); never shrink below the floor."""
    import numpy as np

    # Perfectly calibrated |z|=1 → loo_tail factor is ~1/z_0.975 < 1 → clamped to 1 without floor
    y = np.array([1.0, -1.0, 1.0, -1.0])
    mu = np.zeros(4)
    sd = np.ones(4)
    mild = study_module._latent_inflation_from_loo_residuals(
        y, mu, sd, mode="loo_calibration_tail", floor=1.0
    )
    floored = study_module._latent_inflation_from_loo_residuals(
        y, mu, sd, mode="loo_calibration_tail", floor=1.5
    )
    assert mild == pytest.approx(1.0)
    assert floored == pytest.approx(1.5)

    # When loo_tail already exceeds the floor, the tail wins
    y_spike = np.array([1.0, -1.0, 1.0, -1.0, 6.0])
    strong = study_module._latent_inflation_from_loo_residuals(
        y_spike, np.zeros(5), np.ones(5), mode="loo_calibration_tail", floor=1.5
    )
    assert strong > 1.5


def test_scoring_settings_reject_inflation_floor_below_one():
    with pytest.raises(ValueError, match="latent_inflation_floor"):
        ScoringExecutionSettings(
            calibration_grid_size=256,
            terminal_grid_size=64,
            map_grid_size=48,
            certificate_grid_size=24,
            certificate_draws=32,
            certificate_rho_grid_size=8,
            fit_restarts=1,
            latent_inflation_floor=0.5,
        )



def test_controlled_tau_makes_quarter_grid_reliable_and_releases_numeric_only():
    harness = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    threshold = controlled_tau(
        harness,
        sigma_rel=0.10,
        sigma_add=0.01,
        gamma=0.95,
        q_tau=0.75,
        root_seed=7,
        execution_mode="TEST_ONLY",
        settings=_test_settings(),
    )
    assert isinstance(threshold.tau, float)
    assert 0.20 <= threshold.reliable_fraction <= 0.30
    assert threshold.grid_size == 256
    assert threshold.execution_mode == "TEST_ONLY"
    assert not hasattr(harness.scorer(), "truth")


def test_finite_legacy_truth_can_explicitly_bypass_only_lockbox_range_check():
    def legacy_truth(X):
        return _truth(X) - 0.75

    harness = SealedOracleHarness(
        legacy_truth,
        optimum_value=1.0,
        oracle_identity="legacy-development-toy",
        truth_range_contract="legacy_unit_scaled",
    )
    threshold = controlled_tau(
        harness,
        sigma_rel=0.10,
        sigma_add=0.01,
        gamma=0.95,
        q_tau=0.75,
        root_seed=17,
        execution_mode="TEST_ONLY",
        settings=_test_settings(),
    )
    assert 0.20 <= threshold.reliable_fraction <= 0.30
    assert threshold.truth_range_contract == "legacy_unit_scaled"


@pytest.mark.parametrize("bad", [0, 1, None, "finite", "unit_interval"])
def test_sealed_harness_rejects_unknown_truth_range_contract(bad):
    with pytest.raises(ValueError, match="truth_range_contract"):
        SealedOracleHarness(
            _truth,
            optimum_value=1.0,
            oracle_identity="typed-domain-contract",
            truth_range_contract=bad,
        )


@pytest.mark.parametrize("value", [-1e-9, 1.0 + 1e-9])
def test_strict_truth_contract_rejects_either_unit_interval_violation(value):
    def out_of_range(X):
        return torch.full((X.shape[0],), value, dtype=torch.double)

    harness = SealedOracleHarness(
        out_of_range,
        optimum_value=1.0,
        oracle_identity="strict-range-toy",
    )
    with pytest.raises(ValueError, match="strict_unit_interval"):
        controlled_tau(
            harness,
            sigma_rel=.1,
            sigma_add=.01,
            gamma=.95,
            q_tau=.75,
            root_seed=1,
            execution_mode="TEST_ONLY",
            settings=_test_settings(),
        )


def test_legacy_truth_contract_still_rejects_values_above_one():
    def above_one(X):
        return torch.full((X.shape[0],), 1.001, dtype=torch.double)

    harness = SealedOracleHarness(
        above_one,
        optimum_value=1.0,
        oracle_identity="legacy-upper-bound-toy",
        truth_range_contract="legacy_unit_scaled",
    )
    with pytest.raises(ValueError, match="legacy_unit_scaled"):
        controlled_tau(
            harness,
            sigma_rel=.1,
            sigma_add=.01,
            gamma=.95,
            q_tau=.75,
            root_seed=1,
            execution_mode="TEST_ONLY",
            settings=_test_settings(),
        )


def test_truth_range_contract_is_bound_into_threshold_digest():
    strict = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="same")
    legacy = SealedOracleHarness(
        _truth,
        optimum_value=1.0,
        oracle_identity="same",
        truth_range_contract="legacy_unit_scaled",
    )
    kwargs = dict(
        sigma_rel=.1,
        sigma_add=.01,
        gamma=.95,
        q_tau=.75,
        root_seed=99,
        execution_mode="TEST_ONLY",
        settings=_test_settings(),
    )
    strict_threshold = controlled_tau(strict, **kwargs)
    legacy_threshold = controlled_tau(legacy, **kwargs)
    assert strict_threshold.truth_range_contract == "strict_unit_interval"
    assert legacy_threshold.truth_range_contract == "legacy_unit_scaled"
    assert strict_threshold.record_digest != legacy_threshold.record_digest


def test_registered_threshold_rejects_reduced_settings():
    harness = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    with pytest.raises(ValueError, match="REGISTERED"):
        controlled_tau(
            harness,
            sigma_rel=.1,
            sigma_add=.01,
            gamma=.95,
            q_tau=.75,
            root_seed=1,
            execution_mode="REGISTERED",
            settings=_test_settings(),
        )


@pytest.mark.parametrize("bad_seed", [True, -1, 2**63, 1.5])
def test_threshold_and_scoring_reject_invalid_root_seeds(bad_seed):
    harness = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    with pytest.raises(ValueError, match="root_seed"):
        controlled_tau(
            harness, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
            root_seed=bad_seed, execution_mode="TEST_ONLY", settings=_test_settings(),
        )


def test_score_freezes_rule_p_and_certificate_before_any_truth_call():
    events = []

    def truth(X):
        events.append(("truth", X.shape[0]))
        return _truth(X)

    harness = SealedOracleHarness(truth, optimum_value=1.0, oracle_identity="toy")
    threshold = controlled_tau(
        harness, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
        root_seed=8, execution_mode="TEST_ONLY", settings=_test_settings(),
    )
    events.clear()
    scorer = harness.scorer(event_log=events)
    result = score_campaign(
        _campaign(tau=threshold.tau), threshold.tau, scorer,
        sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
        scoring_seed=41, execution_mode="TEST_ONLY", settings=_test_settings(),
    )
    assert events[0][0] == "freeze"
    assert all(event[0] == "truth" for event in events[1:])
    assert result.terminal_rule == "P"
    assert len(result.terminal_x) == 6
    assert result.certificate_selection_draws == 16
    assert result.certificate_evaluation_draws == 16
    assert result.latent_inflation_factor == pytest.approx(1.0)
    if result.certificate_nonempty:
        assert result.certificate_abstention_reason == "issued"
    else:
        assert result.certificate_abstention_reason in {
            "volume_cap", "no_feasible_ce", "map_disagreement",
        }


def test_score_records_loo_tail_latent_inflation_factor(monkeypatch):
    settings = ScoringExecutionSettings(
        calibration_grid_size=256,
        terminal_grid_size=64,
        map_grid_size=48,
        certificate_grid_size=24,
        certificate_draws=32,
        certificate_rho_grid_size=8,
        fit_restarts=1,
        latent_draw_inflation="loo_calibration_tail",
        latent_inflation_floor=2.0,
        mean_marginalisation=False,
    )
    monkeypatch.setattr(study_module, "_loo_latent_inflation", lambda *args, **kwargs: 2.25)
    harness = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    threshold = controlled_tau(
        harness, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
        root_seed=11, execution_mode="TEST_ONLY", settings=settings,
    )
    score = score_campaign(
        _campaign(tau=threshold.tau), threshold.tau, harness.scorer(),
        sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
        scoring_seed=42, execution_mode="TEST_ONLY", settings=settings,
    )
    assert score.latent_inflation_factor == pytest.approx(2.25)


def test_score_volume_cap_records_abstention_reason(monkeypatch):
    from boec.reliable_region import ConservativeSetResult

    settings = _test_settings()
    fake_mask = torch.ones(24, dtype=torch.bool)
    monkeypatch.setattr(
        study_module,
        "conservative_set_split",
        lambda *args, **kwargs: ConservativeSetResult(
            mask=fake_mask,
            crossfit_containment=0.96,
            selection_containment=0.95,
            volume=0.5,
            selection_draws=16,
            evaluation_draws=16,
        ),
    )
    harness = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    threshold = controlled_tau(
        harness, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
        root_seed=12, execution_mode="TEST_ONLY", settings=settings,
    )
    score = score_campaign(
        _campaign(tau=threshold.tau), threshold.tau, harness.scorer(),
        sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
        scoring_seed=43, execution_mode="TEST_ONLY", settings=settings,
    )
    assert score.certificate_abstention_reason == "volume_cap"
    assert score.certificate_nonempty is False
    assert score.certificate_volume == 0.0


def test_score_refits_common_model_on_all_48_and_ignores_injected_model(
    _capture_common_terminal_fits,
):
    class MaliciousModel:
        def posterior(self, *args, **kwargs):
            raise AssertionError("injected terminal model was trusted")

    settings = _test_settings()
    campaign = _campaign()
    campaign.terminal_model = MaliciousModel()
    harness = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    threshold = controlled_tau(
        harness, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
        root_seed=9, execution_mode="TEST_ONLY", settings=settings,
    )
    campaign.tau = threshold.tau
    score = score_campaign(
        campaign, threshold.tau, harness.scorer(),
        sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
        scoring_seed=73, execution_mode="TEST_ONLY", settings=settings,
    )

    assert len(_capture_common_terminal_fits) == 1
    call = _capture_common_terminal_fits[0]
    assert torch.equal(call["X"], campaign.X)
    assert torch.equal(call["Y"], campaign.Y)
    assert call["X"].shape == (48, 6)
    assert call["Y"].shape == (48, 1)
    assert call["fit_restarts"] == 1
    expected_seed = derive_seed(
        73,
        "score_terminal_common_gp",
        campaign.run_digest,
        settings.digest,
    )
    assert call["seed"] == expected_seed
    assert score.terminal_fit_seed == expected_seed
    assert score.terminal_fit_restarts == 1


def test_score_rejects_campaign_mode_or_tau_identity_drift():
    settings = _test_settings()
    harness = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    threshold = controlled_tau(
        harness, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
        root_seed=8, execution_mode="TEST_ONLY", settings=settings,
    )
    with pytest.raises(ValueError, match="campaign tau"):
        score_campaign(
            _campaign(tau=threshold.tau + .01), threshold.tau, harness.scorer(),
            sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
            scoring_seed=1, execution_mode="TEST_ONLY", settings=settings,
        )
    with pytest.raises(ValueError, match="execution mode"):
        score_campaign(
            _campaign(tau=threshold.tau), threshold.tau, harness.scorer(),
            sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
            scoring_seed=1, execution_mode="REGISTERED",
        )


def test_scorer_uses_identical_arm_neutral_paths_and_map_loss_reference():
    settings = _test_settings()
    h1 = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    threshold = controlled_tau(
        h1, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
        root_seed=6, execution_mode="TEST_ONLY", settings=settings,
    )
    a = score_campaign(
        _campaign("spade", threshold.tau), threshold.tau, h1.scorer(),
        sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
        scoring_seed=52, execution_mode="TEST_ONLY", settings=settings,
    )
    h2 = SealedOracleHarness(_truth, optimum_value=1.0, oracle_identity="toy")
    controlled_tau(
        h2, sigma_rel=.1, sigma_add=.01, gamma=.95, q_tau=.75,
        root_seed=6, execution_mode="TEST_ONLY", settings=settings,
    )
    b = score_campaign(
        _campaign("sobol48", threshold.tau), threshold.tau, h2.scorer(),
        sigma_rel=.1, sigma_add=.01, gamma=.95, alpha=.95,
        scoring_seed=52, execution_mode="TEST_ONLY", settings=settings,
    )
    assert a.terminal_fit_seed != b.terminal_fit_seed
    assert a.terminal_x == b.terminal_x
    assert a.map_loss == b.map_loss
    assert a.regret_rule_p == b.regret_rule_p

    grid = sobol_grid(6, settings.map_grid_size, a.map_grid_seed)
    p_true = 1 - torch.distributions.Normal(0.0, 1.0).cdf(
        (threshold.tau - _truth(grid))
        / (.1**2 * _truth(grid).square() + .01**2).sqrt()
    )
    mean = torch.full_like(p_true, .62)
    assay_noise = .1**2 * mean.square() + .01**2
    p_hat = 1 - torch.distributions.Normal(0.0, 1.0).cdf(
        (threshold.tau - mean) / (.04 + assay_noise).sqrt()
    )
    assert a.map_loss == pytest.approx(float((p_hat - p_true).square().mean()), abs=1e-12)


def _score_payload():
    return {
        "schema": "boec-spade-score-v1",
        "arm": "spade",
        "protocol_digest": "a" * 64,
        "run_digest": "b" * 64,
        "terminal_rule": "P",
        "budget": 48,
        "rounds": 2,
        "execution_mode": "REGISTERED",
        "scoring_settings_digest": REGISTERED_SCORING_SETTINGS.digest,
        "threshold_record_digest": "3" * 64,
        "scoring_seed": 4,
        "terminal_fit_seed": 5,
        "terminal_fit_restarts": 4,
        "terminal_grid_seed": 6,
        "map_grid_seed": 7,
        "certificate_grid_seed": 8,
        "certificate_draw_seed": 9,
        "decision_digest": "4" * 64,
        "tau": .5,
        "sigma_rel": .1,
        "sigma_add": .01,
        "gamma": .95,
        "alpha": .95,
        "q_tau": .75,
        "terminal_x": [.2, .3, .4, .5, .6, .7],
        "terminal_truth": .8,
        "regret_rule_p": .2,
        "map_loss": .1,
        "map_brier": .12,
        "map_auc": .75,
        "map_iou": .6,
        "map_symmetric_difference": .2,
        "certificate_nonempty": True,
        "certificate_volume": .1,
        "certificate_selection_containment": .96,
        "certificate_crossfit_containment": .94,
        "certificate_empirical_containment": True,
        "certificate_selection_draws": 2048,
        "certificate_evaluation_draws": 2048,
        "latent_inflation_factor": 1.5,
        "certificate_abstention_reason": "issued",
    }


def _row(campaign_seed, protocol="d" * 64):
    scores = _score_payload()
    return {
        "schema": STUDY_ROW_SCHEMA,
        "campaign_key": {
            "family": "toroidal_rastrigin",
            "instance_seed": 0,
            "campaign_seed": campaign_seed,
            "arm": "spade",
            "arm_protocol_digest": "a" * 64,
            "run_digest": "b" * 64,
        },
        "protocol_digest": protocol,
        "arm_protocol_digest": "a" * 64,
        "run_digest": "b" * 64,
        "spec_digest": "e" * 64,
        "config_digest": "f" * 64,
        "source_commit": "1" * 40,
        "source_dirty": False,
        "environment": {
            "python": "3.11",
            "platform": "test",
            "packages": {"numpy": "1", "scipy": "1", "torch": "1", "gpytorch": "1", "botorch": "1"},
            "threads": {"torch": 1, "torch_interop": 1, "omp_num_threads": None, "mkl_num_threads": None},
            "executable": "/python",
            "boec_distribution": "0.1.0",
        },
        "command_args": ["--shard", "0"],
        "parent_artifacts": {},
        "family": "toroidal_rastrigin",
        "instance_seed": 0,
        "campaign_seed": campaign_seed,
        "root_seed": 1,
        "derived_seeds": {"noise": 2},
        "arm": "spade",
        "budget": 48,
        "rounds": 2,
        "terminal_rule": "P",
        "estimands": {
            "target": "future_response_reliability",
            "tau": .5,
            "sigma_rel": .1,
            "sigma_add": .01,
            "gamma": .95,
            "alpha": .95,
            "q_tau": .75,
            "map_metric": "integrated_squared_probability_error",
            "terminal_rule": "P",
            "certificate_draws": {"total": 4096, "selection": 2048, "evaluation": 2048},
        },
        "scores": scores,
    }


def test_build_study_row_constructs_the_exact_identity_bound_schema(tmp_path):
    payload = _score_payload()
    payload["terminal_x"] = tuple(payload["terminal_x"])
    score = StudyScore(**payload)
    row = build_study_row(
        score,
        study_protocol_digest="d" * 64,
        spec_digest="e" * 64,
        config_digest="f" * 64,
        source_commit="1" * 40,
        source_dirty=False,
        command_args=("--shard", "0"),
        parent_artifacts={},
        family="toroidal_rastrigin",
        instance_seed=0,
        campaign_seed=0,
        root_seed=1,
        derived_seeds={"noise": 2},
    )
    assert row["campaign_key"] == {
        "family": "toroidal_rastrigin",
        "instance_seed": 0,
        "campaign_seed": 0,
        "arm": "spade",
        "arm_protocol_digest": "a" * 64,
        "run_digest": "b" * 64,
    }
    write_jsonl_gzip(
        tmp_path / "row.jsonl.gz", [row], protocol_digest="d" * 64
    )


def test_deterministic_atomic_gzip_roundtrip_sha_and_fail_closed_validation(tmp_path):
    a = tmp_path / "a.jsonl.gz"
    b = tmp_path / "b.jsonl.gz"
    rows = [_row(0), _row(1)]
    write_jsonl_gzip(a, rows, protocol_digest="d" * 64)
    write_jsonl_gzip(b, rows, protocol_digest="d" * 64)
    assert a.read_bytes() == b.read_bytes()
    assert gzip.decompress(a.read_bytes()).endswith(b"\n")
    assert read_jsonl_gzip(a, protocol_digest="d" * 64) == rows
    assert Path(str(a) + ".sha256").read_text().split()[0] == hashlib.sha256(a.read_bytes()).hexdigest()

    damaged = bytearray(a.read_bytes())
    damaged[-1] ^= 1
    a.write_bytes(damaged)
    with pytest.raises(ValueError, match="SHA-256"):
        read_jsonl_gzip(a, protocol_digest="d" * 64)


def test_jsonl_refuses_duplicates_schema_or_protocol_drift(tmp_path):
    path = tmp_path / "rows.jsonl.gz"
    with pytest.raises(ValueError, match="duplicate campaign_key"):
        write_jsonl_gzip(path, [_row(0), _row(0)], protocol_digest="d" * 64)
    with pytest.raises(ValueError, match="schema"):
        write_jsonl_gzip(path, [{**_row(0), "schema": "wrong"}], protocol_digest="d" * 64)
    with pytest.raises(ValueError, match="protocol"):
        write_jsonl_gzip(path, [_row(0, protocol="0" * 64)], protocol_digest="d" * 64)
    with pytest.raises(ValueError, match="environment"):
        write_jsonl_gzip(
            path, [{**_row(0), "environment": {}}], protocol_digest="d" * 64
        )


def test_jsonl_schema_is_exact_and_identity_bound(tmp_path):
    path = tmp_path / "rows.jsonl.gz"
    mutations = []

    extra_top = _row(0)
    extra_top["unexpected"] = 1
    mutations.append(extra_top)

    extra_score = _row(0)
    extra_score["scores"]["unexpected"] = 1
    mutations.append(extra_score)

    extra_key = _row(0)
    extra_key["campaign_key"]["unexpected"] = 1
    mutations.append(extra_key)

    arm_drift = _row(0)
    arm_drift["campaign_key"]["arm"] = "sobol48"
    mutations.append(arm_drift)

    protocol_drift = _row(0)
    protocol_drift["scores"]["protocol_digest"] = "0" * 64
    mutations.append(protocol_drift)

    run_drift = _row(0)
    run_drift["run_digest"] = "0" * 64
    mutations.append(run_drift)

    float_budget = _row(0)
    float_budget["scores"]["budget"] = 48.0
    mutations.append(float_budget)

    float_key_seed = _row(0)
    float_key_seed["campaign_key"]["campaign_seed"] = 0.0
    mutations.append(float_key_seed)

    for row in mutations:
        with pytest.raises(ValueError):
            write_jsonl_gzip(path, [row], protocol_digest="d" * 64)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("map_loss", -0.1),
        ("regret_rule_p", float("nan")),
        ("certificate_volume", 1.1),
        ("map_auc", 1.1),
        ("certificate_empirical_containment", 1),
        ("terminal_x", [.2] * 5),
    ],
)
def test_jsonl_rejects_corrupt_score_values(tmp_path, field, bad):
    row = _row(0)
    row["scores"][field] = bad
    with pytest.raises(ValueError, match="scores"):
        write_jsonl_gzip(tmp_path / "rows.jsonl.gz", [row], protocol_digest="d" * 64)


def test_jsonl_abstention_reason_matches_certificate_nonempty(tmp_path):
    issued = _row(0)
    issued["scores"].update(
        certificate_nonempty=True,
        certificate_abstention_reason="issued",
    )
    write_jsonl_gzip(tmp_path / "issued.jsonl.gz", [issued], protocol_digest="d" * 64)

    abstained = copy.deepcopy(issued)
    abstained["scores"].update(
        certificate_nonempty=False,
        certificate_volume=0.0,
        certificate_selection_containment=None,
        certificate_crossfit_containment=None,
        certificate_empirical_containment=None,
        certificate_abstention_reason="volume_cap",
    )
    write_jsonl_gzip(tmp_path / "abstained.jsonl.gz", [abstained], protocol_digest="d" * 64)

    mismatch = copy.deepcopy(abstained)
    mismatch["scores"]["certificate_abstention_reason"] = "issued"
    with pytest.raises(ValueError, match="scores"):
        write_jsonl_gzip(tmp_path / "mismatch.jsonl.gz", [mismatch], protocol_digest="d" * 64)


def test_jsonl_containment_nullability_is_consistent(tmp_path):
    valid = _row(0)
    valid["scores"].update(
        certificate_nonempty=False,
        certificate_volume=0.0,
        certificate_selection_containment=None,
        certificate_crossfit_containment=None,
        certificate_empirical_containment=None,
        certificate_abstention_reason="no_feasible_ce",
    )
    write_jsonl_gzip(tmp_path / "valid.jsonl.gz", [valid], protocol_digest="d" * 64)

    invalid = copy.deepcopy(valid)
    invalid["scores"]["certificate_empirical_containment"] = True
    with pytest.raises(ValueError, match="scores"):
        write_jsonl_gzip(tmp_path / "invalid.jsonl.gz", [invalid], protocol_digest="d" * 64)


def test_yaml_freezes_every_registered_design_value_and_its_payload_digest():
    path = ROOT / "configs" / "experiment" / "spade-joint.yaml"
    raw = path.read_bytes()
    cfg = yaml.safe_load(raw)
    p = cfg["protocol"]
    assert p["budget"] == 48
    assert p["dimension"] == 6
    assert p["noise"] == {"sigma_rel": .10, "sigma_add": .01}
    assert p["reliability"] == {"gamma": .95, "alpha": .95, "q_tau": .75}
    assert p["threshold"]["achieved_reliable_prevalence"] == .25
    assert p["threshold"]["registered_tolerance_grid_cells"] == 1
    assert p["threshold"]["unachievable_tie_policy"] == "fail_closed"
    assert p["surrogate"]["terminal_scoring_refit_on_all_observations"] is True
    assert p["grids"] == {"calibration": 65536, "terminal": 16384, "map": 8192, "certificate": 2048}
    assert p["certificate_draws"] == {"total": 4096, "selection": 2048, "evaluation": 2048, "rho_grid": 64}
    assert p["development"]["families"] == ["hill", "ackley", "hartmann6", "levy", "rosenbrock"]
    assert p["development"]["campaigns_per_family_arm"] == 50
    assert p["development"]["truth_range_contracts"] == {
        "hill": "strict_unit_interval",
        "external_families": "legacy_unit_scaled",
    }
    assert p["lockbox"]["families"] == [
        "toroidal_rastrigin", "gaussian_basin_mixture", "curved_ridge", "soft_plateau"
    ]
    assert p["lockbox"]["minimum_campaigns_per_family_arm"] == 350
    assert p["lockbox"]["truth_range_contract"] == "strict_unit_interval"
    canonical = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert cfg["digests"]["protocol_payload_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert cfg["digests"]["protocol_payload_sha256"] == (
        "b846fe2d09237b656b8a9bb0341e4c9f64e6a5989144c0c6a1efb15c2bba4491"
    )
    assert p["certificate_volume_rule"] == "smallest"
    assert p["predictive_observation_noise"] == "assay_relative_additive"
    assert p["latent_draw_inflation"] == "loo_calibration_tail"
    assert p["latent_inflation_floor"] == 2.0
    assert p["mean_marginalisation"] is True
    assert p["certificate_max_volume"] == 0.001
    execution = cfg["execution"]
    assert execution == {
        "schema": "boec-spade-registered-execution-v1",
        "dispatch": {
            "trigger": "workflow_dispatch",
            "dispatches_per_phase": 1,
            "source_sha_input": "exact_40_character_lowercase_commit",
            "event_sha_equals_source_sha": True,
            "workflow_sha_equals_source_sha": True,
            "checkout_ref": "source_sha",
            "checked_out_head_equals_source_sha": True,
            "clean_checkout_required": True,
            "permissions": {"contents": "read"},
        },
        "runtime": {
            "runner": "ubuntu-24.04",
            "platform": "linux/amd64",
            "python": "3.11.15",
            "container": (
                "python@sha256:"
                "eaeffb6e8511935426934aac863940fbd004ef31dab0d7fc27a129bb7c19d9a8"
            ),
            "actions": {
                "checkout": "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
                "upload_artifact": (
                    "actions/upload-artifact@"
                    "ea165f8d65b6e75b540449e92b4886f43607fa02"
                ),
            },
            "environment": {
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "NUMEXPR_NUM_THREADS": "1",
                "PYTHONHASHSEED": "0",
                "CUDA_VISIBLE_DEVICES": "",
            },
            "torch_threads": 1,
            "torch_interop_threads": 1,
        },
        "parallelism": {
            "matrix_max_parallel": 40,
            "processes_per_job_maximum": 2,
        },
        "development_sharding": {
            "family_count": 5,
            "keys_per_family": 50,
            "key_width": 4,
            "logical_shards": 65,
            "jobs": 33,
            "enabled_slots_per_job_maximum": 2,
        },
        "lockbox_sharding": {
            "family_count": 4,
            "key_width": 10,
            "jobs_at_minimum_n_350": 35,
            "jobs_at_maximum_n_2000": 200,
            "family_pairs": [
                ["toroidal_rastrigin", "gaussian_basin_mixture"],
                ["curved_ridge", "soft_plateau"],
            ],
        },
        "artifacts": {
            "one_upload_per_enabled_slot": True,
            "files_per_slot": [
                "raw_jsonl_gzip",
                "sha256_sidecar",
                "resume_json",
                "manifest_json",
            ],
            "compression_level": 0,
            "overwrite": False,
            "retention_days": 90,
        },
    }
    execution_canonical = json.dumps(
        execution,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    assert cfg["digests"]["execution_payload_sha256"] == hashlib.sha256(
        execution_canonical
    ).hexdigest()
    for key, relative in {
        "actions_workflow_sha256": ".github/workflows/spade-distributed.yml",
        "actions_matrix_sha256": "scripts/make_spade_actions_matrix.py",
        "actions_worker_sha256": "scripts/run_spade_actions_worker.py",
        "development_merger_sha256": "scripts/merge_spade_development_shards.py",
        "requirements_sha256": "requirements.txt",
    }.items():
        assert cfg["digests"][key] == hashlib.sha256(
            (ROOT / relative).read_bytes()
        ).hexdigest()
    for key, relative in {
        "lockbox_oracles_source_sha256": "src/boec/lockbox_oracles.py",
        "spade_study_source_sha256": "src/boec/spade_study.py",
        "spec_sha256": "docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md",
    }.items():
        assert cfg["digests"][key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
