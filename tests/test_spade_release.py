from __future__ import annotations

import copy
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

import boec.spade_power as power
from boec.spade import SpadeConfig
from boec.spade_power import DEVELOPMENT_FAMILIES, POWER_ENDPOINTS
from scripts import validate_spade_lockbox_release as release
from scripts import analyse_spade_lockbox as analysis
from scripts import run_spade_lockbox as lockbox


DIGEST = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
GENERATOR_MANIFEST = "c" * 64
SOURCE = "1" * 40
POWER_SOURCE = "2" * 40
POWER_SIZE = 350
_DEVELOPMENT_FIXTURES = None


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


@functools.lru_cache(maxsize=2)
def _real_power_decision(status: str) -> dict[str, object]:
    value = -0.01 if status == "POWERED" else 0.03
    held_out = {
        family: {endpoint: [value] * 50 for endpoint in POWER_ENDPOINTS}
        for family in DEVELOPMENT_FAMILIES
    }
    decision = power.plan_lockbox_sample_size(held_out).as_dict()
    assert decision["status"] == status
    assert decision["selected_sample_size"] == (
        POWER_SIZE if status == "POWERED" else None
    )
    return decision


def _power_decision(*, status: str = "POWERED") -> dict[str, object]:
    return copy.deepcopy(_real_power_decision(status))


def _power_payload(
    *, selected_sha256: str, status: str = "POWERED"
) -> dict[str, object]:
    decision = _power_decision(status=status)
    value = -0.01 if status == "POWERED" else 0.03
    candidate = "spade-o44-fixed_hybrid"
    return {
        "schema": "boec-spade-lockbox-power-v1",
        "status": status,
        "source_commit": POWER_SOURCE,
        "source_dirty": False,
        "environment": {
            "python": "3.11.9",
            "numpy": "2.1.0",
            "scipy": "1.14.0",
            "platform": "test-platform",
        },
        "digests": {
            "study_protocol_sha256": DIGEST,
            "specification_sha256": SPEC,
            "configuration_sha256": CONFIG,
            "generator_sha256": GENERATOR,
            "generator_manifest_sha256": GENERATOR_MANIFEST,
            "power_design_sha256": "4" * 64,
            "power_engine_sha256": "5" * 64,
            "power_planner_sha256": "6" * 64,
        },
        "selected_protocol": {
            "file": "spade-selected-protocol.json",
            "sha256": selected_sha256,
            "source_commit": SOURCE,
        },
        "development_artifacts": _development_artifacts(),
        "held_out_proof": {
            "unanimous": True,
            "selected_candidate": candidate,
            "folds": _proof_folds(candidate),
        },
        "held_out_differences": {
            family: {endpoint: [value] * 50 for endpoint in POWER_ENDPOINTS}
            for family in DEVELOPMENT_FAMILIES
        },
        "decision": decision,
        "decision_sha256": _canonical_sha256(decision),
    }


@pytest.fixture(autouse=True)
def _fast_exact_power_recompute(monkeypatch, tmp_path):
    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(analysis, "ROOT", tmp_path)
    monkeypatch.setattr(
        analysis,
        "paired_bootstrap_upper",
        lambda values, **_kwargs: sum(values) / len(values),
    )

    def synthetic_access(*, repo_root, power_path=None, **_kwargs):
        actual_power_path = power_path or repo_root / "results/spade-lockbox-power.json"
        power_bytes = Path(actual_power_path).read_bytes()
        return {
            "selection": {},
            "power_plan": json.loads(power_bytes),
            "sample_size": POWER_SIZE,
            "power_plan_sha256": hashlib.sha256(power_bytes).hexdigest(),
        }

    monkeypatch.setattr(lockbox, "validate_lockbox_access", synthetic_access)


