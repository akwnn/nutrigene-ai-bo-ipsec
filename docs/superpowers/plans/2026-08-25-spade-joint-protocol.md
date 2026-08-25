# SPADE Joint Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver one deterministic 48-evaluation SPADE method, select it on development
families, and validate it once against Sobol48 and qLogNEI48 on a powered untouched-family
lockbox with publication-grade map, regret, and certificate evidence.

**Architecture:** Add focused reusable modules for stateless seeds, the shared learned-noise
GP, variance-reduction acquisitions, predictive reliable regions, current SPADE
orchestration, and randomized lockbox oracles. Keep historical `final_spade.py` untouched
for replay. New runners generate development and lockbox shards; analyzers and a fail-closed
release validator produce the only paper-facing verdicts.

**Tech Stack:** Python 3.11, PyTorch 2.13, BoTorch 0.18.1, GPyTorch 1.15.2, NumPy,
SciPy, pytest, deterministic gzip JSONL, Git/SHA-256 provenance.

## Global Constraints

- Public method name is `SPADE`; do not introduce `SPADE 2`, `spade_v2`, or a second
  paper-facing SPADE arm.
- Every SPADE, Sobol48, and qLogNEI48 campaign has exactly 48 evaluations.
- Primary lockbox condition is d=6, sigma_rel=0.10, sigma_add=0.01, gamma=0.95,
  alpha=0.95, q_tau=0.75.
- Current Hill, Ackley, Hartmann6, Levy, and Rosenbrock evidence is development-only.
- Lockbox generators and keys are frozen before development selection; lockbox outcomes
  cannot be opened before a clean selected-protocol commit.
- All arms use the same learned-noise Matérn-5/2 GP, adaptive menu, terminal Rule P, and
  endpoint implementation.
- Certificate construction uses 4,096 set draws split 2,048/2,048; empirical oracle
  containment across campaigns is confirmatory and cross-fit containment is diagnostic.
- Empty certificates reduce answer rate and never count as containment successes.
- No truth access is permitted in proposal, gate, GP, or terminal-selection interfaces.
- Every new production behavior follows red-green TDD and every result carries protocol,
  source, environment, seed, and parent-artifact provenance.
- No biological, wet-lab, GMP, or manufacturing-validation claim.

---

## File structure

### New reusable modules

- `src/boec/seedbook.py` — labelled stateless seed derivation and indexed observation noise.
- `src/boec/variance_reduction.py` — greedy global/boundary integrated variance reduction.
- `src/boec/reliable_region.py` — predictive reliability maps, gamma-aware set draws,
  conservative certificates, empirical containment, and exact lower bounds.
- `src/boec/spade.py` — current public SPADE configuration, policies, campaign engine, and
  common Sobol/qLogNEI comparator paths.
- `src/boec/lockbox_oracles.py` — four randomized d=6 lockbox generator families and
  optimum audits.
- `src/boec/spade_study.py` — common campaign scoring, row schema, gzip JSONL, manifests,
  pairing, and provenance.

### New study entry points

- `configs/experiment/spade-joint.yaml` — machine-readable frozen protocol.
- `scripts/run_spade_development.py` — development shards for nine candidates and controls.
- `scripts/select_spade_protocol.py` — nested-family selection and protocol freeze.
- `scripts/run_spade_lockbox.py` — guarded paired lockbox shard runner.
- `scripts/analyse_spade_lockbox.py` — confirmatory inference and verdict.
- `scripts/validate_spade_lockbox_release.py` — complete release-integrity gate.

### Principal tests

- `tests/test_seedbook.py`
- `tests/test_variance_reduction.py`
- `tests/test_reliable_region.py`
- `tests/test_spade.py`
- `tests/test_lockbox_oracles.py`
- `tests/test_spade_study.py`
- `tests/test_spade_development.py`
- `tests/test_spade_lockbox.py`
- `tests/test_spade_release.py`

---

### Task 1: Deterministic seeds, evaluator resume, and baseline classification

