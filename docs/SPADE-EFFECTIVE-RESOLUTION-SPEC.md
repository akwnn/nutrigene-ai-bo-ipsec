# SPADE effective-resolution follow-up — pre-registration ("KR")

**Frozen before any KR result exists.** Registers a single question: is *certified volume
measured in correlation cells* (`k_eff`) the conditioning variable that makes a calibrated
containment guarantee transfer across landscape families, where a cap in raw box volume
does not?

## 1. The defect this targets — established, not hypothesised

Computed from committed artefacts (`results/p8-certificate-families.json`, 24,000 rows,
4,096 draws; `results/tau-quantile-followup.json`, 9,600 rows), γ=0.95, non-empty
certificates only:

**(a) The model-internal containment statistic is blind to what governs failure.**

| certified volume bin | n | model-internal | truth | true prevalence |
|---|---|---|---|---|
| [0.001, 0.002] | 794 | 0.9835 | 1.000 | 0.890 |
| [0.002, 0.014] | 952 | 0.9933 | 0.998 | 0.956 |
| [0.014, 0.082] | 881 | 1.0000 | 0.991 | 0.985 |
| [0.082, 0.326] | 883 | 1.0000 | 0.931 | 0.992 |
| [0.326, 1.000] | 878 | 0.9982 | **0.552** | 0.996 |

**(b) The obvious confound is reversed, not merely absent.** Within the highest
true-prevalence stratum (≥0.95 — the *easiest* case, where the acceptable region is nearly
the whole box), truth containment still falls 0.995 (small regions) → 0.750 (large regions).

**(c) The upstream cause is committed and long-standing.** `results/e3.log` measures the
GP's **latent** coverage at nominal 0.95 as 0.8189 (d=6, σ=0.25), 0.7644 (d=8, σ=0.25) —
miscalibrated in every cell, and *worse where the optimizer chose to look* (selection-effect
gap −0.052 to −0.090). The certificate is a latent-`f` claim computed from those draws.
`conservative_estimate_split`'s cross-fit removes the winner's-curse **selection** bias
(F3); it cannot detect that the draws themselves are too narrow.

**(d) Volume-conditional calibration repairs the guarantee — but does not transfer.**
Leave-one-family-out (calibrate on two families, apply unchanged to the third):

| held-out | V* | uncalibrated | calibrated | 95% LB | answer rate |
|---|---|---|---|---|---|
| hill | 0.1719 | 0.9939 | 0.9988 | 0.9962 | 0.84 |
| levy | 0.2760 | 0.8958 | 0.9730 | 0.9654 | 0.85 |
| rosenbrock | 0.1611 | 0.8930 | 0.9968 | 0.9933 | 0.63 |
| ackley+hartmann6 *(split-half seeds)* | 0.00250 | 0.8284 | 0.9452 | 0.9238 | 0.54 |

Each family passes ≥0.90 when calibrated **on itself**. Transferring hill/levy/rosenbrock's
cap (V*=0.2485) to ackley/hartmann6 **fails**: containment 0.8340, 95% LB 0.8175, and the
cap never binds (answer rate 1.00) because those regions are already far smaller. The caps
span **80×** (0.20 vs 0.0025). *The law is universal; the units are wrong.*

## 2. The registered hypothesis

A simultaneous claim fails once per **effectively independent location** a region spans, not
once per unit of box volume. Under an ARD kernel the correlation cell has volume
`prod_i min(l_i, 1)`, so

    k_eff = V / prod_i min(l_i, 1)

`src/boec/resolution.py::effective_resolution`, TDD, 10 tests, all passing
(`tests/test_resolution.py`), written and committed **before** any KR number exists.
Lengthscales come from the campaign's own fitted GP: **no ground truth is touched**, so
`k_eff` is available at run time, unlike `sup_err` and `grid_r2`.

One committed measurement already points this way and is counter-intuitive enough to state:
on ackley/hartmann6, certified volume separates contained from failed campaigns at **1.22
SD**, while the two ground-truth accuracy statistics separate them at **0.25** (`sup_err`)
and **0.26** (`grid_r2`). Volume predicts certificate failure better than model accuracy
does — the signature of a resolution-limited, not accuracy-limited, failure.

## 3. Falsifiable predictions, registered now

