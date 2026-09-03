# Literature and novelty review for SPADE

**Review status:** `DONE_WITH_CONCERNS`
**Search date:** 2026-09-02
**Scope:** GP excursion/level-set estimation; Vorob'ev summaries; conservative set
estimation; noisy batch Bayesian optimization and qLogNEI; response-surface design of
experiments (DoE), process qualification, and design space; calibration and coverage; and
abstention/selective prediction.

## Executive assessment

SPADE is best presented as a **process-specific integration and an empirical study**, not as
a new theory of excursion sets or conservative set estimation. Nearly every mathematical
ingredient in the current method has direct prior art: Gaussian-process (GP) level-set
learning, batch sequential design near an excursion boundary, posterior distributions over
excursion sets, Vorob'ev quantiles, and selection of a large set subject to a joint posterior
containment constraint. In particular, Azzimonti et al. define a conservative estimate as a
maximum-volume member of a candidate family satisfying
`P(C subset Gamma | data) >= alpha`, use nested Vorob'ev quantiles as that family, and develop
batch-sequential designs for reducing uncertainty about the estimate [4]. That is very close
to SPADE's certification core.

The defensible contribution is narrower and still useful: SPADE adapts this established set
estimation machinery to a fixed-well, noisy, multi-round cell-manufacturing workflow; carries
per-well observation variances through the GP; permits an empty answer; uses a registered
leave-one-family-out uncertainty-inflation rule specifically for the LC/C3 matched-round
analysis (while DC/C2 selects inflation within the DC data, in sample); and evaluates
**empirical truth-containment and answer rate** against qLogNEI, a specified response-surface
DoE pipeline, and one-shot Latin-hypercube sampling under a common well budget. The validated
numerical findings can be novel results of this study without establishing methodological
priority, universal superiority, frequentist coverage for future biological campaigns, or
regulatory qualification of a manufacturing design space. C5 has been repaired after the
original analysis defect: the guarded SPADE-only analysis gives descriptive Spearman
`rho=0.9880098603391883`. This is a valid result of the corrected committed analysis, but the
predictor is oracle-derived and the 25 family-prevalence cells are structured,
nonexchangeable observations, so it is descriptive rather than inferential or deployable.

## 1. GP excursion and level-set estimation

For a response `f` and threshold `tau`, the acceptable region
`Gamma = {x: f(x) >= tau}` is an excursion (upper level) set. Sequential GP methods for
learning such sets are established. Gotovos et al. formulate level-set estimation as
sequential classification under a GP, sample where classification remains ambiguous, give
sample-complexity guarantees, and discuss both percentage-of-maximum thresholds and batch
sampling [1]. Bect et al. derive stepwise-uncertainty-reduction (SUR) designs for estimating
the measure of a GP excursion set [2]. Chevalier et al. develop computationally tractable
multipoint/batch SUR criteria for excursion-set identification [3].

These sources support describing SPADE's boundary-focused sequential design as belonging to
the GP level-set/SUR family. They do **not** support describing boundary-focused acquisition,
batch level-set learning, or sequential GP excursion estimation as inventions of SPADE.
SPADE's `batch_lse_rho` is a particular engineering choice whose exact relation to the loss
functions and guarantees in [1--4] should be stated, rather than implied to inherit them.

## 2. Vorob'ev sets, quantiles, and posterior excursion-set summaries

A GP posterior induces a distribution on `Gamma`. The posterior coverage function
`p_Gamma(x) = P(x in Gamma | data)` generates nested Vorob'ev quantiles
`Q_rho = {x: p_Gamma(x) >= rho}`. The Vorob'ev expectation chooses a quantile whose volume
matches the expected random-set volume; it is a mean-shape summary, not by itself a joint
confidence or containment set. Heinrich, Stoica, and Tran establish consistent estimation of
Vorob'ev expectations from random-set replicates under spatial discretisation [5]. Chevalier
et al. brought Vorob'ev expectation/deviation to GP level-set uncertainty [6], and Azzimonti
et al. use conditional simulations to quantify excursion-set uncertainty on fine grids [7].

