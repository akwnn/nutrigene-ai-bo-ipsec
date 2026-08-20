# ODIN: One-shot Design, Inference, Nomination

**Implementation specification v1.0** — as received, 2026-08-20.

> ⚠️ **Read `docs/ODIN-VERDICT.md` before implementing.** Four of this document's
> stages have already been measured in this repository, and two of its kill gates
> are mis-specified against numbers already on disk. The verdict document says
> which parts survive. This file is preserved verbatim as the object under review.

A budget-matched pipeline for choosing a single recipe from a noisy, small-budget
experimental campaign. Designed for the regime `N < 10d`, `sigma/range > 0.1`,
few available rounds. Intended to be compared head-to-head against classical
DoE/RSM and batch Bayesian optimization at equal well count.

Working name only. Rename before submission.

---

## 0. Read this first

The pipeline has four stages. Each stage exists because of a specific,
falsifiable mechanism. If you cannot state the mechanism, do not implement the
stage.

| Stage | What it does | Mechanism it exploits |
|---|---|---|
| 1. Design | Orthogonal-array-based LHS + true replicates | Stein (1987): LHS variance reduction is proportional to additive share. Replicates make `sigma` identifiable, which BO structurally lacks. |
| 2. Inference | Shape-constrained unimodal additive model + shrunk interaction GP | At `N < 10d` the surrogate has no capacity to be genuinely nonparametric. Encoding biphasic dose-response is free capacity. |
| 3. Nomination | Posterior mean over plausible-optimum region | Terminal regret is bounded by sup-norm surrogate error, not L2. `argmax` of the assay is the unshrunk extreme order statistic. |
| 4. Confirmation | EOC-allocated replicates on a screened shortlist | Optional. Only fires if a second round is affordable. |

**Critical gate before building anything.** Run the two checks in Section 9.1.
If either fails, the mechanism above is wrong and this spec should be discarded
rather than implemented.

---

## 1. Notation and problem statement

- `d` factors, coded to the unit box `X = [0,1]^d`.
- Latent response `f: X -> R`, scaled so `max_x f(x) = 1`.
- Observation `y(x) = f(x) + eps`, `eps ~ N(0, sigma^2)`.
- Total budget `N` wells. One well = one observation. Replicating a point
  consumes an additional well.
- Terminal action: nominate exactly one `xhat`.
- Loss: simple regret `R = 1 - f(xhat)`. Lower is better.
- Round: one plate cycle (prepare, incubate, read, decide). Reported separately
  from well count.

Default configuration used throughout: `d = 6`, `N = 48`, `sigma = 0.25`.

---

## 2. Stage 1 — Design

### 2.1 Budget split

```
N            = 48   total wells
N_unique     = 42   distinct design points
n_anchor     = 3    points measured in triplicate
extra_wells  = 6    = n_anchor * (3 - 1)
N_confirm    = 0    (set > 0 only if Stage 4 is enabled; taken OUT of N_unique)
```

Check: `N_unique + extra_wells = 42 + 6 = 48`. Pure-error degrees of freedom
= `n_anchor * (reps - 1) = 3 * 2 = 6`.

If Stage 4 is enabled with `N_confirm = 8`, then `N_unique = 34` and the total
is still 48. **The confirmation budget is always taken out of the design, never
added.** Any comparison that adds wells is not budget-matched and must not be
reported as a headline.

### 2.2 Primary construction: strength-2 orthogonal-array LHS

A strength-2 OA-LHS (Tang 1993) stratifies every one-dimensional marginal into
`n` equal bins **and** every two-dimensional projection into `s x s` cells. Plain
LHS only guarantees the first, and can place points along a diagonal in any
given 2D projection.

`scipy.stats.qmc.LatinHypercube(d, strength=2)` implements this, with the
constraint that `n = p^2` for prime `p` and `d <= p + 1`.

| p | n | max d |
|---|---|---|
| 5 | 25 | 6 |
| 7 | 49 | 8 |
| 11 | 121 | 12 |

```python
from scipy.stats import qmc

def oa_lhs(d, n, seed):
    """Strength-2 OA-LHS. Requires n = p^2, p prime, d <= p+1."""
    sampler = qmc.LatinHypercube(d=d, strength=2, seed=seed)
    return sampler.random(n)          # shape (n, d), values in [0,1)
```

