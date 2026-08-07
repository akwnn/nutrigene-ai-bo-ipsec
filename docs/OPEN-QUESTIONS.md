# OPEN QUESTIONS — ONE PLACE FOR EVERYTHING NEEDING A DECISION

**This is the only file that collects questions. Nothing gets asked anywhere else.**

Updated after every completed piece of work. Last updated: **2026-08-07 (evening) — Person A onboarded. Q2/Q3/Q4/Q5/Q8 answered. Two new questions (Q12, Q13) raised by A, both about E4 and both with measurements attached. Q1 is no longer a blank sheet — see the status block under it.**

- **[A]** = needs Person A
- **[YOU]** = needs Alan
- **[EITHER]** = whoever gets there first

Status: 🔴 blocking · 🟠 will block soon · 🟡 answer before writing the paper · ⚪️ noted, proceeding on a stated default

---

## 🔴 BLOCKING — work stops without these

### Q1 [A] · The made-up data generator is the critical path for both lanes

Nothing else matters as much. Waiting on it: A's own pre-flight check, A's Experiment 2, A's Experiment 3, and B's Experiment 4. **Every other item on this page is smaller than this one.**

Needed: the biphasic oracle with the depth inversion, feasibility scan, acceptance checks, instance hashing, and cached optima.

> ### ⛔️ THIS IS NOW HARD-BLOCKING. B has run out of work.
>
> **Person B's lane is code-complete.** Every module is built and tested, and Experiment 4 is wired end to end and verified against a stand-in landscape. **There is nothing left for B to build that does not require A's oracle.**
>
> **What A needs to provide.** The oracle just has to answer three questions — nothing more:
>
> ```
> x_star          -> (d,)                  where each ingredient's response peaks
> truth(X)        -> (n, 1)                the NOISELESS value. Scoring only, never fitting.
> observe(X)      -> ((n, 1), (n, 1))      a noisy measurement and its noise estimate
> ```
>
> That is the whole interface, and it is **structural** — A's class does not need to import or inherit anything from B's code. If it has those three, it drops straight in. It is written down as `boec.e4.Oracle`, and `boec.campaign.Evaluator` is the matching two-method version for the loop.
>
> **A stand-in with exactly this shape is already in `tests/test_e4.py`.** A can read it as a worked example of what is expected, and B's tests use it to prove the pipeline runs — so the moment A's real one arrives, E4 produces numbers the same hour.
>
> **The mechanism has been confirmed to fire on the stand-in**: trained on a corner, the traditional fit points outside what it has seen and overshoots, and hiding more of the space increases the overshoot. That is not proof it will happen on A's real landscapes — that is exactly what PF1 measures — but it does prove the experiment is capable of detecting the effect if it is there.

> ### ✅ A's status, 2026-08-07 evening — the oracle exists, and the mechanism fires on it
>
> **A has a working biphasic oracle already built** (numpy, 42 tests, ensembles generated at d ∈ {6, 8}, 25 instances each). It was developed against the same `phase1_build.md` but has since moved to an internal `v8`, which **deviates from §4 in three ways — see Q13, which needs B's agreement before any number is published.**
>
> **It satisfies B's interface today.** A thin torch adapter over the numpy core passes `isinstance(adapter, boec.e4.Oracle)`, and `run_e4_cell` completes on a real generated instance:
>
> ```
> d=6, kappa=0.6, one instance   n_train 48
> over_prediction   second_order 10.81 · stepwise 13.53 · gp 1.23 · parametric 1.61
> argmax escaped the sub-box     all four models
> stationary kind                second_order saddle · stepwise ridge
> PI width at argmax             second_order 6.85 · gp 1.91
> scorer agreement (max offdiag) 0.798  -> HEADROOM, under the 0.95 kill threshold
> ```
>
> **B has a lane.** The effect is not near zero — it is enormous. Which is itself the problem: see **Q12**. The full PF1 sweep over κ ∈ {0.6…0.9} × 10 instances is A's next task; these are one cell, and are reported as evidence the pipeline runs on real landscapes, not as PF1.
>
> Adapter is a spike, not committed. Porting it properly is A's day-2 work.

