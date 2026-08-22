"""Version C section 3.3 -- selecting and fitting the ONE-CLASS boundary.

The fit set is single-class: hill, levy and rosenbrock all tie (Q53's committed table has
levy null at all four cells and rosenbrock null at all four). So the rule cannot be
discriminative and the boundary is a novelty boundary -- the empirical support of the tie
families. Everything here must be computable from the fit set ALONE.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_analyse_versionc_detector", ROOT / "scripts" / "analyse_versionc_detector.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def _rows(values, stat="additive_share", family="hill"):
    return [{"family": family, "dim": 6, "sigma": 0.10, "seed": i, stat: v}
            for i, v in enumerate(values)]


def test_the_non_viable_candidates_are_excluded_by_name():
    """`n_local_maxima` is identically zero at this budget and
    `{x : LCB >= max LCB}` always has one component. A selection procedure that could
    pick either would pick a constant."""
    assert "n_local_maxima" not in B.VIABLE_STATISTICS
    assert set(B.VIABLE_STATISTICS) == {
        "n_components_plausible", "n_peaks_raw", "additive_share",
        "additive_refit_residual", "ard_separation_ratio"}


def test_a_constant_statistic_scores_as_unusable():
    """Tightness is the selection criterion, but a statistic that never moves is not
    tight -- it is uninformative, and the two must not be confused."""
    assert B.is_usable(_rows([0.5] * 20)) is False
    assert B.is_usable(_rows([0.1, 0.4, 0.9, 0.3, 0.7])) is True


def test_the_boundary_is_the_observed_support_with_no_margin():
    """No margin. A margin is a free parameter and there is nothing in the fit set to
    choose it against -- choosing one by looking at hartmann6 is the single thing the
    protocol forbids."""
    lo, hi = B.one_class_boundary(_rows([0.2, 0.5, 0.9, 0.4]), "additive_share")
    assert (lo, hi) == (0.2, 0.9)


def test_the_boundary_pools_every_fitting_family():
    """One boundary across hill, levy and rosenbrock. A per-family boundary would be
    three rules, and the detector sees one plate with no family label on it."""
    rows = (_rows([0.3, 0.4], family="hill")
            + _rows([0.8, 0.9], family="levy")
            + _rows([0.5], family="rosenbrock"))
    assert B.one_class_boundary(rows, "additive_share") == (0.3, 0.9)


def test_tightness_prefers_the_statistic_with_the_smaller_relative_spread():
    """Relative, not absolute: `ard_separation_ratio` lives on a different scale from
    `additive_share`, and an absolute spread would always pick whichever is smaller."""
    tight = _rows([0.50, 0.51, 0.49, 0.50])
    loose = _rows([0.10, 0.90, 0.30, 0.70])
    assert B.tightness(tight, "additive_share") < B.tightness(loose, "additive_share")


def test_ranking_returns_only_usable_statistics_and_is_ordered():
    rows = []
    for i in range(8):
        rows.append({"family": "hill", "dim": 6, "sigma": 0.10, "seed": i,
                     "additive_share": 0.50 + 0.001 * i,        # very tight
                     "ard_separation_ratio": 2.0 + 1.0 * i,     # loose
                     "n_components_plausible": 1,               # constant -> unusable
                     "n_peaks_raw": 100 + i,
                     "additive_refit_residual": 0.5 + 0.05 * i})
    ranked = B.rank_statistics(rows)
    names = [r["statistic"] for r in ranked]
    assert "n_components_plausible" not in names, "a constant statistic was ranked"
    assert names[0] == "additive_share"
    assert [r["tightness"] for r in ranked] == sorted(r["tightness"] for r in ranked)


def test_classify_is_outside_the_support_in_either_direction():
    """A deceptive landscape could sit either side. A one-sided rule would be a guess
    about which, made without a single deceptive example to check it against."""
    assert B.classify(0.50, (0.30, 0.70)) == "UNIMODAL"
    assert B.classify(0.20, (0.30, 0.70)) == "DECEPTIVE"
    assert B.classify(0.80, (0.30, 0.70)) == "DECEPTIVE"
    assert B.classify(0.30, (0.30, 0.70)) == "UNIMODAL", "the support is inclusive"


def test_the_report_refuses_to_touch_a_held_out_family():
    """Defence in depth: the runner cannot construct them, and the analysis will not
    read them if one somehow appears in the file."""
    rows = _rows([0.4, 0.5]) + _rows([0.9], family="hartmann6")
    with pytest.raises(ValueError) as e:
        B.rank_statistics(rows)
    assert "hartmann6" in str(e.value)
