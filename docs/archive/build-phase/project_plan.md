# PROJECT PLAN
## Bayesian Optimization for hiPSC → Endothelial Differentiation

**Document 2 of 3.** Project context, the scientific argument, Phase 2 and 3 plans, research grounding, design rationale.
**Document 1** (`phase1_build.md`) — the buildable specification for the current phase.
**Document 3** (`source_verification.md`) — which factual claims are confirmed against primary sources.

**Owners:** 2 people · **Client:** NutriGeneAI · **Horizon:** **14 days.**
**Current position:** Phase 1, day 1.

> **The 14-day horizon overrides every schedule in this document.** Where the original text says "weeks", read it as a statement of *ordering*, not duration. Phase 3 is out of scope at this horizon. See §A.4.

---

# PART A — CONTEXT

## A.1 Setting

Internship engagement with NutriGeneAI. Two people, **14 days**. The deliverable is a **publishable research paper** plus a reusable software tool the company keeps.

Five AI-automation proposals were produced earlier for NutriGeneAI stakeholders. This is **Proposal #1: Bayesian optimization for iPSC-EC cytokine priming**, chosen because the client explicitly named Bayesian optimization. The other four are out of scope.

## A.2 The problem

NutriGeneAI works on **hiPSC → endothelial cell differentiation**. Efficiency depends on a large combinatorial space: extracellular matrix coating composition, cytokine and growth factor concentrations, timing, inhibitor use.

Standard readout: **CD31 (PECAM-1) positive area normalized to DAPI area** by immunofluorescence around day 10, or CD31⁺ percentage by flow cytometry. These are different numbers and cannot be mixed within a campaign.

The field optimizes these protocols by Design of Experiments — a structured screen of conditions, then a polynomial response surface fitted to the results. It works, but at roughly 48 conditions and two weeks per condition it is expensive.

## A.3 The three phases

| Phase | Data source | What it establishes | Lab dependency |
|---|---|---|---|
| **1** | Fake (synthetic oracle) | The code is correct, efficient, and well-calibrated | None |
| **2** | Published (Hall/Ogle 2025) | **BO reaches their best result in fewer experiments than the ~48 they ran** | None |
| **3** | In-house wet lab | The loop closes on live cells | Full |

**Phase 2 is the paper.** Phase 1 is the control experiment that makes Phase 2's numbers believable. Phase 3 is proof-of-concept.

Phases 1 and 2 are deliberately lab-independent. **If the wet lab slips, the paper still ships without Phase 3.** That is a structural design decision, not a fallback.

## A.4 Timeline — 14 days

| Days | Work |
|---|---|
| 1 | Gate 0 interface contract. Gate 1 pre-flight, all four checks, read together. |
| 2–5 | **Build the optimizer.** A: space, oracles, evaluators, designs. B: surrogate, campaign, optimizers, runner, metrics, rsm. |
| 6–9 | **Phase 1 experiments.** A: E2, E3. B: E4. |
| 8–11 | Digitize the published figures — both people independently, then reconcile. Runs in parallel with the tail of Phase 1. |
| 10–13 | Phase 2 replay. Uncertainty analysis at the published optimum. |
| 13–14 | Write, figures, preprint. |

**Phase 3 is out of scope.** A wet-lab round is 10–14 days on its own. Nothing in this schedule depends on it, which was the original design decision — see §A.3.

**What the compression costs.** The grid shrinks before the science does: fewer instances and seeds before any experiment is dropped, and the second noise level goes before the first. Digitization is the one item that cannot be compressed by running it worse, because the independent-double-reading *is* the error estimate.

## A.5 Venues

bioRxiv preprint first — free, one day, timestamps the work. Then *Bioinformatics Advances*, *Digital Discovery*, or *SoftwareX*. *Biotechnology and Bioengineering* if Phase 3 lands, since they publish the bioprocess BO work this builds on. Not a stem-cell journal — they want more biology than this produces.

## A.6 Open items

Author order. Whether code and digitized data can be released publicly. Whether anything from the lab rounds needs IP protection before the preprint goes up.

---

# PART B — THE SCIENTIFIC ARGUMENT

## B.1 What the paper claims

A response surface fitted to experimental data returns a prediction **and** a prediction variance — `Var[ŷ(x₀)] = σ̂²·x₀ᵀ(XᵀX)⁻¹x₀`. This is standard: variance dispersion graphs, scaled prediction variance, and fraction-of-design-space plots are all built on it, and extrapolation error beyond the investigated region is a named, documented limitation in that literature.

