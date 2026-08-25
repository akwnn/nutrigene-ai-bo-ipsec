from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import validate_spade_lockbox_release as release


DIGEST = "a" * 64
SOURCE = "1" * 40


def _row(family="soft_plateau", key=0, arm="spade"):
    return {
        "family": family, "instance_seed": key, "campaign_seed": 0, "arm": arm,
        "budget": 48, "terminal_rule": "P", "source_dirty": False,
        "protocol_digest": DIGEST, "spec_digest": DIGEST, "config_digest": DIGEST,
        "source_commit": SOURCE, "environment": {"python": "fixture"},
        "parent_artifacts": {"spec": DIGEST, "config": DIGEST, "generator": DIGEST},
        "scores": {"certificate_nonempty": arm == "spade", "certificate_empirical_containment": True if arm == "spade" else None},
    }


def _payload():
    rows = [_row(family=family, key=key, arm=arm) for family in release.LOCKBOX_FAMILIES for key in range(350) for arm in ("spade", "sobol48", "qlognei48")]
    return {
        "manifest": {
            "status": "COMPLETE", "sample_size": 350, "protocol_digest": DIGEST,
            "source_commit": SOURCE, "source_dirty": False, "generator_digest": DIGEST,
            "raw_shards": [{"raw_file": "fixture.jsonl.gz", "raw_sha256": "0" * 64}],
        },
        "selection": {"status": "SELECTED", "study_protocol_digest": DIGEST, "source_commit": SOURCE},
        "analysis": {
            "overall_verdict": "PASS", "permissible_claim": release.PERMISSIBLE_PASS_CLAIM,
            "families": {
                family: {
                    "map_noninferiority": {"one_sided_bound": .01, "margin": .02, "verdict": "PASS"},
                    "regret_noninferiority": {"one_sided_bound": .01, "margin": .02, "verdict": "PASS"},
                    "certificate_willingness": {"one_sided_bound": .51, "margin": .50, "verdict": "PASS"},
                    "certificate_validity": {"one_sided_bound": .91, "margin": .90, "verdict": "PASS"},
                } for family in release.LOCKBOX_FAMILIES
            },
        },
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
