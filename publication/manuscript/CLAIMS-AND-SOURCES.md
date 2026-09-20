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
- **Analysis command:** `.venv/bin/python software/scripts/analyse_dc_doe_certificate.py`.
- **Expected output:** SPADE-minus-qLogNEI mean/CI/p/n above from 160 matched
  family-seed campaigns.
- **Protocol and destination:** `publication/manuscript/PROTOCOLS.md` (DC); Manuscript 3.1.
- **Guard status:** `software/scripts/verify_conclusions.py` and
  `software/tests/test_current_conclusion_guard.py` pin the estimate, CI, and n; they do not
  pin p or the full DC grid.
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
- **Canonical results:** DC files listed under C1.
- **Analysis command:** `.venv/bin/python software/scripts/analyse_dc_doe_certificate.py`.
- **Expected output:** at p=.30 the analyser selects the smallest passing inflation separately
  for each arm using the DC cells themselves (not held-out calibration), reports the counts
  above, and prints the adverse regret contrast.
- **Protocol and destination:** `publication/manuscript/PROTOCOLS.md` (DC); Manuscript 3.3.
- **Guard status:** standalone analysis only. The numeric conclusion guard does not assert C2
  counts, lower bounds, within-DC inflation selection, or the adverse regret estimate/CI/p.

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
- **Analysis command:** `.venv/bin/python software/scripts/analyse_lc_confirmatory.py --glob
  'research/results/comparisons/lc-*.json'`.
- **Expected output:** the R5 leave-one-family-out contrast above, pooled over p=.30 and .10;
  n=320 is five families x 32 seeds x two family-seed-prevalence cells.
- **Protocol and destination:** `publication/manuscript/PROTOCOLS.md` (LC); Manuscript 3.2.
- **Guard status:** `software/scripts/verify_conclusions.py` and the focused test pin the mean
  and n. They do not pin the CI, p, fold-specific inflation choices, or prevalence pooling.
- **Support:** matched-`margin/sd` binning is separately evaluated in the TAU analysis.
- **Limit:** the analogous R=3 certified-volume claim was withdrawn at 32 seeds; C3 is
  restricted to the registered R=5 comparison.

### C4 — SPADE beats a one-shot space-filling design

- **Allowed:** at 3 rounds SPADE has lower regret than one-shot LHS.
- **Estimate:** `-0.0783`, 95% CI `[-0.1104,-0.0490]`, `n=80`.
- **Canonical results:** SPADE R3 rows in `research/results/comparisons/lc-*.json` and LHS rows in
  `research/results/comparisons/la-*.json`.
- **Analysis command:** `.venv/bin/python software/scripts/verify_conclusions.py`; there is no
  dedicated C4 report command.
- **Expected output:** mean above from n=80 = four LA families (Ackley, Hartmann6, Levy,
  Rosenbrock) x 20 common seeds; unmatched LC Hill and seeds 20--31 are excluded.
- **Protocol and destination:** `publication/manuscript/PROTOCOLS.md` (LA and LC); Manuscript 3.2.
- **Guard status:** the conclusion guard asserts only the mean (tolerance .004), not the CI, n,
  schedule, or pair composition.

### C5 — Certifiability generalizes across five families through margin-to-noise

- **Allowed:** across Ackley, Hartmann6, Hill, Levy, and Rosenbrock and five prevalences,
  SPADE answer rate at `c=1.0`, `alpha=0.95` is descriptively associated with the mean of
  the 64 unique seed-specific true-surface `margin/sd` values in each cell.
- **Forbidden:** presenting `margin/sd` as a deployable prospective diagnostic; it uses the
  true response surface and is currently explanatory.
- **Estimate:** Spearman rho `0.9880098603391883` over 25 nested family-prevalence cells.
  Median seed-specific margin gives the same rho; qLogNEI-only mean margin gives rho
  `0.9682461469`.
- **Limit:** the nested cells are dependent and not exchangeable population samples; this is
  a descriptive registered-gate result, not population inference from a naive p-value.
