# Steelman both arms — can BO be made to win, and does the reversal survive?

**Status.** Design, 2026-08-20. Nothing here has been run. Registered before running, per the
project's standing convention.

**The question.** Does the terminal-decision reversal survive when *both* methods are given their
best available form? Not "can we tune BO until it wins."

**Why the framing matters.** The project's own fairness rule (`START-HERE-PERSON-A.md`, Q5) is
explicit: *do not tune your own method while leaving the baselines at defaults.* `PROMPTS-NEXT.md`
adds *do not invent a winner*. A programme that upgrades BO alone and reports the best variant is
the exact failure those rules exist to prevent, and it would destroy the paper's central claim
rather than strengthen it. **Every BO upgrade in this document is paired with a matched classical
upgrade, and every arm run is reported including the losers.**

Either outcome is publishable and both are stronger than the status quo:

- BO wins under steelman -> a real prescription for laboratories, with the mechanism identified.
- BO still loses -> the central claim is close to bulletproof, because a serious attempt was made
  to break it and is documented.

---

## 1. The diagnosis, computed from stored data

Computed from `results/q57-search-vs-id.json`, seeds averaged per landscape, n = 25.

**Primary cell, d = 6, sigma = 0.25:**

| Arm | Measured-value argmax | Search (hidden tested-best) | Identification gap |
|---|---:|---:|---:|
| DoE/RSM | 0.0958 | 0.0597 | **0.0361** |
| qLogEI | 0.1553 | 0.0755 | **0.0797** |
| qLogNEI | 0.1532 | 0.0834 | **0.0698** |

**Lower-noise cell, d = 6, sigma = 0.10:**

| Arm | Measured | Search | Identification gap |
|---|---:|---:|---:|
| DoE/RSM | 0.0892 | 0.0544 | 0.0348 |
| qLogEI | 0.0874 | 0.0496 | 0.0378 |
| qLogNEI | 0.0808 | 0.0435 | 0.0373 |

**Read this before proposing any idea.**

1. At the primary cell BO's identification gap is **2.2x** the classical arm's (0.0797 vs 0.0361).
   At lower noise the two are nearly equal (0.0378 vs 0.0348). **The failure is specific to
   identification under high noise**, not to BO generally.
2. Mechanism, already stated in the paper: BO clusters points near the optimum, producing many
   near-ties that a single noisy reading cannot separate. The CCD spreads out, so its best point
   stands above the noise. This is a *consequence of exploiting well*, not a defect in search.
3. **Headroom.** If BO identified perfectly it would score its search value, 0.0755, against the
   classical arm's 0.0958 — a BO win of **+0.0203**, just above the 0.02 SESOI. So a win is
   arithmetically available.
4. **But the bar is higher than "match DoE."** BO must get its identification gap below **0.0203**,
   whereas the classical arm sits at 0.0361. Matching classical identification is *not enough* —
   BO would still lose by 0.0158, because it also searches slightly worse (0.0755 vs 0.0597). BO
   must identify roughly **44% better than the classical arm** to win outright, or roughly halve its
   own gap to reach declared equivalence.

**Consequence for the idea list.** Interventions that improve *search* are predicted to fail. That
prediction already has two confirmations on disk: better kernels moved held-out R^2 without moving
regret, and Q62's TuRBO changed nothing (0.1538 vs 0.1532). **Register this prediction now**, so
that further search-side nulls count as confirmations rather than surprises.

**The exchange rate is the contribution.** Spending wells on replication costs search and buys
identification. BO's exchange rate is far better than the classical arm's because its identification
gap is 2.2x larger. That is a mechanism and a prescription, not a tuning trick.

---

## 2. BO interventions, ranked by predicted effect on the diagnosed failure

### Tier 1 — attack identification directly

**B1. Budget split between exploration and confirmation.**
Reserve part of the 48 wells for re-measuring candidates instead of visiting new ones. Start with a
registered grid of fixed splits (48/0, 44/4, 40/8, 36/12), shortlist by posterior mean, allocate
confirmation wells across the shortlist, decide on the pooled mean of all readings of each well.
*Predicted:* the largest single gain available. It is the only intervention that spends budget
directly on the 0.0797.
*Note on numbering:* `TURBO-OCBA-GONOGO.md` reserves **Q63** for OCBA and assigns it to Paper 2 as
"weeks of method." A fixed-split version is days, not weeks, and is Paper-1-scoped. **Confirm with
the other session whether this takes Q63 or a fresh number before running.**

**B2. Knowledge-gradient acquisition.**
`qKnowledgeGradient` is present in BoTorch 0.18.1 and **is not implemented in this repo** —
`optimizers.py` offers only qLogEI and qLogNEI. Expected improvement optimizes the best *observation*;
knowledge gradient optimizes the value of the final *recommendation*, which is literally this
project's estimand, E[1 - f(delta(D_N))]. Its absence is arguably a gap in the current comparison
rather than a tuning choice, which makes it the most defensible addition here.
*Predicted:* moderate. It should reduce wasteful clustering and improve the recommendation, but it
does not buy repeat measurements.

