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

**Blocked on:** the version-2 pre-registration — Q12, Q14, Q15 and Q16 together, as one bump. Ordering and owners are in `docs/archive/build-phase/TASKS.md`; two of the four (T1, T2) are waiting specifically on B.

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


---

## 📋 Q47 — THE MULTI-FIDELITY THRESHOLD. Registered before the experiment exists.

**This is a threshold calculation, not a method arm, and that distinction must survive
into the write-up.** A multi-fidelity *arm* would measure the correlation it assumed
between the cheap and expensive readouts. No such correlation is published for
endothelial differentiation, so any single value would be invented and the result would
be whatever was plugged in. This sweeps the correlation and the cost ratio instead and
reports where a cheap tier stops paying.

> **Deliverable.** A threshold surface over (ρ, cost ratio) marking where a two-tier
> design achieves lower simple regret than a single-tier design **at equal total cost**.
> **This is not a claim that multi-fidelity helps.** It is a statement of the conditions
> under which it would.

### ⚠️ PREMISE CHECK — the brief's §8 is stale on three of four items

| the brief says "still unwritten" | this clone |
|---|---|
| `RESULTS.md` | ❌ **written** — `docs/RESULTS.md`, 641 lines, commit `1dc09d3` |
| the citation check | ❌ **done** — Task A, commit `a36581a` (one characterisation refuted, one "missing" citation found) |
| the engineering fixes | ❌ **done** — Task B, commits `7bfe0e3` / `8ed2516` |
| the noise threshold curve | ✅ **correct, still unwritten** — see the next block |

### ⚠️ The "noise ceiling" this is supposed to rhyme with is two points, not a curve

The brief's §6 pairs this with a noise ceiling stated as *"above CV ≈ X, no method finds
anything within budget."* **No such curve exists.** What exists is held-out surrogate R²
at exactly two noise levels — **0.106 at σ_rel=0.25 and 0.744 at σ_rel=0.10**
(`results/bench-surrogate.log`) — which is a statement about how well a model can be
*fitted*, not about whether any method *finds* anything. The two results compose as §6
claims only once the σ sweep is actually run. Recorded so the write-up does not assert a
curve the project does not have.

### ⚠️ The baseline arm named in the brief does not exist

> *"Single-tier baseline — the existing spread+GP arm at full expensive budget."*

E2's arms are `coord`, `doe`, `lhs`, `qlogei`, `qlognei`, `random`, `sobol`
(`results/e2-grid.json`). **None of them fits a GP to a space-filling design** — the
space-filling arms are scored from their observations and never build a surrogate. So
the baseline has to be constructed here: **LHS(48) expensive + the project's own
`build_gp`**, scored under both rules. It is ~15 lines and it reuses `build_gp`
unchanged, so it is not a new model — but it is a new arm and it is *this* registration
that creates it, not a prior result. (It is also Q46's first Paper-2 arm. Noted so the
overlap is on the record; it is a control here, not a method.)

### 🔬 MEASURED FIRST, AND IT REFRAMES THE SWEEP

The expensive readout is not a gold standard. Under this project's own observation model
`y = f(x)(1+ε) + η`, its correlation with the truth, over 4096 Sobol points on all 25
instances:

| | σ_rel = 0.25 | σ_rel = 0.10 |
|---|---|---|
| d=6 | **0.583** [0.546, 0.613] | **0.872** [0.850, 0.887] |
| d=8 | **0.557** [0.506, 0.593] | **0.863** [0.830, 0.881] |

Closed form check: `ρ_e = σ_f / sqrt(σ_f² + σ_rel²·E[f²])` with σ_f = 0.1228 and
E[f²] = 0.478 gives 0.579 against the measured 0.583. The model is right.

**Consequence for the brief's ρ range of 0.3–0.95.** Above ρ_e the "cheap" readout is
*more accurate than the expensive one and also cheaper*. That is not a fidelity
trade-off; it is a better assay, and the correct recommendation there is to stop running
the expensive one. At σ_rel=0.25 that covers **everything above 0.583 — half the swept
range.** The threshold question is only meaningful below ρ_e, and **ρ = ρ_e is drawn on
every reported surface as the line above which the trade-off is not a trade-off.**

Grid points are therefore re-spaced to straddle both anchors rather than sit uniformly:
**ρ ∈ {0.30, 0.45, 0.55, 0.65, 0.80, 0.95}** brackets 0.583 (between 0.55 and 0.65) and
0.872 (between 0.80 and 0.95). Six levels and the brief's stated range, both kept.

### 📌 REGISTERED PREDICTION — computed, not asserted

`scripts/q47_predict_threshold.py`, run and committed **before** the experiment script
exists; output at `results/q47-prediction.log`. A Gaussian order-statistic proxy: no
landscape, no GP, no design — only the selection and the reported-best scoring rule.
Predicted gain over the single-tier baseline, in units of the response SD:

| σ_rel | cost | ρ=0.30 | 0.45 | 0.55 | 0.65 | 0.80 | 0.95 |
|---|---|---|---|---|---|---|---|
| 0.25 | 3× | +0.019 | +0.054 | +0.059 | +0.061 | +0.054 | +0.046 |
| 0.25 | 20× | +0.355 | +0.523 | +0.615 | +0.691 | +0.757 | +0.785 |
| 0.10 | 3× | **−0.026** | **−0.003** | +0.006 | +0.012 | +0.006 | −0.001 |
| 0.10 | 20× | +0.307 | +0.452 | +0.538 | +0.590 | +0.629 | +0.605 |

**P1 — there is essentially no correlation threshold, and the finding is about the cost
ratio.** For every cost ratio ≥ 5 the two-tier design pays at ρ = 0.30, the bottom of
the swept range. The only crossing inside the grid is **cost ratio 3 at σ_rel=0.10,
between ρ=0.45 and ρ=0.55**, and the effect there is ~0.01 — too small to matter. This
is the brief's own "the threshold is very low" outcome, and the recommendation it implies
is *build a cheap tier*.

**P2 — the benefit is NON-MONOTONE in ρ at σ_rel=0.10, peaking near ρ≈0.65–0.80 and
declining at 0.95.** Mechanism: near-perfect screening confirms 32 points that are nearly
tied in truth, and a noisy confirmation cannot rank a tied set, so the reported point is
close to a random draw from the top of the distribution. Imperfect screening leaves the
confirmation step something to discriminate on. Registered at **low confidence** — the
effect is 0.02 against a scale of 0.6, and the iid proxy has no spatial structure.

**P3 — rule A and rule C should disagree, and the proxy cannot see why.** The
screen-then-confirm arm fits its GP to 32 points *all clustered in the high-response
region*. That is a good set to report from and a bad set to fit a surface to. So:
two-tier should win under rule A roughly as tabled, and **lose, or win by much less,
under rule C** — with the joint-model arm recovering the difference because its pseudo-
observations span the whole space. If rule A and rule C give the same threshold, P3 is
wrong and the clustering cost is smaller than argued.

**What would falsify the design of the study itself:** any two-tier arm *losing* at
ρ > ρ_e. Above ρ_e the cheap readout dominates the expensive one on accuracy and on
cost simultaneously, so a loss there is a harness bug, not a finding.

### The arms, and the one the brief does not have

Equal **total cost**, never equal evaluation count. Budget 48 expensive-equivalents; a
cheap assay costs 1/c of an expensive one; the cheap tier is allocated a fixed fraction
**φ = 1/3** of the budget, so **k = 32 confirmations and n_cheap = 16c ∈ {48, 80, 160,
320}**. Every term is an integer and the identity `k + n_cheap/c == 48` is asserted per
arm per run, not assumed — a cost bug here would invalidate the whole surface.

| id | expensive pts | how they are chosen | model | depends on ρ |
|---|---|---|---|---|
| `single` | 48 | LHS | GP on the 48 | no |
| `budget_only` | 32 | LHS | GP on the 32 | **no** — the pure cost of the downgrade, using no cheap information at all |
| `screen` | 32 | top-k by cheap value | GP on the 32 expensive | yes |
| `joint` | 32 | 16 top + 16 random | recalibrated GP on 32 expensive **+ n_cheap pseudo-observations** | yes |

**`budget_only` is not in the brief and is the arm that makes the surface readable.**
Without it, a two-tier win confounds "the cheap tier helped" with "32 well-spread
expensive points were enough anyway", and a two-tier loss confounds "the cheap tier was
useless" with "losing 16 expensive points was expensive". It costs almost nothing: it
depends on neither ρ nor the cheap draw, so it is computed once per (d, σ, φ).

**Why `joint` confirms 16 top + 16 random.** Estimating the cheap→expensive relation
needs spread in the cheap value. Confirming only the top-k gives a truncated range, which
attenuates the slope and would handicap the joint model for a reason that has nothing to
do with the model. The split keeps calibration spread and keeps something worth reporting.

### The joint model, and the one place this deviates from the brief

The brief says *"standard multi-fidelity co-kriging."* Implemented instead as
**regression-adjusted co-kriging** (Le Gratiet & Garnier's recursive formulation, with
the discrepancy absorbed into the noise): OLS-regress the expensive observation on the
cheap observation at the points measured on both tiers, map every cheap point onto the
expensive scale, and fit **the project's own `build_gp`** to the pooled data with the
pseudo-observations carrying variance `max(σ̂_resid² − mean(Yvar_expensive), σ_add²)`.

**Reason for the deviation, stated as required.** BoTorch's `MultiTaskGP` / ICM brings
its own kernel, priors and transforms, so `joint` vs `screen` would differ in the
fidelity structure *and* in the surrogate — the exact model-versus-design confound Q34
and Q45 spent this project's budget untangling. The recalibration route holds kernel,
priors, `Normalize`, `Standardize` and the fitting code identical and changes exactly one
thing: whether the recalibrated cheap points are in the training set.

**And it hands the joint model the correct functional form.** The generative cheap
readout is affine plus Gaussian noise, which is precisely what the OLS adjustment
assumes. So this arm is an **upper bound** on what a joint model achieves here. If even a
correctly-specified joint model does not beat screen-then-confirm, that is a stronger
result than the reverse — and it is the brief's own stated preference: *"If the naive
version captures most of the benefit, that is the more useful finding."*

### The cheap-readout model, and the invariance that doubles as a test

`y_cheap = a·y_true + b + ε_cheap`, with **a and b sampled per instance** — a cheap
readout with a stable known calibration is an unrealistically favourable case.
Parameterised by ρ, not by σ_cheap: σ_cheap is derived as `a·σ_f·sqrt(1/ρ² − 1)`, where
σ_f is the instance's own signal SD over the box, estimated once from a fixed 4096-point
Sobol sample. **The achieved correlation is asserted against the target before anything
is scored.**

That derivation makes `y_cheap` an *exact* affine function of a calibration-free
quantity, so **`screen` is mathematically invariant to (a, b)** — an affine map with
a > 0 preserves the ranking it selects on. That is not a guess; it is provable from the
construction, and it is written as a test. **If the sampled-vs-fixed sensitivity moves
`screen` at all, the harness is broken.** Only `joint` can be hurt by unknown calibration,
which is the whole point of sampling (a, b).

### Two correlations, and only one of them is measurable in a morning

ρ as swept is `corr(y_cheap, y_true)`. **A lab cannot measure that** — it has no access
to the truth. What a lab measures in a morning is `corr(y_cheap, y_expensive)`, which is
strictly lower, because the expensive readout is itself only 0.583/0.872 correlated with
the truth. **The threshold is therefore reported on both axes**, with the empirical
mapping between them tabulated per cell. Reporting only the ρ-to-truth axis would make
the deliverable's central actionability claim false.

### Limits — written before the numbers exist

- **The correlation is assumed, not measured.** No published value exists for endothelial
  differentiation. **That is why this is a threshold rather than a result.**
- **The linear-plus-noise cheap-readout model is a choice.** A real cheap readout might
  saturate, or track well at high response and poorly at low. The functional form is an
  assumption, and it is the *same* assumption the `joint` arm's adjustment makes — so
  `joint` is being graded on a model it is guaranteed to have right.
- **Cost ratios are illustrative** and depend on a lab's actual assays.
- **The allocation φ = 1/3 is a registered choice, not an optimum.** A threshold read off
  a badly-split budget is a threshold for that split. Sensitivity at φ ∈ {1/4, 1/2} is
  run at the primary cell only, and the surface is labelled with its φ.
- **This says nothing about whether a suitable cheap readout exists for CD31.** It says
  what one would have to be worth building.
- **The proxy prediction above is rule A only.** It has no landscape and no surrogate.

### Scope

**Not a method arm in Paper 1.** Reported alongside the noise ceiling, in the same
section, framed the same way. Gets a `docs/RESULTS.md` entry on completion, with the
assumed-correlation limitation in its Limits field.

**Status: registered. Prediction committed. Experiment not yet written.**


---

## 🔴 Q48 — E2's STATIC ARMS SHARE ONE DESIGN ACROSS ALL 25 INSTANCES, AND `lhs` DREW A GOOD ONE

**Found by accident.** Q47 needed a single-tier LHS+GP baseline. Built with a
per-instance design seed it scored **0.1778** at d=6 σ=0.25; `results/e2-grid.json`
reports **0.1270** for the `lhs` arm at the same cell. Same code path, same instances,
same noise draws, same scoring rule. **Only the design seed differed.**

### The mechanism

`runner.static_design(bounds, method, budget, seed)` **takes no instance argument.** At a
given seed every instance in the cell is scored on the identical 48 points, so a cell
with 2 seeds contains **2 distinct designs across all 50 runs**, not 50.

The second consequence is the serious one:

1. The reported mean is conditioned on those two draws rather than averaged over designs.
2. **`instance_bootstrap` resamples the 25 instances as if independent. They are not** —
   they share a design. So the design component of variance is **absent from every
   confidence interval this project reports for a static arm.**

### Result — `results/q48-design-variance.log`, 60 designs per arm per cell

| d=6 σ=0.25 | E2 reports | design-averaged | sd | percentile of E2's draw |
|---|---|---|---|---|
| `lhs` | 0.1270 | **0.1752** | 0.0251 | **0th of 60** |
| `sobol` | 0.1724 | 0.1777 | 0.0265 | 40th |
| `random` | 0.2216 | 0.1778 | 0.0237 | 98th |

**Two findings, and the first was invisible before.**

**(a) At 48 points in 6 dimensions, LHS, Sobol and uniform random are indistinguishable.**
Design-averaged they are 0.1752 / 0.1777 / 0.1778 — a spread of 0.003 against a
design SD of 0.025. E2's reported spread of 0.095 between the best and worst of them is
**almost entirely which design each happened to draw**, not a property of the design
method. The same holds at d=6 σ=0.10 (0.1278 / 0.1281 / 0.1292) and at both d=8 cells.

**(b) The comparison the paper leans on reverses at the registered primary cell.**

| d=6 σ=0.25 | verdict |
|---|---|
| qLogEI 0.1553 vs `lhs` **as reported** 0.1270 | LHS ahead by 0.0282 |
| qLogEI 0.1553 vs `lhs` **design-averaged** 0.1752 | **BO ahead by 0.0199** |

At the other three cells BO was already ahead and design-averaging widens its margin
(σ=0.10: 0.0153 → 0.0404; d=8 σ=0.25: 0.0380 → 0.0522; d=8 σ=0.10: 0.0288 → 0.0370).

### ⚠️ WHAT THIS DOES **NOT** ESTABLISH — read before quoting (b)

**Only the LHS side has been design-averaged.** qLogEI carries the same conditioning:
`initial_design` is `sobol_design(bounds, 2d+2, seed)`, which also takes no instance
argument, so its **14-point opening batch is shared across all 25 instances too**. Its
0.1553 is therefore also a two-draw number.

The shared component should be smaller — 14 points instead of 48, and the remaining 34
are chosen from each instance's own data — but *should be smaller* is an argument, not a
measurement. **The reversal in (b) is indicated, not established.** Settling it needs
qLogEI re-run across ~30 opening seeds, which is ~30× the primary cell's BO compute and
has not been run. Registered here as the outstanding test.

Finding (a) does not depend on that caveat: it is a comparison among static arms, all
three measured the same way.

### Why this is not the same as Q39 or Q46

Three now bear on "LHS beats BO", and they are independent:

| | what it says |
|---|---|
| **Q39** | Holm over the 39 non-primary contrasts takes p 0.0147 → 0.2356. **A tie.** |
| **Q46** | the Paper-2 brief's premise that this is "a win" is not supported. |
| **Q48** | the point estimate itself is the **best of 60 design draws**, and averaging it **reverses the sign**. |

Q39 widens the interval. **Q48 moves the estimate.** Anything in the write-up that
reports the static arms' *relative ordering* as a finding is affected.

### Cost of having not known

`results/q48-design-variance.log` is **seconds of numpy** — static arms are design,
evaluate, reported-best, with no GP anywhere. It was never run because nobody asked
whether the design was a random variable.

### Actions

- **Any claim about the relative ordering of `lhs` / `sobol` / `random` must be struck**
  or restated as design-averaged. `docs/CLAIMS.md` and `docs/RESULTS.md` both carry
  E2 static-arm numbers.
- **`instance_bootstrap` intervals for static arms are within-design intervals** and must
  be labelled as such wherever they appear.
- The fix for a future run is one argument: seed the static design on
  `(instance, seed)`, as `run_q47_multifidelity.py` already does.
- **Do not restate (b) as established** until the qLogEI opening-seed sweep is run.


---

## ✅ Q49 — THE NOISE THRESHOLD CURVE. The outstanding item, and it is not the curve anyone described.

Every close-out list has carried *"the noise threshold curve"* as unwritten, and Q47's §6
pairs its correlation floor with a noise ceiling stated as **"above CV ≈ X, no method
finds anything within budget."** That sentence is now measurable, and **it is false.**

What existed before was held-out surrogate R² at two noise levels — 0.106 at σ_rel=0.25,
0.744 at 0.10 (`results/bench-surrogate.log`). That is a statement about how well a model
can be **fitted**, not about what an experimenter walks away with.

**Found while validating a control arm.** Q47's under-budget arm spends 32 expensive
assays instead of 48 and scored *better* at d=6 σ=0.10 under rule A. Chasing that
produced this. `results/q49-noise-threshold.log`, no GP anywhere, seconds of numpy.

### The measurement splits the regret in two

| | what it is |
|---|---|
| **oracle-best** | the best TRUE value among the points visited — what the design **found** |
| **reported** | the true value of the point chosen by the best *observation* — what you **walk away with** (rule A, `reported_best_curve`) |

**The gap between them is the noise ceiling in units anyone can act on.**

### ❌ FIRST, THE CORRECTION: more assays keep helping at every CV

| d=6, rule A, paired at instance level | 48 → 96 | 48 → 192 |
|---|---|---|
| σ_rel = 0.10 | +0.0320 [+0.0159, +0.0492] | +0.0409 [+0.0272, +0.0547] |
| σ_rel = 0.25 | +0.0351 [+0.0086, +0.0629] | +0.0384 [+0.0078, +0.0672] |
| σ_rel = 0.50 | +0.0211 [−0.0061, +0.0494] **null** | +0.0362 [+0.0055, +0.0699] |

**Doubling and quadrupling the budget both help, significantly, at every noise level
tested including σ_rel=0.50.** Only one contrast in the whole sweep is null
(48→96 at σ=0.50, and 48→96 at d=8 σ=0.20). So "above CV ≈ X, no method finds anything
within budget" must not be written. **Nothing in this project supports it.**

⚠️ **A correction to a reading I made from this same table.** Looking at the unpaired
means — d=6 σ=0.25 reported-best of 0.1699 / 0.1746 / 0.1763 / 0.1640 / 0.1778 at
n = 16 / 24 / 32 / 40 / 48 — I said quadrupling the budget buys nothing. The paired
contrast says otherwise, and the paired contrast is the correct instrument: the marginal
SE at n=25 instances is ~0.03, which swamps the effect, while the instance-paired
difference has a CI of ±0.03 around +0.038. **An unpaired comparison of two means from
the same 25 instances throws away the pairing that makes the effect visible.**

### ✅ WHAT THE CURVE ACTUALLY SHOWS — the identification gap

Oracle-best does not depend on σ at all: the design finds what it finds. So the entire
noise effect is the gap between finding and identifying, and **that gap is where the
threshold lives.** At n=192:

| σ_rel | d=6 gap | share of remaining regret | d=8 gap | share |
|---|---|---|---|---|
| 0.05 | +0.0232 | **30%** | +0.0273 | 32% |
| 0.10 | +0.0431 | **44%** | +0.0514 | 47% |
| 0.15 | +0.0671 | **55%** | +0.0544 | 49% |
| 0.20 | +0.0796 | **60%** | +0.0667 | 54% |
| 0.25 | +0.0855 | **61%** | — | — |
| 0.35 | +0.0936 | 63% | — | — |
| 0.50 | +0.1148 | 68% | — | — |

**The threshold is CV ≈ 0.15.** Below it, most of what you are still missing is a recipe
you never tried. Above it, **most of what you are missing is a recipe you already ran and
could not tell was the best one.**

That is the actionable statement, and it is a different instruction from the one the
brief expected:

> Below CV ≈ 0.15, spend on **more conditions**. Above it, spend on **identifying the
> conditions you already ran** — replication, or a better readout. More distinct
> conditions still help, but they are no longer where most of the loss is.

### 🔗 How it composes with Q47, which is the pairing §6 wanted

At d=6 σ_rel=0.25, at **equal total cost of 48 expensive-equivalents**, Q47's two-tier
design with a cost ratio of 20× and ρ=0.80 gains **+0.0638** [+0.0360, +0.0908].
Quadrupling the expensive budget to 192 — **four times the money** — gains **+0.0384**.

> **A cheap screening tier at a 20:1 cost ratio is worth more than quadrupling the
> expensive budget, and costs nothing extra.**

Both results say the same thing from opposite directions: at this noise level the
expensive assay's *identification* is the binding constraint, so buying more of it is the
weaker move. It also independently supports the **replication** half of Q46's Paper-2
derivation, which was derived from the surrogate-fit ceiling rather than from regret.

### Limits

- **σ_rel above 0.25 is outside the ensemble's design range.** The acceptance floor was
  calibrated so a true depth of ~0.11 clears 3σ/√48 at σ_rel=0.25 (Phase A2). The 0.35
  and 0.50 rows describe instances built for a quieter assay. They are reported because
  the trend is the answer, not because those instances are calibrated for it.
- **One design family.** LHS only, seeded per instance (Q48). An adaptive arm would place
  points differently and its oracle-best curve would differ; the identification gap is a
  property of the readout, not of the design, so it should carry over, but that is an
  argument and not a measurement.
- **No replication arm.** The recommendation "spend on identification above CV 0.15"
  follows from the size of the gap, not from a measured replication arm beating a
  non-replicated one. **That arm is Q46's, and it has not been run.**


---

## ✅ Q47 RESULT — THE MULTI-FIDELITY THRESHOLD. All three registered predictions wrong.

6,600 runs, 22 shards, **zero rule-C fit failures in 4,800 fits**.
`results/q47-multifidelity.log` · `results/q47-analysis.log` · `results/q47-multifidelity.json`

### The threshold surface — lowest ρ at which the two-tier advantage clears zero

`*` marks a crossing **above** the expensive readout's own correlation with the truth,
where the "cheap" assay is simply the better assay and the trade-off is not a trade-off.

| cell | arm | rule | 3× | 5× | 10× | 20× |
|---|---|---|---|---|---|---|
| d=6 σ=0.25 | screen | A | never | never | 0.45–0.55 | **≤0.30** |
| d=6 σ=0.25 | joint | A | never | 0.65–0.80\* | 0.65–0.80\* | 0.30–0.45 |
| d=6 σ=0.10 | screen | A | 0.45–0.55 | **≤0.30** | 0.30–0.45 | **≤0.30** |
| d=6 σ=0.10 | joint | A | 0.45–0.55 | **≤0.30** | 0.30–0.45 | **≤0.30** |
| d=8 σ=0.25 | screen | A | never | 0.45–0.55 | 0.30–0.45 | 0.30–0.45 |
| d=8 σ=0.25 | joint | A | 0.80–0.95\* | 0.55–0.65\* | 0.45–0.55 | 0.30–0.45 |
| d=8 σ=0.10 | screen | A | 0.45–0.55 | **≤0.30** | 0.30–0.45 | **≤0.30** |
| d=8 σ=0.10 | joint | A | **≤0.30** | 0.30–0.45 | 0.30–0.45 | **≤0.30** |

Rule C is in `results/q47-analysis.log`; it does not tell a different story (see P3).

### 📌 THE THREE REGISTERED PREDICTIONS — ALL THREE WRONG

**P1 REFUTED.** *"No correlation threshold: the two-tier design pays at ρ=0.30 for every
cost ratio ≥ 5."* It pays at ρ=0.30 in **5 of 12** such cells. There **is** a threshold,
it moves with the cost ratio, and at 3× and 5× in the noisy d=6 cell there is no crossing
in range at all. The Gaussian order-statistic proxy got the *effect sizes* roughly right
and the *detectability* wrong: it has no instance-to-instance variance, so it could not
predict which effects would clear an n=25 interval.

**P2 REFUTED.** *"The benefit is non-monotone in ρ at σ=0.10, peaking near 0.65–0.80 and
declining at 0.95."* It **rises** from ρ=0.80 to 0.95 in **6 of 8** cost-ratio × dimension
combinations. The proposed mechanism — near-perfect screening confirming a set too tied
for a noisy confirmation to rank — is not visible at this budget. Registered at low
confidence, and the low confidence was warranted.

**P3 REFUTED as a directional claim.** *"Two-tier should do worse under rule C, because
the top-k design is clustered where a surrogate needs spread."* Across 16 cells the rule-C
threshold is lower in 4, higher in 4, and equal in 8. **No systematic difference either
way.** ⚠️ At d=6 alone rule C *is* systematically lower, and that is how it looked before
the d=8 shards finished — an interim reading that the completed grid does not support.

### 🔴 THE ALLOCATION IS A BIGGER LEVER THAN THE CORRELATION

The registration fixed φ = 1/3 as "a registered choice, not an optimum" and promised a
sensitivity check. That check is the most consequential number in the experiment.

**d=6 σ=0.25, cost ratio 5×, rule A advantage over the single-tier arm:**

| φ | k | n_cheap | ρ=0.30 | 0.45 | 0.55 | 0.65 | 0.80 | 0.95 |
|---|---|---|---|---|---|---|---|---|
| 0.25 | 36 | 60 | −0.0160 | +0.0110 | −0.0056 | −0.0104 | −0.0017 | +0.0061 |
| **0.333** | 32 | 80 | +0.0232 | +0.0090 | +0.0223 | +0.0255 | +0.0200 | +0.0240 |
| 0.50 | 24 | 120 | **+0.0388** | **+0.0469** | **+0.0521** | **+0.0555** | **+0.0543** | **+0.0529** |

(bold = clears zero)

**At φ=0.25 there is no advantage at any correlation. At φ=0.5 there is one at every
correlation, including ρ=0.30.** Same cost ratio, same cell, same budget. The same
pattern holds at 20×.

> **The deliverable as specified — a threshold surface over (ρ, cost ratio) — is
> under-specified. The surface is over (ρ, cost ratio, φ), and φ is the leading term.**
> A threshold read off a fixed split is a threshold for that split. Every number in the
> table above is labelled φ=1/3 for that reason, and **none of them should be quoted
> without it.**

This is not a small caveat bolted on. It says the practical question is not *"is my cheap
assay correlated enough?"* but *"how much of the budget should go to screening?"* — and
this experiment did not sweep that axis properly, because the registration treated it as
a nuisance parameter.

### The under-budget control earns its place

Cutting the expensive budget from 48 to 32 and buying **nothing** with the savings:

| | rule A | rule C |
|---|---|---|
| d=6 σ=0.25 | +0.0016 [−0.0284, +0.0308] | +0.0044 [−0.0191, +0.0267] |
| d=6 σ=0.10 | **+0.0234 [+0.0057, +0.0411] — 32 is BETTER** | −0.0104 [−0.0286, +0.0074] |
| d=8 σ=0.25 | +0.0019 [−0.0225, +0.0268] | −0.0152 [−0.0342, +0.0035] |
| d=8 σ=0.10 | +0.0091 [−0.0124, +0.0309] | −0.0107 [−0.0251, +0.0032] |

**No measurable difference in 7 of 8 comparisons**, and in the eighth the *smaller* budget
wins. So a two-tier win is not "the cheap tier bought more than the expensive points it
displaced" — **the displaced expensive points were worth nothing measurable to begin
with**, and the whole of the two-tier gain comes from screening a larger candidate pool.
Without this arm that decomposition is invisible and the result reads as a much stronger
endorsement of multi-fidelity than it is. It is not in the brief.

### Fixed versus sampled calibration — using a proven invariant as the noise floor

⚠️ **The arm does not isolate `(a, b)`, and that is a flaw in how it was built.**
`run_shard` draws `a` and `b` from the generator that then draws the cheap readout's
noise, so skipping those two draws leaves the generator in a different state and every
later draw differs. The arm varies the calibration **and** re-draws the noise.

It is still interpretable, because `screen` is *provably* invariant to `(a, b)`: every
difference it shows is pure Monte Carlo re-draw, with a known true value of zero.

| | `screen` (true value 0) | `joint` |
|---|---|---|
| 5×, ρ=0.30 | −0.0104 | −0.0054 |
| 5×, ρ=0.65 | +0.0015 | −0.0110 |
| 5×, ρ=0.95 | −0.0037 | +0.0025 |
| 20×, ρ=0.30 | +0.0022 | +0.0130 |
| 20×, ρ=0.65 | +0.0024 | +0.0110 |
| 20×, ρ=0.95 | −0.0102 | +0.0094 |

`screen`'s known-zero spread is ±0.010 and `joint`'s is ±0.013. **No detectable
calibration effect on the joint model, at a noise floor of ±0.01.** The threshold is not
soft with respect to the calibration assumption — which is the one thing in §4 of the
brief that came out where it was expected.

### The two correlations, and the one a lab can measure

ρ as swept is against the *truth*, which no lab can observe. Against the expensive
readout — what a morning's work actually measures:

| ρ to truth | 0.30 | 0.45 | 0.55 | 0.65 | 0.80 | 0.95 |
|---|---|---|---|---|---|---|
| d=6 σ=0.25 → measurable ρ | 0.18 | 0.26 | 0.32 | 0.38 | 0.47 | **0.56** |
| d=6 σ=0.10 → measurable ρ | 0.26 | 0.39 | 0.48 | 0.57 | 0.70 | **0.83** |

**A perfect-looking cheap assay reads 0.56 against the expensive one at σ_rel=0.25.**
Any threshold quoted on the ρ-to-truth axis will be read by a lab as the number it
measured, and it is not. **Both axes, always.**

### What the result actually supports

At the primary cell and φ=1/3, a cheap tier at a **10:1 cost ratio or better** pays from
a measurable correlation of roughly **0.26–0.32**. Below 5:1 it does not pay at any
correlation. But see the φ finding: at φ=0.5 even 5:1 pays everywhere, so **the honest
one-line recommendation is about the split, not the correlation.**

And composed with **Q49**: at equal total cost a 20:1 cheap tier gains +0.0638 where
quadrupling the expensive budget gains +0.0384. **The cheap tier is worth more than four
times the money.**

### Limits

- Everything above is at **φ=1/3** except the sensitivity table. See the φ finding.
- The correlation is **assumed, not measured** — no published value exists for endothelial
  differentiation. That is why this is a threshold and not a result.
- The **linear-plus-noise cheap readout is a choice**, and it is the same form the joint
  arm's adjustment assumes, so `joint` is graded on a model it is guaranteed to have right.
- `joint`'s pseudo-observation variance is **deliberately conservative** — measured 2× to
  20× the oracle-true value, worst at high ρ. This biases against `joint`, so the
  registration's claim that `joint` is a clean upper bound is **withdrawn**.
- **Cost ratios are illustrative.** They depend on a lab's actual assays.
- Nothing here says a suitable cheap readout for CD31 exists. It says what one would have
  to be to be worth building.


---

## 📋 Q51 — HARTMANN6 AT d=8. Registered before the run. Closing a gap in Task C.1.

### The gap, and it was nobody's decision

Q42 answers *"you built the landscape that gave you your answer"* with Hartmann6:
non-additive, deceptive, six local optima, fifty years old, not ours. **It ran at two of
the four cells every other family ran at** — d=6 at both noise levels, and no d=8 at
either. `Hartmann6` is defined at six dimensions, and `run_q42_families.py` returned
`None` for anything else.

So the one family carrying the generality argument is the one with half the coverage, and
**that is exactly the reduction that should never be made**: reduce families if compute
forces it, never cells, because d=6/σ=0.25 is the cell where BO lost and dropping the
others would be selection on the outcome.

### The fix uses the structure this project already built

`oracles.Embedded` places Hartmann6's six coordinates in a larger cube with the rest
inert. That is the Hill oracle's own convention: it holds `n_active=4` at **both**
dimensions and draws the active subset at random (`rng.choice(dim, n_act, replace=False)`)
precisely so d=6 against d=8 isolates **the cost of nuisance dimensions** rather than
confounding dimension with active-count. Hartmann6-in-8D gets six active axes, two inert,
active subset from a recorded seed.

The inert axes are **exactly** inert — asserted as an equality over random draws, not a
tolerance (`tests/test_embedded_oracle.py`, 8 tests). An approximately-inert axis would
mean the arm measures a different function rather than a nuisance dimension.

### The structural fact that makes this sharp

**The DoE arm's screen keeps a fixed `n_keep = 4` factors** (`doe.py:196`, matching the
published 6→4). Hartmann6 has **six** active coordinates. So the classical pipeline must
discard genuinely active factors *at both dimensions* — this is not new at d=8. What **is**
new at d=8 is that the screen can also **waste slots on the two inert axes**.

Every row now records `n_kept_active`: how many of the screen's four slots landed on a
genuinely active factor. That is the diagnostic that separates the two failure modes, and
it is reported whether or not it flatters the DoE arm.

### 📌 REGISTERED PREDICTION

**1. The reversal will still NOT reproduce at d=8.** At d=6 BO wins every rule by wide
margins — rule A +0.2460 [+0.1827, +0.3068], rule C constrained +0.2753, all p<0.0001,
and the fitted surface is a **saddle in 25/25 runs**. Two inert dimensions will not
rescue a quadratic that has no interior maximum.

**2. BO's margin will WIDEN at d=8, not narrow.** The DoE arm has four slots and six real
factors at both dimensions, but at d=8 it must first *find* which six of eight matter. Any
slot spent on an inert axis is a slot not spent on real signal.

**3. The screen will spend most of its slots correctly — `n_kept_active` ≥ 3.5 of 4.**
Inert axes have exactly zero main effect, so a resolution-IV screen should reject them
reliably even under σ_rel=0.25. **If it does not, that is the more interesting result**,
and it would say the screening stage is noise-limited rather than design-limited.

**What would falsify the generality argument:** the DoE arm winning rule A at d=8. That
would mean the reversal reproduces on Hartmann6 after all and the non-additive defence is
weaker than Q42 claims.

### The d=6 cells are re-run too, deliberately

The d=6 path is unchanged (`Hartmann6()`, not `Embedded(..., dim=6)`), so re-running it
must regenerate the committed shard **bit-exactly**. That is checked against a copy of the
committed file rather than assumed — the same discipline as `probe_e2_determinism.py`, and
this project has already shipped one fidelity gate that compared a regeneration against an
untracked file and so proved only that a clone agreed with itself (D12).

**Status: registered. Experiment launched immediately after this commit.**


---

## ✅ Q50 RESULT — qLogEI DESIGN-AVERAGED. Q48's REVERSAL IS **ESTABLISHED**.

**Files:** `results/q50-qlogei-seedsweep.log` · `results/q50-qlogei-seedsweep.json` ·
`results/q50-shards-run2.log` · **20 shards registered, 20 run.** The scope reduction
below was closed on 2026-08-13; the entry keeps it as the record of what was cancelled
and what the completed run did to it.

### The fidelity check passed exactly

E2 ties the campaign seed to the noise seed, so its number is the **diagonal** of this
grid. If the diagonal does not reproduce E2, nothing else in the file counts.

| | |
|---|---|
| `e2-grid.json` qlogei, d=6 σ=0.25 | **0.1553** (n=50) |
| this harness, diagonal (g=0,s=0)+(g=1,s=1) | **0.1553** (n=50) |

Agreement to four decimals. The harness is E2.

### Result

| campaign seed | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| cell mean | 0.1617 | 0.1668 | 0.1396 | 0.1574 | 0.1458 | 0.1506 | 0.1498 | 0.1543 | 0.1573 | 0.1359 |

| campaign seed | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|
| cell mean | 0.1652 | 0.1679 | 0.1487 | 0.1523 | 0.1705 | 0.1535 | 0.1427 | 0.1563 | 0.1542 | 0.1327 |

**qLogEI design-averaged 0.1532, SD 0.0102**, range 0.1327–0.1705, 1000 campaigns over all
20 registered seeds. E2's draw (0.1553) sits at the **60th percentile** — unremarkable, as
it should be.

