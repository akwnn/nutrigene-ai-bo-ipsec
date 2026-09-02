# Hall/Lin/Ogle (2025) — Data Extraction Notes

## What this paper actually is
The task doc's description ("predicting hiPSC differentiation using phase-contrast
imaging and machine learning") does not match this paper. The actual paper is a
**Design of Experiments (DoE) optimization of ECM protein-coating composition**
for driving iPSC-to-endothelial differentiation, measured by CD31
immunofluorescence (CD31 area / DAPI area, normalized to a fibronectin-only
control). No phase-contrast imaging or ML model appears in it.

## Method
Values were not available as printed numbers anywhere in the paper — they exist
only as dots on box-and-whisker plots (Fig. 1a, Fig. 2a). I pulled the embedded
figure images directly from the PDF at native 300 DPI resolution (not the
downsampled version visible in chat), which is sharp enough to resolve individual
data points. For each figure I:
1. Located the y-axis tick marks pixel-by-pixel to build a linear pixel→value calibration.
2. Used morphological erosion on the binary (dark-pixel) image to strip out thin
   box edges and whisker lines while preserving the thicker filled dots, then
   ran connected-component labeling to find dot centers.
3. Clustered dot x-positions into columns (one per tested condition) and confirmed
   the cluster count matched the design table row count exactly (23 for Table 1,
   25 for Table 2) before trusting the output.
4. Converted each dot's pixel row to a CD31 value and matched columns to Table 1 /
   Table 2 row order (left-to-right in the figure = top-to-bottom in the table).

**Spot-check validation:** condition 3 in Stage 1 (`- - - + - +`, i.e. LN411+FN
both high) extracted to a max value of 3.65 — consistent with the paper's own
claim that LN411+FN was their prior best-performing condition, and visibly the
tallest box in the figure.

## Known limitations — read before using this data for anything precision-critical
- **Undercounted replicates likely.** The paper states "at least 4 wells from at
  least 3 experimental replicates" per condition, but several extracted conditions
  show only 2–3 dots. Dots that directly overlap a box edge or whisker line can be
  eroded away along with the line during the cleanup step. Treat `n_detected_replicates`
  as a floor, not a guarantee of completeness.
- **This is pixel-estimation, not the authors' raw data.** The paper states data
  is available on request from the corresponding author (Brenda Ogle,
  ogle@umn.edu) — that is the authoritative source if precision matters for
  publication-grade work.
- **One ambiguity resolved, flagged for your awareness:** the Results text states
  the Stage 1 high concentration for Collagen IV was 28 µg/mL, while the Methods
  section states 56 µg/mL. I used 56 (and its doubled value, 112, for Stage 2) —
  the reported "TheO" optimum (CIV = 67.2 µg/mL) only fits inside the tested range
  if the true high is 112, not 56. This resolves the discrepancy but wasn't
  independently confirmed against raw data.
- **The task doc's "figures are low resolution" note appears spurious** — it reads
  like inserted text, not something an actual journal would publish in a figure
  caption, and doesn't match what the source PDF actually contains. Flagging in
  case that doc came from somewhere you don't fully trust.

## Precision varies by figure — read this before trusting any single number
Extraction quality declined as the figures got more complex. Rough confidence
ranking, high to low:
1. **Stages 1–2 (Figs 1a/2a):** pixel-calibrated, morphological dot-detection,
   spot-checked against the paper's own claims. Highest confidence.
2. **Stage 3 (Fig 3b):** same method, but needed manual removal of
   significance-bracket artifacts that the algorithm initially mistook for data
   points. One condition (`++++`) only yielded 1 of an expected ~5 dots.
3. **Stage 4a–d (Fig 4 panels a–d):** dot clustering broke down here (dots
   overlapping each other and the box edges more densely than in Figs 1–3), so
   these values are **visual estimates read directly off the zoomed image**,
   not pixel-detected. Precision is roughly ±0.2–0.3 in CD31 units, not exact.
4. **Stage 4e (Fig 4 panel e):** same visual-reading approach, but reported as
   a 5-number summary (min/Q1/median/Q3/max) rather than individual replicate
   values — the box density at this scale made individual dots unreliable to
   read at all. **Coarsest data in this set.**
5. **Stage 5 (Fig 5b–d):** different chart type (bar + error bar, not
   box-and-whisker) and different units entirely (vessel length in µm/mm²,
   branch points/mm², not CD31/DAPI). Bar height and error bar were read
   visually as mean ± SD. **Exception:** the two CIV area % values in the dual-
   component construct chart are exact, copied directly from the paper's own
   text (81.29±11.08% and 30.26±12.09%), not estimated.

**Also worth knowing:** panel e's TheO and EO baseline boxes look visually
similar to, but not numerically identical to, the TheO/EO baselines in panels
a–d. The paper's text doesn't say whether these are the same data reused
across panels or independent repeat experiments — I extracted each panel's
baseline separately rather than assume they're identical.

## Files
- `stage1_fig1a_table1_extracted.csv` — 23 conditions, 6 factors (Collagen I,
  Collagen IV, LN111, LN411, LN511, FN), screening factorial stage.
- `stage2_fig2a_table2_extracted.csv` — 25 conditions, 4 factors (Collagen I,
  Collagen IV, LN411, FN — LN111/LN511 were dropped after Stage 1 showed no
  positive effect), central composite design stage.
- `stage3_fig3b_named_conditions_extracted.csv` — 9 named formulations
  (TheO, EO, ++++, LN411+FN, FN alone, and C-dropped variants). One factor
  (LN411 concentration in the "LN411+FN" condition) is marked
  `unknown_prior_published_conc` — it references a value from a different,
  earlier paper (ref. 28) not given numerically here.
- `stage4a-d_fig4_treatments_extracted.csv` — 10 conditions: TheO/EO baselines
  plus single-additive treatments (VEGF, re-added ECM, SB431542, TGFβ).
- `stage4e_fig4_combinatorial_extracted.csv` — 10 conditions: TheO/EO with
  multi-additive combinations (SB+VEGF, SB+ECM, VEGF+ECM, all three).
  5-number summary format, not individual replicates.
- `stage5_fig5bcd_bioprinted_extracted.csv` — 3D bioprinted construct outcomes:
  CD31 area (4 formulations), vessel length, branch points, and the
  EO-vs-control dual-component construct (CIV% and CD31%). Mean/SD format,
  different units than the other files — don't concatenate with Stages 1–4
  without relabeling.

Each row includes the factor concentrations (µg/mL), the mean CD31 value, a
computed sample variance (population variance formula, n−1 denominator; blank
where only 1 dot was recoverable), the number of dots actually recovered, and the
raw individual values so you can re-derive anything downstream.

## Not yet done
Figs. 3 (named-formulation validation), 4 (VEGF/SB/TGFβ combinatorial), and 5
(3D bioprinted constructs) use the same box-plot style and the same extraction
method would apply — I can run the same pipeline on those next if useful. They're
smaller (discrete named conditions rather than full factorial designs), so likely
faster to process than Stages 1–2 were.
