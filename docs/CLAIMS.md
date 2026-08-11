# CLAIMS — what the evidence supports, and what it does not

**STATUS: DRAFT PROPOSAL by B, for A and Alan to cut. Nothing here is settled.**

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
| **Picheny, Wagner & Ginsbourger 2013**, *Struct Multidiscip Optim* 48:607 | The canonical noisy-BO benchmark. It explicitly separates the **infill** criterion (where to sample next) from the **identification** criterion (which point you report at the end). **That distinction is exactly rule A versus rule C.** | Cite as prior art for the distinction. **Do not present it as new.** Ours is a measurement of how much the choice matters on a classical comparator, not the observation that a choice exists. |
| **Bull 2011; Wang & de Freitas 2014; Nguyen 2017; Berk 2019** | The incumbent choice — best observation, best posterior mean, best sampled posterior mean — is an active theory thread for GP-EI. | Cite the lineage, in the **introduction**, not in related work. It frames the question rather than following from it. |
| **Nguyen et al. 2017** | Reports empirically that **best-observed beats the GP-mean counterpart** — **the opposite sign to our rule-C result.** | **Engage directly.** State their setting, state ours, name what differs. Most plausibly noise level and the number of near-optimal candidates: at σ_rel=0.25 the posterior mean's smoothing is worth more than it is at low noise, and our menus have many near-ties. Omitting a contrary published result would be the worst kind of citation. |
| **Gisperg et al.**, *Biotechnol Bioeng* review | BO gave a more precise model near the optimum, but **the number of experiments could not be reduced compared with DoE**, and increasing noise slowed BO. | **This is our ceiling finding, already in print.** Cite as convergent prior art, not as our discovery. It also independently predicts our σ=0.25-versus-0.10 pattern. |
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

And Q35 closes the loop: scored the way classical practice actually prescribes (constrained to the region explored), the DoE arm's rule-C figure is **0.1169** against BO's 0.1232. **The reversal disappears.** "BO wins under rule C" was an artefact of scoring the classical arm in a way its own literature warns against.

### What this contribution is NOT

- **Not "BO loses".** Q36 tested that on two standard functions and it does not generalise — BO wins everything on Hartmann6. Which method wins is a property of the landscape.
- **Not a new estimator, criterion or algorithm.** Nothing here is a method contribution.
- **Not a claim that anyone acted in bad faith.** The convention is unregistered in both camps; that is the point. An unregistered convention with a 10:1 leverage on the verdict is a field-level measurement problem, not a fault of either paper.

### Delete on sight

`project_record.md` §B.1.2 states of the efficiency claim: *"nothing in the prior-art critique touches it."* **That sentence is now doubly false** — replay benchmarking of BO against published datasets is an established genre with purpose-built frameworks, and Gisperg et al. report the no-reduction result in print. It is the most exposed claim in the record and must go.

---

## Tier 1 — established, robust, and the strongest thing the project has

These survived every check run against them, reproduce across independent
implementations, and do not depend on any contested choice.

**1.1 The published-style two-stage DoE workflow over-promises systematically and
massively.** Its fitted surface predicts a value at its recommended recipe that reality
does not deliver — pooled over-prediction **+1.103 [+1.024, +1.182]** against a response
whose maximum is **1.0**, in **100/100** cells (`E4-RESULTS-v2.md`). Running the
published procedure over the *full* space, hiding nothing, the predicted optimum fell
outside the region stage 2 explored in **100%** of runs and under-delivered against the
arm's own best measured point in **100%**, at both noise levels (`doe-arm.log`).

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
the UNCONSTRAINED scoring and must name it.** **The figure barely moves with dimension (6→8) or
with a 2.5× change in measurement noise**, which means it is driven by geometry rather
than by measurement error. This is 1.1 arriving independently, in regret units.

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

**2.2 The GP's uncertainty versus plain distance is κ-dependent and reverses sign.**
Pooled −0.0269 [−0.0728, +0.0182], "no advantage". By κ: **+0.1068** [+0.0461, +0.1668]
at κ=0.6 (GP better, and **above the pre-registered 0.08 equivalence bound**), −0.0173
at 0.7, **−0.0960** and **−0.1011** at 0.8 and 0.9 (GP worse, intervals clear of zero).
The pre-registration names κ=0.6 as the primary cell; the results document reports the
pooled figure under that name. **Blocked on Q19.**

---

## Tier 3 — negative results, and they are load-bearing

Reported as findings, not as failures. Several are stronger than a positive would have been.

**3.1 A GP's uncertainty does not beat plain nearest-neighbour distance at flagging
extrapolation.** Bounded, not merely unrefuted: any advantage is below 0.08. Prior art
says this was the expected outcome under GP theory (`E4-RESULTS-v2.md`).

**3.2 Giving the GP the biology's known shape made extrapolation worse**, not better
(`NEGATIVE-shape-aware-mean.md`).

**3.3 Surrogate accuracy is not the binding constraint on BO's regret here.** The
additive kernel made the model roughly twice as accurate — held-out R² **0.375 → 0.744**,
factor identification **0.853 → 0.965** — and regret did not move (−0.0015, p=0.711).
**"BO is losing because the model is bad, so improve the model" is refuted by direct
test with a measurably better model** (Q30).

**3.4 Four candidate explanations for BO's performance are eliminated by direct test:**
the prior (Q25), the acquisition solver (Q21, max failure rate 0.875% against a
pre-registered 1% threshold), the opening batch size (Q26, partial at low noise only),
and the model class (Q30). The surviving candidate is the scoring rule (2.1).

**3.5 Separability does not explain the κ sign flip.** Additive-fit R² inside each κ's
training sub-box is flat — 0.9645 to 0.9670, a range of 0.0025 — while the
discrimination difference swings 0.21 and changes sign. B's own proposed mechanism,
tested and refuted (Q22). **The 93% figure must not be cited as though it explained
this.**

