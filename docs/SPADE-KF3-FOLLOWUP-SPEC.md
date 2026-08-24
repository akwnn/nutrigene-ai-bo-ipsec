# SPADE-KF3-FOLLOWUP — frozen specification for the plate-2 mechanism follow-up

**Study ID:** `spade-kf3-followup-2026-08-24`
**Frozen at commit:** *(this file's first commit)*
**Namespace:** every artefact of this study is named `kf3-followup-*`. No file of
`spade-final-2026-08-23` (`docs/SPADE-FINAL-SPEC.md`) is modified, overwritten, deleted, or
re-registered. This document supplements that study; it does not amend it.

> **Frozen before any arm of this follow-up has been run.** Amendments are permitted only as
> numbered errata appended to §12, each committed *before* the result it would affect. An
> amendment made after seeing an outcome it bears on is a protocol violation.

---

## 1. The question, and why the original test can't answer it

`spade-final-2026-08-23`'s KF-3 asked one question — does `spade_cf_m0`'s boundary-targeted
plate 2 beat a random plate 2 — and answered it: **FAIL**, −0.0019 [−0.0062, +0.0026], p=0.41
(`docs/FINDINGS-SPADE-FINAL.md` §17.4). That answer does not say *why*. Three candidate
explanations, each with a different fix, were left conflated in a single null result:

1. **The acquisition criterion is a misaligned proxy.** `batch_lse`'s straddle score targets
   point-level margin ambiguity, not the volume-weighted quantity SPADE is actually scored
   on (symmetric-difference error). A point can have high straddle score and sit in a region
   of the excursion boundary that barely affects the certified volume.
2. **The batch is redundant, not badly aimed.** Greedy selection with a hard `L∞` exclusion
   radius can still cluster picks on one segment of the boundary, wasting wells that a
   diversity-aware selection would have spent elsewhere.
3. **Eight wells in six dimensions is a power problem, not a design problem.** At this
   budget, random sampling may already land near the boundary often enough by sheer volume
   that no criterion can separate itself from chance.

**Question this follow-up answers.** Holding the original study's budget, controls, and
statistical discipline fixed, does correcting (1) and/or (2) let targeted plate-2 sampling
beat random plate-2 sampling where the original criterion could not — and if so, which
correction is responsible?

**The claim this follow-up may support, at most:** that a specific, named replacement for the
acquisition criterion, the batch-diversity mechanism, or both together, clears KF-3's original
bar (≥SESOI on symmetric-difference error, no certificate or calibration cost) in at least one
TARGET or cross-family-stress condition — attributed to the specific mechanism(s) that earned
it, not to "SPADE" generically.

**The claim this follow-up may never support:** that any result here reopens or overturns
`spade-final-2026-08-23`'s KF-3 verdict. That verdict stands as reported. This is a new,
separate registered test of new, separate arms.

---

## 2. New definitions

| symbol | meaning |
|---|---|
| `EV(x)` | expected reduction in the model's own `vorobev_deviation` (posterior symmetric-difference ambiguity) from adding candidate `x`, under the current posterior — **never** computed from ground truth (§2.1, Erratum 1) |
| `λ` | repulsion weight in the diversity-penalized batch score (§2.2) |
| `k_ARD(x, x')` | `exp(−‖(x − x′)/ℓ‖₂²)`, the same ARD lengthscales `ℓ = ard_lengthscales(model)` L1 already uses |
| `K_ERR` | size of the randomly-subsampled candidate shortlist scored by `EV` (frozen: **64**) |
| `K_FANTASY` | number of fantasy draws averaged per candidate (frozen: **8**) |
| `X_er` | `EV(x)`'s own 200-point scoring grid, distinct from the certificate's `X_sub` (frozen: `EV_SCORING_N=200`, Erratum 1) |
| `EV_N_DRAWS` | joint posterior draws used inside `EV(x)`, on `X_er` only (frozen: **128**, Erratum 1) |

### 2.1 `EV(x)` — expected symmetric-difference reduction (a Bect et al. 2012-style SUR criterion)

This is a real, previously-published class of acquisition function for excursion-set
estimation (stepwise uncertainty reduction, "SUR"), not an invented heuristic — chosen because
it targets the *exact* quantity §7.2 of the frozen spec scores SPADE on, unlike the straddle
score, which targets point-level margin.

**Corrected by Erratum 1 (§12) before any implementation — see there for why.** `EV(x)` is
computed **entirely from the model's own posterior, never from ground truth**, using
`boec.vorobev.vorobev_deviation` — "expected symmetric-difference volume between the random
set and its expectation," the model-internal analogue of the study's outcome metric, already
implemented and validated elsewhere in this project.

**`EV(x)` runs on its own small scoring grid, `X_er`, distinct from the certificate's
2,000-point `X_sub`.** `vorobev_deviation` needs a **joint** posterior (a Cholesky
factorization of an `n × n` covariance matrix, `O(n³)`), and doing that at `n=2000` per
fantasy per candidate would make the factorization, not the GP refit, the dominant cost.
`X_er = sobol_grid(dim, EV_SCORING_N=200, seed=GRID_SEED)` — a fixed 200-point Sobol subset,
its own frozen seed, distinct from and never substituted for `X_sub`.

**`EV(x)` is an acquisition-time-only quantity. It is never reported as, and never confused
with, this study's outcome metric.** After plate 2 is chosen, `spade_cf_erroraware` is scored
by the **same, unmodified, full-fidelity** pipeline as every other arm — 4,096 draws, the
2,000-point `X_sub`, `conservative_columns`, `error_volumes` — exactly as the frozen spec's
§7.2/§2.1 require. §2.1 here describes what plate 2's *selection* optimizes, not how any arm's
*result* is measured.

Given the plate-1 (or plate-1 + already-picked plate-2) model and a candidate `x`:

1. Draw `EV_N_DRAWS = 128` joint posterior samples on `X_er` (`split_joint_draws(model, X_er,
   n_draws=128, seed=seed)[0]` — reusing the **first** half of the existing cross-fit joint-draw
   machinery rather than a new sampler; the second half is unused here, since this is not a
   cross-fit quantity). **128, not 4,096:** this is a subordinate, acquisition-time estimate
   scored on a 200-point grid, not the study's primary certificate — a tenth of the primary
   draw count is a deliberately reduced, explicitly named fidelity, not an oversight.
2. `deviation_before = vorobev_deviation(draws, theta)`.
3. Compute `mean(x), sd(x) = model.posterior_mean_and_sd(x)`.
4. Draw `K_FANTASY = 8` fantasy outcomes, deterministically:
   `y_k = mean(x) + sd(x) * Phi_inv((k - 0.5) / K_FANTASY)` for `k = 1..8` — a fixed
   quantile ladder, not a random draw, so `EV(x)` is bitwise reproducible given a seed and
   does not add a second source of Monte Carlo noise on top of the certificate's own draws.
   **Precise language:** because the ladder is fixed quantiles rather than sampled draws,
   `EV(x)` is a **quantile-quadrature approximation of the expectation**, not a Monte Carlo
   estimate — it has no sampling-error confidence interval of its own, and must not be
   described as one in any later methods writeup.
5. For each `y_k`, refit the GP via `build_gp` (`src/boec/surrogate.py`) on the design plus
   `(x, y_k)` — the **same** surrogate constructor every arm in the frozen study uses, not a
   new conditioning implementation. A full refit is slower than an analytic rank-1 update, and
   is the deliberate choice: a new closed-form GP-conditioning function would be a second
   surrogate-inference implementation in a project that has twice been burned by a second
   source of truth for a shared quantity (`docs/FINDINGS-SPADE-FINAL.md` §4.5).
6. Draw `EV_N_DRAWS = 128` joint posterior samples on the **same** `X_er` from the
   fantasy-updated model (same procedure as step 1, same seed — only the model changed), and
   compute `deviation_after_k = vorobev_deviation(draws_k, theta)`.
7. `EV(x) = deviation_before − mean_k(deviation_after_k)`. Higher is better (more expected
   ambiguity removed).

**Candidate shortlist, and why it is a criterion-blind subsample, not a straddle prefilter.**
Computing `EV` on all 4,096 plate-2 candidates is not tractable at this budget. The shortlist
of `K_ERR = 64` is a **uniform random subsample of the frozen Sobol candidate set**
(`sobol_grid(dim, CAND_N=4096, seed=seed)`, same seed as every other arm), selected with an
independent frozen sub-seed — **never** a straddle-score-based prefilter. Prefiltering by
straddle score would make `spade_cf_erroraware` "straddle-shortlisted, error-ranked," which is
a different, weaker claim than "acquisition target replaced," and would misattribute any
result to the wrong mechanism.

**Batch selection for `spade_cf_erroraware`:** greedy over the 64-candidate shortlist,
re-scoring `EV` after each pick against the design-so-far (a fantasy update per step, not a
one-shot ranking), for `q = N_PLATE2 = 8` wells. No exclusion radius and no repulsion term —
this arm isolates the *criterion* only; batch diversity is §2.2's arm.

### 2.2 Diversity-penalized batch selection — repulsion-penalized greedy, not a full DPP

A full Determinantal Point Process MAP batch was considered and rejected for this
registration: it is a materially larger implementation (a new kernel-quality decomposition,
its own numerical stability concerns) for a property a much simpler mechanism already
delivers, and a harder-to-unit-test one. The frozen mechanism:

**`spade_cf_diverse_batch`'s selection rule**, given the *same* `straddle_score(mean, sd,
theta)` `spade_cf_m0` uses (unchanged — this arm isolates *batch selection only*):

1. `bandwidth = exclude = 0.1` — the **same** exclusion radius already registered for
   `spade_cf_m0`'s `batch_lse` call (`src/boec/lse.py`), reused so the new mechanism operates
   at the same registered spatial scale rather than a new, untested one.
2. Greedily select `q = 8` wells maximizing, at each step:
   `straddle_score(x) − λ · max_{x' in already-picked} k_ARD(x, x')`, with the ARD
   lengthscales scaled so `k_ARD` at distance `bandwidth` equals `0.5` (a fixed half-max
   convention, not a free parameter).
3. `λ = 1.0` — frozen. A pick directly on top of an already-chosen well is penalized by one
   full unit of straddle score (effectively excluded, matching the qualitative behaviour of
   the original hard exclusion), decaying smoothly rather than admitting any point outside a
   hard radius regardless of how close it is to the boundary.

**`λ` and the half-max bandwidth convention above are chosen by analogy to the existing hard
exclusion, not calibrated or tuned against any outcome.** Neither has been fit, swept, or
selected by any criterion other than "reproduce the old mechanism's qualitative behaviour at
its own registered spatial scale." A reader must not treat either as an optimized
hyperparameter.

**`spade_cf_erroraware_diverse` (gated, §4)** combines §2.1's criterion with §2.2's selection
rule: greedy on the 64-candidate shortlist maximizing `EV(x) − λ · max k_ARD(x, x')`, same
`λ`.

---

## 3. Compute cost — a firewalled timing pilot, decided before any real campaign runs

`EV(x)` requires a GP refit and a full symmetric-difference scoring pass per fantasy per
candidate: `K_ERR × K_FANTASY = 512` refits per plate-2 well, `×8` wells `= 4,096` refits per
campaign for `spade_cf_erroraware` (and again for `spade_cf_erroraware_diverse`). This is
substantially slower than every other arm in either study, and the actual cost is not known
until measured. A timing pilot is registered here — **before** it is run — with its own
firewall, because an unstructured pilot is a backdoor to peeking at results and tuning `n`,
SESOI, or the criterion itself with the answer already half-known, which is the exact failure
mode this project's discipline exists to prevent.

### 3.1 What the pilot may and may not measure

**Wall-clock time only. Never an outcome.** The pilot runs `spade_cf_erroraware`'s **full**
pipeline — plate-2 selection *and* the standard scoring pass (certificate, symmetric
difference, calibration) — because the real run's cost includes both, and timing only the
selection stage would understate it. But the pilot script:

1. Writes **only** a wall-clock elapsed-seconds line per campaign to
   `results/kf3-followup-pilot-timing.log` — nothing else, no arm name needed since the file
   contains only `spade_cf_erroraware` timings, no outcome columns, no per-gamma or per-alpha
   breakdown.
2. Writes every other output (rows, certificates, symmetric-difference numbers) to
   `results/kf3-followup-pilot-DISCARD.json` — a filename chosen to make the taboo visible in
   a directory listing. This file is added to `.gitignore`, is never opened, never loaded by
   any analysis script, and is deleted once §3.3's decision is committed.
3. **5 campaigns, Hill (C2) only**, matched to the first 5 `(instance, seed)` keys already
   used by `spade_random_plate2`'s committed data (§4.1) — reused seeds, not new ones, so the
   pilot cannot accidentally become a 5-campaign head start on the real comparison even if the
   discard file were opened by mistake.

### 3.2 The decision rule — exact thresholds, fixed now, not at pilot time

Let `T` = the pilot's mean per-campaign wall-clock time (seconds), from
`kf3-followup-pilot-timing.log` only. A single acceptability bar, **2 hours**, applies at
every rung below — no rung is accepted just for landing under a looser bar than the one
before it. Each rung's cost is re-extrapolated from the **same** pilot measurement `T` under
a stated linear-scaling assumption (GP-refit cost scales linearly in `K_FANTASY`; total cost
scales linearly in `n`) — the pilot is not re-run between rungs.

Rungs are tried **in order**, each changing exactly **one thing** relative to the rung
before it, until one lands at or under 2 hours:

| rung | configuration | extrapolated cost | if ≤ 2 h | erratum |
|---|---|---|---|---|
| 0 | `K_FANTASY=8`, `n=100`, SESOI=0.02 (registered) | `T × 100 × 2` | **proceed as registered** | none |
| 1 | `K_FANTASY=4`, `n=100`, SESOI=0.02 | rung 0 cost `× 0.5` | adopt: fantasies only | yes |
| 2 | `K_FANTASY=4`, `n=75`, SESOI=0.02 | rung 1 cost `× 0.75` | adopt: `n` only, SESOI untouched | yes |
| 3 | `K_FANTASY=4`, `n=50`, SESOI=**0.03** (KF-3b/KF-3c only) | rung 1 cost `× 0.5` | adopt: last automatic rung — `n` and SESOI change **together**, and only here | yes |
| — | still > 2 h at rung 3 | — | **do not cut further automatically.** Stop and consult the study owner — a sample size below 50 changes what this follow-up can claim badly enough that it is a scope decision, not a formula | study owner decides |

Rung 2 exists specifically so a sample-size cut and a SESOI widening are never adopted in the
same step unless every single-change rung ahead of it has already failed the 2-hour bar — two
simultaneous changes make the eventual result harder to attribute cleanly, so the ladder never
takes that step before it has to.

**The erratum, when required, cites only `kf3-followup-pilot-timing.log`'s numbers** — never
anything from the discarded outcome file — as its evidence. `spade_cf_diverse_batch` and
`spade_cf_erroraware_diverse` are not piloted separately: `spade_cf_diverse_batch` has no
fantasy-refit cost and is expected to run at ordinary arm speed; `spade_cf_erroraware_diverse`
inherits whatever `K_FANTASY`/`K_ERR` this decision fixes, since it reuses §2.1's criterion
unchanged.

### 3.3 Do the 5 pilot campaigns count toward the real `n`?

**Pre-declared now, not after seeing pilot numbers:** the 5 pilot campaigns are folded into
the final `n` **only if** the decision rule above lands on "proceed exactly as registered" (no
erratum). If any erratum fires — a parameter or `n` changed — the 5 pilot campaigns were run
under different settings than the registered arm and are **discarded entirely**, and the real
run generates its full `n` fresh.

---

## 4. The frozen method arms

| arm | plate 1 | plate 2 criterion | plate 2 selection | tests |
|---|---|---|---|---|
| `spade_cf_erroraware` | identical to `spade_cf_m0` | `EV(x)`, §2.1 | greedy, no repulsion | isolates: does the criterion matter? |
| `spade_cf_diverse_batch` | identical | straddle score (unchanged) | repulsion-penalized greedy, §2.2 | isolates: does batch diversity matter? |
| `spade_cf_erroraware_diverse` | identical | `EV(x)`, §2.1 | repulsion-penalized greedy, §2.2 | **gated** — built and run only if both arms above individually clear KF-3b/KF-3c |

All three: `N_PLATE1 = 40`, `N_PLATE2 = 8`, total **48 wells**, **2 rounds** — identical to
`spade_cf_m0`. **`N_PLATE1`, `N_PLATE2`, and `BUDGET` are not touched for the primary test.**
Budget-scaling is §11, run only after the primary result is in, and never substituted into
the tables below.

`spade_cf_erroraware_diverse` is explicitly **not** run alongside the other two. Building it
before KF-3b/KF-3c resolve would let a combined win hide which mechanism (if either) actually
works — the same mistake §7.3/§7.5 of the frozen spec already guards against for `m0` vs.
`m4`/`m8`.

### 4.1 The control (reused, not re-run)

`spade_random_plate2` from `spade-final-2026-08-23` is the control for all three arms above.
**It is not re-run.** Its existing 100-campaign data at C2 and C3 (`docs/FINDINGS-SPADE-FINAL.md`
§17.4) is reused directly — the campaign seeds, oracle instances, and plate-1 designs for the
new arms below are matched to it exactly (same `(instance, seed)` keys), so the comparison is
paired on the identical landscapes and noise draws the frozen study already spent compute on.

---

## 5. Conditions — reused from the frozen study, not re-derived

| id | family | d | σ_rel | role here |
|---|---|---|---|---|
| **C2** | hill | 6 | 0.10 | TARGET — the condition KF-3 was tested in originally |
| **C3** | hartmann6 | 6 | 0.25 | cross-family stress — the harder, curved-boundary condition the proposal specifically nominates as where targeting should matter more, if it matters at all |

No new feasibility gate is run. C2 and C3's regime classification, `tau_q`, and
`tau_max_by_gamma` are read from the **committed** `results/final-spade-feasibility.json`,
identical to the frozen study — regenerating them here would risk a classification that
disagrees with the one every other arm in the combined table was gated against.

---

## 6. Sample size

**100 campaigns per arm per condition**, matching `spade-final-2026-08-23`'s convention —
subject to §3's compute-cost erratum clause. Paired against `spade_random_plate2`'s existing
100 campaigns at the same `(instance, seed)` keys.

---

## 7. Primary endpoints and decision rules

Identical machinery to the frozen spec §7: symmetric-difference error volume is the primary
map scalar (never type I alone), both terminal rules reported for every arm, SESOI = 0.02,
exact Wilcoxon governs significance with paired bootstrap intervals, `n=25` unpaired unit per
§8's inherited convention.

**The exact "does not worsen" bars, named here rather than left implicit.** The frozen spec's
§7.3 (the original KF-3 conjunction this follows) states "does not produce worse cross-fit
certificate validity" and "does not materially worsen calibration" without repeating a
number at that section — the only place either bar is given a concrete value anywhere in
either study is §7.5's `m>0` conjunction. Both KF-3b and KF-3c below borrow those exact,
already-registered numbers rather than leaving "materially" undefined at read-time:

* **Certificate validity:** every F-CERT-comparable cell that was `PASS` under
  `spade_random_plate2` remains `PASS` (not downgraded to `FAIL`/`INCONCLUSIVE`) under the
  candidate arm — non-inferiority on the ledger's own PASS/FAIL/INCONCLUSIVE verdict, not a
  numeric margin.
* **Calibration:** Murphy calibration does not worsen by more than **0.005** (frozen spec
  §7.5's cap, the only calibration-worsening threshold either study has ever registered).

### 7.1 KF-3b — does the error-volume-aware criterion earn its complexity?

`spade_cf_erroraware` vs. `spade_random_plate2`, same 48-well budget, C2 and C3.

**PASS** only if `spade_cf_erroraware` beats `spade_random_plate2` by ≥ SESOI (0.02) on
symmetric-difference error in **at least one** of C2 or C3, **and** certificate validity does
not downgrade, **and** Murphy calibration does not worsen by more than 0.005 (both bars
above). **FAIL** otherwise: the error-volume-aware criterion is retired.

### 7.2 KF-3c — does diversity-penalized batch selection earn its complexity?

`spade_cf_diverse_batch` vs. `spade_random_plate2`, same setup and bar as KF-3b.

### 7.3 KF-3d — additivity (gated on both KF-3b and KF-3c passing)

Only built and run if **both** KF-3b and KF-3c independently PASS. `spade_cf_erroraware_diverse`
vs. **both** `spade_cf_erroraware` and `spade_cf_diverse_batch` individually — **not** a
win/loss test against random. The question is whether combining the two mechanisms improves
on the better of the two alone by ≥ SESOI (additive), leaves it unchanged (redundant), or
worsens it (interference). All three outcomes are reportable; none is a failure of this
follow-up.

**If neither KF-3b nor KF-3c passes:** KF-3d is **MOOT** — not built, not run, recorded as
such — and the conclusion is that the original KF-3 FAIL reflects a genuine power or
budget-geometry limit (candidate explanation 3, §1), not a fixable proxy or clustering defect.
This is exactly the useful negative result the proposal's own §2/§3 aims at; §11 is where it
gets tested, separately.

---

## 8. Statistical plan

Inherits `spade-final-2026-08-23` §8 in full: exact Wilcoxon, paired bootstrap, `n=25`
unpaired unit, exact Clopper–Pearson / exact binomial tail for any containment reference,
no normal approximation anywhere in certificate inference.

### 8.1 New Holm family

| family | membership |
|---|---|
| **F-KF3FU** | `spade_cf_erroraware` and `spade_cf_diverse_batch` vs. `spade_random_plate2`, at C2 and at C3, symmetric-difference outcome — **exactly 4 tests** (2 arms × 2 conditions), corrected together. |

**Confirmed exhaustive — no fifth comparison exists or is admitted later.** Each of the 4
tests is one arm against `spade_random_plate2` **within** a condition. There is no
C2-vs-C3 contrast for either arm in this family, and none is created by implication: a
condition is a fixed property of the landscape, not a treatment, so "does `spade_cf_erroraware`
perform differently on Hill than on Hartmann6" is not a hypothesis this follow-up tests at
all, in F-KF3FU or anywhere else. `spade_cf_erroraware_diverse`'s additivity test (§7.3) is
descriptive, not hypothesis-tested, and is not added to this family after the fact — nor is
any budget-sensitivity comparison from §11, which has its own separate, non-primary reporting
and is never pooled into a corrected family at all.

F-KF3FU is disjoint from the frozen study's F-CERT/F-BOUND/F-ALLOC/F-MAP families — this
follow-up's tests are never pooled into those already-closed corrections.

---

## 9. Required tests before any result is trusted

Per the corrected design, in order:

1. **`EV(x)` unit tests against a hand-checked toy case.** A 1-D or 2-D toy GP with a known
   posterior and a known threshold, where the expected symmetric-difference reduction at two
   or three candidate points can be computed by hand (or by direct numerical integration) and
   compared to `EV(x)`'s output to a stated tolerance.
2. **A test that `exclusion_radius` and `design_theta`/`tau_q` behaviour is unchanged when the
   acquisition criterion swaps.** `spade_cf_erroraware` must still compute `design_theta`
   identically to `spade_cf_m0` and must not silently redefine what "boundary" means relative
   to the frozen `exclusion_radius`/ARD-lengthscale machinery — a regression test asserting
   these values are byte-identical across the two arms given the same plate-1 data.
3. **A bit-for-bit regression test that `spade_cf_m0` and `spade_random_plate2` reproduce
   their already-committed rows exactly**, run *before* any new arm's data is trusted. If this
   fails, nothing below it is meaningful — the frozen study's own arms must still reproduce
   before a new arm built alongside them can be believed.
4. Unit tests for the repulsion-penalized greedy selection (§2.2): given a toy candidate set
   and a known straddle score, the selected batch must visibly spread across two known modes
   rather than clustering on the higher one, verified against a hand-computed expected pick
   order.

TDD throughout: each test written and confirmed RED before its corresponding implementation,
matching this project's standing convention.

---

## 10. Publication guards

Inherits `spade-final-2026-08-23` §9 in full, plus:

8. **A KF-3d additivity result may not be reported unless both KF-3b and KF-3c are named
   PASS in the same sentence or table** — an additivity claim implies both mechanisms already
   cleared their own bar, and reporting it without that context would misstate what was
   actually shown.
9. **This follow-up's result may not be worded as reopening, overturning, or superseding**
   `spade-final-2026-08-23`'s KF-3 verdict. That verdict is a separate, already-closed,
   already-published finding about a specific named arm (`spade_cf_m0`); this follow-up tests
   different, new arms.

---

## 11. Budget and design-split sensitivity — explicitly non-primary

Two orthogonal appendix arm sets, **run only after §7's primary result is in**, reported in a
clearly labeled secondary appendix table, **never substituted into or averaged with the
primary KF-3b/KF-3c/KF-3d table:**

### 11.1 Unequal-budget sensitivity (tests candidate explanation 3, §1)

`spade_cf_m0` and `spade_random_plate2`, re-run with `N_PLATE1 = 40` fixed and
`N_PLATE2 ∈ {16, 24}` (total budget 56 / 64). **Explicitly and permanently unequal-budget
relative to every arm in both studies.** If targeting separates from random as plate-2 size
grows, the honest finding is a stated break-even well count, not a retraction of KF-3.

### 11.2 Plate-1/plate-2 split sensitivity (tests whether shrinking plate 1 confounds §11.1)

`spade_cf_m0` and `spade_random_plate2` at fixed total budget 48, split
`{32+16, 24+24}` against the registered `40+8`. This isolates whether any effect seen in
§11.1 is attributable to *more plate-2 wells* or to *a smaller, worse plate-1 fit* — its own
question, its own kill condition (**KF-3e**, informal: "plate-1 shrinkage does not by itself
explain a targeting effect"), not folded into §11.1's numbers.

---

## 12. Errata

### 🔴 Erratum 1 — `EV(x)` as first registered would have used ground truth during acquisition

**Committed before any test, any code, or any campaign for this follow-up exists.**

**The defect.** §2.1's first-registered recipe scored each fantasy-updated posterior with
`boec.designspace.predictive_probability_map` and `boec.calibration.error_volumes`.
`error_volumes(vol, fi, prevalence)` requires `prevalence` and `fi` (false-inclusion rate),
both computed **against the true oracle values**. Using them inside plate-2's acquisition
step would mean `spade_cf_erroraware` chooses where to sample by consulting ground truth at
unobserved locations — exactly what §3.1's Local Rule L1 (`docs/SPADE-FINAL-SPEC.md` §3.2)
already forbids by construction, and exactly the failure mode its architectural
guard (a `truth`-free function signature) exists to make structurally impossible elsewhere in
this project. As first registered, `spade_cf_erroraware` would have been comparable to
nothing — a method that peeks is not the method under test.

**The fix.** `EV(x)` is redefined to use `boec.vorobev.vorobev_deviation(draws, theta)` —
"expected symmetric-difference volume between the random set and its expectation," computed
purely from the model's own joint posterior draws. It is the model-internal analogue of the
study's outcome metric, requires no ground truth, and is already implemented and validated
elsewhere in this project (`src/boec/vorobev.py`) — reused, not invented, consistent with the
project's standing avoidance of a second source of truth for a shared quantity.

**A second, dependent correction found while fixing the first.** `vorobev_deviation` needs
**joint** posterior samples, which cost `O(n³)` in grid size to draw (a Cholesky
factorization). Scoring on the certificate's full 2,000-point `X_sub` per fantasy per
candidate would make that factorization, not the GP refit, dominate §3's already-flagged
compute cost. `EV(x)` therefore gets its **own** small, named grid (`X_er`, `EV_SCORING_N=200`)
and its own reduced draw count (`EV_N_DRAWS=128`) — both frozen, both explicitly distinct
from and never substituted for the certificate's registered `X_sub`/`4096` draws, which still
score every arm's actual reported result unchanged.

**What this changes and what it does not.** It changes §2.1's implementation steps and the
definitions table (§2) — both already updated in place above, not left as a stale original
beside a patch. **It does not change** §7.1's decision rule, SESOI, calibration/certificate
bars, the arm's name, or anything about §3's pilot protocol other than confirming the cost
model still centers on the GP-refit count (§3's own arithmetic is unaffected, since `X_er` is
cheap enough that the Cholesky cost is negligible next to `K_ERR × K_FANTASY` refits at
`n=200`). No test, no implementation, and no campaign existed when this was found.
