# 05 — The campaign loop

**File:** `src/boec/campaign.py` · **Status: ✅ built, 27 tests passing**

Built against a small `Evaluator` interface so anything that returns results can plug in. Person A's standard test-function wrappers (and later the real oracle) still need to land for the deliberate swap-cleanliness check — the loop itself is not blocked.

---

## The problem it solves

This is the cycle that everything else plugs into:

> propose some experiments → run them → learn from the results → propose again

It's the piece that turns a model and a proposal engine into an actual
self-directing search. It's also **the module Person A must be able to explain
back** — not as a formality, but because if the internship doesn't extend,
whoever stays has to run the next two phases alone.

## What it builds

**Ask and tell, kept separate.** You *ask* it for recipes to try. You go away and
run them. You *tell* it what happened. The loop never runs the experiment
itself.

> That separation looks pedantic and isn't. It's what makes a later phase
> possible where the thing being "run" is **a human in a lab**, taking days to
> come back. The loop doesn't need to care.

**Tracking of experiments that are out but not back.** Ask for more recipes
while three are still running and it must not suggest those same three again.

**Save and resume.** Development means interrupting things. You need to stop and
pick up exactly where you were.

**A record of every prediction, made before the answer is known.** Each time it
proposes a recipe, it writes down what it expected to happen — *before* the
result comes in. This is what makes the central claim testable at all: you
cannot assess whether a model knew it was guessing by looking at predictions
made after the fact.

## The decision worth flagging

**What gets saved is your data, your settings, and the random-number state — not
the trained model.**

Saving the trained model would be the obvious choice and it's the wrong one:
those saved files break when the underlying library updates, and this project
will span at least one update. Saving the inputs and rebuilding the model on
resume is slower by seconds and survives.

The random-number state is the fiddly part and it's essential — without it,
stopping and resuming gives you a *different* run, and the test proving the
whole thing is reproducible would fail.

## How we'll know it works

Start a run, save it, reload it, finish it. Then run the same thing start to
finish without interruption. **The two must be identical, step for step.** That
single test covers the loop, the saving, and the random-number handling all at
once.

And the human test: A narrates what this module does and why. If A can't, it
isn't done.
