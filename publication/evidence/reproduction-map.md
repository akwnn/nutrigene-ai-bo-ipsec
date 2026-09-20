# SPADE paper reproduction map

Run commands from the repository root using the committed `.venv` or an equivalent Python
3.11 environment installed from `requirements.txt` and `pip install -e .`. Frozen designs are
in `publication/manuscript/PROTOCOLS.md`; complete dimensions and guard gaps are in
`publication/evidence/benchmark-matrix.md`.

## Fast numeric guard

```bash
.venv/bin/python software/scripts/verify_conclusions.py
```

Expected: `12/12` selected values reproduce. This is a partial guard: it covers C1
estimate/CI/n, C3 mean/n, C4 mean, C5 primary rho/cell count, and C6 SPADE
answered/contained/lower bound. C2, S1, S2, S3, and L1 are not included.

## Main claims

### C1 — DC one-process regret

- **Canonical inputs:** `research/results/comparisons/dc-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis:** `.venv/bin/python software/scripts/analyse_dc_doe_certificate.py`.
- **Expected:** SPADE R5 minus qLogNEI R10 `-0.0005`, 95% CI
  `[-0.0221,+0.0207]`, p=.96, n=160.
- **Protocol/destination:** `PROTOCOLS.md` (DC); Manuscript 3.1.
- **Validation:** estimate, CI, and n are guarded; p and full grid are not.

### C2 — DC certificate versus classical DoE

- **Canonical inputs:** the five DC files above.
- **Analysis:** `.venv/bin/python software/scripts/analyse_dc_doe_certificate.py`.
- **Expected:** at p=.30, the smallest passing c is selected separately for each arm from the
  DC cells themselves. SPADE reports 66/160 answered and 66 contained; screened DoE 122/85;
  unscreened DoE 134/77. SPADE-minus-screened-DoE regret is `+0.1026`, CI
  `[+0.0486,+0.1578]`, p=.0003.
- **Protocol/destination:** `PROTOCOLS.md` (DC); Manuscript 3.3.
- **Validation:** standalone analyser only. Counts, lower bounds, adverse regret, within-DC
  inflation choice, and grid completeness are not asserted by the numeric guard.

### C3 — LC matched-round certified volume

- **Canonical inputs:** `research/results/comparisons/lc-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis:** `.venv/bin/python software/scripts/analyse_lc_confirmatory.py --glob
  'research/results/comparisons/lc-*.json'`.
- **Expected:** R5 SPADE-minus-qLogNEI `+0.000855`, 95% CI
  `[+0.000691,+0.001028]`, p<.0001, n=320. LOFO pools p=.30 and .10, so n is five
  families x 32 seeds x two prevalence cells. Historical `+0.001353` prose is unsupported.
- **Protocol/destination:** `PROTOCOLS.md` (LC); Manuscript 3.2.
- **Validation:** mean and n are guarded; CI, p, prevalence pooling, fold c choices, and full
  grid are not. Run the producer with `--seeds 32`; its current default remains 25.

### C4 — LC SPADE R3 versus LA one-shot LHS

- **Canonical inputs:** SPADE R3 rows in the five LC files and LHS rows in
  `research/results/comparisons/la-{ackley,hartmann6,levy,rosenbrock}.json`.
- **Analysis:** `.venv/bin/python software/scripts/verify_conclusions.py` (no dedicated C4
  report command).
- **Expected:** regret `-0.0783`, 95% CI `[-0.1104,-0.0490]`, n=80 = four families x
  20 common seeds.
- **Protocol/destination:** `PROTOCOLS.md` (LA and LC); Manuscript 3.2.
- **Validation:** only the mean is guarded (tolerance .004); CI, n, schedules, and pair
  composition are not asserted.

### C5 — TAU margin/noise generalization

