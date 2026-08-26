# SPADE Plate-2 certificate follow-up — pre-registration ("KV")

**Frozen before any KV result exists.** Registers the prospective confirmation of a **post-hoc**
finding, and one registered attempt to enlarge it.

## 1. What is being confirmed, and why it is not yet a result

KF-3, KF-3b and KF-3c killed boundary-targeted Plate-2 placement three times, on **map error**.
That negative is **well-powered, not an absence of evidence**: n=250 paired campaigns,
**MDE 0.0057** against the pre-declared SESOI of **0.02** — resolution 3.5× finer than the
smallest effect of interest — observed +0.0029, targeted nominally *worse* than random.

This session examined a **different deliverable** and found the opposite. Campaign-clustered
paired tests (mean over each campaign's `(gamma, tau_frac)` cells, then paired; per-cell pairing
would count 24 correlated rows per campaign), γ=0.95, truth containment:

| comparison | n | effect | p |
|---|---|---|---|
| targeted plate 2 vs **random** plate 2 | 149 | **+0.0239** | 0.019 |
| predictive plate 2 vs random plate 2 | 150 | **+0.0227** | 0.0088 |
| targeted 2-plate vs 1-plate | 149 | +0.0242 | 0.053 |
| **random 2-plate vs 1-plate** | 150 | **+0.0003** | **0.95** |

Bootstrap on the key contrast: **+0.0239, 95% CI [+0.0016, +0.0467]**.

**Random placement of the extra 8 wells is worth nothing. The second plate has value only when
it is targeted.**

**Three reasons this is not a result yet, all of which KV exists to remove:**
1. **The endpoint is post-hoc.** Containment was examined *after* map error failed. The *wells*
   were allocated prospectively by each arm's own rule in Version B, so this is a genuine
   allocation comparison rather than a pure re-score — but the endpoint was not pre-registered.
2. **No multiplicity control.** p=0.019 is uncorrected across the many endpoints examined.
3. **No SESOI for containment has ever been declared** (§2).

## 2. The SESOI, declared now, on the project's existing convention

**SESOI = 0.02 on the truth-containment scale.** This is not chosen to fit the observed effect;
it is this project's existing SESOI, already pre-declared for map error, transferred unchanged
to the other scale — both are fractions in [0, 1].

**Stated plainly because it matters: the post-hoc effect (+0.0239) sits only just above this
bar.** A modest regression to the mean puts the confirmation *inside* the SESOI, in which case
KV-1 is reported as **real but not material**, exactly as KF-6/KF-7 were. That risk is accepted
before the run rather than negotiated after it.

## 3. The improvement being tested, and why it is principled rather than tuned

`boec.lse.straddle_score` targets `mean = theta` — the **p = 0.5** contour. That is the correct
target for map loss, whose symmetric-difference error is *defined* at that contour, and the
measurements above are consistent with it: targeting moves map error by nothing and containment
by +0.024.

But `boec.vorobev.conservative_estimate` bounds its region by `{x : p(x) >= rho_alpha}`, and for
a **joint** claim `rho_alpha` sits well above 0.5. In response units that contour is

    p(x) = rho   <=>   mean(x) - z_rho * sd(x) = theta,     z_rho = Phi^-1(rho)

so the current rule has been aiming at p=0.5 while the certificate's frontier lives near p=0.95.
`src/boec/certstraddle.py` (`certificate_straddle`, `batch_lse_rho`), TDD, 13 tests, committed
**before this spec was frozen**, targets the frontier directly.

**`rho` is REGISTERED, not tuned: `rho = 0.95`**, matching the assurance level the certificate is
scored at. No `rho` sweep is run, and no `rho` is selected after seeing an outcome. A
campaign-adaptive `rho` (reading the level `conservative_estimate` actually selects on plate 1)
is a **follow-up**, registered separately only if fixed-`rho` clears KV-3.

**Safety of the change.** At `rho = 0.5`, `batch_lse_rho` is **bit-identical** to the committed
`batch_lse` — asserted by `test_batch_lse_rho_at_one_half_is_bit_identical_to_the_committed_
batch_lse`. Adopting this module cannot silently move any committed number.

## 4. Arms

| arm | plate 2 rule | role |
|---|---|---|
| `spade_cert_rho95` | `batch_lse_rho`, `rho=0.95` | the new arm |
| `versionb` | `batch_lse`, Bryan's straddle (= `rho=0.5`) | current targeting |
| `versionb_random` | uniform random | **the causal control** |
| `plate1_only` | none, 48 wells in one round | architecture control |

**Arm-distinctness assertion, mandatory.** The runner asserts the selected well sets differ
between `spade_cert_rho95` and `versionb` on every campaign. This project has shipped three
errata of exactly this shape (`EV(x)` reading ground truth; `exclusion_radius` hardcoded to 0.1;
`above_ceiling` copied across rows), and a fourth — two arms silently identical — is the failure
mode a `rho` parameter most invites. Identical batches on any campaign **pause KV** and are
reported.

## 5. Falsifiable predictions, registered now

**KV-1 (PRIMARY — confirmation).** Prospectively, `versionb` beats `versionb_random` on truth
containment at γ=0.95 by **≥ 0.02** (the SESOI), Holm-corrected within the KV family.
- **PASS** → the post-hoc finding survives, and the targeting mechanism has its first positive
  result in this project's history.
