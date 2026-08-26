# Session log — 2026-08-26 · SPADE certificate calibration and the Plate-2 question

Complete record of one session. Every number here was computed in-session from committed
artefacts or from runs launched here; each is traceable to a file and a commit. Failures,
retractions and my own bugs are recorded alongside the positive results, in the order they
happened.

Branch: `kr-effective-resolution`. Specs frozen: `7ae6fc6` (KR), `1a3d927` (KS), `6848e2f` (KT),
KU + amendments. Campaigns regenerated: 2,000+, **zero gate failures**.

---

## 0. One-paragraph summary

The SPADE excursion certificate was diagnosed as miscalibrated. The root cause is **not** the
acquisition rule, the noise model, or duplicate policies: the GP's latent posterior is
measurably too narrow (E3, committed long ago), the certificate's own containment statistic is
computed from those same draws and is therefore blind to the error, and the resulting failure
rate is governed by **how much volume the certificate claims**. Calibrating a volume cap against
held-out truth repairs the guarantee on every family tested. Two registered attempts to make
that calibration transfer across families **failed** (`k_eff`, `kappa_tail`), and a third
explanation — that my transfer comparison was confounded by target size — is under prospective
test (KU). Separately, the Plate-2 targeting rule, killed three times on map error, is found to
**beat random placement on certificate containment** (+0.0239, 95% CI [+0.0016, +0.0467]),
while random placement is worth nothing at all (+0.0003, p=0.95).

---

## 1. Stress-test of the incoming diagnosis

The diagnosis handed to me was directionally right and specifically wrong in five ways.

| claim | verdict |
|---|---|
| "pointwise GP probabilities don't give simultaneous coverage" | **Wrong about this codebase.** `src/boec/vorobev.py` opens with a section titled *"WHY POINTWISE CERTIFICATION IS THE WRONG OBJECT"* and implements Azzimonti's conservative estimate properly. `containment_probability` is a genuine **joint** quantity over joint draws. |
| "boundary acquisition uses `p(1-p)`, should target γ=0.95 not 0.50" | **Wrong.** γ is *joint assurance over a region*, not a pointwise level. p=0.5 is *correct* for the map-loss metric (symmetric difference is defined at that contour). The committed arm uses Bryan's straddle in value space, not `p(1-p)`. |
| "truth containment was 38.1%" | **Does not reproduce.** Committed P8 at α=0.95 pooled: **0.9248, LB 0.9192 — already clears 90%.** The pairing "internal 99.5% + truth 38.1%" occurs nowhere in committed data. |
| "29 maps with zero failures for a 90% bound" | **Correct** (`0.05^(1/29) = 0.9019`) but brittle: one failure needs n=46; at n=29 one failure drops the bound to 0.847. |
| six co-equal contributing problems | The one true root cause ("validates against draws from its own fitted GP") is listed sixth of six, beside duplicate arms and scoring seeds. **It is not one of six problems. It is the problem.** |

Reproduction table across every committed source, γ=0.95 and below:

| source | α | non-empty | model-internal | **truth** | 95% LB |
|---|---|---|---|---|---|
| P8 (5 families) | 0.95 | 6,384 | 0.9948 | **0.9248** | 0.9192 |
| P8 | 0.80 | 9,493 | 0.9452 | 0.9331 | 0.9287 |
| P8 | 0.50 | 12,461 | 0.7588 | 0.8511 | 0.8458 |
| τ-quantile (ackley+h6) | 0.95 | 1,518 | 0.9850 | 0.8340 | 0.8175 |
| τ-quantile | 0.50 | 3,216 | 0.5764 | **0.4104** | 0.3961 |

---

## 2. Root cause, in three verified steps

**Step 1 — the GP's latent variance is too small, and this was measured long ago and never
connected to the certificate.** `results/e3.log`, committed:

| cell | latent coverage (nominal 0.95) | selection-effect gap |
|---|---|---|
| d=6, σ=0.25 | **0.8189** | +0.0086 |
| d=6, σ=0.10 | 0.8500 | **−0.0520** |
| d=8, σ=0.25 | **0.7644** | **−0.0900** |
| d=8, σ=0.10 | 0.8912 | −0.0149 |

Miscalibrated in every cell, and worse *exactly where the optimizer chose to look*. The
certificate is a latent-`f` claim, so this is the relevant column.

