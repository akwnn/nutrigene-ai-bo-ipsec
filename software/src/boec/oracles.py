"""Synthetic oracles for Phase 1.

Two families behind one ABC:

* **Standard test functions** (Branin, Hartmann6, Ackley). Shipped first on purpose —
  the campaign loop is built against these, and the biphasic oracle swaps in later
  through the same interface. If that swap is not clean, the forward-compatibility
  design was never real, and it is better to find that out now than in Phase 2 when a
  lookup table has to swap in.

* **The biphasic Hill oracle.** Saturating dose-response with an inhibitory arm, so
  every factor has a genuine interior optimum. This is the fake data the Phase 1
  claims are measured on.

Every ``f`` takes ``(n, d)`` and returns ``(n,)``. There is no ``(d,)`` fast path.

Interaction structure
---------------------
Two modes, selected by ``InteractionMode``:

``"product"`` — the v6 form ``f = sum_i w_i*ft_i + (1/k) sum_pairs beta_ij*ft_i*ft_j``.
Retained because the v6 acceptance rate is a required pre-flight deliverable, and
because reproducing a known-bad configuration is how you demonstrate it is bad.

``"peak_modulation"`` — the default. Factor ``j``'s level shifts factor ``i``'s peak
*location*, which is what cytokine cross-talk actually does. This exists because the
product form provably cannot move the optimum::

    df/dx_i = ft_i'(x_i) * [ w_i + (1/k) sum_j beta_ij*ft_j(x_j) ]

The bracket contains no ``x_i``, so ``argmax_{x_i} f = x*_i`` for any setting of the
other coordinates and the planted optimum is coordinate-wise separable. Measured over
300 d=6 instances: max |joint argmax - per-factor peak| = 0.00e+00 on the 92% with a
positive bracket. On the other 8% the bracket goes negative, that coordinate's optimum
jumps to a box edge, and an optimum search seeded at ``x*`` converges to a *local* max
— giving a cached optimum below the true one and negative regret.

Peak modulation fixes all of it: the optimum is a fixed point rather than a closed
form, positivity is automatic (``f = sum_i w_i*ft_i >= 0``), and there is no bracket
to go negative. It does *not* make the problem harder for coordinate search — a sum of
coordinate-wise-unimodal terms is intrinsically easy — so genuine multivariate
difficulty comes from Hartmann6, not from here.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from scipy.optimize import minimize

InteractionMode = Literal["peak_modulation", "product"]

#: Bumped whenever the construction OR the acceptance parameters change. Under any
#: rejection sampling the seed -> instance map depends on the acceptance rule, because
#: rejections consume RNG draws. Changing a threshold without bumping this makes the
#: same instance_id denote a different landscape.
ORACLE_FAMILY = "biphasic-hill-v8"

_EPS = 1e-12


# --------------------------------------------------------------------------------
# Oracle ABC
# --------------------------------------------------------------------------------
class Oracle(ABC):
    """A noiseless function plus a noise model.

    The optimizer never touches an Oracle directly; an ``Evaluator`` does. That
    indirection is what lets Phase 2 substitute a lookup table and Phase 3 a human.
    """

    name: str
    dim: int

    @abstractmethod
    def f(self, X: np.ndarray) -> np.ndarray:
        """Noiseless response. ``(n, d)`` -> ``(n,)``."""

    @property
    def optimum_x(self) -> np.ndarray | None:
        """``(d,)`` location of the global maximum, if known."""
        return None

    @property
    def optimum_value(self) -> float | None:
        return None

    def check_X(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be (n, d); got shape {X.shape}")
        if X.shape[1] != self.dim:
            raise ValueError(f"X must have d={self.dim} columns; got {X.shape[1]}")
        return X


# --------------------------------------------------------------------------------
# Standard test functions — all posed as MAXIMISATION on coded [0, 1]^d
# --------------------------------------------------------------------------------
class Branin(Oracle):
    """2-D smoke test. Negated so the optimum is a maximum; three global optima."""

    name = "branin"
    dim = 2
    _OPT_VALUE = -0.397887  # negated Branin at its three minima

    def f(self, X: np.ndarray) -> np.ndarray:
        X = self.check_X(X)
        x1 = X[:, 0] * 15.0 - 5.0
        x2 = X[:, 1] * 15.0
        a, b, c = 1.0, 5.1 / (4 * np.pi**2), 5.0 / np.pi
        r, s, t = 6.0, 10.0, 1.0 / (8 * np.pi)
        return -(a * (x2 - b * x1**2 + c * x1 - r) ** 2 + s * (1 - t) * np.cos(x1) + s)

    @property
    def optimum_x(self) -> np.ndarray:
        return np.array([(np.pi + 5.0) / 15.0, 2.275 / 15.0])

    @property
    def optimum_value(self) -> float:
        return self._OPT_VALUE


class Hartmann6(Oracle):
    """6-D, deceptive, six local optima. The workhorse benchmark.

    This is what supplies genuine multivariate difficulty to Phase 1 — the Hill
    oracle cannot, because it is a sum of coordinate-wise-unimodal terms.
    """

    name = "hartmann6"
    dim = 6
    _ALPHA = np.array([1.0, 1.2, 3.0, 3.2])
    _A = np.array(
        [
            [10.0, 3.0, 17.0, 3.5, 1.7, 8.0],
            [0.05, 10.0, 17.0, 0.1, 8.0, 14.0],
            [3.0, 3.5, 1.7, 10.0, 17.0, 8.0],
            [17.0, 8.0, 0.05, 10.0, 0.1, 14.0],
        ]
    )
    _P = 1e-4 * np.array(
        [
            [1312, 1696, 5569, 124, 8283, 5886],
            [2329, 4135, 8307, 3736, 1004, 9991],
            [2348, 1451, 3522, 2883, 3047, 6650],
            [4047, 8828, 8732, 5743, 1091, 381],
        ]
    )

    def f(self, X: np.ndarray) -> np.ndarray:
        X = self.check_X(X)
        inner = ((X[:, None, :] - self._P[None, :, :]) ** 2 * self._A[None, :, :]).sum(-1)
        return (self._ALPHA[None, :] * np.exp(-inner)).sum(-1)

    @property
    def optimum_x(self) -> np.ndarray:
        return np.array([0.20169, 0.150011, 0.476874, 0.275332, 0.311652, 0.6573])

    @property
    def optimum_value(self) -> float:
        return 3.32237

class Ackley(Oracle):
    """Needle in a haystack. Tests exploration — BO can genuinely lose here."""

    name = "ackley"

    def __init__(self, dim: int = 6, domain: float = 32.768) -> None:
        self.dim = dim
        self._domain = domain

    def f(self, X: np.ndarray) -> np.ndarray:
        X = self.check_X(X)
        z = (X * 2.0 - 1.0) * self._domain
        d = self.dim
        t1 = -20.0 * np.exp(-0.2 * np.sqrt((z**2).sum(-1) / d))
        t2 = -np.exp(np.cos(2 * np.pi * z).sum(-1) / d)
        return -(t1 + t2 + 20.0 + np.e)

    @property
    def optimum_x(self) -> np.ndarray:
        return np.full(self.dim, 0.5)

    @property
    def optimum_value(self) -> float:
        return 0.0


class Levy(Oracle):
    """Multimodal, many local minima, a different structure from Ackley's.

    Standard domain [-10, 10]^d, global minimum 0 at z = (1, ..., 1). Negated for
    maximisation like the others; coded optimum sits at x = 0.55 in every coordinate,
    which is deliberately NOT the box centre -- see `UnitScaled` and Q36's Ackley
    confound for why that matters.
    """

    name = "levy"

    def __init__(self, dim: int = 6, domain: float = 10.0) -> None:
        self.dim = dim
        self._domain = domain

    def _z(self, X: np.ndarray) -> np.ndarray:
        return (X * 2.0 - 1.0) * self._domain

    def f(self, X: np.ndarray) -> np.ndarray:
        z = self._z(self.check_X(X))
        w = 1.0 + (z - 1.0) / 4.0
        head = np.sin(np.pi * w[..., 0]) ** 2
        mid = ((w[..., :-1] - 1.0) ** 2
               * (1.0 + 10.0 * np.sin(np.pi * w[..., :-1] + 1.0) ** 2)).sum(-1)
        tail = (w[..., -1] - 1.0) ** 2 * (1.0 + np.sin(2.0 * np.pi * w[..., -1]) ** 2)
        return -(head + mid + tail)

    @property
    def optimum_x(self) -> np.ndarray:
        return np.full(self.dim, (1.0 + self._domain) / (2.0 * self._domain))

    @property
    def optimum_value(self) -> float:
        return 0.0


class Rosenbrock(Oracle):
    """The curved valley. Ill-conditioned, non-separable, easy to reach and hard to finish.

    Domain [-2.048, 2.048]^d rather than the wider [-5, 10]: on the wide box the raw
    range exceeds 1e6, and a multiplicative noise model on a quantity that large is not
    comparable to any other family here.
    """

    name = "rosenbrock"

    def __init__(self, dim: int = 6, domain: float = 2.048) -> None:
        self.dim = dim
        self._domain = domain

    def f(self, X: np.ndarray) -> np.ndarray:
        z = (self.check_X(X) * 2.0 - 1.0) * self._domain
        a, b = z[..., :-1], z[..., 1:]
        return -(100.0 * (b - a**2) ** 2 + (a - 1.0) ** 2).sum(-1)

    @property
    def optimum_x(self) -> np.ndarray:
        return np.full(self.dim, (1.0 + self._domain) / (2.0 * self._domain))

    @property
    def optimum_value(self) -> float:
        return 0.0


class Embedded(Oracle):
    """Place a low-dimensional benchmark in a larger cube, the rest of the axes inert.

    WHY, and it is not a convenience
    ---------------------------------
    Q42 answers *"you built the landscape that gave you your answer"* with Hartmann6 --
    non-additive, deceptive, fifty years old, not ours. But ``Hartmann6`` is defined at
    d=6 only, so it ran at **two of the four cells** every other family ran at. The one
    family carrying the argument was missing both d=8 cells, and that was a property of
    the function rather than a decision anyone took.

    This closes the gap the way the project already builds its d=8 comparison. The Hill
    oracle holds ``n_active=4`` at **both** dimensions and draws which coordinates are
    active at random, so that d=6 against d=8 isolates **the cost of nuisance
    dimensions** rather than confounding dimension with active-count. ``Embedded`` gives
    a standard benchmark the same structure.

    The inert axes are **exactly** inert: the response does not move when they move, and
    ``software/tests/test_embedded_oracle.py`` asserts that as an equality rather than a
    tolerance. An approximately-inert axis would mean the arm measures a different
    function, not a nuisance dimension.

    The active subset is drawn from a recorded ``seed`` rather than taken as the first
    ``inner.dim`` axes, matching the Hill oracle's own convention. The designs used here
    are exchangeable in the coordinates, so it makes no distributional difference -- but
    "the interesting factors happen to be listed first" is a regularity worth not having.

    Args:
        inner: the oracle to embed.
        dim: the outer dimension. Must be at least ``inner.dim``.
        seed: fixes which outer coordinates are active.
        inert_at: where the inert axes sit in :attr:`optimum_x`. The response does not
            depend on them, so every value is an argmax; the centre is reported.
    """

    def __init__(self, inner: Oracle, *, dim: int, seed: int = 0,
                 inert_at: float = 0.5) -> None:
        if dim < int(inner.dim):
            raise ValueError(
                f"cannot embed a {inner.dim}-D oracle in {dim} dimensions; "
                f"dim must be at least {inner.dim}")
        self.inner = inner
        self.dim = int(dim)
        self.seed = int(seed)
        self.inert_at = float(inert_at)
        self.name = f"{inner.name}_in{dim}d"
        self.active = (np.arange(dim) if dim == int(inner.dim)
                       else np.sort(np.random.default_rng(seed).choice(
                           dim, int(inner.dim), replace=False)))

    def f(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(self.inner.f(self.check_X(X)[:, self.active]), dtype=float)

    @property
    def optimum_x(self) -> np.ndarray | None:
        inner_x = self.inner.optimum_x
        if inner_x is None:
            return None
        x = np.full(self.dim, self.inert_at, dtype=float)
        x[self.active] = np.asarray(inner_x, dtype=float)
        return x

    @property
    def optimum_value(self) -> float | None:
        return self.inner.optimum_value


class UnitScaled(Oracle):
    """Affinely rescale any oracle so its optimum is exactly 1.0 and its floor ~0.

    WHY THIS IS NECESSARY, not cosmetic
    -----------------------------------
    The observation model is ``y = f(x)(1 + eps) + eta`` -- noise PROPORTIONAL to the
    signal, because assay CV is what scales in the readout this project is calibrated to.
    Hartmann6 aside, every standard test function here has an optimum VALUE of exactly 0
    once negated. So the multiplicative term vanishes precisely at the optimum, and the
    single hardest region of the search becomes the quietest. That is an artefact of
    pairing a relative-noise model with a zero-valued optimum, and it makes those
    families spuriously easy in exactly the place the benchmark is measuring.

    Rescaling to ``optimum = 1`` puts every family on the Hill oracle's footing, so
    ``sigma_rel`` means the same thing across all five and the comparison is like for
    like. The floor is the minimum over a fixed Sobol sample -- deterministic given
    ``floor_samples`` and ``floor_seed``, and both are recorded in the results.

    Regret is then in units of the family's own range, which is what makes per-family
    regrets readable side by side. It does NOT make them poolable, and nothing here
    pools them.
    """

    def __init__(self, inner: Oracle, *, floor_samples: int = 65536,
                 floor_seed: int = 0) -> None:
        self.inner = inner
        self.dim = int(inner.dim)
        self.name = f"{inner.name}_unit"
        self.floor_samples = int(floor_samples)
        self.floor_seed = int(floor_seed)
        from scipy.stats import qmc
        pts = qmc.Sobol(d=self.dim, scramble=True, seed=floor_seed).random(floor_samples)
        vals = np.asarray(inner.f(pts), dtype=float)
        top = inner.optimum_value
        if top is None:
            top = float(vals.max())
        self._top = float(top)
        self._floor = float(vals.min())
        if not self._top > self._floor:
            raise ValueError(f"{inner.name}: optimum {self._top} is not above the "
                             f"sampled floor {self._floor}")

    @property
    def scale(self) -> float:
        return self._top - self._floor

    def f(self, X: np.ndarray) -> np.ndarray:
        return 1.0 - (self._top - np.asarray(self.inner.f(X), dtype=float)) / self.scale

    @property
    def optimum_x(self) -> np.ndarray | None:
        return self.inner.optimum_x

    @property
    def optimum_value(self) -> float:
        return 1.0


# --------------------------------------------------------------------------------
# Biphasic Hill factor mathematics
# --------------------------------------------------------------------------------
def factor_value(
    x: np.ndarray, xstar: np.ndarray, n_hill: np.ndarray, r: np.ndarray
) -> np.ndarray:
    """Peak-normalised biphasic factor. Peaks at exactly 1.0 at ``x = xstar``.

    ``h(x) = x^n / (EC50^n + x^n)``      activating, saturating
    ``g(x) = 1 / (1 + (x/IC50)^n)``      inhibitory
    ``ft   = h*g*((1+s)/s)^2``           with ``s = r^(n/2)``, ``r = IC50/EC50``

    With ``a = EC50^n``, ``b = IC50^n``, ``u = x^n`` the factor is ``ub/((a+u)(b+u))``,
    whose derivative numerator is ``ab - u^2``, so ``u* = sqrt(ab)`` and therefore
    ``xstar = sqrt(EC50*IC50)`` exactly. At the peak the raw value is ``s^2/(1+s)^2``,
    which is why the normaliser is ``((1+s)/s)^2``.

    Broadcasting: ``x`` is ``(N, d)``; ``xstar`` may be ``(d,)`` or ``(N, d)`` — the
    latter is how peak modulation makes the peak depend on the other coordinates.
    ``n_hill`` and ``r`` are ``(d,)``.
    """
    x = np.clip(np.asarray(x, dtype=float), _EPS, None)
    sq = np.sqrt(r)
    ec50 = xstar / sq
    ic50 = xstar * sq
    s = r ** (n_hill / 2.0)
    h = x**n_hill / (ec50**n_hill + x**n_hill)
    g = 1.0 / (1.0 + (x / ic50) ** n_hill)
    return h * g * ((1.0 + s) / s) ** 2


def depth_of_r(xstar: float | np.ndarray, n_hill: float | np.ndarray, r: float | np.ndarray):
    """``delta = 1 - ft(1)``: normalised decline from the peak to the upper box edge."""
    return 1.0 - factor_value(np.ones_like(np.asarray(xstar, dtype=float) * 1.0),
                              np.asarray(xstar, dtype=float),
                              np.asarray(n_hill, dtype=float),
                              np.asarray(r, dtype=float))


def delta_max(xstar, n_hill, r_min: float = 2.0):
    """Largest achievable depth, in closed form.

    ``delta`` is strictly decreasing in ``r`` over the admissible range, so the
    maximum over ``r in [r_min, r_cap]`` is always attained at ``r_min`` and the
    "1-D scan over r maximising delta" the spec describes is a no-op. Verified
    monotone on 3000 random draws from the stated ranges.

    The absolute supremum as ``r -> 1`` is ``((V-1)/(V+1))^2`` with ``V = xstar^-n``
    (see :func:`delta_supremum`); ``r_min`` sits below that.
    """
    return depth_of_r(xstar, n_hill, np.asarray(r_min, dtype=float))


def delta_supremum(xstar, n_hill):
    """Absolute feasibility bound on ``delta``, as ``r -> 1``.

    The inversion's discriminant is non-negative iff ``c >= 4V/(1+V)^2``, i.e.
    ``delta <= ((V-1)/(V+1))^2`` with ``V = xstar^-n``. Zero violations in 20,000
    random draws. Beyond this bound no real ``r`` produces the requested depth — a
    shallow-exponent factor peaking near the origin simply cannot decline that far
    by ``x = 1``.
    """
    V = np.asarray(xstar, dtype=float) ** (-np.asarray(n_hill, dtype=float))
    return ((V - 1.0) / (V + 1.0)) ** 2


def invert_r(xstar, n_hill, delta):
    """Derive the window ratio ``r = IC50/EC50`` from a requested depth.

    With ``V = xstar^-n`` and ``c = 1 - delta`` the defining equation is quadratic
    in ``s = r^(n/2)``::

        V(1-c)*s^2  +  [2V - c(1+V^2)]*s  +  V(1-c)  =  0

    The two roots multiply to 1 (a reciprocal pair); take the root exceeding 1.
    Verification case: ``(xstar=0.4, n=2, delta=0.414) -> s = 3.9917 -> r = 4``.

    Returns NaN where the requested depth is infeasible.
    """
    xstar = np.asarray(xstar, dtype=float)
    n_hill = np.asarray(n_hill, dtype=float)
    delta = np.asarray(delta, dtype=float)
    V = xstar ** (-n_hill)
    c = 1.0 - delta
    A = V * (1.0 - c)
    B = 2.0 * V - c * (1.0 + V * V)
    disc = B * B - 4.0 * A * A  # C == A, so 4AC == 4A^2
    out = np.full(np.broadcast(V, c).shape, np.nan, dtype=float)
    ok = (disc >= 0.0) & (A > 0.0)
    if np.any(ok):
        s = (-np.asarray(B)[ok] + np.sqrt(np.asarray(disc)[ok])) / (2.0 * np.asarray(A)[ok])
        out[ok] = s ** (2.0 / np.broadcast_to(n_hill, out.shape)[ok])
    return out if out.shape else float(out)


# --------------------------------------------------------------------------------
# Instance
# --------------------------------------------------------------------------------
@dataclass
class HillInstance:
    """One sampled landscape. Everything needed to rebuild it exactly."""

    dim: int
    seed: int
    oracle_version: str
    interaction: InteractionMode
    # sampled
    xstar: np.ndarray            # (d,)
    n_hill: np.ndarray           # (d,)
    delta: np.ndarray            # (d,)
    weights: np.ndarray          # (d,) sums to 1
    # derived
    r: np.ndarray                # (d,)
    ec50: np.ndarray             # (d,)
    ic50: np.ndarray             # (d,)
    delta_max_achieved: np.ndarray   # (d,)
    #: (d,) bool. True for the dominant factors. Inert factors still have a genuine
    #: interior peak; they simply carry little weight, so pushing them to a bound costs
    #: almost nothing. That is realistic, not a defect -- Hall/Ogle's own optimum sits
    #: at zero for laminin-111 and laminin-511, i.e. on the boundary in those two.
    active_mask: np.ndarray | None = None
    # interaction params (exactly one is populated)
    gamma: np.ndarray | None = None      # (d, d) peak modulation
    pairs: tuple[tuple[int, int], ...] = ()
    beta: np.ndarray | None = None       # (k,) product form
    k_pairs: int = 0
    # cached, filled by the generator
    optimum_x: np.ndarray | None = None
    optimum_value: float | None = None
    true_depth: float | None = None
    formula_depth: float | None = None
    n_factor_resamples: int = 0

    @property
    def active_idx(self) -> np.ndarray:
        """Indices of the dominant factors; all of them if no mask was set."""
        if self.active_mask is None:
            return np.arange(self.dim)
        return np.flatnonzero(self.active_mask)

    @property
    def influence_ratio(self) -> float:
        """Mean active weight / mean inert weight. 1.0 means ARD has nothing to find."""
        if self.active_mask is None or self.active_mask.all():
            return 1.0
        return float(self.weights[self.active_mask].mean()
                     / self.weights[~self.active_mask].mean())

    @property
    def instance_id(self) -> str:
        """Hash of (dim, seed, oracle_version). Stable identity across runs."""
        payload = f"{self.dim}|{self.seed}|{self.oracle_version}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def sidecar(self) -> dict:
        d = {}
        for key, val in asdict(self).items():
            if isinstance(val, np.ndarray):
                d[key] = val.tolist()
            elif isinstance(val, tuple):
                d[key] = [list(t) for t in val]
            else:
                d[key] = val
        d["instance_id"] = self.instance_id
        return d


def make_oracle_version(
    *,
    interaction: InteractionMode,
    accept_floor: float,
    formula_prefloor: float,
    xstar_range: tuple[float, float],
    n_range: tuple[float, float],
    u_range: tuple[float, float],
    w_range: tuple[float, float],
    gamma_max: float,
    beta_range: tuple[float, float],
    r_min: float,
    r_cap: float,
    accept_on: str,
    n_active: int | None,
    active_share: float,
) -> str:
    """Version string hashing the construction AND the acceptance parameters.

    The acceptance parameters are in here deliberately. Rejections consume RNG draws,
    so the seed -> instance map depends on the acceptance rule; a threshold change
    without a version bump silently redefines every instance_id.
    """
    payload = json.dumps(
        {
            "family": ORACLE_FAMILY,
            "interaction": interaction,
            "accept_floor": accept_floor,
            "formula_prefloor": formula_prefloor,
            "xstar_range": list(xstar_range),
            "n_range": list(n_range),
            "u_range": list(u_range),
            "w_range": list(w_range),
            "gamma_max": gamma_max,
            "beta_range": list(beta_range),
            "r_min": r_min,
            "r_cap": r_cap,
            "accept_on": accept_on,
            "n_active": n_active,
            "active_share": active_share,
        },
        sort_keys=True,
    )
    return f"{ORACLE_FAMILY}+{hashlib.sha256(payload.encode()).hexdigest()[:12]}"


# --------------------------------------------------------------------------------
# The oracle
# --------------------------------------------------------------------------------
class HillOracle(Oracle):
    """Biphasic Hill landscape built from a :class:`HillInstance`."""

    def __init__(self, inst: HillInstance) -> None:
        self.inst = inst
        self.dim = inst.dim
        self.name = f"hill-d{inst.dim}-{inst.instance_id}"

    # -- factor level, before any interaction ------------------------------------
    def base_factors(self, X: np.ndarray) -> np.ndarray:
        """``(n, d)`` unmodulated factor values, each in [0, 1]."""
        return factor_value(X, self.inst.xstar, self.inst.n_hill, self.inst.r)

    def _modulated_peaks(self, X: np.ndarray) -> np.ndarray:
        """``(n, d)`` effective peak locations under cross-modulation.

        ``m_i(x) = exp( (1/k) * sum_j gamma_ij * (ft0_j(x_j) - 1/2) )``

        The modulation reads the *unmodulated* factor values, which is what breaks
        the circularity — otherwise ``ft_i`` would depend on ``ft_j`` which depends
        on ``ft_i``. ``r`` and ``n`` are untouched, so ``s`` is untouched and the
        peak-normalisation constant still puts the peak at exactly 1.
        """
        gamma = self.inst.gamma
        if gamma is None:
            raise ValueError("peak_modulation requires gamma")
        base = self.base_factors(X)
        m = np.exp((base - 0.5) @ gamma.T / self.inst.k_pairs)
        return self.inst.xstar * m

    def f(self, X: np.ndarray) -> np.ndarray:
        X = np.clip(self.check_X(X), 0.0, 1.0)
        inst = self.inst
        if inst.interaction == "peak_modulation":
            peaks = self._modulated_peaks(X)
            ft = factor_value(X, peaks, inst.n_hill, inst.r)
            return (inst.weights * ft).sum(-1)
        # product form (v6) — retained for the pre-flight comparison only
        ft = self.base_factors(X)
        out = (inst.weights * ft).sum(-1)
        if inst.beta is None:
            raise ValueError("product interaction requires beta")
        for (i, j), b in zip(inst.pairs, inst.beta):
            out = out + b * ft[:, i] * ft[:, j] / inst.k_pairs
        return out

    # -- optimum ------------------------------------------------------------------
    def fixed_point_optimum(self, iters: int = 500, tol: float = 1e-15) -> np.ndarray:
        """``(d,)`` optimum by iterating ``x <- xstar * m(x)``.

        At the fixed point every factor sits exactly at its own (modulated) peak, so
        every ``ft_i = 1`` and ``f = sum w_i = 1`` exactly. Converges in ~18
        iterations at gamma=1. Peak-modulation mode only.
        """
        if self.inst.interaction != "peak_modulation":
            raise ValueError("fixed_point_optimum requires peak_modulation")
        x = self.inst.xstar.copy()
        for _ in range(iters):
            xn = np.clip(self._modulated_peaks(x[None, :])[0], _EPS, 1.0)
            if np.abs(xn - x).max() < tol:
                return xn
            x = xn
        return x

    def locate_optimum(self, n_restarts: int = 40, seed: int = 0) -> tuple[np.ndarray, float]:
        """``(d,) , float`` global maximum, by multistart L-BFGS-B.

        Seeded from the analytic/fixed-point target *and* from random starts. The
        analytic seed alone is not safe: under the product interaction a negative
        coordinate bracket moves that coordinate's optimum to a box edge, and a
        search started at ``x*`` converges to a local max, silently caching an
        optimum below the true one.
        """
        rng = np.random.default_rng(seed)
        starts = [self.inst.xstar]
        if self.inst.interaction == "peak_modulation":
            starts.append(self.fixed_point_optimum())
        starts.extend(rng.uniform(0, 1, (n_restarts, self.dim)))
        best_x = np.clip(self.inst.xstar, 0.0, 1.0)
        best_v = -np.inf
        for s0 in starts:
            res = minimize(
                lambda z: -float(self.f(np.clip(z, 0, 1)[None, :])[0]),
                np.clip(s0, _EPS, 1.0),
                bounds=[(0.0, 1.0)] * self.dim,
                method="L-BFGS-B",
            )
            if -res.fun > best_v:
                best_v, best_x = -res.fun, np.clip(res.x, 0.0, 1.0)
        return best_x, float(best_v)

    def boundary_maximum(
        self, n_restarts: int = 6, seed: int = 0, active_only: bool = True
    ) -> float:
        """Largest ``f`` on the box boundary — face-constrained searches.

        ``active_only`` restricts the faces to the dominant coordinates. This is the
        whole point of the active/inert split: an inert factor can be pushed to a bound
        at negligible cost, so including its faces would make the measured depth equal
        ``min_i w_i*delta_i`` over ALL i and cap it at ``1/d`` again — which is exactly
        what makes sigma_rel=0.25 unreachable at d=8. Restricting to active faces asks
        the question that matters: is the optimum measurably better than the best point
        reachable by moving a factor that actually does something?
        """
        rng = np.random.default_rng(seed)
        best = -np.inf
        faces = self.inst.active_idx if active_only else np.arange(self.dim)
        for i in faces:
            for level in (0.0, 1.0):
                bounds = [(0.0, 1.0)] * self.dim
                bounds[i] = (level, level)
                for s0 in rng.uniform(0, 1, (n_restarts, self.dim)):
                    s0 = s0.copy()
                    s0[i] = level
                    res = minimize(
                        lambda z: -float(self.f(np.clip(z, 0, 1)[None, :])[0]),
                        s0,
                        bounds=bounds,
                        method="L-BFGS-B",
                    )
                    best = max(best, -res.fun)
        return float(best)

    def true_depth(self, seed: int = 0, active_only: bool = True) -> float:
        """``f(x_opt) - max_boundary f`` over active faces. Claim 1's tolerance basis.

        This is computed, not taken from the closed form ``min_i w_i*delta_i``. That
        formula is derived for the zero-interaction case and, applied to instances
        with interactions, overstates the true depth by a median 28% (5th percentile
        -76%) — so a floor placed on it certifies a depth the instance does not have.
        """
        _, vopt = self.locate_optimum(seed=seed)
        return vopt - self.boundary_maximum(seed=seed, active_only=active_only)

    @property
    def optimum_x(self) -> np.ndarray | None:
        return self.inst.optimum_x

    @property
    def optimum_value(self) -> float | None:
        return self.inst.optimum_value


# --------------------------------------------------------------------------------
# Instance sampling
# --------------------------------------------------------------------------------
@dataclass(frozen=True)
class SamplerConfig:
    """Draws and acceptance rule for the instance ensemble.

    ``accept_on`` selects the acceptance criterion:

    ``"true_depth"`` (default) — accept on the numerically computed
    ``f(x_opt) - max_boundary f``. This is what the floor is *meant* to guarantee.

    ``"formula"`` — accept on ``min_i w_i*delta_i``, the v6 rule. Kept because the
    v6 acceptance rate is a required pre-flight number, and because the closed form
    is only valid at zero interaction: with interactions it overstates true depth by
    a median 28%, so a floor on it certifies a depth the instance does not have.

    ``draw_order`` selects the sampler:

    ``"w_first"`` (default) — draw the weights, then resample ``(xstar, n)`` per
    factor until ``delta_max >= formula_prefloor/w_i``, then draw ``delta`` inside
    the feasible interval. Acceptance on the formula is then satisfied by
    construction and the only truncation is factor-local and reportable.

    ``"delta_first"`` — the v6 order: draw everything, then reject whole instances.
    Measured acceptance 6.5% at d=6 and 0.104% at d=8, with the accepted ensemble a
    silent truncation of the stated (xstar, n) marginals.
    """

    accept_floor: float = 0.045
    #: Cheap pre-filter on the closed form. Inflated above accept_floor because the
    #: formula runs ~28% above true depth. 0.070 measured best: 62% / 35% pass at
    #: d=6 / d=8. Higher starts fighting the delta_max ceiling and gains nothing.
    formula_prefloor: float = 0.120
    xstar_range: tuple[float, float] = (0.25, 0.55)
    n_range: tuple[float, float] = (1.0, 3.0)
    u_range: tuple[float, float] = (0.55, 0.90)
    w_range: tuple[float, float] = (0.75, 1.25)
    gamma_max: float = 1.0
    beta_range: tuple[float, float] = (-0.4, 0.6)
    r_min: float = 2.0
    r_cap: float = 8.0
    #: Number of dominant factors. ``None`` makes every factor active (the v7 ensemble).
    #: Four at BOTH dimensions on purpose: holding the active subspace fixed makes the
    #: d=6 vs d=8 comparison measure the cost of NUISANCE DIMENSIONS, which is the real
    #: question -- you do not know in advance which factors matter. Scaling actives with
    #: d would confound dimension with active-count.
    n_active: int | None = 4
    #: Fraction of total weight carried by the active factors.
    active_share: float = 0.90
    interaction: InteractionMode = "peak_modulation"
    accept_on: Literal["true_depth", "formula"] = "true_depth"
    draw_order: Literal["w_first", "delta_first"] = "w_first"
    max_factor_resamples: int = 2000

    def version(self) -> str:
        return make_oracle_version(
            interaction=self.interaction,
            accept_floor=self.accept_floor,
            formula_prefloor=self.formula_prefloor,
            xstar_range=self.xstar_range,
            n_range=self.n_range,
            u_range=self.u_range,
            w_range=self.w_range,
            gamma_max=self.gamma_max,
            beta_range=self.beta_range,
            r_min=self.r_min,
            r_cap=self.r_cap,
            accept_on=self.accept_on,
            n_active=self.n_active,
            active_share=self.active_share,
        )


def _draw_pairs(rng: np.random.Generator, dim: int, k: int) -> tuple[tuple[int, int], ...]:
    """``k`` distinct unordered factor pairs, disjoint where possible."""
    idx = rng.permutation(dim)
    pairs = [(int(idx[2 * i]), int(idx[2 * i + 1])) for i in range(min(k, dim // 2))]
    while len(pairs) < k:
        i, j = rng.choice(dim, 2, replace=False)
        pairs.append((int(i), int(j)))
    return tuple(pairs)


def propose_instance(dim: int, seed: int, cfg: SamplerConfig) -> HillInstance | None:
    """Draw one candidate instance. Returns ``None`` if per-factor sampling fails.

    Does *not* evaluate the acceptance criterion — :func:`generate_ensemble` does
    that, so the expensive numerical depth is only paid once per candidate.
    """
    rng = np.random.default_rng(seed)
    k = int(np.ceil(dim / 2))
    version = cfg.version()

    n_act = dim if cfg.n_active is None else min(cfg.n_active, dim)
    active_mask = np.zeros(dim, dtype=bool)
    active_mask[rng.choice(dim, n_act, replace=False)] = True
    weights = np.empty(dim)
    wa = rng.uniform(*cfg.w_range, n_act)
    weights[active_mask] = wa / wa.sum() * (1.0 if n_act == dim else cfg.active_share)
    if n_act < dim:
        wi = rng.uniform(*cfg.w_range, dim - n_act)
        weights[~active_mask] = wi / wi.sum() * (1.0 - cfg.active_share)

    xstar = np.empty(dim)
    n_hill = np.empty(dim)
    delta = np.empty(dim)
    resamples = 0

    if cfg.draw_order == "w_first":
        # Per-factor floor: what THIS factor must contribute for min_i w_i*delta_i
        # to clear the pre-floor. Small weights demand deep factors.
        # Only the active factors must clear the depth floor. An inert factor is
        # allowed to be shallow -- that is what "inert" means.
        need = np.where(active_mask, cfg.formula_prefloor / weights, 0.0)
        for i in range(dim):
            # The factor must admit a NON-EMPTY sampling interval [need_i, u_hi*dmax],
            # not merely dmax >= need_i. Requiring only the latter admits factors whose
            # interval is empty and silently kills the whole instance.
            for _ in range(cfg.max_factor_resamples):
                a = rng.uniform(*cfg.xstar_range)
                b = rng.uniform(*cfg.n_range)
                dmax = float(delta_max(a, b, cfg.r_min))
                if cfg.u_range[1] * dmax >= need[i]:
                    xstar[i], n_hill[i] = a, b
                    break
                resamples += 1
            else:
                return None
            lo = need[i]
            hi = cfg.u_range[1] * float(delta_max(xstar[i], n_hill[i], cfg.r_min))
            delta[i] = lo + rng.uniform(0.0, 1.0) * (hi - lo)
    else:  # delta_first — the v6 order
        xstar[:] = rng.uniform(*cfg.xstar_range, dim)
        n_hill[:] = rng.uniform(*cfg.n_range, dim)
        dmax = delta_max(xstar, n_hill, cfg.r_min)
        delta[:] = rng.uniform(*cfg.u_range, dim) * dmax

    r = np.asarray(invert_r(xstar, n_hill, delta), dtype=float)
    if not np.all(np.isfinite(r)):
        return None
    # Enforce r_cap by clipping and recomputing delta, so the stated bound is real.
    # Left unenforced, the inversion exceeds it in 31% of draws (max observed 50).
    r = np.clip(r, cfg.r_min, cfg.r_cap)
    delta = np.asarray(depth_of_r(xstar, n_hill, r), dtype=float)

    inst = HillInstance(
        dim=dim,
        seed=seed,
        oracle_version=version,
        interaction=cfg.interaction,
        xstar=xstar,
        n_hill=n_hill,
        delta=delta,
        weights=weights,
        r=r,
        ec50=xstar / np.sqrt(r),
        ic50=xstar * np.sqrt(r),
        delta_max_achieved=np.asarray(delta_max(xstar, n_hill, cfg.r_min), dtype=float),
        k_pairs=k,
        n_factor_resamples=resamples,
        active_mask=active_mask,
        formula_depth=float((weights * delta)[active_mask].min()),
    )

    if cfg.interaction == "peak_modulation":
        gamma = np.zeros((dim, dim))
        for i, j in _draw_pairs(rng, dim, k):
            gamma[i, j] = rng.uniform(-cfg.gamma_max, cfg.gamma_max)
            gamma[j, i] = rng.uniform(-cfg.gamma_max, cfg.gamma_max)
        inst.gamma = gamma
    else:
        pairs = _draw_pairs(rng, dim, k)
        inst.pairs = pairs
        inst.beta = rng.uniform(*cfg.beta_range, len(pairs))
    return inst


def accept_instance(inst: HillInstance, cfg: SamplerConfig) -> tuple[bool, dict]:
    """Evaluate the acceptance criterion. Fills the cached optimum and true depth.

    Checks, in increasing cost order:

    1. **formula depth** ``min_i w_i*delta_i`` — free, and the v6 criterion.
    2. **cached optimum** by multistart, never by the analytic seed alone.
    3. **true depth** ``f(x_opt) - max_boundary f`` — the criterion that means what
       the floor claims to mean.
    4. **positivity** over a dense sample. Automatic under peak modulation
       (``f = sum w_i*ft_i >= 0``); a real check under the product form.
    """
    oracle = HillOracle(inst)
    diag: dict = {"formula_depth": inst.formula_depth}

    if cfg.accept_on == "formula":
        ok = bool(inst.formula_depth is not None and inst.formula_depth >= cfg.accept_floor)
        diag["criterion"] = "formula"
        if not ok:
            return False, diag

    xopt, vopt = oracle.locate_optimum(seed=inst.seed)
    inst.optimum_x, inst.optimum_value = xopt, vopt
    bmax = oracle.boundary_maximum(seed=inst.seed)
    inst.true_depth = float(vopt - bmax)
    diag["true_depth"] = inst.true_depth
    diag["optimum_value"] = vopt

    rng = np.random.default_rng(inst.seed + 90210)
    probe = rng.uniform(0.0, 1.0, (4000, inst.dim))
    fmin = float(oracle.f(probe).min())
    diag["min_f_sampled"] = fmin
    if fmin < 0.0:
        diag["reject"] = "positivity"
        return False, diag

    if cfg.accept_on == "true_depth":
        diag["criterion"] = "true_depth"
        if inst.true_depth < cfg.accept_floor:
            diag["reject"] = "depth"
            return False, diag
    return True, diag


def generate_ensemble(
    dim: int,
    n_instances: int,
    cfg: SamplerConfig,
    seed0: int = 0,
    max_candidates: int | None = None,
) -> tuple[list[HillInstance], dict]:
    """Draw ``n_instances`` accepted landscapes. Returns them plus an audit dict.

    The audit records the acceptance rate and the accepted-vs-nominal marginals of
    ``xstar`` and ``n``. Any acceptance rule truncates the stated draws; the point of
    reporting it is that the truncation is *declared* rather than silent.
    """
    if max_candidates is None:
        max_candidates = max(200 * n_instances, 20000)
    accepted: list[HillInstance] = []
    tried = 0
    rejects: dict[str, int] = {}
    xs_acc: list[np.ndarray] = []
    n_acc: list[np.ndarray] = []
    seed = seed0
    while len(accepted) < n_instances and tried < max_candidates:
        tried += 1
        inst = propose_instance(dim, seed, cfg)
        seed += 1
        if inst is None:
            rejects["factor_sampling"] = rejects.get("factor_sampling", 0) + 1
            continue
        ok, diag = accept_instance(inst, cfg)
        if not ok:
            key = diag.get("reject", "formula")
            rejects[key] = rejects.get(key, 0) + 1
            continue
        accepted.append(inst)
        xs_acc.append(inst.xstar)
        n_acc.append(inst.n_hill)

    audit = {
        "dim": dim,
        "requested": n_instances,
        "accepted": len(accepted),
        "candidates_tried": tried,
        "acceptance_rate": len(accepted) / tried if tried else 0.0,
        "rejections": rejects,
        "oracle_version": cfg.version(),
        "nominal_xstar_mean": float(np.mean(cfg.xstar_range)),
        "nominal_n_mean": float(np.mean(cfg.n_range)),
        "accepted_xstar_mean": float(np.concatenate(xs_acc).mean()) if xs_acc else None,
        "accepted_n_mean": float(np.concatenate(n_acc).mean()) if n_acc else None,
        "mean_factor_resamples": (
            float(np.mean([i.n_factor_resamples for i in accepted])) if accepted else None
        ),
        "true_depth_median": (
            float(np.median([i.true_depth for i in accepted if i.true_depth is not None]))
            if accepted else None
        ),
        "true_depth_min": (
            float(np.min([i.true_depth for i in accepted if i.true_depth is not None]))
            if accepted else None
        ),
        "n_active": cfg.n_active,
        "active_share": cfg.active_share,
        "influence_ratio_median": (
            float(np.median([i.influence_ratio for i in accepted])) if accepted else None
        ),
    }
    return accepted, audit


# --------------------------------------------------------------------------------
# Loading a committed ensemble
# --------------------------------------------------------------------------------
#: The ensemble both people run against. Version-stamped directories exist so that two
#: ensembles can never occupy one namespace -- the silent-mixing failure the version
#: field is for. Bump this only alongside ``ORACLE_FAMILY`` or a SamplerConfig change.
ENSEMBLE_VERSION = "biphasic-hill-v8+82f6db7c8f77"

#: **The config that generated what is on disk. Use this; do not rebuild it by hand.**
#:
#: A bare ``SamplerConfig()`` is NOT this object -- its ``accept_floor`` default is
#: 0.045, the v6 specification's value, while the shipped ensemble was generated at
#: 0.1083 (``3 * 0.25 / sqrt(48)``, the depth needed at the primary noise level).
#: Reconstructing the config by hand therefore produces a different ``oracle_version``
#: and hence different ``instance_id``s for landscapes that are numerically identical,
#: which is precisely the silent mismatch the version field exists to catch. It caught
#: it -- after one reported acceptance rate had already been measured at the wrong
#: floor. Asserted against ``ENSEMBLE_VERSION`` in the test suite.
SHIPPED_CONFIG = SamplerConfig(
    interaction="peak_modulation",
    accept_on="true_depth",
    draw_order="w_first",
    accept_floor=0.1083,
    formula_prefloor=0.120,
    gamma_max=1.0,
    n_active=4,
    active_share=0.90,
)

#: Repo-root-relative, so a clean clone finds the data without configuration.
DATA_ROOT = Path(__file__).resolve().parents[3] / "research" / "data" / "oracles"


def load_instance(path: str | Path) -> HillInstance:
    """Rebuild a :class:`HillInstance` from its JSON sidecar.

    One copy of this mapping, deliberately. If each lane wrote its own JSON-to-instance
    conversion the two would drift on some field nobody checks -- ``active_mask``'s
    dtype, say -- and both sides would compute confidently on different landscapes.

    Args:
        path: a sidecar written by :meth:`HillInstance.sidecar`.

    Returns:
        The instance, byte-for-byte equivalent to the one that was generated.
    """
    raw = json.loads(Path(path).read_text())
    kw: dict = {}
    for key, val in raw.items():
        if key == "instance_id":          # derived, not a field
            continue
        if key == "pairs":
            kw[key] = tuple(tuple(int(v) for v in t) for t in val)
        elif isinstance(val, list):
            kw[key] = np.asarray(val, dtype=float)
        else:
            kw[key] = val
    if kw.get("active_mask") is not None:
        kw["active_mask"] = kw["active_mask"].astype(bool)
    return HillInstance(**kw)


def load_ensemble(dim: int, version: str = ENSEMBLE_VERSION,
                  root: Path | None = None) -> list[HillInstance]:
    """All committed instances at one dimension, ordered by seed.

    Args:
        dim: 6 or 8.
        version: version-stamped directory name under ``research/data/oracles``.
        root: override the search root; defaults to the repo's ``research/data/oracles``.

    Returns:
        The instances, sorted by ``seed`` so iteration order is identical everywhere.

    Raises:
        FileNotFoundError: if the version directory is absent -- loudly, rather than
            returning an empty ensemble that would make every downstream loop a no-op.
    """
    base = (root or DATA_ROOT) / version / "sidecars"
    if not base.is_dir():
        raise FileNotFoundError(f"no committed ensemble at {base}")
    out = [load_instance(p) for p in sorted(base.glob("*.json"))]
    out = [i for i in out if i.dim == dim]
    if not out:
        raise FileNotFoundError(f"no d={dim} instances under {base}")
    return sorted(out, key=lambda i: i.seed)
