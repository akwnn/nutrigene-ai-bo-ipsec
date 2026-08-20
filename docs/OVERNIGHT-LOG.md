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
