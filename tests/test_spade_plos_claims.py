from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript/SPADE-PLOS-ONE.md"
ACTIVE = [
    MANUSCRIPT,
    ROOT / "manuscript/SPADE-PLOS-ONE-cover-letter.md",
    ROOT / "manuscript/CLAIMS-AND-SOURCES.md",
    ROOT / "README.md",
    ROOT / "docs/RESEARCH-SUMMARY.md",
    ROOT / ".planning/STATE.md",
]


def _text(path: Path) -> str:
    assert path.is_file(), f"missing active publication document: {path}"
    return path.read_text(encoding="utf-8")


def test_active_publication_documents_reject_stale_headline_values() -> None:
    for path in ACTIVE:
        text = _text(path)
        assert "0.001353" not in text, path
        assert not re.search(r"(?<![0-9])0\.0016(?![0-9])", text), path


def test_manuscript_states_bounded_operating_region_superiority() -> None:
    text = _text(MANUSCRIPT)
    assert "better for the tested operating-region decision" in text
    assert "greater certified volume" in text
    assert "no detectable regret difference" in text
    assert "DoE found the better point recipe" in text


def test_manuscript_pins_corrected_primary_values_and_denominators() -> None:
    text = _text(MANUSCRIPT)
    for token in (
        "-0.0005", "0.000855", "0.1026",
        "66/160", "66/66", "122/160", "85/122", "134/160", "77/134",
    ):
        assert token in text


def test_manuscript_retains_required_limits() -> None:
    text = _text(MANUSCRIPT)
    for token in (
        "NO_SELECTION", "lockbox", "relative noise 0.68",
        "prospective wet-lab", "not equivalence",
    ):
        assert token in text


def test_manuscript_does_not_make_unqualified_superiority_claims() -> None:
    text = _text(MANUSCRIPT)
    forbidden = (
        r"\bSPADE is (?:universally )?(?:best|better overall)\b",
        r"\bSPADE (?:matches|is equivalent to) qLogNEI\b",
        r"\bSPADE beats DoE\b(?![^.\n]*operating region)",
    )
    for pattern in forbidden:
        assert not re.search(pattern, text, flags=re.IGNORECASE)
