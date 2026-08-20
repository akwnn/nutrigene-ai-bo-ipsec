# Methods

*Draft methods section, Phase 1 (synthetic benchmark). Person A's lane: search space,
oracle, measurement model, and Experiments 1–3. Experiment 4's model-comparison machinery
is described in Person B's documentation and is summarised here only where the two
experiments share a quantity.*

Numerical values are those actually used; each is traceable to a committed configuration
file or module named in the text.

---

## 2.1 Search space and coding

All optimisation is performed in a coded unit hypercube, $\mathcal{X} = [0,1]^d$. Each
coordinate corresponds to the concentration of one extracellular-matrix (ECM) protein,
linearly mapped from its physical range, with $0$ denoting the lowest tested concentration
and $1$ the highest. Physical ranges (Collagen I, 0–35.5 µg mL⁻¹; Collagen IV, 0–28;
Laminin 111, 0–15.8; Laminin 411, 0–0.8; Laminin 511, 0–0.8; Fibronectin, 22–75) are
retained as labels only and never enter the optimisation.

Coded space was adopted for three reasons. First, the source study reports its design
matrices purely as coded levels $(-,0,+)$ and its figure heat-maps as normalised
concentrations, so a coded representation transfers to Phase 2 without requiring absolute
units. Second, the source study's text is internally inconsistent for one protein
(Collagen IV; §2.10), and coding renders that inconsistency irrelevant to the benchmark.
Third, coding equalises the numerical conditioning of the design matrices across factors
whose physical ranges differ by two orders of magnitude.

The fibronectin lower bound is not zero. The source study reports 22 µg mL⁻¹ as the lowest
concentration supporting reliable cell attachment, and states that its own model could not
evaluate below this level; the constraint is therefore a property of the assay rather than
of the design, and is preserved.

Experiments are run at $d = 6$, corresponding to the six proteins of the source study, and
at $d = 8$, which appends two synthetic factors with no physical interpretation. The
purpose of the $d = 8$ condition is stated in §2.4: the number of *influential* factors is
held fixed across both dimensions, so that the contrast isolates the cost of nuisance
dimensions rather than confounding dimensionality with problem difficulty.

## 2.2 The biphasic synthetic oracle

Phase 1 is a control experiment. Its purpose is to establish whether the optimisation
machinery recovers an answer that is known by construction; real data enters in Phase 2.
The benchmark must therefore have a planted optimum, a controllable difficulty, and a
response shape consistent with the biology.

Each factor is modelled as biphasic — rising, peaking, then declining — because high-dose
ECM proteins and growth factors are genuinely inhibitory. This produces a true interior
optimum rather than a boundary one. Writing $h$ for the activating arm and $g$ for the
inhibitory arm, factor $i$ contributes

$$h_i(x) = \frac{x^{n_i}}{\mathrm{EC}_{50,i}^{n_i} + x^{n_i}}, \qquad
g_i(x) = \frac{1}{1 + (x/\mathrm{IC}_{50,i})^{n_i}},$$

with the Hill exponent $n_i$ shared between the two arms. Writing
$r_i = \mathrm{IC}_{50,i}/\mathrm{EC}_{50,i}$ and $s_i = r_i^{n_i/2}$, the factor response is
peak-normalised,

$$\tilde f_i(x) = h_i(x)\, g_i(x) \left(\frac{1+s_i}{s_i}\right)^{2},$$

so that $\max_x \tilde f_i(x) = 1$ exactly (verified to $8.3\times10^{-10}$). Normalisation
is required rather than cosmetic: unnormalised peak heights span roughly 0.34–0.92 across
the sampled parameter ranges, so two factors of equal weight would otherwise differ
threefold in actual influence, and any measure of factor importance would be confounded
with that artefact.

With the exponent shared, the argmax is available in closed form,

$$x^{*}_i = \sqrt{\mathrm{EC}_{50,i}\,\mathrm{IC}_{50,i}},$$

verified numerically to $2.5\times 10^{-6}$.

### Interaction

The specification originally coupled factors multiplicatively,
$f = \sum_i w_i \tilde f_i + k^{-1}\sum_{i<j}\beta_{ij}\tilde f_i \tilde f_j$. This form was
found to be unusable. Differentiating,

$$\frac{\partial f}{\partial x_i} = \tilde f_i'(x_i)\left[w_i + \tfrac{1}{k}\textstyle\sum_j \beta_{ij}\tilde f_j(x_j)\right],$$

