# PRE-FLIGHT FINDINGS — PF3 and PF4

**Person B's Gate 1 checks. Person A: read PF3-Q5 and the units trap below — both land in your lane, not mine.**

Reproduce with `python scripts/preflight_pf3.py` and `python scripts/preflight_pf4.py`.

Installed: **botorch 0.18.1 · gpytorch 1.15.2 · torch 2.13.0 · Python 3.11.15**, macOS/arm64, CPU.

---

## Summary

| Check | Status | Consequence |
|---|---|---|
| PF3-Q1 kernel factory | As specced | None |
| PF3-Q2 `Normalize` bounds | As specced, now **verified** | Doc 3 Part 3 → Part 1 |
| PF3-Q3 discrete candidates | As specced, now **verified** | Doc 3 Part 3 → Part 1 |
| PF3-Q4 lengthscale bound | As specced on this version | Read it off the object anyway |
| **PF3-Q5 `observation_noise=True`** | **Silently wrong** | **Changes what E3 measures** |
| **Units of supplied noise** | **Silently wrong** | **New trap, not in the spec** |
| PF4 wall-clock | ~10× cheaper than estimated | Grid need not shrink |

---

## PF3-Q5 — `observation_noise=True` substitutes a noise level nobody chose

**What happens.** With a fixed-noise likelihood (which contract requirement 5 mandates, since we always pass `Yvar`), asking for a posterior *at a point that has no supplied noise* makes BoTorch substitute the **arithmetic mean of `train_Yvar`** and apply it to every query point.

No warning. No error. The source carries a `TODO: be smarter here`:

```
botorch/models/gpytorch.py:532
    # Use the mean of the previous noise values (TODO: be smarter here).
    observation_noise = self.likelihood.noise.mean(dim=-1, keepdim=True)
```

**Confirmed it is the mean, not the median**, by planting one large outlier in `train_Yvar`: the added variance tracked the mean exactly (0.05095 vs median 0.001).

**Why A cares.** E3's primary metric is posterior-predictive coverage at points *not yet evaluated* — exactly this path. `batch_cross_validation(observation_noise=True)` inherits it too. Left alone, the headline calibration number is computed against a flat, averaged noise level rather than the plug-in variance the oracle actually implies at each point.

**Resolution.** Supply the noise yourself. `posterior()` accepts a **tensor** for `observation_noise`, and honours it per-point. Compute the plug-in variance at the query point and pass it. Say so in methods.

---

## The units trap on that fix — not in the spec, found while testing it

The tensor you pass to `observation_noise` must be in **standardized** units, while `train_Yvar` is in **raw** units. They are inconsistent, and getting it wrong fails silently.

Cause: the noise is applied to the internal standardized model *before* `Standardize` untransforms the posterior back to raw units.

Measured, on a case where the correct added variance was 0.036381:

| What you pass | Resulting added variance | Correct? |
|---|---|---|
| raw plug-in variance | 0.000226 | **No — wrong by 161×** |
| raw plug-in variance ÷ `stdvs²` | 0.036381 | Yes |

The factor is exactly `outcome_transform.stdvs ** 2`, and it depends on the training data, so it differs per fit and per fold.

**This is the same family as the two `Yvar` traps already in the spec** (variance-vs-sd, raw-vs-transformed units), which both produce plausible-looking but systematically wrong calibration. It needs a test asserting the round-trip, alongside the existing "`Standardize` inverse-transforms variance" row in §9.

---

## PF3-Q1, Q2, Q4 — kernel and transform

- `get_covar_module_with_dim_scaled_prior(ard_num_dims, batch_shape=None, use_rbf_kernel=True, active_dims=None)`. **`use_rbf_kernel` defaults to `True`** — omit the override and you silently get RBF and a false methods section.
- Returns a **bare** `MaternKernel` (nu = 2.5) or `RBFKernel`, no `ScaleKernel`.
- **Asymmetry worth knowing:** the legacy `get_matern_kernel_with_gamma_prior` *does* return a `ScaleKernel`. Two factories, two different return shapes. This is exactly why the traversal helper is not optional — a hardcoded `.base_kernel` path breaks on one of them and a hardcoded direct path breaks on the other.
- Lengthscale constraint: `GreaterThan(0.025)` on this version, prior `LogNormalPrior(loc=2.3101, scale=1.7321)`. Read the bound off the constraint object; it is version-dependent.
- `Normalize` without `bounds=` **does** learn from training-data min/max — verified, previously only believed. On a `[0, 0.32]⁶` sub-box, a query at 0.85 mapped to **2.72–3.01**, far outside the unit cube. Load-bearing for E4: always pass explicit bounds.

## PF3-Q3 — discrete candidate mode exists

```
optimize_acqf_discrete(acq_function, q, choices, max_batch_size=2048, unique=True,
                       return_acq_values=True, X_avoid=None, inequality_constraints=None)
optimize_acqf_discrete_local_search(...)
```

Note `inequality_constraints` is accepted — relevant to contract requirement 8.

---

## PF4 — wall-clock

**Stand-in objective.** The biphasic oracle is A's module and does not exist yet, so this used Hartmann6 at d=6 and a synthetic bump function at d=8, with the exact model config, budget convention, and plug-in `Yvar` policy from the spec. Cost is dominated by `optimize_acqf` (92–96%), not by evaluating the objective, so the numbers should hold when the real oracle lands. **Re-run then to confirm.**

| | Spec estimate | Measured |
|---|---|---|
| One 48-evaluation run | ~60 s | **4.8 – 9.2 s** |
| Full grid, single-threaded | 3–5 h | **~0.4 h** |

GP fitting is 4–8% of the time; everything else is multi-start L-BFGS inside the acquisition optimizer.

**Consequence: the grid does not need to shrink.** Keep d ∈ {6, 8}, both noise levels, 10 instances × 5 seeds. More usefully on a short timeline, a full re-run after a bug fix costs about half an hour, so mistakes are cheap.

Caveat: single runs, and they jitter (the same d at two noise levels differed 9.2 s vs 4.8 s — that is L-BFGS convergence variance, not a noise effect). Treat as "seconds not minutes", not as precise.

---

## What this changes in the other documents

- `source_verification.md`: Q2 (`Normalize` bounds) and Q3 (`optimize_acqf_discrete`) move **Part 3 → Part 1**.
- `project_plan.md` §4.1 / Doc 1 §3: replace the timing estimates with the PF4 numbers.
- Doc 1 §9 test table: add a row asserting the supplied-noise units round-trip.
- Doc 1 §5 "three traps that fail silently": there are now **five**.
