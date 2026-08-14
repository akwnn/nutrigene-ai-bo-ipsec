# CLAIMS — what the evidence supports, and what it does not

**STATUS: DRAFT PROPOSAL by B, for A and Alan to cut. Nothing here is settled.**

> ## 🔵 TRIAGED — every claim below now traces to a labelled item in `docs/TRIAGE.md`
>
> **42 claims before, 34 after.**
>
> | | before | after | struck |
> |---|---|---|---|
> | Tier claims (1.x / 2.x / 3.x) | 13 | **9** | 2.2, 3.1, 3.2, 3.5 — all E4 |
> | Limitations (L1–L19) | 19 | **18** | L18, a duplicate of L13 |
> | Blocking decisions | 5 | **2** | Q28/T16 and Q30 (already decided), Q19 (no longer blocks) |
> | "What we do NOT claim" | 5 | **5** | — |
> | **total** | **42** | **34** | **8** |
>
> Two further claims were **demoted** rather than removed (1.1, 1.5). Nothing was deleted: every
> struck item stays in place with its reason, per this project's own rule.
>
> **Read `docs/MAIN-LINE.md` first.** It is CORE and DEFENCE only, and it is the paper's skeleton.
>
> **Four corrections below change published numbers**, all traced: the acquisition-failure rate
> (0.875% → 0.118%, three places), Ackley's rule A (0.0000 → 0.0123, D20), L8's generality
> figure (Q36's +1.0032 → Q42's +0.2460), and 1.3/3.6's asymmetry, which is now σ-conditional.

This exists because the results are in, the logs disagree with each other, and whoever
writes first from whichever log they happen to open will set the paper's claim by
accident. Three known contradictions between artefacts:

- ~~`results/e2.log` prints the primary-cell difference as **−0.0595**; the grid that
  same run persisted gives **−0.0708** (Q29). Three computations agree against the log.~~
  **RESOLVED (T1.4): the log is right and the three computations were one computation.**
  `results/e2-grid.json` was gitignored, so A's clone and B's clone held two different
  E2 runs under one filename. All three "independent" recomputations ran in B's clone
  against B's copy. The committed grid gives **−0.0595** under every aggregation, and
  `run_e2.py`'s `report()` was never wrong. See the resolved Q29 entry and
  `tests/test_e2_provenance.py`.
- `results/E4-RESULTS-v2.md` labels the **pooled** figure "pre-registered primary";
  the pre-registration names a **single cell**, and the two disagree in sign (Q19).
- E2's headline reverses depending on a scoring rule the pre-registration never
  fixed (Q28, Q29).

**Rules for this document.** Every claim carries its evidence and its file. Contested
estimands are listed as contested, with **both** numbers — they are not resolved here,
because the people who have seen both numbers should not be the ones to choose.
Decisions belong in `OPEN-QUESTIONS.md`; this file only states what follows from them.

---

## Positioning — the contribution, and the prior art that bounds it (T1.3)

**The reporting-rule question is not new to Bayesian optimization, and the paper cannot be written as though it is.** Presented as a discovery it is a desk-reject on novelty. Presented as an explanation of an existing disagreement it is defensible, checkable, and — as far as we can find — unmade.

### Prior art that must be engaged, not cited in passing

| source | what it establishes | what we must do |
|---|---|---|
| **Rummukainen et al. 2024**, *Heliyon* 10(2):e24484 | 🔴 **THE CLOSEST PRIOR WORK IN EXISTENCE, and it was missing from this table.** A matched-budget DoE-vs-BO head-to-head, 15 experiments each, **scored on the best condition MEASURED (rule A)**, with the criterion **not fixed in advance** — and BO did not reduce the experiment count. Its winner *"had already been found during the first initialization experiment"*, which is our Q37 finding on real data. | **Cite it in the abstract's framing, not in related work.** Our contribution is not that the split exists but that the split is attributable to the classical arm's unregistered scoring — and Rummukainen is the case where that is visible in print. Verified from the PDF (Task A). |
| ~~**Picheny, Wagner & Ginsbourger 2013**, *Struct Multidiscip Optim* 48:607~~ | ~~It explicitly separates the **infill** criterion from the **identification** criterion. **That distinction is exactly rule A versus rule C.**~~ | 🔴 **STRUCK — the distinction is NOT VERIFIED.** Task A: *"both OA mirrors blocked. **Do not cite it for that distinction yet.**"* What **is** verified is narrower and still useful: Picheny compares **ten kriging-based** criteria and **no non-kriging method**, which is the gap this project fills. Cite it for that, and only that, until someone reads the paper. |
| **Bull 2011; Wang & de Freitas 2014; Berk 2019** | The incumbent choice — best observation, best posterior mean, best sampled posterior mean — is an active theory thread for GP-EI. | Cite the lineage, in the **introduction**, not in related work. ⚠️ **All three are NOT verified** (Task A). Read them or drop them; do not ship the characterisation. |
| ~~**Nguyen et al. 2017**~~ | ~~Reports empirically that **best-observed beats the GP-mean counterpart** — **the opposite sign to our rule-C result.**~~ | 🔴 **STRUCK — REFUTED AS CHARACTERISED (Task A, verified from the PDF).** Nguyen concerns the incumbent ξ *inside* the EI acquisition function — an **infill** choice — not the final recommendation. *"The words 'recommend' and 'report' do not occur."* **It is not a contrary result, and citing it as one would be a serious misreading.** The instruction to "engage directly" is withdrawn. |
| **Gisperg et al.**, *Biotechnol Bioeng* review | BO gave a more precise model near the optimum, but the number of experiments could not be reduced compared with DoE. ⚠️ **Attribution corrected (Task A): the no-reduction result is Rummukainen's, not Gisperg's.** The review reports it; it did not produce it. | Cite as convergent prior art **and cite Rummukainen for the finding itself**. Task A also verified that the review identifies **no gap** in how the final condition is scored — so the contribution is not pre-empted. |
| **Narayanan et al. 2025**, *Nat Commun* | Claims 3–30× fewer experiments than DoE. | Cite as the opposing camp, and note the comparison is against **estimated** design sizes from formulas rather than an executed DoE arm. That is precisely the gap this project fills. |
| **Hoerl 1959; Draper 1963; Box & Draper; Myers & Montgomery** | Ridge analysis, canonical analysis and lack-of-fit testing already handle a stationary point outside the design region. | Already conceded in `project_record.md` §B.1.1 and now **measured** in Q35. The failure is one of practice, not of the DoE toolbox. |

