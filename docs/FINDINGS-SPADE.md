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

### 4.2 K6 — the two rankings disagree in **18 of 18 rankable** cells ✅

*(Read "24 of 24" until 2026-08-22. Six of the 24 cells have no ranking at all — every arm
ties to within 1e-15 — and counting a cell with no ordering as a disagreement is how 24
arose. Denominator differs by metric: **14** for type I, **18** for type II and the symmetric
difference. The committed file said so all along:
`f2-error-volumes.json · decision.rankable_cells = {type_I: 14, type_II: 18, total: 18}`.
**And see §24 — the count itself is near-vacuous and is no longer the evidence.)*

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
0.95 the `doe` arm's circular figure reads a **perfect 1.0000 (n=50)** — *the 0.9997
previously quoted was itself `tau_frac`-pooled over a fabricated n=51, and un-pooling it makes
the contrast starker* — while its empirical containment at
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

**Joint certification works for six of eight arms.** *(This sentence read "seven of eight
… every arm except the screened classical one" and **directly contradicted §9.5 and §12 of
this same file**, both of which already carried the correction. Fixed 2026-08-22.)* Under the
corrected, non-circular test, six of eight arms meet nominal at every level, so a
`(gamma, alpha)` statement built from 48 wells is honest — with plug-in hyperparameters,
which was the flagged risk. The classical arm fails at every level, and at `tau_frac=0.60,
alpha=0.50` its region is contained in **zero of fifty** campaigns. **`random` also fails**,
in one thin cell — contained in **1 of 7** non-empty sets at `tau_frac=0.85, alpha=0.50`.
That cell is 86% empty, so the failure is **not demonstrated**; what is withdrawn is the
claim that *only one* arm fails, which was a pooling artefact.

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
| Spearman ρ, error-volume ordering vs AUC ordering | **+0.071** (type II), +0.214 (type I) — **n = 8 ARMS**, pooled arm-means, p = 0.87 and 0.61. Neither is distinguishable from zero. **Per-cell is a different statistic**: type I **+0.392** [+0.270, +0.514], type II **−0.007** [−0.193, +0.180]. **Neither replicates on P6 — see §24.** |
| cells where the rankings differ | **18 of 18 rankable** (type II, symmetric difference); **14 of 14** (type I). *Not* 24 of 24 — six cells have no ranking. **Near-vacuous as evidence, §24.** |
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
  α\* investigation omitted every SPADE arm *(**no longer true** — P4b was re-run at 12 ranked
  arms including all three; §25)*. F1's three Holm upgrades are **all on Version B contrasts**,
  and **two of three are on `alpha_star`** — the third is on `auc`, a **validated** metric
  (`f1-dual-n.json · status_changes_by_metric_class = {validated: 1, model-internal: 3}`).
  *(This read "all on `alpha_star`, all on Version B contrasts" until 2026-08-22;
  `OPEN-QUESTIONS.md:6585` already said **two** and contradicted `:6469` in the same document.)*
  The point it was making still holds historically: the arm whose upgrades were in question was
  absent from the test of the statistic that produced them.
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
   changes the arm ranking in **18 of 18 rankable cells** (14 of 14 for type I) — *not* 24 of
   24; six cells have no ranking. The published rankings are superseded, but **§24 revises the
   grounds**: the exact-ordering count is near-vacuous and the ρ≈0 finding does not replicate.
4. **A published containment table was a pooling artefact**, and one of its two headline claims
   does not survive. **SPADE's own number was always per-cell and is untouched.**
5. **SPADE's certificate has been measured at exactly one (family, d, σ) point in the entire
   project.** *(The second sentence — "until §10's gap is closed, nothing in Phases 2–4 tests
   it anywhere else" — is **superseded, and the first sentence is STILL TRUE.** The scope gap is
   largely closed for the **map**: Version B arms are now in 5 of 8 runners' sources and 4 of 8
   runners' committed results. **But P6 carries no `alpha_star`, no `ce_*` and no `vorobev_*`
   columns at all**, so the cross-family programme tests SPADE's **map** off Hill and **not its
   certificate.** See §25.)*

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

---

# PART III · OVERNIGHT RESULTS, 2026-08-21 → 22

Four runs completed. **All gates clean.** Result files committed alongside this section.

## 13. ⭐⭐ At (d=6, σ_rel=0.10) the map/regret disagreement REVERSES — and SPADE sweeps the map

**`results/p3-k6-d6-s010.json`** — 14,400 rows, 12 arms, **0 gate failures**, `status: complete`.
**This is the first time SPADE has been scored on the design-space map anywhere except γ=0.50 at
the primary cell.**

| rank | regret (best first) | | AUC(pred), γ=0.50 τ_f=0.60 (best first) |
|---|---|---|---|
| 1 | `qlogei-addonly` 0.0627 | | **`versionb` 0.8441** |
| 2 | `qlogei-add` 0.0791 | | **`versionb_predictive` 0.8417** |
| 3 | `qlognei` 0.0808 | | **`versionb_random` 0.8351** |
| 4 | `qlogei` 0.0874 | | `sobol` 0.8209 |
| 5 | **`doe` 0.0892** | | `qlogei-addonly` 0.8105 |
| 6–7 | `lhs` / `plate1_only` 0.1027 | | `lhs` / `plate1_only` 0.8072 |
| 8–9 | `sobol` / `versionb_random` 0.1210 | | `qlogei` 0.8050 |
| 10 | **`versionb` 0.1261** | | `random` 0.8017 |
| 11 | **`versionb_predictive` 0.1279** | | `qlogei-add` 0.7980 |
| 12 | `random` 0.1693 | | `qlognei` 0.7685 |
| | | | **`doe` 0.5665** ← **LAST, and barely above chance** |

**Two things this establishes:**

1. **The SPADE arms are 9th–11th of 12 on regret and 1st–3rd of 12 on the map.** The two objects
   do not merely rank differently — **they rank SPADE almost exactly opposite.** This is the
   sharpest instance of K6's central claim yet, and it is the first measured at a cell other than
   the primary one.
2. **`doe` is 5th on regret here, not 1st** — confirming §9.2's single-cell finding directly at the
   cell where it was predicted to fail — **and it is LAST on the map at 0.5665**, which is
   *barely above the 0.5 of a coin flip.*

**A free consistency check:** `plate1_only` and `lhs` agree to the printed precision on **both**
regret (0.1027) and AUC (0.8072). They are the same 48-well design; the duplicate guard works.

## 14. 🔴 **THE REGISTERED KILL FIRED. SPADE's certificate FAILS at high assurance.**

**`results/p2-versionb-gamma.json`** — 4,800 rows, **50/50 keys**, **0 gate failures**, and the
`plate1_only` full-width gate at **1,200 rows × 24 columns = 28,800 comparisons, |Δ| = 0.0.**

**The registration said:** *"If containment falls below nominal at any γ × τ_frac × α cell, that is
a failure of the certificate and is reported as one. The committed 0.940/1.000/1.000 at γ=0.50 is
not a prediction for the ladder."*

**`versionb` empirical containment, below nominal in 4 of 72 cells — all at α = 0.95, all at high γ:**

| γ | τ_frac | α | measured | nominal |
|---|---|---|---|---|
| 0.95 | 0.60 | 0.95 | **0.900** | 0.95 |
| 0.99 | 0.60 | 0.95 | **0.840** | 0.95 |
| 0.99 | 0.75 | 0.95 | **0.880** | 0.95 |
| 0.99 | 0.85 | 0.95 | **0.900** | 0.95 |

**And the γ=0.50 row reproduces the committed figures exactly — 0.940 (n=50) / 1.000 (n=50)** —
which is what makes the failures elsewhere credible rather than a scoring change.

**The reading, with Erratum 3's correction attached.** High γ is the **easy** corner of this
ladder, not the hard one: at γ=0.99, τ_frac=0.60 the true set covers **0.99916** of the box. **So
the certificate is failing where the target is nearly the whole space** — which is a worse failure
than the same number at a small target, not a better one.

> **SPADE's certificate holds at the assurance level it was measured at and degrades as assurance
> rises. It cannot currently be claimed at α = 0.95 for γ ≥ 0.95.**

## 15. The α\* question does not resolve — and that is the answer

**`results/p4b-alpha-star-anomaly.json`** — 12 arms, 650/650 keys, `COMPLETE`, `gate_failures: []`.

**Verdict: `NEGATIVE_BUT_ABOVE_THRESHOLD`.** At the **registered primary τ_frac = 0.75**,
twelve arms, n=25: **ρ(α\*, regret) = −0.3916, CI [−0.6643, −0.0839], bootstrap p = 0.0175.**

**The CI excludes zero but ρ does not reach the registered −0.5.** Neither branch fires.

**🔴 Corrected 2026-08-22.** This section headlined **−0.3497 at τ_frac = 0.60** — a real number,
but **not the registered primary**, and quoted without its threshold. That is Erratum 13's exact
defect (*"a single-cell figure quoted without its cell"*) recurring on a different number, and it
propagated onward as "§15's twelve-arm result." **All four thresholds, so no cell can be quoted
alone again:**

| τ_frac | ρ | CI | bootstrap p | CI excludes 0 |
|---|---|---|---|---|
| 0.60 | −0.3497 | [−0.5245, −0.1259] | 0.0075 | yes |
| **0.75 (primary)** | **−0.3916** | **[−0.6643, −0.0839]** | **0.0175** | **yes** |
| 0.85 | **+0.0070** | [−0.4406, +0.3916] | 0.8295 | **no** |
| 0.95 | **+0.0140** | [−0.3147, +0.5105] | 0.7720 | **no** |

**The relationship exists only at the two LOWER thresholds and vanishes completely at the two
higher ones** — sign flips to positive, CI spans zero, p ≈ 0.8. Whatever α\* tracks, it stops
tracking it exactly where the certified regions start going empty. **That is a stronger version
of this section's own conclusion and it was invisible while one threshold stood in for four.**

*(At n=50 the primary's CI is [−0.7063, +0.0350] and does **not** exclude zero, p = 0.081. The
governing unit is n=25 — `ci_width_ratio_n25_over_n50 = 0.783`, so n=25 is the more powerful unit
here, consistent with §9.6. The two units disagree on significance at the primary threshold and
the file records `units_agree: True` only on direction.)*

**And the sign means α\* AGREES with regret** — regret is a loss, so ρ < 0 means arms with higher
α\* have *lower* regret. Against the **symmetric-difference error volume** the correlation runs the
other way at τ_frac = 0.60.

> **α\* tracks quality against regret and badness against the error volumes.** Neither reading
> resolves, and **that is the finding** — reported and not resolved, per Q20 §2.

**Twelve-arm numbers supersede the nine-arm ρ = −0.3667 recorded as provisional in Erratum 11,
which is now CLOSED.** All three structural qualifications survive, and the numbers are:

| Erratum 11's provisional 9-arm figure | 12-arm measurement | survives? |
|---|---|---|
| ρ = −0.3667 | **−0.3916** (primary τ_frac = 0.75) | ✅ direction and rough magnitude |
| leave-one-out drop to −0.0952 | drop `doe` → **−0.2091** | ✅ **`doe` is still the max-leverage arm** — its removal moves ρ furthest toward zero of all twelve — but the leverage is **weaker** than the 9-arm figure implied |
| spread-arm-only +0.5000 | **+0.5000** | ✅ **unchanged exactly** (`lhs`, `random`, `sobol`) |

Full leave-one-out at twelve arms: dropping `random` *strengthens* ρ to **−0.6000**; dropping
`doe` weakens it to −0.2091. **The two extreme arms pull in opposite directions**, which is why
the one-arm-leverage caveat has to travel with every quotation of this number.

## 16. `results/q30-additive.json` exists

Registered in the Phase 2–4 block, **absent from this repository for eight months while being
cited.** The comparator now exists and the kernel arms are gateable — `results/p3-taumax-sensitivity.json`
already gates `qlogei-add` and `qlogei-addonly` against it. **The 2,800-row re-score that decides
whether the committed kernel rows are VALIDATED or WITHDRAWN has not run.**

---

## 17. Test inventory — what guards each result

**Every runner in Phases 2–4 was written test-first**, and the first commit of each task is its
failing test. Counts are of `def test_` in each file.

| test file | tests | what it guards |
|---|---|---|
| `test_calibration.py` | **48** | the Murphy identity to 1e-10, equal-count binning, `average_precision` against `sklearn` to 1e-12, `error_volumes` gated against the committed `iou_pred` column |
| `test_p2_versionb_gamma.py` | **47** | the `plate1_only` full-width gate, per-cell containment, the Vorob'ev cache proven inert at \|Δ\| = 0, partial-file guards |
| `test_p3_cells.py` | **39** | `MissingGateTarget` raising rather than skipping, the d=8 kernel-arm exemption keyed on the arm, per-population ULP bounds, `promote()` re-reading what it publishes |
| `test_p6_families.py` | **39** | family gates at \|Δ\| = 0, the both-halves + count-floor design, `auprc_minority` labels, both degeneracy flags, a constructed unrankable cell |
| `test_p4b_alpha_anomaly.py` | **26** | benefit direction per metric, the bootstrap unit, leave-one-arm-out |
| `test_p1_kernel_gate.py` | **23** | the re-score kill condition, the planted-wrong-comparator failure path |
| `test_replay.py` | **18** | **backward compatibility after the `family=`/`builder=` change** — the 8 pre-existing tests pass byte-identical |
| `test_f2_error_volumes.py` | **16** | the IoU-reproduction identity, per-metric degenerate denominators |
| `test_f1_dual_n.py` | **14** | dual-unit contrasts, the `1 + ICC` identity, the seed-average policy |
| `test_p4_coord.py` / `test_d23_doe_subspace.py` | 9 / 9 | bitwise gates against committed columns |
| `test_p5_tau_quantile.py` | **8** | achieved prevalence to one grid cell, on five families × two dimensions |

**~300 tests added across Phases 2–4**, on top of the 808 the project began with.

**Three test-design lessons that cost something to learn**, all now enforced rather than intended:

1. **A test that asserts only the positive half can pass against the wrong target.** The family
   gate's wrong column agrees with the right one on **88% of ackley rows** — so the test asserts
   the right column reproduces **and** that the wrong one differs, with a **count floor** so it
   cannot decay into one that no longer distinguishes them.
2. **Test the labels a function scores, not the arithmetic beside it.** The AUPRC boundary bug
   (`-truth >= -tau` includes the boundary, putting a point at exactly τ in *both* classes) survived
   a test that checked the tie arithmetic next to the function.
3. **A check must be able to return "still there."** A survivor check on `ppid == parent` is
   structurally blind to orphans, which reparent to PPID 1 — it reported success while three
   processes were alive.

---

# PART IV · CROSS-FAMILY, 2026-08-22

**`results/p6-families.json` · 8 cells · 2,000 campaigns · 48,000 rows · gate failures 0.**
Registered family order (hartmann6 → levy → rosenbrock → ackley) across cells 1 and 2,
`(d=6, σ=0.25)` and `(d=6, σ=0.10)` — the registered fallback pair. Wall clock **2 h 10 m**,
against a registered estimate of ~14 h; the per-arm timings in that estimate were measured
while the machine was running at roughly a tenth speed and are ~5× pessimistic.

---

## 18. 🔴 The IoU identity bound was never a bound — and it halted the programme

P6 halted on hartmann6 seed 24, `qlognei` missing `iou_pred` by **3.331e-16** against the
**2.220e-16** "optimiser" bar. Investigating instead of widening found that **neither
registered scalar is a bound**. Both are `max(observed)` over a few thousand Hill rows.

The two sides of the identity are not comparable pieces of arithmetic:

| side | arithmetic | roundings |
|---|---|---|
| `designspace.iou` | `int(inter) / int(union)` | **one** — exact integer counts |
| `calibration.error_volumes` | `vol*(1-fi)`; `vol+prev-inter`; divide | **five**, on three already-rounded inputs |

and the reconstruction carries two amplifications no constant can cover:
`vol/intersect` (the `1-fi` subtraction loses relative precision as `fi → 1`) and
`(vol+prev)/union` (the union subtraction cancels).

