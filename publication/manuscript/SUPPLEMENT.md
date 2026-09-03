# Supplementary evidence and limitations

## S1. Claim status table

| ID | Status | Evidence |
|---|---|---|
| C1 | Main, bounded | DC one-process regret, `-0.0005`, CI crosses ±0.02 edge |
| C2 | Main, adverse result included | DoE wins regret; SPADE alone has perfect observed containment |
| C3 | Main, corrected | LC LOFO volume `+0.000855`; stale `+0.001353` rejected |
| C4 | Main | SPADE R3 minus one-shot LHS regret `-0.0783` |
| C5 | Main, explanatory | SPADE, `c=1.0`: mean seed-specific margin/noise rho `0.9880098603` over 25 nested cells; truth-dependent diagnostic |
| C6 | Main subgroup within C5 | Hill p=0.70: 40 answered, 40 contained |
| S1 | Support/negative | corrected targeting does not improve aggregate volume and harms regret |
| S2 | Support | posterior-width collapse on in-house and published assays |
| S3 | Support | assay-specific leave-one-out inflation |

## S2. Required reporting dimensions

Every certificate table must state family, target prevalence, relative noise, assurance,
inflation-selection rule, wells, rounds, seeds, answered count, contained count, containment
fraction, and lower confidence bound. A zero or small answer count is abstention or
insufficient denominator, not proof that a family or optimizer cannot certify.

## S2a. Complete experiment inventory

| Study | Evidence role | Design | Current use |
|---|---|---|---|
| DC | Confirmatory/core | Five families × 32 seeds; SPADE R5, qLogNEI R10, two three-round DoE arms; 48 wells | C1 and C2 |
| LC | Confirmatory/core | Five families × 32 seeds × two prevalences; matched SPADE/qLogNEI R5; LOFO inflation | C3 and SPADE side of C4 |
| LA | Frozen development lineage | Four families × 20 matched seeds; one-shot 48-well LHS | C4 only |
| TAU | Confirmatory/core descriptive gate | Five families × 64 seeds × five prevalences; SPADE/qLogNEI R5 | C5 and C6 |
| TT | Frozen negative mechanism test | Five families × 32 seeds; committed, retargeted SPADE, and qLogNEI R5 | S1 |
| In-house iPSC-EC | Retrospective support | Derived candidate table linked to an evidence subset; unsigned CD31 gates | S2/S3 only |
| Hall/Ogle | Retrospective published-data support | Canonical stage-1/stage-2 extraction | S2/S3 only |

Machine-readable paths, producers, analysers, and guard coverage are in
`../evidence/benchmark-matrix.md` and `../evidence/reproduction-map.md`.

## S3. Hill and cross-family interpretation

Hill was initially almost always empty at difficult targets. The prevalence sweep showed that
SPADE answer rate was descriptively associated with mean seed-specific target margin relative
to multiplicative noise (rho `0.9880098603`). The median-margin sensitivity gave the same rho;
the qLogNEI-only mean-margin sensitivity gave rho `0.9682461469`. The 25 cells are nested and
dependent, so a naive correlation p-value is not population inference. At p=0.70, SPADE
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

## S6a. Superseded and non-promoted findings

| Finding | Disposition | Reason |
|---|---|---|
| LC parity estimate `+0.0016` | Superseded | DC provides the one-process C1 comparison. |
| C3 volume `+0.001353` | Rejected | No frozen analyser/input combination reproduces it; current value is `+0.000855`. |
| C3 at R3 | Withdrawn | Seed extension did not retain the registered effect. |
| Original C5 rho `0.9801` | Superseded | The loader overwrote seed-varying Hill margins and pooled arms; repaired SPADE-only rho is `0.9880098603`. |
| Target-at-`tau` acquisition | Not adopted | Volume CI crossed zero and regret worsened. |
| Real-cell width/calibration values | Supporting, unguarded | Scripts reproduce them, but no structured canonical result objects guard them. |
| Noise ceiling near `0.68` | Required limitation | Preserved exploratory evidence; absent from the active scalar guard. |

Existing polished figures belong to earlier studies and are not current-manuscript evidence.
The present submission uses in-text Tables 1–3. If a selected journal requires figures, a new
package must be generated from the current canonical results with captions, alt text, source
data, and status metadata.

## S7. Audit and archive

The pre-consolidation baseline contains 719 commits and 1,402 tracked files. The commit ledger
records chronology and correction chains; the file ledger records the scientific role and
destination of every file. Historical material was moved, not deleted. Ignored local bulk
outputs that were never versioned are retained outside the active tree with sizes and SHA-256
hashes in `archive/generated/local-untracked-manifest.csv`.
