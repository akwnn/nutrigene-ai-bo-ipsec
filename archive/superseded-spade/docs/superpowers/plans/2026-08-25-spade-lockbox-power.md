# SPADE Lockbox Power Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frozen, deterministic development-based power gate that selects an
immutable lockbox prefix of 350–2,000 landscapes per family, or stops before opening the
lockbox when map and regret planning power are inadequate.

**Architecture:** A pure `boec.spade_power` module owns statistical calculations and the
exact power-artifact schema. A write-once planner validates selected-protocol and
development provenance, computes the artifact without importing lockbox outcomes, and
commits the chosen prefix. The guarded lockbox runner, analyzer, and release validator
then consume and independently bind that artifact instead of trusting a hard-coded
sample size.

**Tech Stack:** Python 3.11, NumPy, SciPy, PyYAML, deterministic labelled seeds, canonical
JSON/SHA-256, gzip JSONL, pytest, Git provenance.

## Global Constraints

- SPADE, Sobol48, and qLogNEI48 retain exactly 48 evaluations per campaign.
- The power rule is frozen before development outcomes are generated.
- Development evidence is family-held-out under unanimous leave-one-family-out selection.
- Map and regret non-inferiority margins are both exactly `0.02`.
- One-sided type-I error is `0.05`; target power is `0.80`.
- Candidate lockbox sizes are every integer from 350 through 2,000, inclusive.
- Analytic paired-normal power and the exact lower bound of the nonparametric sensitivity
  power must both be at least `0.80` in every development family and endpoint.
- Sensitivity uses 2,000 deterministic nested-prefix replicates and a one-sided 95%
  Clopper-Pearson lower bound.
- No size through 2,000 means `INSUFFICIENT_POWER` and mandatory stop.
- No lockbox outcome file may be imported, read, or generated while implementing or
  running the power planner.
- Existing development or lockbox artifacts are write-once and never overwritten.
- No biological, wet-lab, GMP, manufacturing-validation, or guaranteed-publication claim.

---

## File structure

- Create `src/boec/spade_power.py`: pure power mathematics, decision construction, exact
  artifact validation.
- Create `scripts/plan_spade_lockbox_power.py`: development/selection loading, provenance,
  write-once CLI.
- Create `tests/test_spade_power.py`: independent numerical and decision-rule tests.
- Create `tests/test_spade_power_plan.py`: artifact, held-out, source-freeze, and tamper
  tests.
- Modify `scripts/run_spade_development.py`: validate frozen power-source/design hashes.
- Modify `scripts/run_spade_lockbox.py`: consume committed power artifact and dynamic `n`.
- Modify `scripts/analyse_spade_lockbox.py`: dynamic registered grid and power provenance.
- Modify `scripts/validate_spade_lockbox_release.py`: independently load and bind power.
- Modify `tests/test_spade_development.py`, `tests/test_spade_lockbox.py`, and
  `tests/test_spade_release.py`: new schemas and adversarial integration.
- Modify `configs/experiment/spade-joint.yaml`, the parent protocol design, generator
  manifest, `.gitignore`, and `.planning/STATE.md`: freeze contracts and progress.

---

### Task 1: Pure deterministic power engine

**Files:**
- Create: `src/boec/spade_power.py`
- Create: `tests/test_spade_power.py`

**Interfaces:**
- Produces: `PowerConstants`, `paired_normal_power`, `sensitivity_power_curve`,
  `plan_lockbox_sample_size`, `validate_power_plan_payload`.
- Consumes: `boec.seedbook.derive_seed`, NumPy, `scipy.stats.beta`, and
  `scipy.stats.norm`.

- [ ] **Step 1: Write independent analytic-power tests**

```python
def test_paired_normal_power_matches_literal_fixture():
    constants = PowerConstants()
    got = paired_normal_power(mean=0.0, standard_deviation=0.2, n=350,
                              constants=constants)
    assert got == pytest.approx(0.5893895935672152, abs=1e-15)

def test_zero_variance_and_noninferior_margin_are_fail_closed():
    c = PowerConstants()
    assert paired_normal_power(0.019, 0.0, 350, c) == 1.0
    assert paired_normal_power(0.02, 0.0, 350, c) == 0.0
    assert paired_normal_power(0.021, 0.1, 2000, c) < 0.05
```

