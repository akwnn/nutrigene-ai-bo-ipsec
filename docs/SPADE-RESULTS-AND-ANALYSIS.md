# SPADE — the consolidated report

**Purpose.** This is the single consolidated report on the SPADE research programme: every
benchmark that shaped a final claim, why it was run, how it scored, and what it means —
plus the architecture-versus-mechanism reframing this document was originally created for.
It does not add new numbers and does not edit `docs/FINDINGS-SPADE.md` or
`docs/FINDINGS-SPADE-FINAL.md`, which remain the primary, chronological findings record;
every number here is read from a committed file or from the findings-record section that
already cites one. Where evidence is thin or a mechanism failed, that is stated in the text.

**What is excluded, deliberately.** The underlying project ran roughly 65 experiments,
diagnostics and re-analyses (`docs/TRIAGE.md`). Most are gate checks, exact-regeneration
proofs, or confirmatory re-runs that exist to make a headline trustworthy, not to say
anything new — e.g. Task 1 (500/500 campaigns regenerate bit-for-bit), the K1 replay gate,
determinism checks, or Version C's K-C4/K-C5/K-C8 (settled elsewhere, contribute no new
evidence). Those are not catalogued below. §0 lists only the tests that changed, established,
or bounded a claim that survives into the final SPADE story.

**Scope.** K6/K6b (design-space vs. regret), Version B (the original two-plate method), P6
(cross-family map), P7 (Murphy calibration), P8 (cross-family certificate), F3 (certificate
draw-count correction), Version C (regret parity, hard-stop, regime detector), the BO-
community performance profile, the prospective confirmatory study `spade-final-2026-08-23`
(KF-1–KF-10), and its follow-up `spade-kf3-followup-2026-08-24` (KF-3b/KF-3c/KF-3d).

These completed studies provide historical and development evidence for a newly frozen
48-evaluation joint SPADE protocol. Its implementation, deterministic release machinery,
development selector and unopened lockbox generators are complete. Its development outcomes,
selected policy and lockbox outcomes have not been generated; no result below is an outcome
of that new protocol.

---

## Background — the prior deliverable this study builds on

Before SPADE existed, this project ran a separate, already-complete study asking whether
Bayesian optimization beats classical response-surface methodology (DoE) at a matched well
budget. That study is not re-summarized here; it has its own full paper draft
(`docs/RESEARCH-SUMMARY.md` — title, abstract, methods, results) and its own audit trail
(`docs/TRIAGE.md`, which labels ~65 experiments CORE/DEFENCE/ARCHIVE/VOID; `docs/MAIN-LINE.md`;
`docs/CLAIMS.md`; `docs/RESULTS.md`). **SPADE exists because of what this study found**: scored
by simple regret (best single recipe), the terminal decision rule used to read out a method's
recommendation — best-observed value ("rule A") vs. the model's own posterior-mean argmax
("rule C"/"rule P") — was enough to *reverse* which method wins. That reversal, and the
question of what a *design-space* deliverable (a certified range, not a single recipe) would
show instead, is what motivated building and testing SPADE in the first place.

**The headline results** (`docs/MAIN-LINE.md` §1, its own curated summary; d=6, σ=0.25 unless
noted; n=25 paired landscapes):

| # | claim | number |
|---|---|---|
| 1 | Under rule A, classical DoE beats BO at a realistic budget | `doe − qlogei` = **−0.0595** [−0.0792, −0.0373], p<0.0001; **−0.0284** at d=8; ties at σ=0.10 |
| 2 | Under rule C (unconstrained, the primary DoE scoring), BO wins every cell | **+0.2931 / +0.3597 / +0.2710 / +0.3228** |
| 2b | Under rule C **constrained** (the sub-box actually explored), the same comparison is three nulls and one BO win | **−0.0063 / +0.0153 / +0.0091 / +0.0001** |
| 3 | The swing is the classical arm's *scoring*, not BO's | `doe` moves **+0.3205** rule A→C; BO moves **−0.0321** — roughly 10:1 |
| 3b | Mechanism: the fitted classical surface is a saddle, so its argmax must reach a boundary | **200/200** runs; ridge path exits the region at radius ≈0.27 vs. a corner radius of 0.50 |
| 3c | The GP's own recommendation beats its own best observation, all four cells | 15–21% better |
| 3d | The polynomial's recommendation is worse than its own best measurement — **only at the noisy assay** (σ=0.25); null at σ=0.10 | — |
| 4 | It is not the surrogate model, and not only the model | Surrogate effect (design fixed) −0.18 to −0.06; design effect (model fixed) +0.11 to +0.27, all p≤0.0008 |
| 5 | The reversal generalizes off the constructed oracle | Reproduces at all 8 Lévy/Rosenbrock cells |
| 6 | No defined "savings ratio" exists under the registered pairings | `doe` censored 64–100% at every rule-C target |
| 6b | What survives is *arrival*: BO reaches a target more often, cheaper in wells, slower in rounds | σ=0.10, target 0.10: BO 24/25 vs. DoE 13/25 arrivals, p=0.0010; BO 32 wells/6 rounds vs. DoE 48 wells/3 rounds |

**Four mechanisms eliminated as the cause of BO's rule-A loss** (`docs/MAIN-LINE.md` §2, "the
defence"): a misspecified GP kernel (additive kernel doubled held-out R², regret moved
0.0015, p=0.71), a bad lengthscale prior (a different prior is measurably worse), a failing
acquisition optimizer (0.118% failure rate, below a pre-registered 1% bar), and too small an
opening design (no detectable effect at the primary cell). **Surrogate accuracy is not the
binding constraint** — the strongest of the four, because a measurably better model
recommends no better.

**What this means for the SPADE report above.** §6's rule-A→rule-P narrative for `doe` (and
its caveats — the 3-well fragility, the contested constrained/unconstrained convention) is
the SPADE-specific continuation of claims 1–3 above, at a different scoring object. Nothing
in the backbone study evaluates a certified region, calibration, or Plate-2 targeting — those
are SPADE's own contribution, not a restatement of the backbone's findings. Read the backbone
as establishing *why the map/certificate question was worth asking at all*, not as evidence
about SPADE itself.

---

## 0. Test catalog — every benchmark that shaped a final claim

Chronological. "Verdict" is the one-line takeaway; "Detail" points to the section below that
explains it. Rows in *italics* are declarations about a metric (not a benchmark result) that
govern how later rows must be read.

