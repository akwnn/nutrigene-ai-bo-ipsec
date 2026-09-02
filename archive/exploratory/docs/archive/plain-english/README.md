# What we are building — in plain English

**Audience: anyone, including people who don't code.** No maths, no jargon that isn't explained on the spot. One file per piece of the build.

If you only read one thing, read the next two sections.

---

## The question the project is asking

You are trying to find the best recipe — the combination of ingredient amounts
that gives the best result. Testing every combination is impossible, so you test
a few, build a model of what's going on, and let the model tell you what to try
next.

**The danger is that the model is confidently wrong.**

Specifically: if all your test recipes sit in one corner of the possible range, a model can look at the trend, extend the line past where you actually measured, and announce "the best recipe is way over here" — pointing somewhere it has no evidence about. Follow that advice and you get a worse result than you had.

This happened in a real published study, which is where the project starts.

**So the question is: can the model tell you when it's guessing?**

Two kinds of model are compared:

- The **classic statistics approach** — fit a curve, report an error bar.
- The **machine-learning approach** — a Gaussian process, which reports how
unsure it is at every point.

The claim under test is that the machine-learning approach knows when it's extrapolating and the classic approach doesn't. The experiment is designed so that the honest answer might be "no" — and there's a deliberate check built in for the embarrassing possibility that the fancy model is just an expensive way of measuring "how far is this from anything I've seen?"

---

## Who is building what

Two people. **Person A** builds the simulated biology — the fake-but-realistic system that plays the role of the real experiment. **Person B** (you) builds the machinery that models it, decides what to test next, and runs the comparison.

**Nothing produces a result until A's simulator exists.** Everything in scope right now is machinery, and every piece of it is needed no matter how the experiment turns out.

---

## The pieces

Read in this order — each builds on the one before.


|     | Piece                                   | What it is                                      | Status   |
| --- | --------------------------------------- | ----------------------------------------------- | -------- |
| 00  | [The measuring tape](00-metrics.md)     | How much the model over-promised                | ✅ Built |
| 01  | [The curve fitter](01-rsm.md)           | The classic-statistics model and its error bars | ✅ Built |
| 02  | [The test plan](02-designs.md)          | Which 48 experiments to actually run            | ✅ Built |
| 03  | [The model builder](03-surrogate.md)    | The machine-learning model                      | ✅ Built |
| 04  | [The proposal engine](04-optimizers.md) | Deciding what to try next                       | ✅ Built |
| 05  | [The campaign loop](05-campaign.md)     | Running the whole cycle, repeatably             | ✅ Built |
| 06  | [The rival model](06-parametric.md)     | What a practitioner would try instead           | ✅ Built |
| 07  | [The comparison](07-e4-comparison.md)   | The actual measurement the paper reports        | ✅ Built |
| 08  | [The batch runner](08-runner.md)        | Running everything, hundreds of times           | ✅ Built |


**✅ Built** means the code exists and has tests that pass. Person B's machinery lane is complete on that measure. **Running the real experiments** still waits on Person A's made-up-data generator.

---

## Two things worth knowing before you read on

**"Tests" are not the experiment.** When these documents say something has 218
tests, that means 218 automatic checks that the code does what it claims —
run in a few seconds, every time anything changes. They catch mistakes.
They are not results.

**Several of these pieces exist to prevent silent wrongness.** The single
biggest risk on this project is not code that crashes — it's code that returns
a plausible-looking number that happens to be wrong, and nobody notices for a
week. Five specific instances of that have already been found and are documented
in `../preflight-findings.md`. Where a piece below exists mainly to close one of
those holes, it says so.