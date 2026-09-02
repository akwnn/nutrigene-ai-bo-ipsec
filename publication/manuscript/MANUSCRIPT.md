# SPADE: certifying operating regions for cell-manufacturing experiments under fixed well budgets

## Abstract

Cell-manufacturing optimization usually returns a best tested recipe or a model optimum, but
development decisions often require a region of operating conditions that remains acceptable
under uncertainty. We developed SPADE, a sequential Gaussian-process design and certification
workflow that can abstain when the data do not support such a region. We compared SPADE with
noisy Bayesian optimization (qLogNEI), screened and unscreened classical design of experiments
(DoE), and one-shot Latin-hypercube sampling at a common budget of 48 wells. Across five
synthetic response families and 32 seeds per family, SPADE at five rounds showed no detectable
regret difference from qLogNEI at ten rounds (SPADE minus qLogNEI `-0.0005`, 95% CI
`[-0.0221, 0.0207]`; n=160). At matched five rounds, SPADE produced greater certified volume
than qLogNEI (`+0.000855`, 95% CI `[0.000691, 0.001028]`; n=320). Classical DoE found a
better single recipe in three rounds (`+0.1026` SPADE-minus-DoE regret) but produced
over-confident regions: screened DoE contained truth in 85 of 122 answered cells and
unscreened DoE in 77 of 134, whereas SPADE contained truth in all 66 answered cells. Across
five families and five target prevalences, answer rate was strongly associated with the true
margin-to-noise ratio (Spearman rho `0.9801`; 25 cells). The biphasic Hill family became
certifiable at prevalence 0.70 (40 answered, 40 contained), but this diagnostic uses the true
surface and is explanatory rather than deployable. Supporting analyses on in-house and
published endothelial-cell data revealed severe posterior-width collapse under plug-in mean
estimation and assay-specific calibration, but do not constitute prospective wet-lab
validation. SPADE therefore offers a measured trade-off: it can return a trustworthy operating
region or abstain, while classical DoE can locate a stronger point recipe faster and BO can
match optimization quality. Its present evidence is bounded to the tested synthetic regime,
48-well budget, and lower-noise setting.

**Keywords:** Bayesian optimization; design of experiments; Gaussian process; operating
region; cell manufacturing; uncertainty quantification; abstention.

## 1. Introduction

Optimization and process qualification answer different questions. A best measured recipe
asks where performance was highest among tested wells. Bayesian optimization asks where to
sample next to improve an objective [1,2]. A manufacturing scientist may instead need a set of
recipes for which performance exceeds a specification with stated assurance. That set is
useful only if its uncertainty statement is empirically trustworthy; returning no set can be
the correct answer when data are insufficient.

This distinction matters in cell manufacturing. Experimental budgets are counted both in
wells and in sequential rounds, and an operating range can be more actionable than a single
model optimum. Classical response-surface DoE can be efficient for locating a recipe, while
adaptive BO can exploit nonlinear surfaces. Neither advantage alone establishes that the
reported operating region contains the true acceptable set at the promised rate.

We developed SPADE to join sequential design with a conservative-set certificate and an
explicit abstention rule. The study asks four bounded questions: whether SPADE preserves
recipe quality relative to noisy BO; whether its extra rounds buy a trustworthy region
relative to classical DoE; whether it improves on a one-shot design; and whether
certifiability generalizes across response families relevant to cell-manufacturing shapes.
The comparisons deliberately report adverse results. In particular, classical DoE is allowed
to win recipe regret, and all certification results report both how often a method answers and
how often answered regions contain truth.

## 2. SPADE workflow

Each campaign has 48 wells. SPADE begins with a space-filling plate, fits a Gaussian process
using per-well observation variance, and allocates later batches near the conservative
acceptability boundary. The fitted posterior is evaluated on a fixed candidate grid. Joint
posterior draws define nested excursion sets; the largest set meeting the requested assurance
is returned as the certified region. If no non-empty set satisfies the rule, SPADE abstains.