For `d = 6, N_unique = 42` the constraint is not met (42 is not a prime square),
so use the fallback below. For a 49-well budget at `d <= 8` the constraint is met
exactly and you should use `oa_lhs` directly. **If your plate format allows 49
wells rather than 48, use it.** The design gain is real and the one-well
difference is immaterial.

### 2.3 Fallback: nearly-orthogonal maximin LHS

Always available, any `n`, any `d`. Construct by simulated annealing over column
permutations of a base LHS.

Objective to minimise:

```
J(D) = w1 * max_{j<k} |corr(D[:,j], D[:,k])|
     + w2 * (1 / min_{i<i'} ||D[i,:] - D[i',:]||_2)
```

with `w1 = 1.0`, `w2 = 0.1` after normalising both terms to unit scale on the
initial design.

```python
import numpy as np

def nolhs(d, n, seed, n_iter=20000, T0=0.1):
    """Nearly-orthogonal maximin LHS by simulated annealing on column perms."""
    rng = np.random.default_rng(seed)
    # base LHS: each column is a random permutation of stratum midpoints,
    # jittered inside its stratum
    strata = (np.arange(n) + 0.5) / n
    D = np.column_stack([rng.permutation(strata) for _ in range(d)])
    D += (rng.random((n, d)) - 0.5) / n

    def score(D):
        C = np.corrcoef(D, rowvar=False)
        max_corr = np.max(np.abs(C - np.eye(d)))
        dists = np.linalg.norm(D[:, None, :] - D[None, :, :], axis=-1)
        np.fill_diagonal(dists, np.inf)
        min_dist = dists.min()
        return max_corr + 0.1 * (1.0 / min_dist)

    s = score(D)
    for it in range(n_iter):
        T = T0 * (1 - it / n_iter)
        j = rng.integers(d)
        a, b = rng.choice(n, 2, replace=False)
        D2 = D.copy()
        D2[[a, b], j] = D2[[b, a], j]
        s2 = score(D2)
        if s2 < s or rng.random() < np.exp(-(s2 - s) / max(T, 1e-9)):
            D, s = D2, s2
    return D
```

Report the achieved `max |corr|` and `min_dist` in the paper. For `n = 42,
d = 6` you should reach `max |corr| < 0.05`.

### 2.4 Anchor selection for replicates

Replicates exist to identify `sigma`, not to average. Place them at points that
span the design so a position or batch effect would show up as heterogeneity.

```python
def choose_anchors(D, n_anchor=3, seed=0):
    """Pick well-separated anchors: centroid-nearest, then farthest-point."""
    centroid = D.mean(axis=0)
    idx = [int(np.argmin(np.linalg.norm(D - centroid, axis=1)))]
    while len(idx) < n_anchor:
        dists = np.linalg.norm(D[:, None, :] - D[idx], axis=-1).min(axis=1)
        dists[idx] = -np.inf
        idx.append(int(np.argmax(dists)))
    return idx
```

Each anchor is measured 3 times. In simulation this means drawing three
independent `eps` at the same `x`. On a real plate, place the three wells in
different plate regions so that plate-position variance is captured in `sigma`
rather than hidden.

### 2.5 Design output

```python
@dataclass
class Design:
    X: np.ndarray          # (N_unique, d) unique design points
    anchor_idx: list[int]  # indices measured multiple times
    reps: np.ndarray       # (N_unique,) int, replicate count per point
    # sum(reps) == N
```

---

## 3. Stage 2 — Inference

### 3.1 Model

```
f(x) = mu0 + sum_j g_j(x_j) + h(x)

y_i  = f(x_i) + eps_i,     eps_i ~ N(0, sigma^2)
```

- `g_j` : one-dimensional component, constrained to be **unimodal** (rises to a
  single interior peak then falls). The family nests monotone components as the
  peak location goes to a boundary, so a non-biphasic factor is representable.
- `h` : interaction remainder. GP with a short-lengthscale prior and a shrunk
  signal variance, so it can only express local wiggle and defaults to zero.

### 3.2 Unimodal component parameterisation

