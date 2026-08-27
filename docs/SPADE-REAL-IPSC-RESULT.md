# SPADE on the real iPSC-EC coating data

**PROVISIONAL.** `data/lab/derived/candidate_campaign_coating_flow.csv` carries
`status = awaiting_human_signoff`. `data/lab/overlay/GATE.md` is explicit that
`bo_primary_conditions.csv`'s `y` stays empty until a person signs the CD31 gate in
CytExpert. **Nothing here is a wet-lab result.** Reproduce with
`scripts/run_real_ipsc_certification.py`.

## 1. The data

12 coating conditions: fibronectin and vitronectin at 0.5, 1, 2.5, 5, 10, 20 ug/mL,
n = 1 each, CD31+ by flow on a CytoFLEX LX.

| quantity | value |
|---|---|
| CD31+ across the 12 tubes | 22.6% - 47.3%, mean 38.7% |
| per-tube noise (`y_spread_pp`, gate-threshold sensitivity) | **12.1 pp** |
| signal variance / noise variance | **0.34** |

The noise is **measured**, not assumed: it is the spread of the positivity call between
the p95 and p99.9 gate thresholds on the instrument files themselves.

## 2. A defect this data exposed, which simulation never did

`build_gp` point-estimates its `ConstantMean` by MLE and never propagates that estimate's
uncertainty. At SNR 0.34 the marginal likelihood is maximised by declaring the function
constant; the outputscale goes to zero; and because **all** posterior variance in that
model comes from the kernel, the posterior width goes with it.

    posterior mean:  37.16 .. 37.16   (range 0.00 across the whole design box)
    posterior sd  :  0.01

The honest width is the standard error of a constant, `12.1 / sqrt(12) = 3.5`. The model
understated it **350-fold**. Posterior inflation cannot repair this: `c = 3` turns 0.01
into 0.03.

**Consequence, and it is a safety issue rather than an accuracy one.** The uncorrected
certificate asserted **95% confidence that every coating condition meets a 35% CD31+
spec**. The posterior actually supports that at **74%**. A process qualified on that
certificate would be qualified on a fabricated guarantee.

**Fix** (`boec.meanmarg`, 5 tests): integrate the constant mean out under a flat prior --
ordinary rather than simple kriging. Rank-one PSD, so it can only ADD uncertainty; no free
parameter; exact given the kernel. Restores `0.007 -> 3.388`, and the certificate then
correctly abstains at alpha = 0.8 and 0.95.

## 3. What SPADE certifies, after the fix

Highest CD31+ spec certifiable over the **entire** FN/VTN x 0.5-20 ug/mL box:

| inflation `c` | alpha=0.50 | alpha=0.80 | **alpha=0.95** | alpha=0.99 |
|---|---|---|---|---|
| 1.0 (none) | 37.1% | 34.3% | **31.6%** | 29.2% |
| 1.5 | 37.0% | 32.8% | **28.8%** | 25.2% |
| 2.0 | 37.0% | 31.4% | 26.0% | 21.3% |
| 3.0 | 36.9% | 28.5% | 20.4% | 13.3% |

**The claim:** *across both coatings and the full dose range, CD31+ >= 28.8% with 95%
confidence* (at `c = 1.5`; 31.6% uncorrected).

The shape is the method behaving correctly: at alpha=0.50 the frontier barely moves with
inflation (37.1 -> 36.9), because a median claim is robust; at alpha=0.99 it collapses
(29.2 -> 13.3), because a strong guarantee is what conservatism has to pay for.

## 4. What this does NOT establish

