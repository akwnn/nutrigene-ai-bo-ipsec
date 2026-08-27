# SPADE Certificate Improvement Decisions

**Status:** binding implement / do-not ledger for certificate work  
**Date:** 2026-08-27  
**Audience:** next session implementing SPADE certificate changes  
**Sources:**
- Manufacturing recovery: `2026-08-26-spade-manufacturing-certificate-recovery-design.md`
- External R&D branch: `origin/kr-effective-resolution` (Joseph; KR→KS→KT→KU→KV→KW)
- Current registered recovery: LOO-tail + Vmax (`study_id`
  `spade-joint-48-mfg-cert-loo-tail-vmax-2026-08-27`, digest `6f38077e…`)

**Scope:** computational / synthetic certificate honesty only. Does not reopen
Plate-2 targeting as the manufacturing selling point. Does not authorize paper
claims beyond what confirmatory gates pass.

---

## 1. Goal

Make SPADE’s certificate **manufacturing-credible**: when it returns a region,
empirical truth containment should clear the registered bar; when evidence is
weak, it should **abstain** with a stated reason rather than issue a false window.

This doc freezes **what to implement next**, **what not to implement**, and
**what stays research-only** so Joseph’s branch is not merged mid-gate and dead
ends are not rebuilt.

---

## 2. Product principle (locked)

SPADE’s certificate upgrade path is:

> **Inflate latent uncertainty + prefer small regions + cap volume + abstain honestly.**

It is **not**:

> Smarter failure detectors, SNR run-time switches, family-library caps, or
> resurrecting Plate-2 boundary targeting as the primary fix.

Referee line (unchanged from manufacturing recovery): the manufacturing advantage
is a **qualified operating region with stated assurance and fewer rounds**, not
Plate-2 targeting craft.

---

## 3. DO IMPLEMENT — ordered queue

Do these in order. Do **not** skip ahead while a registered gate is running.

### 3.1 Now — finish current registered recovery (no new knobs)

**Already wired** in `configs/experiment/spade-joint.yaml` / `SpadeJointSettings`:

| Knob | Value | Role |
|---|---|---|
| `certificate_volume_rule` | `smallest` | Prefer small honest CE over large false CE |
| `predictive_observation_noise` | `assay_relative_additive` | Score under sealed assay noise |
| `latent_draw_inflation` | `loo_calibration_tail` | Campaign-local LOO widen of latent draws |
| `certificate_max_volume` | `0.001` | Abstain if CE exceeds this box fraction |

**Actions:**

1. Complete hill+levy keys 0–15 gate (`ans ≥ 0.5`, `emp ≥ 0.9` on both).
2. Only then full REGISTERED 5×50 → LOFO → power → lockbox.
3. Do not change inflation mode, Vmax, volume rule, or assay noise mid-digest.
4. Do not merge `origin/kr-effective-resolution` into this digest.

**Why LOO-tail (not KS `kappa_tail` transfer):** KS dropped `kappa_tail` as a
*cross-family volume-cap conditioner / failure detector*. Recovery uses the same
self-calib primitives **only** as a **campaign-local multiplier** on latent
draws. That distinction is mandatory; do not reintroduce transfer conditioning.

**Known limit (from Joseph / E3):** LOO residuals are **predictive**; the
certificate is a **latent** claim. LOO inflation is therefore a **lower bound**
on the correction needed. If LOO-tail+Vmax still shortfalls, that gap is the
expected next failure mode — not a reason to resurrect detectors.

### 3.2 Next registered candidate — only if 3.1 shortfalls

**Candidate name (suggested):** `fixed_floor_loo_tail`  
**Rule (to register before any run):**

```text
c_eff = max(c_floor, loo_calibration_tail_factor)
latent_draw_sd *= c_eff
```

with proposed default `c_floor = 1.5` from KT-5 (ackley↔hartmann6 transfer at
α=0.95), still combined with `smallest` + assay noise + `Vmax=0.001`.

**Requirements before coding a run:**

- New study id + protocol digest (do not overwrite LOO-tail+Vmax).
- Explicit registration that `c_floor` is a **fixed inflation**, not a detector.
- Same gate order: hill+levy 0–15 → full 5×50 → LOFO.
- Record answer rate; a pass that empties almost every region is not a product win
  (see KT-7c spirit: answer-rate floor).

**Do not** treat `c=1.5` as proven for levy/rosenbrock γ=0.95; Joseph named a
hard information limit on those families at 48 wells.

### 3.3 Productize abstention reasons (after a SELECTED recovery, or in parallel docs/API)

When the certificate is empty, return a machine-readable reason, e.g.:

- `volume_cap` — selected CE > `certificate_max_volume`
- `no_feasible_ce` — no Vorob'ev level cleared model α under smallest rule
- `information_limit` — reserved for registered cases where inflation cannot create
  a non-empty honest set (do not invent this label without a rule)

