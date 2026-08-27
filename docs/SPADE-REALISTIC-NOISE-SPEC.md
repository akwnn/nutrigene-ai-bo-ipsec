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
