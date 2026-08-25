# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Phase 2 — Joint SPADE implementation

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

## Completed in this milestone

- Task 1 deterministic seed/noise/checkpoint/replay foundations passed independent review.
  The focused post-merge suite is 186 passed with two third-party deprecation warnings.
- Checkpoints now reject oracle/configuration/noise/cursor mismatches and preserve legacy
  RNG state for byte-identical resume.
- The committed tau-quantile, oracle-noise ceiling, and OA-LHS design-lottery evidence from
  `origin/main` is merged into this branch.
- Task 2 common learned-noise GP, explicitly seeded qLogNEI, and Schur-updated IVR passed
  independent numerical review. The focused suite is 96 passed, including randomized
  brute-force conditioning and extreme-weight tests.
- Task 3 predictive reliable-region and split certificate passed independent review. The
  focused suite is 80 passed; joint draws are deterministic without global RNG mutation,
  gamma-aware, split-isolated, and empirically scored with exact confidence bounds.
- Task 4 unified SPADE/Sobol48/qLogNEI48 runners passed independent review: exact 48-point
  budgets, no truth access, frozen registered constants, identity-bound thresholds and
  schedules, RNG isolation, and non-scientific TEST_ONLY execution identities.
- Task 5 lockbox generators/common scorer passed independent review. All live digests
  match, controlled thresholds achieve 25% prevalence, scorer refits all 48 observations,
  and the manifest remains `FROZEN_UNOPENED` with no comparative outcomes inspected.

## Next action

Implement and independently review the resumable development runner and prespecified
nested-family selection, then execute the frozen development campaign grid.
