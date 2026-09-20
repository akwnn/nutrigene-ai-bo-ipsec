# Active SPADE pipeline audit

**Audit scope.** This report traces the active, publication-facing pipeline from executable
code, configuration, committed inputs/results, and tests. Archived specifications and prose
were not used as evidence. The manuscript files are cited only to identify the role assigned to
an artefact or result. All paths and line numbers refer to the current publication-ready tree.

**Overall finding: usable with material qualification.** The five synthetic studies are
internally connected through a common six-dimensional oracle/GP/certificate stack and their
canonical result files have the expected balanced row counts. The headline guard reproduces
C1, C3--C6. However, the active pipeline has four material audit issues: (1) LC's runner default
is 25 seeds while the protocol and committed results are 32; (2) LC calibration and C3 pool two
prevalences without naming that estimand; (3) TAU reduces seed-varying Hill difficulty to the
last encountered seed while pooling answer rate over all seeds and both arms; and (4) the split
canonical JSON arrays carry neither provenance nor an explicit completeness record. S1 and the
real-cell claims are also absent from the numeric conclusion guard.

## 1. Shared synthetic pipeline

### Scientific object, dimension, families, and noise

All DC/LC/LA/TAU/TT runners eventually import `run_p8_certificate_families.py`. Its live
constants are dimension 6, relative noise 0.25, and 4,096 joint posterior draws
(`software/scripts/run_p8_certificate_families.py:67-74`). The families are Ackley,
Hartmann6, Hill, Levy, and Rosenbrock (`software/scripts/run_p8_certificate_families.py:67-71`).
Hill is an ensemble while each other family is one fixed landscape: the P8 key construction
uses ensemble instance/seed pairs for Hill and family-name plus seeds for the other four
(`software/scripts/run_p8_certificate_families.py:117-144`). LC maps Hill seed modulo the
loaded ensemble and leaves all other instance IDs equal to the family label
(`software/scripts/run_lc_confirmatory.py:43-49`). Thus seed-to-seed variability is landscape
plus noise for Hill, but primarily design/noise realization for the other families.

The oracle supplies per-well variance for BO/SPADE. DC's DoE adapters do not retain their
per-well variances; they replace them with one constant plug-in variance,
`sigma_rel^2 * mean(abs(Y))^2`, for every well (`software/scripts/run_dc_doe_certificate.py:41-57`).
This makes the downstream GP/certificate code common but does **not** make the observation-noise
model identical across arms.

### Surrogate, design, acquisition, and schedules

The common fitted surrogate is a `SingleTaskGP` built with known observation variance and
explicit unit-cube bounds. The production default is a product ARD Matérn structure, learned
scale, standard outcome transform, dimension-scaled lengthscale prior, one fit restart, and no
input warping (`software/src/boec/surrogate.py:331-345`, `software/src/boec/surrogate.py:346-421`).
The qLogNEI arm is the ordinary `Campaign` path (`software/scripts/run_lc_confirmatory.py:52-72`).

For 48 wells, non-10-round LC schedules use 8-well adaptive batches and opening size
`48 - 8(R-1)`: R3 = 32+8+8 and R5 = 16+8+8+8+8. qLogNEI R10 instead uses the campaign
default 14-point opening and batches `4 x 8 + 2` (`software/scripts/run_lc_confirmatory.py:60-69`;
the generic split is `software/src/boec/campaign.py:111-146`). SPADE refits after every batch,
uses a fresh 2,000-point Sobol candidate set each round, and greedily selects with a Chebyshev
exclusion radius (`software/src/boec/multiround.py:122-153`). Its acquisition is
`1.96 sd - |mean - z_rho sd - theta|` with rho 0.95
(`software/src/boec/certstraddle.py:82-108`). In the committed path theta is 0.8 of a supplied
`mu_max=1.0`; in the observed operating regime theta cancels from the ranking and the rule acts
as UCB with exploration weight `1.96-z_0.95` (`software/src/boec/multiround.py:13-35`,
`software/src/boec/multiround.py:76-103`). TT is the explicit test of replacing 0.8 with tau.

