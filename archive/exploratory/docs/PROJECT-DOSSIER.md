# PROJECT DOSSIER — one week of work, consolidated

> **Historical dossier (Aug 7–13).** It predates the design-space programme, final-SPADE
> study, τ/noise/OA gates and joint protocol. Use `docs/RESEARCH-SUMMARY.md` for current
> scientific conclusions and `.planning/STATE.md` for current execution status.

**Repo:** `nutrigene-ai-bo-ipsec` · **HEAD:** `3aa6701` (2026-08-13 16:25) · **114 commits, Aug 7–13 2026** · fully pushed to `origin/main`

**What this document is:** every experiment run, every result, the current conclusion, and everything still outstanding — assembled from the git history, `RESULTS.md`, `CLAIMS.md`, `METHODS.md`, `OPEN-QUESTIONS.md`, and the raw artifacts in `results/`. Where documents disagree with each other, this file says so and names which one is right.

---

## 0. THE SHORT VERSION

1. **The project asks one question:** does Bayesian optimization beat a conventional two-stage DoE/RSM pipeline for optimizing iPSC-endothelial differentiation media?
2. **The answer is "it depends on how you score the classical arm" — and that dependence *is* the contribution.** 91–97% of the swing between "DoE wins" and "BO wins" comes from how the DoE arm's recommendation is located, not from anything about BO.
3. **Under the registered primary estimand (Q41: unconstrained argmax), BO wins all four cells** by +0.27 to +0.36. Under the registered *scoring rule* (rule A, best-observed), DoE wins the primary cell by −0.0595.
4. **The data is a synthetic benchmark with a thin real anchor.** No cells were cultured. The real data is 47 usable condition medians digitized off two box-plot panels of one paper.
5. **Q52 §2 has now been run** (Aug 13–14, commit `aff36a9`). The registered analysis produces **no defined savings curve at all** — but it yields one clean, unconditioned result: **at σ=0.10 BO reaches a regret of 0.10 in 24 of 25 landscapes where the classical pipeline reaches it in 13** (11 discordant pairs to 0, exact p=0.0010, survives Holm). At σ=0.25 there is **no arrival difference at any target**. See §11.

---

## 1. YOUR THREE QUESTIONS, ANSWERED

### Q: "Is our data/model based on real endothelial cell information, or synthetic?"

**Mostly synthetic, with a thin and honestly-documented real anchor.** The repo says this about itself more bluntly than any reviewer would.

- Every headline experiment (**E1, E2, E3, E4, and ~30 of 35 Q-experiments**) runs on a **randomly generated parametric function family**, not cell data. The generated files stamp themselves `metric_name = "synthetic_response"` (`scripts/generate_oracles.py:30-32`, `src/boec/space.py:142-144`).
- **The real data is 48 conditions — 47 usable.** 23 stage-1 + 25 stage-2 condition medians (one empty), digitized from Figures 1a and 2a of Hall, Lin & Ogle, *Sci Rep* **15**:24479 (2025), DOI 10.1038/s41598-025-09256-9.
- **No wet-lab work happened.** `CLAIMS.md:277` (L12): *"No wet-lab validation… Nothing in this project has been run on cells. And the title must change: 'stem-cell differentiation protocols' promises cells."*
- **Only 5 of ~40 executable scripts touch real numbers, and only 2 produce a scientific claim** — Q31 (the replay, null) and Q33 (extrapolation geometry, held).

**Nothing was faked.** This is a declared synthetic benchmark built deliberately as a control experiment (`docs/archive/build-phase/phase1_build.md:558`, `docs/archive/build-phase/project_plan.md:35` lists Phase-1 data as *"Fake (synthetic oracle)"*). The risk is only that some downstream prose calls the landscapes *"calibrated to Hall/Ogle"* when the correct phrase is *"shaped like published dose-response behaviour."* See §4.

### Q: "We run rule C and BO wins — right?"

**Right, under the registered primary — but the qualifier is load-bearing and one of your own documents argues against it.**

| cell | rule A (best observed) | **rule C, DoE unconstrained** *(Q41 primary)* | rule C, DoE constrained |
|---|---|---|---|
| **d=6 σ=0.25** *(primary)* | −0.0595 DoE better | **+0.2931 BO better** | −0.0063 NULL (p=0.56) |
| d=6 σ=0.10 | +0.0018 null | **+0.3597 BO better** | +0.0153 BO better (p=0.0088) |
| d=8 σ=0.25 | −0.0321 DoE better | **+0.2710 BO better** | +0.0091 NULL (p=0.20) |
| d=8 σ=0.10 | +0.0015 null | **+0.3228 BO better** | +0.0001 NULL (p=0.79) |

**`RESULTS.md:355` — Q41, status `current`, decided by A:** *"the **unconstrained argmax is primary**; all three scorings reported in every table, always."* Justified on fidelity grounds: **the source study itself used the unconstrained form** — Hall/Ogle's reported optimum puts Collagen IV at coded **+1.40, 20% above the highest concentration ever tested** (`CLAIMS.md:117`, Tier-1 claim 1.5).

**But `CLAIMS.md` never absorbed Q41.** It still calls the unconstrained win *"an artefact"* (`:57`) and still lists the estimand as an **open blocking decision** (`:381`). Fix this before writing — see §8.

### Q: "Didn't the rounds/cost curve show BO winning by 8×?"

**No. Three separate things are being conflated.**

| what you may be remembering | what it actually is |
|---|---|
| **8.5×** | `0.1226` space-filling vs `0.0144` clustered — how much **clustering protects against rule-A mis-identification**. A property of the *scoring rule*, measured with a synthetic Gaussian cluster. `RESULTS.md:979`: *"demonstrates the mechanism rather than measuring its size for any particular arm."* Sources: `identification.py:26-27`, `METHODS.md:543-544`, `test_identification.py:152`. |
| **2.6×** | qLogEI beating the identification-**floor construction** (0.049 at n=500 vs 0.129 at n=384). Refuted the floor. Not a DoE comparison. |
| **the budget curve** | Q52 §1.2, `results/q52-flatten.json`. **qLogEI only — `doe`, `lhs`, `sobol`, `random` appear zero times in the artifact.** 12 instances, d=6 σ=0.25. |

