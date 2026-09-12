# Joseph Push Refresh Integration Implementation Plan

> **For Codex:** Execute this plan one task at a time. Stop before any confirmatory experiment is launched; the corrected protocol must be frozen and reviewed first.

**Goal:** Integrate the strongest parts of Joseph's latest push at exact commit `9d88dc454e85396db64d531a4b044a9ca1ddca18`, preserve its useful code and raw evidence, and correct the statistical and provenance defects that currently make several manuscript claims unsafe.

**Architecture:** Build from a clean worktree at Joseph's exact head, replay the two local publication commits, and make all corrections on that clean integration branch. Treat Joseph's TT and DC result files as immutable historical evidence. Add a deterministic TT activation audit, carry observation variances through the DoE API, freeze a fresh-seed DC correction protocol, and narrow the paper's claims to what the registered intervals actually establish.

**Tech Stack:** Python 3, PyTorch, BoTorch/GPyTorch, pytest, JSON evidence artifacts, Git worktrees.

---

## Decision and evidence snapshot

This plan supersedes the earlier merge recommendation because `origin/main` advanced from `5983bad` to `9d88dc4` through nine Joseph commits. The new work adds completed TT and DC experiments, result propagation, and a manuscript scoreboard.

The best integration strategy remains a clean latest-head base plus replay of the local publication commits:

| Strategy | Scientific traceability | Conflict risk | Preserves Joseph's full chain | Decision |
|---|---:|---:|---:|---|
| Selectively port individual Joseph commits into the current checkout | Low | High | No | Reject |
| Merge `origin/main` directly into the 48-path dirty checkout | Medium | High | Yes | Reject operationally |
| Start from exact `9d88dc4`, replay `0b99806` and `783612f`, then correct claims | High | Low | Yes | Adopt |

The adopted sequence has already been mechanically rehearsed in a disposable clone. Both publication commits cherry-picked without conflicts, and the focused integration suite passed `178` tests with `2` warnings.

### Facts that constrain the merge

- Joseph's earlier head `b93061b` is an ancestor of the new head, so the latest branch is the complete source of his work.
- The current checkout is `2` commits ahead and `127` commits behind `origin/main`, with `3` modified and `45` untracked paths. Those user changes must not be used as the merge surface.
- Preserve the registered `NO_SELECTION` conclusion already present in Joseph's history.
- Preserve the two local publication commits in order: `0b998063622c69136d6a30253850e67161f524d8`, then `783612fbaeca2f223391678984d203a20485f906`.
- TT's configured `spade_tau` arm is not adoptable, but the experiment did not test a fully activated target-aware acquisition: only `206/640` adaptive rounds were target-active, and only `20/160` campaigns were active in all four adaptive rounds.
- TT's aggregate certified-volume estimate is `+0.000425`, with CI `[-0.000022, +0.000875]`; this is inconclusive for a consistent positive benefit.
- TT's regret estimate is `+0.0301`, with CI `[+0.0169, +0.0450]`; its registered noninferiority guard fails. The lower endpoint remains below the `0.02` practical margin, so the evidence does not establish that the harm exceeds that margin.
- The two smallest TT family p-values become `0.06` after Holm correction; family estimates must therefore remain descriptive.
- DC's DoE arms were certified with a constant variance reconstructed from the mean absolute response. The registered oracle instead supplies per-well plug-in variance, `y_i^2 sigma_rel^2 + sigma_add^2`. The published DC numerical claims are not confirmatory evidence until corrected.
- In a five-seed diagnostic comparison across all five families, the constant-variance path answered `18` cases with `12` contained, while the per-well path answered `8` with `2` contained. This pilot is diagnostic only and must not be promoted as the corrected result.
- DC's analyser was added after partial result files existed, so the claim that the adjudicator was written before data landed is not supported by the Git history.
- `scripts/verify_conclusions.py` still verifies the older LC result, not the new TT/DC values or the new scoreboard language.

## Non-negotiable integration rules