**B3. Local quadratic readout on BO's own points.**
Fit a second-order surface to the top-k BO points in a neighbourhood of the incumbent and take its
constrained argmax — giving BO the classical arm's identification machinery on BO's data.
Distinct from factorial cell 6, which fits a *full* d-dimensional quadratic to all 48 clustered BO
points and fails on rank deficiency; a local fit on a neighbourhood is far better posed.
*Predicted:* moderate, and cheap. It costs zero extra wells, which makes it strictly dominant if it
works at all.

### Tier 2 — repair a known defect

**B4. GP calibration.**
Nominal 95% latent intervals cover as little as 76.4%. A miscalibrated posterior corrupts the
acquisition (wrong uncertainty -> wrong exploration) *and* posterior-mean selection. `build_gp`
already exposes `input_warping`, `lengthscale_prior`, `kernel_structure`, `fit_restarts` and
`additive_prior_dims`; none has been swept against *coverage* as the objective.
This is repairing a broken component, not tuning to win, and is defensible under any fairness rule.
Overlaps gap **G4**.

### Tier 3 — structural, only with a matched classical change

**B5. Dimension reduction for BO.**
The classical arm gets a 6->4 screen; BO keeps all six. Q59 showed removing the screen made the
classical arm *worse*, so the screen is a genuine advantage rather than a handicap. The symmetric
move is to give BO a screening step. SAASBO is the natural choice but requires `pyro`, which is
**not installed** — adding a dependency is a decision, not a detail. A no-dependency alternative is
hard ARD-lengthscale screening after the opening design.

**B6. Batch size.** q = 4 today. q = 1 is already registered as **Q61** and is blocked on the 1e-12
replay gate (gap G7). Do not duplicate it.

---

## 3. Matched classical steelman — mandatory

Running section 2 without this section produces a tuned-BO-versus-default-DoE comparison, which is
void under the project's own rules.

- **C1. Replicated design points.** The classical answer to noise is replication. A 48-well design
  that replicates factorial or axial points instead of adding distinct ones. This is the direct
  counterpart to B1 and the fairest possible comparator for it.
- **C2. Relocating sequential RSM at 48 wells.** `doe_ascent` exists but is only exercised at the
  200-well cap. The 48-well cell currently uses the non-relocating pipeline.
- **C3. D-optimal or I-optimal design** in place of the face-centred CCD, on the retained factors.
- **C4. Ridge / canonical readout.** Already implemented; must be carried into every new cell.

---

## 4. Discipline

- **Register every arm and the analysis before running.** Two sessions have already collided once in
  this repo; the record is in `COMMIT_MSG.txt`. Claim ticket numbers in `OPEN-QUESTIONS.md` before
  starting, and check `TURBO-OCBA-GONOGO.md` for numbers the other session holds.
- **Register the section 1 prediction** that search-side interventions will not move regret, so
  further nulls read as confirmations.
- **Report every arm, including losers.** No "best variant" headline. The full grid goes in the
  supplement.
- **Holm across the family of new arms.** These are exploratory until a specific arm is promoted to
  confirmatory and re-run.
- **SESOI stays 0.02.** Do not move it to make a result significant.
- **Power.** At n = 25 the MDE is about 0.027, larger than the SESOI — so this programme run at
  n = 25 will mostly return "inconclusive." **Gap G2 (extend to n = 100) should land first**, or the
  whole exercise produces uninterpretable results.
- **Gate every replay at 1e-12.** Gap G7 must be fixed first for anything that replays stored
  campaigns.

---

## 5. Order of work

1. **Pilot, exploratory, n = 25, primary cell only.** B1 (fixed splits) and B3 (local quadratic
   readout), because both are cheap and both attack the diagnosed failure. Purpose is to size the
   effect, not to decide anything. Label exploratory in every artefact.
2. If a pilot closes a material share of the 0.0797, **fix G7 and G2**, then register the
   confirmatory run.
3. **B2 (knowledge gradient)** — implement in `optimizers.py` beside the existing two acquisitions.
4. **B4 (calibration)** — sweep the existing `build_gp` knobs against coverage.
5. **C1 and C2** — the matched classical arms. These are not optional and should be built alongside,
   not after.
6. Confirmatory run of whatever survives, at n = 100, pre-registered, Holm-adjusted.

**Dependencies.** Steps 1 and 3 are independent. Step 2 gates everything confirmatory. Nothing here
should be written into the paper before G7 and G2 are closed.

---

## 6. Predicted outcome, recorded before running

Written down so it can be scored later rather than reconstructed.

- Search-side interventions (B5, B6, and any kernel work): **no material change.** Two confirmations
  already exist.
- B1: **the largest effect**, and the most likely route to equivalence at the primary cell.
- B3: **small but free.**
- B2: **moderate.**
- Overall: **equivalence at the primary cell is plausible; an outright BO win is possible but
  requires identifying about 44% better than the classical arm, which is a hard target.**
- At sigma = 0.10 the two arms are already close, so the interesting result is confined to the
  higher-noise cell.
