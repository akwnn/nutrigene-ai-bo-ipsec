# OPEN QUESTIONS — ONE PLACE FOR EVERYTHING NEEDING A DECISION

**This is the only file that collects questions. Nothing gets asked anywhere else.**

---

## 🔴 Q24 [A + B] · **"BO beats current practice" is not supported anywhere it was tested — and the d=8 table reads like the opposite**

### The asymmetry, which is the most misreadable thing in the E2 tables

`e2.yaml` scopes the DoE arm to **d=6 only** (`doe: {dim: [6]}`), on budget arithmetic. So:

| | result | but |
|---|---|---|
| **d=6** | BO **loses** to the DoE pipeline | current practice *was* tested here |
| **d=8** | BO **beats every arm run** | **current practice was not among them** |

**Therefore: "BO beats current practice" is not supported at either dimension.** At d=6 it was tested and went the other way; at d=8 it was never tested. At a glance the d=8 table reads as a clean BO win, and it is not one. **This sentence belongs in the write-up in roughly these words**, because a reader skimming two tables will take the opposite meaning. Credit to A's side for spotting it.

### The d=8 DoE arm is the missing comparison, and it is blocked on a real thing

It is the only run that would test BO against current practice **where BO is actually strong**. It needs the 48-measurement split defined at eight factors, registered before the run (Q20).

**Checked, and it does not currently close.** `screening_design(8, n_centre=4, n_derived=2)` gives **68** runs, so 68 + 27 + 1 = **96**, double the budget. Raising the fraction fails deliberately:

> `ValueError: no known minimum-aberration generator for 2^(8-4). Refusing to invent one: a poorly chosen generator silently confuses effects with each other and nothing downstream notices.`

That refusal is correct behaviour and is why the arm was deferred rather than fudged.

**The split that would close it**, for A to accept or reject **before** any d=8 DoE run:

```
stage 1   2^(8-4) resolution-IV screen, 16 runs + 4 centre     20
stage 2   face-centred CCD on the 4 kept factors               27
stage 4   confirmation                                          1
                                                          total 48
```

Identical in structure to d=6, so the two dimensions stay comparable. **It requires adding the standard 2^(8-4)_IV minimum-aberration generators to `designs.py`** — they are textbook (E=BCD, F=ACD, G=ABC, H=ABD) rather than invented, which is exactly the bar `designs.py` refuses to drop below. **Registering the split before the run is not optional here**: the d=6 result already went against BO, so a d=8 DoE arm designed after seeing that is a design chosen with a known incentive.

### Provenance correction — this session ran no E2

Recorded because it bears on how the replication is described, not to relitigate.

**This session did not run E2, sharded or otherwise.** `scripts/run_e2.py` has **no sharding support at all** — no `argparse`, no shard flag — so a sharded run of it is not possible. And the E2 commits (`fbb98e9`, `0aeee09`) are authored by **josephyung6686**, a different account from this session's.

So if two E2 runs exist, they are **A's and the other session's** — not A's and this one's. **The replication may well be genuine, but its provenance has to be re-established before "reproduced across two independent runs" goes into a paper.** The same misattribution ran earlier: `run_e2.py` and its grid design were credited to this session and are A's.

**What does corroborate independently:** the Q21 solver-failure determination. Counted from `results/e2-run1-unfiltered.log` here (9 failures, per-cell rates, max 0.875%) and from the other session's own run (9 / 3400 = 0.26%) — same conclusion by different routes, **too rare to matter**. Q21's repair rule is registered and has nothing to fire on, which should be stated plainly so the result is not re-opened later as an excuse.

---

## 🟠 Q23 [B raises, A confirms] · **`coord` is a second unpaired arm, and it was not declared**

Found while auditing A's modules during the E2 run. **Registered before the numbers landed; not fixed, deliberately.**

`e2.yaml:53` asserts `identical_initial_design_per_seed: true` without qualification, and `pairing_exempt` listed only `lhs`. **`baselines.py` never calls `initial_design`** — `coordinate_descent` starts from a random interior point. So the claim was false for **two** arms: one declared exempt, one silently.

**This is exactly the defect T9/Q18 found, one arm over.** A fairness field asserting something true of most arms and untrue of one, with nothing failing. The Q18 fix corrected `run_static_baseline` and the field's wording; it did not audit the arms that do not go through `run_static_baseline`, and `coord` is the only one.

### Declared, not fixed — for two reasons

**Pairing it may be wrong on the merits.** The docstring's reasoning for the random start is sound: *"A centre start would be a hidden advantage on an oracle whose optimum sits near the middle."* Seeding coordinate descent from the best of the shared 14-point opening would remove that objection, but it makes the arm **a different and stronger algorithm** — screen-then-descend — rather than the textbook baseline it is there to represent. Given Q22's finding that the landscape is ~93% additive, a coordinate method handed a good starting point would be a *very* strong arm, and the comparison would stop being the one the arm was added to make.

**And the numbers already exist.** `d=6` and `d=8 σ=0.25` are done. Changing an arm now means comparing a repaired `coord` against everything else's stored numbers — the same objection Q21 registers against partial re-runs.

### What this costs

`coord` is unpaired, so its comparison against qLogEI carries the extra variance that pairing exists to remove — the same cost `lhs` pays. It is a **wider interval, not a bias**: the starting point is drawn from the same distribution regardless of arm, so nothing systematically favours either side. **Report `coord` and `lhs` as the two unpaired arms**, with the reason, rather than letting a reader assume the whole table is paired.

**If A wants `coord` paired, that is a full re-grid under Q21's rule**, not a patch to one arm.

---

## 🟠 Q22 [B raises] · **the benchmark landscape is ~93% additive, and that is a limitations-section fact currently living in a test docstring**

**Written before the E2 numbers exist, because it changes how they must be read.**

`tests/test_baselines.py:98` discloses it in prose — *"The oracle is a sum of coordinate-wise-unimodal terms, so coordinate search should get close to the optimum… the limitation is recorded in the suite rather than discovered by a reviewer."* Recording it was right. **It was never quantified, and it is larger than "should get close" suggests.**

### Measured

Fitting a **purely additive** surrogate — a per-coordinate nonparametric mean, no interaction terms of any kind — to 3,000 uniform draws per instance on the shipped ensemble:

| | variance explained by a separable fit | range |
|---|---|---|
| d=6 | **0.930** | [0.926, 0.945] |
| d=8 | **0.927** | [0.907, 0.937] |

**Roughly 93% of the response is separable. Interaction accounts for about 7%.** (In-sample, ~72 additive parameters on 3,000 points, so the true share is maybe a point or two lower. It does not change the reading.)

This is by construction, not a bug: `peak_modulation` enters as `exp((f₀ − ½) · γᵀ / k_pairs)` with `gamma_max = 1.0`, which bounds how far interaction can move each factor's optimum.

### Why it matters, in three places

**1. The `coord` arm is not the straw man its "pre-empts an objection" framing implies.** On a 93%-additive landscape coordinate descent is a *strong* baseline, close to the right model for the problem. If qLogEI beats it, that is a real result. If it does not, the honest statement is **"on a near-separable landscape, cheap coordinate search is competitive with BO"** — a finding, not a failure, and one worth reporting plainly.

**2. It bears directly on E4's null.** The GP's failure to beat nearest-neighbour distance is easier to explain when the surface is nearly additive: a near-additive function is easy for *any* smooth model, so there is less for a GP's structure to exploit. This is a mechanism for the Q19 result, and it is testable — the sign flip across κ should track how much interaction each κ's sub-box actually exposes.

