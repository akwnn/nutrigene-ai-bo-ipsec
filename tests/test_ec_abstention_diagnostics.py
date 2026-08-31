from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, "scripts")
import diagnose_ec_abstentions as diagnostics  # noqa: E402


def _result(volumes=(0.0, 0.2, 0.3)):
    return SimpleNamespace(
        status="ABSTAIN_EMPTY_JOINT",
        endpoint_results=tuple(SimpleNamespace(name=n, volume=v)
                                for n, v in zip(("identity", "viability", "yield"), volumes)),
    )


def test_training_seed_contract_is_disjoint_and_exact():
    assert diagnostics.TRAIN_SEEDS == tuple(range(64))
    with pytest.raises(ValueError, match="training seeds"):
        diagnostics.diagnose_one("ec_broad", 64)


def test_classification_reports_deterministic_limiting_cqa():
    assert diagnostics.classify_abstention(_result(), campaign_joint_hits=1) == (
        "model_uncertainty", "identity")
    assert diagnostics.classify_abstention(_result((.2, .1, .3)), campaign_joint_hits=1) == (
        "joint_cqa_bottleneck", "viability")
    assert diagnostics.classify_abstention(_result((.2, .1, .3)), campaign_joint_hits=0) == (
        "acquisition_coverage", "viability")


def test_non_abstention_is_not_classified():
    result = _result()
    result.status = "QUALIFIED"
    with pytest.raises(ValueError, match="abstaining"):
        diagnostics.classify_abstention(result)


def test_atomic_training_dry_run_is_seed_only_and_resumable(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostics, "diagnose_one", lambda family, seed, arm, test_only:
                        {"family": family, "seed": seed, "arm": arm,
                         "classification": "model_uncertainty", "limiting_cqa": "identity",
                         "execution_mode": "TRAINING_ONLY"})
    out = tmp_path / "diagnostics.json"
    report = diagnostics.run(out=out, family="ec_broad", dry_run=True)
    assert report["status"] == "COMPLETE"
    assert report["training_seeds"] == [0]
    assert report["evaluation_seeds"] == []
    assert out.read_text()
