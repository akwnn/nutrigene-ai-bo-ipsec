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

---

## 8. TT RESULT — configured arm not adopted; targeting was only intermittently active

5 families x 32 seeds x 3 arms, `results/tt-*.json`, adjudicated by
`scripts/analyse_tt_theta_tau.py`, written before the data landed. Reproduction gate
passed: `spade` reproduced LC's regret to 1e-12.

### 8.1 TT-1 (PRIMARY) is inconclusive on a consistent volume benefit

`spade_tau` minus `spade` on certified volume at p=0.30, paired, n=160:
**+0.000425, CI [−0.000022, +0.000875], p = 0.0645.** The interval contains zero.

Per-family estimates are descriptive heterogeneity. After correcting the five family tests
with Holm's procedure, neither of the two smallest raw p-values remains below 0.05:

| family | theta/tau mismatch | diff | 95% CI | raw p | Holm p |
|---|---|---|---|---|---|
| hartmann6 | 10.3x | **+0.002766** | [+0.000687, +0.004687] | 0.012 | 0.061 |
| ackley | 13.6x | **−0.000641** | [−0.001187, −0.000141] | 0.015 | 0.061 |
| hill | 1.1x | +0.000000 | [−0.000063, +0.000063] | 1.000 | 1.000 |
| levy | 1.0x | −0.000016 | [−0.000047, +0.000000] | 0.722 | 1.000 |
| rosenbrock | 0.9x | +0.000016 | [+0.000000, +0.000047] | 0.722 | 1.000 |

Correct targeting **helps hartmann6 and hurts ackley by similar magnitudes**, and does
nothing on the three families where theta and tau already nearly coincided. There is no
consistent benefit.

The aggregate interval includes zero, so TT does not establish a consistent positive volume
effect. It also does not vindicate KF-3 or establish failure of a fully active mechanism.
The activation audit records the target inside the adjusted-margin range in only **206/640**
adaptive rounds; only **20/160** campaigns were active in all four adaptive rounds. TT is a
mixed-activation test of this configured arm.

### 8.2 TT-2 (GUARDRAIL) FAILS — the configured arm is not adoptable

Regret, `spade_tau` minus `spade`, n=160: **+0.0301, CI [+0.0169, +0.0450], p < 0.0001**.
The upper endpoint exceeds the registered noninferiority margin of 0.02, so the guard fails
and `spade_tau` is not adoptable. The lower endpoint remains below 0.02; the data therefore
do not establish that the practical harm itself is wholly beyond the margin.

**Even had TT-1 passed, this gate alone would forbid adopting the change.**

### 8.3 TT-3 — it does not fix ackley either

| arm | ackley mean regret |
|---|---|
| qlognei | 0.7140 |
| **spade** | **0.7375** |
| spade_tau | 0.7520 |

ackley has the largest theta/tau mismatch (13.6x), so it was the best candidate for the
mismatch being the cause. The configured `spade_tau` arm was **slightly worse**. Because the
target was not active in every adaptive round, this does not rule out every fully activated
targeting design.

### 8.4 The finding that matters more than either gate

Certification at p=0.30, c=1.0 — reported with `answered` and `contained` per the standing
rule:

| arm | answered | contained | containment | LB |
|---|---|---|---|---|
| **spade** (committed) | **66/160** | **66** | **1.0000** | **0.9556** |
| spade_tau | 63/160 | 61 | 0.9683 | 0.9034 |
| qlognei | 52/160 | 47 | 0.9038 | 0.8084 |

**The committed SPADE is the best arm on every column** — it answers most, contains
perfectly, and has the highest lower bound. And it does so while its targeting mechanism is
provably inert.

**Bounded conclusion:** keep the committed SPADE and do not adopt this `spade_tau`
configuration. The aggregate certified-volume benefit is inconclusive, regret
noninferiority fails, and the acquisition was target-active in only 206 of 640 adaptive
rounds. The experiment does not support a broader claim that every fully activated
certificate-targeting mechanism fails.
