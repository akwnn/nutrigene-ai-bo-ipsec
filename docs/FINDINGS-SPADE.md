# SPADE investigation — findings record

**Started:** 2026-08-20 · **Last updated:** 2026-08-20, mid-run
**Plan:** `docs/superpowers/plans/2026-08-20-spade-go-no-go.md` (body + Amendments A, B, C)
**Registrations:** `docs/OPEN-QUESTIONS.md`, K-series, commits `ef118dd` and `a35b1fc`
**Specs under test:** `docs/ODIN-SPEC.md`, `docs/SPADE-SPEC.md`, reviewed in `docs/ODIN-VERDICT.md`

Every number here is read from a committed file in `results/`. Where a claim is not yet
supported by a finished run it is labelled **RUNNING** and must not be cited.

---

## 1. What we are doing

Testing whether a proposed single-plate method ("SPADE") is worth building, by running the
cheapest experiments that could kill it — **before** building anything.

The proposal: one plate of 48–55 wells, spread across the whole space, produces a
*certified operating region* — a range per ingredient that a manufacturer could put in a
batch record — better than three rounds of classical response-surface work or ten rounds
of Bayesian optimisation.

## 2. Why we are doing it

Three reasons, in order of force.

**The regret column is closed.** Everything in this project so far scores a campaign by
the quality of *one nominated recipe*. On that measure there is nothing left to win.
Search floors are 0.0597 (classical) and 0.0755 (qLogEI); the classical arm already sits
at 0.0958; the whole remaining prize is about 0.01 against a smallest-effect-of-interest
of 0.02. Cutting assay noise by 60% moved the classical identification gap from 0.0361 to
0.0348 — **0.0013**. No method wins there and any spec claiming otherwise gets caught.

**A batch record is not a point.** It is a range for every factor. Nobody in the
BO-versus-DoE comparison literature scores that object. If the two objects rank methods
differently, that is a real finding regardless of which method wins.

**Half the proposal was already refuted or already built.** Q30 measured that doubling
surrogate accuracy moves regret by 0.0015 (p=0.71), and `spread_gp` — the "critical
baseline we must run first" — had already run twice (Q53, Q54). Checking before building
was the whole point.

## 3. Status

| test | question | status |
|---|---|---|
| **Task 1** | can committed campaigns be regenerated? | ✅ **COMPLETE** |
| **K6** | does the design-space ranking differ from regret? | ✅ **COMPLETE** — 9,600 rows, 8 arms |
| **K6b** | joint certification, `alpha*` | ✅ **COMPLETE** — 1,600 rows, 8 arms |
| **Version B** | two-plate SPADE with an LSE round 2 | ❗ **NOT RUN — and it is the actual SPADE**, see §4.8 |
| K0 | does sup-norm or R² govern regret? | not started |
| K1 | what does replicate-identified noise buy? | not started |
| K3 | confirm-and-average vs confirm-and-replace | not started |
| K2 | design lottery | demoted to sensitivity (Amendment B8) |
| K4 | deception detector | not started |
| covariate `R²` | is day-0 confluence predictive? | ✅ **ANSWERED — not recoverable**, see §4.7 |
| cost frontier | is the yield optimum expensive? | ✅ **ANSWERED — no**, see §4.6 |

---

## 4. Results

### 4.1 Task 1 — every committed campaign regenerates exactly ✅

**What we did.** No file in `results/` stores the design points `X` or the measurements
`Y` — the committed grids hold only scalar summaries. So every "re-score the stored
campaigns" test is really a *regenerate-and-score*, and the regeneration has to be proven
faithful before anything is read off it.

**Result.** 500/500 rows. `doe` 100/100, `qlogei` 200/200, `qlognei` 200/200, all at
`worst_abs_delta = 0.000e+00`.

**What it signifies.** The gating policy for every downstream test is **exact**. The plan
pre-registered the possibility that the BO arms would need a tolerance, because Q54 had
measured that path at ~2.5e-06. They do not: Q54's non-reproducibility was in the
*post-hoc rule-C locator* (20 restarts of L-BFGS-B over a fitted posterior mean), not in
the campaign, which `Campaign.seed_everything` pins exactly. Worth having measured rather
than assumed.

### 4.2 K6 — the two rankings disagree in 24 of 24 cells ✅

**Result.** 9,600 rows, 8 arms, 50 instance-seeds, 0 gate failures.

| | ranking |
|---|---|
| simple regret | `doe` 0.0958 < `lhs` 0.1270 < qlogei-add < qlognei < qlogei < qlogei-addonly < sobol < random |
| map quality (AUC) | varies by cell; **`doe` last in 22 of 24** |

**Zero of 24 cells agree with the regret ranking.**

**4.2a The cost of screening, isolated — the cleanest result in the study.**

`lhs` and `doe` are both non-adaptive, both 48 wells, both one round. The only difference
is that `doe` screens 6→4 and confines its response-surface design to a sub-box.

