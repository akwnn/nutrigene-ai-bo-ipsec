# PERPLEXITY · SPADE FINAL — the prospective confirmatory study

**Complete working log: methods, what happened, results, implications.**

**Opened:** 2026-08-23 · **Mandate:** the Final Prospective SPADE Confirmatory Study brief
**Status line:** this document is written *as the work happens*, including the parts that
fail. Nothing here is back-filled to look tidier than it was.

> **Reading contract.** Every factual claim about the *pre-existing* repository in Part 0
> and Part 1 was verified by reading the file named, not recalled. Every claim about *new*
> results carries its result-file path and key, or it is labelled `NOT RUN`. Where a number
> does not exist yet, this document says so rather than leaving a plausible gap.

---

## Part 0 · The mandate, restated in the repository's own terms

The brief asks for a **final prospective confirmatory study**: design it, pre-register it,
implement it test-first, run it, analyse it, and write down honestly what SPADE is and is
not worth. It explicitly forbids aiming for a SPADE win, and it requires that the study be
able to conclude that Sobol is better, or that Plate-2 boundary targeting does not earn its
complexity, if that is what the data say.

The single most important thing established during reconnaissance is that **this study is
not redundant**, and the repository itself says why, in `docs/FINDINGS-SPADE.md` §44.4:

> **§43.5 — Version C has never been run as a method.** Every number is Version B's wells
> scored under Version C's rules. No claim here is evidence that a lab running Version C
> prospectively would see these numbers.

That is exactly the gap the brief names. Every SPADE certificate number in this project to
date is a **re-score** of committed wells under new rules. A prospective run — fresh
campaigns, fresh plate-2 allocation, cross-fit certificate, full comparator set — has never
been done. **That is the study.**

### 0.1 What "prospective" has to mean here, precisely

| | re-score (all prior work) | prospective (this study) |
|---|---|---|
| plate 1 wells | replayed from a committed campaign | generated fresh from the frozen design |
| plate 2 wells | replayed, or re-derived from a replayed model | **chosen live** by the frozen rule from the live plate-1 fit |
| certificate | computed on replayed draws | computed on fresh draws, **cross-fit** |
| what it licenses | "these rules, applied to those wells, give X" | "a lab running this protocol sees X" |

The second row is the load-bearing one. A re-score cannot test an *allocation* rule,
because the allocation already happened. The `m0/m4/m8` question — does spending some of
plate 2 on local exploitation buy regret without costing the certificate — is **only**
answerable prospectively. That is why it is the brief's co-primary design variant and why
it cannot be lifted from any committed file.

---

## Part 1 · Repository reconnaissance — what already exists

Performed before writing any plan, per the brief's §19 step 1. The purpose was to avoid
rebuilding what is already here, and to find the pieces the study can stand on.

### 1.1 Scale of the existing project

| | |
|---|---|
| package | `src/boec`, 38 modules, **14,359 lines** |
| runners | `scripts/`, **86** run/analyse scripts |
| tests | `tests/`, **74** test files, **1,399 tests passing** at HEAD |
| committed results | `results/`, ~300 files |
| findings record | `docs/FINDINGS-SPADE.md`, **3,068 lines**, 44 sections |
| registrations | `docs/OPEN-QUESTIONS.md`, **9,105 lines** |

HEAD at the start of this work: `08afb24` — *"FINDINGS 44: the Version C index"*. Working
tree clean, `main` level with `origin/main`.

### 1.2 🟢 Infrastructure that ALREADY EXISTS and must be reused, not rebuilt

This is the most valuable finding of reconnaissance. **The brief's §2.5 cross-fit
certificate protocol — the thing it treats as the central methodological upgrade — is
already implemented, tested, and used.**

