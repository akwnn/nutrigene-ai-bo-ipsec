# SPADE EC-Differentiation Success Redefinition and Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a scientifically defensible, EC-differentiation-oriented success definition for SPADE, improve answer-rate/containment performance against that definition, and produce an auditable conclusion without rewriting the failed preregistered gate.

**Architecture:** Keep the original registered ≥50% answer-rate and ≥90% containment gate immutable as the confirmatory benchmark. Add a clearly labeled prospective EC benchmark with six-factor, multi-CQA synthetic landscapes representing identity, viability, and yield, then improve SPADE through calibration, abstention control, and boundary-aware acquisition. Every decision is made on training seeds; final claims use untouched evaluation seeds and a fail-closed report.

**Tech Stack:** Python 3, PyTorch, BoTorch/GPyTorch, NumPy/SciPy, pytest, JSON/JSONL artifacts, deterministic seeded simulations, Git provenance.

## Global Constraints

- Never relabel the existing `NO_SELECTION` result as a success.
- Never change the original preregistered thresholds, seeds, raw result files, or lockbox artifacts.
- The new EC benchmark is prospective and must use untouched seeds for final evaluation.
- No wet-lab data may be implied; all landscapes are explicitly synthetic proxies.
- A certificate is valid only when all CQAs satisfy their thresholds jointly.
- Abstention is allowed, but a method cannot pass with fewer than 16 answered campaigns per family.
- Report answer rate, containment, false-certificate rate, regret, and adaptive rounds separately.
- Any incomplete, duplicated, non-finite, or provenance-mismatched artifact is refused.
- Do not claim superiority from a confidence interval that includes both practical margins.

## Why this is the best same-day strategy

This plan is the shortest defensible path to a strong conclusion because it aligns the
estimand, the algorithm, and the evidence boundary instead of trying to rescue a failed
single-response gate after the fact.