**So the argument is not that DoE lacks uncertainty. It is about what kind of uncertainty each method expresses.**

**1. A low-order polynomial basis is a poor fit for saturating dose-response biology.** Growth-factor and matrix responses rise and plateau. A polynomial fitted to that shape can place its fitted optimum outside the region where data was collected.

**2. Polynomial prediction variance is design-geometry-based; GP variance is distance-to-data-based.** `σ̂²x₀ᵀ(XᵀX)⁻¹x₀` grows with leverage — how far `x₀` sits from the design centroid in the metric the design induces. It quantifies uncertainty **conditional on the model form being correct**. It has no mechanism to express doubt about the form itself. A GP's posterior variance grows with distance to observed data and reverts toward the prior far from it.

**Stated precisely:** when the true response saturates and the fitted model is a low-order polynomial, the polynomial can produce an over-confident extrapolated optimum that its own prediction interval fails to flag, while a GP fitted to identical data does flag it.

**This is an empirical claim, not a mathematical necessity.** Whether it happens depends on the surface and the design. Phase 1's Experiment 4a measures the rate on surfaces whose shape we control; pre-flight check 1 verifies it happens at all before anything is built on it.

**Both intervals must be reported.** Comparing a GP posterior against a bare polynomial point estimate is not a fair comparison.

## B.2 Positioning against the RSM literature

An extrapolated stationary point outside the design region is a **named, standard topic in response-surface methodology**. Canonical analysis identifies the stationary point's nature; **ridge analysis** (Hoerl 1959; Draper 1963) handles the case where it falls outside the region. Box & Draper and Myers & Montgomery cover it. Lack-of-fit testing flags model inadequacy where replicates exist.

**So position the contribution accurately.** DoE has tools that cover this ground, and the published study had replicates, so lack-of-fit was available to it. The failure was not that DoE *cannot* detect this — it is that the diagnostic wasn't run.

**What the GP adds** is not a capability the DoE toolbox lacks, but **a single continuous uncertainty field over the whole space that feeds directly into the next decision**, rather than three separate diagnostics a human must remember to run and interpret. That is an automation-and-integration argument. State it that way.

**Cite the RSM literature explicitly** and frame the contribution as *automated, calibration-based detection quantified against model-free nulls*. If a reviewer can point to a prior paper doing GP-versus-polynomial extrapolation detection on saturating biological surfaces, drop novelty language entirely and present it as a clean reproducible demonstration plus tooling.

## B.3 What survives independently

**The efficiency claim.** "BO reaches the same answer in fewer experiments than DoE" is a capability claim that does not depend on ridge analysis, calibration, or Experiment 4. It is measurable against published data, with the original authors' own DoE as the comparison arm.

**That is the paper.** The uncertainty work is a supporting section requiring honest framing and a correctly specified parametric comparator.

## B.4 The Hall/Ogle case

Hall, Lin & Ogle (*Scientific Reports* 2025, 15:24479) optimized ECM coating for hiPSC→EC differentiation with two-stage DoE, fitting a response surface with terms up to third order. It predicted an optimum they called **TheO**: 35.6 µg/mL Collagen I, 67.2 µg/mL Collagen IV, 0.9 µg/mL Laminin 411, 22 µg/mL Fibronectin.

They made it. They tested it. **It produced very little endothelial differentiation, around the level seen on fibronectin alone.**

The authors' own explanation, verbatim: *"the reason for the discrepancy is likely due to use of an on face central composite design which does not allow for accurate modeling outside of the original parameter space."*

### B.4.1 The extrapolation detail — unresolved in the source

Whether Collagen IV's 67.2 µg/mL exceeded the tested range depends on an internal inconsistency in the published text.

- **Results section:** stage-1 highs were 35.5, **28**, 15.8, 0.8, 0.8, 75 µg/mL
- **Methods section:** stage-1 highs were 35.5, **56**, 15.8, 0.8, 0.8, 75 µg/mL

Every value matches except Collagen IV, and 56 = 2 × 28 — which matters because the Results state the highs for Collagen I, Collagen IV, and Laminin 411 were *"increased by a factor of 2 for the subsequent response surface regression."*

| If the stage-1 high is… | Stage-2 high is… | TheO's 67.2 is… |
|---|---|---|
| 28 (Results) | 56 | **outside** the tested range |
| 56 (Methods) | 112 | **inside** |

