# COVERAGE MATRIX — what has been measured, what has not, and what cannot be

**Purpose.** Phase 0 audit. Every design-space number this project can currently cite, laid
out as arm × metric × condition, so that Phases 1–4 are planned against measured coverage
rather than against recollection.

**Audit state.** Read at `HEAD = 1444969` (`Register Step 0 before its runner exists`).
While this audit was running the repository advanced to `c8347f1`; §7 records what moved
and what that does to the findings below. Nothing here was re-read after `c8347f1`.

**Method.** Every cell is one of:

| cell | meaning |
|---|---|
| `file · key` | a committed file in `results/` carries this quantity under this key |
| `NOT RUN` | nothing prevents it; no committed file has it |
| `CANNOT RUN (reason)` | the quantity is undefined, ungatable or not comparable at that condition |
| `NOT VERIFIED` | this audit could not settle it from committed files |

Claims are cited to `file:line` where a line is load-bearing. Numbers were recomputed from
the committed JSONs with `.venv/bin/python` rather than copied from prose; where a
recomputation disagrees with a committed document that is stated.

**Rule carried from `docs/RESULTS.md` rule 1** — a number with no committed file is not a
number. `docs/K6-TECHNICAL-REPORT.md` §9.4 already applies this to itself; this document
extends it to the coverage question.

---

## 1. Arm inventory — every arm ever run

The brief's list is incomplete. Eleven arms carry design-space metrics or regret in a
committed file; four more exist only as regret.

| arm | what it is | design-space metrics? | regret column |
|---|---|---|---|
| `doe` | 20-run screen + 27-run CCD + 1 confirmation, 6→4 screen, 3 rounds | **yes** | `results/e2-grid.json` (d=6 only) |
| `lhs` | 48-well Latin hypercube, 1 round | **yes** | `results/e2-grid.json` |
| `sobol` | 48-well scrambled Sobol, 1 round | **yes** | `results/e2-grid.json` |
| `random` | 48 uniform wells, 1 round | **yes** | `results/e2-grid.json` |
| `qlogei` | batch qLogEI, q=4, 10 rounds | **yes** | `results/e2-grid.json` |
| `qlognei` | batch qLogNEI, q=4, 10 rounds | **yes** | `results/e2-grid.json` |
| `qlogei-add` | qLogEI, `kernel_structure="additive+interaction"` | **yes** | **none — see §3.6** |
| `qlogei-addonly` | qLogEI, `kernel_structure="additive"` | **yes** | **none — see §3.6** |
| `versionb` | LHS 40 + 8 by batch LSE straddle, 2 rounds | **partial** | `results/versionb.json` |
| `versionb_random` | LHS 40 + 8 uniform, 2 rounds | **partial** | `results/versionb.json` |
| `plate1_only` | LHS 48, 1 round. **Identical to `lhs`** (worst \|Δ\| 4.44e-16) | **partial** | `results/versionb.json` |
| `coord` | coordinate descent, 48 wells | no | `results/e2-grid.json`, 200 rows |
| `doe_screened` / `doe_unscreened` | Q59's Hartmann6 pair, with and without the 6→4 screen | no | `results/q59-hartmann-no-screen.json` |
| `spread_gp` | one-shot spread design + GP, rules A and C | no | `results/q53-spread-gp-*.json`, `results/q54-hill-spread-gp-draws.json` |
| `doe_ascent` | steepest-ascent DoE variant, with `oracle_best` | no | `results/q56-doe-ascent.json` |

`coord`, `doe_screened`, `doe_unscreened`, `spread_gp` and `doe_ascent` are the arms in
Q42/Q53/Q56/Q59 that the brief's list omits. **None of them has a single design-space
metric anywhere**, and `coord` is the only one of the five that runs at the primary cell,
so it is the cheapest arm to add to the matrix (§6, P4).

---

## 2. The coverage matrix

### 2.1 Why it factorises, and why that is the finding

A literal metric × γ × τ_frac × d × σ_rel × family product is 13 × 6 × 4 × 2 × 2 × 5 ≈
31,000 cells per arm. It is not printed here because it collapses:

> **Exactly one (family, d, σ_rel) cell — `hill`, `d=6`, `σ_rel=0.25` — carries any
> design-space metric at all.** Verified by scanning every `results/*.json` for the key
> names `auc`, `brier`, `iou`, `alpha_star`, `vorobev`, `ce_*`, `false_inclusion`, `fi_*`,
> `sup_err`, `grid_r2`, `empty_*`, `containment`. Five files match:
> `k6-designspace.json`, `k6-designspace-spread.json`, `k6b-conservative.json`,
> `k6b-conservative-spread.json`, `versionb.json`. All five carry `dim: 6` on every row
> and `sigma: 0.25` on every row. **No file has a `family` key.**

The `auc` in `results/e2-grid.json` is `auc_post_init` — `np.trapezoid` of the
best-so-far regret curve after the opening (`scripts/run_e2.py:178`). It is a
**convergence-speed** statistic, not the AUC of a probability map against a superlevel
set. The two share a name and nothing else, and a matrix that conflated them would show
d=8 and σ=0.10 coverage that does not exist.

So the matrix is presented as (A) metric × arm inside the one populated cell, and (B) the
condition axes, which are answered once for every metric at once.

### 2.2 Matrix A — metric × arm, at `hill · d=6 · σ_rel=0.25 · 25 instances × 2 seeds`

Cells give `file · key`. `k6` = `k6-designspace.json`, `k6s` = `…-spread.json`,
`k6b` = `k6b-conservative.json`, `k6bs` = `…-spread.json`, `vb` = `versionb.json`.
γ-coverage and τ-coverage are the grids that cell spans.

