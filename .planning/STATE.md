# State

**Milestone:** SPADE joint protocol  
**Status:** active — scalar recovery **B2 FAIL**; pivot to B3 research  
**Current phase:** B3 bagged-certificate spike (offline) or B4 cert-targeted 12-arm digest

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Manufacturing claim hierarchy unchanged; Plate-2 tertiary only.
- Recovery stack: `smallest` + assay + `loo_calibration_tail` + meanmarg + floor **1.5** + `Vmax=0.001`.
- Floor20 gate (`b846fe2d…`) **FAIL** — archived; floor increase falsified.
- Meanmarg gate (`1c5c3b7e…`) **FAIL** — archived.
- **B2 alpha0.98** (`7ba21e73…`) **FAIL** — 0 survivors; archived `historical-mfg-cert-floor15-loo-tail-meanmarg-alpha098-gate-fail/`.
- Joseph `boec.sur` + `certificate_targeted` policy integrated (research-ready, not in 9-arm set).
- Joseph hypermix/multiround + probe scripts ported (`2026-08-28` manifest).
- Safeguard harness: `scripts/run_spade_safeguard_tests.sh`; watchdog calls it pre-spawn.
- Phase A instrumentation in scores.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| mfg floor-1.5+meanmarg | `1c5c3b7e…` | **gate FAIL** |
| mfg floor20+meanmarg | `b846fe2d…` | **gate FAIL** |
| **B2 alpha0.98+meanmarg** | `7ba21e73…` | **gate FAIL** |

## B2 gate diagnosis (keys 0–15)

Best complementary arms still do not co-pass:

| Arm | hill ans / emp | levy ans / emp |
|---|---|---|
| o32-staged | 0.47 / **1.00** | 0.07 / 1.00 |
| o32-validity_gated | 0.33 / **1.00** | 0.47 / 0.86 |
| o40-staged | 0.60 / **1.00** | 0.07 / 1.00 |

α=0.98 **collapsed answer rates** on levy (o32-staged ans 0.07) without fixing cross-family pairing.

Analysis: `results/b2-alpha098-gate-analysis.json`

## Next action

1. **B3:** offline `bagged_certificate` replay on archived B2 shards (research spike).
2. **B4 (if B3 insufficient):** freeze 12-arm digest with `certificate_targeted` policy; hill+levy gate.
3. **Do not** start full 5×50 on failed digests.
4. Multi-CQA benchmark remains the parallel winning narrative (PASS).