The distinction between **pointwise membership probability** and **simultaneous set
containment** is essential. A set made by thresholding pointwise probabilities generally does
not have the same nominal joint probability that every included point exceeds `tau`. Bolin
and Lindgren formulate and compute excursion regions with a prescribed joint exceedance
probability for latent Gaussian models and explicitly connect the problem to multiplicity
[8]. SPADE is therefore right to evaluate joint containment of a candidate set, but that
principle is established.

## 3. Conservative set estimation

Azzimonti et al.'s conservative-estimate formulation is the closest methodological
antecedent [4]. They define a level-`alpha` conservative estimate by maximizing set measure
over candidates satisfying a posterior inclusion probability, then use nested Vorob'ev
quantiles to make the search tractable. They also note an important limitation: the chosen
Vorob'ev quantile is optimal within the selected nested family (and has a useful
symmetric-difference property), but need not be the globally largest measurable set satisfying
the containment constraint. Their paper further develops batch-sequential acquisition rules
to reduce uncertainty in such estimates and benchmarks them under varying noise and batch
size.

Consequences for SPADE:

- “Largest set” must mean **largest among the scanned candidate Vorob'ev quantiles on the
  registered finite grid**, not globally largest subset of the continuous input space.
- `P(C subset Gamma | data) >= alpha` is a **model-posterior statement**. It is not, without
  additional assumptions or calibration evidence, a frequentist guarantee over repeated
  campaigns.
- Inflation, finite posterior draws, grid discretisation, fitted hyperparameters, and plug-in
  observation variances can all change the achieved probability. The manuscript correctly
  prioritizes empirical truth-containment, but should keep “certificate” operationally
  defined and avoid implying a theorem that has not been proved.
- Returning the empty set is logically valid under a subset constraint but scientifically
  uninformative. Reporting answer rate with conditional containment is therefore necessary.

## 4. Noisy BO and qLogNEI

Expected improvement and Bayesian optimization are established approaches to expensive
black-box optimization [9]. Letham et al. derive noisy expected improvement for greedy batch
optimization with noisy observations and constraints, using quasi-Monte Carlo approximation
[10]. BoTorch provides a modular Monte Carlo framework for batch Bayesian optimization [11].
Ament et al. identify numerical vanishing of EI and its parallel/noisy variants and introduce
the LogEI family, including the noisy parallel form implemented as qLogNEI, to improve
acquisition optimization [12].

Thus qLogNEI is an appropriate modern comparator for **point optimization under noise**, but
it is not designed specifically to learn or certify an excursion region. Passing qLogNEI's
observations through the same downstream conservative-set estimator is a fair way to compare
the information gathered for certification, provided the paper says that qLogNEI itself is
the acquisition policy and the certificate is a common post-processing layer. Results against
one qLogNEI implementation do not support claims against “Bayesian optimization” as a class.

## 5. Response-surface DoE, process qualification, and design space

Response-surface methodology (RSM) has long combined designed experiments, low-order local
models, and sequential movement toward improved operating conditions [13]. Official NIST
guidance distinguishes screening designs from response-surface designs and lists target
attainment, optimization, variance reduction, and robustness as RSM objectives [14]. The
screen-then-response-surface structure used by SPADE's comparator is therefore conventional,
while its exact 20-run screen, 27-run face-centred design, one confirmation well, and fitted
model are study-specific.

ICH Q8(R2) defines a pharmaceutical design space through relationships among material
attributes/process parameters and critical quality attributes, expects operation within that
space to result in product meeting defined quality, and states that combined univariate
acceptable ranges do not themselves constitute a design space [15]. FDA/ICH training material
also distinguishes design-space verification from process validation and notes that an
appropriate DoE applies confidence across the design space, including its edges [16]. These
documents are useful manufacturing context, not evidence that SPADE's synthetic acceptable
set is a qualified regulatory design space.

The current paper should use “operating region” or “candidate acceptable region.” It may say
the deliverable is *analogous or relevant to* design-space development, but must not say that
48 synthetic wells establish a regulatory design space, process qualification, continued
process verification, or commercial-scale validity. The tested low-order DoE pipeline is not
representative of all RSM, optimal-design, robust-design, or model-based design-space methods.

## 6. Calibration, coverage, and empirical containment

