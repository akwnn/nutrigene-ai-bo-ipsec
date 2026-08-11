"""Digitize Hall, Lin & Ogle 2025 (Sci Rep 15:24479) Figures 1a and 2a.

Both panels are box-and-whisker plots with the coded design shown as a grey-scale
circle matrix beneath (legend: black=1, grey=0.5, light=0). Digitizing them yields the
full (design matrix, response) pair for all 48 published conditions without needing the
underlying data from the authors.

Note the panels are NOT bar charts, as the project documents assumed. They show
dispersion — box, whiskers and individual points — which is the only source-derived
handle on assay variability in the paper, since no CV is reported anywhere.

Extraction method, stated for the paper's methods section:
  * y-axis calibrated from the tick marks left of the axis spine (px per data unit).
  * A box is located by finding a PAIR of vertical ink runs ~one box-width apart whose
    extents match; those give Q3 (top) and Q1 (bottom). Taking the single longest
    vertical run instead finds the WHISKER and silently misreads the box — the first
    version of this script did exactly that.
  * The median is the widest horizontal ink run strictly inside the box.
  * Coded levels are read as mean grey value in a patch centred on each circle.

Known limitations: the published Figure 1 caption contains a leftover note to the
editor stating the figures are low resolution ("figure #1 is especially low"), and
Figure 1a carries an unreplaced "Y axis label" placeholder. Reading error is roughly
one pixel, i.e. ~0.01 response units in Fig 2a and ~0.008 in Fig 1a — negligible
against the biological spread, which is the dominant uncertainty.

Usage::  python scripts/digitize_hall_ogle.py --fig1 fig1.png --fig2 fig2.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from boec.published import (
    canonical_design,
    load_extraction_a,
    validate_against_table,
    validate_extraction,
)

STAGE1_PROTEINS = ("C", "CIV", "LN111", "LN411", "LN511", "FN")
STAGE2_PROTEINS = ("C", "CIV", "LN411", "FN")


def _ink(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")).astype(float)


def _calibrate(gray: np.ndarray, col_thresh: int, row_thresh: int, ymax: int):
    """Return (axis_x, baseline_y, px_per_unit) from the axis spine and its ticks."""
    ink = gray < 128
    ax = int(np.where(ink[:ymax].sum(0) > col_thresh)[0][0])
    base = int(np.where(ink[:ymax].sum(1) > row_thresh)[0][-1])
    rows = np.where(ink[: base + 2, ax - 10 : ax].sum(1) >= 4)[0]
    groups, cur = [], [rows[0]]
    for v in rows[1:]:
        if v - cur[-1] <= 3:
            cur.append(v)
        else:
            groups.append(int(np.mean(cur)))
            cur = [v]
    groups.append(int(np.mean(cur)))
    return ax, base, (groups[-1] - groups[0]) / (len(groups) - 1), len(groups) - 1


def _longest_run(col: np.ndarray):
    idx = np.where(col)[0]
    if len(idx) == 0:
        return None
    segs = np.split(idx, np.where(np.diff(idx) > 2)[0] + 1)
    s = max(segs, key=len)
    return int(s[0]), int(s[-1]), len(s)


def _box_columns(sub: np.ndarray, lo: int, hi: int, gap: int) -> list[float]:
    runs = []
    for r in range(sub.shape[0]):
        row = sub[r]
        d = np.diff(row.astype(int))
        starts = list(np.where(d == 1)[0] + 1)
        ends = list(np.where(d == -1)[0] + 1)
        if row[0]:
            starts = [0] + starts
        if row[-1]:
            ends = ends + [len(row)]
        for a, b in zip(starts, ends):
            if lo <= b - a <= hi:
                runs.append((a + b) / 2)
    runs = np.sort(np.array(runs))
    out, cur = [], [runs[0]]
    for v in runs[1:]:
        if v - cur[-1] <= gap:
            cur.append(v)
        else:
            out.append(float(np.mean(cur)))
            cur = [v]
    out.append(float(np.mean(cur)))
    return out


def _boxes(sub: np.ndarray, centres, base: int, ppu: float, wlo: int, whi: int,
           tol: int = 4):
    """Extract (q1, median, q3) per box using the PAIRED vertical edges.

    ``tol`` is how far the two edges' pixel extents may differ and still be accepted as
    a pair. It exists because a data dot drawn over a box edge merges with it, clipping
    or extending that edge's run.

    **Why 4 and not 3.** The original 3 lost stage-2 box 2 entirely: its left edge spans
    rows 653-700 and its right edge 657-700, a 4 px disagreement at the top caused by a
    dot sitting on the corner. One pixel is 0.0124 response units here, so 3 vs 4 px is
    a 0.012-unit distinction with no rendering justification behind either. The value is
    not tuned to recover that box: the SAME edge pair, and therefore identical q1/q3, is
    found at every tolerance from 4 to 10, and no other box in either figure changes at
    any of them. Robustness across the range is the argument; 4 is simply its floor.
    """
    rows = []
    for xc in centres:
        best = None
        for c1 in range(int(xc) - 26, int(xc) + 27):
            if not (0 <= c1 < sub.shape[1]):
                continue
            r1 = _longest_run(sub[:, c1])
            if not r1 or r1[2] < 8:
                continue
            for c2 in range(c1 + wlo, min(c1 + whi, sub.shape[1])):
                r2 = _longest_run(sub[:, c2])
                if not r2 or r2[2] < 8:
                    continue
                if abs(r1[0] - r2[0]) <= tol and abs(r1[1] - r2[1]) <= tol:
                    h = min(r1[1], r2[1]) - max(r1[0], r2[0])
                    if best is None or h > best[0]:
                        best = (h, max(r1[0], r2[0]), min(r1[1], r2[1]), c1, c2)
        if best is None:
            rows.append((np.nan, np.nan, np.nan))
            continue
        _, top, bot, c1, c2 = best
        med, blen = None, 0
        for r in range(top + 3, bot - 2):
            s = sub[r, c1 : c2 + 1].sum()
            if s > blen:
                blen, med = s, r
        val = lambda p: (base - p) / ppu  # noqa: E731
        rows.append((val(bot), val(med) if med else np.nan, val(top)))
    return np.array(rows)


def _design(gray: np.ndarray, ax: int, base: int, centres, n_rows: int):
    band = gray[base + 10 : base + 340, :]
    dk = (band < 200).sum(1)
    rr = np.where(dk > 200)[0]
    groups, cur = [], [rr[0]]
    for v in rr[1:]:
        if v - cur[-1] <= 6:
            cur.append(v)
        else:
            groups.append(int(np.mean(cur)) + base + 10)
            cur = [v]
    groups.append(int(np.mean(cur)) + base + 10)
    out = []
    for ry in groups[:n_rows]:
        v = np.array(
            [gray[ry - 8 : ry + 9, int(ax + 2 + x) - 8 : int(ax + 2 + x) + 9].mean()
             for x in centres]
        )
        out.append(np.where(v < 110, 1.0, np.where(v < 205, 0.5, 0.0)))
    return np.column_stack(out)


def extract(path: str, proteins, col_t, row_t, ymax, wlo, whi, gap, rlo, rhi, tol=4):
    gray = _ink(path)
    ax, base, ppu, nticks = _calibrate(gray, col_t, row_t, ymax)
    sub = (gray < 128)[: base + 2, ax + 2 :]
    centres = _box_columns(sub, rlo, rhi, gap)
    boxes = _boxes(sub, centres, base, ppu, wlo, whi, tol)
    design = _design(gray, ax, base, centres, len(proteins))
    return dict(
        axis_x=ax, baseline_y=base, px_per_unit=round(ppu, 3), y_max=nticks,
        n_conditions=len(centres), proteins=list(proteins),
        design=design.tolist(),
        q1=boxes[:, 0].tolist(), median=boxes[:, 1].tolist(), q3=boxes[:, 2].tolist(),
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fig1", required=True)
    p.add_argument("--fig2", required=True)
    p.add_argument("--out", default="data/external/hall_ogle_2025")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    s1 = extract(a.fig1, STAGE1_PROTEINS, 350, 900, 800, 24, 46, 14, 24, 44)
    s2 = extract(a.fig2, STAGE2_PROTEINS, 500, 900, 760, 29, 37, 12, 27, 38)
    for tag, rec, expect in (("stage1", s1, 23), ("stage2", s2, 25)):
        d = np.array(rec["design"])
        rec["source"] = "https://www.nature.com/articles/s41598-025-09256-9"
        rec["figure"] = "1a" if tag == "stage1" else "2a"
        rec["readout"] = "CD31 area / DAPI area, normalized to the FN control, day 10"
        rec["design_check"] = {
            "factorial_rows": int((d != 0.5).all(1).sum()),
            "axial_rows": int(((d == 0.5).sum(1) == d.shape[1] - 1).sum()),
            "centre_rows": int((d == 0.5).all(1).sum()),
        }
        # HARD GATE. Counting row types -- which is all `design_check` above does --
        # passed the two defects that shipped: a duplicated corner and an unresolved
        # box. Nothing is written unless the responses are complete AND the design of
        # record is structurally sound AND the figure agrees with the published table
        # everywhere bar the declared, evidenced discrepancies.
        a_rows = load_extraction_a(tag)
        # Structural checks run on the DESIGN OF RECORD -- the strip with its one known
        # cell error corrected -- not on the raw strip and not on the transcription.
        validate_extraction(tag, rec,
                            design=(canonical_design(tag, rec) + 1) / 2)
        validate_against_table(tag, rec, a_rows)
        (out / f"{tag}.json").write_text(json.dumps(rec, indent=1))
        ok = rec["n_conditions"] == expect
        print(f"{tag}: {rec['n_conditions']} conditions (expect {expect}) {'OK' if ok else 'MISMATCH'}"
              f" | {rec['px_per_unit']} px/unit | design {rec['design_check']}"
              f" | medians recovered {int(np.isfinite(rec['median']).sum())}"
              f" | validated")
    print(f"written to {out}/")


if __name__ == "__main__":
    main()
