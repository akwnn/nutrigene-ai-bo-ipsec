"""The third comparison: what a working scientist would reasonably try.

OWNERSHIP: Person B. Phase 1 only.

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

Experiment 4 compares four ways of modelling the same measurements. Two are
obvious: the traditional curved-surface fit, and the newer approach that knows
when it's guessing. This file is the third.

The idea: a biologist looking at dose-response data doesn't reach for a generic
curved surface. They reach for a shape they already believe in. Doses usually
help at first, level off, and then start to hurt at high concentrations. So
they fit *that* shape — a rise, a plateau, a decline — one ingredient at a time,
and add the results up.

**Why include it at all.** Without it, the comparison is "generic maths versus
generic maths", and a reviewer can fairly ask: what if someone had just used
sensible biology? This answers that question instead of leaving it open.

**Why it is deliberately not as good as it could be.** We know exactly how the
made-up data was built, so we could fit that exact formula and win trivially —
and prove nothing, because in real life nobody knows the true formula. So this
uses the shape a practitioner would *guess*, with two deliberate handicaps that
match real ignorance:

  * **No ingredient interactions.** Each ingredient is treated on its own and
    the effects are added up. The real data does have interactions. A working
    scientist starting out would not know that.
  * **Peak positions and steepness are estimated from the data**, not read off
    the answer sheet.

A comparator that has been handed the answer isn't a comparator.

**What honest failure looks like here.** Fitting this shape is a numerical
search that sometimes doesn't converge. **When it fails we record the failure
rather than quietly dropping that dataset.** Silently discarding the awkward
cases would make the method look better than it is — you'd be reporting only
the runs where it worked.

------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from scipy.optimize import least_squares
from torch import Tensor

__all__ = [
    "ParametricFit",
    "biphasic_response_torch",
    "biphasic_response",
    "fit_practitioner_parametric",
]

# Below this, a concentration is treated as zero. Guards the power terms.
_EPS = 1e-12


def biphasic_response(
    x: np.ndarray,
    ec50: np.ndarray,
    ic50: np.ndarray,
    n: np.ndarray,
) -> np.ndarray:
    """One ingredient's rise-plateau-decline curve, scaled to peak at 1.

    Two competing effects multiplied together: a helping term that switches on
    around ``ec50``, and a hurting term that switches on around ``ic50``. When
    the hurting term switches on later than the helping one, the result rises,
    plateaus, then falls — which is what dose-response biology usually does.

    ``n`` controls how sharply each switch happens.

    Scaled so the peak is exactly 1, so that a factor's weight genuinely
    controls its importance rather than being tangled up with how tall its
    curve happens to be.

    Args:
        x: ``(n_points, d)`` concentrations, coded 0 to 1.
        ec50: ``(d,)`` where the helping effect kicks in.
        ic50: ``(d,)`` where the hurting effect kicks in.
        n: ``(d,)`` steepness.

    Returns:
        ``(n_points, d)`` each column peaking at 1.
    """
    xs = np.clip(x, _EPS, None)
    xn = xs**n
    helping = xn / (ec50**n + xn)
    hurting = 1.0 / (1.0 + (xs / ic50) ** n)
    s = (ic50 / ec50) ** (n / 2.0)
    normaliser = ((1.0 + s) / s) ** 2
    return helping * hurting * normaliser


@dataclass(frozen=True)
class ParametricFit:
    """A fitted practitioner-form model.

    Attributes:
        ec50: ``(d,)`` fitted rise points.
        ic50: ``(d,)`` fitted decline points.
        n: ``(d,)`` fitted steepness.
        weights: ``(d,)`` how much each ingredient contributes.
        intercept: baseline level.
        converged: whether the numerical search succeeded. **Check this.**
        n_restarts_converged: how many of the restarts succeeded.
        residual_sum_squares: goodness of fit; ``inf`` if nothing converged.
        message: what the optimizer said.
    """

    ec50: np.ndarray
    ic50: np.ndarray
    n: np.ndarray
    weights: np.ndarray
    intercept: float
    converged: bool
    n_restarts_converged: int
    residual_sum_squares: float
    message: str

    @property
    def d(self) -> int:
        return int(self.ec50.shape[0])

    def predict(self, X: Tensor) -> Tensor:
        """Mean prediction. ``(n, d) -> (n, 1)``, matching ``metrics.PredictFn``.

        Raises:
            RuntimeError: if the fit never converged. Returning numbers from a
                failed fit would put nonsense into the comparison without
                anything flagging it.
        """
        if not self.converged:
            raise RuntimeError(
                "this fit did not converge — refusing to predict from it. "
                f"Optimizer said: {self.message}"
            )
        A = np.asarray(X.numpy() if isinstance(X, Tensor) else X, dtype=np.float64)
        if A.ndim != 2:
            raise ValueError(f"X must be (n, d), got {A.shape}")
        if A.shape[1] != self.d:
            raise ValueError(f"X has {A.shape[1]} factors, fit has {self.d}")
        per_factor = biphasic_response(A, self.ec50, self.ic50, self.n)
        y = self.intercept + per_factor @ self.weights
        return torch.from_numpy(y.reshape(-1, 1))


def _pack(ec50, ic50, n, w, b):
    """Fit in log-space for the positive parameters, so they can't go negative."""
    return np.concatenate([np.log(ec50), np.log(ic50), np.log(n), w, [b]])


