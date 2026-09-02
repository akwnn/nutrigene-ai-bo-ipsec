<!-- refreshed: 2026-08-24 -->
# Architecture

**Analysis Date:** 2026-08-24

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Research protocols and executable entry points                           │
│ `configs/` · `scripts/run_*.py` · `scripts/analyse_*.py`                 │
└───────────────┬─────────────────────────────┬────────────────────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────────┐  ┌───────────────────────────────────────┐
│ Optimisation/experiment core  │  │ Data ingestion and replay             │
│ `src/boec/`                   │  │ `src/boec/published.py`                │
│ campaign, GP, DoE, SPADE      │  │ `src/boec/replay.py`, `src/boec/lab/` │
└───────────────┬───────────────┘  └──────────────────┬────────────────────┘
                │                                     │
                └──────────────────┬──────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Evidence artifacts                                                       │
│ `results/*.json` · `results/*.log` · `data/*/derived-or-canonical files` │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Analysis, figures, and paper-facing interpretation                       │
│ `scripts/analyse_*.py` · `scripts/make_*.py` · `docs/*.md`              │
└──────────────────────────────────────────────────────────────────────────┘
```

The repository is an executable research record for comparing optimisation and design-space methods at a fixed experimental budget. Its original line compares Bayesian optimisation (BO) with static designs and a classical sequential DoE/RSM pipeline on synthetic response landscapes. Its current confirmatory line evaluates SPADE, a two-round boundary-directed method for estimating and certifying acceptable operating regions, against BO, classical, and space-filling comparators. Paper claims are supported by committed JSON artifacts in `results/`, not by prose alone.

The evidence domains remain intentionally separate:

- Synthetic benchmark truth comes from `src/boec/oracles.py` and cached ensembles in `data/oracles/`.
- Published Hall/Ogle measurements are validated by `src/boec/published.py`, stored canonically in `data/published/`, and replayed through `src/boec/replay.py`.
- In-house instrument files remain immutable under `data/lab/raw/`; `src/boec/lab/` produces reviewable derived candidates but does not promote them into optimiser input.

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Campaign engine | Runs the propose → evaluate → update loop, tracks pending points, saves resumable state, and records pre-outcome predictions | `src/boec/campaign.py` |
| Evaluator boundary | Decouples optimisation from the source of outcomes; supports synthetic and lookup-backed observations | `src/boec/campaign.py`, `src/boec/evaluators.py`, `src/boec/torch_oracle.py` |
| Oracle family | Defines noiseless synthetic landscapes, accepted Hill instances, standard benchmark families, and known optima | `src/boec/oracles.py` |
| Surrogate and acquisition | Fits fixed-noise GPs, performs prediction with the repository’s noise-scaling rules, and proposes adaptive batches | `src/boec/surrogate.py`, `src/boec/optimizers.py` |
| Classical pipeline | Implements screening, sub-box construction, central-composite design, RSM fitting, and confirmation | `src/boec/doe.py`, `src/boec/designs.py`, `src/boec/rsm.py`, `src/boec/sequential_rsm.py` |
| Experiment grid | Defines comparable cells, static-design pairing policy, resumable multi-campaign execution, and provenance | `src/boec/runner.py` |
| Scoring and inference | Computes terminal selections, regret curves, constrained/model argmaxes, bootstrap intervals, and diagnostics | `src/boec/metrics.py`, `src/boec/diagnostics.py`, `src/boec/discrimination.py`, `src/boec/budget.py` |
| Replay/regeneration | Reconstructs committed campaigns and family-specific evaluators for exact or tolerance-based gates | `src/boec/replay.py` |
| Design-space mapping | Produces predictive probability maps and map-quality measures such as symmetric difference, IoU, Brier/AUC, and false-inclusion rates | `src/boec/designspace.py`, `src/boec/calibration.py`, `src/boec/norms.py` |
| Certificate estimation | Builds Vorob'ev/conservative acceptable regions and cross-fit containment columns | `src/boec/vorobev.py`, `src/boec/versionc.py` |
| SPADE method | Allocates plate-2 wells between boundary refinement and optional local search, and emits the final-study row schema | `src/boec/final_spade.py`, `src/boec/lse.py` |
| Final prospective runner | Executes registered SPADE and comparator arms per condition with checkpoints and provenance | `scripts/run_final_spade_benchmark.py` |
| Final adjudication | Converts primary rows into feasibility, certificates, kill-ledger verdicts, and Pareto summaries | `scripts/run_final_spade_feasibility.py`, `scripts/analyse_final_spade_benchmark.py`, `scripts/analyse_p8_certificate.py` |
| Figure renderer | Reads committed final-study artifacts only; it cannot fit models or evaluate truth | `scripts/make_final_spade_figures.py` |
| Published-data pipeline | Validates extracted coded designs/responses and emits canonical tables for replay | `src/boec/published.py`, `scripts/build_published_dataset.py`, `scripts/digitize_hall_ogle.py` |
| Lab-data pipeline | Verifies raw-file checksums and derives FCS, imaging, protocol, and plate-reader summaries without automatic promotion | `src/boec/lab/dataset.py`, `scripts/build_lab_dataset.py` |

## Pattern Overview

**Overall:** Layered scientific pipeline with protocol-driven scripts, reusable numerical modules, evaluator inversion, and artifact-based claim gates.

**Key Characteristics:**

- Keep scientific decisions in registered YAML/Markdown protocols such as `configs/experiment/e2.yaml` and `docs/SPADE-FINAL-SPEC.md`; scripts translate those decisions into executable cells.
- Keep reusable mathematics in `src/boec/`; scripts orchestrate studies and write artifacts, while tests exercise both layers.
- Treat the evaluator as the substitution point between synthetic functions, published lookup tables, and eventual laboratory measurements.
- Separate generation, analysis, and rendering. In the final SPADE line, `scripts/run_final_spade_benchmark.py` generates primary rows, analysis scripts derive verdict artifacts, and `scripts/make_final_spade_figures.py` only renders committed artifacts.
- Carry provenance with results: condition, family, dimension, noise, seed/instance, arm, terminal rule, budget, rounds, version information, and registration identity are part of the evidence record.
- Prefer gates that regenerate a committed quantity and compare it at an explicitly justified tolerance; `src/boec/replay.py` centralises reconstruction so each analysis does not invent its own campaign semantics.

## Layers

**Protocol and Registration Layer:**

- Purpose: Freeze estimands, arms, fairness rules, sample sizes, thresholds, kill conditions, and claim boundaries.
- Location: `configs/experiment/`, `configs/lab/`, `docs/SPADE-FINAL-SPEC.md`, `docs/ODIN-SPEC.md`
- Contains: YAML experiment configurations and research specifications.
- Depends on: Prior committed evidence referenced by path and commit.
- Used by: `scripts/run_*.py`, validators, paper-facing documents.

**Domain and Numerical Core:**

- Purpose: Provide landscapes, designs, models, acquisition, region estimation, scoring, and inference.
- Location: `src/boec/`
- Contains: Small Python modules grouped by mathematical responsibility rather than by experiment number.
- Depends on: NumPy, pandas, SciPy, PyTorch, GPyTorch, BoTorch, scikit-learn, statsmodels, and image/data readers declared in `requirements.txt`.
- Used by: All experiment and analysis scripts under `scripts/`.

**Experiment Orchestration Layer:**

- Purpose: Expand registered conditions into campaigns, checkpoint work, enforce pairing/budgets, and serialize raw rows.
- Location: `scripts/run_*.py`, `src/boec/runner.py`, `src/boec/replay.py`
- Contains: Original E/Q/P/F study runners and the prospective `final_spade` runner.
- Depends on: Protocol constants/configs and `src/boec/` numerical modules.
- Used by: Analysis scripts and result gates.

**Evidence Artifact Layer:**

- Purpose: Preserve machine-readable results, logs, manifests, and intermediate scientific records.
- Location: `results/`, `data/oracles/`, `data/published/`, `data/lab/derived/`
- Contains: JSON result envelopes/rows, logs, parquet oracle ensembles, canonical CSVs, derived lab tables, and HTML/PNG figures.
- Depends on: Producing scripts.
- Used by: Analysis, validation, figures, and paper documents.

**Interpretation and Publication Layer:**

- Purpose: Resolve results into claims, limitations, methods, and paper figures.
- Location: `docs/`, `scripts/analyse_*.py`, `scripts/make_*.py`, `results/figures/`
- Contains: Current findings (`docs/FINDINGS-SPADE-FINAL.md`), method records (`docs/METHODS.md`), claim ledgers, and renderers.
- Depends on: Committed artifacts and frozen specifications.
- Used by: Paper drafting and reviewer-defence work.

## Data Flow

### Primary Prospective SPADE Result Path

1. Freeze the study question, conditions, arms, thresholds, cross-fit estimator, inference families, and kill ledger in `docs/SPADE-FINAL-SPEC.md`.
2. Compute feasibility and regime classes before campaigns; write `results/final-spade-feasibility.json` via `scripts/run_final_spade_feasibility.py`.
3. Resolve a condition and deterministic campaign keys from committed prerequisites in `scripts/run_final_spade_benchmark.py`.
4. Construct fresh synthetic evaluators with `src/boec/replay.py` and `src/boec/torch_oracle.py`; Hill instances come from `data/oracles/biphasic-hill-v8+82f6db7c8f77/`, while standard families come from `src/boec/oracles.py`.
5. Generate plate 1 or comparator designs using `src/boec/runner.py`; fit GPs using `src/boec/surrogate.py`.
6. For SPADE arms, select plate-2 boundary/local wells through `src/boec/final_spade.py` and `src/boec/lse.py`; for BO, run the campaign/acquisition loop in `src/boec/campaign.py`; for classical DoE, call `src/boec/doe.py`.
7. Evaluate noisy outcomes while keeping noiseless truth restricted to scoring. Compute rule-A and rule-P regret, probability-map metrics, calibration components, and certificate inputs.
8. Checkpoint campaign rows to sibling `.ckpt.jsonl` files and promote completed condition artifacts under `results/final-spade-primary-*.json` or the registered output path.
9. Analyse committed rows into `results/final-spade-certificate.json`, `results/final-spade-kill-ledger.json`, and `results/final-spade-regret-pareto.json` using `scripts/analyse_final_spade_benchmark.py` and related analyzers.
10. Render figures solely from `results/final-spade-*.json` with `scripts/make_final_spade_figures.py`; interpret them in `docs/FINDINGS-SPADE-FINAL.md` under the condition/rule/sample-size labels frozen by the protocol.

### Original BO-versus-DoE Benchmark Path

1. Load accepted Hill landscapes with `src/boec/oracles.py:load_ensemble` from `data/oracles/`; standard-function sensitivities instantiate classes such as `Hartmann6`, `Ackley`, `Levy`, and `Rosenbrock` from the same module.
2. Wrap truth in `src/boec/torch_oracle.py:BiphasicOracle` or `TorchEvaluator`, which returns noisy observations and plug-in variance without exposing truth to the optimiser.
3. Expand dimension × noise × instance × seed × arm conditions in scripts such as `scripts/run_e2.py`, using the registration in `configs/experiment/e2.yaml`.
4. Route adaptive arms through `src/boec/campaign.py`, static arms through `src/boec/runner.py:static_design`, coordinate descent through `src/boec/baselines.py`, and classical screening/RSM through `src/boec/doe.py`.
5. Score the selected recipe at noiseless truth using `src/boec/diagnostics.py:reported_best_curve` or model-recommendation locators in `src/boec/metrics.py`.
6. Aggregate seeds within instances and compute paired inference with `src/boec/diagnostics.py:instance_bootstrap` plus study-specific Wilcoxon tests.
7. Write raw and summary rows to files such as `results/e2-grid.json`, then use Q/P/F scripts to test mechanisms, sensitivities, map quality, and generality.
8. Consolidate current claim-level results in `docs/MAIN-LINE.md`, `docs/RESULTS.md`, and the SPADE findings documents, always retaining the terminal rule and condition.

### Published-Data Replay Flow

1. Preserve source extractions under `data/external/hall_ogle_2025/` and the independent extraction under `data/external/extraction_a/`.
2. Validate row uniqueness, coded design structure, and recoverable response values with `src/boec/published.py` and `scripts/build_published_dataset.py`.
3. Emit canonical stage tables to `data/published/hall_ogle_2025_stage1.csv` and `data/published/hall_ogle_2025_stage2.csv`, with method and validation records beside them.
4. Restrict proposals to measured rows via `src/boec/evaluators.py:LookupEvaluator`; absent or unextractable conditions fail rather than being interpolated.
5. Replay registered methods using `scripts/run_replay_hall_ogle.py` and write the evidence log to `results/replay-hall-ogle.log`.

### In-House Lab Data Flow

1. Keep instrument outputs immutable in `data/lab/raw/`; verify every file against `data/lab/overlay/MANIFEST.sha256`.
2. Apply human-authored roles and condition metadata from `data/lab/overlay/bo_file_roles.csv` and `data/lab/overlay/bo_primary_conditions.csv`.
3. Run `scripts/build_lab_dataset.py`, which calls `src/boec/lab/dataset.py:build_all` and modality readers in `src/boec/lab/`.
4. Write file provenance, FCS acquisition metadata, candidate gating percentages, imaging features, protocol maps, and plate-reader verdicts to `data/lab/derived/`.
5. Require human sign-off before any `candidate_*` table becomes optimiser input; derived files are explicitly not campaign observations.

**State Management:**

- `src/boec/campaign.py` stores observations, variances, pending points, holdout points, round logs, configuration, and RNG state; it rebuilds the GP from measurements on resume.
- Long runners checkpoint rows incrementally to non-final sibling files, then promote a complete artifact with status/key counts. The final SPADE runner uses `.ckpt.jsonl` beside its output.
- `src/boec/runner.py` skips grid cells already represented on disk.
- Results are immutable evidence by convention; superseded artifacts remain visibly named rather than being silently overwritten.

## Key Abstractions

**Oracle:**

- Purpose: Represent noiseless truth, dimensions, and optionally a known optimum.
- Examples: `src/boec/oracles.py:Oracle`, `HillOracle`, `Hartmann6`, `UnitScaled`, `Embedded`.
- Pattern: Abstract base class over NumPy arrays, with wrapper types for rescaling and embedding.

**Evaluator:**

- Purpose: Supply observable outcomes and variances without granting the optimiser access to truth.
- Examples: torch structural protocol in `src/boec/campaign.py`, NumPy ABC implementations in `src/boec/evaluators.py`, adapters in `src/boec/torch_oracle.py`.
- Pattern: Dependency inversion. Optimisation depends on `evaluate(X) -> (Y, Yvar)`, not on a particular data source.

**Campaign:**

- Purpose: Make the adaptive loop resumable and auditable.
- Examples: `src/boec/campaign.py:Campaign`, `CampaignConfig`, `RoundLog`.
- Pattern: Stateful ask/tell coordinator with deterministic seeding, pending-point tracking, and pre-outcome logs.

**Design and Arm:**

- Purpose: Produce a budgeted sequence/set of measurement locations under a named method.
- Examples: static generators in `src/boec/optimizers.py`, classical pipeline in `src/boec/doe.py`, SPADE allocation in `src/boec/final_spade.py`.
- Pattern: Methods share evaluation budgets but retain method-specific scheduling and pairing exemptions.

**Campaign Record / Artifact Row:**

- Purpose: Make a scientific number attributable and regenerable.
- Examples: `src/boec/replay.py:CampaignRecord`, `src/boec/final_spade.py:ROW_SCHEMA`, JSON rows in `results/`.
- Pattern: Flat, explicit evidence rows nested in a study-level envelope carrying status and provenance.

**Terminal Rule:**

- Purpose: Define which recipe a method ultimately selects before regret is scored at truth.
- Examples: rule A in `src/boec/diagnostics.py`, constrained/grid-screened posterior-mean argmaxes in `src/boec/metrics.py`.
- Pattern: Selection and truth scoring are separate operations; every comparison must name the rule.

**Probability Map and Certificate:**

- Purpose: Move from “best recipe” optimisation to estimation of `D = {x: f(x) >= tau}` and a conservative subset of it.
- Examples: adapters/metrics in `src/boec/designspace.py`, conservative estimation in `src/boec/vorobev.py`, cross-fit columns in `src/boec/versionc.py`.
- Pattern: A seeded evaluation grid carries truth, posterior probabilities, set estimates, map errors, and assurance diagnostics.

## Entry Points

**Package import:**

- Location: `src/boec/__init__.py`
- Triggers: Imports from installed editable package or pytest’s `src` path.
- Responsibilities: Defines package identity; functional entry points live in modules and scripts.

**Original benchmark runner:**

- Location: `scripts/run_e2.py`
- Triggers: Direct Python invocation after editable install.
- Responsibilities: Runs the registered BO/static/coordinate/DoE grid and writes `results/e2-grid.json`.

**Final prospective benchmark:**

- Location: `scripts/run_final_spade_benchmark.py`
- Triggers: `--condition`, optional limits/output, and committed feasibility prerequisites.
- Responsibilities: Runs fresh allocation policies and comparators, checkpoints rows, writes final primary artifacts.

**Final feasibility gate:**

- Location: `scripts/run_final_spade_feasibility.py`
- Triggers: Before any final campaigns.
- Responsibilities: Classifies condition/threshold cells and prevents claims beyond certifiability ceilings.

**Final analysis and validation:**

- Location: `scripts/analyse_final_spade_benchmark.py`, `scripts/validate_final_spade_release.py`
- Triggers: Completed result artifacts.
- Responsibilities: Produce derived evidence, adjudicate registered rules, and verify release completeness/integrity.

**Figure build:**

- Location: `scripts/make_final_spade_figures.py`
- Triggers: Committed `results/final-spade-*.json` files.
- Responsibilities: Render paper figures without recomputing scientific results.

**Published dataset build/replay:**

- Location: `scripts/build_published_dataset.py`, `scripts/run_replay_hall_ogle.py`
- Triggers: Extracted figure data.
- Responsibilities: Validate canonical tables and execute discrete-candidate replay.

**Lab dataset build:**

- Location: `scripts/build_lab_dataset.py`
- Triggers: In-house raw/overlay data tree.
- Responsibilities: Verify and derive candidate tables while preserving the human promotion gate.

## Architectural Constraints

- **Threading:** Numerical experiments are process/single-thread oriented. Runners set `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, and often Torch threads to one; parallel grids should use independent processes rather than nested BLAS pools. `src/boec/runner.py:set_single_threaded` provides the in-process half.
- **Global state:** Randomness is global across Python, NumPy, and Torch in campaign code. Always seed all three through the existing campaign/replay paths and construct a fresh evaluator per campaign so one arm cannot consume another arm’s noise stream.
- **Tensor/array boundary:** The repository contains a torch `Evaluator` protocol in `src/boec/campaign.py` and a NumPy evaluator ABC in `src/boec/evaluators.py`. Use adapters in `src/boec/torch_oracle.py`; do not pass one representation into the other layer implicitly.
- **Truth isolation:** Optimisers receive only noisy `Y` and `Yvar`. Noiseless oracle values are legal only in scoring, feasibility, or simulation diagnostics.
- **Noise semantics:** Known observation variance uses plug-in variance from the observed value. Prediction noise scaling is centralised in `src/boec/surrogate.py:predictive`; bypassing it changes calibration.
- **Fixed budget versus rounds:** Wells/evaluations and sequential rounds are distinct costs. Preserve both in rows and figures; do not collapse one-shot, two-round, three-round, and ten-round arms into a single “budget” statement.
- **Terminal-rule explicitness:** Rule A and posterior/model recommendation rules answer different estimands. Persist the rule in every result/table/figure and never compare columns generated under different rules.
- **Registration boundary:** Final-study constants and claim logic come from `docs/SPADE-FINAL-SPEC.md`; changes affecting outcomes require explicit errata rather than silent code edits.
- **Artifact provenance:** A paper claim must resolve to a committed machine-readable artifact and producing/analyzing script. Logs and prose are supporting records, not substitutes for rows.
- **Raw data immutability:** Never modify files under `data/lab/raw/`; generated files belong in `data/lab/derived/`, and human decisions belong in `data/lab/overlay/`.
- **No automatic lab promotion:** `data/lab/derived/candidate_*` files remain candidates until human sign-off resolves channel/gating/condition identity.
- **Circular imports:** No known circular dependency chain is intentional. Keep `src/boec/replay.py` free of surrogate/design-space fitting; its builder hook exists to prevent runner-specific dependencies from flowing into the shared regeneration gate.

