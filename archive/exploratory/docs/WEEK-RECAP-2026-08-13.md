# Week recap — 7–13 August 2026

**Who this is for.** Anyone (including a confused later session) who needs one file that says: what this project is, what was built, which numbers are canonical, which logs are poison, and what is still open.

**Sources.** Git history on `main` (`3aa6701`, ~106 commits since 7 Aug), `docs/RESULTS.md`, `docs/RESULTS-PERSON-A.md`, `docs/CLAIMS.md` (draft), `docs/OPEN-QUESTIONS.md`, `docs/METHODS.md`, `docs/oracle_defensibility.md`, `results/` artefacts, and the uncommitted Q50 / estimand-evaluation work still in the working tree on 13 Aug. Cursor transcripts only cover 7 Aug (docs) and this recap request; **the experimental week lives in git and `docs/RESULTS.md`, not in chat logs.**

**Authors.** Person A (`josephyung6686`) and Person B (`Alana Kwan`). Alan is the third loop (author-order / release / session-coordination).

---

## 0. The one question: endothelial cells or math?

**Phase 1 (everything E1–E4 and almost every Q-study) is a mathematical model.** It is not fitted to live endothelial measurements. The ground truth is a **biphasic Hill-function oracle** with a planted optimum. `docs/CLAIMS.md` L12: *“Nothing in this project has been run on cells.”*

**Endothelial biology is the framing and the calibration, not the training data.**

| What is biological | What is mathematical |
|---|---|
| Motivation: hiPSC → endothelial (EC) differentiation, ECM protein coatings, CD31 readout | Phase 1 objective function: planted Hill landscape |
| Factor *labels* and coded ranges from Hall/Lin/Ogle 2025 (six ECM proteins) | Factor *values* drawn from design constraints (`x*` in U(0.25, 0.55), `n` in U(1,3), etc.) |
| Screening structure 6 → 4 proteins; fibronectin attachment floor 22 µg/mL | Interaction magnitudes invented (~4.6× weaker than the one documented FN/TGFβ effect) |
| Phase 2: lookup table of **digitized published figures** (48 conditions, pixel extraction) | Noise model `y = f(x)(1+ε)+η` with `σ_rel = 0.25` primary |
| The published DoE *procedure* is what the classical arm copies | d=8 adds two **synthetic** nuisance factors with no physical meaning |

Accurate one-liner for a paper or a later agent:

> This is a **synthetic Hill-function benchmark whose search-space labels, screening structure, and some ranges are taken from a published iPSC→endothelial ECM DoE study**. Real endothelial measurements are not the Phase 1 ground truth. Phase 2 replays digitized figures from that paper. Phase 3 (wet lab) is out of scope *as an optimisation result* — but the in-house drop now exists and is fully read: see `data/lab/` and `docs/superpowers/specs/2026-08-14-lab-data-pipeline-design.md`. No CD31 number from it is signed off, so nothing there is Phase 3 evidence yet.

Do **not** write “we optimized endothelial cells” or “the model is trained on endothelial data.” Write “benchmark calibrated to a published endothelial differentiation dataset.”

Repo name `nutrigene-ai-bo-ipsec` / package `boec` = Bayesian optimization for iPSC-EC. There is no separate “IPSEC protocol” in the code.

---

## 1. One-paragraph story of the week

In seven days (nothing on 9 Aug) two people built a BO-versus-sequential-DoE benchmark, ran the four registered experiments, and got a headline **negative result: at the pre-registered primary cell (d=6, σ_rel=0.25, budget 48), sequential DoE beats qLogEI by 0.0595**. That result then nearly unravelled: first two E2 runs were void (scoring + pairing bugs); a DoE cell once ran BO under a DoE filename; two clones held different E2 grids under one gitignored filename (the −0.0708 number is B’s clone, not canonical); the verdict flips by ~10:1 if you score DoE at its unconstrained model recommendation instead of its best observed point; “LHS beats BO” dies under Holm; static arms secretly shared one design and LHS drew the luckiest of 60. The actual contribution that survived is **methodological**: the comparison criterion on the *classical* arm moves the verdict more than the optimizer does, and that is a field-level measurement, not a new algorithm. A second wave (Q42–Q52) tested generality, cost, multi-fidelity, noise, and identification — and **kept being wrong in the registered predictions**, which is the informative part.

