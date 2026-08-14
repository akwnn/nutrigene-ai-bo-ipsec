# Research summary — what we did, how, what it means, what is left

**Repo:** `nutrigene-ai-bo-ipsec`
**Dates:** 7–14 August 2026
**HEAD:** `b338c5c` (14 Aug 2026, 15:39)
**Commits this week:** 146 (Person A / josephyung6686: 86; Person B / Alana Kwan: 60)
**This file:** the readable record for a paper and for a later session. It restates the work in plain language. The numbered artifacts live in `docs/RESULTS.md`, `docs/MAIN-LINE.md`, and `results/`. Where those files disagree, this file says which number to use.

---

## Direct answers

### Is the model based on endothelial cell data, or on math?

**Math, with a thin published-cell anchor. We did not train on endothelial measurements. We did not optimize live cells.**

| Layer | What it actually is | Used for the main BO-vs-DoE claims? |
|---|---|---|
| **Phase 1 (almost everything)** | Fake landscapes. A Hill-function formula with a known best point. Parameters are drawn at random from ranges we chose. | **Yes.** E1–E4 and most Q-studies. |
| **Phase 2** | Numbers read off two box-plot figures in Hall, Lin & Ogle 2025 (*Sci Rep*). 48 coating conditions. CD31/DAPI immunofluorescence. | **Only three scripts:** the Hall/Ogle replay, the extrapolation check, and a power calculation. Replay was **null**. |
| **Phase 3** | Real in-house iPSC→endothelial flow files under `data/lab/`. | **No.** CD31 percentages are unsigned. The optimizer is coded to refuse them. A feasibility check says this 12-point coating design cannot carry a Phase 3 figure. |

Accurate one-liner for a paper:

> This is a synthetic benchmark. The search-space labels, the 6→4 screening structure, and some ranges come from a published iPSC→endothelial ECM study. The ground-truth function is a Hill landscape we built, not a fit to cell data. No wet-lab Bayesian optimization result exists yet.

Do **not** write: “we optimized endothelial differentiation,” “the model is trained on endothelial data,” or “validated on cells.”

The title must not promise cells. `CLAIMS.md` L12 already says this belongs in the abstract.

---

## 1. What the project is

The field disagrees about whether Bayesian optimization (BO) beats classical design of experiments (DoE) for media and coating optimization.

- One camp reports 3–30× fewer experiments than DoE.
- A 2024 matched-budget study (Rummukainen et al.) found no reduction. Their winner was already in the first batch.

We built a head-to-head test: the same budget, the same landscapes, both methods, scored two different ways.

**The finding is not “BO wins” or “DoE wins.” The finding is that the winner changes when you change how you score the classical method — and that change is larger than anything about BO.**

---

## 2. What we built this week

Two people, eight days (nothing on 9 Aug).

| Day | What landed |
|---|---|
| **7 Aug** | Shared Python package `src/boec/`. First E4 run: the GP mechanism works; the registered headline is null. |
| **8 Aug** | Oracle dispute settled. E4 v2: any GP advantage sits in a regime we cannot defend. Giving the GP a “biology-shaped” prior made extrapolation **worse**. |
| **10 Aug** | Sequential DoE arm. E1 passes. First two E2 runs thrown out (scoring bug, pairing bug). **E2 completes: at the pre-registered primary cell, DoE beats BO.** DoE also wins at 8 dimensions. |
| **11 Aug** | The E2 winner is a scoring-rule effect, not a method effect. Hall/Ogle figures digitized and replayed: **null**. Polynomial on real data runs to whatever wall you give it; the GP does not. Factorial, cost, multiplicity work starts. `CLAIMS.md` drafted. |
| **12 Aug** | Factorial holds. Result reproduces on Levy and Rosenbrock. Design effect favours BO once the model is held fixed. Multi-fidelity and design-variance work. |
| **13 Aug** | Multi-fidelity: all three predictions wrong. Design-averaged BO still beats lucky LHS. Hartmann6: BO wins all cells. Identification-floor check refutes itself. Lab files dropped in. Budget-to-target experiment registered. |
| **14 Aug** | Budget-to-target: **no savings curve**. Lab pipeline reads 305 files. DoE “best observed” bug found and fixed (D20). Claims triaged. One-shot spread+GP tested on standard functions: **ties on smooth landscapes, loses on deceptive ones.** Phase 3 coating feasibility: **no.** |

