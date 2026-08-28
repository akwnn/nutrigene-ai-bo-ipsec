# SPADE Certificate Improvement Decisions

**Status:** binding implement / do-not ledger for certificate work  
**Date:** 2026-08-28 (renewed after meanmarg gate diagnosis + `origin/codex/spade-gate-fix` merge)  
**Audience:** next session implementing SPADE certificate changes  
**Sources:**
- Manufacturing recovery: `2026-08-26-spade-manufacturing-certificate-recovery-design.md`
- EC differentiation roadmap: `docs/superpowers/plans/2026-08-27-spade-ec-differentiation-action-plan.md`
- Remote branches reviewed: `origin/codex/spade-gate-fix` (**merged**), `claude/spade-certificate-targeted-policy` (bench only; not registered)

**Scope:** computational / synthetic certificate honesty only. Does not reopen
Plate-2 targeting as the manufacturing selling point. Does not authorize paper
claims beyond what confirmatory gates pass.

---

## 1. Goal

Make SPADE the **best manufacturing method** on registered evidence: non-empty
qualified operating region with empirical truth containment ≥ 0.9, **fewer culture
rounds than qLogNEI48**, and non-inferior setpoint/map secondary endpoints — only
after `SELECTED` + `POWERED` + lockbox PASS.

When evidence is weak, **abstain** with a stated reason rather than issue a false window.

Preserve **both** workstreams:

- **Alana:** joint manufacturing recovery (smallest CE, assay noise, LOO-tail,
  inflation floor, Vmax, digests, development runners, durable ops).
- **Joseph:** certificate R&D modules, mean-marginalisation, selfcalib, top-k /
  bagged / certstraddle research, real iPSC errata.

---

## 2. Product principle (locked)

SPADE’s certificate upgrade path is:

> **Mean-marginalise (ordinary kriging) + inflate latent uncertainty + prefer small
> regions + cap volume + abstain honestly.**

It is **not**:

> Smarter failure detectors, SNR run-time switches, family-library caps, or
> resurrecting Plate-2 boundary targeting as the primary fix.

---

## 3. DO IMPLEMENT — ordered queue

### 3.1 Completed gates (archived — do not resume)

| Digest | Study suffix | Outcome | Archive |
|---|---|---|---|
| `681947bc…` | floor15-loo-tail | **FAIL** 0 survivors | `historical-mfg-cert-floor15-loo-tail-gate-fail/` |
| `1c5c3b7e…` | floor15-loo-tail-meanmarg | **FAIL** 0 survivors | `historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail/` |

**Diagnosis (evidence, 2026-08-28):**

1. **Model-internal containment is blind to truth.** Failed levy runs still show
   `certificate_selection_containment` ≈ 0.97–0.99 while `certificate_empirical_containment`
   is False (E3 latent coverage 0.76–0.82 vs nominal 0.95; KR §1(a)).
2. **Levy is the binding family.** Hill emp 1.0 on `spade-o32-staged`; levy best
   `spade-o32-validity_gated` emp **0.90** but hill emp **0.875** on that arm;
   complementary pairing — no single arm clears both.
3. **Meanmarg helped but did not break the plateau.** Levy emp 0.75 → 0.875
   (floor15 → meanmarg on o32-staged); validity_gated levy 0.889 → **0.90**.
4. **Answer-rate floor binds some arms.** `spade-o40-staged` levy emp 1.0 but
   ans 0.33 — fails ans≥0.5.

Do **not** start full 5×50 on failed digests.

### 3.2 Merged protocol base (current code on `main`)

| Knob | Value | Owner |
|---|---|---|
| `certificate_volume_rule` | `smallest` | Alana |
| `predictive_observation_noise` | `assay_relative_additive` | Alana |
| `latent_draw_inflation` | `loo_calibration_tail` | Alana (+ Joseph selfcalib) |
| `latent_inflation_floor` | `1.5` | Alana (KT-5; **next: 2.0 trial**) |
| `certificate_max_volume` | `0.001` | Alana |
| `mean_marginalisation` | `true` | Joseph |

