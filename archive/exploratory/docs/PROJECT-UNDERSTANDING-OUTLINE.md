# SPADE: A Publication-Ready Project and Manuscript Outline

## Proposed title

**From Optimal Recipes to Assured Operating Regions: A Two-Round Strategy for Design-Space Learning under Limited Experimental Budgets**

Alternative computational title: **SPADE: Two-Round Learning of Acceptable Formulation Regions with Point-Optimization Parity**

Alternative biology-facing title: **Beyond the Best Well: Learning Reliable Formulation Windows with Two Experimental Rounds**

---

## How to use this document

This document is the main writing blueprint for the paper. It explains the scientific problem, the biological interpretation, the synthetic-data construction, the algorithms, the implementation, the statistical design, the complete result hierarchy, the cited literature and its purpose, and the proposed figure program. Its sections are written in manuscript-ready prose so that a scientific writer can convert them into a full draft without reconstructing the project from scripts or historical experiment notes.

The paper should be SPADE-first. The earlier Bayesian-optimization-versus-response-surface experiments remain essential, but their role is to demonstrate why optimizing one nominated recipe is an incomplete objective when the laboratory needs a defensible operating region. The prospective SPADE study is the principal evidence for method-level performance. Retrospective re-scoring and diagnostic experiments supply motivation, mechanism, and scope.

The historical prospective study and its corrected clean-checkout release are complete. The causal comparison is negative: boundary-targeted `m0` did not improve map error over an equal-well random second plate (effect −0.00188 in the registered sign convention, 95% interval −0.00624 to +0.00261, Holm $p=0.4108$). A newer 48-evaluation joint SPADE protocol is implemented and frozen around the retained τ-quantile correction, scrambled-Sobol openings, and common learned-noise GP. Its development selection and untouched lockbox outcomes have not been run, so the manuscript must keep historical results separate from that new protocol.

---

# 1. Manuscript-level summary

## 1.1 Draft abstract

Multicomponent biological formulations are commonly optimized by selecting a single condition with a high measured or model-predicted response. That formulation-centric objective is insufficient when experimental handoff requires an operating region: a set of compositions expected to satisfy a prespecified performance threshold despite limited data and assay noise. We developed SPADE, a two-round, 48-well strategy that begins with a 40-point space-filling design, fits a heteroscedastic Gaussian-process surrogate, and allocates eight additional wells to reduce uncertainty near the estimated acceptance boundary before constructing a probabilistic design-space map and a conservative excursion-set certificate.

We evaluated SPADE in a preregistered computer experiment using synthetic six- and eight-factor response landscapes, matched 48-well budgets, and comparators spanning one-shot space-filling designs, batch Bayesian optimization, screened response-surface methodology, and a full-dimensional unscreened central-composite design where arithmetically feasible. The primary target condition was a six-factor biphasic Hill landscape under lower benchmark noise. The primary map outcome was normalized symmetric-difference error between the estimated and true acceptable regions; point performance was evaluated by simple regret under a common posterior-mean terminal rule.

In the target condition, the three model-directed SPADE variants had symmetric-difference errors of 0.1770–0.1804. The equal-well random-second-plate control achieved 0.1785, so the registered primary `m0` arm at 0.1804 was not the best SPADE-related arm and did not establish value for boundary targeting. The specialist comparators achieved 0.1913 for Sobol, 0.2067 for qLogEI, 0.2131 for qLogNEI, 0.2502 for unscreened classical design, and 0.2580 for screened response-surface methodology. qLogNEI produced the strongest BO point regret, 0.0750, whereas primary SPADE achieved 0.0844. The mean gap was 0.00937 with a 95% interval of 0.00258–0.01615, wholly inside the prespecified 0.02 practical margin. SPADE required two experimental decision rounds, compared with ten for batch Bayesian optimization at the same 48-well budget.

The distinction between point and region objectives reproduced on multimodal Hartmann landscapes: Bayesian optimization achieved lower point regret, whereas SPADE variants achieved lower map error at both six and eight dimensions. Certificate evidence was narrower than mapping performance. Prospective cross-fit containment was not shown to fall below nominal on the Hill benchmark, but the weakest confirmatory cell had only 13 non-empty certificates and a wide interval. Cross-family prospective evidence was not uniformly conclusive, and an independent five-family analysis found high-assurance under-coverage on Levy and Rosenbrock landscapes while SPADE frequently declined to certify on Ackley and Hartmann landscapes.

These findings establish the evaluated SPADE workflow as a bounded certification-first case study rather than a universally superior optimizer. Its strongest supported contribution is target-regime map competitiveness with practical point-regret parity and fewer decision rounds; its targeted second plate did not earn a causal advantage. The raw prospective artifacts are now tracked, clean validation passes 9/9 checks, and all eight prospective figures are generated. Wet-lab validation and complete cross-family calibration remain absent, while the new joint protocol still requires development selection and untouched lockbox evaluation before it can support any outcome claim.

## 1.2 Draft significance statement

Experimental optimization is usually judged by the best recipe it produces, but many laboratories need a robust window of acceptable recipes rather than one nominal optimum. This project shows that point quality and operating-region quality can rank the same experimental campaigns in opposite orders. SPADE directly targets the second deliverable. Under a fixed 48-well budget, it generated leading design-space maps in two experimental rounds while remaining practically close to ten-round Bayesian optimization on the best predicted recipe. The work also demonstrates why a sharp map, a calibrated probability model, and a valid certificate are related but non-equivalent claims.

## 1.3 Central thesis

The central claim is not that SPADE wins every optimization problem. The defensible claim is narrower and more useful:

> When the experimental deliverable is an acceptable formulation region rather than one best formulation, a two-round spread-and-refine strategy can produce a stronger design-space map than point-focused or classical comparators while retaining practical point-regret parity in a prespecified target regime.

The paper has three linked contributions. First, it demonstrates that the scientific object being optimized—one point or an entire acceptable set—can reverse method rankings. Second, it introduces and prospectively evaluates a two-round workflow designed around the set-estimation objective. Third, it separates map accuracy, probabilistic calibration, and conservative certification, showing that success on one does not prove the others.

---

# 2. Introduction

## 2.1 Biological and experimental problem

Optimizing cell-culture media, extracellular-matrix compositions, bioprocess conditions, or multicomponent formulations requires searching a continuous space that grows exponentially with the number of controllable factors. A modest grid of five levels across six ingredients already contains $5^6=15{,}625$ combinations, far beyond the capacity of a typical experimental campaign. Laboratories therefore use structured design of experiments, response-surface methodology, Bayesian optimization, or space-filling designs to choose a small set of informative conditions.

Most optimizer studies compress the final result to one formulation. The method is rewarded if its nominated point lies near the unknown optimum. This is appropriate when the laboratory wants one carry-forward recipe and can reproduce it precisely. It is not sufficient when manufacturing variability, biological heterogeneity, formulation tolerances, or regulatory expectations require an operating region within which many recipes remain acceptable. A high-performing point can coexist with a poor map of the surrounding formulation space, and a method that accurately maps an acceptable region need not locate the global optimum most efficiently.

This distinction is central to quality-by-design thinking. A design space is not merely a wide confidence interval around one optimum. It is a subset of the factor space associated with an explicit performance threshold and an explicit level of uncertainty. Establishing such a region requires broad spatial information, calibrated uncertainty, and an honest accounting of cases in which the data support no non-empty certified region.

## 2.2 Why conventional BO-versus-DoE comparisons are difficult to interpret

Bayesian optimization and response-surface methodology are not single algorithms. A complete workflow includes the sampling design, fitted surrogate, acquisition or relocation rule, experimental budget, number of adaptive rounds, and final selection rule. Published studies vary across all of these components. Some compare executed workflows at equal experiment counts; others compare an adaptive campaign with a predicted full-factorial or standard-DoE requirement; some nominate the largest measured response; others nominate a posterior-mean optimum or a response-surface stationary point.

The repository's matched-campaign experiments show why these distinctions matter. On identical synthetic landscapes and equal 48-well budgets, the apparent winner changes when the final formulation is selected by a single noisy observation, a fitted model, an in-region rule, or confirmation. The procedures can physically test similarly good recipes yet differ substantially in whether the terminal rule recognizes them. Consequently, a claim that one method “finds better formulations” may actually combine search, identification, extrapolation, and final decision policy.

These results motivate a more fundamental change in objective. If the laboratory wants an operating region, point regret should not remain the only score. The acceptable set must be estimated and compared directly with the truth available in simulation.

## 2.3 SPADE as the response to that gap

SPADE is a two-round, 48-well strategy for learning an acceptable formulation region. It spends 40 wells on broad coverage of all factors, fits a Gaussian-process model with known plug-in observation variance, then allocates eight wells to regions that are both uncertain and near the decision threshold. The final model produces a posterior probability map, a conservative excursion set, an inscribed factor-range box, and a setpoint inside that box.

The method is therefore evaluated on several distinct objects. Symmetric-difference error measures whether the estimated acceptable region has the correct geometry. Murphy calibration and refinement describe the reliability and sharpness of the probability map. Cross-fit containment evaluates whether the conservative set is contained in the true acceptable region at the stated assurance level. Simple regret measures the quality of one model-selected formulation. Wells and rounds measure different experimental costs.

## 2.4 Study questions

The paper should state the following questions explicitly.

