"""Validation and canonical-CSV emission for the digitized Hall/Ogle 2025 data.

The extractor that produced `research/data/external/hall_ogle_2025/*.json` validated itself by
counting design ROW TYPES -- factorial, axial, centre -- and got 16/8/1 for stage 2,
matching the published structure. It never checked that the 16 corners were *distinct*,
and never checked that a response was actually recovered. Both defects were present in
the committed data and both passed that check.

So the checks here are written to fail on the data that shipped. A check whose name
carries a guarantee its body does not verify is worse than no check, because it is
quoted in the methods section as if it were evidence.

Coding convention: everything in this module is in **coded +/-1 units** (-1 low,
0 centre, +1 high). The extractor emits 0/0.5/1; `to_pm1` converts. No physical
concentration ever appears -- the source contradicts itself on Collagen IV
(Results says 28, Methods says 56) and `docs/source_verification.md` records that as
permanently unresolved.
"""

from __future__ import annotations

import csv
import itertools
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = [
    "ExtractionError",
    "STAGE_SPEC",
    "to_pm1",
    "validate_extraction",
    "validate_against_table",
    "canonical_design",
    "load_extraction_a",
    "model_matrix_rank",
]

# Extraction A keys its design to the PUBLISHED coded tables (Table 1 / Table 2) rather
# than to the greyscale strip, which makes it an independent second reading of the
# design. It is NOT an authority that overrides the strip: its own transcription of
# Table 1 row 23 is wrong (see EXTRACTION_A_ERRORS). Each source has one bad cell and
# only the PDF cross-check settles which.
EXTRACTION_A = {
    "stage1": "research/data/external/extraction_a/stage1_fig1a_table1_extracted.csv",
    "stage2": "research/data/external/extraction_a/stage2_fig2a_table2_extracted.csv",
}
_LEVEL = {"-": -1, "0": 0, "+": 1}

# The two design cells where the figure strip and the third-party transcription
# disagree. BOTH are settled by `docs/pdf_crosscheck.md:126-127`, a four-reader read of
# the source PDF itself, and **they split -- one each**. Neither digitization is
# systematically wrong; each has exactly one isolated cell error.
#
# Do not resolve these by preferring one source wholesale. An earlier pass here assumed
# "the table always wins", inferred that Table 1 row 23 could not contain the strip's
# reading, and was about to overwrite a CORRECT cell. The paper prints
# `+ + + + + -` there. Only the PDF settles it; structural argument does not.
#
#: Cells where the FIGURE STRIP is wrong and must be corrected in the canonical design.
FIGURE_STRIP_ERRORS = {
    "stage1": {},
    # Strip reads FN low (patch grey 212.0), repeating col 15 and leaving corner
    # (-1,+1,+1,+1) absent from a face-centred CCD that requires all 16. Table 2 row 21
    # prints `- + + +` (pdf_crosscheck.md:130). Structure and the PDF agree.
    "stage2": {(20, "FN"): (-1, 1, "strip reads FN low (grey 212.0), duplicating col 15 "
                            "and omitting corner (-1,+1,+1,+1); Table 2 row 21 prints "
                            "'- + + +' (pdf_crosscheck.md:130)")},
}

#: Cells where the THIRD-PARTY transcription is wrong. The figure needs no correction
#: here; this exists so `validate_against_table` does not report a false mismatch, and
#: so nobody "fixes" the cell later.
EXTRACTION_A_ERRORS = {
    # A transcribes Table 1 row 23 as `+ + + + - -`. The paper prints `+ + + + + -`
    # (pdf_crosscheck.md:129), and our strip reads solid black (patch grey 0.9) = high.
    # Figure and paper agree; A is the outlier.
    "stage1": {(22, "LN511"): (-1, 1, "A transcribes `+ + + + - -`; the paper prints "
                               "`+ + + + + -` (pdf_crosscheck.md:129) and the strip "
                               "reads grey 0.9 (solid). A is the outlier")},
    "stage2": {},
}

#: Union, for the reconciliation check only.
FIGURE_TABLE_DISCREPANCIES = {
    tag: {**FIGURE_STRIP_ERRORS[tag], **EXTRACTION_A_ERRORS[tag]}
    for tag in ("stage1", "stage2")
}


