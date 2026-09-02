# Codebase Concerns

**Analysis Date:** 2026-08-26

## Tech Debt

**Publication release is mechanically blocked (Critical):**
- Issue: `scripts/validate_final_spade_release.py --pre-release` reports eight blocking violations: one `alpha_star_misuse` in `docs/FINDINGS-SPADE-FINAL.md:578` and seven manifest entries whose per-condition result files are absent (`results/final-spade-c1.json` through `results/final-spade-s3.json`). The script also skips the absent combined benchmark `results/final-spade-primary.json` in pre-release mode.
- Files: `scripts/validate_final_spade_release.py`, `docs/FINDINGS-SPADE-FINAL.md`, `results/final-spade-manifest.json`, `results/final-spade-c1.json`, `results/final-spade-c2.json`, `results/final-spade-c3.json`, `results/final-spade-c4.json`, `results/final-spade-s1.json`, `results/final-spade-s2.json`, `results/final-spade-s3.json`, `results/final-spade-primary.json`
- Impact: The prospective-study findings are not release-ready even though `docs/FINDINGS-SPADE-FINAL.md` says all nine checks pass. The paper must not claim a clean release audit or cite missing condition artefacts as independently inspectable.
- Fix approach: Restore or regenerate the seven condition artefacts named by the manifest, build the combined primary artefact, correct the `alpha_star` sentence, then run the validator without `--pre-release` and preserve its output.

**Current full suite fails reproducibility gates (Critical):**
- Issue: A full run on 2026-08-24 collected 1,622 tests and finished with **1,614 passed, 8 failed, 13 warnings in 360.21 s**. Three failures are material adaptive replay mismatches against committed Q42/Q59 columns (`tests/test_replay.py`); four are exact-reproduction failures with deltas from roughly `2e-16` to `4e-7` (`tests/test_d23_doe_subspace.py`, `tests/test_p4_coord.py`, `tests/test_q59_map_rescore.py`, `tests/test_spread_gp.py`); and the P7 checkpoint subprocess exits non-zero because its map fidelity gate reports 48 failures at a worst delta of `9.082e-13` (`tests/test_calibration.py`). The committed `results/full-test-suite.log` records an older 1,300-test green run and contains absolute paths from `/Users/jy/BO/nutrigene-ai-bo-ipsec`.
- Files: `results/full-test-suite.log`, `tests/`, `pyproject.toml`
- Impact: The current tree is not green, committed adaptive-family results do not replay in the installed environment, and the historical log cannot substantiate current reproducibility. Absolute paths also weaken portability and can confuse provenance.
- Fix approach: Diagnose environment/thread/seed drift without weakening exact gates. Separate deterministic floating-point drift from the large adaptive replay mismatches, restore bitwise or registered-tolerance reproduction as appropriate, then rerun the complete suite and capture a fresh log with git SHA and environment metadata. Do not report a current green suite until this is done.

**No lint, type, coverage, or general automated CI quality gate (Medium):**
- Issue: `pyproject.toml` configures pytest only. `requirements.txt` has no formatter, linter, type checker, or coverage plugin. `.github/workflows/spade-distributed.yml` exists, but it is a manual registered-shard executor with no push/pull-request/schedule trigger and deliberately runs no tests, lint, coverage, analysis, selection, or release validation.
- Files: `pyproject.toml`, `requirements.txt`, `.github/workflows/spade-distributed.yml`, `src/boec/`, `scripts/`, `tests/`
- Impact: The large script surface can accumulate dead branches, inconsistent style, missing annotations, and unexecuted manuscript paths without a machine-visible gate.
- Fix approach: Add only the minimal checks justified for paper release: a reproducible test job, targeted lint, and coverage reporting for `src/boec/` plus release-critical scripts. Establish a baseline before setting thresholds.

**Experiment logic is duplicated across many scripts (Medium):**
- Issue: The repository contains a large sequence of `scripts/run_*` and `scripts/analyse_*` files, with research rules often embedded locally rather than shared through `src/boec/`.
- Files: `scripts/`, `src/boec/`
- Impact: Closely related analyses can drift in seed handling, aggregation unit, multiplicity family, or result schema. The repository’s own corrections in `docs/TRIAGE.md` and `docs/ESTIMAND-EVALUATION.md` show that such drift can change conclusions.
- Fix approach: Do not refactor before manuscript freeze. For any new analysis, reuse tested functions from `src/boec/`; after release, consolidate repeated provenance, pairing, Holm, and result-envelope logic behind stable tested APIs.