1. Does changing the deliverable from one recipe to an acceptable region reorder the compared methods?
2. In the registered target condition, how accurately does SPADE estimate the acceptable region relative to Bayesian optimization, classical response-surface workflows, and one-shot space-filling designs?
3. Does SPADE preserve practically competitive point performance under a common terminal rule, and how many experimental rounds does it require?
4. Does the point-versus-region distinction persist across noise levels, dimensions, and landscape families?
5. Are SPADE's probability maps calibrated and sharp, and does the conservative certificate attain its nominal containment without relying on empty-set degeneracy?
6. Which parts of the proposed allocation strategy are supported, which are trade-offs, and which analyses remain unresolved?

## 2.5 Intended novelty

The novelty is not that Bayesian optimization can optimize biological formulations, that response-surface methods exist, or that synthetic optimizer benchmarks exist. The contribution is the controlled separation of experimental deliverables and decision components. The same project measures point regret, region error, probability calibration, certificate containment, wells, and rounds; it evaluates a region-first method prospectively; and it reports negative, inconclusive, infeasible, and empty-set outcomes rather than allowing a single favorable metric to stand in for all of them.

---

# 3. Literature and citation-purpose map

The manuscript should cite each source for a defined role. Contextual precedent must not be converted into evidence for this project's synthetic results.

| Source | Purpose in the paper | What it supports | What it does not support |
|---|---|---|---|
| Hall, Lin and Ogle (2025) | Biological motivation and workflow inspiration | A six-factor extracellular-matrix screen followed by a four-factor response-surface experiment in endothelial differentiation; a real setting where multicomponent design and confirmation matter | Fitting of this project's Hill landscapes, protein-specific parameters, or wet-lab validation of SPADE |
| Box and Wilson (1951); Box and Draper; Myers and colleagues | Classical experimental-design background | Sequential response-surface methodology, steepest ascent, canonical analysis, ridge analysis, and the principle that design and model interpretation are inseparable | Superiority of the specific classical arm used here |
| Jones, Schonlau and Welch (1998) | Bayesian-optimization foundation | Efficient global optimization and expected improvement | Empirical superiority in this benchmark or biological system |
| Frazier (2018) | Accessible BO methodology | Gaussian-process surrogates, acquisition functions, and sequential decision making | Evidence for the observed numerical results |
| Bryan (2005) and level-set-estimation literature | Second-round acquisition background | Straddle-style prioritization of uncertain points near a level-set boundary | Demonstrated superiority of this implementation; its matched causal comparison was null |
| Chevalier and co-workers; Azzimonti and co-workers | Excursion-set and conservative-estimation methodology | Vorob'ev quantiles, joint containment, and conservative excursion sets | Cross-family validity of this implementation without empirical checks |
| Gneiting and Raftery (2007) | Probabilistic-evaluation framework | Proper scoring and the need to distinguish calibration from sharpness | Proof that SPADE is calibrated |
| ICH Q8 and quality-by-design literature | Regulatory and design-space context | The practical importance of operating regions rather than isolated optima | Regulatory qualification of the synthetic certificate |
| Rummukainen and colleagues (2024) | Closest equal-budget executed precedent | A pilot-scale adaptive-versus-traditional comparison at the same experiment count | A universal conclusion that BO cannot save experiments |
| Narayanan and colleagues (2025) | Biological relevance of adaptive media optimization | BO-guided cell-culture media development and reported reductions relative to predicted or conventional DoE requirements | An equal-budget executed defeat of DoE under this paper's estimands |
| Lapierre and colleagues (2025) | Executed multicycle media optimization | Batch BO compared with a screened CCD/RSM workflow in microbial media optimization | Isolation of sampling, surrogate, and terminal-rule effects |
| Ndahiro and colleagues (2025) | Constraint-aware mammalian-media optimization | Integration of Bayesian optimization and thermodynamic constraints in a wet-lab setting | Representation of solution thermodynamics in this unconstrained synthetic benchmark |
| Gisperg and colleagues (2025) | Field review | Vocabulary and the broader status of BO in bioprocess engineering | Primary evidence for individual experimental studies |
| Kanda and colleagues (2022) | Scale of robotic biological search | The logistical importance of adaptive experimentation in large cell-culture spaces | A direct BO-versus-RSM comparison |

The final manuscript should recheck bibliographic metadata and quotation-level statements against the primary PDFs before submission. The paper should not use a review when the original experimental article is available, and it should not imply that Hall et al.'s experimental values generated the synthetic response surfaces.

---

# 4. Methods

## 4.1 Study design and evidence bodies

The project contains two related but distinct evidence bodies. The first is a point-optimization benchmark in which stored Bayesian-optimization, response-surface, and space-filling campaigns were re-evaluated under multiple terminal decision rules and later scored as design-space maps. This program establishes the terminal-rule problem, the point-versus-region reversal, and diagnostic mechanisms.

The second is the prospective study `spade-final-2026-08-23`. Its condition matrix, endpoints, target-regime definition, statistical families, practical-effect thresholds, feasibility rules, publication guards, and kill conditions were frozen before the final runners produced results. SPADE allocations were generated live from their plate-one fits rather than applied retrospectively to pre-existing wells. This prospective study supplies the main method-level evidence.

The two programs should never be pooled as if they were one experiment. Retrospective results motivate and interpret the prospective study; prospective results govern claims about SPADE as an executed method.

## 4.2 Formulation space and latent response

A formulation is represented by a coded vector

$$
x=(x_1,\ldots,x_d)\in[0,1]^d,
$$

where $d=6$ or $d=8$. The coordinates may be interpreted as ingredient levels or process settings, but they have no validated mapping to physical concentrations. The primary biological scenario is structurally inspired by a six-factor extracellular-matrix optimization problem. The eight-dimensional condition adds nuisance coordinates to test the cost of dimensions that contribute little or nothing to the response.

The principal latent response is a constructed biphasic Hill landscape. Each factor contributes an activating and an inhibitory component,

$$
h_i(x_i)=\frac{x_i^{n_i}}{\mathrm{EC}_{50,i}^{n_i}+x_i^{n_i}},
$$

$$
g_i(x_i)=\frac{1}{1+\left(x_i/\mathrm{IC}_{50,i}\right)^{n_i}}.
$$

Their normalized product creates a rise-and-fall response with an interior marginal peak at

$$
x_i^*=\sqrt{\mathrm{EC}_{50,i}\mathrm{IC}_{50,i}}.
$$

The multivariate function combines weighted factor contributions with sparse pairwise interactions. Four coordinates receive 90% of the total marginal weight, while the remaining coordinates receive 10%. Interaction coefficients alter conditional peak locations, so the vector of marginal optima is not assumed to be the true joint optimum. Numerical optimization identifies and stores the global optimum of every accepted landscape.

The nominal generator draws marginal peaks from $U(0.25,0.55)$, Hill exponents from $U(1,3)$, and sparse interaction coefficients from $U(-1,1)$ before acceptance filtering. These distributions are project choices, not estimates from biological data. Acceptance rules remove surfaces with poorly identifiable or boundary-adjacent optima. Because of this rejection process, the retained parameter distribution is not identical to the nominal sampling distribution and must be described as a filtered ensemble.

## 4.3 How the synthetic observations were generated

The project did not fit a synthetic table to Hall et al.'s measurements. It first generated and froze a hidden mathematical response surface $f(x)$. Each method then chose which coordinates to evaluate, exactly as an experimental strategy would choose formulations. An assay-like observation was produced only when a method evaluated a point.

The observation model was

$$
y(x)=f(x)(1+\epsilon)+\eta,
$$

with

$$
\epsilon\sim\mathcal N(0,\sigma_{\mathrm{rel}}^2),
\qquad
\eta\sim\mathcal N(0,0.01^2).
$$

The relative-noise levels were $\sigma_{\mathrm{rel}}=0.10$ and $0.25$. They are lower- and higher-noise benchmark settings, not empirically estimated assay coefficients of variation. The additive term prevents the observation variance from collapsing near a zero response. The Gaussian process received the plug-in observation variance

$$
\widehat{\operatorname{Var}}(y\mid x)=y(x)^2\sigma_{\mathrm{rel}}^2+0.01^2,
$$

subject to the implemented numerical floor. This variance uses the observed response and does not reveal the hidden value $f(x)$ to the optimizer.

Because the latent function is known in simulation, every final recommendation and estimated region can be scored against ground truth. This is the primary advantage of the synthetic design. It is also the principal limitation: the benchmark tests decision procedures under controlled mathematical conditions rather than validating a biological formulation.

## 4.4 External landscape families

Hartmann6, Ackley, Levy, and Rosenbrock functions were added to test whether the Hill results depended on one geometry. Hartmann supplies multimodality and competing basins. Ackley was declared an exception before scoring because its center-point optimum favors center-heavy classical designs and because earlier work showed that SPADE often declines to certify. Levy and Rosenbrock provide additional smooth but geometrically distinct robustness conditions.

The prospective matrix contained seven conditions: Hill at $d=6$ and both noise levels; Hartmann at $d=6$ and $d=8$ under higher noise; and Ackley, Levy, and Rosenbrock at $d=6$ under higher noise. Only Hill at $d=6$, $\sigma_{\mathrm{rel}}=0.10$ satisfied the frozen criteria for the `TARGET` regime. The remaining conditions were robustness or predeclared exception settings and cannot independently license universal superiority claims.

## 4.5 Experimental methods and budgets

