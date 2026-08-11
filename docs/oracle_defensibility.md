# Oracle defensibility audit

Every parameter range in the Phase 1 oracle was chosen by us. This document answers
"why that number?" for each, and labels the ones that cannot be defended beyond *it made
the experiments work*.

The purpose is not to change the oracle. It is to know which choices rest on evidence
and which rest on convenience, so the limitations section is written by us rather than
by a reviewer.

**Evidence base.** Figures 1a and 2a of Hall, Lin & Ogle 2025 (*Sci Rep* 15:24479) were
digitized for this audit — see `scripts/digitize_hall_ogle.py`,
`data/external/hall_ogle_2025/` and the analysis-ready CSVs at `data/published/`.
Extraction recovers 23 stage-1 conditions (22 non-centre + 1 centre) and 25 stage-2
conditions (16 factorial + 8 axial + 1 centre).

**Correction — the previous version of this paragraph claimed those counts showed the
extraction "matches the published design structure exactly, which is the check that the
extraction is reading the right objects". That claim was false, and the check it
described could not have supported it.** The check counted design ROW TYPES only. It
never verified that the 16 stage-2 corners were *distinct*, and never verified that a
response had been recovered at all. The shipped extraction failed both: corner
`(-1,+1,+1,-1)` appeared twice while `(-1,+1,+1,+1)` was absent, and stage-2 row 2's
quartiles were `NaN`. Row-type counts of 16/8/1 were returned in spite of this, so the
sentence quoted a passing check as evidence of a property the check did not test.

What is verified now, as hard gates in `boec.published` that halt extraction
(`tests/test_published.py`, 31 tests): corner distinctness and completeness, no missing
responses, quartile ordering, axial points at ±1, exactly one centre point, model-matrix
rank, and cell-by-cell agreement with the published coded tables. The regression tests
run against `tests/fixtures/prefix_*.json` — the pre-fix extraction, kept verbatim —
and are required to fail on it.

**A limitation of structural checking, stated because it bit us.** Stage 1's 22
non-centre runs are a D-optimal subset of a 2⁶ space, so flipping a single level yields
another perfectly valid saturated design. Counts, distinctness, rank and axial structure
*all still pass*. Only comparison against the published table detects it — which is how
the stage-1 discrepancy below was found, after the structural suite passed cleanly.

**Two design cells differ between our figure-strip reading and the third-party
transcription, and they split — one error each.** Both are settled by
`docs/pdf_crosscheck.md:126-127`, a four-reader read of the source PDF.

| stage | cell | our strip | transcription | the paper prints | who is wrong |
|---|---|---|---|---|---|
| 2 | col 20, FN | `-1` | `+1` | `- + + +` (Table 2 row 21) | **our strip** — corrected to `+1` |
| 1 | col 22, LN511 | `+1` | `-1` | `+ + + + + -` (Table 1 row 23) | **the transcription** — our value stands |

**A correction that was nearly made and would have been wrong.** An earlier pass here
reasoned that the table is the design of record, inferred that Table 1 row 23 could not
contain `+ + + + + -`, and prepared to overwrite the stage-1 cell to `-1`. The paper
prints exactly that row. Only the PDF settles it — no structural check can, because a
22-run D-optimal subset of a 2⁶ space stays valid under a single flip (rank 22 either
way). *"Prefer the table"* and *"prefer the figure"* are both wrong as rules; each source
has one isolated bad cell.

Column ordering is not in doubt: every other cell agrees (137/138 stage 1, 99/100
stage 2), so box *i* pairs with table row *i* throughout. The canonical CSVs carry the
strip reading with its one corrected cell; the JSON keeps the raw strip, so the
disagreement stays inspectable rather than being overwritten.

**One correction to the project record.** The documents describe Figures 1a and 2a as
"per-condition bar charts". They are **box-and-whisker plots with individual points
overlaid**. This matters: they show dispersion, and dispersion is reported nowhere else
in the paper. Section 2.2 below is source-derived because of it.

