"""The metrics the BO and RSM communities would demand, and Version C's alpha*-analogue.

The coverage brief recorded ZERO coverage for BO conventions -- regret curves against
budget, mean rank, performance profile. The RSM half was closed by FINDINGS section 33.
This closes the BO half, on committed data, plus the correlation question P4b asked of
alpha* asked again of the quantity Version C actually added: the SELECTION BIAS.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "_analyse_versionc_conventions", ROOT / "scripts" / "analyse_versionc_conventions.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


def _rows(spec):
    """spec: {arm: [regret per problem]} -> rows keyed by (instance, seed)."""
    out = []
    for arm, vals in spec.items():
        for i, v in enumerate(vals):
            out.append({"instance": f"i{i}", "seed": 0, "arm": arm,
                        "regret": v, "regret_p": v})
    return out


# --- mean rank --------------------------------------------------------------------------

def test_mean_rank_ranks_within_a_problem_not_across_the_pool():
    """Ranking pooled regrets would let an easy instance outrank a hard one's winner."""
    rows = _rows({"a": [0.1, 0.5], "b": [0.2, 0.6], "c": [0.3, 0.7]})
    r = C.mean_rank(rows, key="regret")
    assert r["a"] == pytest.approx(1.0)
    assert r["b"] == pytest.approx(2.0)
    assert r["c"] == pytest.approx(3.0)


def test_mean_rank_excludes_plate1_only_by_name():
    """`plate1_only` IS `lhs` at 48 wells. Ranking it separately makes `lhs` a second arm
    and shifts every rank below it -- this was wrong in the first cut of the Part IV
    headline and had to be redone."""
    rows = _rows({"lhs": [0.2], "plate1_only": [0.2], "versionb": [0.1]})
    r = C.mean_rank(rows, key="regret")
    assert "plate1_only" not in r
    assert r["versionb"] == pytest.approx(1.0) and r["lhs"] == pytest.approx(2.0)


def test_mean_rank_ties_share_the_average_rank():
    """`lhs` and `plate1_only` agree to 4.44e-16; a tie-breaking rank would invent an
    ordering the data does not contain."""
    rows = _rows({"a": [0.1], "b": [0.1], "c": [0.3]})
    r = C.mean_rank(rows, key="regret")
    assert r["a"] == pytest.approx(1.5) and r["b"] == pytest.approx(1.5)
    assert r["c"] == pytest.approx(3.0)


# --- performance profile (Dolan-More) ----------------------------------------------------

def test_performance_profile_is_one_at_tau_one_for_the_per_problem_winner():
    rows = _rows({"a": [0.1, 0.1], "b": [0.2, 0.2]})
    p = C.performance_profile(rows, key="regret", taus=(1.0, 2.0))
    assert p["a"][1.0] == pytest.approx(1.0)
    assert p["b"][1.0] == pytest.approx(0.0)
    assert p["b"][2.0] == pytest.approx(1.0)


def test_performance_profile_is_monotone_in_tau():
    rows = _rows({"a": [0.1, 0.9], "b": [0.5, 0.2]})
    p = C.performance_profile(rows, key="regret", taus=(1.0, 1.5, 2.0, 10.0))
    for arm, curve in p.items():
        vals = [curve[t] for t in (1.0, 1.5, 2.0, 10.0)]
        assert vals == sorted(vals), f"{arm} profile is not monotone: {vals}"


def test_performance_profile_handles_a_zero_best_without_dividing_by_it():
    """A regret of exactly 0 on some problem is attainable -- the planted-optimum designs
    reach it. A ratio would be inf or nan and would silently drop the problem."""
    rows = _rows({"a": [0.0, 0.2], "b": [0.1, 0.2]})
    p = C.performance_profile(rows, key="regret", taus=(1.0,))
    assert 0.0 <= p["a"][1.0] <= 1.0 and 0.0 <= p["b"][1.0] <= 1.0


# --- Version C's alpha*-analogue: does the SELECTION BIAS track anything? -----------------

def test_bias_correlation_returns_rho_and_a_bootstrap_ci():
    rows = [{"ce_selection_bias_0.95": i / 50, "regret_p": 1.0 - i / 50,
             "total_error_vol_pred": i / 50} for i in range(50)]
    out = C.bias_correlation(rows, against="regret_p", alpha=0.95, n_boot=200)
    assert out["rho"] < -0.9
    # NOT "the CI contains rho". The fixture is a PERFECT monotone relationship, so
    # rho = -1.0 sits on the boundary of the parameter space and no resample can exceed
    # it -- a percentile CI is one-sided there by construction. Asserting containment
    # would be asserting a property percentile bootstraps do not have.
    assert out["ci_lo"] <= out["ci_hi"]
    assert out["excludes_zero"] is True
    assert out["n"] == 50


def test_bias_correlation_drops_nan_rows_rather_than_scoring_them():
    """A nan bias is an EMPTY certificate -- 54-69% of predictive regions are empty at some
    cells, so this is the common row, and scoring it as zero would drag rho toward 0."""
    rows = ([{"ce_selection_bias_0.95": float("nan"), "regret_p": 0.5}] * 20
            + [{"ce_selection_bias_0.95": i / 10, "regret_p": 1.0 - i / 10}
               for i in range(10)])
    out = C.bias_correlation(rows, against="regret_p", alpha=0.95, n_boot=100)
    assert out["n"] == 10


def test_bias_correlation_refuses_too_few_pairs():
    rows = [{"ce_selection_bias_0.95": 0.1, "regret_p": 0.2}] * 3
    with pytest.raises(ValueError):
        C.bias_correlation(rows, against="regret_p", alpha=0.95, n_boot=50)
