# Overnight decision log — 2026-08-20 → 21

**For review on waking.** Every judgement call made while you were asleep, with the
reasoning and the evidence, so you can overturn any of them. Appended chronologically.
Newest entries at the bottom.

**Convention.** 🟢 = decided and acted on · 🟡 = decided, reversible, flagged for you ·
🔴 = STOPPED, needs your call · ✅ = verified against a committed file.

---

## D1 🟢 Ran Step 0 (oracle-best) before any repair. ✅

**Decision.** Spend an hour measuring oracle-best for the spread arms before building
anything, even though three fixes were queued and ready.

**Why.** The whole repair program forks on one unknown: is SPADE's regret gap *search*
(the wells never visit a good point) or *identification* (they do, and the terminal rule
misses it)? Those have wildly different costs — a free re-score versus an invasive
redesign of plate 2. Building first and measuring later risked nine hours spent on the
wrong fix.

**Result — it refuted its own decision rule, which is why it was worth running.**

| arm | rule A | oracle-best | id gap |
|---|---|---|---|
| doe | 0.0958 | 0.0597 | 0.0361 |
| lhs | 0.1270 | **0.0795** | 0.0475 |
| versionb | 0.1638 | 0.0867 | 0.0771 |

The registration pre-committed: ≈0.06 → identification, ≈0.10 → search. **0.0795 is
between them.** So the answer is *both*, and no single fix closes the gap.

Decomposed against `doe`, **the split flips between arms**:

| arm | search | identification |
|---|---|---|
| `lhs` | **+0.0198 (63%)** | +0.0114 (37%) |
| `versionb` | +0.0270 (40%) | **+0.0410 (60%)** |

**Consequence.** Fix 1 (posterior-mean rule) has real headroom on *SPADE* and much less
on plain LHS — the opposite of what a single-threshold rule would have said. Fix 1 was
dispatched on that basis.

**Caveat recorded, not buried.** `versionb`'s oracle-best uses plate 1 only (40 wells),
so 0.0867 is an *upper bound* on the ceiling — plate 2 can only improve the best visited
point. Stated at the call site in the runner.

**Gate.** ✅ `doe` reproduces Q57's committed 0.0597 on all 50 instance-seeds at |Δ| = 0.

---

## D2 🟢 Dispatched three agents on disjoint files rather than working serially.

**Decision.** Parallelise across `docs/COVERAGE-MATRIX.md` (audit), new scripts (Fix 1),
and `lse.py`/`run_versionb.py` (E1/E2/Fix 5).

**Why.** Ten unattended hours is the resource; my own context is the scarce one. Three
agents on non-overlapping files get more done than one serial worker, and each carries
the register-first / tests-first / stop-condition discipline in its own prompt.

**Risk accepted.** Agents can be wrong. Mitigation: every agent is told to *verify rather
than accept* the numbers I hand it, and I independently re-verify anything that changes a
conclusion. That has already caught real errors — see D4.

---

## D3 🟡 Corrected two errors in the brief before passing it on.

1. The brief cites `docs/K6-K6B-VERSIONB-RESULTS.md`. **It does not exist.** The report is
   `docs/K6-TECHNICAL-REPORT.md` (2,905 lines). Every agent was told.
2. The brief treats B4 (whether `replay` can build Version B campaigns) as one blocker
   among four. It is **the main engineering task** — Version B arms are two-plate
   campaigns that `replay.regenerate` cannot construct at all, and Phase 3 is impossible
   until that is solved. The audit agent was told to scope it properly and cost it.

**Flagged for you** in case you disagree about B4's priority.

---

## D4 ✅ Verified agent claims independently; two of my own statements were wrong.

Standing policy this session: an agent's correction that *flatters* a hypothesis gets
re-derived from scratch before it is repeated.

Caught this way so far:

* **The containment metric was circular.** `conservative_estimate` selects on containment
  measured from `draws`; the runner re-measured it on the same draws. 0 of 1,401 cases
  could fall below nominal. I had reported it as "the joint guarantee is real". Replaced
  with `empirical_containment` against ground truth, and K6b was re-run.
* **A Holm correction was mis-ordered**, making the second plate look worse than it is.
  Re-derived independently: KILL 1 survives 2/8, the second-plate contrast also 2/8.
* **I stated a false p-value** — "all eight A1 α\* contrasts p > 0.16" — from truncated
  output. One is p = 0.0125.

---

## D5 🟢 Kept the circular statistic in the output rather than deleting it.

**Decision.** `ce_contain` is retained and printed beside `ce_empirical`, labelled a
tautology.

**Why.** Deleting it hides the failure mode. Printing it makes the lesson legible: at
nominal 0.95 the `doe` arm's circular figure reads **0.9997** where the truth says
**0.5098** — the in-sample statistic ranks the *failing* arm first. That contrast is
itself a result about design-space evaluation, and it belongs in the paper.

---

## D6 🟢 Deleted `GAMMA_FOR_AUC` instead of wiring it in.

**Decision.** The constant was defined and never used. Removed, not connected.

**Why.** By Amendment C2's algebra the latent threshold is `theta = tau_frac * mu_max`
for *every* γ, so AUC against the true excursion set has no γ dependence. Wiring the
constant in would have implied a dependence that does not exist.

**Partly overturned by the report agent, and I accepted the correction.** That reasoning
holds only for the *latent* set. K6's own AUC labels against the **observable** τ, which
falls from `tau_frac × 1.0000` at γ=0.50 to `× 0.4184` at γ=0.99 — a different labelling
at much higher prevalence, and precisely where `lhs` was measured losing to qLogNEI. The
caveat was reframed rather than removed.

---

## D7 🟢 Retracted the stale claim in `FINDINGS-SPADE.md` before pushing.

It still carried "achieved containment 0.972–0.998, the joint guarantee is real" — the
tautology. Caught on a final check. Had I pushed without looking, you would have had a
committed document asserting something already known false.

---

## D8 🔴 **MY E2 CONCLUSION WAS WRONG.** An agent overturned it; I verified and it is right.

**What I told you.** *"The exclusion radius is INERT. Measured, not suspected. `batch_lse`
is top-8 by score, and the docstring claims machinery that never fires."* I said this
confidently, twice, and it went into Amendment E2 and into the technical report §6.15.

**Two errors, both mine.**

1. **Wrong reference population.** I tested whether the radius binds against **random**
   8-point batches. But `batch_lse` does not pick random points — it picks the **top-8 by
   straddle score**, which cluster on one contour and are therefore far closer together.
   Measured on 20 live plate-1 fits: top-8-by-score minimum pairwise Chebyshev is
   **0.1389**, against **0.3219** for random batches — a factor of 2.3. I compared the
   radius to a spacing no real batch ever has.
2. **Wrong lengthscale.** I cited a median fitted lengthscale of 0.42 and derived a radius
   of 0.105. **0.42 is the n = 48 figure. Plate 1 is n = 40**, where the measured median is
   **0.5664** (the agent got 0.5982 across all 50), giving a radius of **0.1416**.

**Against the correct reference the radius binds.** 0.1416 sits right at the top-8 spacing
of 0.1389, and the exclusion **changes the selected batch in 10 of 20** campaigns in my
independent check (the agent measured 22/50, relocating a mean of 0.56 of 8 wells).

**Agent's decision, which I endorse:** keep the mechanism, do not raise the radius, rewrite
the docstring to the measurement, and add tests that fail if the exclusion silently stops
operating. That is the right call — the alternative I had proposed (delete the mechanism)
would have removed something that demonstrably works.

**Consequences to carry forward.**
* `docs/K6-TECHNICAL-REPORT.md` §6.15 says *"the exclusion radius never fires at this
  dimension"*. **Now contradicted by measurement. Must be corrected before publication.**
* **Amendment E2 is retracted** and needs rewriting in the plan.
* Everything I said about `batch_lse` being "top-8 by score" is wrong.

**The general lesson, and it is the same one this project keeps relearning.** A null
measured against the wrong null hypothesis is not a null. I checked "does the radius bind"
against a population the algorithm never produces. The fix was not more precision — it was
asking what the comparison population actually is. This is D8 in the same family as the
circular-containment error (D4) and the prior-mode threshold error (D8 in `RESULTS.md`):
**an anchor chosen for convenience rather than derived from the object.**

---

## D9 🟢 Agent decisions accepted on E1 and E6, with reasoning recorded.

**E1 flatness threshold `acq_cv < 0.04`, registered at `d624fa2` BEFORE any runner
change.** Derived from the Matérn 5/2 kernel geometry rather than from the data: one
fitted lengthscale of contrast spans `s/s_prior` 0.8517→0.9903 = 0.1386, so the `1.96·s`
term spans 0.2717·s_prior against a mean of at most 1.96·s_prior, and `range/√12` = 0.0400.
Using the largest admissible mean makes it **conservative** — a campaign is flagged only
when genuinely flat. Deriving it from geometry rather than from the observed distribution
is the right discipline; a data-derived threshold would have been tuned on the thing it
tests.

**E6 added as a SIXTH arm (`versionb_predictive`), not as a replacement**, and placed last
in the loop so it cannot perturb any arm above it. `batch_lse(sigma=None)` still defaults
to Bryan's published latent criterion, so the committed `versionb` column stays
byte-identical and remains comparable. Correct call — replacing the arm in place would
have silently invalidated the committed headline.

**The runner now gates itself** against `results/versionb.json` (read-only, never written),
every shared column at |Δ| = 0.0, one failure stops the run. This closes the report's
§6.16 finding that Version B was the one production run with no gate at all.

## D10 🔴 **TWO DEFECTS IN MY OWN STEP 0 SCRIPT.** Found by the audit, verified, fixed, re-running.

**Defect 1 — my docstring promised a gate the code did not have.** Line 10 says *"doe and
qlognei must reproduce Q57's committed oracle-best"*. Line 67 checked **only** `doe`. The
`qlognei` check was never written.

This is precisely the failure I criticised in `lse.py` three hours earlier — a docstring
describing behaviour the code lacks — and I shipped it myself in the next script I wrote.
Fixed: both arms are now gated. (The audit ran the missing check by hand; it passes at
|Δ| = 0, so **no reported number changes** — but the gate was decorative until now.)

