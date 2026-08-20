# ODIN — feasibility verdict and go/no-go plan

**Reviewing:** `docs/ODIN-SPEC.md` v1.0
**Date:** 2026-08-20 · **Repo state:** `c0fffff`, 808 tests passing
**Every number below is read from a committed JSON in `results/`. Sources named inline.**

---

## The answer

# YES — but delete Stage 2, and three of the four "day 1" tasks are already done.

The tool is worth building. The spec is not the right build order, because it
spends its largest engineering effort (Stage 2: NumPyro, I-splines, 36
parameters, ~100 CPU-hours) on the one bottleneck this repository has already
measured to be **absent**, and treats as bolt-ons (Stages 3 and 4) the two
components already measured to carry **the entire effect**.

Rebalanced, it is a real contribution and roughly a third of the work.
As specified, its most expensive stage is predicted to return ~0.

---

## 1. What is already answered, with the numbers

The spec's §14 "minimum viable first week" has four items. Three are done.

### Day 1, G1 (lengthscale check) — **ALREADY RUN, and the gate as written is broken**

`results/diagnostic-lengthscales.json`, 200 campaigns, 3 checkpoints each.
The spec's rule is *"median ARD lengthscale below ~0.4 → mechanism wrong, stop."*

Median active-dimension lengthscale, final checkpoint (n=46):

| cell | med active | med inert | **permutation null** | ARD separation (inert/active) | fitted ls ÷ true FWHM |
|---|---|---|---|---|---|
| d=6 σ=0.25 (primary) | **0.421** | 0.745 | 0.488 | 1.77 | 0.57 |
| d=6 σ=0.10 | **0.397** | 1.507 | 0.396 | 3.79 | 0.56 |
| d=8 σ=0.25 | 0.485 | 0.864 | 0.633 | 1.78 | 0.70 |
| d=8 σ=0.10 | 0.442 | 1.609 | 0.569 | 3.64 | 0.60 |

Three problems with G1, in increasing order of seriousness.

**(a) The threshold sits below the no-signal null.** The lengthscale prior is
log-normal and the fit is MAP, so a fit that learns *nothing* returns the prior
**mode** — `exp(loc − scale²)` = **0.5016** at d=6, 0.5792 at d=8. That is also
gpytorch's initialisation. A rule that reads ">0.4 as mechanism-confirmed"
**passes a model that learned nothing.** `src/boec/lengthscale_diag.py` documents
this as defect **D8**: an earlier version of this project's own diagnostic
anchored on the prior *median* (10.08), which made one branch unreachable, and a
conclusion was written and committed from a rule that could only return one
answer. G1 repeats that error one decimal place over.

**(b) On the stated threshold, the gate does not cleanly pass.** d=6 σ=0.10 gives
**0.397 — below 0.4.** The primary cell gives 0.421, a 5% margin. The spec's own
instruction on those numbers is "stop and re-plan."

**(c) It does not test what it claims to test.** Stein (1987) is about **additive
share**. Lengthscale is about **smoothness**. A long-lengthscale Matérn GP is not
additive. The chain *long lengthscale → low-order structure → high additive share
→ LHS variance reduction* has an unjustified link in the middle, and additive
share is directly measurable — **this project already measured it at ~93%** (Q22,
cited in `scripts/run_q30_additive.py`'s docstring; not written up in `RESULTS.md`,
so re-derive it before citing), with no lengthscale argument needed.

**Correct reading, using the repo's own permutation null:** ARD *is* learning.
The inert/active separation ratio is 1.77–3.79 where a purely prior-driven fit
gives exactly 1.0. But `fitted ls ÷ true FWHM = 0.56–0.70` says the GP fits
**shorter** scales than the truth — it is **under-smoothing, not over-smoothing.**
The spec's premise, *"at N < 10d the surrogate has no capacity to be genuinely
nonparametric,"* is empirically **false in this repo.** It has the capacity and
uses it, on noise.

> **Verdict on G1: replace it.** The design story should be gated on measured
> additive share (already 0.93) and on the design lottery (§3 below), not on a
> lengthscale threshold that cannot fail in the direction it is aimed.

### Day 1, G2 (sup-norm vs R²) — **half-answered, and the half that is answered supports the spec**

**Q30** (`docs/RESULTS.md:247`) ran an additive-kernel BO arm:

> **the additive kernel roughly doubled held-out R² and moved regret by 0.0015, p = 0.71.**
> *"Model accuracy is not the constraint. A surrogate that fits twice as well recommends no better."*

That is the L²-half of G2, already decided: **R² does not govern regret.** The
sup-norm half has never been computed and is genuinely worth running (K0 below).

### Day 3, B9 — **ALREADY BUILT AND ALREADY RUN, TWICE**

The spec calls B9 "the critical baseline… run it before anything else." It is
`src/boec/spread_gp.py` — one-shot LHS, one GP fit, posterior-mean argmax — and
it has been run on the Hill family at 5 design draws (**Q54**) and on four
external families at 16 cells (**Q53**):

| family | verdict for one-shot spread vs 10-round qLogEI |
|---|---|
| hill, levy, rosenbrock | **TIE** — in 1 plate round against 10 |
| hartmann6, ackley | **LOSES**, +0.13 to +0.28, all p_holm ≤ 0.0016 |

And Q54 found the stronger version: at σ=0.25 on the model's own recommendation,
**one hypercube plus one GP fit arrives more often than ten rounds of qLogEI.**

> *"Adaptivity buys deception-handling, not sample efficiency per se."* — Q53

The spec's §14 day 3 is complete. Its result is a **tie**, not a win, and the
dividing line is **deception**, not dimension and not noise.

### The oracle ladder (G3) — rungs 0 and 1 are on disk

`results/q57-search-vs-id.json`, d=6 σ=0.25, n=25 landscapes × 2 seeds:

| rung | BO (qLogEI) | classical | contrast |
|---|---|---|---|
| 0 — measured-value argmax | 0.15525 | 0.09580 | **−0.05945** [−0.0797, −0.0375], p=2.2e-05 |
| 1 — oracle terminal rule | 0.07551 | 0.05967 | **−0.01584** [−0.0257, −0.0062], p=0.0067 |
| identification gap | 0.07975 | 0.03613 | |

**Granting a perfect terminal rule removes 73% of the gap and 51% of BO's total
regret.** Rungs 2–6 are unrun. The spec's cited 0.0755 for rung 1 is correct.

---

## 2. What this does to each stage

| Stage | Spec's effort | Evidence | Verdict |
|---|---|---|---|
| **1. Design** (OA-LHS + replicates) | medium | untested; design lottery known to be ±0.15 on Hartmann6 (Q53) | **BUILD — largest untested target in the repo** |
| **2. Inference** (unimodal additive, NUTS, ~100 CPU-h) | **largest** | Q30: 2× R² → **Δregret 0.0015, p=0.71** | **DELETE** |
| **3. Nomination** (posterior mean, plausible region) | small | Q55/Q57: **73% of the gap**; Q35/Q34: winner reverses in 3 of 4 cells | **BUILD — this is the effect** |
| **4. Confirmation** (EOC allocation) | "optional" | Q58: 3 wells (6% of budget) take the gap from −0.0595 to **−0.0009** | **BUILD — but see the sign warning** |

### Stage 2 is refuted at the mechanism level, not merely at the arm level

The spec's own gate **G6** sets the bar at 0.01. Q30 measured **0.0015, p=0.71** —
6.7× below the threshold and statistically null. It is fair to object that Q30's
additive *kernel* is not ODIN's shape-constrained additive *model*, and that is
true. But Q30's finding is not "this particular kernel failed." It is
**"doubling surrogate accuracy does not move the recommendation"** — a statement
about the bottleneck, not about one model. Stage 2 is an accuracy intervention.
The accuracy channel is measured to be closed.

Build Stage 2 only if K0 (below) shows sup-norm error *does* govern regret while
R² does not, because that would mean Q30 improved the wrong norm and a
shape-constrained model that improves the *right* one is still live. That is the
one route by which Stage 2 survives, and it costs a day to check.

### Stage 4 has its sign backwards — but on an untested variant, so it survives

Q58 measured what happens when you spend 3 wells confirming your top 3:

| rule | BO | classical | gap |
|---|---|---|---|
| single readout (published) | 0.1553 | 0.0958 | −0.0595 |
| **confirm top 3** | 0.1446 | **0.1437** | **−0.0009** |

Confirmation moved BO from 0.1553 → 0.1446 (**helped**) and the classical arm
from 0.0958 → **0.1437 (hurt it badly)**. The mechanism: a *spread* design's
first reading was already the trustworthy one; a *clustered* design's was a
lottery among near-ties. **ODIN is a spread design.** On this evidence, Stage 4
is predicted to hurt it.

**The escape, and it is a real one.** Q58 states explicitly that `top_k_confirm`
*"decides by the confirmation reading alone, discarding the first"* and that the
averaging variant **was not run** and is "an open question, not a claim."
ODIN §5.3 refits on **all** observations — i.e. it *averages*. So ODIN's Stage 4
is precisely the variant Q58 flagged as untested. That makes it the single
highest-value unrun experiment in the repository, and it is cheap.

---

## 3. What is genuinely new and worth running

Stripping out what is done and what is refuted, four things remain untested and
each has a measurable target:

1. **Replicates for σ identification.** Never run. The spec's Stage 1 spends 6 of
   48 wells on it. Rung 2 of the oracle ladder bounds its value exactly.
2. **OA-LHS vs plain LHS.** Never run. Target is large and known: Q53 measured
   `spread_gp`'s design SD at **0.140–0.153 on Hartmann6** — over half the entire
   `spread_gp − qLogEI` gap comes from *which hypercube you happened to draw*.
   A design that shrinks that lottery is worth exactly that much.
3. **Confirm-and-average vs confirm-and-replace.** Q58's own flagged gap.
4. **The deception detector.** Q53 established the dividing line — smooth and
   coordinate-wise unimodal → tie; deceptive → lose — but **nobody built the
   statistic that tells you which side you are on from the first plate.**
   This is the regime claim in the spec's §12, and it is the actual contribution.

Item 4 is the paper. Items 1–3 are the mechanism section.

---

## 4. Three specification errors to fix before coding

**(a) The 48-well arithmetic defeats the mechanism.** Strength-2 OA-LHS needs
`n = p²`. `N_unique = 42` is not a prime square, so the spec falls back to
nearly-orthogonal maximin LHS — which is **not** the construction whose Stein-theorem
justification is the entire Stage 1 argument, and is much closer to the plain LHS
already running as `spread_gp`. At `n = 49, p = 7, d ≤ 8` it works exactly.
**Run Stage 1 at n=49 and report the one-well mismatch openly**, or drop the
OA claim and call it maximin LHS. Do not fall back silently and keep the citation.

**(b) The proposed oracle sweep is an inverse crime the spec does not catch.**
§11.1 flags unimodality-vs-Hill. But §8.1 also proposes sweeping additive share
on the Hill generator — while ODIN's model is *additive + unimodal* and the Hill
oracle is *additive + unimodal by construction*. Sweeping λ does not fix that; it
only varies how much variance sits in the part ODIN models correctly by
assumption. The phase diagram would measure *"how much does ODIN win when its
assumptions are exactly true, as a function of how true they are."*
**Q53 already ran the honest version** — Hartmann6 and Ackley, where the one-shot
arm loses. Keep the external families as the *primary* axis, not "validation."

**(c) 60 landscapes × 5 seeds × 20 cells is not budget-matched to this repo.**
Every gate here compares against **committed** columns at 25 instances × 2 seeds.
A new grid at n=60 cannot be gated against them at |Δ|=0, which is this project's
standard (D12: *a gate comparing one fresh run to another can only report that
the code agrees with itself*). Run the confirmatory cells at the committed
geometry; use n=60 only for genuinely new cells.

---

## 5. The revised pipeline

**ODIN-R** — three stages, no NUTS.

| Stage | What | Status |
|---|---|---|
| 1 | OA-LHS at n=49 (or maximin at 48) + 3 anchors × 3 reps for σ̂ | **new** |
| 2 | Plain Matérn GP, σ̂ plugged in from replicates rather than fitted | `build_gp` exists; plug-in path exists (`_plug_in_yvar`) |
| 3 | Posterior mean over the plausible-optimum region | `constrained_argmax` exists; region mask is **new** |
| 4 | Confirm top-k, **decide on the mean of all readings** | `selection.py` exists; averaging variant is **new** |

Claim it can support, which is smaller than the spec's and defensible:

> On landscapes that are smooth and coordinate-wise unimodal — a property
> testable from the first plate — a one-shot orthogonal-array design with
> replicate-identified noise and a shrunk terminal rule matches ten rounds of
> batch BO and beats classical RSM at matched wells, in one plate round against
> ten. On deceptive landscapes it loses, and the detector says which you are on
> before you commit.

---

> ⚠️ **§6 below is SUPERSEDED.** SPADE (`docs/SPADE-SPEC.md`) replaces ODIN, and three
> claims in §6 were wrong. The authoritative plan is
> **`docs/superpowers/plans/2026-08-20-spade-go-no-go.md`**. See §7 for what changed.

## 6. Implementation plan — kill tests in order *(superseded — see §7)*

Ordered by kill-power per CPU-hour. **Stop at the first hard failure.**
Every runner follows the repo's existing conventions: register the question in
`docs/OPEN-QUESTIONS.md` and commit *before* the runner exists; gate any
regenerated column against the committed one at |Δ| = 0; tests written first.

### K0 — finish G2. The only route by which Stage 2 survives. *(~4 h, no new campaigns)*

Refit the stored campaigns' GPs, and on a 20k-Sobol grid compute `sup_err`
= max|E[f(x)] − f(x)| and grid R², then correlate each against realised regret
across all 200 stored campaigns.

- **Kill:** R² correlates with regret at least as strongly as `sup_err`
  → the L∞ thesis is dead → **Stage 2 stays deleted, permanently.**
- **Revive:** `sup_err` correlates and R² does not → Q30 improved the wrong norm
  → Stage 2 goes back on the table, and gets its own gate.
- Pre-register the comparison statistic (Spearman ρ, paired bootstrap on the
  difference of correlations) before looking.

### K1 — oracle-ladder rung 2. Bounds Stage 1's replicate budget exactly. *(~3 h)*

Grant both arms the **true** σ instead of a fitted one. Rungs 0 and 1 are already
on disk, so this slots straight into the existing ladder.

- **Kill:** moves regret < 0.01 → **drop the replicates**, hand those 6 wells back
  to the design, and Stage 1 becomes design-only. (The spec instructs this itself.)
- **Note:** this is a *ceiling*, not an estimate. Replicates give you σ̂, not σ.
  If the ceiling is below 0.01 the estimate cannot beat it.

### K2 — the design lottery. Largest untested target in the repo. *(~6 h)*

20 design draws each of {plain LHS, maximin-LHS, OA-LHS at n=49}, at d=6 and d=8,
on **Hill and Hartmann6**. Report design SD, not just mean regret.

- **Target is known:** Q53 measured plain-LHS design SD at **0.140–0.153 on
  Hartmann6** and 0.029–0.055 elsewhere.
- **Win:** OA-LHS cuts Hartmann6 design SD materially → Stage 1 has a mechanism
  that is *about variance reduction*, which is what Stein actually says, and is
  measurable without the lengthscale detour.
- **Kill:** design SD unchanged → Stage 1 is plain LHS with extra steps →
  ODIN-R collapses into `spread_gp`, which is already published as Q53/Q54.
  **That is the no-go branch.**

### K3 — confirm-and-average. Q58's own flagged open question. *(~4 h)*

Re-select from the **same stored campaigns** — no new wells — under a fifth rule:
shortlist by first reading, decide by the **mean** of first and confirmation.
Compare against Q58's four committed rules; gate those four at |Δ| = 0.

- **Win:** averaging preserves the classical/spread arm's advantage where
  replace-only destroyed it (0.0958 → 0.1437) → Stage 4 is sound and the sign
  warning in §2 is discharged.
- **Kill:** averaging also erases it → **Stage 4 is deleted**, and the honest
  headline becomes *"any confirmation protocol equalises the two methods,"*
  which is a stronger and more useful result than ODIN.

### K4 — the deception detector. This is the paper. *(~2 days)*

From the first plate only — no oracle access — compute candidate statistics and
ask whether they separate the tie families (hill, levy, rosenbrock) from the
lose families (hartmann6, ackley). Candidates, all first-plate-computable:

- measured additive share of the fitted GP (ANOVA decomposition on the grid)
- ARD inert/active separation ratio (already in `lengthscale_diag.py`)
- number of distinct local maxima of the posterior mean above a threshold
- fitted lengthscale ÷ box width, per coordinate
- residual variance after an additive-only fit, relative to σ̂ from replicates

**Register the decision rule and the threshold on the Hill + Levy + Rosenbrock
training set, freeze it, then score on Hartmann6 + Ackley once.** Anything else
is tuning on the evaluation set, which is the failure mode this whole project
exists to document.

- **Win:** a frozen first-plate rule calls the regime correctly on held-out
  families → the §12 regime claim is earned rather than asserted.
- **Kill:** no statistic separates them → the regime boundary is real (Q53 proved
  it) but **not predictable in advance**, so the claim must be cut to
  *"the boundary exists and is deception-shaped"* and the tool ships without a
  detector.

### Go / no-go

**GO** if K2 wins or K3 wins. Either gives ODIN-R a mechanism the current
published arms do not have.

**NO-GO** if K2 and K3 both fail. In that case ODIN-R **is** `spread_gp` plus a
terminal rule, both already measured, and the correct action is to write up
Q53/Q54/Q55/Q57/Q58 as they stand — which is already a complete methods paper —
rather than rebrand them as a new tool.

K0 and K1 do not gate go/no-go on their own. They decide **how much** of the
spec gets built.

### Effort

| | spec as written | this plan |
|---|---|---|
| before a go/no-go | ~1 week + Stage 2 | **~2 days (K0–K3)** |
| CPU | ~100 h for Stage 2's grid alone | **~15 h total, K0–K4** |
| new campaigns | full 20-cell grid | K2 only; K0/K1/K3 re-score stored runs |

Three of the four tests re-score campaigns that are already on disk. That is why
this is two days and not two weeks.


---

## 7. Corrections after SPADE — what §6 got wrong

Three findings from checking SPADE against the repo. Each changes the plan.

### 7.1 "Re-scores stored runs" was wrong for every test

§6 claimed K0, K1 and K3 "re-score campaigns that are already on disk. That is why this
is two days and not two weeks." **No result file stores `X` or `Y`.** `e2-grid.json`
rows are `[instance, dim, sigma, seed, arm, best, regret, auc_post_init]`; Q42, Q57, Q58
and d20 are likewise scalar-only. There is nothing to refit a GP on.

Every such test is a **regenerate-and-score**. The compute is not the problem —
stored `secs` in `q57-search-vs-id.json` give ~6 s/campaign, so 1300 rows is ~1 CPU-hour,
and `Campaign.state_dict()` already persists `train_X/Y/Yvar`; the runners simply never
called `save()`. What is new is a **gating obligation**: a regenerated column must be
checked against the committed one, and Q54 established that anything routed through
multi-start L-BFGS-B is not bit-reproducible (worst |Δ| 2.463e-06, 482/550 exact).

Consequence: the plan gains **Task 1**, a replay module whose *output is a gating
policy*, and every downstream task depends on it.

### 7.2 The certified-volume metrics may be degenerate

SPADE predicts spread designs win on certified volume and inscribed-box volume. Measured
neighbour density says both may be **identically zero** for a spread arm:

| n | d | ℓ | neighbours within one lengthscale |
|---|---|---|---|
| 48 | 6 | 0.42 | **0.49** |
| 48 | 6 | 0.50 | 1.22 |
| 55 | 6 | 0.42 | 0.57 |
| 48 | 8 | 0.485 | **0.15** |

SPADE assumed ~1.4. At 0.49, `s(x)` sits near the prior SD and `LCB = μ − 1.96s` may
clear τ nowhere. Both metrics share that predicate, so they die together.

Fix, adopted in the plan: report **certified volume as a curve over the confidence
multiplier z**, with 95% as one point, and make the threshold-free probability-map score
(Brier/AUC) the **primary** metric. SPADE's own 6D volume ratio (125) and clustered
`s = 0.0395` both check out.

### 7.3 SPADE Stage 2's mechanism is wrong — the real one is better

SPADE argues the GP under-smooths *"because MAP fits lengthscale and noise jointly."*
**It does not.** `build_gp`'s docstring: `train_Yvar` is *"always required, never
optional."* Noise is supplied as known per point; there is no joint fit and no
degeneracy to break.

The live mechanism is a coupling nobody has named. `BiphasicOracle.evaluate` returns
`_plug_in_yvar(y, ...)` = `y²·σ_rel² + σ_add²` — computed from the **noisy reading**,
not from `f`. A well whose noise draw came out low is handed a *low* variance and is
trusted more; a well that read high is declared imprecise. **Assumed precision is
correlated with the residual**, which inflates apparent structure — a direct candidate
cause of the measured ls ÷ FWHM = 0.56–0.70.

This is *better* for SPADE than the argument it replaces. A replicate-pooled σ̂ is
independent of the individual reading, so Stage 1's replicates fix exactly this. Stage 2
survives with a sharper mechanism, and Task 3 tests it directly rather than assuming it.

### 7.4 One probability revised upward

SPADE puts *"nominal-95% certified regions are materially anti-conservative"* at 0.75.
E3 already measured **latent coverage below nominal 0.95 in every cell, worst 0.7644**
(`docs/RESULTS.md:204`) — and the accompanying sentence, *"the interval a lab would
actually use is roughly trustworthy; the model's belief about the underlying smooth
response is not,"* was written for a point-optimum deliverable. Under a design-space
deliverable it **inverts**: certification is an LCB on **latent f**, so the broken
interval is precisely the certification object. Revised to **0.9**, and it is the free
finding that makes K6 worth running whichever way the rankings fall.
