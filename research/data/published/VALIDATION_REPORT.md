# Validation report — third-party digitization of Hall/Ogle 2025

**Status: RESOLVED 2026-08-11 — canonical CSVs produced.** See the closure note at the
foot of this document. Four of five blockers are closed; B1 is closed by a correction
found in the PDF cross-check; the second extraction is confirmed **lost**, not pending.

*(Original status, retained: "BLOCKED. Five blockers. Canonical CSVs were not produced.")*

**Validation method.** The strongest available check was applied: an *independent second
digitization* of the same two figures, performed earlier in this project from the
Springer Nature PNGs (`software/scripts/digitize_hall_ogle.py`,
`research/data/external/hall_ogle_2025/`). The two extractions used different source images
(their 300 DPI PDF-embedded vs our web PNG), different targets (their individual dot
centroids vs our box Q1/median/Q3), and different keying (their figure-order-to-table-order
vs our direct read of the coded circle matrix printed beneath each panel). Agreement
between them is therefore real evidence; disagreement localises the error.

**Nothing was corrected.** Where the evidence favours one reading, that is stated and the
row is still flagged.

---

## 1. Inventory — what arrived

| File | Rows | Cols | Notes |
|---|---|---|---|
| `stage1_fig1a_table1_extracted.csv` | 23 | 12 | matches expected 23 |
| `stage2_fig2a_table2_extracted.csv` | 25 | 10 | matches expected 25 |
| `stage4a-d_fig4_treatments_extracted.csv` | 10 | 11 | not requested |
| `stage4e_fig4_combinatorial_extracted.csv` | 10 | 11 | not requested; 5-number summary |
| `stage5_fig5bcd_bioprinted_extracted.csv` | 16 | 6 | not requested; different units |
| `EXTRACTION_NOTES.md` | — | — | method provenance, supplied |
| `iPSC-EC_BO_Model_Data_Summary.pdf` | — | — | not inspected for this validation |

No blank rows, no duplicated rows, no nulls in any file.

**Column names are the digitizer's, not the source's**, and they are self-describing.
Stage 1/2 columns: `condition_id, factor_code, <protein>_ugml ×N,
cd31_area_dapi_norm_fn_mean, cd31_area_dapi_norm_fn_variance, n_detected_replicates,
raw_extracted_values`.

Figure correspondence is stated explicitly in the filenames and confirmed by row count
and factor count; it was not inferred.

Method provenance **was** supplied, and is unusually good: axis calibration by tick
pixels, morphological erosion plus connected-component labelling for dot centroids,
column clustering checked against the design row count, and a per-figure confidence
ranking. Credit where due — most of section 5's `EXTRACTION_METHOD.md` could be written
from it.

---

## 2. BLOCKERS

### B1 — The two independent extractions disagree on the stage-2 argmax

| | their extraction | our extraction |
|---|---|---|
| stage-2 best condition | **stage2_13** (3.67) | **stage2_18** (4.22) |
| stage-1 best condition | stage1_20 (1.96) | stage1_20 (1.45) — agree |
| Spearman between extractions | 0.860 (stage 2), 0.880 (stage 1) | |
| top-5 overlap | 3/5 both stages | |

Phase 2's headline claim is *"BO recovers the published discrete argmax in k picks."*
**Two good-faith digitizations of the same figure do not agree on what that argmax is.**
Until they do, the replay has no defined target.

*Caveat that partly softens this:* the two extractions measure different statistics —
their mean over detected dots versus our box median — so exact agreement was never
expected. But the argmax is the load-bearing quantity and it must be settled.

**What would resolve it:** the underlying data from Ogle, or the high-resolution Figure 1
the caption says was supplied to the editor. Failing that, adjudicate stage2_13 vs
stage2_18 by hand at high zoom and record the decision.

### B2 — Two design-matrix cells contradict the printed coded design

Their `factor_code` was checked cell-by-cell against our direct read of the grey-scale
circle matrix printed beneath each panel. Agreement: **137/138 (stage 1), 99/100 (stage 2)**.

