# ESTIMAND EVALUATION — were rule A and rule C the right pair?

**Commissioned question:** the estimand choice determines the verdict, both rules were
arrived at by circumstance rather than design, and neither was selected from a considered
set. Should they have been?

**Method.** Every claim below was verified against code, commits and records in this
clone. Nothing is carried from summary. Where a record and a memory disagreed, the record
won; three claims in the commissioning brief did not survive that check and are corrected
in §0.

**Constraint honoured:** no new campaigns. One analysis script was added,
`scripts/estimand_evaluation.py`, which reads committed artefacts only. Its output is
`results/estimand-evaluation.log` / `.json`.

**Verdict, stated up front:** §5 concludes **the choice is under-determined among several
defensible rules** — the third of the three permitted verdicts, and the least comfortable.
But not for the reason the brief anticipated. The binary framing is **already false by
this project's own Q35**, and a third rule computable from stored data returns a **mixed**
verdict where both existing rules return total ones.

---

## §0 — THREE PREMISES IN THE BRIEF THAT DID NOT SURVIVE VERIFICATION

Recorded first because the rest of the document depends on them.

| brief's premise | what the records show | verdict |
|---|---|---|
| *"Rule C gives BO the win everywhere"* | Q35 scored the DoE arm's recommendation **constrained to the region it explored**, which is what classical practice prescribes: **0.1169 against BO's 0.1232** at the registered primary cell. `docs/CLAIMS.md` already states *"The reversal disappears."* | ❌ **False, and already known to be false.** Rule C gives BO the win only in its *unconstrained* form, which Q35 supersedes. |
| *"32 of 32 cells"* | I could not reconstruct this denominator from any artefact. The rule-A/rule-B reversal is documented at **4 of 4** cells (Q28); Q34's cell 5−3 contrast holds at 4 of 4; Q35's three scorings cover 4 cells. | ⚠️ **Unverifiable as stated.** The direction is well supported at four cells. The "32" is not traceable and should not be written. |
| *"at 200 evaluations… random reaches a 0.05 target in 6 evaluations while qLogEI takes 12.5"* | Not located in `q52-floor.json`, `q52-flatten.json` or either log. The *mechanism* it illustrates is real and documented (Q52 §1.2, concentration is protective under rule A) and is confirmed independently in §2.2 below. | ⚠️ **Numbers not verified.** The underlying claim is supported by other evidence; these specific figures should not be quoted. |

**Q35's reasoning stands.** Part 6 made this conditional on the provenance trace not showing
it rested on something false. It does not. Q35's fidelity gate refits the stage-2 surface
from stored measurements and reproduces the arm's own predicted optimum at max |Δ| exactly
0.0 across all 200 runs.

---

## §1 — PROVENANCE

### 1.1 Rule A — best observed

**First implemented:** `678972c`, **2026-08-10 13:25**, *"E3 and the E2 machinery; E4
reproduced; and E2's first scoring was wrong."* Introduces `reported_best_curve` in
`src/boec/diagnostics.py`. The same commit registers `regret_on:
noiseless_value_at_selected_point` in `configs/experiment/e2.yaml` — and **that is the
whole of the registration at that moment.** The scoring block was five lines:

```yaml
scoring:
  regret_on: noiseless_value_at_selected_point
  primary_endpoint: simple_regret_at_budget
  secondary_endpoint: auc_post_initialisation
  report: [median, iqr]
```

There is no `selected_point` key. Which point gets scored is decided by code, not by the
pre-registration.

**Was it registered before use? No. First use precedes first registration.**

| time (2026-08-10) | event | commit |
|---|---|---|
| 13:25 | scoring machinery lands; selected point undefined in the config | `678972c` |
| 13:53 | *"E2's first two runs are void"* — **two E2 runs have already scored under rule A** | `fbb98e9` |
| 15:23 | Q20 §3 flags the rule as unregistered, *"written while the grid is still running, deliberately"* | `d289e7d` |
| **15:34** | **`selected_point` block added — rule A named for the first time** | `9d6fd1d` |
| 16:09 | *"E2 COMPLETE: in the pre-registered primary cell, BO LOSES to the DoE pipeline"* | `0aeee09` |

