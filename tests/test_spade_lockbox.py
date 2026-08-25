from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import analyse_spade_lockbox as analysis
from scripts import run_spade_lockbox as lockbox


PROTOCOL = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
SOURCE = "1" * 40


def _selection() -> dict:
    return {
        "schema": "boec-spade-selected-protocol-v1",
        "status": "SELECTED",
        "source_commit": SOURCE,
        "protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": "c" * 64,
        "selected_canonical_config": {"opening": 44, "policy": "fixed_hybrid"},
        "selected_template_protocol_digest": "b" * 64,
    }


@pytest.fixture
def clean_access(monkeypatch, tmp_path):
    selected = tmp_path / "results" / "spade-selected-protocol.json"
    selected.parent.mkdir()
    selected.write_text(json.dumps(_selection(), sort_keys=True) + "\n")
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": "c" * 64,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    monkeypatch.setattr(lockbox, "registered_metadata", lambda _: metadata)
    monkeypatch.setattr(lockbox, "git_state", lambda _: (SOURCE, False))
    monkeypatch.setattr(lockbox, "_committed_file_hash", lambda *_: hashlib.sha256(selected.read_bytes()).hexdigest())
    monkeypatch.setattr(lockbox, "_is_ancestor", lambda *_: True)
    monkeypatch.setattr(lockbox, "_selected_template_digest", lambda _: "b" * 64)
    monkeypatch.setattr(lockbox, "_load_generator_freeze", lambda _: {"freeze_parent_commit": lockbox.GENERATOR_FREEZE_PARENT_COMMIT})
    return tmp_path, selected


