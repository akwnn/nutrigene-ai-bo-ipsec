"""Batch level-set estimation: where plate 2 should spend its wells.

Plate 1 builds a map. Plate 2's job is not to confirm the peak -- Q58 measured that
confirming the peak *hurt* the classical arm, 0.0958 -> 0.1437, because its first reading
was already the trustworthy one. Plate 2's job is to resolve the **boundary of the
certified region**, because that boundary is what limits how large a region can be
certified at all.

CRITERION
---------
Bryan's (2005) straddle, ``1.96*sd(x) - |mean(x) - theta|``: high where the model is
uncertain *and* near the threshold. Batched greedily, which is the practical stand-in for
Chevalier et al.'s (Technometrics 2014) closed-form parallel SUR.

**The criterion is not boundary-only, and that is deliberate.** Azzimonti et al.'s own
figures place some optimal SUR points deep in the interior, to secure the classification
of regions a boundary-only rule would leave uncertain. The ``1.96*sd`` term is what allows
that: a far-from-threshold point with large enough uncertainty can outscore a
near-threshold point that is already well determined. Hard-coding "sample the boundary"
would be an approximation to this, not an implementation of it. There is a test asserting
the criterion can leave the boundary.

EXCLUSION: WHAT IT DOES, MEASURED RATHER THAN ASSERTED
-----------------------------------------------------
The straddle surface is smooth and the greedy loop re-scores nothing between picks, so
with no exclusion it re-selects its own argmax every iteration: ``q`` wells at **one
location**, a replicate dressed up as a design. That is not an argument, it is what this
code does at ``exclude=0.0``, and there is a test asserting it. Each pick therefore masks
a Chebyshev ball around itself. The radius is read from the model's own fitted
lengthscale, never hardcoded, because a fixed radius means something different at every
noise level and dimension.

**Amendment E2 claimed this mechanism is inert at d=6. It is not, and the claim's two
numbers are both correct -- it is the reference population that is wrong.** E2 measured
the median minimum pairwise Chebyshev distance among 8 **random** points in 6D at 0.320
and concluded that a radius of ``ell/4`` could never bind. Reproduced here exactly:
0.3219 over 2,000 random batches, binding in 0.15% of them. But ``batch_lse`` does not
draw random points. It takes the greedy argmax of a straddle surface whose high scores
concentrate on one contour, so its batch is about **half** as spread out as a random one.
Measured over the 50 live Version B campaigns -- ``d=6``, ``sigma_rel=0.25``, 40 LHS
plate-1 wells, the runner's own 4,096-point Sobol candidate grid, ``theta=0.75*mu_max``:

    median fitted ARD lengthscale (n=40)   0.5982      (E2 assumed 0.42, the n=48 figure)
    median exclusion radius, ell/4         0.1495      (E2 computed 0.105 from that)
    top-q-by-score batch, min pairwise     0.1572      median; 0.0869 worst
    returned batch, min pairwise           0.1943      median; 0.1035 worst
    campaigns where the radius BINDS       22 / 50     the top-q batch violates it
    wells relocated by the exclusion       0.56 of 8   mean

So ``batch_lse`` is **not** top-q by score: in 44% of campaigns it moves wells the score
alone would have stacked. The radius is **not** raised on the strength of that -- raising a
knob that already fires would be tuning, and it would change the committed ``versionb``
column. The achieved minimum pairwise distance is instead logged per batch by
``software/scripts/run_versionb.py`` (:func:`min_pairwise_chebyshev`), so this never again has to be
settled by argument, and a test asserts both halves of the mechanism: that the returned
batch honours its radius, **and** that the top-q batch would have violated it. The second
half is the alarm. If the operating point ever drifts far enough that the exclusion has
nothing to do, that test fails and this docstring stops being true out loud.

If exclusion empties the candidate pool, this returns **fewer points rather than
duplicates**: silently handing back repeats would spend wells while reporting a batch size
that was never achieved.

TWO CONTOURS, AND ONLY ONE OF THEM IS THE DELIVERABLE
-----------------------------------------------------
:func:`straddle_score` uses the GP's ``sd`` alone. That is Bryan's straddle exactly as
published, and it targets the **latent** contour ``{f = theta}`` -- the boundary of what
the *mean response* does. The registered deliverable is Peterson's **predictive**
``D_gamma = {x : P(Y >= tau | x) >= gamma}``, whose boundary additionally absorbs process
noise. These are not the same set: section 5.7 of the technical report measured 54%-69%
of predictive regions empty against 16%-25% of latent ones at the same thresholds. So a
plate 2 driven by :func:`straddle_score` **spends its eight wells resolving a boundary
that is not the boundary of the deliverable** (Amendment E6).

:func:`straddle_predictive_score` is the variant that targets the deliverable's own
boundary, ``1.96*sqrt(sd^2 + sigma(x)^2) - |mean - theta|``. It is **added, never
substituted**: the committed ``versionb`` column is the published criterion and stays
comparable, and the predictive variant runs as its own arm so the difference between the
two is a measurement rather than a revision.

``sigma`` is an **array**, from :func:`predictive_sigma`. This repo's noise is relative
(``y = f(1 + eps) + eta``), so ``sigma`` scales with the response and a scalar would
silently answer a homoscedastic question the campaigns never asked -- the identical trap
:func:`boec.designspace.predictive_probability_map` documents on its own ``sigma``
argument, and the reason that function refuses to default it.
"""

