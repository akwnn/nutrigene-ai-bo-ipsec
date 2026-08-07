"""Choosing what to run next.

OWNERSHIP: Person B. **Long-lived** — Phases 2 and 3 depend on it.

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

The model tells you what it believes and how unsure it is. This file turns that
into an actual answer to "so what should we try next?"

It has to balance two urges that pull in opposite directions:

  * **Exploit** — try something near the best result so far, to squeeze out a
    bit more.
  * **Explore** — try something the model knows nothing about, because that is
    where a surprise could be hiding.

Do only the first and you polish a local hill and never find the mountain. Do
only the second and you wander forever without refining anything. The method
used here weighs both automatically: it favours points that are *either* likely
to be good *or* genuinely unknown, and most strongly favours points that are
both.

**Two modes, and the second is not optional.**

  * **Free search** — propose any recipe at all, anywhere in the space. This is
    what Phase 1 and Phase 3 need.
  * **Pick from a menu** — propose only from a fixed list. This is what Phase 2
    needs, and it is the reason it is built now rather than later. In Phase 2
    we replay a published study, and the only recipes with real measured
    results are the ~48 the original authors ran. If the model is free to
    invent a new recipe there is nothing to look up and the replay stops dead.

**Also here: the things we have to beat.** Picking at random, and two ways of
spreading points evenly. Without something to compare against there is no
result, only a number.

------------------------------------------------------------------------------
ONE OPEN QUESTION, FLAGGED NOT SILENTLY DECIDED
------------------------------------------------------------------------------

The spec mandates a method (``qLogEI``) that assumes you know the best result
seen so far. But our measurements are deliberately noisy — and the best of 48
noisy measurements is systematically *better-looking* than the best true value,
because the winner is partly whichever one got lucky.

BoTorch ships a variant built for exactly this. Its own documentation says it
exists because the standard version's assumption "would require noiseless
observations". The spec's stated reason for choosing ``qLogEI`` is about
numerical stability, which is a different concern entirely — so the noise
question looks unconsidered rather than decided.

**Both are implemented. The spec's choice is the default.** Changing the
default is a joint decision with Person A, because Experiment 2's fairness
rules are explicit that we must not tune our own method while leaving the
baselines alone. See ``ACQUISITION_CHOICES`` below.

------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import torch
from botorch.acquisition.acquisition import AcquisitionFunction
from botorch.acquisition.logei import (
    qLogExpectedImprovement,
    qLogNoisyExpectedImprovement,
)
from botorch.models import SingleTaskGP
from botorch.optim import optimize_acqf, optimize_acqf_discrete
from scipy.stats import qmc
from torch import Tensor
from torch.quasirandom import SobolEngine

from boec.surrogate import predictive

__all__ = [
    "ACQUISITION_CHOICES",
    "AcqConfig",
    "BEST_F_POLICIES",
    "initial_design",
    "lhs_design",
    "make_acquisition",
    "propose",
    "random_design",
    "sobol_design",
]

AcquisitionKind = Literal["qlogei", "qlognei"]
BestFPolicy = Literal["max_observed", "max_posterior_mean"]

ACQUISITION_CHOICES: dict[str, str] = {
    "qlogei": (
        "Spec default. Assumes the best value so far is known. With noisy "
        "measurements that assumption is optimistic — the observed best is "
        "partly whichever point got lucky."
    ),
    "qlognei": (
        "Built for noisy measurements; needs no assumed best. More faithful to "
        "our observation model, but a deviation from spec and therefore a "
        "JOINT decision with Person A under E2's no-tuning rule."
    ),
}

BEST_F_POLICIES: dict[str, str] = {
    "max_observed": (
        "Spec-literal: the largest number we actually measured. Biased upward "
        "under noise."
    ),
    "max_posterior_mean": (
        "The model's smoothed estimate at the points we ran. Less biased, "
        "still a deviation. Only meaningful with qlogei."
    ),
}


@dataclass(frozen=True)
class AcqConfig:
    """How to choose the next points. Every field is a deliberate choice.

    Attributes:
        kind: which acquisition method. See :data:`ACQUISITION_CHOICES`.
        best_f_policy: only used by ``qlogei``. See :data:`BEST_F_POLICIES`.
        num_restarts: how many places the search starts from. More is safer.
        raw_samples: how many points are screened before the search begins.
        mc_samples: how many draws are used to estimate the expected gain.
        inequality_constraints: combinations that must satisfy a linear rule.
        equality_constraints: combinations pinned to a linear relationship.
        nonlinear_inequality_constraints: anything more complicated.
        fixed_features_list: ingredients held at a fixed value.

    The constraint fields are unused in Phase 1 and threaded through anyway.
    Phase 3 will have protein caps and plate arithmetic, and retrofitting them
    later would change this function's signature everywhere it is called.
    """

    kind: AcquisitionKind = "qlogei"
    best_f_policy: BestFPolicy = "max_observed"
    num_restarts: int = 10
    raw_samples: int = 512
    mc_samples: int = 256
    inequality_constraints: list | None = None
    equality_constraints: list | None = None
    nonlinear_inequality_constraints: list | None = None
    fixed_features_list: list[dict[int, float]] | None = field(default=None)

    def __post_init__(self) -> None:
        if self.kind not in ACQUISITION_CHOICES:
            raise ValueError(
                f"unknown acquisition {self.kind!r}; "
                f"choose from {sorted(ACQUISITION_CHOICES)}"
            )
        if self.best_f_policy not in BEST_F_POLICIES:
            raise ValueError(
                f"unknown best_f policy {self.best_f_policy!r}; "
                f"choose from {sorted(BEST_F_POLICIES)}"
            )


# ---------------------------------------------------------------------------
# Starting points and baselines
# ---------------------------------------------------------------------------

def sobol_design(bounds: Tensor, n: int, *, seed: int = 0) -> Tensor:
    """``n`` points spread evenly through the space, in a structured way.

    Sobol sampling fills a space more evenly than random picking, which tends
    to clump and leave gaps. Used for the opening batch and as a baseline.

    Returns:
        ``(n, d)``.
    """
    _check_bounds(bounds)
    d = bounds.shape[1]
    unit = SobolEngine(dimension=d, scramble=True, seed=seed).draw(n).double()
    return bounds[0].double() + unit * (bounds[1] - bounds[0]).double()


def random_design(bounds: Tensor, n: int, *, seed: int = 0) -> Tensor:
    """``n`` points picked uniformly at random. The simplest baseline."""
    _check_bounds(bounds)
    g = torch.Generator().manual_seed(seed)
    d = bounds.shape[1]
    unit = torch.rand(n, d, generator=g, dtype=torch.double)
    return bounds[0].double() + unit * (bounds[1] - bounds[0]).double()


def lhs_design(bounds: Tensor, n: int, *, seed: int = 0) -> Tensor:
    """``n`` points by Latin hypercube — evenly spread one factor at a time.

    Divides each ingredient's range into ``n`` slices and uses each slice
    exactly once. Good coverage of every single ingredient; weaker than Sobol
    at covering combinations.
    """
    _check_bounds(bounds)
    d = bounds.shape[1]
    unit = torch.from_numpy(qmc.LatinHypercube(d=d, seed=seed).random(n)).double()
    return bounds[0].double() + unit * (bounds[1] - bounds[0]).double()


def initial_design(bounds: Tensor, *, seed: int = 0) -> Tensor:
    """The opening batch, before the model knows anything: ``2d + 2`` points.

    **This must be identical across every method being compared, for a given
    seed.** Comparing methods that started from different opening batches is
    the difference between a significant result and a non-significant one at
    this sample size. There is a test for it.
    """
    _check_bounds(bounds)
    return sobol_design(bounds, 2 * bounds.shape[1] + 2, seed=seed)


# ---------------------------------------------------------------------------
# The acquisition function
# ---------------------------------------------------------------------------

def _best_f(model: SingleTaskGP, train_X: Tensor, train_Y: Tensor, policy: BestFPolicy) -> Tensor:
    if policy == "max_observed":
        return train_Y.max()
    # Smoothed: the model's own estimate at the points we ran. Less inflated by
    # whichever measurement happened to draw a lucky noise value.
    return predictive(model, train_X).mean.max()


def make_acquisition(
    model: SingleTaskGP,
    train_X: Tensor,
    train_Y: Tensor,
    *,
    config: AcqConfig | None = None,
    X_pending: Tensor | None = None,
) -> AcquisitionFunction:
    """Build the scoring function that says how attractive a candidate is.

    Args:
        model: the fitted model.
        train_X: ``(n, d)`` what has been run.
        train_Y: ``(n, 1)`` what came back.
        config: see :class:`AcqConfig`.
        X_pending: ``(k, d)`` recipes already proposed but not yet measured.

            **This matters more than it looks.** Without it, proposing a second
            batch while the first is still in the lab would just re-propose the
            same attractive region — the model has no way to know it is already
            being investigated. Phase 3 has humans and two-week turnarounds, so
            overlapping proposals are the normal case, not an edge case.

    Returns:
        An acquisition function ready to be maximized.
    """
    cfg = config or AcqConfig()
    from botorch.sampling.normal import SobolQMCNormalSampler

    sampler = SobolQMCNormalSampler(sample_shape=torch.Size([cfg.mc_samples]))

    if cfg.kind == "qlognei":
        return qLogNoisyExpectedImprovement(
            model=model,
            X_baseline=train_X.double(),
            sampler=sampler,
            X_pending=X_pending,
            prune_baseline=True,
        )
    return qLogExpectedImprovement(
        model=model,
        best_f=_best_f(model, train_X, train_Y, cfg.best_f_policy),
        sampler=sampler,
        X_pending=X_pending,
    )


# ---------------------------------------------------------------------------
# Proposing
# ---------------------------------------------------------------------------

def propose(
    model: SingleTaskGP,
    bounds: Tensor,
    q: int,
    train_X: Tensor,
    train_Y: Tensor,
    *,
    config: AcqConfig | None = None,
    candidates: Tensor | None = None,
    X_pending: Tensor | None = None,
) -> Tensor:
    """Propose ``q`` recipes to run next.

    Args:
        model: the fitted model.
        bounds: ``(2, d)``. Ignored when ``candidates`` is given.
        q: how many to propose at once.
        train_X: ``(n, d)`` what has been run.
        train_Y: ``(n, 1)`` what came back.
        config: see :class:`AcqConfig`.
        candidates: ``(k, d)`` a fixed menu to choose from. ``None`` means free
            search. **Phase 2 always passes this**, because the only recipes
            with measured results are the ones the original study ran.
        X_pending: ``(j, d)`` proposed but not yet measured.

    Returns:
        ``(q, d)``.

    **On proposing several at once.** The naive approach — asking "what is
    best?" ``q`` times — returns ``q`` near-identical recipes clustered on the
    same spot, wasting all but one. Both paths here avoid that. Free search
    optimizes the batch as a whole. The menu path picks one, tells the scoring
    function it is now spoken for, and only then picks the next; each choice
    therefore accounts for the ones already made.
    """
    if q < 1:
        raise ValueError(f"q must be >= 1, got {q}")
    cfg = config or AcqConfig()
    acqf = make_acquisition(model, train_X, train_Y, config=cfg, X_pending=X_pending)

    if candidates is not None:
        if candidates.ndim != 2:
            raise ValueError(
                f"candidates must be (k, d), got {tuple(candidates.shape)}"
            )
        if candidates.shape[0] < q:
            raise ValueError(
                f"asked for q={q} but the menu has only {candidates.shape[0]} options"
            )
        picked, _ = optimize_acqf_discrete(
            acq_function=acqf,
            q=q,
            choices=candidates.double(),
            unique=True,
            inequality_constraints=cfg.inequality_constraints,
        )
        return picked

    _check_bounds(bounds)

    # Only pass constraint kwargs that are actually set. Passing
    # `fixed_features_list=None` is NOT equivalent to omitting it — it routes
    # optimize_acqf down a different internal path that then rejects the
    # keyword. An easy thing to get wrong, and it fails at call time rather
    # than at config time.
    extra: dict = {}
    if cfg.inequality_constraints is not None:
        extra["inequality_constraints"] = cfg.inequality_constraints
    if cfg.equality_constraints is not None:
        extra["equality_constraints"] = cfg.equality_constraints
    if cfg.nonlinear_inequality_constraints is not None:
        extra["nonlinear_inequality_constraints"] = cfg.nonlinear_inequality_constraints
    if cfg.fixed_features_list is not None:
        extra["fixed_features_list"] = cfg.fixed_features_list

    picked, _ = optimize_acqf(
        acq_function=acqf,
        bounds=bounds.double(),
        q=q,
        num_restarts=cfg.num_restarts,
        raw_samples=cfg.raw_samples,
        **extra,
    )
    return picked


def _check_bounds(bounds: Tensor) -> None:
    if bounds.ndim != 2 or bounds.shape[0] != 2:
        raise ValueError(f"bounds must be (2, d), got {tuple(bounds.shape)}")
    if not bool(torch.all(bounds[1] > bounds[0])):
        raise ValueError("every upper bound must exceed its lower bound")