- **Canonical inputs:** `research/results/generalization/tau-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis:** `.venv/bin/python software/scripts/analyse_tau_sweep.py`.
- **Expected:** at c=1.0 and alpha=.95, descriptive SPADE-only Spearman rho
  `0.9880098603391883` over 25 nested family-prevalence cells. Each x value is the mean of
  64 unique seed-specific margins; median gives the same rho and qLogNEI sensitivity is
  `0.9682461469`. No naive population p-value is interpreted.
- **Protocol/destination:** `PROTOCOLS.md` (TAU); Manuscript 3.4.
- **Validation:** the analyser rejects an incomplete canonical TAU key grid; the guard pins
  primary rho/cell count, not sensitivities. Run the producer with `--seeds 64`; its current
  default remains 32.

### C6 — Hill at easier prevalence

- **Canonical inputs/analysis:** the C5 TAU files and command.
- **Expected:** Hill, p=.70, c=1.0, alpha=.95: SPADE 40/64 answered and 40 contained,
  one-sided 95% lower bound .9278; qLogNEI 27/64 answered and 27 contained.
- **Protocol/destination:** `PROTOCOLS.md` (TAU); Manuscript 3.4.
- **Validation:** SPADE answered/contained/lower bound are guarded; qLogNEI counts are not.

## Supporting claims

### S1 — TT targeting mechanism

- **Canonical inputs:** `research/results/mechanism/tt-{ackley,hartmann6,hill,levy,rosenbrock}.json`.
- **Analysis:** `.venv/bin/python software/scripts/analyse_tt_theta_tau.py`.
- **Expected:** TT-1/TT-2 fail; targeted-minus-committed SPADE volume `+0.000425`, CI
  `[-0.000022,+0.000875]`; regret `+0.0301`, CI `[+0.0169,+0.0450]`, p<.0001.
- **Protocol/destination:** `PROTOCOLS.md` (TT); Manuscript 3.5.
- **Validation:** no S1 number is in the conclusion guard, and no executable equality guard
  proves TT committed-SPADE rows reproduce LC. Named files are repository-audited.

### S2 — posterior-width collapse on real assays

- **Canonical inputs:** `research/data/lab/derived/candidate_campaign_coating_flow.csv` and
  `research/data/published/hall_ogle_2025_stage1.csv`. The benchmark 1.004x--1.011x range has
  no active canonical result object.
- **Analysis:** `.venv/bin/python software/scripts/run_real_ipsc_certification.py` and
  `.venv/bin/python software/scripts/certify_hall_ogle.py`.
- **Expected:** approximately 484x in-house and 297.5x Hall/Ogle raw-to-mean-marginalized
  posterior width, followed by certificate tables.
- **Protocol/destination:** `METHODS.md` (Real-data support); Manuscript 3.6.
- **Validation:** stdout-only support. No structured S2 result or numeric guard covers the
  ratios; in-house data remain `awaiting_human_signoff`.

### S3 — assay-specific LOO inflation

- **Canonical inputs:** the S2 in-house and Hall/Ogle CSVs.
- **Analysis:** `.venv/bin/python software/scripts/calibrate_real_assay_loo.py` and
  `.venv/bin/python software/scripts/certify_hall_ogle.py`.
- **Expected:** in-house c=.712 and Hall/Ogle raw-posterior c=.526.
- **Protocol/destination:** `METHODS.md` (Real-data support); Manuscript 3.6.
- **Validation:** stdout-only support. No structured S3 result or numeric guard covers these
  values. LOO scores observation prediction, not independent latent truth.

## Required limitation

### L1 — real-noise ceiling

- **Evidence input:** `archive/exploratory/results/k1-noise-ceiling.json`; registration/result
  narrative at `archive/superseded-spade/docs/SPADE-REALISTIC-NOISE-SPEC.md`.
- **Analysis:** no complete active analysis command is mapped.
- **Expected preserved result:** at sigma_rel=.68, tested arms/inflations have zero answer rate;
  benchmark certification must not be generalized to current assay noise.
- **Protocol/destination:** required limitation; Manuscript Discussion.
- **Validation:** no active structured L1 guard. Link/repository audits preserve and classify
  the evidence but do not recompute it.

## Repository checks

```bash
.venv/bin/python software/scripts/check_paper_links.py
.venv/bin/pytest software/tests/test_current_conclusion_guard.py software/tests/test_paper_links.py software/tests/test_repository_audit.py -q
git diff --check
```

Long campaign producers are not rerun during documentation-only verification. A run is tested
only after its full command, runtime, exit status, and output hash are recorded.
