"""The registered `doe_repeat` budget policy — Q52 §2.

The classical pipeline cannot spend a budget other than 48: ``STAGE1_FRACTION`` is a
table and not a formula, and :func:`boec.doe.run_doe_arm` raises rather than spending 47
or 49. Q52 §2 registers the policy this module implements, and it was fixed in
``docs/OPEN-QUESTIONS.md`` before this file existed:

    Run the unmodified 48-evaluation pipeline with a fresh seed, repeatedly, carrying
    the best result forward; stop when the next full pipeline would exceed the cap. At
    a cap of 200 that is four complete pipelines = 192 evaluations, and the remaining 8
    are deliberately not spent -- a partial pipeline is not the method.

**Rule A is recomputed here, and NOT read from ``DoEResult.curve_true``.** That field is
``np.maximum.accumulate`` over the *noiseless* values, i.e. **oracle-best** — the running
best true value among visited points, which credits an arm for a recipe it measured but
could not identify. That is the precise scoring error which voided E2's first run
(``docs/RESULTS.md`` "VOID RUNS"). Rule A is the true value at the running *observed*
argmax, which is :func:`boec.diagnostics.reported_best_curve`, and on this arm the two
differ by a mean of +0.035 regret at d=6 σ=0.25. Using the audited function is not a
style preference; it is the difference between this arm's registered estimand and a
voided one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import Tensor

from boec.diagnostics import reported_best_curve
from boec.doe import run_doe_arm
from boec.metrics import constrained_argmax
from boec.rsm import fit_second_order

__all__ = ["DoERepeatResult", "run_doe_repeat"]

#: The pipeline's fixed size. Not a parameter: Q24 fixes 20+27+1 at both d=6 and d=8.
PIPELINE_BUDGET = 48

_N_RESTARTS = 20
_RAW_SAMPLES = 4096


@dataclass(frozen=True)
class DoERepeatResult:
    """One `doe_repeat` arm.

    Attributes:
        checkpoints: the budgets at which this arm can answer — multiples of 48 only.
            Every other arm answers at the §2 grid's 8..200; this asymmetry is a
            property of the classical pipeline and is reported wherever the arrivals
            are, per the registration.
        n_pipelines: how many complete pipelines were run.
        evaluations_spent: ``48 * n_pipelines``. Deliberately below the cap when the
            cap is not a multiple of 48.
        seeds: the per-pipeline seeds, distinct by construction — repeating one seed
            would re-measure the same 48 points and buy nothing.
        rule_a: checkpoint -> regret at the running observed-argmax over every point
            measured so far. See the module docstring on why this is not
            ``curve_true``.
        rule_c_unconstrained: checkpoint -> regret at the chosen pipeline's stage-4
            recommendation, located over the kept factors' full range. Q41's primary.
        rule_c_constrained: checkpoint -> the same recommendation located within the
            region stage 2 actually explored.
        chosen_pipeline: checkpoint -> index of the pipeline whose stage-4
            confirmation measured best, which is the run a lab would keep.
        confirmation_y: each pipeline's measured confirmation value, in order.
    """

    checkpoints: tuple[int, ...]
    n_pipelines: int
    evaluations_spent: int
    seeds: tuple[int, ...]
    rule_a: dict[int, float]
    rule_c_unconstrained: dict[int, float]
    rule_c_constrained: dict[int, float]
    chosen_pipeline: dict[int, int]
    confirmation_y: tuple[float, ...]


def _lift(x_kept: Tensor, kept: list[int], held: dict[int, float], dim: int) -> Tensor:
    """Put a kept-factor recipe back into full coded space at the held levels."""
    full = torch.tensor([held.get(i, 0.0) for i in range(dim)], dtype=torch.double)
    full[kept] = x_kept.double().reshape(-1)
    return full.unsqueeze(0)


def run_doe_repeat(
    evaluator,
    bounds: Tensor,
    *,
    truth,
    optimum_value: float,
    cap: int,
    seed: int,
    seeds: tuple[int, ...] | None = None,
    _confirmation_override: tuple[float, ...] | None = None,
) -> DoERepeatResult:
    """Run the registered repeat-and-keep-the-best policy up to ``cap``.

    Args:
        evaluator: anything with ``evaluate(X) -> (Y, Yvar)``.
        bounds: ``(2, d)`` the full coded space.
        truth: the **noiseless** oracle. Scoring only.
        optimum_value: the instance's true optimum, for regret.
        cap: the registered evaluation cap. Floors to whole pipelines.
        seed: fallback first seed, used only when ``seeds`` is not given.
        seeds: the per-pipeline seeds. Q52 §2 registers these as
            ``H(instance_id, 7000 + repeat_index)`` — a hash of the repeat's own
            coordinates, never a global counter, so a repeat is reproducible
            independently of how many other jobs ran first. Must supply at least
            one seed per pipeline the cap affords.
        _confirmation_override: test seam. Substitutes the stage-4 confirmation
            values so the registered tie-break can be exercised, which noise makes
            practically impossible to reach otherwise.

    Raises:
        ValueError: if ``cap`` is negative, or ``seeds`` is shorter than the number
            of pipelines the cap affords — silently running fewer would report a
            smaller budget under the cap's name.
    """
    if cap < 0:
        raise ValueError(f"cap={cap!r} is negative; pass the registered cap (Q52: 200).")

    dim = int(bounds.shape[1])
    n_pipelines = int(cap) // PIPELINE_BUDGET
    if seeds is None:
        seeds = tuple(seed + i for i in range(n_pipelines))
    elif len(seeds) < n_pipelines:
        raise ValueError(
            f"cap={cap} affords {n_pipelines} pipelines but only {len(seeds)} seeds "
            "were given; running fewer would report a smaller budget under the cap's "
            "name."
        )
    else:
        seeds = tuple(seeds[:n_pipelines])

    rule_a: dict[int, float] = {}
    rule_c_un: dict[int, float] = {}
    rule_c_con: dict[int, float] = {}
    chosen: dict[int, int] = {}
    confirmation_y: list[float] = []
    per_pipeline_un: list[float] = []
    per_pipeline_con: list[float] = []

    x_acc: list[Tensor] = []
    y_acc: list[Tensor] = []

    for i, s in enumerate(seeds):
        r = run_doe_arm(evaluator, bounds, truth=truth,
                        budget=PIPELINE_BUDGET, seed=s)

        x_acc.append(r.X_visited)
        y_acc.append(r.Y_visited)
        confirmation_y.append(float(r.confirmation_y) if _confirmation_override is None
                              else float(_confirmation_override[i]))

        # --- this pipeline's own recommendation, both scorings ------------------
        kept = list(r.kept_factors)
        s2 = slice(r.n_stage1, r.n_stage1 + r.n_stage2)
        fit = fit_second_order(r.X_visited[s2][:, kept], r.Y_visited[s2])

        x_con, _, _ = constrained_argmax(fit.predict, r.stage2_bounds,
                                         n_restarts=_N_RESTARTS,
                                         raw_samples=_RAW_SAMPLES, seed=s)
        per_pipeline_un.append(
            optimum_value - float(truth(r.confirmation_x.reshape(1, -1))))
        per_pipeline_con.append(
            optimum_value - float(truth(_lift(x_con, kept, r.dropped_held_at, dim))))

        # --- the arm's answer if it stopped here --------------------------------
        checkpoint = (i + 1) * PIPELINE_BUDGET
        X_all = torch.cat(x_acc, dim=0)
        Y_all = torch.cat(y_acc, dim=0)
        t_all = truth(X_all).double()
        rule_a[checkpoint] = optimum_value - float(reported_best_curve(t_all, Y_all)[-1])

        j = int(np.argmax(confirmation_y))
        chosen[checkpoint] = j
        rule_c_un[checkpoint] = per_pipeline_un[j]
        rule_c_con[checkpoint] = per_pipeline_con[j]

    return DoERepeatResult(
        checkpoints=tuple(sorted(rule_a)),
        n_pipelines=n_pipelines,
        evaluations_spent=n_pipelines * PIPELINE_BUDGET,
        seeds=seeds,
        rule_a=rule_a,
        rule_c_unconstrained=rule_c_un,
        rule_c_constrained=rule_c_con,
        chosen_pipeline=chosen,
        confirmation_y=tuple(confirmation_y),
    )