1. Do not merge into, reset, clean, or otherwise rewrite the current dirty checkout.
2. Do not alter the numerical contents of the ten raw `results/tt-*.json` and `results/dc-*.json` files.
3. Do not describe absence of a detectable difference as equivalence, a tie, or a match.
4. Do not describe TT as a clean failure of a fully activated mechanism.
5. Do not use the original DC seeds `0..31` for a new confirmatory correction after examining their outcomes.
6. Do not run the corrected DC experiment during this merge. Freeze, test, review, and commit the protocol first.
7. Do not claim that every paper number is machine-checked until the verifier actually covers the current TT/DC/scoreboard claims.

---

### Task 1: Create and validate the clean integration candidate

**Files:**

- Preserve: every current user-modified and untracked path in the existing checkout
- Validate: `docs/SPADE-CONCLUSIONS-2026-08-29.md`
- Validate: `.planning/STATE.md`
- Validate: `.planning/ROADMAP.md`

**Step 1: Refresh and pin the source commit**

Run:

```bash
git fetch origin
test "$(git rev-parse origin/main)" = "9d88dc454e85396db64d531a4b044a9ca1ddca18"
git merge-base --is-ancestor b93061b origin/main
```

Expected: both assertions exit `0`. If `origin/main` has advanced again, stop and repeat the evidence audit before changing the pinned SHA.

**Step 2: Create a separate worktree and branch**

Run from the repository root:

```bash
git worktree add ../nutrigene-ai-bo-ipsec-joseph-refresh -b codex/spade-joseph-push-refresh 9d88dc454e85396db64d531a4b044a9ca1ddca18
cd ../nutrigene-ai-bo-ipsec-joseph-refresh
```

Expected: the new worktree is clean and points exactly at Joseph's latest audited head.

**Step 3: Replay the local publication commits**

Run:

```bash
git cherry-pick 0b998063622c69136d6a30253850e67161f524d8
git cherry-pick 783612fbaeca2f223391678984d203a20485f906
git status --short
```

Expected: both cherry-picks complete without conflicts and `git status --short` is empty.

**Step 4: Establish the focused baseline**

Run:

```bash
pytest -q \
  tests/test_publication_tables.py \
  tests/test_doe.py \
  tests/test_doe_unscreened.py \
  tests/test_doe_repeat.py \
  tests/test_reliable_region.py \
  tests/test_vorobev.py \
  tests/test_multiround.py \
  tests/test_multiround_adaptive_theta.py \
  tests/test_certificate_straddle.py \
  tests/test_sur.py
```

Expected: `178 passed`, with the same two known warnings or fewer.

**Step 5: Confirm the protected conclusion survived**

Run:

```bash
rg -n "NO_SELECTION" .planning docs
```

Expected: the registered no-selection outcome remains present. If it disappeared, stop rather than reconstructing it from memory.

**Step 6: Commit only if Git created integration changes**

Cherry-picks create their own commits. Do not add a synthetic merge commit at this stage.

---

### Task 2: Make TT activation observable and narrow its conclusion

**Files:**

- Modify: `src/boec/certstraddle.py`
- Create: `scripts/audit_tt_activation.py`
- Create: `tests/test_tt_activation_audit.py`
- Create: `results/tt-activation-audit.json`
- Modify: `docs/SPADE-THETA-TAU-SPEC.md`
- Modify: `docs/SPADE-PAPER-ARGUMENT.md`
- Modify: `docs/SPADE-CONCLUSIONS-2026-08-29.md`

**Step 1: Write failing unit tests for the target-activation predicate**

Add tests covering all three cases for the adjusted margin `mean - z_rho * sd`:

```python
def test_target_is_active_only_inside_adjusted_margin_range():
    adjusted = torch.tensor([-0.4, 0.1, 0.7])
    assert contour_target_is_active(adjusted, theta=0.0)
    assert not contour_target_is_active(adjusted, theta=-0.4)
    assert not contour_target_is_active(adjusted, theta=0.7)
```

Also test that the production acquisition path calls the same predicate used by the audit. Do not maintain a second, audit-only definition of activation.

Run:

```bash
pytest -q tests/test_certificate_straddle.py tests/test_tt_activation_audit.py
```

Expected: the new tests fail because the shared predicate and audit do not yet exist.

**Step 2: Extract the production predicate**

In `src/boec/certstraddle.py`, add a pure helper with an explicit boundary contract:

```python
def contour_target_is_active(adjusted_margin: torch.Tensor, theta: float) -> bool:
    lo = float(adjusted_margin.min())
    hi = float(adjusted_margin.max())
    return lo < float(theta) < hi
```

Refactor the acquisition implementation to call this helper without changing its numerical behavior.

Run the tests again. Expected: the predicate tests pass.

**Step 3: Build a deterministic audit over the registered TT campaigns**

Create `scripts/audit_tt_activation.py` to:

- reconstruct the five registered families, seeds `0..31`, and four adaptive rounds;
- use the exact TT `theta=tau` and `rho=0.95` configuration;
- record activation for every `(family, seed, round)`;
- fail if any expected cell is missing or duplicated;
- emit `source_commit`, `source_dirty`, the TT spec SHA-256, and the script SHA-256;
- write atomically via a temporary file followed by rename;
- print and store per-family/per-round totals and overall totals.

The output schema must include:

```json
{
  "status": "COMPLETE",
  "source_commit": "9d88dc454e85396db64d531a4b044a9ca1ddca18",
  "families": ["ackley", "hartmann6", "hill", "levy", "rosenbrock"],
  "seed_start": 0,
  "seed_stop": 32,
  "adaptive_rounds": 4,
  "active_rounds": 206,
  "total_rounds": 640,
  "campaigns_active_all_rounds": 20,
  "total_campaigns": 160
}
```

The script must derive the numerical totals; the test may assert them as a regression check against the independently reproduced audit.

Run:

```bash
python scripts/audit_tt_activation.py --out results/tt-activation-audit.json
pytest -q tests/test_tt_activation_audit.py
```

Expected totals:

| Family | Active by adaptive round | Active in all four rounds |
|---|---|---:|
| ackley | `2, 20, 29, 30` | 2 |
| hartmann6 | `19, 30, 32, 32` | 18 |
| hill | `0, 0, 4, 3` | 0 |
| levy | `0, 1, 1, 2` | 0 |
| rosenbrock | `0, 0, 1, 0` | 0 |

**Step 4: Correct TT multiplicity and language**

Update the TT analyser or verifier to report Holm-adjusted p-values for the five family tests. The two smallest raw p-values, `0.012` and `0.015`, must both report as `0.06`; no family-level result is confirmatory at familywise alpha `0.05`.

Replace broad claims with this bounded conclusion:

> The configured `spade_tau` arm is not adopted. Its aggregate certified-volume estimate was +0.000425 with CI [-0.000022, +0.000875], while regret noninferiority failed. The target-aware acquisition was active in only 206 of 640 adaptive rounds, so this is not a clean test of a fully activated mechanism.

Keep family estimates as descriptive heterogeneity. Remove language that says `KF-3` was vindicated, that target awareness was fully repaired, or that harm was wholly beyond the `0.02` practical margin.

**Step 5: Verify and commit TT corrections**

Run:

```bash
pytest -q tests/test_certificate_straddle.py tests/test_tt_activation_audit.py
python scripts/audit_tt_activation.py --out results/tt-activation-audit.json
python scripts/analyse_tt_theta_tau.py
git diff --check
git status --short
```

Expected: tests pass, the audit reproduces `206/640` and `20/160`, and the analyser does not label any family result confirmatory after Holm correction.

Commit:

```bash
git add src/boec/certstraddle.py scripts/audit_tt_activation.py tests/test_tt_activation_audit.py results/tt-activation-audit.json docs/SPADE-THETA-TAU-SPEC.md docs/SPADE-PAPER-ARGUMENT.md docs/SPADE-CONCLUSIONS-2026-08-29.md
git commit -m "fix: bound theta tau conclusions by activation evidence"
```

---

### Task 3: Preserve per-well DoE observation variance

**Files:**

- Modify: `src/boec/doe.py`
- Modify: `scripts/run_dc_doe_certificate.py`
- Modify: `tests/test_doe.py`
- Modify: `tests/test_doe_unscreened.py`
- Create: `tests/test_dc_doe_certificate.py`

**Step 1: Write failing API tests**

Extend the DoE tests so a deterministic evaluator returns distinct variances for distinct wells. Assert:

