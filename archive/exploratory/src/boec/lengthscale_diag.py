"""Is the GP's fitted lengthscale its own, or still the prior's?

OWNERSHIP: Person A. **Diagnostic only.** Nothing in this module is used by any
experiment, arm, or config. It changes no E2 number and is not permitted to.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------

E2's pre-registered primary cell (d=6, sigma_rel=0.25) has BO losing to the
sequential-DoE arm. Two explanations survive that result and they predict
opposite things about the model's internals:

  1. **Nuisance dimensions.** BO wins at d=8 because ARD copes with factors that
     do not matter, and d=6 has fewer of them. Nothing wrong with the model.

  2. **A prior that does not constrain.** BoTorch's
     `get_covar_module_with_dim_scaled_prior` sets
     `LogNormalPrior(loc = sqrt(2) + 0.5*log(d), scale = sqrt(3))`. It came from
     a paper whose abstract concerns high dimensions; the maintainers state that
     the older `Gamma(3, 6)` "yields good results on low-dimensional problems"
     and that the replacement is meant to "perform well independently of the
     dimensionality of the problem" (BoTorch Discussion #2451). At d=8 four of
     eight factors are genuinely inert, so a long lengthscale on those is
     CORRECT. At d=6 four of six are active, and with 14 initial points at 25%
     noise the likelihood may be too weak to pin them down.

------------------------------------------------------------------------------
THE CORRECTION THAT MATTERS, AND WHY THE FIRST VERSION OF THIS RULE WAS VOID
------------------------------------------------------------------------------

**The first version of this module anchored its decision rule on the prior
MEDIAN, exp(loc) = 10.08 at d=6, and it could not fail.** The fit is MAP, not
maximum likelihood -- `ExactMarginalLogLikelihood` adds `log p(lengthscale)` --
and the constraint carries `transform=None`, so raw and constrained lengthscales
coincide and the argmax of the prior term alone is the prior **MODE**:

    exp(loc - scale**2) = 0.5016 at d=6, 0.5792 at d=8

That is also the value gpytorch initialises the kernel to. Measured: a fit on
14 points whose outcomes carry no dependence on X at all returns 0.5016 on every
dimension, to four decimals. The old rule read "lengthscales far below 10" as
"the data is winning", so a model that had learned **nothing** scored as maximal
learning. The measured opening-design median was 0.502.

**So `exp(loc)` is not the reference for anything.** Two consequences:

  * the reference for "has this fit learned?" is not a formula at all, it is the
    **empirical no-signal null**: refit the same design, with the same noise, on
    permuted outcomes. That destroys the X-to-y relationship and preserves
    everything else. Anything the real fit does that the permuted fit does not
    is signal.
  * hypothesis (2) has to be restated. This prior is not *attractive* toward long
    lengthscales, it is *permissive* of them: per dimension it prefers ls=0.5
    over ls=10 by only ~1.5 nats, where Gamma(3, 6) prefers it by ~51. The real
    difference between the two configurations is the size of the penalty on long
    lengthscales, not the location of the belief -- their modes are 0.502 and
    0.333, which is nearly the same place.

------------------------------------------------------------------------------
THE DECISION RULE, RE-ANCHORED, FIXED BEFORE THE NEW NUMBERS ARE READ
------------------------------------------------------------------------------

Per cell, at each checkpoint, compare the real fit against its own **paired
permutation null** (same X, same Yvar, permuted Y):

  * active lengthscales **indistinguishable from the null**
      -> the fit is uninformed. What table 2.1 reports is the initialisation,
         not a learned quantity, and hypothesis (2) is live.
  * active lengthscales **significantly below the null**, inert ones not
      -> ARD is extracting real structure. (2) is refuted for the dimensions
         that matter, and reading (1) survives this test.
  * both moved
      -> the fit is responding to something, but not selectively; report as
         "neither cleanly" rather than forcing a verdict.

The ARD separation ratio (inert / active) is the statistic **immune to the
anchoring error above**, because the prior is identical on every dimension: a
purely prior-driven fit gives exactly 1.0, so any departure from 1.0 is data.
It is reported alongside, and it decides the d=6-versus-d=8 comparison.

Over- versus under-smoothing is read from the ratio of fitted lengthscale to the
**true feature scale** (`censored_fwhm`), never from the prior.

------------------------------------------------------------------------------
"""

from __future__ import annotations

import numpy as np

from boec.oracles import HillInstance, HillOracle
from boec.surrogate import base_kernel

__all__ = [
    "censored_fwhm",
    "fraction_at_floor",
    "permutation_null_lengthscales",
    "prior_band_fraction",
    "prior_loc_scale",
    "prior_mode",
]


def prior_loc_scale(kernel_or_model) -> tuple[float, float]:
    """The lengthscale prior's parameters, read off the live object.

    **Read, never hardcoded.** The entire diagnostic is a comparison against
    this prior, so a version of the library that ships different numbers would
    silently turn every conclusion below into an answer to a different question.

    Returns:
        ``(loc, scale)`` of the log-normal prior. The prior median lengthscale
        is ``exp(loc)``, in the model's normalized input units.
    """
    prior = base_kernel(kernel_or_model).lengthscale_prior
    if not (hasattr(prior, "loc") and hasattr(prior, "scale")):
        raise TypeError(
            f"{type(prior).__name__} is not log-normal, so (loc, scale) is "
            "undefined. The Gamma counterfactual kernel lands here; do not paper "
            "over it with a duck-typed fallback that returns plausible numbers "
            "for a different distribution."
        )
    return float(prior.loc), float(prior.scale)


