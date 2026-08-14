# MAIN LINE — the paper's skeleton

**CORE and DEFENCE only.** Everything else is in `docs/TRIAGE.md` and `docs/archive/`.
Labels and reasons: `TRIAGE.md`. Full entries with limits: `RESULTS.md`.

**Scoring rules used throughout.** **Rule A** — the true value at the running *observed*
argmax (best value measured). **Rule C** — the true value at the recipe each method's own
model recommends; reported at both the **unconstrained** argmax (Q41's primary) and the
**constrained** one (the sub-box actually explored).

---

## 1. The result

| # | Claim | Number | File |
|---|---|---|---|
| **1** | Under rule A the classical pipeline beats BO at a realistic budget | `doe − qlogei` = **−0.0595** [−0.0792, −0.0373], p<0.0001, d=6 σ=0.25, n=25 | `results/e2-grid.json` |
| **1b** | …and at d=8 | **−0.0284**; at σ=0.10 both dimensions tie | `results/e2-doe-d8.json` ✅ *(100 rows, both cells — D17 corrected)* |
| **2** | Under rule C (unconstrained, Q41's primary) BO wins every cell | **+0.2931 / +0.3597 / +0.2710 / +0.3228** | `results/q34-factorial.json` |
| **2b** | Under rule C constrained, the same comparison is **three nulls and one BO win** | **−0.0063 / +0.0153 / +0.0091 / +0.0001** | `results/q35-constrained-rsm.json` |
| **3** | The swing is the classical arm's scoring, not BO's | DoE moves **+0.3205** rule A→C; BO moves **−0.0321**. **≈10:1 at the primary cell, to 33:1** | `q34-factorial.json`, `q35-constrained-rsm.json` |
| **3b** | Mechanism: the fitted surface is a saddle, so its argmax must reach a boundary | **200/200** runs; ridge path leaves the region at radius ≈0.27 against a corner radius of 0.50 | `results/q35-constrained-rsm.json` |
| **3c** | The GP's recommendation beats its own best observation, all four cells | **0.1232 vs 0.1553 · 0.0703 vs 0.0874 · 0.1056 vs 0.1247 · 0.0876 vs 0.0972** (15–21%) | `results/q34-factorial.json` |
| **3d** | The polynomial's recommendation is worse than its own best measurement — **but only at the noisy assay** | σ=0.25: **+0.0211** [+0.0105,+0.0315] and **+0.0185** [+0.0094,+0.0287]. σ=0.10: **−0.0036** and **−0.0071**, both **NULL** | `results/d20-rescore.json` |
| **4** | It is not the model, and not only the model | Surrogate effect (design fixed) **−0.1803 to −0.0559**; design effect (model fixed) **+0.1129 to +0.2669**, all p ≤ 0.0008 | `results/q45-fourfactor-refit.json` |
| **5** | It generalises off the constructed oracle | Reversal reproduces at **all 8** Levy and Rosenbrock cells; scoring-convention effect **+0.22 to +0.48** on every saddle family | `results/q42-families.json` |
| **5b** | …but which *method* wins does not | Hartmann6: BO wins **all four cells under every rule** (+0.2460 to +0.4134). Ackley is void — its optimum is the box centre | `results/q42-families-rerun.log` |
| **6** | The curve: no defined savings ratio exists under the registered pairings | `doe` censored **64–100%** at every rule-C target; n_paired **0** at every rule-A target | `results/q52-budget-to-target.json` |
| **6b** | What survives is **arrival**, split into cost and time | σ=0.10, target 0.10: BO **24/25** vs DoE **13/25**, discordant **11:0**, p=**0.0010**. Among arrivals: BO **32 wells / 6 rounds**; DoE **48 wells / 3 rounds**. BO arrives more often, cheaper in wells, slower in rounds. spread_gp: 24/25, 32 wells, **1 round**. At σ=0.25 **no rate difference**. Reconstructed: `results/q52-rounds-to-arrival.json` | `results/q52-budget-to-target.json` |

**Why the paper needs each.** 1 and 1b are the headline. 2 and 2b are the same runs under the
other rule, and 3 is the only reason the pair is a finding rather than a contradiction — the
verdict moves because of how one arm is scored. 3b–3d supply the mechanism, 4 rules out the
obvious alternative explanation, 5 stops the result being about the oracle, 6 is the efficiency
question asked honestly and answered null.

**The governing decisions**, which the paper must state before any of the above:
**Q17** — regret is scored at the noiseless value of the point the method selected.
**Q20 §1** — the primary estimand is `qlogei` vs `doe` at d=6, σ=0.25, fixed in advance.
**Q20 §2** — Wilcoxon governs the yes/no, the instance bootstrap reports magnitude; disagreements are reported, not resolved.
**Q41** — the unconstrained argmax is the primary DoE scoring, with all three reported in every table.

---

## 2. The defence

Each row is an objection a reviewer raises, and the measurement that closes it.

### "You ran BO badly." — four mechanisms, eliminated by direct test

| Objection | Answer | File |
|---|---|---|
| The GP is misspecified for a near-additive landscape | Additive kernel doubled held-out R² (**0.375 → 0.744**) and moved regret **0.0015, p=0.71** | `results/q30-additive.log` |
| The lengthscale prior crippled it | Gamma(3,6) is significantly **worse** at ARD separation in every cell | `results/diagnostic-lengthscales.log` |
| The acquisition optimiser was failing | **4 / 3400 = 0.118%**, against a 1% threshold registered before the rate was known | `results/e2-determinism.log` |
| The opening design was too small | No detectable effect at the primary cell; the effect at σ=0.10 does not rescue BO | `results/confound-ninit.log` |

**Surrogate accuracy is not the binding constraint** — the strongest of the four, because a
measurably better model recommends no better.

### "Your comparison is rigged, or your statistics are loose."

| Objection | Answer | File |
|---|---|---|
| The DoE arm loses because you gave it a bad design | In its own region the CCD is **~4.4×** more D-efficient than the adaptive design. It fails on good geometry | `results/q43-attribution.json` |
| The effect is an artefact of which landscapes were easy | Sign-flip permutation: **0 of 10,000** as extreme, **4.6 SD**, p=0.0001 | `results/q43-attribution.json` |
| You ran 40+ comparisons and never corrected | Holm applied; it costs the "LHS also beats BO" claim (p 0.0147 → 0.2356) | `results/q39-multiplicity.json` |
| Your LHS baseline drew a lucky design | Conceded and measured — `lhs` sat at the **0th percentile of 60** draws | `results/q48-design-variance.json` |
| Then design-average BO too and the reversal vanishes | It does not. qLogEI moves **−0.002** where `lhs` moves **+0.048**; `lhs − qlogei` = **+0.0219** [+0.0145,+0.0292], p=1.8×10⁻⁵ | `results/q50-qlogei-seedsweep.json` |
| You counted evaluations; a lab pays plate cycles | DoE **3 rounds**, qLogEI **10**, at equal evaluations | `results/q38-cost-model.json` |

### "Your benchmark is made up."

| Objection | Answer | File |
|---|---|---|
| The oracle is near-separable, so it cannot speak to ECM interactions | Measured: **0.930** at d=6, **0.927** at d=8. Stated as a limitation, not discovered by a reviewer | Q22, `OPEN-QUESTIONS.md:1488` |
| The extrapolation finding is a synthetic artefact | It reproduces on the real digitized data — polynomial argmax runs to any wall (**1.0 at ±2, 4.0 at ±5**); the GP's is **bit-identical** at every extension | `results/q33-extrapolation.log` |
| The saddle finding is an artefact of your DoE arm | **800/800** preflight cells, zero maxima, before any DoE arm existed | `results/pf1-grid.log` |
| Is the oracle's mathematics right? | Hill inversion round-trips; closed-form δ_max matches brute force | PF2, `RESULTS-PERSON-A.md` §5 |
| Does your BO work at all? | Beats random search on standard functions — and exposed the scoring bias that voided E2 run 1 | `results/e1.log` |
| Is the GP's uncertainty trustworthy? | No. Coverage is below nominal **0.95 in every cell**; worst **0.7644** | `results/e3.log` |

### "Your data and your reading of the source."

| Objection | Answer | File |
|---|---|---|
| You digitized from figure panels — how much error does that inject? | Reading error is **4–7%** of between-condition spread against a published per-condition SEM of **38–66%**. The assay is the binding constraint by an order of magnitude | `docs/pdf_crosscheck.md` |
| Does any of this hold on real data? | Replay run, registered before the dataset existed: **null at both stages** | `results/replay-hall-ogle.log` |
| So BO is no faster than random | No — the instrument had no resolution. **MDE 0.68 evaluations** at 80% power; stage 1's observed effect (+0.45) is smaller than its own MDE | `results/q37-replay-power.json` |
| The scoring rule is a technicality | At σ=0.25, **61%** of remaining regret is a recipe already run and not identified. Threshold **CV ≈ 0.15** | `results/q49-noise-threshold.json` |
| You have mischaracterised the prior art | Verified against the PDFs. Nguyen 2017 is **not** a contrary result; Rummukainen 2024 is the matched-budget head-to-head and must be cited | `OPEN-QUESTIONS.md` Task A |

---

## 3. Before this is written — six things that must be fixed or stated

These come out of the triage and are not optional. Full detail in `TRIAGE.md` §"Dependency flags".

1. ✅ ~~**D17.**~~ **RESOLVED, and my flag was wrong.** `results/e2-doe-d8.json` exists — it was
   written, gitignored, and never force-added. It is now committed: 100 rows, both d=8 cells,
   18 fields, regenerating the log text exactly. **Claim 1b is fully re-scorable.**
2. 🔴 **"In every cell tested" needs its rule named in the same sentence.** Sentence 2 holds under
   the unconstrained argmax and is three nulls under the constrained one. Q41 requires both.
3. 🔴 **Sentence 3 is σ-conditional.** The polynomial-worse-than-its-data half is null at both
   σ=0.10 cells after the D20 rescore. Write it as a property of the noisy assay.
4. 🔴 **`CLAIMS.md` L19 vs `RESULTS.md`.** L19 says Q48's reversal is "ESTABLISHED (Q50)";
   `RESULTS.md:958` says the settling run is "Not run", and Q50 has no `RESULTS.md` entry at all.
5. 🔴 **The positioning section cites what verification retracted** — Picheny for a distinction
   Task A could not verify, Nguyen as contrary when it is not, Gisperg for Rummukainen's finding —
   and omits Rummukainen, the closest prior work in existence.
6. 🟠 **Three claim sources cannot be regenerated.** `E4-RESULTS-v2.md` and
   `NEGATIVE-shape-aware-mean.md` have no producing script; `METHODS.md` anchors to no artefact at all.