def _selection() -> dict:
    template = SpadeConfig(opening=44, policy="fixed_hybrid", root_seed=0)
    trace = {"rule": "unanimous_lofo_consensus"}
    return {
        "schema": "boec-spade-selected-protocol-v1",
        "status": "SELECTED",
        "selected_candidate": "spade-o44-fixed_hybrid",
        "source_commit": SOURCE,
        "study_protocol_digest": DIGEST,
        "spec_digest": SPEC,
        "config_digest": CONFIG,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "development_artifacts": _development_artifacts(),
        "analysis_file": "spade-development-analysis.json",
        "analysis_sha256": "4" * 64,
        "selection_trace": trace,
        "lofo_folds": _proof_folds("spade-o44-fixed_hybrid"),
        "selection_trace_digest": hashlib.sha256(
            json.dumps(trace, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "selected_canonical_config": json.loads(template.canonical_json),
        "selected_canonical_config_json": template.canonical_json,
        "selected_template_protocol_digest": template.protocol_digest,
        "campaign_root_seed_binding": "sha256_labelled_derived_per_campaign",
    }


def _row(family="soft_plateau", key=0, arm="spade"):
    global _DEVELOPMENT_FIXTURES
    if _DEVELOPMENT_FIXTURES is None:
        spec = importlib.util.spec_from_file_location("synthetic_development_rows", Path(__file__).with_name("test_spade_development.py"))
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _DEVELOPMENT_FIXTURES = module
    module = _DEVELOPMENT_FIXTURES
    arm_id = "spade-o44-fixed_hybrid" if arm == "spade" else arm
    row = module._row("hill", key % 50, arm_id)
    row["family"] = family
    row["instance_seed"] = key
    row["campaign_seed"] = 0
    row["campaign_key"].update(family=family, instance_seed=key, campaign_seed=0)
    row["parent_artifacts"]["generator_manifest"] = GENERATOR_MANIFEST
    row["scores"].update(
        map_loss=.09 if arm == "spade" else (.10 if arm == "sobol48" else .20),
        regret_rule_p=.09 if arm == "spade" else (.20 if arm == "sobol48" else .10),
        certificate_nonempty=arm == "spade",
        certificate_volume=.1 if arm == "spade" else 0.0,
        certificate_selection_containment=.96 if arm == "spade" else None,
        certificate_crossfit_containment=.94 if arm == "spade" else None,
        certificate_empirical_containment=True if arm == "spade" else None,
    )
    return row


@functools.lru_cache(maxsize=1)
def _base_payload():
    selection = _selection()
    selection_bytes = _canonical_bytes(selection)
    selected_sha256 = hashlib.sha256(selection_bytes).hexdigest()
    power_plan = _power_payload(selected_sha256=selected_sha256)
    power_sha256 = hashlib.sha256(_canonical_bytes(power_plan)).hexdigest()
    rows = [_row(family=family, key=key, arm=arm) for family in release.LOCKBOX_FAMILIES for key in range(POWER_SIZE) for arm in ("spade", "sobol48", "qlognei48")]
    for row in rows:
        row["parent_artifacts"]["selected_protocol"] = selected_sha256
        row["parent_artifacts"]["power_plan"] = power_sha256
    provenance = {
        "protocol_digest": DIGEST, "spec_digest": SPEC, "config_digest": CONFIG,
        "generator_digest": GENERATOR, "generator_manifest_sha256": GENERATOR_MANIFEST,
        "selected_protocol_sha256": selected_sha256,
        "source_commit": SOURCE, "power_plan_sha256": power_sha256,
        "power_source_commit": POWER_SOURCE, "sample_size": POWER_SIZE,
        "environment_compatibility": lockbox.environment_compatibility_projection(
            rows[0]["environment"]
        ),
    }
    calculated = analysis.analyse_lockbox_rows(
        rows, sample_size=POWER_SIZE, provenance=provenance
    )
    rows_by_file = {}
    actual_hashes = {
        "top_level": {
            "selected_protocol_sha256": selected_sha256,
            "power_plan_sha256": power_sha256,
        },
        "raw_shards": {},
    }
    raw_shards = []
    for family in release.LOCKBOX_FAMILIES:
        raw_file = f"spade-lockbox-{family}-0000-{POWER_SIZE:04d}.jsonl.gz"
        manifest_file = f"{raw_file}.manifest.json"
        sha256_file = f"{raw_file}.sha256"
        raw_digest = hashlib.sha256(raw_file.encode()).hexdigest()
        manifest_digest = hashlib.sha256(manifest_file.encode()).hexdigest()
        sidecar_digest = hashlib.sha256(sha256_file.encode()).hexdigest()
        rows_by_file[raw_file] = [row for row in rows if row["family"] == family]
        actual_hashes["raw_shards"][raw_file] = {
            "raw_sha256": raw_digest,
            "manifest_sha256": manifest_digest,
            "sha256_sha256": sidecar_digest,
        }
        raw_shards.append({
            "family": family,
            "start": 0,
            "stop": POWER_SIZE,
            "raw_file": raw_file,
            "raw_sha256": raw_digest,
            "command_args": ["--family", family],
            "manifest_file": manifest_file,
            "manifest_sha256": manifest_digest,
            "sha256_file": sha256_file,
            "sha256_sha256": sidecar_digest,
        })
    return {
        "manifest": {
            "schema": lockbox.MERGED_MANIFEST_SCHEMA,
            "status": "COMPLETE", "sample_size": POWER_SIZE, "protocol_digest": DIGEST,
            "source_commit": SOURCE, "source_dirty": False, "generator_digest": GENERATOR,
            "spec_digest": SPEC, "config_digest": CONFIG, "generator_manifest_sha256": GENERATOR_MANIFEST,
            "selected_protocol_sha256": selected_sha256,
            "selection_source_commit": SOURCE,
            "power_plan_sha256": power_sha256,
            "power_source_commit": POWER_SOURCE,
            "environment_compatibility": provenance["environment_compatibility"],
            "raw_shards": raw_shards,
        },
        "selection": selection,
        "power_plan": power_plan,
        "analysis": calculated,
        "rows": rows_by_file,
        "actual_hashes": actual_hashes,
    }


def _payload():
    return copy.deepcopy(_base_payload())


def _write_complete_release_tree(tmp_path: Path) -> dict[str, object]:
    payload = _payload()
    (
        selection_source,
        power_source,
        power_code_digests,
        protocol_digest,
        config_digest,
    ) = _init_source_repo(tmp_path)
    payload["selection"].update(
        study_protocol_digest=protocol_digest,
        config_digest=config_digest,
    )
    payload["power_plan"]["digests"].update(
        study_protocol_sha256=protocol_digest,
        configuration_sha256=config_digest,
    )
    payload["manifest"].update(
        protocol_digest=protocol_digest,
        config_digest=config_digest,
    )
    for shard_rows in payload["rows"].values():
        for row in shard_rows:
            row["protocol_digest"] = protocol_digest
            row["config_digest"] = config_digest
            row["parent_artifacts"]["config"] = config_digest
    payload["selection"]["source_commit"] = selection_source
    selection_path = tmp_path / "spade-selected-protocol.json"
    selection_path.write_bytes(_canonical_bytes(payload["selection"]))
    selected_sha256 = hashlib.sha256(selection_path.read_bytes()).hexdigest()
    payload["power_plan"]["source_commit"] = power_source
    payload["power_plan"]["selected_protocol"].update(
        sha256=selected_sha256, source_commit=selection_source
    )
    payload["power_plan"]["digests"].update(power_code_digests)
    power_path = tmp_path / "results" / "spade-lockbox-power.json"
    power_path.parent.mkdir(exist_ok=True)
    power_path.write_bytes(_canonical_bytes(payload["power_plan"]))
    _commit_path(tmp_path, power_path, "freeze power")
    execution_source = _git_head(tmp_path)
    power_sha256 = hashlib.sha256(power_path.read_bytes()).hexdigest()
    payload["manifest"].update(
        source_commit=execution_source,
        selected_protocol_sha256=selected_sha256,
        selection_source_commit=selection_source,
        power_plan_sha256=power_sha256,
        power_source_commit=power_source,
    )
    for shard_rows in payload["rows"].values():
        for row in shard_rows:
            row["source_commit"] = execution_source
            row["parent_artifacts"]["selected_protocol"] = selected_sha256
            row["parent_artifacts"]["power_plan"] = power_sha256
    all_rows = [row for values in payload["rows"].values() for row in values]
    provenance = {
        "protocol_digest": protocol_digest,
        "spec_digest": SPEC,
        "config_digest": config_digest,
        "generator_digest": GENERATOR,
        "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": execution_source,
        "selected_protocol_sha256": selected_sha256,
        "power_plan_sha256": power_sha256,
        "power_source_commit": power_source,
        "sample_size": POWER_SIZE,
        "environment_compatibility": lockbox.environment_compatibility_projection(
            all_rows[0]["environment"]
        ),
    }
    payload["analysis"] = analysis.analyse_lockbox_rows(
        all_rows, sample_size=POWER_SIZE, provenance=provenance
    )
    payload["actual_hashes"]["top_level"].update(
        selected_protocol_sha256=selected_sha256,
        power_plan_sha256=power_sha256,
    )
    manifest = copy.deepcopy(payload["manifest"])
    for item in manifest["raw_shards"]:
        _rewrite_shard(
            tmp_path,
            manifest,
            item,
            copy.deepcopy(payload["rows"][item["raw_file"]]),
        )
    manifest_path = tmp_path / "spade-lockbox-manifest.json"
    _write_json(manifest_path, manifest)
    stored = analysis.analyse_merged_manifest(manifest_path, power_path=power_path)
    assert stored == payload["analysis"]
    analysis_path = tmp_path / "spade-lockbox-analysis.json"
    _write_json(analysis_path, stored)
    return {
        "payload": payload,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "selection_path": selection_path,
        "power_path": power_path,
        "analysis_path": analysis_path,
        "selection_source_commit": selection_source,
        "power_source_commit": power_source,
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def _git_head(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_path(repo_root: Path, path: Path, message: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), "add", str(path.relative_to(repo_root))],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-q", "-m", message],
        check=True,
    )


def _init_source_repo(
    repo_root: Path,
) -> tuple[str, str, dict[str, str], str, str]:
    subprocess.run(["git", "init", "-q", str(repo_root)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "SPADE test"],
        check=True,
    )
    registered = {
        "power_design_sha256": (
            Path("docs/superpowers/specs/2026-08-25-spade-lockbox-power-design.md"),
            b"registered power design\n",
        ),
        "power_engine_sha256": (
            Path("src/boec/spade_power.py"), b"registered power engine\n"
        ),
        "power_planner_sha256": (
            Path("scripts/plan_spade_lockbox_power.py"), b"registered power planner\n"
        ),
    }
    project_root = Path(__file__).resolve().parents[1]
    execution_paths = (
        Path("configs/experiment/spade-joint.yaml"),
        Path(".github/workflows/spade-distributed.yml"),
        Path("scripts/make_spade_actions_matrix.py"),
        Path("scripts/run_spade_actions_worker.py"),
        Path("scripts/merge_spade_development_shards.py"),
        Path("requirements.txt"),
    )
    for path in execution_paths:
        destination = repo_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((project_root / path).read_bytes())
        subprocess.run(
            ["git", "-C", str(repo_root), "add", path.as_posix()], check=True
        )
    for path, data in registered.values():
        destination = repo_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        subprocess.run(
            ["git", "-C", str(repo_root), "add", path.as_posix()], check=True
        )
    source_root = Path(__file__).resolve().parents[1]
    for path in release.EXECUTION_SOURCE_BLOBS:
        destination = repo_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((source_root / path).read_bytes())
        subprocess.run(
            ["git", "-C", str(repo_root), "add", path.as_posix()], check=True
        )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-q", "-m", "selection source"],
        check=True,
    )
    selection_source = _git_head(repo_root)
    marker = repo_root / "power-source-marker.txt"
    marker.write_text("power source\n")
    _commit_path(repo_root, marker, "power source")
    power_source = _git_head(repo_root)
    digests = {
        name: hashlib.sha256(data).hexdigest()
        for name, (_path, data) in registered.items()
    }
    config_path = repo_root / "configs/experiment/spade-joint.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return (
        selection_source,
        power_source,
        digests,
        str(config["digests"]["protocol_payload_sha256"]),
        hashlib.sha256(config_path.read_bytes()).hexdigest(),
    )


