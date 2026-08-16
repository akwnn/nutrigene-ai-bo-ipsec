# Matched-budget benchmarking of Bayesian optimization and response-surface methodology depends on the terminal decision rule

**Running title.** Terminal decision rules reverse BO-versus-RSM rankings on a synthetic recipe benchmark.

**Keywords.** Bayesian optimization; response-surface methodology; terminal decision rule; matched budget; Gaussian process; simple regret; sequential design; experimental rounds.

**Data.** All numerical claims are taken from the committed artefacts listed in the Data availability statement. Internal experiment identifiers (E2, Q34, …) are given in parentheses for reproducibility. Section 2 is a plain-language guide to the tables. Open loopholes and the runs required to close them are in `docs/PROMPTS-NEXT.md`.

**What this paper is not.** It is not the first BO-versus-DoE comparison, not a claim that “BO maps differently from RSM” as a new idea, and not a wet-lab validation of an ECM formulation. Rummukainen, Lapierre and Ndahiro already ran executed comparisons; Rummukainen already stated that RSM maps a region while BO concentrates near promising conditions.

**What this paper is.** A controlled demonstration that, under identical budgets and identical latent landscapes, changing only the **terminal decision rule** can reverse the apparent winner; and a factorial split of sampling design, surrogate class, recommendation rule, and well-versus-round cost. Most of the large unconstrained “BO win” is a naïve extrapolative readout of a saddle-shaped quadratic, not a fair classical-RSM recommendation.

**Novelty (adversarial).** BO-versus-DoE, “BO optimizes / RSM maps,” matched-budget media comparisons, synthetic optimizer benchmarks, and “best observation ≠ model recommendation” as a concept are **already in the literature**. What is potentially new is the same-campaign winner reversal plus the design × surrogate × locator decomposition (Q34/Q45/Q35). Open loopholes that can still get the paper rejected are listed after the abstract and in `docs/PROMPTS-NEXT.md`.

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
| Current unconstrained-RSM result as the fair main comparison | Not yet |
| Publishable somewhere after revision | Probably yes |
| Strong enough now for a top general journal | No |
| Could become a strong specialist benchmark / methodology paper | Yes |

---

## Abstract

**Background.** Reported advantages of Bayesian optimization (BO) over response-surface methodology (RSM) may depend as much on how the terminal formulation is selected as on where either method samples. Narayanan et al. (2025) report ~2.5–3× fewer experiments than the **predicted** count for standard DoE (and ~10–30× in a nine-factor transfer case): a resource-planning denominator, not an executed equal-budget DoE arm. Rummukainen et al. (2024) ran both methods at 15 experiments, scored the best measured condition, used noisy expected improvement then a posterior-mean final pick, and found no reduction in experiment count. Lapierre et al. (2025) and Ndahiro et al. (2025) add executed media/bioprocess comparisons in which BO improved biomass or titer; those studies compare complete workflows whose screening cuts, factor sets and terminal picks are not factorially separated. Both the “BO saves experiments” and the “no saving at matched budget” findings can be correct if their denominators and terminal decisions differ.

**Methods.** A synthetic Hill benchmark, **structurally inspired by** the six-factor / 6→4 screen of Hall, Lin and Ogle (2025), not fitted to endothelial data. The optimizer observes y = f(x) + ε. Simple regret is 1 − f(x∗). On identical 48-well campaigns we vary only the terminal decision: **hidden tested-best** (DoE stored; BO not stored), **measured-value argmax** (single noisy readout; this is the stored E2 “best observed” column), **naïve unconstrained quadratic or GP recommendation**, and **in-region / ridge recommendation**. Cost is counted in wells and in plate rounds. Named BO is qLogEI; qLogNEI is stored as a control and is the natural noisy comparator (a remaining loophole). The DoE cost-curve arm repeats the 48-well CCD and does not relocate; that comparison is not sequential RSM.

**Results.** On the same campaigns, rankings reversed. At the higher-noise condition (σ = 0.25), measured-value argmax favoured sequential DoE by 0.0595 (d = 6) and 0.0284 (d = 8). Naïve unconstrained recommendation favoured BO by 0.27–0.36: almost all of that swing is the quadratic, a saddle in 200/200 Hill runs, optimized off its learned region. In-region recommendation was null in three of four cells. At lower noise (σ = 0.10) the measured-value-argmax contrast was null. Hidden tested-best for DoE is 0.0597 at the primary cell versus 0.0958 for measured-value argmax; BO’s search column is missing, so search versus identification is not yet separated. One-shot GP versus sequential BO is a secondary observation on one Latin-hypercube draw.

