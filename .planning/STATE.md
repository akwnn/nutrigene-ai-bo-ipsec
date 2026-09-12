# State

**Milestone:** SPADE joint protocol  
**Status:** stopped at the registered development gate (`NO_SELECTION`)
**Current phase:** Phase 6 publication preparation; Phase 5 lockbox access is blocked
**Last reconciled:** 2026-09-12

## Current handoff

- GitHub backup verified: commit `b91867df5cfb8ce99ee491ce6df9cf659d7d8aa9`
  was pushed to `origin/codex/publication-readiness`; remote SHA matched and the
  repository remained PRIVATE. No main merge, public deposit or submission occurred.
  Remaining external gates: author identity/contributions/declarations and scientific
  signoff, account access, publication-fee plan, and DOI deposit authorization.

- User decision, 2026-09-11: Alana Wai Han Kwan and Joseph Yung jointly own the
  original project code and research materials; MIT and CC BY 4.0 respectively are
  explicitly approved. Root license declarations now record that approval and scope.
  This supersedes historical licensing-pending notes below, but does not finalize
  manuscript authorship, contributions or declarations. No paid assistance is
  authorized; this is not a funding declaration or consent to journal charges.
- User authorizes saving project changes to the existing private GitHub repository.
  Keep `.venv` local and unchanged; it exists only on Alana's computer. Do not change
  repository visibility, submit to the journal, publish a DOI deposit or upload new
  private lab data/credentials. Existing tracked lab history is not rewritten.
  Eight historical replay failures remain unresolved with exact tests and references
  preserved. Author details are the last requested step.
- Licensed r3 archive verification, 2026-09-11: 497 payload files, every hash checked
  after extraction; 109 focused tests passed in the workspace (43.54 s) and extracted
  snapshot using the separate clean-install environment (42.95 s). Nine prospective
  release checks passed in each location without `--pre-release`. Evidence and checksum
  are alongside `results/archival-release/SPADE-code-data-local-draft-2026-09-11-r3.zip`.
  No full-suite or new historical replay run is implied by these focused checks.

This file is the authoritative operational handoff for another agent. The detailed
scientific findings and publication narrative are in `docs/RESEARCH-SUMMARY.md`; the
current paper draft is `manuscript/SPADE-PLOS-ONE.md` with a generated Word counterpart.

- The completed publication evidence body is the prospective study
  `spade-final-2026-08-23`: 99,601 combined records across seven conditions, nine release
  checks passed, and four main publication figures prepared. Its claims must remain separate
  from the newer joint-protocol study.
- On 2026-08-31, a clean temporary runner reconciled the joint-protocol development grid:
  five families, 550 rows per family, and 2,750 rows total. The registered unanimous
  leave-one-family-out selector returned `NO_SELECTION` because every candidate missed
  the prespecified 0.90 empirical-containment floor on at least one family.
- Consequence: no protocol was selected, no power artifact may be created, and the
  lockbox remains `FROZEN_UNOPENED`. Do not inspect lockbox outcomes or claim portable
  cross-family certification from this protocol.
- The publishable contribution is bounded: terminal decision rules can reverse apparent
  BO-versus-RSM rankings; point regret, region-map error, calibration, containment, and
  non-vacuity are distinct estimands; historical SPADE variants improve target-regime
  mapping but do not establish a universal certificate.
- Critical source reconciliation on 2026-09-09: the original prospective map mask uses
  a fixed 0.50 cutoff outside the gamma/alpha loops. Its certificates target latent
  response, and `containment_cell` counts held-out posterior probabilities meeting
  alpha rather than oracle-containment indicators. Original Hill certificate reports
  establish posterior self-consistency only, NOT empirical validity. The scorer and
  analyzer match retained commit `1bf51f11695ae348ffa8993ad42992141558fb80` unchanged.
  Manuscript methods, conclusions, Figure 4B and source notes now disclose this. The
  later joint protocol genuinely targets future-response reliability and remains separate.
  The 99,600 scoring rows represent 8,300 campaign-arm executions repeated over 12
  configurations, not 99,600 independent experiments. Frozen result files were not edited.
- Current verification record: the latest full-suite run overlapped manuscript edits:
  2,437 passed and nine failed (964.86 seconds). Eight are the documented historical
  replay/calibration failures; the ninth loaded an obsolete Figure 2 wording assertion
  before its update. That assertion passes in the fresh final 85-test publication suite
  (42.27 seconds, 2026-09-10). The full suite was not rerun after the final edits and is not all green.
  The scientific requirements digest is restored byte-for-byte;
  manuscript-only dependencies are isolated in `requirements-publication.txt`.
  All nine prospective release checks pass. This is not an all-green repository.
- The manuscript now separates retrospective, prospective, and joint-protocol evidence;
  Table 4 reports the nine-candidate development ranges and `NO_SELECTION`. The five
  development shards and analysis/selection artifacts were restored from commit `502ea39`
  without changing their bytes. Authenticated reanalysis of all 2,750 rows exactly
  reproduced the retained analysis and selection outcome.
- Four main PLOS figures were regenerated with renderer-level label-clearance checks at
  450 and 600 dpi, and visually inspected in color, grayscale, and deuteranopia previews.
  Figure 4D no longer applies independent-binomial intervals to dependent pooled cells;
  these are explicitly descriptive. Figure 4B retains original binomial intervals only
  as model-check diagnostics and discloses the lack of instance-cluster adjustment.
  The full paper was rebuilt as a 40-page illustrated reading copy and a 36-page PLOS
  submission-format copy (captions retained, figures separate), with a separate title
  page and a one-page cover-letter draft. All 77 rendered pages across the three
  documents received visual review; no verified clipping or overlap remains. An initial
  batched-image review reported false footer/line-number collisions, retracted after
  individual full-page inspection. Fresh focused verification:
  85 manuscript/bundle/figure/layout/table/package tests passed. Figure/source hashes are recorded
  in the figure build manifest. The abstract contains 230 whitespace-delimited words.
