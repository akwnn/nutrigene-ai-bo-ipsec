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
    METRIC_PREFIXES,
    MODEL_INTERNAL,
    VALIDATED,
    benefit_sign,
    committed,
    containment,
    dual_contrast,
    holm,
    metric_class,
    paired,
    unpaired_icc,
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


def test_the_interval_width_tracks_the_measured_seed_correlation(k6_rows):
    """HOW anti-conservative n = 50 is — as a measured number, not an assumed sqrt(2).

    F1 states that n = 50 "narrows every bootstrap CI by roughly sqrt(2)". sqrt(2) is the
    ICC = 1 corner: two seeds on one landscape agreeing perfectly. The exact sample
    identity is

        Var_boot(n=25) / Var_boot(n=50) = (n50/n25) * s25^2 / s50^2 = 1 + ICC

    so the half-width ratio is sqrt(1 + ICC), which lies anywhere in [0, sqrt(2)] and is
    **below 1** whenever two seeds on one landscape disagree more than two landscapes do.
    The interval does not automatically widen, and this test asserts the identity rather
    than the folklore.
    """
    ratios, predicted = [], []
    for gamma in (0.50, 0.70, 0.80, 0.90, 0.95, 0.99):
        for tf in (0.60, 0.75, 0.85, 0.95):
            d = dual_contrast(k6_rows, "lhs", "doe", "auc_pred", gamma=gamma, tau_frac=tf)
            ratios.append((d["n25"]["hi"] - d["n25"]["lo"])
                          / (d["n50"]["hi"] - d["n50"]["lo"]))
            predicted.append(d["ci_inflation"])
    ratios, predicted = np.array(ratios), np.array(predicted)
    assert len(ratios) == 24
    assert np.allclose(ratios, predicted, rtol=0.05, atol=0), (
        f"bootstrap width ratio departs from sqrt(1+ICC): worst rel err "
        f"{np.max(np.abs(ratios / predicted - 1)):.4f}")
    assert (predicted <= 2 ** 0.5 + 1e-9).all(), "inflation above the ICC=1 ceiling"
    # And on the headline family it is nowhere near sqrt(2): measured median ~1.12.
    assert float(np.median(predicted)) < 1.25, (
        f"median inflation {np.median(predicted):.4f} — if this has moved to sqrt(2) the "
        "seeds have become far more alike and F1's premise needs re-measuring")


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


def test_metric_class_follows_section_1_4():
    """§1.4's table is the authority, and a contrast must know which side it is on.

    A status change on `alpha*` and one on AUC are not the same evidence. `alpha*` and
    Vorob'ev deviation are functionals of the fitted posterior and nothing else, so a
    stronger reading of one under the conservative unit is a stronger reading of a
    statistic that a confidently-wrong model also scores well on (§1.4 consequence 1).
    """
    assert metric_class("alpha_star") == MODEL_INTERNAL
    assert metric_class("alpha_star_0.6") == MODEL_INTERNAL
    assert metric_class("vorobev_dev_0.85") == MODEL_INTERNAL
    for key in ("regret", "regret_p", "regret_a", "auc_pred", "auc_latent", "auc_0.75",
                "brier_pred", "brier_0.6", "iou_pred", "ce_empirical_0.5"):
        assert metric_class(key) == VALIDATED, key


def test_an_unclassified_metric_is_a_hard_error():
    """The grid is about to triple across five families. A new column must be classified
    deliberately rather than defaulting to whichever side is convenient."""
    with pytest.raises(ValueError, match="not classified"):
        metric_class("some_new_metric_0.6")


def test_every_contrast_carries_its_metric_class(k6_rows):
    d = dual_contrast(k6_rows, "lhs", "doe", "auc_pred", gamma=0.50, tau_frac=0.60)
    assert d["metric"] == "auc_pred"
    assert d["metric_class"] == VALIDATED


def test_benefit_direction_accounts_for_lower_is_better_metrics():
    """Corroboration must compare BENEFIT, not raw sign.

    `versionb - versionb_random` is +0.0261 on `alpha*` (higher is better) and -0.0071 on
    Brier (LOWER is better). Both favour `versionb`. A naive sign comparison calls that a
    disagreement and inverts the conclusion, which is what a first cut of this audit did.
    """
    assert benefit_sign("auc_0.6", +0.01) == 1
    assert benefit_sign("alpha_star", +0.01) == 1
    assert benefit_sign("iou_pred", +0.01) == 1
    assert benefit_sign("ce_empirical_0.5", +0.01) == 1
    assert benefit_sign("brier_0.6", -0.01) == 1          # lower Brier is better
    assert benefit_sign("regret", -0.01) == 1             # lower regret is better
    assert benefit_sign("vorobev_dev_0.6", +0.01) == -1   # lower deviation is better
    assert benefit_sign("auc_0.6", 0.0) == 0


def test_every_metric_in_the_class_table_has_a_direction():
    """A column that is classified but has no direction would silently score as a tie."""
    for prefix, _kind, _higher in METRIC_PREFIXES:
        assert benefit_sign(prefix, 1.0) in (1, -1), prefix


def test_unpaired_icc_hits_both_corners_exactly():
    """The same 1 + ICC identity applied to RAW values rather than paired differences.

    Two exact corners pin the arithmetic:
      * both seeds of an instance identical, instances differing -> ICC = +1
      * instance means all equal, seeds differing within -> ICC = -1
    """
    identical = [{"arm": "a", "instance": f"i{i}", "seed": s, "v": float(i)}
                 for i in range(5) for s in (0, 1)]
    assert unpaired_icc(identical, "a", "v") == pytest.approx(1.0, abs=1e-12)

    no_between = [{"arm": "a", "instance": f"i{i}", "seed": s,
                   "v": 10.0 + (1.0 if s else -1.0) * (i + 1)}
                  for i in range(5) for s in (0, 1)]
    assert unpaired_icc(no_between, "a", "v") == pytest.approx(-1.0, abs=1e-12)


def test_the_near_zero_icc_does_not_generalise_beyond_paired_differences(k6_rows):
    """THE portable finding: pairing removes the landscape, raw values keep it.

    The paired differences have a median ICC of about -0.02, so n = 50 was barely
    anti-conservative for the contrasts. That does NOT transfer to unpaired quantities --
    arm means, containment proportions, prevalence figures -- where the landscape effect
    is still fully present. `lhs` on raw `auc_pred` runs far positive while `doe` runs
    negative, so the unpaired ICC is both large and arm-dependent.
    """
    med = {}
    for arm in ("lhs", "doe", "qlogei", "qlognei", "random"):
        vals = [unpaired_icc(k6_rows, arm, "auc_pred", gamma=g, tau_frac=t)
                for g in (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)
                for t in (0.60, 0.75, 0.85, 0.95)]
        med[arm] = float(np.median([v for v in vals if np.isfinite(v)]))
    assert med["lhs"] > 0.4, f"lhs unpaired ICC {med['lhs']:+.3f} — expected strongly positive"
    assert med["doe"] < 0.0, f"doe unpaired ICC {med['doe']:+.3f} — expected negative"
    assert max(med.values()) - min(med.values()) > 0.5, (
        "the unpaired ICC should be strongly arm-dependent; if it has flattened, the "
        "claim that n=25 must stay the default for unpaired quantities needs re-checking")