Do **not** use a parametric Hill form as the headline model. The synthetic
oracle is a Hill function and fitting a Hill surrogate to it is an inverse
crime that a reviewer will identify immediately. Assume only the **sign
pattern** (up then down), not the functional form.

Glue two monotone I-splines at a free peak location:

```
g_j(t) = A_j * u_j( t / p_j )                for t <= p_j
       = A_j * v_j( (1 - t) / (1 - p_j) )    for t >  p_j
```

where `u_j, v_j : [0,1] -> [0,1]` are monotone increasing with `u_j(0) = 0`,
`u_j(1) = 1`, `v_j(0) = 0`, `v_j(1) = 1`. Both are continuous at `t = p_j` with
value `A_j`. Represent each by a monotone I-spline with non-negative weights on
the simplex:

```
u_j(s) = sum_{k=1..K} w_jk * I_k(s),    w_j on the (K-1)-simplex
```

with `I_k` the order-3 I-spline basis on `[0,1]` with `K = 3` interior knots.
Two free weights per monotone piece.

Parameter count per factor: `A_j` (1) + `p_j` (1) + `w_j^left` (2) +
`w_j^right` (2) = **6**. At `d = 6` that is 36, plus `mu0`, `sigma`,
`tau_int`, and the interaction GP lengthscales. Tight against 48 observations,
which is why every parameter carries an informative prior.

### 3.3 Priors

```
mu0        ~ Normal(mean(y), sd(y))
A_j        ~ Normal(0, tau_add)              # sign free: peak or valley
tau_add    ~ HalfNormal(sd(y))
p_j        ~ Beta(2, 2)                      # favours interior peaks, allows edges
w_j^left   ~ Dirichlet(2 * ones(K))          # favours smooth monotone shapes
w_j^right  ~ Dirichlet(2 * ones(K))
tau_int    ~ HalfNormal(0.1 * var(y))        # SHRINKS interaction toward zero
ell_int_j  ~ LogNormal(log(0.25), 0.4)       # SHORT lengthscales only
sigma      ~ HalfNormal(sd(y))               # replicates dominate this in the likelihood
```

Two priors carry most of the design intent and must not be loosened without a
sensitivity analysis:

- `tau_int ~ HalfNormal(0.1 * var(y))` forces the interaction component to
  justify itself. Without it the GP absorbs the additive structure and the
  decomposition is meaningless.
- `ell_int_j ~ LogNormal(log(0.25), 0.4)` restricts the interaction GP to local
  features, leaving the global shape to the additive part. This is a cheap
  substitute for a formally orthogonal ANOVA kernel (Durrande et al.). Upgrade
  to the orthogonal kernel only if the identifiability diagnostic in 3.6 fails.

`sigma` is identified primarily by the anchor replicates through the likelihood.
No separate plug-in estimate is needed; feed all 48 observations, including the
duplicated anchor measurements, and the posterior on `sigma` will concentrate.
This is the whole point of Stage 1's replicate budget.

### 3.4 Inference engine

NumPyro (JAX) with NUTS. Not BoTorch: the model is non-conjugate and
shape-constrained, so the GPyTorch marginal-likelihood path does not apply.

```
chains        = 4
warmup        = 1000
samples       = 1000     (per chain, so 4000 draws total)
target_accept = 0.9
max_tree_depth = 10
```

Convergence gates, enforced in code, not by eye:

- `R_hat < 1.01` for every parameter
- `ESS_bulk > 400` for `mu0`, all `A_j`, all `p_j`, `sigma`, `tau_int`
- zero divergences after warmup, or `< 0.5%` with `target_accept` raised to 0.95

A run failing these gates is **excluded and logged**, not silently retried.
Report the exclusion rate. If it exceeds 2% the model is misspecified.

Expected runtime: 20 to 60 seconds per campaign on CPU. At 60 landscapes x
5 seeds x 20 grid cells that is roughly 100 CPU-hours. Parallelise over
landscapes with `joblib`.

### 3.5 Derived quantity: additive share

