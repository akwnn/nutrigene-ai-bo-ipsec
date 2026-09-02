# PERSON A — WORK PACKAGE
## Data lane · Experiment 2 (efficiency) · Experiment 3 (calibration)

**Read `team_build_plan.md` first** for gates, shared code, and the rules for working in parallel.
**`phase1_build.md` is the technical authority.** This document says what's yours and flags the traps in your lane; it does not replace the spec.

---

## What you own

| Module | Lifetime | Notes |
|---|---|---|
| `space.py` | **Long-lived** — Phases 2 and 3 depend on it | Second reader required |
| `oracles.py` | **Long-lived** | Second reader required |
| `evaluators.py` | **Long-lived** | Second reader required |
| `designs.py` | Phase 1 only | **B wrote working copy; confirm ownership** |
| `diagnostics.py` | Phase 1 only | |
| Instance generation and caching | **Long-lived** | |
| E2 — sample efficiency | | |
| E3 — calibration | | |

**You import from B:** the over-prediction metric in `metrics.py`. Do not reimplement it — the whole point is that E2's confirmation run and E4a produce the same number.

---

## Gate 1 — your pre-flight checks

### PF1 — over-prediction versus κ

> **Half of this is already built. Do not reimplement it.**
>
> PF1 needs a second-order fit, a constrained argmax, Hessian classification, and the over-prediction metric — all specced as B's Gate-3 work, which made PF1 unrunnable at Gate 1. **B has built them for real** (not as throwaways) precisely so this check is not blocked:
>
> - `boec.metrics.over_prediction_at_constrained_argmax(predict, truth, bounds, seed=...)` → returns `.over_prediction`, `.x_argmax`, `.y_predicted`, `.y_true`. **This is the shared function §4 requires — import it, do not write your own.** Deterministic given `seed`, so you and B get the same number from the same inputs.
> - `boec.rsm.fit_second_order(X, Y)` → `.predict`, `.prediction_interval`, `.stationary_point(bounds)`.
> - `boec.rsm.classify_stationary_point(...)` → `.kind` in `{maximum, minimum, saddle, ridge}`, the four categories the distribution below needs.
>
> 25 tests on metrics+rsm at the time of the first handoff note; the suite is now larger (see `person_b_spec.md`). **What is still missing for PF1: only the oracle (yours).** The CCD sub-box design is already in `boec.designs` (face-centred fractional CCD, 32+12+4=48). **Ownership confirmation is still open** — B wrote it because PF1 was otherwise blocked; say keep / replace / co-own in one sentence (`OPEN-QUESTIONS.md` Q2). Composition: at d=6 with `n_subbox = 48` a full 2⁶ core is 64 runs before axials, so it is fractional — **32 (2⁶⁻¹, resolution VI) + 12 axial + 4 centre = 48**, matching the spec's own "28 terms, 20 residual df".

Across 10 instances, for κ ∈ {0.6, 0.7, 0.8, 0.9}: fit a second-order polynomial to a CCD inside the sub-box `[0, κ·x*ᵢ]`, find its constrained argmax over the unit cube, and record over-prediction against the true oracle value.

**Pass the noiseless oracle value as `truth`**, not a noisy draw — otherwise over-prediction picks up observation noise and the distribution widens for a reason unrelated to extrapolation.

**Report the Hessian classification distribution alongside it** — maximum, minimum, saddle, ridge.

**Why the distribution matters.** Inside `[0, κ·x*]` you're on the rising arm, and for `n > 1` the Hill function is convex below its inflection. At low κ the fit will have *positive* curvature and its stationary point will be a **minimum**. A bare over-prediction number hides that, and the two cases mean different things.

**This check decides whether B has a lane.** If over-prediction is near zero at every κ, E4a has no mechanism. Read the results with B before either of you builds.

### PF2 — inversion and acceptance

Four numbers:

1. Does `(x* = 0.4, n = 2, δ = 0.414)` return `s = 3.9917`, recovering `r = 4`?
2. On a constructed `β = 0` variant, does the numerical optimum equal `√(EC50ᵢ · IC50ᵢ)` per dimension?
3. What is the **instance acceptance rate** under `minᵢ wᵢδᵢ ≥ 0.045`?
4. What is the achieved distribution of `δ_max` across factors?