**3.6 BO's recommendation beats its own best observation in all four cells** (15–20%
better). The posterior mean smooths noise, so the model's named recipe is a better bet
than the luckiest single reading. Combined with 1.3: **the two arms fail in opposite
directions — the polynomial's model is worse than its data, the GP's model is better
than its data.**

---

## Limitations — mandatory, and none of these are optional

**L1 The benchmark is ~93% additive.** Variance explained by a purely additive fit:
**0.930** at d=6, **0.927** at d=8 (Q22). The motivating study is *about* ECM protein
interactions, so the benchmark under-represents the phenomenon the paper exists to
study. **Every conclusion here is a conclusion about near-separable landscapes.**

**L2 One oracle family**, d ∈ {6, 8}, 25 instances × 2 seeds. Whether any of this holds
on landscapes with different structure is untested.

**L3 Two arms are unpaired** — `lhs` by registered exemption, `coord` because it starts
from a random interior point (Q18, Q23). Wider intervals for those comparisons, not bias.

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

**L8 The E2 verdict is specific to this landscape family (Q36).** On Hartmann6 —
non-additive, deceptive — **BO wins under every rule** (+1.0032 rule A). On Ackley both
methods fail and DoE fails less. Three families, three answers. **"Current practice beats
BO" is a result about near-separable, coordinate-wise-unimodal landscapes calibrated to
one published dataset, and must be written that way.** What does generalise is the
scoring-convention effect, in direction, on all three.

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
**10**; Latin hypercube reaches lower regret than qLogEI in **one**. A fixed-evaluation
comparison silently grants BO seven extra plate cycles. A regret-versus-rounds *curve*
cannot be drawn from the committed grid — E2 persisted summary rows, not curves — so only
the endpoint and the exact round count are available. Nor is q=4 defended as the right
batch width; a larger q would trade rounds against regret and that experiment has not
been run.

**L15 Multiplicity was never controlled, and correcting it costs one reported claim
(Q39).** `e2.yaml` registers `report_all_comparisons: true` without specifying a
correction. Under Holm over the 39 non-primary contrasts, **"Latin hypercube also beats
BO" at the primary cell fails** (p 0.0147 → 0.1914), as do the two other LHS cells and
qLogNEI's only significant win. The registered DoE contrast is exempt and unaffected.

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

**L18 No public dataset supports a continuous comparison** — no endothelial dataset with
continuous factors and deposited per-condition data, and none for stem-cell differentiation
generally. This is why a synthetic benchmark was necessary, and it is worth stating as a
finding about the field rather than an apology for the method. ⚠️ **The Olympus claim in
the close-out brief does not survive checking and must not be repeated as written.** It
states "ten emulated experimental datasets, none of them biological"; Olympus in fact
provides **33 experimentally-derived benchmarks** alongside 33 analytical functions, and
**the biological breakdown could not be confirmed** from anything indexed. Either read the
Olympus paper and restate it precisely, or drop the sentence — do not ship the count.

**L16 A benchmark-design trap worth stating generally.** **Ackley's optimum sits at the
exact centre of the coded box**, and every screening and CCD design includes centre runs
— so the DoE design *contains the answer* and scores exactly 0.0000 under rule A for
reasons unrelated to search quality. Any centred test function silently rewards any
design with centre runs. We detect and void that comparison rather than report it.

---

## What we explicitly do NOT claim

- **"BO beats current practice."** Not supported under the registered rule at either
  dimension: tested and lost at d=6 and d=8 (σ=0.25), tied at σ=0.10. Under rule C it
  wins everywhere — which is why this is 2.1 and not a claim.
- **"Our BO is more sample-efficient."** Not shown. At the primary cell qLogEI's only
  significant win is over pure random search, which is E1's sanity bar.
- **The additive-kernel secondary arm's win over DoE** (−0.0168, p=0.032). One cell, a
  secondary arm, post-hoc model development. A's own commit gives three independent
  reasons it is not a headline; all three stand.
- **E4's pooled figure as "the pre-registered primary".** It is not, and it disagrees in
  sign with the cell that is (2.2).
- **That the ~93% additivity explains anything about the κ dependence** (3.5).

---

## Blocking decisions — this document cannot be finished without them

| | decision | owner | governs |
|---|---|---|---|
| **Q28 / T16** | rule A or rule C as E2's estimand — or both, co-primary | **A / Alan** | 2.1, the paper's headline |
| **Q19** | E4's registered cell or the pooled figure | **A / Alan** | 2.2, E4's headline |
| **T15** | accept the d=8 DoE split | **A** | whether 2.1's d=8 row stands |
| **Q23** | confirm `coord`'s unpaired status | **A** | L3 |
| **Q30** | how the additive arm is framed — a *different method*, not qLogEI rescued | **A** | 3.3 |

**On the two estimand decisions:** both A and B have now seen both numbers, which is
exactly the situation pre-registration exists to prevent. The defensible resolutions are
to report both side by side with neither promoted, or for **Alan** to choose. What is not
defensible is either of us choosing quietly and writing it up as though it had been the
plan.

---

## Appendix — what would make BO work for iPSC-EC differentiation

Added 2026-08-11, after the Hall/Ogle replay returned null. **This is forward-looking
design advice, not a claim.** It is separated from everything above deliberately: none of
it is evidence, and it must not migrate into the results.

### What our own results say the problem is NOT

Four candidate explanations for BO's performance are eliminated by direct test, and any
proposal to "fix" BO by revisiting them is already answered:

- **not the prior** (Q25) · **not the acquisition solver** (Q21, peak failure 0.875%)
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
