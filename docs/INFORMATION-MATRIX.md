# INFORMATION MATRIX — what is actually known about each arm

**Every number carries its source file and its n. Empty cells are empty because the quantity was
never computed — nothing here is interpolated, substituted from a nearby cell, or estimated.**

Primary cell throughout is **d=6, σ_rel=0.25**, budget 48, unless stated. `n` is **instances**,
with seeds averaged within instance before any test (`run_e2.py:168`), so n=25 not 50.

**Rule A ≡ best observed.** Rule A is defined as the true value at the running *observed* argmax
(Q17), which is exactly "the arm's own best measured value". They are one column, not two, and
the brief's separate "Best-observed" column is folded into "Rule A regret" below.

---

## 1. Coverage — where each arm has run

| arm | Hill d=6 σ.10 | Hill d=6 σ.25 | Hill d=8 σ.10 | Hill d=8 σ.25 | hartmann6 | levy | rosenbrock | ackley |
|---|---|---|---|---|---|---|---|---|
| `doe` | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25×4 | ✅ 25×4 | ✅ 25×4 | ✅ void |
| `qlogei` | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25×4 | ✅ 25×4 | ✅ 25×4 | ✅ void |
| `qlognei` | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25 | ❌ | ❌ | ❌ | ❌ |
| `random` | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25 | ❌ | ❌ | ❌ | ❌ |
| `sobol` | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25 | ❌ | ❌ | ❌ | ❌ |
| `lhs` | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25 | ❌ | ❌ | ❌ | ❌ |
| `coord` | ✅ 25 | ✅ 25 | ✅ 25 | ✅ 25 | ❌ | ❌ | ❌ | ❌ |
| **`spread_gp`** | **✅ 25×2** | **✅ 25×2** | **✅ 25×2** | **✅ 25×2** | **❌** | **❌** | **❌** | **❌** |

✅ **`doe` at d=8 has a machine-readable source after all.** I recorded it as log-text-only on
D17's wording; `results/e2-doe-d8.json` was in fact written, gitignored, and never force-added.
Now committed — 100 rows, both cells, 18 fields, regenerating the log exactly. **Re-aggregatable
and re-scorable.**

Sources: `results/e2-grid.json` (Hill, seven arms) · `results/e2-doe-d8.log` (Hill d=8 `doe`) ·
`results/q42-families.json` (four external families, `doe` and `qlogei` only) ·
`results/q47-multifidelity.json` (`spread_gp`, all four Hill cells, as the `single` arm) ·
`results/q52-budget-to-target.json` (`spread_gp` and `random`, Hill d=6, budget curve).

---

## 2. The matrix — d=6, σ=0.25, budget 48

| arm | rounds | batch structure | rule A regret (= best observed) | rule C regret | model helps (−) or hurts (+) | can propose an untested point |
|---|---|---|---|---|---|---|
| **`doe`** | **3** | screen 20 + CCD 27 + confirm 1 | **0.0958** [0.0870, 0.1045] | **0.4163** uncon *(Q41 primary)* · **0.1169** con | **+0.3205** uncon · **+0.0211** [+0.0105, +0.0315] con | **yes** — polynomial argmax |
| **`qlogei`** | **10** | opening 14, then 9 × q=4 | **0.1553** [0.1367, 0.1734] | **0.1232** | **−0.0320** [−0.0504, −0.0139] p=0.0025 | **yes** — GP posterior-mean argmax |
| **`qlognei`** | **10** | opening 14, then 9 × q=4 | **0.1532** [0.1325, 0.1735] | *(never computed)* | *(never computed)* | yes — same machinery |
| **`random`** | **1** | all 48 known before the first plate | **0.2216** [0.2079, 0.2361] | *(never computed)* | — no model | **no** |
| **`sobol`** | **1** | all 48 known before the first plate | **0.1724** [0.1475, 0.1975] | *(never computed)* | — no model | **no** |
| **`lhs`** | **1** | all 48 known before the first plate | **0.1270** [0.1091, 0.1450] ⚠️ | *(never computed)* | — no model | **no** |
| **`coord`** | **48** | one measurement at a time | **0.1420** [0.1224, 0.1621] | *(never computed)* | — no model | no |
| **`spread_gp`** | **1** | LHS of n, all known before the first plate | **0.1778** (Q47, n=25×2) · **0.1539** [0.1269, 0.1805] (Q52, n=25) 🔶 | **0.1300** (Q47) · **0.1208** [0.1000, 0.1419] (Q52) | **−0.0478** [−0.0679, −0.0294] p=4.5×10⁻⁵ | **yes** — GP posterior-mean argmax |

