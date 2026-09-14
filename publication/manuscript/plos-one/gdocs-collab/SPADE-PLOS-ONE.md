# Point and region objectives reverse method rankings in a synthetic benchmark of SPADE and experimental design strategies

**Short title:** Point versus region experimental design

**Authors:** [AUTHOR ORDER TO BE CONFIRMED]

**Affiliations:** [AFFILIATIONS TO BE CONFIRMED]

**Corresponding author:** [NAME, ADDRESS, AND EMAIL TO BE CONFIRMED]

## Abstract

Selecting one formulation and estimating an acceptable operating region require different evaluations of an experimental campaign. We compared SPADE, Bayesian optimization, response-surface designs, and space-filling strategies under a 48-evaluation budget on synthetic landscapes. Retrospective rescoring examined terminal decisions; a prospectively specified benchmark comprised 8,300 campaign-arm executions across seven conditions, represented by 99,600 repeated scoring records. Changing from the best noisy observation to a common Gaussian-process recommendation reduced SPADE regret by 0.0543 but increased classical-design regret by 0.1035 in the retrospective Hill comparison. In the retained regenerated benchmark's prespecified six-factor, lower-noise Hill target, primary SPADE achieved map error 0.1804 versus 0.2131 for noisy Bayesian optimization, a 15.3% relative reduction. Paired inference used 25 landscape instances. The point-regret gap was 0.00937 (95% bootstrap interval 0.00258–0.01615), within the prespecified ±0.02 practical margin, with two feedback rounds rather than ten. Boundary targeting did not improve on a random second round: random-minus-targeted map error was −0.00188 (95% interval −0.00624 to 0.00261). Source reconciliation showed that map scores used a 0.50 probability cutoff and the reported certificate statistic measured posterior self-consistency, not empirical containment against the oracle. A separate 2,750-row development study tested future-response reliability. None of nine candidates satisfied the cross-family containment requirement, so selection stopped without opening the lockbox. These results quantify how terminal decisions and evaluation targets change method rankings within fixed budgets. Historical replay remains incomplete; neither transferable certification nor biological performance is established.

## Introduction

Optimization of cell-culture media, extracellular-matrix compositions, and bioprocess settings requires experimentation in continuous, multicomponent spaces. Even five levels across six factors define 15,625 combinations, far beyond a typical campaign. Classical design of experiments and response-surface methodology (RSM) address this burden with structured local models, screening, sequential movement, and second-order designs [1–3]. Bayesian optimization (BO) fits a probabilistic surrogate and chooses promising observations with an acquisition function [4–6]. Both families are now used in biological and bioprocess development [7–12].

These comparisons are hard to interpret because a workflow is more than its sampling rule. It also includes the surrogate, budget, number of feedback rounds, noise model, admissible extrapolation, and terminal decision. Published studies differ across these components. Rummukainen and colleagues compared a 15-run Box–Behnken design with a BO sequence that reused five initial experiments before ten new ones; noisy expected improvement selected the first nine new experiments and posterior mean selected the tenth [8]. Lapierre and colleagues compared multicycle batch BO with a two-step DoE workflow after shared screening [9]. Ndahiro and colleagues compared constrained BO with an equal-count JMP space-filling design, rather than classical RSM [10]. Narayanan and colleagues reported large reductions relative to predicted or traditional DoE requirements, not an executed equal-budget DoE arm [11]. Those studies answer important but different questions.

Most optimizer studies compress a campaign to one nominated formulation. That point estimand is appropriate when a laboratory needs one carry-forward recipe and can confirm it independently. It is incomplete when formulation tolerances, process variability, biological heterogeneity, or quality-by-design requirements make the deliverable an *operating region*: a set of compositions expected to satisfy a performance threshold despite limited data and assay noise. A method can locate a strong point while learning little about the surrounding space, or map a threshold-defined region while spending fewer observations on the global optimum. Point regret and region error are therefore distinct estimands, and comparisons that report only one can reverse rankings that would appear under the other.

We developed SPADE as a region-first workflow for that second deliverable. SPADE combines broad first-round coverage, a model-directed second round, a probability map of threshold exceedance, and a conservative certificate that can return no region when evidence is inadequate. We compared SPADE with one-shot space-filling designs, batch BO, and classical response-surface workflows under matched budgets. The benchmark tests whether point and region objectives reorder the same campaigns, reports wells and decision rounds separately, and distinguishes map accuracy from probability calibration, certificate containment, and certificate non-vacuity. An equal-well random control tests whether boundary targeting accounts for any second-round gain. A later registered development study asks the stricter question of whether one joint SPADE protocol satisfies map, regret, answer-rate, and containment requirements across five families.

Region estimation has an established methodological literature. Gotovos and colleagues developed GP confidence-bound classification and batch sampling for level-set estimation, and evaluated the straddle heuristic used here [13]. Azzimonti and colleagues developed conservative excursion-set estimation under a posterior inclusion constraint [14]. Bogunovic and colleagues unified BO and level-set estimation in truncated variance reduction (TruVaR), including heteroscedastic noise and observation costs [15]. These precedents establish both region-directed learning and the relationship between optimization and classification. SPADE contributes a particular two-round workflow and an evaluation of its components; it introduces neither the straddle acquisition nor a new theory of conservative sets.

The empirical question is how much these distinctions change conclusions within the same small-budget campaigns. We examine changes in method ordering under terminal rescoring, quantify the map-versus-regret trade-off under a common GP readout, and test the proposed targeting mechanism against an equal-well random control. The separate development study evaluates whether a posterior-based certificate survives direct checking against known truth. We do not claim that these questions were previously unrecognized, or that SPADE outperforms specialized level-set methods, which were not included as experimental arms.

All landscapes are controlled synthetic proxies for multimodality and noise, structurally motivated by multicomponent formulation logistics but not fitted to biological measurements. The 15,625-combination calculation illustrates a design burden; we did not exhaustively measure that discrete grid or demonstrate its biological replacement by 48 experiments. The study evaluates rankings under known synthetic truth. Biological transfer requires separate data and experiments.

## Materials and methods

### Study design and evidence bodies

The project contains three related but separate evidence bodies. First, stored BO, RSM, and space-filling campaigns were rescored under multiple terminal rules and as design-space maps. These retrospective analyses established the terminal-rule problem and motivated a region-first method. Second, the prospective study `spade-final-2026-08-23` froze the condition matrix, target classification, endpoints, inferential units, practical-effect thresholds, multiplicity families, feasibility rules, and claim gates before final study execution. Prospective results govern claims about the SPADE workflow evaluated in the main benchmark; retrospective results provide motivation and mechanism.

Third, a later joint-protocol development study tested whether a stricter certificate could generalize across Hill, Ackley, Hartmann6, Levy, and Rosenbrock families. It used the stop rule described below. These development results were not pooled with the retrospective or 99,601-record prospective evidence bodies. The prospective registration is the version-controlled specification at repository commit `c4f58d3`, rather than a journal-accepted Registered Report. The retained manifest identifies the analysis source and subsequent regeneration. Where the implemented statistic differs from the intended interpretation, we report the implemented object explicitly.

All experiments were computer simulations. No human participants, animals, cell lines, or biological specimens were used, and no institutional ethics approval was required. Factor labels were nominal, and the synthetic landscapes were not fitted to biological measurements.

### Benchmark decisions and estimands

Each campaign sampled a coded formulation space and could be scored as a point decision, a region decision, or both (Fig 1; Table 1). Point performance was simple regret at a prespecified terminal rule. Region performance was error in a threshold-defined acceptable set. Wells and experimental decision rounds were recorded separately because equal numbers of conditions do not imply equal latency.

