# SPADE Multi-CQA Qualification Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed, deterministic overlay that fits one scalar SPADE GP per manufacturing CQA and intersects their conservative certificates into a joint ESC-to-EC operating region.

**Architecture:** A new `manufacturing_qualification` module owns immutable CQA/result contracts, validation, per-endpoint sign handling, Bonferroni allocation, seeded reliable-set draws, conservative certificate selection, and constrained setpoint selection. It calls existing scalar `build_gp`, `reliable_set_draws`, and `conservative_set_split` primitives without modifying active SPADE recovery code. A standalone YAML records synthetic defaults and example identity/viability/yield metadata.

**Tech Stack:** Python 3.11, PyTorch tensors, BoTorch/GPyTorch through `boec.surrogate.build_gp`, pytest, YAML configuration.

## Global Constraints

- Keep `src/boec/spade.py`, `src/boec/spade_study.py`, `src/boec/reliable_region.py`, `src/boec/selfcalib.py`, active scalar configs, and `results/` unchanged.
- Use sealed relative-plus-additive assay noise (`sigma_rel`, `sigma_add`) for endpoint draws.
- Allocate `alpha_endpoint = 1 - (1 - alpha) / m`; do not claim joint future-batch pass probability.
- Intersect endpoint masks exactly; empty intersections return `ABSTAIN_EMPTY_JOINT` with no setpoint.
- Treat current ESC-to-EC examples as synthetic fixtures only; do not load unsigned lab candidates.
- Tests must be written and observed failing before production implementation.

---

### Task 1: Define the public data contracts and validation behavior

**Files:**
- Create: `tests/test_manufacturing_qualification.py`
- Create: `src/boec/manufacturing_qualification.py`

**Interfaces:**
- `CqaDefinition` is a frozen dataclass with fields `name`, `units`, `threshold`, `direction`, `gamma`, `assay_id`, `assay_version`, `sigma_rel`, `sigma_add`.
- `bonferroni_endpoint_alpha(alpha: float, n_cqas: int) -> float`.
- `qualify_multi_cqa(X, Y, Yvar, bounds, cqas, *, grid=None, alpha=0.95, n_draws=512, n_rho=64, base_seed=0, latent_inflation=1.0, volume_rule="smallest", utility=None, truth_masks=None, cqa_names=None, fit_restarts=1) -> ManufacturingQualificationResult` (fits on observed `X` and scores the shared candidate `grid`; `grid=None` uses `X`).

- [ ] **Step 1: Write failing validation and alpha tests**

```python
def test_bonferroni_allocation_for_three_cqas():
    assert bonferroni_endpoint_alpha(0.95, 3) == pytest.approx(1 - 0.05 / 3)

def test_validation_rejects_mismatched_cqa_columns():
    with pytest.raises(ValueError, match="Y.*shape|cqa"):
        qualify_multi_cqa(torch.zeros(4, 1), torch.zeros(4, 1),
                          torch.ones(4, 2), torch.tensor([[0.], [1.]]),
                          (definition("identity"), definition("viability")))
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_manufacturing_qualification.py -q`

Expected: FAIL because the module and public functions do not exist.

- [ ] **Step 3: Implement contracts and centralized validation**

Implement frozen `CqaDefinition`, `EndpointQualification`, and
`ManufacturingQualificationResult` dataclasses. Convert inputs to cloned `torch.double`
tensors; require finite `X`, `Y`, `Yvar`, valid `(n,d)/(n,m)` shapes, `m >= 2`, finite
bounds with upper > lower, exactly `m` definitions, unique non-empty names/metadata,
valid directions, open `gamma`, paired non-negative noise with at least one positive
component, integer seeds/draw counts, optional matching `cqa_names`, utility shape,
and boolean truth-mask shapes. Implement the exact Bonferroni formula and expose all
validation errors as `ValueError` before model fitting.

- [ ] **Step 4: Run validation tests to verify they pass**

Run: `pytest tests/test_manufacturing_qualification.py -q`

Expected: PASS for the alpha and validation cases.

- [ ] **Step 5: Commit**

```bash
git add src/boec/manufacturing_qualification.py tests/test_manufacturing_qualification.py
git commit -m "feat: add multi-CQA qualification contracts"
```

### Task 2: Implement endpoint fitting, certificate intersection, and setpoint selection

**Files:**
- Modify: `src/boec/manufacturing_qualification.py`
- Modify: `tests/test_manufacturing_qualification.py`

**Interfaces:**
- Use `build_gp(X, transformed_y[:, None], Yvar[:, j:j+1], bounds, fit=True, fit_restarts=fit_restarts)`.
- Use `reliable_set_draws(model, grid, transformed_threshold, definition.gamma, n_draws, seed, sigma_rel=..., sigma_add=..., latent_inflation=...)`.
- Use `conservative_set_split(draws, alpha_endpoint, n_rho=n_rho, volume_rule=volume_rule)`.
- `EndpointQualification.mask` is a boolean `(n_grid,)` tensor; `ManufacturingQualificationResult.joint_mask` is its exact conjunction.