**Runner advertises a method it cannot execute (Medium):**
- Issue: `src/boec/runner.py` includes `doe` in the documented method set but lists it in `UNWIRED_METHODS`; callers must invoke `boec.doe.run_doe_arm` separately.
- Files: `src/boec/runner.py`, `src/boec/doe.py`, `scripts/run_doe_arm.py`
- Impact: A unified campaign grid cannot safely dispatch all named arms, increasing bespoke-script and schema-divergence risk.
- Fix approach: Keep the explicit hard failure. Wire `DoEResult` into `Runner` only with parity tests against the current direct script and no changes to existing committed outputs.

## Known Bugs

**Committed campaign replay is not reproducible in the current environment:**
- Symptoms: Regenerated qLogEI/qLogNEI regrets differ materially from committed Q42/Q59 columns (for example Hartmann6 qLogEI seed 0: `0.193914` regenerated versus `0.227869` committed; Ackley qLogEI seed 0: `0.764910` versus `0.592801`). Several other gates miss only at floating-point scale, but these adaptive replay differences are too large to classify as rounding.
- Files: `src/boec/replay.py`, `tests/test_replay.py`, `results/q42-families.json`, `results/q59-hartmann-no-screen.json`
- Trigger: Run `.venv/bin/pytest tests/test_replay.py -q` in the pinned local environment.
- Workaround: Treat committed results as the manuscript record but do not claim clean regeneration. Preserve the exact environment and investigate acquisition optimisation, thread settings, seeding, and library behaviour before rerunning any headline campaign.

**Prospective-study release statement contradicts the validator:**
- Symptoms: `docs/FINDINGS-SPADE-FINAL.md:578` states that all nine content checks pass, while the current validator flags that sentence for `alpha_star_misuse` and reports seven missing manifest artefacts.
- Files: `docs/FINDINGS-SPADE-FINAL.md`, `scripts/validate_final_spade_release.py`, `results/final-spade-manifest.json`
- Trigger: Run `.venv/bin/python scripts/validate_final_spade_release.py --pre-release`.
- Workaround: Treat the release as blocked and quote the underlying study limitations only from artefacts that exist and validate.

**Full-run warning paths include numerical degeneracy and optimizer retry:**
- Symptoms: `results/full-test-suite.log` records constant-input correlations, degrees-of-freedom/invalid-divide warnings, FCS offset warnings, and BoTorch/SciPy acquisition-optimization retries.
- Files: `results/full-test-suite.log`, `scripts/run_d23_doe_subspace.py`, `scripts/analyse_f1_dual_n.py`, `scripts/run_p4b_alpha_anomaly.py`, `tests/test_replay.py`
- Trigger: Run the historical full suite and slow numerical paths.
- Workaround: Several tests explicitly require degenerate statistics to report `NaN` rather than significance, but each warning in a paper-producing run still needs a recorded disposition. Do not globally suppress these warnings.

## Security Considerations

**Raw biological data and human sign-off boundary:**
- Risk: Raw lab files and derived candidate outcomes can be promoted into optimizer-readable `y` values without appropriate scientific/human approval, or sensitive source files can be committed accidentally.
- Files: `data/lab/README.md`, `src/boec/lab/dataset.py`, `src/boec/lab/manifest.py`, `tests/test_lab_dataset.py`, `tests/test_lab_manifest.py`
- Current mitigation: Candidate tables use `y_candidate`, never `y`; tests require `awaiting_human_signoff`, checksum verification, and explicit disposition of every FCS file.
- Recommendations: Preserve the promotion rule, keep raw data access-controlled and outside publication bundles as required, and rerun manifest/checksum tests before using any lab-derived number.

