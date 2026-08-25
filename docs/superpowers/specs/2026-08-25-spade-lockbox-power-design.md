# SPADE Lockbox Power and Sample-Size Design

**Status:** approved design amendment; freeze before development outcomes exist  
**Parent protocol:** `2026-08-25-spade-joint-protocol-design.md`  
**Scope:** map/regret power planning only; the 48-evaluation campaign budget is unchanged

## 1. Purpose

The joint SPADE protocol requires at least 80% planning power for both primary paired
non-inferiority endpoints before the untouched lockbox may open. The original design
specified `n = max(350, n_map, n_regret)` but did not define an executable estimator or
bind the selected sample size into the release chain. This amendment closes that gap
before any development outcome is generated.

The rule must answer one question only: how many independent lockbox landscapes per
family, from the already frozen prefix of keys `0..1999`, are required for map and regret
non-inferiority planning? It cannot change SPADE, its 48-evaluation budget, its selected
configuration, an endpoint, a margin, or an inferential procedure.

## 2. Frozen inputs and anti-bias rule

The calculator consumes:

1. the exact five complete development shards and their manifests;
2. the committed `SELECTED` protocol artifact;
3. the frozen study protocol, configuration, generator source, and generator manifest;
4. the selected policy's paired per-campaign differences:
   - `SPADE map loss - Sobol48 map loss`;
   - `SPADE Rule-P regret - qLogNEI48 Rule-P regret`.

Each development family is eligible only as held-out evidence. The selector must prove
that the final policy was selected in the fold that excluded that family. Unanimous
leave-one-family-out selection therefore supplies five family-specific held-out vectors
without letting a family's own outcomes choose the policy being evaluated on it. Any
missing fold, non-unanimous policy, wrong comparator, duplicate pair, or nonfinite score
is a hard refusal.

The calculator and all constants below are committed before development execution. The
development rows determine only the numerical sample size under this frozen rule.

## 3. Primary deterministic planning model

For family `f`, endpoint `e`, and its `m=50` held-out paired differences `d`, calculate
the sample mean `mu` and Bessel-corrected sample standard deviation `s`.

The registered non-inferiority margin is `delta = 0.02`, one-sided type-I error is
`alpha = 0.05`, and target power is `1-beta = 0.80`. For any candidate lockbox size
`n in {350, ..., 2000}`, estimated paired-normal power is

```text
Phi((delta - mu) * sqrt(n) / s - z_(1-alpha)).
```

If `s == 0`, power is one when `mu < delta` and zero otherwise. If `mu >= delta`, no
finite candidate is credited with power. Inputs and intermediate values must be finite.

The primary calculation is appropriate to independent paired landscape differences and
is deterministic. Published comparisons have found close power agreement between normal
formula and bootstrap sample-size calculations for continuous non-inferiority settings,
but the transfer from development to untouched generator families remains a planning
assumption rather than a guarantee.

## 4. Nonparametric sensitivity and uncertainty

Normal power alone is insufficient because the 50 held-out differences may be skewed.
For every family and endpoint, generate `2,000` deterministic nonparametric planning
replicates:

1. derive a labelled seed from the frozen study seed, family, and endpoint;
2. sample a `2,000 x 2,000` matrix of indices with replacement from the 50 held-out
   differences;
3. treat columns as a nested prefix, so candidate `n` uses columns `0..n-1`;
4. for every replicate and candidate `n`, form the one-sided paired-normal upper bound
   `mean + z_(0.95) * sample_sd / sqrt(n)`;
5. count success only when that upper bound is strictly below `0.02`;
6. report the simulated success fraction and its one-sided 95% Clopper-Pearson lower
   bound.

The deterministic matrix makes repeated runs bitwise stable and lets all candidate sizes
share common random numbers. The simulation is a distributional sensitivity analysis,
not a replacement for the final registered 10,000-replicate percentile-bootstrap test.

A candidate size clears sensitivity only when the Clopper-Pearson lower bound on
simulated power is at least `0.80`. This incorporates Monte Carlo uncertainty instead of
presenting a noisy point estimate as exact power.

## 5. Sample-size decision

For every integer `n` from 350 through 2,000, in ascending order, require all of:

- paired-normal power is at least `0.80` for map in every development family;
- paired-normal power is at least `0.80` for regret in every development family;
- nonparametric-sensitivity power lower bound is at least `0.80` for map in every family;
- nonparametric-sensitivity power lower bound is at least `0.80` for regret in every
  family.

The first size satisfying the full conjunction is selected. It may never be reduced.

