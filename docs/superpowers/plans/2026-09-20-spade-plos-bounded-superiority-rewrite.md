# SPADE PLOS ONE Bounded-Superiority Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the active PLOS ONE submission package around the defensible conclusion that SPADE performs better for the tested operating-region decision, while preserving adverse point-optimization results and all publication limits.

**Architecture:** Treat the audited `codex/paper-ready` manuscript and claim ledger as the scientific source, but keep `manuscript/SPADE-PLOS-ONE.md` as the active submission source. Add a focused textual claim guard before rewriting prose, synchronize the claim ledger, manuscript, cover letter, README, research summary, and planning handoff, then regenerate all Word derivatives from tracked Markdown and verify their manifests.

**Tech Stack:** Markdown, Python 3.11, pytest, python-docx, SHA-256 derivative manifests, repository analysis scripts

## Global Constraints

- The governing thesis is use-case-specific superiority: SPADE is better for the tested operating-region decision, not universally better.
- Use C1 `-0.0005` with 95% CI `[-0.0221,+0.0207]`, `p=0.96`, `n=160`; say “no detectable difference,” never “matches,” “parity,” or “equivalent.”
- Use C3 `+0.000855` with 95% CI `[+0.000691,+0.001028]`, `p<0.0001`, `n=320` dependent cells; do not use stale current values `+0.0016` or `+0.001353`.
- Retain the adverse DoE result: SPADE-minus-DoE regret `+0.1026`, 95% CI `[+0.0486,+0.1578]`, `p=0.0003`; DoE uses three rounds and SPADE five.
- Retain C2 denominators: SPADE 66/160 answered and 66/66 contained; screened DoE 122/160 and 85/122; unscreened DoE 134/160 and 77/134.
- Retain the real-noise ceiling, `NO_SELECTION`, unopened lockbox, missing prospective wet-lab validation, and dependence/calibration limitations.
- Do not edit frozen primary result files, rerun experiments, inspect lockbox outcomes, submit to PLOS, publish a DOI, or change repository visibility.
- Preserve unrelated local changes and the tracked author identities, affiliations, correspondence details, licensing, and repository URL.

---

### Task 1: Add a manuscript claim-consistency guard

**Files:**
- Create: `tests/test_spade_plos_claims.py`
- Modify: `tests/test_publication_bundle.py`

**Interfaces:**
- Consumes: active Markdown files under `manuscript/`, `README.md`, `docs/RESEARCH-SUMMARY.md`, and `.planning/STATE.md`
- Produces: pytest failures for stale values, forbidden universal/equivalence wording, omitted adverse results, and missing bounded-superiority language

- [ ] **Step 1: Write the failing current-claim tests**

Create `tests/test_spade_plos_claims.py` with tests equivalent to:

```python
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript/SPADE-PLOS-ONE.md"
ACTIVE = [
    MANUSCRIPT,
    ROOT / "manuscript/SPADE-PLOS-ONE-cover-letter.md",
    ROOT / "manuscript/CLAIMS-AND-SOURCES.md",
    ROOT / "README.md",
    ROOT / "docs/RESEARCH-SUMMARY.md",
    ROOT / ".planning/STATE.md",
]


def _text(path: Path) -> str:
    assert path.is_file(), f"missing active publication document: {path}"
    return path.read_text(encoding="utf-8")


def test_active_publication_documents_reject_stale_headline_values() -> None:
    for path in ACTIVE:
        text = _text(path)
        assert "0.001353" not in text, path
        assert not re.search(r"(?<![0-9])0\.0016(?![0-9])", text), path


def test_manuscript_states_bounded_operating_region_superiority() -> None:
    text = _text(MANUSCRIPT)
    assert "better for the tested operating-region decision" in text
    assert "greater certified volume" in text
    assert "no detectable regret difference" in text
    assert "DoE found the better point recipe" in text


def test_manuscript_pins_corrected_primary_values_and_denominators() -> None:
    text = _text(MANUSCRIPT)
    for token in (
        "-0.0005", "0.000855", "0.1026",
        "66/160", "66/66", "122/160", "85/122", "134/160", "77/134",
    ):
        assert token in text


def test_manuscript_retains_required_limits() -> None:
    text = _text(MANUSCRIPT)
    for token in (
        "NO_SELECTION", "lockbox", "relative noise 0.68",
        "prospective wet-lab", "not equivalence",
    ):
        assert token in text


def test_manuscript_does_not_make_unqualified_superiority_claims() -> None:
    text = _text(MANUSCRIPT)
    forbidden = (
        r"\bSPADE is (?:universally )?(?:best|better overall)\b",
        r"\bSPADE (?:matches|is equivalent to) qLogNEI\b",
        r"\bSPADE beats DoE\b(?![^.\n]*operating region)",
    )
    for pattern in forbidden:
        assert not re.search(pattern, text, flags=re.IGNORECASE)
```

