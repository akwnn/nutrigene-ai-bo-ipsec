# TRIAGE — every experiment, diagnostic and analysis, labelled

**One label per item.** The result this triages against is three sentences:

> **1.** Under the registered scoring rule — best value observed (rule A) — the classical DoE
> pipeline outperforms Bayesian optimization at a realistic budget.
> **2.** Under the alternative rule — each method scored at the recipe its own model
> recommends (rule C) — Bayesian optimization outperforms the DoE pipeline, in every cell tested.
> **3.** The mechanism is that the polynomial's model recommends a condition worse than the best
> it measured, while the GP's recommends better.
>
> **Supporting:** the finding holds on standard test functions, so it is not a property of the
> constructed oracle.

**Sentence 2 is true only under the *unconstrained* argmax**, which is what Q41 designated
primary. Under the constrained variant three of four cells are null. Both are reported per
Q41; the label below tracks the primary.

| Label | Meaning | Count |
|---|---|---|
| **CORE** | Directly produces or validates one of the three sentences | **13** |
| **DEFENCE** | Closes a specific objection a reviewer would raise | **21** |
| **ARCHIVE** | Real work, correctly done, not needed for the paper | **19** |
| **VOID** | Superseded, or found to be measuring the wrong thing | **12** |
| | | **65** |

---

## CORE

| ID | Title | Label | Objection closed | Superseded by |
|---|---|---|---|---|
| **E2** | The main grid — 7 arms, 48 evaluations, d∈{6,8} × σ∈{0.10,0.25}, n=25 | CORE | — | — |
| **Q27** | The d=8 DoE arm — Q24's missing comparison | CORE | — | — |
| **Q17** | Score regret at the noiseless value of the point the method *selected* | CORE | — | — |
| **Q20 §1** | Two named estimands; per-instance comparator selection forbidden | CORE | — | — |
| **Q20 §2** | Wilcoxon governs the yes/no; the bootstrap reports magnitude | CORE | — | — |
| **Q28** | The DoE arm's scoring rule was never registered, and the two rules reverse every cell | CORE | — | — |
| **Q41** | 🔒 THE ESTIMAND DECISION — the unconstrained argmax is primary | CORE | — | — |
| **Q35** | The three DoE scorings; saddle in 200/200; unconstrained − constrained = +0.2995 | CORE | — | — |
| **Q34** | Design × surrogate × rule factorial — the registered primary held in all four cells | CORE | — | — |
| **Q45** | The four-factor refit — removes Q34's model-dimensionality confound | CORE | — | — |
| **Q42** | Five families, four cells — the standard-function generality check | CORE | — | — |
| **Q52 §2** | The budget-to-target curve, and the arrival-rate result that survives it | CORE | — | — |
| **D20 fix + rescore** | The classical arm put back on rule A; guard test added | CORE | — | — |

**Why each is here.** E2 and Q27 *are* sentence 1. Q28 discovered the question, Q41 answered it,
Q35 measured it — together they are sentence 2 and the decomposition sentence 3 rests on. Q34
separates design from surrogate from rule, which is the only reason sentence 3 can name a
mechanism rather than a correlation; Q45 is not optional beside it, because without the
four-factor refit Q34's design contrast is confounded with model dimensionality. Q42 is the
supporting claim. Q52 §2 is the curve. Q17/Q20 are governing decisions that every number in the
project passes through. D20 is a correction to CORE numbers and ships with the test that stops it
recurring.

---

## DEFENCE