Calibration has several non-equivalent meanings. Dawid's probability calibration concerns
agreement between assigned event probabilities and long-run event frequencies [17]. Bayesian
posterior credibility is conditional on the model; it need not yield nominal repeated-sampling
coverage under misspecification or empirical-Bayes hyperparameter fitting. GP credible sets
can be overconfident for broad function classes under estimated squared-exponential scaling,
which is direct reason to avoid identifying nominal posterior probability with validated
coverage [18]. Simulation-based calibration tests computational calibration when parameters
and data are generated from the assumed model, but does not validate the model against a real
assay [19].

For the LC/C3 matched-round analysis, SPADE's leave-one-family-out selection of inflation is
an **empirical benchmark calibration protocol**, not distribution-free calibration and not
proof of 95% coverage on new biological response families. This statement does not apply to
DC/C2: that comparison selects inflation within the DC data and is therefore in-sample, not
held-out-family calibration. Synthetic truth-containment is stronger
evidence than an internal posterior diagnostic for the frozen benchmark, yet transport beyond
the five generators, noise level, grid, budget, and fitted pipeline is unestablished. The
real-data leave-one-out procedure assesses observation prediction, as the manuscript already
notes; it does not identify latent-function uncertainty or prospective excursion-set
containment.

The Clopper--Pearson construction supplies exact binomial confidence limits under the
binomial sampling model [20]. Calling a pooled lower bound “exact” requires care here:
family/prevalence cells can be heterogeneous, multiple prevalences from a seed are dependent,
and analysis conditional on `answered` is data-selected. The manuscript should call it a
one-sided Clopper--Pearson binomial bound for the observed answered-cell proportion and state
the sampling unit/dependence structure. It should not claim exact repeated-campaign coverage
for a heterogeneous pooled benchmark without a justification or cluster-aware sensitivity
analysis.

## 7. Abstention and selective prediction

Abstention is established decision theory. Chow derives the optimum error--reject trade-off
when rejection is available [21]. Modern selective classification explicitly reports the risk
on accepted predictions together with coverage (the fraction accepted) and can calibrate a
selection rule to a target risk under stated sampling assumptions [22]. SPADE's empty-set
outcome is not literally a per-example reject-option classifier, but it has the same reporting
logic: reliability among answers is uninterpretable without the frequency of answers.

Accordingly, the explicit `answered`, `contained`, and answer-rate reporting is a strong and
defensible study design choice, not a novel invention of abstention. “Cannot certify” should
be reserved for the method returning no acceptable non-empty set under its frozen rule; it
must not be used when the real issue is merely too few answered replicates to clear a chosen
confidence-bound threshold.

## 8. Novelty classification

| Component or result | Classification | Assessment and permissible wording |
|---|---|---|
| Excursion set `Gamma={x:f(x)>=tau}` under a GP | Established ingredient | Standard level/excursion-set formulation [1--4,7,8]. |
| Sequential sampling near an uncertain level boundary | Established ingredient | GP level-set learning and SUR are established, including batch variants [1--4]. |
| Posterior draws inducing random excursion sets | Established ingredient | Standard Bayesian random-set construction [4,7]. |
| Vorob'ev coverage function and nested quantile sets | Established ingredient | Established random-set summaries [4--7]. |
| Search for a high-volume Vorob'ev quantile satisfying joint posterior containment | Established ingredient, very close antecedent | Azzimonti et al. give essentially this conservative-set formulation [4]. SPADE must cite it prominently and cannot claim the certification core as new. |
| Fixed candidate/Sobol grid and Monte Carlo joint-containment scan | SPADE-specific implementation | A discrete computational realization; novelty only if an algorithmic difference from [4,7,8] is specified and evaluated. |
| Per-well plug-in observation variances in a noisy cell-assay GP | SPADE-specific adaptation | Relevant assay adaptation; not new heteroscedastic GP theory. State exactly whether variances are known, estimated, or replicated. |
| Fixed 48-well, multi-round campaign and eight-well later batches | SPADE-specific adaptation | Operational constraint and workflow design, not a general statistical invention. |
| Inflation selection in LC/C3 | SPADE-specific integration | Registered leave-one-family-out empirical tuning/calibration for the matched-round LC/C3 analysis only. Do not call it a theorem, distribution-free guarantee, or real-assay validation. |
| Inflation selection in DC/C2 | Study-specific in-sample procedure | Selected within the DC data; it is not held-out-family calibration. C2 containment must be described with this limitation. |
| Empty-set return plus answer-rate/containment reporting | SPADE-specific integration of established abstention logic | Good reporting discipline; abstention and risk--coverage trade-offs are established [21,22]. |
| Common downstream certification estimator for SPADE, qLogNEI, and DoE observations | Defensible comparative-design contribution | Helps isolate acquisition/design effects, provided identical fitting/scoring is verified. |
| No detectable regret difference from qLogNEI in the frozen DC comparison | Defensible empirical novelty | A result for five named synthetic families, 32 seeds, 48 wells, and the specified rounds/noise. Say “no detectable difference,” not equivalence. |
| Greater certified volume than qLogNEI at matched five rounds | Defensible empirical novelty | Restricted to the registered leave-one-family-out benchmark and common certificate. Not superiority over BO generally. |
| Tested DoE pipeline has better recipe regret but poorer empirical containment | Defensible empirical novelty | A valuable adverse result for this comparator. Not evidence that classical DoE generally cannot form reliable regions. |
| C5: association between SPADE answer rate and true margin/noise over family-prevalence cells | Repaired, verified descriptive empirical result | The corrected SPADE-only analysis, with row-order and completeness guards, gives Spearman `rho=0.9880098603391883`; it supersedes the defective earlier result. The 25 cells are structured and nonexchangeable, and margin/noise is oracle-derived, so no independence-based p-value, population-generalization claim, or prospective diagnostic claim is warranted. |
| Mean-marginalization width changes and assay-specific LOO inflation | Supporting empirical observation | Retrospective diagnostic, not prospective validation or proof of corrected latent coverage. |

