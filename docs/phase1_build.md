# PHASE 1 — FAKE DATA
## Build specification for the Bayesian optimization model

**Document 1 of 3.** Everything needed to build and test the optimizer on synthetic data.
**Document 2** (`project_plan.md`) — project context, the scientific argument, Phase 2 and 3 plans, research grounding.
**Document 3** (`source_verification.md`) — which factual claims are confirmed against primary sources and which still need checking.

---

## Vocabulary

| Term | Meaning |
|---|---|
| **Phase 1 / 2 / 3** | **Phase 1 = fake data (this document). Phase 2 = published data. Phase 3 = in-house lab data.** |
| **Build Step 1–7** | Milestones inside the Phase 1 code. Unrelated to project phases. |
| **Oracle** | The fake-data generator: a mathematical surface with a planted optimum. |
| **Evaluator** | Supplies outcome values. Phase 1 = the oracle. Phase 2 = a lookup table. Phase 3 = a human with a pipette. |
| **Coded space** | Every factor scaled to [0,1], where 0 is its lowest level and 1 its highest. Canonical throughout. |
| **`x*ᵢ`** | Peak location of factor *i*. Sampled directly. |
| **`δᵢ`** | Depth of factor *i*: `1 − f̃ᵢ(1)`, the normalized decline from peak to the upper box edge. Sampled directly. |
| **`rᵢ`** | Window ratio `IC50ᵢ/EC50ᵢ`. Derived from `(x*ᵢ, nᵢ, δᵢ)` by inversion. |
| **Sub-box** | E4's training region, `[0, κ·x*ᵢ]` per dimension. An experiment construct, not a property of the oracle. |
| **Extended box** | The full unit cube. Where all models are optimized in E4. |

---

## 1. What Phase 1 is for

Phase 1 is the control experiment for your own code. You build the optimizer and prove it works on data where you already know the answer, because you planted it.

| # | Claim | Notes |
|---|---|---|
| 1 | Recovers the planted optimum's **value** within tolerance | Tolerance stated as a fraction of instance depth |
| 2 | Beats non-adaptive designs and a sequential DoE pipeline | |
| 3 | Uncertainty estimates are calibrated, with error bars | |
| 4 | Extrapolation-driven over-prediction is detectable *selectively* | |

**Claim 1's tolerance is relative to depth** — e.g. "within 25% of instance depth of the optimum value." If tolerance exceeded depth, a boundary point would satisfy the claim and the claim would be vacuous.

**Claim 1 is about value, not location.** At d=6 with `Σw = 1`, moving a single coordinate from peak to boundary changes the response by roughly `w·δ ≈ 0.05` — about half a single-observation sigma at `σ_rel = 0.10`. Per-coordinate localization from individual observations is not possible at this signal-to-noise. You localize by pooling.

**On E4's framing.** An extrapolated stationary point outside the design region is a textbook response-surface pathology — canonical analysis and ridge analysis (Hoerl 1959; Draper 1963) exist to detect it. The contribution is *automated, calibration-based detection quantified against model-free nulls*, not discovery. See Doc 2 §B.2.

---

## 2. The forward-compatibility contract

Nine requirements. Meet them in Phase 1 and Phases 2 and 3 are drop-in additions rather than rewrites.

| # | Requirement | Why | Cost |
|---|---|---|---|
| 1 | **Ask/tell separation.** The optimizer proposes; a separate `Evaluator` supplies outcomes. The optimizer never calls the oracle. | Phase 2 swaps in a lookup table; Phase 3 swaps in a human. Same loop. | Free |
| 2 | **Discrete candidate mode.** Choose from a fixed candidate set as well as searching continuously. | **Phase 2 replay can only propose conditions that exist in the published data** — those are the only ones with measured outcomes. | ~20 lines |
| 3 | **Search space in config, canonically coded [0,1]**, physical labels optional. | Phase 2 digitizes figures reporting coded levels only. | Free |
| 4 | **Mixed parameter types in the schema** — continuous, integer, categorical. | Phase 3 may have categorical base medium or integer treatment days. | Low |
| 5 | **Always pass `Yvar`**, imputed where unreplicated from a mean–variance relation with a floor. | One `SingleTaskGP` cannot mix likelihoods, and Phase 3 will have replicated and unreplicated points together. A modelling decision, not plumbing. | Decision |
| 6 | **Serialize data + config + RNG state; refit on resume.** Not model weights. | Robust across BoTorch versions. The identical-trace test only passes if RNG state is captured. | ~30 lines |
| 7 | **Metric identity on every data row** — readout name, units, protocol version. | CD31% by flow cytometry and CD31 area by immunofluorescence are different numbers and must never mix. | Free |
| 8 | **Constraint hooks threaded through config** — `equality_constraints`, `inequality_constraints`, `nonlinear_inequality_constraints`, `fixed_features_list`. | Phase 3 will have protein caps and plate arithmetic. Retrofitting changes the optimizer signature everywhere. | ~20 lines |
| 9 | **`X_pending` tracking** for in-flight proposals. | Phase 3 with humans means staggered, asynchronous returns. | One argument |

**Outcome tensors are always `(n, m)`**, even at m=1.

```python
while budget_remaining:
    X = optimizer.ask(q)                    # identical in all three phases
    Y, Yvar = evaluator.evaluate(X)         # only this changes
    optimizer.tell(X, Y, Yvar)              # identical in all three phases
```

```python
class Evaluator(ABC):
    def evaluate(self, X) -> tuple[Tensor, Tensor | None]: ...

class SyntheticEvaluator(Evaluator):   # Phase 1 — calls the oracle
class LookupEvaluator(Evaluator):      # Phase 2 — indexes a digitized table
class HumanEvaluator(Evaluator):       # Phase 3 — writes CSV, waits, reads back
```

---

## 3. Compute

CPU only, laptops. Cholesky at n ≤ 60 is microseconds; the cost is multi-start L-BFGS inside `optimize_acqf`. A GPU would likely be slower — transfer overhead exceeds the compute at this scale.

**MEASURED — PF4 complete.** The estimates below have been replaced with measurements. See `preflight-findings.md`.

| Quantity | Original estimate | **Measured (PF4)** |
|---|---|---|
| One BO round | 3–5 s | **0.5–1.0 s** |
| One 48-evaluation run at q=4 | ~60 s | **4.8–9.2 s** |
| Baseline runs (no model fitting) | near-instant | near-instant |
| Full grid, single-threaded | 3–5 h | **~0.4 h** |
| Full grid, 4–8 workers | under 1 h | **~0.05–0.1 h** |

Roughly **10× cheaper than estimated.** Cost is 92–96% multi-start L-BFGS inside `optimize_acqf`; GP fitting is 4–8%.

**Consequence: the grid does not need to shrink.** Keep d ∈ {6, 8}, both noise levels, 10 instances × 5 seeds. And a full re-run after a bug fix costs about half an hour — on a 14-day timeline, that is the more valuable fact.

