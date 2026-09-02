# SPADE Repository Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the repository into a publication-ready, fully audited evidence base for the SPADE methods paper while preserving all historical work in an indexed archive.

**Architecture:** Build machine-checkable baseline inventories first, then add human scientific verdicts by tracing claims to data and code. Establish the active paper and evidence paths before moving historical material. Perform migration in small thematic commits, repair paths immediately, and verify claims, tests, figures, and raw-data integrity after each batch.

**Tech Stack:** Python 3.11+, CSV and JSON from the standard library, Git, pytest, existing `boec` package, existing conclusion and figure validators.

**Design specification:** `docs/superpowers/specs/2026-09-01-spade-repository-consolidation-design.md`

**Audit baseline:** commit `6e4f22e`, containing 719 commits and the complete pre-consolidation tracked tree.

---

## File Structure

### New active files

- `paper/README.md`: manuscript navigation and status.
- `paper/MANUSCRIPT.md`: consolidated SPADE paper draft.
- `paper/METHODS.md`: canonical methods linked to producing code.
- `paper/SUPPLEMENT.md`: supporting evidence used by the paper.
- `paper/CLAIMS-AND-SOURCES.md`: authoritative human-readable claim ledger.
- `paper-evidence/README.md`: plain-English evidence guide.
- `paper-evidence/file-review.csv`: one reviewed row for every baseline tracked file.
- `paper-evidence/commit-review.csv`: one reviewed row for every baseline commit.
- `paper-evidence/reproduction-map.md`: exact commands and expected outputs for paper evidence.
- `paper-evidence/main-results/*/README.md`: indexes for the five main evidence groups.
- `paper-evidence/supporting-results/*/README.md`: indexes for supporting evidence groups.
- `archive/README.md`: archive-wide navigation and rules.
- `archive/*/README.md`: section-specific archive manifests.
- `scripts/audit_repository.py`: deterministic baseline inventory and audit validation.
- `scripts/check_paper_links.py`: active-paper path and reference validation.
- `tests/test_repository_audit.py`: audit schema, count, uniqueness, and destination tests.
- `tests/test_paper_links.py`: paper/evidence link and stale-reference tests.
- `CITATION.cff`: citation metadata for a DOI-ready release.
- `LICENSE`: explicit software licensing status or chosen license text.

### Existing files to consolidate or relocate

- Active narrative sources under `docs/` consolidate into `paper/`.
- Canonical compact result artifacts remain linked from `paper-evidence/`; they move only when all hard-coded path consumers are repaired.
- Historical Markdown, runners, logs, and results move into the appropriate `archive/` section.
- Reusable package code stays under `src/boec/` unless the audit proves it is historical and has no active importer.
- Active tests stay under `tests/`; tests for archived-only behavior move only with the corresponding historical implementation.
- Immutable inputs remain under `data/`; this plan does not rename raw inputs before checksum and consumer audits pass.

---

### Task 1: Freeze and test the audit baseline

**Files:**
- Create: `tests/test_repository_audit.py`
- Create: `scripts/audit_repository.py`
- Create: `paper-evidence/file-review.csv`
- Create: `paper-evidence/commit-review.csv`

- [ ] **Step 1: Write failing audit contract tests**

Create tests that require:

```python
from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "6e4f22e"


def _rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_baseline_commit_count_is_frozen() -> None:
    count = subprocess.check_output(
        ["git", "rev-list", "--count", BASELINE], cwd=ROOT, text=True
    ).strip()
    assert count == "719"


def test_file_review_has_one_unique_row_per_baseline_file() -> None:
    tracked = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASELINE], cwd=ROOT, text=True
    ).splitlines()
    rows = _rows("paper-evidence/file-review.csv")
    paths = [row["baseline_path"] for row in rows]
    assert len(paths) == len(tracked)
    assert len(paths) == len(set(paths))
    assert sorted(paths) == sorted(tracked)


def test_commit_review_has_one_unique_row_per_baseline_commit() -> None:
    commits = subprocess.check_output(
        ["git", "rev-list", BASELINE], cwd=ROOT, text=True
    ).splitlines()
    rows = _rows("paper-evidence/commit-review.csv")
    hashes = [row["commit"] for row in rows]
    assert len(hashes) == 719
    assert len(hashes) == len(set(hashes))
    assert set(hashes) == set(commits)


def test_completed_file_rows_use_allowed_classifications() -> None:
    allowed = {
        "CORE", "SUPPORT", "INFRASTRUCTURE", "ARCHIVE-VALID",
        "ARCHIVE-SUPERSEDED", "ARCHIVE-FAILED/VOID", "GENERATED/DISPOSABLE",
    }
    for row in _rows("paper-evidence/file-review.csv"):
        assert row["classification"] in allowed
        assert row["destination"]
        assert row["rationale"]
```

