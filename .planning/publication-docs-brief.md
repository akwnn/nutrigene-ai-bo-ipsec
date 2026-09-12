# Publication documentation reconciliation

User request: finish all work possible toward a consistent, submission-ready paper.

## Task

Own edits only to `docs/RESEARCH-SUMMARY.md`. Read the whole document and reconcile
its present-tense publication guidance, summary, abstract, conclusions, and figure
inventory with the canonical `manuscript/SPADE-PLOS-ONE.md` and `.planning/STATE.md`.
Preserve the historical numerical analyses and distinguish them explicitly from the
current four main figures. Do not delete historical evidence merely to hide conflict.
Correct active unsupported certificate-validity language directly; a notice at the
top alone is insufficient. Avoid inventing scientific results or citations.

Figure 2 uses a common GP recommender for every arm, with 20,000 screen points,
20 restarts and 4,096 raw starts. Earlier quadratic extrapolation diagnostics are
separate. Prospective maps use a fixed 0.50 cutoff. Prospective certificate counts
measure posterior self-consistency, not oracle containment; no empirical validity
is established even in Hill. 99,601 records means 99,600 scored configurations over
8,300 campaign-arm executions plus one unavailable-design declaration. The later
2,750-row joint protocol returns NO_SELECTION and its lockbox stays unopened.

The main manuscript and current figure exports are the submission authorities;
this file remains historical scientific context. Preserve numerical source tables.
Use targeted edits and no-ai-slop principles. Check all certificate-validity and
figure references in the full file after editing. Run `git diff --check` and any
existing applicable publication-document tests; do not run the full suite.

## Constraints

- You are not alone in the codebase. Do not revert others' edits.
- No commits, pushes, uploads, new experiments, primary-result edits, test-gate changes,
  power planning, or lockbox access.
- Do not edit the manuscript, figure code, README, tests, or any other source file.
- Record the concise implementation and verification report in
  `.planning/publication-docs-report.md`; report DONE or remaining concerns in chat.

## Controller work alongside this task

The main agent is preparing supplementary upload files, submission packaging checks,
and reviewing replay provenance. Author declarations, license approval and DOI cannot
be invented and remain author-controlled.
