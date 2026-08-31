from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from boec.spade_study import REGISTERED_SCORING_SETTINGS


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = (
    ROOT
    / "results/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail"
    / "spade-development-hill-000-015.jsonl.gz.resume.json"
)


@pytest.mark.skipif(not ARCHIVE.is_file(), reason="archived meanmarg gate shard missing")
def test_replay_smoke_rescores_archived_row_with_bootstrap_bags():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/replay_certificate_scoring.py"),
            str(ARCHIVE),
            "--smoke",
            "--max-rows",
            "1",
            "--bootstrap-bags",
            "3",
            "--alpha",
            "0.95",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in {0, 2}, proc.stderr
    report = json.loads(proc.stdout)
    assert report["row_count"] == 1
    assert report["settings"]["certificate_bootstrap_bags"] == 3


def test_registered_scoring_settings_include_bootstrap_bags():
    assert REGISTERED_SCORING_SETTINGS.certificate_bootstrap_bags == 5


@pytest.mark.skipif(not ARCHIVE.is_file(), reason="archived meanmarg gate shard missing")
def test_replay_arm_filter_resolves_against_complete_campaign_group():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/replay_certificate_scoring.py"),
            str(ARCHIVE),
            "--smoke",
            "--arms",
            "spade-o32-validity_gated",
            "--max-rows",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in {0, 2}, proc.stderr
    report = json.loads(proc.stdout)
    assert report["row_count"] == 1
    assert set(report["families"]["hill"]) == {"spade-o32-validity_gated"}


def test_conformal_bag1_sensitivity_is_explicitly_test_only_and_has_candidate():
    artifact = ROOT / "results/unified-product-b5-sensitivity-bags1-conformal.json"
    assert artifact.is_file()
    report = json.loads(artifact.read_text())
    assert report["row_count"] == 150
    assert report["settings"]["certificate_bootstrap_bags"] == 1
    assert report["settings"]["conformal_lower_calibration"] is True
    assert report["survivors"] == ["spade-o32-validity_gated"]
    assert report["families"]["hill"]["spade-o32-validity_gated"]["ans"] >= 0.5
    assert report["families"]["levy"]["spade-o32-validity_gated"]["ans"] >= 0.5