**Step 2 — the certificate math is exact with respect to that wrong posterior.** Cross-fitting
(F3, `conservative_estimate_split`) removes the winner's-curse *selection* bias. It cannot
detect that the draws themselves are too narrow.

**Step 3 — the error compounds in certified volume, and the internal statistic is blind to it.**

| certified volume bin | n | model-internal | **truth** | true prevalence |
|---|---|---|---|---|
| [0.001, 0.002] | 794 | 0.9835 | **1.000** | 0.890 |
| [0.002, 0.014] | 952 | 0.9933 | 0.998 | 0.956 |
| [0.014, 0.082] | 881 | 1.0000 | 0.991 | 0.985 |
| [0.082, 0.326] | 883 | 1.0000 | 0.931 | 0.992 |
| [0.326, 1.000] | 878 | 0.9982 | **0.552** | 0.996 |

Internal is **flat at 0.98–1.00**; truth collapses to 0.552. The obvious confound is not merely
absent but **reversed**: inside the *highest* true-prevalence stratum (≥0.95 — where the
acceptable region is nearly the whole box and containment should be easiest), containment still
falls 0.995 → 0.750 with volume. Decay is clean: `P(contained) ≈ exp(−0.85·V)`.

> **Root cause:** the certificate's failure probability is governed by how much volume it claims,
> and the statistic it uses to decide how much to claim cannot see volume.

This also reframes the paper's scope claim: **hill does not pass because hill is special — hill
passes because hill's certified regions are smaller.** It is a volume law, not a family law.

---

## 3. The fix that works

Volume-conditional (Mondrian-style) calibration against held-out truth. A **single global cap
does not bind** — the mass of easy small regions swamps the rare large failures — so calibration
must be conditional on volume.

| held out (never in calibration) | uncalibrated | **calibrated** | 95% LB | answer rate |
|---|---|---|---|---|
| hill | 0.9939 | 0.9988 | 0.9962 | 0.84 |
| levy | 0.8958 | **0.9730** | 0.9654 | 0.85 |
| rosenbrock | 0.8930 | **0.9968** | 0.9933 | 0.63 |
| ackley + hartmann6 (split-half seeds) | 0.8284 | **0.9452** | 0.9238 | 0.54 |

**≥90% held out on all five families.** This has never stopped working and is the session's
central positive result.

---

## 4. KR — `k_eff`. FAILED, dropped.

Frozen `7ae6fc6`. Hypothesis: failure is governed by *effectively independent locations*,
`k_eff = V / ∏ min(ℓᵢ,1)`, so calibration should transfer in those units.
Implementation: `src/boec/resolution.py`, TDD, 10 tests.

1,000 campaigns regenerated, **0 gate failures**.

| gate | bar | measured | verdict |
|---|---|---|---|
| KR-1 transfer | LB ≥ 0.90 | **LB 0.8175** | **FAIL** |
| KR-2 dispersion | `k_eff` < 4× | **1138×** (box volume 370×) | **FAIL** |
| KR-4 Occam | drop if no better | identical to box volume | **DROP** |

`k_eff` made dispersion 3× *worse* and separated contained-from-failed *less* well than raw
volume (easy 1.48 vs 2.40 SD; hard 1.17 vs 1.22). Strictly dominated. Dropped per the registered
falsifier. Arithmetic sanity-checked: hill's caps imply `ℓ = 0.578` against this repo's
independently measured median ARD lengthscale of 0.5982.

**What the failure revealed — two distinct failure modes:**

| family | median `k_eff` | % regions **below one correlation cell** | truth containment |
|---|---|---|---|
| hill / levy / rosenbrock | 0.60 / 0.90 / 1.86 | 57% / 51% / 43% | 0.994 / 0.896 / 0.893 |
| **ackley / hartmann6** | **0.061 / 0.082** | **98.8% / 100%** | 0.889 / 0.808 |

- **Resolution failure** (easy): region spans many cells → volume conditioning works.
- **Localization failure** (hard): sub-resolution regions, confidently placed in the *wrong part
  of the box*. No statistic computed from the region's own geometry can detect a misplaced region.

---

## 5. KS — `kappa_tail` (self-calibration). FAILED, dropped.