from __future__ import annotations

import torch
from torch import Tensor

__all__ = ["batch_lse", "exclusion_radius", "min_pairwise_chebyshev", "predictive_sigma",
           "straddle_predictive_score", "straddle_score"]

#: Bryan's (2005) constant. The 1.96 is the 95% normal quantile, not a tuned knob.
STRADDLE_Z = 1.96
#: Fraction of the median fitted lengthscale used as the exclusion radius.
EXCLUSION_FRACTION = 0.25


def straddle_score(mean: Tensor, sd: Tensor, theta: float) -> Tensor:
    """``1.96*sd - |mean - theta|``. High where uncertain AND near the threshold."""
    return STRADDLE_Z * sd - (mean - theta).abs()


def predictive_sigma(mean: Tensor, sigma_rel: float, sigma_add: float) -> Tensor:
    """``sqrt((sigma_rel*mean)^2 + sigma_add^2)`` -- the observation SD **at each point**.

    The same plug-in ``software/scripts/run_versionb.py`` already uses to score against Peterson's
    ``D_gamma``, so a criterion built on it targets the object it will be judged by.
    ``abs`` on the mean, because a standardised posterior goes negative and a signed
    ``sigma_rel*mean`` would cancel against the additive floor instead of adding to it.
    """
    return ((sigma_rel * mean).abs() ** 2 + float(sigma_add) ** 2).clamp_min(1e-24).sqrt()


def straddle_predictive_score(mean: Tensor, sd: Tensor, theta: float,
                              sigma: Tensor) -> Tensor:
    """``1.96*sqrt(sd^2 + sigma^2) - |mean - theta|`` -- the straddle on ``D_gamma``.

    Amendment E6. Identical to :func:`straddle_score` except that the uncertainty term
    carries **process** noise as well as **estimation** noise, which is what makes its
    contour the deliverable's rather than the latent field's.

    Args:
        sigma: ``(n,)`` observation SD per candidate, from :func:`predictive_sigma`. Not
            optional and not a scalar: see the module docstring.
    """
    total = (sd ** 2 + sigma ** 2).clamp_min(1e-24).sqrt()
    return STRADDLE_Z * total - (mean - theta).abs()


def exclusion_radius(model, fallback: float = 0.1) -> float:
    """A quarter of the median fitted ARD lengthscale, read off the live model.

    Read, never hardcoded: a fixed radius means something different at every noise level
    and dimension, and this repo has already documented (D8) what happens when a decision
    rule is anchored on a constant instead of on the object it is about.
    """
    try:
        ls = model.covar_module.base_kernel.lengthscale.detach().reshape(-1)
        return float(ls.median()) * EXCLUSION_FRACTION
    except AttributeError:
        return fallback


def min_pairwise_chebyshev(X: Tensor) -> float:
    """The batch's achieved minimum pairwise Chebyshev separation. ``inf`` below 2 points.

    The diagnostic Amendment E2 asked for. Chebyshev because that is the metric
    :func:`batch_lse` excludes in, so the logged number is directly comparable to the
    radius that produced it -- a Euclidean number would not be, and would have made the
    E2 question harder to settle rather than easier.
    """
    if X.shape[0] < 2:
        return float("inf")
    d = (X[:, None, :] - X[None, :, :]).abs().amax(dim=-1)
    d = d + torch.eye(X.shape[0], dtype=d.dtype) * (float(d.max()) + 1.0)
    return float(d.min())


def batch_lse(model, X_cand: Tensor, theta: float, q: int,
              exclude: float = 0.1, sigma: Tensor | None = None) -> Tensor:
    """``(<=q, d)`` batch of candidates maximising the straddle, greedily, with exclusion.

    Returns fewer than ``q`` points if exclusion empties the pool -- never duplicates.

    Args:
        sigma: ``None`` (default) selects Bryan's published **latent** straddle, which is
            what the committed ``versionb`` column was run with and must keep running
            with. Passing a ``(n,)`` observation SD selects the **predictive** variant of
            Amendment E6. The default is the published criterion on purpose: an arm that
            silently changed its criterion when a keyword appeared elsewhere would break
            the comparison this whole file exists to support.
    """
    mean, sd = model.posterior_mean_and_sd(X_cand)
    score = (straddle_score(mean, sd, theta) if sigma is None
             else straddle_predictive_score(mean, sd, theta, sigma))
    available = torch.ones(X_cand.shape[0], dtype=torch.bool)
    picks: list[Tensor] = []

    for _ in range(q):
        if not bool(available.any()):
            break
        masked = torch.where(available, score, torch.tensor(float("-inf"),
                                                            dtype=score.dtype))
        idx = int(torch.argmax(masked))
        picks.append(X_cand[idx])
        far = (X_cand - X_cand[idx]).abs().max(dim=1).values >= exclude
        available = available & far

    return torch.stack(picks) if picks else X_cand[:0]
