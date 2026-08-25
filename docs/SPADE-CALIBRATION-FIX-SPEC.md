# SPADE calibration-fix follow-up — pre-registration ("Fix 2")

**Frozen before K0 is computed.** Registers the two never-built spec pieces flagged in
`docs/SPADE-RESULTS-AND-ANALYSIS.md` §1b: a replicate-pooled noise estimator (Piece A,
`SPADE-SPEC.md` Stage 2) and a strength-2 OA-LHS Plate-1 design (Piece B, Stage 1).

## 0. A correction to the plan as described to the user

Piece A was described as "build it, then test whether it closes the γ=0.99 gap." That
skips a cheap, already-registered gate this project's own prior audit
(`docs/ODIN-VERDICT.md` §2, "Stage 2 is refuted at the mechanism level, not merely at the
arm level") puts *before* building it: **Q30 already measured that doubling surrogate
accuracy (an additive kernel, 0.375→0.744 held-out R²) moves regret by 0.0015, p=0.71 —
6.7× below this project's own G6 gate bar of 0.01.** ODIN-VERDICT's reading: *"Stage 2 is
an accuracy intervention. The accuracy channel is measured to be closed."* It registers one
narrow escape route, **K0**, and instructs building Stage 2 only if K0 opens it. This spec
runs K0 first, for free, from already-committed data, before any new code or campaign.

Piece B has its own already-registered gate, **K2** (design lottery), which is not free —
it needs new campaigns — and is registered separately below (§4).

## 1. K0 — does sup-norm error or R² govern regret? (gates Piece A)

**Exact rule, from `docs/ODIN-VERDICT.md` §6, K0, adopted verbatim:**

> Refit the stored campaigns' GPs [not needed — both columns are already committed], and
> correlate `sup_err` (max\|E[f(x)] − f(x)\|) and `grid_r2` against realised regret across
> all 200 stored campaigns, via Spearman ρ with a paired bootstrap on the difference of the
> two correlations.
>
> **Kill:** R² correlates with regret at least as strongly as `sup_err` → the L∞ thesis is
> dead → **Stage 2 (Piece A) stays deleted, permanently.**
> **Revive:** `sup_err` correlates and R² does not → Q30 improved the wrong norm → Piece A
> goes back on the table, and gets its own gate before being built.

**Source data**: `results/p2-versionb-gamma.json` — 4,800 rows, `sup_err`/`grid_r2`/`regret`
per row, constant within each of 200 unique `(arm, seed, instance)` campaigns (each campaign
appears 24× — once per `(gamma, tau_frac)` scoring cell). **Dedupe to one row per campaign
before correlating** — using all 4,800 rows would inflate `n` 24× and fabricate
significance from a single underlying observation repeated 24 times.

**Registered statistic**: `ρ(sup_err, regret)` and `ρ(grid_r2, regret)` (note: R² is
"higher is better," `sup_err` is "lower is better," so the kill/revive comparison is on
`|ρ|`, and sign is reported alongside so the direction is never lost). 4,000-resample
paired bootstrap on `|ρ(grid_r2, regret)| − |ρ(sup_err, regret)|`, `default_rng(0)`, matching
this project's standard bootstrap convention used throughout (`docs/FINDINGS-SPADE.md`).

**No campaigns run for K0. Computed once, immediately after this freeze, from disk alone.**

## 2. K1 — does Piece A actually help, if K0 revives it? (only runs if K0 revives)

Registered but conditional: `docs/ODIN-VERDICT.md` §6 K1 grants both arms the *true* σ
(oracle access to the real noise variance, not a plugged-in estimate) as a ceiling check —
"a ceiling, not an estimate. Replicates give you σ̂, not σ." If the ceiling itself moves
regret by <0.01, replicates are dropped regardless of K0's outcome, before any replicate
machinery is built. **Not run in this pass** unless K0 revives Piece A.

## 3. K0 result

**Computed once, from `results/p2-versionb-gamma.json`, 200 unique campaigns**
(`scripts/analyse_k0_calibration_gate.py`, `results/k0-calibration-gate.json`):

| statistic | ρ (vs. regret) | p |
|---|---|---|
| `sup_err` | **+0.335** | 1.25e-06 |
| `grid_r2` | **−0.318** | 4.51e-06 |

`|ρ_grid_r2| − |ρ_sup_err|` = **−0.0171**, 95% bootstrap CI **[−0.160, +0.118]**
(4,000 resamples).

**Literal point-estimate reading: REVIVE** (`sup_err` correlates marginally more strongly
than `grid_r2`, so under the registered rule's plain wording Piece A is not immediately
killed). **But this is not a confident revival.** The bootstrap CI on the *difference*
comfortably spans zero — the data at n=200 campaigns cannot distinguish which channel
governs regret more strongly. Both `sup_err` and `grid_r2` are, individually, strongly and
significantly correlated with regret (ρ ≈ 0.32–0.34, both p < 5e-06) — the honest finding
is that **surrogate accuracy along both norms tracks regret about equally well, and K0 as
registered does not resolve which one is closer to causal.**

**Decision, given the ambiguity, and given Piece A's real cost (new replicate-carrying
campaigns, a new well-budget accounting, new noise-estimator code, then a full re-run of
the certificate benchmark to check whether it helps at γ=0.99) — this is reported back
rather than auto-decided.** Building Piece A on a gate this marginal is not obviously
justified by the gate's own logic, which was designed to give a clean kill/revive read
and did not. Not proceeding to build Piece A without an explicit decision to do so despite
the ambiguity.

## 4. K2 — the design lottery (gates Piece B, OA-LHS)

**Exact rule, `docs/ODIN-VERDICT.md` §6, K2, adopted verbatim:** 20 design draws each of
{plain LHS, maximin-LHS, strength-2 OA-LHS at n=49}, at d=6, on **hill and hartmann6**
(the tie family and the lose family — not the full 5-family sweep). Report **design SD**
of regret across the 20 draws per design type, not mean regret.

- **Win:** OA-LHS cuts hartmann6 design SD materially below plain-LHS's measured
  0.140–0.153 (`Q53`) → Stage 1 has a mechanism, worth building into SPADE's actual Plate 1.
- **Kill:** design SD is unchanged → Stage 1 is plain LHS with extra steps, and the
  74–85% Plate-1-margin finding (`docs/SPADE-RESULTS-AND-ANALYSIS.md` §2) is not a lottery
  artefact after all.

**Well-count note.** `SPADE-SPEC.md` Stage 1 specifies OA-LHS at n=49 (not 48) — "at exactly
48 you must drop to maximin-LHS, which loses the Stein guarantee." K2 measures OA-LHS at its
specified n=49 for exactly this reason; the one-well mismatch against this project's 48-well
baseline is reported openly, not silently absorbed, per `ODIN-VERDICT.md` §4(a).

**Scope**: 20 draws × 3 design types × 2 families = **60 design draws**, each scored for
regret only (no certificate/calibration scoring needed at this stage — K2 answers a design-
variance question, not a certificate question). A firewalled timing pilot (5 draws, timing
only) runs before committing to the full 60, per this project's standard protocol.

**This spec does not yet build the OA-LHS generator or the replicate-noise estimator.**
Both are gated; §3/§5 record whether either gate opens before either is built.

## 5. K2 result

<!-- Filled in after the pilot and full run. -->
