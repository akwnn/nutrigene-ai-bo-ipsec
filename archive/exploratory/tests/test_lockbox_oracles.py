from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from boec.lockbox_oracles import LOCKBOX_FAMILIES, LockboxOracle, make_lockbox_oracle
from boec.spade_study import SealedOracleHarness, controlled_tau


ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_FAMILIES = {"hill", "ackley", "hartmann6", "levy", "rosenbrock"}


def _audit_grid() -> np.ndarray:
    return torch.quasirandom.SobolEngine(6, scramble=True, seed=917).draw(257).double().numpy()


def test_exactly_four_new_family_names_are_frozen():
    assert LOCKBOX_FAMILIES == (
        "toroidal_rastrigin",
        "gaussian_basin_mixture",
        "curved_ridge",
        "soft_plateau",
    )
    assert not set(LOCKBOX_FAMILIES) & DEVELOPMENT_FAMILIES


@pytest.mark.parametrize("family", LOCKBOX_FAMILIES)
@pytest.mark.parametrize("seed", [0, 1, 84, 349, 1999])
def test_generators_are_deterministic_finite_normalized_and_audited(family, seed):
    first = make_lockbox_oracle(family, seed)
    second = make_lockbox_oracle(family, seed)
    grid = np.vstack([_audit_grid(), first.optimum_x])

    assert first.dim == 6
    assert first.record == second.record
    assert first.record.parameter_digest == second.record.parameter_digest
    assert np.array_equal(first.f(grid), second.f(grid))
    assert np.isfinite(first.f(grid)).all()
    assert np.all((first.f(grid) >= 0.0) & (first.f(grid) <= 1.0))
    assert np.all((first.optimum_x >= 0.2) & (first.optimum_x <= 0.8))
    assert first.optimum_value == 1.0
    assert first.f(first.optimum_x[None, :])[0] == pytest.approx(1.0, abs=1e-6)
    assert first.record.audit.passed is True
    assert first.record.audit.optimum_value == pytest.approx(1.0, abs=1e-6)
    assert first.record.audit.independent_value == pytest.approx(1.0, abs=1e-6)
    assert first.record.audit.agreement <= 1e-6
    json.loads(first.record.parameters_json)
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.record.instance_seed = 9


@pytest.mark.parametrize("family", LOCKBOX_FAMILIES)
def test_instances_are_distinct_and_change_map_topology(family):
    a = make_lockbox_oracle(family, 17)
    b = make_lockbox_oracle(family, 18)
    grid = _audit_grid()
    assert a.record.parameter_digest != b.record.parameter_digest
    assert not np.allclose(a.optimum_x, b.optimum_x)
    assert not np.allclose(a.f(grid), b.f(grid), rtol=0.0, atol=1e-12)


@pytest.mark.parametrize("family", LOCKBOX_FAMILIES)
def test_oracle_state_is_deeply_immutable_and_digest_covers_effective_parameters(family):
    oracle = make_lockbox_oracle(family, 84)
    grid = _audit_grid()
    before = oracle.f(grid).copy()
    optimum_before = oracle.optimum_x
    digest_before = oracle.record.parameter_digest

    assert not any(
        isinstance(getattr(oracle, slot), np.ndarray)
        for slot in oracle.__slots__
        if hasattr(oracle, slot)
    )
    with pytest.raises((AttributeError, TypeError, ValueError)):
        oracle._record = None
    with pytest.raises((AttributeError, TypeError, ValueError)):
        oracle._parameters["shift"][0] = 0.0

    detached = json.loads(oracle.record.parameters_json)
    first_list = next(value for value in detached.values() if isinstance(value, list))
    first_list[0] = 999.0
    optimum_copy = oracle.optimum_x
    optimum_copy[0] = 0.0

    assert np.array_equal(oracle.f(grid), before)
    assert np.array_equal(oracle.optimum_x, optimum_before)
    assert oracle.record.parameter_digest == digest_before
    canonical = json.dumps(
        json.loads(oracle.record.parameters_json),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == digest_before
    forged = dataclasses.replace(oracle.record, parameter_digest="0" * 64)
    with pytest.raises(ValueError, match="immutable instance record"):
        LockboxOracle(family, json.loads(oracle.record.parameters_json), forged)


def test_unknown_family_and_out_of_range_key_fail_closed():
    with pytest.raises(ValueError, match="unknown lockbox family"):
        make_lockbox_oracle("ackley", 0)
    for bad in (-1, 2000, True, 1.5):
        with pytest.raises(ValueError, match="instance_seed"):
            make_lockbox_oracle(LOCKBOX_FAMILIES[0], bad)


@pytest.mark.parametrize("family", LOCKBOX_FAMILIES)
@pytest.mark.parametrize("seed", [0, 84, 349, 1999])
def test_registered_threshold_achieves_quarter_reliable_prevalence(family, seed):
    oracle = make_lockbox_oracle(family, seed)
    harness = SealedOracleHarness(
        oracle,
        optimum_value=oracle.optimum_value,
        oracle_identity=f"{family}:{seed}",
    )
    threshold = controlled_tau(
        harness,
        sigma_rel=.10,
        sigma_add=.01,
        gamma=.95,
        q_tau=.75,
        root_seed=seed,
    )
    assert abs(threshold.reliable_fraction - .25) <= 1 / 65_536
    assert threshold.truth_range_contract == "strict_unit_interval"


def test_registered_threshold_fails_closed_when_ties_make_quarter_unachievable():
    def constant_truth(X):
        return torch.full((X.shape[0],), .25, dtype=torch.double)

    harness = SealedOracleHarness(
        constant_truth,
        optimum_value=1.0,
        oracle_identity="constant-tie-oracle",
    )
    with pytest.raises(RuntimeError, match="controlled reliable prevalence"):
        controlled_tau(
            harness,
            sigma_rel=.10,
            sigma_add=.01,
            gamma=.95,
            q_tau=.75,
            root_seed=0,
        )


def test_frozen_manifest_has_no_outcomes_and_binds_sources_and_key_prefix():
    path = ROOT / "results" / "spade-lockbox-generator-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    encoded = json.dumps(manifest, sort_keys=True).lower()
    assert manifest["status"] == "FROZEN_UNOPENED"
    assert tuple(manifest["families"]) == LOCKBOX_FAMILIES
    assert not set(manifest["families"]) & DEVELOPMENT_FAMILIES
    assert manifest["instance_keys"] == {
        "reserved": {"first": 0, "last": 1999, "count": 2000},
        "selected_prefix": {"first": 0, "last": 349, "count": 350},
    }
    curved = manifest["generator_definitions"]["curved_ridge"]
    assert curved["curvature"] == [-0.9, 0.9]
    assert curved["along_scale"] == [0.25, 0.42]
    assert curved["ridge_width"] == [0.06, 0.13]
    assert curved["background_weight"] == [0.15, 0.22]
    assert curved["background_scale"] == [0.48, 0.68]
    for forbidden in ("map_loss", "regret", "answer_rate", "containment_rate", "verdict"):
        assert forbidden not in encoded

    hashes = manifest["digests"]
    for key, relative in {
        "lockbox_oracles_source_sha256": "src/boec/lockbox_oracles.py",
        "spade_study_source_sha256": "src/boec/spade_study.py",
        "spec_sha256": "docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md",
        "config_file_sha256": "configs/experiment/spade-joint.yaml",
    }.items():
        assert hashes[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