Frozen `1a3d927`. Hypothesis: a misplaced region is a symptom of a surrogate that does not fit
*this* landscape, measurable from the campaign's own leave-one-out residuals — family-agnostic
**by construction**, never consulting a family library.
Implementation: `src/boec/selfcalib.py`, TDD, 13 tests (exact block-inverse LOO identity,
asserted against `n` brute-force refits; condition-number guard rejecting a noise-free kernel).

| gate | bar | measured | verdict |
|---|---|---|---|
| KS-1 transfer | LB ≥ 0.90 | **LB 0.8074** | **FAIL** |
| KS-2 mechanism | ratio ≥ 1.20 | **1.315** | **PASS** |
| KS-4 Occam | gain ≥ 0.25 SD | 0.19 vs 1.22 SD (**−1.03**) | **DROP** |

**KS-2 passing matters:** the GP *does* know it fits worse on the hard families (31% higher
`kappa_tail`). It simply cannot say *which individual campaign* will produce a bad certificate.

**Design bug caught by TDD before any result existed.** `kappa_tail` was registered as the 0.90
quantile of |z|. A synthetic unit test showed that with 2 bad wells in 20, the 0.90 quantile
interpolates to **0.47** — *below* a uniformly-mediocre campaign's 1.5 — so it could not detect
the ackley signature it was chosen for. Changed to `max|z|`, amended in spec §2a with the
reason, **before** the runner was extended or any campaign scored.

**My own analyser bug, found while adjudicating.** The 5×5 grid used ±∞ outer edges, so a test
campaign outside the calibration range inherited the nearest bin's verdict — exactly the "never
assumed safe" failure §5 was written to prevent. Fixed to match the frozen spec, both numbers
reported (0.8175 buggy / 0.8074 correct). Neither passes, so nothing hinged on it.

---

## 6. The confound — why KR and KS were testing the wrong thing

| | median true prevalence of target | median certified volume |
|---|---|---|
| calibration set (easy, `tau_frac` grid) | **0.9870** | 0.0310 |
| test set (hard, τ-quantile grid) | **0.3000** | 0.0020 |

**I calibrated on targets covering 99% of the box and tested on targets covering 30%.** Every
`tau_frac` cell on the easy families sits at median prevalence ≈ 0.98. That is a target-*size*
difference, not a family difference — the same confound `SPADE-TAU-QUANTILE-SPEC.md` §1
diagnosed once before for a different question.

**KR-1's and KS-1's FAIL verdicts stand as recorded.** They are correct verdicts on the
comparisons that were actually run. Not amended.

**Post-hoc evidence, labelled post-hoc.** Both hard families share the quantile grid, so transfer
between them is prevalence-matched and free:

| calibrate on | apply unchanged to | uncalibrated | calibrated | 95% LB | |
|---|---|---|---|---|---|
| ackley | hartmann6 | 0.8081 | 0.9756 | 0.9524 | PASS |
| hartmann6 | ackley | 0.8889 | 0.9067 | 0.8810 | FAIL |
| **pooled** | | | **0.9310** | **0.9131** | **PASS** |

With the easy-family LOFO, **5 of 6 directional transfers pass**, both regimes pass pooled.

---

## 7. KU — prospective confirmation. RUNNING.

Frozen before any result. Scores `levy` + `rosenbrock` on the τ-quantile grid — data
`SPADE-TAU-QUANTILE-SPEC.md` §4 explicitly declined to generate — putting **four** families on
one prevalence convention for the first time. Two amendments, both recorded **before** the run:

- **§5a — `hill` excluded**, technical: `score_family` reaches the oracle via `family_evaluator`,
  which raises `KeyError` on `'hill'` (an ensemble needing `instance_by_id` + `BiphasicOracle`).
  Adding it means forking the committed scorer. This removes the **easiest** family — the one
  already validated — so KU is *harder* for the exclusion. KU-2 moves 4-of-5 → 3-of-4.
- **§5b — seeds restored 25 → 50**, on a firewalled timing pilot measuring 27.8 s/campaign
  (not the 85–113 s estimated from the KT path). Increases power *and* matches the committed
  `ackley`/`hartmann6` seed count exactly, removing an n-mismatch the reduction would have
  injected into the very comparison KU exists to make.

400 campaigns, ~3.1 h.

