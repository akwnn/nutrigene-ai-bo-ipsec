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

| Digest | Study suffix | Outcome | Archive | Analysis |
|---|---|---|---|---|
| `681947bc…` | floor15-loo-tail | **FAIL** 0 survivors | `historical-mfg-cert-floor15-loo-tail-gate-fail/` | — |
| `1c5c3b7e…` | floor15-loo-tail-meanmarg | **FAIL** 0 survivors | `historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail/` | `.planning/artifacts/gate-summaries/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail.json` |
| `b846fe2d…` | floor20-loo-tail-meanmarg (B1) | **FAIL** 0 survivors | `historical-mfg-cert-floor20-loo-tail-meanmarg-gate-fail/` | `.planning/artifacts/gate-summaries/historical-mfg-cert-floor20-loo-tail-meanmarg-gate-fail.json` |
| `7ba21e73…` | alpha098-loo-tail-meanmarg (B2) | **FAIL** 0 survivors | `historical-mfg-cert-floor15-loo-tail-meanmarg-alpha098-gate-fail/` | `.planning/artifacts/gate-summaries/historical-mfg-cert-floor15-loo-tail-meanmarg-alpha098-gate-fail.json` |

**Diagnosis (evidence, 2026-08-29):** see `.planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md`.

1. **Model-internal containment is blind to truth.** Failed levy runs still show
   `certificate_selection_containment` ≈ 0.97–0.99 while `certificate_empirical_containment`
   is False (E3 latent coverage 0.76–0.82 vs nominal 0.95).
2. **Levy is the binding family.** Complementary pairing — no single arm clears both hill and levy.
3. **Meanmarg helped but did not break the plateau.** Levy emp 0.75 → 0.875 (o32-staged).
4. **Floor 2.0 falsified.** Hurts levy; do not increase floor further without new prereg.
5. **α=0.98 falsified.** Collapsed levy answer rates (o32-staged ans 0.07); reverted to 0.95.

Do **not** start full 5×50 on failed digests.

### 3.2 Merged protocol base (current code on `main`)

| Knob | Value | Owner |
|---|---|---|
| `certificate_volume_rule` | `smallest` | Alana |
| `predictive_observation_noise` | `assay_relative_additive` | Alana |
| `latent_draw_inflation` | `loo_calibration_tail` | Alana (+ Joseph selfcalib) |
| `latent_inflation_floor` | `1.5` | Alana (floor 2.0 **falsified** B1) |
| `certificate_max_volume` | `0.001` | Alana |
| `certificate_bootstrap_bags` | `5` | Joseph bagged.py (B3 registered) |
| `mean_marginalisation` | `true` | Joseph |

**Joseph modules in tree:**

| Module | Role | Product default? |
|---|---|---|
| `selfcalib.py` | LOO residuals / inflation / tail | **Yes** |
| `meanmarg.py` | Ordinary-kriging covariance | **Yes** |
| `topk.py` | Finite-set certification | Research only |
| `bagged.py` | Intersect bootstrap certs | **Yes** (B3, n=5) |
| `certstraddle.py` | Cert-frontier acquisition | **Yes** via `certificate_targeted` o32 |
| `selectionblind.py` | Selection-blind covariance | **No** (KW fail) |
| `resolution.py` | `k_eff` | **No** (KR fail) |

### 3.3 Confirmatory infrastructure — **DONE** (`origin/codex/spade-gate-fix` merged 2026-08-28)

Merged into `main`: hardened `select_spade_protocol.py`, `run_spade_lockbox.py`,
`analyse_spade_lockbox.py` + tests. Required before any LOFO/lockbox claim.

### 3.4 Phase A — Instrumentation — **DONE**

1. `latent_inflation_factor` + `certificate_abstention_reason` in scores.
2. `scripts/analyze_gate_failures.py` for archived shard replay.
3. Tests in `tests/test_spade_study.py`.

### 3.5 Phase B1 — `latent_inflation_floor: 2.0` — **FAIL** (`b846fe2d…`)

Raising floor hurt levy; archived. Do not retry without new prereg.

### 3.6 Phase B2 — `reliability.alpha: 0.98` — **FAIL** (`7ba21e73…`)

Collapsed levy answer rates without co-pass; archived. **α reverted to 0.95** in B3.

### 3.7 Phase B3 — Bagged certificate + cert_targeted — **RUNNING** (`2ef1875c…`)

| Field | B3 value |
|---|---|
| `certificate_bootstrap_bags` | **5** |
| `certificate_targeted` policy | **o32 only** (10 SPADE + 2 comparator = 12 arms) |
| `reliability.alpha` | **0.95** |
| study_id | `…-bagged5-2026-08-29` |

Offline replay: `scripts/replay_certificate_scoring.py` on archived shards.

### 3.8 Research track — certificate-targeted bench (historical)

Bench (`bench_certificate.py`): directionally positive; McNemar p=0.146. Now **registered**
as o32 arm under B3 digest — not research-only.

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
- [x] Phase A instrumentation
- [x] Phase B1 gate floor20 — **FAIL**, archived
- [x] Phase B2 gate alpha0.98 — **FAIL**, archived
- [x] Joseph full integration + B3 protocol (`2ef1875c…`)
- [ ] Phase B3 gate hill+levy 0–15 — **RUNNING**
- [ ] Full 5×50 only after gate PASS
- [ ] LOFO → power → lockbox on passing digest

---

## 7. Current digests

| Study | Digest | Outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` |
| mfg floor15+loo-tail+meanmarg | `1c5c3b7e…` | **gate FAIL** (archived) |
| mfg floor20+meanmarg (B1) | `b846fe2d…` | **gate FAIL** (archived) |
| mfg alpha098+meanmarg (B2) | `7ba21e73…` | **gate FAIL** (archived) |
| multi-CQA benchmark | `b29bb57e…` | **PASS** |
| **B3 bagged5+cert_targeted** | `2ef1875c…` | **gate RUNNING** |

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

### 10.6 Second-wave options (status 2026-08-29)

| Priority | Lever | Status | Outcome |
|---|---|---|---|
| B1 | `latent_inflation_floor: 2.0` | **DONE** | **FAIL** — hurt levy (`b846fe2d…`) |
| B2 | `alpha` → 0.98 | **DONE** | **FAIL** — levy ans collapsed (`7ba21e73…`) |
| **B3** | bagged5 + cert_targeted o32 | **RUNNING** | Digest `2ef1875c…` |
| B4 | Further bag-count / acquisition sweeps | **Next if B3 fails** | Offline via `replay_certificate_scoring.py` |
| Parallel | Multi-CQA joint overlay | **PASS** | `b29bb57e…` — separate EC claim |

### 10.7 Revised execution order (as of B3)

```text
A   Instrumentation — DONE
B1  floor 2.0 — FAIL (archived)
B2  alpha 0.98 — FAIL (archived)
B3  bagged5 + cert_targeted + α=0.95 — RUNNING (hill+levy 0–15)
    Diagnosis ledger: .planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md
→   PASS → 5×50 → LOFO → power → lockbox
→   FAIL → archive, analyze_gate_failures, replay sweeps, B4 design
```
```

**Do not pursue** map-based abstention or detector filters — the data rejects them.
