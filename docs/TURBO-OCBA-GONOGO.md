# TuRBO and adaptive explore/identify — go/no-go

*Status (2026-08-20).* Human chose **Option B**: implement TuRBO-1 vs relocating RSM. Option C (OCBA) stays Paper 2. Do not run B and C in parallel. **Implementation is in tree.** Headline numbers are valid only from `results/q62-turbo.json` with `"smoke": false`.

*Ticket IDs.* **Q60** and **Q61** remain the registered Paper 1 closure items (top-3 average confirmation; q=1 BO). They are blocked on the 1e-12 BO replay gate. TuRBO is **Q62**. OCBA/allocation is **Q63**. Do not overwrite `results/q58-selection-sensitivity.json`, E2, or Q56.

*Goal.* Decide whether trust-region BO (TuRBO) and a GP explore/identify split belong in Paper 1, and if so how to run them without wrecking the recommendation-strategy claim.

*Architecture.* Paper 1 stays an ablation of recommendation strategy × design × surrogate × cost unit. TuRBO changes **where** sequential BO may sample. OCBA changes **how** a fixed well budget is split between new locations and confirmation.

*Tech stack (Q62).* Existing `boec` campaign loop, BoTorch 0.18, qLogNEI inside a trust region, `doe_ascent` as the relocating classical comparator, Q55/Q58 locators.

---

## 0. Verdict

Paper 1 does **not** require TuRBO or OCBA. Rankings reverse with the recommendation strategy; most of the noisy-assay DoE lead is identification; confirmation and walking RSM already close the easy reviewer holes.

| Option | What you do | Status |
|---|---|---|
| A — submit Paper 1 | Write from locked JSON. No new arms. | Still valid if Q62 slips |
| **B — TuRBO-1 vs `doe_ascent`** | Spec below (Q62) | **Done.** 48-well + N=200 JSON on disk |
| C — OCBA allocation curve | Paper 2 (Q63). Weeks of method. | Not started |

Default if nobody had picked: A.

---

## 1. What is true, and what is overstated

### 1.1 TuRBO as “RSM’s true analog”

*True.* TuRBO (Eriksson et al., NeurIPS 2019) keeps a hyper-rectangle around the incumbent, expands after consecutive successes, shrinks after consecutive failures, and proposes only inside that box. In noise it should centre on the **posterior-mean incumbent**, not the luckiest observation. That is closer in spirit to “do not trust the fit far from local evidence” than unconstrained-box qLogEI.

*Overstated.* It is not structurally the same as Box–Wilson RSM.

| Piece | Relocating RSM (`doe_ascent`) | TuRBO-1 |
|---|---|---|
| Local region | CCD box on retained factors after a screen | Hyper-rectangle on all *d*, side lengths scaled by GP lengthscales |
| How it moves | Canonical analysis → steepest-ascent path of measured points → replant CCD | Success/fail counters on the batch; length ×2 or ÷2 |
| What is trusted | Local quadratic | Local GP |
| History | Kept | Official TuRBO restarts discard previous TR data |
| Batch | CCD + path plated together | Same *q*=4 as current BO, candidates clipped to TR |

The paper’s in-region GP recommendation is a **terminal locator** on an already-run campaign. TuRBO is a **sampling constraint**. Those are different experiments. On Hill, unconstrained GP-max and in-region GP-max already coincide, so TuRBO cannot “break the in-region tie” by changing the readout. It can only change **where the 48 wells went**.

TuRBO was demonstrated on high-*d* problems. At *d*=6, *N*=48, *q*=4 the trust region can collapse after a few failed batches. Freeze hyperparameters before the grid. Do not retune on Hill.

### 1.2 Adaptive explore/identify (Q63, not now)

*True.* ~73% of the primary measured-argmax gap is identification. Q58: +3 confirmation wells wipe the gap. A live explore-vs-confirm rule is the next scientific question.

*Overstated.* DoE is not “under-resourced for identification.” Q58 showed confirmation **hurt** DoE (0.0958 → 0.1437) when the original reading was discarded. The miscalibration is almost entirely on clustered BO. Frame Q63 as a **budget-allocation rule**, not a new estimand.

---

## 2. Option B — Q62 TuRBO-1 vs relocating RSM

### Question (registered)

**Primary (*N*=48).** At matched wells and matched rounds, when sequential BO may only acquire inside an adaptive trust region, does measured-value-argmax still favour 48-well DoE at *d*=6, σ=0.25?

**Secondary (*N*=200).** Does arrival *P(T* ≤ *N*) still lack a general BO well-count saving vs `doe_ascent`?

