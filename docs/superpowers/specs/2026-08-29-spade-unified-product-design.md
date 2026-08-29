# Unified Product SPADE — Design (Option A)

**Status:** approved for implementation (2026-08-29)  
**Primary claim:** manufacturing certificate recovery (hill+levy ans/emp gate → LOFO → lockbox)  
**Secondary claim:** Joseph round-budget (SPADE R=5 certifies; qLogNEI needs ~10) on the same wells, separate estimand — never a gate substitute  

---

## 1. Product thesis

**SPADE is the 48-well method that spends culture rounds on the certificate contour (ρ=0.95, R≥3) and returns a smallest-volume manufacturing region with LOO / meanmarg / bagged honesty — not a Plate-2 hybrid-IVR lottery.**

---

## 2. Good vs bad (locked)

### Keep

| Layer | Choice | Source |
|-------|--------|--------|
| Acquisition | `certificate_targeted`, **ρ=0.95**, schedule **(32, 8, 8)** | Joseph LA/LB |
| Candidate menu | Fresh Sobol per adaptive batch | `multiround.py` |
| Meanmarg | on | Joseph real-data collapse fix |
| LOO-tail inflation | floor **1.5** | Manufacturing KT-5; floor 2.0 REJECTED |
| Bagged certs | n=**5** intersect | Joseph bagged + mfg conservatism |
| Volume | `smallest` + Vmax **0.001** | Manufacturing honesty |
| α | **0.95** | α=0.98 REJECTED |
| Pipeline | gate → 5×50 → LOFO → power → lockbox | Manufacturing REGISTERED |

### Kill forever

- floor 2.0, α=0.98, ρ=0.5 for cert_targeted  
- `k_eff`, selection-blind, SUR as default, top-k as default region  
- Wholesale merge of `kr-effective-resolution`  
- Expanding back to o40/o44 / 9–12 SPADE hybrids without a measured co-pass  
- Full 5×50 on any digest that fails hill+levy 0–15  
- Treating Joseph volume/R=5 certify-on as manufacturing PASS  

---

## 3. Dual estimand (do not mix)

| | Manufacturing (PRIMARY / GATE) | Joseph round-budget (SECONDARY) |
|--|-------------------------------|----------------------------------|
| Estimand | Reliability region + smallest CE + bags + Vmax | Plate-2 Vorob'ev / largest CE + C_GRID |
| Gate | ans≥0.5 & emp≥0.9 on **hill and levy**, same arm | CP-LB≥0.90 @ ans≥0.05; R-matched volume |
| When | REGISTERED development / lockbox | Locked rescore / LB-LC narrative |

Same campaigns may feed both scores. Secondary never decides a manufacturing survivor.

---

## 4. Minimal arm set (B5+)

| Role | Arm |
|------|-----|
| **PRODUCT** | `spade-o32-certificate_targeted` (ρ=0.95, 32+8+8) |
| Ablation | `spade-o32-validity_gated` (legacy 4×4) |
| Ablation | `spade-o32-staged` (legacy 4×4) |
| Comparator | `sobol48` |
| Comparator | `qlognei48` |

**5 arms total.** Drop all o40/o44 and `fixed_hybrid`.

Product identity: LOFO / lockbox should prefer the PRODUCT arm; if only an ablation co-passes, treat as product FAIL for branding and escalate to human decision (do not ship IVR-hybrid as “SPADE”).

---

## 5. Execution order

1. **Fix** bagged empty-intersection score validation (blocks all REGISTERED runs).  
2. **Freeze B5** digest with 5-arm set + Joseph acquisition + mfg scoring.  
3. **Preflight** before every REGISTERED gate (safeguards + clean tree + digest match).  
4. Gate hill+levy 0–15.  
5. PASS → 5×50 → LOFO → power → lockbox.  
6. FAIL → archive → `analyze_gate_failures` → offline replay (bags/Vmax only) before any new acquisition digest.  
7. Parallel (non-blocking): LC confirmatory for Joseph headline when compute free.

---

## 6. Success criteria

**Manufacturing:** ≥1 SPADE arm with ans≥0.5 and emp≥0.9 on both hill and levy (keys 0–15); preferred survivor = PRODUCT arm.

**Joseph (secondary):** existing LB PASS retained; LC confirmatory when run; never substitutes for manufacturing gate.
