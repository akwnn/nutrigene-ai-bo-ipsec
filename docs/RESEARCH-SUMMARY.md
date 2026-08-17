# Matched-budget benchmarking of Bayesian optimization and response-surface methodology depends on the terminal decision rule

**Running title.** Terminal decision rules reverse BO-versus-RSM rankings on a synthetic recipe benchmark.

**Keywords.** Bayesian optimization; response-surface methodology; terminal decision rule; matched budget; Gaussian process; simple regret; sequential design; experimental rounds.

**Data.** Numerical claims are taken from the committed JSON listed under Data availability. Internal identifiers (E2, Q34, …) are reproducibility tags; the map is in `docs/SUPPLEMENT.md`. Primary cell locked before the E2 grid: commit `d289e7d`. Sequential RSM with `path_argmax`: commit `fd842ac`. Environment pinned in artefact provenance (Python 3.11, BoTorch 0.18.1).

---

## Abstract

**Background.** Rankings between Bayesian optimization (BO) and response-surface methodology (RSM) reverse under different terminal decision rules on identical campaigns. That protocol dependence can reconcile published disagreements without contradictory algorithms. Narayanan et al. (2025) report ~2.5–3× fewer experiments than the **predicted** count for standard DoE (~10–30× in a nine-factor transfer case): a resource-planning denominator, not an executed equal-budget DoE arm. Rummukainen et al. (2024) ran both methods at 15 experiments, scored the best measured condition, used noisy expected improvement then a posterior-mean final pick, and found no reduction in experiment count. Lapierre et al. (2025) and Ndahiro et al. (2025) add executed media/bioprocess comparisons of complete workflows. Both the “BO saves experiments” and the “no saving at matched budget” findings can be correct if their denominators and terminal decisions differ.

**Methods.** A synthetic Hill benchmark, **structurally inspired by** the six-factor / 6→4 screen of Hall, Lin and Ogle (2025), not fitted to endothelial data. The optimizer observes y = f(x) + ε. Simple regret is 1 − f(x∗). On identical 48-well campaigns we vary the terminal decision: hidden tested-best, measured-value argmax, naïve unconstrained quadratic or GP recommendation, in-region / ridge recommendation, and replicate / top-3 confirmation / posterior-mean-at-visited picks. Cost is counted in wells and in plate rounds. Named BO is qLogEI with batch size q = 4 (10 rounds); **qLogNEI is co-primary**. Sequential RSM with steepest-ascent relocation is the long-run classical arm (`doe_ascent`). A fully sequential q = 1 arm is registered (Q61) and not yet run.

**Results.** On the same campaigns, rankings reversed. At σ = 0.25, measured-value argmax favoured sequential DoE by 0.0595 [−0.0797, −0.0375] (d = 6) and 0.0284 [−0.0447, −0.0139] (d = 8); against qLogNEI the primary-cell contrast is −0.0574 [−0.0776, −0.0376]. About 55–73% of that lead is identification, not search. Confirming the top three wells using the confirmation reading alone reduces the primary contrast to −0.0009 [−0.0263, +0.0253] (TOST inconclusive; SESOI = 0.02; Wilcoxon MDE = 0.042). Averaging original and confirmation is not run (Q60). Naïve unconstrained recommendation favoured BO by 0.27–0.36, and in-region / ridge recommendation at the primary cell is −0.0063 [−0.0233, +0.0107] (TOST inconclusive; MDE = 0.027). Under measured-value argmax, sequential RSM matches qLogEI on arrival to N = 200. A one-shot GP, at five Latin-hypercube draws, reached regret 0.10 on 24.4/25 Hill landscapes versus 16/25 for 10-round qLogEI (σ = 0.25, model recommendation, one round). On Hartmann6, removing the 6→4 screen makes DoE worse, not better.

**Conclusions.** A matched evaluation count does not define a unique BO-versus-RSM comparison. Rankings changed when the terminal decision changed. Most of the unconstrained reversal arose from extrapolative optimization of saddle-shaped quadratic fits. Well count and plate-round count are different costs; under measured-value argmax there is no well-count saving versus walking RSM. Comparisons should prespecify the terminal decision, noise handling, permitted extrapolation, confirmation protocol, batch schedule, and unit of experimental cost. The study is not a wet-lab validation.

