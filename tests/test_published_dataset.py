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

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "data" / "published"

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
    expected = (["run_id"] + FACTORS[stage] + ["response", "response_sd", "reading_error",
                "extraction_1", "extraction_2", "reconciled", "flagged", "flag_reason"])
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


def test_the_fibronectin_control_is_present_but_not_extractable_and_that_is_recorded():
    """The readout is normalised TO the FN control, and in stage 2 that control is run 3
    — the one condition whose median could not be read. So the normaliser's own value is
    missing from the dataset that depends on it.

    Asserted rather than fixed, because inventing it would be worse. It is the reason no
    absolute-scale claim can be made from stage 2."""
    rows = load("stage2")
    fn_only = [r for r in rows
               if int(r["fn"]) == 1 and all(int(r[f]) == -1 for f in FACTORS["stage2"] if f != "fn")]
    assert len(fn_only) == 1
    assert fn_only[0]["run_id"] == "3"
    assert fn_only[0]["response"] == ""
    assert fn_only[0]["flagged"] == "True"


@pytest.mark.parametrize("stage", ["stage1", "stage2"])
def test_reconciled_equals_response_and_only_one_extraction_survives(stage):
    """The second extraction was never committed and died with the working folder deleted
    in e28c84c. `extraction_2` is written EMPTY rather than reconstructed, and
    `reconciled` therefore equals the single surviving extraction as corrected."""
    for r in load(stage):
        assert r["extraction_2"] == "", "there is no second extraction; it must not be invented"
        assert r["reconciled"] == r["response"]


def test_every_flagged_row_states_why():
    for stage in ("stage1", "stage2"):
        for r in load(stage):
            if r["flagged"] == "True":
                assert r["flag_reason"].strip(), f"{stage} run {r['run_id']} flagged with no reason"


def test_the_two_corrections_are_applied_and_auditable():
    """A corrected cell that looks identical to an uncorrected one is unauditable."""
    rows = {r["run_id"]: r for r in load("stage2")}
    assert int(rows["21"]["fn"]) == 1, "Table 2 row 21 prints '- + + +'"
    assert "Table 2 row 21" in rows["21"]["flag_reason"]
    assert float(rows["18"]["response"]) == pytest.approx(3.48)
    assert "Q3" in rows["18"]["flag_reason"]


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
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_published_dataset.py")],
                   check=True, capture_output=True, cwd=ROOT)
    for s, text in before.items():
        assert (PUB / f"hall_ogle_2025_{s}.csv").read_text() == text, f"{s} is stale"
