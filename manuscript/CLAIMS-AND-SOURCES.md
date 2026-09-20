# SPADE claims and sources

This is the authoritative claim ledger for `manuscript/SPADE-PLOS-ONE.md`.
The manuscript may say SPADE is better only when the operating-region endpoint,
matched-round setting, benchmark scope, and relevant containment/answer denominators
are named. “Better” without those qualifiers is forbidden.

The active PLOS source is on `codex/publication-readiness`. Current C1–C6 and S1
reproduction uses the consolidated audited evidence in the sibling
`.worktrees/paper-ready` worktree. Where an equivalent result or analyser is present
on this branch, its active path is also named below. Frozen results are not copied or
altered merely to make paths uniform. Values are for 48 wells and relative noise
`0.25` unless stated otherwise.

## Main claims

### C1 — No detectable point-regret difference from longer BO

- **Allowed:** SPADE at five rounds showed no detectable regret difference from
  qLogNEI at ten rounds in the one-process DC comparison.
- **Forbidden:** “SPADE beats BO on regret,” “SPADE matches qLogNEI,” “parity,” or
  any claim that equivalence was established.
- **Estimate:** SPADE minus qLogNEI `-0.0005`, 95% CI
  `[-0.0221,+0.0207]`, `p=0.96`, `n=160` (five families x 32 seeds).
- **Audited evidence:** `.worktrees/paper-ready/research/results/comparisons/dc-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis command:** `(cd .worktrees/paper-ready && .venv/bin/python software/scripts/analyse_dc_doe_certificate.py)`.
- **Guard coverage:** the audited `software/scripts/verify_conclusions.py` pins the
  estimate, interval, and denominator; `tests/test_spade_plos_claims.py` pins the
  complete signed claim in the active manuscript.
- **Limitation:** the interval extends slightly beyond the registered `0.02`
  smallest effect of interest. This is no detectable difference, not equivalence.
- **Correction:** this one-process DC estimate supersedes the cross-run LC estimate.

### C2 — Regional containment and the adverse DoE point result

- **Allowed:** at prevalence `0.30`, SPADE was the only tested arm with perfect
  observed truth containment among answered regions; the tested DoE pipelines
  answered more often but had lower observed conditional containment.
- **Forbidden:** “SPADE finds a better recipe than DoE,” “SPADE beats DoE”
  without naming the operating-region endpoint, or generalization to all DoE.
- **Estimate:** SPADE 66/160 answered and 66/66 contained (lower bound `0.9556`);
  screened DoE 122/160 answered and 85/122 contained (`0.6967`); unscreened
  DoE 134/160 answered and 77/134 contained (`0.5746`).
- **Adverse estimate:** screened DoE found the better point recipe in three rounds:
  SPADE-minus-DoE regret `+0.1026`, 95% CI `[+0.0486,+0.1578]`,
  `p=0.0003`, `n=160`; SPADE used five rounds.
- **Audited evidence and command:** the DC files and analyser listed for C1.
- **Guard coverage:** the active manuscript guard pins all answer/containment
  denominators, the signed adverse estimate, interval, p-value, and round schedules.
  The audited scalar guard is not exhaustive for C2.
- **Limitation:** SPADE selected `c=1` using the DC cells themselves. Neither DoE
  arm passed at any tested inflation, so its counts are fallback diagnostics at
  baseline `c=1`. This is within-sample descriptive evidence, not held-out or
  transportable coverage.

### C3 — Greater certified volume at matched five rounds

- **Allowed:** under registered leave-one-family-out (LOFO) calibration, SPADE had
  greater mean certified volume than qLogNEI at five matched rounds across the
  five-family benchmark.
- **Estimate:** SPADE minus qLogNEI `+0.000855`, 95% CI
  `[+0.000691,+0.001028]`, `p<0.0001`, `n=320`.
- **Active evidence:** `results/lc-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Active analysis command:** `.venv/bin/python scripts/analyse_lc_confirmatory.py
  --glob 'results/lc-*.json'`.
- **Audited evidence:** `.worktrees/paper-ready/research/results/comparisons/lc-*.json`.
- **Guard coverage:** the audited scalar guard pins the mean and denominator; the
  active manuscript guard pins the complete signed estimate, CI, p-value, LOFO
  qualification, matched-R5 setting, and dependent-cell denominator.
- **Limitation:** `n=320` is five families x 32 seeds x two prevalence cells, not
  320 independent campaigns. The ordinary flat-cell bootstrap is conditional and
  may be too narrow under within-cluster dependence.
- **Correction:** the former historical C3 value is unsupported and excluded. The
  analogous positive three-round claim was withdrawn after extension to 32 seeds.

### C4 — Lower regret than one-shot space filling

- **Allowed:** at three rounds SPADE had lower regret than one-shot LHS in the
  frozen paired comparison.
- **Estimate:** SPADE minus LHS `-0.0783`, 95% CI
  `[-0.1104,-0.0490]`, `n=80`.
- **Audited evidence:** `.worktrees/paper-ready/research/results/comparisons/lc-*.json`
  and `.worktrees/paper-ready/research/results/comparisons/la-*.json`.
- **Analysis command:** `(cd .worktrees/paper-ready && .venv/bin/python software/scripts/verify_conclusions.py)`.
- **Guard coverage:** the audited guard pins the mean only.
- **Limitation:** the 80 pairs are four named families x 20 common seeds; unmatched
  Hill rows and seeds 20–31 are excluded, not imputed. This is not a general
  sequential-design claim.