**Sources.** Rounds: `results/q38-cost-model.json`. Rule A: `results/e2-grid.json`.
Rule C `doe`/`qlogei`: `results/q34-factorial.json` (cells 3, 4) and
`results/q35-constrained-rsm.json` (constrained). `doe` model-helps: `results/d20-rescore.json`.
`spread_gp`: `results/q47-multifidelity.json` (`single_a`, `single_c`) and
`results/q52-budget-to-target.json` (checkpoint 48).

⚠️ **`lhs` 0.1270 is one design draw and it is the best of 60.** Design-averaged it is **0.1752**,
the 0th percentile of 60 draws, against a design SD of 0.025 (Q48, `q48-design-variance.json`).
Every static-arm interval in this table is a **within-design** interval.

🔶 **`spread_gp`'s two independent measurements differ by 0.0239 at the same cell** — 0.1778
(Q47) against 0.1539 (Q52). That is **≈1 design SD**, and it is the same design lottery Q48
documents, observed a second time. Neither is wrong; the arm's rule A is not determined to better
than about ±0.02 from a single design draw. **Do not quote either alone.**

---

## 3. Noise sensitivity — rule A mean, σ=0.10 → 0.25

| arm | d=6 σ.10 | d=6 σ.25 | Δ | d=8 σ.10 | d=8 σ.25 | Δ |
|---|---|---|---|---|---|---|
| `doe` | 0.0892 | 0.0958 | **+0.0066** | 0.0948 | 0.0963 | **+0.0015** |
| `qlogei` | 0.0874 | 0.1553 | **+0.0679** | 0.0972 | 0.1247 | +0.0275 |
| `qlognei` | 0.0808 | 0.1532 | **+0.0724** | 0.0849 | 0.1105 | +0.0256 |
| `random` | 0.1693 | 0.2216 | +0.0523 | 0.1272 | 0.1712 | +0.0440 |
| `sobol` | 0.1210 | 0.1724 | +0.0514 | 0.0968 | 0.1804 | +0.0836 |
| `lhs` | 0.1027 | 0.1270 | +0.0243 | 0.1260 | 0.1627 | +0.0367 |
| `coord` | 0.0880 | 0.1420 | +0.0539 | 0.1053 | 0.1926 | +0.0873 |
| `spread_gp` | 0.1380 | 0.1778 | +0.0398 | 0.1392 | 0.1824 | +0.0432 |

**The classical arm is nearly noise-insensitive and the adaptive arms are not** — `doe` moves
+0.0066 where `qlogei` moves +0.0679, a factor of ten. That is the single clearest pattern in the
table, and it is why the σ=0.25 cell is where BO loses and the σ=0.10 cell is where it ties.

d=8 `doe` from `results/e2-doe-d8.json` (committed 2026-08-14; D17 corrected).

### Model helps or hurts, at every cell

| arm / scoring | d=6 σ.25 | d=6 σ.10 | d=8 σ.25 | d=8 σ.10 |
|---|---|---|---|---|
| `qlogei` rule C − best observed | **−0.0320** p=0.0025 | **−0.0171** p=0.011 | **−0.0191** p=0.016 | **−0.0096** p=0.045 |
| `doe` rule C **unconstrained** − best observed | **+0.3205** | **+0.3408** | **+0.2803** | **+0.3156** |
| `doe` rule C **constrained** − best observed | **+0.0211** [+0.0105,+0.0315] | **−0.0036** [−0.0122,+0.0049] **null** | **+0.0185** [+0.0094,+0.0287] | **−0.0071** [−0.0150,+0.0008] **null** |
| `spread_gp` rule C − rule A | **−0.0478** p=4.5e-05 | **−0.0493** p=5.2e-06 | **−0.0645** p=2.0e-06 | **−0.0509** p=1.1e-06 |

**Both GP arms' models beat their own data at every cell. The polynomial's model beats its own
data at no cell** — and, constrained, is *indistinguishable* from its own data at both σ=0.10
cells. The asymmetry is a property of the **noisy** assay, not of the two model classes.