**3. It is the sharpest limit on transfer, and it cuts against the project's own premise.** The motivating study is *about* ECM protein interactions. A benchmark whose interaction term carries ~7% of the variance under-represents the phenomenon the paper exists to study. **Whatever E2 concludes, it is a conclusion about near-separable landscapes.**

### What B recommends

- **Report the 93% figure in limitations, with the method.** "Coordinate search does well" is a hint; a number is a limitation a reviewer can weigh.
- **Report qLogEI vs `coord` explicitly**, alongside qLogEI vs `doe`, under Alan's report-everything ruling. It is the arm that tests whether BO's machinery earns its complexity *on this landscape*.
- **Do not fix it by raising `gamma_max`.** That would be changing the benchmark after seeing which way the results went, and the ensemble is committed and version-stamped precisely to stop that. **A higher-interaction ensemble is a Phase 2 question**, generated deliberately and declared in advance as a separate arm of the study — not a patch.

---

## 🔴 Q21 [A + B] · **the acquisition solver is failing. The repair rule is registered NOW, before the failure rate or the regret numbers are known.**

**Written while `run_e2.py` is still executing, with `d=8` unfinished and `results/e2-grid.json` not yet on disk.** Check the timestamp. This entry is worthless if written afterwards, because every question it settles is one whose answer becomes obvious — and self-serving — once you know whether BO won.

### The problem

`results/e2.log` is accumulating BoTorch acquisition failures: *"Optimization failed on the second try, after generating a new set of initial conditions"* — 4 hard failures in the `d=6` half, plus `A not p.d., added jitter`. On a second-try failure BoTorch does not propose the point it wanted; it falls back to whatever candidates it has.

**Only the adaptive arms call `optimize_acqf`.** So this handicaps qLogEI and qLogNEI and nothing else. A "BO loses" result contaminated by it would be measuring a solver, not a method. (It is also why the rate matters and the raw count does not: 4 failures against ~1,800 optimisations in the `d=6` half is ~0.2%, which changes nothing. `d=8` is where this gets worse, and `d=8` had not finished when this was written.)

### Why this needs registering rather than just fixing

`e2.yaml` registers `no_per_method_tuning: true`, and it is the most-cited objection in this literature — tuning your own method while the baselines sit at defaults. **Raising `num_restarts` or `raw_samples` after seeing that BO underperformed is exactly that objection, whatever the intention.** But refusing to repair a genuine numerical failure is also wrong, and would let a solver bug masquerade as a scientific finding.

The distinction is real and it is decidable **only if the decision rule is fixed before the numbers are seen.**

### What is registered

**1. The repair decision is made on the FAILURE RATE ALONE, computed and acted on before the regret numbers are read.**

> Repair is triggered if second-try acquisition failures exceed **1% of BO batches** in any (dim, sigma) cell. Below that, the run stands and the rate is reported as a limitation.

The 1% threshold is set here, with the `d=6` rate (~0.2%) known and the `d=8` rate **not** known. It is deliberately set above the observed `d=6` rate so it cannot be a rule reverse-engineered to trigger, and low enough that a real `d=8` problem trips it.

**2. Permitted repairs are numerical only.** `num_restarts`, `raw_samples`, `retry` policy, jitter — parameters that change *whether the optimiser converges*, not *what it optimises*. Changing the acquisition function, `best_f` policy, kernel, or budget is not a repair.

**3. A repair is applied identically to every arm that uses the solver** — qLogEI and qLogNEI both, never one — and **the whole grid is re-run**, not the BO arms only. Re-running one arm against another arm's stored numbers compares two different computational conditions.

**4. Both runs are reported.** Pre-repair and post-repair, with the failure rate for each. If the repair changes the conclusion, *that is the finding* and it is stated plainly: the result was solver-sensitive.

**5. Repairing bumps `preregistration_version` again**, with the failure rate that triggered it recorded as the reason.

### What is explicitly forbidden

**Deciding to repair because BO lost.** If the failure rate is under the threshold and BO underperforms, the run stands and the solver is not touched. Under this rule that outcome is reported as-is — which is the entire point of writing the rule down while `d=8` is still running.

### ✅ DETERMINATION — computed from the completed run, **before reading the regret table**

Second-try acquisition failures per (dim, σ) cell, against BO acquisition calls (25 instances × 2 seeds × 2 adaptive arms × rounds per campaign — 9 at d=6, 8 at d=8):

| cell | failures | BO acqf calls | rate | vs 1% |
|---|---|---|---|---|
| d=6, σ=0.25 | 2 | 900 | 0.222% | below |
| d=6, σ=0.10 | 0 | 900 | 0.000% | below |
| **d=8, σ=0.25** | **7** | **800** | **0.875%** | **below — but close** |
| d=8, σ=0.10 | 0 | 800 | 0.000% | below |

**No cell trips the threshold. Under Q21 as registered, the run STANDS, the solver is NOT touched, and the result is reported as-is — including "BO loses".**

This is the rule doing the job it was written for. The threshold was fixed while `d=8` was still running and before any regret number existed; it now binds against the temptation to repair an unfavourable result. **Had it been written afterwards, 0.875% is exactly the number someone could have argued either side of.**

**Report as a limitation:** `d=8, σ=0.25` reached 0.875%, close enough to the line to be worth stating. All 9 failures fall in the two σ=0.25 cells — the failures concentrate at the higher noise level, which is where the GP fit is worst conditioned.

### ⚠️ The evidence was nearly lost

**`results/e2.log` as committed in `0aeee09` contains ZERO of these warnings** — 77 lines against the run's actual 224, with every BoTorch warning stripped. The determination above is not reproducible from the committed artefact.

The full log is restored as **`results/e2-run1-unfiltered.log`**. **A pre-registered decision rule is worth nothing if the evidence it consumes is filtered out of the record before anyone can check it** — and this one exonerates the run rather than condemning it, which is precisely why it must be auditable.

---

## 🔴 Q20 [A decides, B recommends] · E2 · **written while the grid is still running, deliberately**

**The E2 grid was launched before these were settled. Everything below is recorded with no E2 number in existence, which is the only reason it is worth anything.** If it is read after the numbers land, check the git timestamp against `results/e2-grid.json`.

### 1. `comparator: best_non_bo` is under-specified, and it is not the claim Alan is asking about

`e2.yaml:85` registers `primary_cell: {arm: qlogei, comparator: best_non_bo, dim: 6, sigma_rel: 0.25}`. Two separate problems.

**It is under-specified.** "Best non-BO" does not say best by which endpoint, selected per-instance or pooled, or whether qLogNEI counts. `run_e2.py:178` answers all three — pooled mean regret, `qlognei` excluded — but **those are implementation choices sitting outside the pre-registration**, which is how the point-set defect in Q16 and the primary-cell defect in Q19 both happened. Third occurrence of one pattern.

**It is a max-statistic.** The comparator is chosen after the results, as the strongest of ~5 arms. That direction is *conservative* for a "BO wins" claim — you are beating the best of five, not an average — so it does not inflate false positives, and the choice is defensible. But the interval and Wilcoxon *p* attached to a selected comparator are not those of a fixed comparison, and that has to be said out loud rather than left implicit.

**And it answers the wrong question.** The project's framing is a *domain* claim: BO against the procedure the published study actually ran. That is the **DoE arm**, specifically, not whichever arm happens to score best.

