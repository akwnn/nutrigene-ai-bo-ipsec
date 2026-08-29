# State

**Milestone:** SPADE joint protocol  
**Status:** active — **B3 gate RUNNING**  
**Diagnosis ledger:** [.planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md](SPADE-SCALAR-RECOVERY-DIAGNOSIS.md)  
**Current phase:** hill+levy 0–15 on digest `2ef1875c…` (12 arms × 15 keys = 180 rows/family)

## B3 gate (live)

| Field | Value |
|-------|-------|
| Digest | `2ef1875c66a4427c8eef70bb83763da4c071144e388859867eda94c8faa0faec` |
| Commit | `cc43b09` |
| Monitor | `cat /tmp/spade-durable.status` |
| Log | `/tmp/spade-durable.log` |
| Supervisor | `~/spade-ops/spade_gate_then_full_watchdog.sh` |

**Stack:** meanmarg + LOO-tail + floor 1.5 + smallest + Vmax 0.001 + **bagged5** + α **0.95** + **cert_targeted o32**.

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
**Testing now:** bootstrap bagged cert + cert_targeted acquisition.

## Next on B3 outcome

- **PASS** → watchdog advances to full 5×50 → LOFO → power → lockbox  
- **FAIL** → archive shards, update diagnosis ledger, run `replay_certificate_scoring.py` sweeps before B4