**Measured on pure arithmetic — no oracle, no GP, no dataset, so this evidence does not
depend on having seen the failure — the 1.0-ULP bar breaks on 0.152% of configurations and
the 1.5-ULP bar on 0.011%.** P6 runs ~120k identity checks per family, so the *wider* bar
alone fires on float noise about a dozen times per family.

> **The bars were never population-specific. They were SAMPLE-SIZE specific**, which is worse:
> they silently tighten as the study collects more rows.

This is why the same gate fired on `versionb_random` seed 1 earlier and the miss of *exactly*
3.331e-16 was read as "evidence the proxy is right." It was not a population signature. It was
the arithmetic's ordinary output. **That earlier fix — one decision behind both bound and
message — was correct and is untouched; it repaired a second defect sitting on top of this one.**

**No tolerance was widened.** `iou_identity_bound` is Higham (ASNA §3.1) first-order
propagation evaluated per row from the operands — *tighter* than 2.22e-16 wherever `iou` is
small, looser only where the arithmetic warrants. Zero violations in 60k configurations
(worst err/bound **0.54**) while still firing on **100%** of three injected F2a bugs, which
float noise misses by ~13 orders of magnitude. `IOU_IDENTITY_BOUND` is **kept**: it is the
honest record of what each committed file measured, and it still gates those files in
`tests/test_p2_versionb_gamma.py`. It is simply no longer what gates a family it was never
measured on. Tests 39 → 42.

**Schema note.** 242 of the 250 hartmann6 `(6, 0.25)` campaigns predate the fix and therefore
lack `iou_identity_resid_*` / `iou_identity_bound_*`. Every other cell carries them on every
row. A consumer expecting those columns uniformly will find them absent in that one cell.

---

## 19. ⭐⭐ **Screening is fatal for a design-space deliverable on THREE of four families**

The 24/24 Hill screening result was one family and post-hoc. It now reproduces.

**Mean rank on `total_error_vol_pred`** (the symmetric difference — type I alone ranks silence
first and is never the scalar). `plate1_only` is **excluded**: it carries
`never_rank_separately` because it *is* `lhs` at 48 wells, and counting it makes `lhs` a second
arm. 1 = best of 9. Only non-degenerate, non-above-ceiling cells, paired over the same seeds.

| arm | hartmann6 (27 cells) | levy (10) | rosenbrock (9) | ackley (19) |
|---|---|---|---|---|
| **doe** | **7.59** | **8.50** | **8.22** | **4.32** |
| qlogei | 5.74 | 6.40 | 6.78 | 4.95 |
| qlognei | 6.56 | 7.40 | 7.56 | 6.16 |
| lhs | 4.59 | 3.50 | 3.11 | 4.95 |
| **sobol** | **3.44** | **1.60** | **2.89** | 4.47 |
| random | 4.96 | 2.20 | 4.22 | 6.05 |
| versionb (SPADE) | 4.33 | 4.90 | 3.56 | 4.05 |
| versionb_random | 4.11 | 5.20 | 4.22 | 6.11 |
| versionb_predictive | 3.67 | 5.30 | 4.44 | 3.95 |

**Registered contrast, `doe` vs each arm**, paired on seed: 4,000-resample percentile
bootstrap of paired differences (`default_rng(0)`), two-sided Wilcoxon signed-rank on the same
pairs, **Holm across the cells of each family**, SESOI 0.02. Positive median ⇒ `doe` carries
*more* error ⇒ the arm beats `doe`.

| family | arms beating `doe` | above SESOI | strongest |
|---|---|---|---|
| hartmann6 (n=587) | 6 of 8 | **5** | sobol +0.0250, CI [+0.0179, +0.0310], p_holm 6.9e-37 |
| levy (n=209) | **8 of 8** | **6** | random +0.1628, CI [+0.1058, +0.2167], p_holm 1.6e-32 |
| rosenbrock (n=174) | **8 of 8** | **6** | sobol +0.1718, CI [+0.0948, +0.1992], p_holm 9.8e-28 |
| ackley (n=382) | 6 of 8 | **0** | versionb +0.0074 — *every* effect below SESOI |

### The three things this does NOT say

1. **It is not universal — ackley is a genuine exception**, and it is the one family where
   `doe` ranks best (4.32) and wins 9 of 19 cells. Ackley is excluded from every DoE contrast
   by a decision taken **before** these numbers existed, on the pre-existing ground that the
   screen evaluates the box centre as well as the CCD and so hits ackley's exact optimum
   **7 times**. That exclusion removes the only family where `doe` wins, which is exactly what
   a referee will attack — so the ackley column is reported here in full rather than dropped,
   and the effects there are *all* below SESOI in any case.
2. **On hartmann6 `doe` beats both BO arms** (`qlogei` −0.0004, `qlognei` −0.0072) while losing
   to every spread arm. The failure is specific to spread, not to "everything beats screening."
3. **This is a MAP result, not a regret result.** Q53 has one-shot spread *losing* regret on
   hartmann6 by +0.13 to +0.28, all p_holm ≤ 0.0016. Spread wins the map and loses the search
   on the same family. Both are true and neither supersedes the other.

### `sobol` is the best arm on three of four families

Best mean rank on hartmann6 (3.44), levy (1.60) and rosenbrock (2.89), and the most cell wins
on each. This is the §4.2 anomaly arriving from a third direction: `sobol` already had the best
Brier of any arm (0.1273) and the best empirical containment in the study
(0.959 / 1.000 / 1.000) **while placing last on α\* at three of four thresholds.**
**α\* penalises the arm that three independent measurements now call the best.**

---

## 20. The certifiability ceiling is a result — and it is NOT ordered by grid range

Fresh, independent corroboration of the census, measured at d=6 by the runners themselves:

| family | σ=0.25 | σ=0.10 | d=6 total |
|---|---|---|---|
| ackley | 0/24 | 0/24 | **0%** |
| hartmann6 | 1/24 | 0/24 | **2.1%** |
| levy | 16/24 | 10/24 | **54%** |
| rosenbrock | 18/24 | 13/24 | **65%** |

**58 of 192 (d=6) cells sit above `tau_max`.** This reproduces the committed census
(`results/p6-ceiling-census.json`) from a different code path — the first independent check
that file has had. The census's own headline figures verify: 111/384 = 28.906%, and per family
0% / 2.083% / 50.00% / 63.54%.

**🔴 Correction — "ordered by grid range" is wrong**, and it was repeated into an earlier draft
of this section before being checked. Exceedance is **not** monotone in the family's response
range, and not nearly:

| family | max `tau_q` | grid range (d=6) | exceedance |
|---|---|---|---|
| ackley | 0.16159 | 0.40925 | 0% |
| hartmann6 | 0.56612 | **0.92112** | **2.1%** |
| levy | 0.95996 | 0.93187 | 54% |
| rosenbrock | 0.98631 | **0.85290** | **65%** |

hartmann6 has a *larger* range than rosenbrock and 1/30th the exceedance. What **is** perfectly
monotone — across all five families including hill — is **max `tau_q`**, which is what
`above_ceiling` actually compares against `tau_max`. Since `tau_max` is a function of
`(gamma, sigma)` alone, exceedance can only track where the prevalence quantile sits under
`UnitScaled`. **The ordering variable is the quantile's position, not the family's range.**
The `tau_q` column above is read from the runners' own logs, independently of the census file.

**Two provenance defects in the census, found while checking it:**

1. `above_ceiling` is a **majority vote**, not `tau > tau_max`: `n_above * 2 > len(taus)`
   (`run_p6_families.py`). For the four external families `n_landscapes = 1`, so it collapses to
   the strict test and the 384-cell arithmetic is unaffected. For `hill` (`n_landscapes = 25`) it
   needs ≥13 of 25 — **4 hill rows read `above_ceiling = False` with ≥1 landscape above.** The
   file-wide 480-row figure is therefore not the strict test; the 384-row one is.
2. **All 8 ackley rows in the τ source are `sensitivity: true`**, and `ceiling_census()` applies
   no `sensitivity` filter. The "ackley 0%" column is built entirely from sensitivity rows while
   the other four families' columns are not. The arithmetic is unaffected; the provenance is not
   comparable.

**The consequence is severe and is the honest headline of Part IV: rankability collapses off
Hill.** Of 48 cells per family, only **27** (hartmann6), **19** (ackley), **10** (levy) and
**9** (rosenbrock) are rankable at all — **79% and 81% of levy and rosenbrock cells are
excluded** as degenerate or above-ceiling. Every table above rests on those survivors and says
so. The merge's own count: **48 of 192 cells not rankable on the ranking scalar** (48 arms tie,
48 ranking is prevalence only), and per-metric denominators of 136 / 143 / 144 for type I /
type II / symmetric difference.

Emptiness is the mechanism. Empty predictive regions per arm:

| family | range across arms |
|---|---|
| hartmann6 | 18.0% – 45.7% |
| ackley | 1.2% – 57.8% |
| levy | 64.8% – 74.2% |
| **rosenbrock** | **69.5% – 77.8%** |

*"How much of a response surface is certifiable at a given assurance"* has not been asked
quantitatively in the QbD literature. On two of four families the answer at d=6 is **under a
quarter of it.**

---

## 21. What Part IV does NOT license

* **"Screening is always fatal."** Three of four families, and the fourth reverses it. The
  defensible claim names the families and the metric.
* **Any ackley DoE contrast.** Excluded by pre-registered decision; the design hits the optimum.
* **Ranking anything on levy or rosenbrock without the denominator.** 9 and 10 rankable cells of
  48. Every figure carries its `n` or it is withdrawn.
* **A regret claim.** Part IV scores the map. Regret runs the other way on hartmann6.
* **Cells 3 and 4.** `(8, 0.25)` and `(8, 0.10)` have not run. The registered cell order is what
  makes stopping after cells 1+2 coherent — it does not make it complete.

---

## 22. 🔴 §14's multiplicity correction was computed with a normal approximation, and it does not survive the exact tail

The four measured containment figures in §14 **reproduce exactly**: 0.840, 0.880, 0.900,
0.900, at 42, 44, 45, 45 of 50. Nothing about the measurements is in question.

**The p-values attached to them are not the exact binomial tail.** They are a
continuity-corrected normal approximation to it, and the substitution is recoverable to the
printed precision:

| cell | X/50 | claimed p | **exact** `binom.cdf` | normal-cc | ratio |
|---|---|---|---|---|---|
| γ=0.99, τ_f=0.60 | 42 | 0.0006 | **0.00318834** | 0.00058843 | **5.31×** |
| γ=0.99, τ_f=0.75 | 44 | 0.026 | **0.03777617** | 0.02578793 | 1.45× |
| γ=0.95, τ_f=0.60 | 45 | 0.097 | **0.10361681** | 0.09718296 | 1.07× |
| γ=0.99, τ_f=0.85 | 45 | 0.097 | **0.10361681** | 0.09718296 | 1.07× |

A Binomial(50, 0.95) has `np(1−p) = 2.5` — an order of magnitude below the usual ≥10 rule of
thumb, and the far-left tail is where the approximation is worst.

### What changes

* **Holm ×72 on the leading cell is 0.2296, not 0.043.** The claimed value is exactly
  `72 × 0.00058843 = 0.042367`. With the exact tail it is `72 × 0.00318834 = 0.229561`.
  **No cell survives Holm at α = 0.05 across the 72.**
* **"Roughly seven at p < 0.10 expected by chance" is 2.72**, computed as the true null
  probability that a Binomial(50, 0.95) draw yields an exact tail below 0.10 (0.037776),
  times 72. **The observed count is 2 — below even that.**
* The one-cell survival re-appears only in the **18-cell α=0.95 subfamily** (Holm 0.0574,
  α=0.10) — a smaller family than the 72 the claim invokes, and choosing it after seeing the
  table is not available.

### What does NOT change

**§14's registered kill still fired, exactly as specified.** It is a pre-registered decision
rule on containment falling below nominal, not a hypothesis test, and it does not become
un-fired because the post-hoc inference attached to it was computed with the wrong tail.
What is withdrawn is the *inferential* claim layered on top: **"one of the four failures is
statistically real" is not supported.** The defensible statement is that four cells fall below
nominal and **none is distinguishable from chance across 72 cells.**

### The design cannot detect what it was asked to detect

Discreteness at n=50, p=0.95 sets a floor on what any single cell can achieve:

| X | 40 | 41 | 42 | 43 | 44 | 45 |
|---|---|---|---|---|---|---|
| exact tail p | 0.000159 | 0.000756 | 0.003188 | 0.011786 | 0.037776 | 0.103617 |

**A cell at 45/50 can never reach p < 0.10 no matter what else is true**, and after Holm ×72
even 42/50 cannot reach 0.05. Detecting a sub-nominal certificate at this α with this many
cells needs more seeds per cell, not more cells — which is a design finding, and it should be
settled before any further containment sweep is registered.

---

## 23. What Part IV signifies

### 23.1 The screening result is now a claim about designs, not about Hill

Before today, *"screening is fatal for a design-space deliverable"* rested on one family and was
post-hoc besides — the spread arms were added after the fact. It now holds on **hartmann6, levy
and rosenbrock**, with effects one to two orders of magnitude above SESOI and Holm-adjusted
p-values down to 1e-37. That moves it from an observation about a landscape to a claim about
**what a screening design does to a certified region**: it concentrates its budget on estimating
main effects and leaves the posterior too uncertain, over too much of the box, to certify
anything — and the symmetric difference sees that where regret does not.

**The mechanism and the exception agree.** Ackley reverses the result, and ackley is the family
whose optimum the screen's centre point lands on exactly. When the design happens to sample the
right place, screening is fine. That is not a counterexample to the mechanism; it is the
mechanism stated from the other side, and it is why the claim must name designs rather than
families.

### 23.2 The map and the search disagree, consistently, and both are real

On hartmann6, spread arms **win the map and lose the search**: they beat `doe` on the symmetric
difference by up to +0.0250 while Q53 has one-shot spread losing regret by +0.13 to +0.28. Both
are measured, neither supersedes the other, and the project has now seen this sign split at
(6, 0.10) (§13), under the terminal rule (D20), and across families here.

**The implication for the deliverable is the whole point of the study:** *an arm chosen to find
the optimum is not the arm to choose if the deliverable is a certified region.* A lab that wants
a design space and picks its method from a regret benchmark is reading the wrong column.

### 23.3 `sobol` keeps winning and α\* keeps not noticing

`sobol` now has: the best Brier of any arm (0.1273), the best empirical containment in the study
(0.959 / 1.000 / 1.000), and the best mean rank on the symmetric difference on **three of four
families**. It also places **last on α\* at three of four thresholds.**

§15 reported that α\* agrees with regret and disagrees with the error volumes, and declined to
resolve it. Part IV does not resolve it either, but it narrows it: **α\* is now contradicted by
three independent validated metrics on the arm where it is most confident.** α\* is
model-internal — a functional of the fitted posterior and nothing else — and the rule that a
validated metric beats a model-internal one already decides which to believe. **The open
question is no longer "which is right" but "what is α\* measuring that makes it rank the safest
arm last."**

### 23.4 Most of a response surface is not certifiable, and nobody has said so

**79% and 81% of levy and rosenbrock cells cannot be ranked at all** — degenerate or above the
predictive ceiling — and 64.8–77.8% of predictive regions on those families are empty. At d=6
this is not a corner case; on two of four families it is the majority of the design space.

The QbD literature reports design spaces as though certifiability were free. It is not: it is
bounded by `tau_max(gamma, sigma)`, the bound is algebraic and knowable **before any experiment
is run**, and where the prevalence quantile sits relative to it decides whether the question is
answerable at all. **A design-space claim at an assurance level the noise floor forecloses is
not a weak result; it is not a result.** The census turns that into something a practitioner can
check in advance, which is the most directly usable thing in Part IV.

### 23.5 What the certificate story is now

