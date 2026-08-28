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