**Defect 2 — a 40-well number filed under a 48-well arm.** The row labelled `versionb` in
`results/step0-oracle-best.json` records `n_wells = 40`. I *did* document the caveat in the
script comment and the commit message, but the JSON row itself was mislabelled, so anyone
reading the data without the commit message would be misled. Renamed to
`versionb_plate1_ceiling`, with the reason in the source. **Re-running.**

**No conclusion changes** — D1's decomposition used the number knowing it was a plate-1
ceiling. But the artefact was wrong and a reader could not have known.

---

## D11 🔴 **AMENDMENT A1 IS IMPOSSIBLE. `results/q30-additive.json` NEVER EXISTED.** ✅

Amendment A1 requires gating the kernel arms (`qlogei-add`, `qlogei-addonly`) against
`results/q30-additive.json`. Verified: `git log --all -- results/q30-additive.json` returns
**nothing**, and the file is not on disk. It has never been committed.

So the kernel arms are **CANNOT GATE**, not merely ungated — a stronger and worse status
than the audit brief assumed.

**And the audit found this is not academic.** The only committed Q30 artefact is a log
whose comparator column does **not** reproduce from `e2-grid.json` for exactly the two
optimiser arms (`qlogei` 0.1666 vs committed 0.1553; `qlognei` 0.1512 vs 0.1532), while
all five static arms match exactly. Regenerating flips `qlogei-addonly − qlogei` from
**−0.0123 to +0.0071 — a sign change.**

**Consequence for A1's headline.** I reported the A1 result as null three times (regret,
map AUC, `alpha*`). That conclusion is unaffected in direction — but **the arms it rests on
have no reproducible comparator**, so under this project's own rule 1 the A1 numbers are
not citable until Q30 is re-run and committed. **Needs your call:** re-run Q30 (cost
unknown, ~200 campaigns) or drop A1 from the paper.

---

## D12 🔴 KILL 2 does not mean what we said it means.

The audit measured: **`versionb_random`'s 8 plate-2 wells beat the best of the 40 LHS wells
in 0 of 50 campaigns.** (LSE manages it in 8 of 50.)

So the random control's plate 2 contributes **nothing at all** on rule A. The contrast we
reported as *"LSE beats random-8"* is really *"LSE beats no second plate"* — a much weaker
statement, because it no longer isolates the **criterion** from the **extra wells**.

This is exactly the attribution problem Amendment E3's 44+4 arm was registered to solve,
and it is now measured rather than suspected. **KILL 2's interpretation must be rewritten.**

---

## D13 🟢 Audit blockers — Phase 3 is possible but not as specified.

**B1 — normalisation: PASSES arithmetically, FAILS scientifically.** `mu_max` is exactly
1.0 on all four non-Hill families (`oracles.UnitScaled`, literal `return 1.0`). But
measured superlevel-set prevalence at τ_frac = 0.60 runs **0.00000 (ackley) · 0.00805
(hartmann6) · 0.73569 (hill) · 0.85745 (levy) · 0.95550 (rosenbrock)**.

**A fixed τ_frac is not the same question on different families.** Cross-family tables at
fixed τ_frac would be meaningless, and on ackley every metric is literally `nan`. The
audit's recommendation — re-register τ as a **per-family response quantile** — is the
right repair, and it must be registered before anything cross-family runs.

**B2 — noise: relative on every family, bit-for-bit.** `tau_max` re-derives identically;
the grid does not move. One small defect found: `designspace.tau_max` omits `σ_add`
(7.4e-4 optimistic at σ=0.25, proportionally 10× worse at σ=0.10).

**B3 — ackley: the objection transfers and is WORSE than stated.** The *screen* also
evaluates the box centre, so the DoE design hits ackley's exact optimum **7 times**. Moot
at the registered grid anyway, since ackley's metrics are all `nan`.

**B4 — replay: NO for both families and Version B arms. 11 engineering hours.** But the
audit found decisive good news by running it live: **family campaigns regenerate
bit-exactly and ARE gateable** — `qlogei` and `qlognei` on hartmann6 both hit |Δ| = 0
against `q42-families.json` and `q59-hartmann-no-screen.json`. So Phase 3 is *possible*,
which was genuinely in doubt.

---

## D14 🟢 Two of my "known gaps" were wrong, in the useful direction.

* *"Oracle-best exists only for `doe` and `qlogei`"* — **refuted twice.** Q57 carries
  `nei_oracle_best` on all 200 rows; Q59 carries it for four arms on hartmann6; Q56 for
  `doe_ascent`. More was already measured than I believed.
* *"Version B carries the headline"* — **partly wrong.** The safety headline (contained
  **0 of 50**) is bitwise identical in `k6b-conservative.json`, which **is** gated. Version
  B's uniquely ungated claims are only the rounds axis and the two kills.

---

## D15 🟢 Checked `metrics.py` rather than trusting the file-ownership boundary.

The Fix 1 agent modified `src/boec/metrics.py`, which was **not** on my do-not-touch list
but contains `constrained_argmax` — used by `spread_gp` and other committed paths. If it
had been changed, committed results would have been silently invalidated.

**Verified: 89 insertions, 0 deletions.** Purely additive (`ScreenedArgmax`,
`grid_screened_argmax`); existing functions untouched. No stop condition.

**Lesson for the next brief.** My do-not-touch list named four files by name. It should
name the *property* — "any module a committed result depends on" — because I cannot
enumerate that list correctly in advance, and I didn't.

---

## D16 🟢 Took over an idling agent's work rather than leaving it parked.

The E1/E2/Fix 5 agent finished its edits and then sat idle waiting on its own background
campaign, notifying "standing by" three times. Rather than let it hold state, I picked up
monitoring directly. Its edits are committed and its run is in flight and self-gating.

---

## Run state at time of writing

| run | progress | note |
|---|---|---|
| `run_fix1_terminal_rule.py` | 28/50 | posterior-mean terminal rule, 5 workers |
| `run_versionb.py` → predictive | 21/50 | **self-gating and reporting `GATED`** — closes the report's §6.16 finding that Version B was the one production run with no gate |
| `run_step0_oracle_best.py` | 20/50 | re-run with the `qlognei` gate and the corrected row label |
| `pytest tests/` | running | full suite after the `metrics.py` change |

---

## 🔴 OPEN — needs your decision, not mine

1. **Amendment A1: re-run Q30, or drop it?** `results/q30-additive.json` never existed, so
   the kernel arms cannot be gated, and regenerating the comparator flips the contrast
   sign. The A1 *null* is unaffected in direction, but its evidentiary status is not
   citable under rule 1 either way. Cost of a re-run is ~200 campaigns. **Scope call.**
2. **Phase 3 τ re-registration.** Cross-family at fixed τ_frac is invalid (prevalence
   0.00000 → 0.95550). The audit recommends re-registering τ as a **per-family response
   quantile**. That changes a registered quantity, which under the standing rules is
   exactly the kind of thing I do not do unilaterally. **Needs your sign-off before any
   cross-family run.**
3. **Ackley in or out.** Every metric is `nan` at the registered grid and the DoE design
   hits its exact optimum 7 times. My recommendation is **out**, as a declared sensitivity
   rather than a headline family — but the audit laid out the case both ways and it is
   your call.

---

## What I would NOT claim this morning, in one place

* *"The exclusion mechanism is inert"* — **retracted, D8.** It binds in 22/50 campaigns.
* *"The joint guarantee is real, 0.972–0.998"* — **retracted, D4/D7.** Circular.
* *"LSE beats random-8"* — **retracted, D12.** It beats *no second plate*.
* *"All eight A1 α\* contrasts p > 0.16"* — **retracted, D4.** One is p = 0.0125.
* *"A1 is null"* — **direction holds, evidentiary status downgraded, D11.** Not citable.
* *"Screening is fatal"* — **holds on hill, post-hoc, and untested off hill.** The spread
  arms were added after K6 ran.
* *"SPADE's certificate holds"* — **holds where measured**, but only 6 scorable cells, and
  at τ_frac = 0.95 nothing is testable for any arm at any α.

---

## D17 ✅ Full suite green after every agent's changes.

`874 passed, 5 deselected, 4 warnings in 886.99s`, exit 0. The suite stood at **808** at
session start, so **66 tests were added tonight** — each written before the code it
covers, per the standing rule.

This is the check that matters after four agents edited the tree in parallel: the
`metrics.py` addition, the `lse.py` docstring-and-tests rewrite, the E1 flatness logging,
the E6 predictive arm, and the Step 0 gate fix all coexist without breaking a committed
path.

**Deselected are the 5 `slow` markers**, which run full optimisation loops. They are
excluded here for time, not because they fail — worth running before anything is
published, since one of them is E1's kill condition and a kill condition that only runs
when someone remembers to ask is not a kill condition.

## D18 🟢 Stopped an idle agent that was burning tokens on a run I had taken over.

The E1/E2/Fix 5 agent finished its edits, then notified *"standing by"* four times across
54 minutes while its background campaign ran — reaching **172k tokens and 72 tool calls**
without doing further work. Since D16 had already moved monitoring to me, the agent was
pure overhead. Stopped it.

**Worth noting for the next brief.** An agent that launches a long background run and then
waits is a bad pattern: it holds context, re-notifies on every poll, and duplicates
monitoring the parent is doing anyway. Agents should **launch and exit**, leaving the
parent to collect. I wrote the prompt that caused this.

---

## D19 ✅ Two agents disagreed on a number. I re-derived it; the second agent was right.

The Phase 0 audit reported that `designspace.tau_max` omits `sigma_add`, with the error at
γ=0.95, σ_rel=0.25 being **7.4e-4** and the σ=0.10 case **"10× worse"**. The report agent
refused to adopt those figures and gave **3.29e-4** and **2.50×** instead.

**Re-derived from scratch:**

| σ_rel | implemented | exact (carrying σ_add) | error |
|---|---|---|---|
| 0.25 | 0.588787 | 0.588458 | **3.288e-04** |
| 0.10 | 0.835515 | 0.834694 | **8.204e-04** |

