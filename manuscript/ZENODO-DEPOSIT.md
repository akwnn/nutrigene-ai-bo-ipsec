# Archival DOI path (Zenodo)

## Why
PLOS wants a stable public archive. GitHub is fine for review; a Zenodo DOI is the archival deposit.

## What to upload
Prefer a clean release ZIP of:
- `manuscript/` (md + figures used)
- `results/` needed for claims (or the release bundle already used for upload drafts)
- `LICENSE`, `LICENSE-CONTENT.md`, `README.md`
- analysis scripts cited in Software and reproducibility

Existing draft bundles (local):
- `manuscript/SPADE-PLOS-ONE-upload-draft-2026-09-12.zip` (and earlier dated ZIPs)

## Steps
1. Create a GitHub release tag on `codex/publication-readiness` (or the final submission commit), e.g. `v1.0.0-plos-submission`.
2. Go to https://zenodo.org → New upload → upload the release ZIP (or enable GitHub–Zenodo webhook on the repo).
3. Metadata draft:
   - **Title:** Point and region objectives reverse method rankings in a synthetic benchmark of SPADE and experimental design strategies
   - **Creators:** Kwan, Alana Wai Han; Yung, Joseph
   - **Affiliations:** Columbia University (ChemE; IEOR)
   - **License:** dual — code MIT; research content CC BY 4.0 (describe in description; Zenodo often wants one primary license — use CC BY 4.0 for the research archive and point to MIT for software in the description)
   - **Description:** Short abstract + link to https://github.com/akwnn/nutrigene-ai-bo-ipsec commit `c4f58d3` / final tag
   - **Related identifiers:** GitHub URL; later PLOS article DOI when published
4. Publish → copy the DOI into `SPADE-PLOS-ONE.md` Data availability and the cover letter.
5. Rebuild DOCX.

## Do not
- Invent a DOI before Zenodo issues one
- Upload secrets, `.venv`, credentials, or private lab records
