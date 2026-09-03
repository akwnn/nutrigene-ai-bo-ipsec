# Publication-ready SPADE manuscript package design

## Objective

Turn the current publication-first repository into a coherent, submission-oriented scientific
package. The package must explain the problem, method, benchmarks, novelty, results, adverse
findings, evidence boundaries, and reproduction path without overstating the authoritative
claim ledger. It must also make the active codebase understandable to an external reviewer.

## Governing principles

1. `publication/manuscript/CLAIMS-AND-SOURCES.md` remains authoritative for every quantitative
   conclusion. Narrative wording may become clearer but may not become stronger.
2. The main manuscript tells a focused scientific story. Exhaustive technical, negative,
   historical, and provenance detail belongs in Methods, Supplement, and evidence documents.
3. Current, exploratory, superseded, withdrawn, and future work must be labeled explicitly.
4. Novelty must be separated into standard ingredients, adaptations, and genuinely new
   contributions. Literature claims require primary-source support.
5. Every central result must be traceable to committed data, an analysis command, and a claim
   guard or clearly identified validation route.
6. No prospective biological validation claim may be inferred from retrospective real-cell
   analyses.
7. Existing unrelated user changes must be preserved. One commit will be created only after
   the complete package passes review and verification.

## Deliverables

### 1. Main manuscript

Revise `publication/manuscript/MANUSCRIPT.md` into a journal-style article containing:

- a precise title, structured scientific narrative, keywords, and bounded abstract;
- literature-grounded motivation for operating-region certification under fixed well and
  round budgets;
- an explicit contributions/novelty statement distinguishing established GP, BO, DoE,
  excursion-set, and calibration ideas from SPADE's integration and evaluation;
- a concise but complete study-design overview;
- figure and table callouts tied to repository assets or source tables;
- results organized by pre-specified scientific questions, including adverse and null results;
- a discussion that compares optimization, certification, abstention, and operational cost;
- limitations, data/code availability, and an explicit checklist of declarations that must
  be supplied by the authors or selected journal when repository evidence cannot establish
  them; and
- a verified reference list using primary sources wherever possible.

No unsupported effect size, equivalence claim, wet-lab claim, or generalized comparator claim
may be introduced.

### 2. Detailed Methods

Expand `publication/manuscript/METHODS.md` so an informed reader can reconstruct:

- response families, dimensionality, normalization, instance generation, truth grids, and
  observation-noise model;
- well budgets, batch schedules, rounds, seeds, target prevalences, and assurance criteria;
- SPADE fitting, acquisition, uncertainty inflation, joint-draw certification, and abstention;
- qLogNEI, screened DoE, unscreened DoE, and one-shot LHS comparators;
- DC, LC, LA, TAU, and TT experiment roles and the distinction between development and
  confirmatory evidence;
- paired estimands, bootstrap intervals, exact binomial bounds, selection rules, and smallest
  effect of interest;
- retrospective real-data processing and its evidentiary limits; and
- software environment, deterministic seeds, canonical inputs, outputs, and verification.

Method detail must be derived from active configs, runners, analyzers, tests, and canonical
result schemas rather than historical prose alone.

### 3. Supplement and structured tables

Expand `publication/manuscript/SUPPLEMENT.md` with compact, auditable tables for:

- the complete benchmark and comparator matrix;
- all allowed central and supporting claims;
- negative, null, withdrawn, and superseded findings;
- family/prevalence certification interpretation;
- real-cell support and gating/calibration limitations;
- tested versus untested scope; and
- figure inventory and data provenance.

Where a large machine-readable table is more appropriate, create it under
`publication/evidence/` and link it from the Supplement.

### 4. Claim-to-code traceability

Strengthen `publication/manuscript/CLAIMS-AND-SOURCES.md` and
`publication/evidence/reproduction-map.md` only where traceability is incomplete. Each paper
claim should identify canonical inputs, producing or analyzing code, expected result, and a
guard or validation step. Corrections must retain the superseded value and explain why it is
rejected.

### 5. Publication-ready repository documentation

Rewrite the root `README.md` as a scientific landing page rather than a directory list. It
must state:

- the research question and bounded answer;
- what SPADE adds and what components are standard;
- headline findings with essential denominators and limitations;
- the distinction between the active publication path and archived research history;
- an external-reviewer reading order;
- exact quick verification and fuller reproduction routes;
- repository structure, data status, figure status, citation, and license constraints.

Supporting README files in active `publication/`, `research/`, and `software/` paths will be
audited and revised when they are misleading, skeletal, or fail to identify canonical status.
Archive files will not be rewritten merely for style.

### 6. Repository publication audit

Audit the active tree for:

- broken or stale paths after reorganization;
- claims or numbers inconsistent with the ledger;
- undocumented scripts, configs, result families, or figure assets;
- missing provenance and status labels;
- citation metadata, license notice, dependency/install instructions, and data-governance
  caveats;
- generated clutter or misleading `final` naming; and
- tests and workflows that no longer match the publication layout.

Repair in-scope blockers. Record genuine journal-, author-, or owner-dependent items clearly
instead of inventing values.

## Research-agent workflow

After this design is approved, independent research agents will examine:

1. primary literature and novelty boundaries for GP excursion sets, level-set estimation,
   noisy BO/qLogNEI, classical response-surface DoE, calibration, and abstention;
2. the full active code/config/result pipeline and benchmark semantics;
3. manuscript-to-evidence consistency, including missing caveats and superseded claims; and
4. publication and reproducibility readiness across metadata, licensing, data status,
   documentation, and automated checks.

Agent outputs are advisory. Final prose will be reconciled against primary sources, active
code, canonical results, and the claim ledger before inclusion.

## Verification and acceptance criteria

The package is complete when:

- every quantitative statement in the main paper maps to the claim ledger;
- all literature-positioning statements have verified primary citations;
- benchmark designs and comparator budgets agree across manuscript, Methods, configs, and
  analyzers;
- every figure/table callout resolves to an included asset or table;
- current versus archived/superseded evidence is unambiguous;
- manuscript links and repository-internal paths pass automated checks;
- the conclusion guard, repository audit, and relevant test suite pass;
- a fresh-reader audit can identify what is new, what is standard, what was tested, what
  failed, and what remains unvalidated without opening historical files;
- `git diff --check` passes and the final diff contains no unrelated changes; and
- exactly one final commit records the completed publication package.

## Out of scope

- inventing missing biological validation, author contributions, funding, conflicts, ethics
  approvals, or a journal-specific format;
- rerunning expensive campaigns solely to enlarge the claim set;
- promoting exploratory or archived outputs to canonical evidence without a new protocol;
- changing scientific conclusions merely to make the paper sound stronger; and
- deleting historical evidence or unrelated local work.
