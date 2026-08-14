"""The boundary between candidate numbers and the optimizer.

The committed table is unsigned, so the headline test is that building an evaluator
from it FAILS. Everything else exercises the paths a signed table would take.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest
import yaml

from boec.evaluators import ContinuousLookupEvaluator, LookupEvaluator
from boec.lab.evaluator import (
    GatingIncompleteError,
    MetricMismatchError,
    coded_dose,
    conditions_to_arrays,
    load_conditions,
    load_lab_evaluator,
    unsigned_rows,
)
from boec.space import MetricIdentity, SearchSpace

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"
COND = LAB / "bo_primary_conditions.csv"
CFG = ROOT / "configs" / "lab" / "coating_2026-08-06.yaml"

pytestmark = pytest.mark.skipif(not COND.exists(), reason="conditions CSV not present")


def _space() -> SearchSpace:
    return SearchSpace.from_config(yaml.safe_load(CFG.read_text(encoding="utf-8")))


def _metric() -> MetricIdentity:
    return MetricIdentity(
        "CD31_pct_flow", "percent_of_parent", "cytoflexlx-cd31-cd140a-2026-08-06"
    )


def _signed_csv(tmp_path: Path, values: list[float] | None = None) -> Path:
    """Copy the committed table with y filled and status=gated."""
    rows = load_conditions(COND)
    values = values or [10.0 + i for i in range(len(rows))]
    for row, val in zip(rows, values):
        row["y"] = str(val)
        row["status"] = "gated"
    out = tmp_path / "signed.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return out


# --- the config -------------------------------------------------------------------


def test_space_is_two_d_and_not_the_hall_ogle_cube():
    space = _space()
    assert space.dim == 2
    assert space.names == ("coating", "dose")
    assert space.metric.name == "CD31_pct_flow"
    assert space.parameters[1].physical_low == 0.5
    assert space.parameters[1].physical_high == 20.0


def test_config_names_the_instrument_that_acquired_the_data():
    assert "cytoflexlx" in _space().metric.protocol_version
    assert "novocyte" not in _space().metric.protocol_version.lower()


def test_coded_dose_endpoints_map_to_this_box():
    space = _space()
    phys = space.to_physical(np.array([[0.0, 0.0], [1.0, 1.0]]))
    assert phys[0, 1] == pytest.approx(0.5)
    assert phys[1, 1] == pytest.approx(20.0)
    assert coded_dose(0.5) == pytest.approx(0.0)
    assert coded_dose(20.0) == pytest.approx(1.0)


# --- the refusal ------------------------------------------------------------------


def test_the_committed_table_is_unsigned_and_building_an_evaluator_raises():
    """The headline. Software must not seed a campaign with its own output."""
    with pytest.raises(GatingIncompleteError, match="awaiting_gating"):
        load_lab_evaluator(COND, _space())


def test_the_refusal_names_the_offending_files():
    with pytest.raises(GatingIncompleteError) as exc:
        load_lab_evaluator(COND, _space())
    assert "12 of 12" in str(exc.value)
    assert ".fcs" in str(exc.value)
    assert "GATE.md" in str(exc.value)


def test_unsigned_rows_flags_status_and_missing_y_independently():
    rows = load_conditions(COND)
    assert len(unsigned_rows(rows)) == 12
    for row in rows:
        row["status"] = "gated"          # signed but still empty
    assert len(unsigned_rows(rows)) == 12
    for row in rows:
        row["y"] = "1.0"
    assert unsigned_rows(rows) == []


def test_a_partially_gated_table_is_still_refused(tmp_path):
    path = _signed_csv(tmp_path)
    rows = load_conditions(path)
    rows[3]["y"] = ""                     # one hole is enough
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(GatingIncompleteError):
        load_lab_evaluator(path, _space())


# --- the signed path --------------------------------------------------------------


def test_a_signed_table_builds_an_evaluator_that_serves_its_rows(tmp_path):
    ev = load_lab_evaluator(_signed_csv(tmp_path), _space())
    assert ev.candidates.shape == (12, 2)
    Y, Yvar = ev.evaluate(ev.candidates[:1])
    assert Y.shape == (1, 1) and Yvar.shape == (1, 1)
    assert Y[0, 0] == pytest.approx(10.0)
    assert Yvar[0, 0] == pytest.approx(0.05**2)


def test_arrays_place_fn_and_vtn_on_the_declared_coding():
    X, y, sd = conditions_to_arrays(load_conditions(COND))
    assert X.shape == (12, 2)
    assert set(X[:, 0].tolist()) == {0.0, 1.0}
    assert np.all(np.isnan(y)) and np.all(np.isnan(sd))
    assert X[0].tolist() == pytest.approx([0.0, 0.0])          # FN 0.5 ug/mL
    assert X[-1].tolist() == pytest.approx([1.0, 1.0])         # VTN 20 ug/mL


def test_wrong_metric_is_rejected_even_when_the_table_is_signed(tmp_path):
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    cfg["metric"]["name"] = "CD31_area_per_DAPI"
    with pytest.raises(MetricMismatchError, match="CD31_pct_flow"):
        load_lab_evaluator(_signed_csv(tmp_path), SearchSpace.from_config(cfg))


def test_wrong_protocol_version_is_rejected(tmp_path):
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    cfg["metric"]["protocol_version"] = "novocyte-cd31-cd140a-2026-08-06"
    with pytest.raises(MetricMismatchError, match="protocol_version"):
        load_lab_evaluator(_signed_csv(tmp_path), SearchSpace.from_config(cfg))


# --- why this class exists --------------------------------------------------------


def test_rint_lookup_would_collide_four_of_the_six_dose_levels():
    """The reason LookupEvaluator could not be reused.

    Coded doses are 0, 0.0256, 0.1026, 0.2308, 0.4872, 1. np.rint sends the first four
    to 0, so a rint-indexed table silently keeps one of them.
    """
    coded = np.array([coded_dose(d) for d in (0.5, 1.0, 2.5, 5.0, 10.0, 20.0)])
    assert len(set(np.rint(coded).astype(int).tolist())) == 2
    assert len(set(coded.tolist())) == 6


def test_continuous_lookup_distinguishes_doses_that_rint_would_merge():
    X = np.array([[0.0, 0.0], [0.0, coded_dose(1.0)], [0.0, 1.0]])
    ev = ContinuousLookupEvaluator(X, np.array([10.0, 20.0, 30.0]), np.full(3, np.nan), _metric())
    Y, _ = ev.evaluate(np.array([[0.0, coded_dose(1.0)]]))
    assert Y[0, 0] == pytest.approx(20.0)


def test_phase2_lookup_evaluator_is_untouched_and_still_rints():
    ev = LookupEvaluator(
        np.array([[-1.0, 1.0], [1.0, -1.0]]), np.array([1.0, 2.0]), np.array([0.1, 0.1]), _metric()
    )
    Y, _ = ev.evaluate(np.array([[-1.0, 1.0]]))
    assert Y[0, 0] == pytest.approx(1.0)


def test_unknown_proposal_is_a_keyerror_not_an_interpolation():
    ev = ContinuousLookupEvaluator(
        np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([1.0, 2.0]), np.full(2, np.nan), _metric()
    )
    with pytest.raises(KeyError, match="not in the lab table"):
        ev.evaluate(np.array([[0.0, 0.5]]))


def test_ungated_row_raises_rather_than_returning_nan():
    ev = ContinuousLookupEvaluator(
        np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([np.nan, 2.0]), np.full(2, np.nan), _metric()
    )
    assert ev.candidates.shape == (1, 2)
    with pytest.raises(ValueError, match="ungated"):
        ev.evaluate(np.array([[0.0, 0.0]]))


def test_indistinguishable_table_rows_are_rejected_at_construction():
    with pytest.raises(ValueError, match="identical within atol"):
        ContinuousLookupEvaluator(
            np.array([[0.0, 0.0], [0.0, 0.0]]), np.array([1.0, 2.0]), np.full(2, np.nan), _metric()
        )


def test_zero_sd_floor_is_rejected():
    with pytest.raises(ValueError, match="sd_floor must be positive"):
        ContinuousLookupEvaluator(
            np.array([[0.0, 0.0]]), np.array([1.0]), np.array([np.nan]), _metric(), sd_floor=0.0
        )


def test_truth_matches_evaluate_and_does_not_burn_budget():
    ev = ContinuousLookupEvaluator(
        np.array([[0.0, 0.0]]), np.array([7.0]), np.array([np.nan]), _metric()
    )
    assert ev.truth(np.array([[0.0, 0.0]]))[0, 0] == pytest.approx(7.0)
    assert ev.n_evaluations == 0
    ev.evaluate(np.array([[0.0, 0.0]]))
    assert ev.n_evaluations == 1


def test_wrong_column_count_is_caught():
    ev = ContinuousLookupEvaluator(
        np.array([[0.0, 0.0]]), np.array([1.0]), np.array([np.nan]), _metric()
    )
    with pytest.raises(ValueError, match="columns"):
        ev.evaluate(np.array([[0.0, 0.0, 0.0]]))
