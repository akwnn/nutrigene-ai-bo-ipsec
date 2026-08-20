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
| **K6** | does the design-space ranking differ from regret? | ✅ **COMPLETE**, but wrong classical arm — see §4.2 |
| **K6-spread** | same, with a true one-shot spread arm | 🔄 **RUNNING** |
| **K6b** | joint certification, `alpha*` | 🔄 **RUNNING** |
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

### 4.2 K6 — the two rankings disagree in 24 of 24 cells ✅ (with a caveat that matters)

**Result.** 6,000 rows, 50 instance-seeds, 0 gate failures.

| | ranking |
|---|---|
| simple regret | `doe` **0.0958** < qlogei-add < qlognei < qlogei 0.1553 < qlogei-addonly |
| map quality (AUC) | qlognei > qlogei-addonly > qlogei-add > qlogei > **`doe`, last in all 24 cells** |

`doe` − `qlogei` on AUC: **−0.09 to −0.12, p < 0.002 in every cell**, n=50 paired.
**Zero of 24 cells agree.**

**What it signifies — and what it does not.** The design-space object does not measure
what regret measures. That much is now data.

But **`doe` is not a spread design.** It is 20 screening runs, then a 27-run
central-composite design confined to a *sub-box*, then one confirmation — with **two of
six axes pinned by the screen** (the runner logged `active=4` throughout). So these 24
cells establish, decisively, that **screening is fatal for a design-space deliverable**:
an arm that never varied two factors cannot state a range for them, and a batch record
needs a range for every factor.

They do **not** establish that a one-shot spread design maps better than adaptive search,
because no one-shot spread arm was in the run. That was an arm-selection error on our
part, not a property of the data. `lhs`, `sobol` and `random` are the genuine one-shot
arms and are **RUNNING** now.

### 4.3 A1 — the additive kernel does not rescue itself on the map ❌ NULL

**Why we asked.** Q30 measured that doubling held-out R² moved regret by 0.0015 (p=0.71).
If the same campaigns gained on the certification object, that would be the cleanest
figure the project could produce: *doubling accuracy is worth nothing for choosing a point
and a great deal for certifying a region.*

**Result.** It is not there. `qlogei-add` AUC **+0.0143 [−0.0094, +0.0412], p=0.52**;
`qlogei-addonly` **+0.0235 [−0.0059, +0.0542], p=0.13**.

**What it signifies.** The accuracy channel is closed for *both* deliverables, not just
for regret. A single-instance smoke test had shown `alpha*` of 0.30 against 0.03 and it
did not survive n=50 — which is why it was reported as a hypothesis at the time.

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

## 6. What it all signifies so far

**The design-space object is genuinely different from regret.** 0 of 24 cells agree, with
large and consistently significant contrasts. That part of the thesis survives.

**But the direction currently runs against the proposal.** The arm that wins on regret
loses on the map, everywhere. Until the spread arms land we cannot say whether that is
about *screening* (which we can prove) or about *spread designs in general* (which we
cannot yet).

**Two of the proposal's supporting arguments are dead**: the cost frontier has no test bed,
and the additive-kernel figure is null. **One of our own predictions is retracted**: the
certified regions are conservative, not anti-conservative.

**One argument is stronger than when it was proposed**: screening is fatal for a
design-space deliverable. It needs no new method, no new campaign, and it does not depend
on SPADE winning anything.

---

## 7. What needs to be done

**Immediate, running now.**
1. **K6-spread** — `lhs`, `sobol`, `random` through the same scorer. Without it the
   registered question is unanswered. *This is the decisive one.*
2. **K6b** — `alpha*` and conservative excursion sets, for a joint rather than pointwise
   guarantee.

**Then, in order.**
3. **Decide on the registered tree.** Map ranking matches regret → stop and write up what
   is banked. Diverges with spread ahead → build Version B. Diverges with clustered ahead
   → different paper: *the design-space deliverable favours adaptive designs*.
4. **K0** — does sup-norm error govern regret where R² does not? The only route by which
   the deleted shape-constrained model returns.
5. **K1** — what replicate-identified noise buys, and whether the `Yvar`-to-reading
   coupling explains the measured under-smoothing (fitted lengthscale ÷ true feature width
   is 0.56–0.70).
6. **K3** — confirm-and-average versus confirm-and-replace, the variant Q58 registered as
   unrun.

**Lab, blocking nothing but deciding what can be claimed.**
7. **Day-0 covariate `R²`** — prospective, per well, day 0 and endpoint.
8. **Reagent cost per well** — decides whether "matched plates, not matched wells" is
   decisive or merely suggestive.

**Explicitly not being done.** NUTS and shape-constrained additive models (closed by Q30
unless K0 reopens it); covariate adjustment as an algorithm stage (needs a real plate); the
55-well budget (cannot be gated against any committed column); TuRBO and OCBA (different
estimand — see the separate plan); the cost frontier (§4.6).
