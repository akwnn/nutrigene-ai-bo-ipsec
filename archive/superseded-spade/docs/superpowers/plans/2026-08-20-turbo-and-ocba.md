# TuRBO and adaptive explore/identify — go/no-go plan

> **For agentic workers:** Do not start campaigns from this file until the human has chosen Option A, B, or C below. This is a decision document plus a run spec, not a license to add algorithms.

**Goal.** Decide whether trust-region BO (TuRBO) and a GP-OCBA explore/identify split belong in the current paper, and if so how to run them without wrecking the evaluation-protocol claim.

**Architecture.** Paper 1 stays an ablation of *terminal decision × design × surrogate × cost unit*. TuRBO changes *where sequential BO is allowed to sample*. OCBA changes *how a fixed well budget is split between new locations and confirmation*. Those are Paper 2 questions unless the human explicitly delays submission.

**Tech stack (only if running).** Existing `boec` campaign loop, BoTorch 0.18 (already pinned), `qLogNEI` as noisy acquisition inside a trust region, `doe_ascent` as the relocating classical comparator, Q55/Q58 locators.

---

## 0. Verdict (read this first)

**Do not run either experiment as a condition of submitting the current paper.**

The manuscript is already a methods-journal argument: rankings reverse with the terminal rule; most of the noisy-assay DoE lead is identification; three confirmation wells erase it; walking RSM kills the “fewer wells” headline. Adding TuRBO or OCBA does not close a hole a reviewer can still use to reject *that* claim. It opens a new paper.

| Option | What you do | When it is the right call |
|---|---|---|
| **A — submit Paper 1** (recommended) | Write, package code/JSON, read the cited PDFs. No new arms. | You want a methods paper this season. |
| **B — one add-on: TuRBO-1 vs `doe_ascent` only** | Spec below, ~1–2 weeks if it behaves, longer if hyperparameters fight d=6 / n=48. | You are willing to delay submission for a “both methods may relocate locally” cell. |
| **C — OCBA allocation curve** | Spec below. Treat as Paper 2. Weeks of method, not a weekend runner. | You want a new estimand/unit of comparison. Do not bolt this onto Paper 1. |

**Do not run B and C in parallel.** OCBA changes the BO pipeline so a TuRBO×OCBA factorial is four new methods, not two.

Default if nobody picks: **A**.

---

## 1. What is true in the two pitches, and what is overstated

### 1.1 TuRBO as “RSM’s true analog”