**Files:**
- Create: `src/boec/seedbook.py`
- Create: `tests/test_seedbook.py`
- Modify: `src/boec/torch_oracle.py`
- Modify: `src/boec/campaign.py`
- Modify: `tests/test_torch_oracle.py`
- Modify: `tests/test_campaign.py`
- Modify: `.gitignore`
- Create: `scripts/audit_historical_replay.py`
- Create: `tests/test_historical_replay_audit.py`

**Interfaces:**
- Produces: `derive_seed(root_seed: int, label: str, *parts: object) -> int`
- Produces: `IndexedGaussianNoise(root_seed, sigma_rel, sigma_add).draw(indices, latent)`
- Produces: evaluator `state_dict()` / `load_state_dict()` support where available.
- Consumes: existing `TorchEvaluator`, `BiphasicOracle`, and `Campaign` APIs.

- [ ] **Step 1: Write failing labelled-seed tests**

```python
def test_seed_labels_are_stable_independent_and_order_free():
    a = derive_seed(7, "opening", "family", 3)
    assert a == derive_seed(7, "opening", "family", 3)
    assert a != derive_seed(7, "noise", "family", 3)
    assert derive_seed(7, "noise", "family", 3) == derive_seed(7, "noise", "family", 3)

def test_indexed_noise_does_not_depend_on_chunking():
    source = IndexedGaussianNoise(11, sigma_rel=.1, sigma_add=.01)
    f = torch.tensor([[.2], [.5], [.9]], dtype=torch.double)
    together = source.observe(torch.arange(3), f)
    split = tuple(torch.cat([source.observe(torch.arange(2), f[:2])[i],
                             source.observe(torch.arange(2, 3), f[2:])[i]])
                  for i in range(2))
    assert all(torch.equal(a, b) for a, b in zip(together, split))
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_seedbook.py -q`  
Expected: import failure because `boec.seedbook` does not exist.

- [ ] **Step 3: Implement stateless seed and noise primitives**

```python
def derive_seed(root_seed: int, label: str, *parts: object) -> int:
    payload = json.dumps([int(root_seed), label, *parts], sort_keys=True,
                         separators=(",", ":"), default=str).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**63 - 1)

@dataclass(frozen=True)
class IndexedGaussianNoise:
    root_seed: int
    sigma_rel: float
    sigma_add: float

    def observe(self, indices: Tensor, latent: Tensor) -> tuple[Tensor, Tensor]:
        # One generator per labelled index makes chunking and resume irrelevant.
        eps, eta = [], []
        for index in indices.reshape(-1).tolist():
            g_rel = torch.Generator().manual_seed(derive_seed(self.root_seed, "rel", index))
            g_add = torch.Generator().manual_seed(derive_seed(self.root_seed, "add", index))
            eps.append(torch.randn((), generator=g_rel, dtype=torch.double))
            eta.append(torch.randn((), generator=g_add, dtype=torch.double))
        eps_t = torch.stack(eps).reshape_as(latent) * self.sigma_rel
        eta_t = torch.stack(eta).reshape_as(latent) * self.sigma_add
        y = latent * (1 + eps_t) + eta_t
        return y, torch.full_like(y, float("nan"))
```

The `nan` variance is deliberate: current SPADE fits learned noise and must not consume a
truth-derived or noisy-response-derived fixed variance.

- [ ] **Step 4: Add opt-in indexed evaluation and checkpoint state**

Add `noise_source: IndexedGaussianNoise | None = None` and `_next_index` to the torch
evaluators. Preserve legacy behavior when `noise_source is None`. When present, evaluate
with indices `[_next_index, ..., _next_index+n-1]`, advance once, and expose:

```python
def state_dict(self) -> dict[str, int]:
    return {"next_index": self._next_index}

def load_state_dict(self, state: dict[str, int]) -> None:
    self._next_index = int(state["next_index"])
```

`Campaign.state_dict()` stores optional evaluator state and `load_state_dict()` restores
it before any further evaluation. Reject a saved evaluator state when the current
evaluator does not implement restoration.

- [ ] **Step 5: Prove interrupted and uninterrupted indexed-noise campaigns match**