**Circumstantial support for the Results reading:** of TheO's four values, Collagen IV would be the only one outside its range (Collagen I 35.6 in [0,71], Laminin 411 0.9 in [0,1.6], Fibronectin 22 at its floor). And the authors' own explanation — a design that cannot model outside the original parameter space — only makes sense if something was outside.

**Table 2 will not settle it.** Its run pattern is coded (minus, zero, plus), not absolute. **This will not be resolved — we are not contacting the authors.** Treat it as permanently open and do not write the sentence that depends on it.

**This blocks exactly one sentence** — the one asserting 67.2 exceeded 56. It does not block the replay, the efficiency comparison, or the uncertainty analysis, all of which work in coded space.

### B.4.2 The biological explanation

The paper also reports that **TheO without fibronectin — which they rename EO — worked very well**, better than their previously published formulation. Their explanation is mechanistic and supported by intervention experiments: fibronectin activates TGFβ signalling, which inhibits endothelial specification. A TGFβ inhibitor rescued differentiation on TheO; adding TGFβ suppressed it on EO.

And critically: *"the model used did not allow for concentrations of FN below 22 µg/mL to be evaluated,"* with TheO sitting at that floor because *"the TheO formulation indicated the lowest FN concentration would lead to the highest CD31 expression."*

**So the DoE correctly wanted less fibronectin and was structurally unable to ask for it.** That is a **design-boundary** failure, not an extrapolation failure — and the response surface flagged it correctly. The authors read the signal and tested TheO-minus-FN because of it.

**TheO's failure has at least two contributing causes, and they must be separated:**

| Cause | Nature | Does the GP help? |
|---|---|---|
| Collagen IV possibly extrapolated beyond the tested range | Modelling-uncertainty problem | **Yes — this is the claim** |
| Fibronectin optimum below the design floor | Design-space problem | **No.** The polynomial signalled it correctly. |

**Claim the first. Report the second honestly.** Phase 1's Experiment 4 tests them as E4a and E4b for exactly this reason.

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
| 1 | `SyntheticEvaluator` | Calls the oracle. Instant. |
| 2 | `LookupEvaluator` | Indexes the digitized table. Instant. |
| 3 | `HumanEvaluator` | Writes a CSV of proposed conditions, waits ~2 weeks, reads results back. |

Each is roughly 40 lines. Build `SyntheticEvaluator` now.

## C.2 The nine requirements

Build requirements are in Doc 1 §2. Here is why each exists.

| # | Requirement | Which phase needs it |
|---|---|---|
| 1 | Ask/tell separation | 2 and 3 — the basis of swapping evaluators |
| 2 | **Discrete candidate mode** | **2 — see C.3** |
| 3 | Search space in config, coded [0,1] | 2 (digitized figures are coded) and 3 (whatever the lab varies) |
| 4 | Mixed parameter types in the schema | 3 — categorical base medium, integer treatment days |
| 5 | Always pass `Yvar`, imputed where unreplicated | 3 will have replicated and unreplicated points together, and one `SingleTaskGP` cannot mix likelihoods |
| 6 | Serialize data + config + RNG state; refit on resume | 3 runs over weeks; refitting is robust across BoTorch versions |
| 7 | Metric identity on every row | 3 — CD31% by flow and CD31 area by IF must never mix |
| 8 | Constraint hooks threaded through config | 3 will have protein caps and plate arithmetic. **And the Hall/Ogle failure was itself a constraint problem** — the true optimum needed FN = 0 against a design floor of 22 µg/mL. |
| 9 | `X_pending` / in-flight proposal tracking | 3 with humans means staggered, asynchronous returns |

## C.3 Discrete candidate mode

**In Phase 2 the optimizer can only propose conditions that already exist in the published dataset**, because those are the only ones with measured outcomes. You cannot let the model search freely — there would be nothing to look up.

The acquisition step must therefore support choosing the best `q` from a **fixed candidate set** as well as searching continuously. Roughly twenty lines now; a structural change to the optimizer's core later.

**This is also a stated limitation of the paper.** Replay from a fixed menu is easier than free search, so the efficiency numbers are conservative — a free search would likely do better, not worse. Say it before a reviewer does.

## C.4 Coded space

Phase 1's search space is canonically coded `[0,1]`. Phase 2's digitized data is coded by construction. Phase 3's lab variables get coded against whatever min/max the lab declares.

**One representation, three phases, no unit conversion anywhere.**