**Conclusions.** A matched evaluation count does not define a unique BO-versus-RSM comparison. Rankings changed when the terminal decision changed. Most of the reversal arose from extrapolative optimization of saddle-shaped quadratic fits and largely disappeared under in-region constraints. Sampling geometry and surrogate class made independently measurable contributions; well count and plate-round count are different costs. Comparisons should prespecify the terminal decision, treatment of measurement noise, permitted extrapolation, and unit of experimental cost. The study is not a wet-lab validation.

**Open loopholes (do not submit until these are closed or explicitly demoted).** (1) BO hidden tested-best / search-versus-identification is missing, so the noisy-assay DoE lead is unexplained. (2) Named BO is qLogEI under y = f + ε; qLogNEI is the natural noisy comparator and is only a stored control. (3) Unconstrained saddle maximization is not classical RSM; the principal classical readout is in-region / ridge, and sequential RSM with relocation does not yet exist. (4) N = 200 pits sequential BO against repeated non-relocating CCDs. (5) Hill one-shot GP used one Latin-hypercube draw. (6) Hartmann6 currently discards two active factors by construction. (7) “Measured-value argmax” is one operational rule, not every laboratory’s carry-forward. Runs that close (1)–(6) are Workstreams 1–5 in `docs/PROMPTS-NEXT.md`.

---

## 1. Introduction

Optimization of culture media and extracellular-matrix (ECM) coatings is an expensive black-box problem. Each experimental condition consumes a well; each plate cycle—selection, incubation, readout, then reselection—consumes a **round**. Full-factorial grids are infeasible: five levels in six factors require 5⁶ = 15,625 evaluations. Practitioners therefore use sequential or planned designs that nominate a small set of conditions and, after the budget is spent, a single formulation to carry forward.

Two families of methods dominate this setting.

**Classical DoE and RSM** (Box and Wilson, 1951; Myers et al.) treat the unknown response as locally quadratic. A screening design identifies a subset of active factors. A **central composite design** (CCD) is then executed in that subregion and a second-order polynomial is fitted. Canonical analysis classifies the stationary point as a maximum, minimum, saddle or ridge. Classical RSM then uses **steepest ascent**, **ridge analysis**, and often a relocated CCD — not unconstrained maximization of a saddle over the whole box.

**Bayesian optimization** (Močkus, 1975; Jones, Schonlau and Welch, 1998; Frazier, 2018) places a Gaussian-process prior on the latent response and picks the next batch with an acquisition function. We report **qLogEI** as the named arm; **qLogNEI** is the natural comparator under observation noise and is stored as a control (Workstream 3 in `docs/PROMPTS-NEXT.md`). The distinction between using the best noisy observation and using a posterior-mean incumbent is already standard in noisy BO; this paper asks whether that already-known distinction is large enough to reverse a BO-versus-RSM ranking.

That RSM maps a design region while BO concentrates accuracy near promising conditions is **background**, not a finding. Rummukainen et al. (2024) already state it, and note that RSM remains usable if the criterion later changes whereas BO needs an explicit scalar objective.

Executed comparisons already exist. Rummukainen: 15-run Box–Behnken versus 5 initial + 10 sequential BO experiments, noisy EI then posterior-mean final pick, best measured condition, no reduction in experiment count. **Lapierre et al. (2025)** compared CCD/RSM after factor reduction with batch BO that kept all factors, after a shared 48-condition screen, on *Sporosarcina pasteurii* growth media; the BO medium gave higher biomass. **Ndahiro et al. (2025)** reported mammalian (CHO) media BO with thermodynamic constraints and higher titers than classical DoE **at the same experiment count**. **Narayanan et al. (2025)** report ~2.5–3× fewer experiments than the **predicted** standard-DoE count (SI calculation), and ~10–30× in a nine-factor transfer case. That is a different scientific experiment from giving each method 48 evaluations on the same landscape. Synthetic optimizer benchmarks (Olympus and related platforms; materials-science BO suites) already exist; novelty here is not “we ran a benchmark.”

**Hypothesis.** Apparently conflicting BO-versus-DoE conclusions can arise without contradictory algorithmic behaviour when studies bundle different terminal decisions, surrogate readouts, screening cuts, and budget definitions. Previous experimental papers compare complete workflows. We hold components under experimental control: same campaigns, several terminal rules; same points, both surrogates; same surrogate dimension, both designs; wells versus rounds.

Figure 1 is winner reversal by terminal rule. Figure 2 is cost in two currencies. Figure 3 is the saddle / ridge mechanism. The factorial (Q34/Q45) is the strongest original analysis. Open loopholes — BO hidden tested-best, sequential RSM, qLogNEI as co-primary, multi-draw one-shot GP, Hartmann without forced 6→4 — are listed in `docs/PROMPTS-NEXT.md` and must not be papered over.

