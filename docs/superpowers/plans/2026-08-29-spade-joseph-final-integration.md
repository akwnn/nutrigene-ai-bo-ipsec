# SPADE Joseph Final Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Selectively integrate Joseph's final SPADE research sequence through `b5a5bfe` into the manufacturing `main` line, preserve the registered B5 evidence, and replace stale claims with conclusions supported by the frozen adjudication rules.

**Architecture:** Keep `origin/kr-effective-resolution` as a read-only research reference and port only named files or hunks into a fresh worktree based on local `main`. Treat LC, TAU, and ACK as separate evidence packages with their own tests and commits; do not let research-only changes mutate the registered manufacturing digest. Reconcile documentation only after the imported analysers reproduce the committed result files.

**Tech Stack:** Python 3, PyTorch, SciPy, pytest, Git worktrees, JSON result artifacts, Markdown specifications.

## Global Constraints

- Source remote is exactly `origin/kr-effective-resolution` at `b5a5bfeb8aa7dbc101bb22162a1c2439dec8c19e`.
- Manufacturing baseline is local `main` at or after `2682d13a54d657df199f6341340951441f25c4d4`.
- Do not work in the dirty `codex/publication-readiness` checkout.
- Do not wholesale-merge or rebase `origin/kr-effective-resolution`; it deletes manufacturing runners and evidence allowlists.
- Do not alter, relabel, or resume registered B5 digest `404b4884260b756a9b4777178ffae8350f6c9d0da0da6e912e3e06432090dbd4`.
- Do not replace the manufacturing `.gitignore`; add only the five TAU result allowlists. LC allowlists already exist.
- Primary manufacturing evidence and Joseph's round-budget evidence remain separate estimands.
- Read certificate truth from `ce_empirical_*`, never the circular `ce_contain_*` fields.
- Every certification statement must carry `sigma_rel = 0.25`; the measured real-noise ceiling remains `sigma_rel = 0.68`, where no arm certified.
- Every Hill certification statement must carry prevalence `p = 0.70`.
- Under the frozen LC-1 rule, CI `[−0.0184, +0.0208]` is **INCONCLUSIVE** because it crosses the `+0.0200` SESOI edge. The later half-width reinterpretation is exploratory and must not replace the registered verdict.
- Never claim “SPADE certifies at five rounds; qLogNEI needs ten.” LC disproved it.
- Do not activate adaptive `theta` in the registered product. ACK showed that `theta` cancels from the acquisition ranking in the measured regime; `rho` is the live lever.

---

## File Map

### Research evidence packages

- Modify `scripts/run_lc_confirmatory.py` — add deterministic checkpoint resume support.
- Create `scripts/analyse_lc_confirmatory.py` — frozen LC adjudicator.
- Create `scripts/analyse_lb_monotonicity.py` — post-hoc LB round-shape analysis.
- Create `docs/SPADE-LC-CONFIRMATORY-SPEC.md` — LC registration, results, and limitations.
- Create `results/lc-{ackley,hartmann6,hill,levy,rosenbrock}.json` — committed 32-seed LC evidence.
- Create `scripts/run_tau_sweep.py` — resumable prevalence sweep.
- Create `scripts/analyse_tau_sweep.py` — TAU-1/2/3 adjudicator.
- Create `docs/SPADE-TAU-DEGENERACY-SPEC.md` — frozen TAU registration and 64-seed result.
- Create `results/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json` — committed 64-seed TAU evidence.
- Create `docs/SPADE-ACKLEY-THETA-SPEC.md` — ACK hypothesis and explicit retraction.
- Create `scripts/run_ack_theta.py` — research-only ACK runner.
- Modify `src/boec/multiround.py` — add an explicit, backwards-compatible `resolve_theta` helper without changing registered callers.

### Integration tests

- Create `tests/test_lc_final_integration.py` — result balance, resume parsing, and frozen LC verdict.
- Create `tests/test_tau_final_integration.py` — 64-seed balance and Hill containment certificate.
- Create `tests/test_multiround_adaptive_theta.py` — explicit-threshold compatibility and adaptive-threshold behavior.
- Modify `tests/test_certificate_straddle.py` — prove the measured `theta` cancellation regime.

