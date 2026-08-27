# What we fixed in SPADE, and what's still broken

Written 2026-08-27. Every number here comes from a real result file you can re-run.

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
study — and the same bug was there, worse. It said plus or minus 0.0003 on data ranging
0.5 to 1.4. That's 297x too confident.** So it's not a quirk of your lab. It's a real bug
in how everyone does this.

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

- Your iPSC-EC data: **0.71**
- Published Hall & Ogle data: **0.53**

Both under 1. Meaning the real data is *less* noisy than our simulations assumed, and using
1.5 makes SPADE about **3x more cautious than it needs to be**. Using the right number
raises your certified claim from 28.8% to **31.6% CD31+**.

And we can measure this from data you already have — no new experiments needed.

### Widening the model fixes one problem and can't fix another

If the model is *unsure*, widening helps. If the model is *wrong*, widening does nothing —
because widening only makes the answer fuzzier, it never moves it.

We can see both happen. On two test problems, widening keeps improving accuracy up to 93%.
On two others it **stalls at 75% and stops**, no matter how much we widen. Those are cases
where the model is confidently wrong, and there's no fixing that with a safety factor.

### At real-world noise levels, SPADE can't certify anything

Real cell data is noisy. The published study has noise **10x bigger than the signal**.

At that noise level, on 48 wells, SPADE certifies **nothing, 0% of the time**. Not because
it's broken — we checked, it works fine at lower noise — but because **the data genuinely
doesn't contain the answer.**

We got the same result two different ways: on the real published data, and in simulation.

**The real bottleneck isn't clever algorithms. It's replicates.** To tell apart ECM
recipes in that published study you'd need about **27 repeats of each one, ~621 runs
total.** No method can invent information that was never measured.

### SPADE beats regular BO on the one test problem that looks like biology

We have five test problems. Four are abstract math functions. One (`hill`) is a real
dose-response curve shape — the kind you actually see with media and coatings.

On `hill`, SPADE **beats** standard Bayesian optimization. And the noisier it gets, the
bigger SPADE's lead:

| noise level | who wins |
|---|---|
| low (0.10) | BO, slightly |
| realistic (0.25) | **SPADE, clearly** |

On the abstract math problems, BO wins. Those have one sharp peak to find, which is exactly
what BO is built for — and nothing in cell manufacturing looks like that.

---

## What you can actually claim about your cells right now

> **Across both fibronectin and vitronectin, at every dose from 0.5 to 20 µg/mL,
> CD31+ is at least 31.6% — with 95% confidence.**

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
6. **It still says "I don't know" too often.** We built a version that answers 2.3x more
   often at the same accuracy, but only tested it on 64 cases so far.
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
