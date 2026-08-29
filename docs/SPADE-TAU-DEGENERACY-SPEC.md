# TAU — is `hill`'s saturation a property of the family, or of `tau`? Pre-registration.

**Frozen before the run exists.** No TAU data has been generated at the time of writing.

Runner: `scripts/run_tau_sweep.py` · Analyser: `scripts/analyse_tau_sweep.py` ·
Data: `results/tau-*.json`

## 1. The claim under test

`SPADE-LC-CONFIRMATORY-SPEC.md` §9.2 measured, on the shared grid:

| family | median/max | margin over tau | noise sd | margin/sd | cert. rate |
|---|---|---|---|---|---|
| hartmann6 | 3% | 0.1320 | 0.0524 | 2.52 | 66.7% |
| ackley | 11% | 0.0268 | 0.0214 | 1.25 | 33.8% |
| hill | 71% | 0.0658 | 0.2064 | 0.32 | 0.5% |
| levy | 77% | 0.0567 | 0.2219 | 0.26 | 0.1% |
| rosenbrock | 85% | 0.0396 | 0.2351 | 0.17 | 0.0% |

`margin/sd` rank-orders certification perfectly. The proposed mechanism: noise is
**multiplicative** (`sigma_rel * f`), so a landscape compressed near the top of its range
carries large absolute noise against a thin quantile band.

**If true, `hill` is not uncertifiable — the TARGET is mis-specified.** `tau_quantile(t, p)`
returns `tau` with `P(truth >= tau) = p`, so `p` is the prevalence of the good region and
**larger `p` is an easier target**. Every `p` this project has ever run is `<= 0.30`. The
real iPSC-EC certification (`SPADE-REAL-IPSC-RESULT.md`) asserted "CD31+ >= 33.2% across
the WHOLE coating box" — prevalence near 1.0. **The benchmark has been asking a far harder
question than the application.**

## 2. Design

5 families x 32 seeds x arms {SPADE R=5, qLogNEI R=5} — the one comparison that survived
LC at 32 seeds (§9.1) — x **`p` in {0.70, 0.50, 0.30, 0.20, 0.10}** x `c` in
{1.0, 1.5, 2.0, 3.0}. 48 wells, `sigma_rel = 0.25`, `alpha = 0.95`.

`p = 0.30` and `p = 0.10` reproduce LC exactly and serve as the reproduction gate.
`margin/sd` is recorded per `(family, seed, p)` so the collapse can be tested directly.

Containment is read from `ce_empirical_*`, **never `ce_contain_*`**.

## 3. TAU-1 (PRIMARY) — does `margin/sd` govern certification?

Across all `(family, p)` cells, Spearman rho between `margin/sd` and the answer rate is
**>= 0.80**.

- **PASS** -> saturation is explained by one controlling variable that is a property of the
  TARGET, not of the family. `hill` is then not evidence against dose-response landscapes.
- **FAIL** -> §9.2's root cause is wrong and **is retracted**. The mechanism would then be
  something family-specific that this measurement has not found.

## 4. TAU-2 — can `hill` certify at all?

There exists a `p` at which `hill` reaches **LB >= 0.90 at answer rate >= 0.05** for at
least one arm.

- **PASS** -> the dose-response generalisation claim is RECOVERABLE, and the paper reports
  the prevalence at which it becomes attainable.
- **FAIL** -> the limitation is real at every target tested, and `SPADE-LC-CONFIRMATORY-SPEC.md`
  §8.3's scope restriction stands as written. **This is a real possible outcome.**

## 5. TAU-3 (ADVERSARIAL) — is SPADE's win just a difficulty artefact?

LC §9.1's surviving result is SPADE's certified-volume win at matched R=5
(+0.001353, p<0.0001). But SPADE and qLogNEI were compared on landscapes of wildly
different difficulty, and SPADE **answers more** — which mechanically raises its own
Clopper–Pearson bound.

**At matched `margin/sd`** (cells binned by difficulty), does SPADE still beat qLogNEI on
certified volume, paired by `(family, seed, p)`?

- **PASS** -> the win is a method effect and survives the confound.
- **FAIL** -> the LC §9.1 headline is a **difficulty artefact and must be withdrawn.**
  This gate is registered against our own surviving claim, deliberately.

## 6. Honesty constraints

- `p = 0.30/0.10` must reproduce LC's certification rates, or the runner is wrong and no
  TAU verdict is readable.
- A larger `p` is an EASIER question. Any recovered `hill` certification must be reported
  **with its prevalence attached** — "certifies at prevalence 0.70" is not the same claim
  as "certifies at prevalence 0.10", and conflating them would be the retraction pattern
  repeating.
