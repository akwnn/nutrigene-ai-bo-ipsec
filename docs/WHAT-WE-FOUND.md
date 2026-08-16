# What we found — in plain English

Three experiments. Written down in advance, then run. This explains what they were for and
what came out, without the statistics vocabulary.

**First, the honest caveat.** None of this is real cells. It is a computer simulation of a
lab experiment — a made-up "response surface" shaped like a real one. It tells you about
the *methods*, not about biology.

---

## The setup

We are comparing two ways of finding the best recipe.

**The textbook lab method.** Run a screening batch to see which ingredients matter. Throw
away the ones that don't. Run a structured grid of experiments around the promising area.
Fit a curve to the results. The curve tells you where the best recipe should be. Go and
make it. Total: 48 wells.

**The AI method.** Fit a model to whatever you've measured so far, let it pick the next
four wells, measure them, refit, repeat. Also 48 wells — but it has to wait for results ten
separate times, where the textbook method only waits three times.

Both get exactly the same number of wells. That's the whole point of the comparison.

---

## The thing that turned out to matter most

**How you decide which well to call "the answer" changes who wins.**

There are two honest ways to finish a campaign:

1. **Pick the well that read highest on the day.** This is what most people do.
2. **Go with what your model says is best**, even if you never measured that exact recipe.

These sound like small bookkeeping details. They are not. Every one of the three
experiments below found that switching between them can flip which method looks better —
on the same wells, the same problem, the same model.

That is the finding. Everything else is detail.

---

## Experiment 1: how much of the win is just bad eyesight?

### The question

The textbook method beat the AI method when you pick the highest reading. But there are two
different reasons that could happen:

- The textbook method **looked in better places**, or
- Both methods looked in equally good places, and the textbook method was just **better at
  spotting** which of its wells was the good one.

Those need completely different responses. The first means the search is better. The second
means the *measurement* is noisy and the search had nothing to do with it.

Nobody could tell them apart, because we had never recorded the best well each method
actually tried — only the one it reported.

### What we did

Re-ran 200 AI campaigns and 200 textbook campaigns and recorded both numbers.

Before trusting any new number, we checked that re-running reproduced the *old* published
numbers exactly. It did — all 400 rows, to the last decimal place. If it hadn't, we'd be
describing a different experiment.

### What we found

**Both methods are far better than they realise.** Here is the gap between the best well
each one actually tried and the one it ended up reporting:

| Setup | AI method's blind spot | Textbook method's blind spot |
|---|---|---|
| 6 ingredients, noisy assay | **0.080** | 0.036 |
| 6 ingredients, quiet assay | 0.038 | 0.035 |
| 8 ingredients, noisy assay | 0.055 | 0.039 |
| 8 ingredients, quiet assay | 0.032 | **0.045** |

To put that in perspective: the entire difference between the two methods — the headline
result of this project — is 0.060. **The amount each method fails to notice about its own
results is bigger than the difference between the methods.**

How often does the highest reading actually come from the genuinely best well tried?
**Between 2% and 18% of the time.** Almost never.

### The headline

At the main setting, the textbook method's lead shrinks from **0.060 to 0.016** once you
score both methods on what they really tried.

**About three quarters of its advantage is not better searching. It is that the noisy
readout misleads the AI method more.**

Which makes sense. The AI method piles its wells into the good region, where everything is
nearly as good as everything else and the differences are smaller than the measurement
noise — so picking the winner is a coin toss. The textbook grid repeats its centre point
and spreads the rest out, so its readings are easier to tell apart.

**One setting looked like it flipped — and then didn't hold up.** At 8 ingredients with a
quiet assay, the two methods look identical by the highest reading, but the textbook method
appeared to have genuinely tested better recipes. **When we re-ran the whole thing with a
better-suited AI method, that difference vanished.** So it was a fact about the particular
AI setting we had used, not about the textbook method, and we withdrew it. See the last
section for what happened there. What does stand: the spotting rate at that setting is 2%,
the worst in the study.

### What this does and doesn't mean

It does **not** say which method a lab should use. It says the existing result is mostly a
statement about *reading a noisy plate*, not about *where to look*. If your lab repeats
measurements, or runs a confirmation, or trusts a model rather than a single reading, most
of this advantage doesn't apply to you.

---

## Experiment 2: we were being unfair to the textbook method

### The question

When we let both methods run long (200 wells instead of 48), we did something unfair, and
we said so in writing at the time.

The AI method re-aims after every four wells. It can walk right across the space.

Our textbook method couldn't move at all. It just repeated the same 48-well procedure four
times with different random starts, in the same place.

But that isn't the real textbook method. The actual textbook says: fit your curve, work out
which direction is uphill, take some steps that way, measure as you go, and rebuild your
grid wherever you ended up. It walks.

Until we built that version, we could not honestly say the AI method needs fewer
experiments.

### What we did

Built it. Wrote 19 tests first, then the code.

It works: it moves its grid an average of 3.4 times per campaign, and in 191 out of 199
cases the fitted curve had no peak inside the area it had explored — which is exactly the
situation where moving is the right call.

### What we found

**On "pick the highest reading" — the fair fight is a tie.**

At the easiest quality bar: 21 problems out of 25 for the walking textbook method, 21 out
of 25 for the AI method. Dead level. Across all the quality bars, after adjusting for the
fact that we ran many comparisons, essentially nothing separates them.

**And this cost us our best result.** We used to report: *"at a quiet assay, the AI method
gets there at all, far more often"* — 24 out of 25 against 13 out of 25. It was the single
strongest thing in the whole project, and it's the headline on our cost figure.