---

## 1. Introduction

Optimization of culture media and extracellular-matrix (ECM) coatings is an expensive black-box problem. Each experimental condition consumes a well; each plate cycle—selection, incubation, readout, then reselection—consumes a **round**. Full-factorial grids are infeasible: five levels in six factors require 5⁶ = 15,625 evaluations. Practitioners therefore use sequential or planned designs that nominate a small set of conditions and, after the budget is spent, a single formulation to carry forward.

**Classical DoE and RSM** (Box and Wilson, 1951; Myers et al.) treat the unknown response as locally quadratic. A screening design identifies a subset of active factors. A **central composite design** (CCD) is then executed in that subregion and a second-order polynomial is fitted. Canonical analysis classifies the stationary point. Classical RSM then uses **steepest ascent**, **ridge analysis**, and often a relocated CCD — not unconstrained maximization of a saddle over the whole box.

**Bayesian optimization** (Močkus, 1975; Jones, Schonlau and Welch, 1998; Frazier, 2018) places a Gaussian-process prior on the latent response and picks the next batch with an acquisition function. We report **qLogEI** and **qLogNEI** as co-primary under observation noise. Stored BO uses batch size q = 4 after an n₀ = 2d+2 Sobol opening (commit `d289e7d` locked the primary comparison). A q = 1 sensitivity at the primary cell is registered as Q61. The distinction between using the best noisy observation and using a posterior-mean incumbent is already standard in noisy BO; this paper asks whether that distinction is large enough to reverse a BO-versus-RSM ranking, and whether a short confirmation protocol is.

That RSM maps a design region while BO concentrates accuracy near promising conditions is **background**, not a finding (Rummukainen et al., 2024). Executed comparisons already exist: Rummukainen (15-run Box–Behnken versus 5+10 BO, noisy EI then posterior-mean pick, no reduction in experiment count); **Lapierre et al. (2025)** (CCD/RSM after factor reduction versus batch BO that kept all factors, *S. pasteurii*); **Ndahiro et al. (2025)** (CHO media, same experiment count, higher titers under BO). **Narayanan et al. (2025)** report ~2.5–3× fewer experiments than the **predicted** standard-DoE count. That is a different scientific experiment from giving each method 48 evaluations on the same landscape.

**Hypothesis.** Apparently conflicting BO-versus-DoE conclusions can arise without contradictory algorithmic behaviour when studies bundle different terminal decisions, surrogate readouts, screening cuts, batch schedules, and budget definitions. We hold those pieces under experimental control.

Figure 1 is winner reversal by terminal rule. Figure 2 is cost in wells and in rounds, with hit probability P(T ≤ N) first. Figure 3 is the saddle / ridge mechanism. Protocol sensitivities (Q54–Q59) ask whether those findings survive noisy EI, a walking RSM arm, a confirmation pick, multi-draw one-shot GP, and Hartmann without a forced 6→4 screen.

The latent function is constructed. Factor count and the 6→4 screen are **structurally inspired by** Hall, Lin and Ogle (2025). No wet-lab BO campaign is reported.

---

## 2. Definitions and decision rules

This paper is a computer experiment. A hidden function stands in for recipe quality. The optimizer sees y = f(x) + ε. After a fixed number of recipes we score **simple regret** R = 1 − f(x∗) at the nominated point. Table-reading conventions and internal experiment IDs: `docs/SUPPLEMENT.md` §S1–S2.

**Inferential hierarchy.** Confirmatory, unadjusted: sequential DoE versus named BO at d = 6, σ = 0.25, N = 48, under measured-value argmax and under in-region recommendation. The other three cells are exploratory. Holm–Bonferroni is used for multi-arm families (control arms vs qLogEI) and multi-target arrival families, not for the primary-cell confirmatory contrasts. Equivalence is TOST at SESOI = 0.02 on the 25 paired landscape differences (both one-sided t-tests must reject). Verdicts: equivalent, different, or inconclusive. Wilcoxon MDE at 80% power is reported beside inconclusive cells. Source: `results/tost-contrasts.json`.

