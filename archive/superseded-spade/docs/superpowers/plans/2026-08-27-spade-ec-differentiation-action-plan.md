# SPADE for Synthetic EC-Differentiation Optimization — Action Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to carry out this plan task-by-task. This is a roadmap and evidence plan; it does not authorize reopening frozen scalar lockbox artifacts.

**Goal:** Make SPADE the strongest defensible computational method for ESC-to-EC differentiation process development, with a multi-CQA operating-region output and a manuscript whose claims match the registered evidence.

**Architecture:** Keep the existing scalar SPADE benchmark and active LOO-tail recovery as a sealed evidence body. Build the EC-differentiation contribution as a separate synthetic vector-valued benchmark: common recipes, three release CQAs, independent endpoint surrogates, exact certificate intersection, and explicit abstention. Add process realism through registered factor semantics, donor/lot/passage perturbation scenarios, and well/round cost reporting without pretending these are measured cells.

**Tech Stack:** Existing PyTorch/BoTorch SPADE primitives, `manufacturing_qualification.py`, `manufacturing_benchmark.py`, canonical JSON runners, YAML registrations, pytest, and the manuscript documents under `docs/`.

## Non-negotiable evidence boundaries

- The current project is synthetic-only; do not claim that a CHIR, BMP4, ECM, media, or passage condition is biologically optimal.
- Do not inject unsigned lab CD31 candidates into the benchmark. `docs/LAB-DATA-FOR-BO.md` says the official score is unsigned and viability/yield are absent.
- Do not modify or reinterpret the active Cursor campaign files: `src/boec/spade.py`, `src/boec/spade_study.py`, `src/boec/reliable_region.py`, `src/boec/selfcalib.py`, `configs/experiment/spade-joint.yaml`, or its running `results/` artifacts.
- Do not reuse the scalar lockbox as multi-CQA evidence. A vector-valued claim requires a new protocol digest, new families, and fresh results.
- Repeated algorithm seeds are computational replicates, not donors, lots, passages, operators, or biological replicates.

## Source documents to keep synchronized

Before each phase, read and cross-check:

- `.planning/STATE.md` and `.planning/ROADMAP.md` for the scalar milestone and its `NO_SELECTION`/lockbox stop rule.
- `docs/RESEARCH-SUMMARY.md` for the current paper scope, limitations, and claims already supported.
- `docs/superpowers/specs/2026-08-27-spade-multi-cqa-qualification-design.md` for the overlay contract.
- `docs/superpowers/specs/2026-08-27-spade-multi-cqa-benchmark-design.md` for the registered synthetic vector benchmark.
- `docs/LAB-DATA-FOR-BO.md` for the explicit prohibition on inventing signed EC metrics.

At the end of each phase, update only the document sections that the phase actually changes; never silently revise a frozen result.

---

## Phase 0 — Protect and finish the scalar evidence body

**Owner:** active Cursor recovery worktree.  
**Deliverable:** a frozen scalar status that can be cited independently of the EC extension.

1. Monitor the Hill/Levy 0–15 gate until it either clears or fails the registered answer-rate and empirical-containment bars.
2. If it clears, allow only the registered development → `SELECTED` → power → lockbox sequence. If it fails, record the negative stop; do not tune after seeing the outcome.
3. Keep the manuscript’s existing scalar conclusions bounded: region-first architecture is promising, targeting mechanism is not established, and general certificate portability is not established.
4. Record the final status in chat and the existing planning state; do not create a new status markdown file.

**Gate:** No multi-CQA result is used to rescue or overturn the scalar `NO_SELECTION` outcome.

## Phase 1 — Complete the registered multi-CQA synthetic benchmark

**Files already implemented:**

- `src/boec/manufacturing_qualification.py`
- `src/boec/manufacturing_benchmark.py`
- `scripts/run_spade_multi_cqa_benchmark.py`
- `configs/experiment/spade-multi-cqa-benchmark.yaml`

1. Run the smoke command and verify canonical reproducibility:

```bash
PYTHONPATH=.:src .venv/bin/python scripts/run_spade_multi_cqa_benchmark.py \
  --out /tmp/spade-multi-cqa-smoke.json --replicates 1 --algorithm-seeds 1 \
  --train-count 16 --grid-count 128
```

2. Run the registered development benchmark with 25 replicates × 2 algorithm seeds for `aligned`, `moderate_conflict`, and `strong_conflict`.
3. Audit every row for finite metrics, exact source commit, protocol digest, and no truth leakage into fitting or certificate selection.
4. Report per family: scalar unsafe-release rate, joint unsafe-release rate, scalar/joint non-empty rate, scalar/joint volume, containment, and limiting CQA.
5. Use replicate-level paired summaries only. Never treat candidate-grid points as independent observations.

**Success criteria:**

- The aligned family normally retains a non-empty joint region.
- The moderate-conflict family shows whether joint certification trades volume for safety.
- The strong-conflict family may abstain; abstention is a registered safety outcome, not a failure to hide.
- The joint method has no unsafe issued points in every family where its certificate is non-empty, or the paper reports the observed shortfall plainly.

## Phase 2 — Make the synthetic surfaces EC-process-relevant without fabricating biology

**New files:** `src/boec/ec_process_benchmark.py`, `tests/test_ec_process_benchmark.py`, `configs/experiment/spade-ec-process-benchmark.yaml`.