## C.5 Replicate structure — flagged, not yet specified

Hall/Ogle collected at least 4 wells from at least 3 experimental replicates per condition. That is a **nested** structure, and treating wells as independent inflates precision. Phase 3 will have the same shape.

The pooling story — well-level mean with a random-effects variance, versus condition-level mean with replicate SEM — is a Phase 2/3 modelling decision. It does not affect the Phase 1 build, but requirement 5's `Yvar` policy is where it lands, so decide it before Phase 2 data arrives.

---

# PART D — PHASE 2 PLAN

## D.1 Primary dataset

**Hall, Lin & Ogle 2025**, *Scientific Reports* 15:24479, open access.
`https://www.nature.com/articles/s41598-025-09256-9`

| | |
|---|---|
| Stage 1 | Factorial screen across Collagen I, Collagen IV, Laminin 111, Laminin 411, Laminin 511, Fibronectin. Low = 0 for all except Fibronectin at 22 µg/mL (lowest concentration with good attachment), plus one centre point. |
| Stage 2 | On-face central composite design on the four proteins carried forward: Collagen I, Collagen IV, Laminin 411, Fibronectin. Response surface fitted with **terms up to third order**, stepwise-reduced to significant terms. |
| Readout | CD31 area ÷ DAPI area by immunofluorescence at day 10, normalized to a fibronectin control. At least 4 wells from at least 3 experimental replicates. |
| Software | JMP |
| Total conditions | **~48 — not confirmed.** The 23 + 25 split comes from earlier project notes; the tables were not retrievable. Verify. |

**Data availability:** the paper states per-condition data is available on request from the authors. **We are not requesting it.** Phase 2 therefore runs entirely on values digitized from the published figures — which is why §D.2's coded-space approach is not a convenience but the only route.

**Key findings:** Collagen I + Collagen IV + Laminin 411 (their EO formulation) drives high endothelial differentiation. The Matrigel comparison is **transitive, not direct** — the paper shows EO > LN411+FN, and cites their own earlier work for LN411+FN > Matrigel. State it that way. VEGF improves outcomes; TGFβ inhibits specification.

## D.2 Working in coded space

**The replay runs entirely in coded [0,1] coordinates.** Digitize the bar charts; the heatmaps below them give coded levels directly, per the figure captions. Absolute concentrations are never needed.

This sidesteps the §B.4.1 contradiction for everything except the single sentence about 67.2 versus 56.

## D.3 The replay experiment

Give the GP only the first N conditions from the dataset, in the order they were run. The model proposes what it would test next, restricted to the fixed candidate set. Look that condition up in the remaining data and feed back the real measured value. Repeat.

**The question:** how many conditions does the model need before it reaches the best value in their dataset, compared to the ~48 actually run?

Phase 1's Experiment 2 uses a budget of 48 for exactly this reason — the numbers read directly against each other.

## D.4 The uncertainty analysis at TheO

Fit the GP to the stage-2 data. Query at TheO's coded position. Record predicted mean and predictive interval; compare against conditions well inside the sampled region. **Also compute the published model's own prediction interval at TheO** — the comparison is GP interval versus polynomial interval, never GP interval versus polynomial point estimate.

**Report the fibronectin caveat alongside it**, per §B.4.2.

## D.5 Secondary dataset

**Hou et al. 2017**, *Scientific Reports*, open access.
`https://www.nature.com/articles/s41598-017-06986-3`

63 combinatorial coating conditions from six components, CD31 readout, three cell lines. Same replay procedure. Results are in a heat map, so values are harder to read than bars. Shows the method generalizes across studies rather than working on one dataset by luck.

## D.6 Method precedent

**Narayanan et al. 2025**, *Nature Communications* 16:6055. BO of culture media with eight cytokines. Data on figshare, code on GitHub (MIT). Wrong cell type, so it contributes nothing to the biological argument — but it downloads cleanly, so it is the development target and the method-precedent citation.

## D.7 Limitations to state

