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
- **Structural self-check — WITHDRAWN AS STATED.** This previously read: *"the recovered
  design reproduces 22 factorial + 1 centre (stage 1) and 16 factorial + 8 axial + 1
  centre (stage 2), matching the published design without being told to."* The counts
  were correct and the conclusion did not follow. Counting row types cannot see a
  duplicated corner or a missing one, and the shipped stage-2 extraction had both. See
  "Corrections" below.

**Reading error:** one pixel = 0.0082 response units (Fig 1) and 0.0124 (Fig 2). A ±3 px
error is ±0.025 and ±0.037 units, i.e. 6.9% and 3.8% of the between-condition spread.
Optical precision is not the limiting factor; per-condition biological SEM (0.24 and 0.37
units) is.

---

## Agreement between the two extractions

Recomputed after the corrections below. Stage 2's second row changed — it was `24/24`
only because the unresolved box was excluded from the denominator rather than counted as
a failure, which is its own small instance of a check flattering itself.

| | Stage 1 | Stage 2 |
|---|---|---|
| coded design cells agreeing | 137/138 (99.3%) | 99/100 (99.0%) |
| their mean inside our [Q1, Q3] | 23/23 | **25/25** (was 24/24) |
| Spearman rank correlation | 0.880 | **0.871** (was 0.860) |
| Pearson | 0.850 | **0.847** (was 0.835) |
| argmax agreement | yes (`stage1_20`) | **no** — theirs `stage2_13`, ours `stage2_18` |
| FN-only control (must be ≈1.0) | 0.966 vs 0.969 | 0.846 vs 1.028 |

The single disagreeing design cell in each column is C2/C3 below — the paper's figure
contradicting the paper's table — not a disagreement between the digitizers.

The two extractions measure different statistics — mean over detected dots versus box
median — so exact numerical agreement was never expected. Rank agreement and the
fibronectin control are the meaningful checks, and both pass. The FN-only control is the
all-low row in each stage (every other protein at 0 µg/mL, fibronectin at its low level
of 22), and the stage-2 pair straddles 1.0 more loosely than stage 1's — 0.846 and 1.028
against a normalisation target of exactly 1 — which is a fair measure of how much
agreement to expect from this source at all. The stage-2 argmax disagreement is
unresolved; see `VALIDATION_REPORT.md` blocker B1, and both rows carry `flagged = true`
in the canonical CSV.

---

## Corrections applied to this dataset

Three defects, none of which the original validation could detect. The order below was
mandatory: the checks were tightened first, **verified to fail against the shipped
data**, and only then was anything re-read. Emitting a CSV first would have laundered the
defects into a new file; hand-patching values would have hidden that the extractor
produced them.

### C1 — stage 2, row 2 (`stage2_03`): no response recovered

**Was:** `q1`, `median`, `q3` all `NaN`. One of the 48 published conditions had no value.

**Cause, at pixel level.** A box is found by matching a *pair* of vertical ink runs whose
extents agree within a tolerance. For this box the left edge spans image rows 653–700 and
the right edge 657–700 — a 4 px disagreement at the top, caused by a data dot drawn over
the top-right corner and merging with the edge. The tolerance was ±3 px. It missed by one
pixel and the extractor wrote `NaN` silently.

**Fix.** Tolerance widened 3 → 4 px, threaded as the `tol` parameter of `_boxes` rather
than left as a literal.

**Why this is not tuning.** The recovered value is invariant to the parameter: the *same*
edge pair, and therefore identical `q1`/`median`/`q3`, is found at every tolerance from 4
to 10, and **no other box in either figure changes at any value in that range**. The full
diff of the re-extraction against the previous version is exactly three numbers — this
row's three quartiles. 4 is simply the floor of the stable range, not a value chosen for
its effect.

**Recovered:** `q1 = 0.4704`, `median = 0.7056`, `q3 = 1.0028`.

**Independent corroboration:** Extraction A reads this condition's dots as
0.161 / 0.712 / 0.737 / 0.991, mean 0.650. Our box median (0.7056) falls between A's two
middle dots, and A's mean lies inside our [Q1, Q3].

### C2 and C3 — the published figures contradict the published tables

**These are not extraction errors.** Both greyscale patches were re-read at 4×
magnification and both are unambiguous — mean patch grey 212.0 and 0.9 against palette
thresholds of 205 (low) and 110 (high), with essentially no within-patch variation. The
extractor read the figure correctly. The figure disagrees with the paper's own table.

| | cell | patch centre (x, y) | mean grey | figure says | Table says |
|---|---|---|---|---|---|
| **C2** | stage 2, col 20, FN | (1417, 915) | 212.0 (min 211, max 212) | `-1` | `+1` |
| **C3** | stage 1, col 22, LN511 | (1509, 735) | 0.9 (min 0, max 154) | `+1` | `-1` |

