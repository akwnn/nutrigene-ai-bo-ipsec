from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts import analyse_spade_lockbox as analysis
from scripts import run_spade_lockbox as lockbox
from scripts import select_spade_protocol as selector


PROTOCOL = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
SOURCE = "1" * 40


def _built_selection(monkeypatch, tmp_path: Path) -> dict:
    metadata = {
        "study_protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": "c" * 64,
        "source_commit": SOURCE,
        "source_dirty": False,
    }
    monkeypatch.setattr(selector, "registered_metadata", lambda _root: metadata)
    monkeypatch.setattr(selector, "git_state", lambda _root: (SOURCE, False))
    monkeypatch.setattr(selector, "_load_complete_shards", lambda *_args, **_kwargs: ([], []))
    monkeypatch.setattr(
        selector,
        "analyse_development",
        lambda *_args, **_kwargs: {
            "schema": selector.ANALYSIS_SCHEMA,
            "status": "SELECTED",
            "selected_candidate": "spade-o44-fixed_hybrid",
            "selection_trace": {"rule": "unanimous_lofo_consensus"},
            "lofo_folds": [],
        },
    )
    _, selected = selector.selection_payload_from_shards([tmp_path / "builder-input"], repo_root=tmp_path)
    return selected


@pytest.fixture
def clean_access(monkeypatch, tmp_path):
    selected_payload = _built_selection(monkeypatch, tmp_path)
    selected = tmp_path / "results" / "spade-selected-protocol.json"
    selected.parent.mkdir()
    selected.write_text(json.dumps(selected_payload, sort_keys=True, separators=(",", ":")) + "\n")
    metadata = {
        "protocol_digest": PROTOCOL,
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
    monkeypatch.setattr(lockbox, "_load_generator_freeze", lambda _: {"freeze_parent_commit": lockbox.GENERATOR_FREEZE_PARENT_COMMIT})
    return tmp_path, selected, selected_payload


def test_access_control_fails_closed_without_a_clean_committed_selection(clean_access, monkeypatch):
    root, selected, selected_payload = clean_access
    assert lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)["status"] == "SELECTED"

    selected.unlink()
    with pytest.raises(ValueError, match="missing"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_text(json.dumps({**selected_payload, "status": "NO_SELECTION"}) + "\n")
    with pytest.raises(ValueError, match="SELECTED"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_text(json.dumps(selected_payload) + "\n")
    monkeypatch.setattr(lockbox, "git_state", lambda _: (SOURCE, True))
    with pytest.raises(ValueError, match="dirty"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    monkeypatch.setattr(lockbox, "git_state", lambda _: (SOURCE, False))
    monkeypatch.setattr(lockbox, "_committed_file_hash", lambda *_: None)
    with pytest.raises(ValueError, match="committed"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_control_rejects_digest_drift_and_pre_freeze_selection(clean_access, monkeypatch):
    root, selected, selected_payload = clean_access
    bad = copy.deepcopy(selected_payload)
    bad["generator_digest"] = "0" * 64
    selected.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="digest"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_text(json.dumps(selected_payload) + "\n")
    monkeypatch.setattr(lockbox, "_is_ancestor", lambda *_: False)
    with pytest.raises(ValueError, match="freeze"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_uses_exact_selector_schema_and_study_protocol_digest(clean_access):
    root, selected, selected_payload = clean_access
    bad = copy.deepcopy(selected_payload)
    bad["study_protocol_digest"] = "0" * 64
    selected.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="protocol.*digest"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)

    bad = copy.deepcopy(selected_payload)
    bad["unexpected"] = "field"
    selected.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="schema"):
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
    metadata = {"protocol_digest": PROTOCOL, "spec_digest": SPEC, "config_digest": CONFIG, "generator_digest": GENERATOR, "generator_manifest_sha256": "c" * 64, "source_commit": SOURCE, "source_dirty": False, "selected_protocol_sha256": "b" * 64, "selection_source_commit": SOURCE, "command_args": []}
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
    assert all(item["sha256_file"].endswith(".sha256") for item in final["raw_shards"])
    assert all(len(item["sha256_sha256"]) == 64 for item in final["raw_shards"])
    broken = json.loads(paths[0].read_text())
    broken["row_count"] = 1049
    paths[0].write_text(json.dumps(broken))
    with pytest.raises(ValueError, match="row count"):
        lockbox.merge_lockbox_manifests(paths, output=tmp_path / "second.json", metadata=metadata)


def test_merge_keeps_distinct_shard_command_args(tmp_path):
    metadata = {"protocol_digest": PROTOCOL, "spec_digest": SPEC, "config_digest": CONFIG, "generator_digest": GENERATOR, "generator_manifest_sha256": "c" * 64, "source_commit": SOURCE, "source_dirty": False, "selected_protocol_sha256": "b" * 64, "selection_source_commit": SOURCE, "command_args": []}
    paths = []
    for index, family in enumerate(lockbox.LOCKBOX_FAMILIES):
        raw = tmp_path / f"spade-lockbox-{family}-000-350.jsonl.gz"
        raw.write_bytes(family.encode()); digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        (tmp_path / f"{raw.name}.sha256").write_text(f"{digest}  {raw.name}\n")
        shard = {"schema": lockbox.MANIFEST_SCHEMA, "status": "COMPLETE", "family": family, "start": 0, "stop": 350, "sample_size": 350, "expected_rows": 1050, "row_count": 1050, "complete": True, "raw_file": raw.name, "raw_sha256": digest, **metadata, "command_args": ["--family", family, "--out", str(raw), str(index)]}
        path = tmp_path / f"{raw.name}.manifest.json"; path.write_text(json.dumps(shard)); paths.append(path)
    merged = lockbox.merge_lockbox_manifests(paths, output=tmp_path / "merged.json", metadata=metadata)
    expected = {family: ["--family", family, "--out", str(tmp_path / f"spade-lockbox-{family}-000-350.jsonl.gz"), str(index)] for index, family in enumerate(lockbox.LOCKBOX_FAMILIES)}
    assert {item["family"]: item["command_args"] for item in merged["raw_shards"]} == expected


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


def test_statistics_match_independent_constants_and_use_strict_boundaries():
    upper = analysis.paired_bootstrap_upper(
        [-0.07, -0.02, 0.01, 0.08], replicates=11, seed=314_159
    )
    assert upper == pytest.approx(0.055, rel=0.0, abs=1e-15)

    lower_43_of_50 = analysis.clopper_pearson_lower(43, 50)
    assert lower_43_of_50 == pytest.approx(0.7530647982687908, rel=0.0, abs=1e-15)
    assert lower_43_of_50 < analysis.CONTAINMENT_MINIMUM

    assert analysis._endpoint(0.02, 0.02, 50, 0.02, direction="upper")["verdict"] == "FAIL"
    assert analysis._endpoint(0.90, 0.90, 50, 0.90, direction="lower")["verdict"] == "FAIL"


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
    assert lockbox.SHARD_MANIFEST_FIELDS <= lockbox.MERGED_MANIFEST_FIELDS | {"family", "start", "stop", "expected_rows", "row_count", "complete", "raw_file", "raw_sha256", "command_args"}
    assert "protocol_digest" in lockbox.SHARD_MANIFEST_FIELDS
    assert "study_protocol_digest" not in lockbox.MERGED_MANIFEST_FIELDS
    assert "selected_protocol_sha256" in lockbox.SHARD_MANIFEST_FIELDS
    assert "command_args" in lockbox.SHARD_MANIFEST_FIELDS


@pytest.mark.parametrize("existing_suffix", ["", ".sha256", ".manifest.json"])
def test_runner_rejects_existing_publication_targets_before_access(tmp_path, monkeypatch, existing_suffix):
    destination = tmp_path / "scratch.jsonl.gz"
    Path(f"{destination}{existing_suffix}").write_text("existing")
    monkeypatch.setattr(
        lockbox,
        "validate_lockbox_access",
        lambda **_kwargs: pytest.fail("access must not run for an occupied destination"),
    )
    with pytest.raises(ValueError, match="exists|immutable"):
        lockbox.run_lockbox_shard(
            family="soft_plateau",
            start=0,
            stop=1,
            output=destination,
            limit=1,
            smoke=True,
            repo_root=tmp_path,
        )


def test_interrupted_publication_never_installs_completion_manifest(tmp_path, monkeypatch):
    destination = tmp_path / "scratch.jsonl.gz"
    staging = tmp_path / ".staging"
    staging.mkdir()
    staged_raw = staging / destination.name
    staged_sidecar = Path(f"{staged_raw}.sha256")
    staged_manifest = Path(f"{staged_raw}.manifest.json")
    staged_raw.write_bytes(b"raw")
    staged_sidecar.write_text("digest  scratch.jsonl.gz\n")
    staged_manifest.write_text('{"status":"COMPLETE"}\n')

    real_link = os.link
    attempted: list[str] = []

    def interrupt_before_manifest(source, target):
        attempted.append(Path(target).name)
        if len(attempted) == 3:
            raise OSError("simulated interruption")
        real_link(source, target)

    monkeypatch.setattr(lockbox.os, "link", interrupt_before_manifest)
    with pytest.raises(OSError, match="interruption"):
        lockbox._install_staged_completion(
            destination=destination,
            staged_raw=staged_raw,
            staged_sidecar=staged_sidecar,
            staged_manifest=staged_manifest,
        )
    assert attempted[-1] == f"{destination.name}.manifest.json"
    assert not Path(f"{destination}.manifest.json").exists()
