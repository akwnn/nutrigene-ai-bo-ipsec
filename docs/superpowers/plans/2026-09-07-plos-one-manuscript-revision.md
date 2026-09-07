# PLOS ONE Manuscript Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a synchronized, verified PLOS ONE manuscript that presents the supported SPADE results and the joint-protocol `NO_SELECTION` outcome as separate evidence bodies.

**Architecture:** Treat the tracked Markdown as the canonical manuscript and use the existing Python builder to regenerate the DOCX. Make only evidence-backed editorial changes, preserve the user's existing DOCX-generation improvements, and validate both text and rendered layout.

**Tech Stack:** Markdown, Python, python-docx, native Word OMML equations, pytest, LibreOffice-based DOCX renderer

## Global Constraints

- Target journal is PLOS ONE.
- Do not pool the retrospective, 99,601-record prospective, or 2,750-row joint-protocol evidence bodies.
- Report `NO_SELECTION` from the authenticated artifacts at commit `502ea39`.
- Do not run power planning or open the lockbox.
- Do not claim biological validation, universal certificate validity, or elapsed-time savings.
- Preserve all unrelated worktree changes.

---

### Task 1: Revise the canonical manuscript

**Files:**
- Modify: `manuscript/SPADE-PLOS-ONE.md`

**Interfaces:**
- Consumes: `.planning/STATE.md`, `docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md`, and the selection artifacts stored at commit `502ea39`
- Produces: canonical PLOS ONE manuscript text for DOCX generation

- [ ] **Step 1: Rewrite the abstract and introduction framing**

Lead with the decision-object benchmark, retain the target-regime estimates, and state the failed joint-protocol selection without implying that it invalidates the completed prospective study.

- [ ] **Step 2: Add the joint-protocol methods**

Describe nine SPADE candidates, three opening sizes, three policy families, 50 matched campaigns across five development families, two comparators, the 0.90 empirical-containment gate, unanimous leave-one-family-out selection, and the preregistered stop before power or lockbox access.

- [ ] **Step 3: Add the joint-protocol result**

Report 2,750 campaign-arm rows, no survivor in any leave-one-family-out training fold, final status `NO_SELECTION`, and an unopened lockbox.

- [ ] **Step 4: Rewrite the discussion and conclusion**

Make the transferable contribution the separation of decision estimands and certificate properties. Keep SPADE's positive finding bounded to the target regime and treat the null mechanism and selection stop as results.

- [ ] **Step 5: Scan the complete manuscript**

Run `rg -n "not been run|universally validated|universal optimizer|lockbox outcomes" manuscript/SPADE-PLOS-ONE.md` and confirm that every match is accurate in context.

### Task 2: Synchronize and test the DOCX

**Files:**
- Modify: `manuscript/SPADE-PLOS-ONE.docx`
- Preserve: `scripts/build_manuscript_docx.py`
- Test: `tests/test_manuscript_docx.py`

**Interfaces:**
- Consumes: revised `manuscript/SPADE-PLOS-ONE.md`
- Produces: submission-ready Word manuscript with native equations and stable tables

- [ ] **Step 1: Run the manuscript DOCX tests**

Run `pytest -q tests/test_manuscript_docx.py` and require all tests to pass before generation.

- [ ] **Step 2: Regenerate the DOCX**

Run the bundled Python runtime against `scripts/build_manuscript_docx.py` with the canonical Markdown input and tracked DOCX output.

- [ ] **Step 3: Re-run the manuscript tests**

Run `pytest -q tests/test_manuscript_docx.py` and require all tests to pass after generation.

### Task 3: Verify content and layout

**Files:**
- Verify: `manuscript/SPADE-PLOS-ONE.md`
- Verify: `manuscript/SPADE-PLOS-ONE.docx`

**Interfaces:**
- Consumes: synchronized Markdown and DOCX outputs
- Produces: evidence that the manuscript is factually and visually ready for author-detail completion

- [ ] **Step 1: Verify the reported selection facts**

Compare every joint-protocol number and decision against `results/spade-selected-protocol.json` and `results/spade-development-analysis.json` at commit `502ea39`.

- [ ] **Step 2: Run prose and placeholder scans**

Confirm that no stale outcome claim remains and that only author-supplied submission fields and the repository DOI remain unresolved.

- [ ] **Step 3: Render the DOCX**

Use the bundled document renderer to create one PNG per page in a temporary QA directory.

- [ ] **Step 4: Inspect every rendered page**

Check all pages at full resolution for clipping, overlap, broken equations, table overflow, missing figures, and incorrect page breaks. Correct any defect and repeat the render once.

- [ ] **Step 5: Report the verified deliverables**

Return links to the Markdown and DOCX manuscripts and list only the remaining author-owned submission fields.
