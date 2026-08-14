# TEAM BUILD PLAN — SHARED
## Phase 1: Bayesian optimization on synthetic data

**Read this first, both of you.** It defines the gates, the interfaces, the ownership boundaries, and the rules for working in parallel without colliding.

**Companion documents:**
- `phase1_build.md` — the full technical specification. The authority on *what* to build.
- `project_plan.md` — project context, the scientific argument, Phase 2 and 3 plans.
- `source_verification.md` — which factual claims are confirmed and which need checking.
- `person_a_spec.md` / `person_b_spec.md` — individual work packages.

When this document and `phase1_build.md` disagree, **`phase1_build.md` wins** on technical content. This document governs coordination only.

---

## 1. What we're building and why the split works

Phase 1 is a control experiment. We build a Bayesian optimizer and prove it works on synthetic data where we planted the answer ourselves — before pointing it at published data in Phase 2, which is the paper.

Four claims, and each maps to an experiment:

| Experiment | Claim | Owner |
|---|---|---|
| E1 | Recovers planted optima on standard test functions | Shared (smoke test, folded into the spine) |
| E2 | More sample-efficient than non-adaptive designs and a sequential DoE pipeline | **A** |
| E3 | Uncertainty estimates are calibrated, with error bars | **A** |
| E4 | Extrapolation-driven over-prediction is detectable *selectively* | **B** |

### Why this cut

**The obvious split is wrong.** Dividing by "truth versus learner" — one person owns the oracle and the response-surface model, the other owns the GP — puts E4 across the handoff. E4 compares GP predictive standard deviation against polynomial prediction-interval width. Under that split, the paper's main result becomes the one thing neither person can debug alone.

**So B owns E4 end to end**: the response-surface model, the designs, the parametric comparator, and the discrimination test. One person owns that result completely.

**And A hits the same phenomenon from the other side.** The DoE confirmation run inside E2 *is* E4a — the published failure mode reproducing in our benchmark without being staged for it. Two independent views of the same finding.

**Which only works if they share code.** See §4.

---

## 2. The gates

Work inside a gate is parallel. Gates are ordered.

```
Gate 0  →  Gate 1  →  Gate 2  →  Gate 3
contract   pre-flight   spine      experiments
```

### Gate 0 — Interface contract, together

Agree and commit before either of you writes an implementation:

- `Oracle`, `Evaluator`, `Optimizer` abstract base classes
- `SearchSpace` schema — coded bounds, names, units, types, constraint hooks
- The parquet result-row columns
- `metrics.py` function signatures

**These are the seams.** Agreed seams are what let parallel work merge instead of collide. Everything else in this plan assumes they exist.

**No author contact.** We are not emailing the original authors. Phase 2 runs on values digitized from the published figures in coded space, which needs nothing from them. The Collagen IV Results-vs-Methods contradiction stays permanently open and blocks one sentence of the write-up — nothing in the build.

### Gate 1 — Pre-flight, split four ways

| Person A | Person B |
|---|---|
| **PF1** ⬜ **OPEN** — over-prediction versus κ ∈ {0.6, 0.7, 0.8, 0.9} across 10 instances, plus the Hessian classification distribution | **PF3** ✅ **DONE** — API signatures on the installed BoTorch |
| **PF2** ⬜ **OPEN** — inversion verification case, closed-form check on the β=0 variant, instance acceptance rate, δ_max distribution | **PF4** ✅ **DONE** — wall-clock for one 48-evaluation run at both noise levels |

Fully parallel. **Read all four results together before anyone builds.**

> **B's two are done — see `preflight-findings.md`.**
>
> - **PF3 found two silent failures**, both landing in A's lane. `observation_noise=True` substitutes `mean(train_Yvar)` at unevaluated points with no warning, which is exactly where E3's primary metric lives. And the fix has a units trap on top of it — the supplied noise tensor is in standardized units while `train_Yvar` is in raw units, wrong by 161× in the test case. Doc 1 §5 now lists **five** silent traps, not three.
> - **PF4: ~10× cheaper than estimated.** One run is 4.8–9.2 s, the full grid ~0.4 h. **The grid does not need to shrink**, and a full re-run after a bug fix costs about half an hour.
>
> **PF1 is now the entire remaining pre-flight risk**, and it cannot run yet — see the ordering note below.

### The ordering problem in this gate

**PF1 cannot run at Gate 1 as written.** It needs A's oracle (Gate 2), a CCD sub-box design (`designs.py`, Gate 3), *and* B's second-order fit plus over-prediction metric (`rsm.py`/`metrics.py`, Gate 3). The check meant to precede building requires building — and it is the check that decides whether B has a lane at all.

