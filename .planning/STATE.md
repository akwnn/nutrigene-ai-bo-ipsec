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

## Baseline evidence

On commit `02a6bfa`, the full suite produced 1,676 passed, 9 failed, and 2 skipped.
Two failures were caused by the isolated worktree lacking `.venv`; four were historical
bitwise numerical drift; three were material historical adaptive qLogEI/qLogNEI replay
mismatches already recorded in `.planning/codebase/CONCERNS.md`.

## Next action

Write and self-review the implementation plan, then execute it task-by-task with TDD and
review gates.

