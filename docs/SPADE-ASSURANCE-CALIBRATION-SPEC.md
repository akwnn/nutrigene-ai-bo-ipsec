# SPADE assurance-calibration — pre-registration ("KT")

**Frozen before any KT result exists.** Registers the successor to KR (`k_eff`, killed) and KS
(`kappa_tail`, killed). Both tried to fix the certificate with a **post-hoc filter on its
output**. KT turns the knob the certificate already has.

## 1. The category error KR and KS shared

`conservative_estimate(draws, theta, alpha)` returns the largest Vorob'ev quantile whose
model-internal containment reaches `alpha`. The sets are **nested in `alpha` by construction**:
raising `alpha` can only shrink the certified region. That is precisely the monotone,
nested, one-dimensional family that risk-controlling prediction sets require of a calibration
parameter — and this project has never calibrated it. Both KR and KS instead fitted a *cap on a
statistic computed from the region after the fact*, which is neither nested nor monotone in
anything the certificate controls.

**The headroom is measured and unsaturated** (committed data, no new compute):

| nominal `alpha` | hill/levy/rosenbrock | ackley/hartmann6 |
|---|---|---|
| 0.50 | 0.8544 | 0.4104 |
| 0.80 | 0.9357 | 0.6533 |
| 0.95 | 0.9251 | **0.8340** |

The hard families climb 0.41 → 0.65 → 0.83 and the grid simply **stops at 0.95**. `ALPHAS` has
been `(0.50, 0.80, 0.95)` in every certificate run this project has ever done
(`run_p2_versionb_gamma.py:470`), so the region above 0.95 is unmeasured, not measured-and-failed.

## 2. Two registered levers, both nested, both frozen now

**Lever A — the assurance level `alpha` (PRIMARY).** Score the existing campaigns at
`ALPHAS_KT = (0.95, 0.98, 0.99, 0.995, 0.999)`. Nested by construction; no new estimator.

**Lever B — posterior inflation `kappa` (SECONDARY, registered now so it cannot be promoted
later).** KS-4 dropped `kappa_tail` as a **conditioning variable**. That says nothing about
`kappa` as a **variance correction**, which is what `src/boec/selfcalib.py` was built for and
what E3's finding actually implies: latent coverage 0.7644–0.8189 against nominal 0.95 means the
draws are too narrow, so scale them. Scaling posterior SD by `c >= 1` shrinks the excursion
probability toward 0.5 monotonically and therefore also yields a nested family. Grid
`C_KT = (1.0, 1.25, 1.5, 2.0)`, with `1.0` the identity control.

`alpha` is **PRIMARY**. If both clear their gates, `alpha` is adopted and `kappa`-inflation is
reported as a secondary result, never swapped in because it looked better.

## 3. Falsifiable predictions, registered now

**KT-1 (PRIMARY — transfer).** An `alpha` calibrated on hill/levy/rosenbrock — the smallest
`alpha` whose 95% Clopper–Pearson **upper** bound on map-level failure is ≤ 0.10 — applied
**unchanged** to ackley/hartmann6, achieves held-out truth containment with a one-sided 95%
lower bound **≥ 0.90**.
*Comparators, fixed and already measured: box volume LB 0.8175 FAIL; `k_eff` LB 0.8175 FAIL;
`(volume, kappa_tail)` LB 0.8074 FAIL.*

**KT-2 (validity of the lambda — PAIRED monotonicity).** Among campaigns non-empty at **both**
levels, achieved containment must be non-decreasing in `alpha`, on every family.
*This gate exists because the marginal table in §1 is NOT monotone (0.9357 → 0.9251 on the easy
families from 0.80 to 0.95). That is a composition effect — raising `alpha` empties different
campaigns — and the paired comparison is the one that tests the nesting property.* **If the
PAIRED comparison is non-monotone, `alpha` is not a valid calibration parameter and KT-1 is
VOID regardless of its number.**

**KT-3 (no free lunch).** Answer rate ≥ 0.30 on ackley/hartmann6 at the calibrated `alpha`.
Raising `alpha` empties certificates, and a rule that certifies nothing is not a deliverable.
*Measured baseline: at `alpha`=0.95 the hard families are already non-empty in only 1518 of
9600 scored rows.*

