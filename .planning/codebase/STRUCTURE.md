# Codebase Structure

**Analysis Date:** 2026-08-24

## Directory Layout

```text
nutrigene-ai-bo-ipsec/
├── pyproject.toml                 # Installable `boec` package and pytest configuration
├── requirements.txt              # Runtime and research dependencies
├── START-HERE-PERSON-A.md        # Historical onboarding to the original benchmark
├── configs/
│   ├── experiment/               # Registered experiment grids and rules
│   └── lab/                      # In-house condition/metric schemas
├── src/
│   └── boec/                     # Reusable optimisation, inference, mapping, and data code
│       └── lab/                  # Modality-specific in-house data readers/pipeline
├── scripts/                      # Executable runners, analyses, validators, and figure builds
├── tests/                        # Unit, integration, reproducibility, and protocol tests
│   └── fixtures/                 # Small published-data prefixes used by tests
├── data/
│   ├── oracles/                  # Accepted synthetic ensembles and sidecar provenance
│   ├── external/                 # Source extractions/raw publication-derived inputs
│   ├── published/                # Validated canonical Hall/Ogle tables
│   └── lab/
│       ├── raw/                  # Immutable in-house instrument output
│       ├── overlay/              # Human roles, conditions, manifests, and gates
│       └── derived/              # Regenerable pipeline outputs
├── results/                      # Machine-readable evidence, run logs, and figures
│   ├── figures/                  # Rendered paper/exploration figures
│   └── p6-families/              # Per-family shards merged into cross-family evidence
└── docs/
    ├── FINDINGS-SPADE-FINAL.md   # Current prospective-study findings
    ├── SPADE-FINAL-SPEC.md       # Frozen prospective-study protocol
    ├── MAIN-LINE.md              # Compact original paper result skeleton
    ├── METHODS.md                # Method write-up and reproducibility details
    ├── CLAIMS.md                 # Claim/evidence ledger
    ├── archive/                  # Superseded planning and exploratory materials
    └── superpowers/              # Historical implementation specs/plans
```

## Directory Purposes

**`src/boec/`:**

- Purpose: The reusable scientific library; place mathematical definitions and stable experiment-independent behavior here.
- Contains: Oracles, evaluator adapters, campaign loop, GP fitting/prediction, designs, DoE/RSM, metrics, inference, replay, design-space mapping, certificates, and SPADE allocation.
- Key files: `src/boec/campaign.py`, `src/boec/surrogate.py`, `src/boec/oracles.py`, `src/boec/doe.py`, `src/boec/replay.py`, `src/boec/designspace.py`, `src/boec/final_spade.py`.

**`src/boec/lab/`:**

- Purpose: Read and derive in-house instrument-specific data while keeping modality and metric identities separate.
- Contains: FCS parsing/gating, imaging, manifest verification, plate-reader import, protocol parsing, evaluation, and dataset assembly.
- Key files: `src/boec/lab/dataset.py`, `src/boec/lab/manifest.py`, `src/boec/lab/fcs.py`, `src/boec/lab/gating.py`, `src/boec/lab/imaging.py`.

**`scripts/`:**

- Purpose: Define executable studies and transformations around the reusable package.
- Contains: `run_*.py` campaign/study runners, `analyse_*.py` aggregators, `preflight_*.py` gates, `make_*.py` renderers, data builders, and release validators.
- Key files: `scripts/run_e2.py`, `scripts/run_final_spade_benchmark.py`, `scripts/analyse_final_spade_benchmark.py`, `scripts/make_final_spade_figures.py`, `scripts/build_published_dataset.py`, `scripts/build_lab_dataset.py`, `scripts/validate_final_spade_release.py`.

**`tests/`:**