**The mean did not move at all between 8 seeds and 20: 0.1532 both times, to four
decimals.** The SD rose from 0.0082 to 0.0102, which is the expected direction — eight
draws under-estimate a spread — and it lands inside the registered 0.010–0.018 interval
that the 8-seed number missed. See the re-scored predictions below.

**qLogEI's number moves by −0.0021 when design-averaged. `lhs` moves by +0.0482.**
Twenty-three times less. That is the asymmetry Q48 argued for and could not measure:
qLogEI shares only its 14-point opening and chooses the other 34 points from each
instance's own data, so it has far less shared-design variance to average away.

### The comparison Q48 could not make

|  | as E2 reports | design-averaged |
|---|---|---|
| `lhs` | 0.1270 | **0.1752** |
| `qlogei` | 0.1553 | **0.1532** |
| **verdict** | LHS ahead by 0.0283 | **BO ahead by 0.0220** |

**Paired at instance level, both arms design-averaged (n=25):**

> **`lhs − qlogei` = +0.0219 [+0.0145, +0.0292], Wilcoxon p = 1.8×10⁻⁵, qLogEI wins
> 21 of 25 instances.**

Two point estimates would not have been enough; this is the paired inference. The `lhs`
side is a per-instance mean over 60 designs, the `qlogei` side a per-instance mean over 8
campaign seeds. The qLogEI side therefore carries more averaging error, which **widens**
the paired differences — the interval is conservative, not flattering.

> **✅ FIXED 2026-08-14 — and fixing it found that the numbers were stale.**
>
> The defect was real: `run_q48_design_variance.py:82` collapses per-instance regrets to
> `np.mean(out)` before returning, so `q48-design-variance.json` holds 60 cell means per
> arm and nothing underneath. No script could regenerate the paired block.
>
> The prescribed fix is done. `scripts/q50_paired_recompute.py` re-runs the `lhs` arm
> (static design, no BO cost — 7 seconds) keeping the per-instance axis, pairs it against
> the committed sweep **by `instance_id` rather than by list position**, and writes
> `results/q50-paired.json` with both per-instance vectors so the next pairing needs no
> re-run at all. Locked by `tests/test_q50_paired.py`.
>
> **What it turned up.** The published figures were computed over **8 campaign seeds, not
> 20**, and were never refreshed — precisely because no script existed to refresh them.
> The script reproduces both, which is how the gap was identified rather than guessed at:
>
> | | published (8 seeds) | corrected (20 seeds) |
> |---|---|---|
> | mean `lhs − qlogei` | +0.0219 | **+0.0220** |
> | 95% CI | [+0.0145, +0.0292] | **[+0.0170, +0.0272]** |
> | Wilcoxon p | 1.8×10⁻⁵ | **6.0×10⁻⁸** |
> | BO ahead on | 21 of 25 | **25 of 25** |
> | Bonferroni over 39 | 7.1×10⁻⁴ | **2.3×10⁻⁶** |
>
> **The staleness was undetectable from the headline.** qLogEI's arm mean is 0.1532 to
> four decimals at 8 seeds and at 20 — this entry says so two paragraphs above, and that
> stability is exactly what hid the problem. Only the paired statistics moved, and they
> moved *in BO's favour*, so the correction strengthens the claim rather than weakening
> it. Direction and point estimate unchanged.
>
> **Residual defect — also now fixed, same day.** `cell_mean` was split into
> `cell_regrets`, which returns the `(n_instances, n_seeds)` array, and a thin `cell_mean`
> wrapper that collapses it for existing callers. `q48-design-variance.json` now carries
> `per_instance`, `per_instance_design_averaged`, `instance_ids` and `noise_seeds` for
> **all 12 arm-cells**, not just the one this claim needed. 477 KB, 15 s to regenerate.
>
> The regeneration was checked to be **additive**: every pre-existing value —
> `e2_reported`, `design_averaged`, `design_sd`, `percentile_of_e2` and all 60 `draws` per
> record — is bit-for-bit identical to the previously committed file, and the new detail
> reconstructs each of them. So no published number moved.
>
> `q50_paired_recompute.py` now **reads** that artefact instead of re-running, with
> `--recompute` kept as a cross-check. The two paths agree to 0.000e+00 per instance,
> which is a genuine two-implementation verification rather than one script agreeing with
> itself. Any future paired claim against another cell or arm is now a read, not a re-run.

**Multiplicity.** "Latin hypercube also beats BO" was one of Q39's 39 non-primary
contrasts, so this re-analysis **replaces** a member of that family rather than adding
one. At p = 1.8×10⁻⁵, even Bonferroni over all 39 gives p = 7.1×10⁻⁴. It survives any
correction this project applies.

### 📌 Predictions scored

Scored at the **completed 20 seeds**. The 8-seed column is kept because the two disagree
on one row, and which of them was the partial run matters.

| registered | at 8 seeds | at 20 seeds (registered n) |
|---|---|---|
| SD **smaller** than the static arms' 0.025 | ✅ 0.0082 | ✅ **0.0102** |
| "roughly 0.010–0.018" | ⚠️ under-shot | ✅ **0.0102 — inside the range.** |
| E2's draw near the middle, not an extreme | ✅ 62nd pct | ✅ **60th pct** |
| the reversal stands | ✅ established | ✅ **established** |

**The one row that changed is the one the scope reduction created.** At 8 seeds the SD
magnitude was scored wrong; at the registered 20 it is right. The prediction was correct
and the *partial run* was what missed it — eight draws under-estimate a spread, which is a
property of the truncation and not of the prediction. This is the case for finishing a
cancelled run even when the arithmetic says the conclusion is safe: the conclusion was
indeed safe, and a scored prediction was wrong anyway.

### ✅ SCOPE REDUCTION — STATED RATHER THAN SILENT, AND NOW CLOSED

> **CLOSED 2026-08-13.** All 12 cancelled seeds ran; the entry below is the record of the
> reduction, kept because its arithmetic was tested by the completion and half of it was
> vindicated. **Throughput was the whole story.** The 12 shards took **197–269s each**,
> against the 1,020–9,459s that forced the cancellation — the same work on the same
> machine, at concurrency 3 instead of contending. The 9× spread was contention, not the
> workload.
>
> **What the arithmetic got right:** the mean did not move — 0.1532 at 8 seeds, 0.1532 at
> 20. The 16-standard-error argument held exactly.
> **What it got wrong:** it defended the *conclusion* and said nothing about the *scored
> prediction*, and the SD row flipped from ⚠️ to ✅ on the extra seeds. A scope note can
> be right that the finding is safe and still leave a registered prediction mis-scored.

The registration specified **20 campaign seeds; 8 ran.** The machine's throughput
collapsed mid-run — four identical Q50 shards took **1,020s, 1,022s, 6,121s and 9,459s**,
a 9× spread on identical work, at load averages between 98 and 249 driven mostly by other
processes. The remaining 12 seeds were cancelled rather than left to contend with Q51.

**This does not weaken the conclusion, and here is the arithmetic rather than an
assurance.** The quantity at issue is whether qLogEI's mean moves by ~0.048 as `lhs`
did. With SD 0.0082 over 8 seeds the standard error of its mean is **0.0029**, so a
0.048 shift is **16 standard errors** away from what was observed. Twelve more seeds
could not change that. The reported SD itself is the less precise number — with 7 degrees
of freedom its own 95% interval is roughly 0.005–0.017 — but every value in that range is
well under the static arms' 0.025.

### What this changes in the write-up

**`docs/CLAIMS.md` L19 moves from "indicated, not established" to established**, and any
sentence reporting "Latin hypercube also beats BO" at the registered primary cell is now
not merely a tie under Holm (Q39) but **reversed**: BO is ahead by 0.0219, p = 1.8×10⁻⁵.


---

## 📋 Q52 — BUDGET-TO-TARGET CURVES. §1 complete; §2 registered and NOT yet run.

**Files:** `results/q52-floor.log` · `results/q52-floor.json` ·
`results/q52-flatten.log` · `results/q52-flatten.json` · `src/boec/identification.py`

The brief asks how many evaluations each method needs to reach a given quality of answer,
and requires the floor check to gate it: *"If the floor is above 0.10, this experiment
measures censoring rather than efficiency, and that is worth knowing in an afternoon
rather than after a week of compute."*

### §1.1 — identification error. **The construction did not do what it was built to do.**

Plant the true optimum in the visited set, score normally, and whatever regret survives is
identification error rather than search failure. Verified as a precondition: across all 50
instances `|truth(x*) − optimum_value| = 0.00e+00`, and no design point ever beats the
planted one.

It was registered as an **oracle-search lower bound** — a regret no arm could beat. **It is
not one, and §1.2 refuted it the same afternoon:** qLogEI reports **0.049** at n=500,
d=6 σ=0.25, where the planted space-filling design gives 0.129 at n=384.

**Why the reasoning was wrong.** Rule A's cost on a mis-pick is the true value of
*whichever point won by luck*, so the bound needs the runners-up to be bad — and a good
optimiser's runners-up are not. Holding the planted optimum, the noise and `n` fixed and
varying only the spread of the competitors:

| competitors, n=384, d=6, σ_rel=0.25 | rule A regret |
|---|---|
| space-filling | 0.1226 |
| clustered near the optimum | **0.0144** — 8.5× lower |

**Concentration is protective under rule A, independently of finding a better point.** So
the §1.1 numbers are the identification penalty **of a space-filling design** — the static
arms' bound, not a universal one.

| cell | rule A (best over n) | rule C | hit rate at n=384 |
|---|---|---|---|
| d=6 σ=0.10 | 0.0432 | 0.0421 | 24% |
| **d=6 σ=0.25** | **0.1219** | 0.0781 | **8%** |
| d=8 σ=0.10 | 0.0425 | 0.0313 | 23% |
| d=8 σ=0.25 | 0.1214 | 0.0777 | 8% |

Within this design family rule A **worsens with budget** (0.0432 → 0.0746 from n=24 to
n=384 at σ=0.10) while rule C improves. At σ=0.25, n=384 the assay names the true optimum
in **8% of readouts, on a point it measured.**

### §1.2 — the curve does **not** flatten. Cap decided against it.

qLogEI, d=6 σ=0.25, one 500-evaluation campaign per instance scored at every prefix.

| budget | 24 | 48 | 100 | 200 | 300 | 500 |
|---|---|---|---|---|---|---|
| rule A | 0.1752 | 0.1748 | 0.1408 | 0.0946 | 0.0946 | **0.0487** |
| rule C | 0.0659 | 0.1111 | 0.1044 | 0.0526 | 0.0431 | **0.0440** |

Paired at instance level, 100 → 500: rule A **+0.0921 [+0.0340, +0.1502]**, rule C
**+0.0604 [+0.0165, +0.1106]**. Both clear of zero. **Regret is still falling at 500** —
it drops 72% from the project's budget of 48.

⚠️ **SCOPE, stated rather than silent: 4 instances, not the 12 launched.** Stopped early
because the question §1.2 asks is directional and already answered — the 100→500 contrast
excludes zero under both rules. The 100→200 and 100→300 contrasts under rule A do *not*
(CI covers zero), and with n=4 they would not be expected to; that is a power statement,
not evidence of flatness, and no claim rests on them. Machine throughput was the binding
constraint: unrelated desktop processes held 100–200% of CPU throughout.

### 📌 TARGETS — registered, none pruned

```
0.30 · 0.25 · 0.20 · 0.15 · 0.12 · 0.10 · 0.08 · 0.05
```

**All eight kept.** Two reasons, both decided before §2 runs. First, the §1.1 numbers
bound only the static arms, and qLogEI at n=500 already reaches 0.049 — below every target
in the list — so nothing can be pruned as universally unreachable. Second, a target
reachable only at σ=0.10 must be kept regardless, because "reachable if you halve your
assay CV" **is** the §3.4 noise contrast, not a nuisance.

Recorded so it cannot be re-decided later: under rule A at σ_rel=0.25 **every target
tighter than 0.15 is below the static arms' identification error**, so those arms are
expected to be censored there. That is a prediction about censoring, not a pruning.

### 📌 CAP — 200, and it is a compute limit, not a scientific one

§1.2 shows the curve still descending at 500, so a cap of 200 **will** censor the tighter
targets for reasons that have nothing to do with the arms. This is registered explicitly:
wherever a censored result is reported, the cap is reported beside it, and no arm is
described as "unable to reach" a target that the cap forbids it from trying for.

### 📌 REGISTERED PREDICTION

The brief's, verbatim:

> At σ = 0.25, no arm reaches the tighter targets and savings ratios are undefined across
> most of the curve. At σ = 0.10, BO reaches targets in fewer evaluations than DoE under
> the posterior-mean rule, and the advantage grows as the target tightens.

**§1 already puts the first clause in doubt**, and that is registered here rather than
discovered later: qLogEI reaches 0.049 at σ=0.25 given 500 evaluations. Under a cap of 200
it reaches 0.0946, which clears 0.15 and 0.12 but not 0.10. So the honest form of the
prediction is *"undefined below 0.10 at σ=0.25, under a cap of 200"* — a statement about
the cap.

**Three further predictions, mine, with what would falsify each:**

**P1. The savings ratio inverts as the target tightens.** At loose targets (0.30, 0.25) the
static arms arrive first, because 24 well-spread points beat 24 adaptive ones before the
surrogate has anything to fit. At tight targets BO arrives first or alone. *Falsified if
the ratio is monotone in either direction across the whole curve.*

**P2. The savings ratio is larger under rule C than rule A at every target.** Rule A
credits the static arms with their luckiest draw. *Falsified if rule A shows the larger
saving at more than one target.*

**P3. Censoring under rule A will be worse at n=200 than at n=100 for the static arms** at
σ=0.25 — because their identification error rises with budget (§1.1) while their search
gain flattens. This is the sharpest test of §1.1's mechanism on a real arm. *Falsified if
static-arm rule A regret at 200 is below that at 100 with a CI clear of zero.*

### 📌 §2 DESIGN — registered before any §2 number existed

Everything below was fixed and committed **before the runner was written**. Check this
commit's timestamp against `results/q52-budget-to-target.json`. The targets, the cap and
the four predictions above are unchanged; what this section adds is the design the brief
left unspecified, and it is recorded here rather than discovered in a script.

**Why it had to be added at all.** The brief names targets, a cap and predictions but
never says how the classical arm spends a budget other than 48 — and it cannot, as built:
`STAGE1_FRACTION` is *"a table and not a formula"*, defined only at 48, and `run_doe_arm`
**raises** on any other budget rather than spending 47 or 49. Without a policy there is no
DoE curve and therefore no savings ratio, which is why §2 stalled.

**Cells.** d=6, σ_rel ∈ {0.10, 0.25}. 25 instances, the E2 ensemble, same instance IDs.
One campaign seed per instance (E2 used two; one is a compute decision and is stated, not
hidden). d=8 is **not** run — declared out of scope, not attempted and dropped.

**Checkpoints.** `8, 12, 16, 20, 24, 32, 48, 64, 100, 150, 200`.

> ⚠️ **Sub-24 resolution is required, and this is a measured finding, not a preference.**
> Applying `boec.budget.first_budget_to_target` to the committed `q52-flatten.json`, qLogEI
> under rule C reaches **every target down to 0.10 at n=24 — the first checkpoint — in 4 of
> 4 instances**. On §1.2's grid the rule-C arrivals are therefore censored *from below* and
> every savings ratio computed on it would be understated. §2's grid must resolve below 24.

**Arms.** `qlogei`, `doe_repeat`, `lhs`, `sobol`, `random`.

**`doe_repeat` — the registered budget policy.** Run the unmodified 48-evaluation pipeline
with a fresh seed, repeatedly, carrying the best result forward; stop when the next full
pipeline would exceed the cap. At a cap of 200 that is **four complete pipelines = 192
evaluations, and the remaining 8 are deliberately not spent** — a partial pipeline is not
the method, and stage 4 is not optional (`doe.py`). So the DoE arm's own checkpoints are
**48, 96, 144, 192**, and this asymmetry is reported wherever its arrivals are.

- **Rule A:** best observed over every point measured across all completed pipelines.
- **Rule C:** the recommendation of the pipeline whose **stage-4 confirmation measured
  best** — a lab keeps the run that confirmed best. Reported at **both** the unconstrained
  and the constrained argmax, per Q41's *"all three scorings reported in every table,
  always."*

*Chosen over the alternatives on the record: scoring a fixed 48-run pipeline and censoring
it at 48 makes every savings ratio above 48 trivially infinite in BO's favour, which is a
strawman; designing new fractions and CCDs per budget requires minimum-aberration
generators that have not been verified at those sizes. Repeating is the weaker of the
defensible options for the classical arm — it never moves the design region — and that is
stated as a limitation rather than left for a reviewer.*

**Rules by arm.** Rule A for all five arms. Rule C for `qlogei` and `doe_repeat` only —
E2 established that no rule C exists for the static arms on the Hill oracle and producing
one needs a GP fit per arm per instance, which is a different experiment. P1 and P3 are
rule-A statements and are unaffected; P2 compares BO against DoE and is fully served.

**Savings ratio — defined before it is computed.**

```
savings(T, rule) = median over instances of [ arrival(doe_repeat) / arrival(qlogei) ]
```

Paired per instance, **complete cases only** — an instance contributes only if *both* arms
arrive within the cap. `> 1` means BO arrives sooner. Reported always with `n_paired` and
the per-arm censoring counts beside it. **Undefined, and reported as undefined, if fewer
than 13 of 25 instances have both arms arriving** — a ratio over a censored minority is a
statement about who survived, not about efficiency.

**Censoring.** `boec.budget.ARRIVAL_CENSORED`, reported with the cap beside it. No arm is
described as "unable to reach" a target the cap forbade it from trying for.

### 📌 §2 DESIGN — AMENDED AND SUPERSEDING, still before any §2 number

The brief was reissued with a fuller specification before the runner had produced a
single number; the smoke test had caught one defect and nothing else had run. This
section **supersedes** the design above wherever they differ. What is unchanged: cap 200,
d=6, σ_rel ∈ {0.10, 0.25}, n=25, `doe_repeat` as the budget policy, complete-case pairing.

**Arms — four, production configurations, no tuning.** `doe` (repeat-keep-best),
`qlogei`, `random`, `spread_gp`. `spread_gp` is an LHS design of *n* points with a GP fit
to it, reported at the GP's posterior-mean argmax — the arm that separates *"a model
helps"* from *"adaptive sampling helps"*. `lhs` and `sobol` as bare static arms are
**dropped**: Q48 established that at 48 points in six dimensions lhs/sobol/random are
indistinguishable (0.1752/0.1777/0.1778 design-averaged), so carrying all three would
spend compute on a distinction already measured to be absent.

**`doe` tie-breaking — registered rather than left to float equality.** If a repeat's
stage-4 confirmation **exactly equals** the incumbent's, the **earlier** pipeline is kept.
The incumbent is already paid for, and deciding an exact tie by recency would make the
reported answer depend on floating-point equality between independent runs.

**`doe` seed derivation.** `seed(instance, repeat) = H(instance_id, 7000 + repeat_index)`
— a hash of the instance and the repeat index, never a global counter, so a repeat is
reproducible from its own coordinates and no arm's seeds depend on how many other jobs
ran first.

**Targets.** Posterior-mean rule (rule C): `0.30 · 0.25 · 0.20 · 0.15 · 0.12 · 0.10 ·
0.08 · 0.05`. Best-observed rule (rule A): `0.03 · 0.02 · 0.01`, tighter because the
loose targets are trivially reachable and would measure sampling luck.

> **Registered now so it is not a later addition: the full 11-target set is computed
> under BOTH rules and all of it is written to the artifact.** Extracting an arrival from
> a stored curve costs nothing, and computing only the designated set would mean a
> re-run to answer any follow-up. The designated sets above are the **headline**; the
> remainder is reported as an appendix and is not eligible to become the headline.

**Rounds-to-target, reported beside evaluations** — a lab pays in rounds (Q38).
`doe` spends **3 rounds per pipeline** (screen, response-surface, confirmation), so *k*
repeats cost 3*k*. `qlogei` spends `1 + ceil((n − 14)/4)` at d=6. `random` and
`spread_gp` are one-shot designs and spend **1 round** at any *n*.

**Censoring.** Fraction censored reported in every cell beside every median. **Above 50%
censored at a target: the rate is reported and no point estimate is.** A median over only
the instances that arrived is stated to be biased — the arm that fails most often would
look best — and is never the headline. The savings ratio is **undefined** wherever either
arm is censored; the cap is never substituted for an arrival.

**Fidelity gate, run before the grid is trusted.** qLogEI is re-run at budget 48 under
E2's seed convention and scored rule A against the stored per-row regret in
`results/e2-grid.json`. The maximum absolute deviation is reported. This is the
equivalent of Q50's diagonal check and the grid is not reported without it.

### 📌 §2 REGISTERED PREDICTION — mine, with its falsifier

**P4. Under rule A the tight target set is censored almost everywhere, and the rule-A
savings curve is undefined across its whole length.** §1.1 measured the identification
error of a space-filling design at **0.1219** (d=6 σ=0.25) and **0.0432** (σ=0.10); the
registered rule-A targets are 0.03, 0.02 and 0.01, all far below both. qLogEI reaches
0.0946 at n=200 and 0.049 only by n=500, so the cap forbids it too.
*Falsified if any arm reaches 0.03 in more than half its instances at either noise level.*

**P5. Under rule C the savings ratio exceeds 1 at every target, but a large part of it at
loose targets is DoE's granularity and not BO's efficiency.** The classical arm cannot
answer before 48 evaluations at all, while §1.2 shows qLogEI already at every rule-C
target down to 0.10 by n=24. So a savings ratio near 2.0 at loose targets is close to the
mechanical floor 48/24 and **must not be read as adaptive efficiency**. This is registered
before the run precisely so the number cannot be presented that way afterwards.
*Falsified if the loose-target ratio is materially above 48/24 = 2.0.*

**P6. The noise contrast is where the real finding is: savings grow as σ falls.** At
σ=0.10 the identification floor drops roughly 3×, so tighter targets become reachable and
the adaptive arm's advantage has room to express itself.
*Falsified if the σ=0.10 savings curve is at or below the σ=0.25 curve at most targets.*

**Conservative direction, stated as a limitation now rather than conceded later.** The
`doe` arm repeats a fixed pipeline and **never moves its design region**; classical
sequential RSM would insert a steepest-ascent phase (L10) which would very likely improve
it. **So this curve understates DoE, and every savings ratio here is biased in BO's
favour.** L10 is updated to say so.

**Status: §1 complete and reported. §2 design amended and registered above; run pending.**

---

# 📋 Q53 — spread_gp ON THE EXTERNAL FAMILIES. Registered before the runner exists.

**Status: registered. No runner file exists at this commit — check the timestamps.**

`docs/INFORMATION-MATRIX.md` established that `spread_gp` — a one-shot LHS design, one GP fit,
scored at the posterior-mean argmax — **ties qLogEI on the Hill family** under both rules at both
noise levels, at budget 48, while spending **1 round against qLogEI's 10**. It also established
that the arm has run on **nothing but Hill**. Q42 answers the same generality question for `doe`
vs `qlogei` on four external families; this closes the same gap for `spread_gp`.

## §1 THE REGISTERED PREDICTION

> **PRIMARY: `spread_gp` loses to qLogEI on Hartmann6, at both dimensions and both noise levels,
> under both scoring rules.**

**Reasoning.** A one-shot space-filling design has nothing to exploit on a deceptive surface.
Adaptive search is exactly what Hartmann6 rewards, and Q42/Q51 established that BO wins every
Hartmann6 cell under every rule, by +0.2460 to +0.4134. **The Hill tie is expected to be
Hill-specific.**

> **SECONDARY, low confidence: on Levy, Rosenbrock and Ackley the result is unpredicted.**

Ackley in particular is multimodal and near-flat, so neither arm should do well and the contrast
may be null for uninformative reasons. **Ackley's rule A is VOID for the DoE arm** (its optimum is
the box centre, and every CCD carries centre runs) — but that void does **not** extend to
`spread_gp` vs `qlogei`, because neither arm's design is guaranteed to contain the centre. An LHS
draw hits the exact centre with probability zero. **Ackley is therefore reported here, not voided**,
and that is a departure from how Q42 treats the same family. Recorded now so it is not read later
as convenience.

**FALSIFIER.** If `spread_gp` ties or beats qLogEI on Hartmann6, **the Hill result becomes the
suspicious one, not this one.** Both then need re-examining rather than the new number being taken
at face value. Specifically it would mean a one-shot design is competitive on a surface built to
reward adaptivity, which is more likely to indicate that 48 points in 6–8 dimensions is too small
a budget for adaptivity to express itself at all than that space-filling is a good search strategy.

## §2 WHAT RUNS

Arm exactly as implemented at `scripts/run_q52_budget_to_target.py:201-211`. **No modification,
no tuning, production configuration:** `lhs_design(bounds, 48, seed)` → evaluate once → one
`build_gp` → `constrained_argmax` of the posterior mean at `n_restarts=20, raw_samples=4096`.

**Grid — matched to Q42 exactly:** families `hartmann6 · levy · rosenbrock · ackley`;
`d ∈ {6,8} × σ_rel ∈ {0.10, 0.25}`; **budget 48**; `UnitScaled` wrapper; `[0,1]^d` bounds;
Hartmann6 at d=8 via `Embedded(Hartmann6(), dim=8, seed=0)`. **All sixteen family-cells. No
reduction.**

⚠️ **DEVIATION FROM THE BRIEF, stated before the run.** The brief says *"n = 25 instances × 2
seeds"*. That is the **Hill** convention and it does not apply: the external families are single
functions, not ensembles, so Q42's clustering unit is **seed**, and Q42 ran **`N_REPS = 25`
seeds**. Matching Q42 is the stronger requirement — §5 of the brief demands the same instances —
so this runs **25 seeds**, and the comparison is paired on seed. Calling 25 seeds on one function
"n=25 landscapes" would be the pseudo-replication this project criticises the source paper for,
and it is not claimed.

**Both rules.** Rule A = `reported_best_curve` at the observed argmax. Rule C = true value at the
GP posterior-mean argmax. Same scoring functions as Q42's BO arm, so the contrast is like-for-like.

## §3 THE DESIGN LOTTERY, HANDLED IN ADVANCE

`spread_gp`'s two independent measurements of the *same* Hill cell differ by **0.0239**, about one
design SD. That is Q48's defect (D16) caught a second time, and **a single-draw number from this
arm is not quotable.**

> **Registered: `D = 5` independent LHS draws per (family, cell, seed), averaged within seed
> before any test. The design SD across those draws is reported beside every point estimate.**

**And the registered stopping rule for interpretation:** *if a family-cell contrast is smaller in
magnitude than that cell's design SD, it is reported as **"within design noise"** and is not
called a result*, whichever direction it points. Fixed now so it cannot be applied selectively.

## §4 ANALYSIS, FIXED BEFORE THE NUMBERS EXIST

- **Primary contrast:** `spread_gp − qlogei`, paired on seed, per family-cell, both rules.
  Positive = qLogEI better. Instance bootstrap for magnitude; Wilcoxon for the yes/no (**Q20 §2** —
  if they disagree, the disagreement is reported, not resolved).
- **Also reported: `spread_gp − doe`** wherever `doe` is not censored, from Q42's committed rows.
- **Holm across the sixteen family-cells**, since none of these is a registered primary (**Q39**).
- **Rounds stated per family:** `spread_gp` = **1**, qLogEI = **10** at budget 48 with q=4 and a
  14-point opening. The cost argument is the point of this arm.
- **Every cell reported, including where `spread_gp` loses badly.**

## §5 GUARDS

- **Fidelity first.** Re-run Q42's qLogEI arm on a sample of stored rows and reproduce them before
  any new number is trusted. **The match is reported whatever it is.** Q42's rows are the
  comparator, so if they do not regenerate, nothing here is comparable and the run is void.
- **Same instances as Q42** — same oracle constructors, same seeds, not regenerated, not reseeded.
- **Checkpoint per family-cell.** Written incrementally; a kill costs one cell, not the run.
- **Time one cell before committing to sixteen.**

## §6 AFTERWARDS

`docs/RESULTS.md` entry · whether the prediction held, **stated either way** · the generality
sentence updated to either *"holds across five families"* or *"Hill-specific; loses on deceptive
surfaces"* · design SD wherever a `spread_gp` number appears.

**No follow-up run. One run, registered, reported once.** If the result is null or unfavourable it
is reported as-is.

---

# K-SERIES — SPADE GO/NO-GO

Registered 2026-08-20, **before any runner in this series exists**. Plan:
`docs/superpowers/plans/2026-08-20-spade-go-no-go.md` (body + Amendments A, B, C).
Timestamps are checkable against the commits that add each script.

## K1-gate — can a committed campaign be regenerated?

No file in `results/` stores `X` or `Y`. `results/e2-grid.json` rows carry
`[instance, dim, sigma, seed, arm, best, regret, auc_post_init]` and nothing else, and
Q42/Q57/Q58/d20 are likewise scalar-only. Every downstream K-test needs the observations,
so they must be regenerated from `(instance, dim, sigma, seed, arm)`.

**Question.** Does a regenerated campaign reproduce the committed `regret` column exactly?

**Decision rule, fixed before the numbers exist.** The **measured** per-arm worst
`|delta|` becomes the gating policy for K0, K6, K1 and K3.

* `doe` has no acquisition optimiser, so **exact equality is the right bar** and a failure
  there is a hard stop: it would mean the ensemble order or seeding convention has
  drifted, and every downstream number is unsafe until that is understood.
* `qlogei` / `qlognei` route through multi-start L-BFGS-B. Q54 measured that path at
  worst `|delta|` 2.463e-06 with 482/550 exact. **If they are not exact they get Q54's
  treatment** — gate on whether a *verdict* changes under a ±(worst delta) shift, with a
  ceiling far below the effect being measured. **A constant is never raised to make a
  gate pass.**

Winner not pre-written. Either outcome is reported.

## K6 — does the design-space deliverable rank arms differently from regret?

**Primary metric:** Brier score and AUC of the probability map against `1{f >= tau}`, plus
IoU of `D_gamma` against the true superlevel set.
**Primary object:** Peterson `D_gamma = {x : P(Y >= tau | x) >= gamma}` on the posterior
**predictive** (Peterson 2008; Peterson & Lief 2010). The **latent** map is reported
alongside as secondary, because E3 measured latent coverage at 0.7644 against nominal
0.95 while predictive coverage recovers to ~0.90-0.92 — so **the gap between the two maps
is itself a result**, and it is the one a certificate would be built on.

**Grids, fixed now.** `gamma in {0.50, 0.70, 0.80, 0.90, 0.95, 0.99}`. Sobol 20,000 at
seed 0. **`tau` is registered as a FRACTION of `tau_max(gamma)`**, never as an absolute:
`tau_frac in {0.60, 0.75, 0.85, 0.95}` where
`tau_max = mu_max * (1 - z * sigma_rel)` and `s_typical = 0.19`.

Absolute `tau` must not be pre-registered, for a measured reason: at `sigma_rel = 0.25,
gamma = 0.95`, `tau_max = 0.589` at `s = 0`, so **any absolute grid above ~0.59 certifies
nothing for any arm at any budget** and returns a table of zeros. An earlier draft of this
registration carried `{0.70, 0.80, 0.85, 0.90}` and would have done exactly that.

**Dropped-factor policy.** For an axis with zero design variation (the classical arm's
screened-out factors, held at one value by `dropped_held_at`):
**(a) refuse to certify is PRIMARY** — a batch record needs a range for every CPP, and a
factor never varied has no evidence for any range. **(b) full range** is the declared
sensitivity, being what practice implicitly assumes; `false_inclusion_rate` exposes it if
unsafe. **(c) the GP's own answer is reported and labelled prior-driven**, because on a
zero-variance axis the likelihood is flat and the lengthscale reverts to the prior mode
0.5016 — so (c) is what fires silently if nobody decides, and its certified range would be
set by a BoTorch default.

**Empty regions are reported as counts, never as zeros in a mean.**

**Decision.** If the arm ranking on the primary metric matches the ranking on simple
regret, the design-space reframe adds nothing and SPADE Stages 4-5 are dropped. If it
diverges with the spread arm ahead, Version B is built. If it diverges with the clustered
arm ahead, that is a different paper and SPADE is not built.

## What is NOT registered here, and why

**The cost-assurance curve is withdrawn before running.** It rested on the yield optimum
being expensive. Measured across every family in the repo, `c(x*)` is hill 0.355,
hartmann6 0.345, ackley 0.500, levy 0.550, rosenbrock 0.744, against a space-filling
average of 0.500 — so four of five have no binding constraint, and rosenbrock's optimum is
identical in every coordinate, making it symmetric rather than a counterexample. Reported
as a negative result, not run as a metric.

## K6b — joint certification, and `alpha*` as a non-degenerate metric

Registered **before `scripts/run_k6b_conservative.py` exists**, and before any K6b number
is read. Additive to K6; K6 is not modified and its registered primary metric stands.

### Why

`{x : LCB(x) >= tau}` is 20,000 **marginal** statements presented as one **regional**
statement. A batch record asserts the joint quantity — the probability that *no*
certified point is false. Prior art: Chevalier (2013) Vorob'ev machinery; Azzimonti,
Ginsbourger, Chevalier, Bect & Richet (2016; SIAM/ASA JUQ 2021) conservative estimates;
Chevalier et al. (Technometrics 2014) batch SUR.

### The algebra, checked before it was used

Peterson's `P(Y >= tau|x) >= gamma` mixes **process** noise (irreducible) with
**estimation** uncertainty (reducible). Separating them, margin 1 is a threshold shift on
the latent field. Under this repo's **relative** noise `sigma(x) = sigma_rel*f(x)`:

```
Gamma = {f >= tau + z*sigma}
      = {f(1 - z*sigma_rel) >= tau}
      = {f >= tau / (1 - z*sigma_rel)}
```

and since `tau = tau_frac * tau_max` with `tau_max = mu_max(1 - z*sigma_rel)`:

```
theta = tau / (1 - z*sigma_rel) = tau_frac * mu_max        EXACTLY, for every gamma
```

Verified to machine precision at 12 `(gamma, tau_frac)` combinations before the runner
was written. **Margin 1 is therefore fully absorbed by the tau-as-fraction
parameterisation already registered for K6** — the latent excursion set depends on
`tau_frac` alone. `gamma` re-enters only as interpretation: at a given `tau_frac`, the
absolute `tau` promisable at content level `gamma` is `tau_frac * tau_max(gamma)`.

Consequence: K6b scores **4 thresholds** per campaign, not 24. This was not a convenience
choice; it is what the algebra forces, and it is a second reason the tau-as-fraction
registration was correct.

### What is computed

Per regenerated campaign, on a **2,000-point** Sobol subset (seed 0) with **512** joint
posterior draws — the joint covariance is 3.2 GB at 20,000 points but 0.14 s at 2,000
(measured), so conditional simulation replaces orthant probabilities and is a Monte Carlo
approximation of the same object:

* `alpha_star(theta)` — the largest confidence at which a **non-empty** conservative
  estimate exists. **Always defined**: as `rho -> 1` the Vorob'ev quantile shrinks to the
  most-certain point, so `alpha*` is bounded below by `max_x p(x)`. This is the metric
  that cannot degenerate the way a fixed-95% volume can.
* `vorobev_deviation(theta)` — expected symmetric-difference volume; the set-valued
  analogue of posterior variance, reported beside Brier and AUC.
* IoU of the **Vorob'ev expectation** against the true excursion set.
* `|CE_alpha|` at `alpha in {0.50, 0.80, 0.95}`, with **empty counted, never averaged**.

`theta in {0.60, 0.75, 0.85, 0.95} * optimum_value`, matching K6's `tau_frac` grid.

### Decision

Same as K6 and it does not get its own escape hatch. If the arm ranking on `alpha*` and
Vorob'ev deviation **matches** the ranking on simple regret, the reframe adds nothing and
SPADE v2 dies with v1. If it **diverges with the spread arm ahead**, v2 is the build. If
it diverges with the clustered arm ahead, that is a different paper.

### Stated limit, which travels with every number

`CE_alpha` is conservative **given the model**. Hyperparameters are plug-in, so their
uncertainty sits *outside* the guarantee — Azzimonti et al. flag this themselves. The
E3-style coverage check is reported beside it to quantify what that costs.

## Version B — the two-plate arm. Registered before `src/boec/lse.py` exists.

**Why.** K6 and K6b tested plate 1 only. SPADE v2 is a two-plate method — its own spec
says *"the certificate is 2 rounds by default; one round is the map, not the batch
record"* — so plate 1 losing to qLogNEI (15 of 24 cells) does not settle it.

**Design.** Plate 1 = **40** wells space-filling. Plate 2 = **8** wells chosen by batch
LSE on the `D_gamma` boundary. Total **48**, budget-matched to every committed column.
The confirmation budget comes **out of** the design, never on top.