The latent function is constructed. Factor count and the 6→4 screen are **structurally inspired by** Hall, Lin and Ogle (2025). No wet-lab BO campaign is reported.

---

## 2. Reader's guide

This paper is a **computer experiment**, not a wet-lab validation. A hidden mathematical function stands in for “how good is this recipe.” The optimizer never sees that function. It sees a noisy measurement, as a laboratory assay would. After a fixed number of recipes, we ask how far the nominated recipe is from the hidden best. Distance from the best is **simple regret**: 0 is perfect; larger is worse.

### 2.1 The laboratory questions

Every table answers one of these. They are not interchangeable.

1. **Hidden tested-best (search quality).** Among wells actually run, max noiseless f. A lab cannot compute this. DoE: 0.0597 at the primary cell. BO: not stored. Until it is stored, search versus identification cannot be separated.
2. **Measured-value argmax (single-readout selection).** Pick argmax of noisy y, score noiseless f. One transparent operational rule, **not** “what every researcher would do.” Labs may replicate, confirm, or use a posterior mean (Rummukainen’s final pick). This is the stored E2 “best observed” column (`reported_best_curve`). Primary cell: DoE 0.0958, BO 0.1553.
3. **Naïve unconstrained model recommendation.** Argmax of the fitted quadratic or GP over the whole box. For the quadratic this is a **diagnostic failure mode** when the fit is a saddle, not classical RSM.
4. **In-region / ridge recommendation.** The principal classical readout: argmax inside the explored region.
5. **Cost.** Wells and plate rounds until a target. Lead with hit probability P(T ≤ N). The current DoE curve repeats the CCD and is **not** sequential RSM.

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

| Estimand | How x∗ is chosen | What a lab can actually do |
|---|---|---|
| Hidden true-best among tested | Evaluated x of maximal true f | Not available without an oracle. DoE stored; BO not stored |
| Researcher pick (rule A) | Evaluated x of maximal noisy y; score true f | Carry forward the well that looked best on the assay |
| Unconstrained recommendation | arg max of f̂(x) over x ∈ [0,1]ᵈ | Run the model’s suggested next condition, including extrapolation |
| Constrained recommendation | arg max of f̂(x) over the explored region | Same, restricted to the explored region (ridge analysis) |

Rule A is defined for every procedure. Recommendation locators require a surrogate. The headline already-run tables use rule A, not hidden true-best.

### 3.2 Second-order response surfaces

The second-order model on the retained factors is

> *f̂*(*x*) = β₀ + Σᵢ βᵢ *x*ᵢ + Σᵢ βᵢᵢ *x*ᵢ² + Σ βᵢⱼ *x*ᵢ *x*ⱼ (i < j)

The Hessian of f̂ may be negative definite (local maximum), positive definite (local minimum) or indefinite (**saddle**). A saddle has a stationary point that is not a maximum; on a compact box the maximum of a saddle lies on the boundary. An unconstrained argmax of a saddle fit is therefore forced onto a face or corner, typically outside the region in which the polynomial was identified. Ridge analysis is the classical remedy.

The DoE procedure implemented here follows a published three-stage pipeline: (i) a 20-run screen (fractional factorial with centre points) retaining four factors, matching Hall/Ogle 6→4; (ii) a 27-run **face-centred CCD** on those four factors; (iii) one confirmation at the fitted stationary point. There is **no steepest-ascent stage** after the CCD. Cost-curve comparisons are therefore biased in favour of BO, which we state wherever those comparisons appear.

**D-efficiency** quantifies the information matrix of a stated model on a stated region. High in-region D-efficiency does not imply a useful recommendation outside that region.

### 3.3 Gaussian-process surrogates and expected improvement

A GP is a distribution over functions. Conditioning on data yields, at each unevaluated x, a posterior mean μ(x) and posterior variance σ²(x). **Expected improvement** (Jones et al., 1998) is the expected increase in the incumbent value if x is evaluated; it is large both where μ is high and where σ is high. The named stored arm is **qLogEI**, a numerically stable batch form, with batch size q = 4. The initial design is n₀ = 2d+2 (14 at d = 6); subsequent batches of four continue until N = 48 (**10 rounds**). That choice is awkward under observation noise: noisy expected improvement exists because the incumbent is itself uncertain, and Rummukainen used noisy EI then a posterior-mean final pick. **qLogNEI** is already stored as a control (primary-cell measured-value-argmax mean 0.1532 versus qLogEI 0.1553, null). It is the natural co-primary and is not yet treated as such (Workstream 3).

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