def _init_power_repo(repo_root: Path, power_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo_root)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "SPADE test"],
        check=True,
    )
    _commit_path(repo_root, power_path, "freeze power")


def _commit_power(tree: dict[str, object]) -> None:
    repo_root = Path(tree["power_path"]).parents[1]
    power_path = Path(tree["power_path"])
    _commit_path(repo_root, power_path, "replace power")


def _rewrite_shard(
    directory: Path,
    manifest: dict[str, object],
    item: dict[str, object],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    raw_path = directory / item["raw_file"]
    raw_digest = lockbox.write_jsonl_gzip(
        raw_path, rows, protocol_digest=str(manifest["protocol_digest"])
    )
    item["raw_sha256"] = raw_digest
    sidecar_path = Path(f"{raw_path}.sha256")
    item["sha256_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    shard_manifest = {
        "schema": lockbox.MANIFEST_SCHEMA,
        "status": "COMPLETE",
        "family": item["family"],
        "start": item["start"],
        "stop": item["stop"],
        "sample_size": manifest["sample_size"],
        "expected_rows": (item["stop"] - item["start"]) * 3,
        "row_count": len(rows),
        "complete": True,
        "raw_file": item["raw_file"],
        "raw_sha256": raw_digest,
        "protocol_digest": manifest["protocol_digest"],
        "spec_digest": manifest["spec_digest"],
        "config_digest": manifest["config_digest"],
        "generator_digest": manifest["generator_digest"],
        "generator_manifest_sha256": manifest["generator_manifest_sha256"],
        "source_commit": manifest["source_commit"],
        "source_dirty": False,
        "selected_protocol_sha256": manifest["selected_protocol_sha256"],
        "selection_source_commit": manifest["selection_source_commit"],
        "power_plan_sha256": manifest["power_plan_sha256"],
        "power_source_commit": manifest["power_source_commit"],
        "environment_compatibility": manifest["environment_compatibility"],
        "command_args": item["command_args"],
    }
    shard_manifest_path = directory / item["manifest_file"]
    _write_json(shard_manifest_path, shard_manifest)
    item["manifest_sha256"] = hashlib.sha256(shard_manifest_path.read_bytes()).hexdigest()
    return shard_manifest


def _rewrite_merged(tree: dict[str, object]) -> None:
    _write_json(tree["manifest_path"], tree["manifest"])


def _run_release_main(
    tmp_path: Path, *, manifest_text: str, analysis_text: str, selection_text: str = "{}",
    power_text: str = "{}",
) -> dict[str, object]:
    manifest = tmp_path / "manifest.json"
    selection = tmp_path / "selection.json"
    stored_analysis = tmp_path / "analysis.json"
    output = tmp_path / "release.json"
    power_path = tmp_path / "results" / "spade-lockbox-power.json"
    power_path.parent.mkdir()
    manifest.write_text(manifest_text)
    selection.write_text(selection_text)
    stored_analysis.write_text(analysis_text)
    power_path.write_text(power_text)
    _init_power_repo(tmp_path, power_path)
    code = release.main([
        "--manifest", str(manifest),
        "--selection", str(selection),
        "--analysis", str(stored_analysis),
        "--power", str(power_path),
        "--out", str(output),
    ])
    assert code == 2
    report = json.loads(output.read_text())
    assert report["schema"] == "boec-spade-lockbox-release-v2"
    assert report["verdict"] == "FAIL"
    assert report["violations"]
    assert set(report) == {
        "schema", "checks", "hashes", "row_counts", "manifest_sample_size",
        "power_status", "selected_sample_size", "verdict", "violations",
        "permissible_claim",
    }
    return report


def _run_complete_tree(
    tree: dict[str, object], *, power_path: Path | None = None
) -> dict[str, object]:
    output = Path(tree["manifest_path"]).parent / "release.json"
    code = release.main([
        "--manifest", str(tree["manifest_path"]),
        "--selection", str(tree["selection_path"]),
        "--power", str(power_path or tree["power_path"]),
        "--analysis", str(tree["analysis_path"]),
        "--out", str(output),
    ])
    report = json.loads(output.read_text())
    assert report["schema"] == "boec-spade-lockbox-release-v2"
    assert code == (0 if report["verdict"] == "PASS" else 2)
    return report


def _forbid_outcome_reads(monkeypatch) -> None:
    original_loader = release._load_json_mapping

    def guarded_loader(path, *, key, label, hashes, violations):
        if label == "stored analysis":
            raise AssertionError("stored analysis opened before power preflight passed")
        return original_loader(
            path, key=key, label=label, hashes=hashes, violations=violations
        )

    monkeypatch.setattr(release, "_load_json_mapping", guarded_loader)

    import boec.spade_study as study

    def forbidden_raw_reader(*_args, **_kwargs):
        raise AssertionError("raw outcome opened before power preflight passed")

    monkeypatch.setattr(study, "read_jsonl_gzip", forbidden_raw_reader)
    monkeypatch.setattr(study, "read_jsonl_gzip_bytes", forbidden_raw_reader)


def _analysis_with_bound_literal(literal: str) -> str:
    endpoint_names = (
        "map_noninferiority",
        "regret_noninferiority",
        "certificate_willingness",
        "certificate_validity",
    )
    endpoints = ",".join(
        f'"{name}":{{"one_sided_bound":{literal},"margin":0.02,"verdict":"FAIL"}}'
        for name in endpoint_names
    )
    families = ",".join(
        f'"{family}":{{{endpoints}}}' for family in release.LOCKBOX_FAMILIES
    )
    return f'{{"families":{{{families}}},"overall_verdict":"FAIL"}}'


def test_release_validator_collects_every_registered_corruption():
    payload = _payload()
    rows = payload["rows"][next(iter(payload["rows"]))]
    rows.pop()
    rows.append(copy.deepcopy(rows[0]))  # duplicate plus missing qLogNEI key
    rows[0]["budget"] = 47
    rows[1]["terminal_rule"] = "X"
    rows[0]["source_dirty"] = True
    rows[1]["environment"] = {"python": "other"}
    rows[0]["parent_artifacts"]["generator"] = "bad"
    rows[1]["protocol_digest"] = "b" * 64
    rows[0]["scores"]["certificate_nonempty"] = False
    rows[0]["scores"]["certificate_empirical_containment"] = True
    payload["manifest"]["sample_size"] = 2
    payload["manifest"]["lockbox_started_before_selection_commit"] = True
    payload["analysis"]["permissible_claim"] = "SPADE beats everything"
    payload["manifest"]["raw_shards"].append({"raw_file": "absent.jsonl.gz", "raw_sha256": "0" * 64})
    payload["actual_hashes"]["raw_shards"][next(iter(payload["rows"]))][
        "raw_sha256"
    ] = "f" * 64
    violations = release.collect_release_violations(**payload)
    expected = {
        "missing campaign key", "duplicate campaign key", "budget", "terminal rule", "dirty",
        "environment", "parent", "protocol", "premature", "certificate denominator",
        "absent raw shard", "sample size", "unsupported prose claim", "hash",
    }
    joined = "\n".join(violations).lower()
    assert all(fragment in joined for fragment in expected)
    assert len(violations) >= len(expected)


def test_clean_release_uses_only_computed_permissible_claim(tmp_path):
    payload = _payload()
    report = release.build_release_report(**payload)
    assert report["verdict"] == "PASS"
    assert report["violations"] == []
    assert report["permissible_claim"] == release.PERMISSIBLE_PASS_CLAIM
    path = tmp_path / "release.json"
    release.write_release_report(path, report)
    assert json.loads(path.read_text()) == report
    original = path.read_bytes()
    with pytest.raises(ValueError, match="immutable|exists"):
        release.write_release_report(path, {**report, "verdict": "FAIL"})
    assert path.read_bytes() == original


def test_pass_claim_is_rejected_when_a_computed_primary_bound_fails():
    payload = _payload()
    payload["analysis"]["families"]["soft_plateau"]["map_noninferiority"]["one_sided_bound"] = .02
    violations = release.collect_release_violations(**payload)
    assert any("computed primary bound" in violation for violation in violations)


def test_release_recomputes_bounds_instead_of_trusting_fabricated_analysis():
    payload = _payload()
    payload["analysis"]["families"]["soft_plateau"]["certificate_validity"]["denominator"] = 999
    violations = release.collect_release_violations(**payload)
    assert any("recomputed" in violation for violation in violations)


def test_release_collects_schema_and_parse_violations_without_raising():
    violations = release.collect_release_violations(
        manifest={"raw_shards": [None, {"raw_file": 4}]}, selection={},
        power_plan={}, analysis={},
        rows={"broken": [None]}, actual_hashes={},
    )
    assert any("schema" in violation or "invalid raw shard" in violation for violation in violations)


def test_release_binds_exact_selection_hash_schema_and_all_frozen_identities():
    payload = _payload()
    payload["manifest"]["selected_protocol_sha256"] = "0" * 64
    payload["selection"].update(
        study_protocol_digest="1" * 64,
        source_commit="2" * 40,
        spec_digest="3" * 64,
        config_digest="4" * 64,
        generator_digest="5" * 64,
        generator_manifest_sha256="6" * 64,
        unexpected="field",
    )
    violations = release.collect_release_violations(**payload)
    joined = "\n".join(violations).lower()
    for fragment in (
        "selection hash",
        "selection schema",
        "study protocol",
        "selection source",
        "selection spec",
        "selection config",
        "selection generator source",
        "selection generator manifest",
    ):
        assert fragment in joined


def test_release_compares_the_complete_canonical_registered_analysis():
    payload = _payload()
    payload["analysis"].update(
        schema="wrong-schema",
        execution_mode="TEST_ONLY",
        provenance={"fabricated": True},
        primary_rule="pooled",
        secondary={"pooled": {"does_not_change_primary": False}},
    )
    violations = release.collect_release_violations(**payload)
    assert any("canonical" in violation and "recomputed" in violation for violation in violations)


def test_release_uses_selected_hash_and_environment_compatibility_provenance():
    payload = _payload()
    provenance = payload["analysis"]["provenance"]
    assert provenance["selected_protocol_sha256"] == payload["manifest"][
        "selected_protocol_sha256"
    ]
    assert provenance["environment_compatibility"] == payload["manifest"][
        "environment_compatibility"
    ]
    assert "executable" not in provenance["environment_compatibility"]

    host_only = _payload()
    first_rows = host_only["rows"][next(iter(host_only["rows"]))]
    first_rows[0]["environment"]["executable"] = "/another/compatible/python"
    assert release.collect_release_violations(**host_only) == []

    incompatible = _payload()
    first_rows = incompatible["rows"][next(iter(incompatible["rows"]))]
    first_rows[0]["environment"]["threads"]["torch"] += 1
    violations = release.collect_release_violations(**incompatible)
    assert any("environment compatibility" in value for value in violations)


def test_release_loader_hashes_every_actual_artifact_and_detects_binding_drift(tmp_path):
    tree = _write_complete_release_tree(tmp_path)
    first = tree["manifest"]["raw_shards"][0]
    raw = tmp_path / first["raw_file"]
    sidecar = tmp_path / first["sha256_file"]
    shard_manifest = tmp_path / first["manifest_file"]
    raw.write_bytes(b"not-a-gzip")
    sidecar.write_text("tampered sidecar\n")
    shard_manifest.write_text('{"status":"TAMPERED"}\n')

    loaded = release.load_release_inputs(
        manifest_path=tree["manifest_path"],
        selection_path=tree["selection_path"],
        power_path=tree["power_path"],
        analysis_path=tree["analysis_path"],
    )
    hashes = loaded["actual_hashes"]
    assert hashes["top_level"]["power_plan_sha256"] == hashlib.sha256(
        Path(tree["power_path"]).read_bytes()
    ).hexdigest()
    assert hashes["raw_shards"][raw.name] == {
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(shard_manifest.read_bytes()).hexdigest(),
        "sha256_sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
    }
    report = release.build_release_report(**loaded)
    joined = "\n".join(report["violations"]).lower()
    assert "raw shard hash" in joined
    assert "shard manifest hash" in joined
    assert "sha-256 sidecar hash" in joined


@pytest.mark.parametrize(
    "reserved_name",
    ["merged_manifest_sha256", "stored_analysis_sha256", "power_plan_sha256"],
)
def test_release_hash_namespaces_cannot_be_overwritten_by_reserved_raw_names(
    tmp_path, reserved_name
):
    tree = _write_complete_release_tree(tmp_path)
    manifest = tree["manifest"]
    first = manifest["raw_shards"][0]
    original_raw = tmp_path / first["raw_file"]
    reserved_raw = tmp_path / reserved_name
    reserved_raw.write_bytes(original_raw.read_bytes())
    raw_digest = hashlib.sha256(reserved_raw.read_bytes()).hexdigest()
    reserved_sidecar = Path(f"{reserved_raw}.sha256")
    reserved_sidecar.write_text(f"{raw_digest}  {reserved_name}\n")
    original_shard_manifest = json.loads((tmp_path / first["manifest_file"]).read_text())
    original_shard_manifest.update(raw_file=reserved_name, raw_sha256=raw_digest)
    reserved_manifest = Path(f"{reserved_raw}.manifest.json")
    _write_json(reserved_manifest, original_shard_manifest)
    first.update(
        raw_file=reserved_name,
        raw_sha256=raw_digest,
        manifest_file=reserved_manifest.name,
        manifest_sha256=hashlib.sha256(reserved_manifest.read_bytes()).hexdigest(),
        sha256_file=reserved_sidecar.name,
        sha256_sha256=hashlib.sha256(reserved_sidecar.read_bytes()).hexdigest(),
    )
    _rewrite_merged(tree)

    loaded = release.load_release_inputs(
        manifest_path=tree["manifest_path"],
        selection_path=tree["selection_path"],
        power_path=tree["power_path"],
        analysis_path=tree["analysis_path"],
    )
    hashes = loaded["actual_hashes"]
    assert hashes["top_level"]["merged_manifest_sha256"] == hashlib.sha256(
        tree["manifest_path"].read_bytes()
    ).hexdigest()
    assert hashes["top_level"]["stored_analysis_sha256"] == hashlib.sha256(
        tree["analysis_path"].read_bytes()
    ).hexdigest()
    assert hashes["raw_shards"][reserved_name]["raw_sha256"] == raw_digest
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "FAIL"
    assert any("exact registered raw filename" in value for value in report["violations"])
    with pytest.raises(ValueError, match="exact registered raw filename"):
        analysis.analyse_merged_manifest(
            tree["manifest_path"], power_path=tree["power_path"]
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("complete", False, "completion"),
        ("sample_size", 349, "sample size"),
        ("expected_rows", 1049, "expected row count"),
        ("row_count", 1049, "row count"),
        ("command_args", ["--tampered"], "command args"),
    ],
)
def test_release_and_manifest_analysis_reject_every_shard_contract_drift(
    tmp_path, field, value, message
):
    tree = _write_complete_release_tree(tmp_path)
    first = tree["manifest"]["raw_shards"][0]
    shard_path = tmp_path / first["manifest_file"]
    shard = json.loads(shard_path.read_text())
    shard[field] = value
    _write_json(shard_path, shard)
    first["manifest_sha256"] = hashlib.sha256(shard_path.read_bytes()).hexdigest()
    _rewrite_merged(tree)

    loaded = release.load_release_inputs(
        manifest_path=tree["manifest_path"],
        selection_path=tree["selection_path"],
        power_path=tree["power_path"],
        analysis_path=tree["analysis_path"],
    )
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "FAIL"
    assert any(message in value for value in report["violations"])
    with pytest.raises(ValueError, match=message):
        analysis.analyse_merged_manifest(
            tree["manifest_path"], power_path=tree["power_path"]
        )


