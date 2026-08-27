# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Live floor-1.5 gate on campaign WT; combined Joseph+Alana merge on merge WT

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Manufacturing claim hierarchy unchanged; Plate-2 tertiary only.
- **Live gate (do not disturb):** `.worktrees/spade-campaign` —
  `smallest` + assay + LOO-tail + **floor 1.5** + Vmax  
  study `spade-joint-48-mfg-cert-floor15-loo-tail-2026-08-27`, digest `681947bc…`.
- **Combined next protocol (merge branch):** same + **`mean_marginalisation: true`**  
  study `spade-joint-48-mfg-cert-floor15-loo-tail-meanmarg-2026-08-27`, digest `1c5c3b7e…`  
  branch `spade/merge-joseph-alana` @ `.worktrees/spade-merge-joseph`.
- Prior LOO-tail-only gate (`6f38077e…`) **FAIL** — archived.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` |
| mfg assay+smallest | `f6eca072…` | shortfall; archived |
| mfg LOO-RMS+Vmax | `6e6dec2a…` | levy ~0.72; archived |
| mfg LOO-tail+Vmax | `6f38077e…` | **gate FAIL** (archived) |
| mfg floor-1.5+LOO-tail (live gate) | `681947bc…` | gate in flight |
| **mfg floor-1.5+LOO-tail+meanmarg (merge)** | `1c5c3b7e…` | implemented; gate after cutover |

## Next action

1. Do not touch campaign worktree code while `run_spade_development` runs.
2. Finish hill+levy 0–15 gate on `681947bc…`; read verdict.
3. Complete merge-branch tests/commit; cut over only when idle.
4. New gate on `1c5c3b7e…` (meanmarg) — do not resume floor15 shards.
5. Ledger: `docs/superpowers/specs/2026-08-27-spade-certificate-improvement-decisions.md`