| ID | Title | Label | Objection closed | Superseded by |
|---|---|---|---|---|
| **Q30** | The additive-kernel arm | DEFENCE | *"Your GP is misspecified for a 93%-additive landscape — fix the model and BO wins."* Held-out R² 0.375→0.744 and regret moved 0.0015, p=0.71. | — |
| **Q25** | Lengthscale prior | DEFENCE | *"Your lengthscale prior crippled the GP."* Gamma(3,6) is significantly **worse** at ARD separation in every cell. | — |
| **Q21** | Acquisition-solver failure rate | DEFENCE | *"Your acquisition optimiser was silently failing."* 4/3400 = 0.118%, against a threshold registered at 1% before the rate was known. | — |
| **Q26** | Opening batch size | DEFENCE | *"Your 2d+2 opening design was too small."* No detectable effect at the primary cell; the effect that exists is at σ=0.10 and does not rescue BO. | — |
| **Q43** | Permutation test on the surrogate effect | DEFENCE | *"The surrogate effect is an artefact of which landscapes happened to be easy."* 0 of 10,000 sign-flip permutations as extreme, 4.6 SD. | — |
| **Q44** | D-efficiency and CCD conditioning | DEFENCE | *"The DoE arm loses because you gave it a bad design."* In its own region the CCD is ~4.4× more D-efficient than the adaptive design. It fails on good geometry. | — |
| **Q39** | Holm over the non-primary contrasts | DEFENCE | *"You ran 40+ comparisons and never corrected."* Corrected; costs the "LHS also beats BO" claim. | — |
| **Q48** | Static arms share one design across all 25 instances | DEFENCE | *"Your LHS baseline drew a lucky design and your intervals ignore design variance."* Conceded and measured: `lhs` sat at the 0th percentile of 60. | — |
| **Q50** | qLogEI design-averaged | DEFENCE | *"Then design-average BO too and the reversal disappears."* It does not: qLogEI moves −0.002 where `lhs` moves +0.048. | — |
| **Q22** | Benchmark additivity — 0.930 at d=6 | DEFENCE | *"Your oracle is near-separable, so it cannot speak to ECM interactions."* Measured, quantified, and stated as L1 rather than discovered by a reviewer. | — |
| **Q33** | Extrapolation geometry on the published data | DEFENCE | *"Your extrapolation finding is an artefact of a synthetic oracle."* It reproduces on the real digitized data: polynomial argmax runs to any wall, the GP's is bit-identical. | — |
| **Q37** | The replay is a power bound | DEFENCE | *"Your real-data replay found nothing, so BO does not work."* MDE 0.68 evaluations; stage 1's observed effect is smaller than its own MDE. The instrument had no resolution. | — |
| **Q31 + amendment** | The Hall/Ogle replay, null at both stages | DEFENCE | *"Does any of this hold on real data?"* Run, registered before the dataset existed, null — and read with Q37. | — |
| **Q38** | The cost model — rounds, not evaluations | DEFENCE | *"You counted evaluations; a lab pays for plate cycles."* DoE 3 rounds vs qLogEI 10 at equal evaluations. | — |
| **Q49** | The noise threshold — the identification gap | DEFENCE | *"The scoring rule is a technicality."* At σ=0.25, 61% of remaining regret is a recipe already run and not identified. The threshold is CV≈0.15. | — |
| **E1** | Correctness on standard functions | DEFENCE | *"Does your BO work at all?"* It beats random search — and it exposed the scoring bias that voided E2's first run. | — |
| **E3** | Calibration | DEFENCE | *"Is the GP's uncertainty trustworthy?"* No — coverage below nominal in every cell. Stated as L4. | — |
| **PF1** | The (κ,ρ) over-prediction surface; saddle in 800/800 | DEFENCE | *"Is the saddle finding an artefact of your DoE arm?"* 800/800 cells, zero maxima, before any DoE arm existed. | — |
| **PF2** | Hill inversion, closed-form δ_max, acceptance rate | DEFENCE | *"Is the oracle's mathematics right?"* Round-trips and matches brute force. | — |
| **Digitization ×2 + `pdf_crosscheck`** | Two independent extractions, merged; four-reader source audit | DEFENCE | *"You digitized from figures — how much error does that inject?"* Reading error 4–7% of between-condition spread against a published SEM of 38–66%. | — |
| **Task A** | Literature verification | DEFENCE | *"You have mischaracterised the prior art."* Verified against PDFs; found Nguyen is *not* contrary and surfaced Rummukainen 2024, the matched-budget head-to-head. | — |

---

## ARCHIVE

*Not a criticism. Several of these are better work than items above them.*