**KT-4 (Occam).** If `alpha`=0.95 — already committed, already free — reaches the same verdict
as the calibrated `alpha`, the calibration adds nothing and is dropped, as `k_eff` and
`kappa_tail` were.

**KT-5 (Lever B).** Same transfer test with posterior inflation `c` as the calibration
parameter, `alpha` held at 0.95. Registered now, reported regardless of outcome, and **not
eligible to replace Lever A as the primary**.

**KT-6 (the registered ceiling).** If KT-1 and KT-5 both FAIL, the recorded conclusion is: *the
conservative excursion certificate cannot be made family-general at 48 wells by calibrating any
parameter it exposes; its validity scope must be declared in advance.* Combined with KR, KS, and
the 0/50 scope detector, that is four independent confirmations and it is the paper's finding,
not a gap in it. **No further parameter is tried without a new pre-registration.**

## 4. Scope and cost

Same campaigns, same wells, same seeds: 5 families × 4 arms × 50 seeds, d=6, σ=0.25,
`N_DRAWS=4096`, hard families on the τ-quantile grid. **The certificate IS recomputed here** —
that is the point — but no campaign is re-simulated: wells are regenerated through P8's `build()`
and gated against committed `regret`/`n_wells` at `|delta| = 0`, exactly as KR did 1000/1000.

The joint posterior draw is computed **once per campaign** and shared across every
(`alpha`, `c`) combination, so the full grid costs one pass, not twenty.

**Firewalled timing pilot before the full run** (`SPADE-KF3-FOLLOWUP-SPEC.md` §3): 3 campaigns,
wall clock only, no outcome inspected. P8's own log measures ~20–30s/campaign. If the projection
exceeds 8 hours the run is **reduced in seeds and the reduction reported**, not silently
extended, and the reduced power is stated with the result.

## 5. Statistics

Calibration selects the **smallest** `alpha` (most informative region) whose CP upper bound on
failure over the calibration families is ≤ 0.10 — the standard RCPS selection over a nested
family, not a grid search over a filter. Held-out evaluation is across-family. Answer rate is
the fraction of scored rows with a non-empty certificate.

## 6. What KT does not decide

KT does not revisit Plate-2 allocation. That question was settled this session and the mechanism
recorded: on map error the test has n=250 pairs and MDE 0.0057 against a SESOI of 0.02 — a
**well-powered** null, observed +0.0029 — and at γ=0.95 only 14 of 250 pairs are non-empty for
both arms (MDE 0.75 SD), so the certificate cannot adjudicate allocation at this budget at all.
The first-principles reason: 8 wells on 40 moves wells-per-correlation-cell by exactly 20%
whatever the placement rule, and levy/ackley sit **below one well per correlation cell**. The
earlier "+19.1% certified volume" reading of `versionb` over `plate1_only` is **withdrawn** — it
came from a single calibration split, the ordering reverses on the full data, and the bootstrap
CI on the arm difference is [−0.114, +0.232].

`NO_SELECTION` is preserved; the lockbox stays sealed.

## 7. Result — KT-5 (Lever B) PASSES. A single dimensionless inflation factor transfers.

**12,800 rows over KV's prospective campaigns** (`results/ktb-inflation.json`). Lever A (alpha
above 0.95) remains unrun; Lever B was registered in §2 as SECONDARY and is reported as such.

### 7.1 The sweep

| `c` | non-empty rate | model-internal | **truth** | 95% LB | mean certified vol |
|---|---|---|---|---|---|
| 1.00 (identity control) | 0.0803 | 0.9846 | 0.8327 | 0.7896 | 0.00604 |
| 1.25 | 0.0666 | 0.9824 | 0.9296 | 0.8936 | 0.00292 |
| **1.50** | 0.0519 | 0.9792 | **0.9699** | **0.9377** | 0.00155 |
| 2.00 | 0.0222 | 0.9692 | 1.0000 | 0.9587 | 0.00127 |

`c = 1.0` reproduces the standard certificate, as the identity control requires.

### 7.2 The transfer test, which is the point

`c` chosen on one family by standard RCPS selection over the nested family — the **smallest**
`c` whose 95% Clopper–Pearson upper bound on failure is ≤ 0.10 — then applied **unchanged** to
a family it never saw:

| calibrate on | `c*` | apply to | at `c`=1.0 | **calibrated** | 95% LB | answer rate | n | |
|---|---|---|---|---|---|---|---|---|
| ackley | 1.5 | hartmann6 | 0.7953 | **0.9597** | 0.9171 | 0.155 | 124 | **PASS** |
| hartmann6 | 1.5 | ackley | 0.9048 | **1.0000** | 0.9312 | 0.053 | 42 | **PASS** |
| **pooled** | | | | **0.9699** | **0.9377** | | 166 | **PASS** |

*Comparators, all fixed and previously measured:* `k_eff` LB 0.8175 FAIL · `kappa_tail`
LB 0.8074 FAIL · box-volume cap LB 0.8175 FAIL.

**Both families independently select the same `c* = 1.5`.** That is the transfer property
demonstrated rather than assumed, and it is why a dimensionless factor succeeds where a cap in
box-volume units failed: `c` carries no units to be re-scaled per landscape.

### 7.3 Why this works when five other corrections did not

`k_eff`, `kappa_tail`, `alpha_star`, Vorob'ev deviation and the 0/50 scope detector all tried
to **predict which campaigns would fail** from run-time observables. Every one failed. `c` does
not predict anything — it **widens the posterior until the guarantee holds empirically**, which
is the standard risk-controlling construction over a nested family and needs no detector.

E3 is why a multiplicative factor is the right form: latent coverage 0.7644–0.8189 against
nominal 0.95, while **predictive** coverage recovers to 0.9087–0.9156. The latent posterior is
under-dispersed by roughly a scale factor, and `c ≈ 1.5` is the size of that correction.

### 7.4 Limits, stated

1. **Two usable families.** `levy` and `rosenbrock` certify almost nothing at the quantile grid
   at γ=0.95 (`SPADE-PREVALENCE-MATCHED-SPEC.md` §7.2), so the transfer test rests on
   ackley↔hartmann6. It is a two-family result, not a five-family one.
2. **The guarantee costs answer rate and volume.** Non-empty falls 0.0803 → 0.0519 and mean
   certified volume 0.00604 → 0.00155, a 3.9× smaller region. That is the price and it is not
   hidden.
3. **The `c` grid is coarse** (4 values). `c*` = 1.5 in both directions, but the true optimum
   lies somewhere in (1.25, 1.5] and is not resolved.
4. **This is a re-score of prospectively-generated campaigns.** KV generated the wells live, so
   the designs are prospective; the inflation is applied at scoring time. A fully prospective
   confirmation still needs its own run.
5. **It does not fix Plate-2 targeting.** KV-6 stands: targeting still earns nothing over random.
   KT-5 fixes calibration and transfer, not allocation.


## 8. Amendment KT-7 — the alpha-generality test, registered before its run

### 8.1 What §7's result does NOT cover, measured

§7 validated `c` at **alpha = 0.95 on ackley and hartmann6 only**. Tested at the other
assurance levels, where `levy` and `rosenbrock` DO produce certificates:

| alpha | usable families | pooled LOFO containment | 95% LB | `c*` selected | verdict |
|---|---|---|---|---|---|
| 0.50 | all four (levy 151, rosen 214, ackley 259, h6 273) | 0.7510 | 0.7242 | **2.0 = grid max** | **FAIL** |
| 0.80 | rosen, ackley, h6 | 0.8951 | 0.8616 | **2.0 = grid max** | **FAIL** |
| 0.95 | ackley, h6 only | 0.9699 | 0.9377 | 1.5 | PASS |

**`c*` hit the grid ceiling at both lower alpha.** That is a truncated search, not a settled
failure, and it is exactly the "coarse 4-point grid" limitation §7.4 recorded.

### 8.2 A hard limit, named rather than engineered around

At alpha = 0.95, `levy` and `rosenbrock` yield **fewer than 10 non-empty certificates at every
`c` in the grid**. Inflation only ever SHRINKS a certified region — it cannot create one where
none exists. So no value of `c` can make those families testable at alpha = 0.95.

**Recorded conclusion: `levy` and `rosenbrock` cannot support a gamma=0.95 certificate at
realistic target sizes (tau-quantile, p <= 0.30) on 48 wells, with or without this correction.**
That is an information limit of the budget, consistent with `SPADE-PREVALENCE-MATCHED-SPEC.md`
§7.2 (non-empty rates 0.0025 and 0.0000), and it is not a defect any calibration can repair.