§14's kill fired and stands. §22 removes the statistical claim layered on it: four cells fall
below nominal and **none is distinguishable from chance across 72**. So the honest position is
**not** "SPADE's certificate is broken" and **not** "the failures were noise" — it is that
**the experiment as designed cannot tell those apart**, because at n=50, p=0.95 and 72 cells the
discreteness floor forecloses significance for anything short of 42/50.

That is a stronger reason to run F3 than the one originally registered. F3 asks whether the
sub-nominal containment is an artefact of the winner's curse inside `CE_alpha`; §22 says the
containment sweep cannot answer it by adding cells. **The two together specify the next
experiment: more draws and more seeds per cell, not a wider grid** — and `conservative_estimate_split`
now exists to cross-check the answer by a route that removes the bias instead of measuring it.

---

## 24. 🔴 The grounds for superseding AUC do not all survive — and one of them inverts on new data

The **conclusion** stands: error volumes supersede AUC. **Two of the three things offered as
evidence for it do not**, and they were the two most quoted.

### 24.1 "The rankings differ in N of N cells" is near-vacuous

Two independent random orderings of 8 arms coincide with probability **1/8! = 1/40,320**; of 9
arms, **1/362,880**. **"0 of 18 exact agreement" is what near-identical metrics would also
produce.** Two orderings that agreed 90% of the time pairwise would still almost never be
*exactly* equal.

`scripts/analyse_f2_error_volumes.py` says this in its own source — *"the two 8-arm orderings are
not literally equal' is nearly uninformative — there are 40,320 of them"* — and the figure was
quoted as a headline anyway, in five places, at the wrong denominator.

**This count is no longer offered as evidence for anything.** It is reported as a descriptive
fact with its denominator and nothing rests on it.

### 24.2 The ρ ≈ 0 finding does not replicate — the sign structure REVERSES

Per-cell Spearman(−AUC, volume) over arms, K6 against the fresh P6 cells:

| metric | K6 (n = 14/18/18) | **P6 (n = 90/92/92)** |
|---|---|---|
| type I | **+0.392** [+0.270, +0.514] | −0.038 [−0.131, +0.054] |
| type II | −0.007 [−0.193, +0.180] | **+0.248** [+0.151, +0.345] |
| symmetric difference | +0.062 [−0.143, +0.267] | **+0.295** [+0.198, +0.393] |

**An exact reversal.** On K6, type I is the metric concordant with AUC and type II / symmetric
difference are indistinguishable from zero. On P6 it is the other way round: type I is null and
type II / symmetric difference are **significantly positive**, CIs excluding zero on 92 cells
across four families.

So *"the two orderings are close to unrelated"* — the claim ρ = +0.071 was carrying — **holds on
K6 and fails on P6.** On four families at d=6 the error volumes and AUC are weakly but reliably
**concordant** on exactly the metrics where K6 said they were unrelated.

**The +0.071 figure itself is verified and was always fragile:** it is `spearmanr` over
**n = 8 arms**, one pair of 8-element orderings, p = 0.87. It was quoted with no `n` and no
interval. At n = 8 it could not have been distinguished from zero in either direction.

### 24.3 What the supersede decision now rests on

Two grounds, both of which survive and neither of which is a rank correlation:

1. **Arm-level reversals — the load-bearing one.** On P6, `doe` is AUC-best in **27 of 92** full
   cells and symmetric-difference-**worst in 36 of 92**. On K6 the same reversal runs the other
   way (`doe` AUC-last in 23 of 24, type I second). A metric that calls the same arm best and
   worst on the same data is not measuring the deliverable. And **type I read alone ranks
   certifying-nothing first** (§9.4), which is a defect of the metric, not of an arm.
2. **Coverage.** Error volumes score **6,000 of 6,000** rows; `fi_pred` scores **2,553**. They
   are defined exactly where `fi` and `iou` are `nan` — and 54–69% of predictive regions are
   empty at some cells, so that is the common case, not the corner.

### 24.4 What this costs

`f2-ce-error-volumes.json` **cannot bear on this at all** — it carries no `auc_pred`, and its
own `like_for_like_across_arms: false` records that B3 scores `doe` on a 4-D active subspace, so
prevalence differs by arm in 198 of 200 cells. It must not be cited for any arm ranking.

**The honest statement is narrower than the one it replaces**, and it is the shape this project
keeps rediscovering: *a result measured on Hill described a property of Hill.* The supersede
decision survives on mechanism — what the metrics do to an empty region, and to an arm that
certifies nothing — not on a correlation that turned out to be family-dependent.

---

## 25. The §10 scope gap is mostly closed — and P6 does NOT close the half that matters

§10 was written when SPADE appeared in **1 of 8** Phase 2–4 runs. That is now stale, and it
matters that the record says so rather than leaving a solved problem marked open.

### 25.1 Where the Version B arms actually are

| runner | Version B in source | in committed results |
|---|---|---|
| `run_p2_versionb_gamma` | ✅ all four | ✅ |
| `run_p3_cells` | ✅ all four | ✅ (6, 0.10) only |
| `run_p4b_alpha_anomaly` | ✅ all four scored, three ranked | ✅ |
| `run_p6_families` | ✅ all four | ✅ **8 cells, today** |
| **`run_p7_murphy`** | ✅ all four | 🔴 **no output exists at all** |
| `run_p4_coord`, `run_p1_kernel_gate`, `run_d23_doe_subspace` | n/a — single-arm or kernel-only, as registered | — |

**5 of 8 in source, 4 of 8 in committed results.** The registered fix's five requirements — arms
added, ungated with a per-row reason, `plate1_only` gated where a comparator exists and never
double-counted, all five error-volume columns emitted, results committed — are satisfied by
`p3`, `p4b` and `p6`.

### 25.2 The α\* half of §10 is simply no longer true

`results/p4b-alpha-star-anomaly.json` carries **`n_arms: 12`**, including `versionb`,
`versionb_random` and `versionb_predictive`, with `plate1_only` scored and excluded from the
ranking. **ρ(α\*, regret) = −0.3916 [−0.6643, −0.0839]** on twelve arms, against the provisional
nine-arm −0.3667. **Errata 11 and 13, both still marked PENDING on the grounds that the twelve-arm
figures did not exist, can be closed from this file.**

*(One stale artefact: all three P4b runs print `50 units x 9 arms` in a hard-coded banner while
the final block reports 12.)*

### 25.3 🔴 **P6 tests SPADE's map off Hill. It does not test SPADE's certificate.**

This limit is easy to misread from Part IV and is stated here explicitly.

`results/p6-families.json` carries **no `alpha_star`, no `ce_contain_*`, no `ce_empirical_*`,
no `vorobev_*`** — zero occurrences of any of them in any checkpoint. P6 measures AUC, AUPRC,
Brier, IoU, false inclusion and the type I / type II / symmetric-difference error volumes. All
map. **The conservative excursion estimate — which IS the SPADE certificate — is not computed
anywhere in the cross-family programme.**

Consequently, and despite everything in Part IV:

> **SPADE's certificate has still been measured at exactly one (family, d, σ) point in the
> entire project: hill, d=6, σ=0.25.** Four families and eight cells later, that sentence is
> unchanged.

P6 also excludes hill, so it does not re-measure the one cell where the certificate exists, and
it is d=6 only.

### 25.4 What is still actually open

| item | state |
|---|---|
| 🔴 **P7 Murphy calibration** | **no results exist.** `results/p7-murphy.json` does not exist; the log holds two aborted runs, **both at the OLD six-arm tuple**, the second logging zero campaigns. `OVERNIGHT-LOG.md` records "P7 is restarting at 10 arms" — **that restart left no trace and no JSON.** The source is at 10 arms; nothing has been run from it. Calibration is the one Brier component AUC cannot see, and SPADE's whole claim is a calibrated statement. |
| 🔴 **P3 cells (8, 0.25) and (8, 0.10)** | never ran. Their logs stop after one campaign at the **pre-fix 8-arm tuple**, killed on the hold order. A re-run now picks up the 12-arm tuple automatically. |
| 🟡 **`results/versionb.json` still lacks the five columns** | `vol_pred`, `vol_latent`, `fi_pred`, `fi_latent`, `true_frac_above_tau` are all absent. The requirement was that *new* rows emit them — satisfied — but the original file was never re-emitted, so **error volumes remain uncomputable from it.** |
| 🟡 **Errata 11 and 13** | closable now; see §25.2. |

**The honest restatement of §10: the map half of the scope gap is closed and the certificate
half is not.** Nothing in Phases 2–4 measures SPADE's calibrated claim anywhere except the one
cell it was born on — which is exactly what §22 says the containment sweep lacks the power to
resolve, and exactly what F3 was registered to attack.

---

## 26. ⭐ Q59: screening is NOT the mechanism. Part IV's caveat 1 is discharged.

`results/q59-map-rescore.json` — 50 campaigns, 2,400 rows, **0 gate misses**: regenerated
`rule_a` and `oracle_best` reproduce the committed Q59 columns at **|Δ| = 0** on all 100
arm-campaigns. Scored through `run_p6_families.map_row`, imported, on the same grid at the
same seed against the same committed `tau_q` table, so every row is comparable to
`results/p6-families.json` cell for cell. Both files use `UnitScaled(Hartmann6())`; that was
checked before any comparison was made.

### The registered decision rule, and which branch fired

Registered before the runner existed: *"`doe_unscreened` still loses the symmetric difference
to the spread arms → screening is **not** the mechanism and Part IV's caveat 1 is
discharged."*

**That branch fired.** Paired on seed, non-degenerate cells only, Holm across the family,
SESOI 0.02. Positive ⇒ the first arm carries **more** error:

| contrast | median | CI | p_holm | |
|---|---|---|---|---|
| `doe_unscreened` − `lhs` | **+0.0295** | — | 4.97e-17 | **> SESOI** |
| `doe_unscreened` − `sobol` | **+0.0327** | — | 1.98e-20 | **> SESOI** |
| `doe_unscreened` − `random` | **+0.0240** | — | 3.76e-17 | **> SESOI** |
| `doe_unscreened` − `versionb` | **+0.0234** | — | 3.59e-04 | **> SESOI** |
| `doe_unscreened` − `qlogei` | **−0.0306** | — | 2.61e-22 | **> SESOI** |

*(Corrected values, `sigma_add` fix. The `versionb` contrast was ns at 0.05 before the fix and
is now significant AND above SESOI — the correction moved it across both bars.)*

**Turning the screen off does not rescue the classical arm's map.** It still loses to every
spread arm by more than SESOI at p_holm < 1e-10.

### 🔴 CORRECTED — the screen accounts for a fifth to a quarter, NOT "a consistent third"

**The numbers first published here were computed with `sigma_add` dropped from `sigma_pred`
and from `Yvar`** — see §32's closing note. The predictive band was 6.5% too narrow at
σ=0.25 and **30.2% too narrow at σ=0.10**, and `sigma_pred` feeds
`predictive_probability_map` directly. Re-run with the fix (50 campaigns, 2,400 rows, **0 gate
misses**):

| against | screened | unscreened | closed | *(as first published)* |
|---|---|---|---|---|
| `lhs` | +0.0412 | +0.0295 | **28.4%** | *30.5%* |
| `sobol` | +0.0408 | +0.0327 | **19.8%** | *31.3%* |
| `random` | +0.0305 | +0.0240 | **21.1%** | *27.7%* |

**The "consistent ~30%, three times" claim is WITHDRAWN. It was an artefact of the bug.** The
corrected range is **19.8–28.4%** — a fifth to a quarter, and *not* strikingly consistent. I
read a pattern into three numbers that the defect had made agree.

The conclusion is unchanged and slightly strengthened: **the 6→4 cut costs the classical arm
roughly a fifth to a quarter of its map deficit; the response-surface model costs the rest.**
Every corrected contrast is larger than the buggy one, so `doe` looks *worse* against the
correct wider band, not better.

### The disagreement the registration requires me to report rather than resolve

`doe_unscreened` − `doe_screened`: **median +0.0036, CI [−0.0029, +0.0091] spanning zero,
Wilcoxon p_holm = 1.22e-04.** And the **means run the other way**: 0.3265 unscreened against
0.3607 screened.

Median and mean have **opposite signs**, so the paired differences are strongly skewed —
unscreened is better on average and marginally worse at the median. Per Q20 §2 the Wilcoxon
governs yes/no and the bootstrap reports magnitude, and **disagreements are reported, not
resolved.** The within-arm comparison is therefore *not* the load-bearing one; the
cross-arm contrasts above are, and they are unambiguous.

### And `doe` beats both BO arms on the map here too

`doe_unscreened` − `qlogei` = **−0.0376**, `doe_screened` − `qlogei` = −0.0182, both
significant. §19 found exactly this on hartmann6 at d=6 — `doe` beats the BO arms on the map
while losing to every spread arm — and it reproduces on an arm built by a different runner.
**The failure is specific to spread designs, not to "everything beats screening."**

### What cannot be reached, by arithmetic

**d=8 can never have this confound isolated.** A second-order model needs `C(d+2,2)` terms —
28 at d=6, **45 at d=8** — and no face-centred CCD lands on 48 wells at d=8; the only design
small enough carries 35 runs for 45 parameters. **An unscreened classical pipeline does not
exist at d=8 within the shared budget**, which is the reason the 6→4 screen exists at all.
Part IV's d=8 cells inherit the confound permanently, and no future run can remove it.

---

## 27. 🔴⭐ THE SCOPE GAP IS CLOSED — and calibration does not flatter SPADE

`results/p7-murphy.json` — **500 campaigns, 12,000 rows, all 10 arms including all four
Version B arms.** P7 had produced nothing at all before today: its only two logged runs were
at the **old six-arm tuple** and the second logged zero campaigns, so the handoff's "8/50" was
really **0/50**. It has now run at the registered arm set.

**This is what §10 was blocking.** The Murphy decomposition was promoted to primary *precisely
because AUC cannot see calibration*, and SPADE's entire claim — *"this region holds at
assurance γ"* — is a calibrated statement. It had been run on every arm except the one making
that claim. Not any more.

`Brier = calibration − refinement + uncertainty`, verified on **all 12,000 rows: 0 violations,
worst residual 2.220e-16.** Calibration is reliability (**lower is better**); refinement is
resolution (**higher is better**).

### The result

Predictive map, non-degenerate cells, `plate1_only` excluded:

| arm | calibration | rank | refinement | rank | Brier | AUC |
|---|---|---|---|---|---|---|
| `doe` | **0.22959** | **9** | 0.00235 | **9** | 0.3367 | 0.5960 |
| `qlogei` | 0.03366 | 4 | 0.00996 | 7 | 0.1331 | 0.7005 |
| `qlognei` | 0.04425 | 8 | 0.01261 | 4 | 0.1411 | 0.7392 |
| `lhs` | 0.03034 | 3 | 0.01175 | 5 | 0.1280 | 0.7229 |
| **`sobol`** | **0.02893** | **1** | 0.01142 | 6 | **0.1269** | 0.7270 |
| `random` | 0.03032 | 2 | 0.00900 | 8 | 0.1307 | 0.6884 |
| `versionb` | 0.03593 | **6** | **0.01506** | **1** | 0.1303 | **0.7583** |
| `versionb_random` | 0.03846 | **7** | 0.01288 | 3 | 0.1350 | 0.7442 |
| `versionb_predictive` | 0.03532 | **5** | 0.01436 | 2 | 0.1304 | 0.7529 |

### 27.1 SPADE is the sharpest and it is not the best calibrated

**SPADE takes ranks 1, 2 and 3 on refinement and ranks 5, 6 and 7 of 9 on calibration.** Its
regions are the most *informative* in the study and its probabilities are *below average* in
reliability.

**And AUC ranks `versionb` FIRST (0.7583).** So on the very cell where the two metrics can
disagree, they do: **the metric that cannot see calibration puts SPADE at the top, and
calibration puts it in the bottom half.** The Murphy split was promoted to primary for exactly
this reason, and the first thing it does with SPADE in scope is catch it.

**This is not a kill.** SPADE's calibration (0.0353–0.0385) sits in the same band as every
other non-`doe` arm (0.0289–0.0443), and it wins refinement outright. The honest statement is
that **SPADE buys sharpness and does not buy reliability**, and any claim resting on the
calibrated half needs that said beside it.

