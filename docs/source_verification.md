# SOURCE VERIFICATION
## Which factual claims are confirmed, and which still need checking

**Document 3 of 3.** Reference for anyone writing the paper or defending a claim.
**Document 1** (`phase1_build.md`) — the buildable specification.
**Document 2** (`project_plan.md`) — project context, scientific argument, phase plans.

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

Botorch 0.18.1 · gpytorch 1.15.2 · torch 2.13.0 · Python 3.11.15, macOS/arm64. Reproduce with `scripts/preflight_pf3.py`. Full write-up in `preflight-findings.md`.

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

## 1.3 Published precedent — verified in project research

Narayanan et al. 2025 (*Nat Commun* 16:6055, DOI, CC-BY, the three optimization cases, the 33–50% categorical-kernel figure, the 3× and 10–30× efficiency figures, the GitHub repo and Zenodo DOI) · Kanda et al. *eLife* 2022 (LabDroid, 7 parameters, ~200 million combinations, 143 conditions, 111 days, 88% improvement) · Bader et al. 2023 · Gisperg et al. 2025 review · Cosenza et al. 2022 · Romero, Krause & Arnold *PNAS* 2013 · Honegumi, BoFire, BayBE, Olympus/Atlas repositories and licenses · botorch 0.18.1 and ax-platform 1.3.1 versions · Ax 1.0.0 `Client` API · one-hot categorical default (Discussion #3063) · equality-constraint issue #1227 · Matérn 5/2 kernel formula · Expected Improvement formula · LogEI / Ament et al. 2023 · EHVI/NEHVI/qLogNEHVI and Daulton et al. · Turner et al. 2021 PMLR v133 · *npj Comput. Mater.* 2021 50-seed benchmark · arXiv 2504.03943, 2505.07750, 2511.16230 · Acharki et al. arXiv 2106.05396 · Hill / four-parameter-logistic formulation · SAASBO, TuRBO.

## 1.4 Standard results, no citation risk

The OLS prediction-variance formula `σ̂²x₀ᵀ(XᵀX)⁻¹x₀` and the response-surface variance-dispersion literature are textbook regression. Ridge analysis (Hoerl 1959; Draper 1963), canonical analysis, Box & Draper, and Myers & Montgomery are the standard references for extrapolated stationary points. Gneiting & Raftery 2007 (proper scoring rules) and Demšar 2006 (critical-difference diagrams) are well-established.

The closed-form results derived for this project are verified algebraically: the biphasic peak at `x* = √(EC50·IC50)`, the peak height `(s/(1+s))²`, the normalized response `f̃(v) = v^n(1+s)²/((1+s·v^n)(s+v^n))`, and the depth-inversion quadratic `V(1−c)s² + [2V − c(1+V²)]s + V(1−c) = 0` with reciprocal roots. The inversion is checked numerically: `(x* = 0.4, n = 2, δ = 0.414) → s = 3.9917 → r = 4`.

---

# PART 2 — CORRECTLY FLAGGED AS UNRESOLVED

| Item | Status |
|---|---|
| **Whether TheO's Collagen IV exceeded the tested range** | Depends on the Results-versus-Methods contradiction. **Permanently unresolved — we are not contacting the authors.** Blocks one sentence; blocks nothing in the build. Do not assert it either way. |
| **The 23-run / 25-run / ~48-condition split** | From earlier project notes, not confirmed against the paper's tables. Affects only the E2 budget rationale. |
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

**Writing the methods section?** Everything in Part 1 can be cited directly. Part 4.2 must be described as a design choice with stated ranges.

**Someone questions a claim?** Check which part it falls in. If Part 3, say so and verify rather than defending it.

**Adding a new factual claim to any document?** Add it here with its status at the same time. A claim without a status line in this document has not been checked.