| test | question | N | headline result | verdict | detail |
|---|---|---|---|---|---|
| **K6 / K6b** | Does the design-space (map) ranking of 8 campaign arms match the simple-regret ranking? | 9,600 + 1,600 rows, 8 arms | Map ranking agrees with regret ranking in 0 of 18 rankable cells; unscreened `lhs` beats screened `doe` on map by +0.105–0.221 AUC in 24/24 cells while `doe` still wins regret (+0.0312) | Map quality and regret are different objects — screening buys one and costs the other | §5 |
| *`alpha_star` declared* | *Does a model-internal "certainty" statistic track certificate quality?* | *K6b, P4b, P8, 9 arms* | *`doe` (worst-calibrated arm) ranks 1st on α\*; `sobol` (best-calibrated) ranks last* | *α\* is willingness to certify, not correctness — never cite it as calibration* | §4 |
| **Version B** (original 2-plate SPADE) | Does plate 2 close SPADE's regret gap to `qLogNEI`, and does its certificate hold against ground truth? | 250 campaigns, 5 arms | KILL-1 (gap-closing) survives Holm in 2/8 tests; KILL-2's "LSE beats random-8" reading was **retracted** (conflated criterion with 8 extra wells); certificate meets nominal in 45/50 scorable cells, `doe` fails at all 3 levels | Plate 2 exists and the certificate is real; the *targeting rule's* contribution was never isolated here — that gap is what KF-3 was built to close | §2, §3 |
| **P6** (cross-family map) | Does the screening-cost finding reproduce off hill and at d=8? | 96,000 rows, 8 arms × 4 families × 2 dims | `doe` worse at d=8 on 3/4 families; **all 8 arms beat `doe`** at d=8, `random` margin +0.0517 at p≈8e-113 | Screening's map cost strengthens and generalizes with dimension | §5 |
| **P7** (Murphy calibration) | Is SPADE's certificate calibrated, or just sharp? | 12,000 rows, 10 arms | SPADE ranks 1–3/9 on refinement, 5–7/9 on calibration; `sobol` wins calibration + Brier + containment; `doe` is 5–8× worse than every other arm | SPADE buys sharpness, not reliability; `sobol` is the strongest simple baseline on 4 validated metrics | §4 |
| **P8** (cross-family certificate) | Does the certificate itself (not just the map) hold off hill, at a corrected draw count? | 24,000 rows, 4,096 draws, 5 families | `hill`: 0/18 cells below nominal. `levy`/`rosenbrock`: 3/64 cells fail at γ=0.99, Holm-significant. `ackley`/`hartmann6`: decline to certify at all (0/24, 2/24) | Certificate claims must name family **and** γ — it is not a general property of SPADE | §3 |
| **F3** (draw-count sweep) | Was the original certificate "failure" (§14) real, or a 512-draw estimator artefact? | 3,000 rows, 250 campaigns | All 4 originally sub-nominal hill cells reach/exceed nominal by 1,024 draws (worst: 0.860→0.980); no cell fails at 4,096 draws with power | §14's hill-level claim withdrawn — it was the estimator, not SPADE, *at that cell*; P8 later showed the underlying phenomenon is real elsewhere | §3 |
| **Version C / K-C1–K-C8** | Does a posterior-mean terminal rule change SPADE's regret standing? Does a trust-region/detector improve anything? | 28,800 rows | K-C1 PASS (parity, not a win, vs. 4 arms); K-C2/K-C3 PASS structurally (re-score of already-gated columns); **K-C7 FIRED** (regime detector 0/50 on held-out families); K-C4/5/8 MOOT | Regret parity confirmed a second way; no working automatic scope detector exists | §3, §6 |
| **Performance profile** (BO convention) | What *kind* of "middling" is SPADE's regret? | same 28,800 rows, τ-sweep | SPADE wins outright 2% of problems, within 3× of best on 70%; `doe` matches the 2% but is within 3× on only 22% | SPADE is rarely best and rarely catastrophic; `doe` shares the rare win but carries a long, heavy tail | §6 |
| **`spade-final-2026-08-23`** (prospective confirmatory study, KF-1–KF-10) | Run fresh (not re-scored) campaigns and formally adjudicate 10 pre-registered kill conditions | 99,601 rows, 7 conditions | KF-3/4/5 **FAIL** (targeting does not earn its cost); KF-6/7/8 **PASS** (map/regret competitiveness); KF-1 PASS, KF-2 **FAIL** (certificate does not generalize cleanly); clean regeneration corrects KF-9 to **PASS** (0/23,600 above ceiling); KF-10 **FAIL** (18/64 empty-set downgrades) | The first prospective test of SPADE as a method narrows every broad claim; the complete release now passes 9/9 clean-checkout checks | §2 |
| **`spade-kf3-followup-2026-08-24`** (KF-3b/c/d) | Do two principled fixes (error-aware acquisition, diversity-aware batching) rescue KF-3's failure? | 400 campaigns, 2 new arms | Both FAIL at the registered 0.02 SESOI; both show a real but small effect only on the harder cross-family cell (hartmann6), not at the target condition; KF-3d MOOT | Not a fixable acquisition/clustering defect — most consistent with a budget/power limit at 8 wells in 6D | §2 |

---

## 1. Two separate claims, kept separate

SPADE is two things that are easy to conflate:

1. **Architecture** — a two-round protocol: Plate 1 (40–48 wells, space-filling) maps the
   whole box; Plate 2 (8 wells) reacts once to Plate 1's fitted uncertainty; a conservative
   excursion certificate is computed from the joint posterior.
2. **Mechanism** — the specific rule that chooses where Plate 2's 8 wells go (boundary
   SUR/straddle targeting, or the error-aware and diversity-aware variants tested below).

The registered kill programme (KF-3, KF-4, KF-5, and the KF-3 follow-up) tested the
**mechanism**, not the architecture, and it did not survive:

> We retain the two-round architecture as the object evaluated, not as a demonstrated
> improvement over one plate. In the registered target cell, the 40-well first plate had
> slightly lower map error than the full 48-well workflow, and the targeted second plate did
> not materially outperform random placement of the same eight wells. This document claims
> neither a marginal benefit of Plate 2 nor a benefit of its targeting rule.

Everything that follows is organized around that split.

---

## 1b. What was actually tested, versus what SPADE specifies

Everything in §2–§6 is about **the SPADE that was built**, not every stage in the founding
specifications. The three highest-priority specification gaps have now been tested under
registered gates, so they are decisions rather than open assumptions.

- **The controlled-prevalence threshold correction was retained.** Replacing a fixed
  fraction of peak height with a per-family prevalence quantile increased non-empty
  certification on Ackley from 0% to 13.3% overall (41.9% at the loosest target) and on
  Hartmann6 from 8.3% to 24.7% overall (81.2% at the loosest target) across 400 campaigns.
  It did not make the top-3% and top-1% regions answerable. The newer joint protocol applies
  the same principle to the γ-adjusted future-response reliability margin.
- **Strength-2 OA-LHS was tested and rejected.** The generator was implemented for the K2
  experiment, but exact strength 2 requires 49 rather than 48 wells. Across 125 matched
  Hartmann6 campaigns, its design-lottery SD was 0.1628 versus 0.1496 for plain LHS; the
  difference was +0.013 with a confidence interval spanning zero. The current 48-evaluation
  protocol therefore uses a scrambled-Sobol opening rather than adopting OA-LHS.
- **Replicate-pooled noise estimation was gated and rejected before implementation.** K0
  was ambiguous. K1 then granted the GP oracle knowledge of the true noise variance as an
  unattainable upper bound; mean regret improved by 0.00816 (95% CI +0.00202 to +0.01417,
  p=0.017), below the registered 0.01 build bar. Since a real replicate estimator cannot
  exceed that oracle ceiling, the 48-evaluation protocol retains learned noise and spends
  no wells on replication.
- **K3/K4 remain outside the evaluated method.** Confirmation-rule sensitivity is reported
  in the main BO-versus-RSM programme, but the older go/no-go ladder's confirm-and-average
  and Plate-1 deception-detector proposals were not added to SPADE.
- **Stage 0 (a day-0 covariate adjustment) was scoped out for a stated, legitimate reason** —
  not recoverable from the data this project has, would need a fresh real plate
  (`FINDINGS-SPADE.md`) — so SPADE as tested is missing one of its four specified stages, by
  a documented decision rather than an oversight.

None of this reverses any verdict below. It means every claim in §2–§8 concerns the tested
implementation. The threshold correction moves forward; OA-LHS and pooled-replicate noise
do not remain speculative rescue mechanisms because their registered gates did not support
building them into the 48-evaluation method.

---

## 2. Does Plate-2 targeting earn its complexity? KF-3, KF-3b, KF-3c, KF-3d

![Results across all seven registered conditions (C1–C4, S1–S3)](../results/figures/final-spade/final-spade-cross-condition.png)

![Causal controls: targeted vs. random vs. plate-1-only Plate 2](../results/figures/final-spade/final-spade-causal-controls.png)

![m>0 local-exploitation allocation trade-off](../results/figures/final-spade/final-spade-allocation-tradeoff.png)

**KF-3 (original, `results/final-spade-kill-ledger.json`, FINDINGS-SPADE-FINAL.md §12).**
`spade_cf_m0` (LSE/straddle-targeted second plate) versus `spade_random_plate2` (same
Plate-1 design, same 8-well budget, wells placed at random): symmetric-difference effect
**−0.00188, not significant**. **FAIL.** KF-4 (plate 2 vs. plate-1-only) also **FAIL** in the
harder direction (+0.01171, p=1.3e-04 — plate 2 measurably *worse*, not better, at this cell).
KF-5 (does spending some of plate 2 on local exploitation, `m>0`, lower regret) also **FAIL**
(−0.00278, not significant).

**KF-3b / KF-3c (`spade-kf3-followup-2026-08-24`, FINDINGS-SPADE-FINAL.md §19,
`results/kf3-followup-analysis.json`).** Two principled fixes were isolated into
independently-registered arms against the same `spade_random_plate2` control, each tested
against a pre-declared SESOI of 0.02:

- **`spade_cf_erroraware`** (KF-3b) — an SUR criterion targeting expected reduction in
  `vorobev_deviation` (a truth-free, model-internal analogue of the study's own error
  metric) directly, rather than the original straddle-score proxy. C2 (target condition):
  effect +0.00146, interval spans zero, p_holm=0.49 — **worse than random**. C3
  (hartmann6): effect **−0.00825**, CI [−0.0145, −0.0019] excludes zero, p_holm=0.0067 — a
  real, non-null improvement over random, but well short of the 0.02 bar. **FAIL.**
- **`spade_cf_diverse_batch`** (KF-3c) — the original straddle criterion with a
  repulsion-penalized batch selector replacing hard exclusion. C2: effect +0.00342, interval
  spans zero, p_holm=0.17 — **worse than random**, and its cross-fit containment cell
  downgrades from `spade_random_plate2`'s PASS at all three primary γ. C3: effect
  **−0.01722**, CI [−0.0233, −0.0112] excludes zero far more sharply, p_holm=2.2e-06 — the
  closest either mechanism comes to the bar, and still short of it. **FAIL.**
- **KF-3d** (gated combined arm): neither KF-3b nor KF-3c passed individually, so the
  combined mechanism was never built. **MOOT** — correctly, per its own registered gate.

**Reading the four results together.** Both replacement acquisition/batch rules show a real,
statistically non-null improvement over random placement — but only on the harder
cross-family cell (hartmann6), and only at roughly a third to two-thirds of the size needed
to matter practically. At the study's own target condition (hill, the cell the method was
designed for) both replacements underperform random. This is not consistent with "the
acquisition criterion was mis-specified" or "the batch selector clustered badly" — both were
tested directly and fixed, and the fix did not rescue the mechanism. It is consistent with
the third candidate explanation the KF-3 follow-up registered in advance: **eight wells in
six dimensions may simply be too few for any targeting criterion to separate itself from
random by a practically meaningful margin.** The break-even well count at which targeting
would start to earn its complexity was never measured (flagged, not tested, in the KF-3
follow-up spec §11 appendix).

**A caveat on how far this generalizes: whether a landscape can even distinguish these
variants is itself landscape-dependent.** On one registered ackley seed, all four two-plate
variants (`versionb`, `versionb_random`, `versionb_predictive`, and the plate-1-only control)
post **bit-identical regret** (0.7704) while their map metrics differ — on that family, regret
has zero power to separate targeted from random Plate 2 at all, and only the map can. On
hartmann6, `versionb`/`versionb_predictive` coincide while `versionb_random` separates; on
hill, KF-3/KF-3b/KF-3c is the only family where the comparison has ever actually been run.
**Every "targeting doesn't earn its cost" verdict in this document rests on hill alone** — a
null there could in principle be partly a property of that one landscape rather than a fully
general property of the mechanism, and nothing in the evidence base can currently distinguish
the two (`docs/OPEN-QUESTIONS.md`, Version-B cross-family probe).

**Reframing the role of Plate 2.** Plate 2's demonstrated value in this evidence base is
*that a second round exists*, not *which rule chose its wells*:

> `spade_random_plate2` is a control arm — it shares Plate 1's design and Plate 2's budget
> with SPADE and places the second-plate wells at random. It exists to test whether any
> Plate-2 targeting rule earns its complexity over that control. Under KF-3, KF-3b and
> KF-3c, no tested targeting rule did so at the registered 8-well budget.

**Independent, earlier evidence points the same way.** The K6/Version B technical report
(`docs/K6-TECHNICAL-REPORT.md` §5.11.3) decomposed where SPADE's earlier (re-scored) margin
over `qLogNEI` actually came from: **74–85% of the surviving-threshold margin is contributed
by Plate 1 being a space-filling (LHS) design, not by Plate 2.** Plate 2's own marginal
contribution, isolated, *cost* regret (+0.0276 vs. a plate-1-only arm, p=0.0166) in that
analysis — though that specific deficit is not cleanly attributable to Plate 2 as a *design*
choice either: a separate registered test (Step 0, `results/step0-oracle-best.json`) found
its own identification-vs-search decision rule **self-refuted** (measured 0.0795, exactly
between the two pre-committed branches), with Version B's own split running 40% search / 60%
identification against `doe` — so part of that +0.0276 may be a terminal-rule effect rather
than a pure design cost. That report also found `plate1_only` (no second plate at all)
matched full SPADE on certificate containment at every cell tested — **containment there was
a floor the design choice did not move.** Two independently-run analyses, at different times
and by different routes, now agree: Plate 2's targeting rule is not where SPADE's value comes
from. **One correction to what "the criterion" means in that analysis**: an earlier belief
that the LSE selector's exclusion radius was inert (too small to ever bind) was itself
retracted — the correctly-computed radius (0.1416–0.1495, not the earlier 0.105, from the
right lengthscale and the right reference population) **does bind, relocating a well in 22 of
50 live campaigns** (a mean of 0.56 of 8 wells per campaign). So `batch_lse` is not
equivalent to raw top-8-by-score; the arm under test throughout this section is
straddle-with-diversity, and that mechanism does operate — it simply hasn't been shown to
improve any deliverable (no committed arm isolates the *criterion* from the *extra wells* on
its own, which is exactly the gap KF-3/KF-3b/KF-3c was built to close).

---

## 3. Is the certificate valid? F3's correction

![Same-draw vs. cross-fit containment](../results/figures/final-spade/final-spade-samedraw-vs-crossfit.png)

![Cross-fit containment by cell](../results/figures/final-spade/final-spade-crossfit-containment.png)

![Threshold feasibility across τ_frac](../results/figures/final-spade/final-spade-threshold-feasibility.png)

The earlier registered kill (FINDINGS-SPADE.md §14) read as *"SPADE's certificate fails
below nominal containment at high assurance (γ ≥ 0.95)."* F3 (`results/f3-draw-sweep.json`,
250 campaigns / 3,000 rows, FINDINGS-SPADE.md §29) re-ran the same cells at 1,024, 2,048 and
4,096 posterior draws, against the 512 used to produce §14:

| cell (α=0.95) | 512 draws | 1,024 | 2,048 | 4,096 |
|---|---|---|---|---|
| γ=0.99, τ_f=0.60 | 0.860 | 0.980 | 0.980 | 0.980 |
| γ=0.99, τ_f=0.75 | 0.960 | 1.000 | 1.000 | 1.000 |
| γ=0.95, τ_f=0.60 | 0.940 | 1.000 | 1.000 | 1.000 |
| γ=0.99, τ_f=0.85 | 0.940 | 1.000 | 1.000 | 1.000 |
| γ=0.50 (control) | 1.000 | 1.000 | 1.000 | 1.000 |