| γ | τ_frac 0.60 | 0.75 | 0.85 | 0.95 |
|---|---|---|---|---|
| 0.50 | +0.112\* | +0.143\* | +0.192\* | +0.221\* |
| 0.70 | +0.110\* | +0.118\* | +0.138\* | +0.179\* |
| 0.80 | +0.112\* | +0.111\* | +0.121\* | +0.143\* |
| 0.90 | +0.113\* | +0.111\* | +0.110\* | +0.117\* |
| 0.95 | +0.113\* | +0.114\* | +0.112\* | +0.111\* |
| 0.99 | +0.105\* | +0.114\* | +0.113\* | +0.114\* |

**Significant in 24 of 24**, favouring the unscreened arm. And it runs exactly opposite to
regret, where `doe` **beats** `lhs` by **+0.0312 [+0.0133, +0.0491], p=0.0028**.

Two arms, one difference, a complete ranking reversal. **Screening buys the better single
recipe and costs the ability to state a range for two of six factors** — which is what a
batch record needs. This needs no new method and does not depend on SPADE winning
anything.

**4.2b Spread versus adaptive — and the acquisition decides it.**

| contrast | wins | losses |
|---|---|---|
| `lhs` vs **qLogEI** | 9/24 | 0/24 |
| `lhs` vs **qLogNEI** | 3/24 | **15/24** |
| `sobol` vs qLogNEI | 0/24 | 0/24 |

**qLogNEI is the strongest arm on the map.** A one-shot spread design beats qLogEI in a
third of cells and never loses to it — but loses to qLogNEI in 15 of 24.

**This is the Q57 trap repeating.** Q57 retracted a Q55 claim for exactly this reason: the
headline held against qLogEI and died against the noisy acquisition. Had only qLogEI been
run here, this would have been recorded as a win.

### 4.3 A1 — the additive kernel does not rescue itself on the map ❌ NULL

**Why we asked.** Q30 measured that doubling held-out R² moved regret by 0.0015 (p=0.71).
If the same campaigns gained on the certification object, that would be the cleanest
figure the project could produce: *doubling accuracy is worth nothing for choosing a point
and a great deal for certifying a region.*

**Result.** It is not there. `qlogei-add` AUC **+0.0143 [−0.0094, +0.0412], p=0.52**;
`qlogei-addonly` **+0.0235 [−0.0059, +0.0542], p=0.13**.

**And a third time, on `alpha*`.** All eight contrasts p > 0.16.

**What it signifies.** The accuracy channel is closed for **all three** deliverables —
regret, map quality, and joint certification. A single-instance smoke test had shown
`alpha*` of 0.30 against 0.03 and it did not survive n=50, which is why it was reported as
a hypothesis at the time.

### 4.4 A prediction of ours was wrong, in the opposite direction 🔴 RETRACTED

**What we claimed.** That nominal-95% certified regions would be *materially
anti-conservative*. The probability was raised from 0.75 to **0.9** on the strength of
E3's measured latent coverage of 0.7644 against nominal 0.95.

**Measured.** False-inclusion rate at nominal 95%, target 0.05:

| arm | predictive | latent |
|---|---|---|
| doe | 0.0046 | 0.0477 |
| qlogei | 0.0002 | 0.0095 |
| qlognei | 0.0000 | 0.0026 |

**Conservative by 10× to 500×.** The opposite of the prediction.

**Why we were wrong.** E3 measures *pointwise coverage of the latent response*. False
inclusion in a *thresholded region* is a different quantity: the region test only fails
where the interval error happens to cross the threshold, and most grid points sit far from
it. We over-read E3. The "free finding that makes K6 worth running either way" is not
there.

### 4.5 The threshold registration had a self-defeating bug, caught before it ran ✅

Peterson's design space uses the *predictive* distribution, so it carries process noise σ
as well as estimation error. Setting estimation error to zero — infinite data — still
requires `mu - tau >= z*sigma`. Under this repo's relative noise that gives a closed-form
ceiling:

```
tau_max = mu_max * (1 - z * sigma_rel)     = 0.589 at sigma_rel=0.25, gamma=0.95
```

**No method certifies above 0.589 at that noise level, at any budget, ever.**

An earlier draft registered absolute thresholds {0.70, 0.80, 0.85, 0.90} — **all four
above the ceiling.** Every arm would have certified nothing and the table would have been
zeros. Re-registered as a *fraction* of `tau_max`. Measured outcome: AUC defined in
**100%** of cells.

**A second reason the fix was right, found later.** The process-noise margin collapses
into that parameterisation exactly — `theta = tau_frac * mu_max` for every gamma, verified
to machine precision at 12 combinations. So the fraction is not a convenience, it is the
natural coordinate for the object.

### 4.6 The cost frontier has no test bed 🔴 WITHDRAWN BEFORE RUNNING

**The proposal.** Recipe cost is known exactly and noiselessly, so the real problem is
"cheapest recipe meeting spec", and the metric is never degenerate.

**Measured.** Cost of the true optimum, as mean coordinate, against a space-filling design
average of 0.500:

