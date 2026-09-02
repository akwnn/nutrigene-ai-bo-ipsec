# SPADE paper reproduction map

Run commands from the repository root using the committed `.venv` or an equivalent Python
3.11 environment installed from `requirements.txt` and `pip install -e .`.

## Fast guarded claims

### C1, C4, C5, and C6

```bash
.venv/bin/python software/scripts/verify_conclusions.py
```

Expected: `12/12` values reproduce. C1 must name the DC one-process source and report
`-0.0005`; C5 reports rho `0.9801`; C6 reports Hill `40/40`, lower bound `0.9278`; C4 reports
SPADE-minus-LHS `-0.0783`.

### C1 and C2 — DC comparison

```bash
.venv/bin/python software/scripts/analyse_dc_doe_certificate.py
```

Inputs: `research/results/comparisons/dc-*.json`. Expected: SPADE certifies with 66/66 containment; screened and
unscreened DoE do not; SPADE-minus-qLogNEI regret is `-0.0005`; SPADE-minus-DoE regret is
`+0.1026`.

### C3 — matched-round volume

```bash
.venv/bin/python software/scripts/analyse_lc_confirmatory.py --glob 'research/results/comparisons/lc-*.json'
```

Inputs: `research/results/comparisons/lc-*.json`. Current output is R5 mean `+0.000855`, 95% CI
`[+0.000691,+0.001028]`, `p<0.0001`, `n=320`. Historical prose reports `+0.001353`, but
the frozen analyser and its exact committed inputs do not reproduce it. The claim ledger
records that correction; `software/scripts/verify_conclusions.py` now guards the executable value.

### S1 — theta/tau mechanism

```bash
.venv/bin/python software/scripts/analyse_tt_theta_tau.py
```

Inputs: `research/results/mechanism/tt-*.json`. Expected: TT-1 and TT-2 fail; volume difference `+0.000425` and
regret cost `+0.0301`.

## Real-cell supporting evidence

### S2/S3 — in-house iPSC-EC

```bash
.venv/bin/python software/scripts/run_real_ipsc_certification.py
.venv/bin/python software/scripts/calibrate_real_assay_loo.py
```

Requires committed lab-derived inputs. Results remain provisional until manual CD31 gate
signoff; running the code does not change that status.

### S2/S3 — published Hall/Ogle data

```bash
.venv/bin/python software/scripts/certify_hall_ogle.py
```

Inputs: canonical extractions under `research/data/published/`. Expected posterior-width ratio `297x`
and assay-specific LOO inflation `c=0.526`.

## Verification suite

```bash
.venv/bin/pytest software/tests/test_current_conclusion_guard.py software/tests/test_repository_audit.py -q
```

Long runners are not rerun during document-only moves. Each is marked tested only after its
full command, runtime, exit status, and output hash are recorded in the final audit report.