**If the acceptance rate is low**, the weight draw is too wide relative to the floor, or `δ` isn't being sampled relative to `δ_max`. Tell B — it changes the ensemble E4 runs on.

---

## Gate 2 — spine

### Ship the standard test functions first

Branin, Hartmann6, Ackley wrappers **before** the biphasic oracle. B builds the entire campaign loop against them; the real oracle swaps in later.

**This is a deliberate contract test.** If the swap isn't clean, the forward-compatibility design was never real, and you want that failure now rather than in Phase 2 when a lookup table has to swap in for the same interface.

### `space.py`

`SearchSpace` from YAML: coded `[0,1]` bounds, names, units, and types (continuous, integer, categorical — only continuous is used in Phase 1, but the schema must support all three for Phase 3).

**Constraint hooks.** Thread `equality_constraints`, `inequality_constraints`, `nonlinear_inequality_constraints`, and `fixed_features_list` through config to `optimize_acqf`. Phase 3 will have protein caps and plate arithmetic, and retrofitting these changes B's optimizer signature everywhere.

### `oracles.py` — the biphasic oracle

**Sample `(x*ᵢ, nᵢ, δᵢ)`. Derive `rᵢ` by inversion. Then `EC50ᵢ = x*ᵢ/√rᵢ`, `IC50ᵢ = x*ᵢ·√rᵢ`.**

The depth inversion, with `V = x*^{−n}` and `c = 1 − δ`:

```
V(1−c)·s²  +  [2V − c(1+V²)]·s  +  V(1−c)  =  0
```

Roots multiply to 1. **Take the root exceeding 1**, then `r = s^{2/n}`.

**Pair on this with B.** You implement it from the quadratic; B implements it independently from a numerical root-find on `δ(r)`. Agree on random draws and check they match. One verification case is thin cover for math that voids every downstream number.

**Feasibility.** Not every `δ` is achievable — at low `x*` and low `n` the discriminant goes negative. Compute `δ_max(x*ᵢ, nᵢ)` by scanning `r ∈ [2, 8]`, then sample `δᵢ = u·δ_max` with `u ~ U(0.55, 0.9)`.

**Peak normalization** — `f̃ᵢ = hᵢ·gᵢ·((1+sᵢ)/sᵢ)²`, peaking at exactly 1. Without it, peak heights span a 2.7× range and equal weights don't mean equal influence.

**Interaction scaling** — `1/k` with `k = ⌈d/2⌉`. Without it, interaction magnitude grows with pair count so d=6 and d=8 differ for reasons unrelated to dimension, and `f` can cross zero.

**Acceptance:** `minᵢ wᵢδᵢ ≥ 0.045`, positivity across a dense Sobol sample, the closed-form check on a `β = 0` variant, and non-separability. **The floor is noise-independent and frozen** — one ensemble serves both noise levels.

**`oracle_version` hashes the construction *and the acceptance parameters*.** Under any rejection sampling the seed→instance map depends on the acceptance rule, since rejections consume RNG draws. Change a threshold without a version bump and the same `instance_id` denotes a different landscape.

### `evaluators.py`

`Evaluator` ABC plus `SyntheticEvaluator`. The ABC matters more than the implementation — Phase 2 swaps in a lookup table and Phase 3 a human, against this same interface.

**Test that the evaluator cannot leak `y_true`.** The entire regret story depends on it.

### The `Yvar` you return

**Default: the plug-in estimate** `ŷ²σ_rel² + σ_add²`, computed from the *observed* value.

**Not the analytic variance.** That's `f(x)²σ_rel² + σ_add²` — a function of the noiseless value, from which `|f(x)|` is exactly recoverable. Returning it hands the model the truth at every training point, which corrupts E3 specifically. It also doesn't transfer: Phase 2 has no variance and Phase 3 has replicate SEM.

Keep the analytic version behind an ablation flag, as an upper bound on calibration under perfect noise knowledge.

