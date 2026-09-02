# External Integrations

**Analysis Date:** 2026-08-26

## APIs & External Services

**Published scientific source:**
- Hall, Lin & Ogle (2025), *Scientific Reports* 15:24479, DOI 10.1038/s41598-025-09256-9 - biological/design inspiration and the real-data replay source.
  - SDK/Client: none. Source figures are checked into `data/external/hall_ogle_2025/`; the independent transcription is in `data/external/extraction_a/`.
  - Auth: none; the article is open access (CC-BY), documented in `data/published/EXTRACTION_METHOD.md`.
  - Processing: `scripts/digitize_hall_ogle.py` reads the Springer Nature figure PNGs; `scripts/build_published_dataset.py` reconciles them with the independent extraction and emits `data/published/hall_ogle_2025_stage1.csv` and `data/published/hall_ogle_2025_stage2.csv`.
  - Verification: `src/boec/published.py`, `data/published/VALIDATION_REPORT.md`, `docs/pdf_crosscheck.md`, and `docs/source_verification.md` preserve discrepancies, optical uncertainty, structural checks, and source-level decisions.

**Network APIs:**
- None in runtime code. Experiment, data-ingestion, and paper-support workflows operate on committed local files; no HTTP client, cloud SDK, SaaS API, or live download path is detected in `src/` or the principal build scripts.
- External literature links in `docs/` are citations and audit references, not runtime integrations.

## Data Storage

**Databases:**
- Not detected. There is no SQL database, ORM, or connection configuration.
- The repository itself is the versioned evidence store. JSON/CSV/Parquet files under `results/` and `data/` are the research database of record.

**File Storage:**
- Local filesystem and Git only.
- `data/oracles/` holds immutable, versioned synthetic landscape ensembles in Parquet with JSON construction audits; `src/boec/oracles.py` is the read interface.
- `results/` holds committed experiment outputs, checkpoints, logs, validation gates, and figures.
- `data/lab/raw/` holds immutable instrument exports; `data/lab/overlay/` holds human classifications and gates; `data/lab/derived/` holds regenerable outputs. This three-layer contract is defined in `data/lab/README.md` and enforced by `src/boec/lab/manifest.py`.
- `data/published/` holds the canonical published-data replay tables plus extraction and validation reports.

**Caching:**
- No external cache service.
- Long-running scripts use result JSON files as resumable checkpoints, skip completed `(configuration, instance, seed)` keys, and rewrite the consolidated artefact. Examples: `scripts/run_p6_families.py`, `scripts/run_q52_budget_to_target.py`, and `scripts/run_q59_hartmann_no_screen.py`.
- Python `__pycache__/` and `.pytest_cache/` are local development caches only and are not scientific evidence.

## Instrument and File Interfaces

**Flow cytometry:**
- CytoFLEX LX/CytExpert exports - FCS event files plus `.xit` experiment state and `ExpSummaryForAPI.xml` sidecars under `data/lab/raw/flow/`.
  - Client: `flowio` and `flowutils` through `src/boec/lab/fcs.py` and `src/boec/lab/gating.py`.
  - Output: acquisition metadata, channel identity, compensation/transform-aware gating candidates, and sensitivity sweeps in `data/lab/derived/flow_acquisitions.csv`, `data/lab/derived/channel_identity.json`, and `data/lab/derived/flow_positivity_candidate.csv`.
  - Scientific gate: candidate percentages are not optimizer outcomes until a human completes the gating decision recorded in `data/lab/overlay/GATE.md` and promotes values through `data/lab/overlay/bo_primary_conditions.csv`.

**Microscopy:**
- Leica DMi8 JPEG images with `.jpeg.metadata` JSON sidecars and EVOS JPEG images under `data/lab/raw/microscopy/`.
  - Client: scikit-image in `src/boec/lab/imaging.py`.
  - Output: focus, intensity, texture coverage, Otsu threshold/separability, and acquisition comparability keys in `data/lab/derived/image_features.csv`.
  - Constraint: phase-contrast coverage is a distinct metric and must not be mixed with flow `CD31_pct_flow` or published `CD31_area_per_DAPI`; the separation is recorded in `data/lab/overlay/GATE.md`.

**Plate reader:**
- Thermo Multiskan SkyHigh XLSX endpoint export at 562 nm under `data/lab/raw/plate-reader/`.
  - Client: standard-library ZIP/XML parser in `src/boec/lab/plate.py`.
  - Output: structured plate metadata and BCA standard-curve verdict in `data/lab/derived/plate_reader.json`.
  - Constraint: the file is total-protein/BCA evidence with an unlabelled layout, not a CD31 optimizer response.

**Protocol documents:**
- iPSC-to-endothelial protocol DOCX files under `data/lab/raw/protocols/`.
  - Client: standard-library ZIP/XML parser in `src/boec/lab/protocol.py`.
  - Output: protocol/well mapping in `data/lab/derived/protocol_wellmap.csv`.