**Joseph modules in tree:**

| Module | Role | Product default? |
|---|---|---|
| `selfcalib.py` | LOO residuals / inflation / tail | **Yes** |
| `meanmarg.py` | Ordinary-kriging covariance | **Yes** |
| `topk.py` | Finite-set certification | Research only |
| `bagged.py` | Intersect bootstrap certs | Research only |
| `certstraddle.py` | Cert-frontier acquisition | Research only (see §3.8) |
| `selectionblind.py` | Selection-blind covariance | **No** (KW fail) |
| `resolution.py` | `k_eff` | **No** (KR fail) |

### 3.3 Confirmatory infrastructure — **DONE** (`origin/codex/spade-gate-fix` merged 2026-08-28)

Merged into `main`: hardened `select_spade_protocol.py`, `run_spade_lockbox.py`,
`analyse_spade_lockbox.py` + tests. Required before any LOFO/lockbox claim.

### 3.4 Phase A — Instrumentation (next code change)

1. Persist `latent_inflation_factor` and `certificate_abstention_reason` in scores
   (`volume_cap`, `no_feasible_ce`, `map_disagreement`, `issued`).
2. Add `scripts/analyze_gate_failures.py` for archived shard replay.
3. Tests in `tests/test_spade_study.py`.

**Gate:** git-clean REGISTERED runs; no protocol digest change in this phase alone.

### 3.5 Phase B1 — Scalar recovery: `latent_inflation_floor: 2.0` (**NEXT GATE**)

**Hypothesis:** KT-5 grid shows c=2.0 truth 1.0 (lower answer rate). Levy failures
are 1-in-8–1-in-10 marginal leaks at floor 1.5; raising floor widens draws
monotonically.

| Field | B1 value |
|---|---|
| `latent_inflation_floor` | **2.0** (only change from `1c5c3b7e`) |
| study_id | `…-floor20-loo-tail-meanmarg-2026-08-28` |
| All else | unchanged (meanmarg, LOO-tail, smallest, Vmax, α=0.95) |

**Pre-gate:** hill+levy keys 0–15; ans≥0.5 & emp≥0.9 both; ≥1 SPADE survivor.

**Falsification:** emp unchanged on levy o32-staged/validity_gated while ans drops
below 0.5 → proceed to B2 without further floor increases.

### 3.6 Phase B2 — Scalar recovery: raise assurance `alpha` (if B1 fails)

Preregister `reliability.alpha` ∈ {0.98, 0.99} per KT Lever A
(`SPADE-ASSURANCE-CALIBRATION-SPEC.md`). Requires **KT-2 paired monotonicity** and
**KT-3 answer rate ≥ 0.30** at full scale.

New digest per α value; never append to B1 shards.

### 3.7 Phase B3 — Abstention policy (if B1+B2 improve emp but ans blocks)

Offline replay on archived meanmarg rows first:

- Abstain `map_disagreement` when `map_iou < τ_map` (preregister τ_map on gate grid).
- Abstain when selection passes but map symmetric difference > 0.30.
- Goal: convert would-be false positives to honest abstentions; improve emp among answered.

### 3.8 Research track — certificate-targeted acquisition (NOT registered)

Branch `claude/spade-certificate-targeted-policy` (commit `9c51799`):

- Fourth policy using Joseph `certstraddle` (contour-straddling batches).
- **NOT** in registered 9-arm set (would change arm digests).
- Bench (`bench_certificate.py`, keys 18–29): straddle ρ=0.9 + κ=1.5 → containment
  **0.898**, LB95 **0.797** vs sobol48+κ=1.5 → 0.769 — directionally positive but
  **does not clear LB95 ≥ 0.90**; McNemar p=0.146 vs κ alone.

**Decision:** Keep as Phase H research spike; adopt into registered arms only after
a frozen spec amendment and new 12-arm digest — not before scalar B1 gate.

