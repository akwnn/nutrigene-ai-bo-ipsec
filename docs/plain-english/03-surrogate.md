# 03 — The model builder

**File:** `src/boec/surrogate.py` · **Status: ✅ built, 24 tests passing**

---

## The problem it solves

This builds the machine-learning model at the centre of the project — a
**Gaussian process**.

The one-sentence version: it draws a smooth surface through the measurements you
have, and at every point it also tells you **how confident it is**. Near your
measurements it's confident. Far from them it isn't, and it says so.

That second part is the entire reason it's here. The claim being tested is that
this model knows when it's guessing.

## What it builds

A single function that takes your measurements and hands back a fitted model —
plus a small number of helpers that exist purely to stop known mistakes.

## Why this file is mostly about avoiding silent errors

The underlying library is excellent and has **five specific ways of quietly
doing the wrong thing** if you use it the obvious way. All five have been
verified on the exact installed version — they're not theoretical. Details are
in `../preflight-findings.md`.

Two are worth understanding even without any code background, because they'd
each invalidate the headline result:

**The made-up noise level.** When you ask the model about a point you haven't
measured, it needs to know how noisy a measurement there would be. If you don't
tell it, **it silently averages the noise from everything you have measured and
uses that everywhere.** No warning. There's even a comment in the library's own
source code saying "be smarter here." The project's main calibration number is
measured at exactly these unmeasured points — so left alone, that headline
number would be computed against a noise level nobody chose.

**The 161× units trap.** Fixing the above means supplying the noise level
yourself. But the number you hand over at *setup* time must be in ordinary
units, while the number you hand over at *question* time must be in rescaled
units. Do the obvious thing and use ordinary units for both, and you are wrong
by a factor of **161** — in a case that was actually measured. Silently. Plausible
numbers come out either way.

This second one was not in the original specification. It was found while
testing the fix for the first one.

**So this file's real job is to be the one place that handles all five.**
Everywhere else in the project calls this file rather than the library directly,
which means each trap has exactly one place it could go wrong, with a test
sitting on it.

## How we'll know it works

A test per trap — each one written so it fails if the trap is ever
reintroduced. Including one that takes a known noise level, sends it through the
whole conversion, and checks the number that comes out the other end is the one
that went in.