```python
assert result.Yvar_visited.shape == result.Y_visited.shape
assert torch.equal(result.Yvar_visited, expected_variances)
assert torch.unique(result.Yvar_visited).numel() > 1
```

Cover both `run_doe_arm` and `run_doe_unscreened_arm`, including the final confirmation well.

Add a DC runner test that stubs a DoE result and asserts `build()` returns its exact `Yvar_visited`, not a reconstructed constant.

Run:

```bash
pytest -q tests/test_doe.py tests/test_doe_unscreened.py tests/test_dc_doe_certificate.py
```

Expected: failures because `DoEResult` has no `Yvar_visited` field and the DC runner synthesizes a constant.

**Step 2: Carry variance through the screened arm**

Add `Yvar_visited: Tensor` to `DoEResult` and document it as `(budget, 1)` per-well observation variances returned by the evaluator.

In `run_doe_arm`, retain the second return value from every evaluator call:

```python
Y1, Yvar1 = evaluator.evaluate(X1)
Y2, Yvar2 = evaluator.evaluate(X2)
Yc, Yvarc = evaluator.evaluate(x_full.unsqueeze(0))
Yvar_visited = torch.cat((Yvar1, Yvar2, Yvarc), dim=0)
```

Use the actual local variable names in the function, and preserve the existing order of `X_visited` and `Y_visited` exactly.

**Step 3: Carry variance through the unscreened arm**

Retain `Yvar_design` and `Yvarc`, concatenate them in measurement order, and return the result through the same dataclass field.

Do not recompute variance from `Y_visited`: the evaluator is the source of truth and may include additive noise or a future non-plug-in model.

**Step 4: Remove the DC constant-variance reconstruction**

In `scripts/run_dc_doe_certificate.py::build`, replace the `torch.full_like` reconstruction with:

```python
X, Y, Yvar = res.X_visited, res.Y_visited, res.Yvar_visited
```

Do not call the private replay helper as a substitute. Direct variance plumbing is both more general and auditable.

**Step 5: Verify and commit the variance fix**

Run:

```bash
pytest -q tests/test_doe.py tests/test_doe_unscreened.py tests/test_doe_repeat.py tests/test_dc_doe_certificate.py
git diff --check
```

Expected: all tests pass and the DC test proves the returned variance vector is nonconstant when the evaluator supplies nonconstant variances.

Commit:

```bash
git add src/boec/doe.py scripts/run_dc_doe_certificate.py tests/test_doe.py tests/test_doe_unscreened.py tests/test_dc_doe_certificate.py
git commit -m "fix: preserve per-well variance in DoE certification"
```

---

### Task 4: Quarantine historical DC evidence and freeze a valid correction

**Files:**

- Move: `results/dc-ackley.json` to `results/historical-dc-constant-yvar/dc-ackley.json`
- Move: `results/dc-hartmann6.json` to `results/historical-dc-constant-yvar/dc-hartmann6.json`
- Move: `results/dc-hill.json` to `results/historical-dc-constant-yvar/dc-hill.json`
- Move: `results/dc-levy.json` to `results/historical-dc-constant-yvar/dc-levy.json`
- Move: `results/dc-rosenbrock.json` to `results/historical-dc-constant-yvar/dc-rosenbrock.json`
- Create: `results/historical-dc-constant-yvar/README.md`
- Create: `docs/SPADE-DOE-CERTIFICATE-CORRECTION-SPEC.md`
- Create: `scripts/run_dc2_doe_certificate.py`
- Create: `scripts/analyse_dc2_doe_certificate.py`
- Create: `tests/test_dc2_protocol.py`
- Modify: `docs/SPADE-DOE-CERTIFICATE-SPEC.md`
- Modify: `scripts/analyse_dc_doe_certificate.py`

**Step 1: Preserve the old files byte-for-byte**

Record hashes, move with Git, and verify the hashes after the move:

```bash
shasum -a 256 results/dc-*.json
mkdir -p results/historical-dc-constant-yvar
git mv results/dc-ackley.json results/historical-dc-constant-yvar/dc-ackley.json
git mv results/dc-hartmann6.json results/historical-dc-constant-yvar/dc-hartmann6.json
git mv results/dc-hill.json results/historical-dc-constant-yvar/dc-hill.json
git mv results/dc-levy.json results/historical-dc-constant-yvar/dc-levy.json
git mv results/dc-rosenbrock.json results/historical-dc-constant-yvar/dc-rosenbrock.json
shasum -a 256 results/historical-dc-constant-yvar/dc-*.json
```

Expected: corresponding before/after hashes are identical.

In the historical README, state exactly:

- these are Joseph's original DC outputs;
- the DoE certification path used constant reconstructed `Yvar` instead of per-well evaluator variance;
- the files are retained for auditability, not confirmatory inference;
- no numerical value in the files was edited;
- Git history shows the analyser was committed after partial results existed.

**Step 2: Mark the original DC specification and analyser historical**

Add a prominent scientific caveat to `docs/SPADE-DOE-CERTIFICATE-SPEC.md`. Make `scripts/analyse_dc_doe_certificate.py` require an explicit historical directory or `--historical` flag so it cannot accidentally consume future corrected outputs.

Do not erase its original calculations; preserve reproducibility of the historical result.

**Step 3: Write the correction protocol before generating outcomes**

The new frozen spec must define:

- purpose: repeat DC with exact per-well evaluator variance;
- fresh confirmatory seeds `32..63` for each registered family;
- arms: `doe`, `doe_unscreened`, and `spade`;
- `48` wells per campaign and the existing registered SPADE round count;
- the same registered `p`, inflation, alpha, subset, and containment definitions unless the spec explicitly motivates a change before data;
- primary estimand and one acceptance rule stated before execution;
- family estimates as descriptive unless a correction procedure is registered;
- failure policy: any campaign error makes the artifact incomplete and the analyser must refuse adjudication;
- exact completeness grid and expected row count;
- provenance fields and digest algorithm;
- no use of seeds `0..31` for confirmatory interpretation.

The fresh-seed choice is mandatory because outcomes from `0..31`, including a five-seed corrected diagnostic, have already been inspected.

**Step 4: Test protocol integrity before implementing the runner**

Write tests that require:

```python
assert protocol.seed_start == 32
assert protocol.seed_stop == 64
assert set(protocol.arms) == {"doe", "doe_unscreened", "spade"}
assert protocol.expected_jobs == 5 * 32
```

Also require that:

- every expected `(family, seed, arm, p_value, inflation_c)` cell occurs exactly once;
- a partial artifact is rejected;
- a duplicate row is rejected;
- a provenance digest mismatch is rejected;
- resume skips a job only when every expected row for that job is present;
- writer exceptions propagate and leave no file marked `COMPLETE`.

Run:

```bash
pytest -q tests/test_dc2_protocol.py
```

Expected: tests fail before the DC2 runner and analyser exist.

**Step 5: Implement an auditable runner**

Create `scripts/run_dc2_doe_certificate.py` with explicit `--seed-start` and `--seed-stop` arguments whose defaults are `32` and `64`.

The top-level artifact must include:

```json
{
  "status": "PARTIAL",
  "source_commit": "git SHA captured at runtime",
  "source_dirty": false,
  "seed_start": 32,
  "seed_stop": 64,
  "spec_sha256": "computed digest",
  "runner_sha256": "computed digest",
  "rows": []
}
```

Implementation requirements:

- use `res.Yvar_visited` for both DoE arms;
- write atomically after each complete job;
- represent job completion explicitly rather than inferring it from one row;
- reject resume when source/spec/runner provenance is incompatible;
- never swallow an exception and continue to a final `COMPLETE` artifact;
- mark `COMPLETE` only after exact-grid validation passes.

**Step 6: Implement a fail-closed analyser**

Create `scripts/analyse_dc2_doe_certificate.py` so it validates status, provenance, exact dimensions, unique cells, finite values, and expected row counts before computing any inferential statistic.

The analyser must print `REFUSED` and return nonzero for an incomplete or inconsistent artifact. It must not silently overwrite duplicate dictionary keys.

Run:

```bash
pytest -q tests/test_dc2_protocol.py
git diff --check
```

Expected: all protocol tests pass.

