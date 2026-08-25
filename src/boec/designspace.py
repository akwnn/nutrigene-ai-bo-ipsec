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

__all__ = ["NEIGHBOURS_PER_AXIS", "POSTERIOR_CHUNK", "brier_and_auc", "certified_mask",
           "certified_volume_curve", "component_report", "connected_components",
           "false_inclusion_rate", "gp_adapter", "grid_neighbours", "inscribed_box",
           "inscribed_box_from_mask", "iou", "predictive_probability_map",
           "probability_map", "tau_max", "tau_max_exact", "tau_quantile"]

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


def tau_quantile(truth: Tensor, p: float) -> float:
    """The threshold whose TRUE superlevel set covers fraction ``p`` of ``truth``.

    Registered fix for the family-agnostic-grid defect in :func:`tau_max` /
    ``tau_frac``: a fixed *fraction of the max* is not the same question on every
    landscape (ackley's true prevalence at ``tau_frac=0.60`` is 0.0000; rosenbrock's
    is 0.9560 -- FINDINGS-SPADE.md sec 5, ``docs/COVERAGE-MATRIX.md`` sec B1). This
    instead asks for a fixed *fraction of the box*, which is comparable by
    construction: ``P(truth >= tau_quantile(truth, p)) == p`` (up to the grid's
    discretisation), on every family. ``docs/SPADE-TAU-QUANTILE-SPEC.md`` registers
    ``p in {0.30, 0.10, 0.03, 0.01}`` as the replacement for the four ``tau_frac``
    values -- COVERAGE-MATRIX's own recommended repair, adopted verbatim.
    """
    if not (0.0 < p < 1.0):
        raise ValueError(f"p must be in (0, 1), got {p}")
    return float(torch.quantile(truth.reshape(-1).double(), 1.0 - p))


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


# ---------------------------------------------------------------------------
# CONNECTED COMPONENTS OF THE CERTIFIED SET
# ---------------------------------------------------------------------------
#
# WHY THIS IS NOT A WORKAROUND
# ----------------------------
# A multimodal process genuinely has several acceptable operating windows, and a batch
# record can name more than one. The single-box metric therefore **structurally penalises
# a method for finding more than one good region** -- which is precisely what spread
# designs are better at than clustered ones, and precisely the comparison this repository
# exists to make. `inscribed_box_from_mask` fits ONE box to the whole mask, so on a
# disconnected `D_gamma` its volume is bounded by the largest component and the rest of
# the certified space is invisible.
#
# The single-box number is reported **alongside**, always, so the committed comparison
# stays intact and the difference between the two is a measurement rather than a revision.
#
# WHY A NEIGHBOURHOOD GRAPH AND NOT `scipy.ndimage.label`
# ------------------------------------------------------
# The evaluation grid is a **scattered Sobol set**, not a lattice. `ndimage.label` needs
# an array whose axes are the coordinates; there is no such array here and constructing
# one would mean binning 20,000 quasi-random points onto a raster, which invents a
# resolution parameter and loses points to collisions. Connectivity is instead defined by
# a k-nearest-neighbour graph **on the full grid**, of which the mask selects an induced
# subgraph -- the exact analogue of a lattice, where connectivity is a property of the
# lattice and the mask selects a subgraph of it.
#
# **The graph must be built on the full grid, not on the masked points.** A graph built on
# the masked points alone joins each point to its k nearest *survivors*, however far away
# they are, so every mask with more than k points comes back as one component and the
# statistic is vacuous.

#: Neighbours per axis. ``k = 2*d`` is face connectivity -- a point on a regular lattice
#: has exactly ``2d`` face neighbours, and face connectivity is `scipy.ndimage.label`'s
#: default structure. Not a tuned constant: it is the lattice's own coordination number,
#: so the definition carries over to the scattered grid without acquiring a scale.
NEIGHBOURS_PER_AXIS = 2


