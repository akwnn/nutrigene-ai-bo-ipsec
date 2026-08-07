# 08 — The batch runner

**File:** `src/boec/runner.py` · **Status: ✅ built, 24 tests passing**

---

## The problem it solves

One run of the search proves nothing. Any single run could have got lucky.

So the real experiment is **hundreds of runs**: several simulated systems, each
with several different starting random seeds, each searched by several different
methods. This file runs that whole grid and collects the results into one table.

## What it builds

**The grid loop.** Work through every combination, run it, record the outcome.

**Results in a proper table format**, with a companion file recording the exact
settings and the exact version of every library used. That companion file is
what makes a result reproducible six months later, when the libraries have moved
on and nobody remembers which settings produced which figure.

**Skip anything already done.** Re-running the grid picks up where it left off.

> Not primarily for crash recovery. It's because during development you
> interrupt runs constantly, and redoing hours of finished work every time is
> intolerable on a two-week schedule.

**Optional parallel execution**, with each worker told to use exactly one
processor core. Left alone, the numerical libraries each grab every core they
can, and running eight jobs at once ends up *slower* than running them one at a
time as they fight each other.

## How long this actually takes — measured, not guessed

The original plan estimated 3–5 hours for the full grid, single-threaded.

**Measured: about 25 minutes.** One individual run is 5–9 seconds, not the
estimated 60.

Two consequences, and the second matters more:

- **Nothing has to be cut.** An earlier worry was that the grid would need
  shrinking to fit the schedule. It doesn't.
- **Mistakes became cheap.** A complete re-run after fixing a bug costs about
  half an hour. On a two-week project that changes how you work: when you're
  unsure whether a change mattered, you re-run and find out rather than reasoning
  about it.

One caveat, stated plainly: those timings were measured against a stand-in
problem, because A's real simulator doesn't exist yet. Nearly all the time goes
into the search step rather than into evaluating the problem, so the numbers
should hold — but they get re-measured once the real one lands.