**Result and manifest integrity:**
- Risk: A result path can point to different local untracked content in different clones, making a self-comparison look like independent reproduction.
- Files: `.gitignore`, `.github/workflows/spade-distributed.yml`, `scripts/merge_spade_development_shards.py`, `tests/test_e2_provenance.py`, `tests/test_spade_development_merge.py`, `results/e2-grid.json`, `results/final-spade-manifest.json`
- Current mitigation: Specific paper-critical results are allow-listed in `.gitignore`; provenance and manifest tests detect known drift patterns. Distributed SPADE uploads carry raw, hash, resume, and manifest files, while the development merger validates their bytes, exact paths, clean common provenance, canonical coverage/order, and parent hash ledger before write-once promotion.
- Recommendations: Every number entering the manuscript must resolve to a committed immutable artefact or a documented source-data limitation. Preserve the complete four-file shard contract through download/extraction, retain the parent ledger, and validate SHA/checksum fields against the actual tree rather than only internal consistency.

## Performance Bottlenecks

**Full scientific suite and campaign grids are expensive:**
- Problem: The historical full suite took 253.50 seconds for 1,300 tests; current collection is 1,622 tests. Several committed result grids took tens of minutes to hours, as documented in `.gitignore` comments for `results/q53-spread-gp-families.json` and related runs.
- Files: `pyproject.toml`, `results/full-test-suite.log`, `.gitignore`, `scripts/run_*.py`
- Cause: Real GP fits, BO campaigns, many seeds/landscapes, and statistical resampling remain in the default or slow suite by design.
- Improvement path: Use focused tests and `-m "not slow"` during development, but run the complete default suite and release validator before paper freeze. Preserve sharding/resume manifests for expensive experiments.

**Thread oversubscription hazard:**
- Problem: Multiple Torch workers may each spawn multiple BLAS threads and run slower than a single-threaded configuration.
- Files: `src/boec/runner.py`, `scripts/run_spade_actions_worker.py`, experiment scripts under `scripts/`
- Cause: `set_single_threaded()` sets environment variables after Torch is already imported in `src/boec/runner.py`, and its docstring warns that some builds fix thread pools at import time.
- Improvement path: Set thread environment variables before importing Torch and retain `set_single_threaded()` as a secondary guard. The distributed worker wrapper already fails closed on the full environment freeze, CPU-only execution, and one Torch intra/inter-op thread; preserve that wrapper and the workflow's maximum of two concurrent worker processes per runner.

## Fragile Areas

**Distributed SPADE custody and lockbox provenance:**
- Files: `.github/workflows/spade-distributed.yml`, `scripts/make_spade_actions_matrix.py`, `scripts/run_spade_actions_worker.py`, `scripts/merge_spade_development_shards.py`, `scripts/run_spade_lockbox.py`, `results/spade-lockbox-power.json`, `tests/test_spade_actions_workflow.py`, `tests/test_spade_actions_matrix.py`, `tests/test_spade_development_merge.py`
- Why fragile: GitHub artifact transport is temporary and external to Git history, while the lockbox matrix depends on an exact committed canonical `POWERED` prefix and an exact source SHA. The workflow uploads shard contracts but intentionally performs no outcome inspection, analysis, or merge. Losing a sidecar/resume/manifest, mixing run attempts or source identities, or bypassing guarded lockbox execution breaks the provenance chain even if raw rows appear complete.
- Safe modification: Keep dispatch manual and phase-confirmed; preserve pinned action/container identities, the 40-runner/two-process ceilings, and all four files per shard. Download without renaming, reject mixed source/protocol/config/generator identities, use the deterministic development merger, and keep lockbox planning/execution gated by the committed power decision and guarded runner.
- Test coverage: Structural workflow, matrix, worker-preflight, and development-merge contracts are strong. They do not turn GitHub Actions into a general CI gate, prove artifact retention/custody after upload, or replace lockbox release/provenance validation.