the bracket contains no dependence on $x_i$. The interaction therefore **cannot displace
the optimum**: over 300 instances at $d=6$, the maximum discrepancy between the joint
argmax and the vector of per-factor peaks was $0.00\times10^{0}$ in all 276 cases where the
bracket was positive. In the remaining 8% the bracket is negative, one coordinate's optimum
moves to a box edge, and an optimum search seeded at $x^{*}$ converges to a local maximum,
caching an optimum below the true one and producing negative regret.

The interaction was therefore replaced by *peak modulation*, in which the level of factor
$j$ displaces the peak *location* of factor $i$:

$$m_i(x) = \exp\!\left(\tfrac{1}{k}\textstyle\sum_j \gamma_{ij}\left(\tilde f^{0}_j(x_j) - \tfrac12\right)\right), \qquad k = \lceil d/2 \rceil,$$

with $\gamma_{ij}\sim\mathcal U(-1,1)$ and effective peak $x^{*}_i m_i(x)$; $r_i$ and $n_i$
are unchanged. The modulation reads the *unmodulated* factor value $\tilde f^{0}$, which
breaks the circularity that would otherwise arise. The scaling $1/k$ keeps interaction
magnitude independent of dimension. Positivity is automatic, since
$f = \sum_i w_i \tilde f_i \ge 0$.

The optimum is the fixed point of $x \leftarrow x^{*} \odot m(x)$, which converges in
approximately 18 iterations; $f(x_{\text{opt}}) = 1$ to $1.3\times10^{-16}$. It is
cross-checked against multi-start L-BFGS-B and never taken from the fixed point alone.

**Stated limitation.** Peak modulation does not make the landscape hard for coordinate-wise
search: measured coordinate-descent shortfall is 0–1% of achievable depth even at twice the
chosen $\gamma$ range, because a sum of coordinate-wise-unimodal terms is intrinsically easy
for such methods. The oracle therefore supplies biological realism, calibration structure
and extrapolation geometry; genuine multivariate difficulty is supplied by Hartmann-6
(§2.6). Coordinate descent is included as a benchmark arm specifically so that this
limitation is measured and reported rather than left as an unexamined objection.

## 2.3 Instance sampling and acceptance

Instances are drawn by sampling $(x^{*}_i, n_i, \delta_i)$ and *deriving* $r_i$, rather than
sampling $r_i$ directly, because depth is the property the experiments depend on and
sampling $r$ independently would make window width correlate with $\mathrm{EC}_{50}$ by
construction.

Depth is defined as $\delta = 1 - \tilde f(1)$. Writing $V = (x^{*})^{-n}$ and
$c = 1-\delta$, the defining relation is quadratic in $s$,

$$V(1-c)s^{2} + \left[2V - c\left(1+V^{2}\right)\right]s + V(1-c) = 0.$$

Its roots multiply to unity; the root exceeding one is taken and $r = s^{2/n}$. The
verification case $(x^{*}=0.4,\,n=2,\,\delta=0.414)$ returns $s = 3.9917$, recovering
$r = 4$; the round trip has maximum error $5.0\times10^{-16}$ over 2000 random draws.

Not every depth is achievable: at low $x^{*}$ and low $n$ the discriminant is negative.
The largest achievable depth $\delta_{\max}(x^{*},n)$ is available in closed form as
$1 - \tilde f(1; r=2)$, and this is asserted against a brute-force scan in the test suite —
the specification's prescribed scan over $r\in[2,8]$ is a no-op, since $\delta$ is strictly
decreasing in $r$ throughout that interval.

### Factor influence

The specification drew weights $w_i \sim \mathcal U(0.75,1.25)$ normalised to
$\sum_i w_i = 1$. Under that scheme, and with $\beta = 0$, achievable depth is
$\min_i w_i \delta_i \le \min_i w_i \le 1/d$, so depth is bounded above by $0.125$ at
$d = 8$. The depth required for a signal detectable against pooled measurement error at the
primary noise level is $3\sigma_{\text{rel}}/\sqrt{n_{\text{budget}}} = 0.1083$, i.e. 87% of
the absolute ceiling. Measured on an ensemble generated under the specification: median
depth $0.064$, maximum $0.077$, and **0 of 50 instances** cleared the threshold. Equal
weights do not merely make the primary noise level awkward; they make the $d=8$ arm
infeasible.

The weight structure was therefore changed so that $n_{\text{active}} = 4$ dominant factors
carry a fixed share (0.90) of the total weight and the remainder are near-inert, and the
depth criterion is applied to active coordinates only. An inert factor can be moved to a
bound at negligible cost, which is realistic rather than defective: the source study's own
reported optimum sits at zero for two of six proteins.

