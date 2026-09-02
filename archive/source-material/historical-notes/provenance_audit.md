# PROVENANCE AUDIT
## Every substantive claim in `phase1_bo_build.md` and `project_record.md`, classified by evidence

**Verification date:** 6 August 2026
**Method:** direct fetch of Hall/Lin/Ogle 2025 full text; BoTorch source and documentation searches; cross-check against the research report generated earlier in this project.

---

# PART 1 — CLAIMS THAT ARE WRONG

## 1.1 ❌ The paper did not fit a quadratic. It fitted a third-order model.

**What our documents say:** the mechanism is that *"a quadratic fitted to a monotone-saturating truth must turn over, because a downward parabola is the only way a quadratic can have an interior maximum."*

**What Hall/Ogle actually did**, from the Results section:

> a regression analysis was performed to determine the coefficients of the response surface relating ECM exposure to CD31 expression **based only on significant terms up to the 3rd order**

And the Figure 2 caption:

> **Terms up to the third order were included.**

**Why this matters.** The "must turn over" argument is specific to quadratics. A cubic can be monotone, can have two stationary points, and does not carry the same forced-concavity property. **The mechanism as written does not describe what they did.**

**What survives.** The general misspecification argument still holds — a low-order polynomial basis is a poor fit for saturating dose-response, and its fitted stationary point can land outside the design region. But it becomes an empirical claim, not a mathematical necessity, and Experiment 4 must fit a **third-order model** to match, not a quadratic.

**Required edits:** Doc 1 §6 (E4), Doc 1 §4.5, Doc 1 §7 check 1, Doc 2 §B.1.

---

## 1.2 ❌ The "67.2 > 56" claim is not confirmed. The paper contradicts itself.

This is the headline detail of the whole project, and it rests on an unresolved internal inconsistency in the published paper.

**Results section** — stage-1 high concentrations:

> The high concentrations were set based on literature values for ECM coating for cell culture applications to 35.5 µg/mL, **28 µg/mL**, 15.8 µg/mL, 0.8 µg/mL, 0.8 µg/mL, and 75 µg/mL for C, CIV, LN111, LN411, LN511, and FN respectively.

**Methods section** — stage-1 high concentrations:

> the concentration of each ECM protein (C, CIV, LN111, LN411, LN511, FN) was set to either a low (0,0,0,0,0,22 µg/mL) or high (35.5, **56**, 15.8, 0.8, 0.8, 75 µg/mL) level respectively.

Every value matches except Collagen IV: **28 in Results, 56 in Methods.** And 56 = 2 × 28.

**The scaling step**, from Results:

> Thus, the high concentration of these proteins was increased **by a factor of 2** for the subsequent response surface regression.

(applied to C, CIV, and LN411, which showed positive significant associations)

**So the fork is:**

| If stage-1 CIV high is… | Then stage-2 CIV high is… | And TheO's 67.2 µg/mL is… |
|---|---|---|
| 28 (Results) | 56 | **outside** the tested range ✓ claim holds |
| 56 (Methods) | 112 | **inside** the tested range ✗ claim fails |

The most likely reading is that the Methods section mistakenly reports the *doubled* stage-2 value in the stage-1 list — which would make the claim correct. But that is inference, not evidence.

**Resolving it requires Table 2**, which gives the actual stage-2 run-pattern concentrations and which I could not retrieve (it renders as a separate linked object). Alternatively, email Ogle.

**Do not build the argument on this until it is resolved.** This is now the single highest-priority verification task.

---

## 1.3 ⚠️ The paper gives a *biological* explanation for TheO's failure, and our documents omit it

This is not an error, but it is a serious omission that a reviewer would catch immediately.

The paper reports that **TheO without fibronectin — which they rename EO — worked very well.** Their explanation is mechanistic and supported by intervention experiments: fibronectin activates TGFβ signalling, which inhibits endothelial specification. Adding a TGFβ inhibitor rescued differentiation on TheO; adding TGFβ suppressed it on EO.

And critically:

> the model used did not allow for concentrations of FN below 22 µg/mL to be evaluated

> Since the TheO formulation indicated the lowest FN concentration would lead to the highest CD31 expression…

**So the DoE model correctly wanted less fibronectin and was structurally unable to ask for it.** TheO sits at the FN *lower bound* of the design.

