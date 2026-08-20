# Revision program: make the paper defensible

**Status (2026-08-17).** Workstreams 1–7 are closed (Q54–Q59). Sequential RSM exists (`src/boec/sequential_rsm.py`). The living paper is `docs/RESEARCH-SUMMARY.md`; long tables live in `docs/SUPPLEMENT.md`.

**Registered next, not run:** Q60 (`top_k_average`) and Q61 (q=1). BO replay of Q58/E2 failed the 1e-12 gate (acquisition-optimizer retry; DoE still matches). Do not block the paper on those runs. TOST is in `results/tost-contrasts.json`. Spec: `docs/superpowers/specs/2026-08-17-review-response-design.md`. Plan: `docs/superpowers/plans/2026-08-17-q60-q61-tost.md`. Do not re-run closed workstreams from the checklist below.

**Q62 (done, 2026-08-20):** TuRBO-1 qLogNEI. Locked JSON `results/q62-turbo.json` and
`results/q62-turbo-n200.json`. Figure 4. Do not overwrite E2/Q56. Q63 (OCBA) is Paper 2.

Hand this file to the agent that will do the next month of work. Do not mix campaigns in one run. Do not invent a winner.

**The paper to publish is not** “BO and DoE address different estimands” or “which acronym wins.”

**The paper to publish is:** matched-budget BO-versus-RSM rankings are not a property of the algorithm names. They depend on campaign geometry + surrogate + terminal decision + noise + allowed extrapolation + unit of cost. We quantify each piece under identical budgets and identical latent landscapes.

Locked science that must not regress:

- Mathematical Hill oracle. Not wet-lab validation. Hall/Ogle is **structural inspiration** (factor count, 6→4 screen), not a fitted endothelial surface.
- Primary cell: d = 6, σ = 0.25, n = 25 landscapes, matched budget 48.
- Do not cite −0.0708, voided E2 runs 1–2, retracted savings crossover at 0.15, or Ackley as a DoE-versus-BO cell.
- JSON wins over RESULTS.md.
- Measured-value argmax = `reported_best_curve` (pick by noisy y, score noiseless f). Hidden tested-best = `curve_true`. Never mix labels.
- Unconstrained quadratic argmax is a **naïve diagnostic**, not “the DoE recommendation.” Constrained/ridge is the principal classical readout. Sequential RSM with relocation is implemented (`doe_ascent`, `path_argmax`, commit `fd842ac`).

What is **not** novel (do not claim it):

- BO versus DoE as an idea.
- “BO optimizes, DoE maps a region” (Rummukainen already states this).
- Matched-budget BO–DoE comparisons (Rummukainen; Lapierre 2025; Ndahiro 2025).
- Synthetic optimizer benchmarks (Olympus, Liang et al., etc.).
- That best observation ≠ model recommendation (noisy-EI / incumbent literature).

What **is** the contribution to defend:

- Same-campaign **winner reversal** when only the terminal decision changes.
- **Design × surrogate × locator** factorial (Q34 / Q45 / Q35): most applied papers compare bundled workflows.
- Most of the giant unconstrained “BO win” is an **invalid extrapolative readout of a saddle**, and it largely disappears under in-region RSM.
- Wells ≠ rounds as a laboratory cost unit, with numbers.

**Map of big changes.** Writing vs experiments. Do not start new campaigns until Workstream 0 in the paper is consistent (it now is, in `docs/RESEARCH-SUMMARY.md`).

### Writing (no new runs) — applied in RESEARCH-SUMMARY.md

| Change | Why |
|---|---|
| Drop “estimands” from title; preferred title is terminal-decision dependence | Statistician: one target E[1−f(δ(D_N))], several locators δ |
| Abstract: both Narayanan and Rummukainen can be correct; do not call savings “misleading” | Denominator and terminal decision differ |
| Related work: Lapierre 2025, Ndahiro 2025, Gisperg 2025; Rummukainen is not the only executed comparison | Reviewer will supply these if we omit them |
| Rename researcher pick → measured-value argmax / single-readout selection | Labs may replicate, confirm, or use posterior mean |
| Hall/Ogle = structurally inspired; σ = higher/lower-noise, not “realistic” | Oracle is constructed; box-plot CV ≠ additive Gaussian σ |
| Unconstrained quadratic = naïve diagnostic; in-region/ridge = principal classical readout | 0.27–0.36 is saddle extrapolation, not fair RSM |
| Flag qLogEI as awkward primary; promote stored qLogNEI beside it | Rummukainen used noisy EI |
| Hartmann stated as screening-workflow confound | 6→4 drops two active factors |
| Cost: P(T ≤ N) first; no N=200 efficiency headline; one-shot GP secondary | Censoring; doe_repeat ≠ sequential RSM; one LHS draw |
| Inferential hierarchy; do not call p=0.052 a win | Effect-switch is the story |

