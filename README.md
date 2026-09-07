# SPADE

SPADE is a research workflow for designing cell-manufacturing experiments and returning a
conservative operating region—or abstaining when the available wells do not support one.
This repository contains the method, matched-budget comparisons, canonical evidence, and an
audited archive of the research history.

The methodological ingredients—Gaussian-process level-set learning, Vorob'ev quantiles,
conservative excursion-set estimation, noisy BO, response-surface DoE, and abstention—are
established. SPADE's contribution is their fixed-well cell-assay integration, explicit
answer/containment reporting, held-out-family inflation for the matched-round analysis, and
the bounded empirical comparison. In particular, the conservative-set core closely follows
Azzimonti et al. (2021); the paper does not claim that theory as new.

## Start here

- [Paper draft](publication/manuscript/MANUSCRIPT.md)
- [Review-ready Word manuscript](publication/manuscript/SPADE-MANUSCRIPT.docx)
- [Methods](publication/manuscript/METHODS.md)
- [Frozen protocols](publication/manuscript/PROTOCOLS.md)
- [Claims and sources](publication/manuscript/CLAIMS-AND-SOURCES.md)
- [Reproduction map](publication/evidence/reproduction-map.md)
- [Evidence guide](publication/evidence/README.md)
- [Benchmark matrix](publication/evidence/benchmark-matrix.md)
- [Literature and novelty review](publication/evidence/literature-and-novelty-review.md)
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
- At `c=1.0` and `alpha=0.95`, SPADE answer rate tracks the mean seed-specific true
  margin/noise ratio across 25 family-prevalence cells (descriptive rho `0.9880098603`).
- Hill is part of the five-family result and certifies at prevalence 0.70 (40/40 contained).
- Real-cell analyses are supporting evidence, not prospective wet-lab validation.

## Evidence status

| Evidence | Status | Use |
|---|---|---|
| DC and LC | Confirmatory/core | C1-C3 |
| LA | Frozen development lineage | C4 support |
| TAU | Confirmatory/core descriptive gate | C5-C6 |
| TT | Frozen negative mechanism test | S1 |
| In-house and Hall/Ogle | Retrospective support | S2-S3; not prospective validation |

The current manuscript uses in-text Tables 1-3. Existing polished figures are explicitly
historical and are not relabelled as current evidence.

## Reproduce guarded claims

Use Python 3.11:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
.venv/bin/python software/scripts/verify_conclusions.py
.venv/bin/python software/scripts/build_manuscript_docx.py
.venv/bin/pytest -q
```

This verifies 12 selected scalar checks, including the repaired, order-invariant C5 result; it
is not an exhaustive guard for every interval, p-value, real-data support value, or limitation.
Individual producer/analyser commands, inputs, expected outputs, and guard coverage are in
`publication/evidence/reproduction-map.md`. Long campaign runners are not required to verify
calculations from committed canonical results.

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
├── scripts/          active runners, analysers, verification, and manuscript build tools
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

The C3 interval uses a conditional flat-cell bootstrap over dependent
family-seed-prevalence cells. C5 is a descriptive association across 25 nested cells, not a
population correlation. Clopper-Pearson bounds summarize observed answered cells under a
binomial model; they are not a transportable frequentist guarantee for new assays.

## Publication readiness

The code, manuscript, canonical results, claim ledger, and CI verification path are packaged
for scientific review. Before a public reusable release or journal submission, the owners
must still choose a license, settle rights for each data class, supply author affiliations,
ORCIDs, contributions, funding/conflict/ethics statements as applicable, select a journal,
and create a current figure package if that venue requires one. These owner-dependent items
are disclosed rather than guessed.

## Citation and license

Citation metadata are provided in `CITATION.cff`. No software or data reuse license has yet
been granted; see `LICENSE`. A release intended for public reuse must replace that notice with
an owner-approved license and confirm data-governance terms.