All principal comparisons used a maximum of 48 evaluated conditions. The number of adaptive decision rounds differed substantially.

| Method | Experimental design | Wells | Rounds | Primary purpose |
|---|---|---:|---:|---|
| SPADE primary and allocation variants | 40-point LHS followed by an eight-point model-directed second round | 48 | 2 | Design-space mapping and certification |
| SPADE plate-one reference | 40-point LHS only | 40 | 1 | Quantify what the additional round contributes; not equal-well |
| Latin hypercube | One-shot space-filling design | 48 | 1 | Broad nonadaptive coverage |
| Sobol | One-shot low-discrepancy design | 48 | 1 | Broad nonadaptive coverage |
| Uniform random | One-shot random design | 48 | 1 | Nonadaptive control |
| qLogEI | Opening design followed by batched expected improvement | 48 | 10 | Point-focused Bayesian optimization |
| qLogNEI | Same schedule with noisy expected improvement | 48 | 10 | Noise-aware point-focused Bayesian optimization |
| Screened DoE/RSM | 20-run screen, 27-run four-factor face-centered CCD, one confirmation | 48 | 3 | Classical staged optimization |
| Unscreened DoE/RSM | Full-dimensional CCD where feasible | 48 | 1 | Isolate screening and model effects |

The unscreened design uses a full-dimensional central composite design. At six factors, the implemented design uses 47 design points within the 48-well limit and fits the same type of second-order model used by the classical pipeline. At eight factors, the factorial and axial points consume the budget before the center replicates needed for a valid CCD can be included. The arm is therefore recorded as structurally unavailable rather than silently omitted or fabricated.

## 4.6 SPADE implementation

SPADE as actually measured differs from the earliest concept document. The historical prospective protocol used plain LHS and response-derived plug-in variances; day-zero covariate correction was unavailable and its landscape-regime detector failed. The two proposed specification repairs were subsequently gated: 49-point strength-2 OA-LHS did not reduce the Hartmann6 design lottery, and even oracle noise variance improved regret by only 0.00816, below the registered 0.01 build bar. Neither was adopted. The executed historical protocol is the following two-round method; the frozen joint protocol instead uses scrambled Sobol and a common learned-noise GP.

### Plate one: broad coverage

Plate one contains 40 Latin-hypercube points spanning all $d$ factors. No factor is screened out. A Matérn-$5/2$ automatic-relevance-determination Gaussian process is fit to the observations using the plug-in observation variances described above. Varying every factor is essential because the intended deliverable is a design-space map; a factor removed by screening cannot receive a defensible operating range.

### Plate two: uncertainty reduction near the decision surface

The current implementation evaluates a straddle score over a 4,096-point Sobol candidate set,

$$
a_{\mathrm{straddle}}(x)=1.96s(x)-\left|\mu(x)-\theta\right|,
$$

where $\mu(x)$ and $s(x)$ are the posterior mean and standard deviation and $\theta$ is the working response threshold used for acquisition. Large values identify locations that are uncertain and plausibly near the estimated level-set boundary. Eight points are selected greedily. A Chebyshev exclusion radius derived from the median ARD length scale prevents the batch from collapsing into one neighborhood.

After the second round, one Gaussian process is refit to all 48 observations. The second-round wells are new locations, not replicate confirmations of plate-one points. Against the matched random-placement control, the registered `m0` targeting effect was −0.00188 (95% interval −0.00624 to +0.00261, Holm $p=0.4108$): boundary targeting did not demonstrate value at the eight-well second-round budget.

### Allocation variants

The prospective study included `m0`, `m4`, and `m8` variants. The primary `m0` arm devotes all eight second-round wells to the region-learning objective. Positive-$m$ variants reserve part or all of the second round for locally exploitative allocation intended to improve the final point recommendation. An allocation variant is counted as an improvement only if it reduces Rule-P regret by at least 0.02, does not worsen map error by more than 0.02, does not worsen calibration by more than 0.005, and retains acceptable certificate behavior.

## 4.7 Point estimand and terminal rules

Simple regret evaluates the quality of one nominated formulation,

$$
r(\widehat x)=f(x^*)-f(\widehat x).
$$

All stored Hill functions are normalized so that $f(x^*)=1$, giving $r=1-f(\widehat x)$. Lower regret is better.

Rule A selects the evaluated point with the highest noisy observed value. Rule P selects the point favored by the fitted model's posterior mean. The prospective paper uses Rule P as the primary point estimand because it compares model-based terminal decisions under one common rule. Rule A remains a required robustness result. A Rule-A value for one method must never be compared with a Rule-P value for another as if they were the same estimand.

The retrospective program also evaluated hidden tested-best, unconstrained model optima, in-region recommendations, replication, and top-three confirmation. Hidden tested-best is an oracle-only diagnostic of search quality. The others are alternative laboratory decision protocols and are used to demonstrate terminal-rule sensitivity.

## 4.8 Design-space estimands

For a performance threshold $\tau$, the true acceptable region is

$$
A_\tau=\left\{x\in\mathcal X:f(x)\geq\tau\right\}.
$$

The fitted model supplies an exceedance-probability map

$$
p_\tau(x)=\Pr\!\left(Y(x)\geq\tau\mid D\right).
$$

At probability threshold $\gamma$, the estimated region is

$$
\widehat A_{\tau,\gamma}=\left\{x:p_\tau(x)\geq\gamma\right\}.
$$

The primary map error is the normalized symmetric-difference volume,

$$
E_{\Delta}=\frac{\mu\!\left(\widehat A_{\tau,\gamma}\triangle A_\tau\right)}{\mu(\mathcal X)},
$$

where $\triangle$ denotes points belonging to one set but not the other and $\mu$ denotes design-space volume. This measure combines false inclusion and false exclusion. Type-I volume is never interpreted alone because an empty predicted set obtains zero false-inclusion volume while providing no useful answer.

AUC, intersection over union, false-inclusion rate, Brier score, Murphy calibration, and Murphy refinement are secondary or supporting outcomes. AUC measures ranking but cannot detect monotonic miscalibration. The Murphy decomposition used in the project is

$$
\operatorname{Brier}=\operatorname{calibration}-\operatorname{refinement}+\operatorname{uncertainty}.
$$

Lower calibration error is better; higher refinement indicates sharper separation of probabilities.

## 4.9 Conservative certificate

SPADE constructs a conservative excursion set using posterior joint draws and Vorob'ev quantiles. Candidate sets are selected using one half of 4,096 draws and evaluated using the other half. This cross-fit prevents the same Monte Carlo draws from both choosing and validating the set.

For a requested containment level $\alpha$, the target property is

$$
\Pr\!\left(C_{\alpha}\subseteq A_\tau\mid D\right)\geq\alpha.
$$

The primary empirical check asks whether the reported set is actually contained in the known true region across independent synthetic campaigns. Empty certificates are excluded from both the numerator and denominator of containment. They are reported separately because an empty set is vacuously contained but scientifically uninformative.

The certificate is conservative conditional on the fitted model and plug-in hyperparameters. Hyperparameter uncertainty is not integrated into the guarantee. Consequently, empirical coverage must accompany every certificate claim.

## 4.10 Feasibility ceiling

For multiplicative noise and a response normalized to a maximum of one, a threshold may become impossible to certify at a high probability level even with perfect knowledge. The approximate ceiling is

$$
\tau_{\max}(\gamma,\sigma_{\mathrm{rel}})=1-z_\gamma\sigma_{\mathrm{rel}},
$$

where $z_\gamma$ is the standard-normal quantile. At $\gamma=0.95$ and $\sigma_{\mathrm{rel}}=0.25$, this ceiling is approximately 0.5888. Thresholds at or above the ceiling are properties of the requested assurance level, not failures of a method. They must be excluded before method comparison.

The original threshold-fraction plan placed most conditions above this ceiling. A preregistered erratum replaced those thresholds with condition-specific response quantiles and sigma-dependent primary probability levels before final outcomes were analyzed. The paper should present this as a protocol correction caught by the feasibility gate.

## 4.11 Prospective condition classification

A condition was eligible for the target regime only if the threshold was certifiable at both primary probability levels, the true acceptable-set prevalence lay between 0.05 and 0.60, at least half of pilot plate-one campaigns were expected to produce a non-empty certificate, and at least 5% of the grid remained in the posterior straddle band. Classification used oracle geometry and a frozen 20-campaign pilot, never final method performance.

Only Hill at $d=6$, $\sigma_{\mathrm{rel}}=0.10$ met these criteria. Hill at higher noise, both Hartmann settings, Levy, and Rosenbrock were robustness conditions. Ackley was a predeclared exception.

## 4.12 Replication, pairing, and inference

The prospective benchmark used 100 campaigns per arm per condition. Hill campaigns were organized around 25 stored landscape instances with repeated campaign seeds. Paired method contrasts were evaluated on matched instances and seeds. The default inferential unit for paired outcomes was the landscape-level aggregate, $n=25$, with the seed-level unit also reported and a direction-disagreement guard.

Wilcoxon signed-rank tests governed directional decisions for paired contrasts. Paired bootstrap intervals quantified effect magnitude. The smallest effect of scientific interest was 0.02 for simple regret and symmetric-difference error. Certificate proportions used exact binomial tails and Clopper–Pearson intervals; normal approximations were prohibited. Holm correction was applied within four frozen families covering certificate cells, plate/allocation contrasts, allocation variants, and map comparators.

