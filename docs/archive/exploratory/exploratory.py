"""EXPLORATORY BRANCH ONLY — see EXPLORATORY.md at the repo root.

**Nothing in this module is registered, and no number produced with it may enter
a results document without being re-run clean under a registration.**

Three modifications, each isolating one structural difference between the GP and
the second-order polynomial that beats it at d=6, sigma_rel=0.25. The question
is mechanism, not rescue: what does the polynomial have that this GP does not.
"""

from __future__ import annotations

import math

import torch
from gpytorch.means import Mean
from torch import Tensor

__all__ = ["QuadraticMean", "ReplicatedEvaluator"]


class QuadraticMean(Mean):
    """A full second-order trend, fitted jointly with the kernel.

    This is universal kriging: a parametric trend AND distance-based
    uncertainty, where `ConstantMean` gives only the second.

    **Why this is the interesting arm.** The DoE arm's advantage may be nothing
    to do with sequential design and everything to do with its model. A
    second-order surface pools all n observations into 1 + d + d + d(d-1)/2
    coefficients -- 28 at d=6, the same 28 the DoE arm fits -- and that pooling
    is heavy implicit averaging, which is exactly what helps at low
    signal-to-noise. `ConstantMean` reverts to a single constant away from data
    and pools nothing.

    **The weak prior is a deviation and is declared.** 28 coefficients against
    14 opening observations is not identifiable from the marginal likelihood
    alone; without regularisation the fit wanders and `fit_gpytorch_mll` retries
    into nonsense. A unit normal prior on standardised outcomes is the mildest
    thing that makes the arm runnable. It is a difference from the polynomial
    arm, which fits by unregularised least squares, and any comparison has to
    say so.

    Args:
        d: number of inputs.
        prior_sd: standard deviation of the normal prior on every coefficient,
            in standardised outcome units. `None` disables it.
    """

    def __init__(self, d: int, prior_sd: float | None = 1.0) -> None:
        super().__init__()
        self.d = int(d)
        self._iu, self._ju = torch.triu_indices(self.d, self.d, offset=1)
        self.register_parameter("bias", torch.nn.Parameter(torch.zeros(1, dtype=torch.double)))
        self.register_parameter(
            "linear_weights",
            torch.nn.Parameter(torch.zeros(self.d, dtype=torch.double)))
        self.register_parameter(
            "square_weights",
            torch.nn.Parameter(torch.zeros(self.d, dtype=torch.double)))
        self.register_parameter(
            "cross_weights",
            torch.nn.Parameter(torch.zeros(self._iu.numel(), dtype=torch.double)))
        if prior_sd is not None:
            from gpytorch.priors import NormalPrior
            for name in ("bias", "linear_weights", "square_weights", "cross_weights"):
                self.register_prior(
                    f"{name}_prior", NormalPrior(0.0, prior_sd),
                    lambda m, n=name: getattr(m, n))

    def forward(self, x: Tensor) -> Tensor:
        lin = x @ self.linear_weights.to(x)
        sq = (x * x) @ self.square_weights.to(x)
        cross = (x[..., self._iu] * x[..., self._ju]) @ self.cross_weights.to(x)
        return self.bias.to(x) + lin + sq + cross


class ReplicatedEvaluator:
    """Spend `r` evaluations on every condition and hand back the average.

    **The budget is unchanged and the trade is the experiment.** At r=2 the
    campaign sees 24 distinct conditions instead of 48, each read at an
    effective noise of sigma/sqrt(2). Fewer places, cleaner reads.

    **The confound is stated rather than designed away: the number of distinct
    conditions is NOT held fixed, and at a fixed budget no design can hold it
    fixed.** Any difference in outcome is attributable to the trade as a whole,
    not to precision alone.

    Central composite designs carry replicated centre points by construction,
    so the DoE arm already has some of this; and Binois, Huang, Gramacy &
    Ludkovski (Technometrics 2019) show replication benefits GP surrogates at
    low signal-to-noise. The source study averaged roughly 12 measurements per
    condition. This benchmark gives one.

    `r = 3` is infeasible at d=6: a 14-condition opening design would consume 42
    of the 48 evaluations.

    Attributes:
        n_evaluations: replicates actually spent, so the budget can be audited
            rather than trusted.
    """

    def __init__(self, evaluator, r: int = 1) -> None:
        if r < 1:
            raise ValueError(f"r must be at least 1, got {r}")
        self.evaluator = evaluator
        self.r = int(r)
        self.n_evaluations = 0

    def evaluate(self, X: Tensor) -> tuple[Tensor, Tensor]:
        ys, vs = [], []
        for _ in range(self.r):
            y, v = self.evaluator.evaluate(X)
            if v is None:
                raise ValueError(
                    "the wrapped evaluator returned no noise estimate; contract "
                    "item 5 requires it always be supplied"
                )
            ys.append(y)
            vs.append(v)
            self.n_evaluations += int(X.shape[0])
        # the mean of r independent reads, and its variance: plug_in / r
        return torch.stack(ys).mean(dim=0), torch.stack(vs).mean(dim=0) / self.r

    # pass-throughs so this can stand in for the oracle wherever one is expected
    def truth(self, X: Tensor) -> Tensor:
        return self.evaluator.truth(X)

    @property
    def x_star(self):
        return self.evaluator.x_star


def replicated_plan(budget_evaluations: int, r: int, d: int) -> tuple[int, int, int]:
    """Conditions, opening size and batch size for a replicated arm.

    Keeps total EVALUATIONS at `budget_evaluations` for every r, so the arms are
    comparable at the thing the practitioner pays for.

    Returns:
        ``(n_conditions, n_init_conditions, q_conditions)``.
    """
    if budget_evaluations % r:
        raise ValueError(
            f"budget {budget_evaluations} is not divisible by r={r}; the arm "
            "would not spend the same number of evaluations as the others"
        )
    n_cond = budget_evaluations // r
    n_init = math.ceil((2 * d + 2) / r)
    q = max(1, 4 // r)
    return n_cond, n_init, q