Add a real resume test that runs an opening and one adaptive batch, saves, rebuilds with a
fresh evaluator, resumes, and compares `train_X`, `train_Y`, logs, evaluator index, and
serialized state byte-for-byte.

- [ ] **Step 6: Diagnose historical failures without weakening them silently**

`scripts/audit_historical_replay.py` emits a committed-schema audit row for every failing
historical gate with observed delta, environment, source hash, and one of:
`REPRODUCIBLE_EXACT`, `REPRODUCIBLE_REGISTERED_TOLERANCE`, or
`HISTORICAL_NONREGENERABLE`. Exact gates may move to an explicit registered tolerance only
when the audit proves the scientific decision and selected point are unchanged. Material
qLogEI/qLogNEI trajectory mismatches are classified non-regenerable, not rounded away.

- [ ] **Step 7: Run Task 1 tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_seedbook.py tests/test_torch_oracle.py \
  tests/test_campaign.py tests/test_historical_replay_audit.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add .gitignore src/boec/seedbook.py src/boec/torch_oracle.py src/boec/campaign.py \
  scripts/audit_historical_replay.py tests/test_seedbook.py tests/test_torch_oracle.py \
  tests/test_campaign.py tests/test_historical_replay_audit.py
git commit -m "fix: make campaign randomness resumable and auditable"
```

---

### Task 2: Common learned-noise GP and deterministic acquisition engines

**Files:**
- Modify: `src/boec/surrogate.py`
- Modify: `src/boec/optimizers.py`
- Create: `src/boec/variance_reduction.py`
- Modify: `tests/test_surrogate.py`
- Modify: `tests/test_optimizers.py`
- Create: `tests/test_variance_reduction.py`

**Interfaces:**
- Produces: `build_learned_noise_gp(train_X, train_Y, bounds, *, fit_restarts, seed)`
- Produces: `AcqConfig.sampler_seed`
- Produces: `greedy_ivr(model, candidates, reference, q, *, weights=None)`

- [ ] **Step 1: Write failing learned-noise and seeded-qLogNEI tests**

```python
def test_learned_noise_gp_does_not_accept_fixed_yvar():
    model = build_learned_noise_gp(X, Y, bounds, fit_restarts=2, seed=3)
    assert model.likelihood.noise.detach().item() > 0

def test_qlognei_sampler_seed_reproduces_discrete_batch():
    cfg = AcqConfig(kind="qlognei", mc_samples=64, sampler_seed=19)
    assert torch.equal(propose(model, bounds, 4, X, Y, config=cfg, candidates=menu),
                       propose(model, bounds, 4, X, Y, config=cfg, candidates=menu))
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_surrogate.py tests/test_optimizers.py -q`  
Expected: missing builder and `sampler_seed` failures.

- [ ] **Step 3: Implement the learned-noise GP**

Reuse the existing covariance/input/outcome transform construction, but instantiate
`SingleTaskGP(train_X, train_Y, train_Yvar=None, ...)`. Use four deterministic restart
seeds derived through `seedbook`; keep the best exact marginal likelihood. Constrain raw
likelihood noise to a positive finite interval and record restart diagnostics on the
returned model as `_boec_fit_diagnostics`.

- [ ] **Step 4: Seed qLogNEI QMC explicitly**

Extend `AcqConfig` with `sampler_seed: int = 0` and construct:

```python
sampler = SobolQMCNormalSampler(
    sample_shape=torch.Size([cfg.mc_samples]), seed=cfg.sampler_seed)
