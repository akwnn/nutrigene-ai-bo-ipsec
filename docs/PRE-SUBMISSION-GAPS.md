# Pre-submission gaps

**What this is.** Every hole found in a full audit of the paper as it stands, with the evidence for
each, what closing it requires, and whether closing it can move a number that is currently in print.
Written to be executed from, not read once.

**Audited 2026-08-20.** Branch `q60-q61-tost`, last commit `f697724`, working tree dirty.
Test suite at audit time: **832 passed, 1 failed, 152 s**.

**Scope.** Everything here is doable with the current repo and compute. No wet-lab work appears in
this document. The applied/wet-lab programme is a separate track and does not block any item below.

**Rule for this file.** Each finding separates what was *verified* from what is *inferred*. Where an
item says the evidence is a stated assumption rather than a computed value, that is the finding —
do not close it by restating the assumption.

---

## Priority A — can change a number that is currently in print

### G1. The fair-comparison cell is an asymmetric comparison

**Finding.** Table 3's primary contrast compares a **constrained** quadratic against an
**unconstrained** GP. The GP's in-region value was never computed.

**Evidence (verified).**
- `src/boec/paper_figures.py:3-5` — "GP in-region uses the stored unconstrained GP peak, which the
  manuscript states already lies inside the sampled region."
- `results/q35-constrained-rsm.json` — 200 rows, DoE arm only. Has `constrained` and
  `unconstrained` for the quadratic. **No GP fields at all.**
- `results/q34-factorial.json` — 200 rows. Has `cell4_bo_gp` (one GP-on-BO-wells value). **No
  constrained/in-region GP field.**
- Neither file records, per instance, whether the GP peak lies inside the sampled region.

**Why it matters.** Table 3 primary is quadratic 0.1169 vs GP 0.1232, contrast **−0.0063
[−0.0233, +0.0107]**. That contrast carries the paper's entire fair-readout argument — it is the
answer to "what would a careful RSM practitioner actually ship?". It is currently justified by a
manuscript assertion with no per-instance check behind it. This is the sharpest available attack on
the paper and it is in our own source file, in writing.

**To close.**
1. For every stored BO campaign, compute the GP posterior-mean peak and test containment in the
   sampled region using the same region definition the quadratic arm uses.
2. Report the containment fraction as a number in the paper.
3. Where the peak falls outside, compute a properly constrained GP peak and rescore.
4. Re-derive Table 3 and Figure 1's GP in-region bars from the new field, not from the
   unconstrained value.
5. Store as a new `results/` file with Q-numbered provenance. Do not overwrite q34 or q35.

**Effort.** Hours. **Can move a printed number:** yes — Table 3 primary, Table 3 all four cells,
Figure 1 in-region bars, and the "GP in-region = GP unconstrained" sentence in the text.

**Do this before G2.** If Table 3 shifts, the power extension must be pointed at the corrected
contrast.

---

### G2. The primary fair-comparison contrast is underpowered, not null

**Finding.** In-region primary is **inconclusive**: MDE ≈ 0.027 against a SESOI of 0.02. The design
cannot resolve the effect it was built to test.

**Evidence (verified).** Table 3, `docs/RESEARCH-SUMMARY.md`. n = 25 landscapes × 2 seeds averaged.

**Why it matters.** The point estimate is −0.0063 — small. With adequate power the likely outcome is
a **declared equivalence**, which is a materially stronger claim than "inconclusive" and is the
sentence that makes the terminal-rule thesis land: the entire gap lives in the readout, not in the
method. As written, the paper's central fair comparison says nothing.

**To close.**
1. Extend the committed ensemble from 25 to 100 landscapes using
   `generate_ensemble(dim, n_instances, cfg, seed0=...)` in `src/boec/oracles.py:966`, continuing
   from the last accepted seed so **landscapes 1-25 remain bit-identical**. Do not redraw.
2. Keep the same `SamplerConfig`. A changed config is a different oracle family and voids the
   comparison.
3. Run **both** confirmatory contrasts at the new n — measured-value argmax and in-region
   recommendation. Running only the inconclusive one is cherry-picking and will be read as such.
4. Report n = 25 as the prespecified primary and n = 100 as a declared post-hoc power extension.
   Both in the paper. Do not silently replace the registered analysis.

**Arithmetic.** MDE scales as 1/sqrt(n). 0.027 x sqrt(25/100) = **0.0135**, inside the 0.02 SESOI.

**Effort.** Overnight compute. **Can move a printed number:** yes — every interval and every TOST
verdict at the new n.

---

### G3. Top-3 confirmation is underpowered and the run variant is the wrong one