*Caveats: measured on a stand-in objective (Hartmann6 at d=6, a synthetic bump function at d=8), because the biphasic oracle did not exist yet. Cost is dominated by acquisition optimization rather than objective evaluation, so the numbers should hold — re-run once the real oracle lands. Single runs, and they jitter: the same d at two noise levels gave 9.2 s and 4.8 s, which is L-BFGS convergence variance, not a noise effect.*

**Two threading settings, not one.** Set `OMP_NUM_THREADS=1` in the environment **before importing torch**, in addition to `torch.set_num_threads(1)` per worker. Some builds fix the OpenMP pool at import and the in-process call arrives too late.

Keep the runner resumable — skip configs whose result file already exists.

---

## 4. The fake data

### 4.1 Search space

Canonical coded `[0,1]^d`. Physical units are labels only.

**Why coded.** Phase 2 digitizes published bar charts whose heatmaps report coded levels — the figure captions state concentrations vary between 0 (lowest for each protein) and 1 (highest). Absolute concentrations appear only in prose, where the source paper is internally inconsistent for one protein. Coded space means Phase 2 never needs absolute units and Phase 1's space definition transfers unchanged.

Physical ranges, for labels only:

| Factor | Range (µg/mL) |
|---|---|
| Collagen I | 0 – 35.5 |
| Collagen IV | 0 – 28 or 56 *(source inconsistent; irrelevant in coded space)* |
| Laminin 111 | 0 – 15.8 |
| Laminin 411 | 0 – 0.8 |
| Laminin 511 | 0 – 0.8 |
| Fibronectin | 22 – 75 *(the 22 floor is a hard attachment constraint)* |

For d=8, add two synthetic cytokine-like factors.

### 4.2 Construction

Each factor is **biphasic** — rises, peaks, declines. High-dose extracellular matrix and growth factors are genuinely inhibitory, so this is the biologically correct shape and it produces a true interior optimum.

```
hᵢ(x) = x^{nᵢ} / (EC50ᵢ^{nᵢ} + x^{nᵢ})        activating, saturating
gᵢ(x) = 1 / (1 + (x / IC50ᵢ)^{nᵢ})            inhibitory
sᵢ = rᵢ^{nᵢ/2}                                 where rᵢ = IC50ᵢ/EC50ᵢ
f̃ᵢ(x) = hᵢ(x)·gᵢ(x)·((1+sᵢ)/sᵢ)²              peak-normalized: f̃ᵢ ∈ [0,1], peak = 1
```

```
f(x) = Σᵢ wᵢ·f̃ᵢ(xᵢ)  +  (1/k)·Σ_{pairs} βᵢⱼ·f̃ᵢ(xᵢ)·f̃ⱼ(xⱼ)          k = ⌈d/2⌉
```

**Observation model:** `y = f(x)·(1 + ε) + η`, `ε ~ N(0, σ_rel²)`, `η ~ N(0, σ_add²)`. The multiplicative term makes variance grow with signal, as real assays do.

**Peak normalization is required, not cosmetic.** Unnormalized peak height spans roughly 0.34 to 0.92 across plausible parameters — a 2.7× range. With `Σwᵢ = 1`, two factors of equal weight would then differ nearly threefold in actual influence, and the non-separability and signal-to-noise checks would be measuring that confound rather than what they claim to. Normalized, `wᵢ` genuinely controls importance and the additive term lands in [0,1].

**The `1/k` scaling is required too.** Without it, interaction magnitude grows with the number of pairs, so d=6 and d=8 would differ in non-separability for reasons unrelated to dimension — and `f` could cross zero, which is unphysical for a differentiation fraction and breaks the multiplicative noise model.

Sparse `βᵢⱼ`, sign unrestricted.

### 4.3 The closed form

With the exponent shared between both arms:

```
x*ᵢ = √(EC50ᵢ · IC50ᵢ)          exactly, by construction
```

Derivation: with `a = EC50ⁿ`, `b = IC50ⁿ`, `u = xⁿ`, the factor is `f = ub/((a+u)(b+u))`, whose derivative numerator is `ab − u²`. So `u* = √(ab)`.

**With `β = 0` the function is separable, so the joint optimum is the vector of per-dimension peaks.** That is an analytic target for the numerical optimum search — the strongest test in the suite, because it has a known answer.

### 4.4 Sampling — invert for depth

**Sample `(x*ᵢ, nᵢ, δᵢ)`. Derive `rᵢ`, then `EC50ᵢ = x*ᵢ/√rᵢ` and `IC50ᵢ = x*ᵢ·√rᵢ`.**

Depth is the property the experiments depend on, so it is the quantity to control directly rather than let float.

#### The inversion

Depth is `δ = 1 − f̃(1)`. Writing `V = x*^{−n}` and `c = 1 − δ`, the defining equation is quadratic in `s`:

```
V(1−c)·s²  +  [2V − c(1+V²)]·s  +  V(1−c)  =  0
```

The two roots multiply to 1 — a reciprocal pair. **Take the root exceeding 1** and set `rᵢ = s^{2/nᵢ}`.

*Verification case:* `x* = 0.4, n = 2, δ = 0.414` → `s = 3.9917`, recovering `r = 4`. Assert this in tests.

#### Feasibility — `δ` is bounded by `(x*, n)`

Not every depth is achievable. At low `x*` and low `n` the discriminant goes negative and no real root exists: a shallow-exponent factor peaking near the origin cannot decline 85% by `x = 1`.

**Sample `δ` relative to what's achievable:**

1. For each factor compute **`δ_max(x*ᵢ, nᵢ)`** — the largest depth with a real root at `r ≤ r_cap`. A 1-D scan over `r ∈ [2, r_cap]`; trivial cost.
2. Sample `δᵢ = u·δ_max` with `u ~ U(0.55, 0.9)`.
3. If `δ_max` falls below the acceptance floor in §4.6, resample `(x*ᵢ, nᵢ)` for that factor.

This guarantees feasibility by construction and gives a **stated ensemble** you can describe in the paper.

#### Parameters

| Parameter | Draw | Justified by |
|---|---|---|
| `x*ᵢ` | U(0.25, 0.55) | **E2 depth.** High `x*` and measurable depth are not jointly achievable — see §4.5. |
| `nᵢ` | U(1.0, 3.0), shared across both arms | Sharing gives the closed form in §4.3 |
| `δᵢ` | `u·δ_max(x*ᵢ, nᵢ)`, `u ~ U(0.55, 0.9)` | Depth is what Claim 1 depends on |
| `rᵢ` | **Derived** by inversion | Sampling `r` independently would make window width correlate with `EC50` by construction |
| `r_cap` | 8 | Bounds the `δ_max` scan |
| `wᵢ` | U(0.75, 1.25), normalized to Σ = 1 | Depth scales with `min wᵢ`, so a wide draw makes the acceptance floor hard to clear |
| Interaction pairs `k` | `⌈d/2⌉` | Non-separability should scale with dimension |
| `βᵢⱼ` | U(−0.4, 0.6), scaled by `1/k` | Keeps interaction magnitude dimension-independent and `f` positive |
| `σ_rel` | **0.10 primary, 0.25 robustness** | Real assay CV exceeds 10%. **Both run on the same ensemble** — see §4.6. |
| `σ_add` | 0.01 | Noise floor |

