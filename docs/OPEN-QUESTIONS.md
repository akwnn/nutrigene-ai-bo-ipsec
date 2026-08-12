# OPEN QUESTIONS — ONE PLACE FOR EVERYTHING NEEDING A DECISION

**This is the only file that collects questions. Nothing gets asked anywhere else.**

---

## ⚠️ NUMBERING · **Two sessions used "Q29" for different questions, within eleven minutes.**

`b91a395` (10:12) registered the symmetric-scoring comparison as Q29. `3e83fa2` (10:23)
registered the additive-kernel arm as Q29. **The earlier commit keeps the number**; the
additive-kernel work is renumbered **Q30** here and in `surrogate.py`, `campaign.py`,
`scripts/run_q30_additive.py` and `results/q30-additive.*`. Nothing else moves.

Recorded rather than silently fixed, because a pre-registration's whole value is that its
identifier is stable — a reader following "Q29" from a commit message written before 11:07
lands on the other entry, and needs to know why.

### 🔴 The collision is the symptom. The near-miss is the problem.

**The two sessions independently built the same experiment, and it was caught by luck.** This
session wrote out "run the symmetric estimand" as its recommended next action and had begun
the runner — while the other session had already finished it and committed the result forty
minutes earlier. It was noticed only because a `git log` was read *after* an unrelated
commit. Nothing in the workflow would have stopped a full duplicate run.

**Why it happened, and it is structural rather than careless.** Both sessions correctly
identified the same highest-value next step from the same evidence — which is the system
working — and neither had any way to see the other's work-in-progress, because the only
shared channel is a commit that appears once the work is already done. Registering *before*
running is supposed to be that channel, and it does not function when both parties register
inside the same eleven minutes.

**What this costs if unaddressed:** wasted compute is the cheap failure. The expensive one is
two sessions writing contradictory entries about the same result under different numbers, and
a reader downstream not knowing which is authoritative — which is precisely what almost
happened to Q28/Q29, one of which raises the scoring problem and the other of which resolves
it, written independently and unaware of each other.

**Not fixed here** — it needs a convention both sessions follow (claim a number before the
work, not with it), and that is an agreement, not a commit. **Flagged for Alan**, since only
he is in both loops.

---

## 🟢 Q30 RESULT [B] · **The kernel WAS mismatched and fixing it doubled the model's accuracy — and bought exactly nothing in regret. My registered prediction was wrong, and the negative is worth more than the win would have been.**

> **🔴 READ Q29 FIRST — it was answered concurrently and it reframes this entire entry.**
> Under the symmetric scoring rule, **BO already beats the DoE arm in all four cells** by
> +0.27 to +0.36. So the deficit this arm was built to close **is convention-dependent**, and
> at least partly does not exist. This work was aimed at a gap whose sign was still open.
> That does not invalidate the negative below — "accuracy is not the binding constraint" holds
> regardless of who is ahead — but it does mean the framing "BO is losing, so improve the
> model" was resting on the rule-A convention throughout.

`scripts/run_q30_additive.py` · log `results/q30-additive.log` · rows `results/q30-additive.json`.
Accuracy bench: `scripts/bench_surrogate.py` · `results/bench-surrogate.log`. Registration is
the entry below; check its commit timestamp (`3e83fa2`).

**FIDELITY:** the stored qLogEI comparator regenerates over 20 campaigns at max |Δ| **exactly
0.0**. **No E2 number moved.** `kernel_structure` still defaults to `"product"`.

### The model got much better. Held-out R² against noiseless truth, n=46, d=6:

| σ | product (E2) | additive | add+int | relevance, product → add+int |
|---|---|---|---|---|
| 0.25 | 0.050 | −0.014 | **0.106** | 0.746 → 0.735 |
| 0.10 | 0.375 | **0.744** | 0.699 | **0.853 → 0.965** |

At d=8 σ=0.10 the same: 0.448 → 0.764, relevance 0.771 → **0.975** (chance 0.500). The
mechanism argued in the registration is real and it is large.

### THE REGRET DID NOT MOVE. Primary endpoint, d=6, paired on instance, n=25:

| comparison | σ=0.25 | σ=0.10 |
|---|---|---|
| **`qlogei-add` − `qlogei` (THE PRIMARY)** | **−0.0106, p=0.381** | **−0.0015, p=0.711** |
| `qlogei-addonly` − `qlogei` | −0.0123, p=0.264 | −0.0126, p=0.127 |
| `qlogei-add` − `doe` | **+0.0602, p=0.0001** | −0.0057, p=0.396 |
| `qlogei-addonly` − `doe` | +0.0586, p<0.0001 | **−0.0168, p=0.032** |

**The registered primary returned nothing at either noise level.** A surrogate whose held-out
R² nearly doubled and whose factor identification went from 0.853 to 0.965 produced a regret
change of −0.0015 with p=0.71.

### MY PREDICTION WAS WRONG, and this is the informative half

Registered: *"σ=0.10: `qlogei-add` beats stored `qlogei`, and by enough to matter… I expect it
to close the gap to `doe` and to beat it."* **It did not beat qLogEI (p=0.711) and did not
beat DoE (p=0.396).** The σ=0.25 half was correct — no improvement, still loses to DoE — but
that was the half predicted from a ceiling, not from a mechanism.

The error is specific and diagnosable. I reasoned: the surrogate is nearly blind → make it see
→ the search improves. **The first two steps happened and the third did not.** So on this
benchmark, **surrogate accuracy is not the binding constraint on BO's regret.**

This is the accuracy-versus-regret decoupling Q26 already documented from the other side —
one cell where the surrogate learned nothing extra and regret improved, another where
discrimination improved sharply and regret did not move. **I flagged that risk in writing
before running this, and then predicted as though it would not apply.** The registration's own
limitations section named the failure mode it went on to hit.

### What this kills, which is the point

**A whole family of proposals is now closed off, not just one.** "BO is losing because the
model is bad, so improve the model" is refuted by a direct test with a model that is
measurably, substantially better. Combined with what was already eliminated:

| candidate explanation for BO's performance | verdict | where |
|---|---|---|
| lengthscale prior | refuted | Q25 |
| acquisition solver | refuted | Q21 |
| opening batch size | partial, low noise only | Q26 |
| **kernel structure / model accuracy** | **refuted — accuracy doubled, regret unmoved** | **Q30** |

Four of four. **Whatever is limiting BO here, it is not the surrogate.** The remaining
candidates are the budget itself, the acquisition's exploration behaviour under noise, and —
the one now looking most likely — **that the comparison is being scored in a way that does not
measure what either method produces (Q28).**

### The one positive, and why it is NOT a headline

`qlogei-addonly` beats `doe` at σ=0.10: **−0.0168 [−0.0297, −0.0028], p=0.032.** It is the
first time any BO arm has beaten current practice in this project with an interval clear of
zero.

**It should not be reported as "BO beats current practice", for three independent reasons,
any one of which is sufficient:**

1. **It is the SECONDARY arm.** The registered primary was `qlogei-add`, which does not beat
   DoE (p=0.396). Promoting the secondary after seeing the results is arm selection.
2. **It is one cell of four**, at the non-primary noise level.
3. **Multiplicity.** 28 paired comparisons are printed across the two cells. p=0.032 is raw;
   nothing survives a correction over that family.

Recorded because it is real and someone will find it. Not promoted, because it was not
predicted and was not primary.

### Limits, restated

- **Post-hoc, permanently**, and the label travels with every number above.
- **The baselines were not given the same opportunity.** Nobody has tried to improve the DoE
  arm's stage-2 model. This is a tuned method against untuned baselines and it stays stated.
- **Input warping was tried and is a NET NEGATIVE**, contrary to a single-instance result that
  looked promising: it helps R² only at σ=0.10 and destroys calibration everywhere (coverage
  0.49–0.77 against nominal 0.95). Since the acquisition consumes the variance, a model that
  predicts better while misstating its confidence is not an improvement. Not adopted.
- **Fit restarts are not a lever**: +0.008 to +0.019 at σ=0.25, −0.008 to −0.036 at σ=0.10.
- **The benchmark is near-separable by construction (Q22)**, which is the structure an additive
  kernel exists to exploit. That it still bought no regret makes the negative stronger, not
  weaker — this was the friendliest possible test for the idea.

### 🔴 SEPARATE FINDING, from the bench, and it lands on E3 rather than E2

**Every model tested is overconfident, including the shipped one.** The E2 production
surrogate's own 95% intervals cover **0.824–0.909** of held-out truth across all four cells.
Nothing in the bench reaches nominal.

This corroborates T1's coverage work by a different route: T1 measured **0.625** at the
model's own constrained argmax, this measures 0.82–0.91 domain-wide, and the gap between
those two numbers is exactly the "two point sets, and the primary never says which" defect T1
raised. **E3 is the experiment about whether the confidence claims are trustworthy**, so this
is evidence for its headline arriving from a bench that was not built to test it. Worth
someone picking up deliberately.

---

## 🔴 Q31 [B] · PRE-REGISTRATION · STAGE 0 of the Hall/Ogle replay · **the claim, fixed before the dataset that will test it exists**

**Committed before Stage 1 begins.** No canonical CSV exists yet; `data/published/` holds only two markdown files and `VALIDATION_REPORT.md` opens `Status: BLOCKED`. Registering now is the whole point: otherwise the scope of the claim and the capability of the data get decided together and no reader can tell which came first.

### 1. Argmax recovery is not supportable — **and the usual reason for saying so is the wrong one**

The stated blocker (B1) is that two independent extractions disagree on the stage-2 best condition: `stage2_13` at 3.67 versus `stage2_18` at 4.22.

**That reason does not survive contact with the PDF cross-check, and registering it would be a trap.** `docs/pdf_crosscheck.md:119` found that our `stage2_18 = 4.22` corresponds to that column's **Q3 (4.24)**, not its **median (3.48)** — a box-statistic error in *our own* extraction. Corrected, our median is 3.48, their `stage2_13` is 3.67, and **the two extractions would agree**. Stage 1 will apply that correction.

So if the registered reason were "the extractions disagree", Stage 1 would appear to dissolve the objection and the argmax claim would walk back in. **It must not.** The durable reasons, neither of which Stage 1 can touch:

- **The top conditions are not separable.** The top five IQRs share a common band (`pdf_crosscheck.md:116`). An argmax is a claim about a difference the data cannot resolve.
- **The paper never names a best-performing stage-2 condition** (`pdf_crosscheck.md:117`). There is no published target to recover. No text can be contradicted and none can adjudicate.
- **Per-condition SEM is 38–66% of the between-condition spread**, against a source assay CV of ~68% and a paper reporting no variance at all.

> **Registered: no claim of the form "BO recovers the published best condition" will be made, at either stage, regardless of what Stage 1 does to the extraction disagreement.**

### 2. ⚠️ The obvious rank claim is VACUOUS, and this is why Stage 0 exists

The natural phrasing — *"BO reaches the top-k of the published ranking in fewer than 48 evaluations"* — **cannot fail.**

**Stage 2 has 25 conditions. Stage 1 has 23.** The replay proposes only conditions that exist in the dataset (discrete candidate mode). With a budget of 48 against a candidate set of 25, **any method reaches the top-5 by exhaustion**, including one that picks at random and one that picks alphabetically. It would be a test that cannot fail — the fourth in this project, after the ρ-trend, the E4 non-separability check, and the DoE arm's first escape statistic.

### 3. The registered claim

> **Bayesian optimization reaches the pre-specified top-5 condition set in significantly fewer evaluations than random selection over the identical candidate set.**
>
> - **k = 5**, fixed now. Chosen because top-5 overlap (3/5 at both stages) is the granularity at which the two extractions *measurably* agree — the claim is pinned to the resolution the data demonstrably has, not to a rounder number.
> - **Budget = 8** at stage 2 (25 candidates) and **8** at stage 1 (23 candidates) — roughly one third of the set, so exhaustion is impossible and the comparison is about search rather than enumeration.
> - **Ranking source: the reconciled extraction from Stage 2 of the plan** — not either individual extraction, and not the paper.
> - **Comparator: uniform random selection over the same candidate set**, same budget, averaged over orderings, exactly as `run_static_baseline` does.
> - **Test:** paired over conditions where pairing exists; instance-level bootstrap for the interval; Wilcoxon governs significance, per Q20 §2.
>
> **What would falsify it:** BO reaching the top-5 set no faster than random selection. Given 25 candidates and a budget of 8, that is a genuinely available outcome.

**Flagged conditions are excluded from any rank position that depends on the disagreement**, per the plan's Stage 2.2. If `stage2_13` and `stage2_18` remain unreconciled, neither can occupy a rank that decides membership of the top-5.

### 4. The limitation that inverts the obvious objection — **written before the numbers exist**

A reader's instinct is that reading values off a figure is the weak link. **It is not, by roughly an order of magnitude.** Both numbers belong side by side:

| | fraction of between-condition spread |
|---|---|
| digitization reading error | **4–7%** |
| published per-condition SEM | **38–66%** |
| source assay CV | ~68% |
| variance reported in the paper | **none** |

**The constraint is the published experiment, not our extraction.** Recorded now so it reads as a finding rather than as a defence written after someone raised it.

### ✅ RESULT — the registered claim is NOT SUPPORTED, and it is reported as it came out

`scripts/run_replay_hall_ogle.py`, 40 seeds, budget 8, opening 4 shared between arms.

| stage | usable conditions | BO median evals to first top-5 | random | random − BO | Wilcoxon |
|---|---|---|---|---|---|
| stage 2 | 24 of 25 | 3.50 | 3.50 | −0.075 [−0.475, +0.300] | p=0.7243 |
| stage 1 | 23 of 23 | 2.50 | 2.50 | **+0.450 [+0.025, +0.850]** | **p=0.0565** |

**Stage 2: flatly null.** BO is not faster than random selection over the same candidates.

**Stage 1: the two tests disagree, and Q20 §2 says what to do about it.** The bootstrap interval clears zero (+0.025 lower bound); the Wilcoxon does not (p=0.0565). **Q20 §2 registered that Wilcoxon governs significance and the bootstrap reports magnitude, and that a disagreement is reported rather than resolved.** Under that rule, applied as written: **not significant, claim not supported.** The disagreement is itself the finding — with n=40 and a discrete 1–9 outcome there are many ties, which is precisely where a signed-rank test and a bootstrap of the mean come apart.

**One signal that is real and should not be buried.** At stage 1, BO failed to find *any* top-5 condition within budget in **2 of 40** runs against random's **7 of 40**. Time-to-first-hit is not significantly different, but the failure rate is less than a third. **The registered endpoint was speed, not reliability, so this is a secondary observation and not a rescue** — reporting it as the headline would be exactly the estimand-swapping this project has caught five times.

#### Amendment, forced not chosen: the ranking source

Q31 §3 registered the ranking as coming from "the reconciled extraction". **There is no reconciled extraction.** The digitizer's five CSVs were never committed — `git log --diff-filter=A` returns nothing — and commit `e28c84c` ("Rescue A's digitization work before deleting the old working folder") saved only the JSONs, the rasters and two markdown files. **The second extraction died with that folder.**

The ranking therefore comes from the single surviving extraction as corrected. What remains of the second is its summary statistics quoted in `VALIDATION_REPORT.md` — Spearman 0.860/0.880, top-5 overlap 3/5, 47/47 inside IQR — carried as a limitation. `extraction_2` is written **empty** in the canonical CSVs rather than reconstructed.

#### Two forced decisions, recorded because they were not in the registration

**Opening size 4.** `batch_plan` gives `2d + 2` — 10 at d=4, 14 at d=6 — both larger than the registered budget of 8, so the default opening cannot be used at all. Set to 4, leaving 4 adaptive evaluations. Both arms share it, so the comparison stays paired.

**Thin adaptive phase.** Four adaptive evaluations is very little for BO to demonstrate anything. That is a consequence of the registered budget, which was itself forced by the candidate set being only 23–25 conditions — and a larger budget would have made the claim vacuous by exhaustion (Q31 §2). **This is a real limit on what the replay can show, and it is a property of the published study's size, not of the method.**

### 5. Already resolved, so Stage 1 should not re-litigate it

**B2 is adjudicated** by the PDF cross-check, and the two disputed cells **split** (`pdf_crosscheck.md:125–130`): `stage1_23` LN511 is printed `+` (our patch reading was right, the digitizer wrong); `stage2_21` FN is printed `+` (the digitizer was right, our reading wrong). Both corrections are applied with that citation, and neither is a matter of judgement.

**Better than assumed:** per-condition dispersion does not need re-extraction. `stage1.json` and `stage2.json` already carry `q1`, `median` and `q3` per condition, so `Yvar` can be derived without returning to the rasters. `n_conditions` is **23** and **25**, matching the plan's Stage 4 row-count assertions.

---

## 🔴 Q30 [B builds, A + B decide] · PRE-REGISTRATION · **An additive-kernel BO arm. Alan asked for a significantly better BO model; this is the one the diagnostics indicate, and it is registered before any regret exists.**

**⚠️ READ THIS FIRST — the conflict of interest is structural and cannot be argued away.**
`e2.yaml` registers `no_per_method_tuning: true`, which is the most-cited objection in this
literature, and **BO is currently losing to current practice at both dimensions (Q27).**
Anything improved now is improved by someone who knows BO is behind. So:

1. **This is a NEW ARM, not a fix.** No E2 number moves. `kernel_structure` defaults to
   `"product"` — what every stored E2 number is — and a misspelling raises rather than
   falling through, so no stored row can be silently re-attributed.
2. **It is reported as post-hoc model development whatever it returns**, never as E2's
   result. E2's registered primary stays the product-kernel qLogEI arm.
3. **The baselines are not re-run at a disadvantage.** DoE, LHS, Sobol, random and coord
   keep their stored numbers, which were produced under identical conditions.
4. **The failure branch is written below and is reported.** If the improved model still
   loses, that is the result and it is a stronger one than the loss we already have.

### Why THIS change, and not a tuning knob

Three candidate explanations for BO's performance have already been tested and eliminated,
which is what makes this a diagnosis rather than a guess:

| candidate | verdict | where |
|---|---|---|
| the lengthscale prior | **refuted** — `Gamma(3,6)` is significantly *worse* in every cell, and SAASBO's premise with it | Q25 |
| the acquisition solver | **refuted** — max failure rate 0.875%, below the pre-registered 1% repair threshold | Q21 |
| the opening batch size | **partly, at low noise only** — 14→18 helps at σ=0.10, not detectably at σ=0.25, and closes none of the gap to DoE | Q26 |

What has never been varied is the kernel's **structure**, and the landscape's structure is
known:

- **Q22: the benchmark is 93% additive** (0.930 at d=6, 0.927 at d=8). Almost all of the
  response is a sum of per-factor terms.
- **Q25: the production surrogate captures 16% of the shape variance** along the axes that
  matter, at n=46, in the primary cell.

A product ARD kernel treats the response as fundamentally d-dimensional, so learning it
means filling a d-dimensional cube — at 48 points in six factors, about **1.9 points per
axis**. A sum of one-dimensional terms turns the same 48 points into **48 points per axis**.
The sample requirement stops being exponential in d and becomes linear. That is the
mismatch, and it is a model-class mismatch, not a tuning problem.

**Second mechanism, and it may matter more.** Under a product ARD kernel "this factor does
nothing" is said by pushing its lengthscale to infinity — a direction in which the
likelihood is nearly flat, so it is weakly identified. Q25 measured exactly that: ARD
separation at the d=6 opening design was **1.000 against a null of 1.000**, no information
at all, taking ~30 of 34 adaptive evaluations to recover. Under an additive kernel the same
statement is "this component's variance is zero" — a scale parameter with data on both
sides, identified from the first fit.

### The arms

| arm | kernel | note |
|---|---|---|
| `qlogei` (stored) | product ARD Matérn 5/2 | E2's registered primary. Not re-run. |
| **`qlogei-add`** | **sum of d 1-D Matérns + one full ARD term** | **the new primary.** Strictly nests the production kernel. |
| `qlogei-addonly` | sum of d 1-D Matérns, no interaction | secondary; tests whether the ~7% interaction is worth its parameters |

Everything else is held identical: same acquisition, same `n_init = 2d+2`, same budget 48,
same q=4, same instances, same seeds, same scoring (Q17), same clustering.

### Model selection was done on FIT, before any regret existed — and one of my predictions was already wrong

Held-out R² on 800 uniform draws, fit on a Sobol design of size n, 10 instances × 2 seeds,
d=6. **No BO loop, no regret.** This is how the arm was chosen, and the numbers are recorded
here so the choice is checkable rather than asserted.

| surrogate | R²@14 | R²@30 | R²@46 | | R²@14 | R²@30 | R²@46 |
|---|---|---|---|---|---|---|---|
| | **σ=0.25** | | | | **σ=0.10** | | |
| product (E2) | 0.007 | −0.006 | 0.050 | | 0.077 | 0.295 | **0.375** |
| additive, prior=d | −0.091 | −0.158 | −0.014 | | −0.087 | 0.433 | **0.744** |
| additive, prior=1 | −0.086 | −0.099 | 0.043 | | −0.036 | 0.425 | 0.707 |
| **add+int, prior=d** | −0.026 | −0.006 | **0.106** | | 0.091 | **0.436** | 0.699 |
| add+int, prior=1 | −0.008 | −0.047 | 0.097 | | 0.066 | 0.435 | 0.711 |

Relevance — share of the model's weight landing on the 4 genuinely active factors, chance
0.667 — at n=46: product **0.746 / 0.853**, add+int prior=d **0.735 / 0.965**.

**`additive+interaction` with `prior_dims=d` is the primary**: best R² at σ=0.25, within
noise of the best at σ=0.10, best relevance at σ=0.10, and it nests the production model so
the comparison cannot be won by removing capacity.

**A prediction I recorded in code and then refuted before running anything.** I argued in
`build_gp`'s docstring that a 1-D component needs a 1-D-scaled prior, because at `prior_dims=d`
the prior mode is 0.502 on a normalised axis against 0.205 at 1, and a biphasic Hill curve has
structure at 0.2–0.4 — so mode 0.502 "can barely bend". **The measurement says the opposite:
`prior_dims=d` fits better in 3 of 4 comparisons.** The reasoning was wrong. It is recorded
because the methodologically convenient choice — hold the prior at production, move one thing
— turned out to also be the better-fitting one, and that coincidence is exactly the kind of
thing that should be visible rather than quietly enjoyed.

### 🔴 THE FINDING THAT IS ALREADY IN THE TABLE, INDEPENDENT OF ANY BO RESULT

**At σ=0.25 — the E2 primary cell — no surrogate of any structure learns this landscape from
46 points.** The best held-out R² anywhere in the table is **0.106**. At σ=0.10 the same
models reach **0.744**.

That is a signal-to-noise limit, not a modelling failure, and it reframes E2's headline. BO
does not lose the primary cell because its model is badly chosen; it loses because **at 25%
relative noise there is almost nothing for any model to learn**, so adaptive proposals are
guided by noise while structured coverage — DoE, LHS — collects information regardless. It
also predicts, before the fact, that a better surrogate cannot rescue the primary cell.

**This holds whatever the BO comparison returns, and it should be in the write-up either
way.**

### Primary endpoint

**Simple regret at budget 48, scored per Q17, d=6 — `qlogei-add` versus stored `qlogei`,
paired on instance and seed, Wilcoxon on instance-level means (n=25).** Reported at both
noise levels, both pre-named; **σ=0.10 is where the mechanism predicts the effect** and
σ=0.25 is the E2 primary cell.

Secondary: `qlogei-add` versus the stored `doe` arm — the Q24 question, asked of the improved
model; `qlogei-addonly`; d=8 if the d=6 arms return anything.

### Decision rule — fixed now

| outcome | conclusion |
|---|---|
| `qlogei-add` beats `qlogei` at σ=0.10, p<0.05 | **the model class was the problem at low noise**, and E2's BO arm was handicapped by a kernel mismatched to a 93%-additive landscape. Reported as post-hoc model development. |
| it also beats `doe` at σ=0.10 | **BO beats current practice once the surrogate matches the landscape** — the first such result in this project, and it is stated with the post-hoc label attached, not as E2's finding |
| no improvement at σ=0.25 | **expected, and predicted above.** Reported as confirming the signal-to-noise ceiling, not as a failure of the arm |
| no improvement anywhere | **the model class is not the problem either**, and three of four candidate explanations are now eliminated. That is a real result and it gets written up as one. |

**No branch licenses a further arm.** If this does not work, the next model is not tried
until the failure is written down.

### MY PREDICTION, RECORDED BEFORE RUNNING

**σ=0.10: `qlogei-add` beats stored `qlogei`, and by enough to matter — the surrogate's
held-out R² doubles (0.375 → 0.699) and relevance goes 0.853 → 0.965, so the adaptive phase
is being steered by a model that can actually see the shape. I expect it to close the gap to
`doe` (currently +0.0042, a tie) and to beat it.**

**σ=0.25: no improvement, p>0.05, and it still loses to `doe`.** R² 0.050 → 0.106 is a
doubling of nearly nothing. If it *does* improve here, my signal-to-noise reading is wrong
and the interesting question becomes how a model with R²=0.1 steers a search usefully at all.

### What this CANNOT settle

- **It is post-hoc, permanently.** No decision rule can convert a model chosen after seeing
  the first one lose into a pre-registered comparison. The label travels with the number.
- **The baselines were not given the same opportunity.** Nobody has tried to improve the DoE
  arm's stage-2 model, and a fair "best versus best" comparison would. **If `qlogei-add`
  wins, that asymmetry must be stated in the same paragraph**, and it is the obvious
  reviewer objection.
- **It is one landscape family, and one chosen for near-separability** — which is precisely
  the structure an additive kernel is built to exploit. **On a genuinely interacting
  landscape this arm would have no such advantage, and Q22 already flags that the benchmark
  under-represents the interaction the source study is about.** An additive kernel winning
  here is close to a tautology and must not be reported as a general claim about BO.

---

## 🔴 Q28 [B raises, A + B decide] · **The DoE arm's scoring rule was never registered, and the two defensible rules give OPPOSITE answers at every cell. This governs the paper's headline, not a footnote.**

Raised immediately on finding it, in the same session that produced the Q27 result it
undercuts. **Found because Q27's own over-prediction number contradicted its own regret
number** — the arm with the lowest regret in the d=8 table is also over-promising by a
median of +1.55 on a response bounded at 1.0, in 100% of cells. Both cannot describe the
same "winner" without an explanation, and the explanation is the scoring rule.

### The two rules

Q20 §3 already flagged this and left it open: *"`regret_on: noiseless_value_at_selected_point`
does not define the DoE arm's selected point… it is the more generous of two defensible
rules, and it is unregistered. Say which one it is."* It was never said. Here is what it
costs.

| | what it scores | defence |
|---|---|---|
| **Rule A — best-so-far over all 48** (what `run_e2.py:120` does) | the best point the arm *measured* | a practitioner walks away with the best recipe they actually saw |
| **Rule B — the stage-4 recipe** | the point the arm *produced* | `doe.py`: *"The published study evaluated its predicted optimum. So does this."* Stage 4 exists for exactly this reason |

### Measured. Every cell reverses.

DoE minus qLogEI, instance-clustered, n=25. Negative means DoE has less regret.

> **⚠️ PROVENANCE (T1.4a/T1.4b). Every rule-A figure in the table below is from B's clone**, computed against B's untracked copy of `results/e2-grid.json`. A's committed grid — the one behind every number in the paper — gives different values. Regenerated on A's machine in `q34-factorial.json`:
>
> | cell | **A (committed grid)** | B (as printed below) |
> |---|---|---|
> | d=6 σ=0.25 | **−0.0595** [−0.0792, −0.0373] p<0.0001 | −0.0708 |
> | d=6 σ=0.10 | **+0.0018** [−0.0083, +0.0117] p=0.69 | +0.0042 |
> | d=8 σ=0.25 | **−0.0284** [−0.0453, −0.0140] p=0.0023 | −0.0321 |
> | d=8 σ=0.10 | **−0.0024** [−0.0091, +0.0051] p=0.43 | +0.0015 |
>
> Directions and verdicts are unchanged at three cells; **at d=8 σ=0.10 the sign flips** (both null). And the "rule B / rule C" columns score the DoE arm at an **unconstrained** argmax, which **Q35** shows is the wrong scoring — constrained, the DoE arm's recommendation regret falls from ~0.41 to ~0.09–0.12 and the rule-C gap disappears (**Q34**).