## Anti-Patterns

### Computing Scientific Numbers in Figure Code

**What happens:** A renderer fits a model, evaluates an oracle, or derives an uncommitted statistic while drawing.
**Why it's wrong:** The paper can show a number that exists in no auditable result artifact.
**Do this instead:** Derive the statistic in an analysis script, commit it under `results/`, and keep `scripts/make_final_spade_figures.py` restricted to JSON/NumPy/Matplotlib reads.

### Letting the Optimiser See Truth

**What happens:** Code calls `oracle.f`, `truth`, or analytic variance while choosing points.
**Why it's wrong:** Synthetic ground truth leaks into the method and invalidates the benchmark.
**Do this instead:** Pass only an evaluator implementing the contract in `src/boec/campaign.py`; reserve truth access for scoring functions in `src/boec/metrics.py` and `src/boec/diagnostics.py`.

### Recomputing Variance by Re-evaluating a Stored Point

**What happens:** Analysis calls the noisy evaluator a second time to recover `Yvar`.
**Why it's wrong:** It draws new noise and no longer describes the stored observation.
**Do this instead:** Reconstruct plug-in variance from stored `Y` using `src/boec/torch_oracle.py:_plug_in_yvar`, as centralised by `src/boec/replay.py`.

### Treating Static DoE as a Generic Runner Method