**KR-1 (PRIMARY — transfer).** A `k_eff` cap calibrated on hill/levy/rosenbrock and applied
**unchanged** to ackley/hartmann6 achieves held-out truth containment with a one-sided 95%
Clopper–Pearson lower bound **≥ 0.90**.
*Comparator, already measured: the raw box-volume cap gives 0.8340, LB 0.8175 — FAIL.*
- **PASS** → `k_eff` is the conditioning variable; it is adopted into the calibrated rule.
- **FAIL** → `k_eff` is not sufficient. Volume-conditional calibration stays **family-local**,
  and the paper must say so explicitly rather than implying a general guarantee.

**KR-2 (mechanism — cap dispersion).** The five per-family calibrated `k_eff` caps span
**< 4×** max/min, against the box-volume caps' measured **80×**.
- **FAIL** → `k_eff` is not the natural unit even if KR-1 passes by luck; report both.

**KR-3 (no free lunch — abstention floor).** KR-1's containment must not be bought purely by
abstaining. Registered floor: **answer rate ≥ 0.30** on ackley/hartmann6 at γ=0.95, where
answer rate is the fraction of non-empty certificates retained by the cap.
*Current box-volume calibrated answer rate there is 0.54.*
- **FAIL** → the rule certifies too rarely to be a deliverable; report as such, do not tune.

**KR-4 (Occam falsifier).** If raw box volume transfers **as well as** `k_eff` — both PASS or
both FAIL identically on KR-1 — then `k_eff` adds nothing and is **dropped**. A more complex
statistic must earn its place by a measured difference, not by being better motivated.

## 4. Scope, data, and what is NOT run

**Source campaigns.** P8's registered grid, unchanged: 5 families × 4 arms
(`versionb`, `versionb_random`, `versionb_predictive`, `plate1_only`) × 50 seeds, d=6,
σ=0.25, at γ ∈ {0.5, 0.8, 0.95}. `tau-quantile-followup.json` supplies ackley/hartmann6
under the τ-quantile grid, which `SPADE-TAU-QUANTILE-SPEC.md` §6b already established should
replace the fixed-fraction grid in any cross-family certificate work.

**No new campaigns are simulated, and no certificate is recomputed.** The `ce_*` columns are
already committed. This pass regenerates each campaign's **wells only**, via
`run_p6_families.versionb_builder(arm)` (and `regenerate`'s spread-arm path for
`plate1_only`), fits the GP with P8's exact `build_gp` settings, and reads the ARD
lengthscales. The expensive step in P8 — the 4,096-draw joint posterior and its Cholesky —
is **not** repeated.

**Regeneration gate.** Every regenerated campaign's `regret` and `n_wells` must reproduce the
committed P8 row at `|delta| = 0` before any lengthscale from it is used, matching the gate
`SPADE-CALIBRATION-FIX-SPEC.md` §3b and `SPADE-TAU-QUANTILE-SPEC.md` §3 already apply. **If a
campaign fails the gate it is reported, not patched, and KR is paused** — a builder that no
longer reproduces its committed column is a separate finding.

**Firewalled timing pilot.** Per this project's standard protocol
(`SPADE-KF3-FOLLOWUP-SPEC.md` §3): 5 campaigns, wall-clock only, no outcome inspected, before
committing to the full run. If measured cost exceeds 2× the estimate, pause and report.

## 5. Statistics

One-sided 95% Clopper–Pearson bounds on binary map-level containment, as in §1. Calibration
uses 20 quantile strata of the conditioning variable; the cap is the largest stratum edge at
which the upper bound on stratum-local failure stays ≤ 0.10, scanning upward and stopping at
the first stratum that fails. Held-out evaluation never reuses a calibration campaign:
across-family for KR-1/KR-2, split-half by seed (0–24 calibrate, 25–49 test) within a family.

## 6. What KR does not decide

KR is scoped to the certificate's conditioning variable alone. It does **not** test the
Plate-2 allocation question (KF-3/3b/3c killed boundary targeting on *map error*; the
+19.1% certified-volume signal for `versionb` over `plate1_only` measured this session is a
**re-score**, and §4.2's rule stands — it needs its own prospective registration before it
counts), does not revisit regret, and does not license any claim that SPADE beats a
comparator. `NO_SELECTION` is preserved and the lockbox stays sealed.

## 7. Result

*(Empty at freeze. Filled once, immediately after, from the run.)*
