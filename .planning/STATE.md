# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Phase 1 — Freeze and foundations

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Existing families are development-only; four new randomized generators form lockbox.
- Primary target is future-response reliability at gamma 0.95.
- Certificate validation is empirical truth containment, not model-internal non-rejection.
- Development compares exactly three policies by three opening sizes.
- Lockbox success is a four-endpoint conjunction required in every family.
- The tau correction is retained as a per-instance quantile of the gamma-adjusted
  reliability margin, rather than a fixed fraction of peak height or a latent-only
  quantile.
- Replicate-pooled noise estimation is excluded: its oracle-variance regret ceiling
  improved by 0.00816, below the registered 0.01 build bar, and the 48-evaluation budget
  has no replicate reserve.
- OA-LHS is excluded: exact strength-2 construction needs 49 evaluations and the matched
  Hartmann6 study did not reduce design-lottery SD. The opening remains scrambled Sobol.

## Baseline evidence

On commit `02a6bfa`, the full suite produced 1,676 passed, 9 failed, and 2 skipped.
Two failures were caused by the isolated worktree lacking `.venv`; four were historical
bitwise numerical drift; three were material historical adaptive qLogEI/qLogNEI replay
mismatches already recorded in `.planning/codebase/CONCERNS.md`.

## Next action

Correct the fail-closed checkpoint/provenance defects found in the first independent
review, merge the committed tau/noise/OA-LHS evidence, then continue task-by-task with TDD
and independent review gates.