**What happens:** A `GridCell(method="doe")` falls through the adaptive branch.
**Why it's wrong:** It can produce believable BO output labelled as DoE.
**Do this instead:** Call `src/boec/doe.py:run_doe_arm` directly; `src/boec/runner.py:UNWIRED_METHODS` deliberately fails this case loudly.

### Pooling Conditions, Seeds, or Estimands

**What happens:** Rows with different family/dimension/noise/threshold/rule are merged, or repeated seeds are treated as independent landscapes.
**Why it's wrong:** Effective sample size and scientific meaning change while the summary remains numerically plausible.
**Do this instead:** Aggregate seeds within instance, analyse registered condition cells separately, and carry `condition_id`, rule, `n`, `tau`, `gamma`, and `alpha` in every applicable output.

### Treating Derived Lab Metrics as Observations

**What happens:** `data/lab/derived/candidate_*` enters a campaign automatically.
**Why it's wrong:** Channel identity, controls, condition mapping, and assay identity contain human judgement not resolved by arithmetic.
**Do this instead:** Record candidates in `data/lab/derived/`, decisions in `data/lab/overlay/GATE.md`, and promote only a signed condition table.

## Error Handling

**Strategy:** Fail loudly on scientific contract violations, preserve partial work for expensive runs, and represent unavailable evidence explicitly rather than substituting plausible values.

