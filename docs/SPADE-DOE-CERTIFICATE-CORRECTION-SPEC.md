# DC2 — variance-corrected DoE certificate replication

**Status: FROZEN, NOT RUN.** This protocol must be committed and reviewed before any DC2
outcome is generated. Runner: `scripts/run_dc2_doe_certificate.py`. Analyser:
`scripts/analyse_dc2_doe_certificate.py`. Intended data: `results/dc2-sweep.json`.

## 1. Reason for correction

The historical DC runner discarded the observation variance returned for each DoE well and
replaced all 48 values with one constant. The evaluator's registered model is per-well:
`Yvar_i = Y_i^2 * sigma_rel^2 + sigma_add^2`. Because certification depends on GP
uncertainty, the historical containment numbers cannot adjudicate the DoE claim.

The historical files remain immutable under `results/historical-dc-constant-yvar/`. They are
diagnostic evidence only. A five-seed corrected check has already been inspected, so neither
it nor any seed from the historical `0..31` range is eligible for confirmatory interpretation.

## 2. Frozen design

- Families: `ackley`, `hartmann6`, `hill`, `levy`, `rosenbrock`.
- Fresh seeds: integers `32..63`, exactly 32 per family.
- Arms: screened `doe` at 3 rounds, `doe_unscreened` at 3 rounds, and committed `spade` at
  5 rounds.
- Budget: exactly 48 wells per campaign.
- Noise: `sigma_rel = 0.25` through the existing evaluator construction.
- Prevalence grid: `p in {0.70, 0.30}`.
- Inflation grid: `c in {1.0, 1.5, 2.0, 3.0}`.
- Certificate alpha, subset grid, truth containment, answer floor, and Clopper-Pearson lower
  bound are unchanged from the original DC specification.
- Every DoE observation uses the exact `Yvar_visited` returned by its evaluator.

The exact grid contains `5 * 32 = 160` family/seed jobs and
`160 * 3 * 2 * 4 = 3,840` result rows. Missing or duplicate cells forbid adjudication.

## 3. Primary estimand and acceptance rule

At prevalence `p = 0.30`, choose the smallest registered inflation `c` for each arm that
simultaneously reaches answer rate at least `0.05` and one-sided 95% Clopper-Pearson
containment lower bound at least `0.90`.

DC2 confirms the narrow DoE certification claim only if:

1. `spade` satisfies that gate; and
2. neither `doe` nor `doe_unscreened` satisfies it.

All answer and containment counts must be shown. Regret and family-specific results are
secondary descriptive estimates. No family-specific significance claim is licensed unless a
multiple-testing procedure is registered before execution.

## 4. Failure and provenance rules

- Any campaign exception stops execution. A failed run remains `PARTIAL`; the runner must not
  swallow the exception or mark the artifact complete.
- Rows are persisted only after all three arms and all eight `(p, c)` cells for one family/seed
  job finish.
- Resume skips a job only when its entire 24-cell grid is present exactly once.
- `COMPLETE` is written only after exact-grid validation succeeds.
- The artifact records source commit and dirty state, seed bounds, families, arms, grids,
  completed jobs, and SHA-256 digests of this specification and the runner.
- Resume refuses a source, protocol, or digest mismatch.
- The analyser refuses partial status, dirty source provenance, non-finite values, missing or
  duplicate cells, and digest drift before computing any statistic.

## 5. Execution boundary

Freezing and unit-testing the protocol is part of the Joseph integration. Running the real
five-family replication is not. Execution requires a separate decision after this protocol
commit has passed review from a clean source tree.