**All four originally sub-nominal cells reach or exceed nominal containment by 1,024 draws
and stay there.** The worst cell improved from 0.860 to 0.980. A powered re-test at 4,096
draws (n=200 pairs, the sample size the project's own multiplicity work showed was needed)
found no cell significantly below nominal, even before Holm correction. **The registered
mechanism prediction — that the bias scaled with the number of scored candidates — was
tested directly and failed**: containment at `n_rho`=16 and `n_rho`=64 is identical at every
draw level. The bias is Monte Carlo noise in the containment estimate itself at low draw
counts, not the candidate scan.

**Corrected statement.** The blanket claim **"SPADE's certificate fails below nominal at high
assurance" is withdrawn.** With at least 1,024 posterior draws, the conservative excursion
certificate meets nominal containment at the original hill condition. 512 draws are
insufficient and produce an anti-conservative artefact. A small residual selection bias
(1.5–3.5 percentage points, concentrated at the two highest-γ cells, where Vorob'ev quantiles
tie) survives even at 4,096 draws and is corrected by cross-fitting (independently confirmed
by Version C's `conservative_estimate_split` on the same draws, FINDINGS-SPADE.md §29.3).

**Off hill, the certificate was tested properly — and it fails on two families (P8,
FINDINGS-SPADE.md §41).** This is not an absence of evidence: `results/p8-certificate-
families.json` scored 1,000 campaigns (5 families × 4 SPADE arms × 50 seeds, 24,000 rows, 0
gate failures) at the **already-corrected 4,096-draw count**, specifically to test whether
§14's original (withdrawn) claim was a hill-only estimator artefact or a real phenomenon
elsewhere. Per-cell, never pooled, across 64 scored `(family, γ, τ_frac)` cells:

| family | γ | τ_frac | contained | rate | Holm p |
|---|---|---|---|---|---|
| `levy` | 0.99 | 0.60 | 34/49 | **0.694** | **6.05e-07** |
| `rosenbrock` | 0.99 | 0.60 | 37/50 | **0.740** | **4.74e-05** |
| `levy` | 0.99 | 0.75 | 37/48 | **0.771** | **1.22e-03** |

**Historical fixed-fraction analysis.** All three failing cells are at γ=0.99; `hill` has zero cells below nominal (18 of 18 scored
cells clear 0.95, worst 0.980).** One correction to how to read "γ=0.99": it is *not*
straightforwardly the hardest corner. The absolute threshold `tau` is `tau_frac × tau_max(γ,
σ)`, and `tau_max` **decreases** as γ increases (a mechanical fact — confirmed independently
via the `tau_max` sequence across γ in `docs/COVERAGE-MATRIX.md` §B2, which strictly
decreases from 1.0000 at γ=0.50 toward 0.42–0.77 at γ=0.99 depending on σ), so a **higher** γ
implies a **lower** absolute bar and a **larger** true superlevel set — `docs/OVERNIGHT-LOG.md`
records the γ=0.99/τ_frac=0.60 cell as having true prevalence near the whole box, not a small
sliver. Failing to properly bound a set that covers most of the box is not "failing the
hardest test" in the intuitive sense; it is a specific, sharper finding about behavior at high
nominal assurance that should not be read as "SPADE only fails when pushed to an extreme
corner." The original §14 kill "fired on the right phenomenon, on the wrong family, for the
wrong reason" — it was measured on hill using an estimator too noisy to see anything, and
happened to fire; the real, Holm-significant under-coverage is on `levy` and `rosenbrock`,
and F3's 512-draw correction (above) does not touch it, because P8 already used 4,096 draws.
**Two more families (`ackley`, `hartmann6`) don't fail at all — they decline to answer**:
0/24 and 2/24 cells certify anything (mean empty rate 1.000 and 0.990). This decline has a
concrete mechanism, not just an observation: at the registered `tau_frac`-of-`mu_max` grid,
true superlevel-set prevalence at τ_frac=0.60 is **0.00000 on ackley and 0.00805 on
hartmann6** (vs. 0.736–0.956 on hill/levy/rosenbrock) — there is almost nothing there to
certify at that grid, on either family, largely independent of SPADE (`docs/COVERAGE-MATRIX.md`
§B1/B3). This same emptiness was **predicted before the data existed**: `docs/ODIN-VERDICT.md`
§7.2 measured spread-design neighbour density well below the level assumed by the certificate
math and predicted certified volume "may be identically zero" at high assurance — exactly
what P8 and F3 later found, which is evidence the emptiness is an understood mechanism, not an
unexplained artefact. **The families that certify most readily (`levy`, `rosenbrock`, 22/24
cells each) are the ones whose certificate is least trustworthy at high assurance; hill is
the only family that is both willing to certify and calibrated where it does.**

A later registered τ-quantile follow-up replaces this incommensurate scoring convention
going forward. It substantially improves Ackley and Hartmann6 answerability at the loosest
target but does not make the top-3% and top-1% regions answerable. P8 remains evidence about
the historical fixed-fraction estimand, not the active threshold policy of the joint protocol.

**Registered constraint arising from this: no containment claim may be stated
family-agnostically.** Any statement about SPADE's certificate must name the family and the
γ. "SPADE's certificate is valid" is not a defensible claim on its own; "SPADE's certificate
is valid on hill at γ up to 0.99, and under-covers on levy/rosenbrock at γ=0.99 specifically"
is. The prospective KF-2 test (FINDINGS-SPADE-FINAL.md §17.4) independently found the
certificate does not cleanly pass every confirmatory cell on hartmann6 either — a second,
independently-run line of evidence narrowing the claim to hill. **Dimension 8 remains
genuinely untested** (P8 is d=6, σ=0.25 only), and the two non-hill families have only 4
`tau_q` registration rows against hill's 100, a noisier statistic flagged before the data.

**A second, independent test against ground truth (K6-TECHNICAL-REPORT.md §5.11.7) — and it
also has a boundary.** Scored against the true excursion set rather than re-checked against
itself, SPADE's certified region met its nominal joint confidence in **45 of 50 scorable
`(arm, τ_frac, α)` cells**, and *failed* for the screened classical arm (`doe`) at every
level tested at τ_frac=0.60 (0/50, 12/50, 25/50 against nominal 0.50/0.80/0.95) — a second,
independent confirmation that the certificate mechanism does something real, and that
`doe`'s narrower design is where it breaks. **The boundary:** SPADE's own certified set is
**empty in 42–50 of 50 campaigns at τ_frac=0.85, and in 50 of 50 campaigns for every arm at
τ_frac=0.95** — there is no evidence at those higher thresholds, in either direction. The
correct statement is "the certificate is not shown miscalibrated on the cells that carry
evidence," never "the certificate is sound at τ_frac=0.95," where no evidence exists at all.

**An attempted automatic scope detector failed completely.** Because the certificate's
validated scope is narrow (§3 above), Version C tried to build a live detector that would
flag, from data alone, whether a new family/condition falls inside that scope (K-C7,
`docs/HANDOFF.md` §8.3, `docs/CLAIMS.md`). **It fired: 0 of 50 correct on both held-out
families.** The registered response was to ship without it. **Scope must be declared in
advance from the family/dimension/noise cells actually tested (as this document does), not
detected automatically at run time — no such detector currently exists or works.** The
failure was in fact structurally predictable rather than a surprise: one candidate detector
statistic was satisfied only by the argmax itself; another was identically zero at both fit
families' operating point; and the surviving statistic's fit set turned out to be
single-class (all three fit families on one side of the boundary, both held-out families on
the other) — a one-class novelty boundary cannot discriminate by construction, and a
follow-up analysis correctly predicted the fire from this in advance (`docs/OVERNIGHT-LOG.md`).

**A caveat on hill itself — the one family the certificate is validated on.** `hill` is a
synthetic construction built to resemble the project's one real dataset (Hall/Ogle ECM
biology), not fitted to it. `docs/oracle_defensibility.md` reports that hill's defining
structural assumptions are contradicted by that real data on the two properties that matter
most to what a certificate is certifying: hill assumes all 6 factors are biphasic with an
interior optimum, but only 1 of 4 measurably resolvable real proteins shows an interior peak
(p=0.05, low power); and hill's active-factor share (0.90, a 4.5–9× active-to-inert ratio —
the property giving the certificate's regime test something structured to detect) is
contradicted by the real main-effects analysis (~0.94:1, near flat, not 4.5:1). Separately,
the noise level used throughout every certificate/calibration number in this document
(σ=0.25) is **optimistic relative to the one real anchor by roughly 2.7×**: CV backed out of
the source box plots gives a median implied CV of 68.2% (IQR 55.8–86.1%) against σ_rel=0.25.
Neither point changes any verdict above, but both bear directly on how strongly "hill is the
validated family" should be read as evidence about a real assay, versus evidence about a
synthetic construction whose own structure is a design choice not yet reconciled with the
project's one real anchor.

**A scoping caveat on the ground-truth evidence above.** Version B's headline certificate
number (45 of 50 scorable cells) is a per-cell containment statistic and is not tied to a
single γ. But a *different* Version B result this document cites elsewhere — the KILL-1
gap-closing test (§0 catalog, "survives Holm in 2/8 tests") — is scored entirely against a
single γ=0.50 labelling, and that specific corner is independently known (§5's `lhs`-vs-`doe`
map result, and K6's own higher-γ rows) to be the one that favors spread designs most; `lhs`
actually *loses* to `qLogNEI` at γ≥0.70 in 15 of 24 K6 cells. Version B has never been scored
against those harder, higher-γ labellings. Separately, the unit of analysis for that 2/8
figure matters: under an alternate (arguably more conservative) per-instance unit it upgrades
to 4/8, but two of the three upgrades are on `alpha_star` — a statistic this document already
declares not to be a quality metric (§4) — so the upgrade is weaker than it looks
(`docs/K6-TECHNICAL-REPORT.md` §3.9.1, §5.11.3; `docs/OVERNIGHT-LOG.md`).

---

## 4. Is SPADE calibrated? P7's Murphy decomposition

![Murphy calibration/refinement decomposition](../results/figures/final-spade/final-spade-murphy.png)

`results/p7-murphy.json` (500 campaigns, 12,000 rows, all 10 arms; Brier decomposition
verified to hold exactly on all rows, worst residual 2.2e-16) splits Brier score into
**calibration** (reliability — lower is better) and **refinement** (resolution — higher is
better).

| arm | calibration | rank | refinement | rank | Brier |
|---|---|---|---|---|---|
| `doe` | 0.22959 | 9 (worst) | 0.00235 | 9 (worst) | 0.3367 |
| `qlogei` | 0.03366 | 4 | 0.00996 | 7 | 0.1331 |
| `qlognei` | 0.04425 | 8 | 0.01261 | 4 | 0.1411 |
| `lhs` | 0.03034 | 3 | 0.01175 | 5 | 0.1280 |
| **`sobol`** | **0.02893** | **1 (best)** | 0.01142 | 6 | **0.1269 (best)** |
| `random` | 0.03032 | 2 | 0.00900 | 8 | 0.1307 |
| `versionb` (SPADE) | 0.03593 | 6 | **0.01506** | **1 (best)** | 0.1303 |
| `versionb_random` | 0.03846 | 7 | 0.01288 | 3 | 0.1350 |
| `versionb_predictive` | 0.03532 | 5 | 0.01436 | 2 | 0.1304 |

**SPADE's three arms take refinement ranks 1, 2 and 3 of 9 — the sharpest regions in the
study — and calibration ranks 5, 6 and 7 of 9 — below-average reliability.** Where AUC (which
cannot see calibration) ranks `versionb` first, the decomposition that was promoted to
primary specifically to catch this puts it in the bottom half on the metric that speaks
directly to what a certificate claims.

**`sobol` is now best on four independently validated metrics**: calibration (0.02893),
Brier (0.1269), empirical containment (§23.3, FINDINGS-SPADE.md), and mean symmetric-
difference rank on three of four external families (§5 below) — using a plain scrambled
low-discrepancy sequence, one plate, no model, no adaptivity.

**`doe` is not merely worst on calibration — it is off the scale.** 0.22959 against 0.04425
for the next-worst arm: **5.2× worse than any other arm and 7.9× worse than the best
(`sobol`)**, and simultaneously last on refinement. A single arm accounts for nearly the
entire spread of the metric.

**Reframed statement.** SPADE's certificate is an empirically tested conservative excursion
statement at its validated (hill) setting (§3 above); its underlying probability surface is
sharp but only moderately calibrated relative to `sobol`. "SPADE is calibrated" is not a
defensible unqualified claim — "SPADE buys sharpness and does not buy reliability" is. The
registered oracle-noise ceiling in §1b showed a statistically non-zero but sub-threshold
0.00816 regret benefit, so replicate-pooled noise estimation was rejected for the fixed
48-evaluation protocol. That bounded result does not prove that calibration is immutable
under every alternative model or replication budget.

**A metric that must not be substituted for calibration: `alpha_star`.** An earlier
model-internal statistic (`alpha_star`, a functional of the fitted posterior only) was
investigated as a possible calibration proxy and **explicitly declared not to be one**
(FINDINGS-SPADE.md §28). The declaration rests on the extremes: `alpha_star` ranks `doe`
**first** — the arm whose calibration is 5.2× worse than any other and worst on refinement —
and ranks `sobol` **last** — the arm that is first on calibration, first on Brier, and first
on empirical containment. The demonstration works from both ends at once: `sobol`
simultaneously has the study's **best empirical containment** (0.959/1.000/1.000) and is
last-or-second-last on `alpha_star` at 3 of 4 thresholds — low `alpha_star` and near-perfect
containment are entirely consistent, which only makes sense if `alpha_star` is penalizing the
*safest* arm in the study, not the least correct one (`docs/K6-TECHNICAL-REPORT.md` §7.2).
`alpha_star` tracks how confidently a posterior asserts an excursion, not whether the
assertion is correct, and no ranking or claim in this document rests on it.

---

## 5. Does SPADE win the map? Cross-family results (K6, P6)

**Screening's cost is the cleanest result in the K-series** (FINDINGS-SPADE.md §19,
§26; `docs/SPADE-FOR-RESEARCHERS.md` §1.1). `lhs` and `doe` differ only in the 6→4 screen and
sub-box confinement: the unscreened arm wins the map by **+0.105 to +0.221 AUC, significant
in all 24 `(γ, τ_frac)` cells tested**, while `doe` still beats `lhs` on simple regret
(+0.0312, p=0.0028) — a complete ranking reversal from one structural difference. **This
original K6 number is in AUC, a metric the project's own later work found unreliable enough
to replace**: fitted-surface diagnostic `grid_r2` is negative for all 8 arms including `doe`
(−6.19), meaning AUC cannot see that the fitted surface is worse than a constant mean
everywhere, and a corrected error-volume metric (Amendment F2) ranks arms differently from
AUC in 24 of 24 cells (`docs/OVERNIGHT-LOG.md`). The screening-cost *finding* is not
undermined by this — it independently reproduces on the corrected, validated metric via the
cross-family table below (`doe` loses on symmetric-difference error, not AUC) — but the
specific "+0.105 to +0.221 AUC" figure itself should be read as the superseded-metric version
of a conclusion that holds up on the metric that replaced it, not cited as the primary
number on its own. **Screening's cost runs only one direction, not both**: on the same
family (hartmann6, no screen at all), removing the screen makes `doe`'s *regret* worse, not
better (+0.206 to +0.207, both p<1.4e-4, `results/q59-hartmann-no-screen.json` — a different
file from the map-rescore below, despite the shared "Q59" label) — screening is a genuine
adaptive-resource-allocation asset for regret specifically, while costing the map. Turning
the screen off does **not** rescue the classical pipeline on the map either: `doe_unscreened`
still loses to every spread arm by more than SESOI at p_holm < 1e-10
(`results/q59-map-rescore.json`). Screening explains only 19.8–28.4% of `doe`'s map deficit
(the corrected figure, after a since-fixed `sigma_add` bug had earlier and wrongly reported a
"consistent ~30%" three separate times); the response-surface model itself costs the rest.

**Cross-family mean rank on symmetric-difference error, both dimensions**
(`results/p6-families.json`, 96,000 rows, 0 gate failures; FINDINGS-SPADE.md §30):

| arm | h6 d=6 | h6 d=8 | levy d=6 | levy d=8 | rosen d=6 | rosen d=8 | ackley d=6 | ackley d=8 |
|---|---|---|---|---|---|---|---|---|
| `doe` | 7.59 | 7.96 | 8.50 | 7.67 | 8.22 | 8.40 | 4.32 | 4.44 |
| `qlogei` | 5.74 | 5.50 | 6.40 | 7.50 | 6.78 | 6.90 | 4.95 | 5.17 |
| `qlognei` | 6.56 | 6.35 | 7.40 | 6.67 | 7.56 | 6.90 | 6.16 | 5.78 |
| `lhs` | 4.59 | 4.54 | 3.50 | 4.25 | 3.11 | 3.00 | 4.95 | 5.56 |
| **`sobol`** | **3.44** | 5.35 | **1.60** | **3.25** | **2.89** | **2.30** | 4.47 | 5.28 |
| `random` | 4.96 | 2.85 | 2.20 | 3.08 | 4.22 | 3.90 | 6.05 | 4.17 |
| `versionb` (SPADE) | 4.33 | 3.73 | 4.90 | 5.00 | 3.56 | 4.60 | 4.05 | 4.67 |

(Lower rank = better; 8 arms per cell.)

**`sobol` beats `versionb` on 3 of 4 families at d=6** (hartmann6, levy, rosenbrock) and on
2 of 4 at d=8 (levy, rosenbrock decisively; hartmann6 and ackley favour SPADE). `doe` gets
**worse** at d=8 on three of four families, and at d=8 **every one of the eight arms —
including both BO arms — beats `doe` on the map**, the largest single effect in the study
being `random` vs `doe` at +0.0517, p_holm=7.9e-113.

**Reframed statement.** Across Hartmann6, Lévy, Rosenbrock and Ackley, SPADE arms are often
near the top on symmetric-difference map error, but **`sobol` is the strongest simple
baseline overall** — it most frequently posts the lowest error and the best mean rank. SPADE
is competitive and sharp (§4); it does not universally dominate `sobol` on map quality.
Ackley is the one family where `doe` does not collapse (its screen centre lands near ackley's
exact optimum by construction) and is excluded from every DoE contrast for that reason,
decided before the cross-family numbers existed.

**A caveat specific to SPADE's own numbers in this table.** SPADE's Plate-2 acquisition
targets a fixed design threshold, θ = 0.75·`mu_max`, unmodified per family — the same
fixed-fraction defect the certificate's `tau_q` machinery was registered specifically to
correct for *scoring*, but it is baked unmodified into SPADE's *design*. Measured coverage of
that fixed target against each family's actual grid: **ackley 0.0000** (0.75 exceeds ackley's
grid maximum — there is nothing to straddle), **hartmann6 0.0020** (near-empty), **levy
0.5417**, **rosenbrock 0.7825** (`docs/OPEN-QUESTIONS.md`). SPADE's Plate 2 is effectively
not targeting anything meaningful on ackley or hartmann6 in this table — a real and unresolved
mismatch, not retargeted by registered decision, and worth weighing before reading SPADE's
ackley/hartmann6 numbers above as representative of the method operating as intended.