**Inventory now:** 26 `src/boec/` modules plus a lab subpackage; 51 scripts; 40 test files / 688 tests; 159 result files.

There is **no manuscript**. Only these docs. Paper writing has not started.

---

## 3. Methods (plain)

### 3.1 The test

We generate 25 fake “landscapes” (functions from recipe → quality). Quality has a known best value of 1.0. Each method gets **48 measurements**. We report how far the method’s chosen recipe is from the true best. That gap is **regret**. Lower is better.

**Primary setting (locked before E2 finished):**

- 6 factors (standing in for 6 ECM proteins)
- measurement noise σ = 0.25 (noisy assay)
- 25 landscapes × 2 random seeds
- budget 48

We also ran 8 factors and a quieter assay (σ = 0.10).

### 3.2 The fake biology (Phase 1 oracle)

Each factor is a Hill curve: response goes up, peaks, then goes down. We add a weighted sum across factors and a mild interaction. The best point is planted. Observations are:

`measured = true_value × (1 + noise) + extra_noise`

Nothing in this formula is fitted to cell numbers. Peak locations, Hill slopes, and which 4 of 6 factors matter are drawn from ranges we chose. Hall/Ogle informed the *shape of the story* (biphasic, 6→4 screen, noisy assay), not the parameter values.

Known mismatches with the published figures:

- The oracle assumes an interior peak on every factor. A fit to the digitized stage-2 medians resolves an interior peak on **1 of 4** proteins.
- The oracle is ~93% additive. Real ECM work talks about stronger interactions.
- Peak positions in the oracle sit in [0.25, 0.55]. The one interior peak we can see in the paper (laminin-411) sits at 0.685 — outside that range.
- Primary noise 0.25 is **lower** than the CV implied by the paper’s box plots (~68%). We called 0.25 conservative.

Factor names in the code are `x0…x5`, not Collagen I / fibronectin. Protein names are labels we put on afterwards.

### 3.3 The seven methods (E2)

| Name | What it does | Rounds at budget 48 |
|---|---|---|
| **qLogEI** | Bayesian optimization (primary BO method). Opening design, then batches of 4. | 10 |
| **qLogNEI** | Second BO method. | 10 |
| **random** | 48 random points. | 1 |
| **Sobol** | Quasi-random space-filling. | 1 |
| **LHS** | Latin hypercube. | 1 |
| **coord** | Coordinate descent from a random start. Never paired with the others. | — |
| **doe** | Copy of the published pipeline: ~20-run screen, keep 4 factors, 27-run face-centred CCD, fit a quadratic, measure the predicted optimum once. | 3 |

### 3.4 How we score a winner (this is the whole paper)

Every score uses the **true noiseless value** of a chosen recipe. The rules differ only in *which recipe is chosen*.

| Rule | Chosen recipe | Plain meaning |
|---|---|---|
| **A** | The recipe that looked best when measured | “What would you send to the next experiment if you trust the data you already ran?” |
| **C unconstrained** | The recipe the *model* likes best, anywhere in the box | “What does the fitted surface tell you to try next, even outside the region you explored?” |
| **C constrained** | The recipe the model likes best *inside the region you actually explored* | Classical practice when the stationary point is outside the design. |

Rule B mixed the two (DoE on its model, BO on its data). We computed it, then dropped it.

**Locked decision (Q41):** when we talk about rule C as the alternative, the primary version is **unconstrained**. Constrained is always reported next to it. Both belong in every table.

### 3.5 Hall/Ogle data (Phase 2)

Hall, Lin & Ogle, *Scientific Reports* 15:24479 (2025). Six ECM proteins, two-stage DoE, CD31 area / DAPI area at day 10, normalized to fibronectin-only.

The paper never prints per-condition numbers. We digitized the box plots. Two independent readings agree. Optical reading error is small compared with the assay’s own scatter. **48 conditions, 47 usable.** That is not enough to train a GP and declare a winner. We used it as a lookup table and as a geometry check.

