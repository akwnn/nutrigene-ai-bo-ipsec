# SPADE Manufacturing Certificate Recovery

**Status:** approved redesign before new development outcomes  
**Date:** 2026-08-26  
**Parent protocol:** `2026-08-25-spade-joint-protocol-design.md`  
**Public method name:** SPADE  
**Scope:** computational / synthetic only — no wet-lab, GMP, or biological-efficacy claim

## 1. Manufacturing claim hierarchy

SPADE is judged as the better method from a **cell-manufacturing / CMC / tech-transfer**
perspective. Claim priority is frozen as:

1. **Primary — qualified operating region.** SPADE returns a non-empty design-space
   certificate with empirical truth containment credible for a tech-transfer window
   (development gate: empirical containment ≥ 0.9 on every training family; lockbox:
   Clopper–Pearson lower bound > 0.90 among non-empty certificates in every lockbox
   family).
2. **Co-primary — round / passage economy.** At 48 wells, SPADE uses 2–5 plate rounds
   versus 10 for qLogNEI48. Calendar cost of culture passages is part of the method
   comparison and is never collapsed into “same budget.”
3. **Secondary — setpoint parity.** If manufacturing later freezes one recipe, Rule-P
   regret remains non-inferior to qLogNEI48 within the registered SESOI (+0.02 UCB).
4. **Secondary — map competitiveness.** Probability-map error remains non-inferior to
   Sobol48 within the same SESOI.
5. **Tertiary / historical — Plate-2 targeting.** The old 40+8 boundary-targeting
   ablation (KF-3 FAIL; random slightly better) is **not** the manufacturing selling
   point. It remains frozen historical evidence of a discarded mechanism.

### Referee answer (locked)

> “What is the demonstrated methodological advantage if random Plate 2 performed
> slightly better?”

**Answer:** The advantage is not Plate-2 targeting craft. It is that SPADE is the
method built to return a **qualified operating region with stated assurance and fewer
culture rounds**, while remaining competitive on a single frozen setpoint. Random versus
targeted eight-well Plate 2 is an internal ablation of a superseded protocol and does
not define the manufacturing value of the recovered SPADE.

This answer may be published only after a **new** prospective study with valid
certificates. It is not available from the 2026-08-26 `NO_SELECTION` joint-development
run.

## 2. Diagnosis of the failed joint development

Frozen artifacts (do not reopen for confirmatory reinterpretation):

- `results/spade-selected-protocol.json` — `status: NO_SELECTION`
- `results/spade-development-analysis.json`
- `results/spade-development-*-000-050.jsonl.gz*` (historical joint v1)

**Primary failure mode.** `conservative_set_split` selected the **largest** Vorob'ev
set whose **model-internal** containment ≥ α=0.95. Under a misspecified homoskedastic
learned-noise GP relative to the sealed relative+additive estimand, that check almost
always passed (answer rate ≈ 0.94–1.0) while the issued set was **not** inside the true
reliable region. Model cross-fit on empirical failures stayed ≈ 0.99 — “conservative
given the wrong model,” not manufacturing-valid.

**Shard pattern.** Single-cell certificates in the frozen rows were empirically
contained; larger certificates failed. More adaptive rounds (opening 32, staged) issued
smaller sets and had the best containment, still below 0.9 on Hill/Levy/Rosenbrock.

## 3. Redesign

### 3.1 Certificate volume rule (mandatory)

Replace largest-CE selection with **smallest non-empty** Vorob'ev quantile whose
selection-half model containment is at least `alpha`. Prefer a smaller honest region
over a larger false window.

- Registered default: `certificate_volume_rule: smallest`
- Historical largest rule remains testable via an explicit argument but is **not**
  used for REGISTERED scoring in this recovery protocol.

### 3.2 Predictive observation noise (mandatory)

Map probabilities and certificate set-draws use the **sealed assay noise law**
(`sigma_rel`, `sigma_add`) on latent posterior samples/means, not the GP's learned
homoskedastic likelihood noise. The assay specification is already provided to every
arm; aligning the predictive event with oracle truth is required for manufacturing-
credible containment. Learned homoskedastic noise remains available only as an
explicit non-registered option.

- Registered default: `predictive_observation_noise: assay_relative_additive`

### 3.3 Unchanged

- 48-evaluation budget, γ=0.95, α=0.95, q_τ=0.75
- Development openings {32,40,44} and policies {staged, fixed_hybrid, validity_gated}
- Map / regret / willingness / validity lockbox conjunction
- Lockbox generators remain `FROZEN_UNOPENED`
- Prior `NO_SELECTION` study must not be power-planned or lockbox-opened

### 3.4 Provenance

- New study id / protocol payload digest after the volume-rule and assay-noise changes
- Historical joint-v1 development artifacts archived under
  `results/historical-joint-v1-noselection/`
- New development writes fresh `results/spade-development-*` shards

### 3.5 LOO inflation + volume cap (registered recovery history)

Assay+smallest alone raised hill best-candidate empirical containment to **0.878**
(still < 0.9) and levy to ~**0.67**. LOO **RMS** inflation + `Vmax=0.001`
(`6e6dec2a…`) cleared hill for `spade-o32-staged` (emp 1.0, ans 0.54) but levy
stalled at emp ~**0.72**. LOO-**tail** + Vmax (`6f38077e…`) cleared hill again but
levy best emp **0.875** (7/8) — gate **FAIL**.

Current registered recovery therefore uses:

1. **`latent_draw_inflation: loo_calibration_tail`** with
   **`latent_inflation_floor: 1.5`** — `c_eff = max(1.5, LOO-tail factor)` (KT-5-style
   fixed floor; campaign-local, not a family detector).
2. **`certificate_max_volume: 0.001`** — abstain if CE exceeds this box fraction.

Study id: `spade-joint-48-mfg-cert-floor15-loo-tail-2026-08-27`  
Prior LOO-tail gate FAIL: `results/historical-mfg-cert-loo-tail-gate-fail/`  
Assay-only shortfall: `results/historical-mfg-cert-assay-shortfall/`

Must still clear LOFO ≥0.9 before any manufacturing claim.


## 4. Success

SPADE may be claimed as the better manufacturing method only when the new development
returns `SELECTED`, power returns `POWERED`, and lockbox release PASSes the four-endpoint
conjunction in every family. Until then, manufacturing-facing prose must state that the
recovered certificate rule is implemented but confirmatory outcomes are pending or
failed.

## 5. Cross-workstream consolidation (2026-08-26)

`origin/main` had no competing commits at freeze time; local recovery commits live on
this worktree. External certificate R&D on `origin/kr-effective-resolution`:

| item | status | action here |
|---|---|---|
| Volume law / E3 underdispersion | Established | Motivates smallest CE + Vmax |
| Family-local volume calibration ≥90% | Works | Not deployed as a library rule |
| `k_eff` (KR) / `kappa_tail` transfer (KS) | FAILED / DROP | Not re-adopted |
| KU / KT / KV | Open / frozen | Follow-on studies only after this digest closes |

**Full implement / do-not ledger (2026-08-27):**
`docs/superpowers/specs/2026-08-27-spade-certificate-improvement-decisions.md`

Durable runner: `scripts/spade_development_watchdog.sh` (resume, backups, LOFO on complete).