**Step 7: Freeze without running the experiment**

Run only deterministic smoke tests using tiny fixtures or mocked evaluators. Do not invoke the real five-family, 32-seed campaign.

Commit:

```bash
git add results/historical-dc-constant-yvar docs/SPADE-DOE-CERTIFICATE-SPEC.md docs/SPADE-DOE-CERTIFICATE-CORRECTION-SPEC.md scripts/analyse_dc_doe_certificate.py scripts/run_dc2_doe_certificate.py scripts/analyse_dc2_doe_certificate.py tests/test_dc2_protocol.py
git commit -m "test: freeze variance-corrected DC protocol"
```

Create a separate reviewed execution decision after this commit. The protocol commit SHA and clean status must become part of the future result provenance.

---

### Task 5: Make manuscript claims and the verifier agree with the evidence

**Files:**

- Modify: `docs/SPADE-PAPER-ARGUMENT.md`
- Modify: `docs/SPADE-CONCLUSIONS-2026-08-29.md`
- Modify: `scripts/verify_conclusions.py`
- Create: `tests/test_conclusion_language.py`
- Modify: `tests/test_publication_tables.py`

**Step 1: Add failing semantic claim tests**

Add tests that load the two claim documents and enforce:

```python
assert "ties BO" not in paper
assert "matches BO" not in paper
assert "only method that returns an operating region you can trust" not in paper
assert "no detectable regret difference" in paper
assert "variance-corrected replication" in paper
```

Use case-insensitive regular expressions to cover minor capitalization differences. Also test that the current DC numerical result is labelled historical rather than confirmatory.

Run:

```bash
pytest -q tests/test_conclusion_language.py
```

Expected: failures on the current scoreboard language.

**Step 2: Correct equivalence and uniqueness claims**

Change the DC comparison language as follows:

- CI `[-0.0221, +0.0207]` is **no detectable regret difference**, not equivalence, because it extends beyond both sides of the registered `±0.02` margin.
- State observed certification counts: SPADE `66/66` contained and qLogNEI `58/59` contained among answered cases.
- State that both pass the registered containment gate; do not call SPADE the only trustworthy method.
- State observed answer counts without a superiority claim. The exploratory Fisher tests do not establish a difference in containment or answer rate.
- Keep SPADE's five-round versus qLogNEI's ten-round comparison as a factual computational-budget distinction, not proof of universal dominance.
- Label the current DoE containment result historical and awaiting variance-corrected replication.

**Step 3: Upgrade the verifier from stale numbers to current claims**

Refactor `scripts/verify_conclusions.py` so it is root-relative and fail-closed. It must verify at least:

- TT raw artifacts form the exact expected family/seed/arm/`p`/`c` grid;
- TT aggregate volume CI and regret noninferiority values match the analyser;
- Holm-adjusted family p-values match the stated descriptive status;
- `results/tt-activation-audit.json` is complete and reports `206/640` and `20/160`;
- historical DC artifacts reproduce their stated old values but are labelled non-confirmatory;
- no current DC2 conclusion is emitted without a complete, provenance-valid DC2 artifact;
- the paper contains the bounded terminology enforced by `tests/test_conclusion_language.py`.

Retain the existing LC checks, but rename output labels so LC values cannot be mistaken for DC values.

**Step 4: Verify all claim surfaces**

Run:

```bash
pytest -q tests/test_conclusion_language.py tests/test_publication_tables.py
python scripts/verify_conclusions.py
python scripts/analyse_tt_theta_tau.py
python scripts/analyse_dc_doe_certificate.py --historical results/historical-dc-constant-yvar
git diff --check
```

Expected: all commands exit `0`; the verifier identifies DC as historical, TT as not adopted and mixed-activation, and the BO comparison as no detectable difference rather than equivalence.

**Step 5: Commit the claim correction**

Run:

```bash
git add docs/SPADE-PAPER-ARGUMENT.md docs/SPADE-CONCLUSIONS-2026-08-29.md scripts/verify_conclusions.py tests/test_conclusion_language.py tests/test_publication_tables.py
git commit -m "docs: align SPADE claims with registered evidence"
```

---