**A caveat on the arm list itself.** `lhs` beats `qlogei` in 9 of 24 K6 cells with zero
losses, but *loses* to `qlognei` in 15 of 24 (10 Holm-significant) — the map-versus-regret
story is sensitive to *which* acquisition function represents "BO," a sensitivity this
project has already been burned by once (a withdrawn Q57 claim that held against `qlogei`
alone and reversed against `qlognei`). The cross-family table above inherits the same
multi-acquisition arm list, so this sensitivity travels with it.

**A methodological caveat on cross-family comparisons.** Comparing families at a fixed
*fraction* of each family's maximum (τ_frac) is not the same underlying question on every
family: at τ_frac=0.60 the true superlevel set covers 0.0% of the box on ackley, 0.8% on
hartmann6, 73.6% on hill, 85.7% on levy and 95.6% on rosenbrock (`docs/COVERAGE-MATRIX.md`
§B1) — ackley's map metrics are undefined (`nan`) at that grid entirely. The mean-rank table
above scores each family against its own arms consistently and is not itself a pooled
cross-family statistic, so it is not directly exposed to this problem, but any absolute
(non-rank) cross-family comparison at a shared τ_frac should be read with this
incommensurability in mind, and ackley numbers specifically should never be pooled with the
other three families.

---

## 6. Rounds versus regret: SPADE's operational case, and its regret parity