The non-empty evidence floor for a certificate cell was 10. Failure to reject sub-nominal coverage is not proof of validity, especially when the denominator is close to that floor.

## 4.13 Implementation and reproducibility architecture

The primary implementation is organized around the following modules.

| File or component | Responsibility |
|---|---|
| `src/boec/oracles.py` and stored sidecars | Generate and record synthetic Hill landscapes |
| `src/boec/torch_oracle.py` | Return noisy observations and plug-in variances |
| `src/boec/campaign.py` and optimizer modules | Run adaptive BO campaigns |
| `src/boec/doe.py` and `src/boec/rsm.py` | Run screened and unscreened classical designs and fit second-order surfaces |
| `src/boec/lse.py` | Compute straddle scores and select diversified second-round points |
| `src/boec/designspace.py` | Build probability maps, connected regions, and inscribed boxes |
| `src/boec/vorobev.py` | Construct conservative excursion sets |
| `src/boec/versionc.py` | Split posterior draws and compute cross-fit certificate quantities |
| `src/boec/final_spade.py` | Define prospective conditions, merging, and final-study helpers |
| `scripts/run_final_spade_benchmark.py` | Execute condition-level prospective campaigns |
| `scripts/analyse_final_spade_benchmark.py` | Compute map, regret, certificate, and registered decision artifacts |
| `scripts/validate_final_spade_release.py` | Enforce publication guards and release completeness |

The manifest records the study identifier, registration commit, code commit, package versions, seed policy, configuration, and hashes of the seven source condition files. The reported combined dataset contains 99,601 rows: 92,400 original prospective rows, 7,200 unscreened-DoE rows, and one structured declaration that the unscreened arm is unavailable at eight factors.

All seven raw condition files and their per-condition primary aliases are tracked. Clean regeneration reproduced 99,601 rows and corrected stale pre-`dd75c91` per-row feasibility flags. From a clean checkout, the release validator passes all 9 checks, the focused final-SPADE suite passes 214 tests, and the figure generator emits all eight prospective figures. The manifest preserves the superseded source hashes and regeneration rationale so the correction is auditable rather than silently replacing history.

---

# 5. Results

## 5.1 Point optimization does not determine design-space quality

The retrospective benchmark established the conceptual premise of the paper. At $d=6$ and higher noise, the staged classical arm achieved mean measured-value regret of approximately 0.0958, compared with 0.1553 for qLogEI and 0.1532 for qLogNEI. Hidden tested-best regret was much closer: approximately 0.0597 for the classical arm, 0.0755 for qLogEI, and 0.0834 for qLogNEI. Thus, much of the measured-value difference arose after the methods had already evaluated their points; it reflected identification under noisy observations rather than search alone.

Changing the terminal rule changed the ranking. Under an unconstrained model optimum, the fitted quadratic frequently extrapolated to an unsupported boundary point and produced a large apparent BO advantage. On the Hill program, the classical stationary point was a saddle in 200 of 200 diagnostic runs. Restricting the recommendation to the learned region largely removed the extreme difference. Confirming the top three candidates on the same campaigns reduced the primary classical-versus-BO gap to approximately $-0.0009$, which was treated as null.

When the same campaigns were evaluated as acceptable regions, the ordering changed again. At $d=6$, $\sigma_{\mathrm{rel}}=0.10$, historical SPADE variants ranked first through third on map AUC while lying near the bottom on measured-value regret; the screened classical arm placed last on map AUC despite competitive point performance. Across Hill cells, the classical arm was last on map quality in 23 of 24 cells. This was the key observation that justified a prospective region-first study.

The paper should use these results as motivation rather than as the final SPADE claim: the scientific deliverable determines which method appears successful.

## 5.2 Registered target condition: SPADE produced the leading design-space maps

The registered target condition was the six-factor Hill landscape at $\sigma_{\mathrm{rel}}=0.10$. Both map error and regret are lower-is-better. The table below reports condition means from the committed prospective Pareto artifact, including the matched random-second-plate control.

| Method | Wells | Rounds | Rule-P regret | Symmetric-difference error |
|---|---:|---:|---:|---:|
| SPADE m4 | 48 | 2 | 0.0871 | **0.1770** |
| SPADE random Plate 2 | 48 | 2 | 0.0822 | **0.1785** |
| SPADE m8 | 48 | 2 | 0.0835 | **0.1797** |
| **SPADE m0, registered primary** | **48** | **2** | **0.0844** | **0.1804** |
| Latin hypercube | 48 | 1 | **0.0747** | 0.1867 |
| Sobol | 48 | 1 | 0.0855 | 0.1913 |
| SPADE plate one only | 40 | 1 | 0.0863 | 0.1921 |
| Uniform random | 48 | 1 | 0.0905 | 0.2050 |
| qLogEI | 48 | 10 | 0.0798 | 0.2067 |
| qLogNEI | 48 | 10 | 0.0750 | 0.2131 |
| Unscreened DoE/RSM | 48 | 1 | 0.2866 | 0.2502 |
| Screened DoE/RSM | 48 | 3 | 0.3072 | 0.2580 |

The model-directed SPADE variants and random-second-plate control occupied a leading map range, 0.1770–0.1804. The primary m0 arm had lower map error than the named BO, screened or unscreened classical, and one-shot space-filling comparators, but was worse than its matched random-placement control. Against qLogNEI, the target-specific difference favoring m0 was 0.03265, with a Holm-adjusted probability of approximately $1.8\times10^{-7}$. This supports target-specific map competitiveness, not universal superiority or a benefit of boundary targeting.

The target result also shows that SPADE's map result is not simply better point optimization. qLogNEI achieved the strongest BO Rule-P regret, 0.0750, while primary SPADE achieved 0.0844. The mean gap was 0.00937 with a bootstrap interval of approximately 0.00258–0.01615, wholly inside the registered 0.02 practical margin. The registered decision therefore supports practical parity, not superiority.

The operational contrast is important. SPADE used two decision rounds; qLogNEI and qLogEI used ten. At equal wells, SPADE therefore reached its map result with one fifth as many plate-to-model decision cycles. Calendar-time superiority is plausible but not directly measured because the project did not attach days, labor, or turnaround time to a round.

## 5.3 The second round improved the map modestly relative to plate one

The 40-well plate-one reference produced symmetric-difference error of 0.1921, whereas the 48-well primary SPADE arm produced 0.1804. The paired improvement was 0.0117, with a bootstrap interval of approximately 0.0074–0.0156 and Holm-adjusted $p\approx1.3\times10^{-4}$. This is a statistically detectable reduction in map error, but it is smaller than the prespecified 0.02 smallest effect of interest.

The correct interpretation is that the additional eight wells and second model fit changed the target-condition map modestly, but the observed gain did not reach the project's threshold for a practically meaningful improvement. The plate-one arm is also eight wells short, so this comparison combines the effects of additional observations and an additional round. The matched equal-well causal control resolves the acquisition question separately: boundary targeting did not beat random placement.

## 5.4 Local exploitative allocation did not safely improve the primary point decision

The m4 and m8 variants were intended to test whether reserving second-round capacity for local exploitation could improve the nominated point without sacrificing the map or certificate. The m4 arm produced Rule-P regret of 0.0871 compared with 0.0844 for m0, a deterioration of approximately 0.0028 rather than the required 0.02 improvement. The paired interval crossed zero and the registered test was not significant. The full conjunction also required preserved map error, calibration, and certificate behavior. It was not met.

The paper should report positive-$m$ allocation as a trade-off experiment, not an improvement. Numerically, m4 produced the lowest target-condition map error, but that fact cannot be converted into a general allocation claim because the variant failed its prespecified multi-outcome rule.

## 5.5 The point-versus-region split reproduced on Hartmann landscapes

Hartmann supplied the strongest cross-family replication of the paper's central distinction. At six dimensions, qLogNEI and qLogEI achieved Rule-P regrets of 0.2305 and 0.2997, clearly ahead of primary SPADE at 0.4221. Map error reversed the ordering: SPADE m4, m8, and m0 achieved 0.1815, 0.1836, and 0.1848, ahead of Sobol at 0.1899, qLogNEI at 0.2243, and qLogEI at 0.2259.

At eight dimensions, qLogNEI and qLogEI again led point regret at 0.2620 and 0.2945. SPADE m4, m0, and m8 led map error at 0.1883, 0.1908, and 0.1950, compared with 0.2006 for Sobol, 0.2196 for qLogNEI, and 0.2348 for qLogEI.

These are robustness results, not confirmatory target-regime wins. Their importance is conceptual: the same family-level split reproduced at two dimensions. Bayesian optimization committed its budget to resolving promising basins and nominated better points; SPADE retained broader spatial information and estimated the acceptable region more accurately.

## 5.6 Ackley confirmed the predeclared exception

Ackley's optimum lies at the center of the domain, favoring center-point classical designs. Screened DoE/RSM achieved the best Rule-P regret, 0.5540, compared with 0.6566 for qLogNEI and approximately 0.7601 for primary SPADE. Its map error, however, was 0.4599, almost twice the 0.23–0.24 range of most other methods. Thus, a design could locate the privileged center point while providing a poor account of the acceptable region.

SPADE's conservative sets were empty in roughly 83–90% of campaigns across its variants. This is not a calibration failure because a method that produces no set makes no non-vacuous containment claim. It is a practical failure to answer. The exception therefore illustrates two independent limits: point success can coexist with map failure, and conservative certification may legitimately decline when the data do not support a reliable region.