### The reframed contribution

> **The DoE-versus-BO literature is split — one camp reports 3–30× fewer experiments, a 2025 review reports no reduction at all — and the split is substantially attributable to an unregistered scoring convention on the *classical* arm.**

**Measured, at the registered primary cell (d=6, σ=0.25), all on one machine with one locator:**

| arm | rule A (best observed) | rule C (its model's recommendation) | swing |
|---|---|---|---|
| DoE | 0.0958 | 0.4163 | **+0.3205** |
| BO | 0.1553 | 0.1232 | −0.0321 |

**≈10:1.** The verdict moves from "DoE better by 0.0595" to "BO better by 0.2931" — a swing of 0.3526 — and **91% of it comes from how the DoE arm is scored, not from anything about BO.**

And Q35 measures the sensitivity: scored the way classical practice *also* prescribes (constrained to the region explored), the DoE arm's rule-C figure is **0.1169** against BO's 0.1232 — the gap narrows to a null at three of four cells.

> **🔵 CORRECTED (triage).** This read: ~~"**The reversal disappears.** 'BO wins under rule C' was an artefact of scoring the classical arm in a way its own literature warns against."~~ That reports the **sensitivity** as though it were the result. **Q41 designates the unconstrained argmax as primary**, under which BO wins rule C at every cell by **+0.2710 to +0.3597**. The honest sentence carries both: *the rule-C gap is +0.27 to +0.36 at the primary scoring and collapses to three nulls under the constrained sensitivity — and that spread, larger than the BO-versus-DoE gap it modifies, is itself the finding.*

### What this contribution is NOT

- **Not "BO loses".** ~~Q36~~ **Q42** tested that on four standard families and it does not generalise — BO wins everything on Hartmann6, at all four cells under every rule. Which method wins is a property of the landscape. *(Q36 is superseded — it ran two families at one cell without the noise-model fix.)*
- **Not a new estimator, criterion or algorithm.** Nothing here is a method contribution.
- **Not a claim that anyone acted in bad faith.** The convention is unregistered in both camps; that is the point. An unregistered convention with a 10:1 leverage on the verdict is a field-level measurement problem, not a fault of either paper.

### Delete on sight

`project_record.md` §B.1.2 states of the efficiency claim: *"nothing in the prior-art critique touches it."* **That sentence is now triply false** — replay benchmarking of BO against published datasets is an established genre with purpose-built frameworks; the no-reduction result is in print (Rummukainen 2024, reported by Gisperg); and **Rummukainen is a matched-budget DoE-vs-BO head-to-head scored on rule A with the criterion not fixed in advance**, which is the prior-art critique landing directly on the claim. It is the most exposed claim in the record and must go.

> ⚠️ **`project_record.md` IS NOT IN THIS REPOSITORY** — and never has been, at any commit
> (`git log --all --diff-filter=D` finds no deletion). It is cited here twice, and also by
> `pdf_crosscheck.md`, `RESULTS-PERSON-A.md` and `OPEN-QUESTIONS.md`. **The two sentences quoted
> from it above cannot be checked by anyone reading this repository**, and one of them is the
> target of a "delete on sight" instruction. Either commit the file or restate both passages from
> a source that exists. *(Triage — dangling-reference audit.)*

---

## Tier 1 — established, robust, and the strongest thing the project has

These survived every check run against them, reproduce across independent
implementations, and do not depend on any contested choice.

**1.1 The published-style two-stage DoE workflow over-promises systematically and
massively.** Running the published procedure over the *full* space, hiding nothing, the
predicted optimum fell outside the region stage 2 explored in **100%** of runs and
under-delivered against the arm's own best measured point in **100%**, at both noise levels
(`doe-arm.log`).

> **🔵 DEMOTED (triage). The E4 half of this claim is withdrawn from Tier 1.** It read:
> ~~"pooled over-prediction **+1.103 [+1.024, +1.182]** against a response whose maximum is
> **1.0**, in **100/100** cells (`E4-RESULTS-v2.md`)."~~ Three independent reasons:
> **(i)** that pooled figure is the exact quantity **Q19 disputes** — `E4-RESULTS-v2.md` labels it
> "pre-registered primary" and the pre-registration names a single cell, and the two disagree in
> sign. A contested number cannot sit in a tier defined as *"survived every check, does not depend
> on any contested choice."*
> **(ii)** `E4-RESULTS-v2.md` has **no producing script** — `run_e4.py` declares only
> `E4-FIRST-RESULTS.md`. It cannot be regenerated.
> **(iii)** E4 is labelled ARCHIVE in `TRIAGE.md`: it asks whether GP uncertainty beats
> nearest-neighbour distance at *flagging* extrapolation, which is not a question this paper asks.
>
> **What survives is the `doe-arm.log` sentence above, and it is enough** — it is the same
> phenomenon measured on the arm the paper actually runs, at 100% in both cells, from a committed
> log with a named script.

**1.2 The failure is extrapolation, not a constrained-optimiser artefact.** The
predicted optimum sat *on* the stage-2 boundary in **0%** of runs — so it is genuine
extrapolation, and separable from the boundary-clamping mechanism identified in the
source paper (`doe-arm.log`, Q15).

**1.3 The DoE pipeline's own recommendation is its weakest product.** Scored at the
recipe each method recommends, the DoE arm carries **0.37–0.44 regret** against a
ceiling of 1.0, versus **0.09** for the best recipe it happened to measure — in all four
cells (~~`q29-symmetric-allcells.log`~~ — **superseded; that log is B's clone under the
old locator. Current source: `q35-constrained-rsm.log`, which gives 0.3766–0.4300 across
the four cells, and `q34-factorial.json`**). **Scored the way classical practice prescribes
the same recommendation carries only 0.086–0.117 (Q35), so this row is a statement about
the UNCONSTRAINED scoring — which is Q41's primary — and must name it.** **The figure barely
moves with dimension (6→8) or
with a 2.5× change in measurement noise**, which means it is driven by geometry rather
than by measurement error. This is 1.1 arriving independently, in regret units.

> **🔵 TWO AMENDMENTS (D20 rescore).**
> **(i) The comparison number is corrected.** "0.09 for the best recipe it happened to measure" is
> **0.0958**, not 0.0597 — the old figure was `curve_true`, i.e. oracle-best rather than rule A.
> The corrected value now agrees with E2's independently computed **0.0957**, resolving a
> discrepancy the two documents had carried for the life of the project. The claim is unaffected:
> 0.3766–0.4300 against 0.0958 is still the arm's own recommendation being its weakest product.
> **(ii) The constrained residual is σ-conditional** — see the amendment under **3.6**. The
> sentence pairing this row with 3.6 ("the two arms fail in opposite directions") holds at
> σ=0.25 and is **null at both σ=0.10 cells**.

**1.4 The fitted surface is a saddle ~~essentially always~~ WHENEVER THE RESPONSE IS
BIPHASIC — and the exception identifies the mechanism.** 800/800 PF1 cells, 100/100 E4
cells, 20/20 DoE-arm runs, 200/200 Q35 runs — zero maxima, zero minima (`pf1-grid.log`,
Q16, Q35). The spec predicted a mix and specifically predicted minima at tight settings;
it was comprehensively wrong.

> **⚠️ CORRECTED (Q42). "Essentially always" is FALSE as a general claim about fitted
> quadratics.** Across 350 runs on four standard test families the stationary point is a
> saddle in **247** and a genuine **maximum in 103**, and the maxima are concentrated in
> **Ackley** — a broad bowl with fine oscillations, which is exactly the shape a
> second-order model *can* represent. **The correct statement is conditional:** where the
> fitted Hessian is indefinite the unconstrained argmax must reach a boundary and the
> scoring convention dominates everything; where it is negative-definite the scoring
> choice is worth **exactly nothing** — Ackley's unconstrained and constrained figures are
> identical to four decimals. That conditional is stronger than the unconditional version,
> because it names the precondition and the precondition is testable on any real fit.

**1.5 The source paper's own reported optimum was extrapolated.** Reconstruction from
the published figure puts Collagen IV at coded **+1.40** — 20% above the highest
concentration ever tested (`pdf_crosscheck.md`). Flagged as **our inference**, not the
authors' statement, and needing a statistician to re-derive before it carries weight.

> **🔵 DEMOTED (triage) — out of Tier 1, into the defence.** Tier 1 is defined as *"established,
> robust, does not depend on any contested choice."* This row is explicitly an **unverified
> inference about a third party's analysis**, by its own last sentence. It belongs beside
> `pdf_crosscheck.md` as source-reading evidence (DEFENCE), not among the project's established
> results. Keep the number; move the claim.

---

## Tier 2 — established but CONTESTED, because the estimand was never fixed

**Both of these are real measurements. Neither has an agreed headline.**

**2.1 Whether BO beats current practice depends on the scoring convention, and nothing
else.** Same runs, same seeds, same data:

| cell | rule A — best observed *(registered)* | rule C — DoE **unconstrained** *(as Q29 scored it)* | rule C — DoE **constrained** *(as practice prescribes)* |
|---|---|---|---|
| **d=6 σ=0.25** | **−0.0595** DoE better | +0.2931 BO better | **−0.0063 NULL** (p=0.56) |
| d=6 σ=0.10 | +0.0018 null | +0.3597 BO better | **+0.0153** BO better (p=0.0088) |
| d=8 σ=0.25 | −0.0321 DoE better | +0.2710 BO better | **+0.0091 NULL** (p=0.20) |
| d=8 σ=0.10 | +0.0015 null | +0.3228 BO better | **+0.0001 NULL** (p=0.79) |

> ## 🔴 THE FRAMING BELOW READS THE WRONG VARIANT AS PRIMARY — corrected in triage
>
> Everything from "The contested estimand is no longer contested" onward treats the
> **constrained** argmax as the scoring that settles the question, and concludes that
> *"BO wins under rule C" was an artefact*. **Q41 decided the opposite**, and it is this
> project's single most binding decision:
>
> > *"**Decision: the unconstrained argmax is the primary DoE scoring.** Constrained argmax and
> > best-observed are reported alongside it, in every table, always."* — Q41,
> > `OPEN-QUESTIONS.md:2971`, decided by A
>
> Under the primary scoring, **BO wins rule C at all four cells by +0.2710 to +0.3597.** That is
> not an artefact; it is the registered result. The constrained variant is a **declared
> sensitivity** — and the largest one in the paper, which is why Q41 puts it in main text — but it
> does not demote the primary.
>
> **Both readings are legitimate and Q41 requires both to be printed.** What is not legitimate is
> the paragraph below, which reports only the sensitivity and calls the primary an error. Q41 was
> decided on grounds independent of these numbers (fidelity to the source study's "prediction
> solution" wording; that a saddle has no interior maximum, so the constrained value reports
> *where the search stopped* rather than *where the model pointed*).
>
> **Every claim conditioned on a scoring rule must name that rule in the same sentence** — Q41's
> own reporting rule. The text below does not.

> **✅ RESOLVED (T1.1 / T1.2 / T1.4c). Every figure is now from A's clone, on one machine,
> with one locator (`constrained_argmax`, `n_restarts=20, raw_samples=4096, seed=seed`,
> asserted over the AST). Sources: `q34-factorial.log`, `q35-constrained-rsm.log`. The two
> scripts agree on their shared cell to max |Δ| = 0.0e+00.**
>
> **The contested estimand is no longer contested in the way this section assumed.** Q29
> reported BO ahead under rule C by +0.29 to +0.36 at every cell, which made the E2
> verdict look purely convention-dependent. **That gap was almost entirely an artefact of
> scoring the classical arm at an unconstrained argmax** — a practice its own literature
> (Box & Draper; ridge analysis) warns against, and which produces a boundary point
> because the fitted surface is a saddle in 200/200 runs (Q35).
>
> Scored as classical practice prescribes, rule C gives **three nulls and one BO win of
> +0.0153**. The swing decomposition makes the same point directly: moving from rule A to
> rule C moves the **DoE** arm by +0.28 to +0.34 and the **BO** arm by only −0.01 to −0.03
> — a ratio of **10:1 at the primary cell, up to 33:1**, i.e. **91–97% of the verdict swing
> is the classical arm's scoring**.
>
> **So the correct statement is not "the verdict depends on the convention" but
> "the apparent dependence was one arm being scored badly."** Under both rules, scored
> competently, the two methods are close — DoE ahead on best-observed at d=6, and
> statistically indistinguishable on recommendation at three of four cells.

**~~2.2 The GP's uncertainty versus plain distance is κ-dependent and reverses sign.~~**
~~Pooled −0.0269 [−0.0728, +0.0182], "no advantage". By κ: **+0.1068** [+0.0461, +0.1668]
at κ=0.6 (GP better, and **above the pre-registered 0.08 equivalence bound**), −0.0173
at 0.7, **−0.0960** and **−0.1011** at 0.8 and 0.9 (GP worse, intervals clear of zero).
The pre-registration names κ=0.6 as the primary cell; the results document reports the
pooled figure under that name.~~ **Blocked on Q19.**

> **🔵 DROPPED (triage) — rests on an ARCHIVE item and has no objection to close.** E4 asks
> whether a GP's uncertainty beats plain nearest-neighbour distance at *flagging* extrapolation.
> No sentence of this paper's result depends on that, so under the triage rule the claim is either
> promoted to DEFENCE with its objection named, or dropped. **There is no objection to name** — a
> reviewer of a DoE-versus-BO scoring paper does not ask it.
>
> Three further reasons it could not have stayed as written: its headline is **unresolved**
> (Q19 — the registered cell and the pooled figure disagree in sign, and the decision was
> explicitly deferred: *"B is deliberately not choosing"*, and no A resolution exists anywhere in
> the record); its source `E4-RESULTS-v2.md` has **no producing script**; and a claim marked
> "Blocked on Q19" has been blocked for the entire life of the document.
>
> **The measurement is real and is not lost.** It stays here struck, and E4 is labelled ARCHIVE
> in `TRIAGE.md` with its files intact. If Paper 2 asks the extrapolation-flagging question, this
> is where it starts.

---

## Tier 3 — negative results, and they are load-bearing

Reported as findings, not as failures. Several are stronger than a positive would have been.

**~~3.1 A GP's uncertainty does not beat plain nearest-neighbour distance at flagging
extrapolation.~~** ~~Bounded, not merely unrefuted: any advantage is below 0.08. Prior art
says this was the expected outcome under GP theory (`E4-RESULTS-v2.md`).~~

> **🔵 DROPPED (triage)** — same reason as 2.2, of which this is the pooled summary. It also
> **contradicts 2.2 on its own evidence**: 2.2 records +0.1068 at the registered primary cell,
> which is *above* the 0.08 bound this row says nothing exceeds. The two cannot both be reported.
> Archived with E4, not deleted.

**~~3.2 Giving the GP the biology's known shape made extrapolation worse~~**, ~~not better
(`NEGATIVE-shape-aware-mean.md`).~~

> **🔵 DROPPED (triage) — and it is the least recoverable item in the file.**
> `results/NEGATIVE-shape-aware-mean.md` is a **hand-authored narrative with no producing script
> anywhere in the repo** — not in `scripts/`, not in `src/`, not in `tests/`. Its underlying log
> `results/e4-shape-mean-negative.log` has no producer either. **This claim cannot be regenerated,
> re-scored, or checked**, which fails rule 1 of `RESULTS.md` in substance if not in letter.
> It is also an E4-lane result, so it fails the ARCHIVE test independently.
>
> If it is ever wanted, it must be **re-run from a committed script**, not quoted from the file.

**3.3 Surrogate accuracy is not the binding constraint on BO's regret here.** The
additive kernel made the model roughly twice as accurate — held-out R² **0.375 → 0.744**,
factor identification **0.853 → 0.965** — and regret did not move (−0.0015, p=0.711).
**"BO is losing because the model is bad, so improve the model" is refuted by direct
test with a measurably better model** (Q30).

**3.4 Four candidate explanations for BO's performance are eliminated by direct test:**
the prior (Q25), the acquisition solver (Q21, max failure rate ~~0.875%~~ **0.250%**, overall
**4/3400 = 0.118%**, against a pre-registered 1% threshold), the opening batch size (Q26,
partial at low noise only), and the model class (Q30). The surviving candidate is the
scoring rule (2.1).

> **🔵 CORRECTED (triage).** 0.875% is **B's run on B's machine** — L6 records this and
> corrects it, but the correction never reached this row or the Appendix. The rate for the run
> that produced the committed grid, and therefore every number in the paper, is **0.118% overall
> and 0.250% worst-cell**, and the failures do **not** concentrate at high noise. Q21's verdict is
> unchanged either way; the "close to the line" reading is not available at 0.250%.

**~~3.5 Separability does not explain the κ sign flip.~~** ~~Additive-fit R² inside each κ's
training sub-box is flat — 0.9645 to 0.9670, a range of 0.0025 — while the
discrimination difference swings 0.21 and changes sign. B's own proposed mechanism,
tested and refuted (Q22).~~ **The 93% figure must not be cited as though it explained
this.**

> **🔵 DROPPED (triage) — it explains a result that is no longer claimed.** The κ sign flip is
> 2.2's, and 2.2 is dropped. A refutation of a mechanism for an archived finding has nothing left
> to close.
>
> **One sentence must survive elsewhere, and it is the useful half:** the ~93% additivity figure
> (L1) explains nothing about E4, and must never be cited as though it did. That prohibition is
> now carried by **L1**, where the 93% figure actually lives. The refutation itself — flat 0.0025
> against a 0.21 swing — is a genuinely good null and is archived with Q22's entry, not deleted.

**3.6 BO's recommendation beats its own best observation in all four cells** (15–21%
better — 0.1232 vs 0.1553, 0.0703 vs 0.0874, 0.1056 vs 0.1247, 0.0876 vs 0.0972). The
posterior mean smooths noise, so the model's named recipe is a better bet than the
luckiest single reading.