### Experiments still required (Workstreams 1–7 below)

| Priority | Test | Closes which loophole | Output |
|---|---|---|---|
| 1 make-or-break | BO + DoE R_search, R_id, R_measured, R_model, R_ridge | Cannot tell if DoE searched better or was easier to identify | `qXX-search-vs-id.json` |
| 2 essential for “classical DoE” in the title | Sequential RSM: screen → CCD → ridge/ascent → recenter | N=200 currently vs repeated non-relocating CCD | `qXX-sequential-rsm.json` |
| 3 co-primary | qLogNEI on every new campaign; posterior-mean final pick | Headline DoE win dismissible as wrong acquisition | reuse qlognei + new runs |
| 4 if one-shot GP stays in discussion | Hill spread_gp ≥5 (prefer 10–20) independent LHS draws | One draw is not a conclusion | new JSON, do not overwrite Q52 |
| 5 mechanistic | Hartmann screening-workflow vs optimizer-only (all 6 active) | Current BO win bundles 6→4 information loss | new Q42 variant |
| 6 optional | Replicate / top-k confirm / posterior-mean at visited points | Single-readout selection is not all of lab practice | small sensitivity JSON |
| 7 analysis | P(T ≤ n) curves from stored Q52; add sequential_rsm after WS2 | Medians-among-hits change the denominator by method | update Figure 2 |

**Do not add** dozens of algorithms. These seven close the rejection path.

Venue after the runs: ML:ST, Digital Discovery, or Chemometrics and Intelligent Laboratory Systems. Not Nature Communications without wet-lab or a much broader benchmark.

---

## Workstream 0 — writing only (no new runs)

**Status: largely applied** in `docs/RESEARCH-SUMMARY.md` (new title/abstract, related-work framing, naming, novelty table, open-loophole list, decision-guide retone). Remaining writing-only items:

- Read PDFs of Lapierre, Ndahiro, Narayanan (SI for the predicted-DoE count), Gisperg, and any 2026 bioprocess BO guide before submission; tighten citations to page-level facts.
- Optional: add Olympus / Liang / noisy-EI incumbent papers to the reference list once PDFs are checked.
- Keep CLAIMS.md / MAIN-LINE.md from being copied into the paper; they still carry old “scoring convention / literature split” language.

Checklist that should stay true:

1. Title without “estimands.” Preferred: *Matched-budget benchmarking of Bayesian optimization and response-surface methodology depends on the terminal decision rule.*
2. Abstract hook: reported advantages may depend as much on how the terminal formulation is selected as on where either method samples. Both Narayanan and Rummukainen can be correct because denominators and terminal decisions differ. Do not write that prior savings claims are “misleading.”
3. Related work must include, with PDFs checked before submission:
   - Rummukainen et al. 2024, *Heliyon* e24484: 15-run Box–Behnken vs 5+10 BO; noisy EI then posterior-mean final pick; no reduction in experiment count; RSM maps, BO concentrates.
   - Narayanan et al. 2025, *Nat. Commun.* 16:6055: ~2.5–3× vs **predicted** standard DoE count (SI calculation); 10–30× in the nine-factor transfer case. Resource-planning question, not equal-budget executed DoE.
   - Lapierre et al. 2025, *J. Chem. Technol. Biotechnol.* 100:1571–1583, doi:10.1002/jctb.7860: 48-condition screen then CCD/RSM (factors reduced) vs batch BO (all factors kept); *S. pasteurii*; BO medium higher biomass. Not our factorial, but in-domain and cannot be omitted.
   - Ndahiro et al. 2025, *iScience*, doi:10.1016/j.isci.2025.112944: CHO media, BO with thermodynamic constraints, higher titers than classical DoE **with the same number of experiments**.
   - Gisperg et al. 2025 review; any 2026 BO-in-bioprocess guide used only after the PDF is read.
   - Olympus / Liang-style BO benchmarks: existence of synthetic/experimental-surface benchmarks is not our novelty.
   - Noisy EI incumbent literature (best observation vs posterior mean vs sampled posterior mean). We did not invent that distinction; we show it reverses a BO-versus-RSM ranking.
