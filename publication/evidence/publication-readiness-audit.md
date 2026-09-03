# Publication-readiness audit

**Audit date:** 2026-09-02
**Scope:** active repository at the publication-ready worktree, including staged but uncommitted
canonical-result restoration supplied by the root agent
**Initial verdict:** **NOT READY FOR PUBLIC RELEASE OR JOURNAL SUBMISSION**

## Resolution status (2026-09-03)

This document preserves the pre-repair findings below. The publication-preparation pass has
since resolved the repository-controlled blockers:

- B1: the unusable distributed workflow was replaced by a clean-checkout publication CI job
  that installs the environment, verifies claims and links, and runs the full test suite;
- B2: the lab README now accurately describes the retained evidence subset and labels the old
  manifest/RUN record as historical provenance rather than a portable rebuild contract;
- B4: all 25 canonical result artifacts are tracked and a regression test requires them;
- B5: C5 was repaired to a seed-aware, SPADE-only, row-order-invariant descriptive estimand
  (`rho=0.9880098603391883`) with completeness and malformed-input tests; and
- the manuscript, Methods, Supplement, traceability matrix, and repository landing page were
  rewritten around the bounded claim ledger and reviewed primary literature.

Fresh local verification reports 764 passing tests, 12/12 selected scalar checks, valid
publication links, valid workflow/CFF YAML, and a clean diff check. The package is therefore
ready for scientific review. It is **not yet a public reusable release**: B3 (license and data
rights), journal choice, author metadata/declarations, and any journal-required current figure
package require owner decisions and cannot be inferred by repository automation.

The claim/evidence spine has useful structure: the claim ledger identifies allowed and forbidden
wording, the canonical result set is explicit, 12 selected scalar values recompute, and the
focused publication tests pass. Those checks are not a scientific validation or a complete
manuscript/data consistency audit. The original C5 defect has been repaired in the current
uncommitted tree but still requires final tests, commit, and fresh-checkout verification. Release
remains blocked by a non-runnable workflow, an
active lab-data README that describes and verifies a dataset which is no longer present at that
path, unresolved reuse rights, and the fact that the canonical-result recovery is not yet part of
a commit. A manuscript submission also still needs an owner/journal-specific figure and submission
package.

## Release blockers

### B1. The sole GitHub workflow cannot run

`.github/workflows/spade-distributed.yml:100-105` calls
`software/scripts/make_spade_actions_matrix.py`; lines 156 and 185-211 call
`software/scripts/run_spade_actions_worker.py`. Neither file exists in the active tree. The
workflow therefore fails in its plan job before producing a matrix, and its worker preflight and
shards are also unreachable. This conflicts with the workflow's strong immutable-source and
container claims at lines 73-91 and 129-156. Restore/rewrite those scripts and add a workflow
preflight test that resolves every repository-local command, or remove/archive the workflow if it
is not part of this release.

### B2. The active lab-data documentation and checksum contract are false after reorganization

`research/data/lab/README.md:3` describes the directory as the source-material drop;
lines 11-13 define `raw/`, `overlay/`, and rebuildable `derived/`; lines 19 and 96-106 promise a
missing `software/scripts/build_lab_dataset.py` and a checksum-verification command. The command
fails because 235 manifest-listed raw files are absent from the active data tree (for example,
`raw/flow/2026-07-21/10%FBS-p1.fcs`), while those files now live under `archive/exploratory/`.
The same README's inventory still claims 300 data files and 267 MB at lines 55-75, and its link to
`../../docs/LAB-DATA-FOR-BO.md` at line 5 is broken. Meanwhile
`research/data/lab/derived/RUN.json:3` embeds a contributor-local absolute path and lines 4-10
record the old 306-file/300-checksum/52-flow-file build, not the active subset.

This is more than editorial drift: `MANUSCRIPT.md:183-186` says in-house raw data are retained with
checksums, and `METHODS.md:80-83` says the supporting table is linked to raw FCS files, overlays,
and checksums. Either restore a coherent, governed support dataset and its builder, or explicitly
document that only an evidence-linked subset is active, regenerate a subset manifest and portable
RUN record, and point to the archive for the full immutable drop. Add the lab README to the active
link/audit test; `software/scripts/check_paper_links.py:21-27` currently omits it.

### B3. No public reuse license or settled data rights

