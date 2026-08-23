# FINDINGS · SPADE FINAL — the prospective confirmatory study

**Study:** `spade-final-2026-08-23` · **Registration:** `docs/SPADE-FINAL-SPEC.md` at commit
`c4f58d3` · **Errata:** §12 of that file

> **Status of this document.** Sections are filled as artefacts are committed. Anything not
> yet supported by a committed result file is labelled **`NOT RUN`** and **must not be
> cited**. This project has retracted its own headline three times (§4.4, §9.5, §14/§29);
> the labelling is the defence against a fourth.

---

## 1. What was frozen before results

| frozen | where | commit |
|---|---|---|
| the three SPADE arms `m0`/`m4`/`m8`, local rule **L1** | spec §3.1–3.2 | `c4f58d3` |
| the two causal controls | spec §3.3 | `c4f58d3` |
| the mandatory 13-arm registry | spec §4 | `c4f58d3` |
| the pre-run regime classifier and its numeric bars | spec §5.1 | `c4f58d3` |
| `N_DRAWS = 4096`, cross-fit split 2048/2048 | spec §2.1 | `c4f58d3` |
| the four Holm families | spec §8.1 | `c4f58d3` |
| ten kill-ledger items and their firing conditions | spec §10 | `c4f58d3` |
| the broad-paper conjunction | spec §10.1 | `c4f58d3` |
| **Erratum 1** — `tau_q` estimand, σ-dependent primary γ | spec §12 | `4832403` |

**Erratum 1 was committed before `results/final-spade-primary.json` existed.** That is
checkable from the commit graph and is the only defence that matters against the suspicion
that the threshold definition was chosen to flatter SPADE.

## 2. Final SPADE specification

See spec §3. The two points a reader should check first:

* **Rule L1's trust region is the ARD ball of radius 1** — not a tuned box. That radius is
  literally `n_effective`'s bound (`src/boec/versionc.py:91`), the statistic FINDINGS §9.3
  identified as governing the identification gap. A test *measures* that every local well
  increments `n_eff` rather than asserting it.
* **No Stage-0 detector.** K-C7 fired: the regime detector separated **0/50** on both
  held-out families (FINDINGS §37). It gates nothing in this study.

## 3. Benchmark arms and fairness

Spec §4. Wells and rounds are reported on **separate axes** throughout (§4.2): SPADE spends
48 wells over **2** rounds; `qlognei` spends 48 over **10**. A tie on the map at equal wells
is therefore a 5× rounds result, and collapsing the two into one "budget" hides it.

`spade_plate1_only` spends **40** wells, not 48. It is a **rounds/wells reference, not an
equal-well comparator**, and every table that shows it says so.

## 4. Feasible, target, exception and infeasible conditions

**Source:** `results/final-spade-feasibility.json`. Committed **before** any campaign, per
spec §6.2.

This section carries the study's first substantive result, and it is a result about the
**study design**, not about SPADE. See `docs/PERPLEXITY-SPADE-FINAL.md` Part 3 for the full
account.

* The originally registered `τ_f ∈ {0.60, 0.75}` sat **above** the certifiability ceiling
  `tau_max(γ=0.95, σ=0.25) = 0.5888`, returning **INFEASIBLE for 12 of 14 cells** including
  the continuity condition. This is FINDINGS §4.5's defect recurring, and the gate caught it
  before any compute was spent.
* **`τ_frac` equalises nothing across families**: prevalence at `τ_f = 0.60` runs from
  **0.0000** (ackley) to **0.9555** (rosenbrock).
* **At σ_rel = 0.25, γ = 0.95 admits no nontrivial certifiable region on hill** — the ceiling
  0.5888 sits at a true prevalence of ≈0.71, so every certifiable threshold there covers more
  than 70% of the box. A statement about assurance and noise that **no method can fix**.

Under Erratum 1's `tau_q` estimand the achieved prevalence is exact at every planned `p`.
Final classification table: **see `results/final-spade-feasibility.json`**.

## 5. Certificate validity: cross-fit results

**`NOT RUN`** — pending `results/final-spade-certificate.json`.

