"""Tests for the canonical Hall/Ogle 2025 dataset and the checks that gate it.

The extraction that shipped carried two defects -- a duplicated design corner and a box
whose quartiles were never resolved -- and the validation of the day passed both,
because it counted design ROW TYPES without checking distinctness or completeness of
the responses. `docs/oracle_defensibility.md` then quoted that check as evidence the
extraction "matches the published design structure exactly".

So the first thing these tests establish is that the new checks would have caught it.
`tests/fixtures/prefix_*.json` is the pre-fix extraction, kept verbatim: a regression
test that cannot detect the original defect is not a regression test.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pytest

from boec.published import (
    COLUMNS,
    FIGURE_TABLE_DISCREPANCIES,
    READING_ERROR,
    STAGE_SPEC,
    ExtractionError,
    build_canonical_rows,
    load_extraction_a,
    model_matrix_rank,
    to_pm1,
    validate_against_table,
    validate_extraction,
)

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("stage1", "stage2")
FACTORS = ("collagen_i", "collagen_iv", "laminin_111", "laminin_411", "laminin_511",
           "fibronectin")


def _csv(tag: str) -> list[dict]:
    with (ROOT / f"data/published/hall_ogle_2025_{tag}.csv").open() as fh:
        return list(csv.DictReader(fh))


def _extraction(tag: str) -> dict:
    return json.loads((ROOT / f"data/external/hall_ogle_2025/{tag}.json").read_text())


def _fixture(tag: str) -> dict:
    return json.loads((ROOT / f"tests/fixtures/prefix_{tag}.json").read_text())


def _design(rows: list[dict]) -> np.ndarray:
    cols = [c for c in FACTORS if c in rows[0]]
    return np.array([[int(r[c]) for c in cols] for r in rows])


# --------------------------------------------------------------------------------------
# THE REGRESSION GUARD -- these must fail against the data that shipped
# --------------------------------------------------------------------------------------

def test_corner_distinctness_catches_the_shipped_defect():
    """The duplicated corner must be detected in the pre-fix stage-2 extraction."""
    with pytest.raises(ExtractionError) as e:
        validate_extraction("stage2", _fixture("stage2"))
    msg = str(e.value)
    assert "CORNER-DISTINCTNESS" in msg
    assert "CORNER-COMPLETENESS" in msg


def test_missing_response_catches_the_shipped_defect():
    """Row 2's unresolved box must be detected in the pre-fix stage-2 extraction."""
    with pytest.raises(ExtractionError) as e:
        validate_extraction("stage2", _fixture("stage2"))
    assert "MISSING-RESPONSE" in str(e.value)
    assert "rows [2]" in str(e.value)


def test_structural_checks_alone_do_not_catch_the_stage1_defect():
    """Stage 1's mis-read cell is INVISIBLE to structural validation, by construction.

    Flipping one level in a 22-run D-optimal subset of a 2**6 space yields another
    perfectly valid saturated design. This test pins the limitation so nobody later
    reads a passing structural check as proof the stage-1 design is right.
    """
    validate_extraction("stage1", _fixture("stage1"),
                        design=_table_design("stage1"))  # does NOT raise


def test_table_comparison_catches_the_stage1_defect():
    """Only agreement with the published table detects it."""
    with pytest.raises(ExtractionError) as e:
        validate_against_table("stage1", _fixture("stage1"), root=ROOT,
                               allow_known=False)
    assert "LN511" in str(e.value)


def _table_design(tag: str):
    return [[(v + 1) / 2 for v in r["design"]] for r in load_extraction_a(tag, ROOT)]


# --------------------------------------------------------------------------------------
# The current data must pass
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("tag", STAGES)
def test_current_extraction_passes_every_check(tag):
    rec = _extraction(tag)
    validate_extraction(tag, rec, design=_table_design(tag))
    validate_against_table(tag, rec, root=ROOT)


@pytest.mark.parametrize("tag", STAGES)
def test_row_counts(tag):
    assert len(_csv(tag)) == STAGE_SPEC[tag].n_conditions


@pytest.mark.parametrize("tag", STAGES)
def test_coded_levels_only(tag):
    for r in _csv(tag):
        for c in FACTORS:
            if c in r:
                assert r[c] != "", f"{r['run_id']}.{c} is empty; 0 is a real level"
                assert int(r[c]) in (-1, 0, 1), f"{r['run_id']}.{c} = {r[c]}"


@pytest.mark.parametrize("tag", STAGES)
def test_no_missing_responses(tag):
    for r in _csv(tag):
        for c in ("response", "response_q1", "response_q3", "reconciled"):
            assert r[c] != "" and not math.isnan(float(r[c])), f"{r['run_id']}.{c}"


def test_stage2_is_a_complete_face_centred_ccd():
    D = _design(_csv("stage2"))
    corners = [tuple(r) for r in D if set(r) <= {-1, 1}]
    assert len(corners) == 16
    assert len(set(corners)) == 16, "duplicated corner -- the original defect"
    assert set(corners) == set(itertools.product((-1, 1), repeat=4))
    axial = [tuple(r) for r in D if sum(v != 0 for v in r) == 1]
    assert len(axial) == 8
    for r in axial:
        assert set(r) & {-1, 1}, f"axial run {r} not at +/-1 -- alpha must be 1"
    assert sum(1 for r in D if set(r) == {0}) == 1


def test_stage1_saturates_the_two_factor_model():
    D = _design(_csv("stage1")).astype(float)
    noncentre = D[[i for i, r in enumerate(D) if set(r) != {0}]]
    assert len(noncentre) == 22
    assert len({tuple(r) for r in noncentre}) == 22, "duplicated non-centre run"
    n_par, rank = model_matrix_rank(noncentre, "2fi")
    assert (n_par, rank) == (22, 22)
    # The full 23-run design therefore leaves exactly ONE residual df, not zero. The
    # "zero residual df" figure in the project record describes the 22 non-centre runs.
    _, rank_all = model_matrix_rank(D, "2fi")
    assert len(D) - rank_all == 1


