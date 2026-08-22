"""Version C's kill conditions, evaluated rather than assumed.

`run_versionc_form1.py` computes columns; it decides nothing. Without this file the run
finishes, drops ~7 MB, and **no code calls K-C1, K-C2 or K-C3.** A registered kill that
nothing evaluates is not a kill.

Five of the eight are already settled and must be REPORTED as settled rather than silently
skipped -- a kill that quietly disappears is indistinguishable from one that passed.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_analyse_versionc_form1", ROOT / "scripts" / "analyse_versionc_form1.py")
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)


def test_all_eight_kills_are_accounted_for_and_none_is_dropped():
    """The registration lists eight. Every one must appear in the verdict with a status,
    including the ones that cannot fire -- silence and a pass look identical otherwise."""
    assert set(K.KILLS) == {f"K-C{i}" for i in range(1, 9)}


def test_the_settled_kills_carry_the_reason_they_are_settled():
    for kill, expect in (("K-C4", "trust region"), ("K-C5", "versionb_random"),
                         ("K-C8", "same campaign"), ("K-C6", "cannot"),
                         ("K-C7", "one-shot")):
        # K-C7 has now FIRED; its reason still names the one-shot pass that settled it.
        assert K.KILLS[kill]["status"] != "LIVE", f"{kill} is not live"
        assert expect.lower() in K.KILLS[kill]["reason"].lower(), kill


def test_exactly_three_kills_are_live_and_kc2_is_the_hard_stop():
    live = [k for k, v in K.KILLS.items() if v["status"] == "LIVE"]
    assert sorted(live) == ["K-C1", "K-C2", "K-C3"]
    assert K.KILLS["K-C2"]["hard_stop"] is True
    assert K.KILLS["K-C1"]["hard_stop"] is False


# --- K-C1: parity at sigma = 0.10 -------------------------------------------------------

def test_kc1_reads_r_star_from_the_registered_source_only():
    """r* is 'the best committed regret at this (d, sigma) cell, read from e2-grid.json.
    Registered, never chosen after the fact.' Reading it from the run's own best arm would
    be choosing the bar after seeing the numbers."""
    assert "e2-grid" in K.R_STAR_SOURCE


def test_kc1_fires_only_when_the_gap_exceeds_sesoi():
    r_star = 0.0808
    assert K.kc1(regret_p=0.0792, r_star=r_star)["fired"] is False
    assert K.kc1(regret_p=r_star + 0.019, r_star=r_star)["fired"] is False
    assert K.kc1(regret_p=r_star + 0.021, r_star=r_star)["fired"] is True


def test_kc1_reports_the_residual_gap_whether_or_not_it_fires():
    """The registration says 'report the residual gap and its cause' -- so the gap is an
    output, not something only printed on failure."""
    v = K.kc1(regret_p=0.0792, r_star=0.0808)
    assert v["gap"] == pytest.approx(0.0792 - 0.0808)
    assert v["beats_r_star"] is True


# --- K-C2: the hard stop ----------------------------------------------------------------

def test_kc2_thresholds_are_the_committed_version_b_figures():
    assert K.KC2_NOMINAL == {0.50: 0.940, 0.80: 1.000, 0.95: 1.000}


def test_kc2_fires_when_any_alpha_falls_below_its_nominal():
    ok = K.kc2({0.50: 0.940, 0.80: 1.000, 0.95: 1.000})
    assert ok["fired"] is False
    below = K.kc2({0.50: 0.920, 0.80: 1.000, 0.95: 1.000})
    assert below["fired"] is True and 0.50 in below["failed_alphas"]


def test_kc2_treats_a_difference_from_version_b_as_a_DEFECT_not_a_kill():
    """**The distinction that makes this analysis honest.** Version C Form 1's selected
    set is bit-identical to Version B's (C1.2a), so its containment MUST equal Version B's.
    A movement is therefore a bug in the re-score, not evidence about the certificate --
    and calling it a kill would report a defect as a scientific finding."""
    v = K.kc2({0.50: 0.960, 0.80: 1.000, 0.95: 1.000})
    assert v["fired"] is False           # above nominal, so not a kill
    assert v["invariance_violated"] is True
    assert "defect" in v["note"].lower()


def test_kc2_invariance_holds_when_containment_matches_version_b_exactly():
    v = K.kc2({0.50: 0.940, 0.80: 1.000, 0.95: 1.000})
    assert v["invariance_violated"] is False


# --- K-C3: the error-volume trade -------------------------------------------------------

def test_kc3_fires_only_past_ten_percent_worse():
    assert K.kc3(versionc=0.100, versionb=0.100)["fired"] is False
    assert K.kc3(versionc=0.109, versionb=0.100)["fired"] is False
    assert K.kc3(versionc=0.111, versionb=0.100)["fired"] is True


def test_kc3_improvement_never_fires():
    v = K.kc3(versionc=0.080, versionb=0.100)
    assert v["fired"] is False and v["relative_change"] < 0


def test_kc3_also_carries_the_invariance_check():
    """Symmetric difference is built from vol_pred / fi_pred / prevalence, all gated at
    |delta| = 0 against the committed file. It cannot move either."""
    assert K.kc3(versionc=0.100, versionb=0.100)["invariance_violated"] is False
    assert K.kc3(versionc=0.104, versionb=0.100)["invariance_violated"] is True


def test_a_verdict_over_an_empty_run_refuses_rather_than_reporting_pass():
    """No rows must not read as 'nothing fired'."""
    with pytest.raises(ValueError):
        K.verdict([], sigma=0.10)


def test_the_verdict_never_writes_back_over_its_own_input(tmp_path):
    """**Caught by running it.** The output name is derived by replacing
    'versionc-form1' with 'versionc-kills' in the stem. On a file whose name does not
    contain that substring the replace is a no-op, the derived path equals the input
    path, and the analyser silently OVERWRITES the run it was asked to read -- destroying
    hours of compute to write a few kB of verdict.
    """
    src = tmp_path / "vc1.json"
    src.write_text('{"x": 1}')
    assert K.verdict_path(src) != src
    assert K.verdict_path(tmp_path / "versionc-form1-s010.json").name == \
        "versionc-kills-s010.json"


def test_kc7_records_that_it_HAS_fired_not_that_it_is_predicted_to():
    """The one-shot pass ran (FINDINGS §37): 0/50 DECEPTIVE on both hartmann6 and ackley,
    against a rule frozen and committed at 95fca9c before either was touched. Leaving the
    status as BLOCKED/predicted would misreport a settled result as pending."""
    k = K.KILLS["K-C7"]
    assert k["status"] == "FIRED"
    assert k["fired"] is True
    assert "0 / 50" in k["reason"] or "0/50" in k["reason"]
    assert "without Stage 0" in k["consequence"]