### 3.6 In-house lab data (Phase 3)

305 files: 52 FCS, 121 images, protocols. Pipeline reads them in ~31 seconds. CD31 channel identified as B525-A. Official response column `y` is **empty on purpose**. Human gating has not been signed. Do not paste candidate percentages into the optimizer.

---

## 4. Results that belong in a paper

These are the CORE results. Use these numbers. Do not use the VOID list in §6.

### 4.1 Under “best recipe we actually ran” (rule A), DoE wins at a realistic budget

Primary cell (6 factors, σ = 0.25, n = 25):

| Method | Regret |
|---|---|
| DoE | **0.0958** |
| qLogEI | **0.1553** |
| Difference (DoE − BO) | **−0.0595** [−0.0792, −0.0373], p < 0.0001 |

DoE is better. The same direction holds at 8 factors (difference **−0.0284**). At the quiet assay (σ = 0.10) the two methods **tie**.

File: `results/e2-grid.json`, `results/e2-doe-d8.json`.

**What it means:** if you score both methods the way a lab actually reports a winner — the best well you already measured — the published-style classical pipeline beats this BO setup at 48 measurements and a noisy assay.

### 4.2 Under “recipe the model recommends, anywhere” (rule C unconstrained), BO wins every cell

| Cell | BO minus DoE (positive = BO better) |
|---|---|
| d=6, σ=0.25 | **+0.2931** |
| d=6, σ=0.10 | **+0.3597** |
| d=8, σ=0.25 | **+0.2710** |
| d=8, σ=0.10 | **+0.3228** |

File: `results/q34-factorial.json`.

**What it means:** if you score each method at the point its own model would tell you to try next, and you let that point sit outside the explored region, BO looks much better.

### 4.3 If you keep the recommendation inside the explored region, the BO win mostly disappears

Constrained rule C, same four cells: **−0.0063 / +0.0153 / +0.0091 / +0.0001**. Three nulls, one small BO win.

File: `results/q35-constrained-rsm.json`.

**What it means:** “BO wins under rule C” is only true if the classical model is allowed to recommend outside the region it was fit on. Classical textbooks already warn against that (ridge analysis). We measured what happens if you ignore the warning.

### 4.4 Almost all of the swing comes from how DoE is scored, not from BO

Primary cell:

| Arm | Rule A | Rule C unconstrained | Change |
|---|---|---|---|
| DoE | 0.0958 | 0.4163 | **+0.3205** (much worse) |
| BO | 0.1553 | 0.1232 | **−0.0321** (slightly better) |

About **90%** of the move from “DoE wins” to “BO wins” is the classical arm changing score. BO barely moves.

**Mechanism:** the fitted quadratic is a **saddle in 200/200 runs**. A saddle has no interior peak, so the unconstrained “optimum” is forced onto a boundary. That boundary point is a bad recipe. The GP’s recommended point is 15–21% *better* than the best point it already measured.

After a scoring bug fix (D20): “polynomial recommends worse than its own data” holds at σ = 0.25 (**+0.0211**) and is **null at σ = 0.10**. Write that as a noisy-assay fact, not a universal one.

### 4.5 It is not only the model, and not only the points

We swapped designs and models on the same data, then refit both polynomials on the same four factors so the comparison is fair (Q34, Q45).

- Holding the design fixed and swapping the model: GP still beats the polynomial (**−0.1803 to −0.0559**).
- Holding the model fixed and swapping the design: the adaptive (clustered) design beats the CCD (**+0.1129 to +0.2669**), all p ≤ 0.0008.

The CCD is actually *better geometry* inside its own region (~4.4× more D-efficient). It still recommends a worse global recipe. The failure is not “we gave DoE a bad design.”

### 4.6 The scoring-rule finding is not an artefact of our Hill oracle

Same comparison on standard test functions (Q42):

- **Levy and Rosenbrock:** the reversal reproduces at all 8 cells. Scoring-rule swing +0.22 to +0.48.
- **Hartmann6:** BO wins under **every** rule. This landscape has several local peaks; the DoE screen is at chance.
- **Ackley:** do not use for the DoE comparison. Its optimum is the centre of the box, and a CCD always measures the centre.