| Row | Factor | Digitizer | Printed matrix | Pixel evidence |
|---|---|---|---|---|
| `stage1_23` | LN511 | `-` (0) | high (1) | patch mean grey **0.9** — pure black, 109 levels from the nearest threshold |
| `stage2_21` | FN | `+` (1) | low (0) | patch mean grey **212.0** — the exact canonical "light" value in that figure |

The grey palette in both figures is strictly discrete (fig 2: 0/33, 125/155, 212 with no
intermediates; 212 recurs 37 times), so neither read is borderline.

**Both cells favour the printed matrix over the CSV.** Not corrected here.

*Important diagnostic:* these are **isolated single cells, not a row offset.** A keying
error would misalign whole rows and produce ~50% disagreement. At 99%+, both keyings are
structurally correct and these are transcription slips.

### B3 — The µg/mL columns bake in the contested Collagen IV value

`stage2_*.collagen_iv_ugml` has centre = 56.0, implying a stage-2 high of **112** and
therefore a stage-1 high of **56** — the Methods reading.

The notes state the reasoning: *"the reported TheO optimum (CIV = 67.2 µg/mL) only fits
inside the tested range if the true high is 112."* **That is circular.** Whether TheO lay
inside the tested range is precisely the contested question, and the project's headline
detail depends on the opposite answer. Assuming it to resolve the ambiguity assumes the
conclusion.

This also violates the project's standing format rule: **coded levels only, no µg/mL
anywhere**, adopted specifically so nothing depends on this unresolved number.

*Independent note, in fairness:* a separate geometric argument in this project (TheO's
coded position showing the signature of a constrained JMP profiler) also leans toward the
Methods reading. But it reaches that by different evidence and still calls the question
50/50. The CSV should not encode either answer.

**What would resolve it:** drop the µg/mL columns entirely and carry coded levels only.
The coded levels are independently verified (B2) and sufficient for everything downstream.

### B4 — Collagen IV's main effect contradicts a published claim

Main-effects fit to their stage-1 means (23 rows, 16 residual df):

| Protein | Effect | SE | Paper says | |
|---|---|---|---|---|
| C | +0.096 | 0.078 | positive significant | consistent |
| **CIV** | **−0.001** | 0.078 | **positive significant** | **contradicts** |
| LN411 | +0.086 | 0.079 | positive significant | consistent |
| LN111 | −0.046 | 0.078 | dropped | consistent |
| LN511 | −0.119 | 0.079 | dropped | consistent |
| FN | +0.008 | 0.078 | retained | — |

Our independent extraction gives CIV −0.053, i.e. the same sign. So **both digitizations
contradict the paper on Collagen IV**, which points at either a shared extraction
artefact or at the published claim resting on interaction terms rather than the main
effect.

*Strong mitigating caveat:* their stage 1 is saturated for the two-factor-interaction
model (22 non-centre runs, 1+6+15 = 22 parameters), and significance in the paper came
from replicate-level degrees of freedom, not the design. A main-effects fit on condition
means cannot reproduce their model and a disagreement here is weak evidence. Flagged as a
blocker because the instruction is explicit that a published finding outranks a figure
reading.

### B5 — A referenced file was not delivered

`EXTRACTION_NOTES.md` lists `stage3_fig3b_named_conditions_extracted.csv` under **Files**
and describes its contents (9 named formulations, one column marked
`unknown_prior_published_conc`). **It is not on disk.** Either it was omitted from the
handoff or the notes describe work not completed.

---

## 3. FLAGS — manual check requested