**The limit, stated in advance.** 48 conditions from one study, published as figures,
with no reported variance. A six-dimensional surface cannot be validated against that.
The defensible claim is *"shaped like published dose-response behaviour, with stated
parameter ranges and a factor-activity structure matched to the published screen"* —
not *"matches real hiPSC data."*

---

### Parameter: `x*` — peak position

**Value / range:** `U(0.25, 0.55)`; realized mean **0.340** after acceptance truncation.

**Justification:** Chosen so the decline from peak to the upper box edge exceeds
measurement noise. At `x* = 0.8` the deepest achievable decline over the full stated
`(n, r)` ranges is **8.2%** — under one sigma at the primary noise level — and a 30%
decline is unreachable at any `n` for `r ∈ [2,8]`. High peak position and measurable
depth are not jointly achievable.

The single anchor available in the data points the **other way**. LN411 is the only
stage-2 factor with a resolvable interior peak; its fitted vertex sits at coded +0.37,
i.e. **0.685 in [0,1] units — above our entire sampled range**. That is n=1 and it does
not support the choice.

**Evidence class:** **design constraint** (and the one available anchor contradicts it).

**Limitation to state in the paper:** "Peak positions were constrained to the
lower-middle of each factor's range so that the decline to the boundary exceeds
measurement noise. This is a requirement of the benchmark, not a claim about biology.
The one interior peak resolvable in the source data (laminin-411, coded 0.685) lies
above the sampled range."

---

### Parameter: biphasic form — every factor rises, peaks, declines

**Value / range:** all `d` factors biphasic with an interior optimum.

**Justification:** The Hill and four-parameter-logistic forms are standard pharmacology
and are grounded. The *universality* of the interior peak is not.

Fitting a second-order model to the digitized stage-2 medians (n=24 of 25, 15 terms,
9 residual df, σ̂ = 0.671):

| protein | linear | quadratic | vertex (coded) | shape | p(quad) |
|---|---|---|---|---|---|
| C | −0.171 ± 0.175 | −0.293 ± 0.421 | −0.29 | unresolved | 0.50 |
| CIV | −0.109 ± 0.180 | +0.425 ± 0.421 | +0.13 | unresolved | 0.34 |
| **LN411** | +0.716 ± 0.180 | **−0.968 ± 0.421** | **+0.37** | **interior peak** | **0.05** |
| FN | −0.402 ± 0.178 | −0.033 ± 0.421 | −6.18 | monotone decreasing | 0.94 |

**1 of 4 interior. The oracle assumes 6 of 6.**

This agrees with the independent prior from TheO's coded position and sharpens it. FN at
the lower bound ↔ monotone decreasing: consistent. LN411 interior in both: consistent.
And C being *unresolved* explains why TheO placed it at +0.003 — a factor with no
resolvable effect is one a constrained profiler never moves off its midpoint
initialisation. That **strengthens** the argument that TheO came from a constrained
optimiser rather than an unconstrained stationary point.

**But this is low power, not evidence of absence.** The SE on a quadratic coefficient is
0.421, so curvature is only resolvable at p<0.05 if |Q| > 0.95 — a large effect against
medians spanning 0.4–4.2. An oracle factor with `w = 0.225` and `δ = 0.5` moves the
response by 0.113 of the normalised range, **far below what this design could have
detected**. The published experiment could not have resolved our oracle's curvature even
if it were present.

**Partly addressed by v8.** An inert factor carries `w ≈ 0.025–0.05`, so pushing it to a
bound costs almost nothing and it behaves much like the flat C and CIV marginals — and
closer to fibronectin's boundary behaviour than a fully active biphasic factor would.
The active/inert split moved in the right direction. It did not go as far as the data
suggests: v8 is 4 active of 6 (67%), while stage 1 already screened 6→4 and stage 2
resolves 1–2 of those 4.

**Evidence class:** **literature-analogy** for the functional form; **design constraint**
for its universality.

