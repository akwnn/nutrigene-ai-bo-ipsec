# SPADE claims and sources

This is the authoritative claim ledger for the final SPADE methods paper. A quantitative
statement may enter `MANUSCRIPT.md` only if it has an ID here, a committed result, and a
producing or validating path. Values below are at 48 wells and `sigma_rel = 0.25` unless
the entry says otherwise.

## Main claims

### C1 — SPADE matches BO on recipe quality with fewer rounds

- **Allowed:** SPADE at 5 rounds has no detectable regret difference from qLogNEI at 10
  rounds in the one-process DC comparison.
- **Forbidden:** “SPADE beats BO on regret” or “equivalence was proved.”
- **Estimate:** SPADE minus qLogNEI `-0.0005`, 95% CI `[-0.0221, +0.0207]`, `p=0.96`,
  `n=160` (5 families x 32 seeds).
- **Canonical results:** `research/results/comparisons/dc-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis:** `software/scripts/analyse_dc_doe_certificate.py`.
- **Guard:** `software/scripts/verify_conclusions.py`, `software/tests/test_current_conclusion_guard.py`.
- **Correction:** supersedes LC's cross-run `+0.0016` estimate. The DC interval is slightly
  wider than the `0.02` SESOI, so the wording is “no detectable difference.”

### C2 — SPADE returns a trustworthy region where classical DoE does not

- **Allowed:** at prevalence `0.30`, SPADE is the only tested arm with perfect containment;
  classical DoE answers often but is over-confident.
- **Forbidden:** “SPADE finds a better recipe than DoE” or hiding that DoE uses fewer rounds.
- **Estimate:** SPADE 66/160 answered, 66 contained, containment `1.0000`, lower bound
  `0.9556`; screened DoE 122/160 answered, 85 contained, containment `0.6967`; unscreened
  DoE 134/160 answered, 77 contained, containment `0.5746`.
- **Adversarial result:** DoE beats SPADE on regret by `+0.1026` SPADE-minus-DoE, 95% CI
  `[+0.0486,+0.1578]`, `p=0.0003`, using 3 rounds versus SPADE's 5.
- **Canonical results and analysis:** DC files and analyser listed under C1.
- **Frozen protocol:** `publication/manuscript/PROTOCOLS.md` (DC).

### C3 — SPADE improves certified volume at matched rounds

- **Allowed:** under the registered leave-one-family-out calibration, at 5 matched rounds
  SPADE has greater mean certified volume than qLogNEI across the five-family benchmark.
- **Estimate:** SPADE-minus-qLogNEI certified volume is
  `+0.000855`, 95% CI `[+0.000691,+0.001028]`, `p<0.0001`, `n=320`.
- **Correction:** several historical documents report `+0.001353`. The frozen analyser
  and the exact committed inputs at the commit introducing that prose reproduce
  `+0.000855`, not `+0.001353`; fixed-c and live-family-only alternatives also do not
  produce the historical value. It is therefore an unsupported manual calculation or
  transcription and must not enter the manuscript.
- **Canonical results:** `research/results/comparisons/lc-*.json`.
- **Analysis:** `software/scripts/analyse_lc_confirmatory.py`.
- **Guard:** `software/scripts/verify_conclusions.py`, `software/tests/test_current_conclusion_guard.py`.
- **Support:** matched-`margin/sd` binning is separately evaluated in the TAU analysis.
- **Limit:** the analogous R=3 certified-volume claim was withdrawn at 32 seeds; C3 is
  restricted to the registered R=5 comparison.

### C4 — SPADE beats a one-shot space-filling design

- **Allowed:** at 3 rounds SPADE has lower regret than one-shot LHS.
- **Estimate:** `-0.0783`, 95% CI `[-0.1104,-0.0490]`, `n=80`.
- **Canonical results:** SPADE R3 rows in `research/results/comparisons/lc-*.json` and LHS rows in
  `research/results/comparisons/la-*.json`.
- **Guard:** `software/scripts/verify_conclusions.py`.

### C5 — Certifiability generalizes across five families through margin-to-noise

- **Allowed:** across Ackley, Hartmann6, Hill, Levy, and Rosenbrock and five prevalences,
  true-surface `margin/sd` strongly explains answer rate.
- **Forbidden:** presenting `margin/sd` as a deployable prospective diagnostic; it uses the
  true response surface and is currently explanatory.
- **Estimate:** Spearman rho `0.9801`, 25 family-prevalence cells, `p<0.0001`.
- **Canonical results:** `research/results/generalization/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis:** `software/scripts/analyse_tau_sweep.py`.
- **Guard:** `software/scripts/verify_conclusions.py`.