![Benchmark decisions and estimands.](../results/paper-figures/plos/fig1.png)

**Fig 1. Benchmark decisions and estimands.** (A) Each method operates within one 48-well campaign. (B) The same sampled campaign supports point and region decisions. (C) The estimand ledger distinguishes the reported object, observability, score, additional wells, and experimental rounds for every deliverable. This figure defines the benchmark and contains no performance result.

**Table 1. Predeclared claim and stop-rule ledger.** Lower map error and lower regret are better. SESOI denotes the smallest effect of scientific interest.

| Claim gate | Estimand | Primary contrast | Decision rule | Outcome used for interpretation |
|---|---|---|---|---|
| Map leadership | Symmetric-difference error | SPADE m0 vs BO / space-filling / RSM | Direction + Holm family | Confirmatory target result |
| Point parity | Rule-P simple regret | SPADE m0 − qLogNEI | Entire 95% interval inside ±0.02 SESOI | Practical equivalence, not superiority |
| Targeting mechanism | Map error | Random Plate 2 − SPADE m0 | SESOI 0.02; Holm | Positive values favor targeting; null allowed |
| Plate-2 increment | Map error | SPADE m0 − Plate 1 only | Detectability and SESOI | Combined sample-size + round effect |
| Local allocation | Regret ∩ map ∩ calibration ∩ certificate | m4/m8 vs m0 | Prespecified conjunction | Safe-improvement rule |
| Certificate audit | Fraction meeting a held-out posterior check | Hill registered cells | Original binomial rule + non-empty floor ≥10 | Posterior self-consistency only; not empirical validity |
| Joint-protocol selection | Answer rate ∩ containment ∩ regret ∩ map | Nine candidates across five development families | Unanimous leave-one-family-out selection | Stop before power and lockbox if any fold returns `NO_SELECTION` |

### Synthetic formulation spaces and latent responses

A formulation was represented by a coded vector $x=(x_1,\ldots,x_d)\in[0,1]^d$, with $d=6$ or $d=8$. The primary landscape was a constructed biphasic Hill response. Each active coordinate combined activation and inhibition,

\[
h_i(x_i)=\frac{x_i^{n_i}}{\mathrm{EC}_{50,i}^{n_i}+x_i^{n_i}},\qquad
g_i(x_i)=\frac{1}{1+(x_i/\mathrm{IC}_{50,i})^{n_i}},
\]

whose normalized product has an interior marginal peak at $x_i^*=\sqrt{\mathrm{EC}_{50,i}\mathrm{IC}_{50,i}}$. The multivariate function combined weighted coordinate contributions and sparse pairwise interactions. Four coordinates received 90% of the marginal weight; the remaining coordinates received 10%. Interaction coefficients shifted conditional peaks, so the vector of marginal optima was not assumed to equal the joint optimum. Numerical optimization identified and stored the global optimum for every accepted instance.

Marginal peaks were drawn from $U(0.25,0.55)$, Hill exponents from $U(1,3)$, and sparse interaction coefficients from $U(-1,1)$, followed by prespecified acceptance filtering for identifiable, non-boundary optima. These distributions and filters were benchmark design choices, not biological estimates. The six-factor structure and subsequent four-factor classical stage were inspired by the workflow of Hall, Lin, and Ogle [7], but neither their response values nor fitted parameters were used. Their published study used 23 stage-one and 25 stage-two formulations; the 20+27+1 classical benchmark below was our own 48-well construction.

Hartmann6, Ackley, Levy, and Rosenbrock functions were added to test dependence on Hill geometry. The prospective matrix comprised seven conditions: Hill at six dimensions and both noise levels; Hartmann at six and eight dimensions under higher noise; and Ackley, Levy, and Rosenbrock at six dimensions under higher noise. Only six-dimensional Hill under lower noise satisfied the frozen target-regime criteria. The other conditions were robustness or predeclared-exception settings.

### Observation model

An assay-like observation was generated only when a method evaluated a point:

\[
y(x)=f(x)(1+\epsilon)+\eta,
\]

where $\epsilon\sim\mathcal{N}(0,\sigma_{\mathrm{rel}}^2)$ and $\eta\sim\mathcal{N}(0,0.01^2)$. Relative-noise levels were 0.10 and 0.25. These were lower- and higher-noise benchmark settings, not empirical assay coefficients of variation. The additive term prevented variance collapse near zero response. Gaussian-process (GP) models received the response-derived plug-in variance

\[
\widehat{\mathrm{Var}}(y\mid x)=y(x)^2\sigma_{\mathrm{rel}}^2+0.01^2,
\]

subject to a numerical floor. Because the latent function was known, terminal points and estimated regions could be scored against ground truth.

### Compared methods and experimental budgets

Principal comparisons used at most 48 evaluated conditions (Table 2). SPADE used 40 first-round Latin-hypercube points and eight second-round points. One-shot Latin-hypercube, Sobol, and uniform-random arms used 48 points. qLogEI and qLogNEI used an opening design followed by batches of up to four; the registry reports ten decision rounds. These logarithmic expected-improvement acquisitions address numerical difficulties in optimizing ordinary expected improvement [16]. The screened classical workflow used a 20-run screen, a 27-run four-factor face-centered central composite design, and one confirmation. This split was an in-house matched-budget construction, not Hall et al.'s published design. A full-dimensional central-composite arm was included where arithmetically feasible. At eight dimensions, the registered factorial and axial construction exhausted the budget before valid center replication; this does not imply that every possible RSM design is infeasible at 48 runs.

**Table 2. Compared methods, budgets, and intended deliverables.**

| Method | Design | Wells | Rounds | Primary purpose |
|---|---|---:|---:|---|
| SPADE variants | 40-point LHS plus eight model-directed points | 48 | 2 | Region mapping and certification |
| SPADE random Plate 2 | 40-point LHS plus eight random points | 48 | 2 | Equal-well targeting control |
| SPADE Plate 1 only | 40-point LHS | 40 | 1 | Additional-round reference, not equal-well |
| Latin hypercube | One-shot space-filling design | 48 | 1 | Broad coverage |
| Sobol | One-shot low-discrepancy design | 48 | 1 | Broad coverage |
| Uniform random | One-shot random design | 48 | 1 | Nonadaptive control |
| qLogEI | Opening design plus batch expected improvement | 48 | 10 | Point optimization |
| qLogNEI | Opening design plus noisy expected improvement | 48 | 10 | Noise-aware point optimization |
| Screened RSM | Screen, four-factor CCD, confirmation | 48 | 3 | Staged classical optimization |
| Unscreened RSM | Full-dimensional CCD where feasible | 48 | 1 | Screening/model diagnostic |

### SPADE implementation

Plate one used 40 Latin-hypercube points over all factors. A Matérn-5/2 automatic-relevance-determination GP was fitted with the plug-in variances above. Plate-two candidates were scored over a 4,096-point Sobol set using

\[
a_{\mathrm{straddle}}(x)=1.96s(x)-|\mu(x)-\theta|,
\]

where $\mu(x)$ and $s(x)$ were the posterior mean and standard deviation and $\theta$ was the working response threshold. This is the established straddle score reported by Gotovos et al. [13]. Eight points were selected greedily, with a Chebyshev exclusion radius based on the median fitted length scale. This geometric exclusion is not the covariance-updated batch rule of that study and does not inherit its guarantees. The model was then refitted to all 48 observations. These second-round points were new locations, not replicate confirmations.