**Finding.** Table 4's confirmation row is **inconclusive** (MDE ≈ 0.042), and the variant that was
run discards the original reading.

**Evidence (verified).** Table 4: −0.0009 [−0.0263, +0.0253]. DoE absolute regret goes
0.0958 -> 0.1437 under confirmation-alone, because the original measurement is thrown away.

**Why it matters.** Real laboratories re-measure and **average**. The averaged variant is specified
as Rule 8 and is unrun. So the one terminal rule closest to actual lab practice is missing, and the
rule that *is* reported degrades DoE for a reason that is an artefact of the rule rather than a
property of the method. A reviewer reading Table 4 will ask exactly this.

**To close.** Fix G7, then run Rule 8. Power it at n >= 110 (25 x (0.042/0.02)^2 = 110), which the
G2 ensemble extension already supplies.

**Effort.** Blocked on G7, then overnight compute. **Can move a printed number:** yes — Table 4.

---

### G4. Two terminal rules rest on a surrogate we have declared untrustworthy

**Finding.** GP latent coverage falls to **76.4%** against a nominal 95%. Intervals that include
observation noise cover about 90-92%.

**Evidence (verified).** `docs/RESEARCH-SUMMARY.md`, Table 3 note and the "Objections already
measured" table.

**Why it matters.** Posterior-mean selection (Table 4) and the GP optimum (Table 3, Figure 1) both
depend on it. The paper currently labels them "conditional on miscalibration," which is honest but
leaves two of seven terminal rules caveated into near-uselessness. Fixing or properly characterising
calibration upgrades both from caveated to usable.

**To close.**
1. Diagnose the source: lengthscale prior, outputscale, noise handling, or the rescaled-axis issue
   flagged in `START-HERE-PERSON-A.md` (prediction noise must go through
   `boec.surrogate.predictive` and nothing else).
2. Attempt a fix. If coverage cannot be brought near nominal, report a calibration curve rather than
   a single worst-case number, so the reader can see where it fails.
3. Re-run the two dependent rules under the fixed or characterised surrogate.

**Effort.** Days. **Can move a printed number:** yes — Table 3 GP column, Table 4 posterior-mean row.

---

### G5. The headline result may be an artefact of a near-separable landscape

**Finding.** The Hill family is **~93% additive**. The headline is that a quadratic identifies
better under noise.

**Evidence (verified).** Stated as a limitation in `docs/RESEARCH-SUMMARY.md`.

**Why it matters.** The obvious objection is that a near-separable surface flatters a second-order
polynomial by construction, so "DoE identifies better" is a property of the test family rather than
of the method. Levy, Rosenbrock and Hartmann6 partly answer it, but none of them is a Hill landscape
with the interaction structure turned up — which is the direct test.

**To close.** Add a strong-interaction Hill variant (raise the interaction term until the additive
share drops materially, e.g. to ~0.7 and ~0.5), rerun the primary cell, and report whether the
measured-argmax DoE lead and the identification share survive. Register the target additive shares
before running.

**Effort.** Overnight compute. **Can move a printed number:** no — it adds a robustness cell. But it
determines whether the headline is defensible.

---

## Priority B — visible holes in what is already on the page

### G6. Figure 1 has empty slots

**Finding.** qLogNEI has no stored model recommendation, so the headline figure has gaps.

**Evidence (verified).** Figure 1 caption, `docs/RESEARCH-SUMMARY.md`.

**To close.** Run the model-recommendation locator on the stored qLogNEI campaigns and refill the
bars. Coordinate with G1 — the in-region locator must be the corrected one.

**Effort.** Hours.

### G7. Two separate replay gates are failing, and they block two unrun rules

**Finding (a) — verified now.** `tests/test_spread_gp.py::test_the_extracted_arm_reproduces_the_committed_q52_rows_exactly`
fails with worst |delta| = **3.123e-07** against the committed Q52 grid. The gate asserts
`worst == 0.0`.

**Finding (b) — recorded in the repo, not re-verified here.** A separate **1e-12** gate on replaying
stored BO visit logs fails after an acquisition-optimizer retry. DoE still matches.

These are two different problems. Fixing one does not fix the other.

**Why it matters.** (a) The magnitude is float32 noise and moves nothing at four decimals, but the
project's stated policy is "JSON wins" with the committed file as the reference — so "our code
reproduces our committed results exactly" is currently false for the one-shot GP arm, which feeds a
headline (24.4/25 in one round) and two columns of Table 5. The audit trail is the credibility of
the paper. (b) blocks Rule 8 (G3) and q=1 BO (G8).