> **🔴 AMENDED (D20 rescore) — the "opposite directions" sentence is now σ-conditional.**
> It read: ~~"Combined with 1.3: **the two arms fail in opposite directions — the polynomial's
> model is worse than its data, the GP's model is better than its data.**"~~
>
> **The GP half is unaffected** — BO's numbers were always scored on `reported_best_curve` and
> could not move. **The polynomial half held only because its own data was scored at
> oracle-best.** Rescored on rule A (`results/d20-rescore.json`, fidelity gate |Δ| = 0.0 over all
> 200 rows), the constrained recommendation is worse than the arm's own best measurement at the
> **noisy** cells and **not** at the quiet ones:
>
> | cell | as published | corrected |
> |---|---|---|
> | d=6 σ=0.25 | +0.0572 | **+0.0211** [+0.0105, +0.0315] |
> | d=6 σ=0.10 | +0.0312 | **−0.0036** [−0.0122, +0.0049] **NULL** |
> | d=8 σ=0.25 | +0.0573 | **+0.0185** [+0.0094, +0.0287] |
> | d=8 σ=0.10 | +0.0377 | **−0.0071** [−0.0150, +0.0008] **NULL** |
>
> **The correct statement:** *at a realistic assay the two arms fail in opposite directions; at an
> optimistic one the polynomial's model is no worse than its data either.* **The asymmetry is a
> property of the noisy assay, not a general property of the two model classes**, and it survives
> at the realistic cells at about a third of its published magnitude. Write it that way.
>
> Note this residual is **not** `CLAIMS.md`'s L6, which is about acquisition-solver failures.
> Q41 requires it to appear adjacent to the constrained number wherever that number is reported —
> so the σ-conditioning travels with it.

