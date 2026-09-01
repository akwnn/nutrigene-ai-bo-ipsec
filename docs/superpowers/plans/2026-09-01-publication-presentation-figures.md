# SPADE publication and presentation figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign all five SPADE figures as a coherent color narrative with PLOS-oriented submission exports and larger presentation exports, without changing evidence.

**Architecture:** Keep the existing evidence/builders and deterministic exporter. Extend the venue preset with a presentation preset, centralize color/typography/layout settings, and make the EC gate figure use the same export contract. Generated artifacts remain derived from frozen results.

**Tech Stack:** Python 3.11, Matplotlib, Pillow, pytest.

## Global Constraints

- Preserve raw evidence, transformations, thresholds, exclusions, and missing/abstention semantics.
- Use color plus markers, hatching, direct labels, or panel separation.
- Use constrained layout and fixed physical dimensions; do not use accidental tight bounding-box cropping.
- Export PDF/SVG plus RGB PNG/TIFF, alt text, captions, long descriptions, data, and provenance.
- Keep PLOS submission assets at 300–600 dpi and under 10 MB per figure.

### Task 1: Shared venue and style contract

**Files:**
- Modify: `src/boec/paper_figures/style.py`
- Modify: `src/boec/paper_figures/paper.mplstyle`
- Test: `tests/test_paper_figure_layout.py`

- [ ] Add a `presentation` venue preset with a larger canvas and typography while retaining the existing `portable` and `plos` presets.
- [ ] Add explicit export defaults (`savefig.bbox: None`, opaque white background, Type 42 PDF fonts) to the style file.
- [ ] Extend layout tests to assert both presets have fixed positive physical dimensions and approved font resolution.
- [ ] Run `MPLCONFIGDIR=/tmp/mpl-cache PYTHONPATH=src .venv/bin/pytest -q tests/test_paper_figure_layout.py`.

### Task 2: Regenerate all figure builders under the shared contract

**Files:**
- Modify: `src/boec/paper_figures/figure1.py`
- Modify: `src/boec/paper_figures/figure2.py`
- Modify: `src/boec/paper_figures/figure3.py`
- Modify: `src/boec/paper_figures/figure4.py`

- [ ] Preserve each figure's estimand and uncertainty semantics while applying shared preset sizing and redundant color encodings.
- [ ] Keep explanatory content in panel annotations/captions, with no unsupported ranking language.
- [ ] Run the figure tests before exporting.

### Task 3: Make EC gate export part of the complete figure workflow

**Files:**
- Modify: `scripts/make_ec_gate_figure.py`
- Modify: `scripts/make_paper_figures.py`
- Create: `tests/test_ec_gate_figure.py`

- [ ] Expose a callable builder accepting an input path, output directory, and preset dimensions.
- [ ] Generate manuscript and presentation variants from the identical source JSON and write exact aggregation provenance.
- [ ] Add tests for source-row count, family metrics, RGB output, and explicit gate annotations.

### Task 4: Build, inspect, and validate deliverables

**Files:**
- Generated: `results/paper-figures/portable/*`, `results/paper-figures/presentation/*`

- [ ] Regenerate all five figures for both presets.
- [ ] Generate color, grayscale, and deuteranopia contact sheets.
- [ ] Inspect rendered figures for clipping, readable labels, and honest failure display.
- [ ] Run the complete figure/EC test suite and metadata checks.
- [ ] Rebuild `manuscript/SPADE-PLOS-ONE.docx`.

### Task 5: Review and push safely

- [ ] Review `git diff --check`, `git status`, and the complete diff.
- [ ] Attempt a focused commit for the redesign; if linked-worktree permissions prevent commit/push, report the exact blocker without rewriting unrelated changes.
