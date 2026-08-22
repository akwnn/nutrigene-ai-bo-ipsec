"""Version C Form 1 -- the re-score. Zero new wells.

C0 returned IDENTIFICATION_ARTEFACT, so section 2 is not built; C3.3b predicts K-C7 fires,
so the detector does not gate. The three Version C arms therefore collapse into one whose
campaign is IDENTICAL to Version B's, and Version C becomes three scoring changes:

    rule P as the terminal rule | split-sample CE | components + five columns + non-vacuity

**Any difference from Version B is therefore attributable to the scoring changes and to
nothing else.** That is the cleanest attribution available, and it only holds if every
shared column reproduces at |delta| = 0 -- which is what most of this file tests.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_run_versionc_form1", ROOT / "scripts" / "run_versionc_form1.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


# --- the arm set, after C0 collapsed it ------------------------------------------------

def test_the_three_versionc_arms_collapsed_and_only_one_is_run():
    """`versionc` == `versionc_form1` == `versionc_nodetect` once m=0 and no detector
    gates. Running three labels for one campaign would triple-count it in every ranking."""
    assert V.COLLAPSED_INTO == "versionc_form1"
    for alias in ("versionc", "versionc_nodetect"):
        assert V.ARM_ALIASES[alias] == "versionc_form1"
    assert "versionc" not in V.ARMS and "versionc_nodetect" not in V.ARMS


def test_versionc_random_is_not_created_as_a_duplicate_arm():
    """At m=0, `versionc_random`'s plate 2 is 8 random wells -- which IS
    `versionb_random`, already committed. Creating it again would put the same campaign in
    the ranking twice under two names."""
    assert "versionc_random" not in V.ARMS
    assert V.ARM_ALIASES["versionc_random"] == "versionb_random"


def test_versionc_fixed_m_is_moot_and_recorded_as_such():
    """It splits 4 trust + 4 boundary, and the trust region was never built."""
    assert "versionc_fixed_m" in V.MOOT_ARMS
    assert "section 2" in V.MOOT_ARMS["versionc_fixed_m"].lower()


def test_plate1_only_is_flagged_never_rank_separately():
    """It IS `lhs` at 48 wells. Including it makes `lhs` a second arm -- this was wrong in
    the first cut of the Part IV headline and had to be redone."""
    assert V.NEVER_RANK_SEPARATELY["plate1_only"] == "lhs"


# --- the gate that makes the attribution clean ------------------------------------------

def test_shared_columns_are_gated_at_exactly_zero():
    assert V.GATE_TOL == 0.0


def test_the_gated_column_list_covers_every_committed_k6_field():
    """A re-score that changes a number it was not supposed to change is a bug, and the
    gate is how you find it -- so the gate must be FULL WIDTH, not a sample."""
    for col in ("vol_pred", "vol_latent", "fi_pred", "fi_latent", "true_frac_above_tau",
                "iou_pred", "auc_pred", "brier_pred", "box_vol_pred", "grid_r2",
                "sup_err", "regret"):
        assert col in V.GATED_COLUMNS, f"{col} is committed but ungated"


def test_a_changed_shared_column_is_a_failure_not_a_finding():
    ref = {"vol_pred": 0.25, "iou_pred": 0.5}
    same = V.gate_row({"vol_pred": 0.25, "iou_pred": 0.5}, ref)
    assert same == []
    moved = V.gate_row({"vol_pred": 0.25 + 1e-16, "iou_pred": 0.5}, ref)
    assert len(moved) == 1 and moved[0]["column"] == "vol_pred"


def test_a_nan_matches_a_nan_because_empty_regions_are_the_common_case():
    """54-69% of predictive regions are empty at some cells, so `fi`/`iou` are nan there.
    nan != nan would fire the gate on the most common row in the study."""
    assert V.gate_row({"fi_pred": float("nan")}, {"fi_pred": float("nan")}) == []
    assert len(V.gate_row({"fi_pred": 0.1}, {"fi_pred": float("nan")})) == 1


# --- the three scoring changes ----------------------------------------------------------

def test_non_vacuity_is_a_registered_metric_not_a_derived_afterthought():
    """D21 found the predictive straddle null on every registered metric while yielding
    32% more non-empty certificates. That effect surfaced post-hoc twice with no home."""
    assert "non_vacuous_pred" in V.ADDED_COLUMNS
    assert "ce_non_vacuous_0.95" in V.ADDED_COLUMNS or "non_vacuous_ce" in V.ADDED_COLUMNS


def test_the_added_columns_never_collide_with_a_gated_one():
    """Additive means additive. A new column that shadows a committed one would make the
    gate compare the new number against itself."""
    assert not (set(V.ADDED_COLUMNS) & set(V.GATED_COLUMNS))


def test_rule_p_and_split_ce_and_components_are_all_present():
    for col in ("regret_p", "ce_split_contain_0.95", "ce_selection_bias_0.95",
                "n_components_pred"):
        assert col in V.ADDED_COLUMNS, f"{col} missing from the re-score"


# --- registered prediction for components -----------------------------------------------

def test_the_component_prediction_is_registered_before_the_run():
    """Largest on hartmann6 (multimodal, disconnected superlevel sets), near-zero on hill
    (unimodal, one component). If it helps everywhere equally, something is wrong."""
    assert V.COMPONENT_PREDICTION["largest"] == "hartmann6"
    assert V.COMPONENT_PREDICTION["near_zero"] == "hill"


# --- partial discipline ------------------------------------------------------------------

def test_a_partial_is_never_written_to_the_registered_path(tmp_path):
    final = tmp_path / "versionc-form1.json"
    V.write_partial(final, rows=[{"arm": "versionc_form1"}], keys_present=1,
                    keys_expected=50, argv=["t"], cfg={})
    assert not final.exists()
    assert final.with_suffix(".json.partial").exists()


def test_promote_refuses_an_incomplete_partial(tmp_path):
    final = tmp_path / "versionc-form1.json"
    V.write_partial(final, rows=[{"arm": "versionc_form1"}], keys_present=1,
                    keys_expected=50, argv=["t"], cfg={})
    with pytest.raises(ValueError):
        V.promote(final)
    assert not final.exists()
