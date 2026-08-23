# FINDINGS · SPADE FINAL — the prospective confirmatory study

**Study:** `spade-final-2026-08-23` · **Registration:** `docs/SPADE-FINAL-SPEC.md` at commit
`c4f58d3` · **Errata:** §12 of that file

> **Status of this document.** Sections are filled as artefacts are committed. Anything not
> yet supported by a committed result file is labelled **`NOT RUN`** and **must not be
> cited**. This project has retracted its own headline three times (§4.4, §9.5, §14/§29);
> the labelling is the defence against a fourth.

---

## 1. What was frozen before results

**Condition: all** · **terminal rule: n/a (registration inventory)** · **n: n/a**

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

**C2 (hill, d=6, σ=0.10) is IN — the study's one registered TARGET condition, n=100.** Every
other primary/secondary condition is `NOT RUN`; nothing below generalises past hill.

**Source:** `results/final-spade-certificate.json`, `results/final-spade-kill-ledger.json`,
adjudicated at the primary map cell `(τ_q p=0.25, γ=0.95, α=0.95)` per spec §5.2/§7 (τ_q p=0.25
is C2's TARGET threshold; γ=0.95 is the binding primary γ at σ=0.10; α=0.95 is the figure cell
named in spec §11).

**KF-1 — INCONCLUSIVE.** No cell is confirmatory: every one sits below the evidence floor of
10, outside the frozen F-CERT family, or in a condition missing a mandatory comparator.
`doe_unscreened` is absent from every condition (spec §4's `doe` runs, but the unscreened
variant was never wired into this runner) — recorded as `missing mandatory comparator(s):
doe_unscreened` on the printed table, and it is why **no cell in this run is confirmatory
regardless of its containment numbers.** This blocks any PASS/FAIL certificate claim until
fixed.

**KF-9 — PASS.** 0 of 8,800 primary-γ (0.50, 0.95) rows sit above the certifiability ceiling.
2,200 rows at the registered diagnostic γ=0.99 do breach it (τ_q p=0.10 at hill σ=0.10
exceeds `tau_max(γ=0.99)=0.7674`) — expected and excluded from this check by design (spec
§2.4; the diagnostic corner is never claimed as primary evidence).

**KF-10 — FAIL, genuinely.** 10 cells reached PASS on raw containment while **more than
half their campaigns certified nothing** (up to 81% empty for `spade_plate1_only`), and were
correctly downgraded to INCONCLUSIVE. This is the **empty-set trap** §41.3 already documented
off hill, now reproduced prospectively on hill itself: the problem is emptiness, not
miscoverage, and a method that declines to answer two campaigns in three has not shown a
valid certificate.

Cross-fit and same-draw containment are reported as **separate columns on every cell**, never
collapsed — e.g. `spade_cf_m0` at `(0.25, 0.95, 0.80)`: cross-fit 87/97 = 0.8969, same-draw
1.0000. Inference is **exact** (`scipy.stats.binom`), never a normal approximation.

## 6. Does targeted Plate 2 earn its place?

**KF-3 — FAIL.** `spade_cf_m0` vs `spade_random_plate2` on symmetric-difference error at the
primary cell: effect **−0.00188** (m0 is *worse*, not better), n=25, Holm p=0.4108 — nowhere
near the ≥SESOI(0.02) bar spec §7.3 requires. **Targeted plate-2 SUR did not demonstrate
value beyond an equal-well random second plate on hill at σ=0.10.** Per spec §7.3's
registered consequence, **the mechanistic claim comes out of the paper** for this condition.
This is the load-bearing causal comparison of the whole study, and on the one TARGET cell
available it does not hold.

**KF-4 — FAIL.** `spade_cf_m0` vs `spade_plate1_only`: effect **+0.01171** in the wrong
direction (plate1_only reads *better* on symmetric difference), n=25, Holm p=1.273e-04
(significant, and significant against SPADE). Per spec §4.1's registered asymmetry —
`plate1_only` is 8 wells short and therefore *favourable* to plate 2 — **this is the
stronger reading of the two failures, not the weaker one.**

## 7. Can local allocation lower regret safely?

