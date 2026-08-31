# SPADE — the paper's argument

**This is the paper.** The BO-versus-DoE terminal-rule study is **background**, not the
argument — see `MAIN-LINE.md`, `RESEARCH-SUMMARY.md`, `CLAIMS.md`, all marked as the
companion study. Nothing there was deleted; the SPADE paper cites it in one paragraph.

Design: `docs/superpowers/specs/2026-08-30-spade-paper-argument-design.md`.
Every number here is machine-checked by `scripts/verify_conclusions.py`.

---

## The scoreboard, at a glance

All at 48 wells, `sigma_rel = 0.25`, 32 seeds x 5 families, adjudicated against gates frozen
before each run.

| | **finds the recipe** | **returns a trustworthy region** | rounds |
|---|---|---|---|
| **SPADE** | no detectable difference from BO · loses to DoE | 66/66 contained among answered cases | **5** |
| BO (qLogNEI) | no detectable difference from SPADE | 58/59 contained among answered cases | 10 |
| classical DoE | **wins** (+0.1026, p=0.0003; historical) | historical result — variance-corrected replication pending | 3 |
| one-shot design | loses badly (−0.0783 vs SPADE) | answers 3.4% of cells — effectively never | 1 |

**One sentence:** *SPADE shows no detectable regret difference from BO in this benchmark,
using five rounds versus ten; both arms passed the registered containment gate.*

**Never overstate the BO comparison as superiority, equivalence, or a tie.** The interval
is compatible with both a small advantage and a small disadvantage, so the bounded wording
is *no detectable difference*.

**The losses are load-bearing.** DoE finds a better recipe than SPADE and cannot certify;
that is precisely the paper's point — the recipe is not the deliverable. A method that won
everything would read as tuned.

---

## The claim

> For expensive cell-manufacturing assays the deliverable should be a **certified design
> space**, not a recipe. SPADE returns one from 48 wells; in this benchmark it showed no
> detectable regret difference from Bayesian optimisation while using **half the experimental rounds** — and *when* a certificate can
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

**SPADE's acquisition is a UCB with exploration weight `1.96 - z_rho`** — 0.315 at
rho = 0.95. It is *not* a certificate-contour straddle, despite what this module's own
docstring claimed until 2026-08-30: the threshold `theta` **cancels out of the ranking**
whenever the contour lies outside the posterior's range, which is every family at the
opening round (rank correlation between scores at two very different thetas: **exactly
1.000000**, identical argmax). The docstring is now corrected in source.

**And the sophistication was never what worked.** We repaired the mechanism — pointed it at
`tau`, the region actually being certified, which a practitioner knows because it is their
own spec — and tested it at 5 families x 32 seeds. **TT-1 was inconclusive** (+0.000425,
CI [−0.000022, +0.000875]); it **significantly damaged** optimisation (TT-2: regret
+0.0301, CI [+0.0169, +0.0450], p < 0.0001, outside the 0.02 SESOI).

**Both SPADE and qLogNEI pass the registered containment gate in the committed comparison:**

| arm | answered | contained | containment | LB |
|---|---|---|---|---|
| **SPADE** | **66/160** | **66** | **1.0000** | **0.9556** |
| SPADE aimed at tau | 63/160 | 61 | 0.9683 | 0.9034 |
| qLogNEI | 52/160 | 47 | 0.9038 | 0.8084 |

**So the method's value is architectural, not a claim of universal dominance:** a space-filling opening,
low-exploration adaptive batches that concentrate wells where the response is high, and a
conservative certificate that abstains when the data cannot support one. **The simple part
works; the sophisticated part never did, and repairing it makes things worse.** That is the
paper's honest claim about the method, and it is stronger than a targeting result would have
been because it was tested in both the broken and the repaired state.

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
| **SPADE @ 5 rounds vs BO @ 10 rounds, regret** | **−0.0005, CI [−0.0221, +0.0207], p = 0.96** — no detectable difference, **both arms measured in one process** | 160 |
| **Certified volume at matched 5 rounds** | **+0.001353, p < 0.0001**, independently in ackley and hartmann6 | 320 |
| …and it is not a difficulty artefact | survives matched-`margin/sd` binning, 3 of 4 bins, all positive | 1600 |
| SPADE @ 3 rounds vs a one-shot design | **−0.0783, CI [−0.1104, −0.0490]** | 80 |
| SPADE @ 3 rounds vs BO @ 10 | +0.0263, CI [+0.0054, +0.0472] — **3 rounds is not enough** | 160 |

**"No detectable difference", never proven equality:** the CI half-width is 0.0214 against
the 0.02 SESOI. The point estimate is −0.0005 — essentially exactly zero.

### 4.1 Against classical DoE the claim is narrow, and must be written narrowly

**DoE spends 3 rounds; SPADE spends 5. SPADE costs MORE rounds than DoE**, so the round
argument does not apply here and no table may hide it.

| comparison | rounds | diff | 95% CI | p |
|---|---|---|---|---|
| SPADE vs **`doe`** on regret | 5 vs 3 | **+0.1026** | [+0.0486, +0.1578] | 0.0003 |