```

Keep legacy default behavior reproducible by an explicit zero rather than ambient global
RNG. Add tests for different seeds and no duplicate discrete choices.

- [ ] **Step 5: Write failing IVR tests**

```python
def test_global_ivr_selects_the_point_with_greatest_reference_reduction(): ...
def test_boundary_weights_change_the_selected_point(): ...
def test_ivr_batch_is_unique_and_deterministic(): ...
def test_zero_or_nonfinite_weights_refuse(): ...
```

- [ ] **Step 6: Implement greedy IVR**

For each greedy member, compute posterior cross-covariance between reference points and
remaining candidates. Score candidate `j` by

\[
\sum_r w_r Cov(f_r,f_j)^2/(Var(f_j)+sigma_n^2).
\]

After selection, condition the reference/candidate covariance through a rank-one Schur
update before selecting the next batch member. Use latent covariance and learned
likelihood noise. Normalize weights to mean one; reject negative, all-zero, or nonfinite
weights. Break exact ties by candidate row index.

- [ ] **Step 7: Run Task 2 tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_surrogate.py tests/test_optimizers.py \
  tests/test_variance_reduction.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/boec/surrogate.py src/boec/optimizers.py src/boec/variance_reduction.py \
  tests/test_surrogate.py tests/test_optimizers.py tests/test_variance_reduction.py
git commit -m "feat: add deterministic learned-noise and variance-reduction acquisitions"
```

---

### Task 3: Gamma-aware predictive reliable regions and positive-evidence inference

**Files:**
- Create: `src/boec/reliable_region.py`
- Create: `tests/test_reliable_region.py`
- Modify: `src/boec/vorobev.py`
- Modify: `tests/test_vorobev.py`

**Interfaces:**
- Produces: `true_reliability_probability(f, tau, sigma_rel, sigma_add)`
- Produces: `model_reliability_probability(model, X, tau)`
- Produces: `reliable_set_draws(model, X, tau, gamma, n_draws, seed)`
- Produces: `conservative_set_split(set_draws, alpha, n_rho=64)`
- Produces: `empirical_set_containment(mask, truth_mask)`
- Produces: `clopper_pearson_lower(successes, total, confidence=.95)`

- [ ] **Step 1: Write gamma and empirical-containment regression tests**

```python
def test_gamma_changes_the_reliable_set_draws():
    low = reliable_set_draws(model, grid, tau=.5, gamma=.5, n_draws=128, seed=1)
    high = reliable_set_draws(model, grid, tau=.5, gamma=.95, n_draws=128, seed=1)
    assert not torch.equal(low, high)
    assert high.sum() <= low.sum()

def test_empty_certificate_is_not_a_containment_success():
    assert empirical_set_containment(torch.zeros(4, dtype=torch.bool),
                                     torch.ones(4, dtype=torch.bool)) is None
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_reliable_region.py -q`  
Expected: module import failure.

- [ ] **Step 3: Implement true and model reliability maps**

Use `torch.distributions.Normal(0,1).cdf`. Oracle truth uses
`sqrt(sigma_rel**2*f**2 + sigma_add**2)`. Model probability uses latent posterior mean
and variance plus learned likelihood noise; document that this is the common
homoskedastic model approximation.

- [ ] **Step 4: Implement set-valued posterior draws**

Draw latent samples jointly, compute each draw's future-observation exceedance
probability using learned likelihood noise, and threshold at `gamma`. Return boolean shape
`(n_draws, n_grid)`. Reject odd counts for split certification, invalid probabilities,
and nonpositive model noise.

- [ ] **Step 5: Generalize split conservative estimation to boolean set draws**

`conservative_set_split` computes pointwise inclusion probabilities from the first half,
scans 64 quantiles for the largest non-empty set whose joint first-half containment is at
least `alpha`, and scores that frozen set on the second half. Return a frozen dataclass
containing mask, cross-fit containment or `None`, selection containment, volume, and
draw counts.

- [ ] **Step 6: Implement exact confidence lower bound and PASS semantics**

```python
def clopper_pearson_lower(successes: int, total: int,
                          confidence: float = .95) -> float | None:
    if total == 0:
        return None
    if successes == 0:
        return 0.0
    return float(beta.ppf(1 - confidence, successes, total - successes + 1))
```

Tests must prove `43/50` cannot pass a 0.90 lower-bound criterion and that an empty
denominator returns `None`, never PASS.

- [ ] **Step 7: Run Task 3 tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_reliable_region.py tests/test_vorobev.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/boec/reliable_region.py src/boec/vorobev.py \
  tests/test_reliable_region.py tests/test_vorobev.py
