from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dc2_runner", ROOT / "scripts" / "run_dc2_doe_certificate.py")
dc2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc2)


def row(key):
    f, s, arm, p, c = key
    return {"family": f, "seed": s, "arm": arm, "p_value": p,
            "inflation_c": c, "regret": 0.1}


def tiny_protocol():
    return dc2.Protocol(seed_start=32, seed_stop=33)


def complete_rows(protocol):
    return [row(k) for k in sorted(dc2.expected_cells(protocol))]


def test_frozen_protocol_defaults():
    p = dc2.PROTOCOL
    assert p.seed_start == 32
    assert p.seed_stop == 64
    assert set(p.arms) == {"doe", "doe_unscreened", "spade"}
    assert p.expected_jobs == 5 * 32
    assert p.expected_rows == 5 * 32 * 3 * 2 * 4


def test_exact_grid_and_duplicate_rejection():
    p = tiny_protocol()
    rows = complete_rows(p)
    assert dc2.validate_rows(rows, p)
    with pytest.raises(ValueError, match="duplicate"):
        dc2.validate_rows(rows + [rows[0]], p)


def test_partial_artifact_is_rejected(tmp_path):
    p = tiny_protocol()
    artifact = {"status": "PARTIAL", "seed_start": 32, "seed_stop": 33,
                "spec_sha256": dc2.sha256(dc2.SPEC), "rows": complete_rows(p)}
    with pytest.raises(ValueError, match="COMPLETE"):
        dc2.validate_artifact(artifact, protocol=p)


def test_provenance_digest_mismatch_is_rejected(tmp_path):
    p = tiny_protocol()
    artifact = {"status": "COMPLETE", "seed_start": 32, "seed_stop": 33,
                "spec_sha256": "wrong", "rows": complete_rows(p)}
    with pytest.raises(ValueError, match="spec digest"):
        dc2.validate_artifact(artifact, protocol=p)


def test_atomic_writer_does_not_leave_partial_file(tmp_path):
    out = tmp_path / "nested" / "dc2.json"
    dc2.atomic_write(out, {"status": "PARTIAL", "rows": []})
    assert json.loads(out.read_text())["status"] == "PARTIAL"
    assert not list(out.parent.glob("*.tmp"))
