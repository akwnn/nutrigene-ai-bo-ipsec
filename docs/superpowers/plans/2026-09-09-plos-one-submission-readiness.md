# PLOS ONE Submission Readiness Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining gaps between the current manuscript and a submittable PLOS ONE package: resolve or formally scope the eight reproducibility failures, capture author-supplied submission fields, and prevent stale figures from reaching the rendered paper.

**Architecture:** The tracked Markdown at `manuscript/SPADE-PLOS-ONE.md` stays canonical. Both Word copies and all four figures are regenerated derivatives. No experimental campaign is rerun by this plan.

**Tech Stack:** Python 3.11 (`.venv`), pytest, matplotlib, python-docx, native Word OMML equations, LibreOffice-based renderer

## Global Constraints

- Target journal is PLOS ONE.
- Do not pool the retrospective, 99,601-record prospective, and 2,750-row joint-protocol evidence bodies.
- Do not run power planning and do not open the lockbox. It remains `FROZEN_UNOPENED`.
- Do not claim biological validation, universal certificate validity, or elapsed-time savings.
- Do not invent author names, affiliations, funding, competing interests, licence terms, or a DOI. These are author-supplied and must stay marked until provided.
- Do not weaken or delete a failing reproducibility test to make the suite green. Fix the cause or scope the claim.
- Preserve all unrelated worktree changes. Nothing in this plan is committed yet.

---

## Current verified state (2026-09-09, do not redo)

> **Concurrency warning:** this state was verified at ~19:00 UTC on 2026-09-09. A Codex session resumed on this repository at 19:09 UTC and began editing `src/boec/paper_figures/figure4.py` again, including a further revision of the panel-B title. Re-read the working tree before trusting any file detail below, and do not run two agents against this repo at once.

Confirmed by execution, not assumption:

- Publication-focused tests pass: **62 passed** across `tests/test_manuscript_docx.py`, `tests/test_paper_figure_builders.py`, `tests/test_paper_figure_layout.py`, `tests/test_publication_bundle.py`.
- Full suite: **2,432 passed, 8 failed** in 940s. The eight failures are itemised in Task 1.
- Fig 4 label-clearance defect is fixed. The two-line "no non-empty certificate" annotation on the last row of panel B crossed the bottom spine in the PLOS preset only. Fixed in `src/boec/paper_figures/figure4.py` by reserving a full row of space when the final row is a declined row.
- Both figure presets regenerated from current source; `manuscript/SPADE-PLOS-ONE.docx` rebuilt from current Markdown; `manuscript/SPADE-PLOS-ONE-submission.docx` created (4 captions, 0 embedded drawings).
- All 34 rendered pages scanned: no clipping, no margin intrusion, minimum body-to-footer clearance ~96px at 100dpi (~1in). The even-page footer overlap seen on 2026-09-07 is not present.
- All four figure pages inspected visually: no overlapping or clipped labels.
- Joint-protocol numbers reconciled against `results/spade-development-analysis.json`: 9 candidates, 11 arms, 50 campaigns/family, 5 families = 2,750 rows; all five leave-one-family-out folds `NO_SELECTION`; every candidate below the 0.90 containment floor in at least one family; lockbox unopened. Every range printed in Table 4 matches the artifact.
- Abstract and Table 3 values reconciled against `results/publication-tables/table-spade-comparison.md`: map error 0.1804 vs 0.2131 (15.3% relative), point-regret gap 0.00937, terminal-rule effects −0.0543 and +0.1035.
- `scripts/make_publication_tables.py` is idempotent against the current artifacts: rerunning it produces no diff.

**Near-miss worth knowing:** before this pass the manuscript was embedding PLOS figures last built on 2026-09-08. The corrected panel-B labels ("posterior self-consistency", not "cross-fit containment") existed in the figure source and the caption but had never been rendered into the paper, so the built manuscript contradicted its own caption. Task 3 exists to make that failure mode impossible rather than merely fixed.

---

### Task 1: Triage the eight reproducibility failures

**Files:**
- Investigate: `tests/test_replay.py`, `tests/test_calibration.py`, `tests/test_d23_doe_subspace.py`, `tests/test_p4_coord.py`, `tests/test_q59_map_rescore.py`, `tests/test_spread_gp.py`
- Likely modify: `manuscript/SPADE-PLOS-ONE.md` (limitations), `docs/source_verification.md`

**Interfaces:**
- Consumes: committed reference columns and the current `.venv` environment
- Produces: either restored reproduction, or an accurate written scope for what is and is not bitwise reproducible

