from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_ec_benchmark as runner  # noqa: E402
import analyse_ec_benchmark as analyser  # noqa: E402


def test_defaults_and_seed_separation():
    assert runner.TRAIN_SEEDS == tuple(range(64))
    assert runner.EVAL_SEEDS == tuple(range(64, 96))
    assert runner.WELLS == 48
    assert runner.ROUNDS["spade"] == 5
    assert runner.ROUNDS["doe"] == 3
    assert set(runner.ARMS) == {"spade", "doe", "doe_unscreened", "qlognei"}


def test_dry_run_is_atomic_and_resumable(tmp_path):
    path = tmp_path / "artifact.json"
    artifact = runner.run(out=path, dry_run=True)
    assert path.exists()
    assert artifact["status"] == "PARTIAL"
    assert len(artifact["rows"]) == 4
    resumed = runner.run(out=path, resume=True, dry_run=True)
    assert len(resumed["rows"]) == 4
    assert json.loads(path.read_text())["rows"] == resumed["rows"]


def _complete_artifact():
    artifact = runner.empty_artifact()
    artifact["rows"] = [runner._mock_row(f, s, a) for f in runner.FAMILIES for s in runner.EVAL_SEEDS for a in runner.ARMS]
    artifact["status"] = "COMPLETE"
    return artifact


def test_validator_rejects_partial_duplicate_missing_cqa_nonfinite_and_digest(tmp_path):
    artifact = _complete_artifact()
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact))
    analyser.validate_artifact(path)

    cases = []
    partial = copy.deepcopy(artifact); partial["rows"] = partial["rows"][:-1]; cases.append(partial)
    duplicate = copy.deepcopy(artifact); duplicate["rows"][-1] = copy.deepcopy(duplicate["rows"][0]); cases.append(duplicate)
    missing = copy.deepcopy(artifact); del missing["rows"][0]["joint_volume"]; cases.append(missing)
    nonfinite = copy.deepcopy(artifact); nonfinite["rows"][0]["point_regret"] = float("nan"); cases.append(nonfinite)
    digest = copy.deepcopy(artifact); digest["spec_sha256"] = "wrong"; cases.append(digest)
    for index, case in enumerate(cases):
        bad = tmp_path / f"bad-{index}.json"; bad.write_text(json.dumps(case, allow_nan=True))
        with pytest.raises(ValueError): analyser.validate_artifact(bad)


def test_validator_rejects_training_evaluation_overlap(tmp_path):
    artifact = _complete_artifact()
    artifact["evaluation_seed_start"] = 0
    path = tmp_path / "overlap.json"; path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError): analyser.validate_artifact(path)


def test_full_evaluation_is_not_launchable(tmp_path):
    with pytest.raises(RuntimeError, match="disabled"):
        runner.run(out=tmp_path / "x.json", dry_run=False)


def test_training_template_is_explicitly_not_evaluation_evidence():
    path = ROOT / "results" / "ec-training-calibration-template.json"
    report = analyser.validate_training_report(path)
    assert report["evaluation_status"] == "NOT_RUN"
    assert report["claims"] == []


def test_training_report_rejects_evaluation_seeds(tmp_path):
    report = json.loads((ROOT / "results" / "ec-training-calibration-template.json").read_text())
    report["evaluation_seeds"] = [64]
    path = tmp_path / "training.json"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="evaluation seeds"):
        analyser.validate_training_report(path)