`LICENSE:3-12` explicitly grants no license and requires owner approval for software and separate
confirmation for laboratory and published-source data. `README.md:84-88` correctly discloses this,
and `MANUSCRIPT.md:181-186` makes availability conditional on the eventual license and laboratory
policy. That is transparent but not a reusable public software/data release. Before release,
owners must select the software/documentation license, document rights and access terms by data
class (in-house raw/derived, third-party images/extractions, synthetic results, figures), and make
the manuscript availability statement match what a reader can legally obtain and reuse.

### B4. Canonical evidence recovery must be committed and verified from a fresh checkout

At the audit start, all 25 canonical JSON/log inputs named by the claim ledger were staged as new
files because `.gitignore:23-24` had ignored the entire `research/results/*` tree and the files were
absent from a fresh checkout. Without them, `verify_conclusions.py` and the reproduction map fail.
The root agent has staged their restoration and added
`software/tests/test_repository_audit.py:163-184`, which requires the complete named set to appear
in `git ls-files`; the working `.gitignore` also adds explicit canonical-directory exceptions.
This is the correct repair direction, and the restored inputs produce 12/12 guarded values, but it
is not release evidence until the files, ignore exceptions, and regression test are committed and
the checks are rerun from a genuinely fresh checkout/archive rather than this populated worktree.

### B5. C5 order-dependence is repaired in the working tree, pending final verification and commit

The audited baseline C5 claim was not a valid reproducible statistic. In
`software/scripts/analyse_tau_sweep.py:28-42`, `load()` assigns `diff[(family, p)] = margin_sd`
inside the loop over every arm, seed, and inflation row. Each assignment overwrites the previous
one, so the retained margin for each family/prevalence cell is whichever row happens to occur last
in the JSON/input traversal. Lines 93-116 then correlate those 25 arbitrary last-row margins with
answer rates pooled across arms at `c=1.0`. `verify_conclusions.py:69-82` repeats the same load and
therefore merely reproduces the same order-dependent `0.9801`; it does not independently validate
C5. A direct inventory found multiple `margin_sd` values in 5 of the 25 cells, with as many as 40
distinct values in one cell; this is not a harmless overwrite of identical values. Reordering
scientifically identical rows can change the explanatory variable and rho.

This mattered because C5 is a main claim in the abstract and Results (`MANUSCRIPT.md:18-20`,
109-116), claim ledger (`CLAIMS-AND-SOURCES.md:62-71`), and protocol gate (`PROTOCOLS.md:41-51`).
The current uncommitted repair now defines the estimand as SPADE-only answer rate at `c=1.0`,
`alpha=0.95` versus the mean of 64 unique seed-specific margins per family/prevalence cell.
`analyse_tau_sweep.py:28-87` deduplicates margins by family/seed/prevalence, rejects inconsistent
duplicates, and checks the complete canonical grid; `tau1_points()` is arm/inflation-specific.
The repaired descriptive result is rho `0.9880098603391883` across 25 nested cells, with median-margin
and qLogNEI-only sensitivities, and the manuscript/ledger/protocol no longer report a naive
correlation p-value or treat the cells as exchangeable population samples.

B5 is resolved in substance in the working tree, not yet in release history. Before tagging or
submission, complete the pending quality fixes, run the new order/completeness guards and full
suite, commit the analyser, guard, tests, and synchronized C5 prose, then verify them from a fresh
checkout. Preserve the dependence caveat: the repaired rho is a descriptive registered-gate
summary over nested cells, not population inference. If the repair does not survive those checks,
withdraw C5 and its downstream interpretation.

## Submission blockers or owner/journal-dependent actions

### S1. There is no current-manuscript figure package

`research/results/figures/README.md:6-13` accurately says that the four fully packaged figures
(caption, alt text, description, source data, PDF/PNG/SVG/TIFF) belong to the earlier terminal-rule
paper, while eight `final-spade-development/` images are from an earlier SPADE study and the current
manuscript reports results only in text. `MANUSCRIPT.md` contains no figure calls, tables, captions,
or image references. Thus the repository has a good historical figure inventory, but no figure or
table communicates the current C1-C6 results.

Owners should decide with the target journal whether a text-only results draft is acceptable. A
normal submission will need a current figure/table inventory mapped to C1-C6, in-text calls,
captions, accessible alt text/descriptions, source-data files, and journal-compliant formats. Do not
reuse the terminal-rule or earlier-development figures merely because they exist.

### S2. Submission metadata are incomplete

