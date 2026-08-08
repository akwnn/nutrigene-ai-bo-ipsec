# NEGATIVE RESULT — giving the model the biology's shape makes it worse

**Person B, 2026-08-08.** Tried, measured, rejected. Recorded so nobody tries it
again expecting a different answer.

Reproduce: `results/e4-shape-mean-negative.log`.

## The idea

Far from anything measured, a standard GP falls back to a flat guess. That is
honest but useless — it's exactly where a prediction is needed, and flat is the
one thing the biology certainly is not.

So: have it fall back on the *shape* instead. Every ingredient helps, plateaus,
then hurts. Fit that shape from the data and let the model settle onto it far
away, rather than onto nothing.

## The safety mechanism, which did not save it

The shape might be wrong, and a confidently wrong fallback is worse than a flat
one. So the shape was multiplied by a weight the model learns for itself. If the
shape were unhelpful, that weight would shrink toward zero and leave exactly the
model we already had — **the downside was supposed to be bounded by
construction.**

## The result

15 landscapes, over-promise at each model's claimed best recipe (lower is better):

| | over-promise |
|---|---|
| plain GP — flat fallback | **+0.302** |
| GP + biphasic fallback | +0.563 |
| practitioner form alone | +0.606 |

**Shaped minus plain: +0.26 [+0.15, +0.37], significant. It is nearly twice as
bad.**

## Why the safety mechanism failed — the part worth remembering

**The learned weight never shrank.** Across every landscape it sat around 5.3,
never near zero. The model never rejected the shape.

It could not have. **The weight is chosen to explain the training data, and on
the training data the shape genuinely is helpful** — the measurements sit on the
rising arm, which the shape fits well. The harm only appears far away, in
territory the fitting procedure never sees.

So the thing the safety mechanism was meant to protect against is **structurally
invisible to the procedure that sets it.** That is not a tuning problem; a
bounded-downside argument that relies on a quantity fitted in-sample cannot
protect an out-of-sample failure.

## And the ceiling was predicted in advance

Research flagged this before the run: the shape has **no ingredient
interactions**, while the real landscapes do. Far from data the model reverts to
its fallback exactly, so its error there is floored near the fallback's own
error. Predicted ceiling ≈ the parametric model's +0.54. Measured **+0.563**,
against the parametric's +0.606.

The prediction was right, the mechanism was right, and the safety valve did not
work for a reason worth writing down.

## What this rules out, and what it does not

**Ruled out:** improving extrapolation by handing the model a fitted global
shape. Anything whose fallback is fitted in-sample inherits this failure.

**Also ruled out without needing a run** — the same logic, plus evidence already
in hand: a linear or quadratic fallback would be worse still. The training data
sits on the convex rising arm, so a quadratic fitted to it curves *upward* and
keeps climbing past the true peak. Our own polynomial numbers (+1.10, +1.18)
already are that experiment.

**Not ruled out:** constraining the shape *in the extrapolation region itself*
rather than fitting it in-sample — shape-constrained GPs with virtual derivative
observations. That is the one approach whose mechanism does not depend on
in-sample fitting. It is also weeks of work, has no support in our libraries,
and would break the calibration machinery. Future work, honestly labelled.

**The thing that did work is elsewhere:** cross-model disagreement, which needs
no shape assumption at all. See `EXPLORATORY-disagreement.md`.
