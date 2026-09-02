# PHASE 1 — FAKE DATA
## Build specification for the Bayesian optimization model

**Document 1 of 3.** The buildable spec.
**Document 2** (`project_record.md`) — project context, scientific argument, Phase 2 and 3 plans, research grounding, decision log.
**Document 3** (`provenance_audit.md`) — which claims were verified against primary sources.

> **v6 — oracle version bump.** v5's depth criterion `f(x*) − max_{∂box} f > 3σ_rel·f(x*)` **cannot be satisfied by any instance at any dimension or noise level** — depth is bounded above by `1/d` while the threshold is `0.30`. Generation would never terminate. The oracle is now sampled by `(x*, n, δ)` with the window ratio `r` **derived by inversion**, the acceptance criterion compares against the *pooled* standard error and is **noise-independent**, the E4 sub-box uses a **CCD design** rather than an unspecified fill, E4a's primary outcome is **over-prediction at the constrained argmax** rather than stationary-point escape, the discrimination null is **nearest-neighbour distance**, and the DoE arm gets a **confirmation evaluation**.
>
> **All cached optima from v3–v5 are void.**

---

## Vocabulary

| Term | Meaning |
|---|---|
| **Phase 1 / 2 / 3** | **Phase 1 = fake data (this doc). Phase 2 = published data. Phase 3 = in-house lab data.** |
| **Build Step 1–7** | Milestones inside the Phase 1 code. Unrelated to project phases. |
| **`x*ᵢ`** | Peak location of factor *i*. **Sampled directly.** |
| **`δᵢ`** | **Depth** of factor *i*: `1 − f̃ᵢ(1)`, the normalized decline from peak to the upper box edge. **Sampled directly.** |
| **`rᵢ`** | Window ratio `IC50ᵢ/EC50ᵢ`. **Derived** from `(x*ᵢ, nᵢ, δᵢ)` by inversion. |
| **Sub-box** | E4's training region, `[0, κ·x*ᵢ]` per dimension. An *experiment* construct. |
| **Extended box** | The full unit cube. Where all models are optimized in E4. |

---

## 1. What Phase 1 is for

| # | Claim | Notes |
|---|---|---|
| 1 | **Recovers the planted optimum's *value*** within tolerance | **Tolerance must be a fraction of instance depth** — see below |
| 2 | Beats non-adaptive designs and a sequential DoE pipeline | |
| 3 | Uncertainty estimates are calibrated, with error bars | |
| 4 | Extrapolation-driven over-prediction is detectable *selectively* | |

**Claim 1's tolerance is defined relative to depth.** State it as a fraction — e.g. *"within 25% of instance depth of the optimum value."* If tolerance exceeded depth, a boundary point would satisfy the claim and the claim would be vacuous.

**Claim 1 is about value, not location.** At d=6 with `Σw = 1`, moving a *single* coordinate from peak to boundary changes the response by roughly `w·δ ≈ 0.05` — about half a single-observation sigma at `σ_rel = 0.10`. Per-coordinate localization from individual observations is not possible at this SNR. You localize by pooling.

**On E4's framing.** An extrapolated stationary point outside the design region is a **textbook RSM pathology** (ridge analysis, Hoerl 1959; Draper 1963). **Do not claim discovery.** See Doc 2 §B.1.1.

---

## 2. The forward-compatibility contract

| # | Requirement | Why | Cost |
|---|---|---|---|
| 1 | **Ask/tell separation.** A separate `Evaluator` supplies outcomes. | Phase 2 swaps in a lookup table; Phase 3 a human. | Free |
| 2 | **Discrete candidate mode.** | **Phase 2 replay can only propose conditions in the published data.** | ~20 lines |
| 3 | **Search space in config, coded [0,1].** | Phase 2 digitizes coded figure levels. | Free |
| 4 | **Mixed parameter types in the schema.** | Phase 3 categorical medium, integer days. | Low |
| 5 | **Always pass `Yvar`**, imputed where unreplicated. | One `SingleTaskGP` can't mix likelihoods. **A modelling decision.** | Decision |
| 6 | **Serialize data + config + RNG state; refit on resume.** Not model weights. | Robust across BoTorch versions; the identical-trace test needs RNG state. | ~30 lines |
| 7 | **Metric identity on every row.** | CD31% by flow ≠ CD31 area by IF. | Free |
| 8 | **Constraint hooks in config.** | Phase 3 protein caps. **The Ogle failure was a constraint problem.** | ~20 lines |
| 9 | **`X_pending` tracking.** | Phase 3 asynchronous returns. | One argument |

**Outcome tensors are always `(n, m)`.**

```python
while budget_remaining:
    X = optimizer.ask(q)                    # identical in all three phases
    Y, Yvar = evaluator.evaluate(X)         # only this changes
    optimizer.tell(X, Y, Yvar)              # identical in all three phases
```