These parameter choices are ours, not literature values. The "justified by" column names the structural fact each range depends on, so a change to the design becomes a search rather than a recollection.

### 4.5 The design invariant

> **E4 needs the polynomial to extrapolate. E2 needs a measurable peak. Satisfying E4 by pushing the peak toward the box edge flattens it and breaks E2.**
>
> **Move the training box relative to the peak. Never move the peak relative to the box.**

**Why.** With `v = x/x*`, the normalized response is `f̃(v) = v^n(1+s)²/((1+s·v^n)(s+v^n))`. Evaluate at the box edge, `v = 1/x*`.

At `x* = 0.8`, scanning the full stated ranges, the deepest achievable decline is **8.2%** (at `n = 3, r = 2`) — under one sigma at `σ_rel = 0.10`. Raising `n` does not help: since `r ≥ 2` forces `s = r^{n/2}` to grow with `n`, a larger exponent widens the plateau as fast as it sharpens the peak. **A 30% decline is unreachable at `x* = 0.8` at any `n` under `r ∈ [2, 8]`.**

At `x* = 0.4, n = 2, r = 4` the edge value is **0.586** — a 41% decline. Depth lives in the low-`x*` regime.

The `κ·x*` sub-box (§6 E4a) resolves the tension: with training confined to `[0, κ·x*ᵢ]`, the turnover is never in-sample at any `x*`, so E4's mechanism is independent of peak location.

**If more extrapolation is wanted, lower κ. Do not raise `x*`.**

### 4.6 Instance acceptance

With `β = 0` and peak normalization, `f(x*) = 1`, and the boundary maximum is reached by moving one coordinate to 1 with the rest at their peaks. So

```
depth = minᵢ [ wᵢ · δᵢ ]
```

Since `Σwᵢ = 1`, `minᵢ wᵢ ≤ 1/d` — depth is bounded above by 0.167 at d=6 and 0.125 at d=8. **Any acceptance threshold must sit below that bound.** A criterion comparing depth against a single-observation standard deviation is unsatisfiable by construction; the comparison has to be against the **pooled** standard error across the budget. That is the same fact that makes Claim 1 about value rather than location.

**Acceptance criterion — one number, noise-independent:**

```
minᵢ ( wᵢ · δᵢ )  ≥  0.045
```

0.045 is `3σ_rel/√n_budget` evaluated at the primary noise level (`σ_rel = 0.10`, `n = 48`) with a small margin, then **frozen as a structural property of the oracle**.

**Why noise-independent.** A `σ_rel`-dependent criterion would change the ensemble with the noise level, so the 0.10-versus-0.25 comparison would mix a noise effect with an ensemble effect and neither could be attributed. **Generate one ensemble; run both noise levels on it.** Some instances will be unrecoverable at 0.25 — that is the robustness finding, not something to design away.

**Other acceptance checks:**

| Check | Test |
|---|---|
| Positivity | `f > 0` across a dense Sobol sample of the box |
| Closed form | On a **constructed `β = 0` variant** of the accepted instance, the numerical optimum equals `√(EC50ᵢ·IC50ᵢ)` per dimension. *(Generated instances have `β ≠ 0`; build the variant explicitly.)* |
| Non-separability | Coordinate-wise optimum ≠ joint optimum |

**Log the acceptance rate.** With `δ` sampled by inversion rather than rejection it should be high; a low rate means the weight draw is too wide relative to the floor.

### 4.7 Output schema

```
instance_id, oracle_version, seed, dim, x_0 … x_{d-1}, y_true, y_observed, y_var
```

**`instance_id` hashes (dim, seed, oracle_version), and `oracle_version` covers the construction *and the acceptance parameters*.** Under any rejection sampling the seed→instance map depends on the acceptance rule, because rejections consume RNG draws — so changing a threshold without a version bump would make the same `instance_id` denote a different landscape, and results would mix silently in the results files.

`in_subbox` is **not** in this schema — it is an E4 construct, derived at experiment level.

JSON sidecar per instance: sampled `x*`, `n`, `δ`, `w`, `β`; derived `r`, EC50, IC50; `δ_max` per factor; cached optimum and value; acceptance results.

### 4.8 The returned `Yvar`

Analytic variance `f(x)²σ_rel² + σ_add²` is a function of the **noiseless** value, from which `|f(x)|` is exactly recoverable. Returning it would hand the model the truth at every training point — which corrupts E3 specifically, and doesn't transfer, since Phase 2 has no variance and Phase 3 has replicate SEM.

**Default: the plug-in estimate** `ŷ²σ_rel² + σ_add²`, computed from the observed value — what a lab actually computes.

**Known bias, pre-identified.** `E[y_obs²] = f²(1+σ_rel²) + σ_add²`, so the plug-in over-estimates by ~1% at `σ_rel = 0.10` and ~6% at 0.25. A point that drew high noise gets a larger `Yvar` and is down-weighted — a systematic shrinkage effect. This happens in real labs, so it is the right default. **If E3 shows mild over-coverage at the higher noise level, this is the first candidate, not a bug.**

**Ablation:** the analytic version, as an upper bound on calibration under perfect noise knowledge.

---

## 5. The model

```python
covar_module = get_covar_module_with_dim_scaled_prior(
    ard_num_dims=d, use_rbf_kernel=False        # Matérn 5/2; default is True → RBF
)
covar_module = ScaleKernel(covar_module)        # learned outputscale — primary config

model = SingleTaskGP(
    train_X, train_Y, train_Yvar,
    covar_module=covar_module,
    input_transform=Normalize(d=d, bounds=space.bounds),   # explicit bounds, always
    outcome_transform=Standardize(m=m),
)
```

`qLogExpectedImprovement`. `optimize_acqf(num_restarts=10, raw_samples=512)` for continuous, discrete mode for fixed candidate sets. Sobol initial design of `2d+2`.

**Outputscale is a config axis, learned primary.** Fixed at 1 with `Standardize` puts the far-from-data 95% interval at approximately ±1.96 × training-sd in raw units. E4's sub-box sits where training sd is compressed, so a fixed outputscale could make the interval narrow for a reason unrelated to the hypothesis.

For the legacy prior configuration, `get_matern_kernel_with_gamma_prior` exists — no need to hand-roll it.

### Five traps that fail silently