**To close.**
- (a) Find the source of the 3.1e-07 drift between the extracted `spread_gp` arm and the committed
  grid — dtype, device, BLAS ordering, or a library version change. Either restore bit-exactness or,
  if the drift is provably environmental, replace the equality gate with a declared tolerance **and
  say so in Methods**. Do not silently loosen the gate.
- (b) Isolate the acquisition-optimizer retry that breaks determinism; make the retry path seeded and
  replayable.

**Effort.** Hours to days. **Can move a printed number:** unlikely for (a); (b) unblocks new rows.

### G8. q=1 sequential BO is unrun

**Finding.** Specified, blocked on G7(b).

**Why it matters.** Answers "your DoE win is a batching artefact," which is a standard reviewer move
against any batch-BO comparison.

**To close.** Fix G7(b), run at the primary cell, report beside q=4.

### G9. One-shot GP sits at the floor of its own spec

**Finding.** Hill `spread_gp` uses **5** LHS draws. `docs/PROMPTS-NEXT.md` Workstream 4 asks for
">= 5, prefer 10-20."

**Why it matters.** One-shot GP reaching 24.4/25 in a single round is one of the most striking
claims in the paper, and it is resting on the minimum acceptable number of design draws.

**To close.** Rerun at 10-20 independent LHS draws, treat draw as a random factor, pair by
landscape. Do not pool with the Q53 external-family draws.

**Effort.** Overnight compute.

### G10. Figure 3 panel A is a cartoon

**Finding.** The caption says so: "Cartoon of a saddle; not a fitted contour from one run."

**Why it matters.** 200 real saddle fits are sitting in `results/q35-constrained-rsm.json` with
eigenvalues, `ridge_exit_radius`, and `stationary_kind` per instance. A real fitted contour from a
named instance is strictly more convincing and costs about an hour.

**To close.** Replace panel A with a fitted quadratic contour from a named instance; keep the
instance id in the caption.

---

## Priority C — credibility and provenance

### G11. Three load-bearing citations were never verified

**Finding.** **Rummukainen, Lapierre and Ndahiro do not appear anywhere in
`docs/source_verification.md`.** Narayanan is covered (Part 1). Hall/Ogle is covered exhaustively.

**Why it matters.** Those three carry a substantive claim in the introduction — that they match
experiment count but not the final-pick rule, the plate cycles, or which factors each arm keeps.
That is a criticism of three published papers and it is the setup for the entire contribution. If
even one of them prespecified a terminal rule, the sentence and part of the novelty claim change.

**To close.** Read all three PDFs. Record page-level findings in `source_verification.md` under the
existing STATES / IMPLIES / INFERS convention. Specifically confirm:
- Rummukainen: 15-run Box-Behnken vs 5+10 BO; noisy EI then posterior-mean final pick; no reduction
  in experiment count.
- Lapierre: 48-condition screen then CCD/RSM with factors reduced, vs batch BO keeping all factors.
- Ndahiro: CHO media, BO with thermodynamic constraints, same number of experiments.

**Effort.** One day.

### G12. Narayanan's denominator underpins the "both can be correct" framing

**To close.** Read the SI and confirm the predicted-DoE count calculation at page level. Record it.
Note `source_verification.md:117` already flags that Narayanan's continuous kernel is **not
established** — do not cite that paper for a kernel choice.

### G13. Gisperg 2025 is cited but unverified

**To close.** Read the PDF before it stays in the reference list.

### G14. Nothing is citable

**Finding.** The project has locked commits, committed JSON, and replay gates — genuinely strong
provenance — and none of it is externally citable.

**To close.** Public repo plus a Zenodo deposit with a DOI, referenced from Methods. Do this after
G7 so the archived snapshot passes its own gates.

---

## Priority D — consistency and hygiene

### G15. The paper and its own supplement use different names for the same rule

**Evidence (verified).** `docs/RESEARCH-SUMMARY.md`: "measured-response argmax" x4.
`docs/SUPPLEMENT.md`: "measured-value argmax" x11, "measured-response argmax" x1.
`docs/PROMPTS-NEXT.md` checklist item 4 mandates **measured-value argmax**.

**Why it matters.** Two names for the single most important terminal rule, split across a paper and
its supplement, reads as two different quantities.

**To close.** Standardise on **measured-value argmax** everywhere. Same pass should confirm checklist
items 5-7: "terminal decision rule" not "estimand"; "structurally inspired by" not "calibrated to";
"higher-noise / lower-noise" not "realistic measurement noise"; "naive unconstrained quadratic
recommendation" for the diagnostic locator.

### G16. Banned language survives in files that must not leak into the manuscript