---

## Limitations — mandatory, and none of these are optional

**L1 The benchmark is ~93% additive.** Variance explained by a purely additive fit:
**0.930** at d=6, **0.927** at d=8 (Q22). The motivating study is *about* ECM protein
interactions, so the benchmark under-represents the phenomenon the paper exists to
study. **Every conclusion here is a conclusion about near-separable landscapes.**

> **The 93% figure must not be cited as though it explained anything else.** It was proposed as
> the mechanism for E4's κ sign flip and **tested and refuted**: additive-fit R² inside each κ's
> training sub-box is flat — 0.9645 to 0.9670, a range of **0.0025** — while the discrimination
> difference swings **0.21** and changes sign (Q22). *(Prohibition inherited from the dropped 3.5,
> so it survives where the figure lives.)*
>
> ⚠️ **This limitation is also partly answered, and the answer belongs beside it:** Q42 reproduced
> the reversal on **Levy and Rosenbrock**, which are non-additive and multimodal. The
> near-separability objection to *the scoring-convention finding* is closed by data (L8); what
> stays open is whether the **DoE-beats-BO** verdict transfers, and it does not — see L8.

**L2 One oracle family**, d ∈ {6, 8}, 25 instances × 2 seeds. Whether any of this holds
on landscapes with different structure is untested.

