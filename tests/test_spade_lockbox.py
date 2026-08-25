from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import boec.spade_power as power
from boec.spade_power import DEVELOPMENT_FAMILIES, POWER_ENDPOINTS
from scripts import analyse_spade_lockbox as analysis
from scripts import run_spade_lockbox as lockbox
from scripts import select_spade_protocol as selector


PROTOCOL = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
SOURCE = "1" * 40
POWER_SOURCE = "2" * 40
CURRENT_SOURCE = "3" * 40
POWER_HASH = "9" * 64


def _environment(
    executable: str = "/opt/host-a/bin/python",
    *,
    platform_name: str = "macOS-15.6.1-arm64-arm-64bit",
    torch_threads: int = 4,
) -> dict[str, object]:
    return {
        "python": "3.11.13",
        "platform": platform_name,
        "packages": {
            "numpy": "2.3.2",
            "scipy": "1.16.1",
            "torch": "2.7.1",
            "gpytorch": "1.14",
            "botorch": "0.15.0",
        },
        "threads": {
            "torch": torch_threads,
            "torch_interop": 1,
            "omp_num_threads": "4",
            "mkl_num_threads": None,
        },
        "executable": executable,
        "boec_distribution": "0.1.0",
    }


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)[:-1]).hexdigest()


def _lockbox_metadata() -> dict[str, object]:
    return {
        "protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": "c" * 64,
        "source_commit": CURRENT_SOURCE,
        "source_dirty": False,
        "selected_protocol_sha256": "b" * 64,
        "selection_source_commit": SOURCE,
        "power_plan_sha256": POWER_HASH,
        "power_source_commit": POWER_SOURCE,
    }


def _install_trusted_merge_access(
    monkeypatch: pytest.MonkeyPatch,
    metadata: dict[str, object],
    *,
    sample_size: int,
) -> None:
    monkeypatch.setattr(
        lockbox,
        "validate_lockbox_access",
        lambda **_kwargs: {
            "selection": {"source_commit": metadata["selection_source_commit"]},
            "power_plan": {
                "source_commit": metadata["power_source_commit"],
                "selected_protocol": {
                    "sha256": metadata["selected_protocol_sha256"]
                },
            },
            "sample_size": sample_size,
            "power_plan_sha256": metadata["power_plan_sha256"],
        },
    )
    monkeypatch.setattr(
        lockbox,
        "registered_metadata",
        lambda _root: {
            field: metadata[field]
            for field in (
                "protocol_digest",
                "spec_digest",
                "config_digest",
                "generator_digest",
                "generator_manifest_sha256",
                "source_commit",
                "source_dirty",
            )
        },
    )