**True.** TuRBO (Eriksson et al., NeurIPS 2019) keeps a hyper-rectangle around the incumbent, expands after consecutive successes, shrinks after consecutive failures, and proposes **only inside that box**. In noise it should centre on the **posterior-mean** incumbent, not the luckiest observation ([BoTorch TuRBO tutorial](https://botorch.org/docs/tutorials/turbo_1); original paper). That is closer in *spirit* to “do not trust the fit far from local evidence” than unconstrained-box qLogEI.

**Overstated.** It is not “structurally isomorphic” to Box–Wilson RSM.

| Piece | Relocating RSM (`doe_ascent`) | TuRBO-1 |
|---|---|---|
| Local region | CCD box on retained factors after a screen | Hyper-rectangle on all d, side lengths scaled by GP lengthscales |
| How it moves | Canonical analysis → steepest-ascent *path of measured points* → replant CCD | Success/fail counters on the batch; length ×2 or ÷2 |
| What is trusted | Local quadratic | Local GP |
| History | Kept | Official TuRBO *restarts discard previous TR data* |
| Batch | CCD + path plated together (registered in `sequential_rsm.py`) | Same q=4 as current BO, but candidates clipped to TR |

The paper’s in-region GP recommendation is a **terminal locator** on an already-run campaign. TuRBO is a **sampling constraint**. Those are different experiments. You already know unconstrained GP-max and in-region GP-max **coincide** on Hill, so “TuRBO to break the in-region tie” will not work by changing the readout. It can only work by changing **where the 48 wells went**.

**Also true, and a reason to be cautious.** TuRBO was demonstrated on high-d problems (BoTorch demo: 20-D Ackley). At d=6, N=48, q=4 the trust region can collapse after a few failed batches and the arm becomes a local polisher. That may look like RSM (good) or like a broken BO (bad) depending on length_init / failtol. Those knobs will be accused of tuning unless frozen *before* the grid.

### 1.2 Adaptive explore/identify split

**True.** Q55/Q57 say ~73% of the primary measured-value-argmax gap is identification. Q58 says +3 confirmation wells wipe the gap. A live explore-vs-confirm rule is the natural *next* scientific question: **given 48 wells, when should the next well be a new location vs a replicate of a leader?**

**Overstated, and one factual error.** The pitch says DoE is “under-resourced for identification at high noise” and BO “over-invests in exploration.” Q58 showed the opposite on DoE: confirmation **hurt** the classical arm (0.0958 → 0.1437) because its first reading was already the trustworthy one. The miscalibration is almost entirely on the **clustered BO** side. An adaptive split that copies DoE’s centre-point logic onto BO is largely “Q58, but decided by the GP instead of a fixed top-3.” That is still worth doing — as Paper 2 — but it is not a new diagnosis. It is an *automated* version of a protocol you already measured.

**“New estimand” is the wrong slogan.** The last round of the paper dropped “estimands” from the title on purpose. Frame this as a **budget-allocation rule**, not a third scientific target. The performance target stays E[1 − f(δ(D_N))].

None of Narayanan / Rummukainen / Lapierre / Ndahiro ran TuRBO vs relocating RSM or an allocation curve. That is true and **not a reason to delay Paper 1**. “Nobody did X” is how papers never ship.

---

## 2. If you choose Option B — TuRBO-1 vs relocating RSM

### Question (register before coding)

> At matched wells and matched rounds, when sequential BO may only acquire inside an adaptive trust region, and classical RSM may relocate by steepest ascent, does measured-value-argmax still favour DoE at d=6, σ=0.25, N=48? Does arrival to N=200 still tie under that rule?

Winner not pre-written. Either “TuRBO samples more like walking RSM and the 48-well identification gap shrinks” or “even local BO does not close it” is publishable **in a sequel**, not required for Paper 1.

### Arms (do not add TuRBO-m, SAASBO, SCBO)

| Arm | Role |
|---|---|
| `qlognei` | Existing co-primary sequential BO (unconstrained acquisition box) |
| `turbo1_qlognei` | **New.** TuRBO-1, acquisition = qLogNEI **restricted to the current TR** |
| `doe_ascent` | Existing walking RSM (primary classical) |
| `doe` | Existing 48-well screen+CCD (N=48 only; no relocation to do) |

qLogEI may be a sensitivity column, not a third BO.

### Locked hyperparameters (write these in the runner docstring *before* the first landscape)

Copy BoTorch TuRBO-1 defaults; do not tune on Hill:

- One trust region (TuRBO-1), not TuRBO-m.
- `length_init = 0.8` of the unit box, `length_min` / `length_max` as in the [BoTorch tutorial](https://botorch.org/docs/tutorials/turbo_1).
- Success: batch improves the **posterior-mean incumbent** (noisy rule from Eriksson et al., not raw max y).
- Failtol / succtol as tutorial.
- On restart (`restart_triggered`): **keep all data** and start a new TR from the current posterior-mean best. Discarding history would be unfair to `doe_ascent`, which keeps every CCD. Register this deviation from canonical TuRBO and say why.
- Opening: same n₀ = 2d+2 Sobol as qLogNEI, **not** a CCD. Pair instance ids with E2/Q56.
- Batch q = 4, budget 48 and (separately) cap 200 at d=6 only.
- Cells: d=6 × σ ∈ {0.10, 0.25}, n=25, 2 seeds, same instance ids as E2.

If length hits `length_min` before budget is spent: keep proposing inside the minimum TR (local polish). Do not silently switch to global qLogNEI.

### Locators (same as the paper)

Per campaign, store:

- R_search, R_measured_argmax, R_id
- GP recommendation (unconstrained box vs inside current TR — they may differ for TuRBO)
- For DoE: naïve unconstrained quadratic vs in-region / ridge

Q58-style top-3 confirmation as a **secondary** readout on the same campaigns if cheap (replay only).

### Cost

Charge rounds exactly as current BO: 1 + ⌈(n − n₀)/4⌉. Do not invent extra rounds for TR updates. Compare to `doe_ascent` rounds via `rounds_for_sequential_rsm`.

Lead with P(T ≤ N). No fold-savings if one arm is heavily censored.

### Implementation sketch (only after Option B is chosen)

Files:

- Create `src/boec/turbo.py` — `TurboState`, `update_trust_region`, `tr_bounds(lengthscales)`.
- Modify `src/boec/optimizers.py` — `propose(..., bounds=tr_bounds)` already uses `optimize_acqf`; pass TR bounds instead of the unit box.
- Modify `src/boec/campaign.py` — after each batch, update TR from incumbent + success/fail.
- Create `scripts/run_q60_turbo.py` — gate: replay qLogNEI at stored seeds, measured-argmax must match 0.1532 / 0.0808 at d=6 before any TuRBO row is trusted.
- Tests in `tests/test_turbo.py` **first**: TR contains incumbent; shrinks after failtol failures on a fixture; never proposes outside TR (1e-12); noisy incumbent is posterior-mean not max y; restart keeps history.

Output: `results/q60-turbo.json`. Do not overwrite E2 or Q56.

### Gates and stop rules

- qLogNEI replay gate fails → stop, do not interpret TuRBO.
- If TuRBO uses < 20 unique locations in 48 wells on > half of landscapes: the TR collapsed; report that as a result, do not retune length_init after seeing Hill regret.
- Primary confirmatory contrast: `doe` vs `turbo1_qlognei` measured-argmax at d=6, σ=0.25, N=48. Secondary: vs `qlognei` (does the TR change BO?). Tertiary: N=200 arrival vs `doe_ascent`.

### What this will not do

It will not make unconstrained quadratic-max a fair RSM readout. That remains a diagnostic. The fair classical arm is still `doe_ascent` + in-region recommendation.

---

## 3. If you choose Option C — adaptive explore/identify (Paper 2)

### Question

> For a fixed 48-well budget, after each BO batch, should the next q wells be new locations (qLogNEI) or replicates of current leaders, using a GP posterior allocation rule? Does that close the identification gap that Q58 closed with a *fixed* top-3 confirmation?

### Do this only after Q58 is the headline of Paper 1

Q58 already gives the lab the actionable rule: confirm three wells. OCBA’s job is to ask whether a **GP-computed** split beats that dumb rule, and whether a quadratic-based split looks different from a GP-based split.

### Minimal mechanism (do not build a full ranking-and-selection stack)

After each batch of size q, for each remaining well slot in the next plate compute two scores:

1. **Explore value.** qLogNEI at unevaluated x (standard).
2. **Identify value.** Expected reduction in P(noisy argmax ≠ true argmax among visited), or a cheap proxy: posterior variance of the current leader’s μ(x) if one more replicate is taken at that x (or at the top-k).

Spend the next plate on the q points with highest score, mixing the two lists. Stop at N=48.

**Register the proxy before seeing Hill.** If you switch from P(wrong pick) to “variance of the leader” after looking at regret, the run is exploratory.

### Classical analog (or do not claim a crossed allocation curve)

A true “quadratic vs GP allocation curve” needs a DoE arm that can also spend leftover wells on extra centre replicates vs extra path points. `doe_ascent` leftover wells currently go **unspent** (`sequential_rsm.py`). Changing that is a second method. Paper 2 may start with **BO-only adaptive split vs Q58’s fixed top-3 vs vanilla qLogNEI**, all vs the same `doe` campaign. That already answers “does adaptive identification help BO?” without pretending DoE got the same allocator.

### Cells and output

d=6, σ=0.25 primary; σ=0.10 sensitivity. n=25, same ids. Output `results/q61-ocba.json`. Store per round: n_explore, n_confirm, R_search, R_measured_argmax.

### Cheap negative control (do this before OCBA if you only have a day)

Q58 already moved BO 0.1553 → 0.1446 with three confirms and DoE 0.0958 → 0.1437. A **fixed** schedule “40 explore + 8 centre-style replicates on the current GP leader” is enough to see if allocation, not OCBA theory, is doing the work. If that matches OCBA, the fancy allocator is not the contribution.

---

## 4. Recommended sequence

```
now     Paper 1 write-up + PDF checks + reproducibility packet
        (Figures 1–2 already generated from JSON)

optional delay   Option B: Q60 TuRBO-1 vs doe_ascent
                 then decide if Paper 1 still submits without it

later            Option C: Q61 allocation, as a new paper
                 citing Paper 1’s identification split and Q58
```

### Paper 1 sentences that stay legal without B or C

- Unconstrained quadratic-max is a naïve diagnostic; in-region / ridge is the 48-well classical readout.
- `doe_ascent` is the long-run classical comparator; under measured-value argmax it ties sequential BO on arrival.
- Identification, not search, dominates the noisy single-readout DoE lead; three confirmation wells erase it.

You do **not** need “BO’s closest analog to ridge relocation” to say those.

---

## 5. Explicit do-nots

- Do not add TuRBO, SAASBO, SCBO, and MES in one grid.
- Do not retune TuRBO length after seeing Hill.
- Do not discard TuRBO history on restart unless you also wipe `doe_ascent` history (you must not).
- Do not call TuRBO “isomorphic to RSM” in the paper. “Locally constrained sequential search” is enough.
- Do not restore “different estimands” as the OCBA pitch.
- Do not claim DoE is identification-starved; Q58 says otherwise.
- Do not block submission on these runs.

---

## 6. Files that would change only after a human picks B or C

| If | Code | Tests | Output |
|---|---|---|---|
| B | `src/boec/turbo.py`, `campaign.py`, `optimizers.py`, `scripts/run_q60_turbo.py` | `tests/test_turbo.py` | `results/q60-turbo.json` |
| C | `src/boec/allocation.py`, `scripts/run_q61_ocba.py` | `tests/test_allocation.py` | `results/q61-ocba.json` |
| A | none | none | journal PDF |