The stored named comparison is qLogEI versus sequential DoE. qLogNEI should be co-primary under noise (Workstream 3); until then it is reported beside qLogEI wherever the E2 grid already contains it. Remaining arms are controls.

- **qLogEI (BO).** Start with 14 recipes, then pick 4 more per plate using expected improvement, ten plates total. Awkward as the sole noisy comparator.
- **qLogNEI.** Same loop with noisy expected improvement. Natural comparator when y = f(x) + ε.
- **DoE (current pipeline).** Screen 20 recipes, keep four ingredients, run a 27-run face-centred CCD, confirm one point. Three plate stages. **No steepest-ascent / ridge relocation.** This is not sequential classical RSM. Cost-curve comparisons that use repeated copies of this pipeline are biased toward BO.
- **spread_gp.** One Latin hypercube, one GP fit, read the posterior peak. One plate. Isolates “having a GP” from “adapting plate by plate.” Hill results currently use **one** design draw (Workstream 4).
- **LHS / Sobol' / random.** Spread or scatter 48 recipes with no model. Scored only under measured-value argmax.
- **Coordinate descent.** Tune one factor at a time. Unpaired control.

| Procedure | Description | N = 48 evaluations | Rounds at N = 48 |
|---|---|---|---|
| qLogEI (BO) | GP; qLogEI; n₀ = 14, then batches of 4 | 48 | 10 |
| DoE | 20-run screen, retain 4; 27-run face-centred CCD; 1 confirmation. No steepest ascent | 48 | 3 |
| spread_gp | One Latin hypercube of size n; one GP; nominate arg max μ | n (one shot) | 1 |
| LHS / Sobol' / random | Space-filling or i.i.d. uniform; measured-value argmax only | 48 | 1 |
| qLogNEI | Identical loop, noisy-EI acquisition | 48 | 10 |
| Coordinate descent | Sequential; unpaired; control only | 48 | sequential |

The main experiment (E2) stores **measured-value argmax** (`reported_best_curve`: pick by noisy y, score noiseless f). Surrogate recommendations are computed on the same campaigns (Q34 naïve unconstrained; Q35 in-region). Space-filling arms have no recommendation column on the Hill oracle.

An earlier DoE “best observed” column read the oracle-best point among tested wells rather than the noisy argmax. All measured-value-argmax DoE figures below use the corrected locator (D20; primary-cell mean 0.0958). The superseded 0.0597 is DoE **hidden tested-best**, not rule A. Surrogate recommendations were unaffected. BO hidden tested-best is not stored.

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

**Measured-value argmax (single-readout selection).** Pick argmax of noisy y, score noiseless f. One transparent operational rule, not “what a researcher would carry forward.” qLogNEI is shown because it is the natural noisy comparator; it is not yet co-primary for new campaigns.

#### Measured-value argmax

| Cell | DoE | qLogEI | qLogNEI | DoE − qLogEI | Call vs qLogEI |
|---|---|---|---|---|---|
| d=6, σ=0.25 (primary) | **0.0958** | 0.1553 | 0.1532 | **−0.0595** [−0.0792, −0.0373] | DoE (qLogNEI 0.1532, null vs qLogEI) |
| d=6, σ=0.10 | 0.0892 | 0.0874 | 0.0808 | +0.0018 | null |
| d=8, σ=0.25 | 0.0963 | 0.1247 | 0.1105 | **−0.0284** | DoE |
| d=8, σ=0.10 | 0.0948 | 0.0972 | 0.0849 | −0.0024 | null (qLogNEI 0.0849 vs qLogEI, p = 0.027 uncorrected) |

At the higher-noise condition, the single noisy readout favours sequential DoE over both stored BO acquisitions. At lower noise the DoE–qLogEI contrast is null. This is **not** a claim that DoE tested better latent conditions: that requires R_search for both arms.

**Hidden tested-best / search quality (DoE only).** R_search = 1 − max_i f(x_i). A lab cannot compute this. BO’s column is missing (Workstream 1). Until it exists, search error and identification error are mixed in the BO measured-value-argmax number.

| Cell | DoE R_search | DoE measured-argmax | Identification gap |
|---|---|---|---|
| d=6, σ=0.25 | 0.0597 | 0.0958 | +0.0361 |
| d=6, σ=0.10 | 0.0544 | 0.0892 | +0.0348 |
| d=8, σ=0.25 | 0.0575 | 0.0963 | +0.0388 |
| d=8, σ=0.10 | 0.0500 | 0.0948 | +0.0448 |

Q49 finds that at σ = 0.25, on a space-filling design at n = 192, 61% of remaining regret is identification rather than search; **that figure is not the E2 BO campaign.**

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