## Internal Interfaces

**Evaluator boundary:**
- Optimization code depends on evaluator abstractions rather than directly on a wet lab or one oracle. `src/boec/evaluators.py`, `src/boec/campaign.py`, and `src/boec/lab/evaluator.py` separate proposal generation from synthetic, published lookup, or future human/lab feedback.
- Preserve metric identity and design-space identity at this boundary. `src/boec/space.py` carries metric identity, while `src/boec/lab/dataset.py` and `src/boec/lab/evaluator.py` reject ungated/wrong-metric lab rows.

**Synthetic oracle interface:**
- `src/boec/oracles.py` loads committed oracle instances; `src/boec/torch_oracle.py` exposes them as seeded noisy evaluators; `src/boec/runner.py` and `src/boec/campaign.py` consume the evaluator without knowing its storage format.
- Ensemble directories encode a version hash, for example `data/oracles/biphasic-hill-v8+82f6db7c8f77/`. The committed Parquet is authoritative; generation code in `scripts/generate_oracles.py` is the audit trail.

**Published replay interface:**
- `src/boec/published.py` validates/reconciles the digitized design; `src/boec/replay.py` and `scripts/run_replay_hall_ogle.py` consume canonical coded CSVs.
- Use coded `-1/0/+1` factor levels. Do not import contested physical Collagen IV concentrations into the computational design; the unresolved source inconsistency is recorded in `docs/source_verification.md`.

**Lab promotion interface:**
- `scripts/build_lab_dataset.py` reads all raw and overlay files and writes only derived evidence; it does not invent a BO response.
- `data/lab/overlay/bo_file_roles.csv` classifies every raw file, `data/lab/overlay/bo_primary_conditions.csv` is the human-owned campaign table, and `data/lab/overlay/GATE.md` records unresolved scientific judgments.
- `src/boec/lab/evaluator.py` fails closed with a gating error when response values are absent or invalid. Preserve that refusal rather than substituting inferred or image-derived values.

## Authentication & Identity

**Auth Provider:**
- Not applicable. There are no user accounts, sessions, OAuth providers, or service credentials.
- Git commit identity and SHA are provenance identifiers, not application authentication.

## Monitoring & Observability

**Error Tracking:**
- No external error-tracking service.
- Failures surface through exceptions, nonzero process exits, pytest failures, and explicit scientific gates in JSON/log artefacts.

**Logs:**
- CLI scripts print progress and save companion `.log` files under `results/`; examples include `results/e2.log`, `results/p1-kernel-gate.log`, and `results/final-spade-certificate.json`.
- Machine-readable artefacts commonly include provenance envelopes with git SHA, dirty state, Python/package versions, argv, timestamps, and thread settings. Follow `scripts/run_p1_kernel_gate.py`, `scripts/run_p3_cells.py`, or `scripts/run_q52_budget_to_target.py` for new paper-critical runs.
- `data/lab/derived/RUN.json` records lab-ingestion counts, checksum status, and whether any output is eligible for optimizer promotion.

## CI/CD & Deployment

**Hosting:**
- Not applicable. The project is a local/repository-based research workflow, not a network service.

**CI Pipeline:**
- `.github/workflows/spade-distributed.yml` is a manual-only (`workflow_dispatch`) execution workflow for registered SPADE development or lockbox shards. It is not a general CI or quality gate: it has no `push`, `pull_request`, or scheduled trigger and does not run pytest, lint, coverage, analysis, selection, or release validation.
- Dispatch requires an exact 40-character `source_sha` plus the phase-specific confirmation string. The workflow binds both the event and workflow source to that SHA, checks out a clean tree with read-only contents permission, pins `actions/checkout`, `actions/upload-artifact`, and the Linux/amd64 Python 3.11.15 container by immutable digest.
- `scripts/make_spade_actions_matrix.py` generates and validates one exact no-gap matrix. Development uses 65 logical width-4 family/key shards packed into 33 jobs. Lockbox uses width-10 ranges and creates 35 through 200 jobs from the exact committed canonical `POWERED` sample-size prefix (`n=350..2000`); it refuses a wrong source SHA, uncommitted/drifted artifact, noncanonical JSON, or non-`POWERED` decision.
- The workflow caps GitHub runners at 40 in parallel. `scripts/run_spade_actions_worker.py` enforces CPU-only, single-thread NumPy/BLAS/Torch execution, and each runner job starts at most two worker processes concurrently. Development jobs use one pair; lockbox jobs run two sequential pairs over the four families.
- Each completed logical shard is uploaded as an uncompressed, non-overwriting, 90-day artifact containing the raw `.jsonl.gz`, `.sha256`, `.resume.json`, and `.manifest.json` files. The workflow intentionally does not inspect outcomes or merge shards.
- Development artifacts are merged separately with `scripts/merge_spade_development_shards.py`. The merger requires exact `[0,50)` family coverage, canonical row order, matching clean registered provenance and execution environments, authenticated parent hashes/commands, exact repository result paths, and write-once atomic promotion.
- General verification remains local: `pytest` uses `pyproject.toml`, and dedicated release/fidelity scripts such as `scripts/validate_final_spade_release.py`, `scripts/run_k1_replay_gate.py`, and `scripts/probe_e2_determinism.py` compare regenerated outputs with committed evidence.
- Git history is part of the scientific workflow because preregistrations and analysis decisions cite commits in `configs/experiment/`, `docs/OPEN-QUESTIONS.md`, and final-study scripts.

