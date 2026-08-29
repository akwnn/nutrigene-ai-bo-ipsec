# State

**Milestone:** SPADE joint protocol — **Unified Product (Option A)**  
**Status:** active — **B5 gate** (5-arm product grid)  
**Design:** [docs/superpowers/specs/2026-08-29-spade-unified-product-design.md](../docs/superpowers/specs/2026-08-29-spade-unified-product-design.md)  
**Diagnosis ledger:** [.planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md](SPADE-SCALAR-RECOVERY-DIAGNOSIS.md)

## B5 gate (live)

| Field | Value |
|-------|-------|
| Digest | `404b4884260b756a9b4777178ffae8350f6c9d0da0da6e912e3e06432090dbd4` |
| Arms | 5: `o32-certificate_targeted` (PRODUCT), `o32-validity_gated`, `o32-staged`, sobol48, qlognei48 |
| Rows/family | 15 keys × 5 arms = **75** |
| Stack | meanmarg + LOO-tail/1.5 + bagged5 + α0.95 + **ρ=0.95** + **(32,8,8)** |
| Preflight | `scripts/run_spade_unified_preflight.sh` |
| Gate report | `scripts/report_unified_spade_gate.py` |
| Monitor | `cat /tmp/spade-durable.status` |

**Primary claim:** manufacturing ans≥0.5 & emp≥0.9 on hill **and** levy.  
**Secondary claim:** Joseph LB round-budget (committed `results/lb-*.json`) — not a gate substitute.

## Superseded digests (do not resume)

| Digest | Why |
|--------|-----|
| `967eb654…` B4 | 12-arm; crash-loop empty bagged cert; superseded by B5 |
| `2ef1875c…` B3 | ρ=0.5 wrong acquisition |
| `7ba21e73…` B2 | α=0.98 FAIL |
| `b846fe2d…` B1 | floor 2.0 FAIL |
| `1c5c3b7e…` meanmarg | complementary near-miss |

## Next

- **PASS** with PRODUCT arm → 5×50 → LOFO → power → lockbox  
- **PASS** without PRODUCT arm → human: do not brand IVR ablation as SPADE  
- **FAIL** → archive, `analyze_gate_failures`, replay bags/Vmax only before new acquisition digest  
