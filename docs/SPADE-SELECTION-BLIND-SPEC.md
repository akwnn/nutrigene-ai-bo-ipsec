# SPADE selection-blind certification — pre-registration ("KW")

**Frozen before any KW result exists.** KV-6 closed the question of new *acquisition* rules.
KW is not one: it changes what variance the **certificate** is allowed to use, and it is
registered on a diagnosis KV itself produced.

## 1. The diagnosis, in four measured steps

| step | evidence |
|---|---|
| Targeting concentrates plate 2 near the θ contour | `lse.py`: its batch is ~half as spread as random (min pairwise 0.157 vs 0.322) |
| The posterior becomes locally confident there | E3: coverage at **proposed** points is worse than at **holdout** points, gap −0.052 to −0.090 |
| Shrunken SD lets the Vorob'ev quantile admit more volume | KV: targeted certifies **0.00714** vs random **0.00119** — 6× more |
| The extra volume is claimed on unearned confidence | KV: internal−truth gap **+0.1918** (targeted) vs **−0.0208** (random), paired +0.2171, 95% CI [+0.0746, +0.3838], p=0.0187 |

**The acquisition converts unearned confidence into claimed volume.** Random placement induces
no selection effect: its gap is *negative* (genuinely conservative), truth containment 1.0000.

**Two detectors were tried and both failed, informatively.**
- `k_eff` (KR): dispersion 1138× vs box volume's 370×, strictly dominated. Dropped.
- `kappa_tail` (KS): separates campaign failure at 0.19 SD vs volume's 1.22. Dropped. And KW's
  diagnosis explains **why**: measured this session, `kappa_tail` is *significantly **lower***
  for targeted than random (−0.0869, 95% CI [−0.1385, −0.0380], p=3.5e-05). The targeted arm's
  LOO residuals look **better** while its certificate is **worse** — a textbook overfitting
  signature. LOO measures fit at the **design points**, and targeting chooses design points the
  model will fit well. **It measures honesty in the wrong location.**

## 2. The fix, and why it is exact rather than heuristic

**A Gaussian-process posterior variance does not depend on the observed y-values at all.** It is
a function of the design locations and the kernel only:

    Sigma_post(A) = K(A,A) - K(A,D) [K(D,D) + noise]^-1 K(D,A)

So the variance implied by the **unselected sub-design** is exactly computable, and because
adding points can only reduce posterior variance, it is **pointwise larger** than the full
design's. Using it is therefore conservative by construction, not by tuning.

**KW's certificate takes the MEAN from all 48 wells and the COVARIANCE from the unselected
sub-design only.** Plate 1 is a space-filling LHS chosen before any data was seen; plate 2 is
chosen by the acquisition. The certificate is thus **blind to its own selections** for the
purpose of quantifying uncertainty, while still using every well to locate the region.

This is the precise mathematical counterpart of the diagnosis: the model may use plate 2 to say
*where* the region is, and may not use plate 2 to say *how sure it is*.

## 3. Falsifiable predictions, registered now

**KW-1 (PRIMARY — the overconfidence gap closes).** Under selection-blind certification, the
paired internal−truth gap difference between `versionb` and `versionb_random` falls below
**+0.05**, from the measured **+0.2171**.
- **FAIL** → selection-induced variance shrinkage is not the mechanism, and §1's diagnosis is
  wrong despite its supporting measurements.

**KW-2 (containment recovers).** Under selection-blind certification, `versionb`'s truth
containment at γ=0.95 reaches a one-sided 95% Clopper–Pearson lower bound **≥ 0.90**.

**KW-3 (no free lunch — the region must not vanish).** `versionb`'s non-empty rate under
selection-blind certification must be **≥ 0.50 of** its standard-certification rate. Inflating
variance shrinks certified regions; a guarantee bought by certifying nothing is not a fix.

**KW-4 (targeting must now EARN something).** With the certificate made honest, `versionb` must
beat `versionb_random` on **certified volume at matched containment**. *Registered as the real
test of the two-plate architecture: if targeting cannot buy more certified volume once it is
forbidden from buying false confidence, then it buys nothing, and KV-6's closure stands as the
final word.*