> **This section said "three" until PF3 was run on the installed version. There are five.** Traps 4 and 5 were found while testing the resolution to trap 4. All five are verified against the installed BoTorch 0.18.1 / gpytorch 1.15.2. **None produces an error message.** See `preflight-findings.md` for the probe output.

1. **`use_rbf_kernel` defaults to `True`.** Omitting the override gives an RBF kernel, silently, and a methods section that is false. Test for it. ✅ *verified on installed version*
2. **The function returns a bare `MaternKernel | RBFKernel`, not wrapped in `ScaleKernel`.** Lengthscales are at `model.covar_module.lengthscale`; the common tutorial idiom `.base_kernel.lengthscale` raises AttributeError. The prior is constrained above **0.025** on this version. **Write a defensive traversal helper** — the primary config *does* wrap in `ScaleKernel`, so any hardcoded path breaks on one of the two configurations. Read the constraint bound off the constraint object rather than hardcoding it; it is version-dependent. ✅ *verified — and note the asymmetry: the legacy `get_matern_kernel_with_gamma_prior` returns a `ScaleKernel` while `get_covar_module_with_dim_scaled_prior` returns a bare kernel. Two factories, two return shapes. This is why the helper is not optional.*
3. **`Normalize` without `bounds=` learns from training-data min/max.** E4's training data is deliberately a sub-box, so without explicit bounds the extrapolation point lands outside the unit cube and nothing compares across instances. ✅ *verified — on a `[0, 0.32]⁶` sub-box, a query at 0.85 mapped to 2.72–3.01.*
4. **`observation_noise=True` substitutes `mean(train_Yvar)` at unevaluated inputs.** Under the fixed-noise likelihood that contract item 5 mandates, BoTorch averages the training noise and applies that flat value to every query point. `botorch/models/gpytorch.py:532`, carrying the comment `# Use the mean of the previous noise values (TODO: be smarter here).` **Confirmed to be the mean and not the median** by planting an outlier in `train_Yvar`. `batch_cross_validation(observation_noise=True)` inherits the same path. **E3's primary metric is coverage at exactly these points**, so left alone the headline calibration number is computed against a noise level nobody chose. **Resolution: pass a tensor to `observation_noise` — it is honoured per-point — computed from the plug-in formula, and say so in methods.**
5. **The supplied `observation_noise` tensor must be in STANDARDIZED units, while `train_Yvar` is in RAW units.** The noise is applied to the internal standardized model *before* `Standardize` untransforms the posterior. Pass the raw plug-in variance — the obvious thing to do — and you are wrong by a factor of `outcome_transform.stdvs**2`, measured at **161×** in the PF3 test case. Divide by `stdvs**2` first. The factor depends on the training data, so it differs per fit and per CV fold. **Same family as the two `Yvar` traps in §9** (variance-vs-sd, raw-vs-transformed), which also produce plausible-looking but systematically wrong calibration.

---

## 6. The four experiments

### E1 — Correctness

BoTorch standard functions: Branin (2-D), Hartmann6 (6-D, deceptive), Ackley (many local optima). 20 seeds each.

Plus: on a `β = 0` oracle instance, BO converges toward `√(EC50·IC50)` per dimension.

**Passes if** BO finds the known optimum and beats random search. Losing to random on Hartmann6 means a bug.

### E2 — Sample efficiency

qLogEI vs **random, Sobol, LHS, and a sequential DoE pipeline.**

**The DoE arm, with a confirmation evaluation:**

```
Stage 1  two-level screening design + centre points        ~half of 47
Stage 2  CCD centred on the best stage-1 region            remainder of 47
Stage 3  fit second-order model, locate the stationary point
Stage 4  EVALUATE IT                                       1 run
```

**47 design runs plus 1 confirmation = 48.** Without stage 4 the arm's best-so-far is just its best design point and the pipeline's actual output never enters the regret curve. The published study evaluated its predicted optimum; so should this.

> **This connects the two experiments.** The confirmation run *is* E4a, inside E2. If the DoE arm's confirmation lands outside its own design region and under-delivers, the published failure mode reproduces in the benchmark without being staged for it — a stronger result than E4a in isolation, at the cost of one run.

**Scoped deliberately.** Reproducing the published study's exact 23-run screening design is out of scope: `1 + 6 + C(6,2) = 22` is the two-factor-interaction parameter count in six factors, suggesting a D-optimal custom design, and coordinate-exchange construction is real work for a Phase 1 baseline. **Phase 2 is the definitive DoE comparison — there you implement nothing, because the published data already contains it.**

**Ordering for static baselines.** A one-shot design has no regret *curve* — best-so-far is a step function determined by arbitrary run order, so AUC over it is meaningless. **Randomize run order and average over orderings.**

Oracle at d ∈ {6, 8}. **10 instances × 5 seeds.** Budget 48 evaluations.

**Budget convention, enforced identically across methods.** d=6: 14 initial + 8 batches of 4 + one trailing batch of 2 = 48. d=8: 18 initial + 7 batches of 4 + one trailing batch of 2 = 48.

**What the seed varies:** the initial design draw and the noise draws. The instance is separately seeded. **The initial design must be identical across methods for a given seed** — paired comparison at n=50 is the difference between a significant and a non-significant result. Test for it.

**Report:** best-so-far and log₁₀ regret; median with interquartile bands; **simple regret at budget and AUC over the post-initialization segment**, with bootstrapped CIs and paired tests. Computing AUC from evaluation 1 would include the shared initial design and dilute the between-method difference.

**Instances over seeds:** five seeds on ten landscapes generalizes better than fifty seeds on one, because across-landscape variance is usually larger.

**d=12 is a capability test, not an experiment.** `2d+2 = 26` of 48 leaves 22 adaptive evaluations.

### E3 — Calibration

**Prospective (primary), at two point sets.** Each round, log the GP's predictive distribution *before* evaluating:

- **at BO-proposed points** — decision-relevant, but this is coverage *under a selection rule*, since acquisition maximization deliberately targets high-mean and high-variance regions
- **at a fixed held-out Sobol set** — domain-wide coverage, no selection effect

Two lines of extra code. **The gap between them is itself informative** and should be reported.

**Leave-one-out (secondary).** Use `batch_cross_validation`, which fits separate models with separate hyperparameters per fold. **Do not use `loo_cv` for any published number** — its documentation states it does not refit the model to each fold and keeps hyperparameters fixed as a fast approximation. Used naively, the held-out point has already influenced the model and coverage comes out optimistically inflated.

**Watch the noise flag.** `batch_cross_validation(..., observation_noise=False)` is the default, which gives **latent** coverage. Pass `observation_noise=True` for coverage of what a lab measures — the primary metric.

