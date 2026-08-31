from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from scripts.run_dc2_doe_certificate import (
    DC2Protocol,
    atomic_write,
    complete_job_keys,
    new_artifact,
    validate_artifact,
    assert_source_identity,
)
from scripts import analyse_dc2_doe_certificate as analyse_dc2


def _tiny_protocol() -> DC2Protocol:
    return DC2Protocol(
        families=("hill",),
        seed_start=32,
        seed_stop=33,
        arms=(("doe", 3), ("spade", 5)),
        p_grid=(0.30,),
        c_grid=(1.0, 2.0),
    )


def _rows(protocol: DC2Protocol) -> list[dict]:
    return [
        {
            "family": family,
            "seed": seed,
            "arm": arm,
            "rounds": rounds,
            "n_wells": 48,
            "p_value": p_value,
            "inflation_c": inflation_c,
            "regret": 0.1,
            "ce_empty_0.95": False,
            "ce_empirical_0.95": True,
            "ce_vol_0.95": 0.01,
        }
        for family in protocol.families
        for seed in range(protocol.seed_start, protocol.seed_stop)
        for arm, rounds in protocol.arms
        for p_value in protocol.p_grid
        for inflation_c in protocol.c_grid
    ]


def _complete_artifact(protocol: DC2Protocol) -> dict:
    artifact = new_artifact(
        protocol,
        source_commit="a" * 40,
        source_dirty=False,
        spec_sha256="b" * 64,
        runner_sha256="c" * 64,
    )
    artifact["rows"] = _rows(protocol)
    artifact["completed_jobs"] = [["hill", 32]]
    artifact["status"] = "COMPLETE"
    return artifact


def test_registered_protocol_uses_unseen_seeds_and_three_arms():
    protocol = DC2Protocol()
    assert protocol.seed_start == 32
    assert protocol.seed_stop == 64
    assert {arm for arm, _rounds in protocol.arms} == {"doe", "doe_unscreened", "spade"}
    assert protocol.expected_jobs == 5 * 32
    assert protocol.expected_rows == 5 * 32 * 3 * 2 * 4


def test_complete_exact_grid_is_accepted():
    protocol = _tiny_protocol()
    artifact = _complete_artifact(protocol)
    validate_artifact(
        artifact,
        protocol,
        require_complete=True,
        expected_spec_sha256="b" * 64,
        expected_runner_sha256="c" * 64,
    )


def test_duplicate_cell_is_rejected():
    protocol = _tiny_protocol()
    artifact = _complete_artifact(protocol)
    artifact["rows"].append(dict(artifact["rows"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        validate_artifact(artifact, protocol, require_complete=True)


def test_partial_artifact_is_rejected_by_confirmatory_validation():
    protocol = _tiny_protocol()
    artifact = _complete_artifact(protocol)
    artifact["status"] = "PARTIAL"
    with pytest.raises(ValueError, match="COMPLETE"):
        validate_artifact(artifact, protocol, require_complete=True)


def test_missing_cell_is_rejected_when_marked_complete():
    protocol = _tiny_protocol()
    artifact = _complete_artifact(protocol)
    artifact["rows"].pop()
    with pytest.raises(ValueError, match="missing|grid|row"):
        validate_artifact(artifact, protocol, require_complete=True)


def test_provenance_digest_mismatch_is_rejected():
    protocol = _tiny_protocol()
    artifact = _complete_artifact(protocol)
    with pytest.raises(ValueError, match="spec_sha256"):
        validate_artifact(
            artifact,
            protocol,
            require_complete=True,
            expected_spec_sha256="d" * 64,
        )


def test_nonfinite_nonempty_certificate_volume_is_rejected():
    protocol = _tiny_protocol()
    artifact = _complete_artifact(protocol)
    artifact["rows"][0]["ce_vol_0.95"] = math.inf
    with pytest.raises(ValueError, match="non-finite ce_vol_0.95"):
        validate_artifact(artifact, protocol, require_complete=True)


def test_wrong_well_count_is_rejected():
    protocol = _tiny_protocol()
    artifact = _complete_artifact(protocol)
    artifact["rows"][0]["n_wells"] = 47
    with pytest.raises(ValueError, match="n_wells"):
        validate_artifact(artifact, protocol, require_complete=True)


def test_source_identity_rejects_head_or_dirty_state_drift(monkeypatch):
    payload = {"source_commit": "a" * 40}
    monkeypatch.setattr(
        "scripts.run_dc2_doe_certificate._git",
        lambda *args: "b" * 40 if args == ("rev-parse", "HEAD") else "",
    )
    with pytest.raises(RuntimeError, match="source_commit changed"):
        assert_source_identity(payload)

    monkeypatch.setattr(
        "scripts.run_dc2_doe_certificate._git",
        lambda *args: "a" * 40 if args == ("rev-parse", "HEAD") else " M source.py",
    )
    with pytest.raises(RuntimeError, match="dirty"):
        assert_source_identity(payload)


def test_resume_skips_only_a_job_with_its_complete_cell_grid():
    protocol = _tiny_protocol()
    artifact = new_artifact(
        protocol,
        source_commit="a" * 40,
        source_dirty=False,
        spec_sha256="b" * 64,
        runner_sha256="c" * 64,
    )
    artifact["rows"] = _rows(protocol)[:-1]
    assert complete_job_keys(artifact["rows"], protocol) == set()
    artifact["rows"] = _rows(protocol)
    assert complete_job_keys(artifact["rows"], protocol) == {("hill", 32)}


def test_atomic_writer_failure_leaves_existing_partial_artifact(tmp_path, monkeypatch):
    path = tmp_path / "dc2.json"
    path.write_text(json.dumps({"status": "PARTIAL"}))

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("scripts.run_dc2_doe_certificate.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        atomic_write(path, {"status": "COMPLETE"})
    assert json.loads(path.read_text()) == {"status": "PARTIAL"}


def test_analyser_refuses_a_partial_artifact(tmp_path, monkeypatch, capsys):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"status": "PARTIAL"}))
    monkeypatch.setattr("sys.argv", ["analyse_dc2", "--input", str(path)])
    assert analyse_dc2.main() == 2
    assert "REFUSED" in capsys.readouterr().err
