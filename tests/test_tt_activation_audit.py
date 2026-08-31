from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_tt_activation import summarize_rows, validate_rows
from scripts.analyse_tt_theta_tau import holm_adjust


def _row(family: str, seed: int, round_index: int, active: bool) -> dict:
    return {
        "family": family,
        "seed": seed,
        "adaptive_round": round_index,
        "active": active,
    }


def test_validate_rows_rejects_a_duplicate_cell():
    rows = [_row("ackley", 0, 1, True), _row("ackley", 0, 1, False)]
    with pytest.raises(ValueError, match="duplicate"):
        validate_rows(rows, ("ackley",), range(1), adaptive_rounds=1)


def test_validate_rows_rejects_a_missing_cell():
    with pytest.raises(ValueError, match="missing"):
        validate_rows([], ("ackley",), range(1), adaptive_rounds=1)


def test_summarize_rows_counts_rounds_and_fully_active_campaigns():
    rows = [
        _row("ackley", 0, 1, True),
        _row("ackley", 0, 2, True),
        _row("ackley", 1, 1, True),
        _row("ackley", 1, 2, False),
    ]
    got = summarize_rows(rows, ("ackley",), range(2), adaptive_rounds=2)
    assert got["active_rounds"] == 3
    assert got["total_rounds"] == 4
    assert got["campaigns_active_all_rounds"] == 1
    assert got["total_campaigns"] == 2
    assert got["by_family"]["ackley"]["active_by_round"] == [2, 1]


def test_holm_adjusts_the_two_smallest_family_p_values_to_point_zero_six():
    got = holm_adjust({
        "hartmann6": 0.012,
        "ackley": 0.015,
        "hill": 0.40,
        "levy": 0.70,
        "rosenbrock": 0.90,
    })
    assert got["hartmann6"] == pytest.approx(0.06)
    assert got["ackley"] == pytest.approx(0.06)
    assert all(value >= 0.05 for value in got.values())


def test_committed_audit_has_the_independently_reproduced_totals():
    path = Path(__file__).resolve().parents[1] / "results" / "tt-activation-audit.json"
    if not path.exists():
        pytest.skip("activation artifact is generated after the audit implementation is frozen")
    raw = json.loads(path.read_text())
    assert raw["status"] == "COMPLETE"
    assert raw["active_rounds"] == 206
    assert raw["total_rounds"] == 640
    assert raw["campaigns_active_all_rounds"] == 20
    assert raw["total_campaigns"] == 160