| metric | class | `doe` | `qlogei` | `qlognei` | `qlogei-add` | `qlogei-addonly` | `lhs` | `sobol` | `random` | `versionb` | `versionb_random` | `plate1_only` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **regret** | VALIDATED | `k6·regret` | `k6·regret` | `k6·regret` | `k6·regret` | `k6·regret` | `k6s·regret` | `k6s·regret` | `k6s·regret` | `vb·regret` | `vb·regret` | `vb·regret` |
| **oracle-best** | VALIDATED | `step0·oracle_best`, `q55/q57·doe_oracle_best` | `q55·bo_oracle_best`, `q57·bo_oracle_best` | `step0·oracle_best`, `q57·nei_oracle_best` | NOT RUN | NOT RUN | `step0·oracle_best` | `step0·oracle_best` | `step0·oracle_best` | `step0·oracle_best` **(40 wells — see §3.5)** | NOT RUN | `step0·oracle_best` |
| **AUC (map)** | VALIDATED | `k6·auc_pred`,`auc_latent` γ×6 τ×4 | ditto | ditto | ditto | ditto | `k6s·auc_pred` γ×6 τ×4 | ditto | ditto | `vb·auc_{tf}` **τ×4, γ=0.50 only** | ditto | ditto |
| **Brier** | VALIDATED | `k6·brier_pred`,`brier_latent` γ×6 τ×4 | ditto | ditto | ditto | ditto | `k6s·brier_pred` | ditto | ditto | `vb·brier_{tf}` **τ×4, γ=0.50 only** | ditto | ditto |
| **Brier decomposition** (Murphy cal–ref, 10 equal-count bins, Amendment A5) | VALIDATED | **NOT RUN** | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| **IoU** | VALIDATED | `k6·iou_pred`,`iou_latent` γ×6 τ×4 | ditto | ditto | ditto | ditto | `k6s·iou_*` | ditto | ditto | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| **alpha\*** | MODEL-INTERNAL | `k6b·alpha_star` τ×4 | ditto | ditto | ditto | ditto | `k6bs·alpha_star` | ditto | ditto | `vb·alpha_star_{tf}` τ×4 | ditto | ditto |
| **vorobev_deviation** | MODEL-INTERNAL | `k6b·vorobev_deviation` τ×4 | ditto | ditto | ditto | ditto | `k6bs·…` | ditto | ditto | `vb·vorobev_dev_{tf}` τ×4 | ditto | ditto |
| **ce_contain (circular)** | MODEL-INTERNAL | `k6b·ce_contain_{α}` τ×4 α×3 | ditto | ditto | ditto | ditto | `k6bs·…` | ditto | ditto | `vb·ce_contain_{tf}_{α}` | ditto | ditto |
| **empirical containment** | VALIDATED | `k6b·ce_empirical_{α}` τ×4 α×3 | ditto | ditto | ditto | ditto | `k6bs·…` | ditto | ditto | `vb·ce_empirical_{tf}_{α}` | ditto | ditto |
| **ce_vol / ce_empty** | — | `k6b·ce_vol_{α}`,`ce_empty_{α}` | ditto | ditto | ditto | ditto | `k6bs·…` | ditto | ditto | `vb·ce_vol_{tf}_{α}`,`ce_empty_{tf}_{α}` | ditto | ditto |
| **false-inclusion @ nominal** | VALIDATED | `k6·fi_pred`/`fi_latent` (γ-region) **and** `k6b·ce_false_in_{α}` (CE) | ditto | ditto | ditto | ditto | `k6s·fi_*`, `k6bs·ce_false_in_*` | ditto | ditto | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| **sup_err** | VALIDATED | `k6·sup_err` | ditto | ditto | ditto | ditto | `k6s·sup_err` | ditto | ditto | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| **grid_r2** | VALIDATED | `k6·grid_r2` | ditto | ditto | ditto | ditto | `k6s·grid_r2` | ditto | ditto | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| **emptiness** | — | `k6·empty_pred`,`empty_latent`,`vol_pred`,`vol_latent`; `k6b·ce_empty_{α}` | ditto | ditto | ditto | ditto | `k6s`,`k6bs` | ditto | ditto | `vb·ce_empty_{tf}_{α}` only (no `empty_pred`, no `vol_pred`) | ditto | ditto |
| **inscribed box** | — | `k6·box_vol_pred` **4-D, not comparable — report §6.12** | `k6·box_vol_pred` (6-D) | ditto | ditto | ditto | `k6s·box_vol_pred` | ditto | ditto | NOT RUN | NOT RUN | NOT RUN |
| **gated?** | | **yes** (0 fail / 50) | **yes** | **yes** | **CANNOT GATE — §3.6** | **CANNOT GATE — §3.6** | **yes** | **yes** | **yes** | **UNGATABLE (no committed comparator)** | **UNGATABLE** | ungated in `vb`; gateable against `k6s·lhs` |

Row counts, recomputed: `k6` 6,000 rows = 5 arms × 50 campaigns × 24 (γ, τ_frac) cells;
`k6s` 3,600 = 3 × 50 × 24; `k6b` 1,000 = 5 × 50 × 4; `k6bs` 600 = 3 × 50 × 4;
`versionb.json` 250 = 5 × 50 × 1.

### 2.3 Matrix B — the condition axes

Answered once, because it is the same answer for every metric in Matrix A.

| axis | value | coverage |
|---|---|---|
| **γ** | 0.50 | `k6`/`k6s` all metrics; **`versionb` all metrics (implicitly — §3.1)** |
| | 0.70, 0.80, 0.90, 0.95, 0.99 | `k6`/`k6s` all metrics. **`versionb` NOT RUN at any of them.** `k6b` is γ-free by construction (`theta = tau_frac · mu_max`) |
| **τ_frac** | 0.60, 0.75, 0.85, 0.95 | full, every file, every arm |
| **d** | 6 | full |
| | **8** | **NOT RUN — every design-space metric, every arm.** `results/e2-grid.json` has d=8 regret for 6 arms and `results/e2-doe-d8.json` has the `doe` column, so gate targets exist |
| **σ_rel** | 0.25 | full |
| | **0.10** | **NOT RUN — every design-space metric, every arm.** Gate targets exist in `e2-grid.json` for 7 arms |
| | 0.20, 0.15 (Amendment A5) | **NOT RUN**, and **CANNOT GATE** — no committed campaign exists at either level; A5 already labels them exploratory |
| **family** | hill | full |
| | **hartmann6** | **NOT RUN.** Runnable but **near-degenerate** — see §2.4 |
| | **ackley** | **CANNOT RUN at the registered τ grid** — see §2.4 |
| | **levy, rosenbrock** | **NOT RUN.** Runnable and non-degenerate at τ_frac ≤ 0.85 — see §2.4 |

### 2.4 The `CANNOT RUN` block — measured, not asserted

`tau_frac` is registered as a fraction of `tau_max(γ, σ_rel)`, and `tau_max` is
`mu_max · (1 − z·σ_rel)` with `mu_max = 1.0` on every family (§4, B1). So `τ` is the same
absolute number on every family at the same `(γ, τ_frac)`. What is **not** the same is
what that number selects. Prevalence of the true superlevel set, measured on the
registered 20,000-point Sobol grid at seed 0:

| family | d | τ_f=0.60 | 0.75 | 0.85 | 0.95 | grid f range |
|---|---|---|---|---|---|---|
| **ackley** | 6 | **0.00000** | **0.00000** | **0.00000** | **0.00000** | 0.001 – **0.410** |
| **ackley** | 8 | **0.00000** | **0.00000** | **0.00000** | **0.00000** | 0.004 – **0.337** |
| hartmann6 | 6 | 0.00805 | 0.00195 | 0.00045 | **0.00000** | 0.000 – 0.921 |
| hartmann6 | 8 | 0.00755 | 0.00175 | 0.00045 | **0.00000** | 0.000 – 0.931 |
| levy | 6 | 0.85745 | 0.54170 | 0.24505 | 0.01810 | 0.059 – 0.991 |
| levy | 8 | 0.79325 | 0.40660 | 0.13265 | 0.00355 | −0.023 – 0.989 |
| rosenbrock | 6 | 0.95550 | 0.78250 | 0.50150 | 0.10635 | 0.146 – 0.999 |
| rosenbrock | 8 | 0.91415 | 0.65370 | 0.33110 | 0.03520 | 0.105 – 0.994 |
| hill (mean of 25) | 6 | 0.73569 | 0.28944 | 0.06844 | 0.00294 | 0.143 – 0.989 |
| hill (mean of 25) | 8 | 0.74579 | 0.29247 | 0.06665 | 0.00236 | 0.152 – 0.986 |