Holding $n_{\text{active}} = 4$ at *both* dimensions is deliberate. It fixes the active
subspace so that the $d=6$ versus $d=8$ contrast isolates the cost of nuisance dimensions.
Scaling the active count with $d$ would confound dimensionality with the number of
influential factors.

This structure additionally reproduces the source study's 6→4 screening reduction, giving
the sequential-DoE benchmark arm a real signal to detect, and yields an active-to-inert
influence ratio of 4.50× at $d=6$ and 9.00× at $d=8$, against 1.00× under equal weights —
that is, under the original specification the kernel's automatic relevance determination
had no signal on which to discriminate.

### Acceptance

Instances are accepted on **numerically computed** depth,
$f(x_{\text{opt}}) - \max_{\partial\mathcal{B}} f$, evaluated by $2d$ bound-constrained
searches over the active faces, rather than on the closed-form criterion. The closed form
is derived for the zero-interaction case; applied to instances with interactions it
overstates true depth by a median of 28.4% under the product form (5th percentile −76.3%),
so a threshold placed on it certifies a depth the instance does not possess. Under peak
modulation the overstatement is smaller (6.1% at $d=6$, 3.0% at $d=8$) but non-zero.

Acceptance rates were measured directly. Under the specification's own procedure —
independent draws of $(x^{*},n,\delta,w)$ followed by the test $\min_i w_i\delta_i \ge 0.045$
— acceptance is **6.395% at $d=6$ and 0.105% at $d=8$**, i.e. 952 draws per accepted
instance. The specification's assertion that acceptance "should be high" is false as
written. Drawing $w$ first and resampling $(x^{*}_i, n_i)$ per factor until
$\delta_{\max} \ge \text{floor}/w_i$ raises this to 70% and 80% respectively.

The acceptance floor is **noise-independent and frozen**, so a single ensemble serves both
noise levels; a noise-dependent criterion would confound the noise contrast with an
ensemble contrast.

The ensemble identifier hashes the construction parameters *and* the acceptance parameters,
because under rejection sampling the seed→instance map depends on the acceptance rule.
Because that hash does not cover the numerical optimiser's behaviour, the generated
ensembles are committed as artefacts rather than regenerated on demand (§2.11).

## 2.4 Measurement model

Observations follow $y = f(x)(1+\varepsilon) + \eta$ with
$\varepsilon\sim\mathcal N(0,\sigma_{\text{rel}}^{2})$ and
$\eta\sim\mathcal N(0,\sigma_{\text{add}}^{2})$, $\sigma_{\text{add}} = 0.01$. The
multiplicative term makes variance grow with signal, as assay coefficient of variation does.

$\sigma_{\text{rel}} = 0.25$ is treated as primary and $0.10$ as an optimistic bound,
reversing the original specification. The justification is that the source study normalises
every plate to a fibronectin control explicitly to accommodate interexperimental
variability, and reports no coefficient of variation for its readout. A systematic reading
of the published article confirms this absence: no standard deviation, standard error,
coefficient of variation or exact $p$-value is reported for the CD31 readout anywhere, and
the only $\pm$ values in the article refer to a different assay. The noise level is
therefore a stated modelling assumption backed by a *verified* absence of published
dispersion data, not by a published estimate, and is reported as such.

The variance returned with each observation is the **plug-in** estimate
$\hat y^{2}\sigma_{\text{rel}}^{2} + \sigma_{\text{add}}^{2}$, computed from the *observed*
value and floored at $\sigma_{\text{add}}^{2}$. The analytic alternative
$f(x)^{2}\sigma_{\text{rel}}^{2}+\sigma_{\text{add}}^{2}$ is a function of the noiseless
value from which $|f(x)|$ is exactly recoverable; supplying it would disclose the objective
at every training point and corrupt the calibration experiment. It is retained behind an
ablation flag, and the test suite demonstrates the leak by recovering $|f(x)|$ from it.

The plug-in estimator carries a known bias: since
$\mathbb E[y^{2}] = f^{2}(1+\sigma_{\text{rel}}^{2}) + \sigma_{\text{add}}^{2}$, it
overestimates by approximately 1% at $\sigma_{\text{rel}}=0.10$ and 6% at $0.25$, and a
point drawing high noise receives a larger variance and is downweighted. This occurs in
practice and is therefore the appropriate default; the magnitudes are asserted numerically
in the test suite so that any mild over-coverage observed in Experiment 3 can be attributed
rather than debugged.