**Interpretation.** Method ranking is not a property of the acronyms. Measured-value argmax at higher noise favours DoE. Naïve unconstrained quadratic readout favours BO because the saddle extrapolates. Proper in-region RSM is essentially tied. Search versus identification for BO is not yet separated.

Sources: `results/e2-grid.json`, `results/e2-doe-d8.json`, `results/q34-factorial.json`, `results/q35-constrained-rsm.json`, `results/d20-rescore.json`.

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
- **Hartmann6.** Six local maxima; the global one is easy to miss. Used as a **deceptive** surface. The DoE pipeline keeps only four factors, so two active ingredients are discarded by construction.
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

**Hartmann6 results.** Saddle in 25/25 at all four cells. No terminal-rule reversal: BO leads on every score. This is a **screening-workflow** comparison: the DoE pipeline retains four factors while all six Hartmann coordinates are active, so two active factors are discarded by construction. It is not a clean optimizer-only comparison conditional on both arms receiving the correct active subspace (Workstream 5).

| Cell | DoE A | BO A | DoE − BO (A) | DoE C unc. | BO C | DoE C con. | Call, every terminal rule |
|---|---|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.5623 | **0.2984** | +0.2460 | 0.9008 | 0.2695 | 0.5449 | BO |
| d=6, σ=0.10 | 0.5428 | **0.1938** | +0.3460 | 0.8985 | 0.1740 | 0.5223 | BO |
| d=8, σ=0.25 | 0.6393 | **0.3134** | +0.3189 | 0.8792 | 0.2992 | 0.6309 | BO |
| d=8, σ=0.10 | 0.6534 | **0.2370** | +0.4134 | 0.8751 | 0.2269 | 0.6442 | BO |

All best-observed contrasts p < 0.0001, favouring BO. Hartmann6 has six active coordinates; the pipeline retains four, so active signal is discarded at every cell. At d = 8, chance places 3.00/4 retained slots on active factors; the screen scored 2.96/4 at σ=0.25 and 2.88/4 at σ=0.10. Twenty runs plus four centre points do not distinguish a provably inert coordinate on this surface. At d = 6 the screen fills 4.00/4 active slots and BO remains superior, so chance-level screening is an additional eight-factor deficit, not the whole mechanism.

**Ackley.** The global minimizer is the centre of the box. A face-centred CCD evaluates the centre by construction. Best-observed DoE regret is ~0–0.013; BO is 0.56–0.76. Constrained and unconstrained recommendations agree to four decimals. The comparison is void under every terminal rule. Of 350 Q42 stationary-point classifications, 103 were interior maxima, concentrated on Ackley: a negative-definite Hessian makes unconstrained and constrained recommendations coincide.

Which procedure is ahead is therefore landscape-dependent. On saddle-like surfaces, DoE leads under measured-value argmax and BO under naïve unconstrained recommendation. On Hartmann6, BO leads under every terminal rule, but that comparison currently bundles screening loss with optimizer behaviour. No universal ranking is claimed.

### 5.6 Cost curves

Question 3. A snapshot at 48 wells cannot say who is cheaper. Campaigns were extended to a cap of 200 wells (d = 6 only; σ = 0.10 and 0.25; qLogEI, **repeated-CCD DoE**, random, spread_gp). That DoE arm is `doe_repeat`: the 48-well pipeline again, **no steepest ascent**. It is not sequential classical RSM. Do not treat N = 200 as a main efficiency claim (Workstream 2). Eight-factor cost curves were not computed.

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

At low noise the match with 10-round BO holds at 0.12, 0.10 and 0.08; it does **not** hold at the tighter target 0.05 (16 vs 18 hits). At the noisy assay, one-shot GP hits **more** landscapes than sequential BO at every reported target, still in one round. Medians among hits are not comparable across rows with different denominators. Hill spread_gp used one design draw; do not generalise until Hill is re-run at several design draws. Absence of steepest ascent in the DoE arm still biases BO-versus-DoE cost curves. Eight-factor cost curves were not computed.

### 5.7 Sequential adaptation versus a one-shot GP

Q53 asks whether BO’s extra plates are doing work, or whether a GP fit on a single space-filling batch would have been enough. **spread_gp** places all wells at once, fits one GP, and reads the peak: one round. **qLogEI** uses the same well count but ten adaptive rounds. If they tie, sequential search is not buying sample efficiency on that surface. If spread_gp is worse, adaptation is doing work (typically on deceptive surfaces such as Hartmann6).

