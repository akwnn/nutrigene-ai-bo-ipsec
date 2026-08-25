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
    actual_hashes = {"selected_protocol_sha256": selected_sha256}
    raw_shards = []
    for family in release.LOCKBOX_FAMILIES:
        raw_file = f"spade-lockbox-{family}-000-350.jsonl.gz"
        manifest_file = f"{raw_file}.manifest.json"
        sha256_file = f"{raw_file}.sha256"
        raw_digest = hashlib.sha256(raw_file.encode()).hexdigest()
        manifest_digest = hashlib.sha256(manifest_file.encode()).hexdigest()
        sidecar_digest = hashlib.sha256(sha256_file.encode()).hexdigest()
        rows_by_file[raw_file] = [row for row in rows if row["family"] == family]
        actual_hashes.update({
            raw_file: raw_digest,
            manifest_file: manifest_digest,
            sha256_file: sidecar_digest,
        })
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
    payload["actual_hashes"][next(iter(payload["rows"]))] = "f" * 64
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
    assert hashes["merged_manifest_sha256"] == hashlib.sha256(merged.read_bytes()).hexdigest()
    assert hashes["selected_protocol_sha256"] == hashlib.sha256(selection.read_bytes()).hexdigest()
    assert hashes["stored_analysis_sha256"] == hashlib.sha256(stored_analysis.read_bytes()).hexdigest()
    for path in (raw, sidecar, shard_manifest):
        assert hashes[path.name] == hashlib.sha256(path.read_bytes()).hexdigest()
    report = release.build_release_report(**loaded)
    joined = "\n".join(report["violations"]).lower()
    assert "selection hash" in joined
    assert "raw shard hash" in joined
    assert "shard manifest hash" in joined
    assert "sha-256 sidecar hash" in joined


def test_complete_manifest_analysis_and_release_flow_uses_canonical_registered_result(tmp_path):
    payload = _payload()
    manifest = copy.deepcopy(payload["manifest"])
    selection = payload["selection"]
    selection_path = tmp_path / "spade-selected-protocol.json"
    selection_path.write_text(
        json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n"
    )

    for item in manifest["raw_shards"]:
        raw_path = tmp_path / item["raw_file"]
        family_rows = payload["rows"][item["raw_file"]]
        raw_digest = lockbox.write_jsonl_gzip(
            raw_path, family_rows, protocol_digest=DIGEST
        )
        item["raw_sha256"] = raw_digest
        sidecar_path = Path(f"{raw_path}.sha256")
        item["sha256_sha256"] = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
        shard_manifest = {
            "schema": lockbox.MANIFEST_SCHEMA,
            "status": "COMPLETE",
            "family": item["family"],
            "start": 0,
            "stop": 350,
            "sample_size": 350,
            "expected_rows": 1050,
            "row_count": 1050,
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
        shard_manifest_path = tmp_path / item["manifest_file"]
        shard_manifest_path.write_text(
            json.dumps(shard_manifest, sort_keys=True, separators=(",", ":")) + "\n"
        )
        item["manifest_sha256"] = hashlib.sha256(
            shard_manifest_path.read_bytes()
        ).hexdigest()

    manifest_path = tmp_path / "spade-lockbox-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
    )
    stored = analysis.analyse_merged_manifest(manifest_path)
    assert stored == payload["analysis"]
    analysis_path = tmp_path / "spade-lockbox-analysis.json"
    analysis_path.write_text(
        json.dumps(stored, sort_keys=True, separators=(",", ":")) + "\n"
    )

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
    manifest_path.write_text(
        json.dumps(aliased, sort_keys=True, separators=(",", ":")) + "\n"
    )
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
