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
