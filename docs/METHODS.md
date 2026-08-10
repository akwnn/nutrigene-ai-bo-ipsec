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
(Collagen IV; §2.9), and coding renders that inconsistency irrelevant to the benchmark.
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
ensembles are committed as artefacts rather than regenerated on demand (§2.10).

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

## 2.9 Source verification

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

## 2.10 Reproducibility

All randomness is seeded per (configuration, instance, seed). All runs are single-threaded,
with thread counts pinned before framework import; this is a correctness requirement rather
than a performance choice, because altering thread counts changes floating-point reduction
order and therefore results.

Generated ensembles are committed as versioned artefacts rather than regenerated from seeds.
The acceptance procedure wraps a numerical optimiser, and the ensemble version hash covers
the construction parameters but not the optimiser's behaviour; two installations with
differing numerical libraries could therefore accept different instances under an identical
version string, with nothing downstream detecting it. Committing the artefact makes the
ensemble authoritative and the generator an audit trail. Regeneration is asserted in the
test suite to reproduce committed landscapes exactly.

## 2.11 Limitations

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
