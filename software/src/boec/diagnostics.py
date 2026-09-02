"""Calibration diagnostics for Experiment 3.

OWNERSHIP: Person A. Phase 1 only, but the ideas carry forward.

------------------------------------------------------------------------------
WHAT THIS FILE ANSWERS
------------------------------------------------------------------------------

Not "is the model's guess good?" but "**when the model says it is confident,
should you believe it?**" A model that is usually right but wildly overconfident
on the rare occasions it is wrong is far more dangerous in a lab than one that
is vaguer and honest about it, because the confident-and-wrong case is the one
that gets turned into an experiment.

Four things get measured:

* **Coverage** — of the recipes we said would land in a range, how many did?
  If the model claims 95% and delivers 70%, it is overconfident.
* **Sharpness** — how wide those ranges are. Trivially perfect coverage is
  available to anyone willing to say "somewhere between minus infinity and
  infinity", so coverage is only meaningful reported next to sharpness.
* **PIT** — a finer-grained version of coverage that checks the whole shape of
  the predicted distribution rather than one interval.
* **CRPS** — one number combining accuracy and honesty, so two models can be
  ranked.

------------------------------------------------------------------------------
TWO THINGS THAT WOULD SILENTLY CORRUPT ALL OF IT
------------------------------------------------------------------------------

**Never call `model.posterior(..., observation_noise=True)`.** It substitutes
the average of every training noise value and applies that one flat figure
everywhere, including at recipes nobody has run — which is exactly where E3's
headline number lives. Use `boec.surrogate.predictive`, which caters for this
and for the units mismatch on top of it. Nothing here calls `posterior` directly.

**Bootstrap over instances, never over points.** Points inside one run are
sequential BO proposals: each was chosen *because* of the ones before it, so
they are not exchangeable and resampling them gives an interval that is far too
narrow. :func:`instance_bootstrap` takes one number per landscape and resamples
those. Coverage at nominal 0.95 with n=48 has a standard error near 3.1%, so
95% and 89% are indistinguishable in a single run — error bars are not
decoration here.
"""

from __future__ import annotations

import math

import numpy as np
import torch
from torch import Tensor

__all__ = [
    "coverage",
    "crps_gaussian",
    "instance_bootstrap",
    "pit_values",
    "reported_best_curve",
    "sharpness",
]

_SQRT_PI = math.sqrt(math.pi)


def _std_normal():
    return torch.distributions.Normal(
        torch.tensor(0.0, dtype=torch.double), torch.tensor(1.0, dtype=torch.double)
    )