### 2.1 Terminal decisions

1. **Hidden tested-best (search quality).** Among wells actually run, max noiseless f. A lab cannot compute this. Primary cell: DoE 0.0597, qLogEI 0.0755, qLogNEI 0.0834 (Q55/Q57).
2. **Measured-value argmax (single-readout selection).** Pick argmax of noisy y, score noiseless f. One operational rule, not every laboratory carry-forward. Primary cell: DoE 0.0958, qLogEI 0.1553, qLogNEI 0.1532.
3. **Naïve unconstrained model recommendation.** Argmax of the fitted quadratic or GP over the whole box. For a saddle-shaped quadratic this is a diagnostic failure mode, not classical RSM.
4. **In-region / ridge recommendation.** The principal classical readout: argmax inside the explored region.
5. **Confirmation / replicate / posterior-mean pick.** Same campaigns, different final pick (Q58). Confirming the top three wells by the confirmation reading alone yields −0.0009 [−0.0263, +0.0253] (TOST inconclusive; MDE = 0.042). Averaging original and confirmation is Q60 (not run; BO replay failed the 1e-12 gate).
6. **Cost.** Wells and plate rounds until a target. Lead with P(T ≤ N). Sequential RSM with relocation (`doe_ascent`, `path_argmax`, commit `fd842ac`) is the fair long-run classical arm; `doe_repeat` does not relocate.

DoE and BO can win different questions on the same 48 wells. That is the point of the paper, not a contradiction.

### 2.2 Experimental cells

A **cell** is one setting: d ∈ {6, 8} × σ ∈ {0.25, 0.10}. Six factors match the Hall/Ogle ECM proteins; eight adds two inert coordinates. σ = 0.25 and 0.10 are higher-noise and lower-noise **benchmark** conditions, not an estimated assay CV. The **primary cell** is d = 6, σ = 0.25 (commit `d289e7d`). Each cell: 25 landscapes × 2 seeds; tests use the 25 paired landscape differences.

---

## 3. Methods

The latent response is a biphasic Hill function with known optimum 1. Parameters are drawn from pre-specified ranges; they are not fitted to Hall/Ogle measurements. Algorithms observe y = f(x) + ε; reported regret uses only f(x∗). Digitized Hall/Ogle medians were used in auxiliary analyses only (replay underpowered; MDE 0.68).

Unless otherwise stated the budget is N = 48 (20-run screen + 27-run face-centred CCD + 1 confirmation). Stored BO: n₀ = 2d+2, then batches of q = 4 (**10 rounds**). DoE at this budget is 3 rounds; a 48-point Latin hypercube is 1 round. Q61 (not yet run) repeats the primary cell at q = 1 (**35 rounds**).

**GP calibration.** Latent posterior coverage is below the nominal 95% in every cell (worst 0.764; E3). Predictive coverage after adding observation noise is approximately 0.90–0.92. The **posterior-mean-at-visited** pick (Q58) and the **in-region GP** recommendation are therefore conditional on a miscalibrated surrogate. Measured-value argmax and hidden tested-best do not use the posterior.

| Procedure | N = 48 | Rounds at 48 | Role |
|---|---|---|---|
| qLogEI, q = 4 | 48 | 10 | Named stored BO |
| qLogNEI, q = 4 | 48 | 10 | Co-primary under noise |
| DoE | 48 | 3 | Published pipeline; no relocation at this budget |
| doe_ascent (Q56) | up to 200 | variable | Sequential RSM (`path_argmax`) |
| spread_gp | n, one shot | 1 | Isolates the GP from sequential adaptation; Hill uses five LHS draws (Q54) |
| random | 48 | 1 | Trivial measured-argmax baseline |

The 48-well DoE arm has no steepest-ascent stage because there is nothing to relocate inside that budget. Long-run comparisons use `doe_ascent`. `doe_repeat` remains a control (supplement §S8). Locator-history (D20) is in the supplement changelog.

---

## 4. Results

