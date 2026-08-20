# Where Bayesian optimization actually wins — the evidence, ranked

**Written 2026-08-20.** Every number below is recomputed from committed JSON, not copied from
prose. Contrast convention throughout: **DoE/RSM minus BO**, so **positive = BO better**.

**The standard applied here.** Running variants until one favours BO is selection, not evidence,
and `PROMPTS-NEXT.md` forbids it ("do not invent a winner"). What counts is a comparison BO could
have lost and did not. Items are ranked by how hard they are to attack, and the attack on each is
stated. Items 2 and 3 are weaker than they look, and the reasons are given rather than hidden.

---

## 1. STRONGEST — Hartmann6, same rule, same budget, same noise, BO wins by 0.26–0.30

`results/q59-hartmann-no-screen.json`, sigma = 0.25, n = 25, **measured-value argmax**.

| Arm | Mean regret |
|---|---:|
| qLogNEI | **0.2642** |
| qLogEI | **0.2984** |
| DoE/RSM, screened 6->4 | 0.5623 |
| DoE/RSM, unscreened | 0.7685 |

| Contrast | Mean | 95% CI | Wilcoxon P |
|---|---:|---|---:|
| DoE screened − qLogEI | **+0.2639** | [+0.1949, +0.3304] | 1.5e-06 |
| DoE screened − qLogNEI | **+0.2981** | [+0.2261, +0.3709] | 4.2e-07 |
| DoE unscreened − qLogEI | +0.4701 | [+0.3974, +0.5329] | 1.2e-07 |

**Why this is the best evidence in the project.** It uses the *same terminal rule that DoE wins
under on Hill* — carry forward the largest noisy reading. Same 48-well budget. Same noise level.
Nothing was re-read, re-scored, or re-picked. **Only the shape of the landscape changed**, and the
ranking inverts by a margin an order of magnitude larger than the Hill result, at P ~ 1e-6.

**Attack, and the answer.** "You handed DoE a landscape it cannot fit." Partly true, and that *is*
the finding: a second-order polynomial cannot represent a multimodal surface, so the classical
pipeline fails structurally rather than by bad luck. Note the screen *helped* the classical arm here
(0.5623 screened vs 0.7685 unscreened), so the comparison is not rigged by the 6->4 cut.

**What it licenses.** "On multimodal landscapes, BO beats matched-budget RSM under the same
single-readout rule, decisively." Not "BO is better."

---

## 2. LARGEST MARGIN, WEAKEST EVIDENCE — unconstrained model recommendation

`results/q34-factorial.json`. Positive = BO better.

| Cell | DoE quadratic | BO GP | Contrast |
|---|---:|---:|---|
| d=6, sigma=0.10 | 0.4300 | 0.0703 | **+0.3598** [+0.3423, +0.3774] |
| d=6, sigma=0.25 | 0.4163 | 0.1232 | **+0.2931** [+0.2659, +0.3215] |
| d=8, sigma=0.10 | 0.4104 | 0.0876 | **+0.3228** [+0.3045, +0.3409] |
| d=8, sigma=0.25 | 0.3766 | 0.1056 | **+0.2710** [+0.2423, +0.2989] |

Every interval excludes zero by a wide margin, in all four cells.

**Do not lead with this.** The DoE side is the *naive unconstrained* maximisation of a fitted
quadratic over the whole box, and **200/200 of those fits are saddles**, so the recommendation is
driven to a far boundary. The project's own position is that this is a diagnostic of unsupported
extrapolation, not what a competent practitioner ships. Restricting the quadratic to the sampled
region collapses the gap to **−0.0063** (inconclusive) at the primary cell. Leading with the
unconstrained number is a strawman, and a reviewer who knows ridge analysis will say so.

**What it licenses.** "Unconstrained polynomial extrapolation from a saddle is catastrophic, and a
GP does not have that failure mode." That is a statement about locators, not about BO.

---

## 3. COST — BO arrives at tight targets far more often, at low noise

Recomputed from `results/q52-budget-to-target.json`, cap N=200, measured-value argmax, both seeds
required to hit. Landscapes out of 25.

| sigma | target | qLogEI | CCD in place | one-shot GP | random |
|---|---:|---:|---:|---:|---:|
| 0.25 | 0.15 | 21 | 23 | 25 | 25 |
| 0.25 | 0.10 | 14 | 11 | 21 | 23 |
| 0.25 | 0.05 | **6** | 4 | 9 | 4 |
| 0.10 | 0.15 | 25 | 23 | 25 | 25 |
| 0.10 | 0.10 | **24** | 13 | 24 | 25 |
| 0.10 | 0.05 | **18** | 7 | 16 | 9 |