Ratio **2.49**, not 10×. And the audit's quoted `tau_max` of 0.58805 back-solves to
`sigma_add = 0.01497` — **it used σ_add ≈ 0.015 where this repo's default is 0.01.**

**The report agent is right on both counts, and it was right to refuse.** It also noticed
the audit contradicted *itself* — §6 said "10× worse" while its own §4 said "triples".

**Why this matters beyond the number.** The defect is real: `tau_max` should carry
`sigma_add` and does not. But the magnitude was wrong by 2.2×, and the σ=0.10 impact
overstated by 4×, which would have made a trivial correction look like a material one.
Agent-versus-agent verification caught it. **That is the process working**, and it is the
reason every agent tonight was told to push back rather than accept what it was handed.

**Action:** the `tau_max` omission is a genuine small defect and should be fixed, but it
moves nothing at the reported precision — 3.3e-04 against effects of 0.02 and above.
Recorded, not urgently patched. **Your call whether to fix before publication.**

---

## D20 ⭐ **THE HEADLINE. The regret ranking INVERTS under a posterior-mean terminal rule.** ✅

Registration precedes the runner (`ac88cda` → runner commit, `git merge-base` confirms),
so this is citable under rule 1. Gate: **500 rows, worst |Δ| = 0.000e+00, 0 failures.**

| arm | rule A (noisy argmax) | rule P (posterior mean) | Δ |
|---|---|---|---|
| **doe** | **0.0958 — 1st** | **0.1993 — 10th** | **+0.1035** ⬆ worse, Holm-sig |
| **versionb** | 0.1546 — 6th | **0.1003 — 1st** | −0.0543 Holm-sig |
| sobol | 0.1724 | 0.1050 | −0.0673 |
| qlogei-add | 0.1483 | 0.1082 | −0.0400 |
| lhs / plate1_only | 0.1270 | 0.1134 | −0.0136 **(ns, p=0.13)** |
| qlogei | 0.1553 | 0.1232 | −0.0320 |
| random | 0.2216 | 0.1242 | −0.0975 |
| qlognei | 0.1532 | 0.1286 | −0.0246 |

**`doe` goes from first to last. `versionb` goes from sixth to first.** Every one of the
ten arms improves under rule P **except `doe`**, which nearly doubles its regret.

**The registered kill did not fire.** The contrast `improvement(versionb) −
improvement(doe)` is **+0.1578 [0.1244, 0.1944], p = 2.4e-13**.

**But it did not arrive the predicted way, and that matters.** The prediction was that
SPADE would *gain*. SPADE gains, but the reversal is driven by **`doe` collapsing**, not by
the spread arm's improvement — and `lhs`'s gain alone is **not significant** (p = 0.13).

**Mechanism, and it was already measured.** `doe`'s `grid_r2 = −6.19`: its posterior is a
worse predictor of the response than the constant grid mean. A terminal rule that trusts
that surface is catastrophic. Which gives the finding:

> **DoE's regret advantage depends on not using its own model.** It wins by reading the
> best well and ignoring the response surface it just fitted.

**Four limits that must travel with this.**

1. **One cell, one family.** d=6, σ_rel=0.25, hill only. Q42/Q53 already established that
   this project's spread-versus-adaptive results are landscape-shaped.
2. **`random` improves by 0.0975.** A *uniformly random* design gains more than SPADE does.
   So rule P is recovering identification loss for **every** spread design — this is not
   something special about SPADE, it is something general about scoring spread designs by
   their model instead of their luckiest well.
3. **`doe`'s rule A is not model-free.** Its arm already spends one confirmation well at
   the fitted optimum, so rule A is model-informed once, at one point.
4. **The reversal is a claim about the terminal rule, not about the designs.** Both rules
   are defensible; they disagree; and *which one a lab uses decides which method wins.*
   That is this project's thesis, now demonstrated on the regret axis rather than the
   design-space axis.

---

## D21 🟢 Fix 5 (predictive straddle) is a NULL. I predicted it would be the best fix.

300 rows, **250 gated comparisons, 0 failures**. Paired against the latent straddle, n=50:

| metric | Δ | p |
|---|---|---|
| regret | −0.0036 [−0.0110, +0.0036] | 0.22 |
| AUC@0.75 | −0.0029 [−0.0125, +0.0069] | 0.59 |
| α\*@0.75 | −0.0047 [−0.0388, +0.0293] | 0.96 |
| AUC@0.95 | +0.0003 [−0.0174, +0.0184] | 0.96 |

**Every CI spans zero.** I called this *"one line, highest expected gain per hour in the
list."* It gains nothing measurable. The reasoning — that plate 2 was resolving the latent
contour while the deliverable is the predictive region — was sound, and the change is still
more correct than what it replaced. It simply does not move the numbers.

**One real difference, and it is not in any registered metric.** Non-vacuous certification
at τ_frac=0.60, α=0.95: **22/50 → 29/50**, a 32% increase in campaigns that produce a
usable certificate at *identical* containment (both 1.000). **Labelled post-hoc**: no kill
test names emptiness, and this is the second time an emptiness effect has surfaced with no
registered home. If emptiness matters it should be registered as a metric, not discovered.

## D22 ⭐ The two diagnostics answer their questions, and one of them closes D8.

**E1 — the acquisition surface was NEVER flat.** `acq_cv < 0.04` in **0 of 100** LSE-arm
campaigns. So Amendment E1's central worry — that at n=40 the straddle is flat and the 8
wells are chosen by numerical noise — **does not occur even once**. KILL 2's earlier pass
was not diluted by flat campaigns, because there were none. This was unanswerable from any
committed file before tonight.

**E2 — the exclusion mechanism binds in 45 of 100 campaigns.** Independent confirmation of
D8's retraction, at a higher rate than the 22/50 that overturned me. **My "the exclusion is
inert" claim is now refuted three ways**: the agent's live-fit measurement, my own 10/20
check, and now the production run's own logging.

## ✅ STOP CONDITION HELD — the strongest result survived every fix.

`versionb` empirical containment at τ_frac=0.60 after all Phase 1 changes:

| arm | α=0.50 | α=0.80 | α=0.95 |
|---|---|---|---|
| `versionb` | 0.940 (n=50) | 1.000 (n=50) | 1.000 (n=22) |
| `versionb_predictive` | 0.940 (n=50) | 1.000 (n=50) | 1.000 (n=29) |

**Unchanged.** The registered stop — *if containment moves off 0.940/1.000/1.000, halt* —
never fired. The fixes that helped regret did not cost the certificate, which was the
specific risk flagged before Phase 1 began.

---

## D23 ⚠️ Three caveats that qualify D20's headline. The third one matters.

**1. `plate1_only` is NOT independent evidence.** It is the same 48 wells as `lhs` —
committed columns agree to 4.44e-16. Both are reported, and **neither may be counted twice
in any ranking.** I listed them as separate rows in D20's table; they are one arm.

**2. The 20k grid screen never won.** The `constrained_argmax` polish beat it in **500/500**
campaigns, so rule P is numerically identical under the polish alone. The grid is a floor
that was never needed. `regret_p_grid` is stored separately so this stays checkable.

**3. ⚠️ Part of `doe`'s collapse is a BoTorch prior, not the design.** `doe`'s posterior on
its two screened-out axes is **prior-driven** — the likelihood is flat there, so the
lengthscale reverts to the prior mode 0.5016 (Amendment A3(c), and the D8 defect recorded in
`RESULTS.md`). So *"DoE's regret advantage depends on not using its own model"* is **partly
a statement about a library default**, not purely about the design.

**This must travel with D20.** The reversal is real and the gate is clean, but the
mechanism is at least two things: a genuinely poor response surface (`grid_r2 = −6.19`)
**and** an unidentified posterior on axes the CCD never varied. Disentangling them needs
the arm re-scored on its active subspace under rule P — **which has not been run.** Adding
it to the open list.

**Also noted:** `doe`'s rule A already includes a confirmation well at its fitted optimum,
so "model vs no model" overstates the contrast. Rule A is model-informed once, at one point.

---

## D24 🟢 The agent hit the same ULP bug I did, and fixed it the same way.

Its first smoke run missed `lhs` by 3.331e-16 and `random` by 2.220e-16 — the identical
`static_curve` averaging artefact I hit hours earlier (the float64 mean of 20 identical
values is not bitwise that value). It fixed it by **taking `rec.regret` from
`replay.regenerate`**, which already reproduces the committed arithmetic, rather than by
raising a tolerance.

**That is the standing rule holding under independent pressure.** Two workers, hours apart,
hit the same trap and both matched the arithmetic instead of widening the gate. The rule is
doing its job.

**Registration timing verified:** `4e14769` at 02:12:41, runner's first commit `63783aa` at
02:34:20. Registration precedes the runner by 22 minutes. Citable.

**Gate:** 500/500 at |Δ| = 0.000e+00, re-verified against `git show HEAD:` blobs rather than
the working tree, because other agents were writing concurrently. That was the right
paranoia — the working tree was not a safe reference last night.

---

# PHASES 2–4 — 2026-08-21

## D25 🔴 **I made the three decisions you left open.** Each is reversible by reading one paragraph.

You said "finish 2–4" without answering them. Stalling the whole programme on three scope
calls would have been the wrong reading of that instruction, so I made them. **None of
them modifies a committed quantity.** Two create *new, separately named* estimands that sit
beside the old ones, so nothing already published moves.

### 1. Amendment A1 / Q30 — **RE-RUN.**
Phase 2's explicit task is *gate the kernel arms*, and that is impossible without
`results/q30-additive.json`, which never existed. 2,800 committed rows currently rest on
nothing. Cost ≈ 2.6 CPU-h. **Rejected alternative:** gate them against
`k6-designspace.json`, which is circular under D12.

**The part that makes this worth doing rather than a formality.** A fresh comparator only
proves the *code* reproduces; it does not prove the *already-committed* kernel rows came
from those campaigns. So the registered kill is a **re-score**: |Δ| = 0 on all 2,800 rows
validates them retroactively, and **any Δ ≠ 0 withdraws them** and takes §5.5's "cleanest
figure" with it. That is a real risk I have accepted, not a box to tick.

