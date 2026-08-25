from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from boec.spade import SpadeConfig
from scripts import validate_spade_lockbox_release as release
from scripts import analyse_spade_lockbox as analysis
from scripts import run_spade_lockbox as lockbox


DIGEST = "d" * 64
SPEC = "e" * 64
CONFIG = "f" * 64
GENERATOR = "a" * 64
GENERATOR_MANIFEST = "c" * 64
SOURCE = "1" * 40
_DEVELOPMENT_FIXTURES = None


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
        "development_artifacts": [],
        "analysis_file": "spade-development-analysis.json",
        "analysis_sha256": "4" * 64,
        "selection_trace": trace,
        "lofo_folds": [],
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


def _payload():
    selection = _selection()
    selection_bytes = (json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n").encode()
    selected_sha256 = hashlib.sha256(selection_bytes).hexdigest()
    rows = [_row(family=family, key=key, arm=arm) for family in release.LOCKBOX_FAMILIES for key in range(350) for arm in ("spade", "sobol48", "qlognei48")]
    for row in rows:
        row["parent_artifacts"]["selected_protocol"] = selected_sha256
    provenance = {
        "protocol_digest": DIGEST, "spec_digest": SPEC, "config_digest": CONFIG,
        "generator_digest": GENERATOR, "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": SOURCE, "environment": rows[0]["environment"],
    }
    calculated = analysis.analyse_lockbox_rows(rows, provenance=provenance)
    rows_by_file = {}
    actual_hashes = {
        "top_level": {"selected_protocol_sha256": selected_sha256},
        "raw_shards": {},
    }
    raw_shards = []
    for family in release.LOCKBOX_FAMILIES:
        raw_file = f"spade-lockbox-{family}-000-350.jsonl.gz"
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
            "stop": 350,
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
            "status": "COMPLETE", "sample_size": 350, "protocol_digest": DIGEST,
            "source_commit": SOURCE, "source_dirty": False, "generator_digest": GENERATOR,
            "spec_digest": SPEC, "config_digest": CONFIG, "generator_manifest_sha256": GENERATOR_MANIFEST,
            "selected_protocol_sha256": selected_sha256,
            "selection_source_commit": SOURCE,
            "raw_shards": raw_shards,
        },
        "selection": selection,
        "analysis": calculated,
        "rows": rows_by_file,
        "actual_hashes": actual_hashes,
    }


