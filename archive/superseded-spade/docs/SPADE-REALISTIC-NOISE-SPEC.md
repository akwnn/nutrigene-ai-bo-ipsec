# KZ — does SPADE survive REAL cell-manufacturing noise? Pre-registration

**Frozen before any KZ result exists.**

## 1. Why this is the load-bearing test for the cell-manufacturing claim

Every result showing plate-2 targeting earns its place -- `SPADE-SELECTION-BLIND-SPEC.md`
§6.2, 49 vs 8 discordant, p = 2.7e-08 -- was measured at `sigma_rel = 0.25`.

Measured noise in real cell-manufacturing data:

| dataset | noise | SNR |
|---|---|---|
| simulated benchmarks | `sigma_rel = 0.25` | high |
| in-house iPSC-EC assay | CV 31% | 0.34 |
| **Hall & Ogle 2025 (published)** | **median CV 68%** | **0.10** |

**`sigma_rel = 0.25` is not the regime this method is being proposed for.** Targeting works
by placing wells near the threshold contour; if noise swamps the contour, there is nothing
to target and the entire two-plate architecture is unjustified for this application.

## 2. KZ-1 (PRIMARY, registered now)

At `sigma_rel = 0.68` -- Hall & Ogle's median CV -- `versionb` (targeted plate 2) beats
`versionb_random` on **non-empty certificate count**, paired by `(family, seed, p)`,
McNemar **p < 0.05**.

- **FAIL** -> plate-2 targeting does **not** survive realistic cell-manufacturing noise.
  The two-plate architecture would then be justified only in a noise regime real assays do
  not occupy, and every targeting claim in this repo must be restated as conditional on
  `sigma_rel <= 0.25`. **I consider FAIL at least as likely as PASS and am registering it
  first**, because the Hall & Ogle result showed the fitted posterior goes flat at SNR 0.10
  -- and a flat posterior has no contour to target.

## 3. KZ-2 (containment must not degrade)

At `sigma_rel = 0.68`, truth containment for `versionb` must not fall below its
`sigma_rel = 0.25` value by more than 0.10 at matched `c`. A targeting rule that keeps
answering while becoming wrong is worse than one that abstains.

## 4. KZ-3 (the honest control)

`sigma_rel = 0.25` is re-run in the same process as the internal control. If the 0.25 arm
does not reproduce the direction of §6.2's targeting advantage, the harness is wrong and
**no KZ verdict may be read at all**.

## 5. Scope

`SIGMA` is rebound on `run_p8_certificate_families.py`, the same technique
`run_ku_prevalence_matched.py` used for `TQ.FAMILIES`. Certification path otherwise
byte-identical. 4 families x 12 seeds x 2 arms x 2 sigma. Exploratory scale: a PASS
licenses a registered confirmatory run, not a claim.

**What KZ cannot establish.** It is still simulation. It tests whether the *mechanism*
survives realistic noise, not whether SPADE works in a wet lab.

## 6. KZ RESULT — the certificate is VACUOUS at real noise, and that is the finding

4 families x 12 seeds x 2 arms x 2 sigma, `alpha = 0.95`.

### 6.1 KZ-3 control PASSES, so the verdict is readable

At `sigma_rel = 0.25` the harness reproduces `SPADE-SELECTION-BLIND-SPEC.md` §6.2's
direction: targeted plate 2 beats random on non-empty certificates **16 v 1**
(p = 2.7e-04) at c=1.0 and **12 v 2** (p = 1.3e-02) at c=1.5.

### 6.2 At sigma_rel = 0.68 nothing certifies at all

| sigma | c | targeted answer rate | random answer rate |
|---|---|---|---|
| 0.25 | 1.0 | 24.0% | 8.3% |
| 0.25 | 1.5 | 15.6% | 5.2% |
| **0.68** | 1.0 | **0.0%** | **0.0%** |
| **0.68** | 1.5 | **0.0%** | **0.0%** |
| **0.68** | 2.0 | **0.0%** | **0.0%** |

**KZ-1 is not adjudicable as targeting-vs-random**, because both arms are vacuous. The
discordant counts are 0 and 0. Recorded as such rather than as a PASS or a FAIL: the gate
asked a question the data cannot answer, and the reason it cannot is itself the result.

### 6.3 The finding, and it is consistent with the real data

**At real cell-manufacturing noise, the REGION certificate on 48 wells answers 0% of the
time.** This is the simulated counterpart of `SPADE-PUBLISHED-ECM-RESULT.md` §4, where
Hall & Ogle's SNR of 0.10 supported no composition-specific claim, and §5, where resolving
a one-signal-sd effect needed ~27 replicates per composition.

Two independent routes -- a published real dataset and a controlled simulation -- now give
the same answer: **the binding constraint at realistic noise is replication, not
acquisition design.** No inflation, no acquisition rule and no calibration recovers
information that was never measured.

**Registered consequence for the targeting claim.** Every result in this repo showing
plate-2 targeting earns its place is hereby **conditional on `sigma_rel <= 0.25`**. It is
not established at CV 68%, because at CV 68% there is no certificate to earn.