Rule A was named **35 minutes before the result it governs was reported**, after two void
runs had used it and while the surviving grid was mid-flight. To the project's credit the
naming commit says so in the config itself, in capitals:

> `# Both readings are defensible and REPORTED-BEST IS THE MORE GENEROUS ONE, so it is`
> `# named rather than inherited.`

**Q20 §3, verbatim** — the flag that produced that line:

> **`regret_on: noiseless_value_at_selected_point` does not define the DoE arm's selected
> point.** For every other arm the selected point is the observed argmax. The DoE arm's
> *output* is the stage-4 confirmation recipe, and `run_e2.py:120` scores it as
> reported-best over all 48 — so the confirmation counts only if it happens to be the
> observed argmax, which `results/doe-arm.log` says it is not, in 100% of runs at both
> noise levels. **This is not obviously wrong** — a practitioner does walk away with the
> best recipe they saw — but it is the more generous of two defensible rules, and it is
> unregistered. Say which one it is.

**What happened next:** it was said, eleven minutes later, in `9d6fd1d`. The naming was
prompt and honest. What it was *not* was a choice between alternatives.

**Was rule A ever compared against an alternative before becoming primary?** **No. It
became primary by being the only thing implemented.** Rule B was not computed until Q28
(`06df4f1`, 08-10 23:44) — **eight hours after** E2 was reported complete and rule A was
the registered primary. The 15:34 commit names rule A and describes the alternative in a
comment; it does not measure it.

### 1.2 Rule C — symmetric, each method at its own model's recommendation

**Registration:** `b91a395`, **2026-08-11 10:12**, *"Q29 PRE-REGISTRATION: the symmetric
comparison, fixed before the run."* Verbatim:

> **Rule C — symmetric.** Each method is scored at the point **its own model recommends**,
> evaluated on `truth()`:
> - **DoE** → the stage-4 confirmation recipe (the constrained argmax of its fitted
>   second-order surface). Already computed.
> - **BO** → the **argmax of the GP posterior mean** over the same box. **E2 never recorded
>   this**, which is why this needs a run rather than a re-analysis: `results/e2-grid.json`
>   stores summary rows only, no visited points.

**What prompted it, as recorded:** Q28's finding that every cell reverses sign between
rule A and rule B, plus the judgement that rule B *"is not like-for-like and flatters BO
for exactly the reason rule A flatters DoE."* Rule C is explicitly constructed to remove
that asymmetry.

**Before or after the confirmation-run observation?** **After, and it says so.** Q28 records
the observation — the DoE arm pays one of 48 for a confirmation point that is not its
observed argmax in 100% of runs — and rule C is the response to it. The sequence is
recorded rather than obscured.

