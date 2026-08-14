# Methods and results — one record

**What this file is.** The paper-facing summary. Every table below is a result. The sentence under it is what that result means. Methods are stated only as far as they explain the table.

**Repo:** `nutrigene-ai-bo-ipsec` · 7–14 Aug 2026 · 146 commits · no manuscript yet.

**Where numbers live.** This file. If another doc disagrees, this file and the named `results/*.json` win. Audit trail: `docs/RESULTS.md`. Paper skeleton: `docs/MAIN-LINE.md`.

Charts for the same numbers: open the results canvas beside chat.

---

## The answer in six sentences

1. This is a **math benchmark**, not a cell experiment. The ground truth is a Hill function we built. Hall/Ogle 2025 gave us labels, a 6→4 screen, and 47 digitized box-plot medians. No wet-lab BO result exists.
2. At a noisy assay, scored on the **best well already measured** (rule A), classical DoE beats BO by **0.0595**.
3. Scored on each method’s **model recommendation anywhere in the box** (rule C unconstrained), BO beats DoE by **0.27 to 0.36**. Keep that recommendation inside the explored region and the BO win mostly vanishes.
4. About **90%** of that swing is how DoE is scored, not anything BO does. The fitted quadratic is a saddle in 200/200 runs.
5. We cannot claim BO needs fewer experiments. There is **no savings ratio**. At a quiet assay BO **arrives more often** (24/25 vs 13/25), **cheaper in wells** (32 vs 48), **slower in rounds** (6 vs 3). A one-shot spread+GP matches that arrival in **1 round**. At the realistic assay the arrival-rate difference disappears.
6. Closest prior work: **Rummukainen et al. 2024**. Cite it in the framing.

---

## 1. Data — endothelial cells or math?

**Math.** We did not train on endothelial measurements. We did not optimize live cells.

| Layer | What it is | Used for the BO-vs-DoE claims? |
|---|---|---|
| **Phase 1** | Fake Hill landscapes. Known best value = 1.0. Parameters drawn at random from ranges we chose. | **Yes.** Almost every experiment. |
| **Phase 2** | 47 usable condition medians digitized from Hall, Lin & Ogle 2025 Figs 1a/2a. CD31/DAPI. | **Three scripts only.** Replay was null. The assay cannot resolve a method difference (MDE 0.68). |
| **Phase 3** | Real in-house iPSC→EC flow files (`data/lab/`). | **No.** CD31 `y` is empty. Optimizer refuses unsigned numbers. The 12-point coating scan cannot carry a Phase 3 figure. |

Paper one-liner: *a synthetic benchmark whose search-space labels and screening structure come from a published iPSC→endothelial ECM study.* Do not write “validated on cells.”

The oracle is not fitted to the figures. Peak range, interaction strength, and “all factors biphasic” are design choices. Digitized stage-2 data resolves an interior peak on **1 of 4** proteins; the oracle assumes all of them.

---

## 2. Method — what we ran, and why the grid exists

```
recipe x  →  fake quality f(x)  →  noisy measurement y = f(x) + noise
                ↓
     method spends a budget of wells and then names one recipe
                ↓
     score = 1.0 − true (noiseless) quality of that named recipe
             = regret. Lower is better. 0 = it named the true peak.
```

The method never sees `f`. It only sees noisy `y`. The score never uses `y`. That split is the whole point of Q17: if you score on the noisy reading, a lucky noise draw looks like a good recipe.

### 2.1 The four cells — what d and σ are

We did not run one condition and then mention the others in passing. The registered grid is **2 × 2**:

| | **σ = 0.25** (noisy / “realistic” assay) | **σ = 0.10** (quiet / optimistic assay) |
|---|---|---|
| **d = 6** (six factors) | **Primary cell.** Locked in Q20 *before* E2 finished. | Sensitivity: what if the assay is cleaner? |
| **d = 8** (eight factors) | Same biology-shaped landscape plus two empty axes. | Same, at the quiet assay. |

**What d is.** `d` is the number of recipe factors the method is allowed to change, each scaled to the unit box `[0, 1]`.

- **d = 6** matches Hall/Ogle’s six ECM proteins. In the code the axes are `x0…x5`. The labels (Collagen I, IV, …) are names only; the Hill function is not fitted to those proteins.
- **d = 8** is not “a more complete medium.” It is the **same** 4-active / 4-kept screening structure with **two extra inert axes** that do nothing to `f`. That isolates the cost of extra empty dimensions. It is not extra biology.

**What σ is.** `σ` is relative Gaussian noise on the measurement. Larger σ = a sloppier assay = harder to tell a good well from a lucky well.

- **σ = 0.25** is the registered noisy assay. It is still about **2.7× quieter** than the coefficient of variation implied by the Hall/Ogle box plots (~68%). We are not simulating their instrument; we are simulating a cleaner version of it.
- **σ = 0.10** is the optimistic assay. Methods that need to read a smooth surface (GPs, quadratics) get an easier job. This cell exists so we can say whether a result is noise-driven.

**Why both, not one.** A method that only wins when the assay is quiet is not a method a noisy CD31 assay can use. A method that only wins at six factors may be winning because the screen is well-matched to six proteins, not because the optimiser is better. The four cells exist to stop those two stories being smuggled in.

**Replication inside each cell.** 25 independent landscapes (instances) × 2 random seeds = **50 rows**. Pairing is at the landscape: same 25 fake media, both methods, then the 25 differences. The two seeds are averaged first. n for a Wilcoxon or a bootstrap interval is **25**, not 50.

**Budget.** 48 wells, unless a later experiment (Q52) raises the cap to 200. 48 is not a round number we liked. It is the published pipeline: 20-run screen + 27-run face-centred CCD + 1 confirm = 48. BO is given the **same well count** so the comparison is not “BO used more experiments.”

### 2.2 Two bills

A lab pays twice.

