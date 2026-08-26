# Publication Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce reproducible publication tables for the completed final-SPADE study, verify every cited source used by the paper, capture author declarations without inference, and validate a clean submission commit.

**Architecture:** Add one focused table builder that reads only the tracked final-SPADE raw and adjudication artefacts, emits machine-readable JSON plus journal-ready CSV and Markdown, and refuses pooling across registered cells. Extend the existing source-verification record with primary-PDF checks. Keep human authorship declarations outside computed evidence and run the existing fail-closed release validator after all publication artefacts are committed.

**Tech Stack:** Python 3.11, standard-library JSON/CSV, NumPy 2.4.6, pytest 9.1.1, existing final-SPADE JSON artefacts, Git/SHA-256 provenance.

## Global Constraints

- Use only the completed `spade-final-2026-08-23` evidence; do not include unopened joint-protocol outcomes.
- Preserve the registered 48-well budgets, Rule-P primary terminal decision, condition-specific primary gamma, and n=25 instance-level aggregation.
- Never pool distinct tau, gamma, alpha, condition, or evidence bodies.
- Report calibration and refinement together; AUC cannot substitute for calibration.
- Treat `spade_cf_m0` versus `spade_random_plate2` as the equal-well targeting contrast and `spade_plate1_only` as a budget-short reference.
- Do not infer authorship, affiliations, funding, or conflicts from repository activity.
- Do not claim wet-lab, biological-efficacy, GMP, manufacturing, or universal method validation.

---

### Task 1: Publication table evidence model

**Files:**
- Create: `scripts/make_publication_tables.py`
- Create: `tests/test_publication_tables.py`

**Interfaces:**
- Consumes: `results/final-spade-c1.json` through `results/final-spade-s3.json`, `results/final-spade-regret-pareto.json`, and `results/final-spade-kill-ledger.json`.
- Produces: `build_tables(results_dir: Path) -> dict[str, object]` containing `prospective_calibration`, `spade_comparison`, and `kill_ledger` tables with source provenance.

- [ ] **Step 1: Write failing schema and anti-pooling tests**

  Assert that target calibration uses exactly `hill-d6-s0.1`, `tau_frac=0.25`, `gamma=0.95`, `alpha=0.95`; campaign seeds are averaged within each of 25 landscape instances; every row reports Brier, Murphy calibration, Murphy refinement, AUC, symmetric-difference error, Rule-P regret, wells, and rounds; and duplicated certificate alpha rows cannot inflate the denominator.

- [ ] **Step 2: Run the focused test and confirm RED**

  Run: `.venv/bin/python -m pytest tests/test_publication_tables.py -q`

  Expected: collection fails because `scripts.make_publication_tables` does not exist.

- [ ] **Step 3: Implement strict input loading and aggregation**

  Load top-level JSON objects, validate study IDs and required columns, select one registered cell, deduplicate by `(arm, instance_seed, campaign_seed)`, average campaign seeds within instance, and reject conflicting duplicate values.

- [ ] **Step 4: Implement the three table payloads**

  `prospective_calibration` ranks all available target-condition arms by Brier while preserving calibration and refinement columns. `spade_comparison` selects the six paper-facing arms (`doe`, `sobol`, `qlogei`, `qlognei`, `spade_cf_m0`, `spade_random_plate2`) from the committed Pareto artefact across all seven conditions. `kill_ledger` preserves KF-1 through KF-10 status, effect, interval, p-values, SESOI, denominator, and bounded interpretation.

- [ ] **Step 5: Run focused tests and confirm GREEN**

  Run: `.venv/bin/python -m pytest tests/test_publication_tables.py tests/test_final_spade_statistics.py -q`

  Expected: all tests pass.

### Task 2: Journal-ready table exports

**Files:**
- Modify: `scripts/make_publication_tables.py`
- Modify: `tests/test_publication_tables.py`
- Create: `results/publication-tables/publication-tables.json`
- Create: `results/publication-tables/table-spade-prospective-calibration.csv`
- Create: `results/publication-tables/table-spade-prospective-calibration.md`
- Create: `results/publication-tables/table-spade-comparison.csv`
- Create: `results/publication-tables/table-spade-comparison.md`
- Create: `results/publication-tables/table-spade-kill-ledger.csv`
- Create: `results/publication-tables/table-spade-kill-ledger.md`

