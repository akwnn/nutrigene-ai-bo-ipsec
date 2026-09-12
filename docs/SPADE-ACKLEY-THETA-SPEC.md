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

---

## 8. ACK-1 FAILS — and §1's root cause is RETRACTED

Per §4: *"FAIL -> the threshold was not the cause. §1's root cause is then retracted."*
It failed. `spade_adaptive` reproduced `spade` **bit-identically** — same design, same
`Xsum`, same regret to 6 dp — despite provably using different thresholds
(θ = 0.108 → 0.279 → 0.347 per round, against a fixed 0.80; instrumented and confirmed).

### 8.1 Why: θ cancels out of the acquisition

`certificate_straddle` is `1.96·sd − |mean − z_ρ·sd − θ|`. When θ exceeds `mean − z_ρ·sd`
for **every** candidate, the absolute value resolves to `θ + z_ρ·sd − mean` and the score
becomes:

```
score = 1.96·sd − θ − z_ρ·sd + mean = (1.96 − z_ρ)·sd + mean − θ
```

**θ is then a constant offset and drops out of the ranking entirely.** Measured at the
opening round, ρ = 0.95, z_ρ = 1.6449:

| family | θ | max(mean − z·sd) | candidates above θ | |
|---|---|---|---|---|
| ackley | 0.80 | 0.0437 | **0.0%** | θ cancels |
| ackley | 0.108 (adaptive) | 0.0437 | **0.0%** | θ cancels |
| hartmann6 | 0.80 | 0.0846 | **0.0%** | θ cancels |
| hartmann6 | 0.179 (adaptive) | 0.0846 | **0.0%** | θ cancels |

Rank correlation between the scores at the two θ values: **exactly 1.000000**, identical
argmax, on both families.

### 8.2 What SPADE's acquisition actually is

**SPADE is not straddling the certificate contour.** In this regime it reduces to

```
argmax  (1.96 − z_ρ)·sd + mean
```

— a UCB whose exploration weight is set by **ρ**, not θ. At ρ = 0.95 that weight is
`1.96 − 1.645 = 0.315`; at ρ = 0.50 it is `1.96`. **ρ controls exploration; θ does
nothing.** The module docstring's claim that the acquisition targets "the certificate
contour, not Bryan's straddle" describes an intent the code does not realise whenever the
contour lies outside the posterior's range — which is every family, at the opening round.

This also reinterprets `SPADE-ROUND-MATCHED-SPEC.md`'s measured gap between the
certificate contour and the true-contour straddle (median regret 0.2996 vs 0.4008): that
difference came from **ρ changing the sd weight**, not from moving the target contour.

### 8.3 Consequences

- **The ackley loss is NOT explained by the `mu_max` fallback.** §1's root cause is
  withdrawn. The `getattr(orc, "mu_max", 1.0)` fallback is still a genuine latent bug —
  no evaluator defines `mu_max` — and `resolve_theta` still fixes it, with 5 red-first
  tests and a bit-identical regression gate. **But it changes no result, and must not be
  presented as a fix.**
- **The real lever is ρ**, the exploration weight. ackley is needle-in-haystack and
  `0.315·sd` is very little exploration; that is the live hypothesis for the loss.
- **ACK-2 and ACK-3 are moot** — with an identical design there is nothing to guard.
- **Not yet tested, and not to be claimed:** whether lowering ρ fixes ackley, and what it
  costs in certification. ρ is the certificate's Vorob'ev level, so moving it changes the
  estimand, not just the search — that trade must be registered before it is run.
