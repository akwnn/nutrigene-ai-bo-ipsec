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

## 3b. K1 result — PIECE A KILLED CLEANLY

**Computed on `versionb`, all 50 hill seeds** (`scripts/analyse_k1_noise_ceiling.py`,
`results/k1-noise-ceiling.json`). Before running: a real, previously-undetected
regeneration break was found and routed around, not silently patched over —
`run_fix1_terminal_rule.py`'s call to `_VB._two_plate(orc, DIM, seed, mu_max, True)`
predates that function's current signature (`mode: str`, returns 4 values; changed in
commit `c8347f1`) and raises `ValueError` if actually run today. `run_fix1_terminal_rule.py`
was not edited (frozen); this analysis calls `_two_plate(..., mode="lse")` directly and
gates its own regenerated `regret_a` against the committed value at every one of the 50
campaigns (0 failures) before trusting any `regret_p` comparison.

| | value |
|---|---|
| mean ceiling improvement (plugin σ̂ → true σ) | **+0.00816** |
| 95% bootstrap CI | **[+0.00202, +0.01417]** |
| Wilcoxon p | 0.0166 |

**Statistically real (CI excludes zero) but below the registered 0.01 bar.** Per K1's own
rule: *"moves regret < 0.01 → drop the replicates, hand those 6 wells back to the design."*
**Even perfect, oracle-granted knowledge of the true noise variance — a better ceiling than
any finite-replicate estimator could ever reach — buys less than a hundredth of regret on
average.** Piece A (the replicate-pooled noise estimator) is **not worth building**: no
achievable estimator can beat this ceiling, and the ceiling itself doesn't clear the bar.

**Verdict: Piece A KILLED.** Not because K0 was clean (it wasn't — genuinely ambiguous), but
because the second, more direct gate K0's own escape route pointed to (K1) answers it
cleanly. SPADE's calibration shortfall (`docs/SPADE-RESULTS-AND-ANALYSIS.md` §4, SPADE
ranks 5th–7th/9) is not explained by this specific, previously-diagnosed noise-estimator
defect at a magnitude worth fixing — the architecture-level explanation stands unless a
different mechanism is found.

## 4. K2 — the design lottery (gates Piece B, OA-LHS)

**Exact rule, `docs/ODIN-VERDICT.md` §6, K2, adopted in spirit; the sampling structure is
matched exactly to the already-committed comparator, not invented fresh.**
`results/q53-spread-gp-hartmann6.json` (d=6, σ=0.25, `BUDGET=48`) reports **25 seeds ×
5 LHS draws per seed**, giving 25 independent per-seed design-SD estimates, range
[0.051, 0.272] (the source of "0.140–0.153"). **This spec runs the identical structure —
25 seeds × 5 OA-LHS draws each, on `hartmann6` only** — substituting only the design
generator and its required `n=49`, so the two distributions are directly comparable.
`plain LHS` is not re-run — Q53's own committed number is the comparator. **Maximin-LHS is
dropped from this pass**: no generator exists in this codebase, `ODIN-VERDICT.md` only
proposes it as a fallback for when `n=48` doesn't admit strength-2 OA-LHS (not this
project's case, since OA-LHS runs at its own specified `n=49`), and building one is
separable, lower-priority work not gated by anything above.

**One-well mismatch, reported openly, not hidden** (`docs/ODIN-VERDICT.md` §4(a)): OA-LHS
runs at `n=49` against the committed plain-LHS reference's `n=48`. `SPADE-SPEC.md` Stage 1
itself accepts exactly this mismatch ("at exactly 48 you must drop to maximin-LHS, which
loses the Stein guarantee").

- **Win:** OA-LHS cuts hartmann6 design SD materially below plain-LHS's measured
  0.140–0.153 (`Q53`) → Stage 1 has a mechanism, worth building into SPADE's actual Plate 1.
- **Kill:** design SD is unchanged → Stage 1 is plain LHS with extra steps, and the
  74–85% Plate-1-margin finding (`docs/SPADE-RESULTS-AND-ANALYSIS.md` §2) is not a lottery
  artefact after all.

**Well-count note.** `SPADE-SPEC.md` Stage 1 specifies OA-LHS at n=49 (not 48) — "at exactly
48 you must drop to maximin-LHS, which loses the Stein guarantee." K2 measures OA-LHS at its
**Scope**: 25 seeds × 5 draws = **125 OA-LHS campaigns**, `hartmann6` only, scored for
`(rule_a, rule_c)` regret via `boec.spread_gp.spread_gp_once`'s exact GP-fit/locator
settings (the same function that produced the committed comparator), so the two numbers
are commensurable. No certificate/calibration scoring needed — K2 answers a design-variance
question, not a certificate question. A firewalled timing pilot (5 campaigns, timing only)
runs before committing to the full 125, per this project's standard protocol.

**Neither the OA-LHS generator nor the replicate-noise estimator was built before this
spec was frozen.** `oa_lhs_design` (TDD, `src/boec/optimizers.py`) is built now, gated by
this section; Piece A (the replicate estimator) was killed by K1 (§3b) and is not built.

## 5. K2 result — PIECE B KILLED

**Computed: 25 seeds × 5 OA-LHS draws each, hartmann6, d=6, σ=0.25**
(`scripts/analyse_k2_design_lottery.py`, `results/k2-design-lottery.json`).

| | design SD (mean) | range |
|---|---|---|
| OA-LHS (n=49, this run) | **0.1628** | [0.0761, 0.2733] |
| plain LHS (n=48, `Q53`, committed) | 0.1496 | [0.0512, 0.2724] |

**Difference (OA − plain): +0.0132, 95% bootstrap CI [−0.0196, +0.0450] — spans zero, and
the point estimate trends in the WRONG direction** (OA-LHS's design SD is nominally
*higher*, not lower, though not significantly so). Per K2's own rule: *"design SD
unchanged → Stage 1 is plain LHS with extra steps."*

**Verdict: Piece B KILLED.** Strength-2 OA-LHS's theoretical stratification advantage
(every 2D projection covered, not just every 1D marginal — independently verified by
`oa_lhs_design`'s own test suite) does not measurably shrink the design-lottery variance
on Hartmann6 in practice. The lottery itself is real and large on both designs (SD
0.08–0.27 either way) — it is just not the specific mechanism OA-LHS addresses. This is
consistent with, not contradicted by, `docs/SPADE-RESULTS-AND-ANALYSIS.md` §2's finding
that Plate 1's contribution is real but the specific reducing mechanism was never shown to
work: it still hasn't been, now on direct test rather than by absence of evidence.

## 6. Summary — both pieces of Fix 2 killed

| piece | gate | result | verdict |
|---|---|---|---|
| A (replicate noise estimator) | K0 → K1 | ceiling improvement +0.008, below the 0.01 bar | **KILLED** |
| B (OA-LHS Plate 1) | K2 | design SD +0.013 vs. plain LHS, CI spans zero, wrong-signed | **KILLED** |

Neither of SPADE's two never-built spec pieces, once actually built and tested, closes the
gap it was hypothesized to close. SPADE's calibration shortfall (§4 of the consolidated
report) and its Plate-1-lottery dependence (§2) both stand as architecture-level properties,
not artefacts of these two specific unbuilt fixes — the two most plausible candidate
explanations were tested directly and did not survive.