The floor is set to $\sigma_{\text{add}}^{2}$ rather than a numerical epsilon. That value is
the estimator's own infimum, so the floor is non-binding by construction in Phase 1 and
alters no reported number; its function is to prevent a zero variance being supplied in
later phases, where a fixed-noise Gaussian process would interpolate the affected point
exactly and distort its neighbourhood.

## 2.5 Surrogate model

Experiments use a single-task Gaussian process with a Matérn-5/2 kernel, automatic relevance
determination, and dimension-scaled log-normal lengthscale priors. Observation variances are
supplied explicitly at every training point (fixed-noise likelihood). Inputs are normalised
with explicit bounds; outcomes are standardised.

Predictive quantities are obtained exclusively through a single wrapper. Requesting a
posterior with observation noise via the library's boolean flag substitutes the arithmetic
mean of the training noise vector and applies that single value at every query point,
without warning — behaviour confirmed by planting an outlier in the training variances and
observing the added variance track the mean rather than the median. Because the calibration
experiment's primary quantity is evaluated at points that have not been measured, this path
would compute the headline number against a noise level nobody selected. Supplied noise must
additionally be expressed on the standardised scale while training noise is on the raw
scale; passing raw variances was wrong by a factor of 161 in testing. Both corrections are
implemented in one place and nothing else calls the posterior directly.

## 2.6 Experimental design

**Experiment 1 (correctness).** Branin, Hartmann-6 and Ackley, 20 seeds, budget 48, Bayesian
optimisation against random search at identical budget. This is a gate, not a result:
Hartmann-6 is declared in advance as the pass condition, and a loss there indicates a defect
in the loop rather than a property of the function. Ackley is reported but explicitly not
gated, declared before the run on the grounds that its near-flat global structure at $d=6$
leaves a Gaussian process little to learn.

**Experiment 2 (sample efficiency).** Seven arms at identical budget 48: qLogEI (primary),
qLogNEI (declared secondary), random, Sobol, Latin hypercube, coordinate descent, and a
sequential design-of-experiments pipeline reproducing the source study's procedure —
a resolution-IV screening design (16 runs + 4 centre points), a face-centred central
composite design on the four surviving factors (16 + 8 + 3), a second-order fit, and
**evaluation of the predicted optimum** (1 run), totalling 48. The confirmation run is not
optional: without it the arm's reported outcome is merely its best design point, and the
quantity the method actually produces never enters the comparison.

Grid: $d\in\{6,8\}$, $\sigma_{\text{rel}}\in\{0.10,0.25\}$, 25 instances × 2 seeds. The
25 × 2 allocation is preferred to 10 × 5 at equal cost because across-landscape variance
dominates within-landscape variance by roughly 10:1, giving relative standard errors of
0.648 and 1.010 respectively.

**Experiment 3 (calibration).** Predictive distributions are recorded *before* each batch is
measured, at two point sets: the points the acquisition function proposed, and a fixed
held-out Sobol set. The first is decision-relevant but is coverage under a selection rule;
the second is domain-wide. Both latent and posterior-predictive quantities are reported and
labelled, since they answer different questions. Coverage, sharpness, probability integral
transform and continuous ranked probability score are computed; CRPS uses the closed form
$\sigma[z(2\Phi(z)-1) + 2\phi(z) - \pi^{-1/2}]$ rather than sampling.

## 2.7 Scoring and statistical inference

**Regret.** Simple regret at budget is computed at the **noiseless value of the point the
method would report**, where the reported point is the argmax of the *observed* values. Two
alternatives were rejected, both after being implemented and observed to fail:

- Scoring at the best *observed* value inflates every arm, and not equally. Experiment 1
  demonstrated the magnitude concretely: Branin's reported best-so-far exceeded the true
  optimum, which is impossible.
- Scoring at the best *true* value among visited points credits an arm for reaching a point
  it had no means of identifying. That credit scales with the number of distinct points an
  arm visits, which differs by arm by design, so space-filling arms gain systematically.
  Implemented first, this produced three diagnostic signatures — non-adaptive arms became
  exactly noise-independent, and two space-filling arms matched or beat the adaptive one.

The resulting curve is deliberately not monotone: a later point drawing favourable noise can
displace a genuinely better incumbent, and that error is a real cost of operating under
noise rather than an artefact to smooth away.

**Clustering.** All inference is clustered at the instance level. A grid of 25 landscapes ×
2 seeds has effective $n = 25$, not 50, because the two seeds on one landscape are two
measurements of the same object. Paired differences are aggregated to one value per
landscape before testing; intervals are percentile bootstrap over landscapes (2000
replicates) and significance is assessed by Wilcoxon signed-rank. Resampling individual
evaluations would be invalid, since sequential acquisition proposals are chosen in light of
their predecessors and are not exchangeable.

