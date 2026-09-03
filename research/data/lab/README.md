# In-house iPSC-EC evidence subset

This directory contains the evidence-linked subset used by the retrospective iPSC-to-
endothelial analyses. It is supporting material, not a prospective SPADE campaign and not a
complete public laboratory-data release.

## Status and boundaries

- `derived/candidate_campaign_coating_flow.csv` is the active analysis input.
- The candidate table and CD31 gates remain `awaiting_human_signoff`; they cannot support an
  optimization or biological-validation claim.
- `raw/` contains only acquisitions and protocols retained in the active support path. The
  larger immutable source drop and assay-development material are preserved under
  `archive/exploratory/` and classified in `publication/evidence/file-review.csv`.
- `overlay/bo_file_roles.csv`, `overlay/bo_primary_conditions.csv`, and `overlay/GATE.md`
  record reviewed roles, candidate conditions, and unresolved gating decisions.
- `derived/` contains retained derivation and provenance artifacts. Their presence does not
  assert that the archived full source drop can be rebuilt from this subset.

```text
research/data/lab/
├── raw/        evidence-linked FCS acquisitions and protocol documents
├── overlay/    roles, candidate conditions, gate status, historical manifest
└── derived/    candidate tables and retained derivation/provenance summaries
```

`overlay/MANIFEST.sha256` covers the historical full source drop and is retained for
provenance. It is not an active-subset checksum contract: many listed files were moved to the
archive during publication-first consolidation. `derived/RUN.json` likewise describes the
historical full-drop build and contains a contributor-local source path; it is not a portable
rebuild receipt.

## Use in this paper

The active scripts read the committed candidate table and report retrospective uncertainty
diagnostics. Mean marginalization changes mean posterior marginal standard deviation over the
candidate grid by approximately 484-fold, and leave-one-out observation-prediction calibration
gives `c=0.712`. These values are supporting and currently lack structured canonical result
objects and exhaustive numeric guards. See `publication/manuscript/CLAIMS-AND-SOURCES.md`
(S2/S3) and `publication/evidence/reproduction-map.md` for commands and limitations.

## Governance

No reuse permission is implied. The repository `LICENSE` grants no license, and owners must
settle laboratory-data access and reuse terms before public deposit. Repository presence does
not establish ethics approval, participant consent, or regulatory qualification.