4. Rename throughout: **measured-value argmax** or **single-readout selection**, not “what a researcher would carry forward.” Real labs may replicate, confirm, or use a posterior mean (Rummukainen’s final pick; Narayanan models process noise).
5. Stop “estimand” in the title and as the discovery. Use **terminal decision rule**. Underlying target is always E[1 − f(δ(D_N))].
6. Stop “calibrated to Hall/Ogle.” Use **structurally inspired by** / **dimensionally anchored to**. Stop “realistic measurement noise.” Use **higher-noise** (σ = 0.25) and **lower-noise** (σ = 0.10) benchmark conditions unless assay σ is estimated from replicated raw observations on the same scale.
7. Label unconstrained quadratic as **naïve unconstrained quadratic recommendation**. Principal classical recommendation in the text is **in-region / ridge**. The 0.27–0.36 gap is a failure-mode experiment, not the fair DoE-versus-BO headline.
8. qLogEI remains in the current tables. Flag in the paper that it is an awkward primary noisy comparator; Rummukainen used noisy EI. Existing E2 already has qLogNEI: at the primary cell it is 0.1532 vs qLogEI 0.1553 (null). DoE still leads both under measured-value argmax at σ = 0.25. That is **supporting**, not a substitute for making qLogNEI co-primary in the write-up after Workstream 3.
9. Hartmann6: state that the current pipeline **discards two active factors by construction**. Do not present it as a clean optimizer comparison until Workstream 5.
10. Cost: lead with **hit probability P(T ≤ N)**. Medians among hits are secondary and not comparable across rows with different denominators. No fold-savings ratio.
11. Inferential hierarchy: primary confirmatory = DoE vs named BO at d = 6, σ = 0.25, measured-value argmax and in-region recommendation. Secondary = unconstrained diagnostic, design×surrogate factorial, arrival. Exploratory = controls, Q42, one-shot GP (one draw). Effect size and interval first; p second. Do not call p = 0.052 “small BO.”
12. One-shot GP is a **promising secondary finding**, not a conclusion, until Workstream 4.

---

## Workstream 1 — search vs identification, both arms (make-or-break)

**Why.** Headline measured-value-argmax DoE advantage at σ = 0.25 cannot tell search from identification.

```
R_search = 1 - max_i f(x_i)                         # hidden tested-best
R_id     = f(x_best true tested) - f(x_argmax y)     # ≥ 0
R_measured_argmax = R_search + R_id
R_model  = 1 - f(x_model)
R_ridge  = 1 - f(x_constrained)
```

DoE already has R_search (0.0597 / 0.0544 / 0.0575 / 0.0500) and R_measured_argmax (0.0958 / 0.0892 / 0.0963 / 0.0948). **BO R_search is not in e2-grid.json.**

**Do this.** `scripts/rescore_oracle_best.py` on the D20 pattern.

- DoE: replay `run_doe_arm` at stored seeds. Gate rule-C columns to 1e-12. Reproduce both DoE columns above or stop.
- BO: replay qLogEI (and, once Workstream 3 exists, qLogNEI) at the same instance ids/seeds. Gate stored measured-argmax against 0.1553 / 0.0874 / 0.1247 / 0.0972. Then write `bo_search`. Shard; this is the expensive arm.
- Store per row: R_search, R_measured_argmax, hit/miss of noisy argmax, identification gap.
- Output `results/qXX-search-vs-id.json` with Wilcoxon + bootstrap on:
  - DoE_search − BO_search
  - DoE_measured − BO_measured (must match published)
  - identification gap by arm and σ

**Language after the file exists.**

- “DoE searched better locations” only if search contrast is negative and the interval excludes 0.
- “DoE was easier to identify under noise” only if identification gaps differ and search is null.
- “Measured-value argmax favours DoE” is the current headline and stays a statement about that decision rule only.

