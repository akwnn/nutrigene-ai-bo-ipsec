# PDF cross-check — digitized data and project record against the source

**Source:** Hall, Lin & Ogle 2025, *Scientific Reports* 15:24479, 15 pages. Full text plus all
figure rasters. Four independent readers; disagreements between them are recorded, not averaged.

**Rule applied throughout: report, do not correct.** Where the PDF settles something it is cited.
Where it does not, the item stays open. Nothing was quietly patched.

**Distinguish three things**, and this document does so explicitly: what the paper **STATES**, what
it **IMPLIES**, and what we **INFER**. The Collagen IV resolution below is an inference, and the
single most consequential claim in the project now rests on it.

---

## 1. THE HEADLINE — Collagen IV, and it reverses our previous lean

### 1.1 The contradiction is real and confined to one number

**Results, p. 2** — "The high concentrations were set based on literature values for ECM coating for
cell culture applications to 35.5 µg/mL, **28 µg/mL**, 15.8 µg/mL, 0.8 µg/mL, 0.8 µg/mL, and
75 µg/mL for C, CIV, LN111, LN411, LN511, and FN respectively."

**Methods, p. 12** — "…was set to either a low (0,0,0,0,0,22 µg/mL) or high (35.5, **56**, 15.8,
0.8, 0.8, 75 µg/mL) level respectively."

Every other value is identical. **CIV alone differs: 28 versus 56.** No unit slip is possible —
"mg/mL" appears zero times in the paper, and the discrepancy is a factor of 2, not 1000.

The paper never prints a numeric stage-2 concentration for any protein. Table 2 is purely symbolic.
There is no stage-2 concentration table anywhere, and no figure caption, table footnote or
supplementary reference supplies one.

### 1.2 The published model settles it — by reconstruction, not by statement

Figure 2b publishes the complete fitted surface (coded factors c=C, v=CIV, l=LN411, f=FN):

```
y = 2.724 + 0.007c + 0.079v + 0.736l − 0.131f − 0.078vl − 0.087vf
    − 0.626c² − 0.492l² + 0.036f² − 1.442·v·l² + 1.435·v·f²
```

The paper states TheO = **C 35.6, CIV 67.2, LN411 0.9, FN 22 µg/mL** (p. 4). Setting
`∂y/∂l = 0` gives `l* = (0.736 − 0.078v) / (0.984 + 2.884v)`, so the model's own optimal LN411 is a
function of where CIV sits. Testing both readings against the paper's stated LN411 = 0.9:

| stage-1 CIV high | stage-2 range | TheO's CIV 67.2 at coded | model's optimal LN411 | vs paper's 0.9 |
|---|---|---|---|---|
| **28 (Results)** | [0, 56] | **+1.4000** — outside | **0.900** | **exact match** |
| 56 (Methods) | [0, 112] | +0.2000 — inside | 1.169 | mismatch |

Three exact hits under the Results reading: coded position **+1.4000**, LN411 **0.900**, and
**28 × 2.4 = 67.2** precisely. Independently recomputed by the lead from the published coefficients,
not taken on a reader's word.

> **Conclusion: the stage-1 Collagen IV high was 28 µg/mL, the stage-2 range was [0, 56], and
> TheO's CIV at 67.2 µg/mL sits 40% beyond the upper coded bound — 20% above the highest CIV
> concentration ever tested. TheO was extrapolated.**

**This reverses the project's previous position.** `project_record.md` §E9 leaned toward the Methods
reading on the grounds that TheO's coded position looked like the signature of a *constrained*
optimiser, which could not return +1.40. That argument is now dead on two counts, below.

**Status: resolved by INFERENCE. Not stated by the authors anywhere.** Caveats that must travel with
it: coefficients are rounded to three decimals; C reconstructs to 35.70 against a printed 35.6;
Figure 2b shows only *significant* terms, so a suppressed CIV² term would create an interior
stationary point and weaken the argument. **A statistician should re-derive this before it carries a
headline.**

### 1.3 The constrained-optimiser argument has no textual support

Whole-document keyword search: **"profiler", "desirability", "maximize", "maximise", "stationary
point" and "canonical analysis" do not appear anywhere in the paper. Zero hits.** There is no JMP
output pane; Figure 2b is a hand-rebuilt two-column table.

The paper's actual wording is "**this prediction solution**" (p. 4) — which is JMP's Response Surface
**Solution** report language, i.e. the unconstrained critical point. Suggestive, not conclusive,
and the paper never says so.

### 1.4 But it is a HYBRID, and this is where our two readers disagreed

