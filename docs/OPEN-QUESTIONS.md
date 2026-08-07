# OPEN QUESTIONS — ONE PLACE FOR EVERYTHING NEEDING A DECISION

**This is the only file that collects questions. Nothing gets asked anywhere else.**

Updated after every completed piece of work. Last updated: **2026-08-07 — Person B's lane is code-complete. 233 tests. HARD BLOCKED on Q1.**

- **[A]** = needs Person A
- **[YOU]** = needs Alan
- **[EITHER]** = whoever gets there first

Status: 🔴 blocking · 🟠 will block soon · 🟡 answer before writing the paper · ⚪️ noted, proceeding on a stated default

---

## 🔴 BLOCKING — work stops without these

### Q1 [A] · The made-up data generator is the critical path for both lanes

Nothing else matters as much. Waiting on it: A's own pre-flight check, A's Experiment 2, A's Experiment 3, and B's Experiment 4. **Every other item on this page is smaller than this one.**

Needed: the biphasic oracle with the depth inversion, feasibility scan, acceptance checks, instance hashing, and cached optima.

> ### ⛔️ THIS IS NOW HARD-BLOCKING. B has run out of work.
>
> **Person B's lane is code-complete.** Every module is built and tested, and Experiment 4 is wired end to end and verified against a stand-in landscape. **There is nothing left for B to build that does not require A's oracle.**
>
> **What A needs to provide.** The oracle just has to answer three questions — nothing more:
>
> ```
> x_star          -> (d,)                  where each ingredient's response peaks
> truth(X)        -> (n, 1)                the NOISELESS value. Scoring only, never fitting.
> observe(X)      -> ((n, 1), (n, 1))      a noisy measurement and its noise estimate
> ```
>
> That is the whole interface, and it is **structural** — A's class does not need to import or inherit anything from B's code. If it has those three, it drops straight in. It is written down as `boec.e4.Oracle`, and `boec.campaign.Evaluator` is the matching two-method version for the loop.
>
> **A stand-in with exactly this shape is already in `tests/test_e4.py`.** A can read it as a worked example of what is expected, and B's tests use it to prove the pipeline runs — so the moment A's real one arrives, E4 produces numbers the same hour.
>
> **The mechanism has been confirmed to fire on the stand-in**: trained on a corner, the traditional fit points outside what it has seen and overshoots, and hiding more of the space increases the overshoot. That is not proof it will happen on A's real landscapes — that is exactly what PF1 measures — but it does prove the experiment is capable of detecting the effect if it is there.

---

## 🟠 WILL BLOCK SOON

### Q2 [A] · Who owns `designs.py`? B has written it — say keep / replace / co-own

Specced as A's. B wrote it because A's pre-flight check cannot run without it and that check decides whether B's experiment exists at all.

What's there: the 48-run pattern (32 corners + 12 axial + 4 centre), screening designs for A's Experiment 2, sub-box scaling, face-centred default, 28 tests.

**PF1 is no longer blocked on the missing CCD — only on your oracle.** This question is about ownership and duplicated effort, not about whether the file exists.

**If A has already started a competing copy, tell B now.** B's original spec said "ask, don't fork" — this is the ask, retrospectively, with working code attached.

### Q3 [A] · Standard test-function wrappers — still wanted for the swap test

The plan is explicit that B builds the loop against Branin/Hartmann6/Ackley first and swaps the real oracle in later, as a **deliberate test of whether the pieces really do swap cleanly**.

**Update:** B's `campaign.py` is already built against an `Evaluator` protocol with that shape. A's wrappers (and later the oracle) should implement the same interface so the swap test is still meaningful. Without them, B's tests use stand-in callables — fine for unit tests, weaker as a contract rehearsal.

### Q4 [A] · Confirm the `Evaluator` interface matches what B coded

B implemented exactly what Doc 1 §2 states:

```
Evaluator.evaluate(X: (n, d)) -> tuple[Y: (n, m), Yvar: (n, m) | None]
```

**This is now in `campaign.py` as a Protocol, with tests.** One sentence of confirmation still matters — if A's version differs, adapters get written once rather than after E2 starts.

---

## 🟡 ANSWER BEFORE THE PAPER

### Q5 [A] · The acquisition method assumes noiseless measurements. Ours are noisy.

**This is the most substantive technical question found so far.**

The spec mandates `qLogEI`, which needs "the best value seen so far". But our measurements are deliberately noisy, and the best of 48 noisy measurements is systematically flattering — the winner is partly whichever point drew lucky noise. At the higher noise level this is not a rounding error.

BoTorch ships `qLogNoisyExpectedImprovement` for exactly this case. **Its own documentation says it exists because the standard version's assumption "would require noiseless observations".**

The spec's stated reason for choosing `qLogEI` is numerical stability — a different concern entirely. So this looks unconsidered rather than decided.

