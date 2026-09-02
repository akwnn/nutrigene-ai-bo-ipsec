# Cross-check 2: Collagen IV concentration, Hall/Lin/Ogle 2025 (Sci Rep 15:24479)

Source PDF: `/Users/jy/BO/s41598-025-09256-9.pdf` (15 pages; PDF page numbers = printed page numbers).
Full text extracted with `pypdf`; all 6 figure images extracted and read visually. No supplementary
file is present locally — SI (Figures S1–S3) is referenced only via the article DOI.

---

### Item: Stage-1 concentration levels — RESULTS statement
Source: p2, Results, "Optimization of an extracellular matrix formulation… using DoE"
Finding (verbatim, two consecutive sentences):
> "For Collagen I (C), CIV , LN111, LN411, and LN511 the low concentration was set to 0. The low
> Fibronectin (FN) concentration was set to 22 µg/mL, which was the lowest concentration on which
> human induced pluripotent stem cells (hiPSCs) showed good attachment and survival."

> "The high concentrations were set based on literature values for ECM coating for cell culture
> applications to 35.5 µg/mL, 28 µg/mL, 15.8 µg/mL, 0.8 µg/mL, 0.8 µg/mL, and 75 µg/mL for C, CIV ,
> LN111, LN411, LN511, and FN respectively."

Status: contradicts our record — confirms the Results value is **28 µg/mL** for CIV.
Action: none; this is the Results figure the project already recorded.

---

### Item: Stage-1 concentration levels — METHODS statement
Source: p12, Methods, "Design of experiments approach"
Finding (verbatim):
> "The first stage of the Design of Experiments (DoE) approach was a set of factorial experiments in
> which the concentration of each ECM protein (C, CIV , LN111, LN411, LN511, FN) was set to either a
> low (0,0,0,0,0,22 µg/mL) or high (35.5, 56, 15.8, 0.8, 0.8, 75 µg/mL) level respectively."

Status: contradicts the Results sentence above. Every other value is identical (35.5 / 15.8 / 0.8 /
0.8 / 75, lows 0,0,0,0,0,22). **CIV alone differs: 28 (Results) vs 56 (Methods).**
Action: the contradiction is real and is confined to CIV. Confirmed by direct reading, not inference.

---

### Item: Doubling of highs for stage 2
Source: p2, Results (end of page)
Finding (verbatim):
> "These estimates showed that C, CIV , and LN411 had positive and significant associations with CD31
> expression with the highest levels of CD31 expression corresponding to the highest concentrations of
> these proteins. Thus, the high concentration of these proteins was increased by a factor of 2 for the
> subsequent response surface regression."

Source: p4, Results (top), on FN
Finding (verbatim):
> "The trend for FN was similar to the first group of proteins, with the highest differentiation seen at
> the highest FN concentrations. However, because this association was not significant the high
> concentration of FN was kept the same."

Source: p2, Results, on LN111/LN511
Finding (verbatim):
> "LN111 and LN511 also showed significant associations with CD31 expression. However, the maximum
> expression occurred at the lowest concentrations of these proteins, which was set to 0, so these
> proteins were eliminated."

Status: resolved — the doubling applies to C, CIV, LN411 only; FN high unchanged at 75; LN111/LN511
dropped. Methods (p12) says nothing at all about doubling.
Action: none.

---

### Item: Stage-2 (response surface) concentration levels — absolute values
Source: p4, Results; Table 2 (p4) and its footnote; p12 Methods
Finding (verbatim, Results p4):
> "An on face central composite design was used to add levels of ECM concentration for the four
> proteins brought through to this stage: C, CIV , LN411, and FN as shown in Table 2."

Finding (verbatim, Table 2 footnote p4):
> "Table 2 . Run pattern for central composite design. abbreviations used: abbreviations used: collagen
> I (C), collagen IV (CIV), laminin 411 (LN411), fibronectin (FN). The run pattern for the second stage
> of the design. of experiments method for optimizing endothelial differentiation. (-) indicates the
> lowest concentration of the protein, (+) indicates the highest concentration of the protein, and (0)
> indicates the midpoint."

Finding (verbatim, Methods p12):
> "In this stage, different levels of each protein were evaluated as shown in Table 2 using a central
> composite design."

Status: **unresolved by direct statement.** The paper NEVER prints a numeric stage-2 concentration for
any protein. Table 2 is purely symbolic (−, 0, +). There is no stage-2 concentration table anywhere.
Action: manual check needed only if SI contains one — see "Supplementary" item below.

