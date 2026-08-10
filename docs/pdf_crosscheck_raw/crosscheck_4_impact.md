# Cross-check 4 — Claims impact & variance
Source: Hall ML, Lin W-H, Ogle BM. *Optimizing extracellular matrix for endothelial differentiation using a design of experiments approach.* Sci Rep (2025) 15:24479. DOI 10.1038/s41598-025-09256-9. PDF read in full (15 pp., text + all figure images extracted).

Legend used throughout: **[STATES]** = paper's own words. **[IMPLIES]** = follows closely from the paper's words/numbers. **[INFER]** = our reasoning on top of the paper; not the paper's claim.

---

## 1. VARIANCE AND REPLICATION

### Item: Published coefficient of variation for the CD31/DAPI readout
Source: whole paper (searched all 15 pages for "CV", "coefficient of variation", "standard deviation", "standard error", "SEM", "s.d.", "error bar", "±")
Finding: **No coefficient of variation, standard deviation, standard error, or variance estimate is reported anywhere for the 2D CD31 area/DAPI area readout.** The strings "coefficient of variation", "standard deviation", "standard error", "SEM", and "error bar" do not occur in the article. Not stated.
Status: resolved (definitively absent)
Action: sigma_rel = 0.25 cannot be cited to this paper. Any document claiming a paper-derived CV must be corrected to say the CV was back-computed from digitized Fig. 1a/2a box plots — see item below for what the paper *does* license.

### Item: Only ± values printed anywhere in the paper
Source: p. 9, Results, "EO ECM validation in 3D"
Finding: "While most of the area on the EO side was CIV positive as expected (81.29 ± 11.08%, Fig. 5c, bottom left; 5d, top row), the control side also showed substantial CIV deposition (30.26 ± 12.09%) at the end of the culture period."
Status: resolved — these are the ONLY numeric ± values in the article. **What the ± represents (SD vs SEM vs CI) is not stated.** These are CIV-positive *area fractions in cryosectioned 3D bioprinted constructs* (n = 4), a different assay, different readout, and different dimensionality from the 2D CD31/DAPI DoE oracle.
Status: unresolved (for our purpose)
Action: do NOT use as support for sigma_rel. If cited at all, cite as "the only dispersion figures in the paper, from a different assay, with the ± undefined." (Arithmetically 11.08/81.29 = 13.6% and 12.09/30.26 = 40.0%, but this is **[INFER]** and cross-assay.)

### Item: n per condition — DoE stages 1 and 2 (the data our oracle is fit to)
Source: p. 12, Methods, "Design of experiments approach"
Finding: "The response was the level of CD31 expression seen at day 10 of differentiation. **Data were collected from at least 4 wells from at least 3 experimental replicates.**"
Status: resolved — this is the paper's only replication statement, and it is a lower bound ("at least"), not an n.
Note **[IMPLIES]**: the sentence is ambiguous between (i) ≥4 wells *in total*, drawn from ≥3 independent experiments, and (ii) ≥4 wells *per* experiment × ≥3 experiments (≥12 wells). Figure reading favors (i): Fig. 1a and Fig. 2a boxes carry ~4–6 overlaid points each (one condition in Fig. 2a, the all-low/FN condition, carries ~10). The paper does not say whether a plotted point is a well or an experiment mean. Not stated.
Action: our record may state n ≈ 4–6 per condition **only** with the qualifier "≥4 wells across ≥3 experimental replicates (paper's wording); point-level unit not stated."

### Item: n per condition — validation (Fig. 3) and signaling (Fig. 4) experiments
Source: Fig. 3 caption (p. 6), Fig. 4 caption (p. 7), Methods p. 12
Finding: **No n is given for Fig. 1, Fig. 2, Fig. 3, or Fig. 4** — not in the captions, not in Methods, not in Results. The "at least 4 wells / at least 3 experimental replicates" sentence appears only under "Design of experiments approach" and does not explicitly extend to the validation or signaling experiments. Not stated.
Status: resolved (absent)
Action: any record asserting n for TheO/EO validation must be marked figure-derived (~5–6 points per box in Fig. 3b).