**Pairing.** Every arm not explicitly exempt opens on an identical initial design for a
given seed, and that opening segment is excluded from the ordering randomisation applied to
non-adaptive arms; pairing that survives design but not scoring is not pairing. Two arms are
declared exempt: Latin hypercube, because sharing an opening would destroy its defining
stratification, and coordinate descent, because it starts from a random interior point by
construction — a centre start would be a hidden advantage on a landscape whose optimum lies
near the centre. Both exemptions are declared rather than silently repaired, because
altering an arm's algorithm after its results exist is a distinct problem.

## 2.8 Pre-registration

Each experiment's endpoints, grid, scoring rule and inference procedure were committed to
version control before the corresponding run, with commit timestamps available for audit.
Where a registered quantity later required amendment, the registration version was
incremented and the reason recorded in place rather than the original text being edited.

One registration failure is reported because it bears on how the remainder should be read.
The over-prediction endpoint was initially registered as a monotone trend in the
extrapolation ratio $\rho$. That claim is not falsifiable: the scoring regions are nested in
$\rho$, the fitted surface is identical across $\rho$, so the constrained maximum is
non-decreasing by construction while the true response is bounded above by peak
normalisation. The measured statistic was a Spearman coefficient of exactly $+1.0000$ with a
zero-width bootstrap interval, which is the signature of the defect rather than of a strong
effect. The endpoint was replaced, before the confirmatory run, with a falsifiable
alternative: whether the second-order model's prediction interval loses nominal coverage as
$\rho$ increases, and at what $\rho$.

A registered secondary hypothesis — that over-prediction decreases with instance depth —
was **refuted**, measuring $+0.3893$ at $\kappa = 0.6$. It is reported as refuted. Achievable
depth spans only $[0.109, 0.139]$ across the ensemble, because the acceptance floor
compresses it, so the test had limited power and the positive sign should not be
over-interpreted either.

## 2.9 Falsifiability auditing of registered endpoints

Pre-registration as described in §2.8 protects against one failure mode only: choosing an
endpoint after seeing which endpoint would give the desired answer. It provides no
protection against a registered endpoint that **cannot return more than one answer**, and
in this project that second failure occurred twice under correct pre-registration
procedure. Because both instances were caught by an explicit check rather than by
intuition, and because the check is cheap and general, it is reported here as a stated
practice rather than as two isolated corrections.

**The failure mode.** A registered decision rule partitions the range of a statistic into
regions and assigns a conclusion to each. The rule is void if any of the following holds,
and none of them is visible from the rule's text:

1. the region assigned to "hypothesis supported" is unreachable given the construction of
   the statistic;
2. the value the statistic takes **when the hypothesised mechanism is absent** falls inside
   a region assigned to some conclusion other than "absent";
3. the two quantities being contrasted differ by construction, so their ordering is fixed
   by the data-generating process rather than by the phenomenon.

The first occurred in the over-prediction endpoint of §2.8: nested scoring regions make the
statistic monotone in $\rho$ by arithmetic, so the measured Spearman coefficient of exactly
$+1.0000$ with a zero-width interval was a property of the definition. The second occurred
in the surrogate diagnostic. Its rule read "fitted lengthscales near the prior median
$e^{\mu} = 10.08$ implies the prior dominates; materially shorter implies the data
dominates". Hyperparameters here are obtained by maximum *a posteriori* estimation, not
maximum likelihood, so the attractor in the absence of likelihood information is the prior
**mode**, $e^{\mu - \sigma^{2}} = 0.5016$, which is also the value the library uses to
initialise the kernel. A fit on outcomes carrying no dependence on the inputs returns
$0.5016$ to four decimal places. The observed opening-design median was $0.502$. Both
branches of the rule therefore resolved to "the data dominates", and the branch that would
have implicated the prior was unreachable, because the prior's own gradient at $\ell = 10$
points downward. The third occurred in the same diagnostic's slice-error measure, where the
response varies in proportion to each factor's weight, so the contrast between influential
and inert factors was fixed by the sampler's `active_share` and took the same value in the
cell where Bayesian optimisation won as in the cell where it lost.

**The practice.** For every registered endpoint, before data collection:

- **State the null value of the statistic, not only the decision rule.** Derive, or obtain
  by simulation, the value the statistic takes when the hypothesised mechanism is absent,
  and check that this value lies in the region the rule assigns to absence. This is a
  single computation and it would have caught all three failures above.