LA is a separate two-round lineage. `versionb` and `spade_cert_rho95` use 40+8 wells;
`qlognei_r2` matches 40+8; `qlognei_r10` uses 14 plus eight fours plus two; `lhs` is one-shot
48 (`software/scripts/run_la_round_matched.py:43-68`). The comment that the only difference
between all arms is the last eight wells is therefore too broad: it holds only for the two-round
arms, not qLogNEI R10 or LHS (`software/scripts/run_la_round_matched.py:43-44`).

### Targets and certification

Targets are per-instance quantiles of noiseless truth on a 20,000-point Sobol grid, seed 0;
certificates and empirical truth containment are evaluated on a 2,000-point Sobol subset
(`software/scripts/run_p2_versionb_gamma.py:156`, `software/scripts/run_lc_confirmatory.py:91-105`).
The active studies use 4,096 posterior draws inherited from P8. Inflation multiplies the joint
posterior Cholesky factor while retaining the same standard-normal draws for all `c` values
(`software/scripts/run_lc_confirmatory.py:124-142`). The certificate scans 64 Vorob'ev levels
and takes the largest quantile whose same-draw joint model containment reaches alpha
(`software/src/boec/vorobev.py:151-184`). The stored `ce_contain_*` is therefore circular;
all active analysers correctly adjudicate against `ce_empirical_0.95` and exclude empty sets
(e.g. `software/scripts/analyse_lc_confirmatory.py:28-44`). The selected reporting alpha is
0.95; stored secondary alphas are 0.50 and 0.80. The alternative split-draw estimator exists
but is not used in these runners (`software/src/boec/vorobev.py:187-231`).

Certification requires empirical-containment lower bound >=0.90 and answer rate >=0.05.
The lower bound is a one-sided 95% Clopper--Pearson beta quantile
(`software/scripts/analyse_dc_doe_certificate.py:17-25`, `software/scripts/analyse_dc_doe_certificate.py:67-72`).
Paired mean differences use 8,000 ordinary nonparametric bootstrap resamples of the flat list
of family/seed cells and percentile endpoints; the reported p value is twice the smaller
bootstrap sign fraction (`software/scripts/analyse_dc_doe_certificate.py:45-53`). This is a
cell-level, not family-cluster or hierarchical, bootstrap. Since four families have one fixed
landscape, intervals principally quantify run/noise variation conditional on these five
families, not population-level generalization to new response families.

The canonical synthetic schema contains family, seed, arm, rounds where applicable, regret,
prevalence, inflation, well count in DC/LC/LA/TAU, and alpha-star/deviation plus
empty/volume/internal-containment/empirical-containment at three alphas. TAU adds
margin/noise fields; TT adds `theta_used` but omits `n_wells` and tau. Canonical files are bare
arrays, so configuration, software versions, input hashes, completion status, expected key
count, and producing command cannot be recovered from the result itself.

## 2. DC -- unified SPADE/BO/DoE comparison

- **Question and manuscript role:** Does SPADE match BO recipe quality while producing an
  empirically trustworthy region that screened or unscreened low-order DoE does not? DC is the
  one-process source for C1 and C2 and supersedes LC for C1
  (`publication/manuscript/CLAIMS-AND-SOURCES.md:10-34`).
- **Design/status:** five families x seeds 0--31 x 48 wells, d=6, sigma_rel=0.25. Arms are
  screened DoE R3, unscreened DoE R3, SPADE R5, and qLogNEI R10; prevalences 0.70/0.30 and
  inflation 1/1.5/2/3 (`software/scripts/run_dc_doe_certificate.py:20-23`,
  `software/scripts/run_dc_doe_certificate.py:60-76`). Each canonical family file has 1,024
  rows = 32 seeds x 4 arms x 2 prevalences x 4 inflations.