- Targeted literature/comparator revision on 2026-09-10: 20 sequentially cited references,
  a new Table 5 comparing published studies, and expanded interpretation against
  established straddle, conservative excursion sets, TruVaR, and a 2026 synthetic
  batch-BO study. This is not a systematic review. No specialized-method superiority
  or new acquisition principle is claimed. The paper now highlights one-shot LHS's
  small mean map gap (0.0063), lower mean regret, and fewer rounds; no retained paired
  decision establishes LHS equivalence or SPADE superiority. The Sobol map contrast
  is below the 0.02 practical threshold. Hill inference explicitly uses 25 landscape
  instances with four seeds averaged per instance. No new scientific study was run.
  A regression test first reproduced a detached table-caption problem; the Word
  builder now keeps table captions with their tables. Final visual QA covered all
  pages, reusing only pixel-identical pages from the preceding reviewed render.
- Further source reconciliation: Figure 2 uses a shared GP recommender for every arm
  (20,000-point screen, 20 restarts, 4,096 raw starts), not quadratic RSM. Its source
  replay still differs by 3.88e-7 for one classical campaign; the stored aggregate
  was not replaced. The calibration checkpoint writes successfully, then intentionally
  stops at its map-fidelity gate (worst numeric drift 9.08e-13, no changed latent-map
  cells). Both targeted replay tests still fail; equality gates remain unchanged.
  Matching package versions alone does not establish a code defect as the cause.
  New bundle regressions reject changes to recorded source/data/export hashes and
  stale embedded Word figure bytes. Both Word copies were rebuilt and all page
  contact sheets reviewed, with changed methods, Figure 2, and limitations enlarged.
  Latest temporary renders: `/private/tmp/spade-literature-final-reading/`,
  `/private/tmp/spade-literature-final-submission/`, and `/private/tmp/spade-literature-final-cover/`.
- Latest local upload draft: `manuscript/SPADE-PLOS-ONE-upload-draft-2026-09-10.zip` contains nine
  upload files (submission DOCX, cover-letter DOCX, four TIFF figures, three CSV tables)
  plus a SHA-256 manifest listing outstanding author actions. It is explicitly
  `AUTHOR_REVIEW_REQUIRED`, not a code/data archive, DOI deposit, or journal submission.
  ZIP CRC and all nine source/manifest SHA-256 comparisons pass; 12 unresolved fields
  remain listed. SHA-256: `9d1067c10677a1cdabef58242813f23232f006c1a8182017b1806fe31d523616`.
  The older unversioned ZIP is preserved but superseded and contains the earlier manuscript.
  Packaging rejects stale sources/exports, wrong document modes, and overwrite attempts.
  All three DOCXs have source/builder/output hash sidecars. Supporting tables now preserve
  archived interpretations separately from corrected interpretations, distinguish Hill
  landscape replication from external-function campaigns, and retain tiny nonzero
  p-values in scientific notation. Raw scientific result files and equality gates were
  not changed. `docs/RESEARCH-SUMMARY.md` is reconciled with the current manuscript.
- Submission remains blocked by author/affiliation/contribution/funding/conflict approval,
  scientific signoff on the implementation disclosures,
  study-wide AI-tool disclosure and human review, and a clean public archival snapshot/DOI. Historical
  replay limitations remain disclosed and unresolved; do not weaken equality gates,
  replace reference results, or claim complete campaign regeneration.
- On 2026-09-11, the user requested diagnosis of remaining replay failures and a **local**
  archival draft with no upload; author details are explicitly deferred to the last step.
  Fresh original checks: all five fixed-design/calibration failures reproduced (22.64s),
  and all three adaptive failures reproduced (22.78s). No tests or references changed.
  Commit `01d2ea5` added explicit acquisition sampler seed 0: current and legacy probes
  share initial X/Y/Yvar and GP hashes but diverge at the first acquisition. Restoring
  legacy sampler behavior only recovers the earlier failed replay values, not the
  original references. Original historical root cause remains unresolved. Torch 1/4
  and an Accelerate-thread control did not repair the fixed-design probes. See
  `.planning/debug/replay-adaptive-2026-09-10.md` and `replay-fixed-2026-09-11.md`.
- A safe local packager and test-first exclusion/integrity tests now exist:
  `scripts/prepare_archival_release.py`, `tests/test_archival_release.py`.
  Current local draft: `results/archival-release/SPADE-code-data-local-draft-2026-09-11-r2.zip`,
  495 allowlisted files, SHA-256
  `8afbdb5a8b339ff3b7455fbe9948e66f17183ddf7b6ffa2d76d97783b64a8a9d`.
  It excludes private lab data/code, third-party published data, environments, Git
  history/worktrees, fonts, and lockbox outcomes. All 495 extraction hashes match.
  Final r2 extracted verification: **106 tests passed in 43.55s**, all nine prospective
  release checks passed **without** `--pre-release`, and `boec.__file__` was asserted
  to belong to the extracted source. Existing local dependencies/Arial were used;
  a fresh dependency installation was not tested. ZIP checksum and a structured
  verification sidecar are beside the archive. This does not imply full-suite success.
  Its manifest identifies licensing decisions and full-suite portability limits.
  Five preserved development resume files contain preexisting machine paths; these
  are flagged, not silently rewritten. An example path in the new safety test is also
  flagged. The first local archive is superseded by r2 but preserved. No upload occurred.