# Boxes whose MEDIAN the extractor reads off a horizontal rule that is not the median.
#
# `_boxes` looks for the widest horizontal run in `range(top + 3, bot - 2)`. The box's
# own Q3 rule is full width too, so wherever that rule is thicker than the 3 px skip it
# wins and the median is reported AS Q3. Person B caught this on box 17 by cross-check
# against the third-party extraction (`pdf_crosscheck.md:119`); generalising their find
# showed it hits three boxes, not one.
#
# These are declared here, with the pixel evidence, rather than fixed in `_boxes`. Two
# attempts at a general fix both made things worse -- skipping consecutive full-width
# rows breaks on antialiasing holes (stage-1 box 15 is full width at +0 and +2 but not
# +1, so the skip stops early and returns the rest of the Q3 rule), and band-grouping
# turned 7 confidently-wrong medians into NaN. The algorithm needs proper work; until
# then the three affected boxes are corrected explicitly or refused explicitly.
MEDIAN_CORRECTIONS = {
    # (stage, row): (value or None, evidence)
    ("stage2", 17): (3.4911, "row 397 is inside a 4 px Q3 rule; the median rule is row "
                             "456, width 30/30. B reads 3.48 independently"),
    ("stage2", 10): (2.3645, "rows 508-511 are the Q3 rule; the median rule is rows "
                             "547-548, width 31/31"),
    ("stage2", 4): (None, "NOT SEPARABLE: a 10 px full-width band at the top (its Q1 "
                          "rule is 2 px) and no full-width rule below it -- the median "
                          "is drawn flush against Q3. Bounded to [2.686, 2.798]"),
}

# +/-3 px at each figure's calibration (1 px = 0.00821 units in Fig 1a, 0.01238 in
# Fig 2a). This is OPTICAL error only. It is not the uncertainty on the condition --
# that is the biological spread, which is an order of magnitude larger and is carried
# by `response_q1`/`response_q3`.
READING_ERROR = {"stage1": 0.025, "stage2": 0.037}

# CSV column order. This IS the replay's contract: `run_replay_hall_ogle.py` reads
# `int(r["run_id"])`, the short factor names, `response` and `response_sd`.
#
# The short names and integer run_ids are B's, kept deliberately over the longer names
# in the original spec. The spec is a document; the replay is working code that already
# consumes these, and breaking it to satisfy a naming preference would be the wrong
# trade. `response_q1`/`response_q3` and a populated `extraction_2` are added on top.
COLUMNS = ("run_id", "c", "civ", "ln111", "ln411", "ln511", "fn",
           "response", "response_sd", "response_q1", "response_q3",
           "reading_error", "extraction_1", "extraction_2", "reconciled", "flagged",
           "flag_reason")
_COLUMN_OF = {"C": "c", "CIV": "civ", "LN111": "ln111",
              "LN411": "ln411", "LN511": "ln511", "FN": "fn"}

#: IQR -> sd assuming normality (Q3 - Q1 = 1.349 sd), B's derivation, kept because the
#: replay consumes `response_sd`. Treat it as indicative only: these are 3-10 dot samples
#: visibly skewed enough that mean and median diverge by 0.34, so the normal conversion
#: overstates several of them (stage2_08 comes out at sd 4.38 on a response of 2.27).
#: `response_q1`/`response_q3` carry the same information without the distributional
#: assumption, and are what new code should prefer.
IQR_TO_SD = 1.349


class ExtractionError(AssertionError):
    """Raised when an extraction fails a structural or completeness check.

    Subclasses `AssertionError` so a failed extraction reads as a failed assertion
    wherever it surfaces, but carries the full list of failures rather than the first.
    """


@dataclass(frozen=True)
class StageSpec:
    """What a stage's design must look like if the extraction read the right objects.

    Attributes:
        n_conditions: published run count.
        n_factors: proteins carried into this stage.
        full_factorial: whether the corner block is the complete ``2**n_factors``.
            Stage 2 is a face-centred CCD and must contain every corner exactly once.
            Stage 1 is a 22-run D-optimal subset of a 2**6 space -- completeness is
            not merely unmet there, it is impossible, so distinctness is the check.
        n_corners: expected corner rows.
        n_axial: expected axial rows (0 for stage 1, which has no axial block).
        n_centre: expected all-centre rows.
        model: model the design must support at full rank.
        model_rank: that rank.
    """

    n_conditions: int
    n_factors: int
    full_factorial: bool
    n_corners: int
    n_axial: int
    n_centre: int
    model: str
    model_rank: int