**Error bars are mandatory.** Coverage at nominal 0.95 with n=48 has SE ≈ 3.1%, so 95% and 89% are indistinguishable in a single run. **Bootstrap at the instance level only** — resample instances with replacement and recompute the statistic from all their data. Points within a run are sequential BO proposals and are not exchangeable, so resampling them is invalid.

**CRPS has a closed form** for a Gaussian predictive: `σ[z(2Φ(z)−1) + 2φ(z) − 1/√π]` with `z = (y−μ)/σ`. Don't sample it.

**State which σ.** Posterior predictive (includes observation noise) → coverage of measurements; **primary**. Latent posterior → coverage of the underlying function; a model diagnostic. Report both, labelled.

**Self-test:** fit the GP to a function generated *from* a GP, where coverage should be near-perfect by construction. If it isn't, the bug is in the code.

### E4 — Detecting extrapolation-driven over-prediction

**d=6 only, `n_subbox = 48`.** See the estimability note below.

#### E4a — the measurement

Per instance, per κ ∈ {0.6, 0.7, 0.8, 0.9}:

1. **Sub-box `[0, κ·x*ᵢ]` per dimension, sampled by a CCD-family design** — a central composite design scaled into the sub-box.

   > **The design is not optional detail.** `(XᵀX)⁻¹` — hence the polynomial's prediction interval, which *is* the comparator in the discrimination test — depends entirely on it. A space-filling sample and a CCD give different interval widths at the same extrapolation distance. It is also a fairness question: a response-surface practitioner would use a CCD, and the prediction-interval formula in step 5 is the formula for a designed experiment. **Use identical points for all four models.**

2. **Fit four models to identical data:** a **second-order polynomial** (primary), a **stepwise-reduced third-order polynomial** (descriptive only), the **GP**, and a **practitioner-form parametric model** — additive biphasic, no interaction terms, by nonlinear least squares.

3. **Optimize all four over the same extended box** (the unit cube).

4. **Primary outcome: over-prediction at each model's constrained argmax over the extended box** — `predicted value − true value`. Always defined regardless of curvature.

   > **Why the constrained argmax rather than stationary-point escape.** Inside `[0, κ·x*]` you are on the rising arm, and for `n > 1` the Hill function is convex below its inflection. At low κ the second-order fit therefore has *positive* curvature and its stationary point is a **minimum** — "did the stationary point escape the sub-box" would be answering a question about a minimum. Stationary-point location and Hessian classification are reported as a **distribution**, descriptively.

5. **Prediction intervals**, second-order and GP only:
   - Polynomial: `ŷ ± t·σ̂·√(1 + x₀ᵀ(XᵀX)⁻¹x₀)`
   - GP: posterior predictive

   **Both must be reported.** A polynomial response surface *does* have prediction variance; comparing a GP posterior against a bare polynomial point estimate would be an unfair comparison and the first thing a reviewer would object to.

**Why second-order is primary:**

*Estimability.* Second-order has `1 + 2d + C(d,2)` terms — **28 at d=6** (20 residual df at n=48, workable) but **45 at d=8** (3 residual df, `t₀.₉₇₅,₃ = 3.18`, and the interval balloons for reasons unrelated to extrapolation, which would make the polynomial look well-calibrated and collapse the comparison). Full third-order is `C(d+3,3)` — **84 at d=6, 165 at d=8** — rank-deficient at n=48, so `(XᵀX)⁻¹` does not exist and step 5's formula is undefined.

*Literature.* Canonical and ridge analysis are second-order techniques. That is the literature this experiment cites.

*Post-selection inference.* A stepwise model selects terms from the same data its interval is computed from, so that interval is **anticonservative — too narrow for reasons unrelated to extrapolation.** Fatal here, because "the polynomial's interval is too narrow" is exactly what E4a wants to conclude. **Report the stepwise third-order model descriptively — over-prediction, stationary-point classification, surviving term count — and omit its interval entirely.** *(Stepwise reduction also matches published practice: "only significant terms up to the 3rd order.")*

**Parametric comparator: practitioner-form only.** Additive biphasic without interaction terms — what someone would try without knowing the truth. An oracle-form fit is matched by construction, wins trivially, and tells you nothing. **Log NLS convergence failure rates** rather than silently dropping instances.

#### The discrimination test — the actual novel claim

Note this **never touches the stationary point.** It is Spearman ρ between scorers and `|polynomial error|` over a Sobol candidate set. The stationary point is the narrative hook; this is the measurement.

**Candidate set:** a Sobol sample of N points over the extended box, per instance. Not one point per instance — with 10 points the AUC has no usable standard error.

**Three scorers:**

| Scorer | What it is |
|---|---|
| GP predictive sd | The claim |
| Second-order PI width | The DoE comparator |
| **Nearest-neighbour distance to the training set** | **The model-free null** |

**Nearest-neighbour, not centroid distance.** It is the sharper null — it is what GP predictive sd actually approximates, whereas centroid distance ignores design geometry. If the GP has an edge it comes from ARD lengthscales making its distance anisotropic, so an isotropic null is the right thing to beat.

**"The GP is uncertain far from data" is near-tautological.** The result only means something if the flag is *selective*. **If plain distance discriminates as well as GP predictive sd, the result is that the GP is an expensive distance function** — and that is the comparison a reviewer reaches for.

**Report the scorer–scorer rank correlation matrix first.** With the sub-box in a corner and candidates over the unit cube, all three may be monotone in the same underlying quantity. ρ > 0.95 among scorers would mean there is no headroom for the comparison to show anything either way. **The reader needs to see the headroom before seeing the result.**

**Primary: Spearman ρ** against `|polynomial error|` — no threshold to justify. **Secondary: AUC** at a pre-registered τ. **CIs by instance-level bootstrap.**

#### E4b — Design boundary (reported, not claimed)

A distinct failure mode: the true optimum lies **outside the design box entirely**, and the model reports its constrained corner as the optimum.

Construct a variant where one factor's true optimum lies below the lower bound. Fit all four models. Does any signal that the surface is still improving at the boundary?

**Report honestly.** A polynomial's fitted coefficient in that dimension will be significantly negative and *will* signal "lower is better" — which is what the published study observed and acted on. **This is not a mechanism where the GP wins.** It is a design-space problem, not a modelling-uncertainty problem, and claiming otherwise would be indefensible to anyone who has read the source paper.

**Claim E4a. Report E4b.**

---

## 7. Pre-flight — before Build Step 2

Four checks. Two of them can change the plan.