def grid_neighbours(X_grid: Tensor, k: int | None = None,
                    chunk: int = POSTERIOR_CHUNK) -> Tensor:
    """``(n, k)`` indices of each grid point's ``k`` nearest neighbours, **chunked**.

    Chunked for the same reason :func:`gp_adapter` is: the full pairwise distance matrix
    at ``n = 20,000`` is 3.2 GB of doubles, the same trap that produced Q54's memory leak.
    Only the ``k`` smallest entries of each row are ever used, so the rows are reduced as
    they are produced.

    Euclidean, because the ARD lengthscales are not in scope here -- this is the geometry
    of the *grid*, which is the same for every arm and every campaign, and making it
    model-dependent would let the component count of one arm's certified set be decided by
    another arm's fitted hyperparameters.

    Args:
        k: neighbours per point. Defaults to ``NEIGHBOURS_PER_AXIS * d``.
    """
    n, d = X_grid.shape
    k = int(NEIGHBOURS_PER_AXIS * d) if k is None else int(k)
    k = max(1, min(k, n - 1))
    out = torch.empty((n, k), dtype=torch.long)
    Xd = X_grid.double()
    for start in range(0, n, chunk):
        block = Xd[start:start + chunk]
        dist = torch.cdist(block, Xd)
        # Exclude self, which is always the nearest at distance 0.
        rows = torch.arange(block.shape[0])
        dist[rows, rows + start] = float("inf")
        out[start:start + chunk] = torch.topk(dist, k, dim=1, largest=False).indices
    return out


def connected_components(mask: Tensor, X_grid: Tensor, k: int | None = None,
                         neighbours: Tensor | None = None) -> tuple[Tensor, int]:
    """Label the connected components of ``mask``. ``(labels (n,) int64, n_components)``.

    ``labels`` is ``0`` outside the mask and ``1..n_components`` inside it, **numbered
    largest component first**. The numbering is by size and not by grid order, because a
    per-component table whose row 1 meant a different region in every campaign could not
    be compared across campaigns at all. Ties in size are broken by first grid index, so
    the labelling is deterministic.

    Connectivity is the ``k``-nearest-neighbour graph of :func:`grid_neighbours`,
    symmetrised: ``i`` and ``j`` are adjacent if either is among the other's ``k`` nearest.
    Symmetrised rather than mutual because a point on the edge of a component is
    systematically *not* in its neighbours' nearest lists while they are in its, and a
    mutual graph would shave those edges off and split single regions.

    **Component count is resolution-dependent, and that is not a defect to be tuned out.**
    A region sparser than the grid that is meant to resolve it is not one region at that
    grid. Measured on a 4,096-point Sobol grid in 4D: a Chebyshev ball holding 15 points
    has a within-ball median nearest-neighbour distance of 0.1131 against the grid's own
    0.0932, and comes back as several components -- correctly. Version C section 3.2
    offers this count as a regime-detector statistic, so **any threshold fitted on it must
    be fitted at the grid the detector will run on**, or the detector is reading its own
    resolution rather than the landscape.

    **The one place this can disagree with lattice face connectivity.** At the boundary of
    the box a point has fewer than ``2d`` face neighbours, so its ``2d`` nearest include a
    diagonal, and two regions separated by a single lattice cell along the boundary can
    therefore be joined. Across a two-cell gap the two definitions cannot disagree.
    ``tests/test_designspace.py`` gates against ``scipy.ndimage.label`` in that regime and
    says so.

    Args:
        neighbours: a precomputed :func:`grid_neighbours` result. The graph depends only on
            the grid, so a caller sweeping many ``(gamma, tau)`` cells on one grid should
            build it once -- it is by far the most expensive part of this call.
    """
    n = int(mask.shape[0])
    if not bool(mask.any()):
        return torch.zeros(n, dtype=torch.long), 0

    nbr = grid_neighbours(X_grid, k=k) if neighbours is None else neighbours

    # Union-find with path halving and union by size. Only masked points are ever united,
    # so the induced subgraph is what gets labelled.
    parent = list(range(n))
    size = [1] * n

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]

    idx = torch.nonzero(mask.reshape(-1)).reshape(-1)
    inside = mask.reshape(-1)
    # Symmetrised: iterating every masked point's own neighbour list and uniting whenever
    # the neighbour is also masked covers both directions of the "either is among the
    # other's k nearest" relation, because the union is symmetric.
    for i in idx.tolist():
        for j in nbr[i].tolist():
            if inside[j]:
                union(i, j)

    roots: dict[int, list[int]] = {}
    for i in idx.tolist():
        roots.setdefault(find(i), []).append(i)

    # Largest first; ties broken by first grid index, so the order is total and stable.
    ordered = sorted(roots.values(), key=lambda m: (-len(m), m[0]))
    labels = torch.zeros(n, dtype=torch.long)
    for label, members in enumerate(ordered, start=1):
        labels[torch.tensor(members, dtype=torch.long)] = label
    return labels, len(ordered)


