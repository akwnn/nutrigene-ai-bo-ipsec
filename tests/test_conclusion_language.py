from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "docs" / "SPADE-PAPER-ARGUMENT.md"
CONCLUSIONS = ROOT / "docs" / "SPADE-CONCLUSIONS-2026-08-29.md"


def _text(path: Path) -> str:
    return path.read_text().lower()


def test_paper_does_not_claim_equivalence_or_unique_trustworthiness():
    paper = _text(PAPER)
    forbidden = (
        r"ties bo",
        r"ties spade",
        r"spade matches bo's recipe quality",
        r"optimisation quality equal to bayesian optimisation",
        r"only method that returns an operating region you can trust",
    )
    for pattern in forbidden:
        assert not re.search(pattern, paper), pattern
    assert "no detectable regret difference" in paper


def test_historical_dc_is_not_presented_as_confirmatory_evidence():
    paper = _text(PAPER)
    conclusions = _text(CONCLUSIONS)
    for text in (paper, conclusions):
        assert "variance-corrected replication" in text
        assert "historical" in text
        assert "not confirmatory" in text


def test_conclusion_table_uses_no_detectable_difference_not_match():
    conclusions = _text(CONCLUSIONS)
    assert "spade at 5 rounds matches qlognei" not in conclusions
    assert "no detectable regret difference" in conclusions


def test_conclusion_verifier_is_root_relative(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_conclusions.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "60/60 current checks pass" in completed.stdout