### 27.2 `doe` is not merely worst — it is off the scale

`doe`'s calibration is **0.22959 against 0.04425 for the next worst: 5.2× worse than any other
arm and 7.9× worse than the best.** It is also last on refinement. **A single arm accounts for
almost the entire spread of the metric**, and every other arm sits inside a band a tenth its
width. Alongside §19 and §26 this is the strongest single indictment of the classical pipeline
in the study, and it is on the metric the RSM community would itself nominate.

### 27.3 `sobol` wins a FOURTH validated metric while α\* ranks it last

`sobol` is now **best on calibration**, on top of best Brier, best empirical containment, and
best mean symmetric-difference rank on three of four families (§23.3) — while placing **last on
α\* at three of four thresholds**.

**Four independent validated metrics, one model-internal metric, and they point in opposite
directions on the same arm.** §15 declined to resolve α\*; §24 removed one of the grounds for
that refusal. **This removes the last reason to treat it as unresolved** — see §28.

### 27.4 The registered A5 check fired

*"The two rankings differ at **23 of 24** predictive-map cells (24 of 24 latent), and **6 of
371** inverted pairs survive Holm at the conservative unit n=25 (6 at n=50)."*

Refinement and Brier rank the arms differently almost everywhere, with a Spearman ρ across
cells of **min −0.283, median −0.075, max +1.000** and **371 of 864 pair inversions**. Reporting
Brier alone hides which half of it an arm is winning — which is the whole argument for the
decomposition, now measured rather than asserted.

---

## 28. ⭐ α\* DECLARED: it is not a metric of certificate quality

§15 reported the α\* question and declined to resolve it, correctly, on the evidence then
available. Three things have changed: §24 removed one of the grounds for the refusal (the
ρ≈0 finding does not replicate), §25 put SPADE inside the α\* investigation for the first
time, and §27 added **calibration** — the one validated metric that speaks directly to what a
certificate claims. **Option (a), declare, is taken and registered.**

### The table that decides it

α\* and calibration, **the same cell** (hill, d=6, σ=0.25), 9 arms, `plate1_only` excluded:

| arm | α\* | rank | calibration | rank | Brier | rank | regret | rank |
|---|---|---|---|---|---|---|---|---|
| **`doe`** | **0.7875** | **1** | **0.22959** | **9** | 0.3367 | 9 | 0.0958 | 1 |
| `versionb` | 0.6908 | 2 | 0.03593 | 6 | 0.1303 | 3 | 0.1546 | 5 |
| `versionb_predictive` | 0.6861 | 3 | 0.03532 | 5 | 0.1304 | 4 | 0.1510 | 3 |
| `random` | 0.6521 | 4 | 0.03032 | 2 | 0.1307 | 5 | 0.2216 | 9 |
| `lhs` | 0.6291 | 5 | 0.03034 | 3 | 0.1280 | 2 | 0.1270 | 2 |
| `qlognei` | 0.6055 | 6 | 0.04425 | 8 | 0.1411 | 8 | 0.1532 | 4 |
| `versionb_random` | 0.6054 | 7 | 0.03846 | 7 | 0.1350 | 7 | 0.1638 | 7 |
| `qlogei` | 0.5968 | 8 | 0.03366 | 4 | 0.1331 | 6 | 0.1553 | 6 |
| **`sobol`** | **0.5275** | **9** | **0.02893** | **1** | **0.1269** | **1** | 0.1724 | 8 |

**The two extremes are exactly inverted.** α\* ranks `doe` **first** — an arm whose calibration
is **5.2× worse than any other arm in the study** and which is last on refinement, last on
Brier, and worst-or-near on the symmetric difference. α\* ranks `sobol` **last** — the arm that
is first on calibration, first on Brier, first on empirical containment, and first on mean
symmetric-difference rank on three of four families.

### What it is actually tracking

| against | Spearman ρ | reads as |
|---|---|---|
| calibration (lower better) | **+0.4667** (p = 0.21) | α\* tracks **badness** |
| Brier (lower better) | **+0.2333** (p = 0.55) | α\* tracks **badness** |
| regret (lower better) | **−0.5667** (p = 0.11) | α\* tracks **quality** |

**None of these is individually significant at n = 9 arms, and the declaration does not rest on
them.** It rests on the mechanism and on the extremes, which are unambiguous: α\* agrees with
**regret** and disagrees with **every metric of how good the probabilities are**.

### The declaration

**α\* is a functional of the fitted posterior and nothing else.** It measures how confidently a
model asserts an excursion, not whether the assertion is right. An arm whose posterior is
badly miscalibrated but *confident* — which is exactly `doe`, at 5.2× the calibration error of
any other arm — scores highest.

The project's registered rule is that **a validated metric beats a model-internal one**. Five
validated metrics (calibration, Brier, empirical containment, symmetric difference, and the
per-family rank) now point one way and α\* points the other, on the same arms, in the same
cell.

> **α\* is not a metric of certificate quality and is not reported as one.** It is retained,
> labelled MODEL-INTERNAL, as a measure of *posterior confidence* — which is a real thing and
> a different thing. No ranking, no claim, and no kill condition in this project may rest on
> it.

### What this closes, and what it does not

**Closes:** the §15/§4.2 anomaly, the two-arm puzzle of §4.2 (`random` scoring 2nd–3rd on α\*
with the worst regret; `sobol` scoring last with the best containment). Both are the same
fact seen twice — **α\* rewards confident assertion, and neither arm's confidence tracks its
correctness.** They were never two anomalies.

**Does not close:** *why* the posterior is confident where it is wrong. Option (b) — testing
whether α\* rewards spatially coherent high exceedance probability rather than correctness —
remains available and is now the only open question about α\*. It is **not** required for any
claim in this document, because nothing here rests on α\* any more.

---

## 29. 🔴⭐⭐ F3: §14's KILL WAS AN ESTIMATOR ARTEFACT. It fired on 512 draws, not on SPADE.

`results/f3-draw-sweep.json` — 250 campaigns, 3,000 rows, **0 crashes**. Registered at commit
8032925 **before the runner existed**; the decision rule below was written before any number
existed. Every tail is `scipy.stats.binom.cdf`, exact, never a normal approximation.

### The registered branch that fired

> *"Containment rises toward nominal as draws increase, at n=200 → **the estimator failed, not
> SPADE**, and the correction is itself a reportable result."*

**Empirical containment against draw count** (α = 0.95, n = 50 pairs, non-empty sets only):

| cell | 512 | 1024 | 2048 | 4096 |
|---|---|---|---|---|
| **γ=0.99, τ_f=0.60** | **0.860** | **0.980** | 0.980 | 0.980 |
| γ=0.99, τ_f=0.75 | 0.960 | 1.000 | 1.000 | 1.000 |
| γ=0.95, τ_f=0.60 | 0.940 | 1.000 | 1.000 | 1.000 |
| γ=0.99, τ_f=0.85 | 0.940 | 1.000 | 1.000 | 1.000 |
| γ=0.50, τ_f=0.60 **[CONTROL]** | 1.000 | 1.000 | 1.000 | 1.000 |

**All four of §14's sub-nominal cells reach at-or-above nominal by 1,024 draws and stay there.**
The worst goes 0.860 → 0.980 and flattens.

**`results/p2-versionb-gamma.json` was produced at `N_DRAWS = 512`.** That is the whole of it:
**§14's certificate failure is an artefact of the draw count, not a property of SPADE's
certificate.**

### The powered test agrees

Seeds arm, 4,096 draws, `n_rho`=64, **n = 200 pairs** — the sample size Erratum 21 showed was
needed:

| cell | x/n | rate | exact tail | Holm ×72 |
|---|---|---|---|---|
| γ=0.99, τ_f=0.60 | 186/200 | 0.9300 | 1.299e-01 | 1.0000 |
| γ=0.99, τ_f=0.75 | 191/200 | 0.9550 | 6.730e-01 | 1.0000 |
| γ=0.95, τ_f=0.60 | 196/200 | 0.9800 | 9.910e-01 | 1.0000 |
| γ=0.99, τ_f=0.85 | 196/200 | 0.9800 | 9.910e-01 | 1.0000 |
| γ=0.50, τ_f=0.60 **[CTRL]** | 65/66 | 0.9848 | 9.661e-01 | 1.0000 |

**At 4,096 draws, with the power to detect it, no cell is significantly below nominal** — not
even before multiplicity correction.

### 29.1 The registered mechanism is REFINED: it is not the scan over `n_rho`

The registration predicted *"bias scales with `n_rho` → confirms the maximum-over-candidates
mechanism specifically."* **It does not scale.** `n_rho` = 16 and `n_rho` = 64 give **identical
containment at every draw level in all four cells.**

So the bias is **not** primarily the maximum over 64 near-tied quantiles. It is **Monte Carlo
error in `containment_probability` itself at low draw counts** — the containment of *each*
candidate is estimated on the same 512 draws, and at 512 that estimate is simply too noisy.
Scanning more candidates does not make it worse; scanning them on more draws makes it better.

**This is a prediction the design was built to test, and it failed. Recorded as a failed
prediction, not quietly dropped.**

### 29.2 The negative control behaves as registered

γ=0.50 is **flat at 1.000 across every draw level**, with no trend to explain away. At
`n_rho`=16 it has almost no non-empty sets (n = 2, 1, 0, 0) and is nearly vacuous there; at
`n_rho`=64 it carries n = 22, 19, 16, 20. **The control was the reason to be able to say the
draw trend is selection bias rather than a draw-count effect on everything**, and it earns it.

### 29.3 The cross-fit confirms a small residual bias — two independent routes, compared

Version C's `conservative_estimate_split` on the **same draws**, seeds arm:

| cell | full | cross-fit | Δ |
|---|---|---|---|
| γ=0.99, τ_f=0.60 | 0.9300 | **0.8950** | **−0.0350** |
| γ=0.99, τ_f=0.75 | 0.9550 | **0.9400** | **−0.0150** |
| γ=0.95, τ_f=0.60 | 0.9800 | 0.9800 | 0.0000 |
| γ=0.99, τ_f=0.85 | 0.9800 | 0.9800 | 0.0000 |
| γ=0.50 **[CTRL]** | 0.9848 | 1.0000 | +0.0152 |

**Selection bias is real and it survives at 4,096 draws — at 1.5 to 3.5 percentage points, and
only at the two highest-γ cells.** This track *measured* the bias by sweeping draws; Version C
*removed* it by cross-fitting; **neither was designed to test the other and they agree**: the
bias exists, it is concentrated exactly where the quantiles tie, and it is an order of
magnitude smaller than the 512-draw artefact that produced §14.

### 29.4 What §14 now says

**The registered kill fired as specified, and it fired on the estimator.** It is a decision
rule, not a hypothesis test, and it did its job: it stopped the programme and forced this
investigation. What has to change is the *attribution*.

* **Withdrawn:** *"SPADE's certificate fails below nominal at high assurance."*
* **Stands:** at 512 draws the conservative estimate is anti-conservative, most where the
  Vorob'ev quantiles tie, and the project reported that as a property of SPADE for a week.
* **New and stronger:** **`N_DRAWS = 512` is not enough to estimate `CE_alpha`'s containment at
  γ ≥ 0.95.** Any future containment claim needs ≥ 1,024, and the residual selection bias at
  4,096 needs the cross-fit.

**§22 said the containment sweep could not answer this by adding cells. It was right, and the
answer was on the other axis entirely.**

---

## 30. Cells 3 and 4: the screening result STRENGTHENS at d = 8

`results/p6-families.json` now carries **all 16 cells — 4,000 campaigns, 96,000 rows, gate
failures 0 across every cell.** The registered stop condition *"the screening result fails to
reproduce at d=8"* **did not fire.** It did the opposite.

### Mean rank on the symmetric difference, both dimensions

| arm | h6 d=6 | h6 d=8 | levy d=6 | levy d=8 | rosen d=6 | rosen d=8 | ackley d=6 | ackley d=8 |
|---|---|---|---|---|---|---|---|---|
| **`doe`** | 7.59 | **7.96** | 8.50 | 7.67 | 8.22 | **8.40** | 4.32 | **4.44** |
| `qlogei` | 5.74 | 5.50 | 6.40 | 7.50 | 6.78 | 6.90 | 4.95 | 5.17 |
| `qlognei` | 6.56 | 6.35 | 7.40 | 6.67 | 7.56 | 6.90 | 6.16 | 5.78 |
| `lhs` | 4.59 | 4.54 | 3.50 | 4.25 | 3.11 | 3.00 | 4.95 | 5.56 |
| `sobol` | 3.44 | 5.35 | **1.60** | 3.25 | 2.89 | **2.30** | 4.47 | 5.28 |
| **`random`** | 4.96 | **2.85** | 2.20 | 3.08 | 4.22 | 3.90 | 6.05 | **4.17** |
| `versionb` | 4.33 | 3.73 | 4.90 | 5.00 | 3.56 | 4.60 | 4.05 | 4.67 |
| `versionb_predictive` | 3.67 | 3.81 | 5.30 | 4.33 | 4.44 | 4.20 | 3.95 | 4.83 |

`doe` gets **worse** at d=8 on three of four families; only levy improves.

### Every effect is larger at d=8, and the BO arms flip sides

`doe` against each arm, paired on seed, pooled per dimension, Holm-adjusted (positive ⇒ the
arm beats `doe`):

| arm | d=6 | d=8 |
|---|---|---|
| `qlogei` | +0.0030 (p 3.5e-03) | **+0.0112** (p 1.1e-21) |
| `qlognei` | **−0.0005, ns (p 0.97)** | **+0.0056** (p 5.9e-12) |
| `lhs` | +0.0350 | **+0.0454** |
| `sobol` | +0.0379 | **+0.0450** |
| `random` | +0.0274 | **+0.0517** (p 7.9e-113) |
| `versionb` | +0.0283 | **+0.0359** |
| `versionb_random` | +0.0311 | **+0.0401** |
| `versionb_predictive` | +0.0292 | **+0.0354** |

**At d=6, `qlognei` ties `doe` and `qlogei` beats it only marginally. At d=8 every one of the
eight arms beats `doe`, both BO arms included.** §19's caveat 2 — *"on hartmann6 `doe` beats
both BO arms"* — is a **d=6 phenomenon and does not survive the harder regime.**

`random`'s +0.0517 at p_holm = 7.9e-113 is **the largest single effect in the study**, and it
is against the classical arm on the deliverable the classical arm exists to produce.

### What this does and does not change

* **Strengthens §19.** Three families at d=6 becomes three families at *both* dimensions, with
  larger effects and one fewer exception.
* **Narrows §19's caveat 2.** `doe` beating the BO arms was true at d=6 and false at d=8.
* **Ackley still reverses it at both dimensions** (4.32, 4.44), so the exclusion recorded in
  Decision 1 is unchanged and so is the reason for it.
* **Rankability does not improve with dimension** — 44–81% of cells excluded at d=6, 46–79% at
  d=8. §20's finding is dimension-independent.
* **§26 still applies only at d=6.** The unscreened classical arm cannot exist at d=8 within 48
  wells, so **the d=8 cells above inherit the screening/sub-box confound permanently.** The
  ~30% attribution from §26 cannot be checked here.

---

## 31. What α\* is actually measuring: willingness to certify

§28 declared α\* not a metric of certificate quality and left one question open — *why* the
posterior is confident where it is wrong (option (b)). **P7's committed columns answer most of
it with no new compute**, because **non-vacuity** — the fraction of campaigns in which the arm
certifies a **non-empty** set — is derivable from `pred_empty` and had never been read.

Hill, d=6, σ=0.25, 9 arms, same cell throughout:

| arm | non-vacuity | α\* | calibration |
|---|---|---|---|
| **`doe`** | **0.4617** | **0.7875** | **0.22959** |
| `versionb_predictive` | 0.4267 | 0.6861 | 0.03532 |
| `versionb` | 0.4225 | 0.6908 | 0.03593 |
| `qlogei` | 0.4183 | 0.5968 | 0.03366 |
| `qlognei` | 0.4125 | 0.6055 | 0.04425 |
| `random` | 0.4067 | 0.6521 | 0.03032 |
| `versionb_random` | 0.3925 | 0.6054 | 0.03846 |
| `lhs` | 0.3800 | 0.6291 | 0.03034 |
| **`sobol`** | **0.3117** | **0.5275** | **0.02893** |

