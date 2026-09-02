"""Tests for the canonical Hall/Ogle 2025 dataset and the checks that gate it.

The extraction that shipped carried two defects -- a duplicated design corner and a box
whose quartiles were never resolved -- and the validation of the day passed both,
because it counted design ROW TYPES without checking distinctness or completeness of
the responses. `docs/oracle_defensibility.md` then quoted that check as evidence the
extraction "matches the published design structure exactly".

So the first thing these tests establish is that the new checks would have caught it.
`software/tests/fixtures/prefix_*.json` is the pre-fix extraction, kept verbatim: a regression
test that cannot detect the original defect is not a regression test.

Schema note: the short factor names and integer `run_id` are the replay's contract
(`software/scripts/run_replay_hall_ogle.py:72-76`). `software/tests/test_published_dataset.py` covers the
same file from the replay's side; this module covers extraction and validation.
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
    EXTRACTION_A_ERRORS,
    FIGURE_STRIP_ERRORS,
    MEDIAN_CORRECTIONS,
    READING_ERROR,
    STAGE_SPEC,
    ExtractionError,
    build_canonical_rows,
    canonical_design,
    model_matrix_rank,
    to_pm1,
    validate_against_table,
    validate_extraction,
)

ROOT = Path(__file__).resolve().parents[2]
STAGES = ("stage1", "stage2")
FACTORS = ("c", "civ", "ln111", "ln411", "ln511", "fn")


def _csv(tag: str) -> list[dict]:
    with (ROOT / f"research/data/published/hall_ogle_2025_{tag}.csv").open() as fh:
        return list(csv.DictReader(fh))


def _extraction(tag: str) -> dict:
    return json.loads((ROOT / f"research/data/external/hall_ogle_2025/{tag}.json").read_text())


def _fixture(tag: str) -> dict:
    return json.loads((ROOT / "software" / "tests" / "fixtures" / f"prefix_{tag}.json").read_text())


def _design(rows: list[dict]) -> np.ndarray:
    cols = [c for c in FACTORS if c in rows[0]]
    return np.array([[int(r[c]) for c in cols] for r in rows])


def _canonical01(tag: str):
    return (canonical_design(tag, _extraction(tag)) + 1) / 2


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


# --------------------------------------------------------------------------------------
# Which source wins, and why it cannot be decided wholesale
# --------------------------------------------------------------------------------------

def test_the_two_sources_disagree_on_exactly_one_cell_each():
    """Neither digitization is systematically wrong; each has one isolated cell error.

    This is the test that stops "prefer the table" or "prefer the figure" from becoming
    a rule. An earlier pass assumed the table always wins and was about to overwrite
    stage1_23 LN511, which the paper prints as `+`.
    """
    assert len(FIGURE_STRIP_ERRORS["stage2"]) == 1 and not FIGURE_STRIP_ERRORS["stage1"]
    assert len(EXTRACTION_A_ERRORS["stage1"]) == 1 and not EXTRACTION_A_ERRORS["stage2"]


def test_stage1_ln511_is_left_alone():
    """The paper prints `+ + + + + -` (pdf_crosscheck.md:129). Do not "fix" it.

    Our strip reads solid black there (patch grey 0.9) and agrees with the paper; the
    third-party transcription is the outlier. No structural check can see any of this --
    a 22-run D-optimal subset stays valid under a single flip, rank 22 either way -- so
    only the PDF settles it.
    """
    row = next(r for r in _csv("stage1") if r["run_id"] == "23")
    assert int(row["ln511"]) == 1
    assert row["flagged"] == "False", "this cell is correct; it is not a correction"
    assert int(to_pm1(_extraction("stage1")["design"])[22][4]) == 1


def test_stage2_fn_corner_is_corrected_from_the_strip():
    row = next(r for r in _csv("stage2") if r["run_id"] == "21")
    assert int(row["fn"]) == 1
    assert row["flagged"] == "True" and "pdf_crosscheck" in row["flag_reason"]
    assert int(to_pm1(_extraction("stage2")["design"])[20][3]) == -1  # strip still wrong


# --------------------------------------------------------------------------------------
# The current data must pass
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("tag", STAGES)
def test_current_extraction_passes_every_check(tag):
    rec = _extraction(tag)
    validate_extraction(tag, rec, design=_canonical01(tag))
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
    """Every row has a response, except those DECLARED unresolvable with evidence."""
    unresolvable = {i for (t, i), (v, _) in MEDIAN_CORRECTIONS.items()
                    if t == tag and v is None}
    for i, r in enumerate(_csv(tag)):
        for c in ("response_q1", "response_q3"):
            assert r[c] != "", f"{r['run_id']}.{c}"      # quartiles always recovered
        for c in ("response", "reconciled"):
            if i in unresolvable:
                assert r[c] == "", f"{r['run_id']}.{c} must be EMPTY, not a substitute"
                assert r["flagged"] == "True" and r["flag_reason"]
            else:
                assert r[c] != "" and not math.isnan(float(r[c]))


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


@pytest.mark.parametrize("tag,run_id,value", [("stage1", "1", 0.9692),
                                              ("stage2", "25", 1.0275)])
def test_fibronectin_control_is_the_all_low_row_and_reads_near_one(tag, run_id, value):
    """Responses are normalized to the FN-only control, so it must read ~1.

    The FN-only condition is the ALL-LOW row. Every other protein's low level is 0 ug/mL
    while fibronectin's low is 22, so "fibronectin only" means the others are absent --
    NOT that fibronectin is at its high level. Both `- - - -` and `- - - +` are
    fibronectin-only in stage 2; only the all-low one reads ~1.0 (1.0275 against 0.7056),
    and it is the same physical condition that reads 0.9692 in stage 1.
    """
    row = next(r for r in _csv(tag) if r["run_id"] == run_id)
    assert all(int(row[c]) == -1 for c in FACTORS if c in row)
    assert float(row["response"]) == value
    assert 0.8 <= float(row["response"]) <= 1.2


@pytest.mark.parametrize("tag", STAGES)
def test_responses_non_negative_and_ordered(tag):
    for r in _csv(tag):
        if r["response"] == "":
            continue
        assert float(r["response"]) >= 0
        assert float(r["response_q1"]) <= float(r["response"]) <= float(r["response_q3"])


@pytest.mark.parametrize("tag", STAGES)
def test_reconciliation_integrity(tag):
    """`reconciled` is our box median, NOT the mean of the two extractions.

    They measure different statistics -- a dot mean and a box median -- so their
    difference (0.10 / 0.34) is dominated by the choice of statistic, not by reading
    error (0.025 / 0.037). Averaging them would mix estimands, and the "agree within
    reading error" rule flags 42 of 48 rows. The estimand-appropriate test is whether
    A's mean lies inside our [q1, q3], asserted here for every row.
    """
    rows = _csv(tag)
    for r in rows:
        assert float(r["reading_error"]) == READING_ERROR[tag]
        assert r["flagged"] in ("True", "False")
        assert (r["flag_reason"] != "") == (r["flagged"] == "True"), (
            f"{r['run_id']}: flagged and flag_reason must agree")
        if r["reconciled"] == "":
            continue
        assert float(r["reconciled"]) == float(r["extraction_2"])
        assert float(r["reconciled"]) == float(r["response"])
        lo, hi = float(r["response_q1"]), float(r["response_q3"])
        assert lo <= float(r["extraction_1"]) <= hi, (
            f"{r['run_id']}: extraction A's mean {r['extraction_1']} falls outside "
            f"our [{lo}, {hi}] -- the two extractions genuinely disagree here")


@pytest.mark.parametrize("tag", STAGES)
def test_the_second_extraction_is_present(tag):
    """It was reported lost. It was outside the repo, at `research/data/external/extraction_a/`.

    A build that believes there is only one extraction cannot reconcile anything and,
    more importantly, has no second reading of the design to check against.
    """
    rows = _csv(tag)
    unresolvable = {i for (t, i), (v, _) in MEDIAN_CORRECTIONS.items()
                    if t == tag and v is None}
    assert sum(1 for r in rows if r["extraction_1"] != "") == len(rows)
    assert sum(1 for r in rows if r["extraction_2"] != "") == len(rows) - len(unresolvable)


def test_stage2_argmax_agrees_once_the_median_defect_is_corrected():
    """The argmax dispute was OUR bug, not an ambiguity in the source.

    Before correction our stage2_18 median was 4.2215 -- actually that column's Q3 --
    which beat stage2_13 and manufactured a disagreement with the third-party
    extraction. With the declared corrections applied both pick the same condition.

    This does NOT reinstate an argmax claim. The top IQRs share a common band and the
    paper never names a best stage-2 condition; the scope stays rank recovery.
    """
    rows = _csv("stage2")
    ours = max((r for r in rows if r["reconciled"]), key=lambda r: float(r["reconciled"]))
    theirs = max(rows, key=lambda r: float(r["extraction_1"]))
    assert ours["run_id"] == theirs["run_id"] == "13"


def test_every_median_correction_is_reflected_in_the_csv():
    """Guards against a declared correction silently not being applied."""
    for (tag, i), (value, _) in MEDIAN_CORRECTIONS.items():
        row = _csv(tag)[i]
        if value is None:
            assert row["response"] == "", f"{row['run_id']} should be unresolved"
        else:
            assert float(row["response"]) == value, row["run_id"]
        assert row["flagged"] == "True" and row["flag_reason"]


@pytest.mark.parametrize("tag", STAGES)
def test_reading_error_is_optical_not_a_fraction_of_the_signal(tag):
    """+/-3 px at each figure's calibration, and nothing else.

    A previous derivation took 7% of the medians' RANGE, giving 0.0655 and 0.2496. The
    doc it came from never defined "spread", and its quoted percentages only reconcile
    against the standard deviation, not the range. 0.2496 is a quarter of a response
    unit -- larger than most between-condition differences it is meant to bound.
    """
    px = {"stage1": 1 / 121.75, "stage2": 1 / 80.778}[tag]
    assert READING_ERROR[tag] == pytest.approx(3 * px, abs=0.0005)
    med = np.array([float(r["response"]) for r in _csv(tag) if r["response"]])
    assert READING_ERROR[tag] < 0.1 * med.std(ddof=1)


@pytest.mark.parametrize("tag", STAGES)
def test_no_physical_units_anywhere(tag):
    # "conc" as a bare substring is not usable here -- it matches "re-conc-iled".
    forbidden = ("ugml", "ug_ml", "concentration", "_conc", "mgml", "molar")
    for c in _csv(tag)[0]:
        assert not any(f in c for f in forbidden), f"column {c!r} names a physical unit"
    for r in _csv(tag):
        for c in FACTORS:
            if c in r:
                assert abs(float(r[c])) <= 1


@pytest.mark.parametrize("tag", STAGES)
def test_schema_matches_the_replay_contract(tag):
    got = list(_csv(tag)[0].keys())
    dropped = {"ln111", "ln511"} if tag == "stage2" else set()
    assert got == [c for c in COLUMNS if c not in dropped]


@pytest.mark.parametrize("tag", STAGES)
def test_csv_round_trips_from_the_raw_json(tag):
    """The CSV must be regenerable; it is a derived artefact, not a hand-edited one."""
    rebuilt = build_canonical_rows(tag, ROOT)
    on_disk = _csv(tag)
    assert len(rebuilt) == len(on_disk)
    for a, b in zip(rebuilt, on_disk):
        assert str(a["run_id"]) == b["run_id"]
        assert str(a["reconciled"]) == b["reconciled"]
        for c in FACTORS:
            if c in b:
                assert int(a[c]) == int(b[c])


def test_canonical_design_rejects_a_stale_declaration():
    """If the strip stops reading what a declared correction says it reads, halt."""
    rec = _extraction("stage2")
    tampered = dict(rec, design=[list(r) for r in rec["design"]])
    tampered["design"][20][3] = 1.0          # design is (conditions x factors)
    with pytest.raises(ExtractionError):
        canonical_design("stage2", tampered)


def test_to_pm1_rejects_levels_it_does_not_understand():
    with pytest.raises(ExtractionError):
        to_pm1([[0.0, 0.25, 1.0]])