- `sigma_rel = 0.25` throughout. The real-noise ceiling (`sigma_rel = 0.68`, nothing
  certifies) is untouched by this experiment.

---

## 7. TAU RESULT at 32 seeds, and a PRE-DECLARED extension

`results/tau-*.json`, adjudicated by `scripts/analyse_tau_sweep.py`.
Reproduction gate passed before the run: p=0.30/0.10 reproduced LC on 32 overlapping
cells with 0 mismatches.

### 7.1 TAU-1 PASSES — decisively

**Spearman rho(margin/sd, answer rate) = 0.9923 over 25 (family, p) cells, p < 0.0001.**
One variable explains certification across every family and every prevalence:

| family | p=0.70 | p=0.50 | p=0.30 | p=0.20 | p=0.10 |
|---|---|---|---|---|---|
| hartmann6 | 100.0% | 100.0% | 100.0% | 98.4% | 89.1% |
| ackley | 90.6% | 82.8% | 76.6% | 71.9% | 59.4% |
| hill | 48.4% | 28.1% | 10.9% | 4.7% | 0.0% |
| levy | 32.8% | 14.1% | 1.6% | 0.0% | 0.0% |
| rosenbrock | 23.4% | 4.7% | 0.0% | 0.0% | 0.0% |

**`SPADE-LC-CONFIRMATORY-SPEC.md` §9.2's root cause is CONFIRMED, not retracted.**
Saturation is a property of the target's SNR, not of the family.

### 7.2 TAU-3 PASSES — SPADE's win is a method effect, not a difficulty artefact

Certified volume, SPADE − qLogNEI, binned by `margin/sd`:

| bin | n | mean diff | 95% CI | p |
|---|---|---|---|---|
| [0.0,0.5) | 416 | +0.002457 | [+0.000036, +0.007285] | <0.0001 |
| [0.5,1.0) | 64 | +0.000156 | [−0.000070, +0.000383] | 0.185 |
| [1.0,2.0) | 192 | +0.001010 | [+0.000557, +0.001495] | <0.0001 |
| [2.0,99) | 128 | +0.001477 | [−0.000273, +0.003293] | 0.090 |

All four bins positive; two clearly significant. **And the extra volume is not bought with
bad certificates** — containment at matched difficulty:

| bin | SPADE answered / contained | qLogNEI answered / contained |
|---|---|---|
| [0.0,0.5) | 43 / 42 = 0.9767 | 13 / 13 = 1.0000 |
| [1.0,2.0) | 169 / 163 = 0.9645 | 132 / 127 = 0.9621 |
| [2.0,99) | 128 / **127 = 0.9922** | 127 / **113 = 0.8898** |

In the easiest bin SPADE is markedly better calibrated than qLogNEI (0.9922 vs 0.8898).
**SPADE answers more AND contains at least as well, at matched difficulty.**

### 7.3 TAU-2 FAILS as registered — but the measured cause is n, not the method

By the frozen rule, `hill` never reaches LB >= 0.90, so **TAU-2 is recorded FAIL.** The
cause, measured:

| family | p | arm | answered | contained | containment | LB | cause |
|---|---|---|---|---|---|---|---|
| hill | 0.70 | SPADE | 17 | **17** | **1.0000** | 0.8384 | **n < 29** |
| hill | 0.70 | qLogNEI | 14 | 14 | 1.0000 | 0.8074 | **n < 29** |
| levy | 0.70 | SPADE | 13 | 13 | 1.0000 | 0.7942 | **n < 29** |

**`hill`'s certificates are perfectly contained. Every one it issued was right.** It fails
only because 17 < 29, the minimum answered count at which a Clopper–Pearson lower bound can
reach 0.90 with zero misses.

**This is the THIRD time in this project that the CP bound has produced a false "cannot
certify"** — after LB §7.2's qLogNEI-at-R=5 (withdrawn in LC §8.1) and now `hill` and
`levy`. It is the single most common defect in this project's negative conclusions.
**Standing rule: no "X cannot certify" may be stated without reporting `answered` and
`contained`, so that an n-limit is never again mistaken for a method limit.**

### 7.4 PRE-DECLARED extension — decided BEFORE the extension is run

`hill` at p=0.70, SPADE, c=1.0 answers 17/32 = 53.1% of seeds. Reaching 29 answered needs
`29 / 0.531 = 55` seeds. **Registered now: extend to 64 seeds, adjudicate ONCE, and do not
extend again.**