| family | `c(x*)` |
|---|---|
| **hill** (the primary oracle) | **0.355** |
| **hartmann6** | **0.345** |
| ackley | 0.500 |
| levy | 0.550 |
| rosenbrock | 0.744 |

**Four of five put the optimum at or below the design average.** Hill is in the cheap half
on *every one* of its six coordinates. Skewed prices do not rescue it — at 100× weight on
one factor, Hill's median cost moves 0.355 → 0.357, because that factor's optimum is low
too. Rosenbrock is not a counterexample: its optimum is 0.744 in *every* coordinate, so it
is symmetric and the cost problem collapses to a 1-D radial profile.

**Why.** The Hill oracle is biphasic — each factor rises then falls, and the interior peak
sits below midrange because too much growth factor is inhibitory. Realistic biology, and
it makes "the optimum is expensive" false on the one family built to resemble the
application.

**What it signifies.** Reported as a negative result: *across five landscape families, the
yield optimum already sits at or below median recipe cost, so cost-constrained
optimisation is not the binding problem the framing assumes.* Rescuing the metric would
mean building an oracle whose optimum is expensive and asymmetric — constructing a test
bed to make the method look good, which is what this project exists to warn against.

### 4.7 The covariate `R²` is not recoverable from existing data ✅ ANSWERED

**Why it matters.** Adjusting for day-0 confluence would lower effective noise via
`sigma_eff = sigma * sqrt(1 - R^2)`, and σ sits inside the certification ceiling. It is
the only lever on the floor in §4.5.

**Result.** `data/lab/derived/image_features.csv` holds 121 images across 9 dates. 58 have
parsable well identifiers, but **no identifier has two dates 4–9 days apart**, and labels
like "well1" are reused across unrelated experiments 10 days apart. There is no
day-0 → day-6 paired series.

**What it signifies.** It needs a *prospective* measurement: image the plate at day 0 and
at endpoint, same wells, recorded per well. Not an analysis task. The registered σ-sweep
already turns it into a lookup when the number arrives.

### 4.8 K6b — the joint guarantee holds, and `alpha*` ranks differently again ✅

**Why.** `{x : LCB(x) >= tau}` is 20,000 *marginal* statements presented as one *regional*
one. A batch record asserts the joint quantity: the probability that **no** certified point
is false. Conservative excursion sets (Chevalier 2013; Azzimonti et al. 2016, 2021) give
that, and `alpha*` — the largest confidence at which a non-empty conservative estimate
exists — is **always defined**, so unlike certified volume it cannot degenerate into a
table of zeros.

**Result.** 1,600 rows, 8 arms, 0 gate failures. `alpha*` ranking matches regret in
**0 of 4** thresholds, and it reverses *within itself*:

| τ_frac | best → worst on `alpha*` |
|---|---|
| 0.60 | **doe 1.000** > qlogei-add 0.981 > qlogei 0.976 > … > lhs 0.958 > sobol 0.948 |
| 0.75 | **doe 0.725** > random 0.652 > lhs 0.629 > … > sobol 0.527 |
| 0.85 | qlogei-addonly 0.296 > random 0.290 > lhs 0.287 > … > **doe 0.213** > sobol 0.175 |
| 0.95 | qlogei-addonly 0.097 > lhs 0.080 > random 0.080 > … > **doe 0.038** > sobol 0.035 |

`doe` is **first** at easy thresholds and **last** at hard ones. Two further oddities worth
a second look: `random` places second or third at three of four thresholds, and `sobol` is
**last at three of four** despite being a low-discrepancy design.

**🔴 RETRACTED — the containment check was circular, and the corrected result inverts it.**

The original version of this section reported achieved containment of 0.972–0.998 at
nominal 0.95 and called the joint guarantee real. **It was a tautology.**
`conservative_estimate` selects the largest set whose containment exceeds α *measured on
`draws`*, and the runner then re-measured containment on **the same draws**. It cannot
fall below nominal by construction: 0 of 1,401 non-empty cases fell below, with minima of
exactly 0.5000 / 0.8008 / 0.9512.

A second defect compounded it: `run_k6b_conservative.py` contained **zero** references to
`kept_factors`, so Amendment B3's refuse-to-certify policy was implemented in K6 only and
every K6b `doe` number certified along axes the CCD never varied.

Both were fixed and **K6b was re-run**. The non-circular test is
`empirical_containment` — against one realisation a set is wholly contained or it is not,
so the guarantee is the **fraction of campaigns contained**, which must be at least α.

