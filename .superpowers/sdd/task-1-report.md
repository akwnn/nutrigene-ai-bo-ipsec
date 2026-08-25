# Task 1 report

## Implementation summary

Established the publication-figure foundation under `boec.paper_figures`:

- Added immutable `FigureBundle`, strict top-level-object JSON loading, required-key validation, prohibited-content checks, and streaming SHA-256 file hashing.
- Added method-family visual encodings, physical venue presets, axis styling, and validated lowercase panel labels.
- Added the committed `paper.mplstyle` and setuptools package-data configuration.
- Added focused tests covering method palette redundancy, physical widths, panel labels, strict JSON loading, and figure bundle metadata.

## RED/GREEN TDD evidence

RED:

```text
.venv/bin/pytest tests/test_paper_figure_core.py -v -x
ModuleNotFoundError: No module named 'boec.paper_figures'
```

GREEN:

```text
.venv/bin/pytest tests/test_paper_figure_core.py -v
7 passed in 15.37s
```

The system `pytest` command was unavailable, so the repository's `.venv/bin/pytest` was used.

## Test commands and results

- `.venv/bin/pytest tests/test_paper_figure_core.py -v`: **7 passed**.
- `.venv/bin/pytest -q`: **1647 passed, 2 skipped, 8 failed** in 5:02. The failures are in pre-existing calibration/replay and exact-reproduction gates (`tests/test_calibration.py`, `test_d23_doe_subspace.py`, `test_p4_coord.py`, `test_q59_map_rescore.py`, `test_replay.py`, and `test_spread_gp.py`), unrelated to this package.
- `git diff --check`: passed.

## Files changed

- `pyproject.toml`
- `src/boec/paper_figures/__init__.py`
- `src/boec/paper_figures/core.py`
- `src/boec/paper_figures/style.py`
- `src/boec/paper_figures/paper.mplstyle`
- `tests/test_paper_figure_core.py`

## Self-review

Reviewed the diff for scope, exact brief values, import paths, immutable dataclass declarations, strict JSON error behavior, and package-data configuration. `git diff --check` reported no whitespace errors. No later figure builders or unrelated files were modified.

## Concerns

The full suite has eight unrelated baseline failures involving numerical reproducibility and calibration gates. Focused Task 1 tests are green. Fontconfig emitted a non-writable-cache warning during matplotlib collection, but did not affect the focused test result.

## Review fix: venue text-size enforcement

Added optional `VenuePreset` (or preset name) arguments to `apply_axis_style` and `panel_label`. Axis labels, tick labels, titles, and legend text now use the selected preset's `body_pt`; panel labels use the selected preset's `panel_pt` while retaining lowercase validation and bold weight. Added contract and rendering regressions for the portable/RSC/Nature 7–8 pt body and 8 pt panel-label requirements.

### RED/GREEN evidence

RED:

```text
.venv/bin/pytest tests/test_paper_figure_core.py -v
4 failed, 6 passed in 15.47s
TypeError: panel_label() got an unexpected keyword argument 'preset'
TypeError: apply_axis_style() got an unexpected keyword argument 'preset'
```

GREEN:

```text
.venv/bin/pytest tests/test_paper_figure_core.py -v
11 passed in 15.42s
```

The focused test command completed without warnings or errors in the final run.
