# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Scalar recovery B1 — `latent_inflation_floor: 2.0` gate **running**

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Manufacturing claim hierarchy unchanged; Plate-2 tertiary only.
- Recovery stack base: `smallest` + assay + `loo_calibration_tail` + meanmarg + `Vmax=0.001`.
- Meanmarg gate (`1c5c3b7e…`) **FAIL** — archived.
- Floor15 gate (`681947bc…`) **FAIL** — archived.
- Multi-CQA synthetic benchmark **PASS** (`b29bb57e…`).
- `origin/codex/spade-gate-fix` **merged** (LOFO/lockbox hardening).
- Phase A instrumentation: `latent_inflation_factor` + `certificate_abstention_reason` in scores.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` |
| mfg floor-1.5+LOO-tail | `681947bc…` | **gate FAIL** |
| mfg floor-1.5+LOO-tail+meanmarg | `1c5c3b7e…` | **gate FAIL** |
| multi-CQA benchmark | `b29bb57e…` | **PASS** |
| **B1 floor20+meanmarg** | `b846fe2d…` | **gate running** |

## Gate diagnosis (meanmarg, 2026-08-28)

0 survivors. Hill emp 1.0 (`o32-staged`); levy emp 0.90 (`o32-validity_gated`) but
hill emp 0.875 on that arm — complementary pairing. Model-internal containment
~97% on failed runs; levy is binding family.

## Next action

1. Hill+levy 0–15 gate on digest `b846fe2d…`.
2. If PASS → full 5×50 → LOFO → power → lockbox.
3. If FAIL → B2 alpha sweep per ledger §3.6.
4. Ledger: `docs/superpowers/specs/2026-08-27-spade-certificate-improvement-decisions.md` §9

## Ops durability

- `~/spade-ops/` LaunchAgents: meta, persist, health
- Backups: `~/spade-ops/persist-backups/`
- Check: `~/spade-ops/spade_health.sh`
