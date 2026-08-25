# Matched-budget benchmarking of Bayesian optimization and response-surface methodology depends on the terminal decision rule

**Running title.** Terminal decision rules reverse BO-versus-RSM rankings on a synthetic recipe benchmark.

**Keywords.** Bayesian optimization; response-surface methodology; terminal decision rule; matched budget; Gaussian process; simple regret; sequential design; experimental rounds.

**Data.** All numerical claims are taken from the committed artefacts listed in the Data availability statement. Internal experiment identifiers (E2, Q34, …) are given in parentheses for reproducibility. Section 2 is a plain-language guide to the tables. The revision workstreams in `docs/PROMPTS-NEXT.md` are complete (Q54–Q59).

**What this paper is not.** It is not the first BO-versus-DoE comparison, not a claim that “BO maps differently from RSM” as a new idea, and not a wet-lab validation of an ECM formulation. Rummukainen, Lapierre and Ndahiro already ran executed comparisons; Rummukainen already stated that RSM maps a region while BO concentrates near promising conditions.

**What this paper is.** A controlled demonstration that, under identical budgets and identical latent landscapes, changing only the **terminal decision rule** can reverse the apparent winner; and a factorial split of sampling design, surrogate class, recommendation rule, and well-versus-round cost. Most of the large unconstrained “BO win” is a naïve extrapolative readout of a saddle-shaped quadratic, not a fair classical-RSM recommendation. The measured-value-argmax DoE lead at the primary cell is mostly identification, survives noisy expected improvement, and **vanishes under a three-well confirmation protocol**.

**Novelty (adversarial).** BO-versus-DoE, “BO optimizes / RSM maps,” matched-budget media comparisons, synthetic optimizer benchmarks, and “best observation ≠ model recommendation” as a concept are **already in the literature**. What is potentially new is the same-campaign winner reversal plus the design × surrogate × locator decomposition (Q34/Q45/Q35), the identification-versus-search split, and the demonstration that a three-well confirmation protocol erases the primary measured-value-argmax ranking.

| Claim | Assessment |
|---|---|
| BO versus DoE itself is novel | No |
| “BO optimizes while DoE maps a region” is novel | No (Rummukainen) |
| Matched-budget BO–DoE comparisons are novel | No (Rummukainen; Lapierre 2025; Ndahiro 2025) |
| Synthetic benchmarking of experimental optimizers is novel | No |
| Best-observation versus model-recommendation as a distinction is novel | No (noisy-EI literature) |
| Same-campaign winner reversal across terminal rules | Yes, potentially |
| Design × surrogate × locator decomposition | Yes, and probably the strongest contribution |
| Explicit well-cost versus plate-round-cost | Valuable for laboratory practice |
| Confirmation / replicate protocol as a terminal-rule sensitivity | Yes, and the most lab-relevant add-on |
| Current unconstrained-RSM result as the fair main comparison | Still a diagnostic; in-region is the fair 48-well readout |
| Publishable somewhere after revision | Yes, as a specialist methods / benchmark paper |
| Strong enough now for a top general journal | No |
| Could become a strong specialist benchmark / methodology paper | Yes |

---

## Abstract

**Background.** Reported advantages of Bayesian optimization (BO) over response-surface methodology (RSM) may depend as much on how the terminal formulation is selected as on where either method samples. Narayanan et al. (2025) report ~2.5–3× fewer experiments than the **predicted** count for standard DoE (and ~10–30× in a nine-factor transfer case): a resource-planning denominator, not an executed equal-budget DoE arm. Rummukainen et al. (2024) ran both methods at 15 experiments, scored the best measured condition, used noisy expected improvement then a posterior-mean final pick, and found no reduction in experiment count. Lapierre et al. (2025) and Ndahiro et al. (2025) add executed media/bioprocess comparisons in which BO improved biomass or titer; those studies compare complete workflows whose screening cuts, factor sets and terminal picks are not factorially separated. Both the “BO saves experiments” and the “no saving at matched budget” findings can be correct if their denominators and terminal decisions differ.

**Methods.** A synthetic Hill benchmark, **structurally inspired by** the six-factor / 6→4 screen of Hall, Lin and Ogle (2025), not fitted to endothelial data. The optimizer observes y = f(x) + ε. Simple regret is 1 − f(x∗). On identical 48-well campaigns we vary the terminal decision: **hidden tested-best**, **measured-value argmax** (single noisy readout; stored E2 “best observed”), **naïve unconstrained quadratic or GP recommendation**, **in-region / ridge recommendation**, and — on the same campaigns — **replicate, top-3 confirmation, and posterior-mean-at-visited** picks. Cost is counted in wells and in plate rounds. Named BO is qLogEI; **qLogNEI is co-primary** under observation noise. Sequential RSM with steepest-ascent relocation is the long-run classical arm (`doe_ascent`); `doe_repeat` is retained as the non-relocating control.

**Results.** On the same campaigns, rankings reversed. At σ = 0.25, measured-value argmax favoured sequential DoE by 0.0595 (d = 6) and 0.0284 (d = 8); the same verdict holds against qLogNEI (−0.0574 at the primary cell). About 55–73% of that lead is identification, not search. Confirming the top three wells on the same campaigns reduces the primary contrast to −0.0009 (null). Naïve unconstrained recommendation favoured BO by 0.27–0.36: almost all of that swing is a saddle-shaped quadratic optimized off its learned region (200/200 Hill runs). In-region recommendation was null in three of four cells. Under measured-value argmax, sequential RSM matches qLogEI on arrival to N = 200; the previous “BO hits more often” result does not survive a walking classical arm. One-shot GP at five Latin-hypercube draws is stable in 20 of 22 cells and, at σ = 0.25 under model recommendation, beats 10-round qLogEI. On Hartmann6, removing the 6→4 screen makes DoE worse, not better. **Scored as a design space rather than a single recipe, the ranking reorders:** the regret winner `doe` is last on map quality in 23 of 24 Hill cells and symmetric-difference-worst in 36 of 92 cross-family cells, and it fails four of the RSM community's own diagnostics — rank-deficient in 50 of 50 campaigns, over-predicting confirmation in 25 of 25, calibration 5.2× worse than any other arm. A two-plate spread protocol (SPADE) is first on map quality and first on refinement at 2 plate rounds against 3 and 10, with regret at parity under a posterior-mean rule — but mid-field on calibration (5th–7th of 9), and its certificate holds on Hill while failing at γ = 0.99 on two of four external families and declining to certify at all on the other two. The prospective SPADE study now contains 99,601 combined records across seven conditions, including the full-dimensional classical comparator where feasible. It narrows the claim: the boundary-targeted second plate does **not** beat random placement of the same wells (−0.0019, p = 0.41), and the second plate's benefit over one plate (+0.0117) falls below the declared 0.02 SESOI. A registered 400-campaign follow-up tested error-aware acquisition and diversity-aware batching; both failed the same 0.02 bar at the Hill target, and their smaller Hartmann improvements did not rescue the mechanism.

**Conclusions.** A matched evaluation count does not define a unique BO-versus-RSM comparison. Rankings changed when the terminal decision changed, including when a laboratory-plausible confirmation protocol replaced a single noisy readout. Most of the unconstrained reversal arose from extrapolative optimization of saddle-shaped quadratic fits and largely disappeared under in-region constraints. Well count and plate-round count are different costs; under measured-value argmax there is no well-count saving versus walking RSM. Comparisons should prespecify the terminal decision, treatment of measurement noise, permitted extrapolation, confirmation protocol, and unit of experimental cost — and, where the deliverable is an operating window rather than a setpoint, the scored object itself, which reorders the arms in every cell measured. The study is not a wet-lab validation.

**Revision status.** Search versus identification, qLogNEI co-primary, sequential RSM, multi-draw one-shot GP, Hartmann without forced 6→4, and selection-rule sensitivity are closed (Q54–Q59). The design-space programme (K6, P6–P8, Version C), all seven conditions of `spade-final-2026-08-23`, and the registered KF-3 mechanism follow-up are complete. The `doe_unscreened` comparator is implemented and has 100 campaigns in every six-factor condition; it is structurally unavailable at eight factors within 48 wells. The final prospective ledger has four passes (KF-1, KF-6–KF-8) and six failures (KF-2–KF-5, KF-9, KF-10). Both proposed repairs to second-plate targeting fail their registered bar, so the combined repair is moot. SPADE's certificate is measured on five families: no Hill cell is below nominal at 4,096 draws, it fails at γ = 0.99 on Levy and Rosenbrock, and it usually declines on Ackley and Hartmann6. Remaining before submission: restore the ignored raw prospective artefacts for a clean-checkout audit, generate the final prospective calibration table and publication figures, re-read citations from primary PDFs, and retain the existing scope gaps—no d = 8 cost curves, no in-region long-run RSM recommendation, and no wet-lab validation.

---

## 1. Introduction

Optimization of culture media and extracellular-matrix (ECM) coatings is an expensive black-box problem. Each experimental condition consumes a well; each plate cycle—selection, incubation, readout, then reselection—consumes a **round**. Full-factorial grids are infeasible: five levels in six factors require 5⁶ = 15,625 evaluations. Practitioners therefore use sequential or planned designs that nominate a small set of conditions and, after the budget is spent, a single formulation to carry forward.

Two families of methods dominate this setting.

**Classical DoE and RSM** (Box and Wilson, 1951; Myers et al.) treat the unknown response as locally quadratic. A screening design identifies a subset of active factors. A **central composite design** (CCD) is then executed in that subregion and a second-order polynomial is fitted. Canonical analysis classifies the stationary point as a maximum, minimum, saddle or ridge. Classical RSM then uses **steepest ascent**, **ridge analysis**, and often a relocated CCD — not unconstrained maximization of a saddle over the whole box.

**Bayesian optimization** (Močkus, 1975; Jones, Schonlau and Welch, 1998; Frazier, 2018) places a Gaussian-process prior on the latent response and picks the next batch with an acquisition function. We report **qLogEI** and **qLogNEI** as co-primary under observation noise. The distinction between using the best noisy observation and using a posterior-mean incumbent is already standard in noisy BO; this paper asks whether that already-known distinction is large enough to reverse a BO-versus-RSM ranking, and whether a short confirmation protocol is.

That RSM maps a design region while BO concentrates accuracy near promising conditions is **background**, not a finding. Rummukainen et al. (2024) already state it, and note that RSM remains usable if the criterion later changes whereas BO needs an explicit scalar objective.

Executed comparisons already exist. Rummukainen: 15-run Box–Behnken versus 5 initial + 10 sequential BO experiments, noisy EI then posterior-mean final pick, best measured condition, no reduction in experiment count. **Lapierre et al. (2025)** compared CCD/RSM after factor reduction with batch BO that kept all factors, after a shared 48-condition screen, on *Sporosarcina pasteurii* growth media; the BO medium gave higher biomass. **Ndahiro et al. (2025)** reported mammalian (CHO) media BO with thermodynamic constraints and higher titers than classical DoE **at the same experiment count**. **Narayanan et al. (2025)** report ~2.5–3× fewer experiments than the **predicted** standard-DoE count (SI calculation), and ~10–30× in a nine-factor transfer case. That is a different scientific experiment from giving each method 48 evaluations on the same landscape. Synthetic optimizer benchmarks (Olympus and related platforms; materials-science BO suites) already exist; novelty here is not “we ran a benchmark.”

**Hypothesis.** Apparently conflicting BO-versus-DoE conclusions can arise without contradictory algorithmic behaviour when studies bundle different terminal decisions, surrogate readouts, screening cuts, and budget definitions. Previous experimental papers compare complete workflows. We hold components under experimental control: same campaigns, several terminal rules; same points, both surrogates; same surrogate dimension, both designs; wells versus rounds.