---

## 2. What was built (methods)

### 2.1 Pipeline

```
instance (Hill oracle) → opening design → ask/tell campaign
        → surrogate (GP) or classical RSM
        → selected point → noiseless simple regret
```

| Layer | Where | What it does |
|---|---|---|
| Search space | `src/boec/space.py` | Coded [0,1]^d; six ECM labels; d=8 adds two dummy factors |
| Oracle | `src/boec/oracles.py`, `torch_oracle.py` | Biphasic Hill, peak-modulated (not product) interactions, planted `x*` |
| Evaluator | `src/boec/evaluators.py` | Phase 1 synthetic; Phase 2 lookup of digitized medians |
| Surrogate | `src/boec/surrogate.py` | Single-task GP, Matérn 5/2, ARD, fixed noise |
| Optimizers | `src/boec/optimizers.py` | qLogEI / qLogNEI + Sobol/LHS/random openings |
| Campaign | `src/boec/campaign.py` | Ask/tell loop, pending points, E3 logging |
| Runner | `src/boec/runner.py` | Grid over instances × seeds × methods |
| Classical arm | `src/boec/doe.py`, `rsm.py`, `designs.py` | Screen (~20) → face-centred CCD (~27) → 2nd-order fit → 1 confirm = 48 |
| E4 | `src/boec/e4.py`, `discrimination.py`, `parametric.py` | Fit in sub-box, optimize on extended box, over-prediction + Spearman vs \|poly error\| |
| Metrics | `src/boec/metrics.py` | Shared over-prediction at **constrained** argmax |
| Published data | `src/boec/published.py` | Digitization validation, canonical CSVs |

Person A owns oracle / space / evaluators / E2 / E3. Person B owns surrogate / campaign / optimizers / runner / E4 / metrics. Split is so the main result is not undebuggable by one person.

### 2.2 Oracle (the math)

Per factor: activating Hill × inhibitory Hill, peak-normalised so max = 1. Landscape is a weighted sum with exponential peak-modulation from other factors (the original multiplicative interaction was abandoned as unusable). Observations: `y = f(x)(1+ε) + η` with `σ_rel = 0.25` primary and `0.10` optimistic. Ensemble: 25 instances, committed under `data/oracles/biphasic-hill-v8+…/`.

Caveats already in the record:

- Landscape is ~93% additive — weaker interactions than the source study emphasises.
- Digitized stage-2 data: only **1/4** proteins show a resolvable interior peak; the oracle assumes **all** factors biphasic.
- `x*` range, `active_share = 0.90`, `γ` magnitude, and `r` bounds are design choices, not fitted.

### 2.3 Scoring rules (load-bearing — read this before any number)

| Rule | What it scores | Who uses it in the wild |
|---|---|---|
| **A** | Noiseless truth at the **best observed** point | E2 pre-registration; typical “best so far” |
| **C unconstrained** | Truth at the model’s recommended recipe, **anywhere** | What Q29 originally called “symmetric” |
| **C constrained** | Truth at the model’s recommendation **inside the explored region** | Classical RSM practice (ridge / canonical analysis) |

**91% of the E2 verdict swing is how the DoE arm is scored, not anything about BO.** Picheny et al. 2013 already named infill vs identification; this project *measures how much it moves a classical comparator*. Do not write it as a discovery of the distinction.

### 2.4 Registered experiments