| brief requires | already exists | where |
|---|---|---|
| cross-fit / split-draw containment | `conservative_estimate_split(draws, theta, alpha, n_rho)` → `(mask, held-out containment)` | `src/boec/vorobev.py:160` |
| cross-fit column emitter | `conservative_columns(draws_sel, draws_val, truth_eval, theta, alphas)` | `src/boec/versionc.py:144` |
| deterministic draw splitting | `split_joint_draws(model, X, n_draws, seed, ...)` | `src/boec/versionc.py:448` |
| non-circular containment test | `empirical_containment(mask, truth, theta)` — returns `None` for empty sets, refusing to score silence as success | `src/boec/vorobev.py:236` |
| certifiability ceiling | `tau_max(gamma, sigma_rel, mu_max)`, `tau_max_exact(...)` | `src/boec/designspace.py:71,489` |
| Plate-2 batch LSE / SUR | `batch_lse(model, X_cand, theta, q, exclude=, sigma=)` | `src/boec/lse.py:163` |
| straddle acquisition (latent + predictive) | `straddle_score`, `straddle_predictive_score`, `predictive_sigma` | `src/boec/lse.py:102,118,107` |
| exclusion radius from fitted ARD | `exclusion_radius(model)` | `src/boec/lse.py:134` |
| Murphy calibration / refinement | `murphy_decomposition(p, truth, tau, ...)` | `src/boec/calibration.py:121` |
| type I / type II / symmetric-difference error volumes | `error_volumes(vol, fi, prevalence)` | `src/boec/calibration.py:240` |
| Brier, AUC, IoU, false inclusion | `brier_and_auc`, `iou`, `false_inclusion_rate` | `src/boec/designspace.py:178,169,158` |
| Vorob'ev quantile / expectation / deviation | `vorobev_quantile`, `vorobev_expectation`, `vorobev_deviation` | `src/boec/vorobev.py:85,90,257` |
| two-plate campaign generation | `_two_plate(orc, dim, seed, mu_max, mode)` — modes `lse`/`predictive`/`random` | `scripts/run_versionb.py:131` |

**Consequence for the plan:** the study does *not* need new certificate mathematics. It
needs a new **runner** that composes these prospectively, a new **allocation rule** for the
`m` local wells, and the analysis/figure/audit layer. That is a much smaller and much safer
build than the brief's file list implies, and the reduction is entirely because prior
tracks already paid for the hard parts.

### 1.3 🔴 The one piece of certificate science the brief gets *empirically* right, already proven here

The brief's §2.5 justifies cross-fit by asserting that 512 draws produced an apparent
high-assurance failure that was really Monte Carlo error. **The repository proved exactly
this, independently, and it is one of the most important results in the project.**

`docs/FINDINGS-SPADE.md` §29, from `results/f3-draw-sweep.json` (250 campaigns, 3,000 rows,
0 crashes; every tail `scipy.stats.binom.cdf`, never a normal approximation):

| cell | 512 draws | 1024 | 2048 | 4096 |
|---|---|---|---|---|
| **γ=0.99, τ_f=0.60** | **0.860** | **0.980** | 0.980 | 0.980 |
| γ=0.99, τ_f=0.75 | 0.960 | 1.000 | 1.000 | 1.000 |
| γ=0.95, τ_f=0.60 | 0.940 | 1.000 | 1.000 | 1.000 |
| γ=0.99, τ_f=0.85 | 0.940 | 1.000 | 1.000 | 1.000 |
| γ=0.50, τ_f=0.60 **[control]** | 1.000 | 1.000 | 1.000 | 1.000 |

§14's registered kill — *"SPADE's certificate fails below nominal at high assurance"* — was
**withdrawn**: it fired on the estimator, not on SPADE. And §29.1 records a *failed
prediction* honestly: the registration predicted the bias would scale with the `n_rho` scan,
and it does not (`n_rho`=16 and 64 give identical containment at every draw level). The
mechanism is Monte Carlo error in `containment_probability` itself at low draw counts.

§29.3 then measured the **residual** selection bias at 4,096 draws by comparing full against
cross-fit on the same draws:

| cell | full | cross-fit | Δ |
|---|---|---|---|
| γ=0.99, τ_f=0.60 | 0.9300 | **0.8950** | **−0.0350** |
| γ=0.99, τ_f=0.75 | 0.9550 | **0.9400** | **−0.0150** |
| γ=0.95, τ_f=0.60 | 0.9800 | 0.9800 | 0.0000 |
| γ=0.99, τ_f=0.85 | 0.9800 | 0.9800 | 0.0000 |
| γ=0.50 **[control]** | 0.9848 | 1.0000 | +0.0152 |

**Two independent routes, neither designed to test the other, agree:** the selection bias is
real, it is 1.5–3.5 percentage points, it is concentrated exactly where the Vorob'ev
quantiles tie, and it is an order of magnitude smaller than the 512-draw artefact.