Empty is a **valid SPADE outcome**, not a silent failure.

### 3.4 Later — acquisition experiments (optional, lowest priority)

Only after certificate honesty is SELECTED (or clearly failed for honesty reasons
independent of sampling):

| Idea | Source | Condition |
|---|---|---|
| `certificate_straddle` acquisition | Joseph `certstraddle.py` | Revisit only with locked inflation; map-targeting already failed SESOI (KF-3) |
| Bagged / intersected certificates | Joseph `bagged.py` | Research; no registered pass as product default |

These are **not** on the manufacturing claim critical path.

---

## 4. DO NOT IMPLEMENT

Hard bans unless a **new** preregistered study overturns the verdict and this doc
is amended.

| Item | Source verdict | Why banned |
|---|---|---|
| `k_eff` as transfer / filter | KR-1/KR-2 **FAIL**, dropped | Does not transfer; extreme dispersion |
| `kappa_tail` as cross-family conditioner or campaign failure detector | KS-1/KS-4 **FAIL**, dropped | Adds nothing reliable over volume; wrong product shape |
| Threshold SNR / `(mean−τ)/σ_pred` run-time detector | Section 9 **RETRACTED** | Expanded cells: Spearman n.s.; must not be built on |
| Family-library volume calibration as deployable default | Works in-lab, not deployable | Lab has one unknown landscape, not a named family |
| Selection-blind covariance as honesty fix | KW-1/KW-2 **FAIL** | Makes targeting gap worse; mismatched posterior |
| Merging `kr-effective-resolution` into active recovery digest | Process | Different digests; invalidates registered gate |
| Reopening Plate-2 targeting as manufacturing primary | KF-3 / recovery hierarchy | Tertiary / historical only |
| Claiming paper manufacturing-superiority from Joseph’s branch alone | Evidence rules | Needs SELECTED + POWERED + lockbox PASS on registered protocol |
| Putting retracted SNR explanation in the manuscript | Retraction | Honesty / review risk |

---

## 5. Paper vs product (so claims stay bounded)

| Material | Use in paper? | Use in SPADE product? |
|---|---|---|
| Current LOO-tail+Vmax gate | Only after SELECTED+powered+lockbox | **Yes — current path** |
| KT-5 fixed `c≈1.5` | Discussion / follow-up methods if registered prospectively | **Next candidate if gate fails** |
| KR/KS detector fails | Discussion (negative evidence) | **No** |
| Retracted SNR story | **No** | **No** |
| Hard limit on some families @ γ=0.95 / 48 wells | Limitations (helps honesty) | Abstain, don’t force a region |
| `publication-readiness` / figures (other branches) | Manuscript assets | N/A |

Joseph’s branch **protects** the paper (narrower, more honest certificate story).
It does **not** unlock a stronger confirmatory certificate claim by itself.

---

## 6. Implementation checklist (copy into the implementing session)

Before writing code for any new certificate knob:

- [ ] Confirm current digest gate status in `.planning/STATE.md`
- [ ] If gate still running / not failed: **stop** — no knob changes
- [ ] If proposing `c_floor` or other change: new study id + digest + tests first
- [ ] Re-read §4 DO NOT IMPLEMENT — confirm the change is not a banned detector
- [ ] Keep `smallest` + assay noise unless a separate registered study drops them
- [ ] Keep Vmax unless a registered study replaces the abstention rule
- [ ] Do not import `selectionblind` / `resolution` filters into scoring defaults
- [ ] Update this doc’s “Current registered” line when a new digest freezes

---

## 7. Current registered (update when digests change)

| Field | Value |
|---|---|
| Study id | `spade-joint-48-mfg-cert-floor15-loo-tail-2026-08-27` |
| Digest | `681947bc…` |
| Inflation | `loo_calibration_tail` with **`latent_inflation_floor: 1.5`** |
| Vmax | `0.001` |
| Volume rule | `smallest` |
| Predictive noise | `assay_relative_additive` |
| Prior LOO-tail+Vmax gate | **FAIL** (archived `historical-mfg-cert-loo-tail-gate-fail/`; near-miss emp 0.875) |
| Next action | Re-gate hill+levy 0–15 under this digest; full 5×50 only if clear |

---

## 8. Amendment rule

Amend this file only when:

1. A registered gate completes (PASS/FAIL) and the next candidate is frozen, or
2. A new preregistered study overturns a §4 ban, with digest + tests cited.

Do not amend based on post-hoc reinterpretation of archived shortfalls
(`historical-joint-v1-noselection`, assay-only, LOO-RMS shortfall, or Joseph’s
retracted SNR section).

---

## 9. Numbered path to clear the ≥90% bar