def test_release_and_manifest_analysis_reject_cross_shard_row_relocation(tmp_path):
    tree = _write_complete_release_tree(tmp_path)
    manifest = tree["manifest"]
    left, right = manifest["raw_shards"][:2]
    left_rows = copy.deepcopy(tree["payload"]["rows"][left["raw_file"]])
    right_rows = copy.deepcopy(tree["payload"]["rows"][right["raw_file"]])
    left_rows[0], right_rows[0] = right_rows[0], left_rows[0]
    _rewrite_shard(tmp_path, manifest, left, left_rows)
    _rewrite_shard(tmp_path, manifest, right, right_rows)
    _rewrite_merged(tree)

    loaded = release.load_release_inputs(
        manifest_path=tree["manifest_path"],
        selection_path=tree["selection_path"],
        power_path=tree["power_path"],
        analysis_path=tree["analysis_path"],
    )
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "FAIL"
    assert any("exact local key/arm grid" in value for value in report["violations"])
    with pytest.raises(ValueError, match="exact local key/arm grid"):
        analysis.analyse_merged_manifest(
            tree["manifest_path"], power_path=tree["power_path"]
        )


def test_complete_manifest_analysis_and_release_flow_uses_canonical_registered_result(tmp_path):
    tree = _write_complete_release_tree(tmp_path)
    manifest = tree["manifest"]
    manifest_path = tree["manifest_path"]
    selection_path = tree["selection_path"]
    power_path = tree["power_path"]
    analysis_path = tree["analysis_path"]

    loaded = release.load_release_inputs(
        manifest_path=manifest_path,
        selection_path=selection_path,
        power_path=power_path,
        analysis_path=analysis_path,
    )
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "PASS"
    assert report["violations"] == []

    aliased = copy.deepcopy(manifest)
    first = aliased["raw_shards"][0]
    alias_sidecar = tmp_path / "aliased.sha256"
    alias_sidecar.write_bytes((tmp_path / first["sha256_file"]).read_bytes())
    alias_manifest = tmp_path / "aliased.manifest.json"
    alias_manifest.write_bytes((tmp_path / first["manifest_file"]).read_bytes())
    first["sha256_file"] = alias_sidecar.name
    first["sha256_sha256"] = hashlib.sha256(alias_sidecar.read_bytes()).hexdigest()
    first["manifest_file"] = alias_manifest.name
    first["manifest_sha256"] = hashlib.sha256(alias_manifest.read_bytes()).hexdigest()
    _write_json(manifest_path, aliased)
    loaded = release.load_release_inputs(
        manifest_path=manifest_path,
        selection_path=selection_path,
        power_path=power_path,
        analysis_path=analysis_path,
    )
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "FAIL"
    assert any("artifact filename identity" in value for value in report["violations"])


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing", "missing"),
        ("malformed", "json parse"),
        ("noncanonical", "canonical"),
        ("uncommitted", "committed"),
        ("symlink", "symlink"),
        ("relocated", "registered path"),
        ("other_repo", "registered path"),
    ],
)
def test_release_main_writes_fail_report_for_invalid_power_file(
    tmp_path, monkeypatch, mutation, expected
):
    tree = _write_complete_release_tree(tmp_path)
    power_path = Path(tree["power_path"])
    supplied = power_path
    if mutation == "missing":
        power_path.unlink()
    elif mutation == "malformed":
        power_path.write_text("{")
    elif mutation == "noncanonical":
        power_path.write_text(json.dumps(tree["payload"]["power_plan"], indent=2))
        _commit_power(tree)
    elif mutation == "uncommitted":
        power_path.write_bytes(power_path.read_bytes() + b" ")
    elif mutation == "symlink":
        target = tmp_path / "power-target.json"
        power_path.rename(target)
        os.symlink(target, power_path)
    elif mutation == "relocated":
        supplied = tmp_path / "relocated-power.json"
        supplied.write_bytes(power_path.read_bytes())
    elif mutation == "other_repo":
        supplied = tmp_path / "copied-repository" / "results" / power_path.name
        supplied.parent.mkdir(parents=True)
        supplied.write_bytes(power_path.read_bytes())
        _init_power_repo(supplied.parents[1], supplied)
    _forbid_outcome_reads(monkeypatch)
    report = _run_complete_tree(tree, power_path=supplied)
    assert report["verdict"] == "FAIL"
    assert any(expected in value.lower() for value in report["violations"])


