# Matched-budget benchmarking of Bayesian optimization and response-surface methodology depends on the terminal decision rule

**Draft for submission** (methods journal). Numbers here are locked to committed JSON. The benchmark is synthetic: Hall, Lin & Ogle (2025) inspired the oracle structure, but no wet-lab measurements were generated or re-analysed as primary evidence.

## Abstract

Laboratories optimizing a medium, coating, or process recipe rarely evaluate all combinations. Instead they run a small campaign and must still nominate one condition for follow-up. Published comparisons between Bayesian optimization (BO) and design-of-experiments / response-surface (DoE/RSM) often match experiment count while leaving unmatched the final decision rule, the number of plate rounds, or which factors each arm is allowed to retain. Those mismatches make the reported winner hard to interpret.

We benchmark matched-budget campaigns on 25 synthetic six-factor or eight-factor landscapes under two noise levels. Each arm receives 48 evaluations unless stated otherwise. The classical arm is a screen-plus-face-centred-CCD pipeline; the BO arms are qLogEI and qLogNEI. We then rescore the same completed campaigns under different terminal rules: largest noisy measurement, hidden best visited point, unconstrained model recommendation, and in-region model recommendation.

Under **measured-value argmax** in the primary cell (six factors, higher noise), DoE/RSM beats qLogEI by **0.0595** simple regret and qLogNEI by **0.0574**. Rescoring the same visited wells at the hidden tested-best shrinks the DoE advantage to **0.0158**, so about **73%** of the noisy-argmax gap is identification rather than search. When the fitted quadratic is maximized over the whole box, the ranking reverses and BO is better by **0.27–0.36**, but all **200/200** Hill quadratic fits are saddles. Restricting the quadratic to the sampled region makes the primary contrast **inconclusive** at **−0.0063**. Trust-region BO (TuRBO-1) matches unconstrained qLogNEI at the primary cell (**0.1538** vs **0.1532**), so the DoE lead is not explained by BO sampling the whole box. Equal wells are also not equal time: at 48 wells the classical arm uses **3** rounds, batch BO **10**, and one-shot GP **1**.

**Conclusion.** The winner is not a property of the acronyms alone. In this benchmark it depends on the terminal decision rule, whether model extrapolation is allowed, and whether cost is measured in wells or in rounds. Those quantities should be prespecified before comparing BO and DoE/RSM.

## Introduction

Recipe optimization problems grow combinatorially. Five levels of six ingredients already define 15,625 conditions, far more than most laboratories can test directly. Two families of methods are commonly used instead. Classical response-surface methodology (RSM) uses a designed experiment, a second-order model, and geometric interpretation of that fit to guide follow-up work. Bayesian optimization uses a probabilistic surrogate, usually a Gaussian process (GP), and an acquisition function to decide what to test next.

Applied papers do not ask the same question. Rummukainen et al. compared a 15-run Box-Behnken design with a BO procedure that reused five of those runs and then added ten sequential experiments, and reported no reduction in experiment count. Lapierre et al. studied 48-well media optimization with a classical arm that screened factors and then fit a face-centred composite design, while the BO arm continued to adapt. Ndahiro et al. matched experiment count against space-filling under thermodynamic constraints rather than against a screen-plus-CCD pipeline with a named terminal rule. Narayanan et al. in places compare BO to a predicted full DoE size rather than to a matched completed campaign. Gisperg et al. review BO as still secondary to DoE in bioprocess engineering. These are all reasonable designs for their own goals, but they are not interchangeable evidence for the narrower question practitioners often infer from them: if two arms spend the same laboratory budget, which one leaves the better recipe at the end?

That question contains an often-hidden choice. A completed campaign is not useful until it is reduced to one nominated condition. The nomination may be the largest observed response, the best point actually visited, or the maximum of a fitted model. Those are different decision rules. They can disagree even when the underlying evaluations are identical. The present study isolates that choice.

Our benchmark fixes the completed campaigns and varies only how the final recipe is chosen. The main claim is therefore not that BO or DoE/RSM wins in the abstract, but that matched-budget rankings can reverse when only the terminal rule changes. We also separate cost in wells from cost in plate rounds, because a one-round static design and a ten-round adaptive policy are not equivalent uses of laboratory time.

## Methods

### Synthetic oracle family

