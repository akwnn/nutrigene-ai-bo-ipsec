# 02 — The test plan

**File:** `src/boec/designs.py` · **Status: ✅ built, 28 tests passing**
**⚠️ Ownership between A and B is unresolved — see the bottom.**

---

## The problem it solves

You can afford 48 experiments. You have 6 ingredients to vary.

**Which 48 combinations do you run?**

Not a rhetorical question — the answer changes the result of the study, and not
in the way you'd expect.

## Why the choice matters more than it looks

Here's the surprising part. The classical model's error bar — the thing being
compared against the machine-learning model — is calculated **from the pattern
of points you measured**, before any data comes back.

Change which 48 combinations you run and the error bars change, *with the same
underlying reality and the same measurements*.

So picking the points casually would quietly rig the comparison. Using a
scattered or random set of points, when a real statistician would use a
deliberate pattern, would make the classical approach look worse than it is —
and the finding would be an artefact of a badly chosen test plan.

**This file exists to make the comparison fair.**

## What it builds

The pattern is a **central composite design**, which comes in three parts:

- **Corners** — every ingredient at either its low or high setting. This is
  where you learn how ingredients interact with each other.
- **Axial points** — one ingredient pushed to its extreme while everything else
  sits in the middle. This is where you learn whether the response *curves* —
  whether more of something starts helping less.
- **Centre points** — everything in the middle, run several times over. Running
  the identical thing repeatedly is the only way to measure how noisy your
  measurement is, which is the only way to know if a difference you see is real.

## The arithmetic, and why it's forced

With 6 ingredients there are **64** corners. That already blows the budget of 48
before a single axial or centre point is added.

So a carefully chosen **half** of the corners is used — 32 of them, picked so
that nothing you care about gets confused with anything else:

> **32 corners + 12 axial + 4 centre = 48**

That "picked so nothing gets confused" is doing real work. Take the wrong half
and two different effects become mathematically indistinguishable — you'd get a
number, and it would silently be the sum of two things you wanted separately.
The code refuses to invent a halving rule it doesn't have on file, rather than
guessing.

## The one judgement call in here

**How far out should the axial points go?**

There's a textbook answer that gives the mathematically nicest properties, and
it pushes those points to about 2.4× the normal range.

**That answer is wrong for this experiment.** The whole setup is that training
data stays inside a boundary and the model is then asked about points beyond it.
Textbook-placed axial points would land *outside* that boundary — putting
training data in the very region the experiment is supposed to be extrapolating
into. That doesn't make the experiment worse, it makes it not exist.

So the axial points sit exactly on the boundary instead. This costs some
mathematical elegance and it's a documented, deliberate trade.

## How we know it works

The real test isn't "does it produce 48 rows." It's that the resulting plan is
fed straight into the curve fitter (piece 01) and must survive — proving there's
enough information in those 48 points to estimate all 28 numbers, with exactly
the 20 units of spare information the specification claims.

## ⚠️ The unresolved bit

This file is **specified as Person A's work** and Person B wrote it, because
A's critical first check was blocked without it.

**The code is done and tested.** What is still open is a one-sentence ownership
call from A (keep / replace / co-own) — not whether the CCD exists. PF1 now
waits only on A's oracle. See `../OPEN-QUESTIONS.md` Q2.