**Conduct.** Rule C is the best-conducted of the three by a distance. Registered before
running; prediction stated with its mechanism; falsification condition named (*"DoE matching
or beating BO under rule C"*); and a three-branch decision rule fixed in advance, including:

> **Either way rule A stays the registered primary** (Q20/`e2.yaml`). Rule C is a declared
> secondary. **This entry does not re-designate the headline**, because the headline cannot
> be chosen by the person who ran the tiebreak.

### 1.3 Rule B — the stage-4 recipe. **Dropped after its output was seen.**

**Definition, verbatim from Q28:**

> **Rule B — the stage-4 recipe** | the point the arm *produced* | `doe.py`: *"The published
> study evaluated its predicted optimum. So does this."* Stage 4 exists for exactly this
> reason

Rule B scores **DoE at its model's recommendation and qLogEI at its best measurement.**

**What it produced** (Q28's table — B's clone figures, superseded in magnitude by T1.4a but
not in direction):

| cell | rule A | rule B |
|---|---|---|
| d=6 σ=0.25 | −0.0708 | **+0.2497** |
| d=6 σ=0.10 | +0.0042 | **+0.3450** |
| d=8 σ=0.25 | −0.0321 | **+0.2482** |
| d=8 σ=0.10 | +0.0015 | **+0.3170** |

**Why it was dropped — recorded reason:** asymmetry. Verbatim:

> It scores **DoE by its model's recommendation and qLogEI by its best measurement.** Those
> are different standards, and the asymmetry runs entirely against DoE.

> **Under Rule B as computed, BO wins everywhere by a wide margin — and that comparison is
> not evidence**, because the comparator was held to an easier standard.

**Was it dropped before or after anyone saw what it produced? AFTER. This is selection and
it is reported as such, per the brief's instruction.**

The numbers and the rejection appear in the **same entry**, `06df4f1`. Rule B was computed,
seen to favour BO everywhere, and rejected in the same breath.

**Three things keep this from being a straightforward indictment, and one thing does not:**

1. The rejection reason is **principled and outcome-independent**. "Different standards for
   the two arms" would be a defect whichever direction it pointed.
2. It was rejected in the direction **against** the project's then-standing headline — rule
   B favoured BO, and the project's headline at the time was that BO *loses*. Discarding a
   result that would have rescued the more flattering story is the opposite of the usual
   selection worry.
3. The record **flags its own incentive**, unprompted:

   > **Registering it before running is not optional.** Rule A is already known to favour
   > DoE and asymmetric Rule B is already known to favour BO, so whoever runs the symmetric
   > version knows in advance which direction each error points.

4. **But the sequence is still selection.** Three rules were available; one was computed,
   its output inspected, and then eliminated. Had rule B been symmetric-but-inconvenient it
   is not knowable from the record whether the same scrutiny would have applied. **The
   write-up must say that rule B was computed before it was rejected**, and not present the
   A/C pair as though B were rejected on inspection of its definition alone.

### 1.4 The letters — accumulated, not assigned

| letter | first named | commit |
|---|---|---|
| A and B | together, in Q28 | `06df4f1`, 08-10 23:44 |
| C | in Q29, the next morning | `b91a395`, 08-11 10:12 |

**Not one commit.** No entry assigns the scheme; the letters accrete as the rules are
discovered. **They map to nothing meaningful** — not to chronology of use (rule A was used
first but so was its code, and B was never used in production), not to symmetry (A and C are
symmetric, B is not), not to preference. They are arbitrary labels, and their arbitrariness
is mildly harmful: "rule B" now denotes a rejected estimand that nonetheless appears in
tables throughout `OPEN-QUESTIONS.md`, which is a reading hazard.

There is also a **numbering collision** already recorded at the top of the file: two sessions
used "Q29" for different questions within eleven minutes.

---

## §2 — THE TWO SURVIVORS, INTERROGATED

### 2.1 What each measures, without using its name

- **Rule A measures** *the true value of the single best-scoring condition the experiment
  physically ran* — i.e. what a practitioner keeps if they walk away with their best plate.
- **Rule C measures** *the true value of the condition the method's fitted model names as
  best* — i.e. what a practitioner runs next if they believe the model.

Both sentences were easy to write, which by the brief's own diagnostic is a good sign for
both. Neither rule is incoherent. The problem is not that either is meaningless; it is that
they are answers to different questions and nothing in the project says which question the
paper is asking.

### 2.2 The known failure of rule A — **and it is worse than the brief supposed**

Computed in `scripts/estimand_evaluation.py` §1 from `results/q52-floor.json` (planted
space-filling design, 25 instances, budgets 24/48/96/192/384, all four cells).

| cell | n=24 | n=48 | n=96 | n=192 | n=384 | rule A minimises at | 384 − minimum, paired |
|---|---|---|---|---|---|---|---|
| **d=6 σ=0.25** (primary) | **0.1219** | 0.1330 | 0.1292 | 0.1291 | 0.1292 | **n=24** | +0.0073 [+0.0019, +0.0132] |
| d=6 σ=0.10 | **0.0432** | 0.0540 | 0.0593 | 0.0684 | 0.0746 | **n=24** | +0.0314 [+0.0281, +0.0348] |
| d=8 σ=0.25 | **0.1214** | 0.1324 | 0.1270 | 0.1334 | 0.1279 | **n=24** | +0.0066 [+0.0008, +0.0130] |
| d=8 σ=0.10 | **0.0425** | 0.0562 | 0.0622 | 0.0733 | 0.0718 | **n=24** | +0.0293 [+0.0247, +0.0342] |

**Rule A minimises at the smallest budget tested, in all four cells, and gets worse with
more budget with the CI clear of zero in all four.**

Rule C over the same range, **reported in full including the cell that does not suit the
argument**:

| cell | rule C, n=384 − n=24 | |
|---|---|---|
| d=6 σ=0.25 | −0.0122 [−0.0265, +0.0046] | improves, CI covers zero |
| d=6 σ=0.10 | +0.0003 [−0.0085, +0.0087] | null |
| d=8 σ=0.25 | −0.0032 [−0.0181, +0.0118] | null |
| **d=8 σ=0.10** | **+0.0214 [+0.0156, +0.0277]** | **worsens, CI clear of zero** |

So rule C is **not** immune: at d=8 σ=0.10 it degrades with budget too, significantly. The
contrast between the rules is therefore **3 of 4 cells, not 4 of 4** — rule A degrades
everywhere, rule C degrades in one cell. The direction of the argument survives; its
strength is one cell weaker than a summary would suggest.

**Answering the brief's question directly:**

> **At what budget does rule A stop measuring optimization and start measuring sampling
> luck?** Between **24 and 48**, at every cell. The grid's resolution cannot localise it
> more finely, but it is bracketed above by 48.
>
> **Is 48 above or below it? ABOVE.**

The brief states the consequence, and it is the correct one:

> **If above, rule A was already measuring luck in the main grid — and that is a serious
> finding about the registered primary.**

**Scope, stated rather than silent.** This curve is a **static space-filling** family, not
qLogEI. Q52 §1.2 established that concentration is protective under rule A — clustered
competitors gave 0.0144 against space-filling's 0.1226, 8.5× lower — so an **adaptive** arm's
crossover is *later* than this one. Therefore:

- For `random`, `sobol`, `lhs` — **three of E2's seven arms** — this is close to exact, and
  rule A was measuring luck at the registered budget.
- For `qlogei`, `qlognei`, `coord` the crossover is later and its position is **not
  measured**. It cannot be measured without campaign data that is not stored (§3).
- For `doe`, whose 47 of 48 points are a fixed screen plus CCD, the static result is the
  closer analogue.

**This does not mean rule A is invalid.** "The best plate you actually ran" remains a real
quantity a practitioner keeps. It means rule A is **not a measure of search quality at
budget 48**, and the paper cannot use it as one without this qualifier in the same sentence.

### 2.3 The known weakness of rule C — **it is not defined for most of the benchmark**

**How are `random`, `sobol` and `lhs` scored under rule C? They are not.** `docs/RESULTS.md`
states it plainly: *"No rule C exists for these arms. `e2-grid.json` stores reported-best
only."* Q34's factorial covers exactly two designs — DoE and BO — across four recommended
cells. `coord` has no surrogate either and is likewise absent.

**Was a model fitted to them post hoc?** **No.** But the machinery exists and is already
used elsewhere: Q34's cells 5 and 6 fit *the other arm's* surrogate to the same collected
data (`build_gp(X_doe, …)`, `fit_second_order(X_bo, …)`). Nothing but campaign data prevents
the same being done for the static arms — and campaign data is not stored (§3).

**Consequence, and it is structural:** rule A scores **7 of 7** arms; rule C scores **2 of
7**. They are not two conventions over one benchmark. They are two conventions over
different benchmarks, and the smaller one silently excludes every arm that has no model —
including `lhs`, the arm Q48/Q50 showed to be BO's closest competitor under rule A. **Any
sentence comparing "the verdict under rule A" with "the verdict under rule C" is comparing
across a changed arm set**, and I found no place in the records where that is said.

### 2.4 The asymmetry test

**Does rule A charge the DoE arm for a point it discards? YES.** Confirmed in code:
`src/boec/doe.py` documents the split — *"Twenty plus twenty-seven plus one is forty-eight
— the identical budget every [arm gets]"* — with the `+1` being the stage-4 confirmation.
`results/doe-arm.log` records that the confirmation is **not** the observed argmax in 100%
of runs. So the DoE arm spends 1/48 of its budget on a measurement that under rule A can
essentially never be its score.

The record already states this, in Q28, and states the converse for rule C:

> **The DoE arm pays a measurement for its recommendation. BO does not.** … Under rule C,
> BO's posterior-mean argmax is located for free, out of budget.
>
> **So neither rule is budget-matched, and they are unmatched in opposite directions.** Rule
> A taxes DoE; rule C subsidises BO.

**The fix was proposed and NOT run:** give every model-based arm a stage-4, spending one of
BO's 48 measuring its own posterior-mean argmax. Q28 estimates the cost at *"roughly one
re-run of the BO arms"* and requires registration first. **This remains outstanding and is
the single most valuable unrun experiment identified by this review** — it is the only thing
that would make rule C budget-symmetric as well as point-symmetric.

**Is the locator defect closed? YES — verified, not assumed.** T1.4c found the two arms used
different locators: DoE via `metrics.constrained_argmax` at `n_restarts=20,
raw_samples=4096, seed=seed`; BO via a script-local `optimize_acqf(PosteriorMean(...),
num_restarts=10, raw_samples=256)` — **unseeded, 16× smaller screen**. Now fixed in
`scripts/q29_symmetric.py`, both arms calling `constrained_argmax` at identical settings,
and locked over the **AST** by `tests/test_q29_locator.py` — including
`test_no_second_locator_survives_in_the_script`. Q34 applies one locator to all four
recommended cells, asserted by `tests/test_q34_factorial.py`. **All pass** (622/622 suite
green at `3aa6701`).

---

## §3 — THE ALTERNATIVES

### 3.0 The finding that governs this entire section

**`results/e2-grid.json` stores eight fields per campaign** — `arm`, `dim`, `sigma`, `seed`,
`instance`, `best`, `regret`, `auc_post_init` — **and no visited points.** I checked every
JSON in `results/` for stored coordinates; none holds them.

**Consequence: this project cannot re-score itself under any new estimand without
re-running.** Every alternative that needs the visited set, the fitted model, or the
posterior is uncomputable from committed data — which is six of the seven candidates below.
Q29 recorded this in one line as a reason its own rule needed a run; its full cost has not
been stated anywhere until now.

**This is the same family as D12 and D17** — the project's recurring failure is artefacts
that exist in a clone, or not at all, rather than in the repository. Here the artefact was
never written. **Recommendation: persist `train_X`/`train_Y` per campaign.** At 48×(d+1)
doubles per campaign, the full E2 grid is on the order of a few megabytes, and it converts
every future estimand question from a re-run into a re-analysis.

### 3.1 The seven candidates

| candidate | literature name | what it measures | computable from stored data? |
|---|---|---|---|
| **Best posterior mean at an observed point** | closest to Picheny's *identification criterion*; the "best sampled posterior mean" incumbent of Bull 2011 / Wang & de Freitas 2014 / Nguyen 2017 | the best condition you ran, judged by the model rather than by its noisy readout | ❌ needs visited points **and** the fitted GP |
| **Simple regret at the true best visited point** | oracle bound; not reportable | ceiling on what *any* recommendation rule could recover from this visited set | ❌ needs visited points. **Partly superseded:** Q52 §1.1 built this and it *refuted itself* — planting the optimum is not a lower bound, because rule A's cost depends on the runners-up and a good optimiser's runners-up are good |
| **Expected value under the posterior** | model calibration, not performance | what the method *believes* it achieved | ❌ needs the fitted model. **Already measured in another form:** E4's over-prediction, +0.87–1.29 for the polynomial vs +0.25–0.33 for the GP |
| **Inference regret** | the standard noisy-BO term | true value of the recommended point vs the global optimum | ✅ **this IS rule C, under a different name** — see 3.1a |
| **Probability of correct selection** | PCS / ε-correct selection | did this run land within ε, yes or no | ✅ **computable — and computed in 3.2** |
| **Top-k overlap** | ranking agreement | does the method's ordering match the truth | ❌ for E2 (needs candidate scores). Already used in the published-data replay |
| **Cost-weighted regret** | regret per round, not per evaluation | what a wet lab actually pays | ⚠️ partially — **Q38 already answered this**: *"Evaluations are not the cost a wet lab pays — rounds are"* |

**3.1a — Rule C already has a name in the literature, and the paper should use it.**
"Inference regret" — the gap between the recommended point's true value and the global
optimum — is precisely rule C. `docs/CLAIMS.md` already cites Picheny, Wagner & Ginsbourger
2013 for separating the **infill** criterion from the **identification** criterion, and
notes *"that distinction is exactly rule A versus rule C."* **So the A/C pair is not novel
and the project already knows it.** What is novel is the *magnitude* measurement on a
classical comparator. This is correctly framed in CLAIMS.md and must not regress.

**Nguyen et al. 2017 reports best-observed beating the GP-mean counterpart — the opposite
sign to rule C's result here.** CLAIMS.md already flags this as requiring direct engagement.
§2.2 supplies a mechanism the project did not previously have: **the sign of that contrast
depends on where the budget sits relative to the rule-A crossover.** Below the crossover
best-observed is measuring search; above it, luck. That is a testable reconciliation of two
contrary published results, and it is the most publishable thing in this document.

### 3.2 The one that matters most — and it could not be computed

The brief nominates **best posterior mean at an observed point**, correctly, as the rule
sitting between the two: it does not reward the luckiest draw (unlike A) and does not
require extrapolating to an untested point (unlike C).

**Instruction: "Compute it from stored campaigns. No new runs."**

**It cannot be done.** It needs, per campaign, the visited set and the fitted GP. Neither is
stored (§3.0). This is not a judgement call — the data is absent.

**What it would cost:** one re-run of the model-based arms, which is the *same* re-run Q28's
budget-symmetry fix requires (§2.4). **Both should be registered and run together**, since
they need identical machinery: a stage-4 for every model-based arm, recording the
posterior-mean argmax over (a) the whole box and (b) the visited set only. That single run
yields rule C budget-symmetric, the best-posterior-mean-at-observed rule, and the stored
campaigns that make every future estimand a re-analysis.

**Substitute computed instead: probability of correct selection.** PCS is the only candidate
that needs regret alone, so it is the only one the stored grid can answer. Full table in
`results/estimand-evaluation.log`; the headline contrast is qLogEI minus DoE, where positive
means BO selects correctly more often:

| cell | mean regret (rule A) | ε=0.30 | 0.25 | 0.20 | 0.15 | 0.12 | 0.10 | **0.08** | **0.05** |
|---|---|---|---|---|---|---|---|---|---|
| **d=6 σ=0.25** (primary) | DoE by 0.0595 | −0.02 | −0.08 | −0.24 | −0.44 | −0.48 | −0.34 | −0.18 | −0.04 |
| d=6 σ=0.10 | DoE by 0.0018 | 0.00 | 0.00 | 0.00 | −0.08 | −0.10 | −0.02 | **+0.14** | **+0.10** |
| d=8 σ=0.25 | DoE by 0.0284 | −0.02 | −0.04 | −0.06 | −0.32 | −0.36 | −0.20 | **+0.06** | **+0.08** |
| d=8 σ=0.10 | DoE by 0.0024 | 0.00 | 0.00 | 0.00 | −0.10 | −0.22 | −0.06 | **+0.12** | **+0.12** |

**Which arm does it favour? Both — and that is the result.**

**PCS returns a MIXED verdict in three of four cells.** DoE selects correctly more often at
loose targets; **BO overtakes it at the two tightest targets** in every cell except the
registered primary. The registered primary is the one cell where DoE leads at every ε, and
even there its lead collapses from −0.48 at ε=0.12 to −0.04 at ε=0.05.

**This is a third defensible rule, and it splits the difference.** It is also arguably the
most practitioner-relevant of the three: a lab asking *"will this campaign find me a
condition within 5% of optimal?"* is asking for PCS, not for a mean.

---

## §4 — THE HARD QUESTIONS

**1. Would an outside reviewer pick A or C?**

**Neither, as primary.** They would most likely pick **inference regret** — which is rule C
— because it is the standard identification criterion in the noisy-BO literature the paper
must engage (Picheny 2013). But they would expect it **budget-matched**, which this project's
rule C is not (§2.4), and **defined for every arm**, which it is not (§2.3). A reviewer who
noticed that rule C covers 2 of 7 arms would treat the rule-A/rule-C comparison as
confounded with arm set.

**2. Is there a rule under which the verdict is genuinely ambiguous rather than total?**

**Yes — PCS, computed in §3.2.** It is mixed in three of four cells, reversing as the target
tightens. So the clean split is **a property of the two rules chosen, not of the benchmark.**
Two rules that each aggregate to a mean over instances will each be dominated by whichever
arm wins on average; a rule that asks a per-run yes/no question is free to disagree with
itself across the range, and does.

**The absence of a mixed result under A and C therefore means less than it appears to.** It
is close to guaranteed by the fact that both are means of a scalar over the same 25
instances.

**3. Does the estimand finding depend on there being exactly two rules?**

**Yes, and the binary is already false.** Three separate findings converge:

- **Q35:** constrained rule C gives DoE **0.1169** vs BO **0.1232** — *"the reversal
  disappears."* So "rule C ⇒ BO wins" holds only for the *unconstrained* variant that Q35
  supersedes.
- **Q34:** a **GP fitted to the DoE arm's own data** recommends 0.1993 against the
  polynomial's 0.4163 at the same cell — a third distinct rule-C value on identical data.
- **§3.2:** PCS returns a mixed verdict.

So there are at least **four** defensible scorings, not two, and they do not line up on a
single axis. **The "published disagreement is explained by an unregistered convention"
argument weakens accordingly** — it becomes *one of several conventions*, which is a weaker
but still publishable claim. **CLAIMS.md's positioning already hedges correctly** ("the split
is *substantially attributable* to an unregistered scoring convention"), and that wording
should not be strengthened.

**4. What does a lab actually do?**

**Honest answer: I don't know, and neither does this project.** No record contains an
observation of practitioner behaviour; the closest evidence is the source paper, which the
brief explicitly excludes. Two indirect signals:

- Q38 found *"evaluations are not the cost a wet lab pays — rounds are"*, implying labs
  optimise a cost model neither rule represents.
- The DoE arm's stage-4 exists **because** the published study ran its predicted optimum —
  so at least one real lab did rule C.

**If neither A nor C is what labs do, both are academic and the paper should say so.** I
cannot establish that from the records, and constructing an answer would be exactly the
failure this exercise exists to prevent. **This is the largest genuine gap the review found,
and it is not closable by computation.**

**5. Is rule C's advantage partly a GP-smoothing artefact?**

**Almost certainly yes, in part — and Q34 has already half-answered it.** Q34's cell 5 fits a
**GP to the DoE arm's own data**: regret falls from 0.4163 to 0.1993, and cell 5 − cell 3 is
**−0.2171 [−0.2524, −0.1834]** at the primary cell, GP better at all four cells. So the GP's
advantage is **not** an artefact of which design collected the data — it survives holding the
design fixed.

**But that is not the same question.** Cell 5 shows GP-beats-polynomial; the brief asks
whether *averaging noise beats taking a maximum of noisy draws* — a property any smoother
would share. §2.2 supplies the missing half: rule A's score **degrades with budget** while
rule C's does not, in all four cells, which is exactly the signature of max-of-noise versus
averaged-noise. **So the mechanism is real and is not specific to Gaussian processes.** A
random-forest or LOESS arm would isolate the remainder; it is not computable from stored
data.

**6. If rule A is measuring luck at budget 48, was the registered primary measuring the
wrong thing?**

**It was measuring a real thing, and not the thing the headline claims.**

Rule A at n=48 measures "the best plate you ran, on a benchmark where at this budget the
best-plate score is already dominated by the luckiest noise draw for space-filling designs."
That is a legitimate practitioner quantity. It is **not** a measure of search efficiency,
which is what *"BO is not more sample-efficient than current practice"* asserts.

**What follows, concretely:**

1. **Do not change the registered primary** (Part 6, and Q29's own decision rule). It stays.
2. **The qualifier belongs in the sentence, not the limitations section** — the project's own
   standard, applied in Q28 to Q27.
3. The proposed sentence: *"Under the registered scoring rule — the true value of the best
   condition each arm measured — BO does not beat the classical pipeline at 48 evaluations.
   At this budget that statistic is substantially an identification measure rather than a
   search measure, and the comparison under recommendation-based scoring is reported
   alongside it."*
4. **The static arms are the ones to worry about**, since the crossover result is near-exact
   for them and they include `lhs`, BO's closest competitor under rule A.

---

## §5 — VERDICT

**The third option: the choice is under-determined among several defensible rules, and the
paper must say so.**

Not "arbitrary" — each rule is individually defensible and rule C was well conducted. But
the *set* was never enumerated, and the count is wrong: the records treat this as a binary
when at least four scorings are live, at least three of which a practitioner might use, and
they do not agree.

**What is genuinely established and should be stated confidently:**

- The estimand choice moves the verdict by far more than any other factor in the benchmark.
  Reported at 4 of 4 cells; the 10:1 leverage figure in CLAIMS.md is sound.
- Rule A was **used before it was registered** — two void runs and a launched grid — and
  became primary by being the only implementation. The project caught this itself within two
  hours and named it honestly.
- The locator asymmetry is **closed and AST-locked**.
- Q35's constrained scoring stands, and it already breaks the binary.

**What must change in the write-up:**

1. **State that rule B was computed before it was rejected.** The rejection was principled
   and ran against the project's own headline, but the sequence is selection.
2. **State that rule C covers 2 of 7 arms** wherever rule A and rule C verdicts are compared.
3. **Add the budget qualifier to rule A's headline sentence** (§4.6).
4. **Report PCS as a third estimand.** It is computable, practitioner-relevant, and mixed —
   and per Part 6, *"if any alternative changes the verdict, report it prominently."* PCS
   changes it at 6 of 32 (cell × target) points, all at the tight end. **This is the finding
   that must not be buried.**
5. **Correct the three unverifiable premises in §0**, particularly "rule C gives BO the win
   everywhere", which Q35 already refutes.
6. **Use "inference regret"** for rule C and cite Picheny. The pair is not novel; the
   magnitude measurement is.

**The one experiment worth running**, registered first, combining two outstanding proposals
into one run: **give every model-based arm a stage-4**, spending one of its 48 on its own
posterior-mean argmax, and **persist `train_X`/`train_Y`**. That single run delivers
budget-symmetric rule C, the best-posterior-mean-at-an-observed-point rule the brief
correctly identified as the most interesting, rule C for the static arms, and an archive that
turns every future estimand question into a re-analysis instead of a re-run.

**And the uncomfortable sentence, stated plainly because it is true of rule A by the
project's own record:** *two rules were arrived at by circumstance, one of them a code
default that predates its own registration, and they happen to be defensible.* Saying that
is stronger than constructing a rationale afterwards.

---

## Appendix — what this review verified, and what it did not

**Verified against code or commits:** rule A's implementation commit and timestamp; the
five-line original scoring block; the two void runs; Q20's timing relative to the grid;
rule A's naming commit; Q28's and Q29's registration text; the 20+27+1 budget split in
`doe.py`; the locator fix and its AST test; `e2-grid.json`'s stored fields; the absence of
visited points in every `results/*.json`; Q34's and Q35's tables; the full suite green at
`3aa6701` (622 passed).

**Computed here, no new campaigns:** the rule-A crossover across five budgets and four
cells; PCS across eight targets, seven arms and four cells. `scripts/estimand_evaluation.py`,
outputs in `results/estimand-evaluation.{log,json}`.

**Not verified — stated as unknown rather than constructed:** what practitioners actually do
(§4.4); the brief's "32 of 32" denominator; the brief's random-vs-qLogEI figures; the
crossover position for the adaptive arms; whether a non-GP smoother reproduces rule C's
advantage.
