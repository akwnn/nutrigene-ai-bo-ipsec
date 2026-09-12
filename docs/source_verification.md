# SOURCE VERIFICATION
## Which factual claims are confirmed, and which still need checking

**Document 3 of 3.** Reference for anyone writing the paper or defending a claim.
**Document 1** (`archive/build-phase/phase1_build.md`) — the buildable specification.
**Document 2** (`archive/build-phase/project_plan.md`) — project context, scientific argument, phase plans.

**Purpose.** Every substantive factual claim used in this project, sorted by evidence status. Cite freely from Part 1. Verify before citing from Part 3. Never present Part 4 as anything but our own choices.

---

# PART 1 — CONFIRMED AGAINST PRIMARY SOURCES

## 1.1 Hall, Lin & Ogle 2025 — verified from full text

DOI 10.1038/s41598-025-09256-9, *Scientific Reports* 15:24479, open access.

| Claim | Status |
|---|---|
| The response surface was fitted with **terms up to third order**, stepwise-reduced to significant terms | ✅ Results section and Figure 2 caption |
| TheO = 35.6 µg/mL Collagen I, 67.2 µg/mL Collagen IV, 0.9 µg/mL Laminin 411, 22 µg/mL Fibronectin | ✅ exact |
| TheO produced very little differentiation, around the level seen on fibronectin alone | ✅ exact |
| Authors attribute the discrepancy to an on-face central composite design not allowing accurate modelling outside the original parameter space | ✅ exact, direct quote |
| Readout: CD31 area per DAPI area by immunofluorescence, normalized to the fibronectin control | ✅ |
| Analysed at day 10 of differentiation | ✅ |
| At least 4 wells from at least 3 experimental replicates | ✅ |
| Six proteins; low = 0 for all except fibronectin at 22 µg/mL, the lowest concentration with good attachment | ✅ |
| Stage 2 = on-face central composite design on Collagen I, Collagen IV, Laminin 411, Fibronectin | ✅ |
| The highs for Collagen I, Collagen IV, and Laminin 411 were doubled for the response-surface stage | ✅ |
| The model did not allow fibronectin concentrations below 22 µg/mL to be evaluated | ✅ exact |
| TheO minus fibronectin (EO) performed well; fibronectin activates TGFβ, which inhibits specification; demonstrated with inhibitor and add-back experiments | ✅ |
| The paper states per-condition data is available on request from the authors | ✅ *(we are not requesting it — Phase 2 uses digitized figures only)* |
| VEGF improves differentiation; TGFβ inhibits specification | ✅ |
| Statistical software: **JMP** | ✅ |
| Figure heatmaps report **coded** concentrations, 0 = lowest per protein, 1 = highest | ✅ figure captions |
| Table 2's run pattern is **coded** (minus, zero, plus), not absolute | ✅ table caption |
| Stage 1 lists **23 formulations** and stage 2 lists **25 formulations** | ✅ Tables 1 and 2; describe this as a 23+25 two-stage study, not a published 20+27+1 pipeline |

**Internal inconsistency in the source, unresolved:** the Results section lists the stage-1 Collagen IV high as **28 µg/mL**; the Methods section lists **56 µg/mL**. Every other value in both lists matches. See Doc 2 §B.4.1.

**One nuance to state correctly:** the comparison against Matrigel is **transitive, not direct.** The paper shows EO > LN411+FN and cites the authors' earlier work for LN411+FN > Matrigel. No numeric EO-versus-Matrigel comparison appears in the 2025 paper.

## 1.2 BoTorch API — verified from source and documentation

