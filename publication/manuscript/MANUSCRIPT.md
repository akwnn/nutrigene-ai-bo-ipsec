# From point optimization to operating-region decisions: a fixed-well evaluation of conservative Gaussian-process design for cell manufacturing

## Abstract

Cell-manufacturing development commonly seeks a best recipe, although an operational decision may require a region of conditions expected to remain above a specification. These are different estimands: point optimization does not establish simultaneous acceptability over a region. We evaluated SPADE, a fixed-well, multi-round workflow that adapts established Gaussian-process (GP) level-set design and conservative Vorob'ev-set estimation to noisy assay campaigns with an explicit empty-set outcome. The closest antecedent, Azzimonti *et al.*, already formulated maximum-volume conservative estimation within nested Vorob'ev candidates; SPADE's contribution is therefore assay-oriented integration and bounded empirical comparison, not new excursion-set theory. At 48 wells and relative noise 0.25, SPADE at five rounds showed no detectable regret difference from qLogNEI at ten rounds (SPADE minus qLogNEI `-0.0005`, 95% bootstrap CI `[-0.0221,0.0207]`; `n=160`). At five matched rounds, leave-one-family-out analysis descriptively gave greater certified volume than qLogNEI under the conditional flat-cell bootstrap (`+0.000855`, 95% CI `[0.000691,0.001028]`; `n=320` dependent family-seed-prevalence cells, not campaigns). A specified response-surface design of experiments (DoE) found a better point recipe in three rounds (`+0.1026` SPADE-minus-DoE regret), yet at prevalence 0.30 contained truth in only 85 of 122 answered cells (screened) or 77 of 134 (unscreened), compared with 66 of 66 for SPADE. SPADE selected `c=1` within the DC data; neither DoE arm passed at any tested inflation, so its diagnostic counts are reported at baseline `c=1`. Across five families and five prevalences, SPADE answer rate at `c=1.0` was descriptively associated with mean seed-specific true margin-to-noise (Spearman rho `0.9880098603`; 25 nested cells); no naive correlation p-value is interpreted. These results expose a trade-off among optimization, regional decisions, abstention, and operational rounds. They do not establish frequentist coverage, a regulatory design space, or prospective wet-lab validity.

**Keywords:** abstention; Bayesian optimization; cell manufacturing; design of experiments; excursion set; Gaussian process; operating region; uncertainty quantification.

## 1. Introduction

A best tested condition and a defensible operating region answer different scientific questions. Expected improvement and modern Bayesian optimization (BO) allocate expensive evaluations to improve an objective [9--12]. Response-surface methodology combines designed experiments with low-order models for target attainment and optimization [13,14]. Neither objective alone answers whether every point in a reported region exceeds a specification with a joint uncertainty statement. This distinction matters when an assay campaign is constrained both by wells and by sequential experimental rounds.

For latent response `f`, threshold `tau`, and domain `X`, the acceptable region `Gamma={x in X:f(x)>=tau}` is an excursion set. Sequential GP learning of excursion or level sets, including batch and stepwise-uncertainty-reduction strategies, is established [1--3]. Posterior excursion sets can be summarized by coverage functions and nested Vorob'ev quantiles [5--7], while simultaneous excursion probabilities differ from pointwise membership probabilities [8]. Most importantly here, Azzimonti *et al.* defined a conservative estimate as a maximum-volume member of a candidate family satisfying `P(C subset Gamma | data)>=alpha`, used nested Vorob'ev quantiles as candidates, and developed batch-sequential designs [4]. That work is a close antecedent to SPADE's certification core and constrains novelty claims about its mathematics.

The applied question is how this machinery behaves in a noisy, fixed-well assay workflow when judged on optimization and regional outcomes. Posterior credibility is conditional on the fitted model and need not provide nominal repeated-sampling coverage under misspecification or empirical-Bayes fitting [17--19]. An empty conservative set is logically valid but operationally uninformative, so containment among answered cases must accompany answer rate. This parallels established reject-option and selective-prediction reporting [21,22], although SPADE's set-level abstention is not selective classification.

We ask whether SPADE preserves point-recipe quality relative to one implementation of noisy BO; whether matched-round adaptive sampling changes certified volume; whether a tested low-order DoE workflow trades point optimization against empirical regional containment; and what explains abstention across synthetic families and target prevalences. “Operating region” is deliberate: ICH design-space and process-validation concepts require evidence beyond this synthetic study [15,16].