### C6 — Hill demonstrates the biology-shaped, higher-prevalence case

- **Allowed:** on the biphasic Hill family at prevalence `0.70`, SPADE answers 40/64 and all
  40 answered certificates contain truth; lower bound `0.9278`.
- **Forbidden:** “BO cannot certify Hill”; qLogNEI also has perfect containment but only 27
  answered cells, two below the minimum perfect-containment count.
- **Canonical results, analysis, and guard:** TAU paths under C5.
- **Interpretation:** Hill must remain within the five-family result while receiving a clearly
  labeled paper subsection because its response shape is the closest benchmark analogue to
  the cell-manufacturing biology.

## Supporting mechanism and real-data claims

### S1 — Targeting does not earn its complexity

- Correctly aiming SPADE at `tau` changes certified volume by `+0.000425`, 95% CI
  `[-0.000022,+0.000875]`, and worsens regret by `+0.0301`, 95% CI
  `[+0.0169,+0.0450]`, `p<0.0001`.
- The family aggregate is a cancellation: it helps Hartmann6 and hurts Ackley.
- **Canonical results:** `research/results/mechanism/tt-*.json`.
- **Analysis:** `software/scripts/analyse_tt_theta_tau.py`.
- **Protocol and interpretation:** `publication/manuscript/PROTOCOLS.md` (TT).

### S2 — Real assays expose posterior collapse hidden by benchmarks

- Mean marginalization adds only `1.004x-1.011x` posterior width on benchmarks but changes
  the in-house iPSC-EC width by `484x` and the published Hall/Ogle width by `297x`.
- **In-house code/data:** `software/scripts/run_real_ipsc_certification.py`, `boec.meanmarg`, and
  `research/data/lab/derived/candidate_campaign_coating_flow.csv`.
- **Published code/data:** `software/scripts/certify_hall_ogle.py` and `research/data/published/`.
- **Status:** SUPPORT, not prospective wet-lab validation.

### S3 — Real-data calibration is assay-specific

- In-house LOO calibrated `c=0.712`; published Hall/Ogle LOO calibrated `c=0.526`, both below
  the simulated default `1.5`.
- **Code:** `software/scripts/calibrate_real_assay_loo.py`, `software/scripts/certify_hall_ogle.py`.
- **Limit:** LOO scores observation prediction, not independently identified latent-function
  uncertainty; replicate tubes are still required.

## Required limitations

### L1 — Noise ceiling

All benchmark headline results use `sigma_rel=0.25`. At measured real-assay noise near
`0.68`, no tested arm certifies. Do not generalize benchmark certification to current wet-lab
noise without this limitation.

### L2 — In-house status

The in-house candidate dataset remains `awaiting_human_signoff`; its CD31 gates require
manual CytExpert review. It is not a prospective wet-lab SPADE validation and must not be
written as one.

### L3 — Abstention reporting

Every certification claim must report both `answered` and `contained`, plus prevalence,
noise, confidence level, wells, rounds, and seeds. “Cannot certify” is forbidden when the
observed issue is only insufficient answered-cell count.

### L4 — Unresolved method scope

R=4 and a rho sweep remain untested. The DoE comparator is a low-order response-surface
pipeline; conclusions must not be generalized to every possible classical design or model.