**Known bias, so you don't debug it later.** `E[y_obs²] = f²(1+σ_rel²) + σ_add²`, so the plug-in over-estimates by roughly 1% at `σ_rel = 0.10` and 6% at 0.25 — and a point that drew high noise gets a larger `Yvar` and is down-weighted. This happens in real labs, so it's the right default. **If B's or your calibration shows mild over-coverage at the higher noise level, this is the first candidate.**

---

## Gate 3 — your experiments

### `designs.py` — B already wrote a working version; confirm ownership

Specced as yours. **B shipped `boec.designs` (CCD face-centred and rotatable, screening designs, sub-box scaling, 28 tests) because PF1 could not run without it.**

**B's E4 sub-box uses this.** If you need a different variant, change it in place or ask B — do not maintain two copies.

**One sentence from you:** keep B's, replace with yours, or co-own with A as second reader. Until then, treat the file on disk as the shared source.

**The design is not a detail on B's side.** `(XᵀX)⁻¹` determines the polynomial's prediction interval, which is the comparator in B's discrimination test. A space-filling sample and a CCD give different interval widths at the same extrapolation distance.

### E2 — sample efficiency

qLogEI versus random, Sobol, LHS, and a **sequential DoE pipeline**.

```
Stage 1  two-level screening design + centre points        ~half of 47
Stage 2  CCD centred on the best stage-1 region            remainder of 47
Stage 3  fit second-order model, locate the stationary point
Stage 4  EVALUATE IT                                       1 run
```

**47 design runs plus 1 confirmation = 48.**

**Stage 4 is not optional.** Without it the arm's best-so-far is just its best design point and the pipeline's actual output never enters the regret curve. The published study evaluated its predicted optimum.

> **Your confirmation run is E4a, from the other side.** If it lands outside its own design region and under-delivers, the published failure mode reproduces in the benchmark without being staged for it — a stronger result than E4a in isolation. **Use B's over-prediction metric from `metrics.py`** so the two views produce the same number.

**Fairness, enforced in your harness:**

- Identical total budget for every method
- **The initial design must be identical across methods for a given seed.** Paired comparison at n=50 is the difference between a significant and non-significant result. Write a test for it.
- No per-method tuning — including qLogEI. Tuning your own method while leaving baselines at defaults is among the most frequently cited objections in this literature.
- **Randomize run order for static baselines and average over orderings.** A one-shot design has no regret *curve*; best-so-far is a step function determined by arbitrary run order, so AUC over it is otherwise meaningless.

**Budget convention.** d=6: 14 initial + 8 batches of 4 + one trailing batch of 2. d=8: 18 initial + 7 batches of 4 + one trailing batch of 2.

**Reporting.** Best-so-far and log₁₀ regret; median with interquartile bands; **simple regret at budget and AUC over the post-initialization segment only** — computing AUC from evaluation 1 includes the shared initial design and dilutes the between-method difference.

**Grid:** 10 instances × 5 seeds, d ∈ {6, 8}. Five seeds on ten landscapes generalizes better than fifty on one, because across-landscape variance is usually larger.

**d=12 is a capability test, not an experiment.** `2d+2 = 26` of 48 leaves 22 adaptive evaluations.

### E3 — calibration

**This is yours deliberately.** B owns the GP; you writing its calibration diagnostics means two people understand the model that carries into Phases 2 and 3.

**Prospective calibration is primary, at two point sets.** Each round, log the GP's predictive distribution *before* evaluating:

- **at BO-proposed points** — decision-relevant, but this is coverage *under a selection rule*, since acquisition deliberately targets high-mean and high-variance regions
- **at a fixed held-out Sobol set** — domain-wide, no selection effect

Two lines of extra code. **The gap between them is itself informative** and should be reported.

**Leave-one-out is secondary.** Use `batch_cross_validation`, which refits hyperparameters per fold.

> **Never use `loo_cv` for a published number.** Its documentation states it does not refit the model to each fold and keeps hyperparameters fixed as a fast approximation. Used naively, the held-out point has already influenced the model and coverage comes out optimistically inflated. **Assert in a test that per-fold hyperparameters actually differ** — "refit was called" is not the invariant.

**Watch the noise flag.** `batch_cross_validation(..., observation_noise=False)` is the default, giving **latent** coverage. Pass `True` for coverage of what a lab measures — the primary metric.

