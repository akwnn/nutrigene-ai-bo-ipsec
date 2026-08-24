# Testing Patterns

**Analysis Date:** 2026-08-24

## Test Framework

**Runner:**
- pytest 9.1.1, pinned in `requirements.txt`.
- Config: `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["src"]`, registered `slow` marker).
- Collection on 2026-08-24 found 1,622 tests. The committed `results/full-test-suite.log` records an earlier 1,300-test run, so it is evidence of a historical green run rather than proof of the current suite.
- Verified current result on 2026-08-24: **1,614 passed, 8 failed, 13 warnings in 360.21 s**. Failures are concentrated in committed-result replay/exactness gates (`test_replay`, `test_d23_doe_subspace`, `test_p4_coord`, `test_q59_map_rescore`, `test_spread_gp`) plus the P7 checkpoint/map-gate path (`test_calibration`).

**Assertion Library:**
- Native Python `assert` plus `pytest.raises`, `pytest.approx`, fixtures, parametrization, marks, and conditional skips.
- SciPy/NumPy reference implementations are used for statistical cross-checks, for example in `tests/test_final_spade_statistics.py` and `tests/test_calibration.py`.

**Run Commands:**
```bash
.venv/bin/pytest                         # Run all tests, including registered slow kill conditions
.venv/bin/pytest -m "not slow"           # Fast development subset
.venv/bin/pytest tests/test_<area>.py -q # Focused module/workstream validation
.venv/bin/pytest --collect-only -q       # Verify collection and current test count
.venv/bin/python scripts/validate_final_spade_release.py --pre-release
                                         # Publication checks while final benchmark is absent
.venv/bin/python scripts/validate_final_spade_release.py
                                         # Full publication release gate
```
- No watch-mode plugin or coverage command/configuration is detected.

## Test File Organization

**Location:**
- Tests live in the separate top-level `tests/` directory.
- Core modules are mirrored by subject (`src/boec/campaign.py` → `tests/test_campaign.py`). Research workstreams and scripts have dedicated contract tests (`scripts/run_p3_cells.py` → `tests/test_p3_cells.py`).
- Small committed inputs live under `tests/fixtures/`. Large or sensitive lab-data tests reference `data/lab/` and skip when the raw drop is unavailable.

**Naming:**
- Files: `tests/test_<module-or-workstream>.py`.
- Functions: long behavioral names beginning with `test_`, often encoding the invariant and expected refusal: `test_a_primary_condition_missing_a_mandatory_arm_refuses_a_primary_conclusion` in `tests/test_final_spade_statistics.py`.
- Fixtures: descriptive lower-case names, commonly module-scoped for expensive artefact loading.

**Structure:**
```text
tests/
├── fixtures/                         # Small stable JSON fixtures
├── test_<core_module>.py             # Unit and property tests for src/boec
├── test_<experiment_id>.py           # Script/result fidelity and analysis tests
├── test_final_spade_*.py             # Protocol, statistics, release, reproducibility
└── test_lab_*.py                     # Conditional real-data ingestion/QC tests
```

## Test Structure

**Suite Organization:**
```python
def test_the_rule_is_bitwise_deterministic():
    cand = _grid_candidates(1024, d, seed=7)
    X1 = _grid_candidates(40, d, seed=8)
    first = rule(cand, X1)
    second = rule(cand, X1)
    assert torch.equal(first, second)

def test_invalid_input_refuses_loudly():
    with pytest.raises(ValueError, match="width mismatch"):
        rule(bad_input)
```
This representative pattern appears throughout `tests/test_final_spade_protocol.py`, `tests/test_surrogate.py`, and `tests/test_campaign.py`.

**Patterns:**
- Test scientific identities and invariants, not only example outputs: exact budgets, monotonic curves, bounds, calibration decompositions, deterministic seeds, pairing, and no leakage.
- Add regression tests for every documented failure. Several modules call these “traps,” “gates,” “kills,” or “refusals,” for example `tests/test_surrogate.py`, `tests/test_e2_provenance.py`, and `tests/test_final_spade_reproducibility.py`.
- Cross-check reported results against committed artefacts and independently recomputed references. `tests/test_e2_provenance.py` checks grid/log/document agreement; `tests/test_q50_paired.py` checks paired vectors and statistics.
- Use exact/bitwise comparisons when determinism is part of the contract, and `pytest.approx` with an explicit tolerance for numerical results.
- Mark genuinely expensive optimization or real-data tests with `@pytest.mark.slow`; the marker remains in the default suite because some slow tests are scientific kill conditions (`pyproject.toml`).
- Use `pytest.mark.skipif` only for optional external/raw data or absent committed artefacts, and state the reason, as in `tests/test_lab_protocol.py`, `tests/test_lab_imaging.py`, and `tests/test_q50_paired.py`.