> **B's recommendation — register both, as two named estimands, neither chosen afterwards:**
>
> | | comparison | claim type |
> |---|---|---|
> | **Primary — domain** | `qlogei` vs `doe`, d=6, σ=0.25 | "BO beats current practice." The paper's actual thesis. Fixed in advance, not selected. |
> | **Co-primary — methods** | `qlogei` vs `best_non_bo` | "BO beats the strongest alternative we ran." Conservative, and labelled as a selected comparator. |
>
> **Per-instance selection of the comparator is forbidden** — that would be an oracle competitor that exists as no method, the same error as the oracle-best scoring that voided E2's first run.

### 2. Wilcoxon vs the bootstrap — which governs

`e2.yaml` registers `test: wilcoxon_signed_rank` **and** `bootstrap: instance_level` and does not say which decides.

> **B's recommendation:** the **Wilcoxon signed-rank test governs the yes/no**; the instance-level bootstrap reports the **magnitude and interval**. They answer different questions and neither is a check on the other. **If they disagree, the disagreement is reported, not resolved** — a signed-rank test disagreeing with a bootstrap of the mean is a fact about skew or an outlying landscape, and that is worth a sentence rather than a silent choice of whichever agrees.

**Verified good, so it is not on the list:** the clustering is right. `run_e2.py:168` averages seeds within an instance *before* testing, so both the Wilcoxon and the bootstrap see n=25, not n=50. That is the exact error `e2.yaml:74` says would be indefensible, and A avoided it.

### 3. Two smaller things in `e2.yaml`

**`preregistration_version` is still 1 after an in-place correction.** The header says *"If any of them must change afterwards, bump `preregistration_version` and say why."* `identical_initial_design_per_seed` was then corrected in place after B's T9/Q18 — the right thing to record, but it is a post-hoc edit to a pre-registration under the version that predates it. **By the file's own rule this is version 2.**

**`regret_on: noiseless_value_at_selected_point` does not define the DoE arm's selected point.** For every other arm the selected point is the observed argmax. The DoE arm's *output* is the stage-4 confirmation recipe, and `run_e2.py:120` scores it as reported-best over all 48 — so the confirmation counts only if it happens to be the observed argmax, which `results/doe-arm.log` says it is not, in 100% of runs at both noise levels. **This is not obviously wrong** — a practitioner does walk away with the best recipe they saw — but it is the more generous of two defensible rules, and it is unregistered. Say which one it is.

---

## 🔴 Q19 [B raises, A + B decide] · **E4's reported headline is not E4's registered primary, and they disagree in sign**

**This may reverse E4's headline. Raised before anything is written up, not after.**

Verified by re-running `scripts/run_e4.py --instances 25 --rho 2.0` on the current ensemble. Reproduces B's v2 pooled numbers exactly, so this is not a version or ensemble difference.

### The discrimination result is not one number, it is a sign flip

| κ | GP ρ | NN ρ | paired difference | interval clears zero |
|---|---|---|---|---|
| 0.6 | +0.590 | +0.483 | **+0.1068** [+0.0461, +0.1668] | **yes — GP better** |
| 0.7 | +0.404 | +0.422 | −0.0173 [−0.0745, +0.0415] | no |
| 0.8 | +0.272 | +0.368 | **−0.0960** [−0.1450, −0.0470] | **yes — GP worse** |
| 0.9 | +0.267 | +0.368 | **−0.1011** [−0.1481, −0.0561] | **yes — GP worse** |

Pooled: **−0.0269** [−0.0728, +0.0182]. **Three of four cells have intervals clear of zero, in opposite directions, and the pooled number is their average.** "No advantage" is arithmetically true and describes none of the four cells.

### 🔴 The part that matters: the reported headline is the wrong estimand

`configs/experiment/e4.yaml:106` registers `primary_cell: {kappa: 0.6, rho: 2.0}`, and Q16 restates it — *"E4's primary endpoint remains the discrimination Spearman (GP vs nearest-neighbour distance) at `primary_cell: {kappa: 0.6, rho: 2.0}`, with the equivalence bound at 0.08."* **A single cell, named in advance.**

`results/E4-RESULTS-v2.md:25` reports, labelled "pre-registered primary", the number **pooled across all four κ**: −0.027, "no advantage".

**Those are different quantities and they disagree in sign.** At the cell actually registered as primary, the GP is **better** by +0.1068 with an interval clear of zero — and **+0.107 exceeds the pre-registered equivalence bound of 0.08**, so the standing claim *"the advantage is below 0.08 — established, not merely unrefuted"* is false at the registered primary cell. It is true only of the pooled average.

**This is the same defect three times over in this project**, and B is raising it against B's own experiment rather than waiting for a reviewer: the ρ-trend that could not fail, the coverage primary that never named its point set, and now a primary cell that is named and then not reported. Each time the registered quantity and the reported quantity came apart.

### What B is NOT claiming

**Not that the GP wins.** κ=0.6 is the *most* extrapolated cell, the pooled estimate is negative, the two largest-κ cells are significantly negative, and the prior art in `E4-RESULTS-v2.md` says a null is the expected outcome under GP theory. A single favourable registered cell inside a negative surface is exactly the "corner-shaped claim" Q16 warns against.

**The honest reading is that E4 has no single headline.** The discrimination result is κ-dependent, the dependence is large, and it reverses sign across the registered grid.

### The decision, for A

Two defensible resolutions, and **B is deliberately not choosing**, because either choice made by the person who has seen the numbers is the thing pre-registration exists to prevent:

1. **The registered cell stands.** Report κ=0.6 as the confirmatory result — GP better, +0.107 [+0.046, +0.167], equivalence bound breached — and the other three κ as the pre-specified surface that contradicts it. Most faithful to what was written down. Reverses the headline.
2. **The pooled estimand was always the intent** and `primary_cell` was a mis-registration. Then say so explicitly, in the paper, with the date the discrepancy was found — and report the sign flip regardless, because pooling across it is what hides the finding.

**What must happen either way:** the per-κ table is reported in full. Pooling a sign flip into "no advantage" is not a summary, it is a cancellation.

### One reporting defect found alongside

`run_e4.py` prints `significant=False` for κ=0.8 and κ=0.9, whose intervals are [−0.145, −0.047] and [−0.148, −0.056] — **clear of zero**. The flag is one-sided and means "significant *advantage*", but it is unlabelled, so the output reads as "nothing here" next to two of the strongest effects on the grid. Anyone scanning this log would conclude the opposite of what it shows.

---

## 🟠 Q18 [A + B] · T9 · **the paired opening batch did not exist, and the test that said it did tested something else**

**B has implemented the part the spec already decided and is flagging the one part it did not. A: the LHS exemption below is the only genuinely new call and it needs your sign-off.**

### The defect, in two independent halves

`optimizers.initial_design`'s docstring says *"This must be identical across every method being compared, for a given seed… There is a test for it."* Both clauses were false.

**Half one — the arms shared nothing.** `initial_design` had exactly one caller, `campaign.py:280`, the BO arm. `run_static_baseline` generated all 48 points from the method's own generator and never called it. So random and LHS opened on a completely different batch from qLogEI.

**Half two — the pairing was destroyed at scoring even where it existed.** The ordering average permuted **all** `budget` points, scattering any shared opening through the curve. Pairing that survives design but not scoring is not pairing.

