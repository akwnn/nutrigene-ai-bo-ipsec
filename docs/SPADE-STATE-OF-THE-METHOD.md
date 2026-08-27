# SPADE: what it is now, what changed, and what it lacks

**Written 2026-08-27.** Every number traces to a committed result file or a named script.
Where a claim was retracted during this work, the retraction is kept rather than the
original. Three runs were still in flight when this was written and are marked as such.

---

## 1. What SPADE is, stated precisely

SPADE is a **certification-first** design method for a fixed well budget. It spends
plate 1 on a space-filling design, spends plate 2 near the decision boundary, and returns
a **conservative excursion set**: a region of the design space with a *simultaneous*
guarantee that every point in it exceeds a threshold.

It is **not** an optimiser that beats Bayesian optimisation in general, and this document
does not claim it is. What it does that no comparator in this repo does is **refuse to
answer when the evidence does not support an answer.**

---

## 2. The four defects fixed, with evidence

### 2.1 The certificate was over-claiming (FIXED)

Truth containment at `alpha = 0.95` was **0.7938** against a nominal 0.95. Posterior
inflation at `c = 1.5` raises it to **0.9677**, one-sided 95% LB **0.9019** (n = 62,
`versionb` arm, four families pooled, `results/ktb-inflation.json`).

### 2.2 A published bound pooled SPADE with its own controls (FIXED — erratum)