- **DoE detail:** the screened path calls the active two-stage DoE and defaults to retaining
  four of six factors; stage 1 uses a two-level screen plus centres, stage 2 a face-centred CCD,
  then a confirmation, exactly closing the 48-well budget (`software/src/boec/doe.py:192-223`,
  `software/src/boec/doe.py:263-280`). The unscreened active arm is a separate function selected
  at the runner boundary (`software/scripts/run_dc_doe_certificate.py:46-52`).
- **Estimands/gates:** at p=0.30, choose the smallest c satisfying the binomial/answer rule per
  arm, compare answered/contained counts, bootstrap paired terminal regret, and diagnose
  screened versus unscreened at c=1 (`software/scripts/analyse_dc_doe_certificate.py:94-149`).
  Canonical outcome: C1 SPADE-qLogNEI regret -0.0005, CI [-0.0221,0.0207], n=160; C2 SPADE
  66/160 answered and 66 contained, while DoE containment is adverse
  (`publication/manuscript/CLAIMS-AND-SOURCES.md:15-32`).
- **Runner/analyser/results:** `software/scripts/run_dc_doe_certificate.py`;
  `software/scripts/analyse_dc_doe_certificate.py`; five `research/results/comparisons/dc-*.json`.
- **Tests/guards:** `verify_conclusions.py` recomputes C1 from DC and asserts n=160 and estimate/CI
  (`software/scripts/verify_conclusions.py:36-50`); `test_current_conclusion_guard.py` executes it
  (`software/tests/test_current_conclusion_guard.py:9-21`); the repository audit requires all
  five named files (`software/tests/test_repository_audit.py:163-181`). There is no direct guard
  for C2 counts, calibration choice, row balance, or DoE noise substitution.
- **Concern:** c is selected and evaluated on the same DC cells; unlike LC there is no held-out
  calibration (`software/scripts/analyse_dc_doe_certificate.py:56-72`). The headline happens at
  c=1, but the procedure permits optimistic in-sample selection. Exceptions are logged and
  skipped, and a bare array is written at the end without a completeness gate
  (`software/scripts/run_dc_doe_certificate.py:94-135`).

## 3. LC -- confirmatory BO and matched-round certificate volume

- **Question and manuscript role:** compare SPADE and qLogNEI in one process across round counts;
  LC supplies C3 (matched R5 certified volume) and the SPADE R3 half of C4, while DC supplies C1
  (`publication/manuscript/PROTOCOLS.md:30-39`).
- **Design/status:** five families, committed seeds 0--31, 48 wells, d=6, sigma_rel=0.25;
  SPADE R3/R5 and qLogNEI R3/R5/R10; p=0.30/0.10; c=1/1.5/2/3
  (`software/scripts/run_lc_confirmatory.py:22-25`, `software/scripts/run_lc_confirmatory.py:98-105`).
  Each canonical file has 1,280 rows = 32 x 5 x 2 x 4.
- **Calibration/estimand:** the registered path chooses the first c that passes on four families
  and evaluates volume/containment on the held-out family (`software/scripts/analyse_lc_confirmatory.py:58-101`).
  Importantly, both calibration and scoring pool p=0.30 and p=0.10: neither `pooled` nor `lofo`
  filters prevalence. C3's n=320 is 5 families x 32 seeds x **2 prevalences**, not 320 campaigns.
  The claim ledger calls this the “five-family benchmark” but does not state that expected volume
  averages two target prevalences (`publication/manuscript/CLAIMS-AND-SOURCES.md:36-52`).
- **Canonical outcome:** SPADE-qLogNEI R5 volume +0.000855, CI
  [+0.000691,+0.001028], n=320 (`publication/manuscript/CLAIMS-AND-SOURCES.md:38-49`). The analyser
  also includes explicitly post-hoc leave-one-seed-out output because LOFO becomes degenerate
  under saturated families (`software/scripts/analyse_lc_confirmatory.py:104-164`); this is not
  the C3 estimand.