```python
def additive_share(posterior_draws, X_grid):
    """Posterior distribution of the additive share a-hat."""
    shares = []
    for draw in posterior_draws:
        add = sum(g_j(X_grid[:, j], draw, j) for j in range(d))
        inter = h(X_grid, draw)
        shares.append(np.var(add) / np.var(add + inter))
    return np.array(shares)
```

`X_grid`: 20,000 Sobol points. Report the posterior median and 90% interval of
`a_hat`. This is both a diagnostic and, in the two-round variant, the switching
statistic.

### 3.6 Identifiability diagnostic

Run once during development on synthetic data with **known** additive share.
Simulate at `a_true in {1.0, 0.8, 0.6, 0.4}`, fit, and check that the posterior
median of `a_hat` tracks `a_true` with acceptable error. If the standard error
of `a_hat` at `N = 48, d = 6` exceeds about 0.15, the two-round switching
variant (Section 5) is not viable and you should ship the one-round pipeline
only. **This is a real risk. Test it before building Stage 4.**

---

## 4. Stage 3 — Nomination

### 4.1 Plausible-optimum region

```python
def plausible_region(draws, X_grid, level=0.95):
    F = posterior_f(draws, X_grid)         # (n_draws, n_grid) latent f, NOT y
    lo = np.quantile(F, (1 - level) / 2, axis=0)
    hi = np.quantile(F, 1 - (1 - level) / 2, axis=0)
    return hi >= lo.max()                  # boolean mask over X_grid
```

Use the **latent** `f` posterior, not the posterior predictive of `y`. The
decision is about `f`.

### 4.2 The nomination

```python
def nominate(draws, X_grid):
    F = posterior_f(draws, X_grid)
    mask = plausible_region(draws, X_grid)
    mean_f = F.mean(axis=0)
    mean_f[~mask] = -np.inf
    x0 = X_grid[np.argmax(mean_f)]
    # polish with multi-start L-BFGS on the posterior mean, projected into the box
    return polish(x0, draws)
```

### 4.3 Mandatory reported diagnostics

For every campaign, log:

| Quantity | Definition | Why |
|---|---|---|
| `R` | `1 - f(xhat)` | the loss |
| `post_decision_surprise` | `yhat_at_xhat - E[f(xhat)]` | Smith & Winkler (2006). Nobody in bioprocess reports it. |
| `sup_err` | `max_x \|E[f(x)] - f(x)\|` on the grid | the L-infinity quantity the theory says governs `R` |
| `r2` | held-out or grid R-squared | the L2 quantity the theory says does **not** govern `R` |
| `coverage_95` | fraction of grid points where the 95% latent interval contains `f` | your current draft reports 76.4%; this must improve |
| `a_hat` | posterior median additive share | phase-diagram coordinate |
| `xhat_in_region` | whether the unconstrained argmax equals the in-region argmax | if these ever differ substantially, something is wrong |

`sup_err` and `r2` together are the test of the central theoretical claim. If
`R` correlates with `r2` more strongly than with `sup_err`, the theory is wrong
and you should say so.

---

## 5. Stage 4 — Optional confirmation round

Enable only when a second round is affordable. Budget comes out of `N_unique`.

### 5.1 Shortlist construction

1. Multi-start L-BFGS on `E[f(x)]` from 200 starts (100 Sobol, 100 seeded at
   design points), keeping local maxima inside the plausible region.
2. Deduplicate: drop any candidate within `0.15` (in coded units, per
   coordinate, Chebyshev distance) of a retained higher-valued candidate. Points
   closer than this are one arm, not several, and replicating them all wastes
   budget.
3. Screen: using the MCMC draws, keep candidate `i` only if
   `P(f_i >= f_max_candidate) > 0.05`. This is computed exactly from the draws:
   evaluate every draw at every candidate, then count.
4. Cap at `k = 4`.

### 5.2 Allocation by simulated expected opportunity cost

You already have posterior draws, so compute the allocation exactly by
simulation rather than using an OCBA closed form.