The fair classical comparator is **relocating** RSM (`doe_ascent`, Q56), not the CCD-in-place
control above: 16/25 at sigma=0.10 / tau=0.10 and 6/25 at tau=0.05. qLogEI still leads both.

**Three honest caveats.**
- At loose targets everyone arrives, including **random**. The BO advantage lives only at tight
  targets, and only at low noise.
- Random beats qLogEI at sigma=0.25, tau=0.10 (23 vs 14). Do not present arrival as a general BO win.
- Multiplicity: the paper states no pairwise arrival contrast survived Holm across 26 tests.

**⚠ Flagged inconsistency.** Table 5 of `RESEARCH-SUMMARY.md` prints a multiplicity-adjusted
P of **0.042** at sigma=0.10 / tau=0.05 while the surrounding text says no contrast survived Holm.
Those cannot both be right. Resolve before submission — a reviewer will find it.

---

## 4. SMALL AND CLEAN — search quality at low noise

`results/q57-search-vs-id.json`, hidden tested-best (search only, no locating).

| Cell | vs qLogEI | vs qLogNEI |
|---|---|---|
| d=6, sigma=0.10 | +0.0048 [−0.0033, +0.0131] | **+0.0109 [+0.0019, +0.0197]** |

One clean directional result: at six factors and low noise, **qLogNEI visits better wells than the
classical design does**. Small, but it excludes zero, and it is a statement about search rather than
about a scoring convention.

Also in-region model recommendation at that cell: **+0.0153 [+0.0042, +0.0269]**, GP favoured
(exploratory).

---

## 5. Where BO ties, and where it loses — stated so the list is not one-sided

**Ties — and as of Q68 this is now a DECLARED tie, not a shrug.** The primary-cell
in-region contrast read −0.0063 [−0.0233, +0.0107], *inconclusive*, at n=25. At **n=100**:

| Contrast | n=25 | n=100 |
|---|---|---|
| DoE quad − qLogEI GP | −0.0055 [−0.0215, +0.0119] inconclusive | **−0.0023 [−0.0100, +0.0057] EQUIVALENT** |
| DoE quad − qLogNEI GP | −0.0091 [−0.0260, +0.0086] inconclusive | **−0.0006 [−0.0098, +0.0082] EQUIVALENT** |

**This is the sentence the paper was missing.** Under the fair in-region readout, at matched
budget and the primary noise level, BO and classical RSM are **statistically equivalent within
the smallest effect the study declared interesting** — not "we could not tell." It is the
result that makes the terminal-rule thesis land, because it shows the entire gap lives in the
readout rather than in the method.

The other two verdicts sharpen at n=100 rather than move:
measured-value argmax **−0.0668 [−0.0754, −0.0582]** (DoE better, declared different);
unconstrained model **+0.2951 [+0.2813, +0.3082]** (BO better, declared different).

So all three terminal rules at the primary cell now carry a *declared* verdict:
**DoE better / equivalent / BO better**, depending only on the rule. That is the thesis,
fully powered.

At d=8 / sigma=0.10: +0.0001, equivalent within 0.02 (n=25, unchanged).

**Loses.** Measured-value argmax at sigma = 0.25, both dimensions, both acquisitions:

| Cell | vs qLogEI | vs qLogNEI |
|---|---|---|
| d=6, sigma=0.25 | −0.0595 [−0.0792, −0.0373] | −0.0574 [−0.0770, −0.0370] |
| d=8, sigma=0.25 | −0.0284 [−0.0453, −0.0140] | −0.0142 [−0.0252, −0.0036] |

**Under measured-value argmax, BO does not significantly beat the classical arm in ANY of the four
Hill cells.** That is the honest summary of the headline rule, and no amount of re-slicing changes it.

---

## 6. Why the obvious rescue does not work — Q65

A budget-neutral explore/confirm split was run as an exploratory pilot: take wells out of the 48 and
spend them re-measuring a shortlist. Primary cell, DoE comparator gated bit-exact (worst 0.0).

| Split | Rule | Regret | Search | Identification gap |
|---|---|---:|---:|---:|
| 48/0 | DoE/RSM | 0.0958 | 0.0597 | 0.0361 |
| 48/0 | BO baseline | 0.1552 | 0.0804 | 0.0748 |
| 44/4 | wide | 0.1529 | 0.0857 | 0.0672 |
| 40/8 | wide | 0.1535 | 0.0902 | 0.0633 |
| 36/12 | wide | 0.1595 | 0.0965 | 0.0630 |
| 36/12 | deep | 0.1539 | 0.0965 | 0.0574 |

