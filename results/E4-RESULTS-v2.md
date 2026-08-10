# EXPERIMENT 4 — RESULTS, pre-registration v2

**Person B, 2026-08-08.** Supersedes `E4-FIRST-RESULTS.md`, which reported the
regime this version deprecates. 25 landscapes × 4 κ, both regimes.

Reproduce: `python scripts/run_e4.py` (primary) and
`python scripts/run_e4_robustness.py` (the three checks below).

---

## The finding

**The traditional method over-promises badly, and a Gaussian process does not
warn you about it any better than plain distance does.**

The second half is the surprising part, and it survived every check we could
think to run against it.

---

## The headline, and why the regime decides it

| | GP minus plain distance | verdict |
|---|---|---|
| **rho = 2.0** — pre-registered primary | **−0.027** [−0.073, +0.018] | no advantage |
| unit cube — limiting case | **+0.055** [+0.017, +0.089] | significant |

**The GP's apparent advantage exists only in the regime nobody would defend.**

The unit cube asks every model about territory 2–4× beyond anything it
measured, in six ingredients at once; the study motivating this project
extrapolated 1.2×, in one. Person A raised that objection on geometric grounds
**before any of these numbers existed**. Moving to the defensible regime
reverses the headline.

Had we simply run the indefensible regime with more landscapes, we would have
published a significant effect that is an artefact of the question being asked.

### The regimes really do differ — tested, not inferred

Saying "significant here, not there" does **not** establish that two things
differ; one can sit just inside a threshold and the other just outside while
being statistically indistinguishable. So we tested the difference between the
differences directly, paired landscape by landscape:

| aggregation | cube minus rho=2.0 | regimes differ |
|---|---|---|
| raw | +0.0817 [+0.0454, +0.1171] | **yes** |
| Fisher-z | +0.1024 [+0.0657, +0.1394] | **yes** |

## The null is a claim, not a shrug

> **The GP's advantage is below 0.08 — upper limit +0.011.**

Not "we failed to find an effect" but "any advantage is too small to be worth
having, and here is the bound." The bound was pre-registered before the run.

| check | raw | Fisher-z |
|---|---|---|
| mean difference | −0.0269 | −0.0172 |
| sign-flip p | 0.861 | 0.745 |
| upper limit | +0.0113 | +0.0231 |
| below the 0.08 bound | yes | yes |

**Robust to how correlations are averaged.** Both aggregations agree in sign
and differ by 0.0097 against a bound of 0.08. Correlations are not on an
additive scale, so this needed checking rather than assuming.

*Both p-values are sampled, not exact — 25 landscapes gives 33 million sign
arrangements. Monte Carlo error under 0.001. An earlier version of this
analysis reported such numbers as exact; it no longer can.*

## The mechanism, in the defensible regime

| κ | over-promise | interval width | headroom |
|---|---|---|---|
| 0.6 | +1.290 | 1.084 | 0.872 |
| 0.7 | +1.184 | 1.274 | 0.872 |
| 0.8 | +1.019 | 1.435 | 0.872 |
| 0.9 | +0.872 | 1.543 | 0.872 |

Pooled over-promise **+1.103** [+1.024, +1.182], against a response whose
maximum is 1.0 — the fitted surface promises more than the best achievable
result, everywhere, at every setting.

**And the interval is now the same order as the response** (≈1.1–1.5 rather than
the ≈7–12 of the unit cube), which is what makes the comparison fair. In the
extreme regime an interval seven times the response range covers almost
anything, so "its interval is too narrow" was never available as a finding.

100/100 cells valid — the true optimum was outside the training corner every
time. Headroom 0.87 everywhere, under the 0.95 kill threshold, so the null is
not an artefact of the three scorers being the same quantity in disguise. No
fit failures.

## Every surface was a saddle

40/40 in version 1, 100/100 here. No maxima, no minima. The specification
predicted a mix and specifically warned that tight settings would produce
*minima*. It was wrong, cleanly, and this is exactly why the spec required the
distribution rather than a bare rate.

## How to frame this in the paper

**Do not claim discovery.** A prior-art search found the mechanism is already
established:

- GP posterior variance equals the RKHS power function — it depends on the
  kernel and the design geometry, **not on the observed values** (Kanagawa et
  al., arXiv:1807.02582). That is the formal version of "GP variance is a
  distance function."
- "Simple distance rivals sophisticated uncertainty" is a known genre result
  (Sun et al., ICML 2022, k-NN beating Mahalanobis for OOD detection; the
  distance-awareness line behind SNGP, NeurIPS 2020).
- TuRBO-ENN (arXiv:2506.12818, 2025) replaces the GP surrogate with an explicit
  squared-distance term and matches GP-based performance.

**Cite these as why the null was the expected outcome under GP theory**, rather
than presenting it as a surprise and having a reviewer supply the citations.

What is defensible as new: a pre-registered, paired, adequately powered test of
this equivalence in the response-surface / DoE extrapolation setting relevant to
saturating dose-response biology, against both a model-free null and the
polynomial's own interval, with the anisotropy question tested rather than
assumed — plus the tool. That is precisely the fallback the project plan
specified.

## Limitations, stated plainly

- **25 landscapes, not the 40 first pre-registered.** A's committed ensemble
  holds 25. That is 2.5× the pilot — the 80% power tier — and the amendment was
  recorded before the run, for a reason independent of any result. Extending to
  40 needs A.
- **Two-sided equivalence holds, but with thin margin.** *Corrected 2026-08-10 —
  this bullet previously read "the lower limit does not clear −0.08, so a
  meaningful disadvantage is not excluded either", which contradicts this
  document's own log.* `equivalence_bound_test` printed the **`Established, not
  merely unrefuted`** verdict, and that branch is only reachable when
  `lower >= -bound` (`discrimination.py`); the "not equivalence" wording belongs
  to the other branch, which did not fire. Recomputed from
  `results/e4-robustness.json`: one-sided limits **−0.0658 / +0.0112**,
  two-sided **[−0.0737, +0.0187]**, both inside ±0.08. So the *disadvantage*
  direction is excluded too, and the result is stronger than was claimed here.

  The honest caveat is a different one. This is **not** bootstrap-seed noise —
  across seeds 0/1/7 the lower limit moves by only ~0.0006. It is that the
  **two-sided margin to the bound is ~0.006**, so equivalence in that direction
  is established but not comfortably. The one-sided margin, which is what the
  registered test uses, is ~0.014.
- **One oracle family.** Whether this holds on landscapes with different
  structure is untested.
- **d=6 only**, per spec.
