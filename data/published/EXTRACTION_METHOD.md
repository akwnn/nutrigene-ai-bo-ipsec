# Extraction method — Hall/Ogle 2025 Figures 1a and 2a

Provenance for two independent digitizations of the same figures. Both are recorded
because the disagreement between them is the main validation evidence, and because the
paper's methods section needs a real provenance statement rather than an inferred one.

**Source.** Hall, Lin & Ogle 2025, *Scientific Reports* 15:24479, open access (CC-BY).
`https://www.nature.com/articles/s41598-025-09256-9`

**Readout.** CD31 area ÷ DAPI area, normalized to the fibronectin-only control, at day 10
of differentiation, from ≥4 wells across ≥3 experimental replicates per condition.

**Why digitization was necessary.** The per-condition values are not printed anywhere.
Tables 1 and 2 are purely coded (−/0/+) with no concentration values and no responses;
the supplementary file contains only figure legends; no erratum exists. The values exist
only as marks on the Figure 1a and 2a box plots.

**Correction to the project record:** Figures 1a and 2a are **box-and-whisker plots with
individual points overlaid**, not bar charts as the project documents state. This matters —
they are the only source of dispersion information in the paper.

**Published caveat, verified verbatim from the live article.** The Figure 1 caption
contains an unremoved note to the editor: *"The resolution of all figures is low, but
figure #1 is especially low. We have attached th[e high resolution figure 1 here]."*
Figure 1 panel b additionally carries an unreplaced "Y axis label" placeholder in the
rendered image. A high-resolution Figure 1 therefore exists and can be requested from the
corresponding author.

---

## Extraction A — third-party (supplied)

Recorded from `EXTRACTION_NOTES.md` as supplied by the digitizer. Not independently
reproducible from this repository; the code was not provided.

- **Source image:** figure images pulled from the article PDF at native 300 DPI.
- **Calibration:** y-axis tick marks located pixel-by-pixel to build a linear
  pixel→value mapping.
- **Target:** individual data points. Morphological erosion on the binarised image to
  strip thin box edges and whisker lines while preserving thicker filled dots, then
  connected-component labelling for dot centres.
- **Keying:** dot x-positions clustered into columns, cluster count confirmed against the
  design table row count (23 / 25) before use; columns matched to table rows as
  *left-to-right in figure = top-to-bottom in table*.
- **Outputs:** per-condition mean, sample variance (`ddof=1`), detected replicate count,
  and the raw individual values.
- **Digitizer's own stated limitations:** replicate undercount is likely, because dots
  overlapping a box edge or whisker are eroded away with the line; `n_detected_replicates`
  is a floor. Precision degrades sharply for Figures 4 and 5, which were read visually
  (±0.2–0.3 CD31 units) rather than pixel-detected.

**Not reproducible from the record:** the erosion kernel and thresholds, the clustering
tolerance, and the exact tick rows used for calibration were not supplied. Re-running
this extraction would not be guaranteed to reproduce these numbers.

---

## Extraction B — this repository (independent)

Fully reproducible: `scripts/digitize_hall_ogle.py`, raw inputs preserved at
`data/external/hall_ogle_2025/fig{1,2}_raw.png`.

- **Source image:** Springer Nature static PNGs — Fig 1 1654×2258, Fig 2 1800×1596.
  A different source from Extraction A, which is what makes the two independent.
- **Calibration:** axis spine located as the longest vertical ink column; tick rows as
  short horizontal ink runs immediately left of it. Fig 1: 121.75 px per response unit
  (ticks 0–4). Fig 2: 80.78 px per unit (ticks 0–9).
- **Target:** box statistics, not dots. A box is located by finding a **pair** of vertical
  ink runs one box-width apart whose extents match; those give Q3 and Q1. The median is
  the widest horizontal ink run strictly inside the box.
  - *Failure mode found and fixed during development:* taking the single longest vertical
    run instead finds the **whisker**, not the box edge, and silently misreads Q1/Q3/median.
    The first version of this script did exactly that and reported box 2's median as 7.27
    instead of 1.30.
- **Keying:** none required. The coded design is read directly from the grey-scale circle
  matrix printed beneath each panel, at the same x-positions as the boxes. Levels are
  assigned from patch mean grey against a discrete palette (fig 2: 0/33 = high, 125/155 =
  mid, 212 = low; no intermediate values occur).
- **Structural self-check:** the recovered design reproduces 22 factorial + 1 centre
  (stage 1) and 16 factorial + 8 axial + 1 centre (stage 2), matching the published design
  without being told to.

**Reading error:** one pixel = 0.0082 response units (Fig 1) and 0.0124 (Fig 2). A ±3 px
error is ±0.025 and ±0.037 units, i.e. 6.9% and 3.8% of the between-condition spread.
Optical precision is not the limiting factor; per-condition biological SEM (0.24 and 0.37
units) is.

---

## Agreement between the two extractions

| | Stage 1 | Stage 2 |
|---|---|---|
| coded design cells agreeing | 137/138 (99.3%) | 99/100 (99.0%) |
| their mean inside our [Q1, Q3] | 23/23 | 24/24 |
| Spearman rank correlation | 0.880 | 0.860 |
| Pearson | 0.850 | 0.835 |
| argmax agreement | yes (`stage1_20`) | **no** — theirs `stage2_13`, ours `stage2_18` |
| FN-only control (must be ≈1.0) | 0.966 vs 0.969 | — |

The two extractions measure different statistics — mean over detected dots versus box
median — so exact numerical agreement was never expected. Rank agreement and the
fibronectin control are the meaningful checks, and both pass. The stage-2 argmax
disagreement is unresolved; see `VALIDATION_REPORT.md` blocker B1.