![Map quality vs. regret Pareto front](../results/figures/final-spade/final-spade-pareto.png)

**Rounds are not wells.** Under equal wells (48), the arms used very different numbers of
experimental rounds to get there: BO (`qlogei`/`qlognei`) used **10 adaptive rounds**; SPADE
used **2 rounds** (Plate 1, Plate 2); screened `doe` used **3 rounds** (screen, CCD, confirm);
`doe_unscreened` uses **1 round** (FINDINGS-SPADE-FINAL.md §17.4).

**Regret, under the posterior-mean terminal rule (rule P).** Under rule A (best-observed),
`doe` posts an apparent lead that is mostly identification, not search — measured directly at
**73% of `doe`'s rule-A lead over `qlogei` at the primary cell** (`results/q55-oracle-best.json`,
`results/q57-search-vs-id.json`, `docs/RESULTS.md`). That lead is also fragile in a way worth
stating plainly: a companion sensitivity test found confirming just **three wells out of 48
(6% of budget)** collapses `doe`'s entire rule-A advantage over BO from −0.0595 to a dead tie
of **−0.0009** (`results/q58-selection-sensitivity.json`, `docs/RESULTS.md` Q58) — "every
better selection rule cuts the advantage by more than half, and confirming three wells removes
it entirely." Switching to rule P reverses the remaining lead: `doe`'s identification gap goes
from +0.0361 (rule A) to **+0.1396 (rule P)** — it nearly quadruples, while every other arm's
gap falls. Against `lhs`, `doe` moves from +0.0114 *better* (rule A) to **0.1057 worse** (rule
P); against `sobol`, from +0.0369 better to **0.1339 worse** (FINDINGS-SPADE.md, rule-A/rule-P
table). **Under rule P, `doe` has no advantage to be above or below SESOI — it has a
deficit**, reversing the classical pipeline's apparent regret advantage from best to worst.
One structural caveat travels with this: `doe`'s round-count comparators throughout this
section are a *static* classical design (`doe_repeat`) that never relocates after its first
CCD — flagged in advance by this project as biased in BO's favor for exactly this kind of
comparison, and confirmed directly: a steepest-ascent-capable classical arm
(`doe_ascent`) that *is* allowed to relocate **erases BO's entire rule-A arrival advantage**
(`results/q56-doe-ascent.json`, `docs/RESULTS.md` Q56) — it still loses decisively under rule
C/P, so the qualitative reversal stands, but the round-count framing below leans on the more
favorable (to BO) static comparator. The backbone reversal this rule-P story is modeled on is
also itself convention-dependent to a degree worth naming: under DoE's *constrained*
(practice-consistent) scoring the analogous rule-A→rule-C flip collapses from "BO wins every
cell by +0.27–0.36" to **3 nulls and one small win**, and which of the two scorings counts as
primary was a contested, explicitly-flagged decision (`docs/CLAIMS.md` Tier 2, `Q41`) — not a
settled fact the way this section's brevity implies.

**SPADE's own regret parity (K-C1, Version C, σ=0.10; `docs/CLAIMS.md` "Version C" section) —
and what kind of measurement this actually is.** SPADE's two-plate arm posts rule-P regret
**0.0792**, moving from **10th of 12 arms under rule A to within SESOI of every arm except
`doe`**: **+0.0165** against `qlogei-addonly` (0.0627), **+0.0163** against `qlognei`,
**+0.0090** against `qlogei`, **+0.0028** against `lhs` — all paired on `(instance, seed)`,
n=50, all statistically real (Wilcoxon and bootstrap agree) and all **inside the 0.02 SESOI**.
This is reported as **detected but not material**: parity, not a win, and not a loss, against
four independent BO/spread comparators, not just one. **One fact that must travel with every
citation of this result: "Version C" has never been run as a method.** No `versionc` arm
exists; this is a **re-score of Version B's already-stored campaigns under Version C's rule**,
not a fresh prospective measurement (`docs/CLAIMS.md` "Version C," explicit) — every number in
this paragraph is a property of *Version B's wells*, scored a second way. The mechanistic
model that motivated running this re-score in the first place — a prediction that the deficit
was purely an identification artefact, based on a `regret_P ~ σ/√n_eff` relationship — turned
out to have **essentially no explanatory power on proper regression (R² ≈ 0.01–0.03)**; the
earlier apparent good fit was "a coincidence of two cancelling errors" (measured `n_eff` off
by ~10×, the model under-predicting by ~3×, which happen to cancel) (`docs/OPEN-QUESTIONS.md`,
`docs/CLAIMS.md`). The empirical parity numbers above still stand on their own (they rest on
the measured, gated `regret_P` values, not on that broken model), but the *reason* parity was
predicted in the first place is not sound, and the result is a re-score, not new evidence.
SPADE's own Hartmann6 regret is a clean loss, not parity: **+0.13 to +0.28 worse than
comparators, every p_holm ≤ 0.0016** (`docs/CLAIMS.md`, citing `Q53`-labelled Hartmann6
regret) — the parity story above is specific to hill, σ=0.10.

