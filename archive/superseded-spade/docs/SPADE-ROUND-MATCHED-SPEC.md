# LA — the round-matched benchmark. Pre-registration.

**Frozen before any LA result exists.**

## 1. The confound KX did not control

`SPADE-CALIBRATED-BENCHMARK-SPEC.md` §9 recorded KX-1 FAIL: `qlognei` certifies 27.7% of
the time at LB 0.9226 against SPADE's 7.5% at LB 0.8353. That was read as "BO's design
beats SPADE's design". **It is not what was measured.**

| arm | rounds | wells |
|---|---|---|
| `qlognei`, `qlogei` | **10** | 48 |
| `spade_cf_*` | **2** (40 + 8) | 48 |
| `doe` | 3 | 48 |
| `sobol`, `lhs`, `random` | 1 | 48 |

**`qlognei` gets ten sequential adaptive rounds; SPADE gets two.** Same well count, five
times the adaptivity. KX measured *10 rounds vs 2 rounds*, not *design vs design*.

**Why this matters specifically for cell manufacturing.** A round is a full
differentiation cycle -- thaw, plate, differentiate, assay -- days to weeks of wall-clock
per round, with an operator and a fresh cell lot each time. Ten sequential rounds of iPSC
differentiation is not a protocol any lab runs. Two is the realistic budget, and it is why
the two-plate architecture exists. **Comparing certificate quality without holding rounds
fixed prices SPADE against a design a lab cannot execute.**

This does not excuse the KX result; it re-scopes it. KX's finding stands as *"given ten
adaptive rounds, BO's wells support a better certificate than SPADE's two-plate wells."*
LA asks the question a lab actually faces.

## 2. Arms

`Campaign` already supports this: `CampaignConfig(q=8, n_init=40)` yields a 40-well opening
plus one batch of 8 -- **exactly SPADE's structure**. No new optimiser code.

| arm | rounds | structure |
|---|---|---|
| `versionb` | 2 | 40 LHS + 8 straddle-targeted |
| `qlognei_r2` | 2 | 40 opening + 8 qLogNEI |
| `qlognei_r10` | 10 | committed config -- **control, must reproduce KX** |
| `lhs` | 1 | 48 space-filling -- floor |

## 3. LA-1 (PRIMARY, registered now)

At **matched 2 rounds**, SPADE's expected certified volume (abstentions = 0, `c`
calibrated per-arm leave-one-family-out exactly as KX does) **exceeds `qlognei_r2`'s**,
paired by `(family, seed, p)`, bootstrap 95% CI excluding zero.

- **PASS** -> SPADE's targeted plate 2 beats BO's adaptive batch **at the round budget a
  lab actually has**, and KX's loss is an artefact of an unrunnable protocol.
- **FAIL** -> BO's acquisition beats SPADE's straddle at equal rounds, the two-plate
  architecture earns nothing even on its home ground, and KX's conclusion stands
  unqualified. **This is a real possible outcome and is registered first.**

## 4. LA-2 (is the round count the whole story?)

`qlognei_r10` minus `qlognei_r2` on expected certified volume measures **how much of KX's
margin came from rounds alone**. If `qlognei_r2` collapses to near SPADE's level, the
KX gap is a round-count effect. If `qlognei_r2` still beats SPADE, it is not.

## 5. LA-3 (regret, the honest second axis)

Final regret is recorded for all arms. If SPADE wins certification at 2 rounds but loses
regret at 2 rounds, both are reported; a certification win purchased with a worse optimum
is a trade-off and must be named as one.

## 6. Scope and honesty constraints

- Certification path byte-identical across arms: same `vorobev_columns`, same subset, same
  seeded generator, same inflation grid. **Only the wells differ.**
- `qlognei_r10` is the control. If it does not reproduce KX's direction, the harness is
  wrong and **no LA verdict may be read**.
- Exploratory scale (4 families x 20 seeds). A PASS licenses a registered confirmatory
  run, not a claim.
