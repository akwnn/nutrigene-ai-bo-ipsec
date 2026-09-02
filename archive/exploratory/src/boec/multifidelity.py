"""Q47 — the cheap-readout model, the cost accounting, and the recalibration.

OWNERSHIP: Person A. Phase 1 only, and **not a method**: this supports a *threshold
calculation*. Nothing here proposes running a two-tier design; it measures the conditions
under which one would pay.

------------------------------------------------------------------------------
WHY ρ AND NOT σ_cheap
------------------------------------------------------------------------------

A lab can measure a correlation in a morning. It cannot measure ``sigma_cheap``, which is
not interpretable without also knowing the signal spread of the response over the region
being searched. So the sweep is parameterised by the correlation and the noise is derived
from it::

    rho = corr(y_cheap, y_true) = a*sf / sqrt(a^2 sf^2 + sc^2)
      =>  sc = a * sf * sqrt(1/rho^2 - 1)

------------------------------------------------------------------------------
THE INVARIANCE THAT MAKES (a, b) TESTABLE RATHER THAN DECORATIVE
------------------------------------------------------------------------------

Because ``sc`` carries the same factor ``a``, the readout is an *exact* affine image of a
calibration-free quantity::

    y_cheap = a * (y_true + sf*sqrt(1/rho^2 - 1) * z) + b

An affine map with positive slope preserves rankings, so **any arm that only ranks the
cheap values is provably invariant to the sampled calibration.** Screen-then-confirm is
such an arm. That is not an approximation to be checked empirically; it is an identity,
and ``tests/test_multifidelity.py`` asserts it as one. Only the joint model, which has to
*estimate* the calibration, can be hurt by it — which is the entire reason the
registration samples ``(a, b)`` per instance rather than fixing them.

------------------------------------------------------------------------------
THE COST IDENTITY
------------------------------------------------------------------------------

Equal **total cost**, never equal evaluation count. One cheap assay costs ``1/c`` of an
expensive one, so a two-tier arm satisfies ``n_expensive + n_cheap/c == budget``.
:func:`allocate` refuses any split it cannot spend exactly, because a rounding fudge here
would quietly hand one arm more money than the other and every number downstream would
be a comparison between unequal budgets.

------------------------------------------------------------------------------
THE JOINT MODEL, AND WHAT IT IS NOT
------------------------------------------------------------------------------

:func:`recalibrate` is regression-adjusted co-kriging (Le Gratiet & Garnier's recursive
formulation with the discrepancy absorbed into the noise), **not** an ICM or AR(1)
co-kriging GP. The reason is stated in the Q47 registration and is worth repeating here:
BoTorch's ``MultiTaskGP`` brings its own kernel, priors and transforms, so the joint arm
would differ from the screening arm in the fidelity structure *and* in the surrogate.
Q34 and Q45 both exist because this project previously confounded design with model. The
adjustment route hands the pooled data to the same ``build_gp`` every other arm uses and
changes exactly one thing.

**It also hands the joint model the correct functional form** — the generative cheap
readout is affine plus Gaussian noise, which is precisely what the OLS adjustment
assumes. So the joint arm is an upper bound on what a joint model achieves here, and a
failure to beat screen-then-confirm is the stronger of the two possible findings.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "Allocation",
    "CheapTier",
    "allocate",
    "cheap_sigma",
    "draw_cheap",
    "recalibrate",
    "signal_sd",
    "split_confirm",
    "top_k",
]

_EXACT = 1e-6


@dataclass(frozen=True)
class Allocation:
    """How a budget of expensive-equivalents is split across the two tiers.

    Attributes:
        n_expensive: confirmations run on the expensive readout.
        n_cheap: screening points run on the cheap readout.
        cost_ratio: cheap assays purchasable for the price of one expensive assay.
        budget: the total, in expensive-equivalents. Spent exactly.
    """

    n_expensive: int
    n_cheap: int
    cost_ratio: int
    budget: int

    @property
    def spent(self) -> float:
        """Total cost in expensive-equivalents. Must equal ``budget``."""
        return self.n_expensive + self.n_cheap / self.cost_ratio


@dataclass(frozen=True)
class CheapTier:
    """One instance's cheap readout: ``y_cheap = a*y_true + b + N(0, sigma_cheap^2)``.

    Attributes:
        a: slope. Strictly positive — a readout that anti-correlates with the response
            is not a lower-fidelity version of it and is outside the model.
        b: offset.
        sigma_cheap: readout noise SD, derived from the target correlation by
            :func:`cheap_sigma`. **Never set directly** — setting it independently of
            ``a`` breaks the affine invariance the harness is tested against.
        rho_target: the correlation with ``y_true`` this tier is meant to achieve.
    """

    a: float
    b: float
    sigma_cheap: float
    rho_target: float


def allocate(*, budget: int, cost_ratio: int, phi: float) -> Allocation:
    """Split ``budget`` expensive-equivalents, giving fraction ``phi`` to the cheap tier.

    Args:
        budget: total spend in expensive-equivalents.
        cost_ratio: cheap assays per expensive assay.
        phi: fraction of the budget spent on screening. ``0.0`` is single-tier.

    Returns:
        The split, with ``spent == budget`` exactly.

    Raises:
        ValueError: if the split cannot be spent exactly in whole assays. Rounding it
            would give one arm more money than another, and every contrast downstream
            would then compare unequal budgets.
    """
    if not 0.0 <= phi < 1.0:
        raise ValueError(f"phi must be in [0, 1); got {phi}")
    if cost_ratio < 1:
        raise ValueError(f"cost_ratio must be at least 1; got {cost_ratio}")
    cheap_spend = phi * budget
    exp_f, cheap_f = budget - cheap_spend, cheap_spend * cost_ratio
    n_exp, n_cheap = int(round(exp_f)), int(round(cheap_f))
    if abs(n_exp - exp_f) > _EXACT or abs(n_cheap - cheap_f) > _EXACT:
        raise ValueError(
            f"phi={phi} at cost_ratio={cost_ratio} cannot spend budget={budget} "
            f"exactly: {exp_f} expensive and {cheap_f} cheap assays"
        )
    return Allocation(n_expensive=n_exp, n_cheap=n_cheap,
                      cost_ratio=int(cost_ratio), budget=int(budget))


def cheap_sigma(a: float, sigma_f: float, rho: float) -> float:
    """Readout noise SD giving correlation ``rho`` with the truth. A **standard deviation**.

    Args:
        a: the readout's slope. Must be positive.
        sigma_f: SD of the true response over the region being searched.
        rho: target correlation, in ``(0, 1]``.

    Returns:
        ``a * sigma_f * sqrt(1/rho^2 - 1)``; exactly ``0.0`` at ``rho == 1``.
    """
    if a <= 0.0:
        raise ValueError(f"the cheap readout's slope must be positive; got {a}")
    if not 0.0 < rho <= 1.0:
        raise ValueError(f"rho must be in (0, 1]; got {rho}")
    if sigma_f <= 0.0:
        raise ValueError(f"sigma_f must be positive; got {sigma_f}")
    if rho == 1.0:
        return 0.0
    return float(a * sigma_f * np.sqrt(1.0 / rho**2 - 1.0))


def draw_cheap(y_true: np.ndarray, tier: CheapTier,
               rng: np.random.Generator | None = None, *,
               z: np.ndarray | None = None) -> np.ndarray:
    """``a*y_true + b + sigma_cheap*z``, with ``z`` standard normal.

    Args:
        y_true: ``(n,)`` noiseless response at the screening points.
        tier: the instance's cheap readout.
        rng: draws ``z`` when it is not supplied.
        z: pre-drawn standard normals. Supplying them is what makes the affine
            invariance testable as an exact identity rather than a sample statistic.
    """
    y = np.asarray(y_true, dtype=float).ravel()
    if z is None:
        if rng is None:
            raise ValueError("supply either rng or z")
        z = rng.standard_normal(y.shape)
    z = np.asarray(z, dtype=float).ravel()
    if z.shape != y.shape:
        raise ValueError(f"z {z.shape} must match y_true {y.shape}")
    return tier.a * y + tier.b + tier.sigma_cheap * z


def signal_sd(values: np.ndarray) -> float:
    """SD of the true response over a screening sample. The ``sigma_f`` in ``rho``.

    Estimated from a fixed Sobol sample of the *truth*, so it is a property of the
    landscape and the region, and identical across noise levels and arms. It is a
    construction parameter of the sweep, not something any method observes.
    """
    return float(np.asarray(values, dtype=float).std())


def top_k(values: np.ndarray, k: int) -> np.ndarray:
    """Indices of the ``k`` largest values, ties broken by index for determinism."""
    v = np.asarray(values, dtype=float).ravel()
    if not 0 < k <= v.size:
        raise ValueError(f"k must be in (0, {v.size}]; got {k}")
    return np.argsort(-v, kind="stable")[:k]


def split_confirm(values: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """``k//2`` best by cheap value, plus the rest drawn uniformly from what is left.

    Estimating the cheap-to-expensive relation needs spread in the cheap value.
    Confirming only the top ``k`` truncates that range, attenuates the fitted slope, and
    would handicap the joint model for a reason that has nothing to do with the model.
    """
    v = np.asarray(values, dtype=float).ravel()
    if not 0 < k <= v.size:
        raise ValueError(f"k must be in (0, {v.size}]; got {k}")
    n_top = k // 2
    order = np.argsort(-v, kind="stable")
    chosen = order[:n_top]
    rest = order[n_top:]
    extra = rng.choice(rest, size=k - n_top, replace=False)
    return np.concatenate([chosen, extra])


@dataclass(frozen=True)
class Recalibration:
    """The cheap tier mapped onto the expensive scale.

    Attributes:
        pseudo: ``(n,)`` mapped values, usable as observations of the response.
        variance: the single **variance, in raw outcome units** to attach to all of them.
        slope, intercept: the fitted map.
        resid_var: residual variance of the fit, ``variance`` before the floor.
        mean_yvar: mean plug-in variance of the expensive readings it was fitted to.
            Exposed because ``resid_var - mean_yvar`` is the *unbiased* target and is
            unusable — see :func:`recalibrate`.
    """

    pseudo: np.ndarray
    variance: float
    slope: float
    intercept: float
    resid_var: float
    mean_yvar: float


def recalibrate(*, cheap_paired: np.ndarray, exp_paired: np.ndarray,
                cheap_all: np.ndarray, yvar_exp: np.ndarray,
                sigma_add: float) -> Recalibration:
    """Map every cheap reading onto the expensive scale, with an honest variance.

    OLS-regress the expensive observation on the cheap observation at the points measured
    on both tiers, then apply that fit to every cheap point.

    **Why the variance is the raw residual variance and not the unbiased one.** The
    residual of that regression is ``(f - pseudo) + e``: the pseudo-observation's own
    error plus the expensive readout's noise. The unbiased estimate of what we want is
    therefore ``resid_var - mean(yvar_exp)`` — and it is unusable here. At this project's
    primary noise level the expensive readout carries more variance than the signal
    (correlation 0.583 with the truth), so the two terms are the same size, the
    difference is dominated by estimation error at 30 residual degrees of freedom, and
    it went **negative on every draw tested** — pinning the pseudo-observations at the
    noise floor and handing the model a set of points it believed were exact.

    So the raw residual variance is used, floored at the assay's own noise floor. That is
    **deliberately conservative**: it inflates the pseudo-variance by roughly the
    expensive readout's noise, which down-weights the cheap tier. ``resid_var`` and
    ``mean_yvar`` are both returned so the size of that conservatism is measurable after
    the fact rather than asserted.

    Args:
        cheap_paired: ``(k,)`` cheap readings at the confirmed points.
        exp_paired: ``(k,)`` expensive readings at those same points.
        cheap_all: ``(n,)`` the cheap readings to map.
        yvar_exp: ``(k,)`` plug-in variance of each expensive reading.
        sigma_add: the assay's additive noise floor.
    """
    cp = np.asarray(cheap_paired, dtype=float).ravel()
    ep = np.asarray(exp_paired, dtype=float).ravel()
    ca = np.asarray(cheap_all, dtype=float).ravel()
    if cp.size < 3:
        raise ValueError(f"need at least 3 paired points to recalibrate; got {cp.size}")
    if cp.shape != ep.shape:
        raise ValueError(f"paired arrays disagree: {cp.shape} vs {ep.shape}")

    var_c = float(np.var(cp))
    if var_c <= 0.0:            # a degenerate cheap tier carries no information
        beta, alpha = 0.0, float(ep.mean())
    else:
        beta = float(np.cov(cp, ep, bias=True)[0, 1] / var_c)
        alpha = float(ep.mean() - beta * cp.mean())
    pseudo = alpha + beta * ca
    resid = ep - (alpha + beta * cp)
    dof = max(cp.size - 2, 1)
    resid_var = float(resid @ resid) / dof
    return Recalibration(pseudo=pseudo,
                         variance=max(resid_var, float(sigma_add) ** 2),
                         slope=beta, intercept=alpha, resid_var=resid_var,
                         mean_yvar=float(np.mean(yvar_exp)))
