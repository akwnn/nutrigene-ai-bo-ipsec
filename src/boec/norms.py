"""The two competing error norms, computed against known truth on a fixed grid.

The claim under test (K0) is that terminal regret is governed by **sup-norm** surrogate
error and **not** by L2 accuracy. Q30 already measured the L2 half: an additive kernel
roughly doubled held-out R-squared and moved regret by **0.0015, p=0.71**. This module
supplies the other half, so the two can be compared on the same campaigns.

``grid_r2`` is deliberately **not clamped at zero**. A model worse than predicting the
mean has negative R-squared, and clamping would hide exactly the campaigns where the
comparison is most informative.
"""

from __future__ import annotations

import torch
from torch import Tensor
from torch.quasirandom import SobolEngine

__all__ = ["grid_r2", "sobol_grid", "sup_err"]


def sobol_grid(dim: int, n: int, seed: int = 0) -> Tensor:
    """``(n, dim)`` scrambled Sobol points in the unit box, deterministic in ``seed``."""
    return SobolEngine(dimension=dim, scramble=True, seed=seed).draw(n).double()


def _mean_and_truth(model, truth_fn, X_grid: Tensor) -> tuple[Tensor, Tensor]:
    """``(mean, truth)`` as flat double tensors.

    Accepts either the ``posterior_mean`` protocol used by the analytic stand-ins in the
    tests, or a BoTorch model exposing ``posterior``. One code path for both, so a test
    double cannot pass through logic the real model skips.
    """
    with torch.no_grad():
        if hasattr(model, "posterior_mean"):
            mean = model.posterior_mean(X_grid)
        else:
            mean = model.posterior(X_grid).mean
    return mean.reshape(-1).double(), truth_fn(X_grid).reshape(-1).double()


def sup_err(model, truth_fn, X_grid: Tensor) -> float:
    """``max_x |E[f(x)] - f(x)|`` over the grid. The L-infinity quantity."""
    mean, truth = _mean_and_truth(model, truth_fn, X_grid)
    return float((mean - truth).abs().max())


def grid_r2(model, truth_fn, X_grid: Tensor) -> float:
    """``1 - SS_res / SS_tot`` against truth on the grid. Unclamped, so it may go below 0."""
    mean, truth = _mean_and_truth(model, truth_fn, X_grid)
    ss_res = ((truth - mean) ** 2).sum()
    ss_tot = ((truth - truth.mean()) ** 2).sum()
    return float(1.0 - ss_res / ss_tot)
