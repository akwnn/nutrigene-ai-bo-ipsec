# Zenodo deposit (DOI for PLOS)

PLOS needs a stable archive DOI, not only GitHub.

## Steps (~30–60 minutes)
1. Create a free Zenodo account (https://zenodo.org) and link GitHub if you want one-click.
2. Prefer: Zenodo ↔ GitHub release of `codex/publication-readiness` (or tag the submission commit).
   Or: New upload → upload a zip of the repo at the submission commit plus `publication/`, `manuscript/`, and `research/results/comparisons/`.
3. Title: `SPADE PLOS ONE submission package (nutrigene-ai-bo-ipsec)`.
4. Creators: Alana Wai Han Kwan; Joseph Yung. License: MIT for code / CC-BY-4.0 for content as in the repo.
5. Publish → copy the DOI (for example `10.5281/zenodo.xxxxxxx`).
6. Paste the DOI into `manuscript/SPADE-PLOS-ONE.md` Data availability (replace the placeholder sentence) and rebuild the DOCX.

Anchor commit for the audited science bible: `ec14bc7`. Submission manuscript rebuilds live on `codex/publication-readiness`.
