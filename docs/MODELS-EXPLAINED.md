# Models in This Study, in Plain English

This note explains the main models in the project for a non-technical reader:

- what each model is,
- why it was included,
- and how it changes the interpretation of the study.

This is a teaching document, not a manuscript. For the locked numbers, use
`docs/RESEARCH-SUMMARY.md`.

---

## Start with the big picture

This study is about a simple laboratory problem: you can test only a small
number of recipes, but at the end you must choose **one** to carry forward.

There are three different things that can be called a "model" in this project:

1. The **simulated world** the methods are tested on
2. The **curve or surface** each method fits to the data it has seen
3. The **decision rule** used to turn that fitted model, or the raw
   measurements, into one final choice

Those are different. A lot of the project exists to stop them from being mixed
together.

---

## 1. The simulated world: the Hill landscape

Before comparing methods, the project needed a stand-in for a real biological
optimization problem. That stand-in is a family of synthetic response surfaces
called **biphasic Hill-type landscapes**.

In plain language, each ingredient usually helps at first, then too much becomes
harmful. So the best recipe is somewhere **inside** the tested range, not at an
extreme corner. That is a reasonable shape for many dose-response problems.

### Why it was picked

- It resembles the kind of rise-then-fall behavior people expect in media or
  extracellular-matrix tuning
- It creates a realistic optimization problem with an interior optimum
- It lets the team compare methods many times under controlled noise

### How it affects the study

- It makes the study a **dry-lab simulation**, not a wet-lab validation
- It favors smooth surfaces, which is important when interpreting one-shot
  methods
- It is one reason the project also checked Levy, Rosenbrock, and Hartmann6 as
  robustness benchmarks

### What a non-technical reader should remember

The Hill landscape is the **world being tested**, not one of the competing
methods.

---

## 2. The classical model: a quadratic surface in DoE/RSM

The classical arm of the study uses a design-of-experiments / response-surface
workflow. After running a structured set of experiments, it fits a
**quadratic** surface.

You can think of this as drawing a smooth bowl-like or saddle-like sheet through
the observed results. The sheet can curve, and ingredients can interact, but it
is still a fairly simple mathematical shape.

### Why it was picked

- It is the standard model behind classical response-surface methodology
- It is what a fair comparison to BO should use, because BO is often presented
  as an alternative to this classical workflow
- With only 48 wells, a simple second-order model is realistic; a much more
  flexible classical model would ask the data to estimate too many moving parts

### How it affects the study

This model is central to one of the paper's main findings.

When the fitted quadratic is maximized over the whole allowed box, it often
points to a bad answer because the fitted surface is usually a **saddle**, not a
true peak. In the locked Hill runs, all 200 fitted quadratics were classified
as saddles.

That means the quadratic can make the classical method look much worse than it
really is if you read it in a naive way. Once the same quadratic is restricted
to the region actually supported by data, the giant BO advantage mostly
disappears.

### What a non-technical reader should remember

The classical method did not "fail" simply because it was classical. A large
part of the apparent failure came from **how the quadratic model was read**.

---

## 3. The machine-learning model: the Gaussian process

The BO arm uses a **Gaussian process**, usually shortened to **GP**.

In plain language, a GP is a flexible smooth curve or surface that does two
things at once:

- it predicts what response you might get at a recipe you have not yet tested,
- and it estimates how uncertain that prediction is.

That uncertainty estimate is important because BO uses it to decide whether to
try something promising, something uncertain, or a balance of both.

### Why it was picked

- It is the standard surrogate model in much of the BO literature
- It is flexible enough to learn smooth nonlinear patterns from a limited number
  of experiments
- It can express uncertainty, which is one of BO's main claimed advantages over
  classical response-surface fitting

### How it affects the study

The GP helps BO in two ways:

- it can guide the next batch toward promising or informative places,
- and it can make a model-based final recommendation after the campaign ends.

But the study also found an important caution: the GP's uncertainty was **not
perfectly calibrated**. In other words, its confidence statements were not fully
trustworthy as literal probability statements. That matters when someone wants
to say "the GP knew this point was good" or "the GP was sure enough."

So the GP is useful, but its uncertainty should not be treated as automatically
correct just because it comes from a machine-learning model.

### What a non-technical reader should remember

The GP is the model that gives BO its adaptive behavior. It is one of the
reasons BO can look smarter than simple space-filling designs, but it is not
magically reliable in every respect.

---

## 4. qLogEI: the main BO decision rule

**qLogEI** is not a different fitted model from the GP. It is the **rule that
uses the GP** to choose the next batch of experiments.

Very roughly, it asks: "if I run these next points, how much improvement might I
expect over my current best result?" The `q` means it chooses a **batch** rather
than a single next experiment.

### Why it was picked

- It is a standard modern BO acquisition rule
- It is appropriate when experiments are run in batches rather than one at a
  time
- It represents the most direct BO comparator in the matched-budget study

### How it affects the study

qLogEI is the BO arm in the main headline comparison.

Against measured-response argmax in the primary setting, DoE/RSM beat qLogEI by
0.0595 regret. But when the same visited wells are rescored by the hidden best
visited point, that gap shrinks to 0.0158. This is one of the most important
results in the study: much of the headline difference was about **identifying**
the best tested well under noise, not about visiting dramatically better places.

### What a non-technical reader should remember

qLogEI is the main BO method in the paper. It is not "the GP itself"; it is the
GP plus a rule for where to experiment next.

---

## 5. qLogNEI: the noise-aware BO rule