Figure 1 is winner reversal by terminal rule (generated from stored JSON; blank cells are quantities that were never measured). Figure 2 is cost in two currencies, with hit probability P(T ≤ N) as the primary arrival display. Figure 3 is the saddle / ridge mechanism. The factorial (Q34/Q45) separates design from surrogate. Protocol sensitivities (Q54–Q59) ask whether those findings survive noisy EI, a walking RSM arm, a confirmation pick, multi-draw one-shot GP, and Hartmann without a forced 6→4 screen.

The latent function is constructed. Factor count and the 6→4 screen are **structurally inspired by** Hall, Lin and Ogle (2025). No wet-lab BO campaign is reported.

---

## 2. Reader's guide

This paper is a **computer experiment**, not a wet-lab validation. A hidden mathematical function stands in for “how good is this recipe.” The optimizer never sees that function. It sees a noisy measurement, as a laboratory assay would. After a fixed number of recipes, we ask how far the nominated recipe is from the hidden best. Distance from the best is **simple regret**: 0 is perfect; larger is worse.

### 2.1 The laboratory questions

Every table answers one of these. They are not interchangeable.

1. **Hidden tested-best (search quality).** Among wells actually run, max noiseless f. A lab cannot compute this. Primary cell: DoE 0.0597, qLogEI 0.0755, qLogNEI 0.0834 (Q55/Q57).
2. **Measured-value argmax (single-readout selection).** Pick argmax of noisy y, score noiseless f. One transparent operational rule, **not** “what every researcher would do.” This is the stored E2 “best observed” column (`reported_best_curve`). Primary cell: DoE 0.0958, qLogEI 0.1553, qLogNEI 0.1532.
3. **Naïve unconstrained model recommendation.** Argmax of the fitted quadratic or GP over the whole box. For the quadratic this is a **diagnostic failure mode** when the fit is a saddle, not classical RSM.
4. **In-region / ridge recommendation.** The principal classical readout: argmax inside the explored region.
5. **Confirmation / replicate / posterior-mean pick.** Same campaigns, different final pick (Q58). Confirming the top three wells at the primary cell makes measured-value-argmax DoE and BO indistinguishable.
6. **Cost.** Wells and plate rounds until a target. Lead with hit probability P(T ≤ N). Sequential RSM with relocation (`doe_ascent`) is the fair long-run classical arm; `doe_repeat` does not relocate.

DoE and BO can win different questions on the same 48 wells. That is the point of the paper, not a contradiction.

### 2.2 What one “cell” is

A **cell** is one experimental setting, not a tissue-culture well. The four cells are the four combinations of:

- **d = 6 or 8.** Number of recipe factors. Six matches the Hall/Ogle ECM proteins. Eight is the same six active factors plus two dummy ingredients that do not affect quality, to test wasted dimensions.
- **σ = 0.25 or 0.10.** Higher-noise and lower-noise **benchmark** conditions. A Hall/Ogle box-plot CV is not the same object as this additive Gaussian σ. Do not read 0.25 as “realistic assay noise” until σ is estimated from replicated raw observations on this scale.

The **primary cell** is d = 6, σ = 0.25: the setting locked before the main experiment closed. The other three cells ask whether the same pattern holds with extra dummy factors or a cleaner assay.

Each cell is repeated on **25 landscapes** (25 random hidden surfaces). Each landscape is run twice with different random seeds and averaged. Statistical tests therefore use 25 paired differences, not 50 independent campaigns.

### 2.3 How to read a results table

| Column | Meaning in one sentence |
|---|---|
| DoE, BO, Mean R | Average simple regret. **Lower is better.** 0.10 means the nominated recipe has true quality 0.90. |
| DoE − BO | DoE’s regret minus BO’s regret on the same landscapes. **Negative: DoE better. Positive: BO better.** |
| p | Wilcoxon signed-rank p-value. Small p means the sign of the difference is consistent across landscapes. It does **not** by itself say the gap is large. |
| Call | One-word verdict: which method is ahead, or **null** if we cannot tell them apart (p large, or the confidence interval covers zero). |
| [low, high] | 95% bootstrap interval for the mean difference. If it includes 0, the contrast is treated as null even if the point estimate is not exactly zero. |

**Wilcoxon signed-rank test.** For each of the 25 landscapes, subtract one method from the other. The test asks: is one method ahead on most landscapes, allowing for the size of the ranks? It is used because the 25 differences are paired (same hidden surface) and need not be Gaussian. A conventional threshold is p < 0.05.

**Bootstrap interval.** Resample the 25 landscapes and recompute the mean gap. The interval is the range of typical mean gaps. It answers “how large,” which Wilcoxon does not.

**Holm–Bonferroni correction.** When many arms are compared with BO in the same cell, or when many regret targets are tested, some p-values will look small by chance. Holm raises the bar. “Not significant after Holm” means the raw p was small but does not survive that correction. The primary DoE-versus-BO tables in Section 5.1 are single planned contrasts and are not Holm-adjusted.

**Null** means “no demonstrated difference,” not “the methods are proven identical.” Do not describe p ≈ 0.05 as a directional win.

**Inferential hierarchy.** Primary confirmatory contrasts: sequential DoE versus named BO at d = 6, σ = 0.25, N = 48, under measured-value argmax and under in-region recommendation. Secondary: naïve unconstrained diagnostic, design × surrogate factorial, arrival / P(T ≤ N). Exploratory: control arms, Q42 families, one-shot GP on one Hill draw, p = 0.052 cells. Report effect size and interval first; p second. The scientifically interesting fact is that a 0.0595 DoE advantage becomes an approximately 0.293 BO advantage when the same experiment is read out differently — not that p = 2.2 × 10⁻⁵.

### 2.4 Why each experiment exists

The identifiers (E2, Q34, …) are internal run names. They are not additional scientific claims. Each exists to answer one confound.

| ID | In one sentence | Why it is needed |
|---|---|---|
| E1 | Can this BO implementation beat random search on standard functions? | Sanity check. If BO cannot beat random, later DoE comparisons are uninterpretable. |
| E2 | At 48 wells on the Hill ensemble, who has the better already-run recipe under measured-value argmax? | Main matched-budget comparison (single-readout selection). |
| Q27 | Same comparison at eight factors. | The original E2 grid omitted DoE at d = 8. |
| Q34 | On the **same** 48 wells, refit a polynomial and a GP to **both** designs. | Separates “who sampled where” from “which model was fitted.” |
| Q35 | On the **same** DoE polynomial, score the best well vs the polynomial peak vs the in-region peak. | Separates the locator (which point we read off the fit) from the campaign. |
| Q45 | Repeat the polynomial comparison with **four** factors on both designs. | Q34’s BO-side polynomial used six factors; that confounds design with model size. |
| Q42 | Repeat the whole pipeline on Levy, Rosenbrock, Hartmann6 and Ackley. | Checks that the Hill pattern is not an artefact of one oracle family. |
| Q52 | Continue to 200 wells; plot regret vs wells and vs plate rounds; record when a target is first hit. | A snapshot at 48 wells cannot say who is cheaper. |
| Q53 | One big random batch plus one GP fit, versus 10-round sequential BO, same well count. | Asks whether sequential adaptation is doing work, or whether the GP alone would suffice. |
| Q54 | Same one-shot GP on Hill at five Latin-hypercube draws. | One draw is not a conclusion. |
| Q55 / Q57 | Hidden tested-best beside measured-value argmax, both arms; qLogNEI co-primary. | Separates search from identification; blocks “wrong acquisition.” |
| Q56 | Sequential RSM with steepest ascent / relocation, cap 200. | `doe_repeat` is not classical sequential RSM. |
| Q58 | Replicate, confirm top-3, or posterior-mean pick on the same 48-well campaigns. | Measured-value argmax is one laboratory protocol, not all of them. |
| Q59 | Hartmann6 with and without the 6→4 screen (d = 6). | Tests whether BO’s Hartmann win is a screening artefact. |