If no size through 2,000 passes, the artifact status is `INSUFFICIENT_POWER`, the selected
size is null, and every lockbox runner must refuse. This is a registered negative result,
not permission to weaken margins, power, families, or endpoints.

The certificate planning floor remains independently protected: `n=350` was already
chosen for approximately 82.5% joint planning power under answer rate 0.60 and conditional
containment 0.95. Increasing `n` cannot reduce its nominal binomial planning power.

## 6. Immutable power artifact

`scripts/plan_spade_lockbox_power.py` writes exactly one write-once artifact:
`results/spade-lockbox-power.json`.

Its exact schema records:

- status: `POWERED` or `INSUFFICIENT_POWER`;
- selected sample size and frozen key prefix, or null;
- all constants, formulas, simulation replicate count, and labelled seeds;
- per-family/per-endpoint held-out count, mean, standard deviation, analytic power,
  sensitivity point estimate, exact lower bound, and required size;
- the unanimous fold-selection trace proving held-out use;
- hashes of every development shard and manifest;
- selected-protocol hash;
- protocol, specification, configuration, generator, and generator-manifest hashes;
- source commit, clean-tree assertion, and environment identity.

The script refuses an existing destination, a dirty tree, uncommitted inputs, malformed
or incomplete development artifacts, `NO_SELECTION`, source/provenance drift, or any
attempt to use lockbox outcomes.

## 7. Lockbox and release integration

The selected size is no longer a source-code constant. The guarded lockbox runner must:

1. load the committed power artifact before constructing an oracle or campaign;
2. require status `POWERED` and `350 <= n <= 2000`;
3. accept only the exact prefix `0..n-1` for every frozen lockbox family;
4. bind the power-artifact SHA-256 and selected `n` into every row, sidecar, shard
   manifest, merged manifest, analysis provenance, and release report.

The analyzer and release validator independently hash the actual power artifact, compare
its complete canonical contents to the selected protocol and development provenance, and
require every shard's size/range/count to match it. A copied, altered, absent,
uncommitted, or `INSUFFICIENT_POWER` artifact is a release violation.

The four untouched generator definitions and reserved keys remain frozen and unopened.
Changing the calculator or any power constant after development execution invalidates
all development outputs and requires a clean rerun before selection.

## 8. Failure handling

All production paths fail closed:

- no unanimous selected policy: stop before power planning;
- no eligible `n <= 2000`: freeze `INSUFFICIENT_POWER` and stop before lockbox;
- malformed statistics or a negative/nonfinite variance contract: report the exact
  family and endpoint, then stop; exact zero variance follows the frozen rule in
  Section 3;
- artifact/provenance mismatch: refuse before campaign construction;
- partial write: no completion artifact is installed;
- existing output: refuse rather than overwrite.

No fallback distribution, relaxed margin, pooled-family rescue, post hoc endpoint, or
manual sample-size override is permitted.

## 9. Verification

Tests must prove:

- the analytic formula against independently calculated fixtures;
- zero-variance and `mu >= margin` behavior;
- exact first-passing integer selection and the 350/2,000 boundaries;
- deterministic nonparametric prefixes and independent labelled seeds;
- Clopper-Pearson simulation uncertainty is enforced, including equality at 0.80;
- every family and both endpoints participate in the conjunction;
- held-out fold provenance and unanimous selection are mandatory;
- `INSUFFICIENT_POWER` blocks lockbox access before oracle construction;
- a powered artifact controls exact ranges and counts through merge, analysis, and
  release;
- power-artifact byte tampering, aliasing, relocation, or provenance drift fails;
- no power-planning module imports or reads lockbox outcome artifacts.

Focused tests, full SPADE tests, independent statistical review, and adversarial release
review must pass before development execution.

## 10. Claim boundary

Passing this gate means only that the chosen lockbox size has at least 80% estimated
planning power under both the paired-normal development model and the registered
nonparametric sensitivity rule. It does not prove that unseen lockbox families have the
same effect or variance, and it does not establish SPADE's performance. Performance is
decided only by the untouched lockbox and its prespecified intersection-union analysis.

References:

- Wang Z. *Comparison of Sample Size by Bootstrap and by Formulas Based on Normal
  Distribution Assumption.* Therapeutic Innovation & Regulatory Science. 2019.
  https://doi.org/10.1177/2168479018778280
- Kleinman LC, Huang SS. *Calculating Power by Bootstrap, with an Application to
  Cluster-Randomized Trials.* EGEMS. 2017. https://doi.org/10.13063/2327-9214.1202