- Next scientific step, if historical recovery is pursued, needs the original generating
  environment/dirty-source snapshot or intermediate campaign traces; do not search seeds
  or adjust thresholds to manufacture a passing reference. Code-owner licensing and
  data/manuscript/figure rights decisions remain separate from deferred author details.
  Public deposit/DOI and final submission need later authorization and author review.
  Do not submit placeholders, discard existing worktree changes, or open the lockbox.
- Further completion request on 2026-09-11: user requests all remaining work and asks
  to be consulted for necessary decisions. Fresh-install validation is now complete:
  54 dependencies downloaded uncached from public PyPI into an isolated temporary
  environment; archived package built successfully; 55-package compatibility check
  passes. Extracted r2 source passes 106 publication/archive tests in 67.71s and all
  nine release checks without `--pre-release`. Source import location was asserted.
  The same seven historical tests fail in 89.98s with identical observed values;
  direct fresh-Python P7 execution exits 1 with the same 48 map-field mismatches.
  Its legacy integration test hard-codes `.venv/bin/python`, so direct invocation
  was used to avoid inadvertently exercising the old environment. The original
  scientific references/tests and archive ZIP were not changed. The new clean-install
  verification sidecar is beside r2; prior verification records remain intact.
  Same macOS/ARM host and local Arial, not cross-platform validation or a full-suite run.
- Awaiting user answers: availability/access to original generating environment,
  rights-holder approval of proposed MIT code / CC BY 4.0 materials licensing,
  Zenodo/PLOS destination and account arrangements, publication-fee funding or
  assistance needs. No license or public-upload permission inferred while these
  choices are unresolved. Author details, declarations, scientific/AI disclosure
  approval and final submission approval remain last. GSD resume/debug workflow
  resources are still absent; saved state and systematic debugging were used.
  `.planning/PROJECT.md` was corrected because it still incorrectly said development
  had no outcomes; original unmet scientific success criteria remain labeled unmet.
- User supplied code owners: **Alana Wai Han Kwan and Joseph Yung**. This identifies
  code ownership only; it is not author-order confirmation or explicit approval of
  MIT licensing. Ownership/approval for data, figures and manuscript remains to be
  confirmed. User has no archive/journal accounts yet and asks whether to create them.
  User believes original research files/environments are on this computer, Joseph
  Yung's computer, or both; no exact original environment location is identified yet.
  Preserve older environments/checkouts while locating them; do not reinstall or
  overwrite possible original environments. No account, license, upload or submission
  has been created based solely on these answers.

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Existing families are development-only; four new randomized generators form lockbox.
- Primary target is future-response reliability at gamma 0.95.
- Certificate validation is empirical truth containment, not model-internal non-rejection.
- Development compares exactly three policies by three opening sizes.
- Lockbox success is a four-endpoint conjunction required in every family.
- The tau correction is retained as a per-instance quantile of the gamma-adjusted
  reliability margin, rather than a fixed fraction of peak height or a latent-only
  quantile.
- Replicate-pooled noise estimation is excluded: its oracle-variance regret ceiling
  improved by 0.00816, below the registered 0.01 build bar, and the 48-evaluation budget
  has no replicate reserve.
- OA-LHS is excluded: exact strength-2 construction needs 49 evaluations and the matched
  Hartmann6 study did not reduce design-lottery SD. The opening remains scrambled Sobol.
- Lockbox size is selected only by the frozen held-out LOFO power rule: the first
  `n` in 350..2,000 that passes paired-normal power and exact-confidence
  nonparametric sensitivity for map and regret in all five development families.
  Failure to find such an `n` yields `INSUFFICIENT_POWER` and forbids lockbox access.

## Baseline evidence

On commit `02a6bfa`, the full suite produced 1,676 passed, 9 failed, and 2 skipped.
Two failures were caused by the isolated worktree lacking `.venv`; four were historical
bitwise numerical drift; three were material historical adaptive qLogEI/qLogNEI replay
mismatches already recorded in `.planning/codebase/CONCERNS.md`.

The current implementation produced 2,012 passed, 8 failed, and 2 skipped. All eight
failures were rerun in isolation and reproduced from an archive of pre-SPADE commit
`02a6bfa` using the same environment: one historical calibration stop-gate, four
historical exact-float replay drifts, and three historical stochastic qLogEI/qLogNEI
replay mismatches. They are therefore baseline reproducibility debt rather than SPADE
regressions and are not being repaired inside the prospective study branch.

## Completed in this milestone

- Task 1 deterministic seed/noise/checkpoint/replay foundations passed independent review.
  The focused post-merge suite is 186 passed with two third-party deprecation warnings.
- Checkpoints now reject oracle/configuration/noise/cursor mismatches and preserve legacy
  RNG state for byte-identical resume.
- The committed tau-quantile, oracle-noise ceiling, and OA-LHS design-lottery evidence from
  `origin/main` is merged into this branch.
- Task 2 common learned-noise GP, explicitly seeded qLogNEI, and Schur-updated IVR passed
  independent numerical review. The focused suite is 96 passed, including randomized
  brute-force conditioning and extreme-weight tests.
- Task 3 predictive reliable-region and split certificate passed independent review. The
  focused suite is 80 passed; joint draws are deterministic without global RNG mutation,
  gamma-aware, split-isolated, and empirically scored with exact confidence bounds.