- Purpose: Assert numerical primitives, end-to-end method contracts, artifact schemas, scientific protocol rules, and reproducibility boundaries.
- Contains: Module-matched tests (`test_campaign.py`, `test_surrogate.py`), experiment tests (`test_p*.py`, `test_versionc_*.py`), final-study tests (`test_final_spade_*.py`), and data-pipeline tests (`test_published*.py`, `test_lab_*.py`).
- Key files: `tests/test_final_spade_protocol.py`, `tests/test_final_spade_reproducibility.py`, `tests/test_replay.py`, `tests/test_campaign.py`.

**`configs/experiment/`:**

- Purpose: Preserve compact preregistration/configuration for named experiments.
- Contains: YAML grids, arms, fairness constraints, scoring rules, and inference settings.
- Key files: `configs/experiment/e2.yaml`, `configs/experiment/e4.yaml`.

**`configs/lab/`:**

- Purpose: Describe a laboratory search space and metric without conflating it with the synthetic/published cube.
- Contains: Parameter coding, physical bounds, metric identity, and constraints.
- Key files: `configs/lab/coating_2026-08-06.yaml`.

**`data/oracles/`:**

- Purpose: Cache accepted synthetic Hill instances and exact provenance so experiment ids resolve to stable landscapes.
- Contains: Dimension-specific parquet tables, acceptance audits, and one JSON sidecar per instance.
- Key files: `data/oracles/biphasic-hill-v8+82f6db7c8f77/instances_d6.parquet`, `data/oracles/biphasic-hill-v8+82f6db7c8f77/instances_d8.parquet`, `data/oracles/biphasic-hill-v8+82f6db7c8f77/audit_d6.json`.

**`data/external/`:**

- Purpose: Preserve source-level publication extraction inputs before canonical validation.
- Contains: Hall/Ogle figure images/JSON and an independent CSV extraction with notes.
- Key files: `data/external/hall_ogle_2025/stage1.json`, `data/external/hall_ogle_2025/stage2.json`, `data/external/extraction_a/EXTRACTION_NOTES.md`.

**`data/published/`:**

- Purpose: Hold the validated, analysis-ready published dataset and validation record.
- Contains: Canonical stage CSVs, extraction method, and validation report.
- Key files: `data/published/hall_ogle_2025_stage1.csv`, `data/published/hall_ogle_2025_stage2.csv`, `data/published/VALIDATION_REPORT.md`.

**`data/lab/raw/`:**

- Purpose: Preserve original instrument output byte-for-byte.
- Contains: FCS/XIT/XML flow exports, microscopy images/metadata, protocol documents, and plate-reader workbooks.
- Key files: Source paths are indexed and checksummed by `data/lab/overlay/MANIFEST.sha256`; do not edit or regenerate files here.

**`data/lab/overlay/`:**

- Purpose: Store human judgement separately from both raw bytes and generated tables.
- Contains: File-role classifications, signed/working condition tables, promotion rules, checksum manifest, and gating decisions.
- Key files: `data/lab/overlay/bo_file_roles.csv`, `data/lab/overlay/bo_primary_conditions.csv`, `data/lab/overlay/GATE.md`, `data/lab/overlay/BO-PURPOSE.md`.

**`data/lab/derived/`:**

- Purpose: Hold disposable, reproducible outputs from the lab ingestion pipeline.
- Contains: File index, acquisition metadata, candidate gating metrics, image features, protocol maps, plate-reader assessment, and candidate campaigns.
- Key files: `data/lab/derived/RUN.json`, `data/lab/derived/flow_acquisitions.csv`, `data/lab/derived/flow_positivity_candidate.csv`, `data/lab/derived/image_features.csv`.

**`results/`:**

- Purpose: Serve as the machine-readable evidence ledger for the paper.
- Contains: Raw rows, aggregated summaries, feasibility/classification, certificate cells, kill ledgers, logs, and figure outputs.
- Key files: `results/e2-grid.json`, `results/q34-factorial.json`, `results/p6-families.meta.json`, `results/final-spade-feasibility.json`, `results/final-spade-certificate.json`, `results/final-spade-kill-ledger.json`, `results/final-spade-regret-pareto.json`.