- **Runner/analyser/results:** `run_lc_confirmatory.py`; `analyse_lc_confirmatory.py`; five
  `research/results/comparisons/lc-*.json`.
- **Tests/guards:** C3's LOFO mean and n are guarded (`software/scripts/verify_conclusions.py:52-67`),
  and all LC filenames are repository-audit requirements. No test pins fold-specific c choices,
  prevalence pooling, interval endpoints, or complete arm/family/seed balance.
- **Mismatch:** the live runner still defaults to **25** seeds
  (`software/scripts/run_lc_confirmatory.py:75-83`) while the active protocol says 32 and the
  committed JSONs contain 32 (`publication/manuscript/PROTOCOLS.md:36-38`). The analyser regards
  >=25 unique seed IDs as non-partial (`software/scripts/analyse_lc_confirmatory.py:198-210`), so a
  default run can look complete while failing the publication design. Its global seed count can
  also conceal a missing family/arm cell. Exceptions are skipped and final output has no
  completeness record (`software/scripts/run_lc_confirmatory.py:114-155`).

## 4. LA -- two-round and one-shot lineage

- **Question and manuscript role:** isolate acquisition versus adaptivity at fixed wells and
  compare one-shot LHS with adaptive SPADE. For the paper, only LHS regret is paired with LC
  SPADE R3 to support C4 (`publication/manuscript/PROTOCOLS.md:20-28`).
- **Design/status:** four non-Hill families x 20 seeds x 48 wells. Arms are Version B R2,
  certificate-straddle rho=.95 R2, qLogNEI R2, qLogNEI R10, and LHS R1; targets p=0.30/0.10/
  0.03/0.01; c=1/1.5/2/3/4 (`software/scripts/run_la_round_matched.py:20-24`,
  `software/scripts/run_la_round_matched.py:105-126`). Each canonical file has 2,000 rows =
  20 x 5 x 4 x 5. Hill is deliberately absent.
- **Calibration/estimands:** LA's own analyser selects c leave-one-family-out while pooling all
  four prevalences, then bootstraps paired volume differences for the best of two SPADE arms
  against qLogNEI R2 (`software/scripts/analyse_la_round_matched.py:44-99`,
  `software/scripts/analyse_la_round_matched.py:122-146`). Selecting the “best SPADE arm” on the
  same held-out estimates is not selection-adjusted. This LA-1 result is not the final manuscript
  claim. C4 instead pairs 80 common family/seed keys: LC SPADE R3 minus LA LHS, yielding -0.0783
  (`software/scripts/verify_conclusions.py:93-109`).
- **Runner/analyser/results:** `run_la_round_matched.py`; `analyse_la_round_matched.py`; four
  `research/results/comparisons/la-*.json`.
- **Tests/guards:** only C4's mean (with a loose tolerance 0.004) is guarded; its CI, n, schedule,
  and the LA analyser's own gates are not. Named-file presence is guarded by repository audit.
- **Ambiguity:** LA canonical rows contain no `rounds` field. Schedules must be inferred from arm
  names/code, unlike DC/LC/TAU/TT. The analyser does not print seed counts or reject partial
  files. The runner catches exceptions and still writes a bare final array
  (`software/scripts/run_la_round_matched.py:126-147`).

## 5. TAU -- prevalence generalization and margin/noise explanation

- **Question and manuscript role:** determine whether certifiability across the five families and
  five prevalences tracks true excursion margin relative to noise, and test Hill at easier
  prevalence. TAU supplies C5 and C6 (`publication/manuscript/CLAIMS-AND-SOURCES.md:62-82`).
- **Design/status:** five families x **64 committed seeds** x SPADE/qLogNEI R5 x 48 wells,
  p={.70,.50,.30,.20,.10}, c={1,1.5,2,3}, d=6, sigma_rel=.25. The active runner, however,
  defaults to **32** seeds (`software/scripts/run_tau_sweep.py:23-26`,
  `software/scripts/run_tau_sweep.py:44-49`). Each canonical file has 2,560 rows =
  64 x 2 x 5 x 4. The protocol says 64 (`publication/manuscript/PROTOCOLS.md:47-49`).