- **The deliverable is multi-objective.** Current cell-culture optimization literature uses
  iterative Bayesian optimization for interacting media factors and multiple biological
  outcomes, including viability and phenotype, rather than treating one scalar optimum as
  the whole deliverable ([Cosenza et al., 2022](https://pmc.ncbi.nlm.nih.gov/articles/9541924/);
  [Harini et al., 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12218302/)). The plan therefore
  certifies identity, viability, and yield jointly.
- **The comparison must be budget-matched and uncertainty-aware.** These studies support
  adaptive BO as a practical alternative to large DoE campaigns, but they do not establish
  universal superiority. The plan tests matched wells, rounds, regret, and region recovery
  on unseen seeds instead of importing a headline from a different budget or objective.
- **The success claim must be prospective.** ICH E9 requires the estimand and analysis to be
  specified before interpretation, and equivalence requires the complete confidence interval
  to lie inside pre-specified margins ([ICH E9](https://www.ema.europa.eu/en/documents/scientific-guideline/ich-e-9-statistical-principles-clinical-trials-step-5_en.pdf);
  [ICH E9(R1)](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)).
  The plan consequently preserves the old `NO_SELECTION` result and freezes a new EC
  criterion before evaluating seeds 64–95.
- **Containment and abstention are separate outcomes.** A method that certifies one safe
  recipe can appear perfect while answering almost nothing. The minimum answered-campaign
  rule and per-family lower bounds prevent vacuous containment from being reported as
  success.

This is a better route than changing the threshold until the existing data pass: it can
produce a strong positive result if SPADE genuinely works, and a precise failure diagnosis
if it does not, while remaining publishable either way.

---

## Success contract

The original gate remains the confirmatory historical criterion:

> SPADE must achieve answer rate ≥0.50 and containment ≥0.90 on both registered families under the existing protocol.

The new EC-differentiation criterion is a separate prospective claim:

> On unseen six-factor EC-differentiation proxy landscapes, SPADE must achieve (a) answer rate ≥0.50 in every required family, with at least 16 answered campaigns per family; (b) lower one-sided 95% containment bound ≥0.90 in every required family; (c) zero false certificates in the evaluated campaigns; (d) point regret no worse than matched-budget DOE by more than 0.02; and (e) no more adaptive rounds than matched-budget DOE.

Passing containment only among one or two answered campaigns is explicitly insufficient. If the new criterion fails, the conclusion must say so and identify whether abstention, model misspecification, or acquisition placement is the limiting failure mode.

---

### Task 1: Freeze the EC benchmark and claim boundary

**Files:**
- Create: `docs/SPADE-EC-SUCCESS-SPEC.md`
- Create: `src/boec/ec_benchmark.py`
- Create: `tests/test_ec_benchmark.py`
- Modify: `.planning/STATE.md`

**Interfaces:**
- `ec_benchmark.py::ECBenchmarkConfig` stores factors, CQA thresholds, seed ranges, budgets, and acceptance margins.
- `ec_benchmark.py::make_ec_landscape(family: str, seed: int) -> ECLandscape` returns six-factor truth and noisy evaluator.
- `ec_benchmark.py::joint_success(y: Tensor, thresholds: Tensor) -> Tensor` returns a per-row Boolean requiring every CQA threshold.

- [ ] **Step 1: Write failing configuration tests.**

```python
def test_ec_config_is_six_factor_and_fresh_seeded():
    cfg = ECBenchmarkConfig()
    assert cfg.n_factors == 6
    assert cfg.eval_seed_start == 64
    assert cfg.eval_seed_stop == 96
    assert cfg.min_answered_per_family == 16
```

- [ ] **Step 2: Implement immutable benchmark configuration.**

Use a frozen dataclass with explicit CQA names (`identity`, `viability`, `yield`) and thresholds. Keep training seeds `0..63` separate from evaluation seeds `64..95`.

- [ ] **Step 3: Implement joint CQA truth and evaluator.**

Each landscape must return a `(n, 3)` CQA matrix and a `(n, 3)` variance matrix. `joint_success` must be equivalent to `(y >= thresholds).all(dim=-1)` and must reject wrong dimensionality.

- [ ] **Step 4: Add provenance and specification text.**

Record the spec SHA-256 and source commit in every generated artifact. State that the landscapes are computational proxies, not biological measurements.

- [ ] **Step 5: Run and commit.**

Run `pytest -q tests/test_ec_benchmark.py`; expect all configuration, shape, threshold, and seed-separation tests to pass. Commit with `feat: freeze EC differentiation success benchmark`.

---

### Task 2: Add multi-CQA SPADE certification

**Files:**
- Create: `src/boec/multicqa.py`
- Create: `tests/test_multicqa.py`
- Modify: `src/boec/reliable_region.py`

**Interfaces:**
- `multicqa.py::joint_lower_bound(mean, covariance, alpha) -> Tensor` computes simultaneous lower bounds for all CQAs.
- `multicqa.py::certificate_from_draws(draws, thresholds, alpha) -> Certificate` returns containment, volume, abstention reason, and limiting CQA.

- [ ] **Step 1: Write failing joint-certificate tests.**

Test that a recipe failing any one CQA is excluded, that the limiting CQA is reported deterministically, and that an empty joint region returns `abstention_reason="no_joint_region"` with volume zero.

- [ ] **Step 2: Implement conservative joint certification.**

Use a simultaneous alpha allocation across CQA dimensions. Do not multiply marginal probabilities and call the result joint coverage. Require all lower bounds to clear all thresholds.

- [ ] **Step 3: Integrate with the existing region object.**

Preserve single-response behavior. Add optional CQA fields rather than changing existing serialized fields in-place, so old evidence remains readable.

- [ ] **Step 4: Test limiting-attribute diagnostics.**

For every non-empty certificate, store the CQA with the smallest normalized margin. For an empty certificate, store the CQA that blocks the largest candidate volume.

- [ ] **Step 5: Run and commit.**

Run `pytest -q tests/test_multicqa.py tests/test_reliable_region.py`; commit with `feat: add conservative joint CQA certificates`.

---

### Task 3: Improve answer rate without weakening containment

**Files:**
- Create: `src/boec/answer_control.py`
- Create: `tests/test_answer_control.py`
- Modify: `src/boec/selfcalib.py`
- Modify: `src/boec/certstraddle.py`

**Interfaces:**
- `answer_control.py::calibrate_inflation(y, covariance, target_answer_rate, seed) -> InflationPolicy`.
- `answer_control.py::apply_policy(certificate, policy) -> Certificate`.

- [ ] **Step 1: Write failing calibration tests.**

Require calibration to use only training seeds, to be deterministic for a fixed seed, and to never reduce a lower bound or enlarge a certificate beyond the uninflated certificate.

- [ ] **Step 2: Implement split-conformal inflation.**

Estimate a residual quantile on held-out training campaigns, enforce a minimum inflation of `1.0`, and cap the target answer rate at a registered value. Do not tune on evaluation seeds.

- [ ] **Step 3: Add an explicit abstention policy.**

Return structured reasons: `no_joint_region`, `nonfinite_posterior`, `insufficient_calibration`, or `provenance_mismatch`. Never convert abstention into a positive certificate.

- [ ] **Step 4: Instrument activation and limiting CQA.**

Record whether the boundary acquisition was active, the selected target, and the limiting CQA for every adaptive round.

- [ ] **Step 5: Run and commit.**

Run `pytest -q tests/test_answer_control.py tests/test_conformal_lower_bound.py tests/test_certificate_straddle.py`; commit with `fix: calibrate EC answer control conservatively`.

---

### Task 4: Build the matched-budget EC experiment

**Files:**
- Create: `scripts/run_ec_benchmark.py`
- Create: `scripts/analyse_ec_benchmark.py`
- Create: `tests/test_ec_runner.py`

**Interfaces:**
- Runner defaults: training seeds `0..63`, evaluation seeds `64..95`, 48 wells, SPADE five rounds, DOE three rounds.
- Arms: `spade`, `doe`, `doe_unscreened`, and `qlognei`.
- `analyse_ec_benchmark.py::validate_artifact(path) -> None` must fail closed.

- [ ] **Step 1: Write artifact-integrity tests.**

Test rejection of partial grids, duplicate `(family, seed, arm)` cells, missing CQA columns, non-finite values, wrong source/spec digest, and evaluation seeds overlapping training seeds.

- [ ] **Step 2: Implement atomic, resumable execution.**

Write after each complete job. A job is complete only when all arms, CQA metrics, and provenance fields exist. Resume may skip only complete jobs with matching provenance.

- [ ] **Step 3: Implement matched-budget scoring.**

For each arm report answer rate, empirical containment, Wilson lower bound, false-certificate count, joint volume, point regret, and adaptive rounds. Use the same candidate grid and truth for all arms.

- [ ] **Step 4: Add a dry-run mode.**

The dry run must execute one family and one seed with mocked evaluators and must never write a `COMPLETE` artifact unless exact-grid validation passes.

- [ ] **Step 5: Run and commit.**

Run `pytest -q tests/test_ec_runner.py`; run only the dry run; commit with `feat: add fail-closed EC benchmark runner`.

---

### Task 5: Execute a calibration-development sweep, then freeze evaluation

**Files:**
- Create: `results/ec-development/`
- Create: `docs/SPADE-EC-CALIBRATION-REPORT.md`
- Modify: `scripts/analyse_ec_benchmark.py`

- [ ] **Step 1: Run training-only calibration sweep.**

Use seeds `0..63` only. Compare inflation policies, candidate-grid sizes, and activation settings. Select one policy using a predeclared lexicographic rule: first containment lower bound, then answer rate, then regret, then rounds.

- [ ] **Step 2: Freeze policy and hash it.**

Write the selected policy, its parameters, training seed range, code digest, and selection table. After this commit, no evaluation result may influence policy parameters.

- [ ] **Step 3: Review the frozen policy.**

Run the runner’s dry mode and verify that policy provenance is embedded in every row. Commit with `chore: freeze EC calibration policy`.

---

### Task 6: Run unseen-seed evaluation and adjudicate success

**Files:**
- Create: `results/ec-evaluation.json`
- Create: `results/ec-evaluation.manifest.json`
- Create: `docs/SPADE-EC-EVALUATION-REPORT.md`
- Modify: `scripts/verify_conclusions.py`
- Create: `tests/test_ec_conclusions.py`

- [ ] **Step 1: Run the frozen evaluation.**

Use only seeds `64..95`; do not inspect individual outcomes to alter the policy. Preserve raw rows and write atomically.

- [ ] **Step 2: Apply the acceptance rule.**

Require every required family to have at least 16 answered campaigns, answer rate ≥0.50, and one-sided 95% containment lower bound ≥0.90. Also require zero false certificates, regret noninferiority within 0.02, and no more rounds than DOE.

- [ ] **Step 3: Produce a fail-closed adjudication.**

The report must emit exactly one of `PASS_EC_PROSPECTIVE`, `FAIL_ANSWER_RATE`, `FAIL_CONTAINMENT`, `FAIL_FALSE_CERTIFICATE`, `FAIL_REGRET`, `FAIL_ROUNDS`, or `REFUSED_INCOMPLETE`.

- [ ] **Step 4: Update paper language.**

If pass: state that SPADE met the prospective EC proxy criterion, while keeping the original registered `NO_SELECTION` result separate. If fail: state the limiting failure and do not claim DOE replacement.

- [ ] **Step 5: Add semantic claim tests and commit.**

Tests must reject “universally superior,” “equivalent,” “only trustworthy method,” and any claim that synthetic EC proxies are biological validation. Commit with `docs: adjudicate prospective EC benchmark`.

---

### Task 7: Final verification and merge review

**Files:**
- Review all files changed by Tasks 1–6.
- Preserve all original raw evidence and the dirty checkout.

- [ ] **Step 1: Run focused validation.**

```bash
pytest -q \
  tests/test_ec_benchmark.py tests/test_multicqa.py tests/test_answer_control.py \
  tests/test_ec_runner.py tests/test_ec_conclusions.py tests/test_doe.py \
  tests/test_doe_unscreened.py tests/test_certificate_straddle.py
```

- [ ] **Step 2: Run the conclusion verifier.**

```bash
python scripts/verify_conclusions.py
```

Expected: the verifier passes existing historical claims and reports the EC adjudication without conflating it with the original gate.

- [ ] **Step 3: Check provenance and raw-file integrity.**

Verify SHA-256 hashes of all original TT/DC files against the pre-plan manifest, confirm evaluation seeds are `64..95`, and confirm no DC2 or EC result is marked complete without exact-grid validation.

- [ ] **Step 4: Run the full suite with baseline comparison.**

Run `pytest -q`. Record all failures by node ID and distinguish pre-existing infrastructure/reproducibility failures from touched-code failures. A full-suite failure in touched code blocks merge.

- [ ] **Step 5: Final review questions.**

1. Did the new criterion improve the scientific question without rewriting the old result?
2. Is joint CQA containment actually simultaneous rather than marginal?
3. Are answer-rate gains obtained without weakening certificates?
4. Were evaluation seeds untouched during calibration?
5. Can incomplete or duplicated artifacts be adjudicated as success?
6. Are all EC claims explicitly limited to synthetic proxies?

Only if every answer is satisfactory should the isolated branch be proposed for merge. Do not merge into the existing dirty checkout automatically.

## Definition of Done

- Original preregistered results and `NO_SELECTION` remain unchanged.
- The EC success definition is written, versioned, and machine-checked.
- SPADE supports joint identity/viability/yield certification with limiting-CQA diagnostics.
- Calibration can improve answer rate without weakening containment guarantees.
- The evaluation runner is resumable, provenance-bound, and fail-closed.
- Final unseen-seed adjudication is either a genuine `PASS_EC_PROSPECTIVE` or an explicit failure code.
- The paper states exactly what passed and what did not; it never converts abstention into success.
- The original dirty checkout is untouched until a separate, reviewed merge decision.