**This is why the final study's ≥4,096 draws + cross-fit is not bureaucratic caution. It is
the minimum configuration at which a containment number in this repository has ever been
trustworthy**, and the repository had to retract a headline to learn it.

### 1.4 Prior findings the final study must not re-litigate

Recorded so the study does not spend campaigns re-deriving settled results.

| finding | § | status going in |
|---|---|---|
| Screening is fatal for a design-space deliverable — 24/24 cells, isolated between `lhs` and `doe` which differ in nothing else | §4.2a, §19 | **settled, and it strengthens at d=8** (§30) |
| Screening is not the *mechanism* for `doe`'s map collapse | §26 | settled — caveat discharged |
| `alpha*` is not a metric of certificate quality; it measures willingness to certify | §28, §31 | **settled — must not be used as evidence of a good certificate** |
| Doubling surrogate accuracy moves regret 0.0015 (p=0.71) | Q30, §4.3 | accuracy channel closed on all three deliverables |
| The cost frontier has no test bed — 4 of 5 families put the optimum at or below design-average cost | §4.6 | withdrawn before running; do not revive |
| Anti-conservatism prediction was wrong in the opposite direction (conservative by 10×–500×) | §4.4 | retracted |
| `doe`'s regret advantage is a **single-cell** result (6, 0.25), and 59% of it is identification not search | §9.2, §9.3 | settled |
| The D20 reversal is the terminal rule, not a BoTorch prior default (subspace restriction removes 0.5% of the collapse) | §9.1 | settled |
| AUC is invariant to monotone transformation and cannot see calibration; symmetric-difference error volume is the primary map scalar | §9.4 | settled — but §24 revises the *grounds* |
| Type I volume read alone ranks silence first — an empty certificate scores 0 | §9.4 ⚠️ | **carried forward as a trap the new analyser must refuse** |
| The two σ levels are ONE noise realisation at two amplitudes (`BiphasicOracle` seeds on `seed` alone) | §9.7 | **must be fixed or declared in the new study** |
| Pooling across `tau_frac` on the same campaign/posterior/draws is invalid — 11 pooling sites found | §9.5 | **the new analyser must hard-fail on it** |
| The regime detector separates nothing: 0/50 on both held-out families | §37, K-C7 | **FIRED — no Stage-0 detector in any final arm** |
| SPADE is a low-variance middling arm on the BO community's own conventions | §42 | settled — the paper may not claim general superiority |
| SPADE's certificate off hill: it declines to answer on ackley (certified nothing in 1,200 campaigns); rosenbrock/levy under-cover at γ=0.99 | §41 | **the sharpest limitation on record** |

### 1.5 What the reconnaissance changes about the brief

Three adjustments, each recorded now rather than discovered later:

1. **The brief's file list overstates the build.** `scripts/analyse_final_spade_benchmark.py`
   and the certificate infrastructure largely compose existing, tested functions. Building
   parallel implementations would create two sources of truth for containment — the exact
   defect §9.5 and §14 punished this project for. **Reuse is mandatory, not optional.**
2. **The brief's `γ=0.99` "stress diagnostic" is where the known pathology lives.** §29
   localises the residual cross-fit bias to exactly the γ≥0.95 tie corner, and §41 finds the
   real under-coverage there too. It stays in as a diagnostic, and it is read with that
   history attached.
3. **`doe_unscreened` at d=8 may be arithmetically impossible** at the shared budget. A
   second-order RSM in d=8 needs 45 coefficients; a 48-well shared budget leaves ~3 residual
   degrees of freedom. The brief already forbids fabricating it. This is recorded as an
   expected `unavailable_reason`, decided by arithmetic **before** any run.

---

*(Log continues as the work proceeds. Sections below are appended in execution order.)*

---

## Part 2 · What was built, and in what order

Execution followed the brief's §19 ordering. Every production file was written **test-first**:
the failing test was written, run, and *watched to fail* before the implementation existed.
The commit graph shows this — each implementation commit names the RED it was written
against.

### 2.1 The registration, frozen first

`docs/SPADE-FINAL-SPEC.md`, committed at **`c4f58d3`**, before any runner file existed. It
freezes: the three SPADE arms and local rule L1, the two causal controls, the mandatory
13-arm registry, the pre-run regime classifier and its numeric bars, the condition matrix,
`N_DRAWS = 4096` with a cross-fit split, the four Holm families, ten kill-ledger items with
their firing conditions, and the broad-paper conjunction.