- **Prefer statistics whose null is structural.** The diagnostic's deciding statistic was
  replaced with the ratio of inert to active fitted lengthscale. The prior is identical on
  every input dimension, so any fit that has not learned dimension-specific structure —
  prior-dominated, badly initialised, or otherwise — returns a ratio of $1$ by symmetry.
  A null fixed by construction cannot be mis-specified by the analyst.
- **Where no structural null exists, obtain an empirical one by breaking the link under
  test, not by summarising the model.** Refitting the identical design and identical noise
  with permuted outcomes gives the distribution of the statistic under "no signal" while
  holding sample size, design geometry, outcome marginal and noise level exactly fixed.
  A closed-form quantity taken from the model's prior is not a substitute: with $n$
  observations present the likelihood term always displaces the estimate, and by how much
  is an empirical question. The measured null ratio was $1.006$ (interquartile range $[0.72, 1.50]$ over 200
  runs), confirming the structural argument and quantifying the finite-sample dispersion
  around it.
- **Distinguish a distributional summary from an optimisation target.** The specific error
  above was using the prior's median where its mode was required. Any reference value read
  off a prior must be the one the estimator actually moves toward under the estimation
  procedure in use.
- **Include at least one condition that varies the hypothesised cause.** A design in which
  every model is built with the same prior can describe what the fitted values are; it
  cannot attribute anything to the prior. A counterfactual condition was added in which the
  same recovered designs are refit under $\mathrm{Gamma}(3,6)$, constructed so that exactly
  one factor differs — the library's convenience constructor would have changed the kernel
  wrapper, the outputscale prior and the parameter constraint simultaneously, and a
  contrast that moves three factors attributes to none of them.
- **Normalise contrasts to a scale-free score with a principled zero, or remove them.** The
  slice-error measure was replaced by $1 - \operatorname{Var}(\text{residual}) /
  \operatorname{Var}(f)$ along the corresponding axis, on which a shape-blind predictor
  scores $0$ irrespective of its level error. Measures that could not be repaired this way
  were deleted rather than reported with a caveat.

**Adversarial audit is scheduled between producing numbers and interpreting them.** The
diagnostic's numbers existed for the duration of the audit and were deliberately not read
until it returned. Four independent readings were commissioned with disjoint remits —
whether any reported quantity could fail; whether the claims about the inference library
hold against the installed source and the cited primary literature; whether the secondary
measures are confounded; and whether the artefacts inspected are the ones the experiment
actually produced. The two readings whose remits covered the decision rule — falsifiability
and library provenance — both identified the maximum *a posteriori* anchoring error, and
did so independently of one another; the remaining two did not, their remits lying
elsewhere. Disjoint remits buy coverage rather than replication, and the count of
concurring readers is therefore not evidence of the finding's strength: it was accepted
because the claim was reproduced directly against the installed library, not because two
readers agreed. Placing the audit before interpretation is what makes its verdict usable:
an audit commissioned after a conclusion has been formed is answering a different question,
and its finding cannot be distinguished from post-hoc rationalisation by a reader.

**Reporting.** Endpoints found void are reported as void, with the arithmetic that makes
them so, rather than being silently replaced. Of eight such constructs identified across
this project, five originated with the present author, one was introduced while repairing
another, and one — the lengthscale anchor — repeated in a new place the exact failure whose
guard the same author had written. That rate is reported because it is the relevant prior
for a reader deciding how much of the remaining apparatus to take on trust: the appropriate
inference is not that these particular measurements are unusually fragile, but that
measurement code is, and that the defect rate is only observable where someone looks.

## 2.10 Source verification

Design matrices, response readout, replication statement and reported optimum were verified
against the published article by four independent readings, with disagreements recorded
rather than reconciled by averaging.

The article states the stage-1 Collagen IV high concentration as 28 µg mL⁻¹ in Results and
56 µg mL⁻¹ in Methods; all other factor levels agree. The distinction determines whether the
reported optimum lies inside the tested design region. The published parameter estimates
resolve it: the fitted model's stationary condition in Laminin 411 returns 0.900 µg mL⁻¹
under the Results reading — matching the reported optimum exactly — and 1.169 µg mL⁻¹ under
the Methods reading. The reported Collagen IV optimum therefore lies at coded $+1.40$,
approximately 20% beyond the highest concentration tested.

