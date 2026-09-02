# EXPLORATORY — model disagreement as a warning signal

**NOT PRE-REGISTERED. Exploratory, found after seeing the confirmatory result.**
Treat as a hypothesis for a fresh test, not as a finding. Person B, 2026-08-08.

Reproduce: `results/e4-disagreement-exploratory.log`.

---

## What was tried, and why

Our pre-registered comparison had three warning systems and the sophisticated
one did not beat a ruler. But we already fit **four different models to
identical data** and never used that fact.

So: when four models trained on the same 48 measurements **disagree with each
other** about what happens at a recipe, is that a better warning than any one
model's own confidence?

Costs nothing extra — the four predictions are already computed.

## Result

25 landscapes, the pre-registered regime, 512 candidate recipes each. Higher is
better; this is how well each signal tracks where the traditional fit is
actually wrong.

| warning signal | how well it tracks real error |
|---|---|
| plain distance to nearest measurement | +0.412 |
| GP's own uncertainty | +0.437 |
| **disagreement between all four models** | **+0.529** |
| disagreement between the three *non-GP* models | +0.408 |

| paired comparison | difference | significant |
|---|---|---|
| disagreement vs plain distance | **+0.117** [+0.098, +0.136] | **yes**, p < 0.0001 |
| disagreement vs GP uncertainty | **+0.092** [+0.068, +0.114] | **yes**, p < 0.0001 |
| disagreement *without* the GP vs plain distance | −0.004 [−0.032, +0.025] | no |

**Every one of the 25 landscapes points the same way** on the first two rows.

## Why this is interesting rather than just a bigger number

**The third row is the important one.** Disagreement among the three
polynomial-ish models is worth *nothing* — it matches plain distance exactly.
The signal only appears when the GP is one of the disagreeing voices.

That fits the theory rather than contradicting it. A GP's uncertainty is
essentially a distance function, so on its own it tells you *where you are*.
What it adds to an ensemble is a genuinely different **functional form** — one
that reverts toward its prior far from data while the polynomials keep
extrapolating their trend. The disagreement between those behaviours is
information that neither a distance nor any single model's variance contains.

Stated more carefully: **single-model variance expresses uncertainty given that
the model form is right. Disagreement across model families expresses doubt
about the form itself** — which is exactly the quantity our whole scientific
argument says the polynomial's interval cannot represent.

## It does not collapse far from data — the documented failure mode, tested

The obvious way this idea dies: if all four models revert toward the same flat
answer far from data, they stop disagreeing exactly where you need the warning.
That is documented behaviour for neural-net ensembles (Kang et al.,
arXiv:2310.00873), so it had to be checked rather than assumed.

Swept over how far out we ask, 15 landscapes, κ = 0.6:

| how far out | GP's uncertainty | plain distance | **disagreement** | disagreement advantage | size of disagreement |
|---|---|---|---|---|---|
| 1.2× | +0.020 | +0.080 | **+0.299** | +0.219 [+0.165, +0.270] | 0.026 |
| 1.5× | +0.412 | +0.351 | **+0.525** | +0.175 [+0.129, +0.221] | 0.088 |
| 2.0× | +0.795 | +0.486 | +0.767 | +0.281 [+0.225, +0.343] | 0.163 |
| 3.0× | +0.827 | +0.650 | +0.776 | +0.125 [+0.044, +0.207] | 0.594 |
| whole cube | +0.661 | +0.572 | **+0.755** | +0.183 [+0.108, +0.257] | 3.104 |

**No collapse.** The disagreement grows steadily the further out you ask
(0.026 → 3.104) and beats plain distance at every distance tested.

### The row that matters most is the first one

**At 1.2× — the distance the published study actually extrapolated — both
pre-registered warning systems are close to useless.** The GP's own uncertainty
scores +0.020 and plain distance +0.080; neither tells you much. Disagreement
scores +0.299.

So the regime where our motivating case study actually lived is the regime where
single-model uncertainty fails hardest, and where disagreement helps most in
relative terms. If that holds up under a proper pre-registered test, it is the
practically useful version of this whole line of work.

## What this does NOT license

- **It is not a result.** It was found by looking at the data after the
  confirmatory analysis. Reporting it as though it were pre-registered would be
  precisely the practice this project has spent effort avoiding.
- **The honest route is a fresh pre-registration and a fresh test**, ideally on
  landscapes not used here, or at least declared before running.
- The effect is large enough that it should survive that. If it does not, that
  is worth knowing too.

## Suggested next step

Pre-register a version 3 with disagreement as a fourth scorer, stating that it
was suggested by exploratory analysis of the version-2 data, then run it on an
extended ensemble. Person A extending the ensemble to 40 landscapes would give
both the power upgrade and a partly-fresh sample in one run.