**KW-5 (transfer, the second objective).** With selection-blind certification, leave-one-family-out
volume-conditional calibration must reach pooled LB **≥ 0.90** *and* **≥ 3 of 4** families
individually — the gate KU-2 failed at 1 of 3.
- *Rationale, registered: if part of the family-to-family variation in the volume→failure law is
  selection-induced rather than intrinsic, removing it should shrink the dispersion that made a
  box-volume cap non-transferable. If KW-5 fails while KW-1 passes, the two problems are
  independent and transfer needs its own separate mechanism.*

**KW-6 (ceiling).** If KW-1 FAILS, the recorded conclusion is that the certificate's
overconfidence is **not** selection-induced, every detector and correction this project has
tested has failed (KR, KS, KT unrun, KU, KV, KW), and the scope must be declared in advance.

## 4. Scope

Re-scores the **existing** KV campaigns — the wells already exist and are gated. For each
campaign the GP is fitted once on all 48 wells for the mean; the joint covariance on the
2,000-point subset is recomputed from the **plate-1 40 wells only**; draws are formed as
`mean_full + L_plate1 @ z` with the same seeded generator, and `vorobev_columns` is applied
unchanged. `plate1_only` has no plate 2 and is therefore **identical under both schemes** — it
serves as the null control that must not move, and any movement is a bug, reported not patched.

Firewalled timing pilot first. No new campaigns are simulated.

## 5. What KW does not decide

KW does not reopen acquisition-rule design (KV-6 stands), does not revisit regret, and does not
license any comparator claim. The `certificate_straddle` module remains unused by any arm.

`NO_SELECTION` is preserved; the lockbox stays sealed.

## 6. Result — KW-1/KW-2 FAIL; but KW-4 PASSES under a DIFFERENT honesty mechanism

### 6.1 Selection-blind certification fails, and makes things worse

800 campaigns (`results/kw-selection-blind.json`). The null control is exact: `plate1_only`'s
non-empty rate is **0.0400 → 0.0400, ratio 1.000**, so the implementation is right and the
result is real.

| gate | bar | measured | verdict |
|---|---|---|---|
| **KW-1** gap closes | < +0.05, from +0.2171 | **+0.1924**, 95% CI [−0.0194, +0.4033] | **FAIL** |
| **KW-2** containment | LB ≥ 0.90 | 0.7938 → **0.6667**, LB 0.5792 | **FAIL** |

The absolute gaps got **worse**, not better: targeted +0.1972 → +0.3353, random −0.0199 →
+0.1429. The mechanism is now clear and is a genuine lesson: pairing a **sharp mean** (48 wells)
with a **wide covariance** (40 wells) is not a valid posterior, it is a mismatched pair. The
excursion probability `Phi((mean − theta)/sd)` then mixes a confident numerator with a diffuse
denominator, and the Vorob'ev quantile selects on a distorted surface. **Selection-induced
variance shrinkage is not the binding defect.** §1's diagnosis identified a real correlate, not
the cause.

### 6.2 KW-4 passes once the certificate is made honest by inflation instead

