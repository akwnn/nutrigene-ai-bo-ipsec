# LC — the confirmatory run. Pre-registration.

**Frozen while LC was in flight and BEFORE any LC outcome was inspected.** At the time of
writing, the author had seen only row counts and seed indices from the checkpoint files
(`400 rows, 10 seeds done`) — no regret, no volume, no containment, no per-arm value. The
commit that adds this file lands before the run completes; `git log` timestamps against the
`results/lc-*.json` mtimes are the check.

Data: `results/lc-*.json` · Runner: `scripts/run_lc_confirmatory.py` ·
Analyser: `scripts/analyse_lc_confirmatory.py` (frozen with this document).

## 1. Why LC exists

Three defects in the current headline, from `SPADE-ROUND-SWEEP-SPEC.md` §8.2:

1. **The headline is a cross-experiment pairing.** SPADE R=5 came from LB, qLogNEI R=10
   from LA — separate processes. Families, seeds, sigma, well count and certification path
   were identical, but the two were never executed together.
2. **`hill` is absent from LA and LB entirely**, and was void in KZ-2 (tau was computed
   from instance 0 while each seed drew a different instance). `hill` is the biphasic
   dose-response family — **the only one shaped like the cell-manufacturing problem the
   paper claims to address.** LC computes tau PER INSTANCE.
3. **n = 10 seeds.** LC runs 25.

## 2. Design

5 families (`hill`, `ackley`, `hartmann6`, `levy`, `rosenbrock`) x 25 seeds x
`CONFIGS = (spade R3, spade R5, qlognei R3, qlognei R5, qlognei R10)`, 48 wells,
`sigma_rel = 0.25`, `alpha = 0.95`, inflation grid `c in {1.0, 1.5, 2.0, 3.0}`.

**`c` is selected leave-one-family-out**, exactly as `analyse_la_round_matched.py` does:
calibrate on the other four families, evaluate on the held-out one. Containment is read
from `ce_empirical_*`, **never `ce_contain_*`**.

**Declared limitation, not a finding:** `CONFIGS` contains **no R = 4**, so LC **cannot**
re-test the R = 4 tie that makes `SPADE-ROUND-SWEEP-SPEC.md` §7.5's pattern non-monotone.
That needs a separate companion run. LC re-tests the R = 3 spike and the R = 5 margin only.

## 3. LC-1 (PRIMARY) — the headline survives in one process

**SPADE at R = 5 and qLogNEI at R = 10 are at parity on regret**, paired by
`(family, seed)`, bootstrap 95% CI within the **pre-registered SESOI of 0.02** already
declared in `SPADE-ROUND-SWEEP-SPEC.md` §8.

- **PASS** — CI lies within +/- 0.02: the cross-experiment caveat is discharged and
  "same optimisation quality in half the rounds" is a one-process result.
- **FAIL, qLogNEI better beyond SESOI** — the headline was an artefact of pairing two runs.
  **This retracts §8.** It is a real possible outcome and is stated here before the fact.
- **INCONCLUSIVE** — CI straddles a SESOI edge. Parity is then *undemonstrated*, not
  disproven, and must be reported as such rather than rounded to PASS.

## 4. LC-2 — the certification asymmetry, in one process

Smallest `c` reaching **LB >= 0.90 at answer rate >= 0.05**, per arm and round count.
Registered expectation from LB §7.2 and LA §7.1: **SPADE certifies at R = 5; qLogNEI does
not at R = 5 but does at R = 10.**

- **PASS** — that pattern reproduces. This is the *qualitative* half of the headline and
  LB §7.4 already argues it is the more robust half.
- **FAIL** — if qLogNEI certifies at R = 5, "half the differentiation cycles" is dead.

## 5. LC-3 — `hill`, the family that decides generalisation (CO-PRIMARY)

`SPADE-ROUND-SWEEP-SPEC.md` §7.5 established that LB-1's effect is carried by **two of four
families**: levy and rosenbrock never certify for either arm. So the open question is not
only "is the effect real" but **"does it exist on the shape the paper is about."**

Reported for `hill` specifically, and this is registered as **co-primary, not a subgroup**:

1. Does `hill` certify at all for either arm at R = 5? (levy/rosenbrock do not.)
2. Does the LC-1 regret parity hold on `hill` alone?
3. Does the LC-2 asymmetry hold on `hill` alone?

- **`hill` saturates like levy/rosenbrock** — then **every certification claim in this paper
  is a claim about test functions that do not resemble a dose-response**, and must be
  written that way. This would be the single most important negative result in the project.
- **`hill` behaves like hartmann6/ackley** — the cell-manufacturing framing is supported by
  the one family that earns it.

## 6. LC-4 — the R = 3 spike, at 2.5x the seeds

`SPADE-ROUND-SWEEP-SPEC.md` §7.5 found SPADE's certified-volume win over qLogNEI at R = 3
(paired R3−R4 contrast p = 0.0035, replicating independently in ackley p = 0.0060 and
hartmann6 p = 0.0227). **That was exploratory and post-hoc.** LC re-measures the R = 3
comparison at 25 seeds with `hill` added.