> 🔴 **THE TABLE THAT STOOD HERE IS WITHDRAWN (Amendment F4).** Every figure in it was
> **pooled across `tau_frac`** — four thresholds computed on *the same campaign, the same
> posterior and the same 512 draws*, counted as four independent trials. They are not four
> Bernoulli trials, and the pooled `n` (97 / 69 / 51 for `doe`) is fabricated. The withdrawn
> values are printed below **as withdrawals**, so the correction is auditable rather than
> silent, and are replaced by **per-cell** figures.
>
> | arm | α=0.50 | α=0.80 | α=0.95 | |
> |---|---|---|---|---|
> | ~~**doe** (active=4)~~ | ~~0.155~~ | ~~0.420~~ | ~~0.510~~ | withdrawn, pooled |
> | ~~lhs~~ | ~~0.912~~ | ~~1.000~~ | ~~1.000~~ | withdrawn, pooled |
> | ~~sobol~~ | ~~0.959~~ | ~~1.000~~ | ~~1.000~~ | withdrawn, pooled |
> | ~~qlogei~~ | ~~0.884~~ | ~~0.983~~ | ~~1.000~~ | withdrawn, pooled |
> | ~~qlognei~~ | ~~0.923~~ | ~~0.968~~ | ~~0.970~~ | withdrawn, pooled |
> | ~~random~~ | ~~0.646~~ | ~~0.930~~ | ~~1.000~~ | withdrawn, pooled |

**Per-cell, at `tau_frac = 0.60`, containment as a fraction of NON-EMPTY certified sets,
`n` stated because it is not 50 everywhere:**

| arm | α=0.50 | α=0.80 | α=0.95 |
|---|---|---|---|
| **doe** (active=4) | **0 / 50 = 0.000** | **12 / 50 = 0.240** | **25 / 50 = 0.500** |

`doe` reads **worse** per-cell than pooled, not better — the pooling was flattering it.
Identical at n=25.

🔴 **TWO CLAIMS DID NOT SURVIVE UN-POOLING.**

1. **"Seven of eight arms hold at every level" → SIX of eight.** `random` is contained in
   **1 of 7** non-empty sets at `tau_frac = 0.85`, α=0.50, against a nominal 0.50 — at both
   units. Pooling averaged that against 30/50 and 31/39 and reported **`0.646 ok`**. The
   cell is thin (n=7, 86% of regions empty), so this is a failure that is **not
   demonstrated** rather than a demonstrated failure — but *"only one arm fails"* was a
   **pooling artefact**, and the corrected statement is that a second arm's calibration is
   unestablished where its sets are almost all empty.
2. **The B3 "made it worse" comparison is WITHDRAWN ENTIRELY.** *"at α=0.50 the subspace
   restriction makes it worse (0.155 against 0.250 unrestricted)"* — **both sides were
   pooled**, and the unrestricted run was never broken out per cell, so **the comparison
   cannot be made from committed files at all.** It is not corrected here; it is removed.
   Whether B3's subspace restriction helps or hurts `doe`'s calibration is now an **open
   question with no committed evidence either way.**

The starkest evidence for why the circular metric had to go, restated per-cell: at nominal
0.95 the `doe` arm's circular figure reads **0.9997** while its empirical containment at
`tau_frac = 0.60` is **25/50 = 0.500**. The in-sample statistic ranks the failing arm
first. *(The previously quoted 0.5098 was the pooled figure and is withdrawn with the
rest.)*

**Version B measured it too** (`tau_frac=0.60`, the only threshold where all three α
levels are testable):

| arm | α=0.50 | α=0.80 | α=0.95 |
|---|---|---|---|
| versionb | 0.940 (n=50) | 1.000 (n=50) | 1.000 (n=22) |
| plate1_only | 0.940 (n=50) | 1.000 (n=47) | 1.000 (n=16) |
| qlognei | 0.900 (n=50) | 0.979 (n=48) | 0.968 (n=31) |
| **doe** | **0.000 (0 of 50)** | **0.240 (n=50)** | **0.500 (n=50)** |

**At α=0.50 the classical arm's certified region is contained in zero of fifty
campaigns.** SPADE meets nominal in all six of its scorable cells.

**A hard limit on all of this.** Only `doe` has n=50 in every cell; the other arms' α=0.95
rates rest on 16–31 scorable campaigns. **At `tau_frac=0.95` nothing is testable for any
arm at any α** — empty in 50 of 50, fifteen cells of n=0. Cells with n=1–8 are excluded
from claims: a 1.0000 at n=3 has a Wilson lower bound of 0.439.

### 4.9 ❗ WHAT WE HAVE **NOT** TESTED: SPADE is a two-round method

**This qualifies every conclusion above and was missed until late.**

SPADE v2 (Version B) is **two plates**: plate 1 builds the map, **plate 2 spends wells on
the `D_gamma` boundary by batch LSE / parallel SUR**. Its own specification says *"the
certificate is 2 rounds by default; one round is the map, not the batch record."*

Everything in §4.2 and §4.8 is **plate 1 only** — Version A, which changes no sampling.
Running A as the gate was the registered sequencing and was correct. But concluding from
it that *SPADE* fails is judging a two-stage method on stage one, and plate 2 is precisely
the machinery meant to repair a weak certified region.

**Two things follow.**

1. *"A one-shot spread design does not map better than qLogNEI"* is supported.
   *"SPADE does not map better than qLogNEI"* is **not tested**.
2. **The rounds axis has been under-reported throughout.** Every contrast above is at
   equal *wells*. Plate 1 is **1 round against qLogNEI's 10**; SPADE v2 is **2 against
   10**. Even a tie on the map is a 5× rounds result, and rounds were one of the three
   original claims.

