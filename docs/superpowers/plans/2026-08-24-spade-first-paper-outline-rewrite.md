# SPADE-First Paper Outline Rewrite Implementation Plan

> **Historical completed plan.** Its boundary hold and missing-raw constraints were later
> resolved. See `docs/PROJECT-UNDERSTANDING-OUTLINE.md` for the corrected current blueprint.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing project-understanding document with a publication-grade, SPADE-first manuscript blueprint that a scientific writer can turn directly into the paper.

**Architecture:** One authoritative Markdown document will carry the complete scientific narrative, methods, results, figures, tables, limitations, citation purposes, and provenance. The prospective SPADE artefacts govern numerical claims; retrospective BO/RSM experiments provide motivation and supporting mechanism. The boundary-targeting result remains explicitly reserved and contributes no positive or negative claim.

**Tech Stack:** Markdown, Git, `rg`, `jq`, repository JSON result artefacts.

## Global Constraints

- Modify only `docs/PROJECT-UNDERSTANDING-OUTLINE.md` during the manuscript rewrite.
- Use complete professional prose; bullets are limited to genuinely tabular or checklist material.
- Use `$...$` for inline mathematics and `$$...$$` for display mathematics.
- Do not quote, interpret, graph, or adjudicate the current boundary-targeting comparison.
- Treat committed JSON decision artefacts as numerical authority over stale historical prose.
- Describe the reported 99,601-row prospective dataset while disclosing that ignored raw condition files prevent fresh-clone release validation.
- Keep point-optimization and prospective design-space studies separate before synthesizing them.

---

### Task 1: Replace the document architecture and scientific narrative

**Files:**
- Modify: `docs/PROJECT-UNDERSTANDING-OUTLINE.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-08-24-spade-first-paper-outline-design.md`, `docs/SPADE-FINAL-SPEC.md`, `docs/FINDINGS-SPADE-FINAL.md`, `docs/SPADE-FOR-RESEARCHERS.md`.
- Produces: a self-contained SPADE-first manuscript blueprint with title, abstract, significance, Introduction, Methods, Results, Discussion, and conclusion.

- [ ] **Step 1: Replace the old BO-first framing**

Write a new opening in which the central problem is estimation of an acceptable formulation region rather than discovery of one best formulation. Present terminal-rule instability as the motivation for changing the scientific deliverable.

- [ ] **Step 2: Write the full Methods blueprint**

Describe the synthetic Hill landscapes, external benchmark families, observation model, experimental budgets, SPADE plates, comparators, terminal rules, map and certificate estimands, cross-fitting, prospective registration, inference, multiplicity, and feasibility ceiling. Define every equation in adjacent prose.

- [ ] **Step 3: Write the Results blueprint**

Organize results by scientific claim: point-versus-region reordering; target-condition SPADE performance; completed allocation ablations; cross-family robustness; calibration and refinement; certificate scope; and the registered claim ledger. Mark boundary targeting as reserved without quoting current results.

- [ ] **Step 4: Write Discussion and conclusions**

Explain the laboratory meaning, contribution, constraints, wet-lab validation requirements, and safe claims. Distinguish a useful design-space map from a calibrated guarantee.

- [ ] **Step 5: Review the narrative architecture**

Run:

```bash
rg -n '^#|^##|^###' docs/PROJECT-UNDERSTANDING-OUTLINE.md
```

Expected: a coherent manuscript sequence led by SPADE, with BO/RSM appearing as motivation and supporting evidence.

### Task 2: Add publication-ready figures, tables, citations, and provenance

**Files:**
- Modify: `docs/PROJECT-UNDERSTANDING-OUTLINE.md`

**Interfaces:**
- Consumes: `results/final-spade-regret-pareto.json`, `results/final-spade-kill-ledger.json`, `results/final-spade-certificate.json`, `results/final-spade-manifest.json`, and retrospective committed result artefacts cited by the existing outline.
- Produces: exact central tables, four main figure specifications and captions, supplementary display plan, citation-purpose map, artifact map, reviewer-risk responses, and submission checklist.

- [ ] **Step 1: Add central numerical tables**

Include the target Hill comparison, cross-family point-versus-map pattern, certificate scope, and completed claim-evidence matrix. Report terminal rule, condition, denominator, direction, and practical threshold wherever relevant.

- [ ] **Step 2: Write four main figure specifications**

For every figure provide scientific question, panels, visual encoding, statistical annotations, draft caption, supported conclusion, and prohibited interpretation. Exclude the boundary-targeting comparison from all displays.

- [ ] **Step 3: Write the citation-purpose map**

Explain what each cited paper contributes and what it cannot substantiate. Keep Hall et al. as biological inspiration rather than a source of fitted synthetic parameters.

- [ ] **Step 4: Add provenance and reproducibility disclosure**

Identify the decisive artefacts, stale documents that must not be quoted directly, the 99,601-row arithmetic, passing targeted tests, and the missing ignored raw files that block a fresh-clone release audit.

### Task 3: Verify claim safety, mathematics, and source consistency

**Files:**
- Verify: `docs/PROJECT-UNDERSTANDING-OUTLINE.md`

**Interfaces:**
- Consumes: completed manuscript blueprint and authoritative JSON artefacts.
- Produces: a structurally clean and internally consistent final document.

- [ ] **Step 1: Verify the boundary reservation**

Run:

```bash
rg -n 'boundary.target|targeted.*random|KF-3|0\.00188|0\.410' docs/PROJECT-UNDERSTANDING-OUTLINE.md
```

Expected: only explicit statements that the analysis is reserved; none of the current effect, interval, p-value, or verdict appears.

- [ ] **Step 2: Verify central values against JSON**

Run:

```bash
jq -r '.rows[] | select(.condition=="hill-d6-s0.1") | [.arm,.regret.P,.symmetric_difference,.rounds,.wells] | @tsv' results/final-spade-regret-pareto.json
jq -r '.kills | to_entries[] | [.key,.value.status,.value.effect] | @tsv' results/final-spade-kill-ledger.json
```

Expected: manuscript values match the committed artefacts, except that the reserved boundary-targeting entry is not reproduced in the manuscript.

- [ ] **Step 3: Verify Markdown and placeholders**

Run:

```bash
git diff --check
rg -n 'TBD|TODO|FIXME|&(#x20|nbsp);|\\\[|\\\]' docs/PROJECT-UNDERSTANDING-OUTLINE.md
```

Expected: `git diff --check` succeeds and the placeholder/formatting scan returns no matches.

- [ ] **Step 4: Verify document completeness**

Run:

```bash
rg -n 'Proposed title|Abstract|Introduction|Methods|Results|Discussion|Figure 1|Figure 2|Figure 3|Figure 4|Limitations|References|reproducib' docs/PROJECT-UNDERSTANDING-OUTLINE.md
```

Expected: every required manuscript component appears.

- [ ] **Step 5: Commit the rewrite**

```bash
git add docs/PROJECT-UNDERSTANDING-OUTLINE.md
git commit -m "docs: rewrite paper outline around SPADE"
```