| ID | Question | Owner |
|---|---|---|
| **E1** | Does BO beat random on Branin / Hartmann-6 / Ackley? Gate. | Shared |
| **E2** | Sample efficiency at budget 48: qLogEI, qLogNEI, random, Sobol, LHS, coord, sequential DoE | A |
| **E3** | Is the GP calibrated? Coverage / PIT / CRPS | A |
| **E4a** | Does a 2nd-order fit over-predict outside its box, and can a GP flag that? | B |
| **E4b** | Design-boundary variant (code only; no production grid) | B |
| **PF1–PF4** | Pre-flights: mechanism exists; inversion math; BoTorch traps; wall-clock | split |
| **Q-series** | Follow-ups after E2/E4. Numbered in `OPEN-QUESTIONS.md`. Two sessions collided on “Q29”; additive kernel is **Q30**. | mostly B |

Configs: `configs/experiment/e2.yaml`, `configs/experiment/e4.yaml`.

---

## 3. Timeline (what happened when)

| Day | Commits | What landed |
|---|---|---|
| **7 Aug** | 3 | Person B machinery (optimizer, E4, 255 tests). Person A day-1 Qs. Oracle port starts. Face-centred CCD settled. Docs were stale vs code; Cursor session synced them. |
| **8 Aug** | 9 | E4 first results: mechanism yes, headline null. Figures. Nested-CI bug. Adversarial audit. E4 v2: GP advantage only in indefensible regime. Shape-aware mean **negative**. Q13: A’s v8 oracle deviations **accepted**. |
| **9 Aug** | 0 | — |
| **10 Aug** | 38 | Gate 0. Sequential DoE arm. E1 (and the scoring bias that voided E2 runs 1–2). E2/E3 machinery. Runner bug: DoE cell ran BO (`e2a93aa`). **E2 COMPLETE: BO loses.** Q16–Q26 pre-regs. Hall/Ogle digitization rescued. |
| **11 Aug** | 27 | Q29 scoring crisis → Q30 additive kernel (accuracy ↑, regret unchanged). Hall/Ogle replay **claim not supported**. CLAIMS.md born. E2 grid committed. Q33–Q40. T1/T2 contribution reframe. |
| **12 Aug** | 21 | Q34 factorial: “BO wins under rule C” collapses under constrained argmax. Q42–Q49. `docs/RESULTS.md` standing record. Literature verification. |
| **13 Aug** | 11 + dirty tree | Q47 all three predictions wrong. Q50 design-averaged reversal. Hartmann6 d=8: BO wins, DoE screen at chance. Q52 identification floor **refutes itself**. Uncommitted: Q50 20-seed shards, d=8 DoE JSON, estimand-evaluation script. |

Stale remote branch: `origin/person-a/oracle-port`. Five stashes; E1/E2 WIP stashes are superseded.

---

## 4. Results — canonical numbers only

**Rule of this section.** Every number below traces to a committed (or named uncommitted) artefact. If two logs disagree, the **grid / later factorial** wins, not the chat.

### 4.1 E2 — the primary experiment (canonical)

**Source:** `results/e2-grid.json` + `results/e2.log` (A’s sharded run, merged 13 Aug). Locked by `tests/test_e2_provenance.py`.

**Registered primary: d=6, σ_rel=0.25, rule A, 25 instances × 2 seeds, paired.**

| arm | median regret | vs qLogEI | note |
|---|---|---|---|
| **doe** | **0.0957** | **−0.0595** [−0.0792, −0.0373] p=0.0000 | registered primary; Holm-exempt |
| lhs | 0.1271 | −0.0282 p=0.0147 | **fails Holm** (→ ~0.19); not a finding |
| qlognei | 0.1366 | −0.0020 | tie |
| coord | 0.1393 | −0.0133 | unpaired by design (random interior start) |
| **qlogei** | **0.1484** | — | |
| sobol | 0.1530 | +0.0171 | |
| random | 0.2308 | +0.0664 | BO’s only surviving win in this cell |

Instance-mean qLogEI is **0.1553**. The log prints **medians**; Q48/Q50 use **means**. Both are real. Mixing them is how people get confused.