- Task 4 unified SPADE/Sobol48/qLogNEI48 runners passed independent review: exact 48-point
  budgets, no truth access, frozen registered constants, identity-bound thresholds and
  schedules, RNG isolation, and non-scientific TEST_ONLY execution identities.
- Task 5 lockbox generators/common scorer passed independent review. All live digests
  match, controlled thresholds achieve 25% prevalence, scorer refits all 48 observations,
  and the manifest remains `FROZEN_UNOPENED` with no comparative outcomes inspected.
- Task 6 resumable development runner and unanimous leave-one-family-out selector passed
  independent adversarial review. Exact shard names, write-once selection artifacts,
  tamper-resistant resume, and all five fold gates are enforced.
- The first development launch exposed a pre-analysis adapter-contract mismatch before
  any result shard existed: legacy `UnitScaled` floors are sampled rather than hard
  bounds. The aborted Hill/Rosenbrock checkpoints were isolated and never reused, and no
  comparative outcome was inspected. Truth-range contracts are now named and digest
  bound: Hill and lockbox are strict `[0,1]`; the four historical external families allow
  finite negative tails without clipping but still enforce an upper bound of one. The
  focused suite is 103 passed and the broader relevant suite is 171 passed; independent
  re-review found no remaining issue.
- The next clean launch exposed a registered-scale implementation bottleneck before any
  IVR row completed: the dense path materialized an 18,432-square covariance (about
  2.7 GB per process). Five one-row, qLogNEI-only checkpoints were isolated without
  reading metrics and will not be reused. IVR now evaluates exact posterior covariance
  in deterministic 1,024-candidate blocks and applies the same sequential Schur updates.
  It selected identical points to an independent dense reference on five randomized
  positive-definite cases, completed the real 16,384-candidate/2,048-reference shape in
  2.061 seconds, and passed 174 focused compatibility tests.
- Task 7 guarded lockbox execution, manifest-driven confirmatory analysis, and the
  fail-closed release validator passed final independent adversarial review. Hashes are
  byte-bound in disjoint namespaces; every shard has an exact registered filename,
  completion/count/command/provenance contract, and local family/key/arm grid; malformed
  numeric or deeply nested JSON becomes a written FAIL report; publication is write-once
  with the completion manifest installed last. The final relevant suite is 275 passed
  with two pre-existing Torch deprecation warnings, and the reviewer reported no
  Critical, Important, or Minor findings.
- The pre-lockbox power system is fully implemented through release validation. It
  authenticates exact committed held-out development bytes, recomputes the selected
  LOFO analysis, writes one immutable power artifact, derives every lockbox range and
  count from its decision, and binds the same power hash/source through shard, merge,
  analysis, and release. Symlink/path-swap races and post-outcome code reinterpretation
  are rejected before outcome readers or oracle construction can run.
- Lockbox execution supports any number of disjoint cross-host shards with exact
  no-gap/no-overlap coverage. Full host provenance is retained per row while a frozen
  science-affecting environment identity permits different virtualenv paths on
  compatible hosts. The focused end-to-end suite is 262 passed with two pre-existing
  Torch deprecation warnings. After final immutable metadata/read/write and source-blob
  fixes, the two touched lockbox/release modules passed 90 tests with the same two
  warnings. At that implementation checkpoint, no development or lockbox outcome had
  been run or opened; the later development result is recorded in the current handoff
  above and the lockbox remains unopened.

## Chronological work log

Joseph final evidence was selectively ported into this checkout on 2026-08-29: LC, TAU,
ACK adjudicators/specifications, result packages, and the backwards-compatible
multi-round helper are available for reproducible analysis. The registered B5 digest and
the active `spade-campaign` worktree remain untouched. LC is bounded/inconclusive at the
all-family regret SESOI edge; TAU-1 and TAU-2 pass; ACK-1 fails and its fixed-theta cause
is withdrawn. These results must remain separate from the registered product arm.