Ordered work only. Do not skip ahead or add banned §4 items.

**GitHub sync (2026-08-27):** `origin/main` has **no new commits** to pull (this
worktree is ahead). Useful external material inspected (not merged mid-recovery):

| Remote | Useful for ≥90% path? | Takeaway |
|---|---|---|
| `origin/kr-effective-resolution` | **Yes (selective)** | KT-5 floor `c≈1.5` PASS; volume-conditional calib hits ≥90% in-family but not deployable as a library rule; KX finite-set/topk estimand; `meanmarg` fixes posterior collapse on low-SNR real data; KV/KR/KS/KW detectors mostly FAIL → stay banned |
| `origin/codex/spade-gate-fix` | **Yes (later confirmatory)** | Hardens LOFO selection + lockbox publication gates — adopt when entering SELECTED→lockbox, not as a certificate honesty knob |
| `origin/codex/publication-readiness` | Paper only | Manuscript/tables — not on the 90% engineering path |
| `origin/q60-q61-tost` / figure branches | Paper / other estimands | Out of scope for certificate containment bar |

### Critical path (honesty → claim)

1. **Close LOO-tail+Vmax as evidence** — Archive gate shards; record FAIL and near-miss (`o32-staged` levy 7/8 = emp 0.875). Do not reinterpret as a pass.
2. **Register `fixed_floor_loo_tail` (from KT-5 on GitHub)** — New study id + digest: `c_eff = max(1.5, loo_tail)` on latent draws; keep `smallest` + assay noise + `Vmax=0.001`. Tests first; clean git tree. **Do not** merge the whole KR branch — port only this registered rule.
3. **Re-gate hill+levy keys 0–15** — Same bars: ans ≥ 0.5 and emp ≥ 0.9 on **both**. Watch `spade-o32-staged` / `spade-o40-staged`. Stop if ans collapses below 0.5 (KT-7c spirit).
4. **If gate PASS → full REGISTERED 5×50 → LOFO** — Adopt useful bits from `codex/spade-gate-fix` for selection/publication hardening when wiring LOFO, still under a clean registered digest.
5. **If LOFO `SELECTED` → power → lockbox** — Lockbox Clopper–Pearson lower bound **> 0.90** on containment (plus the other three endpoints) in every lockbox family. Use hardened lockbox gates from `spade-gate-fix` here.
6. **Only then claim manufacturing superiority** — Researcher-facing prose; development 90% alone is not enough.

### If step 3 or 4 still miss ≥90% (ordered fallbacks from GitHub evidence)

7. **Productize abstention reasons** — Machine-readable empty codes (`volume_cap`, `no_feasible_ce`, later `information_limit`). Empty is a valid SPADE outcome; Joseph’s hard-limit note @ 48 wells / γ=0.95 on some families is a **feature**, not a bug to paper over.
8. **Port `meanmarg` (ordinary kriging / integrate-out constant mean)** — From KR real iPSC-EC work: MLE constant-mean collapse understates width hundreds-fold on noise-dominated data; inflation cannot fix sd≈0. Required before any low-SNR / real-assay certificate claim; add tests + a registered scoring option or default with new digest.
9. **Evaluate finite-set / top-k certification (KX)** — Certify a handful of formulations with joint P(all exceed τ) ≥ α instead of a continuous region. Weaker claim, much higher answer rate when region CE abstains. **Must** calibrate `c` against **truth** containment (`topk_contain`), never against the model’s own joint probability (selection optimism is worse than region CE). New estimand = new study — does not silently replace the region bar.
10. **Volume-conditional (Mondrian) calibration — development-only diagnostic or separate study** — Joseph’s central positive: family-local volume caps clear ≥90% LB on held-out seeds. **Still banned as a deployable family-library rule** (§4). Allowed only as (a) LOFO analysis of *why* a digest fails, or (b) a newly preregistered protocol that does **not** require naming the landscape at deploy time (if no such design exists, skip — do not smuggle library caps).

### Optional / after honesty SELECTED (not required for 90%)

11. **Certificate-straddle acquisition / bagging** — From KR `certstraddle.py` / `bagged.py`; only after honesty is SELECTED (or failed for reasons independent of sampling). Not on the manufacturing critical path; KF-3 still blocks Plate-2-as-pitch.

### Explicitly do **not** add from GitHub (reconfirmed)

12. **Keep banned:** `k_eff`, `kappa_tail` transfer/detectors, SNR switch, selection-blind as honesty fix, family-library volume caps as product default, merge `kr-effective-resolution` wholesale, Plate-2 as manufacturing primary, pooling SPADE with its own controls in published bounds (KR erratum).

**Done means:** SELECTED + POWERED + lockbox PASS on a registered recovery — that is what “above the conventional 90% bar” requires for a manufacturing claim.
