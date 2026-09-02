# Publication-first Repository Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the repository into publication, software, research, and archive domains while preserving every research artifact and every reproduction guarantee.

**Architecture:** Physical paths express audience and lifecycle. Publication-facing material is isolated from executable software, active research inputs/outputs, and historical artifacts; workspace exclusions hide local machinery without deleting it.

**Tech Stack:** Git, Python 3.11, pytest, Markdown, JSON workspace settings

---

### Task 1: Preserve loose source material

**Files:**
- Create: `archive/source-material/README.md`
- Move: `/Users/jy/BO/*.md`, `/Users/jy/BO/*.pdf`, `/Users/jy/BO/stage*.csv`

- [ ] Compare loose extraction files with repository copies using SHA-256.
- [ ] Move unique papers, drafts, records, and tables into purpose-labelled subdirectories.
- [ ] Move exact duplicates into `archive/source-material/duplicate-published-extraction/`.
- [ ] Record every source file and its interpretation in the archive README.

### Task 2: Move the active domains

**Files:**
- Move: `paper/` to `publication/manuscript/`
- Move: `paper-evidence/` to `publication/evidence/`
- Move: `src/`, `scripts/`, `tests/`, `configs/` to `software/`
- Move: `data/`, `results/` to `research/`
- Move: `docs/` to `archive/superseded-spade/docs/post-consolidation/`

- [ ] Create the four-domain hierarchy.
- [ ] Move directories without copying or deleting their contents.
- [ ] Create `research/results/figures/README.md` as the only active figure destination.
- [ ] Remove `.planning` only after confirming it is empty.

### Task 3: Repair paths and packaging

**Files:**
- Modify: `pyproject.toml`
- Modify: active Python, Markdown, YAML, and CSV files containing repository paths

- [ ] Point setuptools at `software/src`.
- [ ] Rewrite active paths from `paper`, `paper-evidence`, `src`, `scripts`, `tests`, `configs`, `data`, and `results` to their new locations.
- [ ] Update audit destinations and migration checks without rewriting archived historical prose.
- [ ] Confirm `pip install -e .` and `python -c 'import boec'` succeed.

### Task 4: Clean the explorer presentation

**Files:**
- Create: `/Users/jy/BO/.vscode/settings.json`

- [ ] Exclude Git internals, GitHub automation, virtual environments, caches, plugin state,
      workspace settings, Python bytecode, and package build metadata from Explorer.
- [ ] Keep publication, software, research, archive, and root metadata visible.

### Task 5: Verify and commit once

**Files:**
- Test: `software/tests/`

- [ ] Run `.venv/bin/pytest -q` and require all active tests to pass.
- [ ] Run the conclusion guard and require 12/12 values.
- [ ] Run publication-link and repository-audit validation.
- [ ] Run `git diff --check` and inspect the final root tree.
- [ ] Stage and create one final repository-layout commit.
