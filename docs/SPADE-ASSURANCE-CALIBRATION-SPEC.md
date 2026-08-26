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

## 7. Result

*(Empty at freeze. Filled once, immediately after, from the run.)*
