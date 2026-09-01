# SPADE Repository Consolidation Design

**Date:** 2026-09-01  
**Status:** Approved design, pending implementation plan  
**Primary objective:** Turn the repository into a clear, reproducible evidence base for a SPADE methods paper without deleting the scientific history.

## 1. Scientific scope

The final paper is a **SPADE methods paper**. Its primary contribution is a method for returning a certified cell-manufacturing design space rather than only a single optimized recipe.

The active paper must compare SPADE with Bayesian optimization, classical design of experiments, and one-shot designs. The in-house and published iPSC-EC data motivate and test the method on real cell-manufacturing evidence. The earlier terminal-rule and BO-versus-DoE investigation is a companion study and background, not a coequal paper narrative.

The cross-family benchmark is CORE evidence. It includes Ackley, Hartmann6, Hill, Levy, and Rosenbrock across the tested target prevalences. The Hill work is especially important because its biphasic response is the biology-shaped benchmark and because its successful higher-prevalence certification is part of the generalization argument. The Hill evidence must remain easy to locate without being separated from the five-family comparison that gives it meaning.

## 2. Governing principles

1. Current summaries, handoffs, and prior agent conclusions are leads, not ground truth.
2. A claim is accepted only after it is traced to committed data and its producing or validating code path.
3. Every tracked file and every commit receives an explicit review record.
4. Nothing is permanently deleted as part of this consolidation.
5. Git history is not rewritten.
6. Raw lab and published source data remain immutable.
7. Negative results, retractions, and corrections remain accessible when they constrain an honest paper claim.
8. Material outside the paper's active evidence path moves to an indexed archive with a reason and, when applicable, a named replacement.
9. Repository cleanup must preserve or improve reproducibility; reducing the file count is not itself success.
10. The manuscript is written from the validated claim-and-source ledger, not from whichever historical narrative document appears most complete.

## 3. Audit method

The audit uses two complementary passes.

### 3.1 Claim-to-evidence pass

Start from each proposed manuscript claim and trace it backward through:

1. manuscript-ready table or figure;
2. canonical analysis output;
3. analysis or figure-building script;
4. frozen configuration and protocol;
5. reusable source modules;
6. relevant tests and validators;
7. processed inputs; and
8. immutable raw inputs.

This creates the minimum complete reproduction path for every main and supporting claim.

### 3.2 Exhaustive repository pass

Independently inspect:

- every tracked file;
- all 719 pre-consolidation commits through baseline commit `6e4f22e` in chronological research eras;
- additions, corrections, retractions, and supersessions within those commits; and
- dependencies that cross research eras.

This second pass prevents the current summaries from silently determining the outcome and catches useful evidence that is not linked from current documents.

File-level and commit-level conclusions must be reconciled before any move. A recent file is not automatically authoritative, and an old file is not automatically obsolete.

## 4. Classification framework

Each file receives one destination classification and may receive multiple scientific or technical roles.

| Classification | Meaning |
|---|---|
| `CORE` | Directly states, computes, validates, or visualizes a main SPADE paper claim. |
| `SUPPORT` | Supplies reviewer defense, sensitivity analysis, real-data validation, a limitation, or a negative result used by the paper. |
| `INFRASTRUCTURE` | Source code, tests, configurations, build tooling, or workflow definitions required to reproduce CORE or SUPPORT evidence. |
| `ARCHIVE-VALID` | Sound work that answers a different or earlier research question and is not needed by this paper. |
| `ARCHIVE-SUPERSEDED` | Replaced by a later protocol, implementation, analysis, result, or correction. |
| `ARCHIVE-FAILED/VOID` | Invalid run, wrong estimand, broken implementation, incomplete output, abandoned experiment, or withdrawn result. |
| `GENERATED/DISPOSABLE` | Cache, duplicate export, log, checkpoint, or rebuildable intermediate that is not a canonical result. It is archived or excluded from the active tree, not permanently destroyed by this project. |

Classification and role are distinct. For example, a Hill runner can be classified as `INFRASTRUCTURE` and carry the role `supports CORE cross-family claim`.

## 5. Required audit records

### 5.1 `paper-evidence/file-review.csv`

One row per tracked file with at least:

- current path;
- file type;
- first introducing commit;
- latest meaningful commit;
- research era;
- scientific question;
- evidence level;
- manuscript claim supported;
- reproduction role;
- important dependencies;
- supersession or defect status;
- classification;
- proposed destination; and
- plain-language rationale.

### 5.2 `paper-evidence/commit-review.csv`

One row per commit with at least:

- commit hash and date;
- subject;
- research era;
- scientific or technical purpose;
- important files introduced or changed;
- whether its conclusion still stands;
- correction, retraction, or superseding commit when applicable;
- relevance to the final paper; and
- audit notes.

### 5.3 `paper-evidence/reproduction-map.md`

For every main result, table, and figure, record:

- the exact claim;
- canonical input files;
- exact command;
- expected outputs;
- relevant source modules and tests;
- expected headline values or validation conditions; and
- environment requirements.

## 6. Target repository structure