---

### Item: TheO composition, in full
Source: p4, Results, "Optimization…" (final paragraph before "Validation of TheO")
Finding (verbatim):
> "Following this set of experiments, a regression analysis was performed to determine the coefficients
> of the response surface relating ECM exposure to CD31 expression based only on significant terms up
> to the 3rd order (Fig. 2). The resulting parameter estimates shown in Fig. 2b and the values at which
> a maximum CD31 expression was predicted were identified. This prediction solution of 35.6 µg/mL C,
> 67.2 µg/mL CIV , 0.9 µg/mL LN411, and 22 µg/mL FN is the Theoretical Optimized formulation (TheO),
> with the concentrations of CIV and LN411 having the largest effect sizes and FN having a medium
> effect size. While the concentration of C was predicted to be significant, the effect size was
> predicted to be small."

Status: resolved — TheO = C 35.6, CIV 67.2, LN411 0.9, FN 22 µg/mL. This is the only place TheO is
numerically defined. EO = TheO minus FN (p5: "it will now be referred to as Endothelial Optimized or EO").
Action: none.

---

### Item: HOW TheO was obtained — search for profiler / desirability / stationary point / canonical
Source: whole-document keyword search (profiler, desirab*, maximi[sz]e, optimi[sz]e, stationary,
canonical, response surface solution, JMP, prediction)
Finding: **The words "profiler", "desirability", "maximize", "maximise", "stationary point", and
"canonical analysis" DO NOT APPEAR ANYWHERE IN THE PAPER.** Zero hits. There is no JMP screenshot or
JMP-output figure; Fig 2b is a hand-rebuilt two-column table ("Parameter" / "Estimate"), not a JMP
report pane.

The only three statements bearing on the derivation are:

p4 (Results), verbatim:
> "the values at which a maximum CD31 expression was predicted were identified. This prediction
> solution of 35.6 µg/mL C, 67.2 µg/mL CIV , 0.9 µg/mL LN411, and 22 µg/mL FN is the Theoretical
> Optimized formulation (TheO)"

p12 (Methods), verbatim:
> "The second stage of the DoE approach used a Response Surface Methodology to determine the optimal
> ECM formulation for endothelial differentiation. In this stage, different levels of each protein were
> evaluated as shown in Table 2 using a central composite design. JMP software was used to fit the data,
> conduct ANOV A, and sort parameter estimates to identify the theoretical optimized ECM formulation
> (TheO)."

p4 (Results, Validation of TheO), verbatim:
> "The fact that the TheO condition did not produce the expected result of high levels of
> differentiation could be attributed to several factors including the complexity of cell-ECM
> interactions or high variability in levels of differentiation. However, the reason for the discrepancy
> is likely due to use of an on face central composite design which does not allow for accurate
> modeling outside of the original parameter space."

Status: resolved as to method-naming (no profiler/desirability language anywhere; the term used is
"prediction solution", which is JMP's Response-Surface **Solution** report wording, i.e. the
critical/stationary point from canonical analysis — but the paper never says so).
The third quote is the paper's own explanation for why TheO failed, and it invokes modelling
**outside of the original parameter space**. That is the paper IMPLYING extrapolation; it does not
state that CIV specifically was extrapolated.
Action: treat the "prediction solution" wording as suggestive, not conclusive, on its own.

---

### Item: FN boundary behaviour (bears on constrained vs unconstrained optimisation)
Source: p4, Results, "Validation of TheO"
Finding (verbatim):
> "Additionally, TheO without FN (TheO-FN) was evaluated as the model used did not allow for
> concentrations of FN below 22 µg/mL to be evaluated, as again that was the lowest concentration of FN
> on which consistent cell attachment was seen. Since the TheO formulation indicated the lowest FN
> concentration would lead to the highest CD31 expression…"

Status: resolved. TheO's FN = 22 is the **lower boundary** of FN's range, and the paper says the model
was not allowed below it. So at least one factor was boundary-clamped.
Action: note that boundary-clamping of FN coexists with (apparent) extrapolation of CIV — the paper
describes a hybrid, not a pure constrained profiler run and not a pure unconstrained solve.

---