### 1.1 Contribution and novelty boundary

Table 1 separates established ingredients, application-specific adaptation, and empirical contribution. The intended claim is integration plus evidence, not theoretical priority or universal superiority.

**Table 1. Contribution and novelty map.**

| Element | Classification | Scope in this study |
|---|---|---|
| GP excursion sets and boundary-focused sequential design | Established ingredient | Used within the GP level-set and batch-SUR tradition [1--4]. |
| Posterior excursion draws and nested Vorob'ev quantiles | Established ingredient | Used as established random-set summaries [4--8]. |
| High-volume candidate satisfying joint posterior containment | Established ingredient; close antecedent | Azzimonti *et al.* [4] give essentially this formulation. SPADE searches registered nested candidates on a finite grid, not all measurable subsets. |
| qLogNEI and low-order response-surface DoE | Established comparator ingredients | qLogNEI is one noisy point-optimization policy [10--12]; the DoE pipeline is study-specific [13,14]. |
| Per-well plug-in variances, 48-well schedules, eight-well later batches, empty answer | SPADE-specific assay adaptation | Engineering adaptation to the operational setting; not new heteroscedastic-GP or abstention theory. |
| LC/C3 held-out-family inflation and DC/C2 in-sample selection/fallback | Study-specific analysis adaptation | LC selects inflation without the held-out family. In DC, SPADE selects `c=1` in sample; neither DoE arm passes, so DoE is diagnosed at baseline `c=1`. Neither procedure is distribution-free or prospectively validated. |
| Common regional estimator for SPADE, qLogNEI, and DoE observations | Comparative-design contribution | Isolates acquisition/design within the tested pipelines. |
| Regret, volume, answer-rate, and truth-containment results | Empirical contribution | Bounded to the named families, seeds, targets, noise, schedules, grid, and implementation. |

## 2. Materials and methods

### 2.1 Study design

Synthetic programs used six normalized factors, 48 wells, relative noise `sigma_rel=0.25`, a 20,000-point truth grid, a 2,000-point scoring subset, 4,096 joint posterior draws, and reported assurance `alpha=0.95`. Families were Ackley, Hartmann6, biphasic Hill, Levy, and Rosenbrock. Hill varied by registered instance; the others used fixed landscapes with design/noise varying by seed. These are structural test functions, not fits to endothelial-cell measurements.

Table 2 gives exact arms, wells, rounds, seeds, prevalences, and evidence status. A round is a sequential decision opportunity, not extra wells: all synthetic arms used 48 wells. SPADE R3 used `32+8+8`, SPADE R5 used `16+8+8+8+8`, and qLogNEI R10 used its registered 14-point opening followed by batches totaling 48 wells. Fewer rounds therefore do not imply fewer wells.

**Table 2. Study and benchmark overview.**

| Program | Arms and operational rounds used here | Wells | Families and seeds | Target prevalences | Status and role |
|---|---|---:|---|---|---|
| DC | Screened DoE R3; unscreened DoE R3; SPADE R5; qLogNEI R10 | 48 | Five families x 32 seeds | 0.70, 0.30 | Complete active grid; confirmatory/core C1/C2; C1 supersedes the cross-run estimate. |
| LC | SPADE R3/R5; qLogNEI R3/R5/R10 | 48 | Five families x 32 seeds | 0.30, 0.10 | Complete active grid; confirmatory/core C3 and SPADE side of C4; LOFO inflation. |
| LA/C4 | One-shot LHS R1 paired with LC SPADE R3 | 48 | Four common families x 20 common seeds | Regret paired by family and seed | Complete active grid; frozen development lineage used as core C4 support; exactly `4 x 20=80` pairs; unmatched Hill and seeds 20--31 excluded, not imputed. |
| TAU | SPADE R5; qLogNEI R5 | 48 | Five families x 64 seeds | 0.70, 0.50, 0.30, 0.20, 0.10 | Complete active grid; confirmatory/core descriptive gate for C5/C6; `c={1,1.5,2,3}`. |
| TT | Committed SPADE R5; target-aligned SPADE R5; qLogNEI R5 | 48 | Five families x 32 seeds | 0.70, 0.30 | Complete active grid; mechanism study S1. |
| In-house iPSC-EC | Retrospective GP diagnostic; no adaptive rounds | 12 observed tubes | No campaign seeds | Absolute thresholds | Provisional support; `awaiting_human_signoff`; not prospective validation. |
| Hall/Ogle | Retrospective GP diagnostic; no adaptive rounds | 23 usable stage-1 compositions | No campaign seeds | Multiples of observed median | Published-data support [23]; not a prospective SPADE campaign. |