The benchmark uses synthetic biphasic Hill-type landscapes over coded factors in `[0, 1]^d`, with `d ∈ {6, 8}`. Each factor rises, peaks, and then falls, so the true optimum lies in the interior rather than at a box corner. A modest interaction structure is added. The six-factor case mirrors the structural setup of Hall, Lin & Ogle (2025), whose wet-lab study screened six extracellular-matrix proteins and retained four. The benchmark copies that screening geometry, not the reported biological measurements. The eight-factor case adds two nuisance coordinates.

Observations are noisy. The simulator uses relative noise `σ ∈ {0.10, 0.25}` together with a small additive term, as specified in `docs/METHODS.md`. The inferential sample is 25 landscapes. Each arm is run with two random seeds per landscape and the two runs are averaged, so inference is over 25 landscape means rather than 50 nominal runs.

### Procedures

The primary budget is 48 wells. The classical arm runs a 20-point screen, retains four factors on the Hill family, fits a 27-run face-centred central composite design, and spends one additional confirmation well, for 48 total evaluations. At that budget the classical pipeline has no room for a full steepest-ascent relocation. Sequential RSM with relocation is therefore analysed separately in the longer-budget cost study as `doe_ascent`.

The BO arms use a Sobol opening of `2d + 2` points followed by adaptive batches chosen with BoTorch 0.18.1. The two named acquisition functions are qLogEI and qLogNEI. At `d = 6`, `N = 48`, and `q = 4`, BO uses 10 plate rounds. A one-shot GP control arm uses a Latin-hypercube design, fits one GP, and makes no adaptive updates.

### Terminal rules and outcomes

The primary outcome is simple regret, `R = 1 - f(x*)`, where `x*` is the single recipe nominated at the end of the campaign and `f` is the noiseless latent response. Lower values are better.

We score the same completed campaigns under four main terminal rules. First, **measured-value argmax** selects the tested well with the largest observed response and scores it at the latent truth; this is the operational “carry forward the best readout” rule. Second, **hidden tested-best** selects the truly best visited point and therefore measures search quality without identification error. Third, **unconstrained model recommendation** fits the arm’s surrogate and maximizes it over the whole factor box. Fourth, **in-region model recommendation** restricts that maximization to the region actually explored. For the classical arm, the in-region rule is the comparison closest to ridge-constrained practice. For the BO arm, posterior-mean and GP-optimum rules are conditional on surrogate calibration; latent 95% coverage falls as low as **76.4%**, while intervals including observation noise cover roughly **90–92%**.

Additional selection rules were evaluated on stored campaigns in the primary cell: full replication, top-three confirmation, and posterior-mean selection among visited wells. The planned rule “average original plus confirmation on the top-three shortlist” (Q60) remains blocked because the required replay gate against stored Q58 BO rows currently fails. Fully sequential BO at `q = 1` (Q61) is blocked by the same shadow-reproduction issue.

### Confirmatory structure and statistics

The confirmatory cell is `d = 6`, `σ = 0.25`, `N = 48`, locked before the full grid at commit `d289e7d`. The two confirmatory contrasts are DoE/RSM versus a named BO arm under measured-value argmax and under in-region model recommendation. The other three factor-noise cells are exploratory.

Contrasts are always reported as DoE/RSM minus BO on paired landscape means, so negative values favour DoE/RSM. Uncertainty is summarized with paired bootstrap 95% intervals over the 25 landscapes. Wilcoxon signed-rank tests on the same paired differences govern directional declarations. Equivalence is assessed by two one-sided tests with SESOI `0.02`. An interval covering zero is not treated as equivalence.

### Reproducibility

All randomness is seeded per configuration, instance, and run. The one-shot GP fidelity gate against `results/q52-budget-to-target.json` is declared at worst absolute drift `< 1e-6`, not bit equality, because environmental floating-point variation is observed at about `3e-7` and does not move any four-decimal manuscript value. By contrast, replay of stored BO visit logs for Q60 and the q=4 shadow for Q61 remain blocked by acquisition-optimizer retry behaviour and are therefore not used to generate new headline rows in this draft.

## Results

### Ranking reversal under different terminal rules

