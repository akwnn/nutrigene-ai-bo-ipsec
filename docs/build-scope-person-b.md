# BUILD SCOPE — PERSON B

> **Status note (2026-08-07):** This was written on day 1 as a build order. **All eight in-scope modules below are now built** (218 tests). Keep this file as the rationale and exclusions list; for live status use `person_b_spec.md`, `OPEN-QUESTIONS.md`, and `what-each-file-does.md`.

**Written 2026-08-07, day 1 of 14.** What gets built now, in what order, and what is deliberately excluded.

Person A: this is also a declaration of the interfaces I am assuming. **Objecting now is cheap; objecting on day 6 is not.** Anything marked ⚠️ is a guess I have made in order to keep moving, and I will change it on request.

---

## The principle

Everything here is needed **under every outcome**, including the one where PF1 comes back empty and E4 shrinks. Nothing in this scope is a bet on E4 working.

Two things gated the rest and neither was mine: **A's oracle** and **the CCD sub-box design**. The CCD is now built (ownership confirmation still open). **Until the oracle lands I build machinery, not results** — and the machinery listed below is done.

---

## In scope now

Ordered. Each item is independently useful; if we stop after any of them, what exists still works.

### 1. `surrogate.py` — the GP builder

The model everything else uses. Nothing blocks it: PF3 already answered every question it depends on.

- `build_gp(train_X, train_Y, train_Yvar, bounds, *, use_scale_kernel=True)` — Matérn 5/2 via `get_covar_module_with_dim_scaled_prior(..., use_rbf_kernel=False)`, `ScaleKernel`-wrapped as the primary config, `Normalize` with **explicit** bounds, `Standardize`.
- `base_kernel(model)` / `lengthscales(model)` — the defensive traversal helper. Used **everywhere including tests**, never a hardcoded `.base_kernel` path. Trap 2 makes this mandatory, not stylistic.
- `predictive(model, X, *, noise)` — the wrapper that resolves traps 4 and 5 in one place. Takes plug-in variance in **raw** units, divides by `outcome_transform.stdvs**2` internally, and passes a tensor. **Nothing anywhere else in the codebase calls `observation_noise=True`.**

**Done when:** kernel identity, lengthscale-bound-read-off-the-object, explicit-bounds, and the noise-units round-trip all have tests. Every one of the five silent traps has a test that fails if the trap is reintroduced.

**Interface I am assuming ⚠️:** `bounds` is a `(2, d)` float64 tensor. I do **not** require A's `SearchSpace` object — `space.bounds` can be passed in. This keeps `surrogate.py` testable before `space.py` exists.

### 2. `optimizers.py` — proposals

- **qLogEI, continuous.** `optimize_acqf(num_restarts=10, raw_samples=512)`, joint q-acquisition, never top-q of a single-point surface.
- **qLogEI, discrete.** `optimize_acqf_discrete(acq_function, q, choices, ...)` — signature confirmed by PF3. **Not optional.** Phase 2's replay can only propose conditions that exist in the published data, and retrofitting this later is a change to the optimizer's core.
- **Baselines:** random, Sobol, LHS. Sobol initial design of `2d+2`.
- Constraint hooks (`inequality_constraints`, `equality_constraints`, `nonlinear_inequality_constraints`, `fixed_features_list`) threaded through from config to both paths — `optimize_acqf_discrete` accepts `inequality_constraints`, confirmed by PF3.

**Done when:** every discrete proposal provably comes from the candidate set; q=4 proposals are not all within ε of each other; qLogEI finds the peak on a 1-D toy.

**Out of scope here:** A's sequential DoE pipeline. That is A's arm of E2.

### 3. `campaign.py` — the ask/tell loop

The module the whole project rests on, and the one A must be able to explain back.

- `ask(q)` / `tell(X, Y, Yvar)`. The optimizer never calls the oracle.
- `X_pending` tracking for in-flight proposals.
- **Serialize data + config + Python/NumPy/torch RNG state. Refit on resume. Never model weights** — brittle across BoTorch versions, and the identical-trace test only passes if the torch RNG state is in the dump.
- **Log predictive distributions at proposed points *before* evaluation**, at both the BO-proposed points and a fixed held-out Sobol set. A's E3 prospective calibration depends on this existing, and the gap between the two sets is itself a reported result.

**Done when:** same seed reproduces an identical trace through a save/reload cycle, and A can narrate what the module does and why.

**Interface I am assuming ⚠️:** `Evaluator.evaluate(X) -> tuple[Tensor, Tensor | None]`, shapes `(n, m)` and `(n, m)`, exactly as Doc 1 §2 states. I will build against A's standard test-function wrappers first and swap the biphasic oracle in later — **that swap is a deliberate contract test.** If it isn't clean, the forward-compatibility design was never real, and we want that failure now rather than in Phase 2.

### 4. `parametric.py` — the practitioner-form comparator

Additive biphasic, **no interaction terms**, by nonlinear least squares. What someone would try without knowing the truth.

An oracle-form fit is matched by construction, wins trivially, and tells us nothing — so it is not built. **Log NLS convergence failures rather than silently dropping instances**; the failure rate is a reported number.