On the Hill ensemble, one-shot spread_gp was indistinguishable from 10-round qLogEI at N = 48 (one design draw). The same evaluation count on the Q42 families, with five design draws and a prediction fixed before the runner existed, held in 8 of 8 cells: spread_gp is inferior on Hartmann6.

| Family | spread_gp versus 10-round qLogEI |
|---|---|
| Levy, Rosenbrock | null |
| Hartmann6, Ackley | inferior, large gap |

**Q54 has now re-run Hill at five draws, so the two are poolable.** The verdict is stable in 20 of 22 cells; the two that move (σ = 0.25 rule C at τ = 0.05, σ = 0.10 rule A at τ = 0.03) are exactly the two with the largest design SDs (1.92 and 2.05), and Q52 had drawn at the favourable extreme in both. The σ = 0.25 rule-C advantage is unanimous across all five draws. Sequential BO therefore purchases robustness on deceptive surfaces. The Hill one-shot-GP match is a **promising secondary finding**, not a protocol recommendation.

---

## 6. Discussion

The contribution is not that BO and RSM “address different scientific questions.” Rummukainen already states that RSM maps a region while BO concentrates near promising conditions. Lapierre and Ndahiro already report executed media/bioprocess comparisons. Narayanan already reports large experiment-count reductions against **predicted** DoE sizes. Synthetic BO benchmarks already exist. The best-observation versus posterior-recommendation distinction is already in the noisy-EI literature.

What this study isolates is that **published BO-versus-DoE conclusions are not invariant to the evaluation protocol.** Under identical budgets and identical latent landscapes, changing only the terminal decision can reverse the apparent winner. Design geometry, surrogate class, noise-induced identification error, allowed extrapolation, and well-versus-round cost can then be separated. Both Narayanan’s resource-planning claim and Rummukainen’s matched-budget null can be correct because their denominators and terminal decisions differ; the paper does not treat prior savings claims as “wrong.”

Figure 1 is winner reversal on one synthetic ensemble: measured-value argmax at higher noise favours DoE; naïve unconstrained quadratic favours BO; in-region RSM is a tie. Figure 2 is cost in two currencies (wells and rounds). Figure 3 is why the unconstrained quadratic is a saddle, not a third method. Q34/Q45 show a GP on DoE points already dominates the quadratic, and a four-factor quadratic on BO points already dominates the same quadratic on the CCD — so sampling geometry and surrogate class are separately measurable. The CCD remains the more D-efficient design in its own region.

The giant 0.27–0.36 gap is a **diagnostic of invalid extrapolation**, not a fair classical-RSM loss. NIST / Box–Wilson RSM includes canonical analysis, ridge analysis, steepest ascent and relocation. Q56 now answers “is BO more efficient than sequential classical RSM?” and the answer is rule-dependent: under **measured-value argmax the two are near-indistinguishable** — no arrival contrast survives Holm over all 26 tests, only the tightest target (σ = 0.10, τ = 0.05) survives within the rule-A family of ten, and the one cell Q52 reported as surviving (σ = 0.10, τ = 0.10) falls to Holm 0.0703 within its own family once the classical design may relocate. Under **naïve unconstrained recommendation BO still wins every cell**, though relocation triples to sextuples the classical arm's chance of reaching a target at all. The concession that the long-run curve was biased in BO's favour was therefore load-bearing, and removing it cost BO its single surviving arrival result.

### Decision guide for a laboratory

Use this only as far as the benchmark reaches: a constructed Hill-like surface, six or eight factors, 48–200 wells, higher-noise / lower-noise conditions 0.25 / 0.10, no wet-lab confirmation. qLogNEI is not yet co-primary. Sequential RSM with relocation now exists (Q56) and BO’s tested-best column now exists (Q55).