- **Canonical results:** `research/results/generalization/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis command:** `.venv/bin/python software/scripts/analyse_tau_sweep.py`.
- **Expected output:** the exact descriptive rho above at c=1.0 over 25 complete cells, with
  mean and median seed-margin and qLogNEI sensitivity results.
- **Protocol and destination:** `publication/manuscript/PROTOCOLS.md` (TAU); Manuscript 3.4.
- **Guard status:** the analyser validates the full canonical TAU key grid; the conclusion guard
  pins the primary rho and 25-cell count, but not the sensitivity rho values.

### C6 — Hill demonstrates the biology-shaped, higher-prevalence case

- **Allowed:** on the biphasic Hill family at prevalence `0.70`, SPADE answers 40/64 and all
  40 answered certificates contain truth; lower bound `0.9278`.
- **Forbidden:** “BO cannot certify Hill”; qLogNEI also has perfect containment but only 27
  answered cells, two below the minimum perfect-containment count.
- **Canonical results and analysis:** TAU paths and command under C5.
- **Expected output:** at p=.70, c=1.0, alpha=.95, SPADE 40/64 answered, 40 contained,
  one-sided 95% lower bound .9278; qLogNEI answers 27/64 with 27 contained.
- **Protocol and destination:** `publication/manuscript/PROTOCOLS.md` (TAU); Manuscript 3.4.
- **Guard status:** the conclusion guard pins SPADE answered, contained, and lower bound; it
  does not pin qLogNEI counts.
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
- **Analysis command:** `.venv/bin/python software/scripts/analyse_tt_theta_tau.py`.
- **Expected output:** TT-1 and TT-2 fail; the volume/regret estimates and intervals above are
  printed, with per-family cancellation context.
- **Protocol and destination:** `publication/manuscript/PROTOCOLS.md` (TT); Manuscript 3.5.
- **Guard status:** standalone analysis and named-file audit only. S1 is absent from the numeric
  conclusion guard, and no executable equality check proves TT's committed SPADE rows reproduce LC.

### S2 — Real assays expose posterior collapse hidden by benchmarks

- Mean marginalization adds only `1.004x-1.011x` posterior width on benchmarks but changes
  the in-house iPSC-EC width by `484x` and the published Hall/Ogle width by `297x`.
- **Canonical inputs:** `research/data/lab/derived/candidate_campaign_coating_flow.csv` and
  `research/data/published/hall_ogle_2025_stage1.csv`; benchmark width support remains indirect
  and is not an active canonical result object.
- **Analysis commands:** `.venv/bin/python software/scripts/run_real_ipsc_certification.py` and
  `.venv/bin/python software/scripts/certify_hall_ogle.py`.
- **Expected output:** approximately 484x in-house and 297.5x Hall/Ogle raw-to-mean-marginalized
  posterior width, alongside certificate tables.
- **Protocol and destination:** `METHODS.md` (Real-data support); Manuscript 3.6.
- **Guard/status:** SUPPORT, not prospective wet-lab validation. Outputs are stdout-only; no
  canonical structured S2 result or numeric conclusion guard covers these ratios.

### S3 — Real-data calibration is assay-specific

- In-house LOO calibrated `c=0.712`; published Hall/Ogle LOO calibrated `c=0.526`, both below
  the simulated default `1.5`.
- **Canonical inputs:** the in-house and Hall/Ogle CSVs under S2.
- **Analysis commands:** `.venv/bin/python software/scripts/calibrate_real_assay_loo.py` and
  `.venv/bin/python software/scripts/certify_hall_ogle.py`.
- **Expected output:** in-house c=.712 and Hall/Ogle raw-posterior c=.526.
- **Protocol and destination:** `METHODS.md` (Real-data support); Manuscript 3.6.
- **Guard status:** stdout-only support; no canonical structured S3 result or numeric conclusion
  guard covers either value.
- **Limit:** LOO scores observation prediction, not independently identified latent-function
  uncertainty; replicate tubes are still required.

## Required limitations

### L1 — Noise ceiling

All benchmark headline results use `sigma_rel=0.25`. At measured real-assay noise near
`0.68`, no tested arm certifies. Do not generalize benchmark certification to current wet-lab
noise without this limitation.

- **Evidence input:** `archive/exploratory/results/k1-noise-ceiling.json`, retained outside the
  active canonical result root; the registered/result narrative is preserved at
  `archive/superseded-spade/docs/SPADE-REALISTIC-NOISE-SPEC.md`.
- **Analysis command and expected output:** no complete active analysis command is mapped; the
  preserved result reports zero answer rate at sigma_rel=.68 across tested inflations/arms.
- **Protocol and destination:** required limitation; Manuscript Discussion.
- **Guard status:** no active structured L1 guard. The paper-link/repository scans preserve and
  classify the sources but do not recompute the ceiling.

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
