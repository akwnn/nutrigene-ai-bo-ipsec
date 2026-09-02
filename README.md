# SPADE

SPADE is a research workflow for designing cell-manufacturing experiments and returning a
conservative operating region—or abstaining when the available wells do not support one.
This repository contains the method, matched-budget comparisons, canonical evidence, and an
audited archive of the research history.

## Start here

- [Paper draft](publication/manuscript/MANUSCRIPT.md)
- [Methods](publication/manuscript/METHODS.md)
- [Frozen protocols](publication/manuscript/PROTOCOLS.md)
- [Claims and sources](publication/manuscript/CLAIMS-AND-SOURCES.md)
- [Reproduction map](publication/evidence/reproduction-map.md)
- [Evidence guide](publication/evidence/README.md)
- [Archive guide](archive/README.md)

The claim ledger is authoritative. Historical files containing “final,” “result,” or a newer
date are not automatically current evidence.

## Main findings

- SPADE at five rounds has no detectable regret difference from qLogNEI at ten rounds in the
  one-process comparison (`-0.0005`, 95% CI `[-0.0221, 0.0207]`).
- At matched five rounds, SPADE has greater certified volume (`+0.000855`, 95% CI
  `[0.000691, 0.001028]`). The older `+0.001353` prose value is corrected and guarded.
- Screened DoE finds a better point recipe in fewer rounds, but its answered regions contain
  truth only 85/122 times; SPADE contains truth in 66/66 answered cells.
- Certifiability tracks target margin relative to noise across five families (rho `0.9801`).
- Hill is part of the five-family result and certifies at prevalence 0.70 (40/40 contained).
- Real-cell analyses are supporting evidence, not prospective wet-lab validation.

## Reproduce guarded claims

Use Python 3.11:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
.venv/bin/python software/scripts/verify_conclusions.py
.venv/bin/pytest -q
```

Individual analysis commands and expected outputs are documented in
`publication/evidence/reproduction-map.md`. Long campaign runners are not required to verify the
committed result calculations.

## Repository map

```text
publication/
├── manuscript/       actual paper, methods, supplement, protocols, claim ledger
└── evidence/         result guide, reproduction map, file and commit audits

research/
├── data/             benchmark, laboratory, and published-data inputs
└── results/
    ├── comparisons/      DC, LC, and LA canonical JSON files
    ├── generalization/   TAU cross-family canonical JSON files
    ├── mechanism/        TT mechanism canonical JSON files
    ├── real-cell/        real-cell outputs
    └── figures/          all existing research figures, grouped by status

software/
├── src/              active Python implementation
├── scripts/          active runners, analysers, and verification tools
├── tests/            active regression suite
└── configs/          frozen active configurations

archive/             source material and preserved historical research
```

The pre-consolidation baseline (`6e4f22e`) contains 719 commits and 1,402 tracked files. Every
one has a disposition in `publication/evidence/file-review.csv`; no baseline material was deleted.

## Scope and limitations

Headline benchmarks use 48 wells and relative noise 0.25. At real-assay noise near 0.68, no
tested arm certifies. The in-house dataset awaits manual CD31 gate signoff. SPADE has not yet
been validated prospectively in a wet-lab campaign. See `publication/manuscript/SUPPLEMENT.md` for the complete
limitation set.

## Citation and license

Citation metadata are provided in `CITATION.cff`. No software or data reuse license has yet
been granted; see `LICENSE`. A release intended for public reuse must replace that notice with
an owner-approved license and confirm data-governance terms.