@pytest.mark.parametrize("tag,run_id", [("stage1", "stage1_01"), ("stage2", "stage2_25")])
def test_fibronectin_control_sits_near_one(tag, run_id):
    """Every response is normalized to the FN-only control, so it must read ~1.

    The FN-only condition is the ALL-LOW row: every other protein's low level is
    0 ug/mL while fibronectin's low is 22 ug/mL.
    """
    row = next(r for r in _csv(tag) if r["run_id"] == run_id)
    assert all(int(row[c]) == -1 for c in FACTORS if c in row)
    assert 0.8 <= float(row["response"]) <= 1.2, row["response"]


@pytest.mark.parametrize("tag", STAGES)
def test_responses_non_negative_and_ordered(tag):
    for r in _csv(tag):
        assert float(r["response"]) >= 0
        assert float(r["response_q1"]) <= float(r["response"]) <= float(r["response_q3"])


@pytest.mark.parametrize("tag", STAGES)
def test_reconciliation_integrity(tag):
    """`reconciled` is extraction B's median, and `flagged` marks rank disagreement.

    It is NOT the mean of the two extractions: they measure different statistics (dot
    mean vs box median), so averaging them would mix estimands. The check that they
    agree is whether A's mean lies inside B's [q1, q3] -- asserted here for every row.
    """
    rows = _csv(tag)
    for r in rows:
        assert float(r["reconciled"]) == float(r["extraction_2"])
        assert float(r["reconciled"]) == float(r["response"])
        assert float(r["reading_error"]) == READING_ERROR[tag]
        lo, hi = float(r["response_q1"]), float(r["response_q3"])
        assert lo <= float(r["extraction_1"]) <= hi, (
            f"{r['run_id']}: extraction A's mean {r['extraction_1']} falls outside "
            f"B's [{lo}, {hi}] -- the two extractions genuinely disagree here")
        assert r["flagged"] in ("true", "false")
    a1 = max(rows, key=lambda r: float(r["extraction_1"]))["run_id"]
    a2 = max(rows, key=lambda r: float(r["extraction_2"]))["run_id"]
    disputed = {r["run_id"] for r in rows if r["flagged"] == "true"}
    assert disputed == ({a1, a2} if a1 != a2 else set())


def test_stage2_argmax_disagreement_is_visible_in_the_data():
    """The one disagreement that could change a conclusion must be in the file."""
    flagged = {r["run_id"] for r in _csv("stage2") if r["flagged"] == "true"}
    assert flagged == {"stage2_13", "stage2_18"}


@pytest.mark.parametrize("tag", STAGES)
def test_no_physical_units_anywhere(tag):
    """Coded levels only. The source contradicts itself on Collagen IV."""
    # "conc" as a bare substring is not usable here -- it matches "re-conc-iled".
    forbidden = ("ugml", "ug_ml", "concentration", "_conc", "mgml", "molar")
    for c in _csv(tag)[0]:
        assert not any(f in c for f in forbidden), f"column {c!r} names a physical unit"
    # and no VALUE may be a physical level either: coded factors are only ever -1/0/+1
    for r in _csv(tag):
        for c in FACTORS:
            if c in r:
                assert abs(float(r[c])) <= 1


@pytest.mark.parametrize("tag", STAGES)
def test_schema_matches_the_lookup_evaluator_contract(tag):
    got = list(_csv(tag)[0].keys())
    dropped = {"laminin_111", "laminin_511"} if tag == "stage2" else set()
    assert got == [c for c in COLUMNS if c not in dropped]


@pytest.mark.parametrize("tag", STAGES)
def test_csv_round_trips_from_the_raw_json(tag):
    """The CSV must be regenerable; it is a derived artefact, not a hand-edited one."""
    rebuilt = build_canonical_rows(tag, ROOT)
    on_disk = _csv(tag)
    assert len(rebuilt) == len(on_disk)
    for a, b in zip(rebuilt, on_disk):
        assert a["run_id"] == b["run_id"]
        assert float(a["reconciled"]) == float(b["reconciled"])
        for c in FACTORS:
            if c in b:
                assert int(a[c]) == int(b[c])


def test_declared_discrepancies_are_exactly_the_two_known_cells():
    """Guards against quietly widening the accept-list to silence a new mismatch."""
    assert FIGURE_TABLE_DISCREPANCIES == {
        "stage1": {(22, "LN511"): FIGURE_TABLE_DISCREPANCIES["stage1"][(22, "LN511")]},
        "stage2": {(20, "FN"): FIGURE_TABLE_DISCREPANCIES["stage2"][(20, "FN")]},
    }
    for tag in STAGES:
        with pytest.raises(ExtractionError):
            validate_against_table(tag, _extraction(tag), root=ROOT, allow_known=False)


@pytest.mark.parametrize("tag", STAGES)
def test_design_in_csv_is_the_published_table_not_the_figure(tag):
    """Where the paper contradicts itself the CSV carries the TABLE."""
    csv_D = _design(_csv(tag))
    table = np.array([r["design"] for r in load_extraction_a(tag, ROOT)])
    assert np.array_equal(csv_D, table)
    figure = to_pm1(_extraction(tag)["design"])
    n_diff = int((csv_D != figure).sum())
    assert n_diff == len(FIGURE_TABLE_DISCREPANCIES[tag])


def test_to_pm1_rejects_levels_it_does_not_understand():
    with pytest.raises(ExtractionError):
        to_pm1([[0.0, 0.25, 1.0]])
