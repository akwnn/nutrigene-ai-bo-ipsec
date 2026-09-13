# Replay limitations: claim-impact audit

Date: 2026-09-12. Assessment: **share with the specified caveats; exact historical
replay remains unresolved**. This is a bounded dependency and sensitivity audit,
not journal approval or a new benchmark. No reference rows or original equality
tests were changed. No new study grid, power artifact or lockbox outcomes were used.

## Decision

Retain the primary findings as analyses of the identified retained benchmark.
Explicitly exclude the older Q42/Q59 adaptive reference columns from cross-family
ranking support. Do not label the prospective comparisons independently replay
validated: their generators share optimizer code, and current sampler defaults
differ from recovery commit `1bf51f1`. Do not infer all-campaign numerical bounds
from the checked fixed-design cases. No numerical main-paper finding had to be
deleted on this audit's evidence; the scope and reproducibility claims were narrowed.

## All eight gates mapped

| Gate | Failed reference / observed discrepancy | Paper dependency and disposition |
|---|---|---|
| D23 full-space Rule P | `fix1-terminal-rule.json`, one classical campaign, 3.878e-7 | Direct input to Figure 2 and terminal-rule narrative through `fix1-analysis.json`. Conditional one-row reanalysis below preserves displayed results and selected-arm ordering. Retain with limitation. |
| P4 LHS bitwise scorer | `k6-designspace-spread.json`, first failed field 2.22e-16; prior 24-cell probe worst 6.66e-16 | Historical map-fidelity reference, also consulted by the P7 gate. Not the prospective Table 3/S1 source. Figure 4A does not select LHS. No direct numerical replacement or blanket harmlessness claim. |
| Q59 unscreened additivity | `q59-hartmann-no-screen.json`, Rule C 3.173e-8 | Old unscreened scalar, not the prospective unscreened Table 3 row. Preserve audit; do not use old Q59 comparisons to establish current cross-family ranking. |
| Q52 spread extraction | `q52-budget-to-target.json`, worst 3.123e-7 over six tested rows | Historical budget-to-target evidence, not a numerical input to Figures 2–4 or prospective publication tables. No Q52 budget-to-target conclusion is advanced by the paper. |
| P7 checkpoint/map gate | `k6-designspace.json` / spread reference, 48 fields up to 9.082e-13 | `p7-murphy.json` supplies Figure 4A. Fresh checked classical campaign compared directly to those retained P7 rows below; displayed calibration/refinement ordering unchanged. Gate stays failing. |
| Q42 Hartmann6 qLogEI | Old Rule A 0.2278685246 vs current 0.3038381094 | Not Figure 3D's numerical source. Prospective C3 uses later regenerated campaigns. Old reference excluded from ranking support; shared-code/version caveat retained. |
| Q42 multi-family qLogEI | First failure Ackley d6 seed 0: 0.5928006956 vs 0.9140845131 | Not prospective S1's numerical source. Test stops at its first failure: this does not clear subsequent families/seeds/dimensions. Same restriction as above. |
| Q59 Hartmann6 qLogNEI | Old Rule A 0.1699699209 vs current 0.1112758790 | Not prospective C3's numerical source. Same restriction as above; magnitude is material, not rounding noise. |

All eight original selected tests failed freshly in **43.58 seconds**, with the
same observed values as the preceding diagnostic work. Their purpose and exact
assertions remain unchanged; the new impact tests are additional tests, not substitutes.

## Numerical dependency routes

- **Primary 15.3%, target regret parity, targeting null, Table 3, S1–S3, Figure 3A–C:**
  final-SPADE condition rows → `analyse_final_spade_benchmark.py` → retained
  pareto/kill-ledger outputs; `make_publication_tables.py` independently reads the
  seven condition files plus those outputs. C2 is Hill d6, sigma 0.10. No Q42/Q59/Q52
  scalar is imported to calculate the target estimate.
- **Figure 3D / prospective external-family paragraphs:** final-SPADE C3/C4/S1
  rows → final-SPADE pareto output. These are not the earlier external-family files.
- **Figure 2:** Fix 1 raw rows and analysis plus `step0-oracle-best.json`.
  The Fix 1 generator's baseline references are E2, K6 and Version B, not Q42/Q59.
  It fits a common terminal GP; the D23 failure is directly relevant to its classical
  Rule-P row. The observed mismatch is therefore not ignored just because it is small.
- **Figure 4A:** means of selected `p7-murphy.json` fields for doe, sobol, qlognei
  and versionb. Historical K6 files are fidelity-gate references, not substituted
  values in these means.
- **Figure 4B:** final-SPADE certificate rows. Interpretation remains posterior
  self-consistency, not empirical oracle containment.
- **Figure 4C/D:** P8 certificate-family raw rows filtered to `versionb`, with P8
  prediction summaries checked against them. `run_p8_certificate_families.py` builds
  versionb/plate1 variants, not qLogEI/qLogNEI baseline campaigns. No old Q42/Q59
  adaptive scalar feeds these selected panels.
- **Table 4 / NO_SELECTION:** separate joint-protocol development artifacts and
  their hash-bound analysis/selection. No historical reference substitution occurs.