```python
def eoc(alloc, draws, cands, sigma_draws, n_sim=2000):
    """Expected opportunity cost of an allocation over candidate wells."""
    F = posterior_f(draws, cands)          # (n_draws, k)
    losses = []
    for _ in range(n_sim):
        i = rng.integers(len(draws))
        f_true, s = F[i], sigma_draws[i]
        # hypothetical confirmation observations
        obs = f_true + rng.normal(0, s / np.sqrt(np.maximum(alloc, 1)))
        # posterior update on candidate values: precision-weighted blend of
        # the prior (posterior mean/var across draws) and the new observations
        prior_m, prior_v = F.mean(0), F.var(0)
        obs_v = s**2 / np.maximum(alloc, 1e-9)
        post_m = (prior_m / prior_v + obs / obs_v) / (1 / prior_v + 1 / obs_v)
        post_m[alloc == 0] = prior_m[alloc == 0]
        losses.append(f_true.max() - f_true[np.argmax(post_m)])
    return np.mean(losses)


def allocate(N_v, draws, cands, sigma_draws):
    """Greedy sequential allocation: assign wells one at a time."""
    alloc = np.zeros(len(cands), dtype=int)
    for _ in range(N_v):
        gains = []
        for j in range(len(cands)):
            trial = alloc.copy(); trial[j] += 1
            gains.append(eoc(alloc, draws, cands, sigma_draws)
                         - eoc(trial, draws, cands, sigma_draws))
        alloc[int(np.argmax(gains))] += 1
    return alloc
```

Cost: `k * N_v` EOC evaluations, each `n_sim` cheap operations. Seconds.

### 5.3 Final pick

Refit the full model on all `N` observations (design plus confirmation) and take
`argmax` of the posterior mean over the shortlist. A conjugate-update shortcut
on candidate values is acceptable if the refit is too slow, but report which was
used.

### 5.4 Two-round switching variant (conditional on 3.6 passing)

If `a_hat` is estimable to within about 0.15:

```
if posterior_median(a_hat) > 0.7:
    spend round 2 on confirmation (Section 5.1-5.3)
else:
    spend round 2 on batch qLogNEI or qKG, seeded from the fitted model
```

The threshold `0.7` must be **derived from the phase diagram in Section 8, not
tuned on the test set**. Fit the crossover on a training sweep of additive
shares, then freeze it before running the evaluation grid. If you tune it on the
evaluation grid the entire result is invalid and a reviewer will say so.

---

## 6. Baselines

All at matched total well count `N = 48`. Rounds reported separately.

| ID | Arm | Terminal rule | Rounds |
|---|---|---|---|
| B1 | CCD/RSM (current arm: 20 screen + 27 CCD + 1) | argmax-y | 3 |
| B2 | CCD/RSM | in-region quadratic max | 3 |
| B3 | CCD/RSM with negative-definite Hessian constraint | constrained stationary point | 3 |
| B4 | DSD + second-order fit | in-region max | 2 |
| B5 | qLogEI | argmax-y | 10 |
| B6 | qLogEI | posterior mean | 10 |
| B7 | qLogNEI | posterior mean | 10 |
| B8 | qKG | posterior mean | 10 |
| **B9** | **one-shot LHS + plain Matern GP** | **posterior mean** | **1** |
| B10 | random uniform | argmax-y | 1 |

**B9 is the critical baseline.** It shares ODIN's design philosophy but none of
its model or terminal machinery. If ODIN does not beat B9, the entire modelling
contribution is worthless and the honest result is "one-shot design wins", which
is a different and smaller paper. Run B9 before anything else.

B8 (qKG) closes the most obvious hole in the current draft: the EI family was
benchmarked but not the acquisition whose decision theory matches a
posterior-mean terminal rule.

---

## 7. Ablations

Each removes exactly one component. Together these are the mechanism section.

| ID | Change from full ODIN | Isolates |
|---|---|---|
| A1 | no replicates, all 48 wells unique | value of identifying `sigma` |
| A2 | plain LHS instead of OA-LHS / NOLHS | value of 2D projection stratification |
| A3 | unconstrained additive GP components | value of the unimodality constraint |
| A4 | full-dimensional Matern GP, no additive decomposition | value of the additive structure |
| A5 | argmax-y terminal rule | value of shrinkage at the pick |
| A6 | MAP hyperparameters instead of NUTS | value of full Bayesian treatment |
| A7 | Stage 4 disabled | value of confirmation |

Report each as a paired delta against full ODIN on the same landscapes and
seeds. The sum of ablation effects will not equal the total effect; say so
rather than pretending it decomposes additively.

