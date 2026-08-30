# DC — can classical DoE certify a design space at all? Pre-registration.

**Frozen before any DC data exists.**

Runner: `scripts/run_dc_doe_certificate.py` · Analyser: `scripts/analyse_dc_doe_certificate.py`
Data: `results/dc-{family}.json`

## 1. The gap this closes

The paper's claim against BO is **"same optimisation quality in half the rounds, plus a
certificate."** The claim against classical DoE **cannot** be about rounds — DoE spends 3
rounds, SPADE spends 5. **SPADE uses MORE rounds than DoE.** The only justification for that
extra cost is that DoE cannot return a certified region at all.

**That has never been measured.** Every result file was checked: no `doe` arm has ever
carried a `ce_*` column. The certificate has only ever been computed for SPADE variants,
qLogNEI, and `lhs` (one-shot space-filling, which answers 11/320 = 3.4% and does not clear
the 5% floor). **"DoE cannot certify" is currently asserted, not measured**, and it is the
first thing a cell-manufacturing reviewer will ask ("why not just run a CCD?").

## 2. Design

5 families x 32 seeds x 48 wells, `sigma_rel = 0.25`, `alpha = 0.95`, `c` in
{1.0, 1.5, 2.0, 3.0}, `p` in {0.70, 0.30}. **One process**, so no cross-experiment pairing.

| arm | rounds | what it is |
|---|---|---|
| `doe` | 3 | screened classical DoE, 6->4 factors, CCD + confirmation |
| `doe_unscreened` | 3 | the same without the screen — isolates the screening decision |
| `spade` | 5 | committed multi-round SPADE |
| `qlognei` | 10 | BO at its own best round count |

**The certification path is byte-identical across arms:** each arm's 48 `(X, Y)` wells are
fitted with the same `build_gp`, and the same `vorobev_columns` is computed from the joint
posterior. No arm gets a different estimator. Regret is scored identically for all four via
`scored_curve`, so no arm is scored under its own favourable rule.

**Reproduction gate:** `spade` and `qlognei` must reproduce LC's regret exactly, or nothing
here is readable.

## 3. DC-1 (PRIMARY) — does SPADE certify where DoE cannot?

`spade` reaches **LB >= 0.90 at answer rate >= 0.05**; `doe` does not.

- **PASS** -> the extra rounds are justified: they buy a guarantee DoE cannot supply, and
  the paper may say so from measurement rather than assertion.
- **FAIL, `doe` also certifies** -> **the design-space argument against DoE collapses.**
  SPADE would then cost more rounds than DoE for a deliverable DoE also provides, and the
  paper must say that. **This is a real possible outcome and is registered first.**

## 4. DC-2 (ADVERSARIAL) — does DoE beat SPADE on regret?

The companion study found classical DoE beats BO on regret at this noise level
(-0.0595, d=6, sigma=0.25, measured-value argmax). **DoE may therefore beat SPADE on
regret here.** Reported per family and pooled, paired by `(family, seed)`.

- If DoE wins regret, **that is reported as the headline of this section**, not buried. The
  paper's position becomes "DoE finds a good recipe; only SPADE certifies a region" — which
  is a narrower claim than the current draft implies, and it must be written that way.

## 5. DC-3 — does the 6->4 screen destroy certifiability?

`doe` versus `doe_unscreened` on answer rate and containment. A screened design never varies
two of six factors, so a certificate over the full box may be undefined in those dimensions.

- Mechanistic, and it decides whether "DoE cannot certify" is a property of **DoE** or a
  property of **screening**. If `doe_unscreened` certifies and `doe` does not, the honest
  claim is about the screen, not the method.

## 6. Honesty constraints

- No "X cannot certify" without reporting `answered` and `contained`
  (`SPADE-TAU-DEGENERACY-SPEC.md` §7.3). A Clopper-Pearson bound at 0.90 needs **>= 29
  answered cells** even at perfect containment.
- Rounds are stated per arm in every table. **SPADE uses more rounds than DoE** and no table
  may omit that.
- `sigma_rel = 0.25`. The real-noise ceiling (0.68, nothing certifies) is untouched.
- At n <= 25 seeds an effect here is not reliable; 32 seeds minimum.

---

## 7. AMENDMENT, before the run — the BO arm has drifted

The §2 reproduction gate was written expecting `spade` **and** `qlognei` to reproduce LC.
Measured before launching:

| arm | R | family | seed | committed (LC) | current code | |
|---|---|---|---|---|---|---|
| spade | 5 | hartmann6 | 0 | 0.371536 | 0.371536 | exact |
| spade | 5 | hartmann6 | 1 | 0.075667 | 0.075667 | exact |
| spade | 5 | ackley | 0 | 0.678465 | 0.678465 | exact |
| spade | 5 | ackley | 1 | 0.755496 | 0.755496 | exact |
| **qlognei** | 10 | hartmann6 | 0 | 0.169970 | **0.091732** | **drifted** |
| **qlognei** | 10 | hartmann6 | 1 | 0.244261 | **0.290664** | **drifted** |
| **qlognei** | 10 | ackley | 0 | 0.799783 | **0.759596** | **drifted** |
| **qlognei** | 10 | ackley | 1 | 0.705043 | **0.681228** | **drifted** |

**SPADE reproduces exactly; the BO arm does not.** Mean change **−0.023959** — BO is
**stronger** under current code. Verified deterministic: the same call twice gives the same
answer, and pinning the global torch seed changes nothing, so this is a **code change**, not
RNG order. The only source change since LC is the merge of `origin/main` (136 commits).

**Consequences, recorded before any DC number exists:**

1. **The reproduction gate is amended:** `spade` must still reproduce LC exactly. `qlognei`
   **cannot** and is no longer gated on it. This is a measurement fact, not a relaxed
   standard — and it is recorded here rather than quietly dropped.
2. **`SPADE-LC-CONFIRMATORY-SPEC.md` §9.1's parity claim is now PROVISIONAL.** It compared
   SPADE R=5 against the *old* BO. A ~0.024 improvement in BO would move that comparison
   (+0.0016, half-width 0.0196) **outside the registered SESOI of 0.02**. **DC re-measures
   both arms in one process under current code and supersedes it.**
3. **This is the likely root cause of the three failing `test_replay.py` tests on main**
   (`HANDOFF-2026-08-30.md` §6b) — they assert that current code reproduces committed
   q42/q59 **BO** columns, and the BO path has changed. Not bisected; stated as the leading
   hypothesis with direct supporting evidence.