---

## 3. Compute

CPU only. Estimates below; pre-flight check 4 replaces them and must include the second noise level.

| Quantity | Estimate |
|---|---|
| One BO iteration | 3–5 s |
| One 48-evaluation run at q=4 | ~60 s |
| Full grid, single-threaded | 3–5 h |
| Full grid, 4–8 workers | under 1 h |

`OMP_NUM_THREADS=1` **before importing torch**, plus `torch.set_num_threads(1)` per worker.

---

## 4. The fake data

### 4.1 Search space

Canonical coded `[0,1]^d`. Physical units are labels only.

### 4.2 Construction

```
hᵢ(x) = x^{nᵢ} / (EC50ᵢ^{nᵢ} + x^{nᵢ})        activating, saturating
gᵢ(x) = 1 / (1 + (x / IC50ᵢ)^{nᵢ})            inhibitory
sᵢ = rᵢ^{nᵢ/2}                                 where rᵢ = IC50ᵢ/EC50ᵢ
f̃ᵢ(x) = hᵢ(x)·gᵢ(x)·((1+sᵢ)/sᵢ)²              peak-normalized: f̃ᵢ ∈ [0,1], peak = 1
```

```
f(x) = Σᵢ wᵢ·f̃ᵢ(xᵢ)  +  (1/k)·Σ_{pairs} βᵢⱼ·f̃ᵢ(xᵢ)·f̃ⱼ(xⱼ)          k = ⌈d/2⌉
```

**Observation model:** `y = f(x)·(1 + ε) + η`, `ε ~ N(0, σ_rel²)`, `η ~ N(0, σ_add²)`.

**Why normalize.** Unnormalized peak height spans ~0.34–0.92. With `Σwᵢ = 1`, equal-weight factors would differ nearly threefold in influence, and the non-separability and SNR checks would be measuring that confound.

**Why `1/k`.** Without it, interaction magnitude grows with `k`, so d=6 and d=8 differ in non-separability for reasons unrelated to dimension — and `f` could cross zero, which is unphysical.

### 4.3 The closed form

```
x*ᵢ = √(EC50ᵢ · IC50ᵢ)          exactly, by construction
```

With `a = EC50ⁿ`, `b = IC50ⁿ`, `u = xⁿ`, the factor is `f = ub/((a+u)(b+u))`, whose derivative numerator is `ab − u²`. So `u* = √(ab)`.

**With `β = 0` the function is separable, so the joint optimum is the vector of per-dimension peaks.** That gives an analytic target for the numerical search.

### 4.4 Sampling — invert for depth, don't reject for it

**Sample `(x*ᵢ, nᵢ, δᵢ)`. Derive `rᵢ`, then `EC50ᵢ = x*ᵢ/√rᵢ` and `IC50ᵢ = x*ᵢ·√rᵢ`.**

#### The inversion

Depth is `δ = 1 − f̃(1)`. Writing `V = x*^{−n}` and `c = 1 − δ`, the defining equation is quadratic in `s`:

```
V(1−c)·s²  +  [2V − c(1+V²)]·s  +  V(1−c)  =  0
```

The two roots multiply to 1 — a reciprocal pair. **Take the root exceeding 1** and set `rᵢ = s^{2/nᵢ}`.

*Verification case:* `x* = 0.4, n = 2, δ = 0.414` → `s = 3.9917`, recovering `r = 4`. Assert this in tests.

#### Feasibility — `δ` is bounded by `(x*, n)`

Not every `δ` is achievable. At low `x*` and low `n` the discriminant goes negative and no real root exists — a shallow-exponent factor peaking near the origin simply cannot decline 85% by `x = 1`.

**So sample `δ` relative to what's achievable:**

1. For each factor, compute **`δ_max(x*ᵢ, nᵢ)`** — the largest depth with a real root at `r ≤ r_cap`. A 1-D scan over `r ∈ [2, r_cap]` maximizing `δ`; trivial cost.
2. Sample `δᵢ = u·δ_max` with `u ~ U(0.55, 0.9)`.
3. If `δ_max` itself falls below the acceptance floor in §4.6, resample `(x*ᵢ, nᵢ)` for that factor.

This guarantees feasibility by construction and gives a **stated ensemble** — which rejection sampling would not.

#### Parameters