### Claim and state reconciliation

- Modify `docs/SPADE-ROUND-SWEEP-SPEC.md` — retain historical LB text but mark the five-vs-ten claim withdrawn.
- Modify `docs/HANDOFF-2026-08-29.md` — replace obsolete headline and pending-LC status.
- Create `docs/SPADE-CONCLUSIONS-2026-08-29.md` — conservative integrated conclusions.
- Modify `docs/superpowers/specs/2026-08-28-spade-joseph-integration-manifest.md` — advance the source pin and port ledger.
- Modify `docs/superpowers/specs/2026-08-29-spade-unified-product-design.md` — correct the secondary claim without changing the primary manufacturing gate.
- Modify `.planning/STATE.md` — record research integration separately from B5 execution status.
- Modify `.planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md` — update the Joseph integration reference and note what remains research-only.
- Modify `.gitignore` — allow only the five named TAU JSON files.

---

### Task 1: Freeze the Integration Baseline in an Isolated Worktree

**Files:**
- Modify: `docs/superpowers/specs/2026-08-28-spade-joseph-integration-manifest.md`

**Interfaces:**
- Consumes: local `main`; fetched `origin/kr-effective-resolution`.
- Produces: branch `codex/spade-joseph-final-integration` and an auditable 15-commit source range.

- [ ] **Step 1: Fetch GitHub and assert the exact Joseph head**

Run:

```bash
git fetch origin --prune
test "$(git rev-parse origin/kr-effective-resolution)" = "b5a5bfeb8aa7dbc101bb22162a1c2439dec8c19e"
```

Expected: both commands exit `0`; the assertion prints nothing.

- [ ] **Step 2: Create a clean worktree from local manufacturing `main`**

Run:

```bash
git worktree add .worktrees/spade-joseph-final-integration -b codex/spade-joseph-final-integration main
git -C .worktrees/spade-joseph-final-integration status --short --branch
```

Expected:

```text
## codex/spade-joseph-final-integration
```

- [ ] **Step 3: Capture the missing range before changing files**

Run:

```bash
git -C .worktrees/spade-joseph-final-integration log --reverse --oneline 07ae40e..origin/kr-effective-resolution
git -C .worktrees/spade-joseph-final-integration cherry main origin/kr-effective-resolution 07ae40e
```

Expected: 15 commits, from `8c52197 LC: --resume...` through `b5a5bfe Conclusions...`; every `git cherry` line begins with `+`.

- [ ] **Step 4: Update the integration manifest source pin and safety boundary**

Replace the manifest header and prior “LC pending” paragraph with:

```markdown
**Joseph reference:** `origin/kr-effective-resolution` → `b5a5bfe`  
**Integrated source range:** `8c52197..b5a5bfe`, selectively ported after `07ae40e`  
**Remote:** `origin/kr-effective-resolution`  
**Manufacturing trunk:** `main` (REGISTERED gate pipeline)

Joseph's branch remains the read-only research reference. The final range is imported as
three evidence packages—LC, TAU, and ACK—without wholesale merging its tree or changing the
registered B5 digest.
```

Add this status table:

```markdown
| Package | Source commits | Integration rule |
|---|---|---|
| LC confirmatory | `8c52197`–`7d0e519` | Port runner, analyser, spec, and five 32-seed result files |
| TAU prevalence | `0c21304`–`0ff1e30` | Port runner, analyser, spec, and five 64-seed result files |
| ACK theta | `6947c81`–`0728d07` | Port research utility/tests and retraction; do not activate in registered product |
| Final conclusions | `b5a5bfe` | Reconcile against frozen LC verdict before publishing |
```

- [ ] **Step 5: Commit the pinned baseline**

Run:

```bash
git add docs/superpowers/specs/2026-08-28-spade-joseph-integration-manifest.md
git commit -m "docs(spade): pin Joseph final integration range"
```

Expected: one commit containing only the integration manifest.

