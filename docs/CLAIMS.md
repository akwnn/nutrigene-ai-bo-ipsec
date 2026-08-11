# CLAIMS — what the evidence supports, and what it does not

**STATUS: DRAFT PROPOSAL by B, for A and Alan to cut. Nothing here is settled.**

This exists because the results are in, the logs disagree with each other, and whoever
writes first from whichever log they happen to open will set the paper's claim by
accident. Three known contradictions between artefacts:

- `results/e2.log` prints the primary-cell difference as **−0.0595**; the grid that
  same run persisted gives **−0.0708** (Q29). Three computations agree against the log.
- `results/E4-RESULTS-v2.md` labels the **pooled** figure "pre-registered primary";
  the pre-registration names a **single cell**, and the two disagree in sign (Q19).
- E2's headline reverses depending on a scoring rule the pre-registration never
  fixed (Q28, Q29).

**Rules for this document.** Every claim carries its evidence and its file. Contested
estimands are listed as contested, with **both** numbers — they are not resolved here,
because the people who have seen both numbers should not be the ones to choose.
Decisions belong in `OPEN-QUESTIONS.md`; this file only states what follows from them.

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
cells (`q29-symmetric-allcells.log`). **The figure barely moves with dimension (6→8) or
with a 2.5× change in measurement noise**, which means it is driven by geometry rather
than by measurement error. This is 1.1 arriving independently, in regret units.

**1.4 The fitted surface is a saddle essentially always.** 800/800 PF1 cells, 100/100
E4 cells, 20/20 DoE-arm runs — zero maxima, zero minima. Four independent confirmations.
The spec predicted a mix and specifically predicted minima at tight settings; it was
comprehensively wrong (`pf1-grid.log`, Q16).

**1.5 The source paper's own reported optimum was extrapolated.** Reconstruction from
the published figure puts Collagen IV at coded **+1.40** — 20% above the highest
concentration ever tested (`pdf_crosscheck.md`). Flagged as **our inference**, not the
authors' statement, and needing a statistician to re-derive before it carries weight.

---

## Tier 2 — established but CONTESTED, because the estimand was never fixed

**Both of these are real measurements. Neither has an agreed headline.**

**2.1 Whether BO beats current practice depends on the scoring convention, and nothing
else.** Same runs, same seeds, same data:

| cell | rule A — best observed *(registered)* | rule C — each model's recommendation |
|---|---|---|
| d=6 σ=0.25 | **−0.0708** DoE better | **+0.2915** BO better |
| d=6 σ=0.10 | +0.0042 null | **+0.3598** BO better |
| d=8 σ=0.25 | **−0.0321** DoE better | **+0.2689** BO better |
| d=8 σ=0.10 | +0.0015 null | **+0.3253** BO better |

All rule-C results p < 0.0001; rule A regenerates the stored grid at max |Δ| **exactly
0.0 over 200 rows**. At the low-noise cells the convention changes a *tie* into a
decisive win — it does not merely rescale the effect. **Blocked on Q28 / T16.**

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

**L6 Acquisition-solver failures**: 9 second-try failures, concentrated entirely in the
two σ=0.25 cells, peaking at **0.875%** at d=8 σ=0.25 — below the pre-registered 1%
threshold, and close enough to it to state (Q21).

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
