# PERSON B — WORK PACKAGE
## Loop lane · Experiment 4 (extrapolation detection)

**Read `team_build_plan.md` first** for gates, shared code, and the rules for working in parallel.
**`phase1_build.md` is the technical authority.** This document says what's yours and flags the traps in your lane; it does not replace the spec.

---

## What you own

| Module | Lifetime | Notes |
|---|---|---|
| `surrogate.py` | **Long-lived** — Phases 2 and 3 depend on it | Second reader required |
| `campaign.py` | **Long-lived** | Second reader required |
| `optimizers.py` | **Long-lived** | Second reader required |
| `runner.py` | **Long-lived** | Second reader required |
| `metrics.py` | **Long-lived** | **A imports the over-prediction metric** |
| `designs.py` | Phase 1 only | ✅ Built by B (28 tests); A ownership call open |

**You import from A:** nothing hard-blocking for machinery now. Formally, `designs.py` was A's to write — B already shipped a working version; get A's one-sentence call (keep / replace / co-own). If you need a design variant that does not exist yet, **ask** — don't fork a second copy.

**A imports from you:** the over-prediction metric. A's DoE confirmation run and your E4a must call the **identical function**. If you each implement it, you get two numbers that disagree and no way to tell which is right.

---

## Why you own E4 end to end

The obvious split — one person owns the oracle and response-surface model, the other owns the GP — would put E4 across the handoff. E4 compares GP predictive standard deviation against polynomial prediction-interval width, so the paper's main result would become the one thing neither person can debug alone.

**So you own all of it:** the response-surface model, the parametric comparator, and the discrimination test. A hits the same phenomenon from the other side through the DoE confirmation run in E2, using your shared metric.

---

## Status — updated 2026-08-07 (Person B machinery complete)

| Item | State |
|---|---|
| PF3 — API signatures | ✅ **DONE.** Two silent failures found, both landing in A's lane |
| PF4 — wall-clock | ✅ **DONE.** ~10× cheaper than estimated; grid need not shrink |
| `metrics.py` — over-prediction metric | ✅ **BUILT.** 10 tests. **A imports this** |
| `rsm.py` — 2nd-order fit, PIs, Hessian; stepwise 3rd-order descriptive | ✅ **BUILT.** 33 tests (15 + 18) |
| `designs.py` — CCD / screening / sub-box | ✅ **BUILT by B.** 28 tests. Face-centred default. **⚠️ Ownership confirmation still needed from A** |
| `surrogate.py` | ✅ **BUILT.** 24 tests |
| `optimizers.py` — qLogEI continuous + discrete, baselines | ✅ **BUILT.** 30 tests |
| `campaign.py` | ✅ **BUILT.** 27 tests |
| `parametric.py` | ✅ **BUILT.** 15 tests |
| `discrimination.py` — E4 scorers / discrimination | ✅ **BUILT.** 27 tests |
| `runner.py` | ✅ **BUILT.** 24 tests |
| E4 pre-registration — the two blank numbers | ✅ **LOCKED.** `configs/experiment/e4.yaml` |
| E4 *results* | ⬜ gated on A's oracle |
| Total tests | **218 passing** |

**Why `rsm.py`, `metrics.py`, and `designs.py` were pulled forward out of Gate 3:** A's PF1 cannot run without them, and PF1 is the check that decides whether your lane exists. On a 14-day horizon nothing can be written twice, so they were built properly rather than as throwaways. Full write-up in `preflight-findings.md`. **PF1 is now blocked only on A's oracle** — the CCD and RSM pieces exist.

**You import from A (when it lands):** formal ownership/sign-off on `designs.py` if A wants to take it; otherwise keep B's. Spec originally said ask — don't fork; the fork already happened with working tests attached. See `OPEN-QUESTIONS.md` Q2.

**Two numbers the spec left blank, now pre-registered** (in git, dated, before any result existed):
- **Candidate set: 512 Sobol points per instance.** Compute is not a constraint — PF4 settled that.
- **AUC τ: the within-instance 0.80 quantile of |polynomial error|.** Not an absolute value — instances differ in scale, and a quantile fixes the base rate at 0.20 everywhere, which is what makes AUCs comparable across instances and κ. The primary outcome, Spearman ρ, needs no threshold at all.

---

## Gate 1 — your pre-flight checks

### PF3 — API signatures ✅ DONE

On the **installed** BoTorch, not from the spec:

1. Does `get_covar_module_with_dim_scaled_prior` accept `use_rbf_kernel`, and does it return a **bare kernel** (no `ScaleKernel` wrapper)?
2. Does `Normalize` without `bounds=` learn bounds from training-data min/max?
3. What is the discrete-candidate acquisition function's name and signature?
4. What is the lengthscale constraint's lower bound? **Read it off the constraint object** — it's version-dependent, don't hardcode 0.025.
5. **What does `observation_noise=True` do under a fixed-noise likelihood at an unevaluated input?**