def component_report(mask: Tensor, X_grid: Tensor, truth: Tensor, tau: float,
                     k: int | None = None, neighbours: Tensor | None = None,
                     n_steps: int = 20, active: Tensor | None = None,
                     seed_score: Tensor | None = None) -> list[dict]:
    """One row per connected component of ``mask``, largest first.

    Per component: ``vol``, ``box_vol`` and its per-axis ranges, ``fi``, the type I / type
    II / symmetric-difference error volumes, and ``empirical_containment``.

    **The symmetric difference, not type I alone.** Type I error volume read by itself
    ranks a method that certifies nothing in first place -- this repository has already
    been caught by that once -- so the per-component number is the same symmetric
    difference :func:`boec.calibration.error_volumes` reports, computed against the
    component's own certified volume.

    **``box_vol_all_components`` is on every row**, so the committed single-box number
    travels with the decomposition and the difference between the two is visible rather
    than inferred. That is the whole point of section 4: it must not silently replace the
    number the committed comparison is made on.

    ``empirical_containment`` is all-or-nothing per component, the convention
    :func:`boec.vorobev.empirical_containment` holds -- against one realisation of the
    truth a set is either wholly inside it or it is not.

    Args:
        truth: ``(n,)`` noiseless values on the same grid. Requires oracle access, so this
            is a scoring function and never part of a method's own decision path.
    """
    from boec.calibration import error_volumes

    labels, n_comp = connected_components(mask, X_grid, k=k, neighbours=neighbours)
    t = truth.reshape(-1)
    true_set = t >= tau
    prevalence = float(true_set.double().mean())
    _, whole_box = inscribed_box_from_mask(X_grid, mask, n_steps=n_steps, active=active,
                                           seed_score=seed_score)

    rows: list[dict] = []
    for c in range(1, n_comp + 1):
        part = labels == c
        box, box_vol = inscribed_box_from_mask(X_grid, part, n_steps=n_steps,
                                               active=active, seed_score=seed_score)
        vol = float(part.double().mean())
        fi = false_inclusion_rate(part, truth, tau)
        # `error_volumes` is defined exactly where `fi` is nan -- an empty region makes no
        # type I error -- but a component is non-empty by construction, so `fi` is real.
        ev = error_volumes(vol, fi, prevalence)
        rows.append({
            "component": c,
            "n_points": int(part.sum()),
            "vol": vol,
            "box_vol": box_vol,
            "box_lower": [float(v) for v in box[0]],
            "box_upper": [float(v) for v in box[1]],
            "box_vol_all_components": whole_box,
            "n_components": n_comp,
            "fi": fi,
            "iou": iou(part, truth, tau),
            "true_frac_above_tau": prevalence,
            "empirical_containment": bool(t[part].ge(tau).all()),
            **ev,
        })
    return rows


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