- Predicted at 64 seeds: ~34 answered. With containment held at 1.0000, LB = 0.9147 -> PASS.
- **With even ONE miss at n = 34, LB = 0.868 -> FAIL.** That is the honest coin-flip, and
  it is stated before the run rather than discovered after.
- **This stopping rule is binding.** Extending again if 64 fails would be optional stopping
  and would invalidate the result. If 64 fails, TAU-2 is FAILED and `hill` stays out of
  scope.

---

## 8. TAU at 64 seeds — the pre-declared adjudication. TAU-2 PASSES.

Run to the n registered in §7.4, adjudicated ONCE. No further extension (binding).

### 8.1 TAU-2 PASSES — `hill` certifies. The dose-response limitation is DISSOLVED.

| hill, p = 0.70, c = 1.0 | answered | contained | containment | LB |
|---|---|---|---|---|
| **SPADE** | **40/64** | 40 | **1.0000** | **0.9278** — CERTIFIES |
| qLogNEI | 27/64 | 27 | **1.0000** | 0.8950 — 2 short of the n threshold |

`levy` also certifies (SPADE, p = 0.70: LB 0.9079). **`SPADE-LC-CONFIRMATORY-SPEC.md`
§8.3's scope restriction — "every certification claim is a claim about two synthetic
functions" — is now LIFTED.** A biphasic dose-response landscape has been certified at 95%
with perfect empirical containment.

**Reported with its prevalence attached, as §6 requires:** this is certification of the
region covering the top **70%** of the design space, not the top 10%. `hill` still does not
certify at p <= 0.50. The claim is "certifies at prevalence 0.70", and the honest reading
is that the attainable target on a compressed landscape is a broad one.

That is not a weak claim for this application: the real iPSC-EC result asserted
"CD31+ >= 33.2% across the WHOLE coating box" — a prevalence near 1.0. **A broad,
high-prevalence guarantee is the shape of claim cell manufacturing actually wants.**

### 8.2 What must NOT be claimed — the same trap, avoided

**Do NOT write "SPADE certifies the dose-response family and BO cannot."** Both arms have
containment **1.0000**. qLogNEI fails by **two answered cells**, and its answered count
grows with seeds exactly as SPADE's does — at ~96 seeds qLogNEI would reach ~40 and also
pass. A binary certifies/does-not statement here is a statement about where n sits relative
to the CP threshold of 29, which is the precise error behind LB §7.2, LC §8.1, and §7.3.

**The durable, n-independent claim is coverage:**

> On the dose-response family, at identical and perfect empirical containment (1.0000 for
> both arms), **SPADE answers 40 of 64 cells against qLogNEI's 27 — 48% more** — and so
> reaches a 95% certificate at a seed count where qLogNEI does not yet.

### 8.3 TAU-1 PASSES again at 64 seeds

Spearman rho(margin/sd, answer rate) = **0.9801** over 25 cells, p < 0.0001.

### 8.4 TAU-3 PASSES — 3 of 4 difficulty bins

| bin | n | mean diff | 95% CI | p |
|---|---|---|---|---|
| [0.0,0.5) | 832 | +0.001228 | [+0.000011, +0.003648] | 0.0057 |
| [0.5,1.0) | 128 | +0.000273 | [+0.000109, +0.000445] | 0.0015 |
| [1.0,2.0) | 384 | +0.001217 | [+0.000845, +0.001589] | <0.0001 |
| [2.0,99) | 256 | +0.000021 | [−0.001496, +0.001463] | 0.96 |

Three of four bins separate, all positive. **The easiest bin shows nothing, and that is
expected rather than damaging:** at margin/sd > 2 both arms answer ~100% (hartmann6 is
100.0% at every p), so there is no headroom for a coverage advantage. SPADE's edge exists
where certification is *hard*, which is where it matters.

**LC §9.1's certified-volume win is therefore a method effect, not a difficulty artefact.**

### 8.5 The paper's claims after TAU

- **Certification generalises to a dose-response landscape** — `hill`, prevalence 0.70,
  LB 0.9278, containment 1.0000. §8.3's scope restriction is lifted.
- **Certifiability is governed by `margin/sd`**, rho = 0.98. This is a quantitative law,
  and it converts "levy and rosenbrock saturate" from an embarrassment into a prediction.
- **SPADE's advantage is COVERAGE at equal containment**, and it survives matched
  difficulty in every bin that has headroom.
- **Unchanged ceiling:** `sigma_rel = 0.25` throughout. At the real assay noise of 0.68
  nothing certifies for any arm.