1. **Need a map of a planned region, or may change the criterion later.** Run classical DoE (screen + CCD). That is what the CCD is D-efficient for. Do not read the unconstrained polynomial peak as the answer; it was a saddle in 200/200 Hill runs (Figure 3). Use in-region / ridge.
2. **Will select by a single noisy readout (measured-value argmax), higher-noise condition.** On this benchmark the DoE campaign’s noisy argmax had better true f than qLogEI and than stored qLogNEI. **Q55 now separates why:** the classical arm did also *test* better conditions, but at roughly a quarter of the apparent margin (−0.0158 against −0.0595 at d = 6, σ = 0.25). **73% of the lead is the assay failing to identify BO’s best well, not the search failing to find it.** If your carry-forward is replicates, a confirmation run, or a posterior mean rather than a single noisy argmax, most of this advantage does not apply to you.
3. **Same selection rule, lower-noise condition.** DoE and qLogEI were indistinguishable at 48 wells.
4. **Willing to try an unconstrained model peak anywhere in the box.** Do not use the unconstrained quadratic when canonical analysis diagnoses a saddle. The GP improved 10–21% on its own measured-value argmax; the naïve quadratic did not.
5. **Willing to try a suggested well only inside the explored region.** In-region GP and in-region quadratic were tied in three of four cells.
6. **Rounds are expensive (incubations, not wells).** Prefer DoE (3 rounds at 48 wells) or a one-shot Latin hypercube plus one GP (1 round). Sequential BO is 10 rounds at the same well count. One-shot GP is exploratory until multi-draw.
7. **Wells are expensive, rounds are cheap, surface believed smooth.** Arrival numbers exist; lead with hit probability, not medians among hits. Q54 re-ran Hill at five draws: the one-shot protocol is stable in 20 of 22 cells and **beats** 10-round BO on the model’s recommendation at the noisy assay. Do not carry that to a deceptive surface — Q53 shows it fails badly there.
8. **The surface may be deceptive (Hartmann6-like).** Sequential BO led under every score in the current **screening** workflow. Split screening from optimizer-only before treating this as a general BO win.
9. **Campaign will continue past 48 wells with “DoE” as comparator.** Sequential RSM with relocation now exists (Q56). Under measured-value argmax it matches qLogEI on arrival — **do not claim BO is cheaper on that rule.** Under an unconstrained model recommendation BO still wins every cell.

The only defined fold-reductions are at σ = 0.10 under the **unconstrained** rule, where qLogEI needs 0.09–0.23 of sequential RSM's wells (Q56). Read them as a statement about *when each arm can first answer* — the classical pipeline cannot speak before 53 wells, qLogEI has a posterior after 14 — not as search efficiency. Under measured-value argmax every defined ratio is 0.73–1.02, i.e. **no saving at all.** Rule-C ratios against the non-relocating `doe_repeat` remain undefined: it is censored above 50% everywhere.

**Venues after the critical runs.** Machine Learning: Science and Technology (benchmark category), Digital Discovery (self-driving-lab evaluation protocol), Chemometrics and Intelligent Laboratory Systems (evaluation confound, not a routine application). Biotechnology and Bioengineering only if biological grounding is strengthened (real emulator or wet-lab). Not Nature Communications on the current synthetic axis.

---

## 7. Limitations and robustness checks

The latent function is constructed, not identified from endothelial measurements. Hall/Ogle (2025) is **structural inspiration** (factor count, 6→4 screen), not a fitted endothelial surface. Digitized stage-2 data resolve an interior peak on one of four proteins. Replay on digitized medians is underpowered (minimum detectable effect 0.68). GP posterior coverage is below the nominal 95% in every cell (worst latent coverage 0.764); adding observation noise recovers predictive coverage of approximately 0.90–0.92.

**Make-or-break gaps (see `docs/PROMPTS-NEXT.md`).** **(1) CLOSED by Q55** — BO's tested-best column now exists for all four cells (`results/q55-oracle-best.json`), gated against the published rule-A column at |Δ| = 0 on all 400 rows. Search and identification are separated: at d = 6, σ = 0.25, 73% of the classical arm's rule-A lead is identification rather than search, and both arms identify their own best well only 2–18% of the time. (2) Named BO is qLogEI; qLogNEI is a stored control, not co-primary. **(3) and (4) CLOSED by Q56** — `boec.sequential_rsm` implements screen → CCD → canonical classification → steepest-ascent relocation, and was run to the 200-well cap against the stored arms (`results/q56-doe-ascent.json`). It relocates 3.4 times per campaign at σ = 0.25. **(5) CLOSED by Q54** — Hill spread_gp re-run at five design draws (`results/q54-hill-spread-gp-draws.json`), with draw 0 reproducing Q52's committed rule-A curves exactly, 550 of 550. The match is stable in 20 of 22 cells, and on rule C at σ = 0.25 the one-shot arm in fact *beats* ten-round qLogEI at τ = 0.12, 0.10 and 0.08, unanimously across draws. (6) Hartmann6 currently drops two active factors. (7) Measured-value argmax is one operational rule. Cost curves were not computed at d = 8. Surrogate-recommendation columns do not exist for space-filling arms on the Hill oracle. Q49’s 61% identification share is LHS at n = 192, not E2 BO. Coordinate descent is unpaired. Narayanan’s 3–30× figures should be re-read from the PDF before submission; they are cited as predicted DoE counts, not executed equal-budget DoE. Lapierre 2025 and Ndahiro 2025 PDFs must be read before claiming related-work completeness.