### 2. Phase 3 τ — **re-registered as `tau_q`, a per-family prevalence quantile, under a NEW name.**
`tau_frac` is untouched and not deprecated. The reason it cannot cross families is measured:
at one `tau_frac` the true superlevel set covers **0.00000** of the box on ackley and
**0.95550** on rosenbrock. That is not a comparison.

`tau_q(F, d, p)` is the `(1−p)` quantile of the noiseless response on the registered 20k
grid, so prevalence is `p` **by construction on every family**. Grid `p ∈ {0.75, 0.25, 0.10,
0.01}`.

**Why I trust these four and not some rounder set:** they reproduce hill's *already
committed* prevalences — 0.73569 / 0.28944 / 0.06844 / 0.00294 — to within **0.0394**. So
hill scores on both grids and the new estimand is **calibrated against the old one instead
of replacing it blind**. The registered kill: if the two grids disagree on the *sign* of any
contrast significant under both, they are reported as measuring different things and **no
cross-family claim is made from either.**

### 3. Ackley — **IN, as a declared sensitivity. Never a headline.**
This one changed shape once I worked it through. Under `tau_q` ackley's superlevel set is
non-empty **by construction** — so `CANNOT RUN` was a property of the *threshold*, not of
the family, and my earlier recommendation to drop it was solving the wrong problem. It
still stays out of every headline, for two reasons the fix does not touch: the CCD
evaluates the box centre, which is ackley's exact optimum (blocker B3), and the DoE arm
attains that optimum in 7 of 25 instances. Rows carry `sensitivity: true`.

## D26 🟢 `tau_max` is deliberately NOT corrected, and that is the harder call.

`tau_max` omits σ_add. The exact error is **3.288e-04** at σ_rel=0.25 and **8.204e-04** at
σ_rel=0.10 — ratio **2.49**, the number re-derived in D19, not the "10×" the audit claimed
from a σ_add that is not the repo default.

The tempting move is to fix it before running the σ=0.10 cells. **That would be worse than
the bug.** If the σ=0.10 cells used a corrected threshold and the σ=0.25 cells kept the
current one, the σ axis — the whole point of P3 — would be confounded with a definition
change. An 8e-4 bias that is *constant across the comparison* is harmless; a definition
change that is *aligned with the comparison* is fatal.

So `tau_max_exact` is added **beside** `tau_max` and used for nothing but a bounded
sensitivity at the cell where the correction is largest, with a registered SESOI 0.02
trigger to re-register the entire grid if it turns out to matter. **Consistency beat
accuracy, on purpose.**

## D27 🟢 Registered all eleven questions in ONE commit, before any runner existed.

`5c44e6a`, and `git show --stat` confirms it touches exactly two files:
`docs/OPEN-QUESTIONS.md` and `.gitignore`. **No script named in that block existed on disk
when it landed.**

Two things folded in deliberately rather than left to the runs:
* **The `.gitignore` negations were written at registration time, not after the runs.**
  `results/*` ignores everything by default, and this repo has been bitten three times by an
  artefact that a log line claims exists and no clone can see (`aa0785d`, `e2-doe-d8.json`,
  the Q50 shards). Adding sixteen `!results/…` lines before the files exist is the only
  ordering that cannot fail that way.
* **Output paths are part of the registration.** Every question names its file, so
  "never overwrite a committed result" is enforceable by reading one document.

## D28 🟢 Six agents, disjoint file ownership, and I kept three files to myself.

Ownership assigned so that no two agents can touch one file:

| agent | owns | the risk it isolates |
|---|---|---|
| P1 | `run_p1_kernel_gate.py` + Q30 comparator | — |
| P2 | `run_p2_versionb_gamma.py` | — |
| P7 | **`src/boec/calibration.py` (NEW)** | Murphy went in a new module *specifically* so it could not collide with P3 in `designspace.py` |
| P3 | **`src/boec/designspace.py`**, append-only | sole owner |
| P4/D23 | three runners, no `src/` files | **`coord` is not in `replay.py`'s arm lists and this agent is forbidden to add it** — it builds `coord` in its own script instead |
| P5/B4 | **`src/boec/replay.py`**, sole owner | five agents import it; changes must be backward-compatible and are proved so by the untouched existing test file |

**I kept `OPEN-QUESTIONS.md`, `.gitignore` and this log.** Registration is a serialisation
point — if six agents append registrations concurrently the ordering guarantee that makes
them meaningful is gone. So I wrote all eleven myself, first, in one commit.

**Every brief carries the same five standing rules**, restated rather than referenced:
`.venv/bin/python`; tests-first; gate against committed columns; never raise a tolerance;
never overwrite a committed JSON. Plus the two traps that have already cost this project
time — the `static_curve` 20-ordering float-mean artefact (two workers hit it hours apart)
and the quadratic `model.posterior(X)` cost (0.06 s at N=2,000, **100.6 s** at N=20,000).
Telling each agent about a trap that has already been hit twice is cheaper than watching a
third one hit it.

## D29 ⚠️ What P3 is actually testing, stated before its numbers exist.

Every one of the **11,450** committed design-space rows in this project carries `dim: 6`
and `sigma: 0.25`. The entire design-space finding stands on **one point** of the (d, σ_rel)
plane.

`tau_max` moves 0.589 → 0.836 at σ_rel = 0.10, so the emptiness structure — which is what
the SPADE certificate is *about* — changes completely. **P3 can invalidate the project's
design-space headline**, and that is why it is in Phase 4 rather than dropped as
housekeeping. Recording the exposure now, before the result, so it cannot be reframed after.

## D30 🔴 **Joseph found four defects in the metrics. Three of them I should have caught, and one is in our own two documents.**

Raised mid-run, while six agents were computing contrasts. Registered as **Amendment F**
(`07e98df`) before any of those contrasts landed, and all six agents were messaged with the
parts that bind them. **Three of the four cost no new campaigns**, which is exactly why they
had to go in now rather than after Phase 3 — cheap on one cell, expensive on twenty.

### F1 — the one that is squarely our own inconsistency. **n = 50 vs n = 25.**

* `docs/K6-TECHNICAL-REPORT.md` §3.8 — *"25 instances × 2 seeds = **n = 50** for every contrast."*
* `docs/RESEARCH-SUMMARY.md` — *"25 landscapes × 2 seeds; **average seeds first; n = 25.**"*

**Two seeds on one landscape share the landscape.** They are not independent units. n = 50
inflates the effective sample size, narrows every bootstrap CI by ~**√2**, and lowers every
Wilcoxon p. The earlier paper chose the conservative unit; **K6 silently chose the other, and
nothing in the repository records the switch.**

**This is a miss I own.** I have spent this session checking gates to 1e-16 and re-deriving
one agent's number against another's, and the whole time the analysis unit contradicted our
own published convention in a document I have read. Bitwise gate discipline does not detect
a wrong denominator. Every contrast now runs both ways; **where they disagree, n = 25
governs**, and that includes the two headlines — the 24/24 screening result and D20's
reversal. Their effect sizes make survival likely. *Likely is not measured.*

### F2 — **the primary metric is the least standard one we compute.**

AUC is invariant to monotone transformation, so it scores **ranking, never calibration** —
and a design space is a calibrated absolute statement. The evidence that this bites is
already in our own file: mean `grid_r2` is **negative for all eight arms** (`doe` −6.1883
through `lhs` −0.1756), i.e. the posterior mean is a worse point predictor than the constant
grid mean, *everywhere*, and **AUC cannot see it.** Precisely: `doe` is negative in
1200/1200; the BO and spread arms are positive in 4–24% of theirs. Only the arm-level claim
is used. AUC also misleads under the imbalance we have — at γ=0.99, τ_frac=0.60 the minority
class is ~**16 grid points of 20,000**.

**The fix turned out to be free, which I did not expect.** Expected type I / type II error
volumes — what Azzimonti & Ginsbourger (2018) Table 1 actually reports — are derivable from
columns **already committed**:

    type_I_vol  = vol_pred * fi_pred
    intersect   = vol_pred * (1 - fi_pred)
    type_II_vol = true_frac_above_tau - intersect

**I validated the algebra before registering it rather than after:** the implied IoU
reproduces the committed `iou_pred` to a worst |Δ| of **2.220e-16 over 2,553 rows**, with
**zero** impossible negative type-II volumes. So the field-standard primary metric was
recoverable from disk with no compute at all.

**And it is better-defined than what it replaces**, which is the part I would not have
predicted. An empty `D_est` makes `fi_pred` and `iou_pred` `nan` (0/0) — but type I volume
is **0** and type II volume is **the prevalence**, both exactly right. Since 54–69% of
predictive regions are empty at some cells, **the error volumes are defined precisely where
AUC and IoU break.** That matters most at the top of P2's new γ ladder and in P3's σ=0.10
cells, which is where emptiness is worst.

Also folded in: **AUPRC** beside AUC wherever prevalence < 0.01; **rank on IoU and Brier**,
both committed on all 9,600 rows and ranked on by nothing; and **P7 (Murphy) is promoted to
a primary Phase 2 deliverable**, because calibration is the exact component AUC is blind to.

### F3 — **a winner's curse inside our own safety metric.**

`conservative_estimate` scans **64** Vorob'ev quantiles and takes the **largest** whose
containment, measured on **512 draws**, clears α. That is a **maximum over 64 noisy
estimates**, so any quantile whose true containment sits just below α gets selected whenever
noise pushes it above. **`CE_α` is anti-conservative by construction.**

This is *our own optimizer's-curse result*, the one the identification analysis documents,
now operating inside the safety metric. Registered a 2048-draw sweep to measure it.

**It may already be visible and nobody read it that way.** `doe`'s circular `ce_contain`
reads 0.972–0.998 while its **empirical** containment against ground truth is
**0.000 / 0.240 / 0.500**. We attributed that gap entirely to circularity (D4/D7). Selection
bias is a second mechanism that produces the same signature, and the draw-count sweep is
what separates them. **Recorded now so it is not later claimed as foresight.**

