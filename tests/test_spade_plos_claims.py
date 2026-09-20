from __future__ import annotations

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

STALE_REGRET = re.compile(r"(?<![0-9])0\.0016(?![0-9])")
CLAIM_WINDOW = 420

C1_SIGNED_INTERVAL = re.compile(
    r"\[\s*-0\.0221\s*,\s*\+?0\.0207\s*\]",
    flags=re.IGNORECASE,
)
C1_P_VALUE = re.compile(r"\bp\s*=\s*0\.96\b", flags=re.IGNORECASE)

C3_SIGNED_INTERVAL = re.compile(
    r"\[\s*\+0\.000691\s*,\s*\+0\.001028\s*\]"
    r"|\[\s*0\.000691\s*,\s*0\.001028\s*\]",
    flags=re.IGNORECASE,
)
C3_P_VALUE = re.compile(r"\bp\s*<\s*0\.0001\b", flags=re.IGNORECASE)

ADVERSE_DOE_SIGNED_INTERVAL = re.compile(
    r"\[\s*\+0\.0486\s*,\s*\+0\.1578\s*\]"
    r"|\[\s*0\.0486\s*,\s*0\.1578\s*\]",
    flags=re.IGNORECASE,
)
ADVERSE_DOE_P_VALUE = re.compile(r"\bp\s*=\s*0\.0003\b", flags=re.IGNORECASE)

BOUNDED_SUPERIORITY_CONTEXT = (
    r"operating[- ]region|regional deliverable|certified volume|"
    r"truth containment|conservative[- ]set volume|operating-region decision"
)


def _text(path: Path) -> str:
    assert path.is_file(), f"missing active publication document: {path}"
    return path.read_text(encoding="utf-8")


def _assert_regex(text: str, pattern: str, label: str) -> None:
    assert re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL), label


def _coherent_claim_near_anchor(
    text: str,
    anchor: str,
    interval: re.Pattern[str],
    p_value: re.Pattern[str],
    label: str,
) -> None:
    for match in re.finditer(re.escape(anchor), text):
        chunk = text[match.start() : match.start() + CLAIM_WINDOW]
        if interval.search(chunk) and p_value.search(chunk):
            return
    raise AssertionError(label)


def assert_coherent_c1_regret_claim(text: str) -> None:
    _coherent_claim_near_anchor(
        text,
        "-0.0005",
        C1_SIGNED_INTERVAL,
        C1_P_VALUE,
        "missing coherent C1 claim: -0.0005 with signed CI [-0.0221,+0.0207] and p=0.96",
    )


def assert_coherent_c3_volume_claim(text: str) -> None:
    for anchor in ("+0.000855", "0.000855"):
        for match in re.finditer(re.escape(anchor), text):
            chunk = text[match.start() : match.start() + CLAIM_WINDOW]
            if C3_SIGNED_INTERVAL.search(chunk) and C3_P_VALUE.search(chunk):
                return
    raise AssertionError(
        "missing coherent C3 claim: +0.000855 with signed CI [+0.000691,+0.001028] and p<0.0001",
    )


def assert_coherent_adverse_doe_claim(text: str) -> None:
    _coherent_claim_near_anchor(
        text,
        "0.1026",
        ADVERSE_DOE_SIGNED_INTERVAL,
        ADVERSE_DOE_P_VALUE,
        "missing coherent adverse DoE claim: 0.1026 with signed CI [+0.0486,+0.1578] and p=0.0003",
    )


def assert_manuscript_pins_c1_regret(text: str) -> None:
    assert_coherent_c1_regret_claim(text)
    _assert_regex(text, r"\bn\s*=\s*160\b", "missing C1 n")
    _assert_regex(
        text,
        r"no detectable (?:regret )?difference",
        "missing C1 no-detectable-difference wording",
    )
    _assert_regex(
        text,
        r"SPADE.{0,80}(?:five|5).{0,40}round",
        "missing SPADE five-round schedule for C1",
    )
    _assert_regex(
        text,
        r"qLogNEI.{0,80}(?:ten|10).{0,40}round",
        "missing qLogNEI ten-round schedule for C1",
    )


def assert_manuscript_pins_c3_certified_volume(text: str) -> None:
    assert_coherent_c3_volume_claim(text)
    _assert_regex(text, r"\bn\s*=\s*320\b", "missing C3 n")
    _assert_regex(
        text,
        r"dependent.{0,80}(?:cell|family[- ]seed[- ]prevalence)",
        "missing C3 dependent-cell qualification",
    )
    _assert_regex(
        text,
        r"leave-one-family-out|\bLOFO\b",
        "missing C3 LOFO calibration reference",
    )
    _assert_regex(
        text,
        r"(?:five|5).{0,40}matched.{0,40}round|matched.{0,40}(?:five|5).{0,40}round",
        "missing matched five-round C3 setting",
    )


def assert_manuscript_pins_c2_containment_and_adverse_doe(text: str) -> None:
    for token in ("66/160", "66/66", "122/160", "85/122", "134/160", "77/134"):
        assert token in text, f"missing C2 containment token: {token}"
    assert_coherent_adverse_doe_claim(text)
    _assert_regex(
        text,
        r"(?:DoE|design of experiments).{0,120}(?:three|3).{0,40}round",
        "missing DoE three-round schedule",
    )
    _assert_regex(
        text,
        r"SPADE.{0,120}(?:five|5).{0,40}round",
        "missing SPADE five-round schedule for DoE contrast",
    )