Update `tests/test_publication_bundle.py` assertions that encode the superseded two-round manuscript so they require the bounded-superiority claims, current four-figure inventory, adverse/null results, abstract length, and resolved citation order without requiring stale phrases such as “only 0.0063 above primary SPADE.”

- [ ] **Step 2: Run the claim tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_spade_plos_claims.py tests/test_publication_bundle.py
```

Expected: failures for missing `manuscript/CLAIMS-AND-SOURCES.md`, stale `0.0016`/`0.001353`, old parity wording, and old publication-bundle phrase assertions.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_spade_plos_claims.py tests/test_publication_bundle.py
git commit -m "test: define bounded SPADE PLOS claims"
```

### Task 2: Rebuild the claim ledger and canonical PLOS manuscript

**Files:**
- Create: `manuscript/CLAIMS-AND-SOURCES.md`
- Modify: `manuscript/SPADE-PLOS-ONE.md`
- Reference only: `.worktrees/paper-ready/publication/manuscript/{MANUSCRIPT,CLAIMS-AND-SOURCES,METHODS,SUPPLEMENT,PROTOCOLS}.md`
- Reference only: `.worktrees/paper-ready/publication/evidence/manuscript-consistency-audit.md`

**Interfaces:**
- Consumes: audited C1–C6, S1–S3, L1–L4 evidence and active PLOS author/submission metadata
- Produces: authoritative active claim ledger and canonical PLOS Markdown source

- [ ] **Step 1: Recreate the active claim ledger**

Copy the audited ledger structure into `manuscript/CLAIMS-AND-SOURCES.md`, updating paths from the consolidated paper-ready tree to the corresponding active repository paths. Retain each claim’s allowed wording, forbidden wording, exact estimate, evidence file, analysis command, guard coverage, and limitation. Add an opening rule:

```markdown
The manuscript may say SPADE is better only when the operating-region endpoint,
matched-round setting, benchmark scope, and relevant containment/answer denominators
are named. “Better” without those qualifiers is forbidden.
```

- [ ] **Step 2: Replace the title, abstract, and contribution statement**

Use a title centered on decision-specific superiority, for example:

```markdown
# SPADE improves operating-region decisions under fixed experimental budgets: a synthetic comparison with Bayesian optimization and response-surface design
```

Keep the abstract at 250 words or fewer and include C3 first, then C1, C2/adverse, scope, and limitations. It must contain the exact phrase “better for the tested operating-region decision.”

- [ ] **Step 3: Rewrite the introduction and methods from audited sources**

Describe SPADE as an assay-oriented integration of established GP level-set and conservative-set methods. Replace the false “certificate-contour straddle targets the threshold” mechanism account with the architectural account: space-filling opening, adaptive high-response sampling, common posterior conservative-set estimator, and abstention. State LOFO calibration for C3, in-sample calibration/fallback for C2, and flat-cell/bootstrap dependence assumptions.

- [ ] **Step 4: Reorder and rewrite Results**

Use this order:

1. C3 matched-R5 operating-region advantage.
2. C1 R5-versus-R10 point result.
3. C2 DoE trade-off and adverse regret result.
4. C5/C6 family, prevalence, and margin-to-noise scope.
5. S2/S3 Joseph mean-marginalisation and real-data posterior-collapse diagnosis.
6. S1 failed targeting, L1 real-noise ceiling, and joint-protocol `NO_SELECTION`.

Locally state certification dimensions or place all dimensions in the immediately preceding results table.

- [ ] **Step 5: Rewrite Discussion and Conclusions**

End with a method-selection recommendation:

```markdown
Choose SPADE when a moderate-noise, fixed-well campaign must return a conservative
operating region and may abstain; choose a point optimizer when only one recipe is
required. These computational results do not establish recipe equivalence,
manufacturing qualification, regulatory validation, or prospective wet-lab performance.
```

