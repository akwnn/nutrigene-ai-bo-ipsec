# 04 — The proposal engine

**File:** `src/boec/optimizers.py` · **Status: ✅ built, 30 tests passing**

---

## The problem it solves

The model (piece 03) tells you what it believes and how unsure it is. This piece
turns that into an actual answer to: **"so what should we try next?"**

That's the decision at the heart of the whole method. Test something you're
confident is good, or test something you're unsure about and might learn from?
Too much of the first and you polish a mediocre recipe forever. Too much of the
second and you wander around learning things that don't help.

## What it builds

**The main proposer.** Scores every possible recipe by how much better than your
current best it might plausibly be, accounting for uncertainty, and picks the
winner.

**A "pick from this list" mode.** Instead of proposing any recipe at all, it
picks from a fixed menu of allowed ones.

> **This one is not optional and the reason is a scheduling one.** A later phase
> of the project replays a real published dataset — and there, the only recipes
> you can propose are the ones somebody actually ran, because they're the only
> ones with a measured result. Build only the free-choice version now and that
> later phase means rewriting the core of this file. Building both now costs
> almost nothing.

**Simple comparison baselines.** Random picks, and two kinds of evenly-spread
picks. You need to know whether the clever method actually beats picking
sensibly-but-dumbly. Often it doesn't, and that's worth knowing.

## The trap in here

When proposing several recipes at once, the obvious approach is to score every
recipe and take the top few.

**That gives you near-duplicates.** The top four all cluster on the same
promising hill, a hair apart — so you spend four experiments learning what one
experiment would have told you.

The fix is to score *sets* of recipes together, so the scoring understands that
a second recipe next to the first adds almost nothing. It's a different
calculation, not a filter applied afterwards.

## How we'll know it works

- Every proposal from the menu mode is provably on the menu.
- Ask for four proposals and check they aren't all crowded together.
- Give it a simple problem with a known answer and confirm it finds the peak.