**Ackley's superlevel set is empty on the grid at every registered threshold.** Its
normalised optimum is a needle at the exact box centre that a 20,000-point Sobol grid
never lands in; the grid maximum is 0.410 at d=6. Consequences, run live on one `lhs`
campaign:

```
family      tf   prev   auc_pred   brier      iou       fi      vol
ackley    0.60  0.00000     nan    0.0000     nan      nan   0.0000
ackley    0.75  0.00000     nan    0.0000     nan      nan   0.0000
hartmann6 0.60  0.00805  0.5184    0.0080  0.0000      nan   0.0000
hartmann6 0.95  0.00000     nan    0.0000     nan      nan   0.0000
levy      0.60  0.85745  0.5958    0.1997  0.7038   0.1275   0.7710
rosenbrock 0.60 0.95550  0.6261    0.0911  0.9373   0.0450   0.9810
```

`brier_and_auc` returns `nan` for AUC when either class is empty
(`src/boec/designspace.py`, `if pos.numel() == 0 or neg.numel() == 0`), `iou` returns
`nan` when the union is empty, and `false_inclusion_rate` returns `nan` on an empty
region. So:

- **ackley: `CANNOT RUN` for AUC, Brier, IoU, false-inclusion, empirical containment and
  alpha\*'s excursion set — at all four registered τ_fracs, at both dimensions.** Not
  "expensive"; undefined.
- **hartmann6: `CANNOT RUN` at τ_frac = 0.95; runnable but degenerate at 0.60–0.85** —
  prevalence 0.008 to 0.0005, D_γ empty for the arm tested, IoU identically 0,
  false-inclusion `nan`. `docs/K6-TECHNICAL-REPORT.md` §6.6 already flags extreme AUC
  prevalence as a threat on **hill**, where prevalence is 0.003–0.74; on hartmann6 it is
  two orders of magnitude worse.
- **levy, rosenbrock: runnable and non-degenerate at τ_frac 0.60–0.85**, `CANNOT RUN` for
  IoU/false-inclusion at 0.95 (D_γ empty).

**This is the single largest finding of the audit.** A cross-family table at fixed
`τ_frac` compares an empty set against a set covering 95.6% of the box. It is not a
comparison. Fixing it requires re-registering τ as a **per-family quantile of the true
response** rather than a fraction of `mu_max` — a new estimand, not a parameter change,
and one that must be registered before any family runs.

### 2.5 The `gated?` column, verified against the JSONs

`results/k1-replay-gate.json` measured the policy: `doe` 100/100 exact, `qlogei` 200/200
exact, `qlognei` 200/200 exact, worst \|Δ\| = 0.0 on all 500 rows, over d ∈ {6,8} ×
σ ∈ {0.25, 0.10}. Gate = exact for all three.

Campaigns actually compared to a committed value, recomputed by intersecting each result
file's `(instance, seed, arm)` keys with `results/e2-grid.json`:

| file | gated campaigns | silently ungated |
|---|---|---|
| `k6-designspace.json` | `doe` 50, `qlogei` 50, `qlognei` 50 | **`qlogei-add` 50, `qlogei-addonly` 50** |
| `k6-designspace-spread.json` | `lhs` 50, `sobol` 50, `random` 50 | none |
| `k6b-conservative.json` | `doe` 50, `qlogei` 50, `qlognei` 50 | **`qlogei-add` 50, `qlogei-addonly` 50** |
| `k6b-conservative-spread.json` | `lhs` 50, `sobol` 50, `random` 50 | none |
| `versionb.json` | **0 — no `gate_failures` key exists in the file** | all 250 |
| `step0-oracle-best.json` | `doe` 50 only | `qlognei`, `lhs`, `sobol`, `random`, `plate1_only`, `versionb` — 300 |

All five gated files report `gate_failures: []`.

---

## 3. The seven suspected gaps — verdicts

### 3.1 `versionb`/`versionb_random` exist only at γ=0.50, and the four AUC cells coincide with K6's γ=0.50 row — **CONFIRMED, and stronger than stated**

`scripts/run_versionb.py` (blob at `547b8af`, which produced the committed
`results/versionb.json`) computes `theta = tf * mu_max` with `mu_max = inst.optimum_value`
and has **no γ constant at all** — the file's own comment says a `GAMMA_FOR_AUC = 0.90`
was defined and never used, "so the AUC actually computed was at the gamma=0.50 row".
`scripts/run_k6_designspace.py` uses `tau = tf * tau_max(gamma, orc.sigma_rel)`, and
`tau_max(0.50, σ) = 1.0 · (1 − 0 · σ) = 1.0` exactly. The two thresholds therefore
coincide at γ=0.50 and nowhere else.

Measured on the shared arms:

| comparison | result |
|---|---|
| `versionb.json` `auc_{tf}` vs `k6-designspace.json` `auc_pred` at γ=0.50, arm `doe` | **200/200 bitwise identical**, worst \|Δ\| = 0.000e+00 |
| same, arm `qlognei` | **200/200 bitwise identical**, worst \|Δ\| = 0.000e+00 |
| `brier` on the same pairs | 254/400 bitwise; the rest differ by ≤ 3.9e-16 (the `optimum_value` = 1.0 ± 2e-16 float offset) |

So Version B's entire γ coverage is one point, K6's lowest-assurance corner. The
K6 γ ladder shows `tau_max` = 1.0000 / 0.8689 / 0.7896 / 0.6796 / 0.5888 / 0.4184 at
γ = 0.50 / 0.70 / 0.80 / 0.90 / 0.95 / 0.99, so γ=0.50 is also the only γ at which the
absolute τ is unconstrained by the noise floor.

**Caveat that must travel with this.** By Amendment C2's algebra the *latent* threshold is
γ-invariant, so AUC-against-truth genuinely does not depend on γ. What depends on γ is the
**region** `D_γ` and everything derived from it — `vol_pred`, `empty_pred`, `iou_pred`,
`fi_pred`. Version B has none of those (§3.2), so the γ ladder is missing exactly where it
would have bitten.

### 3.2 `versionb`/`versionb_random` have no IoU, no `sup_err`, no `grid_r2`, no false-inclusion@95 — **CONFIRMED**

The full key set of every row in `results/versionb.json` is: `alpha_star_{tf}`, `arm`,
`auc_{tf}`, `brier_{tf}`, `ce_contain_{tf}_{α}`, `ce_empirical_{tf}_{α}`,
`ce_empty_{tf}_{α}`, `ce_vol_{tf}_{α}`, `dim`, `instance`, `n_active`, `n_wells`,
`regret`, `rounds`, `seed`, `sigma`, `vorobev_dev_{tf}`.

Absent: `iou_pred`/`iou_latent`, `sup_err`, `grid_r2`, `fi_pred`/`fi_latent`,
`ce_false_in_{α}`, `vol_pred`, `empty_pred`, `box_vol_pred`, `true_frac_above_tau`.
`ce_empirical_*` (empirical containment) **is** present — so containment is covered and
false-inclusion is not, and those are different quantities.