### 3.9 Parallel winning narrative — multi-CQA synthetic (**PASS**)

`results/spade-multi-cqa-benchmark.json`: joint containment **1.0** on `aligned` and
`moderate_conflict` with same stack (floor 1.5, meanmarg, smallest). Use for EC
differentiation manuscript per `2026-08-27-spade-ec-differentiation-action-plan.md`.
**Does not** substitute for scalar manufacturing gate or overturn `NO_SELECTION` on
joint v1.

---

## 4. DO NOT IMPLEMENT

| Item | Source verdict | Why banned |
|---|---|---|
| `k_eff` as transfer / filter | KR **FAIL** | Does not transfer |
| `kappa_tail` as cross-family conditioner | KS **FAIL** | Not a detector |
| Threshold SNR run-time detector | **RETRACTED** | Not significant |
| Family-library volume caps as deployable default | Lab-only | One unknown landscape |
| Selection-blind covariance as honesty fix | KW **FAIL** | Makes gap worse |
| Treating `c=1.5` as α-general | KT-7 **FAIL** at α=0.5 | Claim stays α=0.95 |
| Publishing KT-5 LB as 0.9377 without erratum | Erratum | SPADE-alone LB is 0.9019 |
| Finite-set / top-k as confirmed SPADE win | Exploratory | Needs own calibration |
| Merging into live gate worktree mid-run | Process | Corrupts digest / resume |
| Plate-2 targeting as manufacturing primary | KF-3 / hierarchy | Tertiary only |
| Adding cert-targeted policy without new digest | Process | 9→12 arms = registration |

---

## 5. Paper vs product

| Material | Paper | SPADE product |
|---|---|---|
| Scalar recovery + floor | Only after SELECTED+powered+lockbox | B1→B2→B3 queue |
| Mean-marginalisation | Methods + safety limitation | **Yes** |
| Multi-CQA joint overlay | EC differentiation primary | **Yes** (benchmark PASS) |
| Cert-targeted acquisition | Future work / bench only | Not default |
| KR/KS detector fails | Negative Discussion | **No** |
| Real iPSC result | Only after human signoff | meanmarg motivation |

---

## 6. Implementation checklist

- [x] Merge Joseph branch (meanmarg, selfcalib modules)
- [x] Wire `mean_marginalisation` into scoring
- [x] Meanmarg gate hill+levy 0–15 (`1c5c3b7e…`) — **FAIL**, archived
- [x] Multi-CQA benchmark PASS
- [x] Merge `origin/codex/spade-gate-fix` (LOFO/lockbox hardening)
- [ ] Phase A instrumentation (abstention reasons + inflation in scores)
- [ ] Phase B1 gate: `latent_inflation_floor: 2.0` new digest
- [ ] Phase B2 if needed: α=0.98/0.99 new digest
- [ ] Full 5×50 only after gate PASS
- [ ] LOFO → power → lockbox on passing digest

---

## 7. Current digests

| Study | Digest | Outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` |
| mfg floor15+loo-tail+meanmarg | `1c5c3b7e…` | **gate FAIL** (archived) |
| mfg floor15+loo-tail | `681947bc…` | **gate FAIL** (archived) |
| multi-CQA benchmark | `b29bb57e…` | **PASS** |
| **next (B1)** | TBD | `floor20-loo-tail-meanmarg-2026-08-28` |

---

## 8. Amendment rule

Amend when a registered gate completes, or a new preregistered study overturns a §4 ban.
Do not amend from archived shortfalls or retracted SNR claims.

---

## 9. Renewed plan — SPADE above all comparators

**Definition of “above all others”** (locked hierarchy,
`2026-08-26-spade-manufacturing-certificate-recovery-design.md` §1):

| Rank | Endpoint | Beat whom | Bar |
|---|---|---|---|
| **Primary** | Qualified operating region | qLogNEI48, Sobol48 | emp containment ≥ 0.9 (dev gate); CP LB > 0.90 (lockbox) |
| **Co-primary** | Culture rounds | qLogNEI48 | 2–5 rounds vs 10 at 48 wells |
| **Secondary** | Setpoint (Rule-P) | qLogNEI48 | non-inferior within SESOI +0.02 |
| **Secondary** | Map error | Sobol48 | non-inferior within SESOI |
| **Differentiation** | Multi-CQA joint safety | scalar-primary alone | 0 unsafe issued on non-empty joint cert |

**Claim language:** Manufacturing-superior only after scalar `SELECTED` + `POWERED` +
lockbox PASS. Multi-CQA supports EC differentiation **in parallel**, not as rescue.

### 9.1 Execution timeline

```text
NOW     Pull/merge gate-fix ✓
        │
