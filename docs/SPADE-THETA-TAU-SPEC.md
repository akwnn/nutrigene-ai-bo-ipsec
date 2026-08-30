# TT — does SPADE's mechanism work when it is actually pointed at the certified region?

**Frozen before any TT data exists.**

Runner: `scripts/run_tt_theta_tau.py` · Analyser: `scripts/analyse_tt_theta_tau.py` ·
Data: `results/tt-{family}.json`

## 1. Why this exists

`SPADE-ACKLEY-THETA-SPEC.md` §8 established that `theta` **cancels** out of the acquisition
ranking whenever it exceeds `mean - z_rho*sd` for every candidate — true for every family at
the opening round. So SPADE is a UCB with exploration weight `1.96 - z_rho`, and **the
targeting mechanism has never been active.**

Two things follow, and this experiment tests both.

**(a) The registered KF-3 result tested a disabled mechanism.** The 99,601-row prospective
study found targeted plate-2 placement does not beat random (−0.0019, p=0.41). That is a
true statement about the code as written, and **not** a test of whether targeting works.

**(b) `theta` was pointed at the wrong quantity anyway.** The certificate is about
`{f >= tau}`. `theta` was `tau_frac * mu_max` = 0.80. Measured at p=0.30:

| family | theta used | tau | ratio |
|---|---|---|---|
| ackley | 0.80 | 0.0587 | **13.6x** |
| hartmann6 | 0.80 | 0.0774 | **10.3x** |
| hill | 0.80 | 0.7597 | 1.1x |
| levy | 0.80 | 0.8310 | 1.0x |
| rosenbrock | 0.80 | 0.9006 | 0.9x |

**`tau` is not oracle knowledge.** It is the practitioner's own specification — the real
iPSC-EC certification used "CD31+ >= 33.2%". Targeting it is legitimate and available.

## 2. Correction to an earlier claim

An earlier handoff and `SPADE-CONCLUSIONS-2026-08-29.md` §5 stated that **rho moves the
estimand** and so any rho change needed registering. **That was wrong.** `rho` is passed
only to `batch_lse_rho` (the acquisition); the certificate is computed independently from
`p2.ALPHAS`. `rho` is a design hyperparameter and changes nothing about what is measured.
Recorded here rather than quietly fixed.

## 3. Design

5 families x 32 seeds x R=5 x arms:

| arm | theta | what it tests |
|---|---|---|
| `spade` | `0.80` (committed) | the control, bit-identical to LC |
| `spade_tau` | **`tau` at p=0.30** | the mechanism pointed at the certified region |
| `qlognei` | n/a | the baseline |

`sigma_rel = 0.25`, `alpha = 0.95`, `c` in {1.0, 1.5, 2.0, 3.0}, evaluated at p = 0.30
(the threshold `spade_tau` targets) and p = 0.70.

**Reproduction gate:** `spade` must reproduce LC's regret exactly, or nothing here is
readable.

## 4. TT-1 (PRIMARY) — does correct targeting beat the disabled mechanism?

`spade_tau` versus `spade` on **certified volume at p = 0.30**, paired by `(family, seed)`,
bootstrap 95% CI excluding zero.

- **PASS** -> the mechanism works when actually pointed at the certified region, and
  **KF-3's negative result is confined to the disabled implementation.** This is the result
  that would repair §2 and §6 of the paper.
- **FAIL** -> targeting does not help even when correctly aimed. **Then KF-3's conclusion
  stands on its merits**, the two-plate and multi-round lines agree, and the paper says
  plainly that certificate-contour targeting does not earn its complexity. **This is a real
  possible outcome and is registered first.**

## 5. TT-2 (GUARDRAIL) — does it cost regret?

`spade_tau` versus `spade` on regret, paired. A targeting rule that buys certified volume by
abandoning the optimum is not an improvement. Non-inferiority within the registered SESOI of
**0.02**.

## 6. TT-3 — does it fix ackley?

ackley is SPADE's only regret loss (+0.0652, p=0.004) and has the **largest** theta/tau
mismatch (13.6x). If the mismatch is the cause, `spade_tau` should narrow it.
**Descriptive, not a gate** — one family, and the direction is known in advance.

## 7. Honesty constraints

- `spade_tau` targets p = 0.30's threshold. Certification at p = 0.70 is then being scored
  at a threshold the arm did **not** target; report it separately and never pool the two.
- No "X cannot certify" without `answered` and `contained`
  (`SPADE-TAU-DEGENERACY-SPEC.md` §7.3).
- At n <= 25 seeds an effect here is not reliable; 32 seeds minimum.