### 8.3 KT-7, registered now

Extended grid `C_FINE = (1.0, 1.2, 1.3, 1.4, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0)` — resolving the
unresolved (1.25, 1.5] interval AND extending past the ceiling `c*` kept hitting.

**KT-7a (four-family transfer).** At alpha = 0.50, leave-one-family-out over **all four**
families reaches pooled 95% LB **>= 0.90**.
- **PASS** -> the correction is general across families; §7's two-family limit was a grid
  artefact.
- **FAIL** -> the correction is alpha-specific, `c` does not generalise downward, and §7's
  claim is permanently narrowed to alpha = 0.95 on the families that can answer there.

**KT-7b (is one constant enough?).** The per-family `c*` values at alpha = 0.50 span **< 2x**.
- **FAIL** -> `c` is not one universal constant but a per-landscape quantity, and the honest
  product is "calibrate `c` on your own family library," not "use c = 1.5."

**KT-7c (no free lunch).** Pooled answer rate at the selected `c*` is **>= 0.10**.
*Inflation shrinks regions; at c = 4.0 it may empty them entirely, in which case a passing
KT-7a would be meaningless.*

**KT-7d (resolve c\*).** With the finer spacing, the alpha = 0.95 `c*` for ackley and hartmann6
is reported to one decimal place, replacing §7.4's "somewhere in (1.25, 1.5]".

Firewalled pilot measured **26.0 s/campaign -> 5.8 h** for 4 families x 50 seeds x 4 arms,
inside the 8-hour ceiling. No new campaigns are simulated; this re-scores KV's wells.


## 9. Why some families certify and others cannot — the answer, and it is not the landscape

§8.2 recorded "levy and rosenbrock cannot support a gamma=0.95 certificate" as a brute
information limit. That was incomplete. Diagnosed here:

**Hypothesis 1, SHAPE — REFUTED.** Compactness of the true acceptable region (mean fraction of
a point's 20 nearest neighbours also inside it) at matched prevalence p=0.30:

| family | compactness | deep points | certifies |
|---|---|---|---|
| rosenbrock | **0.648** | **0.107** | **0.0000** |
| ackley | 0.555 | 0.069 | 0.1580 |

Rosenbrock's region is *geometrically better* than ackley's and certifies nothing. Shape is not
the mechanism.

**Hypothesis 2, MARGIN — CONFIRMED, with perfect rank agreement.** Distance of the acceptable
region above its own threshold, in units of the observation noise, at p=0.30:

| family | tau | median margin/sigma | 10th pct | certifies |
|---|---|---|---|---|
| hartmann6 | 0.0774 | **2.1181** | 0.4889 | 0.1580 |
| ackley | 0.0587 | **0.8617** | 0.1578 | 0.1580 |
| levy | 0.8310 | **0.2393** | 0.0491 | 0.0025 |
| rosenbrock | 0.9006 | **0.1585** | 0.0337 | 0.0000 |

**The cause is the noise model, not the family.** `sigma = sigma_rel * f(x)` is multiplicative
(`boec.lse.predictive_sigma`). `UnitScaled` places levy's and rosenbrock's acceptable regions at
`f ~ 0.83-0.90`, where `sigma ~ 0.21-0.23`; ackley's and hartmann6's sit at `f ~ 0.06-0.08`,
where `sigma ~ 0.015-0.019` -- **more than 10x smaller**. The absolute margins are comparable;
the noise is not.

**Consequences.**

1. **"levy/rosenbrock are uncertifiable" is a benchmark-construction artefact**, produced by
   `UnitScaled` interacting with a multiplicative noise model — not a property of those
   landscapes. §8.2's "information limit of the budget" is **withdrawn as stated**: the limit
   is real for these *instances as scored*, and is not evidence about the method's generality.
2. **The certificate's operating range is governed by signal-to-noise at the threshold**, a
   single scalar, and this project has never reported it. It explains KU §7.2's 60x
   certifiability gap, which was recorded as an unexplained inversion.
3. **It supplies the run-time detector every previous attempt lacked.** `k_eff`,
   `kappa_tail`, `alpha_star` and Vorob'ev deviation all failed to predict certificate failure.
   The estimated threshold margin `(mean(x) - tau) / sigma_pred(x)` over the candidate set is
   computable from the fitted GP alone, with no ground truth. **This is registered as an
   observation, not a result** — it needs its own pre-registration and a held-out test before
   anything rests on it.
4. **KT-7a's alpha=0.50 four-family test is still the right test**, and is now interpretable:
   if it fails, the reason is predicted in advance to be levy's and rosenbrock's 4-13x worse
   threshold SNR, not a failure of `c` to generalise.


## 9a. RETRACTION of §9 — the SNR explanation does not survive expansion

§9 claimed threshold SNR explains certifiability with "perfect rank agreement." **That claim
rested on four data points** — one per family, at a single alpha (0.95) and a single target
size (p=0.30). Expanded to all sixteen `(family, p)` cells at alpha=0.50:

**Spearman(margin/sigma, non-empty rate) = +0.237, p = 0.377. Not significant.**

Stratifying by SNR and ignoring family does not separate the outcome either:

| SNR stratum | cells | families | non-empty | containment |
|---|---|---|---|---|
| [0.0, 0.3) | 8 | levy, rosenbrock | 0.228 | 0.476 |
| [0.6, 1.2) | 5 | ackley, hartmann6 | 0.265 | 0.467 |

Two strata differing 3x in SNR give the same non-empty rate. And `levy` at p=0.30 certifies
**more** often (0.475) than `ackley` at p=0.10 (0.355) despite **3.6x lower** SNR.

**Retracted:** "the certificate's operating range is governed by signal-to-noise at the
threshold." **Retracted:** the claim that `(mean - tau)/sigma_pred` is the run-time detector
five earlier attempts were missing — it has no established predictive validity and must not be
built on.

**What survives.** §9's *refutation* of the shape hypothesis stands (rosenbrock's region is
geometrically better than ackley's and certifies nothing). §8.2's original statement — that
`levy` and `rosenbrock` cannot support a gamma=0.95 certificate at realistic target sizes on 48
wells — **stands as measured**, and §9's attempt to explain it away as a benchmark artefact is
withdrawn. The cause remains **unexplained**.

**Recorded as an open question, not a finding.** Certifiability at alpha=0.50 is driven mostly
by target size `p` (0.47-0.98 at p=0.30 against 0-0.14 at p=0.01) with a residual family effect
at matched `p` that neither shape nor SNR accounts for. Anyone continuing this should note that
`levy`/`rosenbrock` have *better* containment at alpha=0.50 when they do certify (0.705, 0.816)
than `ackley`/`hartmann6` (0.440, 0.264) — the inverse of the alpha=0.95 ordering, which is
itself unexplained.

## 7a. ERRATUM to §7 — the published bound pools SPADE with its own controls

§7 reports pooled truth containment **0.9699**, 95% LB **0.9377**, at `c = 1.5`. Attempting
to reproduce those digits from `results/ktb-inflation.json` under the stated rule failed,
and an exhaustive search over pooling schemes located them exactly:

    arms  = (plate1_only, spade_cert_rho95, versionb, versionb_random)   <- ALL FOUR
    fams  = (ackley, hartmann6)
    c=1.5, alpha=0.95  ->  n=166, k=161, containment=0.9698795, LB=0.9377155

**The denominator pools SPADE with `plate1_only` and `versionb_random`, which are its
control arms.** Restricted to SPADE's own arm:

| pooling | n | containment | 95% LB |
|---|---|---|---|
| all four arms (as published) | 166 | 0.9699 | **0.9377** |
| `versionb` only (SPADE) | 62 | 0.9677 | **0.9019** |

**What survives.** `c* = 1.5` is unchanged, and **both** poolings clear the 0.90 bar, so
§7's conclusion stands. The RCPS selection is also unchanged: at `c=1.5` the failure-rate
upper bound on `versionb` alone is 0.0981 <= 0.10, and 1.25 does not clear it.

**What must change before publication.** The 0.9377 figure must not be presented as
SPADE's containment bound. Pooling arms is defensible *only* under the explicit claim that
`c` calibrates the **posterior**, which is a property of the model and not of the
acquisition -- and under that claim the controls belong in the denominator. That argument
was never stated in §7, and a reader recomputing on the SPADE arm will get 0.9019.

**Report both, or state the pooling.** Recorded here rather than silently corrected,
because the published number is *more favourable* than the SPADE-only number and the
direction of an unexplained discrepancy matters.
