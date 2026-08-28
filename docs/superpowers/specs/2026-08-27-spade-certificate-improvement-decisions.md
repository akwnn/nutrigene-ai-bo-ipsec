# SPADE Certificate Improvement Decisions

**Status:** binding implement / do-not ledger for certificate work  
**Date:** 2026-08-27 (updated same day after Joseph push + merge)  
**Audience:** next session implementing SPADE certificate changes  
**Sources:**
- Manufacturing recovery: `2026-08-26-spade-manufacturing-certificate-recovery-design.md`
- External R&D branch: `origin/kr-effective-resolution` (Joseph; KR→…→KX + real iPSC)
- Merge branch: `spade/merge-joseph-alana` (worktree `.worktrees/spade-merge-joseph`)
- Live gate (do not disturb): worktree `.worktrees/spade-campaign` on digest
  `681947bc…` / study `…-floor15-loo-tail-2026-08-27` (no meanmarg yet)

**Scope:** computational / synthetic certificate honesty only. Does not reopen
Plate-2 targeting as the manufacturing selling point. Does not authorize paper
claims beyond what confirmatory gates pass.

---

## 1. Goal

Make SPADE’s certificate **manufacturing-credible**: when it returns a region,
empirical truth containment should clear the registered bar; when evidence is
weak, it should **abstain** with a stated reason rather than issue a false window.

Preserve **both** workstreams:

- **Alana:** joint manufacturing recovery (smallest CE, assay noise, LOO-tail,
  `c_floor=1.5`, Vmax, digests, development runners).
- **Joseph:** certificate R&D modules, registered specs/runners, mean-marginalisation
  safety fix, finite-set / top-k research, real-data errata.

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

### 3.1 Meanmarg gate (completed 2026-08-28) — FAIL

Hill+levy keys 0–15 on digest `1c5c3b7e…` finished with **0 survivors**.
Archived: `results/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail/`.

Best near-miss: `spade-o32-validity_gated` levy emp **0.90** but hill emp **0.875**;
`spade-o32-staged` hill emp **1.0** but levy emp **0.875**. Meanmarg improved hill
containment vs floor15-only but did not close the cross-family pairing.

Do **not** start full 5×50 on this digest.

### 3.2 Merged protocol (spade/merge-joseph-alana) — both sides kept

**Already merged git-clean** from `origin/kr-effective-resolution` into Alana `main`
tip (`e815042`). Alana `spade_study` / digests / recovery settings preserved;
Joseph modules landed as adds.

**Combined registered scoring (merge branch):**

| Knob | Value | Owner |
|---|---|---|
| `certificate_volume_rule` | `smallest` | Alana |
| `predictive_observation_noise` | `assay_relative_additive` | Alana |
| `latent_draw_inflation` | `loo_calibration_tail` | Alana (+ Joseph selfcalib) |
| `latent_inflation_floor` | `1.5` | Alana (from Joseph KT-5) |
| `certificate_max_volume` | `0.001` | Alana |
| `mean_marginalisation` | `true` | Joseph (wired into `reliable_set_draws`) |

Study id:
`spade-joint-48-mfg-cert-floor15-loo-tail-meanmarg-2026-08-27`  
Protocol digest: `1c5c3b7e…`

**Joseph modules kept in tree (available; not all are product defaults):**

| Module | Role | Product default? |
|---|---|---|
| `selfcalib.py` | LOO residuals / inflation / tail | **Yes** (via LOO-tail) |
| `meanmarg.py` | Ordinary-kriging covariance | **Yes** (SPADE scoring) |
| `topk.py` | Finite-set certification | Research only |
| `bagged.py` | Intersect bootstrap certs | Research only |
| `certstraddle.py` | Cert-frontier acquisition | Research only |
| `selectionblind.py` | Selection-blind covariance | **No** (KW fail) |
| `resolution.py` | `k_eff` | **No** (KR fail) |

### 3.3 After live gate completes — cut over

1. Commit merge-branch wiring if still dirty; push `spade/merge-joseph-alana`.
2. Merge into `main` only when campaign worktree is idle (or via PR).
3. Start a **new** gate on the meanmarg digest (do not append to floor15 shards).
4. Productize abstention reasons (`volume_cap`, `no_feasible_ce`, …).

---

## 4. DO NOT IMPLEMENT

| Item | Source verdict | Why banned |
|---|---|---|
| `k_eff` as transfer / filter | KR **FAIL** | Does not transfer |
| `kappa_tail` as cross-family conditioner | KS **FAIL** | Not a detector |
| Threshold SNR run-time detector | **RETRACTED** | Not significant on expanded cells |
| Family-library volume caps as deployable default | Lab-only | One unknown landscape |
| Selection-blind covariance as honesty fix | KW **FAIL** | Makes gap worse |
| Treating `c=1.5` as α-general | KT-7 **FAIL** at α=0.5 | Claim stays α=0.95 |
| Publishing KT-5 LB as 0.9377 without erratum | Erratum | SPADE-alone LB is 0.9019 |
| Finite-set / top-k as confirmed SPADE win | Exploratory | Needs own calibration |
| Merging into live gate worktree mid-run | Process | Corrupts digest / resume |
| Plate-2 targeting as manufacturing primary | KF-3 / hierarchy | Tertiary only |

---

## 5. Paper vs product

| Material | Paper | SPADE product |
|---|---|---|
| Alana recovery + floor 1.5 | Only after SELECTED+powered+lockbox | Current live gate / merge base |
| Mean-marginalisation | Methods + safety limitation | **Yes — registered in merge** |
| KT-5/KT-7 inflation story | Discussion; cite erratum | Floor 1.5 at α=0.95 only |
| KR/KS detector fails | Negative Discussion | **No** |
| Retracted SNR | **No** | **No** |
| Real iPSC result | Only after human signoff | meanmarg motivation |
| top-k / bagged / straddle | Future work | Not default |

---

## 6. Implementation checklist

- [x] Merge Joseph branch without deleting Alana `spade_study` / recovery
- [x] Wire `mean_marginalisation` into `reliable_set_draws` + scoring settings
- [x] Keep LOO-tail + `c_floor` + Vmax + smallest + assay
- [ ] Finish live gate on campaign worktree (do not disturb)
- [ ] Run focused tests on merge worktree
- [ ] Cut over / new gate on meanmarg digest when idle
- [ ] Do not enable selectionblind / resolution filters in scoring defaults

---

## 7. Current digests

| Tree | Study | Protocol digest | Notes |
|---|---|---|---|
| `.worktrees/spade-campaign` | `…-floor15-loo-tail-meanmarg-2026-08-27` | `1c5c3b7e…` | **gate FAIL** (archived) |
| archived | `…-floor15-loo-tail-2026-08-27` | `681947bc…` | **gate FAIL** (0 survivors) |

Meanmarg gate (2026-08-28): 0 survivors. Levy emp plateau ~0.875–0.90; hill OK.
Next scalar attempt requires a **new** preregistered digest.

---

## 8. Amendment rule

Amend when a registered gate completes, or a new preregistered study overturns a §4 ban.
Do not amend from archived shortfalls or retracted SNR claims.