---

## 8. Evaluation protocol

### 8.1 Oracle

Extend the existing Hill generator with an explicit interaction-strength
parameter so that the **true additive share `a_true` is a swept independent
variable**, not a fixed property.

```
f(x) = (1 - lam) * sum_j g_j(x_j) + lam * interaction_term(x)
```

Calibrate `lam` so that the realised `a_true = Var(additive) / Var(total)`
hits targets in `{1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4}`, verified by Monte Carlo
per landscape and logged.

This turns the current draft's stated weakness ("Hill is too additive, 0.93")
into the paper's controlled instrument.

### 8.2 Grid

Priority order. Do not run the full cross product.

1. **Additive sweep** (the headline): `a_true` in 7 levels, at `sigma = 0.25`,
   `d = 6`, `N = 48`. All arms.
2. **Noise sweep**: `sigma` in `{0.05, 0.10, 0.15, 0.25, 0.35}` at
   `a_true = 0.9`, `d = 6`, `N = 48`.
3. **Budget/dimension sweep**: `N` in `{24, 48, 96}` x `d` in `{6, 8}` at
   `a_true = 0.9`, `sigma = 0.25`.
4. **External validation**: Levy, Rosenbrock, Hartmann6, Hall/Ogle replay.
   These are out-of-sample points on the phase diagram, not robustness
   afterthoughts.

### 8.3 Replication and pairing

- 60 landscapes per cell, 5 seeds each. Average seeds first, so `n = 60`.
- **Common random numbers.** For a given `(landscape, seed)`, every arm draws
  its observation noise from the same stream, seeded identically. This is the
  single largest variance reduction available and it is why 60 landscapes is
  enough where 25 was not.
- Store RNG state at every checkpoint. Do **not** attempt to replay stored visit
  logs to reconstruct campaigns; that is what broke the previous
  `1e-12` reproducibility gate. Re-run instead.

### 8.4 Statistics

- Primary contrast: paired Wilcoxon signed-rank per cell, ODIN versus each
  baseline.
- Effect size: paired bootstrap 95% interval on the mean difference.
- Equivalence: TOST at SESOI `0.02`.
- Multiplicity: Holm across the baseline family within each cell. Pre-declare
  B9 and B5 as the two confirmatory comparisons; the rest are exploratory.
- Report achieved MDE per cell. With paired CRN at `n = 60` you should reach
  MDE well below `0.02`; if you do not, the pairing is not working and you
  should debug it before interpreting anything.

### 8.5 Cost accounting

Report every result on two axes: **wells** and **rounds**. ODIN uses 1 or 2
rounds, CCD/RSM 3, batch BO 10. In cell culture a round is two weeks and a well
is a pipetting step, so the rounds axis is often the binding constraint and may
be the more persuasive result.

---

## 9. Kill tests

Written down in advance. Each is cheap and each can end the project.

### 9.1 Two gates before implementation (run these first, one day)

**G1 — lengthscale check.** Pull the fitted ARD lengthscales from the existing
stored GP models. If the median across dimensions is below about 0.4 in coded
units, the "N < 10d forces low-order structure" argument is wrong and the
additive design story collapses. **Stop and re-plan.**

**G2 — norm check.** On every stored run, compute `sup_err` and `r2` against the
known latent `f` on a dense grid, and correlate each with the realised regret. If
`r2` correlates more strongly than `sup_err`, the L-infinity thesis is wrong.
**Stop and re-plan.**

### 9.2 Gates during development

**G3 — oracle ladder.** Take qLogEI at `d = 6, sigma = 0.25, N = 48` and grant
progressively more oracle information. Each rung attributes a slice of the
regret.

| Rung | Granted | Tests | Known value |
|---|---|---|---|
| 0 | nothing | baseline | 0.1553 |
| 1 | oracle terminal rule (hidden tested-best) | identification headroom | 0.0755 |
| 2 | true `sigma` | ceiling on Stage 1 replicates | ? |
| 3 | true lengthscales/hyperparameters | model-fitting bottleneck | ? |
| 4 | true additive structure | ceiling on Stage 2 | ? |
| 5 | best of 20 LHS draws in hindsight | ceiling on Stage 1 design | ? |
| 6 | everything | irreducible noise floor | ? |

