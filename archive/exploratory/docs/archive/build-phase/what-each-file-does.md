# WHAT EACH FILE DOES

**Written for someone who is not a programmer.** No code, no jargon that isn't explained. If you want the technical version, each file has a long comment at the top saying the same things more precisely.

Updated 2026-08-07.

---

## The one-paragraph version of the whole project

We are trying to work out the best recipe for turning stem cells into blood-vessel cells. There are many ingredients and each can be used in many amounts, so trying every combination is impossible — each experiment takes about two weeks. The standard approach runs a fixed pattern of about 48 experiments and fits a curve through the results. We are testing whether a smarter approach — one that looks at results so far and *chooses* what to try next — gets to the same answer in fewer experiments. Right now we are proving the software works on made-up data where we already know the right answer, before pointing it at real published data.

---

## The two ideas everything else hangs off

**Ideas about the recipe are separate from actually running it.** The software never runs an experiment itself. It only ever says "try this one next", and something else comes back with a result. Right now that something else is a made-up formula. Later it will be a table of published results. Later still it will be a person with a pipette. Because the software only ever proposes, none of it has to change when the source of results changes. That is the single most important design decision in the project.

**Being honest about not knowing is the point.** Any model can give you a number. The valuable thing is a model that also tells you how much to trust that number — confident near things it has seen, openly guessing far away. The published study we are building on made exactly this mistake: its curve pointed confidently at a recipe outside the range it had actually tested, they made it, and it barely worked.

---

## Files that exist now

### `metrics.py` — "you promised X, what did we actually get?"

Ask a model where the best recipe is. Go and look at what really happens there. Report the gap between the promise and the reality.

That gap is the headline number of the whole experiment. If a model confidently points somewhere it has never been and reality falls short, this is the file that measures by how much.

**Why it matters that this is one file and not two.** Two people on this project need this exact measurement, from two different directions. If each wrote their own version we would get two numbers that disagree and no way to tell which was right. One shared piece of code means the two results genuinely confirm each other. It is deliberately built so that the same inputs always give the same answer, no matter who runs it.

### `rsm.py` — the traditional approach, fairly represented

This is the method the field already uses: fit a smooth curved surface through your measurements, then read off where its peak is.

It does three things:

- **Fits the curve** to whatever measurements it's given.
- **Works out honest error bars** — not just "the peak is here" but "here, give or take this much".
- **Says what kind of peak it is.** A genuine high point, a low point, or something ambiguous like a saddle or a ridge. This matters more than it sounds: when you only measure a small region on the rising slope of something, the fitted curve can end up curving the *wrong way*, so its "turning point" is actually a bottom, not a top. Reporting a bottom as if it were a top would be an embarrassing error.

**Why the error bars are so important here.** The whole comparison in this project is between the error bars this traditional method produces and the ones the newer method produces. Comparing a careful newer method against a bare number from the older one would be unfair, and would be the first thing a reviewer objected to. This file makes sure the older method gets a fair hearing.

### `designs.py` — which experiments to actually run

Suppose you can afford 48 experiments and you have 6 ingredients. Which 48 combinations?

Not at random. There is a well-established pattern with three parts:

- **Corners** — every ingredient at either its lowest or highest setting. This is where you learn how ingredients affect *each other*.
- **Axial points (the "edges")** — one ingredient pushed to an extreme while the rest sit in the middle. This is where you learn whether more of something starts helping less, or starts actively hurting.
- **The middle, repeated** — the same central recipe several times over. Running the same thing more than once is the only way to know how noisy your measurements are, and therefore whether a difference you see is real or just wobble.

**The arithmetic that forced our hand.** With 6 ingredients there are 64 corners — already more than our budget of 48, before adding a single axial or middle point. So we use a carefully chosen *half* of them: 32 corners, picked so nothing important gets confused with anything else. Add 12 axial points and 4 middles and you get exactly 48. That number isn't a coincidence; it's the budget the plan calls for.

**Why the exact pattern isn't a detail.** The traditional method's error bars are calculated from the pattern of experiments itself — change which 48 you run and the error bars change even if no measurement changes. So using a different pattern from the one a real practitioner would use would mean comparing against a straw man.