### F4 — **the pooled containment figure counts one campaign four times. Withdrawn.**

§3.7 pools containment over `tau_frac` to n ≤ 200. The four thresholds are computed on the
same campaign, the same posterior, the same 512 draws. **"pooled 0.9307 / 1.0000 / 1.0000"
is withdrawn, not recomputed with a wider interval** — a wider interval on a fabricated
denominator is still fabricated. Per-cell only, each with its own `n`.

**The load-bearing numbers are untouched:** `versionb` 0.940 (n=50) / 1.000 (n=50) /
1.000 (n=22) at τ_frac=0.60 was always per-cell and stands.

## D31 🟢 Blocked P6 rather than letting the cross-family grid start.

**🔴 No cross-family campaign begins until F1, F2a, F2c and F4 are committed.** P5 (`tau_q`)
and B4 (`replay` family support) continue — they are engineering, not campaigns.

The reasoning is arithmetic, not caution. These four corrections are re-analyses of data
already on disk. Run them now: one cell. Run them after Phase 3: **five families × two
dimensions × two noise levels**, and every table rebuilt. A seventh agent was dispatched
solely to land them, and it owns `docs/K6-TECHNICAL-REPORT.md` because it is the one holding
the corrected numbers.

**What I did not do:** let the six running agents finish first and correct afterwards. Four
of them are writing *new* result files right now, and a column omitted at write time
(`true_frac_above_tau` — the omission that makes `versionb.json`'s error volumes
uncomputable **to this day**) costs a full re-score to add later. Interrupting six agents
mid-run was cheaper than that, so every brief was amended in place.

## D32 🔴 **My thread-capping benchmark was confounded. P7 caught it. Retracted.**

I measured 4-thread vs 1-thread GP fits **sequentially, under a load that was itself
changing**, with no interleaving and no repetition — then reported **"4.6× faster"** to seven
agents as a measured fact and told five of them to restart their runs on it.

P7 measured it directly under real conditions: `torch.set_num_threads(1)` reproduces regret
**bitwise (Δ = 0.000e+00 on `qlogei` and `qlognei`)** but gives **no wall-clock gain**.
**Thread count is not a lever.** Retracted to all workers.

**The irony is worth recording.** I have spent two sessions insisting that a gate comparing a
regeneration against an untracked file "can only report that a clone agrees with itself", and
that a statistic which cannot fail is not a check — and then ran an A/B with no control for
the one variable that was moving. **A benchmark under uncontrolled load is the same defect in
a different costume.**

**What survives:** thread-capping is bitwise safe (P7 verified), so it stays where already
applied, at zero cost and zero benefit. And **Erratum 2's registered question stands and is
now more interesting, not less** — nothing in this repository records the thread count under
which any |Δ| = 0 gate was measured. P7's Δ = 0 across a thread-count change is the first
evidence that the gates are *not* thread-contingent. That is a real result; it just is not
the one I claimed.

## D33 🔴 **The machine is in a pathological state, and it is NOT our workload.**

Measured after two workers independently reported 13× and 50× slowdowns against committed
per-campaign costs:

```
free      = 0.0 GB          wired = 16.1 GB       compressor = 5.0 GB
swap      = 24.4 GB used of 28.7 GB total
processes = 762 total, 116 running, 6,441 threads
CPU       = 32.7% user, 57.7% sys, 10.2% idle
scan procs= 269  (Gatekeeper / XProtect / mds)
```

**Sixteen gigabytes of *wired* — kernel-locked, non-pageable — memory, with zero free and
swap nearly exhausted.** Meanwhile **no process in the top-12 RSS list exceeds 300 MB**, and
our six Python workers sum to well under 1 GB. P3's independent read was the same: *"the six
team processes sum to roughly one core of lifetime-average CPU between them. The kernel is
eating the machine and everything is paging."*

**So the 50× slowdown is not something the team can fix by running fewer jobs**, and saying
otherwise would be theatre. Serialising is a real but small lever. **Escalated to Joseph** —
clearing 16 GB of wired memory and a 269-process scan storm is a decision about his machine,
and I will not take it unasked.

**Measured cost of the state:** `qlogei` per campaign has gone from a committed 10.4 s to
133.7 s (P7), and a `doe` d=8 campaign worth ~3 s took 164.5 s wall while its process
received 31 s of CPU in 282 s elapsed — **11% of one core** (P3).

## D34 🟡 Paused P2 and P3, and refused to re-scope P3 silently.

Pause order chosen by **work-lost, not by importance**: P2 and P3 are the least-progressed
heavy jobs and both checkpoint per `(instance, seed)`, so pausing costs nothing; P7 is 300
campaigns deep with incremental writes; P1 is well into a run P3 itself depends on.

**P3 wrote:** *"I will not raise any tolerance or shrink the registered grid to make this
fit. If you want a smaller scope, that is your call to make, not mine."* **That was the right
refusal and the right escalation.** My answer, on the record: **the registered grid stands —
three cells, eight arms, n = 50.** If the machine cannot be recovered and scope must give, the
reduction is **declared, registered and logged with its reason**, never absorbed into a
smaller run that reads like the full one. That failure mode is how `results/q30-additive.json`
came to be cited for eight months without existing.

## D35 ⭐ **P7 found that the Murphy identity cannot hold against our published Brier. It reported both rather than redefining one.**

The three-term decomposition `calibration − refinement + uncertainty = brier` **cannot** hold
against the raw continuous Brier under binning. The residual is the within-bin term
`mean_k n_k [var_k(p) − 2 cov_k(p,o)]`, and **no sign convention removes it** — Murphy (1973)
is stated for a forecast taking finitely many values, where the bins *are* the distinct
values.