def assert_manuscript_states_bounded_operating_region_superiority(text: str) -> None:
    _assert_regex(text, r"operating[- ]region", "missing operating-region scope")
    _assert_regex(
        text,
        r"(?:greater|larger).{0,60}certified volume",
        "missing certified-volume superiority wording",
    )
    _assert_regex(
        text,
        r"no detectable (?:regret )?difference",
        "missing no-detectable-regret-difference wording",
    )
    _assert_regex(
        text,
        r"(?:DoE|design of experiments).{0,160}(?:better|found).{0,60}(?:point|recipe)",
        "missing adverse DoE point-recipe result",
    )
    assert (
        "better for the tested operating-region decision" in text
        or re.search(r"better.{0,40}operating[- ]region", text, flags=re.IGNORECASE)
        or re.search(
            r"operating[- ]region.{0,40}(?:decision|deliverable)",
            text,
            flags=re.IGNORECASE,
        )
    ), "missing bounded operating-region superiority thesis"


def assert_manuscript_retains_required_limits(text: str) -> None:
    assert "NO_SELECTION" in text
    _assert_regex(text, r"relative noise 0\.68", "missing real-noise ceiling")
    _assert_regex(
        text,
        r"prospective wet[- ]lab",
        "missing prospective wet-lab limitation",
    )
    _assert_regex(
        text,
        r"not equivalence|not establish equivalence|does not establish equivalence",
        "missing explicit not-equivalence limit",
    )
    _assert_regex(
        text,
        r"lockbox.{0,120}(?:unopened|not opened|remained unopened|FROZEN_UNOPENED|no lockbox evidence was opened)"
        r"|(?:unopened|FROZEN_UNOPENED|not opened).{0,120}lockbox",
        "missing unopened/frozen lockbox statement",
    )
    _assert_regex(
        text,
        r"flat[- ]cell bootstrap.{0,200}(?:conditional|descriptive|too narrow|dependent|dependence|not independent|not campaigns)"
        r"|(?:conditional|descriptive).{0,120}flat[- ]cell bootstrap"
        r"|flat[- ]cell bootstrap.{0,120}intervals?.{0,80}(?:too narrow|conditional|descriptive)",
        "missing flat-cell bootstrap dependence/limitation language",
    )
    _assert_regex(
        text,
        r"(?:dependent|nonexchangeable|not exchangeable).{0,120}(?:cell|campaign|sample|inference|correlation|interval)"
        r"|(?:cell|campaign|sample).{0,120}(?:dependent|nonexchangeable|not exchangeable)"
        r"|not.{0,40}independent campaigns",
        "missing dependence limitation language",
    )
    _assert_regex(
        text,
        r"within[- ]sample.{0,160}(?:not held[- ]out|not transportable|DC cells themselves|without held[- ]out|within the DC)"
        r"|(?:inflation|calibration).{0,160}(?:without the held[- ]out family|not held[- ]out|within the DC|within-?sample)"
        r"|(?:not held[- ]out|without the held[- ]out family).{0,120}(?:calibration|inflation|transport)",
        "missing DC within-sample / non-transportable calibration limitation",
    )


def assert_manuscript_forbids_unqualified_superiority(text: str) -> None:
    bounded = rf"(?![^\n]{{0,220}}(?:{BOUNDED_SUPERIORITY_CONTEXT}))"
    forbidden = (
        r"\bSPADE is (?:universally )?(?:best|better overall)\b",
        rf"\bSPADE is (?:better|best)\b{bounded}",
        rf"\bSPADE is superior\b{bounded}",
        rf"\bSPADE outperforms (?:all|every)(?:\s+\w+){{0,4}}\s+methods?\b{bounded}",
        rf"\bSPADE dominates\b{bounded}",
        r"\bSPADE (?:matches|matched|is equivalent to|equivalent to) qLogNEI\b",
        r"(?<!\bnot )\b(?:SESOI )?parity\b",
        r"\b(?:recipe|point[- ]recipe|point optimization|manufacturing|regulatory|prospective wet[- ]lab).{0,40}superior(?:ity)?\b",
        r"\bSPADE beats DoE\b(?![^.\n]*operating region)",
        r"\buniversal(?:ly)? superior(?:ity)?\b",
    )
    for pattern in forbidden:
        assert not re.search(pattern, text, flags=re.IGNORECASE), pattern


def test_active_publication_documents_exist() -> None:
    for path in ACTIVE:
        assert path.is_file(), f"missing active publication document: {path}"


def test_active_publication_documents_reject_stale_headline_values() -> None:
    for path in ACTIVE:
        text = _text(path)
        assert "0.001353" not in text, path
        assert not STALE_REGRET.search(text), path


def test_manuscript_states_bounded_operating_region_superiority() -> None:
    assert_manuscript_states_bounded_operating_region_superiority(_text(MANUSCRIPT))


def test_manuscript_pins_c1_regret_claim() -> None:
    assert_manuscript_pins_c1_regret(_text(MANUSCRIPT))


def test_manuscript_pins_c3_certified_volume_claim() -> None:
    assert_manuscript_pins_c3_certified_volume(_text(MANUSCRIPT))


def test_manuscript_pins_c2_containment_and_adverse_doe() -> None:
    assert_manuscript_pins_c2_containment_and_adverse_doe(_text(MANUSCRIPT))


def test_manuscript_retains_required_limits() -> None:
    assert_manuscript_retains_required_limits(_text(MANUSCRIPT))


def test_manuscript_does_not_make_unqualified_superiority_claims() -> None:
    assert_manuscript_forbids_unqualified_superiority(_text(MANUSCRIPT))
