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

## 7a. Amendment, made BEFORE any KX row was read

The first KX launch projected **15.5 h** at 280 s/job under three-way CPU contention.
Amended now, with the partial output discarded unread:

1. **`C_GRID` narrowed from 8 values to `(1.0, 1.5, 2.0, 4.0, 6.0, 8.0)`.** The dropped
   values are the *interior* ones (2.5, 3.0). The wide ceiling that §7 registered as the
   rationale -- "a comparator may need far more inflation" -- is **preserved intact**, and
   the truncation rule still applies at 8.0. Resolution between 2.0 and 4.0 is the only
   thing lost, and no gate depends on it.
2. **Seeds 50 -> 30.** KX-1's unit is `(family, seed, p)`, so this is 4 x 30 x 4 = 480
   paired cells per arm, ample for the registered bootstrap.
3. **The finite-set estimand is scored alongside the region estimand**, from the *same
   draws, same tau, same inflation*. The two differ only in what they are asked to
   certify. No KX gate is changed by this; it adds columns, and any claim about them
   requires its own registration (§7b).

**Nothing above was informed by a KX result.** The partial file from the first launch was
deleted without being analysed.

## 7b. KX-4, registered now — the finite-set estimand against real BO

Motivated by an exploratory probe (64 cells, `versionb` only, committed at `bf4845b` with
its own caveats): at `c=2.0` the finite-set estimand answered **10.9%** against the region
estimand's **4.7%** at identical containment 1.0000.

**KX-4 PASSES iff, at each arm's own calibrated `c*` (selected exactly as KX-1 selects it,
but on finite-set containment), SPADE's finite-set answer rate exceeds every comparator's
AND its held-out finite-set containment lower bound is >= 0.90.**

- **FAIL** -> the finite-set estimand is not a SPADE advantage; it is an estimand change
  that helps every design equally, and must be reported as such rather than as a SPADE
  result. **This is the outcome I consider most likely** and it is registered first.

**Registered interpretation constraint.** The finite-set guarantee is strictly weaker than
the region guarantee: a certified region implies it for any subset, and the converse is
false. Every reported KX-4 number must carry that sentence. An answer-rate gain bought by
weakening the claim is a trade, not a free improvement, and must never be presented as
the region result.

## 9. KX RESULT — KX-1 FAILS. qLogNEI's certificate beats SPADE's.

4 families x 30 seeds x 7 arms x 6 inflation values, 20160 rows
(`results/kx-calibrated-benchmark.json`), adjudicated by
`scripts/analyse_kx_calibrated_benchmark.py`, written before the data landed.

### 9.1 The result

Pooled over all four families at `alpha = 0.95`:

| arm | best `c` | answer rate | containment | 95% LB | clears 0.90? |
|---|---|---|---|---|---|
| **`qlognei`** | **1.0 (none)** | **27.7%** | **0.9624** | **0.9226** | **YES** |
| `versionb` (SPADE) | 1.5 | 7.5% | 0.9444 | 0.8353 | no |
| `lhs` | 1.0 | 4.2% | 1.0000 | 0.8609 | no |
| `sobol` | 1.0 | 3.5% | 1.0000 | 0.8384 | no |
| `qlogei`, `random`, `doe` | -- | -- | -- | -- | no |

**KX-2: `qlognei` is the ONLY arm that can be calibrated to an honest certificate**, and it
requires **no inflation at all**. **KX-1: FAIL.** SPADE's held-out expected certified volume
is **0.000000** against `qlognei`'s **0.000780**; paired difference **-0.000780**, 95% CI
[-0.000982, -0.000596]. The CI excludes zero **in the comparator's favour**.

This is not a power artefact. At `c = 1.0`, `qlognei` answers on **133** cells to SPADE's
**54** and is simultaneously *more* accurate (0.9624 vs 0.7222).

### 9.2 The mechanism, and it inverts this project's premise

`qlognei` concentrates wells at the optimum, so the region it certifies sits **where the GP
has the most data** -- tight posterior, honest certificate, small but real volume. SPADE
spends plate 1 space-filling and plate 2 on the theta contour, i.e. deliberately at the
place the model knows **least**. §3 predicted the opposite: that forcing honesty would cost
`qlognei` more volume than SPADE because it "bought volume with confidence it had not
earned at the boundary". **That prediction is refuted.** `qlognei` had not over-claimed; its
certificate was honest at `c = 1.0` from the start.

### 9.3 What this does and does not overturn

**Overturned:** any claim that SPADE's two-plate design yields better certificates than
Bayesian optimisation. `SPADE-SELECTION-BLIND-SPEC.md` §6.2's result -- targeting beats
*random plate 2* and *one plate*, p ~ 1e-8 -- **stands as measured and is now known to be
the wrong comparison**: it compared SPADE against its own weaker controls and never against
BO. KX supplies the comparison that was missing, and SPADE loses it.

**Not overturned:**
1. The posterior-collapse fix (`boec.meanmarg`). It is a property of the GP, applies to
   **every** arm including `qlognei`, and is what makes any of these certificates
   trustworthy on real data (297-484x).
2. Honest abstention. `doe` still certifies large regions at 0.2934 containment
   (§2); the failure mode SPADE was built to prevent is real.
3. The real-noise wall. At `sigma_rel = 0.68` nothing certifies, `qlognei` included.
4. The `hill` regret advantage (`SPADE-STATE-OF-THE-METHOD.md`), which is a separate
   estimand on a separate dataset.

### 9.4 Recorded conclusion

**The honest headline is that SPADE's contribution is the DIAGNOSIS and the FIX, not the
design.** This session found that conservative excursion-set certification is
self-validating, that its posterior collapses at low SNR in a way simulation cannot detect,
and that simulation-calibrated inflation is 3x too conservative for real assays. Those
findings apply to `qlognei`'s certificate exactly as much as to SPADE's -- and on this
evidence, **the right recommendation for a lab is to run qLogNEI's design and SPADE's
corrected certificate.**