> **STATUS: PF3 ✅ and PF4 ✅ are DONE (Person B).** Results in `preflight-findings.md`. PF3 found two silent failures, now traps 4 and 5 in §5. PF4 replaced §3's estimates. **PF1 and PF2 (Person A) remain open, and PF1 is the entire remaining pre-flight risk.**
>
> **Ordering problem, stated plainly.** "Pre-flight before Build Step 2" is not achievable as written. PF1 needs the oracle (Build Step 2), a CCD sub-box design (`designs.py`, Build Step 3), *and* a second-order fit plus over-prediction metric (`rsm.py`/`metrics.py`, Build Step 3). The check that is meant to precede building requires building. On a 14-day horizon nothing can be written twice, so: **`metrics.py`, `rsm.py`, and `designs.py` were built first, properly, rather than as throwaways** — they are needed for PF1/E4 anyway, and A imports the over-prediction metric. **PF1 now needs only the oracle.** Face-centred CCD composition is settled (32+12+4); A's ownership confirmation on `designs.py` remains open.

1. **Over-prediction versus κ.** Across 10 instances, κ ∈ {0.6, 0.7, 0.8, 0.9}: the second-order model's over-prediction at its constrained argmax, **plus the Hessian classification distribution** (max / min / saddle / ridge). A bare rate would hide that low κ produces minima rather than escaped maxima. **If over-prediction is near zero at every κ, E4a has no mechanism** and the parameters need revisiting before anything is built on it.

2. **Inversion and acceptance.** Does `(x* = 0.4, n = 2, δ = 0.414)` return `s = 3.9917`? Does the closed form hold on the `β = 0` variant? **What is the instance acceptance rate**, and what is the achieved distribution of `δ_max`?

3. ~~**API signatures.**~~ ✅ **DONE.** All five questions answered on botorch 0.18.1 / gpytorch 1.15.2 / torch 2.13.0. `use_rbf_kernel` defaults `True` and returns a bare kernel; `Normalize` without `bounds=` does learn from training min/max; `optimize_acqf_discrete(acq_function, q, choices, ..., inequality_constraints=None)`; lengthscale constraint `GreaterThan(0.025)`. **And `observation_noise=True` does silently substitute a heuristic — the mean of `train_Yvar`.** It was the "silently substitute" branch, not the "raise" branch. Resolution implemented as anticipated, *plus* a units trap the spec did not anticipate. Traps 4 and 5 in §5.

4. ~~**Wall-clock.**~~ ✅ **DONE.** ~10× faster than estimated. §3 updated. The grid does not need to shrink.

---

## 8. Repo layout

Repo: `akwnn/nutrigene-ai-bo-ipsec`, shared between A and B. Package name stays `boec`.
✅ = exists on disk · ⬜ = not written yet · **(A)** / **(B)** = owner.

```
nutrigene-ai-bo-ipsec/
├── .gitignore             ✅  .venv is ~950 MB — never commit it
├── requirements.txt       ✅  exact pins; both people must match
├── pyproject.toml         ✅  pytest pythonpath = src
├── src/boec/
│   ├── space.py           ⬜ (A) SearchSpace: coded bounds, types, constraint hooks
│   ├── oracles.py         ⬜ (A) Oracle ABC, test functions, biphasic oracle + inversion
│   ├── evaluators.py      ⬜ (A) Evaluator ABC, SyntheticEvaluator
│   ├── designs.py         ✅ (B wrote; A ownership call open) CCD, screening, sub-box — face-centred default
│   ├── diagnostics.py     ⬜ (A) batch_cross_validation, reliability, instance bootstrap
│   ├── surrogate.py       ✅ (B) build_gp, kernel traversal helper, predictive noise wrapper
│   ├── rsm.py             ✅ (B) 2nd-order fit, PIs, Hessian; stepwise 3rd-order descriptive
│   ├── parametric.py      ✅ (B) practitioner-form biphasic NLS
│   ├── discrimination.py  ✅ (B) E4 scorers + discrimination test
│   ├── optimizers.py      ✅ (B) qLogEI (continuous + discrete), baselines
│   ├── campaign.py        ✅ (B) ask/tell, X_pending, serializable (data+config+RNG)
│   ├── metrics.py         ✅ (B) over-prediction metric — **A imports this**
│   └── runner.py          ✅ (B) resumable grid runner
├── configs/
│   └── experiment/e4.yaml ✅ (B) E4 pre-registration — the two locked numbers
├── scripts/
│   ├── preflight_pf3.py   ✅ (B) API probe — PF3
│   ├── preflight_pf4.py   ✅ (B) wall-clock — PF4
│   ├── generate_oracles.py ⬜ (A)
│   ├── run_experiments.py ⬜
│   └── make_figures.py    ⬜
├── docs/                  ✅  specs + plain-english + OPEN-QUESTIONS + preflight-findings
├── data/oracles/          ⬜  generated instances + JSON sidecars
├── results/                   parquet + JSON sidecars, gitignored
└── tests/                 ✅  **218 tests passing** (metrics 10, rsm 15, rsm_stepwise 18, designs 28, surrogate 24, optimizers 30, campaign 27, parametric 15, discrimination 27, runner 24)
```

**Ownership note:** `rsm.py` and `metrics.py` were pulled forward out of Build Step 3 because PF1 cannot run without them (see §7). `designs.py` was likewise written by B for the same reason — **A's one-sentence ownership call is still open** (`OPEN-QUESTIONS.md` Q2). Face-centred vs rotatable inside the sub-box is **decided: face-centred** (rotatable axials leave the hard boundary).

---

## 9. Tests

| Test | Asserts |
|---|---|
| **Inversion round-trip** | `(x*=0.4, n=2, δ=0.414) → s = 3.9917 → r = 4`; and `δ(r) → r` recovers the input for random draws |
| **Inversion picks the right root** | The returned `s > 1`, and the two roots multiply to 1 |
| **`δ_max` feasibility** | Sampled `δ ≤ δ_max`; discriminant non-negative for every generated factor |
| **Closed-form optimum** | On the `β=0` variant, optimum equals `√(EC50·IC50)` per dimension |
| **Peak normalization** | `max_x f̃ᵢ(x) == 1` to tolerance |
| **Acceptance floor** | Every accepted instance satisfies `minᵢ wᵢδᵢ ≥ 0.045` |
| **Acceptance is noise-independent** | The same ensemble is produced regardless of `σ_rel` |
| **`oracle_version` covers acceptance params** | Changing a threshold changes the hash |
| **Positivity** | `f > 0` across a dense Sobol sample |
| **`Yvar` units and shape** | Variance, not standard deviation. **The classic fixed-noise GP bug** — it produces plausible-looking but wrong calibration. |
| **`Yvar` in raw outcome units** | `Standardize` handles the scaling. A separate bug from variance-vs-sd. |
| **Oracle noise** | Empirical variance of repeated `evaluate` matches the **analytic** variance. *(The plug-in varies across repeats — check its bias separately against the closed form.)* |
| **`Standardize` inverse-transforms variance** | Not just the mean. All of E3 depends on it. |
| **Supplied prediction-noise units round-trip** | Pass plug-in variance `v` as `posterior(X, observation_noise=v/stdvs**2)` and assert the added variance comes back as exactly `v` in raw units. **Trap 5 — off by 161× in the PF3 case if you pass raw.** Separate bug from the two `Yvar` rows above. |
| **`observation_noise=True` is never used for a published number** | It substitutes `mean(train_Yvar)` silently (trap 4). Assert the code path supplies an explicit tensor. |
| **Transform applied in eval mode** | `model.posterior(X_raw)` matches the manually-normalized path |
| **Kernel identity via traversal helper** | Not `isinstance(...)` — that breaks under `ScaleKernel` |
| **Lengthscale bound read, not hardcoded** | From the constraint object; version-dependent |
| **CV refit** | Per-fold hyperparameters actually **differ** |
| **Sub-box CCD full rank** | For second-order at the chosen `n_subbox` |
| **Identical design across models** | All four E4 models fit the same points |
| **DoE arm spends 48** | 47 design + 1 confirmation, and the confirmation enters the regret curve |
| **Evaluator can't leak `y_true`** | The entire regret story depends on it |
| **Paired initial design** | Identical across methods for a given seed |
| **Polynomial correctness** | Second-order recovers known coefficients and prediction variance on a synthetic quadratic |
| **Hessian classification** | Correct labels on constructed max / min / saddle / ridge cases |
| Discrete mode | Every proposal comes from the candidate set |
| Serialization round-trip | Data + config + RNG resumes to an identical trace |
| Non-separability | Coordinate-wise optimum differs from joint |
| Acquisition | qLogEI proposes near the true max on a 1-D toy |
| Batch diversity | q=4 proposals aren't all within ε |
| Shape contract | Outcomes are `(n, m)` everywhere |
| Resumability | Re-running a completed config skips it |
| Smoke | Branin, 20 iterations, regret decreases |