| Parameter | Draw | Justified by |
|---|---|---|
| `x*ᵢ` | U(0.25, 0.55) | **E2 depth.** High `x*` and measurable depth are not jointly achievable — see §4.5. |
| `nᵢ` | U(1.0, 3.0), shared across both arms | Gives the closed form in §4.3 |
| `δᵢ` | `u·δ_max(x*ᵢ, nᵢ)`, `u ~ U(0.55, 0.9)` | **Sampled, not derived.** Depth is the property Claim 1 depends on, so it is the quantity to control. |
| `rᵢ` | **Derived** by the inversion above | Removes the v5 artifact where `IC50 ~ U(2·EC50, 1.2)` made window width anti-correlated with EC50 by construction |
| `r_cap` | 8 | Bounds the search in the `δ_max` scan |
| `wᵢ` | U(0.75, 1.25), normalized to Σ = 1 | **Narrowed from U(0.5, 1.5).** Depth scales with `min wᵢ`, so a wide weight draw makes the acceptance floor hard to clear. |
| Interaction pairs `k` | `⌈d/2⌉` | Non-separability should scale with dimension |
| `βᵢⱼ` | U(−0.4, 0.6), scaled by `1/k` | Keeps interaction magnitude dimension-independent and `f` positive |
| `σ_rel` | **0.10 primary, 0.25 robustness** | Real assay CV exceeds 10%. **Both run on the same ensemble** — see §4.6. |
| `σ_add` | 0.01 | Noise floor |

### 4.5 The rule that keeps E2 and E4 from fighting

> **E4 needs the polynomial to extrapolate. E2 needs a measurable peak. If you satisfy E4 by pushing the peak toward the box edge, the peak flattens and E2 breaks.**
>
> **Move the training box relative to the peak. Never move the peak relative to the box.**

**Why.** With `v = x/x*`, the normalized response is `f̃(v) = v^n(1+s)²/((1+s·v^n)(s+v^n))`. Evaluate at the box edge, `v = 1/x*`.

At `x* = 0.8`, scanning the full stated ranges, **the deepest achievable decline is 8.2%** (at `n = 3, r = 2`) — under one sigma at `σ_rel = 0.10`. Raising `n` does not rescue it: since `r ≥ 2` forces `s = r^{n/2}` to grow with `n`, a larger exponent widens the plateau as fast as it sharpens the peak. **A 30% decline is not reachable at `x* = 0.8` at any `n` under `r ∈ [2, 8]`.**

At `x* = 0.4, n = 2, r = 4` the edge value is **0.586** — a 41% decline. Depth lives in the *low* `x*` regime.

The `κ·x*` sub-box (§6 E4a) resolves the tension: with training confined to `[0, κ·x*ᵢ]`, the turnover is **never in-sample at any `x*`**, so E4's mechanism is independent of peak location.

**If a future revision wants more extrapolation, lower κ. Do not raise `x*`.**

### 4.6 Instance acceptance — pooled, and noise-independent

**The v5 criterion was unsatisfiable.** With β=0 and peak normalization, `f(x*) = 1` and the boundary maximum is reached by moving one coordinate to 1 with the rest at their peaks, so

```
depth = minᵢ [ wᵢ · δᵢ ]
```

Since `Σwᵢ = 1`, `minᵢ wᵢ ≤ 1/d`, so **depth ≤ 1/d — 0.167 at d=6, 0.125 at d=8 — while the v5 threshold `3σ_rel·f(x*)` was 0.30.** No instance could pass at any draw. Generation would never terminate.

**The comparison must be against the pooled standard error**, not a single-observation sd. That is the same fact that makes Claim 1 about value rather than location.

**Acceptance criterion — one number, no `σ_rel` in it:**

```
minᵢ ( wᵢ · δᵢ )  ≥  0.045
```

0.045 is `3σ_rel/√n_budget` evaluated at the **primary** noise level (`σ_rel = 0.10`, `n = 48`) with a small margin. **It is then frozen as a structural property of the oracle.**

**Why noise-independent.** A `σ_rel`-dependent criterion means the ensemble changes with the noise level, so the 0.10-versus-0.25 comparison would mix a noise effect with an ensemble effect and neither could be attributed. At 0.25 the pooled threshold would be 0.108, demanding a materially different instance family.

**Generate one ensemble; run both noise levels on it.** Some instances will be unrecoverable at 0.25. **That is the robustness finding, not something to design away.**

**Other acceptance checks:**

| Check | Test |
|---|---|
| Positivity | `f > 0` across a dense Sobol sample of the box |
| Closed form | On a **constructed `β = 0` variant** of the accepted instance, the numerical optimum equals `√(EC50ᵢ·IC50ᵢ)` per dimension. *(Generated instances have `β ≠ 0`; build the variant explicitly for this check.)* |
| Non-separability | Coordinate-wise optimum ≠ joint optimum |

**Log the acceptance rate.** With `δ` sampled by inversion rather than rejection, it should be high; a low rate means the weight draw is too wide relative to the floor.

### 4.7 Output schema

```
instance_id, oracle_version, seed, dim, x_0 … x_{d-1}, y_true, y_observed, y_var
```