**L3 Two arms are unpaired** — `lhs` by registered exemption, `coord` because it starts
from a random interior point (Q18, Q23). Wider intervals for those comparisons, not bias. ⚠️ **Not the whole story — see L19.** A shared design across instances is a
separate defect from unpairing across arms, and that one does bias the estimate.

**L4 Prediction-interval coverage is never nominal anywhere on the grid** — highest cell
**0.625** against a nominal 0.95, including at ρ=1.2 (Q16). And coverage at the model's
own argmax differs from domain-wide coverage, giving opposite verdicts on the same
registered sentence.

**L5 Over-prediction is measured at an argmax whose location is poorly determined.**
T7 found value converges while location does not — BO reaches 0.90–0.95 of a ceiling of
1.0 while sitting 0.35–0.74 away from the true optimum in six dimensions.

**L6 Acquisition-solver failures.** ~~9 second-try failures, concentrated entirely in the
two σ=0.25 cells, peaking at **0.875%** at d=8 σ=0.25.~~ **Corrected (T1.4b): those are
B's run on B's machine.** For the run that produced the committed grid — and therefore
every number in the paper — the rate is **4 failures in 3400 acquisition calls (0.118%)**,
worst cell **0.250%** at d=8 σ=0.25, and they do **not** concentrate at high noise (one
falls in d=8 σ=0.10). Below the pre-registered 1% threshold either way, so Q21's verdict
is unchanged; but the "close to the line" caveat belongs to B's run, not to the result.

**L7 The adaptive arms are not reproducible across machines.** `qlogei` and `qlognei`
regenerate **bit-exactly within a machine** (400/400 rows, max |Δ| = 0.000e+00, T1.4b)
and disagree across two: A's primary-cell qLogEI mean is 0.1553, B's 0.1641. Every other
arm — `random`, `sobol`, `lhs`, `coord`, `doe` — reproduces on both. The arms that
diverge are exactly those calling `optimize_acqf`, i.e. those depending on BLAS reduction
order in the GP fit and on the L-BFGS-B path. **A published BO regret figure is a
machine-specific quantity at this precision**, and the effect (0.009) is a sixth of the
headline (0.0595). Sharding is *not* the cause: a sequential single-process run
reproduces the four-shard grid exactly.

**L8 The E2 verdict is specific to this landscape family (~~Q36~~ **Q42**).** On Hartmann6 —
non-additive, deceptive — **BO wins under every rule, at all four cells**
(**+0.2460 / +0.3460 / +0.3189 / +0.4134**, all p<0.0001). On Ackley the comparison is **void**
under every rule, because its optimum is the box centre (L16). On **Levy and Rosenbrock the
reversal reproduces at all eight cells**. Four families, three answers. **"Current practice beats
BO" is a result about near-separable, coordinate-wise-unimodal landscapes calibrated to
one published dataset, and must be written that way.** What does generalise is the
scoring-convention effect — **+0.22 to +0.48 on every family and cell where the surface is a
saddle, always larger than the rule-C gap it modifies.**

> **🔵 CORRECTED (triage).** This row cited **Q36, which is VOID** — superseded by Q42, which ran
> four families at four cells with the noise-model fix where Q36 ran two families at one cell
> without it. The struck **+1.0032** is Q36's number and must not be quoted; Q42's Hartmann6
> figure at the matched cell is **+0.2460**. Two substantive changes come with it: Ackley is
> **void under every rule**, not merely "both methods fail and DoE fails less" (Q36 voided only
> its rule A, which Q42 found insufficient — the constrained and unconstrained rule-C figures are
> identical to four decimals, so rule C carries no information there either); and the generality
> claim is **stronger**, not weaker, because Levy and Rosenbrock reproduce the reversal cleanly at
> every one of their eight cells.

