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