**This is a reconstruction from published coefficients, not a statement by the authors**, and
is reported as such. Coefficients are given to three decimal places; one of four
coordinates reconstructs to 35.70 against a printed 35.6; and the published table reports
only terms deemed significant, so a suppressed quadratic term would weaken the argument.
Independent statistical review is required before this supports any claim.

Separately, the article states twice that its model could not evaluate fibronectin below the
attachment floor, and its reported optimum sits at that floor. Boundary constraint and
extrapolation therefore both operated, on different factors; they are not competing
explanations.

## 2.11 Reproducibility

All randomness is seeded per (configuration, instance, seed). All runs are single-threaded,
with thread counts pinned before framework import; this is a correctness requirement rather
than a performance choice, because altering thread counts changes floating-point reduction
order and therefore results.

**Declared replay tolerances.** The one-shot GP (`spread_gp`) fidelity gate against
`results/q52-budget-to-target.json` requires worst absolute drift **< 1e-6**, not bit
equality. Environmental float32/BLAS ordering can move ~3e-7; that does not change any
four-decimal number in the paper. Sequential BO `ask()` reseeds from
`(campaign_seed, round, n_observed)` before each `optimize_acqf` call so BoTorch's
internal retry is a function of recorded campaign state (G7b). Replaying *stored visit
logs* from E2 remains a different problem: those logs do not record optimizer retries.
Q60/Q61 therefore re-run from seed rather than splice confirmation onto frozen BO traces.

Generated ensembles are committed as versioned artefacts rather than regenerated from seeds.
The acceptance procedure wraps a numerical optimiser, and the ensemble version hash covers
the construction parameters but not the optimiser's behaviour; two installations with
differing numerical libraries could therefore accept different instances under an identical
version string, with nothing downstream detecting it. Committing the artefact makes the
ensemble authoritative and the generator an audit trail. Regeneration is asserted in the
test suite to reproduce committed landscapes exactly.

## 2.13 Embedding a benchmark in a higher dimension

Generality is tested on four standard families as well as the synthetic oracle. Three of
them (Ackley, Levy, Rosenbrock) accept any dimension. **Hartmann6 does not** — it is
defined at six — and it is the family that carries the reply to *"you built the landscape
that produced your answer."* Reported without d=8 it would be the one family with half the
coverage of the others, which is a reduction along exactly the axis that must not be
reduced: families may be dropped if compute forces it, cells may not, because the cell
where BO lost is one of them.

`oracles.Embedded` places a `k`-dimensional oracle in a `d`-dimensional cube, `d ≥ k`,
with the remaining `d − k` coordinates inert. The active subset is drawn from a recorded
seed rather than taken as the leading coordinates. This mirrors the synthetic oracle,
which holds `n_active = 4` at both d=6 and d=8 and draws the active subset at random, so
that a dimension contrast measures **the cost of nuisance dimensions** rather than
confounding dimension with the number of influential factors.

The inert coordinates are **exactly** inert: the response is bit-identical when they vary,
asserted as an equality over random draws rather than to a tolerance. An
approximately-inert coordinate would mean the arm measures a different function, not a
nuisance dimension. The optimum value is the inner oracle's; the inert coordinates are
reported at the box centre in `optimum_x`, and it is checked that this does not place the
optimum at the exact centre of the box, which would void rule A (see §2.6 — every
screening and central-composite design includes centre runs, so a centred optimum is
contained in the design for free).

Embedding into the oracle's own dimension is the identity, and is tested as such.

**A consequence worth recording, because it is a property of the classical pipeline rather
than of the embedding.** The screening stage retains a fixed four factors (§2.6, matching
the published 6→4 reduction). Hartmann6 has six active coordinates, so the pipeline
discards genuinely influential factors at every dimension. At d=8, where two coordinates
are provably inert, the screen retains **2.96 of 4 (σ=0.25) and 2.88 of 4 (σ=0.10)**
active factors against a chance value of **3.00** — and does marginally worse at the lower
noise level. On this surface the screening design is not merely noise-limited; it carries
no information about which factors matter. Screening performance is therefore reported
alongside regret wherever an active set is known, rather than assumed adequate.

## 2.14 Identification error, and why concentration protects against noise

A budget-to-target curve reports *"evaluations needed to reach regret T"*. If T lies below
what the assay can resolve, that curve measures **censoring rather than efficiency**.
Whether that is so must be settled before the grid runs, so the decision cannot be made
after seeing which targets flattered which arm.