**Number 5 is the one that matters most.**

**ANSWERED: it silently substitutes a heuristic.** `mean(train_Yvar)`, applied flat to every query point, no warning. `botorch/models/gpytorch.py:532`, comment `# Use the mean of the previous noise values (TODO: be smarter here).` Confirmed mean rather than median by planting an outlier. `batch_cross_validation(observation_noise=True)` inherits it.

**The resolution works — with a trap on top of it that the spec did not anticipate.** `posterior()` accepts a **tensor** for `observation_noise` and honours it per-point. But that tensor must be in **standardized** units while `train_Yvar` is in **raw** units, because the noise is applied before `Standardize` untransforms. Pass the raw plug-in variance — the obvious move — and you are wrong by `outcome_transform.stdvs**2`, measured at **161×**. Divide first.

**Answers to 1–4:** `use_rbf_kernel` defaults `True`, returns a bare `MaternKernel(nu=2.5)`; `Normalize` without `bounds=` does learn from training min/max (0.85 → 2.72–3.01 on a `[0,0.32]⁶` sub-box); `optimize_acqf_discrete(acq_function, q, choices, ..., inequality_constraints=None)`; lengthscale constraint `GreaterThan(0.025)` read off the object. **Plus one not on the list:** the legacy `get_matern_kernel_with_gamma_prior` returns a `ScaleKernel` while `get_covar_module_with_dim_scaled_prior` returns a bare kernel — the two factories disagree, which is why the traversal helper is mandatory rather than defensive.

**A must read this before finalizing E3's metric.**

### PF4 — wall-clock ✅ DONE

**~10× cheaper than the spec estimated.** One 48-evaluation run is **4.8–9.2 s**, not ~60 s. The full grid is **~0.4 h** single-threaded, not 3–5 h. 92–96% of the cost is `optimize_acqf`; GP fitting is 4–8%.

**Nothing needs resizing.** Keep d ∈ {6, 8}, both noise levels, 10 instances × 5 seeds. On a 14-day timeline the more useful consequence is that a **full re-run after a bug fix costs about half an hour** — mistakes are cheap, so prefer re-running to reasoning about whether a change mattered.

*Caveat: measured on a stand-in objective, since A's biphasic oracle did not exist. Cost is dominated by acquisition optimization, so it should hold — re-run once the real oracle lands.*

---

## Gate 2 — spine

### Build against A's standard test functions first

A ships Branin, Hartmann6, and Ackley wrappers before the biphasic oracle. **Build the entire campaign loop against those.** The real oracle swaps in later.

**This is a deliberate contract test.** If the swap isn't clean, the forward-compatibility design was never real — and this is where you want to find out, not in Phase 2 when a lookup table has to swap in for the same interface.

### `surrogate.py`

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

**Pair with A on this.** ~~Three~~ **Five** traps, all silent, all producing plausible-looking but wrong calibration. All five verified on the installed version by PF3 — traps 4 and 5 are in the PF3 section above and in Doc 1 §5:

1. **`use_rbf_kernel` defaults to `True`.** Omit the override and you get RBF with no error — and a methods section that's false. Test for it.
2. **The function returns a bare kernel, not wrapped in `ScaleKernel`.** Lengthscales are at `model.covar_module.lengthscale`; the common tutorial idiom `.base_kernel.lengthscale` raises. **But the primary config *does* wrap it in `ScaleKernel`**, so any hardcoded path breaks on one of the two configurations. **Write a defensive traversal helper and use it everywhere, including in tests.**
3. **`Normalize` without explicit `bounds=`** learns them from training-data min/max. E4's training data is deliberately a sub-box, so without explicit bounds the extrapolation point lands outside the unit cube and nothing compares across instances.

**Outputscale is a config axis, learned as primary.** Fixed at 1 with `Standardize` puts the far-from-data 95% interval at roughly ±1.96 × training-sd in raw units — and E4's sub-box sits where training sd is compressed, so a fixed outputscale could make the interval narrow for a reason unrelated to the hypothesis.

### `campaign.py`

Ask/tell loop, `X_pending` tracking for in-flight proposals, and serialization.

**Serialize data + config + RNG state. Refit on resume. Not model weights.** More robust across BoTorch versions, and the identical-trace test only passes if the torch RNG state is in the dump.

**Log predictive distributions at proposed points *before* evaluation** — A's E3 prospective calibration depends on this, at both the BO-proposed points and a fixed held-out Sobol set.

### `optimizers.py`