1. Define six coded process factors with documented semantics: ECM identity/dose, CHIR timing, BMP4 dose, induction/finishing medium, passage timing, and seeding density or culture duration.
2. Keep all factors normalized to `[0,1]`; do not use the current unsigned laboratory rows to fit ranges or thresholds.
3. Define synthetic CQAs with different optima and smoothness: endothelial identity, viable EC yield, viability, and an optional unwanted-lineage penalty. Start with three CQAs to match the registered overlay; add the fourth only in a new protocol version because Bonferroni allocation changes.
4. Include at least three generator families: aligned, moderate trade-off, and strong trade-off. Add a ridge/plateau family to test broad manufacturing windows rather than only Gaussian peaks.
5. Register thresholds, direction, assay noise, factor meanings, and family parameters before generating results.
6. Keep the synthetic generator’s prose explicit: it is structurally motivated by EC differentiation logistics, not fitted to EC biology.

**Gate:** A reviewer can identify which conclusions are about algorithmic qualification and which would require real cell measurements.

## Phase 3 — Add manufacturing robustness scenarios

**New files:** extend `ec_process_benchmark.py` and add `tests/test_ec_robustness.py` plus a new YAML protocol version.

1. Add fixed synthetic perturbation blocks for donor-like response shifts, reagent-lot shifts, passage drift, and site/operator noise.
2. Fit only on development blocks and evaluate on held-out blocks. Use leave-one-block-out summaries; do not pool blocks as IID grid points.
3. Compare three policies: nominal certificate, worst-block intersection, and block-robust intersection. Keep the current joint-CQA certificate as the release region.
4. Report robustness cost explicitly: joint volume, empty-region rate, unsafe-release rate, and number of blocks covered.
5. Do not call these “donor validation.” Call them stress tests of transportability assumptions.

**Success criteria:** The method either demonstrates reduced unsafe release under perturbations or clearly identifies the conditions under which it abstains. A smaller region is acceptable if its safety tradeoff is measured.

## Phase 4 — Make cost and round economy part of the decision

**New files:** `src/boec/manufacturing_cost.py`, `tests/test_manufacturing_cost.py`, `configs/experiment/spade-ec-process-cost.yaml`.

1. Keep wells and plate rounds as separate primary cost currencies, consistent with `docs/RESEARCH-SUMMARY.md`.
2. Add only predeclared synthetic resource terms: incubation/passaging days, destructive-assay burden, and optional reagent/assay cost units.
3. Never infer cost weights from the current lab drop. Store the weights in the protocol and run sensitivity bounds.
4. Compare scalar and joint decisions on safety-adjusted cost: cost to obtain a non-empty qualified region, cost per qualified grid volume, and cost of abstention.
5. Do not convert synthetic cost units into dollars or claim calendar savings without site-specific data.

**Gate:** Cost reporting cannot change the certificate mask or conceal empty certificates.

## Phase 5 — Run the full confirmatory synthetic study

1. Freeze a new protocol digest covering the EC-process families, CQAs, robustness blocks, cost terms, seeds, and metrics.
2. Run at least 25 paired replicates × 2 algorithm seeds per family, averaging seeds before inference.
3. Compare the scalar-primary baseline, joint overlay, Sobol/static coverage, qLogNEI, and any process-aware SPADE variant at the same 48-well budget.
4. Keep acquisition and terminal qualification separable: report whether a difference comes from sampling, surrogate, or the joint terminal decision.
5. Apply the same no-family-pooling and multiplicity discipline already used by the scalar study.
6. Generate a machine-readable JSON artifact with source/protocol digests and a human-readable table generated from that artifact.

**Required table columns:** family, replicate count, method, non-empty rate, median/IQR volume, unsafe-release rate, empirical containment, limiting CQA, wells, rounds, and synthetic resource cost.

**Decision rule:** If joint certification reduces unsafe release but frequently abstains, publish that as a safety-versus-availability tradeoff. Do not optimize thresholds after seeing this table.

## Phase 6 — Integrate into the paper without overclaiming

**Primary document:** `docs/RESEARCH-SUMMARY.md` (or the manuscript branch’s successor document once Cursor finishes its rewrite).

1. Keep the existing introduction’s central thesis: rankings depend on estimand, surrogate, budget, rounds, noise, extrapolation, and terminal decision.
2. Add a short manufacturing extension paragraph after the region-first motivation: real release decisions involve multiple CQAs, so SPADE can intersect endpoint certificates.
3. Add a Methods subsection describing the synthetic EC-process benchmark and the exact scalar-versus-joint comparison.
4. Add Results only from the frozen benchmark artifact. State the number of families/replicates and show unsafe-release, abstention, containment, volume, and cost tradeoffs.
5. Add a limitations paragraph: synthetic surfaces are not EC biology; independent endpoint GPs do not model CQA correlation; donor/lot/site transport is simulated stress testing; no real release criterion is validated.
6. Preserve the existing negative scalar findings and do not use the extension to claim SPADE is universally superior to BO or RSM.
7. Update the conclusion to say “computational multi-CQA qualification framework for EC-process development,” not “validated EC differentiation optimizer.”

## Phase 7 — Final quality and claim audit

Run:

```bash
.venv/bin/pytest tests/test_manufacturing_benchmark.py \
  tests/test_manufacturing_qualification.py tests/test_reliable_region.py -q
git diff --check
git status --short --branch
```

Then verify:

- Every numerical manuscript claim has a committed JSON source artifact.
- Every claim labels synthetic versus biological evidence.
- No unsigned lab data entered a model.
- No active Cursor result was edited or reinterpreted.
- Empty certificates are reported as abstention, not silently converted to zero success.
- The current scalar `NO_SELECTION`/lockbox stop state remains intact unless the registered scalar workflow itself changes it.

## Definition of done

SPADE is “best it can be” for this synthetic EC-differentiation paper when the code,
protocol, benchmark artifact, and manuscript all agree on the same bounded claim:
SPADE provides a reproducible, region-first, multi-CQA qualification decision under
matched computational conditions, can identify the limiting quality attribute, and
fails closed when evidence does not support a joint operating window. It is not
presented as biologically validated without biological data.
