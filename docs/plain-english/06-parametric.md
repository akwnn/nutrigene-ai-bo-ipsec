# 06 — The rival model

**File:** `src/boec/parametric.py` · **Status: ✅ built, 15 tests passing**

---

## The problem it solves

A reviewer will ask: *"you compared a machine-learning model against a generic
curve fit — but a real scientist wouldn't use a generic curve. They'd use a
formula that reflects what they know about the biology. How does your model do
against that?"*

This file is the answer to that question.

## What it builds

A model in the shape a practitioner would actually reach for — a formula that
encodes the known pattern of "more helps, up to a point, then more starts
hurting", fitted to each ingredient.

## The one design decision, and it's the whole point

There's a version of this that would be much easier to build: use the **exact**
formula the simulator uses to generate the data.

**That version is deliberately not built.** It would win, trivially, because it
would be the right answer by construction — you'd have handed the model the
answer sheet. It would tell you nothing about the real world, where nobody knows
the true formula.

So the version built here is the honest one: right general shape, and
**deliberately missing the parts about ingredients affecting each other** —
because someone working without the answer sheet would leave those out too.

The comparison is only meaningful if the rival is the model a competent person
would actually build, not the model that happens to be correct.

## The thing that must not be swept under the rug

Fitting a formula like this is an iterative search that **sometimes doesn't
converge** — it can fail to settle on an answer for a particular dataset.

The tempting move is to quietly skip those cases. That's a serious problem: if
the fit tends to fail on the hard instances, silently dropping them means the
reported average is computed over the easy ones and looks better than reality.

So every failure gets logged, and **the failure rate is itself a reported
number** in the paper.