**Why this matters for the paper.** A reviewer will say: *the authors explained this failure biologically. Why are you attributing it to extrapolation?* You need an answer, and the honest one may be stronger than the current story:

The failure was a **design-boundary** problem as much as an extrapolation problem. The optimum lay outside the design region in the FN direction (below 22), and the response surface could neither reach it nor express that it wanted to. A GP with the same constraint would face the same box — but its uncertainty at the constraint boundary would say something the response surface's cannot.

That is a different and more defensible claim than the current one. It needs deciding before the argument is rebuilt.

---

## 1.4 ❌ "Matérn 5/2 is what the published cell-culture BO work uses" — unsupported

This is **argument #1** for the locked kernel choice in Doc 2 §G, and nothing we retrieved supports it.

Our research established that Narayanan et al. used a GP with a UCB acquisition function and a custom categorical kernel. **It never established their continuous kernel.** Bader et al.'s kernel is likewise unestablished. I asserted the field-wide pattern and should not have.

**What is supported:** Matérn 5/2 was BoTorch's default before 0.12. That is documented. The claim about scikit-optimize, GPyOpt, and Spearmint defaults is also mine and unverified.

**What the evidence actually says about the kernel question**, from BoTorch Discussion #2451 — a user asks why the default changed from Matérn to RBF, noting the common belief that Matérn's roughness suits real-world problems. Hvarfner, the author of the paper the change is based on, replies that he agrees the RBF-versus-Matérn motivation is not well justified. Another participant reports better performance with `use_rbf_kernel=False` in some cases.

**So the kernel choice is genuinely unsettled**, by the admission of the person whose work prompted the change. That is a weaker foundation than Doc 2 currently claims — but it also means running the comparison and reporting it is the defensible move, rather than asserting a field standard.

**Required edit:** Doc 2 §G, kernel row. Rewrite argument #1 as "Matérn 5/2 was BoTorch's default prior to 0.12 and remains a common choice; the RBF-versus-Matérn question is explicitly unsettled per the author of the work that motivated the change."

---

# PART 2 — CLAIMS CONFIRMED

## 2.1 Hall/Ogle — verified from full text

| Claim | Status |
|---|---|
| TheO = 35.6 µg/mL C, 67.2 µg/mL CIV, 0.9 µg/mL LN411, 22 µg/mL FN | ✅ exact |
| TheO produced very little differentiation, around the level of FN alone | ✅ exact |
| Authors attribute the discrepancy to an on-face central composite design not allowing accurate modelling outside the original parameter space | ✅ exact, direct quote |
| Readout: CD31 area per DAPI area, normalized to the FN control | ✅ |
| Analysed at day 10 of differentiation | ✅ |
| At least 4 wells from at least 3 experimental replicates | ✅ |
| Six proteins; low = 0 for all except FN at 22 µg/mL (lowest concentration with good attachment) | ✅ |
| Stage 2 = on-face central composite design on C, CIV, LN411, FN | ✅ |
| Data available on request from the corresponding author (ogle@umn.edu) | ✅ |
| VEGF improves differentiation; TGFβ inhibits specification | ✅ |
| Collagen I + Collagen IV + Laminin 411 formulation beats Matrigel | ⚠️ **transitive, not directly tested here.** The paper shows EO > LN411+FN, and cites their own earlier work for LN411+FN > Matrigel. State it that way. |
| Statistical software | ⚠️ **JMP**, not Design-Expert. Correct any reference. |
| 23-run stage 1 / 25-run stage 2 / ~48 total | ⚠️ **not confirmed** — from your proposal; Tables 1 and 2 were not retrievable. Verify before using 48 as the E2 budget. |

## 2.2 BoTorch API — verified from source and docs

| Claim | Status |
|---|---|
| `get_covar_module_with_dim_scaled_prior(ard_num_dims, batch_shape=None, use_rbf_kernel=True, active_dims=None)` | ✅ exact signature |
| `use_rbf_kernel` defaults to `True` → **the override is required** | ✅ |
| Returns `MaternKernel \| RBFKernel` — a bare kernel, **no `ScaleKernel` wrapper** | ✅ confirmed by return type annotation |
| Lengthscale constrained above **0.025** for numerical stability | ✅ exact, from the docstring |
| Lengthscale prior `LogNormalPrior(loc=SQRT2 + log(ard_num_dims)*0.5, scale=SQRT3)` | ✅ exact, from source |
| `loo_cv` does **not** refit hyperparameters | ✅ **exact.** The docs state it keeps hyperparameters fixed as a fast approximation and recommend `batch_cross_validation` where hyperparameter changes matter. |
| `batch_cross_validation` fits separate models with **separate hyperparameters** per fold | ✅ |
| `gen_loo_cv_folds(train_X, train_Y, train_Yvar)` | ✅ |
| Legacy config available via `get_matern_kernel_with_gamma_prior` | ✅ **new** — simpler than hand-rolling the old priors |
| Kernel default changed to RBF in 0.12, per Discussion #2451 and Hvarfner et al. ICML 2024 | ✅ |