The protocol is fixed regardless of outcome: cross-fit is **primary**, same-draw is a
labelled **diagnostic**, and their difference rides on every row. Inference is **exact**
(`scipy.stats.binom`), never a normal approximation — FINDINGS §22 records a Holm correction
computed with a normal approximation that did not survive the exact tail.

## 6. Does targeted Plate 2 earn its place?

**`NOT RUN`** — KF-3 / KF-4.

The load-bearing comparison is `spade_cf_m0` vs `spade_random_plate2`: same plate 1, same
number of plate-2 wells, differing **only** in whether those wells are boundary-targeted. If
`m0` does not beat it by ≥ SESOI on symmetric-difference error in a TARGET condition, the
finding is that **targeted plate-2 SUR did not demonstrate value beyond extra random wells**,
and the mechanistic claim leaves the paper.

## 7. Can local allocation lower regret safely?

**`NOT RUN`** — KF-5.

`m > 0` is an improvement only under the full conjunction of spec §7.5. **A regret reduction
that damages the certificate is a trade-off, not a SPADE improvement**, and is reported as
one.

## 8. Map quality versus regret: Pareto results

**`NOT RUN`** — pending `results/final-spade-regret-pareto.json`.

The Pareto figure is mandatory because this project's central claim is that **choosing a
point and certifying a region are different problems**. FINDINGS §13 measured SPADE arms
**9th–11th of 12 on regret and 1st–3rd of 12 on the map** at the same cell — the two objects
rank SPADE almost exactly opposite.

## 9. Calibration and refinement

**`NOT RUN`**.

AUC is **secondary only**: it is invariant to monotone transformation and cannot see
calibration, and mean `grid_r2` is negative for all eight arms (§9.4). The primary map scalar
is the **symmetric difference**. **Type I volume alone ranks silence first** — an empty
certificate scores exactly 0 — and is never emitted without its partner.

## 10. Cross-family, noise and dimension scope

**`NOT RUN`** for campaigns; feasibility complete (§4).

Known limits going in: hartmann6 and ackley are structurally unfavourable (§37, §41), and
**ackley is a pre-declared EXCEPTION** — §41 records SPADE certifying **nothing in 1,200
campaigns** there.

## 11. Sobol, BO and DoE comparison

**`NOT RUN`**.

Sobol is a **mandatory** arm in every primary condition, not a weak foil: FINDINGS §13 has
`sobol` 4th of 12 on the map, ahead of `qlogei`, `qlognei` and `doe`. Both `qlogei` and
`qlognei` run, because §4.2b records the **Q57 trap** — a headline that held against the
weaker acquisition and died against the noisy one.

## 12. Kill ledger

**`NOT RUN`** — pending `results/final-spade-kill-ledger.json`. Registered items KF-1…KF-10
are in spec §10 with their firing conditions.

## 13. What the final paper may claim

**`NOT RUN`.** Determined by the spec §10.1 conjunction, not by narrative preference. If any
component fails, **the claim narrows** — it is never hidden.

## 14. What the final paper may not claim

Fixed in advance and **independent of any result**:

* That SPADE beats Sobol, BO or DoE **generally**. FINDINGS §42 already characterises SPADE
  as **a low-variance middling arm** on the BO community's own conventions — it wins outright
  on **2%** of problems and is within 3× of best on **70%**.
* That `alpha_star` evidences a good certificate. §28/§31 **declared** it does not; it
  measures *willingness to certify*.
* That high same-draw containment evidences a valid certificate. It is circular by
  construction (`src/boec/vorobev.py:105`).
* Anything at `γ = 0.95` and `σ = 0.25` — Erratum 1 shows no nontrivial threshold exists
  there.
* Any universal claim from TARGET-regime evidence.

## 15. Limitations and exceptions

* **Only one TARGET cell exists** in the registered matrix. The central claim, if supported,
  rests on a narrow base and must say so.
* Plug-in hyperparameters: their uncertainty sits **outside** the guarantee, exactly as for
  `conservative_estimate`.
* §9.7's shared noise stream — σ levels are analysed **separately**, never pooled as
  independent replicates.
* `doe_unscreened` is expected **unavailable at d=8**: a second-order RSM needs 45
  coefficients against a 48-well budget. Recorded by arithmetic, never approximated into
  existence.

## 16. Reproducibility manifest

**`NOT RUN`** — pending `results/final-spade-manifest.json`.
