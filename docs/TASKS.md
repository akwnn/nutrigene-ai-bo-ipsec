# TASKS — what has to happen, in dependency order

**Decisions live in `OPEN-QUESTIONS.md`. This file is only the ordering and the
owner.** If the two disagree, OPEN-QUESTIONS wins.

Ordered by what blocks what, not by size.

## Status — 2026-08-10

**Gate 0 is CLOSED** (`be3cdc5`). All four items answered and pushed.

**Gate 1 and Gate 2 are closed too, and this section below them is stale in
that respect** — E2 has run, on both dimensions, and T9 was settled as Q18.
The table below is kept as the record of how they closed, not as a to-do list.

**The critical path is now T15**, the one comparison the paper's central
sentence depends on and does not have.

| | Task | Owner | Done when |
|---|---|---|---|
| **T15** | **The d=8 DoE arm** — Q24 found that "BO beats current practice" is unsupported at *both* dimensions: at d=6 it was tested and BO lost, at d=8 current practice was never run, and the d=8 table reads at a glance like a clean BO win. Registered as **Q27** with the design fixed in a commit beforehand, because a d=8 arm designed after seeing d=6 go against BO is an arm designed with a known incentive. | **B builds, A + B decide** | Registered ✅ (`1b064e8`), built ✅ (2^(8-4)_IV in `designs.py`, per-dimension fraction in `doe.py`), run ✅ — DoE wins the primary cell, −0.0321, p=0.0003. **A has not accepted the split**, which is the open half. |
| **T16** | **Choose the DoE arm's estimand — Q28, and it governs the headline.** `regret_on` never defined the DoE arm's selected point (Q20 §3 flagged it and it was left open). Rule A, best-so-far over all 48, is what E2 scores; Rule B, the stage-4 recipe, is what the method produces. **They reverse the sign at every cell at both dimensions**, so "current practice beats BO" is currently a statement about an unregistered choice. Rule B as measured is *not* like-for-like — the symmetric version needs BO's posterior-mean argmax, which E2 never records. | **A decides, B has measured it** | Both estimands named in the pre-registration and reported side by side, and the symmetric Rule B registered *before* it is run — Rule A is already known to favour DoE and asymmetric Rule B to favour BO. |

| | | |
|---|---|---|
| T1 Q16 | ✅ | Replacement primary accepted; its *reported quantity* objected to. See the caveat below. |
| T2 Q15 | ✅ | `best_stage1` primary, `zero` a declared sensitivity, both always reported. Registered with neither arm run. |
| T3 Q14 | ✅ | n=40 for margin, not power. Stale power table marked, not deleted. |
| T4 Q12 | ✅ | Carried into the config. |
| T5 | ✅ | **Premise was wrong** — `preregistration_version` was *already* 2 (verified against `e2a93aa:configs/experiment/e4.yaml`). The real gap was that v2's content did not contain what v2 claimed to; fixed as a "VERSION 2 ADDENDUM" rather than a silent re-bump. |
| T8 | ◐ | Trap closed (`e2a93aa`). Wiring `DoEResult` into a best-so-far curve is still A's. |
| T12 | ✅ | Measured, d=6 single-threaded: qLogEI **7.4s**, random/sobol/lhs **<0.01s**, DoE arm **0.03s**. ~100 BO cells, so the full 500-cell E2 grid is **~13 minutes**, not a day. |
| T9 | ⚠ | In progress as **Q18**, but see the warning below. |

### T1 follow-up — the real coverage rate is now computed, and it changes the objection

`scripts/pf1_coverage.py`, log at `results/pf1-coverage.log`. 800 cells,
instance-level cluster bootstrap. Covered ⟺ `|over| <= pi/2` at the model's own
constrained argmax.

| κ | ρ=1.2 | 1.5 | 2 | 3 | cube |
|---|---|---|---|---|---|
| 0.6 | 0.475 | 0.075 | 0.025 | 0.000 | 0.100 |
| 0.7 | 0.325 | 0.100 | 0.075 | 0.100 | 0.175 |
| 0.8 | 0.525 | 0.300 | 0.300 | 0.425 | 0.550 |
| 0.9 | 0.575 | 0.300 | 0.350 | 0.575 | 0.625 |

**Highest coverage anywhere on the grid: 0.625, against a nominal of 0.95.**

1. **Zero crossings, not two.** Coverage starts below nominal at ρ=1.2 and never
   approaches it, so "the ρ at which it crosses" is undefined because the
   interval never had nominal coverage to lose. The objection's *conclusion*
   holds; its stated mechanism does not.