The registered primary variant, `m0`, allocated all eight second-round wells to region learning. Variants `m4` and `m8` placed four or eight wells in a local region around the first-round posterior-mean maximizer. The local region was the unit ball in fitted length-scale coordinates. Greedy maximin selection spread these points relative to the existing design; any shortfall reverted to boundary selection and was recorded. The design threshold was the frozen moderate threshold, indexed by a nominal upper-tail prevalence of 0.25, and did not change across retrospective scoring configurations. A variant counted as a safe improvement only if it improved Rule-P regret by at least 0.02, worsened map error by no more than 0.02, worsened calibration by no more than 0.005, and retained acceptable certificate-check behavior.

### Point estimands and terminal rules

Maximizing the posterior mean is a standard terminal decision for a risk-neutral decision-maker under the fitted model [6]. Rule A is included to audit noisy selection, not as a recommended default for noisy BO. Holding observations fixed isolates the effect of the terminal rule; it does not prove that either rule is uniformly preferable under model misspecification.

Simple regret was $r(\widehat{x})=f(x^*)-f(\widehat{x})$. Hill landscapes were normalized so that $f(x^*)=1$. Rule A selected the evaluated point with the largest noisy observation. Rule P selected a model-recommended point. In the prospective benchmark, we refitted a common Matérn GP to every arm's observed data, including the classical designs, then maximized its posterior mean using a 20,000-point Sobol screen and ten continuous-optimization restarts with 512 raw starts and fixed locator seed zero. Thus, the prospective point results compare designs followed by a common GP terminal recommendation; their RSM rows are not terminal quadratic recommendations. The retrospective terminal-rule comparison also used a common GP for every arm, with the same grid size and seed but twenty restarts and 4,096 raw starts. Separate earlier extrapolation diagnostics compared arm-specific recommenders, including quadratic RSM; those diagnostics are distinct from the common-GP terminal-rule contrast.

For the retrospective decomposition, hidden tested-best regret was $f(x^*)-\max_i f(x_i)$. The difference between Rule-A regret and tested-best regret measured identification loss caused by selecting among noisy observations. Their sum equals Rule-A regret. Unconstrained model optima, constrained in-region recommendations, replication, and top-three confirmation were evaluated retrospectively to separate search, identification, and extrapolation effects. The constrained in-region RSM recommendation was not labeled ridge analysis because the implementation did not use the full classical ridge procedure [1–3].

### Acceptable-region estimands

For response threshold $\tau$, the true acceptable region was

\[
A_\tau=\{x\in\mathcal{X}:f(x)\geq\tau\}.
\]

The fitted model supplied a plug-in predictive exceedance probability,

\[
p_\tau(x)=\Phi\!\left(\frac{\mu(x)-\tau}{\sqrt{s^2(x)+\sigma_{\mathrm{rel}}^2\mu^2(x)+0.01^2}}\right),
\]

where $\Phi$ is the standard normal distribution function and $s^2(x)$ is latent posterior variance. The implemented prospective map used a 0.50 cutoff: $\widehat{A}_{\tau,0.50}=\{x:p_\tau(x)\geq0.50\}$. Under this Gaussian construction, that is the posterior-mean superlevel set. The primary map outcome was normalized symmetric-difference volume,

\[
E_\Delta=\frac{|\widehat{A}_{\tau,0.50}\triangle A_\tau|}{|\mathcal{X}|},
\]

where $|\cdot|$ denotes volume and lower values indicate better geometric agreement. Volumes were approximated on a 20,000-point Sobol grid with seed zero. The threshold labels 0.10 and 0.25 index frozen oracle-derived upper-tail quantiles; target-condition comparisons use the moderate 0.25 threshold. The runner reads one frozen threshold per condition, including across Hill instances. These labels therefore do not impose exactly the same prevalence on every instance. No reported map-error value was recomputed at a different probability cutoff for this manuscript.

The stored rows repeat map scores over nominal $\gamma$ and $\alpha$ configurations. Those labels are not independent map measurements: the prospective scorer computes its map once per campaign and response threshold, outside both loops. Area under the receiver-operating-characteristic curve (AUC), intersection over union, false-inclusion rate, Brier score, Murphy calibration, and Murphy refinement were secondary. Brier and calibration summaries used the noiseless binary label $\mathbf{1}\{f(x)\geq\tau\}$, not repeated future-observation outcomes. They assess agreement with latent acceptability and cannot establish calibration of future-response reliability [17].

### Conservative certificate, non-vacuity, and feasibility

SPADE constructed a conservative latent excursion set on a 2,000-point Sobol subset. Of 4,096 joint latent posterior draws, 2,048 selected among 64 Vorob'ev quantiles and 2,048 evaluated the selected set. The halves were generated sequentially from one seeded stream, preserving the archived sampling convention. For requested assurance $\alpha\in\{0.80,0.95\}$, the model-level target was

\[
\Pr(C_\alpha\subseteq A_\tau\mid D)\geq\alpha.
\]

Two distinct quantities were stored. Empirical containment was the binary oracle check $\mathbf{1}\{C_\alpha\subseteq A_\tau\}$ on the evaluation subset. The held-out posterior check was the fraction of evaluation draws containing the selected set. The original prospective report then counted campaigns whose held-out posterior fraction was at least $\alpha$. Its displayed numerator is therefore a posterior self-consistency pass count, not empirical containment against the oracle. We retain that statistic with its meaning corrected. Neither a held-out posterior check nor a failure to reject its nominal level establishes real-world coverage. The certificate masks also do not depend on the stored $\gamma$ labels in this prospective implementation.

Empty certificates were excluded from each displayed numerator and denominator and their frequency was reported separately. Hyperparameter uncertainty was not integrated. Containment on a finite evaluation subset does not establish containment throughout the continuous domain.

For multiplicative noise and a normalized maximum response, some threshold–assurance pairs cannot be certified even with perfect knowledge. We screened pairs using the approximate ceiling

\[
\tau_{\max}(\gamma,\sigma_{\mathrm{rel}})=1-z_\gamma\sigma_{\mathrm{rel}}.
\]

After a preregistered feasibility correction, condition-specific response quantiles and noise-dependent primary probability labels replaced combinations above this ceiling. The registry used $\gamma=0.50$ at relative noise 0.25 and $\gamma\in\{0.50,0.95\}$ at relative noise 0.10; 0.99 was diagnostic. Only conditions with feasible thresholds, acceptable-set prevalence between 0.05 and 0.60, projected non-empty certificates in at least half of pilot campaigns, and at least 5% of the grid in the posterior straddle band were eligible for the target regime. These labels controlled eligibility and report membership, but did not change the implemented map cutoff or latent certificate. We retain them for provenance and do not reinterpret this screen as proof of future-response certification.

### Replication and statistical analysis

Reported intervals quantify variation within the specified synthetic benchmark. They do not account for choosing a different landscape family, kernel, noise law, budget, or practical margin. The 0.02 margin is a benchmark design choice on normalized scores, not a clinically or industrially validated tolerance. Ordering sample means does not by itself establish a significant difference, and failure to reject a difference does not establish equivalence.

The prospective benchmark used 100 campaigns per available arm and condition. Hill campaigns comprised 25 stored landscape instances with four campaign seeds per instance. Paired map and regret contrasts were averaged within landscape before inference ($n=25$); seed-level analyses were retained as a direction-disagreement guard. External-family means summarize repeated campaigns on the specified function and do not represent 100 independently drawn function families. Wilcoxon signed-rank tests governed paired decisions, and 4,000 paired percentile-bootstrap resamples quantified effects. Exact *p*-values are reported where available; approximate scientific notation is used when only a rounded value was retained. The smallest effect of scientific interest (SESOI) was 0.02 for simple regret and symmetric-difference error. Practical point-regret parity required the entire paired bootstrap interval for SPADE minus qLogNEI to lie inside ±0.02.