- **Difficulty definition:** for each instance/prevalence, tau is the truth quantile; margin is
  mean truth above tau minus tau; noise SD is `sigma_rel * mean(abs(truth above tau))`; and
  `margin_sd=margin/noise_sd` (`software/scripts/run_tau_sweep.py:65-83`). It is a true-surface
  explanatory diagnostic, not deployable.
- **Primary estimand/gate:** the analyser computes answer rate at c=1 by pooling **both arms** for
  each family/prevalence, then Spearman correlation across 25 cells; pass at rho>=.80
  (`software/scripts/analyse_tau_sweep.py:93-120`). Canonical result is rho=.9801. Hill C6 is
  SPADE-only at p=.70,c=1: 40/64 answered, 40 contained, lower bound .9278
  (`software/scripts/verify_conclusions.py:84-91`).
- **Runner/analyser/results:** `run_tau_sweep.py`; `analyse_tau_sweep.py`; five
  `research/results/generalization/tau-*.json`.
- **Tests/guards:** rho/cell count and Hill counts/LB are guarded
  (`software/scripts/verify_conclusions.py:69-91`), plus named-file presence. The stated runner
  correctness gate—p=.30/.10 reproducing LC—is only a comment and is not executed
  (`software/scripts/run_tau_sweep.py:3-7`).
- **Material aggregation defect:** `load()` assigns `diff[(family,p)] = margin_sd` for every row,
  overwriting prior seeds and arms (`software/scripts/analyse_tau_sweep.py:28-42`). For Hill,
  `margin_sd` is instance-dependent, so the x value is whichever Hill seed appears last, whereas
  y pools 64 seeds and two arms. The five canonical files are ordered so this is presently seed
  63, but that is an undocumented ordering dependency. C5's rho is therefore not a well-defined
  aggregate of its recorded per-seed diagnostic. Additionally, pooling arms makes C5 a statement
  about the two-method mixture rather than SPADE specifically. The analyser's partial warning is
  `<32`, so the runner default of 32 would not be flagged despite the protocol requiring 64
  (`software/scripts/analyse_tau_sweep.py:83-90`).

## 6. TT -- theta/tau mechanism adjudication

- **Question and manuscript role:** test whether pointing the rho=.95 acquisition at the actual
  p=.30 tau increases certified volume without materially worsening terminal regret. It supports
  S1, a negative mechanism result (`publication/manuscript/CLAIMS-AND-SOURCES.md:84-94`).
- **Design/status:** five families x 32 seeds x 48 wells, SPADE(theta=.8),
  SPADE-tau(theta=tau at p=.30), qLogNEI, all R5; evaluated at p=.70/.30 and c=1/1.5/2/3
  (`software/scripts/run_tt_theta_tau.py:19-23`, `software/scripts/run_tt_theta_tau.py:53-79`).
  Each family file has 768 rows = 32 x 3 x 2 x 4.
- **Mechanism and estimands:** non-targeted arms reuse LC exactly; targeted SPADE changes only the
  explicit theta (`software/scripts/run_tt_theta_tau.py:41-50`). Primary is paired certified
  volume at p=.30,c=1; the bootstrap CI must exclude zero. Guardrail is targeted-minus-committed
  regret with upper CI <= +.02 (`software/scripts/analyse_tt_theta_tau.py:85-118`). Canonical
  outcome fails both: +.000425 volume with CI crossing zero and +.0301 regret
  (`publication/manuscript/CLAIMS-AND-SOURCES.md:86-94`).
- **Runner/analyser/results:** `run_tt_theta_tau.py`; `analyse_tt_theta_tau.py`; five
  `research/results/mechanism/tt-*.json`.