**C2 is decided by structure.** With the strip's reading, column 20 is `- + + -` —
character-for-character identical to column 15 — and `- + + +` appears nowhere in the
figure. A face-centred central composite design requires all 16 distinct corners. Table 2
has all 16; the strip has 15 and one duplicate. **The strip is provably the erroneous
object.**

**C3 is decided on weaker grounds, and this is flagged rather than smoothed over.** The
strip reads `+ + + + + -`, which is not a row of Table 1 at all — so the two objects
certainly disagree — but no structural argument settles it, because stage 1's 22
non-centre runs are a D-optimal subset of a 2⁶ space and flipping one level yields
another perfectly valid saturated design (verified: rank 22 of 22 either way). The
resolution rests on the C2 precedent and on the table being the design of record.

**Column ordering is not in doubt.** Every other cell in both figures agrees with its
table row — 137/138 in stage 1, 99/100 in stage 2 — so box *i* pairs with table row *i*
throughout, and the response attached to each corrected design row is the box that sits
directly above it.

**What each artefact carries.** The canonical CSVs take the **table** design. The raw
JSON keeps the **figure** read unchanged, so the disagreement remains inspectable instead
of being overwritten. The two cells are declared in
`boec.published.FIGURE_TABLE_DISCREPANCIES` with their evidence, and the validator fails
on any *undeclared* disagreement — and equally on a declared one that has stopped
disagreeing, so the accept-list cannot rot into an excuse for a future mismatch.

---

## Reconciliation rule, as actually applied

The specification called for averaging the two extractions where they agree within
reading error, and flagging where they do not. **That rule was not applied, because the
two extractions do not measure the same quantity.** Extraction A reports the *mean of
detected dots*; Extraction B reports the *box median*. On skewed samples of ~5 points
those differ by far more than any optical error:

| | stage 1 | stage 2 |
|---|---|---|
| median \|A − B\| | 0.104 | 0.344 |
| reading error (±3 px) | 0.025 | 0.037 |
| rows exceeding reading error | 18/23 (78%) | 24/25 (96%) |
| **A's mean inside B's [Q1, Q3]** | **23/23** | **25/25** |

Applied literally the rule flags 42 of 48 rows and the column stops carrying information —
not because the digitizations disagree, but because a mean is not a median. By the
estimand-appropriate test the two agree on **48 of 48**.

So: `reconciled` = extraction B's box median (the replay needs a robust centre with
matching quartiles to derive `Yvar`, and only B supplies quartiles). `flagged` marks
**rank disagreement** — rows that are the maximum under one extraction but not the other,
plus any row where A's mean falls outside B's [Q1, Q3]. This keeps the column meaningful
and puts the one disagreement that could change a conclusion into the data:

- **stage-2 argmax is disputed.** A says `stage2_13` (3.667); B says `stage2_18` (4.221).
  Both rows carry `flagged = true`. Neither may be used for a rank-position claim.
- stage-1 argmax agrees (`stage1_20`), and no stage-1 row is flagged.

**Reading error** in the CSV is optical only: ±3 px at each figure's calibration, 0.025
(Fig 1a) and 0.037 (Fig 2a) response units. It is *not* the uncertainty on a condition —
that is the biological spread, an order of magnitude larger, carried by `response_q1` and
`response_q3`. Those quartiles are the only dispersion information the paper contains
anywhere.

---

## Reproducing this

```
PYTHONPATH=src python scripts/digitize_hall_ogle.py \
    --fig1 data/external/hall_ogle_2025/fig1_raw.png \
    --fig2 data/external/hall_ogle_2025/fig2_raw.png \
    --out data/external/hall_ogle_2025
PYTHONPATH=src python -c "from boec.published import write_canonical_csv as w; \
    w('stage1','data/published/hall_ogle_2025_stage1.csv'); \
    w('stage2','data/published/hall_ogle_2025_stage2.csv')"
pytest tests/test_published.py
```

The extractor now refuses to write unless every structural check passes **and** the
design agrees with the published table outside the two declared cells.

**Not reproducible from this repository:** Extraction A. Its CSVs and notes are preserved
at `data/external/extraction_a/`, but the code was never supplied, and the erosion
kernel, clustering tolerance and calibration rows are unrecorded. It can be *used* and
*checked against*; it cannot be *re-run*. Every claim resting on it — the design
arbitration in C2/C3 above included — depends on a transcription no one here can
regenerate. Stage-2's C2 is independently secured by the CCD structure; **C3 is not**.

**Figure 1's resolution caveat, verbatim from the published caption:** *"The resolution of
all figures is low, but figure #1 is especially low. We have attached th[e high resolution
figure 1 here]."* Figure 1 panel b additionally carries an unreplaced "Y axis label"
placeholder. Extraction A's notes judged this note *"appears spurious — it reads like
inserted text, not something an actual journal would publish"*; **that judgement was
wrong.** The note is in the live article and in the PMC mirror. A high-resolution Figure 1
exists and can be requested from the corresponding author. Recorded here because a
digitizer's stated confidence was contradicted by the source, which is exactly the kind of
thing a provenance document exists to preserve.