**One signature detail to note:** `batch_cross_validation(model_cls, mll_cls, cv_folds, fit_args=None, observation_noise=False)`. The default is `observation_noise=False`, which gives **latent** coverage. For coverage of what the lab measures, pass `observation_noise=True`. This is exactly the ambiguity Doc 1 §6 flags — the default is the opposite of the primary metric.

## 2.3 Verified earlier in this project's research

Narayanan et al. 2025 (Nat Commun 16:6055, DOI, CC-BY, the three optimization cases, the 33–50% categorical-kernel figure, the 3× / 10–30× efficiency figures, the repo and Zenodo DOI) · Kanda et al. eLife 2022 (LabDroid, 7 parameters, 200 million combinations, 143 conditions, 111 days, 88% improvement) · Bader et al. 2023 · Gisperg et al. 2025 review · Cosenza et al. 2022 · Romero, Krause & Arnold PNAS 2013 · Honegumi, BoFire, BayBE, Olympus/Atlas repositories and licenses · botorch 0.18.1 and ax-platform 1.3.1 versions · Ax 1.0.0 `Client` API · `FixedNoiseGP` merged into `SingleTaskGP` · `HeteroskedasticSingleTaskGP` removed (PR #2616) · one-hot categorical default (Discussion #3063) · equality-constraint issue #1227 · Matérn 5/2 kernel formula · EI formula · LogEI / Ament et al. 2023 · EHVI/NEHVI/qLogNEHVI and Daulton et al. · Turner et al. 2021 PMLR v133 · npj Comput. Mater. 2021 50-seed benchmark · arXiv 2504.03943, 2505.07750, 2511.16230 · Acharki et al. arXiv 2106.05396 · Hill/4PL formulation · SAASBO, TuRBO.

---

# PART 3 — NOT VERIFIED

These are not necessarily wrong. They are unsupported by anything we retrieved, and the documents present some of them more confidently than that warrants.

## 3.1 From the third-party critique, claimed-verified but not independently checked by me

| Claim | My assessment |
|---|---|
| `Normalize` without `bounds=` learns bounds from training-data min/max | **High confidence, not directly confirmed this session.** Documented BoTorch behaviour and consistent with the tutorials, which call `Normalize(d=...)` with no bounds. Verify in Build Step 1. |
| Design-Expert plots standard error across the design space | Plausible, unchecked. Not load-bearing. |
| BoTorch ships a Relevance Pursuit robust-GP path | Unchecked. Tier 3 anyway. |
| BoTorch 0.18 shipped a feasibility-driven trust-region tutorial | Unchecked. Tier 3. |
| Ax `AxClient` removal in 1.4.0 | **The critique itself flagged this as unconfirmed, and so do our documents.** Correct as handled. |

The OLS prediction-variance formula `σ̂²x₀ᵀ(XᵀX)⁻¹x₀` and the RSM variance-dispersion literature are standard textbook regression and I am confident in them. Gneiting & Raftery 2007 and Demšar 2006 are real, well-known papers.

## 3.2 My own assertions, not from any source

| Claim | Where | What it actually is |
|---|---|---|
| "Matérn is the field standard in published cell-culture BO" | Doc 2 §G | **Unsupported — see 1.4.** Fix required. |
| scikit-optimize / GPyOpt / Spearmint kernel defaults | Doc 2 §G | Believed true, unverified |
| "Published evidence attributes most of the gain to the priors, not the kernel" | Doc 2 §F.3 | Directionally supported by Hvarfner's own comment that the kernel motivation is weak — but "most of the gain" is my quantification, not anyone's finding. Soften. |
| "The most common reviewer objection in this literature" | Doc 1 §6 | It appears in the pitfalls lists. The ranking is mine. |

## 3.3 Engineering estimates — not measured

| Claim | Where |
|---|---|
| One BO iteration 3–5 s; 48-evaluation run ~60 s; full grid 3–5 h | Doc 1 §3 |
| Parallelized grid under 1 h | Doc 1 §3 |
| Memory 1–2 GB | Doc 1 §3 |
| "A GPU would make this slower" | Doc 1 §3 |
| "~20 lines", "~30 lines", "~40 lines" | Doc 1 §2, Doc 2 §C.1 |

All reasoned from Cholesky complexity at n<100 and GPU kernel-launch overhead. **None measured.** Pre-flight check 4 exists to replace the timing numbers with real ones; the table should be labelled as estimates until then.

## 3.4 Design choices, not claims about the world

The Hill oracle parameter distributions in Doc 1 §4.3 — `EC50 ~ U(0.2,0.7)`, `n_i ~ U(1,3)`, `w_i ~ U(0.5,1.5)`, `IC50 ~ U(0.4,0.9)`, `β ~ U(0.2,0.8)`, `k = d//3` interaction pairs, `σ_rel = 0.10`, `σ_add = 0.01` — are **mine, invented for this project.** They are not literature values and the table should say so. The sanity checks in §4.5 exist precisely to tune them.

The Hill and four-parameter-logistic functional forms themselves are standard pharmacology and are grounded.

## 3.5 Also unverified

`optimize_acqf_discrete` — I believe it exists in `botorch.optim` and that the discrete-candidate approach is sound, but I did not confirm the function name or signature this session. Verify in Build Step 1 alongside the other API checks.

---

# PART 4 — WHAT TO DO

## Immediate, before any code

1. **Resolve the Collagen IV inconsistency.** Retrieve Table 2 from the paper, or email Ogle. The headline claim is unresolved until this is settled, and everything downstream depends on it.
2. **Decide the mechanism story** in light of §1.3. Extrapolation, design-boundary constraint, or both. This determines what Experiment 4 actually tests.
3. **Change Experiment 4 to fit a third-order model**, not a quadratic, to match what was actually done.

## Document edits required

| Doc | Section | Change |
|---|---|---|
| 1 | §4.3 | Label the oracle parameters as design choices, not literature values |
| 1 | §4.5, §6 E4, §7 check 1 | Quadratic → third-order polynomial |
| 1 | §3 | Label the timing table as unmeasured estimates |
| 1 | §6 E2 | Flag the 48-evaluation budget as depending on an unconfirmed condition count |
| 1 | §6 E3 | Note `batch_cross_validation` defaults to `observation_noise=False`; pass `True` for the primary metric |
| 2 | §B.1 | Rewrite the mechanism per §1.1 and §1.3 |
| 2 | §B.3 | Add the FN/TGFβ biological explanation and the FN lower-bound constraint |
| 2 | §D.1 | Record the Results/Methods inconsistency; mark 23/25/48 as unconfirmed |
| 2 | §F.1 | Correct the Matrigel comparison to transitive |
| 2 | §F.3 | Add `get_matern_kernel_with_gamma_prior`; soften the priors-versus-kernel attribution |
| 2 | §G | Rewrite the kernel rationale per §1.4 |
| 2 | §H | Promote the Collagen IV check to the top and mark it blocking |

## Confirmed as correct — no change needed

The three silent-failure traps in Doc 1 §5 are all verified: the RBF default, the bare kernel with no `ScaleKernel`, and the 0.025 lengthscale bound. The `loo_cv` refitting warning is verified verbatim from the documentation. Those were the highest-risk technical items and they hold.

---

# PART 5 — HOW THIS HAPPENED

Worth recording, because the pattern will recur.

The wrong claims entered the documents in three ways:

**Inherited without challenge.** The original "DoE gives a prediction without an uncertainty" framing came from the project proposal. I built research and specifications on top of it without interrogating the thing it was comparing against. The third-party critique caught it.

**Adopted from a critique without independent verification.** The corrected mechanism — "a quadratic must turn over" — was well-argued and I accepted it. Neither of us checked what order of polynomial the paper actually fitted. It was third-order.

**Asserted from plausibility.** "Matérn is the field standard in published cell-culture BO" felt true and fit the argument. Our research never established it.

The general lesson: reading the primary source directly caught all three, and it should have happened before the first specification was written, not after the third.
