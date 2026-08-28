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