Lower regret is better. Control-arm tables, the design × surrogate grid, Q42 family tables, and Q-ids are in `docs/SUPPLEMENT.md`.

- **Figure 1** (`results/figures/fig1-scoring.html`): same 48 wells, four terminal decisions.
- **Figure 2** (`results/figures/cost-curves.html`): wells and rounds to 200; `doe_ascent` is the classical arm; P(T ≤ N) first.
- **Figure 3** (`results/figures/fig3-saddle.html`): why the quadratic is a saddle and why ridge constraints matter.

### 4.1 Matched budget N = 48 (Figure 1)

The campaigns do not change. Only the terminal decision changes. That reversal is the core result. Contrasts are DoE − BO unless noted. Intervals are 95% instance bootstraps (n = 25). The primary row is confirmatory; the other three cells are exploratory (not Holm-adjusted as a four-cell family).

**Measured-value argmax.** Pick argmax of noisy y, score noiseless f.

| Cell | DoE | qLogEI | qLogNEI | random | DoE − qLogEI | DoE − qLogNEI |
|---|---|---|---|---|---|---|
| d=6, σ=0.25 (primary) | **0.0958** | 0.1553 | 0.1532 | 0.2216 | **−0.0595** [−0.0797, −0.0375] | **−0.0574** [−0.0776, −0.0376] |
| d=6, σ=0.10 | 0.0892 | 0.0874 | 0.0808 | 0.1693 | +0.0018 [−0.0086, +0.0117] | +0.0084 [−0.0059, +0.0214] |
| d=8, σ=0.25 | 0.0963 | 0.1247 | 0.1105 | 0.1712 | **−0.0284** [−0.0447, −0.0139] | **−0.0142** [−0.0251, −0.0036] |
| d=8, σ=0.10 | 0.0948 | 0.0972 | 0.0849 | 0.1272 | −0.0024 [−0.0095, +0.0053] | +0.0100 [−0.0010, +0.0207] |

Random minus qLogEI at the primary cell: +0.0664 [+0.0418, +0.0914]. Search beats a trivial baseline; the DoE–BO ranking still flips with the terminal rule. At higher noise the single noisy readout favours DoE over both acquisitions. At lower noise DoE and qLogEI are **equivalent** at SESOI = 0.02 (d = 6: +0.0018 [−0.0086, +0.0117]; d = 8: −0.0024 [−0.0095, +0.0053]). A q = 1 BO arm is not in this table (Q61; not run).

**Hidden tested-best (Q55, Q57).** R_search = 1 − max_i f(x_i).

| Cell | qLogEI R_search | qLogNEI R_search | DoE R_search | DoE − qLogEI (search) | Share of measured lead that is identification |
|---|---|---|---|---|---|
| d=6, σ=0.25 | 0.0755 | 0.0834 | 0.0597 | **−0.0158** [−0.0257, −0.0062] | **73%** |
| d=6, σ=0.10 | 0.0496 | 0.0435 | 0.0544 | +0.0048 [−0.0030, +0.0131] | — |
| d=8, σ=0.25 | 0.0702 | 0.0685 | 0.0575 | −0.0127 [−0.0251, −0.0008] | ~55% |
| d=8, σ=0.10 | 0.0653 | 0.0564 | 0.0500 | −0.0153 [−0.0254, −0.0059] | acquisition-dependent |

At the primary cell qLogEI identifies its own best well 8% of the time (gap +0.0797); qLogNEI 22% (+0.0698); DoE 12% (+0.0361). **Most of the published 0.0595 is identification among clustered BO samples, not better search.** Against qLogNEI the measured-argmax lead is −0.0574 [−0.0776, −0.0376] and the search lead is larger (−0.0237 [−0.0379, −0.0111]). Quiet-assay tested-best verdicts are acquisition-dependent: “DoE tested better at d = 8, σ = 0.10, and the readout hid it” is **withdrawn** against qLogNEI (p = 0.56).