### `surrogate.py` — the model that knows when it's guessing

Feed it your measurements so far. It gives back two things for any recipe you ask about: what it expects to happen, and how sure it is.

The intuition is simple: recipes that are similar probably behave similarly. So it's confident near things you have measured, and progressively less confident the further you get. That "less confident far away" behaviour is exactly what the traditional curve-fitting approach cannot express, and it is the heart of the argument.

**This file is unusually paranoid, for a good reason.** There are **five known ways to set this up wrongly where nothing complains** — no error, no warning, believable-looking output, and a completely wrong statement about how confident the model is. Since how-confident-the-model-is *is* the finding, every one of them would quietly ruin the result.

Three were already known and written down. **Two more we found ourselves**, by testing the actual installed software rather than trusting the documentation:

- Asking the model to include measurement noise made it quietly average all the noise it had ever seen and apply that one flat figure everywhere — including at recipes nobody has run. The software's own source code has a note from its authors admitting this should be smarter.
- Fixing that by supplying the noise ourselves turned out to need it on a *different scale* from the one used everywhere else. Getting that wrong was off by a factor of over a hundred. Silently.

All five are handled in this one file, and **no other part of the project is allowed to ask the model a question directly** — everything goes through here. That is what stops the traps coming back. Every trap has a test that fails if someone reintroduces it.

### `optimizers.py` — what to try next

Turns the model's beliefs into a concrete proposal. Two modes: search anywhere (continuous), or pick only from a fixed menu (discrete). The menu mode is what makes replaying a published study possible later. Also includes the simple baselines (random, Sobol, LHS) so the comparison is fair.

### `campaign.py` — propose, measure, learn, repeat

The loop everything else plugs into. Asks for the next batch, gets results back from whatever is answering today (a stand-in formula, later A's oracle, later a published table, later a person), updates the model, and can save its place mid-run. It never calls the oracle itself — only through an evaluator interface.

### `parametric.py` — what a practitioner would try

A third comparator: fit an additive biphasic curve with no interaction terms — what someone would reasonably try without knowing the planted answer. Convergence failures are logged, not silently dropped.

### `discrimination.py` — the comparison the paper reports

The E4 machinery: three scorers (GP uncertainty, second-order error-bar width, and plain nearest-neighbour distance), rank correlations, and the discrimination test. The two numbers that needed locking (candidate-set size and the AUC threshold) live in `configs/experiment/e4.yaml` and were fixed before any result existed.

### `runner.py` — run the grid, skip what's done

Sweeps instances × seeds × methods, writes parquet plus config sidecars, and skips anything already finished so interrupted development runs do not redo hours of work.

---

## Files that don't exist yet (Person A's lane)

| File | In plain terms | Whose |
|---|---|---|
| `oracles.py` | The made-up data. A formula with a right answer hidden inside it, so we can check whether the software finds what we planted. **Everything experimental is waiting on this.** | A |
| `space.py` | The list of what can be varied and between what limits. | A |
| `evaluators.py` | The go-between that fetches results — from the formula now, a published table later, a person later still. (B's campaign already defines the interface shape.) | A |
| `diagnostics.py` | Checks whether the model's confidence claims are actually trustworthy (E3). | A |

---

## How to check any of this yourself

Every claim above is backed by a test that fails if the claim stops being true. There are **218** of them right now.

```
python -m pytest -q
```

Two of those tests exist purely to *demonstrate the bugs we're avoiding* — they deliberately do the wrong thing and confirm it produces the wrong answer, so that if a future software update changes the behaviour, we find out immediately rather than silently publishing a wrong number.

---

## Where things stand

**Done (Person B):** the shared measurement, the traditional method (including descriptive stepwise third-order), the experiment pattern, the GP, the proposal engine, the campaign loop, the practitioner comparator, the E4 discrimination machinery, and the batch runner.

**Still open with A:** who formally owns `designs.py` (B wrote it; A was the original owner — one sentence). A's standard test-function wrappers before the real oracle.

**Blocked:** the actual experiments (PF1, E2, E3, E4 *results*) cannot run until Person A finishes the made-up data generator. That one file is what everything else on both sides is waiting for.
