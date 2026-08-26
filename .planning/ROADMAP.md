# Roadmap

## Phase 1 — Freeze and foundations — COMPLETE

Write the governing design and implementation plan, isolate the branch, repair
deterministic seed/checkpoint foundations, and classify historical replay failures.

Requirements: REP-01, REP-04.

## Phase 2 — Joint SPADE method — COMPLETE

Implement the common learned-noise GP, deterministic discrete qLogNEI, IVR acquisitions,
whole-batch allocation, 48-evaluation SPADE orchestration, and common comparator paths.

Requirements: METH-01 through METH-04.

## Phase 3 — Predictive certification — COMPLETE

Implement controlled-prevalence thresholding, future-response reliability maps,
gamma-aware set draws, split conservative regions, exact confidence bounds, and common
map/regret/certificate scoring.

Requirements: CERT-01 through CERT-05.

## Phase 4 — Development selection — COMPLETE (`NO_SELECTION`)

Ran the registered nine-candidate development study and nested family folds. Selection
status is `NO_SELECTION` (no candidate met empirical containment ≥ 0.9 on any LOFO
training fold). Locked artifacts are under `results/spade-development-*` and
`results/spade-selected-protocol.json`.

Requirement: EVAL-01.

## Phase 5 — Lockbox evidence — STOPPED (selection gate)

Lockbox is forbidden after `NO_SELECTION`. Generators remain frozen/unopened; no powered
sample size and no lockbox outcomes may be produced for this protocol instance.

Requirements: EVAL-02 through EVAL-04, REP-02 — N/A under stop rule.

## Phase 6 — Publication release — NEXT (negative-stop handoff)

Freeze the `NO_SELECTION` evidence, update methods/summary from selection artifacts only,
and hand off bounded joint-protocol claims (registered negative stop; no lockbox claims).

Requirements: REP-03, REP-05 (as applicable without lockbox release).