### Task 6: Run final integration gates and prepare review

**Files:**

- Review: every file changed by Tasks 2 through 5
- Preserve: the original dirty checkout and all of its user-owned changes

**Step 1: Re-run the focused scientific suite**

Run:

```bash
pytest -q \
  tests/test_publication_tables.py \
  tests/test_doe.py \
  tests/test_doe_unscreened.py \
  tests/test_doe_repeat.py \
  tests/test_reliable_region.py \
  tests/test_vorobev.py \
  tests/test_multiround.py \
  tests/test_multiround_adaptive_theta.py \
  tests/test_certificate_straddle.py \
  tests/test_sur.py \
  tests/test_tt_activation_audit.py \
  tests/test_dc_doe_certificate.py \
  tests/test_dc2_protocol.py \
  tests/test_conclusion_language.py
```

Expected: all tests pass. Compare any warnings with the established baseline rather than silently accepting new ones.

**Step 2: Run the full suite and compare with baseline**

Run:

```bash
pytest -q
```

Expected: no new failure relative to the repository's previously observed full-suite baseline. The earlier checkout had eight unrelated full-suite failures; record exact before/after node IDs in the review if they still exist. Do not call the branch verified merely because the failure count is unchanged if any touched test fails.

**Step 3: Verify repository and evidence integrity**

Run:

```bash
python scripts/verify_conclusions.py
git diff --check 9d88dc454e85396db64d531a4b044a9ca1ddca18..HEAD
git status --short
git log --oneline --decorate 9d88dc454e85396db64d531a4b044a9ca1ddca18..HEAD
rg -n "NO_SELECTION" .planning docs
```

Expected:

- verifier exits `0`;
- no whitespace errors;
- the integration worktree is clean after commits;
- the two publication commits and correction commits are visible;
- the no-selection conclusion is intact;
- no real DC2 result file exists because the confirmatory rerun was deliberately not launched.

**Step 4: Review the branch before any merge**

The review must explicitly answer:

1. Does any document still equate a CI crossing the SESOI margins with equivalence?
2. Can any incomplete or duplicate result grid reach a `COMPLETE` or adjudicated state?
3. Does every DoE certification observation use the evaluator-returned per-well variance?
4. Is TT described as mixed-activation and non-adopted, without claiming a clean mechanism failure?
5. Are the old DC files still byte-identical and clearly quarantined?
6. Did any step alter the original dirty checkout?

Only after those answers are satisfactory should the clean branch be proposed for merge.

---

## Why this is the least-biased merge strategy

This plan separates three questions that the current branch blends together:

1. **Is Joseph's code and evidence worth preserving?** Yes. The commit chain is coherent, mechanically integrates, and contains valuable experiments and manuscript work.
2. **Are all current interpretations supported?** No. TT is a mixed-activation experiment, DC used the wrong observation-variance representation for the DoE arms, and several paper phrases claim equivalence or uniqueness that the registered comparisons do not establish.
3. **Should the work be discarded?** No. Preserve the raw evidence, correct the reusable code, downgrade invalid claims, and freeze a prospective correction using unseen seeds.

The statistical basis is conventional and source-backed:

- ICH E9 describes equivalence as requiring the entire confidence interval to lie within the equivalence margins: https://www.fda.gov/media/71336/download
- Holm's sequentially rejective procedure controls familywise error across multiple hypotheses: https://doi.org/10.2307/4615733
- Conservative excursion-set work treats set containment as a joint-set property, supporting the repository's containment-first certification framing: https://arxiv.org/abs/1611.07256

## Definition of done

The integration is ready for merge review when:

- the branch is based on exact Joseph head `9d88dc4` and contains both local publication commits;
- the focused suite has no regressions and the full-suite comparison has no new touched-code failures;
- TT activation is machine-audited and the paper uses the bounded non-adoption conclusion;
- DoE retains exact per-well evaluator variances end to end;
- old DC outputs are immutable, reproducible, and explicitly historical;
- a fresh-seed DC correction protocol is frozen and tested but not yet run;
- the verifier checks current numerical and semantic claims rather than only the stale LC result;
- the original dirty checkout remains untouched;
- `NO_SELECTION` remains preserved.
