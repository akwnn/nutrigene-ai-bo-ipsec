# RESULTS — the standing record of every experiment this project has run

**Purpose.** Results are scattered across `OPEN-QUESTIONS.md`, `RESULTS-PERSON-A.md`,
`E4-RESULTS-v2.md`, individual logs, and chat sessions that no longer exist. Several
entries were superseded in interpretation without being marked. This file is the index:
what ran, why, what it found, and whether it is still current.

## Rules for this file

1. **Every number traces to a committed file.** The log or JSON path is named in each
   entry. *A number with no committed file does not go in* — one fabricated figure has
   already nearly entered a decision.
2. **Superseded entries stay, marked.** Nothing is deleted.
3. **Wrong predictions get their own line.** Six registered predictions have been wrong.
   Each is more informative than a correct one; burying them makes the correct ones
   worthless.
4. **Corrections get their own line**, including *how the error arose*.
5. **Plain language in "What it means."** A cold reader should not have to reconstruct
   the method.

## Status legend

`current` · `superseded by [ID]` · `void — [reason]` · `provenance-flagged` (the number
is real but was computed in a clone whose inputs were not shared — see D12)

> ⚠️ **Two numbering systems exist.** The close-out brief uses different Q-numbers from
> this repository. The concordance is at the top of `OPEN-QUESTIONS.md`. Where this file
> says QNN it always means **this repository's** numbering.

---

# PART 1 — PRE-FLIGHT

## PF1 — the (κ, ρ) over-prediction surface, and a trend that could not fail

**Ran:** `scripts/preflight_pf1.py`, `scripts/pf1_coverage.py` · `results/pf1-grid.log`,
`results/pf1-coverage.log`
**Status:** current, but see D3

### Why
Before building E4, establish that a second-order surface fitted in a sub-box
over-predicts at its own constrained argmax, and measure how that scales with the
sub-box fraction κ and the extrapolation ratio ρ.

### Result
The over-prediction surface across κ × ρ, and prediction-interval coverage of the true
response. Coverage is below the nominal 0.95 everywhere on the grid.

### What it means
The mechanism E4 was built to detect is present and measurable before any GP is involved.

### Limits — and the defect it produced
**D3: the ρ pre-registration was unfalsifiable.** Nested boxes make over-prediction
monotone in ρ *by arithmetic*, so the registered trend could not have come out any other
way. Measured Spearman +1.0000 with a zero-width CI, and it was written up as a finding
before anyone noticed it could not fail.

---

## PF2 — the mathematics the downstream numbers rest on

**Ran:** `scripts/preflight_pf2.py` · covered in `RESULTS-PERSON-A.md` §5
**Status:** current

### Why
The Hill inversion, the closed-form δ_max, and the sampler's acceptance rate are load
bearing for every oracle instance. Check them against brute force before generating an
ensemble.

### Result
Inversion round-trips; the closed-form δ_max matches a brute-force scan; the acceptance
loop terminates at the declared rate.

### What it means
The oracle's construction is arithmetically sound. This says nothing about whether it is
*realistic* — see L1 and Q42.

---

## PF-A / PF-B — sampler acceptance and the E4 kill condition

**Status:** current
**Ran:** `scripts/preflight_pf3.py`, `scripts/preflight_pf4.py`

### Result
The v6 sampler accepted **0.15%** of draws at d=8 — effectively a rejection sampler that
would never terminate. Restructured (draw `w` first, resample per factor, accept on
numerically computed true depth) to **100%**. PF-B settled E4's kill condition before any
BO code existed.

### What it means
A generator that accepts 1 in 665 draws is not a generator. Catching it pre-flight saved
the ensemble.

---

# PART 2 — THE FOUR EXPERIMENTS

## E1 — correctness, and the scoring bias it exposed

**Ran:** `scripts/run_e1.py` · `results/e1.log`
**Status:** current

### Why
A sanity bar: on standard functions, BO must beat random search. If it does not, there is
a bug.

### Result
It does. **And it exposed a scoring bias that voided E2's first two runs**: Branin's
BO best-so-far read *better than the true optimum*, because scoring on the observed value
credits an arm for a noise draw.

### What it means
The most valuable thing E1 produced was not its own result but the defect it surfaced in
another experiment. Scoring must read the **noiseless** value at the point the method
selected (Q17).

---

## E2 — sample efficiency. The project's primary experiment.

**Ran:** `scripts/run_e2_shard.py` ×4 then `run_e2.py --merge` · `results/e2.log`,
`results/e2-grid.json` (+ 4 shard files, all committed)
**Status:** current · **two earlier runs void, below**

### Why
The thesis. Seven arms at a budget of 48, on landscapes calibrated to Hall/Ogle, paired
at instance level, n=25.

### What ran
d ∈ {6,8} × σ_rel ∈ {0.10, 0.25}; qLogEI, qLogNEI, random, Sobol, LHS, coordinate
descent, sequential DoE (20+27+1). Registered in `configs/experiment/e2.yaml`.

### Result — d=6, σ=0.25, the registered primary cell
| arm | median regret | vs qLogEI |
|---|---|---|
| **doe** | 0.0957 | **−0.0595** [−0.0792, −0.0373] p<0.0001 |
| lhs | 0.1271 | −0.0282 — **does not survive Holm** (Q39) |
| **qlogei** | 0.1484 | — |
| random | 0.2308 | +0.0664 |

### What it means
**The sequential-DoE pipeline beats qLogEI at the registered primary cell.** qLogEI's only
surviving win in that cell is over random search. The finding is dimension-dependent: BO
wins at d=8.

### Limits
Every arm spends 48 *evaluations*; DoE spends **3 rounds** and BO **10** (Q38). The DoE
arm is d=6 only, so at d=8 BO's strongest opponent was absent.

### VOID RUNS — kept because the reasons are more instructive than most results
- **E2 run 1 — void.** Scored *best true value among visited points*, which credits an
  arm for stumbling onto a recipe it cannot identify. Space-filling arms win by
  construction. The tell was unmissable in hindsight: the static arms came out
  **identical at σ=0.25 and σ=0.10**, i.e. noise-independent.
- **E2 run 2 — void.** The paired opening batch did not exist; the test that promised it
  asserted determinism instead (D6).

---

## E3 — calibration

**Ran:** `scripts/run_e3.py` · `results/e3.log`
**Status:** current

### Result
Coverage is below nominal 0.95 in **every** cell. Latent coverage worst at d=8/σ=0.25
(**0.7644**); adding observation noise recovers predictive coverage to ~0.90–0.92.

### What it means
The interval a lab would actually use is roughly trustworthy. The model's belief about the
underlying smooth response is not.

### Correction recorded
A first draft described the selection effect as uniformly negative. On the full grid it is
negative at two cells, ~zero at one and **positive** at another. The generalisation was
made from one cell.

---

## E4 — extrapolation detection

**Ran:** `scripts/run_e4.py`, `run_e4_robustness.py` · `results/E4-RESULTS-v2.md`
**Status:** **provenance-flagged** — headline disputed, see D-record and Q19

### Result
Pooled over-prediction **+1.103** [+1.024, +1.182] against a response whose maximum is
**1.0**, in 100/100 cells.

### Limits / defects
**D2:** an earlier DoE arm let stage 2 span the whole space, so the predicted optimum
*could not* fall outside it — a reported 0% escape rate that was a tautology.
**Q19:** `E4-RESULTS-v2.md` labels the **pooled** figure "pre-registered primary"; the
pre-registration names a **single cell**, and the two disagree in sign. Unresolved.

---

# PART 3 — THE MECHANISM HUNT (all five refuted)

Every one of these asked "is BO underperforming because of X?" and answered no.

| # | mechanism | file | verdict |
|---|---|---|---|
| Q25 | lengthscale prior | `results/diagnostic-lengthscales.log` | refuted — and produced **D8** |
| Q21 | acquisition solver | `results/e2-determinism.log` | refuted — rate 0.118%, below the registered 1% |
| Q26 | opening batch size | `results/confound-ninit.log` | refuted at the primary cell |
| Q30 | additive kernel | `results/q30-additive.log` | **refuted, and the sharpest of the five** |
| — | Knowledge Gradient | *no committed file* | **not citable** — see below |

## Q30 — the additive kernel. The most informative refutation.

**Status:** current
**Result:** the additive kernel roughly doubled held-out R² and moved regret by
**0.0015, p=0.71**.
**What it means:** **model accuracy is not the constraint.** A surrogate that fits twice
as well recommends no better. This is the single strongest argument that the problem is
the *estimand and the noise ceiling*, not the model.

## Q25 — and the defect it produced

**D8:** the diagnostic anchored its decision rule on the prior **median** (10.08) when the
fit is MAP and its no-data attractor is the prior **mode** (0.5016). The "prior is
dominating" branch was unreachable and the "data is winning" branch was where an untrained
model sits. A conclusion was written and committed from a rule that could return only one
answer. Rebuilt against an empirical permutation null.

## The qKG swap — ⚠️ NOT CITABLE

Run to ~52 rows and abandoned; **`results/exploratory-kg.log` is untracked**. Under this
file's rule 1 it cannot be cited. Either commit the log or drop the claim.

---

# PART 4 — THE ESTIMAND AND ATTRIBUTION WORK

**This is the paper.**

## Q28 — the DoE arm's scoring rule was never registered

**Ran:** `scripts/diagnostic_doe_scoring.py` · `results/doe-scoring.log`
**Status:** **provenance-flagged — computed in B's clone.** Its rule-A figures
(−0.0708 etc.) are not this repository's. Corrected table in `OPEN-QUESTIONS.md`.
**What it means:** every cell reverses sign depending on how the DoE arm is scored, and
the pre-registration never said which. That question became Q41.

## Q29 — the symmetric comparison

**Status:** **superseded by Q34.** Two independent defects: it ran in B's clone against
B's untracked grid, and its two arms used **different locators at a 16× screening-budget
difference** (BO side unseeded).
**What survives, recomputed:** the GP's recommendation beats its own best observation in
all four cells — 0.1232 vs 0.1553, 0.0703 vs 0.0874, 0.1056 vs 0.1247, 0.0876 vs 0.0972.

## Q34 — design versus surrogate. The registered factorial.

**Ran:** `scripts/run_q34_factorial.py --all-cells` · `results/q34-factorial.{log,json}` ·
registered in `a1420d4` **before cells 5 and 6 existed**
**Status:** current

### Why
E2 compares `(structured design + polynomial + rule)` against `(adaptive design + GP +
rule)` — three factors at once — and attributes the reversal to model class. The
experiment could not support that attribution.

### Result
| cell | d=6 σ=.25 | d=8 σ=.25 |
|---|---|---|
| 3 DoE / polynomial | 0.4163 | 0.3766 |
| 4 BO / GP | 0.1232 | 0.1056 |
| **5 DoE / GP** *(new)* | **0.1993** | **0.1139** |
| **6 BO / polynomial** *(new)* | **0.5838** | **0.6972** |

**Registered primary, cell 5 − cell 3: −0.2171** [−0.2524, −0.1834], and −0.16 to −0.29 at
every other cell. **Held.**

### What it means
**It is the model, not the points.** Swapping the surrogate on identical data moves regret
by 0.16–0.29. Swapping the design with the surrogate fixed moves it by 0.00–0.20 — and the
design effect is **null** at d=8 σ=0.25.

**And "BO wins under rule C" collapses.** Combining cell 4 with Q35's constrained DoE
scoring gives **three nulls and one BO win of +0.0153**, against Q29's reported +0.29 to
+0.36.

### Prediction scored — headline right, BOTH specifics wrong
- ✅ cell 5 ≫ cell 3, cell 5 modestly worse than cell 4.
- ❌ **Predicted frequent hard failures for cell 6. Got 0 in 200 runs.**
- ❌ **Predicted BO's clustered points would be ill-conditioned. The opposite** —
  cond(DoE) 8.1e16–1.1e18 (singular), cond(BO) 2.4e2–3.9e3. *You can fit a full
  second-order surface to BO-collected data and you cannot fit one to the DoE arm's own 48
  points.* The pipeline is viable only because it screens to four factors first.

### Limits
The 3−6 contrast confounds design with model dimensionality — addressed in Q45.

## Q35 — the three DoE scorings

**Ran:** `scripts/run_q35_constrained_rsm.py --all-cells` ·
`results/q35-constrained-rsm.{log,json}` · script committed **before** it ran
**Status:** current

### Result — d=6 σ=0.25
best observed **0.0597** · unconstrained argmax **0.4163** · constrained argmax **0.1169**.
`unconstrained − constrained = +0.2995` [+0.2790, +0.3228], p<0.0001, at all four cells.

**The fitted surface is a SADDLE in 200/200 runs.** A saddle has no interior maximum, so
the argmax must reach a boundary — the 100% escape rate is arithmetic. Closed-form ridge
path leaves the design region at radius ≈0.27 against a corner radius of 0.50.

### What it means
**Most of the published failure is a practice failure, not a method failure.** Constraining
the argmax to the region actually explored removes about three quarters of the
recommendation error. The claim narrows to: *unconstrained* polynomial surfaces
extrapolate badly, and the source study used the unconstrained form.

**Residual that must accompany the constrained number wherever it appears:** even
constrained, the recommendation is significantly worse than the arm's own best
measurement — **+0.0572, p<0.0001**.

## Q41 — the estimand decision

**Status:** current · decided by A · `OPEN-QUESTIONS.md`
**Decision:** the **unconstrained argmax is primary**; all three scorings reported in
every table, always. Fidelity to the case study and the estimand argument are each
independently sufficient; the survey evidence only strengthens it.
**Recorded:** reason 3 was **weakened by Task A verification** and rewritten — the 87.61%
figure the brief offered could not be verified and was replaced with the verified 75.29%
saddle figure.

## Q43 — permutation test on the surrogate effect

**Ran:** `scripts/run_q43_attribution.py` · `results/q43-attribution.{log,json}`
**Status:** current

### Result
Observed cell5 − cell3 = **−0.2171**. Sign-flip null over 10,000 permutations:
**+0.00014 ± 0.04676, p = 0.0001, 4.6 SD, and 0 of 10,000 permutations as extreme.**

### What it means
The surrogate effect is not manufactured by some landscapes being easier than others.

### Correction — how the error arose
**My first null was vacuous.** I permuted which polynomial result paired with which GP
result, but `mean(a − perm(b)) = mean(a) − mean(b)` identically — permuting a vector does
not change its mean. The "null" reproduced the observed effect with a standard deviation
of exactly 0.00000. **The tell was the zero.** Replaced with a pairing-sensitive statistic;
the correct reading is that the mean paired difference is *pairing-invariant by
construction*, so the "easier landscapes" objection cannot touch the effect size at all —
only the interval.

## Q44 — design conditioning (D-efficiency)

**Ran:** same script · `results/q43-attribution.log`
**Status:** current — **and it resolves a dispute rather than taking a side**

### Result — four-factor model (p=15), the model stage 2 is built for
| coding | CCD (stage 2) | adaptive (BO) | ratio |
|---|---|---|---|
| common unit cube | 4.99e-3 | 1.05e-2 | **BO 2.1×** |
| each design in its **own** region | 4.58e-2 | 1.05e-2 | **CCD 4.4×** |

Six-factor model: **CCD singular in 50/50 runs, adaptive in 0/50.**

### What it means
**D-efficiency is undefined without stating the region, and the two competing claims in
the record are the same quantity under different codings.** The earlier "adaptive is
1.5–2.9× more efficient" is the common-cube coding; the proposed "correction" to "CCD
7.6×" is the own-region coding. **Neither is simply wrong; replacing one with the other
would have propagated the same category error in the opposite direction.**

The substantive conclusion is unchanged either way: at the model stage 2 is built for, in
the region it occupies, **the CCD is well-conditioned. The polynomial fails on good
geometry.**

### Limits
**The six-factor singularity was found during analysis, not anticipated.** Stated plainly
because a reviewer could otherwise read the conditioning analysis as post-hoc.

## Q45 — the four-factor refit *(registered; result pending)*

**Registered:** `scripts/run_q45_fourfactor_refit.py`, committed before the run, with a
prediction that **disagrees with the close-out brief's**.

---

# PART 5 — GENERALITY, POWER, COST, MULTIPLICITY

## Q42 — five families, four cells. **The main generality experiment.**

**Ran:** `scripts/run_q42_families.py` (4 shards) · `results/q42-families.{log,json}` ·
registered before the run
**Status:** current · **supersedes Q36**

### Result — reversal reproduces in **8 of 14** family-cells
| family | cells | reversal |
|---|---|---|
| **levy** | all 4 | **YES** |
| **rosenbrock** | all 4 | **YES** |
| hartmann6 | both | no — BO wins every rule |
| ackley | all 4 | **VOID** — optimum is the box centre |

**The scoring-convention effect is the universal part**: DoE unconstrained − constrained
is **+0.22 to +0.48** on every family and cell where the surface is a saddle, always
larger than the rule-C gap it modifies. Constrained, rule C is **null at 6 of 8**
Levy/Rosenbrock cells.

Across all 350 runs: **saddle 247, maximum 103**, the maxima concentrated in Ackley.

### What it means
**The "~93% additive, therefore your oracle" objection is answered by data.** Levy and
Rosenbrock are non-additive and multimodal and reproduce the result anyway. The
scoring-convention finding now rests on **four families**.

**"The fitted surface is always a saddle" is FALSE.** Correct conditional: where the
Hessian is indefinite the argmax must reach a boundary and the scoring choice dominates;
where it is negative-definite the choice is worth nothing. Ackley's exact **0.0000** is
the case that proves it.

### Prediction scored — WRONG, in the favourable direction
I registered that it would **not** reproduce cleanly on any family. It reproduces cleanly
on Levy and Rosenbrock at every cell. The secondary prediction (the scoring effect
survives everywhere) held exactly.

### Correction to Q36
Q36 voided only Ackley's **rule A**. Insufficient — its constrained and unconstrained
rule-C figures are identical to four decimals, so rule C carries no information there
either. **Ackley is void under every rule.**

## Q37 — the replay is a power bound

**Ran:** `scripts/run_q37_replay_power.py` · `results/q37-replay-power.{log,json}`
**Status:** current

**MDE 0.68 evaluations at 80% power, both stages.** Stage 1's observed effect (+0.45) is
*smaller than its own MDE*. **P(a top-5 condition is already in the shared 4-point
opening) = 0.64**, and only 4 of 8 evaluations are adaptive.

**Write it as "the head start is bounded below 0.7 evaluations at 80% power", not "BO is
no faster".**

### Two corrections — both made the design look *powerful*
1. A continuous shift on an integer endpoint → MDE 0.10.
2. Imposing the null by `diff − diff.mean()`, which turned every exact tie into +0.025 and
   made all differences positive → MDE 0.03.
**The tell was internal inconsistency, not intuition:** an MDE of 0.03 cannot coexist with
a 95% CI of width 0.9 on the same data.

## Q38 — the cost model

**Ran:** `scripts/run_q38_cost_model.py` · `results/q38-cost-model.log`
**Status:** current

| arm | evals | **rounds** | mean regret |
|---|---|---|---|
| doe | 48 | **3** | 0.0958 |
| lhs | 48 | **1** | 0.1270 |
| coord | 48 | **48** | 0.1420 |
| qlogei | 48 | **10** | 0.1553 |

**Latin hypercube reaches lower regret than qLogEI in one plate.** At equal lab time the
comparison is not 48-vs-48: when DoE finishes its 3 rounds, qLogEI has spent 22 of 48.

**Not claimed:** a regret-versus-rounds *curve* — E2 stored summary rows, not curves. Nor
that q=4 is the right batch width.

## Q39 — multiplicity

**Ran:** `scripts/run_q39_multiplicity.py` · `results/q39-multiplicity.{log,json}`
**Status:** current

Holm over **54** non-primary contrasts. **Five lose significance**, including
**"Latin hypercube beats BO" at the primary cell (p 0.0147 → 0.2356)**. The registered DoE
contrast is exempt and unaffected.

### Correction
My first version said that where an uncorrected CI and a corrected *p* disagree, the
interval governs. **That would undo the correction by the back door** — those intervals are
per-contrast, not simultaneous. Now: intervals carry **magnitude**; the **verdict** outside
registered primaries is the Holm-adjusted *p*.

## Q40 — critical-difference diagrams

**Ran:** `scripts/run_q40_critical_difference.py` · four PNGs in `results/figures/`
**Status:** current

At the primary cell it **independently confirms Q39**: `doe`−`qlogei` = 2.52 > CD 1.80;
`lhs`−`qlogei` = 1.24 < CD.

**Where it disagrees with Q39** (d=8 σ=0.25) the two control different families — Nemenyi
within a cell, Holm across all 54. **Ruling: Holm governs any sentence in the paper;
the diagrams are summary presentation only.**

## Q33 — extrapolation geometry on the published data

**Ran:** `scripts/run_q33_extrapolation.py` · `results/q33-extrapolation.log`
**Status:** current

The polynomial's argmax runs to whatever wall it is given (distance 1.0 at ±2, 4.0 at ±5);
the GP's argmax is **bit-identical at every extension**. Mechanism: the stationary point is
a **saddle** at `fn = +5.76`. Constrained to ±1 the polynomial returns TheO's signature.

**The qualifying check, reported prominently:** LOO RMSE polynomial **1.0720** against a
response sd of **1.0138** — *worse than predicting the mean*; GP 0.9355, better by 7.7%.
**Neither model fits well; the recommendation comparison is between two models that barely
fit.**

**Prediction:** headline held; the specific prediction (both models pushing FN past −1) was
**wrong** — the GP put FN at +0.333.

---

# PART 6 — THE REAL DATA

## Digitization ×2, re-extraction, and the canonical CSVs

**Files:** `data/published/hall_ogle_2025_stage{1,2}.csv`,
`data/published/EXTRACTION_METHOD.md`, `docs/pdf_crosscheck.md`
**Status:** current

Two independent extractions were merged. Three stage-2 medians were corrected (rows that
had read the box's **Q3** rule); one median (`stage2_05`) is **not separable** and ships
empty and flagged — never zero, because zero is a real coded level.

**D11 — the near-miss.** A "correction" to stage1_23 LN511 would have **overwritten a
correct cell**. Reasoning from "the table is the design of record", A inferred the figure
strip must be wrong. The paper prints `+ + + + + -`; the strip was right and the
third-party transcription was the outlier. Caught only by reading a cross-check B had
already written, which says in terms: *"Recorded so nobody 'fixes' a correct cell."*

**Reading error is 4–7% of the between-condition spread against a published per-condition
SEM of 38–66%.** The source assay is the binding constraint by roughly an order of
magnitude — the opposite of the reader's intuition, and both numbers belong side by side.

## The replay — null, and structurally so

**Ran:** `scripts/run_replay_hall_ogle.py` · `results/replay-hall-ogle.log`
**Status:** current · **read with Q37**

Registered as rank recovery with k fixed. Null at both stages. **160 proposals, every one
verified to be a member of the candidate menu.** See Q37 for why the instrument had no
resolution.

---

# PART 7 — LITERATURE FINDINGS

Marked as literature, not experiment. Full detail in `OPEN-QUESTIONS.md` Task A.

| finding | status |
|---|---|
| **Nguyen et al. 2017 is NOT a contrary result** — it concerns the incumbent ξ *inside* the EI acquisition function, not the final recommendation. "Recommend" and "report" do not occur. | ✅ verified from the PDF · **refutes a claim in the close-out brief** |
| **Rummukainen et al. 2024, *Heliyon* 10(2):e24484** — the matched-budget DoE-vs-BO head-to-head. 15 experiments each, **scored on the best condition MEASURED (rule A)**, criterion **not fixed in advance**, BO did not reduce experiment count. | ✅ verified · **the most important citation found** |
| Rummukainen's winner *"had already been found during the first initialization experiment"* | ✅ verified — **independently our Q37 finding, on real data** |
| Gisperg et al. 2025's no-reduction claim is **Rummukainen's**, not theirs; the review identifies **no gap** in how the final condition is scored | ✅ verified — the contribution is not pre-empted |
| 2019 RSM survey: **"more than 75.29% of the models have presented a saddle shape"**, 123 surfaces in 49 papers, IJAMT 2014–2017, manufacturing only | ✅ verified — corroborates Q35's 200/200 saddle on *real published surfaces* |
| Ridge analysis *"does not guarantee the global maximum... for non-spherical designs such as face-centered designs"* — Hall/Ogle used a face-centred CCD | ✅ verified — the textbook safeguard is documented as inadequate for this design class |
| Picheny 2013 compares **ten kriging-based** criteria and **no non-kriging method** | ✅ verified — the DoE-vs-BO gap is real |
| Picheny's infill-vs-identification separation | ⚠️ **NOT verified** — both OA mirrors blocked. **Do not cite it for that distinction yet.** |
| The **87.61%** figure | ⚠️ **NOT verified. Do not use.** |
| Narayanan 2025's "estimated" DoE | ⚠️ **NOT verified** |
| Bull 2011, Berk 2019, Gramacy | ⚠️ **NOT verified** |

---

# PART 8 — THE DEFECT RECORD

Twelve defects, full detail in `RESULTS-PERSON-A.md` §7. **Six share one pattern: a check
whose name carries a guarantee its body does not verify.**

**D12 is the newest and its failure mode is new again.** `results/e2-grid.json` was
gitignored while five scripts and three fidelity gates anchored to it *by path*. Two clones
held two different E2 runs under one filename and **every gate passed in both** — a gate
that compares a regeneration against an untracked file can only report that a clone agrees
with itself. Unlike D1/D2/D3 the check body is *correct*; the defect is in what it points
at.

**Placement in the paper:** one methods paragraph on the *practice* in main text; the
twelve-item inventory in supplementary. An inventory of twelve errors as a reader's first
impression invites the wrong inference from a project that found its own mistakes.

---

# PART 9 — WRONG PREDICTIONS

Kept together because they are the most informative rows in this file.

| # | prediction | outcome |
|---|---|---|
| 1 | Q33: both models would push fibronectin past −1 | **Wrong.** The GP put it at **+0.333**. Reading one top condition as a monotone trend was the error. Headline held. |
| 2 | Q34: cell 6 would fail often, worst at d=8 | **Wrong.** 0 failures in 200 runs. |
| 3 | Q34: BO's clustered points would be ill-conditioned | **Wrong, and backwards.** The DoE design is singular at six factors; the adaptive design is not. |
| 4 | Q42: the reversal would not reproduce cleanly on any family | **Wrong.** Levy and Rosenbrock reproduce it at every cell. |
| 5 | Q37 (twice) | Two power calculations, both making the design look *powerful*. |
| 6 | Q34: the decision rule would pick one of three branches | **Wrong.** The decomposition is cell-dependent — a fourth outcome I had not listed. |

**Correct predictions, for balance:** Q33's headline; Q34's registered primary (all four
cells); Q42's secondary prediction that the scoring effect would survive on every family;
Q35's registered commitment to report all three scorings whichever way it came out.
