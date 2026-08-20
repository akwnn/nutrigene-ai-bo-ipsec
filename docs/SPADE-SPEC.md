# SPADE — Single-Plate Assured Design Envelope

**Specification as received, 2026-08-20.** Successor to `docs/ODIN-SPEC.md`.

> ⚠️ **Read `docs/ODIN-VERDICT.md` §7 and the plan at
> `docs/superpowers/plans/2026-08-20-spade-go-no-go.md` before implementing.**
> Three claims in this document are contradicted by the repository:
> (a) K6 is not a re-score — no result file stores `X` or `Y`;
> (b) the certified-volume metrics may be identically zero for a spread design
> at n=48, d=6 (measured neighbour density is 0.49 per lengthscale, not 1.4);
> (c) Stage 2's stated mechanism is wrong — this repo's GP does **not** fit
> noise jointly, it is handed `train_Yvar` as known. Stage 2 survives with a
> different and stronger mechanism; see the plan, Task 2.
> This file is preserved verbatim as the object under review.

---

## Stage 0 — Capture the covariate (free, day 0)

Before the recipes have acted, record per well:

- confluence or cell count by imaging
- plate row and column
- cell batch, passage number

These cannot contain recipe effects because the recipes have not acted yet. That
is what makes subtracting them safe.

**Randomise which recipe goes in which well position.** Otherwise plate position
is confounded with factor level and the covariate cannot separate them.

---

## Stage 1 — Design (one plate)

**49-point strength-2 OA-LHS.** `scipy.stats.qmc.LatinHypercube(d, strength=2)`
with `n = p² = 49, p = 7, d ≤ 8`. Stratifies every 1D marginal and every 2D
projection.

**3 anchor points, each measured in triplicate.** Choose by centroid-nearest,
then farthest-point. Place the three replicate wells in different plate regions
so plate variation lands in σ̂ rather than hiding.

**Total: 55 wells.** Budget-match the baselines at 55, not 48. Edge wells are
blanks.

At exactly 48 you must drop to maximin-LHS, which loses the Stein guarantee. Do
not keep the citation if you take that path.

---

## Stage 2 — Adjust, then fix the noise

**Covariate adjustment.** `y_adj = y − θ(x_cov − mean(x_cov))`, θ from OLS of y
on the covariates. Report the achieved `r`. Variance drops by `r²`.

**σ̂ from replicates**, pooled within-anchor variance of the *adjusted* values.
6 degrees of freedom.

**Fit a plain Matérn-5/2 ARD GP with σ̂ plugged in and held fixed.** Not fitted.

This last line is the fix for your measured defect. Fitted lengthscale ÷ true
FWHM = 0.56 to 0.70 means the GP is eating noise as signal. That happens because
MAP fits lengthscale and noise *jointly*, and at n = 48 in 6D they are barely
separable, so the optimiser trades one against the other. Replicates break the
degeneracy from outside the likelihood.

Diagnostic: ls ÷ FWHM should move from 0.57 toward 1.0, and coverage from 76.4%
toward 95%. `lengthscale_diag.py` already computes the first.

No NUTS. No I-splines. Q30 measured 2× R² buying Δregret 0.0015, p = 0.71, so
the accuracy channel is closed and Stage 2 of the old spec stays deleted.

---

## Stage 3 — Regime test, from the first plate only

Compute, with no oracle access:

- measured additive share â from an ANOVA decomposition of the fitted GP on a
  Sobol grid
- count of distinct local maxima of the posterior mean whose LCB clears the
  second-highest UCB
- residual variance after an additive-only refit, divided by σ̂²

Freeze the rule on hill, levy, rosenbrock. Score once on hartmann6, ackley.

```
if smooth and coordinate-wise unimodal:  go to Stage 4, ship in ONE round
else (deceptive):                        go to Stage 3b
```

**3b:** one batch of qLogNEI seeded from the fitted model, then Stage 4.

---

## Stage 4 — The deliverable

On a 20k Sobol grid, from the posterior:

**Probability map.** `P(f(x) ≥ τ)` everywhere. This is the ICH Q8 object.

**Certified set: inscribable hyperrectangle.** This is what goes in a batch
record: a range per parameter.

```
start at argmax LCB
repeat until no axis can expand:
    for each axis j:
        expand [l_j, u_j] by the largest step keeping
        min LCB over the expanded slab >= tau
return the box, its volume, and the per-axis ranges
```

**Setpoint.** argmax posterior mean inside the box, for the nominal operating
point.

---

## Stage 5 — Confirmation, if a second round is affordable

**Place the wells on the weakest points of the box boundary, not on the peak.**

The box volume is limited by `min LCB over the box`, which sits on the boundary.
Precision at the peak buys you nothing; the peak is already certified. Precision
at the constraining face is what lets the box grow.

Decide by the **mean** of first and confirmation readings, never by the
confirmation alone.