---

### Task 2: Integrate LC Confirmation and LB Non-Monotonicity Evidence

**Files:**
- Modify: `scripts/run_lc_confirmatory.py`
- Create: `scripts/analyse_lc_confirmatory.py`
- Create: `scripts/analyse_lb_monotonicity.py`
- Create: `docs/SPADE-LC-CONFIRMATORY-SPEC.md`
- Create: `results/lc-ackley.json`
- Create: `results/lc-hartmann6.json`
- Create: `results/lc-hill.json`
- Create: `results/lc-levy.json`
- Create: `results/lc-rosenbrock.json`
- Create: `tests/test_lc_final_integration.py`

**Interfaces:**
- Consumes: `boec.multiround.multiround_design`, `boec.designspace.tau_quantile`, existing LA/LB result files.
- Produces: resumable LC execution; `load(paths, alpha)`, `verdict_lc1(lo, hi)`, and `regret_pair(...)` analysis interfaces; balanced 32-seed evidence.

- [ ] **Step 1: Write the failing LC integration tests**

Create `tests/test_lc_final_integration.py`:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_registered_lc1_rule_remains_inconclusive_at_32_seeds():
    lc = _script("analyse_lc_confirmatory")
    verdict = lc.verdict_lc1(-0.0184, 0.0208)
    assert verdict.startswith("INCONCLUSIVE")


def test_lc_results_are_balanced_over_32_seeds_and_five_families():
    lc = _script("analyse_lc_confirmatory")
    paths = sorted((ROOT / "results").glob("lc-*.json"))
    cells, regret = lc.load(paths, "0.95")
    assert {key[2] for key in cells} == {
        "ackley", "hartmann6", "hill", "levy", "rosenbrock"
    }
    assert {key[3] for key in cells} == set(range(32))
    delta, keys = lc.regret_pair(
        regret,
        ["ackley", "hartmann6", "hill", "levy", "rosenbrock"],
        "spade", 5, "qlognei", 10,
    )
    assert len(delta) == 160
    assert len(keys) == 160


def test_resume_reader_accepts_partial_dict_and_completed_list(tmp_path):
    runner = _script("run_lc_confirmatory")
    rows = [{"family": "hill", "seed": 0}, {"family": "ackley", "seed": 0}]
    partial = tmp_path / "partial.json"
    partial.write_text(__import__("json").dumps({"status": "PARTIAL", "rows": rows}))
    assert runner.load_resume_rows(partial) == rows
    complete = tmp_path / "complete.json"
    complete.write_text(__import__("json").dumps(rows))
    assert runner.load_resume_rows(complete) == rows
