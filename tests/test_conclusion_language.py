"""Guard publication wording against claims stronger than the registered evidence."""
from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
PAPER = (ROOT / "docs" / "SPADE-PAPER-ARGUMENT.md").read_text().lower()
CONCLUSIONS = (ROOT / "docs" / "SPADE-CONCLUSIONS-2026-08-29.md").read_text().lower()


def test_regret_is_not_framed_as_equivalence_or_tie():
    assert "ties bo" not in PAPER
    assert "matches bo" not in PAPER
    assert "no detectable difference" in PAPER


def test_no_uniqueness_claim_for_trustworthy_region():
    assert "only method that returns an operating region you can trust" not in PAPER
    assert "only arm with containment 1.0000" not in PAPER


def test_doe_values_are_explicitly_historical_and_replication_pending():
    assert "historical" in PAPER
    assert "variance-corrected replication" in PAPER
    assert "historical" in CONCLUSIONS
    assert "variance-corrected replication" in CONCLUSIONS
    assert re.search(r"doe.{0,100}non-confirmatory", CONCLUSIONS, re.DOTALL)


def test_tt_is_mixed_activation_and_not_adopted():
    assert "not adopted" in CONCLUSIONS
    assert "206 of 640" in CONCLUSIONS
    assert "mixed-activation" in CONCLUSIONS
