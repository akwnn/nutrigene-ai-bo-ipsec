# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Scalar recovery B2 — `alpha: 0.98` gate **running**

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Manufacturing claim hierarchy unchanged; Plate-2 tertiary only.
- Recovery stack: `smallest` + assay + `loo_calibration_tail` + meanmarg + floor **1.5** + `Vmax=0.001`.
- Floor20 gate (`b846fe2d…`) **FAIL** — archived; floor increase falsified.
- Meanmarg gate (`1c5c3b7e…`) **FAIL** — archived.
- Joseph `boec.sur` + `certificate_targeted` policy integrated (research-ready, not in 9-arm set).
- Joseph hypermix/multiround + probe scripts ported (`2026-08-28` manifest).
- Safeguard harness: `scripts/run_spade_safeguard_tests.sh`; watchdog calls it pre-spawn.
- Phase A instrumentation in scores.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| mfg floor-1.5+meanmarg | `1c5c3b7e…` | **gate FAIL** |
| mfg floor20+meanmarg | `b846fe2d…` | **gate FAIL** |
| **B2 alpha0.98+meanmarg** | `7ba21e73…` | **gate running** |

## Next action

1. Hill+levy 0–15 gate on digest `7ba21e73…`.
2. If PASS → full 5×50 → LOFO → power → lockbox.
3. If FAIL → B3 abstention replay or cert-targeted 12-arm digest spike.
