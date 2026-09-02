# SPADE

SPADE is a research workflow for designing cell-manufacturing experiments and returning a
conservative operating region—or abstaining when the available wells do not support one.
This repository contains the method, matched-budget comparisons, canonical evidence, and an
audited archive of the research history.

## Start here

- [Paper draft](paper/MANUSCRIPT.md)
- [Methods](paper/METHODS.md)
- [Frozen protocols](paper/PROTOCOLS.md)
- [Claims and sources](paper/CLAIMS-AND-SOURCES.md)
- [Reproduction map](paper-evidence/reproduction-map.md)
- [Evidence guide](paper-evidence/README.md)
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
.venv/bin/python scripts/verify_conclusions.py
.venv/bin/pytest -q
```

Individual analysis commands and expected outputs are documented in
`paper-evidence/reproduction-map.md`. Long campaign runners are not required to verify the
committed result calculations.

## Repository map

```text
paper/             publication draft, methods, supplement, claim ledger
paper-evidence/    evidence indexes, reproduction commands, file/commit audits
src/boec/          active SPADE and comparator implementation
scripts/           active runners, analysers, guards, and audit tooling
tests/             active regression suite
configs/           frozen active configurations
data/              active benchmark and supporting real-cell inputs
results/           canonical compact results used by the manuscript
archive/           preserved superseded, exploratory, void, and generated material
```

The pre-consolidation baseline (`6e4f22e`) contains 719 commits and 1,402 tracked files. Every
one has a disposition in `paper-evidence/file-review.csv`; no baseline material was deleted.

## Scope and limitations

Headline benchmarks use 48 wells and relative noise 0.25. At real-assay noise near 0.68, no
tested arm certifies. The in-house dataset awaits manual CD31 gate signoff. SPADE has not yet
been validated prospectively in a wet-lab campaign. See `paper/SUPPLEMENT.md` for the complete
limitation set.

## Citation and license

Citation metadata are provided in `CITATION.cff`. No software or data reuse license has yet
been granted; see `LICENSE`. A release intended for public reuse must replace that notice with
an owner-approved license and confirm data-governance terms.
