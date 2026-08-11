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

------------------------------------------------------------------------------
MERGED, AND WHAT CHANGED
------------------------------------------------------------------------------

The row-building logic now lives in `boec.published` so that ONE function writes these
files. Two builders claiming the same path is how a schema drifts.

Corrections to the notes above, from merging the two parallel builds:

* **The second extraction was not lost.** It is at `data/external/extraction_a/`,
  recovered from `/Users/jy/BO/` -- outside the repo, which is why
  `git log --diff-filter=A` found nothing. `extraction_2` is now populated 47/48 and the
  agreement statistics are recomputed rather than quoted.
* **stage1_23 LN511 stays as it is, and the note above is right.** An attempt to "fix"
  it to `-1` from the third-party transcription was wrong: the paper prints
  `+ + + + + -` (pdf_crosscheck.md:129). The transcription has the error, not us.
* **Two more medians read the Q3 rule, not just stage2_18.** The same defect hits
  stage2_11 (corrected to 2.3645) and stage2_05 (refused -- its median has merged with
  Q3 and is only bounded, to [2.686, 2.798]).
* **stage2_03 is extractable** (0.7056), so `test_the_fibronectin_control...` needs its
  premise revisited: the FN-only control is the ALL-LOW row, `stage2_25` (1.0275), not
  the FN-high row. Every other protein's low level is 0 ug/mL while fibronectin's is 22,
  so both rows are "fibronectin only" and only the all-low one reads ~1.0 -- in both
  stages (stage1_01 = 0.9692).
* **`reading_error` is optical**, 0.025 / 0.037. The 7%-of-spread figure was propagated
  from a doc that never defined "spread"; its percentages only reconcile against the
  standard deviation of the medians, not their range.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))      # runnable without PYTHONPATH, as the
                                           # round-trip test invokes it bare
from boec.published import write_canonical_csv  # noqa: E402


def main() -> None:
    for stage in ("stage1", "stage2"):
        path = ROOT / "data" / "published" / f"hall_ogle_2025_{stage}.csv"
        rows = write_canonical_csv(stage, path, ROOT)
        flagged = [r["run_id"] for r in rows if r["flagged"] == "True"]
        missing = [r["run_id"] for r in rows if r["response"] == ""]
        print(f"{path.relative_to(ROOT)}: {len(rows)} rows, {len(rows[0])} columns, "
              f"flagged {flagged or 'none'}, no response {missing or 'none'}")
        scored = [(r["run_id"], float(r["response"])) for r in rows if r["response"] != ""]
        top = sorted(scored, key=lambda t: -t[1])[:5]
        print(f"    top-5 by response: {[t[0] for t in top]} "
              f"{[round(t[1], 3) for t in top]}")


if __name__ == "__main__":
    main()