## 5.7 Levy and Rosenbrock showed that some map cells are intrinsically uninformative

At higher noise, the registered high-probability map cells for Levy and Rosenbrock exceeded the certifiability ceiling. Their condition-specific primary probability level was therefore $\gamma=0.50$. At that level, Levy map errors lay in a narrow 0.2451–0.2511 range, and Rosenbrock map errors lay in a still narrower 0.2452–0.2494 range. These cells barely discriminated among methods.

Point regret remained informative on Levy: qLogNEI achieved 0.0595, whereas screened and unscreened classical designs were substantially worse. Rosenbrock showed modest regret spread, approximately 0.027–0.053, with SPADE, Sobol, and the plate-one reference near the front.

These conditions should not be forced into a winner narrative. They show that threshold choice, noise, and landscape prevalence can compress map metrics until method differences are practically negligible. This is part of the paper's methodological contribution: feasibility and discriminability must be established before interpreting a map comparison.

## 5.8 SPADE produced sharp maps but not the best-calibrated probabilities retrospectively

In the retrospective five-family Murphy analysis, primary SPADE achieved the highest AUC, 0.7583, and the highest refinement, approximately 0.0151. Its calibration error, approximately 0.0359, ranked in the lower half of the nonclassical arms. Sobol achieved the lowest calibration error, 0.0289, and the lowest Brier score. The screened classical arm's calibration error was 0.2296, more than five times the next-worst arm, and it also ranked last on refinement.

The correct statement is that SPADE generated the sharpest probability separation in that analysis but did not generate the most reliable probabilities. AUC alone would have ranked SPADE first and hidden the calibration result. The main paper should therefore report calibration and refinement together and avoid language implying that a sharp design-space map is automatically well calibrated.

The prospective final study contains per-row Murphy values, and the restored raw artifacts now reproduce the registered Murphy figure. The paper should derive any prospective calibration table directly from those rows and retain the retrospective decomposition as supporting evidence; it must not infer a new ranking from prose summaries.

## 5.9 Hill certificate evidence was encouraging but underpowered at the weakest cell

The prospective Hill certificate kill passed under its registered rule because no confirmatory cell was demonstrably below nominal after exact inference and Holm correction. The weakest confirmatory cell was 11 contained sets among 13 non-empty certificates, or 0.8462 against nominal 0.80. Its exact interval was approximately 0.546–0.981, and its Holm-adjusted probability was 1.0.

This is a failure to demonstrate under-coverage, not proof of validity. The denominator is only three above the non-empty evidence floor, and the interval contains values far below nominal. The manuscript should use language such as “not shown to fall below nominal on Hill under the prospective cross-fit analysis” and should never replace it with “validated,” “guaranteed,” or “proved calibrated.”

Cross-fit and same-draw containment must be shown separately. Same-draw estimates were often larger because the same Monte Carlo information influenced both selection and evaluation. Historical draw-sweep experiments showed that 512 posterior draws were insufficient at high assurance; 4,096 draws and cross-fitting reduced the estimator artifact.

## 5.10 Certificate scope did not extend cleanly beyond Hill

The prospective cross-family certificate rule required every confirmatory Hartmann cell to be clean. That condition was not met because some cells were inconclusive even though the worst Hartmann containment proportion itself was above its nominal level. The registered consequence is to narrow the certificate claim to Hill rather than declare a demonstrated cross-family coverage failure from that prospective study.

An independent retrospective five-family certificate program provides stronger evidence about the limitation. At 4,096 draws, Hill had no cell significantly below nominal. Levy and Rosenbrock under-covered at $\gamma=0.99$ in three of 64 scored cells after Holm correction: Levy achieved 34/49 containment at one threshold and 37/48 at another, while Rosenbrock achieved 37/50. Ackley and Hartmann usually produced empty certificates and therefore declined to answer.

Taken together, the evidence supports a Hill-scoped statement: the certificate has not been shown to fail on Hill under the implemented cross-fit analysis, but it is not established as a portable guarantee across landscape families. Off Hill, the dominant failure can be either high-assurance miscoverage or non-vacuity.

## 5.11 Empty-set and feasibility guards materially changed the interpretation

Eighteen of 64 certificate cells satisfied their raw containment rule while producing empty sets in more than half of campaigns. They were correctly downgraded to inconclusive. This guard prevents vacuous containment from being reported as certificate success.

Clean regeneration corrected stale checkpoint flags written before the row-level `above_ceiling` fix. The current ledger records 0 of 23,600 primary-probability rows at or above the certifiability ceiling, so KF-9 passes. The superseded 4,400 count was an artifact of stale checkpoint state, not a property of the registered thresholds.

These results deserve a dedicated methods-and-results paragraph because they are broadly relevant. A conservative set method can appear perfectly safe by returning nothing, and a benchmark can appear universally difficult by requesting an impossible threshold. Non-empty denominators and feasibility ceilings are therefore primary scientific quantities, not implementation details.

## 5.12 Full-dimensional DoE did not rescue the classical map

The newly implemented unscreened six-factor central-composite arm allowed the project to test whether the classical map deficit was caused only by screening. In the target condition, unscreened DoE improved symmetric-difference error from 0.2580 to 0.2502 and improved Rule-P regret from 0.3072 to 0.2866, but it remained far behind the SPADE and space-filling map results. At higher-noise Hill, the screened arm led the unscreened arm on both regret rules. The comparison therefore varied by terminal rule and condition.

Retrospective Hartmann re-scoring had already shown that turning off screening closed only about one fifth to one quarter of the classical arm's map deficit relative to spread designs. The full prospective comparison reinforces the interpretation that screening is not the sole mechanism; the combination of a low-order response surface, concentrated geometry, and terminal recommendation also matters.

At eight dimensions, a full second-order CCD with center replication could not fit within 48 wells. The unscreened arm is structurally unavailable there. This is not missing data; it exposes a real budget constraint of full-dimensional classical response-surface design.

## 5.13 Classical-arm diagnostics explain why point and map performance diverged

The retrospective diagnostic program evaluated the classical workflow using criteria from the response-surface literature itself. Its pooled 48-well six-factor design was rank-deficient in 50 of 50 campaigns because the screened factors were pinned after stage one and resolution-IV interaction aliases remained in the pooled design. Its stage-two four-factor design was locally estimable, but the resulting model described only a restricted subregion while being used to make statements about the full six-factor box.

The fitted quadratic overpredicted the confirmation response in 25 of 25 campaigns at both noise levels. Approximately half of the predicted optima exceeded the true global maximum of the synthetic landscape, every stationary point was classified as a saddle, and the confirmation well never improved on the best point already visited. The lack-of-fit test had only two pure-error degrees of freedom. Pooling replicate information already paid for by the screen increased detection of lack of fit at lower noise from 8/25 to 24/25 without adding wells.

These diagnostics should not be used to dismiss response-surface methodology generally. They identify weaknesses of the implemented screened pipeline and demonstrate why canonical analysis, ridge analysis, replication, and sequential relocation are necessary components of a fair classical workflow.

## 5.14 Round count changes the practical comparison

One-shot space-filling designs use one decision round, SPADE uses two, screened DoE/RSM uses three, and the 48-well batch-BO arms use ten. Equal wells therefore do not imply equal experimental latency. A two-round method may be attractive when assays require days of incubation or manual analysis between batches, even if a ten-round method achieves slightly better point regret.

The repository contains longer-run cost experiments through 200 wells for selected point-optimization arms, but it does not contain a complete prospective regret-against-budget curve for SPADE. The main paper may report the fixed-budget round counts exactly. It should not claim a measured fivefold reduction in calendar time or overall cost without a schedule, cost model, or per-round SPADE performance curve.

---

# 6. Registered claim-evidence matrix

The paper should translate internal kill identifiers into scientific statements and include the resolved negative boundary-targeting comparison.

| Scientific statement | Status for this manuscript | Evidence and interpretation |
|---|---|---|
| Primary SPADE has lower target-regime map error than the named BO and classical comparators | Supported, target-specific | m0 error 0.1804; qLogEI 0.2067; qLogNEI 0.2131; unscreened DoE 0.2502; screened DoE 0.2580 |
| SPADE is competitive with Sobol in the target regime | Supported | m0 is numerically lower by 0.0109, inside the 0.02 practical margin |
| SPADE is practically close to the best BO point decision under Rule P | Supported | Mean regret gap 0.00937; 95% interval 0.00258–0.01615, inside the 0.02 margin |
| A second round improves on the 40-well plate-one map by a practically meaningful amount | Not supported at the registered magnitude | Improvement 0.0117 is statistically detectable but below the 0.02 threshold |
| Positive-$m$ allocation safely improves regret without sacrificing map or certificate behavior | Not supported | m4 regret is 0.0028 worse than m0 and the full conjunction is unmet |
| Prospective Hill containment is demonstrably below nominal | Not observed | No confirmatory Hill cell failed the exact Holm-adjusted rule; weakest denominator is only 13 |
| The certificate is established beyond Hill | Not supported | Prospective Hartmann evidence is not uniformly clean; independent cross-family study identifies under-coverage or non-vacuity failures |
| Empty certificates do not explain apparent containment success | Not supported in all cells | Eighteen of 64 raw passing cells exceeded 50% emptiness and were downgraded |
| Every analyzed primary threshold was feasible | Supported after clean regeneration | 0 of 23,600 primary-γ rows reached the analyzer at or above the certifiability ceiling |
| Boundary-focused second-round placement improves on its matched control | Not supported | m0 minus random-control improvement was −0.00188, 95% interval −0.00624 to +0.00261, Holm $p=0.4108$ |

