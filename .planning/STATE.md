# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Manufacturing certificate recovery — **floor-1.5 + LOO-tail** registered; re-gate next

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Manufacturing claim hierarchy unchanged; Plate-2 tertiary only.
- Current registered recovery: `smallest` + assay + `loo_calibration_tail` +
  **`latent_inflation_floor: 1.5`** + `Vmax=0.001`
  (study `spade-joint-48-mfg-cert-floor15-loo-tail-2026-08-27`, digest `681947bc…`).
- Prior LOO-tail-only gate (`6f38077e…`) **FAIL** — archived.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` |
| mfg assay+smallest | `f6eca072…` | shortfall; archived |
| mfg LOO-RMS+Vmax | `6e6dec2a…` | levy ~0.72; archived |
| mfg LOO-tail+Vmax | `6f38077e…` | **gate FAIL** (archived) |
| **mfg floor-1.5+LOO-tail (current)** | `681947bc…` | re-gate in flight / pending |

## Next action

1. Clean commit of floor-1.5 freeze.
2. Durable hill+levy 0–15 re-gate (ans≥0.5, emp≥0.9 both).
3. Only if PASS → full 5×50 → LOFO → power → lockbox.
4. Ledger: `docs/superpowers/specs/2026-08-27-spade-certificate-improvement-decisions.md`