`spread_gp`'s model gain (−0.048 to −0.065) is **larger than qLogEI's** (−0.010 to −0.032) at
every cell. A GP fitted to a spread design has more to smooth than one fitted to a design that
has already clustered on the incumbent.

---

## 4. Superseded numbers — the oracle-best scoring bug (D20)

`DoEResult.curve_true` is `np.maximum.accumulate` over the **noiseless** values — oracle-best, not
rule A. Three scripts read it as rule A. **Everything below was computed before the fix.** The
fidelity gate on the rescore is **worst |Δ| = 0.000e+00** over 400 Q42 rows and 200 Q35 rows on
the columns the fix does not touch.

| quantity | superseded | corrected | source of correction |
|---|---|---|---|
| `doe` best observed, d=6 σ=0.25 | 0.0597 | **0.0958** | `d20-rescore.json` |
| `doe` best observed, d=6 σ=0.10 | 0.0544 | **0.0892** | `d20-rescore.json` |
| `doe` best observed, d=8 σ=0.25 | 0.0575 | **0.0963** | `d20-rescore.json` |
| `doe` best observed, d=8 σ=0.10 | 0.0500 | **0.0948** | `d20-rescore.json` |
| constrained − best observed, d=6 σ=0.25 | +0.0572 | **+0.0211** [+0.0105,+0.0315] | `d20-rescore.json` |
| constrained − best observed, d=6 σ=0.10 | +0.0312 | **−0.0036** [−0.0122,+0.0049] **NULL** | `d20-rescore.json` |
| constrained − best observed, d=8 σ=0.25 | +0.0573 | **+0.0185** [+0.0094,+0.0287] | `d20-rescore.json` |
| constrained − best observed, d=8 σ=0.10 | +0.0377 | **−0.0071** [−0.0150,+0.0008] **NULL** | `d20-rescore.json` |
| `doe` rule A, levy d=6 σ=0.25 | 0.0040 | **0.0392** | `d20-rescore.json` |
| `doe` rule A, rosenbrock d=6 σ=0.25 | 0.0003 | **0.0328** | `d20-rescore.json` |
| `doe` rule A, hartmann6 d=6 σ=0.25 | 0.5444 | **0.5623** | `d20-rescore.json` |
| `doe` rule A, ackley (all cells) | 0.0000 | **0.0123 / 0.0011 / 0.0131 / 0.0013** | `d20-rescore.json` |

🔴 **`results/q35-constrained-rsm.json`'s `best_observed` column is still the superseded value on
disk.** The file was not rewritten; the correction lives in `d20-rescore.json`. **Anything
recomputed from `q35-constrained-rsm.json` directly will reproduce the bug.** No verdict moved —
0 of 16 family-cells flipped — but eight published numbers did.

**Not affected:** every rule-C figure at every site, and therefore Q41's primary estimand. The bug
touched only the arm's *own best observed* column.

---

## 5. Cost matrix — evaluations / rounds to target

From `results/q52-budget-to-target.json`, d=6, n=25, cap 200, checkpoints
8·12·16·20·24·32·48·64·100·150·200. Cells are **median evaluations / rounds (censoring %)**.
**No point estimate is given above 50% censoring**, per the registration.

### σ = 0.25, rule C

| target | `doe` | `qlogei` | `random` | `spread_gp` |
|---|---|---|---|---|
| 0.30 | >50% cens (72%) | **8 / 1** (0%) | — | **8 / 1** (0%) |
| 0.25 | >50% cens (80%) | **8 / 1** (0%) | — | **8 / 1** (0%) |
| 0.20 | >50% cens (84%) | **8 / 1** (0%) | — | **8 / 1** (0%) |
| 0.15 | >50% cens (96%) | **12 / 1** (4%) | — | **12 / 1** (0%) |
| 0.12 | >50% cens (96%) | **18 / 2** (20%) | — | **20 / 1** (0%) |
| 0.10 | >50% cens (100%) | **18 / 2** (36%) | — | **24 / 1** (0%) |
| 0.08 | >50% cens (100%) | >50% cens (60%) | — | **40 / 1** (12%) |
| 0.05 | >50% cens (100%) | >50% cens (72%) | — | **48 / 1** (40%) |

### σ = 0.10, rule C

