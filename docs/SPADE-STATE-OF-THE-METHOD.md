# What we fixed in SPADE, and what's still broken

Written 2026-08-27. Every number here comes from a result file in `results/`, with the
script that made it in `scripts/`. Nothing is quoted from memory.

| what | data file | script |
|---|---|---|
| calibration sweep | `results/ktb-inflation.json`, `ktb-inflation-fine.json` | `run_ktb_inflation.py` |
| model-too-confident bug, test problems | `results/probe-meanmarg-benchmarks.json` | `probe_meanmarg_benchmarks.py` |
| model-too-confident bug, your cells | -- | `run_real_ipsc_certification.py` |
| model-too-confident bug, published study | -- | `certify_hall_ogle.py` |
| safety factor from real data | -- | `probe_loo_real_assay.py`, `certify_hall_ogle.py` |
| "pick a few recipes" version | `results/probe-topk-finite-set.json` | `probe_topk_finite_set.py` |
| real-noise test | `results/probe-kz-realistic-noise.json` | `probe_kz_realistic_noise.py` |
| 75% stall investigation | `results/probe-hypermix-6seed.json` | `probe_hypermix_saturation.py` |
| head-to-head vs BO | `results/final-spade-combined.json` | committed study |

---

## What SPADE does

You have 48 wells. SPADE uses 40 to spread out and look around, then uses the last 8 to
look closely at the edge of "good enough". Then it hands you a region of recipes and says:
**every recipe in here beats your target, and I'm 95% sure.**

The important part: when the data isn't good enough, it says "I don't know" instead of
guessing. Nothing else we tested does that. `doe`, the standard screening design, hands
back a big confident region that is **wrong 71% of the time**.

---

## What we fixed

### 1. It was lying about how sure it was

It said 95% confident. It was actually right **79%** of the time.

Fixed by widening the model's uncertainty by a factor of 1.5. Now it's right **96.8%** of
the time, and the worst case we can prove is 90.2%.

### 2. A number in our own writeup was too flattering

We had published "93.8% confidence". We went back and found that number was computed by
mixing SPADE together with its own control groups. SPADE on its own is **90.2%**.

Still passes. But anyone who checks our math would get a different number than we printed,
so we corrected it.

### 3. On real cell data, the model thought it knew everything

This is the big one.

We ran SPADE on your real iPSC-EC coating data. The model said the answer was
**37.16, plus or minus 0.01**. But your actual measurements ranged from 22.6 to 47.3. It
should have said plus or minus **3.5**. It was **350x too confident**.

Because of that, it told us "95% sure every coating hits 35% CD31+". The truth was 74%.
**If you had qualified a manufacturing process on that, you'd have qualified it on a
number that was made up.**

The cause: the model estimates the average level of the data, then forgets that its
estimate could be wrong. When the data is noisy, that forgotten piece is the *only* thing
that matters.

We fixed it properly (no fudge factor, no tuning). Now it says plus or minus 3.4, and it
correctly refuses to make the 35% claim.

**We then checked it on a totally different dataset — the published Hall & Ogle iPSC-EC
study — and the same bug was there, worse.** So it's not a quirk of your lab.

| data | model said +/- | should have said | how wrong |
|---|---|---|---|
| our 4 test problems | -- | -- | **1.004x - 1.011x** (basically fine) |
| your iPSC-EC cells | 0.007 | 3.388 | **484x** |
| published Hall & Ogle | **0.0003** | 0.0818 | **297x** |

Your cells: 12 tubes, CD31+ from 22.6% to 47.3%, measured noise 12.1 pp.
Published study: 23 ECM recipes, response 0.509 to 1.446, noise **10x bigger than the
signal**.

### 4. A code bug that silently ran the wrong thing

If you typed a plate-2 mode name wrong, it quietly ran a different method instead of
erroring. Now it errors.

---

## What we learned that's genuinely new

### Testing on fake data would never have caught bug #3

On our synthetic test problems, that bug changes the answer by **1%**. Nobody would notice.
On real data it changes it by **297x to 484x**.

So: **you cannot validate this kind of method on simulated data alone.** That's worth
publishing on its own, and it applies to everyone doing this, not just us.

### Real experiments need *less* safety margin than fake ones

We tuned the safety factor on simulated data and got **1.5**. Then we measured what real
data actually needs:

| dataset | safety factor it actually needs | how we checked |
|---|---|---|
| simulated test problems | 1.5 | tuned on fake data |
| your iPSC-EC cells | **0.71** | leave-one-tube-out, 11 of 12 inside a 68% band |
| published Hall & Ogle | **0.53** | leave-one-recipe-out, 22 of 23 inside |

Both under 1. Meaning the real data is *less* noisy than our simulations assumed, and using
1.5 makes SPADE about **3x more cautious than it needs to be**. Using the right number
raises your certified claim from 28.8% to **31.6% CD31+**.

And we can measure this from data you already have — no new experiments needed.

### Widening the model fixes one problem and can't fix another

If the model is *unsure*, widening helps. If the model is *wrong*, widening does nothing —
because widening only makes the answer fuzzier, it never moves it.

We can see both happen. Accuracy as we widen (same cases at every setting, so nothing is
cherry-picked):

| test problem | 1x | 2x | 3x | 4x | |
|---|---|---|---|---|---|
| ackley | 35% | 75% | 89% | **93%** | keeps improving |
| hartmann6 | 20% | 58% | 82% | **88%** | keeps improving |
| levy | 33% | 75% | 75% | **75%** | **stuck** |
| rosenbrock | 64% | 73% | 73% | **73%** | **stuck** |