**`oracle_version` hashes the construction *and the acceptance parameters*.** Under any rejection sampling the seed→instance map depends on the acceptance rule, because rejections consume RNG draws — so changing a threshold without bumping the version makes the same `instance_id` denote a different landscape. That is exactly the silent-mixing failure this field exists to prevent, arriving through a door it wouldn't otherwise cover.

`in_subbox` is **not** in this schema — an E4 construct, derived at experiment level.

JSON sidecar: sampled `x*`, `n`, `δ`, `w`, `β`; derived `r`, EC50, IC50; `δ_max` per factor; cached optimum and value; acceptance results.

### 4.8 The returned `Yvar` must not leak the truth

Analytic variance `f(x)²σ_rel² + σ_add²` is a function of the **noiseless** value, from which `|f(x)|` is exactly recoverable.

**Default: the plug-in** `ŷ²σ_rel² + σ_add²`, from the observed value — what a lab computes.

**Known bias, pre-identified.** `E[y_obs²] = f²(1+σ_rel²) + σ_add²`, so the plug-in over-estimates by ~1% at `σ_rel = 0.10` and ~6% at 0.25, and a point that drew high noise gets a larger `Yvar` and is down-weighted. This happens in real labs, so it is the right default. **When E3 shows mild over-coverage at the higher noise level, this is the first candidate, not a bug.**

**Ablation:** the analytic version, as an upper bound under perfect noise knowledge.

---

## 5. The model

```python
covar_module = get_covar_module_with_dim_scaled_prior(
    ard_num_dims=d, use_rbf_kernel=False        # Matérn 5/2; default True → RBF
)
covar_module = ScaleKernel(covar_module)        # learned outputscale — primary

model = SingleTaskGP(
    train_X, train_Y, train_Yvar,
    covar_module=covar_module,
    input_transform=Normalize(d=d, bounds=space.bounds),
    outcome_transform=Standardize(m=m),
)
```

`qLogExpectedImprovement`. `optimize_acqf(num_restarts=10, raw_samples=512)`. Sobol initial design of `2d+2`.

**Outputscale is a config axis, learned primary.** Fixed at 1 with `Standardize` puts the far-field interval at ≈ ±1.96 × training-sd in raw units, and E4's sub-box sits where training sd is compressed.

### Three traps that fail silently — verified against source

1. **`use_rbf_kernel` defaults to `True`.**
2. **The function returns a bare kernel**; the primary config wraps it in `ScaleKernel`. **Write a defensive traversal helper.** Read the lengthscale constraint bound off the object.
3. **`Normalize` without `bounds=` learns from training-data min/max.**

---

## 6. The four experiments

### E1 — Correctness

Branin, Hartmann6, Ackley. 20 seeds each. Plus: on a `β = 0` Hill instance, BO converges toward `√(EC50·IC50)` per dimension. Losing to random on Hartmann6 means a bug.

### E2 — Sample efficiency

qLogEI vs **random, Sobol, LHS, and a sequential DoE pipeline.**

**The DoE arm — with a confirmation evaluation.**

```
Stage 1  two-level screening design + centre points        ~half of 47
Stage 2  CCD centred on the best stage-1 region            remainder of 47
Stage 3  fit second-order model, locate the stationary point
Stage 4  EVALUATE IT                                       1 run
```

**47 design runs plus 1 confirmation = 48.** Without stage 4 the arm's best-so-far is just its best design point and the pipeline's actual output never enters the regret curve. **Ogle evaluated TheO.**

> **This connects the two experiments for free.** The confirmation run *is* E4a, inside E2. If the DoE arm's confirmation lands outside its own design region and under-delivers, the Ogle failure reproduces in your benchmark **without being staged for it** — a stronger result than E4a in isolation.

**Scoped deliberately.** Reproducing Ogle's exact 23-run design is out of scope: `1 + 6 + C(6,2) = 22` is the two-factor-interaction parameter count in six factors, so it is likely a D-optimal custom design, and coordinate-exchange is real work. **Phase 2 is the definitive DoE comparison — there you implement nothing.**

**Ordering for static baselines.** A one-shot design has no regret *curve*; best-so-far is a step function set by arbitrary run order. **Randomize run order and average over orderings.**

Hill oracle at d ∈ {6, 8}. **10 instances × 5 seeds.** Budget 48.

**Budget convention, identical across methods.** d=6: 14 initial + 8×4 + one trailing q=2. d=8: 18 initial + 7×4 + one trailing q=2.

**The seed varies** the initial design draw and noise draws; the instance is separately seeded. **The initial design must be identical across methods for a given seed** — paired comparison at n=50 is the difference between significant and not.