`CITATION.cff:1-23` is syntactically simple and internally consistent with project version 0.1.0,
authors, title, repository URL, abstract, and release date. Before an actual archive/submission,
owners should replace or augment repository URLs with the immutable release/DOI, add ORCIDs and
preferred paper citation when available, and confirm the release date/version against the tag.
`MANUSCRIPT.md:1-3` begins directly with the title and abstract: author list, affiliations,
corresponding-author details, declarations, funding, contributions, conflicts, acknowledgements,
ethics/data-governance statements, and journal-specific front/back matter are absent. Their exact
requirements depend on the venue and owners.

## Important improvements before release

### I1. Make packaging metadata describe an installable distribution

The documented local procedure is coherent (`README.md:33-43`): Python 3.11, pinned requirements,
then `pip install -e .`. Package discovery correctly points at `software/src` in
`pyproject.toml:12-21`. However, `[project]` at lines 1-4 contains only name, version, and Python
floor: it has no description, readme, authors, license expression/file, dependencies, classifiers,
or project URLs. Consequently `pip install .` alone does not install runtime dependencies; readers
must know to use the separate requirements file. Either declare package dependencies/metadata (and
keep the lock/pins as a reproducibility environment) or explicitly state that this is not intended
for package-index distribution.

Clean stale comments while doing so: `pyproject.toml:7-11` contains the malformed path
`software/software/scripts` and references removed `docs/RESULTS-PERSON-A.md`; requirements lines
8-11 and 37-43 likewise describe pre-reorganization `src`, `scripts`, `docs`, and `data/lab` paths.
These comments do not break installation but undermine a publication-facing root.

### I2. Expand automated publication-path checks

`check_paper_links.py:13-18` checks 12 required artifacts, and lines 21-27 validate selected root,
publication, and archive READMEs. It deliberately or accidentally excludes active
`research/data/lab/README.md`, all workflow command targets, code-span paths, figure/source-data
coverage, citation/license metadata, and fresh-checkout tracking. That is why its success coexists
with B1 and B2. Extend it (or add separate tests) for every active README, repository-local workflow
command, protocol/reproduction command, canonical tracked input, and current figure manifest.

### I3. Clarify what “reproduction” means for each result

The map is useful and executable for analyses, but it is incomplete as an end-to-end reproduction
map. `publication/evidence/reproduction-map.md:18-46` names inputs and analysis commands for C1-C3
and S1; C4-C6 are only covered indirectly by the all-claims guard at lines 8-16. Lines 50-58 name
two in-house commands without enumerating exact inputs/outputs, and those commands are potentially
output-producing; lines 60-67 give only one Hall/Ogle command despite separate build/digitization
provenance. Lines 75-76 promise runtime, status, and output hashes in a “final audit report,” but no
such run ledger is linked.

For every C/S claim, record: immutable input paths and hashes, producer versus analyser, exact
command, expected output, whether it is read-only or overwrites an artifact, approximate resources,
and last verified commit/platform. Distinguish fast recomputation from expensive campaign
regeneration and from manual data adjudication.

### I4. State calibration and dependence limits in the claims and methods

The certification claims do not all have the same out-of-sample status. DC/C2 chooses the first
inflation that passes pooled certification on the same five-family DC dataset it evaluates
(`analyse_dc_doe_certificate.py:56-72`, 94-117); its containment result is therefore
in-sample with respect to calibration selection. LC/C3 instead selects inflation on the other
families and evaluates volume on the held-out family (`analyse_lc_confirmatory.py:71-101`,
242-260). The manuscript/ledger should state this distinction wherever C2 and C3 are compared;
the DC result must not inherit the stronger LOFO interpretation used for C3.

The inferential calculations also treat analysis rows as exchangeable independent units without
justification. The scalar bootstrap samples individual paired differences (`analyse_dc_doe_certificate.py:45-53`;
`analyse_lc_confirmatory.py:47-55`), although cells share families, synthetic landscapes and/or
seeds and multiple prevalence cells can derive from one run. Pooled Clopper-Pearson bounds count
answered cells as binomial trials (`analyse_dc_doe_certificate.py:56-64`;
`analyse_lc_confirmatory.py:58-68`; `analyse_tau_sweep.py:56-66`), again ignoring within-family,
within-seed, and cross-prevalence dependence plus selection of inflation on related cells. These
intervals may be too narrow and their nominal coverage is not established by the current code.
Specify the independent sampling unit and target population, use a design-respecting clustered or
hierarchical analysis (and nested evaluation where selection is involved), or explicitly relabel
the intervals/lower bounds as descriptive sensitivity summaries. This is a scientific limitation,
not just a software improvement, and should be resolved before inferential submission claims.