Mean-marginalised GP covariance is now enabled in the manufacturing CQA qualification
and benchmark paths. It propagates constant-mean uncertainty without changing the
registered product scorer's defaults. Focused implementation validation is 137 passed;
the three-family smoke benchmark produced 100% joint containment for aligned and
moderate-conflict families and correctly abstained on strong conflict.
The attempted 25-replicate/2-seed, 4,096-grid rerun was stopped after several minutes
during GP fitting; it produced no accepted artifact and does not alter registered results.
Development/merge/multi-round compatibility validation subsequently passed 62 tests;
the registered full grid remains intentionally unrun from this dirty publication
checkout because its provenance contract requires a clean source commit.
A clean archived snapshot was initialized with an immutable local commit and completed
the first registered Hill shard (11 rows, `source_dirty=false`); it is preserved under
`results/verified-clean-snapshot/` as provenance-separated verification evidence, not
mixed into the official development grid because its source commit is the archive
snapshot rather than the eventual release commit.
The same clean snapshot also completed first-key registered shards for Ackley,
Hartmann6, Levy, and Rosenbrock (11 rows each; all `source_dirty=false`). These are
runner/provenance verification only, not comparative selection evidence.
The mean-marginalised multi-CQA medium replication (10 replicates × 2 seeds, 1,024-grid)
returned 100% joint containment and 100% non-empty rate for aligned and moderate-conflict
families, and 0% non-empty with safe abstention for strong conflict. This is a robustness
replication, not the frozen 25-replicate/4,096-grid registration.
The five clean first-key development shards contain only 11 scored rows per family;
their observed certificate outcomes are retained for runner verification only and are
explicitly excluded from the ≥50%/≥90% comparative gate because the registered
confidence rule requires the complete development sample.
The merge validator was exercised against a partial clean shard and failed closed with
`development shard ranges do not cover exact interval [0,50)`, confirming incomplete
evidence cannot be promoted.
The clean snapshot then completed Hill campaigns 1–4 as a second registered shard
(44/44 rows, `source_dirty=false`), bringing Hill runner verification to five campaign
keys while remaining clearly below the complete selection sample.
It also completed Hill campaigns 5–9 (55/55 rows, `source_dirty=false`), bringing the
clean runner verification to ten Hill campaign keys and 110 Hill rows. These shards are
still not promoted as final selection evidence until all 50 keys and all families exist.
Hill campaigns 10–14 are now complete as a third authenticated shard (55/55 rows,
`source_dirty=false`), covering 15 of 50 Hill campaign keys and 165 Hill rows total.
Hill campaigns 15–19 completed as a fourth authenticated shard (55/55 rows,
`source_dirty=false`), covering 20 of 50 Hill campaign keys and 220 Hill rows total.
Hill campaigns 20–24 completed as a fifth authenticated shard (55/55 rows,
`source_dirty=false`), covering 25 of 50 Hill campaign keys and 275 Hill rows total.
Hill campaigns 25–29 completed as a sixth authenticated shard (55/55 rows,
`source_dirty=false`), covering 30 of 50 Hill campaign keys and 330 Hill rows total.
Hill campaigns 30–34 completed as a seventh authenticated shard (55/55 rows,
`source_dirty=false`), covering 35 of 50 Hill campaign keys and 385 Hill rows total.
Hill campaigns 40–44 completed as a ninth authenticated shard (55/55 rows,
`source_dirty=false`), covering 45 of 50 Hill campaign keys and 495 Hill rows total.
The final Hill merge from that archived snapshot completed with 550 rows. The row field
`arm="spade"` is intentionally shared by SPADE candidates; validation through each
`arm_protocol_digest` confirms all 11 registered arms and all 50 campaign keys. It is
therefore a valid family-complete development artifact, but remains provenance-separated
until the eventual release commit is fixed (its clean snapshot commit is recorded in
the manifest).
Independent audit confirms 11 unique arm protocol digests and 50 unique campaign keys
in the merged Hill artifact. Its raw per-arm answer rates are 0.98–1.00, while the
50-campaign empirical containment fractions remain below 0.90 for every SPADE variant;
these are descriptive diagnostics and do not satisfy the registered lower-bound gate.
Hill campaigns 35–39 completed as an eighth authenticated shard (55/55 rows,
`source_dirty=false`), covering 40 of 50 Hill campaign keys and 440 Hill rows total.

