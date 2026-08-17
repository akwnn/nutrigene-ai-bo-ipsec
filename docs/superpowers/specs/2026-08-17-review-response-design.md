# Review-response design: Q60, Q61, TOST, and a non-fragile paper pass

**Date.** 2026-08-17  
**Status.** Approved in conversation. Science not yet run.

## Goal

Close the two load-bearing reviewer holes (batch size; averaged confirmation) and stop calling non-significance a tie, without rewriting the paper twice.

## Freeze vs open

**Locked numbers.** Anything already in `results/*.json`. Do not re-run E2, Q54–Q59 to “refresh” headlines.

**Open prose.** `docs/RESEARCH-SUMMARY.md` (spine) and `docs/SUPPLEMENT.md`.

**Not this cycle.** Student-t / learned-noise GP refit; d=8 cost curves; Zenodo DOI; PDF/SVG figure export; q=1 on non-primary cells.

## Paper pass (no new campaigns)

Allowed now:

- Strip internal editing notes from the spine.
- Abstract leads with the reversal, then Narayanan / Rummukainen.
- Never print 0.27–0.36 without the in-region result in the same sentence.
- CIs on every headline contrast from stored JSON (`instance_bootstrap`, n=25).
- Random-48 measured-argmax row in Table 4.1 (primary-cell random mean 0.2216, not within 0.02 of either arm).
- One-shot GP (Q54: 24.4/25 vs 16/25 at σ=0.25, τ=0.10, model recommendation, one round) in abstract Results and as its own conclusions bullet.
- Retitle §2 to “Definitions and decision rules.”
- GP latent coverage 0.764 into Methods; posterior-mean pick and in-region GP are conditional on that miscalibration.
- Cite timestamped commits: primary cell `d289e7d` (Q20); sequential RSM / `path_argmax` `fd842ac`.
- D20 locator correction moves to supplement changelog.
- Inferential hierarchy in one sentence: primary cell (d=6, σ=0.25) confirmatory and unadjusted; other three cells exploratory. Holm is for multi-arm and multi-target families, not silently skipped.
- Do **not** newly declare “null,” “tie,” or “lead vanishes.” Write “interval covers 0; equivalence not tested” until TOST exists. Keep the Q58 confirmation-alone numbers with CIs and the averaging caveat.

## Q60 — averaged top-3 confirmation

Primary cell only. Replay Q58 campaigns (same instance ids, seeds, both arms).

New locator `top_k_average`: shortlist k=3 by first reading; pick argmax of (Y + Y_confirm)/2 on the shortlist. Cost +3 wells.

Keep `top3` (confirmation reading alone) as a sibling column.

**Gate.** The four existing Q58 rules reproduce per row at 1e-12. Stop if not.

**Falsifiers (fixed before the runner exists).**

- Averaging restores a DoE lead whose bootstrap interval excludes 0 → “confirm 3 → vanish” is an artefact of discarding the first reading.
- Averaging interval covers 0 → the lab-facing sentence can be stated for a protocol labs use.

Output: `results/q60-top3-average.json`. Tests for `top_k_average` in `tests/test_selection.py` **before** the runner.

## Q61 — q=1 at the primary cell

d=6, σ=0.25, N=48, n₀=14, n=25×2, same instances as E2.

| Arm | Source | Rounds |
|---|---|---|
| qLogEI q=1 | new | 35 |
| qLogNEI q=1 | new | 35 |
| qLogEI q=4 | read `e2-grid.json` | 10 |
| DoE | read stored E2/Q57 | 3 |

Score measured-value argmax and tested-best. DoE is not re-run. Use existing `CampaignConfig.q`.

**Gate.** A q=4 shadow on stored seeds still matches published 0.1553 (cell mean to 5e-5). Stop if not.

**Falsifiers.**

- q=1 vs DoE interval covers 0 or flips on measured-argmax → 0.0595 is partly batching.
- q=1 still loses, interval excludes 0 → batching objection closed. Report 35 rounds.

Do not Holm Q61 into the four-cell E2 grid. One planned sensitivity.

Output: `results/q61-q1-sequential.json`.

## TOST

SESOI = 0.02 regret on n=25 paired landscape differences. Both one-sided tests must reject to call equivalent; else different or inconclusive. Report Wilcoxon MDE at 80% power for n=25 beside it.

Apply to: four in-region cells; two low-noise measured-argmax cells; Q58 posterior; Q58 top3; Q60 average.

Can ship as `scripts/tost_contrasts.py` reading stored JSON; no new campaigns.

## Collaboration

Spine remains `docs/RESEARCH-SUMMARY.md`. Tables in `docs/SUPPLEMENT.md`. New runs land in `docs/RESULTS.md` first. JSON wins over markdown.