**Naïve unconstrained recommendation** is a diagnostic, not classical RSM. Quadratic minus GP: +0.2931 [+0.2662, +0.3204] / +0.3598 [+0.3427, +0.3770] / +0.2710 [+0.2433, +0.2994] / +0.3228 [+0.3042, +0.3427]. Almost all of the swing is a saddle (Figure 3).

**In-region / ridge** is the principal classical readout. Quadratic minus GP:

| Cell | DoE in-region | GP | DoE − GP |
|---|---|---|---|
| d=6, σ=0.25 (primary) | 0.1169 | 0.1232 | −0.0063 [−0.0233, +0.0107] |
| d=6, σ=0.10 | 0.0856 | 0.0703 | +0.0153 [+0.0042, +0.0269] |
| d=8, σ=0.25 | 0.1148 | 0.1056 | +0.0091 [−0.0057, +0.0243] |
| d=8, σ=0.10 | 0.0877 | 0.0876 | +0.0001 [−0.0118, +0.0115] |

At the primary cell TOST is **inconclusive** (MDE = 0.027). At d = 6, σ = 0.10 the GP is ahead and the interval excludes 0 (exploratory; TOST different). At d = 8, σ = 0.10 the in-region contrast is **equivalent** at SESOI = 0.02. BO’s unconstrained and in-region columns coincide in this implementation (the GP peak already lies inside the sampled region). In-region GP is conditional on the miscalibrated posterior (Methods).

| Cell | Measured-value argmax | Naïve unconstrained | In-region |
|---|---|---|---|
| d=6, σ=0.25 | DoE by 0.0595 | BO vs naïve quadratic by 0.2931 | TOST inconclusive |
| d=6, σ=0.10 | equivalent (SESOI 0.02) | BO vs naïve quadratic by 0.3598 | GP by 0.0153 |
| d=8, σ=0.25 | DoE by 0.0284 | BO vs naïve quadratic by 0.2710 | TOST inconclusive |
| d=8, σ=0.10 | equivalent (SESOI 0.02) | BO vs naïve quadratic by 0.3228 | equivalent (SESOI 0.02) |

**Confirmation (Q58).** Same primary-cell campaigns; only the final pick moves.

| Terminal pick | Extra wells | DoE − BO |
|---|---|---|
| Single noisy readout (published) | 0 | **−0.0595** [−0.0797, −0.0375] |
| Replicate every well | +48 | −0.0262 [−0.0446, −0.0079] |
| Confirm top 3 (confirmation reading alone) | +3 | −0.0009 [−0.0263, +0.0253] (TOST inconclusive; MDE = 0.042) |
| Posterior mean at visited wells | 0 | −0.0227 [−0.0438, −0.0022] (TOST different; Wilcoxon p = 0.11) |

Confirmation-alone moves DoE from 0.0958 to 0.1437 because it re-decides from a fresh single reading and discards the CCD’s first readout. Averaging original and confirmation is **not run** (Q60): replaying Q58’s BO campaigns failed the registered 1e-12 gate (acquisition-optimizer retry). Posterior-mean pick is conditional on GP calibration (Methods). TOST table: supplement and `results/tost-contrasts.json`.

Sources: `results/e2-grid.json`, `results/q34-factorial.json`, `results/q35-constrained-rsm.json`, `results/q57-search-vs-id.json`, `results/q58-selection-sensitivity.json`, `results/tost-contrasts.json`.

### 4.2 Cost in wells and rounds (Figure 2)

A snapshot at 48 wells cannot say who is cheaper. Campaigns were extended to a 200-well cap (d = 6 only). The fair classical arm is **`doe_ascent`** (Q56): it relocates 3.4 times per campaign at σ = 0.25. `doe_repeat` never moves; those arrival tables are in supplement §S8 and must not be read as sequential RSM.

Lead with **P(T ≤ N)**. Medians among hits are not comparable across rows with different denominators.

**Measured-value argmax, `doe_ascent` vs qLogEI (Q56, registered primary ascent rule `path_argmax`).**

