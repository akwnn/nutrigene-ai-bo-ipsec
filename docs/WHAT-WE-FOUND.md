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
---

# Part two: we then tried to break all of it

The three experiments above produced findings. The next four asked whether those findings
are **real**, by attacking each one at its weakest point.

Three attacks, three different outcomes: **one held, one broke it, and one turned out to
run backwards.**

---

## Attack 1: three extra wells erase the whole result

### The worry

Our headline says: pick the well that read highest, and the textbook method wins.

But we already knew that rule is bad — the highest reading is the genuinely best well you
tried only 2–22% of the time. And it's *worse* for the AI method, because the AI piles its
wells into the good region, where everything is nearly as good as everything else and the
differences are smaller than the measurement noise. So its highest reading is close to a
coin toss.

That raises an uncomfortable possibility: maybe the textbook method isn't better at
*searching* at all. Maybe it just happens to suit one particular way of picking a winner.

### What we did

Took the **exact same campaigns** — same wells, same order, same everything — and changed
only the final step. Four ways to pick:

1. **One reading** (what we've been doing)
2. **Measure everything twice** and pick by the average — costs another 48 wells
3. **Confirm the top three**: re-run just your best three and keep whichever confirms best
   — costs 3 wells
4. **Ask the model** which of the wells you already ran is best — costs nothing

### What we found

| how you pick | extra wells | textbook advantage | vs the published number |
|---|---|---|---|
| one reading *(published)* | 0 | **−0.0595** | — |
| measure everything twice | +48 | −0.0262 | **44%** of it |
| **confirm the top three** | **+3** | **−0.0009** | **1%** of it |
| ask the model | 0 | −0.0227 | 38% of it |

**Confirming three wells makes the two methods equal.** Three extra measurements on a
48-well campaign — 6% more work — and the entire advantage is gone.

### Why so little effort does so much

Because it doesn't help both methods equally.

- Confirmation moves the AI method from 0.1553 to **0.1446** — a bit better.
- Confirmation moves the textbook method from 0.0958 to **0.1437** — clearly *worse*.

The textbook method's single reading was already the trustworthy one, because its design
repeats the centre point and spreads the rest out. A protocol that says *"decide using a
fresh single reading"* throws that reliability away.

So the headline was never really "the textbook method searches better." It was "the
textbook method's readings are easier to trust" — and a lab that confirms its shortlist
doesn't need that help.

### Two things we're not hiding

Our "confirm top three" rule decides using the confirmation reading **alone**, throwing
away the first one. A lab that averaged both readings would be doing something different,
and **we didn't run that version**. The tie is a property of the protocol as we built it.

And the "ask the model" row disagrees with itself: one statistical test says there's a real
difference, the other says there isn't. The project already had a rule for that, written
down long before this run — the stricter test decides, so we call it **no difference** and
report both numbers rather than the convenient one.

---

## Attack 2: does it depend on which AI we used?

### The worry

There isn't one "AI method" — there's a family, and they differ in how they choose the
next wells to try. We used the standard one. But our measurements are noisy, and there's a
version built specifically for noisy measurements, which is arguably the one we should have
raced.

Any reviewer can dismiss the whole result with "you used the wrong one."

### What we did

Re-ran everything with **both**. Worth noting: the noise-aware version is **better than the
standard one at all four settings**, so this makes life harder for the textbook method, not
easier.

### What we found — the main result holds

At the noisy assay, both settings, both ways of picking: **same winner, same story.** At
the main setting the textbook method's advantage is −0.0574 with the noise-aware AI against
−0.0595 with the standard one. Essentially unchanged.

And on "what did each method actually test," the textbook advantage is *bigger* against the
noise-aware AI, not smaller.

**The noise-aware version does exactly what it's supposed to do.** It spots its own best
well 22% of the time instead of 8% — nearly three times better. It just doesn't spot it
often enough to close the gap.

### But it withdraws one thing I told you earlier

In Part One I said that at 8 ingredients with a quiet assay, the textbook method *"genuinely
tested better recipes and the readout hid it completely."* I called it the interesting cell.

**With the noise-aware AI, that difference disappears** (the significance test gives 0.56 —
nothing). It was a fact about the standard AI's search, not about the textbook method.

That claim is **withdrawn**. It's struck through in the detailed record rather than deleted,
so the retraction stays visible.

---

## Attack 3: were we handicapping the textbook method?

### The worry

One of our test problems has six ingredients that **all matter**. But the textbook pipeline
starts by screening six down to four — so it's forced to throw away two ingredients that
genuinely do something.

So when the AI wins on that problem, we can't tell whether the AI optimised better, or
whether we just crippled the competition.

### What we found first, before running anything

You can't remove the screening step at eight ingredients. The arithmetic forbids it: fitting
a curved surface in eight dimensions needs **45 numbers**, and the only design that fits
inside 48 wells gives you **35 measurements**. Fewer measurements than things to estimate.

That isn't a limitation of our experiment. **It's the reason the screening step exists.** So
the comparison only runs at six ingredients, where an unscreened design lands on exactly 47
wells plus one confirmation.

### What we found — the opposite of the worry

| noise | AI (standard) | AI (noise-aware) | textbook, screened | textbook, **unscreened** |
|---|---|---|---|---|
| high | 0.2984 | 0.2642 | **0.5623** | 0.7685 |
| low | 0.1938 | 0.1658 | **0.5428** | 0.7502 |

Giving the textbook method all six ingredients makes it **worse by 0.207**, and the AI's
lead gets **1.6 to 1.8 times bigger**.

The reason is simple once you see it: 47 wells spread across the whole six-dimensional
space is very thin coverage. Twenty-seven wells concentrated in a small region around the
best screening result is a much better use of the same budget when the peak is narrow.

**The screening step wasn't a handicap. It was the textbook method's way of concentrating
its effort, and it was earning its keep.**

### And a side result that matters elsewhere

We have a big finding elsewhere that when the textbook method's fitted curve suggests a
recipe, that recipe is often terrible — and we've been explaining it as *extrapolation*: the
curve is fitted in a small box and then asked about the whole space.

The unscreened design covers the whole space, so extrapolation is **impossible** there. If
our explanation were right, the problem should mostly vanish.

It barely moves — 0.02 to 0.03 out of about 0.90.

So on this particular test problem, the bad recommendation isn't about extrapolating out of
a small box. **A curved surface simply can't describe a landscape with six separate peaks.**
Our usual explanation is right about our main problem and wrong about this one, and the two
shouldn't be lumped together.

---

## Attack 4: could anyone rebuild our figures?

Not really, it turned out. Two problems of the same kind:

- **Figure 1 had no code behind it at all.** It was a hand-made page with twenty numbers
  typed into it, and it wasn't even stored in version control — while the paper referred to
  it by filename. Anyone downloading the project got a paper pointing at a figure that
  wasn't there and couldn't be rebuilt.
- **Figure 2 had code, but the code had a table typed into it.** So the page could be
  rebuilt except for the one table that mattered most.

Both are now generated from the stored data. Figure 1 lists where each bar came from, right
on the page.

We also had Figure 1 **check its own claim**: its whole point is that the winner changes
depending on how you pick. The build now verifies that's still true (it is, in 3 of 4
settings) and **fails rather than drawing the figure** if it ever stops being true.

