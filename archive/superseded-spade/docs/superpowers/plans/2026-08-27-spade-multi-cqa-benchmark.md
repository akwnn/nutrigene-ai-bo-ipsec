# SPADE Multi-CQA Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a reproducible registered synthetic comparison showing when a scalar primary-CQA certificate releases unsafe recipes and when the joint SPADE overlay safely abstains or shrinks the operating region.

**Architecture:** A new benchmark module owns bounded vector-valued synthetic families, indexed noisy observations, scalar-baseline scoring, joint-overlay scoring, and JSON-safe aggregate metrics. A small CLI script runs one or more registered families and writes canonical JSON. Existing scalar SPADE files and lockbox artifacts remain untouched.

**Tech Stack:** Python 3.11, PyTorch, BoTorch/GPyTorch via existing `build_gp`, existing reliable-region primitives, PyYAML, pytest.

## Global Constraints

- Use exactly 48 observed recipes and a shared 4,096-point candidate grid for the registered protocol.
- Use three synthetic CQAs (identity, viability, yield), thresholds `0.50`, `gamma=0.95`, `alpha=0.95`, `sigma_rel=0.04`, `sigma_add=0.01`.
- Fit scalar baseline and joint overlay on byte-identical inputs; truth is evaluation-only.
- Use 25 paired replicates per family with two algorithm seeds averaged at replicate level; smoke runs may override counts and are exploratory.
- Register `aligned`, `moderate_conflict`, and `strong_conflict` Gaussian-peak families with fixed centers and widths.
- Serialize finite canonical JSON with protocol/source/family/seed provenance; never modify active Cursor files or scalar lockbox results.

---

### Task 1: Add synthetic vector families and test their deterministic truth

**Files:**
- Create: `src/boec/manufacturing_benchmark.py`
- Create: `tests/test_manufacturing_benchmark.py`

**Interfaces:**
- `SyntheticFamily(name: str, centers: tuple[tuple[float, ...], ...], widths: tuple[float, ...])`.
- `registered_families(dimension: int = 6) -> tuple[SyntheticFamily, ...]`.
- `evaluate_family(family: SyntheticFamily, X: Tensor) -> Tensor` returning finite `(n, 3)` values in `[0, 1]`.

- [ ] **Step 1: Write failing family tests**

```python
def test_registered_families_are_bounded_and_deterministic():
    families = registered_families()
    assert [family.name for family in families] == ["aligned", "moderate_conflict", "strong_conflict"]
    X = torch.rand(7, 6, dtype=torch.double)
    for family in families:
        first = evaluate_family(family, X)
        second = evaluate_family(family, X)
        assert first.shape == (7, 3)
        assert torch.equal(first, second)
        assert bool(torch.all((first >= 0) & (first <= 1)))
```

- [ ] **Step 2: Run the family test and verify RED**

Run: `pytest tests/test_manufacturing_benchmark.py -q`

Expected: FAIL because the benchmark module is absent.

- [ ] **Step 3: Implement the registered family contracts**

Use frozen dataclasses and dimension validation. Define three six-dimensional
families with exactly the centers in the benchmark spec and widths `(5.0, 5.0,
5.0)`. Evaluate each CQA as `exp(-width * squared_distance(first three active
coordinates))`; inert coordinates remain absent from the function. Reject wrong
dimensions, non-finite inputs, unknown family names, and malformed center/width
lengths.

- [ ] **Step 4: Run family tests and verify GREEN**

Run: `pytest tests/test_manufacturing_benchmark.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/boec/manufacturing_benchmark.py tests/test_manufacturing_benchmark.py
git commit -m "feat: add registered multi-CQA synthetic families"
```

### Task 2: Implement paired scalar-versus-joint replicate scoring

**Files:**
- Modify: `src/boec/manufacturing_benchmark.py`
- Modify: `tests/test_manufacturing_benchmark.py`

**Interfaces:**
- `BenchmarkConfig` stores protocol values and validates positive counts/seeds.
- `BenchmarkRow` stores finite JSON-safe per-replicate metrics.
- `run_replicate(family, *, config, replicate_seed, algorithm_seed) -> BenchmarkRow`.
- `aggregate_rows(rows) -> dict[str, object]` reports medians/IQRs and paired counts without pooling grid points.

- [ ] **Step 1: Write failing scoring tests**