git commit -m "fix: make SPADE certificates predictive and empirically testable"
```

---

### Task 4: Current 48-evaluation SPADE and common comparators

**Files:**
- Create: `src/boec/spade.py`
- Create: `tests/test_spade.py`
- Modify: `src/boec/__init__.py` only if package metadata requires it; do not re-export.

**Interfaces:**
- Produces: `SpadeConfig`, `SpadeCampaignResult`, `run_spade`, `run_sobol48`,
  `run_qlognei48`
- Consumes: `build_learned_noise_gp`, seeded qLogNEI, `greedy_ivr`, labelled seeds.

- [ ] **Step 1: Write configuration and budget refusal tests**

```python
@pytest.mark.parametrize("opening,rounds", [(32, 5), (40, 3), (44, 2)])
def test_spade_uses_exactly_48_evaluations(opening, rounds):
    result = run_spade(evaluator, bounds, SpadeConfig(opening=opening,
                       policy="fixed_hybrid", root_seed=7), fast=True)
    assert result.X.shape == (48, 6)
    assert result.rounds == rounds

@pytest.mark.parametrize("bad", [31, 33, 41, 45, 48])
def test_unregistered_openings_refuse(bad): ...
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_spade.py -q`  
Expected: module import failure.

- [ ] **Step 3: Implement frozen dataclasses and protocol digest**

`SpadeConfig` validates total budget 48, batch size 4, openings `{32,40,44}`, policies
`{staged,fixed_hybrid,validity_gated}`, all deterministic grid/menu sizes, and seed. Its
canonical sorted JSON representation produces a SHA-256 protocol digest.

- [ ] **Step 4: Implement objective-specific batch dispatch**

`staged` returns qLogNEI for every adaptive batch. `fixed_hybrid` alternates qLogNEI and
global IVR. `validity_gated` alternates qLogNEI with map batches; map batches compute
`w=p*(1-p)`, effective sample size `(sum(w)**2 / sum(w**2))`, and use boundary IVR only
when a non-empty `p>=gamma` region and ESS >=32 exist. Otherwise use global IVR. Record
objective and pre-outcome diagnostics in every round log.

- [ ] **Step 5: Implement all three arm runners through common internals**

The common internals own evaluator calls, learned-GP fitting, adaptive menu removal,
terminal model fitting, and raw records. `run_sobol48` evaluates one complete scrambled
Sobol design. `run_qlognei48` uses opening 14 followed by eight q=4 batches and q=2. No
arm-specific scoring is allowed in this module.

- [ ] **Step 6: Add no-truth leak tests**

Use an evaluator whose `truth` method raises if called. All three campaign runners must
finish. A second test supplies an evaluator with only `evaluate` and proves the public
decision signature has no oracle parameter.

- [ ] **Step 7: Run Task 4 tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_spade.py tests/test_seedbook.py \
  tests/test_variance_reduction.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/boec/spade.py tests/test_spade.py
git commit -m "feat: implement the unified 48-evaluation SPADE protocol"
```

---

### Task 5: Untouched randomized generators, thresholds, and common scoring

**Files:**
- Create: `src/boec/lockbox_oracles.py`
- Create: `src/boec/spade_study.py`
- Create: `tests/test_lockbox_oracles.py`
- Create: `tests/test_spade_study.py`
- Create: `configs/experiment/spade-joint.yaml`
- Create: `results/spade-lockbox-generator-manifest.json`

**Interfaces:**
- Produces: `LOCKBOX_FAMILIES`, `make_lockbox_oracle(family, instance_seed)`
- Produces: `controlled_tau`, `score_campaign`, deterministic JSONL/shard APIs.

- [ ] **Step 1: Write generator invariant tests**