### 2.2 SPADE and regional decision rule

SPADE fits a GP to coordinates `X`, normalized outcomes `Y`, and plug-in observation variances `Yvar`. The synthetic oracle supplied per-well variances for SPADE and qLogNEI; DoE adapters used the registered constant plug-in variance. SPADE begins with a space-filling batch, refits after each later batch, and samples near the uncertain boundary using its registered conservative-set straddle acquisition. This implementation is related to, but does not inherit guarantees from, prior level-set losses [1--4].

For posterior draw `b`, `Gamma^(b)={x:f^(b)(x)>=tau}` is evaluated on the registered grid. The algorithm scans 64 nested Vorob'ev levels and returns the largest scanned candidate whose same-draw Monte Carlo joint model-containment estimate reaches `alpha=0.95`; posterior inflation `c` is selected from `{1.0,1.5,2.0,3.0}`. “Largest” means largest among these finite candidates, not a global continuous-domain optimum. No non-empty passing candidate yields abstention.

Recorded outcomes are `answered`, truth `contained` conditional on an answer, answer rate, conditional empirical containment, certified grid volume, and simple regret. Truth containment uses the known synthetic surface; model-internal containment is not validation. The registered gate requires a one-sided 95% Clopper--Pearson lower bound at least 0.90 and answer rate at least 0.05. These bounds summarize the observed answered-cell proportion under ordinary binomial assumptions, not cluster-aware campaign-level coverage [20].

### 2.3 Comparators and calibration

qLogNEI used the same well budget and GP model but optimized noisy expected improvement [10--12]. Its observations then entered the common regional estimator; a qLogNEI certificate is common post-processing, not an intrinsic qLogNEI output. Screened DoE used a 20-run six-factor screen reduced to four factors, a 27-run face-centred response-surface design, and one confirmation well. The unscreened arm omitted screening while retaining the registered budget and low-order model. These arms do not represent all classical, optimal, robust, or model-based designs.

Calibration differed by claim. LC/C3 selected the smallest passing `c` on four families and evaluated it on the held-out fifth; selection and scoring pooled prevalences 0.30 and 0.10. In DC/C2, SPADE selected `c=1` using the DC cells themselves. Neither DoE arm passed the registered gate at any tested inflation, so the screened and unscreened DoE counts are baseline `c=1` diagnostics rather than selected passing certificates. C2 is in-sample and descriptive, not the held-out-family procedure used for C3.

### 2.4 Statistical analysis and real-data support

Contrasts were paired by `(family,seed)` or `(family,seed,prevalence)`. Frozen analysers used 8,000 ordinary nonparametric bootstrap resamples of flat contrast rows, percentile intervals, and two-sided bootstrap tail-area proportions relative to zero. Because observations can share families, landscapes, seeds, prevalences, or campaigns, these are conditional descriptive summaries under a cell-exchangeability approximation and may be too narrow under within-cluster dependence. C1 used a regret smallest effect of interest of 0.02; crossing its boundary was not interpreted as equivalence.

For C5, each of 25 family-prevalence cells paired SPADE answer rate at `c=1.0`, `alpha=0.95` with the mean of 64 unique seed-specific true margin-to-noise values. Median margin and qLogNEI answer rate were sensitivities. Cells are nested within five families and share ordered prevalences; the Spearman coefficient is descriptive, without a naive independence-based p-value.

Retrospective support used an in-house iPSC-EC candidate dataset and the published Hall--Ogle stage-1 extraction [23]. Mean-marginalized covariance propagated estimated-mean uncertainty. Leave-one-out (LOO) inflation evaluated held-out observation prediction, not latent-response uncertainty or prospective set containment.

### 2.5 Display-item status