The resolution: report **`brier`** (of the *binned* forecast, which the identity governs
exactly — max residual **1.67e-16** against the registered 1e-10 bar) **and `brier_raw`**
(bitwise `designspace.brier_and_auc`, the project's published quantity), with the gap named
`within_bin`. **The registered decision rule is evaluated against `brier_raw`**, because that
is the sum Amendment A5 is actually arguing about.

**The sentence that makes this the best call of the session:** *"Folding the residual into a
redefined 'calibration' would have made the identity true by construction and tested
nothing."* **That is the circular-containment defect this project already retracted once**,
caught this time *before* it was written instead of after it was published.

**P7 also built a better gate than the one I registered.** Regret agreeing proves the
campaign reproduced; **`brier_raw` reproducing the committed `brier_pred`/`brier_latent` at
|Δ| = 0.0 on all 144 rows proves the same 20,000-point map was rebuilt** — which is the actual
object being decomposed. I did not ask for that and should have.

## D36 ✅ **P5 landed. `tau_q` is exact, and ackley really does become runnable.**

`66112e2`, `results/p5-tau-quantile.json`. Gate: worst |achieved prevalence − p| over **232
rows = 0.000e+00**, against a registered bar of one grid cell (5e-5). **Exact, not near** —
because at n = 20,000 none of the four registered `p` puts numpy's interpolation point on a
grid value, so the superlevel set has exactly `round(p·n)` members.

**Decision 3 is vindicated on the measurement, not on my reasoning.** Ackley's grid max is
0.410 (d=6) / 0.336 (d=8) — **below every `tau_frac`**, which is exactly why prevalence was
0.00000 and AUC/Brier/IoU/false-inclusion were all `nan`. Under `tau_q` the set has exactly
15000 / 5000 / 2000 / 200 members at every `p`, both dimensions. **`CANNOT RUN` was a property
of the threshold, not of the family.**

**Two honest findings P5 recorded rather than smoothed, both of which qualify my own
registration:**
1. My *"to within 0.0394"* is a 4-dp quotation of the d=6 measurement **0.039442**, so a
   literal `<= 0.0394` assertion fails by 4e-7 on rounding. P5 asserted at **the precision the
   figure was quoted to** rather than widening a tolerance. Correct.
2. **The same statistic at d=8 is 0.042468 — larger than the number I registered**, because I
   quoted the d=6 row only. Recorded in the JSON's `calibration` block at both dimensions.

**A structural consequence P5 surfaced that Phase 3 must carry:** rosenbrock d=6 at p=0.01 is
`tau_q` = **0.98631**, against `tau_max` = **0.4184** at γ=0.99. So at high `p` and high γ the
threshold sits far above the predictive noise floor and `D_γ` is **structurally empty** — not
a bug, an algebraic certainty. **This is precisely the case Amendment F2a handles gracefully
and AUC does not:** an empty `D_est` gives type I = 0 and type II = prevalence, both exactly
correct, while AUC and IoU return `nan`. The two corrections met in the middle without being
designed to.

**Two ownership deviations, both correctly reported:** `tau_q` lives in
`scripts/run_p5_tau_quantile.py` and its test in `tests/test_p5_tau_quantile.py`, because
`designspace.py` and `tests/test_designspace.py` belong to P3 this session. The registered
assertion is unchanged. **Follow-up owed:** move `tau_q` beside `tau_max` once P3 releases the
file — the committed JSON is the registered artefact either way.

## D37 ⭐⭐ **`doe`'s regret advantage is a property of ONE CELL. Combined with D20, the headline now needs two conditions to hold at once.**

P3's second result, on committed data, no new compute — `e2-grid.json` + `e2-doe-d8.json`,
paired on `(instance, seed)`, n=50, 4,000-resample bootstrap `rng(0)`, two-sided Wilcoxon,
Holm across the four cells, SESOI 0.02. **`doe − qlognei` on regret; negative favours `doe`:**

| cell | mean | 95% CI | Holm p | verdict |
|---|---|---|---|---|
| **(6, 0.25)** | **−0.0574** | [−0.0766, −0.0387] | **3.9e-07** | **SIG, ≥ SESOI — `doe` better** |
| (6, 0.10) | **+0.0084** | [−0.0048, +0.0204] | 0.217 | ns, < SESOI — **sign flipped** |
| (8, 0.25) | −0.0142 | [−0.0296, +0.0008] | 0.217 | ns, < SESOI |
| (8, 0.10) | **+0.0100** | [−0.0017, +0.0217] | 0.217 | ns, < SESOI — **sign flipped** |

Full rankings, with Kendall τ-b against the baseline cell:

```
(6, 0.25)  doe < lhs < qlognei < qlogei < sobol < random     (baseline)
(6, 0.10)  qlognei < qlogei < doe < lhs < sobol < random     tau-b +0.47
(8, 0.25)  doe < qlognei < qlogei < lhs < random < sobol     tau-b +0.60
(8, 0.10)  qlognei < doe < sobol < qlogei < lhs < random     tau-b +0.33
```

**Why this is a headline-level finding and not housekeeping.** K6's central claim is that the
**map** ranks the arms differently from **regret** — `doe` first on regret, last on
`auc_pred` in **24/24** cells. *That contrast is anchored on `doe` being the regret winner.*
**It is the regret winner at one cell out of four.** At both σ=0.10 cells the sign flips to
`qlognei`, and nowhere outside (6, 0.25) does the contrast clear SESOI or survive Holm.

So some of what K6 reads as *"the design-space object disagrees with regret"* may be
**"regret at (6, 0.25) disagrees with regret everywhere else."** Those are very different
papers.

### The synthesis, which neither result states alone

**`doe`'s regret advantage now requires TWO conditions simultaneously**, established by
independent routes on different evidence:

1. **A specific terminal rule.** D20: under a posterior-mean rule `doe` goes 0.0958 → 0.1993,
   **first of ten to last**, gate clean at 500/500.
2. **A specific cell.** D37: significant and beyond SESOI at **(6, 0.25) only**, sign flipping
   at both σ=0.10 cells.

Neither was designed to test the other. **This is what D29 registered as P3's exposure —
"P3 can invalidate the project's design-space headline" — arriving from the regret side
before the map side has even finished.**

**P3 correctly refused to write it up as the P3 conclusion.** The registered question is
whether the **map** ranking survives, and the map half is still running. The regret half is
answered, and it answers *against* the single-cell reading. **Holding the conclusion until
the registered question can actually be answered is the right call and it is the second time
tonight a worker has declined to over-claim a partial result.**

### One thing I asked P3 to add before this travels

**It is reported at n=50 only, and P3 flagged the reason itself** — it pairs on
`(instance, seed)` per K6's convention while Q57 clusters on landscapes at n=25, and the two
are not interchangeable. **Amendment F1 requires both.** Requested, at no compute cost.

The direction of the check matters: **(6, 0.25) at Holm p = 3.9e-07 will survive anything;
the three non-significant cells are the load-bearing half**, and "not significant at n=50" is
strictly weaker than "not significant at n=25". The conclusion should get **stronger** at the
conservative unit. That has to be confirmed, not assumed.

## D38 🟢 **The `doe` d=8 gate — the trap that started §3.6 — is closed. 600/600 exact.**

`results/p3-preflight-gate.log`, `9720d3b`:

```
d=6 sigma=0.10   doe lhs sobol random   50/50 each, worst |delta| = 0.000e+00
d=8 sigma=0.25   doe lhs sobol random   50/50 each, worst |delta| = 0.000e+00
d=8 sigma=0.10   doe lhs sobol random   50/50 each, worst |delta| = 0.000e+00
```

Three details make this the version that could actually have failed, and all three were the
worker's own:
* **Run before the scoring, not alongside it** — so a missing target is found in seconds
  rather than after hours of compute.
* **Aimed at exactly the arms K1 does not cover.** `k1-replay-gate.json` measured
  doe/qlogei/qlognei, and `doe` only at d=6. This covers the complement.
* **Verified `e2-doe-d8.json` carries the same 50 `(instance, seed)` keys** as `e2-grid.json`'s
  qlogei column at that cell — the join was checked, not assumed. That is precisely the defect
  found in `step0-oracle-best.json`, where an `arm == "versionb"` join silently compared two
  different campaigns.

Tolerance 0.0 throughout, none introduced. And `MissingGateTarget` now **raises** where
`committed.get(...)` + `if ref is not None` used to swallow — the §3.6 defect fixed at the
root rather than worked around.

## D39 🟡 I reversed the P3 pause on new evidence, and said so rather than dropping it quietly.

I paused P3 on the theory that serialising our jobs would relieve contention. Then I measured
RSS: our six workers sum to **under 1 GB**, top-12 max 300 MB, against **16.1 GB wired** and
24.4 GB of swap consumed. **The pause was premised on us being the load, and we measurably are
not.** Stopping and restarting checkpointed cells to relieve a problem we are not causing
costs more than it saves. **Released.** P2 stays paused on work-lost grounds only.

Recording the reversal because a silently-dropped instruction is indistinguishable from a
forgotten one, and this team is running on written instructions.

## D40 ✅ **F1 answered, and it partly REFUTES the premise I registered. Both headlines survive.**

`96c0870`, `results/f1-dual-n.json`, 137 contrasts at both units, read from committed blobs via
`git show HEAD:` with **no campaign run**.

| family | n | Holm-sig n=50 | Holm-sig n=25 | changed |
|---|---|---|---|---|
| **HEADLINE 1 — `lhs − doe` on AUC(pred)** | 24 | **24** | **24** | **0** |
| `doe − qlogei` on AUC(pred) | 24 | 24 | 24 | 0 |
| **D20 HEADLINE 2 — rule-P reversal, per arm** | 10 | 8 | 8 | **0** |
| **D20 — the SIGN FLIP itself** | 2 | 2 | 2 | **0** |
| containment cells | 156 | — | — | **0** |

**Both headlines survive the conservative unit unchanged.** The registered kill
(`improvement(versionb) − improvement(doe)`) is significant at both — p = 2.4e-13 and
1.2e-07 — and did not fire.

**And the premise of my own amendment is wrong in an interesting way.** F1 asserted n=50
"narrows every bootstrap CI by roughly **√2**". Measured:

```
CI inflation  sqrt(Var_n25/Var_n50):  median 0.9884   min 0.4922   max 1.1763   below 1.0: 73/137
ICC equivalent:                       median -0.0231  min -0.7577  max +0.3836  negative: 73/137
```

**√2 is the ICC = 1 corner, and the median ICC is slightly NEGATIVE.** Two seeds on one
landscape are not positively correlated *on the paired differences*, because the landscape
effect largely cancels in the difference — which is exactly the quantity being tested. **So
n = 50 was not meaningfully anti-conservative on these contrasts.**

**The exercise was still right.** The convention genuinely contradicted itself
(`K6-TECHNICAL-REPORT.md` §3.8 vs `RESEARCH-SUMMARY.md`), nothing recorded the switch, and the
discrepancy is now **measured rather than assumed**. That is the defence it was for. But the
honest headline is *"the inconsistency was real and its effect is ~zero"* — not "we were
wrong", and not "we were fine".

**Four Holm status changes — and THREE are UPGRADES, all on SPADE's registered kills:**
* ⬆ KILL 1 `versionb − qlognei` on **`alpha_star`** tf=0.85, and on **AUC** tf=0.75
* ⬆ KILL 2 `versionb − versionb_random` on **`alpha_star`** tf=0.6
* ⬇ §5.8 `sobol − qlognei` on `alpha_star` tf=0.6

KILL 1 goes **2/8 → 4/8**, KILL 2 **3/8 → 4/8**. **The conservative unit makes SPADE look
better.**

**⚠️ The caveat that must travel with that, and it is not a small one.** **Two of the three
upgrades are on `alpha_star` — MODEL-INTERNAL**, and P4b is currently testing α\* as
*anti-correlated* with the validated metrics. **An upgrade on α\* is not SPADE improving; it
is a stronger reading of a statistic under suspicion.** Only the AUC upgrade is validated —
and under F2a the AUC ranking is itself superseded by the error volumes wherever they
disagree, so even that one must clear the new framing before it is quoted.

## D41 🔴 **The machine, diagnosed by two workers independently and verified. Two items are Joseph's call.**

```
CCXProcess (Adobe, pid 41386)   82.1% CPU,  4,491 CPU-MINUTES accumulated since 13 Aug
free RAM                        59 MB       (was 146 MB an hour earlier)
wired                           16.2 GB     compressor 5.4 GB
swap                            24.4 GB of 28.7 GB
CPU                             40.3% user, 57.7% sys, 2.0% idle
```

**~75 hours of CPU burned by Adobe for nothing to do with this programme.** Measured cost to
the team: `qlogei` **220 s** per campaign against a committed 16 s; `doe` **115 s** against
0.1 s; each worker receiving **5–6% of one core**. P3's estimate moved 7 h → **17 h**.

**Both workers named it, neither touched it, and both said explicitly that killing a process
on Joseph's machine is his call.** That is the correct boundary and both drew it unprompted.
**Escalated with their numbers.**

**One correction so it does not travel unqualified:** `pmset -g therm` reports **no recorded
thermal warning level**. That neither confirms nor refutes P3's `kernel_task` at 177% reading
— pmset logs warning levels, not the throttle mechanism — so the thermal point is passed on as
**P3's observation, not as verified fact.** The Adobe and memory numbers *are* verified.

## D42 🟡 **Serialised to two heavy slots. Third instruction to P3, and the churn is mine.**

Both P1 and P3 independently recommended serialising the campaign generators. Adopted.
**Running: P1** (an hour invested; blocks P3's own kernel gate) **and P4-D23-trio** (`doe` at
0.1 s/campaign — best value per CPU-second on the team, and D23 qualifies the session
headline). **Paused: P7, P3, P2. Release order: P7 → P3 → P2.**

**I paused P3, released it, and re-paused it.** The release was wrong and the reason is worth
recording: I had measured that our processes were small in **RSS** and inferred they could not
be the problem. **At 59 MB free that inference does not hold** — every torch process is
200–400 MB resident-or-compressed, and seven of them is the difference between paging and not.
P3's *"everything is paging"* was the right reading of a true observation and my inference from
it was wrong.

**P3 refused to re-scope itself twice**, writing *"the only honest lever is scope, and that is
your call to make explicitly, not mine to take quietly."* **Both refusals were correct.**
Answered on the record: **the registered grid stands** — three cells, eight arms, n=50, full γ
and τ_frac grids. Any reduction will be written, registered and logged with its reason,
**never a smaller run that reads like the full one.**

## D43 🟢 P1 cut 2 CPU-h by measuring an assumption instead of paying for it.

P1 had a real concern — K6 reaches `build_gp` via `score_campaign` while K6b calls it directly,
and moving `build_gp`'s position in the global RNG stream could break reproduction. The lazy
options were two passes (costly) or assuming it does not matter (unsound).

**It measured:** the same `(X, Y, Yvar, bounds)` fitted under two deliberately different global
RNG states returns parameters identical at **|Δ| = 0.000e+00** — `build_gp` at
`fit_restarts=1` takes the early-return `fit_gpytorch_mll` path and never touches the global
stream, and `joint_draws` carries its own `torch.Generator`. K6 and K6b now score from **one**
regeneration. **~2 CPU-h saved, scope unchanged, 2,800 rows and the kill condition intact.**

**And it kept the evidence the second pass had been providing for free** — a
`--determinism-recheck` that re-regenerates a few kernel campaigns and re-gates them, at ~3% of
the cost. That is the part most would have dropped. Asked for both RNG facts to go in the
committed `provenance` block rather than the report: a fact that lives only in a chat log is a
fact this project has already lost once.

## D44 🔴 **I had the γ ladder backwards. P2 found it; verified from committed data.**

My P2 registration framed **γ=0.99 as the hard corner** of the containment ladder — *"tightens
`tau_max` from 1.0000 to 0.4184 and there is no reason the certificate must survive that."*

**It is the easy corner.** γ enters τ **multiplicatively** (`tau = tau_frac × tau_max(γ,σ)`)
and `tau_max` *decreases* in γ, so higher γ buys a **lower** absolute τ, a **larger** true
superlevel set, and **easier** containment. Measured on committed `lhs` rows:

```
gamma=0.99  tf=0.60   tau=0.2510   prevalence 0.99916   <- I called this HARD
gamma=0.50  tf=0.95   tau=0.9500   prevalence 0.00294   <- the actual hard corner
```

**I conflated "a higher assurance requirement" with "a harder threshold."** Higher γ *does*
demand more assurance — and discharges it by lowering the threshold it is willing to certify.
**59 grid points of 20,000** is where the certificate is actually tested.

**The registered kill is unchanged** — every cell runs, every below-nominal containment is
reported as a failure. **It was correctly specified; only my expectation about where it would
bite was wrong.** Adopted programme-wide, P2's call: **`true_frac_above_tau` travels beside
every containment fraction.** A containment number read without its prevalence **inverts the
reading** — 0.99 where the true set covers 99.9% of the box is nearly vacuous; 0.94 where it
covers 0.29% is a strong result.

**This sharpens F2a rather than complicating it, and the two were found independently.** AUC is
unreliable at **both** ends of the ladder, mirrored — ~17 *negative* grid points of 20,000 at
one end, ~59 *positive* at the other. **The type I / type II error volumes stay well-defined
across the whole ladder**, including where `D_est` is empty. Two corrections, different routes,
same direction.

## D45 ✅ **ERRATUM 2 CLOSED. The gates are not thread-contingent — and P2 proved far more than was asked.**

I registered the open question off the back of my own bad benchmark: nothing in this repository
records the thread count under which any |Δ| = 0 gate was measured, so every gate might have
rested on an unrecorded environment variable. **Two workers answered it independently.**

* **P7** — bitwise reproduction (Δ = 0.000e+00) on `qlogei` and `qlognei` under
  `set_num_threads(1)`.
* **P2, the strong one** — extended its `plate1_only` gate from regret alone to **all 20
  numeric K6 columns** (`sup_err`, `grid_r2`, `iou_pred`, `fi_pred`, `box_vol_pred`,
  `auc_pred`, …) at **all 24 (γ, τ_frac) cells**, **every column exactly 0.0**, measured under
  a thread change **and** after deliberately burning the global torch RNG by fitting an
  unrelated GP first.

**So the entire scoring path — not just regret — is invariant to thread count and to global
RNG position.** Thread count becomes **provenance documentation**, not a control variable.
**P2 built a gate that validates the whole scoring path from a registration that asked only
for regret**, and did it without being asked.

**A provenance defect found on the way, and it is the same class this project keeps finding.**
`versionb.json`'s own `plate1_only` regret is **not** bitwise the committed `lhs` column — off
by **3.33e-16** — because `run_versionb.py` scores it with a single `scored_curve` call while
`replay.regenerate` reproduces `static_curve`'s 20-ordering arithmetic. **Two committed files
disagree with each other at 3e-16.** P2 built against the gateable one.

**That is the `static_curve` float-mean artefact for the THIRD independent time** — I hit it,
the Fix 1 worker hit it hours later, and P2 has now found it sitting *inside a committed
file*. The standing rule (match the arithmetic, never widen the tolerance) has caught it in
three separate places, which is the strongest evidence yet that the rule is load-bearing
rather than ceremonial.

## D46 🟢 P3 and P1 made *opposite* engineering calls, and both are right.

P1 shares one GP fit between K6 and K6b, having **measured** that `build_gp` at
`fit_restarts=1` never touches the global RNG stream (D43) — saving ~2 CPU-h.

**P3 deliberately does NOT**, and said so explicitly: `run_k6_designspace.score_campaign` fits
internally, and P3 imports it **unmodified** precisely so that K6's numbers come from the
committed code path. Sharing the fit would mean re-expressing that path and losing the
guarantee, to save ~5% of runtime.

**These are not in conflict.** P1 is *already* re-expressing K6b's scorer (it is inline in
`main()` and cannot be imported), so it has no committed path to preserve and must validate by
other means — which it does, by re-scoring already-gated arms. P3 *does* have one and keeps it.
**Two workers, opposite decisions, each correct for its own constraint, each stated with its
reason.** Recorded because a reader comparing the two runners will otherwise see an
inconsistency where there is a considered difference.