**`docs/`:**

- Purpose: State protocols, methods, claims, findings, handoffs, source verification, and paper structure.
- Contains: Current paper-facing documents at top level and non-current planning/exploration in `docs/archive/`.
- Key files: `docs/SPADE-FINAL-SPEC.md`, `docs/FINDINGS-SPADE-FINAL.md`, `docs/MAIN-LINE.md`, `docs/METHODS.md`, `docs/CLAIMS.md`, `docs/source_verification.md`, `docs/pdf_crosscheck.md`.

**`docs/archive/`:**

- Purpose: Preserve superseded build plans, exploratory scripts/results, and plain-English module explanations without mixing them into current evidence.
- Contains: Original phase plans, exploratory Python, task records, and explanatory notes.
- Key files: `docs/archive/build-phase/phase1_build.md`, `docs/archive/build-phase/what-each-file-does.md`, `docs/archive/exploratory/EXPLORATORY.md`.

## Key File Locations

**Entry Points:**

- `scripts/run_final_spade_benchmark.py`: Prospective final-study campaign runner.
- `scripts/run_final_spade_feasibility.py`: Pre-campaign feasibility/regime gate.
- `scripts/analyse_final_spade_benchmark.py`: Final-study aggregation and registered comparisons.
- `scripts/validate_final_spade_release.py`: Release-level completeness and integrity check.
- `scripts/run_e2.py`: Original registered BO-versus-baseline grid.
- `scripts/run_replay_hall_ogle.py`: Published-data replay.
- `scripts/build_lab_dataset.py`: In-house raw-to-derived pipeline.

**Configuration:**

- `pyproject.toml`: Python >=3.11 package layout and pytest configuration.
- `requirements.txt`: Runtime/test dependency pins or lower bounds.
- `configs/experiment/e2.yaml`: Original sample-efficiency preregistration.
- `configs/experiment/e4.yaml`: Extrapolation experiment configuration.
- `configs/lab/coating_2026-08-06.yaml`: In-house coating/dose search-space and metric schema.
- `docs/SPADE-FINAL-SPEC.md`: Frozen final prospective-study contract.

**Core Logic:**

- `src/boec/campaign.py`: Adaptive campaign state machine and evaluator protocol.
- `src/boec/runner.py`: Multi-cell execution, static designs, pairing policy, provenance.
- `src/boec/oracles.py`: Synthetic truth families and ensemble loading.
- `src/boec/torch_oracle.py`: Torch-facing oracle/evaluator adapters and plug-in noise.
- `src/boec/surrogate.py`: GP build and predictive interface.
- `src/boec/optimizers.py`: Initial/static designs and acquisition proposals.
- `src/boec/doe.py`: Registered classical sequential pipeline.
- `src/boec/metrics.py`: Recipe locators and regret-related scoring.
- `src/boec/replay.py`: Campaign regeneration and artifact gate support.
- `src/boec/designspace.py`: Probability-map construction and region metrics.
- `src/boec/vorobev.py`: Conservative region estimation.
- `src/boec/versionc.py`: Cross-fit certificate/statistic utilities.
- `src/boec/final_spade.py`: Prospective SPADE plate-2 method and output schema.

**Paper and Evidence:**

- `docs/FINDINGS-SPADE-FINAL.md`: Current final-study result narrative; distinguish `done` and `NOT RUN` conditions.
- `docs/SPADE-FINAL-SPEC.md`: Maximum defensible claim and registered decision rules.
- `docs/MAIN-LINE.md`: Original BO/DoE result skeleton and source-artifact map.
- `docs/METHODS.md`: Detailed methods; verify each number/path against current artifacts.
- `docs/CLAIMS.md`: Claim ledger; use alongside current findings because older entries can reflect earlier estimands.
- `results/final-spade-*.json`: Primary final-study evidence family.
- `results/e2-grid.json`, `results/q34-factorial.json`, `results/q35-constrained-rsm.json`: Core original BO/DoE rule comparison.
- `results/p6-families/`, `results/p6-families.meta.json`: Cross-family evidence shards and merge metadata.