| relationship | Spearman ρ | p |
|---|---|---|
| **non-vacuity vs α\*** | **+0.7333** | **0.0246** |
| non-vacuity vs calibration (lower better) | +0.6333 | 0.0671 |
| α\* vs calibration | +0.4667 | 0.2054 |

**The α\*/non-vacuity correlation is the only relationship in the entire α\* investigation that
reaches p < 0.05**, and it does so at n = 9 arms where nothing else came close.

### The mechanism, stated

**α\* measures how often an arm is willing to certify something.** An arm that certifies a
non-empty region in 46% of campaigns scores 0.79; one that certifies in 31% scores 0.53. That
is not a property of the region's *correctness* — it is a property of the arm's *readiness to
make a claim at all*.

And **willingness to certify is associated with worse calibration** (+0.6333, p = 0.067 —
marginal, and stated as marginal). The arm most ready to claim is the arm whose probabilities
are least reliable, by a factor of five.

> **α\* rewards claiming more, and claiming more is associated with claiming worse.** That is
> why it ranks `doe` first and `sobol` last, and it is the same fact §4.2 saw twice and called
> two anomalies.

### What this does not establish

**n = 9 arms.** The α\*/non-vacuity link is significant; the non-vacuity/calibration link is
**not** at 0.05 (p = 0.067) and is reported as marginal rather than claimed. The *spatial*
half of option (b) — whether α\* specifically rewards **coherent** high-exceedance regions as
against merely **large** ones — is untested and would need a region-geometry statistic this
project does not compute.

**§28's declaration does not depend on any of this.** It rests on the mechanism and the
inverted extremes. §31 explains the mechanism; it does not carry the conclusion.

### The non-vacuity ordering is itself a registered gap now filled

D21 found the predictive straddle yields 32% more non-empty certificates at identical
containment, and the brief records that **emptiness has surfaced post-hoc twice with no
registered home.** It has one now: **`versionb_predictive` (0.4267) does certify more often
than `versionb` (0.4225) and markedly more than `versionb_random` (0.3925)** — the predictive
straddle's advantage, on the ladder, at 24 cells, in a committed file.

---

## 32. ⭐⭐ VERSION C, C0: the σ=0.10 regret deficit was an IDENTIFICATION ARTEFACT

**`results/versionc-gate-s010.json`** — 600 rows, 12 arms × 50 keys, **gate clean at
|Δ| = 0 exactly**, double-gated against `p3-k6-d6-s010.json` and, for seven arms,
independently against `e2-grid.json`. Analysis in `results/versionc-gate-analysis.json`.
Registered in `docs/OPEN-QUESTIONS.md` (C0) **before the runner existed**, branch thresholds
and all.

**This is the sharpest confirmation of the terminal-rule claim the project has.** §13
measured SPADE at **10th–11th of 12 on regret** at (d=6, σ=0.10) while sweeping the map at
1st–3rd. C0 re-scores the *same committed wells* under a posterior-mean terminal rule.

| arm | rule A | rule P | A − P | 95% CI | p Holm | n_eff |
|---|---|---|---|---|---|---|
| `qlogei-addonly` | 0.0627 | **0.0627** | −0.0000 | [−0.0098, +0.0108] | 0.8482 | 20.30 |
| `qlognei` | 0.0808 | 0.0629 | +0.0179 | [+0.0106, +0.0251] | 0.0000 | 25.38 |
| `qlogei` | 0.0874 | 0.0703 | +0.0171 | [+0.0065, +0.0280] | 0.0106 | 21.96 |
| `lhs` / `plate1_only` | 0.1027 | 0.0765 | +0.0263 | [+0.0129, +0.0393] | 0.0011 | 10.76 |
| **`versionb`** | 0.1261 | **0.0792** | **+0.0468** | [+0.0304, +0.0623] | 0.0000 | 13.98 |
| `doe` | 0.0892 | **0.2728** | **−0.1835** | [−0.2307, −0.1387] | 0.0000 | 31.38 |

**SPADE moves from 10th of 12 to within SESOI of every arm except `doe`.** Paired on
`(instance, seed)`, n = 50:

| contrast | Δ | 95% CI | Wilcoxon p | |
|---|---|---|---|---|
| `versionb` − `qlogei-addonly` | +0.0165 | [+0.0029, +0.0314] | 0.0088 | **within SESOI** |
| `versionb` − `qlognei` | +0.0163 | [+0.0031, +0.0320] | 0.1355 | **within SESOI** |
| `versionb` − `qlogei` | +0.0090 | [−0.0034, +0.0230] | 0.3326 | **within SESOI** |
| `versionb` − `lhs` | +0.0028 | [−0.0137, +0.0200] | 0.9695 | **within SESOI** |

Against `qlogei-addonly` the Wilcoxon and the bootstrap **agree**: a real difference exists
and it is **below SESOI**. Per Q20 §2 both are reported — detectable, not material.

**`doe` inverts at a second cell.** D20 measured the reversal at σ=0.25 (rule P 0.1993
against rule A 0.0892). At σ=0.10 it is **0.2728** — worse, not better. **The asymmetry
now holds at both noise levels**: a terminal rule that reads the model punishes the arm
whose `grid_r2` is −6.19 and rewards the arms whose map scores AUC 0.77–0.84. That is the
D20 mechanism, reproduced at an independent cell, on 600 gated rows.

### 32.1 🔴 But the model behind §2.2 is dead, and the prediction was right by coincidence

C0 registered a second, separable test: regress `regret_P` on `σ/√n_eff`.

```
all arms    slope -1.7347   R2 0.0309   n=600
minus doe   slope +0.5124   R2 0.0112   n=550
```

**Excluding `doe` flips the sign and leaves R² ≈ 0.01.** Not a `doe` artefact — the model
explains about **one percent** of the variance either way.

**And the agreement that fired the branch is two cancelling errors.** C0 assumed
`n_eff ≈ 1.4` and predicted `0.10/√1.4 = 0.0845` against a measured **0.0792**. But:

| arm | measured n_eff | σ/√n_eff | measured regret_P | ratio |
|---|---|---|---|---|
| `sobol` | 9.56 | 0.0323 | 0.0823 | 2.54× |
| `versionb` | **13.98** | 0.0267 | 0.0792 | **2.96×** |
| `qlogei-addonly` | 20.30 | 0.0222 | 0.0627 | 2.82× |
| `doe` | 31.38 | 0.0179 | 0.2728 | 15.28× |

`n_eff` was underestimated by ~**10×** and the model under-predicts by ~**3×**, and
√10 ≈ 3.16. **The two errors cancel almost exactly.** The number was right; the mechanism
was not. Every non-`doe` arm shows the same 2.5–3.0× ratio, so this is systematic rather
than noise.

**What this does and does not overturn.** The branch is a decision rule on the **measured**
`regret_P`, which is gated and real — so the branch stands and **§2 is not built**. What
falls is §2.2's allocation rule `n_required = (σ̂/r*)²`, which rested on that model: its
well-count formula **has no basis and would require empirical calibration**. C0 registered
that consequence in advance, whichever way the branch fell.

**One-σ caveat, carried.** C0 registers the regression across **both** σ. This is σ=0.10
alone. `fix1-terminal-rule.json` carries `regret_p` at σ=0.25 but no `n_eff`, and
`run_fix1_terminal_rule.py` **raises at HEAD** (stale `_two_plate` signature — it passes
`True` and unpacks three of four returns). The two-σ version needs the C0 runner re-run at
σ=0.25.

### 32.2 What Version C now is

**Form 1 only — §1 + §3, no trust region.** And because §1's three changes are *scoring*
and *reporting* changes only (§1.4 keeps plate 1, the LSE criterion and the predictive
straddle unchanged), and because §2 is not built and K-C7 is predicted to fire, **§5's arm
table collapses**:

| §5 arm | after C0 |
|---|---|
| `versionc` | detector-gated → always boundary; `m` = 0 → 8 boundary |
| `versionc_form1` | 8 boundary |
| `versionc_nodetect` | always boundary |
| `versionc_fixed_m` | **moot** — requires §2's trust region |
| `versionc_random` | `m` = 0 → 8 random ≡ **`versionb_random`**, already committed |

The first three are **the same arm**, and its design **is Version B's design**.

> **Version C Form 1 requires zero new campaigns. It is a re-score of the stored Version B
> campaigns**, and its regret number already exists: the **0.0792** in the table above.

**What remains unrun:** the re-score itself — split-sample CE columns, connected-component
design spaces, and the five columns, on stored campaigns. Every library piece is built and
tested; the runner is not written.

---

## 33. The RSM community's own toolkit, run at last — and the classical arm fails all four

§6.2 of the evaluation brief records **zero coverage** of the diagnostics the response-surface
community would itself demand. All four now exist. Every number below comes off regenerated
`doe` campaigns that reproduce the committed `q59-hartmann-no-screen.json · doe_screened.rule_c`
at **worst |Δ| = 0.000e+00 over all 50 (σ, seed) rows**. n = 50 campaigns for items 1 and 4;
3 seeds at σ=0.25 for items 2 and 3 (design geometry, which barely varies by seed).

### 33.1 Lack-of-fit F-test — the arm CAN run it, and throws away the power to

**It has pure error: 2 df.** The stage-2 CCD carries 3 centre runs among 27 points.

| σ | F median | #F > 1 | **#p < 0.05** | MS_pure_error | MS_LOF |
|---|---|---|---|---|---|
| 0.25 | 3.56 | 23/25 | **2/25** | 0.000999 | 0.003430 |
| 0.10 | 12.81 | 25/25 | **8/25** | 0.000186 | 0.002579 |

**The misfit is real and the test cannot see it.** `MS_LOF` exceeds `MS_PE` in **48 of 50**
campaigns — a median of 3.4× at σ=0.25 and **13.9× at σ=0.10** — but 2 denominator df puts
`F_crit(0.05; 10, 2)` at **19.40**, so lack of fit is declared in 2/25 and 8/25.

**And the arm discards replicates it has already paid for.** In **50/50** campaigns the best
stage-1 run is one of the 4 screen centre points, so the stage-2 sub-box is `[0.25, 0.75]^4`
every time and its centre lands on the *identical 6-d point* as the 4 screen centres — a
**7-fold replicate** in the pooled 48. But the fit uses stage-2's 27 points only
(`boec/doe.py:330`). Pooling them costs nothing:

| σ | #p<0.05, as fitted (2 df) | #p<0.05, pooling the screen centres (6 df) |
|---|---|---|
| 0.25 | 2/25 | **8/25** |
| 0.10 | 8/25 | **24/25** |

**Tripling the pure-error df takes the σ=0.10 detection rate from 8/25 to 24/25 at zero extra
cost.** The arm has the replicates and drops them at a stage boundary.

*Caveat, stated not hidden:* the LOF test assumes constant variance; this oracle's noise is
multiplicative, so pure error is estimated at one location and applied across a sub-box. The
test is run as the literature specifies; the assumption it rests on is violated by this
project's noise model.

### 33.2 🔴 `doe`'s 48 wells are NOT A DESIGN for the model it reports

D- and G-efficiency, 48-point designs at d=6, second-order model, **p = 28**:

| arm | rank/28 | D-eff % | G-eff % | max SPV |
|---|---|---|---|---|
| **`doe`** | **25, 23, 25** | **undefined** | **undefined** | **undefined** |
| `doe_unscreened` | 28 | 42.90–43.30 | 68.74–70.61 | 39.7–40.7 |
| *ref* CCD(6), 48 runs | 28 | 42.42 | 68.87 | 40.7 |
| `sobol` | 28 | 10.42–10.63 | 2.72–3.14 | 892–1031 |
| `random` | 28 | 8.14–9.83 | 1.32–2.31 | 1213–2127 |
| `lhs` | 28 | 9.08–9.20 | 0.93–1.54 | 1820–3007 |
| `qlogei` | 28 | 4.48–4.71 | 0.14–0.35 | 7966–19991 |
| `qlognei` | 28 | 3.44–7.47 | 0.08–0.54 | 5198–34416 |

**`doe`'s pooled design is rank-deficient in 50 of 50 campaigns — full rank in ZERO.** Two
exact collinearities, both structural rather than accidental:

1. The two dropped factors are pinned across all 28 post-screen runs, so their pure-quadratic
   columns are **identical vectors** over all 48 rows.
2. The `2^(6-2)` screen is **resolution IV**, so its two-factor interactions are aliased in
   pairs — and because those columns are nonzero only on the 16 screen rows, **the screen's
   aliasing becomes an exact rank deficiency of the pooled design.**

**The classical arm builds a well-designed 4-factor experiment** — its own stage-2 model is
fine at D-eff 42.1%, G-eff 78.8% — **inside a box covering 1/16 of the space, then reports it
as an answer about 6 factors.** By the RSM community's own criterion the 48 wells taken
together are not a design at all.

*G-eff is an upper bound: the maximum is taken over a finite candidate set (the 20,000-point
grid plus vertices, face centres and design points).*

### 33.3 FDS is the bridge to certifiability, and it is exact arithmetic

`SecondOrderModel.prediction_interval` (`boec/rsm.py:238`) has half-width
`t·σ·sqrt(1 + SPV/n)`. **So the FDS curve IS the distribution of prediction-interval width
over the space, up to a constant** — and a certified region is exactly
`{x : lower bound ≥ τ}`. Interval width multiplier `sqrt(1 + SPV/48)`:

| arm | 10th | 50th | 90th | 99th |
|---|---|---|---|---|
| `doe_unscreened` | 1.09 | 1.17 | 1.24 | 1.29 |
| `sobol` | 1.19 | 1.40 | 1.86 | 2.42 |
| `lhs` | 1.22 | 1.52 | 2.21 | 3.15 |
| `qlogei` | 1.74 | 2.95 | 5.52 | 8.81 |
| `qlognei` | 1.68 | 2.89 | 5.40 | 9.14 |

**The adaptive arms buy their regret by leaving the space 3–9× less precisely mapped than a
CCD.** That is the trade §23.2 describes, in the RSM literature's own units, and it is why
spread designs win the map while BO wins the search.

*This is the classical, design-based FDS on SPV. The project's certified regions use **GP
posterior** SD, and no committed file stores per-grid-point posterior SD, so a GP-based FDS
would need a fresh 20,000-point posterior per arm per seed.*

### 33.4 ⭐ The classical arm fails its OWN acceptance test, 25 times out of 25

The confirmation run is the well the classical pipeline spends on checking itself. True global
optimum = 1.0000, n = 25 per σ:

| | σ=0.25 | σ=0.10 |
|---|---|---|
| predicted `f(x̂)` mean | 0.9805 | 0.9625 |
| true `f(x̂)` mean | **0.0992** | **0.1015** |
| **gap = predicted − true, mean** | **0.8813** | **0.8609** |
| **over-promised (gap > 0)** | **25/25** | **25/25** |
| **predicted ABOVE the true global optimum** | **12/25** | **12/25** |
| stationary point classified a **saddle** | **25/25** | **25/25** |
| confirmation beat the best of the 48 visited | **0/25** | **0/25** |

**The arm predicts a response above the global maximum of the landscape in half its
campaigns**, its chosen point is a **saddle every single time**, and the confirmation run
**never once** improves on a point it had already visited.

`grid_r2 = −6.19` is the same fact in a language the RSM community does not use. **This is that
fact in the language it does use, and it is worse:** the classical pipeline's own,
self-administered, single-well acceptance test **fails in 50 of 50 campaigns.**

---

## 34. ⭐⭐ The D20 reversal as a RANK, and E7's registered prediction FAILS

Every number in this section was **recomputed from committed files in this session**, not
taken from the agent that first reported them. Two of the reported numbers did not survive
that check; both corrections are below and both are material.