**And the test.** `test_initial_design_is_identical_across_methods_for_a_seed` called `initial_design` twice with the same seed and asserted equality. It tested determinism. It never touched a second method. **A test whose name carries the guarantee and whose body does not is worse than no test — it is where everyone stops looking.** Renamed to `test_initial_design_is_deterministic_for_a_seed`; the real cross-arm assertions are in `test_runner.py`.

### One thing nobody had noticed: **Sobol was already paired, for free**

`initial_design` *is* `sobol_design(bounds, 2d+2, seed)`, and a Sobol prefix is stable, so the natural 48-point Sobol design already began with exactly the shared opening. Verified and now guarded by a test, because it is the reason the policy costs that arm nothing and a change to either function would silently end it.

### What is registered

> **Every arm opens on the identical batch, in the identical order, and that segment is not shuffled.** Only the method-specific remainder is shuffled and averaged — which is also the segment spec §E2 computes AUC over.

**This half is not a new decision.** Spec §E2 already fixed it — *"The initial design must be identical across methods for a given seed — paired comparison at n=50 is the difference between a significant and a non-significant result. Test for it."* It was specified, never implemented, and guarded by a test that did not test it. Implementing it is not B deciding anything.

Cost by arm, which is why this was cheap: **Sobol — free**, already paired. **Random — free**, it has no global structure to damage. **LHS — expensive**, and hence:

### 🔶 THE ONE NEW CALL, AND IT IS A + B: **LHS is exempt**

A Latin hypercube's stratification is a property of the **whole** n-point set. A 14-point Sobol prefix plus a 34-point Latin-hypercube remainder **is not a Latin hypercube** — it is a straw man wearing the name of a baseline. The spec's own scoping is explicit that a baseline has to be good or the result is worthless.

So LHS runs **unpaired**, and is reported as the one unpaired arm with its wider interval and the reason stated. **B's reasoning, A's call.** The alternatives, both worse: pair it and report a hybrid under the `lhs` label, or drop the arm.

**What would change this:** if A can construct a Latin hypercube of 48 whose first 14 points are the shared opening and which still stratifies, the exemption is unnecessary and should go. B could not.

### Implemented

`runner.static_design(bounds, method, budget, seed, share_opening=None)`. `None` applies the registered policy — pair unless exempt. `True` **demands** pairing and raises on an exempt arm, so a caller who believes every arm is paired finds out rather than being quietly right for three arms and wrong for one. `False` opts out explicitly. Six tests, including one asserting unpaired LHS is still a real Latin hypercube — the exemption has to actually buy something — and one asserting the ordering average still applies to the remainder, so the pairing fix does not silently trade away the thing that makes a one-shot design comparable to an adaptive one.

**Deliberately not done:** wiring this into E2's driver. That is T11 and it is A's.

---

## 🔴 Q16 [EITHER] · PRE-REGISTRATION, WRITTEN BEFORE THE NEXT RUN · **the (κ, ρ) grid is the over-prediction result. No single cell is the headline.**

**Committed before PF1 is re-run at the pre-registered regime, deliberately, so the history shows it was decided in advance and not selected afterwards.**

### The problem this fixes

The over-prediction endpoint has moved four times: unit cube → ρ=1.2 proposed as primary → ρ=2.0 adopted in v2 → ρ=3.0 floated as the strongest cell. **Every one of those moves followed seeing a result, and every one was individually defensible.** That is exactly the pattern pre-registration exists to stop — the cumulative effect is a headline chosen for its size, and no reader can tell the difference from outside.

It will happen again. ρ is still not a *declared factor*; it is a config value we keep re-picking. And the oracle has already changed once (v6 → v8); a corner-shaped claim would not survive another change, while a trend would.

### What is registered

**Estimand — a surface, not a point.** The full grid is the result and is reported in full:

```
kappa in {0.6, 0.7, 0.8, 0.9}   x   rho in {1.2, 1.5, 2.0, 3.0, inf}
```

**Primary claim, directional and falsifiable:**

> **Over-prediction increases monotonically with the extrapolation ratio ρ, and decreases monotonically with κ.**

Tested as a *trend across the grid*, not a contrast between two cells: per-instance Spearman of over-prediction against ρ (and against κ), aggregated to a single estimate **at instance level** with a cluster bootstrap. Four κ on one landscape are four measurements of one landscape, not four independent observations — B already fixed this nested-clustering bug once in `0fc2610`, and it applies here identically.

**Secondary claim:** over-prediction decreases with the instance's true depth. Now testable, because the shipped ensemble records `true_depth` per instance and it varies (0.109–0.135 at d=6).

**What would falsify it:** a non-monotone trend, or a bootstrap interval on the trend statistic that includes zero. Both are real possibilities — the trend must be demonstrated, not assumed from the four unit-cube numbers we happen to have.

**ρ = ∞ (the unit cube) stays in the grid** as the limiting case. It is not dropped for being indefensible; it is *reported as* the indefensible end of a continuum, which is more informative than deleting it.

### What this does NOT change

**B's v2 pre-registration stands untouched.** E4's primary endpoint remains the discrimination Spearman (GP vs nearest-neighbour distance) at `primary_cell: {kappa: 0.6, rho: 2.0}`, with the equivalence bound at 0.08. **This entry governs the over-prediction *characterisation*, which is the mechanism evidence, not the novel claim.** The two coexist: one cell carries the confirmatory test, the whole grid carries the description.

### Why a trend is the better scientific object anyway

*"Over-prediction rises with extrapolation ratio and falls with instance depth"* is a statement about when a second-order surrogate stops being trustworthy — which is the thing a practitioner actually needs, and it transfers to Phase 2 and Phase 3. *"Over-prediction is +9.2 at κ=0.6 in the unit cube"* is a fact about one corner of one synthetic ensemble and transfers nowhere.

**Signed off by A. B: object here before the run if you disagree, not after.**

### ⚠️ CORRECTION TO Q16, made after the first grid run and BEFORE E4 — **A registered a primary that could not fail**

PF1 ran the registered grid (40 instances × 4 κ × 5 ρ = 800 cells, `results/pf1-grid.log`). The ρ trend came back at **Spearman +1.0000, CI [+1.0000, +1.0000]** — a perfect score on every instance at every κ. That is not a strong result; it is the signature of a test that cannot fail.

**It is forced by geometry, and the proof is three lines.** `extended_box_bounds` gives `[0, min(1, ρ·κ·x*)]`, so the boxes are strictly **nested** in ρ — verified: upper bound 0.288 → 0.360 → 0.480 → 0.720 → 1.000. The fitted surface is *identical* across ρ (we fit once per (instance, κ) and reuse). The maximum of a fixed function over a larger set is ≥ its maximum over a subset, so `y_predicted` is monotone non-decreasing in ρ **by construction**. And `y_true` is bounded above by 1.0 because the oracle is peak-normalised. So `over_prediction = y_predicted − y_true` rises with ρ as a matter of arithmetic, not biology.

**This is the same defect A has flagged twice in other people's work this project** — E4's original non-separability check that could never pass, and A's own first DoE arm whose escape statistic was vacuously 0%. Registering it in a pre-registration is worse, because a pre-registration is exactly the document a reader trusts not to contain one. Recording it rather than quietly restating the endpoint.

#### The replacement primary, which can fail

> **The second-order model's prediction interval loses nominal coverage of the true response as ρ increases, and we report the ρ at which it crosses.**