| Bill | Unit | What it is |
|---|---|---|
| **Cost** | wells (evaluations) | How many recipes you actually ran. |
| **Time** | rounds | How many plate cycles: choose wells → incubate → read → then choose the next set. |

A 48-well one-shot Latin hypercube costs 48 wells and **1 round**. The same 48 wells as BO with opening 14 then batches of 4 costs 48 wells and **10 rounds**. Those are not the same experiment in a hood.

### 2.3 Arms — what each method actually does

Headline comparison is **qLogEI vs doe**. Everything else is a control.

| Arm | What it does | Wells at budget 48 | Rounds at that budget | In which experiments |
|---|---|---|---|---|
| **qLogEI** (BO) | Gaussian process + batch log expected improvement. Opening **14** (= 2d+2 at d=6), then batches of **4**. | 48 | **10** | E2, Q27, Q34, Q42, Q52, Q53 |
| **doe** | Published pipeline. Stage 1: 20-run screen, keep 4 factors. Stage 2: 27-run face-centred CCD on those 4. Stage 3: 1 confirmation at the fitted peak. | 48 | **3** | E2, Q27, Q34–Q35, Q42, Q52 |
| **spread_gp** | One Latin hypercube of size n, one GP fit, pick the GP’s best guess. No adaptive rounds. | n (one shot) | **1** | Q52, Q53 — **not in E2** |
| **LHS / Sobol / random** | Space-filling or uniform. No model. Score = best measured well. | 48 | 1 | E2 |
| **qLogNEI** | Same BO loop, different acquisition (noisy EI). | 48 | 10 | E2 only. Not the headline. |
| **coord** | Coordinate descent. | 48 | (sequential) | E2 only. Q23: unpaired. Not the headline. |

**DoE does not walk the design.** There is no steepest-ascent / ridge-follow stage after the CCD. That is a bias **toward BO** on any “how many wells until you arrive” question. Write it next to every Q52 number.

**spread_gp is not LHS.** E2’s `lhs` arm reports the best well it measured. Q52’s `spread_gp` fits a GP on the same kind of spread and reports the GP’s favourite point. Different scoring, different arm.

### 2.4 Scoring — three ways to name the recipe

Every number in this file is **true noiseless quality of one named recipe**, written as regret `1 − f(x*)`. The rules differ only in **which** `x*` is named.

| Rule | Chosen recipe | Lab translation | Who can use it |
|---|---|---|---|
| **A** | The well already measured whose **true** value is best | What you send forward if you trust the data you already have | Every arm |
| **C unconstrained** | The fitted model’s favourite point, **anywhere in the box** | What the surface tells you to try next, including outside the region you explored | Arms with a model (DoE quadratic, BO GP, spread_gp) |
| **C constrained** | The fitted model’s favourite point **inside the explored region** | Classical practice when the stationary point sits outside the design (ridge analysis) | Same |

Locked **Q41**, before the factorial was treated as a paper result: **unconstrained is the primary rule-C version.** Constrained is always sitting next to it. Reason: the source study’s polynomial recommendation is the unconstrained argmax, and that is the scoring the DoE-versus-BO literature actually disagrees about.

E2’s JSON stores rule A only (`regret` = best observed). Rule C for DoE vs BO comes from Q34 (unconstrained polynomial / GP) and Q35 (constrained polynomial). There is **no** rule C for LHS, Sobol, random, or coord on the Hill oracle.

**D20 correction, applied everywhere below.** An earlier DoE “best observed” was secretly the oracle’s best point on the whole design, not the best measured well. That made DoE look better than rule A. Rescored in `results/d20-rescore.json`. Use **0.0958** at the primary cell, not 0.0597. Q42 family tables below use the D20 rule-A column. Rule C was never affected.

### 2.5 How we test — what the p-value is for, and what it is not

Three tools, three jobs. They are not interchangeable.

| Tool | Job | What a “win” means |
|---|---|---|
| **Wilcoxon signed-rank** on the 25 paired landscape differences | Yes / no: is the sign of the difference systematic? | p small ⇒ not a coin flip. Says nothing about *how much*. |
| **Instance bootstrap** (resample the 25 landscapes) | Size: mean difference and a 95% interval | The number we quote in a sentence. Interval covering 0 = **null**, even if the means look apart. |
| **Holm** | Multiplicity: several arms vs qLogEI in one cell, or several arrival targets in Q52 | A raw p that dies under Holm is **not** a result. E2’s LHS-beats-BO at the primary cell dies. Q52’s quiet-assay target 0.10 survives. |

Sign convention in every contrast table below: **DoE − BO**. Negative = DoE has lower regret = DoE wins. Positive = BO wins. Zero in the interval = tie.

### 2.6 Why each experiment was run

E2 alone cannot support the sentences we want to write. Each later ID exists because a specific confound or objection was still open.

| ID | Question it answers | What it holds fixed | What it changes |
|---|---|---|---|
| **E1** | Does BO work at all? | Standard test functions | BO vs random |
| **E2** | At 48 wells, who wins on the Hill oracle? | Landscapes, budget, rule A | The arm |
| **Q27** | Same question at **d = 8**. E2’s grid had no d=8 DoE rows, so a glance at that file looked like a BO win at eight factors. | Same as E2 | Adds the missing `doe` arm (`results/e2-doe-d8.json`) |
| **Q17 / Q20 / Q41** | What is the score, and which cell is primary? | Locked *before* treating E2 as a result | Scoring rule; primary = d=6, σ=0.25, n=25, budget 48 |
| **Q28 / Q34** | Is the E2 reversal “the model,” “the points,” or “the scoring rule”? E2 changes all three at once. | Same 48 wells, same landscapes | 2×2 of (DoE design vs BO design) × (polynomial vs GP), plus rule A vs rule C |
| **Q35** | On the *same* DoE fit, what happens if we score the unconstrained peak vs the peak inside the region vs the best well? | The fitted quadratic | The locator |
| **Q45** | Q34’s polynomial-on-BO-points used six factors; DoE’s polynomial used four. Was the “design effect” just that confound? | Both polynomials on the **same four kept factors** | Design only, then model only |
| **Q42** | Is “how you score DoE changes the winner” a quirk of our Hill function? | Same pipeline, same four cells | Swap the oracle for Levy, Rosenbrock, Hartmann6, Ackley |
| **Q52** | Never mind a fixed 48. When does each method first hit a quality target, in wells and in rounds? | d=6 only, cap 200 | Budget, target, σ. **d=8 was not run.** |
| **Q53** | On Hill, one-shot spread+GP tied 10-round BO. Is that Hill-only? | Same well count | Q42’s families; five design draws |