qLogEI with **both continuous and discrete candidate modes.**

**Discrete mode is not optional.** Phase 2's replay can only propose conditions that exist in the published dataset — those are the only ones with measured outcomes. Hardcode continuous search and Phase 2 requires refactoring your optimizer's core.

`optimize_acqf(num_restarts=10, raw_samples=512)`. Sobol initial design of `2d+2`.

**Batch proposals use joint q-acquisition**, never top-q of a single-point surface — that returns q near-duplicates clustered on the same peak.

Simple baselines here (random, Sobol, LHS). A's sequential DoE pipeline is separate.

### `runner.py`

Grid over instances × seeds × methods × oracles → parquet with JSON sidecars carrying the resolved config and library versions.

**Skip-if-exists.** Not for crash recovery — because you'll interrupt runs while developing and shouldn't redo hours.

Optional multiprocessing with `torch.set_num_threads(1)` per worker, and `OMP_NUM_THREADS=1` set in the environment **before** torch is imported.

### The depth inversion — pair with A

A implements it from the quadratic:

```
V(1−c)·s²  +  [2V − c(1+V²)]·s  +  V(1−c)  =  0        V = x*^{−n},  c = 1 − δ
```

**You implement it independently** from a numerical root-find on `δ(r)` directly. Agree on a set of random draws and check the two agree.

One verification case (`s = 3.9917`) is thin cover for math that voids every downstream number if it's wrong.

---

## Gate 3 — E4

### The framing, before the code

An extrapolated stationary point outside the design region is a **textbook response-surface pathology** — canonical analysis and ridge analysis (Hoerl 1959; Draper 1963) exist to detect it, and Box & Draper and Myers & Montgomery cover it.

**Do not claim discovery.** The contribution is *automated, calibration-based detection quantified against model-free nulls*.

### E4a — the measurement

**d=6 only, `n_subbox = 48`.** Second-order at d=8 leaves 3 residual degrees of freedom and the interval balloons for reasons unrelated to extrapolation, which would make the polynomial look well-calibrated and collapse the comparison.

Per instance, per κ ∈ {0.6, 0.7, 0.8, 0.9}:

1. **Sub-box `[0, κ·x*ᵢ]` per dimension, sampled by a CCD from `designs.py` (B-built; A ownership call open).**

   > The design determines `(XᵀX)⁻¹`, hence the polynomial's prediction interval — which *is* your discrimination comparator. A space-filling sample and a CCD give different interval widths at the same extrapolation distance. It's also a fairness question: a response-surface practitioner would use a CCD, and the interval formula is the formula for a designed experiment. **Identical points for all four models.**

2. **Fit four models to identical data:** second-order polynomial (**primary**), stepwise-reduced third-order polynomial (**descriptive only**), the GP, and a practitioner-form parametric model (additive biphasic, no interaction terms, by NLS).

3. **Optimize all four over the same extended box** (the unit cube).

4. **Primary outcome: over-prediction at each model's constrained argmax over the extended box.** Always defined regardless of curvature.

   > **Why not stationary-point escape.** Inside `[0, κ·x*]` you're on the rising arm, and for `n > 1` the Hill function is convex below its inflection. At low κ the second-order fit has *positive* curvature and its stationary point is a **minimum** — "did it escape the sub-box" would be answering a question about a minimum. Report stationary-point location and Hessian classification as a **distribution**, descriptively.

5. **Prediction intervals**, second-order and GP only. **Both must be reported** — comparing a GP posterior against a bare polynomial point estimate is not a fair comparison and would be the first reviewer objection.

**Why second-order is primary, and the third-order model has no interval:**

*Estimability.* Second-order is 28 terms at d=6 with 20 residual df. Full third-order is 84 terms — rank-deficient at n=48, so `(XᵀX)⁻¹` doesn't exist.

*Literature.* Canonical and ridge analysis are second-order techniques. That's what you're citing.

*Post-selection inference.* A stepwise model selects terms from the same data its interval is computed from, so that interval is **anticonservative — too narrow for selection reasons.** Fatal here, because "the polynomial's interval is too narrow" is exactly your finding. **Report the stepwise model descriptively — over-prediction, stationary-point classification, surviving term count — and omit its interval entirely.**

**Parametric comparator: practitioner-form only.** Additive biphasic without interaction terms — what someone would try without knowing the truth. An oracle-form fit is matched by construction, wins trivially, and tells you nothing. **Log NLS convergence failures** rather than silently dropping instances.

### The discrimination test — this is the actual claim

**Note it never touches the stationary point.** It's Spearman ρ between scorers and `|polynomial error|` over a Sobol candidate set. The stationary point is the narrative hook; this is the measurement.