Tables 1--3 are the current manuscript display items. Existing repository figures describe historical pipeline states and are not cited as current results. A figure package regenerated from the active pipeline is pending; no conclusion depends on it.

## 3. Results

Table 3 gives the exact analysis populations and status. Regional-containment rows state target, noise, assurance, wells, rounds, seeds, answered denominator, and contained numerator locally.

**Table 3. Primary and supporting results.**

| ID | Analysis population and settings | Result | Interpretation/status |
|---|---|---|---|
| C1 | DC; five families x 32 seeds (`n=160`); 48 wells; SPADE R5 vs qLogNEI R10; noise 0.25 | Regret `-0.0005`, 95% CI `[-0.0221,0.0207]`, `p=0.96` | No detectable difference; not equivalence. |
| C2 | DC, prevalence 0.30; five families x 32 seeds (160 eligible/arm); 48 wells; noise 0.25; `alpha=0.95`; SPADE R5 selected `c=1`; neither DoE R3 arm passed at any tested inflation, so DoE uses baseline/fallback `c=1` | SPADE 66/160 answered, 66/66 contained, `1.0000`, LB `0.9556`; screened DoE 122/160 answered, 85/122 contained, `0.6967`; unscreened DoE 134/160 answered, 77/134 contained, `0.5746` | Perfect observed SPADE containment among answers; low observed conditional DoE containment despite frequent answers. |
| C2 adverse | DC; five families x 32 seeds (`n=160`); 48 wells; SPADE R5 vs screened DoE R3; noise 0.25 | SPADE-minus-DoE regret `+0.1026`, 95% CI `[+0.0486,+0.1578]`, `p=0.0003` | DoE found the better point recipe with fewer rounds. |
| C3 | LC R5 vs R5; five families x 32 seeds x prevalences 0.30 and 0.10 (`n=320` cells); 48 wells; noise 0.25; `alpha=0.95`; LOFO inflation | SPADE-minus-qLogNEI volume `+0.000855`, 95% CI `[+0.000691,+0.001028]`, `p<0.0001` | Greater matched-round volume; conditional flat-cell bootstrap. |
| C4 | LC SPADE R3 vs LA LHS R1; four named families x 20 common seeds (`4 x 20=80`); 48 wells; noise 0.25 | SPADE-minus-LHS regret `-0.0783`, 95% CI `[-0.1104,-0.0490]` | Lower regret than one-shot space filling. |
| C5 | TAU; five families x five prevalences; 64 seeds; SPADE R5; 48 wells; noise 0.25; `alpha=0.95`; `c=1.0` | Descriptive rho `0.9880098603` over 25 nested cells; median-margin rho identical; qLogNEI sensitivity `0.9682461469` | Oracle-derived explanation; no naive p inference. |
| C6 | Hill, prevalence 0.70; 64 seeds; SPADE/qLogNEI R5; 48 wells; noise 0.25; `alpha=0.95`; `c=1.0` | SPADE 40/64 answered, 40/40 contained, LB `0.9278`; qLogNEI 27/64 answered, 27/27 contained, LB below `0.90` | Both had perfect observed containment; qLogNEI was two answers below the registered minimum perfect-containment count. |
| S1 | TT, prevalence 0.30; five families x 32 seeds; 48 wells; noise 0.25; committed vs target-aligned SPADE R5 | Volume `+0.000425`, 95% CI `[-0.000022,+0.000875]`; regret `+0.0301`, 95% CI `[+0.0169,+0.0450]`, `p<0.0001` | Adoption gate failed; Hartmann6/Ackley effects cancelled. |
| S2/S3 | Retrospective synthetic, in-house, and Hall/Ogle diagnostics | Mean posterior marginal SD over the candidate grid widened `1.004x--1.011x` on benchmarks, `484x` in-house, and `297x` on Hall/Ogle; LOO `c=0.712` in-house, `c=0.526` published | Supporting stdout-reproduced diagnostics without structured result objects or numerical guards. |

### 3.1 Point optimization

The DC SPADE R5 minus qLogNEI R10 regret contrast was `-0.0005` (95% CI `[-0.0221,0.0207]`, `p=0.96`; `n=160`; Table 3). The interval extends slightly beyond the registered +/-0.02 effect boundary. It supports no detectable difference, not equivalence. Both used 48 wells; SPADE used fewer rounds, but time and cost were not measured.

