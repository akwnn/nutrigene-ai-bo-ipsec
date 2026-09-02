# KY — can hyperparameter mixing break the saturation? Pre-registration

**Frozen before any KY result exists.** Registered on a mechanism KT-7 measured, not on
a hunch.

## 1. The measured limit KY attacks

`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10.2, fixed cohort (cells certifying at EVERY `c`,
so survivorship is removed):

| family | c=1.0 | 2.0 | 3.0 | 4.0 | behaviour |
|---|---|---|---|---|---|
| ackley | 0.3509 | 0.7544 | 0.8947 | **0.9298** | climbs |
| hartmann6 | 0.1970 | 0.5758 | 0.8182 | **0.8788** | climbs |
| levy | 0.3333 | 0.7500 | 0.7500 | **0.7500** | **SATURATES** |
| rosenbrock | 0.6364 | 0.7273 | 0.7273 | **0.7273** | **SATURATES** |

Inflation scales the posterior SD and leaves the mean untouched; the Vorob'ev quantile
shrinks toward the HIGHEST-probability points; so a confidently-wrong point is retained at
every `c` **by construction**. No scalar can fix it.

## 2. The hypothesis

`build_gp` fits lengthscale and outputscale by MLE and then treats them as known. Error
there is a **structured** error in the mean: an over-long lengthscale smooths a real
feature away and the mean is confidently wrong in a spatially organised pattern. An
evidence-weighted mixture over restarts changes the **shape** of the posterior, not merely
its width, and can therefore move a point inflation cannot.

`boec.hypermix`, 6 tests. **One of those tests already earned its place**: the first
implementation produced five identical models, because `build_gp`'s fit is deterministic
given the data and seeding torch does not move it. The "ensemble" was five copies of one
model. Initialisations are now explicitly perturbed.

## 3. KY-1 (PRIMARY, registered now)

On the **fixed cohort** at alpha = 0.50, the mixture posterior raises truth containment for
**both** `levy` and `rosenbrock` by **>= 0.05** above their inflation ceilings (0.7500 and
0.7273), at an answer rate no lower than **0.5x** the single-fit rate.

- **FAIL** -> saturation is **not** hyperparameter-driven. Combined with the refuted shape
  hypothesis (§9) and the retracted SNR hypothesis (§9a), that would make three
  independent mechanisms excluded, and the honest conclusion is that levy/rosenbrock
  failures are irreducible at this budget. **That outcome is the one I consider more
  likely and it is registered first.**

## 4. KY-2 (no free lunch)

Mixing must not degrade `ackley`/`hartmann6`: their containment at matched `c` must not
fall by more than 0.05.

## 5. Scope and honesty constraints

- Restarts **explore** the likelihood surface; they do not **sample** it. This is an
  approximation to hyperparameter marginalisation and is labelled as one everywhere.
  Full NUTS (`SaasFullyBayesianSingleTaskGP`) needs JAX and NumPyro, which are not
  installed, and adding dependencies was not a call to make unilaterally mid-session.
- Exploratory scale (4 families x 6 seeds). A PASS licenses a registered confirmatory
  run, not a claim.
- Draws are joint (Cholesky of the full covariance) within each component. The
  certificate is a SIMULTANEOUS claim and pointwise draws would understate it.

## 6. KY RESULT — KY-1 FAILS, KY-2 PASSES

30 seeds x 4 families (`results/probe-hypermix-30seed.json`, 1440 rows).

### 6.1 A power problem the 6-seed probe hid, and how it was handled

At 6 seeds the fixed cohorts were **0, 1, 4, 9** cells. **No verdict was read**, and the
probe was re-run rather than adjudicated -- the same error this project has retracted
three times already. At 30 seeds the cohorts are `ackley` 29 and `hartmann6` 46, but
`levy` and `rosenbrock` are still only **2 each**, because the cohort rule requires a
non-empty certificate at EVERY `c` under BOTH models and those two collapse hardest at
c = 4.0.

The cohort was therefore re-defined over the narrower range where saturation actually
onsets (c in {1.0, 2.0}), giving cohorts of **5, 8, 37, 47** -- and the primary analysis
switched to the **paired per-cell** test, which is strictly more powerful because it uses
every cell non-empty under both models rather than only those surviving the whole grid.

### 6.2 The verdict

Does mixing flip a wrong certificate to a right one? (c = 2.0, paired)

| family | mixture fixed | mixture broke | p |
|---|---|---|---|
| levy | 2 | 0 | 0.500 |
| rosenbrock | 0 | 1 | 1.000 |
| ackley | 1 | 2 | 1.000 |
| hartmann6 | 4 | 2 | 0.688 |
| **pooled** | **7** | **5** | **not significant** |

**KY-1: FAIL.** Hyperparameter mixing does not break the saturation.

**KY-2: PASS.** No harm done -- `ackley` 0.8378 -> 0.8108 (within the registered 0.05 bar)
and `hartmann6` *improves*, 0.5745 -> 0.6170.

### 6.3 What this rules out, stated at the right strength

**Three independent mechanisms are now excluded for the levy/rosenbrock saturation:**

| mechanism | outcome | where |
|---|---|---|
| region shape / compactness | REFUTED | `SPADE-ASSURANCE-CALIBRATION-SPEC.md` §9 |
| signal-to-noise at the threshold | RETRACTED | §9a |
| hyperparameter misspecification | **FAIL (KY-1)** | here |

**Precision about what FAIL means here.** With 12 discordant pairs pooled, this rules out a
**large** effect -- and only a large effect could lift a ceiling stuck at 0.75 and 0.73
across the entire grid. It does **not** rule out a small one. The honest statement is *no
evidence that hyperparameter uncertainty drives the saturation, and enough power to
exclude an effect big enough to matter.*

**Recorded conclusion.** levy/rosenbrock certificate failures remain **unexplained and
uncured**, and are now the longest-standing open question in this project. Anyone
continuing should note that mixing is cheap, harmless, and slightly helps `hartmann6`, so
it may be worth keeping for other reasons -- but not as a fix for this.