For every family and several seeds, assert d=6, finite values in [0,1], deterministic
parameters, distinct instances, an interior optimum, optimum value 1 within `1e-6`, and
non-identical map topology. Assert the manifest names exactly four families and contains
no existing development-family name.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_lockbox_oracles.py -q`  
Expected: module import failure.

- [ ] **Step 3: Implement the four generators**

Use seed-derived shifts in `[.2,.8]^6`, orthogonal matrices from seeded QR with fixed sign
normalization, and bounded shape parameters. Implement:

- toroidal shifted/rotated Rastrigin transformed to [0,1];
- log-sum-exp anisotropic Gaussian mixtures with deterministic multistart optimum audit;
- an exponential curved-ridge penalty with unique optimum at its shift; and
- a normalized radial logistic soft plateau with unique center maximum.

Store every sampled parameter and optimum-audit result in an immutable instance record.

- [ ] **Step 4: Write threshold and common-score failing tests**

```python
def test_controlled_tau_makes_quarter_grid_reliable(): ...
def test_scorer_uses_identical_paths_for_all_arms(): ...
def test_rule_p_is_selected_before_truth_is_called(): ...
def test_map_loss_matches_independent_squared_error_reference(): ...
```

- [ ] **Step 5: Implement controlled threshold and scoring**

`controlled_tau` evaluates only inside a sealed harness on the 65,536 calibration grid.
`score_campaign` receives an already-run arm result, numeric tau, and scorer-only oracle;
fits/snapshots the final common model, locates Rule P on the 16,384 terminal grid, computes
map loss on the 8,192 map grid, constructs the certificate on the 2,048 certificate grid,
and evaluates empirical containment. Ensure truth is called only after the terminal point
and certificate mask are frozen.

- [ ] **Step 6: Implement deterministic gzip JSONL and provenance**

Write gzip with fixed `mtime=0`, sorted compact JSON keys, one row per line, atomic rename,
and SHA-256 sidecar. Rows include all Global Constraints provenance. Read refuses duplicate
campaign keys or schema/protocol drift.

- [ ] **Step 7: Freeze protocol and generator manifest**

The YAML contains every numeric design value from the spec. The manifest contains family
definitions, parameter ranges, instance key range `0..349`, source/spec/config digests,
and status `FROZEN_UNOPENED`; it contains no outcome metrics.

- [ ] **Step 8: Run Task 5 tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_lockbox_oracles.py tests/test_spade_study.py -q
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add src/boec/lockbox_oracles.py src/boec/spade_study.py \
  tests/test_lockbox_oracles.py tests/test_spade_study.py \
  configs/experiment/spade-joint.yaml results/spade-lockbox-generator-manifest.json
git commit -m "feat: freeze SPADE scoring and untouched lockbox generators"
```

---

### Task 6: Development runner and immutable protocol selection

**Files:**
- Create: `scripts/run_spade_development.py`
- Create: `scripts/select_spade_protocol.py`
- Create: `tests/test_spade_development.py`
- Modify: `.gitignore` to allowlist the small development analysis and selection artifacts.

**Interfaces:**
- Produces: development shards, `spade-development-analysis.json`,
  `spade-selected-protocol.json` or `NO_SELECTION`.

- [ ] **Step 1: Write failing grid/completeness tests**

Assert exactly five development families, 50 matched campaigns, nine SPADE candidates,
two controls, 48 evaluations, and common campaign keys. Reject a tenth candidate, an
unknown opening, absent arm rows, or a family presented as held out.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_spade_development.py -q`  
Expected: scripts or exported helpers absent.

- [ ] **Step 3: Implement resumable development shards**

The runner accepts explicit family, start/stop key range, and output path. Smoke/limited
runs can write only under caller-provided scratch paths and carry status `SMOKE`; they
cannot write registered result paths. Complete rows use the common scorer and deterministic
gzip writer.

- [ ] **Step 4: Implement nested-family selection**

Compute per-candidate family-fold answer rate, empirical containment, paired regret
difference, and map loss. Apply the four-step lexicographic rule verbatim. Emit every
candidate's failure reason and the complete tie-break trace. Synthetic fixtures must prove
each gate and `NO_SELECTION` independently.

- [ ] **Step 5: Guard the selected-protocol artifact**

Selection refuses a dirty tree, incomplete development manifest, wrong protocol digest,
or unhashed raw file. Output includes source commit, spec/config/generator digests,
development hashes, selected canonical config, and status `SELECTED` or `NO_SELECTION`.

- [ ] **Step 6: Run Task 6 tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_spade_development.py \
  tests/test_spade_study.py tests/test_spade.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add .gitignore scripts/run_spade_development.py scripts/select_spade_protocol.py \
  tests/test_spade_development.py
git commit -m "feat: add prespecified SPADE development selection"
```