Winner not pre-written. Either “TuRBO samples more like walking RSM and the identification gap shrinks” or “even local BO does not close it” is publishable in this cell / a sequel, not required for Paper 1’s existing claims.

### Arms

| Arm | Role |
|---|---|
| `qlognei` | Existing unconstrained sequential BO |
| `turbo1_qlognei` | **New.** TuRBO-1, qLogNEI restricted to the current TR |
| `doe_ascent` | Existing walking RSM |
| `doe` | Existing 48-well screen+CCD (*N*=48 only) |

qLogEI is a sensitivity column, not a third BO. Do not add TuRBO-m, SAASBO, SCBO, MES.

### Locked hyperparameters (frozen before the first landscape)

Copy BoTorch TuRBO-1 defaults. Do not tune on Hill.

- One trust region (TuRBO-1).
- `length_init = 0.8` of the unit box; `length_min` / `length_max` as BoTorch tutorial (`0.5**7` and `1.6`).
- Success: batch improves the **posterior-mean incumbent among visited wells** (noisy rule), not raw max *y*. Same incumbent definition as qLogEI’s `max_posterior_mean` policy, for a one-change comparison (TR on vs off).
- `success_tolerance = 3`; `failure_tolerance = ceil(max(4/q, d/q))`.
- On restart (`restart_triggered`): **keep all data** and start a new TR from the current posterior-mean best. Discarding history would be unfair to `doe_ascent`. Register this deviation from canonical TuRBO.
- Opening: same *n*₀ = 2*d*+2 Sobol as qLogNEI, not a CCD. Pair instance ids with E2/Q56.
- Batch *q* = 4. Budget 48 and, separately, cap 200 at *d*=6 only.
- Cells: *d*=6 × σ ∈ {0.10, 0.25}, *n*=25, 2 seeds, same instance ids as E2.

If length hits `length_min` before budget is spent: keep proposing inside the minimum TR. Do not silently switch to global qLogNEI.

### Locators (same as the paper)

Per campaign store *R*_search, *R*_measured_argmax, identification, GP recommendation (full box vs inside current TR), and for DoE unconstrained quadratic vs in-region.

### Cost

Charge rounds as current BO: 1 + ⌈(*n* − *n*₀)/4⌉. Lead with *P(T* ≤ *N*). No fold-savings if one arm is heavily censored.

### Gates

- Replay qLogNEI at stored seeds: measured-argmax means must match **0.1532** (σ=0.25) and **0.0808** (σ=0.10) at *d*=6 before any TuRBO row is trusted.
- If TuRBO uses < 20 unique locations in 48 wells on > half of landscapes: report TR collapse; do not retune `length_init`.
- Primary confirmatory contrast: `doe` vs `turbo1_qlognei` measured-argmax at *d*=6, σ=0.25, *N*=48.

### Fairness (what this is and is not)

Matched budget, frozen knobs, kept history, and one intended change (local box) are **fair enough** to answer the registered question. TuRBO is **not** isomorphic to walking RSM (screen, CCD, measured path). Do not write that it is.

---

## 3. Option C — Q63 (Paper 2, not now)

For a fixed 48-well budget, after each BO batch, should the next *q* wells be new locations or replicates of current leaders? Compare BO-only adaptive split vs Q58’s fixed top-3 vs vanilla qLogNEI, same stored DoE campaigns as reference.

Cheap negative control first: fixed “40 explore + 8 replicates on the current GP leader.” If that matches OCBA, the fancy allocator is not the contribution.

Output would be `results/q63-ocba.json`. Do not reuse the Q61 filename.

---

## 4. Files (Q62)

| Code | Tests | Output |
|---|---|---|
| `src/boec/turbo.py`, `campaign.py`, `scripts/run_q62_turbo.py`, `src/boec/paper_figures.py` | `tests/test_turbo.py`, `tests/test_q62_runner.py`, `tests/test_paper_figures.py` | `results/q62-turbo.json`, `results/q62-turbo-n200.json`, `docs/figures/fig4-turbo.pdf` |

Do not overwrite E2 or Q56.

---

## 5. Explicit do-nots

- Do not add TuRBO, SAASBO, SCBO, and MES in one grid.
- Do not retune TuRBO length after seeing Hill.
- Do not discard TuRBO history on restart unless you also wipe `doe_ascent` history (you must not).
- Do not call TuRBO “isomorphic to RSM.” “Locally constrained sequential search” is enough.
- Do not restore “different estimands” as the OCBA pitch.
- Do not claim DoE is identification-starved; Q58 says otherwise.
- Do not block Paper 1 submission on Q62 if the grid is slow; Q62 is an add-on cell.
- Do not reuse ticket IDs Q60/Q61 for these runs.