### 5. `rsm.py` — the stepwise third-order model

Descriptive only. **No prediction interval, ever** — stepwise selects terms from the same data the interval is computed from, making it anticonservative, which is fatal when "the polynomial's interval is too narrow" is the finding.

Reports: over-prediction, stationary-point classification, surviving term count. Matches the published study's practice ("only significant terms up to the 3rd order").

**Open ⚠️:** stepwise selection criterion is listed in Doc 1's "ask rather than assume". I will use backward elimination on p-values unless told otherwise, and record the choice in config.

### 6. E4's comparison machinery

Pure numerics. Takes arrays, returns numbers — needs no oracle, so it can be finished and tested before A's module lands.

- Three scorers: GP predictive sd, second-order PI width, **nearest-neighbour distance to the training set**.
- The scorer–scorer rank-correlation matrix. **Computed and reported first**, before any result. If all three correlate above 0.95 there is no headroom and the comparison cannot show anything either way — that is the finding, not something to bury.
- Spearman ρ against |polynomial error| (**primary**), AUC at the pre-registered τ (**secondary**), instance-level bootstrap CIs.

Constants already locked in `configs/experiment/e4.yaml`: 512 candidate points, τ = within-instance 0.80 quantile.

### 7. `designs.py` — the CCD ✅ BUILT · ⚠️ OWNERSHIP CONFIRMATION STILL OPEN

**Specced as A's. B wrote it** (face-centred fractional CCD, screening designs, sub-box scaling, 28 tests) because it is half of what A's PF1 was missing and PF1 is the whole remaining risk.

At d=6 with `n_subbox = 48` a full 2⁶ factorial core is 64 runs before axials, so the design must be fractional:

> **32 (2⁶⁻¹, resolution VI) + 12 axial + 4 centre = 48**

which reproduces the spec's own "28 terms, 20 residual df". Resolution VI is more than sufficient for a second-order model.

**Open ⚠️:** ownership confirmation from A (keep / replace / co-own). Face-centred versus rotatable is **settled: face-centred** — the sub-box is a hard boundary and a rotatable design's axial points would fall outside it.

**A: say the word and I stop.** Duplicated effort here is worse than a day's delay.

### 8. `runner.py` — the grid runner

Last, because everything else feeds it. Parquet output with JSON sidecars carrying resolved config and library versions. **Skip-if-exists** — not for crash recovery but because runs get interrupted during development and re-doing hours is intolerable on this timeline. Optional multiprocessing with `torch.set_num_threads(1)` per worker and `OMP_NUM_THREADS=1` set before torch imports.

---

## Explicitly out of scope

| Item | Why |
|---|---|
| **Running E4** | Needs A's oracle and the CCD. Machinery yes, results no. |
| `space.py`, `oracles.py`, `evaluators.py`, `diagnostics.py` | A's. |
| A's sequential DoE pipeline, E2, E3 | A's. |
| Anything Phase 2 or Phase 3 | Out of the 14 days, except that the interfaces must not preclude them. |
| Ax, Docker, Hydra, GPU | Excluded by spec. |
| Multi-objective (qLogNEHVI) | The published readout is single-objective. Deferred to Phase 3. |
| Batch-effect modelling, bounded-proportion response | Deferred to Phase 3 by spec §E.6. |

---

## Sequence and rough cost

| | Work | Cost | Blocked by |
|---|---|---|---|
| Now | 1 `surrogate` + 2 `optimizers` | ~1 day | nothing |
| Now | 7 `designs` (if mine) | ~half day | ownership call |
| Next | 3 `campaign` | ~1 day | A's test-function wrappers |
| Next | 4 `parametric` + 5 stepwise | ~half day | nothing |
| Next | 6 E4 machinery | ~half day | nothing |
| Then | 8 `runner` | ~half day | 1–3 |
| **Gated** | **E4 results** | ~1 day | **A's oracle + CCD** |

About 4 days of machinery, then roughly a day of experiment once A unblocks it. That fits the 14 days with room — **provided A's oracle lands by about day 4.** It is the critical path for both lanes.

---

## What I need from A

1. **The oracle.** Everything downstream of it is stalled — A's PF1, A's E2, A's E3, my E4.
2. **The `designs.py` ownership call.** One sentence.
3. **Standard test-function wrappers before the biphasic oracle**, per the plan. I build the loop against them.
4. **Read `preflight-findings.md`** before finalizing E3's metric. Two silent failures land in A's lane, not mine.
5. **Object to any ⚠️ above.** Cheap now.

## Standing constraints on everything here

Outcome tensors always `(n, m)`, even at m=1 · everything internal in coded `[0,1]^d` · seed Python, NumPy and torch, log the seed on every row, same seed → identical trace · `OMP_NUM_THREADS=1` before importing torch **and** `torch.set_num_threads(1)` per worker · no `AxClient`, no `FixedNoiseGP`, no `HeteroskedasticSingleTaskGP`, no un-`Log`-prefixed `qExpectedImprovement` · type hints throughout, docstrings stating tensor shapes, fail loudly on shape mismatches, comment every deliberate override of a BoTorch default.

**This code is read by biologists. Clarity over cleverness.**
