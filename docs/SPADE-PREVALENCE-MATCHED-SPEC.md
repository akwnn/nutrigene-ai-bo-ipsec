# SPADE prevalence-matched transfer — pre-registration ("KU")

**Frozen before any KU result exists.** Registers the prospective confirmation of a
**post-hoc** finding. KR and KS both failed their transfer gates; the cause was not the method
but a confound in how I built the comparison, and this spec exists to test whether removing it
holds up on data that does not yet exist.

## 1. The confound, stated plainly

KR-1 and KS-1 calibrated on hill/levy/rosenbrock — scored on the **`tau_frac` grid** — and
tested on ackley/hartmann6 — scored on the **`tau`-quantile grid**. Measured on the committed
rows at γ=0.95, non-empty certificates only:

| | median true prevalence of the target region | median certified volume |
|---|---|---|
| calibration set (easy, `tau_frac`) | **0.9870** | 0.0310 |
| test set (hard, quantile) | **0.3000** | 0.0020 |

Every `tau_frac` cell on the easy families sits at median prevalence ≈ 0.98 (0.9922 / 0.9857 /
0.9870 / 0.9828 at `tau_frac` = 0.60 / 0.75 / 0.85 / 0.95). **A cap calibrated on targets
covering 99% of the box was applied to targets covering 30%.** That is a target-size difference,
not a family difference, and it is the same confound `SPADE-TAU-QUANTILE-SPEC.md` §1 already
diagnosed once for a different question.

**KR-1's and KS-1's FAIL verdicts stand as recorded** — they are correct verdicts on the
comparisons that were actually run. What is now in question is whether those comparisons
answered the question they were registered to answer. This spec does not amend them.

## 2. The post-hoc evidence that motivates KU, labelled as post-hoc

Both hard families are on the **same** grid, so transfer between them is prevalence-matched and
computable with no new compute. Discovered **after** KR and KS failed:

| calibrate on | apply unchanged to | uncalibrated | calibrated | 95% LB | answer rate | |
|---|---|---|---|---|---|---|
| ackley | hartmann6 | 0.8081 | 0.9756 | 0.9524 | 0.238 | PASS |
| hartmann6 | ackley | 0.8889 | 0.9067 | 0.8810 | 0.926 | FAIL |
| **pooled** | | | **0.9310** | **0.9131** | | **PASS** |

Together with the leave-one-family-out result among the easy families (hill 0.9988/LB 0.9962,
levy 0.9730/LB 0.9654, rosenbrock 0.9968/LB 0.9933 — all PASS), that is 5 of 6 directional
transfers passing and both regimes passing pooled.

**This is a lead, not a result.** It was found by inspecting data after two registered gates
failed, one of its six directions FAILS (LB 0.8810), and this project's own rule is that a
re-score cannot settle a question a prospective run can. KU is that prospective run.

## 3. The missing data, and why it does not exist yet

`SPADE-TAU-QUANTILE-SPEC.md` §4 scored **only** ackley and hartmann6 on the quantile grid, and
said so explicitly: *"hill/levy/rosenbrock are NOT re-run under this grid — committing further
compute to re-confirm an already-settled result is out of scope."* That decision was right for
that question and is what leaves KU's comparison impossible today. KU scores
**hill / levy / rosenbrock on the quantile grid** so that all five families sit on one
prevalence convention for the first time.

## 4. Falsifiable predictions, registered now

**KU-1 (PRIMARY — full cross-family transfer at matched prevalence).** With all five families on
the quantile grid, leave-one-family-out volume-conditional calibration — calibrate on four,
apply **unchanged** to the fifth — achieves a one-sided 95% Clopper–Pearson lower bound
**≥ 0.90 pooled across all held-out families** (see §5a: four families, not five), at γ=0.95.
*Comparators, fixed: the confounded version gave LB 0.8175 (`k_eff`) and 0.8074
(`kappa_tail`).*
- **PASS** → the certificate is family-general under a single, declarable scoring convention,
  and the KR/KS failures are explained rather than explained away.
- **FAIL** → the prevalence confound is not the explanation, the post-hoc signal in §2 does not
  survive prospective test, and KU-4 applies.

**KU-2 (per-family, the stricter version).** At least **3 of 4** held-out families (§5a) individually
clear LB ≥ 0.90. *`hartmann6 → ackley` already misses at 0.8810 in the post-hoc data, so this
gate is registered expecting it to be tight, and a 5/5 is not required.*

**KU-3 (no free lunch).** Pooled answer rate ≥ 0.30 across held-out families.
*The post-hoc `ackley → hartmann6` direction achieved its PASS at an answer rate of 0.238,
below this floor; if KU-1 passes only at a comparably low answer rate, KU-3 FAILS and the
result is reported as "calibrated but rarely willing to answer," not as a success.*