---

## 5. Defects found and fixed along the way

Recorded because each one would have produced a plausible wrong number.

| defect | what would have happened |
|---|---|
| **`Yvar` recovered by re-evaluating** | Re-calling `evaluate(X)` draws *fresh noise*, so the variance handed to the model would not be the one the campaign carried. Recomputed from the stored `Y` instead. |
| **`kept_factors` inferred from `X`** | Tempting to find screened-out axes as zero-variance columns. That finds nothing — the screen varies all six factors across its 20 runs and only stage 2 pins them — so a factor the response-surface fit never saw move would have been silently certified. Recorded explicitly instead, with a test asserting both halves. |
| **Quadratic posterior** | `model.posterior(X)` builds the *joint* covariance when only marginals are used: **0.06 s at N=2,000 and 100.60 s at N=20,000**, and 3.2 GB of dense matrix. The first smoke test hit a timeout. Chunked at 2,048, with a test asserting chunk sizes agree to 1e-9. |
| **A 1-ULP gate failure** | The spread arms missed the committed column by 1.110e-16. Cause: `static_curve` averages 20 *identical* curves and the float64 mean of 20 copies of x is not bitwise x. The fix was to reproduce that arithmetic, **not** to raise a tolerance — the gate stays exact. |
| **Self-defeating τ grid** | §4.5. |
| **A wrong test** | The first `tau_max` test hardcoded the textbook z=1.645 against a module using the exact inverse-normal CDF. The test was wrong and the code was right. |

---

## 6. What it all signifies

**The design-space object is genuinely different from regret.** 0 of 24 cells agree on map
quality, 0 of 4 on `alpha*`, with large and consistently significant contrasts. That part
of the thesis is now data.

**Screening is fatal for a design-space deliverable.** 24 of 24 cells, isolated between two
arms that differ in nothing else, and running exactly opposite to regret. This is the
strongest and most portable result of the investigation. It needs no new method, no new
campaign, and does not depend on SPADE winning anything.

**Joint certification works for seven of eight arms.** Under the corrected, non-circular
test, every arm except the screened classical one meets nominal at every level, so a
`(gamma, alpha)` statement built from 48 wells is honest — with plug-in hyperparameters,
which was the flagged risk. The classical arm fails at every level, and at `tau_frac=0.60,
alpha=0.50` its region is contained in **zero of fifty** campaigns.

**And model-internal metrics cannot be trusted alone.** `doe` posts the *highest* `alpha*`
at easy thresholds and the *worst* empirical containment. `alpha*` measures how confident
a model is, not whether that confidence is earned. Only AUC, Brier and empirical
containment are scored against known truth.

**A one-shot spread design does not beat the strongest BO arm on the map.** It beats
qLogEI in 9 of 24 cells and never loses to it, but loses to qLogNEI in 15 of 24. Choosing
only the weaker acquisition would have manufactured a win — the same trap Q57 documented.

**Three supporting arguments are dead**: the cost frontier has no test bed, the
additive-kernel figure is null on all three deliverables, and our own anti-conservatism
prediction is retracted in the opposite direction.

**And the headline question is still open**, because SPADE is a two-round method and only
round one has been run.

---

## 7. What needs to be done

**The decisive one, and it is now the only thing that can settle the question.**

1. **Version B — the two-plate arm.** Plate 1 space-filling, plate 2 batch LSE / parallel
   SUR on the `D_gamma` boundary, decided by the **mean** of first and confirmation
   readings. Comparators: qLogNEI at 10 rounds (the arm that actually beats plate 1), and
   `doe_ascent`. Report **wells and rounds on separate axes**. Registered before it runs.
   * Kill: plate 2 does not close the gap to qLogNEI on map AUC or `alpha*` → SPADE is
     dead and the banked findings are the paper.
   * Kill: plate 2 does not beat **8 random wells** → the SUR machinery is not earning its
     place; that comparison arm stays in.

**Then, in order.**

2. **K0** — does sup-norm error govern regret where R² does not? The only route by which
   the deleted shape-constrained model returns.
3. **K1** — what replicate-identified noise buys, and whether the `Yvar`-to-reading
   coupling explains the measured under-smoothing (fitted lengthscale ÷ true feature width
   is 0.56–0.70).
4. **K3** — confirm-and-average versus confirm-and-replace, the variant Q58 registered as
   unrun.
5. **Explain two oddities from §4.8** — `random` placing second or third on `alpha*`, and
   `sobol` placing last at three of four thresholds. Neither is predicted by any argument
   in the specs, and an unexplained result that favours us is as dangerous as one that
   does not.

**Lab, blocking nothing but deciding what can be claimed.**

6. **Day-0 covariate `R²`** — prospective, per well, day 0 and endpoint.
7. **Reagent cost per well** — decides whether "matched plates, not matched wells" is
   decisive or merely suggestive.

**Explicitly not being done.** NUTS and shape-constrained additive models (closed by Q30
unless K0 reopens it); covariate adjustment as an algorithm stage (needs a real plate); the
55-well budget (cannot be gated against any committed column); TuRBO and OCBA (different
estimand — see the separate plan); the cost frontier (§4.6).