The retained prospective certificate reports used binomial tails and Clopper–Pearson intervals on posterior-check pass counts, with a minimum non-empty count of ten. These intervals assume independent Bernoulli trials; they do not adjust for repeated Hill instances and are presented as diagnostics of the original analysis. They do not validate empirical oracle containment. Holm adjustment was applied within the four frozen comparison families: certificate checks, plate/allocation contrasts, allocation variants, and map comparators. No prospective outcome was pooled across conditions. Repeated threshold, probability, and assurance rows were not treated as additional campaigns in point or map inference.

### Joint-protocol development and selection

The joint-protocol study crossed three Sobol opening sizes (32, 40, and 44 observations) with three post-opening policies. The `staged` policy used qLogNEI for every later batch. The `fixed_hybrid` policy alternated qLogNEI with global integrated-variance reduction. The `validity_gated` policy alternated qLogNEI with boundary-weighted variance reduction when its prespecified diagnostic was satisfied and otherwise used global variance reduction. Sobol48 and qLogNEI48 were the two comparators. Every arm received exactly 48 observations. Fifty matched campaigns were run for each of 11 arms in each of five development families, yielding 2,750 campaign-arm rows.

This later study changed the target to future-response reliability. For the registered assay law, let $q_\tau(x)=\Pr(Y_{\mathrm{new}}(x)\geq\tau\mid f(x))$ and $R_{\tau,\gamma}=\{x:q_\tau(x)\geq\gamma\}$. The primary settings were $\gamma=0.95$, $\alpha=0.95$, relative noise 0.10, and additive noise 0.01. Thresholds were chosen per instance from a quantile of the noise-adjusted reliability margin to target 25% reliable-set prevalence. Models learned observation noise rather than receiving the earlier response-derived plug-in variances. Candidate sets were scored by the oracle event $C_\alpha\subseteq R_{\tau,\gamma}$. This is a different endpoint from both the earlier latent map and its posterior self-consistency check.

Selection used five leave-one-family-out folds. Within each four-family training fold, a candidate first needed an answer rate of at least 0.50 and empirical certificate containment of at least 0.90 in every family. Survivors then had to meet the prespecified 0.02 regret non-inferiority margin against qLogNEI48; map loss relative to Sobol48 and frozen tie-break rules ranked any remaining candidates. The same candidate had to win all five folds. A fold-level `NO_SELECTION` could not be overridden by an all-family refit. Only a unanimous `SELECTED` result could authorize the registered power calculation and access to four randomized lockbox families. Otherwise, the protocol required the study to stop with the lockbox unopened.

### Software and reproducibility

The implementation used Python, PyTorch, GPyTorch, BoTorch [18], NumPy, SciPy, pandas, and scikit-learn. The retained prospective manifest identifies Python 3.11.15, PyTorch 2.13.0, NumPy 2.4.6, SciPy 1.17.1, registration commit `c4f58d3`, and recovery code commit `1bf51f11695ae348ffa8993ad42992141558fb80`. Scientific requirements are hash-bound separately from the optional Word-generation dependencies.

The combined prospective artifact contains 99,601 records: 92,400 original-arm scoring records, 7,200 unscreened-RSM scoring records, and one declaration that the eight-dimensional unscreened design was unavailable. Each available campaign contributes 12 configurations from two response thresholds, three probability labels, and two assurance levels. Consequently, 99,600 scored records represent 8,300 campaign-arm executions, not 99,600 independent experiments. The separate joint-protocol development study contains 2,750 campaign-arm rows and an immutable selection artifact. S1–S3 Tables provide the prospective calibration summaries, seven-condition comparisons for six matched-budget strategies, and the original decision ledger alongside source-reconciled interpretations.

The manifest records regeneration on 25 August 2026 because the first prospective raw files had been ignored by version control and could not be recovered. The current paper uses the retained regenerated files. The manifest preserves both original and replacement hashes and records the correction of a stale per-row feasibility flag. Reanalysis of the restored joint-protocol shards reproduced the stored development analysis exactly. These recovery and reanalysis checks do not establish exact replay of every historical adaptive trajectory. Source data, provenance, analysis scripts, and the unchanged failure checks are part of the intended archival release; its public identifier remains subject to deposition.

### Artificial intelligence assistance