**Report:** best-so-far and log₁₀ regret; median with IQR; **simple regret at budget and AUC over the post-initialization segment**, with bootstrapped CIs and paired tests.

### E3 — Calibration

**Prospective (primary), at two point sets** — BO-proposed points (decision-relevant, but coverage under a selection rule) and a fixed held-out Sobol set (domain-wide). **The gap between them is the informative quantity.**

**Leave-one-out (secondary).** `batch_cross_validation` with per-fold refitting. **Never `loo_cv` for a published number.** `observation_noise=False` is the default; pass `True` for coverage of measurements.

**Error bars are mandatory.** Coverage at 0.95 with n=48 has SE ≈ 3.1%. **Bootstrap at the instance level only** — resample instances with replacement and recompute from all their data. Points within a run are sequential BO proposals and are not exchangeable.

**CRPS has a closed form:** `σ[z(2Φ(z)−1) + 2φ(z) − 1/√π]`, `z = (y−μ)/σ`.

**State which σ.** Posterior predictive → coverage of measurements, primary. Latent → function coverage, diagnostic.

**Self-test:** fit the GP to a function generated *from* a GP.

### E4 — Detecting extrapolation-driven over-prediction

**d=6 only, `n_subbox = 48`.**

#### E4a — the measurement

Per instance, per κ ∈ {0.6, 0.7, 0.8, 0.9}:

1. **Sub-box `[0, κ·x*ᵢ]` per dimension, sampled by a CCD-family design** — a central composite design scaled into the sub-box.

   > **The design is not optional detail.** `(XᵀX)⁻¹` — hence the polynomial's prediction interval, which *is* the comparator in the discrimination test — depends entirely on it. A Sobol fill and a CCD give different interval widths at the same extrapolation distance. It is also a fairness question: an RSM practitioner would use a CCD, and the PI formula in step 5 is the formula for a designed experiment. Fitting to a space-filling sample and reporting the intervals as "what DoE gives you" is not what DoE gives you. **Use identical points for all four models.**

2. **Fit four models to identical data:** a **second-order polynomial** (primary), a **stepwise-reduced third-order polynomial** (descriptive only), the **GP**, and a **practitioner-form parametric model** (additive biphasic, no interactions, by NLS).

3. **Optimize all four over the same extended box** (the unit cube).

4. **Primary outcome: over-prediction at each model's constrained argmax over the extended box** — `predicted value − true value`. **Always defined, regardless of curvature.**

   > **Why this replaces "did the stationary point escape."** Within `[0, κ·x*]` you are on the rising arm, and for `n > 1` the Hill function is convex below its inflection. When `κ·x*` sits low the second-order fit has **positive** curvature, its stationary point is a *minimum*, and "did it escape the sub-box" is answering a question about a minimum. Stationary-point location and Hessian classification become **descriptive** — reported as a distribution, not as the headline.

5. **Prediction intervals**, second-order and GP only:
   - Polynomial: `ŷ ± t·σ̂·√(1 + x₀ᵀ(XᵀX)⁻¹x₀)`
   - GP: posterior predictive

**Why second-order is primary.** *Estimability:* second-order is 28 terms at d=6 (20 residual df at n=48) but 45 at d=8 (3 df — the interval balloons for reasons unrelated to extrapolation, making the polynomial look well-calibrated and collapsing the comparison). Full third-order is 84 and 165 terms — rank-deficient at n=48, so `(XᵀX)⁻¹` doesn't exist. *Literature:* canonical and ridge analysis are second-order techniques. *Post-selection inference:* a stepwise model's interval is anticonservative — too narrow for **selection** reasons — which is fatal when "the interval is too narrow" is the finding. **Report the stepwise model descriptively; omit its interval entirely.**

**Parametric comparator: practitioner-form only.** An oracle-form fit is matched by construction and tells you nothing. **Log NLS convergence failures** rather than dropping instances.

#### The discrimination test — the actual novel claim

Note this **never touches the stationary point.** It is Spearman ρ between scorers and `|polynomial error|` over a Sobol candidate set. The stationary point is the narrative hook; this is the measurement.

**Candidate set:** a Sobol sample of N points over the extended box, per instance.

**Three scorers:**

| Scorer | What it is |
|---|---|
| GP predictive sd | The claim |
| Second-order PI width | The DoE comparator |
| **Nearest-neighbour distance to the training set** | **The model-free null** |

**Nearest-neighbour, not centroid distance.** It is the sharper null — it is what GP predictive sd actually approximates, whereas centroid distance ignores design geometry entirely. If the GP has an edge it comes from ARD lengthscales making its "distance" anisotropic, so an **isotropic** null is the right thing to beat.

