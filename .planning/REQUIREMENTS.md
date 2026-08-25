# Milestone Requirements

## Method

- [ ] **METH-01:** SPADE executes exactly 48 evaluations with a scrambled Sobol opening
  selected from 32, 40, or 44 and complete q=4 adaptive batches.
- [ ] **METH-02:** Adaptive batches use one objective each: qLogNEI, global IVR, or
  boundary-weighted IVR; raw objective scores are never scalarized together.
- [ ] **METH-03:** The validity gate uses only current model diagnostics and falls back to
  global IVR when a stable non-empty boundary is unavailable.
- [ ] **METH-04:** All arms use the same learned-noise GP family, fit policy, candidate
  menu, Rule P terminal selector, and scoring functions.

## Reliability map and certificate

- [ ] **CERT-01:** The target is `P(Y_new >= tau | f) >= gamma`; changing gamma changes
  the target draws and certificate.
- [ ] **CERT-02:** Threshold construction is sealed, arm-independent, and passes only the
  numeric tau to each method.
- [ ] **CERT-03:** Certificate construction uses 4,096 draws split 2,048/2,048 and records
  model-conditional cross-fit containment only as a diagnostic.
- [ ] **CERT-04:** Confirmatory validity uses empirical truth containment across campaigns;
  empty certificates count only against answer rate.
- [ ] **CERT-05:** PASS requires one-sided exact lower bounds above registered answer-rate
  and containment thresholds.

## Development and lockbox

- [ ] **EVAL-01:** Existing five families are development-only and exactly nine SPADE
  candidates are selected by the registered lexicographic rule.
- [ ] **EVAL-02:** Four new randomized d=6 generator families provide independent
  landscape instances and remain unopened until protocol freeze.
- [ ] **EVAL-03:** The final study runs at least 350 paired campaigns per family and arm,
  increasing that number before launch if map/regret power requires it.
- [ ] **EVAL-04:** Success requires map non-inferiority to Sobol48, regret
  non-inferiority to qLogNEI48, answer-rate evidence, and empirical-containment evidence
  in every family.

## Reproducibility and publication

- [ ] **REP-01:** All random streams are statelessly derived, independently named, and
  reproducible across resume.
- [ ] **REP-02:** Raw shards, manifests, analyses, and selected protocol carry source,
  environment, protocol, and parent hashes.
- [ ] **REP-03:** Release validation fails on missing/duplicate keys, dirty source,
  mismatched hashes, budget/rule mixing, invalid denominators, and premature lockbox use.
- [ ] **REP-04:** Historical replay limitations are disclosed; new evidence does not rely
  on unverifiable historical raw rows.
- [ ] **REP-05:** Full tests, release validation, and independent code review pass before
  any completion or paper claim.