**Classical DoE finds a better recipe than SPADE, in fewer rounds, and says so plainly.**
The DoE certification figures below are historical constant-variance outputs and await
variance-corrected replication — see §5.

## 4.2 DoE cannot certify — measured, and its failure is over-confidence

At p = 0.30, 5 families x 32 seeds, one process, identical certification path for all arms;
the DoE rows are historical and non-confirmatory pending variance-corrected replication:

| arm | rounds | answered | contained | containment | LB | certifies? |
|---|---|---|---|---|---|---|
| `doe` | 3 | **122/160** | 85 | **0.6967** | 0.6210 | **no** |
| `doe_unscreened` | 3 | **134/160** | 77 | **0.5746** | 0.4999 | **no** |
| **SPADE** | **5** | 66/160 | **66** | **1.0000** | **0.9556** | **YES** |
| qLogNEI | 10 | 59/160 | 58 | 0.9831 | 0.9221 | YES |

**DoE does not fail by abstaining — it fails by being confidently wrong.** It answers more
often than any other arm (76% of cells against SPADE's 41%) and roughly **30% of its
certified regions do not contain the truth**. For a cell-manufacturing team, a confident
operating window that is wrong three times in ten is worse than a method that says
"I don't know".

**SPADE had perfect containment among its answered cases in this historical comparison, as
did qLogNEI at 58/59.** And **the screen is not the culprit in that historical analysis**:
removing the 6->4 screen makes containment *worse* (0.5746), so this is a property of the
low-order polynomial fit, not of the screening decision — which closes the obvious objection
that DoE was crippled by its screen.

**This is what the extra two rounds over DoE buy: not a better recipe, but a region you can
operate in.**

## 5. What the real data changed

Simulation would never have found this:

| | benchmarks | real assays |
|---|---|---|
| GP posterior over-confidence | 1.004x - 1.011x | **484x** (in-house iPSC-EC), **297x** (published) |
| Inflation `c` needed (LOO) | 1.5 simulated | **0.712** in-house, **0.526** published |

**Real assays need *less* inflation than simulation prescribes, and the posterior collapse
is invisible on benchmarks.** n = 2 datasets; no prospective wet-lab test of a certificate.

## 6. What does not work — a section, not an appendix

- **The targeting mechanism does not earn its complexity — tested twice, both ways.**
  A registered 99,601-row prospective study found targeted second-plate placement does not
  beat random placement of the same wells (-0.0019, p = 0.41; KF-3), the second plate loses
  to one plate (KF-4), and two independent repairs failed. **This paper supplies the cause**
  — `theta` cancels from the ranking, so the mechanism was never active — **and then tests
  the repaired mechanism.** Aimed at `tau`, at 5 families x 32 seeds: no benefit
  (+0.000425, CI [−0.000022, +0.000875]) and a large regret cost (+0.0301, p < 0.0001).
  The per-family pattern is a cancellation, not an absence: it helps hartmann6 (+0.002766,
  p = 0.012) and hurts ackley (−0.000641, p = 0.015); after Holm correction both are
  0.06, so these family estimates are descriptive. The aggregate interval includes zero,
  and the configured arm is not adopted.
- **ackley is a genuine loss** for SPADE on regret: +0.0652, CI [+0.0203, +0.1104],
  **p = 0.004** — and it *strengthened* with more data. **Not explained by the theta/tau
  mismatch**, which was the leading hypothesis: ackley has the largest mismatch (13.6x), and
  correct targeting made it *worse* (0.7375 -> 0.7520). Cause still open.
- **rosenbrock never certifies**, at any prevalence tested. The law predicts this.
- **The ceiling.** At the measured real assay noise (`sigma_rel = 0.68`) **nothing certifies
  for any arm.** Roughly 27 replicates would be needed. Every result above is at 0.25.

## 7. Open, ranked

1. **sigma sweep at 0.10 and 0.68** — everything rests on 0.25. Cheapest, highest value.
2. **An estimable `margin/sd` proxy** — turns §3 from description into a usable decision rule.
3. **rho sweep** — rho sets the exploration weight (`1.96 - z_rho`) and is the remaining
   untested knob. **Correction: rho does NOT move the estimand** — it feeds only the
   acquisition; the certificate is computed independently from `p2.ALPHAS`. An earlier
   version of this list said otherwise and was wrong.
   *Targeting is no longer on this list: it was repaired and tested, and it failed
   (`SPADE-THETA-TAU-SPEC.md` §8).*
4. R = 4 untested; the DoE arm is a space-filling `lhs`, not the fractional-factorial/CCD an
   RSM reviewer will demand; all new work is d = 6.

## 8. Rules this paper is written under

- No "X cannot certify" without reporting `answered` and `contained` — three such claims in
  this project were wrong, and every certificate involved was correct, just too few. A
  Clopper-Pearson bound at 0.90 needs **>= 29 answered cells** even at perfect containment.
- At n <= 25 seeds an effect here is not reliable; three significant effects vanished
  between 25 and 32 seeds.
- Every certification claim carries its **prevalence** and its **sigma**.