---

# PART II · PHASES 2–4 · findings as at 2026-08-21

## 8. What we are doing in Phases 2–4, and why

**Part I established SPADE's certificate at ONE point:** `hill`, d=6, σ_rel=0.25, τ_frac=0.60 —
empirical containment 0.940 / 1.000 / 1.000. Everything else in this project — 11,450 committed
design-space rows — sits at that same point.

**Phases 2–4 ask three questions the single point cannot answer:**
* **Phase 2 — is the comparison fair?** Version B has one γ, no IoU, no `sup_err`, no `grid_r2`,
  no false-inclusion, and its kernel-arm comparators were never gated.
* **Phase 3 — does anything generalise off Hill?** No design-space metric exists on any other
  landscape family.
* **Phase 4 — does it survive a different dimension or noise level?** Every committed row is
  d=6, σ=0.25.

**All eleven questions were registered — with gates, kill conditions and output paths — in a
single commit (`5c44e6a`) BEFORE any runner file existed.**

---

## 9. Results

### 9.1 ⭐⭐ The headline survived its own strongest challenge

**`doe`'s collapse under a posterior-mean terminal rule is the DESIGN, not a library default.**

Part I's headline (D20) was that the regret ranking **inverts** under a posterior-mean rule:
`doe` 0.0958 → 0.1993 (first of ten to last), SPADE 0.1546 → 0.1003 (sixth to first). **The
caveat that qualified it from the day it was written:** `doe`'s posterior on its two
screened-out axes is prior-driven — the likelihood is flat there, so the lengthscale reverts to
the prior mode 0.5016. If that were the cause, the headline would have been **partly a statement
about a BoTorch default.**

**Measured, n=50, gates clean:**

| | |
|---|---|
| rule A | **0.0958** |
| rule P, full space | **0.1993** |
| **rule P, restricted to `doe`'s own 4 active factors** | **0.1988** |
| distance to the rule-A anchor | **0.1030** — *five times SESOI* |
| distance to the full-space anchor | **0.0005** |
| **share of the collapse removed by the subspace restriction** | **0.5%** |

`regret_p_subspace − regret_a` = +0.1030, Wilcoxon p = 5.76e-08, Holm 9.89e-08.

**Both branches were pre-registered and the result lands cleanly on one, with nothing in
between and no judgement call. It was called at 50, after the live 7-campaign signal was logged
with its campaign keys** — so the prediction is on the record ahead of the result.

### 9.2 ⭐⭐ But `doe`'s regret advantage is a SINGLE-CELL result

`doe − qlognei` on regret, paired, Holm across four cells, **at both sample-size conventions**:

| cell | mean | Holm (n=25) | verdict |
|---|---|---|---|
| **(6, 0.25)** | **−0.0574** | **3.27e-05** | **SIG, ≥ SESOI — `doe` better** |
| (6, 0.10) | **+0.0084** | 0.203 | ns — **sign flipped** |
| (8, 0.25) | −0.0142 | 0.110 | ns |
| (8, 0.10) | **+0.0100** | 0.203 | ns — **sign flipped** |

**The two units agree on all four cells.**

**Why this matters:** K6's central claim is that *the map ranks arms differently from regret* —
`doe` first on regret, last on `auc_pred` in 24/24 cells. **That contrast is anchored on `doe`
being the regret winner.** It is the regret winner at **one cell out of four.**

### 9.3 ⭐ And 59% of that advantage is IDENTIFICATION, not search

Decomposing `regret = oracle-best (search) + identification gap`, `doe − qlognei`:

```
d=6 sigma=0.25   total +0.0574  =  search +0.0237  +  identification +0.0337   (59%)
d=6 sigma=0.10   total -0.0084  =  search -0.0109  +  identification +0.0025
```

**And the asymmetry that explains it — `doe`'s identification gap is noise-invariant while every
BO arm's roughly halves:**

| arm | gap at σ=0.25 | at σ=0.10 | Δ |
|---|---|---|---|
| **`doe`** | 0.0361 | 0.0348 | **−0.0013** |
| `qlogei` | 0.0797 | 0.0378 | −0.0420 |
| `qlognei` | 0.0698 | 0.0373 | −0.0325 |

**Hypothesis (post-hoc, labelled as such):** BO's rule A takes the **argmax of 48 noisy
readings**, so its identification gap carries a winner's-curse term that **scales with σ**.
`doe`'s rule A is a **single confirmation well** at a CCD-fitted optimum — no maximisation over
noise — so its gap does not scale. **`doe`'s advantage is substantially the curse it declines to
pay, not a better design.**

**Three independent routes now give one mechanism**, none designed to test the others: the
advantage inverts under a rule that does not maximise over noise (9.1), survives only at the
highest σ (9.2), and is 59% identification with the only σ-invariant gap (9.3).

### 9.4 The primary metric was the wrong one, and the replacement was free