**A second, earlier regret-tie result at a different noise level.** At σ=0.25 (the K6
technical report's cell, `docs/K6-TECHNICAL-REPORT.md` §5.11.3), SPADE's two-plate arm
already tied `qLogNEI` on regret directly: **+0.0014, p=0.86**, at 2 rounds against
`qLogNEI`'s 10. Two independent analyses, at two different noise levels, by two different
methods (a direct regret contrast at σ=0.25; a rule-P re-score at σ=0.10), reach the same
conclusion: SPADE does not win regret, and it is not measurably behind either.

**Reframed operational statement.** Under equal wells, BO (`qlogei`/`qlognei`) is the
strongest arm on regret; SPADE is regret-competitive at parity (within SESOI) and clearly
beats `doe`, which collapses under the same terminal rule. Operationally, SPADE delivers a
usable operating region and a validated (hill-scope) certificate in 2 rounds, where matching
BO's regret required 10 adaptive rounds and matching the map required `sobol`'s 1 round at
lower sharpness. **Even a tie on regret is a meaningful round-count saving** — this reversal
of the classical pipeline under a terminal-rule change, and its robustness to that change,
is a real and reproducible finding independent of whether any single targeting mechanism
works (§2).

**What kind of "middling": the performance profile (FINDINGS-SPADE.md §42.2).** Mean regret
and mean rank both compress SPADE to "middling" without saying what kind. The performance
profile — the BO community's own convention, fraction of problems where an arm lands within
τ× the best arm on that problem — answers it (σ=0.10, rule P, `results/versionc-
conventions.json`):

| arm | within 1× (wins outright) | within 1.5× | within 2× | within 3× | within 10× |
|---|---|---|---|---|---|
| `qlogei-addonly` | 0.22 | 0.42 | 0.56 | 0.84 | 1.00 |
| `qlognei` | 0.22 | 0.42 | 0.56 | 0.80 | 1.00 |
| `versionb_random` | 0.14 | 0.34 | 0.56 | 0.74 | 0.98 |
| **`versionb` (SPADE)** | **0.02** | 0.24 | 0.42 | **0.70** | 0.98 |
| `doe` | 0.02 | 0.12 | 0.16 | 0.22 | **0.58** |

**SPADE wins outright on 2% of problems and is within 3× of the best on 70% of them.** `doe`
matches SPADE's 2% outright-win rate but is within 3× on only 22%, and fails to reach even
10× on 42% of problems. SPADE is **almost never the best arm and almost never catastrophic**;
`doe` shares its rare win rate but carries a long, heavy tail. For a lab picking one method
for one plate, the tail — not the mean — is what matters, and this is the metric that shows
it.

---

## 7. What we can now claim about SPADE

- **The historical SPADE architecture that was actually built and tested** — a two-round protocol with
  a plain-LHS Plate 1, a straddle-with-diversity-targeted Plate 2, and a conservative
  excursion certificate — matches or nears BO's regret in 2 rounds against BO's 10, and
  produces a certified operating region that `sobol`/`lhs`/plain BO do not (§6). This is
  a claim about that implementation. OA-LHS and pooled-replicate noise were subsequently
  rejected at their registered build gates; the new joint protocol instead uses a scrambled-
  Sobol opening and a learned-noise GP (§1b).
- SPADE's map is sharp: it wins refinement ranks 1–3 of 9 in the Murphy decomposition (§4)
  and is competitive with `sobol` on symmetric-difference map error across most cross-family
  conditions tested, within SESOI at the study's own target condition (§2, KF-6/KF-7 PASS) —
  though its own Plate-2 acquisition target is near-empty by construction on 2 of the 4
  external families tested (ackley, hartmann6; §5), so those two families' SPADE numbers
  should be read with that in mind.
- SPADE's conservative excursion certificate is empirically valid — meets nominal
  containment — at hill, d=6, σ=0.25, given at least 1,024 posterior draws and cross-fitting
  to remove a small residual selection bias (§3). This holds at every γ tested up to 0.99,
  and hill is the only one of five families tested (P8) that is both willing to certify most
  cells and calibrated wherever it does (§3) — with the caveat that hill's own defining
  structural assumptions are contradicted by the project's one real dataset, and its noise
  level is optimistic relative to that same real anchor by roughly 2.7× (§3), so this is
  validity on a synthetic construction, not yet reconciled with real assay behavior.
- SPADE's regret is at practical parity with the strongest rule-P BO arms at the target
  condition (within SESOI, against four independent comparators, not just one) — not a win
  but not a loss either (§6). The measurement is a re-score of already-stored Version-B
  campaigns, not a fresh prospective run, and the mechanistic model that originally predicted
  this parity turned out to have no real explanatory power (§6) — but the empirical parity
  numbers themselves are gated and stand independently of that broken model.
- Screening (used by `doe`) reliably costs a design-space deliverable while helping regret by
  a comparable margin on the one family tested without it (§5), and the classical pipeline's
  calibration is an outlier failure (5–8× worse than every other arm) independent of anything
  about SPADE (§4, §5).
- Against ground truth (not a re-check of the same statistic against itself), SPADE's
  certified region meets nominal joint confidence in 45 of 50 scorable cells, at the
  τ_fracs where evidence exists (§3) — though the exclusion mechanism behind Plate 2's
  targeting (`batch_lse`) is now known to actually operate (binds in 22 of 50 campaigns),
  correcting an earlier belief that it was inert (§2).
- SPADE's regret parity with BO reproduces at two different noise levels (σ=0.10 and
  σ=0.25) by two independent methods, against four separate comparator arms at σ=0.10 alone
  (§6) — though its Hartmann6 regret is a clean, sizeable loss, not parity (§6), so "parity"
  should be read as specific to hill.
- The empty-certificate-set behavior at high τ_frac and the near-total decline to certify on
  ackley/hartmann6 both have concrete, understood mechanisms — low true prevalence at the
  registered grid, and the same emptiness was correctly predicted before any SPADE data
  existed (§3) — rather than being unexplained artefacts.

## 8. What we cannot claim about SPADE

- That SPADE's boundary-targeted Plate-2 rule beats random placement of the same wells. It
  does not, at the registered 8-well budget, under either the original mechanism or two
  principled fixes tested directly (§2, KF-3/KF-3b/KF-3c FAIL).
- That SPADE is best calibrated, or "calibrated" without qualification. `sobol` is best on
  calibration, Brier and empirical containment; SPADE ranks 5th–7th of 9 on calibration (§4).
- That SPADE dominates `sobol` (or any spread design) on map quality universally. `sobol` is
  the strongest simple baseline on most cross-family cells tested (§5).
- That SPADE's certificate is valid outside hill, d=6, σ=0.25 — or valid "off hill" as a
  single verdict at all. It was tested off hill (P8, 24,000 rows, corrected 4,096-draw
  count) and **demonstrably fails**, Holm-significant, on `levy` and `rosenbrock` at γ=0.99;
  it does not pass cleanly on hartmann6 either (KF-2); and `ackley`/`hartmann6` decline to
  certify almost anything, so there is no evidence there in either direction. Dimension 8
  remains completely untested for the certificate (§3).
- That SPADE wins regret outright against BO. The best evidence is parity within SESOI, not
  a win (§6).
- That the KF-3 follow-up's negative result is explained by a fixable acquisition or
  batch-clustering defect. Both were tested and fixed; the fix did not rescue the mechanism.
  The most consistent remaining explanation — insufficient budget for any targeting rule to
  separate from random at 8 wells in 6D — was flagged, not tested (§2).
- That Plate 2, specifically, is where SPADE's demonstrated certificate or regret value
  comes from. 74–85% of the earlier margin over `qLogNEI` traced to Plate 1 alone; a
  plate-1-only arm matched full SPADE on containment at every cell tested (§2).
- That a model can automatically detect whether the certificate's validated scope applies to
  a new condition. A live regime detector was built and tested and failed completely (0/50
  correct on held-out families); scope must be stated in advance, not inferred (§3).
- That `alpha_star` (a model-internal statistic sometimes discussed alongside calibration)
  evidences certificate quality. It has been declared not to — it ranks the worst-calibrated
  arm (`doe`) first and the best-calibrated arm (`sobol`) last (§4).
- Any certificate claim at τ_frac ≥ 0.85. SPADE's own certified set is empty in the large
  majority to all of the campaigns tested at those thresholds — there is no evidence in
  either direction (§3).
- That every component in the founding SPADE specification was tested as one workflow.
  OA-LHS and pooled-replicate noise were evaluated at registered build gates and rejected;
  the reported campaigns use the retained implementation (§1b).
- That KF-3's "targeting doesn't earn its cost" verdict is a fully general property of the
  mechanism. It rests on hill alone; on at least one other family (ackley), regret cannot
  even distinguish targeted from random Plate 2, so the null result there is untestable by
  the same method, and the generality of the hill finding is unverified (§2).
