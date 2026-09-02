# SPADE multi-CQA manufacturing qualification overlay

**Status:** approved design; implementation pending review of this document  
**Date:** 2026-08-27  
**Parent method:** SPADE (`src/boec/spade.py`)  
**Scope:** computational / synthetic qualification only; no wet-lab, GMP, or biological-efficacy claim

## 1. Problem and intended value

The active SPADE recovery campaign is repairing the scalar certificate: one learned
response, one threshold, and one qualified operating region. Cell manufacturing
does not release a recipe on one marker alone. An ESC-to-EC process normally has
several quality attributes (for example endothelial identity, viability, and yield)
that must all meet their release limits.

This change adds a **scorer-side multi-CQA qualification overlay**. It evaluates a
common recipe grid against one independently fitted scalar surrogate per CQA, then
intersects the CQA certificates. The result is a manufacturing-readable answer:

> which recipe region is simultaneously qualified for every registered attribute,
> which attribute limits that region, and whether a usable setpoint exists inside it?

The overlay is deliberately separate from the active Cursor recovery. It must not
change the scalar SPADE model, LOO-tail calibration, running campaign, or lockbox
artifacts.

## 2. Claims and non-claims

### 2.1 Permitted claim

For a fixed grid, fixed CQA definitions, and registered endpoint certificate
procedure, the overlay reports the intersection of endpoint reliable sets. The
family-wise certificate target is controlled by a Bonferroni/union-bound allocation
of the overall confidence level across CQAs.

The output may say that a recipe lies in the **computational joint certificate**
only when every endpoint certificate includes it. It may identify the limiting CQA
as the endpoint with the smallest certified volume (ties are deterministic).

### 2.2 Explicit non-claims

This phase does **not** claim that future batches jointly pass all CQAs with the
reported confidence. Separate endpoint GPs do not model cross-CQA correlation, and
certificate containment is not the same estimand as joint batch pass probability.
A joint predictive-pass claim requires a later multivariate model and a new
registered protocol.

This phase does not claim ESC-to-EC biological performance from the current local
lab drop. The repository data are unsigned, mostly single-replicate, and do not
contain a validated yield/viability panel. Real manufacturing claims require signed,
compensated, repeated measurements and prospective lockbox families.

## 3. Scope boundary and files

Only these new files are in scope for implementation:

- `src/boec/manufacturing_qualification.py` — public data contracts, validation,
  per-CQA scoring, intersection, and reporting.
- `tests/test_manufacturing_qualification.py` — unit and contract tests.
- `configs/experiment/spade-multi-cqa-qualification.yaml` — synthetic registered
  defaults and an explicit example CQA registry.

No edits are made to `src/boec/spade.py`, `src/boec/spade_study.py`,
`src/boec/reliable_region.py`, `src/boec/selfcalib.py`, existing experiment configs,
or any active `results/` files. The overlay may call stable existing primitives
(`surrogate`, `reliable_region`, and `vorobev`) but owns its multi-CQA orchestration.

## 4. Input contract

The implementation accepts observed training recipes, measurements, and a shared
candidate grid:

- `X`: finite floating tensor/array of shape `(n, d)`, one observed recipe per row
  and one shared factorization/order for all CQAs.
- `Y`: finite floating tensor/array of shape `(n, m)`, one observed CQA column per
  recipe. `m >= 2` for this overlay; scalar SPADE remains the existing path.
- `Yvar`: finite, strictly positive tensor/array of shape `(n, m)` giving known
  observation variances. It is not silently replaced by a learned noise estimate.
- `grid`: finite floating tensor/array of shape `(n_grid, d)` on which certificates
  are issued. It uses the same factor bounds and column order as `X`; if omitted,
  the implementation uses `X` as a convenience fallback.
- `cqas`: an ordered tuple of exactly `m` definitions.

Each `CqaDefinition` contains:

| field | requirement |
|---|---|
| `name` | non-empty stable identifier, unique within the registry |
| `units` | non-empty manufacturing/reporting unit string |
| `threshold` | finite release limit in the same units as `Y[:, j]` |
| `direction` | `"greater_equal"` for `Y >= threshold` or `"less_equal"` for `Y <= threshold` |
| `gamma` | open probability in `(0, 1)`, endpoint reliability threshold |
| `assay_id` | stable assay identity (instrument + marker/panel + date family as applicable) |
| `assay_version` | non-empty version/gating/analysis identifier |
| `sigma_rel`, `sigma_add` | non-negative sealed relative/additive future-observation noise parameters; both required together |

The registry is the source of truth for thresholds and assay identity. Thresholds
must be fixed before fitting/scoring; no threshold is inferred from the observed
maximum, posterior, or selected recipe. Because a plain matrix has no semantic
column labels, callers must pass columns in the declared registry order; an
optional `cqa_names` vector can be used to verify that order at runtime.

The initial example registry may use identity, viability, and yield names to show
the ESC-to-EC manufacturing shape, but synthetic fixture values must be labelled as
such. The generic implementation does not special-case biological markers.

## 5. Statistical procedure

For each CQA `j`, in registry order, fit on the observed `X`/`Y[:, j]` rows and
score the resulting certificate on the shared `grid`:

1. Validate `X`, `Y[:, j]`, `Yvar[:, j]`, and the definition. Reject shape,
   non-finite, non-positive variance, duplicate-name, mixed-assay, or incomplete
   metadata errors before fitting any model.
2. Fit one scalar GP using the existing SPADE surrogate construction and the CQA
   column only. There is no implicit multi-output covariance.
3. Convert a lower-tail endpoint to the existing greater-than event by sign
   transformation (`Y <= tau` becomes `-Y >= -tau`) while preserving the original
   reporting direction and units. This transformation is internal only; reports
   retain the original CQA direction.