Calculate the literal fixture independently in the test from the frozen normal quantile,
not by calling production helpers.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONPATH=.:src .venv/bin/pytest -q tests/test_spade_power.py
```

Expected: import failure because `boec.spade_power` does not exist.

- [ ] **Step 3: Implement frozen constants and analytic power**

```python
@dataclass(frozen=True)
class PowerConstants:
    minimum_n: int = 350
    maximum_n: int = 2000
    margin: float = 0.02
    alpha: float = 0.05
    target_power: float = 0.80
    sensitivity_replicates: int = 2000
    sensitivity_confidence: float = 0.95
    root_seed: int = 2_026_08_25

def paired_normal_power(mean: float, standard_deviation: float, n: int,
                        constants: PowerConstants = PowerConstants()) -> float:
    # Validate finite real inputs and registered n.
    if standard_deviation == 0.0:
        return 1.0 if mean < constants.margin else 0.0
    z_alpha = float(norm.ppf(1.0 - constants.alpha))
    return float(norm.cdf(
        (constants.margin - mean) * math.sqrt(n) / standard_deviation - z_alpha
    ))
```

Reject booleans, negative/nonfinite standard deviations, out-of-range `n`, and invalid
probability constants.

- [ ] **Step 4: Write deterministic sensitivity tests**

```python
def test_sensitivity_curve_is_seeded_nested_and_exactly_bounded():
    values = np.array([-0.01, 0.00, 0.01, 0.015, 0.02] * 10)
    a = sensitivity_power_curve(values, family="hill", endpoint="map")
    b = sensitivity_power_curve(values, family="hill", endpoint="map")
    assert a == b
    assert len(a) == 1651
    assert a[0].n == 350 and a[-1].n == 2000
    assert all(0 <= row.successes <= 2000 for row in a)
    assert all(0.0 <= row.lower_bound <= row.point_power <= 1.0 for row in a)

def test_family_and_endpoint_labels_derive_independent_sensitivity_streams():
    values = np.linspace(-0.03, 0.03, 50)
    assert sensitivity_power_curve(values, family="hill", endpoint="map") != \
           sensitivity_power_curve(values, family="ackley", endpoint="map")
    assert sensitivity_power_curve(values, family="hill", endpoint="map") != \
           sensitivity_power_curve(values, family="hill", endpoint="regret")
```

- [ ] **Step 5: Implement the vectorized nested-prefix sensitivity curve**

Use one `(2000, 2000)` `int32` index matrix generated from
`derive_seed(root_seed, "lockbox_power_sensitivity", family, endpoint)`. Gather the 50
held-out values, then use cumulative sums and squared sums to calculate every prefix's
Bessel-corrected standard deviation without Python loops over replicates. For each
`n=350..2000`, count strict successes of:

```python
upper = sample_mean + norm.ppf(0.95) * sample_sd / np.sqrt(n)
success = upper < 0.02
lower = 0.0 if successes == 0 else beta.ppf(
    0.05, successes, 2000 - successes + 1
)
```

Return immutable `SensitivityPoint(n, successes, point_power, lower_bound)` values.
Clamp only negative roundoff smaller than `1e-14` in variance; reject larger negative or
nonfinite variance.

- [ ] **Step 6: Write conjunction and boundary tests**

```python
def test_plan_selects_the_first_integer_passing_every_family_endpoint(monkeypatch):
    # Fixture curves make n=411 fail one held-out regret lower bound and n=412 pass all.
    decision = plan_lockbox_sample_size(_literal_held_out_vectors())
    assert decision.status == "POWERED"
    assert decision.selected_sample_size == 412
    assert decision.selected_instance_prefix == {"first": 0, "last": 411, "count": 412}

def test_no_size_through_2000_is_an_immutable_negative_decision():
    bad = {family: {endpoint: [0.03] * 50 for endpoint in ("map", "regret")}
           for family in DEVELOPMENT_FAMILIES}
    decision = plan_lockbox_sample_size(bad)
    assert decision.status == "INSUFFICIENT_POWER"
    assert decision.selected_sample_size is None
    assert decision.selected_instance_prefix is None
