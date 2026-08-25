from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

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
        certificate_empirical_containment=True if arm == "spade" else None,
    )
    return row


def _payload():
    rows = [_row(family=family, key=key, arm=arm) for family in release.LOCKBOX_FAMILIES for key in range(350) for arm in ("spade", "sobol48", "qlognei48")]
    provenance = {
        "protocol_digest": DIGEST, "spec_digest": SPEC, "config_digest": CONFIG,
        "generator_digest": GENERATOR, "generator_manifest_sha256": GENERATOR_MANIFEST,
        "source_commit": SOURCE, "environment": rows[0]["environment"],
    }
    calculated = analysis.analyse_lockbox_rows(rows, provenance=provenance)
    return {
        "manifest": {
            "status": "COMPLETE", "sample_size": 350, "protocol_digest": DIGEST,
            "source_commit": SOURCE, "source_dirty": False, "generator_digest": GENERATOR,
            "spec_digest": SPEC, "config_digest": CONFIG, "generator_manifest_sha256": GENERATOR_MANIFEST,
            "raw_shards": [{"raw_file": "fixture.jsonl.gz", "raw_sha256": "0" * 64}],
        },
        "selection": {"status": "SELECTED", "study_protocol_digest": DIGEST, "source_commit": SOURCE, "spec_digest": SPEC, "config_digest": CONFIG, "generator_digest": GENERATOR, "generator_manifest_sha256": GENERATOR_MANIFEST},
        "analysis": calculated,
        "rows": {"fixture.jsonl.gz": rows},
        "actual_hashes": {"fixture.jsonl.gz": "0" * 64},
    }


def test_release_validator_collects_every_registered_corruption():
    payload = _payload()
    rows = payload["rows"]["fixture.jsonl.gz"]
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
    payload["actual_hashes"]["fixture.jsonl.gz"] = "f" * 64
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