```

- [ ] **Step 2: Run the LC tests and confirm they fail before the port**

Run:

```bash
.venv/bin/python -m pytest tests/test_lc_final_integration.py -q
```

Expected: failures because the analyser and `load_resume_rows` do not yet exist and LC result files are absent.

- [ ] **Step 3: Port the LC analyser, monotonicity analyser, spec, and result files by path**

Run:

```bash
git checkout origin/kr-effective-resolution -- scripts/analyse_lc_confirmatory.py
git checkout origin/kr-effective-resolution -- scripts/analyse_lb_monotonicity.py
git checkout origin/kr-effective-resolution -- docs/SPADE-LC-CONFIRMATORY-SPEC.md
git checkout origin/kr-effective-resolution -- results/lc-ackley.json
git checkout origin/kr-effective-resolution -- results/lc-hartmann6.json
git checkout origin/kr-effective-resolution -- results/lc-hill.json
git checkout origin/kr-effective-resolution -- results/lc-levy.json
git checkout origin/kr-effective-resolution -- results/lc-rosenbrock.json
```

Expected: exactly nine new tracked files. Do not checkout Joseph's `.gitignore` or round-sweep spec in this step.

- [ ] **Step 4: Add testable resume parsing and wire it into the runner**

Add above `main()` in `scripts/run_lc_confirmatory.py`:

```python
def load_resume_rows(path: Path) -> list[dict]:
    """Read either a PARTIAL checkpoint object or a completed row list."""
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    return list(payload["rows"] if isinstance(payload, dict) else payload)
```

Add the argument:

```python
ap.add_argument(
    "--resume",
    action="store_true",
    help="Keep completed (family, seed) jobs already present in --out.",
)
```

Replace job initialization with:

```python
rows = load_resume_rows(a.out) if a.resume else []
have = {(str(r["family"]), int(r["seed"])) for r in rows}
jobs = [(f, s) for s in range(a.seeds) for f in fams if (f, s) not in have]
t0, done = time.time(), 0
```

- [ ] **Step 5: Preserve the frozen verdict and label the half-width interpretation exploratory**

In `docs/SPADE-LC-CONFIRMATORY-SPEC.md` §9.1, replace the 32-seed “parity” verdict with:

```markdown
The estimate tightened to +0.0016 with CI [−0.0184, +0.0208]. Its half-width, 0.0196,
is smaller than the SESOI, but the frozen LC-1 rule requires the entire CI to lie inside
[−0.0200, +0.0200]. The upper edge exceeds that interval by 0.0008. The registered verdict
therefore remains **INCONCLUSIVE**. The half-width observation is exploratory precision
evidence and does not amend the frozen gate.
```

- [ ] **Step 6: Run LC tests and adjudicators**

Run:

```bash
.venv/bin/python -m pytest tests/test_lc_final_integration.py tests/test_multiround.py -q
.venv/bin/python scripts/analyse_lc_confirmatory.py
.venv/bin/python scripts/analyse_lb_monotonicity.py
```

Expected:

- pytest: all tests pass.
- LC analyser: `SEEDS USED: 32`, 160 regret pairs, registered verdict `INCONCLUSIVE`.
- LB analysis: R3−R4 difference positive and statistically distinguishable; R=3 spike limited to Ackley/Hartmann6.

- [ ] **Step 7: Commit the LC evidence package**

Run:

```bash
git add scripts/run_lc_confirmatory.py scripts/analyse_lc_confirmatory.py scripts/analyse_lb_monotonicity.py
git add docs/SPADE-LC-CONFIRMATORY-SPEC.md results/lc-*.json tests/test_lc_final_integration.py
git commit -m "feat(spade): integrate final LC confirmation evidence"
```

Expected: one self-contained LC commit; no manufacturing protocol or `.planning` files changed.

---

### Task 3: Integrate the 64-Seed TAU Prevalence Evidence

**Files:**
- Create: `scripts/run_tau_sweep.py`
- Create: `scripts/analyse_tau_sweep.py`
- Create: `docs/SPADE-TAU-DEGENERACY-SPEC.md`
- Create: `results/tau-ackley.json`
- Create: `results/tau-hartmann6.json`
- Create: `results/tau-hill.json`
- Create: `results/tau-levy.json`
- Create: `results/tau-rosenbrock.json`
- Create: `tests/test_tau_final_integration.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: LC campaign construction and per-instance `tau_quantile` behavior.
- Produces: `load(paths)` and `pooled(cells, selector)` analysis interfaces; five balanced 64-seed result files.

- [ ] **Step 1: Write the failing TAU integration test**

