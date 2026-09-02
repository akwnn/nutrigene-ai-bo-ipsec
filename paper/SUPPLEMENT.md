# Supplementary evidence and limitations

## S1. Claim status table

| ID | Status | Evidence |
|---|---|---|
| C1 | Main, bounded | DC one-process regret, `-0.0005`, CI crosses ±0.02 edge |
| C2 | Main, adverse result included | DoE wins regret; SPADE alone has perfect observed containment |
| C3 | Main, corrected | LC LOFO volume `+0.000855`; stale `+0.001353` rejected |
| C4 | Main | SPADE R3 minus one-shot LHS regret `-0.0783` |
| C5 | Main, explanatory | margin/noise rho `0.9801`; truth-dependent diagnostic |
| C6 | Main subgroup within C5 | Hill p=0.70: 40 answered, 40 contained |
| S1 | Support/negative | corrected targeting does not improve aggregate volume and harms regret |
| S2 | Support | posterior-width collapse on in-house and published assays |
| S3 | Support | assay-specific leave-one-out inflation |

## S2. Required reporting dimensions

Every certificate table must state family, target prevalence, relative noise, assurance,
inflation-selection rule, wells, rounds, seeds, answered count, contained count, containment
fraction, and lower confidence bound. A zero or small answer count is abstention or
insufficient denominator, not proof that a family or optimizer cannot certify.

## S3. Hill and cross-family interpretation

Hill was initially almost always empty at difficult targets. The prevalence sweep showed that
this was controlled by target margin relative to multiplicative noise. At p=0.70, SPADE
answered 40/64 with 40/40 containment. Hill remains one of five families in the rank analysis;
its separate subsection is interpretation, not removal from the denominator. The response is
biology-shaped but synthetic, so it supports structural plausibility rather than biological
validation.

## S4. Mechanism test

Replacing the historical acquisition threshold with the actual p=0.30 threshold changed
certified volume by `+0.000425`, with CI crossing zero, and worsened regret by `+0.0301`.
Hartmann6 improved while Ackley worsened. The registered adoption guard therefore failed.
The original acquisition remains the active method; no post-hoc targeting variant is promoted.

## S5. Real-cell evidence boundaries

The in-house data role manifest identifies primary flow files, gating controls, matched
morphology, protocols, sidecars, blocked files, assay-development files, and material not for
BO. Only the first evidence-linked groups remain in the active support path. The derived
candidate campaign is `awaiting_human_signoff`; unsigned or ambiguous CD31 gates cannot enter
an optimization claim.

The Hall/Ogle extraction provides an independent assay shape and processing check. It does not
re-evaluate the source study's conclusions. Mean marginalization widened posterior uncertainty
297× in the published data and 484× in-house. LOO inflation differed by assay (`0.526` and
`0.712`). LOO predicts held-out observations, not latent truth, so replicate tubes remain the
required route to independent noise identification.

## S6. Negative and unresolved scope

- At real-assay relative noise near 0.68, no tested arm certifies.
- R=4 and a broader assurance/rho sweep are untested.
- Only one 48-well budget is confirmatory; larger budgets require a new matched protocol.
- The DoE arm is a particular low-order screen-plus-response-surface pipeline.
- Calendar duration, labor, and monetary cost were not measured.
- The C3 R3 effect was withdrawn after seed extension.
- The targeting mechanism did not earn adoption.
- Prospective wet-lab SPADE validation remains open.

## S7. Audit and archive

The pre-consolidation baseline contains 719 commits and 1,402 tracked files. The commit ledger
records chronology and correction chains; the file ledger records the scientific role and
destination of every file. Historical material was moved, not deleted. Ignored local bulk
outputs that were never versioned are retained outside the active tree with sizes and SHA-256
hashes in `archive/generated/local-untracked-manifest.csv`.