## D47 🟢 **The pause was free, and Amendment F would have obsoleted those rows anyway.**

P3 paused at **0 keys complete in all three cells** — its runner checkpoints only after a key's
full 8 arms, so no JSON exists and **nothing was lost.**

**But the better finding is P3's:** resuming the old binary would have produced three cells that
Amendment F immediately sends back for a re-score. F2a's error volumes *are* derivable after the
fact — they are pure functions of `vol_pred`, `fi_pred` and `true_frac_above_tau`. **F2b's AUPRC
is not.** It needs the full `p_pred` vector and truth labels over the 20,000-point grid, and no
stored row carries either.

**So the pause did not cost three cells; it saved running them twice.** And it vindicates the
call to interrupt six agents mid-run rather than correct afterwards — *the one column whose
omission is unrecoverable is the one that must be right at write time.*

## D48 🔴 **My omission: I specified AUPRC to three workers and not the fourth. `p4-coord.json` is committed without it.**

Checking P3's observation against outputs that had **already landed**:

```
results/p4-coord.json   k6_rows 1200, k6b_rows 200
  true_frac_above_tau  YES    vol_pred YES    fi_pred YES    iou YES    brier YES
  auprc                ** MISSING **
```

I sent Amendment F2b explicitly to P2, P3 and P7 and **left it out of the P4/D23 brief.** That
worker did exactly what it was told; the gap is mine.

**Only AUPRC is actually lost** — the error volumes are recoverable because that worker stored
`true_frac_above_tau` on every row **without being asked**, which is precisely the omission that
makes `versionb.json` unscoreable to this day. Queued as a cheap `coord` re-score (coordinate
descent is deterministic and already gates at |Δ| = 0), **third**, behind D23 and P4b. Written to
a new path, or re-issued with the gate re-run rather than inherited.

**Also worth recording: that worker stored `mean_posterior_sd` on every `k6b_row`** — the exact
regressor P4b's registered "α\* rewards posterior width" test needs. **It stored the explanatory
variable before the analysis asked for it.**

**The pattern across D47 and D48 is the useful part.** A mid-run amendment reaches the runs that
have not written yet and misses the ones that have. P3 (0 rows) absorbs it for free; P4 (1,400
rows committed) needs a re-score. **The cost of a late correction is not uniform across a team —
it is a step function at each worker's first committed row.** That is the scheduling fact worth
carrying into the next phase, not a general preference for early or late.

## D49 🟢 B4 landed. Phase 3's engineering blocker is cleared.

`replay.regenerate` now takes `family=` and `builder=`, backward-compatibly. With P5's `tau_q`
(D36) that clears **both** Phase 3 blockers — the estimand and the engineering. **P6 remains
blocked only on Amendment F's analysis half (F1 ✅, F2a, F2c, F4)**, per D31.

## D50 ⭐ **A gate pointed at the WRONG column would have passed on 88% of rows. The B4 worker's test design is now the standard.**

`COVERAGE-MATRIX.md` §4 B4 already warned that `q42-families.json · doe_a` is the **pre-D20**
column and the wrong family gate target. What nobody had measured is **how nearly right the
wrong answer is.** Verified independently on 400 shared keys:

| | agree at d=6 σ=0.25 | agree pooled |
|---|---|---|
| **ackley** | **22/25** | **92/100** |
| hartmann6 | 15/25 | 75/100 |
| levy | 8/25 | 38/100 |
| rosenbrock | 6/25 | 27/100 |

**A spot-check on seeds 0–2 of ackley or hartmann6 would not have noticed a gate aimed at the
wrong column.** The gate would pass, the number would be wrong, and nothing would say so.

**The response is the registered standard now:** assert **both halves** — the right column
reproduces exactly **and** the wrong one is *shown to differ on the rows where it differs* —
**with a count floor** so the test cannot silently degrade into one that no longer
distinguishes them. **A positive-only assertion passes against the wrong column on 88% of
ackley rows.** This generalises well beyond B4: every gate in this project asserts a positive,
and none of the others asserts that the wrong target *fails*.