**Interfaces:**
- Consumes: `build_tables(results_dir)` from Task 1.
- Produces: `write_tables(results_dir: Path, output_dir: Path) -> tuple[Path, ...]` and deterministic SHA-256-addressed publication artefacts.

- [ ] **Step 1: Write failing deterministic-export tests**

  Assert exact filenames, stable ordering, explicit units and lower-is-better notes, fixed numeric formatting, no empty denominator, byte-identical repeated generation, and source hashes in the JSON manifest.

- [ ] **Step 2: Run the focused test and confirm RED**

  Run: `.venv/bin/python -m pytest tests/test_publication_tables.py -q`

  Expected: export tests fail because `write_tables` is absent.

- [ ] **Step 3: Implement CSV, Markdown, JSON, and manifest export**

  Use RFC-compatible CSV, CommonMark tables, canonical sorted JSON, atomic replacement, and SHA-256 hashes of every source and output. Refuse a dirty or missing source payload rather than emitting partial tables.

- [ ] **Step 4: Generate committed publication tables**

  Run: `.venv/bin/python scripts/make_publication_tables.py --results-dir results --output-dir results/publication-tables`

  Expected: seven output files are written and the second run is byte-identical.

- [ ] **Step 5: Reconcile values with existing figures and prose**

  Run: `.venv/bin/python -m pytest tests/test_publication_tables.py tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py -q`

  Expected: all tests pass and the target SPADE values match the committed Figure 3/4 evidence.

### Task 3: Primary-PDF citation verification

**Files:**
- Modify: `docs/source_verification.md`
- Modify: `docs/RESEARCH-SUMMARY.md` only where a citation detail or characterization is contradicted by a primary source.

**Interfaces:**
- Consumes: the 13 references in `docs/RESEARCH-SUMMARY.md` and the claims attached to them.
- Produces: a source-by-source verification record containing DOI or canonical identifier, primary-PDF location, claims checked, verdict, and required manuscript correction.

- [ ] **Step 1: Inventory cited claims and canonical identifiers**

  Record the manuscript claims attached to Box–Wilson, Jones–Schonlau–Welch, Frazier, Hall–Lin–Ogle, Rummukainen, Lapierre, Ndahiro, Narayanan, Gisperg, Močkus, Box–Draper, and Myers–Montgomery–Anderson-Cook. Distinguish article claims from textbook background.

- [ ] **Step 2: Retrieve or open primary PDFs**

  Use publisher/DOI pages, author manuscripts, or official repositories. Do not treat search snippets, review articles, or secondary summaries as verification. Record inaccessible books as bibliographic-only checks rather than pretending to have read a PDF.

- [ ] **Step 3: Verify claim language and bibliographic metadata**

  Check experiment counts, terminal selection rules, comparator definitions, biological system, publication year, volume/pages/article number, and DOI. Keep quotations within copyright limits and paraphrase findings.

- [ ] **Step 4: Correct contradicted manuscript statements**

  Apply only evidence-required corrections. Preserve explicit uncertainty when a primary PDF does not report the needed quantity.

- [ ] **Step 5: Run citation consistency checks**

  Run: `rg -n 'Rummukainen|Lapierre|Ndahiro|Narayanan|Hall|Gisperg|Box|Wilson|Jones|Frazier|Močkus|Myers' docs/RESEARCH-SUMMARY.md docs/source_verification.md`

  Expected: every in-text named source has a verified reference entry and no unresolved citation placeholders remain.

### Task 4: Human publication declarations

**Files:**
- Modify: `docs/RESEARCH-SUMMARY.md` end matter only after the user supplies the declarations.

**Interfaces:**
- Consumes: explicit author-provided order, affiliations, ORCIDs, corresponding-author designation, CRediT roles, funding, and conflicts.
- Produces: journal-ready Authors/Affiliations, Author Contributions, Funding, and Competing Interests sections.

- [ ] **Step 1: Confirm that repository metadata is insufficient**

  Record in the work log—not the manuscript—that no author list or declarations exist and no inference is permitted.