- That "Version C" or "K-C1" is an independent measurement of anything. It is a re-score of
  Version B's already-stored campaigns under new scoring arithmetic, not a new experiment,
  and the theoretical model that motivated running it has since been shown to have no real
  explanatory power (§6).
- That hill's true prevalence and active-factor structure are representative of the real
  assay it is modeled on. The one real dataset available shows only 1 of 4 measurable
  proteins with an interior optimum against hill's assumption of 6 of 6, and a roughly flat
  active/inert ratio against hill's assumed 4.5–9×; the σ=0.25 used throughout every
  certificate/calibration number is also optimistic relative to that same real dataset by
  roughly 2.7× (§3).
- That SPADE's calibration or Plate-2 shortfalls are universal architecture properties.
  Oracle-noise and OA-LHS follow-ups failed their build gates, but each was tested on a
  bounded benchmark and does not exclude every alternative design or noise model (§1b, §4).
- That DoE's rule-A "advantage" this document's rule-P story reverses is itself a robust,
  hard-to-erase effect. It collapses to a dead tie with 3 confirmation wells out of 48, and
  the round-count comparator used throughout §6 is a non-relocating classical design flagged
  in advance as favorable to BO — a relocating classical arm erases the same advantage
  without any terminal-rule change at all (§6).

## 9. Evidence index

Compiled from a direct reading of `docs/FINDINGS-SPADE.md`, `docs/FINDINGS-SPADE-FINAL.md`,
`docs/K6-TECHNICAL-REPORT.md`, `docs/COVERAGE-MATRIX.md`, `docs/CLAIMS.md`, `docs/MAIN-LINE.md`,
`docs/HANDOFF.md`, `docs/TRIAGE.md`, plus a full read of every other project doc
(`docs/OPEN-QUESTIONS.md` — 9,105 lines, `docs/RESULTS.md`, `docs/OVERNIGHT-LOG.md`,
`docs/ODIN-VERDICT.md`, `docs/SPADE-SPEC.md`, `docs/oracle_defensibility.md`,
`docs/pdf_crosscheck.md`, `docs/WHAT-WE-FOUND.md`, `docs/ESTIMAND-EVALUATION.md`,
`docs/PROJECT-DOSSIER.md`, `docs/RESULTS-PERSON-A.md`, `docs/INFORMATION-MATRIX.md`,
`docs/PROMPTS-NEXT.md`, `docs/METHODS.md`, `docs/SUPPLEMENT.md`, `docs/source_verification.md`,
`docs/WEEK-RECAP-2026-08-13.md`, `docs/ODIN-SPEC.md`, and `docs/archive/`), and spot-verified
against the underlying result JSON (`status`, `gate_failures`, `verdicts_withheld` fields) —
not run, no scripts executed.

| section here | evidence |
|---|---|
| §1b retained τ-quantile correction | `docs/SPADE-TAU-QUANTILE-SPEC.md`; `results/tau-quantile-followup.json` |
| §1b OA-LHS / K2 rejected | `docs/SPADE-CALIBRATION-FIX-SPEC.md`; `results/k2-design-lottery.json` |
| §1b pooled-noise / K0–K1 rejected | `docs/SPADE-CALIBRATION-FIX-SPEC.md`; `results/k0-calibration-gate.json`; `results/k1-noise-ceiling.json` |
| §1b K3/K4 not added | `docs/ODIN-VERDICT.md` §2, §3 |
| §2 KF-3 | `results/final-spade-kill-ledger.json`; FINDINGS-SPADE-FINAL.md §12 |
| §2 KF-3b/c/d | `results/kf3-followup-analysis.json`; FINDINGS-SPADE-FINAL.md §19; `docs/SPADE-KF3-FOLLOWUP-SPEC.md` |
| §2 landscape-dependent distinguishability (ackley bit-identical regret) | `docs/OPEN-QUESTIONS.md` |
| §2 plate-1-vs-plate-2 attribution | `docs/K6-TECHNICAL-REPORT.md` §5.11.3, §5.11.5 |
| §2 Step 0 self-refuting identification/search rule | `results/step0-oracle-best.json`; `docs/K6-TECHNICAL-REPORT.md` §5.12 |
| §2 exclusion-radius R1 retraction (binds 22/50) | `docs/K6-TECHNICAL-REPORT.md` §6.15, §2.11, §5.11.4 |
| §3 F3 | `results/f3-draw-sweep.json`; FINDINGS-SPADE.md §29 |
| §3 P8 (cross-family certificate, fails on levy/rosenbrock) | `results/p8-certificate-families.json`; FINDINGS-SPADE.md §41 |
| §3 γ/tau_max mechanics | `docs/COVERAGE-MATRIX.md` §B2; `docs/OVERNIGHT-LOG.md` |
| §3 ackley/hartmann6 emptiness mechanism + prior prediction | `docs/COVERAGE-MATRIX.md` §B1/B3; `docs/ODIN-VERDICT.md` §7.2 |
| §3 KF-2 (cross-family certificate) | FINDINGS-SPADE-FINAL.md §17.4 |
| §3 ground-truth containment (Version B) | `docs/K6-TECHNICAL-REPORT.md` §5.11.7 |
| §3 Version B single-γ-cell scoping (KILL-1) | `docs/K6-TECHNICAL-REPORT.md` §3.9.1, §5.11.3; `docs/OVERNIGHT-LOG.md` |
| §3 regime-detector failure (K-C7) + structural predictability | `docs/CLAIMS.md` "Version C"; `docs/HANDOFF.md` §8.3, §C; `docs/OVERNIGHT-LOG.md` |
| §3 hill oracle validity vs. real data; σ=0.25 optimism | `docs/oracle_defensibility.md`; `docs/pdf_crosscheck.md` §4 |
| §4 P7 | `results/p7-murphy.json`; FINDINGS-SPADE.md §27 |
| §4 `alpha_star` declaration (incl. sobol two-sided demo) | FINDINGS-SPADE.md §28; `docs/K6-TECHNICAL-REPORT.md` §7.1, §7.2 |
| §5 K6 screening cost + AUC→error-volume supersession | `results/k6-designspace.json`, `results/q59-map-rescore.json`; FINDINGS-SPADE.md §19, §26; `docs/SPADE-FOR-RESEARCHERS.md` §1.1; `docs/OVERNIGHT-LOG.md` (Amendment F2) |
| §5 screening helps regret (Q59 no-screen, distinct file from map-rescore) | `results/q59-hartmann-no-screen.json`; `docs/RESULTS.md` Q59 |
| §5 P6 cross-family | `results/p6-families.json`; FINDINGS-SPADE.md §30 |
| §5 τ_frac incommensurability | `docs/COVERAGE-MATRIX.md` §B1 |
| §5 SPADE's own θ=0.75·mu_max cross-family coverage mismatch | `docs/OPEN-QUESTIONS.md` |
| §5 acquisition-function sensitivity (lhs vs qlogei/qlognei) | `docs/K6-TECHNICAL-REPORT.md` §5.4, §6.2 |
| §6 rule A/P reversal | `results/fix1-terminal-rule.json`; FINDINGS-SPADE.md (rule-A/rule-P table) |
| §6 73% identification / Q58 fragility (3-well confirmation) | `results/q55-oracle-best.json`, `results/q57-search-vs-id.json`, `results/q58-selection-sensitivity.json`; `docs/RESULTS.md` |
| §6 doe_ascent erases rule-A arrival advantage | `results/q56-doe-ascent.json`; `docs/RESULTS.md` Q56 |
| §6 rule-A→rule-C contested convention (backbone) | `docs/CLAIMS.md` Tier 2 |
| §6 K-C1 regret parity (σ=0.10) | `results/versionc-kills-s010.json`; FINDINGS-SPADE.md (K-C1 row); `docs/MAIN-LINE.md`; `docs/CLAIMS.md` "Version C" |
| §6 "Version C never run as a method" + σ/√n_eff model refuted | `docs/CLAIMS.md` "Version C"; `docs/OPEN-QUESTIONS.md` |
| §6 SPADE's Hartmann6 regret loss | `docs/CLAIMS.md` "Version C" (citing `Q53`) |
| §6 Version B regret tie (σ=0.25) | `docs/K6-TECHNICAL-REPORT.md` §5.11.3 |
| §6 performance profile | `results/versionc-conventions.json`; FINDINGS-SPADE.md §42.2 |