2. **The non-monotonicity is real** and reproduces on the actual rate, not just
   on the ratio of medians — non-monotone at all four κ, dipping then recovering
   toward the cube. The saturation mechanism argued in Q16 is supported.
3. **The defect neither of us had.** This does *not* contradict A's 96–98% at
   ρ=1.2 — it measures a **different point set**. A's is coverage over the
   design/domain; this is coverage at the recipe the model tells you to run.
   Both legitimate, and they give **opposite verdicts on the same registered
   sentence**. The primary never says which. **Naming the point set is the fix,
   and it matters more than the monotonicity argument.**

**Proposed amendment:** register coverage at *both* point sets as a surface over
the (κ, ρ) grid — at the constrained argmax (decision-relevant, worst case) and
at a fixed held-out set (domain-wide, no selection effect) — reporting a
crossing only where one exists. Same two-point-set structure E3 already uses,
and the same "the grid is the result" logic Q16 argues for, applied to its own
primary. **A has not seen this. Q16 is currently owned by the other session.**

**⚠ T9 is marked A+B and is being decided by B alone.** Spec §E2 says the
pairing choice is worth a significant-vs-non-significant result, which is why it
carries two owners. It is being registered as Q18 — visible and objectable,
which is the right pattern — but A has not seen it. **Do not run E2 on it until
A has.**

---

## Gate 0 — the version-2 pre-registration · ✅ CLOSED (`be3cdc5`)

Q12, Q14, Q15 and Q16 each say *decide before the next run*, and all four are
meant to land as **one** bump. Nothing that produces a headline number can run
until they do. Two of the four are waiting specifically on B.