This is where the design-space reframe pays off algorithmically. Q58 found
confirm-top-3 moved the classical arm 0.0958 → 0.1437, badly hurt. It was
confirming the wrong thing: near-tied peaks, where the first reading was already
trustworthy. Confirming the boundary is a different allocation with a different
mechanism, and it is the one the deliverable actually implies.

---

## What is new versus what exists in the repo

| Stage | Exists | New |
|---|---|---|
| 0 covariate | — | **all of it** |
| 1 OA-LHS n=49 | `spread_gp` is plain LHS | OA strength-2, anchors |
| 2 GP with σ̂ fixed | `build_gp`, `_plug_in_yvar` | wiring σ̂ from replicates |
| 3 regime test | `lengthscale_diag.py` has one statistic | **the frozen rule** |
| 4 design space | `constrained_argmax` | **probability map, certified set, box** |
| 5 boundary confirmation | `selection.py` | **boundary allocation, averaging** |

Four genuinely new pieces. The rest is wiring.

---

## What it beats them on

| | SPADE | classical RSM | batch BO |
|---|---|---|---|
| rounds | **1** (2 if deceptive) | 3 | 10 |
| regret | ~parity | 0.0958 | 0.1553 |
| certified box volume | **should win** | boundary partly covered | blind to the boundary |
| probability map quality | **should win** | fair | prior-only outside the cluster |
| small certified ball | loses | loses | **wins** |

Three claims: **rounds, design space, honest parity on regret.** Not four. The
regret column has about 0.01 left in it against a SESOI of 0.02, so nothing wins
there and claiming otherwise gets you caught.

The one loss is real and worth reporting: clustered BO puts ~40 wells at the
peak, so it certifies a small tight ball better than any spread design can. Say
so. A tiny certified ball gives almost no manufacturing flexibility, which is
precisely why ICH Q8 asks for a space instead of a setpoint, and that argument is
stronger when you have conceded the point.

---

## The claim

> On landscapes that are smooth and coordinate-wise unimodal, testable from the
> first plate, a single-plate orthogonal-array design with covariate-adjusted,
> replicate-identified noise produces a larger certifiable operating window and a
> better-calibrated design-space map than three rounds of RSM or ten rounds of
> batch Bayesian optimisation, at matched well count and one plate round. Simple
> regret is equivalent, not better. On deceptive landscapes it loses, and the
> regime test says which case you are in before you commit.

---

## Two things to do before the first line of code

**K6, five hours, no new wells.** Re-score the 200 stored campaigns under the
Stage 4 metrics. If the design-space ranking matches the regret ranking, Stages 4
and 5 add nothing and you have saved yourself building them. If it diverges, you
have your headline before you have written a runner.

**The `r` number.** Correlate day-0 against day-6 on any existing Nutrigene
plate. If `r < 0.4`, Stage 0 comes out and σ̂ rests on the replicates alone. If
`r > 0.7`, Stage 0 is half your variance and the calibration story gets much
stronger.

Neither blocks the build. Both change what you build.

---

## Metrics, as argued in the accompanying note

Three design-space deliverables, which do **not** favour the same arm:

**(a) Certified volume at 95%, small region.** Local-precision problem. BO
clusters ~40 wells near the peak, so locally `s ≈ σ/√40 ≈ 0.04`. **Clustered BO
probably wins.**

**(b) Probability map quality over the whole box.** Brier score or AUC of
`P(f(x) ≥ τ)` against `1{f ≥ τ}`. Always computable. **Spread should win
clearly.**

**(c) Largest inscribable hyperrectangle.** Requires knowing the boundary along
every axis, which a clustered design does not. **Spread should win, and this is
the practically relevant one.**

> There are two design-space deliverables — a certified operating window and a
> mapped design space — they favour opposite methods, and nobody has
> distinguished them.

**Correction applied in the plan:** (a) and (c) share the `LCB ≥ τ` predicate, so
at measured spread-design neighbour density both may be identically zero. The
plan replaces fixed-95% volume with a **certified-volume-versus-confidence
curve**, which is always defined and reports 95% as one point on it.

---

## Honest probabilities, as supplied

| claim | P | gated by |
|---|---|---|
| One-shot ties BO on non-deceptive families, 1 round vs 10 | 0.9 | already measured |
| Design-space ranking differs from regret ranking | 0.7 | K6 |
| Spread wins on hyperrectangle volume and map quality | 0.65 | K6 |
| Clustered BO wins on small certified volume | 0.6 | K6 |
| Nominal-95% certified regions are materially anti-conservative | 0.75 → **0.9** | E3 already measured latent coverage 0.7644 vs nominal 0.95 in every cell |
| Better σ̂ from replicates fixes calibration measurably | 0.6 | K1 |
| Any of this beats classical RSM on **regret** by > 0.02 | 0.15 | unchanged |
