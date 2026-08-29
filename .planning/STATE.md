# State

**Milestone:** SPADE joint protocol  
**Status:** active — **B4 gate** (Joseph-aligned cert_targeted)  
**Diagnosis ledger:** [.planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md](SPADE-SCALAR-RECOVERY-DIAGNOSIS.md)  
**Current phase:** hill+levy 0–15 on digest `967eb654…` (12 arms × 15 keys = 180 rows/family)

## B4 gate (Joseph-aligned acquisition)

| Field | Value |
|-------|-------|
| Digest | `967eb6544e1f438aaca3a3ea3bb9a7f4115d05cb014623bab0d1bdf8b8f4bfb6` |
| Change from B3 | `certificate_rho` **0.95** + R=3 schedule **(32,8,8)** + per-round candidate menu |
| Monitor | `cat /tmp/spade-durable.status` |

**Stack:** meanmarg + LOO-tail + floor 1.5 + bagged5 + α 0.95 + **Joseph cert contour (ρ=0.95, R=3)**.

## B3 superseded (wrong acquisition defaults)

| Digest | Issue |
|--------|-------|
| `2ef1875c…` | `certificate_targeted` used ρ=0.5 (median) + four×4 batches — not Joseph's winner |

## Failed gates (archived — do not resume)

| Study | Digest | Survivors | Analysis |
|-------|--------|-----------|----------|
| meanmarg floor15 | `1c5c3b7e…` | 0 | [gate-summaries/…meanmarg-gate-fail.json](artifacts/gate-summaries/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail.json) |
| floor20 (B1) | `b846fe2d…` | 0 | [gate-summaries/…floor20….json](artifacts/gate-summaries/historical-mfg-cert-floor20-loo-tail-meanmarg-gate-fail.json) |
| alpha0.98 (B2) | `7ba21e73…` | 0 | [gate-summaries/…alpha098….json](artifacts/gate-summaries/historical-mfg-cert-floor15-loo-tail-meanmarg-alpha098-gate-fail.json) |

Shard archives under `results/historical-mfg-cert-*/` (gitignored; JSON summaries in `.planning/artifacts/gate-summaries/`).

**Persist to git:** commit `.planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md`, `.planning/STATE.md`, `.planning/artifacts/gate-summaries/*.json`, and decisions spec updates so diagnosis survives worktree resets.

## What went wrong vs right (short)

**Wrong:** floor 2.0; α 0.98; map_iou abstention; detector knobs (k_eff, selection-blind).  
**Helped but insufficient:** meanmarg, LOO-tail, floor 1.5, o32 + validity_gated.  
**Testing now:** Joseph-aligned cert_targeted (ρ=0.95, schedule 32+8+8 per LB R=3 winner).

## Next on B4 outcome

- **PASS** → watchdog advances to full 5×50 → LOFO → power → lockbox  
- **FAIL** → archive shards, update diagnosis ledger, run `replay_certificate_scoring.py` sweeps before B4
