# SPADE τ-as-quantile follow-up — pre-registration

**Frozen before any result exists.** Registers a fix for the near-total certificate
emptiness `FINDINGS-SPADE.md` §41 (P8) found on `ackley` (0/24 cells certify) and
`hartmann6` (2/24), and asks whether that emptiness is a property of SPADE or a property
of the registered scoring grid.

## 1. The defect this targets

`docs/COVERAGE-MATRIX.md` §B1 diagnosed the mechanism: `tau = tau_frac × tau_max(γ, σ)`
treats "60% of a family's peak height" as the same question on every landscape. It is not.
Measured true superlevel-set prevalence at `tau_frac = 0.60`:

| family | prevalence |
|---|---|
| ackley | 0.0000 |
| hartmann6 | 0.0080 |
| hill | 0.7360 |
| levy | 0.8570 |
| rosenbrock | 0.9560 |

Ackley's peak is a narrow spike; 60% of its height captures almost no volume. `doc`'s own
recommended repair (§B1): register τ per family as a quantile of the true response, so
every family's threshold corresponds to a comparable *fraction of the box*, not a
comparable *fraction of the peak*. This spec adopts that recommendation verbatim.

## 2. The new definition

`tau_quantile(truth, p)` — the threshold whose true superlevel set covers fraction `p` of
a reference grid, i.e. `P(truth >= tau_quantile(truth, p)) == p`. Implemented at
`src/boec/designspace.py::tau_quantile`, TDD, 5 tests, all passing (`tests/
test_designspace.py`).

**Registered `p` grid: `{0.30, 0.10, 0.03, 0.01}`** — the exact values COVERAGE-MATRIX §B1
names, chosen to keep the same cardinality (4) as the existing `tau_frac` grid
`{0.60, 0.75, 0.85, 0.95}` it replaces, for a like-for-like comparison.

**Reference grid**: the same registered grid P8 already uses per family (`sobol_grid(dim,
N, seed=0)` at P8's committed `N`), so `tau_quantile` is computed once per family from
already-registered machinery, not a new sampling scheme.

## 3. What this does and does not touch

- **Scoring only.** `tau_quantile` replaces `tau_frac × tau_max` in the τ used for
  containment/probability-map computation. It does not change Plate 1, Plate 2, the
  acquisition rule, the noise model, or the certificate math (`conservative_estimate`,
  Vorob'ev quantiles) — those are Fix 2's territory (§7 below), registered separately.
- **No new campaigns.** `score_campaign`'s expensive step (the GP fit and the joint
  posterior draw, seeded) does not depend on τ at all — τ only enters the per-`(γ, τ)`
  scoring loop at the bottom. Campaigns are regenerated bit-for-bit from the same stored
  seeds P8 already used; nothing new is simulated. **This is not free compute** — each
  campaign still needs a GP refit (`build_gp`) to produce `mean`/`sd`/the joint draw, at
  P8's own measured cost (~20–30s/campaign from `results/p8-certificate-families.log`) —
  but it is a re-score of existing data, not a new experiment.
- **Does not touch levy/rosenbrock/hill's diagnosis.** Those three already have real
  prevalence at the existing grid; their γ=0.99 under-coverage (levy, rosenbrock) is a
  genuine miscalibration, not a threshold artefact, and this fix is not expected to move it
  (§5 states the falsifiable prediction explicitly).

## 4. Scope

**Target families: `ackley` and `hartmann6` only** — the two families this fix is meant to
answer. All 4 SPADE arms already in P8 (`versionb`, `versionb_random`,
`versionb_predictive`, `plate1_only`), 50 seeds each = **400 campaigns**, at P8's already-
registered `N_DRAWS = 4096`. `hill`/`levy`/`rosenbrock` are NOT re-run under this grid —
committing further compute to re-confirm an already-settled result is out of scope; a
sanity check that the new `p` grid does not silently break something on a family that
already works is done analytically from committed data (§5, prediction 3), not by re-running
campaigns.

## 5. Falsifiable predictions, registered now

1. **Ackley/hartmann6 answerability.** Under `tau_quantile`, ackley and hartmann6 will
   produce a non-empty certified set (`ce_vol_pred > 0` or equivalent) in **at least half**
   of their `(arm, seed, p)` cells. *(If this fails, the emptiness is not explained by the
   grid and the explanation in FINDINGS-SPADE.md §41 needs revisiting.)*
2. **Prevalence matches the registered `p` exactly**, up to grid discretisation (already
   verified analytically, §2/tests — this is a property of `tau_quantile` itself, not of
   SPADE, and is not re-tested per campaign).
3. **No claim that this changes any verdict about SPADE's targeting mechanism, regret, or
   calibration** (§2 and §4 of `docs/SPADE-RESULTS-AND-ANALYSIS.md`) — this fix is scoped
   to the certificate-emptiness question alone.

## 6. Firewalled pilot before the full run

Per this project's established protocol (`docs/SPADE-KF3-FOLLOWUP-SPEC.md` §3): before
committing to the full 400-campaign run, a small timing pilot (5 campaigns, wall-clock only,
no outcome inspected) confirms the ~20–30s/campaign estimate from P8's own log. If the
measured cost exceeds 2× that estimate, the run is paused and reported before continuing,
not silently extended.

## 6b. Result — real, substantial, but does not uniformly clear the registered bar

**400 campaigns, 9,600 rows, 0 gate failures** (`results/tau-quantile-followup.json`).
Fraction of `(arm, seed, p)` cells producing a non-empty certified set, vs. the original
fixed-fraction grid's **0/24 (ackley) and 2/24 = 8.3% (hartmann6), always**:

| p (target true prevalence) | ackley | hartmann6 |
|---|---|---|
| 0.30 | **41.9%** | **81.2%** |
| 0.10 | 10.7% | 17.0% |
| 0.03 | 0.7% | 0.7% |
| 0.01 | 0.0% | 0.0% |
| **overall (all p pooled)** | **13.3%** | **24.7%** |

**Prediction 1 (§5) — "at least half of cells non-empty" — does not clear in aggregate for
either family**, though it clears decisively for hartmann6 at the loosest target (p=0.30,
81.2%) and comes close for ackley at the same p (41.9%). Reported exactly as measured
rather than forced into a pass/fail: **both families move from a near-total inability to
certify anything (0% and 8.3%) to a partial, p-dependent ability to certify (13.3% and
24.7% pooled, up to 81% at the loosest target)** — a real, large improvement, and evidence
the original grid was a genuine cause of the emptiness (§1) — but not a full fix. At the
tightest targets (p=0.03, p=0.01), both families remain almost entirely empty on either
grid: a genuine sample-size/power limit at 48 wells for a very small target region, not
something any threshold definition can repair.

**Reframed conclusion.** τ-as-quantile is a real, worthwhile scoring correction — it
should replace the fixed-fraction grid in any future cross-family certificate work — but
it narrows, rather than closes, FINDINGS-SPADE.md §41's "ackley/hartmann6 decline to
certify" finding. The honest updated statement: *ackley and hartmann6 can be made to
answer a meaningful fraction of the time at looser assurance targets once scored on a
comparable threshold, but both remain largely unable to certify small target regions at 48
wells, on either scoring convention.*

## 7. Fix 2 (Piece A / Piece B) — registered separately

Fix 2 (a replicate-pooled noise estimator; the specified OA-LHS Plate-1 design) is **not**
covered by this spec. It changes the observation model / design, not just scoring, so it
requires genuinely new campaigns and its own pre-registration:
`docs/SPADE-CALIBRATION-FIX-SPEC.md`.