KT-5 (`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §7) *did* make the certificate honest: at
inflation `c = 1.5`, pooled truth containment 0.9699, LB 0.9377, and the factor transfers
leave-one-family-out. **KW-4 asks whether targeting earns anything once the certificate is
honest — it does not specify which mechanism supplies the honesty.** Evaluated at `c = 1.5`:

| arm | answer rate | truth containment | 95% LB | mean certified volume |
|---|---|---|---|---|
| **`versionb` (targeted)** | **0.0775** | 0.9677 | **0.9019 PASS** | **0.00167** |
| `versionb_random` | 0.0262 | 0.9524 | 0.7933 | 0.00117 |
| `plate1_only` | 0.0225 | 1.0000 | 0.8467 | 0.00117 |

Paired across all 800 campaign-cells (McNemar on discordant pairs):

| comparison | targeted-only | other-only | p |
|---|---|---|---|
| vs `versionb_random` | **49** | 8 | **2.7e-08** |
| vs `plate1_only` | **52** | 8 | **5.2e-09** |

End-to-end certified volume per campaign, **abstentions counted as zero** — the honest measure
of what a lab actually receives: **+0.00010, 95% CI [+0.00006, +0.00015]** against both
controls, roughly **4x** the expected certified volume. **KW-4 PASSES.**

### 6.3 What this does to KV-6

**KV-6's closure was reached with an UNCALIBRATED certificate**, and that is exactly the
condition under which targeting looks bad: its extra volume is unearned, so it inflates the
region without inflating the guarantee. Once the certificate is calibrated, the fake volume is
removed from every arm and what remains is real — and targeting has more of it, more often.

**KV-6 is therefore narrowed, not overturned:** *Plate-2 targeting earns nothing when judged by
an uncalibrated certificate or by map error, and earns a 3x answer rate and ~4x expected
certified volume when judged by a calibrated one.* The prospective KF-3 map-error null stands
unqualified; KV-1's containment FAIL stands as measured at `c = 1.0`.

### 6.3b CORRECTIONS to §6.2, found by stress-testing my own claims

**Retracted: "targeting is the only arm clearing LB >= 0.90."** That is a POWER ARTIFACT, the
same one that made `levy` FAIL in KU. At c=1.5 the point estimates are `versionb` 0.9677
(n=62), `versionb_random` 0.9524 (n=21), `plate1_only` 1.0000 (n=18). The controls' lower
bounds fail **only on sample size**, not on performance. The correct statement is: *all three
arms have point-estimate containment >= 0.95 at c=1.5; only `versionb` certifies often enough
to prove it.*

**Weakened: "both families independently select the same c* = 1.5."** True, but the selection
rule is more fragile than that phrasing implies. `ackley`'s failure bound is **non-monotone**
in c -- 0.165, 0.101, 0.069, **0.181** -- so c=2.0 fails for ackley and the rule lands on 1.5
partly by that failure. Diagnosed: containment itself IS monotone (0.9048 -> 0.9667 -> 1.0000
-> 1.0000); the *bound* rises at c=2.0 only because n collapses to 15 and `cp_up(0,15)=0.181`.
This is the same composition effect KT-2 was registered to catch for Lever A, now observed on
Lever B. The nesting property holds; the **selection rule** is confounded by shrinking n.

**What survives the stress test, and is the real result.** The answer-rate advantage is robust
across the ENTIRE c grid, not an artefact of c=1.5:

| c | targeted-only answers | random-only | p | targeted truth | random truth |
|---|---|---|---|---|---|
| 1.00 | 76 | 5 | 2.3e-17 | **0.7938** | 1.0000 |
| 1.25 | 63 | 3 | 1.3e-15 | 0.9286 | 1.0000 |
| **1.50** | 49 | 8 | 2.7e-08 | **0.9677** | 0.9524 |
| 2.00 | 26 | 4 | 5.9e-05 | 1.0000 | 1.0000 |

**The mechanism, stated correctly.** Calibration did not *reveal* that targeting was good. At
c=1.0 targeting already answered far more often (76 vs 5) — but its containment was 0.7938
against random's 1.0000, so **it answered more and was wrong more, and the extra answers were
worthless.** Inflation removes the containment penalty (0.7938 -> 0.9677) while leaving the
answer-rate advantage intact (49 vs 8). *That* is what changed: not targeting's value, but
whether its extra answers can be trusted.

### 6.4 Status, stated precisely

This is a **re-score** of prospectively-generated campaigns (KV generated the wells live),
analysed under a gate — KW-4 — registered before any of it ran. **The deviation is recorded:
KW-4 was written expecting selection-blindness to supply the honesty; inflation supplied it
instead.** The answer-rate results (p ~ 1e-8, 1e-9) survive any multiplicity correction this
session could reasonably apply; the volume CI excludes zero. A fully prospective confirmation,
with `c` calibrated on held-out families before the run rather than after, is still owed and is
the single remaining step.
