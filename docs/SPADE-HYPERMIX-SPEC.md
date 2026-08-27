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