**Candidate set:** a Sobol sample of N points over the extended box, per instance. Not one point per instance — with 10 points the AUC has no usable standard error.

**Three scorers:**

| Scorer | What it is |
|---|---|
| GP predictive sd | The claim |
| Second-order PI width | The DoE comparator |
| **Nearest-neighbour distance to the training set** | **The model-free null** |

**Nearest-neighbour, not centroid distance.** It's the sharper null — it's what GP predictive sd actually approximates, whereas centroid distance ignores design geometry. If the GP has an edge it comes from ARD lengthscales making its distance anisotropic, so an isotropic null is the right thing to beat.

> **"The GP is uncertain far from data" is near-tautological.** The result only means something if the flag is *selective*. **If plain distance discriminates as well as GP predictive sd, the result is that the GP is an expensive distance function** — and that's the comparison a reviewer reaches for first.

**Report the scorer–scorer rank correlation matrix before the result.** With the sub-box in a corner and candidates over the unit cube, all three may be monotone in the same underlying quantity. ρ > 0.95 among scorers means there's no headroom for the comparison to show anything either way. **The reader needs to see the headroom before the finding.**

**Primary: Spearman ρ** against `|polynomial error|` — no threshold to justify. **Secondary: AUC** at a pre-registered τ. **CIs by instance-level bootstrap.**

### E4b — design boundary, reported not claimed

A variant where one factor's true optimum lies below the lower bound.

**Report honestly.** The polynomial's coefficient in that dimension will be significantly negative and *will* signal "lower is better" — which is what the published study observed and acted on. **This is not a mechanism where the GP wins.** It's a design-space problem, not a modelling-uncertainty problem, and claiming otherwise would be indefensible to anyone who has read the source paper.

**Claim E4a. Report E4b.**

---

## Traps in your lane

| Trap | Consequence |
|---|---|
| **Passing raw-unit variance to `observation_noise`** | **Off by `stdvs**2` — 161× in the PF3 case. Silent. Divide by `outcome_transform.stdvs**2` first.** |
| **Relying on `observation_noise=True`** | **Substitutes `mean(train_Yvar)` flat across all query points. Silent. Pass an explicit tensor.** |
| Omitting `use_rbf_kernel=False` | Silently RBF. No error. Methods section becomes false. |
| `isinstance(model.covar_module, MaternKernel)` as the identity test | Breaks the moment `ScaleKernel` wraps it for the learned-outputscale config. **Use the traversal helper.** |
| Hardcoding the lengthscale bound | Version-dependent. Read it off the constraint object. |
| `Normalize` without explicit `bounds=` | Breaks E4's sub-box silently — nothing compares across instances |
| Reporting the stepwise third-order model's interval | Post-selection inference makes it anticonservative, confounding your central finding |
| Reimplementing the over-prediction metric | A's confirmation run and your E4a produce different numbers with no way to adjudicate |
| Space-filling sub-box instead of a CCD | Changes `(XᵀX)⁻¹` and misrepresents what DoE gives you |
| Centroid distance as the null | Weaker than nearest-neighbour, ignores design geometry |
| Top-q instead of joint q-acquisition | q near-duplicate proposals |
| Serializing model weights | Brittle across BoTorch versions; identical-trace test won't pass without RNG state |

---

## The invariant you must not break alone

> **Move the training box relative to the peak. Never move the peak relative to the box.**

**A owns the oracle.** If your over-prediction rate comes back too low, the fix is **lower κ** — not raising `x*`.

At `x* = 0.8` the deepest achievable decline across the stated ranges is 8.2%, under one sigma at the primary noise level. High peak position and measurable depth are not jointly achievable, so raising `x*` to help your experiment would silently break A's E2.

**If you want more extrapolation, ask A.** Joint decision, made once — not a week of quiet parameter adjustment.

---

## If your lane has no mechanism

**PF1 comes back empty at every κ** — A's check, your consequence. E4a has no mechanism.

**Don't improvise a fix.** Read it with A. Either retune the oracle together, or E4 shrinks and E2 carries the paper. That's an hour of joint decision, not a week of solo adjustment.

**All three scorers rank-correlate above 0.95** — no headroom. Report it as such. That's an honest finding about the design, not a null result to bury.

---

## Definition of done

**Long-lived modules** (`surrogate`, `campaign`, `optimizers`, `runner`, `metrics`): tests pass **and A can explain them back**. Not a review checkbox — A narrates what the module does and why. If A can't, it isn't done.

If the internship doesn't extend, whoever stays runs Phases 2 and 3 alone. Phase 2 swaps a lookup table into the `Evaluator` interface and needs your discrete candidate mode; Phase 3 swaps in a human and needs your `X_pending` and serialization. Neither works if only one of you understands the campaign loop.