### Item: n per condition — 3D bioprinting only
Source: Fig. 5 caption, p. 9
Finding: "(b) Graphical representation of CD31 area ratio, total vessel length per area, and branch point per area for bioprinted constructs with different ECM formulations (**n = 6 for EO; n = 3 for the other conditions**)." and "…graphical representation of CIV area ratio for the EO side and the no ECM control side of the dual component constructs (bottom, left, **n = 4**), as well as CD31 area ratio … (bottom right, **n = 4**)."
Status: resolved — Fig. 5 is the ONLY figure in the paper with a stated n. It is the 3D bioprinting figure, not the DoE.
Action: none (out of scope for the oracle).

### Item: What the error bars / graphical elements represent
Source: Figs. 1a, 2a, 3b, 4a–e captions
Finding: Every caption says only "Graphical representation of CD31 area per DAPI area normalized to the FN control…". **No caption defines the plot type, the box, the whiskers, the centre line, or the overlaid points.** Not stated.
Status: resolved (absent) — but note **[IMPLIES]** from the figure images themselves: the plots ARE box-and-whisker plots with individual data points overlaid (visible in extracted Figs. 1a, 2a, 3b, 4a–e). Whisker convention (min/max vs 1.5·IQR) is not stated; the whiskers appear to terminate on the extreme individual points, i.e. min/max.
Action: our record may say "box plots, min/max whiskers apparent, convention not stated by the authors."

### Item: Normalization to the fibronectin control — why it was done
Source: p. 13, Methods, "Immunofluorescence and image analysis"
Finding: "CD31 area and DAPI area were determined for each image using FIJI (2.0.0-rc-68/1.52e). **All data was normalized to the FN control for each experiment in order to account for interexperimental variability associated with stem cell differentiation.**"
Status: resolved — this is the paper's explicit, and only, statement about experimental variability, and it is qualitative.
Action: **This is directly load-bearing for the oracle.** The published response is a *ratio to a per-experiment FN control*. Two consequences **[INFER]**: (a) the reported spread already has the between-experiment (plate-to-plate) component partially divided out, so a CV read off the box plots understates raw assay variability but is the right scale for the published response surface; (b) the FN-alone condition is by construction ≈ 1.0 with its own sampling noise, and dividing by a noisy denominator inflates the variance of every other condition. Neither point is made by the authors.