Other cells, same grid:

- d=6 σ=0.10: DoE − qLogEI **+0.0018** (null). BO beats random/Sobol.
- d=8 σ=0.25: BO beats random/Sobol/coord. DoE was originally d=6-only in the grid; a separate d=8 DoE arm exists (`results/e2-doe-d8.log`, JSON currently **untracked**).
- d=8 σ=0.10: BO beats random; qLogNEI’s one “win” fails Holm.

**Void / do not quote as E2:**

| Artefact | Number it carries | Why dead |
|---|---|---|
| E2 runs 1–2 | DoE ahead by 0.0158 then unpaired | Q17 scoring + Q18 pairing (`fbb98e9`) |
| `results/e2-run1-unfiltered.log` | qLogEI median 0.1691, doe−qlogei **−0.0708** | B’s clone; gitignored grid (D12) |
| `results/doe-scoring.log`, `q29-symmetric*.log` | same −0.0708 family | B clone + old locator |

BO regeneration / determinism: `results/e2-bo-regeneration.json`, `e2-determinism.log` — max \|Δ\| = 0.0 **on this machine**. Cross-machine qLogEI is **not** bit-exact (0.1553 vs 0.1641). That is L7, not a bug in the report.

### 4.2 The scoring-convention result (the paper’s actual contribution)

**Current sources:** `results/q34-factorial.log`, `results/q35-constrained-rsm.log`. Q29 logs are superseded.

Primary cell, instance means:

| scoring | DoE | BO (qLogEI) | DoE − BO |
|---|---|---|---|
| Rule A (best observed) | 0.0958 | 0.1553 | **−0.0595** (DoE wins) |
| Rule C unconstrained | 0.4163 | 0.1232 | **+0.2931** (BO “wins”) |
| Rule C constrained | 0.1169 | 0.1232 | **−0.0063** (null, p≈0.56) |

Swing unconstrained vs constrained on DoE: **+0.2995**. Q34 registered primary cell5−cell3 = **−0.2171**. “BO wins under rule C” was scoring the classical arm the way its own literature warns against.

### 4.3 E3 — calibration

**Source:** `results/e3.log`. Latent coverage worst cell d=8 σ=0.25: **0.7644** vs nominal 0.95. Posterior-predictive coverage ~0.90–0.92. GP is miscalibrated on the latent; usable-ish for a lab predictive interval.

### 4.4 E4 — extrapolation over-prediction

**Sources:** `results/E4-RESULTS-v2.md`, `e4-rerun.log`. **Q19 still open** (pooled vs registered cell disagree in sign).

- DoE-style over-prediction pooled: **+1.103** [+1.024, +1.182] vs max response 1.0, **100/100 cells**. This is the robust finding.
- Unstaged DoE arm (`doe-arm.log`): 100% escape stage-2, 100% under-deliver, saddle 20/20.
- GP vs nearest-neighbour discrimination: **pooled −0.0269** (no advantage); **registered cell κ=0.6, ρ=2.0: +0.1068** (GP better). Do not print the pooled figure as “pre-registered primary.”
- Shape-aware mean: **negative** (made extrapolation worse).
- PF1 ρ-trend: **void** (D3 — nested boxes make it tautological).

### 4.5 Surrogate ≠ regret (Q30)

**Source:** `results/q30-additive.log`, `bench-surrogate.json`. Additive kernel roughly doubled held-out R² at low noise (0.375 → 0.744 at σ=0.10). **Regret vs product qLogEI: −0.0106, p=0.381 at the primary cell.** Accuracy was not the binding constraint. Registered prediction was wrong; that is the result.

### 4.6 Generality (Q36 / Q42 / Hartmann6 d=8)

**Source:** `results/q42-families*.log`, `q42-families-rerun.log`.