Robustness checks (not headline): an additive kernel raised R² from 0.375 to 0.744 with regret change 0.0015 (p = 0.71); a “better” lengthscale prior worsened automatic relevance determination; acquisition-optimizer failures were 4/3400 = 0.118% against a 1% threshold set in advance; initial-design size had no effect at the primary cell; 0 of 10,000 permutations matched the surrogate-effect magnitude; design-averaged BO remained ahead of a lucky LHS on 25/25 landscapes (p = 6.0×10⁻⁸).

Excluded from the claims of this paper: two voided E2 runs (path-best scoring; unpaired initial design); the figure −0.0708 from an untracked grid; a retracted savings-crossover at 0.15; Ackley as a DoE–BO cell; multi-fidelity predictions that failed (Q47); extrapolation-detection (E4) as a headline, where pooled and registered cells disagree in sign.

---

## 8. Conclusions

A synthetic Hill benchmark, **structurally inspired by** a published iPSC-to-endothelial ECM screen (not fitted to cell data), was used to hold campaign geometry, surrogate class, terminal decision, noise, and cost unit under experimental control.

1. Under **measured-value argmax** at the higher-noise condition, sequential DoE attained lower simple regret than qLogEI by 0.0595 at six factors and 0.0284 at eight. Stored qLogNEI does not remove that DoE lead. At lower noise the qLogEI contrast was null. **Q55/Q57 decompose it:** scored on what each arm actually tested, the same contrasts are −0.0158 and −0.0127, so **55–73% of the lead is identification rather than search.** Both arms identify their own best well only 2–18% of the time, and BO’s identification gap is significantly the larger at both σ = 0.25 cells (+0.0436, p = 0.0004 at d = 6). The direction never reverses between the two locators; the magnitude collapses. **Q57 re-runs all of this with qLogNEI co-primary:** the higher-noise verdicts are unchanged under both acquisitions, and the tested-best advantage at the primary cell is in fact *larger* against qLogNEI (−0.0237). qLogNEI does identify its own best well far more often (22% against 8% at the primary cell), which is what noisy EI is for — and it does not close the measured-value-argmax gap. **The two quiet-assay tested-best verdicts are acquisition-dependent and must not be stated without naming the acquisition.**
2. Under **naïve unconstrained** quadratic or GP recommendation, BO attained lower regret by 0.27–0.36 in every cell. Almost all of that swing is extrapolative optimization of a saddle (200/200 Hill runs). Under **in-region / ridge** recommendation the contrast was null in three of four cells. That is the fairer classical readout.
3. Sampling geometry and surrogate class contribute separately (Q34/Q45). The CCD is 4.4-fold more D-efficient in its own region and still yields a worse global naïve recommendation than a four-factor quadratic on the adaptive design.
4. Ranking is landscape-dependent. Levy and Rosenbrock reproduce the terminal-rule switch. Hartmann6 favours BO under every rule in the current **screening** workflow (two active factors dropped). Ackley is void.
5. Well count and plate-round count are different costs. **Sequential RSM with relocation now exists (Q56), and it changes the long-run answer.** Under measured-value argmax `doe_ascent` matches qLogEI on arrival — no contrast survives Holm, and Q52’s single surviving cell (σ = 0.10, τ = 0.10) falls to 0.0703 within its own family. Under the unconstrained rule BO still wins every cell, and the first defined fold-reductions in this project appear at σ = 0.10 (0.09–0.23), driven substantially by the classical pipeline being unable to answer before 53 wells. **One-shot GP on Hill is no longer exploratory:** Q54's five draws make the match a stable result in 20 of 22 cells, and at σ = 0.25 the one-shot arm beats ten-round qLogEI on the model’s recommendation in one plate round against forty-eight.

Rummukainen, Lapierre and Ndahiro already compared BO and DoE experimentally. Narayanan’s 3–30× figures use predicted DoE counts. This paper’s claim is that matched evaluation counts still do not define a unique comparison unless the terminal decision, noise handling, extrapolation policy, and cost unit are specified — and that those pieces can be quantified.

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
| Tested-best beside measured-best, both arms | `results/q55-oracle-best.json` |
| Sequential RSM with steepest ascent | `results/q56-doe-ascent.json` |
| Cost-curve figures | `results/figures/cost-curves.html` (Figure 2) |
| Scoring-rule figure | `results/figures/fig1-scoring.html` (Figure 1) |
| Saddle / ridge schematic | `results/figures/fig3-saddle.html` (Figure 3) |
| Prompts for missing runs | `docs/PROMPTS-NEXT.md` |
| Control tables and Q-ids | `docs/SUPPLEMENT.md` |
| One-shot GP on external families | `results/q53-spread-gp-families.json` |
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
