from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_historical_replay.py"
GATES = {
    "tests/test_d23_doe_subspace.py::test_full_space_rule_p_reproduces_fix1",
    "tests/test_p4_coord.py::test_k6_scorer_reproduces_a_committed_lhs_row_bitwise",
    "tests/test_q59_map_rescore.py::test_the_edit_is_additive_and_reproduces_the_committed_columns",
    "tests/test_spread_gp.py::test_the_extracted_arm_reproduces_the_committed_q52_rows_exactly",
    "tests/test_calibration.py::test_the_checkpoint_write_path_actually_runs",
    "tests/test_replay.py::test_family_qlogei_reproduces_the_committed_q42_column_exactly",
    "tests/test_replay.py::test_family_qlogei_reproduces_on_every_family_and_at_d8",
    "tests/test_replay.py::test_family_qlognei_reproduces_the_q59_hartmann_column",
}


def _audit_module():
    spec = importlib.util.spec_from_file_location("historical_replay_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_has_one_complete_row_per_observed_historical_failure():
    audit = _audit_module()
    document = audit.build_audit(ROOT)
    assert document["schema_version"] == "boec.historical-replay-audit.v2"
    assert document["observed_run"]["run_id"] == "task-1-historical-replay-2026-08-25"
    assert document["observed_run"]["environment"] == audit.OBSERVED_ENVIRONMENT
    assert document["audit_environment"] == audit.environment()
    rows = document["rows"]
    assert {row["gate"] for row in rows} == GATES
    assert len(rows) == len(GATES)

    required = {
        "schema_version",
        "gate",
        "observed_delta",
        "classification",
        "registered_tolerance",
        "scientific_decision_unchanged",
        "selected_point_unchanged",
        "evidence",
        "environment",
        "observed_run_id",
        "observed_environment",
        "sources",
        "source_hash",
        "current_source_hash",
        "source_matches_observation",
    }
    for row in rows:
        assert set(row) == required
        assert row["schema_version"] == document["schema_version"]
        assert row["observed_delta"] > 0.0
        assert row["classification"] in audit.CLASSIFICATIONS
        assert len(row["source_hash"]) == 64
        assert row["observed_run_id"] == document["observed_run"]["run_id"]
        assert row["observed_environment"] == audit.OBSERVED_ENVIRONMENT
        assert row["environment"] == row["observed_environment"]
        assert row["current_source_hash"] == audit.hash_sources(ROOT, row["sources"])
        assert row["source_matches_observation"] is (
            row["source_hash"] == row["current_source_hash"]
        )


def test_registered_tolerance_requires_the_scientific_result_to_be_unchanged():
    audit = _audit_module()
    rows = audit.build_audit(ROOT)["rows"]
    tolerant = [
        row
        for row in rows
        if row["classification"] == "REPRODUCIBLE_REGISTERED_TOLERANCE"
    ]
    assert tolerant
    for row in tolerant:
        assert row["scientific_decision_unchanged"] is True
        assert row["selected_point_unchanged"] is True
        assert row["registered_tolerance"] >= row["observed_delta"]


def test_material_adaptive_mismatches_are_not_rounded_away():
    audit = _audit_module()
    rows = audit.build_audit(ROOT)["rows"]
    adaptive = [row for row in rows if "qlog" in row["gate"]]
    assert len(adaptive) == 3
    assert all(
        row["classification"] == "HISTORICAL_NONREGENERABLE"
        and row["registered_tolerance"] is None
        for row in adaptive
    )


def test_observed_deltas_are_pinned_to_the_audited_source_content():
    audit = _audit_module()
    document = audit.build_audit(ROOT)
    by_gate = {row["gate"]: row for row in document["rows"]}
    for observation in audit.OBSERVATIONS:
        row = by_gate[observation["gate"]]
        assert row["source_hash"] == observation["source_hash"]
        assert row["current_source_hash"] == audit.hash_sources(
            ROOT, observation["sources"]
        )


def test_observed_environment_is_frozen_not_relabelled_by_the_current_caller(monkeypatch):
    audit = _audit_module()
    current = {"caller_environment": "deliberately-different"}
    monkeypatch.setattr(audit, "environment", lambda: current)

    document = audit.build_audit(ROOT)

    assert document["audit_environment"] == current
    assert document["observed_run"]["environment"] == audit.OBSERVED_ENVIRONMENT
    assert all(
        row["observed_environment"] == audit.OBSERVED_ENVIRONMENT
        and row["observed_environment"] != current
        for row in document["rows"]
    )


def test_audit_document_round_trips_to_json(tmp_path):
    audit = _audit_module()
    output = tmp_path / "historical-replay-audit.json"
    expected = audit.build_audit(ROOT)
    audit.write_audit(output, ROOT)
    assert json.loads(output.read_text()) == expected


def test_default_audit_artifact_is_not_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "results/historical-replay-audit.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout
