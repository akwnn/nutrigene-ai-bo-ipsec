# SPADE Go/No-Go Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Do not skip Task 1.** Tasks 2–5 all read campaign observations that this repository does not currently store. Task 1 is the only thing that makes them possible, and its gate result decides the gating policy for every task after it.

**Goal:** Decide, in roughly two days of work and ~15 CPU-hours, whether SPADE is worth building — by running six kill tests against the committed results, four of which need no new experimental design at all.

**Architecture:** One new module (`boec.replay`) regenerates any committed campaign deterministically and returns its observations, gated against the committed regret column. Four scorers then read those observations and answer one kill test each. Two further tasks run genuinely new campaigns. Nothing in `src/boec/` that E2 depends on is modified.

**Tech Stack:** Python 3.11, torch 2.13.0, botorch 0.18.1, gpytorch 1.15.2, numpy 2.4.6, scipy 1.17.1, pytest. Run everything through `.venv/bin/python`; there is no bare `python` on this machine.

## Global Constraints

Copied from this repository's established conventions. Every task's requirements implicitly include this section.

- **Register before you run.** Add the question to `docs/OPEN-QUESTIONS.md` and **commit** before the runner exists. The commit timestamps are checkable and this project cites them. A result from an unregistered runner is not citable.
- **Gate against committed columns, never against a regeneration.** D12: *a gate that compares one fresh run to another can only report that the code agrees with itself.*
- **Tests first.** Write the failing test, run it, watch it fail, then implement. No exceptions.
- **No tolerance tuned on a pilot.** Q54's first gate set rule C at `1e-06` from a 44-value pilot and failed at `2.463e-06` on the full 550-value population. If a tolerance must exist, gate on the **property the number is used for** (does a verdict change), not on the number.
- **Never overwrite a committed result JSON.** New file per question.
- **`.gitignore` uses negations** — every new `results/*.json` needs an explicit `!results/<name>.json` line or it will not be committed.
- **Do not modify** `src/boec/campaign.py`, `src/boec/surrogate.py`, `src/boec/oracles.py`, `src/boec/torch_oracle.py`, or anything under `scripts/run_e2*`. E2 is the committed baseline; changing it invalidates every gate in the project.
- **Commit messages carry no AI attribution or `Co-Authored-By` trailers.**
- Primary cell throughout: `d=6, sigma_rel=0.25, budget=48, q=4`, 25 instances × 2 seeds.

---

## Amendment A — 2026-08-20, after review

Five changes. The execution order below **replaces** the task numbering in the body.

| run order | task | change |
|---|---|---|
| 1 | Task 1 | unchanged — replay + gating policy |
| 2 | **Task 4 (K6)** | **moved ahead of K0/K1**, absorbs `norms.py`, gains A1 and A3 below |
| 3 | Task 2 (K0) | unchanged, but `norms.py` already exists by then |
| 4 | Task 3 (K1) | unchanged |
| 5 | Task 5 (K3) | unchanged |
| 6 | Task 6 (K2) | **redesigned** — paired within-instance SD, see A4 |
| 7 | Task 7 (K4) | unchanged |

**Why K6 moves up.** It decides whether Stages 4–5 exist at all, and it decides whether
K1's calibration numbers are a footnote or the headline. Running K1 first risks spending
3 CPU-hours on a diagnostic whose interpretation is not yet determined.

### A1 — Run Q30's additive-kernel arms through K6

Q30 measured 2× held-out R² buying **Δregret 0.0015, p = 0.71**. If the same campaigns
show a large gain on the probability map, the project gets its cleanest single figure:

> **Doubling surrogate accuracy is worth nothing for choosing a point and a great deal
> for certifying a region.**

One intervention, two deliverables, both arms regenerable. `scripts/run_q30_additive.py`
defines `ARMS = {"qlogei-add": "additive+interaction", "qlogei-addonly": "additive"}` at
`DIM = 6`, both sigmas, 25 instances × 2 seeds — 200 campaigns, roughly 20 minutes.
(`FIDELITY_SUBSAMPLE = 5` applies only to Q30's own gate, not to its arms.)

**One correction to the proposal:** these arms are *not* "already on disk." Nothing is —
that is what Task 1 exists to fix. They are *regenerable*, which is enough.

**Required change to `regenerate()`:** add `kernel_structure: str = "product"`, passed
through to `CampaignConfig`. Arm names `"qlogei-add"` and `"qlogei-addonly"` map to
`"additive+interaction"` and `"additive"`. Gate them against `results/q30-additive.json`
under the Task 1 policy.

**This also pre-empts the obvious objection to K6's primary metric** — that AUC is a
global ranking quantity and may just be re-measuring R². If it tracks R², that is the
finding, not a flaw, and A5's Brier decomposition separates the two halves cleanly.

### A2 — The K6 branch needs a direction, not just divergence

The body's decision tree says "K6 diverges → HEADLINE." That is wrong if clustered BO
wins on all three design-space metrics: still divergence, but a **no-go** for SPADE.
Corrected in the decision tree below.

### A3 — Pre-register what the DoE arm certifies on screened-out factors

**Unhandled gap, and the code makes it sharper than a two-way choice.**

`DoEResult.X_visited` is `(budget, d)` — **full `d` columns** — and `dropped_held_at:
dict[int, float]` pins each discarded factor at a single value (`hold_dropped_at=
"best_stage1"`, the pre-registered primary). So the two screened-out axes carry
**zero design variation across all 27 CCD runs plus the confirmation**.

That is worse than "no data." The likelihood is flat along those axes, so the fitted
lengthscale reverts to the **prior mode 0.5016** — the exact Q25/D8 no-signal attractor
this project already documented — and posterior SD grows toward the prior SD as you move
off the held value. The certified box therefore pinches to a **thin, prior-driven slab**
on those axes. Not zero, not full: an artefact of a BoTorch default.

**Three options, and option (c) is the trap that fires if nobody decides:**

| policy | certified range on a zero-variance axis | argument |
|---|---|---|
| **(a) refuse** | 0 — cannot certify what you did not vary | conservative; makes DoE volume identically 0 |
| **(b) full range** | the whole axis | what a practitioner implicitly assumes; `false_inclusion_rate` exposes it if unsafe |
| **(c) GP's own answer** | thin slab set by prior mode 0.5016 | **happens silently**; not defensible in a batch record |

**Pre-register (b) as primary and (a) as the declared sensitivity, and report (c)
alongside both, labelled as prior-driven.** Reporting (c) is not optional: it is what an
unreflective implementation produces, and naming it is the contribution.

If (b) shows a high false-inclusion rate, that is a clean result standing on its own:

> **Screening is fatal for a design-space deliverable, because a batch record needs a
> range for every factor.** That argument does not exist in the RSM literature and does
> not depend on SPADE winning anything else.

Applies identically to the d=8 arm and to Q59's unscreened Hartmann6 comparison, which
becomes the natural control: it is the only classical arm with variation on every axis.

### A4 — K2 is underpowered as written; pair it

The relative SE of an SD estimate is ≈ `1/sqrt(2(n-1))`. At 20 draws that is **16.2%**
per design type, so a ratio of two SDs carries ≈ **22.9%** relative SE, and detecting a
30% reduction is **1.31 SE**. Not detectable. The arithmetic checks out and the body's
K2 would have produced a null for lack of power, not for lack of effect.

**Fix is pairing, not more draws.** For each instance, draw `D = 20` designs of each type
and compute the **within-instance SD across designs**. That yields 25 paired SD estimates
per design type and a Wilcoxon on the pairs.

**Cost correction, stated honestly:** this is 25 × 20 × 3 × 2 × 2 = **6,000 campaigns**,
25× the body's estimate of 240. `spread_gp` is one-shot so each is cheap, but the cost is
dominated by `constrained_argmax` at `n_restarts=20, raw_samples=4096` — the same
optimiser Q54 found slow. **Measure one campaign's wall time during Task 1 and scale from
it.** Do not carry the body's 6-hour figure forward unchecked.

### A5 — Brier decomposition, and a σ sweep that makes Stage 0 decision-ready

**Decomposition.** Report Murphy's calibration–refinement split, not just the total.
Refinement is close to a ranking quantity and overlaps what Q30 already measured;
**calibration is the new part, and calibration is exactly what E3's 0.7644 latent
coverage says is broken.** Pre-register the binning: **10 equal-count bins** on the
forecast probability, since equal-width bins are near-empty at the extremes on a 20k grid.

**σ sweep.** Report every K6 metric at `σ ∈ {0.25, 0.20, 0.15, 0.10}`. Effective noise
under covariate adjustment is `σ·sqrt(1 − r²)`, so when the lab `r` arrives it is read
off a curve rather than run. Converts a deferred stage into a lookup, for an afternoon.

**Caveat that must travel with it:** committed campaigns exist only at `σ ∈ {0.25, 0.10}`.
**σ = 0.20 and 0.15 are new campaigns and cannot be gated against anything.** Label them
exploratory and keep them out of any confirmatory contrast.

### A6 — Get the lab numbers in parallel *(extended by B5)*

One correlation on an existing Nutrigene plate: day-0 confluence against day-6 endpoint,
across wells. Blocks nothing, costs an afternoon, and with A5 it turns Stage 0 from an
open question into a go/no-go: `r < 0.4` → Stage 0 comes out, σ̂ rests on replicates
alone; `r > 0.7` → Stage 0 is half the variance.

**Second number, added by B5: reagent cost per well**, from Nutrigene's ordering records.
It decides whether the matched-plates argument is decisive or merely suggestive, and it is
the number the product claim rests on. Neither blocks anything; both are an afternoon.

---

## Amendment B — 2026-08-20, second review

Supersedes parts of Amendment A. **A3's primary policy flips.** Three arithmetic
claims were checked; two hold exactly, one does not.

### B0 — What was verified

**Peterson's noise floor holds, and it is the most important number here.**
`D_γ = {x : P(Y ≥ τ | x) ≥ γ}` uses the posterior *predictive*, so it carries `σ²`:

```
P(Y >= tau | x) = Phi( (mu(x) - tau) / sqrt(s(x)^2 + sigma^2) )
```

Set `s = 0` — infinite data, perfect knowledge. Certifying still requires
`mu - tau >= z*sigma`. This repo's noise is **relative** (`y = f(1+eps) + eta`), so the
noise SD scales with `mu` and the floor comes out the same:

```
tau_max = mu_max * (1 - z * sigma_rel)
```

| γ | z | τ_max at s=0 | τ_max at s=0.15 |
|---|---|---|---|
| 0.95 | 1.645 | **0.589** | 0.520 |
| 0.90 | 1.282 | 0.679 | 0.626 |
| 0.80 | 0.842 | 0.789 | 0.755 |
| 0.70 | 0.524 | 0.869 | 0.847 |

All four right-hand values reproduce the proposal's table exactly.

> **At σ_rel = 0.25, no method can certify above τ ≈ 0.59 at γ = 0.95, at any budget,
> ever.** `D_γ` is floored by *process* noise, not estimation noise.

Two consequences. The γ sweep is **not** a robustness check — it is the only thing
keeping the object non-empty. And the product "a 95% assured design space from one
plate" does not exist at this noise level **for anyone**, which is a finding, not a
failure. It is also a design rule: *never make a primary metric that can be identically
zero for every arm.*

**Variance scaling holds, with one correction.** `mean prediction variance = σ²p/n` is
right. But `p = 24` is not this repo's number — `second_order_n_terms(6) = C(8,2) = 28`.
Corrected:

| n | s (p=28) | τ_max, LCB z=1.96 |
|---|---|---|
| 48 | 0.191 | 0.626 |
| **96** | **0.135** | **0.735** |
| 250 | 0.084 | 0.836 |
| 384 | 0.068 | 0.868 |

The proposal's figures (0.755 at n=96) used p=24 and run ~2–3% optimistic. **The
conclusion is unaffected: the empty box is a 48-well artefact, not a fundamental limit.**

**The cost-concentration finding holds. Its stated mechanism does not.**
`SD(c) = 1/sqrt(12d) = 0.1179` at d=6, so ±2SD spans [0.264, 0.736] and
`Phi(-2.121) = 1.69%` of wells fall below cost 0.25 — **0.76 wells out of 48.** Confirmed
by simulation.

But the claim that *"Stein's theorem is exactly what makes LHS blind along the cost
direction"* is **wrong**, and it is the kind of wrong that a reviewer will enjoy.
Measured over 4,000 designs:

| n | SD(c), iid | SD(c), LHS |
|---|---|---|
| 48 | 0.11789 | 0.11776 |
| 96 | 0.11792 | 0.11795 |

**No difference.** LHS does not concentrate cost more than random sampling. Stein's
theorem concerns the variance of a *sample-mean estimator* over the design; the spread of
an additive functional *across design points* is a different quantity, governed by plain
CLT on a sum of `d` bounded coordinates. Drop the reversal. **State it as CLT** — which
is simpler, still true, and applies to every space-filling design including OA-LHS,
maximin and MaxPro:

> Under any space-filling design, fewer than one well in 48 lands in the cheapest quarter
> of the cost range, and that is where the answer lives. This is CLT, not Stein.

### B1 — Three versions, and only one is being planned now

| version | what it is | build when |
|---|---|---|
| **A · map only** | Change no sampling. Re-score committed campaigns on Peterson `D_γ` + cost frontier. | **now — it is K6** |
| **B · two-plate LSE** | A, plus plate 2 spends wells on the `D_γ` boundary by straddle/LSE, not on the peak. | only if A diverges with spread ahead |
| **C · conformal** | B, plus jackknife+/split-conformal bands for finite-sample coverage. | only after B has a result. Paper 3 |

**Do not build current SPADE.** Its Stage 1 (OA-LHS, triplicate anchors, 55 wells), Stage
3 regime detector, and Stage 5 peak confirmation are all dropped from Version A.

### B2 — The scientific object changes

| | was | now |
|---|---|---|
| certified region | `LCB of latent f >= tau`, z=1.96 | **`D_γ = {x : P(Y >= tau | x) >= gamma}`** (Peterson 2008; Peterson & Lief 2010) |
| box | inscribed hyperrectangle over all `d` | **NOR = inscribed box on ACTIVE axes only** (Stockdale & Cheng 2009: design space ≠ normal operating region) |
| plate-2 allocation | confirm the peak | **batch straddle** `argmax 1.96*s(x) - |mu(x) - tau|` (Bryan 2005; Gotovos 2013; Bect 2012) |

`designspace.py` gains `predictive_probability_map(model, X_grid, tau)` alongside
`probability_map`. Both are reported; the difference between them **is** a result, since
the mean-based region is the one E3 showed is anti-conservative.

### B3 — A3 REVERSED: refuse is now primary

Amendment A registered (b) full-range as primary. **That flips.** For an axis with zero
design variation:

| policy | status now |
|---|---|
| **(a) refuse to certify** | **PRIMARY** — a batch record needs a range for every CPP, and you cannot certify a factor you never varied |
| (b) full range | declared sensitivity — what practice implicitly assumes; `false_inclusion_rate` exposes it |
| (c) GP's own prior-driven slab | reported and labelled, because it is what fires silently |

Under (a) the screened DoE arm's NOR is defined **in 4D, not 6D**, and its 6D volume is
identically zero. That is the finding, stated cleanly.

### B4 — Cost frontier: the always-defined deliverable

The structural fact this literature ignores: **recipe cost is known exactly, linearly and
noiselessly**, `c(x) = sum_j w_j x_j` from the catalogue. Zero wells to evaluate. So the
real problem is `minimize c(x) s.t. f(x) >= tau` — the objective is free and all 48 wells
buy the constraint.

Define `G(k) = max{ f(x) : c(x) <= k }`. `G` is **non-decreasing by construction**, and
the whole decision is one threshold crossing `k* = min{k : G(k) >= tau}`. Six-dimensional
noisy argmax becomes **1D monotone threshold crossing**.

**Report the cost-assurance curve** `k*_γ = min{k : P(G(k) >= tau) >= gamma}` swept over
γ ∈ [0.5, 0.99]. Why this is the right primary metric:

| | certified box volume | cheapest certifiable recipe |
|---|---|---|
| can be zero for every arm | **yes** | no, while the peak certifies |
| units | dimensionless | **currency per litre** |
| ranking when empty | undefined | always ordered |

**One trap, flagged by the proposal and real.** `G` is a max over a posterior draw, so a
plug-in estimate is **biased upward** — the same optimizer's-curse mechanism this project
already documented as its identification result, now reappearing *inside the metric*.
Compute `G` by sampling the posterior over the whole curve, never by plugging in the
posterior mean, and report the bias.

### B5 — Matched plates, not matched wells

A 96-well plate costs one scientist-week whether 48 or 96 wells are filled. Reagents scale
with wells; scientist time, incubator slot, cell prep and calendar scale with **plates**.

| | plates | wells | calendar |
|---|---|---|---|
| classical RSM | 3 | 48 | ~6 weeks |
| batch BO | 10 | 48 | ~20 weeks |
| one full plate | **1** | 96 | ~2 weeks |

**Report both axes.** Whether this argument is decisive depends on one number nobody has:
**reagent cost per well from Nutrigene's ordering.** If reagents dominate, the argument
weakens; if scientist-weeks dominate, it is decisive. Added to A6.

**Gating caveat, unchanged from A5:** n=96 campaigns are new and cannot be gated against
any committed column. Exploratory, and kept out of confirmatory contrasts.

### B6 — Screening structurally overpays

**A factor screened as non-significant is precisely the factor to reduce to zero to save
money.** Screening drops it from the model and pins it at its centre level forever, so
classical RSM pays mid-range price for every factor it proved didn't matter.

This is a clean economic argument against a universal practice, it needs no new method,
and **it does not depend on SPADE winning anything.** It is measurable directly on the
committed DoE arm via `dropped_held_at`. Abstract-worthy on its own.

### B7 — Constrained BO is now a required baseline

If the objective becomes cost-constrained, **constrained BO is the fair comparator and
must be in the paper.** It may win at matched wells. If it does, the finding is "nobody in
bioprocess runs constrained BO, and here is what it is worth", plus the rounds/plates win
— thinner, still publishable. Do not omit it and hope nobody asks.

### B8 — What is now explicitly NOT built

- OA-LHS vs maximin vs MaxPro as a *stage* (old K2). B0 shows the cost-blindness is CLT and hits every space-filling design equally, so this is a **sensitivity, not a mechanism**. Demote K2; keep A4's paired design only if K6 justifies it
- Interior triplicate anchors — σ̂ is a calibration footnote once `Yvar` is known
- The regime detector (old K4) as a *gate*; report `D_γ` disconnectedness on deceptive families instead of switching acquisition
- NUTS, I-splines, shape constraints — closed by Q30 unless K0 reopens the L∞ channel

---

## Amendment C — 2026-08-20, pre-flight checks

Two checks run before starting. One confirms the proposal exactly. **One kills B4.**

### C0 — The regret column is closed. Confirmed, all six figures.

Read from `results/q57-search-vs-id.json`:

| d=6 | rule A | oracle-best (search floor) | identification gap |
|---|---|---|---|
| classical, σ=0.25 | 0.0958 | **0.0597** | **0.0361** |
| qLogEI, σ=0.25 | 0.1553 | **0.0755** | 0.0797 |
| classical, σ=0.10 | 0.0892 | 0.0544 | **0.0348** |

Cutting noise 60% moved the classical identification gap 0.0361 → 0.0348 — **0.0013**,
because the top design points differ by δ ≪ σ and the campaign sits on the flat part of
`Phi(-delta / (sigma*sqrt(2)))`. Against a SESOI of 0.02, **nothing wins on regret.**
Any spec claiming otherwise gets caught.

**One correction to the proposal.** *"Floor is roughly 0.085 to 0.090"* is a σ=0.25
statement. At σ=0.10, qLogNEI already achieves **rule A = 0.0808**, below that floor, and
its search floor is 0.0435. State the floor per cell, not globally.

### C1 — B4 IS DEAD: the cost frontier has no test bed

The cost-assurance curve was made co-primary on the premise that the yield optimum is
expensive, so `min c(x) s.t. f(x) >= tau` has a binding constraint. **Measured across
every family in the repo, it does not.**

| family | `c(x*)` = mean coordinate at the true optimum | lever? |
|---|---|---|
| **hill** (the primary oracle) | **0.355** | none — already cheap |
| **hartmann6** | **0.345** | none — already cheap |
| ackley | 0.500 | none — exactly the design average |
| levy | 0.550 | negligible |
| rosenbrock | 0.744 | real, but see below |

A space-filling design averages `c = 0.500`. **Four of five families put the optimum at
or below that.** Hill's optimum is in the cheap half on *every one* of its six
coordinates (per-coordinate medians 0.30–0.38, range 0.221–0.604).

**Skewed prices do not rescue it.** At 100× weight on one factor, Hill's median `c(x*)`
moves 0.355 → 0.357, because that factor's optimum is low too.

**Rosenbrock is not a counterexample.** Its optimum is at 0.744 in *every* coordinate —
it is symmetric, so its cost problem collapses to a 1D radial profile, not a genuine 6D
constrained problem. Same for ackley (0.5 everywhere) and levy (0.55 everywhere).

**Cause:** the Hill oracle is biphasic — each factor rises then falls, and the interior
peak sits below midrange because too much growth factor is inhibitory. That is realistic
biology, and it makes *"the optimum is expensive"* a false premise on the one landscape
family built to resemble the application.

**Decision: B4 is demoted from co-primary metric to a reported negative result.**

> Across five landscape families — including a biology-motivated biphasic oracle and the
> standard deceptive benchmark — the yield optimum already sits at or below median recipe
> cost. Cost-constrained optimisation is therefore **not** the binding problem the framing
> assumes.

That is worth one paragraph and it saves building the entire apparatus. Rescuing B4 would
require a new oracle whose optimum is expensive and asymmetric — **building a test bed to
make the method look good, which is precisely what this project exists to warn against.**
Do not do it. If Nutrigene's real data later shows an expensive optimum, B4 returns with
evidence behind it.

**Consequence for K6:** it is now purely the **map** question — Brier/AUC and IoU of
`D_γ` against the true superlevel set. B4 no longer supplies the always-defined metric,
so the γ sweep in B0 is doing that job alone, and the empty-region count must be reported
explicitly.

### C2 — The registered τ grid was self-defeating. Fixed.

A5 registered τ ∈ {0.70, 0.80, 0.85, 0.90}. B0 then proved
`tau_max = mu_max(1 - z*sigma_rel)` = **0.483–0.589 at γ=0.95**. Every registered τ
exceeds it, so at γ=0.95 **every arm returns empty at every τ** — a guaranteed table of
zeros, written into the pre-registration across two amendments without reconciling them.

**Re-registered relative to the floor**, so the grid is feasible by construction:

```
tau_frac in {0.60, 0.75, 0.85, 0.95}   of tau_max(gamma, s_typical)
```

with `s_typical = 0.19` (= `sigma*sqrt(p/n)` at p=28, n=48). Absolute τ is then reported
alongside for readability. Pre-register `tau_frac`, never absolute τ — the proposal's own
warning applies: *moderate τ favours spread, τ near the peak favours clustered BO, do not
pick after seeing the table.*

### C3 — The "good at both" tweaks: four in, one dead

| tweak | verdict |
|---|---|
| **1 · dual deliverable from one posterior** | **IN.** Free bookkeeping. Setpoint *and* `D_γ` + NOR from one fit, zero extra wells |
| **2 · split plate 2 boundary/peak 70:30** | **IN, with a caveat.** Q58 measured peak confirmation *hurting* the spread arm (0.0958 → 0.1437), so the 30% may be actively wasted. Register 70:30 as primary and **100:0 as the declared sensitivity** |
| **3 · setpoint inside the certified box** | **IN.** The one genuine trade, and it is favourable: a point you cannot certify a neighbourhood around is not manufacturable |
| **4 · cost frontier as shared metric** | **DEAD.** See C1 |
| **5 · drop triplicates, keep covariate** | **IN.** Triplicates estimate the floor; knowing a floor better does not raise it. The covariate *lowers* it via `sigma_eff = sigma*sqrt(1 - R^2)` |

### C4 — The catch, restated because it governs everything

Regret parity is **already measured** — Q54, one-shot spread tying 10-round qLogEI on
non-deceptive families. So the optimisation half of "good at both" is in the bag **and is
not new.** Everything new is on the design-space side, and with B4 dead that means the
map alone.

**K6 still decides whether the paper exists.** If the design-space ranking matches the
regret ranking, no amount of deliverable tweaking saves it.

---

## Amendment D — Version B, the two-plate arm. THE DECISIVE TEST.

**Why this exists.** K6 and K6b tested **plate 1 only** (Version A, no sampling change).
That was the registered gate and running it was correct. But SPADE v2 is a **two-plate**
method — its own spec says *"the certificate is 2 rounds by default; one round is the map,
not the batch record"* — so concluding from plate 1 that SPADE fails is judging a
two-stage method on stage one. **Plate 2 is the machinery designed to repair a weak
certified region, and it has not been run.**

What plate 1 established, and its limit:

| established | not established |
|---|---|
| screening is fatal for a design space (24/24) | whether plate 2 closes the gap |
| the two objects rank differently (0/24, 0/4) | whether SPADE beats qLogNEI |
| joint certification is honest at n=48 | anything on the rounds axis |
| one-shot spread loses to qLogNEI (15/24) | |

**And the rounds axis has been under-reported throughout.** Every K6 contrast is at equal
*wells*. Plate 1 is **1 round against 10**; Version B is **2 against 10**. Even a tie on
the map is a 5x rounds result, and rounds was one of the three original claims.

### Task 8: the plate-2 LSE arm

**Files:**
- Create: `src/boec/lse.py`, `tests/test_lse.py`, `scripts/run_versionb.py`
- Modify: `docs/OPEN-QUESTIONS.md`, `.gitignore`

**Interfaces:**
- Consumes: `boec.vorobev` (`excursion_probability`, `vorobev_deviation`,
  `conservative_estimate`), `boec.designspace.gp_adapter`, `boec.replay.regenerate`
- Produces:
  - `straddle_score(mean, sd, theta) -> Tensor` — `1.96*sd - |mean - theta|` (Bryan 2005)
  - `batch_lse(model, X_cand, theta, q, *, exclude) -> Tensor` — q points, greedy with a
    lengthscale-scaled exclusion radius so a batch does not collapse onto one location
  - `plate_two(rec, orc, theta, n_wells) -> CampaignRecord` — returns the **combined**
    campaign, first and confirmation readings **averaged**, never replaced

- [ ] **Step 1: Register, and commit before the runner exists**

```markdown
**Version B.** Plate 1 = 40 wells space-filling. Plate 2 = 8 wells by batch LSE on the
D_gamma boundary, decided by the MEAN of first and confirmation readings. Total 48, so it
is budget-matched to every committed column and to plate-1-only at 48. Comparators:
qLogNEI at 10 rounds (the arm that actually beats plate 1), doe_ascent, plate-1-only at
48, and **8 RANDOM wells instead of LSE**. Reported on BOTH axes, wells and rounds.
Winner not pre-written.

Registered kills: (i) plate 2 does not close the map/alpha* gap to qLogNEI -> SPADE is
dead; (ii) plate 2 does not beat 8 random wells -> the SUR machinery is not earning its
place and the honest result is "a second plate helps, the criterion does not".

Correction carried from the research pass: the optimal SUR points are NOT all on the
boundary. Azzimonti's own figures place some deep in the interior, to secure regions a
boundary-only rule leaves uncertain. The criterion decides for itself; do not hard-code a
boundary-only rule.
```

- [ ] **Step 2: Write the failing test**

```python
import torch
from boec.lse import batch_lse, straddle_score


def test_straddle_peaks_at_the_threshold_where_uncertainty_is_equal():
    mean = torch.tensor([0.5, 0.9, 0.1], dtype=torch.double)
    sd = torch.full((3,), 0.1, dtype=torch.double)
    s = straddle_score(mean, sd, theta=0.5)
    assert int(torch.argmax(s)) == 0


def test_straddle_prefers_the_uncertain_point_at_equal_distance():
    mean = torch.tensor([0.6, 0.6], dtype=torch.double)
    sd = torch.tensor([0.05, 0.30], dtype=torch.double)
    assert int(torch.argmax(straddle_score(mean, sd, theta=0.5))) == 1


def test_batch_lse_does_not_collapse_onto_one_location():
    """A greedy batch on a smooth score picks q near-identical points unless excluded."""
    torch.manual_seed(0)
    X = torch.rand(500, 3, dtype=torch.double)

    class _M:
        def posterior_mean_and_sd(self, Z):
            m = 1.0 - Z[:, 0].double()
            return m, torch.full_like(m, 0.2)

    picks = batch_lse(_M(), X, theta=0.5, q=4, exclude=0.15)
    assert picks.shape == (4, 3)
    d = torch.cdist(picks, picks) + torch.eye(4, dtype=torch.double) * 9
    assert float(d.min()) >= 0.15


def test_batch_lse_can_place_points_off_the_boundary():
    """Azzimonti's figures put some SUR points in the interior. A boundary-only rule is
    an approximation and must not be hard-coded."""
    torch.manual_seed(0)
    X = torch.rand(500, 2, dtype=torch.double)

    class _M:
        def posterior_mean_and_sd(self, Z):
            m = 1.0 - Z[:, 0].double()
            sd = torch.where(Z[:, 1] > 0.8, 0.9, 0.02).double()   # a far-from-boundary blob
            return m, sd

    picks = batch_lse(_M(), X, theta=0.5, q=4, exclude=0.15)
    assert bool((picks[:, 1] > 0.8).any()), "criterion never left the boundary"
```

- [ ] **Step 3: Run it, watch it fail**

```bash
.venv/bin/python -m pytest tests/test_lse.py -v
```
Expected: `ModuleNotFoundError: No module named 'boec.lse'`.

- [ ] **Step 4: Implement, then re-run until green**

`straddle_score` is `1.96*sd - (mean - theta).abs()`. `batch_lse` picks greedily, masking
a Chebyshev ball of radius `exclude` around each pick. Default `exclude` from the fitted
median ARD lengthscale divided by 4, **read from the model, never hardcoded**.

- [ ] **Step 5: Run Version B, then commit**

```bash
.venv/bin/python scripts/run_versionb.py --dim 6 --sigma 0.25 2>&1 | tee results/versionb.log
```

**Budget arithmetic, and it must not drift:** 40 + 8 = 48. The confirmation budget comes
**out of** the design, never on top. Any comparison that adds wells is not budget-matched
and must not be reported as a headline.

---

## Amendment E — Version B v2. Four fixes, one of which can invalidate the v1 verdict.

Version B v1 (Task 8, Amendment D) ran. **Do not read its result until these are
addressed** — two of the four were measured and confirmed before this was written.

### E1 — The acquisition surface may be FLAT at n=40. This is the one that matters.

Measured neighbour density per fitted lengthscale (ell=0.42, d=6, 300 designs each):

| n | neighbours |
|---|---|
| 48 | 0.487 |
| **44** | **0.438** |
| **40** | **0.378** |

At 0.378, `s(x)` sits near the prior almost everywhere, so it is nearly **flat**. And
`sqrt(s^2 + sigma^2)` is then ~0.3, a third of the response range, so the distance term
`|mu - theta|` is nearly flat too. **The straddle surface goes flat and the 8 wells get
chosen by numerical noise plus the exclusion radius — which is a space-filling draw.**

If that happens, Version B returns *"LSE ties random"* and it would be read as **"the
criterion does not work"** when the truth is **"the criterion had no signal to act on at
this density."** Those are different findings and only one of them is about the method.

**Fix, ~20 lines.** Before selecting plate 2, compute the acquisition surface's relative
dispersion `SD(a(x)) / |mean(a(x))|` on the candidate grid, log it per campaign, and
**pre-register a threshold** below which the campaign reports *"acquisition uninformative
at this density"* rather than silently contributing a null to the contrast. Report the
fraction of campaigns in that state. **A finding either way.**

### E2 — The exclusion radius is INERT. Measured, not suspected.

`exclusion_radius` returns `median_lengthscale / 4` = **0.105** Chebyshev at ell=0.42.
Measured over 2,000 random 8-point batches in 6D: the median minimum pairwise Chebyshev
distance is **0.320**, and the exclusion binds in **0% of them**.

So the diversity mechanism does nothing and `batch_lse` is **top-8 by score**. That is not
necessarily wrong — but it is not what the module docstring claims, and it means the
"greedy batch collapses without exclusion" argument is untested at this dimension.

**Fix.** Log the achieved minimum pairwise distance per batch. If it stays far above the
radius, either raise the radius on a stated rule or **delete the mechanism and say the
batch is top-q by score** — do not keep a docstring describing machinery that never fires.

### E3 — A 44+4 arm, because a 40+8 loss is currently uninterpretable.

Only 40+8 is registered. If it loses, there is no way to tell whether the problem is
**the criterion** or **the 8 wells taken out of plate 1** — plate 1 drops from 0.487 to
0.378 neighbours, which E1 says may be the difference between a usable and a flat
acquisition surface. 44+4 costs one extra arm and separates the two explanations.

### E4 — The arms must share a common prefix.

Nothing in v1 pairs the branches. They should: run plate 1 to 40 wells, **store the
state**, then branch into LSE-8, random-8 and continue-spread-8 from **identical first 40
wells and an identical noise stream**. That is the variance-reduction argument that
already works elsewhere in this project, and against a SESOI of 0.02 with effects that may
themselves be ~0.02, it could be the difference between a verdict and an inconclusive.

### E5 — Which gamma does plate 2 target? Register it.

`straddle_score` takes one `theta`, and C2 registers tau as a fraction of `tau_max(gamma)`.
Plate 2 can only aim at one boundary while K6 scores across four. **Optimising for
gamma=0.95 and scoring at gamma=0.50 is a self-inflicted handicap.** v1 targeted
`tau_frac = 0.75` with the threshold `theta = tau_frac * mu_max`, which by C2's algebra is
gamma-invariant — so v1 is defensible — but this must be **stated in the write-up**, not
left implicit, and the alternative (run plate 2 once per gamma) should be priced.

### E6 — sigma convention in the straddle.

`predictive_probability_map` requires `sigma` as an array (`sigma_rel * mean`) because the
noise here is relative; a scalar silently answers a homoscedastic question. **v1's
straddle uses the GP's `sd` alone**, which is the estimation term only. That is correct
for Bryan's straddle as published, but it means plate 2 targets the **latent** contour
while the deliverable is the **predictive** region. Register which one is intended.

---

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `src/boec/replay.py` | Deterministically regenerate a committed campaign; return `(X, Y, Yvar)` + provenance. **Nothing else.** | 1 |
| `tests/test_replay.py` | Regeneration matches committed `regret` | 1 |
| `scripts/run_k1_replay_gate.py` | Runs the gate over all 1300 committed rows, writes the gating policy | 1 |
| `src/boec/norms.py` | `sup_err`, grid `r2`, on a Sobol grid against known truth | 2 |
| `tests/test_norms.py` | Both metrics on analytic cases | 2 |
| `scripts/run_k0_norms.py` | K0 — which norm governs regret | 2 |
| `scripts/run_k1_noise_ceiling.py` | K1 — σ ceiling **and** the `yvar`-coupling diagnosis | 3 |
| `src/boec/designspace.py` | Probability map, certified volume curve, inscribed hyperrectangle | 4 |
| `tests/test_designspace.py` | Box expansion and volume on analytic cases | 4 |
| `scripts/run_k6_designspace.py` | K6 — does the deliverable reverse the ranking | 4 |
| `scripts/run_k3_confirm_average.py` | K3 — confirm-and-average vs confirm-and-replace | 5 |
| `src/boec/oa_design.py` | Strength-2 OA-LHS + maximin fallback + anchors | 6 |
| `tests/test_oa_design.py` | Stratification and anchor properties | 6 |
| `scripts/run_k2_design_lottery.py` | K2 — design lottery | 6 |
| `scripts/run_k4_deception.py` | K4 — frozen regime detector | 7 |

---

## Task 1: Campaign replay and the gating policy

**This is the unlock.** No committed result file stores `X` or `Y`. Verified: `results/e2-grid.json` rows are `[instance, dim, sigma, seed, arm, best, regret, auc_post_init]`; Q42, Q57, Q58 and d20 are likewise scalar summaries only. Every "re-score the stored campaigns" test in the SPADE note is therefore a **regenerate-and-score**, and the regeneration must be gated.

`Campaign.state_dict()` already persists `train_X`, `train_Y`, `train_Yvar` and `rng_state` — the runners simply never called `save()`. Regeneration is cheap: stored `secs` in `results/q57-search-vs-id.json` give ~6 s per campaign, so 1300 rows is about 1 CPU-hour.

**Files:**
- Create: `src/boec/replay.py`
- Create: `tests/test_replay.py`
- Create: `scripts/run_k1_replay_gate.py`
- Modify: `.gitignore` (add `!results/k1-replay-gate.json`)
- Modify: `docs/OPEN-QUESTIONS.md` (register K-series)

**Interfaces:**
- Consumes: `boec.campaign.Campaign`, `boec.campaign.CampaignConfig`, `boec.optimizers.AcqConfig`, `boec.torch_oracle.BiphasicOracle`, `boec.oracles.load_ensemble`, `run_e2.scored_curve`, `run_e2.unit_bounds`
- Produces:
  - `CampaignRecord` dataclass with fields `X: Tensor (n,d)`, `Y: Tensor (n,1)`, `Yvar: Tensor (n,1)`, `instance: str`, `dim: int`, `sigma: float`, `seed: int`, `arm: str`, `regret: float`, `optimum_value: float`
  - `regenerate(instance, dim, sigma, seed, arm) -> CampaignRecord`
  - `committed_rows(path="results/e2-grid.json") -> list[dict]`

- [ ] **Step 1: Register the question, and commit before the runner exists**

Append to `docs/OPEN-QUESTIONS.md`:

```markdown
## K-series — SPADE go/no-go

**K1-gate.** No committed result file stores campaign observations. Can a campaign
be regenerated from `(instance, dim, sigma, seed, arm)` such that its scored regret
reproduces `results/e2-grid.json` exactly? Registered before `src/boec/replay.py`
exists. The **measured** worst per-arm |delta| becomes the gating policy for K0, K1,
K3 and K6. Winner not pre-written: arms whose acquisition runs through multi-start
L-BFGS-B may not be bit-reproducible (cf. Q54 rule C, worst |delta| 2.463e-06), and
if so those arms get Q54's verdict-invariance treatment rather than a raised constant.
```

```bash
git add docs/OPEN-QUESTIONS.md
git commit -m "Register the K-series go/no-go questions before any runner exists"
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_replay.py`:

```python
"""Regeneration must reproduce the committed column, not merely agree with itself."""
import json
from pathlib import Path

import pytest

from boec.replay import CampaignRecord, committed_rows, regenerate

GRID = Path("results/e2-grid.json")


def _primary_rows(arm, n=3):
    rows = [r for r in committed_rows(GRID)
            if r["dim"] == 6 and r["sigma"] == 0.25 and r["arm"] == arm]
    assert rows, f"no committed rows for arm={arm}"
    return rows[:n]


def test_regenerate_returns_observations_of_the_right_shape():
    row = _primary_rows("doe")[0]
    rec = regenerate(row["instance"], row["dim"], row["sigma"], row["seed"], row["arm"])
    assert isinstance(rec, CampaignRecord)
    assert rec.X.shape == (48, 6)
    assert rec.Y.shape == (48, 1)
    assert rec.Yvar.shape == (48, 1)


def test_doe_arm_reproduces_committed_regret_exactly():
    """The DoE arm has no acquisition optimiser, so exact equality is the right bar."""
    for row in _primary_rows("doe"):
        rec = regenerate(row["instance"], row["dim"], row["sigma"],
                         row["seed"], row["arm"])
        assert rec.regret == pytest.approx(row["regret"], abs=0.0), (
            f"{row['instance']} seed={row['seed']}: "
            f"regenerated {rec.regret!r} != committed {row['regret']!r}"
        )


def test_unknown_arm_raises_rather_than_guessing():
    with pytest.raises(ValueError, match="unknown arm"):
        regenerate("ce7334da318bc5e5", 6, 0.25, 0, "not_an_arm")
```

- [ ] **Step 3: Run it and watch it fail**

```bash
.venv/bin/python -m pytest tests/test_replay.py -v
```

Expected: `ModuleNotFoundError: No module named 'boec.replay'` — all three tests error.

- [ ] **Step 4: Implement `src/boec/replay.py`**

```python
"""Regenerate a committed campaign and hand back its observations.

WHY THIS EXISTS
---------------
No file in ``results/`` stores ``X`` or ``Y``. ``results/e2-grid.json`` rows carry
``[instance, dim, sigma, seed, arm, best, regret, auc_post_init]`` and nothing else.
Every downstream question in the K-series -- which norm governs regret, what a
replicate-identified sigma buys, what a certified design space looks like -- needs the
observations, so they have to be regenerated.

**This module reproduces; it never re-derives.** The regret it returns is computed by
the same two lines ``run_e2.py`` used (``scored_curve`` then
``optimum_value - curve[-1]``), so a mismatch means the regeneration is wrong, not that
the definition drifted. Callers gate on that mismatch before reading anything else.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import Tensor

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from boec.campaign import Campaign, CampaignConfig
from boec.doe import run_doe_arm
from boec.optimizers import AcqConfig
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle
from run_e2 import BUDGET, scored_curve, unit_bounds

__all__ = ["CampaignRecord", "committed_rows", "regenerate"]

#: Arms whose acquisition never calls an optimiser, so exact equality is the right bar.
DETERMINISTIC_ARMS = ("doe",)
#: Arms routed through multi-start L-BFGS-B. Q54 measured these at ~1e-06 reproducibility.
OPTIMISED_ARMS = ("qlogei", "qlognei")


@dataclass(frozen=True)
class CampaignRecord:
    X: Tensor
    Y: Tensor
    Yvar: Tensor
    instance: str
    dim: int
    sigma: float
    seed: int
    arm: str
    regret: float
    optimum_value: float


def committed_rows(path: str | Path = "results/e2-grid.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def _instance(instance: str, dim: int):
    for inst in load_ensemble(dim):
        if inst.instance_id == instance:
            return inst
    raise KeyError(f"instance {instance!r} not in the d={dim} ensemble")


def regenerate(instance: str, dim: int, sigma: float, seed: int,
               arm: str) -> CampaignRecord:
    """Re-run one committed campaign and return what it measured."""
    inst = _instance(instance, dim)
    bounds = unit_bounds(dim)
    orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)

    if arm in OPTIMISED_ARMS:
        cfg = CampaignConfig(d=dim, budget=BUDGET, q=4, seed=seed,
                             acq=AcqConfig(kind=arm))
        c = Campaign(orc, bounds, cfg)
        c.run()
        X, Y, Yvar = c.train_X, c.train_Y, c.train_Yvar
    elif arm in DETERMINISTIC_ARMS:
        r = run_doe_arm(orc, bounds, truth=orc.truth, budget=BUDGET, seed=seed)
        X, Y = r.X_visited, r.Y_visited
        Yvar = orc.evaluate(X)[1]
    else:
        raise ValueError(f"unknown arm {arm!r}; expected one of "
                         f"{DETERMINISTIC_ARMS + OPTIMISED_ARMS}")

    curve = scored_curve(orc, X, Y)
    return CampaignRecord(
        X=X, Y=Y, Yvar=Yvar, instance=instance, dim=dim, sigma=sigma, seed=seed,
        arm=arm, regret=float(inst.optimum_value - curve[-1]),
        optimum_value=float(inst.optimum_value),
    )
```

- [ ] **Step 5: Run the tests and watch them pass**

```bash
.venv/bin/python -m pytest tests/test_replay.py -v
```

Expected: 3 passed. If `test_doe_arm_reproduces_committed_regret_exactly` fails, **stop and report** — a DoE arm that will not reproduce exactly means either the ensemble load order or the seeding convention has drifted, and every downstream task is unsafe until that is understood.

- [ ] **Step 6: Measure the gating policy over all 1300 rows**

Create `scripts/run_k1_replay_gate.py`:

```python
"""K1-gate: the measured reproducibility of every committed arm.

Its OUTPUT is a policy, not a verdict. Whatever the per-arm worst |delta| turns out
to be is what K0, K1, K3 and K6 must gate against. Registered before this file existed.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from boec.replay import committed_rows, regenerate

OUT = Path("results/k1-replay-gate.json")
ARMS = ("doe", "qlogei", "qlognei")


def main() -> None:
    rows = [r for r in committed_rows() if r["arm"] in ARMS]
    worst: dict[str, float] = defaultdict(float)
    exact: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    for r in rows:
        rec = regenerate(r["instance"], r["dim"], r["sigma"], r["seed"], r["arm"])
        delta = abs(rec.regret - r["regret"])
        worst[r["arm"]] = max(worst[r["arm"]], delta)
        exact[r["arm"]] += int(delta == 0.0)
        total[r["arm"]] += 1
        print(f"{r['arm']:8s} {r['instance']} d={r['dim']} s={r['sigma']} "
              f"seed={r['seed']} delta={delta:.3e}")

    policy = {
        arm: {"rows": total[arm], "exact": exact[arm], "worst_abs_delta": worst[arm],
              "gate": "exact" if worst[arm] == 0.0 else "verdict-invariance"}
        for arm in ARMS
    }
    OUT.write_text(json.dumps({"policy": policy}, indent=2))
    for arm, p in policy.items():
        print(f"{arm:8s} {p['exact']}/{p['rows']} exact, worst "
              f"{p['worst_abs_delta']:.3e} -> {p['gate']}")


if __name__ == "__main__":
    main()
```

```bash
.venv/bin/python scripts/run_k1_replay_gate.py 2>&1 | tee results/k1-replay-gate.log
```

Expected: ~1 CPU-hour. `doe` should be `0.000e+00` exact on every row.

**Read the result before proceeding.** If `qlogei`/`qlognei` are also exact, every downstream task gates at |Δ|=0. If they are not, they get Q54's treatment: gate on whether a **verdict** changes under a ±(worst delta) shift, with a ceiling far below the effect being measured. **Do not raise a constant to make a gate pass.**

- [ ] **Step 7: Commit**

```bash
printf '!results/k1-replay-gate.json\n!results/k1-replay-gate.log\n' >> .gitignore
git add src/boec/replay.py tests/test_replay.py scripts/run_k1_replay_gate.py \
        results/k1-replay-gate.json results/k1-replay-gate.log .gitignore
git commit -m "Replay committed campaigns and measure the per-arm gating policy"
```

---

## Task 2: K0 — which norm governs regret

**Decides:** whether the deleted Stage 2 of `ODIN-SPEC.md` may return. Q30 measured that doubling held-out R² moved regret by 0.0015 (p=0.71), which closes the L² channel. If `sup_err` governs regret and R² does not, Q30 improved the wrong norm and a model that improves the right one is still live. If R² governs at least as strongly, the L∞ thesis is dead and Stage 2 stays deleted permanently.

**Files:**
- Create: `src/boec/norms.py`, `tests/test_norms.py`, `scripts/run_k0_norms.py`
- Modify: `.gitignore`, `docs/OPEN-QUESTIONS.md`

**Interfaces:**
- Consumes: `boec.replay.regenerate`, `boec.surrogate.build_gp`
- Produces: `sup_err(model, truth_fn, X_grid) -> float`, `grid_r2(model, truth_fn, X_grid) -> float`, `sobol_grid(dim, n, seed) -> Tensor`

- [ ] **Step 1: Register**

Append to `docs/OPEN-QUESTIONS.md`, then commit:

```markdown
**K0.** Across the committed campaigns, does realised regret correlate more strongly
with sup-norm surrogate error or with grid R-squared? Statistic fixed before any number
is read: Spearman rho of each against regret, and a paired bootstrap (10,000 resamples,
instance-level) on the DIFFERENCE of the two rho values. Grid: 20,000 Sobol points, seed
0. Decision: if the bootstrap interval on rho(r2) - rho(sup_err) excludes zero in favour
of r2, the L-infinity thesis is refuted and ODIN Stage 2 stays deleted. If it excludes
zero in favour of sup_err, Stage 2 returns with its own gate. An interval containing
zero is reported as "neither norm dominates" and Stage 2 stays deleted on the Q30
evidence alone.
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_norms.py`:

```python
import torch

from boec.norms import grid_r2, sobol_grid, sup_err


class _Constant:
    """Stand-in for a fitted model: posterior mean is a fixed offset from truth."""

    def __init__(self, offset):
        self.offset = offset

    def posterior_mean(self, X):
        return torch.full((X.shape[0], 1), float(self.offset), dtype=torch.double)


def _zero_truth(X):
    return torch.zeros((X.shape[0], 1), dtype=torch.double)


def test_sup_err_is_the_max_absolute_deviation():
    grid = sobol_grid(3, 256, seed=0)
    assert sup_err(_Constant(0.25), _zero_truth, grid) == 0.25


def test_sup_err_is_zero_for_a_perfect_model():
    grid = sobol_grid(3, 256, seed=0)
    assert sup_err(_Constant(0.0), _zero_truth, grid) == 0.0


def test_grid_r2_is_negative_when_the_model_is_worse_than_the_mean():
    """Truth varies, model is constant and wrong: R^2 must go negative, not clamp."""
    grid = sobol_grid(2, 512, seed=0)

    def truth(X):
        return X[:, :1].double()

    assert grid_r2(_Constant(5.0), truth, grid) < 0.0


def test_sobol_grid_is_deterministic_in_its_seed():
    assert torch.equal(sobol_grid(4, 128, seed=7), sobol_grid(4, 128, seed=7))
    assert not torch.equal(sobol_grid(4, 128, seed=7), sobol_grid(4, 128, seed=8))
```

- [ ] **Step 3: Run it and watch it fail**

```bash
.venv/bin/python -m pytest tests/test_norms.py -v
```

Expected: `ModuleNotFoundError: No module named 'boec.norms'`.

- [ ] **Step 4: Implement `src/boec/norms.py`**

```python
"""The two competing error norms, computed against known truth on a fixed grid.

The claim under test is that terminal regret is governed by sup-norm surrogate error
and NOT by L2 accuracy. Q30 already measured the L2 half: an additive kernel doubled
held-out R-squared and moved regret by 0.0015, p=0.71. This module supplies the other
half so the two can be compared on the same campaigns.

``grid_r2`` is deliberately NOT clamped at zero. A model worse than predicting the mean
has negative R-squared, and clamping would hide exactly the campaigns where the
comparison is most informative.
"""

from __future__ import annotations

import torch
from torch import Tensor
from torch.quasirandom import SobolEngine

__all__ = ["grid_r2", "sobol_grid", "sup_err"]


def sobol_grid(dim: int, n: int, seed: int = 0) -> Tensor:
    """``(n, dim)`` scrambled Sobol points in the unit box, deterministic in ``seed``."""
    return SobolEngine(dimension=dim, scramble=True, seed=seed).draw(n).double()


def _mean_and_truth(model, truth_fn, X_grid: Tensor) -> tuple[Tensor, Tensor]:
    with torch.no_grad():
        if hasattr(model, "posterior_mean"):
            mean = model.posterior_mean(X_grid)
        else:
            mean = model.posterior(X_grid).mean
    return mean.reshape(-1).double(), truth_fn(X_grid).reshape(-1).double()


def sup_err(model, truth_fn, X_grid: Tensor) -> float:
    """``max_x |E[f(x)] - f(x)|`` over the grid."""
    mean, truth = _mean_and_truth(model, truth_fn, X_grid)
    return float((mean - truth).abs().max())


def grid_r2(model, truth_fn, X_grid: Tensor) -> float:
    """``1 - SS_res / SS_tot`` against truth on the grid. Unclamped."""
    mean, truth = _mean_and_truth(model, truth_fn, X_grid)
    ss_res = ((truth - mean) ** 2).sum()
    ss_tot = ((truth - truth.mean()) ** 2).sum()
    return float(1.0 - ss_res / ss_tot)
```

- [ ] **Step 5: Run the tests and watch them pass**

```bash
.venv/bin/python -m pytest tests/test_norms.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Write and run the K0 runner**

Create `scripts/run_k0_norms.py`. For every committed `(instance, seed)` at `d=6, sigma=0.25` and every arm in `("doe", "qlogei", "qlognei")`: regenerate, gate the regret against the committed value under the Task 1 policy, fit `build_gp(rec.X, rec.Y, rec.Yvar, bounds)`, then compute `sup_err` and `grid_r2` on `sobol_grid(6, 20_000, seed=0)` against `orc.truth`. Write rows to `results/k0-norms.json`, then report `spearmanr` of each against regret plus a 10,000-resample instance-level paired bootstrap on the rho difference.

```bash
.venv/bin/python scripts/run_k0_norms.py 2>&1 | tee results/k0-norms.log
```

- [ ] **Step 7: Commit**

```bash
printf '!results/k0-norms.json\n!results/k0-norms.log\n' >> .gitignore
git add src/boec/norms.py tests/test_norms.py scripts/run_k0_norms.py \
        results/k0-norms.json results/k0-norms.log .gitignore
git commit -m "K0: measure whether sup-norm or R-squared governs terminal regret"
```

---

## Task 3: K1 — the noise ceiling, and the `Yvar` coupling defect

**Decides:** whether SPADE Stage 1 should spend 6 of 55 wells on replicates.

**A correction that changes this task's design.** `SPADE-SPEC.md` Stage 2 argues the GP under-smooths (measured ls ÷ FWHM = 0.56–0.70) *"because MAP fits lengthscale and noise jointly."* **It does not.** `build_gp`'s docstring states `train_Yvar` is *"always required, never optional"* — observation noise is supplied as known, per point, and is not a free parameter. That mechanism is not available.

The live mechanism is different and testable. `BiphasicOracle.evaluate` returns
`_plug_in_yvar(y, ...)` = `y**2 * sigma_rel**2 + sigma_add**2`, computed from **the noisy reading `y`, not from `f`**. So a well whose noise draw came out low is handed a *low* variance and the GP trusts it more; a well that read high is declared imprecise. Assumed precision is correlated with the residual, which inflates apparent structure — a direct candidate cause of under-smoothing, and precisely what a replicate-pooled σ̂ (independent of the individual reading) would fix.

This task tests the ceiling and the mechanism together, on the same campaigns.

**Files:**
- Create: `scripts/run_k1_noise_ceiling.py`
- Modify: `.gitignore`, `docs/OPEN-QUESTIONS.md`

**Interfaces:**
- Consumes: `boec.replay.regenerate`, `boec.surrogate.build_gp`, `boec.lengthscale_diag.censored_fwhm`, `boec.diagnostics.coverage`, `boec.norms.sobol_grid`
- Produces: `results/k1-noise-ceiling.json` with per-campaign `ls_over_fwhm`, `latent_coverage_95`, `regret` under three `Yvar` conditions

- [ ] **Step 1: Register**

```markdown
**K1.** Three Yvar conditions on the same regenerated campaigns: (i) `plug_in(y)` as
committed; (ii) `plug_in(truth(x))` -- the coupling removed but the model otherwise
identical; (iii) a single pooled scalar variance, as three triplicate anchors would
give. Measured per campaign: regret, fitted-lengthscale / censored_fwhm on active
dimensions, and latent 95% coverage. Registered before the runner exists.
Decision, fixed now: if (ii) moves ls/fwhm from ~0.57 materially toward 1.0, the
coupling is a real defect and replicates have a mechanism. If (iii) also moves regret
by less than 0.01, replicates are a CALIBRATION intervention and not a regret one --
which is the SPADE thesis, and it must then be argued on K6, not here.
E3 already measured latent coverage below nominal 0.95 in every cell, worst 0.7644 at
d=8/sigma=0.25.
```

- [ ] **Step 2: Write the failing test**

Append to `tests/test_replay.py`:

```python
def test_regenerate_yvar_is_coupled_to_the_reading_not_the_truth():
    """Documents the defect K1 tests. If this ever fails, the oracle changed."""
    import torch
    from boec.torch_oracle import BiphasicOracle
    from boec.replay import _instance

    inst = _instance("ce7334da318bc5e5", 6)
    orc = BiphasicOracle(inst, sigma_rel=0.25, seed=0)
    X = torch.rand(64, 6, dtype=torch.double)
    Y, Yvar = orc.evaluate(X)
    # Variance is a monotone function of the NOISY reading, so it correlates with Y.
    r = torch.corrcoef(torch.stack([Y.abs().reshape(-1), Yvar.reshape(-1)]))[0, 1]
    assert float(r) > 0.9, f"expected Yvar coupled to |Y|, got corr={float(r):.3f}"
```

- [ ] **Step 3: Run it and watch it fail**

```bash
.venv/bin/python -m pytest tests/test_replay.py::test_regenerate_yvar_is_coupled_to_the_reading_not_the_truth -v
```

Expected: `ImportError: cannot import name '_instance'` — then export it from `replay.py` and re-run. It should then **pass**, documenting the coupling.

- [ ] **Step 4: Write `scripts/run_k1_noise_ceiling.py`**

For each committed `(instance, seed)` at `d=6, sigma=0.25`, for each arm, regenerate once and refit `build_gp` three times with `Yvar` replaced by each of the three conditions. Record regret at the posterior-mean argmax, `ls_over_fwhm` via `censored_fwhm`, and latent coverage on `sobol_grid(6, 20_000, seed=0)`.

- [ ] **Step 5: Run it**

```bash
.venv/bin/python scripts/run_k1_noise_ceiling.py 2>&1 | tee results/k1-noise-ceiling.log
```

Expected: ~3 CPU-hours.

- [ ] **Step 6: Commit**

```bash
printf '!results/k1-noise-ceiling.json\n!results/k1-noise-ceiling.log\n' >> .gitignore
git add scripts/run_k1_noise_ceiling.py tests/test_replay.py \
        results/k1-noise-ceiling.json results/k1-noise-ceiling.log .gitignore
git commit -m "K1: the noise ceiling and the Yvar-to-reading coupling"
```

---

## Task 4: K6 — does the deliverable reverse the ranking

> **Amendments A, B and C govern this task and override the text below where they
> conflict.** In particular: the primary object is Peterson `D_γ` on the posterior
> predictive, not the mean LCB (B2); refusing to certify an unvaried axis is primary
> (B3); the cost frontier is dead (C1); and τ is registered as a fraction of `τ_max`,
> never absolute (C2). Read all three amendments before implementing.

**Decides:** whether SPADE Stages 4 and 5 exist at all.

**A correction that changes this task's metrics.** The SPADE note predicts spread designs win on certified volume and on the inscribed hyperrectangle. Measured neighbour density says both metrics may be **identically zero** for a spread arm:

| n | d | ℓ | mean neighbours within one lengthscale |
|---|---|---|---|
| 48 | 6 | 0.42 | **0.49** |
| 48 | 6 | 0.50 | 1.22 |
| 55 | 6 | 0.42 | 0.57 |
| 48 | 8 | 0.485 | **0.15** |

The note assumed ~1.4. At 0.49, `s(x)` sits near the prior SD and `LCB = mu - 1.96 s` may clear `tau` nowhere. Certified volume and hyperrectangle volume share that predicate, so both die together and the table becomes zeros — not a finding.

**The fix, which also improves the metric.** Do not fix confidence at 95% and measure volume. Sweep the confidence multiplier `z` and report **certified volume as a curve over z**, plus the `z*` at which the box first becomes non-empty. Always defined; 95% is one point on it. Metric (b), the probability-map score, needs no threshold and is the safe primary.

**Files:**
- Create: `src/boec/designspace.py`, `tests/test_designspace.py`, `scripts/run_k6_designspace.py`
- Modify: `.gitignore`, `docs/OPEN-QUESTIONS.md`

**Interfaces:**
- Consumes: `boec.replay.regenerate`, `boec.surrogate.build_gp`, `boec.norms.sobol_grid`
- Produces:
  - `probability_map(model, X_grid, tau) -> Tensor (n,)`
  - `brier_and_auc(p, truth, tau) -> tuple[float, float]`
  - `certified_mask(model, X_grid, tau, z) -> Tensor (n,) bool`
  - `certified_volume_curve(model, X_grid, tau, z_values) -> dict[float, float]`
  - `inscribed_box(model, X_grid, tau, z, n_steps=20) -> tuple[Tensor, float]`
  - `false_inclusion_rate(mask, truth, tau) -> float`

- [ ] **Step 1: Register**

```markdown
**K6.** On regenerated campaigns, score three design-space deliverables against known
truth: (a) certified volume as a CURVE over confidence multiplier z in {1.0, 1.28, 1.64,
1.96, 2.58} -- not fixed at 95%, because measured spread-design neighbour density (0.49
per lengthscale at n=48,d=6) makes a fixed-95% volume plausibly zero for every spread
arm and a table of zeros is degenerate, not a result; (b) Brier score and AUC of
P(f >= tau) against 1{f >= tau}, which needs no threshold and is the PRIMARY; (c) volume
of the largest axis-aligned box with LCB >= tau throughout, reported at the smallest z
where it is non-empty. tau swept over {0.70, 0.80, 0.85, 0.90}. Also reported: the ACTUAL
false-inclusion rate of each arm's nominal-95% certified region. Registered before the
runner exists. Decision: if the arm ranking on (b) matches the ranking on regret, the
reframe adds nothing and SPADE Stages 4-5 are dropped.
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_designspace.py`:

```python
import torch

from boec.designspace import certified_mask, false_inclusion_rate, inscribed_box
from boec.norms import sobol_grid


class _Linear:
    """mu(x) = 1 - x0, constant sd. Analytic, so the box is checkable by hand."""

    def __init__(self, sd):
        self.sd = sd

    def posterior_mean_and_sd(self, X):
        mean = (1.0 - X[:, 0]).double()
        return mean, torch.full_like(mean, float(self.sd))


def test_certified_mask_is_empty_when_uncertainty_swamps_the_signal():
    """The degenerate case K6 must not silently report as a zero-volume finding."""
    grid = sobol_grid(3, 2048, seed=0)
    mask = certified_mask(_Linear(sd=1.0), grid, tau=0.9, z=1.96)
    assert mask.sum() == 0


def test_certified_mask_grows_as_confidence_is_relaxed():
    grid = sobol_grid(3, 2048, seed=0)
    strict = certified_mask(_Linear(sd=0.05), grid, tau=0.8, z=2.58)
    loose = certified_mask(_Linear(sd=0.05), grid, tau=0.8, z=1.0)
    assert loose.sum() > strict.sum()


def test_inscribed_box_is_contained_in_the_certified_region():
    grid = sobol_grid(3, 2048, seed=0)
    box, vol = inscribed_box(_Linear(sd=0.05), grid, tau=0.8, z=1.96)
    assert vol > 0.0
    inside = ((grid >= box[0]) & (grid <= box[1])).all(dim=1)
    mask = certified_mask(_Linear(sd=0.05), grid, tau=0.8, z=1.96)
    assert bool((mask | ~inside).all()), "box contains an uncertified grid point"


def test_false_inclusion_rate_counts_certified_points_that_are_truly_below_tau():
    mask = torch.tensor([True, True, False])
    truth = torch.tensor([0.95, 0.50, 0.99], dtype=torch.double)
    assert false_inclusion_rate(mask, truth, tau=0.9) == 0.5
```

- [ ] **Step 3: Run it and watch it fail**

```bash
.venv/bin/python -m pytest tests/test_designspace.py -v
```

Expected: `ModuleNotFoundError: No module named 'boec.designspace'`.

- [ ] **Step 4: Implement `src/boec/designspace.py`**

The model argument is duck-typed: anything exposing `posterior_mean_and_sd(X) -> (mean, sd)`. A helper adapts a BoTorch `SingleTaskGP` to that shape, so the analytic stand-ins in the tests and a real fitted GP go down the same path.

```python
"""The design-space deliverables: a probability map, a certified region, and a box.

WHY A CURVE AND NOT A NUMBER
----------------------------
The obvious metric is "certified volume at 95%". Measured neighbour density says that
metric is plausibly degenerate: a 48-point LHS in 6D at the fitted lengthscale 0.42 has
**0.49** neighbours within one lengthscale, so ``s(x)`` sits near the prior SD and
``mu - 1.96 s`` may clear ``tau`` nowhere at all. Certified volume and inscribed-box
volume share that predicate, so both would report zero together and a table of zeros is
not a finding. Everything here is therefore reported as a function of the confidence
multiplier ``z``, with 95% as one point on the curve.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["brier_and_auc", "certified_mask", "certified_volume_curve",
           "false_inclusion_rate", "gp_adapter", "inscribed_box", "iou",
           "predictive_probability_map", "probability_map"]


def gp_adapter(model):
    """Adapt a BoTorch model to the ``posterior_mean_and_sd`` protocol used here."""

    class _Adapted:
        def posterior_mean_and_sd(self, X: Tensor) -> tuple[Tensor, Tensor]:
            with torch.no_grad():
                post = model.posterior(X)
            return (post.mean.reshape(-1).double(),
                    post.variance.reshape(-1).clamp_min(0).sqrt().double())

    return _Adapted()


def probability_map(model, X_grid: Tensor, tau: float) -> Tensor:
    """``P(f(x) >= tau)`` under the Gaussian LATENT posterior. Shape ``(n,)``.

    **SECONDARY.** Amendment B2 makes :func:`predictive_probability_map` the primary
    object. This one is retained because E3 showed the latent interval is the
    anti-conservative one, so the GAP between the two maps is itself a result.
    """
    mean, sd = model.posterior_mean_and_sd(X_grid)
    normal = torch.distributions.Normal(0.0, 1.0)
    return normal.cdf((mean - tau) / sd.clamp_min(1e-12))


def predictive_probability_map(model, X_grid: Tensor, tau: float,
                               sigma: Tensor | float) -> Tensor:
    """``P(Y >= tau | x)`` under the posterior PREDICTIVE — Peterson's ``D_gamma``.

    **PRIMARY** (Amendment B2; Peterson 2008, Peterson & Lief 2010). Carries ``sigma^2``
    as well as ``s^2``, so it is floored by process noise:

        tau_max = mu_max * (1 - z * sigma_rel)

    At ``sigma_rel = 0.25, gamma = 0.95`` that is **0.589 regardless of budget**. A grid
    of ``tau`` above the floor certifies nothing for any arm, which is why C2 registers
    ``tau`` as a FRACTION of ``tau_max`` and never as an absolute value.

    ``sigma`` is the observation SD at each grid point. This repo's noise is RELATIVE
    (``y = f(1 + eps) + eta``), so pass ``sigma_rel * mean``, not a scalar -- a constant
    here silently answers a homoscedastic question the campaigns did not ask.
    """
    mean, sd = model.posterior_mean_and_sd(X_grid)
    total = (sd ** 2 + torch.as_tensor(sigma, dtype=sd.dtype) ** 2).clamp_min(1e-24).sqrt()
    return torch.distributions.Normal(0.0, 1.0).cdf((mean - tau) / total)


def iou(mask: Tensor, truth: Tensor, tau: float) -> float:
    """Intersection-over-union of a certified region against the true superlevel set."""
    true_set = truth.reshape(-1) >= tau
    union = (mask | true_set).sum()
    return float((mask & true_set).sum() / union) if union > 0 else float("nan")


def brier_and_auc(p: Tensor, truth: Tensor, tau: float) -> tuple[float, float]:
    """Brier score (lower better) and AUC (higher better) against ``1{f >= tau}``."""
    label = (truth.reshape(-1) >= tau).double()
    brier = float(((p - label) ** 2).mean())
    pos, neg = p[label == 1], p[label == 0]
    if pos.numel() == 0 or neg.numel() == 0:
        return brier, float("nan")          # AUC undefined; do NOT default it to 0.5
    order = torch.argsort(p)
    ranks = torch.empty_like(p, dtype=torch.double)
    ranks[order] = torch.arange(1, p.numel() + 1, dtype=torch.double)
    auc = float((ranks[label == 1].sum() - pos.numel() * (pos.numel() + 1) / 2)
                / (pos.numel() * neg.numel()))
    return brier, auc


def certified_mask(model, X_grid: Tensor, tau: float, z: float) -> Tensor:
    """``(n,)`` bool: grid points whose lower confidence bound clears ``tau``."""
    mean, sd = model.posterior_mean_and_sd(X_grid)
    return (mean - z * sd) >= tau


def certified_volume_curve(model, X_grid: Tensor, tau: float,
                           z_values) -> dict[float, float]:
    """Grid fraction certified, per confidence multiplier. Always defined."""
    return {float(z): float(certified_mask(model, X_grid, tau, z).double().mean())
            for z in z_values}


def false_inclusion_rate(mask: Tensor, truth: Tensor, tau: float) -> float:
    """Of the points this region certifies, the fraction genuinely below ``tau``.

    This is the safety number. A nominal-95% region whose false-inclusion rate is far
    above 5% is anti-conservative, and E3 already measured latent coverage at 0.7644
    against nominal 0.95 in the worst cell -- so a large value here is expected, not
    surprising, and is a reportable result on its own.
    """
    if mask.sum() == 0:
        return float("nan")                  # empty region: undefined, never 0.0
    return float((truth.reshape(-1)[mask] < tau).double().mean())


def inscribed_box(model, X_grid: Tensor, tau: float, z: float,
                  n_steps: int = 20) -> tuple[Tensor, float]:
    """Largest axis-aligned box with ``LCB >= tau`` throughout, by greedy expansion.

    Returns ``((2, d) lower/upper, volume)``. Volume is 0.0 with a degenerate box when
    nothing certifies -- callers must distinguish that from a genuinely small box, which
    is why :func:`certified_volume_curve` is reported alongside.
    """
    mean, sd = model.posterior_mean_and_sd(X_grid)
    lcb = mean - z * sd
    d = X_grid.shape[1]
    if not bool((lcb >= tau).any()):
        centre = torch.full((d,), 0.5, dtype=torch.double)
        return torch.stack([centre, centre]), 0.0

    seed = X_grid[int(torch.argmax(lcb))].double()
    lo, hi = seed.clone(), seed.clone()
    step = 1.0 / n_steps

    moved = True
    while moved:
        moved = False
        for j in range(d):
            for bound, sign in ((hi, 1.0), (lo, -1.0)):
                trial = bound.clone()
                trial[j] = float(torch.clamp(bound[j] + sign * step, 0.0, 1.0))
                if trial[j] == bound[j]:
                    continue
                new_lo = torch.minimum(lo, trial) if sign < 0 else lo
                new_hi = torch.maximum(hi, trial) if sign > 0 else hi
                inside = ((X_grid >= new_lo) & (X_grid <= new_hi)).all(dim=1)
                if inside.any() and bool((lcb[inside] >= tau).all()):
                    bound[j] = trial[j]
                    moved = True

    return torch.stack([lo, hi]), float(torch.prod(hi - lo))
```

`certified_volume_curve` calls `certified_mask` once per `z` and returns the certified grid fraction.

- [ ] **Step 5: Run the tests and watch them pass**

```bash
.venv/bin/python -m pytest tests/test_designspace.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Write and run the K6 runner**

```bash
.venv/bin/python scripts/run_k6_designspace.py 2>&1 | tee results/k6-designspace.log
```

Expected: ~1 CPU-hour regeneration plus scoring. **Report the empty-region count explicitly** — how many `(arm, tau, z)` cells certified nothing. A silent zero is the failure mode this task is designed around.

- [ ] **Step 7: Commit**

```bash
printf '!results/k6-designspace.json\n!results/k6-designspace.log\n' >> .gitignore
git add src/boec/designspace.py tests/test_designspace.py scripts/run_k6_designspace.py \
        results/k6-designspace.json results/k6-designspace.log .gitignore
git commit -m "K6: score the design-space deliverables against the regret ranking"
```

---

## Task 5: K3 — confirm-and-average

**Decides:** whether SPADE Stage 5 exists. Q58 measured confirm-top-3 moving the classical arm 0.0958 → **0.1437** — it *hurt* it — and Q58 itself states the averaging variant *"was not run"* and is *"an open question, not a claim."* SPADE §5.3 averages. This is that experiment.

**Files:**
- Create: `scripts/run_k3_confirm_average.py`
- Modify: `src/boec/selection.py` (add one rule; do not change the existing four), `tests/test_selection.py`

**Interfaces:**
- Consumes: `boec.selection.SELECTION_RULES`, `boec.replay.regenerate`
- Produces: `mean_of_confirmed(Y: np.ndarray, confirmations: np.ndarray, k: int) -> int` and `"confirm_mean"` added to `SELECTION_RULES`

- [ ] **Step 1: Register, then write the failing test**

Append to `tests/test_selection.py`:

```python
def test_confirm_mean_decides_by_the_average_not_the_confirmation_alone():
    """The distinction Q58 flagged as untested: keep the first reading, do not discard it."""
    import numpy as np
    from boec.selection import mean_of_confirmed

    # Candidate 0 reads high once by luck; candidate 1 is genuinely better.
    Y = np.array([0.90, 0.80, 0.10])
    confirmations = np.array([0.50, 0.82, 0.10])
    idx = mean_of_confirmed(Y, confirmations, k=2)
    assert idx == 1, "averaging must survive one lucky first reading"
```

- [ ] **Step 2: Run it and watch it fail**

```bash
.venv/bin/python -m pytest tests/test_selection.py::test_confirm_mean_decides_by_the_average_not_the_confirmation_alone -v
```

Expected: `ImportError: cannot import name 'mean_of_confirmed'`.

- [ ] **Step 3: Implement, run, and gate**

Add `mean_of_confirmed` to `src/boec/selection.py` and append `"confirm_mean"` to `SELECTION_RULES`. The runner must **regenerate Q58's four committed rules and reproduce them under the Task 1 policy before reading the fifth.**

```bash
.venv/bin/python -m pytest tests/test_selection.py -v
.venv/bin/python scripts/run_k3_confirm_average.py 2>&1 | tee results/k3-confirm-average.log
```

- [ ] **Step 4: Commit**

```bash
printf '!results/k3-confirm-average.json\n!results/k3-confirm-average.log\n' >> .gitignore
git add src/boec/selection.py tests/test_selection.py scripts/run_k3_confirm_average.py \
        results/k3-confirm-average.json results/k3-confirm-average.log .gitignore
git commit -m "K3: confirm-and-average, the variant Q58 registered as unrun"
```

---

## Task 6: K2 — the design lottery

**Decides:** whether SPADE Stage 1 has a mechanism, or is plain LHS with extra steps. Target is known: Q53 measured `spread_gp`'s design SD at **0.140–0.153 on Hartmann6** and 0.029–0.055 elsewhere — over half the whole `spread_gp − qLogEI` gap is which hypercube was drawn.

**Note the arithmetic constraint.** Strength-2 OA-LHS needs `n = p²`. At `n=49, p=7, d<=8` it holds exactly; at 42 or 48 it does not, and the maximin fallback is **not** the construction Stein's theorem justifies. Run at 49 and report the one-well mismatch openly, or drop the OA citation.

**Files:**
- Create: `src/boec/oa_design.py`, `tests/test_oa_design.py`, `scripts/run_k2_design_lottery.py`

**Interfaces:**
- Produces: `oa_lhs(d, n, seed) -> np.ndarray`, `maximin_lhs(d, n, seed, n_iter=20000) -> np.ndarray`, `choose_anchors(D, n_anchor=3) -> list[int]`

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import pytest

from boec.oa_design import choose_anchors, maximin_lhs, oa_lhs


def test_oa_lhs_rejects_a_non_prime_square_rather_than_falling_back_silently():
    """Pitfall 5 of the spec: fail loudly, because the fallback loses the Stein claim."""
    with pytest.raises(ValueError, match="prime square"):
        oa_lhs(d=6, n=48, seed=0)


def test_oa_lhs_stratifies_every_two_dimensional_projection():
    D = oa_lhs(d=6, n=49, seed=0)          # p = 7
    for j in range(6):
        for k in range(j + 1, 6):
            cells = {(int(a * 7), int(b * 7)) for a, b in zip(D[:, j], D[:, k])}
            assert len(cells) == 49, f"projection ({j},{k}) covers {len(cells)}/49 cells"


def test_maximin_lhs_reaches_low_column_correlation():
    D = maximin_lhs(d=6, n=42, seed=0)
    C = np.corrcoef(D, rowvar=False)
    assert np.max(np.abs(C - np.eye(6))) < 0.05


def test_anchors_are_well_separated():
    D = maximin_lhs(d=6, n=42, seed=0)
    idx = choose_anchors(D, n_anchor=3)
    assert len(set(idx)) == 3
    pair = min(np.linalg.norm(D[a] - D[b])
               for a in idx for b in idx if a != b)
    typical = np.median([np.linalg.norm(D[i] - D[j])
                         for i in range(42) for j in range(i + 1, 42)])
    assert pair > typical, "anchors must span the design, not cluster"
```

- [ ] **Step 2: Run it and watch it fail, then implement, then re-run**

```bash
.venv/bin/python -m pytest tests/test_oa_design.py -v
```

- [ ] **Step 3: Run the lottery**

20 design draws each of `{plain LHS, maximin LHS, OA-LHS n=49}`, at `d=6` and `d=8`, on **Hill and Hartmann6**. Report **design SD**, not only mean regret — the SD is the quantity with the known target.

```bash
.venv/bin/python scripts/run_k2_design_lottery.py 2>&1 | tee results/k2-design-lottery.log
```

Expected: ~6 CPU-hours.

- [ ] **Step 4: Commit**

```bash
printf '!results/k2-design-lottery.json\n!results/k2-design-lottery.log\n' >> .gitignore
git add src/boec/oa_design.py tests/test_oa_design.py scripts/run_k2_design_lottery.py \
        results/k2-design-lottery.json results/k2-design-lottery.log .gitignore
git commit -m "K2: does an orthogonal-array design shrink the design lottery"
```

---

## Task 7: K4 — the frozen deception detector

**Run only if Task 6 or Task 5 produced a win.** This is the paper's regime claim. Q53 established the dividing line — smooth and coordinate-wise unimodal ties, deceptive loses — but nobody built the statistic that says which side you are on from the first plate.

**Files:**
- Create: `scripts/run_k4_deception.py`
- Modify: `docs/OPEN-QUESTIONS.md`, `.gitignore`

- [ ] **Step 1: Register the rule and the threshold BEFORE scoring**

Fit on **hill, levy, rosenbrock** only. Freeze the rule and threshold in `docs/OPEN-QUESTIONS.md` and commit. Then score **once** on hartmann6 and ackley. Candidate statistics, all first-plate computable:

- measured additive share from an ANOVA decomposition of the fitted GP on `sobol_grid(d, 20_000, seed=0)`
- ARD inert/active separation ratio (`boec.lengthscale_diag`; a purely prior-driven fit gives exactly 1.0, so departure from 1.0 is data)
- count of distinct local maxima of the posterior mean whose LCB clears the second-highest UCB
- fitted lengthscale ÷ box width per coordinate
- residual variance after an additive-only refit, divided by σ̂²

Scoring the held-out families more than once is tuning on the evaluation set — the exact failure this project exists to document.

- [ ] **Step 2: Run, then commit**

```bash
.venv/bin/python scripts/run_k4_deception.py --fit 2>&1 | tee results/k4-deception-fit.log
git add docs/OPEN-QUESTIONS.md results/k4-deception-fit.log
git commit -m "K4: freeze the deception rule on the training families"
.venv/bin/python scripts/run_k4_deception.py --score 2>&1 | tee results/k4-deception-score.log
```

---

## Decision tree

Run in order. Stop at the first hard failure.

```
Task 1 (replay gate)
  |- DoE arm not exact ................. STOP. Seeding or ensemble order drifted.
  |- policy recorded ................... continue

Task 2 (K0)   r2 wins or ties ......... ODIN Stage 2 stays deleted, permanently
              sup_err wins ............. Stage 2 returns, with its own gate

Task 3 (K1)   condition (ii) moves ls/fwhm toward 1.0 .... coupling is real; replicates
                                                            have a mechanism
              (iii) moves regret < 0.01 .................. replicates are CALIBRATION only
                                                            -> the case rests on K6

Task 4 (K6)   RUNS SECOND, right after Task 1 (Amendment A)
              ranking on (b) == ranking on regret ....... drop SPADE Stages 4-5
              diverges, SPREAD ahead on (b) and (c) ..... GO, headline
              diverges, CLUSTERED ahead everywhere ...... NO-GO for SPADE. Report as
                                                           "the design-space deliverable
                                                           favours adaptive designs" --
                                                           still novel, different paper
              every cell certifies nothing .............. report the z* curve, not zeros
              Q30 additive arm gains on Brier but not
                on regret (A1) .......................... the project's cleanest figure
              DoE false-inclusion high under policy (b)
                (A3) .................................... "screening is fatal for a
                                                           design-space deliverable" --
                                                           stands alone, independent of
                                                           whether SPADE wins

Task 5 (K3)   averaging preserves the spread arm ......... Stage 5 sound
              averaging also erases it ................... drop Stage 5; the stronger
                                                            claim is "any confirmation
                                                            protocol equalises the methods"

Task 6 (K2)   OA-LHS cuts Hartmann6 design SD ............ Stage 1 has a mechanism
              design SD unchanged ....................... Stage 1 is plain LHS with extra
                                                            steps

### Superseded by Amendment B — use this tree

```
K6 map ranking == regret ranking
    -> STOP. Write up Q53/Q54/Q55/Q57/Q58. No new algorithm.

K6 map diverges, SPREAD ahead on Brier/AUC and IoU of D_gamma
    -> GO. Build Version B: two plates, Peterson D_gamma, LSE straddle on plate 2,
       NOR on active axes only.

(the cost-frontier branch is REMOVED -- C1 measured that four of five families put
 the optimum at or below median cost, so there is no test bed for it)

Clustered ahead on BOTH map and cost
    -> different paper: "the design-space deliverable favours adaptive designs."
       Still novel. Not SPADE.
```

**Findings that land regardless of which branch fires**, because none of them needs a new
method or a new campaign:

- `tau_max = mu_max(1 - z*sigma_rel)` — no method certifies above **0.589** at
  σ_rel=0.25, γ=0.95, at any budget (B0)
- fewer than **one well in 48** lands in the cheapest cost quartile, under every
  space-filling design, by CLT (B0)
- **screening structurally overpays** on every factor it drops (B6)
- the `(n, tau, gamma)` surface at which each arm's region becomes non-empty — which
  converts "the box is empty" into a **plate-size specification** (A5)

### Recommendation

**Run Version A (K6) immediately.** If spread wins on the probability map or the cost
curve, build Version B — two plates, Peterson `D_γ`, LSE straddle on plate 2, NOR on
active axes only. **Do not build current SPADE. Do not build C until B has a result.** SPADE is then spread_gp plus a terminal rule, both
      already measured -- write up Q53/Q54/Q55/Q57/Q58 as they stand.
```

K0 and K1 do not gate go/no-go alone. They decide **how much** gets built.

## Cost

| task | new campaigns | CPU |
|---|---|---|
| 1 replay gate | 1300 regenerations | ~1 h |
| 2 K0 norms | reuses task 1 | ~4 h |
| 3 K1 noise ceiling | 3 refits × 150 | ~3 h |
| 4 K6 design space | reuses task 1, **+200 Q30 regenerations (A1)**, **+2 new sigma levels (A5, exploratory)** | ~1 h + ~20 min + scoring |
| 5 K3 confirm-average | reuses task 1 | ~4 h |
| 6 K2 design lottery | **yes** — A4 repairs the power: 25 instances × 20 draws × 3 designs × 2 families × 2 dims = **6,000 campaigns** | **measure in Task 1 and scale; the ~6 h figure was for 240 campaigns and does not carry** |
| 7 K4 deception | reuses tasks 1 and 6 | ~2 d wall |

## Pre-registration freeze

Commit before Task 2 runs:

- K0 statistic: Spearman ρ, 10,000-resample instance-level paired bootstrap on the ρ difference
- K6 grids: τ ∈ {0.70, 0.80, 0.85, 0.90}, z ∈ {1.00, 1.28, 1.64, 1.96, 2.58}, Sobol 20,000 at seed 0
- K6 primary metric: **Brier/AUC of the map, plus IoU of `D_γ` against the true superlevel set**. The cost-assurance curve is **DEAD (C1)**. Certified volume and NOR are secondary, reported as curves over γ, with the empty-region count stated explicitly
- K6 region definition: **Peterson `D_γ` on the posterior predictive** is primary; the mean-LCB region is reported alongside, and the gap between them is a result (B2)
- K6 γ sweep: {0.50, 0.70, 0.80, 0.90, 0.95, 0.99}. **Not a robustness check — it is what keeps the object non-empty** (B0)
- ~~`G(k)` computed by posterior sampling~~ — **removed, B4 is dead (C1)**
- K1 conditions: `plug_in(y)` / `plug_in(truth)` / pooled scalar
- K2: **paired within-instance SD** across D=20 draws, 25 pairs, Wilcoxon on the pairs (A4). Not a comparison of two grand SDs
- K6 dropped-factor policy — **REVERSED BY B3**: **(a) refuse to certify is PRIMARY**, (b) full range is the declared sensitivity, (c) the GP's prior-driven slab is reported and labelled. Under (a) the screened DoE arm's NOR is defined in 4D and its 6D volume is identically zero
- K6 Brier decomposition: Murphy calibration–refinement, **10 equal-count bins** (A5)
- K6 sigma sweep: {0.25, 0.20, 0.15, 0.10}; **0.20 and 0.15 are exploratory and ungated** (A5)
- K6 tau grid — **RE-REGISTERED BY C2**: `tau_frac in {0.60, 0.75, 0.85, 0.95}` of `tau_max(gamma, s=0.19)`, never absolute tau. The old absolute grid {0.70, 0.80, 0.85, 0.90} was entirely above the gamma=0.95 floor and guaranteed an empty table
- Plate-2 split (C3, tweak 2): **70:30 boundary:peak primary, 100:0 declared sensitivity**
- SESOI 0.02; Wilcoxon governs yes/no and the bootstrap reports magnitude, with disagreements reported and not resolved (Q20 §2)

## What is explicitly NOT being built

- NUTS, I-splines, shape-constrained additive components — closed by Q30 unless K0 reopens it
- Covariate adjustment (SPADE Stage 0) — needs a real plate; the `r` number is a lab question, not a simulation one. **A5's sigma sweep makes it a lookup rather than a rebuild, and A6 gets `r` in parallel**
- The 55-well budget — it cannot be gated against any committed column. Keep every K-test at 48
- SPADE Stage 5's **boundary allocation** (placing confirmation wells on the constraining face rather than the peak). It is deferred, not dropped: it cannot be specified until K6 shows whether a non-empty box exists at all, since the allocation targets that box's limiting face. If K6 wins, this becomes Task 8 and is written then. K3 covers only the averaging half of Stage 5
- TuRBO and OCBA — see `docs/superpowers/plans/2026-08-20-turbo-and-ocba.md`, verdict: Paper 2