The scientific estimand is therefore not merely the posterior probability at individual
points. It is the empirical containment of a jointly selected region against the known truth
in synthetic benchmarks. Calibration inflation is selected without using the held-out family
under the registered leave-one-family-out procedure. Full definitions, frozen constants, and
implementation paths are given in `METHODS.md`.

## 3. Results

### 3.1 SPADE and noisy BO have indistinguishable recipe regret in the one-process comparison

The DC experiment ran SPADE and qLogNEI under the same current code and process, eliminating
an earlier cross-run drift concern. SPADE at five rounds minus qLogNEI at ten rounds was
`-0.0005` regret (95% CI `[-0.0221, 0.0207]`, p=0.96; five families × 32 seeds). The interval
is slightly wider than the registered ±0.02 smallest effect of interest. We therefore report
no detectable difference, not equivalence and not superiority. SPADE uses half as many rounds
in this comparison, but no direct calendar-time or financial saving was measured.

### 3.2 SPADE certifies more volume than qLogNEI at matched five rounds

Under the frozen leave-one-family-out analysis, SPADE minus qLogNEI certified volume at five
rounds was `+0.000855` (95% CI `[0.000691, 0.001028]`, p<0.0001; n=320). This corrects an
unsupported `+0.001353` value in historical prose; the frozen analyser and exact committed
inputs never reproduce the older number. The analogous three-round effect did not survive
extension to 32 seeds and is not claimed.

At three rounds, SPADE also improved recipe regret relative to one-shot Latin-hypercube
sampling (`-0.0783`, 95% CI `[-0.1104, -0.0490]`; n=80). This isolates value beyond a single
space-filling batch, while avoiding the stronger claim that all sequential mechanisms help.

### 3.3 Classical DoE finds a better recipe but returns over-confident regions

The classical comparison is intentionally adverse to SPADE. Screened DoE used three rounds,
SPADE five, and qLogNEI ten. Screened DoE beat SPADE on regret: SPADE minus DoE was `+0.1026`
(95% CI `[0.0486, 0.1578]`, p=0.0003; n=160). The extra SPADE rounds did not buy a better
point recipe.

They did buy a different deliverable. At target prevalence 0.30, SPADE answered in 66 of 160
cells and all 66 regions contained truth (one-sided 95% lower bound 0.9556). Screened DoE
answered in 122 cells but contained truth in only 85 (0.6967); unscreened DoE answered in 134
but contained truth in only 77 (0.5746). Removing the 6-to-4 factor screen worsened rather
than repaired containment. DoE's failure was therefore over-confidence, not abstention and
not merely the screening decision. The defensible conclusion is narrow: in this benchmark,
DoE finds a stronger recipe faster, while SPADE is the only tested arm with perfect observed
containment of its answered regions.

### 3.4 Certifiability follows target margin relative to noise across five families

At a fixed target prevalence, several families initially appeared impossible to certify.
Sweeping prevalences 0.70, 0.50, 0.30, 0.20, and 0.10 showed that answer rate tracks the
true-surface margin divided by observation noise (Spearman rho `0.9801`, p<0.0001; 25
family-prevalence cells). This result spans Ackley, Hartmann6, Hill, Levy, and Rosenbrock.
Because it uses the latent truth, margin-to-noise is a mechanistic explanation rather than a
prospective diagnostic available to a practitioner.

The biphasic Hill family is retained inside this cross-family analysis and reported
separately because its response shape most closely resembles the biological motivation. At
prevalence 0.70 and inflation 1.0, SPADE answered 40 of 64 cells; all 40 contained truth
(lower bound 0.9278). qLogNEI also had perfect observed containment but answered only 27
cells, below the minimum count needed for the registered lower-bound criterion. This is not
evidence that BO cannot certify Hill; it is evidence that answer count and target prevalence
must accompany any certification statement.

### 3.5 Correctly aiming the acquisition at the target does not improve SPADE