### 3.3 No arm has any design-space metric on hartmann6/ackley/levy/rosenbrock — **CONFIRMED**

No `results/*.json` carries both a family key and a design-space metric key. The four
family files — `q42-families.json`, `q53-spread-gp-families.json`, `d20-rescore.json`,
`q59-hartmann-no-screen.json` — carry only regret-class columns (`bo_a`, `bo_c`, `doe_a`,
`doe_c_*`, `spread_a`, `spread_c`, `rule_a`, `oracle_best`, `rule_c`).
`docs/K6-TECHNICAL-REPORT.md` §6.4 states the same and is correct.

### 3.4 No arm has any design-space metric at d=8 or σ_rel=0.10 — **CONFIRMED**

All 11,450 design-space rows across the five files carry `dim: 6` and `sigma: 0.25`.
§6.4 of the technical report states this and is correct.

### 3.5 Oracle-best exists only for `doe` and `qlogei` (Q57) — **REFUTED, twice over**

This is the one suspected gap that is wrong.

1. **`results/q57-search-vs-id.json` itself has three arms, not two.** Every one of its 200
   rows carries `nei_oracle_best` (qLogNEI) as well as `doe_oracle_best` and
   `bo_oracle_best`; zero nulls. It spans d ∈ {6,8} × σ ∈ {0.25, 0.10}.
   `results/q55-oracle-best.json` carries `doe`/`bo` over the same four cells.
2. **`results/q59-hartmann-no-screen.json` carries `oracle_best` for four arms on
   hartmann6** — `qlogei`, `qlognei`, `doe_screened`, `doe_unscreened` — at d=6,
   σ ∈ {0.25, 0.10}. `results/q56-doe-ascent.json` carries `oracle_best` for `doe_ascent`.
3. **`results/step0-oracle-best.json` now exists and is committed** (at `6edf708`, after
   the brief was written). 350 rows, 7 arms at d=6 σ=0.25: `doe`, `qlognei`, `lhs`,
   `sobol`, `random`, `plate1_only`, `versionb`. `gate_failures: []`.

Two defects in `step0-oracle-best.json`, both found by this audit:

- **Its `versionb` arm is 40 wells, not 48.** `scripts/run_step0_oracle_best.py:52-57`
  builds plate 1 only and labels the row `arm: "versionb"`; the row carries
  `n_wells: 40` but no label field distinguishing it. Its `rule_a` is **bitwise identical
  (50/50, worst \|Δ\| = 0.000e+00) to `versionb.json`'s `versionb_random` regret**, and
  differs from `versionb.json`'s `versionb` regret by up to 0.2046. Any join on
  `arm == "versionb"` across the two files silently compares two different campaigns.
- **The gate covers `doe` only.** The module docstring at line 10 and the registration in
  `docs/OPEN-QUESTIONS.md` both say `doe` **and** `qlognei` must reproduce Q57; the code
  at line 66 tests `if arm == "doe"` and nothing else. This audit ran the missing check:
  `qlognei` oracle-best reproduces `q57·nei_oracle_best` at worst \|Δ\| = 0.000e+00, 50/50,
  and its rule A likewise. **The gate would have passed** — the defect is that it was never
  run, not that it fails.

### 3.6 `qlogei-add`/`qlogei-addonly` are UNGATED because `committed` is built from `e2-grid.json` only — **CONFIRMED, and the arms are UNGATABLE, not merely ungated**

The mechanism is exactly as suspected. `scripts/run_k6_designspace.py:161-162` builds
`committed` from `committed_rows()`, whose default path is `results/e2-grid.json`
(`src/boec/replay.py:141`). `results/e2-grid.json` contains seven arms — `qlogei`,
`qlognei`, `random`, `sobol`, `lhs`, `coord`, `doe` — and no kernel arms. Line 180 does
`ref = committed.get(...)` and line 181 guards `if ref is not None`, so 100 campaigns
(50 per arm) skip the gate silently. `scripts/run_k6b_conservative.py:135-136` is the same
code and skips the same 100. `_gate_tol` at line 66 would return 0.0 for these arms, so
the tolerance is not the issue; the missing key is.

Amendment A1 required "gate them against `results/q30-additive.json`". **That file does not
exist, has never existed in git history, has no `.gitignore` negation line, and is not on
disk.** `git log --all --diff-filter=A -- results/q30-additive.json` returns nothing.
The only committed Q30 artefact is `results/q30-additive.log`.

That log cannot serve as a substitute gate, and this is the part the technical report's
§6.11 does not reach:

| comparator, d=6 σ=0.25, Q30-style per-instance mean | `q30-additive.log` | recomputed from committed `e2-grid.json` |
|---|---|---|
| `doe` | 0.0958 | 0.0958 ✅ |
| `lhs` | 0.1270 | 0.1270 ✅ |
| `sobol` | 0.1724 | 0.1724 ✅ |
| `random` | 0.2216 | 0.2216 ✅ |
| `coord` | 0.1420 | 0.1420 ✅ |
| **`qlogei`** | **0.1666** | **0.1553** ❌ |
| **`qlognei`** | **0.1512** | **0.1532** ❌ |

The five non-optimiser comparators reproduce exactly; **the two optimiser-driven ones do
not.** `results/e2-grid.json` was first committed at `ae3295f` (2026-08-11 22:43); the Q30
log was committed at `daceb6b` (2026-08-11 11:14) and its own header records
`HEAD=3e83fa2` and a working directory of `/Users/alanakwan/…` — a clone whose
`e2-grid.json` was never shared. This is `docs/RESULTS.md`'s `provenance-flagged` /
D12 category exactly.

The consequence for the K6 numbers:

| quantity | `q30-additive.log` | regenerated, `k6-designspace.json` | Δ |
|---|---|---|---|
| `qlogei-add` mean regret | 0.1560 | **0.1483** | 0.0077 |
| `qlogei-addonly` mean regret | 0.1544 | **0.1623** | 0.0079 |
| paired `qlogei-add − qlogei` | **−0.0106** | **−0.0070** | 0.0036 |
| paired `qlogei-addonly − qlogei` | **−0.0123** | **+0.0071** | **sign flips** |

Both Δ are ~5× the effect Q30 reported (0.0015) and ~0.4 × SESOI. Whether the shift is a
regeneration failure or a consequence of the superseded comparator **cannot be determined
from committed files**. Until `results/q30-additive.json` exists at the current `e2-grid`,
these two arms and every A1 conclusion drawn from them are `CANNOT GATE`.

The Fix 1 registration (`docs/OPEN-QUESTIONS.md`, commit `4e14769`) proposes gating them
against `results/k6-designspace.json` instead. **That is circular under D12** — K6 is
itself a regeneration, so the gate would only report that the code agrees with itself. It
should be labelled as a reproducibility check, not a gate.

### 3.7 Version B has no gate block at all, and carries the headline — **CONFIRMED on the gate; PARTLY WRONG on the headline**