E1, E3, Q21–Q26, Q30, Q33, Q37–Q39, Q43–Q44, Q48–Q50, PF1–2 are defence. They are in §3.7, not the headline.

### 2.7 Cost / time reconstruction (Q52)

Rounds were **not stored** per landscape. The JSON has regret at evaluation checkpoints only. Rounds were rebuilt from those checkpoints using the runner that produced the grid (commit `633e74d`):

| Arm | Opening | After that | Mid-batch / partial |
|---|---|---|---|
| qLogEI | 14 wells = round 1 | batches of 4 | a half-finished batch **pays for the whole plate**. Formula: `1` if n≤14, else `1 + ceil((n−14)/4)` |
| DoE | 20 + 27 + 1 = 48 | the whole pipeline repeats at 48, 96, 144, 192 | a partial pipeline is **not the method**. Rounds = `3 × (n // 48)` |
| spread_gp / random | n wells in one shot | none | **1 round at any n** |

File: `results/q52-rounds-to-arrival.json`. This is reconstructed, not logged. Do not write “we recorded 6 rounds.”

---

## 3. Results — each method, then its number

How to read this section. Each subsection is: **why we ran it → the full grid, not a slash of four numbers → what that grid means.** Primary cell is always **d=6, σ=0.25**. The other three cells are not footnotes; they are the test of whether the primary cell generalises.

### 3.1 Fixed budget 48: who wins depends on the scoring rule

**Why this was run.** E2 is the thesis test: same 48 wells, same 25 landscapes, seven arms, score the recipe each method would actually send forward. Q27 exists because without a d=8 DoE arm you cannot say who wins at eight factors — the E2 file simply had no `doe` rows there. Q34/Q35 exist because E2 only stored rule A; the model-recommendation numbers are a different recipe on the same runs.

**What is held fixed.** Budget 48. 25 landscapes × 2 seeds. Hill oracle. Pairing at instance.

**What changes.** The arm (E2), then only the named recipe (rules A / C unconstrained / C constrained).

#### Scoring grid — DoE vs qLogEI, all four cells

Means are over 50 rows. Contrasts are paired at 25 landscapes (seeds averaged first). Sign: **DoE − BO**. Negative = DoE wins.

**Rule A — best well already measured.**

| Cell | What this cell is | DoE regret | BO regret | DoE − BO | p (Wilcoxon) | Winner |
|---|---|---|---|---|---|---|
| **d=6, σ=0.25** | **Primary.** Noisy assay, six factors. | **0.0958** | 0.1553 | **−0.0595** [−0.0792, −0.0373] | 2.2×10⁻⁵ | **DoE** |
| d=6, σ=0.10 | Quiet assay, six factors. | 0.0892 | 0.0874 | **+0.0018** | 0.69 | **tie** |
| d=8, σ=0.25 | Noisy assay, two extra empty axes. | 0.0963 | 0.1247 | **−0.0284** | 0.0023 | **DoE** (gap halved vs primary) |
| d=8, σ=0.10 | Quiet assay, eight factors. | 0.0948 | 0.0972 | **−0.0024** | 0.43 | **tie** |

`RESULTS.md` printed the last contrast as +0.0015 [−0.0103, +0.0140]. Re-aggregation from `e2-grid.json` + `e2-doe-d8.json` gives −0.0024. Both intervals cover 0. The winner is a tie either way. This file follows the JSON.

**Rule C unconstrained — model’s favourite point, anywhere.** From Q34 cells 3 (DoE polynomial) and 4 (BO GP).

| Cell | DoE regret | BO regret | DoE − BO | Winner |
|---|---|---|---|---|
| **d=6, σ=0.25** | 0.4163 | **0.1232** | **+0.2931** | **BO** |
| d=6, σ=0.10 | 0.4300 | **0.0703** | **+0.3597** | **BO** |
| d=8, σ=0.25 | 0.3766 | **0.1056** | **+0.2710** | **BO** |
| d=8, σ=0.10 | 0.4104 | **0.0876** | **+0.3228** | **BO** |

All four p < 10⁻⁷. BO wins every cell, and the gap is *larger* at the quiet assay.

**Rule C constrained — model’s favourite point inside the explored region.** DoE from Q35; BO’s GP recommendation is already inside its sampled region in this setup, so BO’s two rule-C columns match.

| Cell | DoE constrained | BO | DoE − BO | Winner |
|---|---|---|---|---|
| **d=6, σ=0.25** | 0.1169 | 0.1232 | **−0.0063** | **null** |
| d=6, σ=0.10 | 0.0856 | 0.0703 | **+0.0153** | small BO win |
| d=8, σ=0.25 | 0.1148 | 0.1056 | **+0.0091** | **null** |
| d=8, σ=0.10 | 0.0877 | 0.0876 | **+0.0001** | **null** |

Three nulls, one small BO win at the quiet six-factor cell.

**Same numbers, one row per cell, so the reversal is visible without arithmetic.**

