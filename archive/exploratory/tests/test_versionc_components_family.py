"""Version C section 4's registered prediction, tested on the family that discriminates.

Registered in `run_versionc_form1.COMPONENT_PREDICTION` **before any component number
existed**: the effect should be **largest on hartmann6** (multimodal, disconnected
superlevel sets) and **near-zero on hill** (unimodal, one component). *"If it helps
everywhere equally, something is wrong."*

FINDINGS section 38.5 confirmed the hill half (1.07 components, box gain +0.0004) and
recorded the hartmann6 half as NOT RUN. This is that half.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_run_vc_comp_family", ROOT / "scripts" / "run_versionc_components_family.py")
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)


def test_the_prediction_is_the_one_registered_in_the_form1_runner():
    """Imported from the runner that registered it, never restated -- a prediction
    retyped in the file that tests it is a prediction that can drift."""
    assert F.PREDICTION["largest"] == "hartmann6"
    assert F.PREDICTION["near_zero"] == "hill"


def test_both_the_target_and_its_control_are_run():
    """hartmann6 alone cannot show 'largest'. The unimodal control is what makes the
    contrast a contrast."""
    assert set(F.FAMILIES) == {"hill", "hartmann6"}


def test_the_screened_arm_is_excluded_by_name_and_the_reason_is_carried():
    """FINDINGS 38.6: `doe` has n_active=4 and its box volume takes only {0.0, 1.0}, so
    summing per-component boxes multiplies 1.0 by the component count. Including it would
    put a +59 in a table about multimodality."""
    assert "doe" in F.EXCLUDED_ARMS
    assert "n_active" in F.EXCLUDED_ARMS["doe"] or "screen" in F.EXCLUDED_ARMS["doe"].lower()
    assert "doe" not in F.ARMS


def test_a_row_carries_components_and_the_single_box_alongside():
    row = F.score_one("hill", dim=6, sigma=0.25, seed=0, arm="versionb",
                      grid_n=2048, gammas=(0.50,), tau_fracs=(0.60,))[0]
    for k in ("family", "arm", "gamma", "tau_frac", "n_components",
              "component_box_vol_sum", "box_vol_all_components", "largest_component_vol"):
        assert k in row, k
    assert row["box_vol_all_components"] <= 1.0 + 1e-12


def test_the_verdict_needs_both_families_before_it_will_call_the_prediction():
    """A verdict computed from one family is not a contrast, and must refuse rather than
    report the target's number as though it were the effect."""
    one = [{"family": "hartmann6", "n_components": 4, "component_box_vol_sum": 0.3,
            "box_vol_all_components": 0.1}]
    with pytest.raises(ValueError):
        F.verdict(one)


def test_the_verdict_confirms_when_hartmann_exceeds_hill_and_refutes_otherwise():
    def rows(fam, ncomp, gain):
        # >= MIN_DEFINED_ROWS non-empty rows, or the underpowered guard fires first.
        return [{"family": fam, "n_components": ncomp,
                 "component_box_vol_sum": gain + 0.1,
                 "box_vol_all_components": 0.1} for _ in range(40)]

    confirmed = F.verdict(rows("hill", 1, 0.001) + rows("hartmann6", 6, 0.20))
    assert confirmed["prediction_holds"] is True

    flat = F.verdict(rows("hill", 5, 0.20) + rows("hartmann6", 5, 0.20))
    assert flat["prediction_holds"] is False
    assert "equally" in flat["note"].lower() or "not" in flat["note"].lower()


def _row(fam, ncomp, gain=0.0):
    return {"family": fam, "n_components": ncomp,
            "component_box_vol_sum": gain + 0.1, "box_vol_all_components": 0.1}


def test_the_verdict_conditions_on_NON_EMPTY_regions():
    """**The loophole this caught in its own first version.**

    A region that certifies nothing has `n_components = 0`. Averaging that in makes the
    statistic measure EMPTINESS, not multimodality -- and hartmann6 certifies nothing in
    89.7% of rows against hill's 27.0%, so the unconditioned mean (0.27 vs 2.00) was
    almost entirely an emptiness contrast wearing a component contrast's name.

    The prediction is about whether a NON-EMPTY superlevel set is disconnected. It is
    undefined on the empty ones, and they must be excluded rather than scored as zero.
    """
    rows = ([_row("hill", 3, 0.02)] * 40 + [_row("hill", 0)] * 40
            + [_row("hartmann6", 5, 0.05)] * 40 + [_row("hartmann6", 0)] * 200)
    v = F.verdict(rows)
    assert v["per_family"]["hill"]["mean_components"] == pytest.approx(3.0)
    assert v["per_family"]["hartmann6"]["mean_components"] == pytest.approx(5.0)
    assert v["prediction_holds"] is True


def test_the_verdict_reports_the_empty_rate_because_it_is_the_confound():
    rows = [_row("hill", 2)] * 80 + [_row("hill", 0)] * 20 + \
           [_row("hartmann6", 2)] * 10 + [_row("hartmann6", 0)] * 90
    v = F.verdict(rows)
    assert v["per_family"]["hill"]["empty_rate"] == pytest.approx(0.2)
    assert v["per_family"]["hartmann6"]["empty_rate"] == pytest.approx(0.9)


def test_the_verdict_refuses_to_call_a_prediction_on_too_few_defined_rows():
    """A family that certifies almost nothing cannot support a verdict either way. The
    honest answer is UNDERPOWERED, not 'does not hold'."""
    rows = [_row("hill", 2)] * 100 + [_row("hartmann6", 3)] * 3 + [_row("hartmann6", 0)] * 297
    v = F.verdict(rows)
    assert v["prediction_holds"] is None
    assert "underpowered" in v["note"].lower() or "too few" in v["note"].lower()
