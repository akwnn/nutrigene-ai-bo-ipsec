"""The design-space deliverables: a probability map, a certified region, and a box.

------------------------------------------------------------------------------
THE PRIMARY OBJECT IS PETERSON'S D_gamma, NOT AN LCB ON THE LATENT MEAN
------------------------------------------------------------------------------

    D_gamma = {x : P(Y >= tau | x, data) >= gamma}

with ``Y`` a **future observation** (Peterson 2008; Peterson & Lief 2010). It therefore
carries ``sigma^2`` as well as the estimation variance ``s^2``. Overlapping-mean and
mean-LCB regions are the thing that literature exists to replace: they are too large,
because they certify a statement about the *mean response* when the batch record needs a
statement about *the next batch*.

E3 measured this repo's latent 95% interval at **0.7644** coverage while the predictive
interval recovers to ~0.90-0.92, and wrote: *"the interval a lab would actually use is
roughly trustworthy; the model's belief about the underlying smooth response is not."*
Under a point-optimum deliverable that is a footnote. Under a certificate it inverts --
the broken interval is precisely the one you would certify with. Both maps are therefore
computed and **the gap between them is a reported result**.

------------------------------------------------------------------------------
WHY THE ASSURANCE LEVEL IS SWEPT AND tau IS REGISTERED AS A FRACTION
------------------------------------------------------------------------------

Set ``s = 0`` -- infinite data, perfect knowledge. Certifying still requires
``mu - tau >= z*sigma``. This repo's noise is relative (``y = f(1+eps) + eta``), so the
noise SD scales with ``mu`` and the ceiling is closed-form:

    tau_max = mu_max * (1 - z * sigma_rel)          [:func:`tau_max`]

At ``sigma_rel = 0.25, gamma = 0.95`` that is **0.589 at any budget, forever**. So a
grid of absolute ``tau`` above ~0.59 certifies nothing for any arm and returns a table of
zeros. An earlier draft of the K6 registration carried ``{0.70, 0.80, 0.85, 0.90}`` and
would have done exactly that. ``tau`` is registered as a fraction of ``tau_max``.

The gamma sweep is not a robustness check. It is the only thing keeping the object
non-empty, and that fact is itself the finding.

------------------------------------------------------------------------------
EMPTY IS NOT ZERO
------------------------------------------------------------------------------

Measured neighbour density for a 48-point design in 6D at the fitted lengthscale 0.42 is
**0.49 points within one lengthscale**, so ``s(x)`` sits near the prior SD and a certified
region can be genuinely empty. Every function here distinguishes *empty* from *small*:
:func:`false_inclusion_rate` and :func:`iou` return ``nan`` rather than a number that
would average into a mean and read as "safe".
"""

from __future__ import annotations

import torch
from torch import Tensor
from torch.distributions import Normal

__all__ = ["POSTERIOR_CHUNK", "brier_and_auc", "certified_mask", "certified_volume_curve",
           "false_inclusion_rate", "gp_adapter", "inscribed_box",
           "inscribed_box_from_mask", "iou", "predictive_probability_map",
           "error_volumes", "probability_map", "tau_max", "tau_max_exact"]

_STD_NORMAL = Normal(0.0, 1.0)


def _z_for(gamma: float) -> float:
    """The one-sided normal multiplier for an assurance level."""
    return float(_STD_NORMAL.icdf(torch.tensor(float(gamma), dtype=torch.double)))


def tau_max(gamma: float, sigma_rel: float, mu_max: float = 1.0) -> float:
    """The highest ``tau`` certifiable at assurance ``gamma``, **at any budget**.

    ``mu_max * (1 - z * sigma_rel)``. Derived with ``s = 0``, so no design, no model and
    no number of wells can beat it -- ``D_gamma`` is floored by *process* noise, not by
    estimation noise.
    """
    return round(mu_max * (1.0 - _z_for(gamma) * sigma_rel), 10)


#: Grid rows per ``posterior`` call. See :func:`gp_adapter` for why this is not optional.
POSTERIOR_CHUNK = 2048