**Done when** Figure 1 has four bar groups for both arms: search, measured-value argmax, naïve unconstrained quadratic, in-region recommendation.

---

## Workstream 2 — sequential RSM with steepest ascent / ridge relocation (fair long-run DoE)

**Why.** N = 200 currently pits sequential BO against **repeated non-relocating 48-well CCDs**. That is not “is BO more efficient than sequential classical RSM?” NIST / Box–Wilson RSM is screen → (ascent) → CCD → canonical/ridge → recenter. Do not make BO-versus-DoE cost at 200 a main claim until this arm exists.

**Implement** `sequential_rsm` / `doe_ascent`. Do not replace `run_doe_arm`. Keep `doe_repeat` labelled “repeated CCD, no relocation.”

Pipeline on [0,1]^d:

1. Same 20-run screen, retain 4, Hall/Ogle 6→4 cut (unless running the no-screen Hartmann variant in Workstream 5).
2. Face-centred CCD (27). Classify stationary point (`boec.rsm`).
3. Interior maximum: confirm, optional small CCD if budget remains.
4. Saddle or exterior: ridge / steepest-ascent path, pre-registered step size, stop when measured y stops improving or box wall. Recenter. New CCD. Repeat until remaining budget < one CCD.
5. Every recommendation a lab would run is evaluated.

Budget: wells and rounds registered **before** the run (suggestion: screen = 1 round, each CCD = 1 round, each ascent batch = 1 round, confirmation = 1 round). Cap 200. d = 6, σ ∈ {0.10, 0.25}, n = 25, same instance ids as Q52. Partial CCD is not the method.

Score at every legal stop: R_search, R_measured_argmax, naïve unconstrained, in-region.

Comparators: qLogEI (and qLogNEI after WS3), doe_repeat, spread_gp.

Arrival: emphasize **P(hit by N)** at τ ∈ {0.15, 0.12, 0.10, 0.08, 0.05}. Medians among hits secondary. Holm on BO vs sequential_rsm arrival tests. No invented fold-savings.

Tests first: relocates on exterior peak; saddle ≠ interior max; leftover wells do not buy a broken CCD; measured-argmax ≠ search on a noisy fixture; rounds formula matches the registered rule.

Output `results/qXX-sequential-rsm.json` with Q52-style provenance. Do not overwrite `q52-budget-to-target.json`. Update Figure 2.

**Done when** the paper can say whether any well-count advantage of BO at σ = 0.10, τ = 0.10 survives a DoE arm that is allowed to walk. Winner not pre-written.

---

## Workstream 3 — qLogNEI as co-primary noisy BO

**Why.** Observations are y = f(x) + ε. Headline BO is qLogEI. Noisy-EI exists because the incumbent is itself uncertain. Rummukainen used noisy EI then posterior-mean final pick. A reviewer can dismiss a DoE win as “wrong acquisition.”

**Do this.**

- Make qLogNEI co-primary with qLogEI for every **new** campaign (WS1 replay, WS2 cost curves, WS4, WS5).
- For already-stored E2: report qLogNEI next to qLogEI in the main measured-argmax table, not only in the control supplement. Existing numbers: primary cell 0.1532 vs 0.1553, p = 0.71; DoE 0.0958 still leads both. d = 8, σ = 0.10: qLogNEI 0.0849 vs qLogEI 0.0972, p = 0.027 uncorrected.
- Final BO recommendation column should include **posterior-mean argmax** (Rummukainen’s last step), not only unconstrained EI peak, as a sensitivity locator.
- Qualitative conclusions that must be checked to survive both acquisitions: (i) measured-argmax DoE lead at σ = 0.25, N = 48; (ii) unconstrained-quadratic disaster; (iii) in-region near-tie; (iv) winner reversal on the same campaigns.

**Done when** no headline sentence depends on qLogEI alone.

---

## Workstream 4 — one-shot GP, many design draws

**Why.** Hill spread_gp used **one** Latin hypercube. Q53 used five draws on external families. Do not pool. Do not recommend one-shot GP to labs on one draw.