The mechanism experiment replaced the historical targeting threshold with the actual
certification threshold. Certified-volume change was `+0.000425` (95% CI
`[-0.000022, 0.000875]`), while regret worsened by `+0.0301` (95% CI
`[0.0169, 0.0450]`, p<0.0001). Family effects cancelled: targeting helped Hartmann6 and
hurt Ackley. The extra targeting mechanism therefore does not earn its complexity in the
tested form.

### 3.6 Real-cell analyses are supporting evidence, not prospective validation

On both the in-house iPSC-EC candidate dataset and a published Hall–Ogle extraction [3],
plug-in posterior uncertainty collapsed when an estimated mean was treated as fixed.
Marginalizing mean uncertainty widened the posterior by 484× in-house and 297× in the
published data, compared with only 1.004–1.011× on synthetic benchmarks. Leave-one-out
inflation was assay-specific (`c=0.712` in-house; `c=0.526` published), rather than the
simulated default 1.5. These analyses support the need for explicit uncertainty treatment,
but the in-house gates still await human signoff and neither dataset is a prospective SPADE
campaign.

## 4. Discussion

SPADE's contribution is a change in deliverable and reporting discipline rather than a claim
of universal optimizer superiority. Under a common well budget, noisy BO matched SPADE's
recipe quality and classical DoE found a better recipe with fewer rounds. SPADE's advantage
was that its answered regions were empirically trustworthy in the tested regime. Its
disadvantage was abstention and additional sequential rounds relative to DoE.

Three findings constrain interpretation. First, “cannot certify” is ambiguous unless answer
count is reported: a method may abstain, answer too few cells for a lower bound, or answer
confidently and be wrong. Second, target difficulty is not a family label. The same Hill
surface moved from apparent saturation to successful certification when prevalence increased.
Third, a plausible targeting mechanism did not improve the aggregate outcome and harmed
regret. These negative results narrow the method and should guide future design.

The most important limitation is noise. All main benchmarks use relative noise 0.25. At the
measured real-assay level near 0.68, no tested arm certifies. The synthetic Hill family is
structurally inspired by dose-response behavior but is not fitted to endothelial-cell data.
The in-house candidate table awaits manual CD31 gate signoff, and leave-one-out calibration
assesses observation prediction rather than independently identified latent-function
uncertainty. R=4, broader assurance sweeps, larger budgets, and prospective replicate-tube
experiments remain open. The DoE comparator is one low-order response-surface workflow and
does not represent every classical design or model.

## 5. Conclusion

At 48 wells and lower benchmark noise, SPADE can trade point-optimization performance and
sequential rounds for a conservative operating region with explicit abstention. It matches
noisy BO on observed regret, exceeds it in certified volume at matched five rounds, and
avoids the over-confident regions produced by the tested DoE pipelines. It does not dominate
DoE on recipe quality, does not establish equivalence to BO, and is not yet prospectively
validated in wet-lab manufacturing. The practical result is a bounded tool: return a region
only when the data support it, report the abstentions, and preserve the distinction between
finding a good point and certifying a usable space.

## Data and code availability

All canonical benchmark results, frozen protocols, analysis scripts, claim guards, and audit
ledgers are included in this repository. `publication/evidence/reproduction-map.md` lists exact
commands. In-house raw data are retained with checksums and role annotations; access and
reuse remain subject to the final repository license and any applicable laboratory policy.

## References

1. Jones, D. R., Schonlau, M. & Welch, W. J. Efficient global optimization of expensive
   black-box functions. *Journal of Global Optimization* **13**, 455–492 (1998).
   https://doi.org/10.1023/A:1008306431147
2. Frazier, P. I. A tutorial on Bayesian optimization. *arXiv* 1807.02811 (2018).
   https://doi.org/10.48550/arXiv.1807.02811
3. Hall, M. L., Lin, W.-H. & Ogle, B. M. Optimizing extracellular matrix for endothelial
   differentiation using a design of experiments approach. *Scientific Reports* **15**,
   24479 (2025). https://doi.org/10.1038/s41598-025-09256-9