**The 8.5× still helps you** — `RESULTS.md:889`: *"concentration is protective under rule A… An adaptive arm gains twice from concentrating."* BO clusters, DoE/LHS spread. That's a real mechanism favouring BO under the registered rule. It is just not a measured margin over DoE.

**The only executed BO-vs-DoE cost comparison is Q38, and DoE wins it on both axes:**

| arm | evals | **rounds** | widest plate | mean regret |
|---|---|---|---|---|
| **doe** | 48 | **3** | 27 | **0.0958** |
| lhs | 48 | 1 | 48 | 0.1270 |
| qlogei | 48 | **10** | 14 | 0.1553 |

---

## 2. WHAT THE PROJECT IS

A **benchmark study**, not a wet-lab study. It builds a synthetic landscape family shaped like published ECM dose–response behaviour, then runs seven optimization arms against it at a fixed budget of 48 measurements, to test whether BO outperforms the two-stage screen→response-surface→confirm pipeline that the source paper actually used.

**Three people.** `josephyung6686` = **Person A** (71 commits), `Alana Kwan` = **Person B** (43 commits), and a third party **"Alan"** who makes rulings (`d1e638b`, `673cc50`, `3e83fa2`). A and B ran as parallel lanes with independent clones, which is why several defects are of the form *"that number was B's clone on B's machine."*

---

## 3. WHAT WAS BUILT — the week

