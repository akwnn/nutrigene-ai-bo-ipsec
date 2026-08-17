# Supplementary tables

The paper is `docs/RESEARCH-SUMMARY.md`. This file is the SI: long tables, Q-ids, and working notes. Edit freely; do not copy these tables back into the main file.

**How we split.** Headline numbers, three figures, and the laboratory decision guide stay in the paper. Internal run names (E2, Q34, …) are reproducibility tags here.

| Figure | File | Generator |
|---|---|---|
| 1. Winner by terminal rule and noise | `results/figures/fig1-scoring.html` | `scripts/make_scoring_figure.py` |
| 2. Cost in wells and in rounds | `results/figures/cost-curves.html` | `scripts/make_cost_curve_page.py` |
| 3. Saddle and ridge constraint | `results/figures/fig3-saddle.html` | `scripts/make_saddle_figure.py` |

Lab notebooks (not the paper): `docs/RESULTS.md`, `docs/WHAT-WE-FOUND.md`. New campaigns go there first.

### Changelog (locator corrections)

**D20.** An earlier DoE “best observed” column read hidden tested-best (`curve_true`) rather than the noisy argmax (`reported_best_curve`). All measured-value-argmax DoE figures in the paper use the corrected locator. Primary-cell mean **0.0958**, not 0.0597. The 0.0597 figure is DoE **hidden tested-best** (Q55/Q57). Surrogate-recommendation columns were unaffected.

---

## S1. How to read a results table

| Column | Meaning in one sentence |
|---|---|
| DoE, BO, Mean R | Average simple regret. **Lower is better.** 0.10 means the nominated recipe has true quality 0.90. |
| DoE − BO | DoE’s regret minus BO’s regret on the same landscapes. **Negative: DoE better. Positive: BO better.** |
| p | Wilcoxon signed-rank p-value. Small p means the sign of the difference is consistent across landscapes. It does **not** by itself say the gap is large. |
| Call | Which method is ahead when the interval excludes 0. An interval covering 0 is **not** equivalence until TOST (SESOI = 0.02). |
| [low, high] | 95% bootstrap interval for the mean difference. |

**Wilcoxon signed-rank test.** For each of the 25 landscapes, subtract one method from the other. Paired, not assumed Gaussian. Conventional threshold p < 0.05.

**Bootstrap interval.** Resample the 25 landscapes and recompute the mean gap. Answers “how large,” which Wilcoxon does not.

**Holm–Bonferroni.** Used when several arms share a family. Primary DoE-versus-BO tables in the paper §4.1 are single planned contrasts and are not Holm-adjusted.

An interval covering 0 is “not distinguished at n = 25,” not “the methods are identical.” TOST at SESOI = 0.02 is in `results/tost-contrasts.json` (supplement §S10).

**Inferential hierarchy.** Confirmatory, unadjusted: sequential DoE versus named BO at d = 6, σ = 0.25, N = 48, under measured-value argmax and under in-region recommendation (commit `d289e7d`). The other three cells are exploratory. Holm is for multi-arm and multi-target families. Secondary: naïve unconstrained diagnostic, design × surrogate factorial, arrival / P(T ≤ N). Exploratory: control arms, Q42, one-shot GP (five Hill draws). Effect size and interval first; p second.

---

## S2. Why each experiment exists

