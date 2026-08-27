# SPADE's certificate on published cell-manufacturing data (Hall & Ogle 2025)

**The gap this closes.** Every containment number in this project came from a synthetic
test function. `scripts/run_replay_hall_ogle.py` replays the real iPSC-EC study but
measures **optimisation only** -- it never certifies. SPADE's certificate had therefore
never been applied to real cell-manufacturing data at all. Reproduce with
`scripts/certify_hall_ogle.py`.

## 1. The data, and how hard it actually is

Stage 1: a 6-factor ECM screen (collagen I, collagen IV, laminin 111/411/511,
fibronectin) at +/-1, 23 usable runs, each with a published response SD.

| quantity | value |
|---|---|
| response | 0.509 - 1.446 (median 0.895) |
| published SD | 0.164 - 1.900, **median CV 68%** |
| signal variance | 0.072 |
| noise variance | 0.700 |
| **SNR** | **0.10** |

The measurement noise is **ten times** the signal variance. The per-composition standard
error at n=1 is 0.837 -- **3.1x the entire signal standard deviation**. This is a harsher
regime than anything the synthetic suite tests (sigma_rel = 0.25), and it is what real ECM
process development looks like.

## 2. The posterior-collapse defect reproduces on INDEPENDENT real data

| dataset | raw posterior sd | mean-marginalised | ratio |
|---|---|---|---|
| benchmark suite (4 families) | -- | -- | **1.004x - 1.011x** |
| in-house iPSC-EC assay | 0.007 | 3.388 | **484x** |
| **Hall & Ogle 2025 (published)** | **0.0003** | **0.0818** | **297x** |

`SPADE-REAL-IPSC-RESULT.md` §6 argued this defect is invisible in simulation and severe on
real data. **That now replicates on a second, independent, published dataset**, and more
severely: the raw posterior reports a standard deviation of **0.0003** on responses
spanning 0.509 to 1.446. It is not a quirk of the in-house assay.

## 3. Real assays need NO inflation — the simulated constant is wrong for them

`c` calibrated by leave-one-out **on each dataset itself**, never imported:

| dataset | LOO residual sd | coverage@68% | calibrated `c` |
|---|---|---|---|
| in-house iPSC-EC | 0.741 | 0.917 | **0.712** |
| Hall & Ogle 2025 | 0.529 | 0.957 | **0.526** |
| *(simulated benchmarks, alpha=0.95)* | -- | -- | *1.5* |

**Both real datasets give `c` well BELOW 1** -- their predictive distributions are
over-dispersed, not under-dispersed. Importing `c = 1.5` from simulation would impose
roughly **3x** the conservatism the data warrant. This is direct evidence for
`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10.3's conclusion that `c` must be calibrated
per-assay, and it shows the direction of the error: **simulation-derived inflation is too
conservative for real assays, not too loose.**

## 4. What the certificate says, and the finding that matters

| tau | alpha=0.50 | alpha=0.80 | alpha=0.95 |
|---|---|---|---|
| 0.448 (0.5x median) | 1.0000 | 1.0000 | **1.0000** |
| 0.671 (0.75x median) | 1.0000 | 1.0000 | **1.0000** |
| 0.895 (median) | 0.0000 | 0.0000 | 0.0000 |
| 1.119 (1.25x median) | 0.0000 | 0.0000 | 0.0000 |

Identical under both posteriors, and `topk` certifies **nothing** at the median at any
level.

**The finding, stated carefully.** At SNR 0.10 with 23 unreplicated runs, the fitted
posterior is effectively constant across the ECM design space: the data **cannot support
any composition-specific claim**. SPADE certifies a floor ("response >= 0.671 everywhere,
95%") and correctly refuses to distinguish compositions.

**This is a claim about what a certificate can support, NOT a claim that the published
study is wrong.** Hall & Ogle's design and conclusions are theirs and are not evaluated
here; a point estimate can rank compositions where a simultaneous guarantee cannot, and
ranking was their objective. What is measured here is only that a *guarantee* at this
noise and this replication is unavailable.

## 5. The actionable number for process development

Replicates per composition needed to resolve an effect at one-sided 95%:

| effect size | in response units | replicates needed |
|---|---|---|
| 2.0 signal-sd | 0.537 | **7** |
| 1.5 signal-sd | 0.402 | 12 |
| 1.0 signal-sd | 0.268 | **27** |
| 0.5 signal-sd | 0.134 | 106 |

**The binding constraint in real ECM optimisation is replication, not design cleverness.**
Resolving a one-signal-sd difference across this 23-point design needs ~621 runs. No
acquisition rule, SPADE's included, recovers information that was never measured -- and a
method that reports a confident answer at SNR 0.10 is reporting an artefact.

**This reframes what SPADE is for in cell manufacturing:** its value at realistic noise is
not that it finds the optimum faster, but that it states *whether the data can support a
guarantee at all*, and if not, *how much replication would be needed*. Every other method
in this repo's comparator set returns a recommendation regardless.