| σ | τ | doe_ascent | qLogEI | doe_repeat | spread_gp | Holm within rule A |
|---|---|---|---|---|---|---|
| 0.25 | 0.15 | 21/25 | 21/25 | 23/25 | 25/25 | 1.00 |
| 0.25 | 0.10 | 8/25 | 14/25 | 11/25 | 21/25 | 0.88 |
| 0.10 | 0.15 | 24/25 | 25/25 | 23/25 | 25/25 | 1.00 |
| 0.10 | **0.10** | **16/25** | **24/25** | **13/25** | **24/25** | **0.070** |
| 0.10 | 0.05 | 6/25 | 18/25 | 7/25 | 16/25 | 0.042 |

No arrival contrast survives Holm over all 26 tests. The cell Q52 reported as surviving (σ = 0.10, τ = 0.10: 24 vs 13 against `doe_repeat`) falls to 24 vs **16**, Holm 0.070, once the classical arm may walk. Under measured-value argmax, defined paired well-count ratios are 0.73–1.02: **no saving**. Under unconstrained recommendation BO still wins every cell; those ratios (0.09–0.23 at σ = 0.10) partly reflect that sequential RSM cannot speak before ~53 wells.

**One-shot GP (Q54).** Five independent Latin-hypercube draws on Hill; draw 0 reproduces Q52 exactly (550/550). Stable in 20 of 22 cells. At σ = 0.25 under **model recommendation**, one-shot GP reached τ = 0.10 on **24.4/25** landscapes versus **16/25** for 10-round qLogEI, in **one round** (unanimous across draws at τ = 0.12, 0.10, 0.08). At low noise the match holds at 0.12/0.10/0.08 and misses at 0.05. On Hartmann6, five-draw spread_gp loses (Q53). Sequential BO purchases robustness on deceptive surfaces, not a unique well-count win on this smooth Hill surface.

### 4.3 Saddle and ridge (Figure 3)

The fitted quadratic was a saddle in **200/200** Hill runs. Unconstrained minus in-region regret at the primary cell: **+0.2995** [+0.2790, +0.3228]. The ridge path leaves the design region at median radius ≈0.27 versus a corner radius of 0.50. Constraining the quadratic to the explored region removes the 0.27–0.36 unconstrained gap at the primary cell (−0.0063 [−0.0233, +0.0107]). That is why Figure 1’s unconstrained panel is a diagnostic of invalid extrapolation, not a fair RSM loss.

Sampling geometry and surrogate class contribute separately (supplement §S6): a GP on DoE points already beats the quadratic on those points; a four-factor quadratic on BO points already beats the same quadratic on the CCD. The CCD remains 4.4-fold more D-efficient **in its own region**.

### 4.4 What survives a harder test

**qLogNEI (Q57).** Better than qLogEI at all four cells, so a harder test for a DoE lead. Higher-noise measured-argmax and tested-best verdicts are unchanged. qLogNEI spots its own best well 22% vs 8% and still does not close the single-readout gap.

**Hartmann6 without 6→4 (Q59).** Removing the screen at d = 6 makes DoE **worse** by ~0.207; BO’s lead widens 1.55–1.78× against both acquisitions. Forty-seven wells over [0,1]⁶ are a thin covering; the screen was concentrating effort, not handicapping DoE. At d = 8 an unscreened second-order fit cannot fit in 48 wells (45 terms). Unscreened unconstrained regret stays ~0.87–0.90: on Hartmann the quadratic fails by misspecification, not by extrapolating out of a sub-box.

Levy and Rosenbrock reproduce the Hill terminal-rule split (supplement §S7). Ackley is void (CCD evaluates the box centre by construction).

---

## 5. Discussion

The contribution is not that BO and RSM “address different scientific questions.” Rummukainen already states that. Lapierre and Ndahiro already report executed media comparisons. Narayanan already reports large reductions against **predicted** DoE sizes. What this study isolates is that **published BO-versus-DoE conclusions are not invariant to the evaluation protocol.** Both Narayanan’s resource-planning claim and Rummukainen’s matched-budget null can be correct because their denominators and terminal decisions differ.

### Decision guide for a laboratory

Use this only as far as the benchmark reaches: a constructed Hill-like surface, six or eight factors, 48–200 wells, σ ∈ {0.25, 0.10}, q = 4 stored BO, no wet-lab confirmation. Averaged confirmation (Q60) and q = 1 BO (Q61) are not run.