> ### ⚠️ B's PF3 answer — read before finalizing the metric. It is not good news.
>
> **`observation_noise=True` does not do what you want.** Under the fixed-noise likelihood that contract item 5 mandates, BoTorch substitutes **`mean(train_Yvar)`** at any point without supplied noise and applies that flat value everywhere. No warning, no error. Source: `botorch/models/gpytorch.py:532`, carrying the comment `# Use the mean of the previous noise values (TODO: be smarter here).` Confirmed to be the mean rather than the median by planting an outlier in `train_Yvar`. `batch_cross_validation(observation_noise=True)` inherits the same path.
>
> **Your E3 headline number sits exactly here** — posterior-predictive coverage at points not yet evaluated. Left alone it is computed against a flat averaged noise level rather than the plug-in variance the oracle implies at each point.
>
> **What to do.** Supply the noise yourself: `posterior()` accepts a **tensor** for `observation_noise` and honours it per-point. Compute the plug-in variance at the query point and pass it. State this in methods.
>
> **And the trap on top of the fix.** The tensor must be in **standardized** units, while `train_Yvar` is in **raw** units — the noise is applied before `Standardize` untransforms the posterior. Passing raw plug-in variance was wrong by **161×** in B's test case. Divide by `outcome_transform.stdvs**2` first. The factor depends on the training data, so it differs per fit and per CV fold. **Write the round-trip assertion** — this is the same family as the two `Yvar` traps already in your lane's table below, and it fails just as silently.
>
> Full write-up and reproduction: `preflight-findings.md`, `scripts/preflight_pf3.py`.

**Error bars are mandatory.** Coverage at nominal 0.95 with n=48 has SE ≈ 3.1%, so 95% and 89% are indistinguishable in a single run.

**Bootstrap at the instance level only.** Resample instances with replacement and recompute from all their data. Points within a run are sequential BO proposals and are **not exchangeable**, so resampling them is invalid.

**CRPS has a closed form** for a Gaussian predictive: `σ[z(2Φ(z)−1) + 2φ(z) − 1/√π]` with `z = (y−μ)/σ`. Don't sample it.

**Self-test:** fit the GP to a function generated *from* a GP, where coverage should be near-perfect by construction. If it isn't, the bug is in the code.

---

## Traps in your lane

| Trap | Consequence |
|---|---|
| Returning analytic `Yvar` instead of the plug-in | Leaks `\|f(x)\|` at every training point; corrupts E3 |
| `Yvar` as standard deviation instead of variance | **The classic fixed-noise GP bug.** Plausible-looking, systematically wrong calibration. Test against an analytic case. |
| `Yvar` not in raw outcome units | Separate bug from the above — `Standardize` handles the scaling |
| Using `loo_cv` for a published number | Inflates the headline calibration number |
| Initial designs not paired across methods | Turns a significant E2 result into a non-significant one |
| AUC computed from evaluation 1 | Dilutes the between-method difference with shared initial data |
| Bootstrapping points within a run | Invalid — sequential proposals aren't exchangeable |
| `in_subbox` in the oracle schema | It's an E4 construct, derived at experiment level — not a property of the instance |

---

## The invariant you enforce

> **Move the training box relative to the peak. Never move the peak relative to the box.**

**You own the oracle.** If B's over-prediction rate comes back too low, the fix is **lower κ**, not raising `x*`.

At `x* = 0.8` the deepest achievable decline across the stated ranges is 8.2% — under one sigma at the primary noise level. High peak position and measurable depth are not jointly achievable, so raising `x*` to help E4 would silently break E2.

**If B asks for more extrapolation, that's a joint decision** made once — not a week of quiet parameter adjustment on either side.

---

## Definition of done

**Long-lived modules** (`space`, `oracles`, `evaluators`): tests pass **and B can explain them back**. Not a review checkbox — B narrates what the module does and why. If B can't, it isn't done.

If the internship doesn't extend, whoever stays runs Phases 2 and 3 alone. Phase 2 swaps a lookup table into your `Evaluator` interface; Phase 3 swaps in a human writing a CSV. Neither works if only one of you understands the oracle.
