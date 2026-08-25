from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
import yaml

from boec.spade_study import (
    REGISTERED_SCORING_SETTINGS,
    STUDY_ROW_SCHEMA,
    ScoringExecutionSettings,
    SealedOracleHarness,
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
    )


def test_registered_scoring_sizes_are_exact_and_immutable():
    assert REGISTERED_SCORING_SETTINGS == ScoringExecutionSettings(
        calibration_grid_size=65_536,
        terminal_grid_size=16_384,
        map_grid_size=8_192,
        certificate_grid_size=2_048,
        certificate_draws=4_096,
        certificate_rho_grid_size=64,
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
    assert a.decision_digest == b.decision_digest
    assert a.map_loss == b.map_loss
    assert a.regret_rule_p == b.regret_rule_p

    grid = sobol_grid(6, settings.map_grid_size, a.map_grid_seed)
    p_true = 1 - torch.distributions.Normal(0.0, 1.0).cdf(
        (threshold.tau - _truth(grid))
        / (.1**2 * _truth(grid).square() + .01**2).sqrt()
    )
    p_hat = 1 - torch.distributions.Normal(0.0, 1.0).cdf(
        torch.full_like(p_true, (threshold.tau - .62) / math.sqrt(.04 + .03))
    )
    assert a.map_loss == pytest.approx(float((p_hat - p_true).square().mean()), abs=1e-12)


def _row(key, protocol="d" * 64):
    return {
        "schema": STUDY_ROW_SCHEMA,
        "campaign_key": key,
        "protocol_digest": protocol,
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
        },
        "command_args": ["--shard", "0"],
        "parent_artifacts": {},
        "family": "toroidal_rastrigin",
        "instance_seed": 0,
        "campaign_seed": 0,
        "root_seed": 1,
        "derived_seeds": {"noise": 2},
        "arm": "spade",
        "budget": 48,
        "rounds": 2,
        "terminal_rule": "P",
        "estimands": {"gamma": .95, "alpha": .95, "q_tau": .75},
        "scores": {"map_loss": .1},
    }


def test_deterministic_atomic_gzip_roundtrip_sha_and_fail_closed_validation(tmp_path):
    a = tmp_path / "a.jsonl.gz"
    b = tmp_path / "b.jsonl.gz"
    rows = [_row("k0"), _row("k1")]
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
        write_jsonl_gzip(path, [_row("same"), _row("same")], protocol_digest="d" * 64)
    with pytest.raises(ValueError, match="schema"):
        write_jsonl_gzip(path, [{**_row("k"), "schema": "wrong"}], protocol_digest="d" * 64)
    with pytest.raises(ValueError, match="protocol"):
        write_jsonl_gzip(path, [_row("k", protocol="0" * 64)], protocol_digest="d" * 64)
    with pytest.raises(ValueError, match="environment"):
        write_jsonl_gzip(
            path, [{**_row("k"), "environment": {}}], protocol_digest="d" * 64
        )


def test_yaml_freezes_every_registered_design_value_and_its_payload_digest():
    path = ROOT / "configs" / "experiment" / "spade-joint.yaml"
    raw = path.read_bytes()
    cfg = yaml.safe_load(raw)
    p = cfg["protocol"]
    assert p["budget"] == 48
    assert p["dimension"] == 6
    assert p["noise"] == {"sigma_rel": .10, "sigma_add": .01}
    assert p["reliability"] == {"gamma": .95, "alpha": .95, "q_tau": .75}
    assert p["grids"] == {"calibration": 65536, "terminal": 16384, "map": 8192, "certificate": 2048}
    assert p["certificate_draws"] == {"total": 4096, "selection": 2048, "evaluation": 2048, "rho_grid": 64}
    assert p["development"]["families"] == ["hill", "ackley", "hartmann6", "levy", "rosenbrock"]
    assert p["development"]["campaigns_per_family_arm"] == 50
    assert p["lockbox"]["families"] == [
        "toroidal_rastrigin", "gaussian_basin_mixture", "curved_ridge", "soft_plateau"
    ]
    assert p["lockbox"]["minimum_campaigns_per_family_arm"] == 350
    canonical = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert cfg["digests"]["protocol_payload_sha256"] == hashlib.sha256(canonical).hexdigest()
    for key, relative in {
        "lockbox_oracles_source_sha256": "src/boec/lockbox_oracles.py",
        "spade_study_source_sha256": "src/boec/spade_study.py",
        "spec_sha256": "docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md",
    }.items():
        assert cfg["digests"][key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