Test that a small smoke configuration produces one row with scalar/joint volumes,
unsafe-release rates, answer indicators, containment diagnostics, joint status, and
three endpoint volumes. Test that repeated seeds reproduce the row and that a
strong-conflict smoke family can return abstention with an undefined (JSON `null`)
unsafe rate rather than zero.

- [ ] **Step 2: Run scoring tests and verify RED**

Run: `pytest tests/test_manufacturing_benchmark.py -q`

Expected: FAIL because scoring functions are absent.

- [ ] **Step 3: Implement paired scoring**

Generate one scrambled Sobol stream and split it into 48 training recipes plus the
candidate grid. Evaluate all three latent CQAs, add indexed relative-plus-additive
noise to training observations, and fit the scalar baseline to identity only. Use
the same grid/noise parameters/draws/rho/volume rule as `qualify_multi_cqa` for both
paths. Construct truth masks from the latent grid and sealed noise law only after
both masks are selected. Compute scalar-primary and scalar-against-all containment,
joint containment, issued counts/volumes, unsafe rates (`null` for empty), answer
indicators, and joint endpoint volumes/status/limiting CQA. Seed every stochastic
operation via `derive_seed`; do not use global RNG state.

- [ ] **Step 4: Run scoring tests and verify GREEN**

Run: `pytest tests/test_manufacturing_benchmark.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/boec/manufacturing_benchmark.py tests/test_manufacturing_benchmark.py
git commit -m "feat: score paired scalar and joint CQA certificates"
```

### Task 3: Add the registered runner, configuration, and reproducibility tests

**Files:**
- Create: `scripts/run_spade_multi_cqa_benchmark.py`
- Create: `configs/experiment/spade-multi-cqa-benchmark.yaml`
- Modify: `tests/test_manufacturing_benchmark.py`

**Interfaces:**
- CLI flags: `--out PATH`, `--replicates INT`, `--algorithm-seeds INT` (defaults from config), `--families aligned moderate_conflict strong_conflict`, `--train-count INT`, `--grid-count INT`.
- Output schema: `boec-spade-multi-cqa-benchmark-v1` with `protocol`, `source_commit`, `rows`, and `aggregate`.

- [ ] **Step 1: Write failing runner/config tests**

Assert the YAML fixes all registered values and the runner emits canonical finite
JSON for one replicate. Assert rerunning with the same source/arguments produces
identical rows and that the active scalar config path is not referenced as an output.

- [ ] **Step 2: Run runner tests and verify RED**

Run: `pytest tests/test_manufacturing_benchmark.py -q`

Expected: FAIL because the runner and YAML are absent.

- [ ] **Step 3: Implement configuration and CLI**

Write the explicit registration, load it with `yaml.safe_load`, derive source commit
metadata, iterate requested family/replicate/algorithm-seed pairs, aggregate by
family, and write sorted/indented JSON with `allow_nan=False`. The default command
must be the 25×2 registered run; tests and smoke runs override counts explicitly.

- [ ] **Step 4: Run a one-replicate end-to-end smoke**

Run:

```bash
PYTHONPATH=.:src .venv/bin/python scripts/run_spade_multi_cqa_benchmark.py \
  --out /tmp/spade-multi-cqa-smoke.json --replicates 1 --algorithm-seeds 1 \
  --train-count 16 --grid-count 128
```

Expected: exit 0, valid JSON, one row per requested family, and finite metrics.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_spade_multi_cqa_benchmark.py configs/experiment/spade-multi-cqa-benchmark.yaml tests/test_manufacturing_benchmark.py
git commit -m "feat: register reproducible multi-CQA benchmark runner"
```

### Task 4: Run validation and record scientific boundary

**Files:**
- No additional production files.

- [ ] **Step 1: Run focused and regression tests**

Run: `pytest tests/test_manufacturing_benchmark.py tests/test_manufacturing_qualification.py tests/test_reliable_region.py -q`

Expected: all focused/regression tests pass.

- [ ] **Step 2: Run the exploratory comparison**

Run the registered runner with at least three replicates per family and report
scalar unsafe-release rate versus joint unsafe-release rate, answer/abstention rate,
volume, and containment. Label this output exploratory until the full 25×2 run is
completed.

- [ ] **Step 3: Verify isolation and commit state**

Run `git diff --check`, `git status --short --branch`, and verify
`../spade-campaign` remains unchanged except for its own resume files.

- [ ] **Step 4: Report the exact claim**

State that the benchmark tests a synthetic safety tradeoff—fewer unsafe releases at
the possible cost of smaller/empty regions—not general optimizer superiority or
biological manufacturing performance.