**Limitation to state in the paper:** "The oracle assumes every factor is biphasic with
an interior optimum. In the source study only one of four stage-2 proteins shows
resolvable interior curvature, one is monotone within range, and two are unresolved —
though that design could not have detected curvature of the magnitude the oracle uses.
The interior optima that make the sample-efficiency experiment meaningful are partly a
property of our construction."

---

### Parameter: `σ_rel` — relative observation noise

**Value / range:** **0.25 primary**, 0.10 as the optimistic bound. `σ_add = 0.01`.

**Justification:** Now **source-derived**, not literature-analogy. Figure 2a shows boxes,
whiskers and individual points. Backing a CV out of the interquartile range
(`CV ≈ IQR / 1.35 / median`) across 24 of 25 conditions:

| statistic | implied CV |
|---|---|
| median | **68.2 %** |
| interquartile range | 55.8 % – 86.1 % |
| full range | 27.3 % – 194.1 % |

**Our 0.25 is roughly 2.7× *lower* than the source-derived value.** The choice is
conservative, not aggressive — the published assay is noisier than our worst case.
Supporting context: Hall/Ogle normalise every plate to a fibronectin control precisely
because interexperimental variability is large, and report **no CV for CD31 anywhere**;
flow-cytometry reproducibility literature and the CLSI H62 tiers place real assay CV well
above 10%.

Caveats on the 68% figure: `IQR/1.35` assumes approximate normality and the readout is a
right-skewed ratio, which inflates it; the spread is across ≥4 wells from ≥3 experiments,
so it includes plate and experiment variation, not assay noise alone; and with ~6 points
per condition the sample IQR is itself noisy.

**Evidence class:** **published** (source-derived, with stated caveats).

**Limitation to state in the paper:** "No coefficient of variation is reported in the
source study. We estimated one from the interquartile ranges in Figure 2a (median 68%
across 24 conditions) and set the primary noise level to 25%, which is conservative
relative to that estimate."

---

### Parameter: `n_active = 4`, `active_share = 0.90`

**Value / range:** 4 dominant factors at both d=6 and d=8; actives carry 90% of the
weight, giving an influence ratio of 4.5× (d=6) and 9.0× (d=8).

**Justification — the 6→4 structure is published and strong.** Hall/Ogle screened six
proteins to four after stage 1, and their own optimum sits at **zero** for both dropped
proteins, laminin-111 and laminin-511, meaning those factors are inert and the optimum
lies on a boundary in those coordinates. That structure is not invented.

**`share = 0.90` is not supported by anything we can extract.** Fitting main effects to
the digitized stage-1 medians (23 conditions, 16 residual df, σ̂ = 0.272):

| protein | main effect | SE | \|t\| | status in the screen |
|---|---|---|---|---|
| C | +0.067 | 0.059 | 1.14 | retained (doubled) |
| CIV | −0.053 | 0.059 | 0.90 | retained (doubled) |
| LN411 | +0.069 | 0.059 | 1.17 | retained (doubled) |
| FN | +0.002 | 0.059 | 0.04 | retained |
| LN111 | −0.036 | 0.059 | 0.61 | dropped |
| LN511 | −0.066 | 0.059 | 1.13 | dropped |

Mean |effect| retained 0.048 vs dropped 0.051 — an observed ratio of **0.94 : 1** against
the **4.5 : 1** the oracle implies. No main effect is significant.

**This analysis cannot reproduce their retention decision, and that limits how far it can
be pushed.** Their stage 1 is exactly saturated for the two-factor-interaction model:
**22 non-centre runs against 1+6+15 = 22 parameters, so zero residual df from those runs**
(verified — model matrix rank 22 of 22, `test_stage1_saturates_the_two_factor_model`).

*Be exact about which figure is meant, because both appear in the literature and only one
is ours to claim.* The **full 23-run design leaves exactly one residual df**, not zero,
because the centre point is a 23rd run that the 22-parameter model does not consume. The
"zero" above describes the non-centre block. One df does not change the argument — a
single degree of freedom cannot support tests on 22 parameters, and a lack-of-fit test on
it would have essentially no power — but the paper criticism must say **1, not 0**, if it
is stated over the whole design. Both numbers are asserted in the test suite so neither
can drift.

