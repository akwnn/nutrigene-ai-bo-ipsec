"""Claim-impact checks, not replacements for the eight exact historical gates.

Recorded diagnostic scalars below come from the 2026-09-11 replay audit. These
checks reanalyse retained rows; they do not run or certify adaptive trajectories.
"""
import json
import importlib.util
import statistics
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / "results" / name).read_text())


def test_primary_map_claim_recalculates_from_c2_balanced_instance_means():
    rows = [r for r in read("final-spade-c2.json")["rows"]
            if (r["tau_frac_or_quantile"], r["gamma"], r["alpha"]) == (.25, .95, .95)]
    means = {}
    for arm in ("spade_cf_m0", "qlognei"):
        selected = [r for r in rows if r["arm"] == arm]
        assert len(selected) == 100
        assert len({(r["instance_seed"], r["campaign_seed"]) for r in selected}) == 100
        instances = {r["instance_seed"] for r in selected}
        assert len(instances) == 25
        instance_means = []
        for instance in instances:
            group = [r for r in selected if r["instance_seed"] == instance]
            assert {r["campaign_seed"] for r in group} == {0, 1, 2, 3}
            instance_means.append(statistics.mean(r["symmetric_difference_pred"] for r in group))
        means[arm] = statistics.mean(instance_means)
    assert means["spade_cf_m0"] == pytest.approx(.180414, abs=1e-12)
    assert means["qlognei"] == pytest.approx(.2130685, abs=1e-12)
    assert round(100 * (means["qlognei"] - means["spade_cf_m0"]) / means["qlognei"], 1) == 15.3


@pytest.mark.parametrize("source,arm,legacy,historical", [
    ("final-spade-c3.json", "qlogei", .19391397009622446, .22786852462983065),
    ("final-spade-c3.json", "qlognei", .19524908867226243, .1699699208688239),
    ("final-spade-s1.json", "qlogei", .7649100065630514, .5928006956256192),
])
def test_prospective_scalars_match_recorded_legacy_probe_not_old_reference(source, arm, legacy, historical):
    rows = [r for r in read(source)["rows"] if r["arm"] == arm and r["campaign_seed"] == 0]
    assert len(rows) == 12
    assert {r["regret_rule_a"] for r in rows} == {legacy}
    assert legacy != historical


def test_one_observed_classical_drift_does_not_change_figure2_display_or_order():
    # Conditional one-row sensitivity only; not an unobserved-campaign error bound.
    delta = .25251124591423746 - .2525116337195932
    arms = {r["arm"]: r for r in read("fix1-analysis.json")["per_arm"]}
    classical = arms["doe"]
    assert classical["n"] == 50
    for field in ("mean_rule_p",):
        old = classical[field]
        assert f"{old:.4f}" == f"{old + delta / 50:.4f}"
    contrast = classical["delta_p_minus_a"]
    spec = importlib.util.spec_from_file_location("impact_fix1", ROOT / "scripts/analyse_fix1.py")
    analysis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analysis)
    raw = read("fix1-terminal-rule.json")
    keys, a = analysis._align(raw["rows"], raw["config"]["arms"], "regret_a")
    _, p = analysis._align(raw["rows"], raw["config"]["arms"], "regret_p")
    baseline = analysis._contrast(p["doe"], a["doe"])
    changed = p["doe"].copy()
    changed[keys.index(("033466197eba3ddb", 0))] = .25251124591423746
    sensitivity = analysis._contrast(changed, a["doe"])
    for field in ("mean", "lo", "hi", "wilcoxon_p"):
        assert baseline[field] == contrast[field]
    for field in ("mean", "lo", "hi"):
        assert f"{baseline[field]:.4f}" == f"{sensitivity[field]:.4f}"
    assert baseline["wilcoxon_p"] == sensitivity["wilcoxon_p"]
    assert contrast["lo"] - abs(delta) > .02
    for arm in ("qlogei", "qlognei", "versionb"):
        assert classical["mean_rule_a"] < arms[arm]["mean_rule_a"]
        assert classical["mean_rule_p"] + delta / 50 > arms[arm]["mean_rule_p"]


def test_manuscript_states_version_boundary_and_withdraws_historical_cross_family_inference():
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()
    assert "### Replay impact on the reported claims" in text
    assert "not used to support cross-family method rankings" in text
    assert "does not bound errors in untested campaigns" in text
    assert "current default sampler is not the archived sampler" in text
    abstract = text.split("## Abstract\n")[1].split("## Introduction")[0]
    assert "retained regenerated benchmark" in abstract


def test_submission_actions_do_not_request_already_approved_licensing():
    text = (ROOT / "scripts/prepare_submission_bundle.py").read_text()
    assert "Obtain code-owner licensing approval" not in text