- [ ] **Step 2: Run the tests and confirm missing audit files fail**

Run: `pytest tests/test_repository_audit.py -v`

Expected: FAIL because the audit script and CSV ledgers do not exist.

- [ ] **Step 3: Implement deterministic inventory generation**

Implement `scripts/audit_repository.py` with these commands and contracts:

```python
BASELINE = "6e4f22e"
ALLOWED = {
    "CORE", "SUPPORT", "INFRASTRUCTURE", "ARCHIVE-VALID",
    "ARCHIVE-SUPERSEDED", "ARCHIVE-FAILED/VOID", "GENERATED/DISPOSABLE",
}

# `inventory` writes rows in lexical path order and reverse chronological commit order.
# It obtains paths from: git ls-tree -r --name-only 6e4f22e
# It obtains first/latest commits from: git log --follow --format=%H -- <path>
# It obtains commit rows from: git log 6e4f22e --format=%H%x09%ad%x09%s --date=short
# Existing human verdict columns are preserved when inventory is regenerated.
# `validate` rejects missing rows, duplicate keys, unknown classifications,
# empty destinations/rationales, and baseline-count drift.
```

The file-review header must be:

```text
baseline_path,file_type,first_commit,latest_meaningful_commit,research_era,scientific_question,evidence_level,manuscript_claim,reproduction_role,dependencies,supersession_status,classification,destination,rationale
```

The commit-review header must be:

```text
commit,date,subject,research_era,purpose,important_files,conclusion_status,superseding_commit,paper_relevance,audit_notes
```

- [ ] **Step 4: Generate baseline ledgers**

Run: `python scripts/audit_repository.py inventory`

Expected: both CSV files exist; file rows equal `git ls-tree` count; commit rows equal 719. Human verdict columns initially contain `UNREVIEWED`, which is accepted only by `inventory`, not by final `validate`.

- [ ] **Step 5: Run inventory-mode tests**

Temporarily limit the completed-row test to rows whose classification is not `UNREVIEWED`, then run:

`pytest tests/test_repository_audit.py -v`

Expected: PASS for baseline identity, row counts, headers, and uniqueness.

- [ ] **Step 6: Commit the audit foundation**

```bash
git add scripts/audit_repository.py tests/test_repository_audit.py paper-evidence/file-review.csv paper-evidence/commit-review.csv
git commit -m "chore: freeze repository audit baseline"
```

---

### Task 2: Review all commits by scientific era

**Files:**
- Modify: `paper-evidence/commit-review.csv`
- Create: `paper-evidence/README.md`

- [ ] **Step 1: Define non-overlapping research eras**

Use these era labels, refined only when a commit demonstrably crosses a boundary:

```text
E1-E4_FOUNDATION
BO_VS_DOE_TERMINAL_RULE
LAB_AND_PUBLISHED_DATA
DESIGN_SPACE_PRE_SPADE
SPADE_DEVELOPMENT_AND_LOCKBOX
SPADE_MANUFACTURING_RECOVERY
SPADE_CONFIRMATION_AND_PAPER
```

- [ ] **Step 2: Review commits chronologically**

For each of the 719 baseline commits, read at minimum:

```bash
git show --format=fuller --stat <commit>
git show --format= --name-status <commit>
```