Significance therefore came from replicate-level degrees of freedom — ≥4 wells across ≥3
experiments — not from the design. We have 23 condition medians and no replicate-level data, so we fitted main
effects only and forced all interaction structure into the residual. A null result is the
expected outcome of that analysis, not a refutation. One genuine discrepancy: CIV comes
out negative here while the paper reports a positive significant association.

**`n_active = 4` at both dimensions is a deliberate confound-avoidance choice.** Holding
the active subspace fixed makes the d=6 vs d=8 comparison measure the cost of **nuisance
dimensions** — the real-world question, since you do not know in advance which factors
matter. Scaling actives with `d` would confound dimension with active-count.

**Evidence class:** **published** for 6→4; **arbitrary** for `share = 0.90`; **design
constraint** for `n_active = 4` at both dimensions.

**Limitation to state in the paper:** "The active/inert split follows the published
screen, which carried four of six proteins into the response-surface stage. The 9:1
weight ratio between active and inert factors is our choice; a main-effects analysis of
the digitized stage-1 data does not distinguish retained from dropped proteins, though
that analysis cannot reproduce the two-factor-interaction model and replicate-level error
term on which the original retention decision was based."

---

### Parameter: `γ ~ U(−1, 1)` — cross-modulation strength

**Value / range:** one factor shifts another's effective peak position by
`m_i = exp((1/k) Σ_j γ_ij (f̃_j − ½))`, giving a peak shift of **±18%** of `x*` per pair.

**Justification — the mechanism is documented.** Fibronectin activates TGFβ signalling,
which inhibits endothelial specification; a TGFβ inhibitor rescued differentiation on
TheO and adding TGFβ suppressed it on EO. That is precisely one factor changing whether
others work, and it is why the previous additive-product interaction form was inadequate
— that form provably cannot move the optimum at all.

**The magnitude is not supported, and is conservative.** Swinging the strongest
modulating factor across its range changes the response by a median of **0.218** against a
response range of ~1.0. Removing fibronectin moved Hall/Ogle across essentially the full
range. The oracle's interaction is therefore about **4.6× weaker than the one documented
effect**, which makes BO's task easier than reality and the efficiency claim conservative.

**Evidence class:** **published** for the mechanism; **arbitrary** for the magnitude
(conservative in a known direction).

**Limitation to state in the paper:** "Cross-modulation strength was chosen, not
estimated. Its effect on the response is roughly a fifth of the one interaction effect
documented in the source study, so the benchmark understates real interaction strength
and the resulting efficiency comparison is conservative."

---

### Parameter: `δ` and the acceptance floor

**Value / range:** `δ ∈ [floor/w_i, 0.9·δ_max]` per active factor; formula pre-floor
**0.120**; acceptance on numerically computed true depth **≥ 0.1083**.

**Justification:** 0.1083 is `3σ_rel/√n_budget` at the primary noise level
(σ_rel = 0.25, n = 48) — three pooled standard errors, so the planted optimum is
distinguishable from the best boundary point by the pooled precision the budget affords.
The pre-floor of 0.120 is inflated above it to absorb the ~6% depth cost of peak
modulation; it was tuned so acceptance stays high (73.5% at d=6, 83.3% at d=8) rather
than reverting to rejection sampling. The floor is **frozen and noise-independent** so one
ensemble serves both noise levels — that is what makes the 0.10-vs-0.25 contrast a noise
effect rather than an ensemble effect.

**Evidence class:** **design constraint** (derived from the budget and noise level, not
from biology).

**Limitation to state in the paper:** "Instances were accepted only if the planted
optimum exceeded the best boundary point by three pooled standard errors. This selects a
subset of the nominal parameter distribution; both nominal and realised marginals are
reported."