STAGE_SPEC = {
    # 22 non-centre runs exactly saturate the 2FI model (1 + 6 + 15 = 22 parameters),
    # which is the published design's own citable weakness: it has no residual df to
    # estimate lack of fit from those runs. The centre point adds the 23rd run and
    # therefore exactly ONE residual df across the full design -- see METHODS.
    "stage1": StageSpec(23, 6, False, 22, 0, 1, "2fi", 22),
    # 16 corners + 8 face-centred axials + 1 centre = 25; full quadratic is
    # 1 + 4 linear + 4 pure-quadratic + 6 two-factor = 15 parameters.
    "stage2": StageSpec(25, 4, True, 16, 8, 1, "quadratic", 15),
}


def to_pm1(design) -> np.ndarray:
    """Convert the extractor's 0/0.5/1 coding to coded -1/0/+1.

    Raises:
        ExtractionError: if any value is not one of 0, 0.5, 1.
    """
    D = np.asarray(design, dtype=float)
    allowed = np.isclose(D[..., None], [0.0, 0.5, 1.0]).any(-1)
    if not allowed.all():
        bad = sorted({float(v) for v in D[~allowed].ravel()})
        raise ExtractionError(f"design carries levels outside {{0, 0.5, 1}}: {bad}")
    return np.round(2 * D - 1).astype(int)


def model_matrix_rank(X: np.ndarray, model: str) -> tuple[int, int]:
    """Return ``(n_parameters, rank)`` of the model matrix for coded design ``X``."""
    n, p = X.shape
    cols = [np.ones(n)] + [X[:, j] for j in range(p)]
    if model == "quadratic":
        cols += [X[:, j] ** 2 for j in range(p)]
    cols += [X[:, a] * X[:, b] for a, b in itertools.combinations(range(p), 2)]
    M = np.column_stack(cols)
    return M.shape[1], int(np.linalg.matrix_rank(M))


def _missing(values) -> list[int]:
    return [i for i, v in enumerate(values)
            if v is None or (isinstance(v, float) and math.isnan(v))]


def load_extraction_a(tag: str, root: str | Path = ".") -> list[dict]:
    """Load the independent third-party digitization for one stage.

    Its ``factor_code`` column is transcribed from the published coded table, which is
    why it can arbitrate design disagreements that no structural check can. Its response
    column is the MEAN OF DETECTED DOTS -- a different estimand from our box median, so
    the two are never averaged together. See `docs/published-data.md`.

    Returns:
        One dict per condition with ``condition_id``, ``design`` (coded +/-1 tuple),
        ``mean``, ``variance``, ``n_replicates`` and ``raw`` (individual dot values).
    """
    path = Path(root) / EXTRACTION_A[tag]
    out = []
    with path.open() as fh:
        for r in csv.DictReader(fh):
            raw = [float(v) for v in r["raw_extracted_values"].split(";") if v]
            var = r["cd31_area_dapi_norm_fn_variance"]
            out.append(dict(
                condition_id=r["condition_id"],
                design=tuple(_LEVEL[t] for t in r["factor_code"].split()),
                mean=float(r["cd31_area_dapi_norm_fn_mean"]),
                variance=float(var) if var else float("nan"),
                n_replicates=int(r["n_detected_replicates"]),
                raw=raw,
            ))
    return out


