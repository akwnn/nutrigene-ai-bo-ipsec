# Task 4 report — Figure 2 terminal-rule display

## Outcome

Implemented `build_figure2(data, preset) -> FigureBundle` in
`boec.paper_figures.figure2`. The portable, three-panel figure shows the same
campaigns under Rule A and Rule P, zero-referenced paired Rule-P-minus-Rule-A
intervals with a stated direction, and the validated Rule-A search-plus-
identification decomposition for the compatible arms.

## RED/GREEN TDD evidence

### RED: absent builder

Added the Figure 2 semantic contract before creating the builder and ran:

```text
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest tests/test_paper_figure_builders.py::test_figure2_encodes_same_campaign_rules_contrasts_and_decomposition -v
```

Result: expected collection-time
`ModuleNotFoundError: No module named 'boec.paper_figures.figure2'`.

### GREEN: semantic contract

Implemented the builder and ran:

```text
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest tests/test_paper_figure_builders.py::test_figure2_encodes_same_campaign_rules_contrasts_and_decomposition tests/test_paper_figure_builders.py::test_figure2_portable_text_stays_inside_the_rendered_figure -v
```

Result: `2 passed in 1.20s`.

### RED/GREEN: portable text containment

Strengthened the visual-boundary test to inspect all rendered Matplotlib text.
It initially failed because the automatic `0.20` decomposition x-tick was
outside the portable canvas. The builder now bounds the axis to evidence and
sets visible ticks explicitly.

The same two-test command then passed: `2 passed in 1.19s`.

## Implementation

- Panel A joins Rule A and Rule P means for Classical DoE, qLogEI, qLogNEI,
  and SPADE from the same campaigns. Method names are direct endpoint labels;
  the two close qLog labels receive small opposite offsets for legibility.
- Panel B uses horizontal paired 95% bootstrap intervals and point estimates,
  not contrast bars or significance stars. Its black vertical reference is
  zero and its x-label states that negative values mean lower Rule-P regret.
- Panel C stacks `oracle_best` (search loss) and `identification_gap` for the
  evidence-selected compatible arms only. Its panel title and direct colour
  key state the Rule-A decomposition.
- Every `apply_axis_style` and `panel_label` call receives the supplied
  `VenuePreset`; all added visible text uses `preset.body_pt` (7.5 pt in the
  portable preset, within the requested final-size range).

## Files

- `src/boec/paper_figures/figure2.py` — Figure 2 builder.
- `tests/test_paper_figure_builders.py` — semantic metadata and full-render
  text-containment contracts.
- `.superpowers/sdd/task-4-report.md` — this task report.

## Test commands and results

```text
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest tests/test_paper_figure_builders.py tests/test_paper_figure_core.py tests/test_paper_figure_evidence.py -v
```

Result: `39 passed in 7.76s`.

```text
MPLCONFIGDIR=/private/tmp/boec-mplconfig .venv/bin/python -m pytest
```

Result: `1679 passed, 2 skipped, 8 failed, 13 warnings in 321.03s`.
All Figure 2 builder/core/evidence tests passed in this run. The eight failures
are unrelated existing calibration/replay exactness gates:

- `tests/test_calibration.py::test_the_checkpoint_write_path_actually_runs`
- `tests/test_d23_doe_subspace.py::test_full_space_rule_p_reproduces_fix1`
- `tests/test_p4_coord.py::test_k6_scorer_reproduces_a_committed_lhs_row_bitwise`
- `tests/test_q59_map_rescore.py::test_the_edit_is_additive_and_reproduces_the_committed_columns`
- `tests/test_replay.py::test_family_qlogei_reproduces_the_committed_q42_column_exactly`
- `tests/test_replay.py::test_family_qlogei_reproduces_on_every_family_and_at_d8`
- `tests/test_replay.py::test_family_qlognei_reproduces_the_q59_hartmann_column`
- `tests/test_spread_gp.py::test_the_extracted_arm_reproduces_the_committed_q52_rows_exactly`

`git diff --check` passed.

## Visual review

Rendered both `/private/tmp/figure2-portable.png` at 450 dpi and a portable
SVG using the `portable` preset. Checked that all panel labels, direct method
labels, titles, ticks, direction text, and the decomposition colour key remain
inside the final canvas. The review led to removing an overlapping `no change`
annotation and correcting the out-of-bounds terminal tick.

## Self-review and concerns

The builder consumes only Task 2's validated data keys and emits no new
statistics. It keeps the comparison panel interval-and-point based, makes
terminal-rule direction explicit, and avoids a legend in favour of direct
method labels and an on-axis colour key. The complete repository suite is not
green because of the pre-existing numerical replay/calibration failures listed
above; no Figure 2 test failed.