| Cell | Rule A winner | Rule C unconstrained winner | Rule C constrained winner |
|---|---|---|---|
| d=6 σ=0.25 primary | DoE by 0.0595 | BO by 0.2931 | null |
| d=6 σ=0.10 | tie | BO by 0.3597 | BO by 0.0153 |
| d=8 σ=0.25 | DoE by 0.0284 | BO by 0.2710 | null |
| d=8 σ=0.10 | tie | BO by 0.3228 | null |

**What it means.** If a lab reports the best well it already ran, DoE wins at the realistic assay and the two methods tie when the assay is quiet. If a lab reports the point its model likes, and lets that point sit outside the explored region, BO wins by a large margin in every cell. Keep that point inside the region and the BO win is gone in three of four cells. Classical textbooks already warn against the unconstrained move (ridge analysis). We measured the warning. The dimension effect under rule A is the **size of the gap**, not who wins: DoE is still ahead at d=8 σ=0.25, by about half.

#### All seven E2 arms, rule A only

These are controls. They answer “is qLogEI at least beating a dart throw?” and “did LHS get lucky?” They are **not** a DoE-vs-BO scoring comparison — there is no rule C for them.

Mean regret. Contrast = arm − qLogEI. Negative = that arm beats BO.

**d=6, σ=0.25 (primary).**

| Arm | Mean regret | vs qLogEI | p | After Holm |
|---|---|---|---|---|
| **doe** | **0.0958** | **−0.0595** | 2.2×10⁻⁵ | **DoE wins** |
| lhs | 0.1270 | −0.0282 | 0.015 | **dies** — not a result |
| coord | 0.1420 | −0.0133 | 0.34 | tie |
| qlognei | 0.1532 | −0.0020 | 0.71 | tie |
| **qlogei** | 0.1553 | — | — | — |
| sobol | 0.1724 | +0.0171 | 0.31 | tie |
| random | 0.2216 | +0.0664 | 3.8×10⁻⁵ | BO beats random |

qLogEI’s only surviving win in this cell is over random. Sequential DoE is the only arm that beats it after Holm.

**d=6, σ=0.10 (quiet, six factors).**

| Arm | Mean regret | vs qLogEI | p | Call |
|---|---|---|---|---|
| qlognei | 0.0808 | −0.0066 | 0.18 | tie |
| **qlogei** | 0.0874 | — | — | — |
| coord | 0.0880 | +0.0006 | 0.92 | tie |
| doe | 0.0892 | +0.0018 | 0.69 | tie |
| lhs | 0.1027 | +0.0153 | 0.11 | tie |
| sobol | 0.1210 | +0.0336 | 0.00033 | BO better |
| random | 0.1693 | +0.0819 | 6×10⁻⁷ | BO better |

**d=8, σ=0.25 (noisy, eight factors).**

| Arm | Mean regret | vs qLogEI | p | Call |
|---|---|---|---|---|
| **doe** | **0.0963** | **−0.0284** | 0.0023 | **DoE wins** |
| qlognei | 0.1105 | −0.0142 | 0.17 | tie |
| **qlogei** | 0.1247 | — | — | — |
| lhs | 0.1627 | +0.0380 | 0.019 | BO better (raw) |
| random | 0.1712 | +0.0465 | 1.8×10⁻⁵ | BO better |
| sobol | 0.1804 | +0.0557 | 0.00063 | BO better |
| coord | 0.1926 | +0.0679 | 1.1×10⁻⁶ | BO better |

**d=8, σ=0.10 (quiet, eight factors).**

| Arm | Mean regret | vs qLogEI | p | Call |
|---|---|---|---|---|
| qlognei | **0.0849** | **−0.0123** | 0.027 | qLogNEI beats qLogEI (acquisition, not paradigm) |
| doe | 0.0948 | −0.0024 | 0.43 | tie |
| sobol | 0.0968 | −0.0004 | 0.94 | tie |
| **qlogei** | 0.0972 | — | — | — |
| coord | 0.1053 | +0.0081 | 0.33 | tie |
| lhs | 0.1260 | +0.0288 | 0.0067 | BO better |
| random | 0.1272 | +0.0301 | 0.00043 | BO better |

**What the all-arm tables add.** At the quiet assay the top four methods (qLogNEI, qLogEI, coord, doe) are indistinguishable at both dimensions. The interesting movement at low noise is **which acquisition function**, not DoE vs BO. At the noisy assay, DoE is ahead at both dimensions and space-filling without a model is behind. LHS’s apparent win at the primary cell is the one Holm kills.

Files: `results/e2-grid.json`, `results/e2-doe-d8.json`, `results/q34-factorial.json`, `results/q35-constrained-rsm.json`, `results/d20-rescore.json`.

### 3.2 The swing is DoE’s scoring, not BO

**Why this was run.** A reader who only sees “DoE wins under A, BO wins under C” can still believe both methods moved. Q35 scores **the same DoE fit** three ways. Subtracting rule A from rule C on each arm, on the same runs, says which arm actually changed.

**What is held fixed.** The 48 wells already collected. The fitted surfaces.

**What changes.** Only the locator: best measured well vs unconstrained model peak vs constrained model peak.

#### Scoring change, all four cells

Change = rule C unconstrained − rule A. Positive = the model recommendation is *worse* than the best well already in hand.

| Cell | DoE rule A | DoE rule C unc. | DoE change | BO rule A | BO rule C | BO change | Share that is DoE |
|---|---|---|---|---|---|---|---|
| **d=6 σ=0.25** | 0.0958 | 0.4163 | **+0.3205** | 0.1553 | 0.1232 | **−0.0321** | **~90%** (~10:1) |
| d=6 σ=0.10 | 0.0892 | 0.4300 | **+0.3408** | 0.0874 | 0.0703 | −0.0171 | ~95% |
| d=8 σ=0.25 | 0.0963 | 0.3766 | **+0.2803** | 0.1247 | 0.1056 | −0.0191 | ~94% |
| d=8 σ=0.10 | 0.0948 | 0.4104 | **+0.3156** | 0.0972 | 0.0876 | −0.0096 | ~97% (~33:1) |