| # | Item | Detail | What would resolve it |
|---|---|---|---|
| F1 | Replicate undercount | `n_detected_replicates` < 4 in **8/23** stage-1 and **4/25** stage-2 conditions; minimum 2. Paper states ≥4 wells from ≥3 experiments. | Acknowledged in their notes as a known limitation of the erosion step. Treat as a floor. Affects condition means most where n=2. |
| F2 | Exactly symmetric raw values | `stage1_01` (n=5) and `stage1_23` (n=4) have raw values **exactly symmetric about their mean** — e.g. 0.588; 0.752; 0.966; 1.18; 1.344. 0/24 stage-2 conditions show this. | Possible dot-detection artefact on evenly spaced overlapping dots, or transcription. Re-read those two boxes. |
| F3 | No centre-point replication | Both stages contain exactly **one** all-centre run (`stage1_13`, `stage2_04`). The task anticipated multiple stage-2 centre runs as a free noise estimate. **The design does not contain them.** | Nothing to fix — the expectation does not match the published design. Noise must come from within-condition dots instead. |
| F4 | Stage-1 argmax value gap | `stage1_20`: theirs 1.96, our median 1.45 — largest stage-1 gap. Both rank it first. | Mean-vs-median difference under right skew, most likely benign. |
| F5 | Stage-2 value gaps | `stage2_18` theirs 3.04 / ours 4.22; `stage2_02` theirs 2.40 / ours 1.31; `stage2_05` theirs 1.69 / ours 2.76. | Directly implicated in B1. Re-read these three. |
| F6 | Files beyond scope | Stage 4a–d, 4e and 5 arrived unrequested and are, by the digitizer's own ranking, the **coarsest** data in the set (visual reading, ±0.2–0.3 CD31 units; 4e is a coarse 5-number summary). | Do not use for anything precision-critical. Not validated here. |

---

## 4. NOTES — recorded, no action needed

**The fibronectin control passes, on both extractions independently.** `stage1_01`
(all proteins zero, FN at 22 µg/mL) = **0.966** theirs, **0.969** ours. The readout is
normalised to the FN-only control, so ~1.0 is required by construction. This is the
single strongest evidence that both the keying and the axis calibration are correct.

**Their mean falls inside our independently-measured [Q1, Q3] for 47 of 47 conditions**
(23/23 stage 1, 24/24 stage 2). Bias +0.078 (stage 1) and −0.010 (stage 2).

**The variance column is genuinely variance, not SD.** Sample variance with `ddof=1`
reproduces the column in 23/23 and 25/25 rows.

**Design structure verified independently.** Stage 1: 22 factorial + 1 centre; 2FI model
matrix rank 22 of 22 parameters, 1 residual df. Stage 2: 16 factorial + 8 axial + 1
centre; second-order model rank 15 of 15, 10 residual df; column balance exactly 0.5 on
every factor, as a face-centred CCD requires. Levels are confined to {0, 0.5, 1} in both.

**Reading error is not the limiting factor.** Fig 1: 121.8 px/unit → 1 px = 0.0082
response units. Fig 2: 80.8 px/unit → 1 px = 0.0124. A generous ±3 px centroid error is
±0.025 and ±0.037 units respectively — **6.9% and 3.8% of the between-condition spread.**

**The binding constraint is biological, not optical.** Per-condition SEM computed from
their own dots is **0.238 units (stage 1) and 0.369 units (stage 2)** — **66% and 38% of
the between-condition spread.** This is consistent with the ~68% CV backed out of the
Figure 2a interquartile ranges elsewhere in this project.

**No values exceed 4.0 in either stage**, none negative, no suspiciously round values, no
monotone-in-row-order pattern, and no duplicated coded conditions.

**On the digitizer's challenge to the source documentation.** The notes state that the
"figures are low resolution" caption note *"appears spurious… reads like inserted text,
not something an actual journal would publish"* and suggest the task documentation came
from an untrustworthy source. **It is verbatim in the published Figure 1 caption.**
Retrieved directly from the live article: *"Contour plots showing the relationship between
CD31 expression and concentration of individual proteins… The resolution of all figures is
low, but figure #1 is especially low. We have attached th[e high resolution figure]…"*
The project documentation is correct on this point. It also matters practically: it means
a high-resolution Figure 1 exists and can be requested from the corresponding author.

---

## 5. Canonical output

