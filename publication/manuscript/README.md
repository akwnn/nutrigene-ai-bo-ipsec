# SPADE paper

This directory is the publication reading path.

1. `MANUSCRIPT.md` — canonical integrated paper source.
2. `SPADE-MANUSCRIPT.docx` — line-numbered, review-ready Word rendering.
3. `METHODS.md` — executable method and statistical specification.
4. `SUPPLEMENT.md` — supporting real-data analyses, mechanism tests, and limitations.
5. `PROTOCOLS.md` — consolidated frozen designs and registration hashes.
6. `CLAIMS-AND-SOURCES.md` — authoritative allowed wording and source for every claim.

Regenerate the Word manuscript from the canonical source and citation metadata with:

```bash
.venv/bin/python software/scripts/build_manuscript_docx.py
```

The claim ledger overrides narrative prose if a discrepancy remains. Exact commands and
expected values are in `../evidence/reproduction-map.md`; the complete historical file
and commit audits are in `../evidence/`.

## Relationship to `manuscript/` (PLOS package)

- **`publication/`** (this tree): audited claims ledger and canonical methods manuscript.
- **`manuscript/SPADE-PLOS-ONE.*`**: active PLOS ONE submission package on `codex/publication-readiness`.

As of 2026-09-20, the active PLOS abstract/results use the locked ledger values
(`C1` `-0.0005`, `C3` `+0.000855`, DoE adverse `+0.1026`). Conclusion guards on
`codex/paper-ready` reproduced **12/12** doc numbers from committed comparison JSONs.
Stale LC `+0.0016` and unsupported `+0.001353` must not appear as current conclusions.