**Both are implemented. The spec's choice is the default and I have not silently deviated.** This is a joint decision because Experiment 2's fairness rules say explicitly: *do not tune your own method while leaving the baselines at defaults.* Switching could be read either as a correctness fix or as exactly that.

**Options:** (a) keep `qLogEI` as specced and state the bias as a limitation; (b) switch to `qLogNEI` and justify it as matching our own observation model; (c) run both and report the difference — cheap, since compute turned out ~10× cheaper than estimated.

*My lean: (c) then (b). But it is A's call as much as mine.*

### Q6 [A] · Stepwise selection criterion for the descriptive third-order model

Listed in Doc 1 as an explicit "ask rather than assume". **Proceeding with backward elimination on p-values** unless told otherwise; the choice will be recorded in config. Descriptive only — no error bars are computed from it, ever, so the stakes are lower than they look.

### Q7 [YOU] · Author order, and whether the code can be released publicly

Doc 2 §A.6 lists these as open. Neither blocks building. Both block posting the preprint.

### Q8 [A] · The `Yvar` floor value

A owns the noise policy. The spec says imputed noise gets "a floor" and never gives a number. I used `1e-8` in a throwaway timing script; that is **not** a decision and shouldn't be inherited.

---

## ⚪️ NOTED — proceeding on a stated default

### Q10 · The two pre-registered numbers ✅ locked

512 candidate points; threshold at the within-instance top 20%. In `configs/experiment/e4.yaml`, in git, dated, before any result existed. **Do not change these after seeing results** — bump the version and say so in the paper if they must move.

### Q11 · Repo layout and the first commit

Nothing is committed yet. The first commit sets the layout for both people, which is arguably a joint decision. Current shape is the spec's §8 layout with package name `boec`.

**[YOU]:** happy for me to commit, or do you want to review first?

---

## ✅ CLOSED

| | Question | Answer |
|---|---|---|
| **C1** | What does `observation_noise=True` do at unrun points? | **Silently averages all training noise and applies it flat.** Source carries a `TODO: be smarter here`. Never used; we supply noise explicitly. |
| **C2** | Units for supplied noise? | **Standardized, not raw** — unlike training noise. Off by 161× otherwise. Handled in one place. |
| **C3** | Does `Normalize` without bounds learn from the data? | **Yes.** Verified. Always pass explicit bounds. |
| **C4** | Discrete-candidate function name? | `optimize_acqf_discrete(acq_function, q, choices, ..., inequality_constraints=None)`. |
| **C5** | Does batch selection cluster proposals? | **No.** It conditions on each pick before making the next, which satisfies the spec's "never top-q" rule. Verified in source and tested. |
| **C6** | Is the grid too slow for the full plan? | **No — ~10× faster than estimated.** Nothing needs shrinking. |
| **C7** | Does the 48-run pattern arithmetic work? | **Yes, exactly.** 32 + 12 + 4. Quality claim verified from first principles, not a lookup table. |
| **C8** | Face-centred vs rotatable CCD in the sub-box? | **Face-centred.** Rotatable axials leave the hard boundary (~2.38 vs 1.0 at d=6). Coded default + test. |

---

## Where B is up to — CODE COMPLETE

| Module | Plain English | Tests |
|---|---|---|
| `metrics.py` | "You promised X — what did we actually get?" **A imports this.** | 10 |
| `rsm.py` | The traditional curve fit, fairly represented, plus the descriptive stepwise variant | 33 |
| `designs.py` | Which 48 experiments to run ⚠️ *ownership open, Q2* | 28 |
| `surrogate.py` | The model that knows when it is guessing. All five silent traps caged | 24 |
| `optimizers.py` | What to try next — free search and fixed-menu | 30 |
| `parametric.py` | What a working scientist would try without knowing the answer | 15 |
| `discrimination.py` | The actual measurement, including the null that must be beaten | 27 |
| `campaign.py` | Propose, measure, learn, repeat. Saves its place | 27 |
| `runner.py` | Runs the whole grid, skips what is already done | 24 |
| `e4.py` | The experiment itself, wired end to end | 15 |
| | **Total** | **233** |

**Runway remaining: none.** Everything that does not need A's oracle is finished. Experiment 4 is wired end to end and verified against a stand-in landscape; only the landscape itself is missing.

**What happens the moment the oracle lands:**

1. **Drop it in — no code changes needed anywhere**, provided it answers the three questions in Q1. The interface is structural, so A's class imports nothing from B's.
2. **Run PF1**, blocked since day one, which decides whether E4 has anything to measure at all.
3. **Run E4** across every landscape and all four hiding levels.
4. On measured timings, the whole thing finishes **well under an hour**.

**Everything still open above is a decision or A's data lane — not a missing B module.**
