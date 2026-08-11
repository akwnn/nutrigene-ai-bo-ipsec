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
error is **±0.025 (Fig 1a) and ±0.037 (Fig 2a)**, and those two numbers are the whole of
it. Optical precision is not the limiting factor; per-condition biological spread is,
and that is carried by `response_q1`/`response_q3`.

> **"Spread" means the standard deviation of the condition medians, not their range.**
> An earlier version of this paragraph said "6.9% and 3.8% of the between-condition
> spread" without defining the word, and a downstream build read it as the range,
> computing `reading_error = 0.07 × (max − min)`. That gives 0.0655 and **0.2496** —
> 2.7× and 6.7× too large, and at stage 2 a quarter of a response unit, larger than most
> of the between-condition differences the column is meant to bound. Against the sd the
> quoted percentages are 9.2% and 3.5%; against the range they are 2.6% and 1.0%.
> **Quote the absolute figures, not the percentages.**

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
| argmax agreement | yes (`stage1_20`) | **yes** (`stage2_13`) once C4 is applied; `no` before it |
| FN-only control (must be ≈1.0) | 0.966 vs 0.969 | 0.846 vs 1.028 |

The single disagreeing design cell in each column is C2/C3 below. They are **not** the
same kind of error: in stage 2 our strip is wrong, in stage 1 the transcription is. One
each, both settled from the PDF.

The two extractions measure different statistics — mean over detected dots versus box
median — so exact numerical agreement was never expected. Rank agreement and the
fibronectin control are the meaningful checks, and both pass. The FN-only control is the
all-low row in each stage (every other protein at 0 µg/mL, fibronectin at its low level
of 22), and the stage-2 pair straddles 1.0 more loosely than stage 1's — 0.846 and 1.028
against a normalisation target of exactly 1 — which is a fair measure of how much
agreement to expect from this source at all.

**The stage-2 argmax disagreement is resolved and `VALIDATION_REPORT.md` blocker B1
closes.** It was our defect, not an ambiguity in the source: our `stage2_18` median was
that column's Q3 (C4 below), which beat `stage2_13` and manufactured the disagreement.
Corrected, both extractions pick `stage2_13`. **This does not reinstate an argmax
claim** — the top IQRs share a common band and the paper never names a best stage-2
condition, so the scope stays rank recovery.

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

### C2 and C3 — one bad design cell in each digitization, and they split

**Neither is a "figure contradicts table" story, and the resolution is not a rule about
which source to prefer.** `docs/pdf_crosscheck.md:126-127` reads the source PDF with four
readers and settles both cells; they fall opposite ways.

| | cell | patch centre (x, y) | our mean grey | our strip | transcription | the paper prints | outcome |
|---|---|---|---|---|---|---|---|
| **C2** | stage 2, col 20, FN | (1417, 915) | 212.0 (min 211, max 212) | `-1` | `+1` | `- + + +` (Table 2 row 21) | **our strip is wrong**, corrected to `+1` |
| **C3** | stage 1, col 22, LN511 | (1509, 735) | 0.9 (min 0, max 154) | `+1` | `-1` | `+ + + + + -` (Table 1 row 23) | **the transcription is wrong**, our value stands |

**C2** is corroborated structurally as well as from the PDF: with the strip's reading,
column 20 is `- + + -`, character-for-character identical to column 15, and `- + + +`
appears nowhere. A face-centred central composite design requires all 16 distinct
corners. The strip has 15 and one duplicate.

**C3 was very nearly "corrected" in the wrong direction, and that is worth recording.**
The reasoning went: the table is the design of record, the strip reads a row absent from
Table 1, therefore the strip is wrong. The premise was false — the paper prints
`+ + + + + -`. No structural check could have caught the mistake either, because stage
1's 22 non-centre runs are a D-optimal subset of a 2⁶ space and flipping one level yields
another perfectly valid saturated design (rank 22 of 22 either way). A cell that is
already correct is the easiest thing in a dataset to damage, because nothing downstream
complains.

**Column ordering is not in doubt.** Every other cell in both figures agrees with its
table row — 137/138 in stage 1, 99/100 in stage 2 — so box *i* pairs with table row *i*
throughout.