## Environment Configuration

**Required env vars:**
- No secrets or service variables.
- Local numerical drivers commonly set `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`, and `OPENBLAS_NUM_THREADS=1` before NumPy/Torch imports. The distributed path has its own exact contract: `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `PYTHONHASHSEED=0`, and an empty `CUDA_VISIBLE_DEVICES`; `scripts/run_spade_actions_worker.py` validates these values and freezes Torch intra/inter-op threads.
- `PYTHONPATH=src` appears in older diagnostic command examples, but the supported setup is an editable install (`pip install -e .`) per `pyproject.toml` and `requirements.txt`.

**Secrets location:**
- Not applicable. No secrets store or `.env` integration is used or required.

## Webhooks & Callbacks

**Incoming:**
- None. The system has no HTTP server or webhook endpoints.

**Outgoing:**
- None. Runtime code does not post results to external services.

## Provenance and Integrity Integrations

**Git:**
- Several result scripts invoke the local Git CLI to embed `HEAD`, dirty state, and registration/code commits; examples include `scripts/run_k6b_conservative.py`, `scripts/run_p3_cells.py`, and `scripts/analyse_final_spade_benchmark.py`.
- Paper-critical preregistrations are committed before the governed run, especially `configs/experiment/e2.yaml`, `configs/experiment/e4.yaml`, and `docs/SPADE-FINAL-SPEC.md`. Do not edit a preregistered value without versioning and recording the reason.
- The SPADE Actions planner and development merger also bind work to the current clean commit. The merger carries an authenticated canonical parent ledger into every merged row, resume checkpoint, and manifest so downstream selection and power planning retain the original shard hash, command, and provenance chain.

**Checksums:**
- `data/lab/overlay/MANIFEST.sha256` records SHA-256 and size for immutable raw lab files.
- `src/boec/lab/manifest.py` classifies every file, computes current SHA-256 values, reports mismatches/missing/unmanifested paths, and excludes generated `data/lab/derived/` files from the integrity domain.
- `scripts/build_lab_dataset.py` carries checksum results into `data/lab/derived/file_index.csv` and `data/lab/derived/RUN.json`.

**Independent source reconciliation:**
- The Hall/Ogle dataset is not a single scrape. `data/external/hall_ogle_2025/` and `data/external/extraction_a/` are independent readings; `src/boec/published.py` encodes known cell/median discrepancies, and `docs/pdf_crosscheck.md` records the adjudicating PDF reads.
- Optical reading uncertainty, biological quartiles, and distribution-assumption-derived SD are kept as separate fields in `data/published/`; new analysis should prefer raw quartile information over collapsing everything to `response_sd`.

## Integration Constraints for Paper Work

- Cite machine evidence by exact artefact path under `results/` and link interpretation to the governing preregistration or method section. Do not treat prose alone as the numeric source.
- Describe the synthetic Hill ensemble as structurally inspired by Hall/Ogle, not fitted or biologically calibrated; the distinction is explicit in `docs/PROJECT-DOSSIER.md` and `docs/PROMPTS-NEXT.md`.
- Keep three outcome identities separate: synthetic oracle values, Hall/Ogle `CD31_area_per_DAPI`, and in-house flow `CD31_pct_flow`/microscopy coverage. `src/boec/space.py` and `data/lab/overlay/GATE.md` make this separation load-bearing.
- Keep the in-house two-factor FN/VTN coating box (0.5-20 micrograms/mL) separate from the six-factor Hall/Ogle cube. The interface and scientific rationale are documented in `docs/LAB-DATA-FOR-BO.md` and `configs/lab/coating_2026-08-06.yaml`.
- Treat empty/gating-pending lab responses as unavailable, not zero, missing-at-random, or inferable. `src/boec/lab/evaluator.py` deliberately refuses them.
- Preserve null and negative results. The replay, robustness, and release artefacts under `results/` are part of the paper's defensibility and are not disposable failed experiments.

---

*Integration audit: 2026-08-26*