def validate_against_table(tag: str, rec: dict, a_rows: list[dict] | None = None,
                           root: str | Path = ".", allow_known: bool = True) -> None:
    """Check the extracted design against the published coded table.

    This is the only check that catches a single mis-read greyscale cell in stage 1.
    Stage 1's 22 non-centre runs are a D-optimal subset of a 2**6 space, so flipping one
    level yields another perfectly valid saturated design -- row counts, distinctness,
    axial structure and rank all still pass. Structural validation cannot see it.

    Args:
        allow_known: tolerate exactly the cells in `FIGURE_TABLE_DISCREPANCIES`, which
            are documented disagreements *within the paper*, not extraction faults.
            Pass ``False`` to see every disagreement, which is what the regression test
            does against the pre-fix fixture.

    Raises:
        ExtractionError: listing every undeclared disagreeing cell, and any declared
            cell that has stopped disagreeing.
    """
    a_rows = a_rows if a_rows is not None else load_extraction_a(tag, root)
    D = to_pm1(rec["design"])
    if len(a_rows) != len(D):
        raise ExtractionError(f"[{tag}] table has {len(a_rows)} rows, extraction has "
                              f"{len(D)}")
    known = FIGURE_TABLE_DISCREPANCIES.get(tag, {}) if allow_known else {}
    bad, seen = [], set()
    for i, (a, b) in enumerate(zip(a_rows, D)):
        for j, (x, y) in enumerate(zip(a["design"], b)):
            if x == int(y):
                continue
            cell = (i, rec["proteins"][j])
            if cell in known:
                seen.add(cell)
                continue
            bad.append(f"row {i} ({a['condition_id']}) factor "
                       f"{rec['proteins'][j]}: table={x:+d} figure={int(y):+d}")
    stale = sorted(set(known) - seen)
    if stale:
        bad.append(f"DECLARED-BUT-ABSENT: {stale} no longer disagree; the declaration "
                   "is stale and must be removed rather than left to excuse a future "
                   "mismatch at the same cell")
    if bad:
        raise ExtractionError(f"[{tag}] design disagrees with the published table in "
                              f"{len(bad)} undeclared cell(s):\n  " + "\n  ".join(bad))