| Claim | Status |
|---|---|
| `get_covar_module_with_dim_scaled_prior(ard_num_dims, batch_shape=None, use_rbf_kernel=True, active_dims=None)` | ✅ exact signature |
| `use_rbf_kernel` defaults to `True` → **the Matérn override is required** | ✅ |
| Returns `MaternKernel \| RBFKernel` — a bare kernel, **no `ScaleKernel` wrapper** | ✅ return type annotation |
| Lengthscale constrained above **0.025** for numerical stability | ✅ docstring |
| Lengthscale prior `LogNormalPrior(loc=SQRT2 + log(ard_num_dims)*0.5, scale=SQRT3)` | ✅ source |
| `loo_cv` does **not** refit hyperparameters per fold; documentation recommends `batch_cross_validation` where hyperparameter changes matter | ✅ exact |
| `batch_cross_validation` fits separate models with **separate hyperparameters** per fold | ✅ |
| `batch_cross_validation(..., observation_noise=False)` is the default → gives **latent** coverage | ✅ |
| `gen_loo_cv_folds(train_X, train_Y, train_Yvar)` | ✅ |
| Legacy prior configuration available via `get_matern_kernel_with_gamma_prior` | ✅ |
| Default kernel changed to RBF in 0.12, per Discussion #2451 and Hvarfner et al. ICML 2024 | ✅ |
| `FixedNoiseGP` merged into `SingleTaskGP`; `HeteroskedasticSingleTaskGP` removed (PR #2616) | ✅ |
| Hvarfner, in Discussion #2451, states he agrees the RBF-versus-Matérn motivation is not well justified | ✅ |

### 1.2b Verified on the *installed* version — PF3, this project

Botorch 0.18.1 · gpytorch 1.15.2 · torch 2.13.0 · Python 3.11.15, macOS/arm64. Reproduce with `scripts/preflight_pf3.py`. Full write-up in `archive/build-phase/preflight-findings.md`.

| Claim | Status |
|---|---|
| `Normalize` without `bounds=` learns bounds from training-data min/max | ✅ **verified — promoted from Part 3.** On a `[0, 0.32]⁶` sub-box, a query at 0.85 mapped to 2.72–3.01 |
| `optimize_acqf_discrete(acq_function, q, choices, max_batch_size, unique, return_acq_values, X_avoid, inequality_constraints)` exists | ✅ **verified — promoted from Part 3.** `optimize_acqf_discrete_local_search` also present |
| `use_rbf_kernel` defaults `True`; the override returns a bare `MaternKernel(nu=2.5)` | ✅ verified on installed version |
| Lengthscale constraint is `GreaterThan(0.025)`; prior `LogNormalPrior(loc=2.3101, scale=1.7321)` | ✅ read off the constraint object |
| `get_matern_kernel_with_gamma_prior` returns a **`ScaleKernel`**, unlike `get_covar_module_with_dim_scaled_prior` which returns a bare kernel | ✅ **new — not in the original spec.** The asymmetry is why the traversal helper is mandatory |
| **`observation_noise=True` under a fixed-noise likelihood at an unevaluated input silently substitutes `mean(train_Yvar)`** | ✅ **verified.** `botorch/models/gpytorch.py:532`, comment `# Use the mean of the previous noise values (TODO: be smarter here)`. Confirmed mean, not median, by planting an outlier. No warning |
| **A tensor passed to `observation_noise` must be in standardized units, while `train_Yvar` is in raw units** | ✅ **new — not anticipated by the spec.** Passing raw was wrong by 161× in the test case; the factor is `outcome_transform.stdvs**2` |

### 1.2c Measured, not estimated — PF4, this project

| Claim | Status |
|---|---|
| One 48-evaluation run takes 4.8–9.2 s, not ~60 s | ✅ measured on a stand-in objective — see Part 4.1 |
| Full grid is ~0.4 h single-threaded, not 3–5 h | ✅ measured |
| 92–96% of run time is `optimize_acqf`; GP fitting is 4–8% | ✅ measured |

## 1.3 Published precedent — rechecked against original full texts

| Source | Confirmed use and required wording |
|---|---|
| Hall, Lin & Ogle (2025) | Six extracellular-matrix factors were reduced to four for an on-face response-surface stage. The source tables list 23 stage-1 and 25 stage-2 formulations. The project's 20+27+1 implementation is therefore an in-house matched-budget design choice, not Hall et al.'s published pipeline. |
| Rummukainen et al. (2024) | The study used a 15-run Box--Behnken design and a BO sequence that reused five of those experiments before ten new BO experiments. No common post-campaign best-measured terminal score was reported: noisy EI selected the first nine new BO experiments, and posterior mean selected the tenth experiment. |
| Lapierre et al. (2025) | The source supports a shared-screen, multicycle batch-BO versus two-step DoE workflow and reports 28% higher maximum backscatter in microbioreactors and 19% higher maximum OD600 in the 2-L test. It does not support calling the optimization design a CCD or asserting an exactly 48-condition shared screen. |
| Ndahiro et al. (2025) | The equal-count experimental comparator was a 12-formulation JMP space-filling design, not classical RSM/DoE; both groups were run in biological duplicate. |
| Narayanan et al. (2025) | The reported approximately 2.5--3-fold and 10--30-fold efficiencies are comparisons with predicted/traditional DoE requirements, not an executed equal-budget DoE arm. |
| Gisperg et al. (2025) | This is a mini-review suitable for broad field context, not primary evidence for a particular budget, comparator, or terminal rule. |
| Jones, Schonlau & Welch (1998) | Expected improvement is the expected gain above the current best under the GP model; it grows with both posterior mean relative to the incumbent and posterior uncertainty. This source does not establish noisy EI. |
| Frazier (2018) | In noisy BO, final selection by posterior mean is a standard decision rule; a raw noisy argmax is an operational comparator, not a generally preferred terminal rule. |

Other project precedents retained for contextual use include Kanda et al. *eLife* 2022, Bader et al. 2023, Cosenza et al. 2022, Romero, Krause & Arnold *PNAS* 2013, and the documented BoTorch, Ax, BoFire, BayBE, Olympus and Atlas software sources. Their individual quantitative claims must still be tied to the cited primary source in the manuscript.

## 1.4 Standard results, no citation risk

The OLS prediction-variance formula `σ̂²x₀ᵀ(XᵀX)⁻¹x₀` and the response-surface variance-dispersion literature are textbook regression. Canonical analysis classifies a stationary point as a maximum, minimum, or saddle; ridge analysis is a separate constrained procedure and must not be listed as a fourth canonical class. If the implementation only maximizes over the explored box, call it a **constrained in-region model recommendation**, not ridge analysis. Box & Wilson (1951) supports sequential local response-surface work and steepest ascent; Box & Draper and Myers et al. remain the fuller references for canonical, constrained/ridge, and relocated analyses. Gneiting & Raftery 2007 (proper scoring rules) and Demšar 2006 (critical-difference diagrams) are well-established.

The closed-form results derived for this project are verified algebraically: the biphasic peak at `x* = √(EC50·IC50)`, the peak height `(s/(1+s))²`, the normalized response `f̃(v) = v^n(1+s)²/((1+s·v^n)(s+v^n))`, and the depth-inversion quadratic `V(1−c)s² + [2V − c(1+V²)]s + V(1−c) = 0` with reciprocal roots. The inversion is checked numerically: `(x* = 0.4, n = 2, δ = 0.414) → s = 3.9917 → r = 4`.

---

# PART 2 — CORRECTLY FLAGGED AS UNRESOLVED

| Item | Status |
|---|---|
| **Whether TheO's Collagen IV exceeded the tested range** | Depends on the Results-versus-Methods contradiction. **Permanently unresolved — we are not contacting the authors.** Blocks one sentence; blocks nothing in the build. Do not assert it either way. |
| ~~**The 23-run / 25-run split**~~ | ✅ **RESOLVED — moved to Part 1.1.** Confirmed from Hall et al.'s Tables 1 and 2. Any 47-condition digitization remains a separate in-house data-extraction count and must not be described as the number of published formulations. |
| **The Ax `AxClient` removal version** | A deprecation warning exists; the specific removal version is unconfirmed. Do not cite a version number. |
| **Summit's license** | Not confirmed from its LICENSE file. Verify before any redistribution. |

---

# PART 3 — NOT INDEPENDENTLY VERIFIED

Not necessarily wrong. Confirm before relying on them.

| Claim | Assessment |
|---|---|
| ~~`Normalize` without `bounds=` learns bounds from training-data min/max~~ | ✅ **RESOLVED — moved to Part 1.2b.** Verified on the installed version by PF3. |
| ~~`optimize_acqf_discrete` or equivalent exists for fixed candidate sets~~ | ✅ **RESOLVED — moved to Part 1.2b.** Exact signature confirmed by PF3. |
| Design-Expert plots standard error across the design space | Plausible, unchecked. Not load-bearing. |
| BoTorch ships a robust-GP path (Relevance Pursuit) | Unchecked. Only relevant to deferred Phase 3 work. |
| BoTorch 0.18 ships a feasibility-driven trust-region tutorial | Unchecked. Not used. |
| scikit-optimize / GPyOpt / Spearmint kernel defaults | Believed to be Matérn; unverified. **Do not cite as evidence for a field-wide standard.** |
| The continuous kernel used by Narayanan et al. or Bader et al. | **Not established.** Narayanan is documented as GP + UCB with a custom categorical kernel; the continuous kernel is not specified in what was retrieved. **Do not cite either paper as support for a particular kernel choice.** |

---

# PART 4 — OUR OWN ESTIMATES AND DESIGN CHOICES

Not claims about the world. Present them as choices, with reasoning.

## 4.1 Engineering estimates — not measured

| Claim | Where | Status |
|---|---|---|
| ~~One BO iteration 3–5 s; one 48-evaluation run ~60 s; full grid 3–5 h~~ | Doc 1 §3 | ✅ **SUPERSEDED by PF4 measurement** — 0.5–1.0 s / 4.8–9.2 s / ~0.4 h. See Part 1.2c. |
| ~~Parallelized grid under 1 hour~~ | Doc 1 §3 | ✅ **SUPERSEDED** — ~0.05–0.1 h at 4–8 workers |
| Memory use 1–2 GB | Doc 1 §3 | Still unmeasured. Not load-bearing. |
| A GPU would likely be slower at this scale | Doc 1 §3 | Still untested. Moot — CPU is fast enough. |
| Effort estimates ("~20 lines", "~30 lines", "~40 lines") | Doc 1 §2, Doc 2 §C.1 | Still estimates. |

The superseded figures were reasoned from Cholesky complexity at n<100 and GPU kernel-launch overhead, and were **~10× pessimistic**. PF4's measurement used a stand-in objective (Hartmann6 at d=6, a synthetic bump at d=8) because the biphasic oracle did not yet exist; since 92–96% of the cost is acquisition optimization rather than objective evaluation, the figures should hold. **Re-run PF4 against the real oracle to confirm.**

## 4.1b Pre-registered choices — E4

Recorded in `configs/experiment/e4.yaml` with `preregistration_version: 1`, committed before any E4 result existed. **These are choices, not findings**, and the spec left both blank:

| Choice | Value | Reasoning |
|---|---|---|
| Discrimination-test candidate-set size | **512** Sobol points per instance | Spec rules out a handful ("with 10 points the AUC has no usable standard error"); a power of two keeps the Sobol sequence balanced; PF4 showed compute is not a constraint |
| AUC threshold τ | **within-instance 0.80 quantile** of \|polynomial error\| | Instances differ in response scale, so any absolute τ means something different on each. A quantile fixes the positive base rate at 0.20 everywhere, which is what makes AUCs comparable across instances and κ |

The **primary** E4 outcome is Spearman ρ, which needs no threshold at all. τ exists only for the secondary AUC.

## 4.2 Oracle design choices — invented for this project

The Hill and four-parameter-logistic functional forms are standard pharmacology and are grounded. **Everything else about the oracle is our design:** `x* ~ U(0.25, 0.55)`, `n ~ U(1,3)`, `δ = u·δ_max` with `u ~ U(0.55, 0.9)`, `r_cap = 8`, `w ~ U(0.75, 1.25)`, `k = ⌈d/2⌉` interaction pairs, `β ~ U(−0.4, 0.6)` scaled by `1/k`, `σ_rel ∈ {0.10, 0.25}`, `σ_add = 0.01`, and the acceptance floor `minᵢ wᵢδᵢ ≥ 0.045`.

These are starting points, chosen so the experiments can measure what they claim to. Doc 1 §4.4 carries a "justified by" column naming the structural fact each range depends on.

## 4.3 Ranked judgements, not sourced findings

| Claim | What it is |
|---|---|
| "Tuning your own method while leaving baselines at defaults is among the most frequently cited objections" | It appears in the pitfalls literature; the ranking is ours |
| "Most first-time failures are normalization and seed data" | Experience-based ordering, not a measured statistic |
| The knob-importance ranking in Doc 1 §11 | Our judgement |

---

# PART 5 — HOW TO USE THIS DOCUMENT

## Publication update checked 2026-09-07

### Additional reconciliation, 2026-09-09

Further source tracing corrected the Figure 2 recommender description: `scripts/run_fix1_terminal_rule.py::one` fits the same GP for every arm and calls the same locator with twenty restarts and 4,096 raw starts. It does not use the earlier arm-specific quadratic RSM recommender. This source matches retained commit `1bf51f11695ae348ffa8993ad42992141558fb80`. The manuscript now separates those diagnostics. A fresh `test_full_space_rule_p_reproduces_fix1` run returned 0.25251124591423746 against 0.2525116337195932 stored for classical campaign `033466197eba3ddb`, seed 0. This is a Figure 2 source dependency, not an unrelated failure. The aggregate remains the archived result and exact replay remains unestablished.

The fresh calibration checkpoint test completed its write path and then exited intentionally after its exact map-fidelity gate failed: worst delta 9.082e-13, 48 differing fields, no regret-gate failures, no changed latent-map cells. It is not a checkpoint-write crash. Matching package versions would not by itself establish a code-change cause; platform, numerical libraries, threads, random-state handling and stored provenance also matter. Neither equality gate was relaxed.

The retained prospective scorer and analyzer match commit `1bf51f11695ae348ffa8993ad42992141558fb80` without changes. In `scripts/run_final_spade_benchmark.py`, the map mask is fixed at probability 0.50 outside the gamma/alpha loops; the threshold is loaded per condition, not recalculated for every Hill instance. `conservative_columns` constructs latent-response certificates and stores both oracle containment and held-out posterior probabilities. In `scripts/analyse_final_spade_benchmark.py`, `containment_cell` counts posterior probabilities meeting alpha, not oracle-containment indicators. Consequently, the original prospective Hill certificate report and Figure 4B are posterior self-consistency checks, not empirical certificate validation. Figure 4D uses separate retrospective oracle counts. The paper now states these differences explicitly, along with the unadjusted repeated-instance structure of the original binomial intervals. No retained scientific result was changed.

The official [PLOS submission guidelines](https://journals.plos.org/plosone/s/submission-guidelines) were checked: abstract at most 300 words, figure files uploaded separately, captions retained in the manuscript, and funding/conflict declarations supplied through the submission system. The [ethical publishing policy](https://journals.plos.org/plosone/s/ethical-publishing-practice) requires disclosure of AI-assisted work; the paper adds a Methods section and leaves author review unconfirmed.

Ament et al., *Unexpected Improvements to Expected Improvement for Bayesian Optimization* (NeurIPS 2023), and Balandat et al., *BoTorch: A Framework for Efficient Monte-Carlo Bayesian Optimization* (NeurIPS 2020), were checked against their primary conference abstract pages, linked in the manuscript references. These support the logarithmic acquisition and software descriptions, respectively.

Gotovos, Casati, Hitz and Krause (2013), *Active Learning for Level Set Estimation*, was checked against the [author-hosted primary paper](https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf). Its abstract and method describe GP confidence-bound level-set sampling/classification, batch extensions and a threshold relative to an unknown maximum. The manuscript now acknowledges this prior work and does not claim SPADE invented level-set estimation.

Azzimonti, Ginsbourger, Chevalier, Bect and Richet, *Adaptive Design of Experiments for Conservative Estimation of Excursion Sets*, was checked against the [institution-hosted accepted manuscript](https://ipg.idsia.ch/preprints/azzimontid2019c.pdf), especially the abstract and introduction. It develops adaptive conservative excursion sets with false-inclusion control. DOI 10.1080/00401706.2019.1693427 identifies the Technometrics article, volume 63, pages 13–26 (2021 issue; online publication in 2019). These methods were not implemented as direct benchmark comparators; that gap is now explicit in the paper.

The Figure 4A Murphy evidence is **retrospective Hill**, not five-family data. Figure 4C uses retrospective campaign answer rates at alpha 0.95, whereas Figure 4D summarizes dependent threshold cells at alpha 0.80. The updated plot removes binomial intervals from the latter pooled counts. Neither panel is evidence from the separate joint-protocol development study.

### Targeted literature and comparator review, 2026-09-10

This was a targeted primary-source comparison, not a systematic review. Manuscript Table 5 now separates physical validation, theoretical precedents, and synthetic benchmarks; cross-paper effect sizes are not ranked.

- **Verified methodological precedent:** [Bogunovic et al., TruVaR (NeurIPS 2016)](https://papers.neurips.cc/paper_files/paper/2016/hash/ce78d1da254c0843eb23951ae077ff5f-Abstract.html) already unifies Bayesian optimization and level-set estimation. The [Gotovos et al. primary paper](https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf) explicitly presents the straddle score used here and covariance-aware batch extensions. SPADE's geometric exclusion is not that batch update and carries no inherited theoretical guarantee. Neither specialized method was directly benchmarked; algorithmic novelty or superiority over them is not established.
- **Verified recent computational context:** [Mia et al., Journal of Materials Research 41:927–948 (2026)](https://doi.org/10.1557/s43578-026-01803-y) studies six-variable Ackley and Hartmann batch BO under noise and acquisition variations. Its noise normalization and settings differ from ours. The manuscript cites it as related evidence of setting dependence, not a replication or a head-to-head comparison.
- **Verified reporting framework:** [Morris, White and Crowther, Statistics in Medicine (2019)](https://doi.org/10.1002/sim.8086) separates simulation aims, data-generating mechanisms, estimands, methods, and performance measures and discusses Monte Carlo uncertainty. Table 3 and inference text now make the 25 landscape instances, with four campaign seeds per instance, explicit. Scoring rows and seeds are not independent landscape replications.
- **Verified terminal-decision precedent:** [Frazier's tutorial](https://arxiv.org/html/1807.02811v1) describes posterior-mean maximization as a risk-neutral terminal recommendation when unobserved points may be returned. Rule P is not a new decision principle; the manuscript's contribution is the controlled rescoring contrast.
- **Internal evidence, not a new analysis:** The retained comparison table reports LHS map error 0.186703 versus primary SPADE 0.180414, a difference of 0.006289, and lower LHS point regret in one rather than two rounds. There is no retained paired claim-ledger decision for this contrast. The SPADE-minus-Sobol map interval is entirely smaller in magnitude than the registered 0.02 practical margin. The text now distinguishes these findings from the 15.3% qLogNEI comparison and does not assert LHS equivalence.
- **Submission assessment:** [PLOS ONE publication criteria](https://journals.plos.org/plosone/s/criteria-for-publication) emphasize originality, technical soundness, reproducibility, and supported conclusions rather than positive results alone. A bounded evaluation contribution is the defensible framing here. Missing specialized comparators, lack of biological validation, and unresolved historical replay prevent stronger claims; editorial acceptance is not guaranteed by this revision.

No frozen results, historical equality gates, development decisions, or lockbox state were changed during this review.

**Writing the methods section?** Everything in Part 1 can be cited directly. Part 4.2 must be described as a design choice with stated ranges.

**Someone questions a claim?** Check which part it falls in. If Part 3, say so and verify rather than defending it.

**Adding a new factual claim to any document?** Add it here with its status at the same time. A claim without a status line in this document has not been checked.