- Replay is easier than prospective optimization; the answer is already in the dataset. Efficiency numbers are a lower bound on difficulty.
- **Replay can only select from conditions actually run, not search freely.** Conservative — say it first.
- **The published optimum is the discrete argmax of ~48 points.** "BO finds it in k < 48 picks" partly measures ordering rather than optimization. Scope the claim to *"recovers the published discrete argmax in k picks."*
- **The true best formulation is not in the replay space at all.** EO is TheO minus fibronectin, below the design floor of 22 µg/mL. A faithful replay **cannot reach the answer the authors ultimately found.** State this before a reviewer does.
- **The surface being replayed is itself a model artifact** — the authors ran a JMP-chosen design, so the 48 points reflect that design's assumptions, not ground truth.
- Digitized values carry reading error, and their noise is unknown. Report the extraction method.
- TheO's failure has at least two causes; only one is a modelling-uncertainty problem.
- The extrapolation detail rests on an unresolved contradiction in the source (§B.4.1).

---

# PART E — PHASE 3 PLAN

## E.1 Structure

**Round 1 — seed batch.** Sobol sampling across the search space. As many conditions as the lab can run at once, ideally 12 or more. Each in at least triplicate. Nothing is being predicted yet; this gives the model something to learn from.

**Round 2 — model-proposed batch.** Fit the GP to round 1. Optimize the acquisition function. A scientist reviews and approves the proposed conditions before anything runs. Same size, same triplicate structure.

**What gets compared:** best outcome in round 2 versus round 1. Replicates give a standard deviation per condition; if the round-2 best exceeds round-1 by more than the combined variability, the improvement is real. Run a t-test and report the p-value. **If the intervals overlap, say so** rather than claiming an improvement that isn't there.

**Why batch size matters more than round count.** At 2–3 weeks per round you realistically get two rounds. The only remaining lever is how much you learn per round, which is set by batch size. Twelve conditions teaches the model substantially more than six.

**Replicates also feed the model.** The GP takes observation variance as an input. Passing measured replicate variance rather than assuming a fixed noise level makes the surrogate more accurate.

## E.2 What is needed from the lab — ask now

| Item | Detail |
|---|---|
| **Variables and ranges** | Which protocol parameters can be varied, min/max for each. Anything held fixed must be declared fixed. **And which bounds are hard physical constraints versus conventional defaults** — the Hall/Ogle fibronectin floor of 22 was a hard attachment limit, and the true optimum was below it. The optimizer should know the difference. |
| **Constraints** | Combinations that are biologically or practically impossible. Any cost or reagent ceiling. Encoded so the optimizer never proposes the unrunnable. |
| **Metric definition, locked** | Exactly what is measured and how. **CD31% by flow cytometry and CD31 area by immunofluorescence are different numbers and cannot be mixed across rounds.** Whichever is chosen gets versioned and recorded on every row. |
| **Throughput and turnaround** | Conditions per batch; days from seeding to readout. Sets `q` and the round budget. |
| **Existing data** | Historical experiments with conditions and outcomes recorded. **If there are enough and they are spread across the range rather than clustered, round 1 can be skipped.** The question is spread, not count. |

## E.3 The budget arithmetic — check this before committing to a factor list

The initial design needs roughly `2d + 2` space-filling points before the optimizer can propose anything.

| Factors | Seed runs | Budget 24 | Budget 48 | Budget 96 |
|---|---|---|---|---|
| 4 | 10 | 14 left to optimize | 38 | 86 |
| 6 | 14 | 10 left | 34 | 82 |
| 8 | 18 | 6 left | 30 | 78 |
| 10 | 22 | **2 left** | 26 | 74 |
| 12 | 26 | **budget exhausted** | 22 | 70 |

At 12 conditions × 2 rounds = 24 evaluations, ten factors leaves two adaptive experiments. **This is arithmetic, not a code limitation**, and quantifying it on the synthetic oracle costs an afternoon and no lab time. It answers the question the client actually has: *how many factors can we afford to vary?*

## E.4 Data format

One row per experimental arm:

```
each variable (units in header) · each measured outcome · replicate SD ·
number of replicates · batch ID · operator ID · date ·
assay protocol version · approver
```

Getting this right from the first experiment saves substantial cleanup. It is why contract requirement 7 exists.

## E.5 Limitations to state

- Two rounds demonstrate the loop closes. They do not demonstrate a converged optimum.
- The method is software-validated and tested against published biology. It is not biologically validated on NutriGeneAI's system beyond two rounds.

## E.6 Deferred work that belongs here

