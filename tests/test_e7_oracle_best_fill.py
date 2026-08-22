"""E7 · `oracle_best` for the arms no committed file carries -- **SPADE above all**.

SPADE was absent from E7 for one reason: `step0-oracle-best.json` carries only
`versionb_plate1_ceiling` at **40 wells**, and a 40-well ceiling is not comparable to the
48-well arms. It is the object under test and it was missing from the headline table.

WHAT THIS PINS
--------------
1. **The construction is GATED against committed `oracle_best`.** Any arm the committed
   files already carry must come back at **|Δ| = 0**. A new column produced by a
   construction that cannot reproduce the old one is not a comparison (D12).
2. **48 wells, not 40.** The whole reason the arm was excluded.
3. **The committed file is never overwritten.**
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


@pytest.fixture(scope="module")
def fill():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "fill", ROOT / "scripts" / "run_e7_oracle_best_fill.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["fill"] = m
    spec.loader.exec_module(m)
    return m


def test_spade_is_in_the_fill_set(fill):
    """The point of the file."""
    assert "versionb" in fill.FILL_ARMS
    assert "versionb" not in fill.GATE_ARMS, "SPADE has no committed column to gate against"


def test_gate_arms_have_a_committed_oracle_best(fill):
    """Every gate arm must actually exist in a committed file, or the gate is theatre."""
    s0 = {r["arm"] for r in json.loads((R / "step0-oracle-best.json").read_text())["rows"]}
    for arm in fill.GATE_ARMS:
        assert arm in s0, f"{arm} is claimed as a gate arm but step0 does not carry it"


def test_the_committed_step0_file_is_never_written(fill):
    src = (ROOT / "scripts" / "run_e7_oracle_best_fill.py").read_text()
    assert "step0-oracle-best.json" in src, "it must READ the gate source"
    assert ".write_text" not in src.split("OUT =")[0]
    assert fill.OUT.name == "e7-oracle-best-fill.json"
    assert fill.OUT.name != "step0-oracle-best.json"


def test_the_40_well_ceiling_row_is_not_reused_as_versionb(fill):
    """The exclusion this file exists to remove. 40 != 48."""
    rows = json.loads((R / "step0-oracle-best.json").read_text())["rows"]
    ceil = [r for r in rows if r["arm"] == "versionb_plate1_ceiling"]
    assert ceil and {r["n_wells"] for r in ceil} == {40}
    assert "versionb_plate1_ceiling" not in fill.FILL_ARMS
    assert fill.BUDGET == 48


def test_oracle_best_is_truth_at_visited_wells(fill):
    assert fill.oracle_best_from(1.0, [0.2, 0.9, 0.5]) == pytest.approx(0.1)


def test_gitignore_negation(fill):
    assert "!results/e7-oracle-best-fill.json" in (ROOT / ".gitignore").read_text()