Read the patch with `git show <commit> -- <relevant-path>` whenever the subject/stat does not establish whether the conclusion still stands. Populate every commit-review field. Name correction, retraction, or superseding hashes explicitly.

- [ ] **Step 3: Validate commit coverage continuously**

Run after each era: `python scripts/audit_repository.py validate-commits`

Expected: the completed era has no `UNREVIEWED` fields; exactly 719 unique hashes remain.

- [ ] **Step 4: Write the plain-English evidence guide introduction**

In `paper-evidence/README.md`, explain that the audit starts at baseline `6e4f22e`, prior summaries are not authorities, and the commit ledger records which conclusions survived.

- [ ] **Step 5: Commit the chronological audit**

```bash
git add paper-evidence/commit-review.csv paper-evidence/README.md
git commit -m "docs: audit pre-consolidation commit history"
```

---

### Task 3: Build the authoritative claim-to-source ledger

**Files:**
- Create: `paper/CLAIMS-AND-SOURCES.md`
- Create: `paper-evidence/reproduction-map.md`
- Modify: `paper-evidence/README.md`

- [ ] **Step 1: Extract candidate claims without accepting them**

Review at minimum:

```text
docs/SPADE-PAPER-ARGUMENT.md
docs/SPADE-CONCLUSIONS-2026-08-29.md
docs/SPADE-RESULTS-AND-ANALYSIS.md
docs/SPADE-STATE-OF-THE-METHOD.md
docs/RESEARCH-SUMMARY.md
docs/CLAIMS.md
docs/TRIAGE.md
docs/MAIN-LINE.md
```

- [ ] **Step 2: Define the claim ledger format**

Each claim entry must contain:

```text
Claim ID
Allowed manuscript wording
Forbidden overstatement
Scientific status: MAIN / SUPPORT / LIMITATION / OPEN
Population, family, prevalence, sigma, wells, rounds, and seeds
Headline estimate, uncertainty, and test
Canonical result path
Producing analysis and runner
Frozen config or protocol
Relevant validators/tests
Figure/table destination
Known corrections or caveats
```

- [ ] **Step 3: Validate the main claim groups**

Create validated entries for:

1. SPADE certification architecture and abstention.
2. SPADE versus BO recipe quality and matched-round certified volume.
3. SPADE versus classical DoE recipe and containment trade-off.
4. SPADE versus one-shot design.
5. Cross-family generalization across Ackley, Hartmann6, Hill, Levy, and Rosenbrock.
6. Hill higher-prevalence certification.
7. In-house and published iPSC-EC results.
8. Targeting/mechanism negative results.
9. Noise ceiling, real-data limitations, and absence of prospective wet-lab validation.

- [ ] **Step 4: Run existing conclusion checks**

Run: `python scripts/verify_conclusions.py`

Expected: exit 0 and all guarded paper numbers reproduce from committed data. Any failure becomes an explicit blocker in the ledger rather than being edited around.

- [ ] **Step 5: Write exact reproduction entries**

For every accepted claim, add the current exact command and expected headline values to `paper-evidence/reproduction-map.md`. Mark commands as `FAST`, `LONG`, or `REQUIRES RAW DATA`; do not claim a command was tested unless it is run during this project.

- [ ] **Step 6: Commit the validated claim map**

```bash
git add paper/CLAIMS-AND-SOURCES.md paper-evidence/README.md paper-evidence/reproduction-map.md
git commit -m "docs: map SPADE claims to canonical evidence"
```

---

### Task 4: Review every tracked file

**Files:**
- Modify: `paper-evidence/file-review.csv`

- [ ] **Step 1: Review documentation and planning files**

Read every baseline Markdown, YAML planning, and workflow file. Determine whether it states an active claim, records a binding protocol, supplies historical provenance, or duplicates/supersedes another document.

- [ ] **Step 2: Review results and generated artifacts**

For every baseline file under `results/`, record producing script, consumer paths, claim supported, canonical/superseded status, and whether it is raw output, checkpoint, log, or publication artifact.

- [ ] **Step 3: Review source, scripts, tests, and configs**

