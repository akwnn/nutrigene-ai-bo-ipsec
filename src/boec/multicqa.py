"""Conservative, simultaneous certificates for multiple CQAs.

The joint certificate uses a Bonferroni allocation across CQA dimensions.  It
therefore makes no independence assumption and is intentionally conservative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import torch
from torch import Tensor


@dataclass(frozen=True)
class Certificate:
    """A joint CQA region and diagnostics for an abstention decision."""

    mask: Tensor
    containment: float | None
    volume: float
    abstention_reason: str | None
    limiting_cqa: str | None
    lower_bounds: Tensor | None = None
    cqa_names: tuple[str, ...] = ()


def _alpha(alpha: Real) -> float:
    if isinstance(alpha, bool) or not isinstance(alpha, Real):
        raise ValueError("alpha must be a finite real scalar")
    value = float(alpha)
    if not math.isfinite(value) or not 0.0 < value < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1")
    return value


def joint_lower_bound(mean: Tensor, covariance: Tensor, alpha: Real) -> Tensor:
    """Return simultaneous lower bounds for each grid point and CQA.

    ``mean`` has shape ``(..., n_cqa)``.  ``covariance`` may be a matching
    diagonal variance tensor, ``(..., n_cqa, n_cqa)``, or ``(n_cqa, n_cqa)``.
    The family-wise miscoverage ``alpha`` is divided equally among CQAs.
    """
    alpha_f = _alpha(alpha)
    if not isinstance(mean, Tensor) or mean.ndim < 1 or mean.shape[-1] < 1:
        raise ValueError("mean must have shape (..., n_cqa)")
    if not isinstance(covariance, Tensor):
        raise ValueError("covariance must be a tensor")
    if not bool(torch.isfinite(mean).all()) or not bool(torch.isfinite(covariance).all()):
        raise ValueError("mean and covariance must be finite")
    q = int(mean.shape[-1])
    if covariance.ndim == mean.ndim:
        if covariance.shape != mean.shape:
            raise ValueError("diagonal covariance must match mean shape")
        variance = covariance
    elif covariance.ndim >= 2 and covariance.shape[-2:] == (q, q):
        try:
            variance = covariance.diagonal(dim1=-2, dim2=-1).expand(mean.shape)
        except RuntimeError as exc:
            raise ValueError("covariance is not broadcastable to mean") from exc
    else:
        raise ValueError("covariance must contain one variance per CQA")
    if bool(torch.any(variance < 0)):
        raise ValueError("covariance diagonal cannot be negative")
    normal = torch.distributions.Normal(
        torch.zeros((), dtype=mean.dtype, device=mean.device),
        torch.ones((), dtype=mean.dtype, device=mean.device),
    )
    # One-sided Gaussian bounds with family-wise error alpha.
    z = normal.icdf(torch.as_tensor(1.0 - alpha_f / q, dtype=mean.dtype, device=mean.device))
    return mean - z * variance.clamp_min(0).sqrt()


def certificate_from_draws(
    draws: Tensor,
    thresholds: Tensor,
    alpha: Real,
    *,
    cqa_names: tuple[str, ...] | list[str] | None = None,
) -> Certificate:
    """Issue a joint certificate from posterior draws of shape ``(draw, grid, CQA)``."""
    _alpha(alpha)
    if not isinstance(draws, Tensor) or draws.ndim != 3:
        raise ValueError("draws must have shape (n_draws, n_grid, n_cqa)")
    if draws.shape[0] < 2 or draws.shape[1] < 1 or draws.shape[2] < 1:
        raise ValueError("draws must contain at least two draws and one grid point")
    if not isinstance(thresholds, Tensor) or thresholds.ndim != 1 or thresholds.shape[0] != draws.shape[2]:
        raise ValueError("thresholds must have shape (n_cqa,)")
    if not bool(torch.isfinite(draws).all()) or not bool(torch.isfinite(thresholds).all()):
        raise ValueError("draws and thresholds must be finite")
    q = int(draws.shape[2])
    names = tuple(cqa_names) if cqa_names is not None else tuple(f"cqa_{i}" for i in range(q))
    if len(names) != q or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("cqa_names must contain one non-empty name per CQA")
    mean = draws.mean(dim=0)
    variance = draws.var(dim=0, unbiased=True)
    lower = joint_lower_bound(mean, variance, alpha)
    mask = (lower >= thresholds).all(dim=-1)
    if bool(mask.any()):
        selected = mask
        pass_rates = ((draws >= thresholds).all(dim=-1)[:, selected]).all(dim=-1).double()
        containment = float(pass_rates.mean())
        margins = (lower - thresholds) / variance.clamp_min(torch.finfo(draws.dtype).eps).sqrt()
        limiting = names[int(torch.argmin(margins[selected].mean(dim=0)))]
        reason = None
    else:
        containment = None
        # The CQA with the fewest individually passing candidates blocks the
        # largest possible joint region; argmin gives deterministic tie breaks.
        blockers = (lower >= thresholds).sum(dim=0)
        limiting = names[int(torch.argmin(blockers))]
        reason = "no_joint_region"
    return Certificate(
        mask=mask,
        containment=containment,
        volume=float(mask.double().mean()),
        abstention_reason=reason,
        limiting_cqa=limiting,
        lower_bounds=lower,
        cqa_names=names,
    )


__all__ = ["Certificate", "certificate_from_draws", "joint_lower_bound"]
