# Cross-check 3 — Hall, Lin & Ogle 2025, Sci Rep 15:24479
Source PDF: /Users/jy/BO/s41598-025-09256-9.pdf (15 pages, full text + all 5 figure rasters inspected)
Method: pypdf text extraction (plain + layout mode) for text/tables; embedded figure images extracted and read visually; dot-column counts verified programmatically.

---

### Item 1: Figures 1a and 2a are box-and-whisker plots with individual points overlaid, NOT bar charts
Source: p. 3 (Fig. 1a raster) and p. 5 (Fig. 2a raster), visual inspection of the embedded figure images
Finding: Fig. 1a is a box-and-whisker plot — 23 boxes with a horizontal median line, hinges, upper/lower whisker caps, and ~4–6 individual black data points overlaid inside each box; y-axis "CD31 Area/DAPI Area Normalized to FN", scale 0–4. Fig. 2a is the same construction — 25 boxes with median lines, whisker caps, and overlaid individual points; y-axis "CD31 Area/DAPI Area Normalized to FN", scale 0–9. Neither has a filled bar from the axis, and neither has an error bar. The captions do not name the plot type; they say only "Graphical representation of CD31 area per DAPI area normalized to the FN control" (Fig. 1a, p. 3) and "Graphical representation of CD31 staining per DAPI area normalized to the FN control" (Fig. 2a, p. 5).
Programmatic confirmation: the condition-heatmap dot row beneath Fig. 1a resolves to exactly 23 evenly spaced columns (x = 139…1495, pitch ≈ 61.7 px); beneath Fig. 2a, exactly 25 columns (x = 159…1652, pitch ≈ 62 px). These match Table 1 (23 runs) and Table 2 (25 runs) one-for-one.
Status: contradicts our record (our record is wrong; the "bar chart" description is incorrect — the paper's Fig. 1a/2a are box plots)
Action: correct the three documents that say "bar chart" for Fig 1a / Fig 2a. NOTE the likely source of the error: **Figure 5b and 5c ARE genuine bar charts** (mean bars with error bars plus overlaid points, p. 9) — see Item 14. If a document's "bar chart" claim was about Fig. 5, it is right; about Fig. 1a/2a, it is wrong.

---

### Item 1b (corroborating): shading levels in the condition heatmaps
Source: p. 3 Fig. 1a legend; p. 5 Fig. 2a legend
Finding: Fig. 1a legend is "1 / 0.5 / 0" and only one column (the 13th) uses the 0.5 grey — i.e. two-level factorial + a single centre point. Fig. 2a legend is also "1 / 0.5 / 0" and only three shades appear across all 25 columns — i.e. exactly three factor levels, which is what a face-centred (on-face) CCD produces, not the five levels of a rotatable CCD.
Status: resolved
Action: none — supporting evidence for Items 2 and 3

---

### Item 2: Stage 1 = 23 runs (22 factorial + 1 centre point)
Source: p. 2, Table 1 "Run pattern for factorial experiments"
Finding: Table 1 contains exactly 23 rows. 22 rows are all-± combinations of the six factors; exactly one row is `0 0 0 0 0 0` (the 13th row). Caption: "The run pattern for the factorial experiments, the first stage of the design of experiments.method for optimizing endothelial differentiation. (-) indicates the lowest concentration of the protein, (+) indicates the highest concentration of the protein, and (0) indicates the midpoint." Body text, p. 2: "One center point (000000 in Table 1) was added to the factorial experiments to account for nonlinear responses to ECM concentration."
Status: resolved
Action: none

---

### Item 3: Stage 2 = 25 runs (16 factorial + 8 axial + 1 centre), face-centred CCD
Source: p. 4, Table 2 "Run pattern for central composite design"; p. 4 body text
Finding: Table 2 contains exactly 25 rows. Classified: 16 rows with all four factors at ± (and these 16 are the complete 2^4 factorial — every one of the 16 sign combinations appears exactly once); 8 rows with one factor at ± and the other three at 0 (`0 0 - 0`, `0 0 0 +`, `0 - 0 0`, `- 0 0 0`, `+ 0 0 0`, `0 0 0 -`, `0 + 0 0`, `0 0 + 0`); and 1 centre row `0 0 0 0`. 16 + 8 + 1 = 25.
On the design name, the paper's exact phrase is "on face", not "face-centred": p. 4 — "An on face central composite design was used to add levels of ECM concentration for the four proteins brought through to this stage: C, CIV, LN411, and FN as shown in Table 2." Methods, p. 12: "In this stage, different levels of each protein were evaluated as shown in Table 2 using a central composite design."
Status: resolved
Action: if our documents write "face-centred central composite design", note that the paper's literal wording is "on face central composite design" (the design is the same thing; the term differs)

---

### Item 4: Stage 2 factors are Collagen I, Collagen IV, Laminin 411, Fibronectin
Source: p. 4, Results; p. 4, Table 2 caption
Finding: "An on face central composite design was used to add levels of ECM concentration for the four proteins brought through to this stage: C, CIV, LN411, and FN as shown in Table 2." Table 2 caption: "abbreviations used: collagen I (C), collagen IV (CIV), laminin 411 (LN411), fibronectin (FN)."
Status: resolved
Action: none

---

### Item 5: Response surface used "significant terms up to the 3rd order" — exact phrasing
Source: p. 4, Results
Finding: "Following this set of experiments, a regression analysis was performed to determine the coefficients of the response surface relating ECM exposure to CD31 expression based only on significant terms up to the 3rd order (Fig. 2)."
Second, near-identical statement in the Fig. 2 caption, p. 5: "(b) A table showing parameter estimates for significant terms in the model produced by stage 2 DOE results. Terms up to the third order were included."
Status: resolved
Action: none

---

### Item 6: Readout = CD31 area / DAPI area by immunofluorescence, day 10, normalized to fibronectin-only control
Source: p. 2 Results; p. 3 Fig. 1 caption; p. 12 Methods ("Endothelial differentiation in 2D culture", "Design of experiments approach"); p. 13 Methods ("Immunofluorescence and image analysis")
Finding: Four separate statements, all consistent.
- p. 2: "The response was defined as expression of the endothelial marker cluster of differentiation 31 (CD31) as detected by immunofluorescence."
- p. 3 Fig. 1a caption: "Graphical representation of CD31 area per DAPI area normalized to the FN control for the conditions indicated by the first stage of the DOE approach."
- p. 12: "Cells were analyzed at day 10 of differentiation." / "The response was the level of CD31 expression seen at day 10 of differentiation."
- p. 13: "CD31 area and DAPI area were determined for each image using FIJI (2.0.0-rc-68/1.52e). All data was normalized to the FN control for each experiment in order to account for interexperimental variability associated with stem cell differentiation."
Imaging detail (p. 13): "Cells were imaged on the Leica DMi8 microscope with a 10x objective. For all experiments, 3 × 3 tilescans were collected in the approximate center of each well."
Status: resolved
Action: none

---

### Item 7: At least 4 wells from at least 3 experimental replicates per condition
Source: p. 12, Methods, "Design of experiments approach"
Finding: "Data were collected from at least 4 wells from at least 3 experimental replicates."
Note what the paper does NOT state: this sentence sits in the stage-1 factorial paragraph. No per-condition n is given for stage 1, stage 2, Fig. 3 or Fig. 4 anywhere in the paper. Explicit n values appear only for the 3D bioprinting figure (Fig. 5): "(n = 6 for EO; n = 3 for the other conditions)" and "(bottom, left, n = 4)" / "(bottom right, n = 4)" (p. 9).
Status: resolved
Action: none, but flag that "at least 4 wells / at least 3 replicates" is a floor, never resolved to an actual n for any 2D condition

---

### Item 8: Fibronectin low = 22 µg/mL, lowest concentration giving good attachment
Source: p. 2, Results
Finding: "The low Fibronectin (FN) concentration was set to 22 µg/mL, which was the lowest concentration on which human induced pluripotent stem cells (hiPSCs) showed good attachment and survival. Without the added FN, attachment was very poor on some proteins of interest, which would have made analyzing their effects on differentiation impossible."
Restated p. 4: "…as again that was the lowest concentration of FN on which consistent cell attachment was seen."
Status: resolved
Action: none

---

### Item 9: Model could not evaluate fibronectin below 22 µg/mL
Source: p. 4, Results ("Validation of TheO"); p. 12, Methods
Finding: p. 4 — "Additionally, TheO without FN (TheO-FN) was evaluated as the model used did not allow for concentrations of FN below 22 µg/mL to be evaluated, as again that was the lowest concentration of FN on which consistent cell attachment was seen."
p. 12 — "Additionally, the TheO formulation was evaluated without FN as the DoE approach did not allow for the value to be set lower than the low FN concentration, and without C as its effect was predicted to be small."
Status: resolved
Action: none

---

### Item 10: TheO produced very little differentiation, around the level of fibronectin alone
Source: p. 4, Results ("Validation of TheO")
Finding: "Interestingly, the TheO formulation resulted in very little endothelial differentiation, around the level seen on FN alone (Fig. 3a, b). However, TheO-FN led to a high level of endothelial differentiation (Fig. 3a, b)."
Status: resolved
Action: none

---

### Item 11: Failure attributed to an on-face CCD not modelling outside the original parameter space
Source: p. 4, Results ("Validation of TheO")
Finding: "The fact that the TheO condition did not produce the expected result of high levels of differentiation could be attributed to several factors including the complexity of cell-ECM interactions or high variability in levels of differentiation. However, the reason for the discrepancy is likely due to use of an on face central composite design which does not allow for accurate modeling outside of the original parameter space."
Status: resolved
Action: none. Note the paper offers three candidate causes and picks the third; "high variability in levels of differentiation" is named by the authors as a candidate explanation but is neither quantified nor tested.

---

### Item 12: TheO minus FN ("EO") performed well; FN activates TGF-β, shown with inhibitor + add-back
Source: p. 5 Results; p. 8 Results ("The role of TGFβ signaling in EO-driven endothelial specification"); p. 10 Discussion
Finding (naming): p. 5 — "Due to the significant level of differentiation on TheO-FN compared to the other conditions, it will now be referred to as Endothelial Optimized or EO."
Finding (EO outperforms): p. 5 — "Differentiation on TheO-FN was also significantly higher than on LN411 + FN… TheO-FN also showed significantly more differentiation than was seen with the maximum concentration of all proteins (++++) or the maximum concentration of C, CIV, and LN411 without FN (+++-)."
Finding (FN → TGFβ mechanism): p. 8 — "FN is known to activate TGFβ signaling39 which has been shown to be detrimental to endothelial differentiation in other contexts40."
Finding (inhibitor): p. 8 — "the TGFβ inhibitor SB431542 (SB) was added beginning on day 0 of differentiation, when CHIR was first added. The addition of SB had no significant effect on endothelial differentiation on EO, which does not contain FN. However, differentiation was significantly improved on TheO which does contain FN (Fig. 4c)."
Finding (add-back): p. 8 — "TGFβ was then added to the differentiations on both ECMs starting on day 0. This addition had no significant effect on differentiation on TheO; however, differentiation on EO was significantly reduced (Fig. 4d). Together, these results indicate that the difference in endothelial differentiation on the TheO and EO ECM coatings is driven at least in part by FN activated TGFβ signaling, which inhibits ECM-guided endothelial specification."
Status: resolved
Action: none. Precision point: "FN is known to activate TGFβ signaling" is asserted with a literature citation (ref 39, Dallas et al. 2005) — the paper does not itself measure TGFβ activation (no pSMAD or reporter data); it infers involvement from the pharmacology.

---

### Item 13: Software used was JMP
Source: p. 12 Methods (twice); p. 13 Methods, "Statistics"
Finding: "JMP software was used to produce the experiment set, create contour plots, and identify statistically significant parameters and interactions." / "JMP software was used to fit the data, conduct ANOVA, and sort parameter estimates to identify the theoretical optimized ECM formulation (TheO)." / "Statistical Analysis was performed using JMP software."
No version number is given for JMP anywhere in the paper. (FIJI versions ARE given: 2.0.0-rc-68/1.52e for 2D, 2.14.0/1.54f for 3D.)
Status: resolved
Action: none

---

### Item 14: Is ANY coefficient of variation, SD, or SE reported for the CD31 readout? (WE BELIEVE NONE)
Source: whole-paper text search + visual inspection of every figure panel
Finding — text: exhaustive search of the extracted full text returns **zero** occurrences of "standard deviation", "standard error", "SEM", "S.E.", "coefficient of variation", or "error bar". The character "±" appears exactly **twice** in the entire paper, both on p. 9 and both for **CIV area, not CD31**: "While most of the area on the EO side was CIV positive as expected (81.29 ± 11.08%, Fig. 5c, bottom left; 5d, top row), the control side also showed substantial CIV deposition (30.26 ± 12.09%) at the end of the culture period." No dispersion statistic of any kind is reported numerically for CD31 anywhere.
Finding — no exact p-values: not a single numeric p-value appears in the paper. Significance is reported only as asterisk thresholds ("* p < 0.05 ** p < 0.01 *** p < 0.001") in the captions of Figs. 3, 4 and 5, and as a decision rule in Methods ("Significance was defined as p < 0.05 for all experiments").
Finding — Fig. 2b table has no uncertainty column: the stage-2 parameter-estimate table (p. 5) has exactly two columns, "Parameter" and "Estimate". There is no standard error, t-ratio, p-value, R², RMSE, or ANOVA table published for the response-surface model.
Finding — figure error bars: Figs. 1a, 2a, 3b and 4a–4e carry **no error bars at all** (box plots; the whiskers are distributional, not error). **Fig. 5b and 5c DO carry error bars** — these panels are bar charts with a mean bar, a vertical error bar, and overlaid individual points. Fig. 5b's leftmost panel plots "CD31 Area (Normalized to No ECM Ctrl)" and Fig. 5c's right panel plots "CD31 (area %)". **The Fig. 5 caption never states what those error bars represent** (SD, SEM, or CI) — verbatim caption text is only "…for bioprinted constructs with different ECM formulations (n = 6 for EO; n = 3 for the other conditions). * p < 0.05 ** p < 0.01 *** p < 0.001."
Status: **resolved with an important qualification** — our belief is correct for the DoE / 2D CD31 readout (Figs. 1–4): no CV, SD, SE or exact p is reported, in text or graphically. It is NOT strictly true that no dispersion appears anywhere for CD31: Fig. 5b/5c show undefined graphical error bars on a CD31 area measure in bioprinted constructs. Numerically, still nothing.
Action: update our documents to the precise form: "no numeric CV/SD/SE and no exact p-value is reported for the CD31 readout anywhere in the paper; Figs. 1a, 2a, 3b, 4a–e have no error bars; Fig. 5b/5c show graphical error bars of undefined type on 3D CD31 area."

---

### Item 15: Data availability — on reasonable request from corresponding author (ogle@umn.edu)
Source: p. 13, "Data availability"
Finding: "Data for the current manuscript will be provided on reasonable request and requests can be made to the corresponding author, Brenda Ogle, ogle@umn.edu."
Corroborating, p. 1 footnote: "email: ogle@umn.edu". p. 15: "Correspondence and requests for materials should be addressed to B.M.O."
Status: resolved
Action: none

---

### Item 16: Figure 1 caption contains a leftover note to the editor about low-resolution figures
Source: p. 3, end of the Fig. 1 caption
Finding — VERBATIM, reproduced exactly as it appears (note it runs on directly from the preceding sentence with no space after "dark blue.", and contains two non-breaking spaces, shown here as ␣):
"The lowest level of CD31 expression is indicated by the bright green and the highest by the dark blue.The resolution of all figures is low, but figure #1 is especially low.␣ We have attached the high resolution figure 1␣here."
The note itself, isolated: **"The resolution of all figures is low, but figure #1 is especially low.  We have attached the high resolution figure 1 here."**
Layout-mode extraction of p. 3 renders it as two caption lines:
`level of CD31 expression is indicated by the bright green and the highest by the dark blue.The resolution of all`
`figures is low, but figure #1 is especially low.\xa0 We have attached the high resolution figure 1\xa0here.`
Status: **resolved — the note is REAL and is present in the published PDF.** The third-party digitizer's claim that it is spurious/fabricated is wrong.
Action: no change needed to our record; push back on the digitizer with the two-line layout extraction above as evidence

---

## ALSO EXTRACTED

### Stage-1 screening outcome — which proteins retained, which dropped, on what basis
Source: pp. 2–4, Results
Finding (verbatim, contiguous): "These estimates showed that C, CIV, and LN411 had positive and significant associations with CD31 expression with the highest levels of CD31 expression corresponding to the highest concentrations of these proteins. Thus, the high concentration of these proteins was increased by a factor of 2 for the subsequent response surface regression. LN111 and LN511 also showed significant associations with CD31 expression. However, the maximum expression occurred at the lowest concentrations of these proteins, which was set to 0, so these proteins were eliminated. The trend for FN was similar to the first group of proteins, with the highest differentiation seen at the highest FN concentrations. However, because this association was not significant the high concentration of FN was kept the same."
Summary of the rule actually applied: RETAINED and range-doubled = C, CIV, LN411 (significant + optimum at high). DROPPED = LN111, LN511 (significant but optimum at the zero level). RETAINED at unchanged range = FN (non-significant, but kept because it is required for attachment — see Item 8).
Also, p. 2: "The factorial experiments were analyzed up to 2nd order interactions which were graphed in contour plots (Fig. 1)."
Status: resolved

### Reported significance values and named model terms for the response surface
Source: p. 5, Fig. 2b, 2c, 2d
Finding: **No p-values, no standard errors, no t-ratios are published for any model term.** Fig. 2b gives point estimates only, verbatim:
Intercept 2.724 | C 0.007 | CIV 0.079 | LN411 0.736 | FN −0.131 | CIV*LN411 −0.078 | CIV*FN −0.087 | C*C −0.626 | LN411*LN411 −0.492 | FN*FN 0.036 | CIV*LN411*LN411 −1.442 | CIV*FN*FN 1.435
(12 terms including intercept; three third-order terms are absent — no C*C*C, no FN*FN*FN, no three-way cross terms other than the two listed.)
Fig. 2c "Main Effect": LN411 0.564 | CIV 0.025 | FN 0.025 | C 0.077
Fig. 2d "Total Effect": LN411 0.721 | CIV 0.218 | FN 0.177 | C 0.092
Narrative reading of these, p. 4: "This prediction solution of 35.6 µg/mL C, 67.2 µg/mL CIV, 0.9 µg/mL LN411, and 22 µg/mL FN is the Theoretical Optimized formulation (TheO), with the concentrations of CIV and LN411 having the largest effect sizes and FN having a medium effect size. While the concentration of C was predicted to be significant, the effect size was predicted to be small."
Status: resolved. Note the ranking in that sentence matches the TOTAL effect panel (2d), not the MAIN effect panel (2c) — in 2c, C (0.077) exceeds both CIV (0.025) and FN (0.025). The paper does not state which panel it is describing.

### Does the paper compare to Matrigel directly, or cite earlier work?
Source: p. 1 Abstract; p. 5 Results; p. 10 Discussion; p. 11 Methods
Finding: **There is no Matrigel arm in any experiment in this paper.** The Matrigel comparison is transitive, through the authors' own earlier paper (ref 28, Hall et al. Stem Cell Reports 2022).
- Abstract, p. 1, states it as though direct: "We found that a combination of Collagen I, Collagen IV, and Laminin 411 could induce endothelial differentiation well beyond that found with Matrigel, the most commonly used differentiation substrate for endothelial cells."
- Results, p. 5, states the chain explicitly: "Differentiation on TheO-FN was also significantly higher than on LN411 + FN, which was previously shown to be significantly better than Matrigel28."
- Discussion, p. 10: "As we previously demonstrated that LN411 + FN outperformed Matrigel in inducing differentiation28 EO represents a significant advancement, providing a defined and efficient alternative for endothelial differentiation."
- Introduction, p. 2: "In our previous work, we found that Laminin 411 coating resulted in significantly more endothelial differentiation than Matrigel or Laminin 11128."
- Matrigel IS used in this paper, but only for routine hiPSC maintenance (Methods, p. 11: "were maintained on Matrigel (Corning, cat# 354277) coated plates at 37 °C"), never as a differentiation-substrate comparator.
Status: resolved
Action: flag the Abstract wording — the "well beyond that found with Matrigel" claim is transitive via ref 28 and is not measured in this study. This is an IMPLICATION, not a STATEMENT of a direct comparison.

### Statements about experimental variability / plate-to-plate normalization
Source: p. 13 Methods; p. 4 Results; p. 13 Methods "Statistics"
Finding (normalization): "All data was normalized to the FN control for each experiment in order to account for interexperimental variability associated with stem cell differentiation." (p. 13). This is per-experiment, not per-plate; the paper never uses the words "plate", "batch", or "block" in a normalization sense, and does not state whether an FN control well was present on every plate.
Finding (variability acknowledged, unquantified): "…could be attributed to several factors including the complexity of cell-ECM interactions or high variability in levels of differentiation." (p. 4)
Finding (variance handling in tests): "For all experiments, the assumption of equal variance was tested using a Bartlett test. If p > 0.05, ANOVA followed by a Tukey's post hoc test were used to determine significance. If p < 0.05, Welch's test followed by the Games-Howell test (Tukey HSD with Welch's correction for unequal variance) were used. Significance was defined as p < 0.05 for all experiments." (p. 13)
Not stated in the paper: how replicate wells were aggregated (well-level vs. condition-median), whether the DoE regression was fit on individual wells or on condition means, randomization or run order, blinding, or any blocking on experimental replicate. None of these are mentioned anywhere.
Status: resolved

---

## ADDITIONAL FINDINGS NOT ASKED FOR — internal inconsistencies in the paper (report only, do not correct)

### A. Stage-1 HIGH concentration of Collagen IV is stated as two different values
Source: p. 2 Results vs. p. 12 Methods
Finding — Results, p. 2: "The high concentrations were set based on literature values for ECM coating for cell culture applications to 35.5 µg/mL, 28 µg/mL, 15.8 µg/mL, 0.8 µg/mL, 0.8 µg/mL, and 75 µg/mL for C, CIV, LN111, LN411, LN511, and FN respectively." → CIV high = **28 µg/mL**.
Finding — Methods, p. 12: "…was set to either a low (0,0,0,0,0,22 µg/mL) or high (35.5, 56, 15.8, 0.8, 0.8, 75 µg/mL) level respectively." → CIV high = **56 µg/mL**.
Observation (not a correction): the predicted TheO CIV concentration is 67.2 µg/mL (p. 4). Since stage-2 doubled the stage-1 high for C, CIV and LN411, 28 → 56 would cap stage-2 CIV at 56 µg/mL, below the reported optimum; 56 → 112 would contain it.
Status: contradicts our record IF our record cites a single CIV high value without noting the conflict
Action: manual check needed — decide which value our documents use and footnote the conflict

### B. VEGF pre-incubation concentration stated as two different values
Source: p. 5 Results vs. p. 12 Methods
Finding — Results, p. 5: "…10 ng/mL VEGF was added to wells coated with ECM, incubated for 30 min at room temperature, and washed prior to adding hiPSCs."
Finding — Methods, p. 12: "Additionally, 50 ng/mL VEGF was incubated with the ECM coating for 30 min at room temperature (VEGF incubation)."
Status: unresolved (paper is internally inconsistent)
Action: manual check needed

### C. Start day for SB / VEGF / TGFβ media additions stated as two different days
Source: pp. 5, 8 and Fig. 4 caption vs. p. 12 Methods
Finding — Results/captions repeatedly say day 0: "the TGFβ inhibitor SB431542 (SB) was added beginning on day 0 of differentiation, when CHIR was first added" (p. 8); "TGFβ was then added to the differentiations on both ECMs starting on day 0" (p. 8); Fig. 4b/4c/4d captions all say "on day 0 of differentiation".
Finding — Methods, p. 12: "SB431542 (SB)…, Vascular Endothelial Growth Factor (VEGF)…, and Transforming Growth Factor β (TGFβ)… were added to the media with every media change beginning on day 1 of differentiation…"
Also within the same Methods sentence, the ECM add-back day differs from the Results: Methods p. 12 says "additional ECM proteins matching the ECM coating were added to the media on Day 1 of differentiation", while Results p. 8 says "ECM matching the original coating was added to the media on the first day of CHIR treatment" and the Fig. 4b caption says "added on day 0 of differentiation".
Status: unresolved (paper is internally inconsistent)
Action: manual check needed

### D. TGFβ concentration given in molar units
Source: p. 12, Methods
Finding: "…were added to the media with every media change beginning on day 1 of differentiation at concentrations of 2µM, 50ng/mL, and 5µM respectively." — i.e. TGFβ is stated as 5 µM (SB 2 µM, VEGF 50 ng/mL).
Status: unresolved — reported as written; the paper gives no ng/mL equivalent for TGFβ
Action: manual check needed if our documents restate the TGFβ dose

### E. Internal figure cross-reference error
Source: p. 13, Methods, "Immunofluorescence and image analysis"
Finding: "CIV staining was also imaged with a 4x objective to provide better visualization of ECM distribution (Fig. 4d, top row)." The CIV dual-construct images are Fig. **5**d, top row (p. 9 caption), not Fig. 4d (which is a TGFβ box plot).
Status: resolved (paper typo)
Action: none unless our documents inherited the wrong reference

### F. Figure 4 caption typo
Source: p. 7, Fig. 4c caption
Finding: "…with and without the addition of the TGBβ inhibitor SB…" — "TGBβ" for "TGFβ".
Status: resolved (paper typo)
Action: none

### G. What the stage-2 model does NOT report
Source: p. 5 Fig. 2; p. 12 Methods
Finding: Methods states "JMP software was used to fit the data, conduct ANOVA, and sort parameter estimates" (p. 12), but no ANOVA table, F-statistic, R², adjusted R², RMSE, lack-of-fit test, or residual analysis is published anywhere in the paper or referred to in the Supplementary Information listing. The only model output shown is Fig. 2b/2c/2d.
Status: resolved (silence confirmed, not inferred)
Action: none

### H. Supplementary figures referenced but not in this PDF
Source: pp. 8, 9, 10, 15
Finding: Figure S1 (VEGF added in media from Day 0), Figure S2 (no CIV on control side just after printing / before differentiation), and Figure S3 (CIV-positive area of the control side vs. EO side) are cited in the text. "Supplementary Information The online version contains supplementary material available at https://doi.org/10.1038/s41598-025-09256-9" (p. 15). The supplementary file is not part of the PDF audited here.
Status: unresolved — cannot verify supplementary content from this file
Action: manual check needed if any of our claims rest on S1–S3

### I. Received / accepted dates and funding (for provenance fields)
Source: p. 13, p. 15
Finding: "Received: 16 April 2025; Accepted: 26 June 2025". Funding: "National Heart Lung and Blood Institute R01 HL137204, R01 HL160779, and T32 HL007741." Competing interests: "The authors declare no competing interests."
Status: resolved