These eight are **not one problem**. They separate into three classes with very different severity. Treat them separately and do not describe them in the paper with a single blanket sentence.

**Class A — sub-microscopic numerical drift (4 tests).** Deltas are 1e-7 or smaller:

| Test | Observed delta |
|---|---|
| `test_d23_doe_subspace.py::test_full_space_rule_p_reproduces_fix1` | 3.878e-07 |
| `test_p4_coord.py::test_k6_scorer_reproduces_a_committed_lhs_row_bitwise` | ~2e-16 (last-bit: `...4847` vs `...4849`) |
| `test_q59_map_rescore.py::test_the_edit_is_additive_and_reproduces_the_committed_columns` | 3.173e-08 |
| `test_spread_gp.py::test_the_extracted_arm_reproduces_the_committed_q52_rows_exactly` | 3.123e-07 |

- [ ] **Step 1: Test the environment-drift hypothesis before accepting it**

The working hypothesis is that these are BLAS/PyTorch/platform nondeterminism rather than logic changes, but that is **unconfirmed** — do not write it into the paper as fact until checked. Compare the installed torch/numpy/scipy versions against the versions recorded in the provenance manifest for the commit that produced the committed columns. If they differ, that supports drift. If they match, the cause is a code change and this is no longer Class A.

- [ ] **Step 2: Decide bitwise vs tolerance, and say which in the paper**

If drift is confirmed, the honest resolution is that these columns reproduce to ~1e-6 on a different toolchain, not bitwise. Either re-pin the environment so the assertions hold, or change the assertions to a documented tolerance **and** state that tolerance in the reproducibility section. Do not silently loosen a tolerance without disclosing it.

**Class B — genuine divergence (2 tests). Highest priority in this plan.**

| Test | Recomputed | Committed |
|---|---|---|
| `test_replay.py::test_family_qlogei_reproduces_on_every_family_and_at_d8` (ackley d=6 seed=0) | 0.9140845131035267 | 0.5928006956256192 |
| `test_replay.py::test_family_qlognei_reproduces_the_q59_hartmann_column` (hartmann6 seed=0) | 0.11127587899761282 | 0.1699699208688239 |

`test_replay.py::test_family_qlogei_reproduces_the_committed_q42_column_exactly` fails in the same family.

- [ ] **Step 3: Determine whether these divergences touch any published number**

These are not rounding. A regret of 0.914 against a committed 0.593 is a different result. Establish whether the affected replay columns feed anything reported in the manuscript — in particular the retrospective terminal-rule evidence body and the Fig 2 values (−0.0543 / +0.1035). Trace the data path rather than assuming isolation.

- [ ] **Step 4: If any published number is affected, stop and report before editing**

If a reported value depends on a column that no longer reproduces, that is a correctness issue outranking every other task here. Surface it to the user with the specific numbers before changing manuscript text. Do not quietly re-derive a published value from the new output.

- [ ] **Step 5: If no published number is affected, scope the limitation precisely**

Say which arms and families fail to replay and by how much, rather than the current vague framing. The reader should be able to tell that the prospective benchmark and the joint-protocol study are unaffected, if that is what the trace shows.

**Class C — runner crash (1 test).**

- [ ] **Step 6: Diagnose `test_calibration.py::test_the_checkpoint_write_path_actually_runs`**

It fails with `AssertionError: runner exited 1` at `tests/test_calibration.py:662` — the subprocess is dying, so the assertion message hides the real error. Capture the runner's stderr and fix the underlying cause. This is a code-health failure, not a claim-validity failure, but it should not ship failing without explanation.

- [ ] **Step 7: Re-run the full suite and record the exact outcome**

Run `.venv/bin/python -m pytest -q` and record the true pass/fail counts. Do not describe the suite as clean unless it is.

### Task 2: Capture author-supplied submission fields

**Files:**
- Modify: `manuscript/SPADE-PLOS-ONE.md`

**Interfaces:**
- Consumes: information only the author can provide
- Produces: a manuscript with no unresolved placeholder text

This task is **blocked on the user** and cannot be completed by inference. It was asked once on 2026-09-07 and not answered.

- [ ] **Step 1: Request the missing fields in one message**

Author names in order, affiliations, corresponding-author email, funding statement, competing-interest declaration, and the code-owner-approved licence.

- [ ] **Step 2: Fill the fields and remove only the placeholders that are genuinely resolved**

`manuscript/SPADE-PLOS-ONE.md` currently carries a literal `[REPOSITORY DOI REQUIRED BEFORE SUBMISSION]` marker in the data-availability statement. Leave it until a real DOI exists.

