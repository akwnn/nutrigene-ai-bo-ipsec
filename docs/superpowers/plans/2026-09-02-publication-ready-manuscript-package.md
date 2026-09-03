# Publication-ready SPADE manuscript package implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a publication-ready, evidence-bounded SPADE manuscript and scientific repository package that explains the complete active benchmark program, distinguishes novelty from standard methods, and traces every conclusion to code and canonical evidence.

**Architecture:** Use a layered publication model: `MANUSCRIPT.md` carries the focused journal narrative, `METHODS.md` carries executable study detail, `SUPPLEMENT.md` carries exhaustive benchmark/history/limitation tables, and the claim ledger plus reproduction map form the traceability layer. Research agents independently audit literature, active implementation, claim consistency, and repository readiness; the primary agent reconciles their findings against primary sources and canonical results before editing.

**Tech Stack:** Markdown, CSV/JSON evidence, Python 3.11, pytest, repository-specific analysis and audit scripts, Git.

---

### Task 1: Establish the publication baseline and independent research reports

**Files:**
- Read: `publication/manuscript/*.md`
- Read: `publication/evidence/*`
- Read: `software/configs/**/*.yaml`
- Read: `software/scripts/*.py`
- Read: `software/src/boec/*.py`
- Read: `software/tests/*.py`
- Create: `publication/evidence/literature-and-novelty-review.md`
- Create: `publication/evidence/active-pipeline-audit.md`
- Create: `publication/evidence/manuscript-consistency-audit.md`
- Create: `publication/evidence/publication-readiness-audit.md`

- [ ] **Step 1: Capture the clean baseline**

Run: `git status --short && git log -3 --oneline && .venv/bin/python software/scripts/verify_conclusions.py`

Expected: only the approved spec/plan are untracked before implementation; the guard reports `12/12` reproduced values.

- [ ] **Step 2: Dispatch the literature and novelty researcher**

Require primary sources and DOI/official links for GP excursion sets, level-set estimation, Vorob'ev sets, noisy BO/qLogNEI, response-surface DoE, uncertainty calibration, and abstention. Require a three-column classification: established ingredient, SPADE adaptation, defensible new contribution. Save the reconciled report to `publication/evidence/literature-and-novelty-review.md`.

- [ ] **Step 3: Dispatch the active-pipeline researcher**

Require a code-derived map of DC, LC, LA, TAU, and TT: configs, runners, analyzers, result schemas, dimensions, seeds, wells, round schedules, prevalences, estimands, calibration, and guards. Save the reconciled report to `publication/evidence/active-pipeline-audit.md`.

- [ ] **Step 4: Dispatch the claims/history researcher**

Require a line-by-line comparison of manuscript numbers and wording against `CLAIMS-AND-SOURCES.md`, canonical JSON, archived correction chains, and negative/withdrawn findings. Save the reconciled report to `publication/evidence/manuscript-consistency-audit.md`.

- [ ] **Step 5: Dispatch the repository-readiness researcher**

Require an audit of active READMEs, CITATION metadata, license, data status, figure inventory, internal links, packaging, workflows, and stale pre-reorganization paths. Save the reconciled report to `publication/evidence/publication-readiness-audit.md`.

- [ ] **Step 6: Review reports against authoritative evidence**

Run: `rg -n "TBD|TODO|FIXME|unsupported|unverified" publication/evidence/*audit.md publication/evidence/literature-and-novelty-review.md`

Expected: no unresolved placeholder; every uncertainty is explicitly labeled as a limitation or owner-dependent action.

### Task 2: Build explicit novelty and benchmark traceability

**Files:**
- Modify: `publication/manuscript/CLAIMS-AND-SOURCES.md`
- Modify: `publication/evidence/reproduction-map.md`
- Modify: `publication/evidence/RESULTS-GUIDE.md`
- Create: `publication/evidence/benchmark-matrix.md`

- [ ] **Step 1: Create the benchmark matrix**

Add one row per active experiment family (DC, LC, LA, TAU, TT, in-house support, Hall/Ogle support) with status, scientific question, arms, wells, rounds, dimensions, seeds, prevalences, canonical input, analyzer, guarded output, and manuscript role.

Run: `rg -n "DC|LC|LA|TAU|TT|Hall|in-house" publication/evidence/benchmark-matrix.md`

Expected: every active family and both supporting real-data analyses are present.

