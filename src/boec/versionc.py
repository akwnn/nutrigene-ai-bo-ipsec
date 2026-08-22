"""Version C: local information, and the statistics the regime detector is built from.

------------------------------------------------------------------------------
WHAT THIS MODULE IS FOR
------------------------------------------------------------------------------

Version B wins the design-space map and ties or beats BO on regret at ``sigma_rel = 0.25``,
but sits **10th of 12** at ``sigma_rel = 0.10`` under rule A. Q53 measured one-shot spread
**losing** on hartmann6 by +0.13 to +0.28, every ``p_holm <= 0.0016``. Version C closes the
first gap and **declares** the second rather than pretending to close it.

Two objects live here.

``n_effective`` is the local-information count. It is the input to section 2.2's
allocation rule and the independent variable in section 0's regression, and it is the
reason section 0 is a gate rather than a formality: if regret is governed by
``sigma / sqrt(n_eff)`` then the sigma = 0.10 deficit is an *identification* artefact of
rule A and no trust region is required; if it is not, the allocation rule has no basis and
must be replaced by empirical calibration.

The detector statistics answer a different question -- **not** "how do we beat hartmann6"
but "can the first plate tell us that we are on a landscape where we will lose". Three
things break a spread design on a multimodal landscape and **only one of them is fixable
at 48 wells**: a disconnected ``{f >= tau}`` bounds a single inscribed box by its largest
component (fixable -- see :func:`boec.designspace.component_report`); a stationary GP
cannot serve basins of different widths with one ARD lengthscale (not fixable without
changing the model to fit a benchmark); and 0.378 neighbours per lengthscale split across
four or five basins is nothing anywhere (not fixable -- that is the budget).

BO wins on Hartmann for a real reason: it commits to one basin and resolves it properly,
which is the **correct** thing to do when you cannot afford to resolve all of them. A
detector that fires on that case and responds the same way arrives at BO's strategy by a
different route, and only when the data say to.

------------------------------------------------------------------------------
THE PROTOCOL, AND WHY IT CONSTRAINS THIS FILE
------------------------------------------------------------------------------

Section 3.3 is **freeze then score once**: fit the rule and its threshold on hill, levy and
rosenbrock only; freeze both in ``docs/OPEN-QUESTIONS.md`` and commit; score **once** on
hartmann6 and ackley. Scoring the held-out families more than once is tuning on the
evaluation set, which is the exact failure this project exists to document.

**One protocol hazard, stated rather than managed.** Version C's *performance* on
hartmann6 depends on the detector, and the detector is *scored* on hartmann6. Both are
measured on the same single pass. If the detector misfires that is a Version C result, not
a reason to refit.

So: every function here is a **statistic**, computed from plate 1 with no oracle access.
None of them is a rule, and no threshold appears in this file. The rule is a registration.

------------------------------------------------------------------------------
NO ORACLE ACCESS, AND WHY IT IS ARCHITECTURAL RATHER THAN A CONVENTION
------------------------------------------------------------------------------

A detector that reads the truth is not a detector; it is a label. Every function here takes
a fitted model and a design and returns a number, and none of them accepts a ``truth``
argument -- so a scoring function cannot be wired into the decision path by accident. The
scoring functions that *do* need truth live in
:func:`boec.designspace.component_report`, on the other side of that line.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["additive_refit_residual_ratio", "additive_share",
           "ard_lengthscales", "ard_separation_ratio",
           "conservative_columns", "detector_statistics", "n_effective",
           "plausible_optimum_mask", "split_joint_draws"]


def ard_lengthscales(model) -> Tensor:
    """``(d,)`` fitted ARD lengthscales, read off the live model.

    Read, never hardcoded -- the rule :func:`boec.lse.exclusion_radius` already follows,
    and for the same reason: a fixed width means something different at every noise level
    and dimension, and this repository has already documented (D8) what happens when a
    decision rule is anchored on a constant instead of on the object it is about.

    Raises:
        AttributeError: if the model carries no ARD kernel. Deliberately not caught and
            defaulted: a silent fallback would make ``n_eff`` a statement about a made-up
            width, and every number downstream of it -- section 2.2's well count, section
            0's regression -- would be about that width rather than about the fit.
    """
    return model.covar_module.base_kernel.lengthscale.detach().reshape(-1).double()


def n_effective(X: Tensor, x_hat: Tensor, lengthscales: Tensor) -> int:
    """``1 + |{x_i : ||x_i - x_hat||_ARD <= 1}|`` -- wells informing the argmax.

    The registered formula (section 2.2, step 2), implemented literally.

    **What it means.** Under a posterior-mean terminal rule, regret is governed by how well
    the posterior localises the argmax. For a peak of local curvature ``c``, a posterior
    mean error of size ``s`` displaces the argmax by ``r ~ sqrt(s/c)``, giving regret
    ``~ c*r^2 ~ s``; and ``s ~ sigma / sqrt(n_eff)``. So ``n_eff`` is the denominator of the
    only quantity section 0 predicts, and section 0 exists to test whether that model
    holds at all before section 2.2 is allowed to allocate wells on the strength of it.

    **The ARD metric, not Euclidean.** Distance is measured in units of the model's own
    fitted lengthscale per axis. A Euclidean ball would answer a question about the *box*;
    what the allocation rule needs is a question about the *fit*, because an axis the GP
    has decided is inert should not be able to push a well out of the neighbourhood.

    **The bound is inclusive**, ``<= 1``, as registered. At 0.378 neighbours per
    lengthscale a single point either way is a third of the statistic, so an exclusive
    bound is a different estimator rather than a rounding choice.

    **The ``+1`` is the argmax's own local information**, and it is added unconditionally.
    ``x_hat`` is the argmax of a posterior mean and is generically not a design point, so
    the two terms describe different wells; where a design point does sit exactly on
    ``x_hat`` it is counted twice. That is a property of the registered formula, not of
    this implementation, and special-casing it here would make the shipped number differ
    from the registered one -- which is the failure mode this project logs as "every
    constant in a registration names the population it was measured on".

    Args:
        X: ``(n, d)`` the campaign's own wells.
        x_hat: ``(d,)`` the posterior-mean argmax.
        lengthscales: ``(d,)`` fitted ARD lengthscales, from :func:`ard_lengthscales`.

    Raises:
        ValueError: on a width mismatch between ``X``, ``x_hat`` and ``lengthscales``. A
            broadcast would silently answer a different question.
    """
    Xd = torch.as_tensor(X, dtype=torch.double).reshape(-1, X.shape[-1])
    x = torch.as_tensor(x_hat, dtype=torch.double).reshape(-1)
    ls = torch.as_tensor(lengthscales, dtype=torch.double).reshape(-1)
    d = Xd.shape[1]
    if x.numel() != d or ls.numel() != d:
        raise ValueError(
            f"width mismatch: X has d={d}, x_hat has {x.numel()}, "
            f"lengthscales has {ls.numel()} -- broadcasting these would answer a "
            "different question silently")
    if bool((ls <= 0).any()):
        raise ValueError(f"non-positive lengthscale in {ls.tolist()}")
    dist = ((Xd - x) / ls).pow(2).sum(dim=1).sqrt()
    return 1 + int((dist <= 1.0).sum())


def conservative_columns(draws_sel: Tensor, draws_val: Tensor, truth_eval: Tensor,
                         theta: float, alphas=(0.50, 0.80, 0.95)) -> dict:
    """The conservative-set columns, with the two absences filled and the cross-fit added.

    Sections 1.2 and 1.3, together, because they land on the same rows.

    ------------------------------------------------------------------------------
    SECTION 1.3 -- WHAT WAS MISSING AND WHY IT BLOCKED A METRIC
    ------------------------------------------------------------------------------

    ``versionb.json`` and ``k6b-conservative*.json`` carry ``ce_vol`` but **no
    false-inclusion rate and no prevalence**, and :func:`boec.calibration.error_volumes`
    needs all three. So the primary error-volume metric -- the symmetric difference, which
    superseded the AUC rankings wherever a ranking exists -- has never been computable on
    a *conservative set* at all, only on the predictive and latent maps. That absence has
    blocked it twice. ``true_frac_above_tau`` and ``ce_fi_{alpha}`` are added here, and
    the derived volumes with them.

    **The type I volume is not reported alone.** Read by itself it ranks a method that
    certifies nothing in first place, which this repository has already been caught by
    once; ``ce_total_error_vol_{alpha}`` is the symmetric difference.

    ------------------------------------------------------------------------------
    SECTION 1.2 -- THE CROSS-FIT, BESIDE THE CIRCULAR COLUMN AND NEVER INSTEAD OF IT
    ------------------------------------------------------------------------------

    ``ce_contain_{alpha}`` is circular: :func:`boec.vorobev.conservative_estimate` selects
    on it, so it cannot fall below ``alpha``. It is **kept**, because removing it would
    hide the tautology rather than expose it, and **the difference between it and
    ``ce_split_contain_{alpha}`` is the selection bias** -- which is the quantity section
    1.2 exists to measure.

    ------------------------------------------------------------------------------
    THE TWO HALVES MUST BE DRAWN SEQUENTIALLY, NOT AS ONE BLOCK OF 1,024
    ------------------------------------------------------------------------------

    Measured, not assumed: ``torch.randn(n, 1024)[:, :512]`` is **not**
    ``torch.randn(n, 512)`` from the same seed, because torch fills a tensor in memory
    order. Drawing 1,024 at once would therefore change every committed ``ce_*`` column
    silently. Two sequential ``randn(n, 512)`` calls on one generator leave the first
    block bit-identical to the committed draw and give a genuinely independent second --
    asserted in ``tests/test_versionc.py``. Callers must supply the halves that way; this
    function checks only that they are equal in size, since it cannot see the generator.

    Args:
        draws_sel: ``(n_draws, n)`` the **committed** half. Selection happens here alone.
        draws_val: ``(n_draws, n)`` the held-out half. Scoring happens here alone.
        truth_eval: ``(n,)`` noiseless values on the same evaluation points.

    Raises:
        ValueError: on unequal halves or a truth of the wrong width. Silently re-weighting
            an unequal split would make the reported containment a different estimator.
    """
    from boec.calibration import error_volumes
    from boec.designspace import false_inclusion_rate
    from boec.vorobev import (alpha_star, conservative_estimate, containment_probability,
                              empirical_containment, vorobev_deviation)

    if draws_sel.shape != draws_val.shape:
        raise ValueError(
            f"the two halves must be equal in size, got {tuple(draws_sel.shape)} and "
            f"{tuple(draws_val.shape)} -- re-weighting an unequal split silently changes "
            "the estimator")
    t = torch.as_tensor(truth_eval, dtype=torch.double).reshape(-1)
    if t.numel() != draws_sel.shape[1]:
        raise ValueError(
            f"truth has {t.numel()} points, the draws have {draws_sel.shape[1]}")

    out: dict = {
        # Every committed column is computed on the SELECTION half alone, so it is
        # bit-identical to what the committed 512-draw run produced.
        "alpha_star": alpha_star(draws_sel, theta),
        "vorobev_deviation": vorobev_deviation(draws_sel, theta),
        "true_frac_above_tau": float((t >= theta).double().mean()),
    }
    for a in alphas:
        ce = conservative_estimate(draws_sel, theta, a)
        n_ce = int(ce.sum())
        vol = n_ce / ce.numel()
        out[f"ce_vol_{a}"] = vol
        out[f"ce_empty_{a}"] = n_ce == 0
        out[f"ce_contain_{a}"] = (containment_probability(draws_sel, ce, theta)
                                  if n_ce else float("nan"))
        emp = empirical_containment(ce, t, theta)
        out[f"ce_empirical_{a}"] = float("nan") if emp is None else float(emp)

        # --- section 1.3, added beside them, never in place of them ------------------
        fi = false_inclusion_rate(ce, t, theta)
        out[f"ce_fi_{a}"] = fi
        for k, v in error_volumes(vol, fi, out["true_frac_above_tau"]).items():
            out[f"ce_{k}_{a}"] = v

        # --- section 1.2: the same set, scored where it was not selected -------------
        out[f"ce_split_contain_{a}"] = (containment_probability(draws_val, ce, theta)
                                        if n_ce else float("nan"))
        # NO `ce_split_empirical`. `empirical_containment` scores against the TRUTH, not
        # against draws, so a "split" version of it would be bit-identical to
        # `ce_empirical_{alpha}` -- a duplicate column dressed as new information. The
        # cross-fit repairs the MODEL-INTERNAL number; the empirical one was never
        # circular and needs no repair.
        out[f"ce_selection_bias_{a}"] = (out[f"ce_contain_{a}"]
                                         - out[f"ce_split_contain_{a}"]) if n_ce \
            else float("nan")
    return out


# ---------------------------------------------------------------------------
# SECTION 3.2 -- THE REGIME-DETECTOR STATISTICS
# ---------------------------------------------------------------------------
#
# Every function below is a STATISTIC. None is a rule and no threshold appears in this
# file, because the rule is a registration: fitted on hill, levy and rosenbrock, frozen in
# `docs/OPEN-QUESTIONS.md`, and scored ONCE on hartmann6 and ackley.
#
# ONE DISCREPANCY WITH THE SPECIFICATION, RECORDED RATHER THAN SILENTLY RESOLVED
# ------------------------------------------------------------------------------
# Section 3.2's first bullet reads "number of connected components of
# `{x : LCB(x) >= max LCB}`". That set is satisfied by the argmax alone -- no other point
# can have an LCB above the largest LCB -- so its component count is ALWAYS exactly 1 and
# it cannot serve as a detector. Section 2.3 defines the trust region as
# `{x : UCB(x) >= max LCB}`, the plausible-optimum set, which is the object with a
# meaningful component count and is plainly what was meant. That is what is implemented.


def plausible_optimum_mask(mean: Tensor, sd: Tensor, z: float = 1.96) -> Tensor:
    """``{x : UCB(x) >= max LCB}`` -- the points not yet excluded as the optimum.

    Section 2.3's trust region, and the set section 3.2 counts components of.

    **Never empty.** The argmax of the LCB has ``UCB >= LCB``, so it always qualifies; a
    detector that could be undefined cannot gate a budget.
    """
    m = torch.as_tensor(mean, dtype=torch.double).reshape(-1)
    s = torch.as_tensor(sd, dtype=torch.double).reshape(-1).clamp_min(0.0)
    return (m + z * s) >= float((m - z * s).max())


def ard_separation_ratio(lengthscales: Tensor) -> float:
    """``max(ls) / min(ls)`` -- how far the fit separates inert axes from active ones.

    **A purely prior-driven fit gives exactly 1.0**, so departure from 1.0 is data. That
    is the entire content of the statistic, and it is why the ratio is the reported form
    rather than the raw lengthscales: the raw vector varies with ``d`` and with the noise
    level, and a threshold fitted on it would not transfer between cells.
    """
    ls = torch.as_tensor(lengthscales, dtype=torch.double).reshape(-1)
    if ls.numel() == 0 or bool((ls <= 0).any()):
        raise ValueError(f"lengthscales must be positive and non-empty, got {ls.tolist()}")
    return float(ls.max() / ls.min())


def additive_share(values: Tensor, X: Tensor, n_bins: int = 20) -> float:
    """Fraction of ``var(f)`` carried by the one-dimensional main effects.

    A binned functional-ANOVA estimate: each main effect ``f_j(x_j) = E[f | x_j] - E[f]``
    is estimated by averaging within ``n_bins`` equal-width bins of coordinate ``j``, and
    the statistic is ``var(sum_j f_j) / var(f)``, **clamped to [0, 1]**.

    **Why this contrast is the one the detector wants.** A sum of one-dimensional
    functions puts all of its variance in the main effects and scores ~1. A pure product
    term has no main effects on a centred design and scores ~0. "Smooth and
    coordinate-wise unimodal" -- the property Q53 found separates the families SPADE ties
    on from the ones it loses on -- is close to the first case, and deceptive multimodal
    landscapes are close to the second.

    **Binned rather than exact.** An exact decomposition needs the conditional
    expectations, which for a GP posterior mean are not available in closed form over an
    arbitrary design. The bin count is a resolution parameter and the estimate is biased
    downward when bins are coarse relative to the wiggle, so any threshold fitted on this
    must be fitted at the ``n_bins`` and grid the detector will run at -- the same
    constraint `boec.designspace.connected_components` carries.

    Returns ``0.0`` for a constant field, where the ratio is 0/0: a constant surface has
    no variance to apportion, and ``nan`` would propagate into a mean as if it were data.
    """
    f = torch.as_tensor(values, dtype=torch.double).reshape(-1)
    Xd = torch.as_tensor(X, dtype=torch.double).reshape(f.numel(), -1)
    total = float(f.var(unbiased=False))
    if total <= 0.0:
        return 0.0
    grand = f.mean()
    additive = torch.zeros_like(f)
    for j in range(Xd.shape[1]):
        col = Xd[:, j]
        lo, hi = float(col.min()), float(col.max())
        width = (hi - lo) or 1.0
        idx = (((col - lo) / width) * n_bins).long().clamp(0, n_bins - 1)
        sums = torch.zeros(n_bins, dtype=torch.double).index_add_(0, idx, f)
        counts = torch.zeros(n_bins, dtype=torch.double).index_add_(
            0, idx, torch.ones_like(f))
        means = torch.where(counts > 0, sums / counts.clamp_min(1.0), grand)
        additive = additive + (means[idx] - grand)
    return float(min(max(float(additive.var(unbiased=False)) / total, 0.0), 1.0))


def detector_statistics(model, X: Tensor, bounds: Tensor, grid_n: int = 20_000,
                        grid_seed: int = 0, z: float = 1.96,
                        n_bins: int = 20) -> dict:
    """Every section 3.2 statistic, from plate 1, with **no oracle access**.

    Architectural rather than conventional: this function takes no ``truth`` argument, so
    a scoring function cannot be wired into the detector's decision path by accident.

    Returns a flat dict of statistics -- never a verdict. The rule that turns these into
    UNIMODAL / DECEPTIVE is a registration, frozen before hartmann6 and ackley are scored
    even once, and it deliberately does not live in code that could be edited after the
    scoring run.
    """
    from boec.designspace import connected_components, gp_adapter, grid_neighbours
    from boec.norms import sobol_grid

    d = int(torch.as_tensor(bounds).shape[-1])
    grid = sobol_grid(d, grid_n, seed=grid_seed)
    mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

    plausible = plausible_optimum_mask(mean, sd, z=z)
    neighbours = grid_neighbours(grid)
    _, n_comp = connected_components(plausible, grid, neighbours=neighbours)

    # A local maximum of the posterior mean: no graph neighbour is higher. Restricted to
    # the plausible region, and then required to clear the SECOND-highest UCB -- a peak
    # that cannot beat the runner-up's optimistic bound is not a competing basin, it is
    # the same basin's shoulder.
    #
    # MEASURED: `n_local_maxima` is IDENTICALLY ZERO at the real operating point -- 40
    # wells, d=6, sigma=0.10, the 20,000-point grid -- on both hill and levy. An LCB must
    # exceed the second-highest UCB among peaks, and at 0.49 neighbours per lengthscale
    # the posterior is nowhere near tight enough. A statistic that cannot vary cannot
    # detect anything, so this candidate is NOT VIABLE at this budget and the fitting run
    # must not select it. `n_peaks_raw` -- the same peaks with no confidence bar -- does
    # vary (135 and 149 on those two fits) and is the usable form. Both are returned.
    # tests/test_versionc_detector_run.py pins the zero as an alarm.
    higher = mean[neighbours] > mean.unsqueeze(1)
    is_peak = (~higher.any(dim=1)) & plausible
    ucb = mean + z * sd
    peak_idx = torch.nonzero(is_peak).reshape(-1)
    if peak_idx.numel() >= 2:
        top2 = torch.topk(ucb[peak_idx], 2).values
        bar = float(top2[1])
    else:
        bar = float("-inf")
    lcb = mean - z * sd
    n_local_maxima = int((lcb[peak_idx] >= bar).sum()) if peak_idx.numel() else 0

    ls = ard_lengthscales(model)
    width = (torch.as_tensor(bounds)[1] - torch.as_tensor(bounds)[0]).double().reshape(-1)

    return {
        "n_components_plausible": n_comp,
        "plausible_volume": float(plausible.double().mean()),
        "n_peaks_raw": int(is_peak.sum()),
        "n_local_maxima": n_local_maxima,
        "additive_share": additive_share(mean, grid, n_bins=n_bins),
        "ard_separation_ratio": ard_separation_ratio(ls),
        "lengthscale_over_width": [float(v) for v in (ls / width)],
        "lengthscales": [float(v) for v in ls],
        "n_wells": int(torch.as_tensor(X).shape[0]),
        "grid_n": grid_n, "grid_seed": grid_seed, "z": z, "n_bins": n_bins,
    }


def additive_refit_residual_ratio(X: Tensor, Y: Tensor, Yvar: Tensor,
                                  bounds: Tensor) -> float:
    """Residual variance after an **additive-only** refit, divided by ``sigma_hat^2``.

    Section 3.2's sixth statistic, and the one that asks the question most directly: how
    much of the response does a model with **no interaction terms at all** fail to
    explain, measured in units of the noise it was told about.

    ``~1`` means the additive kernel explained everything except the noise -- the
    coordinate-wise picture is adequate. Large means real interaction structure the
    additive model cannot hold, which is the deceptive case.

    The additive kernel is this repository's own -- ``build_gp(..., kernel_structure=
    "additive")``, a sum of ``d`` one-dimensional Materns -- so this statistic is fitted
    by the same machinery that produced the ``qlogei-add`` arms rather than by a second
    implementation whose disagreements would be untraceable.

    ``sigma_hat^2`` is the **mean of the supplied ``Yvar``**, not a fitted noise level.
    This repository's GP is handed ``train_Yvar`` as known and does not fit noise jointly
    (the SPADE specification's Stage 2 asserted otherwise and was wrong about this repo),
    so the denominator is a quantity the campaign already knows and the ratio does not
    depend on an optimiser's willingness to trade noise against lengthscale.

    In-sample residuals, deliberately: the detector runs on plate 1 with nothing held out,
    so an out-of-sample version would need a split the budget cannot pay for. The number
    is therefore optimistic in absolute terms and is only ever read as a **contrast**
    between landscapes, which is how section 3.3 fits its threshold.
    """
    from boec.surrogate import build_gp

    Xd = torch.as_tensor(X, dtype=torch.double)
    Yd = torch.as_tensor(Y, dtype=torch.double).reshape(-1, 1)
    Vd = torch.as_tensor(Yvar, dtype=torch.double).reshape(-1, 1)
    sigma2 = float(Vd.mean())
    if sigma2 <= 0.0:
        raise ValueError("sigma_hat^2 must be positive to be a denominator")
    model = build_gp(Xd, Yd, Vd, bounds, kernel_structure="additive")
    with torch.no_grad():
        pred = model.posterior(Xd).mean.reshape(-1).double()
    resid = float(((Yd.reshape(-1) - pred) ** 2).mean())
    return resid / sigma2


def split_joint_draws(model, X: Tensor, n_draws: int = 512, seed: int = 0,
                      jitter: float = 1e-8) -> tuple[Tensor, Tensor]:
    """Two blocks of ``n_draws`` joint posterior samples, drawn **sequentially**.

    Returns ``(selection_half, validation_half)``.

    **The first half is bit-identical to
    ``run_k6b_conservative.joint_draws(model, X, seed=seed)``**, and
    ``tests/test_versionc.py`` asserts exactly that. It is the load-bearing property of
    the whole Version C re-score: the cross-fit must change what is *reported* without
    changing what was *selected*, so every committed ``ce_*`` column has to reproduce.

    **Why this function exists rather than two calls to ``joint_draws``.** That function
    builds a **fresh** generator per call, so calling it twice returns the identical
    block -- two copies of one draw, which as a cross-fit is worse than useless because it
    would silently report the circular number as if it were held out.

    **And why not one block of ``2*n_draws``.** Measured: ``torch.randn(n, 1024)[:, :512]``
    is **not** ``torch.randn(n, 512)`` from the same seed, because torch fills a tensor in
    memory order. Drawing both halves at once would move every committed column.

    The covariance construction -- same jitter, same Cholesky, same mean -- is
    ``joint_draws``' arithmetic, reproduced rather than approximated.
    """
    with torch.no_grad():
        post = model.posterior(X)
        cov = post.mvn.covariance_matrix.double()
        cov = cov + jitter * torch.eye(cov.shape[0], dtype=torch.double)
        L = torch.linalg.cholesky(cov)
        mean = post.mean.reshape(-1, 1).double()
        g = torch.Generator().manual_seed(int(seed))
        halves = []
        for _ in range(2):
            z = torch.randn(cov.shape[0], int(n_draws), generator=g, dtype=torch.double)
            halves.append((mean + L @ z).T)
    return halves[0], halves[1]