- **Tests/guards:** repository audit checks named files. The conclusion guard does **not** recompute
  S1, despite the reproduction guide presenting the standalone analyser. There is no executable
  equality guard that committed SPADE rows reproduce LC, although the protocol requires exact
  reproduction (`publication/manuscript/PROTOCOLS.md:59-62`).
- **Schema/completeness concern:** TT rows omit `n_wells` and tau even though both are essential to
  interpretation; only `theta_used` remains (`software/scripts/run_tt_theta_tau.py:110-117`). As
  elsewhere, exceptions are skipped and a bare array is labeled only by its filename.

## 7. In-house iPSC-EC supporting pipeline

- **Question/status/manuscript role:** on 12 in-house tubes, ask which fibronectin/vitronectin
  coating and dose conditions can reliably exceed a CD31+ specification. This is S2/S3 support,
  **not** prospective validation. Every input row must equal `awaiting_human_signoff`
  (`software/scripts/run_real_ipsc_certification.py:1-17`,
  `software/scripts/run_real_ipsc_certification.py:40-53`); the claim ledger requires manual
  CytExpert review (`publication/manuscript/CLAIMS-AND-SOURCES.md:121-125`).
- **Dimensions/inputs/noise:** d=2: coating (FN=0, VTN=1) and log10 dose 0.5--20 ug/mL mapped to
  [0,1]. The frozen YAML calls coating continuous only because the optimizer schema lacks a
  categorical branch and requires discrete-candidate operation
  (`software/configs/lab/coating_2026-08-06.yaml:1-26`). The derived CSV has 12 rows. Outcome is
  candidate CD31 positivity and per-tube variance is squared threshold-spread in percentage
  points, averaging roughly 10.8--14.1 pp on 38.7% (`software/scripts/run_real_ipsc_certification.py:9-16`).
- **Model/certification:** the same GP is fit once; candidates are 101 log-dose positions on each
  coating (202 total). The posterior covariance is replaced by mean-marginalised covariance;
  4,000 draws seed 0 are inflated by c={1,1.5,2,3}. Thresholds are 25,28,30,32,35%, alphas
  .50/.80/.95; output is printed certified volume/top-k/best condition
  (`software/scripts/run_real_ipsc_certification.py:31-37`,
  `software/scripts/run_real_ipsc_certification.py:67-106`). There are no rounds, adaptive arms,
  holdout certificate tests, or canonical result file.
- **Calibration:** separate leave-one-observation-out fits predict each tube from the other 11,
  add that tube's measurement variance, and estimate c for raw and mean-marginalised posteriors
  (`software/scripts/calibrate_real_assay_loo.py:19-45`). S3 records meanmarg c=.712. This scores
  observation prediction, not latent-function coverage, and observations include six doses for
  each of two coatings rather than biological replicate tubes at identical conditions.
- **Guards:** lab parsers/gating/protocol have focused tests, but neither S2's 484x width nor S3's
  .712 is in `verify_conclusions.py`. Outputs exist only on stdout, so the claimed numbers are not
  backed by a canonical machine-readable result schema or provenance record. `RUN.json` records
  52 flow files, eight aborted, 34 gate candidates, ten protocol wells, and the unsigned
  promotion rule (`research/data/lab/derived/RUN.json:1-38`), but it is not the certification run.

## 8. Published Hall/Ogle supporting pipeline

- **Question/status/manuscript role:** two active uses of digitized Hall/Ogle data must be kept
  distinct. The replay asks whether BO hits a prespecified top-five condition faster than random;
  certification asks which ECM compositions exceed response thresholds. Both support plausibility
  and uncertainty claims, not a prospective SPADE wet-lab validation.
- **Data/dimensions/noise:** stage 1 is a six-factor {-1,0,+1} ECM screen with 23 usable rows;
  stage 2 is four factors with 25 rows, one lacking a usable response. Certification uses stage 1
  only, maps six coded factors to [0,1], drops flagged/missing rows, and uses published response SD
  squared (`software/scripts/certify_hall_ogle.py:31-49`). The canonical extraction explicitly
  states that values are figure digitizations and one of 48 medians is unavailable
  (`research/data/published/EXTRACTION_METHOD.md:317-352`).
