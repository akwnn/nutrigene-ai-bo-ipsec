# Registered synthetic benchmark for SPADE multi-CQA qualification

**Status:** registered synthetic evaluation protocol  
**Date:** 2026-08-27  
**Parent implementation:** `manufacturing_qualification.py`  
**Claim scope:** computational method behavior only; no wet-lab or biological-transfer claim

## 1. Question

Does intersecting endpoint certificates improve manufacturing safety relative to
certifying the primary CQA alone, when both methods receive exactly the same
recipes, noisy observations, model family, candidate grid, and computational
budget?

The comparison is not a claim that joint qualification improves point regret. Its
primary question is whether the scalar workflow releases recipes that fail an
unmodeled release attribute, and how much qualified volume/answer rate is traded
for that protection.

## 2. Registered methods

### Scalar-primary baseline

Fit the existing scalar GP to the identity CQA only. Use the same candidate grid,
sealed assay noise, `gamma=0.95`, `alpha=0.95`, draw count, Vorob'ev grid, and
`volume_rule="smallest"` as the joint method. The issued mask is evaluated against
the truth intersection of all three CQAs, but truth is never used for fitting or
selection.

### Joint-CQA overlay

Run `qualify_multi_cqa` with identity, viability, and yield columns. The endpoint
confidence is Bonferroni-adjusted to
`1 - (1 - 0.95) / 3 = 0.983333...`; the issued mask is the exact intersection.

Both methods use 48 observed recipes and score one shared 4,096-point candidate
grid. Each replicate has one deterministic Sobol design and one indexed assay-noise
stream. A replicate is paired: scalar and joint masks see byte-identical inputs.

## 3. Synthetic CQA families

All factors are coded to `[0, 1]^6`. Each CQA is a smooth, bounded response:

```text
f_j(x) = exp(-w_j * ||x - c_j||²)
```

The remaining coordinates are inert, making the dimension stress explicit. The
three registered families are:

| family | CQA centers | purpose |
|---|---|---|
| `aligned` | centers within 0.05 of `(0.5, 0.5, 0.5)` | joint region should usually exist |
| `moderate_conflict` | centers `(0.35,0.40,0.50)`, `(0.60,0.55,0.45)`, `(0.48,0.35,0.62)` | tests volume loss and limiting CQA |
| `strong_conflict` | centers `(0.18,0.28,0.40)`, `(0.76,0.70,0.60)`, `(0.45,0.20,0.82)` | tests safe abstention when intersection is unsupported |

Widths are fixed at `w=(5.0, 5.0, 5.0)` for the base registration. A later
sensitivity study may vary widths only under a new protocol version.

## 4. Assay and release registration

- `sigma_rel=0.04`, `sigma_add=0.01` for all CQAs.
- Observations use indexed relative-plus-additive Gaussian noise; noise indices are
  keyed by replicate and recipe index, not call order.
- Release thresholds are `0.50` for all three synthetic CQAs.
- Endpoint reliability is `gamma=0.95`.
- Overall certificate containment target is `alpha=0.95`.
- Empty joint regions are `ABSTAIN_EMPTY_JOINT`, never a failed recipe or a scalar
  fallback.

## 5. Primary endpoints

For each method, family, and replicate report:

1. joint truth containment (whether issued mask is a subset of the all-CQA truth);
2. unsafe-release rate: issued grid points outside the all-CQA truth divided by
   issued points (undefined, not zero, for an empty mask);
3. answer rate / non-empty certificate indicator;
4. issued volume and absolute grid-point count;
5. scalar-primary truth containment as a diagnostic for the baseline;
6. joint method limiting CQA and endpoint volumes.

Aggregate by family over the registered replicate set. Report medians, interquartile
ranges, and paired differences. Do not pool grid points as independent replicates.

## 6. Replicates and lockbox separation

The registered development run is 25 replicates per family, each with two algorithm
seeds averaged at the replicate level (`n=25` paired observations per family). The
first implementation smoke run may use `--replicates 1` or `--replicates 3`, but
those outputs are exploratory and cannot be quoted as confirmatory evidence.

The strong-conflict family is not a “failure” if the joint method abstains; the
predeclared endpoint is safety/abstention behavior. Any future confirmatory result
must use fresh vector-valued families and a new protocol digest. Existing scalar
SPADE lockbox artifacts are not reused.

## 7. Interpretation boundary

The joint overlay is expected to reduce unsafe releases, sometimes by shrinking or
emptying the region. That is a manufacturing-safety tradeoff, not proof of general
optimizer superiority. The paper may claim only the observed computational behavior
under this registered generator and parameter regime. It must not describe these
surfaces as fitted ESC-to-EC biology or imply that a synthetic joint certificate is
a validated GMP release criterion.

## 8. Reproducibility contract

Every output records protocol digest, source commit, family, replicate/algorithm
seeds, dimension, training count, grid count, noise law, thresholds, alpha/gamma,
draw count, and volume rule. JSON is canonical and finite; no NaN metrics are
serialized. A rerun with the same source commit and arguments must reproduce every
row byte-for-byte.