**Report the scorer–scorer rank correlation matrix first.** With the sub-box in a corner and candidates over the unit cube, all three may be monotone in the same underlying quantity — ρ > 0.95 among scorers would mean there is no headroom for the comparison to show anything either way. **The reader needs to see the headroom before seeing the result.**

**Primary: Spearman ρ** against `|polynomial error|`. **Secondary: AUC** at a pre-registered τ. **CIs by instance-level bootstrap.**

#### E4b — Design boundary (reported, not claimed)

A variant where one factor's true optimum lies below the lower bound — the fibronectin case, where TheO sat at the FN floor of 22 µg/mL and the true best required FN = 0.

**Report honestly.** The polynomial's coefficient in that dimension will be significantly negative and *will* signal "lower is better" — which is what Hall/Ogle observed and acted on. **Not a mechanism where the GP wins.** A design-space problem, not a modelling-uncertainty problem.

**Claim E4a. Report E4b.**

---

## 7. Pre-flight — before Build Step 2

1. **Over-prediction versus κ.** Across 10 instances, κ ∈ {0.6, 0.7, 0.8, 0.9}: the second-order model's over-prediction at its constrained argmax, **plus the Hessian classification distribution** (max / min / saddle / ridge). A bare escape rate would hide that low κ produces minima rather than escaped maxima.
2. **Inversion and acceptance.** Does the `(x*, n, δ) → r` inversion return `s = 3.9917` for `x* = 0.4, n = 2, δ = 0.414`? Does the closed form hold on the `β = 0` variant? **What is the instance acceptance rate**, and what is the achieved distribution of `δ_max`?
3. **API signatures.** `use_rbf_kernel`; bare-kernel return; `Normalize` bounds behaviour; discrete-candidate function name; lengthscale constraint bound. **And: what does `observation_noise=True` do under a fixed-noise likelihood at an unevaluated input?** Contract item 5 mandates supplied `Yvar`, and E3's primary metric is posterior-predictive coverage at points not yet evaluated — where noise is undefined without a noise model. It may raise, or **silently substitute a heuristic, in which case the headline calibration number uses a noise level you didn't choose.** Clean resolution: supply prediction-point noise yourself from the plug-in formula and say so in methods.
4. **Wall-clock**, including the second noise level.

---

## 8. Repo layout

```
bo-endothelial/
├── requirements.txt          # exact pins
├── src/boec/
│   ├── space.py              # SearchSpace: coded bounds, types, constraint hooks
│   ├── oracles.py            # Oracle ABC, test functions, biphasic HillOracle + inversion
│   ├── evaluators.py         # Evaluator ABC, SyntheticEvaluator
│   ├── surrogate.py          # build_gp, kernel traversal helper
│   ├── rsm.py                # 2nd-order + stepwise 3rd-order, PIs, Hessian, ridge analysis
│   ├── designs.py            # CCD, screening designs, sub-box scaling
│   ├── parametric.py         # practitioner-form biphasic NLS
│   ├── optimizers.py         # qLogEI (continuous + discrete), baselines, sequential DoE
│   ├── campaign.py           # ask/tell, X_pending, serializable (data+config+RNG)
│   ├── metrics.py            # regret, AUC, coverage, closed-form CRPS, Spearman
│   ├── diagnostics.py        # batch_cross_validation, reliability, instance bootstrap
│   └── runner.py             # resumable grid runner
├── configs/ · scripts/ · data/oracles/ · results/ · tests/
```

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
| **`Yvar` units and shape** | Variance, not sd. **The classic fixed-noise GP bug.** |
| **`Yvar` in raw outcome units** | `Standardize` handles scaling. Separate bug from variance-vs-sd. |
| **Oracle noise** | Empirical variance of repeated `evaluate` matches the **analytic** variance. *(The plug-in varies across repeats — check its bias separately against the closed form.)* |
| **`Standardize` inverse-transforms variance** | Not just the mean |
| **Transform applied in eval mode** | `model.posterior(X_raw)` matches the manually-normalized path |
| **Kernel identity via traversal helper** | Not `isinstance(...)` — breaks under `ScaleKernel` |
| **Lengthscale bound read, not hardcoded** | From the constraint object |
| **CV refit** | Per-fold hyperparameters actually **differ** |
| **Sub-box CCD full rank** | For second-order at the chosen `n_subbox` |
| **Identical design across models** | All four E4 models fit the same points |
| **DoE arm spends 48** | 47 design + 1 confirmation, and the confirmation enters the regret curve |
| **Evaluator can't leak `y_true`** | The whole regret story depends on it |
| **Paired initial design** | Identical across methods for a given seed |
| **Polynomial correctness** | Second-order recovers known coefficients and prediction variance on a synthetic quadratic |
| **Hessian classification** | Correct labels on constructed max / min / saddle / ridge cases |
| Discrete mode | Every proposal comes from the candidate set |
| Serialization round-trip | Data + config + RNG resumes to an identical trace |
| Non-separability | Coordinate-wise optimum differs from joint |
| Acquisition | qLogEI proposes near the true max on a 1-D toy |
| Shape contract | Outcomes are `(n, m)` everywhere |
| Resumability | Re-running a completed config skips it |
| Smoke | Branin, 20 iterations, regret decreases |