**Update 2026-08-07:** B has shipped `metrics.py`, `rsm.py`, and `designs.py`. **PF1 now needs only A's oracle.**

**Resolved, partly.** B has built `metrics.py`, `rsm.py`, and **`designs.py` for real, not as throwaways**, because on a 14-day horizon nothing can be written twice and A imports the over-prediction metric anyway. Face-centred CCD is the default (rotatable axials would leave the sub-box). **PF1 is now blocked only on A's oracle.**

**Still open: formal ownership of `designs.py`.** Specced as A's (§4); B wrote it. One sentence from A — keep / replace / co-own. See `OPEN-QUESTIONS.md` Q2. Composition is settled: **32 (2⁶⁻¹, resolution VI) + 12 axial + 4 centre = 48**, matching the spec's own "28 terms, 20 residual df".

**Why together:** PF1 coming back empty means E4a has no mechanism — that is B's entire lane, decided by A's check. PF3 surprises change the model configuration, which changes what E3 measures.

### Gate 2 — Spine, split by layer

| Person A — data lane | Person B — loop lane |
|---|---|
| `space.py` | `surrogate.py` |
| `oracles.py` | `campaign.py` |
| `evaluators.py` | `optimizers.py` (qLogEI + simple baselines) |
| Instance generation and caching | `runner.py` |

**One ordering constraint inside this gate.** A ships the standard test-function wrappers (Branin, Hartmann6, Ackley) **before** the biphasic oracle. B builds the entire campaign loop against those. The real oracle swaps in later.

**If it doesn't swap cleanly, the forward-compatibility contract was never real** — and this is where you want to find that out, not in Phase 2 when a lookup table has to swap in for the same interface.

### Gate 3 — Experiments

| Person A | Person B |
|---|---|
| **E2** — regret, AUC, paired tests | **E4** — scorers, discrimination test, Hessian distribution |
| **E3** — `diagnostics.py`, closed-form CRPS, instance bootstrap | `rsm.py`, `parametric.py`, `discrimination.py` |
| Sequential DoE pipeline + confirmation run | |
| `designs.py` ownership call (B already shipped working copy) | |

**E3 goes to A deliberately, not by whoever has slack.** B owns the GP; making A write its calibration diagnostics means two people understand the model that carries into Phases 2 and 3.

---

## 3. Pair on exactly three things

Everything else is ordinary software and should be written by one person. Pair only where a silent error is expensive and test coverage is thin.

**1. The interface contract (Gate 0).** Short, and it determines whether everything else merges.

**2. The depth inversion.** Implement it **twice, independently** — A from the quadratic, B from a numerical root-find on `δ(r)` directly — then agree on a set of random draws and check they match.

One verification case (`s = 3.9917`) is thin cover for math that voids every downstream number if it's wrong.

**3. The GP configuration and kernel traversal helper.** ~~Three~~ **Five** documented traps, all silent, all producing plausible-looking but wrong calibration. All five now verified on the installed version by PF3 — see Doc 1 §5:

- `use_rbf_kernel` defaults to `True` — omit the override and you get an RBF kernel with no error, and a methods section that's false
- The function returns a **bare kernel**, not wrapped in `ScaleKernel`, so `.base_kernel.lengthscale` raises — but the primary config *does* wrap it, so any hardcoded path breaks on one of the two. *(And the legacy `get_matern_kernel_with_gamma_prior` returns a `ScaleKernel`, so the two factories disagree — the helper is mandatory.)*
- `Normalize` without explicit `bounds=` learns them from training data, which breaks E4's sub-box silently
- **`observation_noise=True` substitutes `mean(train_Yvar)`** at unevaluated points. No warning. This is where E3's primary metric lives — pass an explicit tensor instead
- **The supplied noise tensor is in standardized units** while `train_Yvar` is in raw units. Off by `stdvs**2` — 161× in the PF3 case — if you pass raw

---

## 4. Shared code, and who owns it

Two pieces cross the ownership boundary. Both are deliberate.

### `metrics.py` — over-prediction metric: owned by B, called by both

E2's DoE confirmation run and E4a both measure **over-prediction at a model's constrained argmax over the extended box**. They must call the **identical function**.

If A and B each implement it, you get two numbers that disagree and no way to tell which is right. One function makes them a genuine replication.

**B writes it. A imports it. Neither reimplements it.**