- [ ] **Step 2: Obtain explicit declarations from the user or corresponding author**

  Required fields: ordered full names; institutional affiliations; ORCID if available; corresponding author; CRediT roles; funding agency and grant number or “no specific funding”; conflicts or “none declared.”

- [ ] **Step 3: Insert declarations verbatim and check internal consistency**

  Ensure every author has at least one contribution, every named funding source appears in Funding, and the corresponding author is identified consistently.

### Task 5: Full PLOS ONE manuscript

**Files:**
- Create: `manuscript/SPADE-PLOS-ONE.md`
- Create: `manuscript/SPADE-PLOS-ONE.docx`
- Create: `scripts/build_manuscript_docx.py`

**Interfaces:**
- Consumes: the verified evidence in `docs/RESEARCH-SUMMARY.md`, the publication tables from Tasks 1–2, the four tracked editorial figures, and the citation corrections from Task 3.
- Produces: a complete PLOS ONE research manuscript in Markdown and editable DOCX, with explicit placeholders only for human-supplied author declarations.

- [ ] **Step 1: Write the evidence-locked Markdown manuscript**

  Use a SPADE-bearing title and the standard PLOS ONE research structure: Abstract, Introduction, Materials and Methods, Results, Discussion, Conclusions, Data Availability, Code Availability, Funding, Competing Interests, Author Contributions, Acknowledgements, References, and Supporting Information. Integrate the completed seven-condition final-SPADE study and keep the unopened joint protocol in future work.

- [ ] **Step 2: Check every numerical statement against a tracked artefact**

  Search each main-text number in the publication-table JSON, final-SPADE adjudication artefacts, or existing evidence JSON. Remove unsupported precision and preserve null/failure language.

- [ ] **Step 3: Build the editable DOCX**

  Use the bundled document runtime and the formal scientific-manuscript design tokens. Insert the four tracked figures with captions, add explicit table geometry, continuous line numbers, page numbers, and PLOS-style section hierarchy.

- [ ] **Step 4: Render and visually inspect every DOCX page**

  Run the packaged `render_docx.py`, inspect every generated PNG at full resolution, and revise clipping, overflow, table wrapping, figure scaling, orphan headings, or excessive gaps until clean.

- [ ] **Step 5: Run manuscript integrity checks**

  Confirm that SPADE appears in the title, PLOS ONE does not appear in the scientific title, the joint protocol carries no outcome claim, all figures/tables are cited in order, references resolve, and only author-controlled metadata remains bracketed.

### Task 6: Submission commit and final validation

**Files:**
- Modify: `.planning/STATE.md` only to record completed publication-table and citation-audit evidence.

**Interfaces:**
- Consumes: all artefacts from Tasks 1–4.
- Produces: a clean Git commit that passes table tests, paper-figure tests, final-SPADE release validation, and the repository test suite with pre-existing failures explicitly classified.

- [ ] **Step 1: Run focused publication checks**

  Run: `.venv/bin/python -m pytest tests/test_publication_tables.py tests/test_paper_figure_core.py tests/test_paper_figure_evidence.py tests/test_paper_figure_builders.py tests/test_paper_figure_export.py tests/test_final_spade_reproducibility.py -q`

  Expected: all focused tests pass.

- [ ] **Step 2: Run the fail-closed final-SPADE validator**

  Run: `.venv/bin/python scripts/validate_final_spade_release.py`

  Expected: 9/9 checks pass with zero violations.

- [ ] **Step 3: Run the complete test suite**

  Run: `.venv/bin/python -m pytest -q`

  Expected: no new failure relative to the recorded baseline; each historical failure is matched to `.planning/STATE.md` and `.planning/codebase/CONCERNS.md`.

- [ ] **Step 4: Commit the submission evidence**

  Stage only files produced or deliberately corrected by this plan. Commit with a publication-scoped message and verify `git status --short` is empty.

- [ ] **Step 5: Re-run release validation on the commit**

  Run: `git status --short` followed by `.venv/bin/python scripts/validate_final_spade_release.py`

  Expected: clean worktree and 9/9 checks pass against the committed state.