The GP’s recommendation is **better** than the best well it already measured, in every cell: 0.1232 vs 0.1553 (21% better), 0.0703 vs 0.0874 (20%), 0.1056 vs 0.1247 (15%), 0.0876 vs 0.0972 (10%).

#### Why the quadratic explodes: it is a saddle

Q35 classifies the stationary point of the fitted second-order surface.

| Cell | Saddle | Interior maximum |
|---|---|---|
| d=6 σ=0.25 | **50 / 50** | 0 |
| d=6 σ=0.10 | **50 / 50** | 0 |
| d=8 σ=0.25 | **50 / 50** | 0 |
| d=8 σ=0.10 | **50 / 50** | 0 |

**200 / 200.** A saddle has no interior maximum, so the unconstrained “optimum” is forced onto a boundary. Unconstrained minus constrained at the primary cell: **+0.2995** [+0.2790, +0.3228]. Most of DoE’s rule-C failure is the escape from the region actually explored.

#### After D20: is the polynomial worse than its own data?

That is constrained rule C minus rule A, with rule A scored correctly (best measured well, not oracle-best).

| Cell | Constrained − rule A | Call |
|---|---|---|
| d=6 σ=0.25 | **+0.0211** [+0.0105, +0.0315] | polynomial worse than its data |
| d=6 σ=0.10 | −0.0036 [−0.0122, +0.0049] | **null** |
| d=8 σ=0.25 | **+0.0185** [+0.0094, +0.0287] | polynomial worse than its data |
| d=8 σ=0.10 | −0.0071 [−0.0150, +0.0008] | **null** |

**What it means.** Write the contribution as: the DoE-versus-BO literature is split, and a large part of the split is an unregistered scoring convention on the classical arm. The GP, scored the same way, gets slightly better. “Polynomial worse than its data” is a **noisy-assay** claim only. Do not write it as always.

Files: `results/q34-factorial.json`, `results/q35-constrained-rsm.json`, `results/d20-rescore.json`.

### 3.3 Not only the model, not only the points

**Why Q34 was run.** E2 compares (structured design + polynomial + rule A) to (adaptive design + GP + rule A). That is three factors at once. You cannot attribute the reversal to “GPs are better” from E2 alone. Q34 is a factorial on the same 48 wells: two designs × two models, scored at the model recommendation (rule C).

**Why Q45 was run.** Q34’s polynomial on BO points was a **six-factor** quadratic. DoE’s polynomial is a **four-factor** quadratic on the screened factors. The design contrast was confounded with model size. Q44 also found the six-factor CCD is singular in 50/50 runs, so that polynomial should not have been asked to compete. Q45 refits **both** polynomials on the same four kept factors.

**What is held fixed in Q34.** The 48 collected points of each arm. The landscapes.

**What changes.** Which model is fitted to those points, and which arm’s points you use.

#### Q34 factorial — all four cells

Cell 1 / 2 are rule A (same as E2). Cells 3–6 are rule C (model recommendation).

| Cell | What it is | d=6 σ=0.25 | d=6 σ=0.10 | d=8 σ=0.25 | d=8 σ=0.10 |
|---|---|---|---|---|---|
| 1 | DoE points, best measured (rule A) | 0.0958 | 0.0892 | 0.0963 | 0.0948 |
| 2 | BO points, best measured (rule A) | 0.1553 | 0.0874 | 0.1247 | 0.0972 |
| 3 | DoE points, **polynomial** (unconstrained) | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| 4 | BO points, **GP** | 0.1232 | 0.0703 | 0.1056 | 0.0876 |
| 5 | DoE points, **GP** (swap model, keep design) | 0.1993 | 0.2728 | 0.1139 | 0.1168 |
| 6 | BO points, **six-factor polynomial** (swap model, keep design) | 0.5838 | 0.3956 | 0.6972 | 0.6784 |

Registered primary contrast, cell 5 − cell 3 (GP minus polynomial on **identical DoE points**): **−0.2171** [−0.2524, −0.1834] at d=6 σ=0.25. Same direction at the other three cells (−0.1573 / −0.2628 / −0.2936), all p ≤ 10⁻⁶. Swapping the surrogate on the same data moves regret by 0.16–0.29.

The six-factor polynomial on BO points (cell 6) is the confounded number. Do not use it as the design effect. That is Q45.

Q34 also predicted frequent hard failures fitting a quadratic to BO’s clustered points. **Got 0 in 200 runs.** Condition number of the DoE full second-order matrix is 8.1×10¹⁶–1.1×10¹⁸ (singular). BO’s is 2.4×10²–3.9×10³. You can fit a full second-order surface to BO-collected data and you cannot fit one to the DoE arm’s own 48 points without screening to four factors first.

#### Q45 — both polynomials on four factors

| | d=6 σ=0.25 | d=6 σ=0.10 | d=8 σ=0.25 | d=8 σ=0.10 |
|---|---|---|---|---|
| Cell 3: polynomial on DoE / CCD (four factors already) | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| Cell 6 refit: polynomial on BO points, **four** factors | **0.3035** | **0.1417** | **0.2519** | **0.1435** |
| Cell 6 old: polynomial on BO points, six factors (Q34) | 0.5838 | 0.3956 | 0.6972 | 0.6784 |
| Cell 4: GP on BO points | 0.1232 | 0.0703 | 0.1056 | 0.0876 |
| **Design, model fixed** (cell 3 − cell 6 refit). Positive = CCD worse. | **+0.1129** | **+0.2883** | **+0.1247** | **+0.2669** |
| **Surrogate, design fixed** (cell 4 − cell 6 refit). Negative = GP better. | **−0.1803** | **−0.0715** | **−0.1462** | **−0.0559** |