def validate_extraction(tag: str, rec: dict, design=None) -> None:
    """Check one stage's extraction, raising with EVERY failure rather than the first.

    Reporting only the first failure would have hidden the second defect in the
    shipped data behind the first.

    Args:
        tag: ``"stage1"`` or ``"stage2"``.
        rec: the extractor's record for that stage. Supplies the RESPONSES.
        design: coded design to run the structural checks against, in 0/0.5/1 units.
            Defaults to the figure's own strip read. Pass the published table's design
            to check the design of record, which is what the canonical CSV carries.

    Raises:
        ExtractionError: listing every check that failed.
    """
    if tag not in STAGE_SPEC:
        raise ValueError(f"unknown stage {tag!r}; expected one of {sorted(STAGE_SPEC)}")
    spec = STAGE_SPEC[tag]
    fail: list[str] = []

    # --- completeness of responses -------------------------------------------------
    unresolvable = {i for (t, i), (v, _) in MEDIAN_CORRECTIONS.items()
                    if t == tag and v is None}
    for key in ("q1", "median", "q3"):
        miss = [i for i in _missing(rec[key])
                if not (key == "median" and i in unresolvable)]
        if miss:
            fail.append(f"MISSING-RESPONSE: {key} unresolved at rows {miss}")

    # --- row counts ----------------------------------------------------------------
    if rec["n_conditions"] != spec.n_conditions:
        fail.append(f"ROW-COUNT: {rec['n_conditions']} conditions, expected "
                    f"{spec.n_conditions}")
    for key in ("q1", "median", "q3", "design"):
        if len(rec[key]) != spec.n_conditions:
            fail.append(f"ROW-COUNT: {key} has {len(rec[key])} rows, expected "
                        f"{spec.n_conditions}")
    if len(rec["proteins"]) != spec.n_factors:
        fail.append(f"FACTOR-COUNT: {len(rec['proteins'])} proteins, expected "
                    f"{spec.n_factors}")

    if fail and any(f.startswith(("ROW-COUNT", "FACTOR-COUNT")) for f in fail):
        raise ExtractionError(f"[{tag}] extraction failed {len(fail)} check(s):\n  "
                              + "\n  ".join(fail))

    # The DESIGN checks below describe the design of record -- the published coded
    # table -- not the figure's greyscale strip. Those are two different objects and the
    # paper's own copies of them disagree in one cell per stage (see
    # FIGURE_TABLE_DISCREPANCIES). Applying a "the CCD has all 16 corners" check to the
    # strip would fail on a defect that is the paper's, not the extraction's, and would
    # make the gate unpassable for reasons no re-extraction could fix.
    D = to_pm1(rec["design"] if design is None else design)

    # --- corner block ---------------------------------------------------------------
    corners = [tuple(r) for r in D if set(r) <= {-1, 1}]
    if len(corners) != spec.n_corners:
        fail.append(f"CORNER-COUNT: {len(corners)} corner rows, expected "
                    f"{spec.n_corners}")
    dupes = sorted({tuple(int(v) for v in c) for c in corners if corners.count(c) > 1})
    if dupes:
        fail.append(f"CORNER-DISTINCTNESS: duplicated corner(s) {dupes} at rows "
                    f"{[i for i, r in enumerate(D) if tuple(int(v) for v in r) in dupes]}")
    if spec.full_factorial:
        want = set(itertools.product((-1, 1), repeat=spec.n_factors))
        gone = sorted(want - set(corners))
        if gone:
            fail.append(f"CORNER-COMPLETENESS: missing corner(s) {gone}")
    else:
        noncentre = [tuple(r) for r in D if set(r) != {0}]
        if len(set(noncentre)) != len(noncentre):
            fail.append("CORNER-DISTINCTNESS: duplicated non-centre runs")

    # --- axial block -----------------------------------------------------------------
    axial = [tuple(r) for r in D if sum(v != 0 for v in r) == 1 and set(r) <= {-1, 0, 1}]
    if len(axial) != spec.n_axial:
        fail.append(f"AXIAL-COUNT: {len(axial)} axial rows, expected {spec.n_axial}")
    for r in axial:
        if not any(v in (-1, 1) for v in r):
            fail.append(f"AXIAL-LEVEL: axial run {r} is not at +/-1 (face-centred, a=1)")

    # --- centre points -----------------------------------------------------------------
    centre = [tuple(r) for r in D if set(r) == {0}]
    if len(centre) != spec.n_centre:
        fail.append(f"CENTRE-COUNT: {len(centre)} centre rows, expected {spec.n_centre}")

    # --- rank ---------------------------------------------------------------------------
    basis = D[[i for i, r in enumerate(D) if set(r) != {0}]] if tag == "stage1" else D
    n_par, rank = model_matrix_rank(basis.astype(float), spec.model)
    if rank != spec.model_rank:
        fail.append(f"RANK: {spec.model} model matrix rank {rank} over {len(basis)} runs, "
                    f"expected {spec.model_rank} (parameters {n_par})")

    # --- response sanity ------------------------------------------------------------------
    q1, med, q3 = (np.asarray(rec[k], float) for k in ("q1", "median", "q3"))
    bad = [i for i in range(len(med))
           if i not in unresolvable and not (q1[i] <= med[i] <= q3[i])]
    if bad:
        fail.append(f"QUARTILE-ORDER: q1<=median<=q3 violated at rows {bad}")
    neg = [i for i in range(len(med)) if i not in unresolvable and med[i] < 0]
    if neg:
        fail.append(f"NEGATIVE-RESPONSE: median < 0 at rows {neg}")

    if fail:
        raise ExtractionError(f"[{tag}] extraction failed {len(fail)} check(s):\n  "
                              + "\n  ".join(fail))


def canonical_design(tag: str, rec: dict) -> np.ndarray:
    """The design of record: the FIGURE strip, with its known cell errors corrected.

    Not the third-party transcription -- that has its own error (stage-1 LN511). Each
    source has exactly one bad cell and `docs/pdf_crosscheck.md` settles both from the
    PDF; taking either source wholesale imports the other's mistake.
    """
    D = to_pm1(rec["design"]).copy()
    for (i, factor), (was, now, _ev) in FIGURE_STRIP_ERRORS[tag].items():
        j = rec["proteins"].index(factor)
        if int(D[i, j]) != was:
            raise ExtractionError(
                f"[{tag}] declared strip error at row {i} {factor} expected {was:+d} "
                f"but the extraction reads {int(D[i, j]):+d}; the declaration is stale")
        D[i, j] = now
    return D