Identification improves monotonically — the mechanism is real. Search degrades in lockstep. Net
change at best split: **0.0023**, roughly a tenth of the 0.02 SESOI. **Confirmation does not pay for
itself when the wells come out of the budget.** Contrast with Table 4, where +48 *free* wells narrow
the gap from −0.0595 to −0.0262.

**The rule this establishes: an intervention that costs wells will be cancelled by lost search.
Only free interventions can close the identification gap.**

---

## 6b. The free readout that DOES work — Q67, and the honest way to state it

Q66 tested a local quadratic fitted to the incumbent's neighbourhood on wells BO already
ran. **It fails, at both noise levels**: 94% saddles at sigma=0.25, 96% at sigma=0.10,
with 100% of nominations on the neighbourhood boundary and regret roughly tripled. The
prediction registered before the run -- that local signal-to-noise was the cause and the
saddle rate would fall at low noise -- was **refuted**. The recorded alternative holds:
adaptively clustered points cannot support a second-order fit at any noise level.

But Q66's comparator arm found the one win a zero-well readout change can deliver, and
Q67 powered it to n=100 (extended ensemble, committed 25 verified as an exact prefix,
DoE gated bit-exact on the 50 overlapping rows).

**d = 6, sigma = 0.10. Positive = BO better.**

| Rule | n | DoE | BO | Contrast | Wilcoxon | TOST |
|---|---:|---:|---:|---|---:|---|
| posterior mean | 25 | 0.0892 | 0.0711 | +0.0181 [+0.0073, +0.0292] | 0.0074 | different |
| posterior mean | **100** | 0.0904 | **0.0758** | **+0.0146 [+0.0084, +0.0210]** | **<0.0001** | equivalent |
| measured argmax | 25 | 0.0892 | 0.0872 | +0.0020 [−0.0105, +0.0159] | 0.7310 | equivalent |
| measured argmax | **100** | 0.0904 | 0.0823 | +0.0081 [+0.0007, +0.0150] | 0.0172 | equivalent |

**How to state this, and how not to.** At n=100 the contrast is BOTH significantly
non-zero AND equivalent within the 0.02 SESOI. Those are not in conflict -- detecting
exactly that case is what TOST is for. The defensible sentence is:

> At low noise, BO with posterior-mean selection is **reliably** better than
> matched-budget RSM, by an amount **smaller than the smallest effect this study declared
> interesting.**

Quoting p < 0.0001 alone overclaims it. Quoting the TOST alone hides that it is real.
Note also that the effect shrank from +0.0181 to +0.0146 under quadrupled n -- the
regression toward the mean expected of an n=25 estimate sitting above its own MDE.

`posterior_mean_at_visited` is an existing Q58 locator, not a rule invented to produce
this result; it was run as a comparator for Q66. BO wins on both components at this cell
(search 0.0443 vs 0.0510, identification 0.0296 vs 0.0361), so it is not a scoring
technicality. At sigma=0.25 the same rule does nothing at all (0.1553 vs 0.1552), which
is what the miscalibrated GP (coverage 0.764) predicts -- a rule that won everywhere
would be the suspicious outcome.

---

## 7. What would count as new evidence

Free interventions only, per section 6. Each must be registered before running, and each must be
paired with a matched classical upgrade or it is void under the project's fairness rule.

- ~~**B3 — local quadratic readout.**~~ **CLOSED, negative (Q66).** Saddles at 94-96%,
  boundary nominations at 100%, both noise levels. Do not revisit.
- **B4 — repair GP calibration.** Nominal 95% latent coverage is as low as 76.4%. Zero wells.
- **B2 — knowledge gradient.** Optimises the value of the final recommendation rather than the best
  observation, which is the actual estimand. Present in BoTorch 0.18.1, absent from `optimizers.py`.

Design and fairness constraints: `docs/superpowers/specs/2026-08-20-bo-steelman-design.md`.

**Power warning.** At n = 25 the MDE is about 0.027, larger than the 0.02 SESOI. Any of these run at
n = 25 will most likely return "inconclusive." The extended ensemble now exists (Q67, Q68) and the
committed 25 are a verified exact prefix, so future probes should use it rather than re-litigate n.

---

## 8. The one-line summary

BO wins decisively when the landscape is multimodal, wins on reaching tight targets at low noise,
and ties under the fair in-region readout. It loses under the single-noisy-readout rule at high
noise on smooth near-additive surfaces, and that loss is an identification failure that cannot be
bought off with budget. **Which arm "wins" is a function of landscape shape, noise level, and
terminal rule — which is the paper's thesis, now supported from both directions.**