### I5. Rename misleading historical “final” paths

The root README's authority rule (`README.md:18-19`) and evidence guide
(`publication/evidence/README.md:16-18`) correctly warn that “final” filenames are not ground
truth. Nevertheless `research/results/figures/final-spade-development/` is inside the active result
tree and visually competes with the current manuscript while containing earlier-study graphics.
Rename it to a status-neutral historical/development label or move it under a clearly historical
figure namespace, preserving provenance in a manifest. The current explanatory README reduces the
risk but does not eliminate it for browsing or automated discovery.

### I6. Reduce publication-bundle weight and generated clutter

The worktree is about 1.2 GB, of which `archive/` is about 1.1 GB. Preservation is defensible, but
a journal/software archive may need a smaller source release plus separately deposited governed
data/archive artifacts. Decide whether archival raw instrument files and historical repository
material belong in the software release, a data repository, or a restricted-access deposit.

Local `.venv`, `.pytest_cache`, and `__pycache__` content exists but is ignored and untracked, so it
does not contaminate a Git archive. No tracked pycache, bytecode, editor, or pytest-cache artifacts
were found. The staged `.worktrees/` ignore rule is a sensible local-hygiene improvement.

## What is already publication-strong

- The root reading path is concise and accurate (`README.md:8-19`, 49-72), and it prominently
  bounds real-cell evidence and noise limitations (`README.md:77-82`).
- The claim ledger usefully states allowed/forbidden wording, estimates, inputs, analysers, guards,
  and limitations for C1-C6 and S1-S3 (`CLAIMS-AND-SOURCES.md:8-136`). C5's current uncommitted
  repair is materially better specified but remains descriptive and pending final verification.
- The evidence guide records the audited 719-commit/1,402-file baseline and classification totals
  (`publication/evidence/README.md:10-33`) and explicitly rejects filename/recency authority.
- Protocol registrations map frozen commits to active code and canonical data
  (`PROTOCOLS.md:7-62`), and shared anti-overclaim rules are explicit at lines 64-70.
- The manuscript usefully discloses the tested DoE arm's adverse recipe-quality result, reports
  answered/contained denominators, and disclaims prospective wet-lab validation
  (`MANUSCRIPT.md:93-107`, 135-144, 161-179). This narrow praise does **not** endorse C5 before its
  repair is finalized, the C1
  “matches” framing, DC's in-sample calibration claim, or any bootstrap/Clopper-Pearson inference;
  those remain subject to the blockers and dependence limitations above.
- Existing terminal-rule figures demonstrate a good packaging standard: each of figures 1-4 has
  caption, alt text, extended description, source data, and multiple portable formats.

## Verification performed

All commands were run from the repository root using the existing Python 3.11 virtual environment.

| Check | Result |
|---|---|
| `python software/scripts/check_paper_links.py` | PASS: 17 Markdown files, 12 required artifacts |
| `python software/scripts/verify_conclusions.py` | Earlier run passed only as a consistency check for 12 selected scalars; not an independent scientific validation. The current uncommitted guard replaces the defective C5 scalar with rho `0.9880098603391883` and adds canonical completeness, but final rerun is pending. The script still omits many manuscript estimates/intervals/p-values, calibration-selection validity, dependence assumptions, prose consistency, figure/source-data consistency, and data-governance assertions. |
| Focused claim/audit/link tests | PASS: 21 tests |
| DC, LC, TT, and TAU analysis commands from the reproduction map | Earlier commands executed successfully, but the prior TAU/C5 output was invalid because it depended on row order. The repaired TAU command and new tests require final rerun. DC and LC inferential limitations remain. |
| Lab README checksum command | FAIL: 235 manifest-listed files absent from active tree |
| Workflow local-target existence check | FAIL: matrix and worker scripts absent |
| Tracked generated-clutter scan | PASS: none of the usual cache/bytecode/editor artifacts tracked |
| Full `pytest -q` | PASS: 747 tests in 146.21 s; 3 warnings (two upstream Torch JIT deprecations, one expected small-noise numerical warning) |

## Required disposition

Do not tag, archive, or submit the repository in its current state. Resolve B1-B4 and finalize B5's
tests, synchronized changes, commit, and fresh-checkout verification first. Then obtain
owner decisions for licensing/data governance and the target journal, construct the current figure
and submission package, and perform a clean-clone verification using the exact documented install
commands. Improvements I1-I6 should be closed or explicitly accepted in a release checklist;
the calibration/dependence issue in I4 requires scientific signoff before inferential submission.