### `designs.py` — originally A's; B wrote the working copy

A's sequential DoE pipeline is design-heavy. B's E4 sub-box needs a CCD scaled into a sub-region. Same machinery.

**Working code is on disk under B.** A confirms ownership (keep B's / replace / co-own). Until that call, **do not fork a second `designs.py`.** If either person needs a design variant that is missing, change the shared file.

---

## 5. Bus factor

**Long-lived modules** — `space`, `oracles`, `evaluators`, `surrogate`, `campaign`, `runner`, `metrics` — carry into Phases 2 and 3.

**Phase 1 only** — `rsm`, `designs`, `parametric`. Thrown away after the paper.

**Definition of done for a long-lived module: tests pass, AND the other person can explain it back.**

Not a review checkbox. The non-author narrates what the module does and why it's built that way. If they can't, it isn't done.

**Why this matters concretely:** if the internship doesn't extend, whoever stays has to run Phases 2 and 3 alone. Phase 2 replaces `SyntheticEvaluator` with a lookup table against the same interface. Phase 3 replaces it with a human writing a CSV. Neither works if one person doesn't understand the campaign loop or the oracle.

---

## 6. Cadence

**Daily:** short sync on blockers only. What's stuck, what's waiting on whom.

**Weekly:** merge to main, run the full test suite, and walk through any long-lived module that landed — non-author explaining it back.

**At each gate boundary:** both read the results before either proceeds.

---

## 7. Non-negotiables — both lanes

These apply to every module either of you writes.

**Shape contract.** Outcome tensors are always `(n, m)`, even when m=1. Never `(n,)`.

**Coded space.** Everything internal runs in `[0,1]^d`. Physical units are labels only.

**Determinism.** Seed Python, NumPy, and PyTorch. Log the seed on every result row. Same seed → identical trace.

**Threading.** `OMP_NUM_THREADS=1` in the environment **before importing torch**, plus `torch.set_num_threads(1)` per worker. Some builds fix the OpenMP pool at import.

**Deprecated, do not use:** `AxClient` · `FixedNoiseGP` (use `SingleTaskGP` with `train_Yvar`) · `HeteroskedasticSingleTaskGP` · `qExpectedImprovement` without the `Log` prefix.

**No Ax in Phase 1.** Raw BoTorch.

**Style.** Type hints throughout. Docstrings stating tensor shapes. No global state. Fail loudly on shape mismatches. Comment every deliberate override of a BoTorch default. **This code is read by biologists — clarity over cleverness.**

**Report API surprises immediately.** If an installed signature differs from the spec, tell the other person the same day. It probably changes their lane too.

---

## 8. The invariant neither lane may break alone

> **E4 needs the polynomial to extrapolate. E2 needs a measurable peak. Satisfying E4 by pushing the peak toward the box edge flattens it and breaks E2.**
>
> **Move the training box relative to the peak. Never move the peak relative to the box.**

If E4a's over-prediction rate comes back too low, the fix is **lower κ** — not raising `x*`.

At `x* = 0.8` the deepest achievable decline across the stated parameter ranges is 8.2%, under one sigma at the primary noise level. High peak position and measurable depth are not jointly achievable.

**A owns the oracle. B owns E4.** So if B wants more extrapolation, **B asks A** — B does not retune the oracle. This is a joint decision, made once, not a week of quiet parameter adjustment.

---

## 9. If pre-flight comes back bad

**PF1 empty at every κ** → E4a has no mechanism. Joint decision: retune together, or shrink E4 and let E2 carry the paper. Do not let B improvise a fix alone — the oracle is A's.

**PF2 acceptance rate near zero** → the weight draw is too wide relative to the acceptance floor, or `δ` isn't being sampled relative to `δ_max`. A's fix, but tell B — it changes the instance ensemble E4 runs on.

**PF3 surprises** → ✅ **happened, and they are reported.** Two silent failures, both altering what E3 measures. A must read `preflight-findings.md` before finalizing E3's metric.

**PF4 much slower than estimated** → ✅ **the opposite happened.** ~10× *faster*. Nothing needs resizing; keep both dimensions, both noise levels, 10 instances × 5 seeds.

---

## 10. Later, both of you

**Digitize the Hall/Ogle figures independently, then reconcile.**

You need a digitization error estimate in the paper regardless. Two people reading the same ~48 bar heights independently and comparing **is** that estimate.

Roughly double the effort for a number you'd otherwise have to assert. It's also the least interesting work in the project, so splitting it is a morale call as much as a technical one.
