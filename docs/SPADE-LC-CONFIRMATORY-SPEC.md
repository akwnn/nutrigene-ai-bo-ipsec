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