Against the walking textbook method it's 24 versus **16**, and it no longer holds up once
you adjust for multiple comparisons. Either way you do the adjustment.

**So the unfairness was real and it was doing work.** That result existed because we hadn't
let the competition move.

**On "trust the model" — the AI method still wins clearly**, at every quality bar. But
letting the textbook method walk transforms it: at the quiet assay it goes from 9 out of 25
to 21 out of 25 at the loosest bar, and from 2 out of 25 to 13 out of 25 at a tight one.
Three to six times better. Still beaten, but not embarrassed.

### A judgement call we had to make out loud

The written-down instruction said: walk uphill "until the response stops improving, then
move to the last improving point."

Taken literally, under realistic noise, that means you stop at the first step that reads
low — and a single noisy reading is a coin toss. In practice it meant the method almost
never moved at all, which would have quietly turned it back into the version we were trying
to replace.

The standard textbook (Myers & Montgomery) says something different: take the *best* point
along the path.

We ran both. The best-point version moves 229 times; the literal version 140. They disagree
about the answer in 4 comparisons out of 26.

We flagged this in the results rather than burying it, because picking the rule that makes
your new method look better is exactly the kind of choice that has to be visible.

### Three bugs the tests caught

1. **The uphill path couldn't leave its own grid.** Which means it couldn't actually move —
   the exact limitation we were trying to fix, wearing a new name.
2. **We compared each uphill step against the single best of 27 noisy readings.** The best
   of 27 noisy numbers is inflated by luck. Nothing could ever beat it, so nothing ever
   moved. It has to be compared against the repeated centre measurements, which is what
   those repeats are in the design *for*.
3. **When the grid hit the edge of the allowed range, its centre wasn't where we thought.**
   Three different parts of the code disagreed about where "the middle" was.

---

## Experiment 3: was one lucky roll of the dice?

### The question

There's a third, much simpler method: spread wells evenly across the whole space, measure
them all at once, fit one model, and go with what it says. **One batch. No waiting.**

The AI method needs to wait for results 48 times to spend the same wells. In a lab where
each round means plate, incubate, stain, read, that's the difference between one afternoon
and two months.

Earlier we found this simple method matched the AI method — but we'd only tried **one**
random spread. On other test problems, different random spreads gave answers that varied a
lot. So the match might have been luck.

### What we did

Ran it five times with five different random spreads. The first one deliberately reuses the
original spread, so it has to reproduce the published numbers exactly — and it did, all 550
of them.

### What we found

**It wasn't luck.** In 20 of 22 comparisons, all five spreads agree.

The 2 that disagree are exactly the 2 where the spread-to-spread variation is biggest — and
in both, the original run had happened to draw at the lucky end. So those two stay flagged
as unreliable.

**But here's the part nobody had reported.** At the noisy assay, if you go with what the
model recommends, **the one-batch method beats the AI method outright:**

| Quality bar | AI method (48 rounds of waiting) | One batch |
|---|---|---|
| loose | 20 of 25 | **25 of 25** |
| medium | 16 of 25 | **24.4 of 25** |
| tight | 10 of 25 | **22.2 of 25** |

All five random spreads agree on all three. This is not the lottery.

**And it reverses** if you go by the highest reading instead — there the one-batch method
loses badly at both noise levels.

Same wells. Same problem. Same model. The winner is decided entirely by which of the two
finishing rules you use.

---

## Something small but worth telling you

We set a tolerance for "close enough to count as reproduced" based on 44 values from a
trial run. When we ran the full 550, it failed — the real spread was wider than the sample
had shown.

We didn't just raise the number until it passed. Instead we checked whether the wobble
could actually change any conclusion.

It turns out **one** result in the whole study genuinely is decided by rounding error: a
value sits closer to its quality bar than the wobble itself. So we re-ran the entire
analysis with every value nudged up, then nudged down. **Nothing changed** — 22
comparisons, three versions each. The uncertain value exists, and it provably can't reach
any conclusion we draw.

Worth saying because the general lesson is: a tolerance you calibrate on a convenient
sample will fail on the real thing.

---

## Where this leaves the project

**Closed:**

- We can now separate "searched better" from "spotted it better" — and it's mostly the
  second one.
- The textbook method can now walk, so the long-run comparison is finally fair.
- The one-batch result rests on five spreads, not one.

**Still open:**

- A second AI variant is a stored control, not a full competitor.
- One of the external test problems throws away two ingredients that actually matter.

**What changed in the write-up:**

- **Removed:** "at a quiet assay, the AI method gets there far more often." It was an
  artefact of not letting the competition move.
- **Reinterpreted:** the textbook method's win at the noisy assay is real, but it's mostly
  about reading a noisy plate, not about searching.
- **Strengthened:** the one-batch method now has five spreads behind it, and on the
  model-recommendation rule it wins rather than ties.
- **Unchanged:** the AI method still wins the model-recommendation rule clearly against
  both textbook versions, and the 48-well comparison is untouched — at that budget there's
  nothing to walk to anyway.

---

## The one-sentence version

Same wells, same problem, same model — and which method looks better depends on whether you
report the best number you measured or the recipe your model recommends. Three separate
experiments, each designed to answer something else, all ran into it.

---

*Files: `results/q54-hill-spread-gp-draws.json`, `results/q55-oracle-best.json`,
`results/q56-doe-ascent.json`. Detail and statistics in `docs/RESULTS.md`. Written down in
advance in `docs/PROMPTS-NEXT.md`. New code in `src/boec/sequential_rsm.py` with 19 tests.
798 tests passing.*