## 9. Novelty and validity claims the manuscript must not make

1. **Do not claim that SPADE invents GP level-set estimation, boundary sampling, excursion
   sets, Vorob'ev quantiles/expectations, conservative excursion-set estimates, or joint
   excursion probabilities.** Sources [1--8], especially [4], predate SPADE.
2. **Do not claim a globally maximum-volume certified set.** The computation is restricted to
   nested candidate quantiles on a finite grid and Monte Carlo draws; even the closest prior
   formulation notes that this need not solve the unrestricted set problem [4].
3. **Do not identify nominal posterior containment with frequentist coverage.** The benchmark
   estimates empirical containment under five synthetic generators; it does not prove 95%
   coverage for future assays, new families, new noise regimes, or continuous domains.
4. **Do not call either inflation rule distribution-free, conformal, externally calibrated,
   or prospectively validated.** LC/C3 uses leave-one-family-out calibration within the
   frozen synthetic suite; DC/C2 selects inflation within DC and is in-sample. Real-data LOO
   prediction is a different estimand.
5. **Do not claim “SPADE beats BO,” “BO cannot certify,” or optimizer equivalence.** qLogNEI is
   one point-optimization acquisition; the regret interval does not establish equivalence,
   and qLogNEI can yield contained regions after common post-processing.
6. **Do not claim “SPADE beats DoE” without the adverse regret result and round counts.** DoE
   found better recipes in fewer rounds in this benchmark. Conversely, do not generalize the
   tested DoE certificate failure to all classical or modern DoE.
7. **Do not call the returned region an ICH/FDA-qualified “design space,” process
   qualification, process validation, or manufacturing control strategy.** Regulatory design
   space requires product/process understanding and verification beyond this synthetic study
   [15,16].
8. **Do not call Clopper--Pearson bounds exact evidence for transportable campaign-level
   coverage without stating the binomial and independence assumptions.** Pooled heterogeneous
   cells and repeated prevalences need explicit handling.
9. **Do not call the Hill family biologically validated or fitted to endothelial-cell data.**
   It is a biology-shaped synthetic analogue.
10. **Do not claim wet-lab efficacy, calendar-time savings, financial savings, robustness at
    real-assay noise, or commercial-scale validity.** These outcomes were not tested.
11. **Do not present C5 as inferential evidence of population-level generalization or present
    truth-derived target quantiles or margin/noise as deployable campaign diagnostics.** The
    original C5 analysis was defective; the repaired, guarded SPADE-only result is descriptive
    Spearman `rho=0.9880098603391883`. Its 25 cells are structured and nonexchangeable, and
    margin/noise uses latent synthetic truth unavailable in practice.
