# 07 — The comparison

**Files:** `src/boec/discrimination.py`, plus `configs/experiment/e4.yaml`
**Status: ✅ machinery built, 27 tests passing. The two key numbers were locked first.**

---

## This is the actual result

Everything else is machinery. **This is the measurement the paper reports.**

## The question, stated precisely

Not "is the machine-learning model more accurate?" — that's a different and less
interesting question.

The question is: **when the classical model is about to be badly wrong, does the
machine-learning model's uncertainty warn you?**

So for a large set of candidate recipes, you compute two things:

- how wrong the classical model actually is there, and
- how nervous each method claims to be there,

and ask whether the nervousness tracks the wrongness.

## What gets compared — three "nervousness" scores

| Score | What it is |
|---|---|
| The machine-learning model's uncertainty | **The claim being tested** |
| The classical model's error bar | **The rival** |
| Distance to the nearest measurement you actually have | **The honesty check** |

## Why that third one exists, and why it might sink the whole result

"The model is unsure far from data" is close to a tautology. It's *built* to be
unsure far from data.

So the result only means something if the model's warnings are **selective** —
if they're doing something smarter than measuring distance.

> **If plain distance-to-nearest-measurement predicts the errors just as well,
> then the finding is that the fancy model is an expensive distance function.**

That is the first objection any reviewer reaches for. Building the objection
into the experiment as a third competitor, up front, is much stronger than
having it raised afterwards.

## The check that runs before the result

Before reporting anything, the three scores get compared **to each other**.

If all three turn out to be measuring essentially the same thing — which is
plausible, given the geometry of the setup — then there is no room for the
comparison to show anything either way, in any direction.

**That gets reported first, before the finding.** A reader needs to know there
was room for the answer to come out differently before being told how it came
out. Discovering afterwards that there was never any headroom would be fatal;
saying so up front is just an honest description of the design.

## The two numbers locked in advance ✅

Written down, dated, and committed **before any result existed** —
`configs/experiment/e4.yaml`:

- **512 candidate recipes per instance.** Early timing work showed computation
  is roughly ten times cheaper than assumed, so there was no reason to skimp.
- **The "badly wrong" threshold: the worst 20% within each instance**, rather
  than a fixed number. Different instances operate at different scales, so any
  fixed value would mean something different on each one.

**Why lock them early.** Both are choices that could be tuned after seeing
results to make the finding look better. Fixing them in advance, in a dated
record, means "you picked the threshold that flattered your result" is simply
not available as an objection.

The main reported measure doesn't need a threshold at all — the threshold only
affects a secondary figure.

## What could go wrong, and the honest response

- **The mechanism doesn't exist** — A's first check comes back showing models
  don't over-promise here at all. Then this experiment has nothing to measure,
  and the response is a joint decision with A, not a week of quiet tinkering.
- **No headroom** — the three scores all measure the same thing. Reported as a
  genuine finding about the design, not buried.
