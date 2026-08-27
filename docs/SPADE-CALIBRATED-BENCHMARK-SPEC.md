# SPADE vs all comparators, at matched calibration — pre-registration ("KX")

**Frozen before any KX result exists.** Registered after an exploratory read of
`results/final-spade-combined.json` that is disclosed in full in §2, because that read
motivated the hypothesis and must not be presented as confirming it.

## 1. The gap this closes

SPADE has never been compared to `qlognei`, `qlogei`, `sobol`, `lhs`, `random` or `doe`
**on the task it is designed for**. Every published comparison used regret (an optimiser
metric, KF-8 = parity) or map error (KF-3 = null). The certified-region task was computed
for all twelve arms and never adjudicated.

## 2. Disclosed exploratory finding (motivating, NOT confirming)

From `results/final-spade-combined.json`, all arms, `gate_status=ok`, `rankable=True`,
containment among non-empty certificates, expected volume counts abstentions as zero:

| arm | answer rate | truth containment | E[certified volume] |
|---|---|---|---|
| `doe` | 39.9% | **0.2934** | 0.016491 |
| `qlognei` | 51.3% | 0.8266 | **0.003097** |
| `qlogei` | 50.2% | 0.7482 | 0.002995 |
| `spade_cf_m0` | 23.9% | 0.8552 | 0.001246 |
| `lhs` | 21.5% | 0.8823 | 0.000951 |
| `random` | 18.3% | **0.9023** | 0.000777 |
| `sobol` | 17.7% | 0.8730 | 0.000681 |

**Two facts, both recorded against interest:**
1. **No arm clears a 0.90 lower bound.** The entire comparator field is uncalibrated.
2. **SPADE LOSES on raw volume.** `qlognei` returns 2.5x SPADE's expected certified
   volume. A raw volume comparison is a comparison SPADE loses, and it must not be
   published as if SPADE won it.

## 3. The hypothesis, and why it is mechanistic rather than hopeful

`qlognei` concentrates wells at the **optimum**; SPADE's straddle concentrates them at the
**theta contour**. Certified volume is limited by posterior uncertainty *at the boundary*.
Inflation shrinks a certified region by an amount governed by boundary uncertainty.

**Therefore: forcing every arm to honest containment should cost `qlognei` more volume than
it costs SPADE, because `qlognei` bought its volume with confidence it did not earn at the
boundary.** This is the same mechanism KW-4 measured within the SPADE family
(`SPADE-SELECTION-BLIND-SPEC.md` §6.3b: targeting answered 76 vs 5 at c=1.0 with containment
0.7938 vs 1.0000 -- more answers, more wrong). KX asks whether it holds against real BO.

## 4. KX-1 (PRIMARY, registered now)

Every arm is calibrated **on its own terms**: for each arm, `c*` is the smallest value in
`C_GRID` whose leave-one-family-out pooled truth containment has a one-sided 95%
Clopper-Pearson lower bound **>= 0.90**.

**KX-1 PASSES iff, at each arm's own `c*`, SPADE's expected certified volume (abstentions
counted as zero) exceeds every comparator's, paired by `(family, seed, p)`, with a paired
bootstrap 95% CI excluding zero against the single best comparator.**

- **FAIL** -> SPADE does not win the certified-region benchmark against BO baselines, and
  the honest paper claim is the mechanism paper of `SPADE-SELECTION-BLIND-SPEC.md` §6.3b
  alone. **This is registered as a real possible outcome and will be reported as measured.**

## 5. KX-2 (does any comparator reach honesty at all?)

For each arm, report whether **any** `c` in the grid achieves LB >= 0.90 at answer rate
>= 0.05. An arm that cannot be calibrated to honesty at any inflation, at a non-trivial
answer rate, **cannot deliver a guaranteed region at this budget** -- a qualitative result
that does not depend on KX-1's margin.

## 6. KX-3 (the doe result stands or falls on its own)

`doe`'s 0.2934 containment at 13x SPADE's volume is the largest effect in §2. KX reports
`doe`'s calibrated `c*` and post-calibration volume without folding it into KX-1's ranking,
because `doe` is a screening design and the comparison is not like-for-like.

## 7. Scope and honesty constraints

- `C_GRID = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0)`. Wider than KT's because a comparator
  may need far more inflation; a `c*` at the grid ceiling is reported as **truncated, not
  passed**, exactly as `SPADE-ASSURANCE-CALIBRATION-SPEC.md` §8.1 required.
- Arms regenerated through `boec.replay.regenerate`, identical oracle/seed/noise stream.
- The certification path is byte-identical across arms: same `vorobev_columns`, same subset,
  same seeded generator. **The only thing that differs between arms is where the wells are.**
- Analyser written and its reproduction gate passed BEFORE the data lands.
- `NO_SELECTION` preserved; the lockbox stays sealed.

## 8. What KX cannot establish

KX is simulation at `sigma_rel = 0.25` on benchmark landscapes. It cannot support any claim
about cell-media performance, and a KX-1 PASS is a claim about **certified region recovery
under a fixed 48-well budget**, not about optimisation and not about wet-lab behaviour.