Current verification checkpoint (2026-08-30): the focused post-integration suite for
development, merge validation, reliable-region, and manufacturing qualification passes
115 tests. The full repository suite passes 2,406 tests and reproduces the eight
previously documented baseline failures (one calibration stop-gate, four historical
exact-float drifts, and three historical qLogEI/qLogNEI replay mismatches); none is in
the newly integrated Joseph/CQA path. No registered outcome artifact was altered by
this verification.
The selection CLI was also exercised against the preserved five-family/ Hill artifacts;
it failed closed with `protocol selection refuses a dirty source tree`, as required, and
wrote no analysis or selected-protocol artifact.
The current clean snapshot then completed Ackley campaigns 1–4 (44/44 rows) and 5–9
(55/55 rows), each with `source_dirty=false` and authenticated manifests. Together with
the prior Ackley first-key shard, this covers 10 of 50 Ackley campaign keys; these partial
results remain verification evidence only and are not eligible for protocol selection.
Ackley campaigns 10–14 then completed as another authenticated 55-row shard from clean
source commit `a502d3d`; Ackley coverage is now 15 of 50 campaign keys. The shard is
preserved in the current-clean verification archive and remains non-selectable until the
full five-family grid is complete.
Ackley campaigns 15–19 completed as a further authenticated 55-row shard from clean
source commit `b251ab4`; Ackley coverage is now 20 of 50 campaign keys. It is preserved
in the same archive and remains excluded from selection until all registered families and
keys are present.
Ackley campaigns 20–24 completed as another authenticated 55-row shard from clean
source commit `d6367f0`; Ackley coverage is now 25 of 50 campaign keys. It is preserved
in the same archive and remains excluded from selection until the complete five-family
grid is available.
Ackley campaigns 25–29 completed as an authenticated 55-row shard from clean source
commit `77b577a`; Ackley coverage is now 30 of 50 campaign keys. The artifact and its
resume chain are preserved in the current-clean verification archive and remain excluded
from selection until all families are complete.
Ackley campaigns 30–34 completed as an authenticated 55-row shard from clean source
commit `01e3e80`; Ackley coverage is now 35 of 50 campaign keys. The artifact is preserved
in the current-clean verification archive and remains excluded from selection until the
full five-family grid is available.
Ackley campaigns 35–39 completed as an authenticated 55-row shard from clean source
commit `a671491`; Ackley coverage is now 40 of 50 campaign keys. The artifact and hashes
are preserved in the current-clean verification archive and remain excluded from selection
until the full five-family grid is available.
Ackley campaigns 40–49 completed as an authenticated 110-row shard from clean source
commit `5f8a12b`; Ackley now has complete 50/50 campaign-key coverage (550 rows total)
in the clean snapshot. The artifact remains provenance-separated and non-selectable until
the other four families are complete under the same release source identity.
Hartmann6 campaigns 0–4 completed as an authenticated 55-row shard from clean source
commit `1032e01`; this begins current clean Hartmann6 coverage (5 of 50 campaign keys).
The artifact is preserved in the verification archive and remains non-selectable until
the remaining Hartmann6 keys and other families are complete.
Hartmann6 campaigns 5–9 completed as an authenticated 55-row shard from clean source
commit `dfaa227`; Hartmann6 coverage is now 10 of 50 campaign keys. The artifact and
hashes are preserved in the verification archive and remain excluded from selection.
Hartmann6 campaigns 10–14 completed as an authenticated 55-row shard from clean source
commit `363a571`; Hartmann6 coverage is now 15 of 50 campaign keys. The artifact is
preserved in the verification archive and remains excluded from selection pending full
five-family coverage.
Hartmann6 campaigns 15–19 completed as an authenticated 55-row shard from clean source
commit `26dd83e`; Hartmann6 coverage is now 20 of 50 campaign keys. The artifact and
hashes are preserved in the verification archive and remain excluded from selection.
Hartmann6 campaigns 20–24 completed as an authenticated 55-row shard from clean source
commit `e235221`; Hartmann6 coverage is now 25 of 50 campaign keys. The artifact is
preserved in the verification archive and remains excluded from selection pending the
complete five-family grid.
Hartmann6 campaigns 25–29 completed as an authenticated 55-row shard from clean source
commit `dd167df`; Hartmann6 coverage is now 30 of 50 campaign keys. The artifact and
hashes are preserved in the verification archive and remain excluded from selection.
Hartmann6 campaigns 30–34 completed as an authenticated 55-row shard from clean source
commit `03578e6`; Hartmann6 coverage is now 35 of 50 campaign keys. The artifact is
preserved in the verification archive and remains excluded from selection pending the
complete five-family grid.
Hartmann6 campaigns 35–39 completed as an authenticated 55-row shard from clean source
commit `342e052`; Hartmann6 coverage is now 40 of 50 campaign keys. The artifact and
hashes are preserved in the verification archive and remain excluded from selection.
Hartmann6 campaigns 40–49 completed as an authenticated 110-row shard from clean source
commit `cee8bf3`; Hartmann6 now has complete 50/50 campaign-key coverage (550 rows total)
in the clean snapshot. The artifact remains provenance-separated and non-selectable until
Levy, Rosenbrock, and Hill are complete under the same release workflow.
Levy campaigns 0–4 completed as an authenticated 55-row shard from clean source commit
`f4c39ed`; this begins current clean Levy coverage (5 of 50 campaign keys). The artifact
is preserved in the verification archive and remains excluded from selection.
Levy campaigns 5–9 completed as an authenticated 55-row shard from clean source commit
`4e3c5f2`; Levy coverage is now 10 of 50 campaign keys. The artifact and hashes are
preserved in the verification archive and remain excluded from selection.
Levy campaigns 10–14 completed as an authenticated 55-row shard from clean source
commit `d9dd992`; Levy coverage is now 15 of 50 campaign keys. The artifact is preserved
in the verification archive and remains excluded from selection pending full coverage.
Levy campaigns 15–19 completed as an authenticated 55-row shard from clean source
commit `cffbac2`; Levy coverage is now 20 of 50 campaign keys. The artifact and hashes
are preserved in the verification archive and remain excluded from selection.
Levy campaigns 20–24 completed as an authenticated 55-row shard from clean source
commit `593452a`; Levy coverage is now 25 of 50 campaign keys. The artifact is preserved
in the verification archive and remains excluded from selection pending full coverage.
Levy campaigns 25–29 completed as an authenticated 55-row shard from clean source
commit `0de7156`; Levy coverage is now 30 of 50 campaign keys. The artifact and hashes
are preserved in the verification archive and remain excluded from selection.
Levy campaigns 30–34 completed as an authenticated 55-row shard from clean source
commit `6a15998`; Levy coverage is now 35 of 50 campaign keys. The artifact is preserved
in the verification archive and remains excluded from selection pending full coverage.
Levy campaigns 35–39 completed as an authenticated 55-row shard from clean source
commit `0d13951`; Levy coverage is now 40 of 50 campaign keys. The artifact and hashes
are preserved in the verification archive and remain excluded from selection.
Levy campaigns 40–49 completed as an authenticated 110-row shard from clean source
commit `2d6bcc7`; Levy now has complete 50/50 campaign-key coverage (550 rows total)
in the clean snapshot. The artifact remains provenance-separated and non-selectable until
Rosenbrock and Hill are complete under the same release workflow.

