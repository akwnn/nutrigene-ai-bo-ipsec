# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Manufacturing certificate recovery — **meanmarg gate FAIL**; next protocol TBD

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Manufacturing claim hierarchy unchanged; Plate-2 tertiary only.
- Last tested recovery stack: `smallest` + assay + `loo_calibration_tail` +
  **`latent_inflation_floor: 1.5`** + **`mean_marginalisation: true`** + `Vmax=0.001`
  (study `spade-joint-48-mfg-cert-floor15-loo-tail-meanmarg-2026-08-27`, digest `1c5c3b7e…`).
- Floor-1.5+LOO-tail+meanmarg gate (`1c5c3b7e…`) **FAIL** (0 survivors) — archived
  `results/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail/`.
- Floor-1.5+LOO-tail gate (`681947bc…`) **FAIL** (0 survivors) — archived
  `results/historical-mfg-cert-floor15-loo-tail-gate-fail/`.
- Joseph `kr-effective-resolution` merged into `main` (modules + meanmarg wiring retained).
- Multi-CQA synthetic safety benchmark **PASS** (`results/spade-multi-cqa-benchmark.json`).

## Protocol digests

| study | digest | outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` |
| mfg assay+smallest | `f6eca072…` | shortfall; archived |
| mfg LOO-RMS+Vmax | `6e6dec2a…` | levy ~0.72; archived |
| mfg LOO-tail+Vmax | `6f38077e…` | **gate FAIL** (archived) |
| mfg floor-1.5+LOO-tail | `681947bc…` | **gate FAIL** (archived) |
| mfg floor-1.5+LOO-tail+meanmarg | `1c5c3b7e…` | **gate FAIL** (archived) |

## Gate verdict (meanmarg, 2026-08-28)

0 survivors. Hill clears on several configs (e.g. o32-staged emp 1.0); levy best
o32-validity_gated emp **0.90** but hill emp only **0.875** on that config; o32-staged
levy emp **0.875**. Meanmarg did not fix the cross-family pairing.

## Next action

1. Do **not** start full 5×50 on `1c5c3b7e…`.
2. Preregister next scalar-recovery change (new digest) or pivot manufacturing narrative
   to multi-CQA synthetic evidence until a scalar gate passes.
3. Ledger: `docs/superpowers/specs/2026-08-27-spade-certificate-improvement-decisions.md`