Three choices in it are worth restating because they are the ones a reviewer should attack:

| choice | why it is not arbitrary |
|---|---|
| L1's trust region is the **ARD ball of radius 1** | That is literally `n_effective`'s bound (`src/boec/versionc.py:91`) — the statistic §9.3 identified as governing the identification gap. The radius is *inherited from a registered formula*, not tuned. A test measures that every local well increments `n_eff`, rather than asserting it. |
| `x̂` is a **grid argmax**, not a continuous optimiser | §4.1 records that this project's one non-reproducible path was a post-hoc L-BFGS-B locator with 20 restarts. A grid argmax over a seeded Sobol set is bitwise reproducible. |
| Certificate maths is **reused**, not reimplemented | `conservative_estimate_split` and `conservative_columns` already exist and are tested. A parallel implementation would create two sources of truth for the primary safety endpoint — the exact defect §9.5 and §14 punished this project for. |

### 2.2 The code, and what each test pins

| file | tests | the property it exists to pin |
|---|---|---|
| `src/boec/final_spade.py` · `local_wells` | 10 | every local well lands inside the ARD ball; `n_eff` rises by exactly `m`; bitwise determinism; `m=0` returns nothing so `m0` *is* the boundary arm; short balls report rather than silently shrink; **the signature exposes no `truth`, `model` or `oracle`** |
| `src/boec/final_spade.py` · `classify_regime` | 9 | above-ceiling → INFEASIBLE; feasibility read on the **worst** primary γ; degenerate prevalence at both ends; pre-declared EXCEPTION beats TARGET; **the signature exposes no arm outcome** |
| `src/boec/final_spade.py` · `threshold_facts`, `ROW_SCHEMA` | 6 | τ is a fraction, never absolute; prevalence arithmetic; cross-fit and same-draw are **separate columns** and a combined `containment` field is forbidden |
| `src/boec/final_spade.py` · `spade_plate2` | 13 | equal plate-2 budget at every `m`; **`m4`'s boundary wells are a prefix of `m0`'s**; `m0` is *bit-identical* (`torch.equal`) to plain `batch_lse`; short-ball fallback restores the full budget |

**Total new tests: 38, all green. Full suite: 1,408 passing, 0 failing.**

### 2.3 🔴 A test of mine was wrong, and the code was right

`test_prevalence_is_the_true_grid_fraction_at_or_above_tau` asserted `601/1001` and failed.
I checked the arithmetic before touching either side: `linspace(0,1,1001)` puts exactly `0.6`
at index 600, so indices 600–1000 qualify — **401**, not 601. I had counted from the wrong
end of the ramp.

This is the same defect §5 records for the first `tau_max` test, which hardcoded the textbook
`z = 1.645` against a module using the exact inverse-normal CDF. Recorded here rather than
quietly corrected, and the fixed test now also asserts `truth[600] == 0.6`, because 401 is
only the right answer if `linspace` hits the endpoint exactly.

### 2.4 A defect in my own runner, caught before it ran

The first draft of `run_final_spade_benchmark.py` computed the type I / type II error volumes
by hand and left a **dead line that assigned `type_i` twice**. Replaced with
`boec.calibration.error_volumes` — the registered Azzimonti & Ginsbourger derivation, already
validated against the committed `iou_pred` column, and already what `conservative_columns`
uses for the certificate. Two derivations of one quantity inside one runner is the
"two sources of truth" defect again.

---

## Part 3 · 🔴🔴 THE FEASIBILITY GATE FIRED — and it caught a defect in my own registration

**This is the most important result so far, and it is a result about the study design, not
about SPADE.**

`results/final-spade-feasibility.json`, 14 cells, 7 conditions × 2 thresholds, 20-campaign
plate-1 pilot each.

### 3.1 What came back