def _write_complete_release_tree(tmp_path: Path) -> dict[str, object]:
    payload = _payload()
    manifest = copy.deepcopy(payload["manifest"])
    selection_path = tmp_path / "spade-selected-protocol.json"
    selection_path.write_text(
        json.dumps(payload["selection"], sort_keys=True, separators=(",", ":")) + "\n"
    )
    for item in manifest["raw_shards"]:
        _rewrite_shard(
            tmp_path,
            manifest,
            item,
            copy.deepcopy(payload["rows"][item["raw_file"]]),
        )
    manifest_path = tmp_path / "spade-lockbox-manifest.json"
    _write_json(manifest_path, manifest)
    stored = analysis.analyse_merged_manifest(manifest_path)
    assert stored == payload["analysis"]
    analysis_path = tmp_path / "spade-lockbox-analysis.json"
    _write_json(analysis_path, stored)
    return {
        "payload": payload,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "selection_path": selection_path,
        "analysis_path": analysis_path,
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def _rewrite_shard(
    directory: Path,
    manifest: dict[str, object],
    item: dict[str, object],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    raw_path = directory / item["raw_file"]
    raw_digest = lockbox.write_jsonl_gzip(raw_path, rows, protocol_digest=DIGEST)
    item["raw_sha256"] = raw_digest
    sidecar_path = Path(f"{raw_path}.sha256")
    item["sha256_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    shard_manifest = {
        "schema": lockbox.MANIFEST_SCHEMA,
        "status": "COMPLETE",
        "family": item["family"],
        "start": item["start"],
        "stop": item["stop"],
        "sample_size": 350,
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
        "command_args": item["command_args"],
    }
    shard_manifest_path = directory / item["manifest_file"]
    _write_json(shard_manifest_path, shard_manifest)
    item["manifest_sha256"] = hashlib.sha256(shard_manifest_path.read_bytes()).hexdigest()
    return shard_manifest


def _rewrite_merged(tree: dict[str, object]) -> None:
    _write_json(tree["manifest_path"], tree["manifest"])


def _run_release_main(
    tmp_path: Path, *, manifest_text: str, analysis_text: str, selection_text: str = "{}"
) -> dict[str, object]:
    manifest = tmp_path / "manifest.json"
    selection = tmp_path / "selection.json"
    stored_analysis = tmp_path / "analysis.json"
    output = tmp_path / "release.json"
    manifest.write_text(manifest_text)
    selection.write_text(selection_text)
    stored_analysis.write_text(analysis_text)
    code = release.main([
        "--manifest", str(manifest),
        "--selection", str(selection),
        "--analysis", str(stored_analysis),
        "--out", str(output),
    ])
    assert code == 2
    report = json.loads(output.read_text())
    assert report["schema"] == "boec-spade-lockbox-release-v1"
    assert report["verdict"] == "FAIL"
    assert report["violations"]
    assert set(report) == {
        "schema", "checks", "hashes", "row_counts", "manifest_sample_size",
        "verdict", "violations", "permissible_claim",
    }
    return report


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
        manifest={"raw_shards": [None, {"raw_file": 4}]}, selection={}, analysis={},
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


def test_release_loader_hashes_every_actual_artifact_and_detects_binding_drift(tmp_path):
    raw = tmp_path / "raw.jsonl.gz"
    sidecar = tmp_path / "raw.jsonl.gz.sha256"
    shard_manifest = tmp_path / "raw.jsonl.gz.manifest.json"
    selection = tmp_path / "spade-selected-protocol.json"
    stored_analysis = tmp_path / "spade-lockbox-analysis.json"
    merged = tmp_path / "spade-lockbox-manifest.json"
    raw.write_bytes(b"not-a-gzip")
    sidecar.write_text("0" * 64 + "  raw.jsonl.gz\n")
    shard_manifest.write_text('{"status":"COMPLETE"}\n')
    selection.write_text("{}\n")
    stored_analysis.write_text("{}\n")
    merged.write_text(json.dumps({
        "schema": lockbox.MERGED_MANIFEST_SCHEMA,
        "status": "COMPLETE",
        "sample_size": 350,
        "raw_shards": [{
            "family": "soft_plateau", "start": 0, "stop": 350,
            "raw_file": raw.name, "raw_sha256": "0" * 64,
            "command_args": [],
            "manifest_file": shard_manifest.name, "manifest_sha256": "0" * 64,
            "sha256_file": sidecar.name, "sha256_sha256": "0" * 64,
        }],
        "protocol_digest": DIGEST, "spec_digest": SPEC, "config_digest": CONFIG,
        "generator_digest": GENERATOR, "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": SOURCE, "source_dirty": False,
        "selected_protocol_sha256": "0" * 64, "selection_source_commit": SOURCE,
    }) + "\n")

    loaded = release.load_release_inputs(
        manifest_path=merged,
        selection_path=selection,
        analysis_path=stored_analysis,
    )
    hashes = loaded["actual_hashes"]
    assert hashes["top_level"] == {
        "merged_manifest_sha256": hashlib.sha256(merged.read_bytes()).hexdigest(),
        "selected_protocol_sha256": hashlib.sha256(selection.read_bytes()).hexdigest(),
        "stored_analysis_sha256": hashlib.sha256(stored_analysis.read_bytes()).hexdigest(),
    }
    assert hashes["raw_shards"][raw.name] == {
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(shard_manifest.read_bytes()).hexdigest(),
        "sha256_sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
    }
    report = release.build_release_report(**loaded)
    joined = "\n".join(report["violations"]).lower()
    assert "selection hash" in joined
    assert "raw shard hash" in joined
    assert "shard manifest hash" in joined
    assert "sha-256 sidecar hash" in joined


@pytest.mark.parametrize("reserved_name", ["merged_manifest_sha256", "stored_analysis_sha256"])
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
        analysis.analyse_merged_manifest(tree["manifest_path"])


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
        analysis_path=tree["analysis_path"],
    )
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "FAIL"
    assert any(message in value for value in report["violations"])
    with pytest.raises(ValueError, match=message):
        analysis.analyse_merged_manifest(tree["manifest_path"])


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
        analysis_path=tree["analysis_path"],
    )
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "FAIL"
    assert any("exact local key/arm grid" in value for value in report["violations"])
    with pytest.raises(ValueError, match="exact local key/arm grid"):
        analysis.analyse_merged_manifest(tree["manifest_path"])


def test_complete_manifest_analysis_and_release_flow_uses_canonical_registered_result(tmp_path):
    tree = _write_complete_release_tree(tmp_path)
    manifest = tree["manifest"]
    manifest_path = tree["manifest_path"]
    selection_path = tree["selection_path"]
    analysis_path = tree["analysis_path"]

    loaded = release.load_release_inputs(
        manifest_path=manifest_path,
        selection_path=selection_path,
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
        analysis_path=analysis_path,
    )
    report = release.build_release_report(**loaded)
    assert report["verdict"] == "FAIL"
    assert any("artifact filename identity" in value for value in report["violations"])


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
    manifest.write_text(manifest_text)
    if write_selection:
        selection.write_text("{}")
    stored_analysis.write_text(analysis_text)

    code = release.main([
        "--manifest", str(manifest),
        "--selection", str(selection),
        "--analysis", str(stored_analysis),
        "--out", str(output),
    ])
    assert code == 2
    report = json.loads(output.read_text())
    assert report["schema"] == "boec-spade-lockbox-release-v1"
    assert report["verdict"] == "FAIL"
    assert report["violations"]
    assert set(report) == {
        "schema", "checks", "hashes", "row_counts", "manifest_sample_size",
        "verdict", "violations", "permissible_claim",
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
    report = _run_release_main(
        tmp_path,
        manifest_text='{"raw_shards":[]}',
        analysis_text=analysis_text,
    )
    assert any(expected_violation in value for value in report["violations"])


def test_release_main_reports_endpoint_integer_float_overflow_without_raising(tmp_path):
    report = _run_release_main(
        tmp_path,
        manifest_text='{"raw_shards":[]}',
        analysis_text=_analysis_with_bound_literal("9" * 4000),
    )
    assert report["verdict"] == "FAIL"
