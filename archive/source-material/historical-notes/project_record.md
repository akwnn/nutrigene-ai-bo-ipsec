# PROJECT RECORD
## Bayesian Optimization for hiPSC → Endothelial Differentiation

**Document 2 of 3.** Project context, scientific argument, Phase 2 and 3 plans, research grounding, decision log.
**Document 1** (`phase1_bo_build.md`) — the buildable specification for the current phase.
**Document 3** (`provenance_audit.md`) — which claims were verified against primary sources.

**Owners:** 2 people · **Client:** NutriGeneAI · **Horizon:** 2–3 months, extension possible
**Current position:** Phase 1, weeks 1–3. Nothing built yet.

> **v2.** Corrections from the provenance audit applied throughout. The scientific argument in Part B is substantially rewritten: Hall/Ogle fitted a **third-order** model, not a quadratic, and the paper gives a **biological** explanation for TheO's failure that earlier drafts omitted entirely.

---

# PART A — PROJECT CONTEXT

## A.1 Setting

Internship engagement with NutriGeneAI. Two people, 2–3 months, extension possible. The deliverable is a **publishable research paper** plus a reusable software tool the company keeps.

Five AI-automation proposals were produced earlier for NutriGeneAI stakeholders. This is **Proposal #1: Bayesian optimization for iPSC-EC cytokine priming**, chosen because the client explicitly named Bayesian optimization. The other four are out of scope.

## A.2 The scientific problem

NutriGeneAI works on **hiPSC → endothelial cell differentiation**. Efficiency depends on a large combinatorial space: ECM coating composition, cytokine and growth factor concentrations, timing, inhibitor use.

Standard readout: **CD31 (PECAM-1) positive area normalized to DAPI area** by immunofluorescence around day 10, or CD31⁺ percentage by flow cytometry. Different numbers; cannot be mixed within a campaign.

The field optimizes by Design of Experiments — factorial screens then a response-surface fit.

## A.3 The three phases

| Phase | Data source | What it proves | Lab dependency |
|---|---|---|---|
| **1** | Fake (synthetic oracle) | The code is correct, efficient, well-calibrated | None |
| **2** | Published (Hall/Ogle 2025) | **BO would have reached their best result in fewer experiments than the ~48 they ran** | None |
| **3** | In-house wet lab | The loop closes on live cells | Full |

**Phase 2 is the paper.** Phase 1 is the control experiment that makes Phase 2's numbers believable. Phase 3 is proof-of-concept.

Phases 1 and 2 are deliberately lab-independent. **If the wet lab slips, the paper still ships without Phase 3.**

## A.4 Timeline

| Weeks | Work |
|---|---|
| 1–3 | Email authors for data. **Build the optimizer. Phase 1 experiments.** Lock search space and metric with lab. |
| 4–8 | Digitize published figures. Phase 2 replay. Uncertainty analysis at TheO. |
| 5–10 | Lab rounds 1 and 2, in parallel, on the lab's schedule. |
| 9–12 | Write, figures, bioRxiv preprint. |

## A.5 Publication venues

bioRxiv preprint first — free, one day, timestamps the work. Then *Bioinformatics Advances*, *Digital Discovery*, or *SoftwareX*. *Biotechnology and Bioengineering* if Phase 3 lands. Not a stem-cell journal — they want more biology than this produces.

## A.6 Open items

Author order. Whether code and digitized data can be released publicly. Whether anything from the lab rounds needs IP protection before the preprint goes up.

---

# PART B — THE SCIENTIFIC ARGUMENT

## B.1 What the paper claims

Two earlier framings were wrong and are recorded here so they don't come back.

> **Wrong framing #1:** *"Response-surface methodology gives a prediction without an uncertainty."* False. OLS response surfaces have closed-form prediction variance, `Var[ŷ(x₀)] = σ̂²·x₀ᵀ(XᵀX)⁻¹x₀`, and the RSM literature is built around it — variance dispersion graphs, scaled prediction variance, fraction-of-design-space plots. Extrapolation error beyond the investigated region is a named, documented limitation in that literature.

> **Wrong framing #2:** *"A quadratic fitted to saturating truth must turn over, so its optimum is an artifact."* Hall/Ogle **did not fit a quadratic.** From the Results: the response surface used *"only significant terms up to the 3rd order."* The Figure 2 caption repeats it. The forced-concavity argument is specific to quadratics and does not apply to a cubic.

**The claim, as it now stands:**

A low-order polynomial basis is a poor fit for saturating dose-response biology. Its fitted optimum can land outside the region where data was collected. There, the polynomial's prediction interval — which grows with **design leverage**, conditional on the model form being right — cannot express doubt about the form itself. A GP's posterior variance grows with **distance to observed data** and reverts toward the prior, so it can.

**This is an empirical claim, not a mathematical necessity.** Whether a third-order fit's optimum escapes the design region depends on the surface and the design. Phase 1's Experiment 4a measures the *rate*, on surfaces whose shape we control. Pre-flight check 1 verifies it happens at all before anything is built on it.

**Both intervals must be reported.** Comparing a GP posterior against a bare polynomial point estimate is not a fair comparison.

### B.1.1 The phenomenon is textbook — do not claim discovery

An extrapolated stationary point outside the design region is a **named, standard topic in response-surface methodology**. Canonical analysis identifies the stationary point's nature; **ridge analysis** (Hoerl 1959; Draper 1963) handles the case where it falls outside the region. Box & Draper and Myers & Montgomery cover it; Gramacy's *Surrogates* describes it as an artifact of the local nature of low-order polynomial approximation.

A reviewer will say: *ridge analysis already tells you the stationary point is outside the region, and lack-of-fit testing already flags model inadequacy — and Hall/Ogle had replicates, so lack-of-fit was available to them.*

**The honest position.** The failure was not that DoE *couldn't* detect this. It is that the practitioners didn't run the diagnostic. That is a claim about practice, not method — and it is weaker than earlier drafts implied.

**What the GP genuinely adds** is not a capability the DoE toolbox lacks, but a **single continuous uncertainty field over the whole space that feeds directly into the next decision**, rather than three separate diagnostics (ridge analysis, lack-of-fit, variance dispersion) that a human must run and interpret. That is an automation-and-integration argument. State it that way.

