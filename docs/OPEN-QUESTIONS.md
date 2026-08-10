# OPEN QUESTIONS — ONE PLACE FOR EVERYTHING NEEDING A DECISION

**This is the only file that collects questions. Nothing gets asked anywhere else.**

---

## 🔴 Q16 [EITHER] · PRE-REGISTRATION, WRITTEN BEFORE THE NEXT RUN · **the (κ, ρ) grid is the over-prediction result. No single cell is the headline.**

**Committed before PF1 is re-run at the pre-registered regime, deliberately, so the history shows it was decided in advance and not selected afterwards.**

### The problem this fixes

The over-prediction endpoint has moved four times: unit cube → ρ=1.2 proposed as primary → ρ=2.0 adopted in v2 → ρ=3.0 floated as the strongest cell. **Every one of those moves followed seeing a result, and every one was individually defensible.** That is exactly the pattern pre-registration exists to stop — the cumulative effect is a headline chosen for its size, and no reader can tell the difference from outside.

It will happen again. ρ is still not a *declared factor*; it is a config value we keep re-picking. And the oracle has already changed once (v6 → v8); a corner-shaped claim would not survive another change, while a trend would.

### What is registered

**Estimand — a surface, not a point.** The full grid is the result and is reported in full:

```
kappa in {0.6, 0.7, 0.8, 0.9}   x   rho in {1.2, 1.5, 2.0, 3.0, inf}
```

**Primary claim, directional and falsifiable:**

> **Over-prediction increases monotonically with the extrapolation ratio ρ, and decreases monotonically with κ.**

Tested as a *trend across the grid*, not a contrast between two cells: per-instance Spearman of over-prediction against ρ (and against κ), aggregated to a single estimate **at instance level** with a cluster bootstrap. Four κ on one landscape are four measurements of one landscape, not four independent observations — B already fixed this nested-clustering bug once in `0fc2610`, and it applies here identically.

**Secondary claim:** over-prediction decreases with the instance's true depth. Now testable, because the shipped ensemble records `true_depth` per instance and it varies (0.109–0.135 at d=6).

**What would falsify it:** a non-monotone trend, or a bootstrap interval on the trend statistic that includes zero. Both are real possibilities — the trend must be demonstrated, not assumed from the four unit-cube numbers we happen to have.

**ρ = ∞ (the unit cube) stays in the grid** as the limiting case. It is not dropped for being indefensible; it is *reported as* the indefensible end of a continuum, which is more informative than deleting it.

### What this does NOT change

**B's v2 pre-registration stands untouched.** E4's primary endpoint remains the discrimination Spearman (GP vs nearest-neighbour distance) at `primary_cell: {kappa: 0.6, rho: 2.0}`, with the equivalence bound at 0.08. **This entry governs the over-prediction *characterisation*, which is the mechanism evidence, not the novel claim.** The two coexist: one cell carries the confirmatory test, the whole grid carries the description.

### Why a trend is the better scientific object anyway

*"Over-prediction rises with extrapolation ratio and falls with instance depth"* is a statement about when a second-order surrogate stops being trustworthy — which is the thing a practitioner actually needs, and it transfers to Phase 2 and Phase 3. *"Over-prediction is +9.2 at κ=0.6 in the unit cube"* is a fact about one corner of one synthetic ensemble and transfers nowhere.

**Signed off by A. B: object here before the run if you disagree, not after.**

### ⚠️ CORRECTION TO Q16, made after the first grid run and BEFORE E4 — **A registered a primary that could not fail**

PF1 ran the registered grid (40 instances × 4 κ × 5 ρ = 800 cells, `results/pf1-grid.log`). The ρ trend came back at **Spearman +1.0000, CI [+1.0000, +1.0000]** — a perfect score on every instance at every κ. That is not a strong result; it is the signature of a test that cannot fail.