**What it means:** “how you score the classical arm changes the winner” is a general fact on saddle-shaped problems. “Which method wins” is landscape-dependent. Do not claim the Hill result is universal for the *winner*. Do claim it for the *scoring effect*.

### 4.7 We cannot claim BO needs fewer experiments

Q52 asked: at what budget does each method first reach a target quality?

Registered analysis: **no savings curve**. Under rule C, DoE never arrives at the targets (censored 64–100%). Under rule A the tight targets are also mostly censored.

One unconditioned result survives:

> At the quiet assay (σ = 0.10) and a modest target (regret 0.10), BO gets there on **24 of 25** landscapes; DoE on **13 of 25**. Discordant pairs 11 to 0. Exact p = 0.0010. This survives a Holm correction over 10 tests.
> At the realistic assay (σ = 0.25) there is **no arrival difference at any target**.

A first-pass headline (“savings ratio inverts, crossover at 0.15”) was **retracted**. Do not quote it.

Caveat: our DoE arm repeats a fixed 20+27+1 pipeline. Real sequential RSM would add steepest ascent. This comparison is biased toward BO. Stated before the run, not after.

File: `results/q52-budget-to-target.json`.

### 4.8 One-shot “spread + GP” matches 10-round BO on smooth problems, not on deceptive ones

Q53: take a space-filling design, fit one GP, pick the GP’s best guess. One round. Compare to qLogEI’s 10 rounds, same number of measurements.

Registered prediction held **8 of 8**: this one-shot method **loses to qLogEI on Hartmann6** at every cell, both scoring rules.

| Landscape type | Result |
|---|---|
| Levy, Rosenbrock (smooth) | **Tie** |
| Hartmann6, Ackley (deceptive / needle) | **Loses**, and the gap is large |

**What it means:** extra BO rounds help when the surface can fool a single fit. They do not buy much sample efficiency on the smooth Hill-like surfaces this project was built around. Do not put this in the abstract until you decide it is a main claim — it is in `RESULTS.md` and not yet in `CLAIMS.md`.

Limit: the Hill “tie” used one design draw; Q53 used five. Re-run Hill at five draws before combining those sentences.

---

## 5. Defence results (reviewer objections we already closed)

These are not the headline. They stop the obvious attacks.

| Objection | Answer |
|---|---|
| Your GP was the wrong shape for a nearly additive landscape | Additive kernel doubled held-out R² (0.375 → 0.744). Regret moved **0.0015, p = 0.71**. A better model did not pick a better recipe. |
| Your lengthscale prior crippled BO | The “better” prior was worse at separating active from inert factors. |
| The acquisition optimizer was silently failing | **4 failures in 3400** (0.118%). Threshold was 1%, set before we knew the rate. |
| Opening design too small | No effect at the primary cell. |
| Lucky landscapes | Sign-flip permutation: 0 of 10,000 as extreme. |
| LHS just got lucky | It did. Best of 60 draws. After we give BO the same design averaging, BO still wins that comparison (25/25 instances, p = 6.0×10⁻⁸). |
| “LHS also beats BO” | Dies under Holm correction. Do not claim it. |
| Extrapolation is a fake-oracle artefact | On the digitized Hall/Ogle table, the polynomial’s recommended point runs to any wall you set. The GP’s point does not move. |
| Replay on real data found nothing, so BO is useless | The instrument cannot resolve an effect that small. Minimum detectable effect is 0.68 (on a 0–1-ish scale) at 80% power. |
| You counted wells; a lab pays plate rounds | DoE: 3 rounds. qLogEI: 10 rounds. Same 48 wells. |
| Scoring is a technicality | At σ = 0.25, 61% of leftover regret is a recipe already run that the method failed to identify as best. Identification, not search, is the bottleneck at realistic noise. |
| Does BO work at all? | Yes, on standard functions vs random. That check also found the scoring bug that voided E2 run 1. |
| Is the GP’s uncertainty honest? | No. Coverage is below 95% in every cell. Worst 0.764. State this as a limitation. |

---

## 6. What not to cite

These were real runs. They are not current.