**Construction (`boec.identification`, `scripts/run_q52_floor.py`).** Plant the true
optimum in the visited set — `n − 1` Latin-hypercube points plus `x*`, exactly, not to a
tolerance — and score normally. The surviving regret is then **pure identification
error**: the design already holds the best point in the space, so nothing it loses is a
search failure. Verified as a precondition rather than assumed: across all 50 instances at
d ∈ {6, 8}, `|truth(x*) − optimum_value| = 0.00e+00` and no design point ever exceeds the
planted one.

### ⚠️ This is not a lower bound for adaptive arms, and it was first written as one

The original claim here was that a design containing the optimum cannot be beaten by one
that must find it. **The §1.2 run refuted it within the hour:** qLogEI reports **0.049** at
n=500, d=6, σ_rel=0.25, where this construction gives 0.129 at n=384.

The error was in what rule A costs. Its penalty on a mis-pick is the true value of
*whichever point won by luck*, so a bound needs the runners-up to be **bad** — and a good
optimiser's runners-up are not. Holding the planted optimum, the noise and `n` fixed and
varying only the spread of the competitors:

| competitors, n=384, d=6, σ_rel=0.25 | rule A regret |
|---|---|
| space-filling | 0.1226 |
| clustered near the optimum | **0.0144** |

**Concentration is protective under rule A, independently of finding a better point.** An
adaptive method gains twice from concentrating: its best point is better, *and* its
reported answer degrades far less under assay noise, because every candidate it might
mis-pick is nearly as good as its best. This is the mirror image of the reason
`reported_best_curve` exists at all (§2.7): under *oracle*-best, scattering is rewarded
because a method is credited for points it could not identify; under *reported*-best,
clustering is rewarded because mis-identification stops being expensive.

The numbers below are therefore the identification penalty **of a space-filling design** —
a bound for the static arms (random, Sobol, LHS, and the classical arm insofar as its
design spreads), not for anything adaptive. **No target is pruned on them.**

**The two rules move in opposite directions, so one number would be wrong for one of
them.**

* **Rule A (best-observed, the registered rule)** picks by observation, so every extra
  point is another chance for a mediocre one to draw lucky noise and displace the planted
  optimum. Its floor **rises with n** — at d=6, σ_rel=0.10 it degrades from 0.0432 at
  n=24 to 0.0746 at n=384, and the rate at which the assay names the true optimum falls
  from 68 % to 24 %. At σ_rel=0.25, n=384 that rate is **8 %, on a point that was
  measured.** The best reachable target under rule A therefore sits at an *interior*
  budget, and past it, spending more makes the reportable answer worse.
* **Rule C (posterior mean)** pools every observation into one fit, so it is limited by
  estimation rather than by the luckiest single draw, and its floor is far lower — 0.0781
  against rule A's 0.1219 at d=6, σ_rel=0.25.

**This does not contradict the budget sweep of Q49**, where a Latin-hypercube arm's regret
*falls* with n. That arm must both find and identify, and more points help finding more
than they hurt identifying. The floor isolates identification alone, which is the component
that gets monotonically worse.

**Two limits, stated.** Rule A's interval averages 400 noise draws over a *single* design
per instance, so design variance enters only through the across-instance bootstrap, not
within it. And rule C's floor uses a space-filling design plus one planted point; an
adaptive arm's design is not space-filling, so that number is a floor for this design
family rather than for every conceivable one. It is the weaker of the two bounds.

**One unexplained anomaly, recorded rather than smoothed.** Rule C's floor is non-monotone
in `n` with a consistent local maximum at **n=96 in all four cells** (0.0692 / 0.1198 /
0.0690 / 0.1061), with intervals that do not overlap the n=192 values. Four cells out of
four is not sampling error, and no explanation has been established. It changes no decision
here — pruning uses the minimum over `n`, and n=96 is never the minimum — but it is not
understood and should not be cited as a smooth estimation-limited curve.

## 2.12 Limitations

The benchmark is a control experiment, not a model of hiPSC differentiation. The defensible
claim is that its responses are *shaped like* published dose-response behaviour, with stated
parameter ranges and a factor-activity structure matched to the published screen — not that
it matches real data. Forty-eight conditions from a single study, available only as figure
marks and reporting no dispersion, cannot validate a six-dimensional surface.

The landscape is additive to first order and its factors are coordinate-wise unimodal, which
makes it tractable for coordinate-wise search; this is measured and reported rather than
assumed away, and Hartmann-6 is included because it is not.

Achievable depth is compressed by the acceptance floor, limiting the power of any analysis
treating depth as a factor.

Two benchmark arms are unpaired by declared exemption, so their comparisons against the
adaptive arms are marginally less precise than the paired ones.