---

### Parameter: `n ~ U(1, 3)`, `r ∈ [2, 8]`

**Value / range:** Hill exponent `U(1,3)`; window ratio `r = IC50/EC50` derived by
inversion and clipped to `[2, 8]`.

**Justification:** Hill coefficients of 1–3 span the ordinary pharmacological range
(1 = non-cooperative, 2–3 = moderately cooperative). The `r` bounds are ours: `r ≥ 2`
keeps the activating and inhibitory arms separable, `r ≤ 8` prevents an implausibly wide
plateau. Note `δ` is strictly decreasing in `r`, so `δ_max` is always attained at
`r = 2` and the "scan over `r`" the spec described is a closed form.

**Evidence class:** **literature-analogy** for `n`; **arbitrary** for the `r` bounds.

**Limitation to state in the paper:** "Hill exponents were drawn from the conventional
1–3 range. The ratio between inhibitory and activating half-maxima was bounded to [2, 8];
these bounds are ours and are not estimated from data."

---

### Parameter: the declared truncation

**Value / range:** acceptance reshapes the ensemble — `x*` mean **0.340** against 0.400
nominal, `n` mean **2.32** against 2.00 nominal (d=6, v8 ensemble).

**Justification:** Any acceptance rule truncates the stated draws. The rule here demands
depth from every active factor, which favours low `x*` and high `n`. This is recorded in
the per-dimension audit JSON alongside every generated ensemble.

**Confirmed:** the methods must report this as the **sampled-and-accepted** ensemble with
both nominal and realised marginals, never as the nominal draw.

**Evidence class:** **design constraint**, declared.

**Limitation to state in the paper:** "Reported parameter ranges are the nominal draw;
the accepted ensemble is truncated toward lower peak positions and higher Hill exponents.
Both marginals are given."

---

## Report

### Parameters defensible only as "it made the experiments work"

1. **`x*` peak position range** — the weakest link. Purely an experimental-design
   constraint, and the single available anchor (LN411 at 0.685) lies above the range.
2. **`active_share = 0.90`** — the 6→4 structure is published; the 9:1 magnitude is not,
   and the digitized stage-1 main effects give ~1:1.
3. **`γ` magnitude** — mechanism published, magnitude invented (conservative by ~4.6×).
4. **`r ∈ [2, 8]`** — plausible, unsourced, and not load-bearing.

### Where the data contradicts rather than merely fails to support

Only one candidate: **`active_share = 0.90`**. Observed 0.94:1 against an implied 4.5:1
is a large gap, not an absence. It is downgraded from a contradiction because the
analysis that produced it cannot reproduce the published model — main effects on 23
condition medians versus a saturated two-factor-interaction model with replicate-level
error. Treat it as a flagged discrepancy with a stated caveat.

Everything else in this audit is **absence of support**, and section 2.1's power
calculation shows why: the published design could not have resolved curvature of the
magnitude our oracle uses, so failing to see it there says little.

### Should anything change the v8 oracle before Phase B?

**No. All of it is limitations-section material.**

The stated bar for another oracle revision is a contradiction, not an absence of support,
and nothing here clears it. The one contradiction-grade signal (`share = 0.90`) rests on
an analysis that is underpowered by construction. Against that, another revision would
invalidate cached optima for the fourth time and move the E4 endpoint again — the E4
primary has already shifted twice, from κ-only to κ=0.6/ρ=2.0 to κ=0.6/ρ=3.0, because
each oracle change alters σ̂ and therefore the interval widths E4 measures.

Two things worth carrying forward without changing the oracle:

- **E4b construction** should use the measured fibronectin behaviour — linear −0.402 with
  no resolvable curvature — rather than an invented boundary case. That is a change to an
  experiment, not to the instance family.
- **A `share` sensitivity run** at 0.75 and 0.95 would cost one regeneration and would
  convert the weakest justification into a reported robustness range. Cheaper than
  defending 0.90 in review.

### No further realism work in Phase 1 after this.