**It is forced by geometry, and the proof is three lines.** `extended_box_bounds` gives `[0, min(1, ρ·κ·x*)]`, so the boxes are strictly **nested** in ρ — verified: upper bound 0.288 → 0.360 → 0.480 → 0.720 → 1.000. The fitted surface is *identical* across ρ (we fit once per (instance, κ) and reuse). The maximum of a fixed function over a larger set is ≥ its maximum over a subset, so `y_predicted` is monotone non-decreasing in ρ **by construction**. And `y_true` is bounded above by 1.0 because the oracle is peak-normalised. So `over_prediction = y_predicted − y_true` rises with ρ as a matter of arithmetic, not biology.

**This is the same defect A has flagged twice in other people's work this project** — E4's original non-separability check that could never pass, and A's own first DoE arm whose escape statistic was vacuously 0%. Registering it in a pre-registration is worse, because a pre-registration is exactly the document a reader trusts not to contain one. Recording it rather than quietly restating the endpoint.

#### The replacement primary, which can fail

> **The second-order model's prediction interval loses nominal coverage of the true response as ρ increases, and we report the ρ at which it crosses.**

This is falsifiable and it is the question a practitioner actually has — *how far past my data can I trust this interval?* It can come back null: A's earlier κ×ρ sweep measured **96–98% coverage at ρ = 1.2 at every κ**, i.e. perfectly calibrated in the published study's regime. If coverage holds at every ρ, the claim fails and that is a real finding.

**The κ trend stays as registered and it is genuine:** −0.2712 [−0.3988, −0.1450], instance-level bootstrap. Nothing forces it — κ changes the *training data*, not just the scoring box, so the fitted surface differs and the sign could have gone either way.

**The over-prediction surface stays, demoted to descriptive.** It is still worth printing; it is just not evidence of anything.

#### The registered secondary FAILED, in the opposite direction

> Registered: over-prediction *decreases* with instance true depth.
> **Measured: +0.3893 at κ=0.6 and +0.1285 at κ=0.9. Positive. The claim is refuted.**

Reported as a failed prediction, not quietly dropped. Caveat that cuts both ways: true depth spans only [0.1086, 0.1390] across the ensemble — by design, since the acceptance floor compresses it — so this test had little power and the positive sign should not be over-read either. **If we want depth as a real factor, the ensemble needs deliberate depth variation, which is an ensemble change and therefore a joint decision.**

#### One descriptive fact worth keeping

**Turning point was a saddle in 800 of 800 cells.** Zero maxima, zero minima, across 40 instances and four κ. That is now the fourth independent confirmation, after PF1's first run, B's E4 run, and the DoE arm. The spec's prediction of minima at low κ was 1-D reasoning applied to a 6-D surface and is comprehensively wrong.

---

## 🔴 Q14 [EITHER] · E4 HAS RUN. The mechanism is huge; the headline claim is null. Decide n BEFORE rerunning.

**A: read `results/E4-FIRST-RESULTS.md` before anything else.** 40 cells, 78 seconds, on your v8 ensemble.

**What worked, unambiguously:**

- Over-prediction is enormous and scales with κ exactly as designed: **+9.2 → +5.6 → +3.3 → +2.0**, against a response whose max is ~1.0. Every cell extrapolated (40/40).
- The GP over-promises **5–20× less** than the polynomial at every κ.
- **Your Q13 risk did not materialise: 0/40 cells had the peak inside the training corner.** The validity check stays regardless.
- Headroom healthy everywhere (0.83–0.88, threshold 0.95). Practitioner-fit failures: 0/40.

**What did not:**

> **The GP does not beat plain nearest-neighbour distance. Pooled +0.051, CI [−0.003, +0.100], not significant.** Same at every κ. Against the polynomial's own interval width it is +0.004 — flatly nothing.

That is the comparison E4 was built around. On this evidence the honest statement is *the GP is an expensive distance function*.

**But it is a power problem, not a flat null.** All four κ point the same way; the pooled interval misses zero by 0.003; headroom confirms the comparison could have resolved a difference. Instances needed at the observed effect: **~31 at κ=0.6, ~44 at κ=0.8, ~10 at κ=0.9.** We have 10. **The full grid costs 78 seconds — 40 instances is about five minutes.**

**THE DECISION, AND IT MUST BE MADE BEFORE THE RERUN.** Raising n after seeing a result that missed significance, then reporting it as though n had been chosen in advance, is what makes a finding unpublishable. If we scale: bump `preregistration_version` to 2 and state in the paper — *"the first run at the pre-registered n was underpowered for the paired comparison; n was raised on a power calculation performed on that run."* Defensible. A silent rerun is not.