| Item | Why it is dead |
|---|---|
| E2 run 1 | Scored the best *true* value among visited points, not the point the method would report. |
| E2 run 2 | Opening batches were not paired. |
| Q29 numbers, including −0.0708 | Person B’s clone had a different E2 grid under a gitignored filename. Canonical primary-cell difference is **−0.0595**. |
| Q36 | Replaced by Q42 (more families, all cells). |
| “Savings inverts, crossover 0.15” | Broke the registered analysis gates. Retracted. |
| “Polynomial always worse than its data; GP always better” | After D20, the polynomial half is null at σ = 0.10. |
| Ackley as a DoE-vs-BO cell | Optimum is the box centre. |
| E4 as a Paper 1 headline | Different question (can the GP flag extrapolation?). Pooled figure and registered cell **disagree in sign**. No script regenerates the v2 markdown. Archive it. |
| Q47 multi-fidelity as Paper 1 | 6,600 runs; all three predictions wrong; forward-looking. Archive. |

---

## 7. What is not done

### Paper

- No manuscript. `CLAIMS.md` is still marked “draft, nothing settled.”
- `RESULTS.md` has no standalone Q50 section (the run exists: `results/q50-paired.json`).
- `OPEN-QUESTIONS.md` still says Q52/Q53 are pending. They are finished. Trust `RESULTS.md` and git, not that file’s tail.
- Sentence 2 in the triage (“BO wins in every cell”) must name **unconstrained** rule C in the same sentence.
- Sentence 3 must say the polynomial-worse-than-data half is for the **noisy** assay.
- Prior art: lead with **Rummukainen 2024**. Do not cite Nguyen 2017 as a contrary result (it is about a different choice inside EI). Do not cite Picheny for rule A vs C until someone actually reads it.

### Decisions that need a human, not more compute

1. **T15:** Person A has not formally accepted the d=8 DoE split. That row is otherwise ready.
2. **Q23:** confirm that coordinate descent stays unpaired (limitation L3).
3. **Alan:** claim cut of `CLAIMS.md`; session-coordination so two people do not register the same Q-number eleven minutes apart again.

### Optional experiments (not required for the three-sentence result)

| ID | What | Why you might still run it |
|---|---|---|
| U5 | Wider BO batches (q = 12, 16, 24) at budget 48 | A lab audience will ask whether fewer, fatter plates close the 10-vs-3 round gap. |
| U2 | Noise sweep σ = 0.05 to 0.50 | We only have two noise levels. |
| Hill spread_gp, 5 design draws | Makes the Q53 “three-family tie” include Hill honestly. | |
| U3 | Add constrained rule-C contrasts to the Holm family | ~10 minutes. The +0.0153 cell has raw p = 0.0088. |
| Stage-4 confirmation for BO | Right now rule A taxes DoE (it spends 1 of 48 on a confirm) and rule C does not tax BO the same way. | |

### Lab (Phase 3) — blocked on people, not code

- Sign CD31 gates for 12 Campaign A coating tubes.
- Until `y` is filled and status is `gated`, `load_lab_evaluator` raises.
- Even after sign-off, the 12-point one-factor coating scan is a bad BO test: almost no headroom, n = 1, two factors. Feasibility verdict is already **no** for a Phase 3 figure on this design.
- Protein-cap constraints are not built.

---

## 8. Data problems you should know about

The record is not clean. This is the list, not a surprise later.

1. **Two clones, one gitignored filename.** Early E2 grids differed between machines. The −0.0708 figure is not ours. Use committed `e2-grid.json`.
2. **D20.** For a while DoE “best observed” was secretly the *oracle-best* visited point. Rule A DoE regret at the primary cell moved **0.0597 → 0.0958**. Rule C was untouched. `results/q35-constrained-rsm.json` and `q42-families.json` still contain old columns on disk. Analysis must read `results/d20-rescore.json`.
3. **Most `results/*.json` are gitignored.** Only named exceptions are in the repo. Some large grids (`e3-grid.json`, `pf1-grid.json`) may exist only on disk.
4. **Adaptive BO is not bit-identical across machines.** Person A’s qLogEI mean 0.1553 vs Person B’s 0.1641. Intervals are machine-specific. The paired *difference* vs DoE is the quantity to quote.
5. **LHS in E2 used one design for all 25 landscapes.** That design was the luckiest of 60. Corrected by Q50; the old “LHS beats BO” line is dead.
6. **Q52 savings column** used a mean where the registration said median. Do not quote that column.
7. **Three different Holm family sizes** appear in docs (39 vs 54). Direction is the same (LHS claim dies). Pick one file: `results/q39-multiplicity.json`.
8. **64 result JSONs had no provenance stamp** at audit. Q52 §2 does. Others may not.
9. **Exploratory “report the GP’s best guess” logs** exist and are in no results doc. They suggest a cheap reporting change recovers a large fraction of the E2 gap. Not reviewed. Not a claim.
10. **Digitized Hall/Ogle is 47 numbers.** It cannot carry a method comparison. The replay null is a power statement, not a biology statement.