def gp_adapter(model, chunk: int = POSTERIOR_CHUNK):
    """Adapt a BoTorch model to the ``posterior_mean_and_sd`` protocol, **chunked**.

    The chunking is a correctness-of-runtime issue, not a micro-optimisation.
    ``model.posterior(X)`` builds the **joint** covariance over all of ``X``, so it is
    quadratic in grid size while only the per-point marginals are ever used here.
    Measured on this repo's d=6 GP:

        N =  2,000  ->   0.06 s
        N = 20,000  -> 100.60 s

    A 10x larger grid costs ~1700x more time, and 20,000 doubles is a 3.2 GB dense
    matrix -- the same class of trap that produced Q54's memory leak. Chunking at 2,048
    turns the 20,000-point grid into ~0.6 s.
    """

    class _Adapted:
        def posterior_mean_and_sd(self, X: Tensor) -> tuple[Tensor, Tensor]:
            means, sds = [], []
            with torch.no_grad():
                for start in range(0, X.shape[0], chunk):
                    post = model.posterior(X[start:start + chunk])
                    means.append(post.mean.reshape(-1).double())
                    sds.append(post.variance.reshape(-1).clamp_min(0).sqrt().double())
            return torch.cat(means), torch.cat(sds)

    return _Adapted()


def probability_map(model, X_grid: Tensor, tau: float) -> Tensor:
    """``P(f(x) >= tau)`` under the Gaussian **latent** posterior. Shape ``(n,)``.

    **SECONDARY.** :func:`predictive_probability_map` is the primary object. This is
    retained because E3 showed the latent interval is the anti-conservative one, so the
    gap between the two maps is a result in its own right.
    """
    mean, sd = model.posterior_mean_and_sd(X_grid)
    return _STD_NORMAL.cdf((mean - tau) / sd.clamp_min(1e-12))


def predictive_probability_map(model, X_grid: Tensor, tau: float,
                               sigma: Tensor | float) -> Tensor:
    """``P(Y >= tau | x)`` under the posterior **predictive** -- Peterson's ``D_gamma``.

    Args:
        sigma: observation SD **at each grid point**. This repo's noise is relative, so
            pass ``sigma_rel * mean``; a scalar silently answers a homoscedastic question
            the campaigns never asked.
    """
    mean, sd = model.posterior_mean_and_sd(X_grid)
    sig = torch.as_tensor(sigma, dtype=sd.dtype)
    total = (sd ** 2 + sig ** 2).clamp_min(1e-24).sqrt()
    return _STD_NORMAL.cdf((mean - tau) / total)


def certified_mask(model, X_grid: Tensor, tau: float, z: float) -> Tensor:
    """``(n,)`` bool: grid points whose lower confidence bound on the mean clears ``tau``."""
    mean, sd = model.posterior_mean_and_sd(X_grid)
    return (mean - z * sd) >= tau


def certified_volume_curve(model, X_grid: Tensor, tau: float,
                           z_values) -> dict[float, float]:
    """Certified grid fraction per confidence multiplier. **Always defined.**

    Reported as a curve rather than a single 95% number, because at measured spread-design
    neighbour density the fixed-95% volume is plausibly zero for every arm, and a table of
    zeros is degenerate rather than informative.
    """
    return {float(z): float(certified_mask(model, X_grid, tau, z).double().mean())
            for z in z_values}


def false_inclusion_rate(mask: Tensor, truth: Tensor, tau: float) -> float:
    """Of the points a region certifies, the fraction genuinely below ``tau``.

    The safety number. Returns ``nan`` for an empty region -- ``0.0`` would read as
    perfectly safe when the honest answer is that nothing was claimed.
    """
    if int(mask.sum()) == 0:
        return float("nan")
    return float((truth.reshape(-1)[mask] < tau).double().mean())


def iou(mask: Tensor, truth: Tensor, tau: float) -> float:
    """Intersection-over-union against the true superlevel set. ``nan`` if both empty."""
    true_set = truth.reshape(-1) >= tau
    union = int((mask | true_set).sum())
    if union == 0:
        return float("nan")
    return float(int((mask & true_set).sum()) / union)