**B's recommendation:** bundle the n decision with Q12 into a single version-2 pre-registration, then run once.

> ### ✅ A's side of Q14 is done — **the d=6 ensemble is extended to 40.** `n_instances_if_ensemble_extended: 40  # Needs A` is satisfied.
>
> **Agreed on the substance:** raise n, bump the pre-registration, state the power calculation in the paper. Silent reruns are how findings become unpublishable. B's v2 wording is right.
>
> **Extending is safe, and A verified it rather than asserting it.** Instances are drawn independently per seed and `instance_id` hashes (dim, seed, oracle_version), so seeds 25–39 cannot perturb 0–24. Confirmed by regenerating three committed seeds and comparing the **landscapes**, not just the parameters: `max |f(X) − f'(X)| = 0.000e+00`, identical `instance_id`. Locked as `test_regenerating_a_committed_seed_reproduces_it_exactly`.
>
> **Only d=6 was extended.** E4 is d=6-only by pre-registration, and E2's grid is 25 × 2 seeds, so d=8 stays at 25. Say if you want d=8 raised too.
>
> #### ⚠️ A correction to A's own PF2, found while doing this
>
> The version field earned its keep. Rebuilding the sampler config by hand gave a **different `oracle_version`** for numerically identical landscapes — because a bare `SamplerConfig()` carries `accept_floor = 0.045`, the **v6 spec's** value, while the shipped ensemble was generated at **0.1083**.
>
> **That had already corrupted a number A reported.** PF2.3's "v8 shipped" acceptance rate of *100% / 100%* was measured at the easier floor. **Corrected: 70% (d=6), 80% (d=8)** at the real floor. The v8 case is unchanged — v6 is 6.395% and 0.105% — but the honest figure is 70/80, and anywhere the 100% was quoted needs fixing.
>
> Closed properly rather than patched: `boec.oracles.SHIPPED_CONFIG` is now the one object that generated what is on disk, asserted against `ENSEMBLE_VERSION` in the suite, with a second test that fails if the bare defaults ever drift into matching it. **Do not rebuild the config by hand.**

### Unpredicted finding, worth its own line

**Every fitted surface was a saddle. 40/40.** No maxima, no minima. The spec predicted a mix and specifically warned that low κ would give *minima*. It was wrong, cleanly. This is exactly why the stationary-point **distribution** was required instead of a bare escape rate — a rate would have hidden it.

---

## 🟠 Q12 [EITHER] · A was right, and the numbers now say so

A argued the unit cube is indefensible: 2–4× extrapolation in all six coordinates at once, against the published study's 1.2× in one.

**The run confirms it.** At over-prediction +9.2 with an interval width ~7 on a response of max 1.0, **"the traditional method's interval is too narrow" is not available as a finding** — the interval covers almost anything. A reviewer would call the comparison staged and be right.

`extended_box_bounds(x_star, kappa, rho)` is in `designs.py`, tested, with the default reproducing current behaviour exactly. **This is now a config decision, not a code change.**

**B agrees with A.** Recommend κ=0.6, ρ=2.0 primary, unit cube reported as a limiting case — folded into the same version-2 bump as Q14.

---

## ✅ Q13 [RESOLVED 2026-08-08] · A's three deviations from spec §4 — **ACCEPTED by Alan. B does not exercise the veto.**

**Decision: A's v8 stands. Port it, use it, cite it as the ensemble.**

Reasoning on the record, so the paper can state it:

1. **The interaction term.** A showed by differentiation that the spec's `β` product **cannot move the optimum** — the bracket multiplying each factor's derivative contains no dependence on that factor. Measured shift over 276 instances: `0.00e+00`. This is not a preference; it means §4.6's own non-separability acceptance check **can never pass**, and in the 8% with a negative bracket the cached optimum was landing below the true one, driving regret negative. Reverting would mean knowingly shipping that.
2. **Weight structure.** Equal weights cap depth at `1/d`, which kills the d=8 arm outright at σ_rel=0.25 — A measured 0 of 50 instances clearing the required depth. The 4-active/90% structure also matches the published 6→4 screening, giving the DoE arm something real to find, and gives ARD a 4.5–5.4× active-to-inert ratio against 1.0× under the spec. Under the spec the kernel comparison on the critical path had **no signal to discriminate on**.
3. **Depth formula.** Overstated true depth by a median 28.4%.