- [ ] **Step 2: Complete claim-to-code mappings**

For C1-C6 and S1-S3, ensure the claim ledger and reproduction map name canonical result paths, analysis commands, expected values, frozen protocol, manuscript destination, and guard/validation route.

- [ ] **Step 3: Verify no claim-strength drift**

Run: `.venv/bin/python software/scripts/verify_conclusions.py && rg -n "equivalent|validated prospectively|beats DoE|BO cannot" publication/manuscript publication/evidence`

Expected: `12/12` guard success; any forbidden phrase appears only inside an explicitly marked forbidden/correction context.

### Task 3: Rewrite the main manuscript as a focused journal article

**Files:**
- Modify: `publication/manuscript/MANUSCRIPT.md`
- Read: `publication/evidence/literature-and-novelty-review.md`
- Read: `publication/evidence/benchmark-matrix.md`
- Read: `research/results/figures/README.md`

- [ ] **Step 1: Strengthen title, abstract, and introduction**

Present the qualification problem, operational decision, evidence gap, bounded study question, and contributions. Separate standard ingredients from SPADE's proposed workflow and evaluation without claiming component-level algorithmic novelty.

- [ ] **Step 2: Add an explicit study overview and novelty table**

Include a compact table distinguishing established GP/BO/DoE/excursion-set tools, SPADE's integration/adaptation, and the new empirical contribution. Add a benchmark overview table with arm budgets and roles.

- [ ] **Step 3: Integrate figure and table callouts**

Use only canonical publication figures documented by `research/results/figures/README.md`; assign each callout a scientific purpose and ensure captions/alt-text resolve. Do not present exploratory figures as confirmatory.

- [ ] **Step 4: Rebuild Results around scientific questions**

Retain all C1-C6 and S1 values exactly, include denominators and adverse results, explain abstention versus wrong answers, and make development/confirmatory status visible.

- [ ] **Step 5: Expand Discussion and conclusion**

Compare point optimization, region certification, rounds, and well budget; discuss null and failed mechanisms; delimit biological relevance and noise ceiling; state what the evidence changes and what remains open.

- [ ] **Step 6: Verify citations and quantitative consistency**

Run: `.venv/bin/python software/scripts/verify_conclusions.py && .venv/bin/python software/scripts/check_paper_links.py`

Expected: all guarded conclusions reproduce and every repository callout resolves.

### Task 4: Expand Methods from active code and frozen protocols

**Files:**
- Modify: `publication/manuscript/METHODS.md`
- Modify: `publication/manuscript/PROTOCOLS.md` only when an active path or omission must be corrected
- Read: `software/configs/experiment/*.yaml`
- Read: `software/src/boec/{campaign,multiround,certstraddle,vorobev,doe,rsm,optimizers,calibration,meanmarg}.py`
- Read: `software/scripts/{run_dc_doe_certificate,analyse_dc_doe_certificate,run_lc_confirmatory,analyse_lc_confirmatory,run_la_round_matched,analyse_la_round_matched,run_tau_sweep,analyse_tau_sweep,run_tt_theta_tau,analyse_tt_theta_tau}.py`

- [ ] **Step 1: Specify benchmark generation and observation model**

Document dimensions, normalization, response families, instance generation, truth evaluation, relative-noise construction, candidate grids, wells, seeds, and deterministic seed policy from active code.

- [ ] **Step 2: Specify SPADE and certification**

Document GP inputs, batch schedule, acquisition, joint posterior draws, Vorob'ev candidate sets, assurance, inflation grid, answer/containment definitions, and abstention.

- [ ] **Step 3: Specify all comparators**

Document qLogNEI, screened DoE, unscreened DoE, and LHS with exact round and well allocations and common certification scoring.

- [ ] **Step 4: Specify experiment roles and statistics**

Explain DC/LC/LA/TAU/TT, selection/holdout boundaries, pairing keys, bootstrap procedure, Clopper-Pearson rule, SESOI interpretation, and multiple estimands.

- [ ] **Step 5: Specify retrospective real-data support**

Document input status, mean marginalization, LOO inflation, gate-signoff limitation, and why observation prediction does not identify latent-function uncertainty.

- [ ] **Step 6: Cross-check constants against implementation**

Run: `rg -n "48|32|0\.25|0\.95|8000|0\.02|0\.70|0\.50|0\.30|0\.20|0\.10" publication/manuscript/METHODS.md publication/manuscript/PROTOCOLS.md software/configs software/scripts`