```text
README.md
LICENSE
CITATION.cff
pyproject.toml
requirements.txt

paper/
  MANUSCRIPT.md
  METHODS.md
  SUPPLEMENT.md
  CLAIMS-AND-SOURCES.md
  figures/
  tables/

paper-evidence/
  README.md
  main-results/
    spade-method/
    cross-family-generalization/
    method-comparisons/
    rounds-and-cost/
    real-cell-validation/
  supporting-results/
    mechanism-tests/
    limitations-and-failures/
    reviewer-defenses/
  file-review.csv
  commit-review.csv
  reproduction-map.md

src/
scripts/
  reproduce/
  archive/
tests/
configs/
data/
  raw/
  processed/
results/
  intermediate/

archive/
  README.md
  bo-vs-doe/
  superseded-spade/
  exploratory/
  void/
  generated/
```

The structure is a target information architecture, not a command to move every file mechanically. Existing package conventions remain where they are required by imports or tooling. A file moves only after its dependency path is understood and the destination improves navigation.

## 7. Meaning of the active evidence folders

### 7.1 Main results

- `spade-method/`: the method definition, certification behavior, and canonical SPADE result package.
- `cross-family-generalization/`: the combined Ackley, Hartmann6, Hill, Levy, and Rosenbrock evidence, including prevalence and margin-to-noise analyses.
- `method-comparisons/`: matched comparisons with BO, classical DoE, and one-shot designs.
- `rounds-and-cost/`: wells, rounds, matched-round analyses, and efficiency claims.
- `real-cell-validation/`: in-house and published iPSC-EC analyses and their explicit limitations.

### 7.2 Supporting results

- `mechanism-tests/`: targeting, theta/tau, calibration, and related mechanism investigations used to interpret SPADE.
- `limitations-and-failures/`: noise ceiling, abstention, failed variants, retractions, and other results needed to bound claims honestly.
- `reviewer-defenses/`: robustness and sensitivity analyses that answer plausible objections but do not lead the main narrative.

The active evidence directories should contain compact canonical outputs and readable indexes. Large raw inputs, reusable code, and tests stay in their standard top-level locations and are linked rather than copied.

## 8. Archive design

The archive is searchable, versioned, and explicitly outside the primary reading path.

- `bo-vs-doe/`: the companion terminal-rule study and its supporting record.
- `superseded-spade/`: replaced SPADE protocols, analyses, and outputs.
- `exploratory/`: valid investigations that do not support this paper.
- `void/`: invalid, broken, incomplete, or withdrawn experiments with the reason preserved.
- `generated/`: duplicate or rebuildable artifacts retained for historical completeness when they carry audit value; otherwise the archive index records how to regenerate them without keeping an active copy.

Each archive section must have an index describing:

- what is present;
- why it is not active;
- whether it remains scientifically valid;
- what superseded it, if anything; and
- whether it can still be reproduced.

## 9. Migration sequence

1. Establish and validate the paper claim ledger.
2. Complete the claim-to-evidence dependency graph.
3. Review the commit history by research era.
4. Review every tracked file.
5. Reconcile file and commit verdicts.
6. Build and verify the minimal active reproduction path before moving files.
7. Consolidate overlapping active Markdown documents.
8. Move documentation in small thematic commits and repair links.
9. Move or consolidate canonical and historical results in small thematic commits and repair loaders.
10. Reorganize scripts and configurations only after their active dependencies are proven.
11. Reorganize processed data while preserving immutable raw data and checksums.
12. Move caches, logs, checkpoints, and duplicate exports out of the active path.
13. Run tests, conclusion validators, and figure reproduction after every migration batch.
14. Build the final paper from `paper/CLAIMS-AND-SOURCES.md` and the verified reproduction map.

The migration must use multiple reviewable commits. It must not be delivered as a single repository-wide move.

## 10. Verification and failure handling

Before a file moves, record its dependents and expected replacement path. After each migration batch:

- validate internal links and file references;
- run the affected unit and integration tests;
- run applicable evidence or conclusion validators;
- reproduce affected tables and figures;
- compare canonical headline values; and
- confirm that the working tree contains no unexplained generated files.

If a result cannot be reproduced, it is not silently discarded. It is marked unresolved and placed in SUPPORT or a specifically named archive class only after its role in the paper is assessed.

If two files disagree, neither is selected by convenience or recency. The producing code, data, frozen decisions, and correction history determine the verdict. Unresolved disagreements remain explicit blockers in the audit ledger.

## 11. Publication readiness

The cleaned repository should let a reviewer:

1. understand the SPADE claim from the root README;
2. locate the cross-family, Hill, comparator, cost, and real-cell evidence quickly;
3. map every manuscript claim to data and code;
4. reproduce each main figure and table with a documented command;
5. identify limitations, failures, and abstentions without reading historical logs; and
6. cite a versioned release using `CITATION.cff` and a DOI-ready archive.

The repository will retain the full archive, while a publication release can identify the active reproduction path and minimum dataset clearly. Data and code availability statements belong in the manuscript and README once the target journal and access constraints are known.

## 12. Completion criteria

The consolidation is complete only when:

- every file tracked at baseline `6e4f22e` and all 719 pre-consolidation commits have audit records;
- every active main claim has a complete and passing reproduction path;
- the five-family generalization result and Hill evidence are explicit CORE material;
- no active Markdown document presents a superseded result as current;
- raw data are unchanged and canonical processed data are identifiable;
- archive entries state why they are inactive;
- affected tests, validators, tables, and figures pass from the cleaned tree;
- the root README provides one unambiguous starting point; and
- the manuscript is derived only from validated claims and sources.