- Levy + Rosenbrock: scoring reversal in **8/8** cells (Hill-like).
- Hartmann6: **BO wins all four cells** (d=6 σ=0.25 rule A: BO 0.2984 vs DoE 0.5444).
- Ackley: **VOID** (optimum at box centre; DoE rule A = 0).
- Hartmann6 d=8 screen: **2.96 / 4** active slots (chance = 3.00) — DoE screening is at chance on a genuinely coupled landscape.

**Which method wins is a property of the landscape.** “BO loses” does not generalise. “Saddle always” does not either (103/350 maxima on test families, concentrated in Ackley).

### 4.7 Multiplicity (Q39)

39 non-primary contrasts, Holm. Casualties: all LHS “wins,” qLogNEI’s one significant cell. **DoE vs qLogEI at the registered primary is exempt and stays p=0.0000.**

### 4.8 Static-design luck (Q48 / Q50)

E2’s static arms (LHS, Sobol, random) shared **one design per seed across 25 instances**. LHS’s reported 0.1270 was the **0th percentile of 60 draws**; design-averaged LHS is **0.1752**. qLogEI design-averaged (20 campaign seeds, uncommitted merge) **0.1532** (SD 0.0102). Ordering **reverses**: reported LHS ahead by 0.028; design-averaged BO ahead by **~0.022**.

⚠️ The paired Wilcoxon +0.0219 / p=1.8×10⁻⁵ / 21-of-25 **cannot currently be regenerated** from committed artefacts (`run_q48_design_variance.py` collapses per-instance rows). Point estimates are real; the paired test is a D12-class provenance hole. Shards `q50-qlogei-g08.json`…`g19.json` are untracked.

### 4.9 Thresholds (Q47, Q49, Q52)

- **Q47 multi-fidelity:** 4800 runs. All **three registered predictions wrong.** Screen pays from cost-ratio ~0.26–0.32 at 10:1, not where predicted.
- **Q49 noise curve:** “no method finds anything above CV X” is **false**. 48→192 assays still helps at σ=0.25 (+0.0384, CI excludes 0). Identification (not search) is ~61% of remaining regret at n=192.
- **Q52 identification floor:** registered as a universal bound; **refuted the same day**. Flatten curve only **12/25 instances** (incomplete). Uncommitted `scripts/estimand_evaluation.py` shows rule A on a space-filling design **gets worse with more budget** past n=24 (order-statistic of noise), and the registered budget 48 is already at/above that crossover for static designs.

### 4.10 Hall/Ogle Phase 2 replay

**Source:** `results/replay-hall-ogle.log`. Stage 2: BO not faster than random, p=0.8746. **Published “BO would have found it cheaper” is not supported** on the digitized table. Digitised pixels, not author tables. Collagen IV coded +1.40 (20% above highest tested) is **our inference**, needs a statistician before it is a headline. Figs 3–5 extraction not done.

### 4.11 E1

Hartmann6 BO − random **+1.0847**. Gate passed. Real payload: exposed the noisy-best-so-far scoring bug that voided E2.

---

## 5. What the evidence supports vs what it does not

`docs/CLAIMS.md` is still a **draft for A and Alan to cut**. Until that cut, treat this table as the working filter.

**Supportable (survived checks):**

1. Published-style two-stage DoE over-promises massively (E4 + DoE arm).
2. That failure is unconstrained extrapolation, not a boundary-clamp artefact.
3. At the registered E2 primary (rule A, d=6, σ=0.25), sequential DoE beats qLogEI.
4. The verdict is dominated by how DoE is scored (Q34/Q35); constrained rule C nulls the reversal.
5. Fitted quadratics are saddles **on biphasic landscapes**, not on all landscapes.
6. Better GP R² does not move regret (Q30).
7. GP latent coverage is below nominal (E3).
8. Static-arm rankings in E2 are design-conditioned, not design-averaged (Q48).
9. Nothing has been run on cells.

**Do not claim:**