This is falsifiable and it is the question a practitioner actually has — *how far past my data can I trust this interval?* It can come back null: A's earlier κ×ρ sweep measured **96–98% coverage at ρ = 1.2 at every κ**, i.e. perfectly calibrated in the published study's regime. If coverage holds at every ρ, the claim fails and that is a real finding.

**The κ trend stays as registered and it is genuine:** −0.2712 [−0.3988, −0.1450], instance-level bootstrap. Nothing forces it — κ changes the *training data*, not just the scoring box, so the fitted surface differs and the sign could have gone either way.

**The over-prediction surface stays, demoted to descriptive.** It is still worth printing; it is just not evidence of anything.

#### The registered secondary FAILED, in the opposite direction

> Registered: over-prediction *decreases* with instance true depth.
> **Measured: +0.3893 at κ=0.6 and +0.1285 at κ=0.9. Positive. The claim is refuted.**

Reported as a failed prediction, not quietly dropped. Caveat that cuts both ways: true depth spans only [0.1086, 0.1390] across the ensemble — by design, since the acceptance floor compresses it — so this test had little power and the positive sign should not be over-read either. **If we want depth as a real factor, the ensemble needs deliberate depth variation, which is an ensemble change and therefore a joint decision.**

#### One descriptive fact worth keeping

**Turning point was a saddle in 800 of 800 cells.** Zero maxima, zero minima, across 40 instances and four κ. That is now the fourth independent confirmation, after PF1's first run, B's E4 run, and the DoE arm. The spec's prediction of minima at low κ was 1-D reasoning applied to a 6-D surface and is comprehensively wrong.

### ✅ B'S ANSWER (T1) — **the replacement primary is accepted; the reported quantity is objected to**

A asked for an objection before the run rather than agreement, so both halves are here.

#### The direction claim IS falsifiable — and for a reason stronger than the one given

A's defence was that coverage came back 96–98% at ρ=1.2, so the claim *can* return null. That is evidence, not a proof, and it is the same kind of evidence the ρ-trend had before it was shown to be forced. The structural argument is available and it is three lines, in the same style as A's:

For a second-order model the regressor vector `x₀ = [1, x, x², xx']` **already contains the quadratic terms**. Scale `x` by λ and the quadratic block scales λ², so leverage `h = x₀ᵀ(XᵀX)⁻¹x₀` scales λ⁴ and the half-width `t·σ̂·√(1 + h)` scales **λ²**. The fitted surface's own divergence from a bounded truth also scales **λ²**. **Same order.** Neither term dominates by construction, and which one wins is decided by `σ̂`, the design geometry and the true curvature — none of which are forced.

Contrast with the withdrawn ρ-trend, where `y_true ≤ 1` was bounded and `y_pred` was monotone in ρ by box nesting, so the sign was arithmetic. **This one is a genuine race.** Confirmed in the committed grid — bias and interval grow at near-identical rates from ρ=1.2 to the cube:

| κ | over-prediction | PI width |
|---|---|---|
| 0.6 | ×63 | ×44 |
| 0.7 | ×30 | ×31 |
| 0.8 | ×21 | ×20 |
| 0.9 | ×12 | ×14 |

Had the interval grown an order slower, the claim would have been another tautology. It does not.

#### The objection: **"the ρ at which it crosses" presumes one crossing, and there appear to be two**

Ratio of median over-prediction to median half-width, from `results/pf1-grid.log`. Above 1 means the bias exceeds the interval:

| κ | ρ=1.2 | ρ=1.5 | ρ=2 | ρ=3 | cube |
|---|---|---|---|---|---|
| 0.6 | 1.04 | 1.74 | 2.11 | 2.19 | 1.50 |
| 0.7 | 1.21 | 1.74 | 1.98 | 1.79 | 1.19 |
| 0.8 | **0.89** | 1.35 | 1.38 | 1.19 | **0.92** |
| 0.9 | **0.98** | 1.15 | 1.12 | **0.92** | **0.83** |

**Non-monotone at every κ** — it rises to a peak around ρ=2–3 and falls back. **Caveat stated at the time, because it cut against the objection:** a ratio of two medians is *not* the coverage rate, and can be non-monotone while `P(|over| ≤ pi/2)` is monotone. So this raised a well-posedness risk; it did not establish one.

#### ⚠️ THE RATE HAS NOW BEEN COMPUTED, AND IT CORRECTS THE MECHANISM ABOVE

`scripts/pf1_coverage.py`, all 800 cells, `covered ⟺ |over| ≤ pi/2`, instance-level cluster bootstrap. Log at `results/pf1-coverage.log`. **Independently cross-checked against the median table above: all 20 cells agree in sign about whether coverage sits above or below 50%.**

| κ | ρ=1.2 | ρ=1.5 | ρ=2 | ρ=3 | cube |
|---|---|---|---|---|---|
| 0.6 | 0.475 | 0.075 | 0.025 | 0.000 | 0.100 |
| 0.7 | 0.325 | 0.100 | 0.075 | 0.100 | 0.175 |
| 0.8 | 0.525 | 0.300 | 0.300 | 0.425 | 0.550 |
| 0.9 | 0.575 | 0.300 | 0.350 | 0.575 | 0.625 |

**The conclusion holds. The mechanism given for it was wrong, and is corrected here rather than quietly restated.**

**There are ZERO crossings, not two.** The ratio table crosses **1**, which is the *50%* coverage mark, not the *nominal 95%* one. Coverage never reaches nominal anywhere on the grid — the highest cell is **0.625 against a nominal 0.95**, including at ρ=1.2. So the crossing ρ is undefined because **the interval never had nominal coverage to lose**, not because it loses it more than once. A stronger result than the objection claimed, arrived at by a worse route.

**The non-monotonicity was real** and reproduces on the actual rate at all four κ — dipping and then recovering toward the cube — so the saturation mechanism (the argmax stops moving outward once the box saturates while `σ̂·√(1+h)` keeps inflating) is supported. It is simply not a statement about crossings.

#### 🔴 THE DECISIVE DEFECT — **the registered sentence never says WHICH POINT SET**

This does **not** contradict A's 96–98% at ρ=1.2. **It measures a different point set.** A's figure is coverage over the design/domain; the table above is coverage **at the recipe the model tells you to run**. Both are legitimate, both are "coverage of the second-order prediction interval", and on the same registered sentence they return **opposite verdicts** — calibrated versus catastrophic.

**That ambiguity matters more than the monotonicity argument.** A primary endpoint that two people can compute correctly and disagree about is not a pre-registration; it is the thing pre-registration exists to prevent, in the one document a reader trusts not to contain it. It is also the third time in this project a registered quantity has turned out under-specified, after the ρ-tautology and the E4 non-separability check.

#### Amendment, for A to accept or reject — **supersedes the one first proposed here**

> **Coverage is registered at BOTH point sets, each as a surface over the (κ, ρ) grid:** at the second-order model's **constrained argmax** (decision-relevant, and the worst case, since the argmax is selected for high predicted value) and at a **fixed held-out set** (domain-wide, no selection effect). The crossing ρ is reported only where one exists.

This mirrors the structure E3 already uses for its two point sets, and applies Q16's own "the grid is the result" logic to its replacement primary instead of exempting it. **The gap between the two surfaces is itself informative** and should be reported — it is the difference between "this model is well calibrated" and "this model is well calibrated everywhere except where it sends you".

**What would falsify the claim:** coverage flat near nominal 95% across the whole grid, at both point sets.

---

## 🔴 Q14 [EITHER] · E4 HAS RUN. The mechanism is huge; the headline claim is null. Decide n BEFORE rerunning.

**A: read `results/E4-FIRST-RESULTS.md` before anything else.** 40 cells, 78 seconds, on your v8 ensemble.

**What worked, unambiguously:**

- Over-prediction is enormous and scales with κ exactly as designed: **+9.2 → +5.6 → +3.3 → +2.0**, against a response whose max is ~1.0. Every cell extrapolated (40/40).
- The GP over-promises **5–20× less** than the polynomial at every κ.
- **Your Q13 risk did not materialise: 0/40 cells had the peak inside the training corner.** The validity check stays regardless.
- Headroom healthy everywhere (0.83–0.88, threshold 0.95). Practitioner-fit failures: 0/40.

**What did not:**

> **The GP does not beat plain nearest-neighbour distance. Pooled +0.051, CI [−0.003, +0.100], not significant.** Same at every κ. Against the polynomial's own interval width it is +0.004 — flatly nothing.

That is the comparison E4 was built around. On this evidence the honest statement is *the GP is an expensive distance function*.

**But it is a power problem, not a flat null.** All four κ point the same way; the pooled interval misses zero by 0.003; headroom confirms the comparison could have resolved a difference. Instances needed at the observed effect: **~31 at κ=0.6, ~44 at κ=0.8, ~10 at κ=0.9.** We have 10. **The full grid costs 78 seconds — 40 instances is about five minutes.**

**THE DECISION, AND IT MUST BE MADE BEFORE THE RERUN.** Raising n after seeing a result that missed significance, then reporting it as though n had been chosen in advance, is what makes a finding unpublishable. If we scale: bump `preregistration_version` to 2 and state in the paper — *"the first run at the pre-registered n was underpowered for the paired comparison; n was raised on a power calculation performed on that run."* Defensible. A silent rerun is not.

**B's recommendation:** bundle the n decision with Q12 into a single version-2 pre-registration, then run once.

> ### ✅ A's side of Q14 is done — **the d=6 ensemble is extended to 40.** `n_instances_if_ensemble_extended: 40  # Needs A` is satisfied.
>
> **Agreed on the substance:** raise n, bump the pre-registration, state the power calculation in the paper. Silent reruns are how findings become unpublishable. B's v2 wording is right.
>
> **Extending is safe, and A verified it rather than asserting it.** Instances are drawn independently per seed and `instance_id` hashes (dim, seed, oracle_version), so seeds 25–39 cannot perturb 0–24. Confirmed by regenerating three committed seeds and comparing the **landscapes**, not just the parameters: `max |f(X) − f'(X)| = 0.000e+00`, identical `instance_id`. Locked as `test_regenerating_a_committed_seed_reproduces_it_exactly`.
>
> **Only d=6 was extended.** E4 is d=6-only by pre-registration, and E2's grid is 25 × 2 seeds, so d=8 stays at 25. Say if you want d=8 raised too.
>
> #### ⚠️ A correction to A's own PF2, found while doing this
>
> The version field earned its keep. Rebuilding the sampler config by hand gave a **different `oracle_version`** for numerically identical landscapes — because a bare `SamplerConfig()` carries `accept_floor = 0.045`, the **v6 spec's** value, while the shipped ensemble was generated at **0.1083**.
>
> **That had already corrupted a number A reported.** PF2.3's "v8 shipped" acceptance rate of *100% / 100%* was measured at the easier floor. **Corrected: 70% (d=6), 80% (d=8)** at the real floor. The v8 case is unchanged — v6 is 6.395% and 0.105% — but the honest figure is 70/80, and anywhere the 100% was quoted needs fixing.
>
> Closed properly rather than patched: `boec.oracles.SHIPPED_CONFIG` is now the one object that generated what is on disk, asserted against `ENSEMBLE_VERSION` in the suite, with a second test that fails if the bare defaults ever drift into matching it. **Do not rebuild the config by hand.**

### Unpredicted finding, worth its own line

**Every fitted surface was a saddle. 40/40.** No maxima, no minima. The spec predicted a mix and specifically warned that low κ would give *minima*. It was wrong, cleanly. This is exactly why the stationary-point **distribution** was required instead of a bare escape rate — a rate would have hidden it.

---

## 🟠 Q12 [EITHER] · A was right, and the numbers now say so

A argued the unit cube is indefensible: 2–4× extrapolation in all six coordinates at once, against the published study's 1.2× in one.

**The run confirms it.** At over-prediction +9.2 with an interval width ~7 on a response of max 1.0, **"the traditional method's interval is too narrow" is not available as a finding** — the interval covers almost anything. A reviewer would call the comparison staged and be right.

`extended_box_bounds(x_star, kappa, rho)` is in `designs.py`, tested, with the default reproducing current behaviour exactly. **This is now a config decision, not a code change.**

**B agrees with A.** Recommend κ=0.6, ρ=2.0 primary, unit cube reported as a limiting case — folded into the same version-2 bump as Q14.

---

## ✅ Q13 [RESOLVED 2026-08-08] · A's three deviations from spec §4 — **ACCEPTED by Alan. B does not exercise the veto.**

**Decision: A's v8 stands. Port it, use it, cite it as the ensemble.**

Reasoning on the record, so the paper can state it:

1. **The interaction term.** A showed by differentiation that the spec's `β` product **cannot move the optimum** — the bracket multiplying each factor's derivative contains no dependence on that factor. Measured shift over 276 instances: `0.00e+00`. This is not a preference; it means §4.6's own non-separability acceptance check **can never pass**, and in the 8% with a negative bracket the cached optimum was landing below the true one, driving regret negative. Reverting would mean knowingly shipping that.
2. **Weight structure.** Equal weights cap depth at `1/d`, which kills the d=8 arm outright at σ_rel=0.25 — A measured 0 of 50 instances clearing the required depth. The 4-active/90% structure also matches the published 6→4 screening, giving the DoE arm something real to find, and gives ARD a 4.5–5.4× active-to-inert ratio against 1.0× under the spec. Under the spec the kernel comparison on the critical path had **no signal to discriminate on**.
3. **Depth formula.** Overstated true depth by a median 28.4%.

**The risk A flagged as landing in B's lane is now tested and did not occur.** `run_e4_cell` locates the true optimum and refuses to pool any cell whose optimum sits inside the training corner: **0/40 across all four κ**. The check stays regardless — it costs one optimisation per cell and is the difference between a null result and a silently meaningless one.

**Consequence for the write-up:** the ensemble is `biphasic-hill-v8`, not spec §4 as written. Doc 1 §4 is now historical and must be marked as superseded before anyone cites it.

## 🟠 Q15 [EITHER] · The DoE arm is built, and its result is the strongest one we have. One parameter decides it — pre-register that parameter.

`boec/doe.py`, 14 tests, `scripts/run_doe_arm.py`, log at `results/doe-arm.log`. Stage 1 screen (20) → stage 2 CCD on the survivors (27) → fit → **measure the predicted optimum (1)** = 48, the identical budget every other E2 arm gets.

**d=6, 10 landscapes × 2 seeds, scored with B's shared `over_prediction_at_constrained_argmax`:**

| | σ_rel = 0.10 | σ_rel = 0.25 |
|---|---|---|
| predicted optimum fell **outside** the stage-2 region | **100%** | **100%** |
| confirmation **under-delivered** vs the best design point | **100%** | **100%** |
| over-prediction, median [IQR] | **+0.73** [0.64, 1.00] | **+1.66** [1.41, 2.06] |
| sat *on* the stage-2 boundary | 0% | 0% |
| screen recovered the planted active factors | 94% | 86% |
| fitted surface turning point | saddle 20/20 | saddle 20/20 |

**Why this matters more than it looks, given Q14.** E4's standing objection is that we chose κ, so of course the model extrapolates. **This arm hides nothing.** It runs the published procedure over the full space, and the narrowness of stage 2 comes from the screen rather than from us. The over-promise still reproduces, on the same scale as E4a, against a response whose maximum is 1.0. With E4's discrimination claim null, this is the strongest single result in the project — and it is a *domain* claim, not a methods claim.

Two supporting details. The **0% on-boundary** rate says this is genuine extrapolation, not the constrained-optimiser signature `project_record.md` §E9 identified in the published optimum — so the two mechanisms are separable and we can discuss them independently. And **saddle 20/20** matches PF1 and B's E4 run exactly; three independent routes to the same unpredicted fact.

**The parameter, and why it is a question rather than a default.** Stage 2 explores `± stage2_half_width` around the best stage-1 run. A used 0.25.

> **At 0.5 stage 2 spans the whole range, the predicted optimum cannot fall outside it, and the escape statistic is a vacuous 0%.** A's first implementation did exactly that and reported 0% escape across 40 runs, which read as a clean negative result and was a tautology. Two tests now assert stage 2 is a strict sub-region and the search region strictly wider, so it cannot recur silently.

The headline moves 0% → 100% on one argument. **A has deliberately run no other value**, so the pre-registration is not retrofitted. Proposal: fix `stage2_half_width = 0.25` in the E2 config before any further runs, justified as "a local exploration spanning half the range — standard RSM practice of following a screen with a narrower design", and fold it into the same version-2 bump as Q12/Q14.

**One thing B should call:** dropped factors are currently held at the **best stage-1 run's** level. Holding them at **zero** is arguably closer to the published procedure, since Hall/Ogle's own optimum sits at zero for both dropped laminins. A chose the best-run level because it is what a practitioner does and keeps the confirmation point where the data speaks. Recorded either way in `DoEResult.dropped_held_at`.

### ✅ B'S CALL (T2) — **`best_stage1` is the primary, `zero` is a declared sensitivity. Both are reported.**

**Registered with neither arm run.** The `zero` policy did not exist in the code when this was decided — `doe.py` hardcoded the best-stage-1 level — so there was no number to choose between. That is the point, and it is why this entry can be trusted in a way the four moves of the over-prediction endpoint in Q16 cannot.

#### The decision rests on an asymmetry that is knowable in advance

The two policies are not symmetric candidates where one picks the more realistic. **One is conservative and one is flattering, and which is which follows from the screen's error rate without running either.**

- **`best_stage1` is conservative.** Stage 2 stays near the region stage 1 found good, so the fitted surface has *less* distance to extrapolate and the confirmation point is closer to data. **The over-promise is harder to demonstrate under this policy.**
- **`zero` is flattering, and the mechanism is screen error.** The screen recovers 94% of planted active factors at σ_rel = 0.10 and **86% at 0.25** (the table above). A wrongly dropped factor is an *active* one, and pinning an active factor to zero drags stage 2 into a genuinely worse region of the space. The fitted surface then has further to reach and **should over-promise more.**

**The conservative arm is the primary.** This is the same principle as the `stage2_half_width = 0.5` near-miss recorded above: the policy that makes the headline easiest to obtain is the one that must not be the default. Choosing the flattering arm as primary would be defensible on fidelity grounds and indefensible on every other.

#### Why fidelity to Hall/Ogle does not win here

It is the better argument for `zero` and it is real — their optimum does sit at zero for both dropped laminins. It loses for two reasons. **Their optimum sitting at zero is an output, not a held input**; the PDF cross-check established that fibronectin was boundary-clamped and Collagen IV extrapolated, so their zeros are what a constrained profiler *returned*, not what the design *held*. Reading a held level off a reported optimum assumes the answer. And fidelity to a procedure whose failure we are characterising is a weak reason to adopt its most failure-prone variant as the primary — **especially when we can simply report both.**

#### What is registered

| | policy | role |
|---|---|---|
| primary | `hold_dropped_at="best_stage1"` | the default in `doe.py`; every headline DoE number |
| sensitivity | `hold_dropped_at="zero"` | reported alongside, always, not only if it agrees |

**Both arms are reported whatever they show.** If `zero` over-promises more, that is the screen-error mechanism confirmed and it strengthens the finding. If it over-promises *less*, the a priori argument above is wrong and that is reported as a failed prediction, in the same way Q16's registered secondary was. **Neither outcome licenses swapping the primary.**

Cost is not a consideration: the DoE arm runs in **0.03 s per cell** (measured, d=6, single-threaded), so the sensitivity arm is free.

#### Implemented

`doe.py` takes `hold_dropped_at`, exports `HOLD_POLICIES`, records the policy on `DoEResult.hold_dropped_at` so a stored row can never be attributed to the wrong arm, and **raises on an unrecognised value rather than falling back to the default** — the same silent-substitution class as the T8 `runner.py` fall-through. Four tests, including one asserting the two policies produce genuinely different confirmation points, so the sensitivity cannot go vacuous the way `stage2_half_width = 0.5` did.

**For A:** the default carries the registered primary, so this needs nothing from `e2.yaml` to be correct. Carry `hold_dropped_at` into the E2 config explicitly anyway when T11 lands — an inherited default is not a pre-registration.

---

## 🟠 Q17 [A, but B should sanity-check] · E1 exposed a bias in how regret is scored. Fix it before E2 runs.

**E1 passed the gate**, and while passing it produced a number that cannot be true:

```
function     known optimum        BO best-so-far
branin            -0.3979              -0.3747     <-- BETTER than the optimum
```

Nothing beats the optimum. What is being reported is the best **observed** value, and the best of 48 noisy draws is systematically flattering — the winner is partly whichever point drew lucky noise. At σ_rel = 0.10 on a function whose optimum sits near zero, that bias is larger than the quantity being measured.

**Why it matters for E2 specifically, and why it is not self-cancelling.** All arms see the same noise level, so the naive hope is that the bias cancels in a comparison. It does not: the size of the upward bias depends on **how many distinct high-value points an arm samples**, and that differs by arm *by design*. Random and Sobol scatter 48 independent draws; BO concentrates its later batches in a small region and re-samples near-duplicates. Those are different numbers of effective lottery tickets. **An arm can therefore win E2 partly by buying more chances at good noise**, which is not the claim we want to make.

**The fix, which is standard and which A will implement:** score regret at the **noiseless value of the point the method selected**, not at the noisy observation. Selection still uses only what the method is allowed to see; scoring uses `truth()`, which exists precisely for this and is never shown to any model. Concretely, best-so-far becomes `max_t f_true(x_t)` over evaluated points, and the DoE arm's stage-4 confirmation is scored the same way — as it already is, via B's shared metric.

**This is also the concrete cost of the Q5 decision, now visible.** qLogEI's "best value seen so far" is exactly this inflated incumbent. Q5 registered qLogEI as primary with qLogNEI as a declared secondary; E1 shows the bias is real and measurable rather than theoretical, which makes reporting both more clearly worthwhile than it looked at the time.

**Not a licence to change anything else.** This is a fix to a *scoring* function, decided and written down **before E2 has been run even once**, so it cannot be a response to seeing an E2 number. Every other setting — kernel, acquisition, initial-design size, batch plan, seeds — stays exactly as pre-registered.