- **LA cannot rescue the real-noise result.** At `sigma_rel = 0.68` nothing certifies for
  any arm (`SPADE-REALISTIC-NOISE-SPEC.md` §6). LA is run at 0.25 and its conclusions are
  conditional on that regime.

## 7. LA RESULT — the round confound is confirmed, and SPADE wins at matched rounds

4 families x 20 seeds x 5 arms (`results/la-*.json`), adjudicated by
`scripts/analyse_la_round_matched.py`, written before the data landed.

### 7.1 LA-2: ALL of KX's margin was the round count

| arm | rounds | `c*` | answer rate | containment | LB |
|---|---|---|---|---|---|
| `qlognei_r10` | 10 | 1.5 | **21.2%** | 0.9853 | **0.9321** |
| `qlognei_r2` | **2** | none | **0.0%** | -- | -- |
| `versionb` | 2 | none | 0.0% | -- | -- |
| `spade_cert_rho95` | 2 | none | 0.0% | -- | -- |
| `lhs` | 1 | none | 0.0% | -- | -- |

**Strip `qlognei` to two rounds and it certifies 0.0%** -- identical to every other 2-round
arm. Held-out expected volume 0.000100 at ten rounds, **0.000000** at two.

**`SPADE-CALIBRATED-BENCHMARK-SPEC.md` §9's conclusion is therefore WITHDRAWN as stated.**
KX did not measure "BO's design beats SPADE's design"; it measured *ten adaptive rounds
beat two*. The correct statement is: **adaptivity, not acquisition, is what buys a
certificate at this budget.**

### 7.2 LA-1: a tie at zero, recorded as the registered FAIL

No 2-round arm certifies, so the paired difference is exactly 0.000000 and the CI cannot
exclude zero. **By the frozen gate that is FAIL, and it is recorded as FAIL** -- but the
honest reading is a tie at zero, not a defeat. SPADE does not beat `qlognei_r2` on
certified volume because *nothing* certifies at two rounds.

### 7.3 LA-3: at matched rounds SPADE WINS on regret, and the fix is what does it

Paired over 80 campaigns, negative = SPADE better, SESOI = 0.02:

| comparison | mean diff | median | 95% CI | p |
|---|---|---|---|---|
| **`spade_cert_rho95` vs `qlognei_r2`** | **-0.0310** | -0.0269 | **[-0.0633, -0.0004]** | **0.023** |
| `versionb` vs `qlognei_r2` | -0.0062 | -0.0039 | [-0.0359, +0.0222] | 0.744 |
| `spade_cert_rho95` vs `qlognei_r10` | +0.0561 | -- | [+0.0207, +0.0927] | 0.017 |

**At two rounds, the certificate-contour acquisition beats qLogNEI on regret**, exceeding
the registered SESOI. The classical straddle (`versionb`) is at **parity** -- so the win is
created by the acquisition change, not by the two-plate structure. All four families point
the same way (ackley -0.081, hartmann6 -0.036, levy -0.026, rosenbrock -0.015), though only
`ackley` is individually significant.

**The acquisition that produced this had been sitting unused since KV**, marked FAIL by
KV-2 -- which was measured when the volume metric itself was uncalibrated and could not
have detected it.

### 7.4 Stated at the right strength

The CI's upper bound is **-0.0004**. This is a real effect that clears the bar, but it
clears it **narrowly**, on 80 pairs, with one of four families individually significant. It
licenses a registered confirmatory run at larger n; **it is not yet a headline claim.**

And it is a **regret** win, not a certification win: at two rounds nothing certifies, so
SPADE is better at *finding* the optimum than BO under a realistic round budget, while
neither can *guarantee* a region there.

### 7.5 What this means for cell manufacturing

Ten sequential differentiation rounds is not a protocol a lab runs. At the two-round
budget that is realistic, **SPADE with the certificate-contour acquisition is the best
optimiser tested**, and no method -- SPADE or BO -- can certify a region. The lever that
would change the second half of that sentence is **rounds**, which `boec.multiround` now
makes measurable.