**Arms.** `versionb` (40+8 LSE) · `versionb_random` (40+8 random — the criterion must
earn its place) · `plate1_only` (48 one-shot, the Version A arm) · `qlognei` at 10 rounds
(the arm that actually beats plate 1) · `doe`.

**Reported on BOTH axes: wells and rounds.** Version B is 2 rounds against qLogNEI's 10.
Every K6 contrast was at equal wells only, and that under-reporting is corrected here.

**A design correction, recorded because it changes the implementation.** The averaging
rule from SPADE Stage 5 (*"decide by the mean of first and confirmation, never the
confirmation alone"*) governs **terminal selection among candidates**. Plate 2 here does
something different: it places wells at **new locations** to improve the map, so there is
no first reading at those points to average against. All 48 observations feed one refit.
Implementing "averaging" where it does not apply would be cargo-culting a rule from a
different stage.

**A correction carried from the research pass.** The optimal SUR points are **not** all on
the boundary — Azzimonti's own figures place some in the interior to secure regions a
boundary-only rule leaves uncertain. The criterion decides for itself; a boundary-only
rule is not hard-coded, and there is a test asserting it can leave the boundary.

**Registered kills, winner not pre-written.**
* Plate 2 does not close the map / `alpha*` gap to qLogNEI → **SPADE is dead** and the
  banked findings are the paper.
* Plate 2 does not beat 8 **random** wells → the LSE criterion is not earning its place,
  and the honest result is *"a second plate helps; the criterion does not"*.

## Step 0 — oracle-best for the spread arms. Registered before its runner exists.

**Why.** Q57 has oracle-best for `doe` (0.0597) and `qlogei` (0.0755) and **not** for any
spread arm. Without it the 0.0588 regret gap between `doe` and `versionb` cannot be
attributed, and the two candidate repairs have very different costs.

**Decision rule, fixed now, before the number is read.**

| `lhs` oracle-best | attribution | which fix |
|---|---|---|
| ≈ 0.06 (near `doe`'s) | **identification** — the wells found a good point, the terminal rule missed it | Fix 1, free, re-score only |
| ≈ 0.10 (near its rule-A 0.1270) | **search** — a spread design in 6D never visits a point as good as a 1/16-volume sub-box does | Fix 3, and Fix 1 alone cannot close it |

**Definition, matching Q57 exactly.** `oracle_best = optimum_value - max(truth(X_visited))`
— the true value at the genuinely best *visited* well, which is the ceiling any terminal
rule could reach. Rule A is `optimum_value - truth(argmax observed Y)`. Their difference
is the identification gap.

**Arms.** `lhs`, `sobol`, `random`, `versionb`, `plate1_only`, plus `doe` and `qlognei`
regenerated as a gate — the latter two must reproduce Q57's committed
`doe_oracle_best` / `nei_oracle_best` before any new number is read.

Winner not pre-written. Either attribution is reported.

## Fix 1 — the posterior-mean terminal rule. Registered before `scripts/run_fix1_terminal_rule.py` exists.

**Why.** Every regret number in this study is **rule A**: `reported_best_curve` picks the
well with the best *noisy* reading and scores the truth there. That rule **ignores the
surrogate entirely**. It is therefore applied identically to an arm whose posterior maps
the response well and to one whose posterior does not, and the two are scored as if
neither had a model. From `results/versionb.json`, mean AUC of the predictive map against
`1{f >= tau}` across `tau_frac in {0.60, 0.75, 0.85, 0.95}`:

| arm | AUC by `tau_frac` | rule-A regret |
|---|---|---|
| `versionb` | 0.7148 / 0.7435 / 0.8105 / **0.8850** | 0.1546 |
| `plate1_only` | 0.6819 / 0.7176 / 0.7904 / 0.8703 | 0.1270 |
| `qlognei` | 0.7061 / 0.6995 / 0.7344 / 0.7871 | 0.1532 |
| `doe` | **0.5704** / 0.5747 / 0.5982 / 0.6489 | **0.0958** |

**The claim under test.** That a posterior-mean terminal rule differentially favours the
arm with the better posterior — i.e. that the ordering above inverts, or narrows, when the
terminal rule is allowed to read the model.

**Why that is not implied by the AUC gap, and must be measured.** K6 measured `grid_r2`
**negative for every arm** — `-0.1756` (`lhs`) to `-6.1883` (`doe`) — so every arm's
posterior mean is a worse point predictor of `f` than the constant grid mean of `f`.
Negative `grid_r2` says the **level** is mis-scaled; AUC says the **ranking** is fine; and
an argmax needs only the ranking. A mis-scaled surface can still put its maximum in the
right place. The asymmetry is therefore neither implied nor excluded by K6's numbers, and
asserting it from them would be reading a ranking statistic as a statement about location.

**No new campaigns.** Every arm below is a *regeneration* of a committed campaign, gated
against its committed `regret` column before any new number is read.

### The two rules, stated exactly

* **Rule A (committed).** `optimum_value - truth(argmax_i Y_i)`, computed by the same
  `boec.replay.scored_curve` -> `reported_best_curve` path the committed column used. This
  is the gate, not a new number.
* **Rule P (new).** `optimum_value - truth(x_P)` where `x_P` is the argmax of the fitted
  GP's **posterior mean**:
  1. `model = build_gp(X, Y, Yvar, unit_bounds(6))` — the same fit K6 and Version B used,
     on the campaign's own observations. No refit variation, no hyperparameter change.
  2. **Screen** on the 20,000-point Sobol grid at **seed 0** (`boec.norms.sobol_grid`),
     evaluated through `boec.designspace.gp_adapter` — **chunked**, because
     `model.posterior` on a 20k grid is 100.6 s against 0.06 s at 2k and builds a 3.2 GB
     joint covariance whose off-diagonal is never used.
  3. **Polish** with `boec.metrics.constrained_argmax(posterior_mean, unit_bounds(6),
     n_restarts=20, raw_samples=4096, seed=0)`.
  4. `x_P` = whichever of the screened argmax and the polished point has the **higher
     posterior mean**.

  **Why the polish, and why those constants.** This repo already has a posterior-mean
  terminal rule — "rule C" in `boec.spread_gp.spread_gp_once`, `run_q52_floor.py`,
  `run_q53_spread_gp_families.py`, `run_q42_families.py` — and it is `constrained_argmax`
  at exactly `n_restarts=20, raw_samples=4096`. `spread_gp`'s docstring records those two
  constants as **load-bearing and not parameters by accident**, so that two arms' rule-C
  figures are produced by the same locator at the same effort. Fix 1 matches them rather
  than inventing a locator, or its numbers are not comparable to any rule-C number already
  on disk.

  **Why Sobol seed 0 rather than the campaign seed.** `spread_gp` passes the campaign
  seed; the grid registered here is seed 0. At seed 0 `constrained_argmax`'s 4,096-point
  screen is *literally the first 4,096 rows of the 20,000-point grid*, so the grid is a
  strict superset of the screen and step 4 is well defined instead of being a comparison
  of two unrelated draws. The Sobol seed is not one of the two load-bearing constants.

  The **grid-only** regret is written to the results file beside the combined one, so the
  polish's contribution is visible rather than assumed.

### Arms, and the committed column each is gated against

`d = 6`, `sigma_rel = 0.25`, budget 48, the 50 `(instance, seed)` pairs of the primary cell.

| arm | committed column | rounds |
|---|---|---|
| `doe`, `lhs`, `sobol`, `random`, `qlogei`, `qlognei` | `results/e2-grid.json` | 3 / 1 / 1 / 1 / 10 / 10 |
| `qlogei-add`, `qlogei-addonly` | `results/k6-designspace.json` (Q30's kernel arms have no E2 column; K6 is the committed artefact that carries their regret) | 10 |
| `plate1_only`, `versionb` | `results/versionb.json` | 1 / 2 |

**`versionb` is in the arm list because the registered kill below is stated about it.** It
is a regeneration of a committed campaign, not a new one; a kill that names an arm the
runner never scores is unfalsifiable.

**`plate1_only` is the same 48 wells as `lhs`.** Measured, not assumed: the two committed
columns agree to a worst `|delta|` of 4.44e-16 across all 50 pairs, an artefact of the
20-ordering mean `run_e2.static_curve` takes for the spread arms (`boec.replay`, module
docstring). It is kept because it is `versionb.json`'s Version A label and is gated against
that file, where it reproduces exactly; it is **not independent evidence** and must not be
counted as a separate arm in any ranking.

### The gate

Per row, `|regenerated rule-A regret - committed regret| == 0` **exactly**, for every arm.
K1 (`results/k1-replay-gate.json`) measured `doe`, `qlogei` and `qlognei` at worst
`|delta| = 0.0` over 500 rows; the spread arms are a single `evaluate` call; `plate1_only`
and `versionb` were checked at exactly 0.0 on a 3-key pre-flight run **before** this
registration was written. **No tolerance is introduced.** A single failure stops the run
and is reported, not absorbed.

### Statistics

Unit of analysis `(instance, seed)`, **n = 50**, paired. Per arm: mean regret under both
rules; the paired difference with a **4,000-resample percentile bootstrap of the paired
differences** (`numpy.random.default_rng(0)`) and a **two-sided Wilcoxon signed-rank** on
the same pairs. **Holm** across the arms. **SESOI 0.02.** Per Q20 §2, Wilcoxon governs
yes/no and the bootstrap reports magnitude; **disagreements between them are reported, not
resolved.**

*Caveat carried with every interval here:* Q57 clusters inference on landscapes (n = 25);
K6 and Version B pair on `(instance, seed)` (n = 50). This registration follows K6. The
intervals below are therefore the **narrower** of the two conventions in use in this
project and are not interchangeable with Q57's.

### Registered kill, winner not pre-written

Define **improvement** for an arm as `regret_A - regret_P`, positive when the posterior-mean
rule helps. The claim is an *asymmetry*, so it is tested as one, on the single
pre-registered contrast

    C = improvement(versionb) - improvement(doe),   paired on (instance, seed), n = 50

**If `doe` improves as much as `versionb` — that is, if `C` fails to favour `versionb` by
at least the SESOI of 0.02 with a significant Wilcoxon — the claimed asymmetry is not
there**, and a posterior-mean terminal rule is not the free repair. This is one test and
sits **outside** the per-arm Holm family, so it is not corrected twice.

Both outcomes are reported. A kill that fires is written up as a kill.

### What this may not conclude

Rule P re-scores the **same wells**. It cannot say that any arm would have *run* different
experiments, and it says nothing about a method that chooses where to look. A rule-P regret
is also not comparable to any published rule-A number: they are different estimands, and
every table that carries both must say which column is which.

## Amendment E, Phase 1.1 + 1.5 — E2 exclusion, E1 flatness, E6 the predictive straddle

Registered before `scripts/run_versionb.py` gains any diagnostic and before
`src/boec/lse.py` gains a predictive criterion. **`results/versionb.json` is not
regenerated and not overwritten**: it carries the headline containment result
(0.940 / 1.000 / 1.000 at `tau_frac = 0.60`) and the committed `versionb` column must stay
comparable across everything below. The new run writes to
`results/versionb-predictive.json`, and the four arms it shares with the committed file
must reproduce it at `|delta| = 0.0` or the run is a failure, not a finding.

### E2 — the exclusion radius. MEASURED FIRST, then resolved. Not a pre-registration.

This section records a measurement that was taken **before** it was written, because
Amendment E2 asserted a fact about the code and the first job was to check it. It is
labelled as such and must not be read as a registered prediction.

**Amendment E2 said:** `exclusion_radius` returns `median_lengthscale / 4 = 0.105`
Chebyshev at `ell = 0.42`; the median minimum pairwise Chebyshev distance among 8 random
points in 6D is **0.320**; the exclusion binds in **0 of 2,000** sampled batches; therefore
`batch_lse` is top-8 by score and the "WHY EXCLUSION IS NOT OPTIONAL" docstring describes
machinery that never fires.

**Both of its numbers reproduce exactly.** 2,000 batches of 8 uniform points in 6D,
`Generator().manual_seed(0)`: median minimum pairwise Chebyshev **0.3219**, and at
`r = 0.105` the radius binds in **0.15%** of them (3 of 2,000). Drawing the 8 points from
the runner's own 4,096-point Sobol candidate grid instead of the continuum gives **0.3265**
— the same answer.

**The inference does not survive, because the reference population is wrong.**
`batch_lse` does not draw 8 random points. It takes the greedy argmax of a straddle
surface, whose high-scoring candidates are concentrated near one contour, so its batch is
about **half** as spread out as a random batch. Measured on the live operating point — 50
plate-1 fits, `d = 6`, `sigma_rel = 0.25`, 40 LHS wells, the 4,096-point Sobol candidate
grid, `theta = 0.75 * mu_max`, exactly what `run_versionb.py` does:

| quantity | measured over 50 campaigns |
|---|---|
| median fitted ARD lengthscale (n=40) | **0.5982** |
| median exclusion radius, `ell/4` | **0.1495** |
| min pairwise Chebyshev of the **top-8 by score** | median **0.1572**, min 0.0869 |
| min pairwise Chebyshev of the **excluded batch** | median **0.1943**, min 0.1035 |
| campaigns where the top-8 batch **violates** its own radius | **22 / 50 (44%)** |
| wells relocated by the exclusion | mean **0.56** of 8 |

**Two corrections to E2's arithmetic.** `ell = 0.42` is the n=48 figure quoted in
`src/boec/designspace.py`; plate 1 is **40** wells and fits a longer lengthscale, so the
live radius is 0.150, not 0.105. And 0.320 is the spread of a *random* batch, which is the
population the criterion is supposed to beat, not the population it produces.

**Resolution: the mechanism is kept, the radius is NOT raised, and the docstring is
rewritten to state what was measured rather than what was assumed.** Raising a radius that
already binds in 44% of campaigns would be tuning a live knob to satisfy a claim the code
already meets; deleting a mechanism that relocates wells in 44% of campaigns would change
the committed `versionb` column, which is out of scope here. A regression test asserts
both halves — that the returned batch honours the radius, **and** that the top-q batch
would violate it — so the alarm fires if the mechanism ever does go inert, in either
direction. The achieved minimum pairwise Chebyshev distance is logged per batch, as
Amendment E2's own "Fix" asks, so the question never again has to be settled by argument.

### E1 — acquisition flatness. Threshold derived from the kernel, fixed before the run.

**Statistic**, computed on the 4,096-point Sobol candidate grid immediately before plate 2
is selected, per campaign, for the LSE arms only:

    acq_cv = SD(a(x)) / |mean(a(x))|,    a(x) = the arm's own straddle

`acq_sd` and `acq_mean` are logged raw beside it so `acq_cv` is recomputable and the
degenerate case `mean(a) ~ 0` is visible rather than hidden inside a ratio.

**Registered threshold: `acq_cv < 0.04` -> "acquisition uninformative at this density".**

**Derivation, from the kernel and the definition of the straddle. No campaign data was
consulted.** `build_gp` fits a Matern 5/2 (`use_rbf_kernel=False`,
`src/boec/surrogate.py:492`). For a unit-signal GP, a candidate at distance `r` from its
nearest design point has `s(r)/s_prior = sqrt(1 - k(r)^2)` with
`k(r) = (1 + sqrt(5)r/l + 5r^2/(3l^2)) exp(-sqrt(5)r/l)`:

| `r / l` | 0.25 | 0.50 | **1.00** | 1.50 | **2.00** |
|---|---|---|---|---|---|
| `s / s_prior` | 0.3093 | 0.5598 | **0.8517** | 0.9591 | **0.9903** |

Take **one fitted lengthscale** as the reference contrast — the shortest distance over
which this kernel says two candidates are meaningfully differently determined. Between a
candidate one lengthscale from the design and one effectively at the prior, `s` spans
`0.9903 - 0.8517 = 0.1386 s_prior`, so the straddle's `1.96 s(x)` term spans
`0.2717 s_prior`. Its mean is `1.96 s_prior - E|mu - theta| <= 1.96 s_prior`. Spreading
that range across the grid gives `SD = range/sqrt(12)`, so

    acq_cv(one lengthscale of contrast) = 0.1386 / sqrt(12) = 0.0400

**Using the largest admissible mean makes the threshold conservative in the safe
direction**: any smaller mean raises `acq_cv`, so a campaign is flagged only when it is
genuinely flat, never merely because its distance term is large. A grid below 0.04 contains
no candidate that is even one fitted lengthscale better determined than the typical one —
the criterion is ranking points the model cannot tell apart, and its top 8 are chosen by
whatever residual structure survives, which is a space-filling draw wearing a criterion's
name.

**Policy.** A campaign with `acq_cv < 0.04` is reported as *"acquisition uninformative at
this density"* and is **excluded from the E1 flatness-conditioned contrast**, reported as a
count, never averaged into a silent null. It is **not** dropped from the primary
`versionb` column, which stays exactly as committed.

**Decision, winner not pre-written.** Report the distribution of `acq_cv` over the 50
campaigns and the count below 0.04. If **no** campaign is below threshold, KILL 2's null is
not explained by flatness and E1 is closed as a negative result. If **some** are, the
`versionb` vs `versionb_random` contrast is re-run on the informative subset and reported
beside the full-sample contrast, with both `n` values stated. A subset result that reverses
the full-sample one is reported as a reversal, not substituted for it.

**Also logged per campaign, both LSE arms and the random control:** the achieved minimum
pairwise Chebyshev distance of the plate-2 batch, and the plate-2 design coordinates
themselves — so every claim in this section is recomputable from the committed file
without re-running a GP.

### E6 — `versionb_predictive`, a NEW arm. Registered before it exists.

**The defect.** `straddle_score(mean, sd, theta) = 1.96*sd - |mean - theta|` uses the GP's
`sd` alone: the **estimation** term. K6's registered primary object is Peterson's
**predictive** `D_gamma`, which additionally absorbs process noise, and section 5.7 of the
technical report measured the two regions differing enormously — 54%-69% of predictive
regions empty against 16%-25% of latent ones. **Plate 2 is currently resolving a boundary
that is not the boundary of the deliverable.**

**The new criterion.**

    straddle_predictive_score(mean, sd, theta, sigma)
        = 1.96 * sqrt(sd^2 + sigma^2) - |mean - theta|
    sigma(x) = sqrt((sigma_rel * mean(x))^2 + sigma_add^2)

`sigma` is an **array over the candidate grid, never a scalar**. This repo's noise is
relative (`y = f(1 + eps) + eta`), so a scalar `sigma` silently answers a homoscedastic
question the campaigns never asked — the same trap `predictive_probability_map` already
documents. The plug-in is the one `run_versionb.py` already uses for scoring, so the arm
targets the object it is scored against.

**It is an ADDITIONAL arm, not a replacement.** `versionb` keeps Bryan's published latent
straddle unchanged so the committed column stays comparable; `versionb_predictive` is a
sixth arm at the same 40+8 budget, same plate 1, same seeds, same refit, same scoring.

**Registered kills, winner not pre-written.**
* The predictive straddle does not beat the latent one on **AUC** — the validated metric —
  then E6 is a defect of description, not of design: the deliverable's boundary is not
  worth targeting at this density, and the committed `versionb` column needs no asterisk.
* It beats the latent one on `alpha*` but **not** on AUC or empirical containment -> the
  gain is model-internal and is reported as such, under section 1.4's rule that a validated
  metric beats a model-internal one and the disagreement is reported, not resolved.
* Its **empirical containment falls below nominal at any level** -> reported as a failure
  of the predictive arm. It cannot be repaired by re-tuning `sigma_pred`.

### Statistics for every contrast in this section

Unit of analysis `(instance, seed)`, **n = 50**, paired. **4,000-resample percentile
bootstrap of the paired differences** (`numpy.random.default_rng(0)`) and a **two-sided
Wilcoxon signed-rank** on the same pairs. **Holm across the cells** of each family.
**SESOI 0.02.** Per Q20 section 2, Wilcoxon governs yes/no and the bootstrap reports
magnitude; **disagreements between them are reported, not resolved.** Empirical containment
is a fraction of non-empty certified sets and is reported with its `n`, never averaged
across cells with different `n`.

**Metric status, carried with every number:** AUC and empirical containment are
**validated** — they consult the noiseless oracle. `alpha*` is **model-internal** — it is a
functional of the fitted posterior and nothing else, and section 1.4 of the technical
report shows it flattering exactly the arm whose posterior is least trustworthy.

---

# 🔴 PHASES 2–4 · PRE-REGISTRATION · **written and committed BEFORE any runner file exists**

**Registered:** 2026-08-21. **Standing rule being honoured:** *register before you run;*
this block is committed in its own commit, and no script named below exists on disk yet.
**Gate rule (D12):** every regeneration is gated against a **committed** column, never
against a regeneration of itself. **Tolerance rule:** no constant is raised to make a gate
pass; a gate that fails is reported as a failure.

## THE THREE DECISIONS I MADE ON JOSEPH'S BEHALF

He said "finish 2–4" without answering the three open scope calls. I made them rather than
stall the whole programme, and each is written here so it can be reversed by reading one
paragraph. **None of them modifies a committed quantity.** Two create *new, separately
named* estimands that sit beside the old ones.

### 🟢 DECISION 1 — Amendment A1 / Q30: **RE-RUN.**
`results/q30-additive.json` never existed, so `qlogei-add`/`qlogei-addonly` are
`CANNOT GATE` and 2,800 committed design-space rows rest on nothing. Phase 2's explicit
task is *"gate the kernel arms"*, which is impossible without this file. Cost ≈ 2.6 CPU-h.
Rejected alternative: gate them against `k6-designspace.json`, which is circular under D12.

### 🟢 DECISION 2 — Phase 3 τ: **RE-REGISTER AS A PER-FAMILY PREVALENCE QUANTILE, under a new name.**
`tau_frac` is **not modified and not deprecated**; every committed file keeps its meaning.
A **new** estimand `tau_q` is registered below. The reason `tau_frac` cannot cross families
is measured, not asserted: at one `tau_frac` the true superlevel set covers 0.00000 of the
box on ackley and 0.95550 on rosenbrock (COVERAGE-MATRIX §2.4). That is not a comparison.

### 🟢 DECISION 3 — Ackley: **IN, as a declared sensitivity, never as a headline.**
Under `tau_q` ackley's superlevel set is non-empty **by construction**, so the
`CANNOT RUN` verdict dissolves — it was a property of the threshold, not of the family.
It stays out of every headline for two reasons that survive the fix: the CCD evaluates the
box centre, which is ackley's exact optimum (blocker B3), and the DoE arm attains the
optimum in 7 of 25 instances. Its rows carry `sensitivity: true`.

---

## P5 · **`tau_q` — τ as a per-family prevalence quantile.** The new estimand, defined before it is used.

**Definition.** For a family `F` and dimension `d`, let `G` be the registered
20,000-point Sobol grid at seed 0 and `f` the *noiseless* oracle. Then

    tau_q(F, d, p) = Quantile_{x in G}( f(x), 1 - p )

so that the true superlevel set `{x in G : f(x) >= tau_q}` covers a fraction `p` of the
grid **by construction, identically on every family**. Registered grid:

    p in {0.75, 0.25, 0.10, 0.01}

**Why these four.** They reproduce the prevalence the committed `tau_frac` grid already
achieved on hill — 0.73569 / 0.28944 / 0.06844 / 0.00294 at `tau_frac` 0.60/0.75/0.85/0.95
— to within **0.0394**. So hill is scored on both grids and the two are comparable; the new
grid is calibrated against the old one rather than replacing it blind.

**What this is NOT.** It is not a fix to `tau_frac`, not a re-run of any committed cell, and
not a licence to re-score anything already published. `tau_q` rows live in new files with a
`tau_p` key; `tau_frac` rows keep theirs.

**Gate.** `tau_q` is a deterministic function of a committed grid and a noiseless oracle, so
it is checked by recomputation, not by campaign replay: `tests/test_designspace.py` must
assert the achieved grid prevalence equals `p` to within one grid cell (5e-5) for all four
`p`, all five families, both `d`.

**Kill condition, winner not pre-written.** If on hill the `tau_q` grid and the `tau_frac`
grid disagree on the **sign** of any arm-vs-arm AUC contrast that is significant under both,
the two estimands are reported as measuring different things and **no cross-family claim is
made from either**. Agreement is not assumed; it is the test.

**Output:** `results/p5-tau-quantile.json` — the τ table itself, every (family, d, p),
with achieved prevalence beside each. Committed before any family campaign runs.

---

## P1 · **Q30 re-run, and the retroactive validation of 2,800 committed rows.**

**What runs.** `scripts/run_q30_additive.py` as committed, current code, writing
`results/q30-additive.json`. Four arms, d ∈ {6,8} × σ_rel ∈ {0.25, 0.10}.

**Why this is a real gate and not circular.** `run_q30_additive.py` is the *original
campaign runner*; `src/boec/replay.py` is an *independent reimplementation*. Two
independent code paths agreeing at |Δ| = 0 is the same structure that makes
`e2-grid.json` a valid gate target. What it does **not** prove on its own is that the
kernel-arm rows **already committed** in `k6-designspace.json` came from these campaigns.
So:

**Registered kill condition — this is the point of P1, not a formality.**
After the gate passes, the `qlogei-add` and `qlogei-addonly` design-space rows are
**re-scored** and compared to the committed `k6-designspace.json` / `k6b-conservative.json`
rows. Then:
* **|Δ| = 0 on all 2,800 rows** → the committed kernel-arm rows are validated retroactively
  and A1 becomes citable under rule 1.
* **any Δ ≠ 0** → the committed kernel-arm rows are **WITHDRAWN**, §5.5 of the technical
  report loses its "cleanest figure", and that is reported as the P1 result. It is not
  repaired by re-running until it matches.

**Known-in-advance hazard, recorded so it cannot be discovered as a surprise.** The
2026-08-11 `q30-additive.log` means for the two optimiser arms do **not** reproduce from
the current `e2-grid.json` (`qlogei` 0.1666 vs 0.1553; `qlognei` 0.1512 vs 0.1532), while
all five non-optimiser arms reproduce exactly. A fresh run is therefore **expected** to
disagree with the old log. That disagreement is a **provenance finding about the log**, and
must be reported as one; it is *not* evidence about the additive kernel and may not be
written up as a change in the A1 result.

**Output:** `results/q30-additive.json` (the comparator) and `results/p1-kernel-gate.json`
(the gate + re-score verdict). **Never overwrite either.**

---

## P2 · **Version B on the γ ladder, with the four columns it has never had.**

**The gap, confirmed by audit §3.1/§3.2.** Version B's entire γ coverage is **one point**,
γ = 0.50 — K6's lowest-assurance corner and the only γ at which τ is unconstrained by the
noise floor. Its AUC at that point is **200/200 bitwise identical** to K6's γ=0.50 row, so
it is not independent evidence either. And it carries **no region metric that depends on γ
at all**: no IoU, no `sup_err`, no `grid_r2`, no false-inclusion.

**What runs.** All Version B arms — `versionb`, `versionb_random`, `plate1_only`,
`versionb_predictive` — through the **full 24-cell** (γ × τ_frac) K6 grid, γ ∈ {0.50, 0.70,
0.80, 0.90, 0.95, 0.99}, plus `iou_pred`/`iou_latent`, `sup_err`, `grid_r2`,
`fi_pred`/`fi_latent`, `vol_pred`, `empty_pred`.

**Gate.** `plate1_only` is `lhs` at 48 wells and **is** gateable against
`k6-designspace-spread.json · lhs` — worst |Δ| measured at 4.44e-16. It is the only gate
Version B has and it must be run. `versionb`/`versionb_random`/`versionb_predictive` are
**UNGATABLE in principle** (no comparator exists and none ever will); their guarantee is
seed determinism only, and every table carrying them says so.

**Registered kill, winner not pre-written.** `versionb` empirical containment is measured at
every γ. **If it falls below nominal at any γ × τ_frac × α cell, that is a failure of the
certificate and is reported as one.** The committed 0.940 / 1.000 / 1.000 at γ=0.50 is not a
prediction for the ladder; γ=0.99 tightens `tau_max` from 1.0000 to 0.4184 and there is no
reason the certificate must survive that.

**`plate1_only` may never be counted as a separate arm in any ranking** (D23.1). It is
`lhs`. Both are reported; neither is double-counted.

**Output:** `results/p2-versionb-gamma.json`.

---

## P7 · **Murphy calibration–refinement decomposition, 10 equal-count bins.**

Registered under Amendment A5 and never run. Brier = calibration − refinement + uncertainty;
A5's argument is that **refinement** is the new information, and the project has only ever
reported the sum.

**Specification, fixed here.** 10 **equal-count** bins over the predicted probability (not
equal-width — equal-width bins are empty at the tails where these maps live). Reported per
(arm, γ, τ_frac): `brier`, `calibration`, `refinement`, `uncertainty`, and `bin_counts`.
Identity check as a **test**: `calibration − refinement + uncertainty` must equal `brier`
to 1e-10 on every row, or the decomposition is wrong and the row is not written.

**New module** `src/boec/calibration.py` — **not** `designspace.py`, so it cannot collide
with P3's work in the same file.

**Registered decision rule.** If the arm ranking by **refinement** differs from the ranking
by **Brier**, the decomposition has found something and is reported as the A5 result. If the
two rankings are identical at every cell, A5 is a **null** and is written up as one.

**Output:** `results/p7-murphy.json`.

---

## P4 · **`coord` at the primary cell.**

A committed arm with 50 gated campaigns at d=6 σ=0.25 and **not one design-space metric
anywhere**. Cheapest possible widening of the ranking, 8 arms → 9. Gate against
`e2-grid.json · coord`. **Output:** `results/p4-coord.json`.

---

## D23-RESCORE · **Is `doe`'s rule-P collapse the design, or a BoTorch prior?**

**The finding it qualifies.** D20: under a posterior-mean terminal rule the regret ranking
inverts, `doe` 0.0958 → 0.1993, first to last. **The caveat:** `doe`'s posterior on its two
screened-out axes is prior-driven — the likelihood is flat there, so the lengthscale reverts
to the prior mode 0.5016. Part of the collapse may be a library default rather than the
design.

**The test.** Re-score `doe` under rule P with the argmax **restricted to its 4 kept
factors**, the 2 dropped factors held at the CCD's own hold values —
`CampaignRecord.kept_factors` and `dropped_held_at` already carry both, and
`tests/test_replay.py` already asserts they are recorded rather than inferred.

**Registered decision rule, winner not pre-written.**
* Subspace rule-P regret **recovers to within SESOI 0.02 of `doe`'s rule-A regret
  (0.0958)** → D20's reversal is **substantially a prior artefact**, and the headline must
  be relabelled *"DoE's model is unidentified off its screened subspace"*, which is a
  different and weaker claim.
* Subspace rule-P regret **stays near the full-space 0.1993** → the prior is not the
  mechanism, the response surface is (`grid_r2 = −6.19`), and D20 stands as written.
* **Anything between** → both mechanisms are live, the split is reported as a magnitude,
  and neither wording is used alone.

**Gate:** rule A must reproduce `e2-grid.json · doe` at |Δ| = 0 on all 50, as in Fix 1.
**Output:** `results/d23-doe-subspace.json`.

---

## P3 · **The three missing (d, σ_rel) cells** — (6, 0.10), (8, 0.25), (8, 0.10).

The only axis that is `NOT RUN` rather than `CANNOT RUN`. `tau_max` moves 0.589 → 0.836 at
σ_rel = 0.10, so the entire emptiness structure changes; the (6, 0.25) result that the whole
project rests on is currently a single point on this axis.

**Gate targets:** `e2-grid.json` for 7 arms; **`doe` at d=8 has no column there — use
`results/e2-doe-d8.json`** (audit §5, P3). A run that silently skips the `doe` d=8 gate is
the §3.6 defect repeating and is a stop condition.

**Output:** one file per cell, never merged over a cell boundary:
`results/p3-k6-d6-s010.json`, `results/p3-k6-d8-s025.json`, `results/p3-k6-d8-s010.json`,
and the matching `p3-k6b-*.json`.

### P3-B2 · **`tau_max` omits σ_add. Registered as a bounded sensitivity, NOT as a fix.**

`tau_max = mu_max(1 − z·σ_rel)` drops the additive term. Exact value is
`mu_max − z·sqrt((σ_rel·mu_max)² + σ_add²)`. Re-derived error: **3.288e-04** at σ_rel=0.25
and **8.204e-04** at σ_rel=0.10 — ratio **2.49**, not the 10× first claimed (D19).

**Decision: `tau_max` is NOT changed, and every P3 cell uses it unmodified.** Reason: if
the σ=0.10 cells used a corrected threshold and the σ=0.25 cells used the current one, the
σ axis would be confounded with a definition change — a far worse defect than 8e-4.
`tau_max_exact` is added **beside** it, used for nothing but the sensitivity below.

**Registered kill.** Re-score the (6, 0.10) cell — where the correction is largest — under
both definitions. If any arm-vs-arm contrast moves by more than **SESOI 0.02**, the whole
grid is re-registered on `tau_max_exact` and P3 is re-run. If not, the correction is
recorded as bounded-and-immaterial with the measured maximum movement stated.

**Output:** `results/p3-taumax-sensitivity.json`.

---

## P4b · **The α\* / regret rank inversion on the spread arms.**

**The anomaly, measured from committed files, stated before it is explained.** Mean α\* at
τ_frac = 0.75: `random` 0.6521 > `lhs` 0.6291 > `sobol` 0.5275. Committed regret at the same
cell: `lhs` 0.1270 < `sobol` 0.1724 < `random` 0.2216. **α\* ranks the three spread arms in
almost exactly the reverse of regret**, and `doe` — the worst response surface in the
project, `grid_r2` = −6.19 — scores α\* = **1.0000**, the maximum, at τ_frac = 0.60.

**Hypothesis to be tested, not assumed:** α\* is a functional of posterior *width*, so a
design that leaves large unsampled gaps buys a wider posterior, a more diffuse Vorob'ev
structure, and a higher α\* — i.e. the statistic rewards not knowing.

**Registered test.** Per campaign, regress α\* on the mean posterior sd over the registered
grid, within arm and across arms; report Spearman ρ of α\* against regret across the 9 arms
and its bootstrap CI.
* **ρ ≤ −0.5 with a CI excluding 0** → α\* is confirmed anti-correlated with the validated
  metric and **every table carrying α\* must carry that fact**.
* **CI includes 0** → the ranking is reported as an unexplained anomaly, recorded and not
  smoothed, in the manner of `docs/METHODS.md:583`.

**Output:** `results/p4b-alpha-star-anomaly.json`.

---

## P6 · **Family coverage** — hartmann6, levy, rosenbrock, ackley(sensitivity).

**BLOCKED on P5 and on B4's engineering** (family support in `replay.regenerate` + the
builder hook, ~11 h estimated). Runs only after `results/p5-tau-quantile.json` is committed.

**Gate columns, verified live by the audit at |Δ| = 0:** `qlogei` ← `q42-families.json ·
bo_a` and `d20-rescore.json · bo_a`; `doe` ← **`d20-rescore.json · doe_a_new`, NOT
`q42-families.json · doe_a`**, which is the pre-D20 column and is the obvious wrong target;
`qlognei` ← `q59-hartmann-no-screen.json`, **hartmann6 only**. `lhs`/`sobol`/`random` have
**no family gate column and are ungatable off hill** — every table says so.

**Registered kill.** If any family arm fails its gate at anything other than |Δ| = 0, the
family programme **stops** and reports the failure. It is not repaired by widening a
tolerance.

**Output:** `results/p6-families.json`.

---

## Statistics for every contrast in Phases 2–4

Unchanged from Amendment E and restated so no runner has to go looking: unit of analysis
`(instance, seed)`, **n = 50**, paired. **4,000-resample percentile bootstrap** of the paired
differences, `numpy.random.default_rng(0)`, **and** a two-sided **Wilcoxon signed-rank** on
the same pairs. **Holm across the cells** of each family. **SESOI 0.02.** Per Q20 §2,
**Wilcoxon governs yes/no, the bootstrap reports magnitude, and disagreements between them
are REPORTED, not resolved.** Empirical containment is a fraction of non-empty certified
sets, reported with its own `n`, never averaged across cells with different `n`.

**Metric status travels with every number.** VALIDATED (consults the noiseless oracle):
regret, oracle-best, AUC, Brier and its Murphy components, IoU, empirical containment,
false-inclusion, `sup_err`, `grid_r2`. MODEL-INTERNAL (a functional of the fitted posterior
and nothing else): α\*, `vorobev_deviation`, `ce_contain`. **A validated metric beats a
model-internal one, and the disagreement is reported.**

## Stop conditions for Phases 2–4

Halt and report, do not repair:
1. Any regenerated campaign missing its committed column by anything other than **0**.
2. `versionb` empirical containment below nominal — **now expected to be tested at γ up to
   0.99, where it may legitimately fail.** A failure there is a result, not a bug.
3. P1's re-score disagreeing with the committed kernel-arm rows.
4. Wanting to raise a tolerance, or to change any registered threshold in this block.

---

# 🔴 AMENDMENT F · **Four corrections to the Phases 2–4 registration, raised by Joseph 2026-08-21, registered before the affected analyses land**

Raised while the six Phase 2–4 agents were running. **Three of the four are analysis-layer
and cost no new campaigns; they are cheap now and expensive after the grid triples**, which
is why they are registered ahead of any cross-family run. Amendment F **supersedes the
"Statistics for every contrast in Phases 2–4" section above** where the two conflict.

## F1 · **n = 50 contradicts this project's own earlier convention. Every contrast runs BOTH ways.**

**The inconsistency, in the project's own words:**
* `docs/K6-TECHNICAL-REPORT.md` §3.8 — *"25 instances × 2 seeds = **n = 50** for every contrast."*
* `docs/RESEARCH-SUMMARY.md` — *"25 landscapes × 2 seeds; **average seeds first; n = 25.**"*

**These are different analyses and the difference is not cosmetic.** Two seeds on one
landscape share the landscape, so they are not independent units. Treating them as 50
inflates the effective sample size, narrows every bootstrap CI by roughly **√2**, and lowers
every Wilcoxon p-value. **The original paper chose the conservative version; K6 silently
chose the other, and nothing recorded the switch.**

**Registered fix.** Every contrast in Phases 2–4, and every contrast already reported in
`docs/K6-TECHNICAL-REPORT.md`, `docs/FINDINGS-SPADE.md` and `docs/OVERNIGHT-LOG.md`, is
computed **both ways**:
* **n = 50**, unit `(instance, seed)` — as currently reported.
* **n = 25**, unit `instance`, **seeds averaged first** — the conservative unit, and the one
  the earlier paper committed to.

Both appear in every table. Where they agree, the n = 25 column is the one quoted.

**Registered decision rule, winner NOT pre-written.**
* A result **significant under both** → reported as it stands, with the n = 25 p-value
  quoted, and it has gained a defence at zero cost.
* A result **significant at n = 50 and not at n = 25** → **downgraded to n = 25's verdict.**
  The n = 50 figure is reported beside it and explicitly labelled as the anti-conservative
  unit. It is not quoted alone anywhere.
* This applies **without exception to the two headline results** — the 24/24 screening
  contrast and D20's rule-P reversal. Their effect sizes make survival likely; *likely is
  not measured*, and a headline that has not been checked at the conservative unit is not
  citable under rule 1.

## F2 · **AUC is the least standard metric this project computes, and the two most standard ones are computed-and-unanalysed or uncomputed.**

**Two defects in AUC as the primary, both verified here rather than accepted:**

**(a) AUC is invariant to monotone transformation**, so it scores *ranking*, never
calibration — and a design space is a calibrated absolute statement, not a ranking.
Verified: mean `grid_r2` is **negative for all eight arms** — `doe` −6.1883, `qlognei`
−0.4526, `qlogei` −0.2939, `random` −0.2924, `qlogei-add` −0.2818, `qlogei-addonly` −0.2229,
`sobol` −0.1762, `lhs` −0.1756 — i.e. **the posterior mean is a worse point predictor than
the constant grid mean, for every arm.** *Stated precisely, because the arm mean is not the
row:* `doe` is negative in **1200/1200** campaigns, while the BO and spread arms are positive
in **4%–24%** of theirs. The arm-level claim holds; the row-level one does not, and only the
arm-level claim is used. **AUC cannot see any of this.**

**(b) AUC misleads under heavy class imbalance** (Davis & Goadrich 2006; precision–recall
preferred). §6.6 measures the imbalance: at γ=0.99, τ_frac=0.60 the minority class is about
**16 grid points out of 20,000**, so AUC there is estimated from a few dozen points.

**Registered fix, in priority order.**

**F2a — expected type I / type II error volumes become the PRIMARY design-space metric**
(Azzimonti & Ginsbourger 2018, Table 1 — what the cited community actually reports).
**They require no new campaigns.** Derivation from columns already committed:

    type_I_vol  = vol_pred * fi_pred                        # |D_est \ D_true| / |grid|
    intersect   = vol_pred * (1 - fi_pred)
    type_II_vol = true_frac_above_tau - intersect           # |D_true \ D_est| / |grid|

**Validated before registration, not asserted:** `intersect / (vol_pred +
true_frac_above_tau − intersect)` reproduces the committed `iou_pred` to a worst
|Δ| of **2.220e-16 over 2,553 rows**, and produces **zero** impossible negative type-II
volumes. The algebra is right.

**And it is better-defined than the metrics it replaces**, which is the part that was not
obvious: when `D_est` is empty, `fi_pred` and `iou_pred` are `nan` (0/0) — but type I volume
is **0** and type II volume is **the prevalence**, both exactly correct. Since 54%–69% of
predictive regions are empty at some cells (§5.7), **the error volumes are defined precisely
where AUC and IoU break.** Emptiness must be reported beside them regardless.

**F2b — AUPRC beside AUC at every cell**, and flagged as primary over AUC wherever minority
prevalence < 0.01. Requires the raw maps, so it is folded into the P7 re-score, which already
regenerates campaigns and recomputes maps at the primary cell.

**F2c — actually rank on IoU and Brier.** Both are computed and committed **per row** and
`scripts/analyse_k6.py` ranks on **neither**. This is a pure analysis gap: the data has been
on disk since K6 ran.

**F2d — the Murphy calibration–refinement split** (P7, already dispatched and running) is
the component AUC structurally cannot see. Its priority is raised from "registered, never
run" to a **primary deliverable of Phase 2**.

**Registered decision rule.** If the arm ranking under **type I / type II error volumes**
differs from the ranking under AUC, **the error-volume ranking is the reported one** and the
AUC ranking is retained beside it as the superseded figure. If they agree, AUC is vindicated
*at this imbalance* and that is stated with the prevalence attached.

## F3 · **A winner's curse inside `CE_α`, and it is the project's own optimizer's-curse mechanism operating inside its safety metric.**

`conservative_estimate` scans **64** Vorob'ev quantiles and selects the **largest** whose
containment, measured on **512 draws**, is ≥ α. That is a **maximum over 64 noisy
estimates**: any quantile whose *true* containment sits just below α is selected whenever
noise pushes its estimate above. **So `CE_α` is anti-conservative in expectation by
construction**, with bias growing in the number of ρ values scanned and shrinking in draw
count.

**Registered test.** Re-run K6b on a subset at **`N_DRAWS = 2048`** (4× the committed 512)
and test whether `alpha_star` and CE volumes shift **systematically downward**. Paired by
campaign, both n conventions per F1.

**Registered decision rule.**
* Systematic downward shift beyond SESOI → the committed `alpha_star` and CE volumes carry a
  **stated selection bias** and the 512-draw figures are corrected or withdrawn.
* No detectable shift → the bias is bounded at this draw count and that bound is reported as
  a number, never as "small".

**Recorded so it is not later claimed as foresight:** this bias may already be visible.
`doe`'s circular `ce_contain` reads 0.972–0.998 while its **empirical** containment against
ground truth is **0.000 / 0.240 / 0.500**. That gap is consistent with exactly this
mechanism, and the draw-count sweep is what separates selection bias from ordinary model
mis-specification. **Priority: after F1/F2/F4, before any cross-family claim about `CE_α`.**

## F4 · **The pooled containment figure treats one campaign as four. WITHDRAWN.**

§3.7 pools containment over `tau_frac` to **n ≤ 200** per (arm, α). The four thresholds are
computed on **the same campaign, the same posterior, the same 512 draws.** They are not four
Bernoulli trials.

**Registered fix.** The pooled figure — quoted as **"pooled 0.9307 / 1.0000 / 1.0000"** — is
**WITHDRAWN**, not recomputed with a wider interval. **Per-cell containment at n = 50 (and
n = 25 per F1) is the only reported form.** Any cross-τ_frac summary requires a
mixed-effects model with campaign as a random effect; until one exists, no pooled containment
number appears in any document. Every table states its `n` and its cell.

**This does not touch the per-cell numbers**, which were always the load-bearing ones:
`versionb` 0.940 (n=50) / 1.000 (n=50) / 1.000 (n=22) at τ_frac = 0.60 stands unchanged.

## Ordering, and what is blocked

**F1, F2a, F2c and F4 run on data already on disk and are cheap NOW and expensive after the
grid triples.** Therefore:

> **🔴 NO CROSS-FAMILY CAMPAIGN (P6) STARTS UNTIL F1, F2a, F2c AND F4 ARE COMMITTED.**
> P5 (`tau_q`) and B4 (family support in `replay`) continue — they are engineering and
> registration, not campaigns.

F2b folds into P7. F3 runs after F1/F2/F4.

## What was right, recorded because these were choices and not defaults

Carried forward unchanged, and each of these is a decision someone made rather than a
default that fell out:
* **Peterson's `D_γ` on the posterior *predictive***, carrying σ² rather than only s². This
  is the correct object and the standard one, and it is the part most implementations get
  wrong.
* **Empirical containment against ground truth**, and catching that `ce_contain` was
  circular — a defect of that shape usually survives to publication.
* **Holm across dependent cells** — valid, because Holm holds under arbitrary dependence, so
  it is conservative here, which is the right direction to err.
* **Wilson intervals with `n` reported per cell**, and refusing to count empty sets as
  successes.
* **The τ-as-fraction re-registration**, without which every table would have been zeros.

---

## 📌 ERRATUM 1 to the Phases 2–4 registration · **P1's scope sentence was wrong. The spec was right.**

**Raised by the P1 worker, verified, 2026-08-21. Recorded as an erratum rather than an edit —
a registration that is silently corrected after the fact is not a registration.**

**What P1 says:** *"Four arms, d ∈ {6,8} × σ_rel ∈ {0.25, 0.10}."*

**What is true:** `scripts/run_q30_additive.py` as committed is **`DIM = 6`** (line 59) with
**2 arms**. Two other statements in the record already agree with the code and disagree with
my summary sentence:
* P1's own **operative** instruction — *"`scripts/run_q30_additive.py` **as committed,
  current code**"* — which is what the worker correctly followed.
* `docs/COVERAGE-MATRIX.md` §5's cost model: *"200 campaigns; σ=0.25 at ~35 s and ~107 s,
  σ=0.10 at ~17 s → ≈ 2.6 CPU-h"* = **2 arms × 2 σ × 25 seeds × 2**, i.e. d=6 only.

So the summary was a **wrong gloss on a correct spec**, and the run proceeds as committed.
Both readings stay visible here on purpose.

**THE CONSEQUENCE, which is the part that matters.** `results/q30-additive.json` will carry
**d = 6 only**. Therefore:

| cell | `qlogei-add` / `qlogei-addonly` gate status |
|---|---|
| d=6, σ=0.25 | gateable once P1 lands |
| d=6, σ=0.10 | gateable **only if** P1's committed run covers σ=0.10 — to be read off the file, never inferred from its name |
| **d=8, σ=0.25** | **CANNOT GATE. No committed column exists and none is coming.** |
| **d=8, σ=0.10** | **CANNOT GATE. Same.** |

**P3 must mark those rows `gated: false` with an explicit `gate_reason`, not skip them.**
Silent skipping is the §3.6 defect this work exists to fix: `committed.get(...)` returned
`None`, `if ref is not None` swallowed it, and 100 campaigns lost their gate with no output
saying so. This is the **one** case where an explicit recorded `false` is correct rather than
a hard error, because the absence is now a registered fact rather than a bug.

---

## 📌 ERRATUM 2 · **Every `|Δ| = 0` gate in this project may be contingent on an unrecorded thread setting.**

**Found while diagnosing throughput, 2026-08-21.** The machine was at **57.7% sys vs 32.7%
user** with 116 processes runnable on 8 cores. Benchmarked back-to-back under that load, on
the real workload (`SingleTaskGP` fit at n=48 + a 2,048-row posterior):

```
threads=4 (torch default)   8.553 s per fit+posterior
threads=1                   1.865 s per fit+posterior     -> 4.6x faster
```

At n=48 the matrices are small enough that multithreaded BLAS is pure overhead, and five
concurrent runners × 4 threads put 20 threads on 8 cores with lock contention *inside* each
BLAS call. All workers were instructed to cap threads to 1.

**Why this is registered rather than just done.** BLAS thread count changes the **order of
floating-point reductions**, and this project's entire fidelity regime is **exact equality**.
`results/k1-replay-gate.json` records `worst_abs_delta: 0.0, gate: "exact"` on 500 rows — but
**nothing in the repository records the thread count under which that was measured**, on any
run, ever.

**Registered check, and it is not a formality.** Every worker must re-verify its |Δ| = 0 gate
after capping threads. **If exactness breaks under thread-capping, that is a finding to
report, not a tolerance to raise and not a reason to quietly revert to 4 threads.** It would
mean every gate in this project is contingent on an environment variable nobody wrote down —
which is the `e2-grid.json` lesson (a gate comparing a regeneration against an untracked
file can only report that a clone agrees with itself) in a new costume.

**If exactness holds**, the thread count should be recorded in every `provenance` block from
now on, and that is the cheap permanent fix.

---

## 📌 EXPLORATORY E7 · **`doe`'s regret advantage is mostly an IDENTIFICATION effect, and that is why it needs both a terminal rule and a noise level.** POST-HOC — labelled as such.

**Status: POST-HOC decomposition of committed data. NOT registered before it was computed, and
therefore NOT confirmatory.** It is written here so that the confirmatory version can be
registered before anything re-runs. Source: `results/q57-search-vs-id.json` (200 rows,
d ∈ {6,8} × σ_rel ∈ {0.25, 0.10}, 3 arms), `results/e2-grid.json`, `results/e2-doe-d8.json`.

**Provenance of the question.** P3 reported (D37) that `doe`'s regret advantage is significant
and beyond SESOI at **(6, 0.25) only**, with the sign flipping at both σ=0.10 cells. Asking
*which half of regret moves* is what produced this.

**Step 1 — `doe` is the arm that benefits LEAST from less noise.** Mean regret change,
σ_rel 0.25 → 0.10:

| d | qlognei | qlogei | coord | random | sobol | lhs | **doe** |
|---|---|---|---|---|---|---|---|
| 6 | −0.0724 | −0.0679 | −0.0539 | −0.0523 | −0.0514 | −0.0243 | **−0.0066** |
| 8 | −0.0256 | −0.0275 | −0.0873 | −0.0440 | −0.0836 | −0.0367 | **−0.0015** |

So the sign flip is **not `doe` degrading. It is every other arm improving while `doe` stands
still.**

**Step 2 — decompose `regret = oracle-best (SEARCH) + identification gap`.** `doe` − `qlognei`,
positive favours `doe`:

| cell | total | = search | + identification |
|---|---|---|---|
| **d=6, σ=0.25** | **+0.0574** | +0.0237 | **+0.0337 (59%)** |
| d=6, σ=0.10 | −0.0084 | −0.0109 | +0.0025 |
| d=8, σ=0.25 | +0.0142 | +0.0111 | +0.0031 |
| d=8, σ=0.10 | −0.0100 | +0.0064 | −0.0164 |

**Step 3 — the asymmetry that explains it.** Identification gap per arm, and its response to
less noise:

| d | arm | σ=0.25 | σ=0.10 | Δ |
|---|---|---|---|---|
| 6 | **doe** | 0.0361 | 0.0348 | **−0.0013** |
| 6 | qlogei | 0.0797 | 0.0378 | −0.0420 |
| 6 | qlognei | 0.0698 | 0.0373 | −0.0325 |
| 8 | **doe** | 0.0388 | 0.0448 | **+0.0060** |
| 8 | qlogei | 0.0545 | 0.0319 | −0.0226 |
| 8 | qlognei | 0.0419 | 0.0284 | −0.0135 |

**`doe`'s identification gap is noise-invariant. Every BO arm's roughly halves.**

**Mechanism, stated as a hypothesis and not a result.** BO's rule A takes the **argmax of 48
noisy readings**, so its identification gap carries a winner's-curse term that scales with σ.
`doe`'s rule A is a **confirmation well at a CCD-fitted optimum** — a single reading at one
point, with no maximisation over noise — so its gap does not scale. `doe`'s advantage at the
primary cell is therefore substantially *the curse it declines to pay*, not a better design.

**Why this matters: three independent routes now give one mechanism.**
1. **D20** — the advantage inverts under **rule P**, a terminal rule that does not maximise over noisy readings.
2. **D37** — the advantage survives only at the **highest σ**, and flips at the lowest.
3. **E7** — **59% of it at the primary cell is identification**, and `doe`'s identification gap is the only one that does not shrink with σ.

None of the three was designed to test the others.

### Limits, stated because this is post-hoc

* **d=8 is NOT clean and must not be quoted as a percentage.** Its totals are small
  (+0.0142, −0.0100), so the identification share is computed on a near-zero denominator and
  reads 22% and 164%. **Report the per-arm gaps at d=8, never the decomposition percentages.**
* **The σ cells share noise draws** (E8 below), so the σ=0.25 → 0.10 comparison is paired far
  more tightly than independent replicates. This makes an observed *change* stronger evidence,
  but it means the effective n for a cross-σ static-arm comparison is **12–27 of 50**, not 50.
* **`doe`'s rule A is model-informed once**, at its confirmation well (already noted in D23),
  so "model vs no model" was never the right framing and is not the framing here.
* n = 50 only. **Amendment F1 requires the n = 25 version before any of this is quoted.**

### The confirmatory version, registered here BEFORE it runs

**Registered prediction:** if the mechanism is right, then re-scoring every arm under **rule P**
(posterior-mean argmax, no maximisation over noisy readings) should make the identification
gaps **converge across arms**, and `doe`'s residual advantage at (6, 0.25) should fall below
**SESOI 0.02**. Fix 1 already produced rule-P regret for ten arms at (6, 0.25) in
`results/fix1-terminal-rule.json`; the missing piece is oracle-best under rule P at both σ.

**Registered kill:** if `doe`'s advantage under rule P at (6, 0.25) **remains above SESOI**,
the identification mechanism does **not** explain it and E7 is withdrawn as an explanation,
keeping only its descriptive decomposition. **Output:** `results/e7-search-vs-id-rule-p.json`.

---

## 📌 E8 · **The σ_rel = 0.25 and σ_rel = 0.10 cells are NOT independent samples. Found by P3, verified independently.**

**Mechanism, verified to bitwise equality:** `BiphasicOracle` seeds on `seed` alone, never on
σ, and `numpy.random.Generator.normal(0, s)` is **bitwise** `s * standard_normal()` off the
same stream. Confirmed at n = 100,000 for both σ:

```
default_rng(7).normal(0, 0.25) == default_rng(7).standard_normal() * 0.25   -> True
default_rng(7).normal(0, 0.10) == default_rng(7).standard_normal() * 0.10   -> True
```

So for a given `(instance, seed)` the two σ cells are **one noise realisation at two
amplitudes**, sharing z-draws and additive η draws (σ_add fixed at 0.01 both times).

**One correction to P3's write-up, on an incidental point.** P3 stated the ratio is "2.5
exactly, elementwise". Measured: the ratio takes **2 distinct float64 values 1 ULP apart**, and
is exactly 2.5 in 73,639 of 100,000. **The substantive claim — shared standardised draws — is
exact; the "2.5 exactly" is a float-division artefact.** The finding is unaffected.

**Consequence, counted in committed columns and reproduced independently — all 14 counts match
P3's:**

| | doe | lhs | sobol | random | coord | qlogei | qlognei |
|---|---|---|---|---|---|---|---|
| d=6 | 34/50 | 38/50 | 32/50 | 30/50 | 15/50 | 0/50 | 0/50 |
| d=8 | 30/50 | 37/50 | 23/50 | 31/50 | 8/50 | 3/50 | 4/50 |

bitwise-identical regret between the two σ levels. The split is exactly what the mechanism
predicts: a **one-shot** arm's design is fixed, so σ can only move which well the noisy `Y`
nominates, and scaling the same z-draws rarely moves the argmax. **Adaptive arms diverge at
the first acquisition and land at 0–4 of 50.**

**What this does and does not damage.**
* It does **not** invalidate anything committed. Every campaign is a legitimate draw and every
  gate still holds at |Δ| = 0.
* **Any analysis treating σ=0.25 and σ=0.10 as independent replicates is wrong** — pooling
  across σ, or any unpaired cross-σ contrast. *(Checked: the technical report does not pool
  across σ. F4's withdrawn pooling was across `tau_frac`, a different axis.)*
* **Effective n for a cross-σ STATIC-arm comparison is 12–27 of 50**, not 50: distinct values
  are `lhs` d=6 **12/50**, `doe` d=6 **16/50**, `sobol` d=8 **27/50**, `qlogei` d=6 **50/50**.
* **For D37 it cuts in our favour**, and P3 is right to say so: shared draws make the cells
  *more alike* than independent sampling would, so a ranking change observed across σ **cannot**
  be explained as independent sampling noise. **But note the asymmetry** — the `doe − qlognei`
  contrast pairs an arm that is 34/50 σ-correlated against one that is 0/50, so the
  correlation is **not uniform across the difference** and no single effective-n applies to it.

**This is a property to REPORT, not to repair.** Re-seeding per σ would invalidate every
committed campaign in the project. `torch_oracle.py` stays on the do-not-modify list.

---

## 📌 ERRATUM 3 to Amendment F / P2 · **I inverted the γ-ladder difficulty ordering. P2 found it; verified from committed data.**

**What P2's registration says (mine):** *"γ=0.99 tightens `tau_max` from 1.0000 to 0.4184 and
there is no reason the certificate must survive that."* — framing **γ=0.99 as the hard corner**.

**What is true.** γ enters τ **multiplicatively**: `tau = tau_frac × tau_max(γ, σ_rel)`, and
`tau_max` *decreases* in γ. So a **higher** γ buys a **lower absolute τ**, a **larger** true
superlevel set, and **easier** containment. Measured on the committed `lhs` rows
(`k6-designspace-spread.json`, mean `true_frac_above_tau` over 50 campaigns):

| γ | τ_frac | τ | prevalence |
|---|---|---|---|
| **0.99** | 0.60 | 0.2510 | **0.99916** ← I called this the hard corner |
| 0.99 | 0.95 | 0.3975 | 0.98090 |
| 0.95 | 0.60 | 0.3533 | 0.99131 |
| 0.50 | 0.60 | 0.6000 | 0.73569 |
| 0.50 | 0.85 | 0.8500 | 0.06844 |
| **0.50** | **0.95** | 0.9500 | **0.00294** ← the actual hard corner |

**I conflated "a higher assurance requirement" with "a harder threshold."** Higher γ *does*
demand more assurance — and it discharges that demand by lowering the threshold it is willing
to certify. The certificate is hardest at **γ=0.50, τ_frac=0.95**, where the true set is
**59 grid points of 20,000**.

**What changes and what does not.**
* **The registered kill is UNCHANGED** — every cell still runs and every below-nominal
  containment is still reported as a failure. **The kill was correctly specified; only my
  expectation about where it would bite was wrong.**
* **`true_frac_above_tau` must travel beside every containment fraction** — P2's call, adopted
  programme-wide. A containment number read without its prevalence **inverts the reading**:
  0.99 containment where the true set covers 99.9% of the box is nearly vacuous, and 0.94
  where it covers 0.29% is a strong result.

**This sharpens Amendment F2a rather than complicating it.** AUC is unreliable at **both** ends
of this ladder, mirrored: at γ=0.99 τ_frac=0.60 the **negative** class is ~17 grid points of
20,000; at γ=0.50 τ_frac=0.95 the **positive** class is ~59. Davis & Goadrich cuts both ways.
The **type I / type II error volumes are well-defined across the entire ladder**, including
where `D_est` is empty. **The metric correction and the ladder correction were found
independently and point the same way.**

---

## ✅ ERRATUM 2 — **CLOSED. The `|Δ| = 0` gates are NOT thread-contingent.**

Erratum 2 registered the open question: *"nothing in this repository records the thread count
under which any |Δ| = 0 gate was measured."* **Two workers have now answered it independently,
and the answer is no.**

* **P7:** `torch.set_num_threads(1)` reproduces regret **bitwise (Δ = 0.000e+00)** on `qlogei`
  and `qlognei` against their committed columns.
* **P2, and this is the strong one:** its `plate1_only` gate was extended from regret alone to
  **all 20 numeric K6 columns** (`sup_err`, `grid_r2`, `iou_pred`, `fi_pred`, `box_vol_pred`,
  `auc_pred`, …) at **all 24 (γ, τ_frac) cells** — **every column exactly 0.0**, measured
  under `set_num_threads(1)` **and** after deliberately burning the global torch RNG by
  fitting an unrelated GP first.

**So the whole scoring path, not just regret, is invariant to thread count and to global RNG
position.** Per Erratum 2's registered remedy, **thread count goes into every `provenance`
block from now on** — cheap, and now known to be documentation rather than a control variable.

**A provenance defect found on the way, worth recording because it is exactly the class this
project keeps finding.** `versionb.json`'s own `plate1_only` regret column is **not** bitwise
the committed `lhs` column — it differs by **3.33e-16**, because `run_versionb.py` scores it
with a single `scored_curve` call while `replay.regenerate` reproduces `static_curve`'s
20-ordering arithmetic. **Two committed files disagree with each other at 3e-16.** P2 built
against the gateable one. This is the `static_curve` float-mean artefact for the **third**
time; the rule of matching arithmetic rather than widening tolerance has now caught it in
three independent places.

---

## 📌 ERRATUM 4 · **The audit's `doe` column shifts are ONE CELL, not pooled — and the wrong gate column is mostly right, which is what makes it dangerous.**

**Found by the B4 worker while building the family gate. Verified independently; both number
sets reproduce exactly from `results/d20-rescore.json` × `results/q42-families.json`, 400
shared keys.**

`docs/COVERAGE-MATRIX.md` §4 B4 warns that `q42-families.json · doe_a` is the **pre-D20**
column and the wrong gate target, quoting *"ackley 0.0000 → 0.0123, hartmann6 0.5444 →
0.5623, levy 0.0040 → 0.0392, rosenbrock 0.0003 → 0.0328"*. **Those are the d=6, σ=0.25 cell
only.** Pooled over all four cells:

| family | d=6 σ=0.25 (as quoted) | **POOLED, all cells** | equal rows (pooled) |
|---|---|---|---|
| ackley | 0.0000 → 0.0123 | **0.0000 → 0.0070** | **92/100** |
| hartmann6 | 0.5444 → 0.5623 | **0.5917 → 0.5994** | **75/100** |
| levy | 0.0040 → 0.0392 | **0.0040 → 0.0337** | 38/100 |
| rosenbrock | 0.0003 → 0.0328 | **0.0004 → 0.0245** | 27/100 |

**Consequence for the write-up:** *"the pre-D20 column flatters DoE"* is **much stronger on
levy and rosenbrock than on hartmann6.** Only levy and rosenbrock clear SESOI 0.02 at every
cell; hartmann6's shift is ~0.007 everywhere, well below it. The claim must be stated per
family, not as a blanket.

### The dangerous part: **the wrong column is mostly RIGHT**

At d=6 σ=0.25 the two columns are **identical on 22 of 25 ackley rows** and **15 of 25
hartmann6 rows**. **A spot-check on seeds 0–2 of either family would not notice the wrong gate
target.** A gate that silently uses the pre-D20 column would pass on most rows and be wrong.

**The B4 worker's test design is the correct response and is registered as the standard for
this class of check:** assert **both halves** — the right column reproduces exactly, *and* the
wrong one is **shown to differ on the rows where it differs** — with a **count floor** so the
test cannot silently degrade into one that no longer distinguishes them. **A test that only
asserts the positive half would pass against the wrong column on 88% of ackley rows.**

### Ackley's 92/100 equality is B3's mechanism appearing in the gate data

`doe`'s two columns coincide on ackley because **its optimum is the exact box centre and the
CCD visits it**, so oracle-best and rule A are the same point. That is blocker B3's objection
— the one that justified Decision 3's *"ackley is IN but as a declared sensitivity, never a
headline"* — **showing up independently in data collected for an unrelated purpose.**
Decision 3 is confirmed by evidence it was not derived from.

### Decision on the 20-ordering mean off hill: **LEAVE IT UNBRANCHED.** Registered.

`replay`'s `N_ORDERINGS = 20` mean reproduces `run_e2.static_curve`'s arithmetic. Off hill it
moves a spread-arm regret by a few ULP, **and there is no committed family column for
`lhs`/`sobol`/`random` at all** — they are ungatable off hill by §4 B4. So branching it would
introduce **a second scoring definition inside one function to buy nothing measurable**. Under
the standing rule — *a second definition of a committed quantity is worse than a slow or
slightly-off one* — it stays unbranched, and this paragraph is the record of that being a
decision rather than an oversight.

### API note carried for P6

`CampaignRecord` now carries `family: str = "hill"`. **Off hill, `instance` repeats the family
label**, so a consumer reading only `instance` cannot distinguish a family from a landscape id
— **read `rec.family`.** Passing a hill `instance_id` alongside `family=` raises `ValueError`
rather than being silently ignored.

---

## 📌 ERRATUM 5 · **Amendment F2a's `nan` claim is wrong for IoU, which weakens my own justification. And thread-capping IS a lever — I retracted a correct result.**

### 5a. The two `nan` conditions are different. F2a overstated its case.

**Amendment F2a says:** *"when `D_est` is empty, `fi_pred` and `iou_pred` are `nan` (0/0) — but
type I volume is **0** and type II volume is **the prevalence**, both exactly correct... the
error volumes are **defined precisely where AUC and IoU break**."*

**Wrong for IoU.** Found by the P7 worker, whose first test asserted `nan` there and failed:
* `fi` is `nan` whenever **`D_est`** is empty.
* `iou` is `nan` **only when the UNION is empty** — `D_est` *and* `D_true` both empty.
  **An empty `D_est` against a non-empty true set gives IoU = 0, not `nan`.**

**Consequence, stated against my own registration.** The error volumes are **still strictly
more defined than IoU** — both are well-defined when the union is empty, where IoU is `nan` —
but **the margin is much smaller than F2a claimed.** The "defined precisely where IoU breaks"
half of the argument is **retracted**; the AUC half is unaffected and was always the stronger
one (AUC is invariant to monotone transformation and cannot see that mean `grid_r2` is negative
for all eight arms).

**Required:** scorable-row counts must report **the two `nan` conditions separately**, never a
single combined "IoU/fi break here" figure, and the IoU margin is reported at whatever it
measures rather than at what I asserted.

### 5b. AUPRC inverts at high γ — the minority class becomes the NEGATIVE one.

Found by the P7 worker while implementing F2b. **At γ=0.99, τ_frac=0.60 about 16 of 20,000 grid
points are NEGATIVE**, so a standard positive-class AUPRC is **trivially ≈1 exactly where F2b
flags it as primary.**

**Registered convention, adopted programme-wide:** compute **`auprc_minority`** by scoring the
explicit complement, and carry the **AP baseline — the prevalence, not 0.5 —** on every row,
because average precision is **not comparable across cells** whose prevalence runs 0.0012 to
0.999.

**This is the same inversion as Erratum 3** and has the same cause: γ enters τ *multiplicatively*
through `tau_max`, which decreases in γ, so **high γ means a low absolute threshold and a huge
positive class.** Two workers hit it from different directions within an hour. It is the
strongest argument yet for the Erratum 3 rule that **`true_frac_above_tau` travels beside every
prevalence-sensitive number.**

### 5c. **Thread-capping IS a 3.6× lever. I retracted a correct measurement.**

Erratum 2 recorded my thread benchmark as confounded and retracted its 4.6× figure. **The
retraction was wrong.** Re-measured by P7, controlled, on the real workload:

```
qlogei, one campaign + 24-cell map re-score
  torch default threads   133.7 s
  threads capped to 1      37.2 s      -> 3.6x
```

**The mechanism, which is why three readings disagreed:** `torch.set_num_threads(1)` **in
Python is not sufficient.** Setting the variables via `os.environ` *inside* the process before
importing torch still gave **114 s** — BLAS reads `OMP_NUM_THREADS` **at library load**, so it
must be in the **shell environment before the interpreter starts.**

* My original benchmark used the shell prefix → 4.6×, **correct**.
* P7's first probe set them in-process, while its own uncapped smoke ran in the same directory
  → no gain, **confounded twice over**.
* I accepted P7's over my own → **retracted a correct result.**

**Registered form for every runner:**
```
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -u scripts/...
```

**Erratum 2's exactness conclusion is UNCHANGED and is now measured twice over**, at one thread
against columns produced at the torch default: P7 **144 rows × 11 committed K6 columns** at
worst |Δ| = 0.000e+00, and P2 **20 numeric columns × 24 cells**, all exactly 0.0. **Exactness is
not thread-contingent for this workload.** Thread count is recorded in every `provenance` block
as documentation, not as a control variable.

### 5d. Consolidation: `src/boec/calibration.py` is the canonical home.

`error_volumes` and `average_precision` were about to exist in **three** places — the F-analysis
script, `run_p7_murphy.py`, and `run_p3_cells.py` (where they are currently **undefined names**,
mid-edit). **`boec.calibration` is canonical**; the other two import it and the F-analysis copy
is deleted. **The gate against the committed `iou_pred` column moves with the function** — it is
what makes the derivation checkable rather than asserted, and it must not be lost in the move.

**Fourth invocation tonight of the same principle by four workers on four unrelated problems:**
*a second definition of a committed quantity is worse than a slow, slightly-off, or
inconveniently-located one.*

---

## 📌 ERRATUM 6 · **I committed the F4 defect inside the argument FOR F2. And F2a's decision rule FIRED.**

### 6a. 🔴 **"`grid_r2` is negative in 1200/1200 campaigns" — WRONG. It is 50 of 50, and the error is pseudo-replication.**

Amendment F2 argued for replacing AUC partly on this: *"`doe` is negative in **1200/1200**
campaigns, while the BO and spread arms are positive in 4%–24% of theirs."*

**`grid_r2` is a CAMPAIGN property.** Verified: every `doe` campaign has **exactly one
distinct `grid_r2` value** across its 24 (γ, τ_frac) rows. So 1,200 rows count **each of 50
campaigns 24 times.** The true figure is **50 of 50 campaigns.**

**This is precisely the defect Amendment F4 exists to fix** — treating repeated measurements
of one campaign as independent replicates — **committed by me, in the same document, inside
the supporting statistic for a different correction.** F4 withdrew a containment figure for
counting one campaign four times; F2 quoted a count that did it twenty-four times.

**Direction unaffected** — 50/50 is still *every* campaign, and the BO/spread arms are
negative in 76%–96% of theirs, consistent with the registered 4%–24% positive. **The
argument survives; the number was inflated 24×.** Corrected wherever quoted.

**Carrying the general rule:** any count over `k6-designspace.json` rows is a count over
**cells**, not campaigns, for every campaign-level column — `grid_r2`, `sup_err`, `regret`,
`n_active`. Only cell-level columns (`auc_*`, `brier_*`, `iou_*`, `fi_*`, `vol_*`,
`empty_*`, `tau`, `true_frac_above_tau`) may be counted row-wise.

### 6b. ✅ **F2a's registered decision rule FIRED. The error-volume ranking is now the reported one.**

Registered rule: *"if the arm ranking under type I / type II error volumes differs from the
ranking under AUC, the error-volume ranking is the reported one."*

**It is not a near-miss.** Spearman ρ against the AUC ordering: **+0.071** for type II and the
symmetric difference, **+0.214** for type I; per-cell median **+0.048**. **The two orderings
are close to unrelated.** Differ in **24 of 24** cells.

**Coverage, which is the other half of the case:** **6,000 of 6,000 rows scorable under error
volumes against 2,553 under `fi_pred`** — 57.5% of predictive regions are empty (63.4% on the
spread file). *(Per Erratum 5a this margin is against `fi_pred`, **not** IoU, which is 0 rather
than `nan` on those rows. The surviving half of the argument is the one used.)*

**`doe` is LAST of eight** on type II, symmetric difference, IoU and Brier.

**⚠️ Registered for the cross-family grid: type I volume read ALONE ranks silence first.** An
arm certifying the empty set scores **exactly 0** on type I. `doe` is 2nd on type I for that
reason and no other. **Azzimonti & Ginsbourger report both components; the symmetric difference
is the honest single scalar** and is what any single-number ranking must use.

**Degenerate cells are flagged, not ranked:** 6 of 24 (10 for type I) are ties because at
`tau_frac = 0.95` every region is empty in 100% of campaigns. There is no ordering to compare.

### 6c. Two corrections to what F2/F1 assumed

**`versionb.json` is worse off than recorded.** It lacks **all three** of `vol_pred`/`vol_latent`,
`fi_pred`/`fi_latent` **and** `true_frac_above_tau` — so its error volumes are **not** computable,
not merely awkward. Reported as a finding; **nothing imputed.**

**`n = 50` does NOT uniformly lower the Wilcoxon p.** **36 of 137** contrasts have a *lower* p at
**n = 25** — averaging seeds first removes within-landscape noise, which can make a signed-rank
test *more* powerful. The bootstrap and the Wilcoxon move independently; the registered 2×2 of
disagreements is populated (126 agree at both units, 7 disagree at n=50 only, 1 at n=25 only,
3 at both). **My F1 text asserted a one-directional effect and that is wrong too.**

**One caveat REMOVED, in our favour:** `doe` is scored on the **full 6-D grid** in K6 — prevalence
is identical across all eight arms in all 1,200 cells — so **the K6 error-volume ranking is
like-for-like.** B3's subspace evaluation is K6b-only. The §6.12 mixed-dimension caveat applies
only to `box_vol_pred`, which no ranking uses.

### 6d. Two judgement calls, both APPROVED

**`seed_average_policy`** — drop the `(instance, seed)` pair if either arm is `nan`, *exactly as
n=50 does*, **then** average surviving seeds, **then** pair instances. So n=25 runs on a strict
subset of what n=50 admits and **the units differ only in aggregation.** Correct, and recorded in
the output rather than left implicit. **Approved.**

**CE-set error volumes** — `k6b-conservative.json` carries `ce_false_in_*`, `ce_vol_*` and
`true_frac_above`, so the error volumes are derivable for the **conservative-estimate sets** too,
at zero compute. Outside F2a's registered file list, correctly not computed unasked.
**APPROVED as an addition** — it extends the primary metric to the object the SPADE certificate
is actually about. New file, not an overwrite.

---

## 📌 ERRATUM 7 · **I closed Erratum 2 too early. And the thread speedup is workload-dependent, which reconciles three disagreeing measurements.**

### 7a. 🔴 **Erratum 2 is PARTIALLY RE-OPENED. `k1-replay-gate.json` is still unverified.**

I closed Erratum 2 on P7's and P2's evidence. The B4 worker identified what that misses, and it
is right:

* **Its own family evidence has threads=1 as the CONTROL, not the treatment.** The committed
  family columns were themselves produced at one thread — `run_q42_families.py:60,68`,
  `rescore_d20.py:33,39`, `run_q59_hartmann_no_screen.py:70,76` all set `OMP_NUM_THREADS=1`
  **and** `torch.set_num_threads(1)`. Its new information is that **4 threads also reproduces**
  (worst |Δ| = 0.000000e+00 at both settings, six gates, including two BO arms that fit a GP by
  marginal likelihood and run multi-start L-BFGS-B over an MC acquisition). Still a real
  cross-thread result — just in the opposite direction from how I read it.
* **`results/k1-replay-gate.json`'s 500 Hill rows remain unverified.** Measured at an
  **unrecorded** thread count, and routed through `BiphasicOracle` rather than `TorchEvaluator`
  over `UnitScaled` — **so none of the family evidence implies it.**

**Status: 🟡 OPEN for K1's 500 Hill rows; ✅ CLOSED for the K6 scoring path** (P7: 144 rows × 11
committed columns; P2: 20 numeric columns × 24 cells) **and for the family gates** (both thread
settings, exact). **Unassigned — every worker is committed.**

### 7b. **The thread speedup is workload-dependent. Three measurements, all correct.**

| measurement | scope | speedup |
|---|---|---|
| my microbenchmark | isolated GP fit + 2,048-row posterior | **4.6×** |
| P7 | one campaign **+ 24-cell map re-score** | **3.6×** |
| B4 worker | **campaign regeneration only** | **1.0–1.55×** (confounded by load) |

**The reconciliation is the B4 worker's and it is obviously right once stated: a campaign spends
much of its time outside BLAS**, so the isolated fit+posterior microbenchmark is an **upper
bound**, close to right for map-heavy work and much too optimistic for regeneration-heavy work.

**Registered statement, replacing both of my earlier ones:** *thread-capping is worth ~3.6× on
map-scoring work and ~1.0–1.55× on campaign regeneration.* Keep the cap everywhere — it is free
and proven bitwise safe — but **do not price a regeneration-heavy job on the microbenchmark.**
This is my **third** position on this question; the first two were each right about one workload
and wrong to generalise.

### 7c. ⭐ **A 4× exact reduction in the Vorob'ev scan. Adopted, gate-clean.**

`alpha_star` scans `torch.linspace(0, 1, 64)`; `conservative_estimate` scans
`torch.linspace(1, 0, 64)`. **The two are elementwise equal** (`torch.equal` on the flipped
tensor is True — measured, not assumed). So **one `alpha_star` plus three
`conservative_estimate` calls per cell walk the same 64 Vorob'ev quantiles of the same coverage
function four times.** Counted live: **252 calls over 63 distinct masks** at γ=0.50; 256 over 19
at γ=0.99 where the quantiles collapse.

**The fix does not reimplement either estimator** — it memoises `containment_probability` within
**one cell**, keyed on `(theta, the mask's exact bytes)`. Every distinct call still reaches the
real `boec.vorobev` function. **Worst |Δ| over 1,032 numeric column-comparisons: 0.000e+00.**
Campaign cost **108.9 s → 30.4 s**; that worker's task went from ~17 CPU-h to **~1.7**.

**Applies to every caller of both estimators on the same draws and threshold** — K6b's
conservative run and P4b's α\* regression are paying the identical 4×. Relayed to both owners as
their call, not an instruction.

### 7d. **F2a does NOT rescue ackley under `tau_frac`. "Well-defined" ≠ "a comparison".**

The B4 worker's refinement, adopted in its words. Under `tau_frac` on ackley,
`true_frac_above_tau = 0.00000` (measured, both d). Feeding that through F2a's formulas:

* `type_II_vol = 0 − intersect = 0` for **every arm, identically** — it cannot discriminate at all.
* `type_I_vol = vol_pred · fi_pred = vol_pred` whenever `D_est` is non-empty — it collapses to
  *"how much did you certify"*, **scoring an arm that certifies nothing as perfect.**

**So F2a makes the ackley degeneracy LEGIBLE rather than `nan` — a real gain in diagnosis and no
gain at all in discrimination.** Under `tau_q`, `true_frac_above_tau = p` exactly (worst |Δ| over
232 rows = 0.000e+00), so `type_II_vol = p − intersect` has real range and both components
discriminate. **`tau_q` remains the fix; F2a does not substitute for it.**

**This generalises past ackley and is registered for the cross-family grid:** *type I volume read
alone ranks silence first.* An arm certifying the empty set scores exactly 0. **The symmetric
difference is the only honest single scalar**, and any table reporting type I alone must say what
it is rewarding.

### 7e. `results/p5-tau-quantile.json` rewritten — a justified exception, done with proof.

`achieved_prevalence` → **`true_frac_above_tau`**, matching F2a's formula exactly. One key, not
two: two keys holding the same number is the ambiguity F2a asked to remove. It stays **measured**,
never copied from `p` — *a file storing the nominal value would make `type_II_vol` wrong by
exactly the gate error it exists to detect.*

**This rewrote a JSON committed an hour earlier, which the standing rule forbids.** It was done
with proof rather than trust: committed file copied aside, regenerated, diffed — **all 232 rows
bit-identical** on every other field, `true_frac_above_tau` bit-identical to the old
`achieved_prevalence`, calibration block unchanged, only the key name and a config note differing.
**That is what a justified exception to a standing rule has to look like**, and it is recorded
here so the exception does not become a precedent for unproven ones.

---

## 📌 DECLARED SCOPE REDUCTION 1 · **P1 PASS 3 is DEFERRED.** Registered with its reason, per the standing rule.

**The standing rule:** a scope reduction is **declared, registered and logged with its reason —
never absorbed into a smaller run that reads like the full one.** This is the first reduction
taken in Phases 2–4 and it is recorded in that form.

**What is deferred.** P1's PASS 3 gates the **100 σ_rel = 0.10 kernel campaigns** against
`results/q30-additive.json`. Cost ~0.5–2 CPU-h.

**What is NOT deferred, and must not be:** **Step A stays whole**, all four arm × σ blocks. Its
σ=0.10 half produces the comparator column that **P3's (6, 0.10) cell is currently blocked on** —
those `qlogei-add`/`qlogei-addonly` rows carry `gated: false` precisely because
`q30-additive.json` does not exist yet. Trimming Step A would silently strand a second worker.

**Why the deferral is sound, in two parts:**
1. **The σ=0.10 campaigns carry no design-space rows anywhere**, so they are **outside the
   registered kill condition**, which rests on the **2,800 re-scored rows** at d=6, σ=0.25. The
   kill condition is untouched.
2. **P3's (6, 0.10) cell performs the equivalent comparison against the same committed column,
   through an independent code path** — `replay.regenerate` against `run_q30_additive.py`. That
   is **stronger** evidence than P1 gating its own regeneration against a column P1 produced.
   **The deferral relocates the check to a better place rather than losing it.**

**Raised by the P1 worker, which flagged it and explicitly declined to cut it unilaterally.**
That was the correct escalation; the decision is mine.

**Reinstatement condition:** if P3's (6, 0.10) cell fails or is abandoned, PASS 3 comes back —
because then nothing gates those campaigns.

---

## 📌 ERRATUM 7a — UPDATE · **Effectively closed. The residual is named and narrow.**

Erratum 7a re-opened the thread-exactness question for `results/k1-replay-gate.json`'s 500 rows,
because they were measured at an **unrecorded** thread count and route through **`BiphasicOracle`**
— a path the family evidence did not cover.

**The P1 worker's measurement covers that path.** The kernel arms are **hill**, so
`replay.regenerate` routes them through `instance_by_id` → `BiphasicOracle`, **the same oracle
K1 uses**. At 1 vs 4 torch threads it measured `qlogei-add` regret and **all 24 K6 rows × 20
metric columns identical**, on **both** the deterministic `doe` path **and** the multi-start
L-BFGS-B path the kernel arms use — which is exactly where it could have broken.

**Residual, stated narrowly rather than waved away:** K1's specific **d=8** and **σ=0.10** rows
were not themselves re-run. **No mechanism is known by which thread count would break at one
(d, σ) cell and not another**, and **four workers have now measured exactness across a thread
change on four different code paths** — family gates at both settings, the K6 scoring path
(11 columns × 144 rows), the full K6 column set (20 columns × 24 cells), and now
hill + `BiphasicOracle` + multi-start L-BFGS-B.

**Status: ✅ effectively closed.** Thread count is recorded in every `provenance` block as
documentation. **This erratum has now had three positions and this is the last one** — the
earlier flips were: closed on partial evidence, re-opened on a correct objection, and now closed
on evidence that meets the objection.

---

## 📌 FIRST DIRECT EVIDENCE ON P1's KILL CONDITION — recorded before the verdict exists

Regenerating `qlogei-add` on instance `033466197eba3ddb`, seed 0, gives regret
**`0.10179313939531909`** — **bit-identical to the committed `k6-designspace.json` row.**

**This is the first direct evidence that the committed kernel-arm rows reproduce**, and it is
recorded here *with its campaign key* so it is citable independently of P1's full verdict. It is
**one campaign of fifty per arm** and does **not** discharge the kill condition, which requires
|Δ| = 0 on all 2,800 re-scored rows. Recorded now precisely so that a later VALIDATED verdict
cannot be mistaken for having been foreseen, and a later WITHDRAWN cannot be said to have had no
warning either way.

---

## 📌 AMENDMENT F1 — SUPPLEMENT · **F1's decision rule does not cover NULLS, and my statement about them was inverted.**

**Found by the P3 worker.** I wrote: *"not significant at n=50 is a strictly weaker statement
than not significant at n=25."* **That is backwards.** A non-detection is more informative from
the **higher-power** unit — failing to reject *despite* more power is stronger evidence of
absence.

**And F1 as registered genuinely does not cover the case.** Its rule is written entirely for
positive results (*significant at 50 and not at 25 → downgrade to n=25's verdict*). It says
**nothing** about which unit governs a null.

**The fix is not simply "n=50 governs nulls", because which unit has more power is measurable
and varies.** The P3 worker's own per-cell measurement:

| cell | ρ (within-instance, between seeds) | √(1+ρ) predicted | measured SE ratio |
|---|---|---|---|
| (6, 0.25) | **+0.192** | 1.092 | **1.097** |
| (6, 0.10) | **+0.199** | 1.095 | **1.098** |
| **(8, 0.25)** | **−0.168** | 0.912 | **0.724** |
| (8, 0.10) | +0.181 | 1.087 | 0.976 |

**At (8, 0.25) ρ is NEGATIVE** — the two seeds of one landscape disagree *more* than two
landscapes do, so averaging cancels variance and **n=25 is the MORE precise unit there.**

**REGISTERED RULE, added to F1:** *for a null result, the load-bearing evidence is the
non-detection from whichever unit is more powerful **at that cell**, determined by the measured
ρ — not by a fixed preference for either unit. Report ρ beside any null that is being leaned on.*

### And "√2" is dead as a description of this data — it is ~9%, and my registration presented an upper bound as a typical value.

√2 is the **ρ = 1 limit** — it holds only if the two seeds carry **no independent information at
all.** Predicted-vs-measured agrees to within **0.005** at both d=6 cells, so the real cost of
the conservative unit here is **about 9%, not 41%.** That is why **no verdict moved.**

In the P3 worker's words, recorded verbatim because it is the sharpest statement of the error:
*"anyone re-deriving a power calculation from it would be out by a factor of four in variance."*

This is the **per-cell mechanism** behind the F-analysis worker's aggregate median ICC of
**−0.0231** over 137 contrasts. Two workers, different routes, same conclusion. **F1's rule —
run both, n=25 governs a positive — is unaffected and still right.**

---

## 📌 REGISTERED RULE · **A bar quoted at reduced precision is asserted at the precision of the underlying constant, never widened.**

**Second occurrence tonight, both from my own registrations:**
1. The P5 worker: my *"to within 0.0394"* is the d=6 measurement **0.039442** at 4 s.f., so a
   literal `<= 0.0394` fails by **4e-7**.
2. The P3 worker: my F2a validation bar *"2.220e-16"* is
   **`2.220446049250313e-16`** at 4 s.f. — which **is `numpy.finfo(float).eps` exactly.** A
   literal bar fails by **one ULP**.

**Both workers asserted the underlying constant rather than widening a decimal**, which is the
correct resolution and the same discipline as matching `static_curve`'s arithmetic instead of
raising a tolerance. **Registered as a standing rule**, because the failure mode is mine — I
keep quoting measured constants at display precision inside registrations that are then read as
literal bars.

---

## 📌 CONSOLIDATION FIX · **`error_volumes` had TWO library homes because of my assignment. `boec.calibration` stands.**

I gave `designspace.py` to the P3 worker and `calibration.py` to the P7 worker, then declared
**`boec.calibration` canonical** (Erratum 5d) without telling P3 — which had meanwhile added
`error_volumes()` to `designspace.py`. **My error, not theirs.**

**Resolution: `boec.calibration` stands** — P7 has already deleted its private copy and the
F-analysis worker is rewiring to it, so moving it now would rewire two consumers instead of one.
**P3 imports and deletes its copy.**

**But P3's GATE survives and replaces the incumbent:** it gates the arithmetic against the
**committed `iou_pred` column** rather than against another implementation. That is strictly
better and is now the test guarding the canonical function.

**Scorable rows confirmed independently by two workers: 6,000, not 2,553** — `iou_pred` is
committed as **`0.0`** on the 3,447 empty rows, not `nan` (Erratum 5a). 2,553 + 3,447 = 6,000,
zero negative type-II volumes. **Neither worker took my erroneous `nan` claim on trust.**

---

## 📌 MACHINE HAZARD · **This box is SIGKILLing pool workers. Checkpoint or lose the run.**

**Three runs died with `BrokenProcessPool`** — workers **not raising but being killed**, with
ten-odd concurrent phases each holding a 4-worker torch pool on a machine at **~60 MB free RAM**.
**D23 lost 8 completed campaigns; P4b lost its first.**

**Any long `ProcessPoolExecutor` job without disk checkpointing will lose the whole run and may
not notice why.** The pattern now in use: append every finished campaign to a checkpoint, re-read
it on restart, and **write the result JSON once, whole, at the end** — so a half-finished run can
never be mistaken for a finished one.

**Second hazard, easy to re-introduce off the beaten path:** a D23 draft evaluated a *pinned*
screen through `model.posterior` in **one call** — the 100.6 s / 3.2 GB joint-covariance case
`designspace.gp_adapter` exists to prevent. **Under memory pressure it does not fail, it
starves:** 35 minutes of uninterruptible wait for 1:47 of CPU. **Any new grid variant must route
through the chunked adapter**, not just the grid copied from an existing runner.

---

## 📌 ERRATUM 8 · **I relayed a 4× saving without checking whose cost profile it fitted. And COVERAGE-MATRIX §5's scoring costs are understated by 10–30×.**

### 8a. The Vorob'ev memoisation is profile-dependent. I propagated it as if it were not.

P2 measured the memoisation at **108.9 s → 30.4 s per campaign** and I relayed it to P1, P3 and
P4-D23 as a saving they were "paying". **P1 measured its own profile instead of taking mine:**

```
doe regenerate     0.68 s
K6  score         19.91 s
K6b score         25.40 s     <- the only part memoisation touches
                              -> 5.2% of a 488.5 s kernel campaign
```

**P1's campaigns are regeneration-dominated (~464 s of 488.5 s); P2's are scoring-dominated.**
A perfect 4× on K6b returns **~49 min of ~53,700 s — about 5.5% of Step B**, not 4×. **I was
reasoning from P2's cost profile and generalising it to three workers whose profiles I had not
checked.**

**P1's decline is ACCEPTED, and its three reasons are the right ones**, in its own priority order:
1. Catching the calls that matter would require **patching `boec.vorobev.containment_probability`
   from a runner** — a shared module — and every mechanism in that runner has had to pay for
   itself against the risk of manufacturing a **false WITHDRAWN**, which the registration says is
   *not repaired by re-running*. **5.5% does not clear that bar.**
2. **P4b is in flight on `alpha_star` specifically.** Patching underneath it is a collision.
3. *"My controls would catch a broken memoisation, but 'the safety net would catch it' is a
   reason the risk is survivable, not a reason to take it."* — **that sentence is the standard
   and is registered as such.**

**Correction issued to P3 and P4-D23: measure your own profile before adopting.** The saving is
real where scoring dominates and near-irrelevant where regeneration does.

### 8b. `COVERAGE-MATRIX.md` §5's per-campaign scoring costs are a FLOOR, not an estimate.

| operation | §5 says | measured under contention | ratio |
|---|---|---|---|
| K6 scoring, 24 cells on the 20k grid | **2.0 s** | **19.91 s** | ~10× |
| K6b scoring, 2k × 512 draws × 4 τ | **0.8 s** | **25.40 s** | **~30×** |

**K6b is more expensive than K6, not a third of it.** The likely cause is that `joint_draws`'
2000×2000 Cholesky is **memory-bandwidth-bound**, which is the worst thing to be at 59 MB free
RAM. §5's figures were taken on an uncontended machine.

**Registered:** every cost in `COVERAGE-MATRIX.md` §5 is an **uncontended floor**. Any plan
priced from it on a loaded machine is optimistic by up to 30×, and the P1/P3/P6 wall-clock
projections that overran were overrunning this, not a mis-estimate of the work.

### 8c. 🔴 **Erratum 7a's closure was over-credited. P1 corrected its own evidence downward.**

I recorded P1's thread test as covering the `BiphasicOracle` path and closed Erratum 7a partly on
it. **P1 has corrected me: it set the env vars via `os.environ` INSIDE the process before
importing torch** — which, by the mechanism in my own un-retraction (Erratum 5c), is **too late
for BLAS.** So it varied **torch's intra-op pool** (`torch.get_num_threads()` did report 1 vs 4)
but **probably not the BLAS thread count.**

**Revised weighting, stated accurately:**
* **Load-bearing: P7's measurement** — recomputing at shell-capped threads against columns
  produced **uncapped**. That is a genuine BLAS thread variation. 144 rows × 11 committed K6
  columns at |Δ| = 0.000e+00.
* **Corroborating, not independent:** P1's (intra-op pool only), P2's and B4's (whose `1` was the
  control, since the committed columns were themselves produced at one thread).

**Status: 🟡 7a closes on ONE strong measurement plus corroboration, not on "four workers, four
paths" as I wrote.** That is still enough to proceed — no mechanism is known by which reduction
order would differ at one cell and not another, and every measurement points the same way — but
**the record now says one, not four.**

**P1 volunteered this correction against its own earlier claim, unprompted, when nothing turned
on it.** Recorded because that is the behaviour that makes the rest of its reporting credible.

---

## 📌 REGISTRATION DECISION 2 · **`tau_q` equalises prevalence but NOT certifiability. The P6 headline is the γ=0.50 column, and that column is clean BY CONSTRUCTION.**

**Raised by the P6 worker before any compute, which is why it is a registration question and not a
retraction.**

**The mechanism.** Under `tau_frac`, `τ = tau_frac · tau_max(γ)` — so τ shrank *with* γ and could
never exceed the predictive ceiling. Under `tau_q`, **τ is fixed by prevalence while `tau_max`
still falls with γ.** So τ can now sit **above** the ceiling, and `D_γ` is empty for a reason that
has nothing to do with the design. **This is §2.4's defect relocated from the threshold to the
ceiling.**

**Measured over the full registered P6 grid** (4 families × 2 d × 4 p × 6 γ × 2 σ = 384 cells):

| family | cells above ceiling | | γ (σ=0.25) | cells above ceiling |
|---|---|---|---|---|
| ackley | **0 / 96 (0.0%)** | | **0.50** | **0 / 32** |
| hartmann6 | 2 / 96 (2.1%) | | 0.70 | 9 / 32 |
| levy | 48 / 96 (50.0%) | | 0.80 | 12 / 32 |
| rosenbrock | **61 / 96 (63.5%)** | | 0.90 | 14 / 32 |
| **total** | **111 / 384 (28.9%)** | | 0.95 | 16 / 32 |
| | | | 0.99 | 18 / 32 |

**The ordering — ackley 0% → hartmann6 2% → levy 50% → rosenbrock 64% — is the ordering of the
families' grid ranges.**

### The decision

**1. The P6 HEADLINE is the γ = 0.50 column, at every p.** Verified structural rather than
fortunate: `z_{0.50} = 0`, so `tau_max(0.50, σ) = mu_max = 1.0` **exactly**, and `tau_q ≤ 1.0`
because `UnitScaled` puts every family's optimum at 1. **Max `tau_q` anywhere in the registered
grid is 0.98631.** So **γ=0.50 can never cross the ceiling on any family, at any p, at any σ — by
construction.** The clean cross-family column is *guaranteed*, not discovered.

**2. Higher γ is reported PER FAMILY and NEVER POOLED**, with `tau_above_ceiling` and `tau_max` on
every row. A cross-family table at fixed (p, γ) above γ=0.50 compares *"ackley, certifiable"*
against *"rosenbrock, empty by noise floor"* — not a comparison.

**3. 🔴 DO NOT re-register `p` per γ.** That was the alternative offered and it is **rejected**:
choosing p as a function of γ to keep τ under the ceiling **re-introduces exactly the τ–γ coupling
that `tau_q` exists to remove**, and destroys the equal-prevalence property that is its entire
purpose. **The fix for §2.4 must not be undone to tidy its successor.**

**4. ⭐ The ceiling-crossing census is promoted to a REGISTERED SECONDARY RESULT, not an artefact
to route around.** It measures **what fraction of each family's response range is certifiable at a
given assurance** — a genuine design-space property, ordered by grid range, and one this project
has never reported. `tau_above_ceiling` is a finding in its own right and belongs in the write-up
with the census table, not in a caveat.

**5. Noted, and it bites the primary family hardest at the first rung:** at γ=0.70, σ=0.25, **hill
has 50 cells above the ceiling** — more than any external family. **The asymmetry is not a
property of "external families" and must not be described as one.**

### Two approvals

**The single `--limit 1 --arms doe,lhs` smoke to a scratch path, then deleted, was correct and
inside the hold.** *"A binary that has never executed its main path is not ready"* is right, and it
caught the Erratum 5a distinction on real data — `fi_pred` `nan`, `iou_pred` **`0.0` not `nan`**,
`type_I_vol` 0.0, `type_II_vol` exactly the prevalence.

**The per-family count floor on the `distinguishes` gate is a better design than the one
registered.** Its reasoning — *3/25 on ackley against 19/25 on rosenbrock means a pooled floor is
satisfied by rosenbrock alone and vacuous exactly where the risk is highest* — is the D50 lesson
applied before being told. **Adopted as the standard for every count-floor gate in the programme.**

### One more self-correction in the chain

The P6 worker **withdrew its own timing paragraph** (`33bf44a`): its probe set `OMP_NUM_THREADS`
via `os.environ` in-process — the pattern Erratum 5c identifies as **not capping BLAS** — so both
its arms ran the same configuration, and its "no speedup" reading **contributed to my withdrawing
a correct 4.6×.** Its exactness result is unaffected and stands.

**That is the third worker to correct its own claim against its own interest in this thread**
(P7 on the thread retraction, P1 on Erratum 7a, now this). **The record is being repaired faster
than it is being damaged**, which is the property that makes any of it citable.

---

## 📌 ERRATUM 9 · **I relayed working-tree linter output as "genuine NameErrors". They do not exist at HEAD. And the near-zero ICC does NOT generalise.**

### 9a. 🔴 The NameError alarms were false. I raised them to two workers as verified.

I told the F-analysis worker that `PRIMARY_GAMMA`, `PRIMARY_TAU_FRAC`, `GAMMAS`, `TAU_FRACS` and
`spearmanr` were *"genuine NameErrors, not linter noise"*, and told the P4/D23 worker the same
about `K6_SPREAD`, `MATCHED_GAMMA` and `error_volumes`. **An AST undefined-name check over
`git show HEAD:` for both files returns `NONE`.** The F-analysis worker verified it four
independent ways — grep, AST, live-run of both `main()` functions with output redirected to
scratch, and a bit-for-bit diff against the committed JSONs — before reporting it.

**The cause:** the diagnostics fire on **working trees**, and **seven agents are editing
concurrently**. The flagged code was real and really was broken — the F-analysis worker's first
draft hardcoded `GAMMAS = (0.50, 0.90, 0.95, 0.99)` and silently produced a **16-cell** headline
family instead of 24 — but it **never reached a commit.** I read a mid-edit snapshot as the state
of the repository.

**Registered rule: verify any static-analysis finding against `git show HEAD:<path>` before
relaying it.** In a seven-agent tree, a working-tree diagnostic is a **question**, not a finding.
The cost here was two workers' verification time, and one of them spent four passes on it.

*(Type-stub complaints like `Cannot access attribute "pvalue"` on `scipy.stats.wilcoxon` are
noise in both trees — the committed `analyse_k6.py` and `analyse_fix1.py` make the identical
call.)*

### 9b. 🔴 **"n=50 was not meaningfully anti-conservative" is TOO STRONG as a blanket. It is family-dependent, and the sign REVERSES.**

My D40 write-up quoted the **pooled** median (inflation 0.9884, ICC −0.0231) and concluded n=50
was not meaningfully anti-conservative. **Per family it splits, and the split is the mechanism
behind the three upgrades:**

| family | median ICC | median inflation | reading |
|---|---|---|---|
| **§5.3 HEADLINE 1 `lhs`−`doe` on AUC** | **+0.247** | **1.117** | **n=50 intervals ~12% TOO NARROW — genuinely anti-conservative** |
| §5.1 paired regret | +0.165 | 1.079 | n=50 slightly anti-conservative |
| §5.4 `doe`−`qlogei` on AUC | +0.058 | 1.029 | ~neutral |
| D20 rule-P reversal | −0.008 | 0.996 | neutral |
| §5.8 `alpha*` | −0.200 | 0.894 | **reversed** |
| §5.11.3 KILL 1 | −0.339 | 0.813 | **reversed** |
| §5.11.5 `versionb`−`plate1_only` | −0.404 | 0.772 | **reversed** |
| §5.11.4 Vorob'ev deviation | −0.468 | 0.728 | **reversed** |

**On the K6 AUC and regret contrasts n=50 genuinely WAS anti-conservative** — the headline
family's intervals were about **12% too narrow.** Real, and far short of 41%.

**On every `alpha*` and Version B family the sign REVERSES:** n=50's intervals were too *wide*,
and **n=25 is the MORE powerful unit there.**

**⚠️ That is the mechanism behind all three Holm upgrades — they sit in the two most negative
families.** So the upgrades are **a power effect of averaging seeds, not new evidence.** That
must travel with them.

### 9c. ⭐ **The near-zero ICC is a property of PAIRING and does not generalise to unpaired quantities.**

Why ICC is near zero at all: **pairing has already removed the landscape.** The shared landscape
effect largely cancels in the *difference*, which is the quantity being tested.

**So it does not transfer.** Measured ICC of **raw per-arm `auc_pred`**: **−0.226 (`doe`) to
+0.581 (`lhs`).** For anything **unpaired** in the cross-family grid — arm means with intervals,
containment proportions, prevalence figures — **the unit choice can still matter a great deal,
and n=25 stays the default there.** It may not be waved through on the strength of the
paired-difference median. **Registered for P6.**

### 9d. **A polarity bug worth generalising: raw sign comparison across metrics with opposite direction.**

The F-analysis worker's first corroboration check compared **raw signs** across metrics. **Brier
and regret are lower-is-better; `alpha*` and AUC are higher-is-better.** So
`versionb − versionb_random` reading **+0.0261 on `alpha*` and −0.0071 on Brier** was scored as a
*disagreement* when **both favour `versionb`.** It inverted **two of four** readings, including
turning a fully-corroborated upgrade into an apparently contradicted one. Fixed with an explicit
per-metric direction and `benefit_sign()`, with tests.

**Registered programme-wide: no cross-metric agreement check may compare raw signs.** Every
metric carries its benefit direction. This is the same class as the type-I-alone trap (Erratum
6b) — a statistic read without knowing what "good" means for it.

**Result of the corrected audit:** the **downgrade is the one that is NOT corroborated** — and is
actively **contradicted** by `iou_vorobev_expectation` (+0.0723, p<1e-4) pointing the other way,
so removing it costs nothing. And **two of the three model-internal upgrades DO have validated
backing** (AUC +0.0760 p=3.8e-04; Brier −0.0071 p=0.0012 with regret −0.0091 p=0.0117), so they
are **not bare `alpha*` gains** — though 9b's power explanation still applies to all three.

**The AUC upgrade cannot be checked under the error-volume framing:** `results/versionb.json`
carries none of `vol_*`, `fi_*` or `true_frac_above_tau`. Corroborated on **Brier** instead
(−0.0154, p<1e-4, same benefit direction). Settling it properly needs `run_versionb.py` to emit
the three columns.

### 9e. **Additive regeneration of one's own committed output: APPROVED, with the standard stated.**

`results/f1-dual-n.json` was regenerated to add `metric`, `metric_class`, `arms`, `key_b`,
`filters`, `source` and `status_change_audit`. The worker verified **programmatically** that all
137 contrasts' pre-existing fields, `containment_per_cell`, `registered_kill` and every prior
`summary` key are **byte-identical to `HEAD`.**

**Approved, and preferable to a second file.** Standard, matching the P5 `tau_q` rename
(Erratum 7e): **an additive regeneration of one's own output is permitted when byte-identity of
every pre-existing field is proved programmatically and stated in the report.** Trust is not
sufficient; the proof is what makes it an exception rather than a breach.

---

## 📌 AMENDMENT F2a — CORRECTION · **The registered IoU bound was measured on rows that exclude the arm under test. Per-file bounds, both named.**

**Found by the P2 worker. Verified independently, and it reproduces exactly:**

| file | arms | worst \|Δ\| | ULP at 1.0 | rows | negatives |
|---|---|---|---|---|---|
| `k6-designspace.json` | optimiser + `doe` | **2.220446049250313e-16** | **1.00** | 2,553 | 0 |
| `k6-designspace-spread.json` | **spread** | **3.3306690738754696e-16** | **1.50** | 1,318 | 0 |

**Amendment F2a registered `2.220e-16` — measured on the optimiser file only. `plate1_only` IS a
spread arm, so the registered constant would have FAILED on P2's own deliverable.**

**Registered correction: the bound is recorded PER FILE, both values named**, not widened to a
single global bar:
* optimiser rows — `2.220446049250313e-16`
* **spread rows — `3.3306690738754696e-16`**

**This is NOT a tolerance being widened, and the distinction is the whole point.** The identity is
**exact in real arithmetic**; both numbers are float64 rounding of a single division; nothing about
the decomposition changes. What changed is the **population the bound was measured on.** In the
worker's words, which are the registered statement:

> **"A bound measured on rows that exclude the arm under test is not a bound for that arm."**

**This is the third time tonight a constant I quoted has been wrong for the population it was
applied to** — after `0.0394` (d=6 only, quoted as general) and the audit's `doe` column shifts
(one cell, quoted as pooled). **Same failure mode, three times: a number measured on a subset and
registered as if it were universal.** Registered as a standing check: **every constant in a
registration names the population it was measured on.**

---

## 📌 MULTI-AGENT HAZARD · **Never use an unscoped `pkill` in a shared session.**

The P2 worker ran `pkill -9 -f "spawn_main"` while cleaning up its own workers. **That pattern is
not scoped to one run** — it matches every Python multiprocessing child on the machine, belonging
to any of seven concurrent agents.

**It self-reported this unprompted, checked immediately, and confirmed nothing of anyone's was
killed** (P7, P1's Q30, P3 and P1's gate are all single-process; `run_d23_doe_subspace` started
afterwards). **Registered as a rule anyway, because the check was luck rather than design:** kill
by **PID** from your own launch, or by a pattern containing **your own script name**. Never by a
shared runtime symbol.

**⚠️ One consequence worth flagging rather than asserting.** The P4/D23 worker reported **three
runs dying with `BrokenProcessPool` — "workers not raising, being SIGKILLed"** — and attributed it
to memory pressure. **`pkill -9` produces exactly that signature too**, and both explanations fit.
The timeline says its D23 run started after, so at least that one is memory — but **the earlier
losses should not be attributed to memory with confidence.** Recorded so the machine's behaviour
is not over-diagnosed from an ambiguous signal.

---

## 📌 P2 SCHEMA DISCARD · **Discarding 8 completed keys was CORRECT. Registered so it is not read as waste.**

Amendment F added six columns to every row **after** P2 had completed 8 of 50 keys. Resuming across
that boundary would have put **two schemas in one file, distinguishable only by which key a row
belongs to** — inhomogeneity that a per-cell table averages **without showing.**

**The 8 keys are discarded, `resumable_rows()` refuses the schema change explicitly, and the
partial is parked OUTSIDE `results/`.** Cost ~20 minutes.

**What they established survives the discard and is recorded here:**
* **Gate: 192 rows × 24 columns = 4,608 comparisons, 0 failures.**
* **Determinism: 18 of 24 campaigns at worst |Δ| = 0.000e+00.** The other **6 are all one
  instance** — `32bb966a18f1d863`, whose `optimum_value` is **`1.0000000000000002`** — and **the
  only column that moves is `brier_pred`, at ≤1.39e-16.** `alpha_star`, `vorobev_deviation`,
  `auc_pred` and all twelve `ce_*` are **exactly 0.0 even there.**

**That is §3.1's float offset landing precisely where the `exact_mu_max` split was built to catch
it:** Brier is **continuous in the threshold** and sees a 2e-16 shift; AUC is **rank-based** and
cannot. A design decision made earlier in the project, confirmed by a defect it was built for.

---

# 🔴🔴 SCOPE GAP 1 · **SPADE IS MISSING FROM SEVEN OF THE EIGHT PHASE 2–4 RUNS. Raised by Joseph. My error.**

**The project is about SPADE. Version B appears in ONE of the eight Phase 2–4 runs.** Measured by
scanning each runner's `ARMS` tuple:

| run | what it delivers | Version B arms? |
|---|---|---|
| `run_p2_versionb_gamma` | the γ ladder | ✅ all four |
| **`run_p7_murphy`** | **Murphy calibration — a PRIMARY Phase 2 deliverable (F2d)** | ❌ **none** |
| **`run_p4b_alpha_anomaly`** | **the α\* anomaly — α\* IS SPADE's own statistic** | ❌ **none** |
| **`run_p6_families`** | **the entire cross-family programme** | ❌ **none** |
| **`run_p3_cells`** | **the three missing (d, σ_rel) cells** | ❌ **none** |
| `run_p4_coord` | widening the ranking to 9 arms | ❌ none |
| `run_p1_kernel_gate` | kernel-arm gate | n/a (kernel arms only) |
| `run_d23_doe_subspace` | `doe` subspace re-score | n/a (`doe` only) |

**Committed results carrying any SPADE arm: `versionb.json`, `versionb-predictive.json`,
`fix1-terminal-rule.json`, `step0-oracle-best.json`. That is all.** Every K6, K6b, `p4-coord` and
`p7-murphy` row has **none**.

## How I caused it

`COVERAGE-MATRIX.md` §2.2 marks Version B **"UNGATABLE — no committed comparator, and never will
be"**, and §5 lists gating as the organising principle of Phases 2–4. **I let *cannot be gated*
become *do not run*.** They are different: a Version B campaign is **seed-deterministic and fully
scoreable**; what it lacks is a committed regret column to reproduce. **Everything downstream of
regeneration — the maps, the error volumes, the calibration decomposition, α\* — is computable and
comparable.**

**The consequence, stated plainly:** as registered, Phases 2–4 would have delivered a new (d, σ)
grid, a cross-family grid, a calibration decomposition and an α\* investigation **for every arm
except the one the project exists to evaluate.**

## The two worst cases

**1. `run_p4b_alpha_anomaly` excludes SPADE, and α\* is SPADE's own metric.** The conservative
estimate is the SPADE certificate. Testing *"does α\* reward not-knowing"* across nine arms while
omitting `versionb`, `versionb_random` and `versionb_predictive` tests it **everywhere except
where it decides something.** And F1's three Holm upgrades are **all on `alpha_star`, all on
Version B contrasts** — so the arm whose upgrades are in question is absent from the test of the
statistic that produced them.

**2. `run_p7_murphy` excludes SPADE, and calibration is the metric Amendment F2 promoted to
primary** precisely because AUC cannot see it. **SPADE's whole claim is a calibrated statement**
— "this region holds at assurance γ" — so it is the arm for which calibration matters most.

## Registered fix

**Add the Version B arms — `versionb`, `versionb_random`, `versionb_predictive`, `plate1_only` —
to `run_p7_murphy`, `run_p4b_alpha_anomaly`, `run_p3_cells` and `run_p6_families`.**

* **They are UNGATED and every row must say so** — `gated: false` with a reason string, exactly as
  the kernel arms at d=8 do. **Seed determinism is their only guarantee and every table states
  it.** That is a caveat, not a reason for absence.
* **`plate1_only` IS gateable** against `k6-designspace-spread.json · lhs` and must be. It is also
  `lhs` (agreeing to 4.44e-16) and **may never be counted as a separate arm in a ranking.**
* **Cost is low:** a Version B campaign is a two-plate build, not a 10-round BO regeneration —
  measured at 1.9 s against `qlogei`'s 51 s. **Four extra arms cost less than one BO arm.**
* **`versionb_predictive` is included.** Fix 5 was a null on the committed cell; a null at one cell
  is not a null everywhere, and it is the arm that targets the predictive boundary the deliverable
  is actually about.

**Enabling defect, now blocking twice:** `results/versionb.json` carries **none** of `vol_pred`,
`vol_latent`, `fi_pred`, `fi_latent`, `true_frac_above_tau` — so **error volumes are not
computable for any Version B arm**, and the F-analysis worker could not check F1's AUC upgrade
under the F2a framing. **Any new Version B rows must emit all five**, which `run_p2_versionb_gamma`
already does.

**This is registered as a gap, not a silent fix.** It was raised by Joseph, not found by the
programme, and the runs were already under way when it was raised.

---

## 📌 ERRATUM 10 · **The "turn-tied death" diagnosis was WRONG. Two of the three runs were killed by my own hold order.**

I concluded from three simultaneous stops that *"a run tied to a turn does not outlive the turn"*
and issued relaunch instructions on that basis. **Both premises were wrong:**

* **P3 killed its own cells** with `pkill -f run_p3_cells.py` **on my explicit hold instruction**,
  seconds after reading it, and reported *"Stopped. Zero P3 processes."* The clean logs with no
  error are `pkill`, not a crash.
* **P6 did the same** — *"Your hold crossed my launch — I had started hartmann6 before it arrived
  and killed it on receipt."*
* **P7 alone actually died**, on a genuine `UnboundLocalError`.

**So "we have lost three runs that way in ten minutes" is ZERO.** One crash from a real bug, two
clean stops on my own order, and a timing coincidence I read as a pattern. **I built a systemic
diagnosis out of my own instructions and then issued corrective action for it.**

**P3's response is the standard here.** It declined to execute the relaunch, wrote *"I think you
would not have sent the relaunch had you known I stopped them on your order"*, and held. **A
worker refusing an instruction because it identified the false premise behind it is worth more
than one that complies.**

### 10a. 🔴 `setsid` does not exist on macOS. My relaunch recipe fails at the first word.

```
$ which setsid
setsid not found
```

Anyone pasting it gets `env: setsid: No such file or directory` and **no run at all** — which
would look exactly like another silent death and could have manufactured evidence for the very
diagnosis that was already wrong.

**Two verified portable forms.** P3's, using subshell orphaning:
```
( nohup env OMP_NUM_THREADS=1 ... .venv/bin/python -u scripts/<runner>.py <flags> \
    > results/<log> 2>&1 < /dev/null & )
```
P7's, using Python's own `setsid(2)` binding — this is the one it actually launched under, verified
at **PID 42939, PPID 1, PGID 42939**:
```
subprocess.Popen([...], stdin=subprocess.DEVNULL, start_new_session=True)
```

---

## 📌 ERRATUM 11 · **P4b's registered decision rule has its SIGN INVERTED relative to its own prose.**

**Found by the P4/D23 worker. This is a defect in my registration, not in the analysis.**

The registration says: *"**ρ ≤ −0.5** with a CI excluding 0 → α\* is confirmed **anti-correlated**
with the validated metric"*, under the hypothesis that *"α\* rewards not knowing"*.

**Regret is a LOSS.** So **ρ(α\*, regret) < 0 means arms with higher α\* have LOWER regret — α\*
AGREEING with the validated metric.** The registered threshold `ρ ≤ −0.5` is therefore the
**agreement** case, and the evidence for "α\* rewards not knowing" would be **ρ ≥ +0.5.**
**My threshold and my interpretation point in opposite directions.** The worker did not touch the
threshold and reported the contradiction — correct.

### What was actually measured

**ρ(α\*, regret) over 9 arms at τ_frac = 0.75, n=25: −0.3667, CI [−0.7167, −0.0667].** **Neither
registered branch fires** — the CI excludes 0 so it is not "an unexplained anomaly", and it does
not reach ±0.5 so it is not "confirmed". n=50 agrees at all four τ_fracs.

**Three findings that decide how it may be cited:**

1. **The 9-arm ρ is essentially one arm.** Leave-one-out: drop `doe` and ρ goes **−0.3667 →
   −0.0952** (τ_frac 0.75) and **−0.2500 → +0.0714** (0.60). `doe` sits at the extreme of both
   axes — highest α\*, lowest regret — in a **9-point** rank correlation.
2. **The registered anomaly IS real, but local.** Over the **three spread arms alone, ρ = +0.5000**
   at both τ_fracs — exactly the inversion as described, in the direction that says α\* rewards
   worse designs. **It does not survive adding `doe`.**
3. **⭐ The two validated metrics DISAGREE about α\*.** Against F2a's symmetric difference, at the
   one γ where the two thresholds coincide (γ=0.50, where `z = 0` makes K6's τ equal K6b's γ-free
   θ — measured worst |τ−θ| **3.331e-16 at γ=0.50 against ≥0.124 at every other γ**):
   **ρ(α\*, symmetric difference) = +0.4333, CI [+0.1167, +0.6445], excluding 0, at τ_frac 0.60.**
   **Positive on an error volume means higher α\* ↔ MORE total error.**

> **α\* tracks quality against regret and tracks badness against the symmetric difference.**
> **Reported, not resolved** — per Q20 §2, which governs exactly this.

**Consequence for F1's two `alpha_star` Holm upgrades — the honest wording, replacing mine:** they
**cannot** be called *"strengthened readings of a statistic that rewards not knowing"*, and they
**cannot** be called clean. **Any table carrying α\* must carry both facts.**

---

## 📌 ERRATUM 12 · Three further corrections, all from workers, all narrowing my claims

**12a. My F2a coverage claim is worth SIX ROWS, not thousands.** The gain of error volumes over
**IoU** is **exactly 0 rows on the K6 map** — committed `iou_*` is finite on all 9,600 rows,
because the true excursion set is never empty (minimum prevalence 0.0012), so the union is never
empty. **The union-empty case occurs exactly 6 times in `k6b-conservative.json`.** Erratum 5a
already narrowed this; it is narrower still. **The gain over `fi` is real and large** (+3,447 rows
pred, +1,073 latent on K6; +2,282 / +773 on spread) — **and the AUC half of the argument was
always the stronger one and is untouched.**

**12b. ⚠️ NEW TRAP, and it will bite P6 harder than it bit here.** **When every arm certifies
nothing, total error volume IS the prevalence** — so the "ranking" ranks prevalences and says
nothing about the arms. Measured in **4 of 12** CE cells, all at 100% emptiness. Under B3 `doe`
has the higher prevalence (0.0046 vs 0.0029 at τ_frac 0.95) and therefore places **last
mechanically.** Flagged `ranking_is_prevalence_only`, excluded, with
`separation_from_prevalence = max |total − prevalence|` carried per cell. **Same class as "type I
alone ranks silence first".** **Registered convention: a cell at full emptiness has no ranking;
check the separation before quoting one.**

*Also recorded:* K6b scores `doe` on its **4-D active subspace** (B3), so **prevalence differs by
arm in 198 of 200 cells** and the CE cross-arm ranking is **not like-for-like** — the opposite of
the K6 map, where all eight arms share the grid. `doe`'s slice is easier, so **the bias runs in
its favour.**

**12c. 🔴 A real boundary bug in the AUPRC complement, and three runners are adding AUPRC.**
Scoring the minority class as `-truth >= -tau` is `truth <= tau` — it **includes** the boundary, so
a point at exactly τ lands in **both** classes. **It needs `nextafter(-tau, +inf)`**, or the
explicit relabelling both other workers used. The finder's own test missed it because **it checked
the tie arithmetic beside the function instead of the labels the function actually scored.**

**12d. My "hill has 50 cells above the ceiling, more than any external family" is a UNIT
ARTEFACT — Erratum 6a in a new place.** Hill has **200 rows** in the τ table because it carries 25
landscapes per (d, p); each external family carries **1**. Counting rows weights hill **25×**. At
the **(d, p) cell** unit, γ=0.70 σ=0.25: **rosenbrock 6/8, levy 3/8, hill 2/8, hartmann6 0/8,
ackley 0/8.** **Hill is third of five, inside the range — not above it.** The conclusion survives
(*the asymmetry is not a property of "external families"*) but **the reason is that hill sits in
the middle, not that it leads.**

*And one thing no row-count could show:* **hill is the only family whose landscapes STRADDLE the
ceiling** — 9 of its 240 cells, one at **13/25**, a coin flip. There *"above the ceiling"* is a
**majority verdict, not a cell property**, so hill rows carry `n_landscapes_above` and never a bare
boolean.

---

## 📌 PROVENANCE HAZARD · **A worker's commits were swept into another worker's `git add -A`.**

The P6 census work — the `--census` flag, `ceiling_census()` and three tests — landed inside
**`49fe0e1` "Register the coord re-score's F2a/F2b gates as failing tests"**, a commit about
something else entirely, via another agent's broad `git add`. **Content verified intact** (HEAD
diffed against the working tree, identical, 27 tests pass) — but it is **filed under a title that
has nothing to do with it.**

**Not rewritten** — rewriting another agent's commit in a live shared tree is worse than the
mislabelling. **Recorded here so the provenance is recoverable**, and as the concrete cost of a
broad `git add` in a seven-agent tree. **Every agent uses path-scoped `git add` from here.**

---

## 📌 MULTI-AGENT HAZARD 2 · **A kill that silently failed, and a check structurally incapable of catching it.**

**Found and self-reported by the P2 worker after it checked its own stop twice.** Two independent
mistakes that **agreed with each other** — the class of failure where the verification confirms
the bug instead of catching it.

**1. In zsh, `kill $VAR` with a multi-line `$VAR` is a SILENT NO-OP.**
```zsh
KIDS=$(ps -eo pid,ppid | awk -v p=$PID '$2==p {print $1}')
for k in $KIDS; do kill -9 $k; done      # zsh does NOT word-split unquoted expansions
```
`kill` receives **one newline-joined argument**, fails, and the error had been sent to
`/dev/null`. **Use `${=VAR}` or `${(f)VAR}`, or list the PIDs literally.** This project's shell is
zsh, and this is the difference from bash that bites.

**2. ⚠️ After the parent dies, orphans reparent to PPID 1** — so a survivor check of
`ps | awk '$2==PARENT'` **finds nothing and reads as success.** The workers were alive for
another **~90 seconds** while the verification reported them gone.

**The second is the more dangerous and it generalises well past process management:** the check
was **structurally incapable of returning "still there."** Same failure as a monitor that only
greps the happy path, and the same shape as the wrong-column gate that would have passed on 88%
of ackley rows — **a test that cannot fail is not a test.**

**Registered rule: kill by explicit PID list, then verify each PID individually.** Several agents
are killing pools on this machine.

**Second kill-command defect from the same worker today**, both self-reported unprompted:
`pkill -9 -f spawn_main` (**over**-broad, matching every agent's multiprocessing children), and
now this (**under**-broad, killing nothing). **It found the second only because the first made it
check twice.** That is why the `BrokenProcessPool` attribution stays recorded as **ambiguous**
rather than resolved in anyone's favour.

---

## 📌 COORDINATION DEFECT · **My instruction cadence caused five start-stop cycles. Standing instructions issued.**

Recorded because it cost more compute today than any technical fault.

| worker | crossings | cost |
|---|---|---|
| P6 | **3** — an ordering note read (correctly) as not-a-release; a hold arriving after launch; a hold-confirmed arriving after relaunch | 3 start-stop cycles |
| P3 | 1 — a relaunch instruction premised on an accident that had not happened | 1 cycle, plus a false systemic diagnosis |
| P2 | 1 — **"RELEASED"** then **"HOLD"**, the second written *after* reading its launch report | 1 cycle |

**In every case the worker was right and flagged the crossing rather than complying.** P3 refused a
relaunch and named the false premise; P6 removed its own data point from my diagnosis; P2 stopped
and asked which instruction stood rather than sit idle on an ambiguous one.

**Root cause: I was sending hold/release decisions faster than workers could act on them, and
treating each report as current when it described a state already superseded.**

**Fix, issued: standing instructions with an explicit abort keyword** (`ABORT-P6`, `ABORT-P2`) —
run until told otherwise by a specific token, **do not stop for machine state.** Everything now
checkpoints, so an OOM kill costs at most the in-flight key. **That arbitration is more honest
than a queue I have been wrong about more often than right.**

---

## 📌 MEASUREMENT HAZARD · **Three process-inspection errors, one shape — and the third one is mine, in the numbers I made scheduling decisions on.**

The P2 worker reported its **third** process-inspection command of the day returning something
other than the truth, and named the common shape better than the individual bugs do:

> **"The measurement included or excluded the wrong things and the answer still looked
> plausible."**

| # | command | defect | direction |
|---|---|---|---|
| 1 | `pkill -9 -f "spawn_main"` | matched **every agent's** multiprocessing children | too broad |
| 2 | `ps \| awk '$2==PARENT'` | orphans reparent to PPID 1, so a dead parent makes survivors **structurally invisible** | too narrow |
| 3 | `ps -eo args \| grep -c '[r]un_p2_versionb_gamma\.py'` | counted its own **enclosing `zsh -c` wrapper**, whose command line carries the pattern text | too broad |

**The `[r]` trick suppresses the grep process itself but NOT a parent shell that happens to carry
the string.** Its preflight printed *"p2 procs running: 2"* **before it had launched anything.**

### 🔴 The same defect is in MY OWN monitoring, and it inflated the numbers I scheduled on

I have used `grep "[.]venv/bin/python -u\? scripts/run_"` throughout this session to count heavy
runners. Measured just now, side by side:

```
my pattern                                      -> 5
executable-path AND script, excluding wrappers  -> 4
```

**One of my five "heavy runners" was a `zsh -c` wrapper**, and the wrapper lines were visible in my
own output the whole time. **Every "N runners are up" figure I used to hold or release a worker was
inflated by roughly one per attached agent.** The scheduling calls were directionally right — the
box was genuinely constrained — but **the numbers were wrong, and I quoted them as measurements to
workers who then reasoned from them.**

**Registered rule, generalising the kill rule already recorded:** **match on the executable path
as well as the script name, exclude shell wrappers explicitly, and never trust a bare count.**
```
ps -eo pid,ppid,etime,args | awk '/\.venv\/bin\/python/ && /scripts\/run_[a-z0-9_]+\.py/ && !/zsh -c/'
```

**Four process-inspection defects today, three of them self-reported by the worker that made them,
one of them mine and found only because that worker reported its third.**

---

## 📌 THE `static_curve` ARTEFACT, FOURTH SIGHTING · **and this time it is a trap in the OBVIOUS implementation.**

Building `plate1_only` **through `replay`'s `builder` hook** — the natural choice, since it is
nominally a Version B arm — **misses the committed `lhs` regret by 3.3e-16 and fails an exact
gate.**

**Cause:** `replay.regenerate` reproduces `run_e2.static_curve`'s **20-ordering mean** only on its
own **spread-arm** path. Supplying a `builder` substitutes a single `scored_curve` call. So
`plate1_only` must be built **as `lhs` and relabelled**, which reproduces bitwise.

**The fix pins BOTH directions in a test** — the good path asserts `==`, the hook path asserts
`!=` but within 1e-14 — **so the hook cannot be quietly adopted later by someone reasoning "it's a
Version B arm, use the Version B builder."** A test that only asserted the good path would leave
the trap armed.

**Sightings, all the same float-mean artefact:** (1) my first replay gate; (2) the Fix 1 worker,
hours later, independently; (3) inside a **committed file** — `versionb.json`'s `plate1_only`
column differs from the committed `lhs` column by 3.33e-16; (4) now, latent in the obvious
implementation of a new arm. **The standing rule — match the arithmetic, never widen the
tolerance — has caught it four separate times, which is the strongest evidence available that it
is load-bearing rather than ceremonial.**

---

## 📌 WHY THE SPADE SCOPE GAP MATTERS — the P7 worker's argument, which is better than mine

I argued for inclusion on coverage grounds. **The sharper argument:**

> **Calibration is the one component of the Brier score that can distinguish *"this region holds
> at assurance γ"* from *"this region is ranked above that one"* — and Version B is the only arm
> that makes the first kind of claim.**
>
> **Scoring calibration across nine arms that make no calibrated claim, while omitting the one
> that does, would have produced a technically clean result answering nobody's question.**

**Measured cost of closing it: ~17 s/key for four arms** (`versionb` 12.1 s, `versionb_random`
1.0 s, `versionb_predictive` 3.4 s, `plate1_only` 0.1 s) against **~126 s/key for the original
six.** Four extra arms cost less than one BO arm.

---

## 📌 ERRATUM 13 · **The ρ = +0.4333 I registered in Erratum 11 INVERTS at most cells. This is F4's defect in a correlation, in a finding of mine.**

**Found by the F-analysis worker; verified independently here at 6 of 17 scorable cells positive
(it reports 6 of 18; one cell differs on a tie threshold).** Erratum 11 recorded
**ρ(α\*, symmetric difference) = +0.4333, CI excluding 0** as a headline — *higher α\* ↔ more
total error.* **Recomputed per (γ, τ_frac):**

```
tf\gamma    0.50     0.70     0.80     0.90     0.95     0.99
0.60      +0.690   +0.619   +0.619   +0.524   +0.476   -0.119
0.75      +0.095   -0.429   -0.595   -0.476   -0.714   -0.071
0.85      -0.464   -0.571   -0.257   -1.000   -0.500       —
0.95           —        —        —        —        —       —   (every arm ties)
```

**The two consequences point in opposite directions and BOTH must be reported:**

1. **The concern is live exactly where it matters most.** τ_frac = 0.60 is the primary cell, and
   there the association is **stronger than the number I quoted** — **+0.476 to +0.690 at five of
   six γ.**
2. **But quoted as ONE number without its cell, it inverts the reading at 11 of 17 cells**,
   reaching **−1.000** at (γ=0.90, τ_frac=0.85). **That is precisely the defect Amendment F4
   withdrew the pooled containment figure for** — one summary standing in for cells that disagree
   **in sign**, not merely in magnitude — **reappearing in a correlation, in a correction I wrote
   to catch exactly that class of error.**

**And what the statistic can bear, which I did not state:** **n = 8 arms per cell**, one rank swap
moves ρ by **~0.1**, and no interval is attached. **If P4b's +0.4333 carries a CI, what is it an
interval over?** With 8 arms in one cell there is little to resample; **if it is bootstrapped over
campaigns within a fixed arm ordering it answers a different question than the rank association
does.** To be resolved when `results/p4b-alpha-star-anomaly.json` lands — **and if its ρ is pooled
across cells, it needs the same treatment F4 gave containment.**

### The distinction that stops either half swallowing the other

**ρ is an arm-level RANK ASSOCIATION across eight arms.** F1's Holm upgrades are **PAIRED
CONTRASTS between two specific arms within one cell.** **Different objects — ρ does not govern
them.**

**So both of these are true and neither cancels the other:**
> **The α\* ranking is not trustworthy at the primary cell** — and **these particular paired
> contrasts are corroborated anyway.** KILL 2's upgrade sits at τ_frac = 0.60, the most damaging
> region, and is corroborated by **Brier** and **regret**, both validated, both agreeing in
> benefit direction.

**The ranking problem is real and does not transfer to a corroborated pairwise result; the
corroboration does not rehabilitate the ranking.**

### Standing check, now earned four times over

*Every constant in a registration names the population it was measured on* — and **this adds the
sharper form: a correlation quoted without its cell is a pooled statistic, and this project has
already withdrawn one of those.** Instances to date, all mine: `0.0394` (d=6 only), the audit's
`doe` shifts (one cell), the F2a IoU bound (optimiser rows only), and now **ρ = +0.4333 (one
τ_frac, sign-inverted elsewhere).**

---

## 📌 FINDING · **SPADE's plate-2 design threshold is a fixed fraction of `mu_max`, so it inherits §2.4's defect BY CONSTRUCTION. Empty on ackley.**

**Found by the P6 worker before any family campaign scored. This is a property of the METHOD, not
of the scoring.**

`run_versionb._two_plate` selects plate 2 by straddling
`theta = DESIGN_TAU_FRAC · mu_max = 0.75`, and **`UnitScaled` normalises every family's optimum
to 1.0 — so θ = 0.75 on every family.** Measured prevalence of that design target:

| family | design target covers | |
|---|---|---|
| **ackley** | **0.0000** | **0.75 exceeds its grid max of 0.410 — nothing to straddle** |
| hartmann6 | 0.0020 | near-empty |
| levy | 0.5417 | |
| rosenbrock | 0.7825 | |

**On ackley the straddle degenerates into "wherever the posterior mean is highest."** And since P6
scores at `tau_q`, **the arm targets one threshold and is scored at another.**

**This is exactly §2.4** — a threshold fixed as a fraction of `mu_max`, which selects wildly
different sets across families — **appearing inside SPADE's own design, in the same project that
registered `tau_q` to eliminate it from the scoring.**

### Registration decision: **DO NOT RETARGET. Record the mismatch on every row.**

The worker asked and did not act, which was right. **My answer: `_two_plate` stays imported
verbatim.**

* **Retargeting makes it a different method.** Nothing would be comparable to the committed hill
  results, and the arm would no longer be the arm this project has been evaluating for two phases.
* **The mismatch IS a finding about SPADE as published**, not an obstacle to measuring it. A
  method whose acquisition targets a fixed fraction of the optimum inherits the defect that
  fraction carries. **Reporting that is more valuable than quietly fixing it.**
* **Every `versionb*` row carries `design_theta`, `design_target_prevalence` and
  `design_target_degenerate`**, so an ackley result **cannot be read as "SPADE fails on ackley"**
  when its plate-2 target was empty by the very convention `tau_q` replaces.

**Registered as a follow-up, NOT run:** a `versionb_tauq` arm whose plate-2 straddle targets
`tau_q` instead of `0.75·mu_max` would test whether the mismatch is what hurts SPADE off hill.
**That is a NEW arm and needs registering as one** — with its own gate status (ungatable, like the
rest) and its own kill condition — before it exists.

### ⭐ And the smoke produced an argument for the design-space programme from an unexpected direction

Ackley, seed 0, all four arms:
```
versionb  0.7704   versionb_random  0.7704   versionb_predictive  0.7704   plate1_only  0.8103
```

**Regret is IDENTICAL across all three two-plate variants — and that is correct, not a bug.**
Plate 1's 40 shared LHS wells hold the best observed point, and plate 2's 8 never beat it on
ackley's needle optimum. **But `vol_pred`, `iou`, `brier` and `auprc` all differ between them.**

> **On ackley, regret cannot separate the Version B variants at all. Only the map metrics can.**

**That is the argument for this entire programme, arriving from a direction nobody set up** — and
it is the strongest form of it yet, because it is not "the map ranks differently from regret" but
"**regret has no resolving power here and the map does.**"

### The unrankable-cell trap fired live on real data

Ackley, γ=0.90, p=0.25: **`separation_from_prevalence = 0.00000`, `rankable = False`**, all four
arms at `vol_pred = 0` and `total_error_vol = 0.25 = prevalence` exactly. **Computed at MERGE,
because it is a property across arms that no single campaign can see** — which is the right place
and not where I would have put it.

**Cost correction, so the queue is planned on the real number:** the four Version B arms add
**~115 s per seed, not the ~8 s I estimated** — `versionb` alone is 47 s, because **plate 2's
candidate grid and the 24-cell map scoring dominate, not the 1.9 s campaign build.** That is
**+45% per seed**; a cell goes from ~65 min to **~95 min.** Still worth it.

---

## 📌 FINDING · **The Version B variants collapse on DIFFERENT landscapes. No single family reveals the variant structure.**

**From the P6 worker's first two family smokes, verified from its committed logs.** Regret,
seed 0:

| family | coincident on regret | distinct |
|---|---|---|
| **ackley** | `versionb` = `versionb_random` = `versionb_predictive` = **0.7704** | `plate1_only` 0.8103 |
| **hartmann6** | `versionb` = `versionb_predictive` = **0.6182** | **`versionb_random` 0.4824**, `plate1_only` 0.4116 |

**On ackley all three two-plate variants coincide; on hartmann6 only two do, and the random
control separates.** So **which variants a landscape can distinguish is itself landscape-dependent**
— and **no single family reveals the structure.**

**Why this matters beyond a curiosity.** Every Version B conclusion in this project — including
KILL 1 and KILL 2 — rests on **hill alone.** Fix 5's null (`versionb_predictive` indistinguishable
from `versionb`) was measured there. **Hartmann6 reproduces that null while separating
`versionb_random`, and ackley collapses all three.** A method comparison run on one landscape can
therefore report a null that is a property of the landscape rather than of the method — **and
there is no way to detect that from inside the single family.**

**This is a second, independent argument for the cross-family programme**, alongside the metric
argument: not *"the map ranks differently from regret"*, but **"the arms that a landscape can
separate at all vary by landscape."**

**A free internal consistency check falls out.** `plate1_only` = **0.4116** on hartmann6 seed 0 is
**bit-identical to that seed's `lhs` = 0.4116** — the two are the same 48-well design, and this is
**the only check that arm can have off hill**, where `k6-designspace-spread.json` provides no
comparator. **It was not designed as a gate and functions as one.**

---

## 📌 QUEUE HORIZON · measured, and it is a decision for Joseph, not for me

The P6 worker's observed per-seed cost, **all ten arms**, d=6 σ=0.25:

```
doe 13   qlogei 51   qlognei 65   lhs 10   sobol 10   random 9
versionb 37   versionb_random 15   versionb_predictive 26   plate1_only 18      = ~254 s/seed
```

| scope | wall-clock |
|---|---|
| one family | ~1.8 h |
| **one cell (4 families)** | **~7 h** |
| all four cells | **~28 h** nominal, **~20–24 h** realistic (d=8 and σ=0.10 are cheaper) |
| **cells 1 + 2 only — the registered fallback** | **~14 h** |

**The registered cell ordering is what makes an early stop publishable.** Cells 1 and 2 —
(6, 0.25) and (6, 0.10) — give the cross-family headline **plus** its σ sensitivity on the axis
D37 showed the sign flipping. **Stopping after cells 1 and 3 would not.** That ordering was chosen
on P3's Kendall τ-b measurements before any of this cost was known, and it now pays for itself.

**The worker is not pausing and did not ask for a decision** — it stated the horizon because *"run
the full programme"* and *"the OOM killer will decide"* are both compatible with 28 hours.
**Recorded here so the choice is explicit rather than discovered at hour 20.**

---

## 📌 ⭐ **THE IDENTITY GATE FIRED, AND CAUGHT A BUG IN ITS OWN OWNER'S CODE. No tolerance was widened.**

**First real P6 run, and the registered kill behaved exactly as specified.**

```
MissingGateTarget: hartmann6 versionb_random seed=1 p=0.75 gamma=0.5:
  error-volume identity misses iou_pred by 3.331e-16,
  over the 2.220e-16 bound measured on the spread arms
```

### The message contradicted itself, and that is what identified the bug

**It names the SPREAD population while quoting the OPTIMISER number.** Cause: `SPREAD_POP` had
been extended to include the four Version B arms, but `iou_bound_for` still repeated the literal
`("lhs", "sobol", "random")`. So `versionb_random` was **checked against the optimiser bound while
the failure text used `SPREAD_POP` for the name.**

> **A constant and its consumer disagreeing — one level further down than the defect this gate was
> added to catch.**

Fixed by making `iou_population(arm)` **the single decision**, read by both the bound and the
message.

### And the test is why it shipped wrong — the same shape, again

`test_the_iou_identity_bound_is_per_population_and_both_are_named` covered `lhs`/`sobol`/`random`
and `doe`/`qlogei`/`qlognei` and **omitted the four arms that had just been added to the
constant.** It now asserts the bound for all four **and** asserts, for **every** arm in `ARMS`,
that `iou_bound_for` and the message name come from the same lookup.

**That is the third distinct instance today of a check that could not see the case it was written
for** — after the wrong-column gate that would have passed on 88% of ackley rows, and the survivor
check structurally blind to reparented orphans.

### 🔑 Nothing was widened, and the number is evidence in its own right

**`3.3306690738754696e-16` is the already-registered spread bound**, measured on
`k6-designspace-spread.json`. **Nothing moved.**

**And `versionb_random` landing on EXACTLY the spread worst case is evidence the proxy
classification was right** — the Version B arms **do** behave like the spread population
numerically. **That is the first data anyone has on a population the registration explicitly
recorded as unmeasured** (`SPREAD_POP` "states that the Version B arms are a proxy whose own
population has never been measured"). The proxy is now measured, and it holds.

### The registered stop behaviour is what made a 4e-17 discrepancy visible

The runner **raised**, exited non-zero, and the driver **halted the entire programme** — ackley,
levy and rosenbrock never started; **24 campaigns banked and intact.**

> **A gate that stops the programme is what let a 4e-17 discrepancy surface as a stop rather than
> as a column nobody reads.**

**And the worker correctly did not treat the stop as a hold** — it was a registered kill, it fixed
the cause, and it restarted **within the same standing instruction.** That is the distinction
between a kill condition and a pause, and it was drawn without being asked.

### One requirement carried to the `versionb_tauq` follow-up

**Its kill condition must be written against a MAP metric, not regret.** The three two-plate
variants measured **indistinguishable on regret** on both ackley and hartmann6 while **distinct on
`vol_pred` / `iou` / `brier` / `auprc`.** **A regret-based kill would be unable to detect its own
effect.**

---

## 📌 ERRATUM 14 · **"24 of 24 cells" is "18 of 18 RANKABLE cells". And the `plate1_only` gate target I specified does not exist at the cells I specified it for.**

### 14a. The F2a headline has the wrong denominator. Direction and strength unchanged.

**Found by the P3 worker applying the degenerate-cell rule to the committed baseline. Verified
independently — 6 of 24 exactly degenerate, all six at τ_frac = 0.95:**

```
separation_from_prevalence, k6-designspace.json
 gamma        0.60        0.75        0.85        0.95
  0.50     3.68e-01    1.55e-02    2.68e-04    0.00e+00
  0.70     3.94e-01    1.89e-02    4.91e-04    0.00e+00
  0.80     3.41e-01    1.45e-02    2.52e-04    0.00e+00
  0.90     2.36e-01    1.09e-02    6.00e-05    0.00e+00
  0.95     1.51e-01    7.02e-03    2.00e-05    0.00e+00
  0.99     6.68e-02    1.50e-03    2.00e-06    0.00e+00
```

At τ_frac = 0.95 **`empty_pred = 1.00`** — every arm certifies nothing, so **total error volume IS
the prevalence for all of them** and any ordering ranks the landscape, not the arms.

**So Amendment F2a's *"the error-volume ranking differs from AUC's in 24 of 24 cells"* is
correctly *"18 of 18 rankable cells."*** **The finding is unchanged in direction and strength —
still 100% disagreement wherever a ranking exists** — but **six of the twenty-four could never
have agreed OR disagreed**, and a reader is entitled to know which denominator they are looking
at. **I have quoted 24/24 repeatedly, including to Joseph.** Relayed to the F-analysis worker,
which owns the technical report.

**Also flagged, and the handling is right:** the **τ_frac = 0.85** column decays **9.2e-3 → 5.0e-5**
as γ rises — *technically rankable and nearly vacuous.* The worker **excluded only the exactly
degenerate and reports the separation for the rest**, on the grounds that *"a chosen cutoff would
be my judgement masquerading as a measurement."* **Adopted as the rule: report the separation,
exclude only exact degeneracy, never pick a vacuousness threshold.**

### 14b. 🔴 My `plate1_only` gate target does not exist at the cells I gave it for.

I instructed three workers to gate `plate1_only` against **`k6-designspace-spread.json · lhs`.**
**That file covers d=6, σ=0.25 ONLY — none of P3's three cells, and nothing off hill.**

**The correct target is `e2-grid.json · lhs`**, which carries `lhs` at all three of P3's cells —
**and is the stronger target under D12 anyway:** the original E2 runner against a replay, rather
than one replay against another. **Measured |Δ| = 0.0 exactly at (6, 0.10).**

**And the construction detail that makes it gateable at all:** `plate1_only` must be regenerated
**as `lhs` and relabelled**, so it is built by the arithmetic its column was built by —
**including the 20-ordering mean.** Building a fresh LHS instead misses by ~1e-16 and fires the
gate **on an artefact.** *(Fifth sighting of the `static_curve` artefact, and the second time it is
latent in the obvious implementation.)* Every row carries `duplicate_of: "lhs"` so no downstream
table can double-count it, per D23.1.

---

## ✅ ERRATUM 11 — **CLOSED 2026-08-22.** The twelve-arm top-up exists; all three structural predictions survived.

`results/p4b-alpha-star-anomaly.json` · `n_arms: 12`. At the registered primary τ_frac = 0.75,
n=25: **ρ = −0.3916, CI [−0.6643, −0.0839], p = 0.0175.**

| provisional 9-arm | 12-arm | verdict |
|---|---|---|
| ρ = −0.3667 | **−0.3916** | direction and rough magnitude hold |
| leave-one-out drop to −0.0952 | drop `doe` → **−0.2091** | `doe` **is still the max-leverage arm**, but the leverage is **weaker** than the 9-arm figure implied |
| spread-arm-only +0.5000 | **+0.5000** | **unchanged exactly** |

**Dropping `random` strengthens ρ to −0.6000 while dropping `doe` weakens it to −0.2091 — the two
extreme arms pull in opposite directions.** That caveat travels with every quotation.

**Erratum 13 is CLOSED with it**, on the same file.

**And a NEW defect of the same shape, found while closing these:** `FINDINGS-SPADE.md` §15
headlined **−0.3497 at τ_frac = 0.60** — not the registered primary, quoted without its
threshold — and it propagated onward as "§15's twelve-arm result." Corrected. **All four
thresholds now appear**, and they carry a finding that one cell was hiding:

| τ_frac | ρ | CI excludes 0 |
|---|---|---|
| 0.60 | −0.3497 | yes |
| **0.75 (primary)** | **−0.3916** | yes |
| 0.85 | **+0.0070** | **no** (p = 0.83) |
| 0.95 | **+0.0140** | **no** (p = 0.77) |

**The α\* / regret relationship exists only at the two LOWER thresholds and vanishes at the two
higher ones** — sign flips, CI spans zero. Whatever α\* tracks, it stops tracking it exactly
where certified regions start going empty.

---

## 📌 ⚠️ ERRATUM 11 (original text, retained) — **PROVISIONAL. The ρ figures are NINE-arm numbers and the run is now TWELVE arms.**

**Flagged by the P4/D23 worker before publication, unprompted.** Erratum 11 records
**ρ(α\*, regret) = −0.3667**, the leave-one-out drop to −0.0952, and the spread-arm-only +0.5000.
**All of those were computed over nine arms.** Closing the SPADE scope gap adds `versionb`,
`versionb_random` and `versionb_predictive` to the ranked set — **twelve ranked arms** — and
**every coefficient will move**, the leave-one-out and spread-arm figures with them.

> **🔴 DO NOT write −0.3667 as final.** I have already quoted it in Erratum 11 and reported it as a
> finding. **It is provisional pending the twelve-arm top-up.**

**What is expected to survive, and is structural rather than numeric:** the **one-arm leverage**
(`doe` at the extreme of both axes), the **local three-arm inversion** among the spread arms, and
the **regret / symmetric-difference disagreement**. **The coefficients will not be identical.**

**And Erratum 13 compounds this:** the +0.4333 against the symmetric difference is *also* a
nine-arm figure **and** a single-cell figure quoted without its cell. **Both errata are pending the
same top-up.**

**Note the ranking has now been silently too narrow twice, in opposite directions** — P4 existed
because `coord` was missing (8 arms), and this omitted the arms that **own the statistic**.

---

## 📌 The memoisation is declined a SECOND time, on a sharper reason, and both declines are right

**The P4/D23 worker measured its own profile as instructed** — and it favours the cache, contrary
to P1's:

```
regenerate    13.21s  30.4%
K6 (24 cell)  12.15s  27.9%
K6b (alpha*)  17.27s  39.7%   <- what the memoisation targets
```

**A perfect 4× would save ~30% of a campaign against P1's 5.5%. It declined anyway, and the
reason is better than the arithmetic:**

> **Every α\* the memoised path would touch is UNGATED.** The nine gated arms' α\* is **read from
> committed files, not recomputed** — so the cache would only ever affect the three Version B
> arms, which are **ungatable in principle and have no comparator now or ever.** That is applying
> an optimisation **precisely where the safety net is absent.**

**P1's standard was *"the safety net would catch it is a reason the risk is survivable, not a
reason to take it."* This is the mirror image — there is no net at all**, and 30% of a 20-minute
top-up is six minutes.

**Plus a concrete collision hazard neither I nor P2 had identified:** an **empty or all-true mask
has identical bytes across campaigns**, so a cache keyed on `(theta, mask)` that **outlived one
`draws` tensor** would return **another campaign's number.** P2's per-cell scoping handles it; a
wider scope would not.

**Registered: the memoisation is adopted where scoring dominates AND the result is gated
(P2, P3's K6b half), and declined where either fails (P1 on cost, P4b on absence of a gate).**

---

## 📌 Erratum 14b, restated because I have now sent the wrong gate target TWICE

`k6-designspace-spread.json` covers **d=6, σ=0.25 only.** It cannot gate `plate1_only` at **any
other cell and nowhere off hill.** **Use `e2-grid.json · lhs`**, which carries `lhs` at all three
P3 cells and is the stronger D12 target — original runner against replay, not replay against
replay. **Measured |Δ| = 0.0 exactly at (6, 0.10).**

*(The P6 worker independently marked `plate1_only` ungatable off hill, so it was never exposed —
but it was exposed by luck rather than by my instruction being right.)*

---

## 📌 ERRATUM 14a — REFINED · **The denominator differs BY METRIC. "18 of 18" overstates the evidence for type I.**

**Two refinements from the F-analysis worker, one of which corrects my correction in the direction
of overstatement.**

### 1. 🔴 Per-metric denominators, and type I is 14 not 18

```
type_I  : degenerate 10 of 24  ->  denominator 14
type_II : degenerate  6 of 24  ->  denominator 18
total   : degenerate  6 of 24  ->  denominator 18
```

**An all-empty region scores type I EXACTLY 0**, so it ties at **four further high-γ cells** —
(0.90, 0.85), (0.95, 0.85), (0.99, 0.75), (0.99, 0.85) — **where type II still separates the
arms.** *(This is Erratum 6b's "type I read alone ranks silence first" reappearing as a
denominator, not just as a ranking hazard.)*

**"18 of 18" quoted for type I would be wrong in the direction of OVERSTATING the evidence.**
All three denominators are now stated explicitly and locked in a test.

### 2. The rankability criterion is a TIE TEST, not `separation == 0`

**Two of the six degenerate cells have separation `1.1e-16`, not `0`** — (0.90, 0.95) and
(0.99, 0.95). **A rule written as `separation == 0.0` would have kept them as rankable.** The
criterion that actually decides is **whether the arm means tie** (`max − min ≤ 1e-15`).

*(My own quick table and the worker's differ in the non-degenerate entries — 3.68e-01 vs 3.98e-01
at γ=0.50, τ_frac=0.60 — almost certainly a `pred`/`latent` or arm-set difference in my ad-hoc
recomputation. **Not load-bearing for the denominator**, and the worker's committed script is the
authority; recorded because we were both quoting the column.)*

---

## 📌 ⚠️⚠️ **THE TWO DEGENERACY FLAGS ARE NOT INTERCHANGEABLE — and the cross-family case needs BOTH.**

**This is the most important thing to come out of the correction, and it is invisible from the map
alone.**

| | prevalence across arms | at full emptiness | which flag catches it |
|---|---|---|---|
| **K6 map** | **arm-identical** (0 of 1,200 cells differ) | every arm **ties** | **`_degenerate` (tie test)** |
| **CE sets** | **arm-DIFFERENT** — B3 scores `doe` on its 4-D subspace | arms **do NOT tie; they differ BY PREVALENCE** | **`ranking_is_prevalence_only` only** |

> **`_degenerate` alone would have missed all four vacuous CE cells** — the tie test stays
> **silent** while the ranking is exactly as vacuous. **And `ranking_is_prevalence_only` alone does
> not generalise to metrics that are not prevalence-anchored.**
>
> **Neither is sufficient once arms or families differ in prevalence — which is the cross-family
> case BY CONSTRUCTION.**

Locked in a test asserting `_degenerate` must **not** fire on the CE τ_frac = 0.95 cell.

**Registered requirement for P6:** it must carry **both** flags. Its own ceiling census —
**rosenbrock 8/8 above the noise ceiling at γ ≥ 0.90, levy 8/8 at γ ≥ 0.95** — guarantees it hits
the **CE-shaped** case, not the map-shaped one, **wherever families are compared at a common
threshold.**

**Unchanged:** direction and strength stand — 100% disagreement wherever a ranking exists, ρ =
+0.071 unaffected (the Spearman already excluded degenerate cells, since a correlation against a
constant is undefined). Descriptive arm means remain over all 24 cells, legitimately: **the six
degenerate cells contribute the same prevalence to every arm, shifting all eight equally without
changing their order.**

---

## 📌 A THIRD DEGENERACY CASE · **`arms_tie` catches something `separation` cannot see IN PRINCIPLE.** And my reasoning about P6's shape was wrong.

**Found by the P6 worker while implementing the two-flag requirement.**

### The third case, which neither flag as I described them would catch

I framed it as **map-shaped** (arms tie) versus **CE-shaped** (arms differ by prevalence). **There
is a third:**

> **Arms that agree with EACH OTHER at a value far from the prevalence.** Large separation,
> complete tie, **utterly unrankable** — and `rankable = sep > 0` calls it **rankable.**

Pinned by a constructed test: three arms at `total_error_vol = 0.20` against prevalence 0.75 —
**separation 0.55, `rankable: False`.**

**So the two flags are not merely non-interchangeable in the two directions I gave.
`arms_tie` catches something `separation` cannot see IN PRINCIPLE, because separation never
compares the arms to each other at all** — it compares each arm to the prevalence. **That is a
stronger and more general argument for carrying both than the one I made**, and it holds
regardless of which shape any given file turns out to be.

### 🔴 And my census argument reached the right requirement by a route that does not apply

I told the P6 worker its ceiling census — rosenbrock 8/8, levy 8/8 above the noise ceiling —
**guaranteed it would hit the CE-shaped case.** **It is map-shaped.**

`true_frac_above_tau` is a function of **the grid and τ only**, and P6 does **not** pin the grid to
`doe`'s subspace when scoring — `active` is used solely for `inscribed_box_from_mask`. **So
prevalence is arm-identical within every cell, and at full emptiness the arms TIE rather than
differ.** The census does guarantee full-emptiness cells; **they will present as ties, not as
prevalence differences.**

**I reasoned from the wrong mechanism to the right conclusion.** The requirement stands — both
flags are carried — but **on the third case's argument, not on mine**: the two shapes are one
B3-style subspace change apart, and the third case is real either way.

### Both corrections were live in the code I was reading

`sep > 0.0` **would have kept the two 1.1e-16 cells as rankable** — the same defect I had just
flagged, present in the runner at the moment I flagged it. Now `TIE_TOL = 1e-15` on
`max − min` of the arm means.

**Per-metric denominators are implemented and printed at merge** for `type_I_vol_pred`,
`type_II_vol_pred` and `total_error_vol_pred`, with the mechanism in the docstring: **an all-empty
region scores type I exactly 0 for every arm**, so type I ties wherever every region is empty
while type II still carries the prevalence — which is why K6 splits **10/24 against 6/24.**
**Third independent reason the symmetric difference is the right `RANKING_SCALAR`.**

Every row now carries `separation_from_prevalence`, `ranking_is_prevalence_only`, `arms_tie` and
`rankable`. **`cell_separation` is called only from `merge`**, so this changed no campaign row and
could not disturb the run in flight or the banked checkpoints — the right place for a
cross-arm property, and the reason a live correction cost nothing.

---

## 📌 ERRATUM 10 — **PARTIALLY REVERSED. The turn-tie hypothesis was RIGHT; my evidence for it was wrong.**

Erratum 10 recorded the silent-death count as **zero** — P3 and P6 self-killed on my hold order,
P7 crashed on a real `UnboundLocalError` — and concluded I had *"built a systemic diagnosis out of
my own instructions."*

**The P4/D23 worker's nine-arm P4b pass died at 44/50 from exactly the mechanism I had retracted:**
*"killed when the harness stopped its background task — the same tie-to-an-agent's-turn failure
you flagged."*

> **So the count is ONE, not zero. The hypothesis was correct and every case I cited for it was
> not.** I over-corrected: having found my three examples were my own instructions, I discarded the
> mechanism along with the evidence. **A hypothesis is not refuted by its supporting cases being
> wrong.**

**The remedy was right throughout** — detached launch at PPID 1 — and it is now confirmed working
under real conditions: **P3's cell survived its agent going idle**, and P4b's relaunch is at PPID 1
with its checkpoint intact.

### 🔴 And `setsid` failed silently a THIRD time

*"Your prescribed form failed silently and my first relaunch never started."* **Third worker to
hit it.** The line I circulated does not merely fail — **it fails in a way that looks exactly like
the death it was prescribed to prevent**, which is how it nearly manufactured evidence for a
diagnosis that was, ironically, correct. **`nohup … & disown` reaches PPID 1 on macOS and is what
is running now.**

### My checkpoint search was wrong, and I said it might be

I reported no `*p4b*` checkpoint under the scratchpad. **The checkpoint was in `$TMPDIR` —
`/var/folders/...`, the per-user macOS path — not the session scratchpad I searched. 396 rows, 44
units, never at risk.** I flagged the search as unreliable rather than authoritative and asked for
it to be verified; **it was, and it was wrong.** Fourth process-inspection error of mine today.

**The arm-aware checkpoint preserved all 396 nine-arm campaigns**, so the twelve-arm relaunch is a
**254-campaign top-up, not a 650-campaign re-run** — ~40 minutes.

---

## 📌 ERRATUM 13 — REFINED · **The γ=0.50 restriction was PRINCIPLED. The τ_frac variation is the real limitation.**

**The P4/D23 worker pushed back and is largely right.** Erratum 13 recorded that
ρ(α\*, symmetric difference) = **+0.4333 inverts at 11 of 17 cells** and called it a pooled
statistic. **Two framings, and they differ:**

**Its figure is already cell-attached** — (γ = 0.50, τ_frac = 0.60) — and **γ = 0.50 is not one
choice among six.** It is the **only** γ at which K6's τ and K6b's γ-free θ are the *same number*:
worst |τ − θ| = **3.331e-16 there against ≥ 0.124 at all five others.** So the eleven inversions
found across other γ are **correlations between α\* and an error volume computed on DIFFERENT
superlevel sets** — precisely the comparison the analysis was restricted to avoid, **not a
robustness failure of the matched one.**

**Where my point does land, and the worker has taken it: the sign varies across τ_frac WITHIN
γ = 0.50.**

```
gamma = 0.50:   tau_frac 0.60  ->  +0.4333
                         0.75  ->  -0.2333
                         0.85  ->  -0.1833
                         0.95  ->  nan  (every arm certifies nothing; coefficient undefined)
```

> **So *"α\* tracks badness on the symmetric difference"* is a τ_frac = 0.60 STATEMENT, not a
> general one.** That is the F4 defect, and it is real — **but it is a τ_frac defect, not the γ
> defect I registered.**

**Erratum 13 stands corrected in its diagnosis while its conclusion holds:** the figure needs its
**τ_frac** attached, the **γ = 0.50 restriction is a feature and must not be described as
cherry-picking**, and the 11-of-17 table is a comparison across mismatched thresholds rather than
seventeen attempts at the same one.

---

# 📌 REGISTRATIONS AND DECISIONS · 2026-08-22

## ⭐ DECISION 1 · **Ackley is IN for the map and OUT of every DoE contrast.**

**Taken 2026-08-22, BEFORE the cross-family numbers existed.** The recorded ground is
pre-existing: the screen evaluates the box centre as well as the CCD, so the DoE design hits
ackley's exact optimum **7 times**. A contrast a design artefact decides is not a contrast.

**It then emerged that ackley is the only family of four where `doe` wins** (mean rank 4.32 of
9, 9 of 19 cell wins). **The ordering of decision and result is part of the registration**, and
because the exclusion removes the single family favouring `doe`, the ackley column is
**reported in full in every table rather than dropped**, labelled excluded. Every effect on
ackley is below SESOI in any case.

Ackley was previously unrunnable because its grid max is 0.410, below every `tau_frac`, so every
metric came back `nan` — **a threshold property, not a family property.** It runs under `tau_q`.
This also fixes Version C §3.3's scoring set.

## ⭐ DECISION 2 · **The B3 subspace comparison is DROPPED, and the claim REMOVED.**

Not softened. Both sides were `tau_frac`-pooled and the unrestricted run was never broken out
per cell, so **the comparison cannot be made from committed files at all.** Removed at both
sites — §5.10.2 and, more importantly, the site that asserted the same withdrawn comparison in
the document's own voice **with no F4 marker** while every other site carried one. The `alpha*`
half of that sentence is a different, unpooled quantity and survives. The surviving per-cell
statement (`doe` contained in 0 of 50 at `tau_frac=0.60, alpha=0.50`) is load-bearing and is
kept.

## ⭐ DECISION 3 · **Kernel-arm re-score runs after the cross-family cells.** Launched on completion.

## 🔴 REGISTRATION CHANGE · **The IoU identity gate is now a DERIVED per-row bound.**

**This changes a registered gate and is recorded as such.** Full account in
`FINDINGS-SPADE.md` §18.

`IOU_IDENTITY_BOUND`'s two scalars — 2.220446049250313e-16 "optimiser" and
3.3306690738754696e-16 "spread" — **are not bounds.** They are `max(observed)` over a few
thousand Hill rows. Measured on pure arithmetic with no oracle, no GP and no dataset, the
1.0-ULP bar breaks on **0.152%** of configurations and the 1.5-ULP bar on **0.011%**; P6 runs
~120k identity checks per family.

`iou_identity_bound(vol, prev, inter, union, ref)` is Higham (ASNA §3.1) first-order propagation
evaluated per row. **Zero violations in 60k configurations (worst err/bound 0.54) while firing
on 100% of three injected F2a bugs.**

**`IOU_IDENTITY_BOUND` is KEPT** as the honest record of what each committed file measured, and
it still gates those files in `tests/test_p2_versionb_gamma.py`, where it is keyed by filename
and its population claim is therefore honest. It is no longer what gates a family it was never
measured on.

**This was NOT a widened tolerance.** The evidence is independent of the failure that prompted
it and would read identically had the failure never occurred. **A reviewer who disagrees should
re-tighten the gate and re-score; the campaigns are checkpointed and scoring is cheap relative
to them.**

## 🔴 ERRATUM 20 · **A registered constant must name its SAMPLE SIZE, not only its population.**

The existing rule — *"every constant in a registration names the population it was measured
on"* — is insufficient. `IOU_IDENTITY_BOUND` named its population correctly and was still
invalid, because it was a **maximum over a sample** and a maximum over a sample **gets stricter
as the sample grows.** Such a constant is a defect whose fuse is study size: it passes on the
data that produced it and fails later, on more data, for no reason that is an error.

**Rule: a constant derived as `max(observed)` is a MEASUREMENT, never a BOUND.** If it gates
anything, the derivation must be written down and checked, and the gate must compare against the
derivation.

## 🔴 ERRATUM 21 · **§14's multiplicity correction used a normal approximation.**

`FINDINGS-SPADE.md` §22. A continuity-corrected normal approximation stood in for `binom.cdf`
on a Binomial(50, 0.95), where `np(1−p) = 2.5`. Holm ×72 on the leading cell is **0.2296, not
0.043**; **no cell survives at α=0.05**; "roughly seven at p<0.10 expected by chance" is
**2.72** against an observed 2.

The four measured containment figures reproduce exactly, and **the registered kill still
fired** — it is a decision rule, not a hypothesis test. Withdrawn: *"one of the four failures is
statistically real."*

**Design consequence, to be settled BEFORE any further containment sweep is registered:** at
n=50 and p=0.95, discreteness means a cell at 45/50 **can never** reach p<0.10, and after Holm
×72 even 42/50 cannot reach 0.05. **The sweep cannot detect what it was built to detect. More
seeds per cell, not more cells.**

## 🔴 ERRATUM 22 · **"Ordered by grid range" is wrong.**

Ceiling exceedance is **not** monotone in a family's response range: hartmann6's range (0.92112
at d=6) exceeds rosenbrock's (0.85290) with **1/30th** the exceedance. What is monotone, across
all five families including hill, is **max `tau_q`** — ackley 0.16159, hartmann6 0.56612, hill
0.93129, levy 0.95996, rosenbrock 0.98631. Since `tau_max` is a function of `(gamma, sigma)`
alone, exceedance can only track **where the prevalence quantile sits**, not the family's range.
Verified from the runners' own logs, independently of the census file.

**Two census provenance defects**, immaterial to the 384-cell arithmetic but recorded:
`above_ceiling` is a **majority vote** (`n_above * 2 > len(taus)`), which collapses to the
strict test only at `n_landscapes = 1` — 4 hill rows read `False` with ≥1 landscape above; and
**all 8 ackley rows in the τ source are `sensitivity: true`** while `ceiling_census()` applies
no sensitivity filter, so the "ackley 0%" column has a different provenance from the other four.

## 📌 P6 · **Cells 1+2 COMPLETE. Cells 3 and 4 NOT run.**

`results/p6-families.json` — 8 cells, 2,000 campaigns, 48,000 rows, **gate failures 0**.
Registered family order (hartmann6 → levy → rosenbrock → ackley) at `(6, 0.25)` and `(6, 0.10)`.
**2 h 10 m**, against a registered ~14 h; the per-arm timings behind that estimate were measured
on a machine in heavy swap and are ~5× pessimistic. **Re-estimate for cells 3+4: ~2 h, not ~14 h.**

**The registered cell order is what makes stopping after cells 1+2 coherent. It does not make it
complete.** `(8, 0.25)` and `(8, 0.10)` remain unregistered as run.

**Ranking convention, enforced:** `plate1_only` is excluded from every ranking
(`never_rank_separately` — it **is** `lhs` at 48 wells; including it makes `lhs` a second arm).
It was included in the first cut of the headline and had to be redone.

---

# Version C — registered 2026-08-22, before `run_versionc_gate.py` produced a number

Successor to `docs/SPADE-SPEC.md`. Runs as a **parallel track** to the outstanding
evaluation work; the ownership boundary is the spec's §7 and is honoured here — nothing in
this block edits `replay.py`, `campaign.py`, `surrogate.py`, `oracles.py`,
`torch_oracle.py`, or any committed `results/` file.

## C0 — THE GATE. Rule P at σ_rel = 0.10, all arms. Analysis only, no new campaigns.

**Registered before the runner existed.** Version B ranks 1st–3rd of 12 on the
design-space map at (d=6, σ=0.10) and **10th–11th of 12 on regret at the same cell**,
losing to qLogNEI by 0.045 — more than twice SESOI. Two worlds are consistent with that:

* **identification** — rule A nominates the best *noisy* reading, and a spread design has
  more mediocre wells that can draw lucky noise. A posterior-mean terminal rule closes it
  for free and §2's trust region solves a problem that does not exist.
* **search** — SPADE genuinely does not look where the optimum is. No terminal rule
  repairs that and §2 is required.

**Do not build §2 until this returns.** §1 and §3 are independent of it.

### The prediction, written before looking

Under a posterior-mean terminal rule, regret is governed by how well the posterior
localises the argmax. For a peak of local curvature `c`, a posterior mean error `s`
displaces the argmax by `r ≈ √(s/c)`, giving regret `≈ c·r² ≈ s`, and `s ≈ σ/√n_eff`:

```
regret_P  ≈  sigma / sqrt(n_eff)
```

At σ=0.10 with `n_eff ≈ 1.4` this gives **regret_P ≈ 0.085**. Rule-A reference points at
that cell: qLogNEI 0.0808, qLogEI 0.0874, `doe` 0.0892.

### The branch — `run_versionc_gate.gate_branch`, applied to `versionb` by name

| outcome | reading | §2 is |
|---|---|---|
| `regret_P ≤ 0.090` | identification artefact of rule A | **not built** |
| `regret_P ≥ 0.110` | genuine search deficit | trust region required |
| between | inconclusive | built as an **arm**, not as the method |

Applied to `versionb` **by name**. Reading the best arm's number would let the gate fire
on whichever arm happened to win, which is a different and much easier question.

### The gate on the gate

`|Δ| = 0` exactly, **double-gated** where two committed sources exist:
`p3-k6-d6-s010.json` for all twelve arms, `e2-grid.json` independently for seven.
`plate1_only` is cross-gated through its `lhs` alias and is **not** an independent arm.
A single failure aborts. No tolerance is introduced.

**Correction to a prior registration, stated rather than assumed.** P2 recorded the three
Version B arms as *"ungatable in principle — no committed comparator exists and none ever
will."* That was true when no file existed. `p3-k6-d6-s010.json` is now that file, and
what is checked is seed determinism — precisely the guarantee P2 says those arms have.

**Kernel arms carry their unresolved provenance.** `qlogei-add` / `qlogei-addonly` are
gated here against p3's committed column. That is a **reproduction check and not a
resolution of P1**; the 2,800-row re-score deciding VALIDATED vs WITHDRAWN has not run,
and every row of those arms carries that caveat so a determinism check cannot read as a
provenance answer.

### Also validate the model, not just the number

`n_eff` is emitted per campaign and `regret_P` is regressed on `σ/√n_eff`. **If the slope
is not near 1 and R² is not high, §2.2's well-count formula `n_required = (σ̂/r*)²` has no
basis and must be replaced by empirical calibration** — a finding about §2.2 whichever way
the branch falls. Section 0 registers this across **both** σ; the gate run is σ=0.10 only,
so `both_sigma` is reported as a field and a one-sigma fit is never printed as the
registered one.

## C1.2 — split-sample conservative estimate

`conservative_estimate` keeps the largest of 64 Vorob'ev quantiles whose containment —
measured on the draws — reaches α, then reports that same containment. A **maximum over 64
noisy estimates, scored on the draws that selected it**, and the bias peaks when candidates
are near-tied, which is the high-γ corner where §14's four sub-nominal cells sit.

`vorobev.conservative_estimate_split` selects on the first half and scores on the second.
At 1,024 draws the selection is **bit-identical** to the committed 512-draw estimator, so
a difference against the committed column is attributable to the estimator alone.

**The two halves must be drawn sequentially.** Measured: `randn(n,1024)[:, :512]` is *not*
`randn(n,512)` from the same seed — torch fills in memory order — so drawing 1,024 at once
would silently change every committed `ce_*` column. Two sequential `randn(n,512)` calls
leave the first block bit-identical.

**Registered prediction:** the four §14 failures move toward or above nominal. If they do,
the certificate held and the estimator failed. If not, the certificate genuinely degrades
with assurance and Version C says so. Cross-checks against F3 on the evaluation track.

## C1.3 — the columns that blocked the error-volume metric

`versionb.json` and `k6b-conservative*.json` carry `ce_vol` but **no false-inclusion rate
and no prevalence**, and `calibration.error_volumes` needs all three. So the primary
error-volume metric has never been computable on a **conservative set** at all.
`versionc.conservative_columns` adds `true_frac_above_tau` and `ce_fi_{α}` and the derived
volumes. The **symmetric difference** is reported, never type I alone, which read by itself
ranks silence first.

*For the record:* the pred/latent five columns already exist in `p2-versionb-gamma.json`
and `p3-k6-d6-s010.json`. They are absent from `versionb.json` because `run_versionb.py`
has no `GAMMA`, deliberately, per its own line 74. **No γ is introduced there.**

## C3.2 — the detector statistics, and one specification discrepancy

Six statistics, all from plate 1, **no oracle access** — architecturally, not by
convention: no function in `boec.versionc` accepts a `truth` argument.

**§3.2's first bullet is wrong as written.** It reads *"connected components of
`{x : LCB(x) ≥ max LCB}`"*. No point other than the argmax can have an LCB above the
largest LCB, so that set is a single point, its component count is **always exactly 1**,
and it cannot detect anything. §2.3 defines the trust region as `{x : UCB(x) ≥ max LCB}` —
the plausible-optimum set — which is the object with a meaningful component count and is
what is implemented.

**Two limits, pinned rather than tuned out.** `additive_share` is binned, so it is biased
downward when bins are coarse relative to the wiggle. Component count is
resolution-dependent: a region sparser than the grid meant to resolve it fragments, and
correctly so — measured at within-ball NN distance 0.1131 against a grid's own 0.0932.
**Any threshold fitted on either must be fitted at the grid and bin count the detector
will run at**, or the detector reads its own resolution rather than the landscape.

## C3.3 — NOT YET FROZEN

The rule and its threshold are **not** registered here, because they must be fitted on
hill / levy / rosenbrock first and no fitting run has happened. **No threshold appears in
`boec.versionc`** so that none can be adjusted after the held-out scoring. When the fit
runs, the rule is frozen in this file and committed **before** hartmann6 and ackley are
scored, and they are scored **once**.

**Protocol hazard, stated in advance.** Version C's performance on hartmann6 depends on
the detector and the detector is scored on hartmann6. Both are measured on the same single
pass. If the detector misfires, that is a Version C result, not a reason to refit.

## C4 — connected-component design spaces

`D_γ` is already a mask; its components are labelled and reported per component. **The
single-box number is carried on every row** (`box_vol_all_components`) so the committed
comparison stays intact and the difference between the two is visible. Connectivity is a
k-NN graph on the **full grid** (k = 2d, the lattice coordination number), of which the
mask selects an induced subgraph — a graph over the masked points alone would join each
point to its k nearest survivors however far away and return one component for any mask
larger than k. Gated against `scipy.ndimage.label` on a lattice in the regime where the two
definitions provably agree, and the boundary case where they do not is documented.

## Kill conditions — registered before any Version C arm is scored

| # | condition | consequence |
|---|---|---|
| **K-C2** | containment at γ=0.50 falls below 0.940/1.000/1.000 | **HALT.** The trust region imported `doe`'s failure mode |
| K-C1 | `versionc` does not reach `r*` at σ=0.10 | parity goal fails; report the residual gap and its cause |
| K-C3 | symmetric-difference volume worsens >10% vs Version B at γ=0.50 | ship Form 1 |
| K-C4 | `versionc` does not beat `versionc_fixed_m` | adaptive `m` is decoration; ship the fixed split |
| K-C5 | `versionc` does not beat `versionc_random` | criteria are not earning their place, only the wells are |
| K-C6 | split-sample CE does not move the four §14 failures toward nominal | certificate genuinely degrades with assurance; state as a limit |
| **K-C7** | detector does not separate held-out families | **ship without Stage 0** |
| K-C8 | `versionc` does not beat `versionc_nodetect` on hartmann6 | Stage 0 detects correctly but the response does not help |

**K-C2 is the hard stop.** The others narrow the claim; K-C2 ends it.

## What Version C may not claim

* superiority over BO on regret at σ=0.10 — **parity is the goal and parity is the claim**
* a Hartmann win. Q53 already measured the loss; Version C **declares** it
* anything about calibration until the evaluation track's scope gap closes
* that the trust region improved the certificate — Version B's `plate1_only` matched
  `versionb` on containment at every cell, so **containment is a floor that does not rank
  arms**

## Defect found while building this block, not fixed here

`scripts/run_fix1_terminal_rule.py:170` calls
`run_versionb._two_plate(orc, DIM, seed, mu_max, True)` and unpacks three values. That
function now takes `mode: str` and returns four, so **Fix 1 raises at HEAD and can no
longer reproduce its own committed file.** `results/fix1-terminal-rule.json` is unaffected
— it was produced before the signature changed — but the runner cannot regenerate it.
Flagged for the evaluation track, whose file it is. `run_versionc_gate.py` does not copy
that path; every arm goes through `replay.regenerate`'s builder hook as `run_p3_cells.py`
does.

## 🔴 ERRATUM 23 · **"24 of 24" is "18 of 18 rankable", and the count was never good evidence.**

`FINDINGS-SPADE.md` §24. The committed file always said so:
`f2-error-volumes.json · decision.rankable_cells = {type_I: 14, type_II: 18, total: 18}`.
Six of 24 cells have **no ranking** — every arm ties to within 1e-15 — and counting a cell with
no ordering as a disagreement is how 24 arose. Corrected at three sites in `FINDINGS-SPADE.md`
(§4.2 heading, the summary table, conclusion 3). **Two further "24 of 24" occurrences are a
DIFFERENT quantity** — the `doe`-vs-`lhs` contrast being significant in 24 of 24 cells — and are
correct as they stand. Do not "fix" them.

**More importantly, the count is near-vacuous.** Two independent random orderings of 8 arms
coincide with probability 1/40,320. "0 of 18 exact agreement" is what near-identical metrics
would also produce. `analyse_f2_error_volumes.py` says this in its own source and it was quoted
as a headline anyway. **It is no longer offered as evidence.**

## 🔴 ERRATUM 24 · **The ρ ≈ 0 grounds for superseding AUC do NOT replicate. The sign structure inverts.**

Per-cell Spearman(−AUC, volume), K6 vs the fresh P6 cells:

| metric | K6 | P6 |
|---|---|---|
| type I | **+0.392** [+0.270, +0.514] | −0.038 [−0.131, +0.054] |
| type II | −0.007 [−0.193, +0.180] | **+0.248** [+0.151, +0.345] |
| symmetric difference | +0.062 [−0.143, +0.267] | **+0.295** [+0.198, +0.393] |

**Exact reversal**, on 92 cells across four families. *"The two orderings are close to
unrelated"* holds on K6 and fails on P6.

**ρ = +0.071 is verified and was always fragile:** `spearmanr` over **n = 8 arms**, p = 0.87,
quoted with no `n` and no interval.

**The supersede decision STANDS**, on two grounds that survive and are not rank correlations:
the **arm-level reversals** (`doe` AUC-best in 27 of 92 P6 cells and symmetric-difference-worst
in 36 of 92; type I read alone ranks certifying-nothing first) and **coverage** (6,000 of 6,000
scorable rows vs 2,553 under `fi_pred`).

**`results/f2-ce-error-volumes.json` must not be cited for any arm ranking** — it carries no
`auc_pred`, and its own `like_for_like_across_arms: false` records that B3 scores `doe` on a 4-D
active subspace, so prevalence differs by arm in 198 of 200 cells.

**The general lesson, for the third time this week: a result measured on Hill described a
property of Hill.** Any claim not yet re-measured off Hill should be read as Hill-conditional
until it is.

## C3.3a — the fit set is SINGLE-CLASS, and that changes what the rule can be

**Measured, not anticipated by the specification.** §3.3 says *"fit the rule and its
threshold on hill, levy, rosenbrock ONLY"* and *"score ONCE on hartmann6 and ackley"*.
Checked against the committed Q53 table: **levy is null at all four cells (−0.0002,
+0.0133, +0.0016, −0.0058) and rosenbrock is null at all four (−0.0019, …, +0.0067).**
Hill ties. So **every family in the fit set is on the *same side* of the boundary**, and
the two held-out families are the entire other side.

**Consequence: a discriminative threshold cannot be fitted on the fit set.** There is no
contrast in it to fit against, and "separation" cannot be measured there at all — a
two-class statistic needs two classes. Fitting one anyway would require looking at
hartmann6 or ackley, which is the single thing §3.3 exists to forbid.

**The only protocol that survives.** The rule is a **one-class (novelty) boundary**:

```
DECEPTIVE  if a frozen statistic falls OUTSIDE the range observed
           across hill / levy / rosenbrock on the fitting run
UNIMODAL   otherwise
```

This is fittable **without ever seeing a deceptive landscape** — it needs only the tie
families — and it is frozen before the single scoring pass. The scoring pass then measures
whether hartmann6 and ackley fall outside that boundary, which **is** K-C7's test and is
allowed to happen exactly once.

**What this costs, stated up front.** A one-class boundary has no fitted false-positive
rate against real deceptive landscapes, so its power is unknown until the single scoring
pass, and that pass cannot be repeated to improve it. If it misfires, K-C7 fires and
Version C ships without Stage 0 — which §3.6 already registered as an acceptable outcome
and a smaller but real finding.

## C3.2a — two of the six candidate statistics are non-viable as written

Both found by measurement while building the fitting runner, before any threshold existed.

1. **`{x : LCB(x) ≥ max LCB}`** — satisfied by the argmax alone, so its component count is
   always exactly 1. Replaced by §2.3's plausible-optimum set `{x : UCB(x) ≥ max LCB}`.
2. **`n_local_maxima`** — peaks whose LCB clears the *second-highest UCB*. **Identically
   zero** at the real operating point (40 wells, d=6, σ=0.10, 20,000-point grid) on both
   hill and levy. At 0.49 neighbours per lengthscale no LCB comes near a rival's
   optimistic bound. `n_peaks_raw` — the same peaks with no confidence bar — does vary
   (135 and 149 on those two fits) and is the usable form.

Both zeros are pinned as **alarms** in the test suite rather than as targets: if the budget
or noise level ever moves far enough that they fail, the candidates have become viable and
the docstrings have stopped being true out loud.

**Four candidates remain viable** and are what the one-class boundary will be fitted from:
`n_components_plausible`, `additive_share`, `additive_refit_residual`,
`ard_separation_ratio` — plus `n_peaks_raw` and `lengthscale_over_width`.

## 🔴 ERRATUM 25 · **§10's scope gap is mostly closed. "1 of 8" is stale, and the α\* half is FALSE.**

`FINDINGS-SPADE.md` §25. Version B arms are now in the source of **5 of 8** Phase 2–4 runners
and the committed results of **4 of 8**. `results/p4b-alpha-star-anomaly.json` carries
**`n_arms: 12`** including all three Version B arms — so *"the α\* investigation omitted every
SPADE arm"* is **no longer true**. **ρ(α\*, regret) = −0.3916 [−0.6643, −0.0839]** at twelve
arms, against the provisional nine-arm −0.3667.

**Errata 11 and 13 are CLOSABLE** — both were marked PENDING on the grounds that the twelve-arm
figures did not exist. They do.

**Correction to the registration's own wording (`:6469`):** *"F1's three Holm upgrades are all
on `alpha_star`, all on Version B contrasts"* — **all three are Version B contrasts, but only
TWO are on `alpha_star`.** The third is on **`auc`, a VALIDATED metric**
(`f1-dual-n.json · status_changes_by_metric_class = {validated: 1, model-internal: 3}`). This
document already said **two** at `:6585` and contradicted itself at `:6469`.

## 🔴 REGISTRATION LIMIT · **P6 tests SPADE's MAP off hill, NOT its certificate.**

**Stated because Part IV is easy to misread as more than it is.**
`results/p6-families.json` carries **no `alpha_star`, no `ce_contain_*`, no `ce_empirical_*`,
no `vorobev_*`** — zero occurrences in any checkpoint. The conservative excursion estimate, which
**is** the SPADE certificate, is not computed anywhere in the cross-family programme.

> **SPADE's certificate has still been measured at exactly one (family, d, σ) point in the
> entire project: hill, d=6, σ=0.25.** Four families and eight cells later, unchanged.

P6 also excludes hill and is d=6 only. **The map half of the scope gap is closed; the
certificate half is not.** That is precisely the gap §22 says the containment sweep lacks the
power to close and F3 was registered to attack.

## 🔴 **P7 HAS PRODUCED NOTHING. The "restart at 10 arms" left no trace.**

`results/p7-murphy.json` **does not exist.** The log holds **two aborted runs, both at the OLD
six-arm tuple** (`arms=('doe','qlogei','qlognei','lhs','sobol','random')`), the second logging
zero campaign lines. `OVERNIGHT-LOG.md:1624` records *"P7 is restarting at 10 arms"* — **no such
run reached disk.** The source is at 10 arms; nothing has been run from it.

**This is the "8/50" in the handoff's unfinished table, and 8/50 overstates it: the correct
state is 0/50 at the registered arm set.** Murphy calibration is the one Brier component AUC
cannot see, and SPADE's entire claim is a calibrated statement — so this is the single largest
outstanding item in Phases 2–4, ahead of the d=8 cells.

## 🔴 ERRATUM 26 · **The CIRCULAR statistic was pooled too, at five sites the F4 sweep missed.**

The F4 un-pooling swept `ce_empirical` and left **`ce_contain` — the circular in-sample
statistic — `tau_frac`-pooled in five places with no withdrawal note**:
`K6-TECHNICAL-REPORT.md` §6.15's range table, its "note the ordering" passage, §3737's
eight-arm ranges and §4027's summary bullet, and `FINDINGS-SPADE.md` §4.8.

**Restating them per-cell STRENGTHENS every sentence they sit in**, which is why this is worth
doing rather than merely correcting:

| figure | pooled | **per-cell at `tau_frac = 0.60`** |
|---|---|---|
| `doe` `ce_contain` at nominal 0.95 | 0.9997 (n = **51**) | **1.0000 (n = 50)** |
| nominal 0.50 range, 8 arms | 0.5443–0.5998 | 0.5495 (doe) – 0.6094 (sobol), n=50 |
| nominal 0.80 range | 0.8640–0.8960 | 0.8681 (random) – 0.8960 (sobol), n=42–50 |
| nominal 0.95 range | 0.9605–0.9997 | 0.9605 (sobol, n=13) – **1.0000 (doe, n=50)** |

**The pooled `n` of 51 was fabricated from 50 campaigns at `tau_frac = 0.60` plus ONE at 0.75.**
Un-pooled, `doe` scores a **flawless 1.0000 over 50 campaigns** on the in-sample statistic while
its empirical containment **in the same cell** is **25/50 = 0.500**. A metric that is perfect on
an arm that is right half the time is a sharper indictment than 0.9997 was.

**At `tau_frac` 0.85 and 0.95 there is nothing to report at any alpha** — every arm empty in
every campaign, `n = 0`. At 0.75, `n` is 1, 1 and 2 for the only three arms with anything.
**Those `n`s are why the pooled version existed and why it had to go.**

## ✅ VERIFIED FROM COMMITTED ROWS · the two per-cell figures the evaluation queue asserted

| claim | measured |
|---|---|
| `doe` per-cell reads **0/50, 12/50, 25/50** | **exact** (`tau_frac = 0.60`, alpha 0.50 / 0.80 / 0.95) |
| `random` **1 of 7** at `tau_frac = 0.85`, alpha 0.50, **86% empty** | **exact** — 1/7 non-empty, 43 of 50 empty = 86% |

**And the wider audit result: all 156 per-cell containment figures already in the docs
reproduce from the raw rows at max \|Δ\| = 0.000e+00, at BOTH the n=50 and n=25 units, with 0
value and 0 `n` mismatches.** The seven `ce_empirical` sites the queue listed were **already
corrected in place**. The un-pooling work that remained was on the circular statistic, which
nobody had looked at.

## C3.3b — K-C7 is PREDICTED TO FIRE, from the fit set alone

**`results/versionc-detector-fit.json`** — 150 rows, hill / levy / rosenbrock, d=6, both
σ, 40-well plate 1, 20,000-point grid. **`results/versionc-detector-boundary.json`** —
the ranked statistics and the proposed boundary. **Nothing is frozen and nothing held out
has been scored.**

| statistic | support on the tie families | fires on | within-family ÷ pooled |
|---|---|---|---|
| `additive_share` | [0.1054, 0.8860] | **21.9%** | **0.88** |
| `additive_refit_residual` | [0.2868, 1.7130] | n/a | 0.87 |
| `n_peaks_raw` | [22, 600] | n/a | 0.81 |
| `n_components_plausible` | [1, 5] | n/a | 0.75 |
| `ard_separation_ratio` | [1.0010, 30.66] | n/a | 0.66 |

**`within-family ÷ pooled` = 0.88 means a *single* tie family alone spans 88% of the range
all three span together.** The statistic is dominated by seed-to-seed variation, not by
landscape class. A statistic that cannot order the families *within* one class cannot
separate that class from another, and a novelty boundary drawn on it has almost nothing
left to fire on: `additive_share`'s support leaves **21.9%** of [0, 1] outside.

> **Registered prediction, before the scoring pass: K-C7 fires.** Version C ships without
> Stage 0, plate 2 always uses the boundary allocation, and the claim is cut to *"the
> boundary exists and is deception-shaped"* — §3.6's outcome, which was registered as
> acceptable and as a smaller but real finding.

**Why this is worth having rather than merely disappointing.** The prediction is made from
the **fit set alone**. It does not consume the single look at hartmann6 and ackley, which
§3.5 says cannot be repeated. Learning that the rule is probably powerless *before*
spending that look is strictly better than learning it after — after, there is no second
pass in which to try a different statistic.

**Two diagnostics carry it, both computable with no deceptive example.**
`excluded_fraction` — a novelty rule fires only outside the support, so the attainable
range the support leaves over **is** the rule's power; `None` for unbounded statistics,
where a number would read as power it does not have. `within_family_share` — the mean
per-family support width over the pooled width.

**What would change the verdict.** A statistic with a materially tighter support on the tie
families. None of the six candidates has one at 48 wells; whether one exists at a larger
budget is a different question and is not answered here.

---

# 📌 REGISTRATION · **F3 REDESIGNED — the winner's curse inside `CE_alpha`, on BOTH axes**

**Registered 2026-08-22, before `scripts/run_f3_draw_sweep.py` exists.** Scope decision taken
by Joseph: **draws × seeds**, not the draws-only sweep originally registered.

## Why the registered design changed

**The original F3 was a draw sweep alone. Erratum 21 established it cannot detect the effect
it was built to detect.** At n=50, p=0.95 the exact binomial tail is:

| X/50 | 42 | 43 | 44 | 45 |
|---|---|---|---|---|
| exact tail | 0.0032 | 0.0118 | 0.0378 | 0.1036 |

**A cell at 45/50 can never reach p < 0.10**, and after Holm ×72 even 42/50 cannot reach 0.05.
A draws-only sweep would return four cells that still cannot be called, at four draw levels.

**At n=200, p=0.95, 180/200 gives an exact tail ≈ 0.007** — inside Holm ×72. That is the
difference between *cannot detect* and *can*. **The seeds axis is not a refinement; it is what
makes the experiment able to answer its own question.**

*(Recorded as a registered-design change with its reason, per the standing rule. The reason is
not "the first result was inconvenient" — it is that the original design's power was never
computed, and when computed it is insufficient by construction.)*

## The mechanism under test

`conservative_estimate` scans `n_rho` Vorob'ev quantiles and keeps the **largest** whose
containment, **measured on the draws**, reaches α. A **maximum over `n_rho` noisy estimates**,
then reported on the same draws that selected it — **anti-conservative by construction.** This
is the project's own optimizer's-curse result operating inside its safety metric.

**The bias should peak where the candidates tie.** At γ=0.99, τ_frac=0.60 the true set covers
**0.99916** of the box, so the quantiles collapse onto each other — and that is exactly where
§14's failures sit.

## Design

- **Cells:** the four §14 sub-nominal cells — (γ=0.99, τ_f=0.60), (γ=0.99, τ_f=0.75),
  (γ=0.95, τ_f=0.60), (γ=0.99, τ_f=0.85). Plus **(γ=0.50, τ_f=0.60) as a negative control**:
  the bias should be near-absent where the quantiles are well separated, and a sweep that moves
  there too is measuring something else.
- **Draws:** 512 → 1024 → 2048 → 4096.
- **`n_rho`:** 16 and 64. The bias is a maximum over `n_rho` candidates, so it must scale with
  `n_rho` if the mechanism is what we think.
- **Seeds:** 50 → **200**.
- **Arm:** `versionb` (SPADE). The certificate is SPADE's.

## Reported, per (cell, draws, n_rho, n_seeds)

`alpha_star`, `CE` volume, **empirical containment with its own `n`**, and the **EXACT binomial
tail** (`scipy.stats.binom.cdf`) — **never a normal approximation** (Erratum 21). Wilson
intervals on every proportion. Holm across the cells of the family, stated.

**Also reported: `conservative_estimate_split` on the same draws**, so the measured bias and
the cross-fit removal of it appear on the same row. Version C owns the split; this track owns
the measurement; **neither was designed to test the other, and the two answers are compared
explicitly.**

## Registered decision rule — written before any number exists

- **Containment rises toward nominal as draws increase, at n=200** → **the estimator failed,
  not SPADE.** The correction is itself a reportable result, and §14's kill is attributed to
  the estimator.
- **Containment flat in draws at n=200** → **the certificate genuinely degrades with
  assurance.** §14 stands and strengthens.
- **Bias scales with `n_rho`** → confirms the maximum-over-candidates mechanism specifically,
  as against any other draw-count effect.

**Kill:** if `versionb` containment falls below nominal at **γ = 0.50** at any draw count, that
is a different and worse event than the ladder failures, and the programme stops and reports it.

## Constants

**No constant in this runner may be derived as `max(observed)`** (Erratum 20). The only
tolerance is the exact binomial tail, which is computed, not fitted.

## Output

`results/f3-draw-sweep.json`. **`.gitignore` negation added in this same commit, before the
runner exists**, so the artefact cannot be silently ignored (the defect the gitignore's own
comments record twice).

## 🔴 ERRATUM 27 · **F3's own registration quoted a wrong tail. Caught by its test before the runner ran.**

The registration one commit earlier justified the seeds axis with *"at n=200, p=0.95,
180/200 gives an exact tail ≈ 0.007, inside Holm ×72."* **Both halves are wrong.** The exact
tail at 180/200 is **0.002665**, and ×72 it is **0.1918** — it does **not** survive Holm.

Caught by `tests/test_f3_draw_sweep.py::test_the_seeds_axis_is_what_makes_the_experiment_powered`,
written before the runner existed and run before it was launched. **A registration is not
exempt from its own standing rule** — *verify rather than accept any number handed to you,
including the ones in this document* — and the number was mine.

**The conclusion survives, and the correct arithmetic is stronger than the wrong one.** The
right comparison is the *same containment rate* at the two sample sizes, not an arbitrary count:

| n | X at §14's worst observed rate (0.840) | exact tail | Holm ×72 |
|---|---|---|---|
| 50 | 42/50 | 3.188e-03 | **0.2296 — cannot be called** |
| **200** | **168/200** | **6.798e-09** | **≈ 0.0000 — survives decisively** |

**The detection threshold at n=200 is 170/200 = 0.850** — the worst containment still callable
after Holm ×72. At n=50 there is no such threshold below 1.0: *nothing* is callable.

All three figures are pinned in the test, including 180/200 asserted to **fail**, so the wrong
number cannot return.

## 🔴 C1.2a — the cross-fit CANNOT move §14's failures, and K-C6 as written would misfire

**Found while reconciling C1.2 against the evaluation track's erratum 21. Proven, not
estimated.**

§1.2 registers: *"the four §14 failures move toward or above nominal. If they do, the
certificate held and the estimator failed."* And K-C6: *"split-sample CE does not move the
four §14 failures toward nominal → certificate genuinely degrades with assurance."*

**Those four failures are in `ce_empirical` — empirical containment against known truth**
(0.900 / 0.840 / 0.880 / 0.900 against nominal 0.95). The cross-fit selects on the first
half, which is **bit-identical to the committed 512-draw estimator**, so it returns the
**identical set**. Empirical containment is a function of `(set, truth, theta)` alone.
Identical set, identical truth, **identical number**.

> **The cross-fit repairs the model-internal containment and nothing else. It is
> structurally incapable of moving §14's failures.**

So **K-C6 would fire automatically and for the wrong reason** — not because the certificate
degrades with assurance, but because the estimator does not address that quantity. A kill
that cannot fail to fire tests nothing.

**Two things follow, and they are separable.**

1. **C1.2's own deliverable stands, restated honestly.** The cross-fit measures the
   selection bias in `ce_contain`, which is real and was previously unmeasurable because
   the number was circular. `ce_selection_bias_{α}` is that measurement. It is a statement
   about the **estimator**, never about the certificate.
2. **What would move `ce_empirical` is a different estimator** — selecting at a stricter
   `α'` chosen so the cross-fit's honest estimate reaches `α`. That changes the mask and
   therefore the empirical number. **It is not what §1.2 specifies and is not built here.**
   If the §14 repair is wanted, that is the object to register.

**And erratum 21 removes the effect this was aimed at anyway.** No §14 cell survives Holm
×72 at α=0.05; 2.72 cells at p<0.10 were expected by chance against 2 observed. So the
target of C1.2's prediction is **both unreachable by the estimator and not established as
real**. Recorded rather than quietly dropped.

**Power note, inherited from erratum 21.** At n=50 and p=0.95, `ce_empirical` moves in
steps of 1/50 = **0.02**. The selection bias measured on a correlated synthetic fixture is
**~0.003**. Even against the right quantity, a 50-campaign sweep could not resolve this
effect. The evaluation track's redesigned F3 (draws × seeds, n=200) is the design that can,
and **C1.2's re-score must run at that seed count or it repeats the defect erratum 21
names.**

## ✅ DECISION 3 RESOLVED · **The committed kernel rows are VALIDATED.**

`results/p1-kernel-gate.json` · **2,400 K6 + 400 K6b = 2,800 rows re-scored · metric
failures 0 · worst |Δ| = 0.000e+00 · VERDICT VALIDATED.**

They had been neither validated nor withdrawn for eight months while `q30-additive.json`,
the comparator Amendment A1 named, did not exist. It exists, the gate ran, and it passed
exactly.

**Declared scope reduction, disclosed rather than hidden:** PASS 3 deferred 100 campaigns at
σ ≠ 0.25 and says so in the output's `deferred_scope`. P3's (6, 0.10) cell covers the same
committed column through an independent code path.

## ✅ ERRATUM 22's TWO PROVENANCE DEFECTS · fixed additively, arithmetic proved unchanged

`ceiling_census()` now carries three new columns. **`above_ceiling` itself is NOT changed** —
`results/p6-ceiling-census.json` is committed against its current semantics and must stay
comparable — so the disclosure is beside it, not instead of it:

| column | what it says |
|---|---|
| `above_ceiling_strict` | `n_above > 0` — the strict test |
| `above_ceiling_rule` | `"majority: n_above * 2 > n_landscapes"` — names the vote in the row |
| `sensitivity` | whether the cell's τ rows are all `sensitivity: true` (ackley: yes; the other four: no) |

**Verified additive before regenerating**: 480 rows both, **3 keys added, 0 removed, 0 value
mismatches on every shared key.**

**The disclosed disagreement is exactly 4 rows, all hill, all vote=False / strict=True:**

| cell | landscapes above |
|---|---|
| hill d=8 p=0.25 γ=0.80 σ=0.25 | 1/25 |
| hill d=6 p=0.10 γ=0.95 σ=0.10 | 5/25 |
| hill d=8 p=0.10 γ=0.95 σ=0.10 | 4/25 |
| hill d=8 p=0.25 γ=0.99 σ=0.10 | 9/25 |

**File-wide: vote 150/480, strict 154/480. Non-hill 384 cells: 111/384 by BOTH tests.** The
headline figure is unaffected, which is what makes this a disclosure fix rather than a
correction — and the 4 rows are now visible instead of implicit.

---

# 📌 REGISTRATION · **Q59 MAP RE-SCORE — isolating screening from sub-box confinement**

**Registered 2026-08-22, before `scripts/run_q59_map_rescore.py` exists.**

## What the committed file already settles, and what it cannot

`results/q59-hartmann-no-screen.json` carries **`doe_unscreened`** — the only classical arm in
the repository with variation on **every** axis (a half-fraction face-centred CCD on all six
coordinates, 47 runs + 1 confirmation = exactly 48). That is what makes it the only available
way to isolate **screening** from **sub-box confinement**.

**On regret it is already decisive, and it runs opposite to the intuition behind Task 7:**

| σ | `doe_screened` rule_a | `doe_unscreened` rule_a | screen effect | Wilcoxon |
|---|---|---|---|---|
| 0.25 | 0.5623 | **0.7685** | **+0.2062** [0.1419, 0.2667] | 6.44e-05 |
| 0.10 | 0.5428 | **0.7502** | **+0.2074** [0.1615, 0.2519] | 1.38e-05 |

**The screen HELPS the classical arm on regret, by ~0.21 at both σ.** Removing it makes the arm
worse, not better. So the screen is not why `doe` loses to BO on regret — it is why `doe` is not
*further* behind. Part IV's claim is a **map** claim, and these are the two axes this project has
found disagreeing at every previous opportunity (§13, D20, §23.2).

**What the committed file CANNOT settle:** every arm in it carries only `rule_a` and
`oracle_best`. **No design matrix, no posterior, no map metric.** The question Part IV raises —
*does `doe`'s symmetric-difference failure survive when the classical arm does not screen?* —
is not answerable from the file and requires regeneration.

## Design

Regenerate `doe_screened` and `doe_unscreened` at hartmann6, d=6, both σ, 25 seeds, through
**`scripts/run_q59_hartmann_no_screen.py`'s own design code, imported, never reimplemented** —
a second copy of the CCD construction would be a second experiment.

Score both under **Part IV's metrics**: `auc_pred`, `auprc`, Brier, IoU, false inclusion,
**type I / type II / symmetric difference**, `sup_err`, `grid_r2`, emptiness, and the ceiling
flag — the same `map_row` path P6 uses, so the numbers are comparable to
`results/p6-families.json` cell-for-cell.

**Gate:** the regenerated `rule_a` and `oracle_best` must reproduce the committed Q59 columns at
**|Δ| = 0 exactly**. Q59's own gate against `d20-rescore.json` is at `worst_abs_delta = 0.0`, so
there is a committed column to hold this to and no excuse for a tolerance.

## Registered decision rule — written before any number exists

- **`doe_unscreened` still loses the symmetric difference to the spread arms** → screening is
  **not** the mechanism; the classical arm's map failure is about the response-surface model,
  not the 6→4 cut, and Part IV's caveat 1 is **discharged**.
- **`doe_unscreened` closes the gap on the symmetric difference** → screening **is** the
  mechanism, Part IV's headline is a screening result as claimed, and the confound was real.
- **Either way the regret direction is already known** (the screen helps), so a map result that
  runs the other way is the fourth independent instance of this project's map/regret split and
  is reported as such.

## What this cannot reach, stated rather than discovered later

**d = 8 is arithmetically impossible.** A full second-order model needs `C(d+2,2)` terms — 28 at
d=6, **45 at d=8** — and no face-centred CCD lands on 48 wells at d=8; the only design small
enough carries 35 runs for a 45-term model, fewer observations than parameters. **An unscreened
classical pipeline does not exist at d=8 within the shared budget.** That is not a limitation of
this re-score; it is the reason the 6→4 screen exists at all, and it means **Part IV's d=8 cells
can never have this confound isolated.**

**Output:** `results/q59-map-rescore.json`, with its `.gitignore` negation added in this commit.

## ✅ Q59 MAP RE-SCORE · **RESOLVED. The registered "screening is NOT the mechanism" branch fired.**

`results/q59-map-rescore.json` · 50 campaigns · 2,400 rows · **0 gate misses** (regenerated
`rule_a`/`oracle_best` at |Δ| = 0 on all 100 arm-campaigns). Full account in
`FINDINGS-SPADE.md` §26.

**`doe_unscreened` still loses the symmetric difference to every spread arm above SESOI** —
lhs +0.0264 (p_holm 7.81e-12), sobol +0.0270 (5.38e-13), random +0.0211 (7.52e-11). Turning
the screen off does not rescue the classical arm's map.

**But the screen accounts for a consistent ~30% of the gap** — 30.5% / 31.3% / 27.7% against
lhs / sobol / random. **The defensible statement is neither "the screen is the mechanism" nor
"the screen is irrelevant": the 6→4 cut costs the classical arm about a third of its map
deficit and the response-surface model costs the other two thirds.** Part IV's headline
survives with its magnitude cut by roughly a third and its sign unchanged.

**Reported, not resolved, per Q20 §2:** `doe_unscreened` − `doe_screened` has median +0.0036
with a CI spanning zero but Wilcoxon p_holm = 1.22e-04, and the **means run the other way**
(0.3265 vs 0.3607). Median and mean have opposite signs — the paired differences are strongly
skewed. The within-arm comparison is therefore not load-bearing; the cross-arm contrasts are.

**Permanent limitation, recorded so it is not rediscovered:** an unscreened classical pipeline
is **arithmetically impossible at d=8** within 48 wells (45 second-order terms, no
face-centred CCD lands on 48; the only design small enough has 35 runs for 45 parameters).
**Part IV's d=8 cells inherit this confound permanently and no future run can remove it.**

## ✅ TASK 1 / §10 SCOPE GAP · **CLOSED. P7 ran at the registered arm set.**

`results/p7-murphy.json` — **500 campaigns, 12,000 rows, all 10 arms including all four
Version B arms.** P7 had produced nothing before today; both its logged runs were at the OLD
six-arm tuple and the second logged zero campaigns, so the handoff's "8/50" was really
**0/50**. Full account in `FINDINGS-SPADE.md` §27.

**`Brier = calibration − refinement + uncertainty` verified on all 12,000 rows: 0 violations,
worst residual 2.220e-16.**

### 🔴 The finding, and it does not flatter SPADE

**SPADE ranks 5th, 6th and 7th of 9 on CALIBRATION** — the component the decomposition was
promoted to primary to expose, and the one SPADE's whole claim rests on — **while ranking 1st,
2nd and 3rd on REFINEMENT.** Its regions are the sharpest in the study and its probabilities
are below average in reliability.

**AUC ranks `versionb` FIRST (0.7583).** The metric that cannot see calibration puts SPADE at
the top; calibration puts it in the bottom half. That is precisely the disagreement the Murphy
split was adopted to catch, and the first thing it does with SPADE in scope is catch it.

**Not a kill.** SPADE's calibration (0.0353–0.0385) sits inside the same band as every other
non-`doe` arm (0.0289–0.0443) and it wins refinement outright. **The defensible statement is
that SPADE buys SHARPNESS and does not buy RELIABILITY**, and every claim resting on the
calibrated half must now carry that.

### `doe`'s calibration is off the scale

**0.22959 against 0.04425 for the next worst — 5.2× worse than any other arm, 7.9× worse than
the best** — and last on refinement too. One arm accounts for nearly the whole spread of the
metric.

### `sobol` takes a FOURTH validated metric

Best calibration, on top of best Brier, best empirical containment, and best mean
symmetric-difference rank on three of four families — **while placing last on α\* at three of
four thresholds.** Four validated metrics against one model-internal metric, pointing opposite
ways on the same arm. **This is what unblocks Task 8.**

### Registered A5 check fired

Rankings differ at **23 of 24** predictive cells (24 of 24 latent); **6 of 371** inverted pairs
survive Holm at n=25 (6 at n=50); Spearman ρ across cells min −0.283, median −0.075,
max +1.000; **371 of 864 pair inversions.** Reporting Brier alone hides which half an arm wins.

## ⭐⭐ C0 RESULT — the gate returns **IDENTIFICATION_ARTEFACT**. §2 is NOT built.

**`results/versionc-gate-s010.json`** — 600 rows, 12 arms × 50 keys, **gate clean at
|Δ| = 0 exactly**, double-gated against `p3-k6-d6-s010.json` and, for seven arms,
independently against `e2-grid.json`. `results/versionc-gate-analysis.json`.

**`versionb` mean rule-P regret = 0.0792**, against the registered branch at 0.090.

| arm | rule A | rule P | A − P | 95% CI | p Holm | n_eff |
|---|---|---|---|---|---|---|
| `qlogei-addonly` | 0.0627 | **0.0627** | −0.0000 | [−0.0098, +0.0108] | 0.8482 | 20.30 |
| `qlognei` | 0.0808 | 0.0629 | +0.0179 | [+0.0106, +0.0251] | 0.0000 | 25.38 |
| `qlogei` | 0.0874 | 0.0703 | +0.0171 | [+0.0065, +0.0280] | 0.0106 | 21.96 |
| `lhs` / `plate1_only` | 0.1027 | 0.0765 | +0.0263 | [+0.0129, +0.0393] | 0.0011 | 10.76 |
| **`versionb`** | 0.1261 | **0.0792** | **+0.0468** | [+0.0304, +0.0623] | 0.0000 | 13.98 |
| `doe` | 0.0892 | **0.2728** | **−0.1835** | [−0.2307, −0.1387] | 0.0000 | 31.38 |

**The σ=0.10 deficit was an identification artefact of rule A.** SPADE moves from 10th of
12 under rule A to within SESOI of every arm except `doe` under rule P. Paired, on
`(instance, seed)`:

| contrast | Δ | 95% CI | p | |
|---|---|---|---|---|
| `versionb` − `qlogei-addonly` | +0.0165 | [+0.0029, +0.0314] | 0.0088 | **within SESOI** |
| `versionb` − `qlognei` | +0.0163 | [+0.0031, +0.0320] | 0.1355 | **within SESOI** |
| `versionb` − `qlogei` | +0.0090 | [−0.0034, +0.0230] | 0.3326 | **within SESOI** |
| `versionb` − `lhs` | +0.0028 | [−0.0137, +0.0200] | 0.9695 | **within SESOI** |

Against `qlogei-addonly` the Wilcoxon and the bootstrap **agree** that a real difference
exists and that it is **below SESOI**. Per Q20 §2 both are reported: detectable, not
material.

**`doe` inverts at a second cell.** D20's reversal was measured at σ=0.25 (rule P 0.1993
against rule A 0.0892). At σ=0.10 it is **0.2728 against 0.0892 — worse, not better.** An
arm whose `grid_r2` is −6.19 is punished by a terminal rule that reads its own response
surface, and the asymmetry now holds at both noise levels.

### 🔴 But the MODEL behind §2.2 is dead, and the prediction was right by coincidence

```
regret_P ~ sigma/sqrt(n_eff):   all arms   slope -1.7347   R2 0.0309   n=600
                                minus doe  slope +0.5124   R2 0.0112   n=550
```

**Excluding `doe` flips the sign and leaves R² ≈ 0.01.** This is not a `doe` artefact —
the model explains about **one percent** of the variance either way.

**And the agreement that fired the branch is a coincidence of two cancelling errors.** §0
assumed `n_eff ≈ 1.4` and predicted `0.10/√1.4 = 0.0845` against a measured **0.0792** —
excellent agreement. But **measured `n_eff` is 13.98, not 1.4**:

| arm | n_eff | σ/√n_eff | measured regret_P | ratio |
|---|---|---|---|---|
| `sobol` | 9.56 | 0.0323 | 0.0823 | 2.54× |
| `versionb` | 13.98 | 0.0267 | 0.0792 | **2.96×** |
| `qlogei-addonly` | 20.30 | 0.0222 | 0.0627 | 2.82× |
| `doe` | 31.38 | 0.0179 | 0.2728 | 15.28× |

`n_eff` was underestimated by ~10× and the model under-predicts by ~3× — and √10 ≈ 3.16.
**The two errors cancel almost exactly.** The number was right; the mechanism was not.

**What this does and does not overturn.** The branch is a decision rule on the *measured*
`regret_P`, which is gated and real, so **the branch stands and §2 is not built**. What
falls is **§2.2's allocation rule**: `n_required = (σ̂/r*)²` rests on the σ/√n_eff model,
that model is not validated, and §2.2's well-count formula therefore **has no basis and
would have to be replaced by empirical calibration** — as §0 registered in advance,
whichever way the branch fell.

**One-sigma caveat, carried.** §0 registers the regression across both σ. This is σ=0.10
alone; `fix1-terminal-rule.json` carries `regret_p` at σ=0.25 but no `n_eff`, and
`run_fix1_terminal_rule.py` raises at HEAD. The two-sigma version needs the gate runner
re-run at σ=0.25.

### What Version C now is

**Form 1 only: §1 + §3.** Plate 1 unchanged, plate 2 = 8 boundary wells, rule P as the
terminal rule, split-sample CE, connected-component design spaces. No trust region.

## ✅ TASK 8 · **α\* DECLARED. Option (a) taken and registered.**

`FINDINGS-SPADE.md` §28. §15 declined to resolve α\* on the evidence then available; three
things changed. §24 removed one ground for the refusal (the ρ≈0 finding does not replicate),
§25 put SPADE inside the α\* investigation for the first time, and §27 added **calibration** —
the validated metric that speaks directly to what a certificate claims.

**The two extremes are exactly inverted**, same cell (hill, d=6, σ=0.25), 9 arms:

| | α\* | calibration |
|---|---|---|
| `doe` | **0.7875 — rank 1** | **0.22959 — rank 9** (5.2× worse than any other arm) |
| `sobol` | **0.5275 — rank 9** | **0.02893 — rank 1** |

α\* against calibration ρ = **+0.4667**, against Brier **+0.2333** (both lower-is-better, so
positive means α\* tracks **badness**), against regret **−0.5667** (tracks quality). **None is
significant at n = 9 arms and the declaration does not rest on them** — it rests on the
mechanism and the extremes.

> **α\* is a functional of the fitted posterior and nothing else. It measures how confidently a
> model asserts an excursion, not whether the assertion is right.** An arm that is badly
> miscalibrated but confident scores highest, which is exactly `doe`.
>
> **α\* is NOT a metric of certificate quality and is not reported as one.** Retained, labelled
> MODEL-INTERNAL, as a measure of *posterior confidence* — a real and different thing. **No
> ranking, no claim and no kill condition may rest on it.**

**This closes the §4.2 two-arm anomaly as well**, and shows it was never two: `random` scores
2nd–3rd on α\* with the worst regret, `sobol` scores last with the best containment, and both
are the same fact — **α\* rewards confident assertion and neither arm's confidence tracks its
correctness.**

**Still open, and now the ONLY open question about α\*:** *why* the posterior is confident
where it is wrong (option (b), the spatial-coherence test). **Not required for any claim in
the record, because nothing rests on α\* any more.**

## 🔴⭐ F3 RESOLVED · **§14's kill was an ESTIMATOR ARTEFACT. The registered branch fired.**

`results/f3-draw-sweep.json` — 250 campaigns, 3,000 rows, 0 crashes.
`FINDINGS-SPADE.md` §29. Decision rule written before any number existed.

**Registered branch: *"containment rises toward nominal with draws → the estimator failed,
not SPADE."*** It fired. All four §14 cells reach at-or-above nominal by **1,024 draws**; the
worst goes **0.860 → 0.980** and flattens. **`p2-versionb-gamma.json` was produced at
`N_DRAWS = 512`.**

At 4,096 draws with **n = 200** — the size Erratum 21 showed was needed — **no cell is
significantly below nominal**, not even before multiplicity correction.

### 🔴 A REGISTERED PREDICTION FAILED, and is recorded as failed

The registration predicted *"bias scales with `n_rho` → confirms the maximum-over-candidates
mechanism."* **It does not scale: `n_rho` 16 and 64 give IDENTICAL containment at every draw
level in all four cells.**

**The mechanism is not the scan over candidates. It is Monte Carlo error in
`containment_probability` at low draw counts** — each candidate's containment is estimated on
the same 512 draws, and at 512 that estimate is too noisy. Scanning more candidates does not
worsen it; scanning on more draws fixes it.

### The cross-check the registration demanded

Version C's `conservative_estimate_split` on the **same draws**: cross-fit containment is
**−0.0350** and **−0.0150** below the full estimate at the two highest-γ cells and identical
elsewhere. **Selection bias is real and survives at 4,096 draws at 1.5–3.5 percentage points,
concentrated exactly where the quantiles tie.** This track measured it by sweeping draws;
Version C removed it by cross-fitting; **neither was designed to test the other and they
agree.**

### What changes

* **WITHDRAWN:** *"SPADE's certificate fails below nominal at high assurance."*
* **STANDS:** the registered kill fired as specified — it is a decision rule, not a hypothesis
  test, and it correctly stopped the programme and forced this investigation.
* **NEW REGISTERED CONSTRAINT:** **`N_DRAWS = 512` is not sufficient to estimate `CE_alpha`'s
  containment at γ ≥ 0.95. Any future containment claim requires ≥ 1,024 draws**, and the
  residual bias at 4,096 requires the cross-fit.

## ✅ TASK 3 · **P6 cells 3+4 COMPLETE.** d=8 at both σ, all four families, **gate failures 0**
across all eight cells (250 campaigns each). The screening result **reproduces at d=8** —
`doe` mean rank 7.78 of 9 on hartmann6 σ=0.25 against 7.59 at d=6. **The registered stop
condition "the screening result fails to reproduce at d=8" did NOT fire.**

---

## ⚖️ TASK 6.3 / 6.4 · **E7's registered prediction FAILS — and so does its kill condition**

Full result and all arithmetic in `docs/FINDINGS-SPADE.md` **§34**. Recomputed from committed
files in-session; **not** taken on the reporting agent's word.

**Registered prediction:** under rule P the identification gaps converge and `doe`'s advantage
falls below SESOI (0.02). **Registered kill:** the advantage *remains above* SESOI.

**VERDICT: NEITHER BRANCH FIRES, and the registration was mis-specified.** Under rule P `doe`
has **no advantage to be above or below SESOI — it has a deficit.** Its identification gap
nearly quadruples (+0.0361 → **+0.1396**, Wilcoxon p = 4.95e-08, bootstrap 95% CI
[+0.0723, +0.1367]), while **every** non-`doe` arm's gap falls. Excluding `doe` the gaps do
converge (spread 0.0776 → **0.0395**); including it they diverge (0.0890 → **0.1339**).

§9.3's mechanism is therefore **confirmed for the arms it was about and `doe` is not one of
them.** Rule P does not equalise identification — it replaces `doe`'s identification advantage
with a larger model-quality deficit. **A registration that offers only "above SESOI" and
"below SESOI" cannot express a sign flip; this one could not, and the finding is recorded as
a third outcome rather than forced into either branch.**

**REGISTERED CONSTRAINT — E7 is not a committed artefact.**
`results/e7-search-vs-id-rule-p.json` **does not exist.** The rule-P gap column is a join of
`fix1-terminal-rule.json.regret_p` onto `step0-oracle-best.json.oracle_best`. The join is
sound (`rule_a` agrees across the two files to **max |Δ| = 5.55e-16** over all 300 shared
keys) and **needs no new campaigns**, but until a runner writes the file, **E7 must not be
cited as a committed result.**

### Erratum 28 — two E7 figures had no committed source and are WITHDRAWN

1. **"`doe` +0.0348 → +0.2184 at σ = 0.10."** `step0-oracle-best.json` carries **no `sigma`
   key**; `scripts/run_step0_oracle_best.py:53` hardcodes `sigma_rel = 0.25`. **There is no
   σ = 0.10 E7 measurement on disk.** Withdrawn pending a σ-parameterised re-run.
2. **"`qlogei` .0797 → .0477."** That file carries `qlognei` only. Withdrawn. This is also
   why the excluding-`doe` rule-P spread is **0.0395, not the 0.0420 first reported** — the
   larger figure counted a sixth arm the file does not contain.

**Both figures came from an agent's report and both died on the first check against disk.
The standing rule — verify every number handed to you, including ones you asked for — earned
its place again here.**

### Erratum 29 — the D20 rank reversal was first reported over TEN arms, including `plate1_only`

`plate1_only` carries `never_rank_separately`; its `regret_p` is **identical to `lhs` in 50 of
50 rows** on this file. The ten-arm figures (`doe` 2.12 → 8.80, `random` 8.88, `versionb`
4.08) reproduce exactly but rank `lhs` twice and are **superseded** by the nine-arm table in
§34.1: **`doe` 1.88 (best of nine) → 7.92 (worst of nine); `versionb` 5.28 → 3.76 (best).**
The conclusion is unchanged and the shift is still the largest of any arm. **This is the §19
trap for the second time in this project** — caught before publication, not after.

### Erratum 30 — the `random`-vs-SPADE caveat's p-value

Reported as **p = 1.1e-2**; the two-sided paired Wilcoxon on the committed columns gives
**p = 5.07e-03**. The paired difference (**0.0431**) and the conclusion — *the gain from the
non-maximising rule is general to spread designs and is not evidence for SPADE, because
`random` gains more than SPADE does* — are unchanged and strengthened. The looser figure is
not reproducible from `fix1-terminal-rule.json` and is withdrawn.

**STANDS unchanged:** `lhs` alone does not reach significance — raw Wilcoxon **6.35e-02**,
Holm ×2 = **0.1269**, confirming the registered "p = 0.13" to four figures.

### Registered: "`doe` leads throughout" is FALSE at both σ

`q52-budget-to-target.json` is the **only** committed per-budget curve (11 checkpoints, 4
arms; **no committed file stores per-evaluation regret curves**). At σ = 0.25 `doe` leads at
the shared budget of 48 (−0.0658, p = 1.5e-3) but `qlogei` closes by 150–200; at σ = 0.10 the
lead is **already gone at 48** (p = 0.77) and **inverts** by 150. **The single-budget
comparison at 48 is a snapshot taken across a crossing.**

### Registered: three non-maximising rules are on disk and MUST NOT be pooled

`fix1` stores **rule P** (posterior-mean argmax, multi-start); `q52` stores **rule C** for the
GP arms; and for `doe` in `q52`, rule C is **not a GP at all** — it is the quadratic surface's
own stationary point. **Do not pool the q52 `doe` `rule_c` column with the `fix1` `rule_p`
column.** They share a name and nothing else.