---

# 7. Main figure program

## Figure 1. From one best recipe to an acceptable operating region

**Scientific question.** What different experimental deliverable does SPADE target, and how does its two-round workflow produce it?

**Panel A** should show a simplified two-factor response surface with one optimum marked and a threshold-defined acceptable region shaded. The illustration must state that real experiments use six or eight dimensions and that the two-dimensional surface is explanatory only.

**Panel B** should contrast point optimization with region learning. Point optimization returns one $\widehat x$ and is scored by regret. Region learning returns $\widehat A_{\tau,\gamma}$ and is scored by symmetric difference, calibration, and containment.

**Panel C** should depict the historical SPADE 40-point Latin-hypercube plate, Gaussian-process fit, eight-point uncertainty-reduction plate, 48-point refit, probability map, conservative set, inscribed box, and setpoint. It may illustrate boundary-focused acquisition as the implemented historical method but must state that the matched causal comparison was null.

**Visual encoding.** Use one color for observed plate-one points, a second for plate-two points, a probability gradient for the map, a solid contour for the estimated region, and hatching for the conservative set.

**Draft caption.** *SPADE changes the experimental target from one nominal optimum to a threshold-defined operating region. Forty space-filling observations provide broad coverage of all factors. A Gaussian-process surrogate guides eight second-round observations toward uncertain portions of the estimated decision surface. The refitted model produces an exceedance-probability map, a conservative excursion set, an inscribed factor-range box, and a setpoint. The diagram is schematic; in the registered target condition, this boundary-targeting rule did not outperform equal-well random second-round placement.*

**Supported conclusion.** SPADE is a defined, two-round workflow for region estimation.

**Prohibited interpretation.** The diagram does not show that boundary-targeted acquisition outperforms alternative placement.

## Figure 2. Point regret and design-space error reorder the methods

**Scientific question.** Does the method that nominates the best point also produce the best acceptable-region map?

**Panel A** should plot mean Rule-P regret against symmetric-difference error for the target Hill condition. Each point represents a method; point size may encode wells and outline style may encode rounds. The three SPADE allocation variants and matched random-second-plate control should be visually grouped.

**Panel B** should show the same two outcomes for Hartmann at six dimensions, and **Panel C** at eight dimensions. The axes must retain the same lower-is-better direction. Arrows or quadrant shading may identify “strong point/weak map” and “strong map/weaker point” regions without calling either universally superior.

**Panel D** should show method-family rank on point regret beside rank on map error across the three informative conditions. A slope chart will make the rank reversal visually immediate.

**Draft caption.** *Point optimization and acceptable-region estimation rank the same method families differently. In the registered Hill target condition, SPADE variants occupy the leading map-error range while qLogNEI attains the lowest Rule-P regret. The split reproduces on six- and eight-dimensional Hartmann landscapes: batch BO resolves stronger terminal points, whereas SPADE retains a more accurate estimate of the acceptable set. All comparisons use 48 wells except the explicitly labeled 40-well plate-one reference; robustness conditions do not license universal superiority claims.*

**Supported conclusion.** Point and region objectives are empirically non-equivalent across multiple landscapes.

**Prohibited interpretation.** Do not say that SPADE is the best optimizer or that BO cannot map design spaces.

## Figure 3. Target-condition performance in map error, regret, and experimental rounds

**Scientific question.** What does SPADE gain and what does it trade in the registered target regime?

**Panel A** should present paired mean symmetric-difference error with 95% bootstrap intervals for SPADE m0/m4/m8, Sobol, LHS, random, qLogEI, qLogNEI, screened DoE, unscreened DoE, and the 40-well plate-one reference. Lower values should appear higher or farther left consistently.

**Panel B** should present Rule-P regret for the same methods. A bracket between m0 and qLogNEI should show the 0.00937 mean gap, its 0.00258–0.01615 interval, and the 0.02 practical margin.

**Panel C** should compare wells and rounds. All equal-budget methods should align at 48 wells, while round counts should show one for one-shot designs, two for SPADE, three for screened DoE, and ten for BO.

**Panel D** should compare primary SPADE with the 40-well plate-one reference: 0.1804 versus 0.1921 map error, improvement 0.0117, interval 0.0074–0.0156, with the 0.02 smallest effect marked. This panel addresses the value of the additional observations without attributing that value to a particular acquisition rule.

**Draft caption.** *SPADE's target-regime result is strongest for the design-space map, not the terminal point. Primary SPADE achieved symmetric-difference error 0.1804 and Rule-P regret 0.0844 in two rounds. qLogNEI achieved lower regret, 0.0750, but higher map error, 0.2131, in ten rounds. The mean regret gap was 0.00937 with a 95% interval of 0.00258–0.01615, inside the prespecified 0.02 practical margin. Adding the second round changed map error over the 40-well plate-one reference by 0.0117, a statistically detectable but sub-threshold effect.*

**Supported conclusion.** SPADE offers a map-first trade-off with practical mean regret proximity and fewer decision rounds.

**Prohibited interpretation.** Do not claim proven equivalence, calendar-time savings, or causal superiority of boundary targeting.

## Figure 4. Sharpness, calibration, non-vacuity, and certificate scope

**Scientific question.** Does a strong map imply a reliable probability model or a valid conservative certificate?

**Panel A** should plot retrospective Murphy calibration against refinement for the modeled arms. SPADE should appear high in refinement but mid-field in calibration; Sobol should appear strongest in calibration; screened DoE should appear as the outlier with poor calibration.

**Panel B** should show prospective cross-fit containment and exact intervals for Hill confirmatory cells, with nominal assurance lines and non-empty denominators printed beside every estimate.

**Panel C** should show the percentage of empty certificates by family. Ackley and Hartmann should be visually distinguished as “declines to certify,” not scored as successful containment.

**Panel D** should summarize cross-family high-assurance outcomes: Hill not shown below nominal, Levy and Rosenbrock under-covering in the independent $\gamma=0.99$ analysis, and Ackley/Hartmann predominantly empty. A compact status matrix is preferable to a winner plot.

**Draft caption.** *Map discrimination, probability calibration, and conservative containment are distinct properties. SPADE produced the highest retrospective refinement but not the lowest calibration error. Prospective Hill containment was not shown below nominal, although the weakest confirmatory estimate relied on 13 non-empty certificates and had a wide exact interval. Off Hill, high-assurance under-coverage occurred on Levy and Rosenbrock in an independent cross-family analysis, whereas Ackley and Hartmann frequently produced no non-empty certificate. Empty sets are reported separately and never counted as containment successes.*

**Supported conclusion.** SPADE's mapping result is stronger and broader than its current certificate evidence.

**Prohibited interpretation.** Do not describe Hill failure to reject as proof of validity or treat empty certificates as conservative successes.

---

# 8. Main tables and supplementary program

## Table 1. Methods and experimental budgets

Use the method table in Section 4.5, expanded with surrogate, acquisition, terminal rule, screening status, and whether design-space certification is defined. This table should make clear that equal wells do not mean equal rounds and that the 40-well plate-one arm is not an equal-budget comparator.

## Table 2. Registered target-condition estimates

Use the numerical table in Section 5.2, adding paired intervals and adjusted probability values for the registered contrasts, including the matched boundary-targeting control.

## Table 3. Cross-family claim scope

Report each condition's family, dimension, noise level, regime class, primary probability level, map-error range, leading point method, leading map family, certificate non-vacuity, and whether the result is confirmatory, robustness, or exception evidence.

## Table 4. Claim-evidence matrix

Use Section 6 as the basis. Replace internal kill identifiers with scientific language in the main paper. The complete corrected machine-readable kill ledger can appear in the supplement.

## Supplementary figures

1. Terminal-rule reversal on identical campaigns: hidden tested-best, noisy argmax, posterior mean, unconstrained model optimum, in-region recommendation, and top-three confirmation.
2. Search-versus-identification decomposition across noise and acquisition functions.
3. Quadratic stationary-point diagnostics, including saddle classification and confirmation overprediction.
4. Long-run point-regret curves through 200 wells, shown separately against wells and decision rounds.
5. Complete per-family point-versus-map scatterplots for Hill, Hartmann, Ackley, Levy, and Rosenbrock.
6. Screened versus unscreened DoE at six dimensions, including the arithmetic reason the unscreened design is unavailable at eight dimensions.
7. Murphy calibration, refinement, Brier score, and AUC for every retrospective arm.
8. Draw-count sensitivity for conservative-set containment at 512, 1,024, 2,048, and 4,096 posterior draws.
9. Certificate non-empty rates and exact containment intervals for every family and assurance cell.
10. Feasibility-ceiling diagnostic showing which threshold/probability combinations are mathematically un-certifiable.

The boundary-targeting comparison should receive its own preregistered causal-analysis figure rather than being hidden among broad performance panels. It must show the null effect, interval, adjusted probability value, and equal-well control explicitly.

---

# 9. Discussion

## 9.1 Primary interpretation

The study supports a change in how formulation-optimization methods are evaluated. A laboratory that needs one high-performing recipe should compare confirmed terminal decisions under a common rule. A laboratory that needs a robust operating window should score the acceptable region directly. The two objectives are not interchangeable, and the same experimental design can be strong on one while weak on the other.

