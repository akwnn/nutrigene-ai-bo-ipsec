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
3. **Wrong predictions get their own line.** ~~Twelve~~ **Sixteen** registered predictions have been wrong, plus the brief's two.
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
surviving win in that cell is over random search. The finding is dimension-dependent ~~— BO wins at d=8~~.

> 🔵 **CORRECTED.** **BO does not win at d=8.** Q27 ran the d=8 DoE arm and found
> `doe − qlogei = −0.0284` at σ=0.25 — the classical arm ahead, as at d=6, with the margin more
> than halved and the shrinkage itself significant. At σ=0.10 both dimensions tie. The sentence
> predates Q27 and survived because `e2-grid.json` has no d=8 `doe` rows to contradict it (D17).
> **The dimension-dependence is in the size of the gap, not in who wins.**

### The σ_rel = 0.10 cells, all seven arms — the optimistic-assay baseline

Re-aggregated from `results/e2-grid.json` (d=8 `doe` from `results/e2-doe-d8.json`, which
**does** exist — see the D17 correction), paired at instance level, n=25 instances × 2 seeds. Recorded here because the
budget-to-target work (Q52) needs the low-noise cells as its comparison baseline and they
had never been tabulated with paired contrasts.

| | d=6 regret | vs qLogEI | d=8 regret | vs qLogEI |
|---|---|---|---|---|
| qlognei | **0.0808** | −0.0066 [−0.0200, +0.0078] tie | **0.0849** | −0.0123 [−0.0214, −0.0041] **BO worse** |
| qlogei | 0.0874 | — | 0.0972 | — |
| coord | 0.0880 | +0.0006 [−0.0108, +0.0123] tie | 0.1053 | +0.0081 [−0.0047, +0.0215] tie |
| doe | 0.0892 | +0.0018 [−0.0086, +0.0117] tie | 0.0948 ⚠️ | +0.0015 [−0.0103, +0.0140] tie |
| lhs | 0.1027 | +0.0153 [−0.0015, +0.0317] tie | 0.1260 | +0.0288 [+0.0114, +0.0478] BO better |
| sobol | 0.1210 | +0.0336 [+0.0189, +0.0491] BO better | 0.0968 | −0.0004 [−0.0143, +0.0135] tie |
| random | 0.1693 | +0.0819 [+0.0627, +0.1001] BO better | 0.1272 | +0.0301 [+0.0154, +0.0448] BO better |

**At the optimistic noise level the top four arms are indistinguishable at both
dimensions.** qLogEI's only unambiguous wins are over `random` at both dimensions and
`sobol` at d=6; the classical DoE arm ties it at both. **qLogNEI beats qLogEI at d=8** with
an interval clear of zero — the acquisition function, not the paradigm, is what moves at
low noise.

✅ The d=8 `doe` figure has a machine-readable source after all: `results/e2-doe-d8.json`,
committed 2026-08-14. It holds both cells, 50 rows each, 18 fields, and regenerates the log
text exactly (0.0948 at σ=0.10, 0.0963 at σ=0.25). D17 is corrected below.

**No rule C exists for these arms.** `e2-grid.json` stores reported-best only. Per-arm
posterior-mean scoring exists nowhere for the Hill oracle — only for BO vs DoE on the four
external families (Q42) and for Q47's own four arms. A both-rules version of this table
would need a new run fitting a GP per arm per instance.

### Limits
Every arm spends 48 *evaluations*; DoE spends **3 rounds** and BO **10** (Q38). The DoE
arm is d=6 only in `e2-grid.json`, and its d=8 counterpart ran separately.

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
~~**It is the model, not the points.**~~ **QUALIFIED BY Q45 — see below.** Swapping the
surrogate on identical data moves regret by 0.16–0.29. Swapping the design with the
surrogate fixed moves it by 0.00–0.20, and appeared **null** at d=8 σ=0.25. **Q45 shows
that null was partly an artefact of a model-dimensionality confound: with the model held
fixed the design effect is large and significant at all four cells.**

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
measurement — ~~**+0.0572, p<0.0001**~~.

> 🔴 **CORRECTED (D20).** This residual is `constrained − best_observed`, and
> `best_observed` read `DoEResult.curve_true` — **oracle-best, not rule A**. It therefore
> compared a rule-C number against an oracle-best one. Rescored on rule A
> (`results/d20-rescore.json`, fidelity gate |Δ| = 0.0 over all 200 rows):
>
> | cell | as published | corrected |
> |---|---|---|
> | d=6 σ=0.25 | +0.0572 | **+0.0211 [+0.0105, +0.0315]** |
> | d=6 σ=0.10 | +0.0312 | **−0.0036 [−0.0122, +0.0049] NULL** |
> | d=8 σ=0.25 | +0.0573 | **+0.0185 [+0.0094, +0.0287]** |
> | d=8 σ=0.10 | +0.0377 | **−0.0071 [−0.0150, +0.0008] NULL** |
>
> **It survives at the realistic assay at about a third of its published magnitude, and
> is null at both optimistic-assay cells.** Corrected `best_observed` is **0.0958**,
> which now agrees with E2's independently computed rule-A DoE figure of 0.0957 —
> resolving a discrepancy the two documents had been carrying.

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

## Q45 — the four-factor refit. **The design effect is not null.**

**Ran:** `scripts/run_q45_fourfactor_refit.py` · `results/q45-fourfactor-refit.{log,json}` ·
registered before the run with a prediction that disagreed with the brief's
**Status:** current

### Why
Q34's polynomial design contrast compared a four-factor quadratic on DoE data against a
**six**-factor quadratic on BO data — different models. Q44 sharpened it: at six factors
the CCD is singular in 50/50 runs. Refit both on the same four kept factors.

### Result
| | d=6 σ=.25 | d=6 σ=.10 | d=8 σ=.25 | d=8 σ=.10 |
|---|---|---|---|---|
| cell 6, six-factor *(Q34)* | 0.5838 | 0.3956 | 0.6972 | 0.6784 |
| **cell 6, four-factor REFIT** | **0.3035** | **0.1417** | **0.2519** | **0.1435** |
| **3 − 6 · DESIGN, model fixed** | **+0.1129** | **+0.2883** | **+0.1247** | **+0.2669** |
| 4 − 6 · SURROGATE, design fixed | −0.1803 | −0.0715 | −0.1462 | −0.0559 |

All p ≤ 0.0008.

### What it means
**The design effect is real and was hidden behind a model-dimensionality confound.** It is
significant at all four cells and it is *signed*: the DoE design gives a **worse**
polynomial recommendation than the adaptive design using the identical model. At σ=0.10 it
is **4–5× the surrogate effect**.

**Not a contradiction of Q44 — the two together are the point.** The CCD is ~4.4× more
D-efficient *in its own region*, and recommends worse *over the whole range*.
**D-optimality in a small region is not usefulness for a recommendation made outside it.**
Stage 2's quadratic is well determined inside its narrow sub-box and extrapolates badly
beyond it, which is exactly where the recommendation is made. **The DoE arm's design is
not bad; it is well-built for the wrong question.**

**The surrogate effect remains the only one that never reverses.**

### Predictions scored
Mine: **2 of 3.** Right that cell 6 would improve a lot (0.25–0.53) and right that it
would still lose to the GP (−0.056 to −0.180, so better conditioning does not repair
geometry — my registered falsifier did not occur). **Wrong** that the design contrast
would stay subordinate: true at σ=0.25, false at σ=0.10.

**The brief's prediction — that the design null would strengthen — is refuted.**

---

# PART 5 — GENERALITY, POWER, COST, MULTIPLICITY

## Q42 — five families, four cells. **The main generality experiment.**

**Ran:** `scripts/run_q42_families.py` (4 shards) · `results/q42-families.{log,json}` ·
registered before the run
**Status:** current · **supersedes Q36**

### Result — reversal reproduces in **8 of 16** family-cells
| family | cells | reversal |
|---|---|---|
| **levy** | all 4 | **YES** |
| **rosenbrock** | all 4 | **YES** |
| hartmann6 | **all 4** | no — BO wins every rule, at every cell |
| ackley | all 4 | **VOID** — optimum is the box centre |

**Hartmann6 originally ran at 2 of 4 cells and now runs at 4.** It is defined at six
dimensions, so `run_q42_families.py` returned `None` at d=8 and the one family carrying
the generality argument had half the coverage of every other. That was a property of the
function, not a decision — which is why it went unnoticed. `oracles.Embedded` closes it
using the structure the Hill oracle already uses at d=8: a fixed active subspace plus
inert nuisance axes, so the dimension contrast is not confounded with active-count. Six
active coordinates, two inert, active subset from a recorded seed, inert axes **exactly**
inert (asserted as equality over random draws, `tests/test_embedded_oracle.py`).

**Fidelity gate.** The d=6 path is unchanged, so re-running it must regenerate the
committed shard bit-exactly. It does: **50 rows, 14 fields, max |Δ| = 0.0**, checked
against a copy of the committed file rather than against the file the run overwrites —
D12 is the reason that distinction is spelled out.

#### Hartmann6, all four cells (`results/q42-families-rerun.log`)

| cell | BO rule A | DoE rule A | contrast, DoE − BO | rule C constrained |
|---|---|---|---|---|
| d=6 σ=0.25 | **0.2984** | 0.5444 | +0.2460 [+0.1827, +0.3068] | +0.2753 |
| d=6 σ=0.10 | **0.1938** | 0.5398 | +0.3460 [+0.2992, +0.3956] | +0.3483 |
| d=8 σ=0.25 | **0.3134** | 0.6324 | +0.3189 [+0.2450, +0.3888] | +0.3317 |
| d=8 σ=0.10 | **0.2370** | 0.6504 | +0.4134 [+0.3446, +0.4763] | +0.4173 |

All p < 0.0001, all favouring BO. **On a non-additive, deceptive benchmark this project
did not build, BO wins every cell under every scoring rule — including the constrained
rule C built specifically so the classical arm is not a strawman.** The fitted quadratic
is a **saddle in 25/25 runs at all four cells**.

#### 🔴 The screening stage performs at chance on this surface

Every row now records `n_kept_active`: how many of the screen's four slots landed on a
factor that can actually move the response.

| cell | active of total | slots spent on active factors |
|---|---|---|
| d=6 (both σ) | 6 of 6 | 4.00 / 4 |
| d=8 σ=0.25 | 6 of 8 | **2.96 / 4** |
| d=8 σ=0.10 | 6 of 8 | **2.88 / 4** |

With 2 of 8 coordinates inert, **chance alone gives 3.00**. The screen scores 2.96 and
2.88 — and *slightly worse at low noise*, which rules out noise as the cause. **Twenty
runs plus four centre points cannot distinguish a provably null factor from a real one on
this surface.**

That is a mechanism, not just a score. The classical pipeline's disadvantage at d=8 is not
only that its fitted quadratic is a saddle; it is that **the screen feeding that quadratic
is uninformative**, so two of the six factors it passes forward are chosen effectively at
random. `n_keep = 4` is fixed (`doe.py:196`, matching the published 6→4) while Hartmann6
has six active coordinates, so the pipeline must discard real signal at every cell — but
at d=8 it also spends a slot on a coordinate that provably does nothing.

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

~~Seventeen~~ **Twenty** defects (D1–D20); D1–D12 in full detail in `RESULTS-PERSON-A.md` §7. **Six share one pattern: a check
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


### D13–D17, from the threshold work

| # | defect | how it was caught |
|---|---|---|
| **D13** | Q47's pseudo-observation variance used the *unbiased* `resid_var − mean(yvar)`. At σ=0.25 the expensive readout carries more variance than the signal, so the two terms are the same size and the difference **went negative on every draw** — pinning cheap points at the noise floor and telling the model they were exact. | A smoke test: the joint arm scored 0.244 against a 0.100 baseline. Fixed before the grid ran. |
| **D14** | Q47's achieved-ρ guard used a flat ±0.02 tolerance. That is **1.4 SD at ρ=0.30 and 13 SD at ρ=0.95** — it fires on ordinary sampling error where it should not and cannot fire where it should. | It killed the first grid launch three minutes in. Diagnosed by verifying the construction unbiased at two sample sizes *before* touching the tolerance. |
| **D15** | Q47's fixed-calibration arm does **not** isolate `(a, b)`: they are drawn from the generator that then draws the cheap readout's noise, so skipping them diverges every later draw. The arm varies the calibration **and** re-draws the noise. | Found while writing up the sensitivity table. Left in place and reported as such, because `screen`'s provable invariance turns it into a negative control with a known true value of zero. |
| **D16** | **E2's static arms share one design across all 25 instances** (Q48). Every static-arm interval in this project is a within-design interval. | A control arm in a different experiment disagreed with the published number by 0.05. |
| **D17** ✅ **CORRECTED 2026-08-14** | ~~`results/e2-doe-d8.json` **does not exist**~~ — it did exist, on disk, all along. `run_e2_doe_d8.py:257` wrote it; the blanket `results/*` rule in `.gitignore` hid it; nobody force-added it. The original entry was true of the *repository* and false of the *disk*, and no one checked the disk. The file is now committed and un-ignored by an explicit `!results/e2-doe-d8.json` rule. It holds both d=8 cells, 50 rows each, 18 fields, and regenerates the log text exactly. **So the Q27 primary contrast IS re-aggregatable, re-pairable and re-scorable**, contrary to what this row claimed. `scripts/estimand_evaluation.py` now reads it directly. | Found while pulling the σ=0.10 rows for every arm: the arm was simply absent from `e2-grid.json` and the fallback file was not on disk. **A sibling of D12** — that defect was a gate pointing at an untracked file; this is a *number* with no machine-readable file behind it at all. |

### D18–D19, from the budget-to-target grid

| # | defect | how it was caught |
|---|---|---|
| **D18** | **`report()` prints a savings column the registration does not define.** Q52 §2 registers `savings` as a **median** of per-instance ratios; `boec.diagnostics.instance_bootstrap` returns `v.mean()`. The two disagree in *direction* — under the mean there is no inversion at any target, under the median there appears to be one. The printed column must not be quoted until the estimator matches the registration. | Adversarial re-derivation of the printed table from the raw JSON. The harness's own log and the registration had been read as if they computed the same quantity for a full day. |
| **D19** | **A registration binds only the analysis that runs through it.** Q52 §2's gates — >50% censored ⇒ no point estimate, fewer than 13 pairs ⇒ undefined, designated sets only ⇒ no promoting the appendix — were all registered *and correctly implemented in the harness*. The first-pass headline broke all three anyway, because it was computed in an ad-hoc script that reproduced the arithmetic without the gates. | The gates were fine; the path around them was not. Caught before publication by recomputing the headline against the harness's own printed output and finding `undef` where the headline had a number. |

### 🔴 D20 — the DoE arm's rule A is scored **oracle-best**, and in Q42/Q36 the two arms are on different rules

**`DoEResult.curve_true` is `np.maximum.accumulate` over the NOISELESS values** — the
running best *true* value among visited points. That is **oracle-best**, not rule A. Rule
A is the true value at the running *observed* argmax (`diagnostics.reported_best_curve`),
and the distinction is the one that voided E2's first run.

**Three scripts read it as though it were rule A:**

| site | what it feeds |
|---|---|
| `run_q35_constrained_rsm.py:178` | Q35's **"best observed"** column, and therefore **L6** |
| `run_q42_families.py:128` | the DoE arm's rule A on all four external families |
| `run_q36_generality.py:111` | the same, on Hartmann6 and Ackley |

**In Q42 the asymmetry is inside one loop.** Line 115 scores BO with
`reported_best_curve`; line 128 scores DoE with `curve_true[-1]`. **Same cell, same seed,
two different rules — and the difference runs entirely in DoE's favour:**

| family, d=6 σ=0.25, n=10 | oracle-best (as scored) | true rule A | DoE flattered by | unique values / 10 seeds |
|---|---|---|---|---|
| levy | 0.0040, **sd 0.0000** | 0.0454, sd 0.0434 | **+0.0414** | **1 → 7** |
| rosenbrock | 0.0003, **sd 0.0000** | 0.0441, sd 0.0545 | **+0.0438** | **1 → 7** |
| hartmann6 | 0.5597, sd 0.1119 | 0.5775, sd 0.1207 | +0.0177 | 8 → 9 |

**This supersedes the "centre-replicate void" diagnosis.** The zero variance and the
noise-independence on Levy and Rosenbrock are **symptoms of oracle-best scoring**, not an
unfixable property of a centred test function: under oracle-best the arm is credited with
the true value at its best visited point, and a deterministic centre run makes that a
constant. **Scored correctly those cells have ordinary variance (7 distinct values in 10
seeds), so Q42 is recoverable by re-running rather than by retraction.**

**Two consequences, in opposite directions:**
- **Against the DoE-wins reversal.** It was measured with the classical arm flattered by
  **+0.041 to +0.044** on Levy and Rosenbrock — the same order as the contrasts
  themselves. Some of the "reversal reproduces in 8 of 16 family-cells" may not survive.
- **For Hartmann6.** DoE was flattered by **+0.0177** there too, so correcting it
  **widens BO's margin** rather than narrowing it. Q51's result gets stronger.

**Rule C is untouched at every site.** `unconstrained` and `constrained` are computed from
`constrained_argmax` and `truth`, never from `curve_true`, so **Q41's registered primary
estimand and every rule-C figure in this project stand unaffected.**

### ✅ D20 FIXED AND RESCORED — `scripts/rescore_d20.py` · `results/d20-rescore.{json,log}`

All three sites now use `reported_best_curve`. A structural guard
(`tests/test_rule_a_is_not_oracle_best.py`) asserts over the AST that **no script reads
`curve_true`**, with a companion test proving the two scorings actually differ so the
guard cannot go vacuous.

**Only the DoE arm was re-run, and the equivalence is gated rather than asserted.** The
BO arm was always on `reported_best_curve` and its stored numbers cannot have changed;
the DoE arm runs on its own evaluator at the same seed. `doe_c_unconstrained` and
`best_observed`-adjacent columns are untouched by the fix, so they must come back
identical — **worst |Δ| = 0.000e+00 over 400 Q42 rows and 200 Q35 rows.**

**What changed on the external families — the verdicts did not move.**

| cell | DoE as scored | DoE corrected | flattered by | BO | winner |
|---|---|---|---|---|---|
| hartmann6 d=6 σ=0.25 | 0.5444 | 0.5623 | +0.0178 | **0.2984** | **BO, both ways** |
| hartmann6 d=8 σ=0.25 | 0.6324 | 0.6393 | +0.0069 | **0.3134** | **BO, both ways** |
| levy d=6 σ=0.25 | 0.0040 | 0.0392 | +0.0351 | 0.1156 | DoE, both ways |
| rosenbrock d=6 σ=0.25 | 0.0003 | 0.0328 | +0.0325 | 0.0700 | DoE, both ways |

**Reversal count: 12 of 16 family-cells before, 12 of 16 after. No cell flips.** The
qualitative generality result is robust to the bug.

**But the zero-variance signature was entirely the bug.** Distinct DoE values across 25
seeds, before → after: levy **1 → 9/5/12/5**, rosenbrock **1 → 11/8/12/10**, ackley
**1 → 4/2/4/2**. **So the earlier "Levy and Rosenbrock are void, 12 of 16 family-cells
are void not 4" diagnosis is WITHDRAWN** — those cells are legitimately scored once the
arm is on rule A, and Q42 needed a rescore rather than a retraction.

> ⚠️ **L16 needs a smaller correction.** It states Ackley *"scores exactly 0.0000 under
> rule A"* because its optimum sits at the design centre. Under corrected rule A it
> scores **0.0123 (d=6 σ=0.25)**, not 0.0000 — the exact zero was the oracle-best
> artefact. The *reason* to treat centred functions with suspicion survives; the number
> does not.

### 🔴 Q35 rescored — the constrained-vs-best-observed residual loses two of its four cells

| cell | "best observed" as scored | corrected (rule A) | constrained | **residual as published** | **residual corrected** |
|---|---|---|---|---|---|
| d=6 σ=0.25 | 0.0597 | **0.0958** | 0.1169 | +0.0572 | **+0.0211 [+0.0105, +0.0315]** |
| d=6 σ=0.10 | 0.0544 | **0.0892** | 0.0856 | +0.0312 | **−0.0036 [−0.0122, +0.0049] NULL** |
| d=8 σ=0.25 | 0.0575 | **0.0963** | 0.1148 | +0.0573 | **+0.0185 [+0.0094, +0.0287]** |
| d=8 σ=0.10 | 0.0500 | **0.0948** | 0.0877 | +0.0377 | **−0.0071 [−0.0150, +0.0008] NULL** |

The Q35 residual claims *"even constrained, the recommendation is significantly worse than the arm's
own best measurement — +0.0572 / +0.0312 / +0.0573 / +0.0377, all Holm p=0.0000."*
**Corrected: it survives at the realistic noise level at roughly a third of the claimed
magnitude, and is NULL at both optimistic-assay cells.** The claim there was an artefact
of scoring the arm's own data at oracle-best while scoring its recommendation honestly.

*(Note: this is Q35's residual, not `CLAIMS.md`'s L6, which is about acquisition-solver failures.)*

**And that has a consequence for Tier-1 1.3 / Tier-3 3.6.** Those frame the two arms as
failing in opposite directions — *"the polynomial's model is worse than its data, the
GP's model is better than its data."* At σ=0.10, constrained, the polynomial's model is
**no worse than its data either**. The asymmetry is a property of the noisy assay, not a
general one, and must be written that way.

**Corrected `best_observed` now agrees with E2.** 0.0958 against E2's independently
computed rule-A DoE figure of 0.0957 — the two documents had been quoting 0.0597 and
0.0957 for the same quantity, and that discrepancy is now resolved rather than merely
noted.

**The survivorship trap D19 concealed, stated separately because it generalises.**
Arrival is monotone in the target, so complete-case sets across a budget-to-target curve
are **strictly nested**. Reading down such a column looks like a trend and is partly a
change of population: here n fell 25 → 20 → 14 → 7 and the ratio "declined" 6.00 → 2.70 →
2.46 → 1.44, while on a fixed subset it is **flat at 6.00**. Any budget-to-target curve
with censoring must report the fixed-subset version beside the all-pairs one.

**A methodological note, not a code defect.** While reading Q49 I claimed from unpaired
means that quadrupling the budget bought nothing. The paired contrast says it buys +0.038
with a CI clear of zero. The marginal SE at 25 instances is ~0.03 and swamps the effect.
**Comparing two means computed from the same 25 instances throws away the pairing that
makes the effect visible** — the same error class as D-series arithmetic slips, in the
reading rather than in the code.


---

# PART 9 — THE THRESHOLD WORK, AND WHAT IT FOUND IN E2

Three entries, and **two of the three were not asked for.** Q48 and Q49 both came out of
validating a control arm that Q47's brief did not include.

---

## Q47 — the multi-fidelity threshold. `current`

**Files:** `results/q47-multifidelity.log` · `results/q47-analysis.log` ·
`results/q47-multifidelity.json` · `results/q47-prediction.log` ·
registration in `OPEN-QUESTIONS.md` Q47, committed before the experiment existed.

### Why

Not "does multi-fidelity help" — that answer is whatever correlation you assume, and no
correlation is published for endothelial differentiation. Sweep the correlation and the
cost ratio instead, and report where a cheap screening tier stops paying.

### What ran

6,600 runs. 6 correlations × 4 cost ratios × 4 cells, budget 48 expensive-equivalents,
equal total cost asserted per arm per run. Four arms: single-tier LHS+GP at full budget;
a 32-point control buying nothing; screen-then-confirm; and a regression-adjusted
co-kriging joint model. Zero rule-C fit failures in 4,800 fits.

### Result

At the primary cell and φ=1/3, a cheap tier at **10:1 or better** pays from a
lab-measurable correlation of about **0.26–0.32**. Below 5:1 it does not pay at any
correlation. **All three registered predictions were wrong** (Part 10, rows 8–10).

**The largest effect is on neither registered axis.** The budget split φ dominates the
correlation: at cost ratio 5×, φ=0.25 shows no advantage at any ρ while φ=0.5 shows one at
every ρ including 0.30 — same cell, same budget, same cost ratio.

### What it means

The deliverable as specified is under-specified. **The surface is over (ρ, cost ratio, φ),
and φ is the leading term.** The practical question is not *"is my cheap assay correlated
enough"* but *"how much of the budget goes to screening"*.

And the control settles what the gain is made of: cutting 48 expensive points to 32 and
buying nothing costs **nothing measurable in 7 of 8 comparisons**. The two-tier gain is
not "the cheap tier bought more than the points it displaced" — the displaced points were
worth nothing measurable, and the gain comes entirely from screening a larger pool.

### Limits

- **The correlation is assumed, not measured.** No published value exists for endothelial
  differentiation. **That is why this is a threshold and not a result.**
- Every number is at **φ=1/3** except the sensitivity table, and must be quoted with it.
- The **linear-plus-noise cheap readout is a choice**, and it is the same form the joint
  arm's adjustment assumes, so `joint` is graded on a model it is guaranteed to have right.
- `joint`'s pseudo-observation variance is conservative by 2×–20× (D13), which biases
  against it. The registration's "clean upper bound" claim is **withdrawn**.
- The fixed-calibration arm does not isolate `(a, b)` (D15).
- Cost ratios are illustrative. Nothing here says a cheap CD31 readout exists.

---

## Q48 — E2's static arms share one design across all 25 instances. `current` 🔴

**Files:** `results/q48-design-variance.log` · `results/q48-design-variance.json`

### Why

Not planned. Q47's LHS+GP baseline scored 0.1778 at d=6 σ=0.25 where `e2-grid.json`
reports 0.1270 for `lhs`. Same code, same instances, same noise, same scoring rule — only
the design seed differed.

### Result

`runner.static_design` takes no instance argument, so a cell holds **2 designs across all
50 runs, not 50**. Over 60 draws at d=6 σ=0.25: `lhs` design-averaged **0.1752** against
E2's 0.1270, which is the **0th percentile of 60**. `sobol` 0.1777 (40th), `random`
0.1778 (98th).

### What it means

**At 48 points in 6 dimensions, LHS, Sobol and uniform random are indistinguishable** —
design-averaged spread 0.003 against a design SD of 0.025. E2's reported 0.095 spread
between them is which design each one drew.

And `instance_bootstrap` treats the 25 instances as independent when they share a design,
so **the design component of variance is absent from every interval this project reports
for a static arm.**

### Limits

The primary-cell reversal it implies — qLogEI 0.1553 vs `lhs` design-averaged 0.1752, "BO
ahead by 0.020" — is ~~**indicated, not established.**~~ qLogEI's 14-point opening is also
instance-independent and has **not** been design-averaged. Settling it needs qLogEI across
~30 opening seeds. ~~**Not run.**~~ Finding (a) does not depend on that caveat.

> 🔵 **CORRECTED — it was run, as Q50, and the reversal is ESTABLISHED.** 8 of 20 registered
> campaign seeds (scope reduction stated, not silent). The harness reproduces E2's 0.1553 exactly
> on the diagonal where E2 sits. qLogEI design-averaged is **0.1532, SD 0.0082** — it moves
> **−0.002** where `lhs` moves **+0.048**, because only 14 of its 48 points are shared. Paired at
> instance level with both arms design-averaged: **`lhs − qlogei` = +0.0219 [+0.0145, +0.0292]**,
> Wilcoxon **p = 1.8×10⁻⁵**, BO ahead on **21 of 25** instances, surviving Bonferroni over all 39
> of Q39's contrasts — which it *replaces* a member of rather than adds to.
>
> ⚠️ **Q50 has no entry of its own in this file**, which is exactly how this line stayed wrong
> while `CLAIMS.md` L19 already said "ESTABLISHED". `results/q50-qlogei-seedsweep.json` and its 8
> shards are committed; the write-up is the missing piece.

---

## Q49 — the noise threshold curve. `current`

**Files:** `results/q49-noise-threshold.log` · `results/q49-noise-threshold.json`

### Why

The long-outstanding item. Q47's §6 states the noise ceiling as *"above CV ≈ X, no method
finds anything within budget."* Found while chasing Q47's control arm scoring better on a
smaller budget.

### Result

**That sentence is false and must not be written.** Paired at instance level, 48→192
assays helps at every noise level tested including σ_rel=0.50 (+0.0384 at σ=0.25, CI clear
of zero). Only one contrast in the sweep is null.

What is true: oracle-best does not depend on σ at all, so the entire noise effect is the
gap between **finding** a recipe and **identifying** it. At n=192, d=6, that gap is
**30 / 44 / 55 / 60 / 61 / 63 / 68 %** of remaining regret at σ_rel = 0.05 / 0.10 / 0.15 /
0.20 / 0.25 / 0.35 / 0.50.

### What it means

**The threshold is CV ≈ 0.15.** Below it, what you are missing is a recipe you never
tried. Above it, most of what you are missing is a recipe **you already ran and could not
tell was the best one.** So below 0.15 spend on more conditions; above it spend on
identifying the ones you have.

**Composed with Q47:** at equal total cost a 20:1 cheap tier gains +0.0638 where
quadrupling the expensive budget gains +0.0384. A cheap screening tier is worth more than
four times the money. Both say the same thing — the expensive assay's *identification*,
not its coverage, is binding.

### Limits

σ_rel above 0.25 is outside the ensemble's design range. One design family (LHS). **No
replication arm has been run** — the recommendation follows from the size of the gap, not
from a measured replication arm beating a non-replicated one. That arm is Q46's.

---

## Q52 §1 — the floor check that refuted itself. `current` 🔴

**Files:** `results/q52-floor.log` · `results/q52-floor.json` ·
`results/q52-flatten.log` · `results/q52-flatten.json` · `src/boec/identification.py`

### Why

The budget-to-target brief gates its own grid: compute the regret an assay can resolve
first, because a target below that floor makes the curve a measure of censoring rather
than efficiency. Registered before running, per the brief.

### Result

**The floor is not a floor, and finding that out is the result.**

The construction plants the true optimum among `n − 1` space-filling points and scores
normally — so whatever regret survives is identification error, not search failure. It was
registered as a bound no arm could beat. **qLogEI beats it by 2.6×:** 0.049 at n=500
against 0.129 at n=384, d=6 σ_rel=0.25.

Rule A's penalty on a mis-pick is the true value of whichever point won by luck, so the
bound needs the runners-up to be **bad**. Holding the planted optimum, the noise and `n`
fixed and varying only the spread of the competitors: **0.1226 space-filling against
0.0144 clustered, 8.5×**.

**So concentration is protective under rule A, independently of finding a better point.**
An adaptive arm gains twice from concentrating — a better best point, *and* a reported
answer that degrades far less under noise, because every candidate it might mis-pick is
nearly as good as its best.

#### §1.1 — identification error, all four cells

25 instances; 400 noise draws per instance under rule A, 5 under rule C; instance-level
bootstrap. ⚠️ The committed log's column headers read "floor" — that is the pre-refutation
wording, preserved so the numbers stay traceable to the file that produced them. Read them
as the **static arms'** identification penalty.

| n | 24 | 48 | 96 | 192 | 384 |
|---|---|---|---|---|---|
| **d=6 σ=0.10** rule A | **0.0432** | 0.0540 | 0.0593 | 0.0684 | 0.0746 |
| hit rate | 68% | 57% | 43% | 32% | **24%** |
| rule C | 0.0421 | 0.0462 | *0.0692* | 0.0535 | 0.0424 |
| **d=6 σ=0.25** rule A | **0.1219** | 0.1330 | 0.1292 | 0.1291 | 0.1292 |
| hit rate | 34% | 25% | 18% | 12% | **8%** |
| rule C | 0.0924 | 0.0913 | *0.1198* | 0.0781 | 0.0802 |
| **d=8 σ=0.10** rule A | **0.0425** | 0.0562 | 0.0622 | 0.0733 | 0.0718 |
| hit rate | 66% | 56% | 41% | 32% | **23%** |
| rule C | 0.0313 | 0.0516 | *0.0690* | 0.0566 | 0.0528 |
| **d=8 σ=0.25** rule A | **0.1214** | 0.1324 | 0.1270 | 0.1334 | 0.1279 |
| hit rate | 33% | 24% | 17% | 11% | **8%** |
| rule C | 0.0810 | 0.0917 | *0.1061* | 0.0861 | 0.0777 |

*Italicised n=96 values are the unexplained anomaly recorded under Limits.*

**Rule A worsens with budget** — 0.0432 → 0.0746 at d=6 σ=0.10, a 73% degradation, with
intervals that do not overlap ([0.0401, 0.0461] against [0.0716, 0.0776]). Rule C moves the
other way. **At σ=0.25, n=384 the assay names the true optimum in 8% of readouts, on a
point it measured.**

**The values sit below every measured arm at the same cell**, which is the check that they
bound the static arms at all: at d=6 σ=0.25 n=48 the number is 0.1330 against qLogEI's
0.1532 and LHS's 0.1752 (both design-averaged, Q50); at σ=0.10 it is 0.0540 against LHS's
0.1380 (Q49). The headroom is the point — **0.02 at σ=0.25 against 0.084 at σ=0.10**, so at
the primary cell nearly all remaining regret is identification rather than search.

**No conflict with Q49**, where an LHS arm *improves* with budget (0.1778 → 0.1395 at d=6
σ=0.25). That arm must both find and identify, and more points help finding more than they
hurt identifying. This construction removes finding, leaving only the component that
degrades.

#### §1.2 — the curve does not flatten

qLogEI, d=6 σ_rel=0.25, one 500-evaluation campaign per instance scored at **every prefix**
— which is the faithful instrument, because budget-to-target asks about a lab that keeps
going until it arrives and never pre-commits to a budget.

| budget | 24 | 48 | 100 | 150 | 200 | 300 | 400 | 500 |
|---|---|---|---|---|---|---|---|---|
| rule A | 0.1752 | 0.1748 | 0.1408 | 0.0946 | 0.0946 | 0.0946 | 0.0577 | **0.0487** |
| rule C | 0.0659 | 0.1111 | 0.1044 | 0.0764 | 0.0526 | 0.0431 | 0.0608 | **0.0440** |

Paired at instance level against n=100:

| | rule A | rule C |
|---|---|---|
| 100 → 200 | +0.0462 [−0.0243, +0.1434] | **+0.0518 [+0.0109, +0.1065]** |
| 100 → 300 | +0.0462 [−0.0243, +0.1434] | **+0.0613 [+0.0252, +0.1150]** |
| 100 → 500 | **+0.0921 [+0.0340, +0.1502]** | **+0.0604 [+0.0165, +0.1106]** |

**Regret falls 72% from the project's budget of 48 and is still descending at 500.** Rule
A's flat run at n=150–300 is the reported-best curve being a step function — the incumbent
did not change — not evidence of a plateau; it resumes falling by 400.

The registered cap of **200 is therefore a compute limit, not a scientific one**, and every
censored result must be reported beside it.

### What it means

**This is the complement of the finding that `reported_best_curve` exists for.** Under
*oracle*-best, scattering is rewarded because a method is credited for points it could not
identify — that error reversed E2 once already. Under *reported*-best, clustering is
rewarded because mis-identification stops being expensive. Both are properties of the
scoring rule rather than of the optimiser, and the second one is now measured: 8.5×.

It also sharpens Q49. That entry established that above CV ≈ 0.15 most of what an
experimenter is missing is a recipe they already ran and could not identify. Q52 adds the
lever: **you can buy identification back by concentrating**, not only by replicating.

**No target was pruned.** The §1.1 numbers bound the static arms only, and the cap of 200
— not the assay — is what censors the tight targets.

### Limits

The refutation rests on one cell (d=6, σ=0.25) and **4 instances**, stopped early; the
100→500 contrast excludes zero, the 100→200 and 100→300 contrasts under rule A do not, and
nothing rests on them. The 8.5× spread-versus-clustered comparison uses a synthetic
Gaussian cluster, not a real qLogEI design, so it demonstrates the mechanism rather than
measuring its size for any particular arm. Rule A's intervals average 400 noise draws over
a *single* design per instance, so design variance enters only across instances.

**Unexplained and recorded:** rule C's identification error has a local maximum at n=96 in
all four cells (0.0692 / 0.1198 / 0.0690 / 0.1061), intervals non-overlapping with n=192.
Four of four is not sampling error. No explanation established. It changes no decision
here.

---

## Q52 §2 — the budget-to-target grid. **No defined savings curve; one arrival-rate result survives.** `current`

> 🔵 **HEADING CORRECTED.** It read *"The savings ratio inverts between wells and rounds"* — the
> claim this entry's own body **retracts** 130 lines below. A retracted headline left in a section
> heading is the single most quotable thing in the file.

**Ran:** `scripts/run_q52_budget_to_target.py` · `results/q52-budget-to-target.{log,json}`
**Registered:** `df11ad6` (design) → `d86e2c2` (amended: four arms, tie-break, rounds,
censoring rules, P4–P6) → `633e74d` (runner). In that order; timestamps are checkable.
**Status:** current

### What ran

d=6, σ_rel ∈ {0.10, 0.25}, **25 instances**, cap **200**, four arms — `qlogei`,
`doe` (the 48-run pipeline repeated with fresh seeds, keeping the best), `random`,
`spread_gp` (LHS + GP, scored at the posterior-mean argmax). Checkpoints
`8·12·16·20·24·32·48·64·100·150·200`; targets `0.30…0.05` under rule C and
`0.03·0.02·0.01` under rule A, with the full cross product computed and stored.

**Fidelity gate: `max |Δ| = 0.000e+00`** over 10 stored `e2-grid.json` qLogEI rows
re-run at budget 48 (Q50's diagonal check, applied here). Recorded in the artifact.

**This artifact stamps its own provenance** — git SHA, dirty flag, timestamp, argv,
library versions, full config. No other results file in this repo does.

### Result — **under the registered pairings there is no defined savings curve at all**

That is the finding, and it is a null.

| registered pairing | outcome |
|---|---|
| **Rule C at its targets** (0.30…0.05), σ=0.25 | `doe` censored **72 / 80 / 84 / 96 / 96 / 100 %**; n_paired **7, 5, 4, 1, 1, 0**. **Undefined at every target.** |
| **Rule C at its targets**, σ=0.10 | n_paired **9, 5, 3, 2, 1, 1, 1, 0**. **Undefined at every target.** |
| **Rule A at its targets** (0.03/0.02/0.01), both σ | n_paired **0, 0, 0**. **Undefined across its whole length.** |

The classical arm collapses under unconstrained rule C — consistent with Q35's measured
0.4163, which is worse than the *loosest* target in the set — and no arm reaches the
rule-A targets. **The registered analysis therefore produces no savings ratio anywhere.**

### 🔴 RETRACTED BEFORE PUBLICATION — "the savings ratio inverts, crossover at 0.15"

Recorded because the way it failed is more instructive than the number. A first pass
reported a smooth decline `6.00 → 2.70 → 2.46 → 1.44` in evaluations against
`3.00 → 0.95 → 0.71 → 0.39` in rounds, and concluded BO saves wells but loses lab time
below target 0.15. **Four independent things are wrong with it:**

1. **It crosses the registered pairings.** Those targets are rule **C**'s designated set,
   read under rule **A**. The registration says the designated sets are the headline and
   *"the remainder is reported as an appendix and is not eligible to become the
   headline."* This promoted the appendix.
2. **It reports forbidden cells.** At target 0.10 the DoE arm is censored **56%** and
   n_paired is **7**. Both registered gates fire (>50% censored; fewer than 13 pairs) and
   the harness correctly prints `undef` there. The 1.44 and 0.39 came from an ad-hoc
   recomputation that bypassed the gates — and they were the *only* anchor for "every
   target tighter than 0.15."
3. **The decline is survivorship, not tightening.** Arrival is monotone in target, so the
   complete-case sets are strictly **nested**: n falls 25 → 20 → 14 → 7 and the survivors
   are exactly the instances where BO had already arrived at its first checkpoint. Held
   to the fixed 7 instances that pair at every target:

   | target | rounds, all pairs | n | rounds, **fixed 7** | evals, all pairs | evals, **fixed 7** |
   |---|---|---|---|---|---|
   | 0.30 / 0.25 / 0.20 | 3.000 | 25 | 3.000 | 6.00 | 6.00 |
   | **0.15** | **0.950** | 20 | **3.000** | **2.70** | **6.00** |
   | **0.12** | **0.711** | 14 | **3.000** | **2.46** | **6.00** |
   | 0.10 | 0.391 | 7 | 0.391 | 1.44 | 1.44 |

   **On a fixed population the curve is flat, and the crossover does not exist.**
4. **Nothing was significant anyway.** Sign test on rounds at 0.15: **9 instances
   BO-better, 10 DoE-better, 1 tie.** At 0.12: 6 vs 8. Every bootstrap interval at
   0.15/0.12/0.10 covers 1.

**Also caught, and it is a defect in this harness rather than in the result.**
`boec.diagnostics.instance_bootstrap` returns `v.mean()`, but the registration defines
`savings` as a **median** of per-instance ratios. So `report()` prints a centre statistic
the registration does not define, and under the mean there is no inversion at any target.
**Recorded as D18. The printed savings column must not be quoted until the estimator
matches the registration.**

### 🔴 Two things the 6.00× at loose targets is NOT

**It is not adaptivity.** `batch_plan(6, 200)` opens with **14 points**, so at the
checkpoints where BO "arrives" at loose targets — n=8 and n=12 — **qLogEI has made zero
adaptive decisions**; it is a partial Sobol opening. `spread_gp` arrives at 8 as well,
which is the same fact from the other side.

**It is not efficiency, it is granularity.** The classical arm cannot answer before 48
evaluations at all, because a partial pipeline is not the method. 48 ÷ 8 = **6.00** is
therefore the mechanical floor, and every loose-target cell sits exactly on it.

**So the honest reading of the loose end of the curve is: any space-filling design
answers immediately, while the classical pipeline must spend 48 evaluations first.**
It is a statement about the classical pipeline's minimum answerable budget, and about
nothing else. On the fixed subset the ratio never departs from that floor until the
population has shrunk to 7, so **this grid contains no measurement of adaptive
efficiency at all** — the region where adaptivity would show is exactly the region where
censoring removes the evidence.

### ✅ THE ONE RESULT THAT SURVIVES: arrival RATE, and it is noise-dependent

Every problem above comes from conditioning on arrival. **Arrival itself is
unconditioned** — all 25 instances contribute, nothing is selected — so it is the one
quantity this grid measures cleanly. Paired per instance, exact binomial test on the
discordant pairs (McNemar's exact form), rule A.

**Rounds were reconstructed, not logged.** The committed grid stores regret at evaluation
checkpoints only — there is no per-landscape rounds field. Conversion uses the runner's
own `rounds_for` (`scripts/run_q52_budget_to_target.py:96-103`, the same function that
was on disk at artifact SHA `633e74d`), applied *per landscape*, then summarised as a
median over the landscapes that arrived. A median over 13 of 25 is not comparable to a
median over 24 of 25 without the count; the count is in the cell. File:
`results/q52-rounds-to-arrival.json`, produced by `scripts/report_q52_rounds_to_arrival.py`.
No campaign was re-run.

**Batch structure, read from the code that produced the grid, not from memory:**

| arm | opening | after that | partial batch |
|---|---|---|---|
| **qlogei** | 14 (`2d+2` at d=6; `CampaignConfig(..., q=4)`, `n_init` unset) | batches of 4 | mid-batch pays for the whole plate: `1 if n≤14 else 1+ceil((n−14)/4)` |
| **doe** | 20 (screen) | 27 (CCD) + 1 confirm = 3 sequential stages, 48 evals | a partial pipeline is not the method. Stored checkpoints are 48/96/144/192 only. Rounds = 3 per completed pipeline |
| **spread_gp** | a fresh LHS of size n | none — one-shot | 1 round at any n |

Batch structure did not change between runs: one grid, one harness.

**How to read the next table.** Two different bills:

- **Cost = wells** (evaluations). Consumables, staining, cytometer time.
- **Time = rounds** (plate cycles). Each round is a wait: plate, incubate, read, then choose the next batch.

Medians are over the landscapes that arrived, with that count in the cell. A median over 13 of 25 is not the same population as a median over 24 of 25.

| σ | target | BO reaches | BO wells | BO rounds | DoE reaches | DoE wells | DoE rounds | discordant | exact p |
|---|---|---|---|---|---|---|---|---|---|
| **0.10** | **0.10** | **24/25** | **32 (n=24)** | **6 (n=24)** | 13/25 | **48 (n=13)** | **3 (n=13)** | **11 : 0** | **0.0010** |
| 0.10 | 0.08 | 22/25 | 74 (n=22) | 16.5 (n=22) | 13/25 | 96 (n=13) | 6 (n=13) | 10 : 1 | 0.0117 |
| 0.10 | 0.05 | 18/25 | 100 (n=18) | 23 (n=18) | 7/25 | 96 (n=7) | 6 (n=7) | 15 : 4 | 0.0192 |
| 0.10 | 0.12 | 24/25 | 32 (n=24) | 6 (n=24) | 20/25 | 48 (n=20) | 3 (n=20) | 5 : 1 | 0.2188 |
| 0.25 | 0.10 | 14/25 | 82 (n=14) | 18.5 (n=14) | 11/25 | 96 (n=11) | 6 (n=11) | 7 : 4 | 0.5488 |
| 0.25 | 0.08 | 10/25 | 125 (n=10) | 29 (n=10) | 6/25 | 72 (n=6) | 4.5 (n=6) | 7 : 3 | 0.3438 |
| 0.25 | 0.15 | 21/25 | 32 (n=21) | 6 (n=21) | **23/25** | 48 (n=23) | 3 (n=23) | 1 : 3 | 0.6250 |

Half-integers are the average of the two middle landscapes when the arrival count is even. DoE itself only ever spends 48/96/144/192 wells and 3/6/9/12 rounds.

**Headline row, σ=0.10, target=0.10.** BO reaches a regret of 0.10 on **24 of 25**
landscapes; DoE on **13 of 25**; discordant **11 : 0**, exact p = **0.0010** (survives Holm
over ten tests).

| | reaches | **cost (wells)** | **time (rounds)** |
|---|---|---|---|
| BO | 24/25 | **32** | **6** |
| DoE | 13/25 | **48** | **3** |
| spread_gp | 24/25 | **32** | **1** |

Among the 13 landscapes both BO and DoE reached: BO used fewer wells in **9**, DoE in 4; DoE used fewer rounds in **8**, BO in 5.

**BO arrives more often, cheaper in wells, slower in rounds.** All three facts belong together. The rate advantage is "got there at all within the cap." The cost advantage is "fewer wells among those who arrived." The time disadvantage is "more plate cycles among those who arrived." At the realistic assay (σ=0.25) there is still no arrival-rate difference at any target (every p > 0.34); where both medians exist, BO is again cheaper-or-similar in wells and slower in rounds, except target 0.08 where the DoE median is 72 wells against BO's 125 — that cell is 10 and 6 arrivals, do not over-read it.

The same reconstruction for **spread_gp**, which is 1 round by construction. Wells still depend on how large a one-shot design first hit the target:

| σ | target | spread_gp reaches | wells | rounds | DoE reaches | DoE wells | DoE rounds | discordant vs DoE | exact p |
|---|---|---|---|---|---|---|---|---|---|
| **0.10** | **0.10** | **24/25** | **32 (n=24)** | **1** | 13/25 | 48 (n=13) | 3 (n=13) | 12 : 1 | 0.0034 |
| 0.10 | 0.08 | 23/25 | 32 (n=23) | 1 | 13/25 | 96 (n=13) | 6 (n=13) | 11 : 1 | 0.0063 |
| 0.10 | 0.05 | 16/25 | 48 (n=16) | 1 | 7/25 | 96 (n=7) | 6 (n=7) | 12 : 3 | 0.0352 |
| 0.10 | 0.12 | 25/25 | 20 (n=25) | 1 | 20/25 | 48 (n=20) | 3 (n=20) | 5 : 0 | 0.0625 |
| 0.25 | 0.10 | 21/25 | 48 (n=21) | 1 | 11/25 | 96 (n=11) | 6 (n=11) | 12 : 2 | 0.0129 |
| 0.25 | 0.08 | 17/25 | 48 (n=17) | 1 | 6/25 | 72 (n=6) | 4.5 (n=6) | 13 : 2 | 0.0074 |
| 0.25 | 0.15 | 25/25 | 20 (n=25) | 1 | 23/25 | 48 (n=23) | 3 (n=23) | 2 : 0 | 0.5000 |

At the headline cell spread_gp matches qLogEI's 24/25 arrivals and the same 32-well median, and does it in **1 round against 6**. That is the comparison the one-shot arm exists for: same cost, much less calendar time. These spread_gp-vs-DoE p-values are not in the original Holm family of ten BO-vs-DoE tests; they are reported, not promoted.

> **The sentence that survives, with cost and time attached:** at a quiet assay BO gets there far more often (24/25 vs 13/25). The typical arrival costs **32 wells against DoE's 48**, and **6 plate cycles against DoE's 3**. A one-shot spread+GP matches that arrival rate and well count in **1 cycle**. The difference in *who arrives* vanishes at the noise this project registered as primary. The *time* difference does not favour sequential BO at either noise level.

The cost-curve page (`results/figures/cost-curves.html`, from
`scripts/make_cost_curve_page.py`) is a different cut of the same grid: median *regret*
against wells and against rounds, not wells/rounds-to-first-arrival. Do not quote one as the other.

### The DoE arm collapses under unconstrained rule C

Under rule C with the classical recommendation at the unconstrained argmax — Q41's
primary — `doe` is censored **64–100% at every target including the loosest (0.30)**, so
**the rule-C savings ratio is undefined across the entire curve at both noise levels.**
This is consistent with Q35's measured unconstrained regret of 0.4163, which is worse
than the loosest target in the set. Scored constrained, `doe(con)` arrives at 48
consistently.

### Predictions scored

| # | prediction | outcome |
|---|---|---|
| **brief** | at σ=0.25 no arm reaches the tighter targets, ratios undefined across most of the curve; at σ=0.10 BO reaches targets in fewer evaluations under the posterior-mean rule | **Clause 1 HELD.** **Clause 2 UNTESTABLE as written** — the posterior-mean comparator never arrives, so the quantity it names does not exist. |
| **P4** | rule-A tight targets censored almost everywhere; rule-A savings undefined across its whole length | **Clause 1 HELD** — 0.03/0.02/0.01 are >50% censored for every arm at both σ. **Clause 2 REFUTED** — savings is defined at 5–6 of 11 targets. |
| **P5** | rule-C savings > 1 at every target, largely granularity at loose targets; falsified above 48/24 = 2.0 | **REFUTED, and my stated floor was wrong twice over.** The ratio is *undefined* at every target, not > 1. And the mechanical floor is **48/8 = 6.00**, not 48/24 — I derived it from §1.2's coarse grid, which could not resolve BO's arrival below 24. The *substance* of the warning held, and it held harder than registered: the loose-target number is granularity, and BO is not even adaptive there. |
| **P6** | savings grow as σ falls | **UNTESTABLE.** It compares two savings curves, and under the registered pairings neither exists. The σ contrast quoted in the first pass (4.00 vs 2.70 at 0.15) came from the same appendix-promotion and survivorship that sank the crossover claim. |

**All four registered predictions failed, at least in part — and P6 could not be tested at
all. That is sixteen wrong predictions in this project, plus the brief's two.**

**The sharpest lesson is procedural, not statistical.** Every gate this experiment needed
was registered in advance and implemented correctly in the harness — the >50% censoring
rule, the 13-pair minimum, the designated-headline rule. The first-pass headline broke
all three, not by disabling them, but by **recomputing the numbers in an ad-hoc script
that did not carry them**. A registration only binds the analysis that runs through it.

### Limits

- **The `doe` arm never moves its design region.** It repeats a fixed pipeline; classical
  sequential RSM inserts a steepest-ascent phase (L10). **This curve understates DoE, and
  every savings ratio in it is biased in BO's favour.** Conceded in the registration, not
  after the numbers.
- **Each row is a different subset of instances.** n falls 25 → 3 as the target tightens,
  so the trend down the evaluations column is partly survivorship. The arrival-rate table
  above is the unconditioned view and should be read first.
- One campaign seed per instance, where E2 used two.
- d=8 not run — declared out of scope, not attempted and dropped.

---

## Q53 — spread_gp on the external families. **It ties on smooth landscapes and loses on deceptive ones.** `current`

**Ran:** `scripts/run_q53_spread_gp_families.py` (4 shards + `--merge`) ·
`results/q53-spread-gp-families.json` · **registered `73d2361` before the runner existed**
(`9c7a081`); the timestamps are checkable.
**Status:** current

### Why

`docs/INFORMATION-MATRIX.md` found `spread_gp` — one-shot LHS, one GP fit, scored at the
posterior-mean argmax — **indistinguishable from qLogEI on the Hill family** under both rules at
both noise levels, **in 1 round against 10**. It also found the arm had run on *nothing but Hill*.
A method claim resting on the one landscape family this project built is the weakest possible
evidence, so Q53 puts it on Q42's four external families at all sixteen cells.

### Result — the reversal is landscape-shaped, and the shape is legible

| family | rule A | rule C | verdict |
|---|---|---|---|
| **hartmann6** (deceptive, 6 local optima) | **+0.17 to +0.28**, all p_holm ≤ 0.0004 | **+0.16 to +0.23**, all p_holm ≤ 0.0047 | **spread_gp LOSES, every cell, both rules** |
| **ackley** (multimodal, near-flat basin) | **+0.13 to +0.29**, all p_holm ≤ 0.0016 | +0.05 to +0.23, 2 of 4 significant | **spread_gp LOSES on rule A, every cell** |
| **levy** | −0.006 to +0.026, **all p_holm ≥ 0.09** | −0.000 to +0.010, all p_holm = 1.0000 | **TIE — all 8 contrasts within design noise** |
| **rosenbrock** | +0.002 to +0.024, **all p_holm ≥ 0.09** | −0.010 to +0.012, all p_holm ≥ 0.47 | **TIE — all 8 contrasts within design noise** |

**With Hill, that is three families where a one-shot spread ties adaptive search and two where it
is beaten decisively.** The dividing line is not dimension and not noise — every family was run at
both — it is whether the landscape is **deceptive**. Hartmann6 has six local optima; Ackley is a
needle in a near-flat basin. Levy, Rosenbrock and the Hill oracle are broadly unimodal along the
coordinates that matter.

> **The claim that survives:** *on smooth, coordinate-wise-unimodal landscapes a one-shot
> space-filling design scored at its GP's posterior-mean argmax matches ten rounds of qLogEI at
> equal evaluations, and does it in one round. On deceptive landscapes it does not, and the gap is
> large.* **Adaptivity buys deception-handling, not sample efficiency per se.**

### The design lottery is 6× worse on the hard families, and that is a finding

`spread_gp`'s design SD, averaged over 5 draws per seed:

| family | rule A design SD |
|---|---|
| hill (Q47 vs Q52, 1 draw each) | ~0.025 |
| levy / rosenbrock | 0.029 – 0.055 |
| ackley | 0.033 – 0.049 |
| **hartmann6** | **0.140 – 0.153** |

**On Hartmann6 a single LHS draw moves the answer by ±0.15** — over half the entire
`spread_gp − qlogei` gap. Registering 5 draws per seed (Q53 §3) was not caution, it was necessary:
a single-draw run would have produced a number with no defensible precision. This is Q48/D16 a
third time, and it is worst exactly where the method is worst.

### The registered stopping rule fired, and it cost two Hartmann6 cells

Q53 §3 registered, before any number existed, that **a contrast smaller in magnitude than its
cell's design SD is reported as *within design noise* and is not called a result.** It fires at
**10 of 32 contrasts** — all 16 Levy/Rosenbrock cells (correctly: they are ties), and **two
Hartmann6 rule-C cells** (d=6 σ=0.25, +0.1711 against SD 0.1913; d=8 σ=0.25, +0.1594 against
0.1756) **despite p_holm = 0.0022 and 0.0047**.

**The rule is conservative by construction** — it compares an effect size to a *dispersion*, not
to a standard error, and the mean of 25 seeds has a far smaller SE than one draw's SD. It is
applied as registered rather than relaxed after the fact. The prediction is scored on the eight
contrasts as a set; the direction at those two cells is the predicted one.

### Prediction scored — **HELD, 8 of 8**

Registered: *"spread_gp loses to qLogEI on Hartmann6, at both dimensions and both noise levels,
under both scoring rules."* **It does, at all eight contrasts, every CI clear of zero, every
Holm-adjusted p ≤ 0.0047.** The falsifier — a tie or a win on Hartmann6, which would have made the
*Hill* result the suspicious one — did not fire.

**This is the first correct headline prediction in this project since Q42's secondary.** Sixteen
have been wrong. Recorded with the same prominence the wrong ones get.

The secondary registration was that **Levy, Rosenbrock and Ackley were unpredicted**. Ackley
resolved with `spread_gp` losing on rule A at every cell; Levy and Rosenbrock tie. Registering
them as unpredicted was right — two outcomes, and neither was guessable from Hartmann6.

### Against the classical arm

D20-corrected DoE rule A (`results/d20-rescore.json`; `q42-families.json` still carries the
superseded column on disk — see Limits). `spread_gp` **beats DoE on Hartmann6** (−0.06 to −0.15
rule A, −0.42 to −0.50 rule C) and **loses to it on Levy, Rosenbrock and Ackley under rule A**
while **beating it under unconstrained rule C on all three** (−0.22 to −0.48). The classical
arm's rule-A advantage on those families is the same centre-run and best-observed effect Q42
documents; its rule-C collapse is the saddle.

### Limits

- **Hill's `spread_gp` numbers are single-draw and Q53's are 5-draw averages.** The Hill tie
  therefore rests on weaker footing than the external ties do. It should be re-run at D=5 before
  the three-family tie is stated as one finding.
- **`results/q42-families.json` still holds the pre-D20 `doe_a` column.** The analysis reads the
  correction from `d20-rescore.json` and **refuses to fall back**; anything else recomputing from
  the shard directly will reproduce the bug. Ackley scoring exactly 0.0000 is the tell.
- **n = 25 seeds on single functions, not 25 landscapes.** Q42's convention, stated in the
  registration; calling it n=25 landscapes would be the pseudo-replication this project criticises.
- **Ackley is reported here, not voided.** Q42 voids its rule A because every CCD carries centre
  runs and Ackley's optimum is the box centre; neither `spread_gp` nor `qlogei` has that
  guarantee. Declared in the registration, before the numbers.
- Fidelity gate passed at **0.000e+00** on 8 stored Q42 rows — but all 8 sampled rows landed on
  **Ackley**, spanning four cells and one family. A weakness of the gate's sampling, not of the
  comparator.

---

# PART 10 — WRONG PREDICTIONS

Kept together because they are the most informative rows in this file.

| # | prediction | outcome |
|---|---|---|
| 1 | Q33: both models would push fibronectin past −1 | **Wrong.** The GP put it at **+0.333**. Reading one top condition as a monotone trend was the error. Headline held. |
| 2 | Q34: cell 6 would fail often, worst at d=8 | **Wrong.** 0 failures in 200 runs. |
| 3 | Q34: BO's clustered points would be ill-conditioned | **Wrong, and backwards.** The DoE design is singular at six factors; the adaptive design is not. |
| 4 | Q42: the reversal would not reproduce cleanly on any family | **Wrong.** Levy and Rosenbrock reproduce it at every cell. |
| 11 | Hartmann6 at d=8: the screen would spend ≥3.5 of 4 slots on genuinely active factors, since inert axes have exactly zero main effect | **Wrong, and it is the most informative number in that run.** 2.96 and 2.88 of 4 — **chance is 3.00**. Worse at *low* noise, so not a noise limit. The screening stage is uninformative on this surface. |
| 12 | Q52 §1.1: a design that has already visited the optimum cannot be beaten by one that must find it, so planting it gives a universal lower bound on rule A regret | **Wrong, and refuted the same afternoon by the very next run.** qLogEI reports 0.049 where the construction claims 0.129. Rule A's cost on a mis-pick is the value of whichever point won by luck, so the bound needs *bad runners-up* — the opposite of what a good optimiser produces. Clustering the competitors and changing nothing else drops the number 8.5×. The registered number bounds the **static** arms only. |
| 5 | Q37 (twice) | Two power calculations, both making the design look *powerful*. |
| 6 | Q34: the decision rule would pick one of three branches | **Wrong.** The decomposition is cell-dependent — a fourth outcome I had not listed. |
| 7 | Q45: the design contrast would stay subordinate to the surrogate effect | **Wrong at σ=0.10**, where it is 4–5× larger. Right at σ=0.25. |
| 8 | Q47 P1: no correlation threshold — two-tier pays at ρ=0.30 for every cost ratio ≥5 | **Wrong.** It pays at ρ=0.30 in 5 of 12 such cells. There is a threshold and it moves with the cost ratio. |
| 9 | Q47 P2: the benefit is non-monotone in ρ at σ=0.10, declining at 0.95 | **Wrong.** It rises in 6 of 8 combinations. Registered at low confidence, and that was warranted. |
| 10 | Q47 P3: two-tier does worse under rule C, because the top-k design is clustered | **Wrong as a directional claim** — 4 cells lower, 4 higher, 8 equal. At d=6 alone it looked systematic; the completed grid does not support it. |
| — | *the close-out brief's* prediction that Q45 would strengthen the design null | **Refuted.** The design effect is large and significant at all four cells. |

**~~Twelve~~ Sixteen wrong predictions now, plus the brief's two.** The twelve numbered above, plus Q52 §2's four (the brief's clause 2, P4, P5, P6) recorded in that entry rather than here. Q47 is the sharpest case: its prediction was a *committed computation* rather than a hunch — a Gaussian order-statistic proxy, run and committed before the experiment existed. It got the effect sizes roughly right and the **detectability** wrong, because it had no instance-to-instance variance and so could not know which effects would clear an n=25 interval. A more precise prediction failed in a more informative way.

**Correct predictions, for balance:** **Q53's primary — the first correct *headline* prediction in the project: `spread_gp` loses to qLogEI on Hartmann6 at all four cells under both rules, 8 of 8 contrasts, every Holm-adjusted p ≤ 0.0047, with the falsifier not firing**; Q33's headline; Q34's registered primary (all four
cells); Q42's secondary prediction that the scoring effect would survive on every family;
Q35's registered commitment to report all three scorings whichever way it came out; and Q47's registered statement that a two-tier arm losing above the expensive readout's own correlation would be a harness bug — it never lost there; and Hartmann6 at d=8, where the reversal was predicted not to reproduce and BO's margin was predicted to widen — both held (+0.246 → +0.319 at σ=0.25, +0.346 → +0.413 at σ=0.10).

---

## Q55 — oracle-best beside rule A, both arms. **Most of the classical arm's headline lead is identification, not search.** `current`

**Ran:** `scripts/rescore_oracle_best.py` · `results/q55-oracle-best.json` ·
Prompt 2 of `docs/PROMPTS-NEXT.md`, registered before the script existed.
**Status:** current

### Why

Every headline in this project reports **rule A**: locate by the noisy reading, score the truth
there. A second quantity — **oracle-best**, the truth at the best well the campaign actually
*ran* — did not exist anywhere on disk for BO, because `e2-grid.json` stores one `regret` per row
and nothing else. Without it, "DoE tested better conditions" and "researchers using DoE picked a
better well" could not be told apart, and §7 of the manuscript listed *"BO R_search is not stored,
so search versus identification is unseparated"* as a make-or-break gap.

Q49's 61% identification share is LHS at n=192, not the E2 BO campaign, so it could not be
substituted. The column had to be regenerated: 200 BO campaigns and 200 classical pipelines.

### The gate came first

The published rule-A column reproduced **per row at |Δ| = 0.000e+00 for all 200 BO and all 200 DoE
rows**, and all twelve published cell means reproduced to 5e-05. Only then was the new column
beside it read. Prompt 2 §3: *"If the gate fails, the campaign is not reproduced and the new column
is worthless."*

### Result — both arms are far better than they can tell, and BO more so

| cell | BO rule A | BO oracle-best | BO gap | DoE rule A | DoE oracle-best | DoE gap | BO id% | DoE id% |
|---|---|---|---|---|---|---|---|---|
| d=6 σ=0.25 | 0.1553 | 0.0755 | **+0.0797** | 0.0958 | 0.0597 | +0.0361 | 8% | 12% |
| d=6 σ=0.10 | 0.0874 | 0.0496 | +0.0378 | 0.0892 | 0.0544 | +0.0348 | 18% | 16% |
| d=8 σ=0.25 | 0.1247 | 0.0702 | +0.0545 | 0.0963 | 0.0575 | +0.0388 | 12% | 14% |
| d=8 σ=0.10 | 0.0972 | 0.0653 | +0.0319 | 0.0948 | 0.0500 | +0.0448 | 14% | **2%** |

`id%` is how often the noisy argmax **is** the true argmax among visited points. It is between
**2% and 18%**. Neither arm can identify its own best well, and the identification gap
(+0.032 to +0.080 regret) is of the same order as every between-arm contrast this project reports.

> **The estimand distinction is not pedantry.** At the primary cell the two locators are 0.0797
> apart on the same 48 wells of the same campaign. Any sentence equating "best observed" with "the
> best point evaluated" is false by that margin.

### The headline: 73% of the classical arm's lead is the assay, not the search

| cell | rule A (DoE−BO) | oracle-best (DoE−BO) | same sign? | share of the lead that is identification |
|---|---|---|---|---|
| d=6 σ=0.25 | **−0.0595** [−0.0797,−0.0375] p=0.0000 | **−0.0158** [−0.0257,−0.0062] p=0.0067 | yes | **73%** |
| d=6 σ=0.10 | +0.0018 [−0.0086,+0.0117] p=0.6915 | +0.0048 [−0.0030,+0.0131] p=0.2872 | yes | — (null both) |
| d=8 σ=0.25 | **−0.0284** [−0.0447,−0.0139] p=0.0023 | −0.0127 [−0.0251,−0.0008] p=0.0588 | yes | **55%** |
| d=8 σ=0.10 | −0.0024 [−0.0095,+0.0053] p=0.4261 | **−0.0153** [−0.0254,−0.0059] p=0.0056 | yes | — (see below) |

**The sign never flips.** Prompt 2 §7 asked for both to be written if they disagreed in sign; they
do not, so the licensed sentences are:

* *"Researchers using DoE selected a better well from the noisy readings"* — **true at both σ=0.25
  cells**, and it is the existing headline.
* *"DoE tested better conditions"* — **also true**, at d=6 σ=0.25, d=8 σ=0.10, and marginally at
  d=8 σ=0.25 — but **at roughly a quarter to a half of the magnitude.** At the primary cell the
  classical arm's advantage shrinks from 0.0595 to 0.0158 once both arms are scored on what they
  actually ran.

~~**d=8 σ=0.10 is the interesting cell and it runs the other way.** Rule A is null there (p=0.4261)
while oracle-best is clearly negative (−0.0153, p=0.0056): the classical arm **tested materially
better conditions and the noisy readout hid it entirely**.~~

> 🔴 **STRUCK by Q57.** That contrast is **null against qLogNEI** (−0.0064, p = 0.5602). It was a
> property of qLogEI's search, not of the classical design, and it must not be quoted. The
> identification rate at that cell really is **2%**, the worst in the grid, and that part stands —
> it is a statement about the readout, not about the contrast. Struck rather than deleted so the
> retraction is visible.

### BO's identification problem is significantly worse than DoE's, except where it is better

The paired difference of the two gaps, per landscape:

| cell | BO gap − DoE gap | p |
|---|---|---|
| d=6 σ=0.25 | **+0.0436** [+0.0224,+0.0635] | 0.0004 |
| d=6 σ=0.10 | +0.0029 [−0.0077,+0.0136] | 0.7310 |
| d=8 σ=0.25 | **+0.0157** [+0.0022,+0.0297] | 0.0451 |
| d=8 σ=0.10 | **−0.0129** [−0.0228,−0.0029] | 0.0422 |

This is the mechanism, and it is the one a replicated design predicts. BO concentrates its wells
where values are near-optimal and differences are within noise, so its noisy argmax is a lottery
among near-ties; the CCD replicates its centre and spreads its remaining points, so its argmax is
better determined. **It reverses at d=8 σ=0.10**, and that cell is not explained here.

### What this does not license

Nothing about which method a lab should use. It re-attributes an existing result: the classical
arm's rule-A advantage is mostly a statement about **selecting from noisy readings**, and only
partly about **where the campaign looked.** A lab that carries forward replicates, or a confirmation
run, or a posterior mean — rather than a single noisy argmax — is not operating under rule A at all.

---

## Q56 — `doe_ascent`, the classical arm allowed to walk. **It erases BO's rule-A arrival advantage and produces this project's first defined savings ratios.** `current`

**Ran:** `scripts/run_q56_doe_ascent.py` · `results/q56-doe-ascent.json` ·
new module `src/boec/sequential_rsm.py`, 19 tests in `tests/test_sequential_rsm.py` written first.
Prompt 1 of `docs/PROMPTS-NEXT.md`.
**Status:** current

### Why

Every cost curve in this project carries a concession registered before its numbers landed:
*"biased in favour of BO, because the classical arm has no steepest ascent."* `doe_repeat` runs the
same 48-well pipeline four times with fresh seeds and **never moves its design region**, while
qLogEI re-aims after every batch of four. Until an arm existed that was allowed to walk, *"BO
reaches quality targets in fewer experiments"* was not a claim this project could make.

`boec.sequential_rsm` is the textbook Box–Wilson arm: screen, CCD, classify the stationary point,
step along the steepest-ascent path, relocate the centre to the best measured point on it, rebuild
the CCD there, repeat. `doe_repeat` is **kept** — the contrast *ascent versus repeated CCD* is the
point.

### It genuinely walks

| σ | cycles | wells spent | relocations | converged early | fitted surface |
|---|---|---|---|---|---|
| 0.25 | 4.0 (1–5) | 151/200 | 3.4 | 54% | 8 maximum, **191 saddle** |
| 0.10 | 3.1 (1–5) | 120/200 | 2.3 | 84% | 40 maximum, 115 saddle |

The saddle count is Q35's finding reproduced on a moving design: the fitted quadratic almost never
has an interior maximum, which is exactly the condition that makes relocation the correct move
rather than an optional refinement.

### Result 1 — on rule A, letting the design walk closes the gap with BO

**No rule-A arrival contrast survives Holm over all 26 tests, and only one survives within the
rule-A family of ten** — σ=0.10 at the tightest target τ=0.05, where qLogEI still wins 18/25 to
6/25 (p_holm 0.0418). Everywhere else the two arms are indistinguishable: 21/25 against 21/25 at
σ=0.25 τ=0.15, paired savings **0.95 [0.56, 1.38]**; 24/25 against 25/25 at σ=0.10 τ=0.15.

**All four defined rule-A savings ratios have intervals covering 1.0** (0.95, 0.73, 0.86, 1.02),
so on the estimand a researcher actually uses there is no detectable well-count saving in either
direction.

**Q52's single surviving arrival result does not survive this arm.** Q52 reported σ=0.10, rule A,
τ=0.10 — BO 24/25 against `doe_repeat` 13/25, eleven discordant to nil, the only cell surviving
Holm over ten tests, and the sentence the cost-curve figure headlines. Against `doe_ascent` the
same cell is **16/25 against 24/25, eight discordant to nil, raw p = 0.0078, Holm 0.0938 over 26
tests and 0.0703 within the rule-A family of ten.** The within-family figure is the like-for-like
comparison against Q52, which corrected over ten; **the result fails at either correction.**

> **The concession was load-bearing.** *"At a quiet assay, BO gets there at all, far more often"*
> was a property of a classical arm that was not allowed to move. It does not survive one that is.

### Result 2 — on rule C, BO still wins decisively, but ascent transforms the classical arm

| σ=0.10, rule C | ascent | qLogEI | repeat |
|---|---|---|---|
| τ=0.30 | **21/25** | 25/25 | 9/25 |
| τ=0.25 | **17/25** | 25/25 | 5/25 |
| τ=0.20 | **15/25** | 25/25 | 3/25 |
| τ=0.15 | **13/25** | 25/25 | 2/25 |

Relocation roughly **triples to sextuples** the classical arm's chance of ever producing a
recommendation that good. It still loses to qLogEI at every one of those targets. At σ=0.25 rule C
the classical arm remains near-hopeless under either policy (0–8 of 25), consistent with Q52's
unconstrained rule-C regret of 0.4163.

### Result 3 — the first defined savings ratios in this project

Q52 could not compute a single fold-saving on rule C: `doe_repeat` was censored above 50%
everywhere, and the registered rule forbids a point estimate there. `doe_ascent` arrives often
enough at σ=0.10 that four cells are finally **defined**:

| σ=0.10, rule C | qLogEI wells / doe_ascent wells | n pairs |
|---|---|---|
| τ=0.30 | **0.10** [0.09, 0.11] | 21 |
| τ=0.25 | **0.09** [0.08, 0.10] | 17 |
| τ=0.20 | **0.15** [0.09, 0.25] | 15 |
| τ=0.15 | **0.23** [0.11, 0.42] | 13 |

**Read these with the granularity caveat, not past it.** `doe_ascent` cannot answer *at all* before
53 wells — a screen plus a complete CCD plus one confirmation — whereas qLogEI has a posterior after
its 14-point opening. At loose targets the ratio is therefore dominated by *when each arm can first
speak*, not by adaptivity. That is a real property of the classical pipeline, and it is the honest
reading of a 10× number that would otherwise look like a search-efficiency claim. On **rule A**,
where the classical arm is competitive, every defined ratio is **0.73 to 1.02 — that is, no saving
at all.**

### The ascent rule is load-bearing, and it is declared rather than absorbed

Prompt 1 words the stopping rule as *"step along the path until the measured response stops
improving; move to the last improving point."* Taken literally under noise that is a coin flip on
the first step: a measured path of `[0.999, 1.228, 1.028, 0.835, 0.641]` against a centre reference
of `1.021` stops at step one, never relocates, and the arm silently degenerates into `doe_repeat`.
Myers, Montgomery & Anderson-Cook instead take the **maximum along the path**, which is the
registered primary here. Both were run:

* `path_argmax` (primary): **229 arrivals** over 650 landscape-targets.
* `first_decline` (literal): **140**.
* **4 of 26 cells flip verdict between them**, all at σ=0.10.

The choice is therefore not cosmetic and is reported in the result rather than left in a docstring.

### Two defects this arm surfaced, both found by its own tests

1. **The ascent path was clipped to the CCD box.** A steepest-ascent path that cannot leave the
   region it was fitted on cannot relocate the design — it is precisely `doe_repeat`'s limitation
   wearing the new arm's name. Caught by the relocation test.
2. **The improvement reference was the best of 27 noisy CCD readings.** That is an inflated order
   statistic sitting 0.22–0.60 above the centre estimate at σ=0.25, so no single noisy path point
   could beat it and every campaign returned exactly one cycle. The reference must be the CCD's own
   **centre replicates**, which is what centre points are in the design for. A third, smaller bug
   fell out of the same investigation: because the CCD box is clamped at the factor bounds, the
   replicates sit at the box **midpoint**, which is not the requested centre whenever the box
   clamps — so the gradient origin, the path start and the reference all now read one point.

### What is retired, and what is not

The sentence *"cost curves are biased in favour of BO because the classical arm has no steepest
ascent"* now applies to **`doe_repeat` only**. It is retired for `doe_ascent`, and retiring it
**cost BO its one surviving arrival result.** What is *not* retired: BO still wins rule C
decisively at every cell, and the N=48 matched-budget tables are untouched — at a budget that
affords exactly one CCD there is nothing to relocate, so `run_doe_arm` remains the right comparator
there.

---

## Q54 — Hill `spread_gp` at five design draws. **Q52's match was not one lucky hypercube — and the one-shot arm turns out to beat qLogEI on rule C.** `current`

**Ran:** `scripts/run_q54_hill_spread_gp_draws.py` · `results/q54-hill-spread-gp-draws.json` ·
Prompt 3 of `docs/PROMPTS-NEXT.md`.
**Status:** current

### Why

Q52 ran the one-shot arm on Hill with **one** design draw. Q53 then ran the same arm on four
external families at **five**, and found design SDs of 0.029–0.153 — wide enough that
`spread_gp.design_average` returns `nan` rather than `0.0` for a single draw, on purpose. The two
could not be pooled: the Hill claim rested on n=1 from a lottery already shown to be wide, and the
manuscript was required to *"report the current match and not generalise it."*

### The gate: draw 0 is Q52's own seed

| rule | reproduced | worst \|Δ\| |
|---|---|---|
| rule A | **550 / 550 exactly** | 0.000e+00 |
| rule C | 482 / 550 exactly | 2.463e-06 |

Rule A has no optimiser in it, so exact equality is the right bar and it is met. Rule C runs through
20 restarts of L-BFGS-B over 4096 raw samples on a GP posterior mean, which is **not
bit-reproducible** — BLAS threading breaks ties between near-equal local optima.

> **A tolerance calibrated on a convenience sample fails on the population.** The first version of
> this gate set rule C at 1e-06 from a 44-value pilot; the full 550-value population reached
> 2.5e-06 and the gate fired. The fix was not a bigger constant. Rule C is now gated on the property
> it is actually *used* for — whether a curve crosses a target — with a ceiling of 1e-4 that still
> catches a genuinely different campaign, which would move rule C by ~1e-2.

### One arrival in this study really is decided by floating-point scheduling

The closest any rule-C value comes to a target it is tested against is **2.690e-06**, at instance
`f79c5cf175034acd`, σ=0.25, draw 0, n=150, target 0.08 — *closer than the jitter itself*. That
arrival is genuinely indeterminate.

Rather than raise or ignore it, every rule-C curve was re-scored shifted by **±2.463e-06** and the
whole analysis re-run. **No cell changes its verdict across 22 cells × 3 shifts.** The indeterminate
value exists and cannot propagate to a conclusion.

### Result 1 — the match is stable in 20 of 22 cells

| σ | rule | τ | qLogEI | spread mean | design SD | range | Q52 drew | draws differing | stable |
|---|---|---|---|---|---|---|---|---|---|
| 0.25 | C | 0.12 | 20/25 | 25.0 | 0.00 | 25–25 | 25 | 0/5 | yes |
| 0.25 | C | 0.10 | 16/25 | **24.4** | 0.55 | 24–25 | 25 | **5/5** | yes |
| 0.25 | C | 0.08 | 10/25 | **22.2** | 0.45 | 22–23 | 22 | **5/5** | yes |
| 0.25 | C | 0.05 | 7/25 | 13.8 | **1.92** | 11–16 | 15 | 2/5 | **NO** |
| 0.25 | A | 0.03 | 3/25 | 1.0 | 0.71 | 0–2 | 2 | 0/5 | yes |
| 0.10 | C | 0.05 | 18/25 | 18.4 | 1.14 | 17–20 | 18 | 0/5 | yes |
| 0.10 | A | 0.03 | 10/25 | 3.2 | **2.05** | 0–5 | 5 | 1/5 | **NO** |

(Full 22-cell table in the JSON and log.)

**Q52's single draw was not a fluke** — but the two cells where the verdict *does* move with the
draw are both cells where Q52 happened to draw at the favourable extreme: 15 against a 11–16 range,
and 5 against a 0–5 range. Instability tracks design SD exactly: the two unstable cells carry SDs of
1.92 and 2.05 while every stable cell is at or below 1.14.

### Result 2 — the one-shot arm *beats* ten-round qLogEI on the model's recommendation

This was not what Q52 reported and it is the larger finding. At the higher-noise condition, on
rule C, one Latin hypercube plus one GP fit **arrives more often than ten rounds of qLogEI**, and
does it in **1 plate round against 48**:

| σ=0.25, rule C | qLogEI | spread+GP | draws agreeing |
|---|---|---|---|
| τ=0.12 | 20/25 | **25.0/25** | 5/5 |
| τ=0.10 | 16/25 | **24.4/25** | 5/5 |
| τ=0.08 | 10/25 | **22.2/25** | 5/5 |

Those three cells are unanimous across all five draws — this is not the design lottery.

**And it reverses on rule A**, at both noise levels: 1.0 against 3/25 at σ=0.25 τ=0.03, and 3.2
against 10/25 at σ=0.10 τ=0.03. The one-shot design's *best measured well* is worse; its *fitted
recommendation* is better.

> **This is the paper's central thesis reproduced inside a single arm.** The same 200 evaluations,
> the same landscape, the same GP — and which method "wins" is decided entirely by whether you
> report the best reading you took or the point your model recommends. Q53 found the dividing line
> between families was deception; Q54 finds that within the Hill family the dividing line is the
> terminal decision.

### What this licenses, and what it does not

The manuscript may now say the Hill match is a five-draw result rather than a single draw, and may
state the σ=0.25 rule-C advantage, which is unanimous. It may **not** generalise the two unstable
cells (σ=0.25 rule C τ=0.05; σ=0.10 rule A τ=0.03) — those are properties of which hypercube was
drawn. Q53's constraint still binds for the external families: on deceptive landscapes
(Hartmann6, Ackley) the one-shot arm loses badly, and nothing here touches that.

---

## Q57 — qLogNEI as co-primary. **The primary-cell headline survives; two quiet-assay verdicts do not.** `current`

**Ran:** `scripts/rescore_oracle_best.py` (extended) · `results/q57-search-vs-id.json` ·
Workstreams 1 and 3 of the revision program. Extends Q55; does not supersede it — Q55's
columns reproduce here at |Δ| = 0.
**Status:** current

### Why

Q55 separated search from identification using **qLogEI alone**. The revision program is
explicit that this is not enough: *"a reviewer can dismiss a DoE win as 'wrong
acquisition'"*, and observations here really are noisy, which is the entire reason noisy EI
exists. The executed comparison this project answers to used noisy EI.

**qLogNEI is better than qLogEI at all four cells** (0.1532 / 0.0808 / 0.1105 / 0.0849
against 0.1553 / 0.0874 / 0.1247 / 0.0972), so promoting it is the *harder* test for the
classical arm's lead, not a friendlier one.

### The gate

Rule A reproduced **per row at |Δ| = 0.000e+00 for all 200 qLogEI, 200 qLogNEI and 200
classical rows**, and all sixteen published cell means to 5e-05.

### Result 1 — noisy EI substantially fixes BO's identification problem

| cell | arm | rule A | tested-best | gap | identification rate |
|---|---|---|---|---|---|
| d=6 σ=0.25 | qLogEI | 0.1553 | 0.0755 | +0.0797 | **8%** |
| d=6 σ=0.25 | **qLogNEI** | 0.1532 | 0.0834 | **+0.0698** | **22%** |
| d=8 σ=0.25 | qLogEI | 0.1247 | 0.0702 | +0.0545 | 12% |
| d=8 σ=0.25 | **qLogNEI** | 0.1105 | 0.0685 | **+0.0419** | 18% |

At the primary cell qLogNEI identifies its own best well **22% of the time against
qLogEI's 8%** — nearly three times as often — and its identification gap is a fifth
smaller. That is exactly what noisy EI is for: it does not trust a single incumbent
reading. **It is a real improvement, and it is not enough.**

### Result 2 — the primary headline survives, and is stronger on tested-best

| cell | vs | rule A (DoE−BO) | tested-best (DoE−BO) |
|---|---|---|---|
| d=6 σ=0.25 | qLogEI | −0.0595 [−0.0797,−0.0375] | −0.0158 [−0.0257,−0.0062] |
| d=6 σ=0.25 | **qLogNEI** | **−0.0574** [−0.0776,−0.0376] | **−0.0237** [−0.0379,−0.0111] |
| d=8 σ=0.25 | qLogEI | −0.0284 [−0.0447,−0.0139] | −0.0127 [−0.0251,−0.0008] |
| d=8 σ=0.25 | **qLogNEI** | **−0.0142** [−0.0251,−0.0036] | −0.0111 [−0.0225,−0.0003] |

**Both higher-noise cells give the same verdict under both acquisitions, on both
locators.** The classical arm still selects a better well *and* still tested better
conditions. At the primary cell the tested-best advantage is **larger** against qLogNEI
(−0.0237) than against qLogEI (−0.0158), because qLogNEI's better identification pulls its
rule-A number down without improving where it looked.

> **The headline is not an artefact of the acquisition function.** That was the loophole
> Workstream 3 existed to close, and it is closed in the direction that keeps the result.

### Result 3 — two quiet-assay verdicts ARE acquisition-dependent, and one of them retracts a Q55 sentence

| cell | locator | qLogEI says | qLogNEI says |
|---|---|---|---|
| d=6 σ=0.10 | tested-best | null | **BO** (+0.0109 [+0.0021,+0.0194], p = 0.0342) |
| d=8 σ=0.10 | tested-best | **DoE** (−0.0153, p = 0.0056) | null (−0.0064, p = 0.5602) |

**This retracts a sentence from the Q57 entry's predecessor.** Q55 reported d=8 σ=0.10 as
*"the classical arm tested materially better conditions and the noisy readout hid it
entirely"*, calling it the interesting cell. **Against qLogNEI that contrast is null.** The
effect was a property of qLogEI's search, not of the classical design, and the claim is
withdrawn. It is struck rather than deleted, per §5 of the cleanup brief.

The d=6 σ=0.10 flip runs the other way and is new: under qLogNEI, **BO** tested better
conditions at the quiet assay, which no qLogEI analysis showed.

### What may now be written

* **At the higher-noise condition, on both locators, under both acquisitions** — the
  classical arm's advantage is a result, not an artefact of the acquisition.
* **At the quiet assay, nothing about tested-best may be stated without naming the
  acquisition.** Both σ=0.10 cells change verdict.
* Measured-value argmax is stable everywhere: all four cells give the same verdict under
  both acquisitions (DoE, null, DoE, null).

---

## Q58 — selection-rule sensitivity. **Three confirmation wells erase the classical arm's entire advantage.** `current` 🔴

**Ran:** `scripts/run_q58_selection_sensitivity.py` · `results/q58-selection-sensitivity.json` ·
new module `src/boec/selection.py`, 10 tests written first. Workstream 6.
**Status:** current

### Why

Every headline in this project scores the campaign at the **single noisy readout**. Q55/Q57
showed that rule is poor — the noisy argmax is the genuinely best visited well only 2–22% of
the time — and that the adaptive arm suffers more, because it clusters its wells where the
differences are smaller than the noise. So the obvious objection is that the classical arm's
lead is a fact about **one selection convention**, not about design geometry.

This re-selects from **the same campaigns** under four rules. Only the final pick moves.

### Result

d=6, σ=0.25, n=25 landscapes × 2 seeds:

| rule | extra wells | BO | DoE | DoE − BO | Wilcoxon p | vs published |
|---|---|---|---|---|---|---|
| **single** (published) | 0 | 0.1553 | 0.0958 | **−0.0595** [−0.0797,−0.0375] | 0.0000 | 1.00× |
| replicate every well | +48 | 0.1447 | 0.1185 | −0.0262 [−0.0446,−0.0079] | 0.0173 | **0.44×** |
| **confirm top 3** | **+3** | 0.1446 | 0.1437 | **−0.0009** [−0.0263,+0.0253] | 0.9158 | **0.01×** |
| posterior mean at visited | 0 | 0.1387 | 0.1160 | −0.0227 [−0.0438,−0.0022] | 0.1135 | 0.38× |

> **Every better selection rule cuts the advantage by more than half, and confirming three
> wells removes it entirely.** −0.0595 becomes −0.0009 — a dead tie — for **three extra
> measurements on a 48-well campaign.**

### Why three wells do so much

They do not help both arms equally. Confirmation moves BO from 0.1553 to 0.1446 and moves
the classical arm from 0.0958 to **0.1437 — it makes the classical arm worse.**

That is the mechanism running in reverse. The classical arm's single reading was already
comparatively reliable because its design replicates the centre and spreads the rest; the
adaptive arm's was a lottery among near-ties. A protocol that **decides by a fresh single
reading** therefore takes away the classical arm's advantage rather than improving both.

### A stated limit on the top-3 rule

`top_k_confirm` shortlists by the first reading and **decides by the confirmation reading
alone**, discarding the first. That is one real protocol — *"re-run the best three, keep
whichever confirms best"* — and it is what produced the tie. A lab that instead decided by
the **mean of the original and the confirmation** would be closer to `replicate` at a third
of the cost, and that variant **was not run**. The tie above is a property of the protocol
as implemented, and the alternative is an open question, not a claim.

### A registered disagreement between the two tests

The posterior-mean row has a bootstrap interval excluding zero, [−0.0438, −0.0022], and a
Wilcoxon p of 0.1135. **Q20 §2 registers that Wilcoxon governs yes/no and the bootstrap
reports magnitude, with disagreements reported and not resolved.** By that rule the
posterior-mean contrast is **null**, and both numbers are recorded here rather than the
convenient one.

### What this does to the project's headline

The measured-value-argmax result stands exactly as published — it was always a claim about
that decision rule, and Q57 showed it survives both acquisitions. What Q58 adds is how
**narrow** the rule is:

* It survives replication and a model-based pick at **roughly 40% of its published
  magnitude**.
* It does **not** survive a three-well confirmation protocol.
* The confirmation protocol costs **3 wells out of 48** — 6% of the campaign.

A laboratory that confirms its top three candidates before committing sees **no difference
between the two methods at the primary cell.** That belongs beside the headline, not in a
supplement.

---

## Q59 — Hartmann6 with and without the 6→4 screen. **The screen was helping the classical arm, not handicapping it.** `current`

**Ran:** `scripts/run_q59_hartmann_no_screen.py` · `results/q59-hartmann-no-screen.json` ·
Workstream 5.
**Status:** current

### Why

Hartmann6 has six active coordinates. The classical pipeline screens 6 down to 4 before
building its surface, so the stored result *"BO wins on Hartmann6 under every rule"*
bundles the optimizer's failure with the **screen's** failure — it discards two
coordinates that genuinely matter. The objection writes itself, and until now it could not
be answered.

### The gate

The screened arm reproduces the committed D20-corrected Hartmann6 column on **all 50 rows
at |Δ| = 0.000e+00** before the unscreened arm beside it is read.

### An arithmetic finding that came before any number

A full second-order model needs `C(d+2,2)` terms — 28 at d=6, **45 at d=8**. The
face-centred CCDs that exist inside a 48-well budget:

| d | n_derived | runs | + confirmation | residual df |
|---|---|---|---|---|
| 6 | 1 | 47 | **48** | 19 |
| 8 | 2 | 83 | 84 | 38 |
| 8 | 4 | 35 | 36 | **cannot fit — 35 runs, 45 terms** |

**An unscreened classical pipeline is not merely worse at d=8, it is arithmetically
impossible within the shared budget.** That is not a limitation of the script; it is the
reason the 6→4 screen exists at all, and it is why this run is d=6 only.

### Result — removing the screen makes the classical arm much worse

| σ | qLogEI | qLogNEI | DoE screened | DoE unscreened | cost of removing the screen |
|---|---|---|---|---|---|
| 0.25 | 0.2984 | 0.2642 | **0.5623** | 0.7685 | **+0.2062** |
| 0.10 | 0.1938 | 0.1658 | **0.5428** | 0.7502 | **+0.2074** |

And BO's lead **widens** rather than closing:

| σ | vs | screened | unscreened | change |
|---|---|---|---|---|
| 0.25 | qLogEI | +0.2639 [+0.1949,+0.3304] | +0.4701 [+0.3974,+0.5329] | **1.78×** |
| 0.25 | qLogNEI | +0.2981 [+0.2261,+0.3709] | +0.5043 [+0.4150,+0.5757] | 1.69× |
| 0.10 | qLogEI | +0.3490 [+0.3000,+0.3997] | +0.5564 [+0.5057,+0.6015] | 1.59× |
| 0.10 | qLogNEI | +0.3770 [+0.3222,+0.4320] | +0.5844 [+0.5325,+0.6291] | 1.55× |

> **The confound runs the opposite way to the objection.** BO's Hartmann6 win is *not* an
> artefact of the classical arm being forced to discard two active factors. Given all six,
> and 47 wells to cover them with, the classical arm does **worse** — because a CCD spread
> over the whole six-dimensional box is very coarse, while concentrating 27 wells in a
> sub-box around the best screening run is a far better use of the same budget on a
> landscape with a narrow optimum.
>
> **The screen is doing adaptive resource allocation, and it is earning its place.**

### A second, negative result: the sub-box is not what breaks the recommendation

The unscreened CCD spans the whole box, so its fitted quadratic **cannot** recommend a
point outside the region it was fitted on — the extrapolation failure mode is impossible by
construction. If the giant unconstrained gap were mainly about escaping a sub-box, it
should largely vanish here.

| σ | screened rule C | unscreened rule C | difference |
|---|---|---|---|
| 0.25 | 0.9008 | 0.8695 | −0.0313 |
| 0.10 | 0.8985 | 0.8810 | −0.0175 |

**It barely moves.** Removing every opportunity to extrapolate buys 0.02–0.03 of regret out
of ~0.90. On Hartmann6 the quadratic recommendation is bad because **a quadratic cannot
represent a six-optimum landscape**, not because it was fitted on too small a region. The
sub-box explanation, which does real work on the Hill oracle, does not transfer here.

### What this licenses

* The Hartmann6 result may now be stated **without** the screening caveat at d=6: the win
  is not a screening artefact and is larger when the screen is removed.
* The caveat still stands at **d=8**, where the unscreened comparison cannot be run at all
  within budget — and that impossibility should be stated rather than glossed.
* *"The unconstrained gap is extrapolation out of the design region"* is a claim about the
  Hill oracle. On Hartmann6 it is mostly **model misspecification**, and the two should not
  be pooled.

---

## 2026-08-17 — TOST applied; Q60/Q61 deferred

`results/tost-contrasts.json`. SESOI = 0.02. Primary in-region and Q58 top-3 are
**inconclusive** (MDE 0.027 and 0.042). Low-noise measured-argmax is **equivalent**.
Q58 posterior is **different**.

Q60 smoke: DoE `single` matched Q58 at 1e-12; BO did not
(0.2421 vs stored 0.2411 on instance 0 seed 0). Q57 replay of the same cell also
drifts. Acquisition optimizer retried after a scipy failure. No `src/boec` campaign
code changed since Q58 (`a189ddd`). Paper is written from stored JSON; Q60/Q61 not run.

---

## Q62 — TuRBO-1. Locally constrained qLogNEI does not close the noisy-argmax gap. `current`

**Ran:** `scripts/run_q62_turbo.py` · `results/q62-turbo.json` (N=48) ·
`results/q62-turbo-n200.json` (N=200) · module `src/boec/turbo.py` ·
`CampaignConfig.use_turbo` · Figure 4 from `src/boec/paper_figures.py`.
Ticket **Q62**. Q60/Q61 remain unrun.
**Status:** current

### Why

The remaining easy reviewer line is *"unconstrained BO searches the whole box;
RSM does not."* TuRBO-1 (Eriksson et al. 2019; BoTorch defaults) is the one-knob
answer: the same qLogNEI acquisition, proposals clipped to an adaptive trust
region around the posterior-mean incumbent. Restart **keeps** history — a
registered deviation from canonical TuRBO so `doe_ascent` is not compared to an
amnesiac. Frozen `length_init=0.8`, `length_min=0.5**7`, `length_max=1.6`. Gate:
stored E2 qLogNEI instance means round to 0.1532 / 0.0808 before any row is
trusted.

This is a **sampling constraint**, not a new terminal rule and not walking RSM.

### Result 1 — N=48 measured argmax, primary cell

| Arm | σ=0.25 | σ=0.10 |
|---|---|---|
| 48-well DoE | 0.0958 | 0.0892 |
| Unconstrained qLogNEI | 0.1532 | 0.0808 |
| TuRBO-1 qLogNEI | **0.1538** | **0.0736** |
| DoE − TuRBO | **−0.0580 [−0.0768, −0.0390]** | **+0.0156 [+0.0041, +0.0274]** |
| TuRBO − qLogNEI | +0.0006 [−0.0205, +0.0206] | −0.0072 [−0.0214, +0.0071] |
| Identification gap | 0.0704 | 0.0337 |
| Unique wells / restarts / collapse | 48/48 · 0 · 0 | 48/48 · 0 · 0 |

> **The box is not the result.** At the noisy primary cell TuRBO is statistically
> the same as unconstrained qLogNEI. DoE's measured-argmax lead is not "BO
> wandered."

### Result 2 — N=200 arrival, τ=0.10, both seeds must hit

Do **not** subtract 48-well E2 DoE from 200-well TuRBO regret.

| σ | TuRBO | Q56 `doe_ascent` | Q56 qLogEI |
|---|---|---|---|
| 0.25 | **11/25** | 8/25 | 14/25 |
| 0.10 | **25/25** | 16/25 | 24/25 |

Mean unique locations ≈ 199; ~2 restarts per campaign. No collapse. The noisy
primary cell still does not show a general BO well-count saving versus relocating
RSM. At lower noise everyone arrives.

### What this licenses

* The paper may answer the local-search objection with a number, not a shrug.
* Language: **locally constrained sequential search**. Do not write isomorphic
  to RSM.
* Paper 1 is not blocked on Q63 (OCBA).

### What this does not license

TuRBO as a wet-lab method, a new estimand, or a reason to retire the terminal-rule
reversal. Q60/Q61 remain unrun.