The join is exact: `step0-oracle-best.json.rule_a` and `fix1-terminal-rule.json.regret_a`
agree to **max |Δ| = 5.55e-16** over all 300 shared `(instance, seed, arm)` keys, so the two
files describe the same campaigns and may be joined without re-running anything.

### 34.1 🔴 The reported ranks included `plate1_only` as a tenth arm

`plate1_only` carries `never_rank_separately` — it **is** `lhs` at 48 wells. I verified on
this file that its `regret_p` is **identical to `lhs` in 50 of 50 rows**. Ranking both makes
`lhs` a double arm and inflates every other arm's mean rank. This is the §19 trap a second
time, caught here before publication rather than after.

**n = 25 instances** (regret averaged over the 2 seeds within each instance, then ranked),
d = 6, σ = 0.25, `results/fix1-terminal-rule.json`:

| arm | rule A | rule P | shift |
|---|---|---|---|
| **`doe`** | **1.88** (best) | **7.92** (worst) | **+6.04** |
| `lhs` | 3.64 | 4.60 | +0.96 |
| `qlogei-add` | 4.80 | 4.16 | −0.64 |
| `qlogei` | 5.00 | 5.28 | +0.28 |
| `qlognei` | 5.08 | 5.40 | +0.32 |
| **`versionb`** (SPADE) | 5.28 | **3.76** (best) | −1.52 |
| `qlogei-addonly` | 5.52 | 4.48 | −1.04 |
| `sobol` | 5.88 | 4.04 | −1.84 |
| `random` | 7.92 (worst) | 5.36 | −2.56 |

*(The ten-arm figures first reported — `doe` 2.12 → 8.80, `random` 8.88, `versionb` 4.08 —
reproduce exactly but are **superseded**: they rank `plate1_only` separately.)*

**`doe` goes from best of nine to worst of nine, and SPADE from sixth to first, on the same
campaigns, purely by changing the terminal rule.** Nothing about the designs changed.

### 34.2 The registered caveats verified

Paired mean Δ(P − A) in regret, n = 50 rows per arm:

`random` **−0.0975** · `sobol` −0.0673 · `versionb` **−0.0543** · `qlogei-addonly` −0.0473 ·
`qlogei-add` −0.0400 · `qlogei` −0.0320 · `qlognei` −0.0246 · `lhs` −0.0136 ·
**`doe` +0.1035** (the only arm the non-maximising rule *hurts*).

* **The gain is not SPADE's.** `random` gains **more** than SPADE: paired difference
  **0.0431**, two-sided Wilcoxon **p = 5.07e-03**. *(First reported as p = 1.1e-2; the raw
  paired test on the committed columns gives 5.07e-03. The looser figure is not reproducible
  from this file and is withdrawn.)* The benefit is **general to spread designs**, not
  evidence for SPADE.
* **`lhs` alone does not reach significance**: raw Wilcoxon p = 6.35e-02, Holm ×2 =
  **0.1269** — the registered "p = 0.13", confirmed to four figures.

### 34.3 🔴⭐ E7: **neither registered branch fires**

Registered prediction: under rule P the identification gaps **converge**, and `doe`'s
advantage **falls below SESOI (0.02)**.

Identification gap = `terminal_rule_regret − oracle_best`. Rule A column is
`step0-oracle-best.json.identification_gap` (confirmed identically equal to
`rule_a − oracle_best`, max deviation **0.00e+00**); rule P column is
`fix1.regret_p − step0.oracle_best`. n = 50, 4000-resample bootstrap, `default_rng(0)`.

| arm | gap, rule A | gap, rule P | shift | Wilcoxon p | boot 95% CI on shift |
|---|---|---|---|---|---|
| **`doe`** | **+0.0361** | **+0.1396** | **+0.1035** | 4.95e-08 | [+0.0723, +0.1367] |
| `lhs` | +0.0475 | +0.0339 | −0.0136 | 6.35e-02 | [−0.0304, +0.0040] |
| `qlognei` | +0.0698 | +0.0452 | −0.0246 | 5.41e-03 | [−0.0419, −0.0077] |
| `sobol` | +0.0730 | **+0.0057** | −0.0673 | 7.72e-07 | [−0.0921, −0.0449] |
| `random` | +0.1251 | +0.0277 | −0.0975 | 2.99e-11 | [−0.1175, −0.0771] |

**Spread of mean gaps** (`plate1_only` excluded throughout):

| | rule A | rule P |
|---|---|---|
| **excluding `doe`** | 0.0776 | **0.0395 — they converge** |
| **including `doe`** | 0.0890 | **0.1339 — they diverge** |

So §9.3's convergence mechanism **holds for every arm it was about**, and every non-`doe`
arm's gap falls. `doe` is not a case of it: its gap nearly **quadruples**.

**The verdict, and it matches neither branch.** Under rule P `doe` has **no advantage to be
above or below SESOI — it has a deficit.** Against `lhs` it goes from +0.0114 *better* under
rule A to **0.1057 worse** under rule P; against `sobol`, from 0.0369 better to **0.1339
worse**. The literal kill condition ("remains above SESOI") is not met; the prediction
("falls below SESOI") is not met either. Rule P does not equalise identification — **it
replaces `doe`'s identification advantage with a larger model-quality deficit.**

### 34.3b 🔴 **SUPERSEDED BY §36.** The withdrawals in 34.4 were WRONG.

Everything above stands. **34.4 below does not** — `q57-search-vs-id.json` carries the σ=0.10
and `qlogei` columns I said did not exist, and `results/e7-search-vs-id-rule-p.json` is now
committed. **Read §36 instead of 34.4.** 34.4 is left in place unedited because a withdrawal
that turns out to be wrong is itself a result, and deleting it would hide the mistake.

### 34.4 ~~What this section does NOT establish, and the corrected scope~~ (WRONG — see §36)

* **σ = 0.10 is absent.** `step0-oracle-best.json` carries no `sigma` key at all —
  `scripts/run_step0_oracle_best.py:53` hardcodes `sigma_rel = 0.25`. The reported
  "`doe` +0.0348 → +0.2184 at σ = 0.10" **cannot come from this file and is not reproducible
  from anything committed.** It is **withdrawn pending a σ-parameterised re-run.**
* **`qlogei` is not in E7.** `step0-oracle-best.json` carries `qlognei` only. The reported
  "`qlogei` .0797 → .0477" has no committed source; it is **withdrawn**. This is also why the
  excluding-`doe` rule-P spread is **0.0395 here and not the 0.0420 first reported** — that
  figure counted a sixth arm this file does not contain.
* **SPADE cannot enter E7.** The only Version B row is `versionb_plate1_ceiling` at **40
  wells**, not 48. It is excluded from the table above; a 40-well arm is not comparable to
  eight 48-well ones.
* **No result file exists.** `results/e7-search-vs-id-rule-p.json` is **absent from disk.**
  The rule-P gap column above is a join computed in-session. **It is reproducible from two
  committed files by the recipe in 34.3 and needs no new campaigns**, but until a runner
  writes it, it is not a committed artefact and must not be cited as one.

### 34.5 The endpoint hides a crossing — `doe` does not lead throughout

`results/q52-budget-to-target.json` stores **11 budget checkpoints** (8, 12, 16, 20, 24, 32,
48, 64, 100, 150, 200) for **4 arms** (`qlogei`, `doe`, `random`, `spread_gp`) under both
`rule_a` and `rule_c` — the only per-budget curve committed anywhere. **No committed file
stores per-evaluation regret curves**; 11 checkpoints is the finest resolution that exists.

At σ = 0.25 `doe` leads at the shared budget of 48 (−0.0658, p = 1.5e-3) but `qlogei` closes
the gap by 150–200. At σ = 0.10 the lead is **already gone at 48** (p = 0.77) and **inverts**
by 150. **"`doe` leads throughout" is false at both σ**; the single-budget comparison at 48
is a snapshot across a crossing, not a summary of a curve.

### 34.6 🔴 Three different non-maximising rules are on disk, and they are not one estimator

* `fix1-terminal-rule.json` → **rule P** (posterior-mean argmax, multi-start, `from_grid` flag)
* `q52-budget-to-target.json` → **rule C** for the GP arms
* …and for `doe` in q52, rule C is **not a GP at all** — it is the quadratic surface's own
  stationary point

**Do not pool the q52 `doe` `rule_c` column with the `fix1` `rule_p` column.** They answer
different questions with different estimators and share only a name.

---

## 35. 🔴 VERSION C's KILL CONDITIONS: one of eight is named in code, and three are already moot

Raised by Joseph — *"why the fuck are you not testing Version C, isn't that the whole point"* —
and the audit says the objection lands, though not where it first appears to.

**Version C is being SCORED. It is not being ADJUDICATED.** The distinction is the whole
content of this section: the columns that decide the kills are being produced right now, and
**no code anywhere turns them into a verdict.**

### 35.1 The audit — every kill condition against the code that would evaluate it

Eight kills were registered before any Version C arm was scored (`OPEN-QUESTIONS.md`, *Kill
conditions*). **K-C2 is the hard stop; the others narrow the claim.**

| # | condition | named in any script? | status |
|---|---|---|---|
| **K-C2** | containment at γ=0.50 below 0.940/1.000/1.000 — **HALT** | **NO** | **LIVE — no evaluator** |
| K-C1 | `versionc` does not reach `r*` at σ=0.10 | **NO** | **LIVE — no evaluator** |
| K-C3 | symmetric-difference volume worsens >10% vs Version B at γ=0.50 | **NO** | **LIVE — no evaluator** |
| K-C4 | `versionc` does not beat `versionc_fixed_m` | **NO** | **MOOT** — §2 never built |
| K-C5 | `versionc` does not beat `versionc_random` | **NO** | **MOOT** — alias to `versionb_random` |
| K-C6 | split-sample CE does not move §14's four failures | **NO** | **WOULD MISFIRE** (C1.2a) |
| **K-C7** | detector does not separate held-out families | **YES** — 3 sites | predicted to fire; **one-shot pass unspent** |
| K-C8 | `versionc` does not beat `versionc_nodetect` on hartmann6 | **NO** | **MOOT** — alias to `versionc_form1` |

`grep -rno "K-C[1-8]" scripts/` returns **four hits total**: three in
`analyse_versionc_detector.py` and one in a `run_versionc_form1.py` docstring. **K-C1, K-C2,
K-C3, K-C4, K-C5, K-C6 and K-C8 appear in no script in this repository.**

### 35.2 No Version C artefact on disk carries a kill verdict

Verified against the top-level keys of every committed Version C file:

| file | top-level keys | verdict field? |
|---|---|---|
| `versionc-gate-s010.json` | `status`, `complete`, `keys_present`, `keys_expected`, `provenance`, `config`, `gate`, `rows` | **none** |
| `versionc-gate-analysis.json` | `source`, `per_arm`, `branch`, `regression`, `sesoi`, `n_boot`, `boot_seed` | **none** (`"K-C"` does not occur in the file) |
| `versionc-detector-boundary.json` | `source`, `fit_families`, `single_class`, `ranked`, `proposed`, `frozen` | **none** |
| `versionc-detector-fit.json` | fit rows | **none** |

