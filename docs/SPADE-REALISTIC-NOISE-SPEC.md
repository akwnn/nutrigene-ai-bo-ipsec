# KZ — does SPADE survive REAL cell-manufacturing noise? Pre-registration

**Frozen before any KZ result exists.**

## 1. Why this is the load-bearing test for the cell-manufacturing claim

Every result showing plate-2 targeting earns its place -- `SPADE-SELECTION-BLIND-SPEC.md`
§6.2, 49 vs 8 discordant, p = 2.7e-08 -- was measured at `sigma_rel = 0.25`.

Measured noise in real cell-manufacturing data:

| dataset | noise | SNR |
|---|---|---|
| simulated benchmarks | `sigma_rel = 0.25` | high |
| in-house iPSC-EC assay | CV 31% | 0.34 |
| **Hall & Ogle 2025 (published)** | **median CV 68%** | **0.10** |

**`sigma_rel = 0.25` is not the regime this method is being proposed for.** Targeting works
by placing wells near the threshold contour; if noise swamps the contour, there is nothing
to target and the entire two-plate architecture is unjustified for this application.

## 2. KZ-1 (PRIMARY, registered now)

At `sigma_rel = 0.68` -- Hall & Ogle's median CV -- `versionb` (targeted plate 2) beats
`versionb_random` on **non-empty certificate count**, paired by `(family, seed, p)`,
McNemar **p < 0.05**.

- **FAIL** -> plate-2 targeting does **not** survive realistic cell-manufacturing noise.
  The two-plate architecture would then be justified only in a noise regime real assays do
  not occupy, and every targeting claim in this repo must be restated as conditional on
  `sigma_rel <= 0.25`. **I consider FAIL at least as likely as PASS and am registering it
  first**, because the Hall & Ogle result showed the fitted posterior goes flat at SNR 0.10
  -- and a flat posterior has no contour to target.

## 3. KZ-2 (containment must not degrade)

At `sigma_rel = 0.68`, truth containment for `versionb` must not fall below its
`sigma_rel = 0.25` value by more than 0.10 at matched `c`. A targeting rule that keeps
answering while becoming wrong is worse than one that abstains.

## 4. KZ-3 (the honest control)

`sigma_rel = 0.25` is re-run in the same process as the internal control. If the 0.25 arm
does not reproduce the direction of §6.2's targeting advantage, the harness is wrong and
**no KZ verdict may be read at all**.

## 5. Scope

`SIGMA` is rebound on `run_p8_certificate_families.py`, the same technique
`run_ku_prevalence_matched.py` used for `TQ.FAMILIES`. Certification path otherwise
byte-identical. 4 families x 12 seeds x 2 arms x 2 sigma. Exploratory scale: a PASS
licenses a registered confirmatory run, not a claim.

**What KZ cannot establish.** It is still simulation. It tests whether the *mechanism*
survives realistic noise, not whether SPADE works in a wet lab.