**Manuscript evidence graph and stale artefacts:**
- Files: `docs/MAIN-LINE.md`, `docs/CLAIMS.md`, `docs/RESEARCH-SUMMARY.md`, `docs/TRIAGE.md`, `docs/RESULTS.md`, `docs/archive/`, `results/*.SUPERSEDED-*.json`
- Why fragile: Multiple documents contain historical claims, corrections, retractions, and superseded analyses. `docs/CLAIMS.md` declares itself a draft proposal; `docs/MAIN-LINE.md` is the intended skeleton but still lists items that must be fixed or stated. Superseded JSON remains alongside live results.
- Safe modification: Start paper drafting from `docs/MAIN-LINE.md`, then verify each sentence against `docs/TRIAGE.md`, the cited committed artefact, and the latest `docs/RESEARCH-SUMMARY.md`. Never infer “latest” from filename alone.
- Test coverage: Strong for selected artefact/document links (`tests/test_e2_provenance.py`, `tests/test_q50_paired.py`, final-SPADE validators), but there is no general graph validator covering every claim in every document.

**Statistical unit and estimand selection:**
- Files: `docs/ESTIMAND-EVALUATION.md`, `tests/test_final_spade_statistics.py`, `docs/MAIN-LINE.md`, `docs/RESULTS.md`
- Why fragile: Conclusions change between rule A, unconstrained rule C, constrained rule C, and rule P; n=25 instance-averaged and n=50 instance-seed units can produce different intervals. The codebase records prior contradictions from unregistered choices.
- Safe modification: Name the scoring rule, aggregation unit, pairing, confidence interval, hypothesis test, and Holm family in the same table/caption. Report both registered primary and sensitivity estimands where required.
- Test coverage: Final-SPADE tests reject mixed estimands and invalid pooling, but older scripts and prose are not uniformly governed by those classes.

**Optional/raw-data tests can skip:**
- Files: `tests/test_lab_protocol.py`, `tests/test_lab_imaging.py`, `tests/test_lab_dataset.py`, `tests/test_q50_paired.py`, `data/lab/`
- Why fragile: A green run can include skips when protocols, microscopy, derived run summaries, or optional committed artefacts are absent.
- Safe modification: Record skip counts and reasons. For any paper claim using those inputs, require the relevant test module to run without skips in the release environment.
- Test coverage: Conditional and strong when data is present; not proof of availability in a clean clone.

## Scaling Limits

**48-well design budget:**
- Current capacity: The prospective protocol is constrained to 48 wells; at d=8 a full second-order model requires 45 parameters.
- Limit: An unscreened d=8 classical comparator cannot fit a central composite design within the shared budget.
- Scaling path: This is a stated structural limitation, not a software optimization. Report the d=8 confound explicitly; only a larger experimental budget or a different lower-complexity comparator changes it.
- Files: `docs/RESEARCH-SUMMARY.md`, `docs/SPADE-FINAL-SPEC.md`, `src/boec/designs.py`, `tests/test_designs.py`

**Candidate-grid and posterior-draw memory:**
- Current capacity: Large seeded Sobol grids and posterior-draw matrices are evaluated in chunks in design-space code.
- Limit: High dimension, more posterior draws, or denser grids increase GP prediction and containment cost sharply.
- Scaling path: Preserve deterministic chunking and equality tests such as `tests/test_designspace.py::test_gp_adapter_chunking_gives_the_same_answer_as_one_shot`; shard at experiment boundaries rather than changing numerical definitions.
- Files: `src/boec/designspace.py`, `src/boec/vorobev.py`, `tests/test_designspace.py`

## Dependencies at Risk

**Exact scientific pins are platform-specific:**
- Risk: `requirements.txt` pins future/exact versions including `torch==2.13.0`, `numpy==2.4.6`, and `pandas==3.0.5`, and says the environment is verified on macOS/arm64 CPU only.
- Impact: Other platforms may fail to resolve wheels or may produce numerically different oracle acceptance/optimization outcomes.
- Migration plan: Publish the tested Python/platform metadata and a lock or environment export. Validate a clean installation on the intended archival platform before claiming reproducibility.

**Torch JIT deprecation:**
- Risk: Test collection and the historical suite report `torch.jit.script` deprecation warnings from the installed Torch stack.
- Impact: A future dependency upgrade can remove or change a transitive path even if project code does not call it directly.
- Migration plan: Keep exact pins for the paper release; test upgrades separately and do not regenerate headline artefacts under a changed stack without versioning them.