## Mocking

**Framework:** No dedicated mocking framework is detected; `unittest.mock` is not a dominant pattern.

**Patterns:**
```python
class StubEvaluator:
    def truth(self, X): ...
    def observe(self, X): ...

with pytest.raises(DomainError):
    subject(invalid_record)
```
- Prefer small fake evaluators, synthetic tensors/rows, temporary files through `tmp_path`, and direct monkeypatching only where necessary.
- Exercise real NumPy/SciPy/Torch computations for numerical and statistical behavior instead of mocking them.

**What to Mock:**
- Filesystem boundaries and deliberately unavailable/corrupt artefacts using `tmp_path`.
- Minimal evaluator/model interfaces when testing orchestration rather than GP fitting.
- Synthetic ledger, benchmark, and certificate records when testing release-gate semantics (`tests/test_final_spade_reproducibility.py`, `tests/test_final_spade_statistics.py`).

**What NOT to Mock:**
- Statistical formulas, pairing/aggregation, exact tails, multiplicity correction, and calibration identities.
- Seeded design generation, campaign state, resume behavior, and result serialization.
- Real library behavior when the scientific conclusion depends on it; slow tests intentionally exercise actual BO/GP paths.

## Fixtures and Factories

**Test Data:**
```python
def _row(**overrides):
    row = {
        "instance_seed": 0,
        "campaign_seed": 0,
        "arm": "spade_cf_m0",
        "regime_class": "TARGET",
    }
    row.update(overrides)
    return row
```
- Dictionary factories with overrides are the standard way to build statistical rows, notably in `tests/test_final_spade_statistics.py`.
- Seeded tensor helpers create deterministic candidate sets in `tests/test_final_spade_protocol.py`.
- Stable prefix fixtures are stored in `tests/fixtures/prefix_stage1.json` and `tests/fixtures/prefix_stage2.json`.

**Location:**
- Keep local factories in the test module that owns the schema.
- Put small shared immutable fixture files in `tests/fixtures/`.
- Do not copy raw lab data into tests; tests read `data/lab/` conditionally and validate checksums/manifests through `src/boec/lab/manifest.py` and `tests/test_lab_manifest.py`.

## Coverage

**Requirements:** None enforced. There is no coverage configuration, threshold, CI gate, or `pytest-cov` dependency in `requirements.txt`/`pyproject.toml`.

**View Coverage:**
```bash
# Not currently configured. Add pytest-cov and a declared threshold before treating
# coverage as a project quality gate.
```
- Test volume is high (1,622 collected), but count is not line/branch coverage. Script-heavy `scripts/` and manuscript-to-artefact linkage need explicit review even when the suite is green.

## Test Types

**Unit Tests:**
- Numerical functions, design generators, schema validation, error paths, and exact statistical calculations in `tests/test_calibration.py`, `tests/test_designspace.py`, `tests/test_metrics.py`, and `tests/test_final_spade_statistics.py`.

**Integration Tests:**
- Full campaigns, persistence/resume, real GP fitting, script/result gates, and release validation. Representative files are `tests/test_campaign.py`, `tests/test_runner.py`, `tests/test_replay.py`, `tests/test_e2_provenance.py`, and `tests/test_final_spade_reproducibility.py`.
- Lab ingestion tests cover manifests, FCS parsing/gating, imaging QC, plate parsing, and candidate-only promotion safeguards in `tests/test_lab_*.py`; several skip if local raw data is unavailable.

**E2E Tests:**
- No browser/UI E2E framework is used.
- The closest E2E path is experiment script → committed result artefact → analysis → manuscript/release validator. `scripts/validate_final_spade_release.py` is the publication-level gate.

## Common Patterns

**Async Testing:**
```python
# Not applicable: the codebase is synchronous and CPU-oriented.
```
- Parallel experiment execution is validated through deterministic shards, manifests, merge completeness, and replay rather than async unit tests.

**Error Testing:**
```python
with pytest.raises(ValueError, match="m must be non-negative"):
    local_wells(cand, mean, X1, lengthscales, -1)
```
- Match meaningful error text when it documents the scientific failure.
- Pair each release check with both a synthetic violation and a clean case, as required by `scripts/validate_final_spade_release.py` and implemented in `tests/test_final_spade_reproducibility.py`.

---

*Testing analysis: 2026-08-24*