Use `rg` to identify imports and path consumers. Classify active reusable code as INFRASTRUCTURE when it supports CORE or SUPPORT evidence. Do not archive source merely because its original experiment is historical if current SPADE code imports it.

- [ ] **Step 4: Review data files**

For each baseline data file, distinguish immutable raw input, authoritative external extraction, canonical processed input, disposable derived output, and unrelated historical data. Record checksums or existing manifest references for raw inputs.

- [ ] **Step 5: Validate complete human verdicts**

Restore the strict completed-row test from Task 1 and run:

```bash
python scripts/audit_repository.py validate
pytest tests/test_repository_audit.py -v
```

Expected: PASS; no `UNREVIEWED` value remains; every destination is inside the approved active or archive structure.

- [ ] **Step 6: Commit the file-by-file audit**

```bash
git add paper-evidence/file-review.csv tests/test_repository_audit.py
git commit -m "docs: complete file-by-file SPADE repository audit"
```

---

### Task 5: Create active evidence and archive indexes

**Files:**
- Create: `paper-evidence/main-results/*/README.md`
- Create: `paper-evidence/supporting-results/*/README.md`
- Create: `archive/README.md`
- Create: `archive/bo-vs-doe/README.md`
- Create: `archive/superseded-spade/README.md`
- Create: `archive/exploratory/README.md`
- Create: `archive/void/README.md`
- Create: `archive/generated/README.md`

- [ ] **Step 1: Write evidence group indexes**

Each index lists accepted claims, canonical results, producing code, tests, and exact links to `paper/CLAIMS-AND-SOURCES.md`. The cross-family index must cover all five families and include a dedicated Hill subsection.

- [ ] **Step 2: Write archive indexes**

Each archive index defines validity, reason for inactivity, replacements, and reproducibility status. It must explicitly state that archived does not automatically mean incorrect.

- [ ] **Step 3: Test all index links**

Implement `scripts/check_paper_links.py` to parse relative Markdown links under `paper/`, `paper-evidence/`, and `archive/`, failing on missing local targets or links that escape the repository.

- [ ] **Step 4: Write and run link tests**

Create `tests/test_paper_links.py` and run:

`pytest tests/test_paper_links.py -v`

Expected: PASS with every new index link resolving.

- [ ] **Step 5: Commit navigation**

```bash
git add paper-evidence archive scripts/check_paper_links.py tests/test_paper_links.py
git commit -m "docs: establish paper evidence and archive navigation"
```

---

### Task 6: Consolidate active Markdown and archive historical narratives

**Files:**
- Create: `paper/README.md`
- Create: `paper/METHODS.md`
- Create: `paper/SUPPLEMENT.md`
- Move: audited historical and superseded Markdown according to `file-review.csv`
- Modify: references throughout active files

- [ ] **Step 1: Consolidate methods**

Build `paper/METHODS.md` from validated portions of existing method and protocol documents. Every computational subsection must cite exact code/config paths and every biological-data subsection must cite raw/processed inputs and limitations.

- [ ] **Step 2: Consolidate supporting results**

Build `paper/SUPPLEMENT.md` from SUPPORT claims only. Include failed targeting, calibration limitations, abstention behavior, real-data caveats, and reviewer defenses that remain valid.

- [ ] **Step 3: Move historical narratives by audit verdict**

Use `git mv` in small groups corresponding to `bo-vs-doe`, `superseded-spade`, `exploratory`, and `void`. Update the matching archive index in the same commit as each move.

- [ ] **Step 4: Remove active-path contradictions**

Run searches for withdrawn headline wording and stale paths recorded in `CLAIMS-AND-SOURCES.md`. Active files must not present superseded claims as current.

- [ ] **Step 5: Verify docs after each move group**

Run:

```bash
pytest tests/test_paper_links.py tests/test_repository_audit.py -v
python scripts/verify_conclusions.py
```

Expected: PASS after every thematic move commit.

- [ ] **Step 6: Commit each thematic document migration**

Use commit messages:

```text
docs: consolidate active SPADE methods
docs: consolidate SPADE supporting evidence
archive: move BO versus DoE companion documents
archive: move superseded SPADE documents
archive: move exploratory and void documents
```

