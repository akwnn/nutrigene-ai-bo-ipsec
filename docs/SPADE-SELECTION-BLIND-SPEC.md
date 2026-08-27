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

## 6. Result

*(Empty at freeze. Filled once, immediately after, from the run.)*
