# SPADE PLOS ONE bounded-superiority rewrite

**Status:** approved for planning  
**Date:** 2026-09-20  
**Scope:** rebuild the active PLOS ONE submission package around the current audited evidence

## Goal

Rebuild the SPADE PLOS ONE manuscript and its active supporting documents around the
strongest defensible conclusion:

> SPADE is the better choice when a fixed-well campaign must return a trustworthy
> operating region rather than only one optimized recipe.

The paper will argue for **use-case-specific superiority**, not universal method
superiority. SPADE's advantage is regional: greater certified volume than qLogNEI at
matched five rounds and stronger observed regional containment than the tested DoE
pipelines. The paper will state plainly that DoE found a better point recipe in fewer
rounds and that the evidence does not establish recipe equivalence, manufacturing
qualification, regulatory validation, or prospective wet-lab performance.

## Canonical evidence

The scientific source of truth is the audited publication package on
`codex/paper-ready`, especially:

- `publication/manuscript/MANUSCRIPT.md`
- `publication/manuscript/CLAIMS-AND-SOURCES.md`
- `publication/manuscript/{METHODS,SUPPLEMENT,PROTOCOLS}.md`
- `publication/evidence/manuscript-consistency-audit.md`

The active PLOS submission package under `manuscript/` will be rebuilt from those
materials rather than patched from its older scientific narrative.

The rewrite must use these corrected primary values:

- SPADE R5 versus qLogNEI R10 regret: `-0.0005`, 95% CI
  `[-0.0221, +0.0207]`, `p=0.96`, `n=160`; wording:
  **no detectable difference**, not equivalence or parity.
- SPADE versus qLogNEI at matched R5 certified volume:
  `+0.000855`, 95% CI `[+0.000691, +0.001028]`, `p<0.0001`,
  `n=320` dependent family-seed-prevalence cells under registered LOFO
  calibration.
- SPADE versus tested screened DoE point regret:
  SPADE-minus-DoE `+0.1026`, 95% CI `[+0.0486, +0.1578]`,
  `p=0.0003`; DoE is better on the point recipe and uses three rounds
  versus SPADE's five.
- At prevalence `0.30`, noise `0.25`, assurance `0.95`, 48 wells, and
  five families x 32 seeds: SPADE answered 66/160 and contained 66/66;
  screened DoE answered 122/160 and contained 85/122; unscreened DoE
  answered 134/160 and contained 77/134.
- Hill at prevalence `0.70`: SPADE answered 40/64 and contained 40/40,
  lower bound `0.9278`; qLogNEI also had perfect observed containment
  at 27/27, below the registered answer-count requirement.

The stale active-PLOS values `+0.0016` and `+0.001353` must not appear as
current conclusions.

## Narrative architecture

### Title and abstract

The title and abstract will lead with the decision problem: one recipe versus a
trustworthy operating region. They will state that SPADE is better **for the regional
deliverable under the tested conditions**. The abstract will include the adverse DoE
point result and the no-detectable-difference qLogNEI result so that “better” cannot be
misread as universal superiority.

### Introduction

The introduction will frame three method-selection cases:

1. use point optimization when one recipe is the deliverable;
2. use SPADE when an operating region and principled abstention are required;
3. do not expect any method to overcome the retained real-noise ceiling without
   replication.

Prior work on GP level sets, conservative excursion sets, BO, and RSM remains explicit.
SPADE is positioned as an assay-oriented workflow and evidence package, not a new
excursion-set theory.

### Methods

Methods will accurately describe:

- 48 wells for every synthetic arm;
- the five-round SPADE schedule and comparator schedules;
- posterior conservative-region construction and abstention;
- certified volume, answer rate, truth containment, and point regret as distinct
  estimands;
- LOFO calibration for the qLogNEI matched-round comparison;
- within-sample calibration/fallback limitations in the DoE comparison;
- the flat-cell bootstrap and pooled-binomial dependence assumptions;
- Joseph's mean-marginalisation correction as uncertainty propagation, not an
  optimization improvement.

Any statement that SPADE uses a genuinely threshold-directed acquisition must be checked
against the theta-cancellation and target-alignment findings. The value proposition will
be architectural rather than attributed to a targeting mechanism that failed adoption.

### Results

Results will be ordered by the decision the reader must make:

1. matched five-round operating-region result against qLogNEI;
2. five-round SPADE versus ten-round qLogNEI point result;
3. the DoE trade-off: better recipe, unreliable observed region;
4. Hill and margin-to-noise scope;
5. Joseph's real-data posterior-collapse diagnosis and mean-marginalisation fix;
6. failed targeting, real-noise ceiling, abstention, and negative joint-protocol stop.

Every certification claim will locally state its denominator and relevant prevalence,
noise, assurance, wells, rounds, seeds, and calibration rule, or point to a table that
contains all dimensions.

### Discussion and conclusion

The paper will explicitly distinguish:

- **better for operating-region decisions** — supported;
- **better point optimizer** — contradicted by DoE and unsupported against qLogNEI;
- **equivalent to qLogNEI on point regret** — not established;
- **manufacturing-qualified or wet-lab validated** — not established.

The conclusion will give a method-selection recommendation rather than a universal
ranking: choose SPADE when the decision requires a conservative region and honest
abstention under a fixed-well, moderate-noise campaign; choose a point optimizer when the
decision only requires one recipe.

## Submission package scope

Rebuild and synchronize:

- `manuscript/SPADE-PLOS-ONE.md`
- generated `manuscript/SPADE-PLOS-ONE.docx` and manifest
- `manuscript/SPADE-PLOS-ONE-cover-letter.md`
- generated cover-letter DOCX and manifest
- active claim/source and submission-readiness summaries that repeat the paper thesis
- consistency guards and tests needed to reject stale values and forbidden wording

Author identities, affiliations, correspondence details, CRediT roles, licensing,
repository links, and DOI/submission placeholders will be reconstructed from the current
submission package and verified rather than silently discarded.

## Claim controls

Automated checks will reject:

- stale current values `+0.0016` and `+0.001353`;
- unqualified “SPADE is better/best” wording;
- “SPADE matches/is equivalent to qLogNEI” wording;
- “SPADE beats DoE” without naming the regional endpoint;
- “DoE cannot certify” without answered/contained context;
- manufacturing, regulatory, or prospective wet-lab superiority claims;
- omission of the real-noise ceiling from the limitations.

Positive allowed wording will be pinned around:

> SPADE performed better for the tested operating-region decision: at matched five
> rounds it returned greater certified volume than qLogNEI, and in the DC comparison
> its answered regions had stronger observed truth containment than the tested DoE
> pipelines.

## Verification

Completion requires:

1. current conclusion guards and manuscript-specific tests pass;
2. the canonical analysers reproduce C1, C2, C3, C5, C6, and the adverse/null results
   retained in the manuscript;
3. the Markdown-to-DOCX build succeeds and manifests match generated files;
4. repository search finds no stale current headline values or forbidden conclusion
   wording in active submission documents;
5. a final diff review confirms no unrelated existing work was overwritten.

## Non-goals

- No new simulation, wet-lab analysis, or re-adjudication of frozen studies.
- No claim that SPADE is universally superior.
- No suppression of adverse, null, withdrawn, or `NO_SELECTION` results.
- No conversion of posterior assurance into a frequentist or regulatory guarantee.
- No rewriting of archived historical records merely to make them agree with the current
  paper.