- [ ] **Step 1: Write failing behavioral tests**

Cover lower-tail sign transformation, exact endpoint-mask intersection, endpoint/joint
volumes, empty-joint abstention, limiting-CQA tie-breaking, constrained utility
setpoint selection, optional truth containment, deterministic per-CQA seeds, and
input immutability. Monkeypatch the imported scalar primitives with tiny deterministic
stand-ins so these tests do not spend time fitting real GPs.

- [ ] **Step 2: Run tests to verify the behavioral failures**

Run: `pytest tests/test_manufacturing_qualification.py -q`

Expected: FAIL in endpoint scoring/result construction because orchestration is absent.

- [ ] **Step 3: Implement minimal orchestration**

For each CQA in order, negate `Y[:, j]` and threshold for `less_equal`, fit an
independent scalar GP, draw the endpoint mask with `derive_seed(base_seed,
"manufacturing-cqa", definition.name, j)`, select its conservative certificate, and
record cross-fit/selection containment and optional truth containment. Intersect masks
with `torch.logical_and`. Set `status` to `QUALIFIED` when non-empty, otherwise
`ABSTAIN_EMPTY_JOINT`; choose the minimum-volume endpoint with name-order tie-break;
when utility exists, maximize only among joint `True` entries and break ties by the
lowest grid index. Store cloned tensors and provenance (seed, alpha allocation,
volume rule, digest).

- [ ] **Step 4: Run focused tests to verify the implementation passes**

Run: `pytest tests/test_manufacturing_qualification.py -q`

Expected: PASS with deterministic endpoint and joint assertions.

- [ ] **Step 5: Commit**

```bash
git add src/boec/manufacturing_qualification.py tests/test_manufacturing_qualification.py
git commit -m "feat: intersect multi-CQA SPADE certificates"
```

### Task 3: Add the registered synthetic configuration and integration checks

**Files:**
- Create: `configs/experiment/spade-multi-cqa-qualification.yaml`
- Modify: `tests/test_manufacturing_qualification.py`

**Interfaces:**
- YAML keys: `schema`, `study_id`, `claim_scope`, `protocol.alpha`, `protocol.n_draws`, `protocol.n_rho`, `protocol.base_seed`, `protocol.certificate_volume_rule`, `protocol.predictive_observation_noise`, and `cqas` entries for synthetic identity, viability, and yield.

- [ ] **Step 1: Write failing configuration tests**

Load the YAML with `yaml.safe_load`, assert the registered defaults (`smallest`,
assay relative/additive noise, explicit seed, three CQAs), and assert the active scalar
SPADE files do not change during the overlay test.

- [ ] **Step 2: Run the configuration tests to verify failure**

Run: `pytest tests/test_manufacturing_qualification.py -q`

Expected: FAIL because the YAML does not exist.

- [ ] **Step 3: Add the standalone synthetic configuration**

Record synthetic-only status, no wet-lab claim, overall alpha `.95`, 512 total draws,
64 Vorob'ev levels, base seed `270827`, `smallest` volume rule, assay noise mode,
and explicit example CQA metadata. Do not reference active result artifacts.

- [ ] **Step 4: Run focused and relevant regression tests**

Run: `pytest tests/test_manufacturing_qualification.py tests/test_reliable_region.py -q`

Expected: PASS with no changes to existing reliable-region behavior.

- [ ] **Step 5: Commit**

```bash
git add configs/experiment/spade-multi-cqa-qualification.yaml tests/test_manufacturing_qualification.py
git commit -m "chore: register synthetic multi-CQA configuration"
```

### Task 4: Verify the branch and document handoff

**Files:**
- No production files beyond Tasks 1–3.

- [ ] **Step 1: Run the complete test suite**

Run: `pytest -q`

Expected: all existing tests plus the new multi-CQA tests pass.

- [ ] **Step 2: Run static/reproducibility checks**

Run: `git diff --check`, `git status --short`, and verify the active Cursor worktree
`../spade-campaign` remains at its original source commit and has no files changed by
this branch.

- [ ] **Step 3: Commit test-only fixes atomically if needed**

If verification requires a test correction, stage only
`tests/test_manufacturing_qualification.py` and commit it with:

```bash
git add tests/test_manufacturing_qualification.py
git commit -m "test: harden multi-CQA qualification checks"
```

- [ ] **Step 4: Report completion boundaries**

Report branch, commits, test commands/results, and the explicit limitation that the
overlay is computational/synthetic until signed multi-CQA ESC-to-EC measurements and
new prospective lockbox families exist.
