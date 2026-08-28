# LB — SPADE vs qLogNEI at EVERY matched round count. Pre-registration.

**Frozen before any LB result exists.**

## 1. The question no experiment has answered

| comparison | result | where |
|---|---|---|
| SPADE 2 rounds vs qLogNEI **10** rounds | BO wins certification | KX §9 (withdrawn as a design claim) |
| SPADE 2 rounds vs qLogNEI **2** rounds | **SPADE wins regret** (-0.0310, p=0.023); neither certifies | LA §7.3 |
| SPADE **R** rounds vs qLogNEI **R** rounds, R > 2 | **never run** | -- |

LA proved adaptivity is the lever: `qlognei` goes from 21.2% certification at ten rounds to
**0.0%** at two. But SPADE has only ever been run at two. **`boec.multiround` removes that
restriction**, so both methods can be compared at every round count on the same 48 wells.

## 2. Matched schedules, identical for both arms

At 48 wells, `n_init = 48 - 8(R-1)`, then `R-1` batches of 8:

| rounds | opening | batches |
|---|---|---|
| 2 | 40 | 8 |
| 3 | 32 | 8, 8 |
| 4 | 24 | 8, 8, 8 |
| 5 | 16 | 8, 8, 8, 8 |

Every opening stays at or above `2d + 2 = 14`, the minimum this project's GP needs at
d = 6. **Both arms get the identical schedule** -- the only difference is how each batch is
chosen: qLogNEI's acquisition, or SPADE's certificate-contour straddle
(`boec.certstraddle`, which LA §7.3 showed creates SPADE's regret win).

## 3. LB-1 (PRIMARY, registered now)

**There exists a round count R >= 3 at which SPADE's held-out expected certified volume
exceeds qLogNEI's at the same R**, paired by `(family, seed, p)`, bootstrap 95% CI
excluding zero.

- **FAIL** -> SPADE's acquisition never beats BO's on certification at any matched
  adaptivity, and LA §7.3's regret win is the only advantage SPADE has. **This is a real
  possible outcome. I consider it more likely than not**, because the certificate-contour
  acquisition is designed to place wells where the certificate can use them, and if that
  mechanism worked it should already have shown at R = 2 -- where instead nothing certified.

## 4. LB-2 (where does certification switch on?)

The smallest R at which each arm first reaches LB >= 0.90 at answer rate >= 0.05. **This is
the number a lab needs**, independent of who wins: it says how many differentiation cycles
buy a guarantee. Reported for both arms regardless of LB-1.

## 5. LB-3 (regret across rounds)

Does LA §7.3's 2-round regret win survive at higher R, or does BO overtake as adaptivity
grows? Reported at every R. A win that exists only at R = 2 must be stated as such.

## 6. Scope and honesty constraints

- Certification path byte-identical across arms and round counts.
- `sigma_rel = 0.25`. **LB cannot address real assay noise**, where
  `SPADE-REALISTIC-NOISE-SPEC.md` §6 measured 0% for every arm at every c.
- Exploratory scale (4 families x 10 seeds x 4 round counts). A PASS licenses a registered
  confirmatory run, not a claim.
- **Rounds are not free.** A round is a differentiation cycle -- days to weeks, fresh cell
  lot, operator time. LB-2's answer is a COST in the currency labs actually spend, and any
  result here must be read with that price attached.

## 7. LB RESULT — LB-1 PASSES. My registered prediction was wrong.

4 families x 10 seeds x 4 round counts x 2 arms (`results/lb-*.json`).

**§3 registered that I considered FAIL "more likely than not". That was wrong, and it is
recorded here rather than quietly dropped.**

### 7.1 LB-1: SPADE's certified volume beats qLogNEI's at matched rounds

Paired over 160 cells at `c = 1.0`, positive = SPADE better:

| rounds | mean diff | 95% CI | p |
|---|---|---|---|
| 2 | +0.000300 | [-0.000016, +0.000706] | 0.092 |
| **3** | **+0.001000** | **[+0.000413, +0.001769]** | **0.0004** |
| 4 | +0.000203 | [-0.000156, +0.000597] | 0.503 |
| 5 | +0.000381 | [+0.000009, +0.000822] | 0.079 |

**LB-1 PASSES at R = 3.** R = 5's CI also excludes zero, barely. **R = 4 is a tie, so the
effect is NOT monotone in rounds** -- that is recorded as measured and is not explained.

### 7.2 LB-2: the number a lab needs

Smallest round count at which each arm reaches LB >= 0.90 at answer rate >= 0.05:

| arm | certifies from | at R = 5 |
|---|---|---|
| **SPADE** | **R = 5** | `c = 1.0`, 27.5% answered, containment 1.0000, **LB 0.9342** |
| `qlognei` | **not by R = 5** | 19.4% answered, no `c` reaches LB 0.90 |

`SPADE-ROUND-MATCHED-SPEC.md` §7.1 measured `qlognei` first certifying at **R = 10**.
**SPADE certifies at 5 rounds; qLogNEI needs 10.** In a cell-manufacturing protocol that
is **half the differentiation cycles** -- weeks of wall-clock and a halved cell-lot count,
which is the currency that actually binds.

Answer rate climbs with rounds for both, SPADE ahead at every count:

| rounds | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| SPADE | 6.9% | 15.0% | 17.5% | **27.5%** |
| `qlognei` | 3.8% | 8.8% | 15.6% | 19.4% |

### 7.3 LB-3: regret favours SPADE at every round count, none individually significant

| rounds | mean diff | 95% CI | p |
|---|---|---|---|
| 2 | -0.0326 | [-0.0718, +0.0060] | 0.170 |
| 3 | -0.0122 | [-0.0495, +0.0266] | 0.468 |
| 4 | -0.0138 | [-0.0404, +0.0125] | 0.327 |
| 5 | -0.0102 | [-0.0567, +0.0341] | 0.563 |

All four negative, none significant at n = 40. Consistent direction, underpowered. LA's
2-round regret win (p = 0.023, n = 80) had twice the sample; **this does not replicate it
and does not refute it.**

### 7.4 Stated at the right strength

n = 10 seeds per family. LB-1 rests on **one** round count with a convincing p (R = 3,
p = 0.0004) and one marginal (R = 5, p = 0.079), with R = 4 a tie. The **LB-2 result is
more robust than LB-1**: SPADE reaching LB 0.9342 at R = 5 where qLogNEI reaches nothing
is a qualitative gap, not a margin. A registered confirmatory run at larger n is owed
before LB-1 is a headline.

**And the ceiling stands:** at `sigma_rel = 0.68` nothing certifies for any arm at any
round count tested (`SPADE-REALISTIC-NOISE-SPEC.md` §6). LB is a `sigma = 0.25` result.
