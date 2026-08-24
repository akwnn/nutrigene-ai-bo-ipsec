# Project Understanding Outline

## From a laboratory formulation problem to a computational benchmark and a paper

**Purpose.** This is the orientation document to read before drafting the manuscript. It explains what the project represents, what was implemented, how the synthetic data were constructed, why each cited paper is used, what the experiments actually show, and where the evidence stops. It is an outline of the whole project, not a manuscript draft and not a claim that wet-lab validation has occurred.

> **Central thesis:** A matched number of wells does not, by itself, define a fair BO-versus-RSM comparison. The apparent winner also depends on the final selection rule, confirmation protocol, permitted extrapolation, and whether cost is counted in wells or experimental rounds.

## How to use this guide

- **Understand the project:** Sections 1–6 explain the biological problem, cited literature, synthetic data, and code architecture.
- **Prepare the manuscript:** Sections 7–15 provide terminology, Methods, Results, figures, claims, Discussion, and reviewer risks.
- **Check publication readiness:** Sections 16–18 list unresolved work, project-owner decisions, references, and artifact provenance.

## Quick navigation

1. [Project explanation](#1-project-explanation-for-biology-researchers)
2. [Biological motivation](#2-biological-motivation-and-laboratory-translation)
3. [Research framing](#3-research-framing)
4. [Citation-purpose map](#4-what-was-cited-and-why)
5. [Synthetic-data construction](#5-how-the-synthetic-data-were-made)
6. [Code and experiment architecture](#6-core-project-architecture)
7. [Biology-first glossary](#7-concept-glossary-biology-first-formal-meaning-second)
8. [Methods outline](#8-manuscript-ready-methods-outline)
9. [Results storyline](#9-results-storyline-organized-by-laboratory-questions)
10. [Figure plan](#10-three-figure-main-paper-storyline)
11. [Ranked results](#11-ranked-result-inventory)
12. [Claims and boundaries](#12-claims-and-boundaries)
13. [Discussion outline](#13-biology-focused-discussion-outline)
14. [Reviewer risks](#14-reviewer-risk-audit)
15. [Manuscript structure](#15-recommended-manuscript-outline)
16. [Readiness and unresolved work](#16-current-readiness-and-unresolved-work)
17. [Questions for the project owner](#17-highest-value-questions-for-the-project-owner)
18. [References and evidence trail](#18-primary-references-and-project-evidence-trail)

**Evidence labels used throughout**

- **Source-verified:** checked against a cited paper or primary documentation.
- **Artifact-derived:** calculated from committed code, data, or result files in this repository.
- **Project choice:** invented or selected for this benchmark; not a fact about biology.
- **Interpretation:** a reasoned explanation of an artifact-derived result.
- **Unresolved:** missing, internally inconsistent, or not yet independently verified.

---

# 1. Project explanation for biology researchers

## 1.1 The project in a few sentences

**For a biology researcher.** Imagine optimizing a cell-culture medium or extracellular-matrix coating when only 48 wells are available. One strategy plans a screening and response-surface experiment in advance; another uses results from earlier wells to decide which formulations to test next. This project simulates those campaigns and shows that the apparent winner can change depending on how the laboratory chooses the final formulation: the highest single assay reading, the best condition after confirmation, or a point recommended by a fitted model.

**For a computational researcher.** This is a paired, matched-budget benchmark of batch Bayesian optimization (BO) and classical design of experiments/response-surface methodology (DoE/RSM) on constructed six- and eight-dimensional Hill-like landscapes. It separates sampling design, surrogate class, and terminal locator; distinguishes search from identification; evaluates wells and sequential rounds separately; and extends the evaluation from a single optimum to design-space mapping.

**One-sentence thesis.** A matched number of evaluations does not define a unique BO-versus-RSM comparison, because the terminal decision rule, permitted extrapolation, confirmation procedure, and unit of cost can materially change the conclusion.

**Laboratory problem represented.** A researcher must use a limited number of wells and plate cycles to choose either one multi-factor formulation for follow-up or a reliable region of acceptable formulations despite noisy measurements.

**What the codebase does.** It generates known synthetic response landscapes, runs multiple experimental-design procedures against identical landscapes and budgets, applies different final selection rules to the same campaigns, and scores the choices against hidden ground truth.

**What the project does not claim.** It does not demonstrate that either method improves endothelial differentiation, cell-culture media, or any real assay; it does not fit a six-dimensional biological response from Hall et al.; and its Gaussian noise, factor labels, and interaction magnitudes must not be presented as validated cellular biology.

## 1.2 Central concepts at first use

### Bayesian optimization

**Plain-language meaning:** An adaptive experimental strategy that learns from completed measurements and uses a model to choose the next promising conditions.

**Laboratory analogy:** Run an opening plate, fit a provisional map of assay response, then choose the next four wells because they are predicted to be good or informative.

**Why it matters in this project:** BO spreads its 48 wells across about ten decision rounds. It may use wells efficiently, but it requires repeated plate-to-model-to-plate cycles.

**Formal definition:** Sequential optimization of an expensive black-box function using a probabilistic surrogate and an acquisition function to select new query points.

### Design of experiments and response-surface methodology

**Plain-language meaning:** DoE chooses an organized set of factor combinations; RSM fits a low-order mathematical surface to those results and uses it to guide optimization.

**Laboratory analogy:** First screen six ingredients to retain four, then run a central composite design around the promising region, fit a quadratic surface, and test its proposed optimum.

**Why it matters in this project:** The classical comparator is a concrete 20 + 27 + 1 well workflow, not a generic label. Its fairness depends on how its fitted quadratic is interpreted when it is a saddle or points outside the fitted region.

**Formal definition:** DoE is planned selection of experimental inputs for estimable effects; RSM models a response, commonly with a second-order polynomial, and uses canonical, ridge, or sequential analyses to locate improving regions.

### Terminal decision rule

**Plain-language meaning:** The rule used after the experimental budget is spent to choose the formulation that will be carried forward.

**Laboratory analogy:** The final choice might be the well with the highest reading, the best of three confirmed candidates, or a formulation predicted by a fitted model.

**Why it matters in this project:** The same stored campaigns favor DoE under a single noisy-readout choice, favor BO under a naïve unconstrained model choice, and are largely tied under in-region or top-three-confirmation choices.

**Formal definition:** A mapping $L(D,M)\rightarrow \hat{x}$ from observed data $D$, and optionally fitted model $M$, to the final recommended input $\hat{x}$.

---

# 2. Biological motivation and laboratory translation

## 2.1 Laboratory workflow represented

1. **Choose factors.** Biologically, these could be medium components, ECM proteins, cytokines, or process variables. Computationally, a recipe is a vector $x\in[0,1]^d$. The code uses six or eight coded coordinates, not executable protein concentrations.
2. **Limit the combinations.** A full grid grows exponentially: five levels for six factors require $5^6=15{,}625$ conditions. The benchmark fixes the principal budget at 48 evaluations.
3. **Spend wells and rounds.** Each evaluated point is treated as one well-equivalent condition. A round is a batch chosen before observing that batch; it represents a plate cycle or decision cycle, not necessarily one physical plate in every laboratory.
4. **Observe an assay.** A hidden deterministic function supplies the underlying response, and simulated error changes the measured response. This is a simplified assay model, without explicit donors, batches, plate positions, failed wells, or cell-state drift.
5. **Adapt or follow a plan.** BO uses earlier measurements to choose later points. The two-stage classical workflow follows a screen with a central composite design. Space-filling controls distribute wells without adapting.
6. **Choose a deliverable.** The laboratory may want one recipe or an operating region where many recipes exceed a threshold. These are different scientific products and require different metrics.
7. **Make the final decision.** A single high reading, a model peak, a posterior mean, or confirmation can nominate different recipes from exactly the same measurements.

## 2.2 Translation table

| Laboratory concept | Computational representation | Implemented? | Important limitation |
|---|---|---:|---|
| Biological formulation | Point $x$ in a coded $[0,1]^d$ space | Yes | Coordinates are nominal; no validated concentration mapping |
| Assay result | Observed response $y$ | Yes | Abstract simulated readout, not a named assay unit |
| True biological response | Latent function $f(x)$ | Yes, synthetically | Known only because the landscape is constructed |
| Assay variability | Multiplicative and additive Gaussian error | Yes | Does not separate biological, technical, batch, or plate-position variance |
| Experimental condition | One function evaluation or well-equivalent | Yes | Replicate structure is not biological replication |
| Plate cycle | Batch/experimental round | Yes | Calendar duration and physical plate layout are not modeled |
| Carry-forward formulation | Terminal recommendation $\hat{x}$ | Yes | Several incompatible rules are compared |
| Acceptable formulation range | Thresholded design space $\{x:f(x)\ge\tau\}$ | Yes, extension | Certificate behavior is family-dependent and incompletely validated |
| Reagent and labor burden | No direct representation | No | Wells and rounds are only proxies |
| Donor/batch effects | Hierarchical or blocked noise | No | Limits biological realism |
| Missing/failed wells | Missing observations | No | Every scheduled synthetic evaluation returns a value |

## 2.3 What is realistic and what is simplified

The realistic structure is the decision problem: multiple continuous factors, too few wells for a full grid, noisy readouts, staged experiments, and a required final carry-forward decision. The mathematical landscape has biologically familiar rise-and-fall dose responses and sparse important factors. The numerical parameter ranges, interaction magnitudes, noise distribution, and acceptance rules are project-authored choices. The benchmark therefore tests decision procedures under controlled conditions; it does not estimate the behavior of a real cell system.

---

# 3. Research framing

## 3.1 Problem, questions, and hypothesis

**Biological problem.** A formulation campaign must turn a small, noisy collection of wells into a defensible next condition or operating range.

**Computational problem.** Compare adaptive BO with structured DoE/RSM while holding the hidden landscape and evaluation budget fixed, then determine which part of the result comes from sampling, modeling, final selection, or scoring.

**Why it matters experimentally.** A method that samples useful conditions but identifies the wrong one after a noisy readout may fail at handoff. Conversely, a method that proposes a mathematically impressive point outside the region it learned may fail on confirmation. Well count alone also hides the cost of waiting for repeated adaptive rounds.

**Why a naïve comparison is misleading.** “BO” and “RSM” each describe families of workflows. Studies differ in factor screening, budgets, acquisition functions, model classes, final recommendations, confirmation, and whether cost means conditions or rounds. Changing any of these can change the estimand.

**Main research question.** Under identical 48-well campaigns on the same constructed landscapes, does the BO-versus-DoE conclusion depend on how the final formulation is selected?

**Secondary questions.** How much of a difference is search versus identification? Does a quadratic fail because of its sampling design, surrogate class, or locator? What changes with assay noise, nuisance dimensions, sequential relocation, one-shot designs, other landscape families, and design-space rather than point optimization?

**Central hypothesis.** Method ranking is conditional on the terminal rule: single-readout selection, unconstrained model extrapolation, in-region recommendation, and confirmation need not produce the same winner.

**Practical question for a biology reader.** Given the laboratory's true carry-forward protocol and cost structure, which experimental workflow should be compared—and what evidence is needed before trusting its recommendation?

## 3.2 Novelty audit

| Proposed claim | Already established? | Evidence here | Safe biology-friendly framing |
|---|---|---|---|
| BO can optimize biological formulations | Yes | Context only | BO is an established adaptive strategy in media and culture optimization |
| BO-versus-DoE comparisons exist | Yes | Rummukainen, Lapierre, Ndahiro | This project standardizes budget and landscape to isolate comparison choices |
| Synthetic optimizer benchmarks exist | Yes | Context only | The contribution is the factorial interpretation, not the existence of a benchmark |
| Best measured point differs from model recommendation | Conceptually yes | Explicit same-campaign re-scoring | The potentially new result is a winner reversal on identical campaigns |
| Sampling design, surrogate, and locator can be separated | Components known | Q34/Q45/Q35 factorial decomposition | The project quantifies their separate contributions within one matched benchmark |
| A single noisy readout can confound search and identification | Known statistical issue | Q55/Q57 quantify 55–73% | The contribution is a paired decomposition of the observed method gap |
| Confirmation can change the ranking | Plausible, not broadly novel alone | Q58: primary gap becomes null | A laboratory-plausible three-candidate confirmation removes this benchmark's lead |
| One recipe and a design space are different deliverables | Established in quality-by-design | K6/P6–P8 show rank reordering | Scoring an operating region can reverse arm-level conclusions from point regret |
| SPADE is a generally superior design-space method | Not supported | Prospective study has failed and unrun kills | SPADE is an exploratory two-round protocol with a narrowed, family-specific claim |

---

# 4. What was cited, and why

This section is the citation-purpose map. A paper should be cited only for the role listed here; contextual precedent must not be turned into evidence for this project's result.

| Source | What it establishes | Why this project cites it | What it must not be used to claim |
|---|---|---|---|
| **Hall, Lin & Ogle (2025), Scientific Reports, DOI 10.1038/s41598-025-09256-9** | Six-factor ECM screen followed by four-factor on-face central composite design for iPSC-to-endothelial differentiation; CD31/DAPI readout; fitted model overpredicted a nominated optimum | Structural biological inspiration for factor count, 6→4 screening, the project's staged budget logic, and a real confirmation failure; source of digitized auxiliary data | That the synthetic Hill surface was fitted to their data, that its parameters are protein-specific, or that the project's exact 20+27+1 split is a source-verified Hall run count |
| **Box & Wilson (1951)** and **Box & Draper / Myers et al.** | Foundations and standard practice of sequential RSM, steepest ascent, canonical and ridge analysis | Defines a fair classical comparator and supports the warning that an unconstrained saddle peak is not proper RSM | That every modern DoE implementation must use one exact pipeline |
| **Jones, Schonlau & Welch (1998)** | Efficient global optimization and expected improvement | Foundational reference for EI-based BO | Evidence that EI is superior in this biological problem |
| **Frazier (2018)** | Tutorial treatment of BO, Gaussian processes, and acquisition functions | Accessible formal background | Empirical support for this project's numerical conclusions |
| **Rummukainen et al. (2024), Heliyon, DOI 10.1016/j.heliyon.2024.e24484** | Executed equal-budget pilot comparison: 15 Box–Behnken versus 5+10 adaptive BO experiments; no experiment-count reduction | Closest precedent for a matched-budget executed BO-versus-DoE comparison and for noisy EI/posterior-mean selection | A general proof that BO never saves experiments |
| **Narayanan et al. (2025), Nature Communications, DOI 10.1038/s41467-025-61113-5** | BO-guided cell-culture media development and large reported experiment reductions relative to predicted/conventional DoE requirements | Shows practical biological relevance and why “fewer experiments” is an important claim | An executed equal-budget DoE defeat; its denominator is not the same estimand as this benchmark |
| **Lapierre et al. (2025), JCTB, DOI 10.1002/jctb.7860** | Multi-cycle batch BO for microbial growth-media optimization compared with a CCD/RSM workflow after screening | Executed media precedent and example of whole-workflow comparisons | That sampling design, factor set, model, and terminal rule were independently randomized |
| **Ndahiro et al. (2025), iScience, DOI 10.1016/j.isci.2025.112944** | Mammalian biomanufacturing media BO with thermodynamic constraints and equal-count comparison | Demonstrates real wet-lab, constraint-aware BO relevance | That this unconstrained synthetic benchmark includes solution thermodynamics |
| **Gisperg et al. (2025), Biotechnology and Bioengineering** | Review of BO in bioprocess engineering | Field context and vocabulary | Primary evidence for a result originally reported by Rummukainen or another study |
| **Kanda et al. (2022), eLife, DOI 10.7554/eLife.77007** | Robotic search of an enormous cell-culture condition space | Concrete example of the scale and logistical value of adaptive experimentation | A direct BO-versus-RSM comparator for this project |
| **Gneiting & Raftery (2007)** | Proper scoring rules and probabilistic forecast evaluation | Basis for calibration-oriented design-space metrics | Proof that this project's certificate is calibrated |

**Citation cautions already discovered.** Picheny (2013) was not verified as support for the project's search-versus-identification distinction. Nguyen et al. (2017) discusses an incumbent inside acquisition computation, not the final laboratory recommendation, and should not be described as a contrary terminal-selection result. The Collagen IV high concentration in Hall et al. is internally inconsistent between Results and Methods; do not assert whether the nominated optimum exceeded that tested range. The repository's source audit also leaves the exact 23-run/25-run/~48-condition reconciliation unresolved, so present 20+27+1 as the benchmark's matched-budget implementation rather than an exact published count unless the source tables are reconciled.

---

# 5. How the synthetic data were made

## 5.1 The essential answer

No synthetic table was generated by fitting Hall et al.'s measurements. Instead, the code first constructs a hidden mathematical response surface $f(x)$, then lets every experimental method choose coordinates $x$, and finally generates an assay-like reading $y$ by perturbing $f(x)$ with random error. Because the true surface is known, the project can score whether the formulation selected by a noisy campaign is genuinely close to the hidden optimum.

## 5.2 Step-by-step construction of the primary Hill benchmark

1. **Create a coded factor space.** Use $d=6$ or $d=8$ continuous coordinates scaled to $[0,1]$. These do not carry physical units.
2. **Choose important factors.** Randomly select four active coordinates at both dimensions. They carry 90% of the total response weight; the remaining two or four coordinates carry 10% and act as nuisance factors. This isolates the difficulty of identifying important variables as dimension grows.
3. **Draw a preferred level for each factor.** Candidate factor peaks are drawn from $x_i^*\sim U(0.25,0.55)$, subject to later feasibility and acceptance filtering. The accepted ensemble is therefore not exactly uniform; its reported mean is about 0.340.
4. **Draw Hill steepness.** Draw $n_i\sim U(1,3)$, again subject to filtering. These values control how sharply the response rises and falls.
5. **Construct a biphasic factor response.** For factor $i$, combine an activating Hill term and an inhibitory Hill term:

   $$
   h_i(x_i)=\frac{x_i^{n_i}}{\mathrm{EC}_{50,i}^{n_i}+x_i^{n_i}},
   \qquad
   g_i(x_i)=\frac{1}{1+\left(x_i/\mathrm{IC}_{50,i}\right)^{n_i}}.
   $$

   Their peak occurs exactly at $x_i^*=\sqrt{\mathrm{EC}_{50,i}\mathrm{IC}_{50,i}}$. The product is normalized so its peak equals one.
6. **Set the width of the useful window.** The ratio $r_i=\mathrm{IC}_{50,i}/\mathrm{EC}_{50,i}$ is obtained by inverting a chosen depth parameter, then clipped to $[2,8]$. This controls how broad the rise-and-fall response is.
7. **Weight the factors.** Random positive weights are normalized so the four active factors account for 0.90 of total weight and the inactive factors for 0.10.
8. **Add sparse interactions.** Roughly $\lceil d/2\rceil$ factor pairs receive peak-modulation coefficients drawn from $U(-1,1)$. These interactions shift conditional peak locations. The mechanism is plausible as a generic representation of interacting ingredients; its numeric magnitude is a project choice.
9. **Find the actual multivariate optimum.** Numerical optimization accounts for the interactions; the vector of marginal peaks alone is not assumed to be the final optimum.
10. **Accept only sufficiently identifiable landscapes.** Stored v8 ensemble sidecars have true optimum-to-active-boundary depth at least about 0.1083, chosen as $3(0.25)/\sqrt{48}$. This avoids benchmarks whose optimum is indistinguishable from a boundary at the primary noise/budget scale. Rejection and factor-level resampling alter the nominal parameter distributions and must be disclosed.
11. **Freeze the landscape ensemble.** The main factorial uses 25 landscapes per dimension, although the committed ensemble contains additional instances for other experiments. Each landscape is evaluated with two algorithmic seeds; those two runs are averaged before inference.
12. **Generate observations only when a method evaluates a point.** The observation model is

   $$
   y=f(x)(1+\epsilon)+\eta,
   \qquad
   \epsilon\sim\mathcal{N}\!\left(0,\sigma_{\mathrm{rel}}^2\right),
   \qquad
   \eta\sim\mathcal{N}\!\left(0,0.01^2\right).
   $$

   with $\sigma_{\mathrm{rel}}=0.25$ as the higher-noise primary condition and 0.10 as a lower-noise sensitivity condition.
13. **Give the GP an observation-variance estimate without revealing truth.** The plug-in variance is $y^2\sigma_{\mathrm{rel}}^2+0.01^2$, floored at the additive term. It uses observed $y$, not hidden $f(x)$.
14. **Score recommendations using the hidden surface.** A selected recipe is evaluated noiselessly against the known global maximum. This is possible only in simulation.

### Symbol key for the benchmark equations

| Symbol | Meaning in the model | Laboratory interpretation |
|---|---|---|
| $x_i$ | Coded level of factor $i$ | Concentration setting for one formulation component |
| $n_i$ | Hill exponent | Steepness of the factor's rise-and-fall response |
| $\mathrm{EC}_{50,i}$ | Half-activation scale | Level at which activation becomes substantial |
| $\mathrm{IC}_{50,i}$ | Half-inhibition scale | Level at which inhibition becomes substantial |
| $f(x)$ | Noise-free latent response | Repeat-average performance of formulation $x$ in the simulator |
| $y$ | Observed response | One assay-like measurement |
| $\epsilon$ | Relative random error | Variation proportional to response magnitude |
| $\eta$ | Additive random error | Baseline measurement noise |
| $\sigma_{\mathrm{rel}}$ | Relative-noise standard deviation | Higher- or lower-noise benchmark setting |

## 5.3 Evidence classification for every synthetic ingredient

| Component | Value | Evidence status | Interpretation limit |
|---|---:|---|---|
| Six factors, then four retained | 6→4 | Structurally inspired by Hall et al. | Does not assign Hall's protein identities to coded axes |
| Eight-factor condition | 8→4 active plus nuisance factors | Project choice | Tests dimension/nuisance burden, not a published eight-factor assay |
| Biphasic Hill form | Activating × inhibitory Hill response | Standard functional family | Generic biological shape, not an estimated mechanism |
| Peak range | $U(0.25,0.55)$ before filtering | Project choice | Accepted distribution is truncated |
| Hill exponent | $U(1,3)$ before filtering | Project choice | Not fitted to dose-response data |
| Active share | Four factors carry 90% | Project choice | Sparse importance is planted |
| Interaction coefficients | $U(-1,1)$ on sparse pairs | Project choice | Signs and magnitudes are not biological estimates |
| Relative noise | 0.25 and 0.10 | Project choice | Must be called benchmark noise, not realistic assay CV |
| Additive noise | 0.01 | Project choice | Avoids zero variance near zero response |
| Depth threshold | Stored ensemble approximately ≥0.1083 | Project choice tied to budget/noise | Selects easier-to-identify interior optima |
| Replication | 25 landscapes × 2 algorithmic seeds | Benchmark replication | Not biological or technical replicate wells |

## 5.4 Important implementation inconsistency to resolve

The committed v8 ensemble sidecars and `docs/oracle_defensibility.md` describe a true-depth threshold of approximately 0.1083. The current `SamplerConfig` default in `src/boec/oracles.py` is `accept_floor = 0.045`, while retaining `formula_prefloor = 0.120`. This does not change already stored landscapes, whose sidecars show minima near 0.1086–0.1111, but it means regenerating from current defaults may not reproduce the documented ensemble-selection rule. Before publication, either restore the generation default used for the committed ensemble or document the exact generation configuration outside the mutable default and add a reproducibility test.

## 5.5 Real data in the repository

- **Digitized Hall/Ogle data:** 47 condition medians from published figures are used only in auxiliary analyses. They do not identify a six-dimensional latent surface, and a replay analysis is underpowered (reported minimum detectable effect 0.68).
- **In-house flow-cytometry files:** present but not optimizer-ready; unsigned CD31 percentages are excluded pending biological sign-off. They do not support the paper's computational conclusions.
- **Therefore:** the main results are synthetic. Published data provide motivation and limited plausibility checks, not validation.

---

# 6. Core project architecture

## 6.1 End-to-end flow

Biological question
→ coded formulation space
→ constructed latent response
→ noisy assay-like observation
→ experimental procedure
→ fitted surrogate/response surface
→ terminal selection rule
→ regret or design-space metric
→ paired statistical comparison
→ scoped laboratory interpretation.

## 6.2 Component map

| Project component | Biology translation | Computational operation | Output | Likely paper section |
|---|---|---|---|---|
| Landscape generator | Unknown formulation-response biology | Sample and accept Hill-like functions | Frozen oracle instances and sidecars | Methods: benchmark |
| `src/boec/torch_oracle.py` | Assay instrument interface | Return noisy $y$ and variance estimate | Observation tensors | Methods: response/noise |
| `src/boec/campaign.py` | Adaptive plate campaign | Opening design, model fit, batched proposals, checkpoints | Visited points and observations | Methods: BO |
| `src/boec/optimizers.py` and surrogate modules | Provisional response map | GP fitting and qLogEI/qLogNEI acquisition | Proposed batch/model posterior | Methods: BO |
| `src/boec/doe.py` | Screen, optimize, confirm | Resolution-IV screen, four-factor CCD, quadratic, confirmation | 48-well DoE campaign | Methods: classical arm |
| `src/boec/rsm.py` | Fitted classical response map | Second-order regression, stationary/ridge handling | Model recommendation/diagnostics | Methods: RSM |
| Space-filling designs | Nonadaptive broad sampling | LHS, Sobol', random designs | One-shot 48-point campaigns | Controls |
| Diagnostic locators | Different carry-forward rules | Noisy argmax, tested-best, model maximum, ridge, confirmation | Final $\hat{x}$ | Methods: terminal rules |
| `src/boec/metrics.py`, diagnostics | Distance from true best | Regret, identification gap, overprediction | Per-campaign scores | Outcomes |
| `src/boec/designspace.py`, `vorobev.py`, `versionc.py`, `final_spade.py` | Map acceptable operating region | Threshold exceedance maps and certificates | AUC, symmetric difference, containment/refinement | Separate design-space section/paper |
| `scripts/run_*.py` | Registered analyses | Execute experiments and write artifacts | JSON/CSV/log result files | Reproducibility |
| `docs/OPEN-QUESTIONS.md`, specs | Preregistration/decision history | Lock questions, bars, and interpretations | Audit trail | Supplement |

## 6.3 Repository reading order

1. Read this document for the project model.
2. Read `docs/RESEARCH-SUMMARY.md` for the current manuscript-scale argument and numerical results.
3. Read `docs/oracle_defensibility.md` for the synthetic construction and biological provenance.
4. Read `docs/METHODS.md` and the configuration files for implementation detail.
5. Read `docs/CLAIMS.md` with caution: it records corrections and historical claims, so later corrections take precedence.
6. Read `docs/FINDINGS-SPADE-FINAL.md` and `docs/SPADE-SPEC.md` separately from the point-optimization story.
7. Use result JSON/CSV files as the numerical source of truth and scripts/tests as the computational source of truth.

## 6.4 Scientific work program behind the paper

The repository contains many internal experiment identifiers. They are audit labels, not separate manuscript contributions. The paper should group them by the biological question they answer.

| Internal work | What was done | Scientific purpose | Status in paper |
|---|---|---|---|
| **E2** | Ran matched 48-well BO and staged DoE campaigns on the four d×noise cells | Establish the primary comparison under measured-value selection | Core confirmatory dataset |
| **E4 and related diagnostics** | Measured extrapolation, overprediction, discrimination, coverage, and oracle depth | Test whether model confidence or geometry warns about unsupported recommendations | Supporting diagnostic |
| **Q34 / Q35 / Q45** | Re-scored terminal locators and crossed DoE/BO sampling points with polynomial/GP models | Separate design, surrogate, and locator effects | Core mechanistic contribution |
| **Q42** | Repeated the comparison on Levy, Rosenbrock, Hartmann6, and Ackley families | Test whether the Hill result is landscape-specific | Robustness/exploratory |
| **Q52–Q54** | Compared one-shot spread designs and repeated over five design draws | Ask whether adaptivity itself earns its extra rounds | Secondary |
| **Q55 / Q57** | Stored hidden tested-best for both arms and added qLogNEI | Separate search from identification and use a noise-aware acquisition | Core secondary/co-primary |
| **Q56** | Extended d=6 to 200 wells with relocating sequential RSM | Make the long-run cost comparator fair | Core cost analysis |
| **Q58** | Replayed fixed campaigns under replicate, top-three-confirmation, and posterior-mean picks | Test laboratory selection sensitivity | Core secondary result |
| **Q59** | Turned off screening where arithmetically feasible | Test whether screening explains point or map results | Robustness; replay currently needs resolution |
| **K6 / P6–P8** | Re-scored stored campaigns as threshold-defined design-space maps and certificates | Contrast one best recipe with an acceptable operating region | Separate extension |
| **Version C / final SPADE** | Registered and ran a prospective two-plate method study across seven conditions | Test SPADE as a method rather than a retrospective score | Narrowed/unfinished extension |

The logic is therefore: establish the reversal → explain it → make both comparators fairer → test alternative laboratory decisions → test other landscapes → only then change the deliverable from a point to a map.

---

# 7. Concept glossary: biology first, formal meaning second

The entries below deliberately connect each computational term to a laboratory decision. Confusing the terms changes what the results mean.

### Surrogate model

**Plain-language meaning:** A mathematical approximation of the response across tested and untested formulations.

**Laboratory analogy:** A contour plot fitted from a limited plate, used to estimate what might happen between measured wells.

**Why it matters in this project:** A method can look good because of where it samples or because of what model is fitted afterward; Q34/Q45 separates those effects.

**Formal definition:** A fitted function or probability distribution $M$ approximating an expensive latent function $f$ from data $D=\{(x_i,y_i)\}$.

### Gaussian process

**Plain-language meaning:** A surrogate that gives both a predicted mean response and uncertainty at each formulation.

**Laboratory analogy:** A response map whose shading becomes more uncertain far from measured wells.

**Why it matters in this project:** BO uses the GP's uncertainty to decide where to test, and model-based terminal rules use its posterior mean to recommend a formulation.

**Formal definition:** A probability distribution over functions such that finite collections of function values are jointly Gaussian; conditioning on data yields posterior mean $\mu(x)$ and covariance $k_D(x,x')$.

### Acquisition function

**Plain-language meaning:** A numerical priority score for deciding which untested formulation to measure next.

**Laboratory analogy:** A plate-planning rule balancing a condition that already looks promising with one that could teach the model something important.

**Why it matters in this project:** It defines the adaptive sampling behavior but not the final carry-forward rule. Conflating those two rules causes incorrect claims.

**Formal definition:** A function $a(x;D)$ of the surrogate posterior whose maximizer supplies the next query or batch.

### Expected improvement and noisy expected improvement

**Plain-language meaning:** Expected improvement (EI) prioritizes conditions expected to improve on the current reference; noisy EI accounts for uncertainty about which earlier condition is truly best.

**Laboratory analogy:** EI asks which next well is most likely to beat the incumbent. Noisy EI acknowledges that the incumbent itself may owe its rank to assay noise.

**Why it matters in this project:** qLogEI is the named BO arm and qLogNEI is co-primary under noise. qLogNEI improves identification but does not remove the higher-noise DoE lead under single-readout selection.

**Formal definition:** $\operatorname{EI}(x)=\mathbb{E}\!\left[(f(x)-f_{\mathrm{best}})_+\right]$. NEI integrates improvement over the posterior uncertainty in latent values at observed and candidate points. `qLog` denotes a numerically stable logarithmic batch implementation.

### Latent response and observation noise

**Plain-language meaning:** The latent response is the underlying repeat-average performance of a formulation; observation noise is the variation in an individual measured assay value around it.

**Laboratory analogy:** $f(x)$ is the response expected over ideal repeated assays, while $y$ is what one particular well reports.

**Why it matters in this project:** Algorithms see $y$, but simulation can score against $f$. The Gaussian perturbation is not evidence about real biological variability.

**Formal definition:** $y=f(x)(1+\epsilon)+\eta$, with independent Gaussian relative and additive errors in this benchmark.

### Simple regret and cumulative regret

**Plain-language meaning:** Simple regret asks how far the final selected formulation is from the best possible formulation. Cumulative regret asks how much performance was lost across all wells along the way.

**Laboratory analogy:** Simple regret evaluates the recipe carried forward; cumulative regret would penalize every suboptimal culture used during learning.

**Why it matters in this project:** The project is primarily about a final recipe or map, so simple regret is the point-optimization outcome. Cumulative regret is not a headline outcome and should not be introduced as if analyzed.

**Formal definition:** For maximization, simple regret is

$$
r=f(x^*)-f(\hat{x}).
$$

When $f(x^*)=1$, this becomes $r=1-f(\hat{x})$. Cumulative regret through $T$ is

$$
R_T=\sum_{t=1}^{T}\left[f(x^*)-f(x_t)\right].
$$

### Search quality and identification error

**Plain-language meaning:** Search quality asks whether the campaign physically tested a good formulation. Identification error asks whether the end-of-campaign rule correctly recognized that good formulation.

**Laboratory analogy:** A plate may contain an excellent well, yet a noisier neighbor may have the highest measured signal and be carried forward instead.

**Why it matters in this project:** Roughly 55–73% of the higher-noise measured-value gap is attributed to identification rather than where the procedures searched.

**Formal definition:** Search regret is

$$
r_{\mathrm{search}}=f(x^*)-\max_{x_i\in D}f(x_i).
$$

Identification error is $f(x_{\mathrm{tested\text{-}best}})-f(\hat{x}_{\mathrm{selected}})$, equivalently measured-selection regret minus search regret.

### Hidden tested-best

**Plain-language meaning:** The truly best condition among all wells that were physically tested, known only to the simulator.

**Laboratory analogy:** The well a laboratory would have chosen if it knew every condition's noise-free repeat-average response.

**Why it matters in this project:** It isolates search from recognition but is not an implementable laboratory rule.

**Formal definition:** $\displaystyle \arg\max_{x_i\in D}f(x_i)$, scored with latent $f$.

### Measured-value argmax

**Plain-language meaning:** Choose the tested well with the highest observed assay value.

**Laboratory analogy:** Rank one plate by a single fluorescence or titer reading and carry forward the top well without confirmation.

**Why it matters in this project:** It is the stored E2 primary “best observed” rule and favors DoE at higher noise. It evaluates search plus identification, not search alone.

**Formal definition:** $\displaystyle \hat{x}=x_{\arg\max_i y_i}$, then score $f(\hat{x})$.

### Model, posterior-mean, and visited-point recommendations

**Plain-language meaning:** A model recommendation chooses a formulation because a fitted surface predicts it will perform well; a posterior-mean-at-visited rule restricts this choice to formulations already tested.

**Laboratory analogy:** Trust the contour-map maximum anywhere in the allowed recipe box, or use the model only to re-rank wells that were actually run.

**Why it matters in this project:** These rules answer a different question from choosing the largest assay reading and can reverse or erase the ranking.

**Formal definition:** Continuous model recommendation $\displaystyle \hat{x}=\arg\max_{x\in\mathcal X}\hat f(x)$; visited posterior-mean recommendation $\displaystyle \hat{x}=\arg\max_{x_i\in D}\mu(x_i)$.

### Unconstrained versus in-region/ridge recommendation

**Plain-language meaning:** An unconstrained rule allows the fitted model to recommend any point in the global factor box. An in-region or ridge rule limits the recommendation to a region supported by the experimental design and follows improving paths when no fitted interior maximum exists.

**Laboratory analogy:** Extrapolate a quadratic from a small local plate to an untested corner, versus remain within the region actually mapped or deliberately relocate the design.

**Why it matters in this project:** The apparent 0.27–0.36 BO advantage is mostly an invalid-saddle/extrapolation diagnostic. With an in-region rule, three of four cells are null.

**Formal definition:** Unconstrained $\displaystyle \arg\max_{x\in[0,1]^d}\hat f(x)$; constrained/ridge optimization over a learned design region or fixed-radius path using canonical RSM analysis.

### Confirmation protocol

**Plain-language meaning:** Additional measurements used to choose among shortlisted formulations before commitment.

**Laboratory analogy:** Re-run the three highest-ranked candidate recipes on new wells and choose using the confirmation readings.

**Why it matters in this project:** Adding three confirmation wells changes the primary DoE-minus-BO contrast from −0.0595 to −0.0009, a null result under the registered test.

**Formal definition:** A terminal policy that allocates additional evaluations to candidates selected from the completed campaign and maps their new observations to $\hat{x}$.

### Screening

**Plain-language meaning:** A first-stage experiment used to decide which factors appear important enough for detailed optimization.

**Laboratory analogy:** Test six ECM components in a fractional factorial pattern, retain four, and hold the others at selected levels.

**Why it matters in this project:** Screening concentrates the later CCD but prevents the method from mapping dropped factors. On Hartmann6, removing the screen worsens point optimization, so it was helping rather than handicapping DoE there.

**Formal definition:** A designed experiment estimating main effects or low-order effects with fewer runs than a full factorial, followed by factor selection.

### Central composite design

**Plain-language meaning:** A structured set of center, factorial/face, and axial-like points used to fit curvature.

**Laboratory analogy:** Arrange wells at deliberate combinations around a promising center so a quadratic response surface can be estimated.

**Why it matters in this project:** The four-factor face-centered CCD uses 27 wells in stage 2 and defines the region in which the quadratic has direct support.

**Formal definition:** A second-order response-surface design combining factorial or fractional-factorial points, axial points, and center replicates.

### Steepest ascent and sequential relocation

**Plain-language meaning:** Move the next experimental region in the direction where the current fitted model predicts improvement, then fit again.

**Laboratory analogy:** Rather than repeat the same plate around the old center, shift the next plate toward the most promising concentration direction.

**Why it matters in this project:** The long-run fair classical arm uses screen → CCD → steepest ascent → recentering. Under measured-value arrival it matches qLogEI, eliminating the earlier well-saving claim.

**Formal definition:** Sequential RSM follows the gradient of a first- or second-order fitted model until improvement stops, then relocates the design and refits.

### Experimental budget, well count, and experimental-round count

**Plain-language meaning:** Budget is the resource cap; wells count physical conditions, whereas rounds count how many times results must be observed before choosing the next batch.

**Laboratory analogy:** Two methods may both consume 48 wells, but one needs one plate decision and another needs ten sequential plate cycles.

**Why it matters in this project:** At 48 wells, BO uses about ten rounds, DoE three stages/rounds, and one-shot GP one. A well-count claim is not a calendar-time claim.

**Formal definition:** Evaluation cost is $N=\lvert D\rvert$; round cost is the number of adaptive batches with points chosen jointly before observing that batch.

### D-efficiency

**Plain-language meaning:** How efficiently a design estimates model coefficients within the model and region it was built for.

**Laboratory analogy:** Whether the planned wells give a statistically well-spread basis for estimating a quadratic response surface.

**Why it matters in this project:** The CCD can be D-efficient in its own subregion even when its map of the entire global box is poor. D-efficiency is not optimization regret.

**Formal definition:** A determinant-based measure derived from the information matrix $X^{\mathsf T}X$, usually normalized relative to a reference design.

### Design space

**Plain-language meaning:** A region of formulations expected to meet a performance threshold, not one predicted best recipe.

**Laboratory analogy:** A robust operating window for ingredient concentrations that tolerates routine variation.

**Why it matters in this project:** A method can find a strong recipe yet map the acceptable region badly; the arm ranking changes when the deliverable changes.

**Formal definition:** $A_\tau=\{x\in\mathcal X:f(x)\ge\tau\}$, or a probabilistic/certified estimate of that excursion set.

### Calibration, refinement, and containment

**Plain-language meaning:** Calibration asks whether stated confidence is honest; refinement asks whether the certified region is usefully narrow rather than vague; containment asks whether the claimed region truly lies inside the acceptable region at the promised rate.

**Laboratory analogy:** If a method labels recipes “99% safe,” calibration checks whether that promise holds, refinement checks whether it certifies more than a tiny conservative patch, and containment checks how often its proposed window avoids bad formulations.

**Why it matters in this project:** SPADE is strong on map/refinement in the retrospective program but mid-field on calibration; high-confidence containment fails on Levy/Rosenbrock and is declined on Ackley/Hartmann6.

**Formal definition:** Calibration compares nominal and empirical probabilistic coverage; refinement measures sharpness or informativeness conditional on validity; containment evaluates $P(\hat A\subseteq A_\tau)$ or its finite-sample analogue.

### Synthetic benchmark and wet-lab validation

**Plain-language meaning:** A synthetic benchmark is a controlled simulated system with known truth. Wet-lab validation tests a preregistered method using actual biological samples and measurements.

**Laboratory analogy:** A flight simulator can compare pilot procedures under known conditions; it cannot prove that a new aircraft works until physical testing.

**Why it matters in this project:** Almost every strong numerical conclusion is about the benchmark. Digitized published plots are auxiliary, and in-house data are excluded.

**Formal definition:** A benchmark samples or fixes functions from a known generative family and evaluates algorithms against known targets; validation estimates performance prospectively in the intended empirical domain.

---

# 8. Manuscript-ready Methods outline

## 8.1 Biological scenario represented

- Frame the task as optimizing a multicomponent formulation under a limited well and round budget.
- State that Hall et al.'s six-factor ECM study supplies structural inspiration only: six factors, four retained after screening, a response-surface stage, and a tested prediction that underperformed.
- State immediately that the latent responses are constructed Hill-like functions and not fitted endothelial responses.
- Explain that coded axes could represent concentrations but are not mapped to Collagen I, Collagen IV, Laminin 411, fibronectin, or other physical ingredients.

## 8.2 Formulation space and oracle ensemble

- Analyze $d\in\{6,8\}$ on $[0,1]^d$.
- Hold the number of dominant factors at four in both dimensions; sample the active subset per landscape.
- Allocate 90% of total factor weight to active coordinates.
- Construct biphasic peak-normalized Hill factors and sparse peak-modulation interactions.
- Numerically locate each true optimum and accept landscapes with sufficient optimum-to-boundary depth.
- Freeze and version oracle instances, parameter sidecars, seeds, and audit summaries.
- Disclose acceptance-induced truncation and the current `accept_floor` reproducibility inconsistency.

## 8.3 Response and assay model

- Define latent $f(x)$, normalize its maximum to approximately one, and define observed $y=f(x)(1+\epsilon)+\eta$.
- Use $\sigma_{\mathrm{rel}}\in\{0.25,0.10\}$ and $\sigma_{\mathrm{add}}=0.01$.
- Call these higher- and lower-noise benchmark conditions.
- Do not label either as a biological coefficient of variation: the digitized Hall box plots combine several sources of variation and are not the same estimand.
- Explain the plug-in observation variance and that it avoids access to hidden truth.

## 8.4 Experimental procedures

| Procedure | Laboratory action | Implementation | Strength | Limitation |
|---|---|---|---|---|
| qLogEI BO | Run opening wells; iteratively choose batches of four | $n_0=2d+2$, then $q=4$ to $N=48$; GP plus qLogEI | Adaptive exploitation/exploration | ~10 rounds; EI does not define terminal selection |
| qLogNEI BO | Same, acknowledging incumbent uncertainty | Stored co-primary noisy acquisition | Better aligned with noisy observations | Still model- and prior-dependent |
| DoE/RSM | Screen, retain four, run CCD, fit quadratic, confirm | 20 screening wells + 27 CCD wells + 1 confirmation | Interpretable staged workflow; concentrated local design | Dropped-factor map loss; quadratic can be saddle/rank-deficient |
| Sequential RSM | Relocate after steepest ascent | Screen → CCD → ascent → recenter to N≤200 | Fair long-run classical comparator | Implemented only at d=6 cost curves |
| LHS/Sobol'/random | Spread all wells without learning between plates | One-shot space-filling designs | Broad coverage, one round | No adaptive targeting |
| One-shot GP | Spread wells once, then fit GP | Five LHS design draws analyzed | Separates adaptivity from flexible modeling | Performance depends on design draw and landscape smoothness |
| Crossed design/surrogate arms | Refit GP on DoE points or polynomial on BO points | Q34/Q45 factorial cells | Identifies mechanism | Diagnostic rather than a deployable protocol |

## 8.5 Terminal rules

| Terminal rule | Laboratory interpretation | What it measures | Main risk |
|---|---|---|---|
| Hidden tested-best | Omniscient best well on the plate | Search only | Impossible in a real lab |
| Measured-value argmax | Carry forward largest single reading | Search + noisy identification | Winner's curse/misidentification |
| Continuous model recommendation | Make the recipe maximizing fitted mean | Model-supported optimization | Model misspecification |
| Unconstrained quadratic/GP | Permit any point in global box | Extrapolative model performance | Unsupported boundary/corner recommendation |
| In-region/ridge | Restrict to learned region or canonical ridge path | Supported classical recommendation | May miss distant optimum |
| Replicate selection | Re-measure selected candidate(s) | Robustness to assay noise | Consumes extra wells; exact aggregation matters |
| Confirm top three | Re-run three candidates and decide from confirmation | Shortlist quality plus confirmation | This implementation discards original readings |
| Posterior mean at visited points | Model re-ranks tested wells | Denoised identification | Sensitive to model calibration |

The paper must define a primary terminal rule before interpreting a method comparison. “Best observed” is too ambiguous unless it says whether “best” means largest $y$ or largest hidden $f$ among visited points.

## 8.6 Outcomes

- **Point optimization:** simple regret of the selected formulation.
- **Search:** regret of the hidden tested-best condition.
- **Identification:** difference between selected-condition regret and tested-best regret.
- **Cost:** curves and hitting probabilities versus wells and versus rounds; calendar time, labor, and reagent costs are not directly modeled.
- **Model diagnostics:** saddle status, extrapolation distance, overprediction, rank, predictive coverage, and D-efficiency.
- **Design-space outcomes:** map AUC/symmetric difference, calibration, refinement, containment, and certificate behavior.

## 8.7 Replication and statistics

- The main 2×2 factorial is $d\in\{6,8\}\times\sigma\in\{0.25,0.10\}$.
- The registered primary cell is $d=6$, $\sigma=0.25$, $N=48$.
- Each cell uses 25 hidden landscapes and two algorithmic seeds per landscape. Average the two seeds first; inferential $n=25$, not 50.
- Pair procedures on the same landscape so landscape difficulty cancels in the contrast.
- Use the Wilcoxon signed-rank test to ask whether paired differences are systematically shifted without assuming normality.
- Use instance bootstrap intervals to quantify effect magnitude and uncertainty.
- “Null” means no demonstrated difference under the stated protocol/test. It does not prove equality; an equivalence claim needs a prespecified margin and test.
- Apply Holm correction to declared families of multiple comparisons; report effect and interval before p-value.

---

# 9. Results storyline organized by laboratory questions

## Question 1: Which procedure physically tests better conditions?

“Finds” must mean the hidden tested-best point, not the well with the largest noisy reading. At the primary $d=6$, $\sigma=0.25$ cell, hidden tested-best regret is 0.0597 for DoE, 0.0755 for qLogEI, and 0.0834 for qLogNEI. The DoE-minus-qLogEI search contrast is −0.0158 ($p=0.0067$), much smaller than its measured-value contrast. Thus the classical campaign searches somewhat better in this cell, but most of the apparent single-readout advantage arises later, when the campaign identifies a winner.

This truth-based score is available only in simulation. A laboratory would need replicate or confirmation data to estimate it.

## Question 2: Which procedure selects the better condition from noisy measurements?

Under measured-value argmax at the higher-noise setting, DoE has lower regret than qLogEI by 0.0595 at d=6 and 0.0284 at d=8. Against qLogNEI, the primary difference remains −0.0574. At d=6, the qLogEI campaign's measured-selection regret is 0.1553 even though its hidden tested-best regret is 0.0755; DoE's corresponding values are 0.0958 and 0.0597.

The interpretation is not simply “DoE searches better.” The single noisy readout has trouble identifying which of BO's clustered, similarly promising wells is truly best. The decomposition attributes approximately 55–73% of the higher-noise measured-value gap to identification. qLogNEI identifies its own best well more often than qLogEI (22% versus 8% at the primary cell) but does not remove the DoE lead under that terminal rule.

## Question 3: What happens when the final choice comes from a fitted model?

When the GP and quadratic are each optimized naïvely over the full global box, BO appears better by 0.27–0.36 in all four Hill cells. At the primary cell, quadratic-recommendation regret is 0.4163 and GP-recommendation regret is 0.1232, a DoE-minus-BO gap of +0.2931.

That large number is a diagnostic, not a fair headline comparison of mature methods. The quadratic has a saddle in 200/200 Hill runs; maximizing a saddle over a box pushes the answer to a face or corner beyond the local design region. The primary unconstrained-minus-constrained DoE penalty is +0.2995. Under an in-region/ridge recommendation, the primary difference is −0.0063 (p=0.56), and three of four cells are null.

The design × surrogate × locator decomposition explains the mechanism. A GP fitted to DoE points strongly improves over a quadratic fitted to those same points (primary difference −0.2171). A quadratic fitted to BO points behaves differently from one fitted to the CCD. Sampling geometry, surrogate flexibility, and locator are therefore separable causes.

## Question 4: Does confirmation change the conclusion?

Yes, for the protocol actually tested. The campaign data are held fixed, the top three candidates are re-measured, and the final choice is made from the confirmation reading alone. This adds three wells. The primary qLogEI regret becomes 0.1446 and DoE regret 0.1437; DoE-minus-BO is −0.0009 with interval [−0.0263,+0.0253] and Wilcoxon p=0.92.

This is a biologically plausible demonstration that the terminal protocol is part of the treatment. It is not proof that every confirmation design creates a tie. In particular, averaging original and confirmation readings was not run, and this protocol paradoxically makes the DoE selection worse because it discards an already informative first reading.

## Question 5: How should experimental cost be counted?

At N=48, qLogEI uses an opening design followed by adaptive batches—about ten rounds. DoE uses three stages: screen, CCD, and confirmation. A one-shot GP or space-filling design uses one selection round. These methods can have equal wells but very different incubation, readout, modeling, and replanning cycles.

Long-run d=6 campaigns extend to 200 wells. Once the classical arm is allowed to perform steepest ascent and relocate, it matches qLogEI on measured-value arrival: no BO-versus-DoE arrival contrast survives Holm over all 26 tests. The defined well ratios under this rule are 0.73–1.02, so no meaningful well-count saving is demonstrated. Under naïve unconstrained model recommendation, BO can answer earlier, but that partly reflects that the classical pipeline cannot fit its intended model until enough wells have accrued and still uses the problematic locator.

One-shot GP is stable in 20/22 evaluated cells across five design draws. At $\sigma=0.25$ under model recommendation it beats ten-round qLogEI at several targets in one round. This does not generalize to deceptive surfaces and should be interpreted as evidence that adaptive rounds are not automatically valuable on a smooth Hill family.

## Question 6: Does the terminal-rule result generalize across landscapes?

- **Levy and Rosenbrock:** reproduce the qualitative reversal—DoE under measured-value argmax, BO under naïve unconstrained model recommendation, and mostly null under constrained recommendation.
- **Hartmann6:** BO leads under every terminal rule. Removing the d=6 screen makes DoE worse by about 0.206–0.207, so the BO lead is not caused by unfairly dropping active factors.
- **Ackley:** contains a center/void advantage that lets the classical design hit a special point; it is not a clean comparison of general optimization skill and should remain diagnostic.
- **Conclusion:** landscape class matters. No universal winner is supported.

## Question 7: What changes when the deliverable is an acceptable region?

Point regret and map quality answer different biological questions. In the Hill K6 re-score, `doe` is first on point regret but last on map AUC in 23/24 cells. Across external families it is symmetric-difference-worst in 36/92 cells. Screening concentrates wells to find one recipe but leaves dropped dimensions poorly characterized.

The design-space program also exposes internal RSM diagnostics: the reported classical fit is rank-deficient in 50/50 campaigns, overpredicts its confirmation in 25/25, and has calibration error 0.2296 versus 0.0289–0.0443 for the other arms—5.2 times worse than the nearest comparator.

### SPADE as a separate extension

SPADE is a two-plate spread-and-refine protocol intended to map a threshold-defined design space, not just identify one optimum. Retrospective scoring makes it first on map quality and refinement at two rounds, with point regret at parity under a posterior-mean rule. Its calibration is only mid-field (fifth to seventh of nine), and its certificate is not broadly portable.

Certificate containment holds on the project's Hill family, falls below nominal at $\gamma=0.99$ for Levy and Rosenbrock (three of 64 cells survive Holm correction), and is declined entirely on Ackley and Hartmann6. This leaves Hill—the project's own constructed family—as the only family both willing to certify and calibrated.

The separately registered prospective SPADE-method study contains 92,400 rows across seven conditions and narrows the claim further:

- Boundary-targeted plate 2 does not beat random placement of the same number of wells: effect −0.001882, p=0.4108.
- Plate 2 versus plate 1 alone improves the score by +0.0117145 (adjusted p=0.000127), but the improvement is below the prespecified 0.02 smallest effect of interest.
- The local-allocation trade-off does not support a positive $m>0$ rule.
- The map is competitive/parity in the sole target Hill $d=6$, $\sigma=0.10$ condition, but the certificate verdict is inconclusive.
- The mandatory `doe_unscreened` comparator was never implemented, leaving KF-2 NOT_RUN; a not-run kill is not a pass.

The single-recipe and design-space programs should be separated in the manuscript or, preferably, into two papers. Combining their metrics into one claim would hide that they score different deliverables and have different evidence status.

---

# 10. Three-figure main-paper storyline

## Figure 1: Same 48 wells, different final decisions

**Biological question:** If the laboratory has already run the campaign, does its carry-forward protocol change which method appears better?

**Visual design:** Paired point/interval plot with the same Hill campaigns re-scored under hidden tested-best, measured-value argmax, unconstrained recommendation, in-region/ridge recommendation, and top-three confirmation. Use DoE-minus-BO regret; label negative as DoE better and positive as BO better.

**Suggested panels:** (A) $d=6$, $\sigma=0.25$ primary contrasts; (B) four-cell heat map; (C) search versus identification decomposition; (D) confirmation protocol schematic.

**Caption draft:** “Identical matched-budget campaigns yield different BO-versus-DoE conclusions when only the terminal carry-forward rule changes. Single-readout selection favors DoE, naïve unconstrained model recommendation favors BO, and supported or confirmed selection is null at the primary cell.”

**Main conclusion:** The terminal decision rule defines the comparison.

**Does not prove:** That DoE or BO is universally superior, or that all confirmation protocols eliminate differences.

## Figure 2: Cost in two currencies

**Biological question:** Does a method save wells, plate cycles, or both?

**Visual design:** Regret/hit-probability curves versus cumulative wells beside the same curves versus rounds.

**Suggested panels:** (A) measured-value arrival versus wells; (B) versus rounds; (C) hit probability $P(T\le N)$; (D) one-shot GP versus sequential qLogEI and sequential RSM.

**Caption draft:** “Equal well budgets hide different sequential burdens. Walking RSM and qLogEI have similar measured-value arrival through 200 wells, whereas one-shot designs use fewer decision rounds on the smooth Hill benchmark.”

**Main conclusion:** Cost claims require both well and round units.

**Does not prove:** Calendar-time, labor, reagent, or equipment savings, which were not measured.

## Figure 3: Why the model-based ranking reverses

**Biological question:** Why can the fitted response surface nominate a poor untested recipe?

**Visual design:** A two-dimensional slice through a representative campaign, showing sampled wells, true surface, quadratic contours, GP mean, the quadratic stationary point, allowed design region, ridge/in-region recommendation, and hidden optimum.

**Suggested panels:** (A) DoE sampling region; (B) saddle/canonical diagnostic; (C) unconstrained boundary nomination; (D) constrained/ridge and GP nominations.

**Caption draft:** “The large unconstrained BO advantage is driven mainly by maximizing saddle-shaped quadratic fits outside their learned region. Canonical diagnosis and in-region/ridge recommendation remove most of the gap.”

**Main conclusion:** Locator validity, not only sampling quality, causes the reversal.

**Does not prove:** That quadratic RSM is inherently invalid; proper sequential and ridge procedures are part of classical RSM.

## Optional Figure 4 or separate paper: One recipe versus an operating region

Use an identical campaign to show the best selected point and the inferred acceptable region. Contrast point regret, symmetric difference, calibration, refinement, and containment. Given the prospective failed kills and missing comparator, the cleaner choice is a separate design-space paper or a clearly labeled exploratory section.

---

# 11. Ranked result inventory

| Rank | Biology-facing result | Comparison and metric | Numerical evidence | Interpretation | Category | Placement |
|---:|---|---|---|---|---|---|
| 1 | The carry-forward rule changes the apparent winner | Same Hill campaigns; simple regret | Primary: −0.0595 measured choice, +0.2931 naïve model, −0.0063 in-region | Ranking is not a property of method acronyms alone | Confirmatory + diagnostic | Main text/Fig. 1 |
| 2 | Confirmation removes the primary single-readout lead | qLogEI vs DoE, top-three confirmation | −0.0009 [−0.0263,+0.0253], p=0.92 | Laboratory protocol can dominate benchmark ranking | Secondary/registered | Main text/Fig. 1 |
| 3 | Most higher-noise lead is identification, not search | Tested-best versus measured argmax | 55–73%; primary search gap −0.0158 vs measured −0.0595 | Finding a good well and recognizing it are different tasks | Secondary | Main text |
| 4 | The large model-based BO advantage is an extrapolation diagnostic | Unconstrained versus in-region quadratic | Saddle 200/200; penalty +0.2995; in-region null 3/4 | Do not treat naïve saddle maximization as fair RSM | Diagnostic | Main text/Fig. 3 |
| 5 | qLogNEI does not remove the higher-noise conclusion | DoE vs qLogNEI | Measured gap −0.0574; qLogNEI identification 22% vs qLogEI 8% | Correct acquisition choice improves recognition but not the main verdict | Secondary/co-primary | Main text |
| 6 | Well count and round count give different cost stories | qLogEI, sequential RSM, one-shot GP | 48 wells: ~10, 3, and 1 rounds; measured-value well ratios 0.73–1.02 | Equal wells do not mean equal laboratory cycles | Secondary | Main text/Fig. 2 |
| 7 | No universal landscape winner exists | Hill/Levy/Rosenbrock/Hartmann6/Ackley | Hartmann6 favors BO under all rules; Levy/Rosenbrock reverse | Conclusions are conditional on response geometry | Robustness/exploratory | Main + supplement |
| 8 | Sampling, model, and locator are separately measurable | Crossed design × surrogate analyses | GP-on-DoE minus polynomial-on-DoE −0.2171 primary | Whole-workflow comparisons cannot assign mechanism | Secondary/diagnostic | Main or supplement |
| 9 | Point optimization and map construction reorder methods | `doe` point regret vs map metrics | Last map AUC 23/24 Hill cells; symmetric-difference worst 36/92 | Best recipe is not a reliable operating region | Secondary extension | Separate section/paper |
| 10 | Classical map diagnostics reveal severe fit problems | RSM self-diagnostics | Rank-deficient 50/50; overpredicts 25/25; calibration 5.2× worse | Map claims require estimability and calibration checks | Diagnostic | Design-space paper |
| 11 | SPADE's broad mechanism is not prospectively supported | Targeted vs random second plate | −0.001882, p=0.4108 | Its distinctive boundary targeting lacks evidence | Unsupported broad claim | Design-space limitations |
| 12 | Published biological data do not validate the optimizer ranking | Digitized Hall replay | MDE 0.68; null | Main conclusions remain synthetic | Needs further data | Limitations |

All numerical results in rows 1–11 are artifact-derived synthetic results. None is a direct biological treatment effect.

---

# 12. Claims and boundaries

## 12.1 Strongest defensible claims

1. On a frozen constructed Hill ensemble with 48 matched evaluations, changing only the terminal rule reverses or erases the BO-versus-DoE conclusion.
2. Under higher benchmark noise, the DoE lead from selecting the largest single observed value is mostly an identification effect; a three-candidate confirmation protocol removes that primary-cell difference.
3. The large advantage of GP over a naïvely optimized quadratic is mainly caused by extrapolative maximization of saddle-shaped fits and is not a fair summary of classical RSM with canonical/ridge safeguards.
4. Sampling design, surrogate class, and final locator contribute separately and can be measured on crossed versions of the same campaigns.
5. Well count, experimental-round count, single-recipe regret, and design-space map quality are distinct outcomes that can rank procedures differently.

## 12.2 Overclaims and safer replacements

| Overclaim | Why too strong | Safer wording |
|---|---|---|
| “DoE beats Bayesian optimization.” | True only under specified cells and terminal rules | “Under measured-value argmax at higher benchmark noise, sequential DoE had lower regret than qLogEI/qLogNEI on the Hill ensemble.” |
| “Bayesian optimization beats RSM by 0.3.” | Driven by an invalid unconstrained saddle locator | “Naïve full-box quadratic maximization performed poorly; the gap largely disappeared with an in-region/ridge recommendation.” |
| “BO saves experiments.” | Walking RSM matches measured-value arrival; rounds differ | “No well-count saving was demonstrated under measured-value arrival; the methods use different numbers of decision rounds.” |
| “The benchmark models endothelial differentiation.” | Factor labels and parameters were not fitted | “The benchmark is structurally inspired by a six-to-four-factor ECM workflow and uses generic Hill-like responses.” |
| “The 25% noise level is realistic.” | It is an abstract Gaussian parameter, not an estimated assay variance | “$\sigma_{\mathrm{rel}}=0.25$ is the prespecified higher-noise benchmark condition.” |
| “A null result proves the methods equivalent.” | Non-significance is not equivalence | “No difference was demonstrated under the stated test, sample, and protocol.” |
| “SPADE provides a calibrated design-space certificate.” | Holds only on Hill; fails/declines elsewhere | “The certificate was calibrated on Hill but did not generalize across the four external families.” |
| “SPADE's targeted second plate improves the map.” | Prospective targeted-vs-random test failed | “A second plate was evaluated, but boundary targeting did not outperform random placement at equal well count.” |
| “The benchmark uses biological replicates.” | Replicates are landscapes/seeds, not specimens/wells | “The benchmark uses paired simulated landscapes and algorithmic seeds.” |

## 12.3 Mandatory scope statement

The manuscript should state in the abstract, Methods, and Discussion that this is a computational benchmark. The response surfaces are biologically inspired but constructed; noise is abstract rather than estimated from raw replicate assays; measured-value argmax is one possible laboratory rule; unconstrained quadratic maximization is not synonymous with classical RSM; the design-space and single-recipe studies are separate evidence bodies; and a null result is not proof of identical performance.

---

# 13. Biology-focused Discussion outline

## 13.1 What this means for experimental planning

1. **Start with the deliverable.** If the goal is one formulation, point regret and a confirmation plan are appropriate. If the goal is a robust operating window, map quality and containment must be evaluated directly.
2. **Prespecify the carry-forward rule.** A highest single reading, replicated mean, confirmed shortlist, posterior mean, and untested model peak are different experimental protocols.
3. **Separate finding from recognizing.** If assay noise is material, allocate wells to replication or confirmation rather than assuming a better sampler will identify the correct well.
4. **Diagnose model recommendations.** For quadratic RSM, inspect canonical form, rank, design region, and confirmation performance before trusting a stationary point.
5. **Budget rounds as well as wells.** Adaptive methods trade decision cycles for information. Whether that is worthwhile depends on incubation time, assay turnaround, automation, and the ability to run plates in parallel.
6. **Match flexibility to geometry.** Smooth, low-effective-dimensional systems may not need many adaptive rounds; deceptive or multimodal systems may.

## 13.2 Why published comparisons can appear contradictory

Narayanan et al.'s reduction relative to predicted standard-DoE requirements, Rummukainen et al.'s equal-budget no-saving result, and Lapierre/Ndahiro's executed workflow comparisons answer different questions. Their denominators, screening procedures, factor sets, model constraints, acquisitions, final picks, and experimental systems differ. The correct synthesis is not that one paper invalidates another; it is that an efficiency claim must name its counterfactual and terminal rule.

A comparison of complete workflows is valuable for deployment, but it cannot say which component caused the difference. This benchmark complements such studies by crossing sampling design, surrogate, and locator while holding the hidden landscape fixed.

## 13.3 Practical laboratory decision guide

| Laboratory situation | Recommended comparison/protocol | Reason | Caveat |
|---|---|---|---|
| One recipe, noisy assay | Compare confirmed shortlist performance | Avoids single-well winner's curse | Specify how original and confirmation readings are combined |
| One recipe, cheap rapid feedback | Batch BO versus sequential RSM | Both can adapt and relocate | Report wells and rounds |
| One recipe, slow multi-day assay | One-shot spread design + flexible model | Reduces sequential delays | May be fragile on deceptive landscapes |
| Quadratic fit has a saddle | Canonical/ridge analysis and relocation | Full-box peak is unsupported | Do not label boundary maximum “the RSM optimum” |
| Many nuisance factors | Include screening and unscreened sensitivity where feasible | Screening may concentrate useful wells | Dropped dimensions cannot be mapped |
| Goal is an operating window | Score excursion-set/map quality and containment | Point regret cannot validate a range | Requires calibration on external/real systems |
| High biological heterogeneity | Model donor/batch effects and replicate hierarchy | Gaussian iid noise is inadequate | Increases sample and analysis burden |
| Reagent or safety constraints | Constrained designs/acquisitions | Avoid infeasible recipes | Not represented in the primary benchmark |

## 13.4 Biology limitations

- No prospective wet-lab optimization campaign.
- No fitted mechanistic or empirical cellular response surface.
- No biological replicates in the experimental sense; the two seeds are computational repeats.
- Noise does not separately represent technical replicate error, biological replicate variation, donor/batch variation, or plate-to-plate drift.
- No plate-position effects, edge effects, evaporation, reagent lots, incubation timing, or instrument drift.
- No failed wells, missing values, censoring, limits of detection, or image-analysis failures.
- No formulation feasibility, solubility, osmolarity, toxicity, or compositional constraints unless present in a separate configuration.
- No cell-state drift or nonstationary biology across rounds.
- No cost model for labor, calendar time, robotics, or reagent volumes.
- Only a small set of mathematical benchmark families; these do not span real biological response geometries.
- The main response is single-objective; real studies may balance yield, phenotype, viability, and robustness.

## 13.5 Realistic future biological validation

**System.** Use a tractable multicomponent media or ECM optimization with six continuous factors, a stable phenotype assay, and sufficient prior evidence to define safe concentration ranges. A system with one- to three-day turnaround is preferable before attempting a long differentiation protocol.

**Design.** Pre-register at least two workflows: (1) screen → four-factor CCD → canonical/ridge recommendation and (2) GP-qLogNEI batch BO. Give both the same condition-well budget and comparable replicate/confirmation budget. If a third arm is feasible, use a one-shot space-filling GP to isolate the value of adaptivity.

**Blocking and replication.** Randomize conditions across plate positions; block by biological batch/donor and plate; include shared controls on every plate; use technical replicate wells only where their estimand is clear. Model the biological batch as the inferential unit rather than treating all wells as independent.

**Responses.** Choose one primary continuous endpoint in advance, such as viable cell yield, phenotype-positive area, or product titer. Record secondary viability and quality endpoints but avoid redefining the optimum after results are seen.

**Terminal rule.** Pre-register a shortlist rule and confirm the top three candidates from each method in new biological batches. Define whether selection uses confirmation alone or a hierarchical combination of all readings; the latter is likely more efficient but was not tested in this repository.

**Primary endpoint.** Latent/replicate-mean performance of each method's confirmed carry-forward formulation in held-out biological batches. Use the same held-out batches for paired comparison.

**Success threshold.** Specify a smallest effect of scientific interest in biological units before running the campaign. If the question is equivalence/noninferiority, power and test that claim directly.

**Analysis.** Compare paired held-out performance with effect intervals; estimate variance components; report failed wells; test sensitivity to plate/batch adjustment; and report condition wells, replicate wells, confirmation wells, rounds, and elapsed calendar time separately.

**Design-space validation.** Only after point-selection validation, preregister a separate threshold and test containment on randomly selected formulations from inside and near the proposed region. Do not validate a map solely at its predicted optimum.

---

# 14. Reviewer-risk audit

| Likely critique | Why a biology reviewer may raise it | Current evidence | Manuscript response | Additional work needed |
|---|---|---|---|---|
| Biological relevance is indirect | No real cells generated main outcomes | Hall-inspired structure; auxiliary digitized data | Say “constructed benchmark” early and repeatedly | Prospective wet-lab study |
| Hill benchmark is tuned to the conclusion | Parameters and acceptance are project choices | Frozen versioned ensemble; external families | Publish full generator, sidecars, acceptance audit, sensitivities | Resolve threshold/default mismatch; add preregistered external families if needed |
| Noise is biologically unrealistic | iid Gaussian errors omit hierarchy and drift | Higher/lower noise sensitivity only | Call it benchmark noise, not assay CV | Estimate variance components from raw replicates; simulate heteroscedastic/batch effects |
| RSM comparator is unfair | Naïve saddle maximization is not standard practice | In-region/ridge and sequential relocation analyses | Lead with fair classical rule; present unconstrained result as diagnostic | Ensure long-run model locator is ridge/in-region if making model-based cost claim |
| BO comparator uses wrong acquisition | Observations are noisy | qLogNEI co-primary | Report qLogEI and qLogNEI together | Verify replay drift before release |
| Seeds are called replicates | Could imply biological replication | Analysis averages two seeds within 25 landscapes | Use “algorithmic seeds,” never biological replicates | Wet-lab hierarchical replication |
| Terminal rules look post hoc | Many re-scorings could invite selection | Open-question/registration history; same campaigns | State hierarchy and dates; show all rules | Freeze final estimands in manuscript protocol |
| Statistical n is inflated | 50 runs are not independent | Tests cluster/average to n=25 | Explain paired landscape unit | Audit every table/script for instance clustering |
| Multiple comparisons | Many Q/E/P experiments and cells | Holm used in declared families | Distinguish confirmatory, secondary, exploratory | Produce one final multiplicity map |
| Generalization is weak | Only constructed function families | Levy/Rosenbrock/Hartmann6/Ackley checks | Claim landscape dependence, not universality | Real systems and more preregistered benchmark classes |
| One-shot result is design-lucky | One design draw can dominate | Five-draw Q54, stable 20/22 | Report draw variability | Expand only if central to final paper |
| Design-space story overclaims | Retrospective wins conflict with prospective kills | 92,400-row prospective study, failures disclosed | Separate evidence bodies and narrow claim | Implement `doe_unscreened`; external calibration; likely separate paper |
| Reproducibility is incomplete | Current tests and release validator fail | Artifacts/checkpoints extensive but not clean | Do not claim release-ready | Fix replay drift, missing manifest inputs, and release artifact |
| Novelty is overstated | BO/DoE comparisons and terminal distinctions exist | Adversarial novelty audit | Claim same-campaign reversal and factorial decomposition | Final literature re-read from primary PDFs |

---

# 15. Recommended manuscript outline

## Abstract

- Laboratory problem and matched 48-well budget.
- Constructed Hill benchmark, not wet-lab data.
- Primary same-campaign terminal-rule reversal.
- Search/identification and confirmation result.
- Wells-versus-rounds conclusion.
- Scope limitation and no universal winner.

## Introduction

1. Expensive formulation experiments and exponential design spaces.
2. Planned DoE/RSM and adaptive BO as two laboratory workflows.
3. Existing wet-lab and matched-budget evidence, with denominators clarified.
4. Missing comparison: same campaigns separated into sampling, surrogate, and terminal decision.
5. Study questions and preregistered primary cell.

## Methods

1. Biological scenario and Hall-derived structural inspiration.
2. Synthetic Hill ensemble generation and acceptance.
3. Observation/noise model.
4. BO, qLogEI, qLogNEI, DoE/RSM, sequential relocation, and controls.
5. Terminal decision rules and confirmation.
6. Point, identification, cost, and diagnostic outcomes.
7. Pairing, bootstrap intervals, Wilcoxon tests, and multiplicity.
8. Reproducibility: versions, seeds, artifact provenance.

## Results

1. Same campaigns reverse ranking under different terminal rules.
2. Identification explains most of the higher-noise single-readout lead.
3. Saddle extrapolation explains the giant naïve model gap.
4. In-region/ridge and top-three confirmation erase the primary difference.
5. Wells and rounds give different efficiency conclusions.
6. Landscape-family checks reject a universal ranking.
7. Put detailed design-space work in a clearly separate exploratory section or another manuscript.

## Discussion

1. Terminal protocol is part of experimental design.
2. Finding, identifying, and confirming are distinct laboratory tasks.
3. Classical RSM must include its canonical/ridge/sequential safeguards.
4. Efficiency claims require an explicit denominator and cost unit.
5. Practical selection guide.
6. Synthetic and biological limitations.
7. Prospective wet-lab validation.

---

# 16. Current readiness and unresolved work

## 16.1 What is already strong

- Frozen paired campaigns and extensive result artifacts.
- Explicit separation of terminal rules on the same data.
- qLogNEI co-primary sensitivity.
- Sequential relocating RSM comparator.
- Crossed design × surrogate × locator decomposition.
- Confirmation re-score and cross-family robustness.
- Honest prospective kill ledger for the design-space extension.

## 16.2 What currently blocks a reproducible release

As of 2026-08-24, the full test run reports 1,614 passed and 8 failed. The failures include extremely small numerical drift in several exact comparisons, one P7 map-gate tolerance failure, and larger adaptive replay mismatches in Q42/Q59. The large replay differences must be explained or corrected before treating all committed adaptive artifacts as reproducible under the present environment.

The final SPADE release validator reports nine violations: the missing `results/final-spade-primary.json`, a prose self-reference involving `alpha_star`, and seven absent per-condition manifest source files. In addition, `doe_unscreened` is a required but unimplemented comparator in the prospective study.

The oracle generator's current default depth threshold conflicts with the stored v8 ensemble documentation, as described in Section 5.4. This is a separate provenance issue even if existing artifacts remain unchanged.

## 16.3 Before manuscript submission

1. Decide whether the paper is the terminal-rule benchmark only or includes design-space work.
2. Resolve all adaptive replay failures and document environment/version sensitivity.
3. Repair or explicitly scope the SPADE release validator if SPADE is included.
4. Resolve the oracle-generation threshold provenance and test exact ensemble regeneration.
5. Verify every final number directly from its committed artifact and produce one source table.
6. Re-read cited primary PDFs and correct bibliographic metadata.
7. Freeze confirmatory/secondary/exploratory labels and the multiplicity families.
8. Ensure every use of “replicate,” “best observed,” “RSM,” “cost,” and “noise” is qualified.
9. Decide whether any real biological data can be released and interpreted; otherwise keep them out of the evidentiary chain.

---

# 17. Highest-value questions for the project owner

1. Is the primary audience experimental biologists choosing a formulation workflow, computational-methods reviewers, or an equal mix? This determines how much mathematical detail stays in the main text.
2. Is the manuscript's deliverable one best recipe, an acceptable design space, or two separate papers? The current evidence strongly favors separating them.
3. Which results are formally confirmatory after all revisions: measured-value argmax and in-region recommendation only, or is top-three confirmation also confirmatory?
4. Is the intended headline the terminal-rule reversal, the search-versus-identification decomposition, or the design × surrogate × locator mechanism? One should lead and the others should support it.
5. Should the primary BO comparator be qLogNEI because the benchmark is noisy, with qLogEI as historical/named sensitivity, or retain the current co-primary presentation?
6. What exact oracle configuration generated `biphasic-hill-v8+82f6db7c8f77`, and why does the current `accept_floor` default differ from the stored minimum-depth rule?
7. Will the eight current test failures be fixed by regenerating environment-sensitive artifacts, loosening justified numerical tolerances, or correcting a behavioral regression? This must be decided before final result citation.
8. Will `doe_unscreened` be implemented and the SPADE release completed, or will SPADE be removed from this paper?
9. Are the in-house flow-cytometry data biologically signed off, sufficiently replicated, and releasable? If not, should they be omitted entirely rather than mentioned as pending validation?
10. What wet-lab validation is realistically planned, and which exact terminal rule will be preregistered before the first plate?

---

# 18. Primary references and project evidence trail

## Core external references

- Hall ML, Lin W-H, Ogle BM. “Optimizing extracellular matrix for endothelial differentiation using a design of experiments approach.” *Scientific Reports* 15, 24479 (2025). https://doi.org/10.1038/s41598-025-09256-9
- Box GEP, Wilson KB. “On the Experimental Attainment of Optimum Conditions.” *Journal of the Royal Statistical Society: Series B* 13 (1951). https://doi.org/10.1111/j.2517-6161.1951.tb00067.x
- Jones DR, Schonlau M, Welch WJ. “Efficient Global Optimization of Expensive Black-Box Functions.” *Journal of Global Optimization* 13 (1998). https://doi.org/10.1023/A:1008306431147
- Frazier PI. “A Tutorial on Bayesian Optimization.” arXiv:1807.02811 (2018). https://arxiv.org/abs/1807.02811
- Rummukainen M, et al. “Traditional or adaptive design of experiments? A pilot-scale comparison on wood delignification.” *Heliyon* 10, e24484 (2024). https://doi.org/10.1016/j.heliyon.2024.e24484
- Narayanan H, et al. “Accelerating cell culture media development using Bayesian optimization-based iterative experimental design.” *Nature Communications* 16, 6055 (2025). https://doi.org/10.1038/s41467-025-61113-5
- Lapierre A, et al. “Multi-cycle high-throughput growth media optimization using batch Bayesian optimization.” *Journal of Chemical Technology & Biotechnology* 100, 1571–1583 (2025). https://doi.org/10.1002/jctb.7860
- Ndahiro RK, et al. “Integration of Bayesian optimization and solution thermodynamics to optimize media design for mammalian biomanufacturing.” *iScience* 28, 112944 (2025). https://doi.org/10.1016/j.isci.2025.112944
- Gisperg F, et al. “Bayesian Optimization in Bioprocess Engineering—Where Do We Stand Today?” *Biotechnology and Bioengineering* 122, 1313–1325 (2025). https://doi.org/10.1002/bit.28960
- Kanda GN, et al. “Robotic search for optimal cell culture in regenerative medicine.” *eLife* 11, e77007 (2022). https://doi.org/10.7554/eLife.77007
- Gneiting T, Raftery AE. “Strictly Proper Scoring Rules, Prediction, and Estimation.” *Journal of the American Statistical Association* 102 (2007). https://doi.org/10.1198/016214506000001437

## Primary internal evidence

| Question | Primary repository evidence |
|---|---|
| Main benchmark and current narrative | `docs/RESEARCH-SUMMARY.md` |
| Synthetic construction and biological defensibility | `docs/oracle_defensibility.md`, `src/boec/oracles.py`, `data/oracles/biphasic-hill-v8+82f6db7c8f77/` |
| BO campaign implementation | `src/boec/campaign.py`, `src/boec/optimizers.py`, `configs/experiment/e2.yaml` |
| DoE/RSM implementation | `src/boec/doe.py`, `src/boec/rsm.py` |
| Main matched-budget results | `results/e2-grid.json` and dimension/noise shards |
| Search/identification and qLogNEI | Q55/Q57 artifacts referenced in `docs/RESEARCH-SUMMARY.md` |
| Confirmation | Q58 artifacts referenced in `docs/RESEARCH-SUMMARY.md` |
| Sequential RSM and cost | Q56 artifacts and `results/figures/cost-curves.html` |
| Cross-family robustness | `results/q42-*`, `results/q59-*` |
| Design-space retrospective program | `results/k6-analysis.json`, `results/p6-families/`, P7/P8 artifacts |
| Prospective SPADE study | `docs/SPADE-SPEC.md`, `docs/FINDINGS-SPADE-FINAL.md`, `results/final-spade-*.json` |
| Source checking | `docs/source_verification.md`, `docs/pdf_crosscheck.md` |

**Final writing rule:** every sentence in the manuscript should be traceable to one of four things—a primary source, a committed artifact, a declared project choice, or an explicitly labeled interpretation. If it cannot be traced, it is not ready to publish.
