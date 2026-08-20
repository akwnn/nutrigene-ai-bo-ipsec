"""TuRBO-1 trust region for Q62.

Locked defaults copy the BoTorch TuRBO-1 tutorial (Eriksson et al. 2019).
Do not retune on Hill. Restart keeps all training data — a registered
deviation from canonical TuRBO, so the comparison with ``doe_ascent`` is not
handicapped by forgetting previous wells.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
from botorch.models import SingleTaskGP
from torch import Tensor

from boec.budget import ARRIVAL_CENSORED, first_budget_to_target
from boec.diagnostics import reported_best_curve
from boec.metrics import constrained_argmax
from boec.surrogate import lengthscales, predictive

def n_unique_locations(X: Tensor, ndigits: int = 12) -> int:
    """How many distinct recipes were visited (rounded)."""
    arr = np.round(X.detach().double().cpu().numpy(), ndigits)
    return int(np.unique(arr, axis=0).shape[0])

__all__ = [
    "LENGTH_INIT",
    "LENGTH_MAX",
    "LENGTH_MIN",
    "SUCCESS_TOLERANCE",
    "TurboState",
    "collapse_rate",
    "failure_tolerance",
    "identification_gap",
    "n_unique_locations",
    "posterior_mean_incumbent",
    "rounds_for_bo",
    "score_finished_campaign",
    "tr_bounds",
    "update_trust_region",
]

# BoTorch tutorial defaults. Frozen before Q62.
LENGTH_INIT = 0.8
LENGTH_MIN = 0.5 ** 7
LENGTH_MAX = 1.6
SUCCESS_TOLERANCE = 3
_IMPROVE_REL = 1e-3


def failure_tolerance(dim: int, q: int) -> int:
    """BoTorch TuRBO-1: ceil(max(4/q, d/q))."""
    if q < 1:
        raise ValueError(f"q must be >= 1, got {q}")
    return int(math.ceil(max(4.0 / q, dim / q)))


@dataclass
class TurboState:
    dim: int
    batch_size: int
    length: float = LENGTH_INIT
    length_min: float = LENGTH_MIN
    length_max: float = LENGTH_MAX
    failure_counter: int = 0
    success_counter: int = 0
    success_tolerance: int = SUCCESS_TOLERANCE
    best_value: float = -float("inf")
    restart_triggered: bool = False
    keep_history: bool = True
    n_restarts: int = 0

    def __post_init__(self) -> None:
        self.failure_tolerance = failure_tolerance(self.dim, self.batch_size)

    def after_restart(self) -> TurboState:
        """New TR from the current incumbent. Data stay on the campaign."""
        if not self.keep_history:
            raise RuntimeError("Q62 forbids discarding history on restart")
        return TurboState(
            dim=self.dim,
            batch_size=self.batch_size,
            length=LENGTH_INIT,
            best_value=self.best_value,
            keep_history=True,
            n_restarts=self.n_restarts + 1,
        )


def tr_bounds(
    x_center: Tensor,
    lengthscales: Tensor,
    length: float,
    global_bounds: Tensor,
) -> Tensor:
    """Hyper-rectangle around ``x_center``, stretched by GP lengthscales.

    Side *i* has half-width ``(length / 2) * (ls_i / mean(ls))``, then clipped
    to ``global_bounds``. Every upper bound is forced strictly above the lower.
    """
    center = x_center.reshape(-1).double()
    ls = lengthscales.reshape(-1).double().clamp_min(1e-12)
    weights = ls / ls.mean()
    half = (length / 2.0) * weights
    lo = torch.maximum(global_bounds[0].double(), center - half)
    hi = torch.minimum(global_bounds[1].double(), center + half)
    # Degenerate faces (centre on a wall): give a tiny open interval inside the box.
    too_close = hi - lo < 1e-12
    if bool(torch.any(too_close)):
        span = (global_bounds[1] - global_bounds[0]).double()
        lo = torch.where(too_close, lo, lo)
        hi = torch.where(too_close, torch.minimum(global_bounds[1].double(), lo + 1e-6 * span), hi)
        still = hi - lo < 1e-12
        lo = torch.where(still, torch.maximum(global_bounds[0].double(), hi - 1e-6 * span), lo)
    return torch.stack([lo, hi]).detach()


def posterior_mean_incumbent(
    model: SingleTaskGP, train_X: Tensor
) -> tuple[int, Tensor, Tensor]:
    """Visited well with the highest GP posterior mean (noisy incumbent)."""
    mean = predictive(model, train_X.double()).mean.reshape(-1)
    idx = int(torch.argmax(mean))
    return idx, train_X.double()[idx].reshape(-1).detach().clone(), mean[idx].reshape(()).detach().clone()


def update_trust_region(state: TurboState, incumbent_value: float) -> TurboState:
    """Expand / shrink / flag restart from one batch's posterior-mean incumbent."""
    improved = incumbent_value > state.best_value + _IMPROVE_REL * abs(state.best_value)
    success_counter = state.success_counter
    failure_counter = state.failure_counter
    length = state.length
    best = state.best_value
    restart = False

    if improved:
        success_counter += 1
        failure_counter = 0
        best = float(incumbent_value)
        if success_counter >= state.success_tolerance:
            length = min(state.length_max, length * 2.0)
            success_counter = 0
    else:
        success_counter = 0
        failure_counter += 1
        if failure_counter >= state.failure_tolerance:
            length = length / 2.0
            failure_counter = 0
            if length < state.length_min:
                restart = True
                length = state.length_min

    return TurboState(
        dim=state.dim,
        batch_size=state.batch_size,
        length=length,
        length_min=state.length_min,
        length_max=state.length_max,
        failure_counter=failure_counter,
        success_counter=success_counter,
        success_tolerance=state.success_tolerance,
        best_value=best,
        restart_triggered=restart,
        keep_history=state.keep_history,
        n_restarts=state.n_restarts,
    )