Rosenbrock campaigns 0–4 completed as an authenticated 55-row shard from clean source
commit `2d6bcc7`; this begins current clean Rosenbrock coverage (5 of 50 campaign keys).
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaigns 5–9 completed as an authenticated 55-row shard from clean source
commit `c0394df`; Rosenbrock coverage is now 10 of 50 campaign keys. The artifact and
hashes are preserved in the verification archive and remain excluded from selection.
Rosenbrock campaign 10 completed as an authenticated 11-row registered shard from clean
source commit `1362bec`; current clean Rosenbrock coverage is now 11 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 11 completed as an authenticated 11-row registered shard from clean
source commit `26aff94`; current clean Rosenbrock coverage is now 12 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 12 completed as an authenticated 11-row registered shard from clean
source commit `ca04afa`; current clean Rosenbrock coverage is now 13 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 13 completed as an authenticated 11-row registered shard from clean
source commit `76fb815`; current clean Rosenbrock coverage is now 14 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 14 completed as an authenticated 11-row registered shard from clean
source commit `9751d11`; current clean Rosenbrock coverage is now 15 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 15 completed as an authenticated 11-row registered shard from clean
source commit `2dea756`; current clean Rosenbrock coverage is now 16 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 16 completed as an authenticated 11-row registered shard from clean
source commit `37d807e`; current clean Rosenbrock coverage is now 17 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 17 completed as an authenticated 11-row registered shard from clean
source commit `7bc7ba2`; current clean Rosenbrock coverage is now 18 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 18 completed as an authenticated 11-row registered shard from clean
source commit `408e991`; current clean Rosenbrock coverage is now 19 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 19 completed as an authenticated 11-row registered shard from clean
source commit `87fb818`; current clean Rosenbrock coverage is now 20 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 20 completed as an authenticated 11-row registered shard from clean
source commit `8cb8ad6`; current clean Rosenbrock coverage is now 21 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 21 completed as an authenticated 11-row registered shard from clean
source commit `1672c14`; current clean Rosenbrock coverage is now 22 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 22 completed as an authenticated 11-row registered shard from clean
source commit `5dcf1f2`; current clean Rosenbrock coverage is now 23 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 23 completed as an authenticated 11-row registered shard from clean
source commit `9cd9728`; current clean Rosenbrock coverage is now 24 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 24 completed as an authenticated 11-row registered shard from clean
source commit `c4b2cba`; current clean Rosenbrock coverage is now 25 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 25 completed as an authenticated 11-row registered shard from clean
source commit `d72d582`; current clean Rosenbrock coverage is now 26 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 26 completed as an authenticated 11-row registered shard from clean
source commit `6e4d347`; current clean Rosenbrock coverage is now 27 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 27 completed as an authenticated 11-row registered shard from clean
source commit `d04ac70`; current clean Rosenbrock coverage is now 28 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 28 completed as an authenticated 11-row registered shard from clean
source commit `660bccf`; current clean Rosenbrock coverage is now 29 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 29 completed as an authenticated 11-row registered shard from clean
source commit `da656b0`; current clean Rosenbrock coverage is now 30 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 30 completed as an authenticated 11-row registered shard from clean
source commit `23917dc`; current clean Rosenbrock coverage is now 31 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 31 completed as an authenticated 11-row registered shard from clean
source commit `1bf996e`; current clean Rosenbrock coverage is now 32 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 32 completed as an authenticated 11-row registered shard from clean
source commit `6c998c1`; current clean Rosenbrock coverage is now 33 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 33 completed as an authenticated 11-row registered shard from clean
source commit `dbdba30`; current clean Rosenbrock coverage is now 34 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 34 completed as an authenticated 11-row registered shard from clean
source commit `7390c85`; current clean Rosenbrock coverage is now 35 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 35 completed as an authenticated 11-row registered shard from clean
source commit `21da57b`; current clean Rosenbrock coverage is now 36 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 36 completed as an authenticated 11-row registered shard from clean
source commit `0f2a106`; current clean Rosenbrock coverage is now 37 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 37 completed as an authenticated 11-row registered shard from clean
source commit `e2d190b`; current clean Rosenbrock coverage is now 38 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 38 completed as an authenticated 11-row registered shard from clean
source commit `b9570fe`; current clean Rosenbrock coverage is now 39 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 39 completed as an authenticated 11-row registered shard from clean
source commit `bab3536`; current clean Rosenbrock coverage is now 40 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 40 completed as an authenticated 11-row registered shard from clean
source commit `b54edef`; current clean Rosenbrock coverage is now 41 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 41 completed as an authenticated 11-row registered shard from clean
source commit `aee1bcb`; current clean Rosenbrock coverage is now 42 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 42 completed as an authenticated 11-row registered shard from clean
source commit `72ae104`; current clean Rosenbrock coverage is now 43 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 43 completed as an authenticated 11-row registered shard from clean
source commit `b5a36a0`; current clean Rosenbrock coverage is now 44 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 44 completed as an authenticated 11-row registered shard from clean
source commit `5905e05`; current clean Rosenbrock coverage is now 45 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 45 completed as an authenticated 11-row registered shard from clean
source commit `42cec8c`; current clean Rosenbrock coverage is now 46 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 46 completed as an authenticated 11-row registered shard from clean
source commit `fb77b80`; current clean Rosenbrock coverage is now 47 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 47 completed as an authenticated 11-row registered shard from clean
source commit `de2533f`; current clean Rosenbrock coverage is now 48 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 48 completed as an authenticated 11-row registered shard from clean
source commit `09902e1`; current clean Rosenbrock coverage is now 49 of 50 campaign keys.
The artifact and hashes are preserved in the verification archive and remain excluded
from selection pending full coverage.
Rosenbrock campaign 49 completed as an authenticated 11-row registered shard from clean
source commit `0986fe2`; Rosenbrock now has complete 50/50 campaign-key coverage (550
rows total) in the clean snapshot. The artifact remains provenance-separated and
non-selectable until current clean Hill coverage is complete.
Hill campaign 1 completed as an authenticated 11-row registered shard from clean source
commit `cd768dc`; current clean Hill coverage is now 2 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 2 completed as an authenticated 11-row registered shard from clean source
commit `7a7bc12`; current clean Hill coverage is now 3 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 3 completed as an authenticated 11-row registered shard from clean source
commit `ab5a5d6`; current clean Hill coverage is now 4 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 4 completed as an authenticated 11-row registered shard from clean source
commit `8446094`; current clean Hill coverage is now 5 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 5 completed as an authenticated 11-row registered shard from clean source
commit `195e169`; current clean Hill coverage is now 6 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 6 completed as an authenticated 11-row registered shard from clean source
commit `a63cde1`; current clean Hill coverage is now 7 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 7 completed as an authenticated 11-row registered shard from clean source
commit `8b93682`; current clean Hill coverage is now 8 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 8 completed as an authenticated 11-row registered shard from clean source
commit `769cdfb`; current clean Hill coverage is now 9 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 9 completed as an authenticated 11-row registered shard from clean source
commit `d2f2aba`; current clean Hill coverage is now 10 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 10 completed as an authenticated 11-row registered shard from clean source
commit `34ddee5`; current clean Hill coverage is now 11 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 11 completed as an authenticated 11-row registered shard from clean source
commit `f503804`; current clean Hill coverage is now 12 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 12 completed as an authenticated 11-row registered shard from clean source
commit `f198dfd`; current clean Hill coverage is now 13 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 13 completed as an authenticated 11-row registered shard from clean source
commit `505755f`; current clean Hill coverage is now 14 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 14 completed as an authenticated 11-row registered shard from clean source
commit `f9fb6c7`; current clean Hill coverage is now 15 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 15 completed as an authenticated 11-row registered shard from clean source
commit `54e1193`; current clean Hill coverage is now 16 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 16 completed as an authenticated 11-row registered shard from clean source
commit `4c8d922`; current clean Hill coverage is now 17 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 17 completed as an authenticated 11-row registered shard from clean source
commit `bd28b59`; current clean Hill coverage is now 18 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 18 completed as an authenticated 11-row registered shard from clean source
commit `fe8a316`; current clean Hill coverage is now 19 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 19 completed as an authenticated 11-row registered shard from clean source
commit `095e0fa`; current clean Hill coverage is now 20 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 20 completed as an authenticated 11-row registered shard from clean source
commit `71ac2ed`; current clean Hill coverage is now 21 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 21 completed as an authenticated 11-row registered shard from clean source
commit `228cc8d`; current clean Hill coverage is now 22 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 22 completed as an authenticated 11-row registered shard from clean source
commit `012d28e`; current clean Hill coverage is now 23 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 23 completed as an authenticated 11-row registered shard from clean source
commit `bd44622`; current clean Hill coverage is now 24 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 24 completed as an authenticated 11-row registered shard from clean source
commit `ae5416d`; current clean Hill coverage is now 25 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 25 completed as an authenticated 11-row registered shard from clean source
commit `b4c76ba`; current clean Hill coverage is now 26 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 26 completed as an authenticated 11-row registered shard from clean source
commit `8bdf84e`; current clean Hill coverage is now 27 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 27 completed as an authenticated 11-row registered shard from clean source
commit `8a20c68`; current clean Hill coverage is now 28 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 28 completed as an authenticated 11-row registered shard from clean source
commit `4c9aeb4`; current clean Hill coverage is now 29 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 29 completed as an authenticated 11-row registered shard from clean source
commit `f118642`; current clean Hill coverage is now 30 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 30 completed as an authenticated 11-row registered shard from clean source
commit `166253d`; current clean Hill coverage is now 31 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 31 completed as an authenticated 11-row registered shard from clean source
commit `3f37597`; current clean Hill coverage is now 32 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 32 completed as an authenticated 11-row registered shard from clean source
commit `d065398`; current clean Hill coverage is now 33 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 33 completed as an authenticated 11-row registered shard from clean source
commit `07b4627`; current clean Hill coverage is now 34 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 34 completed as an authenticated 11-row registered shard from clean source
commit `68b4210`; current clean Hill coverage is now 35 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 35 completed as an authenticated 11-row registered shard from clean source
commit `3e2f4ed`; current clean Hill coverage is now 36 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 36 completed as an authenticated 11-row registered shard from clean source
commit `dedd08a`; current clean Hill coverage is now 37 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 37 completed as an authenticated 11-row registered shard from clean source
commit `cdbaec0`; current clean Hill coverage is now 38 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 38 completed as an authenticated 11-row registered shard from clean source
commit `005dfe4`; current clean Hill coverage is now 39 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.
Hill campaign 39 completed as an authenticated 11-row registered shard from clean source
commit `5989004`; current clean Hill coverage is now 40 of 50 campaign keys. The artifact
and hashes are preserved in the verification archive and remain excluded from selection.