OpenAI Codex assisted with manuscript drafting and revision, literature lookup, source-code inspection, figure-generation code, and document formatting. During publication preparation, numerical claims were checked against retained results and analysis code, figure labels were checked with renderer-level tests and visual inspection, and the manuscript was rendered for page-by-page review. No primary result files were altered to improve the reported findings. [AUTHOR CONFIRMATION REQUIRED: complete the study-wide inventory of AI tools and document the authors' review of scientific interpretations, references, code, and generated text before submission.]

## Results

### Terminal decisions changed comparative point performance

On identical retrospective campaigns, changing only the final decision rule changed the apparent winner (Fig 2). In the six-dimensional, higher-noise Hill benchmark, the staged classical arm achieved lower measured-selection regret than qLogEI or qLogNEI, yet hidden tested-best regret was much closer. This indicated that much of the difference arose from identifying a winner under noise rather than from the quality of sampled points. Moving from Rule A to Rule P reduced SPADE regret by 0.0543 but increased classical RSM regret by 0.1035. A top-three confirmation protocol reduced the primary classical-versus-BO difference to approximately −0.0009.

![Terminal-rule sensitivity.](../results/paper-figures/plos/fig2.png)

**Fig 2. The terminal decision rule changes comparative performance on the same campaigns.** (A) Mean simple regret under measured-selection Rule A and common-GP model-recommendation Rule P for the Hill ($d=6$, $\sigma_{\mathrm{rel}}=0.25$) benchmark ($n=50$ paired campaigns per method). (B) Paired Rule P minus Rule A differences with 95% paired-bootstrap intervals; negative values favor Rule P. SPADE shows the largest reduction (−0.0543), whereas the classical design increases regret (+0.1035) under the shared GP readout. (C) For compatible arms, Rule-A regret is decomposed into search loss and identification loss.

Separate earlier diagnostics found that the unconstrained quadratic model recommendation frequently extrapolated to unsupported points, producing a large apparent BO advantage. The classical stationary point was a saddle in 200 of 200 Hill diagnostic runs. Constraining that quadratic recommendation to the explored region largely removed the extreme contrast. These diagnostics motivated a common terminal rule, but they do not explain the common-GP contrast in Figure 2 by themselves.

### Target map gains depended on the comparator

The registered target was six-dimensional Hill at relative noise 0.10. SPADE variants occupied a leading map-error range of 0.1770–0.1804 (Table 3). The registered primary arm, SPADE m0, achieved map error 0.1804, compared with 0.1913 for Sobol, 0.2067 for qLogEI, 0.2131 for qLogNEI, 0.2502 for unscreened RSM, and 0.2580 for screened RSM. Its difference from qLogNEI was −0.03265, with Holm-adjusted *p* approximately $1.8\times10^{-7}$. Using the rounded means, the relative reduction was $(0.2131-0.1804)/0.2131=15.3\%$. This percentage concerns the implemented latent-map score in one target condition. The equal-well random-second-plate control achieved 0.1785, numerically better than m0, as examined by the mechanism test below.

**Table 3. Registered target-condition means. Lower values are better.** Each mean uses 25 Hill landscape instances, with four campaign seeds averaged within each instance. Point scores use the common GP Rule-P recommendation. Map scores use the moderate frozen response threshold and a 0.50 cutoff; the stored probability and assurance labels do not alter these map values. Bold identifies the registered primary arm, not statistical significance; ordering is descriptive.

| Method | Wells | Rounds | Rule-P regret | Symmetric-difference error |
|---|---:|---:|---:|---:|
| SPADE m4 | 48 | 2 | 0.0871 | 0.1770 |
| SPADE random Plate 2 | 48 | 2 | 0.0822 | 0.1785 |
| SPADE m8 | 48 | 2 | 0.0835 | 0.1797 |
| **SPADE m0, registered primary** | **48** | **2** | **0.0844** | **0.1804** |
| Latin hypercube | 48 | 1 | 0.0747 | 0.1867 |
| Sobol | 48 | 1 | 0.0855 | 0.1913 |
| SPADE Plate 1 only | 40 | 1 | 0.0863 | 0.1921 |
| Uniform random | 48 | 1 | 0.0905 | 0.2050 |
| qLogEI | 48 | 10 | 0.0798 | 0.2067 |
| qLogNEI | 48 | 10 | 0.0750 | 0.2131 |
| Unscreened RSM | 48 | 1 | 0.2866 | 0.2502 |
| Screened RSM | 48 | 3 | 0.3072 | 0.2580 |

qLogNEI achieved better point regret than primary SPADE, 0.0750 versus 0.0844. The paired mean gap was 0.00937, with a bootstrap interval of 0.00258–0.01615. The entire interval lay within the prespecified 0.02 practical margin. This supported practical point-regret parity in the target condition, not SPADE point superiority. All principal methods used 48 wells, but SPADE used two decision rounds, compared with ten for batch BO (Fig 3).

![SPADE point, map, and round evidence.](../results/paper-figures/plos/fig3.png)

**Fig 3. Point, map, and experimental-cost evidence for SPADE.** (A) Registered Hill-target means for symmetric-difference map error and Rule-P simple regret ($n=25$ landscape-level means per method); lower is better on both axes. (B) Paired SPADE-minus-comparator contrasts with 95% intervals and the prespecified ±0.02 smallest effect size of interest. SPADE has lower map error than Sobol (−0.0109, below the practical threshold) and qLogNEI (−0.0327), while Rule-P regret is +0.0094 relative to qLogNEI. (C) Every equal-budget method consumes 48 wells, but feedback ranges from one to ten rounds. (D) Hartmann ($d=6$ and $d=8$) robustness values are descriptive means; intervals are unavailable.

The simpler space-filling comparators limit the interpretation of map leadership. SPADE's map advantage over Sobol was 0.01089 (95% interval 0.00597–0.01566), entirely below the 0.02 practical threshold. One-shot Latin hypercube achieved map error 0.1867, only 0.0063 above primary SPADE, while attaining lower point regret (0.0747 versus 0.0844) in one round rather than two. The retained claim ledger contains no paired inferential decision for this LHS contrast, so these means establish neither LHS equivalence nor SPADE superiority. They identify a strong simple comparator that the 15.3% contrast against qLogNEI alone would miss.

### Boundary targeting did not beat random placement

The registered mechanism test compared boundary targeting with random placement under an equal well budget. The effect, defined as random-second-round minus m0 map error, was −0.00188 (95% interval −0.00624 to 0.00261; Holm-adjusted *p* = 0.4108). Negative values favor the random control. Boundary-focused placement therefore showed no advantage over eight random second-round points. The tested targeting rule does not explain SPADE's target-condition map performance.

The unequal-well Plate 1 reference had map error 0.1921; primary SPADE at 48 wells had 0.1804. The paired improvement was 0.0117 (95% bootstrap interval approximately 0.0074–0.0156; Holm-adjusted *p* approximately $1.3\times10^{-4}$). It was statistically detectable but smaller than the 0.02 SESOI. Because Plate 1 used eight fewer wells, this comparison conflates additional sample count with a second round and does not rescue the equal-well targeting null.

### Exploitative allocation did not satisfy the safe-improvement rule

The m4 variant produced Rule-P regret 0.0871 versus 0.0844 for m0, a deterioration of approximately 0.0028. Its paired interval crossed zero and it did not meet the required 0.02 improvement. The prespecified conjunction also required acceptable changes in map error, calibration, and certificate behavior. That conjunction failed. Although m4 had the lowest target-condition map-error mean, it was not classified as a validated allocation improvement.

### Point and region rankings separated on Hartmann landscapes

At six-dimensional Hartmann, qLogNEI and qLogEI achieved Rule-P regrets of 0.2305 and 0.2997, ahead of primary SPADE at 0.4221. Map error reversed the ordering: SPADE m4, m8, and m0 achieved 0.1815, 0.1836, and 0.1848, compared with 0.1899 for Sobol, 0.2243 for qLogNEI, and 0.2259 for qLogEI. At eight dimensions, qLogNEI and qLogEI again led point regret at 0.2620 and 0.2945, whereas SPADE m4, m0, and m8 led map error at 0.1883, 0.1908, and 0.1950. These were descriptive robustness results, not additional confirmatory target-regime wins.

Ackley behaved as the predeclared exception. Screened RSM achieved the lowest point regret, 0.5539, but map error was 0.4599, almost twice the 0.23–0.24 range of most alternatives. SPADE certificates were empty in most Ackley campaigns, indicating refusal to certify. Levy and Rosenbrock map errors were compressed near 0.25 under their feasible primary probability level; those cells provided little method discrimination and were not forced into a winner narrative.

### Sharp maps were not necessarily well calibrated

In the retrospective Hill Murphy analysis, primary SPADE had the highest AUC (0.7583) and refinement (approximately 0.0151), but calibration error was approximately 0.0359. Sobol had lower calibration error (0.0289) and the lowest Brier score. Screened RSM had calibration error 0.2296 and ranked last on refinement. Thus, SPADE produced sharp probability separation without being the best-calibrated method (Fig 4A). These descriptive summaries pool repeated threshold cells and do not treat them as independent campaigns. The standalone prospective calibration table reports Brier score, Murphy calibration, Murphy refinement, AUC, map error, point regret, wells, and rounds from the final raw rows without pooling conditions.

![Calibration and certificate evidence.](../results/paper-figures/plos/fig4.png)

**Fig 4. Calibration, posterior checks, and empirical containment are different outcomes.** (A) Retrospective Hill calibration and refinement use $n=1{,}200$ repeated threshold cells per method. (B) Prospective Hill fractions of non-empty campaigns meeting the held-out posterior check, minus $\alpha$. This is posterior self-consistency, not empirical containment. The original 95% binomial intervals are retained as diagnostics; they do not adjust for repeated Hill instances. Downward triangles mark unadjusted intervals below $\alpha$, not Holm-adjusted decisions. Stored $\gamma$ labels identify report cells but do not alter the latent certificates. (C) In the separate retrospective study at $\alpha=0.95$, campaigns with any non-empty certificate were 0/50 for Ackley, 11/50 for Hartmann6, 50/50 for Hill, 49/50 for Levy, and 50/50 for Rosenbrock. Zero means refusal to certify. (D) At $\alpha=0.80$, empirical oracle containment pools dependent non-empty threshold cells. These proportions are descriptive, without binomial intervals or a cross-family validity test. Panels C and D use different assurance levels.

### Posterior certificate checks did not establish empirical validity

In the original prospective Hill report, no eligible posterior-check cell was below its comparison level after binomial inference and Holm correction. The weakest reported pass fraction was 11/13, or 0.8462, against 0.80; the retained 95% interval was approximately 0.546–0.981 and adjusted *p* = 1.0. Eleven here counts campaigns passing a held-out posterior-probability check, not eleven sets contained in oracle truth. The result cannot support empirical certificate validity, even in Hill. The small non-empty denominator and repeated-instance structure further limit interpretation.

The retrospective five-family analysis used oracle containment and exposed a separate failure mode. At assurance 0.80, pooled non-empty cells had containment 16/32 for Hartmann6, 802/808 for Hill, 697/747 for Levy, and 778/845 for Rosenbrock; Ackley returned no non-empty cells at that assurance. These are repeated-cell descriptions, not independent binomial experiments (Fig 4D). At assurance 0.95, campaigns returning any non-empty certificate were 0/50 for Ackley, 11/50 for Hartmann6, 50/50 for Hill, 49/50 for Levy, and 50/50 for Rosenbrock. Answer frequency and containment must therefore be reported separately.

Eighteen of 64 original certificate-report cells passed the posterior-check rule while returning empty sets in more than half of campaigns; the non-vacuity guard downgraded them to inconclusive. After regeneration, zero of 23,600 primary-label rows entered analysis above the registered feasibility ceiling. These are audit counts across repeated configurations. They show what the reporting guards excluded, but do not repair the distinction between model checks and oracle validity.

### The stricter joint protocol stopped at the development gate

The separate joint-protocol grid completed all five development families, 11 arms, and 50 campaign keys per family, for 2,750 validated rows. The registered unanimous leave-one-family-out selector returned `NO_SELECTION`. In every fold, each of the nine SPADE candidates fell below the 0.90 empirical-containment floor in at least one training family. No candidate reached the subsequent regret or map-ranking steps. Because no candidate was selected, no power artifact was created and the reserved lockbox remained unopened.

This result does not alter the target-condition map comparisons above because the studies used separate protocols and evidence bodies. Lower map error in the Hill target did not establish a certificate that transferred across all development families under the stricter gate. Table 4 reports the development ranges across all nine candidates.

**Table 4. Separate joint-protocol development results across nine candidates.** Ranges are the minimum and maximum across candidates, not confidence intervals. Each candidate ran 50 matched campaigns per family. Containment denominators exclude empty certificates. The 0.90 floor had to hold in every training family; an isolated passing family could not qualify a candidate.

| Development family | Campaigns answering out of 50 | Empirical containment range |
|---|---|---|
| Hill | 49–50 | 0.140–0.490 |
| Ackley | 50 | 0.320–0.820 |
| Hartmann6 | 50 | 0.440–0.940 |
| Levy | 47–49 | 0.213–0.333 |
| Rosenbrock | 47–50 | 0.061–0.320 |

### Full-dimensional RSM did not recover the region map

In the target condition, unscreened RSM improved map error from 0.2580 to 0.2502 and Rule-P regret from 0.3072 to 0.2866 relative to screened RSM, but remained behind SPADE and the space-filling methods. At eight dimensions, a valid full-dimensional CCD with center replication was impossible within 48 wells and was declared unavailable. Retrospective diagnostics further showed that the screened pooled design was rank-deficient in 50/50 campaigns, the fitted stationary point was a saddle in 200/200 Hill runs, and the quadratic confirmation overpredicted response in 25/25 campaigns at both noise levels. These results diagnose the implemented fixed-budget pipeline; they do not invalidate RSM generally, which normally includes canonical analysis, constrained or ridge analysis, replication, steepest ascent, and relocation safeguards [1–3].

## Discussion

The clearest result is a comparator-dependent trade-off. Primary SPADE mapped the target Hill region more accurately than qLogNEI while accepting a small loss in point performance. Against simple space-filling designs, its advantage was much smaller. Rescoring the retrospective campaigns also changed method ordering without changing the sampled observations. Together, these results show how a favorable comparison under one reported endpoint can coexist with an unfavorable comparison under another. They do not establish that a region-directed acquisition is necessary to obtain a useful region map.

### Relationship to published studies

Published studies provide different kinds of evidence (Table 5). The pilot experiments of Rummukainen et al. [8] test optimization in a physical process, while the studies of Lapierre et al. [9], Ndahiro et al. [10], and Narayanan et al. [11] demonstrate biological or bioprocess outcomes. Our simulations provide known truth throughout the domain, which permits direct point and set scoring, but lack those studies' evidence of physical performance. Their reported productivity or experimental-efficiency gains cannot be compared numerically with our 15.3% reduction in synthetic map error.

The closer methodological precedents are level-set estimation and conservative excursion sets [13–15]. These works already distinguish learning a set from locating an optimum. Our straddle implementation is a restricted two-round adaptation with geometric batch exclusion; its null targeting result does not refute covariance-aware batch level-set methods. Likewise, failure of the tested certificates under empirical checking does not disprove posterior excursion-set theory. It identifies a gap between a model-conditional construction and its behavior on the benchmark's fixed truth functions.

Recent synthetic evidence also cautions against attributing performance only to an acquisition name. Mia et al. examined six-variable Ackley and Hartmann tasks and found that batch-BO outcomes depended on noise, landscape geometry, and acquisition settings [19]. Our response-dependent noise law, opening design, kernel, and 48-evaluation schedule define a different comparison. Neither study establishes a ranking that transfers unchanged to other noise models or campaign budgets.

**Table 5. Selected published precedents and the scope of the present contribution.** This targeted comparison is not a systematic review or a cross-paper performance ranking. Different outcomes and budgets preclude comparing effect sizes directly.

| Study | Evidence and objective | Relationship to this benchmark |
|---|---|---|
| Rummukainen et al. [8] | Pilot-scale delignification; Box–Behnken and adaptive BO | Physical process validation; shared starting experiments and a posterior-mean final BO experiment |
| Lapierre et al. [9] | Batch BO and two-step DoE for growth media | Biological growth outcomes; not the same endpoint as latent region error |
| Ndahiro et al. [10] | Constrained media optimization versus space-filling design | A space-filling comparator, not an end-to-end RSM arm |
| Gotovos et al. [13] | Level-set classification and batch sampling | Established straddle baseline; covariance-aware batching differs from our geometric exclusion |
| Azzimonti et al. [14] | Conservative excursion sets under posterior inclusion constraints | Methodological foundation, not evidence of empirical validity for our fitted models |
| Bogunovic et al. [15] | TruVaR unifies BO and level-set estimation | Direct methodological precedent; not included as a comparator here |
| Mia et al. [19] | Synthetic batch BO under varying noise and geometry | Closely related computational evidence; different noise law, schedule, and evaluation targets |
| Present study | Fixed-budget point/map rescoring, targeting control, certificate audit | Quantifies endpoint-dependent trade-offs; no specialized-method superiority or biological validation |

### Practical meaning of the observed differences

SPADE was designed for the region objective. In the prespecified Hill target, SPADE variants produced the lowest range of symmetric-difference errors among the modeled workflows, and the registered primary arm remained within the practical point-regret margin relative to qLogNEI. The operational profile also differed: SPADE used two decision rounds, whereas batch BO used ten. This difference may matter when feedback requires days of incubation, cell expansion, or manual analysis, but the benchmark measured rounds rather than calendar time, labor, or cost. A claim of fivefold faster experimentation would therefore be unsupported.

Boundary-targeted second-round placement did not outperform an equal-well random second plate, and the improvement over Plate 1 was smaller than the SESOI. One-shot LHS also approached SPADE's map accuracy while achieving lower point regret in fewer rounds. These findings make broad coverage a plausible explanation for much of the observed map performance, but they do not isolate the contribution of the surrogate or establish LHS equivalence. A laboratory choosing between these workflows would need evidence that the small map difference justifies an additional feedback round. The present benchmark supplies no calendar-time or financial estimate for that decision.

The Hartmann results extend the point-versus-map distinction beyond the target condition. The tested BO arms located stronger points, whereas SPADE estimated the latent acceptable region more accurately at both dimensions. This pattern is consistent with a trade-off between optimum-seeking and broad domain coverage; it does not identify a universally better method. The prospective comparison also used a common GP for final recommendations, including classical designs. It therefore compares sampling strategies under that shared analysis rule, not the best possible end-to-end implementation of classical RSM. Specialized level-set acquisition methods were not directly compared.

Calibration and certificate results concern different claims. Symmetric-difference error measures geometric disagreement with the latent set. Calibration concerns probabilities against a specified event. A conservative certificate is a joint set-containment statement conditional on a model. SPADE was sharp but not best calibrated retrospectively. The prospective report's held-out posterior check did not measure empirical oracle containment and cannot establish validity even in the target Hill condition. Independent posterior draws reduce reuse of Monte Carlo samples; they do not test whether the fitted model describes the true response surface. A design-space evaluation must report actual oracle or independently observed containment and the non-empty rate separately from internal posterior checks.

The later joint-protocol study tested this boundary prospectively and failed at the intended decision point. None of the nine candidates met the cross-family development rule, so the workflow stopped before power analysis or lockbox evaluation. The stopping rule prevented a target-regime result from being promoted into an unsupported general certificate. Method development must improve cross-family containment on a fresh registered development grid before another confirmatory attempt.

### Scope and reproducibility limitations

The simulation-reporting framework of Morris et al. separates aims, data-generating mechanisms, estimands, methods, and performance measures, and emphasizes Monte Carlo uncertainty [20]. Here, the paired Hill analysis uses 25 independently generated instances; its four seeds per instance quantify repeated campaign behavior rather than expanding the landscape sample to 100. External-function means characterize the named functions only. The inferential results therefore support the prespecified target condition, while the other conditions indicate sensitivity to selected geometries. We did not perform a complete factorial sensitivity study over kernels, initial designs, budgets, and noise specifications.

Known landscapes, matched budgets, frozen claim gates, and retained artifacts make the comparisons auditable, but do not remove implementation and model assumptions. The benchmark omits donor and batch hierarchy, plate-position effects, cell-state drift, failed wells, assay censoring, formulation constraints, toxicity, osmolarity, multiple endpoints, reagent costs, and biological confirmation. Campaign seeds are not biological replicates. The Hill generator was structurally motivated by a multicomponent biological problem but was not fitted to endothelial or bioprocess data. Implications for laboratory practice should therefore be treated as transfer hypotheses, not as conclusions of this study.

Historical replay checks address exact regeneration, a different claim from recomputing summaries from archived rows. A current exact-replay check of the classical Rule-P source used in Figure 2 returned regret 0.2525112459 versus the stored 0.2525116337 for one campaign, a difference of $3.88\times10^{-7}$. The stored aggregate was not replaced. A separate one-campaign calibration check completed its checkpoint writing but stopped at the map-fidelity gate, with worst drift $9.08\times10^{-13}$ and no changed latent-map cells. Three historical adaptive-replay tests also reported material qLogEI/qLogNEI discrepancies on external-family reference columns. These failures have different magnitudes and do not establish that the entire archive is wrong, but exact regeneration of every historical result is not established. The repository retains the failed equality checks and their audit. The prospective release checks apply to their own evidence body; they do not resolve these retrospective replay failures or establish universal reproducibility.

Several methodological limitations also remain. GP uncertainty was conditional on plug-in hyperparameters. The original protocol used response-derived observation variances and fixed evaluation grids. Its map mask used a 0.50 cutoff regardless of stored probability labels; its certificates targeted latent response, not future-response reliability. Calibration scores against latent threshold labels therefore do not establish calibration for repeated noisy outcomes. Finite-grid set checks do not prove containment everywhere in a continuous domain. These implementation distinctions were identified during manuscript preparation and are disclosed without changing the retained results. Original certificate intervals also ignored repeated Hill instances. Some external-family cells were weakly discriminating or frequently empty. The full-dimensional classical arm was unavailable at eight dimensions under the chosen budget. The comparison covered representative implementations rather than every BO, RSM, or level-set method. The later joint-protocol development result must remain separate from the main benchmark: it returned `NO_SELECTION`, authorized no power analysis, and left the lockbox unopened. It supplies negative evidence about future-response certificates, not a replacement estimate for any result reported from the 99,601-record study.

### Replay impact on the reported claims

A claim-level dependency audit separated the eight failing historical gates from the inputs to this paper. The material adaptive discrepancies concern the older Q42/Q59 external-function Rule-A references. Those reference columns are not used to support cross-family method rankings in this paper. The prospective comparisons instead use the retained regenerated final-SPADE condition files. Reaggregation of the target file gave map errors 0.180414 for primary SPADE and 0.2130685 for qLogNEI, a 15.3258% relative reduction. This verifies the reported summary, not regeneration of the underlying adaptive campaigns.

The distinction is version-specific: the current default sampler is not the archived sampler. Commit `01d2ea5` introduced an explicit acquisition-sampler seed after the prospective recovery version `1bf51f1`. In three existing external-function diagnostic cases, restoring the legacy sampler reproduced the prospective archive's Rule-A scalars exactly but did not recover the older Q42/Q59 references. Scalar agreement is not a trajectory or map-replay validation. Shared optimizer code therefore remains a reproducibility risk even where the failing reference files are not numerical inputs. The prospective Hartmann and Ackley comparisons are descriptions of the archived benchmark, not independently replay-validated robustness claims.

For the observed classical Hill discrepancy, a one-row sensitivity reanalysis changed the 50-campaign mean Rule-P regret by only $7.76\times10^{-9}$ and left the displayed four-decimal contrast, its bootstrap interval, Wilcoxon result, and selected-arm ordering unchanged. Replacing only the checked calibration campaign's 24 cells in memory changed the classical arm's mean calibration error by $2.58\times10^{-15}$, without changing the displayed four-arm ordering; its refinement and AUC were unchanged. These substitutions were diagnostics only: no archived rows were replaced. This evidence does not bound errors in untested campaigns or establish a general numerical tolerance. We retain the exact failure gates and restrict conclusions to the identified archived evidence bodies.

### Implications for subsequent evaluations

A stronger computational comparison should include covariance-aware batch level-set sampling and TruVaR alongside one-shot LHS, with matched budgets and a shared terminal rule. Initialization and surrogate changes should be isolated rather than bundled into the acquisition comparison. Repeated randomized instances, an independent scoring grid, and prespecified sensitivity analyses would test whether the observed map-versus-point trade-off survives changes in geometry and noise. Such work would be a new study; it cannot be added retrospectively to the original confirmatory claim set.

For a wet-lab evaluation, the point and region deliverables should be specified before sampling. Point recommendations require independent confirmation with its cost counted. Region validation requires measurements in predicted interior, boundary, and exterior locations, with biological batches and plate position accounted for. The meaningful error margin should come from the application, not the normalized 0.02 benchmark choice. Reporting the random-placement control, non-empty rate, empirical containment, and operational cost would make a negative mechanism or certificate result interpretable rather than hiding it behind a favorable optimization curve.

## Conclusions

Within the retained benchmark, point and region objectives reversed method rankings under matched experimental budgets. In the registered six-factor synthetic target condition, SPADE m0 reduced latent-map error by 15.3% relative to qLogNEI, retained practical point-regret parity, and used two feedback rounds rather than ten. Its map advantage over Sobol was below the practical threshold, and one-shot LHS had similar mean map error with lower mean point regret. Boundary targeting did not beat random placement. The original prospective posterior checks did not establish empirical certificate validity. A separate future-response protocol returned `NO_SELECTION` at its five-family development gate, so no lockbox evidence was opened. These results support explicit separation of sampling, final selection, mapping, and certificate validation in experimental-design benchmarks. They do not establish universal SPADE superiority, complete historical replay, or a validated biological design space.

## Data availability statement

The archival submission release will include data, metadata, and code underlying the reported findings: the seven retained prospective raw condition files, retrospective evidence, the separate joint-protocol development and `NO_SELECTION` artifacts, source data for tables and figures, provenance hashes, and validators. The four lockbox generators remain frozen and contain no opened outcome data. Before submission, the release must be deposited in a public archival repository and this statement updated with its DOI and reviewer-access URL. [REPOSITORY DOI REQUIRED BEFORE SUBMISSION]

## Author contributions

[CRediT ROLES TO BE CONFIRMED FOR EVERY AUTHOR: Conceptualization; Data curation; Formal analysis; Funding acquisition; Investigation; Methodology; Project administration; Resources; Software; Supervision; Validation; Visualization; Writing – original draft; Writing – review & editing.]

## Acknowledgments

[ACKNOWLEDGMENTS TO BE CONFIRMED]

## References

1. Box GEP, Wilson KB. On the experimental attainment of optimum conditions. J R Stat Soc Series B Stat Methodol. 1951;13:1–38. doi:10.1111/j.2517-6161.1951.tb00067.x
2. Box GEP, Draper NR. Empirical model-building and response surfaces. New York: Wiley; 1987.
3. Myers RH, Montgomery DC, Anderson-Cook CM. Response surface methodology: Process and product optimization using designed experiments. 4th ed. Hoboken: Wiley; 2016.
4. Močkus J. On Bayesian methods for seeking the extremum. In: Marchuk GI, editor. Optimization techniques IFIP Technical Conference. Berlin: Springer; 1975. p. 400–404. doi:10.1007/3-540-07165-2_55
5. Jones DR, Schonlau M, Welch WJ. Efficient global optimization of expensive black-box functions. J Glob Optim. 1998;13:455–492. doi:10.1023/A:1008306431147
6. Frazier PI. A tutorial on Bayesian optimization. arXiv:1807.02811 [Preprint]. 2018 [cited 2026 Aug 26]. Available from: https://arxiv.org/abs/1807.02811
7. Hall ML, Lin W-H, Ogle BM. Optimizing extracellular matrix for endothelial differentiation using a design of experiments approach. Sci Rep. 2025;15:24479. doi:10.1038/s41598-025-09256-9
8. Rummukainen H, Hörhammer H, Kuusela P, Kilpi J, Sirviö J, Mäkelä M. Traditional or adaptive design of experiments? A pilot-scale comparison on wood delignification. Heliyon. 2024;10:e24484. doi:10.1016/j.heliyon.2024.e24484
9. Lapierre F, Mattaliano P, Raith D, Castillo-Cota M, Bermeitinger J, Huber R. Multi-cycle high-throughput growth media optimization using batch Bayesian optimization. J Chem Technol Biotechnol. 2025;100:1571–1583. doi:10.1002/jctb.7860
10. Ndahiro N, Ma E, Bertalan T, Donohue M, Kevrekidis Y, Betenbaugh M. Integration of Bayesian optimization and solution thermodynamics to optimize media design for mammalian biomanufacturing. iScience. 2025;28:112944. doi:10.1016/j.isci.2025.112944
11. Narayanan H, Hinckley JA, Barry R, Dang B, Wolffe LA, Atari A, Tseng Y-Y, Love JC. Accelerating cell culture media development using Bayesian optimization-based iterative experimental design. Nat Commun. 2025;16:6055. doi:10.1038/s41467-025-61113-5
12. Gisperg F, Klausser R, Elshazly M, Kopp J, Přáda Brichtová E, Spadiut O. Bayesian optimization in bioprocess engineering—Where do we stand today? Biotechnol Bioeng. 2025;122:1313–1325. doi:10.1002/bit.28960
13. Gotovos A, Casati N, Hitz G, Krause A. Active learning for level set estimation. Proceedings of the Twenty-Third International Joint Conference on Artificial Intelligence. 2013. Available from: https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf
14. Azzimonti D, Ginsbourger D, Chevalier C, Bect J, Richet Y. Adaptive design of experiments for conservative estimation of excursion sets. Technometrics. 2021;63:13–26. doi:10.1080/00401706.2019.1693427
15. Bogunovic I, Scarlett J, Krause A, Cevher V. Truncated variance reduction: A unified approach to Bayesian optimization and level-set estimation. Advances in Neural Information Processing Systems. 2016;29. Available from: https://papers.neurips.cc/paper_files/paper/2016/hash/ce78d1da254c0843eb23951ae077ff5f-Abstract.html
16. Ament S, Daulton S, Eriksson D, Balandat M, Bakshy E. Unexpected improvements to expected improvement for Bayesian optimization. Advances in Neural Information Processing Systems. 2023;36. Available from: https://proceedings.neurips.cc/paper_files/paper/2023/hash/419f72cbd568ad62183f8132a3605a2a-Abstract-Conference.html
17. Gneiting T, Raftery AE. Strictly proper scoring rules, prediction, and estimation. J Am Stat Assoc. 2007;102:359–378. doi:10.1198/016214506000001437
18. Balandat M, Karrer B, Jiang D, Daulton S, Letham B, Wilson AG, et al. BoTorch: A framework for efficient Monte-Carlo Bayesian optimization. Advances in Neural Information Processing Systems. 2020;33. Available from: https://proceedings.neurips.cc/paper/2020/hash/f5b1b89d98b7286673128a5fb112cb9a-Abstract.html

19. Mia I, Tiihonen A, Ernst A, Srivastava A, Buonassisi T, Vandenberghe W, et al. Multi-variable batch Bayesian optimization in materials research: Synthetic data analysis of noise sensitivity and problem landscape effects. J Mater Res. 2026;41:927–948. doi:10.1557/s43578-026-01803-y
20. Morris TP, White IR, Crowther MJ. Using simulation studies to evaluate statistical methods. Stat Med. 2019;38:2074–2102. doi:10.1002/sim.8086

## Supporting information captions

**S1 Table.** Prospective calibration and refinement metrics from final raw rows. Means use 25 Hill landscape instances with four campaign seeds averaged within each instance. Calibration uses latent acceptability labels, maps use a 0.50 cutoff, and point recommendations use a common GP. The CSV contains all 12 available target-condition arms, including the 40-well reference.

**S2 Table.** Seven-condition comparison for six matched-budget strategies. Hill estimates use 25 instances with four campaigns per instance; external-function estimates summarize 100 campaigns on each specified function. Archived certificate statuses refer to posterior checks, not empirical validity. All listed arms use 48 wells; lower map error and Rule-P regret are better.

**S3 Table.** Archived claim decisions and current source-reconciled interpretations. Original statuses, numerical results, and interpretation text are preserved in separate columns from the corrected interpretation. Certificate checks do not establish empirical validity, the Plate-2 gain is below the practical threshold, and the qLogNEI map contrast exceeds that threshold. Denominators retain their original units and are not uniformly independent campaigns.