**Testing:**

- `tests/test_<module>.py`: Direct unit tests for most `src/boec/<module>.py` files.
- `tests/test_final_spade_protocol.py`: Registered final-study invariants.
- `tests/test_final_spade_reproducibility.py`: Artifact-only figure and reproducibility boundaries.
- `tests/test_final_spade_statistics.py`: Statistical/adjudication behavior.
- `tests/test_replay.py`: Exact campaign regeneration semantics.
- `tests/test_published_dataset.py`, `tests/test_lab_dataset.py`: Data pipeline integration.

## Naming Conventions

**Files:**

- Reusable package modules use lowercase snake case: `src/boec/sequential_rsm.py`, `src/boec/spread_gp.py`.
- Executable runners use `run_<study>.py`: `scripts/run_q52_budget_to_target.py`, `scripts/run_final_spade_benchmark.py`.
- Analysis scripts use `analyse_<study>.py`; pure renderers use `make_<subject>.py`.
- Tests use `test_<module-or-study>.py` and normally mirror the implementation/study name.
- Result artifacts use lowercase hyphenated study ids: `results/q52-budget-to-target.json`, `results/final-spade-certificate.json`.
- Result logs share the artifact stem: `results/p6-merge.log`, `results/q49-noise-threshold.log`.
- Paper/protocol documents use uppercase descriptive names: `docs/METHODS.md`, `docs/SPADE-FINAL-SPEC.md`.
- Superseded evidence remains explicit in the filename: `*.SUPERSEDED-*.json`; do not silently replace it.
- Oracle ensemble directories include the family version and content hash: `data/oracles/biphasic-hill-v8+82f6db7c8f77/`.

**Directories:**

- Package directories are lowercase Python identifiers: `src/boec/lab/`.
- Study-specific result sharding uses a hyphenated stem: `results/p6-families/`.
- Immutable/human/generated lab layers are named by role: `data/lab/raw/`, `data/lab/overlay/`, `data/lab/derived/`.
- Archived material stays under `docs/archive/`; do not use archived paths as current paper evidence without revalidation.

## Where to Add New Code

**New Reusable Numerical Feature:**

- Primary code: `src/boec/<focused_module>.py`; extend an existing module when the abstraction already exists (for example, locators in `src/boec/metrics.py`, map metrics in `src/boec/designspace.py`).
- Tests: `tests/test_<focused_module>.py`.
- Rule: Keep study constants and artifact I/O out of the reusable function unless they are intrinsic to its scientific definition.

**New Experiment or Sensitivity:**

- Protocol/registration: `configs/experiment/<study>.yaml` for compact grids, or `docs/<STUDY>-SPEC.md` when claim logic and kill conditions require prose.
- Runner: `scripts/run_<study>.py`.
- Analysis: `scripts/analyse_<study>.py` when aggregation is more than the runner’s report function.
- Tests: `tests/test_<study>.py`.
- Artifacts: `results/<study>.json` and `results/<study>.log`; include status, key counts, provenance, and explicit condition/rule fields.

**New Final SPADE Condition or Arm:**

- Registration: amend `docs/SPADE-FINAL-SPEC.md` through its numbered erratum process before outcome-bearing execution.
- Method behavior: `src/boec/final_spade.py` only if it is genuinely part of the reusable SPADE algorithm.
- Orchestration/registry: `scripts/run_final_spade_benchmark.py`.
- Analysis/adjudication: `scripts/analyse_final_spade_benchmark.py` and related final analyzers.
- Tests: extend `tests/test_final_spade_protocol.py`, `tests/test_final_spade_statistics.py`, and `tests/test_final_spade_reproducibility.py` as applicable.
- Figures: add artifact-only rendering to `scripts/make_final_spade_figures.py` after the metric exists in committed JSON.