### Item: QUANTITATIVE RECONSTRUCTION from Fig 2b — the decisive test
Source: Fig 2b, p5 (parameter-estimates table, read from the extracted figure image)
Finding (verbatim table contents):
> Intercept 2.724 | C 0.007 | CIV 0.079 | LN411 0.736 | FN −0.131 | CIV*LN411 −0.078 |
> CIV*FN −0.087 | C*C −0.626 | LN411*LN411 −0.492 | FN*FN 0.036 | CIV*LN411*LN411 −1.442 |
> CIV*FN*FN 1.435

Reconstruction (THIS IS INFERENCE, NOT A PAPER STATEMENT):
The coefficient magnitudes are only consistent with **coded factors on [−1, +1]** (in raw µg/mL the
C*C term would be absurd: −0.626 × 35.5² ≈ −789 on a response that spans 0–9). Under [−1,+1] coding
the fitted surface reproduces three of TheO's four numbers exactly:

1. `∂y/∂C = 0.007 − 1.252c = 0` → c = 0.0056 → C = 35.5 × 1.0056 = **35.70** (paper: 35.6; the C
   stage-2 range must therefore be 0–71 = 2 × 35.5, confirming the doubling arithmetic).
2. `∂²y/∂f² = 0.072 + 2.870v > 0` for v > 0 → FN's optimum is at a **boundary**, and f = −1 beats
   f = +1 → **FN = 22.0** exactly (paper: 22). ✓
3. Maximising over LN411 and FN at a fixed coded CIV value v:

   | coded CIV v | model's optimal LN411 | model's optimal FN |
   |---|---|---|
   | 0.2  | 1.169 µg/mL | 22.0 |
   | 1.0  | 0.936 µg/mL | 22.0 |
   | **1.398** | **0.900 µg/mL** | **22.0** |

   Solving `∂y/∂LN411 = 0` for v at LN411 = 0.9 gives **v = 1.3979** analytically.

4. Back-solving the CIV coding from v = 1.3979 and TheO's CIV = 67.2:
   `67.2 = centre × (1 + 1.3979)` → **centre = 28.02 → stage-2 range 0–56.05 → stage-1 high = 28.02.**

   - If stage-1 CIV high were **28** (Results): stage-2 range 0–56, centre 28, v = **+1.40** → CIV =
     67.2 ✓ and LN411 = 0.900 ✓ and FN = 22 ✓. All three match.
   - If stage-1 CIV high were **56** (Methods): stage-2 range 0–112, centre 56, TheO's 67.2 → v = +0.20,
     at which the same model's optimal LN411 is **1.169**, not 0.9. ✗ Fails.

Status: **resolved by inference, not by any statement in the paper.** The published parameter estimates
are self-consistent with the Results value (stage-1 CIV = 28 µg/mL, stage-2 high = 56) and are
self-inconsistent with the Methods value (56 / 112). Under the consistent reading, TheO's CIV = 67.2 is
at coded +1.40, i.e. **20% above the highest CIV concentration ever tested (56 µg/mL)** — outside the
design space.
Action: this is a reconstruction I performed, NOT a finding stated by the authors. It should be labelled
as such in any downstream document. A statistician should re-run the check independently before it
carries a headline claim.

Caveats on this reconstruction, stated plainly:
- Coefficients are rounded to 3 decimals; C reproduces to 35.70 vs the printed 35.6 (0.1 off).
- Fig 2b shows only "significant terms"; a CIV*CIV term could have existed in the fitted model and been
  omitted from display. If so, an interior stationary point in CIV would exist and the argument weakens.
- None of the four true stationary points of the displayed surface equals TheO, so TheO is also not a
  clean unconstrained canonical solution of the *displayed* model.

---

### Item: Any other absolute Collagen IV concentration in the paper
Source: p12, Methods, "3D Bioprinting with ECM-based Bioinks"
Finding (verbatim):
> "The final cell-laden bioink optimized for endothelial differentiation (EO bioink) was composed of 15
> million cells/mL with 10% GelMA, 64.37 µg/mL C, 121.5 µg/mL CIV , 1.63 µg/mL LN411, 0.5% LAP , and 5
> µM ROCK inhibitor. The total ECM content was increased to match the previously published
> cardiomyocyte-optimized bioink48 while maintaining the same ratio as in the coating solution used for
> 2D experiments."

Status: resolved — consistent, but NON-discriminating. Ratios vs EO (35.6 / 67.2 / 0.9) are
64.37/35.6 = 1.8081, 121.5/67.2 = 1.8080, 1.63/0.9 = 1.8111 — a uniform 1.808× scale-up, confirming
TheO/EO CIV = 67.2 is a real, used number and not a typo. It says nothing about the tested range.
Action: none.