### 6.4 What is tested next, registered before it runs

The region estimand must include the points it is least sure about; the finite-set
estimand (`boec.topk`) may choose. If the finite set still answers where the region is
vacuous, it is not a convenience -- it is **the only form of certification viable at real
cell-manufacturing noise**. `hill`, the biphasic dose-response family, is added because it
is the only family in the suite that resembles a real dose-response and it was absent from
KZ. Sigma is extended to 0.50 to give a trend rather than two points.

## 7. RETRACTION of §6.4 — the finite-set estimand buys nothing on real data

§6.4 registered the expectation that if the finite set answered where the region
certificate is vacuous, it would be *"the only form of certification viable at real
cell-manufacturing noise."* Measured on both real datasets
(`scripts/probe_finite_set_frontier.py`), highest threshold certifiable, `c` LOO-calibrated
per dataset:

| dataset | confidence | region floor | finite-set floor | gain |
|---|---|---|---|---|
| in-house iPSC-EC | 0.95 | 33.19% | 33.20% | **+0.01** |
| in-house iPSC-EC | 0.99 | 31.53% | 31.55% | +0.02 |
| Hall & Ogle | 0.95 | 0.74 | 0.74 | **+0.00** |
| Hall & Ogle | 0.99 | 0.71 | 0.71 | +0.00 |

**RETRACTED.** The finite set gains nothing on real data.

**Why, and the reason matters more than the result.** The finite-set estimand wins by
selecting the points the posterior is MOST confident about, which requires the posterior to
have spatial structure -- some recipes genuinely safer than others. At SNR 0.10-0.34 the
fitted posterior is effectively **constant** (`SPADE-PUBLISHED-ECM-RESULT.md` §4: posterior
mean range 0.00 across the whole design box). Every candidate is equally uncertain, so
there is nothing to select. **A method that wins by choosing cannot win when every choice
is identical.**

The 2.3x answer-rate gain recorded in `bf4845b` stands **as measured on synthetic
benchmarks at `sigma_rel = 0.25`**, where the posterior does have structure. It does not
transfer to real assay noise, and `boec.topk`'s docstring claim that it addresses the
abstention problem must be read as conditional on that regime.

**What this strengthens.** Three separate mechanisms have now been tried against the
real-noise wall -- inflation (`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10), hyperparameter
mixing (`SPADE-HYPERMIX-SPEC.md` §6) and the finite-set estimand (here) -- and none moves
it. Together with the ~27-replicate power analysis
(`SPADE-PUBLISHED-ECM-RESULT.md` §5), the conclusion is now well supported rather than
merely stated: **at realistic cell-manufacturing noise the binding constraint is
replication, and no change to the estimator, the calibration or the acquisition
substitutes for it.**

## 8. KZ-2 — the finite set works at sigma=0.25 and dies with everything else above it

5 families x 10 seeds x 3 sigma (`results/probe-kz2-finite-set-noise.json`), `alpha=0.95`,
`versionb` arm. **`hill` is EXCLUDED and its rows must not be read** -- see §8.3.

### 8.1 At sigma = 0.25, calibrated, the finite set is a real gain

| `c` | region answers | region containment | finite-set answers | finite-set containment | recipes |
|---|---|---|---|---|---|
| 1.0 | 23.8% | 0.8421 | 26.2% | 0.5714 | 25.9 |
| 1.5 | 12.5% | 1.0000 | 21.2% | 0.8824 | 10.0 |
| **2.0** | **3.8%** | **1.0000** | **11.2%** | **1.0000** | **6.6** |

At `c = 2.0` the finite set answers **2.9x** as often at **identical** containment,
returning ~7 named recipes. This independently confirms `bf4845b`'s 2.3x on fresh
campaigns with a different family set.

**The uncalibrated rows are the warning.** At `c = 1.0` the finite set is markedly *less*
accurate (0.5714 vs 0.8421) -- exactly the selection effect documented in
`boec.topk`'s docstring: it selects harder than the Vorob'ev quantile, so its in-sample
optimism is larger. **The finite set is only safe once `c` is calibrated against truth.**

### 8.2 It does not break the real-noise wall

At `sigma = 0.50` and `0.68`, **both** estimands answer **0.0%** for every family at every
`c`. Consistent with §7's retraction on real data, and with
`SPADE-PUBLISHED-ECM-RESULT.md` §4. The wall is not an artefact of the region estimand.

### 8.3 A bug in this probe, recorded rather than quietly dropped

`hill` reports 0% at every sigma **including 0.25**, and that is **my error, not a result**.
The probe computes `tau` from `tau_quantile` on instance 0's truth, but hill campaigns are
keyed by `instance_id` and each seed draws a **different** instance from the 40-member
ensemble. So `tau` was matched to the wrong landscape on 39 of 40 seeds. Every `hill` row
here is void. The other four families are keyed by family label and are unaffected.

**Consequence:** `hill` at realistic noise -- the family that matters most for cell
manufacturing -- **remains untested**, and the §6.3 conclusion is therefore established on
`ackley`, `hartmann6`, `levy` and `rosenbrock` only.