**What each artefact carries.** The canonical CSVs take the strip reading with C2
applied. The raw JSON keeps the uncorrected strip, so the disagreement stays inspectable.
Both cells are declared in `boec.published.FIGURE_STRIP_ERRORS` and
`EXTRACTION_A_ERRORS` with their evidence, and the validator fails on any *undeclared*
disagreement — and equally on a declared one that has stopped disagreeing, so the
accept-list cannot rot into an excuse for a future mismatch.

### C4 and C5 — two more medians reading the Q3 rule

The defect behind C1's neighbour: `_boxes` searches for the widest horizontal run in
`range(top + 3, bot - 2)`, but a box's Q3 rule is full width too, so wherever that rule
is thicker than the 3 px skip it wins and is reported *as* the median.

Caught on `stage2_18` by cross-check against the third-party extraction
(`pdf_crosscheck.md:119`) — our 4.2215 is that column's Q3. The stored triple gives it
away without any image work: a median 0.04 below Q3 while 2.59 above Q1 is a mis-detected
line, not a skewed distribution. Generalising the find shows it hits **three** boxes.

| box | Q3 rule | was | now | evidence |
|---|---|---|---|---|
| `stage2_18` | 4 px | 4.2215 | **3.4911** | median rule at row 456, 30/30 wide; read independently as 3.48 |
| `stage2_11` | 4 px | 2.8102 | **2.3645** | median rule at rows 547–548, 31/31 wide |
| `stage2_05` | 10 px | 2.7607 | **refused** | no full-width rule below the band; median merged with Q3 |

`stage2_05` is left empty and flagged, bounded to **[2.686, 2.798]**. Its top band is
10 px of continuous full width against a 2 px Q1 rule, and there is no rule below it. A
point value there would be a guess wearing a number.

**Corrected explicitly rather than in `_boxes`, and that is a deliberate stopping point.**
Two attempts at a general fix each made things worse: skipping *consecutive* full-width
rows breaks on antialiasing holes (stage-1 box 15 is full width at +0 and +2 but not +1,
so the skip stops early and returns the rest of the Q3 rule — damaging a box that was
already correct), and grouping full-width rows into bands turned seven confidently-wrong
medians into `NaN`. The algorithm needs proper work. Three declared corrections with
pixel evidence is honest; a third guess is not.

**This dissolves the stage-2 argmax dispute.** Our uncorrected `stage2_18` (4.2215,
actually Q3) beat `stage2_13` and manufactured the disagreement with the third-party
extraction. Corrected, both pick `stage2_13`. **It does not reinstate an argmax claim** —
the top IQRs share a common band and the paper never names a best stage-2 condition, so
the scope stays rank recovery.

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

---

## LIMITATIONS OF THE DIGITIZED DATASET — text for the paper

Every deviation between the published figures and this dataset, stated so a reader can
judge the replay without re-deriving any of it. Nothing below is hedging: each item is
a specific, bounded departure with the evidence attached.

### L1. The responses are pixel measurements of a figure, not the authors' data

The per-condition values appear nowhere in Hall, Lin & Ogle 2025 as numbers. Tables 1
and 2 are purely coded (−/0/+); the supplement contains only figure legends; no erratum
exists. Every response here was measured off the Figure 1a and 2a box plots. The
authoritative source remains the corresponding author, and the paper states data is
available on request.

### L2. The source figures are low resolution, by the authors' own admission

The published Figure 1 caption carries an unremoved note to the editor: *"The resolution
of all figures is low, but figure #1 is especially low. We have attached th[e high
resolution figure 1 here]."* Figure 1 panel b additionally shows an unreplaced "Y axis
label" placeholder. A high-resolution Figure 1 exists and has not been obtained. One
digitizer judged this note spurious; it is verbatim in the live article and the PMC
mirror.

### L3. Optical reading error is ±0.025 (Fig 1a) and ±0.037 (Fig 2a)

±3 px at each figure's calibration — 121.75 and 80.78 px per response unit. **This is not
the uncertainty on a condition.** Biological spread is roughly an order of magnitude
larger and is carried separately in `response_q1`/`response_q3`. Do not quote reading
error as a fraction of anything; the absolute figures are the reportable quantities.

