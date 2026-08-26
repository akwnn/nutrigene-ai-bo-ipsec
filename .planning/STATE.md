# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Phase 4 — Development selection COMPLETE (`NO_SELECTION`)

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
- Lockbox size is selected only by the frozen held-out LOFO power rule: the first
  `n` in 350..2,000 that passes paired-normal power and exact-confidence
  nonparametric sensitivity for map and regret in all five development families.
  Failure to find such an `n` yields `INSUFFICIENT_POWER` and forbids lockbox access.

## Execution choice

- Registered campaigns will run locally; the GitHub Actions workflow remains a frozen,
  tested transport option but will not be dispatched. Development and any eligible
  lockbox must each complete as a homogeneous local run without mixing environments.

## Baseline evidence

On commit `02a6bfa`, the full suite produced 1,676 passed, 9 failed, and 2 skipped.
Two failures were caused by the isolated worktree lacking `.venv`; four were historical
bitwise numerical drift; three were material historical adaptive qLogEI/qLogNEI replay
mismatches already recorded in `.planning/codebase/CONCERNS.md`.

The current implementation produced 2,012 passed, 8 failed, and 2 skipped. All eight
failures were rerun in isolation and reproduced from an archive of pre-SPADE commit
`02a6bfa` using the same environment: one historical calibration stop-gate, four
historical exact-float replay drifts, and three historical stochastic qLogEI/qLogNEI
replay mismatches. They are therefore baseline reproducibility debt rather than SPADE
regressions and are not being repaired inside the prospective study branch.

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
- Task 6 resumable development runner and unanimous leave-one-family-out selector passed
  independent adversarial review. Exact shard names, write-once selection artifacts,
  tamper-resistant resume, and all five fold gates are enforced.
- The first development launch exposed a pre-analysis adapter-contract mismatch before
  any result shard existed: legacy `UnitScaled` floors are sampled rather than hard
  bounds. The aborted Hill/Rosenbrock checkpoints were isolated and never reused, and no
  comparative outcome was inspected. Truth-range contracts are now named and digest
  bound: Hill and lockbox are strict `[0,1]`; the four historical external families allow
  finite negative tails without clipping but still enforce an upper bound of one. The
  focused suite is 103 passed and the broader relevant suite is 171 passed; independent
  re-review found no remaining issue.
- The next clean launch exposed a registered-scale implementation bottleneck before any
  IVR row completed: the dense path materialized an 18,432-square covariance (about
  2.7 GB per process). Five one-row, qLogNEI-only checkpoints were isolated without
  reading metrics and will not be reused. IVR now evaluates exact posterior covariance
  in deterministic 1,024-candidate blocks and applies the same sequential Schur updates.
  It selected identical points to an independent dense reference on five randomized
  positive-definite cases, completed the real 16,384-candidate/2,048-reference shape in
  2.061 seconds, and passed 174 focused compatibility tests.
- Task 7 guarded lockbox execution, manifest-driven confirmatory analysis, and the
  fail-closed release validator passed final independent adversarial review. Hashes are
  byte-bound in disjoint namespaces; every shard has an exact registered filename,
  completion/count/command/provenance contract, and local family/key/arm grid; malformed
  numeric or deeply nested JSON becomes a written FAIL report; publication is write-once
  with the completion manifest installed last. The final relevant suite is 275 passed
  with two pre-existing Torch deprecation warnings, and the reviewer reported no
  Critical, Important, or Minor findings.
- The pre-lockbox power system is fully implemented through release validation. It
  authenticates exact committed held-out development bytes, recomputes the selected
  LOFO analysis, writes one immutable power artifact, derives every lockbox range and
  count from its decision, and binds the same power hash/source through shard, merge,
  analysis, and release. Symlink/path-swap races and post-outcome code reinterpretation
  are rejected before outcome readers or oracle construction can run.
- Lockbox execution supports any number of disjoint cross-host shards with exact
  no-gap/no-overlap coverage. Full host provenance is retained per row while a frozen
  science-affecting environment identity permits different virtualenv paths on
  compatible hosts. The focused end-to-end suite is 262 passed with two pre-existing
  Torch deprecation warnings. After final immutable metadata/read/write and source-blob
  fixes, the two touched lockbox/release modules passed 90 tests with the same two
  warnings. No development or lockbox outcome was run or opened.
- The logistics-only execution freeze preserves the scientific protocol digest at
  `00ce6971a990749645052273215897f57562106610777d0d8ce417e8e9afdd1a` and binds the
  workflow, matrix, worker, merger, dependency, environment, and parallelism contracts.
  After merging the final immutable-read safeguards and refreshing dependent hashes,
  the clean integrated affected suite passed 203 tests with two pre-existing Torch
  deprecation warnings. No workflow was launched and no outcome was read.

## Development campaign outcome (2026-08-26)

- Local REGISTERED development completed on commit `c9199a3` with single-thread BLAS.
- All five families have complete `000-050` shards (Hill via merged parent ledger after a
  path-normalized `000-001` re-run). Artifacts archived under
  `results/historical-joint-v1-noselection/`.
- Unanimous LOFO selection wrote `spade-selected-protocol.json` with status
  `NO_SELECTION`: every SPADE candidate failed the registered empirical-containment ≥ 0.9
  gate on every training fold (and on the all-five refit diagnostic). No candidate survived
  step 1, so steps 2–4 were skipped.
- Per the frozen protocol, lockbox access for that study is **forbidden**.

## Manufacturing certificate recovery (2026-08-26)

- Claim hierarchy locked in
  `docs/superpowers/specs/2026-08-26-spade-manufacturing-certificate-recovery-design.md`:
  qualified operating region + round economy + setpoint/map parity; KF-3 targeting is not
  the selling point.
- Root cause: largest Vorob'ev CE under a misspecified plug-in GP was over-willing
  (answer rate ≈1, empirical containment often 0.15–0.5).
- Redesign: registered `certificate_volume_rule: smallest` in
  `conservative_set_split` / scoring settings / joint yaml.
- New study id `spade-joint-48-mfg-cert-2026-08-26`; protocol digest
  `bebbaba1ee330f6a4c699b6f05e27df811158ceff15152cea78f0bf7ce0cc656`.
- Prior v1 shards archived; new development must write fresh live `results/spade-development-*`.

## Next action

Commit the recovery freeze on a clean tree, then re-run REGISTERED development (50 keys ×
five families), LOFO selection, and — only if `SELECTED` and `POWERED` — lockbox. Do not
reopen the archived v1 lockbox path. Update RESEARCH-SUMMARY manufacturing claims only
after confirmatory PASS.