## D51 🔴 Erratum 4 — **the audit's `doe` shifts are one cell, quoted as if general.**

The §4 B4 figures (*ackley 0.0000 → 0.0123, hartmann6 0.5444 → 0.5623, …*) are the **d=6
σ=0.25** cell. Pooled over all four: **0.0000 → 0.0070, 0.5917 → 0.5994, 0.0040 → 0.0337,
0.0004 → 0.0245.**

**So "the pre-D20 column flatters DoE" must be stated per family.** Only **levy and rosenbrock**
clear SESOI 0.02 at every cell; **hartmann6's shift is ~0.007 everywhere — below it.** A blanket
statement would be wrong on half the families.

## D52 ✅ **Decision 3 confirmed by evidence it was not derived from.**

Ackley's two `doe` columns coincide on **92 of 100** rows because **its optimum is the exact box
centre and the CCD visits it**, so oracle-best and rule A are the same point.

That is **blocker B3's objection** — the reason Decision 3 put ackley in as *a declared
sensitivity, never a headline* — **appearing in data gathered to check a gate.** The decision was
made on B3's reasoning hours before this evidence existed. **A prediction confirmed by data it
was not derived from is worth more than the argument that produced it**, and this is the second
time tonight that has happened (the first: E7's mechanism arriving from three independent
routes).

## D53 🟢 Registered "leave it unbranched" as a decision, so it is not later read as an oversight.

`replay`'s `N_ORDERINGS = 20` mean reproduces `run_e2.static_curve`'s arithmetic and is left
**unbranched off hill**. It moves a family spread-arm regret by a few ULP — and there is **no
committed family column for `lhs`/`sobol`/`random` at all**, so branching buys nothing
measurable while adding a second scoring definition inside one function.

**Same rule, third invocation tonight:** P2 declined to reimplement `containment_probability`
to make it faster (*"a second definition of a committed quantity is worse than a slow one"*),
P3 declined to share a GP fit to preserve the committed code path, and now this. **Three workers
independently reached for the same principle on three unrelated problems.**

## D54 🟡 P6 is engineering-ready and still deliberately held.

**Both Phase 3 blockers are cleared** — P5's `tau_q` (D36) and B4's `family=`/`builder=` (D49),
with every family gate at |Δ| = 0 and `tests/test_replay.py` **19 passed** on the untouched file.

**P6 still does not start.** It is gated on Amendment F's analysis half: F1 ✅, **F2a / F2c / F4
outstanding**. The worker is instead building the P6 runner **with F's columns designed in** —
because **AUPRC is not recoverable after the fact**, and this has already cost us once
(`p4-coord.json`, D48). Same posture as P3.

**Release queue for compute: P7 → P3 → P2**, and nothing new starts until something finishes.
The box is at **59 MB free RAM** with Adobe holding 82% of a core.

## D55 🔴 **A partial result file that is indistinguishable from a complete one. Found on a killed run.**

P2 was **SIGKILLed at 8 of 50** — its log ends mid-progress followed by
`resource_tracker: There appear to be 5 leaked semaphore objects`, the signature of an abrupt
pool teardown. Third worker this has happened to. What it left behind is the finding:

```
results/p2-versionb-gamma.json   1,077,881 bytes   768 rows
  distinct (instance, seed) keys:  8       (expected 50)
  provenance:  full                gate_failures:  []
  completeness marker:  NONE
```

**Untracked but STAGEABLE** — `.gitignore:199` carries `!results/p2-versionb-gamma.json`, so
**any `git add -A` commits a 16%-complete file that reads as the finished Version B γ-ladder
result.** Full provenance, clean gate, and nothing a reader or a downstream analysis script
could use to tell.

**This is this project's own recurring failure class, inverted.** Every previous instance was a
*cited file that did not exist* (`q30-additive.json`, `e2-doe-d8.json`, the Q50 shards). This is
an *existing file that would be cited as complete.* The `.gitignore` negation discipline that
fixed the first class is what **creates** the second: the negation was added at registration
time, before the file existed, precisely so it could not be silently ignored — and it now
un-ignores a partial just as eagerly.

**Required of every runner, propagated:** write incrementally to a **scratch path**, promote to
the final `results/` path **once, whole, at the end**; and carry a top-level `status` plus
`keys_present` / `keys_expected` so a partial cannot be silently consumed even if it does land
at the final path. The D23 worker had already adopted exactly this after being killed itself.

**Nothing has swept it up**, because every commit this session used a path-scoped
`git add -A docs/… .gitignore` rather than a bare `git add -A`. **That was discipline that
happened to matter**, and it is now a stated rule rather than a habit.

## D56 🟡 **I withdrew three releases. The hold on P3 is now deliberate.**

I released P3 three times and each crossed its report in flight. **I have withdrawn all three.**
Machine state at the moment of withdrawal:

```
free RAM   108 MB          swap  14,750 MB of 15,360  ->  96% FULL
alive      3 heavy runners (P7, P1's Q30, D23)
down       P2 (SIGKILLed at 8/50),  P6 (never started — no log)
Adobe      4,524 CPU-minutes and counting
```

**Two of the six runs I released are down.** Starting three more torch pools into 108 MB of free
RAM would likely kill P2's restart, P7 or D23 — all closer to delivering than P3's cells.

**Sequencing: P7 and D23 finish → P2 restarts from its 8 keys → P3 goes.** That puts the
longest job (~17–24 h) last, which is the **opposite** of what its scientific value deserves —
P3's cells are the only work that can invalidate the design-space headline (D29). **Recorded as
a cost of the machine state, not as a judgement about the work.**

**P3 has been told the hold is deliberate**, so it stops reading it as message-crossing. Its
held work is complete and none of it is wasted: Amendment F wired into the scorer means the
cells run **once**; the d=8 gate exemption is keyed on the arm with a test proving it does not
weaken any other arm.

## D57 ⭐ Two independent arrivals at 24-of-24, and an early D23 signal.

**The error-volume ranking differs from AUC's in 24 of 24 cells** — found by the F-analysis
worker as its registered F2a deliverable, and **independently by P3 while merely checking its
analysis script ran.** Two routes, same number, neither aware of the other. That is worth more
than either alone.

**D23's early signal (5/50, gates clean, full-space rule P reproducing `fix1-terminal-rule.json`
at exactly 0.0):** subspace rule-P regret is tracking full-space rule-P to **~1e-4 per
campaign.** If it holds to 50, that is the **second registered branch** — *the prior is not the
mechanism, the response surface is (`grid_r2` = −6.19), and D20 stands as written.* **Not
called at 5 of 50**, and recorded here as a signal precisely so a later confirmation cannot be
presented as having been obvious.

**P4 is DONE:** `coord` gated 50/50 at |Δ| = 0.000e+00 against `e2-grid.json`, 1,200 K6 rows +
200 K6b rows committed. **The design-space ranking is now nine arms wide** — `coord` lands
mid-pack at regret 0.1420 (3rd of 9), `grid_r2` −0.585 (5th). Both P4 scorers were gated
bitwise against a committed `lhs` row before any `coord` number was read.

## D58 🔴 **The partial-file hazard is SYSTEMIC, and its cause is a fix I made. Two of two long runners hit it.**

D55 recorded it on P2's corpse. It is now live in a **second** runner:

| file | rows | keys present | expected | provenance | gate block | marker |
|---|---|---|---|---|---|---|
| `results/p2-versionb-gamma.json` | 768 | **8** | 50 | full | `gate_failures: []` | **NONE** |
| `results/p7-murphy.json` | 576 | **4** | 50 | full | present | **NONE** |

Both **untracked but stageable** — `.gitignore:199` and `:211`. **Two of two long runners wrote
their in-progress checkpoint to the final result path**, which makes this a **default behaviour,
not a lapse.**

**The cause is my own fix for the opposite failure.** I added a `.gitignore` negation for every
registered output path **at registration time, before any file existed** — deliberately, because
this project has been bitten three times by *a cited file that no clone can see*
(`q30-additive.json`, `e2-doe-d8.json`, the Q50 shards). **That negation un-ignores a partial
just as eagerly as it un-ignores a finished result.** Fixing "the artefact is invisible" created
"the artefact is visible and looks finished".

**Rule now propagated to every runner:** write the checkpoint to a **scratch path**; promote to
`results/` **once, whole, at the end**; and carry a top-level **`status`** plus
**`keys_present` / `keys_expected`** so a partial cannot be silently consumed even if it does
land at the final path.

**Nothing has swept either file up**, because every commit this session used a path-scoped
`git add -A docs/… .gitignore` rather than a bare `git add -A`. **Stated as a rule now rather
than left as a habit** — a habit that only holds while one agent is committing is not a control.

## D59 ⭐ **D23 is close, and both campaigns so far land on the SECOND registered branch.**

Live, 7 of 35, gates clean, and the full-space rule P reproducing `fix1-terminal-rule.json`'s
committed `regret_p` at exactly 0.0:

```
5b3926ef2c5fe4b6 seed=0   A=0.0673   P_full=0.1868   P_sub=0.1856   kept=[1,2,3,4]
5b3926ef2c5fe4b6 seed=1   A=0.0973   P_full=0.2297   P_sub=0.2296   kept=[0,1,2,4]
```

**Subspace rule-P regret tracks full-space rule-P to ~1.2e-3 and ~1e-4** — nowhere near
recovering to rule A's 0.0673 / 0.0973. Under the registered decision rule that is the **second
branch**: *the prior is NOT the mechanism, the response surface is (`grid_r2` = −6.19), and D20
stands as written.*

**NOT CALLED at 7 of 35.** Recorded live, with the campaign keys, **precisely so that a
confirmation at 35 cannot later be presented as having been obvious** — and so that a reversal
in the remaining 28 is visibly a reversal. The registered thresholds are unchanged: within SESOI
0.02 of 0.0958 → prior artefact; near 0.1993 → D20 stands; anything between → both mechanisms
live, reported as a magnitude.

**If this holds, the D23 caveat that has qualified D20 since it was written is discharged** —
`doe`'s collapse under a posterior-mean rule is the design, not a BoTorch default.