**KU-4 (the ceiling, unchanged in substance from KT-6).** If KU-1 FAILS, the recorded conclusion
is that the conservative excursion certificate cannot be made family-general at 48 wells by any
means this project has tested — conditioning on region geometry (KR), on surrogate fit (KS), or
on matching the scoring convention (KU) — and its validity scope must be declared in advance.
That, with the 0/50 scope detector, is four independent confirmations and is the paper's finding.

## 5. Scope, cost, and the reduction rule

`levy`, `rosenbrock` × 4 arms (see §5a) × `P_VALUES = (0.30, 0.10, 0.03, 0.01)`, γ grid unchanged,
`N_DRAWS = 4096`, d=6, σ=0.25 — the exact configuration `run_tau_quantile_followup.py` already
applies to the hard families, extended in **families only**.

No campaign is re-simulated; wells are regenerated through P8's `build()` and gated against
committed `regret`/`n_wells` at `|delta| = 0`, as KR passed 1000/1000.

**Firewalled timing pilot first**, per this project's standard protocol. Measured cost on the
comparable path is ~85–113 s/campaign, so 600 campaigns projects to 14–19 h, over the 8-hour
ceiling. **Seeds are therefore reduced to 25 (300 campaigns, ~7 h) and the reduction is recorded
here, before the run, not discovered in the result.** The reduced power is stated with the
result: 25 seeds against the hard families' 50 halves the per-family n, and KU-2's per-family
bounds will be correspondingly wider. If the pilot projects beyond 8 h even at 25 seeds, arms are
cut to `versionb` and `plate1_only` and that further reduction is reported the same way.

## 5a. Amendment: `hill` is excluded, for a technical reason, recorded before the run

`run_tau_quantile_followup.score_family` reaches the oracle through
`boec.replay.family_evaluator`, which raises `KeyError` on `'hill'` -- hill is an **ensemble**
and goes through `instance_by_id` + `BiphasicOracle`, a separate path that P8's
`evaluator_for` implements and the quantile scorer does not. Adding it would mean forking the
committed scorer for KU's convenience.

**KU therefore runs `levy` and `rosenbrock` only**, which with the existing `ackley` and
`hartmann6` puts **four** families on one prevalence convention. KU-1's leave-one-family-out
becomes leave-one-of-four-out, and KU-2's bar moves from "4 of 5" to **"3 of 4"**, preserving
the same one-family-may-miss tolerance.

This exclusion is technical, was found by the pilot crashing, and is recorded **before any KU
number exists**. It is not a response to any result. hill remains the one family whose
certificate was already validated on its own grid (`SPADE-RESULTS-AND-ANALYSIS.md` §3), so its
absence removes the easiest case from the test rather than a hard one — KU is if anything
harder for excluding it, and that is stated so the result is not read as flattered by the
choice.

## 5b. Amendment: seeds RESTORED to 50, recorded before the run

§5 cut seeds to 25 on a cost estimate of 85-113 s/campaign taken from the KT path. The
firewalled KU pilot -- **timing only, no outcome inspected, nothing written** -- measures
**27.8 s/campaign**, because the quantile scorer runs P8's 3-alpha `ALPHAS` rather than KT's
5-alpha grid. At 50 seeds the full run is 400 campaigns and **3.1 h**, well inside §5's 8-hour
ceiling.

**Seeds are therefore restored to 50.** This is a pre-result change driven by a firewalled
timing measurement, it strictly *increases* power rather than trading it away, and it makes KU's
seed count **identical to the committed `ackley`/`hartmann6` rows** it will be compared against
-- removing an n-mismatch the §5 reduction would have introduced into the very comparison KU
exists to make. §5's warning that "KU-2's per-family bounds will be correspondingly wider" no
longer applies and is superseded here.

## 6. What KU does not decide

KU does not revisit Plate-2 allocation (settled this session: well-powered null on map error,
n=250, MDE 0.0057 against a SESOI of 0.02; the "+19.1% certified volume" reading is withdrawn —
bootstrap CI [−0.114, +0.232]). It does not test the assurance level `alpha` — that is KT
(`SPADE-ASSURANCE-CALIBRATION-SPEC.md`), which remains frozen and unrun, and KU takes priority
because it addresses a **known defect in the comparison** rather than a speculative new knob.
It does not license any claim that SPADE beats a comparator.

`NO_SELECTION` is preserved; the lockbox stays sealed.

## 7. Result

*(Empty at freeze. Filled once, immediately after, from the run.)*