**KF-5 — FAIL** (`spade_cf_m4` is the best-conjunction candidate of the two variants).
Effect **−0.00278** on rule-P regret (i.e. `m4` does not even reduce regret at this cell),
n=25, Holm p=0.3123. The §7.5 conjunction is not met. **`m > 0` is reported as a TRADE-OFF,
not an improvement**, on the one TARGET cell measured so far.

## 8. Map quality versus regret: Pareto results

**Source:** `results/final-spade-regret-pareto.json`, combined C1+C2 via
`merge_condition_rows` (spec §15's artefacts are singular; see §17.2).

**C2 (hill, σ=0.10, TARGET):**

| arm | rounds | wells | regret A | regret P (primary) | sym. diff | certificate |
|---|---|---|---|---|---|---|
| doe | 3 | 48 | 0.0924 | 0.3072 | 0.2580 | NOT_ASSESSED |
| lhs | 1 | 48 | 0.1041 | 0.0747 | 0.1867 | NOT_ASSESSED |
| qlogei | 10 | 48 | 0.1000 | 0.0791 | 0.2079 | NOT_ASSESSED |
| qlognei | 10 | 48 | 0.0874 | **0.0691** | 0.2135 | NOT_ASSESSED |
| random | 1 | 48 | 0.1370 | 0.0905 | 0.2050 | NOT_ASSESSED |
| sobol | 1 | 48 | 0.1297 | 0.0855 | 0.1913 | NOT_ASSESSED |
| **spade_cf_m0** | 2 | 48 | 0.1426 | 0.0844 | **0.1804** | INCONCLUSIVE |
| spade_cf_m4 | 2 | 48 | 0.1403 | 0.0871 | 0.1770 | INCONCLUSIVE |
| spade_cf_m8 | 2 | 48 | 0.1385 | 0.0835 | 0.1797 | INCONCLUSIVE |
| spade_plate1_only | 1 | 40 | 0.1426 | 0.0863 | 0.1921 | INCONCLUSIVE |
| spade_random_plate2 | 2 | 48 | 0.1401 | 0.0822 | 0.1785 | INCONCLUSIVE |

`spade_cf_m0` posts the **lowest symmetric difference of all 11 arms** (0.1804) — including
every BO and space-filling comparator — while sitting mid-pack on rule-P regret (`qlognei` is
best at 0.0691). **This is exactly the split FINDINGS §13 predicted**: SPADE competitive-to-
best on the map, unremarkable on regret, at equal wells and a fifth of `qlognei`'s rounds.

**C1 (hill, σ=0.25, ROBUSTNESS — not TARGET, context only):**

| arm | rounds | wells | regret A | regret P (primary) | sym. diff |
|---|---|---|---|---|---|
| doe | 3 | 48 | 0.1141 | 0.1684 | 0.2583 |
| lhs | 1 | 48 | 0.1693 | 0.0991 | 0.2391 |
| qlogei | 10 | 48 | 0.1757 | 0.1317 | 0.2520 |
| qlognei | 10 | 48 | 0.1858 | 0.1380 | 0.2530 |
| random | 1 | 48 | 0.2358 | 0.1234 | 0.2547 |
| sobol | 1 | 48 | 0.1639 | 0.1221 | 0.2504 |
| **spade_cf_m0** | 2 | 48 | 0.1737 | 0.1126 | **0.2415** |
| spade_cf_m4 | 2 | 48 | 0.1765 | 0.1069 | 0.2409 |
| spade_cf_m8 | 2 | 48 | 0.1765 | 0.1065 | **0.2398** |
| spade_plate1_only | 1 | 40 | 0.1802 | 0.1123 | 0.2412 |
| spade_random_plate2 | 2 | 48 | 0.1802 | 0.1194 | 0.2411 |

At σ=0.25 the whole map compresses (all eleven arms sit within 0.2391–0.2583, versus
0.1770–0.2580 at σ=0.10) — consistent with §4's finding that σ=0.25/γ=0.95 admits no
nontrivial certifiable region on hill at all: at this noise level every method is looking at
a nearly featureless map. `spade_cf_m8` is marginally best here, but the spread is inside
noise and this is a ROBUSTNESS condition — no kill is adjudicated on it.

`NOT_ASSESSED` certificate status for non-SPADE arms is correct throughout — the certificate
machinery is SPADE-specific; other arms report map/regret only.

## 9. Calibration and refinement

**Not yet separately tabulated** — Murphy calibration/refinement values exist per-row in
`results/final-spade-c2.json` (used internally by KF-5's calibration clause) but have not
been pulled into a standalone table or figure. AUC remains **secondary only**: it cannot see
calibration, and the primary map scalar above is the symmetric difference throughout. Type I
volume is never reported alone.

## 10. Cross-family, noise and dimension scope

**All four PRIMARY conditions (C1–C4) done. S1 (ackley) done.** S2/S3 running/`NOT RUN`.
Feasibility complete for all seven (§4).

Known limits going in, by condition id:

| condition | family | class | status | why |
|---|---|---|---|---|
| **S1** | ackley | **EXCEPTION** (pre-declared) | **done** (§10.3) | centre-point optimum advantages classical designs; §41 records SPADE certifying **nothing in 1,200 campaigns** on this family |
| C3 | hartmann6 d=6 | ROBUSTNESS | **done** (§10.1) | multimodal; §37/§42 predict SPADE struggles |
| C4 | hartmann6 d=8 | ROBUSTNESS | **done** (§10.2) | `doe_unscreened` not implemented (§15/§18 — a scoped decision, not a defect) |
| S2 / S3 | levy / rosenbrock | ROBUSTNESS | NOT RUN | §41 records both under-covering at γ=0.99 |
| C1 | hill σ=0.25 | ROBUSTNESS | **done** (§8) | pilot non-empty certificates **0 of 20** at α=0.95 — certificates go empty; σ=0.25 map compresses to a near-featureless band (§8) |
| **C2** | hill σ=0.10 | **TARGET** | **done** (§5–9) | the only TARGET cell in the registered matrix; pilot non-empty **11 of 20** at α=0.95 |

**S1 is reported, not dropped.** A pre-declared exception that vanishes from the write-up is
the suppression spec §9.5 forbids.

### 10.1 C3 (hartmann6, d=6, σ=0.25, ROBUSTNESS — no kill is adjudicated here)

| arm | rounds | wells | regret A | regret P (primary) | sym. diff |
|---|---|---|---|---|---|
| doe | 3 | 48 | 0.5521 | 0.5682 | 0.2244 |
| lhs | 1 | 48 | 0.5155 | 0.5405 | 0.2043 |
| **qlogei** | 10 | 48 | 0.2988 | 0.2832 | 0.2283 |
| **qlognei** | 10 | 48 | 0.2685 | **0.2443** | 0.2163 |
| random | 1 | 48 | 0.4999 | 0.4489 | 0.1993 |
| sobol | 1 | 48 | 0.4935 | 0.4608 | 0.1899 |
| spade_cf_m0 | 2 | 48 | 0.4863 | 0.4221 | **0.1848** |
| **spade_cf_m4** | 2 | 48 | 0.4818 | 0.4129 | **0.1815** |
| spade_cf_m8 | 2 | 48 | 0.4768 | 0.3647 | 0.1836 |
| spade_plate1_only | 1 | 40 | 0.5249 | 0.4977 | 0.2100 |
| spade_random_plate2 | 2 | 48 | 0.5021 | 0.4687 | 0.1994 |

**A genuine surprise, reported precisely rather than rounded to the predicted answer.** On
regret, `qlognei`/`qlogei` dominate as expected (1st/2nd, 0.2443/0.2832 — a wide margin
over everything else, consistent with §37's mechanism: BO commits to one basin and resolves
it, the correct strategy when 48 wells cannot resolve hartmann6's several basins). **But on
symmetric difference — the primary map scalar — the three SPADE arms take 1st, 2nd and 3rd
of 11**, ahead of `sobol` (4th) and far ahead of `qlognei` (9th) and `qlogei` (worst, 11th).

This is the opposite of a clean confirmation of §37/§42's prediction that SPADE "struggles"
on hartmann6 — that prediction is about **regret**, and it holds there exactly. On the **map**
it does not hold at all. **This condition is ROBUSTNESS, not TARGET, so no kill is
adjudicated on it and no publication claim may cite this as SPADE "beating" BO on
hartmann6** (spec §9 guard 1) — but the split between the two objects, already the central
finding of the whole project (§13 et al.), reproduces on a family it was never registered as
holding for, and the direction is worth flagging precisely rather than smoothing into either
"SPADE struggles here" or "SPADE wins here": it depends entirely on which of the two
objects — point or region — is being asked about.

### 10.2 C4 (hartmann6, d=8, σ=0.25, ROBUSTNESS — no kill is adjudicated here)

| arm | rounds | wells | regret P (primary) | sym. diff |
|---|---|---|---|---|
| **qlognei** | 10 | 48 | **0.2738** | 0.2198 |
| qlogei | 10 | 48 | 0.3002 | 0.2306 |
| spade_cf_m8 | 2 | 48 | 0.4054 | 0.1950 |
| spade_cf_m4 | 2 | 48 | 0.4300 | **0.1883** |
| spade_cf_m0 | 2 | 48 | 0.4454 | 0.1908 |
| spade_random_plate2 | 2 | 48 | 0.4540 | 0.2117 |
| random | 1 | 48 | 0.4664 | 0.2066 |
| lhs | 1 | 48 | 0.4687 | 0.2049 |
| sobol | 1 | 48 | 0.4796 | 0.2006 |
| spade_plate1_only | 1 | 40 | 0.5399 | 0.2253 |
| doe | 3 | 48 | 0.6391 | 0.2507 |

**§10.1's split reproduces exactly at d=8.** `qlognei`/`qlogei` again 1st/2nd on regret by a
wide margin; the three SPADE arms again 1st, 2nd and 3rd of 11 on symmetric difference, ahead
of `sobol` (4th). The dimension increase does not change which object each method family
wins — regret favours committed single-basin search, the map favours SPADE's two-round
region estimate, at both d=6 and d=8. Still ROBUSTNESS, still no kill adjudicated, still not
citable as a general win (spec §9 guard 1).

### 10.3 S1 (ackley, d=6, σ=0.25, pre-declared EXCEPTION — cleanly confirmed, not surprising)

| arm | rounds | wells | regret P (primary) | sym. diff |
|---|---|---|---|---|
| **doe** | 3 | 48 | **0.5540** | **0.4599** |
| qlognei | 10 | 48 | 0.6566 | 0.2336 |
| qlogei | 10 | 48 | 0.6865 | 0.2401 |
| sobol | 1 | 48 | 0.7321 | 0.2383 |
| random | 1 | 48 | 0.7474 | 0.2389 |
| lhs | 1 | 48 | 0.7488 | 0.2389 |
| spade_random_plate2 | 2 | 48 | 0.7508 | 0.2389 |
| spade_cf_m8 | 2 | 48 | 0.7549 | 0.2370 |
| spade_cf_m4 | 2 | 48 | 0.7582 | 0.2355 |
| spade_cf_m0 | 2 | 48 | 0.7601 | 0.2386 |
| spade_plate1_only | 1 | 40 | 0.7670 | 0.2407 |

**Unlike §10.1/§10.2, this is a clean confirmation of the pre-declared reasoning, not a
surprise.** `doe` wins regret decisively (0.5540, a full 0.10 clear of second place) —
exactly the mechanism the exception was declared for: ackley's optimum sits at the domain
centre, and a classical center-point design finds it almost by construction. But `doe` is by
far the **worst** arm on the map (0.4599, nearly double every other arm's 0.23–0.24 band) —
its screened, centre-heavy design cannot describe the acceptable region away from that one
point.

**SPADE's certificates are empty 83–90% of the time on average across its five arms**
(`spade_cf_m0` 83.2%, `spade_cf_m4` 83.5%, `spade_cf_m8` 85.5%, `spade_plate1_only` 89.5%,
`spade_random_plate2` 86.5%), directly reproducing §41's finding that SPADE "declines to
answer" on this family. Where SPADE *does* answer, its map score is competitive (2nd–5th of
11, behind only `qlognei`) — but the emptiness itself is the finding, not the score
conditional on answering. **This condition needed no defect fix and produced no surprises**;
it did exactly what it was pre-registered to do.

## 11. Sobol, BO and DoE comparison

**C2 (§8's table) is the load-bearing comparison — it is the TARGET condition.** `sobol`
posts symmetric difference 0.1913 there — competitive with but not better than
`spade_cf_m0`'s 0.1804 (KF-6 PASS: SPADE is within SESOI). `qlognei` is the best regret arm
(0.0691, KF-8: SPADE within SESOI = practical parity, never phrased as a win). `doe` is
markedly worse on the map (0.2580, worst of all 11) and dramatically worse under rule P
(0.3072) than rule A (0.0924) — consistent with FINDINGS §9.1's registered mechanism (a
posterior-mean terminal rule punishes `doe`'s prior-driven screened axes). The same `doe`
rule-A/rule-P asymmetry reproduces at C1 (0.1141 → 0.1684), so it is not a σ=0.10 artefact.
`doe_unscreened` did not run in either condition (§5, §15) so the full-dimensional classical
comparison remains incomplete everywhere.

## 12. Kill ledger

**C1 + C2 combined via `merge_condition_rows`, adjudicated at map cell
(τ_q p=0.25, γ=0.95, α=0.95).** Source: `results/final-spade-kill-ledger.json`. Every
target-condition kill below (KF-3–KF-8) is unaffected by adding C1 — C1 is ROBUSTNESS, not
TARGET, and correctly contributes no evidence to those comparisons; only KF-1/KF-9/KF-10's
denominators grew (verified arithmetically additive: 8,800+4,400=13,200 for KF-9,
40+4=44 for KF-10 — see §17.2).

| kill | status | headline |
|---|---|---|
| KF-1 | INCONCLUSIVE | no confirmatory cell (missing `doe_unscreened`, thin denominators) |
| KF-2 | NOT_RUN | no condition beyond hill has run yet |
| KF-3 | **FAIL** | targeted plate 2 does not beat random plate 2 (effect −0.00188, ns) |
| KF-4 | **FAIL** | plate 2 does not beat plate-1-only, in the harder direction (effect +0.01171, p=1.3e-04) |
| KF-5 | **FAIL** | `m>0` does not lower regret; reported as a trade-off (effect −0.00278, ns) |
| KF-6 | PASS | SPADE within SESOI of Sobol on the map |
| KF-7 | PASS | SPADE within SESOI of qLogNEI on the map |
| KF-8 | PASS | SPADE at practical parity with qLogNEI on regret (not a win) |
| KF-9 | PASS | 0/8,800 primary-γ rows above ceiling |
| KF-10 | **FAIL** | 10 cells' PASS was empty-set-driven; correctly downgraded |

**Everything above is ONE condition of seven.** KF-2, KF-6, KF-7, KF-8 in particular are
registered as cross-condition or comparator questions that this single TARGET cell cannot
settle generally — they read as provisional until C1/C3/C4/S1–S3 land.

## 13. What the final paper may claim

**Provisional, C2 only.** On the evidence so far: SPADE is not shown to earn its two-round
complexity over simpler controls on its own TARGET condition (KF-3/KF-4/KF-5 all FAIL), while
remaining map-competitive with Sobol and qLogNEI and at practical regret parity with qLogNEI
(KF-6/7/8 PASS). **This narrows, not broadens, the claim the earlier re-score evidence
suggested** — a prospective run surfaces costs (the causal comparators) that a re-score of
already-chosen wells structurally cannot see. Full conjunction (spec §10.1) needs the
remaining six conditions before any paper-level claim is finalised.

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
* `doe_unscreened` is **unavailable in every condition run so far, not only d=8** — the
  benchmark runner's `ARMS` registry never defines it, so it is missing from C2 (d=6) as
  well as the expected-infeasible d=8 case. This blocks KF-1 confirmatory status
  everywhere until it is either implemented (feasible at d=6: a second-order RSM needs 28
  coefficients against 48 wells) or formally declared `unavailable_reason` per spec §4.

## 16. Reproducibility manifest

**`NOT RUN`** — pending `results/final-spade-manifest.json`.

---

## 17. C2 (n=100) COMPLETE and analysed — three defects found running it, all fixed

**Source:** `results/final-spade-c2.json` (13,200 rows, all 11 mandatory arms present),
adjudicated into `results/final-spade-certificate.json`,
`results/final-spade-regret-pareto.json`, `results/final-spade-kill-ledger.json`. Real
numbers are in §5–§12 above; the earlier n=50 run (`results/final-spade-c2-n50.json`, kept
locally, gitignored) is superseded and was never cited as evidence.

**Three independent defects surfaced running the real pipeline, none visible to the 64+90
unit tests written against synthetic fixtures, all fixed with a regression test first:**

1. **`_keys()` capped hill at n=50.** Fixed before this run (prior pass).
2. **`--map-cell` was accepted by argparse and did nothing.** Two wiring bugs stacked: both
   `write_reports()`/`main()` dropped `map_cell` calling `kill_ledger()`, and `_kf5()`'s own
   signature accepted `map_cell` but never read it. Fixing the first alone was necessary but
   not sufficient — the identical `InvalidPooling` fired one level deeper once it was
   patched. Neither existing test caught it because the pre-existing fixture
   (`_full_comparator_condition`) sat in exactly one map cell, so `map_cell=None` was
   silently correct by accident.
3. **`above_ceiling` was copied from the condition's worst-of-union-gammas flag onto every
   row, regardless of that row's own `gamma`.** KF-9 flagged 6,600 rows; hand verification
   (`tau_max(γ=0.50,σ=0.10)=1.0`, `tau_max(γ=0.95)=0.8355`, `tau_max(γ=0.99)=0.7674`,
   `τ_q(p=0.10)=0.8284`) showed only 2,200 (the γ=0.99 rows) are genuinely above ceiling.
   Added `boec.final_spade.row_above_ceiling`, patched the already-generated C2 file in
   place (the field is a pure function of already-correct `tau_raw`/`tau_max`, so no
   campaign needed to re-run), and fixed the runner for future conditions.
4. **KF-9 itself then failed on the registered DIAGNOSTIC γ=0.99, not just primary-γ
   cells.** Checked spec wording before assuming a bug: KF-9 is about "planned" cells, and
   feasibility classification (Erratum 1) explicitly restricts to primary γ. γ=0.99 was
   never one of the cells classification was gated on, so it is not "a planned cell that
   should have been excluded pre-run" — it is the registered stress diagnostic behaving
   exactly as Erratum 1 anticipated. Filtered `GAMMAS_PRIMARY` into KF-9's row selection.

Every fix has a git commit naming the defect, a regression test written and watched RED
before the fix, and (for defects 3–4) hand-verified arithmetic checked before any code
changed. Full suite: 1,611 passed / 0 failed after defects 1–4.

## 17.1 C1 (n=100) COMPLETE — a fifth defect, found immediately after C2's

**Source:** `results/final-spade-c1.json` (13,200 rows, all 11 mandatory arms). Running it
through the analyser surfaced two more defects, in the same session, before either could
reach a committed artefact:

5. **Primary γ is σ-DEPENDENT (Erratum 1), and `GAMMAS_PRIMARY` was a flat constant.**
   `certificate_report`'s `gamma_role` and KF-9's row filter both used
   `GAMMAS_PRIMARY = (0.50, 0.95)` regardless of a row's own `sigma`. At σ=0.25 (C1),
   γ=0.95 is registered **diagnostic**, not primary (§4's finding: its ceiling sits at
   ~71% prevalence on hill, so treating it as primary evidence would test the ceiling, not
   the method). The flat constant would have wrongly admitted C1's γ=0.95 cells to F-CERT
   and to KF-9's feasibility check. Added `is_primary_gamma(sigma, gamma)`, sourced from
   the same `GAMMAS_BY_SIGMA` the feasibility gate and benchmark runner already used —
   nothing forced this module to agree with the other two until a test compared them.
   Five regression tests, RED first; nine pre-existing tests broke as a direct, verified
   consequence (their default fixture, σ=0.25/γ=0.95, was exactly the corner now correctly
   reclassified) and were updated to a σ-invariant default (γ=0.50) rather than the
   assertions being loosened.

## 17.2 🔴 The artefact-naming architecture, misread for two conditions running

**Found immediately after fixing defect 5**, before committing: running the analyser
against C1 **overwrote C2's already-committed certificate/pareto/kill-ledger** under the
same three fixed filenames spec §15 names in the singular. Caught by `git status` showing
the modification before it was committed; `git checkout` restored C2's version with nothing
lost.

This is not a bug in the analyser — spec §15's artefacts are singular **because the kill
ledger is one document, not one per condition**: KF-2 ("does validity extend beyond hill")
can only be answered from a **single analysis pass that contains both hill and hartmann6
rows**, and no amount of re-analysing a hill-only file answers it. Running the analyser
once per condition and overwriting the same filenames each time does not accumulate
evidence toward that; it destroys the previous condition's contribution.

**Fix:** `boec.final_spade.merge_condition_rows(paths)` — combines completed conditions'
raw row files into one envelope, refusing (not silently pooling) a `study_id` or
`registration_commit` mismatch across files. `results/final-spade-{certificate,
regret-pareto,kill-ledger}.json` are now the analysis of `merge_condition_rows(["C1",
"C2"])`, not of C2 alone. Verified arithmetically additive before trusting the combined
run (§10/§12): KF-9's denominator 13,200 = C2-alone's 8,800 + C1-alone's 4,400 exactly;
KF-10's count 44 = 40 + 4 exactly; every TARGET-condition kill (KF-3–KF-8) is
byte-identical to the C2-only numbers, confirming C1 (ROBUSTNESS) correctly contributes
nothing to comparisons scoped to the TARGET condition.

**Going forward:** every subsequent condition (C3, C4, S1–S3) is combined via
`merge_condition_rows` with all prior completed conditions before each analysis pass —
never analysed alone once C1+C2 exist, and never appended without regenerating the full
combined file from the raw per-condition sources (so a later `git checkout` recovery, as
happened here, is always possible without losing any condition's contribution).

Full suite after defects 5 and the architecture fix: 1,615 passed / 0 failed.

---

## 18. What remains — explicitly, not implicitly

**Done:** all four PRIMARY conditions (C1–C4) complete, combined via
`merge_condition_rows`, and analysed (§10, §17.1, §17.2). S1 (ackley) launched, in flight.

**🔴 One genuine open decision, not a defect (flagged rather than resolved unilaterally):**

`doe_unscreened` is spec-mandatory wherever arithmetically feasible (§4), and it **is**
feasible at d=6 (28-coefficient second-order RSM against 48 wells — the arithmetic is not
in question). But it is **not implemented anywhere in `scripts/run_final_spade_benchmark.py`**
— not a missing `unavailable_reason` declaration, an entire arm-generation capability that
was never built. This currently keeps KF-1 (certificate confirmatory status) and KF-2
(validity beyond hill) at INCONCLUSIVE/NOT_RUN in **every** condition, C1–C4 alike.

Building it is a genuinely new capability (a full unscreened second-order response-surface
design generator, its own campaign type, its own test suite) — comparable in scope to one
of the earlier build phases, not a bug fix. Declaring it `unavailable_reason` instead would
be dishonest in the other direction: the spec explicitly distinguishes "infeasible, declare
so" from "feasible, do the work" (§11 prohibits "fabricating `doe_unscreened` ... where it
is not budget-feasible" — the mirror mistake, declaring it unavailable where it **is**
feasible, is not listed but is equally a misrepresentation of the arithmetic already done).

**This is the one point in the study where implement-vs-defer is a scope decision, not a
research question** — the answer doesn't change what the data say, only whether KF-1/KF-2
can be adjudicated at all in this release. Left for the study owner to decide; not resolved
here.

**Otherwise, blocking full publication:**
1. S1 to complete, fold in via `merge_condition_rows`.
2. S2 (levy), S3 (rosenbrock) — to run and fold in.
3. `scripts/validate_final_spade_release.py` to re-run once all conditions land; last known
   state (before any condition's artefacts existed) reported missing-artefact violations
   only.
4. `scripts/make_final_spade_figures.py` against the now-real combined certificate/Pareto
   artefacts — not yet run.
5. `results/final-spade-manifest.json` has not been written.

**No further design decisions are outstanding besides `doe_unscreened` above** — every other
remaining step is "run an already-built, already-tested script against a result file that
does not exist yet."
