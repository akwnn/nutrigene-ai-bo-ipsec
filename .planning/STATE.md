# State

**Milestone:** SPADE joint protocol  
**Status:** active — **B3 gate ready** (bagged5 + cert_targeted o32 + α=0.95)  
**Current phase:** Launch hill+levy 0–15 gate on digest `2ef1875c…`

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Recovery stack: `smallest` + assay + `loo_calibration_tail` + meanmarg + floor **1.5** + `Vmax=0.001` + **bagged5**.
- **α reverted to 0.95** (B2 α=0.98 FAIL — collapsed levy answer rates).
- **10 SPADE arms** (o32 adds `certificate_targeted`; o40/o44 unchanged) + 2 comparators = **12 arms/family**.
- Joseph real-data scripts ported (`calibrate_real_assay_loo`, `certify_hall_ogle`, `final_real_data_answer`, `probe_loo_real_assay`, `run_lc_confirmatory`).
- Safeguard harness + watchdog pre-spawn checks active.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| meanmarg floor15 | `1c5c3b7e…` | **gate FAIL** |
| floor20 | `b846fe2d…` | **gate FAIL** |
| B2 alpha0.98 | `7ba21e73…` | **gate FAIL** |
| **B3 bagged5+cert_targeted** | `2ef1875c…` | **gate pending** |

## Diagnosis → fix

| Failure | Root cause | B3 response |
|---|---|---|
| Complementary hill/levy winners | Single GP + inflation still overconfident on lengthscales/noise | **Bootstrap bagged** certificate (intersect 5 refits) |
| α=0.98 hurt levy ans | Too conservative globally | **Revert α=0.95** |
| o32-validity_gated near-miss | Acquisition not targeting cert contour on levy | **certificate_targeted** policy on o32 |

Offline replay: `scripts/replay_certificate_scoring.py` on archived shards.

## Next action

1. Run `./scripts/run_spade_safeguard_tests.sh`
2. Launch B3 hill+levy 0–15 gate (`~/spade-ops/spade_gate_then_full_watchdog.sh`)
3. If PASS → full 5×50 → LOFO → power → lockbox