All eight contrasts p ≤ 0.0008.

At the quiet assay the design effect is **4–5× the surrogate effect**. At the noisy assay they are the same order. The surrogate effect is the only one that never reverses sign.

#### Q44 — we did not give DoE a bad design

D-efficiency of the four-factor model (the model stage 2 is built for):

| Coding | CCD (stage 2) | Adaptive (BO) | Ratio |
|---|---|---|---|
| Common unit cube | 4.99×10⁻³ | 1.05×10⁻² | BO 2.1× |
| Each design in its **own** region | 4.58×10⁻² | 1.05×10⁻² | **CCD 4.4×** |

**What it means.** On identical DoE points, a GP recommends a better global recipe than a quadratic. On identical four-factor quadratics, the clustered BO design recommends a better global recipe than the CCD. Both pieces are real. The CCD is ~4.4× more D-efficient *inside its own region* and still recommends a worse *global* recipe. D-optimality in a small box is not usefulness for a recommendation made outside it. The DoE arm’s design is well-built for the wrong question.

Files: `results/q34-factorial.json`, `results/q45-fourfactor-refit.json`, `results/q43-attribution.json`.

### 3.4 The scoring effect is not an artefact of our Hill oracle

**Why Q42 was run.** A reviewer who grants the Hill result can still say: *your oracle is ~93% additive and biphasic in every factor; of course a quadratic saddle-escapes.* Q42 repeats the same DoE-vs-BO, same 48-well pipeline, same four (d, σ) cells, on standard test functions we did not build. The registered prediction was that the reversal would **not** reproduce cleanly on any family. That prediction was wrong, in the favourable direction.

**What is held fixed.** Pipeline, budget, four cells, scoring rules.

**What changes.** The ground-truth function. Hartmann6 at d=8 is the same six-dimensional function plus two inert axes (`oracles.Embedded`), so the dimension contrast is not confounded with “the function grew extra active coordinates.”

**DoE rule A below is D20-corrected.** Old on-disk `doe_a` in `q42-families.json` is oracle-best; do not quote it.

#### Levy — reversal at all four cells

Saddle in 25/25 at three cells; 22/25 at d=6 σ=0.10.

| Cell | DoE A | BO A | Winner A | DoE C unc. | BO C | Winner C unc. | DoE C con. | Winner C con. |
|---|---|---|---|---|---|---|---|---|
| d=6 σ=0.25 | 0.0392 | 0.1156 | DoE | 0.5598 | 0.0794 | BO | 0.0791 | null |
| d=6 σ=0.10 | 0.0241 | 0.0754 | DoE | 0.4559 | 0.0562 | BO | 0.0696 | null |
| d=8 σ=0.25 | 0.0494 | 0.1290 | DoE | 0.4704 | 0.0647 | BO | 0.0663 | null |
| d=8 σ=0.10 | 0.0220 | 0.0787 | DoE | 0.4151 | 0.0664 | BO | 0.0607 | null |

Unconstrained − constrained on DoE: **+0.35 to +0.48**.

#### Rosenbrock — reversal at all four cells

Saddle in 25/25 at all four.

| Cell | DoE A | BO A | Winner A | DoE C unc. | BO C | Winner C unc. | DoE C con. | Winner C con. |
|---|---|---|---|---|---|---|---|---|
| d=6 σ=0.25 | 0.0328 | 0.0700 | DoE | 0.3026 | 0.0388 | BO | 0.0369 | null |
| d=6 σ=0.10 | 0.0156 | 0.0430 | DoE | 0.2444 | 0.0157 | BO | 0.0254 | small BO (p=0.052) |
| d=8 σ=0.25 | 0.0320 | 0.0823 | DoE | 0.3018 | 0.0419 | BO | 0.0357 | null |
| d=8 σ=0.10 | 0.0174 | 0.0580 | DoE | 0.2549 | 0.0195 | BO | 0.0262 | null |

Unconstrained − constrained on DoE: **+0.22 to +0.27**. Constrained rule C is null at 6 of 8 Levy/Rosenbrock cells; the seventh is the borderline Rosenbrock quiet-six cell.

#### Hartmann6 — BO wins under every rule, every cell

Saddle in 25/25 at all four. This is the family that **does not** reverse.

| Cell | DoE A | BO A | DoE − BO (A) | DoE C unc. | BO C | DoE C con. | Winner, every rule |
|---|---|---|---|---|---|---|---|
| d=6 σ=0.25 | 0.5623 | **0.2984** | +0.2460 | 0.9008 | 0.2695 | 0.5449 | **BO** |
| d=6 σ=0.10 | 0.5428 | **0.1938** | +0.3460 | 0.8985 | 0.1740 | 0.5223 | **BO** |
| d=8 σ=0.25 | 0.6393 | **0.3134** | +0.3189 | 0.8792 | 0.2992 | 0.6309 | **BO** |
| d=8 σ=0.10 | 0.6534 | **0.2370** | +0.4134 | 0.8751 | 0.2269 | 0.6442 | **BO** |

All rule-A contrasts p < 0.0001, all favouring BO.

**Why the screen fails at d=8.** Hartmann6 has six active coordinates. The pipeline always keeps four (`n_keep = 4`, matching Hall/Ogle 6→4), so it must discard real signal at every cell. At d=8 two coordinates are inert. Chance alone puts **3.00 / 4** slots on active factors. The screen scored **2.96 / 4** at σ=0.25 and **2.88 / 4** at σ=0.10 — *slightly worse at low noise*, so this is not a noise problem. Twenty runs plus four centre points cannot tell a provably null factor from a real one on this surface. At d=6 (all six active) the screen fills 4.00 / 4 active slots and BO still wins, so screening-at-chance is an extra d=8 wound, not the whole story.

#### Ackley — do not use