@pytest.mark.parametrize("field_action", ["add", "remove"])
def test_release_rejects_power_schema_addition_or_removal(
    tmp_path, monkeypatch, field_action
):
    tree = _write_complete_release_tree(tmp_path)
    power_plan = copy.deepcopy(tree["payload"]["power_plan"])
    if field_action == "add":
        power_plan["unexpected"] = True
    else:
        del power_plan["environment"]
    Path(tree["power_path"]).write_bytes(_canonical_bytes(power_plan))
    _commit_power(tree)
    _forbid_outcome_reads(monkeypatch)
    report = _run_complete_tree(tree)
    assert any("power plan" in value.lower() and "fields" in value.lower() for value in report["violations"])


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("selection", "selected protocol binding"),
        ("source", "source provenance"),
        ("power_blob", "source blob digest"),
        ("decision_digest", "decision_sha256"),
        ("sample_size", "held-out decision"),
        ("insufficient", "powered"),
    ],
)
def test_release_rejects_every_power_semantic_corruption(
    tmp_path, monkeypatch, mutation, expected
):
    tree = _write_complete_release_tree(tmp_path)
    power_plan = copy.deepcopy(tree["payload"]["power_plan"])
    if mutation == "selection":
        power_plan["selected_protocol"]["sha256"] = "0" * 64
    elif mutation == "source":
        power_plan["source_commit"] = "3" * 40
    elif mutation == "power_blob":
        power_plan["digests"]["power_engine_sha256"] = "0" * 64
    elif mutation == "decision_digest":
        power_plan["decision_sha256"] = "0" * 64
    elif mutation == "sample_size":
        power_plan["decision"]["selected_sample_size"] = POWER_SIZE + 1
        power_plan["decision"]["selected_instance_prefix"] = {
            "first": 0,
            "last": POWER_SIZE,
            "count": POWER_SIZE + 1,
        }
        for family in DEVELOPMENT_FAMILIES:
            for endpoint in POWER_ENDPOINTS:
                power_plan["decision"]["families"][family][endpoint][
                    "reported_n"
                ] = POWER_SIZE + 1
        power_plan["decision_sha256"] = _canonical_sha256(power_plan["decision"])
    else:
        power_plan = _power_payload(
            selected_sha256=tree["manifest"]["selected_protocol_sha256"],
            status="INSUFFICIENT_POWER",
        )
    Path(tree["power_path"]).write_bytes(_canonical_bytes(power_plan))
    _commit_power(tree)
    _forbid_outcome_reads(monkeypatch)
    report = _run_complete_tree(tree)
    assert report["verdict"] == "FAIL"
    assert any(expected in value.lower() for value in report["violations"])