---

## 10. Claude Code build prompt

*Copy from here down.*

---

### Project

Build a Bayesian optimization framework in Python for a research paper on optimizing stem-cell differentiation protocols. **Synthetic data only.** A control experiment proving the optimizer is correct and well-calibrated on data where the answer is known, before application to real data in later stages that are out of scope.

Structure it so those stages are drop-in additions. "Forward compatibility" is a hard requirement.

### The four claims

1. Recovers the planted optimum's **value** within a tolerance stated as a fraction of instance depth
2. More sample-efficient than random, Sobol, LHS, and a sequential DoE pipeline
3. Uncertainty estimates are calibrated, with instance-level bootstrap error bars
4. Extrapolation-driven over-prediction is detectable from GP predictive variance **more selectively than from nearest-neighbour distance to the training set** — a model-free null that must be beaten

### Forward compatibility — hard requirements

1. **Ask/tell separation.** 2. **Discrete candidate mode** — confirm the BoTorch function name on the installed version. 3. **Search space in config, coded [0,1].** 4. **Continuous, integer, categorical in the schema.** 5. **Always pass `Yvar`**, imputed where unreplicated. 6. **Serialize data + config + RNG state**; refit on resume, not model weights. 7. **Metric name, units, protocol version on every row.** 8. **Constraint hooks in config.** 9. **`X_pending` tracking.**

### Environment

CPU only. Python ≥3.11, torch ≥2.2, gpytorch ≥1.15.1, botorch 0.18.x, statsmodels, scipy, pandas, pyarrow, pytest. **Exact pins.** **Check installed API signatures and report anything differing from this prompt.** `OMP_NUM_THREADS=1` **before importing torch**, plus `torch.set_num_threads(1)` per worker.

### The oracle — sample the peak and the depth, derive everything else

Sample `x*ᵢ ~ U(0.25, 0.55)` and `nᵢ ~ U(1,3)`. For each factor compute `δ_max(x*ᵢ, nᵢ)` by scanning `r ∈ [2,8]`, then sample `δᵢ = u·δ_max` with `u ~ U(0.55, 0.9)`.

**Derive `rᵢ` by inverting the depth equation.** With `V = x*^{−n}`, `c = 1−δ`:

```
V(1−c)·s²  +  [2V − c(1+V²)]·s  +  V(1−c)  =  0
```

Roots multiply to 1; **take the root exceeding 1**; `r = s^{2/n}`. Then `EC50 = x*/√r`, `IC50 = x*·√r`. Assert the verification case `(0.4, 2, 0.414) → s = 3.9917`.

Peak-normalize `f̃ᵢ = hᵢgᵢ((1+sᵢ)/sᵢ)²`. Combine `f = Σwᵢf̃ᵢ + (1/k)Σβᵢⱼf̃ᵢf̃ⱼ`, `k = ⌈d/2⌉`, `wᵢ ~ U(0.75,1.25)` normalized, `βᵢⱼ ~ U(−0.4,0.6)`.

**Acceptance: `minᵢ wᵢδᵢ ≥ 0.045`, positivity, closed form on a constructed `β=0` variant, non-separability.** The acceptance floor is **noise-independent and frozen** — one ensemble serves both noise levels. Hash acceptance parameters into `oracle_version`.

**Critical invariant:** `x*` is chosen for E2's depth. E4's mechanism comes from the sub-box `[0, κ·x*ᵢ]`. **Never raise `x*` to increase extrapolation — lower κ.** High `x*` and measurable depth are not jointly achievable.

### Model configuration

```python
covar_module = ScaleKernel(get_covar_module_with_dim_scaled_prior(
    ard_num_dims=d, use_rbf_kernel=False))
model = SingleTaskGP(train_X, train_Y, train_Yvar,
    covar_module=covar_module,
    input_transform=Normalize(d=d, bounds=space.bounds),
    outcome_transform=Standardize(m=m))
```

**Three verified traps:** `use_rbf_kernel` defaults to `True`; the function returns a **bare kernel** (write a defensive traversal helper — the primary config wraps it in `ScaleKernel`); `Normalize` without `bounds=` learns from training data.

**Deprecated:** `AxClient` · `FixedNoiseGP` · `HeteroskedasticSingleTaskGP` · `qExpectedImprovement` without `Log`.

### Build steps — stop and report at each boundary

