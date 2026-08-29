# SPADE — conclusions as of 2026-08-29

What is established, what was withdrawn, and how each was obtained. Every number below
traces to a committed result file and an adjudicator script written before its data landed.

---

## 1. The claims that stand

| # | claim | evidence | where |
|---|---|---|---|
| 1 | **SPADE at 5 rounds matches qLogNEI at 10 on regret** | +0.0016, CI [−0.0184, +0.0208], half-width 0.0196 < SESOI 0.0200, n=160 | LC §9.1 |
| 2 | **SPADE certifies more volume at matched 5 rounds** | +0.001353, p<0.0001; independently in ackley and hartmann6 | LC §9.1 |
| 3 | **…and that win is not a difficulty artefact** | survives matched-`margin/sd` binning in 3 of 4 bins, all positive | TAU §8.4 |
| 4 | **Certification generalises to a dose-response landscape** | `hill`, prevalence 0.70: 40/64 answered, **40 contained**, LB 0.9278 | TAU §8.1 |
| 5 | **Certifiability obeys a measured law** | Spearman ρ(`margin/sd`, answer rate) = **0.9801**, 25 cells, p<0.0001 | TAU §8.3 |
| 6 | **SPADE beats a one-shot space-filling design at 3 rounds** | −0.0783, CI [−0.1104, −0.0490] | parity analysis |

**The thesis these support:** SPADE does not optimise better than BO — it *matches* it.
What it does better is **certify**: more of the design space, at comparable containment,
including on the biphasic dose-response landscape BO could not reach at this sample size.

**Unchanged ceiling:** every result is at `sigma_rel = 0.25`. At the measured real assay
noise of 0.68, **nothing certifies for any arm** (`SPADE-REALISTIC-NOISE-SPEC.md` §6).

---

## 2. What was withdrawn today, and why

| withdrawn | why | where |
|---|---|---|
| "SPADE certifies at 5 rounds, qLogNEI needs 10" | qLogNEI certifies at R=3 **and** R=5 once n is adequate | LC §8.1 |
| "SPADE beats BO on regret at matched rounds" | −0.0235 (excl. 0) at 25 seeds → −0.0181 (straddles 0) at 32 | LC §9.1 |
| "SPADE wins certified volume at R=3" | +0.000242 p<0.0001 at 25 seeds → −0.000034 p=0.456 at 32 | LC §9.1 |
| "hill saturates because it is a dose-response" | it saturates because of target SNR; at prevalence 0.70 it certifies | TAU §8.1 |
| "the ackley loss is the `mu_max` fallback" | θ **cancels** out of the acquisition; the fix changes nothing | ACK §8 |

**Five withdrawals in one day.** Four were mine from earlier the same day. They are kept
here rather than deleted, per this project's convention.

---

## 3. The single cause behind most of them

**A Clopper–Pearson lower bound at 0.90 needs ≥ 29 answered cells even with PERFECT
containment** (`0.05^(1/n) ≥ 0.90` → n ≥ 29). Nearly every "X cannot certify" conclusion in
this project was drawn below that threshold, and each was a statement about sample size
wearing the costume of a statement about method:

| claimed | answered | contained | containment | LB | truth |
|---|---|---|---|---|---|
| qLogNEI can't certify at R=5 | 31 | 30 | 0.9677 | 0.8559 | certifies at 62 answered |
| `hill` can't certify | 17 | **17** | **1.0000** | 0.8384 | certifies at 40 answered |
| `levy` can't certify | 13 | **13** | **1.0000** | 0.7942 | certifies at 31 answered |

Every one of those certificates was **correct**. There were merely too few of them.

**Standing rule, now in the specs:** no "X cannot certify" may be stated without reporting
`answered` and `contained` beside it.

**Second rule, from the 25→32 seed extension:** three effects that were significant at 25
seeds vanished at 32. **At n ≤ 25 seeds an effect in this project is not reliable**; only
effects several times their own CI have survived.

---

## 4. How each result was obtained

**Method discipline.** Every experiment had its gate frozen and committed *before* its data
existed, and the commit timestamps precede the result-file mtimes:

- `SPADE-LC-CONFIRMATORY-SPEC.md` — frozen at seed 13 of 25, mid-run (`19f845a`, `a64e3a4`)
- `SPADE-TAU-DEGENERACY-SPEC.md` — frozen before any TAU row existed (`f696567`)
- `SPADE-ACKLEY-THETA-SPEC.md` — frozen before any ACK row existed

**Reproduction gates.** Each new runner had to reproduce the previous experiment before its
own numbers were read. TAU reproduced LC on 32 overlapping cells with 0 mismatches; the
`resolve_theta` change reproduced committed SPADE regret to 1e-12 on 6 cells.

**Adversarial gates.** TAU-3 was registered *against* our own surviving claim (claim 2),
because SPADE answers more cells and answering more mechanically inflates its own CP bound.
It passed. TAU-1 was registered so that a failure would retract the `margin/sd` mechanism.
ACK-1 was registered so that a failure would retract its own root cause — **and it did**.

**Pre-declared stopping.** The TAU extension to 64 seeds was declared in §7.4 *before*
running, with the explicit note that one miss at n=34 would fail it, and bound to a single
adjudication. Extending again would have been optional stopping.

**Calibration honesty.** The published certification numbers use `c` selected in-sample.
Leave-one-family-out is degenerate here (only two families supply certificates, so holding
one out destroys calibration). Leave-one-**seed**-out keeps every family in and still scores
out-of-sample: it returned **LB 0.9342, identical to the pooled figure, with 10/10 folds
choosing the same `c`** — selection is stable, so the pooled number was not an artefact.

---

## 5. The open items, in priority order

1. **`ackley` is SPADE's one real weakness** — +0.0652, CI [+0.0203, +0.1104], **p=0.004**,
   and it *strengthened* from p=0.029 at 25 seeds. The only effect today that grew with n.
   The live hypothesis is **ρ**, not θ: SPADE's acquisition is really
   `argmax (1.96 − z_ρ)·sd + mean`, so ρ=0.95 gives an exploration weight of just **0.315**,
   which is little for a needle-in-a-haystack landscape. **Moving ρ changes the certificate's
   Vorob'ev level, i.e. the estimand — so the trade must be registered before it is run.**
2. **qLogNEI on `hill` at ~96 seeds** — it currently misses by two answered cells (27 vs the
   29 needed) at containment 1.0000. State the coverage gap as a margin (40 vs 27), not as a
   threshold crossing, and pre-empt the reviewer who notices.
3. **The DoE arm is a space-filling `lhs`**, not the fractional-factorial/CCD a reviewer will
   demand. Claim 6 is real but the baseline is not the one the field expects.
4. **The R=4 tie is still untested** — no R=4 in LC's `CONFIGS`, declared before that run.
5. **Sign the 12 CD31 gates in CytExpert** — still the only step between the in-house result
   and a wet-lab claim, and still needs a person.

---

## 6. What must not be written

- **Not** "SPADE certifies the dose-response family and BO cannot." Both arms have
  containment 1.0000 on `hill`; qLogNEI misses by two answered cells and would pass at ~96
  seeds. The durable claim is **coverage: 40 vs 27 answered at identical containment**.
- **Not** "SPADE straddles the certificate contour." Measured: θ cancels from the ranking
  whenever the contour lies outside the posterior range, which is every family at the
  opening round. It is a UCB with exploration weight `1.96 − z_ρ`.
- **Not** any certification claim without its **prevalence** attached. `hill` certifies at
  prevalence 0.70, not 0.10.
- **Not** any regret or certification claim without `sigma_rel = 0.25` attached.