def test_release_rejects_manifest_and_row_power_binding_drift():
    payload = _payload()
    payload["manifest"]["power_plan_sha256"] = "0" * 64
    first_rows = payload["rows"][next(iter(payload["rows"]))]
    first_rows[0]["parent_artifacts"]["power_plan"] = "1" * 64
    violations = release.collect_release_violations(**payload)
    joined = "\n".join(violations).lower()
    assert "power hash" in joined
    assert "parent" in joined


def test_release_rejects_manifest_power_hash_before_outcome_reads(
    tmp_path, monkeypatch
):
    tree = _write_complete_release_tree(tmp_path)
    tree["manifest"]["power_plan_sha256"] = "0" * 64
    _rewrite_merged(tree)
    _forbid_outcome_reads(monkeypatch)
    report = _run_complete_tree(tree)
    assert report["verdict"] == "FAIL"
    assert any("power hash" in value.lower() for value in report["violations"])


@pytest.mark.parametrize(
    "relative",
    [
        "configs/experiment/spade-joint.yaml",
        ".github/workflows/spade-distributed.yml",
        "scripts/make_spade_actions_matrix.py",
        "scripts/run_spade_actions_worker.py",
        "scripts/merge_spade_development_shards.py",
        "requirements.txt",
    ],
)
def test_release_authenticates_execution_source_blobs_before_outcome_reads(
    tmp_path, monkeypatch, relative
):
    tree = _write_complete_release_tree(tmp_path)
    path = tmp_path / relative
    path.write_bytes(path.read_bytes() + b"\n# adversarial execution drift\n")
    _commit_path(tmp_path, path, "execution drift")
    tree["manifest"]["source_commit"] = _git_head(tmp_path)
    _rewrite_merged(tree)

    _forbid_outcome_reads(monkeypatch)
    report = _run_complete_tree(tree)

    assert report["verdict"] == "FAIL"
    assert any(
        "execution source" in value.lower() or "configuration" in value.lower()
        for value in report["violations"]
    )


