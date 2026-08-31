# DC2 — variance-corrected DoE certificate (frozen protocol)

This specification is frozen before any DC2 outcome exists.  It repeats the DC
comparison with the evaluator's per-well observation variance, rather than the
constant variance used by the historical files.  The historical files in
`results/historical-dc-constant-yvar/` are retained for audit only.

## Registered design

- Families: `ackley`, `hartmann6`, `hill`, `levy`, `rosenbrock`.
- Seeds: **32 through 63 inclusive** (`seed_start=32`, `seed_stop=64`). Seeds 0--31
  are excluded from confirmatory interpretation because their outcomes, including
  a corrected five-seed diagnostic, were inspected before this freeze.
- Arms: `doe`, `doe_unscreened`, and `spade`; 48 wells per campaign. DoE uses 3
  rounds and SPADE uses its registered 5 rounds.
- Certification grid: `p ∈ {0.70, 0.30}`, inflation `c ∈ {1.0, 1.5, 2.0, 3.0}`,
  alpha 0.95, and the registered subset and containment definitions.
- Primary estimand: paired difference in final noiseless regret,
  `regret(spade) - regret(doe)`, pooled across the 160 family/seed pairs.
  The pre-registered acceptance rule is a two-sided 95% bootstrap interval that
  excludes zero; family estimates are descriptive unless a multiplicity correction
  is registered before execution.

Every campaign must produce 3 arms × 2 p values × 4 inflation values = 24 rows,
so the exact artifact contains `5 × 32 × 3 × 2 × 4 = 3840` rows and 160
family/seed jobs (each job contains all three arms).
Every `(family, seed, arm, p_value, inflation_c)` cell occurs exactly once.
Any campaign error, missing or duplicate cell, non-finite value, or provenance
mismatch makes the artifact incomplete; the analyser must refuse adjudication.
Resume may skip a job only when all 24 rows for that job are present and valid.

## Provenance and execution

The runner records the runtime source commit and dirty flag, SHA-256 of this spec
and of the runner, the seed bounds, and the exact rows.  It writes atomically after
each complete job. `status=COMPLETE` is permitted only after exact-grid validation;
writer exceptions propagate and cannot yield a complete artifact.  The analyser
is fail-closed and does not overwrite duplicate keys.

No confirmatory experiment is launched by freezing this protocol.  A future
execution decision must cite this protocol commit and preserve these fields.