SPADE was designed for the region objective. In the single registered target regime, its three allocation variants produced the lowest map-error range, while the primary arm retained a mean point-regret gap within the prespecified practical margin relative to qLogNEI. This performance required two experimental rounds rather than ten. The Hartmann results show that the point-versus-region distinction is not restricted to the Hill generator: BO consistently nominated better points, whereas SPADE consistently mapped the acceptable region more accurately.

## 9.2 What the paper contributes methodologically

The paper's most general contribution is its evaluation framework. It separates search from identification, terminal rule from acquisition function, map accuracy from probability calibration, and certificate containment from non-vacuity. It also treats feasibility as part of the scientific design. A threshold above the certifiability ceiling is excluded rather than scored as a method failure; an empty set is reported rather than counted as a perfect conservative answer.

This framework is valuable beyond SPADE. Many optimizer benchmarks reward the largest observed value and stop. The project shows that this can confound the quality of sampled conditions with winner's-curse identification, while a model optimum can introduce extrapolation failures unrelated to the sampling design. Similarly, a high AUC can coexist with mediocre calibration, and nominal containment can be vacuous if the method rarely returns a set.

## 9.3 Interpretation of the second round and allocation variants

The observed second-round gain over the 40-well plate-one reference was real but smaller than the declared meaningful-effect threshold. This indicates that much of SPADE's map performance may already arise from broad plate-one coverage, with the additional observations providing a modest refinement. The comparison does not identify which acquisition policy caused the gain because it changes both sample count and round count.

The positive-$m$ variants did not satisfy the preregistered conjunction for safe point improvement. This result argues against assuming that local exploitation can be added without compromising a region-first objective. It also illustrates the value of conjunctive method criteria: the lowest point estimate on one metric is not automatically an improvement if calibration or certificate requirements fail.

The boundary-targeting causal question is resolved negatively for the registered target: m0 did not beat equal-well random placement. This result constrains the mechanism claim but does not erase the broader estimand-dependent ranking or target-specific map competitiveness.

## 9.4 Why certificate claims are narrower than map claims

Map error is an empirical geometry score. The certificate is a probabilistic safety claim conditional on a fitted model. The latter is harder. It depends on posterior calibration, joint-draw estimation, non-empty evidence, assurance level, and threshold feasibility. The project found strong map results in settings where the conservative certificate was inconclusive or empty. This is not a contradiction; it is evidence that mapping and certifying are different levels of claim.

The Hill results are encouraging but not definitive. Failure to reject under-coverage with 13 non-empty certificates does not establish a guarantee. Cross-family results further restrict the scope. A strong paper should present this limitation as a scientific result: the current certificate is family-dependent, and the dominant failure mode changes from miscoverage to declining to answer.

## 9.5 Practical guidance for experimental laboratories

The experimental deliverable should be specified before choosing a method. If the goal is one formulation, the protocol should include an explicit confirmation rule and compare methods on held-out biological performance. If the goal is an operating window, all relevant factors must remain varied, probability calibration must be evaluated, and conditions inside and near the estimated boundary must be tested prospectively.

Round count should be budgeted alongside wells. Adaptive methods are attractive when feedback is rapid and automation is available. A one- or two-round strategy may be preferable when every adaptive cycle requires several days, a cell expansion step, a donor batch, or extensive image analysis. The present project quantifies rounds but not calendar time, labor, or reagent cost, so these trade-offs must be measured in a wet-lab study.

## 9.6 Relation to classical RSM and Bayesian optimization

The paper should avoid a simplistic SPADE-versus-BO-versus-DoE hierarchy. Each method emphasizes a different experimental object. BO is strong when the task is to resolve one promising basin and nominate a high-performing point. Broad space-filling and SPADE-style designs retain more information about the whole domain. Classical response surfaces can be efficient and interpretable when their model is locally adequate and their canonical, ridge, replication, and sequential safeguards are used.

The implemented screened classical pipeline performed poorly on full-domain mapping and failed several internal diagnostics, but this does not invalidate RSM as a field. It shows that a staged screen-and-local-quadratic workflow should not be treated as a full-factor design-space map without additional evidence.

## 9.7 Biological limitations

The main study is a computer experiment. No cell culture, differentiation, media, or bioprocess campaign was optimized prospectively. The factor labels are nominal, the response surfaces were not fitted to Hall et al.'s data, and the noise parameters were not estimated from biological replicate measurements.

The simulator omits donor and batch hierarchy, plate-position effects, reagent-lot variation, cell-state drift, missing wells, assay censoring, solubility, osmolarity, toxicity, composition constraints, multiple competing endpoints, and calendar-time costs. Algorithmic campaign seeds are not biological replicates. The limited mathematical families do not span the full geometry of biological systems.

The current Gaussian-process certificate is conditional on plug-in hyperparameters and does not propagate hyperparameter uncertainty. The target regime was selected by a frozen geometry-based pilot, which protects against outcome-based relabeling but still means the positive claim applies to one prespecified class rather than all possible landscapes.

## 9.8 Reproducibility limitations

The committed summary and decision artifacts are sufficient to audit many central numbers, and the targeted implementation tests are green. They are not sufficient to recreate the full prospective release from a fresh clone because the raw per-condition JSON files and the merged primary file are ignored and absent. The manifest hashes point to those missing files. The paper must not claim complete computational reproducibility until the raw artifacts are archived in an accessible repository or regenerated deterministically and the release validator passes from a clean checkout.

Earlier narrative documents are append-only research records and contain superseded sections. In particular, early portions of `FINDINGS-SPADE-FINAL.md` predate the unscreened comparator and contain incorrect interpretations of the target table and plate-one contrast. Numerical claims should be regenerated from the current JSON artifacts, not copied from those early paragraphs.

## 9.9 Required wet-lab validation

A realistic validation should use a tractable six-factor formulation system with continuous safe ranges, a stable primary assay, and a one- to three-day turnaround. SPADE, qLogNEI, and a properly implemented classical sequential RSM workflow should receive the same formulation-well budget. Wells should be randomized across plate positions and blocked by biological batch or donor. Shared controls should appear on every plate.

The point endpoint should be the held-out biological performance of each method's preregistered carry-forward formulation after confirmation in new biological batches. The region endpoint should sample formulations randomly from the predicted interior, near the estimated boundary, and just outside the region. The study should estimate empirical false inclusion, false exclusion, and containment against replicate-mean responses. Empty certificates must remain explicit outcomes.

A smallest effect of scientific interest should be stated in biological units before the first plate. The analysis should report formulation wells, replicate wells, confirmation wells, experimental rounds, elapsed calendar time, reagent cost, failed wells, and variance components separately. The boundary-targeting analysis should be corrected computationally before deciding whether it merits a dedicated wet-lab ablation.

---

# 10. Claims, prohibited overclaims, and reviewer responses

## 10.1 Strongest defensible claims

1. Point optimization and acceptable-region estimation produce different and reproducibly reordered method rankings.
2. In the registered six-factor, lower-noise Hill target regime, SPADE variants achieved the leading symmetric-difference map errors among the compared modeled workflows.
3. Primary SPADE's mean Rule-P regret gap from qLogNEI was within the prespecified 0.02 practical margin, with an interval that extended slightly beyond the margin.
4. SPADE used two experimental decision rounds at 48 wells, compared with ten for the batch-BO comparators.
5. The point-versus-region split reproduced descriptively on six- and eight-dimensional Hartmann landscapes.
6. SPADE's retrospective probability maps were sharp but not best calibrated; map quality cannot substitute for calibration.
7. Prospective Hill certificate cells were not shown to under-cover, but the evidence was thin and does not prove validity.
8. Certificate portability beyond Hill is not established; off-Hill failures include both high-assurance under-coverage and declining to certify.
9. Turning off classical screening did not rescue the classical design-space map, and full-dimensional CCD became arithmetically unavailable at eight factors under the 48-well budget.

## 10.2 Statements that must not appear

| Unsafe statement | Required replacement |
|---|---|
| “SPADE is the best optimizer.” | “SPADE produced leading map accuracy in the registered target regime while qLogNEI produced lower point regret.” |
| “SPADE beats BO.” | Name the outcome, condition, comparator, terminal rule, and round count. |
| “SPADE is proven equivalent on regret.” | “The mean gap was within the 0.02 margin, but its interval extended slightly beyond the margin.” |
| “SPADE's certificate is valid.” | “No prospective Hill confirmatory cell was demonstrably below nominal; the weakest cell had 13 non-empty certificates and a wide interval.” |
| “The certificate generalizes.” | “Cross-family validity was not established.” |
| “Empty certificates are conservative successes.” | “The method declined to certify; emptiness was excluded from containment.” |
| “SPADE reduced experimental cost fivefold.” | “SPADE used two decision rounds versus ten at equal wells; calendar time and cost were not measured.” |
| “The synthetic model represents endothelial biology.” | “The benchmark is structurally inspired by a formulation problem but was not fitted to endothelial data.” |
| “The screened classical failure proves RSM is unsuitable.” | “The implemented screened pipeline failed full-domain diagnostics; standard RSM safeguards were not fully represented at the fixed budget.” |
| “Boundary targeting improves the second plate.” | “Boundary-targeted m0 did not outperform equal-well random placement in the registered target condition.” |

## 10.3 Anticipated reviewer criticisms

