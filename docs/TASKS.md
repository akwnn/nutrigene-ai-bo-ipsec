# TASKS — what has to happen, in dependency order

**Decisions live in `OPEN-QUESTIONS.md`. This file is only the ordering and the
owner.** If the two disagree, OPEN-QUESTIONS wins.

Ordered by what blocks what, not by size. Everything in Gate 0 is an hour of
decisions and it is the whole critical path.

---

## Gate 0 — the version-2 pre-registration · **blocks every remaining run**

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