- **Certification:** one six-dimensional GP, 3,000 random candidates, 4,000 draws, raw versus
  mean-marginalised covariance, thresholds {.5,.75,1,1.25} times the observed median and alphas
  .50/.80/.95 (`software/scripts/certify_hall_ogle.py:77-129`). LOO calibration is assay-specific,
  using observation predictive variance exactly as in-house; S2/S3 quote width 297x and c=.526
  (`software/scripts/certify_hall_ogle.py:52-74`,
  `publication/manuscript/CLAIMS-AND-SOURCES.md:96-111`). There are no competing arms, rounds,
  empirical truth containment, bootstrap, or binomial criterion. Output is stdout-only.
- **Replay:** stage 1 d=6 and stage 2 d=4 are separate discrete candidate pools. Both BO and
  random share an opening of 4, spend budget 8, use 40 seeds, target first hit of the observed
  top five, censor misses at 9, and use paired Wilcoxon inference
  (`software/scripts/run_replay_hall_ogle.py:61-67`,
  `software/scripts/run_replay_hall_ogle.py:80-104`). Its only retained result is
  `research/results/real-cell/replay-hall-ogle.log`; it has no structured schema and is not a
  manuscript headline claim.
- **Validation/guards:** `test_published.py` and `test_published_dataset.py` guard extraction and
  canonical tables; the extraction method declares that the independent extraction cannot be
  regenerated because its code/parameters were not supplied
  (`research/data/published/EXTRACTION_METHOD.md:282-303`). Neither the 297x width nor c=.526 is
  covered by the numeric conclusion guard.

## 9. Cross-cutting mismatches and recommended resolution

1. **Freeze seed counts in executable constants and validate per-cell completeness.** LC 25/32
   and TAU 32/64 are live default/protocol mismatches. Every analyser should validate the Cartesian
   product of families, seeds, arms, rounds, prevalences, and inflation levels rather than merely
   count globally unique seeds.
2. **Define C3's prevalence estimand.** Current code averages p=.30 and p=.10 and calibrates c over
   both. Either state this explicitly as equal-weight expected certified volume across the two
   targets or produce prevalence-specific estimates. Do not describe n=320 as independent
   campaigns.
3. **Repair TAU aggregation before treating rho=.9801 as stable.** Aggregate `margin_sd` across
   seeds by a prespecified statistic, or correlate all seed-level matched cells with an inference
   method respecting family/instance clustering. State whether answer rate is SPADE-only or the
   SPADE/qLogNEI mixture. Add an order-invariance test.
4. **Promote canonical result envelopes, not bare arrays.** Include schema version, expected and
   present keys, status, git SHA/dirty state, command/config, library versions, draw/grid seeds,
   and hashes. The stronger P2 payload pattern already implements status/completeness/provenance
   (`software/scripts/run_p2_versionb_gamma.py:220-244`), but DC/LC/LA/TAU/TT discarded it.
5. **Expand numeric guards.** Add C2 counts/LB, full C3 CI and fold choices, C4 n/CI, S1 estimates,
   LC-to-TT and LC-to-TAU reproduction checks, and real-cell S2/S3 values. Current
   `verify_conclusions.py` reports only 12 checks and omits C2 and S1--S3
   (`software/scripts/verify_conclusions.py:30-112`).
6. **Clarify statistical scope.** Flat bootstrap resampling of 160/320 cells treats family/seed
   rows as exchangeable even though four families reuse one landscape and Hill uses an ensemble.
   Claims should remain conditional on the five benchmark families unless a hierarchical or
   family-level generalization design is added.
