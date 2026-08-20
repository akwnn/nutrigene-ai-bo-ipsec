"""Shared measurement functions.

OWNERSHIP: written by Person B, imported by Person A. Do not reimplement.

`over_prediction_at_constrained_argmax` is called from two places that must
agree exactly:

  * Person A — the sequential-DoE confirmation run inside E2 (stage 4)
  * Person B — E4a, for each of the four fitted models

If each of us wrote our own, we would get two numbers that disagree and no way
to adjudicate. One function makes them a genuine replication instead.

Shape contract: every X is ``(n, d)``, every outcome is ``(n, m)`` even at m=1.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import torch
from scipy.optimize import minimize
from torch import Tensor
from torch.quasirandom import SobolEngine

__all__ = [
    "OverPrediction",
    "ScreenedArgmax",
    "constrained_argmax",
    "grid_screened_argmax",
    "over_prediction_at_constrained_argmax",
]

# Predicts a model's mean outcome. Takes (n, d), returns (n, 1).
PredictFn = Callable[[Tensor], Tensor]


@dataclass(frozen=True)
class OverPrediction:
    """Result of asking a model where the optimum is, then going to look.

    Attributes:
        x_argmax: ``(d,)`` the model's best point over the extended box.
        y_predicted: what the model said the response would be there.
        y_true: what the response actually is there (noiseless oracle value).
        over_prediction: ``y_predicted - y_true``. Positive means the model
            promised more than reality delivered. **This is the primary
            outcome of E4a and of A's DoE confirmation run.**
        n_starts_converged: how many multi-starts the optimizer completed.
    """

    x_argmax: Tensor
    y_predicted: float
    y_true: float
    over_prediction: float
    n_starts_converged: int

    def __post_init__(self) -> None:
        if self.x_argmax.ndim != 1:
            raise ValueError(f"x_argmax must be (d,), got {tuple(self.x_argmax.shape)}")


def _as_2d(x: np.ndarray, d: int) -> Tensor:
    return torch.from_numpy(np.asarray(x, dtype=np.float64).reshape(1, d))


def constrained_argmax(
    predict: PredictFn,
    bounds: Tensor,
    *,
    n_restarts: int = 20,
    raw_samples: int = 4096,
    seed: int = 0,
) -> tuple[Tensor, float, int]:
    """Maximize ``predict`` over the box, by Sobol screening then L-BFGS-B.

    Deliberately independent of BoTorch's ``optimize_acqf``: this has to run
    on a polynomial and a nonlinear-least-squares fit as well as on a GP, so it
    takes a plain callable rather than an acquisition function.

    Deterministic given ``seed`` — both people must get the same answer from
    the same inputs, or the shared-metric guarantee is worthless.

    Args:
        predict: maps ``(n, d)`` to ``(n, 1)``. Must not raise inside the box.
        bounds: ``(2, d)``, row 0 lower and row 1 upper. The *extended* box
            (the unit cube) in E4 — not the sub-box the model was fitted on.
        n_restarts: local optimizations run from the best Sobol points.
        raw_samples: Sobol points screened before choosing restarts.
        seed: fixes the Sobol draw.

    Returns:
        ``(x_argmax (d,), y_predicted, n_starts_converged)``.
    """
    if bounds.ndim != 2 or bounds.shape[0] != 2:
        raise ValueError(f"bounds must be (2, d), got {tuple(bounds.shape)}")
    d = bounds.shape[1]
    lo = bounds[0].double().numpy()
    hi = bounds[1].double().numpy()
    if not np.all(hi > lo):
        raise ValueError("every upper bound must exceed its lower bound")

    # --- screen ---
    sobol = SobolEngine(dimension=d, scramble=True, seed=seed)
    unit = sobol.draw(raw_samples).double()
    raw_X = torch.from_numpy(lo) + unit * torch.from_numpy(hi - lo)
    with torch.no_grad():
        raw_Y = predict(raw_X)
    if raw_Y.shape != (raw_samples, 1):
        raise ValueError(
            f"predict must return (n, 1); got {tuple(raw_Y.shape)} for n={raw_samples}"
        )
    top = torch.topk(raw_Y.squeeze(-1), k=min(n_restarts, raw_samples)).indices
    starts = raw_X[top].numpy()

    # --- polish ---
    def neg(x: np.ndarray) -> float:
        with torch.no_grad():
            return float(-predict(_as_2d(x, d)).item())

    box = list(zip(lo.tolist(), hi.tolist(), strict=True))
    best_x, best_y, n_ok = None, -np.inf, 0
    for x0 in starts:
        res = minimize(neg, x0, method="L-BFGS-B", bounds=box)
        if not res.success:
            continue
        n_ok += 1
        if -res.fun > best_y:
            best_y, best_x = float(-res.fun), res.x

    if best_x is None:
        # Every local polish failed. Fall back to the best screened point
        # rather than dropping the instance silently.
        idx = int(torch.argmax(raw_Y.squeeze(-1)))
        return raw_X[idx].clone(), float(raw_Y[idx].item()), 0

    x_out = torch.from_numpy(np.clip(best_x, lo, hi))
    return x_out, best_y, n_ok


@dataclass(frozen=True)
class ScreenedArgmax:
    """Where a model says the optimum is, after a grid screen and a local polish.

    Attributes:
        x: ``(d,)`` the point the rule nominates — whichever of the screened and
            polished points has the higher predicted value.
        value: ``predict`` at ``x``.
        x_grid: ``(d,)`` the best point of the screening grid, kept so the polish's
            contribution can be reported rather than assumed.
        value_grid: ``predict`` at ``x_grid``.
        from_grid: ``True`` when the screen beat the polish and was kept.
        n_starts_converged: local optimizations the polish completed.
    """

    x: Tensor
    value: float
    x_grid: Tensor
    value_grid: float
    from_grid: bool
    n_starts_converged: int


def grid_screened_argmax(
    predict: PredictFn,
    X_grid: Tensor,
    grid_values: Tensor,
    bounds: Tensor,
    *,
    n_restarts: int = 20,
    raw_samples: int = 4096,
    seed: int = 0,
) -> ScreenedArgmax:
    """Maximize ``predict`` by screening a **precomputed** grid, then polishing.

    :func:`constrained_argmax` already screens with its own Sobol draw. This adds a
    second, larger screen that the caller has already paid for — the registered
    20,000-point grid — and keeps whichever point predicts higher. At a shared Sobol
    seed the polish's ``raw_samples`` draw is literally the first ``raw_samples`` rows
    of a ``sobol_grid`` of the same seed, so the grid is a **strict superset** of the
    screen and the two candidates are commensurable rather than unrelated draws.

    ``grid_values`` is passed in, never recomputed. For a BoTorch model
    ``model.posterior(X_grid)`` builds the **joint** covariance over the whole grid:
    100.6 s at 20,000 points against 0.06 s at 2,000, and a 3.2 GB dense matrix whose
    off-diagonal is never used. Callers evaluate the grid once, chunked, through
    :func:`boec.designspace.gp_adapter`; a locator that quietly re-evaluated it would
    put that trap back.

    Args:
        predict: maps ``(n, d)`` to ``(n, 1)``. Must be the same function
            ``grid_values`` came from, or the two candidates are not comparable.
        X_grid: ``(n, d)`` the screening grid.
        grid_values: ``(n,)`` (or ``(n, 1)``) ``predict`` evaluated on ``X_grid``.
        bounds: ``(2, d)`` the box the polish may search.
        n_restarts: passed to :func:`constrained_argmax`.
        raw_samples: passed to :func:`constrained_argmax`.
        seed: passed to :func:`constrained_argmax`; fixes its Sobol screen.

    Returns:
        A :class:`ScreenedArgmax`. ``.x`` is never worse than ``.x_grid`` under
        ``predict``, so adding the polish cannot cost an arm ground it had already won.
    """
    if X_grid.ndim != 2:
        raise ValueError(f"X_grid must be (n, d), got {tuple(X_grid.shape)}")
    values = grid_values.reshape(-1).double()
    if values.numel() != X_grid.shape[0]:
        raise ValueError(
            "grid_values must carry one value per grid row; got "
            f"{values.numel()} for {X_grid.shape[0]} rows"
        )

    idx = int(torch.argmax(values))
    x_grid = X_grid[idx].double().clone()
    v_grid = float(values[idx])

    x_pol, v_pol, n_ok = constrained_argmax(
        predict, bounds, n_restarts=n_restarts, raw_samples=raw_samples, seed=seed
    )
    if v_pol > v_grid:
        return ScreenedArgmax(x=x_pol.double(), value=v_pol, x_grid=x_grid,
                              value_grid=v_grid, from_grid=False,
                              n_starts_converged=n_ok)
    return ScreenedArgmax(x=x_grid, value=v_grid, x_grid=x_grid, value_grid=v_grid,
                          from_grid=True, n_starts_converged=n_ok)


def over_prediction_at_constrained_argmax(
    predict: PredictFn,
    truth: PredictFn,
    bounds: Tensor,
    *,
    n_restarts: int = 20,
    raw_samples: int = 4096,
    seed: int = 0,
) -> OverPrediction:
    """Ask a model where the optimum is, then evaluate the truth there.

    The primary outcome of E4a, and of A's DoE stage-4 confirmation run.

    Why the *constrained argmax* rather than the stationary point: inside a
    sub-box on the rising arm of a biphasic response the second-order fit often
    has positive curvature, so its stationary point is a **minimum**. Asking
    "did the stationary point escape the box" would then be answering a
    question about a minimum. The constrained argmax is always defined,
    whatever the curvature. Stationary-point location and Hessian class are
    reported separately and descriptively — see ``rsm.classify_stationary_point``.

    Args:
        predict: the fitted model's mean. ``(n, d) -> (n, 1)``.
        truth: the noiseless oracle. ``(n, d) -> (n, 1)``. **Must be the
            noiseless value, not a noisy draw** — otherwise over-prediction
            picks up observation noise and the E4a distribution widens for a
            reason unrelated to extrapolation.
        bounds: ``(2, d)`` extended box.
        n_restarts: passed through.
        raw_samples: passed through.
        seed: passed through; fixes the Sobol screen.

    Returns:
        An :class:`OverPrediction`. ``.over_prediction`` is the headline number.
    """
    x_hat, y_pred, n_ok = constrained_argmax(
        predict, bounds, n_restarts=n_restarts, raw_samples=raw_samples, seed=seed
    )
    with torch.no_grad():
        y_true_t = truth(x_hat.unsqueeze(0))
    if y_true_t.shape != (1, 1):
        raise ValueError(f"truth must return (1, 1); got {tuple(y_true_t.shape)}")
    y_true = float(y_true_t.item())

    return OverPrediction(
        x_argmax=x_hat,
        y_predicted=y_pred,
        y_true=y_true,
        over_prediction=y_pred - y_true,
        n_starts_converged=n_ok,
    )