Optimum is the centre of the box. A face-centred CCD **always measures the centre**. DoE rule A is ~0.00 because the design lands on the answer. Constrained and unconstrained rule C are identical to four decimals. Void under **every** rule. The 103 interior maxima out of 350 Q42 runs are concentrated here; this is also the proof that “the fitted surface is always a saddle” is false.

| Cell | DoE A | BO A | Note |
|---|---|---|---|
| all four | ~0.00–0.013 | 0.56–0.76 | CCD sits on the optimum. Not a method comparison. |

**What it means.** “How you score DoE changes the winner” generalises on saddle problems (Hill, Levy, Rosenbrock). “Which method wins” does not (Hartmann6). Claim the first. Do not claim the second as universal. After D20, 12 of 16 family-cells still reverse; Levy and Rosenbrock are not void.

Files: `results/q42-families.json` (rule C and BO rule A), `results/d20-rescore.json` (DoE rule A).

### 3.5 Cost and time: wells vs rounds to first arrival

**Why Q52 was run.** A fixed-budget snapshot at 48 wells cannot answer “does BO need fewer experiments?” That is a **when do you first hit a quality target** question, and it has two clocks (wells, rounds). Q52 §2 is that experiment. Q52 §1 was a floor check that refuted itself; do not cite it.

**What ran.** **d = 6 only.** σ ∈ {0.10, 0.25}. 25 landscapes. Cap **200**. Arms: qLogEI, doe, random, spread_gp. Checkpoints 8·12·16·20·24·32·48·64·100·150·200. Rule A for the arrival numbers below. Rounds reconstructed as in §2.7.

**d = 8 was not run.** Do not interpolate an eight-factor savings or arrival claim from this grid.

**What the registered analysis produced.** A **null**. The savings ratio is the fold-difference in budget-to-target among landscapes **both** arms reached, and only if censoring stays under the registered gates.

| Registered pairing | Outcome |
|---|---|
| Rule C targets 0.30…0.05, σ=0.25 | DoE censored 72–100%. n_paired 7 down to 0. **Undefined at every target.** |
| Rule C targets, σ=0.10 | n_paired 9 down to 0. **Undefined at every target.** |
| Rule A targets 0.03 / 0.02 / 0.01, both σ | n_paired 0, 0, 0. **Undefined across its whole length.** |

Do not quote a fold-savings number. A first-pass “crossover at 0.15” was **retracted**: it mixed rule-C targets with rule-A scores, reported cells the gates had already marked `undef`, and the apparent decline was survivorship (the curve is flat on a fixed set of 7 landscapes).

What survives is **arrival rate** (how many of 25 landscapes hit the target by cap 200) plus, *among those that arrived*, median wells and median rounds. A median over 13 of 25 is not the same population as a median over 24 of 25. Do not compare those medians as if they were.

Holm is over ten BO-vs-DoE arrival tests. **One cell survives:** quiet assay, target 0.10.

#### Quiet assay (σ = 0.10) — the only arrival-rate cell that survives Holm

| Target | BO reaches | BO wells | BO rounds | DoE reaches | DoE wells | DoE rounds | spread_gp reaches | spread wells | spread rounds | disc. BO:DoE | p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.12 | 24/25 | 32 | 6 | 20/25 | 48 | 3 | 25/25 | 20 | 1 | 5:1 | 0.2188 |
| **0.10** | **24/25** | **32** | **6** | **13/25** | **48** | **3** | **24/25** | **32** | **1** | **11:0** | **0.0010** |
| 0.08 | 22/25 | 74 | 16.5 | 13/25 | 96 | 6 | 23/25 | 32 | 1 | 10:1 | 0.0117 |
| 0.05 | 18/25 | 100 | 23 | 7/25 | 96 | 6 | 16/25 | 48 | 1 | 15:4 | 0.0192 |

Headline, among arrivals, σ=0.10 target 0.10:

| | Reaches | Cost (wells) | Time (rounds) |
|---|---|---|---|
| BO | **24/25** | **32** | **6** |
| DoE | 13/25 | **48** | **3** |
| spread_gp | **24/25** | **32** | **1** |

Among the 13 landscapes **both** BO and DoE reached: BO used fewer wells in **9**, DoE in 4; DoE used fewer rounds in **8**, BO in 5.

#### Noisy assay (σ = 0.25) — no rate difference at any target

This is the registered realistic assay. Who-arrives is a coin flip.

| Target | BO reaches | BO wells | BO rounds | DoE reaches | DoE wells | DoE rounds | spread_gp reaches | spread wells | spread rounds | disc. BO:DoE | p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.15 | 21/25 | 32 | 6 | 23/25 | 48 | 3 | 25/25 | 20 | 1 | 1:3 | 0.6250 |
| 0.10 | 14/25 | 82 | 18.5 | 11/25 | 96 | 6 | 21/25 | 48 | 1 | 7:4 | 0.5488 |
| 0.08 | 10/25 | 125 | 29 | 6/25 | 72 | 4.5 | 17/25 | 48 | 1 | 7:3 | 0.3438 |

No p survives Holm. Do not write an arrival-rate win at σ=0.25.

**What it means.** At the quiet assay, BO arrives more often, cheaper in wells, slower in rounds. spread_gp matches the 24/25 rate and the 32-well median in **one** plate cycle. At the realistic assay, who-arrives is a coin flip. Our DoE arm never walks the design (no steepest ascent), so these cost/time numbers are biased toward BO. Quality-against-budget plots (`results/figures/cost-curves.html`) are a different cut: mean regret at each n, not first arrival. Do not present them as the arrival table.

Files: `results/q52-budget-to-target.json`, `results/q52-rounds-to-arrival.json`.

### 3.6 Extra BO rounds help on deceptive landscapes, not on smooth ones

**Method.** Q53. One-shot spread_gp vs 10-round qLogEI, same well count, on Q42’s families. Prediction fixed before the runner existed. Held 8 of 8: spread_gp loses on Hartmann6.

