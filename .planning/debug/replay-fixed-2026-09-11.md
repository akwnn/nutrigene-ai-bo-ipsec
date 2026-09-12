---
status: investigating
created: 2026-09-11
updated: 2026-09-11
trigger: Diagnose historical replay failures without weakening tests or replacing references.
---

## Current focus

The five fixed-design/calibration gates were freshly reproduced. No scientific code,
equality assertion, threshold, or retained reference was changed. The original numerical
cause remains unresolved; a current refactor or Torch thread count is not sufficient
to explain the tested failures. No new study grid or lockbox outcomes were accessed.

## Fresh original-test evidence

Five selected tests failed in 22.64 seconds:

| Test | Observed failure |
|---|---|
| D23 full-space Rule P vs Fix 1 | 0.25251124591423746 vs 0.2525116337195932; gap 3.878e-7 |
| P4 K6 LHS scorer bitwise replay | first sup_err 0.4670338076864847 vs 0.4670338076864849 |
| Q59 unscreened additivity | Rule C gap 3.1730922445127874e-8 |
| spread_gp extraction vs Q52 | worst gap 3.122972902502852e-7 across six checked rows |
| P7 calibration checkpoint | checkpoint executes, then exact map gate fails: 48 fields, worst 9.082e-13 |

Tests: `test_d23_doe_subspace.py::test_full_space_rule_p_reproduces_fix1`,
`test_p4_coord.py::test_k6_scorer_reproduces_a_committed_lhs_row_bitwise`,
`test_q59_map_rescore.py::test_the_edit_is_additive_and_reproduces_the_committed_columns`,
`test_spread_gp.py::test_the_extracted_arm_reproduces_the_committed_q52_rows_exactly`,
`test_calibration.py::test_the_checkpoint_write_path_actually_runs`.

## Controlled diagnosis

- D23 and the original Fix 1 runner, called independently on key
  `033466197eba3ddb`, seed 0, produce **the same current regret and recommendation**.
  Both miss the frozen reference. Their Rule A and grid-only Rule P match the
  reference exactly. Continuous recommendation coordinates differ from the reference
  by up to 4.982355415350526e-6; posterior objective differs by -2.3691049122476215e-12.
  Thus the drift is visible at continuous recommendation, not just a reporting-rounding
  issue, and is not introduced by D23's full-space wrapper alone.
- P4 first LHS key has 84 numeric mismatches across 24 scoring cells, worst
  6.661338147750939e-16. Affected fields: `sup_err`, `grid_r2`, `brier_pred`,
  `brier_latent`; no nonnumeric/discrete mismatch was found in this probe.
- Q59 first unscreened key exactly matches Rule A, oracle-best, design size 47,
  and residual df 19; Rule C is 0.9114370496078972 rather than 0.9114370813388196.
  The retained file lacks the old recommended point, so old/new point identity
  cannot be recovered from these scalars.
- First Q52 spread key: Rule A matches 0.16952961000167888 exactly. Rule C is
  0.14680879036455063 rather than 0.14680880571307187. This is one diagnostic key;
  the original six-key test above establishes its wider failure.
- Repeating these four probes with Torch threads set to 1 and 4 gives identical
  results. Repeating in a new process with `VECLIB_MAXIMUM_THREADS=1` also gives
  identical results; actual Torch counts 1 and 4 were recorded. This control is not
  proof of historical BLAS equivalence, only evidence that these settings do not fix
  the present failure.
- AST comparisons against retained pre-SPADE commit `98c043c` are exactly equal
  for `metrics.constrained_argmax`, `rsm.fit_second_order`, `surrogate.build_gp`,
  and `surrogate._finish`. The Q59 `return_design` historical commit is additive;
  changing an exact test to tolerate drift would not diagnose the original cause.
- P7 output reports zero regret-gate failures, zero identity failures, and zero
  changed latent-map cells. It writes then intentionally exits 1 at map fidelity;
  the checkpoint failure is not an unexplained file-writing crash.

## Environment and recovery boundary

Python 3.11.15, Torch 2.13.0, NumPy 2.4.6, SciPy 1.17.1, BoTorch 0.18.1,
GPyTorch 1.15.2 on macOS-26.2-arm64. NumPy reports Accelerate BLAS/LAPACK with
unknown binary version. These package versions match available historical metadata,
but the recorded dirty source, wheel hashes, binary/platform state and intermediate
campaign traces are not recoverable from that metadata alone.

The temporary probe is `/private/tmp/diagnose-fixed-replay-20260911.py`, with output
`/private/tmp/fixed-replay-t{1,4}-20260911*.json`. It runs only existing first-failing
keys and writes diagnostics outside retained results. No seed search or tolerance
adjustment was attempted. Further attribution needs the original environment or
original intermediate trace; current agreement between two paths is not a replacement
for the frozen reference gate.

## Fresh-install control

On 2026-09-11, public PyPI dependencies were downloaded uncached into a fresh isolated
virtual environment and the r2 archival source was installed. The four fixed-design
tests above still fail with identical values. The direct P7 one-key command also exits
1 with the same 48 map-field mismatches and worst drift 9.082e-13. Direct invocation
was required because the existing integration test hard-codes `.venv/bin/python`.
The seven-test run including adaptive probes failed in 89.98s; meanwhile 106 focused
publication/archive tests and all nine prospective release checks passed in this fresh
environment. This is a same-host installation control, not historical-environment or
cross-platform equivalence. References, exact assertions, and scientific source were
unchanged. Original generating provenance is still needed for further attribution.