**Cite the RSM literature explicitly** and position the contribution as *automated, calibration-based detection quantified against model-free nulls*. If a reviewer can point to a prior paper doing GP-versus-polynomial extrapolation detection on saturating biological surfaces, drop the novelty language entirely and sell it as a clean reproducible demonstration plus tooling.

### B.1.2 What survives regardless

~~**The efficiency claim.** "BO reaches the same answer in fewer experiments than DoE" is a capability claim that does not depend on ridge analysis, calibration, or E4 at all. It is measurable against published data, and nothing in the prior-art critique touches it.~~

> **STRUCK (T1.3, 2026-08-12). This was the most exposed sentence in the record and all three of its clauses are now false.**
>
> - *"nothing in the prior-art critique touches it"* — replay benchmarking of BO against published datasets is an established genre with purpose-built frameworks, and **Gisperg et al.** (*Biotechnol Bioeng* review) report in print that BO gave a more precise model near the optimum while **the number of experiments could not be reduced compared with DoE**. That is this project's ceiling finding, already published.
> - *"BO reaches the same answer in fewer experiments"* — **measured, and it does not.** At the registered primary cell BO loses to the DoE pipeline on best-observed regret (−0.0595, p<0.0001), and on the axis a wet lab actually pays it loses far worse: **3 sequential rounds for DoE against 10 for BO**, with Latin hypercube beating BO in **one** (Q38).
> - *"It is measurable against published data"* — the replay was run and it **cannot** measure this. Minimum detectable effect **0.68 evaluations** at 80% power, with a top-5 condition already in the shared opening batch **64%** of the time (Q37). The instrument has no resolution at the achieved menu size.
>
> **What replaces it as "what survives regardless" is not the efficiency claim but the scoring-convention claim** — see `nutrigene-ai-bo-ipsec/docs/CLAIMS.md` §Positioning. At the primary cell the verdict swings 0.3526 between rule A and rule C, and **91% of that swing comes from how the classical arm is scored** (≈10:1 against the BO arm's contribution). That claim is about an existing disagreement in the literature rather than a discovery, it survives on three landscape families, and it is checkable.

**That is the paper.** The uncertainty work is a supporting section requiring honest framing and a correctly-specified parametric comparator — not the headline it has periodically drifted toward.

## B.2 The counter-argument, and the answer

A reviewer will say: *then fix the basis — fit a saturating parametric model.* Two answers:

- In a 6–8 factor system with unknown interaction structure, you do not know the correct parametric form a priori. A GP is nonparametric and doesn't need it.
- Even a correctly specified parametric model expresses parameter uncertainty, not structural uncertainty.

**The first should be tested, not asserted.** If Phase 1 has spare capacity, add a correctly-specified Hill-model arm to Experiment 4a. If it extrapolates well, say so — the claim sharpens to "the GP wins when the functional form is unknown," which remains the practically relevant case.

## B.3 The Hall/Ogle case — TheO

Hall, Lin & Ogle (*Sci Rep* 2025, 15:24479) optimized ECM coating for hiPSC→EC differentiation with two-stage DoE. Their stage-2 response surface, fitted with terms up to third order, predicted an optimum they called **TheO**: 35.6 µg/mL Collagen I, 67.2 µg/mL Collagen IV, 0.9 µg/mL Laminin 411, 22 µg/mL Fibronectin. *(All four values verified from the paper.)*

They made it. They tested it. **It produced very little endothelial differentiation, around the level seen on fibronectin alone.** *(Verified.)*

The authors' own explanation: *"the reason for the discrepancy is likely due to use of an on face central composite design which does not allow for accurate modeling outside of the original parameter space."* *(Verified, direct quote.)*

### B.3.1 The extrapolation detail — unresolved in the paper

The claim that Collagen IV's 67.2 µg/mL exceeded the tested range rests on an internal contradiction in the published text.

- **Results section:** stage-1 highs were 35.5, **28**, 15.8, 0.8, 0.8, 75 µg/mL for C, CIV, LN111, LN411, LN511, FN
- **Methods section:** stage-1 highs were 35.5, **56**, 15.8, 0.8, 0.8, 75 µg/mL

Every value matches except Collagen IV. And 56 = 2 × 28, which matters because the Results state the highs for C, CIV, and LN411 were *"increased by a factor of 2 for the subsequent response surface regression."*

| If stage-1 CIV high is… | Stage-2 high is… | TheO's 67.2 is… |
|---|---|---|
| 28 (Results) | 56 | **outside** the tested range — claim holds |
| 56 (Methods) | 112 | **inside** — claim fails |

**Circumstantial support for the Results reading:** of TheO's four values, Collagen IV would be the only one outside its range (Collagen I 35.6 in [0,71], Laminin 411 0.9 in [0,1.6], Fibronectin 22 at its floor). And the authors' own explanation — a design that cannot model outside the original parameter space — only makes sense if something *was* outside.

**Table 2 will not settle it.** Its caption confirms the run pattern is coded (minus, zero, plus), not absolute. The µg/mL values appear only in prose. Resolving this needs the corresponding author.

**This blocks exactly one sentence** — the one asserting 67.2 exceeded 56. It does not block the replay, the efficiency comparison, or the uncertainty analysis, all of which work in coded space.

### B.3.2 The biological explanation — and why it complicates the story

**Earlier drafts omitted this entirely. A reviewer would catch it immediately.**

The paper reports that **TheO without fibronectin — renamed EO — worked very well**, better than their previously published LN411+FN formulation. Their explanation is mechanistic and supported by intervention experiments: fibronectin activates TGFβ signalling, which inhibits endothelial specification. A TGFβ inhibitor rescued differentiation on TheO; adding TGFβ suppressed it on EO.

And critically: *"the model used did not allow for concentrations of FN below 22 µg/mL to be evaluated,"* with TheO sitting at that floor because *"the TheO formulation indicated the lowest FN concentration would lead to the highest CD31 expression."*

**So the DoE correctly wanted less fibronectin and was structurally unable to ask for it.** That is a **design-boundary** failure, not an extrapolation failure — and the response surface flagged it correctly. The authors read the signal and tested TheO-minus-FN precisely because of it.

**What this means for the paper.** TheO's failure has at least two contributing causes, and they must be separated:

| Cause | Nature | Does the GP help? |
|---|---|---|
| Collagen IV possibly extrapolated beyond tested range | Modelling-uncertainty problem | **Yes — this is the claim** |
| Fibronectin optimum below the design floor | Design-space problem | **No.** The polynomial signalled it correctly. |

**Claim the first. Report the second honestly.** Phase 1's Experiment 4 tests them as E4a and E4b for exactly this reason. Asserting the GP solves the fibronectin problem would be indefensible to anyone who has read the paper.

---

# PART C — HOW PHASE 1 CODE CARRIES FORWARD

## C.1 The core idea

**The optimizer never evaluates anything. It only proposes.** Something else supplies outcomes.

```python
while budget_remaining:
    X = optimizer.ask(q)                    # identical in all three phases
    Y, Yvar = evaluator.evaluate(X)         # only this changes
    optimizer.tell(X, Y, Yvar)              # identical in all three phases
```

| Phase | Evaluator | What `evaluate()` does |
|---|---|---|
| 1 | `SyntheticEvaluator` | Calls the Hill oracle. Instant. |
| 2 | `LookupEvaluator` | Indexes the digitized table. Instant. |
| 3 | `HumanEvaluator` | Writes a CSV of proposed conditions, waits ~2 weeks, reads results back. |

Each is ~40 lines. Build `SyntheticEvaluator` now.

## C.2 The nine requirements

Build requirements are in Document 1 §2. Here is why each exists.

| # | Requirement | Which phase needs it |
|---|---|---|
| 1 | Ask/tell separation | 2 and 3 — the basis of swapping evaluators |
| 2 | **Discrete candidate mode** | **2 — see C.3, the non-obvious one** |
| 3 | Search space in config, coded [0,1] | 2 (digitized figures are coded) and 3 (whatever the lab varies) |
| 4 | Mixed parameter types in schema | 3 — categorical base medium, integer treatment days |
| 5 | **`Yvar` policy — always pass it, imputed where unreplicated** | 3 will have replicated and unreplicated points together, and one `SingleTaskGP` cannot mix likelihoods. **A modelling decision, not plumbing.** |
| 6 | **Serialize data + config + RNG state; refit on resume.** Not model weights. | 3 runs over weeks. Refitting is robust across BoTorch versions, and the identical-trace test only passes if RNG state is captured. |
| 7 | Metric identity on every data row | 3 — CD31% by flow and CD31 area by IF must never mix |
| 8 | **Constraint hooks threaded through config** | 3 will have total-protein caps and plate arithmetic. **And the Ogle failure was itself a constraint problem** — the true optimum needed FN = 0 against a design floor of 22 µg/mL. Retrofitting changes the optimizer signature everywhere. |
| 9 | **`X_pending` / in-flight proposal tracking** | 3 with humans in the loop means staggered, asynchronous returns |

### C.2.1 Replicate structure — flagged, not yet specified

Hall/Ogle collected at least 4 wells from at least 3 experimental replicates per condition. That is a **nested** structure, and treating wells as independent inflates precision — pseudo-replication. Phase 3 will have the same shape.

The pooling story (well-level mean with a random-effects variance, versus condition-level mean with replicate SEM) is a Phase 2/3 modelling decision. It does not affect the Phase 1 build, but requirement 5's `Yvar` policy is where it lands, so decide it before Phase 2 data arrives.

## C.3 The non-obvious one: discrete candidate mode

**In Phase 2 the optimizer can only propose conditions that already exist in Hall/Ogle's dataset**, because those are the only ones with measured outcomes. You cannot let the model search freely — there would be nothing to look up.

The acquisition step must therefore support choosing the best `q` from a **fixed candidate set** as well as searching continuously. If Phase 1 hardcodes continuous optimization, Phase 2 requires refactoring the optimizer's core. Roughly twenty lines now; a structural change later.

**This is also a stated limitation of the paper.** Replay from a fixed menu is easier than free search, so the efficiency numbers are conservative — a free search would likely do better, not worse. Say it before a reviewer does.

## C.4 Coded space carries forward too

Phase 1's search space is canonically coded `[0,1]`. Phase 2's digitized data is coded by construction — both figure captions state concentrations vary between 0 (lowest for each protein) and 1 (highest). Phase 3's lab variables get coded against whatever min/max the lab declares.

**One representation, three phases, no unit conversion anywhere.** This is also what makes the unresolved Collagen IV question harmless to the build.

---

# PART D — PHASE 2 PLAN (published data)

## D.1 Primary dataset

**Hall, Lin & Ogle 2025**, *Scientific Reports* 15:24479, open access.
`https://www.nature.com/articles/s41598-025-09256-9`

Two-stage DoE on six ECM proteins.

| | |
|---|---|
| Stage 1 | Factorial across Collagen I, Collagen IV, Laminin 111, Laminin 411, Laminin 511, Fibronectin. Low = 0 for all except Fibronectin at 22 µg/mL (lowest concentration with good attachment). Plus one centre point. |
| Stage 2 | On-face central composite design on the four proteins carried forward: C, CIV, LN411, FN. Response surface fitted with **terms up to third order**. |
| Readout | CD31 area ÷ DAPI area by immunofluorescence at day 10, normalized to a fibronectin control. At least 4 wells from at least 3 experimental replicates. |
| Software | JMP |
| Total conditions | **~48 — not confirmed.** The 23 + 25 split comes from the project proposal; the tables were not retrievable. Verify. |

**Data availability:** on reasonable request from the corresponding author, Brenda Ogle, `ogle@umn.edu`.

**Key findings:** Collagen I + Collagen IV + Laminin 411 (their EO formulation) drives high endothelial differentiation. Note the Matrigel comparison is **transitive, not direct** — the paper shows EO > LN411+FN, and cites their own 2022 work for LN411+FN > Matrigel. State it that way. VEGF improves outcomes; TGFβ inhibits specification.

## D.2 Working in coded space — decided

**The replay runs entirely in coded [0,1] coordinates.** Digitize the bar charts in Figures 1a and 2a; the heatmaps below them give coded levels directly, per the figure captions. Absolute concentrations are never needed.

This sidesteps the §B.3.1 contradiction for everything except the single sentence about 67.2 versus 56.

## D.3 The replay experiment

Give the GP only the first N conditions from their dataset, in the order they ran them. The model proposes what it would test next, restricted to the fixed candidate set. Look that condition up in their remaining data and feed back the real measured value. Repeat.

**The question:** how many conditions does the model need before it reaches the best value in their dataset, compared to the ~48 they actually ran?

Phase 1's Experiment 2 uses a budget of 48 for exactly this reason — the numbers read directly against each other.

## D.4 The TheO uncertainty analysis

Fit the GP to their stage-2 data. Query at TheO's coded position. Record predicted mean and predictive interval. Compare against conditions well inside the sampled region. **Also compute their third-order model's own prediction interval at TheO** — the comparison is GP interval versus polynomial interval, never GP interval versus polynomial point estimate.

**Report the fibronectin caveat alongside it**, per §B.3.2. TheO's failure was not purely an uncertainty problem.

## D.5 Secondary dataset

**Hou et al. 2017**, *Scientific Reports*, open access.
`https://www.nature.com/articles/s41598-017-06986-3`

63 combinatorial coating conditions from six components, CD31 readout, three cell lines. Same replay procedure. Results in a heat map, so values are harder to read than bars. Shows the method generalizes across studies rather than working on one dataset by luck.

## D.6 Method precedent

**Narayanan et al. 2025**, *Nature Communications* 16:6055. BO of culture media with eight cytokines. Data on figshare, code on GitHub (MIT). Wrong cell type, so it contributes nothing to the biological argument — but it downloads cleanly, so it is the development target and the method-precedent citation.

## D.7 Phase 2 limitations to state

- Replay is easier than prospective optimization; the answer is already in the dataset. Efficiency numbers are a lower bound on difficulty.
- **Replay can only select from conditions actually run, not search freely.** Conservative — say it first.
- **The published optimum is the discrete argmax of ~48 points.** "BO finds it in k < 48 picks" partly measures ordering rather than optimization. Scope the claim to *"recovers the published discrete argmax in k picks"* and do not overclaim.
- **The true best formulation is not in the replay space at all.** EO is TheO minus fibronectin — FN driven to zero, below the design floor of 22 µg/mL. A faithful replay of the 48 conditions **cannot reach the answer the authors ultimately found.** State this before a reviewer does.
- **The surface being replayed is itself a model artifact.** The authors only ran a JMP-chosen design, so the 48 points reflect that design's assumptions, not ground truth.
- Digitized values carry reading error, and their noise is unknown. Report the extraction method.
- TheO's failure has at least two causes; only one is a modelling-uncertainty problem (§B.3.2).
- The extrapolation detail rests on an unresolved contradiction in the source paper (§B.3.1).

---

# PART E — PHASE 3 PLAN (in-house lab)

## E.1 Structure

**Round 1 — seed batch.** Sobol sampling across the search space. As many conditions as the lab can run at once, ideally 12+. Each in at least triplicate. Nothing predicted yet; this gives the model something to learn from.

**Round 2 — model-proposed batch.** Fit the GP to round 1. Optimize the acquisition. A scientist reviews and approves before anything runs. Same size, same triplicate structure.

**What gets compared:** best outcome in round 2 versus round 1. Replicates give a standard deviation per condition; if the round-2 best exceeds round-1 by more than the combined variability, the improvement is real. Run a t-test, report the p-value. **If the intervals overlap, say so** rather than claiming an improvement that isn't there.

**Why batch size matters more than round count.** At 2–3 weeks per round you realistically get two rounds. The only remaining lever is how much you learn per round, set by batch size. Twelve conditions teaches the model substantially more than six.

**Replicates also feed the model.** The GP takes observation variance as an input. Passing measured replicate variance rather than assuming a fixed noise level makes the surrogate more accurate.

## E.2 What is needed from the lab before round 1 — ask now

| Item | Detail |
|---|---|
| **Variables and ranges** | Which protocol parameters can be varied, min/max for each. Anything held fixed must be declared fixed. |
| **Constraints** | Combinations that are biologically or practically impossible. Any cost or reagent ceiling. Encoded so the optimizer never proposes the unrunnable. |
| **Metric definition, locked** | Exactly what is measured and how. **CD31% by flow cytometry and CD31 area by immunofluorescence are different numbers and cannot be mixed across rounds.** Whichever is chosen gets versioned and recorded on every row. |
| **Throughput and turnaround** | Conditions per batch; days from seeding to readout. Sets `q` and the round budget. |
| **Existing data** | Historical experiments with conditions and outcomes. **If there are enough and they are spread across the range rather than clustered, round 1 can be skipped.** The question is spread, not count. |

**One design lesson from Hall/Ogle worth carrying over:** their fibronectin floor of 22 µg/mL was a hard attachment constraint, and the true optimum was below it. When the lab declares ranges, ask explicitly which bounds are *hard physical constraints* and which are *conventional defaults*. The latter can be pushed; the former cannot, and the optimizer should know the difference.

## E.3 Data format

One row per experimental arm:

```
each variable (units in header) · each measured outcome · replicate SD ·
number of replicates · batch ID · operator ID · date ·
assay protocol version · approver
```

Getting this right from the first experiment saves substantial cleanup. It is why requirement #7 exists.

## E.4 Phase 3 limitations to state

- Two rounds demonstrate the loop closes. They do not demonstrate a converged optimum or a mapped Pareto front.
- The method is software-validated and tested against published biology. It is not biologically validated on NutriGeneAI's system beyond two rounds.

## E.5 Deferred work that belongs here

Cut from Phase 1, recorded so it isn't lost.

| Item | Why it belongs to Phase 3 |
|---|---|
| **Batch-effect modelling** | Passage and lot-to-lot variation are large in stem-cell work. Round index should enter the model as a categorical dimension or fixed effect. |
| **Bounded-proportion response** | CD31⁺/DAPI is bounded with variance shrinking at both ends. A Gaussian likelihood is misspecified precisely near the top of the range. Consider a logit transform and benchmark it. |
| **Replicate-count study** | Real `Yvar` from n=3 has ~2 degrees of freedom — a poor estimate. Benchmarking exact versus 3-replicate variance tells the lab how many replicates to run. A genuine client deliverable. |
| **Round-budget framing** | Wet-lab cost is *rounds* (~10–14 days each), not evaluations. Client plots should show progress versus rounds at fixed plate capacity. |
| **Initial-design size as a factor** | At budget 24 and d=8, the `2d+2` rule consumes 18 of 24. Testing smaller seed designs is plausibly the highest-leverage knob at realistic budgets. |
| Outlier robustness, non-stationarity | Realism work. |
| Multi-objective (qLogNEHVI) | Hall/Ogle's readout is single-objective, so Phase 2 doesn't need it. Efficiency versus reagent cost is the natural pair when it arrives. |

---

# PART F — RESEARCH GROUNDING

## F.1 Published precedent

**Narayanan et al. 2025**, *Nat Commun* 16:6055 (DOI 10.1038/s41467-025-61113-5, CC-BY 4.0). Optimized a 4-media blend under a sum-to-100% constraint, an 8-cytokine cocktail (IL-2, IL-3, IL-4, IL-7, IL-12, IL-15, IL-21, BAFF), and 4-factor carbon-source media for *K. phaffii* with a categorical factor. GP with a UCB acquisition function; a custom categorical kernel reported 33–50% smaller error than one-hot; space-filling initial designs; small batches. Efficiency saving scales with factor count: ~3× fewer experiments than state-of-the-art DoE at modest counts, 10–30× at nine factors. PBMC blend: 24 experiments. Yeast: 90 over 7 iterations. Code: `github.com/NHarini-1995/CellCultureBayesianOptimization`, Zenodo 10.5281/zenodo.15466161.

*Note: their continuous kernel is not specified in what we retrieved. Do not cite them as evidence for a particular kernel choice.*

**Kanda, Natsume et al.**, *eLife* 2022;11:e77007. Batch BO on a LabDroid robot for iPSC→retinal pigment epithelium differentiation, seven parameters, pigmented area readout. From ~200 million combinations, 143 conditions over 111 days, 88% improvement over the pre-optimized protocol. 216 forty-day experiments, ~8,640 experiment-days. **The canonical iPSC-differentiation-by-BO paper.**

**Hall, Lin & Ogle**, *Sci Rep* 2025, 15:24479 — **DoE, not BO.** Baseline and data source. See Part B.

Also: **Bader et al. 2023** (multi-objective batch BO, MSC-derived extracellular vesicles, 4 parameters, 3 objectives, 32 experiments, LHS-seeded) · **Gisperg et al.**, "Bayesian Optimization in Bioprocess Engineering — Where Do We Stand Today?", *Biotechnology & Bioengineering* 122(6):1313–1325, 2025 (the framing review) · **Cosenza, Astudillo, Frazier, Baar & Block**, *Biotech & Bioeng* 2022 · **Romero, Krause & Arnold**, *PNAS* 2013 (origin of this machinery in biology).

## F.2 Reference repositories

| Repo | URL | License | Why |
|---|---|---|---|
| CellCultureBayesianOptimization | `github.com/NHarini-1995/CellCultureBayesianOptimization` | — | Narayanan's code. Closest template. |
| Honegumi | `github.com/sgbaird/honegumi` | MIT | Generates unit-tested Ax/BoTorch scripts. Diff against yours as a sanity check. |
| BoFire | `github.com/experimental-design/bofire` | — | BASF-led. Mixed variables, nonlinear constraints. |
| BayBE | `github.com/emdgroup/baybe` | Apache-2.0 | Merck KGaA. Low-data regime, transfer learning. |
| Olympus / Atlas | `github.com/aspuru-guzik-group/olympus`, `/atlas` | MIT | Benchmarking, self-driving-lab control. |
| Summit | `github.com/sustainable-processes/summit` | verify | Chemical DoE+BO benchmarks. |

## F.3 Version and API notes — verified

**`botorch` 0.18.1**; Python ≥3.11, PyTorch ≥2.2, GPyTorch ≥1.15.1; MIT. Repo at `meta-pytorch/botorch`.

**`ax-platform` 1.3.1**; Python ≥3.11; MIT. Ax 1.0.0 (May 2025) introduced `ax.api` with `Client`. `AxClient` carries a deprecation warning; **the removal version is unverified — do not cite "removed in 1.4.0."** Phase 1 doesn't use Ax. Phase 3 may, for trial tracking and JSON checkpointing.

**Verified from source and documentation:**

- `get_covar_module_with_dim_scaled_prior(ard_num_dims, batch_shape=None, use_rbf_kernel=True, active_dims=None)` returns `MaternKernel | RBFKernel` — **a bare kernel, no `ScaleKernel` wrapper**
- `use_rbf_kernel` defaults to `True`, so **the Matérn override is required**
- The lengthscale prior is `LogNormalPrior(loc=SQRT2 + log(ard_num_dims)*0.5, scale=SQRT3)`, **constrained above 0.025** for numerical stability
- The legacy configuration is available via **`get_matern_kernel_with_gamma_prior`** — no need to hand-roll it
- `loo_cv` **does not refit the model per fold**; its documentation states hyperparameters are kept fixed as a fast approximation and recommends `batch_cross_validation` where hyperparameter changes matter
- `batch_cross_validation(model_cls, mll_cls, cv_folds, fit_args=None, observation_noise=False)` fits separate models with separate hyperparameters. **Note the `observation_noise=False` default** — pass `True` for coverage of measurements
- `FixedNoiseGP` merged into `SingleTaskGP`; `HeteroskedasticSingleTaskGP` removed (PR #2616)

**On the 0.12 default-kernel change.** BoTorch switched from Matérn to RBF with a dimension-scaled LogNormal prior, following Hvarfner et al., ICML 2024. Four things changed at once: kernel, lengthscale prior, noise prior, and outputscale handling. **The kernel component specifically is not well justified** — in Discussion #2451, a user questions the RBF switch and notes the common belief that Matérn's roughness suits real-world problems; Hvarfner replies that he agrees the RBF-versus-Matérn motivation is not well justified. Another participant reports better performance with `use_rbf_kernel=False` in some cases.

## F.4 Benchmarking practice

**Standard test functions.** Branin (2-D, smoke test) · Hartmann6 (6-D, deceptive, the workhorse) · Ackley (needle-in-haystack, tests exploration; BO can genuinely lose) · Rosenbrock (ill-conditioned). Multi-objective: Branin-Currin, ZDT, DTLZ.

**Seeds and instances.** *npj Comput. Mater.* (2021) used 50 seeds; the Black-Box Challenge analysis ran 100 repeats. But seeds on one landscape measure within-landscape noise — **across-instance variance is usually larger**, so instances × seeds beats seeds alone at fixed compute.

**"BO beats random" citation:** Turner, Eriksson, McCourt, Kiili, Laaksonen, Xu & Guyon (2021), PMLR v133:3–26 (arXiv 2104.10201).

**Critiques to pre-empt:** too few seeds or no variance reported · **tuning your method while leaving baselines at defaults** · cherry-picked functions · over-tuning to a fixed seed. Sources: Eggensperger et al. on algorithm configuration; arXiv 2505.07750; arXiv 2511.16230.

*J. Mater. Res.* 2026 (arXiv 2504.03943) advocates simulating before wet-lab to verify budget adequacy — a citable justification for Phase 1 existing.

**Calibration:** Acharki, Bertoncello & Garnier, *Comput. Stat. Data Anal.* 2022 (arXiv 2106.05396) for leave-one-out coverage. Gneiting & Raftery 2007 for proper scoring rules.

---

# PART G — DECISION LOG

| Decision | Choice | Why |
|---|---|---|
| **Thesis, correction 1** | Dropped "RSM lacks uncertainty" | Factually false. RSM has closed-form prediction variance. |
| **Thesis, correction 2** | Dropped "a quadratic must turn over" | Hall/Ogle fitted **third-order** terms, verified from the paper. The forced-concavity argument is quadratic-specific. |
| **Thesis, final** | Low-order polynomial misspecification, as an **empirical** claim measured in Phase 1 | Survives both corrections. Pre-flight check 1 verifies the mechanism exists before anything is built on it. |
| **Two mechanisms separated** | E4a extrapolation (claimed), E4b design boundary (reported) | The paper shows fibronectin's optimum was below the design floor and that the polynomial **correctly signalled it**. Claiming the GP solves that would be indefensible. |
| **Coded space** | Canonical [0,1] representation across all phases | Digitized figures give coded levels only. Sidesteps the unresolved Collagen IV contradiction for everything except one sentence. |
| **Kernel** | ARD Matérn 5/2 with dimension-scaled LogNormal priors, **kernel comparison on the critical path, scored on calibration** | The dimension-scaled priors are the evidenced improvement. **The RBF-versus-Matérn question is explicitly unsettled** — Hvarfner, whose work prompted the change, says the motivation is not well justified. Requires `use_rbf_kernel=False`; the default is RBF. |
| *Kernel — retracted claim* | — | An earlier draft asserted "Matérn is the field standard in published cell-culture BO." **Unsupported.** Our research never established Narayanan's or Bader's continuous kernel. |
| *Kernel — dropped argument* | — | An earlier draft argued for Matérn because it produces wider intervals, suiting a calibration claim. Motivated reasoning, and only half true — far from data both kernels revert to the same prior variance since outputscale is fixed. |
| **Acquisition** | qLogEI single-objective, qLogNEHVI multi | Classic EI has vanishing gradients over most of the domain. qLogEI is EI, correctly implemented. |
| **Framework** | Raw BoTorch for Phase 1; Ax `Client` possibly for Phase 3 | Ax's trial machinery suits lab-in-the-loop campaigns, not thousands of benchmark runs. |
| **Sequential DoE baseline** | **Dropped from Phase 1** | Hall/Ogle already ran DoE and published it. Their conditions are the DoE arm in Phase 2, run by practitioners. Reimplementing a competing method as non-experts is a liability. |
| **Compositional / simplex constraints** | Dropped | Hall/Ogle varied concentrations independently in a box. Compositional structure applies to Narayanan's media blend, a secondary dataset. |
| **Compute** | Laptops, CPU, no GPU | GP fits at n<100 are CPU-bound; GPU transfer overhead should make it slower. Colab was recommended then withdrawn — session timeouts for a workload a laptop does better. |
| **Grid size** | 10 instances × 5 seeds | Across-landscape variance dominates. Fits an overnight run. |
| **E2 budget** | 48 evaluations, provisional | Matches the reported condition count, which is **itself unconfirmed**. |
| **Bug: `Normalize` bounds** | Explicit `bounds=` everywhere | Without them the transform learns from training-data min/max, silently breaking Experiment 4's sub-box. |
| **Bug: CV hyperparameter refitting** | `batch_cross_validation`, never `loo_cv` for published numbers | Verified: `loo_cv` keeps hyperparameters fixed. Used naively, coverage comes out inflated. |
| **Bug: lengthscale access path** | `model.covar_module.lengthscale` | Verified: the function returns a bare kernel, so `.base_kernel` raises. |
| **Oracle parameterization — corrected again** | **Sample `x*` (peak location) and `r = IC50/EC50` directly; derive `EC50 = x*/√r`, `IC50 = x*·√r`** | v4 sampled EC50 and IC50 and let `x*` float. Under that draw the polynomial's escape rate was ≈2.4% per factor and ≈14% per d=6 instance — **E4a had almost no mechanism.** Worse, v4 *narrowed* EC50 to help E4 using v3's monotone-oracle reasoning; under a biphasic oracle that pushes `x*` further inside the sub-box, making E4a worse. Sampling `x*` directly also removes a v4 artifact where `IC50 ~ U(2·EC50, 1.2)` made window width anti-correlated with EC50 by construction. |
| **E4 sub-box — relative to the peak** | **`[0, κ·x*ᵢ]` per dimension, κ swept over {0.6, 0.7, 0.8, 0.9}** | **The invariant: E4 needs extrapolation, E2 needs a measurable peak, and satisfying E4 by raising `x*` flattens the peak and breaks E2.** At `x* = 0.8, n = 3`, the best achievable decline to the box edge over all `s` is ≈10% — one sigma. Reaching 30% would need `n ≈ 6` against `n ~ U(1,3)`. A peak-relative sub-box makes E4's mechanism independent of `x*`, freeing `x*` low for depth. **Future revisions: lower κ, never raise `x*`.** |
| **Peak normalization** | `f̃ᵢ = hᵢ·gᵢ·((1+sᵢ)/sᵢ)²`, peaking at exactly 1 | Unnormalized peak height spans ~0.34–0.92, a 2.7× range. With `Σw = 1`, equal-weight factors would differ threefold in influence, and the non-separability and SNR checks would measure that confound. |
| **Instance acceptance — depth, not location** | `f(x*) − max_{∂box} f > 3σ_rel·f(x*)`, reject-and-resample | At `x* = 0.735, n = 1`, the peak is 0.385 and the boundary value 0.376 — a 2.3% decline against a noise sd of 0.039. **Interior by location, indistinguishable from a corner by measurement.** A location check passes while the property it guarantees fails. |
| **Claim 1 rewording** | Recovers the optimum's **value**, not its location | At d=6 with `Σw=1`, a single-coordinate move from peak to boundary shifts the response ≈0.04σ. Per-coordinate localization from individual observations is impossible at this SNR regardless of parameters. |
| **β scaling** | `1/k` with `k = ⌈d/2⌉`, plus a positivity check | Without scaling, interaction magnitude grows with `k`, so d=6 and d=8 differ in non-separability for reasons unrelated to dimension — and `f` could cross zero, which is unphysical and breaks the multiplicative noise model. |
| **Polynomial order in E4** | **Second-order primary; stepwise third-order descriptive only, interval omitted** | Three reasons. *Estimability:* second-order is 28 terms at d=6 (20 residual df at n=48) but 45 at d=8 (3 df, interval balloons for reasons unrelated to extrapolation); full third-order is 84 and 165 terms, rank-deficient at n=48 so `(XᵀX)⁻¹` doesn't exist. *Literature:* canonical and ridge analysis are second-order techniques. *Post-selection inference:* a stepwise model's interval is anticonservative — too narrow for selection reasons — which is fatal when "the interval is too narrow" is the finding. |
| **E4 dimension and `n_subbox`** | **d=6 only, `n_subbox = 48`** | Follows from estimability above. Matches the Ogle run count the paper argues against. |
| **DoE baseline — sequential, scoped** | Screen → CCD on the best region → second-order fit → stationary point | A resolution-IV design samples corners and centre only, so it **cannot represent an interior optimum** and loses by construction — a formality, not a baseline. Reproducing Ogle's exact 23-run design is out of scope: `1 + 6 + C(6,2) = 22` is the two-factor-interaction parameter count, so it is likely a D-optimal custom design, and coordinate-exchange is real work. **Phase 2 is the definitive DoE comparison — there you implement nothing.** |
| **Static-baseline ordering** | Randomize run order, average over orderings | A one-shot design has no regret *curve*; best-so-far is a step function set by arbitrary run order, so AUC over it is otherwise meaningless. |
| **Parametric comparator** | **Practitioner-form only** — additive biphasic, no interactions | An oracle-form fit is matched by construction, wins trivially, and tells you nothing. Log NLS convergence failures rather than dropping instances. |
| **Noise sweep** | **0.10 primary, 0.25 robustness** — dropped 0.35 | Two levels, not three. The sweep multiplies the grid and interacts with the depth criterion. |
| **Bootstrap** | **Instance level only** | Points within a run are sequential BO proposals and are not exchangeable, so resampling them is invalid. The instance-level resample does the real work. |
| **Parameter table** | Added a **"justified by"** column | The recurring failure across v3–v5 was fixing *derived* quantities while the quantity the experiment depends on floated. Naming the structural fact each range rests on turns the next structural change into a grep. |
| **Depth criterion — unsatisfiable, replaced** | **`minᵢ wᵢδᵢ ≥ 0.045`**, compared against the **pooled** standard error | v5's `f(x*) − max_{∂box} f > 3σ_rel·f(x*)` could not be met by any instance. With peak normalization the boundary maximum comes from moving one coordinate to 1, so `depth = minᵢ wᵢδᵢ`, and since `Σwᵢ = 1` that is bounded above by `1/d` — 0.167 at d=6 against a threshold of 0.30. Generation would never terminate. **The comparison must be against pooled SE, which is the same fact that makes Claim 1 about value rather than location.** |
| **Acceptance is noise-independent** | Floor frozen at the primary noise level; one ensemble, both noise levels | A `σ_rel`-dependent criterion changes the ensemble with the noise level, so the 0.10-vs-0.25 comparison would mix a noise effect with an ensemble effect. Instances unrecoverable at 0.25 are **the robustness finding**, not something to design away. |
| **Sampling — invert, don't reject** | Sample `(x*, n, δ)`; derive `r` from `V(1−c)s² + [2V − c(1+V²)]s + V(1−c) = 0`, root > 1 | Rejection sampling at the corrected floor would need all factors to clear simultaneously — a low acceptance rate producing a **hard truncation toward low `x*` and high `n` that we never chose and couldn't describe in the paper.** Inversion gives a stated ensemble and removes a global optimization per rejected candidate. Verified: `(0.4, 2, 0.414) → s = 3.9917 → r = 4`. |
| **`δ` sampled relative to `δ_max`** | `δ = u·δ_max(x*, n)`, `u ~ U(0.55, 0.9)` | Uniform `δ` isn't feasible — at low `x*` and low `n` the discriminant goes negative and no real root exists. A shallow-exponent factor peaking near the origin cannot decline 85% by `x = 1`. |
| **Weight draw narrowed** | `wᵢ ~ U(0.75, 1.25)` | Depth scales with `minᵢ wᵢ`, so a wide weight draw makes the acceptance floor hard to clear. |
| **`oracle_version` hashes acceptance parameters** | — | Under any rejection sampling the seed→instance map depends on the acceptance rule, since rejections consume RNG draws. Changing a threshold without a version bump makes the same `instance_id` denote a different landscape — the silent-mixing failure arriving through an uncovered door. |
| **E4 sub-box design specified** | **CCD-family, scaled into the sub-box; identical points for all four models** | `(XᵀX)⁻¹` — hence the polynomial's prediction interval, which *is* the discrimination comparator — depends entirely on the design. Also fairness: an RSM practitioner uses a CCD, and the PI formula is the formula for a designed experiment. Fitting to a space-filling sample and calling the intervals "what DoE gives you" is not what DoE gives you. |
| **E4a primary outcome changed** | **Over-prediction at each model's constrained argmax over the extended box.** Stationary-point location and Hessian class become descriptive. | Inside `[0, κ·x*]` you are on the rising arm, and for `n > 1` the Hill function is convex below its inflection — so at low κ the fit has positive curvature and its stationary point is a *minimum*. "Did the stationary point escape" then answers a question about a minimum. Over-prediction at the constrained argmax is always defined. **Note the discrimination test never touches the stationary point anyway** — it is Spearman ρ over a Sobol candidate set. The stationary point is the narrative hook, not the measurement. |
| **Discrimination null changed** | **Nearest-neighbour distance to the training set**, not centroid distance. **Report the scorer–scorer rank correlation matrix first.** | Nearest-neighbour is what GP predictive sd actually approximates; centroid distance ignores design geometry. If the GP has an edge it comes from ARD lengthscales making its distance anisotropic, so an isotropic null is the right thing to beat. And with the sub-box in a corner, all three scorers may rank-correlate above 0.95 — **the reader needs to see the headroom before the result.** |
| **DoE arm gets a confirmation run** | 47 design runs + **1 confirmation evaluation that enters the regret curve** | Without it the arm's best-so-far is just its best design point and the pipeline's actual output never counts. **Ogle evaluated TheO.** This also makes the confirmation run *be* E4a inside E2 — if it lands outside its own design region and under-delivers, the Ogle failure reproduces in the benchmark **without being staged for it.** |
| **Claim 1 tolerance** | Stated as a fraction of instance depth | Undefined tolerance risks exceeding depth, in which case a boundary point satisfies the claim and the claim is vacuous. |
| **Vocabulary** | "Phase" = project part; "Build Step" = code milestone | An earlier draft used "Phase" for both. |
| **Oracle structure — corrected** | **Biphasic factors**, `fᵢ = hᵢ·gᵢ` with `IC50ᵢ > EC50ᵢ` | **The v3 oracle was monotone in every coordinate**, so its optimum was always a corner: `h` increases, `g` decreases, `β > 0`, and activating/inhibitory dimensions were disjoint. E2 became corner-finding; E4 lost its mechanism, since a polynomial extrapolating past a monotone plateau is *directionally correct*. Biphasic gives true interior optima and is better biology. Closed form: `x*ᵢ = √(EC50ᵢ·IC50ᵢ)` when the exponent is shared. |
| **`Yvar` returned** | **Plug-in `ŷ²σ_rel² + σ_add²`**, analytic as ablation | Analytic variance is a function of the **noiseless** `f(x)`, so returning it hands the model `\|f\|` at every training point. Corrupting for E3 specifically, and it doesn't transfer — Phase 2 has no variance, Phase 3 has replicate SEM. |
| **Grid baseline — replaced** | **Resolution-IV fractional factorial with centre points** | At d=6 with 48 evaluations, 48^(1/6) ≈ 1.9 points per dimension; the minimum sensible grid is 2⁶ = 64. Grid is undefined at this budget. A fractional factorial is well-defined **and is the design family the Ogle lab actually ran.** |
| **E4 optimization domain** | **Both models optimized over the same extended box** (the unit cube) | v3 said "unconstrained optimization" for both. Incoherent for a GP, which reverts to prior outside its transform bounds. The polynomial's unconstrained stationary point is reported separately. |
| **E4 stationary-point handling** | **Hessian eigenvalue classification** (max / min / saddle / ridge), with ridge-analysis fallback | The classification *rate* across instances is more informative than the binary v3 recorded, and it connects the work to the RSM literature it must cite. |
| **E4 discrimination — model-free null added** | **Euclidean distance from the sub-box centroid** as a third scorer | "GP is uncertain far from data" is near-tautological. The sharper null needs no model at all. **If distance discriminates as well as GP predictive sd, the GP is an expensive distance function** — the comparison a reviewer reaches for. Spearman ρ is now primary; AUC at a pre-registered τ is secondary. |
| **Parametric comparator** | **Biphasic NLS model**, third arm in E4a | Without it, polynomial-versus-GP on an oracle whose shape we chose is a straw man. Note a monotone Hill/Emax would *also* be misspecified against a biphasic oracle — the comparator must be biphasic too. |
| **Outputscale** | **Config axis, learned as primary**, fixed-at-1 as ablation | Fixed at 1 with `Standardize` puts the far-field 95% interval at ≈ ±1.96 × training-sd in raw units. E4's sub-box sits where training sd is compressed, so the interval can be narrow for a reason unrelated to the hypothesis — and E4 then fails for the wrong cause. |
| **Calibration reporting** | **Hierarchical bootstrap CIs; held-out Sobol set alongside proposed points** | Coverage at 0.95 with n=48 has SE ≈ 3.1% — 95% and 89% are indistinguishable in one run. And prospective coverage at BO-proposed points is coverage *under a selection rule*, since acquisition targets high-sd regions. The gap between the two point sets is itself informative. |
| **Noise level** | **Sweep σ_rel at 0.10 / 0.25 / 0.35** | Flow-cytometry reproducibility literature and the CLSI H62 tiers put real assay CV well above 10%. Hall/Ogle normalize every plate to an FN control precisely because interexperimental variability is large — and report no CV for the CD31 readout. |
| **EC50 range** | Narrowed to U(0.15, 0.45) | At U(0.2, 0.7) with a sub-box of the lower 70%, roughly half of instances put half-max at or beyond the box edge — no plateau visible, nothing for the polynomial to turn over on. Pre-flight check 1 now reports a *rate* as a function of EC50 relative to the edge. |
| **Interaction count** | `k = ⌈d/2⌉` | `d//3` gave 2 pairs at both d=6 and d=8, so non-separability didn't scale with dimension. |
| **Instance identity** | `instance_id` hashes (dim, seed, **oracle_version**) | The oracle has already changed once. Without versioning, pre- and post-change results mix silently in the parquet. |

---

# PART H — VERIFICATION CHECKLIST

**Blocking for one sentence only, not for the build:**
- [ ] **Email Ogle (`ogle@umn.edu`)** for the underlying data, and ask which Collagen IV stage-1 high is correct — the Results section says 28 µg/mL, the Methods section says 56 µg/mL

**Before building:**
- [ ] Run all four pre-flight checks in Document 1 §7
- [ ] Confirm `get_covar_module_with_dim_scaled_prior` signature on the installed botorch
- [ ] Confirm `Normalize` bounds behaviour on the installed botorch
- [ ] Confirm the discrete-candidate acquisition function's name and signature
- [ ] Replace Document 1 §3's timing estimates with measurements

**Before writing:**
- [ ] Confirm the stage-1 and stage-2 run counts against Tables 1 and 2
- [ ] Confirm Narayanan repo is accessible and figshare data downloads
- [ ] Confirm Summit's license before any redistribution
- [ ] Verify the Ax `AxClient` removal version before citing it
- [ ] **Ask the lab the five questions in §E.2**
- [ ] Settle author order and public-release permissions