**The risk A flagged as landing in B's lane is now tested and did not occur.** `run_e4_cell` locates the true optimum and refuses to pool any cell whose optimum sits inside the training corner: **0/40 across all four κ**. The check stays regardless — it costs one optimisation per cell and is the difference between a null result and a silently meaningless one.

**Consequence for the write-up:** the ensemble is `biphasic-hill-v8`, not spec §4 as written. Doc 1 §4 is now historical and must be marked as superseded before anyone cites it.

## 🟠 Q15 [EITHER] · The DoE arm is built, and its result is the strongest one we have. One parameter decides it — pre-register that parameter.

`boec/doe.py`, 14 tests, `scripts/run_doe_arm.py`, log at `results/doe-arm.log`. Stage 1 screen (20) → stage 2 CCD on the survivors (27) → fit → **measure the predicted optimum (1)** = 48, the identical budget every other E2 arm gets.

**d=6, 10 landscapes × 2 seeds, scored with B's shared `over_prediction_at_constrained_argmax`:**

| | σ_rel = 0.10 | σ_rel = 0.25 |
|---|---|---|
| predicted optimum fell **outside** the stage-2 region | **100%** | **100%** |
| confirmation **under-delivered** vs the best design point | **100%** | **100%** |
| over-prediction, median [IQR] | **+0.73** [0.64, 1.00] | **+1.66** [1.41, 2.06] |
| sat *on* the stage-2 boundary | 0% | 0% |
| screen recovered the planted active factors | 94% | 86% |
| fitted surface turning point | saddle 20/20 | saddle 20/20 |

**Why this matters more than it looks, given Q14.** E4's standing objection is that we chose κ, so of course the model extrapolates. **This arm hides nothing.** It runs the published procedure over the full space, and the narrowness of stage 2 comes from the screen rather than from us. The over-promise still reproduces, on the same scale as E4a, against a response whose maximum is 1.0. With E4's discrimination claim null, this is the strongest single result in the project — and it is a *domain* claim, not a methods claim.

Two supporting details. The **0% on-boundary** rate says this is genuine extrapolation, not the constrained-optimiser signature `project_record.md` §E9 identified in the published optimum — so the two mechanisms are separable and we can discuss them independently. And **saddle 20/20** matches PF1 and B's E4 run exactly; three independent routes to the same unpredicted fact.

**The parameter, and why it is a question rather than a default.** Stage 2 explores `± stage2_half_width` around the best stage-1 run. A used 0.25.

> **At 0.5 stage 2 spans the whole range, the predicted optimum cannot fall outside it, and the escape statistic is a vacuous 0%.** A's first implementation did exactly that and reported 0% escape across 40 runs, which read as a clean negative result and was a tautology. Two tests now assert stage 2 is a strict sub-region and the search region strictly wider, so it cannot recur silently.

The headline moves 0% → 100% on one argument. **A has deliberately run no other value**, so the pre-registration is not retrofitted. Proposal: fix `stage2_half_width = 0.25` in the E2 config before any further runs, justified as "a local exploration spanning half the range — standard RSM practice of following a screen with a narrower design", and fold it into the same version-2 bump as Q12/Q14.

**One thing B should call:** dropped factors are currently held at the **best stage-1 run's** level. Holding them at **zero** is arguably closer to the published procedure, since Hall/Ogle's own optimum sits at zero for both dropped laminins. A chose the best-run level because it is what a practitioner does and keeps the confirmation point where the data speaks. Recorded either way in `DoEResult.dropped_held_at`.

---

## 🟠 Q17 [A, but B should sanity-check] · E1 exposed a bias in how regret is scored. Fix it before E2 runs.

**E1 passed the gate**, and while passing it produced a number that cannot be true:

```
function     known optimum        BO best-so-far
branin            -0.3979              -0.3747     <-- BETTER than the optimum
```

Nothing beats the optimum. What is being reported is the best **observed** value, and the best of 48 noisy draws is systematically flattering — the winner is partly whichever point drew lucky noise. At σ_rel = 0.10 on a function whose optimum sits near zero, that bias is larger than the quantity being measured.

**Why it matters for E2 specifically, and why it is not self-cancelling.** All arms see the same noise level, so the naive hope is that the bias cancels in a comparison. It does not: the size of the upward bias depends on **how many distinct high-value points an arm samples**, and that differs by arm *by design*. Random and Sobol scatter 48 independent draws; BO concentrates its later batches in a small region and re-samples near-duplicates. Those are different numbers of effective lottery tickets. **An arm can therefore win E2 partly by buying more chances at good noise**, which is not the claim we want to make.

**The fix, which is standard and which A will implement:** score regret at the **noiseless value of the point the method selected**, not at the noisy observation. Selection still uses only what the method is allowed to see; scoring uses `truth()`, which exists precisely for this and is never shown to any model. Concretely, best-so-far becomes `max_t f_true(x_t)` over evaluated points, and the DoE arm's stage-4 confirmation is scored the same way — as it already is, via B's shared metric.

**This is also the concrete cost of the Q5 decision, now visible.** qLogEI's "best value seen so far" is exactly this inflated incumbent. Q5 registered qLogEI as primary with qLogNEI as a declared secondary; E1 shows the bias is real and measurable rather than theoretical, which makes reporting both more clearly worthwhile than it looked at the time.

**Not a licence to change anything else.** This is a fix to a *scoring* function, decided and written down **before E2 has been run even once**, so it cannot be a response to seeing an E2 number. Every other setting — kernel, acquisition, initial-design size, batch plan, seeds — stays exactly as pre-registered.

**One incidental E1 note, so nobody chases it:** gpytorch emits *"Very small noise values detected… rounding up to 1e-06"* throughout E1. That is a scale artefact of the standard test functions — Branin and Ackley span hundreds of units, so `Yvar / var(Y)` after `Standardize` falls below 1e-6. The biphasic oracle has range ~1 and does not trigger it. Not a bug in our noise path.

> ### ✅ B's sanity-check — **A's reasoning is right, the gate survives the fix, and the bias is ~12% of the effect**
>
> A asked for a sanity-check rather than agreement, so this is the measurement. Same `TorchEvaluator`, same σ_rel = 0.10, same 20 seeds, same budget 48 — **only the scoring changed**. Selection still sees nothing but the noisy observations.
>
> | function | known opt | BO (truth) | random (truth) | difference | 95% CI |
> |---|---|---|---|---|---|
> | branin | −0.3979 | −0.4116 | −0.9745 | +0.5629 | [+0.3083, +0.8601] |
> | **hartmann6** | 3.3224 | 2.6606 | 1.7466 | **+0.9140** | **[+0.6693, +1.1623]** |
> | ackley | 0.0000 | −20.0746 | −20.3301 | +0.2556 | [−1.0059, +1.6794] |
>
> **The gate holds.** Hartmann6 moves +1.03 → **+0.914**, interval nowhere near zero. E1's PASS is not an artefact of the bias.
>
> **A's non-cancellation argument is confirmed, and now has a number.** Inflation on Hartmann6 was **+0.155 for BO against +0.035 for random** — differential **+0.120**, in exactly the direction A predicted, because BO concentrates and re-samples while random scatters. It is real and it is not self-cancelling. It is also only ~12% of the 1.03 gap, so the fix sharpens E1 rather than rescuing it.
>
> **Branin's impossible number resolves cleanly.** Rescored on truth it is **−0.4116**, correctly *below* the optimum instead of above it. That is the fix demonstrated, not merely argued.
>
> **Two consequences worth carrying forward.**
>
> 1. **Every absolute figure in `results/e1.log` is flattering**, not just Branin's. Hartmann6's BO result is really 2.66, not 2.87 — 80% of the way to the optimum rather than 86%. Anywhere those numbers are quoted needs the debiased ones.
> 2. **On Ackley the bias is enormous — +4.15 (BO) and +4.47 (random)** — because its values sit near −20 and relative noise scales with magnitude. Best-observed is close to meaningless there, and the sign of the difference actually flips (−0.058 → +0.256) while staying null. This is a *second*, independent reason Ackley should not gate, on top of the one A declared in advance.
>
> **Caveat on these numbers.** This is an independent re-run, not a rescoring of A's stored traces, and the BO figures differ from `results/e1.log` by ~0.01 (Branin −0.3659 here vs −0.3747 there) from RNG ordering between the two scripts. It does not touch the conclusion, but it is not a byte-identical reproduction.
>
> ### ⚠️ Separately: spec §E1's fourth check is not implemented
>
> §E1 is not only the three textbook functions. It also requires: *"on a `β = 0` oracle instance, BO converges toward `sqrt(EC50·IC50)` per dimension."* `scripts/run_e1.py` runs Branin, Hartmann6 and Ackley only, so this one has never run.
>
> It matters more than the other three, because it is the only E1 check that exercises **our own landscape family** rather than borrowed benchmarks — the three standard functions would pass identically if the Hill oracle were broken.
>
> It is also cheap, and B has verified the construction: the shipped v8 ensemble is `peak_modulation`, so the equivalent of `β = 0` is `gamma = 0`, which makes the effective peak `x*_i · exp(0) = x*_i` in every coordinate. Confirmed on a real accepted instance — `f(x*) = 1.0` exactly, and `x*` equals `sqrt(ec50·ic50)` to machine precision, which is the spec's wording literally. **A's call whether to add it, since E1 is A's lane.**

