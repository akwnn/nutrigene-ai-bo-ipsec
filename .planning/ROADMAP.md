# Roadmap

## Phase 1 — Freeze and foundations — COMPLETE

Write the governing design and implementation plan, isolate the branch, repair
deterministic seed/checkpoint foundations, and classify historical replay failures.

Requirements: REP-01, REP-04.

## Phase 2 — Joint SPADE method — COMPLETE

Implement the common learned-noise GP, deterministic discrete qLogNEI, IVR acquisitions,
whole-batch allocation, 48-evaluation SPADE orchestration, and common comparator paths.

Requirements: METH-01 through METH-04.

## Phase 3 — Predictive certification — COMPLETE

Implement controlled-prevalence thresholding, future-response reliability maps,
gamma-aware set draws, split conservative regions, exact confidence bounds, and common
map/regret/certificate scoring.

Requirements: CERT-01 through CERT-05.

## Phase 4 — Development selection — COMPLETE (`NO_SELECTION`)

The registered nine-candidate development grid was reconciled across all five families
(2,750 rows). The unanimous leave-one-family-out selector returned `NO_SELECTION` because
every candidate missed the 0.90 empirical-containment floor on at least one family.

Requirement: EVAL-01.

## Phase 5 — Lockbox evidence — BLOCKED AND UNOPENED

The implementation and frozen generators exist, but Phase 4 produced no selected protocol.
No power artifact may be created and the lockbox must remain `FROZEN_UNOPENED`. A future
attempt requires a materially revised certificate method and a fresh registered
development grid; the failed protocol cannot be relabeled or promoted.

Requirements: EVAL-02 through EVAL-04, REP-02.

## Phase 6 — Publication release — ACTIVE WITH BOUNDED CLAIMS

2026-09-12 replay disposition: claim-impact audit completed, not replay repair.
Main numerical findings remain analyses of the retained regenerated benchmark;
old failing adaptive columns are excluded from ranking support and the sampler
version boundary is explicit. Exact failure gates remain unchanged. 116 focused
tests and nine release checks pass; eight historical checks still fail. Updated
Word documents have full visual coverage (79 pages, 62 pixel-identical prior reviews).
See `.planning/debug/replay-claim-impact.md` for all eight dependencies and sensitivities.

Prepare the completed 99,601-record prospective evidence body for publication, report the
joint-protocol `NO_SELECTION` as separate negative evidence, verify primary citations,
freeze a clean archival snapshot, and submit only claims supported by the applicable
evidence body.

Requirements: REP-03, REP-05.

Publication preparation verified through 2026-09-10:

- Updated Markdown/Word manuscript, four PLOS main figures, source-data sidecars,
  primary-source context, development-result table, and reproducibility limitations.
- Restored authenticated 2,750-row development evidence and exactly reproduced its
  `NO_SELECTION` analysis without opening the lockbox.
- Added figure collision and publication-bundle regressions; separated optional document
  requirements from the frozen scientific dependency file.
- Latest full suite, run during edits: 2,437 passed, nine failures. Eight historical
  replay/calibration failures remain; the ninth was an obsolete in-memory manuscript
  assertion, now passing in the fresh 85-test publication suite. No final full-suite
  rerun or all-green repository claim. Prospective release validator: nine checks passed.
- Full-paper revision: 40-page illustrated Word copy, 36-page submission-format copy,
  and one-page cover letter; all 77 rendered pages reviewed (pixel-identical pages
  reused between consecutive renders), no verified overlaps or clipping,
  85 focused tests passed in 42.27 seconds. Original prospective
  maps use a fixed 0.50 cutoff and certificate counts are posterior model checks, not
  oracle containment. These source-reconciled limitations are explicit in the paper.
- Figure 2 methods now correctly identify the common GP readout, distinct from the
  earlier quadratic diagnostics. Fresh targeted replay checks retain the small
  classical-source mismatch and intentional calibration stop-gate failure. Added
  recorded-input/export freshness and embedded-Word-image regressions; no historical
  reference results or equality gates were changed.
- Supporting tables now distinguish original archive text from corrected scientific
  interpretation, report replication units accurately, and preserve tiny p-values.
  Research-summary documentation is reconciled. All three Word exports have hash-bound
  provenance. The latest local `manuscript/SPADE-PLOS-ONE-upload-draft-2026-09-10.zip` contains nine
  journal-upload files and an author-action/hash manifest; it is not a public code/data
  archive and has not been submitted. The packager rejects stale artifacts, wrong
  document modes, and overwriting an existing ZIP.
- Targeted primary-literature comparison added Table 5 and brought references to 20,
  acknowledging straddle, conservative excursion sets, TruVaR, and a 2026 synthetic
  BO benchmark. Practical gains are comparator-dependent: the Sobol map contrast is
  below 0.02 and one-shot LHS is a strong descriptive comparator. Replication units
  and novelty boundaries are explicit. Added citation-order/claim-boundary checks
  and a test-first table-caption pagination fix. Latest ZIP CRC and all nine upload
  hashes passed; the old unversioned ZIP is preserved but superseded. No raw results,
  equality gates, scientific decisions, or lockbox state were changed.

Phase 6 is not complete: author declarations, historical
replay disposition, author scientific/AI-disclosure approval, and a clean DOI-bearing
archival release remain outstanding.

2026-09-12 current release state: joint ownership and MIT/CC BY 4.0 licensing are
approved. The licensed r3 snapshot contains 497 hash-verified payload files; 109
focused tests and nine release checks passed both locally and after extraction.
Code, manuscript, figures and the archive are backed up on the private GitHub
`codex/publication-readiness` branch at `b91867d`. This is not a public DOI deposit
or journal submission. The local-only and licensing-pending notes below describe
earlier r2 history, not the current r3 license status. Author/account/fee decisions
and scientific signoff remain required; no paid service or journal charge is approved.

2026-09-11 local-only archival and replay follow-up:

- All eight original historical checks were freshly reproduced as failing, without
  changed thresholds or reference results. A later sampler-seed change explains an
  additional first-acquisition divergence; restoring legacy behavior does not repair
  the original historical discrepancy. Single-key Torch/Accelerate thread controls
  and unchanged historical fitter/optimizer ASTs narrow but do not resolve the cause.
- Prepared a 495-file explicit-scope local code/data archive (`2026-09-11-r2`), with
  all extraction hashes verified, preserved historical reference inputs, and licensing
  decisions recorded. Private lab material, third-party data, fonts, Git history,
  runtime environments and lockbox outcomes are excluded. No upload or license grant.
  The final r2 extracted snapshot passes 106 archive/publication tests (43.55s) and
  all nine prospective release checks without `--pre-release`; source import location
  and all 495 file hashes verified. Existing dependencies and local Arial were used.
- Fresh-install follow-up also passes: all 54 dependencies installed from public PyPI,
  extracted package built, compatibility check passes for 55 packages; 106 focused
  tests and nine release checks pass in the new environment. The same seven historical
  test failures and direct P7 gate failure persist; no reference or assertion changed.
  This closes fresh-install validation on the same macOS/ARM host, not exact historical
  regeneration or cross-platform validation. User decisions/access are now requested.
- Author details are the **last** step per user instruction. Recover original replay
  provenance and settle release rights before public deposit; final author approvals,
  DOI insertion, rebuild and submission remain gated. Do not claim all-green replay.
