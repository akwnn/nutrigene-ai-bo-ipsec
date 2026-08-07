# 01 — The curve fitter

**File:** `src/boec/rsm.py` · **Status: ✅ built, 33 tests passing** (15 second-order + 18 stepwise third-order)

---

## The problem it solves

This is the **rival** in the comparison — the classical statistics approach the
machine-learning model is being measured against.

It has to be good. The entire finding rests on comparing against a competently
fitted classical model, not a straw man. If someone can say "well, you did the
statistics badly," the result is worthless.

## What it does

Three things.

**Fits a curve through the data.** Not a straight line — a curve that can bend,
including bending differently in different ingredients and allowing for
ingredients affecting each other. In six ingredients that works out to 28
separate numbers being estimated from 48 measurements.

**Reports an error bar.** For any recipe you name, it says "I predict this
result, give or take *that much*." This error bar is the thing being compared
against the machine-learning model's uncertainty — it's the whole point of the
file.

**Finds where the curve turns over, and says what kind of turn it is.** A peak?
A valley? A saddle (up one way, down another)? Or a ridge — a whole flat line of
equally-good points rather than a single best one?

## The two decisions in here that a reviewer would attack

**Why not fit a more flexible curve?** A more flexible model — one that can bend
twice instead of once — needs 84 numbers estimated from 48 measurements. That's
not a hard problem, it's an impossible one: there isn't enough information in
48 measurements to pin down 84 things. The error bar doesn't just get big, it
stops existing mathematically.

A reduced version of that flexible model *is* fitted, but only ever described,
never given an error bar. Here's why that matters:

> If you let the data choose which terms to keep and then compute an error bar
> from the same data, **the error bar comes out too narrow** — because the
> model was already tuned to fit that data. And "the classical error bar is too
> narrow" is exactly the finding this project is trying to establish. Reporting
> a number that's too narrow *for a completely different reason* would sabotage
> the result. So it's left out entirely.

**Why fail loudly instead of coping?** If the measurements don't contain enough
information to fit the curve, the code stops with an error rather than falling
back to an approximation. An approximation here would produce an error bar that
looks fine and means something different — the exact silent-wrongness failure
this project keeps guarding against.

## Something the tests caught

While being built, the code mislabelled the **ridge** case — the flat-line
situation — as an ordinary peak or valley. That's not an obscure edge case: it's
the case most likely to come up at the low end of the experiment's range. A test
written from the specification caught it before it could pollute any results.
