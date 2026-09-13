# SPADE research benchmark

Research software for comparing point recommendations and acceptable-region maps
under matched experimental budgets. All reported experiments are synthetic;
the repository does not establish biological efficacy or a manufacturing guarantee.

The current article is [the SPADE manuscript](manuscript/SPADE-PLOS-ONE.md), with an
[editable Word version](manuscript/SPADE-PLOS-ONE.docx). Its four main figures are in
`results/paper-figures/plos/`, including vector PDF/SVG, 450-dpi PNG, 600-dpi RGB TIFF,
source-data JSON, captions and accessible descriptions. The PLOS build uses Arial;
install a legitimately licensed copy before rebuilding figures. Font identity is
recorded in `results/paper-figures/build-manifest.json`.

## Evidence boundaries

- Retrospective campaigns support terminal-rule and point-versus-region comparisons.
- `spade-final-2026-08-23` contains 99,601 prospective records across seven conditions:
  99,600 scored records and one structural-unavailability declaration.
  Twelve repeated scoring configurations per campaign correspond to 8,300 campaign-arm
  executions, not 99,600 independent experiments. Its map mask uses a 0.50 cutoff.
  The original prospective certificate statistic measures a held-out posterior check,
  not empirical containment against oracle truth; it does not establish certificate validity.
- The separate joint-protocol development study contains 2,750 campaign-arm rows
  and returned `NO_SELECTION`. The selected-protocol artifact binds five compressed
  development shards and their manifests by SHA-256. These files are retained
  byte-for-byte from research commit `502ea39`; they are not new simulations.
- No protocol was selected and no lockbox outcomes were opened. Do not run lockbox
  workflows or create a power artifact on the basis of this development result.

The contribution is an auditable comparison of decision criteria and their limits,
not a universally superior optimizer or a transferable certificate.

## Reproducing the publication artifacts

The recorded experiment environment uses Python 3.11. Scientific package versions
are pinned in `requirements.txt`; that file is hash-bound by the registered study
and must not be extended for document tools. Optional Word dependencies are pinned
separately in `requirements-publication.txt`.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-publication.txt
.venv/bin/python -m pip install -e .
.venv/bin/python scripts/make_publication_tables.py
.venv/bin/python scripts/make_paper_figures.py --preset portable
.venv/bin/python scripts/make_paper_figures.py --preset plos
.venv/bin/python scripts/build_manuscript_docx.py
.venv/bin/python scripts/build_manuscript_docx.py --submission --output manuscript/SPADE-PLOS-ONE-submission.docx
.venv/bin/python scripts/build_manuscript_docx.py --input manuscript/SPADE-PLOS-ONE-cover-letter.md --output manuscript/SPADE-PLOS-ONE-cover-letter.docx --submission --cover-letter
```

These commands summarize retained evidence and build artifacts; they do not rerun
the experimental campaigns. Figure exports include renderer-level label checks,
but final PDF/Word inspection remains necessary. The Word builder preserves editable
equations. The submission copy omits embedded figures and retains inline captions;
the default copy includes the figures for reading. The paper's three supporting tables are the calibration, comparison and
claim-ledger files in `results/publication-tables/`; historical planned supporting
figure reservations are not a submission inventory.

Build the PLOS preset last: the shared build manifest records the most recent preset.
If specifying an output directory, use `--output-dir results/paper-figures`, not
`results/paper-figures/plos` (the builder appends the preset name). Publication tests
check recorded source/data and export hashes and compare the reading copy's embedded
image bytes against the four current PLOS PNG files. Run them after rebuilding Word.

Each Word build also writes a `.docx.manifest.json` sidecar binding the Markdown,
builder, image inputs and resulting document. The table manifest binds its builder
and inputs too. A changed source requires rebuilding the corresponding derivative.
Supporting-table CSVs preserve archived numerical results and label the corrected
interpretations separately; small nonzero values use scientific notation.

To collect the journal upload files after rebuilding:

```bash
.venv/bin/python scripts/prepare_submission_bundle.py --output manuscript/SPADE-PLOS-ONE-upload-draft.zip
```

The command refuses an existing output path and rejects stale recorded inputs or
exports. It collects the submission manuscript, cover letter, four TIFF figures,
and `S1_Table.csv`–`S3_Table.csv`, matching the manuscript captions. Its manifest
records hashes and outstanding author requirements. This is a local draft bundle,
not a submission or the code/data archival deposit. Extract its individual files
for the journal; the metadata manifest is for author review, not a supporting item.
The cover letter retains unresolved author confirmations, including prior journal
contact, related submissions, editor/reviewer preferences and approval to submit.

## Validation and known limitations

```bash
.venv/bin/python -m pytest tests/test_publication_bundle.py tests/test_manuscript_docx.py tests/test_paper_figure_builders.py tests/test_paper_figure_layout.py tests/test_publication_tables.py tests/test_submission_package.py -q
.venv/bin/python scripts/validate_final_spade_release.py --pre-release
.venv/bin/python -m pytest -q
```

The final-SPADE validator checks that evidence body's registered release rules. It
does not establish that every manuscript claim, dependency installation, author
declaration, or historical replay is correct. Before making a release, run it again
without `--pre-release` on the intended clean source snapshot.

Eight historical replay checks are known to fail in the current environment,
including three material adaptive qLogEI/qLogNEI mismatches. Their exact equality
checks remain enabled. `scripts/audit_historical_replay.py` records the original
observations and classifications; running it does not rerun those campaigns.
Reaggregating retained rows must not be described as exact regeneration of all
historical experiments. The manuscript discloses this limitation.

The claim-impact audit in `.planning/debug/replay-claim-impact.md` traces each
failure to the paper. Its reaggregation and conditional sensitivity checks are
executable with `python -m pytest -q tests/test_replay_claim_impact.py`. The 15.3%
target map contrast uses the retained regenerated prospective dataset, not the
older failing Q42/Q59 reference columns. Current sampler defaults differ from
the archived recovery version; passing summary checks do not prove trajectory replay.

Current local drafts after that audit are
`manuscript/SPADE-PLOS-ONE-upload-draft-2026-09-12.zip` (journal files) and
`results/archival-release/SPADE-code-data-local-draft-2026-09-12-r4.zip`
(code/data with licenses and the claim-impact audit). Earlier dated ZIPs are
preserved historical drafts, not the current manuscript package.

Publication still requires author-approved declarations and a public archival release
with a DOI. Neither journal submission nor a public upload has been performed by the
artifact-building commands above. A private GitHub backup is not a public deposit.

## Licensing

Alana Wai Han Kwan and Joseph Yung jointly own the original project materials and
have approved MIT for original software and CC BY 4.0 for released original research
materials. See [LICENSE](LICENSE) and [LICENSE-CONTENT.md](LICENSE-CONTENT.md) for
the grants, attribution and exclusions. Third-party materials retain their own
licenses. The virtual environment, credentials and private lab records are not part
of the publication archive. Ownership confirmation does not set manuscript author
order or approve the outstanding author declarations.