| ID | In one sentence | Why it is needed |
|---|---|---|
| E1 | Can this BO implementation beat random search on standard functions? | Sanity check. |
| E2 | At 48 wells on the Hill ensemble, who has the better already-run recipe under measured-value argmax? | Main matched-budget comparison. |
| Q27 | Same comparison at eight factors. | E2 omitted DoE at d = 8. |
| Q34 | On the **same** 48 wells, refit a polynomial and a GP to **both** designs. | Separates sampling from surrogate. |
| Q35 | On the **same** DoE polynomial, score best well vs unconstrained peak vs in-region peak. | Separates locator from campaign. |
| Q45 | Four-factor polynomials on both designs. | Removes Q34’s model-dimension confound. |
| Q42 | Levy, Rosenbrock, Hartmann6, Ackley. | Hill is not the only geometry. |
| Q52 | Continue to 200 wells; arrival. | Snapshot at 48 cannot say who is cheaper. |
| Q53 | One-shot GP vs 10-round BO on Q42 families. | Is sequential adaptation doing work? |
| Q54 | Hill one-shot GP at five Latin-hypercube draws. | One draw is not a conclusion. |
| Q55 / Q57 | Hidden tested-best beside measured-value argmax; qLogNEI co-primary. | Search vs identification; wrong-acquisition objection. |
| Q56 | Sequential RSM with steepest ascent, cap 200. | `doe_repeat` is not classical sequential RSM. |
| Q58 | Replicate, confirm top-3, or posterior-mean pick on the same campaigns. | Single readout is one protocol, not all. |
| Q59 | Hartmann6 with and without the 6→4 screen (d = 6). | Is BO’s Hartmann win a screening artefact? |
| Q60 | Average original + confirmation on the top-3 shortlist. | Is Q58’s confirmation-alone interval covering 0 an artefact of discarding the first reading? **Not run.** BO replay failed the 1e-12 gate. |
| Q61 | qLogEI and qLogNEI at q = 1, primary cell. | Is the 0.0595 lead batching rather than terminal rule? **Not run.** Same replay risk. |

| Experiment | Held fixed | Varied |
|---|---|---|
| E2 | Landscapes, N = 48, measured-value argmax | Procedure |
| Q34 | Same 48 evaluations | Design × surrogate |
| Q35 | Fitted quadratic | Locator |
| Q45 | Four-factor polynomials | Design, then surrogate |
| Q52 | d = 6, cap 200 | Budget, target, σ |
| Q54 | Q52 instances and targets | Latin-hypercube draw |
| Q56 | d = 6, cap 200 | Relocation vs `doe_repeat` |
| Q58 | Primary cell campaigns | Final pick |
| Q59 | d = 6, N = 48 | 6→4 cut |

---

## S3. Reconstruction of experimental rounds

Rounds were reconstructed from evaluation checkpoints (commit `633e74d`). A **round** is one plate cycle.

| Procedure | Initial design | Continuation | Incomplete batches |
|---|---|---|---|
| qLogEI | 14 evaluations = round 1 | batches of 4 | Incomplete batch charged as a full plate. Rounds = 1 if n ≤ 14, else 1 + ⌈(n−14)/4⌉ |
| DoE (`doe_repeat`) | 20+27+1 = 48 | Pipeline repeats at 48, 96, 144, 192 | Partial pipeline is not the method. Rounds = 3 × ⌊n/48⌋ |
| doe_ascent | screen + CCD + ascent + confirm | relocates | Registered in `results/q56-doe-ascent.json` |
| spread_gp / random | n in one shot | none | 1 round at any n |

Artefact: `results/q52-rounds-to-arrival.json`.

---

## S4. Control procedures under measured-value argmax

Contrasts are procedure minus qLogEI. Holm is applied within each cell.

**d = 6, σ = 0.25 (primary).**

| Procedure | Mean R | vs qLogEI | p | After Holm |
|---|---|---|---|---|
| DoE | **0.0958** | **−0.0595** | 2.2×10⁻⁵ | DoE superior |
| LHS | 0.1270 | −0.0282 | 0.015 | not significant |
| Coordinate descent | 0.1420 | −0.0133 | 0.34 | null |
| qLogNEI | 0.1532 | −0.0020 | 0.71 | null |
| qLogEI | 0.1553 | — | — | — |
| Sobol' | 0.1724 | +0.0171 | 0.31 | null |
| Random | 0.2216 | +0.0664 | 3.8×10⁻⁵ | BO superior to random |

**d = 6, σ = 0.10.**

| Procedure | Mean R | vs qLogEI | p | Call |
|---|---|---|---|---|
| qLogNEI | 0.0808 | −0.0066 | 0.18 | null |
| qLogEI | 0.0874 | — | — | — |
| Coordinate descent | 0.0880 | +0.0006 | 0.92 | null |
| DoE | 0.0892 | +0.0018 | 0.69 | null |
| LHS | 0.1027 | +0.0153 | 0.11 | null |
| Sobol' | 0.1210 | +0.0336 | 0.00033 | BO superior |
| Random | 0.1693 | +0.0819 | 6×10⁻⁷ | BO superior |