def brier_and_auc(p: Tensor, truth: Tensor, tau: float) -> tuple[float, float]:
    """Brier score (lower better) and AUC (higher better) against ``1{f >= tau}``.

    AUC is ``nan`` when one class is absent. ``0.5`` would read as "no skill" when the
    honest answer is "undefined", and it would average into a mean as if it were data.
    """
    label = (truth.reshape(-1) >= tau).double()
    brier = float(((p.reshape(-1) - label) ** 2).mean())
    n_pos, n_neg = int(label.sum()), int((1 - label).sum())
    if n_pos == 0 or n_neg == 0:
        return brier, float("nan")
    order = torch.argsort(p.reshape(-1))
    ranks = torch.empty(p.numel(), dtype=torch.double)
    ranks[order] = torch.arange(1, p.numel() + 1, dtype=torch.double)
    auc = float((ranks[label == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
    return brier, auc


def inscribed_box(model, X_grid: Tensor, tau: float, z: float, n_steps: int = 20,
                  active: Tensor | None = None) -> tuple[Tensor, float]:
    """Largest axis-aligned box with ``LCB >= tau`` throughout, by greedy expansion.

    Args:
        active: ``(d,)`` bool, which axes may expand. **Amendment B3**: an axis with no
            design variation is not certifiable -- you cannot certify a factor you never
            varied -- so it is pinned to zero width and the NOR is reported in the active
            subspace only. Default: all axes active.

    Returns:
        ``((2, d) lower/upper, volume)``. Volume over the **active** axes. An empty
        certified region returns a degenerate box and ``0.0``; callers must distinguish
        that from a genuinely small box, which is what
        :func:`certified_volume_curve` is for.
    """
    mean, sd = model.posterior_mean_and_sd(X_grid)
    return inscribed_box_from_mask(X_grid, (mean - z * sd) >= tau,
                                   n_steps=n_steps, active=active,
                                   seed_score=mean - z * sd)


def inscribed_box_from_mask(X_grid: Tensor, mask: Tensor, n_steps: int = 20,
                            active: Tensor | None = None,
                            seed_score: Tensor | None = None) -> tuple[Tensor, float]:
    """Largest axis-aligned box lying entirely inside ``mask``, by greedy expansion.

    Takes the certified set as a **boolean mask** rather than recomputing an LCB, so the
    same routine serves Peterson's ``D_gamma`` and the mean-LCB region. That matters:
    the primary object is ``D_gamma``, and a box routine that could only inscribe into an
    LCB region would quietly hold the secondary object as the deliverable.

    Args:
        seed_score: what to maximise when choosing the starting point. Defaults to the
            mask itself, which picks an arbitrary certified point; pass a continuous
            score (an LCB, or the predictive probability) for a better seed.
    """
    d = X_grid.shape[1]
    if active is None:
        active = torch.ones(d, dtype=torch.bool)
    lcb = mask.double() if seed_score is None else seed_score

    if not bool(mask.any()):
        centre = torch.full((d,), 0.5, dtype=torch.double)
        return torch.stack([centre, centre]), 0.0

    seed = X_grid[int(torch.argmax(torch.where(mask, lcb, lcb.min() - 1)))].double()
    lo, hi = seed.clone(), seed.clone()
    step = 1.0 / n_steps

    moved = True
    while moved:
        moved = False
        for j in range(d):
            if not bool(active[j]):
                continue
            for bound, sign in ((hi, 1.0), (lo, -1.0)):
                proposed = float(min(max(bound[j] + sign * step, 0.0), 1.0))
                if proposed == float(bound[j]):
                    continue
                new_lo = lo.clone()
                new_hi = hi.clone()
                (new_hi if sign > 0 else new_lo)[j] = proposed
                inside = ((X_grid >= new_lo) & (X_grid <= new_hi)).all(dim=1)
                if bool(inside.any()) and bool(mask[inside].all()):
                    bound[j] = proposed
                    moved = True

    widths = (hi - lo)[active]
    return torch.stack([lo, hi]), float(torch.prod(widths)) if widths.numel() else 0.0


def tau_max_exact(gamma: float, sigma_rel: float, sigma_add: float,
                  mu_max: float = 1.0) -> float:
    """:func:`tau_max` with the additive noise term it drops. **Sensitivity only.**

    ``mu_max - z * sqrt((sigma_rel*mu_max)**2 + sigma_add**2)``. The observation model is
    ``y = f*(1 + eps) + eta`` with ``eta ~ N(0, sigma_add**2)``
    (``boec.torch_oracle``:135-137, 239-241), so the predictive SD at ``mu_max`` is the
    quadrature sum, not ``sigma_rel*mu_max``. At the repo default ``sigma_add = 0.01`` and
    ``gamma = 0.95`` :func:`tau_max` is optimistic by **3.288e-04** at ``sigma_rel = 0.25``
    and **8.204e-04** at ``sigma_rel = 0.10`` -- a ratio of 2.49, because ``sigma_add`` is
    4% of ``sigma_rel`` at one and 10% at the other.

    **This is not a fix and nothing in the registered grid uses it.** P3-B2
    (``docs/OPEN-QUESTIONS.md``, commit 5c44e6a) decides that :func:`tau_max` is *not*
    changed: correcting the ``sigma_rel = 0.10`` cells while the committed
    ``sigma_rel = 0.25`` cells keep the old definition would confound the sigma axis with
    a definition change, which is a far worse defect than 8e-4. This function exists so
    that the size of the omission can be **measured** on the cell where it is largest
    (``results/p3-taumax-sensitivity.json``) rather than asserted.
    """
    z = _z_for(gamma)
    total = ((sigma_rel * mu_max) ** 2 + sigma_add ** 2) ** 0.5
    return round(mu_max - z * total, 10)


def error_volumes(vol: float, fi: float, prevalence: float) -> dict[str, float]:
    """Expected type I / type II error volumes. **Amendment F2a**, the PRIMARY metric.

    Azzimonti & Ginsbourger (2018) Table 1 -- what the excursion-set community actually
    reports, against this project's AUC, which is invariant to monotone transformation and
    therefore scores *ranking* and never *calibration*. A design space is a calibrated
    absolute statement, so the invariance is disqualifying rather than convenient: mean
    ``grid_r2`` is negative for all eight arms -- the posterior mean is a worse point
    predictor than the constant grid mean -- and **AUC cannot see that at all**.

        type_I_vol  = vol * fi                       |D_est \\ D_true| / |grid|
        intersect   = vol * (1 - fi)
        type_II_vol = prevalence - intersect         |D_true \\ D_est| / |grid|

    Args:
        vol: ``vol_pred`` or ``vol_latent`` -- the certified fraction of the grid.
        fi: the matching ``fi_*`` false-inclusion rate. May be ``nan``; see below.
        prevalence: ``true_frac_above_tau``. Amendment F / Erratum 3 make this mandatory
            on every row precisely so this call is always possible -- a containment number
            read without its prevalence **inverts**, since 0.99 where the true set covers
            99.9% of the box is vacuous and 0.94 where it covers 0.29% is strong.

    **Defined exactly where ``fi`` and ``iou`` are not, which is the common case rather
    than the corner.** An empty ``D_est`` certifies nothing, so it commits no type I error
    and its type II error is the whole true set; ``fi`` is 0/0 there and ``iou`` is 0/0,
    but both volumes are exact. 54%-69% of predictive regions are empty at some committed
    cells, and Erratum 3 shows AUC degrading at *both* ends of the gamma ladder -- the
    negative class is ~17 grid points of 20,000 at gamma=0.99/tau_frac=0.60 and the
    positive class is ~59 at gamma=0.50/tau_frac=0.95. These volumes hold across all of it.

    ``implied_iou`` is carried **only** so the arithmetic can be gated against the
    committed ``iou_pred`` column -- it reproduces it to a worst ``|delta|`` of 2.220e-16
    over 2,553 rows. It is not a new estimand and nothing should rank on it.
    """
    if vol == 0.0:
        type_i, inter = 0.0, 0.0
    else:
        type_i, inter = vol * fi, vol * (1.0 - fi)
    type_ii = prevalence - inter
    union = vol + prevalence - inter
    return {"type_I_vol": type_i, "intersect": inter, "type_II_vol": type_ii,
            "total_error_vol": type_i + type_ii,
            "implied_iou": inter / union if union > 0 else float("nan")}