---

## 10. Claude Code build prompt

*Copy from here down.*

---

### Project

Build a Bayesian optimization framework in Python for a research paper on optimizing stem-cell differentiation protocols. **Synthetic data only.** This is a control experiment: it proves the optimizer is correct and well-calibrated on data where the answer is known, before application to real data in later stages that are out of scope here.

Structure it so those stages are drop-in additions. "Forward compatibility" is a hard requirement.

### The four claims the code must support

1. Recovers the planted optimum's **value** within a tolerance stated as a fraction of instance depth
2. More sample-efficient than random, Sobol, LHS, and a sequential DoE pipeline
3. Uncertainty estimates are calibrated, with instance-level bootstrap error bars
4. Extrapolation-driven over-prediction is detectable from GP predictive variance **more selectively than from nearest-neighbour distance to the training set** — a model-free null that must be beaten

Nothing outside these four.

### Forward compatibility — hard requirements

1. **Ask/tell separation.** A separate `Evaluator` supplies outcomes; the optimizer never calls the oracle.
2. **Discrete candidate mode.** Choosing the best q from a fixed candidate set, alongside continuous acquisition optimization. **Confirm the correct BoTorch function name and signature on the installed version and report it.**
3. **Search space in config**, canonically coded `[0,1]`, physical labels optional.
4. **Continuous, integer, and categorical types in the schema**, though only continuous is used now.
5. **Always pass `Yvar`**, imputed where unreplicated from a mean–variance relation with a floor. Do not build a path that mixes supplied and inferred noise in one model.
6. **Serialize data + config + torch/numpy/python RNG state**; refit on resume. **Not model weights.**
7. **Every data row records metric name, units, protocol version.**
8. **Constraint hooks threaded through config** — `equality_constraints`, `inequality_constraints`, `nonlinear_inequality_constraints`, `fixed_features_list`.
9. **`X_pending` tracking** for in-flight proposals.

### Environment

Local machine, CPU only. Python ≥3.11, torch ≥2.2, gpytorch ≥1.15.1, botorch 0.18.x, statsmodels, scipy, pandas, pyarrow, pytest. **Exact pins in `requirements.txt`.** **Check installed API signatures and report anything differing from this prompt** rather than assuming.

No Docker, no Hydra, no GPU. Set `OMP_NUM_THREADS=1` in the environment **before importing torch**, plus `torch.set_num_threads(1)` per worker. The runner must skip configs whose result file already exists.

### The oracle — sample the peak and the depth, derive everything else

Sample `x*ᵢ ~ U(0.25, 0.55)` and `nᵢ ~ U(1,3)`. For each factor compute `δ_max(x*ᵢ, nᵢ)` by scanning `r ∈ [2,8]`, then sample `δᵢ = u·δ_max` with `u ~ U(0.55, 0.9)`.

**Derive `rᵢ` by inverting the depth equation.** With `V = x*^{−n}`, `c = 1−δ`:

```
V(1−c)·s²  +  [2V − c(1+V²)]·s  +  V(1−c)  =  0
```

Roots multiply to 1; **take the root exceeding 1**; `r = s^{2/n}`. Then `EC50 = x*/√r`, `IC50 = x*·√r`. Assert the verification case `(0.4, 2, 0.414) → s = 3.9917`.

Peak-normalize `f̃ᵢ = hᵢgᵢ((1+sᵢ)/sᵢ)²` with `sᵢ = rᵢ^{nᵢ/2}`. Combine `f = Σwᵢf̃ᵢ + (1/k)Σβᵢⱼf̃ᵢf̃ⱼ`, `k = ⌈d/2⌉`, `wᵢ ~ U(0.75,1.25)` normalized, `βᵢⱼ ~ U(−0.4,0.6)`.

**Acceptance: `minᵢ wᵢδᵢ ≥ 0.045`, positivity, closed form on a constructed `β=0` variant, non-separability.** The acceptance floor is **noise-independent and frozen** — one ensemble serves both noise levels. Hash acceptance parameters into `oracle_version`.

**Critical invariant:** `x*` is chosen for E2's depth. E4's mechanism comes from the sub-box `[0, κ·x*ᵢ]`. **Never raise `x*` to increase extrapolation — lower κ instead.** High `x*` and measurable depth are not jointly achievable.

### Model configuration — do not substitute

```python
covar_module = ScaleKernel(get_covar_module_with_dim_scaled_prior(
    ard_num_dims=d, use_rbf_kernel=False))
model = SingleTaskGP(train_X, train_Y, train_Yvar,
    covar_module=covar_module,
    input_transform=Normalize(d=d, bounds=space.bounds),
    outcome_transform=Standardize(m=m))
```

`qLogExpectedImprovement`, `optimize_acqf(num_restarts=10, raw_samples=512)`, Sobol initial design of `2d+2`.

**Five silent-failure traps:** `use_rbf_kernel` defaults to `True`, so omitting the override gives RBF with no error — test `isinstance` through a helper. The function returns a **bare kernel** while the primary config wraps it in `ScaleKernel`, so **write a defensive traversal helper** and use it everywhere including tests; read the lengthscale constraint bound off the constraint object. `Normalize` without `bounds=` learns from training-data min/max, which breaks Experiment 4. **`observation_noise=True` silently substitutes `mean(train_Yvar)` at unevaluated points** — pass an explicit tensor instead. **That tensor must be in standardized units** (`÷ stdvs**2`), while `train_Yvar` is raw — see §5 traps 4–5 and `preflight-findings.md`.