And twelve spots in Figure 1 are deliberately left **blank**. There's one quantity we simply
don't have for the AI method, and filling it in with a nearby number would quietly claim
something we never measured.

Figure 2 also gained the thing the cost comparison actually needed: **the share of all
problems solved by a given budget.** Before, we reported medians among the runs that
succeeded — but each method succeeds on a different subset, so the method that succeeds
least often was getting the flattering average.

---

## Where everything stands now

| claim | status | why |
|---|---|---|
| Textbook method wins on the reported reading, noisy assay | **holds** | survives both AI versions |
| …and it's mostly a spotting effect, not a search effect | **holds** | confirmed under both |
| …**and it vanishes if the lab confirms three wells** | **new** | −0.0595 → −0.0009 |
| Textbook tested better at 8 ingredients, quiet assay | **withdrawn** | nothing there with the noise-aware AI |
| The AI's win on the deceptive problem is a screening artefact | **refuted** | lead grows without the screen |
| The bad recommendations are extrapolation | **only on our main problem** | doesn't transfer |
| "At a quiet assay the AI gets there far more often" | **withdrawn** *(Part One)* | it was an artefact of not letting the competition move |

**Still open:** one more hand-made figure with no code behind it; some citations that need
checking against the actual PDFs; and the standing caveat that **none of this is real cells.**

---

## The one-sentence version

Same wells, same problem, same model — which method looks better depends on whether you
report the best number you measured or the recipe your model recommends, and a lab that
confirms its best three wells before committing sees no difference between them at all.

---

*Detail and statistics in `docs/RESULTS.md`. Data:
`results/q54-hill-spread-gp-draws.json`, `q55-oracle-best.json`, `q56-doe-ascent.json`,
`q57-search-vs-id.json`, `q58-selection-sensitivity.json`, `q59-hartmann-no-screen.json`.
New code in `src/boec/sequential_rsm.py` and `src/boec/selection.py`, both with tests
written first. All seven workstreams of the revision program complete. 808 tests passing.*