**d = 8, σ = 0.25.**

| Procedure | Mean R | vs qLogEI | p | Call |
|---|---|---|---|---|
| DoE | **0.0963** | **−0.0284** | 0.0023 | DoE superior |
| qLogNEI | 0.1105 | −0.0142 | 0.17 | null |
| qLogEI | 0.1247 | — | — | — |
| LHS | 0.1627 | +0.0380 | 0.019 | BO superior (uncorrected) |
| Random | 0.1712 | +0.0465 | 1.8×10⁻⁵ | BO superior |
| Sobol' | 0.1804 | +0.0557 | 0.00063 | BO superior |
| Coordinate descent | 0.1926 | +0.0679 | 1.1×10⁻⁶ | BO superior |

**d = 8, σ = 0.10.**

| Procedure | Mean R | vs qLogEI | p | Call |
|---|---|---|---|---|
| qLogNEI | **0.0849** | **−0.0123** | 0.027 | qLogNEI superior to qLogEI |
| DoE | 0.0948 | −0.0024 | 0.43 | null |
| Sobol' | 0.0968 | −0.0004 | 0.94 | null |
| qLogEI | 0.0972 | — | — | — |
| Coordinate descent | 0.1053 | +0.0081 | 0.33 | null |
| LHS | 0.1260 | +0.0288 | 0.0067 | BO superior |
| Random | 0.1272 | +0.0301 | 0.00043 | BO superior |

---

## S5. Change of terminal decision on a fixed campaign (Δ)

Δ = naïve-unconstrained-recommendation regret − measured-value-argmax regret on the same campaign.

| Cell | DoE, measured | DoE, unc. rec. | DoE Δ | BO, measured | BO rec. | BO Δ | DoE share of abs(Δ) |
|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0958 | 0.4163 | **+0.3205** | 0.1553 | 0.1232 | **−0.0321** | ~90% |
| d=6, σ=0.10 | 0.0892 | 0.4300 | +0.3408 | 0.0874 | 0.0703 | −0.0171 | ~95% |
| d=8, σ=0.25 | 0.0963 | 0.3766 | +0.2803 | 0.1247 | 0.1056 | −0.0191 | ~94% |
| d=8, σ=0.10 | 0.0948 | 0.4104 | +0.3156 | 0.0972 | 0.0876 | −0.0096 | ~97% |

GP recommendation vs measured-value argmax: 0.1232 vs 0.1553 (21%); 0.0703 vs 0.0874 (20%); 0.1056 vs 0.1247 (15%); 0.0876 vs 0.0972 (10%).

In-region quadratic minus measured-value argmax (D20-corrected):

| Cell | Constrained − measured | Call |
|---|---|---|
| d=6, σ=0.25 | **+0.0211** [+0.0105, +0.0315] | polynomial worse than its data |
| d=6, σ=0.10 | −0.0036 [−0.0122, +0.0049] | null |
| d=8, σ=0.25 | **+0.0185** [+0.0094, +0.0287] | polynomial worse than its data |
| d=8, σ=0.10 | −0.0071 [−0.0150, +0.0008] | null |

---

## S6. Design versus surrogate (Q34 / Q45)

| Cell of the factorial | d=6, σ=0.25 | d=6, σ=0.10 | d=8, σ=0.25 | d=8, σ=0.10 |
|---|---|---|---|---|
| 1 DoE points, measured-value argmax | 0.0958 | 0.0892 | 0.0963 | 0.0948 |
| 2 BO points, measured-value argmax | 0.1553 | 0.0874 | 0.1247 | 0.0972 |
| 3 DoE points, polynomial (unconstrained) | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| 4 BO points, GP | 0.1232 | 0.0703 | 0.1056 | 0.0876 |
| 5 DoE points, GP | 0.1993 | 0.2728 | 0.1139 | 0.1168 |
| 6 BO points, six-factor polynomial | 0.5838 | 0.3956 | 0.6972 | 0.6784 |