### L4. One of 48 conditions has no median (`stage2_05`)

Its median rule is drawn flush against Q3 and the two have merged into a single 10 px
full-width band, against a 2 px Q1 rule, with no rule below it. The median is bounded to
**[2.686, 2.798]** and the cell is left empty rather than filled with a point estimate.
Any analysis over stage 2 runs on 24 of 25 conditions unless it can use the bound.

### L5. Three medians required manual correction, and the extractor is known-imperfect

`_boxes` locates the median as the widest horizontal run below a fixed 3 px skip from the
box top. A Q3 rule thicker than 3 px is therefore reported as the median. This affected
`stage2_18` (4 px rule), `stage2_11` (4 px) and `stage2_05` (10 px) — 3 of 48 conditions,
all in stage 2, all corrected or refused explicitly with pixel evidence. **The underlying
algorithm has not been fixed.** Two general fixes were attempted and both regressed other
boxes. A future re-extraction should be expected to move these values, and the corrected
cells are marked in `flag_reason` so they can be re-checked rather than trusted.

### L6. One design cell in each digitization was wrong, in opposite directions

Our figure-strip reading had `stage2_21` fibronectin low where Table 2 prints `- + + +`;
the third-party transcription had `stage1_23` laminin-511 low where Table 1 prints
`+ + + + + -`. Both were settled against the source PDF by four readers
(`docs/pdf_crosscheck.md:126-127`). **Neither source is reliable wholesale**, and a
preference rule in either direction would have corrupted a correct cell — one nearly did.
Agreement elsewhere is 137/138 and 99/100 coded cells.

### L7. The two extractions measure different statistics and are not averaged

The third-party extraction reports the mean of detected dots; this one reports the box
median. They differ by 0.10 (stage 1) and 0.34 (stage 2) in the median row — far more
than optical error — because a mean is not a median on a skewed sample of 3–10 points.
`reconciled` is the box median; the two are never combined. By the estimand-appropriate
test — does the third-party mean fall inside our [Q1, Q3]? — they agree on **48 of 48**.

### L8. Replicate counts are a floor, and dispersion is approximate

The paper states ≥4 wells across ≥3 experimental replicates per condition, but the
third-party extraction recovers as few as 2–3 dots for some conditions: dots overlapping
a box edge or whisker are removed with the line. `response_sd` is derived as IQR/1.349,
which assumes normality that these visibly skewed samples do not satisfy — it overstates
several conditions (`stage2_08` yields sd 4.38 on a response of 2.27). **Prefer
`response_q1`/`response_q3`**, which carry the same information without the assumption.

### L9. The dataset is coded-only, and deliberately so

No physical concentration appears in any column. The source contradicts itself on
Collagen IV — Results says 28 µg/mL, Methods says 56 — and the entire pipeline runs in
coded space so that nothing depends on which is right.

### L10. What the dataset cannot support

- **No absolute-scale claim beyond the normalisation.** Responses are ratios to the
  fibronectin-only control, which reads 0.9692 (stage 1) and 1.0275 (stage 2) against a
  target of exactly 1 — that ~3% gap is a fair measure of the achievable accuracy.
- **No single-argmax claim.** The two extractions now agree that `stage2_13` is the
  highest median, but the top conditions' IQRs share a common band and the paper never
  names a best stage-2 condition. **The replay is scoped to rank recovery, not argmax
  identification**, and that scope does not change because the extractions came to agree.
- **No claim about the true optimum.** The paper's own best formulation (EO) sets
  fibronectin to zero, below the design floor of 22 µg/mL. It is not in the design space,
  so no replay of this data can reach it.

### L11. One extraction is not reproducible

The third-party digitization's code was never supplied. Its CSVs and notes are preserved
at `data/external/extraction_a/` and can be *used* and *checked against*, but not
*re-run*: the erosion kernel, clustering tolerance and calibration rows are unrecorded.
The stage-2 design correction (L6) is independently secured by CCD structure; **the
stage-1 one rests on the PDF cross-check alone.**
