"""Budget-to-target extraction — Q52 §2.

A budget-to-target curve reports "evaluations needed to reach regret T" (METHODS 2.14).
This tests the reduction from a regret-versus-budget curve to a single arrival budget,
including the censoring bookkeeping the registration requires: a target the cap forbids
an arm from trying for must be reported as CENSORED, never as "unable to reach"
(OPEN-QUESTIONS Q52, "CAP — 200, and it is a compute limit, not a scientific one").
"""

from __future__ import annotations

import pytest

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target


def test_the_arrival_budget_is_the_first_checkpoint_at_or_below_the_target():
    # regret falls past 0.15 between budget 48 and 100
    curve = {24: 0.30, 48: 0.20, 100: 0.14, 200: 0.09}
    assert first_budget_to_target(curve, target=0.15, cap=200) == 100


def test_a_target_already_met_at_the_first_checkpoint_arrives_there():
    curve = {24: 0.10, 48: 0.08}
    assert first_budget_to_target(curve, target=0.15, cap=200) == 24


def test_equality_counts_as_reaching_the_target():
    """"reach regret T" is <=, not <. A curve that lands exactly on T has arrived."""
    curve = {24: 0.30, 48: 0.15}
    assert first_budget_to_target(curve, target=0.15, cap=200) == 48


def test_a_target_never_reached_within_the_cap_is_censored_not_missing():
    curve = {24: 0.30, 48: 0.20, 100: 0.18, 200: 0.17}
    assert first_budget_to_target(curve, target=0.05, cap=200) is ARRIVAL_CENSORED


def test_checkpoints_beyond_the_cap_are_not_consulted():
    """The cap is a compute limit. An arrival only the uncapped run could see is
    still censored at the cap, because no arm may be credited with a budget it was
    forbidden from spending."""
    curve = {24: 0.30, 100: 0.20, 500: 0.04}
    assert first_budget_to_target(curve, target=0.05, cap=200) is ARRIVAL_CENSORED


def test_a_checkpoint_exactly_at_the_cap_is_consulted():
    curve = {24: 0.30, 200: 0.04}
    assert first_budget_to_target(curve, target=0.05, cap=200) == 200


def test_checkpoints_are_read_in_budget_order_not_insertion_order():
    """A dict built out of order must not change the answer — the arrival is the
    SMALLEST qualifying budget."""
    curve = {200: 0.04, 24: 0.09, 100: 0.05}
    assert first_budget_to_target(curve, target=0.10, cap=200) == 24


def test_a_non_monotone_curve_returns_the_first_crossing():
    """Rule A worsens with budget on the static arms (Q52 §1.1), so curves are not
    monotone. The arrival is the first budget that meets the target, even if the
    curve later rises back above it."""
    curve = {24: 0.09, 48: 0.20, 100: 0.25}
    assert first_budget_to_target(curve, target=0.10, cap=200) == 24


def test_an_empty_curve_is_censored():
    assert first_budget_to_target({}, target=0.10, cap=200) is ARRIVAL_CENSORED


def test_a_curve_with_no_checkpoint_within_the_cap_is_censored():
    curve = {500: 0.01}
    assert first_budget_to_target(curve, target=0.10, cap=200) is ARRIVAL_CENSORED


def test_string_keyed_curves_are_accepted_because_json_has_no_integer_keys():
    """results/q52-flatten.json stores prefixes as JSON object keys, which are
    strings. Reading them back must not silently sort lexicographically."""
    curve = {"24": 0.30, "100": 0.20, "48": 0.14}
    assert first_budget_to_target(curve, target=0.15, cap=200) == 48


def test_a_negative_or_zero_cap_is_refused():
    with pytest.raises(ValueError):
        first_budget_to_target({24: 0.1}, target=0.10, cap=0)