---

### Task 7: Guarded lockbox execution, confirmatory analysis, and release validation

**Files:**
- Create: `scripts/run_spade_lockbox.py`
- Create: `scripts/analyse_spade_lockbox.py`
- Create: `scripts/validate_spade_lockbox_release.py`
- Create: `tests/test_spade_lockbox.py`
- Create: `tests/test_spade_release.py`
- Modify: `.gitignore` to allowlist final manifest, analysis, release report, and compressed
  raw shards.

**Interfaces:**
- Produces: lockbox shards, manifest, confirmatory analysis, release report.

- [ ] **Step 1: Write lockbox access-control tests**

Refuse when selected protocol is absent, `NO_SELECTION`, dirty, uncommitted, digest-mismatched,
or older than the generator freeze commit. Refuse `--limit` at a registered output path.
Prove the runner never imports development result metrics into campaign decisions.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_spade_lockbox.py -q`  
Expected: missing script/helpers.

- [ ] **Step 3: Implement paired resumable lockbox shards**

For each family and instance key, create one oracle and matched indexed-noise/candidate
seed books for SPADE, Sobol48, and qLogNEI48. Run all arms through common scoring. A shard
is complete only when every requested key has all three arms. Promotion is atomic.

- [ ] **Step 4: Write confirmatory-statistics tests**

Use independent fixture calculations to test one-sided paired-bootstrap upper bounds and
Clopper-Pearson lower bounds. Prove `43/50` cannot pass containment, zero non-empty
certificates cannot pass, pooled-family success cannot rescue a failed family, and
superiority language requires an upper bound below zero.

- [ ] **Step 5: Implement the intersection-union analysis**

Analyze every family separately. Emit effect, one-sided bound, denominator, margin,
PASS/FAIL, and reason for all four endpoints. Overall PASS is `all(endpoint PASS for every
family)`. Secondary analyses are clearly marked and never alter the primary verdict.

- [ ] **Step 6: Write release-corruption tests**

Fixtures must trigger every registered violation: missing/duplicate key, wrong budget,
mixed terminal rule, dirty SHA, wrong environment, parent-hash mismatch, wrong protocol,
premature lockbox, invalid certificate denominator, absent raw shard, unregistered sample
size, and unsupported prose claim.

- [ ] **Step 7: Implement the fail-closed release validator**

Collect every violation before exiting. On clean artifacts, write a release JSON with
checks, hashes, row counts, final verdict, and exact permissible claim text. The validator
does not recompute campaigns and does not trust manifest self-report without hashing files.

- [ ] **Step 8: Run Task 7 tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_spade_lockbox.py tests/test_spade_release.py \
  tests/test_reliable_region.py tests/test_spade_study.py -q
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add .gitignore scripts/run_spade_lockbox.py scripts/analyse_spade_lockbox.py \
  scripts/validate_spade_lockbox_release.py tests/test_spade_lockbox.py \
  tests/test_spade_release.py
git commit -m "feat: add powered SPADE lockbox and release gate"
```

---

### Task 8: Execute development, freeze SPADE, and run the one-shot lockbox

**Files:**
- Generate: `results/spade-development.json.gz`
- Generate: `results/spade-development-analysis.json`
- Generate: `results/spade-selected-protocol.json`
- Generate: `results/spade-lockbox-*.jsonl.gz`
- Generate: `results/spade-lockbox-manifest.json`
- Generate: `results/spade-lockbox-analysis.json`
- Generate: `results/spade-lockbox-release.json`
- Update: `.planning/STATE.md`

**Interfaces:**
- Consumes all prior tasks.
- Produces the immutable evidence needed to decide whether the paper can claim combined
  specialist-level performance.

- [ ] **Step 1: Run all development shards**

Use explicit single-thread environment settings and a deterministic shard matrix. After
each shard, run its integrity check and hash it. Do not inspect lockbox outputs.

- [ ] **Step 2: Merge and select**

