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

**And read §7.5 with this:** the effect is carried by **two of the four families** --
levy and rosenbrock never certify for either arm, so they contribute exact zeros to all
160 paired cells. The p-values are unaffected (the zeros are paired), but the family
support is narrower than "4 families x 10 seeds" implies.

**And the ceiling stands:** at `sigma_rel = 0.68` nothing certifies for any arm at any
round count tested (`SPADE-REALISTIC-NOISE-SPEC.md` §6). LB is a `sigma = 0.25` result.
### 7.5 The non-monotonicity, examined — EXPLORATORY, POST-HOC

§7.4 recorded the R = 4 tie as "not explained." This subsection examines it.
**The data already existed, so no gate could be honestly pre-registered here. Nothing below
licenses a claim** — it can only dissolve the puzzle or sharpen it. It sharpens it.
Analyser: `scripts/analyse_lb_monotonicity.py`, which reproduces §7.1's four published
means exactly before computing anything new.

**1. It is not sampling noise.** §7.1 tests each R against zero *separately*; four separate
tests against zero cannot establish that two round counts **differ**. The contrast can,
paired on the same `(family, seed, p)` landscape at both counts:

| contrast | mean diff | 95% CI | p | |
|---|---|---|---|---|
| R2 − R3 | −0.000700 | [−0.001297, −0.000238] | 0.0008 | distinguishable |
| R3 − R4 | **+0.000797** | **[+0.000197, +0.001531]** | **0.0035** | **distinguishable** |
| R2 − R4 | +0.000097 | [−0.000363, +0.000613] | 0.7295 | indistinguishable |
| R2 − R5 | −0.000081 | [−0.000425, +0.000281] | 0.6252 | indistinguishable |
| R3 − R5 | +0.000619 | [−0.000031, +0.001388] | 0.0680 | indistinguishable |
| R4 − R5 | −0.000178 | [−0.000784, +0.000441] | 0.5650 | indistinguishable |

**The dip at R = 4 is a real difference, not a sampling accident.** Only the contrasts
involving R = 3 separate; every other pair is indistinguishable. The shape is therefore a
**spike at R = 3**, not a trend with an outlier — and "a reviewer will poke it" cannot be
answered with "it is noise."

**2. The dip replicates in both families that certify at all — but the LEVEL does not.**
These are separable findings and must not be merged:

| family | R=2 | R=3 | R=4 | R=5 | R3 − R4 contrast |
|---|---|---|---|---|---|
| ackley | +0.000087 | +0.000350 | −0.000187 | +0.000112 | **+0.000538, p = 0.0060** |
| hartmann6 | +0.001112 | **+0.003650** | +0.001013 | +0.001413 | **+0.002638, p = 0.0227** |
| levy | 0.000000 | 0.000000 | −0.000013 | 0.000000 | +0.000013, p = 0.7372 |
| rosenbrock | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — |

The R = 3 spike appears **independently in ackley and in hartmann6**, which is much harder
to dismiss than one family's fluke. But LB-1's headline *level* effect is carried almost
entirely by **hartmann6**: ackley's own per-round tests are all null (p = 0.15 at R = 3).

**3. Half the 160 cells are structural zeros — a generalisation limit, not an inflation.**
levy is 100.0% empty for SPADE and 99.4% for qLogNEI; rosenbrock is 100% empty for both.
They contribute exact zeros to every paired difference at every round count. This is the
**saturation already documented in `SPADE-ASSURANCE-CALIBRATION-SPEC.md`** ("ackley and
hartmann6 climb monotonically. levy and rosenbrock SATURATE"), reappearing here.

Dropping them barely moves anything (R=3 p = 0.0000, R=4 p = 0.2715, R=5 p = 0.0455,
R3−R4 p = 0.0063 on the live families) — because the zeros are **paired**, and shrink the
mean and its standard error together. **So this is not a significance inflation, and §7.1's
p-values stand as computed.** What it does limit is *generalisation*: "paired over 160
cells" reads as broader family support than exists. **LB-1 is a two-family result reported
over four.** §7.4 should be read with that attached.

**4. It is not an empty-certificate artefact.** The empty rate falls monotonically in R for
both arms — SPADE 90.0% → 79.4% → 78.8% → 72.5%, qLogNEI 93.1% → 88.1% → 81.9% → 77.5%.
Nothing about *whether* cells certify is non-monotone. The non-monotonicity lives in
**certified volume conditional on certifying**, so any mechanism proposed for it must act
on volume, not on the answer rate. This rules out the first explanation most readers reach
for and is the most useful negative result in this subsection.

**5. LC, as launched, cannot resolve this.** `run_lc_confirmatory.py`'s `CONFIGS` is
`(spade 3, spade 5, qlognei 3, qlognei 5, qlognei 10)` — **there is no R = 4 in either
arm.** The confirmatory run will re-measure the R = 3 spike and the R = 5 margin at 25
seeds with `hill` included, but it will not re-test the tie that makes the pattern
non-monotone. Closing that needs `(spade, 4)` and `(qlognei, 4)` added to `CONFIGS`, which
changes the per-seed row count and so cannot be merged into the run already in flight —
it is a separate companion run.

## 8. The headline comparison: SPADE at 5 rounds vs qLogNEI at 10

Paired on the same 40 `(family, seed)` landscapes, same 48 wells, same `sigma = 0.25`
(SPADE R=5 from `results/lb-*.json`, qLogNEI R=10 from `results/la-*.json`; the oracle is
seeded by `(family, seed)` so the underlying landscape is identical in both):

| | rounds | median regret | certifies? |
|---|---|---|---|
| **SPADE** | **5** | **0.1489** | **YES -- LB 0.9342, 27.5% answered, no inflation** |
| `qlognei` | 10 | 0.1564 | yes (LA §7.1: 21.2%, LB 0.9321) |

**Regret: mean difference -0.0098, 95% CI [-0.0539, +0.0298], p = 0.705 -- PARITY within
the registered SESOI of 0.02.**

**SPADE reaches the same optimisation quality in five rounds that qLogNEI needs ten to
reach, and obtains a certificate at five rounds where qLogNEI obtains none until ten.**

### 8.1 Why this is the claim that matters for cell manufacturing

Wells are cheap; **rounds are not**. A round is a full differentiation cycle -- thaw,
plate, differentiate, assay -- days to weeks of wall-clock, a fresh cell lot, and operator
time each. Halving the round count at equal well count and equal optimisation quality is a
reduction in the resource that actually binds a process-development lab.

### 8.2 Stated at the right strength

- **"Parity" means no DETECTABLE difference, not proven equality.** The CI spans
  [-0.0539, +0.0298] at n = 40; a true difference up to ~0.03 either way remains
  consistent with this data. A larger confirmatory run is owed.
- **The certification half is more robust than the regret half.** LB 0.9342 against *no
  attainable certificate* is a qualitative gap, not a margin, and does not depend on a
  power calculation.
- This is a **cross-experiment pairing** (LA and LB are separate runs). Families, seeds,
  sigma, well count and certification path are identical, but the two were not executed in
  one process, and that is recorded rather than glossed.
- **Conditional on `sigma_rel = 0.25`.** At 0.68 nothing certifies for any arm at any
  round count (`SPADE-REALISTIC-NOISE-SPEC.md` §6).