| Item | Why Phase 3 |
|---|---|
| **Batch-effect modelling** | Passage and lot-to-lot variation are large in stem-cell work. Round index should enter the model as a categorical dimension or fixed effect. |
| **Bounded-proportion response** | CD31⁺/DAPI is bounded with variance shrinking at both ends. A Gaussian likelihood is misspecified precisely near the top of the range. Consider a logit transform and benchmark it. |
| **Replicate-count study** | Real `Yvar` from n=3 has ~2 degrees of freedom — a poor estimate. Benchmarking exact versus 3-replicate variance tells the lab how many replicates to run. A genuine client deliverable. |
| **Round-budget framing** | Wet-lab cost is *rounds* (~10–14 days each), not evaluations. Client plots should show progress versus rounds at fixed plate capacity. |
| **Initial-design size as a factor** | See §E.3. At realistic budgets this is plausibly the highest-leverage knob. |
| Outlier robustness, non-stationarity | Realism work. |
| Multi-objective (qLogNEHVI) | The published readout is single-objective, so Phase 2 doesn't need it. Efficiency versus reagent cost is the natural pair when it arrives. |

---

# PART F — RESEARCH GROUNDING

## F.1 Published precedent

**Narayanan et al. 2025**, *Nature Communications* 16:6055 (DOI 10.1038/s41467-025-61113-5, CC-BY 4.0). Optimized a 4-media blend under a sum-to-100% constraint, an 8-cytokine cocktail (IL-2, IL-3, IL-4, IL-7, IL-12, IL-15, IL-21, BAFF), and 4-factor carbon-source media for *K. phaffii* with a categorical factor. GP surrogate with an Upper Confidence Bound acquisition function; a custom categorical kernel reported 33–50% smaller error than one-hot encoding; space-filling initial designs, small batches. Efficiency saving scales with factor count: roughly threefold fewer experiments than state-of-the-art DoE at modest counts, 10–30× at nine factors. PBMC blend: 24 experiments. Yeast: 90 over 7 iterations. Code: `github.com/NHarini-1995/CellCultureBayesianOptimization`, Zenodo 10.5281/zenodo.15466161.

*Their continuous kernel is not specified in what was retrieved. Do not cite them as evidence for a particular kernel choice.*

**Kanda, Natsume et al.**, *eLife* 2022;11:e77007. Batch Bayesian optimization on a LabDroid robot for iPSC→retinal pigment epithelium differentiation, seven parameters, pigmented area readout. From roughly 200 million combinations, 143 conditions over 111 days, 88% improvement over the pre-optimized protocol. 216 forty-day experiments, ~8,640 experiment-days. **The canonical iPSC-differentiation-by-BO paper.**

**Hall, Lin & Ogle**, *Scientific Reports* 2025, 15:24479 — **DoE, not BO.** Baseline and data source. See Part B.

Also: **Bader et al. 2023** (multi-objective batch BO, MSC-derived extracellular vesicles, 4 process parameters, 3 objectives, 32 experiments, Latin-hypercube seeded) · **Gisperg et al.**, "Bayesian Optimization in Bioprocess Engineering — Where Do We Stand Today?", *Biotechnology & Bioengineering* 122(6):1313–1325, 2025 (the framing review) · **Cosenza, Astudillo, Frazier, Baar & Block**, multi-information-source BO of culture media, *Biotech & Bioeng* 2022 · **Romero, Krause & Arnold**, *PNAS* 2013 (origin of this machinery in biology).

## F.2 Reference repositories

| Repo | URL | License | Why |
|---|---|---|---|
| CellCultureBayesianOptimization | `github.com/NHarini-1995/CellCultureBayesianOptimization` | — | Narayanan's code. Closest template. |
| Honegumi | `github.com/sgbaird/honegumi` | MIT | Generates unit-tested Ax/BoTorch scripts. Diff against yours as a sanity check. |
| BoFire | `github.com/experimental-design/bofire` | — | BASF-led. Mixed variables, nonlinear constraints. |
| BayBE | `github.com/emdgroup/baybe` | Apache-2.0 | Merck KGaA. Low-data regime, transfer learning. |
| Olympus / Atlas | `github.com/aspuru-guzik-group/olympus`, `/atlas` | MIT | Benchmarking, self-driving-lab control. |
| Summit | `github.com/sustainable-processes/summit` | verify | Chemical DoE+BO benchmarks. |

## F.3 Version and API notes

**`botorch` 0.18.1**; Python ≥3.11, PyTorch ≥2.2, GPyTorch ≥1.15.1; MIT. Repo at `meta-pytorch/botorch`.

