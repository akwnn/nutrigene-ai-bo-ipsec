# EXPERIMENT 4 — FIRST RESULTS ON REAL LANDSCAPES

**Person B, 2026-08-07.** First run of E4 against Person A's `biphasic-hill-v8` ensemble.
10 instances × 4 hiding levels (κ) at d=6, pre-registered settings, **78 seconds** for all 40 cells.

Reproduce: `scripts/run_e4.py`. Raw log: `results/e4-first-run.log`.

---

## The short version

**The mechanism is real and large. The headline claim did not survive.**

The traditional method over-promises enormously — by about ten times the best achievable response. The GP over-promises about twenty times less. That part is unambiguous.

But **the GP does not beat plain distance to the nearest measured point**, which is the comparison the whole experiment was built around. Pooled: **+0.051, 95% CI [−0.003, +0.100], not significant.**

On this evidence, the honest statement is that the GP is an expensive distance function.

---

## 1. Validity — the check A flagged, and it came back clean

**0 of 40 cells had the true optimum inside the training corner.** A's peak-modulation risk (Q13) did not materialise at any κ. Every cell tested what it was supposed to test.

| κ | invalid cells |
|---|---|
| 0.6 | 0/10 |
| 0.7 | 0/10 |
| 0.8 | 0/10 |
| 0.9 | 0/10 |

Worth keeping the check regardless — it costs one optimisation per cell and it is the difference between a null result and a silently meaningless one.

## 2. Headroom — the comparison could have shown something

| κ | median max-agreement | range | cells without headroom |
|---|---|---|---|
| 0.6 | 0.864 | [0.788, 0.889] | 0/10 |
| 0.7 | 0.875 | [0.761, 0.914] | 0/10 |
| 0.8 | 0.825 | [0.779, 0.941] | 0/10 |
| 0.9 | 0.828 | [0.796, 0.890] | 0/10 |

All comfortably under the pre-registered 0.95 kill threshold. **This matters: the null below is not an artefact of the three scorers being the same thing in disguise.** There was room for one to beat another, and none did decisively.

## 3. Over-prediction — the mechanism, and it is enormous

Response maximum is ~1.0, so these are multiples of the entire achievable range.

| κ | second-order | GP | escaped the corner |
|---|---|---|---|
| 0.6 | **+9.217** | +0.492 | 10/10 both |
| 0.7 | +5.551 | +0.383 | 10/10 both |
| 0.8 | +3.339 | +0.268 | 10/10 both |
| 0.9 | +2.009 | +0.245 | 10/10 both |

Pooled: **+5.12, CI [+4.22, +6.04]**, fraction extrapolated **1.00**.

Two things to note:

- **It scales monotonically with κ exactly as designed.** Hide more, over-promise more. The lever works.
- **The GP over-promises 5–20× less at every level.** That is a real difference in behaviour and it is not what the null in §4 is about.

## 4. The discrimination test — the pre-registered primary, and it is null

| κ | GP ρ | nearest-neighbour ρ | paired difference | significant |
|---|---|---|---|---|
| 0.6 | +0.494 | +0.441 | +0.0537 [−0.042, +0.148] | No |
| 0.7 | +0.383 | +0.374 | +0.0093 [−0.100, +0.105] | No |
| 0.8 | +0.466 | +0.419 | +0.0471 [−0.050, +0.148] | No |
| 0.9 | +0.584 | +0.489 | +0.0946 [−0.003, +0.190] | No |

**Pooled: +0.0512, CI [−0.0028, +0.0995].** Misses zero by 0.003.

Against the polynomial's own interval width: **+0.0035, CI [−0.061, +0.060]** — flatly nothing.

### How to read this honestly

**It is not nothing, and it is not a result.**

- All four κ point the same direction. A coin-flip effect would not do that.
- The pooled interval misses zero by 0.003 on 40 cells.
- Headroom was healthy, so the comparison was capable of resolving a difference.

The reading that survives scrutiny: **there is a small consistent effect that 10 instances cannot resolve.** Not "the GP is better" and not "the GP is no better".

### It is a power problem, and a cheap one to fix

Required instances for significance at the observed effect size:

| κ | effect | per-instance sd | n needed |
|---|---|---|---|
| 0.6 | +0.054 | 0.153 | ~31 |
| 0.7 | +0.009 | 0.165 | ~1205 |
| 0.8 | +0.047 | 0.160 | ~44 |
| 0.9 | +0.095 | 0.156 | **~10** |

**The whole 40-cell grid took 78 seconds.** Running 40 instances instead of 10 costs about five minutes.

**This must be pre-registered before running, not after seeing this table.** Deciding to scale up because the current n missed significance, and then reporting the scaled-up result as if the sample size had been chosen in advance, is exactly the practice that makes a result unpublishable. If we scale, `preregistration_version` bumps to 2 and the reason is stated in the paper: *the first run at the pre-registered n was underpowered for the paired comparison; n was raised on a power calculation performed on that run.* That sentence is defensible. Silently rerunning is not.

## 5. An unpredicted finding worth reporting

**Every single fitted surface was a saddle. 40/40.**

Not one maximum. Not one minimum. The spec explicitly anticipated a mix, and specifically warned that low κ would produce *minima* — because inside the corner you sit on the rising arm where the function is convex.

That prediction was wrong, and cleanly so. On this class of surface at this design, a second-order fit at d=6 lands on a saddle every time.

This is exactly why the spec required the stationary-point **distribution** rather than a bare escape rate. A rate would have hidden it entirely.

## 6. Other diagnostics

- **Practitioner-form fit failure rate: 0.00.** All 40 converged. 25 parameters from 48 noisy points, so this was not guaranteed.
- **Second-order interval width at its own claimed optimum: enormous** — consistent with A's Q12 measurement of 6.85 on a response of max 1.0.

---

## What this means for the open questions

### Q12 — A's argument is now much stronger

A argued the unit cube is an indefensible regime: 2–4× extrapolation in all six coordinates at once, against the published study's 1.2× in one. These numbers support that directly.

At an over-prediction of +9.2 and an interval width around 7 on a response of max 1.0, **"the traditional method's interval is too narrow" is not available as a finding.** The interval is so wide it covers almost anything. A reviewer would say the comparison was staged and they would be right.

`extended_box_bounds(x_star, kappa, rho)` is now in `designs.py` with the default reproducing today's behaviour exactly, so this is a config decision rather than a code change.

**B's position: A is right.** Recommend κ=0.6, ρ=2.0 as primary with the unit cube reported as a limiting case, per A's proposal — bundled with the n decision into a single `preregistration_version: 2`.

### Q13 — the risk A flagged did not materialise

0/40 cells had the peak inside the corner. The validity check is in and stays in regardless.

### New: the null needs a decision before anything else runs

Scaling n is cheap and justified. **It cannot be done quietly.** See §4.

---

## Bottom line

The efficiency and over-prediction story is strong and survives on its own. **The selectivity claim — that the GP flags extrapolation better than plain distance — is not supported at n=10 and may not be supported at any n.**

Doc 2 §B.3 anticipated this exactly: *"the efficiency claim is what survives independently; the uncertainty work is a supporting section requiring honest framing."* That framing is now load-bearing rather than cautionary.