### C5 — Margin-to-noise explains certifiability descriptively

- **Allowed:** across five families and five prevalences, SPADE answer rate at
  `c=1.0`, `alpha=0.95` was descriptively associated with mean seed-specific true
  margin-to-noise.
- **Forbidden:** treating margin-to-noise as a deployable prospective diagnostic;
  it uses the latent true response surface.
- **Estimate:** Spearman rho `0.9880098603391883` over 25 nested
  family-prevalence cells. Median-margin sensitivity is identical; the qLogNEI
  sensitivity is `0.9682461469`.
- **Active evidence:** `results/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Active analysis command:** `.venv/bin/python scripts/analyse_tau_sweep.py`.
- **Guard coverage:** the audited conclusion guard validates canonical completeness
  and pins the primary rho and 25-cell count, but not every sensitivity.
- **Limitation:** cells share families and ordered prevalences and are dependent and
  nonexchangeable. No naive correlation p-value is interpreted.

### C6 — Hill higher-prevalence subgroup

- **Allowed:** on synthetic biphasic Hill at prevalence `0.70`, SPADE answered
  40/64 and all 40/40 answered regions contained truth (lower bound `0.9278`).
- **Forbidden:** “BO cannot certify Hill.” qLogNEI also had perfect observed
  containment (27/27) but two fewer answers than the minimum needed to clear the
  registered lower-bound gate.
- **Evidence and command:** active and audited TAU paths under C5.
- **Guard coverage:** the audited guard pins SPADE answered, contained, and lower
  bound, but not the qLogNEI counts.
- **Limitation:** the family is biology-shaped but synthetic. The claim requires
  prevalence `0.70`, relative noise `0.25`, `alpha=0.95`, `c=1`, 48 wells,
  five rounds, 64 seeds, and both answer and containment denominators.

## Supporting mechanism and real-data claims

### S1 — Threshold targeting failed its adoption gate

- **Allowed:** target-aligning the acquisition changed certified volume by
  `+0.000425`, 95% CI `[-0.000022,+0.000875]`, and worsened regret by
  `+0.0301`, 95% CI `[+0.0169,+0.0450]`, `p<0.0001`.
- **Forbidden:** saying the tested acquisition was genuinely threshold-targeted or
  that the targeting mechanism worked.
- **Audited evidence:** `.worktrees/paper-ready/research/results/mechanism/tt-*.json`.
- **Analysis command:** `(cd .worktrees/paper-ready && .venv/bin/python software/scripts/analyse_tt_theta_tau.py)`.
- **Guard coverage:** standalone audited analysis only; S1 is not in the active
  numeric manuscript guard.
- **Limitation:** Hartmann6 and Ackley effects cancelled. The failed variant was not
  adopted; SPADE's supported value is architectural.

### S2 — Mean marginalisation exposes posterior collapse

- **Allowed:** propagating fitted-mean uncertainty widened average posterior
  marginal SD only `1.004x–1.011x` in synthetic diagnostics but approximately
  `484x` in-house and `297x` for Hall–Ogle.
- **Active inputs:** `data/lab/derived/candidate_campaign_coating_flow.csv` and
  `data/published/hall_ogle_2025_stage1.csv`.
- **Audited commands:** `(cd .worktrees/paper-ready && .venv/bin/python
  software/scripts/run_real_ipsc_certification.py)` and
  `(cd .worktrees/paper-ready && .venv/bin/python software/scripts/certify_hall_ogle.py)`.
- **Guard coverage:** supporting stdout-reproduced diagnostics; no structured
  active result object or numerical guard covers the ratios.
- **Limitation:** retrospective support only, not prospective SPADE validation.

### S3 — Real-data calibration is assay-specific

- **Allowed:** observation-prediction leave-one-out inflation was `c=0.712`
  in-house and `c=0.526` for Hall–Ogle.
- **Inputs and commands:** S2 inputs plus the audited
  `software/scripts/calibrate_real_assay_loo.py` and Hall–Ogle command.
- **Guard coverage:** stdout-only support, unguarded.
- **Limitation:** LOO predicts held-out observations, not independently identified
  latent-function uncertainty. Replicate tubes remain necessary.

## Required limitations

### L1 — Real-noise ceiling

- Headline benchmarks use relative noise `0.25`. At measured real-assay relative
  noise near `0.68`, no tested arm certified.
- **Active evidence:** `results/k1-noise-ceiling.json`.
- **Guard coverage:** preserved limitation, not an actively recomputed scalar guard.

### L2 — In-house status

- The candidate in-house dataset remains `awaiting_human_signoff`; CD31 gates
  require manual review. It is not prospective wet-lab validation.

### L3 — Abstention and certification reporting

- Every regional-certification claim must state family/scope, prevalence, relative
  noise, assurance, inflation rule, wells, rounds, seeds, answered count, contained
  count, containment fraction, and lower bound, either locally or in the immediately
  preceding table.
- Empty or sparse answers are abstention/insufficient denominator, not proof that a
  family or optimizer cannot certify.

### L4 — Method and inference scope

- R4, broader assurance sweeps, larger budgets, and continuous-domain validation
  remain untested.
- qLogNEI is one BO acquisition; the DoE comparator is one low-order
  screen-plus-response-surface pipeline.
- The flat-cell bootstrap and pooled binomial intervals do not make dependent cells
  independent campaigns or establish population coverage.
- The later joint-protocol grid returned `NO_SELECTION`; no power artifact was
  authorized and the lockbox remains `FROZEN_UNOPENED`.
