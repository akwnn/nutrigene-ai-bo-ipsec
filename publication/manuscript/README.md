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