---

## 8. KT — the assurance level α. FROZEN, unrun, deprioritised behind KU.

Frozen `6848e2f`. **The category error KR and KS shared:** both fitted a post-hoc filter on the
certificate's *output*. Neither touched the certificate.
`conservative_estimate(draws, θ, α)` is **monotone in α by construction** — the exact nested
family RCPS requires — and `ALPHAS = (0.50, 0.80, 0.95)` in every certificate run this project
has ever done. Achieved containment on the hard families climbs **0.41 → 0.65 → 0.83** and the
grid simply stops. Above 0.95 is *unmeasured*, not measured-and-failed.

KT-2 voids KT-1 if **paired** monotonicity fails (the marginal table is non-monotone,
0.936 → 0.925 on the easy families, a composition effect).

`run_kt_assurance_fast.py` — certificate-only scorer — **reproduction gate vs committed α=0.95:
0 mismatching rows out of 72.** The fork measures the same estimator. It is not faster
(107.9 s/campaign; the certificate scan is the cost, not the 20k grid).

---

## 9. Plate 2 — the architecture question, and the first positive result

### 9.1 What was already established, and stands

KF-3/3b/3c killed boundary targeting on **map error**, three times. That negative is
**well-powered, not an absence of evidence**: n=250 pairs, **MDE 0.0057** against a pre-declared
SESOI of **0.02** — resolution 3.5× finer than the smallest effect of interest — observed
+0.0029, targeted nominally *worse* than random.

### 9.2 A retraction of my own claim, made this session

I reported "+19.1% certified volume for `versionb` over `plate1_only`, 4× over random."
**Withdrawn.** It came from one calibration split (seeds <25); on the full data the ordering
**flips** (`plate1_only` 0.1970 vs `versionb` 0.1475), and a 1,000-resample bootstrap shows the
cap statistic cannot rank arms at all:

| arm | cap V* | 95% CI | CI width ÷ point |
|---|---|---|---|
| versionb | 0.1475 | [0.0170, 0.3216] | **2.1×** |
| versionb_random | 0.1208 | [0.0705, 0.2320] | 1.3× |
| plate1_only | 0.1970 | [0.0150, 0.2210] | 1.0× |

`versionb − random` = +0.057, **95% CI [−0.114, +0.232]** — spans zero decisively.

I also reported the certificate comparison as "n=14, hopelessly underpowered." **That was my own
indexing bug** — I keyed on campaign and `setdefault` silently dropped 23 of each campaign's 24
`(γ, τ_frac)` cells.

### 9.3 Why 8 wells cannot change the resolution regime

From KR's own fitted lengthscales:

| family | median ℓ | correlation cells in box | wells/cell @40 | @48 |
|---|---|---|---|---|
| hill | 0.619 | 28.2 | 1.42 | 1.70 |
| levy | 0.512 | 69.1 | **0.58** | 0.69 |
| rosenbrock | 0.581 | 40.4 | 0.99 | 1.19 |
| ackley | 0.500 | 83.6 | **0.48** | 0.57 |
| hartmann6 | 0.720 | 18.9 | 2.12 | 2.54 |

Plate 2 moves wells-per-correlation-cell by **exactly 20%, whatever the placement rule** (8/40).
levy and ackley sit **below one well per correlation cell** — the design undersamples the field's
own correlation structure. Leverage is roughly linear in the density change, which predicts a
**24/24 split** is where an adaptive second plate starts to have room to matter.

### 9.4 The positive result — targeting beats random ON THE CERTIFICATE

Campaign-clustered paired tests (mean over each campaign's cells, then paired — per-cell pairing
would count 24 correlated rows per campaign):

| comparison | n | effect on truth containment | p |
|---|---|---|---|
| **targeted plate 2 vs RANDOM plate 2** | 149 | **+0.0239** | **0.019** |
| predictive plate 2 vs RANDOM plate 2 | 150 | **+0.0227** | **0.0088** |
| targeted 2-plate vs 1-plate | 149 | +0.0242 | 0.053 |
| **RANDOM 2-plate vs 1-plate** | 150 | **+0.0003** | **0.95** |

Bootstrap on the key contrast: **+0.0239, 95% CI [+0.0016, +0.0467]** — separates from zero.
Independently replicated by a second, differently-built arm (`versionb_predictive`, p=0.0088).

