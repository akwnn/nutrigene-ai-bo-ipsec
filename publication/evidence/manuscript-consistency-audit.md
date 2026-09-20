# Manuscript scientific-claim consistency audit

**Audit status:** `DONE_WITH_CONCERNS`
**Scope:** `publication/manuscript/{MANUSCRIPT,METHODS,SUPPLEMENT,PROTOCOLS}.md`, root
`README.md`, and `publication/evidence/RESULTS-GUIDE.md`, checked against
`publication/manuscript/CLAIMS-AND-SOURCES.md`, canonical JSON, frozen analysers,
`software/scripts/verify_conclusions.py`, and the archived correction record. This is a
consistency audit, not a re-adjudication of the registered designs.

## Executive finding

The active documents use the corrected headline values and no stale `+0.001353` or LC
`+0.0016` value is presented as current evidence. The executable guard reports `12/12`
reproduced values, and direct runs of the DC, LC, TAU, and TT analysers reproduce the ledger's
numbers. The originally audited C5 aggregation was defective; the resolution addendum below
records the repaired estimand and current value. The manuscript otherwise retains the principal
adverse, null, negative, withdrawn, and future-work findings.

Publication readiness nevertheless has several material consistency gaps:

1. C5's original order-dependent, both-arm calculation has been repaired. The current
   SPADE-only, `c=1.0`, `alpha=0.95` descriptive rho is `0.9880098603391883`; it is valid with
   qualification because the 25 family-prevalence cells remain nested and no naive population
   p-value is justified.
2. The conclusion says SPADE “matches” qLogNEI, which is stronger than the adjudicated “no
   detectable difference” wording and can be read as the equivalence claim explicitly
   forbidden by C1.
3. Summary-level certification statements do not consistently carry all reporting dimensions
   required by L3/Supplement S2 (prevalence, noise, assurance, wells, rounds, seeds, answered,
   contained, and lower bound). The information is recoverable elsewhere, but the ledger says
   every certification claim must report it.
4. S2/S3 values reproduce from runnable code and committed inputs, but unlike C1/C3/C5/C6 they
   have no committed canonical result object and no automated conclusion guard. Their active
   evidence path is therefore weaker and partly dependent on rerunning long scripts or reading
   superseded narrative files.

## Consolidated disposition matrix

“Guarded” means the quoted result is checked by `software/scripts/verify_conclusions.py`; it
does not imply that the analysis or inferential assumptions are valid.

| Item | Current disposition | Automated guard | Submission blocker? | Basis / required action |
|---|---|---|---|---|
| C1 | Valid with qualification | Partial (mean, CI, n) | No | DC one-process contrast reproduces, but use “no detectable difference,” never “matches” or equivalence; `CLAIMS-AND-SOURCES.md:10-21`, `verify_conclusions.py:36-50` |
| C2 | Valid with qualification | Unguarded | No, if qualified | Counts reproduce, but inflation is selected and evaluated within the same DC sample and pooled CP inference assumes exchangeable independent answered cells; distinguish from C3 LOFO; `analyse_dc_doe_certificate.py:56-72,94-117` |
| C3 | Valid with qualification | Partial (mean, n only) | No | Registered LOFO calibration is out-of-family for selection, but flat bootstrap treats repeated family/seed/prevalence cells as independent; `analyse_lc_confirmatory.py:47-55,79-101,241-260` |
| C4 | Valid with qualification | Partial (mean only) | No | Mean reproduces; CI/n are unguarded and four-family × seed composition needs stating; `verify_conclusions.py:93-109` |
| C5 | Valid with qualification | Guarded (rho, 25 cells, canonical completeness) | No | Repaired SPADE-only `c=1.0`, `alpha=0.95` estimand uses mean of 64 unique seed margins per cell; rho `0.9880098603391883`; nested cells prohibit naive population inference; `analyse_tau_sweep.py:28-87,138-175`, `verify_conclusions.py:69-80` |
| C6 | Valid with qualification | Partial (SPADE counts/LB) | No | SPADE Hill result reproduces independently of C5 rho, but depends on pooled CP assumptions and must retain qLogNEI/denominator caveat; `verify_conclusions.py:84-91`, `CLAIMS-AND-SOURCES.md:73-82` |
| S1 | Valid with qualification; unguarded | Unguarded | No | TT point estimates reproduce; bootstrap is flat across heterogeneous family/seed units; `analyse_tt_theta_tau.py` and TT JSON |
| S2 | Valid with qualification; unguarded | Unguarded | No | Runnable retrospective support, not prospective validation; commit structured outputs and guard values; `CLAIMS-AND-SOURCES.md:96-103` |
| S3 | Valid with qualification; unguarded | Unguarded | No | Runnable assay-specific LOO result, but LOO predicts observations rather than latent truth; `CLAIMS-AND-SOURCES.md:105-111` |
| L1 | Valid with qualification; unguarded | Unguarded | No | Mandatory negative ceiling currently relies on archived exploratory result/chain; promote or explicitly cite it; `CLAIMS-AND-SOURCES.md:115-119` |