**Gate: confirmed.** The blob that produced `results/versionb.json`
(`provenance.git_sha = 547b8af`) contains no `GATE` path, no `_gate_tol`, no `committed`
dictionary, and writes no `gate_failures` key. The committed JSON's top-level keys are
`provenance`, `config`, `rows` — every other design-space file has a fourth,
`gate_failures`. Two of its five arms (`doe`, `qlognei`) had a committed comparator
available and were never compared; three (`versionb`, `versionb_random`, `plate1_only`)
had none, and two of those three are ungatable in principle.

**Headline: the attribution is wrong.** The technical report's §10 names the headline as
the safety result — the conservative excursion estimate failing its nominal joint level for
the screened classical arm at 0.155 / 0.420 / 0.510 against 0.50 / 0.80 / 0.95, contained
in 0 of 50 campaigns at τ_frac = 0.60, α = 0.50. Recomputed:

| source | doe, τ_f=0.60, fully contained | α=0.50 | α=0.80 | α=0.95 |
|---|---|---|---|---|
| `results/k6b-conservative.json` | **0 / 50** | 12/50 | 25/50 | |
| `results/versionb.json` | **0 / 50** | 12/50 | 25/50 | |

The two agree bitwise, and `k6b-conservative.json` **is gated** (`doe` 50/50 against
`e2-grid.json`, `gate_failures: []`). **So the headline rests on a gated file and is
independently reproduced by an ungated one.** What Version B *uniquely* carries — and what
therefore rests on no gate — is the rounds axis, the two registered kills, and the
`versionb`/`versionb_random` contrast. Those are the ungated claims, not the headline.

The `doe` alpha\* worked proof also reproduces: `k6b-analysis.json` gives `alpha_star`
`doe` = 1.0000 at τ_f = 0.60, the highest of eight arms, and 0.7875 at 0.75, again the
highest — against 0 of 50 empirical containment. VALIDATED and MODEL-INTERNAL point in
opposite directions on the same arm, as the brief states.

---

## 4. The four blockers

### B1 — Is `mu_max` normalised to 1.0 on hartmann6/ackley/levy/rosenbrock?

**YES, exactly 1.0 — arithmetically. NO — scientifically.**

Every runner that touches a non-Hill family wraps it in `oracles.UnitScaled`:
`scripts/run_q42_families.py:105`, `scripts/run_q53_spread_gp_families.py:129` and `:161`,
`scripts/run_q59_hartmann_no_screen.py:114`, `scripts/rescore_d20.py:68`.
`UnitScaled` is `src/boec/oracles.py:327`; its `optimum_value` property at
`src/boec/oracles.py:381-382` is a literal `return 1.0`, and its `f` at
`src/boec/oracles.py:373-374` is the affine map
`1 − (top − f_raw)/scale` with `scale = top − floor` (`:370-371`), `top` the analytic
optimum (`:363`) and `floor` the minimum over 65,536 Sobol points at a fixed seed (`:364`).
The raw optima it normalises are Hartmann6 3.32237 (`:167-168`) and 0.0 for ackley
(`:192-193`), levy (`:228-229`) and rosenbrock (`:256-257`).

The Hill oracle is normalised to 1.0 to within float error only: over
`load_ensemble(6)` the distinct values run 0.9999999999999997 to 1.0000000000000002.
That ±2e-16 is what makes `versionb`'s Brier differ from K6's in the last ULP (§3.1) and is
otherwise harmless.

So `theta = tau_frac · mu_max` is the *same absolute number* on all five families, and the
threshold grid is arithmetically comparable. **It is not scientifically comparable**, and
§2.4 is the measurement: at τ_frac = 0.60 the true superlevel set covers 0.0% of the box on
ackley, 0.8% on hartmann6, 73.6% on hill, 85.7% on levy and 95.6% on rosenbrock. Every
cross-family table at fixed `τ_frac` is therefore comparing incommensurable events, and on
ackley the metrics are literally undefined.

**Recommendation.** Register τ per family as a quantile of `f` on the registered grid —
e.g. τ = the (1 − p) quantile for p ∈ {0.30, 0.10, 0.03, 0.01} — with the absolute τ and
`tau_max(γ, σ)` reported alongside so the noise-floor argument is still visible. This is a
new estimand and must be registered before any family campaign is run.

### B2 — Is the noise model relative on the non-Hill families?

**YES — bit-for-bit the same model, on every family.** Confirmed per family by
construction path, not by inspection of results.

Every family goes through `boec.torch_oracle.TorchEvaluator`. Its `evaluate`
(`src/boec/torch_oracle.py:132-139`) is

```
eps = self._rng.normal(0.0, self.sigma_rel, size=f.shape)     # :135
eta = self._rng.normal(0.0, self.sigma_add, size=f.shape)     # :136
y   = f * (1.0 + eps) + eta                                   # :137
```

`BiphasicOracle.observe` (`src/boec/torch_oracle.py:225-241`) is the identical three lines
at `:239-241`, and `BiphasicOracle.evaluate` (`:248-250`) just delegates. Both classes
default `sigma_add = 0.01` (`:109`, `:178`) and share `_plug_in_yvar` (`:73-80`).

There is **no additive-only family anywhere in the codebase**. The construction is:
`UnitScaled(FAMILIES[fam](dim))` → `TorchEvaluator(oracle, sigma_rel=σ, seed=s)` in
`run_q42_families.py:105/112`, `run_q53_spread_gp_families.py:129/131` and `:161/169`,
`run_q59_hartmann_no_screen.py:114/167`. `UnitScaled` exists **precisely** to keep the
model relative: its docstring at `src/boec/oracles.py:333-341` states that every negated
standard test function has optimum value exactly 0, so without rescaling "the
multiplicative term vanishes precisely at the optimum".

Therefore `tau_max = mu_max·(1 − z·σ_rel)` re-derives identically on all five families and
the grid does **not** move. Verified numerically: `tau_max` at σ_rel = 0.25 is
1.0000 / 0.8689 / 0.7896 / 0.6796 / 0.5888 / 0.4184 across γ, and at σ_rel = 0.10 it is
1.0000 / 0.9476 / 0.9158 / 0.8718 / 0.8355 / 0.7674 — the same numbers for every family.

**One correction, small but real.** `designspace.tau_max` ignores `sigma_add`. The exact
predictive floor is `1 − z·sqrt(σ_rel² + σ_add²)`, which at σ_rel = 0.25, σ_add = 0.01,
γ = 0.95 is 0.58805 against the reported 0.58879 — 7.4e-4 optimistic. The K6 runner *does*
include `sigma_add` in `sigma_pred`, so the map and the reported ceiling use slightly
different noise models. It changes no verdict at σ_rel = 0.25; at σ_rel = 0.10 the relative
error triples (σ_add is 10% of σ_rel there) and it should be corrected before the σ=0.10
cell is run.