`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §7 published containment **0.9699**, LB **0.9377**.
An exhaustive search over pooling schemes located those digits exactly: **n = 166 across
ALL FOUR arms**, including `plate1_only` and `versionb_random`, which are controls.
Restricted to SPADE's own arm the bound is **0.9019** (n = 62). `c* = 1.5` and the
conclusion survive -- both clear 0.90 -- but the published figure is the **more
favourable** one and must not be presented as SPADE's containment bound. (§7a erratum.)

### 2.3 The posterior collapsed to zero width on real data (FIXED)

`build_gp` point-estimates its `ConstantMean` by MLE and never propagates that estimate's
uncertainty. At low SNR the marginal likelihood is maximised by declaring the function
constant, the outputscale goes to zero, and since **all** posterior variance in that model
comes from the kernel, the width goes with it.

| dataset | raw posterior sd | after fix | ratio |
|---|---|---|---|
| benchmark suite (4 families) | -- | -- | **1.004x - 1.011x** |
| in-house iPSC-EC assay | 0.007 | 3.388 | **484x** |
| published Hall & Ogle 2025 | **0.0003** | 0.0818 | **297x** |

**Consequence, and it is a safety issue rather than an accuracy one.** On the in-house
data the uncorrected certificate asserted **95% confidence that every coating condition
meets a 35% CD31+ spec**. The posterior supports that at **74%**. A process qualified on
that certificate would be qualified on a fabricated guarantee.

Fix: integrate the constant mean out under a flat prior -- ordinary rather than simple
kriging (`boec.meanmarg`, 5 tests). Rank-one PSD, so it can only **add** uncertainty; no
free parameter; exact given the kernel.

### 2.4 A live acquisition bug (FIXED)

`run_versionb.py` had a bare `else:` that silently ran the latent straddle for **any**
unrecognised plate-2 mode string. Now raises. Verified safe: 18/18 campaigns reproduce
`regret`/`n_wells` at `|delta| = 0`.

---

## 3. The findings that are new, and matter beyond SPADE

### 3.1 A certification defect can be invisible in simulation and fatal on real data

The collapse in §2.3 adds **under 1.1%** of posterior width across the entire benchmark
suite and **100%** of it on two independent real datasets. The reason is quantitative:
the omitted term is `sigma^2 / n` relative to the kernel variance -- negligible at 48
wells with strong signal, and the entire posterior width at n = 12-23 with SNR 0.10-0.34.

**Benchmark-only validation provably cannot detect this class of failure.** This
generalises well past SPADE and is, in my judgement, the most publishable thing here.

### 3.2 Simulation-derived calibration is too CONSERVATIVE for real assays

`c` calibrated by leave-one-out **on each dataset itself** (`calibrate_real_assay_loo.py`,
`certify_hall_ogle.py`):

| dataset | LOO residual sd | coverage@68% | calibrated `c` |
|---|---|---|---|
| in-house iPSC-EC | 0.741 | 0.917 | **0.712** |
| Hall & Ogle 2025 | 0.529 | 0.957 | **0.526** |
| *simulated benchmarks (alpha=0.95)* | -- | -- | *1.5* |

**Both real datasets calibrate BELOW 1.** Importing 1.5 imposes roughly 3x the
conservatism the data warrant. This also fixes the *direction* of the transfer error,
which KT-7 could only show existed.

**Limit (§7.1 of the iPSC doc):** the LOO test scores the *observation* predictive, which
carries the measurement-noise term. At n = 12 it cannot separate "latent posterior honest,
noise overstated" from "latent posterior too wide". Either way the certificate errs
**conservative**.

### 3.3 Inflation cures under-dispersion and never cures bias

Fixed-cohort containment at `alpha = 0.5` (cells certifying at EVERY `c`, so survivorship
is removed):

| family | c=1.0 | 2.0 | 3.0 | 4.0 | behaviour |
|---|---|---|---|---|---|
| ackley | 0.3509 | 0.7544 | 0.8947 | **0.9298** | climbs |
| hartmann6 | 0.1970 | 0.5758 | 0.8182 | **0.8788** | climbs |
| levy | 0.3333 | 0.7500 | 0.7500 | **0.7500** | **saturates** |
| rosenbrock | 0.6364 | 0.7273 | 0.7273 | **0.7273** | **saturates** |

Inflation scales the posterior SD and leaves the mean untouched, while the Vorob'ev
quantile shrinks the certified region toward its **highest-probability** points. A point
the model is *confidently wrong* about is therefore retained at every `c` **by
construction**. `map_total_error_vol_sub`, a pure mean statistic, is flat in `c` to four
decimals, confirming inflation never moves the mean.

### 3.4 At real cell-manufacturing noise the region certificate is VACUOUS

`sigma_rel = 0.68` is Hall & Ogle's median CV.

| sigma | targeted answer rate | random answer rate |
|---|---|---|
| 0.25 | 24.0% | 8.3% |
| **0.68** | **0.0%** | **0.0%** |

The control passes (at 0.25, targeting beats random **16 v 1**, p = 2.7e-04), so this is
not a broken harness. Two independent routes -- a published dataset at SNR 0.10 and a
controlled simulation at CV 68% -- agree: **the binding constraint at realistic noise is
REPLICATION, not acquisition design.**

Hall & Ogle power analysis: resolving a one-signal-sd effect needs **~27 replicates per
composition, ~621 runs**.

### 3.5 SPADE beats BO on the biological landscape and loses on artificial ones

Paired final regret vs `qlognei`, negative = SPADE better, SESOI = 0.02:

| family | sigma | mean diff | 95% CI | p |
|---|---|---|---|---|
| **hill** | 0.10 | +0.0180 | [+0.0088, +0.0280] | 5.2e-04 |
| **hill** | **0.25** | **-0.0312** | **[-0.0456, -0.0168]** | **8.9e-05** |
| rosenbrock | 0.25 | -0.0131 | [-0.0213, -0.0050] | 4.0e-03 |
| levy | 0.25 | +0.0234 | [+0.0076, +0.0380] | 7.8e-04 |
| ackley | 0.25 | +0.1016 | [+0.0682, +0.1343] | 3.6e-07 |
| hartmann6 | 0.25 | +0.1624 | [+0.1297, +0.1953] | 2.1e-16 |

`hill` is the biphasic dose-response family -- the only one in this suite that resembles a
real media/ECM response. **SPADE beats qLogNEI there at `sigma = 0.25`, and the two hill
CIs do not overlap**, so the advantage genuinely grows with noise. The losses are all
generic multimodal functions with sharp global optima, which is what BO is built for.

Per registered condition: **C1 (hill) SPADE better; C2 (hill, the preregistered TARGET)
parity within SESOI; C3/C4 (hartmann6) and S1 (ackley) worse; S2 (levy) and S3
(rosenbrock) parity.** Four of seven at parity or better.

---

## 4. What SPADE now offers a cell-manufacturing lab

On the real in-house iPSC-EC coating data (12 tubes, 6 factors reduced to coating x dose):

> **CD31+ >= 31.6% across the entire FN/VTN x 0.5-20 ug/mL box, at 95% confidence**
> (`c = 1.0`, which the LOO calibration of §3.2 justifies for this assay).

Plus the number a lab can act on -- replicates needed at the measured 12.1 pp gate noise:

| spec | tubes @95% | tubes @80% |
|---|---|---|
| 25% | 3 | 1 |
| **30%** | **8** | 3 |
| 35% | 86 | 23 |

**The binding constraint is gate noise, not well count.** The highest-leverage next
experiment is tightening the CD31 gate or adding replicates, not adding conditions.

---

## 5. What SPADE LACKS — the honest list

1. **It is not a better optimiser in general.** Parity at the preregistered target
   condition; clearly worse than qLogNEI on hartmann6 (+0.162) and ackley (+0.102).
2. **Cross-landscape calibration transfer FAILS.** KT-7a: no `c` clears the risk ceiling
   at `alpha = 0.50` on any family up to c = 4.0. The calibration claim is scoped to
   `alpha = 0.95`.
3. **levy/rosenbrock saturation is unexplained and uncured.** Three mechanisms excluded:
   shape (refuted), SNR (retracted), and hyperparameter misspecification (KY, in flight).
4. **Every targeting claim is conditional on `sigma_rel <= 0.25`.** At CV 68% there is no
   certificate to earn. This includes the 49 v 8 / p = 2.7e-08 headline.
5. **No wet-lab validation.** The in-house data is `awaiting_human_signoff`: 12 CD31 gates
   need signing in CytExpert. That is an afternoon, not an experiment, and it is the only
   step between this and a citable result.
6. **The abstention rate is still high.** The finite-set estimand (`boec.topk`) gives
   2.3x the answer rate at identical containment (10.9% vs 4.7% at c = 2.0), but on 64
   cells, and it is predicted (§3.3) to hit the same saturation ceiling because it also
   selects highest-probability points.
7. **No comparator has been run on real data.** No superiority claim over BO or RSM on any
   real dataset is made or supported.
8. **Multi-CQA qualification is unverified.** A multi-endpoint layer was reported but does
   not exist in this repository -- no code, branch or worktree. If built, it needs a
   multiplicity correction (k marginal `alpha` certificates intersect at `1 - k(1-alpha)`,
   not `alpha`) and must use `boec.meanmarg` per endpoint or inherit §2.3 on every one.

---

## 6. In flight when this was written

| run | question | status |
|---|---|---|
| KX | SPADE vs qLogNEI/Sobol on certified region recovery, all arms calibrated out-of-sample | ~16/30 per family |
| KY | can hyperparameter mixing break the saturation of §3.3 | running at 30 seeds; **not adjudicable at 6 seeds** (cohorts of 0-9) |
| KZ-2 | does the finite-set estimand still answer where the region certificate is vacuous | running, `hill` included |

**Test suite: 1724 passing.**

---

## 7. The defensible claim, in one paragraph

*Conservative excursion-set certification is self-validating under acquisition-driven
design: the certificate's internal confidence statistic sits at 1.000 while true
simultaneous containment falls to 0.794. The failure is not selection-induced variance
shrinkage -- a selection-blind posterior makes it worse -- but a combination of
under-dispersion, curable by a single dimensionless inflation constant, and a structural
omission of mean uncertainty that is invisible in simulation (1.01x) and fatal on real
biological data (297-484x). On the one benchmark family resembling a real dose-response,
the resulting method matches or beats Bayesian optimisation, with an advantage that grows
with noise; at realistic assay noise it correctly reports that no region-level guarantee is
available on the budget, and quantifies the replication that would be needed.*