**Random placement of the extra 8 wells is worth nothing (+0.0003, p=0.95). The second plate has
value only when it is targeted — the adaptivity *is* the value.**

This reconciles with KF-3 rather than contradicting it. On map error I reproduce the negative
(1-plate better by +0.0088, inside SESOI). Boundary targeting refines the *boundary of the
certified region* — precisely what containment depends on — and barely moves global
symmetric-difference error. **The value was invisible on the endpoint KF-3 registered.** That is
this paper's own thesis applied to itself: map ranking and certificate ranking are different
objects that different methods win.

**Three caveats, unresolved:**
1. **Post-hoc endpoint.** Containment was chosen after map error failed. The *wells* were
   allocated prospectively by each arm's own rule in Version B, so this is a genuine allocation
   comparison — but the endpoint was not pre-registered.
2. **No Holm correction** across the many endpoints examined this session. p=0.019 is uncorrected.
3. **No pre-declared SESOI for containment.** +0.024 separates from zero; materiality has no bar.

---

## 10. Prior art check — one paper lands directly on this plan

**[Dette, Liu & Yu, arXiv:2608.19815](https://arxiv.org/abs/2608.19815), submitted 20 Aug 2026** —
conformal risk control for reliability-set estimation under a misspecified working model, *with
an adaptive design concentrating on the set and its boundary*. The general idea cannot be
claimed as novel. What they do **not** do, read from the paper:

| | Dette et al. 2026 | this setting |
|---|---|---|
| risk controlled | expected **false-inclusion rate** | **simultaneous** whole-region containment |
| calibration unit | individual observations | whole maps / tasks |
| model | logistic / SVM, Bernoulli homoskedastic | GP, heteroskedastic |
| Vorob'ev / conservative sets | never mentioned | core machinery |
| abstention | degenerate (λ = −1 on empty) | principled |
| budget | n=300 | 48 wells |

A false-inclusion *fraction* and a whole-region containment *probability* are different
estimands, and the latter is what a batch record or an ICH Q8 design space asserts.

---

## 11. Ledger

| item | status | evidence |
|---|---|---|
| Root cause of certificate miscalibration | **Established** | E3 + volume law + circular internal statistic |
| Per-family volume-conditional calibration | **Works, ≥90% held out, all 5 families** | §3 |
| `k_eff` transfer | **FAILED, dropped** | KR-1/KR-2/KR-4 |
| `kappa_tail` transfer | **FAILED, dropped** | KS-1/KS-4 |
| Prevalence confound identified | **Established** | §6, 0.987 vs 0.300 |
| Prevalence-matched transfer | **Running (KU)** | 5/6 post-hoc directions pass |
| α as RCPS λ | **Frozen, unrun (KT)** | headroom 0.41→0.65→0.83 |
| Plate-2 targeting on map error | **Well-powered null** | MDE 0.0057 vs SESOI 0.02 |
| Plate-2 targeting on certificate | **+0.0239, CI excludes 0, replicated** | §9.4, post-hoc endpoint |
| "+19.1% certified volume" | **WITHDRAWN** | bootstrap CI [−0.114, +0.232] |
| Two-plate architecture without targeting | **Worth nothing** | +0.0003, p=0.95 |

**Regression suite: 1,645 passed, 0 failures.** New modules: `resolution.py` (10 tests),
`selfcalib.py` (13 tests). All watched RED before GREEN.

---

## 12. Next, in priority order

1. **KU verdict** (running) — does prevalence-matched transfer confirm prospectively?
2. **KV** — pre-register the Plate-2 certificate finding with a declared SESOI and Holm family,
   then confirm prospectively. This is the highest-value open item: it is the first positive
   result for the targeting mechanism in the project's history.
3. **Certificate-targeted acquisition** — the current rule targets the *threshold contour* θ
   (Bryan's straddle). The certificate's binding frontier is the boundary of the conservative
   estimate `CE_α`, which is a *different contour*. Targeting the deliverable directly is the
   principled way to make +0.0239 larger. Registered separately, not tuned into existence.
4. **24/24 budget split** — §9.3 predicts leverage is linear in density change; 8/40 gives 20%,
   24/24 gives 100%.
5. **KT** if KU fails.