| d | σ | Rule A (registered) | Rule B (the arm's output) | over-prediction, median |
|---|---|---|---|---|
| 6 | 0.25 | **−0.0708** (p<1e-5) | **+0.2497** (p<1e-5) | +1.6516 |
| 6 | 0.10 | +0.0042 (p=0.69) | **+0.3450** (p<1e-5) | +0.7432 |
| 8 | 0.25 | **−0.0321** (p=0.0003) | **+0.2482** (p<1e-5) | +1.5468 |
| 8 | 0.10 | +0.0015 (p=0.92) | **+0.3170** (p<1e-5) | +0.7407 |

Regenerated d=6 DoE rows match `results/e2-grid.json` at max |Δ| **exactly 0.0**, so this is
the stored arm being re-scored and not a different one.

**This is the Q16 defect, one experiment over.** There too, two legitimate point sets gave
opposite verdicts on one registered sentence, and the registration never said which. Q16's
answer — *name the point set, and report both* — is the answer here as well. Third
occurrence of the pattern if you count Q19.

### 🔴 But Rule B as computed above is NOT a like-for-like comparison, and must not be quoted as one

It scores **DoE by its model's recommendation and qLogEI by its best measurement.** Those
are different standards, and the asymmetry runs entirely against DoE.

- For a BO arm, "the best point it measured" genuinely *is* its answer — that is what BO
  returns.
- For the DoE arm the two differ, and `results/doe-arm.log` says the confirmation point is
  not the observed argmax in **100%** of runs.
- The symmetric version of Rule B would score **BO at its posterior-mean argmax** — the
  recipe a practitioner would read off the fitted surrogate, which is what the DoE arm's
  stage 4 is. **That number does not exist anywhere in this project.** E2 never records it.

So the honest statement of what is currently known:

1. **Under Rule A, both arms scored the same way, current practice beats BO at σ=0.25 at
   both dimensions.** That comparison is symmetric and it stands.
2. **Under Rule B as computed, BO wins everywhere by a wide margin — and that comparison is
   not evidence**, because the comparator was held to an easier standard.
3. **The symmetric output-versus-output comparison has never been run.**

**Q27's conclusion is therefore narrower than Q27 states it.** "BO beats current practice is
refuted at both dimensions" is true *of the registered scoring rule*, and the registered
scoring rule is the generous one for the arm that won. That qualifier belongs in the same
sentence, not in a limitations section.

### 🔴 THE ASYMMETRY NEITHER RULE CORRECTS — this was missing from this file and belongs in the decision

**The DoE arm pays a measurement for its recommendation. BO does not.** Stage 4 costs 1 of
48 and `results/doe-arm.log` says that point is *not* the observed argmax in 100% of runs —
so under rule A the DoE arm is charged a full evaluation for a point that never helps its
own score. Under rule C, BO's posterior-mean argmax is located for free, out of budget.

**So neither rule is budget-matched, and they are unmatched in opposite directions.** Rule A
taxes DoE; rule C subsidises BO. That is a third axis of the same problem, independent of
which point gets scored, and it should be on the table when the estimand is chosen rather
than discovered afterwards.

**The run that would remove it, proposed and NOT run:** give every model-based arm a
stage-4. Spend one of BO's 48 measuring its own posterior-mean argmax, exactly as the DoE
arm spends one measuring its surface's. Then both arms have paid the same price for the
same kind of output and rule C becomes budget-symmetric as well as point-symmetric. Cost is
roughly one re-run of the BO arms. **Needs registering before it runs** — rule A and rule C
are both already known to favour opposite arms, so the third variant is exactly the kind
whoever runs it can pick the answer to.

### What would settle it — proposed, NOT run

Score every arm at **its own recommended recipe**: DoE at stage 4, qLogEI and qLogNEI at the
posterior-mean argmax of their final surrogate, located with
`metrics.over_prediction_at_constrained_argmax` so both sides use B's one shared function
and cannot disagree by construction. Report Rule A and this symmetric Rule B side by side,
as two named estimands, neither selected after the fact.

**Registering it before running is not optional.** Rule A is already known to favour DoE and
asymmetric Rule B is already known to favour BO, so whoever runs the symmetric version knows
in advance which direction each error points. **This entry is the registration of the
question; the endpoint and decision rule need writing before the run, and A should see them
first** — the estimand this chooses is the paper's headline, and Q20 §1 already put the
choice of estimand in A's lane.

### Not a defect in the DoE arm, and not a reason to touch it

Stage 4 is correctly implemented, correctly costed against the budget, and correctly scored
by `over_prediction_at_constrained_argmax`. **The arm is fine; the sentence written about it
is what is under-specified.** Nothing here licenses re-running, re-tuning or re-scoping any
arm, and no stored number moves.

---

## 🔴 Q27 RESULT [B] · **The d=8 DoE arm ran. Both registered predictions were correct, and current practice wins the primary cell — but read Q28 before quoting this.**

> **🔴 SUPERSEDED IN INTERPRETATION BY Q29, which ran after this was written.** The headline
> below — *"BO beats current practice" is refuted at both dimensions* — is true **of rule A
> only**. Under the symmetric rule C, BO beats the DoE arm at d=8 σ=0.25 by **+0.2689**, the
> same cell where it loses by −0.0321 here. **Do not quote this entry's conclusion without
> rule C beside it.** The arm, the design, the fidelity checks and both registered
> predictions stand exactly as written; what does not stand is the unqualified sentence.

`scripts/run_e2_doe_d8.py` · log `results/e2-doe-d8.log` · rows `results/e2-doe-d8.json`.
Registration is the entry immediately below; check its commit timestamp (`1b064e8`).

**FIDELITY, both tiers, blocking:** 400 stored d=8 rows for `random`/`sobol`/`lhs`/`coord`
and 40 `qlogei`/`qlognei` campaigns over a subsample fixed in code regenerate at max |Δ|
**exactly 0.0**. The arm itself reproduces bit-identically across two independent runs
(100 rows, max |Δ| 0.0). No stored E2 number moved; this adds an arm.

### PRIMARY — d=8, σ=0.25

| arm | mean regret | median | AUC post-init |
|---|---|---|---|
| **doe** | **0.0963** | 0.0960 | 0.8870 |
| qlognei | 0.1086 | 0.1117 | 0.8794 |
| qlogei | 0.1284 | 0.1253 | 0.8649 |
| lhs | 0.1627 | 0.1688 | 0.8257 |
| random | 0.1712 | 0.1716 | 0.8344 |
| sobol | 0.1804 | 0.1979 | 0.8285 |
| coord | 0.1926 | 0.1853 | 0.7917 |

**DoE − qLogEI = −0.0321 [−0.0478, −0.0179], Wilcoxon p=0.0003.** The registered primary.
DoE is also the best arm in the table outright, beating the qLogNEI secondary as well
(−0.0123 [−0.0229, −0.0016], p=0.0160). Minimum detectable paired difference 0.0215.

**Decision rule branch 1 fires**, as written before the run: *"BO beats current practice" is
refuted at BOTH dimensions, not merely unsupported at one* — **subject to Q28.**

### BOTH PREDICTIONS WERE CORRECT, and the second one was tested rather than eyeballed

Registered: *"σ=0.25: DoE beats qLogEI, p < 0.05, by a smaller margin than at d=6 (−0.071).
σ=0.10: no detectable difference."*

> **⚠️ PROVENANCE (T1.4a).** Rule-A figures below are **B's clone**. A's committed grid gives **−0.0595 / +0.0018 / −0.0284 / −0.0024** for the four cells — see the correction table in Q28 above. Rule B / rule C columns use the **unconstrained** DoE scoring that Q35 supersedes.

| σ | d=6 margin | d=8 margin | shrinkage | Mann–Whitney (d8 > d6) |
|---|---|---|---|---|
| 0.25 | −0.0708 | −0.0321 | **+0.0387** | **p=0.00102** |
| 0.10 | +0.0042 (p=0.69) | +0.0015 (p=0.92) | −0.0027 | p=0.672 |

The margin more than halves and **the shrinkage is significant**, so "BO is genuinely
stronger at d=8, just not stronger enough" is measured rather than asserted. That is Q25's
mechanism — d=8 enters the adaptive phase already discriminating — showing up in regret.

### The one cell in this entire project where BO beats current practice

**d=8, σ=0.10, qLogNEI: +0.0117 [+0.0032, +0.0200], p=0.0125.** DoE loses, with an interval
clear of zero. It is a *secondary* arm at a *secondary* noise level, so it is two selections
deep and is not a headline — but Q24 convicts the d=8 table of exactly the sin of letting a
skim-reader take the opposite meaning, and omitting this would repeat it in the other
direction.

At σ=0.10 against the primary arm there is no difference (+0.0015, p=0.9158), matching d=6
(+0.0042, p=0.69). Sobol also ties DoE there (−0.0019, p=0.9158).

### Secondary — the published failure mode reproduces at d=8, unstaged

| σ | over-prediction, median | positive | confirmation outside stage 2 | on its boundary |
|---|---|---|---|---|
| 0.25 | **+1.5468** | 100% | 100% | 0% |
| 0.10 | +0.7407 | 100% | 100% | 0% |

Against a response whose maximum is **1.0**. 0% on-boundary, so this is genuine
extrapolation and not a constrained optimiser pinned to its box. The d=6 figures on the same
arm are +1.6516 and +0.7432 — **materially unchanged by dimension, and roughly doubled by
noise**, consistent with Q25's finding that surrogate quality here is governed by noise
rather than by d.

**This is the finding that contradicted the regret number and led to Q28.** An arm cannot be
both "lowest regret in the table" and "over-promising by +1.55 in every cell" unless regret
is not scoring the thing the arm produces. It is not. **Read Q28.**

### The screen, and the guard that predicted this

| σ | active factors recovered | all 4 exactly |
|---|---|---|
| 0.25 | 0.905 | 0.620 |
| 0.10 | 0.995 | 0.980 |

Identical to the pre-run guard, as it must be — the guard measured the same screen. The d=8
screen beats the d=6 screen at both noise levels (0.860 / 0.935), which is why the arm
transferred to eight factors intact and is the reasoning the registered prediction rested on.

### Limits, stated

- **Q28 governs the interpretation.** The headline holds under the registered scoring rule
  and the registered scoring rule is the generous one for the arm that won.
- **`doe` is a third unpaired arm**, declared in the registration alongside `lhs` and
  `coord` (Q18, Q23). Wider intervals, not a bias.
- **The 8 → 4 screen is ours, not the literature's.** Hall/Ogle screened 6 → 4; nothing
  published screens 8 → 4. It is what the same practitioner would have to do at eight
  factors on the same budget, and it is not a reproduction of anything.
- **Multiplicity is not corrected across the twelve paired comparisons printed.** The
  registered primary is one pre-named comparison at p=0.0003, which survives any correction
  these tables could carry; every other number in them is descriptive and is labelled
  secondary. Stated rather than left to be noticed.
- **One ensemble.** "Current practice wins at six factors and at eight" is a claim about
  this benchmark family.
- **A has not accepted the split** (Q24, Q27). That is still open, and the numbers are
  contingent on it.

---

## 🔴 Q27 [B builds, A + B decide] · PRE-REGISTRATION · **The d=8 DoE arm — Q24's missing comparison. Design fixed and committed BEFORE any number exists.**

**A HAS NOT SEEN THIS.** Q24 is marked A + B and the split it proposes is A's to accept or
reject. It is registered rather than run-then-shown, which is the pattern this project uses
when one session has to move and the other has not answered — same as T9/Q18. **The run is
gated on this entry being committed, not on A's reply**, because the alternative is that the
arm never happens; but if A rejects the split, the numbers go in the bin and are not
argued down from.

**NO EXISTING E2 NUMBER MOVES.** This *adds* an arm at d=8. It does not re-run, re-score or
re-scope anything in `results/e2-grid.json`, and `e2.yaml`'s registered primary is untouched.
Check this entry's commit timestamp against `results/e2-doe-d8.json`.

### Why this run exists

Q24, in one sentence: **"BO beats current practice" is not supported at either dimension** —
at d=6 it was tested and BO lost, and at d=8 the DoE arm was never run, so the table that
looks like a clean BO win contains no representative of current practice at all.

| stored, d=8 | mean simple regret, instance-clustered |
|---|---|
| qLogNEI | 0.1086 |
| **qLogEI (registered primary arm)** | **0.1284** |
| LHS | 0.1627 |
| random | 0.1712 |
| Sobol | 0.1804 |
| coord | 0.1926 |
| **DoE** | **absent — this is the gap** |

For contrast, at d=6 σ=0.25 the DoE arm returns **0.0958** against qLogEI's **0.1666**.

### Why it was blocked, and what unblocks it

`screening_design(8, n_derived=2)` is 64 runs, so 64 + 27 + 1 = 92 against a budget of 48.
Going further failed on purpose: `designs.py` refuses to invent a generator it has not
verified. The sixteenth fraction closes it:

```
stage 1   2^(8-4)_IV screen, 16 runs + 4 centre     20
stage 2   face-centred CCD on the 4 kept factors    27
stage 4   confirmation                               1
                                                total 48
```

**Structurally identical to d=6 in every stage.** Both screens are 16 runs, both keep 4
factors, both stage 2s are the same 27-run CCD, both confirm once. The two extra factors are
absorbed entirely by the fraction. So a d=6 vs d=8 difference in this arm is a difference in
the **landscape**, not in the procedure.

**There is no free parameter to tune here, and that is deliberate.** `n_keep = 4` is forced
by the budget (a CCD on 5 factors is 47 runs on its own), the fraction is forced by the
budget, `stage2_half_width` and `hold_dropped_at` are carried unchanged from the registered
d=6 arm. The only genuine choice was the generator, and it is not a matter of taste —
`test_2_8_4_is_minimum_aberration` enumerates all **330** admissible generator sets, computes
each word-length pattern, and asserts the shipped one is the **unique** minimiser
(A₃=0, A₄=14, A₈=1; the runner-up is resolution III). Resolution IV is derived from the
generators in `test_2_8_4_resolution_iv_verified_from_the_generators_not_the_table`, not read
off the table it is checking.

### The incentive problem, stated rather than managed away

The d=6 result already went against BO. **A d=8 DoE arm designed after seeing that is a
design chosen by someone who knows what he wants it to show**, and this entry exists so that
the design is fixed in a commit before the first number rather than defended afterwards. The
three things that make it checkable: no free parameters (above), the endpoint and decision
rule below, and a prediction that can be wrong.

### Primary endpoint

**Simple regret at budget 48, scored on the noiseless value of the point each method
selected (Q17), at d=8, σ_rel = 0.25 — DoE versus qLogEI, paired on instance and seed,
Wilcoxon on instance-level means (n = 25, `cluster: instance` per `e2.yaml`).**

σ=0.25 is the primary because it is E2's primary noise level. σ=0.10 is reported as a
secondary, on the same statistics, and is not used to adjudicate the Q24 sentence.

Also reported, all secondary: DoE against every other stored d=8 arm; AUC over the
post-initialisation segment; the escape statistics the arm produces anyway
(`confirmation_inside_stage2`, `confirmation_on_stage2_boundary`, over-prediction at the
constrained argmax).

**`doe` is a third unpaired arm and it is declared here, not discovered later.** It shares no
opening batch with qLogEI — its first 20 points are a fixed screen, not `initial_design` —
exactly as `lhs` and `coord` do not (Q18, Q23). The Wilcoxon pairing above is on instance
and seed, which is the pairing E2 already uses for `coord`; it is not observation-level
pairing and is not claimed to be. Cost: a wider interval, not a bias.

### Decision rule — fixed now

| outcome at d=8, σ=0.25 | what goes in the write-up |
|---|---|
| DoE regret **lower** than qLogEI, p < 0.05 | **"BO beats current practice" is refuted at BOTH dimensions**, not merely unsupported at one. Q24's sentence strengthens. |
| DoE regret **higher** than qLogEI, p < 0.05 | **BO beats current practice at d=8 and loses at d=6.** The dimension flip is real and is the headline; Q24's sentence is replaced by a narrower, more interesting one. |
| p > 0.05 either way | **No detectable difference, reported as such**, with the minimum detectable effect stated. No seeds, instances or noise levels are added afterwards to push it across. |

**No branch of that table is a reason to change the arm.** If DoE loses at d=8 it is not
re-tuned; if it wins, the d=6 arm is not re-examined for defects that were acceptable while
it was winning.

### MY PREDICTION, RECORDED BEFORE RUNNING

**σ=0.25: DoE beats qLogEI, p < 0.05, by a smaller margin than at d=6 (−0.071).**
**σ=0.10: no detectable difference, p > 0.05 — as at d=6, where it is 0.0892 vs 0.0850.**

Reasoning, so a wrong prediction is diagnosable rather than merely wrong. The guard below
measures the d=8 screen recovering active factors **more** accurately than the d=6 screen,
not less — because each inert factor at d=8 carries half the weight (0.025 against 0.050),
and that dominates the "4 of 8 rather than 2 of 6" difficulty. The DoE arm's entire exposure
to dimension is concentrated in the screen, since everything downstream of it operates on
exactly 4 factors at either dimension. So the arm should transfer to d=8 essentially intact.
Against that, BO is genuinely stronger at d=8 than at d=6 (Q25: it enters the adaptive phase
already discriminating, ARD 1.150 against 1.000), so the gap should close somewhat.

If DoE instead **loses** at σ=0.25, my model is wrong in a specific and informative way: it
would mean the d=6 DoE win is not "structured coverage beats a blind surrogate at high
noise" (Q24/Q26's reading) but something that depends on dimension through a channel other
than screen accuracy — and since the procedure is identical at both dimensions, that channel
would have to be the landscape's own geometry at d=8, which nothing so far has looked at.

### Guards, run and recorded BEFORE this entry was committed

**G1 — the budget closes exactly.** 20 + 27 + 1 = 48 at both dimensions, asserted in
`test_2_8_4_gives_sixteen_runs_and_closes_the_48_budget` and enforced at runtime by
`run_doe_arm`'s existing split check.

**G2 — the generator is minimum aberration**, by enumeration of all 330 alternatives. Above.

**G3 — screen recovery, measured, and it is not what I expected.** Fraction of each
instance's 4 active factors that survive the screen; 25 instances × 2 seeds; the screen only,
no campaign, no regret.

| d | σ | active factors recovered | all 4 recovered exactly |
|---|---|---|---|
| 6 | 0.25 | 0.860 | 0.460 |
| 6 | 0.10 | 0.935 | 0.740 |
| **8** | **0.25** | **0.905** | **0.620** |
| **8** | **0.10** | **0.995** | **0.980** |

The d=6 row reproduces the 86% / 94% figures already quoted in `doe.py`'s docstring, which
is what says the guard is measuring the same screen the arm runs. **The d=8 screen is
better at both noise levels** — a second, completely independent instrument agreeing with
Q25's ARD finding that d=8's individually-weaker inert factors are easier to identify. Two
different methods, one two-level contrast and one GP lengthscale, same conclusion.

**G4 — the endpoint can return either answer.** The same arm on the same code wins decisively
at d=6 σ=0.25 (0.0958 vs 0.1666) and ties at d=6 σ=0.10 (0.0892 vs 0.0850). Nothing about
this arm forces a win or a loss.

**G5 — fidelity, so the comparison is against numbers this code still produces.** All **400**
stored d=8 rows for `random`, `sobol`, `lhs` and `coord` regenerate against
`results/e2-grid.json` with max |Δ| of **exactly 0.0**. The qLogEI arm is the expensive one
and is checked on a declared subsample in the run script; **if that check fails the run is
void**, because a DoE number compared against a stale qLogEI number is not a comparison.

**G6 — d=6 is untouched by the change that enables d=8.** `run_doe_arm`'s hardcoded
`n_derived=2` became a registered per-dimension table. `test_d6_is_bit_identical_to_before_the_d8_change`
asserts the table reproduces the literal it replaced, to zero tolerance, or every stored d=6
DoE number stops matching the code that claims to produce it.

### What this CANNOT settle — to be restated in any write-up

- **It is one ensemble.** "Current practice loses at six factors and at eight" is a claim
  about this benchmark family, not about DoE in general.
- **The dimension contrast still bundles three things** (Q25, Q26): dimension, opening-design
  size and per-factor inertness move together in this ensemble, and this arm does not
  separate them either. What it *does* do is remove the asymmetry that made the two
  dimensions' tables non-comparable.
- **The screen is not the published screen.** Hall/Ogle screened 6 → 4. Nothing published
  screens 8 → 4; that split is ours, chosen for structural equality with d=6 and forced by
  the budget. It is not "what a practitioner did", it is "what the same practitioner would
  have to do at eight factors on the same budget".

---

## 🟢 Q26 RESULT [A] · **Opening size explains the blindness at LOW noise and is RULED OUT at the E2 primary cell. Both registered predictions were correct.**

`scripts/confound_ninit.py` · `results/confound-ninit.log` · rows in
`results/confound-ninit.json`. Registration is the entry immediately below; check its
commit timestamp. **FIDELITY: 100/100 `n_init=14` campaigns reproduce their stored E2
`best` to 1e-9. E2 is unchanged and stays at `n_init = 2d+2`.**

### THREE CORRECTIONS APPLIED BEFORE READING THE RESULT

Found by a three-lens audit run while the numbers computed, and verified independently
before acting on any of them. **None changes a verdict; all change numbers.**

1. **The inference was pseudo-replicated, in Q25 and nowhere else.** Q25's ARD Wilcoxon ran
   over all **50 runs**. `e2.yaml` registers `cluster: instance`, and 25 landscapes × 2
   seeds has effective n = **25**. This is the exact error this project criticises the
   source paper for, and it is defect **#9**. Both scripts now cluster.
2. **A signed-rank test on a difference of RATIOS is anti-conservative.** The null
   differences are right-skewed, so the symmetry assumption fails: measured type-I error
   **8.9% at a nominal 5%, 2.0% at a nominal 1%**. On the log scale it is 4.9% and 0.9% —
   nominal. All ratio comparisons are now made in log space.
3. **Q26 registered `1.150 / 1.718` as d=8's reference. Those are on the wrong scale** —
   they are Q25's run-level figures. Under the corrected estimator d=8's opening reads
   **1.295 (σ=0.25)** and **1.768 (σ=0.10)**. The report now computes this live from the
   committed Q25 rows rather than quoting a remembered number.

### PRIMARY

| σ | n_init | fit | null | p | verdict |
|---|---|---|---|---|---|
| 0.25 | 14 | 0.992 | 0.984 | 0.427 | no |
| **0.25** | **18** | **1.023** | 0.986 | **0.221** | **no** |
| 0.10 | 14 | 1.036 | 1.001 | 0.317 | no |
| **0.10** | **18** | **1.332** | 1.007 | **0.00336** | **DISCRIMINATES** |

Difference-in-differences, each arm against its **own** null (the null moves with n, so the
anchor must too): σ=0.25 **1.013×, p=0.336**; σ=0.10 **1.191×, p=0.0062**.

**Both registered predictions were correct.** σ=0.25 does not discriminate; σ=0.10 does.

### CORRECTIONS AFTER THE SECOND AUDIT — including to what I first wrote here

A three-lens audit of this test returned after the result was written up. It found no
surviving fatal, because both of its fatals had already been applied before interpretation.
Five material items survived, and two of them hit claims made in this entry. All verified
independently before acting.

**C1. "Ruled out at σ=0.25" was too strong and is withdrawn.** The measured excess over null
is 1.036× (0.037 log). Two things sit at that scale: the bootstrapped minimum detectable
effect at 80% power and α=0.01 is a separation of about **1.14**, and — because every one of
the 25 clusters in a cell shares the *same* design and the *same* three permutation indices
(`sobol_design(..., seed=seed)` and `permutation_null_lengthscales(..., seed=seed)` both key
on seed alone) — the null carries a common Monte-Carlo component bounded at roughly **0.05
log**, which does not shrink with more instances. The point estimate is *inside* that bound.
The defensible statement is **no detectable effect, with a detection floor near 1.14**, not
"ruled out".

**C2. The registered reasoning was wrong even though the prediction was right.** I registered
"at 25% noise the binding constraint is signal-to-noise, not sample count". My own Q25 data
refutes it: at d=6, σ=0.25 the separation runs **0.992 (n=14) → 1.318 (n=30, p=0.020) →
1.370 (n=46, p=0.0006)**. Sample count buys plenty at σ=0.25. What this test actually showed
is narrower — the return *between 14 and 18 specifically* is below the detection floor. The
registration said a wrong prediction would be diagnosable; a right prediction with wrong
reasoning is the case it did not anticipate, and it is the more dangerous one, because
nothing in the result flags it.

**C3. THE DECISIVE TEST I HAD NOT RUN. At matched opening size, d=8 still beats d=6 — at
BOTH noise levels.** Excess over each arm's own null, 25 clusters each, unpaired:

| σ | d=6 @ 18 | d=8 @ 18 | Mann–Whitney (d8 > d6) |
|---|---|---|---|
| 0.25 | 1.036× | 1.199× | **p=0.044** |
| 0.10 | 1.241× | 1.688× | **p=0.0008** |

So **matching the opening size does not close the gap at either noise level.** At σ=0.10 the
four extra points buy real discrimination against d=6's own null (1.332, p=0.0034) — but
d=6 still lags d=8 given the same 18 points. Opening size is therefore **part** of the story
at low noise and **not detectably any of it** at high noise, and at neither level is it the
whole story. Dimension and per-factor inertness, still fused to each other, contribute at
both. This is a better answer than the one first written here and it is less favourable to
the hypothesis.

**C4. The stated justification for the difference-in-differences is false.** I wrote that
"the null moves with n, so the anchor must move with it". Measured: the null shifts
**−0.0087 log (σ=0.25, p=0.81)** and **+0.0191 log (σ=0.10, p=0.92)**. It does not move.
DiD remains the right statistic — it is strictly the more conservative anchoring — but for a
different reason than the one given.

**C5. Multiplicity, declared late but certifiable.** Six primary p-values are printed. The
two `n_init=14` cells are **bit-identical reproductions** of Q25's opening checkpoint —
max |Δ| over all 100 rows is exactly **0.0** — so they are reproductions, not new tests, and
the correction is ×2 rather than ×4. σ=0.10 at p=0.00336 gives **0.0067**, which clears the
registered 0.01 bar; at ×4 it would not (0.0134). The declaration rests on the certificate,
not on convenience, and the certificate is checkable.

**C6. The guard numbers in the registration below are unsourced and wrong.** "Permuted-outcome
ratio at d=6: 1.042 at n=14, 0.937 at n=18" came from an ad-hoc 10-instance check at one σ
with a different permutation count, and matches no quantity any script computes. The actual
nulls are **0.984 / 0.986** (σ=0.25) and **1.001 / 1.007** (σ=0.10). The guard's *conclusion*
— that the null is centred near 1.0 — holds, and holds better than the quoted numbers
suggested. The numbers themselves should not have been written down.

**C7. The re-draw magnitude was quoted from one instance and is larger in the cell that
produced the positive.** Median over 10 instances: **8.4% of sd(Y) at σ=0.25, 12.5% at
σ=0.10**, not the single 7.4% figure first reported.

**C8. The σ=0.25 regret improvement does not survive multiplicity.** p=0.0173 raw, 0.069
under Bonferroni across the four regret tests. "n_init=18 still loses to DoE" (p=0.0046)
does survive.

### Points per dimension — why the σ=0.25 non-result is still informative

Matching `n_init` does not match points per dimension; it *overshoots* in d=6's favour:

| | absolute n | per dimension | per active dim | per inert dim |
|---|---|---|---|---|
| d=6, n=14 | 14 | 2.33 | 3.5 | 7.0 |
| **d=6, n=18** | **18** | **3.00** | **4.5** | **9.0** |
| d=8, n=18 | 18 | 2.25 | 4.5 | 4.5 |

d=6 at 18 weakly dominates d=8 on every normalisation and still shows less separation
(C3). That is what makes the negative informative despite the detection floor: the
manipulation was generous and the gap survived it.

### SECONDARY — regret, and the two effects are ANTI-CORRELATED

| σ | arm | adaptive evals | median regret | vs n_init=14 | p |
|---|---|---|---|---|---|
| 0.25 | qlogei n_init=14 | 34 | 0.1569 | — | — |
| **0.25** | **qlogei n_init=18** | **30** | **0.1208** | **−0.0300 better** | **0.0173** |
| 0.25 | doe (E2) | — | 0.0934 | +0.0295 *(n=18 still worse)* | **0.0046** |
| 0.10 | qlogei n_init=14 | 34 | 0.0842 | — | — |
| 0.10 | qlogei n_init=18 | 30 | 0.0868 | +0.0012 | 0.692 |
| 0.10 | doe (E2) | — | 0.0908 | −0.0007 | 0.812 |

**Where discrimination did not improve, regret did; where discrimination improved sharply,
regret did not move.** At σ=0.25 the surrogate learned nothing extra yet regret improved
significantly on **four fewer** adaptive evaluations — so that gain is not the ARD
mechanism. The likeliest reading is the one Q24 already points at: at high noise, structured
coverage beats adaptive proposals from a model that cannot tell the factors apart, which is
also why LHS and DoE win in that cell. At σ=0.10 the seed round bought knowledge and spent
the budget that would have used it.

**It does not rescue BO. qLogEI at n_init=18 still loses to DoE at the primary cell**
(+0.0295, p=0.0046).

Final-stage separation at n=46 is unchanged by the manipulation (σ=0.25: 1.582 → 1.648;
σ=0.10: 4.102 → 3.790), confirming the noise-governed pattern.

### Limits, stated

- **One confound of three, and the residual two remain fused to each other.** Dimension and
  per-factor inertness need a new ensemble with a per-dimension `active_share` to separate.
- **At fixed budget, opening size and adaptive count are the same variable with opposite
  sign.** There is no `n_init=18, budget=52` arm, so the secondary regret delta is a single
  composite treatment and is unattributable in principle within this design.
- **The null branch is an underpowered accept-the-null.** Bootstrapped minimum detectable
  effect at 80% power and α=0.01 is a separation of about **1.14**, so effects smaller than
  roughly the d=8 effect itself are not ruled out at σ=0.25.
- **The registered decision table does not partition the outcome space** (it keys on a
  conjunction of p and magnitude but assigns only the corners), and the script's verdict
  uses p alone. Both observed results fall in assigned regions, so nothing here turned on
  it, but the rule was under-specified.
- **"The same fourteen points plus four more — nothing else can differ" was false for the
  OUTCOMES.** The design is bit-identically nested; the data is not. `observe` draws the
  multiplicative noise vector then the additive one from one stateful generator, so an
  18-row call shifts the additive block by four positions and the shared 14 rows get
  different y (max |Δ| 0.0177, 7.4% of sd(Y)). A re-draw from the same distribution, not a
  bias — but the arms are not paired at the observation level. Now pinned by a test; the
  original guard used a zero-noise evaluator and could not have caught it.
- **The headline "the 2d+2 rule is insufficient at low dimension" is NOT supported.** One
  dimension and two values of n_init cannot locate a threshold, cannot show the rule fails
  at another d, and cannot separate "the d-scaling is wrong" from "absolute n below ~18 is
  small here". The defensible claim is narrower: *at d=6 on this benchmark, a 14-point
  opening leaves the surrogate indistinguishable from noise at both noise levels, and 18
  points fixes that at σ=0.10 but not at σ=0.25.*

---

## 🔴 Q26 [A] · PRE-REGISTRATION · **Does the opening batch SIZE explain the d=6 blindness? Written and committed BEFORE the first run.**

**E2 IS UNCHANGED AND STAYS UNCHANGED.** The pre-registered primary keeps
`n_init = 2d+2 = 14` at d=6 whatever this returns. This is a mechanism diagnostic that
explains the primary; it does not revise it, and no number in `e2.yaml`, `results/e2.log`
or `results/e2-grid.json` moves. If this test says the seed rule is too small, that is a
finding ABOUT the standard rule, not a licence to re-run E2 under a better one.

Check this entry's commit timestamp against `results/confound-ninit.json`.

### What Q25 left entangled

Three things move together between d=6 and d=8, and Q25 could not separate them:

| | d=6 | d=8 |
|---|---|---|
| opening design size (`2d+2`) | 14 | 18 |
| dimension | 6 | 8 |
| influence of **each** inert factor (`0.10 / n_inert`) | **0.050** | **0.025** |

This isolates **one**: run d=6 with an 18-point opening. Everything else identical — same
ensemble, same instances, same seeds, same kernel, same acquisition, same budget of 48.

**The manipulation is exactly nested and this was verified before registering.**
`initial_design` returns a Sobol design, and `sobol_design(bounds, 18, seed)[:14]` is
bit-identical to `initial_design(bounds, seed)` (max abs difference 0.0). So the treatment
is literally "the same fourteen points, plus four more". Nothing else can differ.

### Primary endpoint

**ARD separation (inert ÷ active fitted lengthscale) on the OPENING DESIGN, against a
paired permuted-outcome null.** Not regret. The mechanism claim is about what the surrogate
knows at the moment adaptive search begins, so that is where it is tested.

Pre-specified comparisons, both reported:
1. d=6 @ n=18 versus its own permutation null (Wilcoxon, one-sided, clustered on instance);
2. d=6 @ n=18 versus d=6 @ n=14, **paired on the same instances and seeds** — available
   because the designs are nested, and a stronger test than either against the null alone.

### Decision rule — fixed now

| outcome at d=6, n=18 | conclusion |
|---|---|
| p < 0.01 and separation ≳ 1.15 (d=8's value) | **opening size explains the opening-stage blindness**; dimension per se is not the driver |
| p > 0.05 and separation ≈ 1.0 | **opening size does not explain it**; dimension or per-factor inertness does, and this design cannot separate those two |
| 0.01 < p < 0.05 | **ambiguous, reported as ambiguous.** No seeds are added to push it across. |

### MY PREDICTION, RECORDED BEFORE RUNNING

**σ_rel = 0.25 (the E2 primary cell): it will NOT discriminate. p > 0.05.**
**σ_rel = 0.10: it WILL discriminate. p < 0.01.**

Reasoning, so a wrong prediction is diagnosable rather than just wrong. At 25% relative
noise the binding constraint is signal-to-noise, not sample count: noise holds the *final*
46-point separation down to 1.40 at d=6, so four extra points at the opening cannot
plausibly buy what forty-two more could not. At 10% noise the final separation reaches 3.41,
which shows the information is extractable from this ensemble once enough of it accumulates,
and the opening value of 1.028 already sits nominally above the null — so the 29% increase
in data has somewhere to go.

If instead σ=0.25 discriminates, my model of the mechanism is wrong in an informative way:
it would mean the opening-stage failure is a small-sample problem that noise does not
govern, and the two regularities Q25 identified (opening tracks dimension, final tracks
noise) would need re-describing as one.

### What this CANNOT settle — to be restated in any write-up

**Per-factor inertness is untouched.** Each inert factor carries 0.050 of the weight at d=6
and 0.025 at d=8, so every individual nuisance factor at d=8 is half as influential and
correspondingly easier to identify as inert. Matching `n_init` does not change that;
separating it needs a different `active_share` per dimension, hence a new ensemble and fresh
cached optima. Out of scope.

**So neither outcome is "we isolated the mechanism". One confound of three.**

### Secondary, clearly marked as such

- Simple regret at budget 48, d=6, both noise levels, versus the pre-registered `n_init=14`
  result and versus the DoE arm. **Not a corrected E2 result and will not be presented as
  one.**
- **The budget trade-off.** At `n_init=18` there are 30 adaptive evaluations instead of 34.
  If separation improves and regret does not, the seed round bought knowledge and spent the
  budget that would have used it — which is the more interesting outcome, not a null.
- Final-stage ARD separation, to confirm the noise-governed pattern still holds.

### Guards, run BEFORE this entry was committed

- **Null is centred.** Permuted-outcome ratio at d=6: **1.042 at n=14, 0.937 at n=18**,
  both ~1.0 as the symmetry argument requires (the prior is identical on every dimension).
- **The endpoint can return either answer.** Nothing about 18 points at d=6 forces
  discrimination or forces its absence: the same statistic on the same ensemble reads 1.000
  at n=14 and 1.403 at n=46, so both branches are reachable at an intermediate n.
- **Fidelity.** The n=14 baseline arm regenerates and is checked against stored E2 rows.
- **One variable.** Verified nested designs, above.

---

## 🟢 Q25 [A, B should second-read] · **The prior is not why BO lost at d=6 — and the nuisance-dimension story is right for a reason nobody had stated. Also: A registered an endpoint that could not fail, for the second time.**

**Nothing in E2 changes. No number, no arm, no config.** Reproduce with
`scripts/diagnostic_lengthscales.py`; rows in `results/diagnostic-lengthscales.json`;
report in `results/diagnostic-lengthscales.log`.

**Fidelity, asserted rather than promised: 200/200 regenerated campaigns reproduce their
stored E2 `best` to 1e-9**, and each row also carries a hash of its design matrix. The
script fails loudly on any mismatch, so these are the runs E2 scored or there is no report.

---

### READ THIS FIRST: version 1 of this diagnostic was void, and I had already written up its conclusion

The rule was registered in the module docstring before any number was read — correct
procedure — and it could only return one answer.

It compared fitted lengthscales against the **prior median**, `exp(loc) = 10.08` at d=6, and
read "far below 10" as *the data is winning*. But `fit_gpytorch_mll` is **MAP**, not maximum
likelihood: `ExactMarginalLogLikelihood` adds `log p(lengthscale)`, the constraint carries
`transform=None` so raw and constrained coincide, and the argmax of the prior term alone is
the **mode**, `exp(loc − scale²) = 0.5016`. That is also the value gpytorch **initialises
the kernel to**. Measured: a 14-point fit on outcomes with no dependence on X returns
0.5016 on every dimension.

**Version 1's measured opening-design median was 0.502.** It scored a model that had learned
nothing as a model that had learned everything. The "prior is dominating" branch was
unreachable — the prior's own gradient at ℓ=10 points *down*.

This is defect #8 and it is the same failure as Q16, committed by the person who wrote the
guard against it. Caught by a four-lens adversarial audit run deliberately **before** the
numbers were interpreted. The general practice this produced is now written into
`docs/METHODS.md` §2.9 as a stated method, not a quiet fix.

### What version 2 measures instead

The anchor is no longer a formula but an **empirical no-signal null**: the same design, the
same noise, refit with outcomes **permuted**. And the deciding statistic is the **ARD
separation ratio**, inert ÷ active lengthscale — immune to this whole class of error,
because the prior is identical on every dimension, so *any* uninformed fit gives 1.00 by
symmetry. Measured null, pooled over 200 runs: **1.006** [0.718, 1.498]. The symmetry
argument holds.

**CORRECTION (from Q26's audit): Q25's p-values below were pseudo-replicated.** They ran
over 50 runs where `e2.yaml` registers `cluster: instance` (n=25), and on the ratio rather
than log scale. Recomputed correctly, every conclusion stands and every number moves:
opening d=6 **0.992 (p=0.674)** and **1.036 (p=0.190)**; opening d=8 **1.295 (p=1.0e-03)**
and **1.768 (p=3.2e-05)**; final d=6 **1.370** / **3.886**, d=8 **1.364** / **3.392**. The
headline contrast survives — opening d=6 vs d=8 **p=8.9e-04** (σ=0.25) and **p=2.7e-05**
(σ=0.10); final **p=0.669** and **p=0.712**. Defect #9.

Checkpoints are now only models the campaign actually built — the opening design, n=30 and
n=46, all real round boundaries at both dimensions. (`Campaign.run` fits before each `ask`
and never after the final `tell`, so v1's n=48 model made no decision, and its n=31/33
sliced through a jointly-optimised batch.)

---

### THE RESULT: d=8 enters the adaptive phase already knowing which factors matter. d=6 does not.

ARD separation (inert ÷ active), paired against each run's own permutation null:

| cell | stage | n | FIT | NULL | p(fit > null) |
|---|---|---|---|---|---|
| **d=6 σ=0.25** | opening | 14 | **1.000** | 1.000 | **0.29 — nothing** |
| | mid | 30 | 1.442 | 1.076 | 0.0075 |
| | final | 46 | 1.403 | 1.090 | 0.00032 |
| **d=8 σ=0.25** | opening | 18 | **1.150** | 1.000 | **0.00035** |
| | mid | 30 | 1.537 | 1.000 | 3.4e-08 |
| | final | 46 | 1.471 | 1.003 | 0.00049 |
| **d=6 σ=0.10** | opening | 14 | 1.028 | 0.932 | 0.25 — nothing |
| | final | 46 | 3.412 | 0.879 | 6.2e-14 |
| **d=8 σ=0.10** | opening | 18 | **1.718** | 0.942 | **8.1e-08** |
| | final | 46 | 3.438 | 1.059 | 2.2e-14 |

Two facts, and together they are the answer:

1. **At the opening design, d=8 discriminates and d=6 does not.** d=6 sits exactly on its
   null (1.000 vs 1.000). The dimension contrast is significant: **p=7.3e-04** at σ=0.25 and
   **p=8.6e-06** at σ=0.10.
2. **By the final model the dimension difference is gone.** 1.403 vs 1.471 (p=0.62) and
   3.412 vs 3.438 (p=0.75).

So it was never "ARD copes better at higher dimension" — asymptotically the two are
identical. **It is that d=8 starts the adaptive search already knowing, and d=6 starts
blind and needs about 30 evaluations to catch up.** At a budget of 48 with only 34 adaptive
evaluations at d=6, that head start is most of the run.

**Declared confound, and it is not small.** `n_init = 2d+2`, so the d=8 opening design has
18 points against d=6's 14, and the 0.10 inert weight share is split 4 ways at d=8 versus
2 ways at d=6 — each individual nuisance factor is *more* inert at d=8 and therefore easier
to identify. Both follow from the dimension change, so the contrast is honest as stated, but
"dimension" here bundles three things and this diagnostic does not separate them. Separating
them needs a d=6 arm at n_init=18, which is a new experiment and is not proposed here.

### Hypothesis (B) is refuted by a varied condition, not by a lengthscale value

Version 1 had no arm in which the prior differed, so nothing in it could attribute anything
*to* the prior. §2.4 adds one: the same recovered designs refit under `Gamma(3,6)`, built by
hand so that **exactly one** thing differs (the library's convenience constructor would have
changed the kernel wrapper, the outputscale prior and the parameter constraint at once).

| cell | shipped active ℓ | Gamma active ℓ | shipped in/act | Gamma in/act | p |
|---|---|---|---|---|---|
| d=6 σ=0.25 | 0.493 | 0.328 | **1.40** | **1.15** | 4.3e-07 |
| d=6 σ=0.10 | 0.404 | 0.326 | **3.41** | **1.84** | 5.3e-15 |
| d=8 σ=0.25 | 0.535 | 0.338 | 1.47 | 1.14 | 3.8e-06 |
| d=8 σ=0.10 | 0.459 | 0.334 | 3.44 | 1.85 | 1.8e-15 |

**Gamma(3,6) is significantly WORSE at the thing BO needs here** — it roughly halves ARD's
active-versus-inert separation in every cell. And on posterior-mean argmax error it is
indistinguishable: +0.0102, +0.0063, +0.0026, −0.0018 (Wilcoxon p = 0.15, 0.33, 0.40, 0.41,
clustered on 25 instances). So the shipped prior is not the problem, and the registered
sensitivity re-run is **NOT triggered and was NOT performed**. Had it been run on the old
reasoning, it would have made things worse and we would have had a "BO improves" number
obtained by switching priors after seeing BO lose.

### What the loss actually cost, measured

At n=46, the model that chose the final batch. Shape skill = 1 − var(residual)/var(truth)
along each axis through the true optimum; a shape-blind predictor scores 0 whatever its
level error.

| cell | shape skill, active axes | level error | x_opt → nearest training point |
|---|---|---|---|
| **d=6 σ=0.25** | **0.162** [0.010, 0.385] | 0.280 | 0.405 |
| d=6 σ=0.10 | 0.530 [0.195, 0.669] | 0.154 | 0.327 |
| d=8 σ=0.25 | 0.215 [0.048, 0.420] | 0.258 | 0.431 |
| d=8 σ=0.10 | 0.471 [0.252, 0.652] | 0.182 | 0.504 |

In the primary cell the surrogate captures **16% of the shape variance along the axes that
matter**, and is off by 0.28 in level at a point 0.41 from its nearest observation. There is
no dimension effect (p=0.22, 0.40) — surrogate quality here is governed by **noise**.

qLogEI's own behaviour is sane and it is not corner-chasing: proposals sit at per-coordinate
RMS distance 0.266 → 0.242 from the optimum on the active subspace against a uniform null of
0.333, the posterior-mean argmax is at 0.198 against the same null, and boundary pinning
falls on **inert** coordinates 2.3× more often than active (0.145 vs 0.062) — which is
correct behaviour, not a pathology. (Version 1 reported 36% of proposals "on the box"
against a uniform reference of 1.2%. That reference was wrong by roughly two orders of
magnitude: qLogEI is a bounded maximiser of an acquisition whose exploration term peaks at
faces, so a uniform draw is not its operative null. No uniform reference is quoted now.)

### Consequences

1. **Nothing to change in E2.** The registered sensitivity is untriggered, and the
   counterfactual says it would have hurt.
2. **SAASBO is not indicated.** Its premise is that a better lengthscale prior helps. A
   different lengthscale prior measurably does not.
3. **`RESULTS-PERSON-A.md` §6b rewritten** with the corrected mechanism, and §7 carries
   defect #8.
4. **For B:** the d=6→d=8 flip now has a stated mechanism — timing of ARD discrimination,
   not its eventual strength — but the confound above means the paper should say
   "dimension, opening-design size and per-factor inertness move together here". The
   separate point from Q24 still stands: the DoE arm is d=6 only, so the arm that beat BO at
   six factors was absent at eight.

---

## 🔴 Q29 [B] · PRE-REGISTRATION · **the symmetric comparison: score BOTH methods at their own model's recommendation**

**Written and committed BEFORE the run. Nothing below depends on a number that does not yet exist.** The point of registering it is that the two existing rules are already known to favour opposite arms, so whoever picks the third one after seeing it has picked the answer.

### Why this is the deciding experiment

Q28 measured that **every cell reverses sign** depending on how the DoE arm is scored:

> **⚠️ PROVENANCE (T1.4a).** Rule-A figures below are **B's clone**. A's committed grid gives **−0.0595 / +0.0018 / −0.0284 / −0.0024** for the four cells — see the correction table in Q28 above. Rule B / rule C columns use the **unconstrained** DoE scoring that Q35 supersedes.

| cell | rule A (best observed) | rule B (its stage-4 recipe) |
|---|---|---|
| d=6 σ=0.25 | −0.0708 | **+0.2497** |
| d=6 σ=0.10 | +0.0042 | **+0.3450** |
| d=8 σ=0.25 | −0.0321 | **+0.2482** |
| d=8 σ=0.10 | +0.0015 | **+0.3170** |

Negative = DoE beats qLogEI. **So "BO loses to current practice" — the project's standing headline at both dimensions — rests entirely on an unregistered scoring choice**, which Q20 §3 flagged as open and which was never closed.

**Neither existing rule is the comparison a practitioner cares about.** Rule A scores *both* arms at their best measurement, which throws away the DoE pipeline's actual output — the thing stage 4 exists to produce. Rule B scores DoE at its model's recommendation but qLogEI at its best measurement, which is **not like-for-like** and flatters BO for exactly the reason rule A flatters DoE.

### The estimand

> **Rule C — symmetric.** Each method is scored at the point **its own model recommends**, evaluated on `truth()`:
> - **DoE** → the stage-4 confirmation recipe (the constrained argmax of its fitted second-order surface). Already computed.
> - **BO** → the **argmax of the GP posterior mean** over the same box. **E2 never recorded this**, which is why this needs a run rather than a re-analysis: `results/e2-grid.json` stores summary rows only, no visited points.
>
> Selection uses only what each method may see; scoring uses `truth()`, never the noisy observation (Q17).

This is the "what recipe would you actually hand the lab" comparison, and it is the only one of the three where both arms are asked the same question.

### The prediction, with its mechanism — **registered, falsifiable**

> **BO beats DoE under rule C**, at both dimensions, at σ=0.25.

Not a guess. E4 measured over-prediction at each model's own constrained argmax on the same oracle family: the **second-order surface over-promises by a median of +0.87 to +1.29** against a response bounded at 1.0, while the **GP over-promises by +0.25 to +0.33** — three to five times less. A method whose recommendation is that badly calibrated should recommend a worse *actual* recipe. Q28's own d=8 figure agrees: the DoE arm's over-prediction is **+1.55** in the cell where it wins under rule A.

**What would falsify it:** DoE matching or beating BO under rule C. That is a real possibility — over-promising at the recommendation and *landing somewhere bad* are different failures, and a badly-calibrated surface can still point uphill.

### The decision rule, fixed now

- **If BO wins under rule C and loses under rule A**, the honest report is that **the verdict is scoring-convention dependent**, both rules are reported with the per-cell table, and neither is promoted to the headline. It is *not* "BO wins after all."
- **If BO loses under rule C too**, then BO loses under every convention tried and the negative result is **robust** — a materially stronger claim than the current one, and it should be stated that way.
- **Either way rule A stays the registered primary** (Q20/`e2.yaml`). Rule C is a declared secondary. **This entry does not re-designate the headline**, because the headline cannot be chosen by the person who ran the tiebreak.

### Scope, fixed before running

Primary cell first — **d=6, σ=0.25, 25 instances × 2 seeds, qLogEI vs DoE**, budget 48, identical seeds and openings to E2. Extended to the other three cells only if the primary completes cleanly. Paired Wilcoxon at instance level (n=25) governs significance, instance bootstrap gives the interval, per Q20 §2.

### ✅ RESULT — the prediction holds, and the verdict is scoring-convention dependent

`scripts/q29_symmetric.py`, log at `results/q29-symmetric.log`. ~~**Fidelity gate passed first: rule A regenerates the stored `e2-grid.json` qLogEI rows at max |Δ| exactly 0.0 over 50 rows**, so this is the same computation E2 ran, not a lookalike.~~

> **🔶 EVERY NUMBER IN THIS SECTION IS STALE. Do not quote it. Two separate defects, both found in T1.4.**
>
> **1 — the fidelity gate proved nothing.** It ran in B's clone against B's untracked `e2-grid.json`, so "regenerates the stored grid at max |Δ| exactly 0.0" says only that B's regeneration matched B's copy. A's committed grid gives qLogEI **0.1553**, not 0.1641, and the rule-A difference **−0.0595**, not −0.0708. See the resolved Q29 discrepancy entry below.
>
> **2 — the two arms did not use the same locator, so rule C is not yet a like-for-like comparison.** The DoE arm located its recommendation with `metrics.constrained_argmax` at `n_restarts=20, raw_samples=4096, seed=seed`. The BO arm used a script-local `optimize_acqf(PosteriorMean(...), num_restarts=10, raw_samples=256)` — **unseeded, and a 16× smaller Sobol screen**. Under a rule whose whole point is "score each method where its own model points", an asymmetric *locator* puts part of the measured gap into the search rather than the model, and it favours the arm with the bigger screen — here the DoE arm, i.e. **against** the direction actually reported, so +0.2915 is if anything conservative. That is an argument for re-running it, not for keeping it.
>
> Fixed in `scripts/q29_symmetric.py` (both arms now call `constrained_argmax` at identical settings and the same per-campaign seed) and locked by `tests/test_q29_locator.py`, which checks it over the AST. **The table below is retained only so the corrected run can be diffed against it.**

| rule | qLogEI | DoE | DoE − qLogEI | 95% CI | p | verdict |
|---|---|---|---|---|---|---|
| **A** — best observed *(registered primary)* | 🔶 0.1641 | 🔶 0.0934 | 🔶 **−0.0708** | [−0.0878, −0.0528] | <0.0001 | **DoE better** |
| **C** — each model's own recommendation | 🔶 0.1207 | 🔶 0.4104 | 🔶 **+0.2915** | [+0.2630, +0.3223] | <0.0001 | **BO better** |

**The registered prediction was correct**, and by more than expected: under a symmetric rule BO does not merely win, it wins by four times the margin it loses by under rule A. The mechanism is the one registered in advance — the DoE arm's recommendation carries **0.41 regret against a response bounded at 1.0**, while its best *observed* point carries 0.09. Its model points somewhere much worse than the best place it happened to look. The GP's recommendation, by contrast, is **better than its own best observation** (0.1207 vs 0.1641): the posterior mean smooths noise, so the GP's named recipe beats the lucky-draw incumbent.

### What this does and does not establish

**It does not mean "BO wins after all",** and per the decision rule fixed before the run, the headline is not re-designated. What it establishes is stronger and less comfortable:

> **The E2 verdict is determined by the scoring convention, not by the methods.** On identical runs, identical seeds and identical data, DoE beats BO by −0.07 or loses to it by +0.29 depending on a choice the pre-registration never made.

Rule A is still the registered primary and still says DoE wins. Rule C is a declared secondary and says the opposite. **Both must be reported together**; quoting either alone is a choice of answer, and the project has now caught that same pattern in Q16, Q19, Q28 and here.

**The practitioner-facing reading**, which is what the paper is actually about: if you run the published DoE workflow and *make the recipe it recommends*, you do materially worse than BO. If you run it and instead **keep the best thing you happened to measure along the way**, you do better than BO. The DoE pipeline's own output is its weakest product — which is precisely the E4 over-prediction finding arriving from a second direction, in regret units.

### ✅ ALL FOUR CELLS — the reversal is universal, not a primary-cell artefact

`results/q29-symmetric-allcells.log`. ~~**Fidelity: rule A regenerates the stored grid at max |Δ| exactly 0.0 over 200 rows** — all four cells, not just the primary.~~ **🔶 That gate proved nothing: it regenerated B's numbers and compared them against B's own untracked grid (T1.4a). Superseded by Q34, which recomputes all four cells in A's clone with a single locator.**

> **⚠️ PROVENANCE (T1.4a).** Rule-A figures below are **B's clone**. A's committed grid gives **−0.0595 / +0.0018 / −0.0284 / −0.0024** for the four cells — see the correction table in Q28 above. Rule B / rule C columns use the **unconstrained** DoE scoring that Q35 supersedes.

| cell | rule A (best observed) | rule C (each model's rec) |
|---|---|---|
| d=6 σ=0.25 | **−0.0708** DoE better | **+0.2915** BO better |
| d=6 σ=0.10 | +0.0042 *null* | **+0.3598** BO better |
| d=8 σ=0.25 | **−0.0321** DoE better | **+0.2689** BO better |
| d=8 σ=0.10 | +0.0015 *null* | **+0.3253** BO better |

Every rule-C result p < 0.0001. **BO wins under the symmetric rule in every cell, at both dimensions and both noise levels**, by margins 4–9× larger than the margins by which it loses under rule A. And where rule A reports a *tie* (both σ=0.10 cells), rule C reports a decisive BO win — so the convention does not merely change the size of the effect, it changes whether there is one.

#### Two mechanism observations, both new

**The DoE recommendation's regret is almost invariant: 0.37 – 0.44 across every cell.** It barely moves with dimension (6 → 8) or with noise (0.25 → 0.10, a 2.5× change in measurement error). A quantity that ignores both is not being driven by measurement error — it is **geometry**. The fitted second-order surface extrapolates to roughly the same badly-chosen place regardless of how cleanly it measured. That is the same conclusion E4 reached from over-prediction, arriving independently through regret.

**The GP's recommendation beats its own best observation in all four cells** — ~~0.1207 vs 0.1641, 0.0694 vs 0.0839, 0.1029 vs 0.1253, 0.0838 vs 0.0959~~; consistently 15–20% better.

> **✅ THIS ONE SURVIVES, with A's numbers and the corrected locator (Q34).** Cell 4 against cell 2: **0.1232 vs 0.1553**, **0.0703 vs 0.0874**, **0.1056 vs 0.1247**, **0.0876 vs 0.0972** — the GP's named recipe beats its own luckiest measurement in all four cells, by 15–21%. The figures moved; the finding did not. It is also the one place where the two arms genuinely differ in kind: **the polynomial's model is worse than its data (0.42 vs 0.10) while the GP's model is better than its data.** The posterior mean smooths noise, so the model's named recipe is a better bet than whichever single measurement drew the luckiest reading. **The two arms therefore fail in opposite directions**: the polynomial's model is worse than its data, the GP's model is better than its data.

**This does not re-designate the headline** (decision rule fixed pre-run). Rule A remains the registered primary. What it does establish is that the E2 verdict is convention-dependent **everywhere it was measured**, which is a stronger and more reportable claim than the single-cell version.

### ⚠️ Discrepancy found while checking: `e2.log`'s headline disagrees with its own stored grid

> **✅ RESOLVED (T1.4). `report()` was never wrong. The two clones held two different E2 runs under one gitignored filename.** The entry as originally written is kept below, struck through, because the way it was wrong is the finding.

~~`results/e2.log` prints the primary-cell paired difference as **−0.0595** [−0.0792, −0.0373]. Recomputed directly from `results/e2-grid.json` — the data that same run persisted — it is **−0.0708**, and Q28's independent `doe-scoring.log` also gives −0.0708, as does this run.~~

~~**Three computations agree; the printed headline is the outlier**, off by about 19%. The direction, significance and conclusion are unchanged, so nothing downstream reverses — but it is the project's most-quoted number and the figure in the log is not the figure in the data. **A should reconcile `run_e2.py`'s `report()` against the stored grid before anything is written up from the printed table.**~~

#### What was actually going on

`results/e2-grid.json` was **gitignored** while five scripts and three fidelity gates anchored to it *by path*. So "recomputed directly from `results/e2-grid.json`" did not name one artefact — it named one filename per clone:

| | qLogEI mean regret | doe − qlogei, primary cell | execution |
|---|---|---|---|
| **A's clone** — the run behind `e2.log` and the committed grid | 0.1553 | **−0.0595** | sharded, 4 processes |
| **B's clone** | 0.1641 | **−0.0708** | sequential, 1 process |

Reproduced from the committed grid in `tests/test_e2_provenance.py`: the primary-cell figure is **−0.0595** under every aggregation tried — instance-mean, instance-median, run-level, and difference-of-medians (−0.0719, −0.0648, −0.0527 for the median variants, none of them −0.0708). `e2.log`, all four shard files and `docs/RESULTS-PERSON-A.md` §1 agree exactly.

**The three "independent" computations were not independent.** All three were run in B's clone against B's copy:

- `results/doe-scoring.log` prints qLogEI = **0.1666**, and 0.0958 − 0.1666 = −0.0708. Its DoE fidelity gate passed at 1e-9 — against B's grid.
- `results/q29-symmetric.log` prints qLogEI = **0.1641** and `FIDELITY vs results/e2-grid.json: max |delta| 0.000e+00 over 50 rows` — B regenerating B's numbers and matching B's grid.
- `results/e2-run1-unfiltered.log` was committed **with unresolved git conflict markers in it** (9 conflicts, `<<<<<<< HEAD` / `>>>>>>> f39d158`), so it carried both runs interleaved. The `−0.0708` a reader finds there is the `f39d158` side.

**A gate that compares a regeneration against an untracked file cannot detect this.** It can only report that a clone agrees with itself, which is exactly what all three did. `probe_e2_determinism.py` gets `max |delta| 0.000e+00` in A's clone too — the same verdict, the other number.

#### What is fixed

`results/e2-grid.json` and its four shards are now **tracked** (`.gitignore` carries the exception and the reason). `run_e2.py --merge` exists and reproduces the committed grid **byte-for-byte** from the committed shards, so `e2.log`'s opening line "merged 1300 rows from 4 shards" is now checkable rather than assertable. `tests/test_e2_provenance.py` guards all of it, including `test_the_guard_rejects_the_other_clones_number`, which feeds −0.0708 through the same comparison to prove the guard can fail.

#### What is NOT fixed, and is a real finding

**A's and B's runs genuinely disagree, and only on the two arms that call `optimize_acqf`.** `random`, `sobol`, `lhs`, `coord` and `doe` are identical to the digit across the two machines; `qlogei` and `qlognei` are not. The two runs differ in execution mode *and* in machine, so they cannot separate those explanations. `probe_e2_determinism.py` holds the machine fixed and varies only the mode — see the Q21 note below for what it also settles.

---

## 🔴 Q24 [A + B] · **"BO beats current practice" is not supported anywhere it was tested — and the d=8 table reads like the opposite**

> **STATUS: the missing d=8 arm is registered (Q27), built, and RUN.** The split proposed
> below is the one registered, unchanged. Result: **DoE beats qLogEI at d=8 σ=0.25,
> −0.0321, p=0.0003**, and is the best arm in the table — so the sentence this entry
> proposes, *"BO beats current practice is not supported at either dimension"*, strengthens
> to **refuted at both**.
>
> **Two things qualify that, and both belong in the same breath as the headline.** First,
> **Q28**: the DoE arm's scoring rule was never registered, and the other defensible rule
> reverses the sign at every cell — so this verdict is a verdict *about the registered
> rule*, which is the generous one for the arm that won. Second, **A still has not accepted
> the split**. Everything else in this entry stands as written.

### The asymmetry, which is the most misreadable thing in the E2 tables

`e2.yaml` scopes the DoE arm to **d=6 only** (`doe: {dim: [6]}`), on budget arithmetic. So:

| | result | but |
|---|---|---|
| **d=6** | BO **loses** to the DoE pipeline | current practice *was* tested here |
| **d=8** | BO **beats every arm run** | **current practice was not among them** |

**Therefore: "BO beats current practice" is not supported at either dimension.** At d=6 it was tested and went the other way; at d=8 it was never tested. At a glance the d=8 table reads as a clean BO win, and it is not one. **This sentence belongs in the write-up in roughly these words**, because a reader skimming two tables will take the opposite meaning. Credit to A's side for spotting it.

### The d=8 DoE arm is the missing comparison, and it is blocked on a real thing

It is the only run that would test BO against current practice **where BO is actually strong**. It needs the 48-measurement split defined at eight factors, registered before the run (Q20).

**Checked, and it does not currently close.** `screening_design(8, n_centre=4, n_derived=2)` gives **68** runs, so 68 + 27 + 1 = **96**, double the budget. Raising the fraction fails deliberately:

> `ValueError: no known minimum-aberration generator for 2^(8-4). Refusing to invent one: a poorly chosen generator silently confuses effects with each other and nothing downstream notices.`

That refusal is correct behaviour and is why the arm was deferred rather than fudged.

**The split that would close it**, for A to accept or reject **before** any d=8 DoE run:

```
stage 1   2^(8-4) resolution-IV screen, 16 runs + 4 centre     20
stage 2   face-centred CCD on the 4 kept factors               27
stage 4   confirmation                                          1
                                                          total 48
```

Identical in structure to d=6, so the two dimensions stay comparable. **It requires adding the standard 2^(8-4)_IV minimum-aberration generators to `designs.py`** — they are textbook (E=BCD, F=ACD, G=ABC, H=ABD) rather than invented, which is exactly the bar `designs.py` refuses to drop below. **Registering the split before the run is not optional here**: the d=6 result already went against BO, so a d=8 DoE arm designed after seeing that is a design chosen with a known incentive.

### Provenance correction — this session ran no E2

Recorded because it bears on how the replication is described, not to relitigate.

**This session did not run E2, sharded or otherwise.** ~~`scripts/run_e2.py` has **no sharding support at all** — no `argparse`, no shard flag — so a sharded run of it is not possible.~~ And the E2 commits (`fbb98e9`, `0aeee09`) are authored by **josephyung6686**, a different account from this session's.

> **⚠️ CORRECTION (T1.4) to the struck clause.** The inference is invalid. Sharding never lived in `run_e2.py` — it lives in **`scripts/run_e2_shard.py`**, which imports `run_e2` and runs one `(dim, sigma)` cell per process, and which shipped **in `0aeee09` itself**, the very commit that produced the sharded grid. So "no argparse in `run_e2.py`" was true and "a sharded run is not possible" did not follow from it. (`run_e2.py` now carries `--merge`, and it reproduces the committed grid byte-for-byte from the committed shards.)
>
> The authorship point stands, and there is now direct physical evidence for the *other* side of it: the BoTorch warnings in `results/e2-run1-unfiltered.log` carry venv paths reading `/Users/alanakwan/Personal Projects/nutrigene-ai-bo-ipsec/...`. **A second E2 run on B's machine did happen**, sequentially, and it disagrees with A's on `qlogei` and `qlognei` — see the resolved Q29 entry above for the table.

So if two E2 runs exist, they are **A's and the other session's** — not A's and this one's. **The replication may well be genuine, but its provenance has to be re-established before "reproduced across two independent runs" goes into a paper.** The same misattribution ran earlier: `run_e2.py` and its grid design were credited to this session and are A's.

~~**What does corroborate independently:** the Q21 solver-failure determination. Counted from `results/e2-run1-unfiltered.log` here (9 failures, per-cell rates, max 0.875%) and from the other session's own run (9 / 3400 = 0.26%) — same conclusion by different routes, **too rare to matter**.~~ Q21's repair rule is registered and has nothing to fire on, which should be stated plainly so the result is not re-opened later as an excuse.

> **⚠️ CORRECTION (T1.4) — the two routes are very likely the same route.** Both counts are **9**. The 9 in `results/e2-run1-unfiltered.log` are now known to be **B's**, from B's machine (venv paths). If "the other session's own run" is also B's, then the same 9 failures were counted twice and reported as mutual corroboration. Two counts of one artefact agreeing is not two routes agreeing.
>
> **A's actual second-try count has never been measured** — A's shard processes never had their stderr captured. It is being measured now: `scripts/probe_e2_determinism.py` regenerates both adaptive arms at all four cells on A's machine, and `results/e2-determinism.log` holds the warning stream. The registered 1% threshold is unchanged and predates all of this, so applying it to A's rate is applying the rule, not rewriting it.

---

## 🟠 Q23 [B raises, A confirms] · **`coord` is a second unpaired arm, and it was not declared**

Found while auditing A's modules during the E2 run. **Registered before the numbers landed; not fixed, deliberately.**

`e2.yaml:53` asserts `identical_initial_design_per_seed: true` without qualification, and `pairing_exempt` listed only `lhs`. **`baselines.py` never calls `initial_design`** — `coordinate_descent` starts from a random interior point. So the claim was false for **two** arms: one declared exempt, one silently.

**This is exactly the defect T9/Q18 found, one arm over.** A fairness field asserting something true of most arms and untrue of one, with nothing failing. The Q18 fix corrected `run_static_baseline` and the field's wording; it did not audit the arms that do not go through `run_static_baseline`, and `coord` is the only one.

### Declared, not fixed — for two reasons

**Pairing it may be wrong on the merits.** The docstring's reasoning for the random start is sound: *"A centre start would be a hidden advantage on an oracle whose optimum sits near the middle."* Seeding coordinate descent from the best of the shared 14-point opening would remove that objection, but it makes the arm **a different and stronger algorithm** — screen-then-descend — rather than the textbook baseline it is there to represent. Given Q22's finding that the landscape is ~93% additive, a coordinate method handed a good starting point would be a *very* strong arm, and the comparison would stop being the one the arm was added to make.

**And the numbers already exist.** `d=6` and `d=8 σ=0.25` are done. Changing an arm now means comparing a repaired `coord` against everything else's stored numbers — the same objection Q21 registers against partial re-runs.

### What this costs

`coord` is unpaired, so its comparison against qLogEI carries the extra variance that pairing exists to remove — the same cost `lhs` pays. It is a **wider interval, not a bias**: the starting point is drawn from the same distribution regardless of arm, so nothing systematically favours either side. **Report `coord` and `lhs` as the two unpaired arms**, with the reason, rather than letting a reader assume the whole table is paired.

**If A wants `coord` paired, that is a full re-grid under Q21's rule**, not a patch to one arm.

---

## 🟠 Q22 [B raises] · **the benchmark landscape is ~93% additive, and that is a limitations-section fact currently living in a test docstring**

**Written before the E2 numbers exist, because it changes how they must be read.**

`tests/test_baselines.py:98` discloses it in prose — *"The oracle is a sum of coordinate-wise-unimodal terms, so coordinate search should get close to the optimum… the limitation is recorded in the suite rather than discovered by a reviewer."* Recording it was right. **It was never quantified, and it is larger than "should get close" suggests.**

### Measured

Fitting a **purely additive** surrogate — a per-coordinate nonparametric mean, no interaction terms of any kind — to 3,000 uniform draws per instance on the shipped ensemble:

| | variance explained by a separable fit | range |
|---|---|---|
| d=6 | **0.930** | [0.926, 0.945] |
| d=8 | **0.927** | [0.907, 0.937] |

**Roughly 93% of the response is separable. Interaction accounts for about 7%.** (In-sample, ~72 additive parameters on 3,000 points, so the true share is maybe a point or two lower. It does not change the reading.)

This is by construction, not a bug: `peak_modulation` enters as `exp((f₀ − ½) · γᵀ / k_pairs)` with `gamma_max = 1.0`, which bounds how far interaction can move each factor's optimum.

### Why it matters, in three places

**1. The `coord` arm is not the straw man its "pre-empts an objection" framing implies.** On a 93%-additive landscape coordinate descent is a *strong* baseline, close to the right model for the problem. If qLogEI beats it, that is a real result. If it does not, the honest statement is **"on a near-separable landscape, cheap coordinate search is competitive with BO"** — a finding, not a failure, and one worth reporting plainly.

**2. It bears directly on E4's null.** The GP's failure to beat nearest-neighbour distance is easier to explain when the surface is nearly additive: a near-additive function is easy for *any* smooth model, so there is less for a GP's structure to exploit. This is a mechanism for the Q19 result, and it is testable — the sign flip across κ should track how much interaction each κ's sub-box actually exposes.

#### ❌ THAT PREDICTION WAS TESTED AND IT FAILED

**EXPLORATORY and post-hoc** — proposed after the sign flip was already known, so it was never confirmatory. Reported because a mechanism that was offered and then quietly dropped is worse than one that was offered and refuted.

Additive-fit R² *inside each κ's training sub-box* `[0, κ·x*]`, 2,000 draws per instance, 25 instances at d=6:

| κ | median additive R² in the sub-box | GP − NN (E4) |
|---|---|---|
| 0.6 | 0.9652 | **+0.1068** |
| 0.7 | 0.9670 | −0.0173 |
| 0.8 | 0.9656 | −0.0960 |
| 0.9 | 0.9645 | −0.1011 |

**Interaction exposure is flat across κ** — the whole range is 0.0025, while the discrimination difference swings by 0.21 and changes sign. **Separability does not explain the sign flip.** The proposed mechanism is refuted, and Q19's result remains unexplained.

**What survives:** the ~93% figure is still a transfer limitation, and it is still a candidate explanation for why the *pooled* GP-vs-distance difference is small. It is simply not the explanation for the *κ-dependence*.

**Still open, and worth someone's attention:** κ changes the training data, not only the scoring box, so the fitted surface genuinely differs — but what about it flips the GP's advantage between κ=0.6 and κ=0.8 is not established. **Do not let the 93% figure be cited as though it answered this.**

**3. It is the sharpest limit on transfer, and it cuts against the project's own premise.** The motivating study is *about* ECM protein interactions. A benchmark whose interaction term carries ~7% of the variance under-represents the phenomenon the paper exists to study. **Whatever E2 concludes, it is a conclusion about near-separable landscapes.**

### What B recommends

- **Report the 93% figure in limitations, with the method.** "Coordinate search does well" is a hint; a number is a limitation a reviewer can weigh.
- **Report qLogEI vs `coord` explicitly**, alongside qLogEI vs `doe`, under Alan's report-everything ruling. It is the arm that tests whether BO's machinery earns its complexity *on this landscape*.
- **Do not fix it by raising `gamma_max`.** That would be changing the benchmark after seeing which way the results went, and the ensemble is committed and version-stamped precisely to stop that. **A higher-interaction ensemble is a Phase 2 question**, generated deliberately and declared in advance as a separate arm of the study — not a patch.

---

## 🔴 Q21 [A + B] · **the acquisition solver is failing. The repair rule is registered NOW, before the failure rate or the regret numbers are known.**

**Written while `run_e2.py` is still executing, with `d=8` unfinished and `results/e2-grid.json` not yet on disk.** Check the timestamp. This entry is worthless if written afterwards, because every question it settles is one whose answer becomes obvious — and self-serving — once you know whether BO won.

### The problem

`results/e2.log` is accumulating BoTorch acquisition failures: *"Optimization failed on the second try, after generating a new set of initial conditions"* — 4 hard failures in the `d=6` half, plus `A not p.d., added jitter`. On a second-try failure BoTorch does not propose the point it wanted; it falls back to whatever candidates it has.

**Only the adaptive arms call `optimize_acqf`.** So this handicaps qLogEI and qLogNEI and nothing else. A "BO loses" result contaminated by it would be measuring a solver, not a method. (It is also why the rate matters and the raw count does not: 4 failures against ~1,800 optimisations in the `d=6` half is ~0.2%, which changes nothing. `d=8` is where this gets worse, and `d=8` had not finished when this was written.)

### Why this needs registering rather than just fixing

`e2.yaml` registers `no_per_method_tuning: true`, and it is the most-cited objection in this literature — tuning your own method while the baselines sit at defaults. **Raising `num_restarts` or `raw_samples` after seeing that BO underperformed is exactly that objection, whatever the intention.** But refusing to repair a genuine numerical failure is also wrong, and would let a solver bug masquerade as a scientific finding.

The distinction is real and it is decidable **only if the decision rule is fixed before the numbers are seen.**

### What is registered

**1. The repair decision is made on the FAILURE RATE ALONE, computed and acted on before the regret numbers are read.**

> Repair is triggered if second-try acquisition failures exceed **1% of BO batches** in any (dim, sigma) cell. Below that, the run stands and the rate is reported as a limitation.

The 1% threshold is set here, with the `d=6` rate (~0.2%) known and the `d=8` rate **not** known. It is deliberately set above the observed `d=6` rate so it cannot be a rule reverse-engineered to trigger, and low enough that a real `d=8` problem trips it.

**2. Permitted repairs are numerical only.** `num_restarts`, `raw_samples`, `retry` policy, jitter — parameters that change *whether the optimiser converges*, not *what it optimises*. Changing the acquisition function, `best_f` policy, kernel, or budget is not a repair.

**3. A repair is applied identically to every arm that uses the solver** — qLogEI and qLogNEI both, never one — and **the whole grid is re-run**, not the BO arms only. Re-running one arm against another arm's stored numbers compares two different computational conditions.

**4. Both runs are reported.** Pre-repair and post-repair, with the failure rate for each. If the repair changes the conclusion, *that is the finding* and it is stated plainly: the result was solver-sensitive.

**5. Repairing bumps `preregistration_version` again**, with the failure rate that triggered it recorded as the reason.

### What is explicitly forbidden

**Deciding to repair because BO lost.** If the failure rate is under the threshold and BO underperforms, the run stands and the solver is not touched. Under this rule that outcome is reported as-is — which is the entire point of writing the rule down while `d=8` is still running.

### ✅ DETERMINATION — computed from the completed run, **before reading the regret table**

Second-try acquisition failures per (dim, σ) cell, against BO acquisition calls (25 instances × 2 seeds × 2 adaptive arms × rounds per campaign — 9 at d=6, 8 at d=8):

| cell | failures | BO acqf calls | rate | vs 1% |
|---|---|---|---|---|
| d=6, σ=0.25 | 2 | 900 | 0.222% | below |
| d=6, σ=0.10 | 0 | 900 | 0.000% | below |
| **d=8, σ=0.25** | **7** | **800** | **0.875%** | **below — but close** |
| d=8, σ=0.10 | 0 | 800 | 0.000% | below |

**No cell trips the threshold. Under Q21 as registered, the run STANDS, the solver is NOT touched, and the result is reported as-is — including "BO loses".**

This is the rule doing the job it was written for. The threshold was fixed while `d=8` was still running and before any regret number existed; it now binds against the temptation to repair an unfavourable result. **Had it been written afterwards, 0.875% is exactly the number someone could have argued either side of.**

**Report as a limitation:** `d=8, σ=0.25` reached 0.875%, close enough to the line to be worth stating. All 9 failures fall in the two σ=0.25 cells — the failures concentrate at the higher noise level, which is where the GP fit is worst conditioned.

### ⚠️ The evidence was nearly lost

~~**`results/e2.log` as committed in `0aeee09` contains ZERO of these warnings** — 77 lines against the run's actual 224, with every BoTorch warning stripped. The determination above is not reproducible from the committed artefact.~~

~~The full log is restored as **`results/e2-run1-unfiltered.log`**. **A pre-registered decision rule is worth nothing if the evidence it consumes is filtered out of the record before anyone can check it** — and this one exonerates the run rather than condemning it, which is precisely why it must be auditable.~~

> **⚠️ CORRECTION (T1.4). The counts above are wrong, and the determination measures a different run from the one it licenses.**

**Nothing was filtered.** `results/e2.log` is the output of the **merge-and-report** step, not of the campaigns — its first line is "merged 1300 rows from 4 shards". No campaign ran in that process, so it contains no BoTorch warnings by construction rather than by stripping. A's four shard processes wrote their campaign output somewhere that was never captured.

**"224 lines" is not any run's log.** 224 was the line count of `results/e2-run1-unfiltered.log` *while it still contained unresolved conflict markers* — two runs interleaved, plus 27 marker lines. Separated: A's side is **78 lines and byte-identical to `results/e2.log`**; B's side is **167 lines** and holds all the warnings.

**All 9 "Optimization failed on the second try" warnings are from B's run on B's machine** — the venv paths in them read `/Users/alanakwan/...`. So the Q21 determination's per-cell rates (0.222% / 0% / 0.875% / 0%) characterise **B's sequential run**, while the run they were used to license is **A's sharded run, the one in the committed grid**. The rule was applied to the wrong artefact. Its structural denominators (900/900/800/800 acquisition calls) are unaffected, and the conclusion may well carry over — but "no cell trips the threshold" has not been established for the run that produced the numbers in the paper.

**A's own rate is being measured, not assumed.** `scripts/probe_e2_determinism.py` regenerates both adaptive arms at all four cells on A's machine and its stderr is captured in `results/e2-determinism.log`; the second-try count there is A's rate, evaluated against the same registered 1% threshold. The threshold is unchanged and was fixed long before this, so re-applying it is not re-deriving it.

The file itself is fixed: the conflict markers are resolved and it now opens with a provenance header stating whose run it is. **The original point stands and is now better evidenced than when it was made** — a pre-registered rule is worth nothing if the evidence it consumes cannot be audited, and this evidence turned out to belong to a different run than everyone assumed.

---

## 🔴 Q20 [A decides, B recommends] · E2 · **written while the grid is still running, deliberately**

**The E2 grid was launched before these were settled. Everything below is recorded with no E2 number in existence, which is the only reason it is worth anything.** If it is read after the numbers land, check the git timestamp against `results/e2-grid.json`.

### 1. `comparator: best_non_bo` is under-specified, and it is not the claim Alan is asking about

`e2.yaml:85` registers `primary_cell: {arm: qlogei, comparator: best_non_bo, dim: 6, sigma_rel: 0.25}`. Two separate problems.

**It is under-specified.** "Best non-BO" does not say best by which endpoint, selected per-instance or pooled, or whether qLogNEI counts. `run_e2.py:178` answers all three — pooled mean regret, `qlognei` excluded — but **those are implementation choices sitting outside the pre-registration**, which is how the point-set defect in Q16 and the primary-cell defect in Q19 both happened. Third occurrence of one pattern.

**It is a max-statistic.** The comparator is chosen after the results, as the strongest of ~5 arms. That direction is *conservative* for a "BO wins" claim — you are beating the best of five, not an average — so it does not inflate false positives, and the choice is defensible. But the interval and Wilcoxon *p* attached to a selected comparator are not those of a fixed comparison, and that has to be said out loud rather than left implicit.

**And it answers the wrong question.** The project's framing is a *domain* claim: BO against the procedure the published study actually ran. That is the **DoE arm**, specifically, not whichever arm happens to score best.

> **B's recommendation — register both, as two named estimands, neither chosen afterwards:**
>
> | | comparison | claim type |
> |---|---|---|
> | **Primary — domain** | `qlogei` vs `doe`, d=6, σ=0.25 | "BO beats current practice." The paper's actual thesis. Fixed in advance, not selected. |
> | **Co-primary — methods** | `qlogei` vs `best_non_bo` | "BO beats the strongest alternative we ran." Conservative, and labelled as a selected comparator. |
>
> **Per-instance selection of the comparator is forbidden** — that would be an oracle competitor that exists as no method, the same error as the oracle-best scoring that voided E2's first run.

### 2. Wilcoxon vs the bootstrap — which governs

`e2.yaml` registers `test: wilcoxon_signed_rank` **and** `bootstrap: instance_level` and does not say which decides.

> **B's recommendation:** the **Wilcoxon signed-rank test governs the yes/no**; the instance-level bootstrap reports the **magnitude and interval**. They answer different questions and neither is a check on the other. **If they disagree, the disagreement is reported, not resolved** — a signed-rank test disagreeing with a bootstrap of the mean is a fact about skew or an outlying landscape, and that is worth a sentence rather than a silent choice of whichever agrees.

**Verified good, so it is not on the list:** the clustering is right. `run_e2.py:168` averages seeds within an instance *before* testing, so both the Wilcoxon and the bootstrap see n=25, not n=50. That is the exact error `e2.yaml:74` says would be indefensible, and A avoided it.

### 3. Two smaller things in `e2.yaml`

**`preregistration_version` is still 1 after an in-place correction.** The header says *"If any of them must change afterwards, bump `preregistration_version` and say why."* `identical_initial_design_per_seed` was then corrected in place after B's T9/Q18 — the right thing to record, but it is a post-hoc edit to a pre-registration under the version that predates it. **By the file's own rule this is version 2.**

**`regret_on: noiseless_value_at_selected_point` does not define the DoE arm's selected point.** For every other arm the selected point is the observed argmax. The DoE arm's *output* is the stage-4 confirmation recipe, and `run_e2.py:120` scores it as reported-best over all 48 — so the confirmation counts only if it happens to be the observed argmax, which `results/doe-arm.log` says it is not, in 100% of runs at both noise levels. **This is not obviously wrong** — a practitioner does walk away with the best recipe they saw — but it is the more generous of two defensible rules, and it is unregistered. Say which one it is.

---

## 🔴 Q19 [B raises, A + B decide] · **E4's reported headline is not E4's registered primary, and they disagree in sign**

**This may reverse E4's headline. Raised before anything is written up, not after.**

Verified by re-running `scripts/run_e4.py --instances 25 --rho 2.0` on the current ensemble. Reproduces B's v2 pooled numbers exactly, so this is not a version or ensemble difference.

### The discrimination result is not one number, it is a sign flip

| κ | GP ρ | NN ρ | paired difference | interval clears zero |
|---|---|---|---|---|
| 0.6 | +0.590 | +0.483 | **+0.1068** [+0.0461, +0.1668] | **yes — GP better** |
| 0.7 | +0.404 | +0.422 | −0.0173 [−0.0745, +0.0415] | no |
| 0.8 | +0.272 | +0.368 | **−0.0960** [−0.1450, −0.0470] | **yes — GP worse** |
| 0.9 | +0.267 | +0.368 | **−0.1011** [−0.1481, −0.0561] | **yes — GP worse** |

Pooled: **−0.0269** [−0.0728, +0.0182]. **Three of four cells have intervals clear of zero, in opposite directions, and the pooled number is their average.** "No advantage" is arithmetically true and describes none of the four cells.

### 🔴 The part that matters: the reported headline is the wrong estimand

`configs/experiment/e4.yaml:106` registers `primary_cell: {kappa: 0.6, rho: 2.0}`, and Q16 restates it — *"E4's primary endpoint remains the discrimination Spearman (GP vs nearest-neighbour distance) at `primary_cell: {kappa: 0.6, rho: 2.0}`, with the equivalence bound at 0.08."* **A single cell, named in advance.**

`results/E4-RESULTS-v2.md:25` reports, labelled "pre-registered primary", the number **pooled across all four κ**: −0.027, "no advantage".

**Those are different quantities and they disagree in sign.** At the cell actually registered as primary, the GP is **better** by +0.1068 with an interval clear of zero — and **+0.107 exceeds the pre-registered equivalence bound of 0.08**, so the standing claim *"the advantage is below 0.08 — established, not merely unrefuted"* is false at the registered primary cell. It is true only of the pooled average.

**This is the same defect three times over in this project**, and B is raising it against B's own experiment rather than waiting for a reviewer: the ρ-trend that could not fail, the coverage primary that never named its point set, and now a primary cell that is named and then not reported. Each time the registered quantity and the reported quantity came apart.

### What B is NOT claiming

**Not that the GP wins.** κ=0.6 is the *most* extrapolated cell, the pooled estimate is negative, the two largest-κ cells are significantly negative, and the prior art in `E4-RESULTS-v2.md` says a null is the expected outcome under GP theory. A single favourable registered cell inside a negative surface is exactly the "corner-shaped claim" Q16 warns against.

**The honest reading is that E4 has no single headline.** The discrimination result is κ-dependent, the dependence is large, and it reverses sign across the registered grid.

### The decision, for A

Two defensible resolutions, and **B is deliberately not choosing**, because either choice made by the person who has seen the numbers is the thing pre-registration exists to prevent:

1. **The registered cell stands.** Report κ=0.6 as the confirmatory result — GP better, +0.107 [+0.046, +0.167], equivalence bound breached — and the other three κ as the pre-specified surface that contradicts it. Most faithful to what was written down. Reverses the headline.
2. **The pooled estimand was always the intent** and `primary_cell` was a mis-registration. Then say so explicitly, in the paper, with the date the discrepancy was found — and report the sign flip regardless, because pooling across it is what hides the finding.

**What must happen either way:** the per-κ table is reported in full. Pooling a sign flip into "no advantage" is not a summary, it is a cancellation.

### One reporting defect found alongside

`run_e4.py` prints `significant=False` for κ=0.8 and κ=0.9, whose intervals are [−0.145, −0.047] and [−0.148, −0.056] — **clear of zero**. The flag is one-sided and means "significant *advantage*", but it is unlabelled, so the output reads as "nothing here" next to two of the strongest effects on the grid. Anyone scanning this log would conclude the opposite of what it shows.

---

## 🟠 Q18 [A + B] · T9 · **the paired opening batch did not exist, and the test that said it did tested something else**

**B has implemented the part the spec already decided and is flagging the one part it did not. A: the LHS exemption below is the only genuinely new call and it needs your sign-off.**

### The defect, in two independent halves

`optimizers.initial_design`'s docstring says *"This must be identical across every method being compared, for a given seed… There is a test for it."* Both clauses were false.

**Half one — the arms shared nothing.** `initial_design` had exactly one caller, `campaign.py:280`, the BO arm. `run_static_baseline` generated all 48 points from the method's own generator and never called it. So random and LHS opened on a completely different batch from qLogEI.

**Half two — the pairing was destroyed at scoring even where it existed.** The ordering average permuted **all** `budget` points, scattering any shared opening through the curve. Pairing that survives design but not scoring is not pairing.

**And the test.** `test_initial_design_is_identical_across_methods_for_a_seed` called `initial_design` twice with the same seed and asserted equality. It tested determinism. It never touched a second method. **A test whose name carries the guarantee and whose body does not is worse than no test — it is where everyone stops looking.** Renamed to `test_initial_design_is_deterministic_for_a_seed`; the real cross-arm assertions are in `test_runner.py`.

### One thing nobody had noticed: **Sobol was already paired, for free**

`initial_design` *is* `sobol_design(bounds, 2d+2, seed)`, and a Sobol prefix is stable, so the natural 48-point Sobol design already began with exactly the shared opening. Verified and now guarded by a test, because it is the reason the policy costs that arm nothing and a change to either function would silently end it.

### What is registered

> **Every arm opens on the identical batch, in the identical order, and that segment is not shuffled.** Only the method-specific remainder is shuffled and averaged — which is also the segment spec §E2 computes AUC over.

**This half is not a new decision.** Spec §E2 already fixed it — *"The initial design must be identical across methods for a given seed — paired comparison at n=50 is the difference between a significant and a non-significant result. Test for it."* It was specified, never implemented, and guarded by a test that did not test it. Implementing it is not B deciding anything.

Cost by arm, which is why this was cheap: **Sobol — free**, already paired. **Random — free**, it has no global structure to damage. **LHS — expensive**, and hence:

### 🔶 THE ONE NEW CALL, AND IT IS A + B: **LHS is exempt**

A Latin hypercube's stratification is a property of the **whole** n-point set. A 14-point Sobol prefix plus a 34-point Latin-hypercube remainder **is not a Latin hypercube** — it is a straw man wearing the name of a baseline. The spec's own scoping is explicit that a baseline has to be good or the result is worthless.

So LHS runs **unpaired**, and is reported as the one unpaired arm with its wider interval and the reason stated. **B's reasoning, A's call.** The alternatives, both worse: pair it and report a hybrid under the `lhs` label, or drop the arm.

**What would change this:** if A can construct a Latin hypercube of 48 whose first 14 points are the shared opening and which still stratifies, the exemption is unnecessary and should go. B could not.

### Implemented

`runner.static_design(bounds, method, budget, seed, share_opening=None)`. `None` applies the registered policy — pair unless exempt. `True` **demands** pairing and raises on an exempt arm, so a caller who believes every arm is paired finds out rather than being quietly right for three arms and wrong for one. `False` opts out explicitly. Six tests, including one asserting unpaired LHS is still a real Latin hypercube — the exemption has to actually buy something — and one asserting the ordering average still applies to the remainder, so the pairing fix does not silently trade away the thing that makes a one-shot design comparable to an adaptive one.

**Deliberately not done:** wiring this into E2's driver. That is T11 and it is A's.

### ⚠️ FOLLOW-UP — the BO side of this guarantee lost its coupling, and was never asserted

Found while checking whether E2's numbers are still reproducible after `campaign.py` and `surrogate.py` were modified **post-E2** (Q26 / the lengthscale diagnostic).

**Reproducibility: confirmed fine.** Both changes are backward-compatible by default — `surrogate.build_gp` gained `lengthscale_prior="dim_scaled"`, which is the original path, and `batch_plan`/`CampaignConfig` gained `n_init=None`, which keeps `2d + 2`. The default opening is **bit-identical** across the change, so the committed E2 numbers reproduce from current `main`.

**But the coupling is gone.** `campaign.py` used to build its opening as `initial_design(bounds, seed)[:n_init]`; it now calls `sobol_design(bounds, n_init, seed)` directly. Identical today — `initial_design` *is* a Sobol design of `2d + 2` at the same seed, and the prefix is stable. **The static arms still follow `initial_design`; the BO arm no longer does.**

So Q18's pairing now rests on two independent code paths *happening* to agree. `initial_design` exists for exactly one purpose — to be the shared opening — so it is precisely the function someone would change. If it were changed, the arms would silently stop sharing an opening, E2's paired comparison would quietly become unpaired, and **`test_paired_arms_open_on_the_identical_batch` would still pass**, because it only checks the static side.

**Fixed:** `test_the_bo_arm_opens_on_initial_design_too` pins the invariant from the BO end. Verified discriminating rather than vacuous — it fails against a different seed and against a different design family.

**The general point, since this is now the fourth instance:** a guarantee enforced by two code paths agreeing is not enforced. It needs one shared source or a test that spans both. This one had neither.

---

## 🔴 Q16 [EITHER] · PRE-REGISTRATION, WRITTEN BEFORE THE NEXT RUN · **the (κ, ρ) grid is the over-prediction result. No single cell is the headline.**

**Committed before PF1 is re-run at the pre-registered regime, deliberately, so the history shows it was decided in advance and not selected afterwards.**

### The problem this fixes

The over-prediction endpoint has moved four times: unit cube → ρ=1.2 proposed as primary → ρ=2.0 adopted in v2 → ρ=3.0 floated as the strongest cell. **Every one of those moves followed seeing a result, and every one was individually defensible.** That is exactly the pattern pre-registration exists to stop — the cumulative effect is a headline chosen for its size, and no reader can tell the difference from outside.

It will happen again. ρ is still not a *declared factor*; it is a config value we keep re-picking. And the oracle has already changed once (v6 → v8); a corner-shaped claim would not survive another change, while a trend would.

### What is registered

**Estimand — a surface, not a point.** The full grid is the result and is reported in full:

```
kappa in {0.6, 0.7, 0.8, 0.9}   x   rho in {1.2, 1.5, 2.0, 3.0, inf}
```

**Primary claim, directional and falsifiable:**

> **Over-prediction increases monotonically with the extrapolation ratio ρ, and decreases monotonically with κ.**

Tested as a *trend across the grid*, not a contrast between two cells: per-instance Spearman of over-prediction against ρ (and against κ), aggregated to a single estimate **at instance level** with a cluster bootstrap. Four κ on one landscape are four measurements of one landscape, not four independent observations — B already fixed this nested-clustering bug once in `0fc2610`, and it applies here identically.

**Secondary claim:** over-prediction decreases with the instance's true depth. Now testable, because the shipped ensemble records `true_depth` per instance and it varies (0.109–0.135 at d=6).

**What would falsify it:** a non-monotone trend, or a bootstrap interval on the trend statistic that includes zero. Both are real possibilities — the trend must be demonstrated, not assumed from the four unit-cube numbers we happen to have.

**ρ = ∞ (the unit cube) stays in the grid** as the limiting case. It is not dropped for being indefensible; it is *reported as* the indefensible end of a continuum, which is more informative than deleting it.

### What this does NOT change

**B's v2 pre-registration stands untouched.** E4's primary endpoint remains the discrimination Spearman (GP vs nearest-neighbour distance) at `primary_cell: {kappa: 0.6, rho: 2.0}`, with the equivalence bound at 0.08. **This entry governs the over-prediction *characterisation*, which is the mechanism evidence, not the novel claim.** The two coexist: one cell carries the confirmatory test, the whole grid carries the description.

### Why a trend is the better scientific object anyway

*"Over-prediction rises with extrapolation ratio and falls with instance depth"* is a statement about when a second-order surrogate stops being trustworthy — which is the thing a practitioner actually needs, and it transfers to Phase 2 and Phase 3. *"Over-prediction is +9.2 at κ=0.6 in the unit cube"* is a fact about one corner of one synthetic ensemble and transfers nowhere.

**Signed off by A. B: object here before the run if you disagree, not after.**

### ⚠️ CORRECTION TO Q16, made after the first grid run and BEFORE E4 — **A registered a primary that could not fail**

PF1 ran the registered grid (40 instances × 4 κ × 5 ρ = 800 cells, `results/pf1-grid.log`). The ρ trend came back at **Spearman +1.0000, CI [+1.0000, +1.0000]** — a perfect score on every instance at every κ. That is not a strong result; it is the signature of a test that cannot fail.

**It is forced by geometry, and the proof is three lines.** `extended_box_bounds` gives `[0, min(1, ρ·κ·x*)]`, so the boxes are strictly **nested** in ρ — verified: upper bound 0.288 → 0.360 → 0.480 → 0.720 → 1.000. The fitted surface is *identical* across ρ (we fit once per (instance, κ) and reuse). The maximum of a fixed function over a larger set is ≥ its maximum over a subset, so `y_predicted` is monotone non-decreasing in ρ **by construction**. And `y_true` is bounded above by 1.0 because the oracle is peak-normalised. So `over_prediction = y_predicted − y_true` rises with ρ as a matter of arithmetic, not biology.

**This is the same defect A has flagged twice in other people's work this project** — E4's original non-separability check that could never pass, and A's own first DoE arm whose escape statistic was vacuously 0%. Registering it in a pre-registration is worse, because a pre-registration is exactly the document a reader trusts not to contain one. Recording it rather than quietly restating the endpoint.

#### The replacement primary, which can fail

> **The second-order model's prediction interval loses nominal coverage of the true response as ρ increases, and we report the ρ at which it crosses.**

This is falsifiable and it is the question a practitioner actually has — *how far past my data can I trust this interval?* It can come back null: A's earlier κ×ρ sweep measured **96–98% coverage at ρ = 1.2 at every κ**, i.e. perfectly calibrated in the published study's regime. If coverage holds at every ρ, the claim fails and that is a real finding.

**The κ trend stays as registered and it is genuine:** −0.2712 [−0.3988, −0.1450], instance-level bootstrap. Nothing forces it — κ changes the *training data*, not just the scoring box, so the fitted surface differs and the sign could have gone either way.

**The over-prediction surface stays, demoted to descriptive.** It is still worth printing; it is just not evidence of anything.

#### The registered secondary FAILED, in the opposite direction

> Registered: over-prediction *decreases* with instance true depth.
> **Measured: +0.3893 at κ=0.6 and +0.1285 at κ=0.9. Positive. The claim is refuted.**

Reported as a failed prediction, not quietly dropped. Caveat that cuts both ways: true depth spans only [0.1086, 0.1390] across the ensemble — by design, since the acceptance floor compresses it — so this test had little power and the positive sign should not be over-read either. **If we want depth as a real factor, the ensemble needs deliberate depth variation, which is an ensemble change and therefore a joint decision.**

#### One descriptive fact worth keeping

**Turning point was a saddle in 800 of 800 cells.** Zero maxima, zero minima, across 40 instances and four κ. That is now the fourth independent confirmation, after PF1's first run, B's E4 run, and the DoE arm. The spec's prediction of minima at low κ was 1-D reasoning applied to a 6-D surface and is comprehensively wrong.

### ✅ B'S ANSWER (T1) — **the replacement primary is accepted; the reported quantity is objected to**

A asked for an objection before the run rather than agreement, so both halves are here.

#### The direction claim IS falsifiable — and for a reason stronger than the one given

A's defence was that coverage came back 96–98% at ρ=1.2, so the claim *can* return null. That is evidence, not a proof, and it is the same kind of evidence the ρ-trend had before it was shown to be forced. The structural argument is available and it is three lines, in the same style as A's:

For a second-order model the regressor vector `x₀ = [1, x, x², xx']` **already contains the quadratic terms**. Scale `x` by λ and the quadratic block scales λ², so leverage `h = x₀ᵀ(XᵀX)⁻¹x₀` scales λ⁴ and the half-width `t·σ̂·√(1 + h)` scales **λ²**. The fitted surface's own divergence from a bounded truth also scales **λ²**. **Same order.** Neither term dominates by construction, and which one wins is decided by `σ̂`, the design geometry and the true curvature — none of which are forced.

Contrast with the withdrawn ρ-trend, where `y_true ≤ 1` was bounded and `y_pred` was monotone in ρ by box nesting, so the sign was arithmetic. **This one is a genuine race.** Confirmed in the committed grid — bias and interval grow at near-identical rates from ρ=1.2 to the cube:

| κ | over-prediction | PI width |
|---|---|---|
| 0.6 | ×63 | ×44 |
| 0.7 | ×30 | ×31 |
| 0.8 | ×21 | ×20 |
| 0.9 | ×12 | ×14 |

Had the interval grown an order slower, the claim would have been another tautology. It does not.

#### The objection: **"the ρ at which it crosses" presumes one crossing, and there appear to be two**

Ratio of median over-prediction to median half-width, from `results/pf1-grid.log`. Above 1 means the bias exceeds the interval:

| κ | ρ=1.2 | ρ=1.5 | ρ=2 | ρ=3 | cube |
|---|---|---|---|---|---|
| 0.6 | 1.04 | 1.74 | 2.11 | 2.19 | 1.50 |
| 0.7 | 1.21 | 1.74 | 1.98 | 1.79 | 1.19 |
| 0.8 | **0.89** | 1.35 | 1.38 | 1.19 | **0.92** |
| 0.9 | **0.98** | 1.15 | 1.12 | **0.92** | **0.83** |

**Non-monotone at every κ** — it rises to a peak around ρ=2–3 and falls back. **Caveat stated at the time, because it cut against the objection:** a ratio of two medians is *not* the coverage rate, and can be non-monotone while `P(|over| ≤ pi/2)` is monotone. So this raised a well-posedness risk; it did not establish one.

#### ⚠️ THE RATE HAS NOW BEEN COMPUTED, AND IT CORRECTS THE MECHANISM ABOVE

`scripts/pf1_coverage.py`, all 800 cells, `covered ⟺ |over| ≤ pi/2`, instance-level cluster bootstrap. Log at `results/pf1-coverage.log`. **Independently cross-checked against the median table above: all 20 cells agree in sign about whether coverage sits above or below 50%.**

| κ | ρ=1.2 | ρ=1.5 | ρ=2 | ρ=3 | cube |
|---|---|---|---|---|---|
| 0.6 | 0.475 | 0.075 | 0.025 | 0.000 | 0.100 |
| 0.7 | 0.325 | 0.100 | 0.075 | 0.100 | 0.175 |
| 0.8 | 0.525 | 0.300 | 0.300 | 0.425 | 0.550 |
| 0.9 | 0.575 | 0.300 | 0.350 | 0.575 | 0.625 |

**The conclusion holds. The mechanism given for it was wrong, and is corrected here rather than quietly restated.**

**There are ZERO crossings, not two.** The ratio table crosses **1**, which is the *50%* coverage mark, not the *nominal 95%* one. Coverage never reaches nominal anywhere on the grid — the highest cell is **0.625 against a nominal 0.95**, including at ρ=1.2. So the crossing ρ is undefined because **the interval never had nominal coverage to lose**, not because it loses it more than once. A stronger result than the objection claimed, arrived at by a worse route.

**The non-monotonicity was real** and reproduces on the actual rate at all four κ — dipping and then recovering toward the cube — so the saturation mechanism (the argmax stops moving outward once the box saturates while `σ̂·√(1+h)` keeps inflating) is supported. It is simply not a statement about crossings.

#### 🔴 THE DECISIVE DEFECT — **the registered sentence never says WHICH POINT SET**

This does **not** contradict A's 96–98% at ρ=1.2. **It measures a different point set.** A's figure is coverage over the design/domain; the table above is coverage **at the recipe the model tells you to run**. Both are legitimate, both are "coverage of the second-order prediction interval", and on the same registered sentence they return **opposite verdicts** — calibrated versus catastrophic.

**That ambiguity matters more than the monotonicity argument.** A primary endpoint that two people can compute correctly and disagree about is not a pre-registration; it is the thing pre-registration exists to prevent, in the one document a reader trusts not to contain it. It is also the third time in this project a registered quantity has turned out under-specified, after the ρ-tautology and the E4 non-separability check.

#### Amendment, for A to accept or reject — **supersedes the one first proposed here**

> **Coverage is registered at BOTH point sets, each as a surface over the (κ, ρ) grid:** at the second-order model's **constrained argmax** (decision-relevant, and the worst case, since the argmax is selected for high predicted value) and at a **fixed held-out set** (domain-wide, no selection effect). The crossing ρ is reported only where one exists.

This mirrors the structure E3 already uses for its two point sets, and applies Q16's own "the grid is the result" logic to its replacement primary instead of exempting it. **The gap between the two surfaces is itself informative** and should be reported — it is the difference between "this model is well calibrated" and "this model is well calibrated everywhere except where it sends you".

**What would falsify the claim:** coverage flat near nominal 95% across the whole grid, at both point sets.

---

## 🔴 Q14 [EITHER] · E4 HAS RUN. The mechanism is huge; the headline claim is null. Decide n BEFORE rerunning.

**A: read `results/E4-FIRST-RESULTS.md` before anything else.** 40 cells, 78 seconds, on your v8 ensemble.

**What worked, unambiguously:**

- Over-prediction is enormous and scales with κ exactly as designed: **+9.2 → +5.6 → +3.3 → +2.0**, against a response whose max is ~1.0. Every cell extrapolated (40/40).
- The GP over-promises **5–20× less** than the polynomial at every κ.
- **Your Q13 risk did not materialise: 0/40 cells had the peak inside the training corner.** The validity check stays regardless.
- Headroom healthy everywhere (0.83–0.88, threshold 0.95). Practitioner-fit failures: 0/40.

**What did not:**

> **The GP does not beat plain nearest-neighbour distance. Pooled +0.051, CI [−0.003, +0.100], not significant.** Same at every κ. Against the polynomial's own interval width it is +0.004 — flatly nothing.

That is the comparison E4 was built around. On this evidence the honest statement is *the GP is an expensive distance function*.

**But it is a power problem, not a flat null.** All four κ point the same way; the pooled interval misses zero by 0.003; headroom confirms the comparison could have resolved a difference. Instances needed at the observed effect: **~31 at κ=0.6, ~44 at κ=0.8, ~10 at κ=0.9.** We have 10. **The full grid costs 78 seconds — 40 instances is about five minutes.**

**THE DECISION, AND IT MUST BE MADE BEFORE THE RERUN.** Raising n after seeing a result that missed significance, then reporting it as though n had been chosen in advance, is what makes a finding unpublishable. If we scale: bump `preregistration_version` to 2 and state in the paper — *"the first run at the pre-registered n was underpowered for the paired comparison; n was raised on a power calculation performed on that run."* Defensible. A silent rerun is not.

**B's recommendation:** bundle the n decision with Q12 into a single version-2 pre-registration, then run once.

> ### ✅ A's side of Q14 is done — **the d=6 ensemble is extended to 40.** `n_instances_if_ensemble_extended: 40  # Needs A` is satisfied.
>
> **Agreed on the substance:** raise n, bump the pre-registration, state the power calculation in the paper. Silent reruns are how findings become unpublishable. B's v2 wording is right.
>
> **Extending is safe, and A verified it rather than asserting it.** Instances are drawn independently per seed and `instance_id` hashes (dim, seed, oracle_version), so seeds 25–39 cannot perturb 0–24. Confirmed by regenerating three committed seeds and comparing the **landscapes**, not just the parameters: `max |f(X) − f'(X)| = 0.000e+00`, identical `instance_id`. Locked as `test_regenerating_a_committed_seed_reproduces_it_exactly`.
>
> **Only d=6 was extended.** E4 is d=6-only by pre-registration, and E2's grid is 25 × 2 seeds, so d=8 stays at 25. Say if you want d=8 raised too.
>
> #### ⚠️ A correction to A's own PF2, found while doing this
>
> The version field earned its keep. Rebuilding the sampler config by hand gave a **different `oracle_version`** for numerically identical landscapes — because a bare `SamplerConfig()` carries `accept_floor = 0.045`, the **v6 spec's** value, while the shipped ensemble was generated at **0.1083**.
>
> **That had already corrupted a number A reported.** PF2.3's "v8 shipped" acceptance rate of *100% / 100%* was measured at the easier floor. **Corrected: 70% (d=6), 80% (d=8)** at the real floor. The v8 case is unchanged — v6 is 6.395% and 0.105% — but the honest figure is 70/80, and anywhere the 100% was quoted needs fixing.
>
> Closed properly rather than patched: `boec.oracles.SHIPPED_CONFIG` is now the one object that generated what is on disk, asserted against `ENSEMBLE_VERSION` in the suite, with a second test that fails if the bare defaults ever drift into matching it. **Do not rebuild the config by hand.**

### Unpredicted finding, worth its own line

**Every fitted surface was a saddle. 40/40.** No maxima, no minima. The spec predicted a mix and specifically warned that low κ would give *minima*. It was wrong, cleanly. This is exactly why the stationary-point **distribution** was required instead of a bare escape rate — a rate would have hidden it.

---

## 🟠 Q12 [EITHER] · A was right, and the numbers now say so

A argued the unit cube is indefensible: 2–4× extrapolation in all six coordinates at once, against the published study's 1.2× in one.

**The run confirms it.** At over-prediction +9.2 with an interval width ~7 on a response of max 1.0, **"the traditional method's interval is too narrow" is not available as a finding** — the interval covers almost anything. A reviewer would call the comparison staged and be right.

`extended_box_bounds(x_star, kappa, rho)` is in `designs.py`, tested, with the default reproducing current behaviour exactly. **This is now a config decision, not a code change.**

**B agrees with A.** Recommend κ=0.6, ρ=2.0 primary, unit cube reported as a limiting case — folded into the same version-2 bump as Q14.

---

## ✅ Q13 [RESOLVED 2026-08-08] · A's three deviations from spec §4 — **ACCEPTED by Alan. B does not exercise the veto.**

**Decision: A's v8 stands. Port it, use it, cite it as the ensemble.**

Reasoning on the record, so the paper can state it:

1. **The interaction term.** A showed by differentiation that the spec's `β` product **cannot move the optimum** — the bracket multiplying each factor's derivative contains no dependence on that factor. Measured shift over 276 instances: `0.00e+00`. This is not a preference; it means §4.6's own non-separability acceptance check **can never pass**, and in the 8% with a negative bracket the cached optimum was landing below the true one, driving regret negative. Reverting would mean knowingly shipping that.
2. **Weight structure.** Equal weights cap depth at `1/d`, which kills the d=8 arm outright at σ_rel=0.25 — A measured 0 of 50 instances clearing the required depth. The 4-active/90% structure also matches the published 6→4 screening, giving the DoE arm something real to find, and gives ARD a 4.5–5.4× active-to-inert ratio against 1.0× under the spec. Under the spec the kernel comparison on the critical path had **no signal to discriminate on**.
3. **Depth formula.** Overstated true depth by a median 28.4%.

**The risk A flagged as landing in B's lane is now tested and did not occur.** `run_e4_cell` locates the true optimum and refuses to pool any cell whose optimum sits inside the training corner: **0/40 across all four κ**. The check stays regardless — it costs one optimisation per cell and is the difference between a null result and a silently meaningless one.

**Consequence for the write-up:** the ensemble is `biphasic-hill-v8`, not spec §4 as written. Doc 1 §4 is now historical and must be marked as superseded before anyone cites it.

## 🟠 Q15 [EITHER] · The DoE arm is built, and its result is the strongest one we have. One parameter decides it — pre-register that parameter.

`boec/doe.py`, 14 tests, `scripts/run_doe_arm.py`, log at `results/doe-arm.log`. Stage 1 screen (20) → stage 2 CCD on the survivors (27) → fit → **measure the predicted optimum (1)** = 48, the identical budget every other E2 arm gets.

**d=6, 10 landscapes × 2 seeds, scored with B's shared `over_prediction_at_constrained_argmax`:**

| | σ_rel = 0.10 | σ_rel = 0.25 |
|---|---|---|
| predicted optimum fell **outside** the stage-2 region | **100%** | **100%** |
| confirmation **under-delivered** vs the best design point | **100%** | **100%** |
| over-prediction, median [IQR] | **+0.73** [0.64, 1.00] | **+1.66** [1.41, 2.06] |
| sat *on* the stage-2 boundary | 0% | 0% |
| screen recovered the planted active factors | 94% | 86% |
| fitted surface turning point | saddle 20/20 | saddle 20/20 |

**Why this matters more than it looks, given Q14.** E4's standing objection is that we chose κ, so of course the model extrapolates. **This arm hides nothing.** It runs the published procedure over the full space, and the narrowness of stage 2 comes from the screen rather than from us. The over-promise still reproduces, on the same scale as E4a, against a response whose maximum is 1.0. With E4's discrimination claim null, this is the strongest single result in the project — and it is a *domain* claim, not a methods claim.

Two supporting details. The **0% on-boundary** rate says this is genuine extrapolation, not the constrained-optimiser signature `project_record.md` §E9 identified in the published optimum — so the two mechanisms are separable and we can discuss them independently. And **saddle 20/20** matches PF1 and B's E4 run exactly; three independent routes to the same unpredicted fact.

**The parameter, and why it is a question rather than a default.** Stage 2 explores `± stage2_half_width` around the best stage-1 run. A used 0.25.

> **At 0.5 stage 2 spans the whole range, the predicted optimum cannot fall outside it, and the escape statistic is a vacuous 0%.** A's first implementation did exactly that and reported 0% escape across 40 runs, which read as a clean negative result and was a tautology. Two tests now assert stage 2 is a strict sub-region and the search region strictly wider, so it cannot recur silently.

The headline moves 0% → 100% on one argument. **A has deliberately run no other value**, so the pre-registration is not retrofitted. Proposal: fix `stage2_half_width = 0.25` in the E2 config before any further runs, justified as "a local exploration spanning half the range — standard RSM practice of following a screen with a narrower design", and fold it into the same version-2 bump as Q12/Q14.

**One thing B should call:** dropped factors are currently held at the **best stage-1 run's** level. Holding them at **zero** is arguably closer to the published procedure, since Hall/Ogle's own optimum sits at zero for both dropped laminins. A chose the best-run level because it is what a practitioner does and keeps the confirmation point where the data speaks. Recorded either way in `DoEResult.dropped_held_at`.

### ✅ B'S CALL (T2) — **`best_stage1` is the primary, `zero` is a declared sensitivity. Both are reported.**

**Registered with neither arm run.** The `zero` policy did not exist in the code when this was decided — `doe.py` hardcoded the best-stage-1 level — so there was no number to choose between. That is the point, and it is why this entry can be trusted in a way the four moves of the over-prediction endpoint in Q16 cannot.

#### The decision rests on an asymmetry that is knowable in advance

The two policies are not symmetric candidates where one picks the more realistic. **One is conservative and one is flattering, and which is which follows from the screen's error rate without running either.**

- **`best_stage1` is conservative.** Stage 2 stays near the region stage 1 found good, so the fitted surface has *less* distance to extrapolate and the confirmation point is closer to data. **The over-promise is harder to demonstrate under this policy.**
- **`zero` is flattering, and the mechanism is screen error.** The screen recovers 94% of planted active factors at σ_rel = 0.10 and **86% at 0.25** (the table above). A wrongly dropped factor is an *active* one, and pinning an active factor to zero drags stage 2 into a genuinely worse region of the space. The fitted surface then has further to reach and **should over-promise more.**

**The conservative arm is the primary.** This is the same principle as the `stage2_half_width = 0.5` near-miss recorded above: the policy that makes the headline easiest to obtain is the one that must not be the default. Choosing the flattering arm as primary would be defensible on fidelity grounds and indefensible on every other.

#### Why fidelity to Hall/Ogle does not win here

It is the better argument for `zero` and it is real — their optimum does sit at zero for both dropped laminins. It loses for two reasons. **Their optimum sitting at zero is an output, not a held input**; the PDF cross-check established that fibronectin was boundary-clamped and Collagen IV extrapolated, so their zeros are what a constrained profiler *returned*, not what the design *held*. Reading a held level off a reported optimum assumes the answer. And fidelity to a procedure whose failure we are characterising is a weak reason to adopt its most failure-prone variant as the primary — **especially when we can simply report both.**

#### What is registered

| | policy | role |
|---|---|---|
| primary | `hold_dropped_at="best_stage1"` | the default in `doe.py`; every headline DoE number |
| sensitivity | `hold_dropped_at="zero"` | reported alongside, always, not only if it agrees |

**Both arms are reported whatever they show.** If `zero` over-promises more, that is the screen-error mechanism confirmed and it strengthens the finding. If it over-promises *less*, the a priori argument above is wrong and that is reported as a failed prediction, in the same way Q16's registered secondary was. **Neither outcome licenses swapping the primary.**

Cost is not a consideration: the DoE arm runs in **0.03 s per cell** (measured, d=6, single-threaded), so the sensitivity arm is free.

#### Implemented

`doe.py` takes `hold_dropped_at`, exports `HOLD_POLICIES`, records the policy on `DoEResult.hold_dropped_at` so a stored row can never be attributed to the wrong arm, and **raises on an unrecognised value rather than falling back to the default** — the same silent-substitution class as the T8 `runner.py` fall-through. Four tests, including one asserting the two policies produce genuinely different confirmation points, so the sensitivity cannot go vacuous the way `stage2_half_width = 0.5` did.

**For A:** the default carries the registered primary, so this needs nothing from `e2.yaml` to be correct. Carry `hold_dropped_at` into the E2 config explicitly anyway when T11 lands — an inherited default is not a pre-registration.

---

## 🟠 Q17 [A, but B should sanity-check] · E1 exposed a bias in how regret is scored. Fix it before E2 runs.

**E1 passed the gate**, and while passing it produced a number that cannot be true:

```
function     known optimum        BO best-so-far
branin            -0.3979              -0.3747     <-- BETTER than the optimum
```

Nothing beats the optimum. What is being reported is the best **observed** value, and the best of 48 noisy draws is systematically flattering — the winner is partly whichever point drew lucky noise. At σ_rel = 0.10 on a function whose optimum sits near zero, that bias is larger than the quantity being measured.

**Why it matters for E2 specifically, and why it is not self-cancelling.** All arms see the same noise level, so the naive hope is that the bias cancels in a comparison. It does not: the size of the upward bias depends on **how many distinct high-value points an arm samples**, and that differs by arm *by design*. Random and Sobol scatter 48 independent draws; BO concentrates its later batches in a small region and re-samples near-duplicates. Those are different numbers of effective lottery tickets. **An arm can therefore win E2 partly by buying more chances at good noise**, which is not the claim we want to make.

**The fix, which is standard and which A will implement:** score regret at the **noiseless value of the point the method selected**, not at the noisy observation. Selection still uses only what the method is allowed to see; scoring uses `truth()`, which exists precisely for this and is never shown to any model. Concretely, best-so-far becomes `max_t f_true(x_t)` over evaluated points, and the DoE arm's stage-4 confirmation is scored the same way — as it already is, via B's shared metric.

**This is also the concrete cost of the Q5 decision, now visible.** qLogEI's "best value seen so far" is exactly this inflated incumbent. Q5 registered qLogEI as primary with qLogNEI as a declared secondary; E1 shows the bias is real and measurable rather than theoretical, which makes reporting both more clearly worthwhile than it looked at the time.

**Not a licence to change anything else.** This is a fix to a *scoring* function, decided and written down **before E2 has been run even once**, so it cannot be a response to seeing an E2 number. Every other setting — kernel, acquisition, initial-design size, batch plan, seeds — stays exactly as pre-registered.

**One incidental E1 note, so nobody chases it:** gpytorch emits *"Very small noise values detected… rounding up to 1e-06"* throughout E1. That is a scale artefact of the standard test functions — Branin and Ackley span hundreds of units, so `Yvar / var(Y)` after `Standardize` falls below 1e-6. The biphasic oracle has range ~1 and does not trigger it. Not a bug in our noise path.

> ### ✅ B's sanity-check — **A's reasoning is right, the gate survives the fix, and the bias is ~12% of the effect**
>
> A asked for a sanity-check rather than agreement, so this is the measurement. Same `TorchEvaluator`, same σ_rel = 0.10, same 20 seeds, same budget 48 — **only the scoring changed**. Selection still sees nothing but the noisy observations.
>
> | function | known opt | BO (truth) | random (truth) | difference | 95% CI |
> |---|---|---|---|---|---|
> | branin | −0.3979 | −0.4116 | −0.9745 | +0.5629 | [+0.3083, +0.8601] |
> | **hartmann6** | 3.3224 | 2.6606 | 1.7466 | **+0.9140** | **[+0.6693, +1.1623]** |
> | ackley | 0.0000 | −20.0746 | −20.3301 | +0.2556 | [−1.0059, +1.6794] |
>
> **The gate holds.** Hartmann6 moves +1.03 → **+0.914**, interval nowhere near zero. E1's PASS is not an artefact of the bias.
>
> **A's non-cancellation argument is confirmed, and now has a number.** Inflation on Hartmann6 was **+0.155 for BO against +0.035 for random** — differential **+0.120**, in exactly the direction A predicted, because BO concentrates and re-samples while random scatters. It is real and it is not self-cancelling. It is also only ~12% of the 1.03 gap, so the fix sharpens E1 rather than rescuing it.
>
> **Branin's impossible number resolves cleanly.** Rescored on truth it is **−0.4116**, correctly *below* the optimum instead of above it. That is the fix demonstrated, not merely argued.
>
> **Two consequences worth carrying forward.**
>
> 1. **Every absolute figure in `results/e1.log` is flattering**, not just Branin's. Hartmann6's BO result is really 2.66, not 2.87 — 80% of the way to the optimum rather than 86%. Anywhere those numbers are quoted needs the debiased ones.
> 2. **On Ackley the bias is enormous — +4.15 (BO) and +4.47 (random)** — because its values sit near −20 and relative noise scales with magnitude. Best-observed is close to meaningless there, and the sign of the difference actually flips (−0.058 → +0.256) while staying null. This is a *second*, independent reason Ackley should not gate, on top of the one A declared in advance.
>
> **Caveat on these numbers.** This is an independent re-run, not a rescoring of A's stored traces, and the BO figures differ from `results/e1.log` by ~0.01 (Branin −0.3659 here vs −0.3747 there) from RNG ordering between the two scripts. It does not touch the conclusion, but it is not a byte-identical reproduction.
>
> ### ⚠️ Separately: spec §E1's fourth check is not implemented
>
> §E1 is not only the three textbook functions. It also requires: *"on a `β = 0` oracle instance, BO converges toward `sqrt(EC50·IC50)` per dimension."* `scripts/run_e1.py` runs Branin, Hartmann6 and Ackley only, so this one has never run.
>
> It matters more than the other three, because it is the only E1 check that exercises **our own landscape family** rather than borrowed benchmarks — the three standard functions would pass identically if the Hill oracle were broken.
>
> It is also cheap, and B has verified the construction: the shipped v8 ensemble is `peak_modulation`, so the equivalent of `β = 0` is `gamma = 0`, which makes the effective peak `x*_i · exp(0) = x*_i` in every coordinate. Confirmed on a real accepted instance — `f(x*) = 1.0` exactly, and `x*` equals `sqrt(ec50·ic50)` to machine precision, which is the spec's wording literally. **A's call whether to add it, since E1 is A's lane.**

---

## 🟡 Q7 [ALAN] · Author order, and whether the code can be released publicly

Neither blocks building. Both block posting the preprint.

---

## ✅ CLOSED

| | Question | Answer |
|---|---|---|
| **Q1** | Does the oracle exist? | **Yes — ported, merged, 310 tests passing. E4 has run on it.** |
| **Q2** | Who owns `designs.py`? | B owns it; A deleted their copy and is second reader. |
| **Q3** | Test-function wrappers? | Exist, wearing the Evaluator interface. |
| **Q4** | Evaluator interface? | Confirmed by execution. No adapters needed. |
| **Q5** | qLogEI vs qLogNEI? | Run both. qLogEI pre-registered primary, qLogNEI declared secondary. |
| **Q8** | `Yvar` floor? | `sigma_add**2 = 1e-4`. |
| **Q9** | Face-centred vs rotatable? | Face-centred — rotatable axials leave the sub-box. |
| **Q10** | The two pre-registered numbers | 512 candidates, τ = within-instance 0.80 quantile. **Version 2 now proposed — see Q14.** |
| **Q11** | First commit / layout | Done, pushed, shared. |
| **Q13** | Accept A's oracle deviations? | **Accepted 2026-08-08.** v8 is the ensemble. Risk to B's lane tested: 0/40. |
| **C1** | `observation_noise=True` at unrun points? | Silently averages training noise. Never used. |
| **C2** | Units for supplied noise? | Standardized, not raw. Off by 161× otherwise. |
| **C3** | `Normalize` without bounds? | Learns from data. Always pass explicit bounds. |
| **C4** | Discrete-candidate function? | `optimize_acqf_discrete(...)`. |
| **C5** | Does batch selection cluster? | No — it conditions on each pick. |
| **C6** | Grid too slow? | No. Full E4 is 78 seconds. |
| **C7** | 48-run pattern arithmetic? | Exact: 32 + 12 + 4. |
| **C8** | Stepwise conditioning via pinv? | Non-issue — rank filter guarantees full rank; agrees with lstsq to 9.7e-13. |

---

## Where B is up to

**E4 is built, tested, and has produced results on real landscapes** at both regimes. Reproduce with `python scripts/run_e4.py` and `python scripts/run_e4_robustness.py`.

**Figures are built** — `boec.figures`, three PNGs under `results/figures/`. Spec Build Step 7 is done, superseding the note that previously stood here.

**Blocked on:** the version-2 pre-registration — Q12, Q14, Q15 and Q16 together, as one bump. Ordering and owners are in `docs/TASKS.md`; two of the four (T1, T2) are waiting specifically on B.

**Latest from B: the d=8 DoE arm exists and has run.** Q24's missing comparison, registered
as **Q27** before it ran (`1b064e8`). `designs.py` now carries the 2^(8-4)_IV generators —
admitted on an enumeration of all 330 alternatives, not on a citation — and `run_doe_arm`
reads a registered per-dimension fraction instead of a hardcoded one, so 20 + 27 + 1 = 48
closes at eight factors exactly as it does at six, with every stage structurally identical.
Reproduce with `python scripts/run_e2_doe_d8.py`. Result: **DoE wins the primary cell**
(−0.0321, p=0.0003) and both registered predictions were correct. **A has not accepted the
split.**

**And the thing to read before quoting any of it — Q28.** Q27's own over-prediction figure
contradicted its own regret figure (lowest regret in the table, +1.55 over-promise in 100%
of cells), and the explanation is that **the DoE arm's scoring rule was never registered**.
The two defensible rules reverse the sign at **every cell, at both dimensions** — the d=6
headline included. Q20 §3 flagged this and it was left open. `scripts/diagnostic_doe_scoring.py`,
log at `results/doe-scoring.log`. **No number moves; the sentence written about them is what
is under-specified, and choosing the estimand is A's call under Q20 §1.**

**Also from B:** Q17 sanity-checked — the E1 gate survives the regret-scoring fix (Hartmann6 +1.03 → +0.914 [+0.669, +1.162]), and A's non-cancellation argument is confirmed at a differential of +0.120. Details in Q17.

**`runner.py` dispatch defect closed (T8).** `run_cell` sent *every* unrecognised method to the adaptive branch, so a `doe` cell — a method `GridCell` already documents as valid — ran a **Bayesian optimization campaign** and wrote a believable parquet under a `method-doe` filename. An E2 grid would have reported BO's numbers as the DoE baseline's. Now `doe` raises `NotImplementedError` pointing at `boec.doe.run_doe_arm`, unknown names raise `ValueError`, and six tests cover the dispatch. **The DoE arm still needs wiring in properly — that is A's, and it is T8's remaining half.**

**Not yet built:** an untested `nonlinear_inequality_constraints` path that matters only for Phase 3.

---

## Q32 — Merge of the two parallel Hall/Ogle digitization builds

Both sessions built a canonical dataset at `data/published/hall_ogle_2025_stage{1,2}.csv`
independently. Merged; below is what changed on each side and why. **Agreement was the
norm** — same 48 conditions, same design bar one cell each, identical responses on 44 of
48.

### Adopted from B

- **Schema.** Short factor names (`c`, `civ`, `ln411`, `fn`), integer `run_id`,
  `response_sd`, `flag_reason`. `run_replay_hall_ogle.py:72-76` already consumes these; a
  naming preference from a spec document does not justify breaking working code.
  Extended with `response_q1`/`response_q3` and a populated `extraction_2`.
- **The `stage2_18` median defect.** B's cross-check found our 4.22 was that column's Q3.
  Correct, and their diagnostic was the better one — *"a median sitting 0.04 below Q3
  while 2.59 above Q1 is a mis-detected median line, not a skewed distribution"* — because
  it is checkable from the stored triple with no image work.
- **`stage1_23` LN511 stays as it is.** B's note *"Recorded so nobody 'fixes' a correct
  cell"* was aimed at exactly the mistake this session was about to make.
- **Not reinstating an argmax claim** after the correction. Scope stays rank recovery.

### Corrections to B's build

1. **The second extraction is not lost.** `git log --diff-filter=A` was right that it was
   never committed, but it was on disk at `/Users/jy/BO/`, outside the repo, and
   duplicated in `~/Downloads/`. Now at `data/external/extraction_a/` with checksums.
   This premise drove four decisions in `build_published_dataset.py`, and one is
   substantive: **without a second reading of the design there was no way to detect a
   single mis-transcribed cell**, which is how the stage-1 LN511 dispute went unexamined.
2. **The Q3-as-median defect hits three boxes, not one.** `stage2_11` (4 px rule, →
   2.3645) and `stage2_05` (10 px rule, refused) carry it too. Hand-correcting the one
   instance a cross-check surfaced, without scanning for the rest, left two in place.
3. **`stage2_03` is extractable** (0.7056). Its box edges disagree by 4 px where a dot
   merges with the corner, against a ±3 px pair tolerance; widening to 4 recovers it and
   moves no other box at any tolerance from 4 to 10.
4. **The fibronectin control is the ALL-LOW row, not the FN-high row.** Every other
   protein's low level is 0 µg/mL while fibronectin's is 22, so `- - - -` and `- - - +`
   are both fibronectin-only and differ only in dose. The normaliser is the all-low row:
   0.9692 (stage 1) and 1.0275 (stage 2) against a target of 1, the same physical
   condition in both stages. `test_the_fibronectin_control_is_present_but_not_extractable`
   selected the FN-high row (0.7056) and concluded the normaliser was missing; it is
   present, correct, and stage 2's absolute scale is not compromised as that docstring
   claimed.
5. **`reading_error` is optical**, 0.025 / 0.037. The `0.07 × (max − min)` derivation gave
   0.0655 and 0.2496 — the latter a quarter of a response unit, larger than most
   between-condition differences it is meant to bound. **The fault is shared:** the doc it
   came from quoted percentages without defining "spread", and they only reconcile against
   the standard deviation. `EXTRACTION_METHOD.md` now defines it and says to quote the
   absolute figures.
6. **`response_sd = IQR/1.349` assumes normality** these 3–10-dot skewed samples do not
   satisfy (`stage2_08` → sd 4.38 on a response of 2.27). Retained because the replay
   reads it; `response_q1`/`response_q3` added alongside and preferred for new code.

### Corrections to A's build

1. **A nearly overwrote a correct cell.** Reasoning "the table is the design of record",
   A prepared to flip `stage1_23` LN511 to `-1`. The paper prints `+ + + + + -`
   (`pdf_crosscheck.md:129`). Recorded as defect 11 in `RESULTS-PERSON-A.md` — a new
   failure mode for the register: not a check that could not fail, but **a plausible
   authority rule applied without checking the authority.**
2. **A's three medians and one design cell** were all found only because B's cross-check
   existed to generalise from.

### Process

**`tests/test_published_dataset.py` mutates the repo.** Its round-trip test shells out to
the builder, which writes to `data/published/`. The logic is right — it captures content
first and compares — but a failing run leaves the tree modified, and a commit was made
from that state before it was noticed. Should write to `tmp_path`. Mitigated for now by
both builders producing byte-identical output: `build_published_dataset.py` is a thin
wrapper over `boec.published.write_canonical_csv`, so there is one producer rather than
two claiming the same path.

**Every deviation is written up for the paper** in `data/published/EXTRACTION_METHOD.md`
under "LIMITATIONS OF THE DIGITIZED DATASET" — L1 to L11, with evidence.

---

## Q31 AMENDMENT — re-run on the merged dataset, and rule C alongside

`scripts/run_replay_hall_ogle.py` · `results/replay-hall-ogle.log` · 40 seeds, budget 8,
opening 4 shared between arms.

**Why re-run.** The original run used the pre-merge dataset. Stage 1's data is
byte-identical after the merge, so those numbers were never stale. Stage 2's changed:
`stage2_03` became extractable (0.7056), `stage2_05` became unresolvable, `stage2_11`
moved 2.8102 → 2.3645 and `stage2_18` 3.48 → 3.4911. The **top-5 target set is unchanged**
at both stages, but stage 2's *candidate pool* is not — the optimizer could not propose
run 3 before and can now, and can no longer propose run 5.

### Rule A — the REGISTERED endpoint. Verdict unchanged: NOT SUPPORTED

| stage | | BO | random | random − BO | Wilcoxon |
|---|---|---|---|---|---|
| stage 2 | **re-run** | 3.50 | 3.50 | −0.025 [−0.475, +0.426] | p=0.9643 |
| stage 2 | *pre-merge (stale)* | *3.50* | *3.50* | *−0.075 [−0.475, +0.300]* | *p=0.7243* |
| stage 1 | **re-run** | 2.50 | 2.50 | +0.450 [+0.025, +0.850] | p=0.0565 |
| stage 1 | *pre-merge* | *2.50* | *2.50* | *+0.450 [+0.025, +0.850]* | *p=0.0565* |

**Stage 1 reproduces to the digit**, which is the check that the merge did not disturb it
and that the runner is deterministic under its seeds. Stage 2 moves slightly and stays
flatly null. The stage-1 bootstrap/Wilcoxon disagreement persists and is resolved the
same way — Q20 §2 gives Wilcoxon the verdict, so **not significant, claim not supported**.

The secondary reliability signal also reproduces: at stage 1, BO fails to find any top-5
condition within budget in **2 of 40** runs against random's **7 of 40**. Still secondary,
still not the registered endpoint, still not a rescue.

### Rule C — the model's recommendation. Also null, and slightly worse for BO

Both arms scored at the posterior-mean argmax over the whole candidate menu, using the
same GP and the same recommendation rule, so only point placement differs. Random has no
model of its own; lending it this one is what makes the contrast about design.

| stage | BO | random | random − BO | Wilcoxon | never recommends a top-5 |
|---|---|---|---|---|---|
| stage 2 | 8.50 | 8.50 | −0.100 [−0.600, +0.375] | p=0.7957 | BO 20/40, random 20/40 |
| stage 1 | 4.00 | 4.00 | −0.125 [−0.500, +0.225] | p=0.4982 | BO 12/40, random 10/40 |

**Rule C is not the registered endpoint and does not govern the claim.** Q31 §3 registered
"reaches the top-5 set in fewer evaluations", and reaching means evaluating — that is
rule A. Rule C is reported because the close-out decision asks for it, and it changes
nothing: both differences are negative (random marginally sooner) and neither is close to
significant.

**Worth noting against the rest of the project.** Elsewhere, recommending from the
posterior beat recommending the best observation by −0.0320 regret. Here it is *worse*:
at stage 2 half the runs never recommend a top-5 condition inside 8 evaluations, while
rule A finds one by 3.5. With 4 adaptive evaluations over 24 discrete candidates the
model has too little to go on, and the measurement beats the model. That is a statement
about this budget, not a contradiction of the earlier finding.

### Discrete candidate mode — verified on real data for the first time

Forward-compatibility requirement 2 has been in the spec since the start and had never
run against a real dataset. **320 proposals across both stages, every one an exact member
of the remaining candidate menu** — matched at 1e-9 on the raw proposal, before any
rounding, so a continuous proposal could not be rounded into a false match. Duplicate
proposals are asserted against separately. `propose(..., candidates=)` routes to
`optimize_acqf_discrete`, which returns rows of `choices` by construction; this checks the
construction rather than trusting it.

### The §3 ranking-source amendment is withdrawn

Q31 §3 registered the ranking as coming from "the reconciled extraction". The Stage-1
amendment substituted the single surviving one, on the premise that the second had died
with the deleted working folder. **That premise was wrong** — it was outside the repo and
is now at `data/external/extraction_a/`. The registered source exists and is what the
ranking uses.

"Reconciled" means our box median with the third-party dot mean as an independent check,
**not an average of the two** — they are different statistics and averaging them would mix
estimands (see `EXTRACTION_METHOD.md`). Measured directly rather than quoted:

| | top-5 by reconciled | top-5 by the third-party extraction | overlap |
|---|---|---|---|
| stage 1 | 3, 6, 9, 17, 20 | 3, 6, 14, 20, 23 | **3/5** |
| stage 2 | 9, 13, 17, 18, 19 | 8, 13, 17, 19, 22 | **3/5** |

**3/5 at both stages, exactly the figure Q31 §3 cited when fixing k=5.** The registration's
rationale holds. It also bounds the endpoint: which five conditions count as "top-5" is
only 3/5 stable across extractions, so the target set is itself a choice the data does not
fully determine — which is a further reason no argmax claim is available.

### Unchanged

**No argmax claim, at either stage, whatever the median correction did to B1.** Q31 §1
registered that in advance and specifically anticipated this: the durable reasons — the
top IQRs share a common band, and the paper never names a best stage-2 condition — are
untouched by anything in the merge. The scope stays rank recovery.

---

## 🔴 Q33 [A] · PRE-REGISTRATION · Extrapolation geometry on the published data

**Committed before the measurement runs.** One measurement: fit a second-order polynomial
and a GP to the same 25 published stage-2 conditions, locate each model's argmax, read off
the coordinates. The design region is coded `[-1, +1]`, so a coordinate outside that range
means the model extrapolated. **Geometry, not outcome — no ground-truth surface is needed
and none exists.**

Why it matters: Phase 2's replay came back null for structural reasons (25 candidates at a
budget of 8 cannot separate two methods), so without this the project's central mechanism
rests entirely on synthetic landscapes. This is the one real-data measurement available for
it, and the last thing this dataset will be asked.

### 0. GATE — PASSED, and reported before the claim it licenses

**Question: is the GP's argmax forced inside the design region by construction?** A GP's
posterior mean reverts toward its prior away from data, so if its argmax structurally
cannot land outside ±1, the primary claim is a tautology — the defect this project has
caught three times.

Run on the real stage-2 design geometry with synthetic monotone responses, production GP,
search over `[-2, +2]^4`:

| synthetic response | GP argmax | max coordinate beyond ±1 |
|---|---|---|
| `y = x0` | `[1.0126, -0.0001, 0.0, -0.0001]` | 0.0126 — outside |
| `y = x0+x1+x2+x3` | `[2.0, 2.0, 2.0, 2.0]` | **1.0000 — runs to the search-box edge** |

**The GP extrapolates freely when the data supports a trend**, in the second case all the
way to the boundary of the search box. The endpoint can return either answer. **Not a
tautology; proceeding.**

### 1. The registered claim

> **Primary:** the second-order polynomial's argmax lies outside the coded design region
> `[-1, +1]` in at least one coordinate; the GP's argmax does not, or lies closer to the
> region.
>
> **Measured by:** per-coordinate distance beyond ±1, and leverage
> `h = x0' (X'X)^-1 x0` at each recommendation.

### 2. Prediction, written before running, with its reasoning

> **I predict the primary claim HOLDS, with one specific caveat that may complicate it.**

**Polynomial — predicted outside, probably at the search-box edge in ≥1 coordinate.** A
full quadratic in 4 factors is 15 parameters against 24 usable conditions. Fitted to noisy
figure-read values, its stationary point is as likely to be a saddle as a maximum; when it
is, maximising over a bounded box drives the answer to the box wall. The published record
supports this — TheO's Collagen IV sat at coded **+1.40**, 40% beyond the highest level
tested, which is what a surface pointing outside its data looks like.

**GP — predicted closer, but I am NOT confident it stays inside.** The gate shows the GP
runs to the wall under a monotone trend, and stage 2's responses may well look monotone in
fibronectin: the top condition (run 13) sits at `FN = -1`, and several other top conditions
are low in FN. If the fitted surface reads as "less fibronectin is better", the GP will
push below −1 exactly as the polynomial does.

**So the most likely single outcome, stated concretely:** both models push FN toward or past
−1, and the polynomial *additionally* extrapolates in CIV or another coordinate where the
GP does not. That would be a **partial** result under §6 — closer, not inside.

**What would surprise me:** the GP extrapolating *further* than the polynomial. That is
outcome three, and per §6 it would mean the Phase 1 mechanism is a property of the
synthetic landscape rather than of the model classes. **It gets reported at least as
prominently if it happens.**

**What would falsify the primary claim:** the polynomial's argmax landing inside ±1 in
every coordinate, or the GP's landing further out than the polynomial's.

### 3. Method, fixed now

- **Data:** stage 2 only, the merged canonical CSV at the committed hash. Coded space
  throughout. 24 of 25 conditions usable (`stage2_05`'s median is not separable).
- **One locator for both arms:** `metrics.constrained_argmax`, same restarts, same
  raw_samples, same seed. **Asserted by test**, not verified by reading — two optimizers at
  different screening budgets is the fifth-instance defect already logged here.
- **Not** `over_prediction_at_constrained_argmax`, which is a scorer, not a locator.
- **Search box `[-2, +2]^4`.** Justification: double the design half-width, comfortably
  containing TheO's coded +1.40 so the published case is representable, while bounding the
  numerical search. **The polynomial's unconstrained stationary point is reported
  separately**, so the extension bounds only the search, not the finding.
- **Production configuration for both arms.** No variant settings.

### 4. Stated before the numbers — what this cannot establish

- **No outcome claim for the GP's recommendation.** It was never built. The strongest
  available statement is *"the polynomial pointed outside its data, the published record
  shows what happened when it did, and the GP pointed somewhere else."* **Not "the GP would
  have worked."**
- **No general claim.** One study, one lab, one assay, 25 conditions read off figures.
- **No argmax claim.** The top-5 target set is only 3/5 stable between the two extractions.
- **Fibronectin's floor is a design constraint, not an optimum.** The published design could
  not evaluate FN below 22 µg/mL (coded −1). A recommendation at FN = −1 sits on a boundary
  the design imposed, and is reported as such **for either arm**. This is the documented
  second cause of TheO's failure and is not a modelling artifact.
- **Digitization limits.** ~0.037 optical reading error against a published per-condition
  SEM of 38–66% of the between-condition spread. **The source assay is the constraint, not
  the extraction**; both figures belong in the write-up.

### 5. The check on the whole exercise

**LOO error for both models via `batch_cross_validation` with per-fold refitting**, reported
prominently. If the GP fits these 25 conditions no better than the polynomial, the
recommendation comparison means much less, and that has to be visible rather than
footnoted.

---

## ✅ Q33 RESULT — the registered prediction HELD, and one check qualifies the whole thing

`scripts/run_q33_extrapolation.py` · `results/q33-extrapolation.log` ·
`tests/test_q33_extrapolation.py` (6 guards, including the gate and the single-locator
assertion). 24 usable of 25 stage-2 conditions, coded space, one locator for both arms.

### The measurement

| | c | civ | ln411 | fn | max beyond ±1 |
|---|---|---|---|---|---|
| **polynomial** | −0.4491 | **−2.0000** | 0.6851 | **−2.0000** | **1.0000** (at the search wall) |
| **GP** | −0.8437 | 0.6638 | 0.9581 | 0.3333 | **0.0000** |
| TheO (published) | 0.0028 | **+1.4000** | 0.1250 | −1.0000 | 0.4000 |

**The polynomial's distance is a lower bound set by my search box, not by the model.**
It sits exactly on the boundary in `civ` and `fn` at every extension tested:

| search box | polynomial argmax | beyond ±1 | GP argmax | beyond ±1 |
|---|---|---|---|---|
| ±1.0 | 0.154, **+1.000**, 0.460, **−1.000** | 0.000 | −0.844, 0.664, 0.958, 0.333 | 0 |
| ±1.5 | 0.310, **+1.500**, 0.472, **−1.500** | 0.500 | *identical* | 0 |
| ±2.0 | −0.449, **−2.000**, 0.685, **−2.000** | 1.000 | *identical* | 0 |
| ±3.0 | −0.596, **−3.000**, 0.809, **−3.000** | 2.000 | *identical* | 0 |
| ±5.0 | −0.889, **−5.000**, 1.056, **−5.000** | 4.000 | *identical* | 0 |

**The polynomial runs to whatever wall it is given; the GP's argmax is bit-identical at
every extension from ±1 to ±5.** The GP is not marginally inside — it is stable and
indifferent to the search domain.

**Why:** the polynomial's unconstrained stationary point is a **saddle** (Hessian
eigenvalues −1.828, −0.935, +0.072, +0.997) at `fn = +5.76`, 4.76 beyond the boundary.
A saddle has no interior maximum, so maximising it over any box lands on a wall by
construction. Its recommendation is not even directionally stable: `civ` flips from
**+1.5 to −2.0** as the box widens, because the two ridge directions trade places.

**At ±1 — a constrained optimiser, which is what JMP's profiler is — the polynomial gives
`civ = +1.000, fn = −1.000`.** That is TheO's signature: fibronectin pinned at its floor,
Collagen IV at or beyond its ceiling (published +1.40). The published optimum is what this
surface produces.

### Supporting quantities

| | polynomial | GP |
|---|---|---|
| leverage `h` at own recommendation | **9.188** | 0.487 |
| prediction at own recommendation | **5.785** | 1.967 |
| 95% interval half-width there | **4.815** | 0.746 |
| distance to TheO (euclidean) | 3.616 | 1.931 |

Mean leverage over the 24 design points is **0.625**; TheO's is 1.646. **The polynomial
recommends a point at 15× the average leverage of its own design** and predicts **5.785**
against an observed best of **4.011** — 44% above anything measured — with an interval
[0.970, 10.601] wider than the entire range of the data. The GP's recommendation sits at
*below-average* leverage (0.487) and predicts within the observed range.

Distance between the two recommendations: **3.574**.

### ⚠️ The check that qualifies all of it — item 8, reported prominently as required

| model | LOO RMSE | LOO MAE |
|---|---|---|
| polynomial | 1.0720 | 0.8566 |
| GP | **0.9355** | **0.6745** |
| *sd of the 24 responses* | *1.0138* | — |

**Neither model predicts these conditions well.** The polynomial's LOO RMSE is **worse
than predicting the mean** (1.0720 against 1.0138 — 5.7% worse). The GP beats the mean by
only **7.7%**.

**This is the most important caveat in the result and it is not a footnote.** The
recommendation comparison is between two models that barely fit. The GP's advantage in
*geometry* is large and unambiguous; its advantage in *accuracy* is 7.7% over a constant.
Anyone quoting the extrapolation finding must quote this beside it.

### The registered prediction, scored

**The primary claim HELD in full**, and per §6 that is the first reading: *the mechanism
reproduces on real data* — the polynomial extrapolated where the GP did not.

**My stated most-likely outcome was WRONG, and diagnosably so.** I predicted a *partial*
result: both models pushing fibronectin toward or past −1, with the polynomial
additionally extrapolating in another coordinate. The reasoning was that the top condition
(run 13) sits at `fn = -1`, so the surface should read as "less fibronectin is better" and
drag the GP down with it. **The GP put fibronectin at +0.333** — the opposite direction.
The error was reading a single top condition as a monotone trend; the GP fits local
structure across all 24 and does not see one.

Getting the headline right for partly the wrong reason is worth recording as exactly that.

### What this does not establish — restated after the numbers, unchanged from §4

- **No outcome claim for the GP's recommendation.** It was never built. The statement is
  *"the polynomial pointed outside its data, the published record shows what happened when
  it did, and the GP pointed somewhere else"* — **not** "the GP would have worked".
- **Fibronectin at −1 is a design floor.** The polynomial reaches it and keeps going; the
  GP does not go there at all. For either arm, a recommendation at `fn = -1` reflects a
  bound the published design imposed.
- **One study, one lab, one assay, 24 conditions read off a figure**, against a published
  per-condition SEM of 38–66% of the between-condition spread. The source assay is the
  binding constraint, not the ~0.037 optical reading error.
- **No argmax claim** — the top-5 set is only 3/5 stable between the two extractions.

**This is the last question put to the published dataset.**

---

## 🔴 Q34 [A] · PRE-REGISTRATION · The design/surrogate/rule factorial — untangling E2's three-way confound

**Written before cells 5 and 6 exist. `results/q34-factorial.json` is not on disk; check the git timestamp against it.** Registered in response to T1.1.

### The confound, stated plainly

E2's headline compares `(structured design + polynomial + rule)` against `(adaptive design + GP + rule)`. **Three factors move at once**, and the write-up attributes the reversal to *model class*. The experiment as run cannot support that attribution. It is the same defect as Q26's `n_init`/dimension/inertness tangle, on the comparison that is actually the paper's thesis.

### The design space collapses, because rule A is surrogate-free

Under rule A the score is `max f_true(x_t)` over visited points — a property of the **design alone**. So the 2×2×2 is really six distinct quantities, not eight:

| cell | design | surrogate | rule | status |
|---|---|---|---|---|
| 1 | DoE | — | best observed | exists (grid `doe`) |
| 2 | BO | — | best observed | exists (grid `qlogei`) |
| 3 | DoE | polynomial | recommended | exists (stage-4 point) — **being recomputed here under the corrected locator** |
| 4 | BO | GP | recommended | exists (Q29 rule C) — **likewise** |
| 5 | **DoE** | **GP** | recommended | **NEW — the decisive cell** |
| 6 | **BO** | **polynomial** | recommended | **NEW** |

```
cell 5 − cell 3   surrogate effect, design held at DoE
cell 4 − cell 6   surrogate effect, design held at BO
cell 4 − cell 5   design effect, surrogate held at GP
cell 3 − cell 6   design effect, surrogate held at polynomial
```

**All four "recommended" cells are recomputed in one execution with one locator.** Cells 3 and 4 already have numbers, but they were produced with the asymmetric locator T1.4c fixed, so reusing them would put a known artefact inside three of the four contrasts. This run therefore also supersedes Q29's rule-C table.

### 📌 REGISTERED PRIMARY

> **cell 5 − cell 3**, at **d=6, σ_rel=0.25**, paired at instance level, **n=25**, seeds averaged within instance.
>
> *A Gaussian process fitted to the DoE arm's own collected data recommends a materially better condition than the second-order polynomial fitted to the same data.*

Reported as a paired difference with a bootstrap CI and a Wilcoxon *p*, the CI primary.

### 📌 REGISTERED PREDICTION, with the reasoning, before the run

**I predict the primary contrast is LARGE and favours the GP — cell 5 ≫ cell 3 — and that cell 5 lands modestly WORSE than cell 4. That is: mostly "the polynomial is the problem", with a smaller genuine design contribution.**

The mechanism I am betting on is **not** "GPs are better models". It is a structural asymmetry in how the two model classes behave *away from data*, which is exactly where a recommendation gets made:

1. **A quadratic has no interior maximum unless its Hessian is negative definite.** Q33 measured this on the published data: the fitted surface's stationary point was a **saddle** (eigenvalues −1.828, −0.935, +0.072, +0.997), so maximising it over any box lands on a **wall**, and which wall moved as the box widened. Cell 3's ~0.41 regret against a response bounded at 1.0, near-invariant across noise (0.25 → 0.10) and dimension (6 → 8), is the signature of geometry rather than measurement error.
2. **A GP posterior mean cannot do that.** Away from data it reverts to the standardized mean; it does not diverge. So the runaway extrapolation that drives cell 3 is *unavailable* to the GP on any design. This is why I expect the surrogate effect to be large rather than marginal.
3. **The design effect should be real but smaller.** BO's 48 points concentrate near high-value regions, giving the GP better local resolution where the argmax will be claimed; the DoE arm spends 20 of its 48 on a two-level screen with no interior points, and its stage 2 holds two dropped factors at fixed levels — so a GP fitted to DoE data has weak information about those coordinates and its posterior mean there will sit near the prior. That costs something, but it costs a *bounded* something.

**Cell 6, secondary prediction: frequent hard failures, and worse conditioning than cell 3 where it does fit.** A full second-order model needs p=28 terms at d=6 (n=48, 20 residual df) and p=45 at d=8 (n=48, **3** residual df). BO clusters by design, so I expect `fit_second_order` to raise on rank deficiency in a substantial fraction of d=8 instances, and condition numbers orders of magnitude above the CCD's 6.6. **The failure rate is a result, not an inconvenience** — it is the quantitative statement of "you cannot fit a response surface to adaptively-collected data", which is a real and citable asymmetry between the two methods.

**What would falsify the primary:** cell 5 ≈ cell 3. That is a live possibility and I want it on the record as such — if the DoE design's coverage is poor enough, a GP fitted to it may recommend just as badly, in which case **the design is the problem, the headline is wrong as currently framed, and it must be rewritten.** Point 3 above is the reason this is not a straw possibility: the two dropped factors are genuinely under-informed in the DoE data.

### 📌 DECISION RULE, fixed now

| outcome | conclusion |
|---|---|
| cell 5 ≈ cell 4, both ≫ cell 3 | **The polynomial is the problem, not the design.** The sharpest available version of the headline. |
| cell 5 ≈ cell 3, both ≪ cell 4 | **The design is the problem.** The headline is wrong as framed and gets rewritten. |
| cell 5 intermediate | **Both contribute.** Report the decomposition; do not round it to either story. |

"≈" means the paired 95% CI covers zero; "≫" means it excludes zero. Fixed before the numbers exist so it cannot be chosen to fit them.

### Guards

- **One locator for every cell**: `metrics.constrained_argmax` at `n_restarts=20, raw_samples=4096, seed=seed`, identical for GP and polynomial. Asserted in `tests/test_q34_factorial.py`, not verified by reading.
- **Scored on `truth()`**, never a noisy draw (Q17).
- **No silent drops.** Every rank-deficient or non-converged fit is recorded with its condition number and reported as a rate. An instance missing from a cell is reported as missing.
- **All four cells run** (d ∈ {6,8} × σ ∈ {0.10, 0.25}), not only the registered primary. Running only the cell where BO lost would be selection on the outcome.
- **No E2 number moves.** This is a re-analysis of regenerated campaigns plus two new scorings; `e2.yaml`'s registered rule A is untouched.

---

## ✅ Q35 RESULT [A] · T1.2 · The constrained-RSM arm — most of the published failure is a PRACTICE failure

`python scripts/run_q35_constrained_rsm.py --all-cells` · `results/q35-constrained-rsm.log` · script committed before it ran (`3ecd943`), with the commitment that all three scorings would be reported whichever way it came out.

**No new campaigns. No E2 number moves.** A third scoring of DoE runs E2 already made. Fidelity gate: the stage-2 surface is refitted from the stored measurements and reproduces the arm's own predicted optimum at **max |Δ| exactly 0.0** across all 200 runs, so this is the arm's model and not a lookalike.

### The three scorings

| cell | best observed | UNCONSTRAINED argmax *(what the paper did)* | CONSTRAINED argmax *(what practice prescribes)* |
|---|---|---|---|
| **d=6 σ=0.25 (primary)** | 0.0597 | **0.4163** | **0.1169** |
| d=6 σ=0.10 | 0.0544 | 0.4300 | 0.0856 |
| d=8 σ=0.25 | 0.0575 | 0.3766 | 0.1148 |
| d=8 σ=0.10 | 0.0500 | 0.4104 | 0.0877 |

| contrast (primary cell, paired, n=25) | difference | 95% CI | p |
|---|---|---|---|
| unconstrained − constrained | **+0.2995** | [+0.2790, +0.3228] | <0.0001 |
| constrained − best observed | **+0.0572** | [+0.0492, +0.0654] | <0.0001 |
| unconstrained − best observed | +0.3567 | [+0.3338, +0.3818] | <0.0001 |

**Constraining the argmax to the region the experiment actually explored removes about three quarters of the DoE arm's recommendation error, at every cell.** Regret falls from ~0.41 to ~0.09–0.12 against a response bounded at 1.0.

### The mechanism, and it is not noise

**The fitted second-order surface is a SADDLE in 200 of 200 runs. Every cell, every instance, every seed. Not one maximum, minimum or ridge.**

A saddle has no interior maximum, so maximising it over a box **must** land on a boundary — the escape is arithmetic, not bad luck, and the "predicted optimum fell outside the stage-2 region" rate is correspondingly **100%** everywhere. At the primary cell the stationary point itself sits *inside* the stage-2 region in 50/50 runs: the surface turns over inside the explored region, but in a saddle, so along at least one direction it keeps climbing to the wall.

Box & Draper ridge analysis, closed-form (no optimizer, so no search seed to argue about): the path of maxima on spheres about the stage-2 centroid **leaves the design region at radius ≈0.27 against a region corner radius of 0.50, in 200/200 runs**. The surface starts pointing out of the box less than a third of the way to its own corner.

**This is the same mechanism Q33 measured on the real published data** — there the stage-2 quadratic's stationary point was also a saddle (eigenvalues −1.828, −0.935, +0.072, +0.997) whose constrained argmax returned TheO's signature, CIV at +1.000 and FN at −1.000. The synthetic benchmark reproduces the published failure's *mechanism*, not merely its symptom, and it was not staged to.

### ⚠️ What this does to the headline — the claim narrows, and this must not be buried

**The entire reported rule-C gap is smaller than the effect of this one scoring choice on the classical arm alone.** Q29 reported BO ahead by **+0.2915** under rule C at the primary cell. Constrained-versus-unconstrained moves the DoE arm by **+0.2995** — more than the whole gap. Scored the way competent practice prescribes, the DoE arm's recommendation (0.1169) sits *beside* the BO arm's rule-C figure rather than 0.3 behind it.

So **"BO wins under rule C" is a statement about how the classical arm was scored, not a statement about BO.** The precise comparison must wait for Q34's cell 4, because Q29's 0.1207 is stale twice over (B's clone, and the asymmetric locator T1.4c fixed) — but the direction is not in doubt and the write-up cannot go out with the old framing.

**The defensible claim narrows to:** *unconstrained* polynomial surfaces extrapolate badly, and the source study used the unconstrained form. That is still a real finding about the published work — the safeguard existed in the literature since Box & Draper, and it was not applied — but it is a **practice** failure, not a **method** failure, and the paper must say so in those words.

### What survives unchanged

- **E2's registered primary is untouched.** Rule A is best-observed, which does not involve a surrogate at all. DoE still beats qLogEI at d=6 σ=0.25 by −0.0595.
- **Even constrained, the model's recommendation is significantly worse than the arm's own best measurement** (+0.0572, p<0.0001, and at every other cell too). Ridge analysis rescues most of the gap but does not close it: you would still have done better taking the best recipe you actually measured than the one the constrained surface names.
- The 100%-saddle result strengthens rather than weakens the geometric argument. It just relocates it: the problem is not that a quadratic is a bad *fit*, it is that a fitted quadratic almost never has an interior maximum, so **what you do with it** determines everything.

---

## ✅ Q37 RESULT [A] · T2.2 · The replay's "NOT SUPPORTED" is a power bound, and it should be written as one

`python scripts/run_q37_replay_power.py` · `results/q37-replay-power.log`. Reads nothing from and writes nothing to the registered replay artefacts — it re-derives the per-seed first-hit vectors by importing `run_replay_hall_ogle` and calling that module's own functions, so these are that run's numbers.

### The bound

| stage | N candidates | observed effect | **minimum detectable effect** | reported *p* |
|---|---|---|---|---|
| stage 2 | 24 | −0.025 evals | **0.68 evals** @ 80% power | 0.8746 |
| stage 1 | 23 | +0.450 evals | **0.68 evals** @ 80% power | 0.0565 |

> **Write it as:** *"the head start is bounded below 0.7 evaluations at 80% power"* — **not** *"BO is no faster than random"*.

**Stage 1's observed effect (+0.45) is smaller than stage 1's own minimum detectable effect (0.68).** A real advantage of exactly the size observed was undetectable by construction, which is the whole content of that *p* = 0.0565. The design did not weigh the claim and find it wanting; it could not lift it.

### The structural ceiling — why no method could separate here

| | stage 2 | stage 1 |
|---|---|---|
| fraction of the menu in the target set | 21% | 22% |
| **P(a top-5 is already in the shared 4-point opening)** | **0.635** | **0.654** |
| uniform-draw median evals to first hit | 3 | 3 |
| observed median (BO / random) | 3.5 / 3.5 | 2.5 / 2.5 |
| adaptive evaluations, of a budget of 8 | **4** | **4** |

Computed in closed form, not simulated: for a uniform draw without replacement, `P(T > m) = C(N−K, m)/C(N, m)`.

**Nearly two thirds of the seeds have a top-5 condition in the opening batch that both arms share, before either method has proposed anything.** Those seeds carry no information about the methods at all — they are ties by construction, and they are why the paired differences are mostly exactly zero. Of the eight evaluations, only four are adaptive.

### And the design removes the capability under test

`optimize_acqf_discrete` confines BO to the 23–25 conditions the published study actually ran. **BO cannot propose a condition the published design did not contain** — so the replay tests BO's *ordering* of someone else's menu, not its ability to search a space. The published design is also a saturated D-optimal screen and a face-centred CCD, i.e. already close to space-filling on that menu, which is exactly the case where an ordering advantage is smallest.

**This is a limitation of the replay as an instrument, and it was baked in by Q31's own design.** It does not reflect on BO and it should not be written as if it does.

### Two wrong versions of the power calculation, recorded

Both made the design look **powerful**, which is the opposite of the finding, so neither is quietly replaced:

1. **A continuous shift `+delta` on every seed.** Not achievable on an integer endpoint — an advantage means arriving one evaluation sooner on some *fraction* of seeds, never 0.1 evaluations sooner on all of them. Reported MDE 0.10.
2. **Imposing the null by `diff − diff.mean()`.** At stage 2 the mean is −0.025, so every *exact tie* became +0.025 and every difference became positive; Wilcoxon then rejects at any injected effect. Reported MDE 0.03, against a published CI of [−0.50, +0.40] that already bounds the resolvable effect near 0.6.

The correct construction injects the effect **discretely** (`+1` on a Bernoulli(*q*) subset, mean effect *q*) and imposes the null by **sign-flipping**, which is what the signed-rank null actually is and which preserves the ties. Both stages then return 0.68, and the observed effects and *p*-values fall into place around it.

**The tell in both cases was internal inconsistency, not intuition:** an MDE of 0.03 cannot coexist with a 95% CI of width 0.9 on the same data.

---

## ✅ Q38 RESULT [A] · T2.4 · Evaluations are not the cost a wet lab pays — rounds are

`python scripts/run_q38_cost_model.py` · `results/q38-cost-model.log`. Batch structure read out of `campaign.batch_plan` and the DoE arm's own stage split, not asserted; regrets from the committed grid.

**48 sequential evaluations is not 48 parallel wells.** A plate runs many conditions at once; what a lab waits for is the next plate, and hiPSC→endothelial differentiation is days per round. The binding cost is sequential rounds.

### d=6, σ=0.25 — the registered primary cell

| arm | evals | **rounds** | widest plate | mean regret | batch structure |
|---|---|---|---|---|---|
| **doe** | 48 | **3** | 27 | **0.0958** | stage1 20 + stage2 27 + confirmation 1 |
| **lhs** | 48 | **1** | 48 | **0.1270** | all 48 known before the first plate |
| coord | 48 | **48** | 1 | 0.1420 | one measurement at a time |
| qlognei | 48 | 10 | 14 | 0.1532 | opening 14, then 9 batches of q=4 |
| **qlogei** | 48 | **10** | 14 | 0.1553 | opening 14, then 9 batches of q=4 |
| sobol | 48 | 1 | 48 | 0.1724 | all 48 known before the first plate |
| random | 48 | 1 | 48 | 0.2216 | all 48 known before the first plate |

**On this axis the ranking is not close, and it is worse for BO than the evaluation axis shows.** The DoE pipeline reaches lower regret in **3** rounds than qLogEI reaches in **10**. Latin hypercube reaches lower regret than qLogEI in **one** — a single plate, designed before any measurement exists, with no model, no fitting and no sequential wait at all.

**At equal lab time the comparison is not 48-vs-48.** By the time the DoE arm has finished its 3 rounds, qLogEI has spent 22 of its 48 measurements (14 opening + 2 batches of 4). A fixed-evaluation comparison silently grants BO seven extra plate cycles.

**Coordinate descent is unusable in a wet lab at any regret** — 48 sequential rounds by definition. Its competitive regret at d=6 (Q3) should never be quoted without this beside it.

### What this does NOT show, stated so it is not over-read

E2 persisted summary rows, not per-evaluation curves, so **a regret-versus-rounds curve cannot be drawn from the committed grid** — only the endpoint regret and the exact round count. The curve needs curves persisted on a re-run and is not claimed here. The round counts themselves are exact, from `batch_plan` and the 20+27+1 split.

Also not claimed: that q=4 is the right batch width for BO. A larger q would cut BO's rounds at some cost in regret, and that trade-off is a real experiment nobody here has run. **What is claimed is narrower and harder to argue with: at the batch structure E2 actually ran, and which `e2.yaml` registered, BO pays 10 rounds where current practice pays 3.**

---

## ✅ T1.4b RESULT — the committed grid regenerates exactly, and Q21 finally measures the run it licenses

`python scripts/probe_e2_determinism.py` · `results/e2-determinism.log` · 400 rows, both adaptive arms, all four cells.

### 1. The grid is reproducible, and sharded == sequential is now demonstrated rather than promised

| cell | arm | n | max abs delta | regenerated mean | stored mean |
|---|---|---|---|---|---|
| d=6 σ=0.25 | qlogei | 50 | **0.000e+00** | 0.1553 | 0.1553 |
| d=6 σ=0.25 | qlognei | 50 | **0.000e+00** | 0.1532 | 0.1532 |
| d=6 σ=0.10 | qlogei / qlognei | 50 / 50 | **0.000e+00** | 0.0874 / 0.0808 | identical |
| d=8 σ=0.25 | qlogei / qlognei | 50 / 50 | **0.000e+00** | 0.1247 / 0.1105 | identical |
| d=8 σ=0.10 | qlogei / qlognei | 50 / 50 | **0.000e+00** | 0.0972 / 0.0849 | identical |

**This probe ran sequentially, in a single process. The grid it reproduces was built by merging four shard processes.** So the claim `run_e2_shard.py` made — that a sharded run and a sequential one produce identical output — is now demonstrated on the real data, having previously been backed by a citation to `tests/test_e2_shard.py`, **a file that has never existed**.

**Therefore the A/B divergence is not execution mode.** Sharded and sequential agree to the last bit on this machine, so the difference between A's qLogEI mean of 0.1553 and B's 0.1641 is the *machine*, not the schedule. The two runs differed in both, and this separates them.

That is a reproducibility finding in its own right and it belongs in the limitations: **the adaptive arms are bit-reproducible within a machine and are not reproducible across machines**, while `random`, `sobol`, `lhs`, `coord` and `doe` reproduce across both. The arms that diverge are exactly the arms that call `optimize_acqf`, i.e. that depend on LAPACK/BLAS reduction order in the GP fit and the L-BFGS-B path.

### 2. Q21 AMENDMENT — A's own solver-failure rate, measured for the first time

Q21's determination was computed from `results/e2-run1-unfiltered.log`, which T1.4a established is **B's run on B's machine**. A's shard processes never had stderr captured, so the rate for the run that produced the committed grid — and therefore every number in the paper — had never been measured. It has now.

| cell | A: 2nd-try failures | BO acqf calls | A rate | vs 1% | B's count | B rate |
|---|---|---|---|---|---|---|
| d=6 σ=0.25 | 1 | 900 | **0.111%** | below | 2 | 0.222% |
| d=6 σ=0.10 | 0 | 900 | **0.000%** | below | 0 | 0.000% |
| d=8 σ=0.25 | 2 | 800 | **0.250%** | below | 7 | **0.875%** |
| d=8 σ=0.10 | 1 | 800 | **0.125%** | below | 0 | 0.000% |
| **total** | **4** | 3400 | 0.118% | — | **9** | 0.265% |

**No cell trips the registered 1% threshold. Under Q21 as registered, the run STANDS, the solver is NOT touched, and the unfavourable result is reported as-is** — the same verdict as before, now reached from the run it actually licenses. Denominators are unchanged from Q21 (100 campaigns per cell × 9 rounds at d=6, × 8 at d=8).

**One recorded limitation changes owner.** Q21 reports "d=8 σ=0.25 reached 0.875%, close enough to the line to be worth stating" and "all 9 failures fall in the two σ=0.25 cells". Both describe **B's** run. A's worst cell is 0.250%, comfortably below, and A's failures do **not** concentrate at the higher noise level — one falls in d=8 σ=0.10. The "close to the line" caveat should be attributed to B's run rather than presented as a property of the result.

The threshold and the repair rule are untouched and predate all of this, so applying them to A's rate is applying the rule, not rewriting it.

---

## ✅ Q36 RESULT [A] · T2.1 · The reversal is family-specific. The mechanism is not.

`python scripts/run_q36_generality.py` · `results/q36-generality.log` · 25 seeds each, σ_rel=0.25, budget 48 — matched to E2's primary cell. Decision rule committed in `f0e4ec6` before the run.

### The registered question: does the E2 reversal reproduce off the Hill oracle?

**No — and not on either function, in opposite directions.**

| | rule A (DoE − BO) | rule C, DoE unconstrained | rule C, DoE constrained | reversal? |
|---|---|---|---|---|
| **Hill oracle** (E2, d=6 σ=0.25) | −0.0595 **DoE better** | *(BO better)* | *(see Q35)* | — the reference |
| **Hartmann6** | **+1.0032** [+0.79, +1.21] **BO better** | +2.1017 BO better | +1.0956 BO better | **NO** |
| **Ackley** | −21.09 DoE better ⚠️ **VOID** | −5.28 DoE better | −6.73 DoE better | **NO** |

**Per the registered decision rule: reproduces on neither, so the finding is family-specific and the paper must say so in those words.**

But the useful statement is sharper than "family-specific", because the two functions fail in **opposite** directions. It is not that BO wins everywhere else. **Which method wins is a property of the landscape, not of the methods** — three families, three different answers:

- **Hill oracle** — ~93% additive, coordinate-wise unimodal. A structured space-filling design with centre points does well; DoE wins rule A.
- **Hartmann6** — deceptive, non-additive, six local optima. Adaptive search earns its keep; BO wins everything.
- **Ackley** — needle in a haystack. Both methods fail badly (BO regret 21.06 of a ~22 range); DoE fails less.

### ⚠️ Ackley's rule-A row is VOID and is reported only to say so

**Ackley's optimum sits at the exact centre of the coded box, and every screening and CCD design in the DoE arm includes centre runs.** The DoE design therefore *contains the answer*, and its rule-A regret is **exactly 0.0000** for a reason that has nothing to do with sequential DoE being a good search strategy. The script detects this (`optimum_x == 0.5` in every coordinate) and prints the warning; the number must never be quoted as a DoE win. Rule C still means something there, because it asks what the fitted **surface** recommends rather than what the design happened to contain — and the surface does *not* recommend the centre (rule C regret 15.78 against rule A's 0.00).

This is a benchmark-design trap worth stating generally: **any centred test function silently rewards any design with centre runs.**

### What DOES generalise

**1. The scoring-convention effect, in direction, on all three families.** Constraining the DoE arm's argmax to the region actually explored improves it every time — Hill +0.2995 (Q35), Hartmann6 +1.0061 (2.9551 → 1.9490), Ackley +1.4521 (15.78 → 14.33). On Hartmann6 that single choice is ~half of the entire rule-C gap. **So the T1.2 finding is not an artefact of the Hill oracle**, and it is the part of this project's contribution that survives the generality test.

**2. The saddle mechanism, but only partly — and the exception is informative.**

| | stationary point of the fitted surface | predicted optimum outside stage-2 |
|---|---|---|
| Hill oracle | **saddle 200/200** | 200/200 |
| Hartmann6 | **saddle 25/25** | 25/25 |
| **Ackley** | **maximum 16/25**, saddle 9/25 | **15/25** |

On Ackley the quadratic often fits a genuine interior maximum, because Ackley is a broad bowl at coarse scale with fine oscillations on top — exactly the shape a second-order model *can* represent. So "the fitted surface is always a saddle" is **false as a general claim** and must not be written that way. The defensible version: *where the quadratic's Hessian is indefinite, the unconstrained argmax necessarily lands on a boundary, and on two of three landscape families it was indefinite in every single fit.*

### What this costs the headline, and what it buys

**Costs:** "current practice beats BO" cannot be stated as a general result. It is a result about one landscape family, and the paper must present it as calibrated to the published endothelial dataset rather than as a claim about optimisation.

**Buys:** the *scoring-convention* claim — the one T1.3 reframes the contribution around — now has support on three landscape families instead of one, including a standard non-additive benchmark. That is the more defensible contribution, and it is the one that generalises.

---

## ✅ Q34 RESULT [A] · T1.1 · The registered primary HELD in all four cells — and the rule-C claim collapses

`python scripts/run_q34_factorial.py --all-cells` · `results/q34-factorial.log`. Registered with its prediction and three-way decision rule in `a1420d4`, **before cells 5 and 6 existed**. One locator, `constrained_argmax` at `n_restarts=20, raw_samples=4096, seed=seed`, for all four recommended cells — asserted over the AST in `tests/test_q34_factorial.py`.

### The six quantities

| cell | d=6 σ=.25 | d=6 σ=.10 | d=8 σ=.25 | d=8 σ=.10 |
|---|---|---|---|---|
| 1 DoE / — / observed | 0.0958 | 0.0892 | 0.0963 | 0.0948 |
| 2 BO / — / observed | 0.1553 | 0.0874 | 0.1247 | 0.0972 |
| 3 DoE / polynomial / recommended | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| 4 BO / GP / recommended | 0.1232 | 0.0703 | 0.1056 | 0.0876 |
| **5 DoE / GP / recommended** | **0.1993** | **0.2728** | **0.1139** | **0.1168** |
| **6 BO / polynomial / recommended** | **0.5838** | **0.3956** | **0.6972** | **0.6784** |

### 📌 The registered primary held everywhere

| cell | 5 − 3 (surrogate, design fixed at DoE) | verdict |
|---|---|---|
| **d=6 σ=0.25 (registered)** | **−0.2171** [−0.2524, −0.1834] | GP better, p<0.0001 |
| d=6 σ=0.10 | −0.1573 [−0.1964, −0.1165] | GP better |
| d=8 σ=0.25 | −0.2628 [−0.2976, −0.2299] | GP better |
| d=8 σ=0.10 | −0.2936 [−0.3193, −0.2665] | GP better |

**A Gaussian process fitted to the DoE arm's own collected data recommends a materially better condition than the second-order polynomial fitted to the same data — at every cell, by a wide margin.**

### The decision rule, applied — and it does not give one answer

| cell | 4 − 5 (design, surrogate fixed at GP) | branch taken |
|---|---|---|
| d=6 σ=0.25 | −0.0761 [−0.1067, −0.0455] | **intermediate — both contribute** |
| d=6 σ=0.10 | **−0.2025** [−0.2466, −0.1595] | **design dominates** (bigger than the surrogate effect, −0.1573) |
| d=8 σ=0.25 | −0.0082 [−0.0317, +0.0162] **null** | **the polynomial is the problem, not the design** |
| d=8 σ=0.10 | −0.0292, **does not survive Holm** (p 0.0393 → 0.5114) | polynomial dominates |

**So the honest answer is not one of the three branches but a fourth: the decomposition is cell-dependent.** The surrogate effect is large and stable everywhere (0.16–0.29). The design effect ranges from **zero** (d=8 σ=0.25) to **larger than the surrogate effect** (d=6 σ=0.10). Reporting a single ratio would be rounding to a story, which the registration forbade.

### ⚠️ The consequence: "BO wins under rule C" does not survive a competently-scored classical arm

Combining cell 4 with Q35's constrained DoE scoring — same machine, same locator, and the two scripts agree on the shared cell to **max |Δ| = 0.0e+00**:

| cell | DoE (constrained) | BO (rule C) | difference | verdict |
|---|---|---|---|---|
| d=6 σ=0.25 | 0.1169 | 0.1232 | **−0.0063** [−0.0241, +0.0108] | **NULL** (p=0.56) |
| d=6 σ=0.10 | 0.0856 | 0.0703 | +0.0153 [+0.0040, +0.0269] | BO better (p=0.0088) |
| d=8 σ=0.25 | 0.1148 | 0.1056 | +0.0091 [−0.0055, +0.0239] | **NULL** (p=0.20) |
| d=8 σ=0.10 | 0.0877 | 0.0876 | +0.0001 [−0.0119, +0.0113] | **NULL** (p=0.79) |

**Q29 reported BO ahead under rule C by +0.2915 to +0.3598 at every cell. Scored the way classical practice prescribes, that becomes three nulls and one win of +0.0153.** The rule-C result was almost entirely an artefact of scoring the classical arm at an unconstrained argmax its own literature warns against.

**The swing decomposition, one machine and one locator, all four cells:**

| cell | DoE arm swing (A→C) | BO arm swing | ratio | DoE's share |
|---|---|---|---|---|
| d=6 σ=0.25 | +0.3205 | −0.0320 | **10.0 : 1** | **90.9%** |
| d=6 σ=0.10 | +0.3408 | −0.0171 | 19.9 : 1 | 95.2% |
| d=8 σ=0.25 | +0.2803 | −0.0191 | 14.7 : 1 | 93.6% |
| d=8 σ=0.10 | +0.3155 | −0.0096 | 33.0 : 1 | 97.1% |

The brief's ≈7:1 was an underestimate, and it mixed A's DoE arm with B's BO arm. Computed consistently it is **10:1 at the primary cell and up to 33:1**.

### 📌 Prediction scored: headline right, both specifics wrong

**Right:** cell 5 ≫ cell 3, and cell 5 worse than cell 4 — "mostly the polynomial, with a smaller real design contribution". That is what the primary cell shows.

**Wrong 1 — cell 6's failure rate.** I predicted "frequent hard failures", especially at d=8 where p=45 against n=48 leaves 3 residual df. **Zero failures in 200 runs.** Every fit succeeded.

**Wrong 2, and it reverses the standard intuition — the conditioning.** I predicted BO's clustered points would be badly conditioned for a quadratic. The opposite, at every cell:

| | cond(full second-order matrix), median |
|---|---|
| **DoE design** | **8.1e16 – 1.1e18** — numerically singular |
| **BO design** | **2.4e2 – 3.9e3** |

**You can fit a full second-order response surface to BO-collected data. You cannot fit one to the sequential-DoE arm's own 48 points.** The DoE arm's stage 1 is a two-level screen with no interior points and its stage 2 holds the dropped factors at fixed levels, so a full *d*-dimensional quadratic is unidentifiable on its own design — the pipeline is only viable *because* it screens down to 4 factors first. The common objection "you cannot fit a response surface to adaptively-collected data" is, on this benchmark, exactly backwards.

That said, cell 6's *recommendations* are the worst in the table (0.40–0.70). It fits; it just points somewhere terrible. **Estimability and usefulness are separate properties, and only the first ran the way the objection assumes.**

### Caveat carried from the registration

The 3−6 contrast confounds design with model dimensionality — cell 3's polynomial is reduced to the kept factors after screening, cell 6's is full *d*-dimensional, because the BO arm has no screening stage to reduce it. It is the weakest of the four contrasts and the registered primary does not depend on it.

---

## 📖 NUMBERING CONCORDANCE — this clone vs the close-out brief

**The close-out brief uses a different Q-numbering from this repository.** Recorded so neither person renumbers the other's work. This is defect 12's pattern one level up: two people, one namespace, no shared index.

| brief calls it | content | **this clone** |
|---|---|---|
| Q32 | the three DoE scorings | **Q35** |
| Q34 | design vs surrogate factorial | **Q34** *(same)* |
| Q35 | the estimand decision | **Q41** *(below — Q35 was taken)* |
| Q36 | permutation test + design conditioning | **Q42** / **Q43** *(never run here before now)* |
| — | generality on Hartmann6/Ackley | **Q36** *(this clone only)* |
| — | replay power bound | **Q37** |
| — | cost model | **Q38** |
| — | multiplicity | **Q39** |
| — | critical-difference diagrams | **Q40** |

---

## 📖 TASK A RESULT — literature verification. **One characterisation in the brief is refuted; one "missing" citation exists.**

Every item below was checked against a primary source or an indexed abstract. **Where I could not reach the full text I say so rather than accepting the characterisation** — that was the instruction and it changes two verdicts.

### A.1 — the repositioning citations

| source | verdict |
|---|---|
| **Picheny, Wagner & Ginsbourger 2013**, *Struct Multidiscip Optim* 48:607–626 | **PARTIALLY VERIFIED.** Confirmed: benchmarks **ten kriging-based** infill criteria on analytical problems under homoscedastic Gaussian noise, varying noise level, budget and initial sample size; reports that initial sample size and covariance choice are not critical. **It compares no non-kriging method**, so the DoE-vs-BO gap we claim is real. ⚠️ **The infill-versus-identification separation is NOT verified** — both open-access mirrors are behind an Anubis block. **Do not cite it for that distinction until the full text is read.** |
| **Nguyen et al. 2017** | ❌ **REFUTED AS CHARACTERISED. It is not the opposite sign to our result — it is a different quantity.** The paper is *"Regret for Expected Improvement over the Best-Observed Value and Stopping Condition"* (PMLR v77). Verified from the PDF: it compares the **incumbent ξ plugged into the EI acquisition function** — *"the incumbent ξ, i.e. E[max{0, f(x) − ξ}]. The incumbent ξ is often set to the best-observed value"* — against ξ = µ_max. **The words "recommend" and "report" do not occur.** That is an **infill** choice (where to sample next), not an **identification** choice (what to report at the end). **Citing it as a contrary finding would be a serious misreading**, which is exactly what the brief warned was most damaging. |
| **Wang & de Freitas 2014** | Confirmed *by Nguyen's own text* as EI regret theory using the µ_max incumbent — **also infill, not identification.** |
| **Bull 2011, Berk 2019** | ⚠️ **NOT VERIFIED.** Not checked against primary sources. Given the Nguyen result, the presumption should now be that this whole lineage is about the **acquisition incumbent**, not final recommendation, until shown otherwise. |
| **Gisperg et al. 2025**, *Biotechnol Bioeng* | ✅ Verified as a review — *"Bayesian Optimization in Bioprocess Engineering—Where Do We Stand Today?"*. ❗ **The no-reduction finding is NOT theirs.** They report **Rummukainen et al. (2024)**. The review **does not identify any gap in how the final recommended condition is chosen or scored** — so our contribution is not pre-empted by it. |
| **Narayanan et al. 2025**, *Nat Commun* | ⚠️ **"estimated" NOT VERIFIED.** Do not write "against *estimated* DoE" until the primary source is read. |

### A.2 — the RSM practice citations

**The 2019 survey** — *Int J Adv Manuf Technol* 10.1007/s00170-019-03809-9. **Scope is much narrower than "a survey of published RSM":** **49 papers from one journal (IJAMT), 2014–2017, 123 response surfaces, manufacturing only.** The bioprocess gap must be flagged explicitly.

- ✅ **"more than 75.29% of the models have presented a saddle shape"** — indexed and consistent across sources. **This corroborates our 200/200 saddle finding directly, on real published surfaces**, and is the stronger number for our purpose because it names the geometry rather than a consequence of it.
- ⚠️ **87.61% NOT VERIFIED.** It does not appear in any indexed excerpt, and the authors' definition of *"convexity incompatible with the optimization direction"* could not be read. **Do not use it.** §7.2.3 should cite the 75.29% saddle figure instead, which says what we need and is verified.
- ⚠️ Ridge/canonical-analysis usage rates: not reported in anything reachable.

**The 2003 ridge-analysis paper** — ✅ **VERIFIED, and stronger than the brief states.** Ridge analysis *"does not guarantee the global maximum or minimum point of response in the experimental region for non-spherical designs such as face-centered designs, Box-Behnken designs, and two-level factorial designs."* Hall/Ogle used a **face-centred CCD**. The same work finds the **desirability function more effective than ridge analysis** for such designs — so the textbook safeguard a reviewer will invoke is *documented as inadequate for this exact design class*.

**Gramacy, *Surrogates*** — ⚠️ **NOT VERIFIED** against the text. The stance stands regardless: **we measured a rate and a geometry; we did not discover the phenomenon.**

### A.3 — the search for what is missing

> ❗ **The head-to-head the brief says is "not in the record" EXISTS, and it is the most important citation found.**

**Rummukainen, Hörhammer, Kuusela, Kilpi, Sirviö & Mäkelä (2024), *Heliyon* 10(2):e24484** — *"Traditional or adaptive design of experiments? A pilot-scale comparison on wood delignification."*

| | |
|---|---|
| Design | Box–Behnken **15 experiments** vs BO **5 initial + 10 adaptive = 15**. **Budget matched.** |
| **Scoring** | **Best condition actually MEASURED — i.e. rule A.** |
| Criterion fixed in advance? | **No.** The objective weights appear chosen post-hoc. |
| Result | BO did not reduce experiment count; it gave a more accurate model near the optimum. |

**Three consequences, and the first is the important one.**

1. **Their result agrees with ours under the same rule.** Scored rule A, at a matched budget, on real pilot-scale data, classical DoE was not beaten. Our d=6 σ=0.25 result is **convergent with published experiment**, not a synthetic curiosity. That is a much stronger position than "we found something nobody else did".
2. **Their winner was in the initialization batch** — *"the experimental conditions with the highest cellulose yield of 56.3% had already been found during the first initialization experiment."* **This is exactly our Q37 finding**, arrived at independently on real data: when the target is reachable from the shared opening, no adaptive method can distinguish itself. Q37 measured P(target in the shared opening) = 0.64 for the Hall/Ogle replay.
3. **They did not fix the comparison criterion in advance, and the review of them did not notice.** That is precisely the gap this project's registration discipline fills, now with a named example rather than an abstract worry.

**The contribution is NOT pre-empted, but it must be re-scoped.** The literature split is not purely "which quantity was scored". Rummukainen executed both arms at a matched budget and scored rule A; Narayanan's 3–30× is against **estimated** design sizes (⚠️ unverified) rather than an executed arm. **So the split is at least two things: whether the classical comparator was actually run, and which quantity was scored when it was.** Writing it as scoring alone would overstate a claim that is already strong enough.

**Not found, after searching:** any DoE-versus-BO comparison with a **registered** scoring rule; any treatment of the estimand under another name in this applied literature. ⚠️ Absence of evidence from a handful of searches is weak evidence — a librarian search is still owed before "nobody has made this claim" goes in print.

---

## 🔒 Q41 [A decides] · THE ESTIMAND DECISION — the unconstrained argmax is the primary DoE scoring

*(The close-out brief calls this Q35; that number is occupied here by the constrained-RSM arm. See the concordance above.)*

> **Decision: the unconstrained argmax is the primary DoE scoring. Constrained argmax and best-observed are reported alongside it, in every table, always.**

### What is being decided

Same runs, same data, three numbers. d=6, σ_rel=0.25:

| scoring | regret | what it is |
|---|---|---|
| best observed | 0.060 | the best value the arm measured |
| **unconstrained argmax** | **0.416** | where the fitted surface's optimum lies, unrestricted |
| constrained argmax | 0.117 | that optimum, restricted to the design region |

`unconstrained − constrained = +0.2995 [+0.2790, +0.3228], p<0.0001`, at all four cells (Q35).

**This choice changes the size of the reported effect, not its direction.**

### The reasoning — stated without reference to which arm any choice favours

**1. Fidelity, the primary reason.** The source study's own wording is **"prediction solution"** — JMP's unconstrained Solution report. *Profiler*, *desirability*, *maximize*, *stationary point* and *canonical analysis* appear **zero times** in that paper. They took the unconstrained optimum, built it, and it failed. That failure is the case study. Scoring the arm any other way stops describing the study being replayed.

**2. The constrained number reports a different quantity.** The fitted surface is a **saddle in 200/200 runs**. A saddle has no interior maximum, so the argmax *must* reach a boundary; the closed-form ridge path leaves the design region at radius ≈0.27 against a corner radius of 0.50, every run. Constraining does not correct the model — it **truncates a search whose target was never inside the region**. The constrained value reports *where the search was stopped*, not *where the model pointed*. The estimand is what the fitted model recommends.

**3. Constrained scoring measures a procedure nobody ran** — not the source study (reason 1), and plausibly not the field. ⚠️ **REWRITTEN AFTER TASK A.** The brief cited *"87.61% convexity incompatible with the optimization direction"*; **that figure could not be verified and is not used.** The verified figure from the same 2019 *Int J Adv Manuf Technol* survey is stronger for this purpose anyway: across **123 response surfaces in 49 papers, more than 75.29% presented a SADDLE shape**, and the survey reports that most optimization solutions were found outside the experimental region, describing *"a preponderant neglect"* of the region constraints. **Scope caveat, stated: one journal, 2014–2017, manufacturing — not bioprocess.**

### The counter-argument, and why it does not decide it

Ridge analysis is textbook (Hoerl 1959; Draper 1963; Box & Draper; Myers & Montgomery; SAS `PROC RSREG`; R `rsm`). A reviewer will ask why it was not applied. **Two things weaken it as a primary.**

**It is provably inadequate for this design class** — ✅ verified in Task A: ridge analysis *"does not guarantee the global maximum or minimum point of response in the experimental region for non-spherical designs such as face-centered designs, Box-Behnken designs, and two-level factorial designs."* **The source used a face-centred CCD.** The same source finds the desirability function *more effective* than ridge analysis there. So our constrained-argmax — maximising over the design region directly — is arguably the more correct constrained treatment for this design type, and classical ridge analysis would not have rescued Hall/Ogle even if applied.

**And the objection is answered by reporting, not by re-designating.** The constrained result is measured, reported prominently, and its magnitude stated. Nothing is hidden by making it secondary.

### What this does not change

**The opposite-direction finding survives under either scoring.** Even constrained at 0.117, the DoE arm's recommendation is significantly worse than its own best measurement of 0.060 — **+0.0572, p<0.0001**. The polynomial's model still costs the practitioner something; the GP's model still gains something. Only the magnitude moves.

**This sentence must appear immediately adjacent to the constrained number wherever it is reported.**

### Reporting rules

- **All three scorings in every table, figure and claim.** Quoting one alone is a choice of answer; this project has caught four cases where a registered quantity and a reported quantity came apart (Q16, Q19, Q28, Q29).
- **The constrained result goes in the main text, not supplementary.** It is the largest single sensitivity in the paper — larger than the BO-versus-DoE gap it modifies.
- **Every claim conditioned on a scoring rule names that rule in the same sentence.**
- **The residual above accompanies the constrained number wherever it appears.**

### Process note

Decided by A. **The reasoning above was written before re-examining which arm each scoring favours** and contains no reference to the outcome. Reason 3 was **weakened, not strengthened, by verification** — the headline percentage the brief offered could not be confirmed and was replaced with a smaller, verified one. Reasons 1 and 2 are each independently sufficient and neither depends on the survey.

**Supersedes:** nothing. Q35 measured all three scorings and remains current; this designates which is primary.

---

## ✅ Q42 RESULT [A] · C.1 · Five families, four cells — **the reversal reproduces on three of four usable families**

`python scripts/run_q42_families.py --family <f>` then `--merge` · `results/q42-families.log`. Registered with its prediction and decision rule **before the run**. Supersedes Q36, which asked the same question at one cell on two families and without the noise-model fix.

### Every family-cell

| family | cell | rule A (DoE−BO) | rule C **unconstrained** | rule C **constrained** | reversal |
|---|---|---|---|---|---|
| **levy** | d=6 σ=.25 | **−0.1116** DoE | **+0.4804** BO | −0.0002 **null** | **YES** |
| **levy** | d=6 σ=.10 | −0.0714 DoE | +0.3996 BO | +0.0133 null | **YES** |
| **levy** | d=8 σ=.25 | −0.1251 DoE | +0.4057 BO | +0.0016 null | **YES** |
| **levy** | d=8 σ=.10 | −0.0748 DoE | +0.3487 BO | −0.0058 null | **YES** |
| **rosenbrock** | d=6 σ=.25 | −0.0696 DoE | +0.2638 BO | −0.0019 null | **YES** |
| **rosenbrock** | d=6 σ=.10 | −0.0426 DoE | +0.2288 BO | +0.0097 BO | **YES** |
| **rosenbrock** | d=8 σ=.25 | −0.0818 DoE | +0.2599 BO | −0.0063 null | **YES** |
| **rosenbrock** | d=8 σ=.10 | −0.0575 DoE | +0.2354 BO | +0.0067 null | **YES** |
| hartmann6 | d=6 σ=.25 | +0.2460 **BO** | +0.6313 BO | +0.2753 BO | no |
| hartmann6 | d=6 σ=.10 | +0.3460 **BO** | +0.7245 BO | +0.3483 BO | no |
| ackley ⚠️ | all four | −0.56 to −0.76 DoE | identical to constrained | identical | **VOID** |

**8 of 14 reproduce; 8 of 8 among the families where the question is well posed and the answer is not already known from Hill.**

### 📌 Prediction scored — headline WRONG, and wrong in the favourable direction

I registered: *"it will NOT reproduce on Hartmann6 and will not reproduce cleanly anywhere else either."*

**Half right.** Hartmann6 does not reproduce it — BO wins every rule there, as at Q36. **But Levy and Rosenbrock reproduce it cleanly at every one of their eight cells**, which I explicitly predicted would not happen. The E2 finding is substantially more general than I expected.

**The secondary prediction held exactly:** *"what I expect to survive on all five is the scoring-convention effect."*

### The scoring-convention effect is the universal part

DoE unconstrained − constrained, i.e. how much the classical arm's score moves on the scoring choice alone:

| family | d=6 σ=.25 | d=6 σ=.10 | d=8 σ=.25 | d=8 σ=.10 |
|---|---|---|---|---|
| Hill (Q35) | +0.2995 | +0.3444 | +0.2618 | +0.3227 |
| levy | **+0.4807** | +0.3863 | +0.4041 | +0.3544 |
| rosenbrock | +0.2657 | +0.2190 | +0.2661 | +0.2288 |
| hartmann6 | +0.3560 | +0.3762 | — | — |
| ackley | **+0.0000** | +0.0000 | +0.0000 | +0.0000 |

**Positive on every family and every cell where the surface is a saddle**, and in every case **larger than the rule-C gap it modifies**. Constrained, rule C is **null at 6 of 8** Levy/Rosenbrock cells — the same collapse Q34 found on Hill.

**Ackley's exact 0.0000 is the exception that explains the rule.** Ackley is a broad bowl with fine oscillations, so its fitted quadratic has a genuine interior maximum and the unconstrained argmax is *already inside* the design region — nothing to constrain. Across all 350 runs the stationary point is a **saddle in 247 and a maximum in 103**, and the maxima are concentrated in Ackley. **So "the fitted surface is always a saddle" is false, and the correct statement is conditional: where the Hessian is indefinite the unconstrained argmax must reach a boundary, and the scoring choice then dominates. Where it is negative-definite, the choice is worth nothing.**

### ⚠️ Ackley is VOID under every rule, not just rule A

Q36 voided only Ackley's rule A. **That was insufficient.** Its constrained and unconstrained rule-C figures are *identical to four decimals* because the argmax never leaves the region, so rule C carries no information about the scoring question either. Ackley's optimum is the exact box centre, every screen and CCD includes centre runs, and the DoE design therefore contains the answer. **Report Ackley only as the degenerate case that identifies the mechanism's precondition.**

### What this does to the claim

**The E2 verdict is no longer "one landscape family".** DoE beats BO on best-observed at d=6 σ=0.25 on **Hill, Levy and Rosenbrock**; BO wins on Hartmann6. The determining property is not additivity per se — Levy and Rosenbrock are both non-additive and multimodal — so the earlier "~93% additive, therefore our oracle" objection is answered by data rather than argument.

**And the scoring-convention finding, which is the paper, now rests on four families rather than one.**

---

## ✅ Q45 RESULT [A] · C.2 · The design effect is NOT null once the model is held fixed — and it favours the adaptive design

`python scripts/run_q45_fourfactor_refit.py` · `results/q45-fourfactor-refit.{log,json}` · registered in `3fd2e88` **before the run**, with a prediction that explicitly disagreed with the close-out brief's.

### The confound, and the fix

Q34's polynomial design contrast compared a **four-factor** quadratic on DoE data against a **six-factor** quadratic on BO data — different models, so it confounded design with model dimensionality. Q44 sharpened it: at six factors the CCD is singular in 50/50 runs. Both polynomial cells are now fitted on **the same four factors the DoE arm's own screen kept**, holding the model fixed and varying only the design.

| cell | d=6 σ=.25 | d=6 σ=.10 | d=8 σ=.25 | d=8 σ=.10 |
|---|---|---|---|---|
| 3 · DoE design, 4-factor poly | 0.4163 | 0.4300 | 0.3766 | 0.4104 |
| 6 · BO design, 6-factor poly *(Q34)* | 0.5838 | 0.3956 | 0.6972 | 0.6784 |
| **6 · BO design, 4-factor poly — REFIT** | **0.3035** | **0.1417** | **0.2519** | **0.1435** |
| 4 · BO design, GP | 0.1232 | 0.0703 | 0.1056 | 0.0876 |

| contrast | d=6 σ=.25 | d=6 σ=.10 | d=8 σ=.25 | d=8 σ=.10 |
|---|---|---|---|---|
| refit − sixfactor *(the fix)* | −0.2803 | −0.2539 | −0.4453 | −0.5349 |
| **3 − 6 · DESIGN, model fixed** | **+0.1129** | **+0.2883** | **+0.1247** | **+0.2669** |
| 4 − 6 · SURROGATE, design fixed | −0.1803 | −0.0715 | −0.1462 | −0.0559 |

All p ≤ 0.0008.

### 📌 Predictions scored — mine 2 of 3; **the brief's, refuted**

**Mine, right (1):** *cell 6 improves a lot.* It improves by **0.25 to 0.53**, at every cell. Fitting 15 parameters with 33 residual df instead of 45 with 3 is worth a great deal, and Q34's cell 6 was substantially measuring model misspecification rather than design.

**Mine, right (2):** *it will still be much worse than the GP on the same data.* The 4−6 surrogate contrast is **−0.056 to −0.180**, significant at every cell. **Better conditioning does not repair the geometry.** The falsifier I registered — cell 6 refitted coming close to cell 4 — did not occur, so the saddle argument stands.

**Mine, WRONG (3):** *the design contrast stays subordinate to the surrogate effect.* It holds at the two **σ=0.25** cells (design +0.113 against surrogate 0.180–0.217 at the registered primary) and **fails badly at both σ=0.10 cells**, where the design effect is **four to five times the surrogate effect** (+0.2883 vs −0.0715; +0.2669 vs −0.0559).

**The brief's prediction — that the design null would STRENGTHEN — is refuted.** The design effect is not null once the model is held fixed. It is large, significant at all four cells, and it **has a sign**: `3 − 6` is **positive**, meaning **the DoE design produces a *worse* polynomial recommendation than the adaptive design does, using the identical model.**

### Why that is not a contradiction of Q44, and what it actually means

Q44 measured the CCD as **~4.4× more D-efficient than the adaptive design at the four-factor model in its own region.** Q45 finds the adaptive design gives better recommendations from the same model. Both are true and together they are the point:

> **D-optimality in a small region is not the same property as usefulness for a recommendation made over the whole factor range — and here the two pull in opposite directions.**

The CCD's excellent local geometry is exactly what confines it. Stage 2 explores a narrow sub-box, so its quadratic is well determined *there* and extrapolates badly *outside*, which is where the recommendation is made. The adaptive design's points are worse-conditioned locally and spread across the space, so the same model extrapolates less. **The DoE arm's design is not bad; it is well-built for the wrong question.**

### Consequence for the paper's decomposition

Q34's headline — *"it is the model, not the points"* — **survives at the registered primary cell and must be qualified at low noise.** The honest three-line version:

- The **surrogate** effect is present at every cell and every family, and is the only effect that never reverses.
- The **design** effect is real, was previously hidden behind a model-dimensionality confound, and at σ=0.10 it **exceeds** the surrogate effect.
- The design effect favours **the adaptive design**, which is the opposite of what "structured designs are better conditioned" would predict, and it is explained by region size rather than by design quality.

**Anything in the write-up that says the design does not matter is now wrong and must be changed.**

---

## 📋 PAPER 2 — REGISTERED DERIVATION (Q46). **NOT ACTIVE. No code until Paper 1 is submitted.**

Registered now rather than later purely for provenance: the point of §2 is to record that the method was *derived*, and a registration dated before any implementation is stronger evidence of that than one written afterwards. **This does not start Paper 2.**

### ⚠️ FIVE PREMISES CHECKED AGAINST THIS CLONE — THREE HOLD, TWO DO NOT

| premise | brief | this clone | verdict |
|---|---|---|---|
| noise ceiling | R² 0.106 @ σ=.25, 0.744 @ σ=.10 | 0.106 / 0.744 (`bench-surrogate.log`) | ✅ confirmed |
| additive-kernel null | 0.0015, p=0.71 | −0.0015, p=0.7112 (`q30-additive.log`) | ✅ confirmed |
| coordinate descent ties BO | competitive at d=6 | 0.1420 vs qLogEI 0.1553, contrast null | ✅ confirmed |
| surrogate effect | −0.266, **≈76 SD** | **−0.2171**, **4.6 SD**, 0/10,000, p=1e-4 | ⚠️ real, both figures wrong |
| "LHS beats BO" | a win | Holm: p 0.0147 → **0.2356** | ❌ it is a **TIE** |
| "design effect an order of magnitude smaller" | −0.049 | **refuted by Q45** | ❌ |

### ❌ The load-bearing premise is refuted by a result that postdates the brief

**Q45** refit both polynomial cells on the same four factors, removing the model-dimensionality confound. With the model held fixed the design effect is **+0.1129 / +0.2883 / +0.1247 / +0.2669** (all p ≤ 0.0008) — **at σ=0.10 it is four to five times the surrogate effect.** The brief's phrase *"it holds at both model orders"* names precisely the test that contradicts it.

**And the sign runs against the proposed method.** Every measured design contrast favours the **adaptive** design: Q34's GP contrast (cell 4 − cell 5) is −0.0761 / −0.2025 / −0.0082 / −0.0292 — the adaptive design beats the structured one *with the GP held fixed*. Q45 finds the same with the polynomial fixed. **The evidence says adaptive designs produce better data**, which is the opposite of what "adaptive proposals are not earning their cost" requires.

### ❌ The brief mislabels its own first new arm

> *"Space-filling + GP, no replication — This is Q34's cell 5 as a live arm."*

**Cell 5 is the DoE design (screen → CCD in a sub-box) plus a GP. It is not space-filling.** Nothing in this project measures space-filling + GP, so that arm is genuinely new and **the derivation currently has no premise supporting it** — the nearest evidence is LHS under best-observed scoring, which Holm reduces to a tie.

### ⚠️ §1.3's novelty claim needs rewriting — hetGP already has the combination

`hetGP` (Binois & Gramacy, CRAN) performs *"learning and design that reduce predictive variance by organically determining an input-dependent degree of replication required to efficiently separate signal from noise."* **That is the proposed replication component, in a standard package with a decade of literature.** qHSRI is confirmed as *"A Portfolio Approach to Massively Parallel Bayesian Optimization"* (arXiv 2110.09334), keeping unique designs *"less than 20% of the total number of observations without degrading the sample efficiency"*, on Hartmann6 under heteroskedastic noise.

**So "neither literature has the other half" is not sustainable.** What remains untried is narrower: **a design fixed in advance that proposes no new points at all** — hetGP and qHSRI both keep choosing new locations. That is a real distinction and it is the falsifiable component the brief already identified. **It must be the stated contribution, and hetGP must be an arm, not a citation.**

### The corrected derivation

The noise ceiling, the additive-kernel null and the coordinate-descent tie are intact and support the **replication** half: at σ=0.25 there is little left to learn from more distinct points, so precision should beat exploration. **They do not support the "drop adaptive proposals" half, which the design-effect evidence now actively opposes.**

> **Corrected prediction, registered:** at σ_rel=0.25 and budget 48, adding **adaptive replication** to a GP arm lowers regret at the posterior-mean argmax relative to the same arm without it. The **design** question is left open rather than asserted — the fixed space-filling arm is a *test*, not a component justified in advance. **At σ=0.10 the replication advantage shrinks or reverses.**

**Additional falsifier:** if qLogEI + replication beats the fixed space-filling arm at σ=0.25, the "information not intelligence" framing is wrong even if replication itself wins. **That arm is not in the brief's list and must be.**

### Registered arms (revised from §3.1)

Existing seven, plus: space-filling+GP · space-filling+GP+uniform replication · space-filling+GP+adaptive replication · **qLogEI+adaptive replication** *(separates replication from design)* · **hetGP** *(the actual prior-art baseline)*.

Allocation policy fixed now: **uncertainty-weighted**, with **uniform** as the control. No per-family tuning.

**Status: registered, inactive.**
