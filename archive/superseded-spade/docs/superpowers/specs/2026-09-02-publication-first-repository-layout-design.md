# Publication-first repository layout design

## Goal

Make the repository understandable from the file explorer without hiding scientific evidence
or breaking reproduction. The visible hierarchy should lead with the paper, then software,
research inputs/results, and finally historical material.

## Final structure

```text
publication/
  manuscript/       integrated paper, methods, supplement, protocols, claim ledger
  evidence/         reproduction map, file/commit audits, evidence guides
software/
  src/              installable Python package
  scripts/          active runners, analysers, guards, audit tools
  tests/            active regression suite
  configs/          active frozen configuration
research/
  data/             benchmark, laboratory, and published-data inputs
  results/
    figures/         every active figure and its build metadata
archive/
  source-material/  loose pre-repository PDFs, tables, drafts, and project records
  exploratory/      valid off-paper work
  superseded-spade/ replaced SPADE work and historical figure systems
  bo-vs-doe/        earlier companion study
  void/             failed or invalid evidence
  generated/        logs and rebuildable products
```

Root metadata (`README.md`, `CITATION.cff`, `LICENSE`, `pyproject.toml`, and
`requirements.txt`) remains at the root. Completed process documents move from `docs/` into
the archive. The empty `.planning` directory is removed.

## Explorer policy

Local machinery remains available but is hidden through workspace settings: `.git`,
`.github`, `.venv`, `.pytest_cache`, `.impeccable`, `.planning`, `.vscode`, `__pycache__`, and
package build metadata. Hiding is presentation-only; active GitHub automation remains tracked.

## Source-material policy

Every loose file in `/Users/jy/BO` is inspected by name, size, and checksum before moving.
Exact duplicates remain preserved in a clearly labelled duplicate-extraction directory rather
than being mistaken for independent evidence. Unique drafts, source papers, derived tables,
and project records receive separate subdirectories. No research file is deleted.

## Compatibility and validation

All hard-coded repository paths, Markdown links, packaging configuration, test locations,
and audit destinations must follow the new hierarchy. Validation requires a clean package
import, the full active test suite, 12/12 claim reproduction, publication-link validation,
strict repository-audit validation, and `git diff --check`.

## Commit policy

The complete reorganization is committed once, after all validation succeeds.