def test_release_requires_selection_source_to_precede_power_source(
    tmp_path, monkeypatch
):
    tree = _write_complete_release_tree(tmp_path)
    selection = copy.deepcopy(tree["payload"]["selection"])
    selection["source_commit"] = _git_head(tmp_path)
    Path(tree["selection_path"]).write_bytes(_canonical_bytes(selection))
    selected_sha256 = hashlib.sha256(Path(tree["selection_path"]).read_bytes()).hexdigest()
    power_plan = copy.deepcopy(tree["payload"]["power_plan"])
    power_plan["selected_protocol"].update(
        sha256=selected_sha256, source_commit=selection["source_commit"]
    )
    Path(tree["power_path"]).write_bytes(_canonical_bytes(power_plan))
    _commit_power(tree)
    tree["manifest"].update(
        selected_protocol_sha256=selected_sha256,
        power_plan_sha256=hashlib.sha256(
            Path(tree["power_path"]).read_bytes()
        ).hexdigest(),
    )
    _rewrite_merged(tree)
    _forbid_outcome_reads(monkeypatch)
    report = _run_complete_tree(tree)
    assert report["verdict"] == "FAIL"
    assert any(
        "selection source is not an ancestor of power source" in value.lower()
        for value in report["violations"]
    )


def test_release_rejects_post_outcome_execution_code_reinterpretation_before_reads(
    tmp_path, monkeypatch
):
    tree = _write_complete_release_tree(tmp_path)
    analyzer_path = tmp_path / "scripts" / "analyse_spade_lockbox.py"
    analyzer_path.write_text("# post-outcome reinterpretation\n")
    _commit_path(tmp_path, analyzer_path, "alter analyzer after outcomes")
    tree["manifest"]["source_commit"] = _git_head(tmp_path)
    _rewrite_merged(tree)
    _forbid_outcome_reads(monkeypatch)
    report = _run_complete_tree(tree)
    assert report["verdict"] == "FAIL"
    assert any(
        "execution source blob digest mismatch" in value.lower()
        for value in report["violations"]
    )


