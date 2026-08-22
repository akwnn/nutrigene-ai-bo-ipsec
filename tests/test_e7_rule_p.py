"""E7 · the rule-P identification gap, as a COMMITTED artefact rather than a session join.

Registered in ``docs/OPEN-QUESTIONS.md`` (Erratum 32 block, commit 04eeebf) **before this
runner existed**.

WHAT THIS PINS
--------------
1. **Zero new campaigns.** Every column is a join of files already committed. A runner that
   regenerated anything here would be measuring something else.
2. **The joins are exact, and are CHECKED rather than assumed.** ``step0`` and ``fix1``
   share ``rule_a`` to floating-point equality; ``q57`` and ``versionc-gate-s010`` share all
   50 keys. If either drifts, the join is meaningless and must fail loudly.
3. **``bo_*`` is ``qlogei`` and ``nei_*`` is ``qlognei``.** Erratum 32 exists because I did
   not know that. The mapping is asserted here so it cannot be forgotten again.
4. **``plate1_only`` never ranks** (Erratum 29) -- it IS ``lhs``.
5. **Arm-set scope is LABELLED on every spread figure** (Erratum 32): 0.0395 over five arms
   and 0.0420 with ``qlogei`` are both right, for different sets.
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
def e7():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "e7", ROOT / "scripts" / "run_e7_rule_p.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["e7"] = mod
    spec.loader.exec_module(mod)
    return mod


# ======================================================================================
# 1. NO NEW CAMPAIGNS
# ======================================================================================
def test_the_runner_regenerates_nothing(e7):
    """The whole justification for this file is that it costs no wells."""
    src = (ROOT / "scripts" / "run_e7_rule_p.py").read_text()
    for banned in ("regenerate(", "BiphasicOracle", "TorchEvaluator", "build_gp",
                   "static_design", "evaluate("):
        assert banned not in src, (
            f"{banned!r} means this runner builds or evaluates a campaign; E7 is a join")


# ======================================================================================
# 2. THE JOINS, CHECKED
# ======================================================================================
def test_step0_and_fix1_describe_the_same_campaigns(e7):
    """5.55e-16 was measured in-session; pin it so a drift cannot pass silently."""
    s0 = {(r["instance"], r["seed"], r["arm"]): r
          for r in json.loads((R / "step0-oracle-best.json").read_text())["rows"]}
    f1 = {(r["instance"], r["seed"], r["arm"]): r
          for r in json.loads((R / "fix1-terminal-rule.json").read_text())["rows"]}
    keys = set(s0) & set(f1)
    assert len(keys) == 300, f"expected 300 shared keys, got {len(keys)}"
    worst = max(abs(s0[k]["rule_a"] - f1[k]["regret_a"]) for k in keys)
    assert worst < 1e-12, (
        f"step0.rule_a and fix1.regret_a differ by {worst:.3e}; they are supposed to be "
        f"the same campaigns and the join is not valid if they are not")


def test_q57_and_versionc_gate_share_every_key_at_sigma_010(e7):
    q = {(r["instance"], r["seed"]) for r in
         json.loads((R / "q57-search-vs-id.json").read_text())["rows"]
         if r["dim"] == 6 and r["sigma"] == 0.1}
    v = {(r["instance"], r["seed"]) for r in
         json.loads((R / "versionc-gate-s010.json").read_text())["rows"]}
    assert len(q) == 50 and len(v) == 50
    assert q == v, "the sigma=0.10 join is only valid across identical key sets"


def test_identification_gap_is_rule_minus_oracle_best(e7):
    """step0 stores the rule-A gap; the definition must match or the two sigmas differ."""
    rows = json.loads((R / "step0-oracle-best.json").read_text())["rows"]
    worst = max(abs(r["identification_gap"] - (r["rule_a"] - r["oracle_best"]))
                for r in rows)
    assert worst == 0.0
    assert e7.gap(0.5, 0.2) == pytest.approx(0.3)


# ======================================================================================
# 3. THE ARM-NAME MAPPING THAT ERRATUM 32 EXISTS BECAUSE I DID NOT KNOW
# ======================================================================================
def test_q57_arm_prefixes_map_to_real_arm_names(e7):
    assert e7.Q57_ARM == {"doe": "doe", "bo": "qlogei", "nei": "qlognei"}


def test_q57_reproduces_the_two_reinstated_figures(e7):
    """+0.0797 (qlogei, s=0.25) and +0.0348 (doe, s=0.10). Erratum 32."""
    g = e7.q57_rule_a_gaps()
    assert g[(6, 0.25)]["qlogei"] == pytest.approx(0.0797, abs=5e-5)
    assert g[(6, 0.10)]["doe"] == pytest.approx(0.0348, abs=5e-5)
    assert g[(6, 0.25)]["doe"] == pytest.approx(0.0361, abs=5e-5)


# ======================================================================================
# 4. RANKING HYGIENE
# ======================================================================================
def test_plate1_only_is_never_ranked(e7):
    assert "plate1_only" in e7.NEVER_RANK_SEPARATELY
    assert "plate1_only" not in e7.rankable(["doe", "lhs", "plate1_only", "sobol"])


def test_spread_figures_carry_their_arm_set(e7):
    """Erratum 32: 0.0395 and 0.0420 are both right, for different arm sets."""
    out = e7.spread({"a": 0.10, "b": 0.20, "c": 0.35})
    assert out["spread"] == pytest.approx(0.25)
    assert out["arms"] == ["a", "b", "c"], "the arm set must travel with the number"
    assert out["n_arms"] == 3


def test_output_path_is_registered_and_negated(e7):
    assert e7.OUT.name == "e7-search-vs-id-rule-p.json"
    assert "!results/e7-search-vs-id-rule-p.json" in (ROOT / ".gitignore").read_text()