**Do this.** Re-run Hill spread_gp at **≥ 5** (prefer 10–20) independent LHS draws, d = 6, σ ∈ {0.10, 0.25}, same checkpoints/targets as Q52. Treat design draw as a random factor; pair by landscape. Report hit probability vs 10-round qLogEI and qLogNEI.

Until then the paper may report the current match at τ = 0.12/0.10/0.08 and the miss at 0.05 as **exploratory**.

---

## Workstream 5 — Hartmann6 with and without 6→4 screening

**Why.** Current Hartmann comparison forces the DoE pipeline to drop two active factors. That confounds screening failure with optimizer failure.

**Do this.** Two protocols, same four cells, same locators:

- **Screening workflow** (current): retain 4, as published.
- **Optimizer-only:** both arms see all six active coordinates (no 6→4 cut; at d = 8 still two inert axes).

**Done when** the paper can say whether BO’s Hartmann win is screening, quadratic misspecification, sequential sampling, or multimodality.

---

## Workstream 6 — optional sensitivity on “measured-value argmax”

Single noisy readout is one operational rule, not all of laboratory practice.

If time: duplicate each well (or confirm top-k) and score argmax of mean y; and/or pick by posterior mean at visited points. Small n is fine. Purpose: show the σ = 0.25 DoE lead is not an artefact of taking the luckiest single spike.

Not a substitute for WS1.

---

## Workstream 7 — cost presentation (mostly analysis of stored Q52)

From `q52-budget-to-target.json` / `q52-rounds-to-arrival.json`:

- Plot **P(T ≤ n)** vs n for each arm, each τ, each σ. Failure to hit is in the denominator.
- Keep medians-among-hits in supplement only.
- After WS2, add sequential_rsm to those curves.
- Do not headline BO cost-efficiency at 200 until WS2 exists.

---

## Suggested run order

1. Workstream 0 (writing) — largely done in RESEARCH-SUMMARY.md; PDF-check citations before submission.
2. Workstream 1 (BO search column) — unblocks the noisy-assay mechanism.
3. Workstream 3 (qLogNEI co-primary on new runs; table promotion of stored qLogNEI).
4. Workstream 2 (sequential RSM) — unblocks the cost claim.
5. Workstream 7 (replot cost with P(hit)).
6. Workstream 4 (spread_gp draws) if one-shot GP stays in the discussion.
7. Workstream 5 (Hartmann no-screen).
8. Workstream 6 if a reviewer attacks single-readout selection.

Do not add dozens of algorithms. These seven close the rejection loopholes.

---

## Files the implementer will touch

| Workstream | Code | Output |
|---|---|---|
| 1 | `scripts/rescore_oracle_best.py`, `src/boec/diagnostics.py` (already has both locators) | `results/qXX-search-vs-id.json` |
| 2 | `src/boec/doe_ascent.py` or similar, tests, `scripts/run_qXX_sequential_rsm.py` | `results/qXX-sequential-rsm.json` |
| 3 | reuse `qlognei` arm in runners; promote in paper tables | existing `e2-grid.json` plus new campaigns |
| 4 | `scripts/run_q52_budget_to_target.py` spread_gp multi-draw | new JSON, do not overwrite Q52 |
| 5 | `scripts/run_q42_families.py` variant without 6→4 | new JSON |
| 7 | `scripts/make_cost_curve_page.py` | update Figure 2 |
| 0 | `docs/RESEARCH-SUMMARY.md` | this file stays the prompt source of truth |

---

## Paper checklist before any submission

- [ ] Title and abstract match the evaluation-protocol claim, not “different estimands.”
- [ ] Lapierre 2025 and Ndahiro 2025 are in related work (PDFs read).
- [ ] Narayanan cited as predicted-DoE-count, both findings allowed to be correct.
- [ ] Unconstrained quadratic is diagnostic; in-region RSM is the classical recommendation.
- [ ] qLogNEI co-primary; every qualitative headline survives it.
- [ ] BO R_search exists; search vs identification separated.
- [ ] No N = 200 efficiency claim without sequential RSM.
- [ ] One-shot GP not a conclusion unless multi-draw.
- [ ] Hartmann screening confound stated or split.
- [ ] “Calibrated / realistic noise / researcher would carry forward / estimand” purged or defined.
- [ ] Cost led by P(T ≤ N).
- [ ] Forbidden numbers still absent.
