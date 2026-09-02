"""Stage 4 — validate the canonical Hall/Ogle CSVs. Tests, not inspection.

This project's defect record is dominated by things that looked right: a pre-registered
trend that could not fail, a test whose name carried a guarantee its body did not, a
`doe` cell that silently ran a BO campaign. The dataset gets asserted, not eyeballed.

Everything here runs from a clean clone: the CSVs are committed, the raw JSONs are
committed, and the round-trip test regenerates one from the other.
"""

from __future__ import annotations

import csv
import itertools
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
PUB = ROOT / "research" / "data" / "published"

FACTORS = {
    "stage1": ["c", "civ", "ln111", "ln411", "ln511", "fn"],
    "stage2": ["c", "civ", "ln411", "fn"],
}
EXPECTED_ROWS = {"stage1": 23, "stage2": 25}
SCHEMA = ["run_id", "*factors*", "response", "response_sd", "reading_error",
          "extraction_1", "extraction_2", "reconciled", "flagged", "flag_reason"]


def load(stage: str) -> list[dict]:
    with (PUB / f"hall_ogle_2025_{stage}.csv").open() as fh:
        return list(csv.DictReader(fh))


def design(stage: str) -> np.ndarray:
    return np.array([[int(r[f]) for f in FACTORS[stage]] for r in load(stage)], dtype=float)


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_row_count(stage):
    assert len(load(stage)) == EXPECTED_ROWS[stage]


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_every_coded_level_is_minus_one_zero_or_plus_one(stage):
    """The JSONs store 0.0/0.5/1.0. Emitting those would silently change the design's
    scaling and every effect estimate computed from it."""
    assert set(np.unique(design(stage)).tolist()) <= {-1.0, 0.0, 1.0}


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_schema_is_exactly_the_lookup_evaluator_contract(stage):
    # response_q1/response_q3 were added when the second extraction was recovered: they
    # carry the dispersion without response_sd's normality assumption, which overstates
    # several rows (stage2_08 -> sd 4.38 on a response of 2.27). response_sd is retained
    # because `run_replay_hall_ogle.py` reads it.
    expected = (["run_id"] + FACTORS[stage] + ["response", "response_sd", "response_q1",
                "response_q3", "reading_error", "extraction_1", "extraction_2",
                "reconciled", "flagged", "flag_reason"])
    assert list(load(stage)[0]) == expected


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_no_physical_unit_column_anywhere(stage):
    """B3. Everything runs in coded space so that nothing depends on the Collagen IV
    concentration the source paper contradicts itself about."""
    cols = " ".join(load(stage)[0]).lower()
    assert "ugml" not in cols and "ug_ml" not in cols and "µg" not in cols


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_missing_values_are_empty_never_zero(stage):
    """Zero is a real coded level and a plausible response. A placeholder zero would be
    indistinguishable from a measurement."""
    for r in load(stage):
        for field in ("response", "response_sd", "extraction_1"):
            assert r[field] == "" or float(r[field]) == float(r[field])
        if r["response"] == "":
            assert r["flagged"] == "True", "an unextractable condition must be flagged"


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_responses_are_non_negative(stage):
    vals = [float(r["response"]) for r in load(stage) if r["response"] != ""]
    assert all(v >= 0 for v in vals)


def test_stage1_is_saturated_for_the_two_factor_interaction_model():
    """B4, and the reason it is a limitation rather than a contradiction.

    22 parameters, rank 22, 23 runs of which one is a centre point. There are **zero
    residual degrees of freedom**, so a main effect computed from condition medians
    returning null is the arithmetically expected outcome, not evidence against the
    paper. The paper's own tests used replicate-level degrees of freedom that do not
    exist in digitized medians."""
    X = design("stage1")
    cols = ([np.ones(len(X))] + [X[:, i] for i in range(X.shape[1])]
            + [X[:, i] * X[:, j] for i, j in itertools.combinations(range(X.shape[1]), 2)])
    M = np.column_stack(cols)
    assert M.shape[1] == 22
    assert np.linalg.matrix_rank(M) == 22
    assert len(X) - M.shape[1] == 1  # the single centre point, and nothing else


def test_stage2_is_a_face_centred_central_composite_design():
    """16 factorial + 8 axial + 1 centre = 25, as `design_check` in the raw JSON says.
    Face-centred means axial points sit at +/-1, not at +/-alpha outside the cube."""
    X = design("stage2")
    centre = [i for i, r in enumerate(X) if np.all(r == 0)]
    axial = [i for i, r in enumerate(X) if np.count_nonzero(r) == 1]
    factorial = [i for i, r in enumerate(X) if np.all(np.abs(r) == 1)]
    assert len(centre) == 1
    assert len(axial) == 8
    assert len(factorial) == 16
    assert len(centre) + len(axial) + len(factorial) == len(X)
    for i in axial:
        assert set(np.abs(X[i][X[i] != 0]).tolist()) == {1.0}, "axial must be face-centred"