def prior_mode(kernel_or_model) -> float:
    """The lengthscale a MAP fit returns when the data say nothing.

    `exp(loc - scale**2)`: 0.5016 at d=6, 0.5792 at d=8. This is the number the
    old version of this module should have been comparing against, and it is
    also the value gpytorch initialises the kernel to, so an unfitted model and
    a fully uninformed fitted one are indistinguishable.

    **Still not the reference for "has this fit learned anything".** Use
    :func:`permutation_null_lengthscales` for that -- with real data present the
    likelihood always moves the fit somewhere, and how far it moves on pure noise
    is an empirical question, not a formula. This exists so the anchoring error
    is visible in the output rather than reconstructed later.
    """
    loc, scale = prior_loc_scale(kernel_or_model)
    return float(np.exp(loc - scale**2))


def prior_band_fraction(ls: np.ndarray, loc: float, scale: float) -> float:
    """Fraction of lengthscales inside the central 68% of the PRIOR DISTRIBUTION.

    **This is a prior-mass statistic. It is NOT a measure of prior dominance,
    and it was reported as one.** The band `|log(ls) - loc| <= scale` spans
    [1.78, 56.9] at d=6 and therefore *excludes the prior mode 0.502 entirely* --
    so a completely uninformed MAP fit scores 0.00 on it, which the first version
    of this module printed as strong evidence against prior dominance.

    Retained only because it answers a real if narrow question: how far into the
    prior's tail a fitted lengthscale sits. Anything about dominance comes from
    :func:`permutation_null_lengthscales`.
    """
    ls = np.asarray(ls, dtype=float).ravel()
    if ls.size == 0:
        return float("nan")
    return float(np.mean(np.abs(np.log(ls) - loc) <= scale))


def fraction_at_floor(ls: np.ndarray, lower_bound: float, rtol: float = 1e-3) -> float:
    """Fraction of lengthscales pinned to the library's positivity constraint.

    Should be ~0. Anything else means the response is wilder than the kernel can
    represent, which is a different failure from the one under investigation and
    has to be excluded before anything else here means much.

    Raises on a configuration with no floor -- the `Gamma(3, 6)` kernel installs
    `Positive()`, whose lower bound is 0.0, and returning 0.0 there would read as
    "nothing is pinned" when there is nothing to pin against. Silent-wrong on the
    exact configuration a sensitivity analysis would use.
    """
    if lower_bound <= 0.0:
        raise ValueError(
            f"lower_bound={lower_bound} — this kernel has no lower bound on its "
            "lengthscales, so 'fraction at the floor' is undefined rather than zero."
        )
    ls = np.asarray(ls, dtype=float).ravel()
    if ls.size == 0:
        return float("nan")
    return float(np.mean(ls <= lower_bound * (1.0 + rtol)))


def permutation_null_lengthscales(train_X, train_Y, train_Yvar, bounds,
                                  n_perm: int = 3, seed: int = 0) -> np.ndarray:
    """What this exact design produces when the outcomes carry no signal.

    Refits the production model on the identical inputs and identical noise, with
    the outcome vector **permuted**. That destroys the X-to-y relationship and
    preserves the design geometry, the sample size, the outcome marginal and the
    noise level exactly, so the difference between a real fit and this one is
    attributable to signal and to nothing else.

    This is the reference the first version of this module got wrong by using a
    closed-form prior quantity instead. A formula cannot answer it: with n points
    present the likelihood term always moves the fit somewhere, and how far it
    moves on pure noise depends on n, on the design, and on the noise level.

    Returns:
        ``(n_perm, d)`` fitted lengthscales, one row per permutation.
    """
    import torch

    from boec.surrogate import build_gp, lengthscales

    rng = np.random.default_rng(seed)
    n = int(train_Y.shape[0])
    out = []
    for _ in range(n_perm):
        idx = torch.as_tensor(rng.permutation(n), dtype=torch.long)
        model = build_gp(train_X, train_Y[idx], train_Yvar[idx], bounds)
        out.append(lengthscales(model).detach().double().cpu().numpy().ravel())
    return np.stack(out)


def censored_fwhm(inst: HillInstance, n_grid: int = 4001) -> np.ndarray:
    """True feature scale per factor: the width of its super-half-maximum set.

    Each unmodulated factor is peak-normalised to exactly 1, so this is the
    measure of ``{x in [0, 1] : f0_j(x) >= 0.5}``.

    **Censored at the box, deliberately.** A factor whose decline is shallow
    never falls back through half-maximum before x=1, so its true width is
    unbounded in a sense the GP can never observe -- the model only ever sees
    [0, 1]. Reporting the censored width keeps the comparison against a fitted
    lengthscale in the same units and on the same domain. The censoring is
    conservative for the question at hand: it makes the true scale look LARGER,
    so a fitted lengthscale that still exceeds it is over-smoothing for certain.

    Returns:
        ``(d,)`` widths in coded units.
    """
    orc = HillOracle(inst)
    grid = np.linspace(0.0, 1.0, n_grid)
    X = np.tile(np.asarray(inst.optimum_x, dtype=float), (n_grid, 1))
    out = np.empty(inst.dim, dtype=float)
    for j in range(inst.dim):
        Xj = X.copy()
        Xj[:, j] = grid
        out[j] = float(np.mean(orc.base_factors(Xj)[:, j] >= 0.5))
    return out