Run the development analyzer and selection script. If status is `NO_SELECTION`, stop the
lockbox and report the registered negative result. If selected, verify every selection
trace field and commit the selected protocol before proceeding.

- [ ] **Step 3: Run pre-lockbox power calculation**

Use development paired differences to simulate registered map/regret power. Set final
`n` to `max(350, n_map, n_regret)` and commit that immutable sample-size decision before
opening lockbox outcomes.

- [ ] **Step 4: Run all lockbox shards exactly once**

Run each family/instance range, verify shard completeness and hashes, merge only after all
expected keys exist, and retain raw compressed rows.

- [ ] **Step 5: Analyze and validate**

Run `analyse_spade_lockbox.py` and `validate_spade_lockbox_release.py`. Preserve stdout,
commands, environment, and exit codes in the release artifact.

- [ ] **Step 6: Commit immutable evidence**

```bash
git add results/spade-development.json.gz results/spade-development-analysis.json \
  results/spade-selected-protocol.json results/spade-lockbox-*.jsonl.gz \
  results/spade-lockbox-manifest.json results/spade-lockbox-analysis.json \
  results/spade-lockbox-release.json .planning/STATE.md
git commit -m "results: freeze SPADE development and lockbox evidence"
```

---

### Task 9: Full verification, independent review, and paper-evidence handoff

**Files:**
- Update: `docs/METHODS.md`
- Update: `docs/RESEARCH-SUMMARY.md`
- Update: `.planning/REQUIREMENTS.md`
- Update: `.planning/STATE.md`
- Generate/update: `results/full-test-suite.log`

**Interfaces:**
- Consumes final code and immutable evidence.
- Produces bounded paper-ready method/evidence prose, not a manuscript.

- [ ] **Step 1: Update methods from implementation, not aspiration**

Document the selected opening/policy, 48-evaluation schedule, learned-noise GP, candidate
pool, Rule P, threshold construction, probability-map metric, certificate construction,
lockbox families, pairing, sample size, and inference exactly as recorded in artifacts.

- [ ] **Step 2: Update the research summary from release evidence**

State each primary endpoint with point estimate, bound, denominator, family, and verdict.
If the conjunction fails, lead with failure and preserve the registered stopping rule. Do
not use wet-lab/manufacturing language.

- [ ] **Step 3: Run focused and non-slow suites**

```bash
.venv/bin/python -m pytest tests/test_seedbook.py tests/test_surrogate.py \
  tests/test_variance_reduction.py tests/test_reliable_region.py tests/test_spade.py \
  tests/test_lockbox_oracles.py tests/test_spade_study.py \
  tests/test_spade_development.py tests/test_spade_lockbox.py \
  tests/test_spade_release.py -q
.venv/bin/python -m pytest -m "not slow" -q
```

Expected: zero failures.

- [ ] **Step 4: Run complete suite and release gates**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_spade_lockbox_release.py
```

Expected: zero unexplained failures and release exit zero. Any strict historical xfail
must have a committed audit classification and must not cover new SPADE code.

- [ ] **Step 5: Perform requirements audit and independent whole-branch review**

Check every requirement in `.planning/REQUIREMENTS.md` against code, test, and artifact
evidence. Dispatch the whole branch for correctness, statistical validity,
reproducibility, simplification, and claim-boundary review; fix every Critical or
Important finding and re-run its covering tests.

- [ ] **Step 6: Commit verified paper support**

```bash
git add docs/METHODS.md docs/RESEARCH-SUMMARY.md .planning/REQUIREMENTS.md \
  .planning/STATE.md results/full-test-suite.log
git commit -m "docs: freeze verified SPADE evidence for paper drafting"
```

## Self-review

- Spec coverage: Tasks 1-9 cover every method, certificate, development, lockbox,
  provenance, test, and paper-boundary requirement in the design.
- Placeholder scan: every implementation and error path is assigned concretely.
  Outcome-dependent values are produced only by registered execution tasks.
- Type consistency: module names and public signatures are introduced once and consumed by
  later tasks under the same names.
- Scope: historical code remains for replay; all new outcome-bearing work uses the current
  `boec.spade` path and one public method identity.