```

Also prove exact equality at analytic or sensitivity power `0.80` passes, `0.80 - 1e-15`
fails, 350 can be selected, and 2,000 can be selected.

- [ ] **Step 7: Implement the decision and exact artifact validator**

`plan_lockbox_sample_size` requires exactly five registered development families, exactly
`map` and `regret`, and exactly 50 finite differences each. It computes both curves and
scans candidate `n` in ascending order. Return a canonical finite mapping containing
per-family/endpoint means, standard deviations, required sizes, and metrics at the chosen
size (or at 2,000 for `INSUFFICIENT_POWER`).

`validate_power_plan_payload(payload)` requires the exact `boec-spade-lockbox-power-v1`
schema, recomputes `decision_sha256` from canonical `decision`, and enforces null/non-null
status semantics, all frozen constants, five-family/two-endpoint coverage, digest formats,
and prefix arithmetic.

- [ ] **Step 8: Run and commit Task 1**

Run:

```bash
PYTHONPATH=.:src .venv/bin/pytest -q tests/test_spade_power.py tests/test_seedbook.py
```

Expected: all pass.

Commit:

```bash
git add src/boec/spade_power.py tests/test_spade_power.py
git commit -m "feat: add deterministic SPADE lockbox power engine"
```

---

### Task 2: Frozen write-once power planner

**Files:**
- Create: `scripts/plan_spade_lockbox_power.py`
- Create: `tests/test_spade_power_plan.py`
- Modify: `scripts/run_spade_development.py`
- Modify: `tests/test_spade_development.py`
- Modify: `configs/experiment/spade-joint.yaml`
- Modify: `docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md`
- Modify: `results/spade-lockbox-generator-manifest.json`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `plan_lockbox_sample_size`, selector `_load_complete_shards`, selected-protocol
  schema, and the five complete development manifests.
- Produces: `power_payload_from_shards(...)`, `write_power_plan(...)`, and immutable
  `results/spade-lockbox-power.json`.

- [ ] **Step 1: Write RED freeze-contract tests**

Add tests asserting that the config records live SHA-256 values for:

```text
docs/superpowers/specs/2026-08-25-spade-lockbox-power-design.md
src/boec/spade_power.py
scripts/plan_spade_lockbox_power.py
```

Amend the parent protocol Section 10 to name this power design and replace the fixed
`0..349` prefix with the exact 350–2,000 decision rule. Assert the generator manifest's
config/spec/protocol digests match current bytes while status remains `FROZEN_UNOPENED`.

- [ ] **Step 2: Update the frozen configuration and digest validators**

Replace `selected_instance_prefix` with:

```yaml
sample_size_rule:
  minimum: 350
  maximum: 2000
  target_power: 0.80
  paired_margin: 0.02
  one_sided_alpha: 0.05
  sensitivity_replicates: 2000
  sensitivity_lower_confidence: 0.95
  decision: first_integer_passing_all_families_and_both_endpoints
```

Add power design/kernel/planner hashes under `digests`. Make
`run_spade_development.registered_metadata` validate all three actual files against those
hashes before returning metadata. Recompute `protocol_payload_sha256`, `spec_sha256`, and
the generator manifest's config/spec/protocol digests only after source text is final.

- [ ] **Step 3: Write RED planner-provenance and held-out tests**

Fixtures must prove refusal for: dirty tree, uncommitted selected artifact, `NO_SELECTION`,
non-unanimous folds, a fold whose selected candidate differs from the final candidate,
missing/wrong development artifact hash, selection-analysis mismatch, only 49 pairs,
wrong comparator, nonfinite score, existing output, and any source/config/spec/manifest
drift.

Add a source test that rejects imports or path literals containing
`spade-lockbox-*.jsonl`, `spade-lockbox-analysis`, or `analyse_spade_lockbox`.

- [ ] **Step 4: Implement selected/development loading and held-out vectors**

`power_payload_from_shards` must:

1. require a clean source tree and actual committed selected-protocol bytes;
2. validate the exact selected schema and `SELECTED` status;
3. call `_load_complete_shards` with `source_commit=selected["source_commit"]` while
   requiring current config/spec/generator identities;
4. recompute development analysis and compare complete canonical selection trace,
   LOFO folds, analysis SHA, and artifact list to the selected artifact;
5. for each held-out family, require that fold's winner equals the unanimous selected
   candidate and extract 50 matched map/Sobol and regret/qLogNEI differences from raw
   rows;
6. call `plan_lockbox_sample_size` and build the exact provenance envelope.

The envelope contains schema, status, source commit/dirty flag, all frozen digests, actual
source hashes, selected-protocol filename/hash/source, development artifacts, held-out
proof, `decision`, and `decision_sha256`.

- [ ] **Step 5: Implement immutable CLI publication**

```text
python scripts/plan_spade_lockbox_power.py \
  --manifest <five manifest paths> \
  --selection results/spade-selected-protocol.json \
  --out results/spade-lockbox-power.json
```

Only that exact output path is registered. Write canonical JSON through a same-directory
temporary file, fsync, and install write-once. Exit `0` for `POWERED`, `2` for
`INSUFFICIENT_POWER`, and nonzero without an artifact for invalid inputs.

- [ ] **Step 6: Run Task 2 tests and live digest audit**

Run:

```bash
PYTHONPATH=.:src .venv/bin/pytest -q \
  tests/test_spade_power.py tests/test_spade_power_plan.py \
  tests/test_spade_development.py tests/test_lockbox_oracles.py
