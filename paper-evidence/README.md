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
- The chronological pass separates scientific results, corrections and retractions, frozen
  protocols, implementation work, merges, and documentation or analysis.
- Result and correction commits remain marked `TRACE_IN_CLAIM_LEDGER` until the next pass names
  the exact surviving claim, canonical result, and superseding correction.
- File classifications remain `UNREVIEWED` until the claim-to-evidence map is established.

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

## Known correction chains requiring evidence adjudication

The chronological pass identifies these high-risk chains for explicit resolution in
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

No file movement begins until the active claims in these chains are tied to canonical evidence.