Create `tests/test_tau_final_integration.py`:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _tau():
    path = ROOT / "scripts" / "analyse_tau_sweep.py"
    spec = importlib.util.spec_from_file_location("analyse_tau_sweep", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tau_results_are_balanced_over_64_seeds():
    tau = _tau()
    paths = [ROOT / "results" / f"tau-{family}.json" for family in tau.FAMILIES]
    cells, margin_sd = tau.load(paths)
    assert {key[1] for key in cells} == set(tau.FAMILIES)
    assert {key[2] for key in cells} == set(range(64))
    assert len(margin_sd) == 25


def test_hill_spade_certifies_at_prevalence_point_seven_with_perfect_containment():
    tau = _tau()
    paths = [ROOT / "results" / f"tau-{family}.json" for family in tau.FAMILIES]
    cells, _ = tau.load(paths)
    selected = {
        key: value for key, value in cells.items()
        if key[0] == "spade" and key[1] == "hill"
        and key[3] == 0.70 and key[4] == 1.0
    }
    answered = [value for value in selected.values() if value[0]]
    assert len(selected) == 64
    assert len(answered) == 40
    assert all(value[1] for value in answered)
    assert tau.cp_lower(40, 40) == pytest.approx(0.9278, abs=5e-5)
```

- [ ] **Step 2: Run the test and confirm it fails before the port**

Run:

```bash
.venv/bin/python -m pytest tests/test_tau_final_integration.py -q
```

Expected: import or missing-file failures.

- [ ] **Step 3: Port the TAU code, spec, and final 64-seed results by path**

Run:

```bash
git checkout origin/kr-effective-resolution -- scripts/run_tau_sweep.py
git checkout origin/kr-effective-resolution -- scripts/analyse_tau_sweep.py
git checkout origin/kr-effective-resolution -- docs/SPADE-TAU-DEGENERACY-SPEC.md
git checkout origin/kr-effective-resolution -- results/tau-ackley.json
git checkout origin/kr-effective-resolution -- results/tau-hartmann6.json
git checkout origin/kr-effective-resolution -- results/tau-hill.json
git checkout origin/kr-effective-resolution -- results/tau-levy.json
git checkout origin/kr-effective-resolution -- results/tau-rosenbrock.json
```

- [ ] **Step 4: Add only the named TAU result allowlists**

Append to `.gitignore` beside the existing LA/LB/LC evidence block:

```gitignore
# Joseph final TAU prevalence adjudication (64 seeds, five named families).
!results/tau-ackley.json
!results/tau-hartmann6.json
!results/tau-hill.json
!results/tau-levy.json
!results/tau-rosenbrock.json
```

Do not import Joseph's complete `.gitignore`; manufacturing evidence rules must remain unchanged.

- [ ] **Step 5: Run the TAU tests and frozen analyser**

Run:

```bash
.venv/bin/python -m pytest tests/test_tau_final_integration.py -q
.venv/bin/python scripts/analyse_tau_sweep.py
```

Expected:

- pytest: both tests pass.
- analyser: `SEEDS USED: 64`, Spearman `rho = 0.9801` over 25 cells, TAU-2 `PASS`, Hill SPADE `LB = 0.9278` at `p = 0.70`, and TAU-3 positive in three of four difficulty bins.

- [ ] **Step 6: Commit the TAU evidence package**

Run:

```bash
git add .gitignore scripts/run_tau_sweep.py scripts/analyse_tau_sweep.py
git add docs/SPADE-TAU-DEGENERACY-SPEC.md results/tau-*.json tests/test_tau_final_integration.py
git commit -m "feat(spade): integrate final TAU prevalence evidence"
```

Expected: one TAU-only commit with five result files and no registered manufacturing configuration changes.

---

### Task 4: Integrate ACK as a Retraction and Research-Only Mechanism Test

**Files:**
- Modify: `src/boec/multiround.py`
- Create: `tests/test_multiround_adaptive_theta.py`
- Modify: `tests/test_certificate_straddle.py`
- Create: `scripts/run_ack_theta.py`
- Create: `docs/SPADE-ACKLEY-THETA-SPEC.md`

**Interfaces:**
- Consumes: `certificate_straddle(mean, sd, theta, rho)`.
- Produces: `resolve_theta(mu_max: float | None, Y: Tensor, tau_frac: float) -> float`; a research-only adaptive-threshold arm; a regression proving `theta` cancellation.

- [ ] **Step 1: Add the failing theta-cancellation regression**

Append to `tests/test_certificate_straddle.py`:

```python
def test_theta_cancels_when_every_candidate_is_below_the_shifted_contour():
    mean = torch.tensor([0.01, 0.02, 0.04], dtype=torch.double)
    sd = torch.tensor([0.04, 0.03, 0.02], dtype=torch.double)
    fixed = certificate_straddle(mean, sd, theta=0.80, rho=0.95)
    adaptive = certificate_straddle(mean, sd, theta=0.108, rho=0.95)
    assert torch.equal(torch.argsort(fixed), torch.argsort(adaptive))
    assert int(fixed.argmax()) == int(adaptive.argmax())
    assert torch.allclose(fixed - adaptive, torch.full_like(fixed, -0.692))
```

- [ ] **Step 2: Port the ACK research files and backwards-compatible helper**

Run:

```bash
git checkout origin/kr-effective-resolution -- docs/SPADE-ACKLEY-THETA-SPEC.md
git checkout origin/kr-effective-resolution -- scripts/run_ack_theta.py
git checkout origin/kr-effective-resolution -- tests/test_multiround_adaptive_theta.py
```

Apply the `resolve_theta` function and per-round call from Joseph commit `6947c81` to `src/boec/multiround.py`, with this signature:

```python
def resolve_theta(mu_max: float | None, Y: torch.Tensor, tau_frac: float) -> float:
    if mu_max is not None:
        return float(tau_frac) * float(mu_max)
    return float(tau_frac) * float(Y.max())
```

Keep all registered callers passing explicit `mu_max`; only `scripts/run_ack_theta.py` may pass `None`.

- [ ] **Step 3: Correct the imported ACK header so it does not cite a missing analyser**

Replace the ACK file map with:

```markdown
Runner: `scripts/run_ack_theta.py` · Deterministic mechanism regression:
`tests/test_certificate_straddle.py::test_theta_cancels_when_every_candidate_is_below_the_shifted_contour`

The empirical ACK run was recorded on Joseph's branch without a committed standalone result
file. The integrated code therefore preserves the runner and the falsified mechanism, but does
not promote adaptive theta into the registered product.
```

- [ ] **Step 4: Run the ACK and multiround tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_multiround.py tests/test_multiround_adaptive_theta.py tests/test_certificate_straddle.py -q
```

Expected: all tests pass; explicit `mu_max` behavior remains unchanged and the theta-cancellation regression passes.

- [ ] **Step 5: Verify registered product callers remain explicit**

Run:

```bash
rg -n "multiround_design\(" src scripts tests
rg -n "mu_max=None" src scripts tests
```

Expected: registered/product callers provide a numeric `mu_max`; `mu_max=None` appears only in the ACK research runner and its tests.

- [ ] **Step 6: Commit the ACK research package**

Run:

```bash
git add src/boec/multiround.py tests/test_multiround_adaptive_theta.py tests/test_certificate_straddle.py
git add scripts/run_ack_theta.py docs/SPADE-ACKLEY-THETA-SPEC.md
git commit -m "test(spade): integrate ACK theta retraction evidence"
```

Expected: one commit that expands research instrumentation without changing the registered B5 configuration.

---

### Task 5: Reconcile Every SPADE Claim and Planning Record

**Files:**
- Modify: `docs/SPADE-ROUND-SWEEP-SPEC.md`
- Modify: `docs/HANDOFF-2026-08-29.md`
- Create: `docs/SPADE-CONCLUSIONS-2026-08-29.md`
- Modify: `docs/superpowers/specs/2026-08-28-spade-joseph-integration-manifest.md`
- Modify: `docs/superpowers/specs/2026-08-29-spade-unified-product-design.md`
- Modify: `.planning/STATE.md`
- Modify: `.planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md`

**Interfaces:**
- Consumes: verified LC, TAU, and ACK outputs from Tasks 2–4.
- Produces: one consistent claim set shared by research documentation and manufacturing planning.

- [ ] **Step 1: Import the final Joseph conclusion document as a draft**

Run:

```bash
git checkout origin/kr-effective-resolution -- docs/SPADE-CONCLUSIONS-2026-08-29.md
```

Then replace its first claim with the frozen-gate wording:

```markdown
1. **SPADE R=5 versus qLogNEI R=10 is inconclusive under the frozen equivalence rule.**
   Mean +0.0016, CI [−0.0184, +0.0208], n=160. The half-width is 0.0196, but the
   registered rule required the whole CI inside ±0.0200; the upper edge exceeds it by
   0.0008. The estimate is consistent with near-parity but does not formally establish it.
```

- [ ] **Step 2: Replace the obsolete secondary product claim**

In `docs/superpowers/specs/2026-08-29-spade-unified-product-design.md`, replace:

```markdown
Joseph round-budget (SPADE R=5 certifies; qLogNEI needs ~10)
```

with:

```markdown
Joseph round-budget: at matched R=5, SPADE produced more certified volume than qLogNEI
(+0.001353, p<0.0001); five-vs-ten regret equivalence remains formally inconclusive.
```

- [ ] **Step 3: Correct the handoff and round-sweep narrative**

Add explicit withdrawal blocks beside every historical five-vs-ten claim:

```markdown
> **WITHDRAWN by LC.** qLogNEI certified at R=3 and R=5 once n was adequate. The prior
> “needs ten rounds” result was a Clopper–Pearson sample-size threshold effect, not a
> containment deficit. Retained below only as historical evidence.
```

The active conclusion must say:

```markdown
- Matched R=5 certified volume: SPADE +0.001353, p<0.0001, at sigma_rel=0.25.
- R=5 SPADE versus R=10 qLogNEI regret: +0.0016 [−0.0184,+0.0208], formally inconclusive.
- Hill: 40/64 answered and 40/40 contained at prevalence p=0.70, LB=0.9278.
- Ackley remains a measured SPADE weakness; adaptive theta did not change the design.
- At sigma_rel=0.68, no tested arm certified.
```

- [ ] **Step 4: Update the integration manifest and diagnosis ledger**

Mark LC and TAU as ported, ACK as research-only, and replace the pending section with:

```markdown
| Item | Status |
|---|---|
| LC 32-seed evidence | Ported; frozen equivalence verdict remains INCONCLUSIVE |
| TAU 64-seed evidence | Ported; Hill certifies at p=0.70 with 40/40 containment |
| ACK adaptive theta | Ported as research instrumentation; not adopted into product |
| Rho follow-up | Not run; changing rho changes the certification estimand and requires a new registration |
```

- [ ] **Step 5: Update `.planning/STATE.md` without disturbing B5 state**

Append a separate section:

```markdown
## Joseph final research integration

- Source pinned at `origin/kr-effective-resolution` commit `b5a5bfe`.
- LC, TAU, and ACK packages are integrated as secondary research evidence.
- The B5 manufacturing gate, digest, primary claim, and archived shards are unchanged.
- The old “qLogNEI needs ten rounds” statement is withdrawn.
- The registered five-vs-ten regret verdict is inconclusive; matched-R5 certified-volume
  advantage and Hill p=0.70 containment survive.
```

- [ ] **Step 6: Scan for stale or overbroad claims**

Run:

```bash
rg -n "qLogNEI needs 10|needs ~10|half the differentiation cycles|parity survives|matches qLogNEI at 10" docs .planning
rg -n "40/64|0\.9278" docs .planning
rg -n "sigma_rel = 0\.68|sigma_rel = 0\.25" docs/SPADE-CONCLUSIONS-2026-08-29.md docs/SPADE-LC-CONFIRMATORY-SPEC.md docs/SPADE-TAU-DEGENERACY-SPEC.md
```

Expected:

- Obsolete phrases appear only inside clearly marked historical/withdrawn blocks.
- Every `40/64` or `0.9278` Hill claim is adjacent to `p = 0.70`.
- The conclusions carry both the `0.25` scope and `0.68` ceiling.

- [ ] **Step 7: Commit claim reconciliation**

Run:

```bash
git add docs/SPADE-ROUND-SWEEP-SPEC.md docs/HANDOFF-2026-08-29.md
git add docs/SPADE-CONCLUSIONS-2026-08-29.md docs/superpowers/specs/2026-08-28-spade-joseph-integration-manifest.md
git add docs/superpowers/specs/2026-08-29-spade-unified-product-design.md
git add .planning/STATE.md .planning/SPADE-SCALAR-RECOVERY-DIAGNOSIS.md
git commit -m "docs(spade): reconcile Joseph final evidence and claims"
```

Expected: documentation and planning changes only.

---

### Task 6: Verify the Integrated Branch and Prepare a Safe Merge

**Files:**
- Verify all files changed in Tasks 1–5.

**Interfaces:**
- Consumes: complete selective-integration branch.
- Produces: a reviewable, test-green branch safe to merge after the active B5 process is archived.

- [ ] **Step 1: Run the focused integration suite**

Run:

```bash
.venv/bin/python -m pytest tests/test_lc_final_integration.py tests/test_tau_final_integration.py tests/test_multiround.py tests/test_multiround_adaptive_theta.py tests/test_certificate_straddle.py -q
```

Expected: `0 failed`.

- [ ] **Step 2: Run SPADE manufacturing safeguards**

Run:

```bash
./scripts/run_spade_safeguard_tests.sh
```

Expected: safeguard script exits `0`; registered protocol/digest compatibility tests pass.

- [ ] **Step 3: Re-run both imported adjudicators from committed files**

Run:

```bash
.venv/bin/python scripts/analyse_lc_confirmatory.py
.venv/bin/python scripts/analyse_tau_sweep.py
```

Expected:

- LC: 32 seeds, 160 regret pairs, formal verdict `INCONCLUSIVE`, matched-R5 volume advantage retained.
- TAU: 64 seeds, `rho=0.9801`, Hill 40/64 answered, 40/40 contained, `LB=0.9278`, `p=0.70`.

- [ ] **Step 4: Run the full test suite**

Run:

```bash
.venv/bin/python -m pytest tests/ -q
```

Expected: `0 failed`; pre-existing warnings may remain.

- [ ] **Step 5: Verify no registered B5 source or evidence was rewritten**

Run:

```bash
git diff main...HEAD -- configs/experiment/spade-joint.yaml results/spade-development-*.jsonl.gz src/boec/spade_study.py
git diff --check main...HEAD
```

Expected: first command prints no diff; second command exits `0` with no whitespace errors.

- [ ] **Step 6: Review the exact branch delta**

Run:

```bash
git status --short --branch
git log --oneline main..HEAD
git diff --stat main...HEAD
```

Expected: clean worktree; five integration commits; delta limited to named LC, TAU, ACK, test, documentation, `.gitignore`, and `.planning` files.

- [ ] **Step 7: Merge only after the B5 runner is finished or archived**

First verify the active manufacturing worktree has no running registered process:

```bash
cat /tmp/spade-durable.status
pgrep -af "run_spade_development|spade_gate_then_full_watchdog"
```

Expected before merge: status reports a terminal PASS/FAIL/archive state and `pgrep` finds no live registered worker. If a registered worker is still active, leave the integration branch ready and do not merge it yet.

When terminal:

```bash
git -C .worktrees/spade-campaign merge --no-ff codex/spade-joseph-final-integration
git -C .worktrees/spade-campaign status --short --branch
```

Expected: a merge commit on local `main` and a clean worktree.

- [ ] **Step 8: Push the reviewed integration**

Run:

```bash
git -C .worktrees/spade-campaign push origin main
```

Expected: `origin/main` advances to the reviewed local merge commit.

---

## Self-Review Results

- **Spec coverage:** All 15 commits after `07ae40e` are assigned: LC (7 commits), TAU (5), ACK (2), conclusions (1).
- **Manufacturing protection:** The plan never wholesale-merges Joseph's tree, never imports his `.gitignore`, and never changes the B5 digest or registered result shards.
- **Scientific consistency:** The stale five-vs-ten certification claim is withdrawn; the LC registered equivalence rule remains authoritative; Hill prevalence and real-noise limitations are mandatory.
- **Type consistency:** `resolve_theta(mu_max: float | None, Y: torch.Tensor, tau_frac: float) -> float` is used consistently; registered callers remain explicit.
- **Test coverage:** Each evidence package has focused tests, deterministic analyser checks, manufacturing safeguards, and a full-suite gate.