**qLogNEI** is a close relative of qLogEI. It is another BO decision rule that
tries harder to account for observation noise.

If qLogEI asks "where might I improve most?", qLogNEI asks a similar question
but does so in a way that is more careful about noisy measurements.

### Why it was picked

- The project's primary problem includes noisy observations
- If BO is criticized for struggling under noise, a noise-aware BO rule is a
  fairer comparator than qLogEI alone
- It tests whether better noise handling changes the story

### How it affects the study

qLogNEI helps with **identification**. In the primary setting, the noisy winner
was truly the best visited well more often under qLogNEI than under qLogEI.

But it does not erase the entire high-noise disadvantage under measured argmax.
So the study does not reduce to "BO only lost because the wrong BO variant was
used."

### What a non-technical reader should remember

qLogNEI shows that noise-aware BO can improve the BO side of the comparison, but
it does not remove the paper's main point that final scoring rules matter.

---

## 6. TuRBO: a box around where BO may look next

**TuRBO** (trust-region Bayesian optimization) is not a new fitted model and not
a new final-choice rule. It is a **sampling constraint**. After the opening
design, the next batch may only be placed inside a moving box around the
current best guess. That box grows after repeated improvements and shrinks
after repeated failures.

The "best guess" under noise is the visited well with the highest GP posterior
mean, not the luckiest noisy observation.

### Why it was picked

- A reviewer can fairly say unconstrained BO is allowed to roam the whole box
  while classical RSM stays local
- It tests that objection with one intended change: the same qLogNEI rule,
  inside an adaptive box
- It is **not** the same algorithm as walking RSM (screen, CCD, measured
  steepest-ascent path)

### How it affects the study

In the primary noisy 48-well cell, TuRBO matched unconstrained qLogNEI. The
DoE/RSM lead on measured argmax did not go away. So the headline is not an
artefact of BO wandering. Extending the same campaigns to 200 wells also did
not produce a general well-count saving versus relocating RSM at that noisy
cell.

Restart keeps all previous wells. That is a registered deviation from
canonical TuRBO, so the comparison is not handicapped by forgetting.

### What a non-technical reader should remember

TuRBO changes **where** sequential BO is allowed to sample. It does not change
how the campaign is scored, and it is not "RSM with a GP."

---

## 7. One-shot GP: a non-adaptive GP baseline

The study also includes a **one-shot GP** arm. This means all 48 experiments are
chosen up front in one spread-out design, then a GP is fitted afterwards. There
is no sequential updating between rounds.

### Why it was picked

- It separates the value of the **GP model** from the value of **sequential BO**
- It asks whether repeated adaptive rounds are always necessary
- It gives a useful cost comparison, because one-shot designs use only one round

### How it affects the study

On the smooth Hill landscapes, one-shot GP often did very well and could hit the
target in a single round. That means adaptation is not always the key advantage;
sometimes broad, well-spread coverage plus a good model is enough.

But on Hartmann6, which is more deceptive and multimodal, one-shot GP loses to
sequential BO. So the value of adaptation depends on the shape of the problem.

### What a non-technical reader should remember

One-shot GP is in the study to show that the question is not just "classical vs
AI." It also matters whether the method is **adaptive** or **plan-everything-up-front**.

---

## 8. Random search: the sanity-check baseline

Random search is exactly what it sounds like: pick points uniformly at random.

### Why it was picked

- Every "smart" method should beat a simple dumb baseline
- It prevents overclaiming when two sophisticated methods are close

### How it affects the study

Random is clearly worse than the main methods in the primary setting. That helps
show the benchmark is meaningful and that qLogEI is still doing useful search,
even where DoE/RSM wins on the final measured pick.

### What a non-technical reader should remember

Random is not a contender. It is there to prove the benchmark is not trivial.

---

## 9. The most important distinction: model versus final choice

For a non-technical reader, this is the single most important lesson in the
project.

The study does **not** just compare one model against another. It also compares
different ways of turning the same information into one final recipe.

That is why the ranking can flip:

- one rule picks the largest noisy measured value,
- another asks which visited point was truly best,
- another asks the fitted model where the best point should be,
- and another restricts that model-based recommendation to where the data
  actually support it.

The final answer depends not only on the model, but also on **how the model is
used**.

---

## 10. Why these models were picked together

The model set was chosen to make the comparison fair and interpretable.

- The **quadratic** represents classical response-surface practice
- The **GP** represents modern Bayesian optimization practice
- **qLogEI** is the main batch BO decision rule
- **qLogNEI** checks whether noise-aware BO changes the story
- **TuRBO** checks whether forcing BO to stay local changes the story
- **One-shot GP** separates modeling from sequential adaptation
- **Random** is the basic sanity baseline

This combination lets the project ask a sharper question than "which method
wins?" It asks:

- Is the difference about search?
- Is it about identifying the best tested recipe under noise?
- Is it about extrapolating with the fitted model?
- Is it about needing many sequential rounds?
- Is it about searching locally versus over the whole box?

That is why the paper's message is not a simple BO-versus-RSM verdict.

---

## 11. The simplest summary

If you remember only four lines, remember these:

1. The **Hill landscape** is the simulated world, not a competing method.
2. The classical arm fits a **quadratic**; the BO arm fits a **Gaussian process**.
3. qLogEI and qLogNEI are **decision rules that use the GP**, not separate
   worlds or separate datasets. TuRBO only restricts **where** those rules may
   look next.
4. The study's conclusion changes a lot depending on **how the final recipe is
   chosen** from the same 48 tested wells.
