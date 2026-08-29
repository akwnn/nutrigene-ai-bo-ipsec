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