12. **Avoid unqualified “trustworthy,” “certified,” and “assurance.”** Prefer “perfect observed
    containment among answered benchmark cells” and define “certificate” as the frozen
    model-and-grid decision rule.

## 10. Recommended positioning sentence

> SPADE integrates established GP level-set design and conservative Vorob'ev-set estimation
> with a fixed-well noisy assay workflow, analysis-specific uncertainty-inflation protocols
> (held-out-family for LC/C3 and within-DC/in-sample for DC/C2), and explicit abstention; its
> contribution in this study is the integration and the bounded empirical
> comparison of recipe regret, answer rate, certified volume, and truth-containment, rather
> than a new theory of excursion-set certification.

## References: primary literature and official technical sources

1. Gotovos, A., Casati, N., Hitz, G. & Krause, A. Active learning for level set estimation.
   *Proceedings of the Twenty-Third International Joint Conference on Artificial Intelligence
   (IJCAI 2013)*, 1344--1350 (2013).
   [Official proceedings PDF](https://www.ijcai.org/Proceedings/13/Papers/202.pdf).
2. Bect, J., Ginsbourger, D., Li, L., Picheny, V. & Vazquez, E. Sequential design of computer
   experiments for the estimation of a probability of failure. *Statistics and Computing*
   **22**, 773--793 (2012). [doi:10.1007/s11222-011-9241-4](https://doi.org/10.1007/s11222-011-9241-4).
3. Chevalier, C., Bect, J., Ginsbourger, D., Vazquez, E., Picheny, V. & Richet, Y. Fast
   parallel kriging-based stepwise uncertainty reduction with application to the
   identification of an excursion set. *Technometrics* **56**, 455--465 (2014).
   [doi:10.1080/00401706.2013.860918](https://doi.org/10.1080/00401706.2013.860918).
4. Azzimonti, D., Ginsbourger, D., Chevalier, C., Bect, J. & Richet, Y. Adaptive design of
   experiments for conservative estimation of excursion sets. *Technometrics* **63**, 13--26
   (2021; online 2019). [doi:10.1080/00401706.2019.1693427](https://doi.org/10.1080/00401706.2019.1693427).
5. Heinrich, P., Stoica, R. S. & Tran, V. C. Level sets estimation and Vorob'ev expectation of
   random compact sets. *Spatial Statistics* **2**, 47--61 (2012).
   [doi:10.1016/j.spasta.2012.10.001](https://doi.org/10.1016/j.spasta.2012.10.001).
6. Chevalier, C., Ginsbourger, D., Bect, J. & Molchanov, I. Estimating and quantifying
   uncertainties on level sets using the Vorob'ev expectation and deviation with Gaussian
   process models. In Ucinski, D., Atkinson, A. C. & Patan, M. (eds), *mODa 10 -- Advances in
   Model-Oriented Design and Analysis*, 35--43. Springer (2013).
   [doi:10.1007/978-3-319-00218-7_5](https://doi.org/10.1007/978-3-319-00218-7_5).
7. Azzimonti, D., Bect, J., Chevalier, C. & Ginsbourger, D. Quantifying uncertainties on
   excursion sets under a Gaussian random field prior. *SIAM/ASA Journal on Uncertainty
   Quantification* **4**, 850--874 (2016).
   [doi:10.1137/141000749](https://doi.org/10.1137/141000749).
8. Bolin, D. & Lindgren, F. Excursion and contour uncertainty regions for latent Gaussian
   models. *Journal of the Royal Statistical Society: Series B* **77**, 85--106 (2015).
   [doi:10.1111/rssb.12055](https://doi.org/10.1111/rssb.12055).
9. Jones, D. R., Schonlau, M. & Welch, W. J. Efficient global optimization of expensive
   black-box functions. *Journal of Global Optimization* **13**, 455--492 (1998).
   [doi:10.1023/A:1008306431147](https://doi.org/10.1023/A:1008306431147).
10. Letham, B., Karrer, B., Ottoni, G. & Bakshy, E. Constrained Bayesian optimization with
    noisy experiments. *Bayesian Analysis* **14**, 495--519 (2019).
    [doi:10.1214/18-BA1110](https://doi.org/10.1214/18-BA1110).
11. Balandat, M., Karrer, B., Jiang, D. R., Daulton, S., Letham, B., Wilson, A. G. & Bakshy,
    E. BoTorch: A framework for efficient Monte-Carlo Bayesian optimization. *Advances in
    Neural Information Processing Systems* **33**, 21524--21538 (2020).
    [Official proceedings PDF](https://proceedings.neurips.cc/paper/2020/file/f5b1b89d98b7286673128a5fb112cb9a-Paper.pdf).
12. Ament, S., Daulton, S., Eriksson, D., Balandat, M. & Bakshy, E. Unexpected improvements
    to expected improvement for Bayesian optimization. *Advances in Neural Information
    Processing Systems* **36**, 20577--20612 (2023).
    [Official proceedings record](https://proceedings.neurips.cc/paper/2023/hash/419f72cbd568ad62183f8132a3605a2a-Abstract-Conference.html).
13. Box, G. E. P. & Wilson, K. B. On the experimental attainment of optimum conditions.
    *Journal of the Royal Statistical Society: Series B* **13**, 1--38 (1951).
    [doi:10.1111/j.2517-6161.1951.tb00067.x](https://doi.org/10.1111/j.2517-6161.1951.tb00067.x).
14. National Institute of Standards and Technology. *NIST/SEMATECH e-Handbook of Statistical
    Methods*, section 5.3.3, “How do you select an experimental design?” (accessed 2026-09-02).
    [Official NIST handbook](https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm).
15. International Council for Harmonisation. *ICH Harmonised Guideline Q8(R2): Pharmaceutical
    Development*, sections 2.3--2.5 (August 2009).
    [Official ICH PDF](https://database.ich.org/sites/default/files/Q8_R2_Guideline.pdf).
16. U.S. Food and Drug Administration. *Q8, Q9, & Q10 Questions and Answers -- Appendix:
    Q&As from Training Sessions (Q8, Q9, & Q10 Points to Consider)* (accessed 2026-09-02).
    [Official FDA guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q8-q9-q10-questions-and-answers-appendix-qas-training-sessions-q8-q9-q10-points-consider).
17. Dawid, A. P. The well-calibrated Bayesian. *Journal of the American Statistical
    Association* **77**, 605--610 (1982).
    [doi:10.1080/01621459.1982.10477856](https://doi.org/10.1080/01621459.1982.10477856).
18. Hadji, A. & Szabó, B. Can we trust Bayesian uncertainty quantification from Gaussian
    process priors with squared exponential covariance kernel? *SIAM/ASA Journal on
    Uncertainty Quantification* **9**, 185--230 (2021).
    [doi:10.1137/19M1253010](https://doi.org/10.1137/19M1253010).
19. Talts, S., Betancourt, M., Simpson, D., Vehtari, A. & Gelman, A. Validating Bayesian
    inference algorithms with simulation-based calibration. arXiv:1804.06788 (2018).
    [doi:10.48550/arXiv.1804.06788](https://doi.org/10.48550/arXiv.1804.06788).
20. Clopper, C. J. & Pearson, E. S. The use of confidence or fiducial limits illustrated in
    the case of the binomial. *Biometrika* **26**, 404--413 (1934).
    [doi:10.1093/biomet/26.4.404](https://doi.org/10.1093/biomet/26.4.404).
21. Chow, C. K. On optimum recognition error and reject tradeoff. *IEEE Transactions on
    Information Theory* **16**, 41--46 (1970).
    [doi:10.1109/TIT.1970.1054406](https://doi.org/10.1109/TIT.1970.1054406).
22. Geifman, Y. & El-Yaniv, R. Selective classification for deep neural networks. *Advances
    in Neural Information Processing Systems* **30** (2017).
    [Official proceedings PDF](https://papers.nips.cc/paper_files/paper/2017/file/4a8423d5e91fda00bb7e46540e2b0cf1-Paper.pdf).

## Source-selection note

Technical assertions above are grounded in original research articles/conference papers or
official NIST, ICH, and FDA materials. Search aggregators were used only to locate records;
they are not cited as authority. No priority claim was inferred from search-result counts,
and absence from this focused review is not evidence that no other related work exists.