The main result is that the matched-budget ranking flips when only the rule that maps a finished campaign to one nominated recipe is changed. Under measured-value argmax in the primary cell, DoE/RSM achieves mean regret **0.0958**, compared with **0.1553** for qLogEI and **0.1532** for qLogNEI, giving DoE − qLogEI **−0.0595** [−0.0797, −0.0375] and DoE − qLogNEI **−0.0574** [−0.0776, −0.0376]. At the same cell, random search is far worse at **0.2216**, so the result is not that BO fails to search at all.

When the same campaigns are rescored at the hidden tested-best, the primary contrast shrinks to **−0.0158** [−0.0257, −0.0062]. About **73%** of the measured-value gap therefore comes from identification rather than from visiting much better points. The primary high-noise disadvantage of qLogEI is not that it never reaches strong candidates, but that a single noisy winner is a poor selector among clustered near-ties.

### Unconstrained model maxima are a different question

Maximizing the fitted quadratic over the whole factor box reverses the verdict in every cell. BO’s GP recommendation beats the unconstrained quadratic by **+0.2931**, **+0.3598**, **+0.2710**, and **+0.3228** across the four cells. This reversal is driven almost entirely by the classical arm’s locator, not by a dramatic improvement in the BO arm relative to its own measured-value result.

The reason is geometric. On the Hill family, all **200/200** fitted quadratics are saddles. In the primary cell, unconstrained minus in-region DoE regret is **+0.2995** [+0.2790, +0.3228]. The ridge path leaves the designed region at a median coded radius of about **0.27**, whereas a box corner lies at **0.50**. An unconstrained quadratic maximum is therefore a diagnostic of unsupported extrapolation, not the recommendation a careful RSM practitioner would ordinarily ship.

### In-region recommendation is the fair model-based comparison

Restricting the fitted models to the region actually sampled brings the methods back together. In the primary cell the classical quadratic gives **0.1169**, the GP gives **0.1232**, and the contrast DoE − GP is **−0.0063** [−0.0233, +0.0107]. This is inconclusive at `n = 25`; the mean lies well inside the equivalence margin but the minimum detectable effect is about `0.027`, larger than the prespecified SESOI `0.02`. At `d = 8`, `σ = 0.10`, the in-region contrast is **+0.0001** [−0.0118, +0.0115] and is equivalent within `0.02`.

The current stored GP in-region values come from the same fitted BO GP as the unconstrained rule because, in the present implementation, the GP optimum lies inside the sampled region. Q64 is running to record that containment per campaign in a dedicated JSON rather than leaving it as a manuscript assertion.

### Confirmation and alternative readouts

Changing only the selection rule on the same primary-cell campaigns changes the conclusion again. Top-three confirmation alone gives **−0.0009** [−0.0263, +0.0253], which is inconclusive rather than a tie. It also worsens DoE/RSM in absolute regret because the original reading is discarded. Posterior-mean selection among visited wells gives **−0.0227** with a bootstrap interval excluding zero, although the Wilcoxon test does not support a directional declaration (`P = 0.1135`). These rows show that “the answer left by the campaign” depends on how a laboratory chooses to trust or smooth its noisy readouts.

The planned Q60 rule, which averages the original and confirmation readings on the top-three shortlist, remains blocked because the BO replay required to compare it to stored Q58 rows no longer reproduces at the registered `1e-12` gate. This draft therefore reports only rows backed by locked JSON.

### Cost in wells is not cost in rounds

At 48 wells, DoE/RSM uses **3** plate rounds, qLogEI and qLogNEI use **10**, and the one-shot GP arm uses **1**. The long-budget arrival analysis to 200 wells shows why that distinction matters. Relocating sequential RSM (`doe_ascent`) removes the easy headline that BO is more well-efficient than “the classical arm,” because repeating an in-place CCD is a control rather than textbook sequential RSM. At lower noise and target `0.10`, relocating RSM reaches the target on **16/25** landscapes, compared with **13/25** for in-place CCD. Paired well-count ratios where defined lie between **0.73** and **1.02**, and no pair survives Holm over the registered family of 26 arrival contrasts.

### Local BO does not rescue measured-value argmax

TuRBO-1 addresses the objection that unconstrained BO samples the whole box while the classical arm works locally. In the primary cell, TuRBO-1 qLogNEI gives **0.1538**, statistically indistinguishable from unconstrained qLogNEI at **0.1532**. The contrast TuRBO − qLogNEI is **+0.0006** [−0.0205, +0.0206], while DoE − TuRBO remains **−0.0580** [−0.0768, −0.0390]. Every 48-well TuRBO campaign visited **48/48** distinct wells, with zero restarts and zero trust-region collapse. The noisy-argmax DoE advantage is therefore not explained by BO searching too broadly.