def _unpack(theta, d):
    ec50 = np.exp(theta[:d])
    ic50 = np.exp(theta[d : 2 * d])
    n = np.exp(theta[2 * d : 3 * d])
    w = theta[3 * d : 4 * d]
    b = theta[4 * d]
    return ec50, ic50, n, w, b


def fit_practitioner_parametric(
    X: Tensor,
    Y: Tensor,
    *,
    n_restarts: int = 8,
    seed: int = 0,
    max_nfev: int = 4000,
) -> ParametricFit:
    """Fit the practitioner-form model by nonlinear least squares.

    Multi-start, because this kind of fit has local optima and a single start
    lands in a bad one often enough to matter.

    Args:
        X: ``(n, d)`` recipes, coded 0 to 1.
        Y: ``(n, 1)`` measurements.
        n_restarts: how many starting points to try.
        seed: fixes the starting points, so the fit is reproducible.
        max_nfev: iteration cap per restart.

    Returns:
        A :class:`ParametricFit`. **Always check ``.converged``** — a failed fit
        is recorded, not raised, so the caller can log the failure rate. Doing
        it the other way round tempts callers into a `try/except` that quietly
        drops the awkward instances.
    """
    if Y.ndim != 2 or Y.shape[1] != 1:
        raise ValueError(f"Y must be (n, 1), got {tuple(Y.shape)}")
    if X.shape[0] != Y.shape[0]:
        raise ValueError(f"X has {X.shape[0]} rows, Y has {Y.shape[0]}")

    A = X.double().numpy()
    y = Y.double().numpy().ravel()
    n_obs, d = A.shape

    n_params = 4 * d + 1
    if n_obs <= n_params:
        return ParametricFit(
            ec50=np.full(d, np.nan), ic50=np.full(d, np.nan), n=np.full(d, np.nan),
            weights=np.full(d, np.nan), intercept=float("nan"),
            converged=False, n_restarts_converged=0,
            residual_sum_squares=float("inf"),
            message=f"{n_obs} measurements cannot fit {n_params} parameters",
        )

    def residuals(theta: np.ndarray) -> np.ndarray:
        ec50, ic50, n, w, b = _unpack(theta, d)
        # ic50 must exceed ec50 or the curve is not rise-then-fall. Penalise
        # rather than hard-constrain: a hard constraint makes the search
        # brittle, and a large penalty is enough to keep it in the valid region.
        penalty = np.maximum(0.0, ec50 - ic50 + 1e-3).sum() * 1e3
        pred = b + biphasic_response(A, ec50, ic50, n) @ w
        return np.concatenate([pred - y, [penalty]])

    rng = np.random.default_rng(seed)
    y_span = float(np.ptp(y)) or 1.0
    best: tuple[float, np.ndarray] | None = None
    n_ok = 0
    last_message = "no restart attempted"

    for _ in range(n_restarts):
        theta0 = _pack(
            ec50=rng.uniform(0.10, 0.45, d),
            ic50=rng.uniform(0.55, 1.60, d),
            n=rng.uniform(1.0, 3.0, d),
            w=rng.uniform(0.5, 1.5, d) * y_span / d,
            b=float(np.min(y)),
        )
        try:
            res = least_squares(residuals, theta0, method="trf", max_nfev=max_nfev)
        except (ValueError, FloatingPointError) as exc:
            last_message = f"{type(exc).__name__}: {exc}"
            continue
        last_message = res.message
        if not res.success:
            continue
        n_ok += 1
        rss = float(np.sum(res.fun[:-1] ** 2))
        if best is None or rss < best[0]:
            best = (rss, res.x)

    if best is None:
        return ParametricFit(
            ec50=np.full(d, np.nan), ic50=np.full(d, np.nan), n=np.full(d, np.nan),
            weights=np.full(d, np.nan), intercept=float("nan"),
            converged=False, n_restarts_converged=0,
            residual_sum_squares=float("inf"),
            message=f"all {n_restarts} restarts failed; last: {last_message}",
        )

    rss, theta = best
    ec50, ic50, n, w, b = _unpack(theta, d)
    return ParametricFit(
        ec50=ec50, ic50=ic50, n=n, weights=w, intercept=float(b),
        converged=True, n_restarts_converged=n_ok,
        residual_sum_squares=rss, message="converged",
    )


def biphasic_response_torch(
    x: Tensor, ec50: Tensor, ic50: Tensor, n: Tensor
) -> Tensor:
    """The rise-plateau-decline curve, in torch so a GP can use it as its mean.

    Same formula as :func:`biphasic_response`, ported because a GP's mean has
    to be a torch computation. Kept beside the original deliberately: if one is
    edited and the other is not, a test comparing them fails.

    Args:
        x: ``(..., d)`` concentrations, coded 0 to 1.
        ec50: ``(d,)`` where the helping effect kicks in.
        ic50: ``(d,)`` where the hurting effect kicks in.
        n: ``(d,)`` steepness.

    Returns:
        ``(..., d)`` each factor peaking at 1.
    """
    xs = x.clamp_min(_EPS)
    xn = xs.pow(n)
    helping = xn / (ec50.pow(n) + xn)
    hurting = 1.0 / (1.0 + (xs / ic50).pow(n))
    s = (ic50 / ec50).pow(n / 2.0)
    return helping * hurting * ((1.0 + s) / s).pow(2)