### 3.2 Matched rounds and one-shot sampling

For C3, five-round certified-volume difference was `+0.000855` (95% CI `[+0.000691,+0.001028]`, `p<0.0001`; Table 3). Its denominator is five families x 32 seeds x two prevalence cells (`n=320`), not 320 independent campaigns. Inflation was selected without the held-out family. The analogous three-round positive volume claim was withdrawn after extension to 32 seeds.

At three rounds, SPADE had lower regret than one-shot LHS (`-0.0783`, 95% CI `[-0.1104,-0.0490]`; `n=80`; Table 3). The denominator is four named families x 20 common seeds. This supports the frozen adaptive-versus-one-shot comparison, not a general claim that sequential design improves every outcome.

### 3.3 DoE traded regional containment for faster point optimization

Screened DoE R3 found a better recipe than SPADE R5: SPADE-minus-DoE regret was `+0.1026` (95% CI `[+0.0486,+0.1578]`, `p=0.0003`; `n=160`). At prevalence 0.30, noise 0.25, `alpha=0.95`, 48 wells, and five families x 32 seeds, SPADE selected `c=1`, answered 66/160, and contained truth in 66/66. Neither DoE arm passed at any tested inflation, so its diagnostic counts are reported at baseline `c=1`: screened DoE answered 122/160 and contained 85/122; unscreened DoE answered 134/160 and contained 77/134 (Table 3). Removing screening did not repair the low observed conditional containment despite frequent answers. Because SPADE inflation was selected and evaluated within the same DC cells and the DoE rows are fallback diagnostics, these are in-sample descriptive results, not transportable 95% coverage or an indictment of DoE as a class.

### 3.4 Certifiability and margin-to-noise

Across five families and prevalences 0.70, 0.50, 0.30, 0.20, and 0.10, SPADE answer rate at `c=1.0`, `alpha=0.95` was descriptively associated with the mean of 64 unique seed-specific true margin-to-noise values (rho `0.9880098603`; 25 nested cells; Table 3). Median-margin rho was identical; qLogNEI sensitivity was `0.9682461469`. Shared families and prevalences make cells dependent and nonexchangeable; no naive correlation p-value is reported. Margin-to-noise uses latent truth and is not a prospective diagnostic.

The biology-shaped but synthetic Hill family remained within the analysis. At prevalence 0.70, 48 wells, R5, 64 seeds, noise 0.25, `alpha=0.95`, and `c=1.0`, SPADE answered 40/64 and contained truth in 40/40 (LB `0.9278`). qLogNEI answered 27/64 and contained 27/27. The limitation was answer count under the registered gate, not inability of BO to return contained regions.

### 3.5 A plausible mechanism failed

Target-aligning the acquisition changed volume by `+0.000425` (95% CI `[-0.000022,+0.000875]`) and worsened regret by `+0.0301` (95% CI `[+0.0169,+0.0450]`, `p<0.0001`; Table 3). Hartmann6 improved and Ackley worsened, cancelling in aggregate. The mechanism did not earn adoption.

### 3.6 Real-cell support

Mean marginalization increased the mean posterior marginal SD over the candidate grid by `484x` in-house and `297x` in Hall--Ogle [23], versus `1.004x--1.011x` in synthetic diagnostics. Observation-prediction LOO inflation differed (`c=0.712` in-house; `c=0.526` published). These are retrospective, stdout-reproduced support without structured result objects or automated numerical guards. In-house gates remain `awaiting_human_signoff`; neither dataset is a prospective SPADE campaign.

## 4. Discussion

This study separates point optimization from a conditional regional decision. With 48 wells, screened DoE found a better point recipe in fewer rounds, and qLogNEI showed no detectable regret difference from SPADE. SPADE instead yielded greater conservative-set volume at matched five rounds and perfect observed containment among its answered DC regions. Optimization and certification are complementary objectives, not one ranking.

The core mathematics is prior art. GP level-set learning, batch SUR, random excursion sets, Vorob'ev summaries, and simultaneous excursion probabilities are established [1--8]. Azzimonti *et al.* [4] are especially close: their estimator already maximizes volume over nested Vorob'ev candidates under posterior set inclusion. SPADE's contribution is the fixed-well assay adaptation, empirical inflation protocols, common comparator scoring, explicit abstention, and bounded evaluation.