One reader concluded design-boundary rather than extrapolation, by maximising the published surface
*constrained* to the coded cube and finding CIV at the +1 face. **That reading has a gap:** coded +1
maps to 56 or 112 under the two candidate ranges, and neither is 67.2, so it cannot reproduce the
paper's own stated number. The reconstruction in §1.2 can, exactly. Recorded because the disagreement
is informative, not because it is unresolved.

**What that reader established, and it stands:** fibronectin was genuinely boundary-clamped, and the
paper says so twice.

> **p. 4** — "TheO without FN (TheO-FN) was evaluated as the model used **did not allow for
> concentrations of FN below 22 µg/mL to be evaluated**… Since the TheO formulation indicated the
> lowest FN concentration would lead to the highest CD31 expression…"
>
> **p. 12** — "the DoE approach did not allow for the value to be set lower than the low FN
> concentration".

**So both mechanisms operated, on different factors: FN pinned at the lower design bound (STATED by
the paper), CIV extrapolated past the upper bound (INFERRED from the published coefficients).** The
project has been treating these as competing explanations. They are not.

### 1.5 What the paper itself blames

> **p. 4** — "the reason for the discrepancy is likely due to use of an on face central composite
> design which **does not allow for accurate modeling outside of the original parameter space**."

The paper's own named cause is extrapolation language. It offers three candidates and picks this one.
Note it does **not** state that TheO's coordinates were outside the tested range — that link is ours.

---

## 2. The open blockers from VALIDATION_REPORT.md

### 2.1 Stage-2 argmax — **closed, and it closes in favour of rank-based replay**

- Highest median in Figure 2a is **stage2_13**, agreeing with the third-party extraction.
- **The top conditions are not separable by eye** — the top five IQRs share a common band.
- **The paper never names a best-performing stage-2 condition.** No text can be contradicted, and
  none can adjudicate.
- Our `stage2_18 = 4.22` appears to correspond to that column's **Q3 (4.24)**, not its median
  (3.48) — i.e. a probable box-statistic error in our own extraction, not theirs.

**Action: scope Phase 2 to rank recovery, as already recommended. A single-argmax claim is not
supportable and the paper cannot make it so.**

### 2.2 The two disputed design cells — **both resolved, and they split**

| cell | printed in the paper | our patch reading | digitizer | verdict |
|---|---|---|---|---|
| `stage1_23` LN511 | **`+`** (Table 1 row 23: `+ + + + + -`) | high | low | **we were right** |
| `stage2_21` FN | **`+`** (Table 2 row 21: `- + + +`) | low | high | **digitizer was right** |

One each. Neither extraction is systematically wrong; both had one isolated cell error.

### 2.3 The missing stage3 file — **does NOT close**

Figure 3b exists and is exactly what the notes describe: named formulations, graphical CD31/DAPI.
**The reference was not an error — the file is genuinely missing and should be requested.**

---

## 3. Corrections to the project record

| claim | verdict |
|---|---|
| Figs 1a/2a are box-and-whisker with overlaid points, not bar charts | **CONFIRMED — our documents are wrong.** Note the likely source of the error: **Fig 5b/5c genuinely ARE bar charts.** |
| Stage 1 = 23 runs (22 factorial + 1 centre) | Confirmed, Table 1 |
| Stage 2 = 25 runs (16 + 8 + 1) | Confirmed, Table 2, all 16 sign combinations present exactly once |
| "face-centred CCD" | Paper's literal wording is "**on face** central composite design". Same design, different term. |
| Stage-2 factors C, CIV, LN411, FN | Confirmed |
| "significant terms up to the 3rd order" | Confirmed verbatim, p. 4 and Fig 2 caption |
| CD31 area / DAPI area, day 10, normalized to FN control | Confirmed, four independent statements |
| ≥4 wells from ≥3 experimental replicates | Confirmed — **but it is a floor, never resolved to an actual n for any 2D condition** |
| FN low = 22 µg/mL, lowest giving good attachment | Confirmed |
| Model could not evaluate FN below 22 | Confirmed, stated twice |
| TheO gave very little differentiation, ~FN alone | Confirmed verbatim |
| Failure attributed to on-face CCD | Confirmed verbatim |
| EO performs well; FN activates TGFβ via inhibitor + add-back | Confirmed. **Precision point: TGFβ activation is never measured** — no pSMAD or reporter data; involvement is inferred pharmacologically and cited to ref 39. |
| Software: JMP | Confirmed, no version given |
| Data availability: on request from ogle@umn.edu | Confirmed |
| The low-resolution caption note | **CONFIRMED VERBATIM. The digitizer's claim that it is spurious is wrong.** |

### 3.1 The low-resolution note, exactly as published (p. 3)

> "The lowest level of CD31 expression is indicated by the bright green and the highest by the dark
> blue.**The resolution of all figures is low, but figure #1 is especially low.  We have attached the
> high resolution figure 1 here.**"