If rung 2 moves regret by less than `0.01`, **drop the replicates**. If rung 4
does not collapse regret toward the floor, **drop the additive model**. This
ladder is itself a publishable figure and it stops you building the wrong stage.

**G4 — additive-share estimability.** Section 3.6. If `a_hat` has SE > 0.15 at
`N = 48, d = 6`, ship the one-round pipeline and drop Section 5.4.

**G5 — the crossover exists.** In the additive sweep, one-shot LHS + GP must beat
qLogEI at `a_true = 0.9` and lose at `a_true = 0.4`, with a crossover somewhere
between. If there is no crossover, the phase-diagram framing is dead.

**G6 — beats B9.** If full ODIN does not beat one-shot LHS + Matern GP +
posterior mean by more than `0.01` at `a_true = 0.9, sigma = 0.25`, the model
contribution is null. Report honestly and pivot the paper to the design and
terminal-rule result.

### 9.3 Pre-registration

Freeze, before running the evaluation grid in Section 8.2:

- the switching threshold in 5.4
- all priors in 3.3
- the SESOI (0.02) and the two confirmatory contrasts
- the shortlist parameters `k = 4`, dedup radius `0.15`, screen `P > 0.05`
- the budget split in 2.1

Commit hash and date in the repository. Given that this paper's own thesis is
about analysis choices driving results, an unregistered method selection would
be self-refuting.

---

## 10. Software and layout

```
python 3.11
numpyro >= 0.15      NUTS on the constrained model
jax                    # numpyro backend
scipy >= 1.11          # qmc.LatinHypercube(strength=2)
botorch 0.18.1         # baselines B5-B9 only
gpytorch 1.15.2
torch 2.13.0
numpy, pandas, joblib, arviz   # arviz for R_hat / ESS gates
```

```
src/odin/
  design.py       # oa_lhs, nolhs, choose_anchors, Design
  model.py        # numpyro model, I-spline basis, fit(), posterior_f()
  nominate.py     # plausible_region, nominate, diagnostics
  confirm.py      # shortlist, eoc, allocate
  baselines.py    # B1-B10
  oracle.py       # Hill generator with swept additive share
  runner.py       # campaign loop, CRN seeding, checkpointing
  analysis.py     # paired Wilcoxon, bootstrap, TOST, Holm, MDE
scripts/
  gate_lengthscales.py    # G1
  gate_norms.py           # G2
  oracle_ladder.py        # G3
  run_grid.py
results/
  <cell>/<landscape>/<seed>/campaign.json   # includes RNG state
docs/
  PREREG.md
```

Every campaign JSON must contain: the design, all observations, the RNG state at
each checkpoint, the posterior summary, `xhat`, and all diagnostics from 4.3.
Anything not written to disk at run time cannot be recovered later; that is the
lesson of the previous replay failure.

---

## 11. Known pitfalls

1. **Inverse crime.** The unimodality constraint is true by construction on a
   Hill oracle. This is why the constraint must be a *shape* assumption
   (I-spline, up-then-down) and never a Hill parametric form, and why Levy,
   Rosenbrock and Hartmann6 must be run. Report ODIN's degradation there
   prominently rather than burying it.

2. **The interaction GP eats the additive structure.** If `tau_int` posterior
   concentrates away from zero on data you know to be additive, the priors in
   3.3 are too loose or the lengthscale prior is too wide. Diagnose with 3.6
   before trusting any `a_hat`.

3. **Plate position effects.** In simulation, replicates are ideal. On a real
   plate they carry position variance. Simulate a per-well position offset
   `N(0, tau_pos^2)` and find the `tau_pos` at which Stage 1 stops helping. This
   is the first question a bioprocess reviewer will ask.

4. **The confirmation round adds a round.** For CCD/RSM that is 3 to 4, a 33%
   increase. Report it. Do not let the wells-axis result hide a rounds-axis
   regression.

5. **Design constraint arithmetic.** `strength=2` in scipy requires `n = p^2`
   and `d <= p+1`. Check this at config-parse time and fail loudly rather than
   silently falling back.

