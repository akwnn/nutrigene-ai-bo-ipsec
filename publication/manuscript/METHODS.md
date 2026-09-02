# Methods

## Study design and benchmark scope

Main experiments used five response families (Ackley, Hartmann6, biphasic Hill, Levy, and
Rosenbrock), 32 deterministic seeds per family, six normalized factors, 48 measured wells,
and relative observation noise `sigma_rel=0.25`. The latent response and optimum were known
only for synthetic scoring. Hill parameters varied by instance; other family labels identify
their registered evaluator. The benchmark is structural and is not fitted to endothelial
measurements.

The principal arms were SPADE, qLogNEI, screened DoE, unscreened DoE, and Latin-hypercube
sampling. SPADE used five rounds for C1–C3, qLogNEI ten rounds for C1 and five for C3,
screened and unscreened DoE three rounds, and one-shot LHS one round. Every comparison states
both well budget and rounds.

## SPADE campaign

SPADE fits a Gaussian process to observed recipe coordinates `X`, normalized outcomes `Y`,
and plug-in per-well variances `Yvar`. The registered multi-round schedule partitions the
48-well budget into a space-filling opening and subsequent eight-well batches. Later batches
use a conservative-set straddle score implemented by `boec.certstraddle.batch_lse_rho`, with
campaign state and round allocation in `boec.campaign` and `boec.multiround`.

For a posterior draw `f^(b)` and specification threshold `tau`, define the excursion set
`Gamma^(b) = {x: f^(b)(x) >= tau}` on the registered Sobol grid. Candidate Vorob'ev quantile
sets are scanned to find the largest set whose joint posterior containment meets assurance
`alpha=0.95`. Inflation `c` multiplies posterior uncertainty and is selected from
`{1.0, 1.5, 2.0, 3.0}`. An empty selected set is an abstention, not successful containment.

## Certification outcomes

For each family, seed, prevalence, and arm we record:

- `answered`: the conservative estimate is non-empty;
- `contained`: an answered estimate is a subset of the known true excursion set;
- answer rate: answered cells divided by eligible cells;
- empirical containment: contained divided by answered;
- certified volume: grid fraction in the returned conservative set;
- simple regret: one minus the truth value at the campaign's recommended recipe.

Certification requires empirical containment with a one-sided 95% Clopper–Pearson lower
bound at least 0.90 and answer rate at least 0.05. Both numerator and denominator are always
reported. Model-internal containment (`ce_contain_*`) is never used as truth validation;
analyses read `ce_empirical_*`.

## Calibration and held-out evaluation

The LC matched-round analysis selects the smallest inflation satisfying the registered rule
on all families except one and evaluates volume on the held-out family. This
leave-one-family-out procedure produces C3 over 320 family-seed-prevalence cells. Historical
prose quoting `+0.001353` is rejected because the frozen executable procedure yields
`+0.0008546875` on the committed inputs.

The TAU analysis evaluates target prevalence `p` in `{0.70, 0.50, 0.30, 0.20, 0.10}`.
`tau` is the truth quantile giving region prevalence `p`. The true-surface margin divided by
noise is computed only for explanatory analysis and is unavailable prospectively.

## Comparators

qLogNEI uses the same 48-well budget and Gaussian-process outcome model, with batch noisy
expected improvement. The screened DoE arm uses a 20-run screen reducing six factors to four,
a 27-run face-centred response-surface design, and one confirmation well. The unscreened arm
omits factor screening while retaining the registered budget and low-order surface model.
Every arm's observed `X`, `Y`, and `Yvar` is passed through the same certification estimator,
preventing comparator-specific scoring.

## Statistical analysis

Paired contrasts use common `(family, seed)` or `(family, seed, prevalence)` keys. Confidence
intervals and two-sided p-values use the deterministic nonparametric bootstrap implemented in
the frozen analysers (`NBOOT=8000` unless the protocol states otherwise). C1 uses the
one-process DC comparison and supersedes the earlier cross-run LC point estimate. C5 uses
Spearman rank correlation over the 25 family-prevalence cells. Exact binomial lower bounds use
the Clopper–Pearson construction. The registered smallest effect of interest for regret is
0.02; an interval crossing its edge is not declared equivalent.

## Real-data support

The in-house supporting input is
`research/data/lab/derived/candidate_campaign_coating_flow.csv`, linked to raw FCS files, manual-role
overlays, and checksums. The published support uses the canonical Hall/Ogle stage-1 and
stage-2 extractions under `research/data/published/`. Mean-marginalized covariance propagates
uncertainty in the estimated intercept/mean instead of treating it as fixed. Leave-one-out
inflation is assay-specific. These analyses are retrospective support and are excluded from
claims of prospective wet-lab validation.

## Reproducibility and software

Python requirements are pinned by `requirements.txt`; the package is installed from
`pyproject.toml`. Canonical runners and analysers are listed in
`publication/evidence/reproduction-map.md`. `software/scripts/verify_conclusions.py` recomputes the guarded
headlines directly from committed JSON results. The historical baseline at commit `6e4f22e`
contains 719 commits and 1,402 files, each adjudicated in the audit ledgers. Inactive material
is retained under `archive/` rather than deleted.