def _write_synthetic_lockbox_shard(
    directory: Path,
    *,
    family: str,
    start: int,
    stop: int,
    sample_size: int,
    metadata: dict[str, object],
    environment: dict[str, object],
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    raw = directory / lockbox.registered_raw_filename(
        family, start, stop, sample_size=sample_size
    )
    # Deliberately not JSONL/gzip: merge may authenticate bytes, but must not inspect
    # outcome rows or metrics before the completed distributed artifact is analysed.
    raw.write_bytes(f"synthetic-no-outcome:{family}:{start}:{stop}".encode("ascii"))
    raw_sha256 = hashlib.sha256(raw.read_bytes()).hexdigest()
    Path(f"{raw}.sha256").write_text(f"{raw_sha256}  {raw.name}\n")
    shard = {
        "schema": lockbox.MANIFEST_SCHEMA,
        "status": "COMPLETE",
        "family": family,
        "start": start,
        "stop": stop,
        "sample_size": sample_size,
        "expected_rows": (stop - start) * len(lockbox.LOCKBOX_ARMS),
        "row_count": (stop - start) * len(lockbox.LOCKBOX_ARMS),
        "complete": True,
        "raw_file": raw.name,
        "raw_sha256": raw_sha256,
        **metadata,
        "environment_compatibility": lockbox.environment_compatibility_projection(
            environment
        ),
        "command_args": ["--family", family, "--start", str(start), "--stop", str(stop)],
    }
    manifest = Path(f"{raw}.manifest.json")
    manifest.write_bytes(_canonical_bytes(shard))
    return manifest


def _distributed_synthetic_shards(
    tmp_path: Path,
    *,
    metadata: dict[str, object],
    sample_size: int = 350,
) -> list[Path]:
    intervals = ((0, 73), (73, 181), (181, 271), (271, sample_size))
    paths: list[Path] = []
    for family_index, family in enumerate(lockbox.LOCKBOX_FAMILIES):
        for shard_index, (start, stop) in enumerate(intervals):
            paths.append(
                _write_synthetic_lockbox_shard(
                    tmp_path / f"host-{family_index}-{shard_index}",
                    family=family,
                    start=start,
                    stop=stop,
                    sample_size=sample_size,
                    metadata=metadata,
                    environment=_environment(
                        f"/opt/worker-{family_index}-{shard_index}/bin/python"
                    ),
                )
            )
    return paths


def _development_artifacts() -> list[dict[str, object]]:
    return [
        {
            "family": family,
            "raw_file": f"spade-development-{family}-000-050.jsonl.gz",
            "raw_sha256": f"{index:x}" * 64,
            "manifest_file": (
                f"spade-development-{family}-000-050.jsonl.gz.manifest.json"
            ),
            "manifest_sha256": f"{index + 5:x}" * 64,
        }
        for index, family in enumerate(DEVELOPMENT_FAMILIES)
    ]


def _proof_folds(candidate: str) -> list[dict[str, object]]:
    return [
        {
            "held_out_family": family,
            "training_families": [
                other for other in DEVELOPMENT_FAMILIES if other != family
            ],
            "selected_candidate": candidate,
        }
        for family in DEVELOPMENT_FAMILIES
    ]


def _power_payload(
    *, selected_sha256: str, selected_source: str = SOURCE, sample_size: int = 412
) -> tuple[dict[str, object], object]:
    held_out = {
        family: {endpoint: [-0.01] * 50 for endpoint in POWER_ENDPOINTS}
        for family in DEVELOPMENT_FAMILIES
    }
    decision = power.plan_lockbox_sample_size(held_out).as_dict()
    decision["selected_sample_size"] = sample_size
    decision["selected_instance_prefix"] = {
        "first": 0,
        "last": sample_size - 1,
        "count": sample_size,
    }
    for family in DEVELOPMENT_FAMILIES:
        for endpoint in POWER_ENDPOINTS:
            decision["families"][family][endpoint]["reported_n"] = sample_size
    decision_sha256 = _canonical_sha256(decision)
    recomputed = SimpleNamespace(
        status="POWERED",
        as_dict=lambda: copy.deepcopy(decision),
        decision_sha256=decision_sha256,
    )
    candidate = "spade-o44-fixed_hybrid"
    payload: dict[str, object] = {
        "schema": "boec-spade-lockbox-power-v1",
        "status": "POWERED",
        "source_commit": POWER_SOURCE,
        "source_dirty": False,
        "environment": {
            "python": "3.11.9",
            "numpy": "2.1.0",
            "scipy": "1.14.0",
            "platform": "test-platform",
        },
        "digests": {
            "study_protocol_sha256": PROTOCOL,
            "specification_sha256": SPEC,
            "configuration_sha256": CONFIG,
            "generator_sha256": GENERATOR,
            "generator_manifest_sha256": "c" * 64,
            "power_design_sha256": "4" * 64,
            "power_engine_sha256": "5" * 64,
            "power_planner_sha256": "6" * 64,
        },
        "selected_protocol": {
            "file": "spade-selected-protocol.json",
            "sha256": selected_sha256,
            "source_commit": selected_source,
        },
        "development_artifacts": _development_artifacts(),
        "held_out_proof": {
            "unanimous": True,
            "selected_candidate": candidate,
            "folds": _proof_folds(candidate),
        },
        "held_out_differences": held_out,
        "decision": decision,
        "decision_sha256": decision_sha256,
    }
    return payload, recomputed


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
    selected_payload["development_artifacts"] = _development_artifacts()
    selected_payload["lofo_folds"] = _proof_folds(
        str(selected_payload["selected_candidate"])
    )
    selected = tmp_path / "results" / "spade-selected-protocol.json"
    selected.parent.mkdir()
    selected.write_bytes(_canonical_bytes(selected_payload))
    selected_sha256 = hashlib.sha256(selected.read_bytes()).hexdigest()
    power_payload, recomputed = _power_payload(selected_sha256=selected_sha256)
    power_path = tmp_path / "results" / "spade-lockbox-power.json"
    power_path.write_bytes(_canonical_bytes(power_payload))
    metadata = {
        "protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": "c" * 64,
        "source_commit": CURRENT_SOURCE,
        "source_dirty": False,
    }
    monkeypatch.setattr(lockbox, "registered_metadata", lambda _: metadata)
    monkeypatch.setattr(lockbox, "git_state", lambda _: (CURRENT_SOURCE, False))

    def committed_file_hash(_root, _revision, relative="results/spade-selected-protocol.json"):
        path = tmp_path / relative
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

    monkeypatch.setattr(lockbox, "_committed_file_hash", committed_file_hash)
    monkeypatch.setattr(lockbox, "_is_ancestor", lambda *_: True)
    monkeypatch.setattr(lockbox, "_load_generator_freeze", lambda _: {"freeze_parent_commit": lockbox.GENERATOR_FREEZE_PARENT_COMMIT})
    monkeypatch.setattr(power, "plan_lockbox_sample_size", lambda *_args, **_kwargs: recomputed)
    return tmp_path, selected, selected_payload, power_path, power_payload


def test_access_control_fails_closed_without_a_clean_committed_selection(clean_access, monkeypatch):
    root, selected, selected_payload, _power_path, _power_payload_value = clean_access
    assert lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)["selection"]["status"] == "SELECTED"

    selected.unlink()
    with pytest.raises(ValueError, match="missing"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_text(json.dumps({**selected_payload, "status": "NO_SELECTION"}) + "\n")
    with pytest.raises(ValueError, match="SELECTED"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_bytes(_canonical_bytes(selected_payload))
    monkeypatch.setattr(lockbox, "git_state", lambda _: (CURRENT_SOURCE, True))
    with pytest.raises(ValueError, match="dirty"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    monkeypatch.setattr(lockbox, "git_state", lambda _: (CURRENT_SOURCE, False))
    monkeypatch.setattr(lockbox, "_committed_file_hash", lambda *_: None)
    with pytest.raises(ValueError, match="committed"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_control_rejects_digest_drift_and_pre_freeze_selection(clean_access, monkeypatch):
    root, selected, selected_payload, _power_path, _power_payload_value = clean_access
    bad = copy.deepcopy(selected_payload)
    bad["generator_digest"] = "0" * 64
    selected.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="digest"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    selected.write_bytes(_canonical_bytes(selected_payload))
    monkeypatch.setattr(lockbox, "_is_ancestor", lambda *_: False)
    with pytest.raises(ValueError, match="freeze"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_uses_exact_selector_schema_and_study_protocol_digest(clean_access):
    root, selected, selected_payload, _power_path, _power_payload_value = clean_access
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


def test_access_binds_exact_committed_power_plan_and_dynamic_size(clean_access):
    root, selected, selected_payload, power_path, power_payload_value = clean_access
    access = lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)
    assert set(access) == {"selection", "power_plan", "sample_size", "power_plan_sha256"}
    assert access["selection"] == selected_payload
    assert access["power_plan"] == power_payload_value
    assert access["sample_size"] == 412
    assert access["power_plan_sha256"] == hashlib.sha256(power_path.read_bytes()).hexdigest()


def test_access_rejects_missing_uncommitted_or_noncanonical_power(
    clean_access, monkeypatch
):
    root, selected, _selected_payload, power_path, power_payload_value = clean_access
    power_path.unlink()
    with pytest.raises(ValueError, match="power.*missing"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)

    power_path.write_bytes(_canonical_bytes(power_payload_value))
    original = lockbox._committed_file_hash
    monkeypatch.setattr(
        lockbox,
        "_committed_file_hash",
        lambda repo_root, revision, relative="results/spade-selected-protocol.json": (
            None
            if relative == "results/spade-lockbox-power.json"
            else original(repo_root, revision, relative)
        ),
    )
    with pytest.raises(ValueError, match="power.*committed"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)

    monkeypatch.setattr(lockbox, "_committed_file_hash", original)
    power_path.write_text(json.dumps(power_payload_value) + "\n")
    with pytest.raises(ValueError, match="canonical|bytes"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_rejects_insufficient_out_of_range_or_wrongly_bound_power(
    clean_access, monkeypatch
):
    root, selected, _selected_payload, power_path, power_payload_value = clean_access
    monkeypatch.setattr(lockbox, "validate_power_plan_payload", lambda payload: payload)

    insufficient = copy.deepcopy(power_payload_value)
    insufficient["status"] = "INSUFFICIENT_POWER"
    insufficient["decision"]["status"] = "INSUFFICIENT_POWER"
    insufficient["decision"]["selected_sample_size"] = None
    insufficient["decision"]["selected_instance_prefix"] = None
    power_path.write_bytes(_canonical_bytes(insufficient))
    with pytest.raises(ValueError, match="POWERED"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)

    outside = copy.deepcopy(power_payload_value)
    outside["decision"]["selected_sample_size"] = 2001
    outside["decision"]["selected_instance_prefix"] = {
        "first": 0,
        "last": 2000,
        "count": 2001,
    }
    power_path.write_bytes(_canonical_bytes(outside))
    with pytest.raises(ValueError, match="350|2000|range"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)

    wrong_selection = copy.deepcopy(power_payload_value)
    wrong_selection["selected_protocol"]["sha256"] = "0" * 64
    power_path.write_bytes(_canonical_bytes(wrong_selection))
    with pytest.raises(ValueError, match="selected protocol|selection"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_requires_selection_and_power_sources_to_be_ancestors(
    clean_access, monkeypatch
):
    root, selected, _selected_payload, _power_path, _power_payload_value = clean_access
    monkeypatch.setattr(
        lockbox,
        "_is_ancestor",
        lambda _root, older, newer: not (
            older == POWER_SOURCE and newer == CURRENT_SOURCE
        ),
    )
    with pytest.raises(ValueError, match="power.*ancestor|power.*reachable"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_cross_checks_power_candidate_folds_and_development_artifacts(
    clean_access
):
    root, selected, _selected_payload, power_path, power_payload_value = clean_access
    wrong_candidate = copy.deepcopy(power_payload_value)
    wrong_candidate["held_out_proof"]["selected_candidate"] = "spade-o32-staged"
    for fold in wrong_candidate["held_out_proof"]["folds"]:
        fold["selected_candidate"] = "spade-o32-staged"
    power_path.write_bytes(_canonical_bytes(wrong_candidate))
    with pytest.raises(ValueError, match="candidate|fold|selection"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)

    wrong_artifact = copy.deepcopy(power_payload_value)
    wrong_artifact["development_artifacts"][0]["raw_sha256"] = "f" * 64
    power_path.write_bytes(_canonical_bytes(wrong_artifact))
    with pytest.raises(ValueError, match="development artifact|selection"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


def test_access_requires_metadata_for_the_checked_clean_commit(
    clean_access, monkeypatch
):
    root, selected, _selected_payload, _power_path, _power_payload_value = clean_access
    metadata = dict(lockbox.registered_metadata(root))
    metadata["source_commit"] = "4" * 40
    monkeypatch.setattr(lockbox, "registered_metadata", lambda _root: metadata)
    with pytest.raises(ValueError, match="current clean source|source commit"):
        lockbox.validate_lockbox_access(repo_root=root, selected_path=selected)


@pytest.mark.parametrize(
    "relative",
    [
        ".github/workflows/spade-distributed.yml",
        "scripts/make_spade_actions_matrix.py",
        "scripts/run_spade_actions_worker.py",
        "scripts/merge_spade_development_shards.py",
        "requirements.txt",
    ],
)
def test_registered_metadata_rejects_live_execution_blob_drift(monkeypatch, relative):
    root = Path(__file__).resolve().parents[1]
    original = lockbox._sha256

    def drift(path):
        if path == root / relative:
            return "0" * 64
        return original(path)

    monkeypatch.setattr(lockbox, "_sha256", drift)
    with pytest.raises(ValueError, match="execution|source digest"):
        lockbox.registered_metadata(root)


def test_registered_path_refuses_limit_and_uses_dynamic_four_digit_range():
    registered = lockbox.ROOT / "results" / "spade-lockbox-toroidal_rastrigin-0000-0412.jsonl.gz"
    assert (
        lockbox.registered_raw_filename("toroidal_rastrigin", 0, 412, sample_size=412)
        == registered.name
    )
    with pytest.raises(ValueError, match="limit"):
        lockbox.validate_shard_request(
            family="toroidal_rastrigin", start=0, stop=350, output=registered,
            limit=1, smoke=False, repo_root=lockbox.ROOT, sample_size=412,
        )
    with pytest.raises(ValueError, match="prefix|range|412"):
        lockbox.validate_shard_request(
            family="toroidal_rastrigin", start=0, stop=413, output=registered,
            limit=None, smoke=False, repo_root=lockbox.ROOT, sample_size=412,
        )
    with pytest.raises(ValueError, match="registered path"):
        lockbox.validate_shard_request(
            family="toroidal_rastrigin", start=0, stop=412,
            output=registered.with_name("wrong.jsonl.gz"), limit=None, smoke=False,
            repo_root=lockbox.ROOT, sample_size=412,
        )


def test_resume_payload_rejects_a_corrupted_or_incomplete_arm_set():
    metadata = _lockbox_metadata()
    payload = lockbox.make_resume_payload(
        family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz",
        rows=[{"family": "soft_plateau", "instance_seed": 0, "campaign_seed": 0, "arm": arm} for arm in lockbox.LOCKBOX_ARMS],
        metadata=metadata, sample_size=412,
    )
    with pytest.raises(ValueError, match="study-row"):
        lockbox.validate_resume_payload(payload, metadata=metadata, family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz", sample_size=412)
    payload["rows"].pop()
    with pytest.raises(ValueError, match="hash-chain|all three|incomplete"):
        lockbox.validate_resume_payload(payload, metadata=metadata, family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz", sample_size=412)


def test_resume_rejects_rows_without_full_study_schema_before_promotion():
    metadata = _lockbox_metadata()
    payload = {
        "schema": "boec-spade-lockbox-resume-v2", "family": "soft_plateau", "start": 0,
        "stop": 1, "sample_size": 412, "raw_file": "scratch.jsonl.gz", "metadata": metadata, "row_count": 3,
        "rows": [{"family": "soft_plateau", "instance_seed": 0, "campaign_seed": 0, "arm": arm} for arm in lockbox.LOCKBOX_ARMS],
    }
    payload["row_chain_head"] = lockbox._row_chain_head(payload["rows"])
    with pytest.raises(ValueError, match="study-row|schema"):
        lockbox.validate_resume_payload(payload, metadata=metadata, family="soft_plateau", start=0, stop=1, raw_file="scratch.jsonl.gz", sample_size=412)


def test_final_manifest_requires_complete_non_overlapping_shards(tmp_path, monkeypatch):
    metadata = {**_lockbox_metadata(), "command_args": []}
    _install_trusted_merge_access(monkeypatch, metadata, sample_size=412)
    paths = []
    for family in lockbox.LOCKBOX_FAMILIES:
        raw = tmp_path / f"spade-lockbox-{family}-0000-0412.jsonl.gz"
        raw.write_bytes(family.encode())
        raw_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
        (tmp_path / f"{raw.name}.sha256").write_text(f"{raw_hash}  {raw.name}\n")
        manifest = {"schema": lockbox.MANIFEST_SCHEMA, "status": "COMPLETE", "family": family, "start": 0, "stop": 412, "sample_size": 412, "expected_rows": 1236, "row_count": 1236, "complete": True, "raw_file": raw.name, "raw_sha256": raw_hash, **metadata, "environment_compatibility": lockbox.environment_compatibility_projection(_environment())}
        path = tmp_path / f"{raw.name}.manifest.json"
        path.write_text(json.dumps(manifest))
        paths.append(path)
    final = lockbox.merge_lockbox_manifests(paths, output=tmp_path / "spade-lockbox-manifest.json", metadata=metadata, sample_size=412)
    assert final["status"] == "COMPLETE"
    assert final["schema"] == "boec-spade-lockbox-manifest-v2"
    assert final["sample_size"] == 412
    assert final["power_plan_sha256"] == POWER_HASH
    assert final["power_source_commit"] == POWER_SOURCE
    assert len(final["raw_shards"]) == 4
    assert all(item["sha256_file"].endswith(".sha256") for item in final["raw_shards"])
    assert all(len(item["sha256_sha256"]) == 64 for item in final["raw_shards"])
    broken = json.loads(paths[0].read_text())
    broken["row_count"] = 1235
    paths[0].write_text(json.dumps(broken))
    with pytest.raises(ValueError, match="row count"):
        lockbox.merge_lockbox_manifests(paths, output=tmp_path / "second.json", metadata=metadata, sample_size=412)


def test_environment_compatibility_projection_excludes_only_host_executable():
    host_a = _environment("/opt/host-a/bin/python")
    host_b = _environment("/srv/host-b/venv/bin/python")
    projection = lockbox.environment_compatibility_projection(host_a)

    assert projection == lockbox.environment_compatibility_projection(host_b)
    assert "executable" not in projection
    assert projection["python"] == host_a["python"]
    assert projection["platform"] == host_a["platform"]
    assert projection["packages"] == host_a["packages"]
    assert projection["threads"] == host_a["threads"]
    assert projection["boec_distribution"] == host_a["boec_distribution"]

    for field, incompatible in (
        ("platform", _environment(platform_name="Linux-6.8-x86_64")),
        ("threads", _environment(torch_threads=8)),
    ):
        assert lockbox.environment_compatibility_projection(incompatible) != projection, field


def test_merge_accepts_arbitrary_cross_host_shards_without_loading_outcomes(
    tmp_path, monkeypatch
):
    metadata = _lockbox_metadata()
    _install_trusted_merge_access(monkeypatch, metadata, sample_size=350)
    paths = _distributed_synthetic_shards(tmp_path, metadata=metadata)

    merged = lockbox.merge_lockbox_manifests(
        list(reversed(paths)),
        output=tmp_path / "spade-lockbox-manifest.json",
        metadata=metadata,
        sample_size=350,
    )

    assert len(merged["raw_shards"]) == 16
    assert merged["environment_compatibility"] == (
        lockbox.environment_compatibility_projection(_environment())
    )
    assert "executable" not in merged["environment_compatibility"]
    assert {
        Path(path).parent.name for path in paths
    } == {f"host-{family}-{shard}" for family in range(4) for shard in range(4)}


@pytest.mark.parametrize("defect", ["gap", "overlap", "duplicate"])
def test_merge_rejects_distributed_range_defects_without_loading_outcomes(
    tmp_path, monkeypatch, defect
):
    metadata = _lockbox_metadata()
    _install_trusted_merge_access(monkeypatch, metadata, sample_size=350)
    paths = _distributed_synthetic_shards(tmp_path, metadata=metadata)
    family_paths = [
        path for path in paths if lockbox.LOCKBOX_FAMILIES[0] in path.name
    ]
    if defect == "gap":
        paths.remove(family_paths[1])
    elif defect == "overlap":
        paths.remove(family_paths[1])
        paths.append(
            _write_synthetic_lockbox_shard(
                tmp_path / "overlap-host",
                family=lockbox.LOCKBOX_FAMILIES[0],
                start=70,
                stop=181,
                sample_size=350,
                metadata=metadata,
                environment=_environment("/overlap-host/bin/python"),
            )
        )
    else:
        paths.append(family_paths[0])

    with pytest.raises(ValueError, match="missing|overlapping|incomplete"):
        lockbox.merge_lockbox_manifests(
            paths,
            output=tmp_path / "spade-lockbox-manifest.json",
            metadata=metadata,
            sample_size=350,
        )


def test_merge_rejects_science_incompatible_distributed_environment(
    tmp_path, monkeypatch
):
    metadata = _lockbox_metadata()
    _install_trusted_merge_access(monkeypatch, metadata, sample_size=350)
    paths = _distributed_synthetic_shards(tmp_path, metadata=metadata)
    drifted = json.loads(paths[-1].read_text())
    drifted["environment_compatibility"]["packages"]["torch"] = "9.9.9"
    paths[-1].write_bytes(_canonical_bytes(drifted))

    with pytest.raises(ValueError, match="environment compatibility"):
        lockbox.merge_lockbox_manifests(
            paths,
            output=tmp_path / "spade-lockbox-manifest.json",
            metadata=metadata,
            sample_size=350,
        )


def test_merge_requires_fresh_validated_access_before_processing_shards(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        lockbox,
        "validate_lockbox_access",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("access denied")),
    )
    output = tmp_path / "merged.json"
    with pytest.raises(ValueError, match="access denied"):
        lockbox.merge_lockbox_manifests(
            [], output=output, metadata=_lockbox_metadata(), sample_size=412,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    ("sample_size", "mutate_metadata", "message"),
    [
        (411, lambda metadata: None, "caller sample size drift"),
        (
            412,
            lambda metadata: metadata.__setitem__("power_plan_sha256", "0" * 64),
            "caller metadata drift",
        ),
        (
            412,
            lambda metadata: metadata.__setitem__("power_source_commit", "0" * 40),
            "caller metadata drift",
        ),
    ],
)
def test_merge_rejects_caller_power_drift_before_processing_shards(
    tmp_path, monkeypatch, sample_size, mutate_metadata, message
):
    metadata = _lockbox_metadata()
    mutate_metadata(metadata)
    access = {
        "selection": {"source_commit": SOURCE},
        "power_plan": {
            "source_commit": POWER_SOURCE,
            "selected_protocol": {"sha256": "b" * 64},
        },
        "sample_size": 412,
        "power_plan_sha256": POWER_HASH,
    }
    monkeypatch.setattr(lockbox, "validate_lockbox_access", lambda **_kwargs: access)
    monkeypatch.setattr(
        lockbox,
        "registered_metadata",
        lambda _root: {
            field: metadata_value
            for field, metadata_value in _lockbox_metadata().items()
            if field
            in {
                "protocol_digest",
                "spec_digest",
                "config_digest",
                "generator_digest",
                "generator_manifest_sha256",
                "source_commit",
                "source_dirty",
            }
        },
    )
    output = tmp_path / "merged.json"
    with pytest.raises(ValueError, match=message):
        lockbox.merge_lockbox_manifests(
            [], output=output, metadata=metadata, sample_size=sample_size,
        )
    assert not output.exists()


def test_merge_keeps_distinct_shard_command_args(tmp_path, monkeypatch):
    metadata = {**_lockbox_metadata(), "command_args": []}
    _install_trusted_merge_access(monkeypatch, metadata, sample_size=412)
    paths = []
    for index, family in enumerate(lockbox.LOCKBOX_FAMILIES):
        raw = tmp_path / f"spade-lockbox-{family}-0000-0412.jsonl.gz"
        raw.write_bytes(family.encode()); digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        (tmp_path / f"{raw.name}.sha256").write_text(f"{digest}  {raw.name}\n")
        shard = {"schema": lockbox.MANIFEST_SCHEMA, "status": "COMPLETE", "family": family, "start": 0, "stop": 412, "sample_size": 412, "expected_rows": 1236, "row_count": 1236, "complete": True, "raw_file": raw.name, "raw_sha256": digest, **metadata, "environment_compatibility": lockbox.environment_compatibility_projection(_environment()), "command_args": ["--family", family, "--out", str(raw), str(index)]}
        path = tmp_path / f"{raw.name}.manifest.json"; path.write_text(json.dumps(shard)); paths.append(path)
    merged = lockbox.merge_lockbox_manifests(paths, output=tmp_path / "merged.json", metadata=metadata, sample_size=412)
    expected = {family: ["--family", family, "--out", str(tmp_path / f"spade-lockbox-{family}-0000-0412.jsonl.gz"), str(index)] for index, family in enumerate(lockbox.LOCKBOX_FAMILIES)}
    assert {item["family"]: item["command_args"] for item in merged["raw_shards"]} == expected


def test_shard_local_grid_rejects_globally_complete_relocation():
    def rows(start: int, stop: int) -> list[dict[str, object]]:
        return [
            {
                "family": "soft_plateau",
                "instance_seed": key,
                "campaign_seed": 0,
                "arm": arm,
            }
            for key in range(start, stop)
            for arm in lockbox.LOCKBOX_ARMS
        ]

    left, right = rows(0, 2), rows(2, 4)
    left[-3:], right[:3] = right[:3], left[-3:]
    assert {
        (row["instance_seed"], row["arm"]) for row in left + right
    } == {(key, arm) for key in range(4) for arm in lockbox.LOCKBOX_ARMS}
    with pytest.raises(ValueError, match="local key/arm grid"):
        lockbox.validate_shard_local_rows(
            left, family="soft_plateau", start=0, stop=2, sample_size=350
        )
    with pytest.raises(ValueError, match="local key/arm grid"):
        lockbox.validate_shard_local_rows(
            right, family="soft_plateau", start=2, stop=4, sample_size=350
        )


def test_runner_source_cannot_depend_on_development_outcome_metrics():
    lockbox.assert_no_development_metric_dependency()


def test_runner_freeze_hash_matches_current_generator_manifest_bytes():
    path = lockbox.ROOT / "results" / "spade-lockbox-generator-manifest.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == lockbox.GENERATOR_FREEZE_SHA256


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


def _registered_provenance(sample_size: int) -> dict[str, object]:
    return {
        "protocol_digest": PROTOCOL,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": "c" * 64,
        "source_commit": CURRENT_SOURCE,
        "selected_protocol_sha256": "b" * 64,
        "power_plan_sha256": POWER_HASH,
        "power_source_commit": POWER_SOURCE,
        "sample_size": sample_size,
        "environment_compatibility": lockbox.environment_compatibility_projection(
            _environment()
        ),
    }


def _registered_rows(sample_size: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for family in lockbox.LOCKBOX_FAMILIES:
        for row in _rows(family, n=sample_size, answers=sample_size, contained=sample_size):
            registered = copy.deepcopy(row)
            registered.update(
                {
                    "schema": "boec-spade-study-row-v1",
                    "protocol_digest": PROTOCOL,
                    "spec_digest": SPEC,
                    "config_digest": CONFIG,
                    "source_commit": CURRENT_SOURCE,
                    "source_dirty": False,
                    "environment": _environment(),
                    "parent_artifacts": {
                        "generator": GENERATOR,
                        "generator_manifest": "c" * 64,
                        "selected_protocol": "b" * 64,
                        "power_plan": POWER_HASH,
                    },
                }
            )
            registered["scores"].update(
                {"budget": 48, "terminal_rule": "P", "execution_mode": "REGISTERED"}
            )
            rows.append(registered)
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
            _rows("soft_plateau"), execution_mode="REGISTERED", sample_size=350,
            bootstrap_replicates=17
        )
    test_only = analysis.analyse_lockbox_rows(
        _rows("soft_plateau"), execution_mode="TEST_ONLY", bootstrap_replicates=17
    )
    assert test_only["overall_verdict"] == "FAIL"


@pytest.mark.parametrize("sample_size", [350, 412])
def test_registered_analysis_uses_exact_power_controlled_sample_size(sample_size):
    provenance = _registered_provenance(sample_size)
    result = analysis.analyse_lockbox_rows(
        _registered_rows(sample_size),
        execution_mode="REGISTERED",
        sample_size=sample_size,
        provenance=provenance,
        bootstrap_replicates=17,
        bootstrap_seed=23,
    )
    assert result["schema"] == analysis.SCHEMA
    assert result["overall_verdict"] == "PASS"
    assert result["provenance"] == provenance
    assert result["provenance"]["sample_size"] == sample_size
    assert result["provenance"]["power_plan_sha256"] == POWER_HASH


def test_registered_analysis_accepts_cross_host_executables_but_not_science_drift():
    rows = _registered_rows(350)
    for index, row in enumerate(rows):
        row["environment"]["executable"] = f"/host-{index % 7}/venv/bin/python"
    provenance = _registered_provenance(350)

    result = analysis.analyse_lockbox_rows(
        rows,
        execution_mode="REGISTERED",
        sample_size=350,
        provenance=provenance,
        bootstrap_replicates=17,
    )
    assert result["provenance"]["selected_protocol_sha256"] == "b" * 64
    assert "executable" not in result["provenance"]["environment_compatibility"]

    incompatible = copy.deepcopy(rows)
    incompatible[0]["environment"]["threads"]["torch"] = 8
    with pytest.raises(ValueError, match="environment compatibility"):
        analysis.analyse_lockbox_rows(
            incompatible,
            execution_mode="REGISTERED",
            sample_size=350,
            provenance=provenance,
            bootstrap_replicates=17,
        )


def test_registered_analysis_requires_every_row_selected_protocol_parent():
    rows = _registered_rows(350)
    rows[0]["parent_artifacts"]["selected_protocol"] = "0" * 64
    with pytest.raises(ValueError, match="parent provenance|selected protocol"):
        analysis.analyse_lockbox_rows(
            rows,
            execution_mode="REGISTERED",
            sample_size=350,
            provenance=_registered_provenance(350),
            bootstrap_replicates=17,
        )


def test_registered_analysis_rejects_grid_or_power_provenance_drift():
    rows = _registered_rows(350)
    provenance = _registered_provenance(350)

    missing_arm = rows[:-1]
    with pytest.raises(ValueError, match="exactly|complete paired"):
        analysis.analyse_lockbox_rows(
            missing_arm, execution_mode="REGISTERED", sample_size=350,
            provenance=provenance, bootstrap_replicates=17,
        )

    wrong_parent = copy.deepcopy(rows)
    wrong_parent[0]["parent_artifacts"]["power_plan"] = "0" * 64
    with pytest.raises(ValueError, match="parent provenance|power"):
        analysis.analyse_lockbox_rows(
            wrong_parent, execution_mode="REGISTERED", sample_size=350,
            provenance=provenance, bootstrap_replicates=17,
        )

    wrong_size = {**provenance, "sample_size": 412}
    with pytest.raises(ValueError, match="sample size|provenance"):
        analysis.analyse_lockbox_rows(
            rows, execution_mode="REGISTERED", sample_size=350,
            provenance=wrong_size, bootstrap_replicates=17,
        )


def test_merged_analysis_hashes_actual_power_and_passes_manifest_size(
    tmp_path, monkeypatch
):
    power_payload = {
        "status": "POWERED",
        "source_commit": POWER_SOURCE,
        "decision": {"selected_sample_size": 350},
        "digests": {
            "study_protocol_sha256": PROTOCOL,
            "specification_sha256": SPEC,
            "configuration_sha256": CONFIG,
            "generator_sha256": GENERATOR,
            "generator_manifest_sha256": "c" * 64,
        },
        "selected_protocol": {
            "sha256": "b" * 64,
            "source_commit": SOURCE,
        },
    }
    power_path = tmp_path / "spade-lockbox-power.json"
    power_path.write_bytes(_canonical_bytes(power_payload))
    power_sha256 = hashlib.sha256(power_path.read_bytes()).hexdigest()
    metadata = {**_lockbox_metadata(), "power_plan_sha256": power_sha256}
    _install_trusted_merge_access(monkeypatch, metadata, sample_size=350)
    manifest_paths: list[Path] = []
    rows_by_family = {
        family: [
            row for row in _registered_rows(350) if row["family"] == family
        ]
        for family in lockbox.LOCKBOX_FAMILIES
    }
    for family in lockbox.LOCKBOX_FAMILIES:
        raw = tmp_path / f"spade-lockbox-{family}-0000-0350.jsonl.gz"
        raw.write_bytes(f"raw:{family}".encode("ascii"))
        raw_sha256 = hashlib.sha256(raw.read_bytes()).hexdigest()
        Path(f"{raw}.sha256").write_text(f"{raw_sha256}  {raw.name}\n")
        shard = {
            "schema": lockbox.MANIFEST_SCHEMA,
            "status": "COMPLETE",
            "family": family,
            "start": 0,
            "stop": 350,
            "sample_size": 350,
            "expected_rows": 1050,
            "row_count": 1050,
            "complete": True,
            "raw_file": raw.name,
            "raw_sha256": raw_sha256,
            **metadata,
            "environment_compatibility": lockbox.environment_compatibility_projection(
                _environment()
            ),
            "command_args": ["--family", family],
        }
        manifest_path = Path(f"{raw}.manifest.json")
        manifest_path.write_bytes(_canonical_bytes(shard))
        manifest_paths.append(manifest_path)
    merged_path = tmp_path / "spade-lockbox-manifest.json"
    lockbox.merge_lockbox_manifests(
        manifest_paths, output=merged_path, metadata=metadata, sample_size=350
    )

    monkeypatch.setattr(
        analysis, "validate_power_plan_payload", lambda payload: copy.deepcopy(payload)
    )
    import boec.spade_study as study

    monkeypatch.setattr(
        study,
        "read_jsonl_gzip",
        lambda path, **_kwargs: rows_by_family[
            next(family for family in lockbox.LOCKBOX_FAMILIES if family in Path(path).name)
        ],
    )
    captured: dict[str, object] = {}

    def capture(rows, **kwargs):
        captured.update(rows=rows, **kwargs)
        return {"schema": "captured"}

    monkeypatch.setattr(analysis, "analyse_lockbox_rows", capture)
    assert analysis.analyse_merged_manifest(
        merged_path, power_path=power_path
    ) == {"schema": "captured"}
    assert captured["sample_size"] == 350
    assert captured["provenance"]["power_plan_sha256"] == power_sha256
    assert captured["provenance"]["selected_protocol_sha256"] == "b" * 64
    assert captured["provenance"]["environment_compatibility"] == (
        lockbox.environment_compatibility_projection(_environment())
    )
    assert len(captured["rows"]) == 4 * 350 * 3

    power_path.write_bytes(_canonical_bytes({**power_payload, "status": "changed"}))
    with pytest.raises(ValueError, match="power.*hash"):
        analysis.analyse_merged_manifest(merged_path, power_path=power_path)


def test_shard_schema_and_merged_schema_share_protocol_and_provenance_keys():
    assert lockbox.SHARD_MANIFEST_FIELDS <= lockbox.MERGED_MANIFEST_FIELDS | {"family", "start", "stop", "expected_rows", "row_count", "complete", "raw_file", "raw_sha256", "command_args"}
    assert "protocol_digest" in lockbox.SHARD_MANIFEST_FIELDS
    assert "study_protocol_digest" not in lockbox.MERGED_MANIFEST_FIELDS
    assert "selected_protocol_sha256" in lockbox.SHARD_MANIFEST_FIELDS
    assert {"power_plan_sha256", "power_source_commit"} <= lockbox.SHARD_MANIFEST_FIELDS
    assert "environment_compatibility" in lockbox.SHARD_MANIFEST_FIELDS
    assert "environment_compatibility" in lockbox.MERGED_MANIFEST_FIELDS
    assert lockbox.MANIFEST_SCHEMA == "boec-spade-lockbox-shard-v2"
    assert lockbox.MERGED_MANIFEST_SCHEMA == "boec-spade-lockbox-manifest-v2"
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


def test_failed_access_never_invokes_lockbox_oracle_factory(tmp_path, monkeypatch):
    oracle_calls: list[tuple[object, object]] = []
    monkeypatch.setattr(
        lockbox,
        "validate_lockbox_access",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("access denied")),
    )
    monkeypatch.setattr(
        lockbox,
        "make_lockbox_oracle",
        lambda family, key: oracle_calls.append((family, key)),
    )
    with pytest.raises(ValueError, match="access denied"):
        lockbox.run_lockbox_shard(
            family="soft_plateau",
            start=0,
            stop=1,
            output=tmp_path / "scratch.jsonl.gz",
            limit=1,
            smoke=True,
            repo_root=tmp_path,
        )
    assert oracle_calls == []


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