@pytest.mark.parametrize(
    ("manifest_text", "write_selection", "analysis_text"),
    [
        ("{", False, "[]"),
        ('{"raw_shards":[null,{"raw_file":"missing.jsonl.gz"}]}', True, "{}"),
    ],
)
def test_release_main_always_writes_complete_fail_report_for_malformed_inputs(
    tmp_path, manifest_text, write_selection, analysis_text
):
    manifest = tmp_path / "manifest.json"
    selection = tmp_path / "selection.json"
    stored_analysis = tmp_path / "analysis.json"
    output = tmp_path / "release.json"
    power_path = tmp_path / "results" / "spade-lockbox-power.json"
    manifest.write_text(manifest_text)
    if write_selection:
        selection.write_text("{}")
    stored_analysis.write_text(analysis_text)
    power_path.parent.mkdir()
    power_path.write_text("{}")
    _init_power_repo(tmp_path, power_path)

    code = release.main([
        "--manifest", str(manifest),
        "--selection", str(selection),
        "--power", str(power_path),
        "--analysis", str(stored_analysis),
        "--out", str(output),
    ])
    assert code == 2
    report = json.loads(output.read_text())
    assert report["schema"] == "boec-spade-lockbox-release-v2"
    assert report["verdict"] == "FAIL"
    assert report["violations"]
    assert set(report) == {
        "schema", "checks", "hashes", "row_counts", "manifest_sample_size",
        "power_status", "selected_sample_size", "verdict", "violations",
        "permissible_claim",
    }


@pytest.mark.parametrize(
    ("analysis_text", "expected_violation"),
    [
        ('{"value":' + "9" * 5000 + "}", "JSON parse violation"),
        (_analysis_with_bound_literal("1e1000000"), "JSON parse violation"),
        ('{"value":' + "[" * 1200 + "0" + "]" * 1200 + "}", "JSON parse violation"),
    ],
)
def test_release_main_reports_oversized_nonfinite_and_deep_json_without_raising(
    tmp_path, analysis_text, expected_violation
):
    tree = _write_complete_release_tree(tmp_path)
    Path(tree["analysis_path"]).write_text(analysis_text)
    report = _run_complete_tree(tree)
    assert any(expected_violation in value for value in report["violations"])


def test_release_main_reports_endpoint_integer_float_overflow_without_raising(tmp_path):
    tree = _write_complete_release_tree(tmp_path)
    Path(tree["analysis_path"]).write_text(
        _analysis_with_bound_literal("9" * 4000)
    )
    report = _run_complete_tree(tree)
    assert report["verdict"] == "FAIL"