| target | `doe` | `qlogei` | `random` | `spread_gp` |
|---|---|---|---|---|
| 0.30 | >50% cens (64%) | **8 / 1** (0%) | — | **8 / 1** (0%) |
| 0.25 | >50% cens (80%) | **8 / 1** (0%) | — | **8 / 1** (0%) |
| 0.20 | >50% cens (88%) | **8 / 1** (0%) | — | **8 / 1** (0%) |
| 0.15 | >50% cens (92%) | **12 / 1** (0%) | — | **12 / 1** (0%) |
| 0.12 | >50% cens (96%) | **16 / 2** (0%) | — | **16 / 1** (0%) |
| 0.10 | >50% cens (96%) | **20 / 3** (4%) | — | **16 / 1** (0%) |
| 0.08 | >50% cens (96%) | **48 / 10** (8%) | — | **20 / 1** (0%) |
| 0.05 | >50% cens (100%) | **100 / 23** (28%) | — | **32 / 1** (28%) |

### Rule A (targets 0.03 / 0.02 / 0.01), both σ

**Every cell is >50% censored for every arm.** No point estimate anywhere. σ=0.25: `doe` 96/100/100%,
`qlogei` 88/96/100%, `random` 96/100/100%, `spread_gp` 92/100/100%. σ=0.10: `doe` 96/100/100%,
`qlogei` 60/84/100%, `random` 92/100/100%, `spread_gp` 80/100/100%.

**`random` has no rule-C column** — the runner computes rule C only for `qlogei`, `doe` and
`spread_gp` (`run_q52_budget_to_target.py:209`). It is a genuine gap, not a censored cell.

### Reading this table honestly

- **`doe` is censored above 50% at every rule-C target including the loosest.** Its unconstrained
  rule-C regret is 0.4163 (Q35), worse than the loosest target in the set. **No savings ratio
  against `doe` is defined anywhere on this curve.**
- **Targets 0.30–0.20 measure granularity, not adaptivity.** `batch_plan(6, 200)` opens with 14
  points, so at n=8 and n=12 **qLogEI has made zero adaptive decisions**. Both one-shot arms
  arrive at 8 because 8 is the first checkpoint.
- **The tight targets are past the opening and are real.** At σ=0.25, `spread_gp` reaches 0.08 and
  0.05 where qLogEI is censored at 60% and 72%.
- **`spread_gp`'s checkpoints are independent, qLogEI's are nested.** `spread_gp` draws a *fresh*
  LHS design of size n at each checkpoint; qLogEI's curve is one campaign read at intervals. That
  is the right comparison for a one-shot method — you would design for your budget — but the
  columns are not the same kind of object and a per-instance trajectory is only meaningful for
  qLogEI.
- **Every ratio in this grid is biased in BO's favour** (L10): the `doe` arm repeats a fixed
  pipeline and never moves its design region, where classical sequential RSM inserts a
  steepest-ascent phase.

---

## 6. The paired contrast the cost table implies — and it is a tie

At **equal evaluations (48)**, same instances, same GP scoring function, from
`results/q52-budget-to-target.json`:

| σ | contrast | diff | 95% CI | Wilcoxon p | n | verdict |
|---|---|---|---|---|---|---|
| 0.25 | `qlogei − spread_gp`, rule A | +0.0365 | [−0.0015, +0.0732] | **0.034** | 25 | ⚠️ **disagree** |
| 0.25 | `qlogei − spread_gp`, rule C | +0.0305 | [−0.0046, +0.0652] | 0.071 | 25 | null |
| 0.10 | `qlogei − spread_gp`, rule A | −0.0112 | [−0.0467, +0.0220] | 0.65 | 25 | null |
| 0.10 | `qlogei − spread_gp`, rule C | +0.0060 | [−0.0179, +0.0300] | 0.67 | 25 | null |

⚠️ **The σ=0.25 rule-A row is a registered disagreement, not a result.** Wilcoxon says
significant (p=0.034); the instance bootstrap covers zero. **Q20 §2 governs: the disagreement is
reported, not resolved.** And this is a non-primary contrast, so Q39's Holm correction applies —
p=0.034 survives no correction over any family of this project's size.

**The defensible statement is a tie on quality and a 10× difference in rounds:**

> At a budget of 48 on the Hill family at d=6, a one-shot Latin hypercube scored at its GP's
> posterior-mean argmax is statistically indistinguishable from qLogEI under both scoring rules,
> at both noise levels — and it spends **1 round** where qLogEI spends **10**.

**This is measured on the Hill family only. Generality is untested** — see §1: `spread_gp` has
never run on hartmann6, levy, rosenbrock or ackley.