**Not produced.** Blockers B1–B5 are unresolved, and the instruction is to produce the
report and stop.

When they are resolved, two of the five are already answerable from material in hand:
B2 (adopt the printed coded matrix, which is independently verified) and B3 (drop the
µg/mL columns and carry coded levels only). B1, B4 and B5 need either a human adjudication
or the authors' data.

---

## 6. Judgement — is this good enough to replay?

**Reading error: yes, comfortably.** At 4–7% of the between-condition spread, optical
precision is not what limits the replay.

**Condition-level precision: marginal, and it is the real constraint.** Per-condition SEM
runs 38–66% of the between-condition spread. Many adjacent conditions are not separable
from one another, which is a property of the published experiment, not of the
digitization — the source assay has a ~68% CV and the paper reports no variance at all.

**The specific claim at risk is the argmax claim.** "BO recovers the published discrete
argmax in k picks" requires knowing the argmax. Two careful extractions disagree on it for
stage 2 (B1). Scoping the Phase 2 claim to *rank recovery* — Spearman 0.86–0.88 between
independent extractions, top-5 overlap 3/5 — is better supported than a claim about a
single best point.

**Recommendation.** Request the underlying data and the high-resolution Figure 1 from
Ogle (ogle@umn.edu) — the caption confirms the latter exists. Until then, treat the
digitization as adequate for rank-based analysis and inadequate for any claim that turns
on the identity of the single best condition.


---

## 7. CLOSURE — 2026-08-11

Canonical CSVs are at `research/data/published/hall_ogle_2025_stage{1,2}.csv`, built by
`software/scripts/build_published_dataset.py` and validated by `software/tests/test_published_dataset.py`
(21 tests, run from a clean clone).

**B1 — closed by correction, not by adjudication.** `pdf_crosscheck.md:119` found our
`stage2_18 = 4.22` is that column's **Q3 (4.24)**, not its median (**3.48**). The stored
triple corroborates it independently: q1 1.634, median 4.221, q3 4.259 — a median sitting
0.04 below Q3 while 2.59 above Q1 is a mis-detected median line. Corrected, the stage-2
argmax moves from condition 18 to **condition 13**, which is what the other extraction
reported. **The extractions agree.** This does *not* reinstate an argmax claim: Q31
registered it as unsupportable on grounds the correction cannot touch — the top five IQRs
share a common band, and the paper never names a best condition.

**B2 — closed, and the two cells split.** `stage2_21` fibronectin corrected low → high
(Table 2 row 21 prints `- + + +`). `stage1_23` laminin 511 needed **no** correction: the
surviving JSON already holds the printed `+`. The dispute was with the lost CSV.

**B3 — closed by construction.** No physical-unit column is emitted at any point, and a
test asserts it. The Collagen IV value the paper contradicts itself about (settled at 28,
not 56) is recorded and unused.

**B4 — downgraded to a limitation, with the arithmetic.** Stage 1 is **saturated**: 22
parameters for the two-factor-interaction model, design rank 22, 23 runs of which one is a
centre point — **zero residual degrees of freedom**. A main effect computed from condition
medians returning null is the expected outcome, not a contradiction of the paper, whose
own tests used replicate-level degrees of freedom that do not exist in digitized medians.
Asserted in `test_stage1_is_saturated_for_the_two_factor_interaction_model`.

**B5 — closed as not-delivered.** The referenced `stage3` file is absent and was never
committed. No third design stage exists in the figures used here.

### What the dataset cannot support, stated plainly

- **A best-condition claim.** Not because the extractions disagree — corrected, they
  agree — but because the top five IQRs overlap and the paper names no best condition.
- **Reproduced main effects.** Foreclosed by the saturated stage-1 design.
- **An absolute-scale claim from stage 2.** The readout is normalised *to* the FN
  control, and in stage 2 that control is run 3 — the one condition whose median could
  not be extracted. The normaliser's own value is missing from the dataset that depends
  on it. Asserted rather than invented.
- **Anything beyond this study.** One dataset, one lab, one assay.