**AUC is invariant to monotone transformation**, so it scores *ranking*, never calibration —
and a design space is a **calibrated absolute statement**. Mean `grid_r2` is **negative for all
eight arms** (`doe` −6.19 through `lhs` −0.18): the posterior mean is a worse point predictor
than the constant grid mean, everywhere. **AUC cannot see that.** It also misleads under the
class imbalance here — at γ=0.99, τ_frac=0.60 the minority class is ~16 grid points of 20,000.

**Expected type I / type II error volumes** (Azzimonti & Ginsbourger 2018) are what the
excursion-set community actually reports, and they were **derivable from columns already
committed** — validated against the committed `iou_pred` before being registered.

**The registered decision rule FIRED, and not narrowly:**

| | |
|---|---|
| Spearman ρ, error-volume ordering vs AUC ordering | **+0.071** (type II), +0.214 (type I) |
| cells where the rankings differ | **24 of 24** |
| scorable rows | **6,000 of 6,000** vs **2,553** under `fi_pred` |

**The two orderings are close to unrelated. The error-volume ranking is now the reported one;
AUC is retained as superseded.** `doe` is **last of eight** on type II, symmetric difference,
IoU and Brier.

**⚠️ Carried forward:** type I volume **read alone ranks silence first** — an arm certifying the
empty set scores exactly 0. **The symmetric difference is the only honest single scalar.**

### 9.5 A published containment table was withdrawn, and one claim did not survive

§3.7 pooled containment across four `tau_frac` values computed on **the same campaign, the same
posterior and the same 512 draws.** Not four Bernoulli trials. **Eleven pooling sites were
found, not the one flagged** — including the `0.155 / 0.420 / 0.510` triple that *is* the `doe`
headline.

**Two claims did not survive un-pooling:**
1. *"Seven of eight arms hold at every level"* → **six of eight.** `random` is contained in
   **1 of 7** non-empty sets at τ_frac=0.85, α=0.50, against nominal 0.50. Pooling averaged that
   against 30/50 and 31/39 and reported `0.646 ok`. The cell is thin (n=7, 86% empty), so this
   is a failure that is **not demonstrated** — but *"only one arm fails"* was a **pooling
   artefact.**
2. **The B3 "made it worse" comparison is withdrawn entirely** — both sides pooled, and the
   unrestricted run was never broken out per cell, so it **cannot be made from committed files
   at all.** Whether B3's subspace restriction helps or hurts `doe`'s calibration is now an
   **open question with no committed evidence either way.**

**`doe` and SPADE are unaffected.** `doe` reads *worse* per-cell (0/50, 12/50, 25/50 at
τ_frac=0.60). **SPADE's 0.940 / 1.000 / 1.000 was always per-cell and stands, at both units.**

### 9.6 The sample-size convention contradicted itself — and the fix is ~9%, not 41%

`K6-TECHNICAL-REPORT.md` §3.8 uses **n=50**, unit `(instance, seed)`. `RESEARCH-SUMMARY.md`
uses **n=25**, seeds averaged first. **Nothing recorded the switch.** All 137 reported contrasts
were recomputed at both.

**Both headlines survive unchanged** — the 24/24 screening result is 24/24 at n=25, D20's
reversal holds, **0 of 156 containment verdicts move.**

**And the premise was wrong in an instructive way.** "√2" is the **ICC = 1 corner.** Measured
per cell, √(1+ρ) matches the observed SE ratio to within **0.005**:

| cell | ρ | cost of the conservative unit |
|---|---|---|
| (6, 0.25) | +0.192 | **+9.7%** |
| (6, 0.10) | +0.199 | +9.8% |
| **(8, 0.25)** | **−0.168** | **−27.6% — n=25 is the MORE precise unit** |

**Two seeds on one landscape are barely correlated on the paired difference, because the
landscape effect cancels in the difference — which is the quantity being tested.** That is why
no verdict moved.

**⚠️ It does NOT generalise to unpaired quantities.** Raw per-arm `auc_pred` ICC runs **−0.226
to +0.581.** For arm means, containment proportions or prevalence figures, **n=25 stays the
default.**

### 9.7 The two noise levels are not independent samples

`BiphasicOracle` seeds on `seed` alone, never on σ, and `normal(0, s)` is **bitwise**
`s × standard_normal()` off the same stream. **So the σ=0.25 and σ=0.10 cells are ONE noise
realisation at two amplitudes.**

Bitwise-identical regret between the two σ levels, of 50: `lhs` **38**, `doe` **34**, `sobol`
32, `random` 30, `coord` 15 — **`qlogei` 0, `qlognei` 0.** Exactly what the mechanism predicts:
a one-shot design is fixed, so scaling the same draws rarely moves the argmax; adaptive arms
diverge at the first acquisition.

**Effective n for a cross-σ static-arm comparison is 12–27, not 50.** Nothing committed is
invalidated — every campaign is a legitimate draw and every gate holds — but **any analysis
treating the two σ as independent replicates is wrong.**

### 9.8 Cross-family work was impossible as registered, and is now possible