| Landscape | spread_gp vs qLogEI |
|---|---|
| Levy, Rosenbrock (smooth) | **Tie** |
| Hartmann6, Ackley (deceptive / needle) | **Loses**, large gap |

On the Hill family, spread_gp was indistinguishable from qLogEI at budget 48 — but that Hill comparison used one design draw; Q53 used five. Re-run Hill at five draws before combining those sentences.

**What it means.** Adaptive BO buys deception-handling. It does not, on this evidence, buy sample efficiency on the smooth surfaces this project was built around.

File: `results/q53-spread-gp-families.json`.

### 3.7 Reviewer objections already closed

Not the headline. Stops the obvious attacks.

| Objection | Measurement |
|---|---|
| GP misspecified for a ~93% additive landscape | Additive kernel: R² 0.375 → 0.744; regret moved 0.0015, p=0.71 |
| Lengthscale prior crippled BO | The “better” prior was worse at ARD separation |
| Acquisition optimizer failing | 4 / 3400 = 0.118% (threshold 1%, set first) |
| Opening too small | No effect at the primary cell |
| Lucky landscapes | 0 of 10,000 permutations as extreme |
| LHS got lucky | It did (best of 60). Design-average BO: still ahead 25/25, p=6.0×10⁻⁸ |
| “LHS also beats BO” | Dies under Holm |
| Extrapolation is synthetic-only | On digitized Hall/Ogle, the polynomial runs to any wall; the GP does not move |
| Replay null ⇒ BO useless | MDE 0.68; the instrument had no resolution |
| GP uncertainty is honest | No. Coverage below 95% in every cell. Worst 0.764 |
| Identification is a technicality | At σ=0.25, 61% of leftover regret is a recipe already run and not identified |

---

## 4. Do not cite

| Dead item | Why |
|---|---|
| E2 runs 1–2 | Scoring bug; unpaired opening |
| −0.0708 | Other clone’s gitignored grid. Use **−0.0595** |
| “Savings inverts, crossover 0.15” | Retracted. Broke registered gates |
| “Polynomial always worse than its data” | Null at σ=0.10 after D20 |
| Ackley as a DoE-vs-BO cell | Optimum is the centre |
| E4 headline | Different question; pooled vs registered cell disagree in sign |
| Q47 multi-fidelity | All three predictions wrong; not this paper |
| Q52 at d=8 | **Not run.** Arrival tables are d=6 only. |

---

## 5. What is left

**Paper.** No manuscript. `CLAIMS.md` is still a draft. Q50 ran (`results/q50-paired.json`) but has no `RESULTS.md` section. Sentence 2 must say **unconstrained** rule C. Sentence 3 must say the polynomial-worse-than-data half is for the **noisy** assay.

**Human decisions.** T15 (accept d=8 DoE). Q23 (coord unpaired). Alan cuts `CLAIMS.md`.

**Optional runs.** U5 (fatter BO batches — the lab question after 6 rounds vs 3). U2 (noise sweep). Hill spread_gp at 5 design draws. Stage-4 confirm for BO so rule A does not tax only DoE. Q52 at d=8 if an eight-factor arrival claim is wanted.

**Lab.** Sign 12 CD31 gates. Until then, nothing in `data/lab/` is a result. Even after sign-off, that 12-point scan is a bad BO test.

---

## 6. What a paper should say, in order

1. **Setup.** Synthetic Hill benchmark motivated by Hall/Ogle. Grid: d ∈ {6, 8} × σ ∈ {0.10, 0.25}. Primary cell d=6, σ=0.25, n=25, budget 48. qLogEI vs 20+27+1 DoE. Score at the true value of the selected recipe. Cost = wells. Time = rounds.
2. **Rule A.** Noisy assay, best measured recipe: DoE beats BO by 0.0595 at d=6 and by 0.0284 at d=8. Quiet assay: tie at both dimensions.
3. **Rule C.** Unconstrained model recommendation: BO beats DoE by 0.27–0.36 in all four cells. Constrained: three nulls and one small BO win.
4. **Mechanism.** Quadratic is a saddle in 200/200 Hill runs. ~90% of the swing is classical scoring. Polynomial-worse-than-data holds at σ=0.25 only.
5. **Design vs model.** GP beats polynomial on the same points. Clustered BO design beats CCD on the same four-factor polynomial. CCD is 4.4× more D-efficient in-region anyway.
6. **Generality.** Scoring swing reproduces on Levy and Rosenbrock (all eight cells). Winner does not (Hartmann6: BO under every rule). Ackley is void.
7. **Cost and time.** No savings ratio. d=6 only. Quiet assay: BO arrives more often, 32 wells vs 48, 6 rounds vs 3. spread_gp: same arrival, 1 round. Realistic assay: no rate difference.
8. **Limits.** No cells. Oracle not fitted. Replay underpowered. GP miscalibrated. DoE has no steepest-ascent phase. Q52 was not run at d=8.

---

## Pointers

| Need | File |
|---|---|
| This summary | `docs/RESEARCH-SUMMARY.md` |
| Long audit | `docs/RESULTS.md` |
| Paper skeleton | `docs/MAIN-LINE.md` |
| CORE / VOID labels | `docs/TRIAGE.md` |
| E2 all arms | `results/e2-grid.json`, `results/e2-doe-d8.json` |
| Scoring factorial | `results/q34-factorial.json` |
| Constrained RSM / saddle | `results/q35-constrained-rsm.json` |
| D20 rule-A correction | `results/d20-rescore.json` |
| Four-factor refit | `results/q45-fourfactor-refit.json` |
| External families | `results/q42-families.json` |
| Arrival wells + rounds | `results/q52-rounds-to-arrival.json` |
| Quality vs budget plots | `results/figures/cost-curves.html` |