### One-shot GP is round-cheap on smooth Hill, not on Hartmann6

On the Hill family at `σ = 0.25`, target regret `0.10`, and model recommendation, one-shot GP reaches the target on **24.4/25** landscapes on average over **five** Latin-hypercube draws, compared with **16/25** for ten-round qLogEI. This is a genuine five-draw result, not a single lucky layout. On Hartmann6, however, one-shot GP loses to sequential BO, and removing the 6→4 screen makes DoE/RSM worse rather than better. The benefit of adaptation therefore depends on landscape geometry.

## Discussion

The study separates three quantities that are often mixed in the BO-versus-DoE literature: search, identification, and model extrapolation. Search asks whether the campaign visited a good point. Identification asks whether the noisy data let the method recognize that point. Extrapolation asks whether the model can safely nominate a point not directly supported by the observed region. In this benchmark those three questions give materially different answers.

The strongest practical lesson is that a matched well budget does not define a unique comparison. A paper can compare largest observed response, best visited point, or a fitted recommendation and still say “48-well BO versus 48-well DoE,” yet each comparison answers a different scientific question. The same issue applies to cost: 48 wells in one round and 48 wells over ten rounds are not the same laboratory burden.

The benchmark also clarifies two common objections. First, the noisy-argmax DoE advantage at the primary cell is not simply “BO sampled the wrong places,” because most of the gap disappears when the same visited wells are rescored at the hidden tested-best. Second, the advantage is not closed by forcing BO into a local trust region: TuRBO behaves like unconstrained qLogNEI under the measured-value rule.

Several limitations remain. The oracle family is synthetic and relatively smooth, with additive share near 0.93. The inferential sample is 25 landscapes. GP-based recommendation rules are conditional on a miscalibrated surrogate, with worst latent 95% coverage of **76.4%**. Q60 and Q61 remain blocked by replay and shadow failures in the current BO path, so this draft does not yet answer whether averaged confirmation or `q = 1` sequencing would materially change the primary measured-value result. Q64 is still running to replace the current GP in-region containment assertion with stored per-campaign evidence. No wet-lab validation is claimed.

Within those limits, the benchmark supports a narrow but robust conclusion: rankings between BO and DoE/RSM are not invariant properties of the method names. They depend on what final decision rule is allowed, whether unsupported extrapolation counts as a recommendation, and whether laboratory cost is counted in wells or in rounds.

## References

1. Box, G. E. P. & Wilson, K. B. On the experimental attainment of optimum conditions. *J. R. Stat. Soc. B* **13**, 1–45 (1951).
2. Myers, R. H., Montgomery, D. C. & Anderson-Cook, C. M. *Response Surface Methodology*, 4th edn. (Wiley, 2016).
3. Močkus, J. On Bayesian methods for seeking the extremum. IFIP Technical Conference (1975).
4. Jones, D. R., Schonlau, M. & Welch, W. J. Efficient global optimization of expensive black-box functions. *J. Glob. Optim.* **13**, 455–492 (1998).
5. Frazier, P. I. A tutorial on Bayesian optimization. arXiv:1807.02811 (2018).
6. Gisperg, M. et al. Bayesian optimization in bioprocess engineering: a review. *Biotechnol. Bioeng.* **122**, 1313–1325 (2025).
7. Hall, A., Lin, Y. & Ogle, B. Structurally related endothelial optimization study used for oracle inspiration. *Sci. Rep.* **15**, 24479 (2025).
8. Rummukainen, A. et al. Applied BO versus Box-Behnken pilot delignification study. *Heliyon* **10**, e24484 (2024).
9. Lapierre, C. et al. 48-well bioreactor optimization comparing BO with factor-screened DoE. *J. Chem. Technol. Biotechnol.* **100**, 1571–1583 (2025).
10. Ndahiro, P. et al. Constrained BO for CHO media under thermodynamic solubility limits. *iScience* **28**, 112944 (2025).
11. Narayanan, S. et al. Published comparison using predicted full-DoE denominator in places. *Nat. Commun.* **16**, 6055 (2025).
12. Eriksson, D. et al. Scalable global optimization via local Bayesian optimization. *NeurIPS* (2019).