def coverage(y: Tensor, mean: Tensor, stddev: Tensor, alpha: float = 0.05) -> Tensor:
    """Fraction of outcomes falling inside the central ``1 - alpha`` interval.

    Args:
        y: ``(n, m)`` what actually happened.
        mean: ``(n, m)`` what the model expected.
        stddev: ``(n, m)`` the model's **standard deviation**, not its variance.
            Passing a variance here is the same family of bug as the ``Yvar``
            traps and produces a plausible-looking wrong number rather than an
            error, which is why the test suite checks the two are distinguishable.
        alpha: 0.05 gives a 95% interval.

    Returns:
        Scalar tensor in [0, 1]. Report it next to :func:`sharpness` — coverage
        alone can be made perfect by widening the interval without limit.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    for name, t in (("y", y), ("mean", mean), ("stddev", stddev)):
        if t.ndim != 2:
            raise ValueError(f"{name} must be (n, m), got {tuple(t.shape)}")
    if not (y.shape == mean.shape == stddev.shape):
        raise ValueError(
            f"shape mismatch: y {tuple(y.shape)}, mean {tuple(mean.shape)}, "
            f"stddev {tuple(stddev.shape)}"
        )
    z = _std_normal().icdf(torch.tensor(1.0 - alpha / 2.0, dtype=torch.double))
    half = z * stddev.double()
    inside = (y.double() >= mean.double() - half) & (y.double() <= mean.double() + half)
    return inside.double().mean()


def sharpness(stddev: Tensor) -> Tensor:
    """Mean predictive standard deviation. **Deliberately ignores the outcome.**

    That is the point: sharpness is how confident the model chose to be, which is
    a property of the forecast alone. Coverage without it is unfalsifiable.
    """
    if stddev.ndim != 2:
        raise ValueError(f"stddev must be (n, m), got {tuple(stddev.shape)}")
    return stddev.double().mean()


def pit_values(y: Tensor, mean: Tensor, stddev: Tensor) -> Tensor:
    """Probability integral transform: ``Phi((y - mu) / sigma)``.

    If the predictive distribution is right, these are uniform on [0, 1] — a
    stronger statement than any single coverage number, because it checks the
    whole shape rather than one interval. A U-shaped histogram means
    overconfidence; a peaked one means the opposite.

    Returns:
        ``(n, m)`` in [0, 1].
    """
    if not (y.shape == mean.shape == stddev.shape):
        raise ValueError("y, mean and stddev must have the same shape")
    return _std_normal().cdf((y.double() - mean.double()) / stddev.double())


def crps_gaussian(y: Tensor, mean: Tensor, stddev: Tensor) -> Tensor:
    """Continuous ranked probability score, closed form. **Do not sample this.**

        ``CRPS = sigma * [ z(2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi) ]``,  ``z = (y-mu)/sigma``

    One number combining accuracy and honesty, in the units of the outcome, lower
    being better. It is a *proper* score: a model minimises its expected CRPS by
    reporting the distribution it actually believes, so it cannot be gamed by
    being strategically vague or strategically confident.

    Returns:
        ``(n, m)`` per-point scores. Aggregate at instance level before
        bootstrapping — see :func:`instance_bootstrap`.
    """
    if not (y.shape == mean.shape == stddev.shape):
        raise ValueError("y, mean and stddev must have the same shape")
    sd = stddev.double().clamp_min(1e-300)
    z = (y.double() - mean.double()) / sd
    normal = _std_normal()
    phi = torch.exp(normal.log_prob(z))
    Phi = normal.cdf(z)
    return sd * (z * (2.0 * Phi - 1.0) + 2.0 * phi - 1.0 / _SQRT_PI)


def instance_bootstrap(
    per_instance: np.ndarray | Tensor,
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Mean and percentile interval, resampling **landscapes** with replacement.

    Args:
        per_instance: one number per landscape — already aggregated. Passing
            per-point values here is the invalid analysis this function exists to
            prevent: BO proposals are chosen in light of earlier ones, so they are
            not exchangeable and resampling them understates the uncertainty.
        n_boot: bootstrap replicates.
        alpha: 0.05 gives a 95% interval.
        seed: fixes the resampling.

    Returns:
        ``(mean, lower, upper)``.

    Raises:
        ValueError: on an empty sample, rather than returning ``nan`` and letting
            an empty grid cell look like a result.
    """
    v = np.asarray(
        per_instance.detach().cpu().numpy() if isinstance(per_instance, Tensor)
        else per_instance, dtype=float
    ).ravel()
    if v.size == 0:
        raise ValueError("empty sample — nothing to bootstrap")
    rng = np.random.default_rng(seed)
    draws = v[rng.integers(0, v.size, (n_boot, v.size))].mean(axis=1)
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(v.mean()), float(lo), float(hi)


# ---------------------------------------------------------------------------
# Experiment 2 scoring — what would the practitioner actually walk away with?
# ---------------------------------------------------------------------------


def reported_best_curve(truth: Tensor, observed: Tensor) -> np.ndarray:
    """Best-so-far as the method would *report* it: pick by observation, score by truth.

    **The distinction this draws is not pedantic; getting it wrong reverses E2.**

    There are two defensible things "simple regret" could mean under noise:

    * *oracle-best* — the best TRUE value among the points visited. This credits a
      method for stumbling onto a good recipe **it had no way to identify**, and the
      credit grows with how many scattered points the method visits. Space-filling
      arms therefore win by construction, and adaptive arms, which concentrate, lose.
    * *reported-best* — the true value of the point the method would actually hand
      you, chosen by the best value it observed. This is what a practitioner walks
      away with, and it is what this function computes.

    E2's first run used oracle-best and the consequences were visible and wrong: the
    static arms became **completely noise-independent** (identical regret at
    sigma_rel 0.25 and 0.10, because neither the design nor the truth depends on the
    noise draw), random and LHS matched qLogEI, and the sequential-DoE arm beat it in
    the primary cell. All three are artefacts of scoring a choice the method never made.

    Args:
        truth: ``(n, 1)`` noiseless value at each visited point, in visit order.
        observed: ``(n, 1)`` what the method saw at each point, in visit order.

    Returns:
        ``(n,)`` the true value of the running observed-argmax.

    Note:
        The curve is **not** monotone, and forcing it to be would smuggle the oracle
        back in: a later point that drew lucky noise can displace a genuinely better
        incumbent, and that mistake is a real cost of working under noise.
    """
    if truth.shape != observed.shape:
        raise ValueError(
            f"truth {tuple(truth.shape)} and observed {tuple(observed.shape)} "
            "must have the same shape"
        )
    t = truth.detach().double().cpu().numpy().ravel()
    o = observed.detach().double().cpu().numpy().ravel()
    # argmax of the observed prefix, resolved to the FIRST occurrence for determinism
    idx = np.array([int(np.argmax(o[: i + 1])) for i in range(len(o))])
    return t[idx]
