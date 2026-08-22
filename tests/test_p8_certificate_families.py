"""P8 · SPADE's certificate off hill. The contract, checked without running a campaign.

Registered in `docs/OPEN-QUESTIONS.md` at commit b281d4b, **before this runner existed**.

WHAT THIS PINS
--------------
1. **The gap P8 exists to close is real.** `p6-families` carries no certificate column. If
   that ever stops being true, P8's justification changes and this test says so.
2. **P2 IS NOT EDITED.** `p2-versionb-gamma.json` is committed against P2's current
   behaviour; P8 imports `score_campaign` read-only (D15).
3. **N_DRAWS = 4,096, never 512.** F3 registered 512 as insufficient at γ ≥ 0.95. A
   certificate run at 512 would reproduce the artefact it exists to avoid.
4. **hill is IN the family list.** Comparing families at 4,096 to committed hill at 512
   confounds family with draw count.
5. **The certificate columns are not gated against P2** — they are supposed to differ.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def p8():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "p8", ROOT / "scripts" / "run_p8_certificate_families.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["p8"] = m
    spec.loader.exec_module(m)
    return m


def test_the_gap_p8_exists_to_close_is_real():
    """`p6-families` must carry NO certificate column. This is P8's whole justification."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from load_p6_families import load
    row = load()["rows"][0]
    cert = [k for k in row if k.startswith(("ce_", "alpha_star", "vorobev"))]
    assert cert == [], (
        f"p6-families now carries certificate columns {cert}; P8's justification has "
        f"changed and the registration must be revisited")


def test_draws_are_4096_never_512(p8):
    """F3: 512 cannot estimate containment at gamma >= 0.95 (§29)."""
    assert p8.N_DRAWS == 4096
    assert p8.N_DRAWS != 512, "512 reproduces the artefact this run exists to avoid"


def test_hill_is_in_the_family_list(p8):
    """Otherwise families at 4096 are compared to committed hill at 512."""
    assert "hill" in p8.FAMILIES
    assert set(p8.FAMILIES) == {"hill", "hartmann6", "levy", "rosenbrock", "ackley"}


def test_p2_is_imported_read_only_and_not_edited(p8):
    """D15: p2-versionb-gamma.json is committed against P2's current behaviour."""
    src = (ROOT / "scripts" / "run_p8_certificate_families.py").read_text()
    for banned in ("p2.N_DRAWS =", "p2.GAMMAS =", "p2.ARMS =", "run_p2_versionb_gamma.py\").write"):
        assert banned not in src, f"{banned!r} mutates P2"
    assert p8.OUT.name != "p2-versionb-gamma.json"
    assert "p2-versionb-gamma.json" not in str(p8.OUT)


def test_the_cell_matches_p2_exactly(p8):
    """hill at d=6 sigma=0.25 is only a check if it is the same cell P2 measured."""
    assert (p8.DIM, p8.SIGMA) == (6, 0.25)
    assert p8.N_SEEDS == 50


def test_arms_are_the_spade_family(p8):
    assert "versionb" in p8.ARMS
    assert set(p8.ARMS) == {"versionb", "versionb_random", "versionb_predictive",
                            "plate1_only"}


def test_the_gate_is_campaign_level_only(p8):
    """Certificate columns MUST NOT be gated against P2's 512-draw columns."""
    assert set(p8.GATE_COLUMNS) == {"regret", "n_wells"}
    for c in p8.GATE_COLUMNS:
        assert not c.startswith(("ce_", "alpha_", "vorobev")), (
            f"{c} is a certificate column; gating it against P2's 512-draw value would "
            f"report the draw-count correction as a defect")


def test_exact_binomial_tail_never_a_normal_approximation(p8):
    """Erratum 21."""
    from scipy.stats import binom
    assert p8.exact_tail(42, 50, 0.95) == pytest.approx(binom.cdf(42, 50, 0.95), rel=1e-12)


def test_output_path_registered_and_negated(p8):
    assert p8.OUT.name == "p8-certificate-families.json"
    assert "!results/p8-certificate-families.json" in (ROOT / ".gitignore").read_text()