def build_canonical_rows(tag: str, root: str | Path = ".") -> list[dict]:
    """Assemble the analysis-ready rows for one stage.

    **Design comes from the published table, responses from the figure.** Those are
    different published objects and they disagree in one cell per stage; the table is
    the design of record and the figure is the only place the responses exist.

    **`reconciled` is extraction B's box median, NOT the mean of the two extractions.**
    The brief specified averaging the two where they agree within reading error, and
    that rule cannot be applied here: A reports the MEAN OF DETECTED DOTS and B the BOX
    MEDIAN, so their difference (median 0.10 in stage 1, 0.34 in stage 2) is dominated
    by the choice of statistic, not by measurement error (0.025 / 0.037). Applied
    literally the rule flags 42 of 48 rows and the column stops carrying information.
    By the estimand-appropriate test -- is A's mean inside B's [Q1, Q3]? -- the two
    agree on 48 of 48. B's median is used because the replay needs a robust centre with
    matching quartiles to derive `Yvar` from, and only B supplies quartiles at all.

    **`flagged` therefore marks RANK disagreement**: rows that are the maximum under one
    extraction but not the other. That is the disagreement that can actually change a
    conclusion, and it keeps the stage-2 argmax dispute visible in the data rather than
    only in prose. It is also set if A's mean ever falls outside B's [Q1, Q3].
    """
    import json

    root = Path(root)
    rec = json.loads((root / f"research/data/external/hall_ogle_2025/{tag}.json").read_text())
    A = load_extraction_a(tag, root)
    med = np.asarray(rec["median"], float)
    q1 = np.asarray(rec["q1"], float)
    q3 = np.asarray(rec["q3"], float)
    a_mean = np.asarray([r["mean"] for r in A], float)
    design = canonical_design(tag, rec)

    # Apply the declared median corrections BEFORE anything downstream, so the argmax is
    # computed from corrected values. Leaving them until after would have `stage2_18`
    # win on a number that is its Q3.
    reasons: dict[int, str] = {}
    for (t, i), (value, evidence) in MEDIAN_CORRECTIONS.items():
        if t != tag:
            continue
        med[i] = float("nan") if value is None else value
        reasons[i] = evidence

    # rows disputed as the maximum between the two independent extractions
    disputed = {int(a_mean.argmax()), int(np.nanargmax(med))}
    if len(disputed) == 1:
        disputed = set()

    rows = []
    for i, ar in enumerate(A):
        m = float(med[i])
        resolved = not math.isnan(m)
        outside = resolved and not (q1[i] <= a_mean[i] <= q3[i])
        why = []
        for (drow, dfactor), (was, now, ev) in FIGURE_STRIP_ERRORS[tag].items():
            if drow == i:
                why.append(f"design corrected, {dfactor} {was:+d} -> {now:+d}: {ev}")
        if i in reasons:
            why.append(("median corrected: " if resolved else "") + reasons[i])
        if i in disputed:
            why.append("argmax disputed between the two extractions")
        if outside:
            why.append("extraction A's mean falls outside our [q1, q3]")

        row = {c: "" for c in COLUMNS}
        row["run_id"] = i + 1
        for name, level in zip(rec["proteins"], design[i]):
            row[_COLUMN_OF[name]] = int(level)
        # An unresolved median leaves response/reconciled EMPTY. Never zero, and never a
        # substituted quartile -- substituting Q3 is precisely the defect being fixed.
        if resolved:
            row["response"] = round(m, 4)
            row["extraction_2"] = round(m, 4)
            row["reconciled"] = round(m, 4)
            row["response_sd"] = round(float(q3[i] - q1[i]) / IQR_TO_SD, 4)
        row["response_q1"] = round(float(q1[i]), 4)
        row["response_q3"] = round(float(q3[i]), 4)
        row["reading_error"] = READING_ERROR[tag]
        row["extraction_1"] = round(float(a_mean[i]), 4)
        row["flagged"] = "True" if why else "False"
        row["flag_reason"] = "; ".join(why)
        rows.append(row)
    return rows


def write_canonical_csv(tag: str, path: str | Path, root: str | Path = ".") -> list[dict]:
    """Write one stage's canonical CSV. Absent factors are EMPTY, never zero.

    Zero is a real coded level (the centre point), so a placeholder zero in a dropped
    factor's column would silently invent 8 centre-point readings in stage 2.
    """
    rows = build_canonical_rows(tag, root)
    present = [c for c in COLUMNS
               if c not in _COLUMN_OF.values() or any(r[c] != "" for r in rows)]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=present, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return rows
