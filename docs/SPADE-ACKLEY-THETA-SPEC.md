# ACK — SPADE's design threshold was unattainable on ackley. Pre-registration.

**Frozen before any ACK data exists.**

Runner: `scripts/run_ack_theta.py` · Analyser: `scripts/analyse_ack_theta.py` ·
Data: `results/ack-*.json`

## 1. The defect, measured

ackley is SPADE's **only** regret loss, and it strengthened with n:

| n | SPADE R=5 vs qLogNEI R=10 on ackley | p |
|---|---|---|
| 25 seeds | +0.0564, CI [+0.0050, +0.1094] | 0.029 |
| **32 seeds** | **+0.0652, CI [+0.0203, +0.1104]** | **0.004** |

Root cause, traced not guessed. `multiround_design` set
`theta = tau_frac * mu_max` **once**, and every runner passed
`mu_max = float(getattr(orc, "mu_max", 1.0))`. **No evaluator defines `mu_max`** —
`hasattr` is False for all five families — so the fallback made `theta = 0.80` everywhere:

| family | true max | theta = 0.80 | attainable? |
|---|---|---|---|
| hartmann6 | 0.9211 | 0.80 | yes |
| hill | 0.9867 | 0.80 | yes |
| levy | 0.9911 | 0.80 | yes |
| rosenbrock | 0.9986 | 0.80 | yes |
| **ackley** | **0.4102** | 0.80 | **NO — above the global maximum** |

**On ackley, SPADE straddles a contour containing no points.** The signature confirms it:
on ackley SPADE's median sampled value is *higher* than qLogNEI's (0.0942 vs 0.0579) while
its best is *worse* (0.3128 vs 0.3738) — it spreads over a mid band instead of climbing.
On hartmann6, where theta is attainable, SPADE's best beats qLogNEI's (0.8799 vs 0.7877).

**Four of five families never exposed the bug because they top out near 1.0.**

## 2. The change

`boec.multiround.resolve_theta`. `mu_max=None` sets `theta = tau_frac * max(Y_observed)`,
recomputed each round. Observations only — it is the EI incumbent, not oracle knowledge.
An explicit `mu_max` is **bit-identical to the committed behaviour**; verified, LC's SPADE
regret reproduces to 1e-12 on six cells, and 21 existing tests pass.

## 3. Design

5 families x 32 seeds x arms {`spade` (fixed theta), `spade_adaptive`, `qlognei`} at R=5,
plus `qlognei` R=10. 48 wells, `sigma_rel = 0.25`, `alpha = 0.95`, same c and p grids.
Paired by `(family, seed)`.

## 4. ACK-1 (PRIMARY) — does it fix ackley?

On **ackley**, `spade_adaptive` regret is lower than `spade` regret, paired, bootstrap 95%
CI excluding zero.

- **PASS** -> the loss was the unattainable threshold, and it is repaired.
- **FAIL** -> the threshold was not the cause. §1's root cause is then **retracted**, and
  the ackley loss is reported as an unexplained property of the straddle. **Real possible
  outcome:** ackley is a needle-in-haystack landscape and a certificate-contour
  acquisition may simply be the wrong tool there regardless of where the contour sits.

## 5. ACK-2 (GUARDRAIL) — does it break the other four?

On hartmann6, hill, levy and rosenbrock, `spade_adaptive` is **non-inferior** to `spade`:
paired CI upper bound within the registered SESOI of **0.02**.

- **FAIL** -> the fix trades ackley for the rest and **must not be adopted**. Registered
  now precisely so that "fixed ackley" cannot be claimed while quietly losing elsewhere.

## 6. ACK-3 (GUARDRAIL) — is certification preserved?

SPADE exists to certify, not to optimise. `spade_adaptive`'s certified volume must be
non-inferior to `spade`'s, and its empirical containment must not fall.

- **FAIL** -> the fix buys regret with certificate quality, which is the wrong trade for
  this method, and it must not be adopted.

## 7. Honesty constraints

- A lower `theta` makes the contour easier to reach. Any certification *gain* must be
  reported with that attached, not presented as free.
- `sigma_rel = 0.25`. The real-noise ceiling (0.68, nothing certifies) is untouched.
- No "X cannot certify" claim without reporting `answered` and `contained`
  (`SPADE-TAU-DEGENERACY-SPEC.md` §7.3's standing rule).