**Build Step 1 — Pre-flight.** (a) second-order over-prediction at its constrained argmax versus κ ∈ {0.6,0.7,0.8,0.9}, **with the Hessian classification distribution**; (b) inversion verification case, closed-form check on the `β=0` variant, instance acceptance rate, `δ_max` distribution; (c) API signatures **including what `observation_noise=True` does under a fixed-noise likelihood at an unevaluated input**; (d) wall-clock including the second noise level. **Report all four before proceeding.**

**Build Step 2 — Space, oracles, evaluators.** `SearchSpace` with constraint hooks. Biphasic `HillOracle` with the inversion, `δ_max` scan, acceptance checks, `instance_id` hashing (dim, seed, oracle_version-including-acceptance-params), cached optima, JSON sidecars. Plug-in `Yvar` default, analytic ablation. `SyntheticEvaluator`. `generate_oracles.py`.

**Build Step 3 — Surrogate, RSM, designs, parametric, diagnostics.** `build_gp` with traversal helper. `rsm.py`: second-order with closed-form PIs, Hessian classification, ridge-analysis fallback; stepwise third-order **descriptive only, no interval**. `designs.py`: CCD and screening designs, sub-box scaling. `parametric.py`: practitioner-form biphasic NLS logging convergence failures. `batch_cross_validation` with per-fold refit. Coverage, reliability, **closed-form CRPS**, **instance-level bootstrap**.

**Build Step 4 — Optimizers and loop.** qLogEI continuous and discrete. Random, Sobol, LHS, **sequential DoE pipeline with 47 design runs + 1 confirmation evaluation that enters the regret curve**. Randomized ordering for static baselines. Campaign loop with `X_pending`, serializable state, per-round predictive logging at **both** proposed points and a fixed held-out Sobol set.

**Build Step 5 — Resumable runner.** Grid → parquet with JSON sidecars carrying resolved config and library versions.

**Build Step 6 — Experiments E1–E4.** E4 at **d=6 only, `n_subbox = 48`, CCD sub-box design, identical points for all four models**, κ swept. Discrimination test with three scorers including **nearest-neighbour distance**; **report the scorer–scorer rank correlation matrix first**.

**Build Step 7 — Figures.** Convergence with IQR, reliability with bootstrap intervals, over-prediction versus κ, Hessian classification distribution, scorer correlation matrix, discrimination across all three scorers.

### Style

Type hints. Docstrings stating tensor shapes. No global state. Fail loudly on shape mismatches. Comment every deliberate override of a BoTorch default. **Read by biologists — clarity over cleverness.**

### Ask rather than assume

Installed API signatures differing from this prompt · screening design choice for the sequential DoE pipeline · CCD face-centred versus rotatable inside the sub-box · stepwise selection criterion for the descriptive third-order fit.

---

## 11. When it misbehaves

**Generation never terminates** → the acceptance floor is unreachable. Check `minᵢ wᵢδᵢ` against 0.045 directly, and check that `δ` is being sampled relative to `δ_max` rather than uniformly. **This is exactly how v5 failed.**

**The GP fits badly:**
1. **Transforms attached, with explicit bounds?** By far the most common cause.
2. **Kernel actually Matérn?** Through the traversal helper.
3. **Lengthscales at a bound?** Read the constraint's bound off the object.
4. **Fewer than ~2d points?** Hyperparameters are prior samples.
5. **Is `Yvar` variance or sd? In raw outcome units?** Two separate bugs, both producing plausible-looking wrong calibration.

> "Is `model.likelihood.noise` large?" applies **only on the `Yvar=None` path.** Contract item 5 mandates supplied `Yvar`, so the likelihood is fixed-noise.

**Mild over-coverage at the higher noise level** → the plug-in `Yvar` bias (§4.8), pre-identified, not a bug.

**Over-prediction near zero at all κ** → the sub-box isn't excluding the turnover. Check `x*` is used per dimension, not a fixed box.

**All three scorers rank-correlate above 0.95** → no headroom; the discrimination test cannot show anything either way. Report it as such rather than reporting a null result.

**Over-exploitation** → overconfident GP, lengthscales too short. **Over-exploration** → lengthscales too long, or supplied `Yvar` too large.

**Batch proposals cluster** → not joint q-acquisition, or `num_restarts`/`raw_samples` too low.

**Calibration below the diagonal** = overconfident = dangerous. Check CRPS too — uniformly wide intervals score perfectly on coverage and terribly on CRPS.

**Knobs ranked:**
1. Normalization with explicit bounds, and output standardization
2. `Yvar` correctness — units, shape, leakage
3. Seed data relative to `d`
4. Outputscale learned vs fixed
5. Kernel and lengthscale priors
6. Acquisition; batch size; `num_restarts`/`raw_samples`