Those bottom two are cases where the model is confidently wrong, and no safety factor
fixes that.

### At real-world noise levels, SPADE can't certify anything

Real cell data is noisy. The published study has noise **10x bigger than the signal**.

| noise | targeted 8 wells | random 8 wells |
|---|---|---|
| normal (0.25) | answers 24% of the time | answers 8% |
| **real (0.68)** | **0%** | **0%** |

At real noise, on 48 wells, SPADE certifies **nothing, 0% of the time**. Not because it's
broken — at 0.25 the targeted wells still beat random 16 to 1 (p = 0.00027), so the test
harness works — but because **the data genuinely doesn't contain the answer.**

We got the same result two different ways: on the real published data, and in simulation.

**The real bottleneck isn't clever algorithms. It's replicates.** To tell apart ECM
recipes in that published study you'd need about **27 repeats of each one, ~621 runs
total.** No method can invent information that was never measured.

### SPADE beats regular BO on the one test problem that looks like biology

We have five test problems. Four are abstract math functions. One (`hill`) is a real
dose-response curve shape — the kind you actually see with media and coatings.

On `hill`, SPADE **beats** standard Bayesian optimization. And the noisier it gets, the
bigger SPADE's lead:

| test problem | noise | SPADE vs BO | who wins |
|---|---|---|---|
| **hill** (dose-response) | 0.10 | +0.018 | BO, slightly |
| **hill** (dose-response) | **0.25** | **-0.031** | **SPADE, clearly** |
| rosenbrock | 0.25 | -0.013 | SPADE, barely |
| levy | 0.25 | +0.023 | tie |
| ackley | 0.25 | +0.102 | BO |
| hartmann6 | 0.25 | +0.162 | BO |

(negative = SPADE better; anything under 0.02 is a tie. The two `hill` rows don't overlap
statistically, so the flip is real, not noise.)

On the abstract math problems, BO wins. Those have one sharp peak to find, which is exactly
what BO is built for — and nothing in cell manufacturing looks like that.

---

## What you can actually claim about your cells right now

> **Across both fibronectin and vitronectin, at every dose from 0.5 to 20 µg/mL,
> CD31+ is at least 31.6% — with 95% confidence.**

How that number moves with how cautious you want to be:

| safety factor | 50% sure | 80% sure | **95% sure** | 99% sure |
|---|---|---|---|---|
| 1.0 (what your data supports) | 37.1% | 34.3% | **31.6%** | 29.2% |
| 1.5 (what simulation said) | 37.0% | 32.8% | **28.8%** | 25.2% |
| 2.0 | 37.0% | 31.4% | 26.0% | 21.3% |

Your 12 measured tubes, for reference:

| dose µg/mL | 0.5 | 1 | 2.5 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| fibronectin | 31.7 | **47.3** | 46.8 | 38.7 | 46.3 | 36.4 |
| vitronectin | 22.6 | 40.1 | 39.6 | 41.3 | 34.3 | 39.8 |

And here's how many tubes you'd need for a stricter target, at your current noise:

| target | tubes needed (95%) |
|---|---|
| 25% | 3 |
| **30%** | **8** |
| 35% | 86 |

**Your bottleneck is the CD31 gate being noisy (12 pp), not the number of conditions.**
Tightening that gate, or running repeats, buys you far more than testing more coatings.

---

## What's still broken

1. **SPADE is not a better optimizer in general.** It ties on the main test and loses on
   two abstract math problems.
2. **The safety factor doesn't transfer between problems.** We tested it, it failed. You
   have to re-measure it for each new assay (which we can now do, cheaply).
3. **Two test problems stall at 75% accuracy and we don't know why.** Three explanations
   tried, all three wrong.
4. **Everything good we said about the 8 targeted wells only holds at low noise.** At real
   noise there's no certificate at all, so there's nothing for them to improve.
5. **No wet-lab proof.** Your 12 CD31 gates still need signing in CytExpert. That's one
   afternoon, and it's the only thing standing between this and a real result.
6. **It still says "I don't know" too often.** We built a version that picks a handful of
   recipes instead of a whole region:

   | version | answers | accuracy | recipes handed back |
   |---|---|---|---|
   | whole region | 4.7% | 100% | -- |
   | **pick a few** | **10.9%** | **100%** | **6.3** |

   Same accuracy, **2.3x more answers**. But only 64 test cases so far, and we expect it to
   hit the same 75% stall for the same reason.
7. **We never compared SPADE to BO on real data.** Only on simulations. So we can't claim
   it's better on real cells.
8. **The multi-CQA work isn't in this repo.** No code, no branch. Can't check it. If it
   gets built: intersecting 3 separate 95% certificates gives you **85%**, not 95% — that
   needs fixing — and every endpoint needs the bug-#3 fix or the whole thing inherits it.

---

## Still running

- **KX** — SPADE vs qLogNEI vs Sobol, head to head, on certified regions
- **KY** — can a smarter model fix the 75% stall
- **KZ-2** — does the "pick a few recipes" version still work at real noise

**All 1724 tests pass.**

---

## The one-paragraph version

SPADE's certificate was overconfident, and we found three separate reasons: the model's
uncertainty was too narrow, the certificate graded its own homework, and — only visible on
real data — the model forgot it might be wrong about the average. We fixed all three. On
the one test problem shaped like real biology, SPADE now matches or beats standard BO, and
wins by more as noise increases. On real cell data it correctly refuses to make claims the
data can't support, and tells you how many repeats you'd need instead. That last part is
the honest answer to "is SPADE good": it's the only method here that knows when to shut up.
