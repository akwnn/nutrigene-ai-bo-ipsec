# Methods

## Study design and evidence roles

The confirmatory DC and LC experiments used five response families (Ackley, Hartmann6,
biphasic Hill, Levy, and Rosenbrock), 32 deterministic seeds per family, six normalized
factors, 48 measured wells, and relative observation noise `sigma_rel=0.25`. TAU used 64
seeds per family. LA supplied four families and 20 common seeds for C4. The latent response
and optimum were known only for synthetic scoring. Hill parameters varied by instance; the
other registered evaluators used a fixed landscape across seeds. The benchmark is structural
and was not fitted to endothelial measurements.

DC is the one-process comparison supporting C1 and C2. LC is the leave-one-family-out (LOFO)
matched-round analysis supporting C3 and supplies SPADE rows for C4. LA is a frozen
development-lineage one-shot comparison used only for C4. TAU is the five-prevalence
explanatory analysis supporting C5 and C6. TT is the negative mechanism test supporting S1.
The full experiment grid, producers, analysers, and result paths are in
`../evidence/benchmark-matrix.md`.

The principal arms were SPADE, qLogNEI, screened DoE, unscreened DoE, and one-shot Latin
hypercube sampling (LHS). SPADE used five rounds for C1-C3, qLogNEI ten rounds for C1 and five
for C3, the DoE arms three rounds, and LHS one round. All arms used 48 wells; comparisons
therefore distinguish well budget from feedback rounds.

## SPADE campaign and operating-region estimator

SPADE fits a Gaussian process to normalized recipe coordinates `X`, outcomes `Y`, and plug-in
per-well observation variances `Yvar`. The registered campaign begins with a space-filling
batch and allocates later eight-well batches using the conservative-set straddle score in
`boec.certstraddle.batch_lse_rho`; allocation and state transitions are implemented in
`boec.campaign` and `boec.multiround`.

For posterior draw `f^(b)` and threshold `tau`, the excursion set is
`Gamma^(b)={x:f^(b)(x)>=tau}` on the registered finite Sobol candidate grid. Posterior draws
generate a coverage function and nested Vorob'ev quantile candidates. The estimator scans
those candidates and returns the largest candidate whose joint model-posterior containment
meets `alpha=0.95`. “Largest” means largest in this scanned nested family on the finite grid,
not a global optimum over all subsets of a continuous domain. Inflation `c` multiplies
posterior uncertainty and is chosen from `{1.0,1.5,2.0,3.0}` under the experiment-specific
rule. If no non-empty candidate passes, SPADE abstains.

## Outcomes and empirical certification

For each family, seed, prevalence, arm, and inflation, the result schema records:

- `answered`: the returned conservative estimate is non-empty;
- `contained`: an answered estimate is a subset of the known synthetic true excursion set;
- answer rate: answered cells divided by eligible cells;
- observed conditional containment: contained divided by answered;
- certified volume: candidate-grid fraction in the returned set; and
- simple regret: one minus truth at the recommended recipe.

The registered empirical criterion requires a one-sided 95% Clopper-Pearson lower binomial
bound of at least 0.90 among answered cells and answer rate of at least 0.05. Both numerator
and denominator are reported. Empty regions are abstentions, not containment successes.
Model-internal `ce_contain_*` is not truth validation; analyses use `ce_empirical_*`.

## Calibration and claim-specific estimands

DC does not use held-out-family calibration. For C2, SPADE passes the within-DC selection rule
at `c=1.0`. Neither DoE arm passes at any tested inflation; their reported `c=1.0` counts are
baseline diagnostics, not selected certificates.

For C3, LC selects the smallest inflation satisfying the registered rule on all families
except one, then evaluates certified volume on the held-out family. The R5 contrast pools
`p=0.30` and `p=0.10`, producing 320 family-seed-prevalence cells (5 families x 32 seeds x 2
prevalences). The executable result is `+0.0008546875`; the historical `+0.001353` value is
not reproducible and is rejected.

C4 pairs SPADE R3 rows from LC with one-shot LHS rows from LA for Ackley, Hartmann6, Levy, and
Rosenbrock and common seeds 0-19. Hill and LC seeds 20-31 are not imputed, giving 80 paired
campaigns.

TAU evaluates `p` in `{0.70,0.50,0.30,0.20,0.10}`, where `tau` is the truth quantile giving
that region prevalence. C5 fixes `c=1.0` and `alpha=0.95`. Within each of 25
family-prevalence cells, `x` is the mean of 64 unique seed-specific true margin/noise values
and `y` is SPADE answer rate over the same seeds. Median margin and qLogNEI-only answer rate
are sensitivities. The analyser rejects duplicate keys, non-finite or inconsistent margins,
incomplete grids, and seed misalignment. This diagnostic uses latent truth and is not
available prospectively.

## Comparators

qLogNEI uses the same Gaussian-process outcome model and well budget with batch noisy log
expected improvement. It is a point-optimization acquisition; all arms' observations are
passed through the same downstream conservative-set estimator. The screened DoE arm uses a
20-run screen reducing six factors to four, a 27-run face-centred response-surface design,
and one confirmation well. The unscreened arm omits factor screening while retaining the
registered low-order response-surface workflow. LHS is a single 48-point space-filling batch.
These implementations do not represent BO or classical DoE as entire method classes.

## Statistical analysis

Contrasts pair common `(family,seed)` or `(family,seed,prevalence)` keys. Frozen analysers use
deterministic nonparametric resampling (`NBOOT=8000` unless otherwise registered) and report
percentile intervals plus two-sided bootstrap tail-area proportions relative to zero. The
flat-cell bootstrap treats rows as exchangeable and is therefore descriptive and conditional
for this fixed generator suite, not a cluster-aware population analysis. The regret smallest
effect of interest is 0.02; an interval crossing its edge is not declared equivalent.

C5 is a descriptive Spearman rank correlation over 25 nested family-prevalence cells. Their
dependence and lack of population exchangeability preclude interpreting a naive correlation
p-value as population inference. Clopper-Pearson bounds likewise summarize observed answered
cells under a binomial model. Heterogeneous families, repeated prevalences, and conditioning
on answering limit transportable coverage interpretation.

## Retrospective real-data support

The in-house input is `research/data/lab/derived/candidate_campaign_coating_flow.csv`; its
role overlays and evidence-linked raw subset are documented under `research/data/lab/`.
The candidate table and CD31 gates remain `awaiting_human_signoff`. Published support uses
canonical Hall/Ogle stage-1 and stage-2 extractions under `research/data/published/`.

Mean-marginalized covariance propagates uncertainty in the fitted intercept/mean instead of
treating it as fixed. The reported width ratio is the ratio of mean posterior marginal
standard deviation over the candidate grid. Leave-one-out inflation is assay-specific and
scores held-out observation prediction; it does not independently identify latent-function
uncertainty. These analyses are retrospective support, not prospective wet-lab validation.

## Reproducibility and software

Python 3.11 dependencies are pinned in `requirements.txt`; the package is installed from
`pyproject.toml`. Exact producer/analyser commands, canonical inputs, expected outputs, and
guard status are listed in `../evidence/reproduction-map.md`. Canonical DC/LC/LA/TAU/TT JSON
files are versioned under `research/results/`. `software/scripts/verify_conclusions.py`
recomputes 12 selected scalar checks; it is not an exhaustive guard for every interval,
p-value, supporting real-data number, or limitation.

The historical baseline at commit `6e4f22e` contains 719 commits and 1,402 files, each
adjudicated in the evidence ledgers. Inactive material is retained under `archive/`. New
campaign runs are not required to verify calculations from the committed canonical results.