| | Task | Owner | Done when |
|---|---|---|---|
| **T1** | **Q16** — accept or object to the replacement primary (does the second-order interval lose nominal coverage as ρ rises, and where does it cross). A's original ρ-trend primary was withdrawn as a tautology; the κ trend stands. | **B** | A written answer in Q16. A explicitly asked for objection *before* the run, so silence is not neutral. |
| **T2** | **Q15** — dropped factors in the DoE arm held at the **best stage-1 level** (A's choice, what a practitioner does) or at **zero** (closer to Hall/Ogle, whose optimum sits at zero for both dropped laminins). | **B** | Value recorded in `DoEResult.dropped_held_at` and fixed in the E2 config. |
| **T3** | **Q14** — the n decision, with the corrected rationale below. | either | `n_instances` fixed in config, reason stated. |
| **T4** | **Q12** — regime: κ=0.6, ρ=2.0 primary, unit cube reported as the limiting case. A proposed, B agreed. Only needs writing down. | either | Recorded as decided. |
| **T5** | Bump `preregistration_version` to 2 in `configs/experiment/e4.yaml`, carrying T1–T4. | **B** | `run_e4.py`'s deviation check passes silently against the new config. |

### Correction that T3 depends on

**The power table in Q14 is stale and should not be used as written.** It was
computed on the **unit-cube** effect (+0.051), the regime v2 deprecates. In the
pre-registered primary regime the point estimate is **negative** (−0.027), so
power is not what stands between us and a GP advantage — there is no advantage
to find, and no n changes that.

What raising n to 40 actually buys is **margin on the equivalence bound**, not
significance. At n=25 the one-sided limits are −0.0658 / +0.0112 against a bound
of ±0.08; the lower limit clears by only ~0.014, thin enough to be sensitive to
the bootstrap seed. n=40 moves it to roughly −0.058. That is the honest reason
to do it, and it is worth doing — A has already extended the d=6 ensemble to 40
and the run costs about five minutes.

Note also that Q14's n's were powered on an effect observed **at a near-miss**,
which is upward-biased by selection. Powering on the smallest effect worth
having — 0.08, already pre-registered — is the internally consistent choice.

---

## Gate 1 — scoring correctness · **blocks E2, not E4**

| | Task | Owner | Done when |
|---|---|---|---|
| **T6** | **Q17 fix** — score regret at the noiseless value of the point the method selected, not at the noisy observation. Decided; not yet implemented. | **A** | `best_so_far` scored via `truth()`; a test fails if it regresses. B has verified the gate survives the fix (Hartmann6 +1.03 → +0.914 [+0.669, +1.162]), so this sharpens E1 rather than rescuing it. |
| **T7** | **Spec §E1's fourth check** — *"on a β=0 oracle instance, BO converges toward √(EC50·IC50) per dimension."* `run_e1.py` runs only the three textbook functions, so this has never run. It is the only E1 check that exercises **our own landscape family**; the borrowed benchmarks would pass identically if the Hill oracle were broken. | **A** | Construction is verified: the shipped v8 ensemble is `peak_modulation`, so the β=0 equivalent is `gamma = 0`, giving `f(x*) = 1.0` exactly with `x* == sqrt(ec50·ic50)` to machine precision. |
| **T8** | **Wire the DoE arm into the Runner.** `runner.py` dispatches random/sobol/lhs by name and sends **everything else** to `Campaign` — so `method="doe"`, which `GridCell` already documents as valid, would silently run a BO campaign and produce believable output. | **B** | `run_cell` raises on an unhandled method rather than falling through, and a test asserts it. |

---

## Gate 2 — E2, the paper's spine · **still unrun**

**E2 is A's lane** (`team_build_plan.md:25`, `build-scope-person-b.md:109`). B
has scoped it; B should not build it. The first move is a message, not a commit
— this is the Q2 `designs.py` situation available to happen again in the other
direction.

| | Task | Owner | Done when |
|---|---|---|---|
| **T9** | **Decide the paired initial design, then enforce it.** `optimizers.initial_design`'s docstring says *"This must be identical across every method… There is a test for it"* — but the test only checks the function is deterministic for a given seed, and `run_static_baseline` never calls it. So random and LHS do not share the opening batch with qLogEI, and the shuffle-averaging would break the pairing even if they did. Either is defensible; the spec says the choice is worth a significant-vs-non-significant result. | **A + B** | Policy chosen, written into the pre-registration, and a test that actually asserts it across arms. |
| **T10** | **Regret and AUC analysis.** Does not exist anywhere. Needs simple regret at budget, log₁₀ regret, AUC over the **post-initialization** segment only (evals 15–48 at d=6 — from eval 1 includes the shared opening design and dilutes the difference), median + IQR bands, instance-level bootstrap CIs, paired tests. `discrimination.instance_bootstrap_ci` / `paired_difference_ci` / `sign_flip_test` are reusable; `oracles.optimum_value` makes regret computable. | **A** | Module + tests. |
| **T11** | Driver, `configs/experiment/e2.yaml`, `scripts/run_e2.py`. `e4.py` is the template. | **A** | Grid runs end to end on one cell. |
| **T12** | **Time one cell before planning the day around it.** The grid is 10 instances × 5 seeds × 5 methods × 2 dims = **500 cells**, each a full 48-evaluation campaign. Nobody has timed one. E4's 100 cells took 145s but those are not campaigns. | **A** | A measured per-cell figure, then the full run. |

---

## Gate 3 — the published-data track · **gates Phase 2, not Phase 1**

| | Task | Owner | Done when |
|---|---|---|---|
| **T13** | **`data/published/VALIDATION_REPORT.md` carries 5 blockers, none worked.** B1 the two independent extractions disagree on the stage-2 argmax; B2 two design-matrix cells contradict the printed coded design; B3 the µg/mL columns bake in the contested Collagen IV value (**partly resolved** — the PDF cross-check settles CIV at the Results reading, 28 not 56); B4 Collagen IV's main effect contradicts a published claim; B5 a referenced file was never delivered. | **A** | Each blocker closed or explicitly accepted with a reason. |

---

## Not blocking any build

| | Task | Owner |
|---|---|---|
| **T14** | **Q7** — author order, and whether the code can be released publicly. Blocks the preprint, nothing else. | **Alan** |

---

## Where the project actually stands

**Standing and strong:** the traditional method over-promises, hugely and
reproducibly — +1.1 against a response whose maximum is 1.0, in 100/100 cells.
A's sequential-DoE arm reproduces it running the *published* procedure over the
full space, 100% predicted-optimum-outside-stage-2 and 100% under-delivery at
both noise levels, with 0% on-boundary so it is genuine extrapolation. Saddle in
800/800 PF1 cells, four independent confirmations. And the PDF cross-check now
puts the published study's own optimum at coded **+1.40** in Collagen IV, 20%
above anything tested — the failure mode is in the source paper, not just our
benchmark.

**Dead:** the GP's uncertainty beats plain nearest-neighbour distance. Bounded,
not merely unrefuted, and the prior art says it was the expected outcome.

**Untested:** whether our BO is more sample-efficient than the baselines. That
is E2, and it has never been run. E1 now rules out a bug in the loop as an
explanation for whatever E2 returns — which is exactly what E1 was for.