---

### Item: Supplementary material, table footnotes, figure captions giving a CIV concentration
Source: Table 1 footnote (p2), Table 2 footnote (p4), Fig 1 caption (p3), Fig 2 caption (p5),
Fig 3 caption (p6), Fig 5 caption (p9), Fig 1b and Fig 2a images
Finding: **None give any CIV concentration.**
- Table 1 and Table 2 footnotes define (−)/(0)/(+) symbolically only.
- Fig 1a and Fig 2a heatmaps are explicitly normalised: "Concentrations vary between 0 (the lowest
  concentration for each protein) and 1 (the highest concentration for each protein)."
- Fig 1b contour plots have **no numeric axes at all** — the axis titles are unreplaced placeholders
  reading literally "X axis label" and "Y axis label" (verified in the extracted figure image).
- Fig 1's caption contains a leftover author-to-editor note published verbatim: "The resolution of all
  figures is low, but figure #1 is especially low.  We have attached the high resolution figure 1 here."
- SI: only "Supplementary Information  The online version contains supplementary material available at
  https://doi.org/10.1038/s41598-025-09256-9" (p15). Figures S1, S2, S3 are cited on pp. 8, 9, 10 and
  concern VEGF timing, pre-differentiation CIV staining, and CD31 on CIV+ control area — none is a
  concentration table.
Status: unresolved — no in-PDF figure/table/footnote source resolves the CIV value.
Action: **manual check needed** — download the SI from https://doi.org/10.1038/s41598-025-09256-9 and
look for a stage-2 concentration table or a JMP output pane. The SI is NOT in `/Users/jy/BO/`.

---

### Item: Unit consistency (µg/mL vs mg/mL slip)
Source: whole document
Finding: **"mg/mL" appears zero times in the paper.** Every ECM protein concentration is µg/mL, in both
Results and Methods, in the bioink recipe, and in the ascorbic acid recipe (100 µg/mL). There is no
µg↔mg slip anywhere. A 28↔56 discrepancy is a factor of 2, not a factor of 1000, so a unit slip could
not produce it in any case.
Status: resolved — no unit slip on the CIV value.
Action: none.

---

### Item: Other Results-vs-Methods numeric discrepancies in the same paper (context for reliability)
Source: p5 Results vs p12 Methods
Finding (verbatim, Results p5):
> "First, to capitalize on the VEGF binding capacity of ECMs28,37,38 10 ng/mL VEGF was added to wells
> coated with ECM, incubated for 30 min at room temperature, and washed prior to adding hiPSCs."

Finding (verbatim, Methods p12):
> "Additionally, 50 ng/mL VEGF was incubated with the ECM coating for 30 min at room temperature (VEGF
> incubation)."

Further discrepancies found:
- Additive timing: Methods p12 "added to the media with every media change **beginning on day 1** of
  differentiation"; Results p8/p8 and Fig 4 caption repeatedly say "**beginning on day 0** of
  differentiation" / "added to the media on the first day of CHIR treatment".
- Methods p13 miscites a figure: "CIV staining was also imaged with a 4x objective… (Fig. 4d, top row )"
  — the referent is Fig. 5d.
- Methods p12 gives TGFβ "at concentrations of 2µM, 50ng/mL, and 5µM respectively", i.e. **TGFβ at 5 µM**,
  which is not a physically plausible unit for a growth factor (ng/mL is standard).

Status: contradicts our record only in the sense that it changes the prior. This paper has at least
three further Results/Methods numeric or unit mismatches, and visible production-QC failures
(unreplaced "X axis label" placeholders, a published author-to-editor note, a miscited figure).
Action: do not assume the Methods section is the authoritative one by default; it is demonstrably not
more reliable than Results in this paper. Note the same directional pattern (Results value lower than
Methods value) in the VEGF case, which is neutral rather than helpful.

---

### Item: The "56 = 2 × 28" origin argument
Status: **ARGUMENT, NOT EVIDENCE.** Stated for completeness as requested:
56 has a natural mechanical origin if stage-1 CIV were 28 — it is the doubled stage-2 high described on
p2, and a Methods writer transcribing the stage-2 value into the stage-1 sentence would produce exactly
the observed error. Conversely, 28 has no natural origin if stage-1 CIV were 56 (56/2 is not a quantity
the paper defines for stage 1). This is an asymmetry in error plausibility. It is NOT evidence, it does
not appear in the paper, and it must not be cited as a finding.