4. Use the sealed CQA assay noise law (`sigma_rel`, `sigma_add`) for predictive
   reliability and joint latent draws. Learned homoskedastic likelihood noise is
   not the registered overlay path.
5. Generate deterministic joint reliable-set draws on the shared grid, using a
   CQA-derived seed from the registered base seed. Use the existing latent
   inflation value only when explicitly supplied by the caller; the overlay default
   is `1.0` so it cannot silently reuse a campaign-specific calibration.
6. Select the endpoint certificate with the existing split/Vorob'ev machinery and
   the registered `certificate_volume_rule` (`smallest` by default). A certificate
   is a boolean mask over the shared grid.

For an overall certificate confidence `alpha` and `m` CQAs, allocate

```text
alpha_endpoint = 1 - (1 - alpha) / m
```

to every endpoint. This union-bound allocation is valid without assuming endpoint
independence. The implementation records both `alpha` and the allocated value in
the result so a report cannot be mistaken for an unadjusted scalar certificate.

The joint manufacturing certificate is the exact boolean intersection:

```text
joint_mask = endpoint_mask[0] & endpoint_mask[1] & ... & endpoint_mask[m - 1]
```

No soft averaging, weighted score, majority vote, or fallback to the primary CQA is
allowed. An empty intersection is a valid **ABSTAIN** result.

## 6. Setpoint policy

The overlay may optionally receive a scalar utility vector (for example a primary
CQA posterior mean) and choose one setpoint from `joint_mask`. Selection is always
constrained to the joint certificate. Ties are broken by lexicographic grid index,
which makes reports reproducible.

If no utility is supplied, the result contains the joint region but no setpoint.
If `joint_mask` is empty, the setpoint is `None` and status is `ABSTAIN_EMPTY_JOINT`.
It is a correctness failure to return a recipe outside the intersection merely to
avoid abstention.

## 7. Output contract

The public result is immutable or treated as immutable after construction and
contains:

- `status`: `QUALIFIED` or `ABSTAIN_EMPTY_JOINT` (validation failures raise).
- `grid`: the validated shared `(n, d)` grid.
- `alpha`, `alpha_endpoint`, `gamma` values, and the registered protocol/config
  digest.
- `endpoint_results`: one record per CQA with definition identity, certificate mask,
  certified volume (`mask.mean()`), posterior/reliability summary, and endpoint
  empirical containment when truth is supplied for a synthetic evaluation.
- `joint_mask`, `joint_volume`, and `limiting_cqa` (minimum endpoint volume;
  deterministic name-order tie break).
- optional `setpoint_index`, `setpoint`, and utility value.
- deterministic seeds and model/protocol provenance sufficient to reproduce the
  result.

Truth masks are optional and evaluation-only. They must never be used to fit the
  model or to choose the certificate. When supplied, endpoint and joint empirical
  containment are reported separately from the model-internal certificate.

## 8. Fail-closed rules

The overlay raises a clear validation error for malformed inputs and returns an
abstaining result for an empty joint region. It must also fail closed when:

- an optional `cqa_names` vector disagrees with the registry order (without labels,
  column order is a caller responsibility);
- assay identity/version is missing or inconsistent within a CQA;
- an upper-limit CQA is accidentally scored as a lower-limit CQA;
- a noise parameter is negative, non-finite, or supplied without its pair;
- a supplied utility or truth mask has the wrong grid shape;
- a caller requests a scalar result through the multi-CQA API (`m < 2`).

There is no automatic imputation, threshold learning, hidden normalization, or
fallback to unsigned local lab candidates.

## 9. Determinism and reproducibility

The base seed, CQA registry order, grid order, model configuration digest, and
per-CQA derived seeds are recorded. Reordering the input columns together with the
registry must produce the same named endpoint results; changing the registry order
without changing columns must raise. The implementation must not mutate caller
arrays/tensors or the existing scalar SPADE model.

## 10. Test-first acceptance criteria

Before implementation is considered complete, tests must cover:

1. valid `(X, Y, Yvar, cqas)` construction and output fields;
2. shape, NaN/Inf, non-positive variance, duplicate-name, missing metadata, and
   incomplete noise-pair rejection;
3. lower-tail sign handling and preservation of original reporting direction;
4. exact Bonferroni allocation, including `m=3, alpha=.95`;
5. exact boolean intersection and endpoint/joint volume calculations;
6. empty-intersection abstention with no setpoint;
7. deterministic limiting-CQA and lexicographic setpoint tie-breaking;
8. setpoint selection never leaving the joint mask;
9. reproducibility under repeated runs and input immutability, including matching
   named outputs when columns and registry are permuted together;
10. optional truth-mask reporting not affecting fit or mask selection;
11. configuration defaults (`smallest`, assay noise, explicit seed) and no edits to
    active scalar files.

Fixtures use small deterministic synthetic ESC-to-EC-like CQAs. They are tests of
the algorithm, not evidence for a biological claim.

## 11. Prospective evidence needed after this phase

To make a manufacturing-facing claim, a later registered study must provide signed
and compensated identity data plus at least the CQAs actually used for release
(typically identity, viability, and yield), repeated across donor/lot/passages.
Development families must remain separate from untouched lockbox families. The
study must report per-CQA and joint containment, empty-certificate rate, joint
volume, limiting CQA, setpoint regret, and rounds/passages. Until that study passes,
the manuscript may describe this overlay as a computational design improvement only.

## 12. Definition of done for this design

The design is ready for implementation when the reviewer agrees that (a) the
intersection is the only release region, (b) Bonferroni controls the stated
certificate-containment family-wise target, (c) no joint pass-probability claim is
implied, and (d) the active scalar Cursor campaign remains isolated. Implementation
then proceeds in a separate plan and test-first work cycle.