---

## 🟡 Q7 [ALAN] · Author order, and whether the code can be released publicly

Neither blocks building. Both block posting the preprint.

---

## ✅ CLOSED

| | Question | Answer |
|---|---|---|
| **Q1** | Does the oracle exist? | **Yes — ported, merged, 310 tests passing. E4 has run on it.** |
| **Q2** | Who owns `designs.py`? | B owns it; A deleted their copy and is second reader. |
| **Q3** | Test-function wrappers? | Exist, wearing the Evaluator interface. |
| **Q4** | Evaluator interface? | Confirmed by execution. No adapters needed. |
| **Q5** | qLogEI vs qLogNEI? | Run both. qLogEI pre-registered primary, qLogNEI declared secondary. |
| **Q8** | `Yvar` floor? | `sigma_add**2 = 1e-4`. |
| **Q9** | Face-centred vs rotatable? | Face-centred — rotatable axials leave the sub-box. |
| **Q10** | The two pre-registered numbers | 512 candidates, τ = within-instance 0.80 quantile. **Version 2 now proposed — see Q14.** |
| **Q11** | First commit / layout | Done, pushed, shared. |
| **Q13** | Accept A's oracle deviations? | **Accepted 2026-08-08.** v8 is the ensemble. Risk to B's lane tested: 0/40. |
| **C1** | `observation_noise=True` at unrun points? | Silently averages training noise. Never used. |
| **C2** | Units for supplied noise? | Standardized, not raw. Off by 161× otherwise. |
| **C3** | `Normalize` without bounds? | Learns from data. Always pass explicit bounds. |
| **C4** | Discrete-candidate function? | `optimize_acqf_discrete(...)`. |
| **C5** | Does batch selection cluster? | No — it conditions on each pick. |
| **C6** | Grid too slow? | No. Full E4 is 78 seconds. |
| **C7** | 48-run pattern arithmetic? | Exact: 32 + 12 + 4. |
| **C8** | Stepwise conditioning via pinv? | Non-issue — rank filter guarantees full rank; agrees with lstsq to 9.7e-13. |

---

## Where B is up to

**E4 is built, tested, and has produced results on real landscapes.** 310 tests. Reproduce with `python scripts/run_e4.py`.

**Blocked on:** the Q14 n-decision and the Q12 regime decision — both must be settled *before* the next run, together, as one pre-registration bump.

**Not yet built:** figures (spec Build Step 7), and an untested `nonlinear_inequality_constraints` path that matters only for Phase 3.