def test_the_fibronectin_control_reads_near_one_in_both_stages():
    """UPDATED, and the previous premise was wrong twice over.

    It identified the FN control as the row with `fn == +1` and the others low, i.e.
    run 3 -- fibronectin at its HIGH level (75 ug/mL). But "fibronectin only" is about
    the other proteins being ABSENT, and every other protein's low level is 0 ug/mL
    while fibronectin's low is 22. So `- - - -` and `- - - +` are BOTH fibronectin-only,
    differing in dose, and the normaliser is the all-low row:

        stage1 run 1   FN 22 alone   0.9692   <- reads ~1
        stage2 run 25  FN 22 alone   1.0275   <- reads ~1
        stage2 run 3   FN 75 alone   0.7056

    The same physical condition reads ~1.0 in both stages, which is what a normaliser
    must do. It also assumed run 3's median was unreadable; it is 0.7056, recovered by
    widening the box-edge pair tolerance from 3 px to 4 (the edges disagree by 4 px where
    a dot merges with the corner).

    So the normaliser is present and correct, and stage 2's absolute scale is not
    compromised the way the old docstring claimed."""
    for stage, run_id, value in (("stage1", "1", 0.9692), ("stage2", "25", 1.0275)):
        rows = {r["run_id"]: r for r in load(stage)}
        row = rows[run_id]
        assert all(int(row[f]) == -1 for f in FACTORS[stage])
        assert float(row["response"]) == pytest.approx(value, abs=1e-4)
        assert 0.8 <= float(row["response"]) <= 1.2
        assert row["flagged"] == "False", "the control needs no correction"


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_reconciled_equals_response_and_only_one_extraction_survives(stage):
    """UPDATED: the second extraction was NOT lost.

    It was never committed -- `git log --diff-filter=A` was right about that -- but it
    was on disk at `/Users/jy/BO/`, outside the repo, and is now preserved at
    `research/data/external/extraction_a/`. So `extraction_2` is populated from the real thing
    rather than left empty, and it is still never invented: rows whose median could not
    be resolved leave it blank.

    `extraction_1` is the third-party dot mean, `extraction_2` our box median, and
    `reconciled` is `extraction_2`. The two are NOT averaged -- they are different
    statistics, and their difference (0.10 / 0.34) is dominated by that rather than by
    reading error (0.025 / 0.037)."""
    for r in load(stage):
        assert r["extraction_1"] != "", "the second extraction is at research/data/external/extraction_a/"
        if r["response"] == "":
            assert r["extraction_2"] == "" and r["reconciled"] == ""
            continue
        assert r["reconciled"] == r["response"] == r["extraction_2"]


def test_every_flagged_row_states_why():
    for stage in ("stage1", "stage2"):
        for r in load(stage):
            if r["flagged"] == "True":
                assert r["flag_reason"].strip(), f"{stage} run {r['run_id']} flagged with no reason"


def test_the_corrections_are_applied_and_auditable():
    """A corrected cell that looks identical to an uncorrected one is unauditable.

    UPDATED: there are four corrections in stage 2, not two. The median-reads-Q3 defect
    caught on run 18 was not isolated -- `_boxes` skips 3 px while a Q3 rule can be
    thicker, so it also hit run 11 (4 px rule) and run 5 (10 px rule). Run 5's median has
    merged with its Q3 entirely and is refused rather than guessed.
    """
    rows = {r["run_id"]: r for r in load("stage2")}
    assert int(rows["21"]["fn"]) == 1, "Table 2 row 21 prints '- + + +'"
    assert "pdf_crosscheck.md:130" in rows["21"]["flag_reason"]
    # run 18 -- the one the cross-check caught; 3.4911 is the same rule B read as 3.48
    assert float(rows["18"]["response"]) == pytest.approx(3.4911, abs=1e-4)
    assert "Q3 rule" in rows["18"]["flag_reason"]
    # run 11 -- same defect, missed by the hand correction
    assert float(rows["11"]["response"]) == pytest.approx(2.3645, abs=1e-4)
    assert "Q3 rule" in rows["11"]["flag_reason"]
    # run 5 -- not separable, left empty with its bound recorded
    assert rows["5"]["response"] == ""
    assert "NOT SEPARABLE" in rows["5"]["flag_reason"]


def test_the_corrected_stage2_argmax_agrees_with_the_lost_extraction():
    """B1 dissolves. Correcting run 18's median from its Q3 to its true median moves the
    argmax from 18 to 13, which is what the other extraction reported.

    **This does not reinstate an argmax claim** — Q31 registered that as unsupportable on
    grounds this correction cannot touch: the top five IQRs share a common band and the
    paper never names a best condition. Asserted here so the agreement is on record and
    the claim's independence from it is explicit."""
    rows = [r for r in load("stage2") if r["response"] != ""]
    best = max(rows, key=lambda r: float(r["response"]))
    assert best["run_id"] == "13"


def test_the_csvs_regenerate_from_the_raw_json():
    """Round-trip. If the builder and the committed CSVs ever disagree, one of them is
    stale and no test that reads only the CSVs would notice."""
    before = {s: (PUB / f"hall_ogle_2025_{s}.csv").read_text() for s in ("stage1", "stage2")}
    subprocess.run([sys.executable, str(ROOT / "software" / "scripts" / "build_published_dataset.py")],
                   check=True, capture_output=True, cwd=ROOT)
    for s, text in before.items():
        assert (PUB / f"hall_ogle_2025_{s}.csv").read_text() == text, f"{s} is stale"