7. **Record active constants in rows or envelopes.** TT lacks well count and tau; LA lacks rounds;
   synthetic files lack dimension/noise/draw/grid metadata. The information is inferable from
   current code but not self-authenticating if code evolves.

## 10. Audit verdict by evidence stream

| Stream | Canonical status | Publication role | Verdict |
|---|---|---|---|
| DC | five balanced JSON arrays, 32 seeds | C1/C2 | Readable; qualify in-sample c selection and DoE noise plug-in |
| LC | five balanced JSON arrays, 32 seeds | C3 and C4-SPADE | Readable only with pooled-prevalence estimand stated; runner default mismatch |
| LA | four balanced JSON arrays, 20 seeds | C4-LHS; contextual LA analysis | C4 readable; LA-specific gates weakly guarded and rounds absent from schema |
| TAU | five balanced JSON arrays, 64 seeds | C5/C6 | C6 readable; C5 aggregation is order-dependent for Hill and needs repair/qualification |
| TT | five balanced JSON arrays, 32 seeds | S1 negative mechanism result | Readable from analyser; absent numeric guard and incomplete schema |
| In-house iPSC-EC | derived CSV/RUN manifest; stdout analyses | S2/S3 support | Provisional, unsigned, non-canonical output; not prospective validation |
| Hall/Ogle | validated digitized CSVs; stdout certification; replay log | S2/S3 support | Support only; digitization and lack of structured result must remain explicit |

## Addendum -- 2026-09-02 C5 aggregation repair

**Status: original defect resolved by the current uncommitted repair, pending final quality
review.** The defect documented in section 5 remains part of the audit trail: the prior loader
overwrote `(family, prevalence)` margins row by row, making Hill's explanatory value depend on
input order, while the response pooled both arms. The repaired analyser retains one value per
`(family, seed, prevalence)`, rejects inconsistent duplicated margins, and computes a
prespecified summary rather than accepting the last row
(`software/scripts/analyse_tau_sweep.py:28-48`, `software/scripts/analyse_tau_sweep.py:51-68`).

The corrected primary C5 estimand is now explicit:

- restrict certification to the **SPADE** arm, posterior inflation `c=1.0`, and the stored
  `alpha=0.95` empty/non-empty certificate indicator;
- within each of the 25 nested `(family, prevalence)` cells, set `x` to the arithmetic mean of
  the 64 unique seed-specific `margin_sd` values and set `y` to SPADE's answer rate over the same
  64 seeds;
- report the descriptive Spearman association across those 25 cells.

That repaired calculation gives **rho = 0.9880098603391883**. The current conclusion guard pins
the value at tolerance `1e-12` and labels it as a descriptive registered gate
(`software/scripts/verify_conclusions.py:69-80`); the focused test checks the SPADE-only label,
exact registered value, and nested-cell wording
(`software/tests/test_current_conclusion_guard.py:39-50`). The analyser additionally reports a
median-margin sensitivity and a qLogNEI-only sensitivity, while explicitly suppressing a naive
correlation p value (`software/scripts/analyse_tau_sweep.py:159-175`).

The repair also adds exact Cartesian-product validation for five families, seeds 0--63, both
arms, five prevalences, and four inflation values, plus the corresponding unique margin grid
(`software/scripts/analyse_tau_sweep.py:71-87`). This removes row-order dependence and makes
missing or extra canonical cells a hard failure when invoked by the conclusion guard.

**Remaining inference caveats.** Rho remains a descriptive association over only 25 dependent,
nested cells: five prevalence thresholds are derived from each family, and four benchmark
families still reuse a single underlying landscape across seeds. Averaging seed margins before
correlation does not create 25 exchangeable population samples and does not justify a naive
Spearman p value or generalization beyond the five named families. The margin/noise quantity
also remains oracle-derived and explanatory rather than prospectively deployable. Finally, the
TAU runner's default remains 32 seeds while the repaired completeness validator requires 64;
the canonical 64-seed inputs pass, but a default fresh run would be rejected rather than
silently accepted.
