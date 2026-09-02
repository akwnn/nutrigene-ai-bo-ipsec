# Results and evidence guide

This page explains the current evidence without making readers open a folder for each result.
Exact allowed wording and values are in
[`CLAIMS-AND-SOURCES.md`](../manuscript/CLAIMS-AND-SOURCES.md); executable commands are in
[`reproduction-map.md`](reproduction-map.md).

## Method comparisons

- **C1/C2:** `research/results/comparisons/dc-*.json` compares SPADE, qLogNEI, screened DoE, and
  unscreened DoE in one process.
- **C3:** `research/results/comparisons/lc-*.json` contains the matched five-round certified-volume
  comparison.
- **C4:** SPADE three-round rows in `research/results/comparisons/lc-*.json` pair with one-shot LHS rows
  in `research/results/comparisons/la-*.json`.

All headline comparisons use 48 wells but not the same number of rounds: SPADE uses five
rounds for C1–C3, qLogNEI uses ten rounds for C1 and five for C3, DoE uses three for C2, and
LHS uses one for C4. No calendar-time or monetary saving was measured.

## Cross-family generalization

`research/results/generalization/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json` supports C5 and C6.
Answer rate tracks margin relative to noise (rho `0.9801`, 25 family-prevalence cells). Hill
remains inside the five-family analysis and is reported separately as the biologically shaped
case.

## Mechanism test

`research/results/mechanism/tt-*.json` supports S1. Correcting the targeting threshold changes certified
volume by only `+0.000425` with a confidence interval crossing zero and worsens regret by
`+0.0301`; the added mechanism therefore is not claimed as an improvement.

## Real-cell support

The in-house iPSC-EC and Hall–Ogle analyses support the uncertainty argument but are not a
prospective wet-lab validation of SPADE. The in-house data remain
`awaiting_human_signoff`, and the CD31 gates require manual review.

## Required limitations

The manuscript must retain the real-noise ceiling, provisional in-house status, answer-count
denominators, and untested-method scope. Failed evidence is preserved under `archive/void/`;
valid off-paper experiments remain indexed in `file-review.csv`.

## Reviewer-facing safeguards

The main safeguards are executable: the one-process DC result supersedes the earlier
cross-run comparison; C3 uses the frozen leave-one-family-out calculation rather than stale
prose; Hill stays in the five-family result; and certification reports both answered and
contained counts. `software/scripts/verify_conclusions.py` guards the headline values.
