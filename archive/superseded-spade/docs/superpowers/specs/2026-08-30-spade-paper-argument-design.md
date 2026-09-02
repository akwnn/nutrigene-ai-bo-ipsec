# SPADE as the paper's argument — design

**Status:** approved spine, 2026-08-30. **Date:** 2026-08-30.
**Decision owner:** Joseph. **Supersedes:** the terminal-rule study as the lead argument.

## 1. The decision

The paper's argument is **SPADE as a cell-manufacturing optimiser whose deliverable is a
certified design space**, with cross-family evidence that the argument generalises. The
terminal-rule study (BO-vs-RSM ranking reversal) is **demoted to the companion study** it
already is in `SPADE_paper_draft.md`'s own background section. **Nothing is deleted.**

## 2. Thesis

> For expensive cell-manufacturing assays the deliverable should be a certified design
> space, not a recipe. SPADE returns one from 48 wells, at optimisation quality equal to
> Bayesian optimisation in half the experimental rounds — and *when* a certificate can be
> trusted is governed by a single measurable quantity that holds across every benchmark
> family tested.

## 3. Structure

| § | content | evidence | status |
|---|---|---|---|
| 1 | Cell manufacturing needs a design space (ICH Q8), not a recipe | real iPSC-EC; Hall & Ogle | have |
| 2 | SPADE and the certificate | `boec.multiround`, `boec.meanmarg` | **definition needs restating (§6.2)** |
| 3 | Cross-family generalisation: `margin/sd` | rho = 0.9801, 25 cells, 5 families | have, **but oracle-dependent (§6.1)** |
| 4 | Rounds are the binding cost | SPADE@5 = BO@10 (+0.0016); volume +0.001353 p<0.0001 | have, marginal |
| 5 | Real data | 484x / 297x collapse; LOO c=0.712 vs 1.5; CD31+ >= 33.2% | have, n=2 |
| 6 | What does not work | theta cancels; ackley; rosenbrock; sigma=0.68 ceiling | have, **unrepaired (§6.3)** |

Real cells are **motivation and demonstration, not validation** — no new wet-lab work, and
the 12 CD31 gates stay unsigned. §3 is load-bearing for "it generalises", because the law
*predicts* the exceptions (rosenbrock) rather than hiding them.

## 4. Deliverables

1. `docs/SPADE-PAPER-ARGUMENT.md` — the spine. Every claim -> number -> result file ->
   script. The single source the manuscript is written from.
2. Companion headers on `MAIN-LINE.md`, `RESEARCH-SUMMARY.md`, `CLAIMS.md`. Bodies
   untouched, so every cited number and the KF ledger stay reachable.
3. Repoint `SPADE-STATE-OF-THE-METHOD.md`, `HANDOFF-2026-08-30.md` and
   `SPADE-CONCLUSIONS-2026-08-29.md` at the spine.
4. Extend `scripts/verify_conclusions.py` to machine-check the spine's numbers.

**Explicitly out of scope here:** rewriting `SPADE_paper_draft.md` (62 KB, two-plate era,
and it lives *outside* this repo in `/Users/jy/BO/`). The spine becomes the source it is
later rewritten from. Also out of scope: the tau_frac sentence in `RESEARCH-SUMMARY.md`'s
abstract — that is now the companion paper's problem.

## 5. Risk the structure must absorb

§6 has to carry KF-3/KF-4/KF-5. A reviewer will find them. Framed as *"the mechanism was
never active, and here is the line that made it a no-op"*, it is a strength — the registered
negative result plus its code-level cause. Framed as an appendix, it sinks the paper. §6 is
written as a full section.

## 6. KNOWN GAPS — recorded before writing, not discovered in review

### 6.1 `margin/sd` is not computable by a practitioner (most serious)
The law is measured from **oracle truth**: `margin` is the mean excess of the *true* good
region over tau, `noise_sd` is `sigma_rel` x the *true* response level. A bench scientist
does not know `f`. **As it stands §3 is diagnostic, not prescriptive.** Needs an estimable
posterior-based proxy; that experiment does not exist.

### 6.2 SPADE has no current definition
`multiround.py`'s docstring claims the acquisition targets "the certificate contour, not
Bryan's straddle". **Measured false:** theta cancels from the ranking (rank correlation
1.000000 at two thetas). SPADE is a UCB with exploration weight `1.96 - z_rho`. The
docstring and any paper text must be restated before §2 can be written. Multi-round SPADE
has also never been compared head-to-head with the two-plate SPADE the KF ledger tested.

### 6.3 The mechanism is diagnosed but unrepaired
The rho sweep was never run, so KF-3's "targeting does not beat random" tested a **disabled**
mechanism. We may write "it was never active"; we may **not** write anything about whether a
working targeting rule beats random.

### 6.4 One noise level
Everything is `sigma_rel = 0.25`. Sigma sensitivity is unrun. At the measured real noise of
0.68 **nothing certifies for any arm**. Whether the law survives at 0.10 and 0.68 is unknown.

### 6.5 Smaller
- Round parity sits *on* the SESOI edge: half-width 0.0196 vs 0.0200.
- R = 4 untested (absent from LC's `CONFIGS`, declared before that run).
- The DoE comparator is `lhs`, a one-shot space-filling design, **not** the
  fractional-factorial/CCD an RSM reviewer will demand.
- Real data is **n = 2** datasets, with no prospective certificate test.
- All new work is d = 6; the cross-family law has no DoE arm.

## 7. Next experiments, ranked

1. **sigma sweep at 0.10 and 0.68** — cheapest, and it either promotes the law or bounds it.
2. **An estimable `margin/sd` proxy** from the posterior — turns §3 into a usable rule.
3. **rho sweep** — the only route from "we found the bug" to "we fixed it". **rho is the
   certificate's Vorob'ev level, so it moves the estimand; register the trade first.**
