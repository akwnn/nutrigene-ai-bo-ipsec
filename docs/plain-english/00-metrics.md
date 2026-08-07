# 00 — The measuring tape

**File:** `src/boec/metrics.py` · **Status: ✅ built, 10 tests passing**

---

## The problem it solves

Every model in this project makes the same kind of claim: *"the best recipe is
over here, and it will score this well."*

You need one number that says how wrong that claim was. Not "was the model
accurate on average" — specifically **did it promise more than reality
delivered, at the exact point it told you to go to.**

## What it does

Three steps, and it's genuinely this simple:

1. **Ask the model where the best point is.** Search the whole allowed range,
   not just the part that was measured. This is the point the model would
   actually send you to.
2. **Go and look.** Ask the simulator what the true value is at that point.
3. **Subtract.** Predicted minus actual.

A positive number means the model over-promised. That gap is the headline
result of the whole experiment.

## Why it's one function and not two

Person A and Person B both need this number, from opposite directions — A from
the classical-design side, B from the model side.

**If each wrote their own version, they would get two numbers that disagree, and
no way to tell which one was right.** One shared function turns that into a
genuine cross-check instead of an argument. The file says so at the top, in
capitals, because it is the kind of thing that quietly gets reimplemented.

## Why "where the model thinks the best point is" and not something simpler

There's an obvious alternative: fit a curve, find where it turns over, check
whether that turning point escaped the region you measured.

**That doesn't work here, and the reason is worth understanding.** In the region
being tested, the true response is still rising and curves *upward*. A fitted
curve through that data often turns over at a **minimum**, not a maximum. So
"did the turning point escape?" would be answering a question about the wrong
kind of turning point, some of the time, silently.

Asking "where does the model say the best point is, within the allowed range?"
is always a meaningful question, whatever shape the fitted curve came out. So
that's what gets measured.

The turning-point information is still recorded — but reported as a description
of what happened, not as the result.

## How we know it works

The number has to be identical whoever runs it and whenever, or the whole
shared-function argument collapses. So the tests check it is fully deterministic
— same inputs, same answer, every time — alongside checks that it recovers
known answers on cases where the right answer was worked out by hand.