| ID | Title | Label | Objection closed | Superseded by |
|---|---|---|---|---|
| **E4** | Extrapolation detection — GP uncertainty vs nearest-neighbour distance | ARCHIVE | — | — |
| **E4 robustness** | Robustness checks on E4's headline | ARCHIVE | — | — |
| **E4 disagreement sweep** | Does model disagreement beat single-model uncertainty? | ARCHIVE | — | — |
| **Shape-aware GP mean** | Giving the GP the biology's known shape | ARCHIVE | — | — |
| **Q19** | E4's registered cell vs its pooled figure | ARCHIVE | — | — |
| **Q47** | The multi-fidelity threshold surface — 6,600 runs | ARCHIVE | — | — |
| **Q46** | Paper 2's registered derivation | ARCHIVE | — | — |
| **Q52 §1.1** | Identification error for a space-filling design, all four cells | ARCHIVE | — | — |
| **Q52 §1.2** | The curve does not flatten — regret still falling at 500 | ARCHIVE | — | — |
| **Q40** | Critical-difference diagrams | ARCHIVE | — | — |
| **Q32** | Merge of the two parallel digitization builds | ARCHIVE | — | — |
| **Q13 / Q14 / Q15 / Q16 / Q18 / Q23** | Build-phase registrations and policy calls | ARCHIVE | — | — |
| **`project_plan.md` Part E** | 🔵 **ARCHIVE-label QUALIFIED.** The file is build-phase scaffolding and stays archived, but **§E.1–E.5 is the live Phase 3 specification** — structure, what to ask the lab for, budget arithmetic, data format, limitations. The in-house lab drop started Phase 3 on 2026-08-13, so that section is active work, not history. `docs/LAB-DATA-FOR-BO.md` §9 points at it. | ARCHIVE (partial) | — | — |
| **PF3 / PF4** | BoTorch API signature checks; wall-clock timing | ARCHIVE | — | — |
| **PF-A / PF-B** | Sampler acceptance (0.15%→100%); E4's kill condition | ARCHIVE | — | — |
| **The qKG swap** | Knowledge Gradient, run to ~52 rows and abandoned | ARCHIVE | — | — |
| **`bench_surrogate`** | Standalone surrogate-accuracy bench, outside the registration | ARCHIVE | — | — |
| **`diagnostic_lengthscales`** | Fitted lengthscales against a no-signal null | ARCHIVE | — | — |
| **EXPLORATORY branch** | Quadratic mean / replication / input warping — unregistered mechanism search | ARCHIVE | — | — |
| **`plain-english/`** | Ten non-technical chapters, one per module | ARCHIVE | — | — |

**Why E4 is archived, since it is the largest single item here.** E4 asks whether a GP's
uncertainty beats plain nearest-neighbour distance at *flagging* extrapolation. That is a
different question from all three sentences, its headline is unresolved (Q19 — the registered
cell and the pooled figure disagree in sign, and nobody has chosen), and its write-up
`results/E4-RESULTS-v2.md` has no producing script, so it cannot be regenerated. It is real work
on a question this paper does not ask.

**Q47 is the second largest** — 6,600 runs, 11 MB, and the largest artefact in the repo. It
answers *"when does a cheap second assay pay?"*, which is forward-looking design advice. Its own
entry concedes the correlation is assumed rather than measured, "which is why this is a threshold
and not a result."

---

## VOID

*Every row names a reason **and** a superseding item.*