---

## 9. What a paper should say, in order

1. **Setup.** Synthetic Hill benchmark motivated by Hall/Ogle’s endothelial ECM screen. Budget 48. qLogEI vs a 20+27+1 sequential DoE copy. Score at the true value of the selected recipe.
2. **Headline A.** At a noisy assay, scored on the best measured recipe, DoE beats BO by 0.0595.
3. **Headline C.** Scored on each method’s model recommendation, unconstrained, BO beats DoE by ~0.27 to 0.36. Constrained, the gap is mostly gone.
4. **Mechanism.** The quadratic is a saddle. Its unconstrained peak is a bad boundary point. The GP’s recommendation is better than its best measurement. Most of the verdict swing is the classical scoring rule.
5. **Generality.** Scoring-rule swing reproduces on Levy and Rosenbrock. Winner does not: Hartmann6 favours BO under every rule.
6. **Efficiency.** No defined savings ratio. At quiet noise BO arrives more often at a modest target; at realistic noise it does not. DoE uses 3 plate rounds, BO uses 10.
7. **Limits.** No cells. Oracle not fitted. Replay underpowered. GP miscalibrated. DoE arm has no steepest-ascent phase. LHS in the original grid was a lucky draw (corrected).

Closest prior work to cite in the framing, not buried: **Rummukainen et al. 2024**.

---

## 10. Questions for you

I used the project’s own triage (CORE vs ARCHIVE) to decide what is paper-important. Confirm or override:

1. **Abstract framing.** Dual reporting (DoE wins on best-measured; BO wins on unconstrained model recommendation; the swing *is* the result) — or rule A only?
2. **Is d=8 DoE accepted (T15)?** Yes / not yet.
3. **Q52 arrival rate at σ = 0.10 (24/25 vs 13/25).** Main text, supplement, or drop until a batch-size sweep exists?
4. **Q53 (one-shot GP ties on smooth landscapes).** Main claim, supplement, or later paper?
5. **Exploratory “report GP argmax” (~40–47% of the E2 gap recovered).** Look at it, or leave buried?
6. **Phase 3.** Paper 1 says “no wet lab” and stops, or we mention the in-house drop as future work?
7. **Which noise is “realistic” in the prose?** σ = 0.25 is the registered primary. σ = 0.10 is where BO looks better. Both are in the tables; the sentences have to pick a lead.
8. **Should I next rewrite `docs/MAIN-LINE.md` and a methods/results skeleton in this same plain voice**, without touching the audit-trail files (`RESULTS.md`, `OPEN-QUESTIONS.md`)?

---

## Pointers

| Need | File |
|---|---|
| Paper skeleton with numbers | `docs/MAIN-LINE.md` |
| Every experiment, long form | `docs/RESULTS.md` |
| CORE / DEFENCE / ARCHIVE / VOID labels | `docs/TRIAGE.md` |
| Draft claims | `docs/CLAIMS.md` |
| Oracle honesty | `docs/oracle_defensibility.md` |
| Lab status | `docs/LAB-DATA-FOR-BO.md`, `data/lab/overlay/GATE.md` |
| Older week recap (through 13 Aug, denser prose) | `docs/WEEK-RECAP-2026-08-13.md` |
| Dossier (through 14 Aug, also dense; header still says old HEAD) | `docs/PROJECT-DOSSIER.md` |