Note the missing space after "dark blue." and the two non-breaking spaces — consistent with an
unremoved author-to-editor note, not with fabrication. **A high-resolution Figure 1 exists and is the
most valuable of the four asks to Ogle.**

---

## 4. Variance — confirmed absent, with one qualification

**This is the item bearing on our σ_rel = 0.25 choice, and the answer is that the paper cannot help.**

- Zero occurrences of "standard deviation", "standard error", "SEM", "coefficient of variation" or
  "error bar" in the entire text.
- "±" appears **exactly twice**, both on p. 9, both for **CIV area, not CD31**: 81.29 ± 11.08% and
  30.26 ± 12.09%. Different assay, different readout, 3D not 2D.
- **Not a single numeric p-value appears in the paper.** Significance is asterisks only.
- Figure 2b has two columns, Parameter and Estimate. **No standard error, t-ratio, p-value, R²,
  RMSE, lack-of-fit test or ANOVA table is published** for the response surface, despite Methods
  saying ANOVA was conducted.
- Figs 1a, 2a, 3b, 4a–e have **no error bars**. Figs 5b/5c **do**, on 3D CD31 area, and the caption
  **never states what they represent**.
- No deposited dataset. Per-condition values exist only in the authors' hands.

**Precise form for our documents:** *no numeric CV, SD, SE or exact p-value is reported for the CD31
readout anywhere in the paper; Figs 1a/2a/3b/4a–e carry no error bars; Figs 5b/5c carry graphical
error bars of undefined type on a 3D CD31 area measure.*

**Consequence for σ_rel: unchanged.** The CV backed out of the figure boxes remains the only
available basis, and the paper confirms no published alternative exists. That is now a verified
absence rather than an assumed one — which is worth stating in the limitations section.

---

## 5. Things that change what we can claim

1. **The Matrigel comparison is transitive, not measured.** There is no Matrigel differentiation arm
   in this paper. The Abstract says EO induces differentiation "well beyond that found with
   Matrigel"; Results p. 5 reveals the chain — "significantly higher than on LN411 + FN, which was
   **previously shown** to be significantly better than Matrigel²⁸". Matrigel appears in this paper
   only for routine hiPSC maintenance. **Do not repeat the Abstract's framing.**

2. **The paper is internally inconsistent in at least four places**, not one: CIV 28 vs 56; VEGF
   10 vs 50 ng/mL; additive start day 0 vs day 1; TGFβ given as 5 µM, not a plausible unit for a
   growth factor. Plus a miscited figure and an unreplaced "X axis label" placeholder in Fig 1b.
   **Consequence: "Methods is the authoritative section" is not a safe default here — it is
   demonstrably no more reliable than Results, and on CIV the Results value is the one the published
   model corroborates.**

3. **Stage-1 screening rule, stated exactly** (p. 2–4): retained and doubled = C, CIV, LN411
   (significant, optimum at high); dropped = LN111, LN511 (significant, but optimum at zero);
   retained at unchanged range = FN (**not significant**, kept only because it is required for
   attachment).

4. **The DoE fit's aggregation is unspecified.** The paper never states whether the regression was
   fit on individual wells or condition means, how replicates were aggregated, or whether there was
   any blocking, randomization or run order. Relevant to any replay claim.

---

## 6. Needs your eyes

| what | where | why |
|---|---|---|
| **Supplementary Information** | doi.org/10.1038/s41598-025-09256-9 — **not in our PDF** | Figures S1–S3 are cited but unavailable. Could contain a stage-2 concentration table or JMP output that settles §1 by statement rather than inference. |
| **Figure 2a, top five columns** | p. 5 | Confirm by eye that the top conditions overlap. This closes §2.1 formally. |
| **Figure 2b** | p. 5 | Verify the twelve coefficients were transcribed correctly — the entire §1.2 reconstruction rests on them. |
| **A statistician on §1.2** | — | The Collagen IV reversal is an inference carrying a headline claim. It should not go in a paper unchecked. |

## 7. The four asks to Ogle, re-ranked

1. **The high-resolution Figure 1** — confirmed to exist, in the caption, in the published paper.
2. **The underlying per-condition data** — confirmed to exist nowhere else; no deposited dataset.
3. **Was the stage-1 Collagen IV high 28 or 56?** — the paper contradicts itself and cannot self-resolve.
4. **How was TheO obtained** — no profiler/desirability/canonical language anywhere; "prediction
   solution" is suggestive only.

*Question 2 in the earlier list — whether TheO came from the Profiler or the Solution table — is now
the least likely to be answered from documents alone and the most decisive if answered.*