**One incidental E1 note, so nobody chases it:** gpytorch emits *"Very small noise values detected… rounding up to 1e-06"* throughout E1. That is a scale artefact of the standard test functions — Branin and Ackley span hundreds of units, so `Yvar / var(Y)` after `Standardize` falls below 1e-6. The biphasic oracle has range ~1 and does not trigger it. Not a bug in our noise path.

> ### ✅ B's sanity-check — **A's reasoning is right, the gate survives the fix, and the bias is ~12% of the effect**
>
> A asked for a sanity-check rather than agreement, so this is the measurement. Same `TorchEvaluator`, same σ_rel = 0.10, same 20 seeds, same budget 48 — **only the scoring changed**. Selection still sees nothing but the noisy observations.
>
> | function | known opt | BO (truth) | random (truth) | difference | 95% CI |
> |---|---|---|---|---|---|
> | branin | −0.3979 | −0.4116 | −0.9745 | +0.5629 | [+0.3083, +0.8601] |
> | **hartmann6** | 3.3224 | 2.6606 | 1.7466 | **+0.9140** | **[+0.6693, +1.1623]** |
> | ackley | 0.0000 | −20.0746 | −20.3301 | +0.2556 | [−1.0059, +1.6794] |
>
> **The gate holds.** Hartmann6 moves +1.03 → **+0.914**, interval nowhere near zero. E1's PASS is not an artefact of the bias.
>
> **A's non-cancellation argument is confirmed, and now has a number.** Inflation on Hartmann6 was **+0.155 for BO against +0.035 for random** — differential **+0.120**, in exactly the direction A predicted, because BO concentrates and re-samples while random scatters. It is real and it is not self-cancelling. It is also only ~12% of the 1.03 gap, so the fix sharpens E1 rather than rescuing it.
>
> **Branin's impossible number resolves cleanly.** Rescored on truth it is **−0.4116**, correctly *below* the optimum instead of above it. That is the fix demonstrated, not merely argued.
>
> **Two consequences worth carrying forward.**
>
> 1. **Every absolute figure in `results/e1.log` is flattering**, not just Branin's. Hartmann6's BO result is really 2.66, not 2.87 — 80% of the way to the optimum rather than 86%. Anywhere those numbers are quoted needs the debiased ones.
> 2. **On Ackley the bias is enormous — +4.15 (BO) and +4.47 (random)** — because its values sit near −20 and relative noise scales with magnitude. Best-observed is close to meaningless there, and the sign of the difference actually flips (−0.058 → +0.256) while staying null. This is a *second*, independent reason Ackley should not gate, on top of the one A declared in advance.
>
> **Caveat on these numbers.** This is an independent re-run, not a rescoring of A's stored traces, and the BO figures differ from `results/e1.log` by ~0.01 (Branin −0.3659 here vs −0.3747 there) from RNG ordering between the two scripts. It does not touch the conclusion, but it is not a byte-identical reproduction.
>
> ### ⚠️ Separately: spec §E1's fourth check is not implemented
>
> §E1 is not only the three textbook functions. It also requires: *"on a `β = 0` oracle instance, BO converges toward `sqrt(EC50·IC50)` per dimension."* `scripts/run_e1.py` runs Branin, Hartmann6 and Ackley only, so this one has never run.
>
> It matters more than the other three, because it is the only E1 check that exercises **our own landscape family** rather than borrowed benchmarks — the three standard functions would pass identically if the Hill oracle were broken.
>
> It is also cheap, and B has verified the construction: the shipped v8 ensemble is `peak_modulation`, so the equivalent of `β = 0` is `gamma = 0`, which makes the effective peak `x*_i · exp(0) = x*_i` in every coordinate. Confirmed on a real accepted instance — `f(x*) = 1.0` exactly, and `x*` equals `sqrt(ec50·ic50)` to machine precision, which is the spec's wording literally. **A's call whether to add it, since E1 is A's lane.**

---

## 🟡 Q7 [ALAN] · Author order, and whether the code can be released publicly

Neither blocks building. Both block posting the preprint.

---

## ✅ CLOSED

| | Question | Answer |
|---|---|---|
| **Q1** | Does the oracle exist? | **Yes — ported, merged, 310 tests passing. E4 has run on it.** |
| **Q2** | Who owns `designs.py`? | B owns it; A deleted their copy and is second reader. |
| **Q3** | Test-function wrappers? | Exist, wearing the Evaluator interface. |
| **Q4** | Evaluator interface? | Confirmed by execution. No adapters needed. |
| **Q5** | qLogEI vs qLogNEI? | Run both. qLogEI pre-registered primary, qLogNEI declared secondary. |
| **Q8** | `Yvar` floor? | `sigma_add**2 = 1e-4`. |
| **Q9** | Face-centred vs rotatable? | Face-centred — rotatable axials leave the sub-box. |
| **Q10** | The two pre-registered numbers | 512 candidates, τ = within-instance 0.80 quantile. **Version 2 now proposed — see Q14.** |
| **Q11** | First commit / layout | Done, pushed, shared. |
| **Q13** | Accept A's oracle deviations? | **Accepted 2026-08-08.** v8 is the ensemble. Risk to B's lane tested: 0/40. |
| **C1** | `observation_noise=True` at unrun points? | Silently averages training noise. Never used. |
| **C2** | Units for supplied noise? | Standardized, not raw. Off by 161× otherwise. |
| **C3** | `Normalize` without bounds? | Learns from data. Always pass explicit bounds. |
| **C4** | Discrete-candidate function? | `optimize_acqf_discrete(...)`. |
| **C5** | Does batch selection cluster? | No — it conditions on each pick. |
| **C6** | Grid too slow? | No. Full E4 is 78 seconds. |
| **C7** | 48-run pattern arithmetic? | Exact: 32 + 12 + 4. |
| **C8** | Stepwise conditioning via pinv? | Non-issue — rank filter guarantees full rank; agrees with lstsq to 9.7e-13. |

---

## Where B is up to

**E4 is built, tested, and has produced results on real landscapes** at both regimes. Reproduce with `python scripts/run_e4.py` and `python scripts/run_e4_robustness.py`.

**Figures are built** — `boec.figures`, three PNGs under `results/figures/`. Spec Build Step 7 is done, superseding the note that previously stood here.

**Blocked on:** the version-2 pre-registration — Q12, Q14, Q15 and Q16 together, as one bump. Ordering and owners are in `docs/TASKS.md`; two of the four (T1, T2) are waiting specifically on B.

**Latest from B:** Q17 sanity-checked — the E1 gate survives the regret-scoring fix (Hartmann6 +1.03 → +0.914 [+0.669, +1.162]), and A's non-cancellation argument is confirmed at a differential of +0.120. Details in Q17.

**`runner.py` dispatch defect closed (T8).** `run_cell` sent *every* unrecognised method to the adaptive branch, so a `doe` cell — a method `GridCell` already documents as valid — ran a **Bayesian optimization campaign** and wrote a believable parquet under a `method-doe` filename. An E2 grid would have reported BO's numbers as the DoE baseline's. Now `doe` raises `NotImplementedError` pointing at `boec.doe.run_doe_arm`, unknown names raise `ValueError`, and six tests cover the dispatch. **The DoE arm still needs wiring in properly — that is A's, and it is T8's remaining half.**

**Not yet built:** an untested `nonlinear_inequality_constraints` path that matters only for Phase 3.
