# Publication documentation reconciliation report

## Implementation

- Reconciled `docs/RESEARCH-SUMMARY.md` with the current manuscript and operational state.
- Preserved the historical numerical tables and explicitly separated historical diagnostics from the four current main manuscript figures.
- Corrected active prospective certificate wording: `containment_cell` is a posterior self-consistency check, not oracle containment, and establishes no empirical validity even in Hill.
- Kept the separate retrospective oracle-containment evidence, including its Hill, Levy, Rosenbrock, Ackley, and Hartmann6 results, as historical evidence.
- Documented the fixed 0.50 prospective map cutoff, the common-GP Figure 2 locator (20,000 screen points, 20 restarts, 4,096 raw starts), and the separation from earlier quadratic extrapolation diagnostics.
- Clarified that 99,601 records comprise 99,600 scored configurations from 8,300 campaign-arm executions plus one unavailable-design declaration.
- Updated the later joint-protocol status to 2,750 rows, `NO_SELECTION`, no power artifact, and an unopened lockbox.
- Left author declarations, licensing approval, DOI assignment, primary results, gates, and lockbox state untouched.

## Verification

- Read the full 887-line research summary and the full canonical manuscript before editing; reconciled against `.planning/STATE.md` and `.planning/ROADMAP.md`.
- Self-reviewed all certificate/containment/validity and figure references with targeted repository searches after editing.
- Focused publication-document tests: `PYTHONPATH=. .venv/bin/pytest -q tests/test_manuscript_docx.py tests/test_publication_bundle.py tests/test_submission_package.py` — **23 passed**.
- A bare `pytest` invocation was unavailable on `PATH`; the repository virtual environment succeeded.
- `git diff --check` — **passed**.

## Remaining concerns

- Submission remains author-controlled for declarations, licensing approval, scientific/AI-disclosure signoff, and the archival DOI.
- Historical exact-replay discrepancies remain disclosed and unresolved; no equality gate or retained result was changed.

## Reviewer follow-up

- Replaced the final stale active `(Figure 3)` citation for the 200/200 saddle result with `(historical saddle/ridge diagnostic)`.
- Re-scanned every `Figure`/`Figures` reference in `docs/RESEARCH-SUMMARY.md`; remaining numbered references either identify the four current manuscript figures or explicitly distinguish historical diagnostics from them.
- Re-ran `git diff --check` after the correction — **passed**.
