"""The sequential design-of-experiments arm of Experiment 2.

OWNERSHIP: Person A. Phase 1 only.

------------------------------------------------------------------------------
WHAT THIS IS, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

This is what a working scientist does when they do *not* have Bayesian
optimization: a textbook two-stage design-of-experiments campaign, which is
exactly the procedure the published study we are benchmarking against ran.

  Stage 1  Measure a cheap screening pattern to find out which of the six
           ingredients matter at all.                        20 measurements
  Stage 2  Build a fuller pattern around the promising region, using only the
           ingredients that survived.                        27 measurements
  Stage 3  Fit a curved surface and ask it where the best recipe is.  free
  Stage 4  **Go and make that recipe and measure it.**        1 measurement

Twenty plus twenty-seven plus one is forty-eight — the identical budget every
other method in Experiment 2 gets. That equality is the whole basis of the
comparison, so a budget that does not split exactly raises rather than quietly
spending forty-seven or forty-nine.

------------------------------------------------------------------------------
WHY STAGE 4 IS NOT OPTIONAL
------------------------------------------------------------------------------

The thing this pipeline *produces* is a predicted optimum. Skip stage 4 and the
arm's best-so-far is merely the best point it happened to measure while
designing, and the method's actual output never appears in the regret curve at
all -- which would flatter it, because the prediction is usually worse than the
best measured point. The published study evaluated its predicted optimum. So
does this.

------------------------------------------------------------------------------
THE CONNECTION TO EXPERIMENT 4
------------------------------------------------------------------------------

Stage 4 is E4a viewed from the other end. Experiment 4 hides part of the space
deliberately and asks whether the traditional model over-promises outside it;
this arm never hides anything, but its stage-2 region is narrow *because the
screen made it narrow*, and the fitted surface can still point outside it.

Scored with `metrics.over_prediction_at_constrained_argmax` -- **B's function,
not a local copy** -- so the two experiments report one number. If the
confirmation run lands outside its own design region and under-delivers, the
published failure mode has reproduced in the benchmark without being staged
for it, which is a stronger result than E4a alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch
from torch import Tensor

from boec.designs import central_composite, scale_to_box, screening_design
from boec.metrics import over_prediction_at_constrained_argmax
from boec.rsm import fit_second_order

__all__ = ["DoEResult", "run_doe_arm"]


@dataclass
class DoEResult:
    """What the arm did and what it produced.

    Attributes:
        curve: ``(budget,)`` best-so-far of the **observed** values, in the order
            the measurements were taken. The last entry includes stage 4.
        curve_true: ``(budget,)`` best-so-far of the **noiseless** values at the same
            points. **This is what E2 scores** -- see OPEN-QUESTIONS Q17. Unlike
            ``curve`` it can never exceed the true optimum, which is precisely how the
            observation-scored version was caught being wrong.
        X_visited: ``(budget, d)`` every point measured, in order.
        Y_visited: ``(budget, 1)`` what the lab saw at each of them.
        n_stage1: measurements spent screening.
        n_stage2: measurements spent on the response-surface design.
        n_confirmation: always 1 -- named rather than assumed, because dropping it
            is the single easiest way to accidentally flatter this arm.
        kept_factors: which ingredients survived the screen, ascending.
        dropped_held_at: dropped ingredient -> the coded level it was held at for
            stage 2. Recorded because without it stage 2's design region, and hence
            the confirmation point, cannot be interpreted.
        confirmation_x: ``(d,)`` the recipe the fitted surface predicted was best.
        predicted_y: what the surface promised there.
        confirmation_y: what the lab actually measured there, with noise.
        over_prediction: ``predicted_y`` minus the **noiseless** truth. B's shared
            metric. Positive means the method promised more than reality delivered.
        confirmation_inside_stage2: whether the predicted optimum fell inside the
            region stage 2 actually explored. False is the interesting case.
        confirmation_on_stage2_boundary: whether it sits ON that region's edge. This
            is the signature of a *constrained* optimiser -- JMP's Prediction
            Profiler confines "Maximize Desirability" to the entered factor ranges --
            and is the pattern the published study's reported optimum shows.
        stage2_bounds: ``(2, n_keep)`` the region stage 2 actually explored.
        search_bounds: ``(2, n_keep)`` the region the predicted optimum was sought
            over. Strictly wider than ``stage2_bounds``, or escape is impossible.
        stationary_kind: maximum / minimum / saddle / ridge, descriptive.
    """

    curve: np.ndarray
    curve_true: np.ndarray
    X_visited: Tensor
    Y_visited: Tensor
    n_stage1: int
    n_stage2: int
    kept_factors: tuple[int, ...]
    dropped_held_at: dict[int, float]
    confirmation_x: Tensor
    predicted_y: float
    confirmation_y: float
    over_prediction: float
    confirmation_inside_stage2: bool
    confirmation_on_stage2_boundary: bool
    stage2_bounds: Tensor
    search_bounds: Tensor
    stationary_kind: str
    n_confirmation: int = 1
    notes: list[str] = field(default_factory=list)


def _main_effects(coded: Tensor, y: Tensor) -> np.ndarray:
    """``(d,)`` absolute main effect of each factor from a two-level screen.

    The classic contrast: mean at the high level minus mean at the low level.
    Centre points sit at 0 and contribute to neither, which is what they are for.
    """
    C = coded.double().numpy()
    v = y.double().numpy().ravel()
    out = np.zeros(C.shape[1])
    for i in range(C.shape[1]):
        hi, lo = C[:, i] > 0, C[:, i] < 0
        if hi.any() and lo.any():
            out[i] = v[hi].mean() - v[lo].mean()
    return np.abs(out)


def run_doe_arm(
    evaluator,
    bounds: Tensor,
    *,
    truth,
    budget: int = 48,
    seed: int = 0,
    n_keep: int = 4,
    n_centre_stage1: int = 4,
    n_centre_stage2: int = 3,
    stage2_half_width: float = 0.25,
) -> DoEResult:
    """Run the two-stage DoE campaign and measure its predicted optimum.

    Args:
        evaluator: anything with ``evaluate(X) -> (Y, Yvar)``.
        bounds: ``(2, d)`` the full space, in coded units.
        truth: the **noiseless** oracle, ``(n, d) -> (n, 1)``. Scoring only -- it is
            never shown to the fitted model. Passing a noisy draw here would make
            over-prediction absorb measurement noise.
        budget: total measurements. Must split exactly as stage1 + stage2 + 1.
        seed: fixes the screen's centre points and the confirmation search.
        n_keep: how many factors survive the screen. 4 matches the published 6 -> 4.
        n_centre_stage1: centre replicates in the screen.
        n_centre_stage2: centre replicates in the response-surface design.
        stage2_half_width: how far stage 2 explores either side of the best stage-1
            run, in coded units. 0.25 gives a box spanning half the range. **This is
            a modelling choice, not a constant** -- at 0.5 stage 2 covers the whole
            space, the predicted optimum can never fall outside it, and the escape
            statistic silently becomes zero.

    Returns:
        A :class:`DoEResult`.

    Raises:
        ValueError: if the budget does not split exactly. Spending 47 or 49 would
            make this arm incomparable to every other arm in E2 and nothing
            downstream would notice.
    """
    d = int(bounds.shape[1])

    # --- stage 1: which ingredients matter at all? --------------------------
    s1 = screening_design(d, n_centre=n_centre_stage1, n_derived=2)
    s2_template = central_composite(
        n_keep, n_centre=n_centre_stage2, n_derived=0, face_centred=True
    )
    n1, n2 = s1.points.shape[0], s2_template.points.shape[0]
    if n1 + n2 + 1 != budget:
        raise ValueError(
            f"budget {budget} does not split: stage 1 is {n1} runs, stage 2 is {n2}, "
            f"and the confirmation is 1, totalling {n1 + n2 + 1}. Spending a different "
            "number would make this arm incomparable to the other E2 arms."
        )

    X1 = scale_to_box(s1.coded, bounds)
    Y1, _ = evaluator.evaluate(X1)

    effects = _main_effects(s1.coded, Y1)
    kept = tuple(sorted(int(i) for i in np.argsort(effects)[::-1][:n_keep]))
    dropped = [i for i in range(d) if i not in kept]

    # --- stage 2: a fuller design on the survivors --------------------------
    # Dropped factors are held at the level of the best stage-1 run rather than at a
    # nominal zero: that is what a practitioner does, and it keeps the confirmation
    # point inside a region the data actually speaks to. Recorded either way.
    best_row = int(torch.argmax(Y1.ravel()))
    held = {int(i): float(X1[best_row, i]) for i in dropped}

    # Stage 2 is a LOCAL exploration centred on the best stage-1 run, not a second
    # sweep of the whole space -- that is what "centred on the best stage-1 region"
    # means, and it is what makes the arm cheap enough to fit in the budget.
    #
    # `stage2_half_width` is a real modelling choice and is surfaced rather than
    # buried: it sets how much of the space the practitioner ends up having seen,
    # and therefore how far the fitted surface has to reach when it predicts an
    # optimum. Making it 0.5 would span the full range and the escape statistic
    # below would be vacuously zero.
    centre = X1[best_row, list(kept)].clone()
    half = float(stage2_half_width)
    lo = torch.clamp(centre - half, min=bounds[0, list(kept)])
    hi = torch.clamp(centre + half, max=bounds[1, list(kept)])
    sub_bounds = torch.stack([lo, hi])

    X2 = torch.empty(n2, d, dtype=torch.double)
    for i, level in held.items():
        X2[:, i] = level
    X2[:, list(kept)] = scale_to_box(s2_template.coded, sub_bounds)
    Y2, _ = evaluator.evaluate(X2)

    # --- stage 3: fit, and ask where the best recipe is ---------------------
    # Fitted on the kept factors only. The dropped ones are constant across stage 2,
    # so including them would make the design matrix rank-deficient and
    # `fit_second_order` would (correctly) refuse.
    fit = fit_second_order(X2[:, list(kept)], Y2)

    # Searched over the kept factors' full range, NOT restricted to the stage-2 box.
    # A practitioner reads the profiler's optimum and makes it; whether that lands
    # outside the region they explored is the finding, not something to prevent.
    search = torch.stack([bounds[0, list(kept)], bounds[1, list(kept)]])
    op = over_prediction_at_constrained_argmax(
        fit.predict, _lift(truth, kept, held, d), search, seed=seed
    )
    x_full = torch.tensor([held.get(i, 0.0) for i in range(d)], dtype=torch.double)
    x_full[list(kept)] = op.x_argmax

    tol = 1e-9
    inside = bool(
        torch.all(op.x_argmax >= sub_bounds[0] - tol)
        and torch.all(op.x_argmax <= sub_bounds[1] + tol)
    )
    on_edge = bool(
        torch.any((op.x_argmax - sub_bounds[0]).abs() < 1e-6)
        or torch.any((op.x_argmax - sub_bounds[1]).abs() < 1e-6)
    )

    # --- stage 4: MEASURE IT ------------------------------------------------
    Yc, _ = evaluator.evaluate(x_full.unsqueeze(0))
    confirmation_y = float(Yc)

    observed = np.concatenate([
        Y1.double().numpy().ravel(), Y2.double().numpy().ravel(), [confirmation_y]
    ])
    X_all = torch.cat([X1, X2, x_full.unsqueeze(0)])
    truth_all = truth(X_all).double().numpy().ravel()
    return DoEResult(
        curve=np.maximum.accumulate(observed),
        curve_true=np.maximum.accumulate(truth_all),
        X_visited=X_all,
        Y_visited=torch.from_numpy(observed).reshape(-1, 1),
        n_stage1=n1, n_stage2=n2,
        kept_factors=kept, dropped_held_at=held,
        confirmation_x=x_full,
        predicted_y=op.y_predicted,
        confirmation_y=confirmation_y,
        over_prediction=op.over_prediction,
        confirmation_inside_stage2=inside,
        confirmation_on_stage2_boundary=on_edge,
        stage2_bounds=sub_bounds,
        search_bounds=search,
        stationary_kind=fit.stationary_point(sub_bounds).kind,
    )


def _lift(truth, kept: tuple[int, ...], held: dict[int, float], d: int):
    """Turn a full-space truth function into one over the kept factors alone.

    The fitted model only knows about `kept`, so the argmax search happens in that
    subspace -- but the oracle needs a full recipe. This pins the dropped factors at
    the levels stage 2 held them at, which is the recipe a practitioner would
    actually make.
    """

    def inner(Xk: Tensor) -> Tensor:
        full = torch.zeros(Xk.shape[0], d, dtype=torch.double)
        for i, v in held.items():
            full[:, i] = v
        full[:, list(kept)] = Xk.double()
        return truth(full)

    return inner