Abstention is central. Perfect containment can coexist with few answers, while frequent answers can be over-confident. Hill shows why answered and contained counts must travel together: qLogNEI's 27/27 contained answers do not support saying BO could not certify. This reporting follows established rejection principles [21,22] without claiming abstention as novel.

Inference remains conditional. LC/C3 holds out a family for inflation selection. DC/C2 selects SPADE's `c=1` in the same data, while neither DoE arm passes and both are diagnosed at baseline `c=1`. Neither procedure converts nominal posterior assurance into repeated-campaign coverage. Flat bootstrap rows share families, landscapes, seeds, and prevalences, while pooled Clopper--Pearson summaries assume an ordinary binomial model [20]. Cluster- or hierarchy-aware analyses are needed for population claims.

The failed target-aligned mechanism shows that plausibility did not translate to aggregate benefit and harmed regret. It argues against complexity without empirical adoption criteria. Noise is the main biological barrier: headline benchmarks use relative noise 0.25, whereas no tested arm certified near measured real-assay noise 0.68 in the retained exploratory ceiling analysis. Hill was not fitted to endothelial data; in-house CD31 gates await review; and LOO prediction does not identify latent-function uncertainty. Replicate tubes and a prospective prespecified campaign are required.

Comparator and operational scope are limited. qLogNEI is one BO acquisition. The DoE comparator is one low-order workflow. Wells were constant but rounds ranged from one to ten; operational benefit cannot be inferred without measured time or cost. R4, broader assurance/Vorob'ev-level sweeps, larger budgets, new families/noise regimes, and continuous-domain validation remain open. The returned object is a candidate operating region, not an ICH/FDA-qualified design space, process validation, or control strategy [15,16].

## 5. Conclusion

At 48 wells and relative noise 0.25, SPADE showed no detectable regret difference from one qLogNEI implementation, returned greater conservative-set volume at matched five rounds, and showed perfect observed containment among answered regions where the tested DoE pipelines were over-confident. DoE nevertheless found a better point recipe in fewer rounds, and SPADE sometimes abstained. The bounded lesson is to distinguish point optimization from regional certification, permit an empty answer, and report answer rate with conditional containment. Prospective biological validation and dependence-aware inference remain necessary.

## Data and code availability

Canonical synthetic results, frozen protocols, analysis scripts, selected-value guard, and audit ledgers are included in this repository; commands are listed in `publication/evidence/reproduction-map.md`. The guard covers selected C1 and C3--C6 scalars, not every number or inferential assumption. In-house data are retained with checksums and role annotations; access, reuse, licensing, and laboratory policy require author/institutional confirmation. Historical figures are not current evidence; the current figure package is pending.

## Declarations requiring author or journal completion

The following metadata were not available and are not inferred:

- [ ] Authors, affiliations, corresponding author, and ORCIDs.
- [ ] CRediT contributions approved by all authors.
- [ ] Funding/grant identifiers or explicit no-funding statement.
- [ ] Competing interests for every author.
- [ ] Ethics oversight/approval or exemption for in-house human-derived cell material, and any required consent statement.
- [ ] Data restrictions, repository identifiers, and release license reconciled with laboratory policy.
- [ ] Code archive DOI/version, license, and submitted environment record.
- [ ] Acknowledgements, material-transfer terms, and third-party permissions.
- [ ] Target-journal AI-use, protocol-registration, reporting-guideline, and source-data statements.

## References