| day | commits | what happened |
|---|---|---|
| **Aug 7** | 9 | B ships the entire `src/boec/` package in one root commit (233 tests). A ports the oracle, raises blocking Q13. E4's first result: mechanism confirmed, **headline null**. |
| **Aug 8** | 9 (B solo) | Q13 accepted (Alan's call). Figures. **Correctness fix: pooled intervals were 1.45× too narrow.** Negative result — giving the GP the biology's shape made extrapolation *worse*. |
| **Aug 9** | **0** | — |
| **Aug 10** | **38** | The big day. E1 passes; E2 run 1 and run 2 **void**; **E2 completes: BO LOSES at the registered primary cell.** Q27: DoE wins at d=8 too. PDF cross-check resolves Collagen IV. |
| **Aug 11** | 29 | Q29 — the verdict is decided by the scoring convention. Q30: additive kernel doubles model accuracy, regret doesn't move. Hall/Ogle digitized ×2, merged, **replay null**. Q33, Q35. |
| **Aug 12** | 21 (A solo) | Q34 factorial, Q37–Q45. Q41 **decides the estimand**. Q42 generality on five families. Q45: design effect favours BO. Q47 multi-fidelity — all three predictions wrong. **Q48: the static-arm design lottery.** |
| **Aug 13** | 8 (A solo) | Q49 noise threshold. Q50: **the Q48 reversal is ESTABLISHED.** Q51: Hartmann6 d=8, BO wins all four cells. Q52 §1: the floor check refuted itself. |

**Inventory:** 330 tracked files — 23 `src/boec/` modules, 50 scripts, 30 test files, 123 results artifacts, 20 docs. `results/` alone is 17 MB.

---

## 4. THE DATA — full provenance

### The synthetic oracle: "biphasic Hill v8"

A **hand-specified parametric family with randomly drawn per-instance parameters. Nothing is fitted to real data.** `src/boec/oracles.py` never imports `boec.published` and never reads a CSV.

Per factor *i*: `h_i(x) = xⁿ/(EC50ⁿ+xⁿ)` (activating) × `g_i(x) = 1/(1+(x/IC50)ⁿ)` (inhibitory), peak-normalised to max exactly 1, then `f(x) = Σ w_i·f̃_i(x_i)` with interaction by peak modulation. Optimum value is **exactly 1.0** by construction.

**Randomized per instance:** peak position `U(0.25,0.55)`, Hill exponent `U(1,3)`, decline depth, weights, **which 4 of 6 factors are active (drawn at random)**, and the interaction matrix `U(−1,+1)`.

| dim | instances | points each | audit acceptance |
|---|---|---|---|
| d=6 | 40 | 48 | 74.07% (14 depth rejections) |
| d=8 | 25 | 48 | 83.33% (5 rejections) |

### Is it calibrated to endothelial biology?

**No parameter is calibrated. One is source-derived. Two are literature-analogy. The rest are design constraints or arbitrary.** `docs/oracle_defensibility.md` assigns an evidence class to each and names **four it declares indefensible**:

1. **Peak-position range** — the weakest link. The only interior peak resolvable in the real data (LN411 at **0.685**) lies **above the entire sampled range** `[0.25, 0.55]`.
2. **`active_share = 0.90`** — the 6→4 structure is published; the 9:1 magnitude is not. The digitized stage-1 main effects give **~0.94:1**.
3. **γ magnitude** — mechanism published, magnitude invented, **~4.6× weaker** than the one documented effect.
4. **`r ∈ [2,8]`** — plausible, unsourced, not load-bearing.

**Where the real data actively contradicts the oracle:**
- Oracle assumes an interior peak on **6 of 6** factors. Second-order fit to the digitized stage-2 medians resolves an interior peak on **1 of 4** (LN411, p=0.05); fibronectin is monotone decreasing. *The doc correctly notes this is low power, not evidence of absence.*
- Oracle implies an active:inert influence ratio of **4.5:1** (d=6) / **9.0:1** (d=8). The data gives **0.94:1**, with **no significant main effect**.

**The one genuinely source-derived number:** σ_rel. A CV backed out of the Figure-2a IQRs gives a **median implied CV of 68.2%**. They set the primary noise to **0.25 — ~2.7× lower** — calling it *"conservative… the published assay is noisier than our worst case."*

**The factors are anonymous in code.** There is no VEGF, no Collagen IV in the Phase-1 oracle. `SearchSpace.unit_cube()` builds `Parameter(name=f"x{i}")`; the parquet columns are `x_0 … x_5`. `grep` for protein names in `src/boec/*.py` returns **six hits, all prose comments, zero executable references**. `METHODS.md:13-40` asserts a mapping (Collagen I 0–35.5 µg/mL, etc.) that **the code does not implement** — it is a narrative label applied afterwards. The proteins *are* correctly named in the digitized CSVs.

**Most consequential mismatch:** the oracle picks its 4 active factors **at random per instance**. Hall/Ogle's 4 survivors are a specific published set (C, CIV, LN411, FN). The ensemble reproduces the *count*, not the *structure*.

### The real data

**Source:** Hall, Lin & Ogle, *Sci Rep* 15:24479 (2025). Readout: **CD31 area ÷ DAPI area** by immunofluorescence at day 10, normalized to a fibronectin-only control, ≥4 wells across ≥3 replicates.

**Why digitization was necessary:** the per-condition values are printed nowhere. Tables are purely coded (−/0/+); the supplement has only figure legends; no deposited dataset. *The values exist only as marks on two box plots.*

**Two independent digitizations**, kept separate on purpose — Extraction A (third-party, dot centroids, **not reproducible**, code never supplied) and Extraction B (this repo, box statistics, fully reproducible via `scripts/digitize_hall_ogle.py`).

**Cross-validation:** coded design cells agree **137/138 (99.3%)** stage 1 and **99/100 (99.0%)** stage 2; A's mean falls inside B's [Q1,Q3] in **23/23** and **25/25**; Spearman **0.880 / 0.871**. The fibronectin-only control must read ≈1.0 by construction and reads **0.969 / 1.028**.

**Reading error is not the weak link.** Optical error is **±0.025 / ±0.037** response units against a published per-condition SEM of **0.238 / 0.369** — i.e. **4–7% of the between-condition spread against 38–66%**. The assay is the binding constraint by roughly an order of magnitude.

**The source paper publishes no dispersion at all:** zero occurrences of "standard deviation", "standard error", "SEM", or "error bar"; **not a single numeric p-value**; no SE, R², RMSE or ANOVA table for the fitted surface despite Methods claiming ANOVA was conducted.

---

## 5. METHODS — the arms and the scoring rules

**Seven arms at budget 48**, paired at instance level, n=25 instances × 2 seeds, d ∈ {6,8} × σ_rel ∈ {0.10, 0.25}:
`qlogei` (primary), `qlognei`, `random`, `sobol`, `lhs`, `coord` (coordinate descent), `doe` (sequential 20+27+1).

**The DoE arm** reproduces the published pipeline: stage 1 screens 6→4 factors, stage 2 runs a face-centred CCD on survivors, stage 3 fits a second-order surface, stage 4 measures the predicted optimum.

**Scoring — all three rules score at the *noiseless* oracle value of the selected point (Q17). They differ only in which point is "selected":**

| rule | selected point | implementation |
|---|---|---|
| **A** | **best observed** — argmax of the observed prefix, indexed into true values | `diagnostics.py:236-237` |
| **B** | DoE's stage-4 confirmation recipe, BO still at best observed — **asymmetric, disqualified by its own author** | `doe.py:333-341` |
| **C** | **symmetric** — each arm at its own model's argmax, one shared locator | `q29_symmetric.py:71-99`, `metrics.py:67-138` |

**Rule C has two variants, and the choice between them is worth more than the entire BO-vs-DoE gap it modifies:**

| variant | DoE bounds | d=6 σ=0.25 DoE regret |
|---|---|---|
| **unconstrained** *(Q41 primary)* | kept factors' full range | **0.4163** |
| constrained | the stage-2 sub-box actually explored | **0.1169** |

Difference: **+0.2995 [+0.2790, +0.3228], p<0.0001**, at all four cells.

**Registered primary:** rule A, `e2.yaml:133-137`, committed **35 minutes before** the E2 result landed. Rule C appears nowhere in `e2.yaml` — it is Q29's declared secondary, later promoted by Q41.

**Inference:** clustered at instance (effective n=25, not 50), Wilcoxon signed-rank governs significance, instance-level bootstrap (2000 draws) governs magnitude.

---

## 6. RESULTS — where BO wins and where it loses

### It wins

| condition | evidence |
|---|---|
| **Rule C with DoE unconstrained — all four cells** *(the registered primary estimand)* | +0.2931 / +0.3597 / +0.2710 / +0.3228, p≈6e-08 |
| **Hartmann6 (non-additive, deceptive) — every cell, every rule** | +0.2460 / +0.3460 / +0.3189 / +0.4134 rule A; all p<0.0001. At d=8, BO wins all four cells and **the DoE screen performs at chance** (2.96 and 2.88 of 4 slots vs chance 3.00) |
| **vs LHS, design-averaged (Q50)** | +0.0219 [+0.0145, +0.0292], Wilcoxon **p=1.8×10⁻⁵**, ahead on **21 of 25** instances, survives Bonferroni over all 39 contrasts |
| **The design effect, model held fixed (Q45)** | +0.1129 / +0.2883 / +0.1247 / +0.2669, all p≤0.0008 — *"the DoE arm's design is not bad; it is well-built for the wrong question"* |
| **Conditioning (Q44/Q34)** | Backwards from prediction: cond(DoE) **8.1e16–1.1e18**, cond(BO) **2.4e2–3.9e3** — ⚠️ these are **per-cell medians**; the actual per-run ranges are **5.1e16–1.9e19** and **117–1.0e7**, and no document says so |
| **BO's recommendation beats its own best observation**, all four cells | **9.9–20.7% better** (not the "15–20%" quoted in several summaries — d=8 σ=0.10 is 9.9%). p-values are **0.0025–0.045**, not p<0.0001; at d=8 σ=0.10 (p=0.045) this would not survive any correction. **Established at d=6 σ=0.25 only** |

### It loses

| condition | evidence |
|---|---|
| **Rule A at the registered primary cell** | DoE −0.0595 [−0.0792, −0.0373], p<0.0001 |
| **Rule A at d=8 σ=0.25** | DoE **−0.0284 [−0.0453, −0.0140], p=0.0023** — *not* the −0.0321 still printed in `CLAIMS.md:135`, which is B's cross-clone pairing |
| **Sequential lab rounds (Q38)** | DoE 3 rounds vs BO 10, at equal evaluations. Against design-averaged qLogEI: **0.0958 in 3 rounds vs 0.1532 in 10** |
| **On real data (Q31 replay)** | **Null at both stages, under BOTH rules.** BO not faster than random to a top-5 condition (3.50 vs 3.50 rule A; 8.50 vs 8.50 rule C). Bounded by Q37: MDE **0.675 evaluations** — the study is too small to show anything |
| ~~Levy and Rosenbrock~~ | 🔴 **WITHDRAWN — see §6b. These family-cells are void under rule A.** |

### 6b. 🔴 THE BIGGEST UNCAUGHT DEFECT — Levy and Rosenbrock are void under rule A

`scripts/run_q42_families.py:109` voids a family only when its optimum is the **exact** box centre (`atol=1e-9`). Ackley trips it; Levy and Rosenbrock do not. But their DoE rule-A regret is a **stage-1 centre replicate in 200 of 200 runs, to nine decimal places, at both noise levels**:

| family | regret at exact box centre | DoE rule-A mean | SD | unique values across 25 seeds | responds to σ? |
|---|---|---|---|---|---|
| levy d=6 | 0.004010759 | **0.004011** | **0.000e+00** | **1 of 25** | **no** |
| levy d=8 | 0.003949667 | 0.003950 | 0.000e+00 | 1 of 25 | no |
| rosenbrock d=6 | 0.000349095 | 0.000349 | 0.000e+00 | 1 of 25 | no |
| rosenbrock d=8 | 0.000443889 | 0.000444 | 0.000e+00 | 1 of 25 | no |
| hartmann6 | 0.8479 | 0.5398–0.6504 | **0.086–0.109** | **11–20 of 25** | **yes** |

**The DoE arm never searched.** Zero variance across seeds and identical figures at σ=0.25 and σ=0.10 is *exactly* the diagnostic this project used to void E2 run 1 and to void Ackley (L16: *"any centred test function silently rewards any design with centre runs"*).

**Consequences:**
- `RESULTS.md:534-536` claims the *"~93% additive, therefore your oracle"* objection is **"answered by data"** because Levy and Rosenbrock reproduce the result. **It is not answered.**
- Under rule A, **12 of 16 family-cells are void, not 4.** The correct statement of Q42's rule-A result is *"the reversal reproduces on **0 of 4** usable family-cells."*
- **The only external family with a usable rule-A DoE number is Hartmann6 — where BO wins all four cells under every rule.**

**What survives:** the rule-C-constrained nulls on Levy/Rosenbrock are less contaminated (the constrained argmax does move off centre), and **the scoring-convention effect stands**, because it is a within-DoE-arm contrast that never involves rule A.

**Fix:** replace the exact-centre void test with two empirical detectors — (a) DoE rule-A regret has zero variance across seeds, (b) it is identical at both σ — then re-run Q42. *One afternoon of compute.*

### It's a tie

- **At σ=0.10 the contest disappears.** Top four arms indistinguishable at both dimensions: `qlognei` 0.0808 / `qlogei` 0.0874 / `coord` 0.0880 / `doe` 0.0892 (d=6).
- **Rule C constrained:** three nulls and one BO win of +0.0153.

### Negative results that are load-bearing

- **Surrogate accuracy is not the constraint.** The additive kernel took held-out R² from **0.375 → 0.744** and regret moved **−0.0015, p=0.711**.
- **A GP's uncertainty does not beat plain nearest-neighbour distance** at flagging extrapolation — bounded below 0.08.
- **Giving the GP the biology's known shape made extrapolation worse.**
- **Four explanations for BO's rule-A deficit eliminated by direct test:** not the prior (Q25), not the solver (Q21, 0.118% vs a registered 1% threshold), not the opening size (Q26), not the model class (Q30).

### Twelve registered predictions came out wrong

Kept deliberately as the most informative rows in `RESULTS.md`. Highlights: the DoE screen was predicted to spend ≥3.5 of 4 slots on active factors — it spends **2.96, where chance is 3.00**. Q52's floor was registered as a bound no arm could beat — **qLogEI beat it by 2.6× the same afternoon**. All three Q47 multi-fidelity predictions failed.

---

## 7. THE CURRENT CONCLUSION

> On a **near-separable** landscape (~93% additive variance) with ~25 candidate conditions and single-replicate measurements, **BO has almost nothing to exploit** — and that is a statement about the experimental regime, not about Bayesian optimization.
>
> Whether BO beats current practice on this benchmark is **decided by how the classical arm's recommendation is located**, and **91–97% of that swing is the DoE arm's scoring, not anything about BO**. Under the registered primary estimand (unconstrained argmax, as the source study itself scored), **BO wins all four cells**. Under best-observed, **DoE wins the primary cell**. On a non-additive landscape this project did not build (Hartmann6), **BO wins everything under every rule**.

**The reframed contribution** (`CLAIMS.md:46`): *the DoE-vs-BO literature is split — one camp reports 3–30× fewer experiments, a 2025 review reports no reduction at all — and the split is substantially attributable to an unregistered scoring convention on the classical arm.*

**This is not a novelty claim.** Picheny, Wagner & Ginsbourger (2013) already separate the infill criterion from the identification criterion — that distinction *is* rule A vs rule C. The contribution is *measuring how much the choice is worth* on an executed classical comparator, not observing that a choice exists.

### ⚠️ How an independent skeptic reads the same evidence

An adversarial adjudicator that recomputed every cell from the raw JSON landed **against** the pro-BO framing, and you should read its verdict because it is the reviewer objection you will face:

> *"BO wins under rule C **only** when the DoE arm's recommendation is taken at the unconstrained argmax of a fitted surface that is a saddle in 200/200 runs — a scoring choice worth +0.2995 to +0.3444 on its own, i.e. larger than the entire BO-vs-DoE gap it creates."*

**Both readings are defensible and the project has not chosen between them.** Q41 makes unconstrained primary on *fidelity-to-the-case-study* grounds — the source study did extrapolate. The skeptic answers that fidelity to a bad practice does not make the comparison fair. `CLAIMS.md:381` still lists this as a live blocking decision owned by A/Alan, and `e2.yaml` forbids resolving it after seeing the numbers.

**A nuance neither side had noticed:** under the *constrained* variant the DoE arm's rule-A→C swing is +0.0211/−0.0036/+0.0185/−0.0071 — **smaller in magnitude than BO's swing in 3 of 4 cells**. So the headline "91–97% of the swing is the classical arm" is itself a statement about *unconstrained* scoring, and must be written that way.

---

## 7b. DOES THE CODE STILL WORK? — yes, verified by running it

Full suite run 2026-08-13 on `.venv/bin/python 3.11.15`:

```
2 failed, 632 passed, 3 warnings in 164.77s
```

**The committed codebase is 100% green.** Both failures are in `tests/test_exploratory.py` — one of the **11 untracked files** — where `build_gp()` is called with a `warp=True` kwarg the committed `build_gp()` does not accept:

```
TypeError: build_gp() got an unexpected keyword argument 'warp'
  tests/test_exploratory.py:88  test_warp_is_chained_after_normalize_and_stays_in_the_unit_cube
  tests/test_exploratory.py:107 test_warp_parameters_are_fitted
```

So the exploratory workstream was written against a version of `build_gp` that was never committed — the uncommitted work is **both untracked and broken against `main`**. Fix or drop it before it is lost.

**Environment:** torch 2.13.0 · botorch 0.18.1 · gpytorch 1.15.2 · numpy 2.4.6 · scipy 1.17.1 · scikit-learn 1.9.0.

---

## 8. DEFECTS IN THE STANDING RECORD — fix before writing

| # | defect | evidence |
|---|---|---|
| **1** | **`RESULTS.md:145` says "BO wins at d=8". It is wrong.** Q27 established DoE beats qLogEI at d=8 σ=0.25 by −0.0321, p=0.0003. `CLAIMS.md:135` has it right. | commit `06df4f1` |
| **2** | **`CLAIMS.md` never absorbed Q41.** It calls the unconstrained rule-C win *"an artefact"* (`:57`) and still lists the estimand as an open blocking decision (`:381`) — decided Aug 12 in `a36581a`. **This is the contradiction most likely to have confused you.** | `RESULTS.md:355` vs `CLAIMS.md:57,381` |
| **3** 🔴 | **The Levy/Rosenbrock void — §6b.** `RESULTS.md:534-536`'s generality claim does not hold. Highest scientific impact of anything on this list. | `q42-families.json` |
| **4** 🔴 | **The rule-C-constrained BO-vs-DoE table has NO committed script and NO committed log.** `run_q39_multiplicity.py` reads both source JSONs but only ever forms *within-file* contrasts — it never computes `q35.constrained − q34.cell4_bo_gp`. Grepping `results/` for `0.0063`, `0.0153`, `0.0091` returns nothing. **The numbers are sound (independently reproduced) but un-backed** under your own rule 1 (*"a number with no committed file does not go in"*). **Fix: commit a 12-line aggregation script.** | `RESULTS.md:10-12` |
| **5** 🔴 | **Q50's headline paired inference is prose-only and NOT recomputable.** `+0.0219 [+0.0145,+0.0292], p=1.8×10⁻⁵, 21/25` appears only in prose. `q48-design-variance.json` stores **60 design-level means per arm-cell and no per-instance LHS values**, so the pairing has no surviving input. **The point-estimate reversal stands; the p-value and win-count have no artifact.** Fix: re-run Q48's LHS sweep persisting per-instance regrets, ~1 hour. | `q50-qlogei-seedsweep.log` is 34 lines |
| **6** | **d=8 rule-A cells still carry B's superseded clone pairing** (−0.0321 / +0.0015). Current values from A's clone: **−0.0284 / −0.0024**. Note the sign flips at σ=0.10 (both null, so no verdict moves). | `CLAIMS.md:135-136`, `RESULTS.md:159` |
| **7** | **`CLAIMS.md:364` says "Under rule C it wins everywhere."** Stale — contradicted by the corrected table 230 lines above it. **This is probably where the belief keeps getting refreshed.** | `CLAIMS.md:131-136` |
| **8** | **`CLAIMS.md:248` (L8) still quotes Q36's superseded un-normalised "+1.0032 rule A".** Q42 supersedes with **+0.2460**. | Q42 |
| **9** | **`q52-flatten`: the log records 12 instances, the committed JSON has 4 rows.** *(Correction: my earlier reading was wrong — `RESULTS.md`'s "4 instances" correctly describes the JSON. Recomputing from the log's 12 gives 0.1708 → 0.0473, −72.3%, vs the committed 4-instance 0.1748 → 0.0488, −72.1%.* **Conclusion unchanged; provenance is not.** Either eight checkpoints were lost or the log is wrong. | `q52-flatten.{log,json}` |
| **10** | **Three different Holm family sizes circulate** for the same contrast — 39 vs 54. Verdict identical (ns) every way; the numbers are not. | `RESULTS-PERSON-A.md:34` vs `q39-multiplicity.log:74` |
| **11** | **`results/e2-doe-d8.log:88` claims rows were written to `e2-doe-d8.json`. That file was never tracked.** Mitigated: Q34/Q35 regenerate the d=8 DoE arm, so the d=8 rule-A contrast *does* have a machine-readable source in `q34-factorial.json`. What is unrecoverable is the **other five arms'** d=8 σ=0.10 pairings, which remain log-text only. | D17 |
| **12** | **`q42-families-rerun.log:278`** labels a result *"BO better"* at **p=0.0516**, keying the verdict on an uncorrected CI — the exact back door Q39 forbade. | — |
| **13** | **11 untracked files — a whole exploratory workstream lives only in your working tree**, and it fails against `main`. Plus a stash from Aug 11. | `git status` |
| **14** | **`METHODS.md:13-40` asserts a protein↔dimension mapping the code does not implement.** | `space.py:132-145` |

---

## 8b. DATA HYGIENE — the unlogged results you suspected

**129 files in `results/`** (the "123" undercounts — 6 more sit in `results/figures/`). ~16.4 MB, of which **11.1 MB (68%) is Q47 alone**.

### The five findings that matter

**1. 🔴 Not one results JSON records provenance.** All **64 JSON/JSONL files** scanned for `git_sha|commit|generated_at|timestamp|config|argv|python_version|hostname` → **zero hits**. Reproducibility rests entirely on row-level `seed` fields plus **two hand-typed strings** in two log headers. Everything else is unstamped.

**2. 🔴 The largest block of unlogged data is a crashed run.** `results/exploratory-three-factor.log` ends in an **uncaught Python traceback** (`ValueError: operands could not be broadcast together with shapes (11,) (25,)`), with **36 of 400 runs failed**, cell 8 of the 2³ factorial never printed, and 217 KB of JSON on disk. Untracked, referenced by no document.

**3. 🔴 A substantial BO-favourable finding is sitting unlogged and untracked.** `results/exploratory-recommendation{,-b}.log` contain a self-consistent result that appears in **no** results document: posterior-argmax reporting recovers **40.2%** of the reported-to-visited gap at σ=0.25 and **45.3%** at σ=0.10, and **a 47-search + 1-confirmation arm closes 47% of E2's +0.0595 gap to DoE.** That is a concrete, cheap improvement to the BO arm that nobody wrote down.

**4. Four scripts print "written to `results/X.json`" for a file that does not exist.** Only one — `e2-doe-d8.json` — is recorded as a defect (D17). The other three are the same failure mode and are **undocumented**: `bench-surrogate.json`, `e4-robustness.json`, `q29-symmetric.json`.

**5. Every file in `results/figures/` is unreferenced by filename in any document**, and the three E4 PNGs were generated from the **superseded E4 first run**, not the v2 rerun whose numbers `RESULTS.md` and `CLAIMS.md` actually cite.

### Also

- **`RESULTS.md:529` is stale against its own artifact.** It says *"Across all 350 runs: saddle 247, maximum 103."* `q42-families.json` today holds **400 rows, saddle 297, maximum 103** — the Hartmann6 d=8 rerun overwrote the file and the sentence was never updated.
- **Large artifacts are untracked:** `e3-grid.json` (1.1 MB), `diagnostic-lengthscales.json` (1.1 MB), `pf1-grid.json`, `confound-ninit.json`.
- **The 8.5× has no computed artifact.** It exists only in prose (`RESULTS.md`, `METHODS.md`), a module docstring, and a test docstring — and the test asserts *direction*, not the ratio. This violates `RESULTS.md`'s own Rule 1.
- **Orphaned but harmless:** the four `e2-grid-d*` shard files and `e2-determinism.json` are superseded by the merged `e2-grid.json`.

---

## 9. WHAT IS STILL UNFINISHED

### Registered but never run

| item | why it matters | blocker |
|---|---|---|
| **Q52 §2–3 — budget-to-target grid** ⭐ | **The stated next step, and the experiment that would settle "does BO need fewer runs".** 8 targets (0.30→0.05), cap 200, four registered predictions. | **No code exists.** Compute-bound. |
| **Symmetric budget-matched rule-B run (Q28)** | Would settle the estimand question empirically instead of by decision. | Endpoint + decision rule need writing first; A must see them |
| **Stage-4 for BO** | Neither rule is budget-matched — *"rule A taxes DoE; rule C subsidises BO."* | Needs registering; ~one re-run of the BO arms |
| **E1 check #4** | The **only** E1 check that exercises your own landscape family. | Never run; `run_e1.py` does Branin/Hartmann6/Ackley only |
| **E4 at n=40** | Ensemble was extended to 40; E4 still ran at 25. Power 80% → 92%. | The config line was never executed |
| **Both-rules table for the E2 arms** | `e2-grid.json` stores reported-best only — **no rule C exists for the Hill-oracle arms.** | Needs a new run fitting a GP per arm per instance |
| **`share` sensitivity at 0.75/0.95** | Would convert the oracle's weakest justification into a reported robustness range. *"Cheaper than defending 0.90 in review."* | Flagged, never done |
| **Q46 / Paper 2** | Replication-vs-adaptivity, incl. hetGP — the actual prior-art baseline. | Deliberately gated: *"no code until Paper 1 is submitted."* Two of five premises already refuted |
| **d=12 capability test**, **Hou 2017 secondary replay** | Generality across studies | Never started |

### Blocking decisions (owner: A / Alan)

| | decision | governs |
|---|---|---|
| **Q28/T16** | rule A or rule C as E2's estimand — **arguably already answered by Q41; reconcile** | the paper's headline |
| **Q19** | E4's registered cell or the pooled figure — they **disagree in sign** | E4's headline |
| **T15** | accept the d=8 DoE split | whether the d=8 row stands |
| **Q23** | confirm `coord`'s unpaired status | L3 |
| **Q30** | frame the additive arm as a *different method*, not qLogEI rescued | Tier-3 claim |

### Unsettled by the artifacts — each needs an experiment

| | question | why unsettled | what settles it |
|---|---|---|---|
| **U1** | Rule A or rule C as the estimand? | `e2.yaml` never fixed it; Q41 designated the DoE *scoring* but says *"Supersedes: nothing"* and did not re-designate E2's primary | Not an experiment. Report both, or let the uninvolved PI choose. `e2.yaml` itself forbids the alternative: `designate_headline_after_seeing_results: forbidden` |
| **U2** | At what σ does the winner flip? | Only two σ values ever ran against a DoE arm. Q49 sweeps 7 levels but runs **one arm** and contains no BO-vs-DoE contrast | σ-sweep of `doe` vs `qlogei` at σ ∈ {0.05…0.50}, both rules |
| **U3** | Does the constrained rule-C win at d=6 σ=0.10 survive correction? | +0.0153, raw p=0.0088, in no multiplicity family. Q39 killed a contrast at raw p=0.0393 → Holm 0.5114 | Add the four constrained contrasts to Q39's family, re-run Holm. **Ten minutes.** |
| **U4** | Is d=8's shrinking margin a dimension effect? | Three-way confounded: `n_init=2d+2`, inert-weight split, `n_active` held at 4 | A d=6 arm at `n_init=18` |
| **U5** ⭐ | **Would a wider BO batch close the round gap?** | Q38 fixes q=4 → 10 rounds. A lab willing to run 27-well plates for BO could plausibly reach ~3 rounds | qLogEI at q ∈ {4,12,16,24}, budget 48. **The single highest-value unrun experiment for a wet-lab audience** |
| **U6** | The n=96 local maximum in Q52's rule-C identification error, 4 of 4 cells, non-overlapping intervals | Four of four is not sampling error; no mechanism established | — |

### Priority order

1. **Reconcile `CLAIMS.md` with Q41** (defect 2) — nothing can be written until the headline is stable.
2. **Fix `RESULTS.md:145` and the superseded d=8 numbers** (defects 1, 6) — flatly wrong headlines in the standing record.
3. **Rebuild the Q42 void test and re-score** (defect 3) — the generality claim currently does not hold, and this is a retraction risk.
4. **Commit the two missing aggregation scripts** (defects 4, 5) — your two most decision-relevant tables have no backing artifact.
5. **Run Q52 §2–3**, and **U5** alongside it — together they answer the sample-efficiency question the literature is split on.
6. **Commit or delete the 11 untracked files.**
7. Then the L-series limitations, which are already written and unusually thorough.

---

## 10. WHAT THE PAPER CAN HONESTLY CLAIM

**Can claim:**
- The DoE-vs-BO split in the literature is substantially attributable to an unregistered scoring convention on the classical arm — measured at **10:1, up to 33:1**.
- The published two-stage pipeline **over-promises systematically**: pooled over-prediction **+1.103 [+1.024, +1.182]** against a response whose maximum is 1.0, in **100/100** cells.
- The fitted surface is a **saddle wherever the response is biphasic** — 800/800 PF1 cells, 200/200 Q35 runs — so the unconstrained argmax must reach a boundary.
- **Surrogate accuracy is not the binding constraint** (Q30, by direct test with a measurably better model).
- Under the registered primary estimand, **BO wins all four cells**; on a non-additive landscape it wins under every rule.

**Cannot claim** (`CLAIMS.md:361-374`):
- ~~"BO beats current practice"~~ — not under the registered *rule*.
- ~~"Our BO is more sample-efficient"~~ — **not shown**; not run (Q52 §2–3), null where tested (Q31), undetectable below 0.68 evaluations (Q37).
- ~~"BO reaches the optimum in fewer runs"~~ — same.
- ~~"Latin hypercube beats BO"~~ — reversed by Q50.

**Mandatory limitations** (L1–L19, already drafted): the benchmark is ~93% additive; one oracle family; **no wet-lab validation**; the title must change; adaptive arms are **not reproducible across machines** (A's qLogEI mean 0.1553, B's 0.1641); every static-arm interval is a *within-design* interval.

---

---

## 11. NEW SINCE THIS DOSSIER WAS WRITTEN — Q52 §2, run Aug 13–14

**Commits:** `df11ad6` (design) → `d86e2c2` (amended spec + predictions P4–P6) → `633e74d` (runner) → `aff36a9` (result). Registration precedes the runner; timestamps are checkable. **Fidelity gate: `max |Δ| = 0.000e+00`** against 10 stored `e2-grid.json` qLogEI rows.

### The headline is a null

Under the **registered** rule/target pairings the savings ratio is **undefined everywhere**, at both noise levels. Rule C: the classical arm is censored 64–100% at every target, including the loosest — consistent with Q35's unconstrained 0.4163 being worse than the loosest target in the set. Rule A at its own registered targets (0.03/0.02/0.01): **zero paired arrivals.**

### The one result that survives, and it is noise-dependent

Arrival rate is the only unconditioned quantity in the grid — every instance contributes, nothing is selected on. Paired exact test on discordant pairs:

| σ | target | BO | DoE | discordant | exact p |
|---|---|---|---|---|---|
| **0.10** | **0.10** | **24/25** | 13/25 | **11 : 0** | **0.0010** ✅ survives Holm |
| 0.10 | 0.08 | 22/25 | 13/25 | 10 : 1 | 0.0117 |
| 0.10 | 0.05 | 18/25 | 7/25 | 15 : 4 | 0.0192 |
| 0.25 | any target | — | — | — | all p > 0.34 |

**Not *"BO gets there in fewer experiments"* — that comparison is undefined here — but *"at a quiet assay BO gets there at all, far more often."* And it vanishes at σ=0.25, the noise level registered as primary.**

### A wrong headline, written and retracted before publication

The first pass claimed *"the savings ratio inverts, crossover at 0.15."* Wrong four ways: it read rule A at rule C's designated targets (the registration forbids promoting the appendix); it quoted a cell where DoE is 56% censored with 7 pairs, tripping both registered gates; the apparent decline was **survivorship** — on the fixed 7 instances that pair at every target the ratio is **flat at 6.00 evaluations / 3.00 rounds**; and the sign test at 0.15 was 9 BO-better to 10 DoE-better. Caught by adversarial re-derivation from the raw JSON. Recorded in `RESULTS.md` rather than deleted.

### Two new defects

- **D18** — `report()` prints a savings column the registration does not define. `instance_bootstrap` returns `v.mean()`; the registration says median of per-instance ratios. **They disagree in direction.** Not quotable until fixed.
- **D19** — *a registration binds only the analysis that runs through it.* Every gate was registered **and correctly implemented**; the bad headline came from an ad-hoc script that reproduced the arithmetic without them.

### 🔴 One more defect, found while implementing — it affects a published number

**`DoEResult.curve_true` is oracle-best, not rule A.** It is `np.maximum.accumulate` over the *noiseless* values — the running best true value among visited points, the exact scoring error that voided E2's first run. **`run_q35_constrained_rsm.py:181` computes its "best observed" column from it.** Measured on 20 DoE runs at d=6 σ=0.25: oracle-best median **0.0629**, rule A median **0.0950**, differing in **18 of 20 runs**. Q35 reports 0.0597; E2 reports 0.0957.

**Impact on L6:** the residual `constrained − best_observed` is **0.0312 / 0.0572 / 0.0377 / 0.0573** across the four cells. Scored with rule A the primary-cell value becomes roughly **+0.0212** — about **2.7× smaller**. Direction survives, magnitude does not, and the contrast sits in Q39's Holm family. **Not fixed: changing published numbers is your call.**

### `.gitignore` nearly swallowed the artifact

`results/*` ignores `.json` and only `*.md` / `*.log` are negated, so the result file was silently unstageable after the run — the `aa0785d` failure mode exactly. Negated explicitly. The artifact carries a **provenance block** (git SHA, timestamp, argv, library versions, full config); no other file in `results/` does.

---

## 12. SINCE §11 — the D20 fix, the triage, the matrix, and Q53

Four pieces of work, in order. All committed; suite green throughout.

### 12.1 D20 fixed and rescored — `e2ccd52`

All three sites now use `reported_best_curve`, guarded by an AST test asserting **no script reads
`curve_true`**, plus a non-vacuity test and a test that the one exemption cannot outlive its
reason. **Only the DoE arm was re-run**, and the equivalence is gated rather than asserted:
untouched columns reproduce at **worst |Δ| = 0.000e+00** over 400 Q42 rows and 200 Q35 rows.

**No verdict moved — 0 of 16 family-cells flipped.** Two things did:

- **My own "Levy and Rosenbrock are void" diagnosis is WITHDRAWN.** The zero-variance signature
  was entirely this bug. Distinct DoE values across 25 seeds went levy **1 → 9/5/12/5**,
  rosenbrock **1 → 11/8/12/10**, ackley **1 → 4/2/4/2**. Those cells are legitimately scored.
  Q42 needed a rescore, not a retraction.
- **Q35's residual loses two of four cells.** σ=0.25 survives at about a third of its published
  magnitude (**+0.0211**, **+0.0185**); **both σ=0.10 cells are NULL**. The "two arms fail in
  opposite directions" framing is a property of the **noisy assay**, not of the model classes.

Corrected `best_observed` is **0.0958**, now agreeing with E2's independent **0.0957** — resolving
a discrepancy the two documents had carried for the life of the project.

### 12.2 Triage — `8696644` · `docs/TRIAGE.md`, `docs/MAIN-LINE.md`, `docs/archive/`

**65 items labelled: 13 CORE, 21 DEFENCE, 19 ARCHIVE, 12 VOID.** `docs/` went from 18 files to 10
plus an archive. **`CLAIMS.md`: 42 claims before, 34 after**, nothing deleted — every struck item
keeps its place and its reason.

Dropped: **2.2, 3.1, 3.2, 3.5**, all E4, which asks whether GP uncertainty beats nearest-neighbour
distance at *flagging* extrapolation — a question no sentence of the result depends on. Merged:
**L18** into L13. Struck as already decided: **Q28/T16** (by Q41) and **Q30** (by its own
registration); **Q19** no longer blocks. Demoted: **1.1** loses its E4 half, **1.5** is an
unverified inference by its own last sentence.

**The largest finding was a framing, not a claim.** Tier-2 2.1's resolution read the
**constrained** argmax as primary and called the rule-C result "an artefact". **Q41 designates the
unconstrained argmax primary**, under which BO wins rule C at all four cells by **+0.2710 to
+0.3597**. Both must be printed; only the sensitivity was.

**Prior art, corrected against the project's own Task A verification:** Nguyen 2017 struck as a
contrary result (it concerns the EI *incumbent*, not the recommendation); Picheny struck for the
infill/identification distinction (*"do not cite it for that distinction yet"*); Gisperg's
no-reduction finding reattributed to **Rummukainen 2024**, which was **missing from the table
entirely** and is the closest prior work in existence.

Also found: **`project_record.md` is cited four times and has never existed at any commit**, and
**`docs/METHODS.md` anchors to zero artefacts**.

### 12.3 The information matrix — `b0a2dc3` · `docs/INFORMATION-MATRIX.md`

Every arm, every column, every number with a path and an n. Two things it made visible that no
single entry did:

- **The classical arm is nearly noise-insensitive.** `doe` moves **+0.0066** from σ=0.10 to 0.25
  where `qlogei` moves **+0.0679** — a factor of ten. That one row explains why BO loses at 0.25
  and ties at 0.10, and it was written down nowhere.
- **`spread_gp` ties qLogEI on Hill in one round against ten.** Paired at 48 evaluations on the
  same instances with the same scoring function, `qlogei − spread_gp` is **null on both rules at
  both σ**. One registered disagreement: at σ=0.25 rule A, Wilcoxon gives p=0.034 while the
  bootstrap covers zero — **Q20 §2 says report it, not resolve it** — and it survives no Holm
  correction.

It also caught the design lottery a second time: `spread_gp`'s two independent measurements of the
same Hill cell differ by **0.0239**, about one design SD (Q48/D16). **A single-draw number from
that arm is not quotable.**

### 12.4 Q53 — registered `73d2361`, harness `9c7a081`, running

**`spread_gp` had never run off the Hill family.** Q42's shards carry only `bo_*` and `doe_*`
columns, so generality was a run, not a lookup. Registered before the runner existed:

> **spread_gp loses to qLogEI on Hartmann6, both dimensions, both noise levels, under both rules.**
> **Falsifier:** if it ties or beats, **the Hill result becomes the suspicious one**, not this one.

Sixteen family-cells, **5 independent LHS draws per (family, cell, seed)** averaged within seed,
design SD reported beside every estimate, and a registered rule that a contrast smaller than its
cell's design SD is **not a result**. **Fidelity gate passed at exactly 0.000e+00** on 8 stored
Q42 rows, both rules — ⚠️ all 8 landed on Ackley, spanning all four cells but one family, which is
a limitation of the gate's sampling and is recorded rather than glossed.

---

*Assembled 2026-08-13 from git history and repository artifacts; §11 added 2026-08-14, §12 the
same day. Every number traced to a file or commit. Where documents disagree, both readings are
given and the primary source named. Suite: **659 passed**, and the two former failures left with
the exploratory workstream into `docs/archive/`, so the committed tree is clean.*
