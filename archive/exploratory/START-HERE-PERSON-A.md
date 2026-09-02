# START HERE — PERSON A

**Read this first. It should take five minutes.**

Written 2026-08-07, end of day 1. Person B's lane is code-complete and **hard-blocked on you**.

---

## The one-sentence version

**Build the oracle. Everything on both sides is waiting behind it.**

---

## Why it is that urgent

The oracle is the critical path for **four** separate pieces of work, not one:

| Blocked | Whose | Why |
|---|---|---|
| **PF1** — does the effect exist at all? | Yours | Needs landscapes to measure on |
| **E2** — is our method more efficient? | Yours | Needs something to optimize |
| **E3** — are the confidence claims trustworthy? | Yours | Needs something to be confident about |
| **E4** — the extrapolation experiment | B's | Needs landscapes with a known peak |

And **PF1 decides whether B's entire experiment exists.** If over-prediction is near zero at every setting, E4 has no mechanism and the plan says we shrink it and let E2 carry the paper. On a 14-day clock, finding that out on day 8 would be very bad. It is day 1.

---

## What to build, exactly

The oracle has to answer **three questions**. That is the whole interface.

```python
class BiphasicOracle:
    @property
    def x_star(self) -> Tensor:                 # (d,)
        """Where each ingredient's response peaks."""

    def truth(self, X: Tensor) -> Tensor:       # (n, d) -> (n, 1)
        """The NOISELESS value. Used only for scoring, never for fitting."""

    def observe(self, X: Tensor) -> tuple[Tensor, Tensor]:   # -> ((n, 1), (n, 1))
        """A noisy measurement, and an estimate of how noisy it is."""
```

**You import nothing from B's code.** The interface is structural — if your class has those three, it drops straight in. Nothing needs changing anywhere.

For the campaign loop, the matching interface is even smaller — just `evaluate(X) -> (Y, Yvar)`. That is `boec.campaign.Evaluator`.

### A worked example already exists

`tests/test_e4.py` contains `StandInOracle`, which implements exactly this shape and is what B's tests currently run against. **Copy its structure.** Yours differs only in being the real thing: the depth inversion, the feasibility scan, the acceptance checks, instance hashing, and cached optima, per `phase1_build.md` §4.

### One thing to get right

`truth()` must return the **noiseless** value. If it returns a noisy draw, over-prediction picks up measurement noise and the whole E4 distribution widens for a reason that has nothing to do with extrapolation.

---

## Two things B found that land in YOUR lane

Both are silent — no error, no warning, believable-looking output. Full write-up in `docs/preflight-findings.md`.

### 1. Your calibration experiment would have measured the wrong thing

Asking the model to include measurement noise makes BoTorch **quietly average all the noise it has ever seen and apply that one flat figure everywhere** — including at recipes nobody has run. Which is exactly where E3's headline number lives.

Source: `botorch/models/gpytorch.py:532`. It carries a comment from its own authors: `# TODO: be smarter here`.

**What to do:** never use that path. Use `boec.surrogate.predictive(model, X, noise=...)` and supply the noise yourself. Say so in methods.

### 2. The fix has a trap on top of it

The noise you supply must be on a **rescaled** axis, while training noise is on the normal one. They are inconsistent. Passing the obvious thing was **wrong by a factor of 161** in testing.

**What to do:** nothing — `boec.surrogate.predictive` handles it, and it is the only place in the codebase allowed to touch prediction noise. Just don't go around it.

---

## What is already built for you

**Do not reimplement any of this.** It is tested and A/B agreement depends on it being one copy, not two.

| You need | Already exists | Note |
|---|---|---|
| Over-prediction measurement | `boec.metrics.over_prediction_at_constrained_argmax` | **The shared function.** Your E2 confirmation run and B's E4 must call the same one, or you get two numbers that disagree with no way to adjudicate. Deterministic given a seed. |
| Second-order curve fit + error bars | `boec.rsm.fit_second_order` | |
| Turning-point classification | `boec.rsm.classify_stationary_point` | Returns max / min / saddle / ridge — the four categories PF1 needs |
| The 48-run pattern | `boec.designs.central_composite` | ⚠️ **This was specced as yours.** See below. |
| The hidden training corner | `boec.designs.sub_box_bounds` | |
| Screening designs for your DoE arm | `boec.designs.screening_design` | |
| The model | `boec.surrogate.build_gp` | All five silent traps handled |
| The campaign loop | `boec.campaign.Campaign` | |
| The grid runner | `boec.runner.Runner` | Skips work already done |

**233 tests passing.** `python -m pytest -q`

---

## Three questions only you can answer

Full list in `docs/OPEN-QUESTIONS.md`. These three matter most:

### Q2 — `designs.py`: keep B's, replace it, or co-own? **One sentence, please.**

It was specced as yours. B wrote it because PF1 was otherwise blocked and PF1 decides whether B has a lane. B's own spec says "ask, don't fork" — **this is the ask, retrospectively, with working code attached.**

**If you have already started your own, say so today.** That is the one thing here that could waste a day.

What's there: 32 corners + 12 axial + 4 centre = 48, exactly. Face-centred rather than rotatable, because rotatable axial points would fall outside the hidden corner and defeat the experiment. Resolution verified from first principles rather than a lookup table.

### Q5 — the acquisition method assumes noiseless measurements. Ours are noisy.

The spec mandates `qLogEI`, which needs "the best value seen so far". But the best of 48 noisy measurements is systematically flattering — the winner is partly whichever point drew lucky noise.

BoTorch ships a variant for exactly this. **Its own documentation says it exists because the standard one "would require noiseless observations".** The spec's stated reason for picking `qLogEI` is numerical stability, a different concern — so this looks unconsidered rather than decided.

**Both are implemented. The spec's choice is still the default — B has not silently deviated.** It needs your input because E2's fairness rules say explicitly: *do not tune your own method while leaving the baselines at defaults.*

### Q8 — the `Yvar` floor value

The spec says imputed noise gets "a floor" and never gives a number. Your call — you own the noise policy.

---

## Your first day, in order

1. **Build the oracle.** Nothing else you do matters as much.
2. **Answer Q2** — one sentence, and it might save you a day of duplicated work.
3. **Run PF1** using the functions listed above. Report over-prediction at each setting **plus the turning-point breakdown** — a bare rate would hide that low settings produce bottoms rather than tops, and those mean different things.
4. **Read `docs/preflight-findings.md`** before you finalise how E3 measures anything.
5. **Run PF2** — the maths checks on your own module.

---

## Useful facts before you plan

- **Compute is ~10× cheaper than the spec assumed.** One run is 5–9 seconds, not 60. The whole grid is about 25 minutes, not 3–5 hours. **Nothing needs to shrink**, and a full re-run after a bug fix costs half an hour — so prefer re-running to reasoning about whether a change mattered.
- **We are not contacting the original paper's authors.** That has been removed from all the planning documents. Everything stage 2 needs comes from digitising the published figures.
- **The horizon is 14 days, not 3 months.** Stage 3 — the wet lab — is out of scope.

---

## Where things are

```
docs/OPEN-QUESTIONS.md        every decision needed, from either of us
docs/preflight-findings.md    the two library bugs — read before finalising E3
docs/what-each-file-does.md   plain-English map of every file, no jargon
tests/test_e4.py              worked example of the oracle interface
```
