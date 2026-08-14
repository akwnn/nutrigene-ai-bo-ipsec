"""The one-shot spread+GP arm, extracted verbatim so it can run off the Hill oracle.

Registered as Q53. The arm was written inline at ``run_q52_budget_to_target.py:201-211`` and
measured there on the Hill family only: a Latin hypercube of ``n`` points, evaluated **once**,
one GP fit, and a recommendation read off the posterior mean's argmax. One round, where qLogEI
at the same budget spends ten.

**Nothing here is new.** The body of :func:`spread_gp_once` is the Q52 code path with the
``BiphasicOracle`` swapped for any object carrying ``evaluate`` and ``truth`` — which is what
Q42's external families need, since they arrive as ``TorchEvaluator`` rather than
``BiphasicOracle``. ``tests/test_spread_gp.py`` gates the extraction against the **committed**
Q52 grid rather than against a regeneration, because a gate that compares one fresh run to
another can only report that the code agrees with itself (D12).

Two constants are load-bearing and are not parameters by accident: ``n_restarts=20`` and
``raw_samples=4096`` are what Q42's BO arm uses, so the two arms' rule-C figures are produced by
the same locator at the same effort. Changing either makes the comparison something else.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import torch
from torch import Tensor

from boec.diagnostics import reported_best_curve
from boec.metrics import constrained_argmax
from boec.optimizers import lhs_design
from boec.surrogate import build_gp

#: Matched to Q42's BO arm (`run_q42_families.py:87-88`). Not tunable — see module docstring.
N_RESTARTS = 20
RAW_SAMPLES = 4096


def spread_gp_once(
    evaluator,
    bounds: Tensor,
    *,
    truth: Callable[[Tensor], Tensor],
    optimum_value: float,
    n: int,
    seed: int,
    n_restarts: int = N_RESTARTS,
    raw_samples: int = RAW_SAMPLES,
) -> tuple[float, float]:
    """Run the arm once and return ``(rule_a, rule_c)`` as regret against ``optimum_value``.

    ``rule_a`` is the true value at the **observed** argmax — :func:`reported_best_curve`, never
    ``np.maximum.accumulate`` over the noiseless values, which is oracle-best and is the error
    that voided E2's first run and later reappeared as D20.

    ``rule_c`` is the true value at the argmax of the fitted GP's posterior mean, located with
    the same solver and effort Q42 gives its BO arm.
    """
    X = lhs_design(bounds, n, seed=seed)
    Y, V = evaluator.evaluate(X)

    rule_a = optimum_value - float(reported_best_curve(truth(X), Y)[-1])

    model = build_gp(X, Y, V, bounds)

    def posterior_mean(Z: Tensor, _m=model) -> Tensor:
        with torch.no_grad():
            return _m.posterior(Z).mean

    x_star, _, _ = constrained_argmax(posterior_mean, bounds, n_restarts=n_restarts,
                                      raw_samples=raw_samples, seed=seed)
    rule_c = optimum_value - float(truth(x_star.reshape(1, -1)))
    return rule_a, rule_c


def design_average(values: Sequence[float]) -> tuple[float, float]:
    """Mean over independent design draws, and the spread across them.

    The spread is the point of this function. One LHS draw of the same size at the same cell
    gave 0.1778 in Q47 and 0.1539 in Q52 — a gap of 0.0239, about one design SD (Q48/D16). A
    single-draw number from this arm is not quotable, so the SD travels with the mean.

    A single draw returns ``nan`` rather than ``0.0``: zero would read as *"the lottery does not
    bite here"*, which is the exact opposite of what one draw establishes.
    """
    v = np.asarray(list(values), dtype=float)
    if v.size == 0:
        raise ValueError("no design draws to average")
    sd = float(np.std(v, ddof=1)) if v.size > 1 else float("nan")
    return float(v.mean()), sd


def within_design_noise(*, diff: float, design_sd: float) -> bool:
    """Q53 §3's registered stopping rule, fixed before any number existed.

    A family-cell contrast smaller in magnitude than that cell's design SD is reported as
    *within design noise* and is not called a result — whichever direction it points. Written as
    a function so it is applied to every cell identically rather than recalled selectively.
    """
    if not np.isfinite(design_sd):
        raise ValueError(
            "design_sd is undefined (a single draw), so the rule cannot fire; "
            "run more draws rather than treating the contrast as clean")
    return abs(diff) < design_sd
