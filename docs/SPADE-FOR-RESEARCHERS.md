# SPADE for researchers — which method, and how to run it

**Audience.** A working experimental scientist with a plate reader, a fixed well budget,
and a decision to make: *which experimental design should I use, and what will it actually
give me back?*

**Provenance rule.** Every quantitative claim below carries a section reference into
`docs/FINDINGS-SPADE.md` (cited as §N) or `docs/K6-TECHNICAL-REPORT.md` (cited as
K6-TR §N), and, where one exists, the result file. Nothing here is general machine-learning
knowledge. Where the evidence is thin or the repository has retracted itself, it says so
in the text rather than in a footnote.

**Standing caveat.** This repository has retracted its own headline three times (§4.4,
§14 vs §29, §43). It scores methods on *synthetic* landscapes — a biphasic Hill oracle
built to resemble ECM-titration biology, plus hartmann6, ackley, levy and rosenbrock. No
result here has been reproduced on a real plate. Read it as a planning tool and a source
of hypotheses, not as a warranty.

---

## Table of contents

1. [The one-page decision tree](#1-the-one-page-decision-tree)
2. [What SPADE is](#2-what-spade-is)
3. [SPADE vs BO vs classical DoE](#3-spade-vs-bo-vs-classical-doe)
4. [The two confidence knobs: gamma and alpha](#4-the-two-confidence-knobs-gamma-and-alpha)
5. [Before you run: the feasibility calculation](#5-before-you-run-the-feasibility-calculation)
6. [How to actually run SPADE](#6-how-to-actually-run-spade)
7. [How to read the output](#7-how-to-read-the-output)
8. [Where SPADE is the wrong tool](#8-where-spade-is-the-wrong-tool)
9. [Known limitations and open questions](#9-known-limitations-and-open-questions)
10. [Glossary](#10-glossary)

---

## 1. The one-page decision tree

The single most important thing in this document:

> **Choosing a point is a different problem from certifying a region, and the methods rank
> differently — sometimes in exact opposition.**

That is not a slogan; it is the measured result. At `(d=6, σ_rel=0.10)` the SPADE arms are
**9th–11th of 12 on simple regret and 1st–3rd of 12 on map quality** — the two objects rank
SPADE almost exactly opposite (§13, `results/p3-k6-d6-s010.json`). At the same cell the
classical screened arm `doe` is 5th on regret and **last on the map at AUC 0.5665, barely
above a coin flip.**

So start by answering one question honestly.

### Start here: what do you have to hand back at the end?

| What you need | What the deliverable is | Use |
|---|---|---|
| **One recipe.** "Give me the best medium formulation you can find." | A single point `x̂` | **Batch BO (qLogNEI / qLogEI)** |
| **One recipe, cheaply, and you must also know which factors matter** | A point plus main effects | **Classical DoE with screening** — but read §1.1 below before you commit |
| **A range per ingredient.** "Collagen I 12–19 µg/mL, Laminin 511 0.3–0.5 …", with a stated confidence, for a batch record or a tech-transfer document | A *certified operating region* | **SPADE** — if the feasibility check in §5 passes |
| **A probability map.** "Show me `P(pass) ≥ 0.9` everywhere in the box" | A calibrated surface over the whole space | **Any spread design.** SPADE, plain LHS or **Sobol** — see §1.2 |
| **You don't know yet** | — | Run the feasibility calculation in §5 first. It is arithmetic, costs nothing, and can tell you the question is unanswerable before you plate anything |

### 1.1 If you were going to screen: stop and read this

Screening — cutting 6 factors to 4 and confining the response surface to a sub-box — is the
single most consequential decision on this list, and it runs in **exactly opposite
directions** for the two deliverables.

`lhs` and `doe` in this repository are both non-adaptive, both 48 wells, both one plate's
worth of measurements. The *only* structural difference is the 6→4 screen and the sub-box.

* On **map quality**, the unscreened arm wins by **+0.105 to +0.221 AUC, significant in 24
  of 24 `(γ, τ_frac)` cells** (§4.2a, `results/k6-designspace.json`).
* On **simple regret**, `doe` **beats** `lhs` by **+0.0312 [+0.0133, +0.0491], p = 0.0028**
  (§4.2a).

Two arms, one difference, a complete ranking reversal.

This reproduces off the Hill oracle. On the symmetric-difference error volume, arms beating
`doe`: **6 of 8 on hartmann6, 8 of 8 on levy, 8 of 8 on rosenbrock** (§19,
`results/p6-families.json`), and it gets *worse* at d=8, where **all eight arms beat `doe`**
(§30). `random`'s margin over `doe` at d=8 is **+0.0517, p_holm = 7.9e-113** — the largest
single effect in the study, and it is against the classical arm on the deliverable the
classical arm exists to produce.

**Screening buys you the better single recipe and costs you the ability to state a range
for the factors you screened out.** You cannot certify a factor you never varied — the
repository enforces this in code (`inscribed_box(..., active=)`, Amendment B3,
`src/boec/designspace.py:196`).

Three things this does **not** license:
1. *"Screening is always fatal."* Ackley reverses it, and ackley is the one family where
   `doe` ranks best (mean rank 4.32 of 9) — because the screen's centre point lands on
   ackley's exact optimum 7 times by construction (§19, §21). Every effect on ackley is
   below the smallest effect of interest (SESOI = 0.02) in any case.
2. *"Everything beats screening."* At d=6 on hartmann6, `doe` beats **both** BO arms on the
   map while losing to every spread arm. The failure is specific to spread designs (§19).
   That caveat does **not** survive d=8 (§30).
3. *"The screen is the whole mechanism."* Turning the screen off does **not** rescue the
   classical arm: `doe_unscreened` still loses to every spread arm by more than SESOI at
   `p_holm < 1e-10`. The screen accounts for **19.8–28.4%** of the deficit; the
   response-surface model costs the rest (§26, `results/q59-map-rescore.json`). *(A
   "consistent ~30%, three times" figure was published here and is withdrawn — it was an
   artefact of a `sigma_add` bug.)*

### 1.2 If you only need a map, you may not need SPADE

`sobol` — a plain scrambled Sobol sequence, one plate, no model, no adaptivity — is the
best arm on **four independent validated metrics**: best calibration (0.02893), best Brier
(0.1269), best empirical containment in the study (0.959 / 1.000 / 1.000), and best mean
symmetric-difference rank on three of four families (§23.3, §27.3).

If your deliverable is "a well-calibrated probability surface over the box," a 48-point
Sobol design is a serious, nearly free baseline, and you should have a reason for doing
anything more complicated.

What SPADE adds over it is **sharpness** — SPADE takes refinement ranks 1, 2 and 3 of 9 —
and a *joint* certificate. It does not add reliability: SPADE's calibration ranks 5, 6 and
7 of 9 (§27.1, `results/p7-murphy.json`).

---

## 2. What SPADE is

SPADE (Single-Plate Assured Design Envelope) as **actually run and measured** in this
repository is the arm called `versionb`. Its budget is **48 wells across two rounds.**

> **Read this before anything else.** `docs/SPADE-SPEC.md` describes a 49-point
> orthogonal-array LHS with triplicate anchors totalling **55 wells**, a day-0 covariate
> adjustment (Stage 0), and a frozen regime detector (Stage 3). **None of those three was
> built or measured.** The 55-well budget cannot be gated against any committed column and
> was explicitly dropped (§7). The day-0 covariate `R²` is not recoverable from existing
> lab data and needs a prospective measurement (§4.7). The regime detector was built,
> frozen, tested once, and **failed** (§37). What follows is the method that has numbers
> attached to it.

### Plate 1 — 40 wells, space-filling

A 40-point Latin hypercube over the coded unit box, `static_design(bounds, "lhs", 40, seed)`
(K6-TR §3.9). Every factor is varied; nothing is screened out. Measure all 40.

Fit a Matérn-5/2 ARD Gaussian process to the 40 readings. The observation variance is
**handed to the model as known, not fitted** — `train_Yvar` is the plug-in
`ŷ² σ_rel² + σ_add²` (`src/boec/torch_oracle.py:73`). This is the one part of SPADE-SPEC
Stage 2 that the code genuinely does; what it does *not* do is derive that σ̂ from
replicates, because the replicate study (K1) has never been run (§7).

### Plate 2 — 8 wells, on the boundary of the certified region

**The 8 wells come out of the 48, never on top of them** (`scripts/run_versionb.py`
module docstring). Anything that adds wells is not budget-matched.

Plate 2 does **not** confirm the peak. Q58 measured that confirming the peak *hurt* the
classical arm, 0.0958 → 0.1437, because its first reading at the peak was already the
trustworthy one (`src/boec/lse.py` docstring; SPADE-SPEC Stage 5). The certified region's
size is limited by the *worst* point on its boundary, so precision at the boundary is what
lets the region grow.

The criterion is Bryan's (2005) straddle over a 4,096-point Sobol candidate grid:

```
straddle_score(mean, sd, theta) = 1.96 * sd - |mean - theta|
```

evaluated at `theta = 0.75 * mu_max` (`DESIGN_TAU_FRAC = 0.75`). High where the model is
uncertain **and** near the threshold. Picked greedily, with each pick masking a Chebyshev
ball of radius `median_ARD_lengthscale / 4` so the batch cannot collapse onto one location
(`src/boec/lse.py`). At the live operating point that radius is 0.1416–0.1495 and **binds
in 22 of 50 campaigns**, relocating a mean of 0.56 of 8 wells — so `batch_lse` is genuinely
not "top-8 by score" (K6-TR §3.9, R1; the opposite claim was published and retracted).

The criterion is **not boundary-only**, deliberately: a far-from-threshold point with large
enough uncertainty can outscore a well-determined near-threshold one, which is what
Azzimonti et al.'s own SUR figures do.

Then refit **one** GP to all 48 observations. There is no averaging step, because plate 2
places wells at *new* locations and there is no first reading to average against (K6-TR
§3.9). *(SPADE-SPEC Stage 5's "decide by the mean of first and confirmation readings" is
therefore not what was run; the K3 confirm-and-average test is unrun, §7.)*

### The certificate

From the refitted GP, on a 20,000-point Sobol grid plus a 2,000-point subset for joint
draws:

1. **A probability map.** `P(Y ≥ τ | x)` at every grid point, under the posterior
   *predictive* — so it carries process noise `σ` as well as estimation error. This is
   Peterson's `D_gamma` object and it is the ICH Q8 deliverable
   (`src/boec/designspace.py` docstring).
2. **A conservative excursion set `CE_α`.** The largest Vorob'ev quantile whose *joint*
   containment probability reaches `α` (Azzimonti et al. 2016, 2021; Chevalier 2013;
   `src/boec/vorobev.py`). This is the certificate.
3. **An inscribed hyperrectangle.** The largest axis-aligned box lying entirely inside the
   certified set — a range per factor, which is what a batch record can hold
   (`inscribed_box_from_mask`).
4. **A setpoint.** The argmax of the posterior mean inside that box.

### Rounds, not just wells

| arm | wells | rounds |
|---|---|---|
| one-shot spread (`lhs`, `sobol`, `random`) | 48 | **1** |
| **SPADE (`versionb`)** | 48 | **2** |
| classical RSM (`doe`) | 20 + 27 + 1 = 48 | **3** |
| batch BO (`qlogei`, `qlognei`) | 14 + 8×4 + 2 = 48 | **10** |

(K6-TR §4.) A round is a plate turnaround — days of calendar time, a thaw, an operator
shift. **Every contrast in K6 and K6b is at equal *wells* only; rounds were under-reported
throughout** (§4.9, K6-TR §4). If a tie on the deliverable comes at 2 rounds against 10,
that is a 5× result on the axis your calendar actually feels — but note that the repository
also records this axis as under-analysed rather than as a proven claim.

---

## 3. SPADE vs BO vs classical DoE

### 3.1 The comparison table

| | **SPADE (`versionb`)** | **Batch BO (`qLogNEI`)** | **Classical RSM + screen (`doe`)** | **Plain Sobol / LHS** |
|---|---|---|---|---|
| Rounds | 2 | 10 | 3 | 1 |
| Wells | 48 | 48 | 48 | 48 |
| **Best single recipe (regret, rule A)** | middling — 9th–11th of 12 at (6, 0.10) (§13) | strong (§5.1) | **best, but at one cell of four** (§9.2) | weak |
| **Best single recipe (rule P, posterior-mean argmax)** | **1st of 9** at (6, 0.25) (§34.1); parity with BO at (6, 0.10), gap +0.0165 inside SESOI (§43.1) | strong | **worst of 9** — 0.0958 → 0.1993 (§9.1); 0.0892 → 0.2728 at σ=0.10 (§32) | improves |
| **Map quality (AUC)** | **1st–3rd of 12** at (6, 0.10) (§13); AUC 0.7583, 1st of 9 on P7 (§27) | 0.7392 | **last, 0.5665** (§13); 0.5960 (§27) | 0.7229–0.7270 |
| **Calibration (Murphy, lower better)** | 0.0353–0.0385, **ranks 5–7 of 9** (§27.1) | 0.04425 (rank 8) | **0.22959 — 5.2× worse than any other arm** (§27.2) | **sobol 0.02893, best** |
| **Refinement / sharpness (higher better)** | **ranks 1, 2, 3 of 9** (§27.1) | 0.01261 | **last** | 0.01142–0.01175 |
| **Joint certificate (empirical containment)** | meets nominal on hill in **18 of 18 scored cells**, worst 0.980 (§41.1) | 0.900 / 0.979 / 0.968 (K6-TR §1.4) | **0 / 50, 12 / 50, 25 / 50 against 0.50 / 0.80 / 0.95 — fails at every level** (§4.8) | sobol 0.959 / 1.000 / 1.000 |
| **Certifies at all, off hill** | rosenbrock 22/24, levy 22/24, hill 18/24, **hartmann6 2/24, ackley 0/24** (§41.1) | not measured off hill | — | not measured off hill |
| **Wins outright (performance profile, τ=1.0)** | **2%** (§42.2) | 22% | 2% | — |
| **Within 3× of the best arm** | **70%** (§42.2) | 80% | **22%** | — |
| **Design quality by RSM's own criteria** | **not measured** — `versionb` is absent from the §33.2 table | D-eff 3.4–7.5%, max SPV 5,198–34,416 | **rank-deficient in 50 of 50 — D- and G-efficiency undefined** (§33.2) | sobol 10.4–10.6%, lhs 9.1–9.2%, random 8.1–9.8% |

### 3.2 What each method wins under, in one line each

**Batch BO wins when the deliverable is one point and you can afford ten rounds.** It is
also the strongest arm on the *map* at the primary cell: a one-shot spread design beats
qLogEI in 9 of 24 cells and never loses to it, but loses to **qLogNEI in 15 of 24** (§4.2b).
That distinction is load-bearing — Q57 retracted an earlier claim for exactly this reason.
**Never quote a spread-vs-adaptive result without naming the acquisition function** (K6-TR
§6.2, §10).

**Classical DoE with screening wins on regret at exactly one cell of four**: `doe − qlognei`
is −0.0574, Holm p = 3.27e-05 at (d=6, σ=0.25), and is non-significant with the **sign
flipped** at (6, 0.10) and (8, 0.10) (§9.2). And **59% of even that advantage is
identification, not search** (§9.3): `doe` nominates a single confirmation well at a
CCD-fitted optimum, so it does not take an argmax over 48 noisy readings and does not pay
the winner's curse that scales with σ. Its identification gap is noise-invariant
(0.0361 → 0.0348, Δ = −0.0013) while every BO arm's roughly halves.

That is a statement about **terminal rules**, not about DoE versus BO — and it is the honest
form of the claim (§11.2).

**SPADE wins when the deliverable is a certified region and the landscape is smooth and
coordinate-wise unimodal.** On hill it is willing (18 of 24 cells certify) and calibrated
(0 cells below nominal) — the only family in the study that is both (§41.3).

**Sobol wins if you want a calibrated map and nothing else** (§1.2).

### 3.3 The honest characterisation of SPADE, on the BO community's own metrics

Run against mean rank and a performance profile — the conventions the BO literature reports
— SPADE is:

> **A low-variance middling arm.** It wins outright on **2%** of problems and is within 3× of
> the best arm on **70%**. `doe` shares its 2% win rate but is within 3× on only **22%** and
> fails to reach even 10× on **42%** (§42.2, `results/versionc-conventions.json`).

SPADE is almost never the best arm and almost never catastrophic. For a lab choosing one
method for one plate, the tail is what matters, and the performance profile is the only
metric in the study that shows it. Mean regret and mean rank both compress this to
"middling" and hide *what kind*.

There is one place SPADE leads a profile outright: at σ=0.25, `versionb_predictive` is
first at τ = 1.0 with **0.16**, above every BO arm — which no mean-based metric in this
project reports (§42.2).

### 3.4 The classical arm fails its own acceptance test

Worth knowing if RSM is your incumbent. Run against the diagnostics the response-surface
community would itself demand (§33, n=25 per σ):

| | σ=0.25 | σ=0.10 |
|---|---|---|
| predicted response at the chosen point | 0.9805 | 0.9625 |
| **true** response there | **0.0992** | **0.1015** |
| over-promised (gap > 0) | **25/25** | **25/25** |
| predicted **above the true global optimum** | **12/25** | **12/25** |
| stationary point classified a **saddle** | **25/25** | **25/25** |
| confirmation run beat the best of the 48 wells already visited | **0/25** | **0/25** |

Two structural findings sit behind it. The pooled 48 wells are **rank-deficient in 50 of 50
campaigns** — two dropped factors give identical pure-quadratic columns, and the resolution-IV
screen's aliasing becomes an exact rank deficiency of the pooled design — so D- and
G-efficiency are **undefined** (§33.2). And the lack-of-fit F-test has only 2 pure-error
degrees of freedom, so real misfit (`MS_LOF` exceeds `MS_PE` in 48 of 50 campaigns) is
declared in only 8 of 25 at σ=0.10. Pooling replicates the arm has **already paid for**
takes that to **24 of 25 at zero extra cost** (§33.1).

*Stated caveat, not hidden:* the lack-of-fit test assumes constant variance, and this
project's noise is multiplicative. The test is run as the literature specifies; the
assumption it rests on is violated by the noise model.

**The same toolkit also explains why spread wins the map and BO wins the search.** A
fraction-of-design-space curve is, up to a constant, the distribution of prediction-interval
width over the box — `SecondOrderModel.prediction_interval` has half-width
`t·σ·√(1 + SPV/n)` — and a certified region is exactly `{x : lower bound ≥ τ}`. The median
interval-width multiplier runs **1.17 for an unscreened CCD, 1.40–1.52 for Sobol and LHS,
and 2.89–2.95 for the BO arms**, reaching 8.8–9.1 at the 99th percentile (§33.3).

> **The adaptive arms buy their regret by leaving the space 3–9× less precisely mapped than
> a CCD does.** That is the map/search trade in the RSM literature's own units.

*(This is the classical, design-based FDS on scaled prediction variance. The project's
certified regions use GP posterior SD, and no committed file stores per-grid-point posterior
SD, so a GP-based FDS would need a fresh 20,000-point posterior per arm per seed.)*

---

## 4. The two confidence knobs: gamma and alpha

Practitioners confuse these constantly. They are different objects and they buy different
things.

### 4.1 Gamma — a point-level margin

`gamma` (γ) lives inside Peterson's design space:

```
D_gamma = { x : P(Y >= tau | x, data) >= gamma }
```

with `Y` a **future observation**, not the mean response (Peterson 2008; Peterson & Lief
2010; `src/boec/designspace.py`).

Read it as: **"if I run this recipe tomorrow, the probability that the batch clears spec τ
is at least γ."** It is a statement about *one point at a time*, and it carries process
noise — the assay CV, the plate-to-plate variation, everything that will still be there
after infinite data.

Raising γ raises the per-point bar and **shrinks the region**.

### 4.2 Alpha — a whole-region assurance

`{x : LCB(x) >= tau}` is twenty thousand **marginal** statements presented as one
**regional** statement. Under independence, twenty thousand pointwise 95% claims contain a
thousand expected false certifications; spatial correlation softens that but does not repair
the category error (`src/boec/vorobev.py`).

What a batch record asserts is joint:

```
P( CE_alpha  is a subset of  Gamma )  >=  alpha
```

— the probability that **no** certified point is false.

Read it as: **"with confidence α, *every* recipe in this region has batch-pass probability
at least γ."** That is the structure of a classical tolerance region: γ is the *content*,
α is the *confidence*.

Raising α makes the estimator more cautious and **shrinks the region — often to empty.**

### 4.3 A worked example, with real numbers

Take the primary operating point of this study: relative assay noise `σ_rel = 0.25` (a 25%
CV — high, but this is what the repo calls primary), an additive floor `σ_add = 0.01`, and
a response normalised so the best achievable value is `mu_max = 1.0`
(`src/boec/torch_oracle.py:145`).

**Step 1. Choose your content level γ.** Say you need 95% of future batches to pass. `γ = 0.95`,
so `z_γ = 1.645`.

**Step 2. Find the ceiling.** With *perfect knowledge* — infinite data, zero estimation
error — certifying still requires `mu − tau ≥ z·σ`. Because this noise is relative, that
closes in form:

```
tau_max = mu_max * (1 - z_gamma * sigma_rel) = 1.0 * (1 - 1.645 * 0.25) = 0.589
```

(`designspace.tau_max`, §4.5.) **No method, no design and no number of wells can certify a
spec above 0.589 at this noise level, ever.**

**Step 3. Choose your spec τ.** Say you want τ = 0.353 — 60% of the ceiling (`τ_frac = 0.60`,
the threshold this study is best powered at). That is below the ceiling, so the question is
answerable.

**Step 4. Note what the model actually has to establish.** The latent requirement is

```
theta = tau + z_gamma * sigma = tau_frac * mu_max = 0.60
```

The `(1 − z·σ_rel)` factors cancel exactly, verified to machine precision at 12
combinations (§4.5, Amendment C2). So `τ_frac` **is** the latent threshold as a fraction of
the achievable maximum, for every γ. This has a consequence that trips people up: in this
parameterisation, **raising γ *lowers* the absolute τ**, so the "high-γ" cells have *larger*
true target sets, not smaller. At γ=0.99, τ_frac=0.60 the true set covers **0.99916 of the
box** (§14). If you fix τ in physical units instead — which is what a real spec does — the
usual intuition returns: higher γ means a smaller region.

**Step 5. Choose your regional confidence α.** Say α = 0.95.

**Step 6. Read the certificate.** SPADE returns `CE_0.95` — a set of grid points, and a box
inscribed in it. The claim is:

> *With 95% confidence, every recipe inside this box has at least a 95% probability of
> producing a batch at or above 0.353.*

**Step 7. Check it was earned.** Across 50 independent campaigns at this cell, SPADE's
certified set was wholly inside the true region:

| α | measured | nominal | verdict |
|---|---|---|---|
| 0.50 | **0.940** (47/50) | 0.50 | clears |
| 0.80 | **1.000** (50/50) | 0.80 | clears |
| 0.95 | **1.000** (22/22) | 0.95 | clears, but on 22 non-empty campaigns of 50 |

against the classical screened arm in the identical cell:

| α | `doe` measured | nominal | verdict |
|---|---|---|---|
| 0.50 | **0.000** (0/50) | 0.50 | **fails** |
| 0.80 | **0.240** (12/50) | 0.80 | **fails** |
| 0.95 | **0.500** (25/50) | 0.95 | **fails** |

(§4.8, K6-TR §1.4, `results/versionb.json`, `results/k6b-conservative.json`.) At α=0.50 the
classical arm's certified region is contained in **zero of fifty** campaigns.

### 4.4 The trap: never grade a certificate on the model's own opinion

Two numbers look like they measure the same thing and do not.

* **`ce_contain` (circular).** `conservative_estimate` *selects* the set by maximising
  containment measured on the posterior draws, and then the containment is re-measured on
  **the same draws**. It cannot fall below α by construction. Measured: 0 of 1,390 non-empty
  cases fell below nominal, with minima of exactly 0.5000 / 0.8008 / 0.9512
  (`src/boec/vorobev.py`). The repository published this as evidence the guarantee held, and
  **retracted it** (§4.8).
* **`ce_empirical` (validated).** Against one realisation of the truth, a set is wholly
  contained or it is not. The guarantee is the **fraction of campaigns contained**, which
  must be at least α. This is the only non-circular test.

The gap is not subtle. In the same cell, at nominal 0.95, `doe`'s circular figure reads a
**perfect 1.0000 over 50 campaigns** while its empirical containment is **0.500 (25/50)**.
**The in-sample statistic ranks the failing arm first** (§4.8).

### 4.5 A third number you will be offered, and must not use: alpha-star

`alpha*` is "the largest confidence at which a non-empty conservative estimate exists." It is
attractive because it is **always defined**, even when every 95% region is empty
(`src/boec/vorobev.py`). It is also **not a metric of certificate quality**, and the
repository has formally declared it so (§28).

The evidence: `alpha*` ranks `doe` **first** (0.7875) — the arm whose calibration is 5.2×
worse than any other arm and whose empirical containment is 0/50 — and ranks `sobol`
**last** (0.5275), the arm that is first on calibration, first on Brier, first on empirical
containment, and best on three of four families. The two extremes are exactly inverted
(§28).

What it actually measures is **willingness to certify**. Its correlation with an arm's
non-vacuity rate — how often it returns a non-empty region at all — is **ρ = +0.7333,
p = 0.0246**, the only relationship in the entire α* investigation that reaches p < 0.05
(§31). An off-hill test confirmed it on data §31 never saw: α* tracks the emptiness rate
almost exactly, while `rosenbrock` has the *highest* α* (0.9351) and two Holm-surviving
coverage failures, and `hill` has a lower α* (0.8591) and none (§41.4).

> **α* rewards claiming more, and claiming more is associated with claiming worse.** Use it
> as a diagnostic — *"this plate supports 60%-confidence certification here; 95% needs
> another plate or a better assay"* — never as a ranking.

---

## 5. Before you run: the feasibility calculation

This is the most directly usable thing in the repository, and it costs nothing. Do it
**before** you plate.

### 5.1 Step 1 — the certifiability ceiling

```python
from boec.designspace import tau_max
tau_max(gamma=0.95, sigma_rel=0.25, mu_max=1.0)   # -> 0.5888
```

`tau_max = mu_max * (1 - z_gamma * sigma_rel)`, derived with estimation error set to zero
(`src/boec/designspace.py:71`). Computed from the repository's own function:

| γ | `tau_max` at σ_rel = 0.10 | `tau_max` at σ_rel = 0.25 |
|---|---|---|
| 0.50 | 1.0000 | 1.0000 |
| 0.70 | 0.9476 | 0.8689 |
| 0.80 | 0.9158 | 0.7896 |
| 0.90 | 0.8718 | 0.6796 |
| **0.95** | 0.8355 | **0.5888** |
| 0.99 | 0.7674 | 0.4184 |

**If your spec τ sits above this line, no method can certify it at that assurance, at any
budget, forever.** That is a planning calculation, not a method failure. Your options are to
lower γ, lower τ, or reduce σ — improve the assay, add replicates, adjust for a covariate.
Nothing else moves it.

This is not hypothetical. An earlier draft of the K6 registration used absolute thresholds
{0.70, 0.80, 0.85, 0.90} — **all four above the ceiling.** Every arm would have certified
nothing and the entire results table would have been zeros (§4.5).

Two caveats on the formula:
* `designspace.tau_max` **omits `σ_add`**. It is optimistic by 3.288e-04 at (σ_rel=0.25,
  γ=0.95) and 8.204e-04 at σ_rel=0.10 — a ratio of 2.49, **not** the "10×" that
  `COVERAGE-MATRIX.md` reports (K6-TR §10, R4c). `designspace.tau_max_exact` carries the
  quadrature-sum version, `mu_max − z·√((σ_rel·mu_max)² + σ_add²)`; it exists so the
  omission can be measured and is **deliberately not** used by the registered grid, because
  correcting one σ cell while the committed ones keep the old definition would confound the
  σ axis with a definition change (`src/boec/designspace.py:489`).
* It assumes *relative* noise, `y = f(1+ε) + η`. If your assay noise is absolute rather than
  proportional to signal, the algebra changes and you should redo it.

### 5.2 Step 2 — how much of your response surface is even certifiable

Across four synthetic families at 24 `(γ, τ_frac)` cells each, **111 of 384 cells (28.9%)
sit above the ceiling** (§9.8, `results/p6-ceiling-census.json`; independently reproduced at
d=6 from a different code path in §20):

| family | cells above ceiling |
|---|---|
| ackley | **0%** |
| hartmann6 | 2.1% |
| levy | 50% |
| rosenbrock | **63.5%** |

The ordering variable is **not** the family's response range — hartmann6 has a *larger*
range than rosenbrock and 1/30th the exceedance. It is where the prevalence quantile sits
relative to `tau_max` (§20, correcting a claim the document had repeated without checking).

The practical consequence is severe: of 48 cells per family, only **27** (hartmann6), **19**
(ackley), **10** (levy) and **9** (rosenbrock) are rankable at all. **79% and 81% of levy
and rosenbrock cells are excluded** as degenerate or above-ceiling (§20).

> *"How much of a response surface is certifiable at a given assurance"* has not been asked
> quantitatively in the QbD literature. On two of four families the answer at d=6 is **under
> a quarter of it** (§23.4).

### 5.3 Step 3 — will my region come back empty?

Emptiness is the dominant failure mode, and it is driven almost entirely by `τ_frac` — how
demanding your spec is relative to the ceiling. Fraction of campaigns with an **empty
predictive region**, 400 rows per cell, d=6, σ_rel=0.25 (K6-TR §5.7):

| γ \ τ_frac | 0.60 | 0.75 | 0.85 | 0.95 |
|---|---|---|---|---|
| 0.50 | 0% | 20% | 86% | **100%** |
| 0.70 | 0% | 28% | 90% | **100%** |
| 0.80 | 0% | 36% | 93% | **100%** |
| 0.90 | 0% | 45% | 97% | **100%** |
| 0.95 | 0% | 54% | 99% | **100%** |
| 0.99 | 4% | 80% | 100% | **100%** |

**At τ_frac = 0.95 the predictive region is empty in 400 of 400 rows at every γ.** Six of the
24 cells carry no region-based information at all.

Two more things this table tells you:

* **The predictive/latent gap is Peterson's process-noise floor biting.** Predictive regions
  are empty 54–69% of the time; latent (mean-response) regions only 16–25%. Same thresholds,
  same data. The difference is entirely that the predictive region must additionally absorb
  σ (K6-TR §5.7). If someone shows you a design space built on a mean-response confidence
  bound, it is larger than the honest one by roughly this much.
* **Emptiness varies by family, not just by threshold.** Empty predictive regions per arm:
  hartmann6 18.0–45.7%, ackley 1.2–57.8%, levy 64.8–74.2%, **rosenbrock 69.5–77.8%** (§20).

### 5.4 Step 4 — the planning summary

Before you plate, you should be able to fill in this table:

| quantity | where it comes from | your value |
|---|---|---|
| `mu_max` — best achievable response | prior data, or a positive control | |
| `σ_rel` — assay CV | replicate wells on a past plate | |
| γ — required per-batch pass probability | your spec / QA | |
| **`tau_max`** | `designspace.tau_max(γ, σ_rel, mu_max)` | |
| τ — your actual spec | your spec / QA | |
| **`τ_frac = τ / tau_max`** | arithmetic | |
| expected emptiness | the table in §5.3 | |

If `τ > tau_max`: **stop.** No design will help. Fix the assay or renegotiate the spec.

If `τ_frac > 0.85`: expect an empty region most of the time. This study can say nothing at
all about τ_frac = 0.95 — the certified set is empty in 50 of 50 campaigns for every arm at
every α, and *"SPADE's certificate is sound at τ_frac = 0.95"* is explicitly on the list of
sentences that may not be written (K6-TR §10).

If `τ_frac ≤ 0.75` and your landscape is smooth: this is where SPADE's evidence lives.

---

## 6. How to actually run SPADE

Named against the repository's own functions. The reference implementations are
`scripts/run_versionb.py` (the original two-plate arm) and `scripts/run_p2_versionb_gamma.py`
(the γ ladder). `scripts/run_p8_certificate_families.py` is the cross-family certificate run
and is the one configured with the draw count you should actually use.

### Step 0 — before the plate

* **Randomise which recipe goes in which well.** Otherwise plate position is confounded
  with factor level (SPADE-SPEC Stage 0). Place any replicates in different plate regions so
  plate variation lands in σ̂ rather than hiding.
* **Record day-0 confluence, row, column, batch and passage** if you can. The covariate
  adjustment `y_adj = y − θ(x_cov − mean(x_cov))` would lower effective noise by
  `σ_eff = σ√(1−R²)`, and σ sits inside the certifiability ceiling — it is the only lever on
  the floor in §5.1. **But be clear that this is untested here.** The day-0 → day-6 paired
  series does not exist in this repository's lab data and the R² is not recoverable from it;
  it needs a *prospective* measurement (§4.7).

### Step 1 — plate 1

```python
from boec.runner import static_design
X1 = static_design(bounds, "lhs", 40, seed)      # 40 wells, all d factors varied
Y1, Yvar1 = evaluate(X1)                         # your assay
```

### Step 2 — fit the GP with noise plugged in, not fitted

```python
from boec.surrogate import build_gp
model = build_gp(X1, Y1, Yvar1, bounds)          # Matern-5/2 ARD, sigma HELD FIXED
# train_Y and train_Yvar are (n, 1) -- always 2-D. A 1-D array is a different bug
# that produces plausible nonsense (src/boec/surrogate.py:326).
```

The variance is handed in as known (`_plug_in_yvar`, `src/boec/torch_oracle.py:73`). This is
deliberate: fitting lengthscale and noise jointly at n≈40 in 6D leaves them barely separable
and the optimiser trades one against the other (SPADE-SPEC Stage 2). Whether replicate-derived
σ̂ measurably improves calibration is **K1, and K1 has never been run** (§7).

### Step 3 — choose plate 2's 8 wells on the boundary

```python
from boec.designspace import gp_adapter
from boec.lse import batch_lse, exclusion_radius, predictive_sigma, min_pairwise_chebyshev
from boec.norms import sobol_grid

adapted = gp_adapter(model)                       # chunked at 2048 -- see below
X_cand  = sobol_grid(d, 4096, seed=seed)
theta   = 0.75 * mu_max                           # DESIGN_TAU_FRAC

mean, sd = adapted.posterior_mean_and_sd(X_cand)
sigma    = predictive_sigma(mean, sigma_rel, sigma_add)   # array, never a scalar

X2 = batch_lse(model=adapted, X_cand=X_cand, theta=theta, q=8,
               exclude=exclusion_radius(model),
               sigma=sigma)                       # sigma=None gives Bryan's LATENT straddle
print(min_pairwise_chebyshev(X2))                 # log it -- Amendment E2
```

Two decisions worth understanding:

* **`sigma=None` targets the latent contour** — Bryan's published straddle, and what the
  committed `versionb` column was run with. **Passing `sigma` targets the *predictive*
  contour, which is the deliverable's own boundary** (Amendment E6). The repository added
  the predictive variant as a separate arm rather than substituting it, so the difference is
  a measurement. Non-vacuity favours the predictive straddle at σ=0.25 (0.4267 vs 0.4225)
  and the ordering **does not hold at σ=0.10** — so the advantage is real but not general
  and must carry its cell (§38.7).
* **`gp_adapter` chunking is a correctness-of-runtime issue, not an optimisation.**
  `model.posterior(X)` builds the *joint* covariance: 0.06 s at N=2,000 and **100.60 s at
  N=20,000**, with a 3.2 GB dense matrix. Chunking at 2,048 turns the 20,000-point grid into
  ~0.6 s (`src/boec/designspace.py:85`).

Also log the acquisition's coefficient of variation on the candidate grid. Below
`ACQ_CV_FLAT = 0.04` no candidate is even one lengthscale better determined than the typical
one, and the eight wells are being chosen by numerical noise — a space-filling draw wearing a
criterion's name. Report *"acquisition uninformative at this density"* rather than
contributing a silent null (`scripts/run_versionb.py`, Amendment E1).

### Step 4 — measure plate 2, refit once on all 48

```python
Y2, Yvar2 = evaluate(X2)
model = build_gp(cat(X1, X2), cat(Y1, Y2), cat(Yvar1, Yvar2), bounds)
```

One refit on all 48. No averaging step — plate 2 sampled new locations, so there is no first
reading to average against (K6-TR §3.9).

### Step 5 — build the deliverables

```python
from boec.designspace import (tau_max, predictive_probability_map, inscribed_box_from_mask,
                              certified_volume_curve, connected_components, component_report)
from boec.vorobev import (conservative_estimate, conservative_estimate_split,
                          alpha_star, empirical_containment)

X_grid = sobol_grid(d, 20_000, seed=0)
adapted = gp_adapter(model)
mu, sd  = adapted.posterior_mean_and_sd(X_grid)

# 1. the probability map -- Peterson's D_gamma, the ICH Q8 object
p = predictive_probability_map(adapted, X_grid, tau,
                               sigma=predictive_sigma(mu, sigma_rel, sigma_add))

# 2. the certificate, on a 2000-point subset with JOINT draws.
#    This is the one place a joint covariance is wanted and small enough to want it
#    (scripts/run_p2_versionb_gamma.py:523).
post = model.posterior(X_sub)                          # X_sub: 2,000 points
cov  = post.mvn.covariance_matrix.double() + 1e-8 * eye(2000)
L    = cholesky(cov)
z    = randn(2000, n_draws, generator=Generator().manual_seed(seed))
draws = (post.mean.reshape(-1, 1).double() + L @ z).T  # n_draws >= 1024; see below

mask = conservative_estimate(draws, theta, alpha=0.95, n_rho=64)

# 2b. the cross-fit version, which removes the selection bias exactly
mask_cf, contain_heldout = conservative_estimate_split(draws, theta, alpha=0.95)

# 3. the box a batch record can hold, inscribed into D_gamma on the FULL grid
d_gamma  = p >= gamma
box, vol = inscribed_box_from_mask(X_grid, d_gamma, active=active_axes, seed_score=p)

# 4. multiple windows, if the certified set is disconnected
labels = connected_components(d_gamma, X_grid)          # (mask, X_grid) -- that order
```

Note the two grids do different jobs. The **map and the box** are computed on the full
20,000-point grid; the **certificate** is computed on a 2,000-point subset, because the
joint covariance at 20,000 points is a 3.2 GB dense matrix. Do not confuse the `CE_α` mask
(subset) with the `D_gamma` mask (full grid).

**Set the draw count to at least 1,024, and prefer 4,096.** This is not a tuning
preference — it is a corrected result. At the repository's original `N_DRAWS = 512` the
conservative estimate is measurably anti-conservative, and containment at γ=0.99 read 0.860
against nominal 0.95. At 1,024 it reaches 0.980 and stays there; at 4,096, with n=200 pairs,
**no cell is significantly below nominal, not even before multiplicity correction** (§29,
`results/f3-draw-sweep.json`). The project reported the 512-draw artefact as a property of
SPADE's certificate for a week before catching it.

A residual selection bias survives at 4,096 — 1.5 to 3.5 percentage points, only at the two
highest-γ cells (§29.3). `conservative_estimate_split` removes it exactly by never scoring
on the draws that selected, at a cost of 2× draws and seconds of wall clock. Use it when
you are quoting a containment number.

### Step 6 — the things you must record with the result

* `n_active` — how many axes the fitted model actually saw vary. If you screened, this is
  **not** `d`, and the certified volume is over the active subspace only (Amendment B3).
* The achieved minimum pairwise Chebyshev separation of plate 2, and the radius that
  produced it (Amendment E2).
* Whether each cell's certified set was empty. Empty is not zero, and every function in
  `designspace.py` returns `nan` rather than a number that would average into a mean and
  read as "safe" (`false_inclusion_rate`, `iou`).
* The draw count and whether the cross-fit was used.

---

## 7. How to read the output

### 7.1 What the certificate promises

> **With confidence α, every recipe inside this region has probability at least γ of
> producing a batch at or above spec τ.**

`α` is the *joint* confidence — the probability that **no** certified point is false, not
the average of pointwise probabilities. `γ` is the content — the per-recipe pass rate for a
*future observation*, so it already carries assay noise.

The box is the practically usable form: a low and a high for every factor you varied. The
setpoint is the argmax of the posterior mean inside the box.

### 7.2 What it does not promise

**It is conservative *given the model*.** Hyperparameters are plug-in, so their uncertainty
sits **outside** the guarantee. Azzimonti et al. flag this themselves; this repository
inherits it (`src/boec/vorobev.py`; K6-TR §6.3). The relevant cost measurement is E3's:
this repo's *latent* 95% interval achieved **0.7644** coverage while the *predictive*
interval recovers to ~0.90–0.92 (`src/boec/designspace.py`). Under a point-optimum
deliverable that is a footnote; under a certificate it inverts, because the broken interval
is precisely the one you would certify with. **Use the predictive map, not the latent one.**

**It says nothing about the space it did not certify.** An empty certificate is not a
statement that the space is bad; it is a statement that these wells did not settle it.
That distinction is enforced in code — `empirical_containment` returns `None` for an empty
set, because counting a vacuous containment as a success would have reported **ackley at
containment 1.000 for certifying nothing in 1,200 campaigns** (§41).

**It is not a claim that your recipe is optimal.** SPADE's regret under the arm's own
reported-best rule is middling (§13, §42). If you need the best point, see §8.

**A single number is not the deliverable.** Report the certified-volume-versus-confidence
curve (`certified_volume_curve`), not a fixed-95% volume. At the measured spread-design
neighbour density — **0.49 points within one fitted lengthscale at n=48, d=6** — the
fixed-95% volume is plausibly zero for every arm, and a table of zeros is degenerate rather
than informative (`src/boec/designspace.py`; SPADE-SPEC "Correction applied in the plan").

### 7.3 Reading the numbers you will be shown

| number | status | how to read it |
|---|---|---|
| **empirical containment** | **validated** | the real test. Fraction of campaigns whose set was wholly inside the truth. Must be ≥ α |
| **Brier, AUC, calibration, refinement** | **validated** | scored against known truth |
| **type I / type II / symmetric-difference error volume** | **validated** | the excursion-set community's own metric; use the **symmetric difference** as the single scalar |
| `ce_contain` | **circular** | cannot fall below α by construction. **Never report as "the guarantee holds"** |
| `alpha*` | **model-internal** | measures *willingness to certify*, not quality (§28, §31) |
| `vorobev_deviation` | **model-internal** | how uncertain the model is about its own set |
| `auc` alone | **superseded** | invariant to monotone transformation, so it scores *ranking* and never calibration (§9.4). Superseded by error volumes — but on grounds narrower than first claimed (§24) |
| **type I volume alone** | **do not use** | it ranks *silence* first: an arm certifying the empty set scores exactly 0 (§9.4) |
| `auprc` without its baseline | **do not use** | plain AUPRC's baseline **is** the positive rate, so it tracks prevalence, not the classifier. Reading it without `ap_baseline` licenses a confident and entirely false statement (§40.2) |
| `component_box_vol_sum` for a screened arm | **undefined** | with inactive axes pinned, the box expands vacuously to fill the subspace and summing over components multiplies 1.0 by N (§38.6) |

**Rule the project applies throughout: where a validated metric and a model-internal metric
disagree, the validated one wins and the disagreement is reported** (K6-TR §1.4).

### 7.4 A calibration sanity check you can run

`Brier = calibration − refinement + uncertainty` (Murphy). Verified on all 12,000 rows of
`results/p7-murphy.json`: 0 violations, worst residual 2.220e-16.

Reporting Brier alone hides which half of it you are winning. The two components rank arms
differently at **23 of 24 predictive-map cells**, with 371 of 864 pair inversions (§27.4).
SPADE is the worked example: **it buys sharpness and does not buy reliability** — refinement
ranks 1, 2, 3; calibration ranks 5, 6, 7 of 9. AUC, which cannot see calibration, puts SPADE
**first**. The first thing the Murphy split did with SPADE in scope was catch that (§27.1).

---

## 8. Where SPADE is the wrong tool

Blunt, because a method that will not name its failure modes is not usable.

### 8.1 If your deliverable is one recipe

Use BO. SPADE **wins outright on 2% of problems** (§42.2). Under the campaign's own
reported-best rule it sits 9th–11th of 12 on regret at (6, 0.10) (§13). It ties BO only
under a *posterior-mean* terminal rule, and even that parity is a parity: like-for-like
against the best rule-P arm the gap is **+0.0165 — inside SESOI, so parity holds and the bar
is not beaten** (§43.1; the "beaten" claim was withdrawn by the project's own loophole
audit).

### 8.2 Multimodal landscapes — hartmann6

SPADE's certificate on hartmann6, α=0.95, 24 cells, 50 seeds each: **it certifies in 2 of 24
cells.** Mean empty rate 0.990. Mean α* 0.056 (§41.1, `results/p8-certificate-families.json`).

It does not answer. That is not a calibration failure — there is nothing to be right or
wrong about — but it is not a deliverable either.

### 8.3 Ackley

**SPADE certified nothing in 1,200 campaigns.** 0 of 24 cells, mean empty rate **1.0000**,
mean α* **0.0000** (§41.1).

Ackley is also the family where the classical screened arm looks best (§19) — for the
uninteresting reason that the screen's centre point lands on ackley's exact optimum 7 times
by construction. Neither result should be read as a method comparison.

*(Caveat carried: every ackley row in the τ source carries `sensitivity: true`, so its
provenance is not comparable to the other families' even though the arithmetic is
unaffected, §20, §41.1.)*

### 8.4 High assurance off the smooth families

This is the sharpest negative result about SPADE in the study, and it comes from the run
built specifically to test the certificate off hill.

At 4,096 draws — the draw count §29 established as sufficient — **three of 64 scored cells
fall below nominal and survive Holm correction across all 64** (§41.2):

| family | γ | τ_frac | contained | rate | Holm p |
|---|---|---|---|---|---|
| levy | **0.99** | 0.60 | 34 / 49 | **0.694** | 6.05e-07 |
| rosenbrock | **0.99** | 0.60 | 37 / 50 | **0.740** | 4.74e-05 |
| levy | **0.99** | 0.75 | 37 / 48 | **0.771** | 1.22e-03 |

All three are at γ = 0.99. **Hill has zero cells below nominal**; its worst is 0.980 and 18
of 18 scored cells clear 0.95.

> **The families that certify most readily are the ones whose certificate is least
> trustworthy at high assurance** (§41.3). Hill is the only family in the study that is both
> willing (18/24) and calibrated (0 failures).

The history matters here because it is instructive: §14 fired a registered kill —
*"SPADE's certificate fails below nominal at high assurance"* — and §29 **withdrew** it as a
512-draw estimator artefact. **Both stand.** The withdrawal was correct as a statement about
hill at 512 draws and would have been wrong as a statement about SPADE. The original kill
fired on the right phenomenon, on the wrong family, for the wrong reason (§41.2).

**Practical rule: do not claim a SPADE certificate at γ ≥ 0.99 on a landscape you have not
verified is smooth and unimodal.**

### 8.5 Very demanding specs

At τ_frac = 0.95 the certified region is empty in 50 of 50 campaigns for every arm at every
α (K6-TR §5.11.7). Fifteen cells of n=0. There is no evidence here of any kind, in either
direction.

### 8.6 When you cannot tell which regime you are in

SPADE-SPEC Stage 3 proposed a regime test computed from plate 1 alone — measure the additive
share, decide smooth-vs-deceptive, and route accordingly. It was built, the rule was frozen
in a commit containing no code and no result, and it was scored once against two held-out
families.

**It fired zero times out of 50 on both** (§37, `results/versionc-detector-heldout.json`).

And it is not a near miss. The held-out families' `additive_share` ranges are **strictly
nested inside** the fit range at both ends:

| set | `additive_share` range | n |
|---|---|---|
| fit (hill / levy / rosenbrock) | [0.1054, 0.8860] | 150 |
| hartmann6 | [0.2673, 0.8856] | 50 |
| ackley | [0.2949, 0.8534] | 50 |

**The deceptive families are *less* extreme on this statistic than the unimodal ones.** No
threshold setting separates classes that are nested. The leave-one-out false-positive rate on
the fit set is 2/150 = 1.33%, so the rule is well-formed and the **statistic** is empty —
which is a sharper conclusion than either fact alone (§37.3).

**Version C ships without the detector.** In practice you have to decide the regime from
prior knowledge of your biology, not from plate 1.

*It does not license* "landscape class is undetectable from plate 1." One statistic, one
plate size (40), two held-out families. Three other candidate statistics were ranked and
never frozen (§37.4).

### 8.7 Cases where SPADE simply declines to answer

Worth stating on its own, because it is a real operational risk. Across the five families at
d=6, σ=0.25, α=0.95, SPADE's **non-vacuity** — the fraction of cells where it certifies
anything at all — runs from 22/24 (rosenbrock, levy) down to 2/24 (hartmann6) and 0/24
(ackley) (§41.1). At the primary Hill cell it certifies a non-empty predictive region in
**42.25%** of campaigns at σ=0.25 (§31, §38.7).

Plan for the possibility that you spend 48 wells and get back "not determined." That is an
honest answer, and it is better than a false region — but you need to know it can happen
before you commit the plate, not after.

---

## 9. Known limitations and open questions

Ordered roughly by how much they should change what you do.

### 9.1 Version C has never been run prospectively as a method

**The single most important caveat in this document.**

> Every number in §32, §38, §40 and §42 is **Version B's wells scored under Version C's
> rules.** The three scoring changes cannot be validated by re-scoring the campaigns they
> were designed against, and **no claim in the repository is evidence that a lab running
> Version C prospectively would see these numbers** (§43.5).

Related: K-C2 (the hard stop) and K-C3 pass **structurally, not evidentially** — Version C's
selected sets are bit-identical to Version B's and both quantities are built from columns
gated at |Δ| = 0. They *could not have moved*, and they did not. A pass there is not an
independent re-test of the certificate (§38.3, §44.4).

### 9.2 The certificate's cross-family coverage is one dimension and one noise level

`results/p8-certificate-families.json` is the first and only measurement of SPADE's
certificate outside hill: five families, **d=6, σ_rel=0.25 only.** The whole cross-family
*map* programme (`p6-families.json`, 96,000 rows) carries **no `alpha_star`, no `ce_*`, no
`vorobev_*` columns at all** — it tests SPADE's map off hill and not its certificate (§25.3).

**`versionb` was never run at d=8**, so the SPADE arms cannot be gated there and no
certificate result exists at d=8 (§44.5).

### 9.3 Plate 2 has not been shown to earn its place

This is uncomfortable and the repository says so plainly.

* **`plate1_only` — plate 1 alone, no LSE, no second plate — scores *identically* to
  `versionb` at every cell of the τ_frac = 0.60 containment table** (K6-TR §1.4). Containment
  is a floor four of five arms clear, not a ranking metric.
* **74–85% of Version B's KILL-1 margin at the surviving thresholds is contributed by plate 1
  being an LHS**, not by plate 2, and plate 2's own contribution **costs** regret (+0.0276 vs
  `plate1_only`, p = 0.0166) (K6-TR §10).
* **You may not write that the LSE criterion beats 8 random wells.** The
  `versionb − versionb_random` contrast conflates *the criterion* with *8 extra wells*; the
  control's 8 plate-2 wells beat the best of its 40 plate-1 wells in **0 of 50** campaigns, so
  on the reported-best rule it is a no-second-plate arm. The arm registered to separate them
  (Amendment E3's 44+4 split) was never run (K6-TR §10, R3).
* Under the posterior-mean terminal rule, `versionb`, `versionb_random` and
  `versionb_predictive` shift by **−0.0468, −0.0482 and −0.0500 — indistinguishable from each
  other**, with `lhs` and `sobol` in the same band. **The wells earn the gain; the selection
  criterion does not** (§39.3).

The honest position: SPADE's *design* (48 spread wells, all factors varied) is doing most of
the work that has been measured. The LSE second plate is the part with the weakest evidence.

### 9.4 The guarantee excludes hyperparameter uncertainty

Conservative-**given-the-model**. Plug-in hyperparameters sit outside the guarantee
(`src/boec/vorobev.py`; K6-TR §6.3). Report the coverage check beside the certificate.

### 9.5 Estimator defects that are corrected but worth knowing

* **512 draws is not enough** to estimate `CE_α`'s containment at γ ≥ 0.95. Use ≥ 1,024,
  prefer 4,096, and cross-fit for a quoted number (§29). The registered mechanism —
  "bias scales with the number of candidate quantiles scanned" — was **tested and failed**:
  `n_rho` = 16 and 64 give identical containment at every draw level. The bias is Monte Carlo
  error in the containment estimate itself (§29.1). Recorded as a failed prediction rather
  than quietly dropped.
* **The circular selection bias is real**, positive at both σ, and **rises with α**. At
  α=0.95, σ=0.10 the reported containment is overstated by **3.3 percentage points on
  average and by up to 12.7** (§38.4). *(A "4× larger at σ=0.10" multiplier was published
  and is withdrawn — the two σ have unequal, self-selected populations, §43.3. The direction
  is safe; the multiplier is not.)*

### 9.6 Statistical-design limits you should not repeat

* **The containment sweep as designed cannot detect what it was asked to detect.** At n=50,
  p=0.95, discreteness means **a cell at 45/50 can never reach p < 0.10 no matter what else
  is true**, and after Holm ×72 even 42/50 cannot reach 0.05. Detecting a sub-nominal
  certificate needs **more seeds per cell, not more cells** (§22). An earlier multiplicity
  correction used a continuity-corrected normal approximation to a Binomial(50, 0.95) tail —
  `np(1−p) = 2.5`, an order of magnitude below the usual rule of thumb — and Holm ×72 on the
  leading cell is **0.2296, not 0.043** (§22).
* **Never pool across `τ_frac`.** Four thresholds computed on the same campaign, the same
  posterior and the same draws are not four Bernoulli trials. Eleven pooling sites were found
  and a published table was withdrawn (§9.5, §4.8).
* **The two noise levels are not independent samples.** The oracle seeds on `seed` alone,
  never on σ, so σ=0.25 and σ=0.10 are **one noise realisation at two amplitudes**. Effective
  n for a cross-σ static-arm comparison is **12–27, not 50** (§9.7).
* **"The rankings differ in N of N cells" is near-vacuous.** Two independent random orderings
  of 8 arms coincide with probability 1/40,320. The count is reported as a descriptive fact
  with its denominator and nothing rests on it (§24.1). The ρ ≈ 0 result behind it **does not
  replicate** — the sign structure reverses between K6 and P6 (§24.2). The supersede decision
  for error volumes survives **on mechanism**, not on that correlation (§24.3).

### 9.7 Things in SPADE-SPEC that were never built or tested

| spec item | status |
|---|---|
| Stage 0 — day-0 covariate adjustment | **untested.** No paired day-0/endpoint series exists; needs a prospective measurement (§4.7) |
| Stage 1 — 49-point OA-LHS + triplicate anchors, 55 wells | **not built.** Cannot be gated against any committed column; dropped (§7). What ran is 40 LHS + 8 LSE = 48 |
| Stage 2 — σ̂ from replicates | **partially.** The GP does take σ as fixed and known, but deriving it from replicates is K1, unrun (§7) |
| Stage 3 — the frozen regime detector | **built, frozen, tested once, FAILED** — 0/50 on both held-out families (§37) |
| Stage 5 — confirm-and-average | **unrun.** K3 (confirm-and-average vs confirm-and-replace) is registered and never executed (§7) |

### 9.8 Genuinely open questions

* Whether the LSE second plate improves any *deliverable*. No arm was run with the exclusion
  disabled, and the 44+4 separation arm was never run (K6-TR §10, R1/R3).
* Whether Amendment B3's subspace restriction helps or hurts `doe`'s calibration. **No
  committed evidence exists either way**; the comparison cannot be made from committed files
  at all (§4.8, §9.5).
* *Why* the posterior is confident where it is wrong — specifically, whether α* rewards
  *spatially coherent* high-exceedance regions rather than merely *large* ones. Untested; it
  would need a region-geometry statistic this project does not compute (§31). Nothing in the
  document rests on it.
* Whether `sobol` beating everything on four validated metrics is a real, portable finding or
  a property of these families. It reproduces from four independent directions (§23.3, §27.3)
  and has no proposed mechanism.
* The regret-against-budget curve. It needs per-round checkpoints; a terminal re-score cannot
  produce them (§42.4). What exists is 11 budget checkpoints for 4 arms, and it shows the
  single-budget comparison at 48 is **a snapshot across a crossing, not a summary of a
  curve** — at σ=0.10 `doe`'s lead is already gone at 48 and inverts by 150 (§34.5).

---

## 10. Glossary

**α (alpha) — regional confidence.** The joint assurance: `P(CE_α ⊆ Γ) ≥ α`, the probability
that **no** point in the certified region is falsely certified. Not the average of pointwise
probabilities. `src/boec/vorobev.py`.

**α\* (alpha-star).** The largest α at which a non-empty conservative estimate exists. Always
defined, even when every 95% region is empty. **Model-internal**; it measures *willingness to
certify*, not certificate quality (§28, §31). No claim in this repository may rest on it.

**Brier / calibration / refinement.** `Brier = calibration − refinement + uncertainty`
(Murphy decomposition). Calibration is reliability, **lower is better**; refinement is
resolution, **higher is better**. Reporting Brier alone hides which half you are winning
(§27.4).

**`CE_α` — conservative estimate.** The largest Vorob'ev quantile whose joint containment
reaches α. This *is* the SPADE certificate. Azzimonti, Ginsbourger, Chevalier, Bect & Richet
(2016; SIAM/ASA JUQ 2021), on Chevalier's (2013) Vorob'ev machinery.

**`ce_contain` — circular containment.** `conservative_estimate` selects on this quantity and
it is then re-measured on the same draws, so it cannot fall below α. **Never report it as
evidence the guarantee holds.**

**`ce_empirical` — empirical containment.** The validated, non-circular test: the fraction of
independent campaigns whose certified set was wholly inside the true region. Must be ≥ α.
Returns `None`/`nan` for an empty set, because a vacuous containment counted as a success
would inflate the rate with campaigns that certified nothing.

**Conservative-given-the-model.** The guarantee holds under the fitted posterior.
Hyperparameters are plug-in and their uncertainty sits *outside* it.

**`D_gamma` — Peterson's design space.** `{x : P(Y ≥ τ | x, data) ≥ γ}` with `Y` a **future
observation**. Carries process noise as well as estimation error. The ICH Q8 object, and the
primary deliverable here. Peterson (2008); Peterson & Lief (2010).

**γ (gamma) — content / point-level margin.** The per-recipe probability that a future batch
clears τ. Raising it raises the per-point bar and lowers the certifiability ceiling.

**Identification gap.** `terminal_rule_regret − oracle_best` — how much worse the nominated
recipe is than the best well the campaign actually visited. It can go **negative** under a
posterior-mean rule, because that rule may propose an unsampled point; at σ=0.10 five arms
including all three SPADE arms do exactly that, and the "gap" becomes an extrapolation margin
(§39.2).

**Latent vs predictive.** *Latent* regions are about the mean response; *predictive* regions
are about the next batch and must additionally absorb σ. Predictive regions are empty 54–69%
of the time against 16–25% for latent ones at the same thresholds (K6-TR §5.7). **The
deliverable is predictive.**

**LSE / straddle.** Level-set estimation. Bryan's (2005) criterion
`1.96·sd − |mean − θ|`: high where the model is uncertain **and** near the threshold.
`straddle_predictive_score` is the variant targeting the predictive contour.

**`n_active`.** How many axes the fitted model actually saw vary. If you screened, this is
less than `d`, and certified volume is over the active subspace only (Amendment B3). It makes
box volumes non-comparable across arms.

**Non-vacuity.** The fraction of campaigns in which the method returns a **non-empty**
certificate. SPADE at the primary Hill cell: 0.4225 (σ=0.25), 0.7892 (σ=0.10) (§38.7).

**Rule A vs rule P.** Two *terminal rules* — how a campaign nominates its final recipe.
**Rule A** takes the best observed reading. **Rule P** takes the argmax of the fitted
posterior mean. They are **different estimands and their numbers must never be compared
across**; every table carrying both must say which is which (§43.1). Under rule P, `doe`
goes from best of nine to worst of nine and SPADE from sixth to first, on the same campaigns
(§34.1).

**SESOI.** Smallest effect of interest. **0.02** on the regret scale throughout this project.

**Simple regret.** `mu_max − f(x̂)` for the one nominated recipe. A functional of **one
point**. The incumbent object in the BO literature, and the one this project argues is the
wrong column to read if you need a region.

**`τ` (tau) — the spec.** The response level a batch must clear.

**`τ_frac`.** `τ / tau_max(γ, σ_rel)`. Registered as a *fraction* rather than an absolute so
the object cannot degenerate into a table of zeros (§4.5). Note the algebraic identity: the
latent threshold `θ = τ_frac · mu_max` for **every** γ, verified to machine precision.

**`tau_max` — the certifiability ceiling.** `mu_max · (1 − z_γ · σ_rel)`. Derived with
estimation error set to zero, so **no design, no model and no number of wells can beat it.**
A spec above it is not a hard problem; it is an unanswerable one. `designspace.tau_max`.

**Symmetric-difference error volume.** Expected type I + type II volume against the true
excursion set (Azzimonti & Ginsbourger 2018). **The only honest single scalar** — type I read
alone ranks *certifying nothing* first (§9.4).

**Vorob'ev quantile.** `Q_ρ = {x : p(x) ≥ ρ}` where `p(x) = P(f(x) ≥ θ)` is the coverage
function of the random excursion set. `CE_α` is the largest such quantile meeting the joint
confidence.

---

*Written against `docs/SPADE-SPEC.md`, `docs/FINDINGS-SPADE.md` (44 sections),
`docs/METHODS.md`, `docs/K6-TECHNICAL-REPORT.md`, and the docstrings of `src/boec/lse.py`,
`src/boec/vorobev.py` and `src/boec/designspace.py`. Where those sources disagree with each
other, `FINDINGS-SPADE.md` §44 is the index of which correction is current.*
