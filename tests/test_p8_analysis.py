"""P8's analyser · the three ways a certificate summary can lie, pinned.

§35's lesson one level up: a registered run whose columns nothing adjudicates is a
paragraph. P8 produces 24,000 rows of certificate columns; this file pins what may be done
with them.

THE THREE TRAPS, ALL OF THEM DOCUMENTED IN `run_p2_versionb_gamma.vorobev_columns` ITSELF
-------------------------------------------------------------------------------------------
1. **`ce_contain` is CIRCULAR.** `conservative_estimate` selects on it, so it cannot fall
   below alpha. Any containment claim built on it is a tautology (F3, §29).
2. **`ce_empirical` is `nan` for an EMPTY set.** An empty certificate is vacuously
   contained. Counting it as a success inflates the rate with campaigns that certified
   nothing, so empties leave the numerator AND the denominator, and the empty rate is
   reported beside every containment figure.
3. **Exact binomial tails, never a normal approximation** (Erratum 21).
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest
from scipy.stats import binom

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def a8():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "a8", ROOT / "scripts" / "analyse_p8_certificate.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["a8"] = m
    spec.loader.exec_module(m)
    return m


def test_the_circular_column_is_refused(a8):
    """`ce_contain` may be reported but must never back a containment verdict."""
    assert a8.CONTAINMENT_COLUMN.startswith("ce_empirical")
    with pytest.raises(Exception):
        a8.containment_rate([{"ce_contain_0.95": 1.0}], 0.95, column="ce_contain")


def test_empty_sets_leave_BOTH_numerator_and_denominator(a8):
    """The trap that would turn 3 real successes into 'containment 1.000'."""
    rows = [{"ce_empirical_0.95": float("nan"), "ce_empty_0.95": True} for _ in range(47)]
    rows += [{"ce_empirical_0.95": 0.99, "ce_empty_0.95": False} for _ in range(3)]
    got = a8.containment_rate(rows, 0.95)
    assert got["n_scored"] == 3, "empty sets must not enter the denominator"
    assert got["n_empty"] == 47
    assert got["empty_rate"] == pytest.approx(47 / 50)
    assert got["n_total"] == 50, "the empty ones must still be COUNTED and reported"
    assert got["rate"] == pytest.approx(1.0)
    assert got["n_scored"] < got["n_total"], (
        "a containment rate over 3 campaigns must not be presentable as though it were 50")


def test_a_cell_that_certified_nothing_reports_no_rate(a8):
    """All-empty must be `None`, never 1.0 and never 0.0."""
    rows = [{"ce_empirical_0.95": float("nan"), "ce_empty_0.95": True} for _ in range(50)]
    got = a8.containment_rate(rows, 0.95)
    assert got["n_scored"] == 0
    assert got["rate"] is None
    assert got["exact_tail"] is None


def test_containment_counts_are_at_or_above_alpha(a8):
    rows = [{"ce_empirical_0.95": v, "ce_empty_0.95": False}
            for v in (0.94, 0.95, 0.96, 0.20)]
    got = a8.containment_rate(rows, 0.95)
    assert got["n_scored"] == 4
    assert got["n_contained"] == 2, "0.95 itself counts; 0.94 and 0.20 do not"


def test_exact_tail_is_exact(a8):
    assert a8.exact_tail(42, 50, 0.95) == pytest.approx(binom.cdf(42, 50, 0.95), rel=1e-12)
    assert a8.exact_tail(0, 0, 0.95) is None, "no denominator, no tail"


def test_holm_is_applied_across_cells_and_is_monotone(a8):
    adj = a8.holm({"a": 0.001, "b": 0.02, "c": 0.5})
    assert adj["a"] == pytest.approx(0.003)
    assert adj["b"] == pytest.approx(0.04)
    assert adj["c"] == pytest.approx(0.5)
    assert adj["a"] <= adj["b"] <= adj["c"], "Holm must be monotone in the sorted order"


def test_below_nominal_is_reported_not_killed(a8):
    """§29 withdrew 'the certificate fails below nominal'. P8 records, it does not kill."""
    src = (ROOT / "scripts" / "analyse_p8_certificate.py").read_text()
    assert "KILL" not in src.upper() or "not a kill" in src.lower()
    assert a8.VERDICT_IS_DESCRIPTIVE is True
