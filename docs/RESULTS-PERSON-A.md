# Person A — everything built, every number, every defect found

**Requested log of A's lane.** Person B's results live in `results/E4-RESULTS-v2.md`,
`results/EXPLORATORY-disagreement.md` and `results/NEGATIVE-shape-aware-mean.md`.

Every number here is reproducible from a committed script; the reproduction command is
named beside each. Nothing is quoted from memory.

**Suite: 422 passing** at the time of writing (233 B, the rest A's).

---

## 1. THE HEADLINE — in the pre-registered primary cell, Bayesian optimization loses

`python scripts/run_e2.py` · `results/e2.log` · pre-registered in `configs/experiment/e2.yaml`

**d=6, σ_rel = 0.25, 25 landscapes × 2 seeds, paired at instance level (n=25):**

| arm | simple regret (median) | vs qLogEI | Wilcoxon p |
|---|---|---|---|
| **doe** | **0.0957** | **−0.0595** [−0.0792, −0.0373] | **0.0000** |
| lhs | 0.1271 | −0.0282 [−0.0477, −0.0084] | 0.0147 |
| qlognei | 0.1366 | −0.0020 [−0.0250, +0.0209] | 0.7112 |
| coord | 0.1393 | −0.0133 [−0.0415, +0.0136] | 0.3388 |
| **qlogei** | **0.1484** | — | — |
| sobol | 0.1530 | +0.0171 [−0.0127, +0.0484] | 0.3123 |
| random | 0.2308 | +0.0664 [+0.0419, +0.0909] | 0.0000 |

**The sequential-DoE pipeline — the procedure the published study actually ran — beats
qLogEI decisively.** qLogEI's only significant win in this cell is over random search.

> **⚠️ CORRECTED (T2.3 / Q39). "Latin hypercube beats it too" has been removed.** That
> comparison is one of **39 non-primary contrasts** in this project, and `e2.yaml`
> registers `report_all_comparisons: true` without specifying a multiplicity correction.
> Under Holm it does **not** survive: **p 0.0147 → 0.1914**. LHS is a *suggestive* effect
> of −0.0282 at this cell, not a finding. The same correction removes the two other LHS
> cells and qLogNEI's only significant win. **The DoE contrast is the registered primary
> (`e2.yaml` `primary_domain`), is exempt from correction, and is unaffected at p=0.0000.**

**It survived both scoring corrections, which is why it is reportable.** Run 1 showed DoE
ahead by 0.0158 and A attributed it to a scoring bug. With the bug fixed *and* the arms
genuinely paired, the gap is nearly **four times larger**. The artefact hypothesis is dead.

### The finding is dimension-dependent, and that is the actual result

| cell | outcome |
|---|---|
| d=6, σ=0.25 **(primary)** | BO **loses** to doe (p=0.0000, registered primary). lhs suggestive only (p=0.0147 → **0.1914** Holm) |
| d=6, σ=0.10 | BO beats random (p=0.0000) and sobol (p=0.0003); ties lhs, coord, doe |
| d=8, σ=0.25 | BO beats random, sobol and coord; **lhs does not survive Holm** (0.0187 → 0.2249). And the DoE arm was not in the race here (d=6 only) |
| d=8, σ=0.10 | BO beats random (p=0.0004); lhs does not survive Holm (0.0067 → 0.0942); ties sobol |

**Read it carefully.** The only difference between d=6 and d=8 is **two synthetic factors
that do not matter** — `n_active = 4` is held fixed at both dimensions precisely so this
comparison isolates the cost of nuisance dimensions. So whatever BO gains here, it does
not gain by optimising the relevant factors better.

**The mechanism has since been measured, and it is real but not the one stated.** It was
natural to attribute the gain to ARD coping with irrelevant ingredients, and an earlier
draft of this document said so without evidence. The lengthscale diagnostic (§6b, Q25)
measured ARD's active-versus-inert separation directly on these same campaigns, against a
permutation null. Two findings:

- **At the opening design, d=8 has already worked out which factors matter and d=6 has
  not.** d=6 sits exactly on its no-signal null (1.000 vs 1.000, p=0.29); d=8 is above it
  (1.150 vs 1.000, p=0.00035). The dimension contrast is significant — p=7.3e-04 at σ=0.25,
  p=8.6e-06 at σ=0.10.
- **By the final model that difference is gone** (1.403 vs 1.471, p=0.62). Both dimensions
  end up discriminating equally well.

So the advantage is one of **timing, not capability**: at d=6 the surrogate is blind for
roughly the first 30 of 48 evaluations, of which only 34 are adaptive at all. It is not that
ARD "copes better" at higher dimension — asymptotically it copes identically.

Two things follow, and they should both be in the paper rather than one of them.

1. The effect is real and now has a stated mechanism, which is worth reporting.
2. **It is confounded three ways and the confound should be printed, not buried.**
   `n_init = 2d+2`, so d=8 opens with 18 points against d=6's 14; and the 0.10 inert weight
   share is split 4 ways at d=8 versus 2, making each nuisance factor individually *more*
   inert and easier to detect. Dimension, opening-design size and per-factor inertness move
   together. Separating them needs a d=6 arm at n_init=18 — a new experiment, not proposed
   here. Separately, the DoE arm is d=6 only (`e2.yaml`: `doe: {dim: [6]}`), so the arm that
   beat BO at six factors was not in the race at eight; LHS does flip sign on its own
   (−0.0282 → +0.0380), so that is not the whole story, but the comparison is missing its
   strongest opponent from one side and should be written that way.

Context that makes the six-factor loss less surprising: in the published optimum four of
six ingredients sit at their limits — fibronectin pinned at its 22 µg/mL attachment floor,
two laminins dropped to zero at screening — so there is not much interior left to search.

### Two pre-registered side decisions paid off

**Q5 (qLogEI vs qLogNEI).** qLogNEI is directionally better in **3 of 4 cells**;
its one nominally significant cell, d=8/σ=0.10 (−0.0123, p=0.0275), **does not survive
Holm correction** (p → 0.3023, Q39), so it is directional only. Registering both was right:
switching silently would have been indistinguishable from tuning, and keeping only qLogEI
would have hidden it.

**Q3 (coordinate descent).** Ties qLogEI at d=6 (p=0.34, p=0.92), much worse at d=8
(+0.0679, p=0.0000). The oracle is a sum of coordinate-wise-unimodal terms; this was
disclosed in advance and the d=6 tie is the stated limitation appearing where predicted.

---

## 2. The DoE arm reproduces the published failure mode, unstaged

`python scripts/run_doe_arm.py` · `results/doe-arm.log`

E4's standing objection is that we choose κ, so of course the model extrapolates. **This
arm hides nothing** — it runs the published two-stage procedure over the full space, and
stage 2 is narrow only because the *screen* made it narrow.

| d=6, 10 landscapes × 2 seeds | σ=0.10 | σ=0.25 |
|---|---|---|
| predicted optimum fell **outside** stage 2 | **100%** | **100%** |
| confirmation **under-delivered** | **100%** | **100%** |
| over-prediction, median | **+0.73** | **+1.66** |
| sat *on* the stage-2 boundary | 0% | 0% |
| screen recovered the planted active factors | 94% | 86% |

Against a response whose maximum is **1.0**. The 0% on-boundary rate matters: this is
genuine extrapolation, **not** the constrained-optimiser signature §E9 identified in the
published optimum — so the two mechanisms are separable and can be discussed independently.

---

## 3. E3 — calibration, and the selection effect is real but not uniform

`python scripts/run_e3.py` · `results/e3.log` · 25 landscapes × 2 seeds per cell

**Coverage is below the nominal 0.95 in every cell.** Latent (the smooth response) and
predictive (what a lab measures) are reported separately because they answer different
questions.

| cell | latent @ proposed | latent @ holdout | predictive @ proposed | selection gap (latent) |
|---|---|---|---|---|
| d=6, σ=0.25 | 0.8189 | 0.8102 | 0.9156 | **+0.0086** [−0.0113, +0.0269] |
| d=6, σ=0.10 | 0.8500 | 0.9020 | 0.9028 | **−0.0520** [−0.0692, −0.0360] |
| d=8, σ=0.25 | **0.7644** | 0.8543 | 0.9087 | **−0.0900** [−0.1243, −0.0563] |
| d=8, σ=0.10 | 0.8912 | 0.9061 | 0.9175 | −0.0149 [−0.0341, +0.0027] |

**Two honest statements, and the second corrects something A said in chat first:**

1. **Latent uncertainty is substantially overconfident, worst at d=8 with high noise
   (0.764 against a nominal 0.95).** Adding observation noise recovers predictive coverage
   to ~0.90–0.92 everywhere. So the interval a lab would use is roughly trustworthy; the
   model's belief about the underlying smooth response is not.
2. **The selection effect is NOT uniformly negative.** It is clearly negative at
   d=6/σ=0.10 and d=8/σ=0.25, near zero at d=8/σ=0.10, and *positive* at d=6/σ=0.25.
   A initially described it as a general finding; on the full grid it is
   **regime-dependent**, and the d=8/σ=0.25 cell is the strongest case rather than the
   typical one.

---

## 4. E4 — reproduced, with structure the pooled number hides

`python scripts/run_e4.py` · `results/e4-rerun.log`

Reproduces B's v2 exactly: **GP vs the model-free null −0.0269 [−0.0728, +0.0182]**,
advantage bounded below 0.08, 100/100 cells extrapolated, **saddle 100/100**.

**For B: the pooled null averages over a sign flip.**

| κ | GP minus nearest-neighbour |
|---|---|
| 0.6 | **+0.1068** [+0.0461, +0.1668] — GP genuinely better |
| 0.7 | −0.0173 [−0.0745, +0.0415] |
| 0.8 | **−0.0960** [−0.1450, −0.0470] — GP significantly worse |
| 0.9 | **−0.1011** [−0.1481, −0.0561] — GP significantly worse |

"No advantage" is true and it hides a real κ-dependence.

---

## 5. E1 — the correctness gate. PASSED

`python scripts/run_e1.py` · `results/e1.log` · 20 seeds, budget 48

| function | d | known opt | BO | random | BO − random | 95% CI |
|---|---|---|---|---|---|---|
| branin | 2 | −0.3979 | −0.3747 | −1.0037 | +0.6290 | [+0.3454, +0.9723] |
| hartmann6 | 6 | 3.3224 | 2.8666 | 1.7819 | **+1.0847** | [+0.8016, +1.3641] ← **gate** |
| ackley | 6 | 0.0000 | −16.0458 | −15.8616 | −0.1842 | [−0.8187, +0.4685] |

Ackley's null was declared **in the script, before the run** — near-flat global structure at
d=6 gives a GP little to learn. Writing that down first is what stops a poor number being
explained away afterwards.

---

## 6. Pre-flight

### PF1 — the (κ, ρ) over-prediction surface
`python scripts/preflight_pf1.py` · `results/pf1-grid.log` · 40 instances × 4 κ × 5 ρ = 800 cells

Median over-prediction, against a response whose maximum is 1.0:

| κ | ρ=1.2 | ρ=1.5 | ρ=2.0 | ρ=3.0 | unit cube |
|---|---|---|---|---|---|
| 0.6 | 0.182 | 0.557 | 1.466 | 4.049 | **11.527** |
| 0.7 | 0.233 | 0.611 | 1.501 | 3.796 | 7.022 |
| 0.8 | 0.197 | 0.546 | 1.218 | 2.805 | 4.147 |
| 0.9 | 0.233 | 0.496 | 1.050 | 2.073 | 2.742 |

- κ trend **−0.2712** [−0.3988, −0.1450] — genuine.
- ρ trend +1.0000 [+1.0000, +1.0000] — **forced by geometry, not a finding.** See §7.
- Registered secondary (over-prediction falls with depth) **FAILED**: measured +0.3893 at
  κ=0.6. Refuted, reported as refuted; depth spans only [0.109, 0.139] so power was low.
- **Saddle in 800/800 cells.** Zero maxima, zero minima.

### PF2 — the maths the downstream numbers rest on
`python scripts/preflight_pf2.py`

1. `(x*=0.4, n=2, δ=0.414)` → **s = 3.9917** ✓, round-trip error 5.0e-16 over 2,000 draws.
2. Closed form on a γ=0 variant of all 50 instances: argmax matches `√(EC50·IC50)` to
   **1.1e-16**; `f(x_opt) − 1` is **3.3e-16**.
3. Acceptance: **6.395% (d=6) / 0.105% (d=8)** under the specification's own procedure,
   versus **70% / 80%** under the shipped sampler.
4. Shipped ensemble: **40 instances at d=6, 25 at d=8**; true depth median 0.1166 / 0.1177,
   min 0.1086 / 0.1111 — 100% clear the σ_rel = 0.25 threshold. Active-to-inert influence
   ratio **4.50× / 9.00×** against 1.0× under the spec.

---

## 6b. Lengthscale diagnostic — why BO lost at d=6

`scripts/diagnostic_lengthscales.py`; report in `results/diagnostic-lengthscales.log`; full
write-up in **Q25**. **Changes no E2 number.** Fidelity is asserted, not promised:
**200/200 regenerated campaigns reproduce their stored E2 `best` to 1e-9**, each row
carrying a hash of its design matrix, and the script aborts on any mismatch.

**Version 1 of this diagnostic was void and its conclusion was withdrawn.** It anchored on
the prior *median* (10.08) when the fit is MAP and the no-data attractor is the prior *mode*
(0.5016 — also the kernel's initialisation). Its opening-design median was 0.502, i.e. the
untrained value, which it scored as maximal learning. See defect 8 in §7 and `METHODS.md`
§2.9. Version 2 replaces the anchor with an **empirical no-signal null** — the same design
and noise refit on permuted outcomes — and decides on the **ARD separation ratio**, which
is immune to the error because the prior is identical on every dimension, so any uninformed
fit gives 1.00 by symmetry. Measured null over 200 runs: **1.006**.

### The finding

**d=8 begins the adaptive search already knowing which factors matter. d=6 begins blind.**

| cell | opening design | | final (n=46) | |
|---|---|---|---|---|
| | fit | p vs null | fit | p vs null |
| **d=6 σ=0.25** | **1.000** | **0.29 — nothing** | 1.403 | 0.00032 |
| d=8 σ=0.25 | **1.150** | **0.00035** | 1.471 | 0.00049 |
| d=6 σ=0.10 | 1.028 | 0.25 — nothing | 3.412 | 6.2e-14 |
| d=8 σ=0.10 | **1.718** | **8.1e-08** | 3.438 | 2.2e-14 |

At the opening design the dimension contrast is significant (p=7.3e-04 at σ=0.25, p=8.6e-06
at σ=0.10). **By the final model it has vanished** (p=0.62 and p=0.75). So the earlier
framing — mine — that "ARD copes better with nuisance dimensions at d=8" was wrong in its
mechanism: asymptotically the two dimensions discriminate identically. What differs is
*when*. At d=6 it takes ~30 evaluations of a 48 budget before ARD separates anything, and
only 34 of those are adaptive.

**Confound, declared:** `n_init = 2d+2` gives d=8 an 18-point opening against d=6's 14, and
the 0.10 inert share is split 4 ways at d=8 versus 2, so each nuisance factor is *more*
inert and easier to spot. Dimension, opening-design size and per-factor inertness move
together here and this diagnostic does not separate them.

### The prior is exonerated by a varied condition, not by a lengthscale value

The same recovered designs refit under `Gamma(3,6)` — one variable changed, by hand, because
the library's convenience constructor would have moved three. **Gamma roughly halves ARD
separation in every cell** (1.40→1.15, 3.41→1.84, 1.47→1.14, 3.44→1.85; all p ≤ 4.3e-06) and
is indistinguishable on posterior-mean argmax error (p = 0.15, 0.33, 0.40, 0.41 over 25
clustered instances). **The registered sensitivity re-run is not triggered and was not
performed** — and the counterfactual says running it would have made BO worse, which is
worth stating plainly given it was the change most likely to be demanded after a BO loss.

### What it cost

Shape skill on the active axes — 1 − var(residual)/var(truth), so a shape-blind predictor
scores 0 — is **0.162** in the primary cell against 0.530 at low noise, with no dimension
effect (p=0.22, 0.40). The surrogate captures a sixth of the shape variance along the axes
that matter, at a level error of 0.28, at points 0.41 from its nearest observation.
**Surrogate quality here is governed by noise, not dimension.**

qLogEI itself behaves sensibly: proposals close from 0.266 to 0.242 per-coordinate RMS on
the active subspace against a uniform null of 0.333, and boundary pinning falls on *inert*
coordinates 2.3× more often than active — correct behaviour. (Version 1's "36% of proposals
on the box against a 1.2% uniform reference" is withdrawn: a uniform draw is not the
operative null for a bounded acquisition maximiser.)

---

## 7. Defects found — the recurring pattern, which is the most useful output

**Twelve constructs that could not fail, were unfair, or were inferred wrongly, caught
before they reached a paper.** Eight were A's own. The consistency is the point: this is the default failure mode
of measurement code, not bad luck.

**Six of the twelve are the same specific pattern — a check whose name carries a guarantee
its body does not verify** (1, 2, 3, 6, 8, 10). That is the single most reproducible
finding in this project, and it is worth more than any individual defect: in every case
the check *ran*, *passed*, and was *quoted as evidence*. Defect 10 is the cleanest
example, because the passing output (16 factorial / 8 axial / 1 centre) was numerically
correct and still proved nothing — the counts were right while the design underneath them
was malformed.

| # | defect | consequence had it shipped |
|---|---|---|
| 1 | E4's non-separability acceptance check **could never pass** (the derivative bracket contains no `x_i`; measured shift 0.00e+00 over 276 instances) | The oracle's headline property was unverified |
| 2 | A's DoE arm let stage 2 span the whole space, so the predicted optimum **could not** fall outside it | Reported 0% escape over 40 runs — read as a clean negative, was a tautology |
| 3 | **A's own ρ pre-registration** was unfalsifiable — nested boxes make over-prediction monotone in ρ by arithmetic | Spearman +1.0000 with a zero-width CI, published as a finding |
| 4 | A reported a **100% acceptance rate measured at the wrong floor** (bare `SamplerConfig()` carries the v6 value 0.045, not the shipped 0.1083) | A wrong number in a commit message; corrected to 70%/80% |
| 5 | A's E2 scored **best true value among visited points** | Credits an arm for a recipe it cannot identify → space-filling arms win by construction |
| 6 | **B's T9:** the paired opening batch never existed, and the test that promised it asserted determinism instead | E2's fairness rule was false; the primary comparison was unpaired |
| 7 | **B's Q23:** `coord` was a **second** unpaired arm and undeclared — A's `coordinate_descent` starts from a random interior point and never calls `initial_design` | `identical_initial_design_per_seed: true` was false for **two** arms, one declared and one silent — the same defect as #6, one arm over |
| 8 | **A's lengthscale diagnostic anchored its decision rule on the prior MEDIAN (10.08) when the fit is MAP and its no-data attractor is the prior MODE (0.5016)** | The "prior is dominating" branch was unreachable and the "data is winning" branch was where an untrained model sits. Measured opening-design median: **0.502**. A conclusion was written, and committed, from a rule that could return only one answer |

| 11 | **A's "correction" to stage1_23 LN511 would have overwritten a CORRECT cell.** Reasoning from "the table is the design of record", A inferred the figure strip must be wrong. The paper prints `+ + + + + -` (`pdf_crosscheck.md:129`) — the strip was right and the third-party transcription was the outlier. Caught only by reading the cross-check B had already written, which says in terms: *"Recorded so nobody 'fixes' a correct cell"* | A dataset silently corrupted in a cell no structural check can see — a 22-run D-optimal design stays valid, rank 22, under a single flip. **The failure mode is new: not a check that could not fail, but a plausible authority rule applied without checking the authority** |
| 12 | **`results/e2-grid.json` was gitignored while five scripts and three fidelity gates anchored to it by path.** A's clone and B's clone therefore held two *different* E2 runs under one filename (qLogEI mean 0.1553 vs 0.1641), and **every gate passed in both** — `q29_symmetric.py` printed `max \|Δ\| 0.000e+00 over 50 rows` in B's clone, and the same gate passes in A's. B's −0.0708 entered the record as an independent recomputation of A's −0.0595, corroborated by two further artefacts that were also B's clone (`doe-scoring.log`, and `e2-run1-unfiltered.log`, which had been **committed with unresolved git conflict markers** holding both runs at once) | The project's most-quoted number contested against itself for a day, and Q29 filed a request that A "reconcile `report()` against the stored grid" — `report()` was correct throughout. **The failure mode is new again: a gate that verifies a regeneration against an untracked file can only report that a clone agrees with itself.** It is unfalsifiable by construction, and unlike defects 1/2/3 the check body is *right* — the defect is in what it is pointed at |

| 10 | **The digitization's design check counted row TYPES and was quoted as proof it "matches the published design structure exactly"** — it never checked corner distinctness or that a response existed. Stage 2 shipped with corner `(-1,+1,+1,-1)` duplicated, `(-1,+1,+1,+1)` missing, and row 2's quartiles `NaN`; the check returned 16/8/1 and passed | The claim in `oracle_defensibility.md` was false, and one of 48 published conditions had no response at all. **Sixth instance of the could-not-fail pattern** (with 1, 2, 3, 6, 8) |

| 9 | **A's ARD inference was pseudo-replicated** — Wilcoxon over 50 runs where `e2.yaml` registers `cluster: instance` (n=25) — and run on a difference of ratios, whose skew makes a signed-rank test anti-conservative (measured 8.9% at a nominal 5%) | Every Q25 p-value was overstated. Conclusions survive recomputation; the numbers did not. **This is the error the project criticises the source paper for, committed in the project's own diagnostic** |

Guards now in the suite for every one. Defect 3 is the worst of them — a pre-registration
is the one document a reader trusts not to contain a test that cannot fail.

**Defect 8 is the same failure as 3, committed by the same person who wrote the guard
against it**, and it is the most instructive one here. The rule was fixed in advance, in
the module docstring, before any number was read — which is the correct discipline and is
exactly what made it dangerous: registering an endpoint in advance guarantees only that you
cannot tune it afterwards, not that it can distinguish anything. The specific error was
using a *distributional* summary of the prior (its median) where the *optimisation* target
was needed (its mode, `exp(loc − scale²)`, which is also gpytorch's kernel initialisation
and is therefore literally the untrained value). It was caught by a four-lens adversarial
audit run deliberately **before** the numbers were interpreted; three of the four lenses
found it independently. What version 2 does about it:

- the anchor is no longer a formula at all but an **empirical no-signal null** — the same
  design and noise refit on permuted outcomes, so "has this learned anything" is measured
  rather than asserted;
- the deciding statistic is the **ARD separation ratio against that null**, which is immune
  to the whole class of error because the prior is identical on every dimension, so any
  uninformed fit gives 1.00 by symmetry (measured null: 1.11);
- a **counterfactual arm** was added — the same recovered designs refit under Gamma(3, 6) —
  because with no condition varying the prior, no lengthscale value could attribute
  anything *to* the prior. `build_gp` gained one defaulted argument to make that possible,
  built by hand rather than by swapping in `get_matern_kernel_with_gamma_prior`, which
  would have changed three things at once;
- `slice_rmse` was **deleted rather than normalised**: it is ~97% level error, and its
  active-versus-inert ordering is fixed by the oracle's `active_share = 0.90`, so it came
  out identically in the cell where BO wins and the cell where it loses. A shape-skill
  score with a principled zero replaced it.

Defect 7 is worth dwelling on because A introduced it *while fixing* #6. The random start
was deliberate and the reasoning was sound — "a centre start would be a hidden advantage on
an oracle whose optimum sits near the middle" — but a sound local decision made a global
fairness claim false, and A did not go back and check the claim. B declared the exemption
rather than repairing it, correctly: seeding coordinate descent from the best of the shared
opening would make it a stronger, different algorithm rather than the textbook baseline it
is there to represent, and changing an arm after its numbers exist is its own problem.

Two things A believed and had to withdraw, both recorded rather than quietly dropped:

- A predicted the effective peak could fall **inside** the training box (worst case
  m ≈ 0.37). **Measured floor is 0.849**; 0/200 cells breached; B's real E4 run agrees at
  0/40. The bound assumed every γ and every factor at its extreme simultaneously, which
  the fixed point never does.
- The spec predicted **minima** at low κ from 1-D convexity. Measured: **saddle in
  800/800**, plus 100/100 in E4 and 20/20 in the DoE arm. Four independent confirmations
  that the prediction was 1-D reasoning applied to a 6-D surface.

---
### Where this register goes in the paper (T3)

**Main text: one methods paragraph, describing the PRACTICE.** Register the claim and the
decision rule before the run; run the adversarial audit *before* interpreting the numbers,
not after; report every registered prediction including the ones that came out wrong.
Three sentences, in Methods, stated as how the work was done.

**Supplementary: this register in full.** Twelve defects, each with the pattern it
belongs to.

**Why split it.** The record is genuinely distinctive and reviewers will value it — it is
the strongest evidence the numbers can be trusted. But a list of twelve errors as a
reader's first impression invites *"why should I trust anything else here"*, which is
exactly the wrong inference to draw from a project that found its own mistakes. The
practice belongs where it is load-bearing; the inventory belongs where it is checkable.

**Do not soften the supplementary version.** Its value is that it names who made each
error and what the reasoning was, including the two that were made by the person who had
just written the guard against them (defects 8 and 11) and the one that survived a
passing fidelity gate in two clones at once (defect 12).

---

## 8. Source verification — the Collagen IV question, resolved

`docs/pdf_crosscheck.md`, raw reports in `docs/pdf_crosscheck_raw/`

Four independent readers over the full paper; two disagreed and the disagreement is
recorded, not averaged. The lead recomputed the decisive step independently.

**Results p.2 says the stage-1 Collagen IV high is 28 µg/mL; Methods p.12 says 56.** Every
other value matches. Figure 2b publishes the whole fitted surface, and its own first-order
condition in LN411 discriminates:

| stage-1 CIV high | TheO's CIV 67.2 sits at | model's optimal LN411 | paper states 0.9 |
|---|---|---|---|
| **28 (Results)** | **coded +1.4000 — outside** | **0.900** | **exact** |
| 56 (Methods) | coded +0.20 — inside | 1.169 | mismatch |

Three exact hits: +1.4000, 0.900, and 28 × 2.4 = 67.2. **So TheO was extrapolated, 20%
past the highest CIV ever tested.** This **reverses** `project_record.md` §E9, whose
constrained-optimiser argument is dead — *profiler*, *desirability*, *maximize*, *stationary
point* and *canonical analysis* appear **zero** times in the paper; the wording is
"prediction solution", JMP's unconstrained Solution report.

**It is a hybrid, and we had been treating the two as competitors:** fibronectin was
genuinely boundary-clamped (stated twice) while Collagen IV was extrapolated.

> **This is an INFERENCE, not an authors' statement.** Caveats: 3-dp rounding; C
> reconstructs to 35.70 against a printed 35.6; a suppressed CIV² term would weaken it.
> **A statistician must re-derive before it carries a headline.**

Also settled: **no CV, SD, SE or exact p-value is reported for CD31 anywhere** — the ± sign
appears exactly twice and both are CIV area, not CD31. σ_rel = 0.25 keeps its current basis,
now as a *verified* absence for the limitations section. The low-resolution caption note is
**real, verbatim**; the digitizer's claim that it was spurious is wrong. Figures 1a/2a are
box plots, not bar charts — three of our documents were wrong. The Matrigel comparison is
**transitive via ref 28**, not measured in this paper, though the Abstract reads as direct.

---

## 9. What A built

| module | purpose | tests |
|---|---|---|
| `oracles.py` | the biphasic Hill landscape, sampler, ensemble loader, `SHIPPED_CONFIG` | 38 |
| `torch_oracle.py` | `BiphasicOracle` + `TorchEvaluator` — the numpy/torch boundary | 20 |
| `doe.py` | the sequential-DoE arm, 20 + 27 + 1 | 16 |
| `diagnostics.py` | coverage, sharpness, PIT, closed-form CRPS, cluster bootstrap, E2 scoring | 17 |
| `baselines.py` | coordinate descent | 7 |
| `space.py`, `evaluators.py` | coded search space, Evaluator ABC | — |

Data: **65 committed landscapes** (40 at d=6, 25 at d=8), version-stamped, plus the source
figure PNGs and both independent digitizations.

Scripts: `generate_oracles`, `preflight_pf1`, `preflight_pf2`, `run_e1`, `run_e2`,
`run_e2_shard`, `run_e3`, `run_doe_arm`, `digitize_hall_ogle`.

---

## 10. Open

- **Q15** — `stage2_half_width` moves the DoE escape statistic from 0% to 100%. Registered
  at 0.25; **no other value has been run**, deliberately.
- **Q16** — replacement primary (PI coverage vs ρ). B reports no crossing: coverage is
  never nominal.
- **Q17/Q18** — both implemented and composed; E2 runs 1 and 2 are void and reported nowhere.
- **Q7 [Alan]** — author order, and whether the code and digitized data can be released.
- **Unresolved in the source:** the supplementary information was never obtained, and the
  high-resolution Figure 1 the caption promises is the most valuable of the four asks to Ogle.
