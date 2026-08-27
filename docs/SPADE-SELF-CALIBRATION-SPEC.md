# SPADE self-calibration follow-up — pre-registration ("KS")

**Frozen before any KS result exists.** Registers the successor question to KR:
`docs/SPADE-EFFECTIVE-RESOLUTION-SPEC.md` §7 killed `k_eff` and, in doing so, split the
certificate's failure into **two mechanisms**. KS targets the one KR could not touch.

## 1. What KR established

KR-1 FAILED (LB 0.8175 against a 0.90 bar), KR-2 FAILED (`k_eff` dispersion 1138× against box
volume's 370×), KR-4 fired and `k_eff` is dropped. The informative part is why:

| family | median `k_eff` | fraction `k_eff` < 1 | truth containment |
|---|---|---|---|
| hill / levy / rosenbrock | 0.60 / 0.90 / 1.86 | 0.57 / 0.51 / 0.43 | 0.9939 / 0.8958 / 0.8930 |
| ackley / hartmann6 | **0.061 / 0.082** | **0.988 / 1.000** | 0.8889 / 0.8081 |

- **Resolution failure** (hill/levy/rosenbrock): regions span multiple correlation cells; a
  simultaneous claim accumulates failure opportunities with volume. Volume-conditional
  calibration repairs it — 0.9730–0.9988 held out (`SPADE-EFFECTIVE-RESOLUTION-SPEC.md` §1d).
- **Localization failure** (ackley/hartmann6): essentially every certified region is **smaller
  than one correlation cell**, and still fails 11–19% of the time. A sub-resolution region
  cannot fail a simultaneous claim by accumulating locations. The region is confidently placed
  in the wrong part of the box, and **no statistic computed from the region's own geometry can
  detect a placement error.**

## 2. The registered hypothesis

A misplaced region is a symptom of a surrogate that does not fit *this* landscape. That is
measurable from the campaign's own wells, without ground truth and without a family library, via
leave-one-out standardised residuals `z_i = (y_i - mu_-i) / sd_-i`:

    kappa_tail = max(|z|)                  PRIMARY   (see 2a)
    kappa_mean = sqrt(mean(z**2))          SECONDARY

`src/boec/selfcalib.py` (`loo_residuals`, `calibration_inflation`), TDD, 11 tests, committed at
`434a987` **before this spec was frozen**. The LOO identity is exact (asserted against `n`
brute-force refits), so it costs one factorization rather than `n` refits.

**Why `kappa_tail` is PRIMARY, decided before seeing any KS number.** The certificate is a
**simultaneous** claim — it fails if *any* point in the region is wrong. The a-priori-matching
diagnostic for a worst-case claim is a worst-case residual statistic, not an average one. A
landscape whose structure the kernel cannot capture (ackley's narrow spikes) produces a few badly
predicted wells while leaving the mean-square residual close to nominal. `kappa_mean` is reported
beside it as secondary and is **not** eligible to be promoted after the fact.

## 2a. Amendment, made before any campaign was scored

`kappa_tail` was first registered above as the **0.90 quantile** of `|z|`. A unit test written
while implementing it -- `test_calibration_tail_sees_localized_misspecification_that_the_mean_
hides`, on synthetic residuals, with **no campaign scored and no KS number in existence** --
showed that choice cannot detect the case it was chosen for: with 2 badly-predicted wells in 20,
the 0.90 quantile interpolates to **0.47**, *below* a uniformly-mediocre campaign's 1.5, because
the spikes sit exactly at the quantile boundary. On 48 wells a handful of bad predictions is
precisely the ackley signature.

**`kappa_tail` is therefore `max(|z|)`.** The amendment is recorded here rather than made
silently, it rests on a synthetic unit test alone, and it was applied **before** the runner was
extended or any campaign scored. The original registration is left in place above so the change
is visible rather than overwritten.

**Why this is family-agnostic by construction, not by empirical transfer.** KS never consults a
family library. A laboratory has one unknown landscape; a rule that must be told which family it
is looking at is not deployable. This is the property KR's cap lacked.

## 3. Falsifiable predictions, registered now

**KS-1 (PRIMARY — transfer).** A rule conditioned on **(box volume, `kappa_tail`)**, calibrated
on hill/levy/rosenbrock and applied **unchanged** to ackley/hartmann6, achieves held-out truth
containment with a one-sided 95% Clopper–Pearson lower bound **≥ 0.90**.
*Comparators, both already measured and fixed: box volume alone LB 0.8175 FAIL; `k_eff` LB
0.8175 FAIL.*
- **PASS** → SPADE has a family-general certificate rule. Adopt.
- **FAIL** → see KS-5.

**KS-2 (mechanism — the model knows it is bad).** Median `kappa_tail` on ackley/hartmann6 exceeds
median `kappa_tail` on hill/levy/rosenbrock by **≥ 20%**.
- **FAIL** → LOO residuals do not see the misspecification that causes localization failure, and
  KS-1 passing would be luck rather than mechanism. Report both.

**KS-3 (no free lunch — abstention floor).** KS-1's containment must not be bought purely by
abstaining: **answer rate ≥ 0.30** on ackley/hartmann6 at γ=0.95.

**KS-4 (Occam falsifier).** If `kappa_tail` adds nothing over box volume alone — same verdict on
KS-1, and separation of contained-from-failed improved by **< 0.25 SD** on the hard families —
then `kappa_tail` is **dropped**, exactly as `k_eff` was. The measured comparator is box volume's
1.22 SD separation on the hard families.

**KS-5 (the registered honest ceiling).** If KS-1 FAILS, the conclusion is recorded as: *no
run-time-observable statistic tested by this project (certified volume, `k_eff`, `alpha_star`,
Vorob'ev deviation, `kappa_tail`, `kappa_mean`) detects localization failure, and SPADE's
certificate is therefore valid only where the surrogate fits — a scope that must be declared in
advance and cannot currently be detected at run time.* This is consistent with, and would be the
second independent confirmation of, the automatic scope detector that already failed 0/50 on both
held-out families (`SPADE-RESULTS-AND-ANALYSIS.md` §3). **KS-5 is a result, not a failure to
report.** No further conditioning variable is tried without a new pre-registration.

## 4. Scope, data, and what is NOT run

Identical to KR §4 and unchanged: P8's registered grid, 5 families × 4 arms × 50 seeds, d=6,
σ=0.25, γ=0.95 primary; ackley/hartmann6 on the τ-quantile grid per
`SPADE-TAU-QUANTILE-SPEC.md` §6b. **No campaign is simulated and no certificate is recomputed.**
The KR runner is extended to emit `kappa_tail`/`kappa_mean` alongside the lengthscales it already
emits, from the same regenerated wells and the same GP fit.

**Regeneration gate unchanged:** `regret` and `n_wells` must reproduce the committed P8 row at
`|delta| = 0`. KR passed this 1000/1000; any failure here pauses KS and is reported, not patched.

**Noise term.** `loo_residuals` requires the covariance **including** the noise diagonal;
supplying the noise-free kernel would inflate every residual and manufacture a KS-2 pass. The
runner takes the likelihood's fitted noise from the same model object it reads lengthscales from,
and a unit test asserts the noise-free matrix is not silently accepted.

## 5. Statistics

Unchanged from KR §5. Two-variable conditioning uses a 5×5 quantile grid of
(box volume, `kappa_tail`); a cell is admissible when the one-sided 95% Clopper–Pearson **upper**
bound on its local failure rate is ≤ 0.10 and it holds ≥ 25 calibration campaigns; cells with
fewer are inadmissible (abstain), never assumed safe. Held-out evaluation is across-family for
KS-1/KS-2 and split-half by seed within a family.

## 6. What KS does not decide

KS is scoped to the certificate's conditioning variable. It does not test Plate-2 allocation
(KF-3/3b/3c stand; the +19.1% certified-volume signal for `versionb` over `plate1_only` is a
re-score and needs its own prospective registration), does not revisit regret, and does not
license any claim that SPADE beats a comparator. `NO_SELECTION` is preserved; the lockbox stays
sealed.

## 7. Result

*(Empty at freeze. Filled once, immediately after, from the run.)*