Week 1  Phase A: instrumentation + tests + commit
        │
Week 1  Phase B1: freeze digest floor20, archive meanmarg shards,
        │           durable gate hill+levy 0–15 (~6–8h)
        ├─ PASS (≥1 survivor) ──► full 5×50 all families
        │                         LOFO SELECTED?
        │                         power POWERED?
        │                         lockbox PASS?
        │                         └──► claim manufacturing primary
        │
        └─ FAIL ──► Phase B2 (α=0.98) gate, then B3 abstention replay
                    │
                    └─ still FAIL ──► publish multi-CQA + scoped scalar limits;
                                      cert-targeted research (§3.8); no false win claim
```

### 9.2 Why B1 should clear the last mile

Gate fails by **~1 empirical leak per family** on complementary best arms while
model-internal containment stays ~97%. That is the KT-5 regime: one grid step more
inflation (1.5 → 2.0) converts marginal false positives to abstentions or smaller
honest sets — pushing levy 7/8 → ≥9/10 and hill 7/8 → ≥8/9 without a new estimator.

Meanmarg already fixed structural mean-collapse (`meanmarg.py`, iPSC 350× under-width).

### 9.3 Comparator positioning (post-PASS)

On lockbox, report head-to-head vs **qLogNEI48** and **Sobol48** on:

1. Certificate answer rate + empirical containment (primary)
2. Plate rounds to qualification (co-primary)
3. Rule-P regret (secondary)
4. Map IoU / symmetric difference (secondary)

Multi-CQA manuscript: joint overlay vs scalar-primary on `aligned` /
`moderate_conflict` / `strong_conflict` — already shows joint safety win.

### 9.4 Ops (outside git)

- `~/spade-ops/`: meta + persist + health LaunchAgents
- Backups: `~/spade-ops/persist-backups/` + `/tmp/spade-resume-backups/`
- REGISTERED requires git-clean; archive historical shards outside tracked tree

### 9.5 Stop rules

- After B1+B2+B3 all fail: **stop scalar tuning**; record KT-6-style ceiling
- Never lower emp threshold below 0.9
- Never enable banned §4 items to force a pass
- Never claim manufacturing superiority without lockbox

---

## 10. Research findings (2026-08-28) — what actually moves the needle

### 10.1 The gate is **one failure away** on the best arm

`spade-o32-validity_gated` (meanmarg gate, keys 0–15):

| Family | ans | emp | Margin to pass |
|---|---|---|---|
| hill | 0.533 | **0.875** (7/8) | **1 leak** |
| levy | 0.667 | **0.900** (9/10) | ✓ |

If the single hill false positive **abstains** instead of issuing: hill emp → **1.000**,
ans → 0.467 (still ≥ 0.5). **Both families pass** on this arm.

`spade-o32-staged` is the mirror image (hill 1.0, levy 7/8). No arm fails by much —
gap **0.025** on both near-misses.

**Implication:** Do not redesign the certificate estimator yet. **Slightly more conservative
inflation** (floor 1.5 → 2.0) should convert marginal leaks to abstentions, which
*improves emp among answered* without needing new campaigns.

### 10.2 What does NOT work (measured on archived shards)

| Idea | Verdict | Evidence |
|---|---|---|
| `map_iou` abstention | **Reject** | OK vs FAIL levy: 0.0786 vs 0.0770 (no separation). Hill's only fail has **highest** map_iou (0.31). Pooled levy emp **drops** with iou filter. |
| Higher `selection_containment` threshold | **Reject** | FAIL runs have **higher** sel containment (~0.985) than OK (~0.975). |
| `k_eff`, `kappa_tail`, SNR, selection-blind | **Banned** | Registered FAIL |
| Plate-2 cert targeting alone | **Insufficient** | +0.024 containment post-hoc; KF-3 map null |

### 10.3 Why floor 2.0 is the right first lever (not α)

- KT-5 (`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §7.1): `c=2.0` → truth **1.000**, LB **0.959** on
  P8 rescoring (ackley/hartmann6). `c=1.5` left truth at 0.970.