1. **Need a map of a planned region, or may change the criterion later.** Run classical DoE (screen + CCD). Do not read the unconstrained polynomial peak as the answer (Figure 3). Use in-region / ridge. At the primary cell the in-region contrast is −0.0063 [−0.0233, +0.0107] (TOST inconclusive; SESOI = 0.02; MDE = 0.027).
2. **Will pick by a single noisy readout at higher noise, 48 wells.** DoE’s noisy argmax had better true f than qLogEI and qLogNEI, but about **73% of that 0.0595 is identification, not search.** Confirming the top three wells by the confirmation reading alone yields −0.0009 [−0.0263, +0.0253] (TOST inconclusive; MDE = 0.042); that protocol discards the first reading. Averaging is not run.
3. **Rounds are expensive and the surface is believed smooth.** Prefer a one-shot Latin hypercube plus one GP (1 round) over 10-round BO. On Hill, at σ = 0.25 under model recommendation, one-shot reached τ = 0.10 on 24.4/25 landscapes versus 16/25 for sequential BO. Do not carry that to a deceptive surface (Q53/Q59).
4. **The surface may be deceptive, or the campaign will continue past 48 wells.** Sequential BO led on Hartmann6 even when DoE kept all six factors. Past 48 wells, walking RSM (`doe_ascent`) matches qLogEI on arrival under measured-value argmax — do not claim BO is cheaper on that rule. Unconstrained model recommendation still favours BO, in part because the classical pipeline cannot speak before ~53 wells.

Defined fold-reductions under measured-value argmax are 0.73–1.02. Under unconstrained recommendation at σ = 0.10 they are 0.09–0.23 and should be read as *when each arm can first answer*, not as search efficiency.

---

## 6. Limitations and robustness checks

The latent function is constructed. Hall/Ogle is structural inspiration, not a fitted endothelial surface. GP coverage is in Methods. Q58’s confirmation result is for confirmation-alone; TOST on that contrast is inconclusive (MDE = 0.042), so it is not an equivalence claim. Q60 (average) and Q61 (q = 1) are unrun: sequential qLogEI is not bit-reproducible on this machine (acquisition-optimizer retry; DoE still matches at 1e-12). Cost curves were not computed at d = 8. Unconstrained long-run recommendation for `doe_ascent` is still not in-region ridge. No wet-lab validation.

Robustness (not headline): additive kernel raised R² from 0.375 to 0.744 with regret change 0.0015 (p = 0.71); acquisition-optimizer failures 4/3400 = 0.118% against a 1% threshold set in advance; 0 of 10,000 permutations matched the surrogate-effect magnitude; design-averaged BO remained ahead of a lucky LHS on 25/25 landscapes.

Excluded: two voided E2 runs; −0.0708 from an untracked grid; retracted savings-crossover at 0.15; Ackley as a DoE–BO cell; Q47 multi-fidelity; E4 as a headline.

---

## 7. Conclusions

1. Under **measured-value argmax** at higher noise, DoE attained lower regret than qLogEI by 0.0595 [−0.0797, −0.0375] at six factors and 0.0284 [−0.0447, −0.0139] at eight. qLogNEI does not remove that lead (−0.0574 [−0.0776, −0.0376] at the primary cell). **55–73% of it is identification, not search.** Confirming three wells by the confirmation reading alone yields −0.0009 [−0.0263, +0.0253] (TOST inconclusive). At lower noise DoE and qLogEI are equivalent at SESOI = 0.02.
2. Under **naïve unconstrained** recommendation, BO won by 0.27–0.36 because the quadratic was a saddle in 200/200 Hill runs; under **in-region / ridge** at the primary cell the contrast is −0.0063 [−0.0233, +0.0107] (TOST inconclusive).
3. Sequential RSM with relocation matches qLogEI on arrival under measured-value argmax. Hartmann6 favours BO even without the 6→4 screen.
4. **One-shot GP.** At σ = 0.25 under model recommendation, a single Latin hypercube plus one GP fit reached regret 0.10 on 24.4/25 landscapes versus 16/25 for 10-round qLogEI, in one round (Q54, five draws). Sequential BO purchases robustness on deceptive surfaces, not a unique well-count win on this smooth Hill surface.
5. A matched evaluation count does not define a unique comparison unless the terminal decision, noise handling, extrapolation policy, confirmation protocol, batch schedule, and cost unit are specified.