def test_access_control_fails_closed_without_a_clean_committed_selection(clean_access, monkeypatch):
    root, selected = clean_access
    assert lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)["status"] == "SELECTED"

    selected.unlink()
    with pytest.raises(ValueError, match="missing"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_text(json.dumps({**_selection(), "status": "NO_SELECTION"}) + "\n")
    with pytest.raises(ValueError, match="SELECTED"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_text(json.dumps(_selection()) + "\n")
    monkeypatch.setattr(lockbox, "git_state", lambda _: (SOURCE, True))
    with pytest.raises(ValueError, match="dirty"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    monkeypatch.setattr(lockbox, "git_state", lambda _: (SOURCE, False))
    monkeypatch.setattr(lockbox, "_committed_file_hash", lambda *_: None)
    with pytest.raises(ValueError, match="committed"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_control_rejects_digest_drift_and_pre_freeze_selection(clean_access, monkeypatch):
    root, selected = clean_access
    bad = _selection()
    bad["generator_digest"] = "0" * 64
    selected.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="digest"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_text(json.dumps(_selection()) + "\n")
    monkeypatch.setattr(lockbox, "_is_ancestor", lambda *_: False)
    with pytest.raises(ValueError, match="freeze"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_registered_path_refuses_limit_and_shard_contract_is_exact():
    registered = lockbox.ROOT / "results" / "spade-lockbox-toroidal_rastrigin-000-350.jsonl.gz"
    with pytest.raises(ValueError, match="limit"):
        lockbox.validate_shard_request(
            family="toroidal_rastrigin", start=0, stop=350, output=registered,
            limit=1, smoke=False, repo_root=lockbox.ROOT,
        )
    with pytest.raises(ValueError, match="exactly"):
        lockbox.validate_shard_request(
            family="toroidal_rastrigin", start=0, stop=349, output=registered,
            limit=None, smoke=False, repo_root=lockbox.ROOT,
        )


def test_resume_payload_rejects_a_corrupted_or_incomplete_arm_set():
    metadata = {"protocol_digest": PROTOCOL, "spec_digest": SPEC, "config_digest": CONFIG, "generator_digest": GENERATOR, "generator_manifest_sha256": "c" * 64, "source_commit": SOURCE, "source_dirty": False}
    payload = lockbox.make_resume_payload(
        family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz",
        rows=[{"family": "soft_plateau", "instance_seed": 0, "campaign_seed": 0, "arm": arm} for arm in lockbox.LOCKBOX_ARMS],
        metadata=metadata,
    )
    with pytest.raises(ValueError, match="study-row"):
        lockbox.validate_resume_payload(payload, metadata=metadata, family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz")
    payload["rows"].pop()
    with pytest.raises(ValueError, match="hash-chain|all three|incomplete"):
        lockbox.validate_resume_payload(payload, metadata=metadata, family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz")


def test_resume_rejects_rows_without_full_study_schema_before_promotion():
    metadata = {"protocol_digest": PROTOCOL, "spec_digest": SPEC, "config_digest": CONFIG, "generator_digest": GENERATOR, "generator_manifest_sha256": "c" * 64, "source_commit": SOURCE, "source_dirty": False}
    payload = {
        "schema": "boec-spade-lockbox-resume-v1", "family": "soft_plateau", "start": 0,
        "stop": 1, "raw_file": "scratch.jsonl.gz", "metadata": metadata, "row_count": 3,
        "rows": [{"family": "soft_plateau", "instance_seed": 0, "campaign_seed": 0, "arm": arm} for arm in lockbox.LOCKBOX_ARMS],
    }
    payload["row_chain_head"] = lockbox._row_chain_head(payload["rows"])
    with pytest.raises(ValueError, match="study-row|schema"):
        lockbox.validate_resume_payload(payload, metadata=metadata, family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz")


def test_final_manifest_requires_complete_non_overlapping_shards(tmp_path):
    metadata = {"protocol_digest": PROTOCOL, "spec_digest": SPEC, "config_digest": CONFIG, "generator_digest": GENERATOR, "generator_manifest_sha256": "c" * 64, "source_commit": SOURCE, "source_dirty": False, "selected_protocol_sha256": "b" * 64, "command_args": []}
    paths = []
    for family in lockbox.LOCKBOX_FAMILIES:
        raw = tmp_path / f"spade-lockbox-{family}-000-350.jsonl.gz"
        raw.write_bytes(family.encode())
        raw_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
        (tmp_path / f"{raw.name}.sha256").write_text(f"{raw_hash}  {raw.name}\n")
        manifest = {"schema": lockbox.MANIFEST_SCHEMA, "status": "COMPLETE", "family": family, "start": 0, "stop": 350, "sample_size": 350, "expected_rows": 1050, "row_count": 1050, "complete": True, "raw_file": raw.name, "raw_sha256": raw_hash, **metadata}
        path = tmp_path / f"{raw.name}.manifest.json"
        path.write_text(json.dumps(manifest))
        paths.append(path)
    final = lockbox.merge_lockbox_manifests(paths, output=tmp_path / "spade-lockbox-manifest.json", metadata=metadata)
    assert final["status"] == "COMPLETE"
    assert len(final["raw_shards"]) == 4
    broken = json.loads(paths[0].read_text())
    broken["row_count"] = 1049
    paths[0].write_text(json.dumps(broken))
    with pytest.raises(ValueError, match="row count"):
        lockbox.merge_lockbox_manifests(paths, output=tmp_path / "second.json", metadata=metadata)


def test_runner_source_cannot_depend_on_development_outcome_metrics():
    lockbox.assert_no_development_metric_dependency()


def _rows(
    family: str,
    *,
    n: int = 50,
    answers: int = 50,
    contained: int = 50,
    map_delta: float = -0.01,
    regret_delta: float = -0.01,
) -> list[dict]:
    rows: list[dict] = []
    for key in range(n):
        values = {
            "spade": (0.10 + map_delta, 0.10 + regret_delta),
            "sobol48": (0.10, 0.20),
            "qlognei48": (0.20, 0.10),
        }
        for arm, (map_loss, regret) in values.items():
            nonempty = arm == "spade" and key < answers
            rows.append(
                {
                    "family": family,
                    "instance_seed": key,
                    "campaign_seed": 0,
                    "arm": arm,
                    "budget": 48,
                    "terminal_rule": "P",
                    "scores": {
                        "map_loss": map_loss,
                        "regret_rule_p": regret,
                        "certificate_nonempty": nonempty,
                        "certificate_empirical_containment": (key < contained) if nonempty else None,
                    },
                }
            )
    return rows


def test_confirmatory_analysis_is_per_family_and_rejects_43_of_50_containment():
    rows = _rows("toroidal_rastrigin", contained=43)
    result = analysis.analyse_lockbox_rows(rows, execution_mode="TEST_ONLY", bootstrap_replicates=1000, bootstrap_seed=7)
    endpoint = result["families"]["toroidal_rastrigin"]["certificate_validity"]
    assert endpoint["denominator"] == 50
    assert endpoint["verdict"] == "FAIL"
    assert "lower bound" in endpoint["reason"]


def test_empty_certificates_fail_and_pooling_cannot_rescue_a_family():
    failed = _rows("toroidal_rastrigin", answers=0, contained=0)
    passed = _rows("soft_plateau")
    result = analysis.analyse_lockbox_rows(failed + passed, execution_mode="TEST_ONLY", bootstrap_replicates=1000, bootstrap_seed=9)
    assert result["families"]["toroidal_rastrigin"]["certificate_validity"]["denominator"] == 0
    assert result["families"]["toroidal_rastrigin"]["certificate_willingness"]["verdict"] == "FAIL"
    assert result["overall_verdict"] == "FAIL"
    assert result["secondary"]["pooled"]["does_not_change_primary"] is True


def test_superiority_claims_require_a_strictly_negative_upper_bound():
    rows = _rows("curved_ridge", map_delta=0.0, regret_delta=0.0)
    result = analysis.analyse_lockbox_rows(rows, execution_mode="TEST_ONLY", bootstrap_replicates=1000, bootstrap_seed=11)
    family = result["families"]["curved_ridge"]
    assert family["map_noninferiority"]["verdict"] == "PASS"
    assert family["map_noninferiority"]["superiority"] is False
    assert family["regret_noninferiority"]["superiority"] is False


def test_registered_analysis_rejects_partial_or_unknown_key_grid():
    with pytest.raises(ValueError, match="exactly|350|frozen families|immutable provenance"):
        analysis.analyse_lockbox_rows(
            _rows("soft_plateau"), execution_mode="REGISTERED", bootstrap_replicates=17
        )
    test_only = analysis.analyse_lockbox_rows(
        _rows("soft_plateau"), execution_mode="TEST_ONLY", bootstrap_replicates=17
    )
    assert test_only["overall_verdict"] == "FAIL"


def test_shard_schema_and_merged_schema_share_protocol_and_provenance_keys():
    assert lockbox.SHARD_MANIFEST_FIELDS <= lockbox.MERGED_MANIFEST_FIELDS | {"family", "start", "stop", "expected_rows", "row_count", "complete", "raw_file", "raw_sha256"}
    assert "protocol_digest" in lockbox.SHARD_MANIFEST_FIELDS
    assert "study_protocol_digest" not in lockbox.MERGED_MANIFEST_FIELDS
    assert "selected_protocol_sha256" in lockbox.SHARD_MANIFEST_FIELDS
    assert "command_args" in lockbox.SHARD_MANIFEST_FIELDS