def identification_gap(r_measured: float, r_search: float) -> float:
    """Extra simple regret from picking the noisy winner instead of the true best visited."""
    return float(r_measured - r_search)


def rounds_for_bo(n: int, d: int, q: int = 4, n_init: int | None = None) -> int:
    """Plate rounds: opening plus ceil((n - n0)/q). Matches Campaign.batch_plan."""
    n0 = 2 * d + 2 if n_init is None else int(n_init)
    if n <= 0:
        return 0
    if n <= n0:
        return 1
    extra = n - n0
    return 1 + (extra + q - 1) // q


def score_finished_campaign(
    campaign,
    truth: Tensor,
    observed: Tensor,
    optimum: float,
    *,
    targets: tuple[float, ...] = (0.15, 0.10, 0.05),
    gp_restarts: int = 8,
    gp_raw_samples: int = 256,
) -> dict:
    """Locators registered for Q62, plus arrival checkpoints and unique-well count."""
    measured = reported_best_curve(truth, observed)
    t = truth.detach().double().reshape(-1)
    opt = float(optimum)
    r_measured = float(opt - measured[-1])
    r_search = float(opt - float(t.max()))
    curve = {i + 1: float(opt - measured[i]) for i in range(len(measured))}
    arrivals = {}
    for tau in targets:
        hit = first_budget_to_target(curve, target=tau, cap=int(campaign.n_observed))
        arrivals[f"{tau:.2f}"] = None if hit is ARRIVAL_CENSORED else int(hit)

    gp_box = gp_tr = None
    ev = campaign.evaluator
    if hasattr(ev, "truth"):
        model = campaign.fit()

        def _mean(X: Tensor) -> Tensor:
            m = predictive(model, X.double()).mean
            return m.reshape(-1, 1)

        x_box, _, _ = constrained_argmax(
            _mean, campaign.bounds, n_restarts=gp_restarts,
            raw_samples=gp_raw_samples, seed=campaign.config.seed,
        )
        gp_box = float(opt - float(ev.truth(x_box.reshape(1, -1)).reshape(-1)[0]))
        tr = campaign.last_tr_bounds
        if tr is None and campaign.turbo_state is not None:
            _, x_inc, _ = posterior_mean_incumbent(model, campaign.train_X.detach())
            tr = tr_bounds(
                x_inc, lengthscales(model).reshape(-1), campaign.turbo_state.length,
                campaign.bounds,
            )
        if tr is not None:
            x_tr, _, _ = constrained_argmax(
                _mean, tr.detach(), n_restarts=gp_restarts,
                raw_samples=gp_raw_samples, seed=campaign.config.seed,
            )
            gp_tr = float(opt - float(ev.truth(x_tr.reshape(1, -1)).reshape(-1)[0]))

    at_48 = None
    if len(measured) >= 48:
        at_48 = float(opt - measured[47])
    return dict(
        R_measured=r_measured,
        R_search=r_search,
        R_id=identification_gap(r_measured, r_search),
        R_gp_box=gp_box,
        R_gp_tr=gp_tr,
        R_measured_at_48=at_48,
        n_unique=n_unique_locations(campaign.train_X),
        n_observed=int(campaign.n_observed),
        n_rounds=rounds_for_bo(
            int(campaign.n_observed), campaign.config.d,
            campaign.config.q, campaign.config.n_init,
        ),
        arrivals=arrivals,
        n_restarts=campaign.turbo_state.n_restarts if campaign.turbo_state else 0,
        length_final=campaign.turbo_state.length if campaign.turbo_state else None,
        keep_history=True if campaign.turbo_state else None,
    )


def collapse_rate(
    unique_counts_by_landscape: list[list[int]],
    thresh: int = 20,
) -> float:
    """Share of landscapes where every seed used fewer than ``thresh`` unique wells."""
    if not unique_counts_by_landscape:
        raise ValueError("empty collapse sample")
    flags = [all(int(n) < thresh for n in seeds) for seeds in unique_counts_by_landscape]
    return float(sum(flags) / len(flags))