**This is a confirmatory replication of a known exploratory finding, and is labelled as
such** — the direction is not blind. A PASS is evidence; it is not independent discovery.

## 7. Honesty constraints binding on the LC write-up

- The analyser reproduces nothing from LB/LA and shares no state with them; LC stands or
  falls on `results/lc-*.json`.
- LC is `sigma_rel = 0.25`. **At the real assay noise measured in
  `SPADE-REALISTIC-NOISE-SPEC.md` §6 (`sigma_rel = 0.68`) nothing certifies for any arm.**
  No LC result may be stated without that ceiling attached.
- Partial data is analysable — the runner is seed-major and checkpoints only after a seed's
  full `CONFIGS` sweep — but **any partial analysis must print the seed count it used.**
- Structural zeros: if a family never certifies for either arm, it contributes exact zeros
  to paired differences. Per §7.5 this does not inflate p-values (the zeros are paired) but
  it does narrow generalisation, and the analyser must report which families are live.

---

## 8. LC RESULT — the headline does not survive. 5 families x 25 seeds, one process.

`results/lc-*.json`, adjudicated by `scripts/analyse_lc_confirmatory.py`, written and
committed before the data landed (`19f845a`, `a64e3a4`, vs the result-file mtimes).

### 8.1 LC-2 FAILS — "SPADE certifies at 5 rounds, qLogNEI needs 10" is DEAD

Registered in §4: *"**FAIL** — if qLogNEI certifies at R = 5, 'half the differentiation
cycles' is dead."* It certifies at R = 5. It also certifies at R = 3.

Leave-one-seed-out (out-of-sample; the LOFO path is degenerate, see §8.4):

| arm | R | LOSO LB | containment | answer | certifies? |
|---|---|---|---|---|---|
| SPADE | 3 | 0.9151 | 0.9815 | 21.6% | **YES** |
| SPADE | 5 | 0.9152 | 0.9663 | 35.6% | **YES** |
| qLogNEI | 3 | **0.9180** | 1.0000 | 14.0% | **YES** |
| qLogNEI | 5 | **0.9258** | 0.9839 | 24.8% | **YES** |
| qLogNEI | 10 | 0.8790 | 0.9452 | 29.2% | no |

**Why the earlier claim was wrong, verified rather than asserted.** It was a sample-size
artefact acting through the Clopper–Pearson bound, *not* a containment deficit:

| | answered | misses | containment | LB |
|---|---|---|---|---|
| LB (10 seeds) qLogNEI R=5, c=1.5 | 31 | **1** | 0.9677 | **0.8559** — fails |
| LC (25 seeds) qLogNEI R=5, c=1.5 | 62 | **1** | 0.9839 | **0.9258** — passes |

Same single miss, same high containment, double the n. With one miss the lower bound is
acutely n-sensitive. **`SPADE-ROUND-SWEEP-SPEC.md` §7.2 and §8's "half the differentiation
cycles" claim must be withdrawn.** It was measured on too little data, and LB §7.4's own
warning that "a registered confirmatory run at larger n is owed" was correct.

### 8.2 LC-1 (PRIMARY) — INCONCLUSIVE, not a pass

SPADE R=5 vs qLogNEI R=10 on regret, paired by `(family, seed)`, n = 125:
**mean +0.0015, 95% CI [−0.0219, +0.0239]** against the registered SESOI of ±0.02.

The CI marginally exceeds the SESOI at both ends, so by §3's own wording this is
**INCONCLUSIVE — parity is UNDEMONSTRATED, not disproven.** The point estimate is close to
zero, and a larger n would likely resolve it, but the registered verdict is what it is.

Per family, SPADE is **worse on ackley** (+0.0564, CI [+0.0050, +0.1094], p = 0.029) — the
only per-family regret result that separates, and it is against SPADE.

### 8.3 LC-3 (CO-PRIMARY) — `hill` SATURATES. The generalisation claim is gone.

| family | cells | non-empty | rate |
|---|---|---|---|
| hartmann6 | 1000 | 667 | 66.7% |
| ackley | 1000 | 338 | 33.8% |
| **hill** | 1000 | **5** | **0.5%** |
| levy | 1000 | 1 | 0.1% |
| rosenbrock | 1000 | 0 | 0.0% |

§5 registered the consequence before the data existed: **every certification claim in this
project is a claim about `ackley` and `hartmann6` — two synthetic test functions, neither of
which resembles a dose-response.** `hill`, the only biphasic family and the only one shaped
like the cell-manufacturing problem the paper is about, certifies 5 times in 1000 cells.
This is the most important negative result in the project and it must be written into the
paper's scope, not buried.

### 8.4 LC-4 — SPADE's certified-volume win at matched rounds REPLICATES and strengthens

The registered LC-4 computation inherits the LOFO path, which is degenerate here and
returns zeros for reasons unrelated to the hypothesis. Recomputed on the LOSO path
(**post-hoc**), SPADE − qLogNEI, positive = SPADE better:

| R | n | mean | 95% CI | p |
|---|---|---|---|---|
| 3 | 250 | +0.000242 | [+0.000108, +0.000390] | <0.0001 |
| 5 | 250 | +0.001326 | [+0.000944, +0.001742] | <0.0001 |