At one `tau_frac`, the true superlevel set covers **0.00000** of the box on ackley and
**0.95550** on rosenbrock. **That is not a comparison.** τ was re-registered as **`tau_q`, a
per-family prevalence quantile** — a *new* estimand; `tau_frac` is untouched.

**Gate: worst |achieved prevalence − p| over 232 rows = 0.000e+00.** Exact. And **ackley becomes
runnable** — its grid max is 0.410, *below every `tau_frac`*, which is why every metric was
`nan`. **`CANNOT RUN` was a property of the threshold, not the family.**

**But `tau_q` equalises prevalence, not certifiability.** τ is now fixed by prevalence while the
noise ceiling `tau_max` still falls with γ, so **111 of 384 cells (28.9%) have τ above the
ceiling** — ackley 0%, hartmann6 2%, levy 50%, **rosenbrock 64%**, ordered by grid range.
**γ=0.50 is clean BY CONSTRUCTION** (z=0 ⇒ `tau_max` = 1.0 exactly; max `tau_q` = 0.98631), so
**the cross-family headline is the γ=0.50 column** and higher γ is reported per family, never
pooled. **The ceiling census is itself a registered result** — it measures how much of each
family's response range is certifiable at a given assurance.

---

## 10. 🔴 What is MISSING — the scope gap, raised by Joseph

**SPADE appears in ONE of the eight Phase 2–4 runs.** Murphy calibration (a *primary*
deliverable), the α\* investigation, the entire cross-family programme, and the three missing
(d, σ) cells all excluded it.

**Cause:** the coverage audit marks Version B **"UNGATABLE — no committed comparator, and never
will be"**, and gating is the organising principle of Phases 2–4. **"Cannot be gated" was
allowed to become "do not run."** They are different: a Version B campaign is
**seed-deterministic and fully scoreable**; it merely has no committed regret column to
reproduce.

**The two worst instances:**
* **α\* IS SPADE's own statistic** — the conservative estimate is the certificate — and the
  α\* investigation omitted every SPADE arm. F1's three Holm upgrades are **all on `alpha_star`,
  all on Version B contrasts**, so the arm whose upgrades are in question was absent from the
  test of the statistic that produced them.
* **Calibration is the metric promoted to primary precisely because AUC cannot see it**, and
  **SPADE's whole claim is a calibrated statement.**

**Fix registered and issued:** all four Version B arms added to the four affected runners,
ungated with a reason per row, `plate1_only` gated where a comparator exists and never
double-counted, and every new row emitting the five columns whose absence from `versionb.json`
has now blocked the error volumes twice.

---

## 11. What it signifies

1. **The headline is stronger than it was**, and survived a challenge that could have reduced it
   to a library default. **The mechanism is the response surface (`grid_r2` = −6.19), not the
   prior.**
2. **But it is narrower than it looked.** `doe`'s advantage needs **a specific terminal rule AND
   a specific (d, σ) cell**, and **59% of it is identification rather than search.** The honest
   claim is: *at high noise, a design that does not maximise over noisy readings avoids a
   winner's curse that adaptive search pays.* That is a statement about **terminal rules**, not
   about DoE versus BO.
3. **The project's primary metric was the least standard one it computes**, and replacing it
   changes the arm ranking in **24 of 24 cells.** The published rankings are superseded.
4. **A published containment table was a pooling artefact**, and one of its two headline claims
   does not survive. **SPADE's own number was always per-cell and is untouched.**
5. **SPADE's certificate has been measured at exactly one (family, d, σ) point in the entire
   project.** Until §10's gap is closed, **nothing in Phases 2–4 tests it anywhere else.**

---

## 12. What needs to be done

**In flight:** Version B arms added to the four runners (§10); the three (d, σ) cells; the
cross-family grid at γ=0.50; the Murphy decomposition; the α\* investigation with SPADE in;
Version B on the full 24-cell γ ladder; the kernel-arm gate and the re-score of 2,800 committed
rows.

**Registered, not yet run:**
* **F3 — the winner's curse inside `CE_α`.** `conservative_estimate` takes a **maximum over 64
  noisy containment estimates on 512 draws**, so it is **anti-conservative by construction.** A
  2048-draw sweep is registered. **This is the project's own optimizer's-curse result operating
  inside its safety metric** — and it may already be visible in `doe`'s circular 0.972–0.998
  against an empirical 0.000 / 0.240 / 0.500.
* **E7's confirmatory arm** — re-score every arm's oracle-best under rule P at both σ. If the
  identification mechanism is right, the gaps should **converge across arms** and `doe`'s
  residual advantage should fall below SESOI.
* **`run_versionb.py` must emit `vol_pred`, `vol_latent`, `fi_pred`, `fi_latent` and
  `true_frac_above_tau`** — a small change that has now blocked the primary metric twice.
* **`k1-replay-gate.json`'s 500 Hill rows** were measured at an unrecorded thread count and
  remain the one unverified corner of the thread-exactness question.

**Open, needing a decision:** whether the B3 subspace comparison is re-run per cell, since it
cannot be made from committed files at all.