- [ ] **Step 6: Run the focused tests and verify GREEN**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_spade_plos_claims.py tests/test_publication_bundle.py
```

Expected: all tests pass.

- [ ] **Step 7: Commit the scientific source rewrite**

```bash
git add manuscript/CLAIMS-AND-SOURCES.md manuscript/SPADE-PLOS-ONE.md tests/test_spade_plos_claims.py tests/test_publication_bundle.py
git commit -m "docs: position SPADE for operating-region decisions"
```

### Task 3: Synchronize the active submission narrative

**Files:**
- Modify: `manuscript/SPADE-PLOS-ONE-cover-letter.md`
- Modify: `README.md`
- Modify: `docs/RESEARCH-SUMMARY.md`
- Modify: `.planning/STATE.md`
- Modify: `manuscript/spade-plos-remaining-blockers.md`
- Preserve: `manuscript/JOSEPH-OK-REQUEST.md`
- Preserve: `manuscript/ZENODO-DEPOSIT.md`

**Interfaces:**
- Consumes: canonical title, abstract, conclusion, and claim ledger from Task 2
- Produces: one consistent active thesis across submission and repository entry points

- [ ] **Step 1: Rewrite the cover letter**

Lead with the bounded-superiority result and include corrected C3, C1, and C2/adverse values. Explicitly state that the contribution is decision guidance for operating-region use cases, not universal superiority. Retain PLOS-specific declarations, suggested editor expertise, repository URL, DOI status, and pending co-author approval.

- [ ] **Step 2: Update repository and research summaries**

Revise current-tense sections of `README.md` and `docs/RESEARCH-SUMMARY.md` to name the new manuscript thesis and corrected values. Preserve historical numerical records as historical; do not rewrite archived evidence. Add pointers to `manuscript/CLAIMS-AND-SOURCES.md`.

- [ ] **Step 3: Update planning handoff and blockers**

Prepend a 2026-09-20 handoff to `.planning/STATE.md` recording the approved bounded-superiority thesis, corrected values, affected files, and outstanding author/DOI/submission gates. Update `manuscript/spade-plos-remaining-blockers.md` so its remaining work is only author/account/external submission work after technical verification.

- [ ] **Step 4: Run active-document claim tests**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_spade_plos_claims.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit synchronized narrative files**

```bash
git add manuscript/SPADE-PLOS-ONE-cover-letter.md README.md docs/RESEARCH-SUMMARY.md .planning/STATE.md manuscript/spade-plos-remaining-blockers.md
git commit -m "docs: synchronize SPADE submission positioning"
```

### Task 4: Reproduce the manuscript’s scientific claims

**Files:**
- Verify: `manuscript/SPADE-PLOS-ONE.md`
- Verify: `manuscript/CLAIMS-AND-SOURCES.md`
- Verify: `.worktrees/paper-ready/research/results/`
- Verify: `.worktrees/paper-ready/software/scripts/`

**Interfaces:**
- Consumes: frozen C1–C6/S1 inputs in the audited `codex/paper-ready` worktree
- Produces: fresh terminal evidence that the rewritten manuscript matches retained results

- [ ] **Step 1: Run the current conclusion verifier**

Run the audited paper-ready verifier:

```bash
(cd .worktrees/paper-ready && .venv/bin/python software/scripts/verify_conclusions.py)
```

Expected: all guarded current values reproduce.

- [ ] **Step 2: Run the DC analyser**

Run:

```bash
(cd .worktrees/paper-ready && .venv/bin/python software/scripts/analyse_dc_doe_certificate.py)
```

Expected: C1 `-0.0005`; C2 SPADE 66/66, screened DoE 85/122, unscreened DoE 77/134; adverse SPADE-minus-DoE regret `+0.1026`.

- [ ] **Step 3: Run the LC analyser**

Run:

```bash
(cd .worktrees/paper-ready && \
  .venv/bin/python software/scripts/analyse_lc_confirmatory.py \
    --glob 'research/results/comparisons/lc-*.json')
