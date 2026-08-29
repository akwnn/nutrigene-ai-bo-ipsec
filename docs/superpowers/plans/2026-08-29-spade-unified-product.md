# Unified Product SPADE Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship Option A unified SPADE — manufacturing gate primary, Joseph acquisition + scoring honesty merged, Joseph round-budget secondary.

**Architecture:** One PRODUCT arm (`o32-certificate_targeted`, ρ=0.95, schedule 32+8+8) + two o32 ablations + two comparators. Scoring: meanmarg + LOO-tail/1.5 + bagged5 + smallest + Vmax. Dual-estimand: never mix Joseph Vorob'ev volume into the manufacturing survivor decision.

**Tech stack:** existing `spade.py` / `spade_study.py` / `run_spade_development.py` / joint yaml digests.

## Tasks (status)

1. [x] Fix bagged empty-intersection validation crash (`c2b2c8f`)
2. [x] Design spec Option A (`docs/superpowers/specs/2026-08-29-spade-unified-product-design.md`)
3. [x] Shrink arm grid to 5; freeze digest `404b4884…`
4. [x] Preflight + gate report scripts
5. [x] Watchdog arm-count + survivor eval for product arm
6. [ ] Gate hill+levy 0–15 on B5 (watchdog)
7. [ ] On PASS → 5×50 → LOFO → power → lockbox
8. [ ] On FAIL → archive + analyze; Joseph secondary remains committed LB results

## Files

| File | Role |
|------|------|
| `configs/experiment/spade-joint.yaml` | Frozen B5 protocol |
| `scripts/run_spade_development.py` | 5-arm grid + PRODUCT_ARM_ID |
| `scripts/run_spade_unified_preflight.sh` | Pre-REGISTERED checks |
| `scripts/report_unified_spade_gate.py` | Primary survivors + Joseph secondary note |
| `src/boec/spade.py` | ρ=0.95 + (8,8) for cert_targeted |
| `src/boec/spade_study.py` | Bagged empty null containments |
