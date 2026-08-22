"""P8.1's four registered predictions, adjudicated by code written BEFORE the data landed.

Written while `rosenbrock` is at ~24/50 seeds and `ackley` is untouched. That ordering is the
point: an adjudicator authored after seeing the numbers can be tuned, however honestly, to
the answer it finds. This one cannot have been.

THE REGISTERED BARS, copied from `OPEN-QUESTIONS.md` c504558 (P1-P3) and 5a3d082 (P4):

    P1  rosenbrock  <= 8 of 24 cells all-empty   AND  mean alpha_star  > 0.80
    P2  ackley      >= 22 of 24 cells all-empty  AND  mean alpha_star  < 0.10
    P3  cells-empty ranking is the exact reverse of the max tau_q ranking, ties allowed
    P4  ackley mean empty rate > 0.90  AND  rosenbrock mean empty rate < 0.70

P3 is expected to FAIL and that expectation is itself registered (Erratum 33). The
adjudicator must report it either way without special-casing.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pr():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "pr", ROOT / "scripts" / "adjudicate_p8_predictions.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["pr"] = m
    spec.loader.exec_module(m)
    return m


def test_the_bars_are_exactly_as_registered(pr):
    """If a bar drifts, the prediction was not the one that was registered."""
    assert pr.BARS["P1"] == {"family": "rosenbrock", "max_all_empty": 8, "min_alpha_star": 0.80}
    assert pr.BARS["P2"] == {"family": "ackley", "min_all_empty": 22, "max_alpha_star": 0.10}
    assert pr.BARS["P4"] == {"ackley_min_empty_rate": 0.90, "rosenbrock_max_empty_rate": 0.70}


def test_p1_holds_only_when_BOTH_conditions_hold(pr):
    assert pr.p1(all_empty=8, alpha_star=0.81)["held"] is True
    assert pr.p1(all_empty=9, alpha_star=0.81)["held"] is False, "9 > 8 fails the count"
    assert pr.p1(all_empty=8, alpha_star=0.80)["held"] is False, "0.80 is not > 0.80"
    assert pr.p1(all_empty=2, alpha_star=0.99)["held"] is True


def test_p2_holds_only_when_BOTH_conditions_hold(pr):
    assert pr.p2(all_empty=22, alpha_star=0.09)["held"] is True
    assert pr.p2(all_empty=21, alpha_star=0.09)["held"] is False
    assert pr.p2(all_empty=24, alpha_star=0.10)["held"] is False, "0.10 is not < 0.10"


def test_p3_is_pairwise_and_allows_ties(pr):
    """Higher tau_q must never have MORE empty cells. Ties are allowed on either side."""
    perfect = {"a": (0.99, 2), "b": (0.90, 6), "c": (0.50, 22)}
    assert pr.p3(perfect)["held"] is True
    ties = {"a": (0.99, 6), "b": (0.90, 6), "c": (0.50, 22)}
    assert pr.p3(ties)["held"] is True, "equal counts at different tau_q is a tie, allowed"
    inverted = {"a": (0.99, 6), "b": (0.90, 2), "c": (0.50, 22)}
    got = pr.p3(inverted)
    assert got["held"] is False
    assert got["violations"], "a failing P3 must name the offending pair"
    assert ("a", "b") in [tuple(v[:2]) for v in got["violations"]]


def test_p3_reports_the_violation_rather_than_only_a_boolean(pr):
    """'It failed' is not a result. WHICH pair inverted is."""
    got = pr.p3({"hill": (0.93, 6), "levy": (0.96, 2)})
    assert got["held"] is True
    got2 = pr.p3({"hill": (0.93, 2), "levy": (0.96, 6)})
    assert got2["held"] is False
    v = got2["violations"][0]
    assert "levy" in v[:2] and "hill" in v[:2]


def test_p4_is_a_threshold_not_a_rank(pr):
    """P4 must not care about rosenbrock's position inside the certifying group."""
    assert pr.p4(ackley_rate=0.99, rosenbrock_rate=0.58)["held"] is True
    assert pr.p4(ackley_rate=0.99, rosenbrock_rate=0.69)["held"] is True, "0.69 < 0.70"
    assert pr.p4(ackley_rate=0.89, rosenbrock_rate=0.58)["held"] is False
    assert pr.p4(ackley_rate=0.99, rosenbrock_rate=0.70)["held"] is False, "0.70 not < 0.70"


def test_the_adjudicator_refuses_an_incomplete_run(pr):
    """Adjudicating P1/P2 on a partial family would answer a different question."""
    with pytest.raises(Exception):
        pr.assert_complete({"status": "partial", "keys_present": 700, "keys_expected": 1000})
    pr.assert_complete({"status": "COMPLETE", "keys_present": 1000, "keys_expected": 1000})


def test_p3_expected_to_fail_is_recorded_not_special_cased(pr):
    """Erratum 33 registered the expectation. The CODE must not act on it."""
    src = (ROOT / "scripts" / "adjudicate_p8_predictions.py").read_text()
    assert pr.P3_EXPECTED_TO_FAIL is True, "the expectation is recorded"
    assert "if P3_EXPECTED_TO_FAIL" not in src, "but it must never change the verdict"
