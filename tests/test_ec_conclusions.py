import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyse_ec_benchmark as analyser  # noqa: E402
import run_ec_benchmark as runner  # noqa: E402


def test_disabled_evaluation_is_refused_with_explicit_reason():
    verdict = analyser.adjudicate(ROOT / "results" / "ec-evaluation.json")
    assert verdict["verdict"] == "REFUSED_INCOMPLETE"
    assert "unseen-seed" in verdict["reason"]


def test_incomplete_artifact_cannot_pass(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(runner.empty_artifact()))
    verdict = analyser.adjudicate(path)
    assert verdict["verdict"] == "REFUSED_INCOMPLETE"


def test_complete_artifact_is_adjudicated_not_refused(tmp_path):
    artifact = runner.empty_artifact()
    artifact["rows"] = [runner._mock_row(f, s, a) for f in runner.FAMILIES for s in runner.EVAL_SEEDS for a in runner.ARMS]
    artifact["status"] = "COMPLETE"
    path = tmp_path / "complete.json"
    path.write_text(json.dumps(artifact))
    verdict = analyser.adjudicate(path)
    assert verdict["verdict"] in analyser.EC_VERDICTS - {"REFUSED_INCOMPLETE"}


def test_verdict_set_is_closed():
    assert analyser.EC_VERDICTS == {
        "PASS_EC_PROSPECTIVE", "FAIL_ANSWER_RATE", "FAIL_CONTAINMENT",
        "FAIL_FALSE_CERTIFICATE", "FAIL_REGRET", "FAIL_ROUNDS", "REFUSED_INCOMPLETE",
    }