Historical plan before the registered development result: complete and verify the
logistics-only distributed-execution freeze, push that exact clean source commit, then
execute the development campaign grid and apply the prespecified unanimous
leave-one-family-out selection. Only after a committed `SELECTED` protocol could the
planner create a power artifact or authorize lockbox access. Historical final-SPADE raw
artifacts remain provenance-separated from the new joint-protocol outcomes. This plan was
superseded by the `NO_SELECTION` result recorded below.

On 2026-08-31, a clean temporary runner reconciled the archived shards without altering
their raw files: all five families validated at 2,750 rows, with a ledger retaining each
parent manifest/hash and original source commit. The registered selector then ran against
that reconciled grid and returned `NO_SELECTION`: every candidate failed the prespecified
0.90 empirical-containment floor on at least one family. This is an honest gate failure,
not evidence to rewrite or relabel; the next improvement must change the certified-region
method and be validated on a fresh registered grid before any SUCCESS claim.

The expanded handoff validation on 2026-08-31 passed 166 focused tests covering development
shards/selection, lockbox provenance, manufacturing qualification, and reliable-region
behavior (two known Torch deprecation warnings only). No registered B5 artifact was changed.

An opt-in `campaign_latent_inflation` diagnostic was added to `boec.selfcalib`. It derives
a conservative multiplier from noise-inclusive leave-one-out residual tails, validates its
inputs, and leaves the registered scorer unchanged until a protocol explicitly registers
the multiplier. Its focused tests pass (9/9).