**“The result is synthetic.”** Agree. State this in the title, abstract, and first Methods paragraph if the target journal requires it. The contribution is controlled method evaluation and claim separation, not biological validation.

**“Only one target regime supports the main claim.”** Agree and frame the claim accordingly. Use Hartmann as descriptive robustness of the point-versus-region split, not as a second confirmatory target.

**“The certificate pass is underpowered.”** Report the 11/13 denominator and exact interval. Avoid binary pass language in the narrative.

**“AUC and refinement flatter SPADE while calibration does not.”** Present the Murphy decomposition in the main paper. This strengthens rather than weakens the work because it prevents a one-metric claim.

**“The classical comparator is unfair.”** Present both screened and unscreened versions, the long-run relocating RSM analysis, in-region terminal rules, and the diagnostic limitations of the implemented fixed-budget pipeline.

**“The method may only be a good space-filling design.”** Report the plate-one comparison, its sub-SESOI second-round change, and the null equal-well targeting comparison. The evidence does not assign a causal benefit to boundary targeting.

**“The release is not reproducible.”** Point to the tracked seven-condition raw artifacts, regeneration record, 9/9 clean-checkout validator result, focused 214-test suite, and deterministic figure workflow. Keep the regeneration disclosure visible because the original ignored files were unavailable.

---

# 11. Recommended manuscript structure

## Introduction

The Introduction should move from the experimental burden of multicomponent formulation spaces to the distinction between a best recipe and an acceptable region. It should review BO, RSM, and quality-by-design precedent, explain why whole-workflow comparisons confound sampling and terminal decisions, and end with the six study questions in Section 2.4. SPADE should be introduced only after the reader understands why point regret is insufficient.

## Methods

The Methods should follow Sections 4.1–4.13 in order: evidence bodies; synthetic landscapes; observation model; external families; comparators and budgets; SPADE implementation; point and region estimands; cross-fit certificate; feasibility; target classification; statistics; and software provenance. Define the boundary-targeting acquisition and its matched random-placement control before reporting the null causal result.

## Results

The Results should follow the scientific logic rather than repository chronology. Begin with terminal-rule and point-versus-region reordering. Present the target-condition SPADE map, regret, and round results next. Then present the modest plate-two gain and the unsuccessful positive-$m$ allocation. Follow with Hartmann robustness, Ackley exception, Levy/Rosenbrock non-discrimination, probability calibration, certificate scope, feasibility and empty-set guards, unscreened DoE, and classical diagnostics.

## Discussion

The Discussion should lead with the difference between point and region deliverables, then explain SPADE's map-first trade-off, the distinction between sharpness and reliability, and the limitations of certificate portability. It should close with practical experimental guidance, computational-release requirements, and a preregistered wet-lab validation design.

---

# 12. Evidence provenance and writing controls

## 12.1 Numerical source hierarchy

The numerical source of truth is, in order:

1. `results/final-spade-regret-pareto.json` for prospective point and map means.
2. `results/final-spade-certificate.json` for prospective containment, emptiness, feasibility, and cross-fit details.
3. `results/final-spade-kill-ledger.json` for registered decisions, interpreted alongside the sign convention in the analysis code.
4. `results/final-spade-manifest.json` for configuration, provenance, seed policy, and source hashes.
5. Retrospective committed result artifacts for terminal-rule, calibration, RSM-diagnostic, cross-family, and draw-sweep findings.
6. The latest corrective sections of `docs/FINDINGS-SPADE-FINAL.md` and `docs/SPADE-FOR-RESEARCHERS.md` for interpretation.

Early narrative sections and `docs/RESEARCH-SUMMARY.md` contain stale statements about the unscreened comparator, certificate status, kill counts, and target-arm ranking. They may help reconstruct history but must not be quoted as current results.

## 12.2 Boundary-targeting reporting rule

The corrected targeted-versus-control result must be reported with its sign convention,
arm means, interval, adjusted probability value and registered consequence. The safe
statement is that `m0` did not outperform equal-well random second-round placement in the
registered Hill target. It must not be generalized to every landscape or second-round
budget.

## 12.3 Publication-readiness checklist

- Keep all seven raw prospective condition files and their per-condition aliases tracked.
- Preserve the clean-checkout 9/9 release-validator result and regenerate it for the submission commit.
- Derive the prospective Murphy calibration/refinement table from authoritative raw rows.
- Report the independently verified boundary-targeting result and sign convention consistently.
- Reconcile the oracle generator's mutable acceptance default with the frozen stored ensemble configuration.
- Verify every central number against its committed JSON key.
- Re-read primary PDFs and finalize the bibliography, author lists, page numbers, and exact claims.
- Freeze the final confirmatory, robustness, exception, and exploratory labels.
- Produce the four main figures with consistent lower-is-better axes and non-empty denominators.
- Ensure every use of “best,” “validated,” “calibrated,” “significant,” “equivalent,” “cost,” “replicate,” and “design space” carries its required scope.
- State prominently that the project is synthetic and has not validated a biological formulation.
- Pre-register the wet-lab terminal rule, confirmation plan, biological effect threshold, and region-validation sampling design before experimental deployment.

---

# 13. Core references and internal evidence trail

## 13.1 External references to verify in the final bibliography

- Hall ML, Lin W-H, Ogle BM. “Optimizing extracellular matrix for endothelial differentiation using a design of experiments approach.” *Scientific Reports* 15, 24479 (2025). DOI: 10.1038/s41598-025-09256-9.
- Box GEP, Wilson KB. “On the Experimental Attainment of Optimum Conditions.” *Journal of the Royal Statistical Society: Series B* 13 (1951). DOI: 10.1111/j.2517-6161.1951.tb00067.x.
- Jones DR, Schonlau M, Welch WJ. “Efficient Global Optimization of Expensive Black-Box Functions.” *Journal of Global Optimization* 13 (1998). DOI: 10.1023/A:1008306431147.
- Frazier PI. “A Tutorial on Bayesian Optimization.” arXiv:1807.02811 (2018).
- Rummukainen M, et al. “Traditional or adaptive design of experiments? A pilot-scale comparison on wood delignification.” *Heliyon* 10, e24484 (2024). DOI: 10.1016/j.heliyon.2024.e24484.
- Narayanan H, et al. “Accelerating cell culture media development using Bayesian optimization-based iterative experimental design.” *Nature Communications* 16, 6055 (2025). DOI: 10.1038/s41467-025-61113-5.
- Lapierre A, et al. “Multi-cycle high-throughput growth media optimization using batch Bayesian optimization.” *Journal of Chemical Technology & Biotechnology* 100, 1571–1583 (2025). DOI: 10.1002/jctb.7860.
- Ndahiro RK, et al. “Integration of Bayesian optimization and solution thermodynamics to optimize media design for mammalian biomanufacturing.” *iScience* 28, 112944 (2025). DOI: 10.1016/j.isci.2025.112944.
- Gisperg F, et al. “Bayesian Optimization in Bioprocess Engineering—Where Do We Stand Today?” *Biotechnology and Bioengineering* 122, 1313–1325 (2025). DOI: 10.1002/bit.28960.
- Kanda GN, et al. “Robotic search for optimal cell culture in regenerative medicine.” *eLife* 11, e77007 (2022). DOI: 10.7554/eLife.77007.
- Gneiting T, Raftery AE. “Strictly Proper Scoring Rules, Prediction, and Estimation.” *Journal of the American Statistical Association* 102 (2007). DOI: 10.1198/016214506000001437.

The final bibliography must also include the exact Bryan, Chevalier, Azzimonti, Vorob'ev-set, Murphy-decomposition, and ICH Q8 sources used by the method section after their primary PDFs and metadata are rechecked.

## 13.2 Internal evidence map

| Paper component | Primary repository evidence |
|---|---|
| Frozen prospective design | `docs/SPADE-FINAL-SPEC.md` |
| Latest prospective narrative and corrections | `docs/FINDINGS-SPADE-FINAL.md`, especially Section 17.4 |
| Researcher-facing method explanation | `docs/SPADE-FOR-RESEARCHERS.md` |
| Target point/map table | `results/final-spade-regret-pareto.json` |
| Certificate and non-vacuity table | `results/final-spade-certificate.json` |
| Registered decisions | `results/final-spade-kill-ledger.json` |
| Study provenance | `results/final-spade-manifest.json` |
| Feasibility and target classification | `results/final-spade-feasibility.json` |
| Prospective implementation | `src/boec/final_spade.py`, `scripts/run_final_spade_benchmark.py` |
| Prospective analysis | `scripts/analyse_final_spade_benchmark.py` |
| Synthetic Hill construction | `docs/oracle_defensibility.md`, `src/boec/oracles.py`, frozen oracle sidecars |
| BO implementation | `src/boec/campaign.py`, optimizer and surrogate modules |
| Classical implementation | `src/boec/doe.py`, `src/boec/rsm.py` |
| Retrospective point findings | `docs/RESEARCH-SUMMARY.md` interpreted through later corrections and committed Q/E artifacts |
| Retrospective design-space findings | `docs/FINDINGS-SPADE.md`, K6/P6/P7/P8 and Version-C artifacts |
| Release checks | `scripts/validate_final_spade_release.py`, final-SPADE tests |

**Final writing rule:** every manuscript sentence must trace to a primary source, a committed artifact, a declared design choice, or an explicitly labeled interpretation. If it cannot be traced, it is not ready for publication.