- “BO beats current practice.”
- “Our BO is more sample-efficient.”
- “LHS beats BO” (Holm + Q50).
- “BO loses everywhere” (Hartmann6).
- E4 pooled “no GP advantage” as the pre-registered primary (Q19).
- “~93% additivity explains the κ sign flip” (Q22 refuted).
- Q52 universal identification floor (refuted).
- Wet-lab / endothelial-trained model.

**Wrong registered predictions (keep them; they are the audit trail):** at least twelve, including Q30, Q47×3, Q52 floor, PF1 ρ-trend, E4 headline-as-pooled, “essentially always a saddle.”

---

## 6. Tests (what is locked in code)

~28 test modules; suite was 422 passing at the RESULTS-PERSON-A write-up (233 B). Load-bearing ones:

| Test | What it prevents happening again |
|---|---|
| `tests/test_e2_provenance.py` | Quoting −0.0708; gitignoring the grid; conflict markers; log ≠ grid |
| `tests/test_q29_locator.py` | Two different argmax locators (256 vs 4096) |
| `tests/test_metrics.py` | Constrained-argmax / over-prediction correctness |
| `tests/test_q34_factorial.py` | Factorial structure of the estimand experiment |
| `tests/test_embedded_oracle.py` | Hartmann6 d=8 embedding |
| `tests/test_identification.py` | Q52 machinery |
| `tests/test_lengthscale_diag.py` | Q25 permutation null (guards D8) |

Conversation-start dirty files (`q29_rescore.py`, `test_e2_report.py`, metrics edits) are **not in the current tree**. That work either landed or was abandoned; do not hunt those filenames as current WIP.

---

## 7. What is yet to be done

The project has left “build and run” and is in **lock estimands, fix provenance, cut claims, write paper.**

### Decisions (block the paper)

| ID | Decision | Owner |
|---|---|---|
| **Q19** | E4 headline = registered cell (GP better +0.107) or pooled (no advantage −0.027)? | A + Alan |
| **Q28 / Q41** | Headline estimand: rule A vs unconstrained C vs constrained C. A chose unconstrained argmax as *primary DoE scoring* in OPEN-QUESTIONS; CLAIMS blocking table still lists Q28 open. Sync them. | A / Alan |
| **T15 / Q27** | Accept the d=8 DoE split (numbers exist, ~−0.0321 at σ=0.25). | A |
| **Q23** | Confirm `coord` is intentionally unpaired. | A |
| **Q7** | Author order; public release of code + digitized data. | Alan |
| **CLAIMS.md** | Cut the draft. Nothing in it is settled until then. | A + Alan |

### Provenance / commit hygiene (do this first, cheap)

1. Fix Q50 paired stats: retain per-instance regrets; commit a script that reproduces +0.0219 or stop quoting it.
2. Commit `results/e2-doe-d8.json`, Q50 shards g08–g19, expanded `q50-qlogei-seedsweep.json`, `.gitignore` exceptions.
3. Commit or drop `scripts/estimand_evaluation.py` + `results/estimand-evaluation.log`.
4. Write the Q51 RESULT entry (Hartmann6 d=8 log exists; OPEN-QUESTIONS still says “registered”).

### Experiments registered but unfinished

| Item | Status |
|---|---|
| Q52 §2–§3 budget-to-target curves | Not started |
| Q52 flatten | 12/25 instances |
| Q50 paired recompute | Blocked on script |
| E4b production grid | Code only |
| E1 on the Hill oracle (T7) | Still Branin/Hartmann/Ackley only |
| PF4 on the real biphasic oracle | Timed on Hartmann6 stand-in |
| Q15 `stage2_half_width` sweep | Only 0.25 |
| d=6 @ n_init=18 (unconfound dimension) | Not proposed/run |
| Q46 / Paper 2 | Registered, not active until Paper 1 |
| Hou 2017 secondary replay | Not seen |
| Phase 2 GP vs polynomial interval at TheO | Not evidenced |
| Figs 3–5 Hall/Ogle extraction | Not done |
| Literature: Picheny full text, Narayanan “estimated DoE”, Bull/Berk | Do not cite as verified |

