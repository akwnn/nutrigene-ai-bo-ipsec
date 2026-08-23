# SPADE-FINAL — the frozen specification for the prospective confirmatory study

**Study ID:** `spade-final-2026-08-23`
**Frozen at commit:** *(this file's first commit — recorded in `results/final-spade-manifest.json`)*
**Namespace:** every artefact of this study is named `final-spade-*` or `final_spade_*`.
No file of any earlier track is modified, overwritten, or deleted.

> **This document is frozen before any final-study number exists.** Amendments are permitted
> only as numbered errata appended to §12, each committed *before* the result it would
> affect. An amendment made after seeing an outcome it bears on is a protocol violation and
> must be recorded as one.

---

## 1. The question, and the claim boundary

**Question.** When a practitioner needs a reliable *certified operating region* — not merely
one nominated best recipe — does a two-round, boundary-directed SPADE procedure provide a
**valid** certificate and a **meaningful** operational or map-quality advantage over strong
BO, DoE, and space-filling baselines?

**The claim this study may support, at most** (conditional, and no wider):

> In feasible response-surface settings with a nontrivial acceptable-region boundary, where
> a user needs a validated operating region and substantial boundary uncertainty remains
> after an initial global design, SPADE's two-round boundary-directed sampling produces an
> empirically valid certificate and improves region estimation beyond Plate-1-only and
> random second-plate sampling, while remaining competitive with strong BO baselines.

**The claim this study may never support:** that SPADE beats Sobol, BO, or DoE everywhere.
The repository already refutes it — `docs/FINDINGS-SPADE.md` §42 characterises SPADE as a
**low-variance middling arm** on the BO community's own conventions, and §41 records that on
`ackley` SPADE **certified nothing in 1,200 campaigns**.

### 1.1 Why this study is not redundant

`docs/FINDINGS-SPADE.md` §43.5: **"Version C has never been run as a method. Every number is
Version B's wells scored under Version C's rules."** Every committed SPADE certificate figure
in this project is a *re-score*. A re-score cannot test an *allocation* rule, because the
allocation already happened. The `m0/m4/m8` question is therefore answerable **only**
prospectively, and it is the reason this study generates fresh campaigns rather than
re-scoring committed ones.

---

## 2. Definitions — fixed for code, tables, figures and prose

| symbol | meaning | this study's values |
|---|---|---|
| `f(x)` | true (noiseless) response at recipe `x` in the unit box | oracle-supplied |
| `τ` | minimum acceptable performance, **raw units** | derived, see §5 |
| `D = {x : f(x) ≥ τ}` | the **true acceptable region** | |
| `γ` | **point-level** confidence. Admit `x` iff `μ(x) − z_γ·s(x) ≥ τ` | **0.50, 0.95** primary; **0.99** diagnostic only |
| `α` | **whole-region** assurance: `P(certificate ⊆ D)` | **0.80, 0.95** |
| `τ_f` | normalized threshold, `τ = τ_f · μ_max` | **0.60** moderate, **0.75** challenging |
| `τ_max` | certifiability ceiling — above it **no method certifies at any budget** | computed per cell |
| `m` | plate-2 wells spent on local exploitation instead of boundary refinement | **0, 4, 8** |

**γ and α are different objects and are never conflated.** γ is a per-point margin; α is a
statement about the whole reported set. A table that reports one without naming the other is
a protocol violation (§9.4).

### 2.1 The certificate estimator — cross-fit, and why

**Official protocol.** Draw `N_DRAWS` joint posterior samples on the evaluation subset.
Split them deterministically in half: the **selection** half chooses the conservative
estimate `CE_α`; the **evaluation** half scores it. Report cross-fit containment as primary.
Same-draw containment is emitted, labelled non-primary, and reported *beside* it as a
diagnostic — never as evidence.

**Implementation is reused, not rebuilt:** `boec.vorobev.conservative_estimate_split`
(`src/boec/vorobev.py:160`) and `boec.versionc.conservative_columns`
(`src/boec/versionc.py:144`). Building a parallel containment implementation would create two
sources of truth for the study's primary safety endpoint — the exact defect §9.5 and §14
punished this project for.

**`N_DRAWS = 4096`, and it is not negotiable.** §29 (`results/f3-draw-sweep.json`) measured
containment against draw count and found §14's four sub-nominal cells were an artefact of
512 draws: the worst cell runs 0.860 → 0.980 between 512 and 1,024 draws and then flattens.
§29.3 then measured the *residual* selection bias at 4,096 draws at 1.5–3.5 points,
concentrated where the Vorob'ev quantiles tie. **4,096 draws plus the cross-fit is the
minimum configuration at which a containment number in this repository has ever been
trustworthy.** A 1,024-draw sensitivity may be reported; it is not the primary result.

**The empty set is never scored as a success.** `empirical_containment` returns `None` for an
empty mask and `conservative_estimate_split` returns `nan`; both are carried through as
missing, never as 1.0. An arm that certifies nothing scores **no** containment, and its
empty rate is reported alongside every containment figure.

---

## 3. The frozen method arms

### 3.1 `spade_cf_m0` — the primary SPADE arm

| stage | specification |
|---|---|
| Plate 1 | `static_design(bounds, "lhs", N_PLATE1, seed)` — the approved global space-filling design |
| Surrogate | `build_gp(X, Y, Yvar, bounds)` — Matérn-5/2 ARD, `Yvar` plugged in as known. No post-hoc model selection. |
| Plate 2 | `batch_lse(adapter, cand, theta, q=N_PLATE2, exclude=exclusion_radius(model), sigma=None)` — batch level-set estimation on the acceptability boundary, latent straddle |
| design θ | `DESIGN_TAU_FRAC · μ_max`, with `DESIGN_TAU_FRAC = 0.75` frozen |
| candidates | `sobol_grid(dim, CAND_N=4096, seed=seed)` |
| Certificate | `CE_α` selected on the selection draws, scored on the evaluation draws (§2.1) |
| **Stage-0 detector** | **ABSENT.** K-C7 fired: the detector separated **0/50** on both held-out families (§37). It gates nothing in this study. |
| **Trust region stage** | **ABSENT** except as the registered `m>0` variants below. |

Budgets: `N_PLATE1 = 40`, `N_PLATE2 = 8`, total **48 wells**, **2 rounds**.

### 3.2 `spade_cf_m4`, `spade_cf_m8` — the allocation variants

Identical to `spade_cf_m0` in every respect except that `m` of the 8 plate-2 wells are placed
by the **local rule L1** below, and the remaining `8 − m` by the *identical* `batch_lse` call.

These are **co-primary design variants, not improvements.** An `m > 0` arm may be called
better only under §7.3's conjunction.

#### Local rule **L1** — frozen, deterministic, plate-1 information only

1. Fit the plate-1 GP. Read `ℓ = ard_lengthscales(model)` (`src/boec/versionc.py:74`).
2. `x̂ = argmax` of the plate-1 **posterior mean** over the *same* frozen candidate set
   `cand` that plate 2 uses. **Deliberately a grid argmax, not a continuous optimizer:** §4.1
   records that this project's one non-reproducible path was a post-hoc L-BFGS-B locator with
   20 restarts. A grid argmax over a seeded Sobol set is bitwise reproducible.
3. **Trust region = the ARD ball of radius 1 about `x̂`**:
   `{x : ‖(x − x̂)/ℓ‖₂ ≤ 1}`.
   **The radius is 1 because that is literally `n_effective`'s bound**
   (`src/boec/versionc.py:91`), so every local well provably increments the statistic §9.3
   identified as governing the identification gap. The radius is *not* a tuned constant; it
   is inherited from the registered formula.
4. Select the `m` local wells by **greedy farthest-point** (maximin, ARD metric) from the
   union of the plate-1 design and the already-chosen local wells, restricted to candidates
   inside the ball. Ties broken by lowest candidate index — deterministic.
5. If fewer than `m` candidates lie inside the ball, take all of them, record
   `m_local_short = True`, and **fall back to the boundary rule for the remainder**. This is
   recorded per row, never silently absorbed.

**L1 may not inspect:** plate-2 outcomes, any truth value at an unobserved location, final
map metrics, final regret, or any competitor's output. Enforced by tests (§13.3) and by the
fact that L1's signature takes no `truth` argument — the same architectural guard
`src/boec/versionc.py` uses for the detector statistics.

### 3.3 The causal controls

| arm | plate 1 | plate 2 | tests |
|---|---|---|---|
| `spade_plate1_only` | identical | **none** (40 wells, 1 round) | does plate 2 do anything at all? |
| `spade_random_plate2` | identical | 8 wells, frozen RNG, uniform | **does *boundary targeting* earn its complexity, or is it just 8 more wells?** |

`spade_cf_m0` vs `spade_random_plate2` is **the** load-bearing causal comparison of the
study. `spade_plate1_only` is budget-short by 8 wells and is therefore reported as a
**rounds/wells reference, not an equal-well comparator** (§4.1).

---

## 4. The benchmark arm registry

Every primary condition runs **all** of the following, or records a structured
`unavailable_reason`. A missing mandatory comparator is a **hard failure** that blocks any
primary conclusion (§13.6).

| arm | family | rounds | mandatory |
|---|---|---|---|
| `spade_cf_m0` | SPADE | 2 | ✅ |
| `spade_cf_m4` | SPADE | 2 | ✅ |
| `spade_cf_m8` | SPADE | 2 | ✅ |
| `spade_plate1_only` | SPADE control | 1 | ✅ |
| `spade_random_plate2` | SPADE control | 2 | ✅ |
| `sobol` | space-filling | 1 | ✅ **the strongest simple map baseline; §13/§19 show it beating BO arms** |
| `lhs` | space-filling | 1 | ✅ |
| `random` | space-filling | 1 | ✅ |
| `qlognei` | BO | 10 | ✅ **the noisy acquisition — the Q57 trap arm** |
| `qlogei` | BO | 10 | ✅ |
| `doe` | classical RSM | 3 | ✅ where the design is feasible |
| `doe_unscreened` | classical RSM | 3 | ✅ **only where arithmetically feasible at 48 wells** |
| `qlogei-addonly` | BO, additive kernel | 10 | ⚠️ **sensitivity only**, and only if its re-score status is confirmed VALIDATED first |

**On `qlogei` vs `qlognei`.** Both are mandatory because §4.2b records the **Q57 trap**: a
headline that holds against `qLogEI` and dies against the noisy acquisition. Running only the
weaker one would manufacture a win.

**On `doe_unscreened` at d = 8.** A full second-order RSM in `d = 8` needs 45 coefficients; at
a 48-well shared budget that leaves ~3 residual degrees of freedom. If the arithmetic does not
close, the arm is recorded `unavailable_reason = "second-order RSM infeasible at shared
budget"` **before any run**, and it is never approximated into existence (§14).

---

## 5. Conditions, and the pre-run regime classification

**Regime class is assigned from oracle geometry and a frozen plate-1 pilot ONLY — never from
final-study arm performance.** A cell cannot be relabelled `TARGET` after outcomes are known
(§13.4).

### 5.1 The frozen classification rules

| class | all of these must hold |
|---|---|
| **TARGET** | `τ < τ_max(γ)` at **both** primary γ; true prevalence ∈ **[0.05, 0.60]**; pilot expected non-empty certificate rate ≥ **0.50**; pilot boundary uncertainty `boundary_frac` ≥ **0.05** |
| **ROBUSTNESS** | feasible (`τ < τ_max`), but fails one or more TARGET criteria on prevalence/emptiness/boundary |
| **EXCEPTION** | feasible, **and** pre-specified structural reason SPADE is not expected to win (centre-point optimum; negligible post-plate-1 boundary uncertainty; the task is point optimisation) |
| **INFEASIBLE** | `τ ≥ τ_max(γ)`, or the true region is degenerate (prevalence < 0.01 or > 0.99), or no valid non-empty certificate is assessable. **Excluded before campaigns run. Never a method failure.** |

`boundary_frac` is defined as the mean over pilot campaigns of the grid fraction with
`|μ(x) − θ| ≤ 1.96·s(x)` after plate 1 — the straddle band, i.e. the region plate 2 exists to
resolve. Pilot = **20 campaigns, `spade_plate1_only`, seeds 0–19**, frozen.

### 5.2 The primary matrix

| id | family | d | σ_rel | why it is in |
|---|---|---|---|---|
| **C1** | hill | 6 | 0.25 | **continuity** — the one point where SPADE's certificate has ever been measured (§8). Re-measured here under the cross-fit protocol, prospectively. |
| **C2** | hill | 6 | 0.10 | **main TARGET candidate** — §13 records SPADE arms 1st–3rd of 12 on the map here while 9th–11th on regret. |
| **C3** | hartmann6 | 6 | 0.25 | **cross-family stress.** §37/§42 predict SPADE struggles; an `EXCEPTION`/`ROBUSTNESS` classification here is expected and is reported, not hidden. |
| **C4** | hartmann6 | 8 | 0.25 | **dimension stress.** `doe_unscreened` expected `unavailable`. |

### 5.3 Secondary conditions — run only after every primary condition is complete and valid

| id | family | d | σ_rel | expected class |
|---|---|---|---|---|
| S1 | ackley | 6 | 0.25 | **EXCEPTION.** §41: SPADE certified nothing in 1,200 campaigns. Its centre-point optimum advantages classical designs, and that is reported plainly. |
| S2 | levy **or** rosenbrock | 6 | 0.25 | included only if feasibility finds a nondegenerate `τ < τ_max`. §41 records rosenbrock/levy under-covering at γ=0.99. |

Secondary results are **robustness/context** and may not carry a confirmatory endpoint.

### 5.4 Noise-stream independence

§9.7 established that `BiphasicOracle` seeds on `seed` alone and never on σ, so σ=0.25 and
σ=0.10 are **one noise realisation at two amplitudes** (bitwise-identical regret in 34/50
`doe` pairs). This study keys the noise stream on
`(family, d, σ, instance_seed, campaign_seed)` and **tests that the two σ levels are not
scaled copies** (§13, `test_noise_streams_are_independent_across_sigma`). If backward
compatibility forces the shared stream, C1 and C2 are analysed **separately** and never
pooled as independent replicates — declared, not assumed.

---

## 6. Sample sizes, draws, and evidence floors

| | value | rationale |
|---|---|---|
| campaigns per arm per primary condition | **100** | map, calibration, regret benchmark |
| campaigns for primary high-assurance certificate cells | **200** target | §29's powered test used n=200; Erratum 21 showed it was needed |
| posterior draws | **4096**, split 2048/2048 | §2.1 |
| draw split | deterministic, `split_seed` recorded per row | |
| `n_rho` | 64 | matches the committed estimator; §29.1 showed the result is insensitive to it |
| **non-empty evidence floor** | **10** | a cell with < 10 non-empty certificates cannot support a containment claim; appendix only, with denominator |

**If compute cannot reach 200 for a high-assurance cell, the sample size is NOT silently
reduced.** The 100-campaign benchmark completes and the cell is labelled **INCONCLUSIVE**,
never confirmatory.

---

## 7. Primary endpoints and decision rules

### 7.1 Certificate validity — the primary safety endpoint

Per SPADE arm × condition × τ_f × γ × α, report: cross-fit containment `X/n`, proportion,
**exact** Clopper–Pearson interval, **exact** one-sided lower-tail p-value
(`scipy.stats.binom.cdf`), Holm-adjusted p, non-empty count, empty rate, same-draw
containment, and the same-draw minus cross-fit difference.

| verdict | condition |
|---|---|
| **PASS** | adequate non-empty denominator (≥10), **not** demonstrably below nominal under the exact test and the frozen Holm family, feasible/nondegenerate cell, cross-fit primary, same-draw gap reported |
| **FAIL** | demonstrably below nominal under the exact one-sided test after Holm |
| **INCONCLUSIVE** | denominator < 10, or underpowered, or infeasible |

**Non-significance is not proof of validity.** A cell with n=12 that fails to reject is
INCONCLUSIVE-leaning and must be reported with its interval, not as a pass.

### 7.2 Map quality — the primary map endpoint

**Primary scalar: predictive symmetric-difference error volume** = type I + type II. Lower is
better. Always reported alongside: type I alone, type II alone, Brier, Murphy calibration,
Murphy refinement, AUC (**secondary only**), IoU and false inclusion where defined with
denominators, rankability denominator, and empty-region rate.

**⚠️ Type I volume read alone ranks silence first** — an arm certifying the empty set scores
exactly 0 (§9.4). The analyser must refuse to emit a type-I-only ranking (§13.5).

**AUC is secondary, not primary** — it is invariant to monotone transformation and therefore
cannot see calibration, and mean `grid_r2` is negative for all eight arms (§9.4). §24 revises
the *grounds* for that supersession without restoring AUC.

### 7.3 The boundary-targeting claim — does plate 2 earn its complexity?

Targeted plate 2 earns its place **only if `spade_cf_m0` beats `spade_random_plate2`** on
symmetric-difference error by ≥ SESOI in a TARGET condition, **and** does not produce worse
cross-fit certificate validity, **and** does not materially worsen calibration.

If it fails: state plainly that **targeted plate-2 SUR did not demonstrate value beyond
random second-plate wells**, and remove the mechanistic claim from the paper.

### 7.4 Regret

Compute under **both** terminal rules for every arm:

* **Rule A** — the established observed-data terminal choice.
* **Rule P** — the posterior-mean terminal choice.

**Primary estimand for the final paper: Rule P**, because the paper asks which campaign
produces the strongest final *model-based* recipe decision. Rule A is a **required**
robustness outcome. Every regret table and figure names its rule. **Comparing rule A for one
arm against rule P for another is a protocol violation** — §43.1 records this project doing
exactly that and having to withdraw the claim (K-C1's bar mixed estimands; like-for-like the
gap fell inside SESOI and the claim became *parity, not a win*).

### 7.5 The allocation claim

`m > 0` is an **improvement** only under the full conjunction, in a TARGET condition:

1. reduces primary-rule (P) regret by ≥ **SESOI 0.02**; **and**
2. does not worsen symmetric-difference map error by more than **0.02**; **and**
3. does not worsen Murphy calibration beyond **0.005**; **and**
4. retains **PASS** or non-inferior cross-fit certificate validity.

**A regret reduction that damages the certificate is not a SPADE improvement.** It is
reported as a **trade-off**.

---

## 8. Statistical plan

* **Pairing.** Matched oracle instances and matched campaign seeds across arms. Paired
  bootstrap intervals; **Wilcoxon** governs yes/no per Q20 §2; bootstrap reports the interval.
* **Unit.** `n=25` (seeds averaged within instance) is the default for **unpaired** quantities
  — arm means, prevalence, containment proportions — per §9.6's measured ICC. Paired contrasts
  report **both** units and the analysis fails loudly if they disagree in direction.
* **Containment inference is EXACT.** `scipy.stats.binom` tails and Clopper–Pearson
  intervals. **A normal approximation anywhere in certificate inference is a hard failure**
  (§13.5) — §22 records this project's Holm correction being computed with a normal
  approximation and not surviving the exact tail.
* **SESOI = 0.02** (regret and symmetric difference), inherited from the project registration.

### 8.1 The four frozen Holm families

Frozen here, before any result. They are **not** combined, split, or redefined afterwards.

| family | membership |
|---|---|
| **F-CERT** | all primary SPADE cross-fit certificate cells |
| **F-BOUND** | `m0` vs `random_plate2` and `m0` vs `plate1_only`, across TARGET primary conditions |
| **F-ALLOC** | all `m0`/`m4`/`m8` comparisons across TARGET primary conditions |
| **F-MAP** | `m0` vs `sobol`, `qlognei`, `doe` on primary symmetric-difference outcomes |

### 8.2 Pooling — the analyser hard-fails on all of these

1. multiple `τ_f` from the same campaign pooled as independent containment observations
   (§9.5: **eleven** pooling sites were found, not the one flagged);
2. multiple γ from the same campaign pooled without the planned repeated-measures treatment;
3. dependent σ results pooled where the base noise stream is shared (§9.7);
4. empty and non-empty certificate outcomes pooled without preserving the denominator;
5. a required arm missing from a primary-condition benchmark.

---

## 9. Publication guards

The release validator hard-fails on:

1. "best", "winner", "certified", "calibrated", "significant", "improved", "outperforms"
   where the matching registered decision condition did not pass;
2. a table without condition labels, terminal rule, or denominators;
3. same-draw containment presented as primary;
4. a normal approximation in certificate inference;
5. a conclusion suppressing a failure, exception, unrankable cell, or unavailable arm;
6. a **universal** claim where only TARGET-regime evidence exists;
7. `alpha_star` offered as evidence of certificate quality — §28/§31 **declared** it is not;
   it measures *willingness to certify*.

---

## 10. Kill ledger — registered before any result

Every item resolves to `PASS` / `FAIL` / `INCONCLUSIVE` / `NOT_RUN` / `MOOT`, with effect,
interval, p, adjusted p, SESOI comparison, denominator, and source artefact path + key.

| id | claim | fires when |
|---|---|---|
| **KF-1** | SPADE's certificate is valid prospectively under cross-fit | any primary F-CERT cell demonstrably below nominal after exact test + Holm → **FAIL** |
| **KF-2** | Certificate validity extends beyond hill d=6 σ=0.25 | C3/C4 INCONCLUSIVE or FAIL → the claim narrows to hill |
| **KF-3** | Targeted plate 2 earns its complexity | `m0` does not beat `random_plate2` by ≥SESOI on symmetric difference in any TARGET condition → **FAIL**, mechanism claim removed |
| **KF-4** | Plate 2 does anything at all | `m0` does not beat `plate1_only` on symmetric difference → **FAIL** |
| **KF-5** | `m>0` lowers regret safely | §7.5 conjunction unmet → **trade-off**, not an improvement |
| **KF-6** | SPADE is competitive with Sobol on the map in TARGET regimes | `sobol` beats `m0` by >SESOI in a TARGET condition → the paper says so |
| **KF-7** | SPADE is competitive with qLogNEI on the map in TARGET regimes | as KF-6 |
| **KF-8** | Regret is at practical parity under a common terminal rule | `m0` − best BO regret > SESOI under rule P → SPADE is a **certification-first trade-off**, stated as such |
| **KF-9** | The study's cells are feasible | any planned cell with `τ ≥ τ_max` → **INFEASIBLE**, excluded pre-run, never a method failure |
| **KF-10** | Empty-set degeneracy does not explain a pass | any PASS cell with empty rate > 0.50 → downgraded to **INCONCLUSIVE** |

### 10.1 The broad-paper condition

The broad SPADE-method paper is supportable only if **all** hold. If any fails, **the paper
claim narrows** — it is never hidden:

1. cross-fit certificate validity supported in primary conditions;
2. evidence extends beyond the single historical condition;
3. SPADE competitive with Sobol and qLogNEI on map quality in TARGET regimes;
4. targeted plate 2 earns its role, **or** the mechanistic claim is explicitly removed;
5. calibration reported honestly;
6. regret at practical parity under a common terminal rule, **or** presented as an explicit
   certification-first trade-off;
7. every artefact regenerates from frozen code and manifests.

---

## 11. Prohibited actions

Tuning SPADE after seeing final results · removing Sobol/qLogNEI/DoE/plate1-only/random-plate2
because they perform well · AUC alone for map quality · `alpha_star` as certificate evidence ·
reusing draws for selection and primary validation · normal approximations in low-count
high-assurance binomial tests · pooling non-independent thresholds or assurance levels ·
reporting a certificate rate without its non-empty denominator · treating an above-ceiling
target as a method failure · comparing regrets under different terminal rules as one estimand
· calling practical parity a superiority win · calling high same-draw containment proof of a
valid certificate · fabricating `doe_unscreened` at d=8 · claiming universal superiority from
a selected target regime · hiding a negative, null, exception or infeasible result ·
overwriting historical committed artefacts.

---

## 12. Errata

### 🔴 Erratum 1 — I registered thresholds above the ceiling, and the gate caught it

**Committed before any campaign ran and before any arm result exists.**
Evidence: `results/final-spade-feasibility.json` at code commit `f3b2b3f`.

**The defect.** §5.2 registered `τ_f ∈ {0.60, 0.75}` as fractions of `μ_max`, with `γ = 0.95`
primary. At `σ_rel = 0.25` the certifiability ceiling is

```
tau_max(gamma=0.95, sigma_rel=0.25) = 1 - 1.6449 * 0.25 = 0.5888
```

**Both registered thresholds sit above it.** The gate returned **INFEASIBLE for 12 of 14
planned cells**, including **C1 — the continuity condition, the single point where SPADE's
certificate has ever been measured.**

This is **§4.5's defect, recurring, committed by me.** §4.5 records an earlier draft of this
project registering absolute thresholds {0.70, 0.80, 0.85, 0.90} with *all four above the
ceiling*, so every arm would have certified nothing and the published table would have been
zeros. I re-made the same mistake in a different parameterisation. **The gate existed
precisely to catch it, ran before any campaign, and caught it.** That is the system working,
and it is recorded as a defect rather than smoothed over.

**A second, independent finding the gate produced.** `τ_frac` does not equalise anything
across families. Measured in this run, true prevalence at `τ_f = 0.60`:

| family | ackley | hartmann6 | hill | levy | rosenbrock |
|---|---|---|---|---|---|
| prevalence | **0.0000** | 0.0080 | 0.7069 | 0.8575 | **0.9555** |

A common `τ_frac` therefore poses a **completely different question** on each family. This is
§9.8's finding reproduced prospectively.

**And a finding about the noise level itself, not about any method.** At `σ_rel = 0.25` the
ceiling 0.5888 corresponds to a true prevalence of ≈ 0.71 on hill. So **every** threshold
certifiable at `γ = 0.95` and that noise level describes a region covering more than 70% of
the box. **At 25% relative noise, γ = 0.95 admits no *nontrivial* certifiable region on the
primary oracle.** That is a statement about assurance and noise, and it is reportable in its
own right.

**The amendment.** Two changes, both adopting machinery this project already registered and
committed rather than inventing anything:

1. **The threshold estimand becomes `tau_q`** — the per-family prevalence quantile of P5
   (§9.8), read from the **committed** `results/p5-tau-quantile.json`, never recomputed.
   **`p ∈ {0.10, 0.25}`**, both already in that committed table. This puts true prevalence
   in the TARGET band `[0.05, 0.60]` **by construction on every family**, which is exactly
   what `tau_q` was built for. `τ_frac` is not deleted — it is simply not this study's
   estimand.
2. **The primary `γ` becomes σ-dependent:** `γ = 0.95` at `σ_rel = 0.10`; `γ = 0.50` at
   `σ_rel = 0.25`, with `γ = 0.95` retained there as a **reported diagnostic**. Forced by
   the arithmetic above: at σ=0.25 there is no nontrivial threshold below the 0.95 ceiling,
   so insisting on γ=0.95 there would test nothing but the ceiling.

**What this amendment may not be used for.** It changes *which cells are evaluable*. It does
**not** relax any decision rule, SESOI, Holm family, or kill condition, and no arm outcome
existed when it was written. If a later reader suspects it was chosen to flatter SPADE, the
check is that it was committed at a point where `results/final-spade-primary.json` did not
exist — verifiable from the commit graph.

**Consequence for scope, stated now:** the study's high-assurance (`γ = 0.95`) evidence will
come from `σ = 0.10`. Any `σ = 0.25` certificate claim is a `γ = 0.50` claim and must say so
in every table.