### Item: Plate-to-plate normalization procedure — mechanics
Source: p. 13, Methods
Finding: The paper states the normalization target ("the FN control for each experiment") but does **not** state whether the divisor was the FN-control mean, median, or a single well; does not state how many FN wells per experiment; does not state whether normalization was per plate or per experiment-day. Not stated.
Status: unresolved
Action: manual check needed (would require the authors' raw data, which is not deposited — see Data availability).

### Item: Technical wells vs biological/experimental replicates
Source: p. 12 Methods; p. 13 Methods
Finding: The only distinction drawn is "**wells**" vs "**experimental replicates**" ("at least 4 wells from at least 3 experimental replicates"). Imaging sampling is stated: "For all experiments, 3 × 3 tilescans were collected in the approximate center of each well." (p. 13). A single iPSC line was used throughout: "hiPSCs (CCND2, … male) … hiPSCs were used between passages 40–70" (p. 11). **No variance decomposition into technical vs biological components is given.** Not stated.
Status: resolved (absent)
Action: our record should note the benchmark's noise model is single-cell-line, single-lab.

### Item: Variance-related statistical procedure
Source: p. 13, Methods, "Statistics"
Finding: "Statistical Analysis was performed using JMP software. For all experiments, **the assumption of equal variance was tested using a Bartlett test. If p > 0.05, ANOVA followed by a Tukey's post hoc test were used to determine significance. If p < 0.05, Welch's test followed by the Games-Howell test (Tukey HSD with Welch's correction for unequal variance) were used.** Significance was defined as p < 0.05 for all experiments."
Status: resolved
Action: **Relevant to the oracle's noise model.** The authors explicitly anticipated *heteroscedastic* data (they pre-specified a Welch/Games-Howell branch) but never report which branch was taken for any figure. A constant sigma_rel is a modelling choice the paper neither supports nor forbids; the box plots show visibly larger absolute spread at higher means. Note this as a limitation rather than claiming paper support.

### Item: Raw data availability
Source: p. 13, "Data availability"
Finding: "Data for the current manuscript will be provided on reasonable request and requests can be made to the corresponding author, Brenda Ogle, ogle@umn.edu."
Status: resolved — **no deposited dataset.** Per-condition numeric values exist only in the authors' hands.
Action: if the true variance matters to the benchmark's credibility, emailing the corresponding author is the only route to a real CV.

---

## 2. WHY TheO FAILED — EXTRAPOLATION OR DESIGN BOUNDARY?

### Item: The authors' own explanation for TheO's failure (the key sentence)
Source: p. 4, Results, "Validation of TheO"
Finding: "Interestingly, the TheO formulation resulted in very little endothelial differentiation, around the level seen on FN alone (Fig. 3a, b). However, TheO-FN led to a high level of endothelial differentiation (Fig. 3a, b). The fact that the TheO condition did not produce the expected result of high levels of differentiation could be attributed to several factors including **the complexity of cell-ECM interactions or high variability in levels of differentiation**. However, **the reason for the discrepancy is likely due to use of an on face central composite design which does not allow for accurate modeling outside of the original parameter space.**"
Status: resolved
Action: This is the *only* causal explanation the paper offers. Note it offers three candidates and endorses one. Also note "high variability in levels of differentiation" is the paper's second qualitative acknowledgement of noise (see §1) — it is offered as a *rejected/secondary* explanation, not quantified.

### Item: The design-boundary statement — fibronectin pinned at 22 µg/mL (Results)
Source: p. 4, Results, "Validation of TheO"
Finding: "Additionally, TheO without FN (TheO-FN) was evaluated as **the model used did not allow for concentrations of FN below 22 µg/mL to be evaluated**, as again that was the lowest concentration of FN on which consistent cell attachment was seen. **Since the TheO formulation indicated the lowest FN concentration would lead to the highest CD31 expression** and the relatively high concentrations of other proteins could allow for sufficient cell survival on the coating, TheO-FN was included to determine the necessity of FN inclusion in the formulation."
Status: resolved — **this is explicit, unambiguous design-boundary language, and it explicitly says the model's FN optimum sat at the lowest evaluable FN level.**
Action: this sentence is the strongest single piece of evidence in the paper on the (a)-vs-(b) question.

### Item: The design-boundary statement — restated in Methods
Source: p. 12, Methods, "Design of experiments approach"
Finding: "Additionally, the TheO formulation was evaluated without FN as **the DoE approach did not allow for the value to be set lower than the low FN concentration**, and without C as its effect was predicted to be small."
Status: resolved (corroborates the Results statement)
Action: none.

### Item: Why the FN floor of 22 µg/mL existed at all
Source: p. 2, Results, first paragraph
Finding: "For Collagen I (C), CIV, LN111, LN411, and LN511 the low concentration was set to 0. **The low Fibronectin (FN) concentration was set to 22 µg/mL, which was the lowest concentration on which human induced pluripotent stem cells (hiPSCs) showed good attachment and survival. Without the added FN, attachment was very poor on some proteins of interest, which would have made analyzing their effects on differentiation impossible.**"
Status: resolved — the boundary was a deliberate, biologically motivated constraint, present in **both** DoE stages.
Action: **Important consequence [IMPLIES]: FN = 0 was never a sampled point in either the factorial or the CCD stage. EO (= TheO−FN, FN = 0) therefore lies strictly outside the entire DoE design space.**

### Item: The fitted model itself — parameter estimates (Fig. 2b)
Source: Fig. 2b, p. 5 (table image; text is legible in the extracted figure)
Finding (verbatim table): Intercept 2.724; C 0.007; CIV 0.079; LN411 0.736; **FN −0.131**; CIV*LN411 −0.078; CIV*FN −0.087; C*C −0.626; LN411*LN411 −0.492; FN*FN 0.036; CIV*LN411*LN411 −1.442; CIV*FN*FN 1.435.
Fig. 2c "Main Effect": LN411 0.564, CIV 0.025, FN 0.025, C 0.077. Fig. 2d "Total Effect": LN411 0.721, CIV 0.218, FN 0.177, C 0.092.
Status: resolved — **the complete fitted model is published and machine-usable.**
Action: high-value. Record that the response surface is fully recoverable from Fig. 2b without digitization.

### Item: Where the published model's optimum actually sits relative to the design box — **[INFER]**
Source: our numerical maximization of the Fig. 2b polynomial over the coded cube [−1,1]^4, cross-checked against the TheO concentrations stated on p. 4.
Finding: the constrained argmax of the published model is at coded **C = 0.00, CIV = +1.00, LN411 = +0.18, FN = −1.00** (predicted response 4.55). Mapping back: C coded 0 → midpoint of a 0–71 µg/mL range = **35.5**, paper reports **35.6** ✓; LN411 coded +0.18 → 0.80 + 0.18(0.80) = **0.94**, paper reports **0.9** ✓; FN coded −1 → **22 µg/mL** (the stated FN low bound), paper reports **22** ✓; CIV coded +1 → the CIV upper bound, paper reports **67.2**.
Status: **contradicts our record** (if our record says TheO failed because it was an extrapolated prediction outside the tested range).
Interpretation, clearly labelled: **[INFER]** TheO is the *constrained* maximum of the fitted surface *inside* the design box, sitting on **two** faces of it — FN at its lower bound and CIV at its upper bound — with C and LN411 interior. It is not an extrapolation. The confidence in this inference rests on the coded-unit assumption, which is independently corroborated by three exact matches (C, LN411, FN) between our constrained argmax and the paper's stated TheO values.
Action: update whichever downstream document asserts explanation (a) EXTRAPOLATION. Explanation (b) DESIGN-BOUNDARY is the one the numbers support, and it is stronger than currently framed: **two** factors were pinned at bounds, not just fibronectin.

### Item: Verdict on which explanation the paper's own text supports
Source: p. 2, p. 4 (×2), p. 12
Finding / verdict:
- The paper **STATES** the design-boundary constraint explicitly and twice, and states that the model's own FN optimum was at the lowest evaluable FN ("the TheO formulation indicated the lowest FN concentration would lead to the highest CD31 expression"). Explanation (b) is **directly supported by the paper's text**.
- The paper's *one* sentence naming a cause — "an on face central composite design which does not allow for accurate modeling outside of the original parameter space" — uses extrapolation *language*, but it does **not** say that TheO's predicted coordinates were outside the tested range. Read together with the FN sentences, the natural reading is: the design could not model the region (FN < 22) where the real optimum lay. Under that reading (a) and (b) are the **same claim**, not competitors.
- The paper **nowhere states** that the predicted optimum fell outside the tested concentration ranges. A pure-(a) claim — "the fitted surface predicted an optimum outside the tested range" — is **not supported by the paper's text and is contradicted by the paper's own numbers** (previous item).
Status: contradicts our record (for pure-(a) framings); resolved in favour of (b).
Action: rewrite the TheO-failure claim as: *the model's optimum was pinned to the boundary of a design region that biologically could not include the true optimum (FN = 0); the authors attribute the failure to the on-face CCD's inability to model outside that region.* Quote both the p. 4 boundary sentence and the p. 4 on-face-CCD sentence.

### Item: The mechanistic follow-up the authors provide for *why* FN hurts
Source: p. 8, "The role of TGFβ signaling…"; p. 10, Discussion
Finding: "Together, these results indicate that **the difference in endothelial differentiation on the TheO and EO ECM coatings is driven at least in part by FN activated TGFβ signaling, which inhibits ECM-guided endothelial specification.**" (p. 8) and "While SB minimally affected differentiation on EO, it significantly enhanced differentiation on TheO, **implicating TGFβ as a factor in the latter's reduced differentiation efficiency.**" (p. 10)
Status: resolved
Action: this is a *third*, biological explanation for TheO's low performance that sits alongside the design-boundary one. If our record frames TheO's failure as purely a DoE artifact, note that the authors also give a signaling mechanism. Optional addition, not a contradiction.

---

## 3. THINGS THAT ACTIVELY CONTRADICT

### Item: Internal contradiction in the paper — Collagen IV high concentration (28 vs 56 µg/mL)
Source: p. 2 Results vs p. 12 Methods
Finding (Results, p. 2): "The high concentrations were set based on literature values for ECM coating for cell culture applications to 35.5 µg/mL, **28 µg/mL**, 15.8 µg/mL, 0.8 µg/mL, 0.8 µg/mL, and 75 µg/mL for C, CIV, LN111, LN411, LN511, and FN respectively."
Finding (Methods, p. 12): "the concentration of each ECM protein (C, CIV, LN111, LN411, LN511, FN) was set to either a low (0,0,0,0,0,22 µg/mL) or high (35.5, **56**, 15.8, 0.8, 0.8, 75 µg/mL) level respectively."
Status: **contradicts** — the paper contradicts itself on the stage-1 CIV high level by a factor of 2.
Action: manual check needed. Flag in our record; do not silently pick one. Note **[INFER]**: neither value doubles to the 67.2 µg/mL that TheO reports for CIV (2 × 28 = 56; 2 × 56 = 112), so the CIV ladder cannot be reconstructed consistently from the paper.

### Item: Stage-2 (CCD) concentrations are never given in physical units
Source: p. 4 Results; Table 2, p. 4; p. 12 Methods
Finding: The only statement is (p. 2/4) "Thus, **the high concentration of these proteins was increased by a factor of 2** for the subsequent response surface regression" and (p. 12) "different levels of each protein were evaluated **as shown in Table 2** using a central composite design." Table 2 contains only −, 0, + symbols. **No µg/mL values for the stage-2 design are stated anywhere.**
Status: **contradicts** any record claiming the stage-2 design matrix is recoverable in physical units.
Action: update the record. Combined with the CIV 28/56 contradiction, the stage-2 CIV axis in µg/mL is genuinely unrecoverable from the paper.

### Item: Figure 1 caption contains an un-removed note to the editor
Source: Fig. 1 caption, p. 3
Finding: "…The lowest level of CD31 expression is indicated by the bright green and the highest by the dark blue. **The resolution of all figures is low, but figure #1 is especially low. We have attached the high resolution figure 1 here.**"
Status: resolved — the note is in the published caption. There is **no file attachment embedded in the PDF** (checked: the PDF's attachment list is empty). The "high resolution figure 1" is not obtainable from this PDF.
Action: none required, but supports the team-lead note; treat Fig. 1 as the low-resolution version.

### Item: Figure 1b contour plots carry placeholder axis labels
Source: Fig. 1b, p. 3 (extracted image)
Finding: The panel-b axis labels read literally "**Y axis label**" (top) and "**X axis label**" (left). The contour tiles carry no numeric axis ticks and the colour legend is qualitative ("high"/"low", "CD31 expression").
Status: resolved
Action: **Fig. 1b is not digitizable.** Any downstream claim that the stage-1 contour surfaces were or can be extracted quantitatively must be dropped. (Fig. 1a and Fig. 2a box plots remain digitizable; Fig. 2b is a numeric table.)

### Item: TheO's collagen I level is *not* a maximum
Source: p. 4 Results; validated by our coded-unit mapping
Finding: "This prediction solution of **35.6 µg/mL C, 67.2 µg/mL CIV, 0.9 µg/mL LN411, and 22 µg/mL FN** is the Theoretical Optimized formulation (TheO), with the concentrations of CIV and LN411 having the largest effect sizes and FN having a medium effect size. While the concentration of C was predicted to be significant, the effect size was predicted to be small."
Status: resolved — note the CIV/LN411/FN effect-size ordering in this sentence **disagrees with Fig. 2c/2d**, where LN411 dominates (main 0.564, total 0.721), CIV is second on total effect (0.218) but near-zero on main effect (0.025), FN third (0.177), C last (0.092). The text's "CIV and LN411 having the largest effect sizes" is only true of the *total* effect panel.
Status: contradicts (minor, internal)
Action: if our record cites an effect-size ranking, cite Fig. 2c/2d numbers, not the prose.

---

## 4. PHASE 2 ("REPLAY THE STUDY WITH BO") — WHAT GETS STRONGER OR WEAKER

### Item: Are per-condition values recoverable?
Source: Figs. 1a, 2a, 3b, 4a–e (extracted images); Data availability p. 13
Finding: **Partially, and only by digitization.** Fig. 1a (stage 1, ~23 box plots matching Table 1's 23 runs) and Fig. 2a (stage 2, ~24–25 box plots; Table 2 lists 25 runs — the exact box count is ambiguous at the published resolution) show box plots **with individual data points overlaid**, so per-well values are digitizable to figure precision. Fig. 1b is not digitizable (placeholder axes, no ticks). The y-axis is "CD31 Area/DAPI Area Normalized to FN": Fig. 1a spans 0–4, Fig. 2a spans 0–9, Fig. 3b spans 0–15, Fig. 4e spans 0–45.
Status: resolved
Action: Phase 2 is feasible **on the response values**, but see the next item — the *design matrix in physical units* is the blocker, not the responses.

### Item: Does the design matrix support a replay?
Source: Tables 1 and 2; p. 2, p. 4, p. 12
Finding: Table 1 (23 runs) and Table 2 (25 runs) give the full run patterns in coded ±/0 form, and the Fig. 1a/2a heatmap strips give per-condition levels graphically ("Concentrations vary between 0 (the lowest concentration for each protein) and 1 (the highest concentration for each protein)", Fig. 1a caption). **A replay in coded space is fully supported. A replay in µg/mL is not, because stage-2 physical levels are never stated and the stage-1 CIV level is self-contradictory.**
Status: unresolved for physical units; resolved for coded units
Action: scope Phase 2 to coded units, or state the assumed concentration ladder explicitly as an assumption.

### Item: Is the argmax well separated, and did the authors name a single best *tested* condition?
Source: Fig. 2a (p. 5); Results pp. 4–5
Finding: The authors **never identify a best-performing tested run**. They go straight from the fitted surface to a predicted optimum: "a regression analysis was performed to determine the coefficients of the response surface … The resulting parameter estimates shown in Fig. 2b and **the values at which a maximum CD31 expression was predicted** were identified." Figure reading: in Fig. 2a the highest median is ≈5.1 with the next cluster of conditions at medians ≈3.4–4.0 and boxes spanning ≈1–7; **the boxes overlap heavily and the argmax is not well separated.**
Status: resolved — **the argmax over the sampled runs is ambiguous.**
Action: **weakens Phase 2's headline framing.** "BO finds the published optimum in fewer experiments" has no well-defined target among the tested runs. Reframe against the *model-predicted* optimum (TheO) or against the fitted surface's argmax.

### Item: Is there a validation/confirmation experiment?
Source: Fig. 3 (p. 6); Results p. 4–5
Finding: **Yes, and it is a genuine prospective confirmation run that falsified the prediction.** Nine conditions were tested (TheO, TheO−C, TheO−FN(=EO), EO−C, ++++, +++− with C=0, +++−, LN411+FN, FN alone). "Interestingly, the TheO formulation resulted in very little endothelial differentiation, around the level seen on FN alone." Figure reading of Fig. 3b: TheO median ≈0.9 vs FN-alone median ≈1.0; EO median ≈6.1 (range ≈4.2–12.7). Text: "Differentiation on TheO-FN was also significantly higher than on LN411 + FN … TheO-FN also showed significantly more differentiation than was seen with the maximum concentration of all proteins (++++) or the maximum concentration of C, CIV, and LN411 without FN (+++-)."
Status: resolved
Action: strengthens Phase 2 — there is a real held-out validation set to score a replay against.

### Item: The single most important constraint on a Phase 2 "replay" claim — **[IMPLIES]**
Source: p. 2 (FN low = 22 in stage 1), p. 4 and p. 12 (FN could not go below 22 in stage 2), p. 5 (EO = TheO−FN)
Finding: FN = 0 was never sampled in either DoE stage, yet the paper's real answer, EO, has FN = 0. Therefore **the best formulation in the paper is not in the paper's own search space, and no optimizer — Bayesian or otherwise — replaying the published data can reach it.**
Status: **contradicts our record** if Phase 2 is framed as "BO finds the published optimum faster."
Action: reframe Phase 2 to one of: (i) BO reaches the best *sampled* condition in fewer runs than the 23 + 25 = 48-run factorial+CCD sequence; or (ii) BO recovers TheO (the fitted surface's constrained optimum) in fewer runs. Claim (iii) "BO would have found EO" is **unsupportable from the published data** and should be removed if present.

### Item: Independence of the EO control data across figure panels — **[INFER]**
Source: Figs. 3b, 4a, 4b, 4c, 4d (extracted images)
Finding: The EO box appears visually identical across Fig. 3b, 4a, 4b, 4c and 4d (median ≈6.1, upper whisker ≈12.7, same overlaid point pattern at ≈4.3, 4.3, 5.4, 6.9). The same holds for the TheO box (median ≈0.9–1.1). The paper does not state whether these are the same experiments replotted.
Status: unresolved
Action: manual check needed. If digitizing, do **not** treat TheO/EO points in Figs. 3b and 4a–d as independent replicates — pooling them would fabricate n.

---

## Summary of status counts
- resolved (paper is clear, including "clearly absent"): 17
- unresolved / manual check needed: 5
- contradicts our record: 6 (CIV 28-vs-56; stage-2 units unrecoverable; Fig. 1b not digitizable; effect-size prose vs Fig. 2c/d; TheO-was-extrapolation framing; "BO finds the published optimum" framing)
