# Consolidated frozen protocols

This is the active protocol index. Original protocol-plus-result narratives are preserved
unchanged under `archive/superseded-spade/docs/`. The hashes below identify registrations
made before their result data; the commit ledger records later results and corrections.

## DC — SPADE, BO, and classical DoE

**Frozen commit:** `8568a449ccf261a3ea19fb9caacd67d761c3f2ac`  
**Code:** `software/scripts/run_dc_doe_certificate.py`, `software/scripts/analyse_dc_doe_certificate.py`  
**Data:** `research/results/comparisons/dc-{ackley,hartmann6,hill,levy,rosenbrock}.json`

Five families × 32 seeds × 48 wells; relative noise 0.25; prevalence 0.70/0.30;
assurance 0.95; inflation `{1.0,1.5,2.0,3.0}`. Arms are screened DoE (3 rounds),
unscreened DoE (3), SPADE (5), and qLogNEI (10), all scored through the same GP and
certificate. Primary gate: SPADE meets lower bound 0.90 at answer rate 0.05 while DoE does
not. A DoE regret win is a registered adverse headline. The screen comparison tests whether
screening causes containment failure.

## LA — round-matched and one-shot comparison

**Frozen commit:** `4cbe17e0919e4baa66e9117b96c70420c4ac2bfc`  
**Code:** `software/scripts/run_la_round_matched.py`, `software/scripts/analyse_la_round_matched.py`  
**Data:** `research/results/comparisons/la-{ackley,hartmann6,levy,rosenbrock}.json`

Forty-eight wells compare two-plate SPADE, qLogNEI at matched and longer schedules, a
historical Version-B arm, and one-shot LHS. C4 pairs LHS with SPADE R3 rows from LC on common
family/seed keys; unmatched families are not imputed.

## LC — confirmatory BO and matched-round comparison

**Frozen commit:** `19f845a7f7757b0c985b365ceb1ecbe69b984b61`  
**Code:** `software/scripts/run_lc_confirmatory.py`, `software/scripts/analyse_lc_confirmatory.py`  
**Data:** `research/results/comparisons/lc-{ackley,hartmann6,hill,levy,rosenbrock}.json`

Five families, extended to 32 seeds, 48 wells, relative noise 0.25, assurance 0.95, and
inflation `{1.0,1.5,2.0,3.0}`. Configurations are SPADE R3/R5 and qLogNEI R3/R5/R10.
Inflation is selected leave-one-family-out. The regret SESOI is ±0.02. R4 remains untested.
DC supersedes LC for C1; LC remains canonical for C3 and the SPADE side of C4.

## TAU — target prevalence and cross-family generalization

**Frozen commit:** `0c21304dfbb471ce7709e49933b6f7d8c8164ed4`  
**Code:** `software/scripts/run_tau_sweep.py`, `software/scripts/analyse_tau_sweep.py`  
**Data:** `research/results/generalization/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json`

Five families × 64 seeds × SPADE/qLogNEI at R5; prevalence
`{0.70,0.50,0.30,0.20,0.10}`; 48 wells; relative noise 0.25; assurance 0.95. Primary gate:
at `c=1.0`, Spearman association of the mean of the 64 unique seed-specific true
margin/noise values with SPADE-only answer rate is at least 0.80 over 25
family-prevalence cells. Median seed-specific margin and qLogNEI-only answer rate are
sensitivities. Hill success must state prevalence and meet the answer/lower-bound rule. The
true-margin diagnostic is explanatory, not deployable; the 25 nested cells are dependent,
not exchangeable population samples.

## TT — acquisition targeting mechanism

**Frozen commit:** `c6c034c1bf337c1c51f9d3660c0a6d40c12b7a33`  
**Code:** `software/scripts/run_tt_theta_tau.py`, `software/scripts/analyse_tt_theta_tau.py`  
**Data:** `research/results/mechanism/tt-{ackley,hartmann6,hill,levy,rosenbrock}.json`

Five families × 32 seeds × 48 wells compare committed SPADE, SPADE targeting the p=0.30
threshold, and qLogNEI. Primary gate: targeted SPADE improves certified volume with an
interval excluding zero. Guardrail: regret non-inferiority within ±0.02. Committed SPADE
must reproduce LC exactly.

## Shared rules

- Validate with empirical truth containment, never model-internal containment.
- Report answered and contained counts together.
- State prevalence, noise, assurance, wells, rounds, and seeds.
- Preserve structural zeros and name saturated families.
- A failed gate narrows or withdraws the claim; it is not rewritten after seeing data.