GP minus polynomial on identical DoE points (cell 5 − cell 3): −0.2171 [−0.2524, −0.1834] at the primary cell; −0.1573 / −0.2628 / −0.2936 at the others; all p ≤ 10⁻⁶. Row 6 is **not** a design contrast (confounds design with model dimension).

Four-factor refit (Q45):

| | d=6, σ=0.25 | d=6, σ=0.10 | d=8, σ=0.25 | d=8, σ=0.10 |
|---|---|---|---|---|
| Polynomial on CCD (four factors) | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| Polynomial on BO points, four-factor refit | **0.3035** | **0.1417** | **0.2519** | **0.1435** |
| Polynomial on BO points, six-factor (Q34) | 0.5838 | 0.3956 | 0.6972 | 0.6784 |
| GP on BO points | 0.1232 | 0.0703 | 0.1056 | 0.0876 |
| Design effect (CCD − BO poly., model fixed) | **+0.1129** | **+0.2883** | **+0.1247** | **+0.2669** |
| Surrogate effect (GP − BO poly., design fixed) | **−0.1803** | **−0.0715** | **−0.1462** | **−0.0559** |

All eight contrasts p ≤ 0.0008.

D-efficiency of the four-factor model:

| Coding | CCD | Adaptive (BO) | Ratio |
|---|---|---|---|
| Common unit hypercube | 4.99×10⁻³ | 1.05×10⁻² | BO 2.1× |
| Each design in its own region | 4.58×10⁻² | 1.05×10⁻² | **CCD 4.4×** |

---

## S7. Standard test functions (Q42)

**A** = measured-value argmax; **C unc.** = unconstrained recommendation; **C con.** = constrained recommendation.

**Levy.** Saddle in 25/25 at three cells; 22/25 at d=6, σ=0.10.

| Cell | DoE A | BO A | A | DoE C unc. | BO C | C unc. | DoE C con. | C con. |
|---|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0392 | 0.1156 | DoE | 0.5598 | 0.0794 | BO | 0.0791 | null |
| d=6, σ=0.10 | 0.0241 | 0.0754 | DoE | 0.4559 | 0.0562 | BO | 0.0696 | null |
| d=8, σ=0.25 | 0.0494 | 0.1290 | DoE | 0.4704 | 0.0647 | BO | 0.0663 | null |
| d=8, σ=0.10 | 0.0220 | 0.0787 | DoE | 0.4151 | 0.0664 | BO | 0.0607 | null |

**Rosenbrock.** Saddle in 25/25 at all four cells.

| Cell | DoE A | BO A | A | DoE C unc. | BO C | C unc. | DoE C con. | C con. |
|---|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0328 | 0.0700 | DoE | 0.3026 | 0.0388 | BO | 0.0369 | null |
| d=6, σ=0.10 | 0.0156 | 0.0430 | DoE | 0.2444 | 0.0157 | BO | 0.0254 | not confirmatory (p=0.052) |
| d=8, σ=0.25 | 0.0320 | 0.0823 | DoE | 0.3018 | 0.0419 | BO | 0.0357 | null |
| d=8, σ=0.10 | 0.0174 | 0.0580 | DoE | 0.2549 | 0.0195 | BO | 0.0262 | null |

**Hartmann6 (screened pipeline).** BO leads under every terminal rule. Q59 (paper §4.4): removing the screen at d = 6 makes DoE worse.

| Cell | DoE A | BO A | DoE − BO (A) | DoE C unc. | BO C | DoE C con. |
|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.5623 | **0.2984** | +0.2460 | 0.9008 | 0.2695 | 0.5449 |
| d=6, σ=0.10 | 0.5428 | **0.1938** | +0.3460 | 0.8985 | 0.1740 | 0.5223 |
| d=8, σ=0.25 | 0.6393 | **0.3134** | +0.3189 | 0.8792 | 0.2992 | 0.6309 |
| d=8, σ=0.10 | 0.6534 | **0.2370** | +0.4134 | 0.8751 | 0.2269 | 0.6442 |

**Ackley** is void: the global minimizer is the box centre, which a face-centred CCD evaluates by construction.

Q53: spread_gp vs 10-round qLogEI on these families, five draws. Levy / Rosenbrock null; Hartmann6 / Ackley inferior.