---

### Task 7: Consolidate canonical results and archive historical outputs

**Files:**
- Move or retain: baseline files under `results/` according to `file-review.csv`
- Modify: result loaders, scripts, tests, docs, and `.gitignore` paths affected by moves
- Modify: `paper-evidence/reproduction-map.md`

- [ ] **Step 1: Produce a result dependency report**

For each proposed result move, use `rg -n --fixed-strings '<old-path>' . --glob '!.git/**'` and record every consumer in the audit ledger.

- [ ] **Step 2: Establish canonical main-result indexes**

Link compact canonical outputs from their five evidence-group indexes. Avoid copying the same JSON into `paper-evidence/`; move only when a clearer canonical path outweighs path churn.

- [ ] **Step 3: Move historical logs, checkpoints, and outputs**

Move in separate commits for companion, superseded, exploratory, void, and generated artifacts. Repair consumers in the same commit. Preserve manifest/checksum sidecars with their data.

- [ ] **Step 4: Update `.gitignore` deliberately**

After moves, ensure every committed canonical result remains explicitly trackable and large regenerated files remain excluded. Never reintroduce the >100 MB `results/p6-families.json` history problem.

- [ ] **Step 5: Verify each result batch**

Run affected result tests, `python scripts/verify_conclusions.py`, and link validation after every move commit.

- [ ] **Step 6: Commit result migrations by evidence class**

Use small commit messages that name the evidence group and never combine unrelated scientific eras.

---

### Task 8: Audit and reorganize scripts, configs, source, tests, and data

**Files:**
- Move: historical scripts/configs/tests only when audit dependencies permit
- Modify: imports, workflow commands, docs, and tests affected by moves
- Preserve: active reusable modules under `src/boec/`
- Preserve: immutable raw data and checksum manifests

- [ ] **Step 1: Build import and invocation maps**

Use `rg` across source, scripts, tests, configs, workflows, docs, and reproduction entries. A source module with an active importer stays active even if its original experiment is archived.

- [ ] **Step 2: Separate active reproduction commands**

Place active paper entry points under `scripts/reproduce/` only when the move makes the workflow clearer. Thin wrappers may call stable modules; do not duplicate analysis logic.

- [ ] **Step 3: Archive historical runners with their configs**

Move runner/config pairs together. Keep archived tests when they are necessary to explain whether the historical result was valid; otherwise retain active regression tests that protect shared code.

- [ ] **Step 4: Verify raw-data integrity**

Compare raw-data paths and checksums against committed manifests before and after any directory work. Do not alter raw bytes.

- [ ] **Step 5: Run the full test suite**

Run: `pytest -q`

Expected: PASS. Record any pre-existing failures separately; do not weaken tests to complete the cleanup.

- [ ] **Step 6: Commit each code/data migration separately**

Keep source, script/config, test, and data migrations in independently reviewable commits.

---

### Task 9: Build the publication entry point and citation metadata

**Files:**
- Modify: `README.md`
- Create: `CITATION.cff`
- Create or clarify: `LICENSE`
- Modify: `paper-evidence/README.md`

- [ ] **Step 1: Rewrite the root README**

The first screen must state: what SPADE is, the narrow main claim, the honest limitation, where the manuscript is, how to reproduce the main results, where raw data live, and how to navigate the archive.

- [ ] **Step 2: Add citation metadata**

Create valid CFF metadata using confirmed project title, authorship, repository URL, license, and version. Do not guess ORCIDs, affiliations, DOI, or final journal.

- [ ] **Step 3: Resolve licensing explicitly**

If no license choice is documented locally, mark licensing as a publication blocker and request the owner’s decision before inserting a license. Do not assume MIT, BSD, GPL, or a data license.

- [ ] **Step 4: Validate entry-point links and metadata**

Run link tests and a CFF validator if installed. If no validator is available, parse the YAML with the project environment and record that limited validation.

- [ ] **Step 5: Commit publication metadata**

