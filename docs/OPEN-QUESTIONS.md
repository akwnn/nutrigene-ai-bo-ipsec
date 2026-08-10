# OPEN QUESTIONS — ONE PLACE FOR EVERYTHING NEEDING A DECISION

**This is the only file that collects questions. Nothing gets asked anywhere else.**

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