**`ax-platform` 1.3.1**; Python ≥3.11; MIT. Ax 1.0.0 introduced `ax.api` with `Client`. `AxClient` carries a deprecation warning; **the removal version is unverified — do not cite a specific version.** Phase 1 doesn't use Ax at all. Phase 3 may, for trial tracking and JSON checkpointing.

**Verified from source and documentation:**

- `get_covar_module_with_dim_scaled_prior(ard_num_dims, batch_shape=None, use_rbf_kernel=True, active_dims=None)` returns `MaternKernel | RBFKernel` — **a bare kernel, no `ScaleKernel` wrapper**
- `use_rbf_kernel` defaults to `True`, so **the Matérn override is required**
- The lengthscale prior is `LogNormalPrior(loc=SQRT2 + log(ard_num_dims)*0.5, scale=SQRT3)`, **constrained above 0.025** for numerical stability
- The legacy configuration is available via **`get_matern_kernel_with_gamma_prior`**
- `loo_cv` **does not refit the model per fold**; its documentation states hyperparameters are kept fixed as a fast approximation and recommends `batch_cross_validation` where hyperparameter changes matter
- `batch_cross_validation(model_cls, mll_cls, cv_folds, fit_args=None, observation_noise=False)` fits separate models with separate hyperparameters. **Note the `observation_noise=False` default** — pass `True` for coverage of measurements
- `FixedNoiseGP` merged into `SingleTaskGP`; `HeteroskedasticSingleTaskGP` removed (PR #2616)

**On the kernel default.** BoTorch switched from Matérn to RBF with a dimension-scaled LogNormal prior in version 0.12, following Hvarfner et al., ICML 2024. Four things changed at once: kernel, lengthscale prior, noise prior, and outputscale handling. **The kernel component specifically is not well justified** — in BoTorch Discussion #2451, a user questions the RBF switch and notes the common belief that Matérn's roughness suits real-world problems; Hvarfner replies that he agrees the RBF-versus-Matérn motivation is not well justified. Another participant reports better performance with `use_rbf_kernel=False` in some cases.

## F.4 Benchmarking practice

**Standard test functions.** Branin (2-D, smoke test) · Hartmann6 (6-D, deceptive, the workhorse) · Ackley (needle-in-haystack, tests exploration; BO can genuinely lose) · Rosenbrock (ill-conditioned). Multi-objective: Branin-Currin, ZDT, DTLZ.

**Seeds and instances.** *npj Computational Materials* (2021) used 50 seeds; the Black-Box Challenge analysis ran 100 repeats. But seeds on one landscape measure within-landscape noise — **across-instance variance is usually larger**, so instances × seeds beats seeds alone at fixed compute.

**"BO beats random" citation:** Turner, Eriksson, McCourt, Kiili, Laaksonen, Xu & Guyon (2021), PMLR v133:3–26 (arXiv 2104.10201).

**Critiques to pre-empt:** too few seeds or no variance reported · **tuning your own method while leaving baselines at defaults** · cherry-picked functions · over-tuning to a fixed seed. Sources: Eggensperger et al. on algorithm configuration; arXiv 2505.07750; arXiv 2511.16230.

*J. Mater. Res.* 2026 (arXiv 2504.03943) advocates simulating before wet-lab to verify budget adequacy — a citable justification for Phase 1 existing.

**Calibration:** Acharki, Bertoncello & Garnier, *Computational Statistics & Data Analysis* 2022 (arXiv 2106.05396) for leave-one-out coverage. Gneiting & Raftery 2007 for proper scoring rules.

---

# PART G — DESIGN RATIONALE

Why the main choices are what they are. Useful for the methods section and for anyone questioning a decision.

| Choice | Rationale |
|---|---|
| **Matérn 5/2 kernel with dimension-scaled LogNormal priors** | Matérn was BoTorch's default before 0.12 and remains a common choice in the surrounding literature; the dimension-scaled priors are the evidenced improvement. **The RBF-versus-Matérn question is explicitly unsettled** per the author of the work that motivated the change (§F.3), which is why a calibration-scored comparison stays on the critical path rather than being asserted away. Requires `use_rbf_kernel=False`; the default is RBF. |
| **qLogEI / qLogNEHVI** | Classic Expected Improvement has vanishing gradients over most of the domain, so the acquisition optimizer gets stuck. qLogEI is EI in its numerically stable log form. |
| **Raw BoTorch for Phase 1** | Ax's trial-management machinery suits lab-in-the-loop campaigns, not thousands of benchmark runs. Ax may enter at Phase 3. |
| **Coded [0,1] as canonical** | Phase 2's digitized figures report coded levels only, and the source is internally inconsistent on absolute concentrations. One representation across all three phases, no unit conversion. |
| **Biphasic oracle factors** | High-dose ECM and growth factors are genuinely inhibitory, so it is the correct biology — and it produces a true interior optimum. Monotone factors would put the optimum at a box corner, which any method finds trivially. |
| **Parameterizing by peak location and depth** | Depth is what Claim 1 depends on and peak position is what E4's mechanism depends on, so those are the quantities to control directly rather than derive. Sampling the arms independently makes both float. |
| **Peak normalization** | Unnormalized peak height spans a 2.7× range, so equal weights would not mean equal influence, and the non-separability and SNR checks would measure that confound. |
| **Sub-box defined relative to the peak** | E4 needs extrapolation, E2 needs a measurable peak, and satisfying E4 by raising the peak flattens it. A peak-relative training box makes E4's mechanism independent of peak location. |
| **Noise-independent acceptance criterion** | A `σ_rel`-dependent criterion would change the ensemble with the noise level, so the two-noise comparison would mix a noise effect with an ensemble effect. |
| **Second-order polynomial primary in E4** | Estimability (28 terms at d=6 with 20 residual df; third-order is rank-deficient at n=48), the RSM literature being second-order, and post-selection inference invalidating a stepwise model's interval — which is fatal when "the interval is too narrow" is the finding. |
| **E4 at d=6 only** | Second-order at d=8 leaves 3 residual df, and the interval balloons for reasons unrelated to extrapolation. Also matches the published run count. |
| **CCD sub-box design** | `(XᵀX)⁻¹` — hence the polynomial's prediction interval, the comparator in the discrimination test — depends entirely on the design. And a response-surface practitioner would use a CCD, so fitting to a space-filling sample and calling the intervals "what DoE gives you" would misrepresent DoE. |
| **Nearest-neighbour distance as the discrimination null** | "The GP is uncertain far from data" is near-tautological. Nearest-neighbour distance is what GP predictive sd approximates, so it is the sharpest model-free comparator. If the GP has an edge it comes from ARD lengthscales making its distance anisotropic. |
| **DoE arm evaluates its predicted optimum** | Without it the arm's best-so-far is just its best design point and the pipeline's output never enters the regret curve. The published study evaluated its predicted optimum. This also makes the confirmation run *be* E4a inside E2. |
| **Practitioner-form parametric comparator only** | An oracle-form fit is matched by construction, wins trivially, and tells you nothing. |
| **Sequential DoE, not a fractional factorial** | A resolution-IV two-level design samples corners and centre points only and cannot represent an interior optimum, so it would lose by construction. |
| **Instance-level bootstrap** | Points within a run are sequential BO proposals and are not exchangeable, so resampling them is invalid. |
| **10 instances × 5 seeds** | Across-landscape variance dominates within-landscape noise, and the grid fits an overnight run. |
| **Laptops, CPU, no GPU** | GP fits at n<100 are CPU-bound; GPU transfer overhead exceeds the compute at this scale. |

---

# PART H — VERIFICATION CHECKLIST

**No author contact.** We are not emailing the original authors for data or clarification. Everything Phase 2 needs is digitized from the published figures in coded space. The Collagen IV Results-vs-Methods contradiction stays permanently open — see §B.4.1.

**When Phase 3 becomes real:**
- [ ] Ask the lab the five questions in §E.2 (variables, constraints, metric, throughput, existing data)

**Before building:**
- [ ] Run all four pre-flight checks in Doc 1 §7 — *PF3 and PF4 are Person B's; PF3 is done, see `docs/preflight-findings.md`*
- [x] Confirm `get_covar_module_with_dim_scaled_prior` signature on the installed botorch
- [x] Confirm `Normalize` bounds behaviour on the installed botorch
- [x] Confirm the discrete-candidate acquisition function's name and signature
- [x] Confirm what `observation_noise=True` does under a fixed-noise likelihood at an unevaluated input
- [x] Replace Doc 1 §3's timing estimates with measurements

**Before writing:**
- [ ] Confirm the stage-1 and stage-2 run counts against Tables 1 and 2
- [ ] Confirm the Narayanan repository is accessible and the figshare data downloads
- [ ] Confirm Summit's license before any redistribution
- [ ] Verify the Ax `AxClient` removal version before citing it
- [ ] Settle author order and public-release permissions