The prospective runner calls the shared `regenerate` dispatch and uses P2 for
Hill instance/seed keys and the frozen feasibility file for condition definitions.
Separate data files are not proof of independent software or complete reproducibility.

## Primary estimate reaggregation

From `final-spade-c2.json`, select tau 0.25, gamma 0.95, alpha 0.95, and each
specified arm. Each arm has exactly 100 unique instance/campaign pairs: 25 instances
with seeds {0,1,2,3}. Average four seeds within each instance, then average instances.

- SPADE m0 map error: **0.180414**.
- qLogNEI map error: **0.2130685**.
- Relative reduction: **15.325822446771815%**, displayed as 15.3%.
- Mean Rule-P regrets: 0.08436358328544825 and 0.07498882256575883.

This reaggregation establishes the archived summary, not fresh campaign regeneration.
It does not promote the effect beyond the registered synthetic target condition.

## Adaptive version boundary

Recorded 2026-09-11 diagnostic probes, checked against the retained prospective rows:

| Existing seed-0 case | Old reference | Recorded legacy probe = prospective Rule A | Fresh current replay |
|---|---:|---:|---:|
| Hartmann6 qLogEI | 0.22786852462983065 | 0.19391397009622446 (C3) | 0.3038381093602984 |
| Ackley qLogEI | 0.5928006956256192 | 0.7649100065630514 (S1) | 0.9140845131035267 |
| Hartmann6 qLogNEI | 0.1699699208688239 | 0.19524908867226243 (C3) | 0.11127587899761282 |

All 12 stored scoring configurations for each prospective case share that Rule-A
scalar. This audit compares the **recorded** legacy probes; it did not rerun the
legacy monkeypatch or change production defaults. Inspection of `git show
1bf51f1:src/boec/optimizers.py` confirms the recovery code lacks the explicit
`seed=cfg.sampler_seed` added in `01d2ea5`. The original historical cause remains
unidentified. Scalar matches do not validate Rule P, maps or full trajectories.

## Conditional fixed-design sensitivity

For Fix 1, reanalyse all retained paired rows with the original 4,000-resample,
seed-0 bootstrap and Wilcoxon function. Change **only an in-memory copy** of
classical instance `033466197eba3ddb`, seed 0, Rule P from
0.2525116337195932 to the observed diagnostic 0.25251124591423746.

- Mean classical Rule-P change: -7.756107114342825e-9 (one of 50 rows).
- Rule-P minus Rule-A contrast: 0.10348625913954412 → 0.103486251383437.
- CI: [0.07225003121385253, 0.13667376335054549] →
  [0.07225003121385253, 0.13667375578834104].
- Wilcoxon p unchanged: 4.945666454148068e-8. Other arms unchanged, hence its Holm
  adjustment is unchanged. Four-decimal displays and selected-arm A/P ordering persist.
- A conservative all-resamples bound alone crossed a four-decimal rounding boundary
  for the lower endpoint; exact reanalysis, not that bound, established the unchanged
  display. No all-campaign stability conclusion follows from this one-row exercise.

P7 was rerun for the same one classical key with an explicit temporary output;
it still exits 1 at its map gate. Compare its 24 cells with matching keys in retained
P7, not merely with K6. Maximum calibration difference: 6.500910920692604e-13;
mean over the full 1,200-cell classical arm changes by 2.582836288594903e-15 when
only these cells are substituted in memory. Refinement and AUC differences are zero;
raw Brier mean shift is 2.9758371692760004e-15. Displayed means and ordering of the
four Figure 4A arms persist. No multi-arm inferential test or other campaign was cleared.

Fresh P7 diagnostic output: `/private/tmp/spade-claim-impact.XvCfVi/p7.json`.
It is an audit output, not a replacement publication dataset. The exact original
test also reruns this case in its own temporary directory.

## Reproduce and limits

`python -m pytest -q tests/test_replay_claim_impact.py` reproduces the primary
reaggregation, prospective-versus-recorded-legacy scalar comparison, conditional
Fix 1 bootstrap/Wilcoxon sensitivity, and manuscript scope checks. Original replay
tests remain separately failing. Temporary P7 cell comparison was an additional
read-only diagnostic; no inferred environment cause or general tolerance is approved.

Manuscript abstract/conclusions and cover letter now identify the archived benchmark;
a dedicated replay-impact subsection records these distinctions. Figures retain
their original data because the audit found no direct contradiction requiring a
numeric replacement. A separately specified validation study would be needed to
claim current-code regeneration or quantify robustness to sampler changes. Such a
study was not started. Public deposit, author signoff and submission remain gated.

## Publication verification

116 focused archive/claim-impact/manuscript/figure/layout/table/package tests passed
in 44.92 seconds. The nine prospective release checks passed without `--pre-release`.
All original eight replay gates were separately rerun and failed in 43.58 seconds.
The figures and scientific source/results remain unchanged. Word documents were
rebuilt: 41-page reading copy, 37-page submission copy, one-page cover letter.
At the same PDFium raster scale, 33 reading pages and 29 submission pages were
pixel-identical to their previously reviewed counterparts. All 17 changed/new pages
were individually visually inspected; no clipping or overlap was observed. Thus
visual coverage spans all 79 current pages, with 62 prior pixel-identical reviews reused.