**Deprecated — do not use:** `AxClient` · `FixedNoiseGP` (use `SingleTaskGP` with `train_Yvar`) · `HeteroskedasticSingleTaskGP` · `qExpectedImprovement` without the `Log` prefix.

**Outcomes are `(n, m)` tensors always. Dimension is a config parameter — must run at d=4 and d=12 by changing YAML. Batch proposals use joint q-acquisition**, never top-q of a single-point surface.

### Build steps — stop and report at each boundary

**Build Step 1 — Pre-flight.** Report: (a) second-order over-prediction at its constrained argmax versus κ ∈ {0.6,0.7,0.8,0.9} across 10 instances, **with the Hessian classification distribution**; (b) the inversion verification case, the closed-form check on the `β=0` variant, the instance acceptance rate, and the `δ_max` distribution; (c) API signatures **including what `observation_noise=True` does under a fixed-noise likelihood at an unevaluated input**; (d) wall-clock including the second noise level. **Report all four before proceeding.**

**Build Step 2 — Space, oracles, evaluators.** `SearchSpace` from YAML with constraint hooks. `Oracle` ABC. Standard test-function wrappers. Biphasic oracle with the inversion, `δ_max` scan, acceptance checks, `instance_id` hashing, cached optima, JSON sidecars. Plug-in `Yvar` default with analytic ablation flag. `Evaluator` ABC plus `SyntheticEvaluator`. A `generate_oracles.py` producing 10 instances at d=6 and d=8.

**Build Step 3 — Surrogate, RSM, designs, parametric, diagnostics.** `build_gp` with the traversal helper. `rsm.py`: second-order with closed-form prediction intervals, Hessian classification, ridge-analysis fallback; stepwise third-order **descriptive only, no interval**. `designs.py`: CCD and screening designs, sub-box scaling. `parametric.py`: practitioner-form biphasic NLS logging convergence failures. `batch_cross_validation` with per-fold refitting and explicit `observation_noise`. Coverage, reliability curves, **closed-form CRPS**, **instance-level bootstrap**.

**Build Step 4 — Optimizers and loop.** qLogEI, continuous and discrete. Random, Sobol, LHS, and a **sequential DoE pipeline with 47 design runs plus 1 confirmation evaluation that enters the regret curve**. Randomized run ordering for static baselines. Campaign loop with `X_pending`, serializable state, and per-round logging of predictive distributions at **both** proposed points and a fixed held-out Sobol set, before evaluation.

**Build Step 5 — Resumable runner.** Grid over instances × seeds × methods × oracles → parquet with JSON sidecars carrying resolved config and library versions. Skip-if-exists. Optional multiprocessing.

**Build Step 6 — Experiments E1–E4.** E4 at **d=6 only, `n_subbox = 48`, CCD sub-box design, identical points for all four models**, κ swept. Discrimination test with three scorers including **nearest-neighbour distance**; **report the scorer–scorer rank correlation matrix first**.

**Build Step 7 — Figures.** Convergence with IQR bands, reliability curves with bootstrap intervals, over-prediction versus κ, Hessian classification distribution, scorer correlation matrix, discrimination across all three scorers, lengthscale importance.

### Style

Type hints throughout. Docstrings stating tensor shapes. No global state. Fail loudly on shape mismatches. Comment every deliberate override of a BoTorch default. **This code is read by biologists — clarity over cleverness.**

### Ask rather than assume

Installed API signatures differing from this prompt · screening design choice for the sequential DoE pipeline at each dimension · stepwise selection criterion for the descriptive third-order fit.

**Settled (were on this list):** face-centred versus rotatable CCD inside the sub-box → **face-centred** (rotatable axials leave the hard boundary; see `boec.designs` and `OPEN-QUESTIONS.md` Q9).

---

## 11. When it misbehaves

**Generation never terminates** → the acceptance floor is unreachable. Check `minᵢ wᵢδᵢ` against 0.045 directly, and confirm `δ` is sampled relative to `δ_max` rather than uniformly.

**The GP fits badly** — LOO predictions near-flat, predicted-vs-observed a horizontal smear:

1. **Are the transforms attached, with explicit bounds?** By a wide margin the most common cause.
2. **Is the kernel actually Matérn?** Check through the traversal helper, not a hardcoded path.
3. **Are lengthscales at a bound?** Read the constraint's lower bound off the object. Sitting there means the function is wilder than the kernel can represent. At the top end, the GP thinks that dimension does nothing — sometimes true and informative.
4. **Fewer than ~2d points?** Hyperparameters are essentially prior samples. Fix with seed data, not modelling.
5. **Is `Yvar` variance or standard deviation? In raw outcome units?** Two separate bugs, both producing plausible-looking wrong calibration.

> "Is `model.likelihood.noise` large?" applies **only on the `Yvar=None` path.** Contract item 5 mandates supplied `Yvar`, so the likelihood is fixed-noise and there is no inferred noise parameter to inspect.

**Mild over-coverage at the higher noise level** → the plug-in `Yvar` bias (§4.8). Pre-identified, not a bug.

**Over-prediction near zero at all κ** → the sub-box isn't excluding the turnover. Check `x*` is being used per dimension rather than a fixed box.

**All three scorers rank-correlate above 0.95** → no headroom; the discrimination test cannot show anything either way. Report it as such rather than reporting a null result.

**Over-exploitation** (resamples one region) → overconfident GP, lengthscales too short. Check for under-coverage.
**Over-exploration** (wanders, never refines) → lengthscales too long, or supplied `Yvar` too large.

**Batch proposals cluster** → not using joint q-acquisition, or `num_restarts`/`raw_samples` too low. Try 20 / 1024.

**Calibration below the diagonal** = overconfident = the dangerous direction, since it undermines the whole uncertainty argument. Check CRPS too — uniformly wide intervals score perfectly on coverage and terribly on CRPS. And check the error bars before concluding anything.

**BO loses to a baseline** → a deceptive function (Ackley is built for this), dimension too high for the budget, noise dominating signal, or a bug. Losing on Hartmann6 is a bug.

**Knobs ranked by how much they matter:**

1. Normalization with explicit bounds, and output standardization — binary, right or catastrophically wrong
2. `Yvar` correctness — units, shape, and whether it leaks the truth
3. Seed data relative to `d`
4. Outputscale learned versus fixed — specifically for extrapolation coverage
5. Kernel and lengthscale priors
6. Acquisition function choice
7. Batch size `q`; `num_restarts` / `raw_samples` — only when candidates cluster

Most first-time failures are (1) and (2).