PYTHONPATH=.:src .venv/bin/python - <<'PY'
from scripts.run_spade_development import registered_metadata
print(registered_metadata())
PY
```

Expected: all tests pass; every digest resolves; generator status remains
`FROZEN_UNOPENED`; no result campaign is run.

- [ ] **Step 7: Commit Task 2**

```bash
git add .gitignore configs/experiment/spade-joint.yaml \
  docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md \
  results/spade-lockbox-generator-manifest.json scripts/run_spade_development.py \
  scripts/plan_spade_lockbox_power.py tests/test_spade_development.py \
  tests/test_spade_power_plan.py
git commit -m "feat: freeze SPADE lockbox power planning"
```

---

### Task 3: Power-controlled variable-size lockbox

**Files:**
- Modify: `scripts/run_spade_lockbox.py`
- Modify: `scripts/analyse_spade_lockbox.py`
- Modify: `tests/test_spade_lockbox.py`
- Modify: `tests/test_spade_power_plan.py`

**Interfaces:**
- Consumes: committed `results/spade-lockbox-power.json` validated by
  `validate_power_plan_payload`.
- Produces: power-bound v2 shard/merged manifests and v2 registered analysis over the
  selected prefix.

- [ ] **Step 1: Write RED access and dynamic-range tests**

Prove access refuses before constructing `_LockboxCore` when the power artifact is
missing, uncommitted, altered, `INSUFFICIENT_POWER`, wrong-selection-bound, wrong-source,
or outside 350–2,000. A valid 412 plan must allow partitions covering `0..411`, reject
key 412, and require exact registered filenames derived from each range.

- [ ] **Step 2: Add exact power access validation**

Change `validate_lockbox_access` to return an exact mapping containing `selection`,
`power_plan`, `sample_size`, and `power_plan_sha256`. It must independently hash actual
power bytes, require the committed HEAD version, validate canonical contents, compare all
selection/config/spec/generator identities, and prove both source commits are ancestors
of the current clean commit.

Do not import development runner, selector, or any development result metric into the
lockbox runner.

- [ ] **Step 3: Replace hard-coded size and upgrade manifest schemas**

Use `boec-spade-lockbox-shard-v2` and `boec-spade-lockbox-manifest-v2`. Add
`power_plan_sha256` and `power_source_commit` to shard/merged provenance. Every study row
adds `"power_plan": power_plan_sha256` to `parent_artifacts`.

All range, count, filename, local-grid, resume, merge, and completion checks take the
validated selected size. Merging requires each family to cover exactly `0..n-1` with no
gap or overlap. Registered filenames use four-digit bounds:

```python
return f"spade-lockbox-{family}-{start:04d}-{stop:04d}.jsonl.gz"
```

- [ ] **Step 4: Write RED registered-analysis tests for arbitrary n**

Use small TEST_ONLY rows and production-shaped 350/412 fixtures to prove the analyzer
requires the manifest-selected `n`, all four families, all three arms, power parent hash,
and power provenance. A globally complete grid with one shard-local relocation must still
fail before pooling.

- [ ] **Step 5: Make registered analysis sample-size explicit**

Upgrade analysis schema to `boec-spade-lockbox-analysis-v2`. Add `sample_size` and
`power_plan_sha256` to provenance. `analyse_lockbox_rows(..., execution_mode="REGISTERED",
sample_size=n, provenance=...)` constructs its exact grid from `n`; TEST_ONLY remains
unable to PASS. `analyse_merged_manifest` validates the actual power-controlled merged
manifest before passing rows and `n` to analysis.

- [ ] **Step 6: Run and commit Task 3**

Run:

```bash
PYTHONPATH=.:src .venv/bin/pytest -q \
  tests/test_spade_power.py tests/test_spade_power_plan.py \
  tests/test_spade_lockbox.py tests/test_spade_study.py
```

Expected: all pass without any campaign outcome run.

Commit:

```bash
git add scripts/run_spade_lockbox.py scripts/analyse_spade_lockbox.py \
  tests/test_spade_lockbox.py tests/test_spade_power_plan.py