**Patterns:**

- Validate tensor/array shape, dimension, positive variance floors, legal method names, and budget arithmetic at module boundaries (`src/boec/campaign.py`, `src/boec/evaluators.py`, `src/boec/runner.py`).
- Raise on published lookup conditions absent from the measured table or with missing responses (`src/boec/evaluators.py:LookupEvaluator`).
- Reject final-study execution when committed feasibility prerequisites are missing (`scripts/run_final_spade_benchmark.py`).
- Keep checkpoint/partial artifacts on interrupted long runs and promote only on completion.
- Record missing mandatory arms with structured `unavailable_reason`; do not silently drop comparators.
- Skip a figure with an explicit message when its artifact is absent; never fabricate an empty/default result (`scripts/make_final_spade_figures.py`).
- Use status fields such as `COMPLETE`, `NOT RUN`, `INCONCLUSIVE`, `PASS`, and `FAIL` as data, not only prose.

## Cross-Cutting Concerns

**Logging:** Long scripts print cell/campaign progress and redirect durable output to `results/*.log`; result JSON remains the claim source. Campaign round logs preserve model beliefs before outcomes.

**Validation:** Pytest covers modules, experiment contracts, gates, final-study protocol/statistics/reproducibility, published data, and lab ingestion under `tests/`. Release validation is performed by `scripts/validate_final_spade_release.py`.

**Authentication:** Not applicable; the repository is a local scientific workflow with no network service or user identity layer.

**Reproducibility:** Seeds, instance ids, family, versions, registration commit, dirty-tree status, budgets, condition ids, and exact row schemas travel with artifacts. Editable installation is defined in `pyproject.toml`; scripts also use a repository-relative `src` path where needed.

**Paper traceability:** Use `docs/MAIN-LINE.md` for the compact original result skeleton, `docs/FINDINGS-SPADE-FINAL.md` for the current prospective study, `docs/METHODS.md` for method prose, and follow every numerical statement back to a `results/*.json` artifact and its producer.

---

*Architecture analysis: 2026-08-24*