1. Gotovos A, Casati N, Hitz G, Krause A. Active learning for level set estimation. *IJCAI*. 2013:1344--1350. https://www.ijcai.org/Proceedings/13/Papers/202.pdf
2. Bect J, Ginsbourger D, Li L, Picheny V, Vazquez E. Sequential design of computer experiments for the estimation of a probability of failure. *Stat Comput*. 2012;22:773--793. https://doi.org/10.1007/s11222-011-9241-4
3. Chevalier C, Bect J, Ginsbourger D, et al. Fast parallel kriging-based stepwise uncertainty reduction with application to the identification of an excursion set. *Technometrics*. 2014;56:455--465. https://doi.org/10.1080/00401706.2013.860918
4. Azzimonti D, Ginsbourger D, Chevalier C, Bect J, Richet Y. Adaptive design of experiments for conservative estimation of excursion sets. *Technometrics*. 2021;63:13--26 (online 2019). https://doi.org/10.1080/00401706.2019.1693427
5. Heinrich P, Stoica RS, Tran VC. Level sets estimation and Vorob'ev expectation of random compact sets. *Spatial Stat*. 2012;2:47--61. https://doi.org/10.1016/j.spasta.2012.10.001
6. Chevalier C, Ginsbourger D, Bect J, Molchanov I. Estimating and quantifying uncertainties on level sets using the Vorob'ev expectation and deviation with Gaussian process models. In: *mODa 10*. Springer; 2013:35--43. https://doi.org/10.1007/978-3-319-00218-7_5
7. Azzimonti D, Bect J, Chevalier C, Ginsbourger D. Quantifying uncertainties on excursion sets under a Gaussian random field prior. *SIAM/ASA J Uncertain Quantif*. 2016;4:850--874. https://doi.org/10.1137/141000749
8. Bolin D, Lindgren F. Excursion and contour uncertainty regions for latent Gaussian models. *J R Stat Soc B*. 2015;77:85--106. https://doi.org/10.1111/rssb.12055
9. Jones DR, Schonlau M, Welch WJ. Efficient global optimization of expensive black-box functions. *J Glob Optim*. 1998;13:455--492. https://doi.org/10.1023/A:1008306431147
10. Letham B, Karrer B, Ottoni G, Bakshy E. Constrained Bayesian optimization with noisy experiments. *Bayesian Anal*. 2019;14:495--519. https://doi.org/10.1214/18-BA1110
11. Balandat M, Karrer B, Jiang DR, et al. BoTorch: a framework for efficient Monte-Carlo Bayesian optimization. *NeurIPS*. 2020;33:21524--21538.
12. Ament S, Daulton S, Eriksson D, Balandat M, Bakshy E. Unexpected improvements to expected improvement for Bayesian optimization. *NeurIPS*. 2023;36:20577--20612.
13. Box GEP, Wilson KB. On the experimental attainment of optimum conditions. *J R Stat Soc B*. 1951;13:1--38. https://doi.org/10.1111/j.2517-6161.1951.tb00067.x
14. National Institute of Standards and Technology. *NIST/SEMATECH e-Handbook of Statistical Methods*, sec. 5.3.3. Accessed 2026-09-02. https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm
15. International Council for Harmonisation. *ICH Q8(R2): Pharmaceutical Development*. 2009. https://database.ich.org/sites/default/files/Q8_R2_Guideline.pdf
16. US Food and Drug Administration. *Q8, Q9, & Q10 Questions and Answers--Appendix*. Accessed 2026-09-02. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q8-q9-q10-questions-and-answers-appendix-qas-training-sessions-q8-q9-q10-points-consider
17. Dawid AP. The well-calibrated Bayesian. *J Am Stat Assoc*. 1982;77:605--610. https://doi.org/10.1080/01621459.1982.10477856
18. Hadji A, Szabo B. Can we trust Bayesian uncertainty quantification from Gaussian process priors with squared exponential covariance kernel? *SIAM/ASA J Uncertain Quantif*. 2021;9:185--230. https://doi.org/10.1137/19M1253010
19. Talts S, Betancourt M, Simpson D, Vehtari A, Gelman A. Validating Bayesian inference algorithms with simulation-based calibration. arXiv:1804.06788. 2018. https://doi.org/10.48550/arXiv.1804.06788
20. Clopper CJ, Pearson ES. The use of confidence or fiducial limits illustrated in the case of the binomial. *Biometrika*. 1934;26:404--413. https://doi.org/10.1093/biomet/26.4.404
21. Chow CK. On optimum recognition error and reject tradeoff. *IEEE Trans Inf Theory*. 1970;16:41--46. https://doi.org/10.1109/TIT.1970.1054406
22. Geifman Y, El-Yaniv R. Selective classification for deep neural networks. *NeurIPS*. 2017;30.
23. Hall ML, Lin W-H, Ogle BM. Optimizing extracellular matrix for endothelial differentiation using a design of experiments approach. *Sci Rep*. 2025;15:24479. https://doi.org/10.1038/s41598-025-09256-9