git commit -m "feat: bind SPADE lockbox size to frozen power"
```

---

### Task 4: Power-bound release validation

**Files:**
- Modify: `scripts/validate_spade_lockbox_release.py`
- Modify: `tests/test_spade_release.py`

**Interfaces:**
- Consumes: merged v2 manifest, selected protocol, power plan, v2 analysis, and all raw
  shard artifacts.
- Produces: `boec-spade-lockbox-release-v2` with independently bound power provenance.

- [ ] **Step 1: Write RED adversarial release tests**

Extend the full file-based release fixture with an actual power artifact. Test every
corruption independently: absent power file, malformed JSON, schema addition/removal,
actual hash mismatch, manifest hash mismatch, selected-protocol mismatch, source mismatch,
decision digest mismatch, changed selected `n`, `INSUFFICIENT_POWER`, wrong row parent,
wrong shard count/range, and an alias filename attempting to overwrite another hash
namespace.

All malformed cases must make production `main()` write a complete FAIL report rather
than raise.

- [ ] **Step 2: Load and hash the power artifact independently**

Add required CLI argument:

```text
--power results/spade-lockbox-power.json
```

`load_release_inputs` stores its actual hash only under
`actual_hashes["top_level"]["power_plan_sha256"]`, parses strict finite JSON, and calls
the pure exact validator. Any failure becomes an accumulated violation.

- [ ] **Step 3: Bind power through every release check**

Remove `LOCKBOX_SAMPLE_SIZE = 350`. Derive `n` only from the validated power artifact,
then require equality with merged manifest, shard manifests, analysis provenance, row
power parents, range coverage, expected global keys, and release-reported sample size.

Recompute the complete v2 REGISTERED analysis with that `n` and compare canonical bytes.
The final report records actual power hash, power status, and selected size. PASS is
impossible unless status is `POWERED` and every power binding is exact.

- [ ] **Step 4: Run and commit Task 4**

Run:

```bash
PYTHONPATH=.:src .venv/bin/pytest -q \
  tests/test_spade_release.py tests/test_spade_lockbox.py \
  tests/test_spade_power_plan.py tests/test_reliable_region.py
```

Expected: all pass; only the existing Torch deprecation warnings may remain.

Commit:

```bash
git add scripts/validate_spade_lockbox_release.py tests/test_spade_release.py
git commit -m "fix: bind SPADE release to powered sample size"
```

---

### Task 5: Freeze, review, and authorize development execution

**Files:**
- Modify: `.planning/STATE.md`
- Modify: `.superpowers/sdd/progress.md` (ignored execution ledger only)

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: independently approved clean commit from which all development campaigns can
  be generated.

- [ ] **Step 1: Run focused and broader suites**

```bash
PYTHONPATH=.:src .venv/bin/pytest -q \
  tests/test_spade_power.py tests/test_spade_power_plan.py \
  tests/test_spade_development.py tests/test_spade_lockbox.py \
  tests/test_spade_release.py tests/test_seedbook.py tests/test_variance_reduction.py \
  tests/test_reliable_region.py tests/test_spade.py tests/test_lockbox_oracles.py \
  tests/test_spade_study.py
```

Run `py_compile` for all new/changed scripts and `git diff --check`.

- [ ] **Step 2: Perform independent statistical review**

Give the reviewer the exact Task 1–2 diff and require verification of formula orientation,
strict margin direction, zero variance, labelled seeds, Bessel variance, Clopper-Pearson
tail, equality at 0.80, held-out proof, and first-passing integer behavior.

- [ ] **Step 3: Perform independent provenance/security review**

Give the reviewer the exact Task 2–4 diff and require an end-to-end trace from committed
selection and development shards through power artifact, access, raw rows, shard merge,
analysis recomputation, and release. Require adversarial byte/range/source/schema checks
and zero Critical or Important findings.

- [ ] **Step 4: Record only verified state**

Update `.planning/STATE.md` with commits, test counts, review verdicts, and the fact that
no development or lockbox outcome has yet run. Do not claim power or performance before
the power artifact exists.

- [ ] **Step 5: Commit the reviewed pre-analysis state**

```bash
git add .planning/STATE.md
git commit -m "docs: authorize powered SPADE development study"
```

The worktree must be clean after this commit. Only then may the five registered
development families run from this exact source commit.

## Self-review

- Spec coverage: Tasks 1–5 cover every section of the approved power design: mathematics,
  held-out extraction, uncertainty, decision, immutable artifact, lockbox integration,
  release binding, failure handling, tests, and claim boundary.
- Scope: the plan adds only the missing power/sample-size mechanism and its required
  provenance chain; SPADE and the 48-evaluation campaign algorithm are unchanged.
- Type consistency: `PowerConstants`, `validate_power_plan_payload`, `power_plan_sha256`,
  `power_source_commit`, and dynamic `sample_size` are introduced once and consumed under
  the same names.
- Outcome boundary: no task executes development or lockbox campaigns.