**One caveat for levy at d=8.** `UnitScaled`'s floor is the minimum over a *finite* Sobol
sample, so `f` can go slightly negative off-sample — measured min −0.023 on the levy d=8
grid. Where `f < 0` the relative-noise SD is `|f|·σ_rel`, which is fine, but the plug-in
`sigma_pred = |σ_rel·μ|` in the K6 runner uses the posterior mean and will behave oddly
near the zero crossing. Report it; do not patch `UnitScaled`, which is a committed input.

### B3 — Ackley: does the CCD-evaluates-the-centre objection transfer to a design-space deliverable?

**The case, both ways, with measurements. Recommendation at the end; not decided here.**

**The mechanism is confirmed and it is worse than "the CCD evaluates the centre".** The
*screen* does too. `screening_design` appends `n_centre` rows of coded zeros
(`src/boec/designs.py:314`), `central_composite` appends `n_centre` more
(`src/boec/designs.py:260`), `scale_to_box` maps coded 0 to the box midpoint
(`src/boec/designs.py:329`), and `run_doe_arm` runs the screen on the **full** box at
`n_centre_stage1 = 4` (`src/boec/doe.py:197`, `:273`, `:285`) plus `n_centre_stage2 = 3`
(`:198`, `:274`). Measured on the real path:

| family | exact box-centre rows in `X_visited` | min Chebyshev distance to the optimum | max true value visited (optimum = 1.0) |
|---|---|---|---|
| **ackley** | **7** | **0.0000** | **1.000000** |
| levy | 7 | 0.0500 | 0.995989 |
| rosenbrock | 7 | 0.2441 | 0.999651 |
| hartmann6 | 7 | 0.3500 | 0.433737 |

`scripts/run_q42_families.py:212-214` already refuses to report rule A on such a family:
*"rule A VOID: this function's optimum is the exact box centre, and every screen and CCD
includes centre runs, so the DoE design contains the answer"*, and
`optimum_at_design_centre` is `True` for ackley and `False` for the other three
(`results/q42-families.json`, all 400 rows).

**The case for keeping ackley IN.**

1. The objection as stated is about **regret**. A design-space deliverable does not score
   the best visited point; it scores a map over the whole box. Containing the argmax buys
   a design nothing on IoU, Brier or containment away from the peak.
2. Ackley is the project's registered *deceptive* family and the one place a spread design
   is most likely to lose. Dropping it removes the hardest case, which is a
   selection-on-the-answer move of exactly the kind `docs/RESULTS.md` exists to catch.
3. The degeneracy is checkable and reportable: `optimum_at_design_centre` is already a
   committed column, so the arm's advantage is labelled rather than hidden.

**The case for taking ackley OUT.**

1. **It is not a judgement call at the registered τ grid — the metrics do not exist.**
   §2.4: prevalence 0.00000 at all four τ_fracs, both dimensions. AUC, IoU, false-inclusion
   and empirical containment all return `nan`. There is no table to argue about.
2. Even at a τ low enough to make the set non-empty (τ < 0.41 at d=6), the `doe` arm has
   **7 wells at the exact optimum** and every other arm has none. The GP's posterior SD
   collapses there and its mean is pinned at the true peak, so `D_γ` around the peak is a
   property of where the design was told to look. That *does* transfer from regret — the
   map is built from the same wells.
3. Levy and rosenbrock have the same disease in a milder form (max true value visited
   0.996 and 0.9997) and they are *not* flagged by `optimum_at_design_centre`, so the
   existing flag under-reports the problem.

**Recommendation, for the human to accept or reject.** Run ackley, but **not** at the
`τ_frac`-of-`mu_max` grid, and never in a pooled cross-family table. Specifically:

- Re-register τ per family as a quantile of `f` (B1's recommendation). Ackley then has a
  non-empty, non-degenerate superlevel set by construction.
- Report `optimum_at_design_centre` and **min Chebyshev distance from the design to the
  optimum** as a committed column for every family and arm, so the geometry advantage is a
  number rather than a footnote.
- Treat ackley's result as a **declared sensitivity**, never as a headline cell, and say in
  the write-up that the classical arm visits ackley's optimum 7 times by construction.
- If the human prefers a single decision: **ackley is IN for the map metrics and OUT of
  every regret-class contrast**, which is what Q42 already does.

### B4 — Does `replay.regenerate` support the non-Hill families and the Version B arms?

**Families: NO, but the change is small and — measured — the result is bit-exactly
gateable. Version B arms: NO, and the runners, not `replay`, are the right place to fix
it.**

**Current capability**, from `src/boec/replay.py`:

| supported | how |
|---|---|
| arms `qlogei`, `qlognei` (`OPTIMISED_ARMS`, `:88`) | `Campaign` + `AcqConfig(kind=arm)`, `:173-180` |
| arms `qlogei-add`, `qlogei-addonly` (`KERNEL_ARMS`, `:90`) | same, with `kernel_structure` |
| arms `lhs`, `sobol`, `random` (`SPREAD_ARMS`, `:98`) | `static_design` + one `evaluate`, `:182-187`; the 20-ordering mean at `:201-216` reproduces `run_e2.static_curve`'s arithmetic exactly |
| arm `doe` (`DETERMINISTIC_ARMS`, `:86`) | `run_doe_arm`, `:188-195` |
| `hill` only | `instance_by_id` → `load_ensemble(dim)` at `:169`; `BiphasicOracle(inst, …)` at `:171` |
| budget 48 only | `BUDGET = 48` at `:80`, documented as "not a parameter" |

**Blocking lines for families:** `:169` (Hill-only lookup), `:171` (Hill-only oracle),
`:221-222` (`inst.optimum_value`). `:209`'s `n_init = 2*dim + 2` and the `N_ORDERINGS = 20`
mean at `:83`/`:212` are `run_e2` arithmetic and apply only when gating against
`e2-grid.json`; family gate targets do not use them.

**The change.** Add one keyword, `family: str = "hill"`, and a factory:

```python
FAMILY_ORACLE = {                      # UnitScaled + TorchEvaluator, exactly as Q42 does
    "hartmann6": lambda d: Hartmann6() if d == 6 else Embedded(Hartmann6(), dim=d, seed=0),
    "ackley":     lambda d: Ackley(dim=d),
    "levy":       lambda d: Levy(dim=d),
    "rosenbrock": lambda d: Rosenbrock(dim=d),
}
```
with `instance` reinterpreted as the family label when `family != "hill"` (family
campaigns are keyed by `(family, dim, sigma, seed)` — there is no `instance_id`), and
`optimum_value` read off the oracle rather than off a `HillInstance`. Two details are
load-bearing and must be copied from `scripts/run_q42_families.py:112` and `:125`: the
campaign and the DoE arm each get their **own fresh** `TorchEvaluator` at the same seed, so
the noise streams start where Q42's did.

**Gate targets exist, and the gate passes.** `q42-families.json`'s `bo_a` is computed by
`opt - reported_best_curve(ev.truth(X), Y)[-1]` (`scripts/run_q42_families.py:115`) — the
identical expression `replay.scored_curve` uses (`src/boec/replay.py:136-138`,
`:221`). This audit ran the check live on four campaigns, hartmann6, d=6, σ_rel=0.25:

```
qlogei  seed=0  44.6s  rule_a=0.22786852   q42 bo_a = 0.22786852462983   delta = 0
qlogei  seed=1  32.0s  rule_a=0.28572998   q42 bo_a = 0.28572997649010   delta = 0
qlognei seed=0  69.1s  rule_a=0.16996992   q59 qlognei.rule_a = 0.16996992086882   delta = 0
qlognei seed=1  56.7s  rule_a=0.24426081   q59 qlognei.rule_a = 0.24426080538068   delta = 0
```

**Family campaigns regenerate bit-exactly and are gateable at \|Δ\| = 0** for both BO arms,
at ~38 s (`qlogei`) and ~63 s (`qlognei`) per campaign. Available gate columns:

| arm | committed column | families | cells |
|---|---|---|---|
| `qlogei` | `q42-families.json · bo_a`, `d20-rescore.json · bo_a` | all four | d ∈ {6,8} × σ ∈ {0.25, 0.10}, 25 seeds |
| `doe` | **`d20-rescore.json · doe_a_new`** — *not* `q42-families.json · doe_a`, which is the pre-D20 column (`docs/RESULTS.md:1459`). Means differ: ackley 0.0000 → 0.0123, hartmann6 0.5444 → 0.5623, levy 0.0040 → 0.0392, rosenbrock 0.0003 → 0.0328 | all four | same |
| `qlognei` | `q59-hartmann-no-screen.json · rows[].arms.qlognei.rule_a` — **verified live above** | **hartmann6 only** | d=6 × σ ∈ {0.25, 0.10}, 25 seeds |
| `lhs`/`sobol`/`random` | **none** | — | ungatable on families; one `evaluate` call, so reproducibility is the RNG's |

**Version B arms.** `versionb`, `versionb_random` and `plate1_only` are two-plate
campaigns built inline in `scripts/run_versionb.py::_two_plate`, which fits a GP, calls
`batch_lse` and evaluates twice. `replay.regenerate` cannot build them and — under the
plan's own File Structure table, which gives `replay.py` the responsibility
"regenerate a committed campaign; return `(X, Y, Yvar)` + provenance. **Nothing else.**" —
should not learn to. Teaching it would create `replay → surrogate, designspace, lse`
dependencies and put a GP fit inside the module every gate depends on.

**Recommended shape: a campaign-builder callable.**

```python
def regenerate(instance, dim, sigma, seed, arm, *, family="hill", builder=None):
    ...
    if builder is not None:
        X, Y, Yvar, kept, held = builder(orc, dim, seed)
```

`run_versionb.py` passes its own `_two_plate` and keeps the LSE logic where it already
lives; `replay` keeps the oracle construction, the scoring rule and the provenance in one
place, which is the property that makes the gate meaningful. `plate1_only` needs no builder
— it is `lhs` at 48 wells, measured identical to worst \|Δ\| = 4.44e-16.

**Hours estimate — engineering only, excluding compute.**

| item | hours |
|---|---|
| `family=` + `FAMILY_ORACLE` + oracle/optimum plumbing in `replay.py` | 2 |
| `builder=` hook + `run_versionb.py` refactored onto it | 1.5 |
| `tests/test_replay.py`: family regeneration reproduces `q42·bo_a` and `d20·doe_a_new` at \|Δ\|=0; builder path reproduces `versionb.json`; unknown family raises | 2.5 |
| Family-aware gate loader (family columns live in three files with three key schemas) | 2 |
| Runner plumbing: `--family`, `--dim`, `--sigma` through `run_k6_designspace.py` and `run_k6b_conservative.py`, and a per-family τ registration if B1's recommendation is taken | 2 |
| Register the new questions in `docs/OPEN-QUESTIONS.md` and commit before any runner changes | 1 |
| **total** | **11 hours**, one working day plus a margin |

**The τ re-registration (B1) is the real dependency, not the code.** Without it the family
runs produce a table of `nan` for ackley and near-`nan` for hartmann6, and 11 hours of
engineering buys nothing.

---

## 5. What Phases 1–4 must run, ranked

Priced from measured per-campaign wall-clock. Regeneration costs from
`results/k1-replay-gate.json` (`secs` per row); scoring costs from the run logs.

| operation | measured cost |
|---|---|
| regenerate `doe` | 0.1 s |
| regenerate `qlogei`, d=6 σ=0.25 | 81.2 s (d=6 σ=0.10: 17.3 s; d=8: 15–16 s) |
| regenerate `qlognei`, d=6 σ=0.25 | **189.9 s** (d=6 σ=0.10: 23.5 s; d=8: 16–18 s) |
| static arm, no regeneration | ~0 s |
| K6 scoring, 24 (γ,τ) cells on the 20k grid | 2.0 s / campaign |
| K6b scoring, 2k subset × 512 draws × 4 τ | 0.8 s / campaign |
| Version B two-plate build + full scoring | 1.9 s / campaign |
| regenerate `qlogei` on hartmann6, d=6 σ=0.25 | ~38 s (n=2: 44.6, 32.0) |
| regenerate `qlognei` on hartmann6, d=6 σ=0.25 | ~63 s (n=2: 69.1, 56.7) |
| K6 metrics on a family, static arm, 4 τ | ~1.0 s / campaign |

| # | work | why | cost | blocked? |
|---|---|---|---|---|
| **P1** | **Re-run Q30 against the current `e2-grid.json` and commit `results/q30-additive.json`** | Without it `qlogei-add`/`qlogei-addonly` are `CANNOT GATE`, and §5.5 of the technical report (A1's "cleanest figure") rests on 2,800 ungated rows whose regeneration moves the paired contrast by up to a sign flip | 200 campaigns; σ=0.25 at ~35 s and ~107 s, σ=0.10 at ~17 s → **≈ 2.6 CPU-h** | no |
| **P2** | **Gate Version B, and re-run it with the γ ladder and the four missing columns** (IoU, `sup_err`, `grid_r2`, false-inclusion at each γ) | Closes §3.1 and §3.2 in one run. Version B currently has one γ and no region metric that depends on γ | re-run is 862 s; ×6 γ ≈ **≈ 1.5 CPU-h** | no. *(A gate landed at `c8347f1` — see §7)* |
| **P3** | **Fill the three missing (d, σ_rel) cells: (6, 0.10), (8, 0.25), (8, 0.10)** for K6 + K6b, all 8 arms | The only axis that is `NOT RUN` rather than `CANNOT RUN`, has committed gate targets for 7 of 8 arms, and `tau_max` moves from 0.589 to 0.836 at σ=0.10 so the whole emptiness structure changes | ≈ 1.3 h + 1.4 h + 1.4 h ≈ **4.1 CPU-h** | **`doe` has no d=8 column in `e2-grid.json`** — use `results/e2-doe-d8.json`. Fix `tau_max`'s missing `σ_add` first (B2) |
| **P4** | **Add `coord` to the primary cell** | It is a committed arm at d=6 σ=0.25 with 50 gated campaigns, currently absent from every design-space file. It is the cheapest way to widen the 8-arm ranking to 9 | regenerate + score, ≈ **10 CPU-min** | no |
| **P5** | **Re-register τ per family as a response quantile** (B1) | Without it P6 is impossible for ackley and meaningless for hartmann6 | analysis + registration, ~2 h human | no |
| **P6** | **Family coverage: hartmann6, levy, rosenbrock (and ackley under P5's grid)** | The only remaining `NOT RUN` axis of substance; Q42/Q53 already establish that this project's spread-vs-BO results are landscape-shaped | engineering 11 h (B4) + compute: static arms 4 fam × 2 d × 2 σ × 25 seeds × 4 arms × 1 s ≈ 0.9 h; BO arms ≈ 4 × 2 × 2 × 25 × (38 s + 63 s) ≈ **11.2 CPU-h**; total ≈ **12 CPU-h** | **BLOCKED on P5.** Ackley is `CANNOT RUN` at the current grid; hartmann6 is degenerate at τ_f ≥ 0.85; `qlognei` has no family gate column outside hartmann6, and no family has a gate column for `lhs`/`sobol`/`random` |
| **P7** | **Murphy calibration–refinement decomposition, 10 equal-count bins** (Amendment A5) | Registered, never run, and it is the half of Brier that A5 argues is the new part | no new campaigns, but the maps are not stored — needs a K6 re-score: ≈ **4.4 CPU-h** at the primary cell, or fold into P2/P3 for free | no |
| **P8** | **σ_rel ∈ {0.20, 0.15}** (Amendment A5) | Converts Stage 0 into a lookup | 2 × 4.4 h ≈ **8.8 CPU-h** | **`CANNOT GATE` by construction** — no committed campaign exists at either σ. A5 already labels them exploratory; keep them out of every confirmatory contrast |

**Phases that are impossible as currently specified:**

- **Any cross-family design-space table at fixed `τ_frac`** — impossible until P5. §2.4 is
  the proof: prevalence spans 0.00000 to 0.95550 at one `τ_frac`.
- **Any design-space metric on ackley at the registered grid** — impossible, full stop.
  AUC, IoU, false-inclusion and containment are all `nan`.
- **Gating `qlogei-add`/`qlogei-addonly` against anything currently committed** —
  impossible until P1. The proposed fallback (gate against `k6-designspace.json`) is
  circular under D12.
- **Gating `versionb`/`versionb_random`** — impossible in principle. They have no
  comparator and never will. Their only guarantee is seed determinism.

---

## 6. Defects found by this audit that were not on the list

1. **`step0-oracle-best.json`'s `versionb` row is a 40-well campaign labelled as the
   48-well arm**, and its `rule_a` is bitwise identical to `versionb_random`'s regret
   (§3.5). Add a `label` or rename the arm `versionb_plate1`.
2. **`step0-oracle-best.json` gates `doe` only**, contrary to its own docstring and
   registration (`scripts/run_step0_oracle_best.py:66`). The missing `qlognei` check was
   run here and passes at \|Δ\| = 0.
3. **`versionb_random`'s 8 plate-2 wells have zero rule-A content.** In **0 of 50**
   campaigns did any of them beat the best of the 40 LHS plate-1 wells, so its regret
   *is* the 40-well regret. The `versionb − versionb_random = −0.0091, p = 0.0117`
   contrast is therefore "LSE plate 2 against no plate 2", not "LSE against random". For
   contrast: an LSE plate-2 well beat plate 1's best in **8 of 50**.
4. **`results/q42-families.json` still carries the pre-D20 `doe_a` column.** Already noted
   at `docs/RESULTS.md:1459`, repeated here because it is the obvious and wrong gate target
   for a family-aware `regenerate` (§4, B4).
5. **`designspace.tau_max` omits `σ_add`** (§4, B2). 7.4e-4 optimistic at σ_rel = 0.25;
   proportionally 10× worse at σ_rel = 0.10, which P3 will run.
6. **`k6·box_vol_pred` mixes 4-D and 6-D volumes** — already `docs/K6-TECHNICAL-REPORT.md`
   §6.12, confirmed here (`n_active` is 4 in 1,200/1,200 `doe` rows and 6 elsewhere).
   Neither analysis script reads the column, so nothing has propagated.
7. **Two "AUC"s share a name.** `e2-grid.json · auc_post_init` is a regret-curve integral
   (`scripts/run_e2.py:178`); `k6 · auc_pred` is a map ranking statistic. Nothing currently
   conflates them; a coverage table built by key-name matching would.

---

## 7. What moved while this audit was running

The repository advanced from `1444969` to `c8347f1` during the audit. Relevant commits:

| commit | effect on this document |
|---|---|
| `6edf708` | `results/step0-oracle-best.json` and its runner became **tracked**. §3.5 reflects the committed state |
| `4e14769` | Registers Fix 1, including the proposal to gate the kernel arms against `k6-designspace.json` — flagged as circular in §3.6 |
| `cee1f45` | **Amendment E2's exclusion-radius claim does not reproduce.** `src/boec/lse.py`'s new docstring records the radius binding in 22 of 50 live campaigns, against E2's "0%". E2's numbers were measured on *random* batches; `batch_lse` takes a greedy argmax. Does not affect any cell above |
| `19f05ac`, `c8347f1` | `run_versionb.py` rewritten: gains a gate against its own committed column, the E1/E2 diagnostics, and a sixth arm `versionb_predictive`. **It now writes `results/versionb-predictive.json` and refuses to overwrite `results/versionb.json`.** §3.7's gate finding therefore describes the blob at `547b8af` that produced the committed file, which is still the file every Version B number is read from. P2's gate half is addressed; P2's γ-ladder half is not |

Untracked at the time of writing: `results/fix1-terminal-rule.{json,log}`,
`results/versionb-predictive.{json,log}`, `scripts/run_fix1_terminal_rule.py`,
`scripts/analyse_fix1.py`, `scripts/analyse_versionb_predictive.py`,
`tests/test_fix1_terminal_rule.py`. Under `docs/RESULTS.md` rule 1 none of their numbers is
citable yet.

---

## 8. Reproduction

Every number in this document is either read from a committed `results/*.json` under the
key named in the cell, or was recomputed by one of the following, all read-only:

```bash
# arm / condition / metric coverage, and the gated-vs-ungated split
.venv/bin/python -c "import json;from pathlib import Path;from collections import Counter; \
  d=json.loads(Path('results/k6-designspace.json').read_text()); \
  print(Counter((r['arm'],r['dim'],r['sigma'],r['gamma']) for r in d['rows']))"

# suspected gap 1: versionb AUC vs K6 gamma=0.50, bitwise
# suspected gap 6: Q30 log comparators vs the committed e2-grid
# B1: superlevel-set prevalence per family on the registered grid
# B3: box-centre rows in the DoE design, per family
# B4: family regeneration against q42-families.json · bo_a
```

The five verification scripts were run under `.venv/bin/python` from the repository root at
`HEAD = 1444969`. `results/q30-additive.json` was confirmed absent with
`git log --all --diff-filter=A --name-only -- results/q30-additive.json` (empty) and
`ls results/q30-additive.json` (no such file).