```
 X C1  hill        d=6 s=0.25  tf=0.60  tau=0.6000 prev=0.7069 ne=0.20  INFEASIBLE
 X C1  hill        d=6 s=0.25  tf=0.75  tau=0.7500 prev=0.2792 ne=0.00  INFEASIBLE
    C2  hill       d=6 s=0.10  tf=0.60  tau=0.6000 prev=0.7069 ne=1.00  ROBUSTNESS
 ** C2  hill       d=6 s=0.10  tf=0.75  tau=0.7500 prev=0.2792 ne=0.85  TARGET
 X C3  hartmann6   d=6 s=0.25  tf=0.60  tau=0.6000 prev=0.0080 ne=0.00  INFEASIBLE
 X C4  hartmann6   d=8 s=0.25  tf=0.60  tau=0.6000 prev=0.0076 ne=0.00  INFEASIBLE
 X S1  ackley      d=6 s=0.25  tf=0.60  tau=0.6000 prev=0.0000 ne=0.00  INFEASIBLE
 X S2  levy        d=6 s=0.25  tf=0.60  tau=0.6000 prev=0.8575 ne=0.40  INFEASIBLE
 X S3  rosenbrock  d=6 s=0.25  tf=0.60  tau=0.6000 prev=0.9555 ne=0.35  INFEASIBLE
```

**12 of 14 INFEASIBLE. 1 TARGET. 1 ROBUSTNESS.** Including **C1 — the continuity condition,
the single point in this entire project where SPADE's certificate has ever been measured.**

### 3.2 The cause, verified rather than guessed

```
tau_max(gamma=0.95, sigma_rel=0.25) = 1 - 1.6449 x 0.25 = 0.5888
```

The registered thresholds were `τ_f ∈ {0.60, 0.75}`. **Both sit above 0.5888.**

**This is §4.5's defect, recurring, and I committed it.** §4.5 records an earlier draft of
this project registering absolute thresholds {0.70, 0.80, 0.85, 0.90} with *all four above
the ceiling* — every arm would have certified nothing and the table would have been zeros,
read inevitably as a method failure. I re-made the same mistake in a different
parameterisation, one document after quoting the warning.

**The gate existed to catch exactly this, ran before any campaign, and caught it.** No
compute was spent on unevaluable cells. That is the system working as designed, and it is the
strongest single argument for the brief's insistence that feasibility be committed first.

### 3.3 Two further findings the gate produced for free

**(a) `τ_frac` equalises nothing across families.** Measured true prevalence at `τ_f = 0.60`:

| family | ackley | hartmann6 | hill | levy | rosenbrock |
|---|---|---|---|---|---|
| prevalence | **0.0000** | 0.0080 | 0.7069 | 0.8575 | **0.9555** |

A common `τ_frac` poses a **completely different question** on each family. This reproduces
§9.8's finding prospectively and independently.

**(b) A statement about assurance and noise, not about any method.** At `σ_rel = 0.25` the
ceiling 0.5888 corresponds to a true prevalence of ≈ 0.71 on hill. So **every** threshold
certifiable at `γ = 0.95` and that noise level describes a region covering **more than 70% of
the box**.

> **At 25% relative noise, γ = 0.95 admits no *nontrivial* certifiable region on the primary
> oracle.** No method can fix this; it is the ceiling, and it is reportable in its own right.

### 3.4 The amendment — Erratum 1, registered before any arm result existed

Two changes, both adopting machinery this project **already registered and committed**:

1. **The threshold estimand becomes `tau_q`** — P5's per-family prevalence quantile (§9.8),
   read from the committed `results/p5-tau-quantile.json` and **never recomputed**, at
   `p ∈ {0.10, 0.25}`. This puts true prevalence inside the TARGET band `[0.05, 0.60]`
   **by construction on every family**, which is precisely what `tau_q` was built for.
2. **Primary `γ` becomes σ-dependent:** `γ = 0.95` at `σ = 0.10`; `γ = 0.50` at `σ = 0.25`,
   with `γ = 0.95` retained there as a reported diagnostic. Forced by §3.3(b) — insisting on
   γ = 0.95 at σ = 0.25 would test the ceiling rather than the method.

**What the amendment may not be used for.** It changes *which cells are evaluable*. It relaxes
**no** decision rule, SESOI, Holm family, or kill condition. No arm outcome existed when it
was written, and that is checkable from the commit graph:
`results/final-spade-primary.json` did not exist at the erratum's commit.

**Consequence for scope, recorded now rather than discovered in the write-up:** the study's
high-assurance (γ = 0.95) evidence can only come from **σ = 0.10**. Any σ = 0.25 certificate
claim is a **γ = 0.50 claim** and every table must say so.