Even K-C7 — the one kill with code — is only a `print()` to stdout in
`analyse_versionc_detector.py`, and what it prints is a **prediction** (*"K-C7 IS LIKELY TO
FIRE"*), never a recorded verdict. `versionc-detector-boundary.json` carries
**`frozen: false`**.

**A kill condition that exists only in prose is not a kill condition. It is an intention.**
This project has spent an entire programme establishing that registered predictions must be
adjudicated against committed columns; Version C registered eight and adjudicated none.

### 35.3 The three moot kills are moot for a real reason, and the code already says so

C0 returned **`IDENTIFICATION_ARTEFACT`** and **§2 — the trust region — was never built**
(§32). Everything downstream of §2 collapses, and `run_versionc_form1.py`'s own constants
record the collapse rather than silently dropping the arms:

```python
ARM_ALIASES = {"versionc": "versionc_form1", "versionc_nodetect": "versionc_form1",
               "versionc_form1": "versionc_form1", "versionc_random": "versionb_random"}
MOOT_ARMS = {"versionc_fixed_m": ("splits 4 trust + 4 boundary, and section 2's trust "
                                  "region was never built -- C0 returned IDENTIFICATION_ARTEFACT")}
```

* **K-C4** compares `versionc` to `versionc_fixed_m` — an arm that cannot exist without §2.
* **K-C5** compares `versionc` to `versionc_random`, which **aliases to `versionb_random`**.
* **K-C8** compares `versionc` to `versionc_nodetect`, which **aliases to `versionc_form1`** —
  the same campaign. It would compare an arm to itself.

**Three of the eight kills were rendered unanswerable by Version C's own first result**, and
that is a finding about the design, not a failure of execution: **§2's collapse took most of
Version C's test surface with it.**

### 35.4 What is actually still live, and what is missing

**K-C1, K-C2 and K-C3 are Version C's entire remaining test surface**, and **K-C2 is the hard
stop.** All three are decided by the run executing at the time of writing.

**The columns they need ARE being produced.** `run_versionc_form1.py` sweeps
`GAMMAS = (0.50, 0.70, 0.80, 0.90, 0.95, 0.99)` — γ=0.50 is exactly K-C2's and K-C3's cell —
and its `ARMS` tuple includes `versionb`, which is K-C3's comparator. It runs σ=0.10 first,
which is K-C1's cell.

**What is missing is one analyser.** There is no `analyse_versionc_form1.py`; the repository
has `analyse_versionc_gate.py` and `analyse_versionc_detector.py` only. Without it the run
finishes, writes ~7 MB of correct columns, and **nobody calls the verdict — including the
hard stop.**

### 35.5 The correction to §34 and to the verdict I gave

The programme-level verdict reported before this audit led with SPADE, `doe` and the spread
arms, and put Version C eighth. **That ordering was wrong for what this project is for.**
`lhs` and `sobol` are comparators; **Version C is the object under test.** The finding that
belongs at the top is 35.2: **eight registered kills, zero adjudicated.**

**What this section does NOT say:** it does not say Version C is untested. C0 ran, gated clean
at |Δ| = 0 over 600 rows, and returned a real verdict that killed §2. The detector's fit set
ran and produced a boundary. **The gap is specifically between scoring and adjudication**, and
it is one file wide.

---

## 36. ⭐⭐ E7 COMMITTED — and at σ=0.10 the terminal rule separates identical arms by 70×

`results/e7-search-vs-id-rule-p.json` now exists. **§34.4's withdrawals are withdrawn**
(Erratum 32): both figures had a committed source I failed to find, and both reproduce
exactly. **Zero new campaigns** — the runner builds no oracle, fits no GP, evaluates no
design, and a test enforces that by refusing the constructors.

**Both joins are checked at run time, not assumed.** σ=0.25 joins
`step0.oracle_best × fix1.regret_p` at worst \|Δ\| = **5.551e-16** over 300 keys; σ=0.10
joins `q57.{doe,bo,nei}_oracle_best × versionc-gate-s010.regret_p` over **50 of 50 identical
keys**. A drift raises `JoinInvalid` rather than reporting across mismatched files.
**`bo_` is `qlogei` and `nei_` is `qlognei`** — the mapping whose absence caused Erratum 28.

### 36.1 σ = 0.25 — six arms, n = 50, 4000-resample bootstrap

| arm | gap rule A | gap rule P | shift | Wilcoxon | boot 95% CI |
|---|---|---|---|---|---|
| **`doe`** | +0.0361 | **+0.1396** | **+0.1035** | 4.95e-08 | [+0.0723, +0.1367] |
| `lhs` | +0.0475 | +0.0339 | −0.0136 | 6.35e-02 | [−0.0305, +0.0041] |
| `qlognei` | +0.0698 | +0.0452 | −0.0246 | 5.41e-03 | [−0.0417, −0.0076] |
| `sobol` | +0.0730 | **+0.0057** | −0.0673 | 7.72e-07 | [−0.0925, −0.0445] |
| **`qlogei`** | **+0.0797** | **+0.0477** | −0.0320 | 1.11e-03 | [−0.0489, −0.0151] |
| `random` | +0.1251 | +0.0277 | −0.0975 | 2.99e-11 | [−0.1177, −0.0766] |

`plate1_only` returns **identical to `lhs` at every digit and on the same bootstrap CI** —
an independent confirmation of Erratum 29, and of why it never ranks.

**Spreads, each carrying its arm set** (the point of Erratum 32):

| | rule A | rule P |
|---|---|---|
| 6 arms, **including `doe`** | 0.0890 | **0.1339 — diverge** |
| 5 arms, **excluding `doe`** | 0.0776 | **0.0420 — converge** |

**0.0420 is the correct excluding-`doe` figure and it is the agent's original number.** My
0.0395 was the same statistic over four arms with `qlogei` absent. Both were right for their
own arm set, which is exactly why the runner now attaches the arm list to every spread.

### 36.2 ⭐⭐ σ = 0.10 — the sharpest version of the whole finding

| arm | gap rule A | gap rule P | shift | Wilcoxon | boot 95% CI |
|---|---|---|---|---|---|
| **`doe`** | +0.0348 | **+0.2184** | **+0.1835** | 1.60e-09 | [+0.1387, +0.2307] |
| `qlognei` | +0.0373 | **+0.0194** | −0.0179 | 4.52e-06 | [−0.0251, −0.0106] |
| `qlogei` | +0.0378 | **+0.0207** | −0.0171 | 3.54e-03 | [−0.0280, −0.0065] |

**Under rule A these three arms are indistinguishable — spread 0.0029, an order of magnitude
below SESOI.** Under rule P they separate by **0.1990: a factor of 70.**

This is the cleanest statement of D20 anywhere in the project. The three arms *identify* the
best visited well equally well; what differs is entirely **what each terminal rule does with
the campaign it was given.** `doe`'s rule-P gap is **worse at σ=0.10 than at σ=0.25**
(+0.2184 against +0.1396) — the quieter the data, the more the quadratic surface's own
stationary point costs it, because the BO arms' posterior means get *better* with less noise
while the misspecified quadratic does not.

**Registered coverage limit:** at σ=0.10 only `doe`, `qlogei` and `qlognei` have a committed
`oracle_best` (q57). **The spread arms enter at σ=0.25 only**, and the σ=0.10 spread figures
are over three arms and say so in the file.

### 36.3 What §34's verdict becomes

**Unchanged and strengthened.** Neither registered branch fires: under rule P `doe` has no
advantage to be above or below SESOI — it has a deficit, now measured at **both** σ, with
every CI excluding zero. §9.3's convergence holds for the arms it was about; `doe` is not one
of them. The σ=0.10 cell makes the mechanism unmistakable: **rule P does not equalise
identification, because identification was already equal.**

---

## 37. 🔴⭐⭐ **K-C7 FIRED. The detector separates nothing, 0 of 50 on both families.**

The one-shot held-out pass ran once, against a rule frozen and committed at `b7dcc41`
**before hartmann6 or ackley was touched**. `results/versionc-detector-heldout.json`,
100 campaigns, `status: complete`.

### 37.1 The result

| family | DECEPTIVE | rate | Wilson 95% | clears 33/50? |
|---|---|---|---|---|
| **hartmann6** | **0 / 50** | 0.000 | [0.000, 0.071] | **no** |
| **ackley** | **0 / 50** | 0.000 | [0.000, 0.071] | **no** |

Zero in **all four** cells — `(6, 0.25)` and `(6, 0.10)`, 25 seeds each, both families.
Holm-adjusted tails against p = 0.50 are **1.0 for both.** **K-C7 FIRED → Version C ships
without Stage 0** (§3.6).

### 37.2 🔴 It is not a near miss — the held-out ranges are NESTED INSIDE the fit range

| set | `additive_share` range | n |
|---|---|---|
| **fit** (hill/levy/rosenbrock) | **[0.1054, 0.8860]** | 150 |
| hartmann6 | [0.2673, **0.8856**] | 50 |
| ackley | [0.2949, 0.8534] | 50 |

**Both held-out families sit strictly inside the boundary at both ends.** The closest any of
the 100 campaigns came to a boundary was **0.0004** — hartmann6's maximum, just under the
top. A one-class rule can only fire on what falls outside its reference range, and nothing
did.

**The deceptive families are LESS extreme on this statistic than the unimodal ones.** That is
stronger than "the detector is weak": it says the statistic's ordering does not track
landscape class at all. Widening or tightening the threshold cannot fix it — **a boundary
strictly containing both target classes has no setting that separates them.**

### 37.3 The prediction was right, and it cost nothing

**C3.3b predicted K-C7 would fire, from the fit set alone, before the pass.** Two fit-set
measurements said so: `excluded_fraction = 0.2194` (the fit families already spanned 78% of
the statistic's attainable range) and `within_family_share = 0.8766` (most of the spread is
seed noise, not landscape class). **Neither consumed the one-shot budget**, and both were
committed before the score.

Measured before the pass and now interpretable: the fit set's **leave-one-out false-positive
rate is 2/150 = 1.33%**. So the boundary is *tight* against its own class and still fires on
nothing — the two facts together say the rule is well-formed and the **statistic** is empty,
which is a sharper conclusion than either alone.

### 37.4 What this licenses, and what it does not

**Publishable negative finding, and the protocol is what makes it one:** *no first-plate
additivity statistic among the six candidates separates smooth from deceptive landscapes at
40 wells.* The rule was frozen in a commit that contains **no code and no result**, so the
ordering is checkable in the history by anyone; the runner verifies the boundary against
`git show HEAD:docs/OPEN-QUESTIONS.md` on every start; and the pass refuses to repeat.

**It does NOT license** *"landscape class is undetectable from plate 1."* This tested **one
frozen statistic** (`additive_share`) at **one plate size** (40) on **two held-out families**.
C3.2a had already ruled two of the six candidates non-viable as written; the other three were
ranked less tight on the fit set and were not frozen. **A different statistic, a larger plate,
or a two-class fit set could all still work** — none was tried, and §3.5 forbids trying them
against these two families now.

**Disclosure.** A smoke run touched hartmann6 and ackley for 4 campaigns before the real
pass, at a **non-protocol configuration** (16-well plate, 1024-point grid, against the
protocol's 40 and 20,000), writing outside `results/`. All four returned UNIMODAL. It could
not have moved the boundary — that was already committed and is re-verified against git at
every start — but it is recorded rather than left for someone to discover.

### 37.5 Version C's kill ledger is now complete

| # | verdict |
|---|---|
| K-C1, K-C2 (hard stop), K-C3 | **evaluated by `analyse_versionc_form1.py`** once the live re-score lands |
| K-C4, K-C5, K-C8 | **MOOT** — §2 was never built (§35.3) |
| K-C6 | **WOULD MISFIRE** as written (C1.2a) |
| **K-C7** | **🔴 FIRED — 0/50 both families. Ship without Stage 0.** |

**Version C is now a measured method rather than a specification**, and the measurement says
its Stage 0 does not work. §35's *"eight registered, zero adjudicated"* is no longer true.

---

## 38. VERSION C FORM 1 — the re-score. **Both sigma committed, all eight kills adjudicated.**

`results/versionc-form1-s010.json` and `-s025.json` — **14,400 rows each**, 12 arms x 50 keys
x 24 (gamma, tau_frac) cells, **GATE CLEAN at |delta| = 0** across all 20 committed K6
columns at both sigma. Verdicts in `results/versionc-kills-s010.json` / `-s025.json`.
**Zero new wells.**

### 38.1 What was actually run

C0 (section 32) returned `IDENTIFICATION_ARTEFACT` so section 2's trust region was never
built, and K-C7 has fired (section 37) so the detector does not gate. With `m = 0` and no
detector, section 5's arm table collapses -- `versionc` = `versionc_form1` =
`versionc_nodetect`, `versionc_fixed_m` is moot, and `versionc_random` **is** the
already-committed `versionb_random`. Section 1's three changes are scoring and reporting
only, since section 1.4 keeps plate 1, the LSE criterion and the predictive straddle
unchanged.

> **Version C Form 1's campaign IS Version B's campaign**, so every difference below is
> attributable to the three scoring changes and to nothing else. That attribution is only
> licensed because every shared column reproduces at `|delta| = 0`, which is why the base
> scoring is `run_p3_cells.score_k6_dual_tau` **imported and called** rather than
> reimplemented.

**The gate earned itself on the first smoke run**, catching an all-six active mask where
Amendment B3 requires per-arm: `doe` came back with `n_active = 6` against a committed 4
and `box_vol_pred = 0.0053` against 1.0.

### 38.2 The kill ledger — eight registered, eight adjudicated

| kill | verdict | evidence |
|---|---|---|
| **K-C1** parity at sigma=0.10 | **PASS — as parity, not as a win. See §40.1** | registered bar: regret_P **0.0792** vs `r*` **0.0808** -> gap **-0.0016**. **But `r*` is a RULE A column and regret_P is RULE P.** Like-for-like, against the best rule-P arm (`qlogei-addonly`, **0.0627**), the gap is **+0.0165** — inside SESOI, so **parity holds and the bar is not beaten** |
| **K-C2** containment, gamma=0.50 | **PASS — HARD STOP CLEARS** | measured {0.50: 0.940, 0.80: 1.000, 0.95: 1.000} against a committed nominal of exactly those three. `failed_alphas` empty, `invariance_violated` **False** |
| **K-C3** symmetric difference | **PASS** both sigma | 0.21089 vs 0.21089 (sigma=0.10), 0.35828 vs 0.35828 (sigma=0.25), +0.00% against a +10% bar |
| K-C4 / K-C5 / K-C8 | **MOOT** | settled by C0 -- no trust region, and the other labels name the same campaign |
| K-C6 | **MISFIRES** | C1.2a -- the cross-fit returns a bit-identical set, so it would fire automatically for the wrong reason |
| **K-C7** | **FIRED** | section 37, 0/50 both held-out families -> ship without Stage 0 |

**Independent cross-check on K-C1:** C0 measured `versionb`'s rule-P regret at **0.0792**
through a separate runner and a separate gate path. The re-score reproduces it to four
decimals. Two routes, one number.

### 38.3 🔴 K-C2 and K-C3 pass STRUCTURALLY, not evidentially

Version C's selected sets are bit-identical to Version B's (C1.2a), and both quantities are
built from columns gated at `|delta| = 0`. **They could not move, and they did not — to the
digit.** `invariance_violated` is `False` on both at both sigma.

> **A pass here must not be read as the certificate having been independently re-tested.**
> It was not. **F3 is what re-tested it** (section 29), by sweeping draws — a mechanism that
> changes the selected set, which the cross-fit by construction does not.

The analyser carries `invariance_violated` as a field separate from `fired` for exactly this
reason: a movement in either would have been a **defect in the re-score**, and reporting a
bug as a kill would publish it as a scientific finding.

### 38.4 ⭐ What section 1.2 actually bought: the selection bias, measured

The circular `ce_contain` cannot fall below alpha by construction. The cross-fit can, and
does. **Mean bias (circular minus held-out), over every non-empty certificate:**

| | alpha = 0.50 | alpha = 0.95 |
|---|---|---|
| **sigma = 0.10** | **+0.01898** (n=10956, max +0.1270) | **+0.03297** (n=7002, max +0.1270) |
| **sigma = 0.25** | +0.00420 (n=6498) | +0.00836 (n=1812) |

**Two things fall out, neither of them registered in advance.** The bias **rises with
alpha** — the scan maximises over more near-tied candidates as the bar rises — and it is
**~4x larger at sigma = 0.10 than at sigma = 0.25**, which is the opposite of where a reader
would expect an estimator to struggle. At alpha = 0.95, sigma = 0.10 the reported
containment is overstated by **3.3 percentage points on average**
and by up to **12.7**.

This is a statement about the **estimator**, never about the certificate.

### 38.5 The component prediction: the Hill half CONFIRMS, the hartmann6 half is UNTESTED

Registered before the run: *largest on hartmann6 (multimodal, disconnected superlevel sets),
near-zero on Hill (unimodal, one component). If it helps everywhere equally, something is
wrong.*

**Hill, excluding `doe`:** mean components at gamma=0.50, tau_frac=0.60 is
**1.07** (sigma=0.10) and **1.50** (sigma=0.25) — one
component, as predicted — and the box-volume gain from decomposing is
**+0.000375** mean / +0.0316 max. **Near-zero, as registered.**

**The hartmann6 half has not been run.** These are Hill campaigns. The prediction's
discriminating half needs the cross-family cells and is section B4 step 5.

### 38.6 🔴 `component_box_vol_sum` is UNDEFINED for a screened arm

`doe` alone gives a box-volume "gain" of **+9.55 mean and +59.00 max**, against
**+0.000375 / +0.0316** for every other arm. It is not a
finding, it is a defect in the aggregate.

**Mechanism.** `doe` has `n_active = 4`, and its `box_vol_all_components` takes only the
values **{0.0, 1.0}**. With the inactive axes pinned to the seed, almost no grid point
falls "inside" a candidate box, so `mask[inside].all()` is **vacuously true** and the box
expands to fill the whole active subspace. That degeneracy is already present in the
committed single-box column — which is why this run gates against it at `|delta| = 0` — but
**summing it across N components multiplies 1.0 by N.**

**`component_box_vol_sum` must not be reported for arms with a screen.** The per-component
volumes and the committed single-box number are unaffected.

### 38.7 Non-vacuity: D21's homeless effect finally has one

Registered as a metric in section 1.4 because it *"has surfaced post-hoc twice with no
registered home."* Fraction of cells producing a **non-empty** predictive certificate:

| arm | sigma = 0.10 | sigma = 0.25 |
|---|---|---|
| `versionb` | 0.7892 | 0.4225 |
| `versionb_predictive` | 0.7883 | **0.4267** |
| `versionb_random` | 0.7617 | 0.3925 |

At sigma = 0.25 the predictive straddle certifies **more often** than the latent one
(0.4267 vs 0.4225) and markedly more than random
(0.3925) — D21's effect, now in a committed column at 24 cells. **At
sigma = 0.10 the ordering does not hold** (0.7892 vs
0.7883), so the advantage is not general and must carry its
cell.

### 38.8 What Version C is, now that it is measured

**Form 1: section 1 + section 3, no trust region, no Stage 0.** Two plate rounds, zero new
wells beyond Version B's, parity **beaten** at sigma=0.10 under a terminal rule the method
declares as its own, the hard stop cleared, and the regime detector shipped as a
**documented failure** rather than a claim.

## 39. ⭐⭐⭐ **SPADE ENTERS E7** — and at σ=0.10 rule P beats the oracle-best ceiling

SPADE was absent from §36's tables for a mundane reason, not a principled one:
`step0-oracle-best.json` carried only `versionb_plate1_ceiling` at **40 wells**, and a
40-well ceiling is not comparable to eight 48-well arms. **The object under test was missing
from the result that matters most.** `results/e7-oracle-best-fill.json` closes it — 700
rows, **all at 48 wells**, **0 gate failures**: `lhs`, `sobol`, `random` and `plate1_only`
were regenerated alongside and reproduce `step0`'s committed `oracle_best` at **\|Δ\| = 0**,
which is what vouches for SPADE's column. Zero new experiments; campaigns are regenerated
deterministically through `replay.regenerate`.

### 39.1 σ = 0.25 — SPADE sits with the spread arms, not with `doe`

| arm | gap rule A | gap rule P | shift | Wilcoxon |
|---|---|---|---|---|
| **`doe`** | +0.0361 | **+0.1396** | **+0.1035** | 4.95e-08 |
| `lhs` | +0.0475 | +0.0339 | −0.0136 | 6.35e-02 |
| `qlognei` | +0.0698 | +0.0452 | −0.0246 | 5.41e-03 |
| `sobol` | +0.0730 | +0.0057 | −0.0673 | 7.72e-07 |
| **`versionb` (SPADE)** | **+0.0742** | **+0.0199** | **−0.0543** | **1.76e-09** |
| `qlogei` | +0.0797 | +0.0477 | −0.0320 | 1.11e-03 |
| `random` | +0.1251 | +0.0277 | −0.0975 | 2.99e-11 |

**SPADE gains 0.0543 from the non-maximising rule** — more than `qlogei`, `qlognei` and
`lhs`, less than `sobol` and `random`. §34.2's caveat holds and is now measured against
SPADE's own 48-well column: **the gain is general to spread designs and `random` still gains
more.** `doe` remains the only arm the rule *hurts*.

### 39.2 🔴⭐⭐⭐ σ = 0.10 — five arms post a NEGATIVE identification gap

| arm | gap rule A | gap rule P | shift | Wilcoxon | boot 95% CI |
|---|---|---|---|---|---|
| `sobol` | +0.0217 | **−0.0171** | −0.0387 | 1.69e-05 | [−0.0544, −0.0234] |
| `lhs` | +0.0232 | **−0.0031** | −0.0263 | 2.12e-04 | [−0.0393, −0.0129] |
| **`doe`** | +0.0348 | **+0.2184** | **+0.1835** | 1.60e-09 | [+0.1387, +0.2307] |
| `versionb_random` | +0.0357 | **−0.0125** | −0.0482 | 8.40e-08 | [−0.0632, −0.0332] |
| `qlognei` | +0.0373 | +0.0194 | −0.0179 | 4.52e-06 | [−0.0251, −0.0106] |
| `qlogei` | +0.0378 | +0.0207 | −0.0171 | 3.54e-03 | [−0.0280, −0.0065] |
| **`versionb` (SPADE)** | **+0.0393** | **−0.0075** | **−0.0468** | **3.04e-07** | [−0.0623, −0.0304] |
| `versionb_predictive` | +0.0412 | **−0.0088** | −0.0500 | 3.09e-08 | [−0.0642, −0.0347] |
| `random` | +0.0728 | +0.0026 | −0.0701 | 5.32e-10 | [−0.0863, −0.0534] |

**A negative identification gap means the terminal rule found a point BETTER than any well
the campaign actually visited.** `oracle_best` is the regret of the best *visited* well; a
rule that only picks among visited wells cannot go below it. **The posterior-mean argmax is
not restricted to the sampled set**, and at σ=0.10 it lands outside it, on a better point,
for **all three SPADE arms plus `lhs` and `sobol`**.

**So "identification gap" stops being a gap and becomes an extrapolation margin.** The
ceiling is not a ceiling once the terminal rule is allowed to propose an unsampled point.
This is the mechanism behind D20 stated at its most literal: with clean data the GP's
posterior mean is a *better* guide to the optimum than the best observation, and every arm
whose design supports a decent fit exploits that — while `doe`'s quadratic stationary point
goes **+0.2184** in the opposite direction.

**Correction to §36.2's framing.** That section reported the σ=0.10 rule-A spread as
**0.0029** and called the arms indistinguishable. **That figure is over the three arms q57
carried.** Across the nine arms now available it is **0.0511**, and the rule-P spread is
**0.2354**. The three-arm statement remains true of those three arms; *"under rule A all
arms are equal at σ=0.10"* would be false and is not claimed. Every spread in the file
carries its arm list precisely so this cannot be misread again.

### 39.3 What this does and does not say about SPADE

**Says:** SPADE's certificate machinery is not what drives its rule-P gain — `versionb`,
`versionb_random` and `versionb_predictive` shift by −0.0468, −0.0482 and −0.0500, which are
**indistinguishable from each other**, and `lhs` and `sobol` are in the same band. **The
wells earn the gain; the selection criterion does not.** That is the same conclusion §34.2
reached at σ=0.25 by a different route, now confirmed at 48 wells with SPADE's own column.

**Does not say:** that SPADE is worthless. E7 measures *identification*, not certification.
SPADE's claim is a calibrated conservative set, and **no E7 column touches that.**

---

## 40. 🔴 VERSION C — the loophole audit. Three claims do not survive it, including my own headline.

**Written after both re-scores and the component run committed.** Every item below is a
defect found in **Version C's own results**, not in another track's. Each is stated with
what survives, because a retraction that leaves nothing standing is usually an overcorrection.

### 40.1 🔴 K-C1's bar mixes estimands. "Beaten" is withdrawn; **parity survives.**

`r*` is registered as *"the best committed regret at this (d, σ) cell, read from
`e2-grid.json`"* — **and that column is rule A.** Version C's number is **rule P**.

This repository's own Fix 1 registration (`OPEN-QUESTIONS.md`) forbids exactly this:

> *"A rule-P regret is also **not comparable to any published rule-A number**: they are
> different estimands, and every table that carries both must say which column is which."*

| bar | value | Version C | gap | |
|---|---|---|---|---|
| registered `r*` — **rule A** | 0.0808 (`qlognei`) | 0.0792 | **−0.0016** | below the bar |
| like-for-like — **rule P** | **0.0627** (`qlogei-addonly`) | 0.0792 | **+0.0165** | above it, **inside SESOI** |

**Both are true; only the second compares like with like.** The kill is evaluated against
the bar as registered — a registered kill is not silently re-specified — but
**"K-C1 beaten, not merely met" is withdrawn.** The defensible claim is the one C0 already
made and §8 of the spec already required: **parity is the goal and parity is the claim.**

`analyse_versionc_form1.kc1` now carries both bars and the `estimand_mismatch` flag, so the
mismatch cannot be quoted away.

### 40.2 🔴 §4's registered prediction FAILS — and my own verdict function had the confound

`results/versionc-components-family.json`, 1,200 rows, hill + hartmann6, both σ, 25 seeds,
3 arms. Registered before any component number existed: *largest on hartmann6, near-zero on
hill; if it helps everywhere equally, something is wrong.*

**The first verdict printed "DOES NOT HOLD" for the wrong reason.** A region that certifies
nothing has `n_components = 0`, and averaging that in measures **emptiness, not
multimodality**:

| family | certifies **nothing** |
|---|---|
| hill | 27.0% |
| **hartmann6** | **89.7%** |

The reported 0.27 against 2.00 was almost entirely an emptiness contrast wearing a
component contrast's name.

**Conditioned on non-empty regions — the only place the prediction is defined:**

| family | defined n | mean components | **>1 component** | box gain |
|---|---|---|---|---|
| hill | 438 | 2.75 | 42.5% | +0.000619 |
| hartmann6 | **62** | 2.65 | **64.5%** | +0.000528 |

**The verdict still fails, and the failure splits.** hartmann6 **is** more often
multi-component — 64.5% against 42.5%,
the direction predicted — but its mean component count and box gain are both **slightly
lower** than hill's. So the prediction fails on the **magnitude** metrics while the
**frequency** metric supports it. Reported as that split rather than collapsed to a word.

**And the box gain is near-zero on both** (+0.000619, +0.000528).
**§4's decomposition buys almost nothing on either family at this budget.**

An `UNDERPOWERED` branch was added: below 30 defined rows the honest answer is not "does
not hold" but *"the family barely certifies, so there is almost nothing to decompose"*.
hartmann6 clears it at 62, so the verdict stands.

### 40.3 The σ-comparison in §38.4 rests on unequal, self-selected populations

§38.4 reports the selection bias as **~4× larger at σ=0.10 than σ=0.25**. The `n` behind
those means are **not** comparable: 10,956 against 6,498 at α=0.50, and **7,002 against
1,812** at α=0.95. Non-empty certificates are far rarer at σ=0.25, and the ones that
survive are the **easy** ones — so the σ=0.25 mean is taken over a self-selected, better-
behaved subset.

**The direction is safe** — the bias is real and positive at both σ, and the α-ordering
holds within each σ. **The 4× is not**, and should be quoted as *"larger at σ=0.10"* without
the multiplier until it is measured on a matched population.

### 40.4 What survives the audit

* **The C0 gate result (§32)** — 600 rows, double-gated at |Δ| = 0, and the branch is a
  decision rule on a measured number. Unaffected.
* **K-C2 and K-C3** — but only as **structural** passes (§38.3), which was already stated.
* **The selection bias itself (§38.4)** — real, positive at both σ, rising with α. Only the
  cross-σ multiplier is withdrawn.
* **K-C7 (§37)** — the one-shot pass ran against a frozen rule; 0/50 both families.
* **Non-vacuity (§38.7)** — already carried its own caveat that the ordering fails at σ=0.10.

### 40.5 The loophole that remains open, and cannot be closed by re-scoring

**Version C has never been run as a method.** Every number in §32, §38 and §40 is
**Version B's wells scored under Version C's rules**. That is exactly what C0 was designed
to measure and it is not a defect in the measurement — but it means **no claim here is
evidence that a lab running Version C prospectively would see these numbers.** The three
scoring changes cannot be validated by re-scoring the campaigns they were designed against.

---

## 40. Three Phase 2–4 results that had no section here — and one of them is a trap

Joseph asked that every result reach this document. An audit of all committed
`results/*.json` against this file found the Phase-1 studies (`q34`–`q58`, `k6*`, `q42`,
`q47`, `q50`) are documented in `RESULTS.md`, `CLAIMS.md` and `K6-TECHNICAL-REPORT.md` —
this file is the SPADE evaluation, not a global index. **But three Phase 2–4 results
appeared only in `HANDOFF.md` / `OPEN-QUESTIONS.md` / `OVERNIGHT-LOG.md` and nowhere here.**

### 40.1 P1 — the kernel arms are **VALIDATED**, and the kill did not fire

`results/p1-kernel-gate.json` · verdict **`VALIDATED`**.

The registered kill: *"\|Δ\| = 0 on all 2,800 re-scored rows → the committed kernel-arm rows
are validated retroactively and Amendment A1 becomes citable. Any Δ ≠ 0 → the committed
kernel-arm rows are **WITHDRAWN**."* Note the phrasing — **withdrawn, not repaired by
re-running.**

**Coverage: 2,400 K6 rows + 400 K6b rows = 2,800 of 2,800 registered**, 100 gate campaigns,
plus 1,320 / 220 control rows. **`error: null`.** So **Amendment A1 is citable**, and the
`qlogei-add` / `qlogei-addonly` columns that appear in §34 and §38's arm tables rest on a
gate that was actually run rather than assumed.

### 40.2 🔴 P4 `coord` — AUPRC now exists, and the plain column is **prevalence in disguise**

`results/p4-coord.json`, 1,200 K6 rows + 200 K6b rows, d=6, σ=0.25. The four `auprc_*`
columns were added by a re-score gated at **\|Δ\| = 0 over all 50 rows** (the runner already
computed them; the committed file predated that edit). `coord` was the **only** arm without
them — and since §24 superseded AUC by error volumes, an arm missing AUPRC was missing from
the metric that replaced the one it had.

| `tau_frac` | prevalence | AP baseline (minority) | `auc_pred` | `auprc_pred` | `auprc_minority_pred` | lift over baseline |
|---|---|---|---|---|---|---|
| 0.60 | 0.9211 | 0.0789 | 0.6626 | **0.9544** | 0.1187 | **1.50×** |
| 0.75 | 0.7495 | 0.2505 | 0.6446 | 0.8270 | 0.3049 | 1.22× |
| 0.85 | 0.6029 | 0.3971 | 0.6413 | 0.6961 | 0.4481 | 1.13× |
| 0.95 | 0.4696 | 0.4696 | 0.6476 | 0.5595 | 0.5739 | 1.22× |

**`auprc_pred` falls from 0.954 to 0.560 across the ladder and this is NOT the map getting
worse.** Prevalence falls from 0.921 to 0.470 over the same rows, and plain AUPRC's baseline
*is* the positive rate. **The column is tracking the base rate, not the classifier.** Read
without its baseline it would license a confident and entirely false statement that `coord`'s
map degrades sharply with `tau_frac`.

**What the map actually does is nearly flat.** `auc_pred` moves only 0.6413–0.6626 across the
whole ladder, and the minority-AUPRC lift over baseline is **1.13–1.50×** — modest, and
**not monotone** (it dips at 0.85 and rises again at 0.95). A real trend would not do that.

This is §24's argument arriving from a new direction: **a metric quoted without its
attainable floor is not a measurement.** It is also why `ap_baseline` and
`ap_baseline_minority` travel on every `p6-families` row.

### 40.3 P5 — the τ quantile table

`results/p5-tau-quantile.json`, **232 rows** over `(family, dim, instance)` carrying `tau_q`,
`true_frac_above_tau`, `grid_min`/`grid_max`, `n_selected` and a `sensitivity` flag. This is
the table §20 draws on for the finding that **the certifiability ceiling is ordered by max
`tau_q`, not by grid range** — the correction to the claim I repeated from the brief without
checking it.

**None of these three changes any conclusion elsewhere in this document.** They are recorded
because a result that exists only in a decision log is a result the next reader will not find.

---

## 41. 🔴⭐⭐⭐ P8 — **SPADE's certificate does not FAIL off hill. It DECLINES TO ANSWER.** *(IN FLIGHT)*

> **⚠️ IN FLIGHT.** The run is at ~400/1000 with `hill` and `hartmann6` complete and `levy`,
> `rosenbrock`, `ackley` pending. **No number below is a finding yet.** This section is
> replaced when `results/p8-certificate-families.json` promotes. It is written now because
> the two completed families already answer the registered question, and because the shape
> of the answer changes what the remaining families are evidence *about*.

**SPADE (`versionb`), α = 0.95, n = 50 campaigns per cell, 4,096 draws, d=6, σ=0.25.**
Containment is `ce_empirical` — the validated statistic. `ce_contain` is **circular**
(`conservative_estimate` selects on it, so it cannot fall below α) and the analyser raises
rather than reporting it.

| | hill | hartmann6 |
|---|---|---|
| cells where the α=0.95 set is **empty in all 50 campaigns** | **6 of 24** | **22 of 24** |
| cells with any scored campaign | 18 of 24 | **2 of 24** |
| containment where scored | **1.000** in 17 of 18 (0.980 once) | **0.900** (n=10) and **0.500** (n=2) |
| mean `alpha_star` range | 0.083 – 1.000 | **0.000 – 0.511** |

Only at γ = 0.99 does hartmann6 certify anything at all: **10 of 50** campaigns at
τ_frac = 0.60 and **2 of 50** at 0.75. Everywhere else the conservative set is empty in
every campaign.

### 41.1 The registered prediction is wrong in an informative way

It said *"containment at γ=0.95 will be LOWER off hill."* **Containment off hill is mostly
UNDEFINED**, because there is no set to measure. That is a third outcome the registration
could not express — **the same shape as E7's failure in §34.3**, and the second time in this
project that a two-branch registration has met a sign-flip or a category change.

### 41.2 🔴 The trap this would have walked into

`ce_empirical` is `nan` for an empty set — an empty certificate is *vacuously* contained.
**Had empties counted as successes, hartmann6 would report containment 1.000 at nearly every
cell**: a perfect score for a method that certified nothing, fifty times out of fifty, and it
would have read as *better* than hill's 0.980 at γ=0.99.

The analyser therefore drops empties from the numerator **and** the denominator, carries
`n_scored` beside every rate, and returns `None` — never 1.0, never 0.0 — for a cell that
certified nothing. `tests/test_p8_analysis.py` pins all three.

### 41.3 What this is NOT

**Not a kill.** §29 withdrew *"the certificate fails below nominal at high assurance"* as a
512-draw artefact, and P8 runs at 4,096. This records where containment sits.

**Not "hill is special and the others are broken".** Hill is empty in **6 of 24** cells
itself — emptiness is driven by `(γ, τ_frac)` as well as by family, and both axes move it.
The honest contrast is **6 of 24 against 22 of 24**, not "hill works, hartmann6 does not".

**Not yet a cross-family result.** Two families of five. `levy`, `rosenbrock` and `ackley`
are pending, and §20's ceiling ordering predicts they will differ from each other.

### 41.4 What it already means for α\*

§31 declared α\* measures **willingness to certify**. Hill's mean α\* is at or near 1.000
across most of the ladder; hartmann6's is **0.000 to 0.020 in 17 of 24 cells**. The two
statements — "the set is empty" and "α\* is ~0" — are **the same fact in two languages**, and
their agreement here is the first off-hill evidence for §31's reading.