| ID | Title | Label | Objection closed | Superseded by |
|---|---|---|---|---|
| **E2 run 1** | Scored best *true* value among visited points — credits an arm for a recipe it cannot identify | VOID | — | **E2 (current run)**; the same error class recurred as D20 |
| **E2 run 2** | The paired opening batch did not exist; the test that promised it asserted determinism (D6) | VOID | — | **E2 (current run)** |
| **Q29** | The symmetric comparison — ran in B's clone against B's untracked grid, and the two arms used different locators at a 16× screening-budget difference | VOID | — | **Q34** (one locator, A's clone, all four cells) |
| **Q28's rule-A figures** | −0.0708 etc. — computed in B's clone, not this repository's numbers | VOID | — | **Q34 / the corrected table** (−0.0595 / +0.0018 / −0.0284 / −0.0024) |
| **Q36** | Generality at one cell on two families, without the noise-model fix | VOID | — | **Q42** (four families, four cells) |
| **Q25 version 1** | Anchored the decision rule on the prior *median* under a MAP fit — one branch unreachable (D8) | VOID | — | **Q25 version 2** (empirical permuted-outcome null) |
| **Q16's ρ-trend primary** | Nested boxes make over-prediction monotone in ρ by arithmetic — a registered primary that could not fail (D3) | VOID | — | **Q16's coverage primary**, itself amended to both point sets |
| **Q16's depth secondary** | Predicted over-prediction falls with true depth; measured +0.3893 and +0.1285 — positive | VOID | — | Nothing; reported as a failed prediction |
| **Q52 §2 first-pass headline** | "The savings ratio inverts, crossover at 0.15" — promoted the appendix, reported forbidden cells, read a survivorship decline as a trend, and was not significant (D19) | VOID | — | **The arrival-rate result** (σ=0.10, target 0.10: 24/25 vs 13/25, 11:0 discordant, p=0.0010) |
| **Q52 §1.1 as an oracle-search floor** | Registered as a universal lower bound; rule A's cost on a mis-pick depends on the runners-up, so the bound needs *bad* ones | VOID | — | **Q52 §1.2**, which refuted it the same afternoon; reinterpreted as the *static* arms' identification penalty |
| **Ackley, under every rule** | Its optimum is the exact centre of the coded box and every screening/CCD design includes centre runs, so the design contains the answer | VOID | — | Nothing; reported only as the degenerate case that identifies the mechanism's precondition |
| **Q47's "joint is a clean upper bound"** | Pseudo-observation variance measured 2–20× the true value (D13), biasing against the arm it was meant to bound | VOID | — | Withdrawn in place; stated as a limitation |

---

## What is deliberately NOT triaged away

Per the brief, and because each is load-bearing for how the rest is read:

- **The defect register — D1–D20.** `RESULTS.md` PART 8 and `RESULTS-PERSON-A.md` §7.
- **Every wrong registered prediction.** `RESULTS.md` PART 10.
- **Superseded numbers that carry their superseded marking.** The marking is the record.
- **Every raw result file.** `results/` is untouched by this triage except for four exploratory
  logs, moved into `docs/archive/exploratory/results/` so they become tracked rather than lost.

---

## Dependency flags — CORE resting on ARCHIVE, VOID, or nothing at all

These are the findings of the exercise and are carried into `MAIN-LINE.md`.

| # | CORE item | Rests on | Severity |
|---|---|---|---|
| **1** | ~~**Q27** — sentence 1 at d=8~~ | 🔵 **REFUTED — withdrawn.** I wrote that `results/e2-doe-d8.json` does not exist. **It does**, and always did: `run_e2_doe_d8.py:257` wrote it, `results/*` ignored it, and nobody force-added it. It holds both d=8 cells, 50 rows each, 18 fields, and regenerates the log text exactly (0.0948 at σ=0.10, 0.0963 at σ=0.25). **The Q27 primary contrast IS re-aggregatable and re-scorable.** My flag repeated D17's own wording without checking the disk — the same mistake D17 records, one level up. | ✅ |
| **2** | **Sentence 2 as stated** | True under Q41's primary (unconstrained). Under the constrained variant it is **three nulls and one BO win of +0.0153**. Both must appear; "in every cell tested" needs the rule named in the same sentence. | 🔴 |
| **3** | **Sentence 3's second half** | Q35's residual — *"even constrained, the recommendation is worse than the arm's own best measurement"* — is **null at both σ=0.10 cells** after the D20 rescore. The asymmetry is a property of the noisy assay, not a general one. | 🔴 |
| **4** | **`CLAIMS.md` L19 "ESTABLISHED"** | Rests on **Q50, which has no entry in `RESULTS.md`**, while `RESULTS.md:958` still says the settling run is "Not run". The two governing documents contradict each other. | 🔴 |
| **5** | **The positioning section (T1.3)** | Cites Picheny for the infill/identification distinction, which Task A records as **NOT verified — "do not cite it for that distinction yet"**; treats Nguyen 2017 as a contrary result, which Task A **refuted**; attributes to Gisperg a no-reduction finding that is **Rummukainen's**; and omits Rummukainen 2024, which the record calls "the most important citation found". | 🔴 |
| **6** | **`CLAIMS.md` 1.1, 2.2, 3.1** | Anchor to `results/E4-RESULTS-v2.md` — an **ARCHIVE** item, with **no producing script**, whose headline is unresolved under Q19. | 🟠 |
| **7** | **`CLAIMS.md` 3.2** | Anchors to `results/NEGATIVE-shape-aware-mean.md` — **no producing script anywhere in the repo**. It cannot be regenerated. | 🟠 |
| **8** | **`docs/METHODS.md`** | Anchors to **zero** artefacts. `grep -c 'results/'` returns 0 across 606 lines. | 🟠 |