Expected: every manuscript constant has a corresponding active definition or an explicit protocol-only explanation.

### Task 5: Make the Supplement exhaustive but navigable

**Files:**
- Modify: `publication/manuscript/SUPPLEMENT.md`
- Modify: `publication/manuscript/README.md`
- Read: `publication/evidence/benchmark-matrix.md`
- Read: `publication/evidence/manuscript-consistency-audit.md`

- [ ] **Step 1: Add the full experiment inventory**

Include status, purpose, design, output, claim role, and whether each active study is development, confirmatory, explanatory, supporting, negative, or withdrawn.

- [ ] **Step 2: Add negative and superseded-result accounting**

Record the rejected `+0.001353`, withdrawn R3 volume claim, failed targeting mechanism, real-noise non-certification, untested R4/rho/assurance scopes, and comparator limits.

- [ ] **Step 3: Add detailed reporting and provenance tables**

Cover required certificate denominators, family/prevalence interpretation, real-data status, canonical figures, and archive boundaries.

- [ ] **Step 4: Update the manuscript reading guide**

Explain which document answers narrative, methodological, supplementary, protocol, claim, benchmark, and reproduction questions.

### Task 6: Make the active repository externally reviewable

**Files:**
- Modify: `README.md`
- Modify as needed: `publication/evidence/README.md`
- Modify as needed: `research/results/figures/README.md`
- Modify as needed: `research/data/lab/README.md`
- Modify as needed: `CITATION.cff`
- Modify as needed: `.github/workflows/spade-distributed.yml`
- Modify as needed: `pyproject.toml`
- Test: `software/tests/test_paper_links.py`
- Test: `software/tests/test_repository_audit.py`

- [ ] **Step 1: Rewrite the root scientific landing page**

Lead with research question, answer, novelty boundary, headline results, limitations, reading order, quick verification, full reproduction, repository map, data status, citation, and license.

- [ ] **Step 2: Repair misleading or skeletal active documentation**

Update only active publication/research/software guides needed for reviewer navigation. Preserve historical archive prose unless a current guide incorrectly points into it.

- [ ] **Step 3: Repair publication blockers identified by the audit**

Fix stale paths, packaging comments, workflow paths, metadata, and missing status statements. Do not invent a license, author role, funding source, ethics approval, or data permission.

- [ ] **Step 4: Run documentation-focused tests**

Run: `.venv/bin/pytest software/tests/test_paper_links.py software/tests/test_repository_audit.py -q`

Expected: all selected tests pass.

### Task 7: Independent review, full verification, and single final commit

**Files:**
- Review: all files changed since `4892b3f`
- Modify: only files necessary to resolve review findings

- [ ] **Step 1: Run independent scientific and code review**

Ask reviewers to check claim fidelity, literature/novelty accuracy, benchmark completeness, readability, internal links, repository readiness, and whether current versus archived evidence is unmistakable.

- [ ] **Step 2: Resolve every material review finding**

Classify findings as fixed, evidence-bounded wording retained, or owner/journal-dependent. Ensure no unresolved placeholder remains in submission-facing documents.

- [ ] **Step 3: Run the complete verification suite**

Run: `.venv/bin/python software/scripts/verify_conclusions.py`

Expected: `12/12` values reproduce.

Run: `.venv/bin/python software/scripts/check_paper_links.py`

Expected: exit 0 with no missing manuscript paths.

Run: `.venv/bin/pytest -q`

Expected: all tests pass.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 4: Audit the final diff and staged scope**

Run: `git status --short && git diff --stat && git diff --name-status`

Expected: only publication-package files and justified publication-readiness repairs are changed; no archive bulk rewrite or unrelated user file appears.

- [ ] **Step 5: Create the sole final commit**

Run: `git add -- README.md CITATION.cff publication research/results/figures/README.md research/data/lab/README.md software .github pyproject.toml docs/superpowers/specs/2026-09-02-publication-ready-manuscript-package-design.md docs/superpowers/plans/2026-09-02-publication-ready-manuscript-package.md`

Run: `git diff --cached --check && git diff --cached --stat`

Expected: clean staged diff containing only reviewed work.

Run: `git commit -m "docs: prepare SPADE publication package"`

Expected: one commit created after all verification, with the worktree clean.