- Development gate runs at **50–67% answer rate**, not P8's 2.2% at c=2.0 — headroom exists.
- Failures sit at **V ≈ 1/2048** (volume floor). Raising α shrinks already-minimal regions;
  inflation widens draws → smaller honest Vorob'ev sets or abstention.
- `selfcalib.py`: LOO inflation is a **lower bound** on latent correction (predictive vs
  latent gap E3). Floor + meanmarg address **two independent** structural gaps.

### 10.4 Opening and policy — register smarter, not just score harder

- **Opening 32** dominates: mean emp hill 0.958 / levy 0.782 vs o40/o44 ~0.87/0.81 / 0.88/0.73.
- **Policy:** `validity_gated` is the only cross-family near-winner; `staged` wins hill,
  loses levy by 1/8.

**Optional B1b digest amendment:** Register only **3 o32 arms** (drop o40/o44) for LOFO —
reduces multiplicity, keeps the arm closest to passing. Requires frozen spec; not required
if floor 2.0 clears validity_gated on the existing 9-arm set.

### 10.5 Comparator positioning (already winning on levy)

Meanmarg gate, keys 0–15:

| Arm | hill emp | levy emp |
|---|---|---|
| **SPADE o32-validity_gated** | 0.875 | **0.90** |
| qLogNEI48 | 1.00 | **0.50** |
| Sobol48 | 1.00 | **0.40** |

SPADE already beats comparators on **levy certificate honesty** — the gap is internal
consistency (one arm must pass **both** families), not raw superiority.

### 10.6 Second-wave options if B1 fails

| Priority | Lever | Rationale | Risk |
|---|---|---|---|
| B2 | `alpha` → 0.98/0.99 | KT headroom above 0.95 unmeasured | ans collapse (o40-staged levy: emp 1.0, ans 0.33) |
| B3 | `bagged_certificate` | Intersect bootstrap refits; addresses lengthscale/noise uncertainty LOO cannot see (`bagged.py`) | Needs truth calibration; not yet run on dev gate |
| B4 | Cert-straddle **acquisition** policy | Bench containment 0.898 (LB 0.797); targets ρ-contour not p=0.5 (`certstraddle.py`) | Requires **new 12-arm digest**; McNemar p=0.146 vs κ alone |
| Parallel | Multi-CQA joint overlay | **PASS** on aligned/moderate_conflict | Different claim; does not rescue scalar gate |

### 10.7 Revised execution order (research-backed)

```text
A   Instrumentation (inflation factor + abstention reason in scores)
B1  latent_inflation_floor: 2.0  ← highest-confidence fix
    Gate hill+levy 0–15; expect o32-validity_gated or o32-staged to survive
B1b (optional) Re-register 3 o32-only arms if 9-arm gate noisy
B2  alpha 0.98 only if B1 converts leaks but ans/emp still short
B3  Bagged cert spike with truth containment calibration (research)
B4  Cert-straddle acquisition in new 12-arm study (research)
→   PASS → 5×50 → LOFO → power → lockbox
```

**Do not pursue** map-based abstention or detector filters — the data rejects them.
