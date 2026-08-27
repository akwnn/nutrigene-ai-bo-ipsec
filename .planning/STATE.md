# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Manufacturing certificate recovery — **floor-1.5 + LOO-tail + meanmarg** gate

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Manufacturing claim hierarchy unchanged; Plate-2 tertiary only.
- Current registered recovery: `smallest` + assay + `loo_calibration_tail` +
  **`latent_inflation_floor: 1.5`** + **`mean_marginalisation: true`** + `Vmax=0.001`
  (study `spade-joint-48-mfg-cert-floor15-loo-tail-meanmarg-2026-08-27`, digest `1c5c3b7e…`).
- Floor-1.5+LOO-tail gate (`681947bc…`) **FAIL** (0 survivors) — archived
  `results/historical-mfg-cert-floor15-loo-tail-gate-fail/`.
- Joseph `kr-effective-resolution` merged into `main` (modules + meanmarg wiring retained).

## Protocol digests

| study | digest | outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` |
| mfg assay+smallest | `f6eca072…` | shortfall; archived |
| mfg LOO-RMS+Vmax | `6e6dec2a…` | levy ~0.72; archived |
| mfg LOO-tail+Vmax | `6f38077e…` | **gate FAIL** (archived) |
| mfg floor-1.5+LOO-tail | `681947bc…` | **gate FAIL** (archived) |
| **mfg floor-1.5+LOO-tail+meanmarg (current)** | `1c5c3b7e…` | gate starting |

## Next action

1. Durable hill+levy 0–15 gate on `1c5c3b7e…` (ans≥0.5, emp≥0.9 both).
2. Only if PASS → full 5×50 → LOFO → power → lockbox.
3. Do not resume archived floor15 shards.
4. Ledger: `docs/superpowers/specs/2026-08-27-spade-certificate-improvement-decisions.md`