**L9 The DoE arm fits a SECOND-order surface; the source used "significant terms up to
the 3rd order", stepwise-reduced.** The choice is forced by estimability, not preference:
a full third-order model is **84 terms at d=6 and 165 at d=8** against n=48, so it is
rank-deficient before any data is seen. The source's *stepwise reduction* is precisely
what made their form feasible, and we do not reproduce that selection step. **So the arm
is not a replica of the published analysis**, and the gap runs in an unknown direction —
a reduced cubic can bend where a full quadratic cannot, but stepwise selection also
inflates its own intervals. Stated, not resolved.

**L10 No steepest-ascent phase.** Classical sequential RSM is screen → **steepest
ascent** → CCD → confirm, and the ascent phase is what moves the design region toward the
optimum. Our pipeline omits it. **So did the source study**, which instead doubled the
range on retained factors between stages — a cruder form of the same move. The omission
therefore preserves fidelity to the case study while making the DoE arm weaker than
textbook practice. Both facts belong in the same sentence.

> **Extended by Q52 §2, and it bites harder there.** The budget-to-target grid gives the
> classical arm budgets above 48 by **repeating the whole 48-run pipeline with a fresh
> seed and keeping the best**. That arm therefore **never moves its design region at all**
> — it re-screens from scratch each time rather than walking toward the optimum. Steepest
> ascent would very likely improve it, and a reviewer will say so. **So every savings
> ratio in Q52 §2 is biased in BO's favour, and the budget-to-target curve understates
> DoE.** Registered as a limitation before the run rather than conceded after it. The
> honest form of any efficiency claim from that grid carries this sentence with it.

**L11 Digitized rather than author-supplied data**, and the comparison that makes it
defensible: optical **reading error is 4–7% of the between-condition spread**, against a
published **per-condition SEM of 38–66%** of that same spread. The source assay is the
binding constraint by roughly an order of magnitude. **This runs opposite to the
intuition** that digitization is the weak link, and should be stated with both numbers
rather than as reassurance.

**L12 No wet-lab validation. This belongs in the ABSTRACT, not only here.** Nothing in
this project has been run on cells. **And the title must change**: "stem-cell
differentiation protocols" promises cells. Something closer to *"a benchmark study on
landscapes calibrated to a published endothelial differentiation dataset"* is accurate.

**L13 No published endothelial dataset with continuous factors and deposited
per-condition data exists.** This is why a synthetic benchmark was necessary at all. It
is worth stating as **a finding about the field** rather than an apology for the method:
the one usable study had to be recovered by digitizing two figure panels, and the closest
alternative (Hou 2017) is a presence/absence design with no dose axis.

**L14 Cost is reported in evaluations, and evaluations are not what a lab pays (Q38).**
At the primary cell the DoE pipeline needs **3 sequential rounds** and qLogEI needs
**10**; Latin hypercube reaches lower regret than qLogEI in **one**. ⚠️ **That LHS number is the best of 60 design draws — see L19**; the round-count comparison stands, the regret comparison inside it does not. A fixed-evaluation
comparison silently grants BO seven extra plate cycles. A regret-versus-rounds *curve*
cannot be drawn from the committed grid — E2 persisted summary rows, not curves — so only
the endpoint and the exact round count are available. Nor is q=4 defended as the right
batch width; a larger q would trade rounds against regret and that experiment has not
been run.

**L15 Multiplicity was never controlled, and correcting it costs one reported claim
(Q39).** `e2.yaml` registers `report_all_comparisons: true` without specifying a
correction. Under Holm over the non-primary contrasts, **"Latin hypercube also beats
BO" at the primary cell fails**, as do the two other LHS cells and
qLogNEI's only significant win. The registered DoE contrast is exempt and unaffected.

> ⚠️ **UNRESOLVED DISCREPANCY, flagged rather than picked (triage).** This row says Holm over
> **39** contrasts takes p **0.0147 → 0.1914**. `RESULTS.md` Q39 says Holm over **54** contrasts
> takes the same p to **0.2356**. `OPEN-QUESTIONS.md:3467` also says 39 → 0.2356. **The family
> size and the adjusted p do not agree across the three governing documents**, and the family size
> determines the adjustment, so this is not a typo in one of them.
>
> The **verdict is identical either way** — the claim fails at any of these numbers — so nothing
> downstream moves. But a reviewer who checks the arithmetic will find two Holm families of
> different sizes, and **whichever is right, the other must be corrected before submission.**
> `results/q39-multiplicity.json` is committed and settles it in one read.

**L17 The DoE arm's design geometry is SOUND, and that strengthens the finding rather
than weakening it (Q44).** At the four-factor second-order model stage 2 is actually built
for, in the region stage 2 occupies, the CCD is **~4.4× more D-efficient** than the
adaptive design. Coded instead to a common unit cube the adaptive design wins ~2.1×,
because it spans more of the space — **D-efficiency is undefined without stating the
region, and any single figure quoted without its coding is unfalsifiable.** Both codings
are reported. Either way the polynomial is **not** failing because its design is bad: it
fails on good geometry. Separately, **both design types are near-singular against a
*six*-factor model** (CCD singular in 50/50 runs, adaptive in 0/50), because stage 2 varies
only the kept factors — **this was found during the conditioning analysis, not anticipated**,
and is stated so that the analysis is not read as post-hoc.

**~~L18 No public dataset supports a continuous comparison~~** — ~~no endothelial dataset with
continuous factors and deposited per-condition data, and none for stem-cell differentiation
generally. This is why a synthetic benchmark was necessary, and it is worth stating as a
finding about the field rather than an apology for the method.~~