Controls (Latin hypercube, Sobol', uniform random, noisy-EI, coordinate descent) are not competing laboratory methods in this paper. They answer “is BO beating anything other than a straw man?” and “does swapping the acquisition function matter?”

---

## 3. Theoretical background

### 3.1 Latent response, observation model and simple regret

Let x ∈ [0,1]ᵈ denote a formulation in coded units and let f(x) be the noiseless quality, scaled so that max f = 1 on every Hill instance. The algorithm observes

> *y* = *f*(*x*) + ε, ε ∼ 𝒩(0, σ²)

in relative units. Larger σ corresponds to a less precise assay: replicate wells of the same x are more likely to rank incorrectly.

Scoring on y credits a fortunate noise draw. All results below use **simple regret** at the nominated point x∗,

> *R*(*x*∗) = 1 − *f*(*x*∗)

R = 0 if and only if the true optimum is nominated. This is the terminal recommendation error of the BO literature, distinct from **cumulative regret** (the sum of instantaneous losses along the path). A laboratory that will nominate one formulation is concerned with simple regret; a laboratory that also values wasted plates along the path is concerned with cumulative regret. We report simple regret, then, separately, the evaluations and rounds required to first cross a regret target.

The locators x∗ are:

| Terminal decision | How x∗ is chosen | What a lab can actually do |
|---|---|---|
| Hidden tested-best | Evaluated x of maximal true f | Not available without an oracle. Both arms stored (Q55/Q57) |
| Measured-value argmax | Evaluated x of maximal noisy y; score true f | Single-readout selection. Confirmation / replicate / posterior-mean variants in Q58 |
| Naïve unconstrained recommendation | arg max of f̂(x) over x ∈ [0,1]ᵈ | Diagnostic when the quadratic is a saddle |
| In-region / ridge recommendation | arg max of f̂(x) over the explored region | Classical remedy; principal RSM readout |

Rule A is defined for every procedure. Recommendation locators require a surrogate. The headline already-run tables use rule A, not hidden true-best.

### 3.2 Second-order response surfaces

The second-order model on the retained factors is

> *f̂*(*x*) = β₀ + Σᵢ βᵢ *x*ᵢ + Σᵢ βᵢᵢ *x*ᵢ² + Σ βᵢⱼ *x*ᵢ *x*ⱼ (i < j)

The Hessian of f̂ may be negative definite (local maximum), positive definite (local minimum) or indefinite (**saddle**). A saddle has a stationary point that is not a maximum; on a compact box the maximum of a saddle lies on the boundary. An unconstrained argmax of a saddle fit is therefore forced onto a face or corner, typically outside the region in which the polynomial was identified. Ridge analysis is the classical remedy.

The DoE procedure implemented here follows a published three-stage pipeline: (i) a 20-run screen (fractional factorial with centre points) retaining four factors, matching Hall/Ogle 6→4; (ii) a 27-run **face-centred CCD** on those four factors; (iii) one confirmation at the fitted stationary point. There is **no steepest-ascent stage** after the CCD. Cost-curve comparisons are therefore biased in favour of BO, which we state wherever those comparisons appear.

**D-efficiency** quantifies the information matrix of a stated model on a stated region. High in-region D-efficiency does not imply a useful recommendation outside that region.

### 3.3 Gaussian-process surrogates and expected improvement

A GP is a distribution over functions. Conditioning on data yields, at each unevaluated x, a posterior mean μ(x) and posterior variance σ²(x). **Expected improvement** (Jones et al., 1998) is the expected increase in the incumbent value if x is evaluated; it is large both where μ is high and where σ is high. The named stored arm is **qLogEI**, a numerically stable batch form, with batch size q = 4. The initial design is n₀ = 2d+2 (14 at d = 6); subsequent batches of four continue until N = 48 (**10 rounds**). **qLogNEI** is co-primary under observation noise (Q57): primary-cell measured-value-argmax 0.1532 versus qLogEI 0.1553. Rummukainen used noisy EI then a posterior-mean final pick.

A GP may also be used non-sequentially: a single Latin hypercube of size n, one posterior fit, and nomination of arg max μ(x). That one-shot procedure (**spread_gp**) costs one round and isolates the contribution of sequential adaptation.

### 3.4 Space-filling baselines

Latin hypercube sampling (LHS) and Sobol' sequences distribute evaluations so that marginal coverage of each factor is even. They neither fit a surrogate nor adapt. If they dominate sequential BO under measured-value argmax, adaptation is not earning its additional rounds.

### 3.5 Experimental cost

**Evaluations** (wells) count formulated conditions. **Rounds** count plate cycles. A 48-point Latin hypercube is 48 evaluations and one round; the same 48 evaluations under qLogEI with n₀ = 14 and q = 4 are 10 rounds. Cost curves are therefore reported on both axes.

### 3.6 Inference

Each landscape is seen by both methods, so the comparison is paired: the same hidden surface, two algorithms. The two random seeds per landscape are averaged first; the test then uses the n = 25 paired differences (one number per landscape). Sign convention throughout: DoE minus BO; negative values mean DoE had lower (better) regret.

The Wilcoxon signed-rank test and the bootstrap interval are defined in Section 2.3. In brief: Wilcoxon answers “is the sign consistent?”; the interval answers “how large is the mean gap?”; Holm correction is used only when several comparisons share a family (control arms versus qLogEI in one cell; several arrival targets). An interval covering zero, or a large p-value, is reported as **null**.

---

## 4. Methods

### 4.1 Benchmark

The latent response on each instance is a biphasic Hill function with known optimum 1. Parameters are drawn from pre-specified ranges; they are not fitted to Hall/Ogle measurements. Peak location, interaction strength and pan-factor biphasicity are design choices. Digitized stage-2 Hall/Ogle data resolve an interior peak on one of four proteins; the oracle assumes an interior peak on all active factors.

Forty-seven condition medians digitized from Hall, Lin and Ogle (2025), Figs. 1a and 2a (CD31/DAPI), were used in three auxiliary analyses only. Replay of the published conditions was null; the minimum detectable effect was 0.68, so the digitized assay cannot resolve a method difference. In-house flow-cytometric files exist but unsigned CD31 percentages are excluded by the optimizer; they are not used.

Algorithms observe only y. All reported R use only f(x∗).

### 4.2 Experimental grid

The registered factorial is d ∈ {6,8} × σ ∈ {0.10, 0.25}.

| | σ = 0.25 (noisy) | σ = 0.10 (low noise) |
|---|---|---|
| d = 6 | **Primary cell**, locked before the main experiment closed | Sensitivity to assay precision |
| d = 8 | Identical active structure plus two inert coordinates | Same, at low noise |

d = 6 matches the six ECM proteins of Hall/Ogle; axis labels are nominal. d = 8 adds two coordinates that do not enter f, isolating the cost of inert dimensions rather than additional biology.

σ = 0.25 and σ = 0.10 are **higher-noise** and **lower-noise benchmark conditions**. A Hall/Ogle box-plot coefficient of variation (~68%) mixes biological variation, measurement variation, between-condition heterogeneity and scaling; it is not this additive Gaussian σ. Do not call 0.25 “realistic assay noise” until σ is estimated from replicated raw observations on the same normalized scale. The 2.7-fold comparison to that CV is background only.

Replication is 25 instances × 2 seeds (50 rows). Tests use n = 25. Unless otherwise stated the experimental budget is N = 48, the published 20+27+1 pipeline length; BO is given the same evaluation count.

### 4.3 Procedures

The stored named comparison is qLogEI versus sequential DoE. **qLogNEI is co-primary** under noise (Q57). Remaining arms are controls.

- **qLogEI (BO).** Start with 14 recipes, then pick 4 more per plate using expected improvement, ten plates total.
- **qLogNEI.** Same loop with noisy expected improvement. Natural comparator when y = f(x) + ε.
- **DoE (48-well pipeline).** Screen 20 recipes, keep four ingredients, run a 27-run face-centred CCD, confirm one point. Three plate stages. No steepest ascent at this budget (nothing to relocate).
- **doe_ascent (Q56).** The same pipeline, then steepest ascent and a relocated CCD, to a 200-well cap.
- **spread_gp.** One Latin hypercube, one GP fit, read the posterior peak. One plate. Hill results use **five** independent design draws (Q54).
- **LHS / Sobol' / random.** Spread or scatter 48 recipes with no model. Scored only under measured-value argmax.
- **Coordinate descent.** Tune one factor at a time. Unpaired control.

| Procedure | Description | N = 48 evaluations | Rounds at N = 48 |
|---|---|---|---|
| qLogEI (BO) | GP; qLogEI; n₀ = 14, then batches of 4 | 48 | 10 |
| qLogNEI | Identical loop, noisy-EI acquisition | 48 | 10 |
| DoE | 20-run screen, retain 4; 27-run face-centred CCD; 1 confirmation | 48 | 3 |
| doe_ascent | Same, then steepest ascent and relocated CCD (Q56) | up to 200 | variable |
| spread_gp | One Latin hypercube of size n; one GP; nominate arg max μ | n (one shot) | 1 |
| Coordinate descent | Sequential; unpaired; control only | 48 | sequential |

The main experiment (E2) stores **measured-value argmax** (`reported_best_curve`: pick by noisy y, score noiseless f). Surrogate recommendations are computed on the same campaigns (Q34 naïve unconstrained; Q35 in-region). Space-filling arms have no recommendation column on the Hill oracle.

An earlier DoE “best observed” column read the oracle-best point among tested wells rather than the noisy argmax. All measured-value-argmax DoE figures below use the corrected locator (D20; primary-cell mean 0.0958). The superseded 0.0597 is DoE **hidden tested-best**, not measured-value argmax. Both arms’ hidden tested-best columns now exist (Q55/Q57).

### 4.4 Auxiliary experiments

Section 2.4 states why each run exists. The table is the same list with the experimental factors. Identifiers are reproducibility tags, not extra results.

| Experiment | Question | Held fixed | Varied |
|---|---|---|---|
| E1 | Does BO dominate random search? | Standard test functions | BO vs random |
| E2 | Matched-budget comparison on the Hill ensemble | Landscapes, N = 48, best-observed | Procedure |
| Q27 | Same at d = 8 | As E2 | DoE arm (absent from the E2 grid) |
| Q34 | Design versus surrogate | Same 48 evaluations | 2 × 2 of (DoE vs BO design) × (polynomial vs GP) |
| Q35 | Locator, same DoE fit | Fitted quadratic | Best observed vs unconstrained vs constrained argmax |
| Q45 | Design effect without model-dimension confound | Four-factor polynomials on both designs | Design; then surrogate |
| Q42 | Generality off the Hill oracle | Pipeline, four cells | Levy, Rosenbrock, Hartmann6, Ackley |
| Q52 | Cost curves and first hitting times | d = 6, cap 200 | Budget, target, σ. d = 8 not run |
| Q53 | Value of sequential adaptation | Equal evaluation count | spread_gp vs 10-round qLogEI on Q42 families |
| Q54 | Hill one-shot GP, many design draws | Q52 instances and targets | Latin-hypercube draw |
| Q55 / Q57 | Search vs identification | Same E2 campaigns | Locator; acquisition (qLogEI / qLogNEI) |
| Q56 | Sequential RSM | d = 6, cap 200 | Relocation vs `doe_repeat` |
| Q58 | Terminal pick on fixed campaigns | Primary cell | Single / replicate / confirm-top-3 / posterior mean |
| Q59 | Hartmann6 screen on or off | d = 6, N = 48 | 6→4 cut |

Calibration, kernel misspecification, acquisition-optimizer failure rates and related checks are reported in Section 7.

### 4.5 Reconstruction of experimental rounds

Rounds were not logged per landscape. They were reconstructed from evaluation checkpoints using the generating runner (commit `633e74d`). A **round** is one plate cycle: formulate, incubate, read, then choose the next set. BO’s 48 wells are 10 rounds because they arrive in batches of 4 after a 14-point start. DoE’s 48 wells are 3 rounds because the published pipeline is screen, CCD, confirm. A Latin hypercube of 48 is 1 round. This is why a method can use fewer wells and still use more calendar plates.

| Procedure | Initial design | Continuation | Incomplete batches |
|---|---|---|---|
| qLogEI | 14 evaluations = round 1 | batches of 4 | An incomplete batch is charged as a full plate. Rounds = 1 if n ≤ 14, else 1 + ⌈(n−14)/4⌉ |
| DoE | 20+27+1 = 48 | Pipeline repeats at 48, 96, 144, 192 | A partial pipeline is not the method. Rounds = 3 × ⌊n/48⌋ |
| spread_gp / random | n in one shot | none | 1 round at any n |

Artefact: `results/q52-rounds-to-arrival.json`.

---

## 5. Results

Lower regret is better. The argument is three figures. Control-arm tables, the 2 × 2 factorial grid, and the Q42 family tables are in `docs/SUPPLEMENT.md`.

- **Figure 1** (`results/figures/fig1-scoring.html`): DoE versus BO at 48 wells, by scoring rule and noise.
- **Figure 2** (`results/figures/cost-curves.html`): regret versus wells and versus rounds, to 200.
- **Figure 3** (`results/figures/fig3-saddle.html`): why the quadratic is a saddle and why ridge constraints matter.

### 5.1 Matched budget N = 48 (Figure 1)

Both methods spend exactly 48 wells. The tables below score the **same campaigns** several ways. Changing only the terminal decision reverses the ranking. That is the core result.

**Measured-value argmax (single-readout selection).** Pick argmax of noisy y, score noiseless f. One transparent operational rule, not “what a researcher would carry forward.” qLogNEI is co-primary under observation noise (Q57).

#### Measured-value argmax

| Cell | DoE | qLogEI | qLogNEI | DoE − qLogEI | Call vs qLogEI |
|---|---|---|---|---|---|
| d=6, σ=0.25 (primary) | **0.0958** | 0.1553 | 0.1532 | **−0.0595** [−0.0792, −0.0373] | DoE (qLogNEI 0.1532, null vs qLogEI) |
| d=6, σ=0.10 | 0.0892 | 0.0874 | 0.0808 | +0.0018 | null |
| d=8, σ=0.25 | 0.0963 | 0.1247 | 0.1105 | **−0.0284** | DoE |
| d=8, σ=0.10 | 0.0948 | 0.0972 | 0.0849 | −0.0024 | null (qLogNEI 0.0849 vs qLogEI, p = 0.027 uncorrected) |

At the higher-noise condition, the single noisy readout favours sequential DoE over both acquisitions. At lower noise the DoE–qLogEI contrast is null. Measured-value-argmax **verdicts** are the same under qLogNEI (DoE, null, DoE, null). This is **not** yet a claim about where each method looked.

**Hidden tested-best / search quality (Q55, Q57).** R_search = 1 − max_i f(x_i). A lab cannot compute this.

| Cell | qLogEI R_search | qLogNEI R_search | DoE R_search | qLogEI measured-argmax | DoE measured-argmax |
|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0755 | 0.0834 | 0.0597 | 0.1553 | 0.0958 |
| d=6, σ=0.10 | 0.0496 | 0.0435 | 0.0544 | 0.0874 | 0.0892 |
| d=8, σ=0.25 | 0.0702 | 0.0685 | 0.0575 | 0.1247 | 0.0963 |
| d=8, σ=0.10 | 0.0653 | 0.0564 | 0.0500 | 0.0972 | 0.0948 |

Identification gap = measured-argmax regret − R_search. At the primary cell: qLogEI +0.0797 (identifies its own best well 8% of the time); qLogNEI +0.0698 (22%); DoE +0.0361 (12%). DoE − qLogEI on R_search is −0.0158 (p = 0.0067); on measured-value argmax it is −0.0595. **About 73% of the published lead is identification.** Against qLogNEI the measured-argmax lead is −0.0574 and the search lead is **larger** (−0.0237), because noisy EI improves spotting without improving where the campaign looked.

Quiet-assay **tested-best** verdicts are acquisition-dependent and must name the acquisition. In particular, “DoE tested better conditions at d = 8, σ = 0.10, and the readout hid it” is **withdrawn**: that contrast is null against qLogNEI (p = 0.56). Q49’s 61% identification share is LHS at n = 192, not the E2 campaign.

**Naïve unconstrained recommendation (diagnostic, not classical RSM).** Argmax of the fitted quadratic or GP over the whole box. For a saddle-shaped quadratic this is a known failure mode, not “the DoE recommendation.”

#### Naïve unconstrained surrogate recommendation

| Cell | Quadratic (naïve) | GP (BO) | Quadratic − GP | Call |
|---|---|---|---|---|
| d=6, σ=0.25 | 0.4163 | **0.1232** | **+0.2931** | BO vs naïve quadratic |
| d=6, σ=0.10 | 0.4300 | **0.0703** | **+0.3597** | BO vs naïve quadratic |
| d=8, σ=0.25 | 0.3766 | **0.1056** | **+0.2710** | BO vs naïve quadratic |
| d=8, σ=0.10 | 0.4104 | **0.0876** | **+0.3228** | BO vs naïve quadratic |

All four p < 10⁻⁷. Almost all of this swing is the quadratic: a saddle in 200/200 Hill runs, optimized off the region where it was learned. Do not headline this as “BO beats classical RSM.”

**In-region / ridge recommendation (principal classical readout).** Same model; the suggested recipe must lie inside the explored region.

#### In-region surrogate recommendation

| Cell | Quadratic (in-region) | GP (BO) | Quadratic − GP | Call |
|---|---|---|---|---|
| d=6, σ=0.25 | 0.1169 | 0.1232 | −0.0063 | null |
| d=6, σ=0.10 | 0.0856 | 0.0703 | +0.0153 | not confirmatory |
| d=8, σ=0.25 | 0.1148 | 0.1056 | +0.0091 | null |
| d=8, σ=0.10 | 0.0877 | 0.0876 | +0.0001 | null |

In this implementation the GP recommendation already lies inside the sampled region, so BO’s unconstrained and in-region columns coincide. Constraining the quadratic removes the giant BO advantage in three of four cells.

| Cell | Measured-value argmax | Naïve unconstrained | In-region |
|---|---|---|---|
| d=6, σ=0.25 | DoE by 0.0595 | BO vs naïve quadratic by 0.2931 | null |
| d=6, σ=0.10 | null | BO vs naïve quadratic by 0.3597 | not confirmatory (+0.0153) |
| d=8, σ=0.25 | DoE by 0.0284 | BO vs naïve quadratic by 0.2710 | null |
| d=8, σ=0.10 | null | BO vs naïve quadratic by 0.3228 | null |

**Interpretation.** Method ranking is not a property of the acronyms. Measured-value argmax at higher noise favours DoE, and most of that lead is identification among clustered BO samples. Naïve unconstrained quadratic readout favours BO because the saddle extrapolates. Proper in-region RSM is essentially tied. A three-well confirmation protocol (Section 5.8) removes the measured-value-argmax lead entirely.

Sources: `results/e2-grid.json`, `results/e2-doe-d8.json`, `results/q34-factorial.json`, `results/q35-constrained-rsm.json`, `results/d20-rescore.json`, `results/q55-oracle-best.json`, `results/q57-search-vs-id.json`.

### 5.2 Control procedures under measured-value argmax

These tables ask only question 1 (best already-run recipe), now including the controls. The comparison is **procedure minus qLogEI**: negative means that procedure beat BO; positive means BO beat it. Holm correction is applied because several arms are tested against the same BO column in one cell. After Holm, “not significant” means the raw p looked small but is not trusted as a family-wise claim.

Contrasts are procedure minus qLogEI.

**d = 6, σ = 0.25 (primary).**

| Procedure | Mean R | vs qLogEI | p | After Holm |
|---|---|---|---|---|
| DoE | **0.0958** | **−0.0595** | 2.2×10⁻⁵ | DoE superior |
| LHS | 0.1270 | −0.0282 | 0.015 | not significant |
| Coordinate descent | 0.1420 | −0.0133 | 0.34 | null |
| qLogNEI | 0.1532 | −0.0020 | 0.71 | null |
| qLogEI | 0.1553 | — | — | — |
| Sobol' | 0.1724 | +0.0171 | 0.31 | null |
| Random | 0.2216 | +0.0664 | 3.8×10⁻⁵ | BO superior to random |

After multiplicity correction, sequential DoE is the only procedure that dominates qLogEI. qLogEI dominates only random search. The apparent LHS advantage does not survive Holm correction.

**d = 6, σ = 0.10.**

| Procedure | Mean R | vs qLogEI | p | Call |
|---|---|---|---|---|
| qLogNEI | 0.0808 | −0.0066 | 0.18 | null |
| qLogEI | 0.0874 | — | — | — |
| Coordinate descent | 0.0880 | +0.0006 | 0.92 | null |
| DoE | 0.0892 | +0.0018 | 0.69 | null |
| LHS | 0.1027 | +0.0153 | 0.11 | null |
| Sobol' | 0.1210 | +0.0336 | 0.00033 | BO superior |
| Random | 0.1693 | +0.0819 | 6×10⁻⁷ | BO superior |

**d = 8, σ = 0.25.**

| Procedure | Mean R | vs qLogEI | p | Call |
|---|---|---|---|---|
| DoE | **0.0963** | **−0.0284** | 0.0023 | DoE superior |
| qLogNEI | 0.1105 | −0.0142 | 0.17 | null |
| qLogEI | 0.1247 | — | — | — |
| LHS | 0.1627 | +0.0380 | 0.019 | BO superior (uncorrected) |
| Random | 0.1712 | +0.0465 | 1.8×10⁻⁵ | BO superior |
| Sobol' | 0.1804 | +0.0557 | 0.00063 | BO superior |
| Coordinate descent | 0.1926 | +0.0679 | 1.1×10⁻⁶ | BO superior |

**d = 8, σ = 0.10.**

| Procedure | Mean R | vs qLogEI | p | Call |
|---|---|---|---|---|
| qLogNEI | **0.0849** | **−0.0123** | 0.027 | qLogNEI superior to qLogEI |
| DoE | 0.0948 | −0.0024 | 0.43 | null |
| Sobol' | 0.0968 | −0.0004 | 0.94 | null |
| qLogEI | 0.0972 | — | — | — |
| Coordinate descent | 0.1053 | +0.0081 | 0.33 | null |
| LHS | 0.1260 | +0.0288 | 0.0067 | BO superior |
| Random | 0.1272 | +0.0301 | 0.00043 | BO superior |

At low noise the leading four procedures (qLogNEI, qLogEI, coordinate descent, DoE) are indistinguishable at both dimensions. The only systematic movement is the acquisition function at d = 8. At high noise, DoE leads at both dimensions and space-filling designs without a surrogate trail.

### 5.3 Change of terminal decision on a fixed campaign

The campaigns do not change. Only the **point we read off at the end** changes. Δ is naïve-unconstrained-recommendation regret minus measured-value-argmax regret on that same campaign. Positive Δ means “trusting the unconstrained model peak was worse than keeping the well selected by noisy y.” Negative Δ means the model suggested something better than that noisy pick.

Expected-improvement BO is designed to produce negative Δ. A quadratic that is a saddle is designed, in effect, to produce large positive Δ: its unconstrained peak sits on the boundary, outside the region where the polynomial was identified.

| Cell | DoE, best obs. | DoE, unc. rec. | DoE Δ | BO, best obs. | BO rec. | BO Δ | DoE share of abs(Δ) |
|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0958 | 0.4163 | **+0.3205** | 0.1553 | 0.1232 | **−0.0321** | ~90% |
| d=6, σ=0.10 | 0.0892 | 0.4300 | +0.3408 | 0.0874 | 0.0703 | −0.0171 | ~95% |
| d=8, σ=0.25 | 0.0963 | 0.3766 | +0.2803 | 0.1247 | 0.1056 | −0.0191 | ~94% |
| d=8, σ=0.10 | 0.0948 | 0.4104 | +0.3156 | 0.0972 | 0.0876 | −0.0096 | ~97% |

“DoE share of abs(Δ)” is how much of the total |Δ| comes from DoE rather than BO. Values near 90% mean almost all of the terminal-rule switch is on the DoE side: the naïve unconstrained quadratic peak is a disaster relative to its measured-value argmax, while the GP peak is a modest improvement on its measured-value argmax.

The GP recommendation improves on the best observed point in every cell (0.1232 vs 0.1553, 21%; 0.0703 vs 0.0874, 20%; 0.1056 vs 0.1247, 15%; 0.0876 vs 0.0972, 10%), which is the behaviour expected improvement is designed to produce.

A **saddle** means the fitted quadratic has a stationary point that is not a maximum. On a box, the maximum of a saddle lies on the boundary, so an unconstrained polynomial recommendation is forced onto a face or corner. **50 / 50** below is 50 runs (25 landscapes × 2 seeds) in each cell; **200/200** is that count across all four cells.

Classification of the fitted quadratic’s stationary point:

| Cell | Saddle | Interior maximum |
|---|---|---|
| all four | **50 / 50** | 0 |

**200/200.** Unconstrained minus constrained regret at the primary cell: +0.2995 [+0.2790, +0.3228]. The ridge path leaves the design region at radius ≈0.27 versus a corner radius of 0.50.

Constrained recommendation minus best observed (D20-corrected):

| Cell | Constrained − best observed | Call |
|---|---|---|
| d=6, σ=0.25 | **+0.0211** [+0.0105, +0.0315] | polynomial worse than its data |
| d=6, σ=0.10 | −0.0036 [−0.0122, +0.0049] | null |
| d=8, σ=0.25 | **+0.0185** [+0.0094, +0.0287] | polynomial worse than its data |
| d=8, σ=0.10 | −0.0071 [−0.0150, +0.0008] | null |

Asked for an unevaluated point anywhere in the hypercube, the GP improves on its data and the quadratic, being a saddle, nominates a boundary. Inferiority of the constrained quadratic to the best observed well holds at σ = 0.25 only.

### 5.4 Design versus surrogate

The headline DoE-versus-BO comparison mixes three things at once: where the 48 wells were placed (CCD versus adaptive BO), which model was fitted (quadratic versus GP), and which point we read off (best well versus model peak). Q34 unmixes the first two by taking the **same 48 wells** and fitting **both** models to **both** designs. If a GP on DoE wells already beats the quadratic on those same wells, the model is doing work. If a quadratic on BO wells already beats the quadratic on CCD wells, the sampling pattern is doing work.

Because the DoE polynomial uses four factors (after screening) and the BO-side polynomial in Q34 used six, both polynomials were refitted on the same four retained factors (Q45). That is the fair design contrast. Row 6 (six-factor polynomial on BO points) is shown for completeness and is **not** used as a design contrast.

**D-efficiency** is a classical score for “how informative is this design for estimating this polynomial, inside a stated region.” High D-efficiency means a better local map. It does not mean a better suggested recipe outside that region. The two rows of the D-efficiency table ask the question in two geometries: the whole unit box, versus each design’s own explored region.

| Cell of the factorial | d=6, σ=0.25 | d=6, σ=0.10 | d=8, σ=0.25 | d=8, σ=0.10 |
|---|---|---|---|---|
| 1 DoE points, best observed | 0.0958 | 0.0892 | 0.0963 | 0.0948 |
| 2 BO points, best observed | 0.1553 | 0.0874 | 0.1247 | 0.0972 |
| 3 DoE points, polynomial (unconstrained) | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| 4 BO points, GP | 0.1232 | 0.0703 | 0.1056 | 0.0876 |
| 5 DoE points, GP | 0.1993 | 0.2728 | 0.1139 | 0.1168 |
| 6 BO points, six-factor polynomial | 0.5838 | 0.3956 | 0.6972 | 0.6784 |

GP minus polynomial on identical DoE points (cell 5 − cell 3): −0.2171 [−0.2524, −0.1834] at the primary cell; −0.1573 / −0.2628 / −0.2936 at the others; all p ≤ 10⁻⁶.

The six-factor polynomial on BO points (cell 6) confounds design with model dimension and is not used as a design contrast. Predicted numerical failures of a quadratic on BO’s clustered points: 0 in 200 runs. Condition numbers: DoE full second-order matrix 8.1×10¹⁶–1.1×10¹⁸ (singular); BO 2.4×10²–3.9×10³. A full second-order fit on all d factors is feasible on BO data and not on the DoE arm’s 48 points without screening.

Four-factor refit (Q45):

| | d=6, σ=0.25 | d=6, σ=0.10 | d=8, σ=0.25 | d=8, σ=0.10 |
|---|---|---|---|---|
| Polynomial on CCD (four factors) | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| Polynomial on BO points, four-factor refit | **0.3035** | **0.1417** | **0.2519** | **0.1435** |
| Polynomial on BO points, six-factor (Q34) | 0.5838 | 0.3956 | 0.6972 | 0.6784 |
| GP on BO points | 0.1232 | 0.0703 | 0.1056 | 0.0876 |
| Design effect (CCD − BO poly., model fixed) | **+0.1129** | **+0.2883** | **+0.1247** | **+0.2669** |
| Surrogate effect (GP − BO poly., design fixed) | **−0.1803** | **−0.0715** | **−0.1462** | **−0.0559** |

All eight contrasts p ≤ 0.0008. At low noise the design effect is four- to five-fold the surrogate effect. The surrogate effect never changes sign.

D-efficiency of the four-factor model (the model for which stage 2 is constructed):

| Coding | CCD | Adaptive (BO) | Ratio |
|---|---|---|---|
| Common unit hypercube | 4.99×10⁻³ | 1.05×10⁻² | BO 2.1× |
| Each design in its own region | 4.58×10⁻² | 1.05×10⁻² | **CCD 4.4×** |

On identical DoE points a GP recommends a better global condition than a quadratic. On identical four-factor quadratics the clustered BO design recommends a better global condition than the CCD. The CCD is nevertheless 4.4-fold more D-efficient in its own region. In-region D-optimality is not a guarantee of a useful recommendation outside that region.

### 5.5 Standard test functions

The Hill ensemble is a smooth, roughly additive surface with a peak inside the box on every active factor. That is a friendly setting for a local quadratic. Q42 repeats the **same** 48-well pipeline, four cells, and three scores on four textbook optimization functions, to see whether the Hill pattern is special.

Column abbreviations: **A** = best observed; **C unc.** = unconstrained recommendation; **C con.** = constrained recommendation. The winner column is the call for that score.

- **Levy.** Many local bumps. A local quadratic is likely to be a saddle. Used to test a multimodal but still “regular” surface.
- **Rosenbrock.** A long, curved valley. The optimum sits in a trough that a local quadratic does not describe well.
- **Hartmann6.** Six local maxima; the global one is easy to miss. Used as a **deceptive** surface. The stored pipeline keeps four factors. Q59 reruns d = 6 **without** that cut.
- **Ackley.** The true best recipe is the **centre of the box**. A face-centred CCD evaluates the centre on purpose, so DoE is handed the answer. The comparison is void: it tests the CCD’s centre point, not DoE versus BO as optimizers.

Hartmann6 at d = 8 is the six-dimensional function with two extra dummy axes. Best-observed DoE figures use the corrected locator (best evaluated well).

**Levy results.** Saddle in 25/25 runs at three cells; 22/25 at d=6, σ=0.10.

| Cell | DoE A | BO A | A | DoE C unc. | BO C | C unc. | DoE C con. | C con. |
|---|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0392 | 0.1156 | DoE | 0.5598 | 0.0794 | BO | 0.0791 | null |
| d=6, σ=0.10 | 0.0241 | 0.0754 | DoE | 0.4559 | 0.0562 | BO | 0.0696 | null |
| d=8, σ=0.25 | 0.0494 | 0.1290 | DoE | 0.4704 | 0.0647 | BO | 0.0663 | null |
| d=8, σ=0.10 | 0.0220 | 0.0787 | DoE | 0.4151 | 0.0664 | BO | 0.0607 | null |

Unconstrained − constrained DoE: +0.35 to +0.48.

**Rosenbrock results.** Saddle in 25/25 at all four cells.

| Cell | DoE A | BO A | A | DoE C unc. | BO C | C unc. | DoE C con. | C con. |
|---|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0328 | 0.0700 | DoE | 0.3026 | 0.0388 | BO | 0.0369 | null |
| d=6, σ=0.10 | 0.0156 | 0.0430 | DoE | 0.2444 | 0.0157 | BO | 0.0254 | not confirmatory (p=0.052) |
| d=8, σ=0.25 | 0.0320 | 0.0823 | DoE | 0.3018 | 0.0419 | BO | 0.0357 | null |
| d=8, σ=0.10 | 0.0174 | 0.0580 | DoE | 0.2549 | 0.0195 | BO | 0.0262 | null |

Unconstrained − constrained DoE: +0.22 to +0.27. Constrained recommendation is null at six of eight Levy/Rosenbrock cells.

**Hartmann6 results.** Saddle in 25/25 at all four cells. No terminal-rule reversal: BO leads on every score. The stored pipeline retains four factors.

| Cell | DoE A | BO A | DoE − BO (A) | DoE C unc. | BO C | DoE C con. | Call, every terminal rule |
|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.5623 | **0.2984** | +0.2460 | 0.9008 | 0.2695 | 0.5449 | BO |
| d=6, σ=0.10 | 0.5428 | **0.1938** | +0.3460 | 0.8985 | 0.1740 | 0.5223 | BO |
| d=8, σ=0.25 | 0.6393 | **0.3134** | +0.3189 | 0.8792 | 0.2992 | 0.6309 | BO |
| d=8, σ=0.10 | 0.6534 | **0.2370** | +0.4134 | 0.8751 | 0.2269 | 0.6442 | BO |

All screened best-observed contrasts p < 0.0001, favouring BO. Q59 asks whether that win is an artefact of discarding two active factors. At d = 6 an unscreened face-centred CCD plus confirmation is 48 wells. Removing the screen makes DoE **worse** by 0.206 (σ = 0.25) and 0.207 (σ = 0.10); BO’s lead widens 1.55–1.78× against both qLogEI and qLogNEI. Forty-seven wells spread over [0,1]⁶ are a thin covering; 27 wells in a subregion after screening is a better use of the same budget on a narrow peak. **The screen was helping the classical arm, not handicapping it.** At d = 8 an unscreened second-order fit is arithmetically impossible inside 48 wells (45 terms, 35-run CCD). That impossibility is why the screen exists.

On Hartmann6 the unconstrained quadratic recommendation stays ~0.87–0.90 even when the CCD spans the whole box (unscreened rule C 0.8695 / 0.8810 versus screened 0.9008 / 0.8985). Extrapolation out of a sub-box is therefore **not** the mechanism: a quadratic cannot represent six local maxima. The Hill saddle-extrapolation account and the Hartmann misspecification account should not be lumped.

**Ackley.** The global minimizer is the centre of the box. A face-centred CCD evaluates the centre by construction. Best-observed DoE regret is ~0–0.013; BO is 0.56–0.76. Constrained and unconstrained recommendations agree to four decimals. The comparison is void under every terminal rule. Of 350 Q42 stationary-point classifications, 103 were interior maxima, concentrated on Ackley: a negative-definite Hessian makes unconstrained and constrained recommendations coincide.

Which procedure is ahead is therefore landscape-dependent. On saddle-like surfaces, DoE leads under measured-value argmax and BO under naïve unconstrained recommendation. On Hartmann6, BO leads under every terminal rule, and that lead is **not** a 6→4 screening artefact at d = 6. No universal ranking is claimed.

### 5.6 Cost curves

Question 3. A snapshot at 48 wells cannot say who is cheaper. Campaigns were extended to a cap of 200 wells (d = 6 only; σ = 0.10 and 0.25). The original DoE curve is `doe_repeat`: the 48-well pipeline again, **no steepest ascent**. Q56 adds `doe_ascent` (screen → CCD → steepest ascent → recenter). Under measured-value argmax the two sequential methods are near-indistinguishable on arrival (Section 6). Eight-factor cost curves were not computed. Figure 2 is generated from stored JSON and reports **P(T ≤ N)** so failure to hit stays in the denominator.

Lead with **hit probability P(T ≤ N)** — the Hits/25 columns below. Failure to hit stays in the denominator. Medians among hits are secondary and are not comparable across rows with different hit counts. A method with few successes can look fast among its successes.

The **cost curve** is median regret plotted against wells and, separately, against plate rounds (`results/figures/cost-curves.html`). **Arrival** (first hitting time) is one horizontal cut: pick τ, then record hits out of 25 and, among hits only, median wells and rounds. Arrival uses measured-value argmax. Rounds are reconstructed as in Section 4.5.

**Why a fold-savings ratio is not reported.** A paired “DoE used X times as many wells as BO” needs landscapes where **both** methods hit the target. If DoE never hits on most landscapes, those pairs do not exist (right-censoring). That ratio is undefined at every registered pairing: DoE is right-censored on 72–100% of landscapes under recommendation-score targets, and no landscape pair hits the tightest best-observed targets (0.03, 0.02, 0.01). Cost curves and arrival counts are the quantities that remain defined.

**How to read the arrival tables.** “Hits” is successes out of 25. “Eval.” and “rounds” are medians **among hits only**, so rows with different hit counts are not comparable as “who is faster.” “disc. BO:DoE” is a sign count among landscapes where **both** hit: how many times BO used fewer wells than DoE, versus the reverse. Holm correction is over ten BO-versus-DoE arrival tests; one cell survives: σ = 0.10, τ = 0.10.

**Low noise (σ = 0.10).**

| τ | BO hits | BO eval. | BO rounds | DoE hits | DoE eval. | DoE rounds | spread_gp hits | spread eval. | spread rounds | disc. BO:DoE | p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.12 | 24/25 | 32 | 6 | 20/25 | 48 | 3 | 25/25 | 20 | 1 | 5:1 | 0.2188 |
| **0.10** | **24/25** | **32** | **6** | **13/25** | **48** | **3** | **24/25** | **32** | **1** | **11:0** | **0.0010** |
| 0.08 | 22/25 | 74 | 16.5 | 13/25 | 96 | 6 | 23/25 | 32 | 1 | 10:1 | 0.0117 |
| 0.05 | 18/25 | 100 | 23 | 7/25 | 96 | 6 | 16/25 | 48 | 1 | 15:4 | 0.0192 |

Among the 13 landscapes both BO and DoE hit at τ = 0.10: BO used fewer evaluations on 9, DoE on 4; DoE used fewer rounds on 8, BO on 5.

**Noisy assay (σ = 0.25).**

| τ | BO hits | BO eval. | BO rounds | DoE hits | DoE eval. | DoE rounds | spread_gp hits | spread eval. | spread rounds | disc. | p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.15 | 21/25 | 32 | 6 | 23/25 | 48 | 3 | 25/25 | 20 | 1 | 1:3 | 0.6250 |
| 0.10 | 14/25 | 82 | 18.5 | 11/25 | 96 | 6 | 21/25 | 48 | 1 | 7:4 | 0.5488 |
| 0.08 | 10/25 | 125 | 29 | 6/25 | 72 | 4.5 | 17/25 | 48 | 1 | 7:3 | 0.3438 |

No contrast survives Holm correction. Sequential BO versus repeated-CCD DoE hitting rates are compatible with equality at the noisy assay.

**One-shot GP across targets, not only τ = 0.10.** spread_gp is one Latin hypercube, one GP fit, one round. It is not a footnote to the τ = 0.10 cell.

| σ | Target τ | BO hits | BO eval. / rounds | spread_gp hits | spread eval. / rounds |
|---|---|---|---|---|---|
| 0.10 | 0.12 | 24/25 | 32 / 6 | **25/25** | 20 / 1 |
| 0.10 | 0.10 | 24/25 | 32 / 6 | 24/25 | 32 / 1 |
| 0.10 | 0.08 | 22/25 | 74 / 16.5 | **23/25** | 32 / 1 |
| 0.10 | 0.05 | **18/25** | 100 / 23 | 16/25 | 48 / 1 |
| 0.25 | 0.15 | 21/25 | 32 / 6 | **25/25** | 20 / 1 |
| 0.25 | 0.10 | 14/25 | 82 / 18.5 | **21/25** | 48 / 1 |
| 0.25 | 0.08 | 10/25 | 125 / 29 | **17/25** | 48 / 1 |

At low noise the match with 10-round BO holds at 0.12, 0.10 and 0.08; it does **not** hold at the tighter target 0.05 (16 vs 18 hits). At the noisy assay, one-shot GP hits **more** landscapes than sequential BO at every reported target, still in one round. Medians among hits are not comparable across rows with different denominators. Q54 repeats Hill at five draws (Section 5.7). Eight-factor cost curves were not computed.

### 5.7 Sequential adaptation versus a one-shot GP

Q53 asks whether BO’s extra plates are doing work, or whether a GP fit on a single space-filling batch would have been enough. **spread_gp** places all wells at once, fits one GP, and reads the peak: one round. **qLogEI** uses the same well count but ten adaptive rounds. If they tie, sequential search is not buying sample efficiency on that surface. If spread_gp is worse, adaptation is doing work (typically on deceptive surfaces such as Hartmann6).

On the Hill ensemble, one-shot spread_gp was indistinguishable from 10-round qLogEI at N = 48 in the original Q52 draw. The same evaluation count on the Q42 families, with five design draws and a prediction fixed before the runner existed, held in 8 of 8 cells: spread_gp is inferior on Hartmann6.

| Family | spread_gp versus 10-round qLogEI |
|---|---|
| Levy, Rosenbrock | null |
| Hartmann6, Ackley | inferior, large gap |

**Q54 has now re-run Hill at five draws, so the two are poolable.** The verdict is stable in 20 of 22 cells; the two that move (σ = 0.25 unconstrained recommendation at τ = 0.05, σ = 0.10 measured-value argmax at τ = 0.03) are exactly the two with the largest design SDs, and Q52 had drawn at the favourable extreme in both. At σ = 0.25 under model recommendation, one-shot GP **beats** 10-round qLogEI at τ = 0.12, 0.10 and 0.08, unanimously across draws (e.g. 24.4/25 versus 16/25 at τ = 0.10). Sequential BO therefore purchases robustness on deceptive surfaces. On this smooth Hill surface it does not purchase a unique well-count win relative to one-shot GP.

### 5.8 Protocol sensitivities (Q57–Q59)

The findings above were then attacked at their weakest points. Same campaigns where stated; only the acquisition, the final pick, or the screening cut moves.

**qLogNEI as co-primary (Q57).** Observations are y = f(x) + ε. Noisy expected improvement is the natural comparator; Rummukainen used it. qLogNEI is better than qLogEI at all four cells, so this is the harder test for a DoE lead. At σ = 0.25, on both locators, both acquisitions give the same winner. Primary-cell measured-value argmax: DoE − qLogNEI = −0.0574 [−0.0776, −0.0376]. Hidden tested-best: −0.0237 [−0.0379, −0.0111]. qLogNEI identifies its own best well 22% of the time versus qLogEI’s 8% and still does not close the single-readout gap. Quiet-assay **tested-best** verdicts flip with the acquisition and must name it. The d = 8, σ = 0.10 “DoE searched better and the assay hid it” sentence is withdrawn.

**Selection-rule sensitivity (Q58).** The same primary-cell campaigns, four final picks.

| Terminal pick | Extra wells | qLogEI | DoE | DoE − BO | vs published −0.0595 |
|---|---|---|---|---|---|
| Single noisy readout (published) | 0 | 0.1553 | 0.0958 | **−0.0595** [−0.0797, −0.0375] | 1.00× |
| Replicate every well; pick by mean y | +48 | 0.1447 | 0.1185 | −0.0262 [−0.0446, −0.0079] | 0.44× |
| **Confirm top 3; decide by the confirmation reading alone** | **+3** | 0.1446 | 0.1437 | **−0.0009** [−0.0263, +0.0253] | **0.01×** |
| Posterior mean at visited wells | 0 | 0.1387 | 0.1160 | −0.0227 [−0.0438, −0.0022] | 0.38× |

Wilcoxon governs the yes/no call (Q20). Confirm top-3: p = 0.92, null. Posterior mean: Wilcoxon p = 0.11 (null) while the bootstrap interval excludes zero; both numbers are reported. Confirmation moves BO from 0.1553 to 0.1446 and DoE from 0.0958 to **0.1437** — it makes the classical arm worse — because a protocol that **re-decides from a fresh single reading** throws away the CCD’s already-trustworthy first readout. The tie is a property of “keep whichever of the three confirms best,” not of averaging original and confirmation; that variant was not run.

A laboratory that confirms its top three candidates before committing sees **no difference** between the methods at the primary cell. The published −0.0595 remains a fact about single-readout selection.

**Figures.** Figure 1 is generated from stored artefacts; cells that were never measured are left blank. The build fails if winner-reversal by terminal rule disappears (it holds in 3 of 4 cells). Figure 2 no longer types the arrival table by hand and leads with P(T ≤ N).

Sources: `results/q57-search-vs-id.json`, `results/q58-selection-sensitivity.json`, `results/q59-hartmann-no-screen.json`.

---

### 5.9 The design space as a second deliverable (K6, P6–P8)

Every result above scores a campaign by the quality of **one nominated recipe**. A manufacturing batch record does not ask for a point. ICH Q8 asks for a **design space** — a certifiable range per parameter — and a laboratory cannot pipette a setpoint to arbitrary precision every batch. SPADE (`docs/SPADE-SPEC.md`) is a two-plate protocol written against that deliverable. Scoring the same campaigns both ways reorders the arms, and the reordering is the result.

**The two objects rank methods differently, and the evidence is arm-level reversal, not a count.** An earlier version of this section reported that the map ranking reproduced the regret ranking in none of 24 cells. That statistic is withdrawn: six of the 24 cells have no ordering at all (every arm ties to within 1e-15), so the denominator is 18 rankable cells, and more importantly two independent orderings of eight arms coincide by chance only once in 40,320 — "the orderings are not identical" is close to uninformative. What survives is stronger and specific: **the same arm is called best by one metric and worst by the other on the same data.** On K6 (Hill, 9,600 rows, 8 arms) `doe` is first on regret at 0.0958 and **last on map AUC in 23 of 24 cells**; on the cross-family programme (`results/p6-families/`, 16 cells, 96,000 rows) `doe` is AUC-best in 27 of 92 cells and symmetric-difference-**worst in 36 of 92**. A metric that ranks one arm first and last on identical campaigns is not measuring the same deliverable.

**Screening buys the recipe and costs the map — on three of four families, and more at d = 8.** The 6→4 screen that gives the classical arm its better single recipe confines the response surface to a sub-box, and a range cannot be stated for the factors it drops. This is not a Hill artefact: the effect reproduces on three of four external families and **strengthens at eight factors**. It is also not the whole mechanism. A registered re-score (Q59, `results/q59-map-rescore.json`) turned the screen off and the classical arm still loses the symmetric difference to every spread arm — `doe_unscreened − lhs` = **+0.0264** [+0.0208, +0.0327], Holm p = 7.8e-12. The screen accounts for roughly a fifth to a quarter of the map deficit; the response-surface model accounts for the rest.

**The classical arm fails its own community's diagnostics.** Scored with the RSM toolkit rather than against BO, the 48-well classical campaign is rank-deficient for the model it reports in **50 of 50** campaigns, its confirmation run over-predicts in **25 of 25** — above the global maximum in half of them — and its calibration is **0.2296 against 0.0289–0.0443 for every other arm, 5.2× worse than the nearest.** This claim requires SPADE to win nothing, and it is the strongest result in the design-space programme.

**SPADE buys sharpness and does not buy reliability.** The Murphy decomposition (`results/p7-murphy.json`, 12,000 rows, 10 arms) was promoted to primary because AUC cannot see calibration, and the first thing it did with SPADE in scope was catch SPADE. Ranked over nine arms:

| arm | calibration (lower better) | refinement (higher better) | AUC |
|---|---:|---:|---:|
| `sobol` | **0.02893** (1st) | 0.01142 (5th) | 0.7270 |
| `versionb` (SPADE) | 0.03593 (6th) | **0.01506** (1st) | **0.7583** (1st) |
| `versionb_predictive` | 0.03532 (5th) | 0.01436 (2nd) | 0.7529 |
| `versionb_random` | 0.03846 (7th) | 0.01288 (3rd) | 0.7442 |
| `doe` | 0.22959 (9th) | 0.00235 (9th) | 0.5960 |

SPADE produces the **most informative regions in the study and probabilities of below-average reliability.** The band is narrow — 0.0353–0.0385 against 0.0289–0.0443 across all non-`doe` arms — so this is not a kill, but every claim resting on the calibrated half must carry it.

**The certificate off Hill: two distinct failure modes.** P8 (`results/p8-certificate-families.json`, 1,000 campaigns, 24,000 rows, 0 gate failures) is the first measurement of SPADE's certificate on any family but Hill — the cross-family map programme computes no certificate column at all. Five families at 4,096 draws:

| family | cells that certify | mean α\* | containment |
|---|---:|---:|---|
| `ackley` | **0 of 24** | 0.0000 | declines — nothing to be right about |
| `hartmann6` | ~0 of 24 | 0.0559 | declines |
| `hill` | 15 of 24 | 0.8591 | no cell below nominal |
| `levy` | 22 of 24 | 0.8745 | **2 cells below nominal, Holm-significant** |
| `rosenbrock` | 23 of 24 | 0.9351 | **1 cell below nominal, Holm-significant** |

Three of 64 scored cells fall below nominal and survive Holm across all 64, all at γ = 0.99: levy at τ_frac 0.60 containing 34/49 = **0.694** (Holm p = 6.05e-07), rosenbrock at the same cell 37/50 = **0.740**, levy at τ_frac 0.75 37/48 = **0.771**.

Conflating the two modes loses both. `ackley` and `hartmann6` **decline to certify** — that is not a calibration failure. `levy` and `rosenbrock` **answer, and at γ = 0.99 answer wrong**. So **the families that certify most readily are the ones whose certificates are least trustworthy, and Hill is the only family that is both willing and calibrated** — which is the family this study is built on, and must be stated as a limit rather than discovered by a reader.

An earlier withdrawal is corrected rather than reinstated. A prior kill on Hill at 512 draws was traced (F3, `results/f3-draw-sweep.json`) to an estimator artefact: all four sub-nominal cells reach nominal by 1,024 draws, and at 4,096 no Hill cell is below nominal. That withdrawal was correct **as a statement about Hill**. P8 shows the effect is real elsewhere. The registered prediction that the bias would scale with the candidate scan **failed** — 16 and 64 candidates give identical containment — so the mechanism is Monte Carlo error at low draw counts, not a winner's curse over candidates.

**What a laboratory would actually choose on.** Mean regret and mean rank both compress SPADE to "middling"; the performance profile shows what kind. **SPADE is within 3× of the best method on 70% of problems and wins outright on 2%. `doe` shares the 2% win rate, is within 3× on only 22%, and fails to reach even 10× on 42%.** For a laboratory committing one protocol to one plate, that tail is the decision, and no mean-based metric in this study reports it.

**Rounds are the uncontested axis.** Two plate rounds against three for sequential RSM and ten for batch BO. At six-day passages that is roughly a month against six weeks against five months, at matched well count.

> **What may be claimed.** No method wins both objects. Scored as a design space the ranking reorders, the classical arm fails four of its own diagnostics, and a two-plate spread protocol produces the sharpest regions in the study at 2 rounds instead of 3 or 10, with simple regret at parity. **What may not.** That SPADE *beats* BO or RSM on regret — under a posterior-mean rule it **matches**, and the registered bar it was tested against mixes estimands, so the like-for-like verdict is parity and not a win. That its probabilities are well calibrated — they are mid-field. That its certificate is established off Hill — on two families it fails at γ = 0.99 and on two others it declines to certify at all.

**The prospective confirmatory study narrows the method claim.** Everything above is a re-score of stored campaigns. A separate registered study (`spade-final-2026-08-23`) runs SPADE **as a method** — three SPADE arms, causal controls, a pre-run regime classifier, seven conditions and a ten-item kill ledger committed before the result files existed. The completed merge contains **99,601 records**: 92,400 original rows, 7,200 `doe_unscreened` rows at the six-factor conditions, and one structured declaration that an eight-factor unscreened second-order design is infeasible within 48 wells. Four kills pass and six fail:

| kill | claim under test | final verdict |
|---|---|---|
| **KF-1** | certificate valid prospectively under cross-fit | **PASS, narrowly stated** — no confirmatory cell is demonstrably below nominal; the weakest has only 13 non-empty certificates, so this is failure to reject under-coverage, not proof of validity |
| **KF-2** | certificate validity extends beyond Hill | **FAIL** — the Hartmann confirmatory family is not uniformly clean, so the claim narrows to Hill |
| **KF-3** | targeted plate 2 earns its complexity | **FAIL** — `m0` does not beat random plate-2 placement: **−0.0019** [−0.0062, +0.0026], p = 0.41 |
| **KF-4** | the second plate produces a practically meaningful map gain | **FAIL** — the measured gain over plate 1 is **+0.0117** [+0.0074, +0.0156], p_adj = 1.3e-04, below the 0.02 SESOI and with eight extra wells |
| **KF-5** | m > 0 lowers regret safely | **FAIL** — **−0.0028** [−0.0076, +0.0021], p = 0.31: a trade-off, not an improvement |
| **KF-6–KF-8** | competitive target-regime map and regret performance | **PASS** — competitiveness/parity, never superiority |
| **KF-9** | all analysed primary cells are certifiable in principle | **FAIL** — 4,400 of 23,600 primary-γ rows at or above the certifiability ceiling reached the analyser |
| **KF-10** | empty-set degeneracy does not explain a pass | **FAIL** — 8 of 44 raw-PASS cells certify nothing in more than half their campaigns and are downgraded to inconclusive |

KF-3 is the consequential mechanism result. **The boundary-targeted second plate does not outperform random placement of the same eight wells at the Hill target.** The registered follow-up `spade-kf3-followup-2026-08-24` then tested two plausible repairs in 400 fresh campaigns. An error-volume-aware acquisition and a diversity-penalized batch selector are both slightly worse than random at the Hill target (+0.00146 and +0.00342 symmetric-difference error). On the harder Hartmann condition they improve on random by 0.00825 and 0.01722, respectively, but both remain below the registered 0.02 practical-effect bar. Both repairs therefore **FAIL**, and the gated combined arm is **MOOT**. Earlier decomposition points in the same direction: 74–85% of SPADE's surviving-threshold margin over qLogNEI came from the space-filling first plate, not the second. The data therefore separate the **architecture** from the **mechanism**: a two-round spread-and-follow-up workflow can remain competitive on map and regret, but none of the three tested targeting rules earns a causal advantage at an eight-well second-round budget. The unmeasured possibility is a larger break-even second-round budget.

**Implementation scope.** These verdicts apply to the SPADE implementation that exists, not every stage in its founding specification. Plate 1 uses plain LHS rather than the specified strength-2 OA-LHS; the replicate-pooled noise estimator proposed to address calibration was never built; and Stage 0 covariate adjustment was scoped out because the required data do not exist. These omissions do not reverse the recorded results, but they prevent the paper from treating the current calibration and design-lottery behaviour as immutable properties of the architecture.

**Scope.** The re-scored programme, the prospective seven-condition study and the KF-3 follow-up are separate evidence bodies and must not be pooled. The frozen regime detector failed on both held-out families (0 of 50 each), so the protocol has no working automatic landscape-scope gate. `doe_unscreened` is now implemented and run at every six-factor condition; at eight factors it is structurally unavailable because a replicated full second-order CCD cannot fit within 48 wells. The raw condition artefacts remain absent from a clean checkout even though the committed decision artefacts are present, so release-level reproducibility is not yet complete.

Sources: `results/k6-analysis.json`, `results/p6-families/` (8 shards + `results/p6-families.meta.json`, read via `scripts/load_p6_families.py`), `results/p7-murphy.json`, `results/p8-certificate-families.json`, `results/f3-draw-sweep.json`, `results/q59-map-rescore.json`, `results/versionc-kills-s010.json`, `results/versionc-kills-s025.json`, `results/final-spade-kill-ledger.json`, `results/final-spade-regret-pareto.json`, `results/kf3-followup-analysis.json`; consolidated report `docs/SPADE-RESULTS-AND-ANALYSIS.md`; chronological records `docs/FINDINGS-SPADE.md` and `docs/FINDINGS-SPADE-FINAL.md`; registrations `docs/SPADE-FINAL-SPEC.md` and `docs/SPADE-KF3-FOLLOWUP-SPEC.md`.

---

## 6. Discussion

The contribution is not that BO and RSM “address different scientific questions.” Rummukainen already states that RSM maps a region while BO concentrates near promising conditions. Lapierre and Ndahiro already report executed media/bioprocess comparisons. Narayanan already reports large experiment-count reductions against **predicted** DoE sizes. Synthetic BO benchmarks already exist. The best-observation versus posterior-recommendation distinction is already in the noisy-EI literature.

What this study isolates is that **published BO-versus-DoE conclusions are not invariant to the evaluation protocol.** Under identical budgets and identical latent landscapes, changing only the terminal decision can reverse the apparent winner. Design geometry, surrogate class, noise-induced identification error, allowed extrapolation, and well-versus-round cost can then be separated. Both Narayanan’s resource-planning claim and Rummukainen’s matched-budget null can be correct because their denominators and terminal decisions differ; the paper does not treat prior savings claims as “wrong.”

Figure 1 is winner reversal on one synthetic ensemble: measured-value argmax at higher noise favours DoE; naïve unconstrained quadratic favours BO; in-region RSM is a tie. Figure 2 is cost in two currencies (wells and rounds). Figure 3 is why the unconstrained quadratic is a saddle, not a third method. Q34/Q45 show a GP on DoE points already dominates the quadratic, and a four-factor quadratic on BO points already dominates the same quadratic on the CCD — so sampling geometry and surrogate class are separately measurable. The CCD remains the more D-efficient design in its own region.

The giant 0.27–0.36 gap is a **diagnostic of invalid extrapolation**, not a fair classical-RSM loss. NIST / Box–Wilson RSM includes canonical analysis, ridge analysis, steepest ascent and relocation. Q56 now answers “is BO more efficient than sequential classical RSM?” and the answer is rule-dependent: under **measured-value argmax the two are near-indistinguishable** — no arrival contrast survives Holm over all 26 tests, only the tightest target (σ = 0.10, τ = 0.05) survives within the rule-A family of ten, and the one cell Q52 reported as surviving (σ = 0.10, τ = 0.10) falls to Holm 0.0703 within its own family once the classical design may relocate. Under **naïve unconstrained recommendation BO still wins every cell**, though relocation triples to sextuples the classical arm's chance of reaching a target at all. The concession that the long-run curve was biased in BO's favour was therefore load-bearing, and removing it cost BO its single surviving arrival result.

### Decision guide for a laboratory

Use this only as far as the benchmark reaches: a constructed Hill-like surface, six or eight factors, 48–200 wells, higher-noise / lower-noise conditions 0.25 / 0.10, no wet-lab confirmation. qLogNEI is co-primary for search versus identification (Q57). Sequential RSM with relocation exists (Q56).

1. **Need a map of a planned region, or may change the criterion later.** Run classical DoE (screen + CCD). That is what the CCD is D-efficient for. Do not read the unconstrained polynomial peak as the answer; it was a saddle in 200/200 Hill runs (Figure 3). Use in-region / ridge.
2. **Will select by a single noisy readout (measured-value argmax), higher-noise condition.** DoE’s noisy argmax had better true f than qLogEI and qLogNEI. About 73% of the 0.0595 lead is identification, not search (Q55/Q57).
3. **Will confirm a shortlist before committing.** Confirming the top three wells on the same campaigns removes the primary-cell lead (−0.0595 → −0.0009). A laboratory that does that sees no difference at 48 wells under this protocol. Averaging original and confirmation readings was not run.
4. **Same single-readout rule, lower-noise condition.** DoE and qLogEI were indistinguishable at 48 wells.
5. **Willing to try an unconstrained model peak anywhere in the box.** Do not use the unconstrained quadratic when canonical analysis diagnoses a saddle. The GP improved 10–21% on its own measured-value argmax; the naïve quadratic did not. On Hartmann6 the quadratic stays bad even when it cannot extrapolate: misspecification, not a sub-box.
6. **Willing to try a suggested well only inside the explored region.** In-region GP and in-region quadratic were tied in three of four cells.
7. **Rounds are expensive (incubations, not wells).** Prefer DoE (3 rounds at 48 wells) or a one-shot Latin hypercube plus one GP (1 round). Sequential BO is 10 rounds at the same well count. Q54: one-shot is stable in 20 of 22 cells.
8. **Wells are expensive, rounds are cheap, surface believed smooth.** Lead with hit probability. One-shot GP beats 10-round BO on the model recommendation at σ = 0.25. Do not carry that to a deceptive surface (Q53).
9. **The surface may be deceptive (Hartmann6-like).** Sequential BO led under every score. Removing the 6→4 screen makes DoE worse, not better (Q59). At d = 8 an unscreened CCD does not fit in 48 wells.
10. **Campaign will continue past 48 wells with “DoE” as comparator.** Sequential RSM with relocation exists (Q56). Under measured-value argmax it matches qLogEI on arrival — **do not claim BO is cheaper on that rule.** Under an unconstrained model recommendation BO still wins every cell.

The only defined fold-reductions are at σ = 0.10 under the **unconstrained** rule, where qLogEI needs 0.09–0.23 of sequential RSM's wells (Q56). Read them as a statement about *when each arm can first answer* — the classical pipeline cannot speak before 53 wells, qLogEI has a posterior after 14 — not as search efficiency. Under measured-value argmax every defined ratio is 0.73–1.02, i.e. **no saving at all.** Rule-C ratios against the non-relocating `doe_repeat` remain undefined: it is censored above 50% everywhere.

**Venues after the critical runs.** Machine Learning: Science and Technology (benchmark category), Digital Discovery (self-driving-lab evaluation protocol), Chemometrics and Intelligent Laboratory Systems (evaluation confound, not a routine application). Biotechnology and Bioengineering only if biological grounding is strengthened (real emulator or wet-lab). Not Nature Communications on the current synthetic axis.

---

## 7. Limitations and robustness checks

The latent function is constructed, not identified from endothelial measurements. Hall/Ogle (2025) is **structural inspiration** (factor count, 6→4 screen), not a fitted endothelial surface. Digitized stage-2 data resolve an interior peak on one of four proteins. Replay on digitized medians is underpowered (minimum detectable effect 0.68). GP posterior coverage is below the nominal 95% in every cell (worst latent coverage 0.764); adding observation noise recovers predictive coverage of approximately 0.90–0.92.

Q54–Q59 closed the registered revision workstreams (Section 5.8). What remains: unconstrained long-run “model recommendation” for `doe_ascent` is still not in-region ridge; Q58’s tie is for confirmation-alone, not averaged original-plus-confirmation; cost curves were not computed at d = 8; d = 8 Hartmann cannot be unscreened inside 48 wells; Figure 3 still needs the same generate-from-JSON discipline as Figures 1–2 if it is hand-authored; Narayanan / Lapierre / Ndahiro PDFs should be re-read before submission. Q49’s 61% identification share is LHS at n = 192, not E2. Coordinate descent is unpaired. No wet-lab validation.

**Design-space limitations (Section 5.9).** The re-scored programme, the prospective study `spade-final-2026-08-23` and the registered KF-3 follow-up are separate evidence bodies and must not be quoted as one. Six of ten prospective kill conditions fail; the registered consequence is a narrowed claim, not suppression. The consequential mechanism result survives two attempted repairs: original straddle targeting, error-volume-aware acquisition and diversity-aware batching all fail to beat random placement by the registered 0.02 margin at the Hill target. The repairs show smaller, statistically non-null Hartmann gains, but still miss that practical bar; the combined repair is therefore moot. The `doe_unscreened` comparator is now implemented at every six-factor condition, closing the earlier NOT_RUN gap, and the prospective cross-family certificate kill is adjudicated **FAIL** rather than unresolved. Certificate evidence remains family-dependent: at 4,096 draws no Hill cell is below nominal, Levy and Rosenbrock fail at γ = 0.99 in three of 64 scored cells, and Ackley and Hartmann6 usually decline to certify. SPADE is mid-field on calibration while first on refinement, so its sharpness claim is better supported than its reliability claim. The frozen regime detector fails on both held-out families (0 of 50 each), Stage 0 is unmeasured, the specified OA-LHS and replicate-pooled noise estimator are unimplemented, and a d = 8 unscreened CCD is arithmetically impossible inside 48 wells. Finally, the committed decision artefacts are present but the ignored raw prospective condition files are absent from a fresh checkout; implementation tests passing is not yet a self-contained reproducible release.

Robustness checks (not headline): an additive kernel raised R² from 0.375 to 0.744 with regret change 0.0015 (p = 0.71); a “better” lengthscale prior worsened automatic relevance determination; acquisition-optimizer failures were 4/3400 = 0.118% against a 1% threshold set in advance; initial-design size had no effect at the primary cell; 0 of 10,000 permutations matched the surrogate-effect magnitude; design-averaged BO remained ahead of a lucky LHS on 25/25 landscapes (p = 6.0×10⁻⁸).

Excluded from the claims of this paper: two voided E2 runs (path-best scoring; unpaired initial design); the figure −0.0708 from an untracked grid; a retracted savings-crossover at 0.15; Ackley as a DoE–BO cell; multi-fidelity predictions that failed (Q47); extrapolation-detection (E4) as a headline, where pooled and registered cells disagree in sign.

---

## 8. Conclusions

A synthetic Hill benchmark, **structurally inspired by** a published iPSC-to-endothelial ECM screen (not fitted to cell data), was used to hold campaign geometry, surrogate class, terminal decision, noise, and cost unit under experimental control.

1. Under **measured-value argmax** at the higher-noise condition, sequential DoE attained lower simple regret than qLogEI by 0.0595 at six factors and 0.0284 at eight. Stored qLogNEI does not remove that DoE lead. At lower noise the qLogEI contrast was null. **Q55/Q57 decompose it:** scored on what each arm actually tested, the same contrasts are −0.0158 and −0.0127, so **55–73% of the lead is identification rather than search.** Both arms identify their own best well only 2–18% of the time, and BO’s identification gap is significantly the larger at both σ = 0.25 cells (+0.0436, p = 0.0004 at d = 6). The direction never reverses between the two locators; the magnitude collapses. **Q57 re-runs all of this with qLogNEI co-primary:** the higher-noise verdicts are unchanged under both acquisitions, and the tested-best advantage at the primary cell is in fact *larger* against qLogNEI (−0.0237). qLogNEI does identify its own best well far more often (22% against 8% at the primary cell), which is what noisy EI is for — and it does not close the measured-value-argmax gap. **The two quiet-assay tested-best verdicts are acquisition-dependent and must not be stated without naming the acquisition.**
2. Under **naïve unconstrained** quadratic or GP recommendation, BO attained lower regret by 0.27–0.36 in every cell. Almost all of that swing is extrapolative optimization of a saddle (200/200 Hill runs). Under **in-region / ridge** recommendation the contrast was null in three of four cells. That is the fairer classical readout.
3. Sampling geometry and surrogate class contribute separately (Q34/Q45). The CCD is 4.4-fold more D-efficient in its own region and still yields a worse global naïve recommendation than a four-factor quadratic on the adaptive design.
4. Ranking is landscape-dependent. Levy and Rosenbrock reproduce the terminal-rule switch. Hartmann6 favours BO under every rule; removing the 6→4 screen at d = 6 makes DoE worse (+0.207) and widens BO’s lead (Q59). Ackley is void.
5. Well count and plate-round count are different costs. Sequential RSM with relocation (Q56) matches qLogEI on arrival under measured-value argmax. One-shot GP on Hill is stable across five draws (Q54) and, at σ = 0.25 under model recommendation, beats ten-round qLogEI in one plate round.
6. The primary measured-value-argmax lead **survives qLogNEI** and **does not survive a three-well confirmation protocol** (Q58: −0.0595 → −0.0009). It is a fact about single-readout selection, not about every laboratory carry-forward.
7. Scoring an acceptable region rather than one recipe reorders the methods. In the prospective Hill target, SPADE is competitive on map quality and at practical regret parity under a common posterior-mean rule, with two rounds rather than ten for batch BO; that is an architecture-level trade-off, not a universal win.
8. The causal targeting claim fails. Original boundary targeting does not beat random placement, and neither error-aware acquisition nor diversity-aware batching reaches the registered practical-effect bar. The current evidence supports studying a two-round spread architecture, but not claiming that any tested eight-well targeting mechanism earns its complexity.
9. SPADE's certificate is not portable as a general guarantee. The prospective claim narrows to Hill; retrospective five-family evidence finds γ = 0.99 under-coverage on Levy/Rosenbrock and frequent refusal to certify on Ackley/Hartmann6.

Rummukainen, Lapierre and Ndahiro already compared BO and DoE experimentally. Narayanan’s 3–30× figures use predicted DoE counts. This paper’s claim is that matched evaluation counts still do not define a unique comparison unless the terminal decision, noise handling, extrapolation policy, confirmation protocol, and cost unit are specified — and that those pieces can be quantified.

---

## Data availability

| Content | Path |
|---|---|
| Primary matched-budget grid | `results/e2-grid.json`, `results/e2-doe-d8.json` |
| Design × surrogate factorial | `results/q34-factorial.json` |
| Constrained RSM; saddle classification | `results/q35-constrained-rsm.json` |
| Best-observed DoE correction | `results/d20-rescore.json` |
| Four-factor polynomial refit | `results/q45-fourfactor-refit.json` |
| External test functions | `results/q42-families.json` |
| Cost-curve campaigns | `results/q52-budget-to-target.json` |
| Reconstructed rounds and arrival | `results/q52-rounds-to-arrival.json` |
| Sequential RSM with steepest ascent | `results/q56-doe-ascent.json` |
| Search vs identification, qLogEI and qLogNEI | `results/q55-oracle-best.json`, `results/q57-search-vs-id.json` |
| Selection-rule sensitivity | `results/q58-selection-sensitivity.json` |
| Hartmann6 with and without 6→4 screen | `results/q59-hartmann-no-screen.json` |
| Hill one-shot GP, five design draws | `results/q54-hill-spread-gp-draws.json` |
| Cost-curve figures | `results/figures/cost-curves.html` (Figure 2) |
| Scoring-rule figure | `results/figures/fig1-scoring.html` (Figure 1) |
| Saddle / ridge schematic | `results/figures/fig3-saddle.html` (Figure 3) |
| Prompts for the completed revision runs | `docs/PROMPTS-NEXT.md` |
| Control tables and Q-ids | `docs/SUPPLEMENT.md` |
| One-shot GP on external families | `results/q53-spread-gp-families.json` |
| Design-space re-score (K6), 9,600 rows | `results/k6-designspace.json`, `results/k6-analysis.json` |
| Joint certification and `alpha*` (K6b) | `results/k6b-conservative.json`, `results/k6b-analysis.json` |
| SPADE on the 24-cell γ ladder, 4,800 rows | `results/p2-versionb-gamma.json` |
| Design-space map at (d = 6, σ = 0.10), 12 arms | `results/p3-k6-d6-s010.json`, `results/p3-k6b-d6-s010.json` |
| SPADE protocol as received | `docs/SPADE-SPEC.md` |
| SPADE findings record, errata and open kills | `docs/FINDINGS-SPADE.md` |
| Prospective SPADE-as-method study, 99,601 combined records | `results/final-spade-certificate.json`, `results/final-spade-regret-pareto.json` |
| Its registered kill ledger and provenance manifest | `results/final-spade-kill-ledger.json`, `results/final-spade-manifest.json` |
| Registered KF-3 mechanism follow-up, 400 campaigns | `results/kf3-followup-analysis.json`, `docs/SPADE-KF3-FOLLOWUP-SPEC.md` |
| Consolidated SPADE evidence and architecture/mechanism audit | `docs/SPADE-RESULTS-AND-ANALYSIS.md` |
| Audit trail | `docs/RESULTS.md` |

---

## References

Box, G. E. P., Draper, N. R. *Empirical Model-Building and Response Surfaces.*

Box, G. E. P., Wilson, K. B., 1951. On the experimental attainment of optimum conditions. *J. R. Stat. Soc. B* 13, 1–45.

Frazier, P. I., 2018. A tutorial on Bayesian optimization. arXiv:1807.02811.

Gisperg, F., et al., 2025. Bayesian optimization in bioprocess engineering—where do we stand today? *Biotechnol. Bioeng.*

Hall, Lin, Ogle, 2025. iPSC-to-endothelial ECM screen. *Sci. Rep.*

Jones, D. R., Schonlau, M., Welch, W. J., 1998. Efficient global optimization of expensive black-box functions. *J. Global Optim.* 13, 455–492.

Lapierre, A., et al., 2025. Comparison of design of experiments and batch Bayesian optimization for growth-medium optimization of *Sporosarcina pasteurii*. *J. Chem. Technol. Biotechnol.* 100, 1571–1583. doi:10.1002/jctb.7860

Močkus, J., 1975. On Bayesian methods for seeking the extremum. In: *Optimization Techniques IFIP Technical Conference.*

Myers, R. H., Montgomery, D. C., Anderson-Cook, C. M. *Response Surface Methodology.*

Narayanan, H., et al., 2025. Bayesian optimization of cell culture media. *Nat. Commun.* 16, 6055. doi:10.1038/s41467-025-61113-5

Ndahiro, R. K., et al., 2025. Bayesian optimization of mammalian cell-culture media with solution-thermodynamic constraints. *iScience.* doi:10.1016/j.isci.2025.112944

Rummukainen, H., Hörhammer, H., Kuusela, P., Kilpi, J., Sirviö, J., Mäkelä, M., 2024. Traditional or adaptive design of experiments? A pilot-scale comparison on wood delignification. *Heliyon* 10, e24484.