6. **NUTS failures.** Enforce the convergence gates in code and log exclusions.
   A silently retried chain is a hidden researcher degree of freedom.

7. **Do not tune on the evaluation grid.** Every threshold in this document is
   either derived, set by the training sweep, or frozen in `PREREG.md`.

---

## 12. What this can and cannot claim

**Can claim, if the gates pass:**

> In the regime `N < 10d`, `sigma/range > 0.1`, additive share above the
> measured crossover, a one-shot orthogonal-array design with replicate-based
> noise identification, a shape-constrained additive surrogate, and a shrinkage
> terminal rule achieves lower simple regret than both classical DoE/RSM and
> batch Bayesian optimization at matched well count and lower round count. The
> regime boundary is predictable in advance from quantities measurable in the
> first plate.

**Cannot claim:**

- that this beats BO in general
- that adaptivity is never useful (Hartmann6 will say otherwise)
- anything about wet-lab performance until Phase 3 runs
- that the ablation effects decompose additively
- that a threshold tuned on the evaluation grid was pre-specified

---

## 13. Prior art to cite and distinguish from

| Work | Relationship |
|---|---|
| Stein (1987) *Technometrics* 29:143 | LHS variance reduction proportional to additive share. The theoretical basis for Stage 1. Not previously connected to BO-versus-design comparisons. |
| Owen (1992, 1994); Tang (1993) *JASA* | OA-based LHS, 2D projection stratification. |
| Box & Wilson (1951); Myers, Montgomery & Anderson-Cook | Centre-point replication for pure error. The one thing RSM does that BO discarded. |
| Jones & Nachtsheim (2011) | Definitive screening designs. Baseline B4. |
| Riihimaki & Vehtari (2010) | Shape-constrained GPs via virtual derivative observations. Alternative to the I-spline route. |
| Duvenaud et al.; Durrande et al. | Additive and orthogonal ANOVA kernels. The rigorous upgrade path for 3.3. |
| Bogunovic et al. (2016) TruVaR; BALLET | Region-restricted variance reduction. Closest prior art to Stage 4's shortlist. Distinguish: theirs acts during search on a discrete domain with asymptotic guarantees; ours is a terminal allocation with the budget taken out of search. |
| Chen et al. (2000) OCBA; Frazier, Powell & Dayanik (2009) | Ranking and selection, correlated knowledge gradient. Stage 4's allocation is a simulation-based EOC variant using MCMC draws directly. |
| Smith & Winkler (2006) *Manage. Sci.* 52:311 | Optimizer's curse, post-decision surprise. The diagnostic in 4.3. |
| Efron (2011) *JASA* 106:1602 | Tweedie selection-bias correction. Optional ablation on the terminal rule. |
| Letham et al. (2019) *Bayesian Analysis* 14:495 | Documents EI clustering under noise. Cite as independent confirmation of the mechanism, not as a novel observation of ours. |
| Binois et al. (2019) *Technometrics* | Replication versus exploration in stochastic simulation. Different objective (surface fitting, large budget) but the nearest precedent for Stage 1's replicates. |
| Siska & Helleckes (2026) *Biotechnol. Bioeng.* 123:805 | Current bioprocess BO guidance, which explicitly advises against replication to maximise information gain. The direct target of Stage 1. |
| Gisperg et al. (2025) *Biotechnol. Bioeng.* 122:1313 | Bioprocess BO landscape review. |

---

## 14. Minimum viable first week

1. **Day 1.** Gates G1 and G2 on existing stored runs. If either fails, stop.
2. **Day 2.** Oracle ladder G3. This tells you which stages are worth building.
3. **Day 3.** Baseline B9 (one-shot LHS + Matern GP + posterior mean) at
   `d = 6, sigma = 0.25, N = 48`, 25 landscapes, against existing B1 and B5.
   Confirms the headline effect exists before you build anything new.
4. **Days 4-5.** Stage 1 design code plus Stage 3 nomination, with a plain
   Matern GP in between. This is ODIN-minus-Stage-2 and it should already sit
   between B9 and full ODIN.
5. **Week 2 onward.** Stage 2 model, ablations, then the grid.

Do not build Stage 4 until G4 passes.