> **🔵 MERGED into L13 (triage) — this is a duplicate.** L13 states the same fact in nearly the
> same words ("No published endothelial dataset with continuous factors and deposited
> per-condition data exists… This is why a synthetic benchmark was necessary… worth stating as a
> finding about the field rather than an apology for the method"). Two limitation numbers for one
> limitation inflates the count and invites a reviewer to ask which is which. **L13 is the one
> that stands.** The Olympus warning below is *not* a duplicate and survives on its own.

⚠️ **The Olympus claim in
the close-out brief does not survive checking and must not be repeated as written.** It
states "ten emulated experimental datasets, none of them biological"; Olympus in fact
provides **33 experimentally-derived benchmarks** alongside 33 analytical functions, and
**the biological breakdown could not be confirmed** from anything indexed. Either read the
Olympus paper and restate it precisely, or drop the sentence — do not ship the count.

**L19 🔴 EVERY STATIC-ARM NUMBER IN E2 IS CONDITIONED ON TWO DESIGN DRAWS, AND `lhs`
DREW THE BEST OF SIXTY (Q48).** `runner.static_design(bounds, method, budget, seed)` takes
no instance argument, so at a given seed **all 25 instances are scored on the identical
48 points** and a cell contains 2 distinct designs across 50 runs, not 50. Two consequences:

- **The reported ordering of the static arms is not a finding.** Design-averaged over 60
  draws at d=6 σ=0.25, `lhs` / `sobol` / `random` are **0.1752 / 0.1777 / 0.1778** — a
  spread of 0.003 against a design SD of 0.025. E2 reports 0.1270 / 0.1724 / 0.2216, a
  spread of 0.095. `lhs` sits at the **0th percentile of 60** and `random` at the 98th.
  **At 48 points in 6 dimensions these three designs are indistinguishable.**
- **`instance_bootstrap` resamples the 25 instances as independent when they share a
  design**, so the design component of variance is absent from every static-arm interval
  this project reports. Those are **within-design** intervals and must be labelled so.

⚠️ This bears on **L14** and **L15**, both of which quote the `lhs` number. It is
independent of L15's multiplicity finding: Holm *widens the interval* to a tie, whereas
this **moves the point estimate**. Design-averaged, qLogEI 0.1553 against `lhs` 0.1752
puts **BO ahead by 0.020** at the registered primary cell, reversing the sign.

> ⚠️ **TRIAGE FLAG — half of this was resolved by the 20-seed completion; half still stands.**
> **Resolved:** the run is no longer 8 of 20 seeds. It completed at **20 of 20**, and the mean is
> identical to four decimals at both counts (SD 0.0082 → 0.0102), which is the strongest possible
> outcome for the scope reduction that was declared.
> **Still standing: Q50 has no entry in `docs/RESULTS.md` at all.** It is cited there for the
> design-averaged 0.1532 and for Q52 §2's fidelity gate, with no write-up behind either, and that
> absence is exactly why `RESULTS.md` went on saying the settling run was "Not run" while this
> claim already said ESTABLISHED. **Write Q50 into `RESULTS.md`.**

**✅ That reversal is now ESTABLISHED (Q50).** qLogEI was re-run across all **20**
registered campaign seeds, and the harness reproduces E2's 0.1553 exactly on the diagonal
where E2 sits. qLogEI design-averaged is **0.1532, SD 0.0102** — the mean is identical to
four decimals at 8 seeds and at 20 — and it moves by −0.002 where `lhs` moves by
+0.048, because only 14 of its 48 points are shared. Paired at instance level with both
arms design-averaged: **`lhs − qlogei` = +0.0220 [+0.0170, +0.0272], Wilcoxon
p = 6.0×10⁻⁸, BO ahead on 25 of 25 instances.** This *replaces* a member of Q39's
39-contrast family rather than adding one, and survives Bonferroni over all 39
(p = 2.3×10⁻⁶).

> ✅ **Reproducible as of 2026-08-14.** `scripts/q50_paired_recompute.py` re-runs the
> `lhs` arm keeping the per-instance axis that `run_q48_design_variance.py:82` collapsed,
> pairs it against the committed seed sweep **by `instance_id`**, and writes
> `results/q50-paired.json` with both per-instance vectors. Locked by
> `tests/test_q50_paired.py`.
>
> ⚠️ **The figures this replaces were stale, not wrong.** CLAIMS.md previously quoted
> **+0.0219 [+0.0145, +0.0292], p = 1.8×10⁻⁵, 21 of 25** — those are reproduced exactly
> by restricting qLogEI to its **first 8 campaign seeds**. They were computed before the
> 20-seed sweep finished and were never refreshed, because no script existed to refresh
> them. **The staleness was invisible in the headline**: the arm mean is 0.1532 to four
> decimals at 8 seeds and at 20, so only the paired statistics moved. The direction and
> the point estimate are unchanged; the corrected evidence is *stronger*, not weaker.

**L16 A benchmark-design trap worth stating generally.** **Ackley's optimum sits at the
exact centre of the coded box**, and every screening and CCD design includes centre runs
— so the DoE design *contains the answer* and scores ~~exactly 0.0000~~ **0.0123** under rule A
(d=6 σ=0.25; 0.0011 / 0.0131 / 0.0013 at the other three cells) for
reasons unrelated to search quality. Any centred test function silently rewards any
design with centre runs. We detect and void that comparison rather than report it.

> **🔵 CORRECTED (D20).** The **exact** zero was itself the oracle-best artefact — scoring the arm
> at the best *true* value among visited points makes a design containing the optimum score
> exactly 0. On rule A the centre run must still be *identified* against 47 noisy competitors, so
> it is near-zero rather than zero. **The reason to void Ackley is unchanged and is arguably
> sharper**: the design still contains the answer, and 0.0123 against BO's 0.7003 is still not a
> search result. Distinct DoE values across 25 seeds went 1 → 4/2/4/2, which is what a genuine
> near-zero looks like.
>
> ⚠️ Do not confuse this with Q42's *other* exact zero: the **unconstrained − constrained rule-C
> difference** on Ackley is genuinely 0.0000 to four decimals, and D20 did not touch it. That one
> stands, and it is the case that proves 1.4's conditional.

---

## What we explicitly do NOT claim

- **"BO beats current practice."** Not supported **under rule A** at either
  dimension: tested and lost at d=6 and d=8 (σ=0.25), tied at σ=0.10. Under rule C at Q41's
  primary scoring it wins everywhere, and under the constrained sensitivity three of four cells
  are null. **The unqualified sentence is not available under any rule** — which is why this is
  2.1 and not a claim. *(Triage: the rule must be named in the same sentence, per Q41.)*
- **"Our BO is more sample-efficient."** Not shown. At the primary cell qLogEI's only
  significant win is over pure random search, which is E1's sanity bar.
- **The additive-kernel secondary arm's win over DoE** (−0.0168, p=0.032). One cell, a
  secondary arm, post-hoc model development. A's own commit gives three independent
  reasons it is not a headline; all three stand.
- **E4's pooled figure as "the pre-registered primary".** It is not, and it disagrees in
  sign with the cell that is. *(Triage: 2.2 is dropped and E4 is ARCHIVE, so this no longer
  guards a live claim — but the prohibition stands for anyone who reopens E4.)*
- **That the ~93% additivity explains anything about the κ dependence.** *(Triage: 3.5 is
  dropped with E4; the prohibition now lives on **L1**, where the 93% figure itself lives.)*

---

## Blocking decisions — this document cannot be finished without them

| | decision | owner | governs |
|---|---|---|---|
| ~~**Q28 / T16**~~ | ~~rule A or rule C as E2's estimand~~ | ✅ **DECIDED** | **Q41: rule A stays the registered primary; the *unconstrained* argmax is the primary DoE scoring; all three scorings reported in every table, always.** |
| **T15** | accept the d=8 DoE split | **A** | whether 2.1's d=8 row stands — still open, reaffirmed at `OPEN-QUESTIONS.md:1399` |
| **Q23** | confirm `coord`'s unpaired status | **A** | L3 |
| ~~**Q19**~~ | ~~E4's registered cell or the pooled figure~~ | — | **No longer blocking — 2.2 and 3.1 are dropped.** Still unresolved, and it moves with E4 into ARCHIVE. It blocks any future paper that uses E4, not this one. |
| ~~**Q30**~~ | ~~how the additive arm is framed~~ | ✅ **DECIDED** | **Fixed in Q30's own registration, before it ran:** *"It is reported as post-hoc model development whatever it returns, never as E2's result."* Nothing was left for A to decide. |

> **🔵 TRIAGED. Five blocking decisions before, two after** — three struck: **two were already
> decided** (Q28/T16, Q30) and one **no longer blocks this paper** (Q19, which moves with E4 into
> ARCHIVE and remains genuinely unresolved for anything that uses E4). Q41 was decided by A and is recorded at
> `OPEN-QUESTIONS.md:2971`; Q30's framing was fixed in advance by its own registration. Listing a
> decided question as blocking is not harmless: it invites someone to re-open it, and the two
> estimand rows were the reason this file could not be finished.

**On the estimand decision, now that it is made:** both A and B had seen both numbers before it
was taken, which is exactly the situation pre-registration exists to prevent — and Q41 addresses
that directly rather than ignoring it. Its stated grounds are **independent of the numbers**:
fidelity to the source study's "prediction solution" wording, and that a saddle has no interior
maximum, so the constrained value reports *where the search was stopped* rather than *where the
model pointed*. The reporting rule it comes with — **all three scorings, every table, always,
with the rule named in the same sentence as the claim** — is what makes it defensible. What is
still not defensible is quoting one scoring alone.

---

## Appendix — what would make BO work for iPSC-EC differentiation

Added 2026-08-11, after the Hall/Ogle replay returned null. **This is forward-looking
design advice, not a claim.** It is separated from everything above deliberately: none of
it is evidence, and it must not migrate into the results.

### What our own results say the problem is NOT

Four candidate explanations for BO's performance are eliminated by direct test, and any
proposal to "fix" BO by revisiting them is already answered:

- **not the prior** (Q25) · **not the acquisition solver** (Q21, peak failure ~~0.875%~~ **0.250%**; 0.118% overall — see L6)
- **not the opening size** (Q26, partial at low noise only)
- **not the model class** — the additive kernel doubled held-out R² (0.375 → 0.744) and
  regret did not move (Q30). **Surrogate accuracy is not the binding constraint.**

The two things that *did* change the answer were **how the recipe is scored** (Q29,
reverses the verdict in all four cells) and **how much budget exists relative to the
candidate set** (Q31, where 8 of 24 conditions leaves 4 adaptive evaluations).

### What the literature converges on, and where it agrees with us

**Budget is the binding constraint, and published successes used far more of it.** The
robotic iPSC study searched 143 conditions over 111 days from ~200M combinations, and
reported 88% better production than the pre-optimised culture. Hall/Ogle's stage 2 has
**25**. A replay over 25 conditions cannot demonstrate what a 143-condition campaign
demonstrates, and our null should be read against that gap rather than as a verdict on
the method.

**Batch structure matters more than acquisition choice.** Reported experimental BO
campaigns typically run 2–5 batches of 3–50 measurements. That is the regime the method
was designed for; a single 48-evaluation budget split into batches of 4 is thinner than
anything in the applied literature.

**Heteroscedastic noise modelling is called out repeatedly** for biological assays, and
it is the one recommendation this project can act on immediately: the source assay has
~68% CV and per-condition SEM is 38–66% of the between-condition spread, yet the
published paper reports no variance at all. `LookupEvaluator` already carries a
per-condition `Yvar` derived from box statistics; a fixed-noise GP over an assay this
variable is the modelling error most likely to matter.

### The four things worth doing, in order

1. **Spend budget on replicates, not only on conditions.** With per-condition SEM at
   38–66% of the between-condition spread, adjacent conditions are not separable at n=1.
   Any method — BO, DoE, or random — is choosing between conditions it cannot tell apart.
   **This is the single highest-value change and it is not a BO change.**
2. **Score the method at the recipe it recommends, and say so in advance.** Q29 showed the
   verdict reverses on this choice alone, and Q28 showed it was never registered. Whatever
   is chosen, choose it before the run.
3. **Model the noise as heteroscedastic** rather than fixed, given the CV above.
4. **Run more conditions before expecting BO to beat a designed experiment.** At 23–25
   candidates a classical design is close to exhaustive, which is the regime where DoE is
   strongest and adaptivity has least room. The published successes operate two orders of
   magnitude above that.

### The honest summary

**On a near-separable landscape with ~25 candidate conditions and single-replicate
measurements, BO has almost nothing to exploit.** Our results and the applied literature
agree on that, from opposite directions. It is a statement about the experimental regime,
not about Bayesian optimisation.

**Sources:** [Robotic search for optimal cell culture in regenerative
medicine](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9239686/) ·
[A Guide to Bayesian Optimization in Bioprocess
Engineering](https://analyticalsciencejournals.onlinelibrary.wiley.com/doi/10.1002/bit.70129) ·
[Multi-Objective Bayesian Optimization for Data-Efficient Bioprocess
Development](https://www.biorxiv.org/content/10.64898/2026.02.02.703372v1) ·
[Biological Sequence Design using Batched Bayesian
Optimization](https://research.google/pubs/biological-sequences-design-using-batched-bayesian-optimization/) ·
[Multifactorial Optimizations for Directing Endothelial Fate from Stem
Cells](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0166663)