### Docs that are stale (do not trust them for status)

`docs/team_build_plan.md`, `START-HERE-PERSON-A.md`, `docs/TASKS.md` Gate 2, parts of `person_b_spec.md` still talk as if the oracle is blocked and E2 unrun. **Trust:** `RESULTS.md`, `RESULTS-PERSON-A.md`, `OPEN-QUESTIONS.md`, this file.

### Paper write-up (when estimands lock)

Lead with the scoring-convention *measurement* on a classical comparator, not “BO loses.” Report all three DoE scorings. Design-average static arms or strike their ordering. Print the E4 κ-dependent surface and the Q19 choice. Defect register (D1–D17) in the supplement. Title must not promise cells.

---

## 8. Data-quality map (why Claude gets confused)

1. **Two numbering systems.** Close-out brief Q-numbers ≠ this repo. Concordance is at the top of `OPEN-QUESTIONS.md`.
2. **Two E2 grids, one filename (D12).** Canonical = committed `e2-grid.json` (−0.0595). B clone = −0.0708. Three “independent” recomputes were one compute.
3. **Median vs mean.** 0.1484 vs 0.1553 for qLogEI at primary. Same run.
4. **Superseded logs still on disk.** `q29-symmetric*`, `doe-scoring.log`, `e2-run1-unfiltered.log`.
5. **Missing logs** for some JSONs (`q29-rescore.json` has no `.log` in the current tree).
6. **Q29 number collision.** Symmetric scoring kept Q29; additive kernel is Q30.
7. **Parallel sessions** nearly duplicated Q29. Convention (claim a number *before* work) is flagged for Alan and not implemented.
8. **Uncommitted 13 Aug work** is Q50 completion + estimand evaluation, not the conversation-start Q29-rescore files.
9. **Chat logs do not contain the experimental week.** Cursor transcripts: 7 Aug docs + 13 Aug recap. Experiments are git.

---

## 9. Canonical file map

```
READ FIRST     docs/WEEK-RECAP-2026-08-13.md   (this file)
INDEX          docs/RESULTS.md
A LANE         docs/RESULTS-PERSON-A.md
DECISIONS      docs/OPEN-QUESTIONS.md
CLAIMS DRAFT   docs/CLAIMS.md          ← not settled
METHODS        docs/METHODS.md
ORACLE AUDIT   docs/oracle_defensibility.md

CANONICAL E2   results/e2-grid.json + results/e2.log
ESTIMAND       results/q34-factorial.log + results/q35-constrained-rsm.log
DESIGN LUCK    results/q48-design-variance.log + q50 (20/20 shards, all committed)
DO NOT QUOTE   results/e2-run1-unfiltered.log
               results/doe-scoring.log
               results/q29-symmetric*.log
```

---

## 10. Questions for Alan / A (please answer)

These are the things a later session cannot infer from the repo:

1. **Which results are “the paper”?** Working proposal: (a) DoE over-promise, (b) E2 primary DoE>BO under rule A, (c) scoring-convention swing and its disappearance under constrained C, (d) landscape-dependence (Hartmann6), (e) static-arm design luck. Everything else is supplement / negative. Confirm or rewrite the list.
2. **Q19:** print the E4 registered cell, the pooled figure, or both as a surface?
3. **Headline estimand:** keep rule A as E2 primary (already pre-registered) and treat Q34/Q35 as the explanation — yes?
4. **Q50 paired p-value:** quote the point estimate only until the script exists, or delay the design-averaged claim?
5. **Person A:** accept d=8 DoE split? confirm `coord` unpaired?
6. **Q7:** author order and whether digitized Hall/Ogle figures can be released with the code?

Until those are answered, a later Claude should **not** invent a paper narrative. It should point at this file and `OPEN-QUESTIONS.md`.
