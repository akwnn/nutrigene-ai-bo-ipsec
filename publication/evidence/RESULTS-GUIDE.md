# Results and evidence guide

This page explains the current evidence without making readers open a folder for each result.
Exact allowed wording and values are in
[`CLAIMS-AND-SOURCES.md`](../manuscript/CLAIMS-AND-SOURCES.md); executable commands are in
[`reproduction-map.md`](reproduction-map.md). The complete program-by-program dimensions,
producers, analysers, and guard coverage are in [`benchmark-matrix.md`](benchmark-matrix.md).

## Method comparisons

- **C1/C2:** `research/results/comparisons/dc-*.json` compares SPADE, qLogNEI, screened DoE, and
  unscreened DoE in one process. C2 chooses inflation within the DC cells separately by arm;
  it is not a held-out calibration result.
- **C3:** `research/results/comparisons/lc-*.json` contains the matched five-round certified-volume
  comparison. Its n=320 comprises five families x 32 seeds x both p=.30 and p=.10 cells.
- **C4:** SPADE three-round rows in `research/results/comparisons/lc-*.json` pair with one-shot LHS rows
  in `research/results/comparisons/la-*.json`; n=80 is four families x 20 matched seeds.

All headline comparisons use 48 wells but not the same number of rounds: SPADE uses five
rounds for C1–C3, qLogNEI uses ten rounds for C1 and five for C3, DoE uses three for C2, and
LHS uses one for C4. No calendar-time or monetary saving was measured.

## Cross-family generalization

`research/results/generalization/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json` supports C5 and C6.
At `c=1.0` and `alpha=0.95`, SPADE answer rate tracks mean seed-specific margin relative to
noise (descriptive rho `0.9880098603`, 25 nested family-prevalence cells); median margin gives
the same rho and qLogNEI-only mean margin gives `0.9682461469`. Dependence and lack of
population exchangeability rule out naive p-value inference. Hill
remains inside the five-family analysis and is reported separately as the biologically shaped
case.

## Mechanism test

`research/results/mechanism/tt-*.json` supports S1. Correcting the targeting threshold changes certified
volume by only `+0.000425` with a confidence interval crossing zero and worsens regret by
`+0.0301`; the added mechanism therefore is not claimed as an improvement. These values are
reproduced by the TT analyser but are not in the numeric conclusion guard.

## Real-cell support

The in-house iPSC-EC and Hall–Ogle analyses support the uncertainty argument but are not a
prospective wet-lab validation of SPADE. The in-house data remain
`awaiting_human_signoff`, and the CD31 gates require manual review. S2/S3 outputs are currently
stdout-only: there are no canonical structured result objects or numeric guards for the quoted
width ratios and assay-specific inflation values.

## Required limitations

The manuscript must retain the real-noise ceiling, provisional in-house status, answer-count
denominators, and untested-method scope. Failed evidence is preserved under `archive/void/`;
valid off-paper experiments remain indexed in `file-review.csv`.

## Reviewer-facing safeguards

The main safeguards are executable: the one-process DC result supersedes the earlier
cross-run comparison; C3 uses the frozen leave-one-family-out calculation rather than stale
prose; Hill stays in the five-family result; and certification reports both answered and
contained counts. `software/scripts/verify_conclusions.py` guards 12 selected scalars for C1,
C3, C4, C5, and C6; it is not an exhaustive manuscript-number guard. C2 and S1 have standalone
analysers, while S2, S3, and L1 still lack complete active structured guard paths.