**New Oracle Family:**

- Implementation: `src/boec/oracles.py` with a known/validated optimum where possible.
- Scaling/adapter: reuse `UnitScaled` and `src/boec/replay.py:family_evaluator` so multiplicative noise has comparable meaning.
- Tests: `tests/test_oracles.py`, `tests/test_replay.py`, plus a study-specific test.
- Cached ensemble: `data/oracles/<version+hash>/` only for accepted sampled families requiring stable instance identity.

**New Published Dataset:**

- Source extraction: `data/external/<source_id>/`.
- Validation/canonicalization: extend `src/boec/published.py` or add a focused peer module.
- Builder: `scripts/build_<source>_dataset.py`.
- Canonical output: `data/published/<source>_*.csv` with method/validation documents.
- Replay: use a discrete-candidate evaluator; never interpolate an unmeasured condition under the source-study label.
- Tests: `tests/test_published*.py` or a source-specific equivalent with small fixtures in `tests/fixtures/`.

**New Lab Modality or Assay:**

- Reader/feature code: `src/boec/lab/<modality>.py`.
- Assembly: `src/boec/lab/dataset.py` while keeping each metric in separate columns/tables.
- Human metadata: `data/lab/overlay/`; never place judgement in generated `derived/` output.
- Raw input: `data/lab/raw/<modality>/` plus updated `data/lab/overlay/MANIFEST.sha256` through the established ingestion process.
- Derived output: `data/lab/derived/` only.
- Tests: `tests/test_lab_<modality>.py` and `tests/test_lab_dataset.py`.

**Utilities:**

- Shared scientific helpers: the closest focused module under `src/boec/`; avoid a generic `utils.py` because units, shapes, and estimands are part of the contract.
- Script-only helpers: keep beside the owning runner when they encode one study’s registration.
- Cross-study regeneration helpers: `src/boec/replay.py`, but keep model fitting and study-specific allocation behind caller-provided builders.

## Special Directories

**`.planning/codebase/`:**

- Purpose: GSD’s current codebase map for later planning/execution and paper-support onboarding.
- Generated: Yes, by codebase mapping.
- Committed: Determined by the GSD orchestrator.

**`data/lab/raw/`:**

- Purpose: Immutable source-of-truth instrument files.
- Generated: No.
- Committed: Yes; integrity is tracked by `data/lab/overlay/MANIFEST.sha256`.

**`data/lab/derived/`:**

- Purpose: Regenerable inspection/candidate tables.
- Generated: Yes, by `scripts/build_lab_dataset.py`.
- Committed: Yes for the current research record, but never treat it as manually editable or automatically promoted.

**`data/oracles/`:**

- Purpose: Stable accepted synthetic instances with audit metadata.
- Generated: Yes, by `scripts/generate_oracles.py`.
- Committed: Yes, because instance identity and rejection history are experiment inputs.

**`results/`:**

- Purpose: Auditable evidence artifacts and logs.
- Generated: Yes.
- Committed: Selected registered/claim-bearing artifacts are committed; `.gitignore` requires explicit handling for new artifacts.

**`results/figures/`:**

- Purpose: Rendered outputs for inspection and paper use.
- Generated: Yes, by `scripts/make_*.py`.
- Committed: Selected figures/artifacts may be committed; source JSON remains authoritative.

**`docs/archive/`:**

- Purpose: Preserve non-current plans/exploration without deleting the research trail.
- Generated: No.
- Committed: Yes; not a default source for current claims.

**`.venv/`, `.pytest_cache/`, `scripts/__pycache__/`, `tests/__pycache__/`:**

- Purpose: Local environment and execution caches.
- Generated: Yes.
- Committed: No; never reference them as research evidence.

---

*Structure analysis: 2026-08-24*