- [ ] **Step 3: Deposit the release and record the DOI**

The archival deposit must exist before the data-availability statement can be finalised. Update the statement with the DOI and reviewer-access URL, then confirm no placeholder text remains anywhere in the manuscript.

### Task 3: Prevent stale figures from reaching the manuscript

**Files:**
- Modify: `tests/test_publication_bundle.py` or `tests/test_manuscript_docx.py`
- Reference: `scripts/make_paper_figures.py`, `scripts/build_manuscript_docx.py`

**Interfaces:**
- Consumes: figure source modules and built figure outputs
- Produces: a test that fails when the embedded figures are older than the code that draws them

The manuscript embeds `results/paper-figures/plos/fig{1..4}.png`. Nothing currently detects that those files are out of date, which is how a corrected label sat unrendered for a day.

- [ ] **Step 1: Write the failing test first**

Assert that each embedded PLOS figure is newer than its `src/boec/paper_figures/figure*.py` source, or compare a recorded source hash in `build-manifest.json` against the current source. Confirm the test fails against a deliberately stale figure before implementing.

- [ ] **Step 2: Make it pass and document the correct rebuild command**

Note the trap explicitly: `make_paper_figures.py` appends the preset name to `--output-dir`, so the correct invocation is `--preset plos --output-dir results/paper-figures`, **not** `--output-dir results/paper-figures/plos`. The wrong form silently writes to a nested `plos/plos/` directory and reports success while changing nothing.

### Task 4: Commit the working tree

**Files:**
- All currently modified and untracked publication files

**Interfaces:**
- Consumes: the verified working tree
- Produces: reviewable atomic commits

Everything described in this plan is uncommitted. The tree mixes manuscript revisions, figure-code fixes, new modules, and new tests.

- [ ] **Step 1: Group the changes into atomic commits**

Suggested separation: figure-layout fix and its regenerated outputs; manuscript text revision and rebuilt Word copies; new analysis modules and their tests; planning/state updates. Do not squash unrelated work into one commit.

- [ ] **Step 2: Confirm the untracked publication artifacts are intended for tracking**

`.gitignore` was amended with `!results/paper-figures/` and `!results/paper-figures/**` so publication derivatives travel with the manuscript. `results/paper-figures/plos/` is therefore un-ignored but still untracked — add it deliberately.

### Task 5: Final rebuild and verification

**Files:**
- Verify: `manuscript/SPADE-PLOS-ONE.md`, `manuscript/SPADE-PLOS-ONE.docx`, `manuscript/SPADE-PLOS-ONE-submission.docx`

**Interfaces:**
- Consumes: the completed tasks above
- Produces: evidence that the submission package is internally consistent

Run this after any change to figures, Markdown, or the builder.

- [ ] **Step 1: Regenerate derivatives in dependency order**

```bash
.venv/bin/python scripts/make_publication_tables.py
.venv/bin/python scripts/make_paper_figures.py --preset portable
.venv/bin/python scripts/make_paper_figures.py --preset plos --output-dir results/paper-figures
.venv/bin/python scripts/build_manuscript_docx.py
.venv/bin/python scripts/build_manuscript_docx.py --submission --output manuscript/SPADE-PLOS-ONE-submission.docx
```

- [ ] **Step 2: Run the publication test set**

```bash
.venv/bin/python -m pytest -q tests/test_manuscript_docx.py tests/test_paper_figure_builders.py \
  tests/test_paper_figure_layout.py tests/test_publication_bundle.py
```

Expect 62 passed plus whatever Task 3 adds.

- [ ] **Step 3: Render and inspect every page**

Convert the DOCX to PDF and rasterise one image per page, then check every page at full resolution for clipping, label overlap, table overflow, broken equations, and body text intruding into the footer. A programmatic ink-bounds scan is a useful first pass but does not replace looking at the figure pages.

- [ ] **Step 4: Confirm figure labels match the manuscript text**

Re-check Fig 4 panel B in the **rendered PDF**, not just the source. Its axis label and title must describe a posterior/model check. If the rendered panel still reads "Cross-fit containment − nominal", the embedded figure is stale and the paper contradicts its own caption. Compare the rendered wording against the Fig 4 caption in `manuscript/SPADE-PLOS-ONE.md` rather than against a fixed string in this plan — the exact panel wording is being revised and this document may lag it.

- [ ] **Step 5: Report honestly**

State the true test counts, name anything left unresolved, and list the author-owned fields still outstanding. Do not report the package as submission-ready while Task 1 or Task 2 is open.