---

## Data availability

Repository artefacts (no external DOI yet). Seeds and instance ids are stored per row in the JSON. BoTorch 0.18.1, GPyTorch 1.15.2, PyTorch 2.13.0 (Q57/Q58 provenance blocks).

| Content | Path |
|---|---|
| Primary matched-budget grid | `results/e2-grid.json`, `results/e2-doe-d8.json` |
| Design × surrogate factorial | `results/q34-factorial.json` |
| Constrained RSM; saddle classification | `results/q35-constrained-rsm.json` |
| Four-factor polynomial refit | `results/q45-fourfactor-refit.json` |
| External test functions | `results/q42-families.json` |
| Cost-curve campaigns | `results/q52-budget-to-target.json` |
| Sequential RSM with steepest ascent | `results/q56-doe-ascent.json` |
| Search vs identification, both acquisitions | `results/q55-oracle-best.json`, `results/q57-search-vs-id.json` |
| Selection-rule sensitivity | `results/q58-selection-sensitivity.json` |
| Hartmann6 with and without 6→4 | `results/q59-hartmann-no-screen.json` |
| Hill one-shot GP, five draws | `results/q54-hill-spread-gp-draws.json` |
| Figure 1 | `results/figures/fig1-scoring.html` |
| Figure 2 | `results/figures/cost-curves.html` |
| Figure 3 | `results/figures/fig3-saddle.html` |
| Supplementary tables | `docs/SUPPLEMENT.md` |
| Audit trail | `docs/RESULTS.md` |
| TOST (SESOI = 0.02) | `results/tost-contrasts.json` |
| Registered, not run | Q60 averaged top-3; Q61 q=1 sequential. Spec: `docs/superpowers/specs/2026-08-17-review-response-design.md` |

---

## References

Box, G. E. P., Draper, N. R. *Empirical Model-Building and Response Surfaces.*

Box, G. E. P., Wilson, K. B., 1951. On the experimental attainment of optimum conditions. *J. R. Stat. Soc. B* 13, 1–45.

Frazier, P. I., 2018. A tutorial on Bayesian optimization. arXiv:1807.02811.

Gisperg, F., et al., 2025. Bayesian optimization in bioprocess engineering—where do we stand today? *Biotechnol. Bioeng.*

Hall, Lin, Ogle, 2025. iPSC-to-endothelial ECM screen. *Sci. Rep.*

Jones, D. R., Schonlau, M., Welch, W. J., 1998. Efficient global optimization of expensive black-box functions. *J. Global Optim.* 13, 455–492.

Lapierre, A., et al., 2025. Comparison of design of experiments and batch Bayesian optimization for growth-medium optimization of *Sporosarcina pasteurii*. *J. Chem. Technol. Biotechnol.* 100, 1571–1583. doi:10.1002/jctb.7860

Močkus, J., 1975. On Bayesian methods for seeking the extremum. In: *Optimization Techniques IFIP Technical Conference.*

Myers, R. H., Montgomery, D. C., Anderson-Cook, C. M. *Response Surface Methodology.*

Narayanan, H., et al., 2025. Bayesian optimization of cell culture media. *Nat. Commun.* 16, 6055. doi:10.1038/s41467-025-61113-5

Ndahiro, R. K., et al., 2025. Bayesian optimization of mammalian cell-culture media with solution-thermodynamic constraints. *iScience.* doi:10.1016/j.isci.2025.112944

Rummukainen, H., Hörhammer, H., Kuusela, P., Kilpi, J., Sirviö, J., Mäkelä, M., 2024. Traditional or adaptive design of experiments? A pilot-scale comparison on wood delignification. *Heliyon* 10, e24484.