1. **`c` is not calibrated for this assay.** 1.5 was selected on simulated benchmark
   families at alpha=0.95, and `SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10 shows it does not
   transfer across conditions. Treat the `c=2.0` row (26.0%) as the conservative read until
   replicates permit a real calibration.
2. **It is a statement about the design box, not about an optimum.** It says every
   condition tested clears the spec -- robustness, not optimisation.
3. **n = 1 per condition.** No replicate structure, so no within-condition variance
   estimate independent of the gate-threshold proxy.
4. **No comparator was run on this data.** No claim of superiority over any method is made
   or implied here.

## 5. The actionable number

At the current gate noise (12.1 pp), tubes required to certify a spec over the box:

| spec | tubes at 95% | tubes at 80% |
|---|---|---|
| 25% | 3 | 1 |
| **30%** | **8** | 3 |
| 32.5% | 19 | 5 |
| 35% | 86 | 23 |

**The binding constraint is gate noise, not well count.** The highest-leverage next
experiment is tightening the CD31 gate or adding replicates -- not adding coating
conditions.

## 6. The defect is invisible in simulation — measured in both directions

The obvious objection to §2 is that a defect this large should have shown up in the
benchmark suite. It does not, and the reason is quantitative.

Posterior width ADDED by mean-marginalisation, `versionb` arm, 24 campaigns
(4 families x 6 seeds, exploratory):

| data | mean posterior sd, raw | mean-marginalised | ratio |
|---|---|---|---|
| ackley | 0.0167 | 0.0168 | **1.008x** |
| hartmann6 | 0.0390 | 0.0392 | **1.004x** |
| levy | 0.1321 | 0.1333 | 1.009x |
| rosenbrock | 0.1270 | 0.1284 | 1.011x |
| **real iPSC-EC** | **0.007** | **3.388** | **484x** |

Certificate behaviour on the benchmarks is correspondingly unchanged (alpha=0.95:
answer rate 22.9% -> 20.8%, containment 0.8182 -> 0.8000, n=11 and 10 — within noise at
this sample size).

**Interpretation.** The correction contributes `sigma^2 / n` relative to the kernel's
own variance. Every simulated family runs at 48 wells with enough signal that the constant
mean is well determined, so the omitted term is negligible. The real assay runs at n=12
with SNR 0.34, where MLE drives the outputscale to zero and the omitted term becomes
**the entire posterior width**.

**Consequence for method validation, stated as the finding:** *a structural defect in
GP-based certification can add under 1% of posterior width across an entire benchmark
suite while accounting for 100% of it on real data. Benchmark-only validation cannot
detect this class of failure.*

**Why the committed benchmark results are NOT retroactively re-scored.** The change is
within noise there (<= 1.1% width), and re-scoring would break provenance against every
committed run for no measurable gain. `boec.meanmarg` is therefore used by the real-data
path and is available, not defaulted. **Recommendation on record: it should be ON for any
low-SNR or small-n assay**, which is every real one this project has seen.

## 7. Calibrating `c` on THIS assay, with no new experiments

The open item was: `c = 1.5` came from simulated benchmarks, and
`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10 proved it does not transfer. Calibrating it
here does **not** require replicates. Each of the 12 tubes is held out, predicted from the
other 11, and its standardised residual computed; if the posterior is honest those
residuals are N(0,1), and the inflation that makes them so is `c` for this assay.
Reproduce with `scripts/calibrate_real_assay_loo.py`.

| posterior | LOO residual sd | coverage @68% | coverage @95% | calibrated `c` |
|---|---|---|---|---|
| raw | 0.741 | 0.917 | 1.000 | **0.712** |
| mean-marginalised | 0.697 | 0.917 | 1.000 | **0.671** |

**`c < 1`: the predictive distribution is OVER-dispersed, not under-dispersed.** Eleven of
twelve tubes fall inside a nominal-68% interval. Importing `c = 1.5` was unwarranted
conservatism, and the honest headline for this assay is the **`c = 1.0` row of §3:
CD31+ >= 31.6% at 95% confidence**, not 28.8%.

### 7.1 What this does NOT show, and it is a real limit

The LOO test scores the **observation** predictive, which carries the 12.1 pp noise term.
The certificate is a claim about the **latent** `f`. At n = 12 these cannot be separated:
an over-dispersed predictive is equally consistent with

1. the latent posterior being honest and `y_spread_pp` **overstating** the noise, or
2. the latent posterior being over-wide.

Backing the ratio out of (1) gives a true measurement noise near **8.8 pp** against the
12.1 pp proxy -- entirely plausible, since gate-threshold sensitivity is a conservative
stand-in for tube-to-tube reproducibility, not a measurement of it.

**What survives either way:** the certificate on this assay errs **conservative**, which is
the safe direction for a manufacturing claim, and `c = 1.5` is not justified here.
**What is still owed:** replicate tubes, which would measure the noise directly and
separate the two explanations. That is the experiment worth running, and it is the same
experiment §5's power table already recommends.