> ### ✅ PORTED — Q1 IS CLOSED. B can run E4 from a clean clone.
>
> One `boec` package. `space.py`, `oracles.py`, `evaluators.py` and a new
> `torch_oracle.py` merged into B's tree; A's `designs.py` deleted per Q2. The ensemble
> is **committed** at `data/oracles/biphasic-hill-v8+82f6db7c8f77/` (25 instances at each
> of d ∈ {6, 8}, 456 KB) alongside `scripts/generate_oracles.py`.
>
> **`OMP_NUM_THREADS=1 pytest -q` → 288 passed, 1 xfailed.** B's 233 are untouched; 37 of
> A's 42 migrated, 4 were dropped as exact duplicates of B's `test_designs.py` (mapping
> recorded in the file), 1 is the strict xfail under Q14, and 18 are new contract tests
> on the adapter.
>
> **Why the ensemble is committed rather than regenerated** — the acceptance loop is
> rejection sampling around scipy's L-BFGS-B, and `oracle_version` hashes the
> construction parameters, *not* the optimiser's behaviour. Two machines on different
> scipy builds could accept different instances from the same seed under the same version
> string with nothing downstream noticing. That is the silent-mixing failure the version
> field exists to prevent, displaced from the config to the platform.
>
> **PF1 · d=6, 10 instances, σ_rel = 0.10, scoring box = unit cube** (B's shared metric):
>
> | κ | over-prediction, median [IQR] | > 0 | argmax escaped | PI width |
> |---|---|---|---|---|
> | 0.6 | **11.52** [9.99, 13.66] | 100% | 100% | 13.77 |
> | 0.7 | 7.62 [5.28, 8.75] | 100% | 100% | 11.12 |
> | 0.8 | 4.96 [3.08, 5.72] | 100% | 100% | 9.01 |
> | 0.9 | 3.19 [1.72, 3.67] | 100% | 100% | 6.77 |
>
> **The mechanism is present and monotone in κ.** Nothing near zero, so E4 is not
> replanned. But read it with Q12 open: the response maximum is 1.0, so an over-prediction
> of 11.5 and an interval of 13.8 are the unit cube's geometry as much as the model's
> behaviour. **These are not the E4 result.**
>
> **Turning-point breakdown, and it contradicts what `person_a_spec.md` predicted.** The
> spec says low κ should produce *minima*, because the Hill function is convex below its
> inflection. Measured: **saddle in 39 of 40 cells**, one maximum at κ = 0.9, **zero
> minima**, and the stationary point is outside the sub-box in **100%** of cells. In six
> dimensions a mixed Hessian is far likelier than a pure minimum. The prediction was
> 1-D reasoning applied to a 6-D surface — worth correcting in the spec, and it vindicates
> B's choice of the *constrained argmax* over the stationary point as the metric, since
> "did the stationary point escape" would have been asking about a saddle.
>
> **PF2 · the four maths checks**
>
> 1. `(x* = 0.4, n = 2, δ = 0.414)` → **s = 3.9917**, r = 3.9917 ✓. Round-trip error 1.7e-16, and max 5.0e-16 over 2,000 random draws.
> 2. On a γ = 0 variant of all 50 instances, the numerical optimum equals `√(EC50·IC50)` to **1.1e-16**, with `f(x_opt) − 1` at **3.3e-16**.
> 3. **Acceptance rate — this is the number that justified the v8 weight change.** Under the specification's own procedure (independent draws, then test `min_i w_i·δ_i ≥ 0.045`): **6.395% at d=6 and 0.105% at d=8** — 952 draws per accepted instance. §4.6's claim that acceptance "should be high" is false as written. Under the shipped sampler: **100% at both**, 40/40.
> 4. `δ_max` over the nominal draw spans p0 = 0.084 to p100 = 0.922, median 0.472. Realised depth on the shipped ensemble is median **0.1147** (d=6) and **0.1177** (d=8), minimum 0.1086 / 0.1111 — so **100% of instances clear the σ_rel = 0.25 threshold of 0.1083**, which no v7 instance did. Active/inert influence ratio is **4.50× (d=6) and 9.00× (d=8)**, against 1.0× under flat weights.
>
> The §4.6 closed form over-states true depth by **6.1% (d=6) / 3.0% (d=8)** on this ensemble — smaller than the 28% measured under the product interaction, because peak modulation perturbs depth far less, but still the reason acceptance is computed numerically.

### Q13 [EITHER] · A's oracle deviates from `phase1_build.md` §4 in three structural ways. Accept, or revert to spec?

**This needs answering before A ports anything in, because the two versions are different ensembles and cannot be mixed.** Each deviation below is a fix for a defect A measured in the spec as written. None is a preference. **The spec is the technical authority, so B gets a veto** — but reverting means knowingly shipping the defect named in each item.

**1. The interaction term — `β` product replaced by peak modulation.**

Spec §4.2 is `f = Σwᵢf̃ᵢ(xᵢ) + (1/k)Σβᵢⱼf̃ᵢ(xᵢ)f̃ⱼ(xⱼ)`. Differentiate it:

```
∂f/∂xᵢ = f̃ᵢ′(xᵢ) · [ wᵢ + (1/k)Σⱼ βᵢⱼ f̃ⱼ(xⱼ) ]        <- the bracket contains no xᵢ
```

**The interaction provably cannot move the optimum.** Measured over 300 instances at d=6: in the 276 (92%) where the bracket is positive, `max |joint argmax − per-factor peak| = 0.00e+00`. Two consequences, both bad:

- §4.6's acceptance check *"non-separability: coordinate-wise optimum ≠ joint optimum"* **can never pass**. It is inverted, not merely useless — it passes only in the pathological case below, the one we want to reject.
- In the 8% with a **negative** bracket a coordinate's optimum flips to the box edge (shift up to 0.547). §4.3 seeds the optimum search from `x*`, so it converges to a local max: **24 of 300 instances get a cached optimum below the true one, worst shortfall 11.7% — and regret goes negative.**

Replacement: modulate each factor's *peak location*, `mᵢ(x) = exp((1/k)Σⱼ γᵢⱼ(f̃⁰ⱼ(xⱼ) − ½))` with effective peak `x*ᵢ·mᵢ(x)`, `γ ~ U(−1,1)`; `f̃⁰` is the unmodulated factor, which breaks the circularity. Measured: `f(x_opt) = 1.0000000` (sd 1.3e-16), positivity automatic since there is no bracket to go negative, optimum located by fixed point `x ← x*·m(x)` in ~18 iterations, and the optimum sits a median **14.8% of `x*`** from the closed form so it can no longer be written down per coordinate.

**Honest limit, so nobody expects more than it gives:** this does **not** make the landscape hard to optimise. Coordinate-descent shortfall is 0–1% of depth even at double the chosen γ. A sum of coordinate-wise-unimodal terms is intrinsically easy for coordinate search and no interaction preserving conditional unimodality changes that. **Hartmann6 carries the optimization difficulty; this oracle carries realism, calibration and extrapolation structure.** See Q3.

**2. Weight structure — equal-ish weights replaced by 4 active factors holding 90%.**

Depth is bounded: `depth = minᵢ wᵢδᵢ ≤ minᵢ wᵢ ≤ 1/d`, i.e. 0.167 at d=6 and **0.125 at d=8**. Under σ_rel = 0.25 the depth needed is `3·0.25/√48 = 0.1083` — **87% of the absolute ceiling at d=8.** Measured on the spec-shaped ensemble: median depth 0.064, max 0.077, **0 of 50 instances clear 0.1083**; at a 0.110 prefloor, d=8 acceptance is **0%**. Equal weights do not merely make σ_rel = 0.25 awkward, **they kill the d=8 arm outright.**

With `n_active = 4` holding `share = 0.90`, feasibility is **100% at both d=6 and d=8**. The depth criterion applies to active coordinates only — an inert factor can be pushed to a bound cheaply, and that is correct, not a leak.

Two things this buys beyond feasibility. It matches the published 6→4 screening structure, so **the DoE arm's stage-1 screen finally has something real to find**. And it gives ARD an active-to-inert influence ratio of **4.5× (d=6) / 5.4× (d=8) against 1.0× under the spec** — under the spec, the kernel comparison sitting on the critical path had *no signal to discriminate on*.

`n_active = 4` at **both** dimensions is deliberate: it holds the active subspace fixed so d=6 vs d=8 isolates the cost of nuisance dimensions, which is the real question. Scaling actives with `d` would confound dimension with active count.

**3. Acceptance on numerically computed depth, not the §4.6 formula.**

`minᵢ wᵢδᵢ` is derived for `β = 0` and then applied to `β ≠ 0` instances, where it **overstates true depth by a median 28.4%** (5th pct −76.3%). The floor certifies a depth the instance does not have. A accepts on `f(x_opt) − max_{∂box} f` computed numerically (2d bound-constrained solves) and stores it; the formula survives only as a cheap pre-filter to keep the sampler efficient.

Related, and worth saying plainly: **§4.6's claim that acceptance "should be high" is false as written.** Measured **6.5% at d=6 and 0.104% at d=8** — 965 draws per accepted instance. Drawing `w` first and resampling `(x*ᵢ, nᵢ)` per factor until `δ_max ≥ floor/wᵢ` takes it to **100%** at both.

**4. (Parameter, not structure) σ_rel = 0.25 primary, 0.10 optimistic — reversing §4.4.** Hall/Ogle normalise every plate to a fibronectin control precisely because interexperimental variability is large, and report no CV for CD31 anywhere. The acceptance floor stays noise-independent and frozen, so **one ensemble still serves both levels** — that property is what keeps the 0.10-vs-0.25 contrast a noise effect rather than an ensemble effect.

> #### ⚠️ The part that lands on B's side, and it is a real risk, not a courtesy note
>
> Under peak modulation, `x_star` is the **unmodulated** per-factor peak. The *effective* peak is `x*ᵢ·mᵢ(x)`, and `m` can fall below 1. B's `sub_box_bounds(x_star, kappa)` assumes `[0, κ·x*]` stops short of the peak — **that guarantee is no longer automatic.** At γ ~ U(−1,1) with `k = ⌈d/2⌉`, `m` has worst-case room to reach ≈0.37, which at κ = 0.9 would put the effective peak **inside the training box**, and E4 would be measuring nothing on that cell.
>
> `e4.py` already detects the symptom — it appends *"every model's answer fell inside the region it had seen"* — but that fires after the fact and per model, not as a guard.
>
> **A owes B a measured answer before E4 runs:** across the generated ensemble, the fraction of (instance, κ) cells where the effective peak falls inside `[0, κ·x*]`. If it is non-zero, the fix is A's, and per the shared invariant it is **lower κ or tighter γ — never a raised `x*`.** A is treating this as a blocking item on the port.
>
> #### ✅ MEASURED — not material. E4's premise holds everywhere. No change needed.
>
> `x_opt[i] ≤ κ·x*[i]` iff `m_i(x_opt) ≤ κ`, so the whole ensemble can be checked in closed form. Across **50 instances × 350 (instance, coordinate) pairs**:
>
> | | value |
> |---|---|
> | `m(x_opt)` range | **[0.849, 1.174]**, median 1.008 |
> | `m < 0.6` (tightest κ) | **0.00%** |
> | `m > 1.0` (peak pushed further out, harmless) | 53.7% |
> | whole optimum inside the box, any κ, any instance | **0 / 200 cells** |
>
> Per-coordinate containment is **0.00% at κ ∈ {0.6, 0.7, 0.8}** and 18.0% (d=6) / 10.5% (d=8) at **κ = 0.9 only**. Verified a second, independent way — maximising `f` directly inside the sub-box and comparing to the global optimum — which agrees: the gap is strictly positive everywhere, minimum **0.0021**.
>
> **A's earlier worst-case estimate of `m ≈ 0.37` was wrong** — it assumed every γ and every `f̃` at its extreme simultaneously, which the fixed point does not do. The measured floor is 0.849. Reported because the loose bound is what prompted this check, and B should not carry it around.
>
> Two things for B to keep. Near-misses cluster at **high |γ| and at κ = 0.9 only** (Spearman(max|γ|, min m) = −0.44), so if γ's range ever widens this needs re-running. And at κ = 0.9 the response headroom outside the box is tiny anyway (global − sub-box max ≈ 0.009 median, well under one σ at either noise level), so κ = 0.9 is a weak cell for reasons beyond containment.
>
> Locked as `test_the_effective_peak_never_falls_inside_the_training_box`, parametrised over both dimensions and all four κ, so a future γ change fails the suite instead of silently emptying E4.

---

## 🟠 WILL BLOCK SOON

### Q2 [A] · Who owns `designs.py`? B has written it — say keep / replace / co-own

Specced as A's. B wrote it because A's pre-flight check cannot run without it and that check decides whether B's experiment exists at all.

What's there: the 48-run pattern (32 corners + 12 axial + 4 centre), screening designs for A's Experiment 2, sub-box scaling, face-centred default, 28 tests.

**PF1 is no longer blocked on the missing CCD — only on your oracle.** This question is about ownership and duplicated effort, not about whether the file exists.

**If A has already started a competing copy, tell B now.** B's original spec said "ask, don't fork" — this is the ask, retrospectively, with working code attached.

> ### ✅ ANSWERED [A] — **Keep B's. A is deleting the competing copy, not porting it.**
>
> **Disclosure, since it was asked for directly: yes, A had started one.** A numpy `designs.py` exists in A's local tree with `two_level_factorial`, `central_composite`, `subbox_bounds`, `screening_design`, `e4_subbox_design` (32+12+4=48, same arithmetic) and `extended_box_bounds`. It is **not** coming into this repo. B's version is torch-native, already imported by `e4.py` and `campaign.py`, derives resolution from first principles rather than a lookup, and carries 28 tests. Two copies of the design is exactly the failure the "ask, don't fork" rule exists to prevent, and B's is the one the experiment already runs on.
>
> **One function A wants moved across, but only if Q12 says yes:** `extended_box_bounds(x_star, kappa, rho)`, which builds the scoring box as `[0, min(1, rho·kappa·x*)]` instead of the unit cube. That is a Q12 decision, not a Q2 one. If Q12 keeps the unit cube, nothing moves and B's file is untouched.
>
> **A's role going forward: second reader, not co-author.** B stays owner; A reviews changes. A has read the file and has no correctness objection.
>
> **One thing A checked and is reporting as a NON-finding, to stop it being rediscovered.** `e4.py` fits the polynomial in raw sub-box units (`train_X = scale_to_box(design.coded, sub)`), which pushes `cond(M'M)` from 116 (coded) to 1.43e5 (raw). A initially took this for a defect. It is not: the full second-order basis spans the same column space under an affine reparameterisation, so predictions and interval widths are mathematically identical, and in float64 they agree to **6.9e-13 and 3.6e-13** on a response of scale 1 with median PI width 2.78. **No change needed. Do not "fix" this.**

### Q3 [A] · Standard test-function wrappers — still wanted for the swap test

The plan is explicit that B builds the loop against Branin/Hartmann6/Ackley first and swaps the real oracle in later, as a **deliberate test of whether the pieces really do swap cleanly**.

**Update:** B's `campaign.py` is already built against an `Evaluator` protocol with that shape. A's wrappers (and later the oracle) should implement the same interface so the swap test is still meaningful. Without them, B's tests use stand-in callables — fine for unit tests, weaker as a contract rehearsal.

> ### ✅ ANSWERED [A] — **Yes, wanted, and they already exist.** Branin, Hartmann6 and Ackley are built behind the same ABC as the biphasic oracle in A's tree and come across with it. They will land wearing the `Evaluator` interface so the swap test is a real rehearsal rather than a stand-in callable.
>
> **A is adding one baseline B's list does not have: coordinate descent.** Reason, stated now rather than when a reviewer says it: `f = Σ wᵢ f̃ᵢ(xᵢ)` is a sum of coordinate-wise-unimodal terms, so it is intrinsically easy for coordinate search, and A measured the coordinate-descent shortfall at **0–1% of depth even at maximum interaction strength**. Reporting that arm pre-empts "your oracle is separable, so of course ARD wins" instead of inviting it. Genuine multivariate difficulty comes from **Hartmann6**, which is therefore not optional in E2 — it is the arm that carries the optimization claim, while the biphasic oracle carries biological realism, calibration and extrapolation structure. ~20 lines, A's lane, no change on B's side.

### Q4 [A] · Confirm the `Evaluator` interface matches what B coded

B implemented exactly what Doc 1 §2 states:

```
Evaluator.evaluate(X: (n, d)) -> tuple[Y: (n, m), Yvar: (n, m) | None]
```

**This is now in `campaign.py` as a Protocol, with tests.** One sentence of confirmation still matters — if A's version differs, adapters get written once rather than after E2 starts.

> ### ✅ CONFIRMED [A] — matches, and it has been executed rather than eyeballed. A's adapter passed `isinstance(_, boec.e4.Oracle)` and ran the full `run_e4_cell` on a real generated landscape (numbers under Q1). `evaluate(X) -> (Y, Yvar)` with `(n, m)` throughout is what A's `SyntheticEvaluator` already returns. **No adapters needed on either side.**
>
> One note for B, not a change request: A's numerical core is **numpy, not torch**, with a thin tensor shim at the boundary. That is safe here because `truth` is only ever called under `torch.no_grad()` at a single already-optimised point (`metrics.py:179-183`) — nothing differentiates through the oracle. **If that ever stops being true, tell A before relying on it**, because a numpy oracle cannot supply a gradient.

---

### Q12 [EITHER] · E4 scores over the unit cube. That is a 2–4× extrapolation in all six coordinates at once, and it changes what we can claim

`e4.py:155` builds the scoring box as the **unit cube**, so the constrained argmax and the 512 Sobol candidates range over all of `[0,1]⁶` while training is confined to `[0, κ·x*]` — roughly `[0, 0.24]` at κ = 0.6. **Not a bug; the code does exactly what the config says.** The question is whether it is the regime we want to publish.

**What it produces, measured** (one real v8 instance, κ = 0.6, from the Q1 spike):

| | value | against a response whose maximum is **1.0** |
|---|---|---|
| second-order over-prediction | **10.81** | promises ~11× the best achievable |
| stepwise third-order | 13.53 | |
| second-order PI width at its argmax | **6.85** | interval is ~7× the entire response range |
| GP over-prediction | 1.23 | |

Across A's earlier κ×ρ sweep the pattern is consistent: over the unit cube the polynomial's interval half-width runs **2.2–3.2 in response units**, and the sub-box occupies about **1.9e-4 of the cube** at κ = 0.6.

**Why it matters, and why it cuts two different ways:**

- **The discrimination test — the actual pre-registered primary — is fine.** It is a Spearman rank correlation between each scorer and `|polynomial error|`. Rank statistics do not care that the regime is extreme, and headroom is healthy: max off-diagonal scorer agreement **0.798**, under the 0.95 kill threshold. **Nothing here threatens Q10's pre-registration.**
- **The narrative outcome is the problem.** "The traditional model's interval is too narrow" is **not available in this regime** — the interval is seven times the response range, so it covers almost anything. And for context, the published study we are motivated by extrapolated **1.20× in a single coordinate.** A reviewer will say the comparison was staged, and on this evidence they would have a point.

**What A measured at more defensible extrapolation**, sweeping `ρ` with the box as `[0, min(1, ρ·κ·x*)]` — polynomial PI coverage of the true response:

| κ | ρ=1.2 | ρ=1.5 | ρ=2.0 | ρ=3.0 | unit cube |
|---|---|---|---|---|---|
| **0.6** | 98.3% | 89.5% | 79.8% | **60.5%** | 73.6% |
| 0.7 | 97.3% | 92.2% | 82.5% | 74.9% | 90.6% |
| 0.8 | 96.3% | 95.2% | 86.1% | 91.6% | 93.8% |
| 0.9 | 98.1% | 93.4% | 94.4% | 92.2% | 91.0% |

**The mechanism is real and it is strongest at low κ with moderate ρ** — at κ = 0.6, coverage degrades 98 → 90 → 80 → 61% as ρ rises, while over-prediction climbs 0.079 → 3.07. At **ρ = 1.2 the polynomial is well calibrated at every κ (96–98%)**, which is worth knowing on its own: the case-study regime is exactly where the second-order interval behaves well, so **TheO's failure is probably not an interval-narrowness story** — which independently supports the fibronectin design-boundary explanation being the solid one.

**A's proposal (not a decision — this touches a dated pre-registration):** keep the unit cube as a reported limiting case, and add **ρ as a declared factor with κ = 0.6, ρ = 2.0 as primary**. That is the cell where the effect is real and the geometry is arguable. Requires `extended_box_bounds` from Q2 moving into B's `designs.py`, and a **`preregistration_version` bump to 2 with the reason stated in the paper** — Q10 is explicit that the locked values do not move silently, and A is not proposing to move them silently.

**If B prefers to leave the pre-registration untouched, A will not push.** Reporting one absurd-but-honest regime with the geometry stated is defensible; what is not defensible is discovering the objection at review.

---

### Q14 [B] · `screening_design(6)` cannot build the 16-run fraction E2's budget needs

`_GENERATORS` has `(6, 1)` but no `(6, 2)`, so `screening_design(6)` falls back to a half fraction and returns **36 runs** (32 corners + 4 centre). E2's sequential-DoE arm needs the **16-run 2^(6−2) resolution-IV** fraction: stage 1 is 16 + 4 centre = 20, stage 2 is a face-centred CCD on 4 factors = 16 + 8 + 3 = 27, and 20 + 27 + 1 confirmation = **48**, identical to every other arm's budget. At 36 the arm spends 36 + 27 = 63 and is no longer comparable to anything.

`2^(6−2)_IV` is a standard minimum-aberration design — generators `E = ABC`, `F = BCD`. **A is not adding it**: `designs.py` is B's under Q2, and the module deliberately raises rather than inventing a generator, which is the right behaviour and not one A should route around from the outside.

**The ask:** add `(6, 2): [(4, (0,1,2)), (5, (1,2,3))]` with resolution 4 to `_GENERATORS`/`_RESOLUTION`, or tell A the budget should change instead.

Recorded in code as `test_doe_arm_budget_is_47_design_runs_plus_one_confirmation`, marked `xfail(strict=True)` — so it fails loudly the moment B adds the generator, and retires itself rather than lingering as a stale skip.

---

## 🟡 ANSWER BEFORE THE PAPER

### Q5 [A] · The acquisition method assumes noiseless measurements. Ours are noisy.

**This is the most substantive technical question found so far.**

The spec mandates `qLogEI`, which needs "the best value seen so far". But our measurements are deliberately noisy, and the best of 48 noisy measurements is systematically flattering — the winner is partly whichever point drew lucky noise. At the higher noise level this is not a rounding error.

BoTorch ships `qLogNoisyExpectedImprovement` for exactly this case. **Its own documentation says it exists because the standard version's assumption "would require noiseless observations".**

The spec's stated reason for choosing `qLogEI` is numerical stability — a different concern entirely. So this looks unconsidered rather than decided.

**Both are implemented. The spec's choice is the default and I have not silently deviated.** This is a joint decision because Experiment 2's fairness rules say explicitly: *do not tune your own method while leaving the baselines at defaults.* Switching could be read either as a correctness fix or as exactly that.

**Options:** (a) keep `qLogEI` as specced and state the bias as a limitation; (b) switch to `qLogNEI` and justify it as matching our own observation model; (c) run both and report the difference — cheap, since compute turned out ~10× cheaper than estimated.

*My lean: (c) then (b). But it is A's call as much as mine.*

> ### ✅ ANSWERED [A] — **(c). Run both. `qLogEI` stays the pre-registered primary; `qLogNEI` is a pre-specified secondary, declared before any E2 result exists.**
>
> **Why not (b), the switch.** The fairness rule bites on things shared across arms — the initial design, the budget, the GP configuration. It cannot literally bite on the acquisition function, because **the baselines do not have one**: random, Sobol, LHS and the sequential DoE pipeline have no acquisition to leave at a default. So "tuning my method while baselines stay default" is not strictly what a switch would be. But that argument is a paragraph long, and a reviewer sees a one-line diff that swapped the acquisition after the spec named a different one. **Being right and looking tuned is a bad trade when the alternative is nearly free.**
>
> **Why (c) is nearly free.** PF4 measured the full grid at ~0.4 h. Doubling the BO arm alone costs roughly **+12 minutes**. That is not a budget question.
>
> **Why it is better than either pure option.** Pre-registering the spec's choice as primary makes the comparison unfalsifiable as post-hoc tuning, and it converts the objection into a result: *how much does the incumbent-bias correction actually buy?* The bias is that "best of 48 noisy observations" is inflated by whichever point drew lucky noise — so **it must be larger at σ_rel = 0.25 than at 0.10, and we have both levels on the same ensemble by design.** A noise × acquisition interaction is a genuine finding either way it lands. If the gap is negligible, that retires the concern with a number instead of a caveat.
>
> **Recorded consequence:** this makes the acquisition function a declared factor in E2's grid. It must go in the config as primary/secondary before the first E2 run, alongside the other endpoint declarations. **If it is not in the config file, it is not pre-registered.**

### Q6 [A] · Stepwise selection criterion for the descriptive third-order model

Listed in Doc 1 as an explicit "ask rather than assume". **Proceeding with backward elimination on p-values** unless told otherwise; the choice will be recorded in config. Descriptive only — no error bars are computed from it, ever, so the stakes are lower than they look.

### Q7 [YOU] · Author order, and whether the code can be released publicly

Doc 2 §A.6 lists these as open. Neither blocks building. Both block posting the preprint.

### Q8 [A] · The `Yvar` floor value

A owns the noise policy. The spec says imputed noise gets "a floor" and never gives a number. I used `1e-8` in a throwaway timing script; that is **not** a decision and shouldn't be inherited.

> ### ✅ ANSWERED [A] — **`Yvar_floor = σ_add² = 1e-4`.** The floor is the assay's additive noise variance, not a numerical epsilon.
>
> **The reasoning, because the number looks arbitrary and isn't.** The plug-in estimator is `Yvar = ŷ²σ_rel² + σ_add²` with `σ_add = 0.01`. Its infimum over all possible observations is at `ŷ = 0`, giving exactly `σ_add² = 1e-4`. So setting the floor there makes it **non-binding by construction in Phase 1** — it touches the estimator on a set of measure zero and changes no number we will publish. That is the point: a floor that alters Phase 1 results is a floor that is silently editing data.
>
> **What it is actually for is Phases 2 and 3**, where the interface stays and the estimator does not. Phase 2 swaps in a lookup table with no variance column; Phase 3 swaps in a human writing a CSV. Both can hand back `0`, or a blank. A fixed-noise GP given near-zero noise at one point will **interpolate that point exactly** and distort the fit in a neighbourhood around it — which is a silent, plausible-looking corruption of precisely the kind this project keeps finding. `1e-8` is small enough to let that through; `1e-4` says "no measurement in this assay is more precise than the noise floor of the assay", which is both true and enforceable.
>
> **Sanity check on stability, since the floor is applied in raw units and the GP sees standardized ones:** at a response of scale ~1, `var(Y)` is order 1e-2, so the floor lands near 1e-2 after `Standardize`. Comfortably conditioned. No jitter interaction.
>
> **Not negotiable separately from `σ_add`.** If `σ_add` ever changes, the floor changes with it and `oracle_version` bumps. It is a derived constant, not a free parameter — please don't let it drift into a magic number in a config file.

---

## ⚪️ NOTED — proceeding on a stated default

### Q10 · The two pre-registered numbers ✅ locked

512 candidate points; threshold at the within-instance top 20%. In `configs/experiment/e4.yaml`, in git, dated, before any result existed. **Do not change these after seeing results** — bump the version and say so in the paper if they must move.

### Q11 · Repo layout and the first commit

Nothing is committed yet. The first commit sets the layout for both people, which is arguably a joint decision. Current shape is the spec's §8 layout with package name `boec`.

**[YOU]:** happy for me to commit, or do you want to review first?

---

## ✅ CLOSED

| | Question | Answer |
|---|---|---|
| **C1** | What does `observation_noise=True` do at unrun points? | **Silently averages all training noise and applies it flat.** Source carries a `TODO: be smarter here`. Never used; we supply noise explicitly. |
| **C2** | Units for supplied noise? | **Standardized, not raw** — unlike training noise. Off by 161× otherwise. Handled in one place. |
| **C3** | Does `Normalize` without bounds learn from the data? | **Yes.** Verified. Always pass explicit bounds. |
| **C4** | Discrete-candidate function name? | `optimize_acqf_discrete(acq_function, q, choices, ..., inequality_constraints=None)`. |
| **C5** | Does batch selection cluster proposals? | **No.** It conditions on each pick before making the next, which satisfies the spec's "never top-q" rule. Verified in source and tested. |
| **C6** | Is the grid too slow for the full plan? | **No — ~10× faster than estimated.** Nothing needs shrinking. |
| **C7** | Does the 48-run pattern arithmetic work? | **Yes, exactly.** 32 + 12 + 4. Quality claim verified from first principles, not a lookup table. |
| **C8** | Face-centred vs rotatable CCD in the sub-box? | **Face-centred.** Rotatable axials leave the hard boundary (~2.38 vs 1.0 at d=6). Coded default + test. |

---

## Where B is up to — CODE COMPLETE

| Module | Plain English | Tests |
|---|---|---|
| `metrics.py` | "You promised X — what did we actually get?" **A imports this.** | 10 |
| `rsm.py` | The traditional curve fit, fairly represented, plus the descriptive stepwise variant | 33 |
| `designs.py` | Which 48 experiments to run ⚠️ *ownership open, Q2* | 28 |
| `surrogate.py` | The model that knows when it is guessing. All five silent traps caged | 24 |
| `optimizers.py` | What to try next — free search and fixed-menu | 30 |
| `parametric.py` | What a working scientist would try without knowing the answer | 15 |
| `discrimination.py` | The actual measurement, including the null that must be beaten | 27 |
| `campaign.py` | Propose, measure, learn, repeat. Saves its place | 27 |
| `runner.py` | Runs the whole grid, skips what is already done | 24 |
| `e4.py` | The experiment itself, wired end to end | 15 |
| | **Total** | **233** |

**Runway remaining: none.** Everything that does not need A's oracle is finished. Experiment 4 is wired end to end and verified against a stand-in landscape; only the landscape itself is missing.

**What happens the moment the oracle lands:**

1. **Drop it in — no code changes needed anywhere**, provided it answers the three questions in Q1. The interface is structural, so A's class imports nothing from B's.
2. **Run PF1**, blocked since day one, which decides whether E4 has anything to measure at all.
3. **Run E4** across every landscape and all four hiding levels.
4. On measured timings, the whole thing finishes **well under an hour**.

**Everything still open above is a decision or A's data lane — not a missing B module.**