```

Expected: matched-R5 LOFO certified-volume difference `+0.000855` with `n=320`; no positive R3 claim.

- [ ] **Step 4: Run the TAU and TT analysers**

Run:

```bash
(cd .worktrees/paper-ready && .venv/bin/python software/scripts/analyse_tau_sweep.py)
(cd .worktrees/paper-ready && .venv/bin/python software/scripts/analyse_tt_theta_tau.py)
```

Expected: descriptive margin-to-noise association and Hill 40/64, 40/40 result reproduce; target-aligned mechanism fails adoption and worsens regret.

- [ ] **Step 5: Record the audited evidence location**

State in `manuscript/CLAIMS-AND-SOURCES.md` that current C1–C6/S1 reproduction uses the
consolidated evidence paths on `codex/paper-ready`, while the active PLOS Markdown/DOCX
remain on `codex/publication-readiness`. Do not copy or alter result files solely to make
paths uniform.

### Task 5: Regenerate Word documents and derivative manifests

**Files:**
- Modify: `manuscript/SPADE-PLOS-ONE.docx`
- Modify: `manuscript/SPADE-PLOS-ONE.docx.manifest.json`
- Modify: `manuscript/SPADE-PLOS-ONE-submission.docx`
- Modify: `manuscript/SPADE-PLOS-ONE-submission.docx.manifest.json`
- Modify: `manuscript/SPADE-PLOS-ONE-cover-letter.docx`
- Modify: `manuscript/SPADE-PLOS-ONE-cover-letter.docx.manifest.json`
- Test: `tests/test_manuscript_docx.py`
- Test: `tests/test_submission_package.py`

**Interfaces:**
- Consumes: canonical Markdown sources and current four PLOS figures
- Produces: reading DOCX, figure-free PLOS submission DOCX, cover-letter DOCX, and source-bound manifests

- [ ] **Step 1: Run builder tests before generation**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_manuscript_docx.py
```

Expected: all tests pass.

- [ ] **Step 2: Generate the reading manuscript**

Run:

```bash
.venv/bin/python scripts/build_manuscript_docx.py
```

Expected: `SPADE-PLOS-ONE.docx` and its manifest are replaced from the current Markdown and four embedded figures.

- [ ] **Step 3: Generate the submission manuscript**

Run:

```bash
.venv/bin/python scripts/build_manuscript_docx.py --submission --output manuscript/SPADE-PLOS-ONE-submission.docx
```

Expected: submission DOCX and manifest contain captions but no embedded figures.

- [ ] **Step 4: Generate the cover letter**

Run:

```bash
.venv/bin/python scripts/build_manuscript_docx.py \
  --input manuscript/SPADE-PLOS-ONE-cover-letter.md \
  --output manuscript/SPADE-PLOS-ONE-cover-letter.docx \
  --submission --cover-letter
```

Expected: letter DOCX and manifest use cover-letter mode.

- [ ] **Step 5: Run derivative and package tests**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_manuscript_docx.py \
  tests/test_submission_package.py \
  tests/test_publication_bundle.py \
  tests/test_spade_plos_claims.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit regenerated submission files**

```bash
git add manuscript/SPADE-PLOS-ONE*.docx manuscript/SPADE-PLOS-ONE*.manifest.json
git commit -m "build: regenerate bounded SPADE submission documents"
```

### Task 6: Final package verification

**Files:**
- Verify: all changed active publication files
- Do not commit: temporary upload ZIP or temporary rendered QA pages

**Interfaces:**
- Consumes: synchronized Markdown, DOCX derivatives, figures, tables, and manifests
- Produces: final evidence-backed completion report and remaining author-owned blockers

- [ ] **Step 1: Run the focused publication suite**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_spade_plos_claims.py \
  tests/test_publication_bundle.py \
  tests/test_manuscript_docx.py \
  tests/test_paper_figure_builders.py \
  tests/test_paper_figure_layout.py \
  tests/test_publication_tables.py \
  tests/test_submission_package.py
```

Expected: all focused publication tests pass.

- [ ] **Step 2: Check formatting and stale claims**

Run:

```bash
git diff --check
rg -n "0\.001353|(?<![0-9])0\.0016(?![0-9])|SPADE matches|SPADE is equivalent|SPADE beats DoE" \
  manuscript README.md docs/RESEARCH-SUMMARY.md .planning/STATE.md
```

Expected: `git diff --check` exits zero; search returns no active stale/forbidden claims except explicitly labeled historical corrections in the claim ledger.

- [ ] **Step 3: Validate the local upload inputs**

Run:

```bash
.venv/bin/python -c \
  "from pathlib import Path; from scripts.prepare_submission_bundle import validate_inputs; validate_inputs(Path.cwd()); print('submission inputs valid')"
```

Expected: `submission inputs valid`.

- [ ] **Step 4: Review changed-file scope**

Run:

```bash
git status --short
git diff --stat
git diff -- manuscript README.md docs/RESEARCH-SUMMARY.md .planning/STATE.md tests/test_spade_plos_claims.py tests/test_publication_bundle.py
```

Expected: only approved publication-package, claim-guard, planning, and generated-derivative changes; pre-existing figure/script changes remain identifiable and are not silently reverted.

- [ ] **Step 5: Report remaining external gates**

Report technical verification separately from author-owned work. Remaining external gates include Joseph’s approval, final author scientific review, declarations/account details, DOI deposit authorization, and journal submission. Do not claim that any external gate is complete.
