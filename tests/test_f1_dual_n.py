"""Amendment F1 — every contrast at BOTH units, n = 50 and n = 25.

`docs/K6-TECHNICAL-REPORT.md` §3.8 fixes the unit of analysis as the `(instance, seed)`
pair, n = 50. `docs/RESEARCH-SUMMARY.md` fixes it as the instance, seeds averaged first,
n = 25. Two seeds on one landscape share the landscape, so n = 50 counts a shared unit
twice: it narrows every bootstrap interval and lowers every Wilcoxon p. The registration
(AMENDMENT F1, commit 07e98df) requires both, and requires the n = 25 verdict to govern.

The tests that matter here are the two tie-backs. A second implementation of the same
statistics is only worth reading if it reproduces the committed one where the two agree by
construction — at n = 50 — so `results/k6-analysis.json` and `results/fix1-analysis.json`
are the fixtures. Everything that then differs at n = 25 differs because of the unit and
not because two scripts disagree.

Committed blobs are read through `git show HEAD:<path>`. Six other agents are writing into
`results/` concurrently.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analyse_f1_dual_n import (  # noqa: E402
    INSTANCE,
    INSTANCE_SEED,
    committed,
    containment,
    dual_contrast,
    holm,
    paired,
)

TOL = 1e-12


@pytest.fixture(scope="module")
def k6_rows():
    main = committed("results/k6-designspace.json")
    spread = committed("results/k6-designspace-spread.json")
    return main["rows"] + spread["rows"]


@pytest.fixture(scope="module")
def fix1():
    return committed("results/fix1-terminal-rule.json")


def test_seed_averaging_halves_the_unit_count_and_is_an_arithmetic_mean(k6_rows):
    cell = {"gamma": 0.50, "tau_frac": 0.60}
    a50, b50, _ = paired(k6_rows, "lhs", "doe", "auc_pred", INSTANCE_SEED, **cell)
    a25, b25, _ = paired(k6_rows, "lhs", "doe", "auc_pred", INSTANCE, **cell)
    assert (len(a50), len(a25)) == (50, 25)

    raw = {(r["instance"], r["seed"]): r["auc_pred"] for r in k6_rows
           if r["arm"] == "lhs" and r["gamma"] == 0.50 and r["tau_frac"] == 0.60}
    instances = sorted({i for i, _ in raw})
    expected = np.array([np.mean([raw[(i, s)] for _i, s in raw if _i == i])
                         for i in instances])
    assert np.allclose(np.sort(a25), np.sort(expected), atol=0, rtol=0)


def test_n50_reproduces_the_committed_k6_analysis(k6_rows):
    """`doe - qlogei` on AUC(predictive), all 24 cells, against `analyse_k6.py`'s output."""
    ref = committed("results/k6-analysis.json")["spread_vs_clustered"]
    assert len(ref) == 24
    for cell in ref:
        got = dual_contrast(k6_rows, "doe", "qlogei", "auc_pred",
                            gamma=cell["gamma"], tau_frac=cell["tau_frac"])["n50"]
        for key in ("n", "mean", "lo", "hi", "wilcoxon_p"):
            assert got[key] == pytest.approx(cell[key], abs=TOL, rel=0), (
                f"cell gamma={cell['gamma']} tau_frac={cell['tau_frac']} key={key}")


def test_n50_reproduces_the_committed_fix1_analysis(fix1):
    """Rule P minus rule A, all 10 arms, against `analyse_fix1.py`'s output."""
    ref = committed("results/fix1-analysis.json")["per_arm"]
    rows = fix1["rows"]
    for entry in ref:
        got = dual_contrast(rows, entry["arm"], entry["arm"], "regret_p",
                            key_b="regret_a")["n50"]
        for key in ("n", "mean", "lo", "hi", "wilcoxon_p"):
            assert got[key] == pytest.approx(entry["delta_p_minus_a"][key],
                                             abs=TOL, rel=0), f"{entry['arm']} {key}"


def test_the_conservative_unit_never_narrows_the_interval(k6_rows):
    """Averaging seeds first cannot buy precision; it can only give some back.

    Var(mean of 25 instance means) / Var(naive mean of 50) = 2(s_b^2 + s_w^2/2)/(s_b^2 +
    s_w^2), which lies in [1, 2]. So the n = 25 half-width is between 1x and sqrt(2)x the
    n = 50 half-width -- never below it. This is the mechanism F1 is about, asserted as a
    property rather than as a number.
    """
    ratios = []
    for gamma in (0.50, 0.90, 0.95, 0.99):
        for tf in (0.60, 0.75, 0.85, 0.95):
            d = dual_contrast(k6_rows, "lhs", "doe", "auc_pred", gamma=gamma, tau_frac=tf)
            hw = {u: (d[u]["hi"] - d[u]["lo"]) / 2 for u in ("n50", "n25")}
            ratios.append(hw["n25"] / hw["n50"])
    ratios = np.array(ratios)
    assert (ratios >= 0.98).all(), f"n=25 narrowed an interval: min ratio {ratios.min():.4f}"
    assert (ratios <= 1.50).all(), f"ratio above sqrt(2)+slack: max {ratios.max():.4f}"
    assert float(np.median(ratios)) > 1.05


def test_holm_matches_the_committed_fix1_adjustment(fix1):
    ref = committed("results/fix1-analysis.json")["per_arm"]
    raw = [e["delta_p_minus_a"]["wilcoxon_p"] for e in ref]
    expected = [e["delta_p_minus_a"]["p_holm"] for e in ref]
    assert holm(raw) == pytest.approx(expected, abs=TOL, rel=0)


def test_every_contrast_carries_both_units_and_the_registered_verdict(k6_rows):
    d = dual_contrast(k6_rows, "lhs", "doe", "auc_pred", gamma=0.50, tau_frac=0.60)
    assert d["n50"]["n"] == 50 and d["n25"]["n"] == 25
    # The registered decision rule: n = 25 governs, n = 50 is labelled and never alone.
    assert d["reported_unit"] == INSTANCE
    assert d["n50_label"] == "anti-conservative unit"
    assert set(d) >= {"n50", "n25", "status_n50", "status_n25", "status_changed",
                      "bootstrap_wilcoxon_disagree_n50", "bootstrap_wilcoxon_disagree_n25"}
    assert d["status_changed"] == (d["status_n50"] != d["status_n25"])


def test_containment_at_n25_averages_the_seeds_of_an_instance():
    """A boolean per campaign becomes {0, 0.5, 1} per instance. Empty sets stay dropped."""
    rows = [
        {"instance": "a", "seed": 0, "hit": True},   # instance a -> 0.5
        {"instance": "a", "seed": 1, "hit": False},
        {"instance": "b", "seed": 0, "hit": True},   # instance b -> 1.0, one seed empty
        {"instance": "b", "seed": 1, "hit": None},
        {"instance": "c", "seed": 0, "hit": None},   # instance c -> not scorable at all
        {"instance": "c", "seed": 1, "hit": None},
    ]
    assert containment(rows, "hit", INSTANCE_SEED) == {"value": pytest.approx(2 / 3), "n": 3}
    assert containment(rows, "hit", INSTANCE) == {"value": pytest.approx(0.75), "n": 2}
    assert containment([r for r in rows if r["instance"] == "c"], "hit", INSTANCE) == {
        "value": None, "n": 0}
