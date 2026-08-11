"""Stages 1-3 of the Hall/Ogle digitization plan: raw JSON -> canonical CSVs.

    python scripts/build_published_dataset.py

Produces `data/published/hall_ogle_2025_stage{1,2}.csv`, the analysis-ready dataset
`LookupEvaluator` consumes. Deterministic: same inputs, same bytes out, so the
round-trip test in `tests/test_published_dataset.py` is meaningful.

------------------------------------------------------------------------------
WHAT SURVIVED, AND WHAT DID NOT
------------------------------------------------------------------------------

**There is only ONE extraction.** `VALIDATION_REPORT.md` inventories the digitizer's
five CSVs, and none of them are in the repository or on disk: they were never committed
(`git log --diff-filter=A` returns nothing) and commit `e28c84c`, "Rescue A's
digitization work before deleting the old working folder", saved only the two JSONs, the
rasters and the two markdown documents. **The second extraction died with that folder.**

So the plan's Stage 2, "reconcile the two extractions", cannot be performed as written.
What survives of the second extraction is its *summary statistics*, quoted inside
`VALIDATION_REPORT.md`: Spearman 0.860 (stage 2) and 0.880 (stage 1), top-5 overlap 3/5
at both stages, 47/47 conditions inside the other's IQR, fibronectin control 0.966 vs
0.969, and two named values. Those are carried as a stated limitation rather than
reconstructed, and the `extraction_2` column is written empty rather than invented.

------------------------------------------------------------------------------
CORRECTIONS APPLIED, EACH WITH ITS EVIDENCE
------------------------------------------------------------------------------

Every correction is declared in `CORRECTIONS` below and stamped into the `flagged`
column. A corrected cell that looks identical to an uncorrected one is unauditable.

1. **stage2_21 fibronectin, coded level low -> high.** Table 2 row 21 prints `- + + +`
   (`docs/pdf_crosscheck.md:130`). The JSON has 0.0. Corrected to +1.

2. **stage2_18 median 4.221 -> 3.48.** `docs/pdf_crosscheck.md:119` finds our value
   corresponds to that column's **Q3**, not its median. The JSON corroborates it
   independently: the stored triple is q1 1.634, median 4.221, q3 4.259 — a median
   sitting 0.04 below Q3 while 2.59 above Q1 is a mis-detected median line, not a
   skewed distribution.

   **This is the correction that dissolves B1.** With it applied the stage-2 argmax
   moves from condition 18 to condition 13, which is what the other extraction reported.
   The two extractions agree. **That does not reinstate an argmax claim** — Q31 §1
   registered the argmax as unsupportable on grounds this correction cannot touch: the
   top five IQRs share a common band, and the paper never names a best condition.

**NOT corrected: stage1_23 laminin 511.** `VALIDATION_REPORT.md` lists it as disputed,
but the JSON already holds 1.0, matching the printed `+ + + + + -` of Table 1 row 23
(`pdf_crosscheck.md:129`). The dispute was with the lost CSV, and our surviving value is
the right one. Recorded so nobody "fixes" a correct cell.

------------------------------------------------------------------------------
CODED SPACE ONLY
------------------------------------------------------------------------------

The JSONs store levels as 0.0 / 0.5 / 1.0; the canonical CSVs use -1 / 0 / +1. **No
physical-unit column is emitted at any point** (B3). Everything in the project runs in
coded space precisely so that nothing depends on the Collagen IV concentration the source
paper contradicts itself about — the PDF cross-check settles it at 28 ug/mL, and the
pipeline still does not use it.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "external" / "hall_ogle_2025"
OUT = ROOT / "data" / "published"

#: IQR -> sd for a normal distribution. Q3 - Q1 = 1.349 sd.
IQR_TO_SD = 1.349

#: Reading error, in response units, from EXTRACTION_METHOD/VALIDATION_REPORT: 4-7% of
#: the between-condition spread. The upper end is used — the conservative choice.
READING_ERROR_FRAC = 0.07

#: (stage, 1-indexed condition, field, new value, evidence). See module docstring.
CORRECTIONS = [
    ("stage2", 21, "design.FN", 1.0, "Table 2 row 21 prints '- + + +'; pdf_crosscheck.md:130"),
    ("stage2", 18, "median", 3.48, "our 4.22 is the column's Q3 not its median; pdf_crosscheck.md:119"),
]


def _coded(v: float) -> int:
    """0.0 / 0.5 / 1.0 -> -1 / 0 / +1. Raises on anything else."""
    lookup = {0.0: -1, 0.5: 0, 1.0: 1}
    if v not in lookup:
        raise ValueError(f"design level {v!r} is not one of {sorted(lookup)}")
    return lookup[v]


def build(stage: str) -> list[dict]:
    d = json.loads((RAW / f"{stage}.json").read_text())
    proteins: list[str] = d["proteins"]
    design = [list(map(float, row)) for row in d["design"]]
    q1 = np.array(d["q1"], dtype=float)
    med = np.array(d["median"], dtype=float)
    q3 = np.array(d["q3"], dtype=float)

    applied: dict[int, list[str]] = {}
    for st, cond, field, value, why in CORRECTIONS:
        if st != stage:
            continue
        i = cond - 1
        if field == "median":
            med[i] = value
        elif field.startswith("design."):
            design[i][proteins.index(field.split(".", 1)[1])] = value
        else:
            raise ValueError(f"unknown correction field {field!r}")
        applied.setdefault(i, []).append(why)

    spread = float(np.nanmax(med) - np.nanmin(med))
    reading_error = round(READING_ERROR_FRAC * spread, 4)

    rows = []
    for i in range(d["n_conditions"]):
        value = med[i]
        sd = (q3[i] - q1[i]) / IQR_TO_SD
        row = {"run_id": i + 1}
        for j, p in enumerate(proteins):
            row[p.lower()] = _coded(design[i][j])
        row["response"] = "" if np.isnan(value) else round(float(value), 4)
        row["response_sd"] = "" if np.isnan(sd) else round(float(sd), 4)
        row["reading_error"] = reading_error
        # Only one extraction survives; extraction_2 is written empty, never invented.
        row["extraction_1"] = "" if np.isnan(med[i]) else round(float(med[i]), 4)
        row["extraction_2"] = ""
        row["reconciled"] = row["response"]
        row["flagged"] = bool(i in applied or np.isnan(value))
        row["flag_reason"] = "; ".join(applied.get(i, [])) or ("median not extractable" if np.isnan(value) else "")
        rows.append(row)
    return rows


def write(stage: str, rows: list[dict]) -> Path:
    path = OUT / f"hall_ogle_2025_{stage}.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def main() -> None:
    for stage in ("stage1", "stage2"):
        rows = build(stage)
        path = write(stage, rows)
        flagged = [r["run_id"] for r in rows if r["flagged"]]
        missing = [r["run_id"] for r in rows if r["response"] == ""]
        print(f"{path.relative_to(ROOT)}: {len(rows)} rows, "
              f"{len(rows[0]) } columns, flagged {flagged or 'none'}, "
              f"no response {missing or 'none'}")

        med = np.array([r["response"] for r in rows if r["response"] != ""], dtype=float)
        ids = [r["run_id"] for r in rows if r["response"] != ""]
        order = np.argsort(med)[::-1][:5]
        print(f"    top-5 by response: {[ids[i] for i in order]} "
              f"{[round(float(med[i]), 3) for i in order]}")


if __name__ == "__main__":
    main()