---

## S8. Q52 arrival vs `doe_repeat` (not the fair long-run arm)

These tables compare qLogEI to **repeated non-relocating CCD**. The paper’s long-run claim uses `doe_ascent` (Q56). Kept here so the withdrawn “24/25 vs 13/25” cell remains auditable.

**Low noise (σ = 0.10), measured-value argmax.**

| τ | BO hits | BO eval. | BO rounds | DoE hits | DoE eval. | DoE rounds | spread_gp hits | disc. BO:DoE | p |
|---|---|---|---|---|---|---|---|---|---|
| 0.12 | 24/25 | 32 | 6 | 20/25 | 48 | 3 | 25/25 | 5:1 | 0.2188 |
| **0.10** | **24/25** | **32** | **6** | **13/25** | **48** | **3** | **24/25** | **11:0** | **0.0010** |
| 0.08 | 22/25 | 74 | 16.5 | 13/25 | 96 | 6 | 23/25 | 10:1 | 0.0117 |
| 0.05 | 18/25 | 100 | 23 | 7/25 | 96 | 6 | 16/25 | 15:4 | 0.0192 |

**Noisy assay (σ = 0.25).** No contrast survives Holm.

| τ | BO hits | DoE hits | spread_gp hits | p |
|---|---|---|---|---|
| 0.15 | 21/25 | 23/25 | 25/25 | 0.6250 |
| 0.10 | 14/25 | 11/25 | 21/25 | 0.5488 |
| 0.08 | 10/25 | 6/25 | 17/25 | 0.3438 |

Q56 `path_argmax` vs `first_decline`: 4 of 26 cells flip. Primary ascent rule is `path_argmax` (Myers & Montgomery: take the best point along the path). See `results/q56-doe-ascent.log`.

---

## S9. TOST at SESOI = 0.02

Source: `results/tost-contrasts.json`. Both one-sided t-tests must reject to call **equivalent**. **Different** = bootstrap interval excludes 0. Otherwise **inconclusive**. Wilcoxon MDE is the smallest |mean| at 80% power given that cell’s observed SD (n = 25).

| Contrast | Mean | 95% interval | Verdict | MDE |
|---|---|---|---|---|
| In-region d=6 σ=0.25 (primary) | −0.0063 | [−0.0233, +0.0107] | inconclusive | 0.027 |
| In-region d=6 σ=0.10 | +0.0153 | [+0.0042, +0.0269] | different (GP ahead) | 0.018 |
| In-region d=8 σ=0.25 | +0.0091 | [−0.0057, +0.0243] | inconclusive | 0.024 |
| In-region d=8 σ=0.10 | +0.0001 | [−0.0118, +0.0115] | equivalent | 0.019 |
| Measured-argmax d=6 σ=0.10 | +0.0018 | [−0.0086, +0.0117] | equivalent | 0.016 |
| Measured-argmax d=8 σ=0.10 | −0.0024 | [−0.0095, +0.0053] | equivalent | 0.012 |
| Q58 posterior | −0.0227 | [−0.0438, −0.0022] | different | 0.033 |
| Q58 top-3 confirmation-alone | −0.0009 | [−0.0263, +0.0253] | inconclusive | 0.042 |
| Q60 top-3 average | — | — | not run | — |

---

## S9. Adversarial novelty checklist (working note)

Not for the submitted paper. Keep while editing.

| Claim | Assessment |
|---|---|
| BO versus DoE itself is novel | No |
| “BO optimizes while DoE maps a region” is novel | No (Rummukainen) |
| Matched-budget BO–DoE comparisons are novel | No (Rummukainen; Lapierre 2025; Ndahiro 2025) |
| Synthetic benchmarking of experimental optimizers is novel | No |
| Best-observation versus model-recommendation as a distinction is novel | No (noisy-EI literature) |
| Same-campaign winner reversal across terminal rules | Yes, potentially |
| Design × surrogate × locator decomposition | Yes, and probably the strongest contribution |
| Confirmation / replicate protocol as a terminal-rule sensitivity | Yes, and the most lab-relevant add-on |
| Strong enough now for a top general journal | No |
| Specialist methods / benchmark paper | Yes |
