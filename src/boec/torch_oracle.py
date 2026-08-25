"""The bridge from A's numpy oracle to B's torch interfaces.

OWNERSHIP: Person A. Long-lived -- Phases 2 and 3 swap implementations in behind the
same interface.

------------------------------------------------------------------------------
WHY THIS IS A SEPARATE FILE
------------------------------------------------------------------------------

``oracles.py`` is deliberately pure numpy/scipy and imports no torch. That is a
property worth keeping rather than an accident: the landscape maths is the part that
survives into Phase 2 (a digitised lookup table) and Phase 3 (a human with a CSV),
neither of which should need a deep-learning framework installed to reason about a
dose-response curve. So the tensor boundary lives here, in one small file, and
everything numerical stays on the other side of it.

------------------------------------------------------------------------------
WHAT IT ANSWERS
------------------------------------------------------------------------------

Three questions for Experiment 4 (``boec.e4.Oracle``)::

    x_star     -> (d,)                where each ingredient's response peaks
    truth(X)   -> (n, 1)              the NOISELESS value. Scoring only, never fitting.
    observe(X) -> ((n, 1), (n, 1))    a noisy measurement and its noise estimate

and two for the campaign loop (``boec.campaign.Evaluator``)::

    evaluate(X) -> ((n, 1), (n, 1))   the same measurement, under the loop's name

Both protocols are *structural*, so nothing here inherits from B's code and neither
module has to exist before the other.

------------------------------------------------------------------------------
THE SILENT TRAPS THIS FILE IS RESPONSIBLE FOR
------------------------------------------------------------------------------

``Yvar`` is a **variance**, in **raw outcome units**. Returning a standard deviation is
the classic fixed-noise GP bug and produces calibration numbers that look entirely
plausible and are systematically wrong.

``Yvar`` is the **plug-in** estimate computed from the *observed* value, not the
analytic variance computed from the noiseless one. The analytic form is a function of
``f(x)``, from which ``|f(x)|`` is exactly recoverable -- returning it hands the model
the truth at every training point and corrupts E3. It is kept behind
``yvar_mode="analytic"`` as an ablation, and ``test_torch_oracle.py`` demonstrates the
leak rather than merely asserting it exists.

``truth`` must be noiseless. If it is not, E4's over-prediction picks up measurement
noise and the whole distribution widens for a reason unrelated to extrapolation.

**Gradients.** Nothing differentiates through this oracle -- ``metrics.py`` evaluates
``truth`` under ``torch.no_grad()`` at a single already-optimised point -- which is what
makes a numpy core safe here. If that ever changes, this file needs rewriting, not
patching.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import torch
from torch import Tensor

from boec.oracles import HillInstance, HillOracle, Oracle
from boec.seedbook import IndexedGaussianNoise

__all__ = ["BiphasicOracle", "TorchEvaluator"]

YvarMode = Literal["plugin", "analytic"]


def _plug_in_yvar(base: np.ndarray, sigma_rel: float, sigma_add: float) -> np.ndarray:
    """``yhat^2 * sigma_rel^2 + sigma_add^2``, floored at the assay's own noise floor.

    One definition, used by both classes here. The floor is ``sigma_add**2`` rather than
    a numerical epsilon -- see OPEN-QUESTIONS Q8. It is non-binding in Phase 1 by
    construction, since that value is the estimator's own infimum.
    """
    return np.maximum(base**2 * sigma_rel**2 + sigma_add**2, sigma_add**2)


class TorchEvaluator:
    """Wraps **any** numpy oracle as a torch ``Evaluator``, for E1 and the swap test.

    OPEN-QUESTIONS Q3. The campaign loop was built against Branin, Hartmann6 and Ackley,
    and the biphasic oracle swaps in later through the same interface. That swap being
    clean is not a convenience -- it is the evidence that the forward-compatibility
    design is real, and it is far cheaper to discover a break here than in Phase 2 when
    a lookup table has to take the same slot.

    **Orientation matters and is asserted in the tests.** B's campaign maximises. Branin
    and Hartmann6 are minimisation problems as usually written, so the implementations in
    ``oracles.py`` are already negated. If one were not, BO would faithfully find its
    worst point and E1 would "fail" for a reason having nothing to do with the optimizer.

    Args:
        oracle: any :class:`boec.oracles.Oracle` -- ``f(X: (n, d)) -> (n,)``.
        sigma_rel: relative noise on the observation model ``y = f(1 + eps) + eta``.
        sigma_add: additive noise floor.
        seed: fixes the noise draws.
    """

    def __init__(
        self,
        oracle: Oracle,
        *,
        sigma_rel: float = 0.10,
        sigma_add: float = 0.01,
        seed: int = 0,
        noise_source: IndexedGaussianNoise | None = None,
    ) -> None:
        self.oracle = oracle
        self.dim = int(oracle.dim)
        self.sigma_rel = float(sigma_rel)
        self.sigma_add = float(sigma_add)
        self.seed = int(seed)
        self.yvar_floor = float(sigma_add) ** 2
        self._rng = np.random.default_rng(seed)
        self.noise_source = noise_source
        self._next_index = 0

    def _check(self, X: Tensor) -> np.ndarray:
        if X.ndim != 2:
            raise ValueError(f"X must be (n, d); got {tuple(X.shape)}")
        if X.shape[1] != self.dim:
            raise ValueError(f"X has {X.shape[1]} factors; oracle has {self.dim}")
        return X.detach().double().cpu().numpy()

    def truth(self, X: Tensor) -> Tensor:
        """``(n, d) -> (n, 1)`` the noiseless value. Scoring only, never fitting."""
        y = self.oracle.f(self._check(X))
        return torch.from_numpy(np.asarray(y, dtype=float).reshape(-1, 1))

    def evaluate(self, X: Tensor) -> tuple[Tensor, Tensor]:
        """``(n, d) -> ((n, 1), (n, 1))`` a noisy measurement and its plug-in variance."""
        f = np.asarray(self.oracle.f(self._check(X)), dtype=float).reshape(-1, 1)
        if self.noise_source is not None:
            indices = torch.arange(self._next_index, self._next_index + f.shape[0])
            result = self.noise_source.observe(indices, torch.from_numpy(f))
            self._next_index += f.shape[0]
            return result
        eps = self._rng.normal(0.0, self.sigma_rel, size=f.shape)
        eta = self._rng.normal(0.0, self.sigma_add, size=f.shape)
        y = f * (1.0 + eps) + eta
        return torch.from_numpy(y), torch.from_numpy(
            _plug_in_yvar(y, self.sigma_rel, self.sigma_add))

    def state_dict(self) -> dict[str, int]:
        return {"next_index": self._next_index}

    def load_state_dict(self, state: dict[str, int]) -> None:
        self._next_index = int(state["next_index"])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"TorchEvaluator({self.oracle.name}, d={self.dim}, seed={self.seed})"


class BiphasicOracle:
    """One generated landscape, wearing the interfaces B's modules consume.

    Observation model ``y = f(x)*(1 + eps) + eta`` with ``eps ~ N(0, sigma_rel^2)`` and
    ``eta ~ N(0, sigma_add^2)``. The multiplicative term is there because assay CV --
    not absolute error -- is what scales in this readout, so variance grows with signal
    exactly as it does on a real plate.

    Args:
        instance: a landscape from ``boec.oracles.load_ensemble``.
        sigma_rel: relative noise. **0.25 is primary and 0.10 the optimistic bound**,
            reversing the spec: Hall/Ogle normalise every plate to a fibronectin control
            precisely because interexperimental variability is large, and report no CV
            for CD31 anywhere. Both levels run on the same ensemble, because the
            acceptance floor is noise-independent and frozen -- that is what keeps the
            0.10-vs-0.25 contrast a noise effect rather than an ensemble effect.
        sigma_add: additive noise floor.
        yvar_mode: ``"plugin"`` (default, correct) or ``"analytic"`` (ablation, leaks).
        seed: fixes the noise draws. Logged on every row per the house rules.

    Attributes:
        yvar_floor: ``sigma_add**2``. See OPEN-QUESTIONS Q8 -- the floor is the assay's
            own noise floor, not a numerical epsilon, so it is **non-binding in Phase 1
            by construction** (the plug-in's infimum is exactly this value) and exists
            to stop a Phase 2 lookup table or a Phase 3 human returning a zero variance
            that would make the GP interpolate one point exactly.
    """

    def __init__(
        self,
        instance: HillInstance,
        *,
        sigma_rel: float = 0.10,
        sigma_add: float = 0.01,
        yvar_mode: YvarMode = "plugin",
        seed: int = 0,
        noise_source: IndexedGaussianNoise | None = None,
    ) -> None:
        if yvar_mode not in ("plugin", "analytic"):
            raise ValueError(f"unknown yvar_mode {yvar_mode!r}")
        self.instance = instance
        self.dim = instance.dim
        self.sigma_rel = float(sigma_rel)
        self.sigma_add = float(sigma_add)
        self.yvar_mode: YvarMode = yvar_mode
        self.seed = int(seed)
        self.yvar_floor = float(sigma_add) ** 2
        self._core = HillOracle(instance)
        self._rng = np.random.default_rng(seed)
        self.noise_source = noise_source
        self._next_index = 0

    # -- identity ----------------------------------------------------------------
    @property
    def instance_id(self) -> str:
        """Hash of (dim, seed, oracle_version). Log it on every results row."""
        return self.instance.instance_id

    @property
    def x_star(self) -> Tensor:
        """``(d,)`` the **unmodulated** peak of each factor.

        Under peak modulation the *effective* peak is ``x*_i * m_i(x)``, so this is not
        where the joint optimum sits -- ``instance.optimum_x`` is. B's
        ``designs.sub_box_bounds`` builds ``[0, kappa*x*]`` from this value, and that box
        is only guaranteed to stop short of the optimum because the ensemble was measured
        to satisfy it (see ``test_the_effective_peak_never_falls_inside_the_training_box``).
        """
        return torch.from_numpy(np.asarray(self.instance.xstar, dtype=float))

    # -- the three questions -----------------------------------------------------
    def _check(self, X: Tensor) -> np.ndarray:
        if X.ndim != 2:
            raise ValueError(f"X must be (n, d); got {tuple(X.shape)}")
        if X.shape[1] != self.dim:
            raise ValueError(f"X has {X.shape[1]} factors; oracle has {self.dim}")
        return X.detach().double().cpu().numpy()

    def truth(self, X: Tensor) -> Tensor:
        """``(n, d) -> (n, 1)`` the noiseless response. **Scoring only, never fitting.**"""
        y = self._core.f(self._check(X))
        return torch.from_numpy(np.asarray(y, dtype=float).reshape(-1, 1))

    def observe(self, X: Tensor) -> tuple[Tensor, Tensor]:
        """``(n, d) -> ((n, 1), (n, 1))`` a noisy measurement and its variance.

        The variance is the plug-in ``yhat^2*sigma_rel^2 + sigma_add^2``, floored at
        ``yvar_floor``, in raw outcome units.

        Known bias, recorded so nobody debugs it twice: ``E[y_obs^2] =
        f^2*(1 + sigma_rel^2) + sigma_add^2``, so the plug-in over-estimates by ~1% at
        ``sigma_rel = 0.10`` and ~6% at 0.25, and a point that drew high noise gets a
        larger Yvar and is down-weighted. Real labs do exactly this, so it is the right
        default -- **if calibration shows mild over-coverage at the higher noise level,
        this is the first candidate, not a bug.**
        """
        f = np.asarray(self._core.f(self._check(X)), dtype=float).reshape(-1, 1)
        if self.noise_source is not None:
            indices = torch.arange(self._next_index, self._next_index + f.shape[0])
            result = self.noise_source.observe(indices, torch.from_numpy(f))
            self._next_index += f.shape[0]
            return result
        eps = self._rng.normal(0.0, self.sigma_rel, size=f.shape)
        eta = self._rng.normal(0.0, self.sigma_add, size=f.shape)
        y = f * (1.0 + eps) + eta

        base = y if self.yvar_mode == "plugin" else f
        yvar = np.maximum(base**2 * self.sigma_rel**2 + self.sigma_add**2, self.yvar_floor)
        return torch.from_numpy(y), torch.from_numpy(yvar)

    # -- the campaign loop's name for the same thing ------------------------------
    def evaluate(self, X: Tensor) -> tuple[Tensor, Tensor]:
        """``(n, d) -> ((n, m), (n, m))``. ``boec.campaign.Evaluator``'s one method."""
        return self.observe(X)

    def state_dict(self) -> dict[str, int]:
        return {"next_index": self._next_index}

    def load_state_dict(self, state: dict[str, int]) -> None:
        self._next_index = int(state["next_index"])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"BiphasicOracle(d={self.dim}, id={self.instance_id}, "
            f"sigma_rel={self.sigma_rel}, yvar_mode={self.yvar_mode!r})"
        )