**FCS parser tolerates malformed offsets:**
- Risk: FlowIO warns that at least one aborted FCS file reports an incorrect data offset and attempts recovery.
- Impact: Recovered event data could be trusted accidentally.
- Migration plan: Preserve tests requiring aborted files to raise or receive an explicit disposition, and document parser warnings in lab-data provenance.
- Files: `results/full-test-suite.log`, `src/boec/lab/fcs.py`, `tests/test_lab_fcs.py`

## Missing Critical Features

**A clean manuscript source and automated build are not present:**
- Problem: The repository has extensive Markdown evidence and figures but no single manuscript source, bibliography, or reproducible paper-build target is detected.
- Blocks: Submission-ready text, stable cross-references, bibliography verification, and a one-command reconstruction of tables/figures.
- Files: `docs/MAIN-LINE.md`, `docs/RESEARCH-SUMMARY.md`, `docs/METHODS.md`, `results/figures/`

**Several claimed figure/result sources are not regenerable:**
- Problem: `docs/MAIN-LINE.md` records that `results/E4-RESULTS-v2.md` and `results/NEGATIVE-shape-aware-mean.md` lack producing scripts, `docs/METHODS.md` anchors to no artefact, and `.gitignore` says `results/figures/fig1-scoring.html` and `results/figures/fig3-saddle.html` are hand-authored with hardcoded numbers.
- Blocks: End-to-end reproduction and safe updates when source numbers change.
- Files: `docs/MAIN-LINE.md`, `results/E4-RESULTS-v2.md`, `results/NEGATIVE-shape-aware-mean.md`, `docs/METHODS.md`, `results/figures/fig1-scoring.html`, `results/figures/fig3-saddle.html`, `.gitignore`

**In-house lab data cannot support the planned Phase 3 figure:**
- Problem: `results/lab-phase3-feasibility.json` records a no-go decision; candidate values remain awaiting human sign-off and single-replicate coating rows are not optimizer-ready.
- Blocks: A defensible in-house biological validation figure from the current drop.
- Files: `results/lab-phase3-feasibility.json`, `data/lab/README.md`, `tests/test_lab_dataset.py`

## Test Coverage Gaps

**Current tree has a verified failing full-suite run:**
- What's not tested: The 2026-08-24 default run exercised all 1,622 collected tests, but eight reproducibility/replay gates failed; the older committed log covers only 1,300 tests and is not current evidence.
- Files: `tests/`, `results/full-test-suite.log`
- Risk: Paper-facing reproducibility regressions are present despite strong overall test volume.
- Priority: Critical before manuscript freeze.

**No quantitative line/branch coverage:**
- What's not tested: There is no evidence identifying unexecuted branches across `src/boec/` or the large `scripts/` surface.
- Files: `pyproject.toml`, `requirements.txt`, `src/boec/`, `scripts/`
- Risk: Rare error paths and one-off analysis branches can remain untested while test count appears reassuring.
- Priority: Medium; prioritize release-critical code and manuscript generators.

**No universal claim-to-artefact validator:**
- What's not tested: Only selected results and final-SPADE prose are mechanically linked to source artefacts. Older statements across `docs/CLAIMS.md`, `docs/RESULTS.md`, `docs/RESEARCH-SUMMARY.md`, and figure HTML are not all cross-validated.
- Files: `docs/CLAIMS.md`, `docs/RESULTS.md`, `docs/RESEARCH-SUMMARY.md`, `results/figures/`, `tests/test_e2_provenance.py`, `scripts/validate_final_spade_release.py`
- Risk: Corrected or superseded numbers can survive in paper drafts.
- Priority: High.

**Clean-clone and cross-platform reproduction is incompletely exercised:**
- What's not tested: The suite uses pytest’s `pythonpath` and an existing `.venv`; the repository documents earlier failures when scripts ran without `pip install -e .`. Current evidence is macOS/arm64 CPU-only.
- Files: `pyproject.toml`, `requirements.txt`, `scripts/`, `results/full-test-suite.log`
- Risk: Reviewers cannot reproduce scripts on a fresh environment even if local tests pass.
- Priority: High; run a clean-clone setup and a representative end-to-end regeneration before release.

---

*Concerns audit: 2026-08-26*