**Evidence (verified).** "estimand" appears 7x in `docs/CLAIMS.md`, 1x in `docs/MAIN-LINE.md`, 2x in
`docs/RESEARCH-SUMMARY.md`.

**To close.** Purge from RESEARCH-SUMMARY. For CLAIMS.md and MAIN-LINE.md, either purge or add a
header stamping them "superseded; not a source for the manuscript" — `PROMPTS-NEXT.md` Workstream 0
already warns they carry old scoring-convention language.

### G17. All of the recent work is uncommitted

**Evidence (verified).** Modified: `docs/RESEARCH-SUMMARY.md` (453 changed lines),
`docs/SUPPLEMENT.md` (14). Untracked: `docs/MODELS-EXPLAINED.md`, `docs/figures/` (3 figures, PDF +
PNG), `scripts/make_paper_figures.py`, `src/boec/paper_figures.py`, `tests/test_paper_figures.py`.
297 insertions / 170 deletions total. Unchanged since 2026-08-17 to 08-19.

**Why it matters.** The paper embeds `figures/fig1-terminal-rules.png`; a fresh clone cannot build
it. This is the only item on the list where the downside is losing work rather than being wrong.

**To close.** Commit. Do it first.

### G18. There is no manuscript

**Finding.** `docs/RESEARCH-SUMMARY.md` states it is not a journal manuscript; what exists is an
ordered outline under "Paper outline (if one is written)".

**To close.** Convert to a submittable draft. Title already chosen in `PROMPTS-NEXT.md` checklist
item 1: *Matched-budget benchmarking of Bayesian optimization and response-surface methodology
depends on the terminal decision rule.* Largest single item here; needs no new data.

### G19. qLogNEI is stored but not promoted

**Finding.** The numbers exist (primary cell 0.1532 vs qLogEI 0.1553) but qLogNEI is not co-primary
in the prose. `PROMPTS-NEXT.md` checklist item 8 says having the numbers is "supporting, not a
substitute."

**Why it matters.** Until the write-up treats qLogNEI as co-primary, the DoE win is dismissible as
"you used the wrong acquisition function."

**To close.** Promote in the text and tables. Confirm the four qualitative conclusions survive both
acquisitions: measured-argmax DoE lead at sigma = 0.25; the unconstrained-quadratic failure; the
in-region result; the winner reversal.

---

### G20. The "BO searches the whole box" objection is now measured

**Finding (closed 2026-08-20).** Q62 ran TuRBO-1 qLogNEI at the primary cell.
TuRBO 0.1538 vs unconstrained qLogNEI 0.1532; DoE − TuRBO −0.0580
[−0.0768, −0.0390]. N=200 arrival vs `doe_ascent` is 11/25 vs 8/25 at σ=0.25,
τ=0.10.

**Evidence.** `results/q62-turbo.json`, `results/q62-turbo-n200.json`,
`docs/figures/fig4-turbo.pdf`. JSON must stay un-ignored (see `.gitignore`).

**Remaining risk.** Uncommitted until G17. Do not quote a smoke row.

---

## Execution order

Dependencies are real; this order respects them.

1. **G17** — commit everything. Five minutes, removes all risk of loss.
2. **G1** — in-region containment check. Fast, and its result decides what G2 is pointed at.
3. **G7** — both replay gates. Unblocks G3 and G8, and must be fixed before the G14 archive.
4. **G2** — extend the ensemble to 100 and rerun both confirmatory contrasts overnight.
5. **G11, G12, G13** — read the four PDFs while the run is going. No dependency.
6. **G3, G6, G8, G9** — the runs that G7 and G2 unblock.
7. **G15, G16** — terminology pass. Do it once the numbers stop moving.
8. **G10** — real saddle contour.
9. **G4, G5** — calibration and the strong-interaction oracle.
10. **G19, G18** — promote qLogNEI, then write the manuscript.
11. **G14** — archive and mint the DOI last, from a tree that passes its own gates.

Items 4 and 5 run in parallel. Items 2 and 3 are independent of each other.

---

## Verified vs asserted in this document

**Verified during the audit:** the failing test and its delta; the contents and key absence in
q34/q35; the `paper_figures.py` docstring; the terminology counts; the "estimand" counts; the
citation absences in `source_verification.md`; git and working-tree state; the test-suite result.

**Taken from the repo's own records, not re-verified:** the 1e-12 BO replay failure; the 76.4%
coverage figure; the ~0.93 additive share; all table values quoted above.

**Inferred, and flagged as such where it matters:** that G1's containment assumption may not hold —
this is stated as unverified in the stored data, which is the finding. It is *not* a claim that the
assumption is false.