**Monotone increasing — LB §7.5's "spike at R = 3" does NOT replicate.** LC has no R = 4,
so the tie itself is still untested (declared in §2 before the run).

**This is the claim that survives LC:** at matched rounds, SPADE certifies more volume than
qLogNEI. It is *not* "SPADE needs half the rounds."

### 8.5 What the paper may now say

- **Survives:** at matched round counts, SPADE certifies more volume than qLogNEI
  (R = 3 and R = 5, both p < 0.0001), on `ackley` and `hartmann6`, at `sigma_rel = 0.25`.
- **Withdrawn:** "SPADE certifies at 5 rounds where qLogNEI needs 10." qLogNEI certifies at
  R = 3 and R = 5 once n is adequate.
- **Undemonstrated:** regret parity between SPADE R=5 and qLogNEI R=10.
- **Scope, mandatory:** the certificate has never been shown to work on a dose-response
  landscape. `hill` saturates.
- **Ceiling, unchanged:** at the measured real assay noise (`sigma_rel = 0.68`) nothing
  certifies for any arm (`SPADE-REALISTIC-NOISE-SPEC.md` §6).

---

## 9. LC EXTENDED to 32 seeds — and why `hill` really saturates

§8.2 showed LC-1 was underpowered: CI half-width 0.0226 against a SESOI of 0.0200.
The run was extended to 32 seeds (`--resume`, so the original 25 are byte-identical).
n = 160 pairs.

### 9.1 What survived, and what did not

| comparison | 25 seeds | 32 seeds | verdict |
|---|---|---|---|
| SPADE R=5 vs qLogNEI R=10, regret | +0.0015 [−0.0219,+0.0239] | **+0.0016 [−0.0184,+0.0208]** | **parity** (half-width 0.0196 < SESOI) |
| SPADE R=3 vs qLogNEI R=10, regret | +0.0237 | +0.0263 [+0.0054,+0.0472] | SPADE worse — 3 rounds is not enough |
| SPADE vs qLogNEI, matched R=3, regret | −0.0235 (excl. 0) | −0.0181 [−0.0373,+0.0013] | **DID NOT SURVIVE** |
| SPADE vs qLogNEI, matched R=5, regret | −0.0051 | −0.0055 [−0.0251,+0.0142] | no difference |
| SPADE vs qLogNEI, R=3, certified volume | +0.000242 (p<0.0001) | −0.000034 (p=0.456) | **DID NOT SURVIVE** |
| **SPADE vs qLogNEI, R=5, certified volume** | +0.001326 | **+0.001353 (p<0.0001)** | **HELD** — ackley and hartmann6 both p<0.0001 |

**Three effects vanished between 25 and 32 seeds.** Only effects several times their own CI
survived. That is now the third such episode in this project (KX, LB-1 at R=3, and these),
and it is a standing rule: **at n <= 25 seeds an effect here is not reliable.**

**The defensible claim:** SPADE at 5 rounds matches qLogNEI at 10 on regret, and delivers
substantially more certified volume at matched 5 rounds. It is NOT better on regret at
matched rounds — that claim died at 32 seeds.

### 9.2 ROOT CAUSE: `hill` does not saturate because it is a dose-response

Measured on the shared Sobol grid, per family (seed 0), where `margin` is the mean excess
of the good region over `tau` and `noise_sd` is `sigma_rel` x the good region's response:

| family | median/max | margin over tau | noise sd | **margin/sd** | observed cert. rate |
|---|---|---|---|---|---|
| hartmann6 | 3% | 0.1320 | 0.0524 | **2.52** | 66.7% |
| ackley | 11% | 0.0268 | 0.0214 | **1.25** | 33.8% |
| hill | **71%** | 0.0658 | 0.2064 | **0.32** | 0.5% |
| levy | 77% | 0.0567 | 0.2219 | **0.26** | 0.1% |
| rosenbrock | 85% | 0.0396 | 0.2351 | **0.17** | 0.0% |

`margin/sd` rank-orders the certification rate perfectly. The mechanism is **dynamic range
under multiplicative noise**: noise is `sigma_rel * f`, so a landscape whose good region
sits at high absolute response carries large absolute noise. `hill`'s median is 71% of its
max — it is compressed near the top — so a 30th-percentile `tau` carves a band 0.066 wide
while the noise sd there is 0.206.

**Therefore `hill` saturating is NOT evidence that the certificate fails on dose-response
landscapes.** It is evidence that **`tau` defined as a QUANTILE of the response is
degenerate on compressed landscapes.** Note the real iPSC-EC certification
(`SPADE-REAL-IPSC-RESULT.md`) used an ABSOLUTE threshold — "CD31+ >= 33.2%" — not a
quantile. The quantile-`tau` is a benchmarking convenience, and it is the thing that fails.

§8.3's conclusion is **narrowed accordingly**: it remains true that no dose-response
landscape has yet been certified, but the reason is now known and is a property of the
benchmark's target definition, not of SPADE.

**This is testable and not yet tested.** The registered follow-up is in
`docs/SPADE-TAU-DEGENERACY-SPEC.md`.