```bash
git add README.md CITATION.cff LICENSE paper-evidence/README.md
git commit -m "docs: add publication-ready repository entry point"
```

Omit `LICENSE` from the commit until the owner approves a license if that decision is unresolved.

---

### Task 10: Build the final manuscript from validated claims

**Files:**
- Create: `paper/MANUSCRIPT.md`
- Modify: `paper/CLAIMS-AND-SOURCES.md`
- Modify: `paper/METHODS.md`
- Modify: `paper/SUPPLEMENT.md`
- Populate: `paper/figures/`
- Populate: `paper/tables/`

- [ ] **Step 1: Draft the paper structure**

Use this narrative order:

```text
Abstract
Introduction: manufacturing needs a certified region, not only a recipe
SPADE method
Benchmark and comparator design
Cross-family generalization, including the Hill result
Comparison with BO, classical DoE, and one-shot design
Rounds and cost
Real iPSC-EC evidence
Mechanism tests, negative results, and limitations
Discussion
Methods
Data availability
Code availability
```

- [ ] **Step 2: Insert only ledger-approved quantitative claims**

Every number in `paper/MANUSCRIPT.md` must have a Claim ID and exact evidence path in `paper/CLAIMS-AND-SOURCES.md`. Forbidden wording from the ledger must not appear.

- [ ] **Step 3: Rebuild publication figures and tables**

Run the commands in `paper-evidence/reproduction-map.md`. Copy or move only validated final exports into `paper/figures/` and `paper/tables/`, with build manifests retained.

- [ ] **Step 4: Check manuscript claims mechanically**

Extend `scripts/check_paper_links.py` or add a focused validator so quantitative Claim IDs referenced by the manuscript exist in the ledger and all figure/table files resolve.

- [ ] **Step 5: Commit the evidence-bound manuscript**

```bash
git add paper paper-evidence/reproduction-map.md
git commit -m "paper: assemble SPADE manuscript from validated evidence"
```

---

### Task 11: Final repository verification and release report

**Files:**
- Create: `paper-evidence/FINAL-AUDIT-REPORT.md`
- Modify: audit ledgers and reproduction map if verification exposes gaps

- [ ] **Step 1: Validate audit completeness**

Run:

```bash
python scripts/audit_repository.py validate
pytest tests/test_repository_audit.py tests/test_paper_links.py -v
```

Expected: every baseline file and commit has a complete verdict; all destinations and links are valid.

- [ ] **Step 2: Run scientific validators**

Run:

```bash
python scripts/verify_conclusions.py
pytest -q
```

Expected: PASS, with no active claim depending only on a narrative document or untracked local file.

- [ ] **Step 3: Execute the reproduction map**

Run every `FAST` command and all feasible `LONG` commands. Record duration, exit status, and output hashes. Clearly identify commands not rerun and why.

- [ ] **Step 4: Verify raw data**

Re-run existing data manifests/checksum validation and record that raw bytes are unchanged from baseline.

- [ ] **Step 5: Write the final audit report**

Report:

- baseline and final commit;
- counts by file classification and archive class;
- active claim count;
- tests and validators run;
- reproduction commands run or deferred;
- raw-data integrity result;
- unresolved scientific or publication blockers;
- final active and archive navigation; and
- explicit confirmation that no historical material was permanently deleted.

- [ ] **Step 6: Commit the verified consolidation**

```bash
git add paper-evidence/FINAL-AUDIT-REPORT.md paper-evidence/file-review.csv paper-evidence/commit-review.csv paper-evidence/reproduction-map.md
git commit -m "docs: certify SPADE repository consolidation"
```

---

## Execution Rules

- Work inline in the current repository because the user explicitly approved immediate execution.
- Do not push unless separately requested.
- Do not rewrite history or permanently delete files.
- Use `git mv` for tracked-file relocation.
- Preserve unrelated user changes if any appear.
- Never classify from filename or age alone.
- Never accept a summary document as evidence without tracing its sources.
- Pause only for a decision that cannot be inferred safely, such as software/data licensing or restricted-data publication.
- After every thematic commit, record the new commit hash in the active audit notes.