## Adjudicated finding inventory

| Class | Ledger item / finding | Current wording and disposition | Evidence |
|---|---|---|---|
| Allowed, bounded | C1: SPADE R5 versus qLogNEI R10 regret | `-0.0005`, CI `[-0.0221,+0.0207]`, `p=0.96`, `n=160`; only “no detectable difference” is allowed | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:10-21`; canonical `research/results/comparisons/dc-*.json`; `software/scripts/analyse_dc_doe_certificate.py`; guard `software/scripts/verify_conclusions.py:36-50` |
| Adverse | C2: screened DoE beats SPADE on regret | SPADE-minus-DoE `+0.1026`, CI `[+0.0486,+0.1578]`, `p=0.0003`, `n=160`; DoE uses 3 rounds versus SPADE 5 | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:23-34`; manuscript `publication/manuscript/MANUSCRIPT.md:93-107`; DC JSON/analyser |
| Allowed with abstention denominator | C2: certificate containment | SPADE 66/160 answered and 66 contained; screened DoE 122/160 and 85; unscreened 134/160 and 77, at prevalence 0.30 | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:25-30`; manuscript `publication/manuscript/MANUSCRIPT.md:100-107`; DC JSON/analyser |
| Corrected allowed | C3: matched-R5 certified volume | `+0.000855`, CI `[+0.000691,+0.001028]`, `p<0.0001`, `n=320`; registered LOFO only | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:36-52`; LC JSON; `software/scripts/analyse_lc_confirmatory.py`; guard `software/scripts/verify_conclusions.py:52-67` |
| Allowed | C4: SPADE R3 versus one-shot LHS regret | `-0.0783`, CI `[-0.1104,-0.0490]`, `n=80`; unmatched families are not imputed | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:54-60`; LC/LA JSON; `publication/manuscript/PROTOCOLS.md:20-28`; guard `software/scripts/verify_conclusions.py:93-109` |
| Exploratory/explanatory, valid with qualification | C5: margin/noise association | Repaired descriptive rho `0.9880098603391883`: SPADE-only at `c=1.0`, `alpha=0.95`; mean of 64 unique seed margins and SPADE answer rate in each of 25 nested cells; no naive p inference | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:62-76`; TAU JSON; `software/scripts/analyse_tau_sweep.py:28-87,138-175`; guard `software/scripts/verify_conclusions.py:69-80` |
| Allowed subgroup | C6: Hill at prevalence 0.70 | SPADE 40/64 answered, 40/40 contained, LB `0.9278`; qLogNEI also 27/27 perfect observed containment but has insufficient count for the registered LB rule | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:73-82`; TAU JSON/analyser; guard `software/scripts/verify_conclusions.py:84-91` |
| Null and adverse mechanism result | S1: corrected targeting | Volume `+0.000425`, CI crosses zero; regret worsens `+0.0301`, CI `[+0.0169,+0.0450]`, `p<0.0001`; Hartmann6/Ackley effects cancel | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:86-94`; TT JSON/analyser; manuscript `publication/manuscript/MANUSCRIPT.md:126-133` |
| Supporting, retrospective | S2: mean-marginalization | Benchmark width `1.004x-1.011x`, in-house `484x`, Hall/Ogle `297x`; not prospective validation | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:96-103`; scripts `software/scripts/run_real_ipsc_certification.py`, `software/scripts/certify_hall_ogle.py`; inputs under `research/data/lab/derived/` and `research/data/published/` |
| Supporting, limited | S3: assay-specific LOO inflation | In-house `c=0.712`, Hall/Ogle `c=0.526`; predicts observations, not latent truth | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:105-111`; calibration scripts and inputs above |
| Negative ceiling | L1 | At real-assay relative noise near `0.68`, no tested arm certifies | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:115-119`; archived registered/result chain `archive/superseded-spade/docs/SPADE-REALISTIC-NOISE-SPEC.md:67-75,159-169`; exploratory canonical result `archive/exploratory/results/k1-noise-ceiling.json` |
| Provisional/null validation status | L2 | In-house data are `awaiting_human_signoff`; no prospective wet-lab validation | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:121-125`; `software/src/boec/lab/dataset.py:236,268`; active prose `publication/manuscript/MANUSCRIPT.md:137-144` |
| Withdrawn | C3 R3 volume effect | At 32 seeds SPADE-minus-qLogNEI is negative (`-0.000073`, CI `[-0.000119,-0.000036]`); no positive R3 volume claim survives | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:51-52`; manuscript `publication/manuscript/MANUSCRIPT.md:83-87`; LC analyser output from `research/results/comparisons/lc-*.json` |
| Superseded | C1 LC cross-run point estimate | LC `+0.0016` is superseded by one-process DC `-0.0005` | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:20-21`; protocol `publication/manuscript/PROTOCOLS.md:36-39`; DC and LC analysers |
| Superseded/unsupported | Historical C3 `+0.001353` | Rejected; frozen executable path gives `+0.0008546875` | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:42-49`; methods `publication/manuscript/METHODS.md:47-53`; archived stale instances include `archive/superseded-spade/docs/SPADE-LC-CONFIRMATORY-SPEC.md:189-216` and `archive/superseded-spade/docs/SPADE-PAPER-ARGUMENT.md:128` |
| Future work / unresolved | L4 and supplement S6 | R4, broader assurance/rho sweep, larger budgets, replicate-tube identification, prospective campaign, and cost/calendar measurements remain open | Ledger `publication/manuscript/CLAIMS-AND-SOURCES.md:133-136`; manuscript `publication/manuscript/MANUSCRIPT.md:161-168`; supplement `publication/manuscript/SUPPLEMENT.md:54-63` |

## Detailed findings

### C0 — Original C5 defect and resolution addendum

**Original defect (preserved for audit history).** The first audited C5 estimate could not be
treated as validated merely because the guard reproduced `0.9801`. The former
`software/scripts/analyse_tau_sweep.py:28-42` assigned
`diff[(family, p)] = margin_sd`. That key omits seed and arm, so later rows silently overwrite
earlier rows. This is harmless for the four fixed-landscape families, but not for Hill: the
committed `research/results/generalization/tau-hill.json` contains **40 distinct** `margin_sd`
values at each prevalence (for example, at `p=0.70` they span approximately `0.6034` to
`0.7688`). The retained Hill value is therefore whichever eligible row happens to occur last;
changing row or file order can change `xs` and hence rho without changing the scientific data.

The response variable is also not the claim as worded. The analyser labels the table “pooled
over arms” (`software/scripts/analyse_tau_sweep.py:93-101`) and `pooled()` selects only family,
prevalence, and `c=1.0`, not arm. Thus each answer rate combines SPADE and qLogNEI observations,
even though the paper presents the result as an explanation of SPADE certifiability
(`publication/manuscript/MANUSCRIPT.md:109-124`) and C5 says margin/noise explains answer rate
without declaring this arm mixture (`publication/manuscript/CLAIMS-AND-SOURCES.md:62-71`).

The former `software/scripts/verify_conclusions.py:69-82` imported those same functions. Its
successful check was circular reproduction of the defective aggregation, not independent
validation. The former `p<0.0001` additionally treated 25 constructed family-prevalence cells
as ordinary observations despite five prevalences being repeated within each family.

**Resolution addendum.** The analyser now keys margins by `(family, seed, prevalence)`, rejects
inconsistent duplicates, and validates the complete 5-family × 64-seed × 2-arm × 5-prevalence
× 4-inflation canonical grid (`software/scripts/analyse_tau_sweep.py:28-87`). The defined
primary estimand fixes SPADE, `c=1.0`, and `alpha=0.95`: within each family-prevalence cell,
`x` is the mean of the 64 unique seed-specific margins and `y` is SPADE answer rate
(`software/scripts/analyse_tau_sweep.py:51-68,138-164`). It gives descriptive Spearman rho
`0.9880098603391883` over 25 cells. Median-margin sensitivity gives the same rho and the
qLogNEI-only sensitivity gives `0.9682461469` (`software/scripts/analyse_tau_sweep.py:166-175`).
The guard now invokes canonical completeness validation and the repaired point constructor
(`software/scripts/verify_conclusions.py:69-80`). Active wording has been updated in the ledger
(`publication/manuscript/CLAIMS-AND-SOURCES.md:62-76`), Methods
(`publication/manuscript/METHODS.md:55-60,76-80`), manuscript, supplement, README, and results
guide.

**Current disposition:** valid with qualification, no longer a submission blocker. The result
is descriptive rather than population inference: the 25 cells remain nested within five
families and share ordered prevalence levels, so they are dependent and non-exchangeable. The
repaired analyser correctly prints no naive correlation p-value
(`software/scripts/analyse_tau_sweep.py:163-175`). Causal wording such as “governs” remains
stronger than this descriptive association supports.

### M0 — DC/C2 uses within-sample calibration, unlike LC/C3 LOFO (material)

C2's certificate verdict selects the smallest inflation `c` on the pooled DC cells and reports
containment on those same cells: `best_c()` calls `cert()` for selection
(`software/scripts/analyse_dc_doe_certificate.py:56-72`) and the selected result is immediately
reported on the same `cells` at `software/scripts/analyse_dc_doe_certificate.py:94-117`.
`publication/manuscript/PROTOCOLS.md:13-18` describes the grid and gate but does not call out
this within-sample selection/evaluation.

C3 is materially different: `lofo()` selects `c` on all families except the held-out family
and evaluates volume on that held-out family (`software/scripts/analyse_lc_confirmatory.py:79-101`),
as correctly stated in `publication/manuscript/CLAIMS-AND-SOURCES.md:38-49` and
`publication/manuscript/METHODS.md:47-53`. The current narrative can make both claims sound
equally out-of-sample. C2 remains a useful empirical descriptive comparison, but “trustworthy”
and “guarantee” should be qualified as observed, within-sample calibrated containment; it is
not the LOFO generalization evidence used for C3.

### M0b — Flat bootstrap and pooled Clopper–Pearson ignore dependence (material)

The frozen `boot()` implementations resample individual contrast rows as if exchangeable
(`software/scripts/analyse_dc_doe_certificate.py:45-53`,
`software/scripts/analyse_lc_confirmatory.py:47-55`, and
`software/scripts/analyse_tau_sweep.py:45-53`). This is a flat bootstrap, although observations
are nested/repeated by family, seed, prevalence, and sometimes arm. Most notably C3's `n=320`
contains repeated prevalence cells for common family/seed campaigns, and TAU repeats five
prevalences per family and shares landscapes/seeds across arms. The quoted CIs and p-values may
therefore be too narrow if within-cluster correlation is ignored.

Likewise `cp_lower()` applies an ordinary binomial Clopper–Pearson bound to pooled answered
cells (`software/scripts/analyse_dc_doe_certificate.py:24-25,56-72` and
`software/scripts/analyse_lc_confirmatory.py:24-25,58-68`). That bound assumes exchangeable,
independent Bernoulli trials; pooling heterogeneous families and repeated outcomes from shared
campaigns/landscapes does not establish those assumptions. The manuscript currently calls the
regions “empirically trustworthy” (`publication/manuscript/MANUSCRIPT.md:148-152`) without this
dependence limitation.

**Required qualification/reanalysis:** state the unit of resampling and the exchangeability
assumption; prefer cluster/hierarchical resampling at the independent campaign or landscape
level and a clustered/hierarchical containment interval. Until then, present bootstrap CIs,
p-values, and pooled lower bounds as conditional descriptive summaries of the registered
benchmark rather than population-level guarantees.

### M1 — C1 claim-strength drift in the conclusion (material)

`publication/manuscript/MANUSCRIPT.md:172-176` says SPADE “matches noisy BO on observed
regret.” The C1 ledger permits only “no detectable regret difference,” forbids proof of
equivalence, and notes that the interval is wider than the registered `0.02` SESOI
(`publication/manuscript/CLAIMS-AND-SOURCES.md:12-21`). The body is correctly cautious at
`publication/manuscript/MANUSCRIPT.md:72-79`, and the root summary is correctly cautious at
`README.md:23-24`; the conclusion should use the same wording. “BO can match optimization
quality” in `publication/manuscript/MANUSCRIPT.md:24-26` is similarly susceptible to an
equivalence reading, though the immediately preceding estimate and the final sentence's scope
make it less severe.

**Required correction:** replace “matches” with “showed no detectable regret difference from”
and retain the non-equivalence caveat.

### M2 — Required certification dimensions are not local to each claim (material)

L3 requires every certification claim to report answered and contained counts **plus**
prevalence, noise, confidence, wells, rounds, and seeds
(`publication/manuscript/CLAIMS-AND-SOURCES.md:127-131`). Supplement S2 additionally requires
family and inflation-selection rule (`publication/manuscript/SUPPLEMENT.md:17-22`), and the
shared frozen rules repeat the obligation (`publication/manuscript/PROTOCOLS.md:64-69`).

Non-compliant or ambiguous summaries include:

- Root `README.md:27-30`: C2 and C6 carry counts/prevalence but omit confidence/lower bound,
  assurance, inflation rule, seeds, and (locally) noise/wells/rounds.
- `publication/evidence/RESULTS-GUIDE.md:23-26`: C6 names Hill only as a biologically shaped
  case and does not state its 40/64 answered denominator, 40 contained, LB, prevalence, or
  inflation.
- `publication/manuscript/SUPPLEMENT.md:7-15`: the status table compresses C2 to qualitative
  containment and C6 to 40/40, omitting the 40/64 answer denominator and LB.
- `publication/manuscript/MANUSCRIPT.md:100-107`: C2 gives answered/contained and LB for SPADE,
  but not the DoE lower bounds and not the local assurance/inflation-selection statement.
- `publication/manuscript/MANUSCRIPT.md:118-124`: C6 is comparatively complete, but noise,
  assurance, wells, rounds, and seeds are inherited from earlier sections rather than stated
  with the certificate claim.

The values are not false, but the paper's own mandatory reporting rule is stricter than the
current summaries. Either make L3 explicitly apply to full certificate tables/primary result
paragraphs, or add the missing dimensions wherever certification is summarized.

### M3 — S2/S3 lack committed result artifacts and automated guards (material provenance gap)

S2/S3 are repeated quantitatively in `publication/manuscript/MANUSCRIPT.md:137-143`,
`publication/manuscript/SUPPLEMENT.md:48-52`, and the ledger
`publication/manuscript/CLAIMS-AND-SOURCES.md:96-111`. The listed scripts reproduce the current
figures from committed inputs: the in-house scripts report raw posterior SD `0.007`,
mean-marginalized `3.388`, and raw LOO `c=0.712`; the Hall/Ogle script reports `0.0003` to
`0.0818` (`297.5x`) and raw LOO `c=0.526`. However:

- `research/results/real-cell/` contains only `replay-hall-ogle.log`, not canonical structured
  S2/S3 result objects;
- `software/scripts/verify_conclusions.py:3-4` claims to cover quantitative statements in the
  ledger/manuscript but actually checks only C1, C3, C5, C6, and the C4 mean
  (`software/scripts/verify_conclusions.py:36-109`);
- the benchmark `1.004x-1.011x` range is supported in the active tree only indirectly through
  code and archived narrative/result material such as
  `archive/exploratory/results/probe-meanmarg-benchmarks.json` and
  `archive/superseded-spade/docs/SPADE-REAL-IPSC-RESULT.md:104-107`.

**Required correction:** commit machine-readable S2/S3 result summaries (including input and
code provenance) and guard every quoted value, or narrow the guard's stated coverage and mark
these figures explicitly as manually reproduced support.

### M4 — `verify_conclusions.py` overstates quantitative coverage (material tooling/documentation gap)

The module docstring says it covers quantitative statements in the entire ledger and
manuscript (`software/scripts/verify_conclusions.py:1-12`). It does not check C2 counts,
fractions, lower bounds, regret contrast/CI/p-value; the C3 CI/p-value; the C4 CI and `n`; C5
`p`; C6 qLogNEI counts; any S1 figure; any S2/S3 figure; or L1's `0.68` ceiling. The final
“12/12 doc numbers” message (`software/scripts/verify_conclusions.py:111-112`) can therefore be
misread as exhaustive coverage.

`publication/evidence/RESULTS-GUIDE.md:48-51` more accurately calls these “headline values,”
while root `README.md:25-26` says the corrected C3 interval is “guarded” even though only its
mean and `n` are guarded. Expand the guard or state its exact subset everywhere.

### M5 — C4 denominator composition is under-described (moderate)

C4 reports `n=80` (`publication/manuscript/CLAIMS-AND-SOURCES.md:56-59` and
`publication/manuscript/MANUSCRIPT.md:89-91`), while general study-design prose says five
families and 32 seeds (`publication/manuscript/METHODS.md:5-7`). Protocol LA explains that
unmatched families are not imputed (`publication/manuscript/PROTOCOLS.md:20-28`), and the
canonical pairing uses four LA families, but no active narrative states the exact family × seed
composition producing 80 pairs. Add that composition so readers do not infer that C4 uses the
five-family/32-seed design.

### M6 — “All main experiments” is too broad for the varied seed counts (moderate)

`publication/manuscript/METHODS.md:5-7` states “Main experiments used ... 32 deterministic
seeds per family.” TAU/C5/C6 uses 64 seeds per family
(`publication/manuscript/PROTOCOLS.md:47-49`), and C4 has `n=80` across four matched families.
The manuscript itself correctly states 64 for Hill at `publication/manuscript/MANUSCRIPT.md:120`
and the protocol is unambiguous, but the Methods opener should say “main DC/LC experiments” or
enumerate the exceptions.

### M7 — Real-noise ceiling relies on archived exploratory evidence (moderate)

L1 is mandatory and consistently retained in the manuscript, supplement, and README
(`publication/manuscript/MANUSCRIPT.md:161-168`, `publication/manuscript/SUPPLEMENT.md:54-63`,
`README.md:77-82`). Its active claim-ledger entry supplies no canonical-result or analyser path
(`publication/manuscript/CLAIMS-AND-SOURCES.md:115-119`). The evidentiary chain lives in the
archived `SPADE-REALISTIC-NOISE-SPEC.md` and exploratory `k1-noise-ceiling.json`. Because L1
constrains every headline, promote a compact canonical ceiling result/guard or explicitly cite
the archived path in the ledger.

### M8 — Qualitative claims without explicit ledger IDs (minor traceability)

The prose contains qualitative scientific interpretations whose intended ledger parent is
inferable but not explicit: screen removal “worsened rather than repaired containment”
(`publication/manuscript/MANUSCRIPT.md:100-105`, presumably C2); Hill is the closest biological
shape (`publication/manuscript/MANUSCRIPT.md:118-120`, C6); and targeting effects “cancelled”
(`publication/manuscript/MANUSCRIPT.md:126-133`, S1). No inline claim tags are used anywhere.
This does not contradict the ledger, but an explicit C2/C6/S1 cross-reference would prevent
these qualitative conclusions from becoming orphan claims during editing.

## Cross-document consistency notes

- Corrected C1 is consistently sourced from DC in `MANUSCRIPT.md:74-79`, `METHODS.md:70-76`,
  `PROTOCOLS.md:7-18,39`, `README.md:23-24`, and `RESULTS-GUIDE.md:10-19,48-50`.
- Corrected C3 `+0.000855` is consistent in all reviewed files; every active mention of
  `+0.001353` labels it stale/unsupported rather than current.
- The Hill subgroup remains inside the five-family dataset and its truth-dependent diagnostic
  caveat is retained (`MANUSCRIPT.md:109-124`, `SUPPLEMENT.md:24-31`,
  `RESULTS-GUIDE.md:21-29`). C5 now uses the mean of unique seed-specific Hill margins and
  SPADE-only answer rate, eliminating the original overwrite and arm-pooling defects.
- The adverse DoE result and the null/adverse TT result are not suppressed. The manuscript
  explicitly says DoE finds the stronger point recipe faster and targeting harms regret.
- Prospective-validation, human-signoff, DoE-scope, cost/calendar, R4, larger-budget, and
  replicate-tube limitations are retained. No active document promotes archived exploratory
  experiments to confirmatory status.
- Paths named by the reviewed active documents exist. The main stale-path risk is evidentiary,
  not filesystem breakage: S2/S3 and L1 point to scripts/inputs or archived chains rather than
  committed active result summaries.

## Verification record

- `.venv/bin/python software/scripts/verify_conclusions.py` — **pass**, `12/12` guarded values.
- `.venv/bin/python software/scripts/analyse_dc_doe_certificate.py` — reproduces C1/C2.
- `.venv/bin/python software/scripts/analyse_lc_confirmatory.py` — reproduces corrected C3 and
  the negative/withdrawn R3 result.
- `.venv/bin/python software/scripts/analyse_tau_sweep.py` — repaired C5 reports descriptive
  rho `0.9880098603391883`, validates canonical completeness, and reproduces C6. Nested-cell
  dependence remains an explicit limitation.
- `.venv/bin/python software/scripts/analyse_tt_theta_tau.py` — reproduces S1 null/adverse
  findings.
- In-house real-data and LOO scripts reproduce `484x` and `c=0.712`; Hall/Ogle output reached
  and reproduced `297.5x` and `c=0.526` before the deliberately long downstream certificate
  grid was interrupted. These values are not currently guarded.

## Publication decision

`DONE_WITH_CONCERNS`. No transcription-level headline contradiction was found. The original C5
submission blocker is resolved; current C5 is valid with the explicit nested-cell,
non-exchangeability, and no-naive-p-value qualification. M0/M0b still require explicit
calibration and dependence qualification (preferably reanalysis), and M1-M4 should also be
resolved before treating the package as publication-ready. M5-M8 are traceability and
interpretation hardening items that should be addressed in the same pass if feasible.
