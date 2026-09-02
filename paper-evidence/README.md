# SPADE paper evidence

This directory answers four questions:

1. What does the SPADE paper claim?
2. Which exact result supports each claim?
3. Which code, configuration, test, and input reproduce it?
4. Why is everything else supporting material or archive material?

## Audit baseline

The audit is frozen at commit `6e4f22e`, immediately before repository consolidation began.
That baseline contains 719 commits and 1,402 tracked files. Later consolidation commits are
reviewed through ordinary code review and are not added to the historical denominator.

The audit does not treat a summary, handoff, filename containing `FINAL`, recent commit, or
prior agent conclusion as ground truth. Those are navigation aids. Scientific conclusions are
accepted only after tracing them to committed results and their producing or validating code.

## Current audit state

- `commit-review.csv` contains one row for every baseline commit.
- `file-review.csv` contains one row for every baseline tracked file.
- Every file has a reviewed era, scientific role, claim relationship, dependency statement,
  supersession status, classification, destination, and rationale. No provisional marker
  remains.
- Final baseline dispositions are: 66 CORE, 89 SUPPORT, 194 INFRASTRUCTURE,
  834 ARCHIVE-VALID, 62 ARCHIVE-SUPERSEDED, 1 ARCHIVE-FAILED/VOID, and
  156 GENERATED/DISPOSABLE.
- The lab role manifest was applied per file: 81 in-house files remain supporting evidence
  and 235 assay-development, blocked, unrelated, or irrelevant-sidecar files are archived.
- `paper/CLAIMS-AND-SOURCES.md` adjudicates the surviving claims and correction chains;
  `reproduction-map.md` gives the executable commands and expected values.

This ordering is intentional. The project contains long correction chains in which a later
document can still quote an earlier invalid number. Automatically classifying files from age,
name, or the latest document would repeat that failure.

## Research eras

| Era | Role in the final SPADE paper |
|---|---|
| `E1-E4_FOUNDATION` | Historical foundation; normally archived. |
| `BO_VS_DOE_TERMINAL_RULE` | Companion study and introductory context. |
| `LAB_AND_PUBLISHED_DATA` | Supporting real-cell evidence and immutable inputs. |
| `DESIGN_SPACE_PRE_SPADE` | Mixed supporting evidence and superseded method development. |
| `SPADE_DEVELOPMENT_AND_LOCKBOX` | Core method and reproducibility infrastructure. |
| `SPADE_MANUFACTURING_RECOVERY` | Core or supporting calibration and real-assay work. |
| `SPADE_CONFIRMATION_AND_PAPER` | Core confirmatory evidence, limitations, and paper synthesis. |

Era is a navigation field, not a truth verdict. A correction can supersede a result within the
same era, and active SPADE code can depend on modules first introduced for an older study.

## Adjudicated correction chains

The chronological pass identified these high-risk chains, which were resolved or bounded in
`paper/CLAIMS-AND-SOURCES.md`:

- E2 scoring and pairing defects, followed by Q20/Q27/Q34/Q35 and the D20 rescore.
- E4's reported headline versus its registered primary.
- Q47 and Q52 registered predictions and retracted headlines.
- K6/K6b circular containment and Version B containment corrections.
- Amendment E/F metric, threading, pooling, and wrong-column errata.
- Version C kill-condition and scope-gap corrections.
- SPADE manufacturing calibration from KR through KX/KY/KZ.
- LA/LB/LC round matching and the withdrawn then narrowed parity headline.
- TAU prevalence expansion, including the Hill higher-prevalence result.
- ACK and TT targeting-mechanism corrections.
- DC comparison with classical DoE and the corrected BO-drift interpretation.

The most important corrections are machine-guarded: DC's one-process `-0.0005` replaces stale
LC parity prose, and the frozen LC LOFO calculation gives C3 `+0.000855`, not the unsupported
manual `+0.001353`. Archived claims do not become current merely because their files remain.

## Navigation

- `main-results/` groups the evidence for the method, comparisons, cross-family result,
  rounds/cost interpretation, and real-cell support.
- `supporting-results/` groups mechanism tests, limitations/failures, and reviewer defenses.
- `../archive/README.md` explains the preserved inactive tree.
- `file-review.csv` is the complete file-level archive manifest; the indexes intentionally do
  not duplicate 1,402 path entries.