- **Significant but < SESOI** → reported as **real but not material**, not as a win.
- **FAIL** → the post-hoc signal does not replicate; §1's table is recorded as a re-score
  artefact and the KF-3 line stands unqualified.

**KV-2 (the improvement).** `spade_cert_rho95` beats `versionb` on truth containment by
**≥ 0.02**, Holm-corrected.
- **FAIL** → aiming at the certificate's own contour does not enlarge the effect; `rho=0.5`
  stays, and the adaptive-`rho` follow-up is **not** run.

**KV-3 (the architecture).** `versionb_random` does **not** beat `plate1_only` by ≥ 0.02.
*Registered as a prediction of NO effect, from §1's +0.0003 (p=0.95). If random plate 2 turns
out to beat one plate prospectively, the "adaptivity is the value" reading in §1 is wrong and
must be withdrawn.*

**KV-4 (no robbing Peter).** `spade_cert_rho95`'s **map error** must not exceed `versionb`'s by
more than the SESOI. A certificate bought by wrecking the map is not an improvement, and moving
the acquisition off the p=0.5 contour is exactly the change that could do it. **This gate can
fail on its own and kill KV-2 even if KV-2's own number passes.**

**KV-5 (answer rate).** `spade_cert_rho95`'s non-empty-certificate rate must be within 0.05 of
`versionb`'s. Targeting a deeper contour could shrink certified regions to nothing; a higher
containment bought by certifying less often is not a gain.

**KV-6 (ceiling).** If KV-1 FAILS, the recorded conclusion is that Plate-2 targeting has now been
tested on both deliverables — map error prospectively (KF-3/3b/3c) and certificate containment
prospectively (KV) — and earns its complexity on neither. That closes the question rather than
leaving it open, and **no further Plate-2 acquisition rule is built without a new
pre-registration.**

## 6. Statistics

Wilcoxon signed-rank on campaign-clustered paired differences (average within a campaign across
its `(gamma, tau_frac)` cells, then pair), bootstrap intervals for effect size, Holm–Bonferroni
across KV-1/KV-2/KV-3/KV-4 as one family. γ=0.95 is primary; γ ∈ {0.50, 0.80} reported beside it
and **not** eligible to be promoted.

## 7. Scope and cost

Fresh campaigns — this is prospective, not a re-score. d=6, σ=0.25, `N_DRAWS=4096`, families and
seeds matched to P8's registered grid. Firewalled timing pilot first; if the projection exceeds
8 hours, seeds are cut and the reduction recorded **before** the run, as KU §5/§5b did.

## 7a. Scope fixed before the run, from the firewalled pilot

Pilot: **8 campaigns, 12.7 s/campaign, 0 arm collisions out of 2 checked.** Twelve times faster
than KU's observed 152 s/campaign because KV's scorer computes the **certificate columns only** —
the joint draw on the 2,000-point subset — and skips the 20,000-point grid map columns
(`sup_err`, `grid_r2`, both probability maps, `inscribed_box_from_mask`, Brier/AUC/AUPRC across
24 cells) that KV does not read. That same certificate-only path had its **reproduction gate
against committed α=0.95 pass 0/72** in `run_kt_assurance_fast.py`.

**Two scope decisions, recorded here BEFORE the run:**

1. **Families: `levy`, `rosenbrock`, `ackley`, `hartmann6` — `hill` excluded.** Same technical
   reason as `SPADE-PREVALENCE-MATCHED-SPEC.md` §5a: `hill` is an ensemble reached through
   `instance_by_id` + `BiphasicOracle`, and `regenerate(family, ...)` for the `plate1_only` arm
   cannot take `"hill"` as an instance id. Adding it means forking a committed path. This also
   makes KV's family set **identical to KU's**, so the two studies are directly comparable.
   `hill` is the family whose certificate is already validated, so its exclusion removes the
   easiest case.

2. **Scoring grid: τ-as-quantile, `p ∈ (0.30, 0.10, 0.03, 0.01)`, not `tau_frac`.** Adopted per
   `SPADE-TAU-QUANTILE-SPEC.md` §6b ("it should replace the fixed-fraction grid in any future
   cross-family certificate work") and because this session established that mixing the two grids
   is exactly the confound that invalidated KR's and KS's transfer comparisons
   (`SPADE-PREVALENCE-MATCHED-SPEC.md` §1). KV must not repeat it.

**Resulting scope: 4 families × 50 seeds × 4 arms = 800 campaigns, ~2.8 h** — inside §7's
8-hour ceiling at **full** seed count, so no seed reduction is needed and none is taken.

## 8. What KV does not decide

KV does not test the certificate's family-generality — that is KU
(`SPADE-PREVALENCE-MATCHED-SPEC.md`) and KT (`SPADE-ASSURANCE-CALIBRATION-SPEC.md`). It does not
revisit regret. It does not license any claim that SPADE beats a comparator. The 24/24 budget
split predicted by the resolution argument (`SESSION-LOG-2026-08-26.md` §9.3 — 8 wells on 40
moves wells-per-correlation-cell by exactly 20% whatever the rule) is **not** tested here and
needs its own registration.

`NO_SELECTION` is preserved; the lockbox stays sealed.

## 9. Result

*(Empty at freeze. Filled once, immediately after, from the run.)*
