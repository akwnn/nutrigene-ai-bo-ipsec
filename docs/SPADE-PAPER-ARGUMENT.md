# SPADE — the paper's argument

**This is the paper.** The BO-versus-DoE terminal-rule study is **background**, not the
argument — see `MAIN-LINE.md`, `RESEARCH-SUMMARY.md`, `CLAIMS.md`, all marked as the
companion study. Nothing there was deleted; the SPADE paper cites it in one paragraph.

Design: `docs/superpowers/specs/2026-08-30-spade-paper-argument-design.md`.
Every number here is machine-checked by `scripts/verify_conclusions.py`.

---

## The claim

> For expensive cell-manufacturing assays the deliverable should be a **certified design
> space**, not a recipe. SPADE returns one from 48 wells, at optimisation quality equal to
> Bayesian optimisation in **half the experimental rounds** — and *when* a certificate can
> be trusted is governed by a **single measurable quantity** that holds across every
> benchmark family tested.

**Why anyone should care.** A cell-manufacturing process is not released on one good recipe.
ICH Q8 asks for a *design space* — a region you can operate anywhere inside. Every method in
this comparison hands back a point. SPADE hands back a region **with a 95% guarantee**, and
says "I don't know" when the data cannot support one.

---

## 1. Cell manufacturing needs a region, not a recipe

| | |
|---|---|
| Your iPSC-EC cells, fully corrected | **CD31+ >= 33.2%** across the whole coating box at 95% |
| Published ECM data (Hall & Ogle) | certified independently, same pipeline |
| The object practitioners are asked for | ICH Q8 design space, not a setpoint |

## 2. What SPADE is

48 wells. An opening space-filling design, then `R-1` adaptive batches. After each batch the
GP is refit and the next batch is chosen; at the end a conservative excursion certificate is
computed from the joint posterior, and reported only if it clears the bar.

> **Stated correctly, which the source code does not yet do.** `multiround.py`'s docstring
> claims the acquisition targets "the certificate contour". **That is false and measured
> false:** the threshold `theta` cancels out of the ranking whenever the contour lies
> outside the posterior's range — which is every family at the opening round. Rank
> correlation between scores at two very different thetas is **exactly 1.000000**, with
> identical argmax. **SPADE's acquisition is a UCB with exploration weight `1.96 - z_rho`**
> (0.315 at rho = 0.95). See §6. The docstring must be corrected before submission.

## 3. It generalises: certifiability obeys one number

Across 5 families x 5 target prevalences, the answer rate is governed by `margin/sd` — how
far the good region sits above the threshold, in units of the noise there:

| family | margin/sd (p=0.30) | certification rate |
|---|---|---|
| hartmann6 | 2.52 | 66.7% |
| ackley | 1.25 | 33.8% |
| hill | 0.34 | 0.5% |
| levy | 0.26 | 0.1% |
| rosenbrock | 0.17 | 0.0% |

**Spearman rho = 0.9801 over 25 (family, prevalence) cells, p < 0.0001.**

This is the section that makes "it generalises" a real claim: the law **predicts its own
exceptions.** rosenbrock failing is not an embarrassment, it is the law being right.

**Raise the target's prevalence and the prediction holds.** At prevalence 0.70, `hill` — the
biphasic dose-response family, the one shaped like the actual biology — **certifies**:
40 of 64 answered, **40 of 40 contained**, LB **0.9278**. `levy` certifies too (LB 0.9079).

> **Honest limit, stated here and not buried.** `margin` and `sd` are computed from the
> **true** response surface. A bench scientist does not know `f`, so as measured this law
> **explains** benchmark behaviour but cannot yet be **applied** to a new assay. An
> estimable posterior-based proxy is the single most valuable open experiment (§7).

## 4. Rounds are the cost that binds

Wells are cheap; a round is a full differentiation cycle — days to weeks, a fresh cell lot,
operator time.

| comparison | result | n |
|---|---|---|
| **SPADE @ 5 rounds vs BO @ 10 rounds, regret** | **+0.0016, CI [-0.0184, +0.0208]** — parity within the registered SESOI of 0.02 | 160 |
| **Certified volume at matched 5 rounds** | **+0.001353, p < 0.0001**, independently in ackley and hartmann6 | 320 |
| …and it is not a difficulty artefact | survives matched-`margin/sd` binning, 3 of 4 bins, all positive | 1600 |
| SPADE @ 3 rounds vs a one-shot design | **-0.0783, CI [-0.1104, -0.0490]** | 80 |
| SPADE @ 3 rounds vs BO @ 10 | +0.0263, CI [+0.0054, +0.0472] — **3 rounds is not enough** | 160 |

**Parity sits on the SESOI edge** (half-width 0.0196 against 0.0200) and is stated as
parity-within-SESOI, never as equality.

## 5. What the real data changed

Simulation would never have found this:

| | benchmarks | real assays |
|---|---|---|
| GP posterior over-confidence | 1.004x - 1.011x | **484x** (in-house iPSC-EC), **297x** (published) |
| Inflation `c` needed (LOO) | 1.5 simulated | **0.712** in-house, **0.526** published |

**Real assays need *less* inflation than simulation prescribes, and the posterior collapse
is invisible on benchmarks.** n = 2 datasets; no prospective wet-lab test of a certificate.

## 6. What does not work — a section, not an appendix

- **The targeting mechanism is a no-op.** A registered 99,601-row prospective study found
  targeted second-plate placement does **not** beat placing the same wells at random
  (-0.0019, p = 0.41; KF-3), the second plate loses to one plate (KF-4), and two independent
  repairs both failed. **This paper supplies the cause:** `theta` cancels from the
  acquisition ranking, so the targeting was never active. **KF-3 tested a disabled
  mechanism.** Whether a *working* targeting rule beats random is untested (§7).
- **ackley is a genuine loss** for SPADE on regret: +0.0652, CI [+0.0203, +0.1104],
  **p = 0.004** — and it *strengthened* with more data.
- **rosenbrock never certifies**, at any prevalence tested. The law predicts this.
- **The ceiling.** At the measured real assay noise (`sigma_rel = 0.68`) **nothing certifies
  for any arm.** Roughly 27 replicates would be needed. Every result above is at 0.25.

## 7. Open, ranked

1. **sigma sweep at 0.10 and 0.68** — everything rests on 0.25. Cheapest, highest value.
2. **An estimable `margin/sd` proxy** — turns §3 from description into a usable decision rule.
3. **rho sweep** — the only route from "we found the bug" to "we fixed it". **rho is the
   certificate's Vorob'ev level, so it moves the estimand: register the trade first.**
4. R = 4 untested; the DoE arm is a space-filling `lhs`, not the fractional-factorial/CCD an
   RSM reviewer will demand; all new work is d = 6.

## 8. Rules this paper is written under

- No "X cannot certify" without reporting `answered` and `contained` — three such claims in
  this project were wrong, and every certificate involved was correct, just too few. A
  Clopper-Pearson bound at 0.90 needs **>= 29 answered cells** even at perfect containment.
- At n <= 25 seeds an effect here is not reliable; three significant effects vanished
  between 25 and 32 seeds.
- Every certification claim carries its **prevalence** and its **sigma**.
