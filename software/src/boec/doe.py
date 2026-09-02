"""The sequential design-of-experiments arm of Experiment 2.

OWNERSHIP: Person A. Phase 1 only.

------------------------------------------------------------------------------
WHAT THIS IS, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

This is what a working scientist does when they do *not* have Bayesian
optimization: a textbook two-stage design-of-experiments campaign, which is
exactly the procedure the published study we are benchmarking against ran.

  Stage 1  Measure a cheap screening pattern to find out which of the
           ingredients matter at all.                        20 measurements
  Stage 2  Build a fuller pattern around the promising region, using only the
           ingredients that survived.                        27 measurements
  Stage 3  Fit a curved surface and ask it where the best recipe is.  free
  Stage 4  **Go and make that recipe and measure it.**        1 measurement

Twenty plus twenty-seven plus one is forty-eight — the identical budget every
other method in Experiment 2 gets. That equality is the whole basis of the
comparison, so a budget that does not split exactly raises rather than quietly
spending forty-seven or forty-nine.

**The same three numbers hold at six factors and at eight** (:data:`STAGE1_FRACTION`,
Q24): a more aggressive fraction absorbs the two extra factors, so stage 1 stays at
sixteen runs and every other stage is untouched. That was not a convenience. Until it
was true, this arm existed only at d=6 — and d=8 is precisely where the E2 tables show
Bayesian optimization winning, so "BO beats current practice" was being read off a
dimension at which current practice had never been run.

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

__all__ = [
    "HOLD_POLICIES", "STAGE1_FRACTION", "UNSCREENED_FRACTION", "UNSCREENED_N_CENTRE",
    "DoEResult", "run_doe_arm", "run_doe_unscreened_arm",
]

#: Q15 (T2). Where screened-out factors sit during stage 2. ``"best_stage1"`` is the
#: pre-registered primary; ``"zero"`` is the declared sensitivity. Registered before
#: either was run — see :func:`run_doe_arm` for the asymmetry the choice rests on.
HOLD_POLICIES = ("best_stage1", "zero")

#: Q24. How aggressive a stage-1 fraction each dimension screens with, chosen so that
#: stage 1 + stage 2 + confirmation lands on exactly 48 at every dimension the arm
#: runs at. It is a table and not a formula because the fraction is only admissible
#: where a minimum-aberration generator exists and has been verified — see
#: ``_GENERATORS`` in :mod:`boec.designs`.
#:
#: ==== ============== ========= ========= ===== =====
#: d    fraction       stage 1   stage 2   conf. total
#: ==== ============== ========= ========= ===== =====
#: 6    2^(6-2)_IV     16 + 4    27        1     48
#: 8    2^(8-4)_IV     16 + 4    27        1     48
#: ==== ============== ========= ========= ===== =====
#:
#: **The two dimensions are structurally identical**, which is the point: the same
#: 16-run resolution-IV screen, the same 4 survivors, the same 27-run face-centred
#: CCD, the same single confirmation. So a d=6 vs d=8 difference in this arm is a
#: difference in the *landscape*, not in the procedure — the one thing that would
#: otherwise confound the comparison Q24 asks for.
#:
#: A missing dimension raises rather than defaulting: a screen with the wrong
#: fraction still runs, still fits, and still produces a believable recipe, and the
#: only symptom is a budget that no longer matches the other arms.
STAGE1_FRACTION: dict[int, int] = {6: 2, 8: 4}


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
        hold_dropped_at: which Q15 policy produced ``dropped_held_at`` --
            ``"best_stage1"`` (the pre-registered primary) or ``"zero"`` (the
            declared sensitivity). Recorded on the result so a stored row can never
            be attributed to the wrong arm.
        n_derived_stage1: the stage-1 fraction actually taken -- ``2`` at d=6, ``4``
            at d=8 (Q24). Recorded for the same reason as ``hold_dropped_at``: the
            two dimensions run structurally identical campaigns on different
            fractions, and a stored row that does not carry which one it used cannot
            be checked afterwards.
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
    hold_dropped_at: str = "best_stage1"
    n_derived_stage1: int = 2
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
    hold_dropped_at: str = "best_stage1",
    n_derived_stage1: int | None = None,
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
        hold_dropped_at: where the screened-out factors sit during stage 2. **Q15,
            registered before either arm was run** (OPEN-QUESTIONS Q15, T2):

            * ``"best_stage1"`` -- the level they took in the best stage-1 run.
              **The pre-registered primary**, and the default. It is what a
              practitioner does, and it is the *conservative* choice: stage 2 stays
              near the region the data speaks to, so the confirmation point has less
              distance to extrapolate and the over-promise is harder to demonstrate.
            * ``"zero"`` -- a nominal zero. **The declared sensitivity.** Closer to
              Hall/Ogle, whose reported optimum sits at zero for both dropped
              laminins. It bites through screen error: the screen recovers 94% of
              planted active factors at sigma_rel=0.10 and 86% at 0.25, and a wrongly
              dropped *active* factor pinned to zero drags stage 2 into a genuinely
              worse region, so this arm should over-promise more.

            The primary was fixed on that asymmetry -- conservative arm primary,
            flattering arm secondary -- and NOT on which produced the larger number.
            Neither had been run when it was chosen.
        n_derived_stage1: how aggressive a fraction the stage-1 screen takes.
            ``None`` reads :data:`STAGE1_FRACTION`, which is registered per
            dimension (Q24) so the budget closes exactly at 48 at both d=6 and
            d=8. Passing it explicitly is for tests and sensitivity arms; a
            dimension absent from the table raises rather than guessing.

    Returns:
        A :class:`DoEResult`.

    Raises:
        ValueError: if the budget does not split exactly. Spending 47 or 49 would
            make this arm incomparable to every other arm in E2 and nothing
            downstream would notice.
    """
    if hold_dropped_at not in HOLD_POLICIES:
        raise ValueError(
            f"hold_dropped_at={hold_dropped_at!r} is not a registered policy; "
            f"choose from {sorted(HOLD_POLICIES)}. Falling back to the default would "
            "report the sensitivity arm's label against the primary arm's numbers."
        )

    d = int(bounds.shape[1])

    if n_derived_stage1 is None:
        if d not in STAGE1_FRACTION:
            raise ValueError(
                f"no registered stage-1 fraction for d={d}; known: "
                f"{sorted(STAGE1_FRACTION)}. Guessing one would produce a campaign "
                "that runs, fits and returns a plausible recipe on a budget that no "
                "longer matches the other E2 arms. Register the split first (Q24)."
            )
        n_derived_stage1 = STAGE1_FRACTION[d]

    # --- stage 1: which ingredients matter at all? --------------------------
    s1 = screening_design(d, n_centre=n_centre_stage1, n_derived=n_derived_stage1)
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
    # Q15 (T2), pre-registered: dropped factors are held at the best stage-1 run's
    # level by default -- what a practitioner does, and the conservative arm, since it
    # keeps the confirmation point inside a region the data actually speaks to. The
    # `zero` policy is the declared sensitivity. Recorded either way, and the policy
    # itself is recorded on the result so a row cannot be attributed to the wrong arm.
    best_row = int(torch.argmax(Y1.ravel()))
    if hold_dropped_at == "zero":
        held = {int(i): 0.0 for i in dropped}
    else:
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
        kept_factors=kept, dropped_held_at=held, hold_dropped_at=hold_dropped_at,
        n_derived_stage1=int(n_derived_stage1),
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


#: The mandatory comparator (spec §4): a full-dimensional second-order design, no
#: screening stage. Registered only where the CCD's own factorial + axial points
#: leave room for the centre replicates a CCD needs to estimate noise -- see
#: :data:`UNSCREENED_N_CENTRE`. ``n_derived=1`` at d=6 gives the half-fraction CCD;
#: the same table entry does not exist at d=8 on purpose (see below).
UNSCREENED_FRACTION: dict[int, int] = {6: 1, 8: 3}

#: Centre replicates for the unscreened arm, registered per dimension so a caller
#: can never derive it from the budget after the fact -- exactly the asymmetry
#: :data:`STAGE1_FRACTION` guards against. At d=6, the half-fraction factorial (32)
#: plus axial (12) leaves 4 of the 48-well budget for centre + confirmation; 3 go
#: to the centre replicates and 1 to stage 4.
#:
#: **d=8 has no entry.** The next resolution down, ``n_derived=3``, gives 32
#: factorial + 16 axial = 48 -- the entire budget -- with nothing left for a
#: single centre point, let alone the confirmation run. A CCD that cannot
#: estimate its own noise is not the same procedure as the d=6 arm, so
#: :func:`run_doe_unscreened_arm` raises there rather than running with
#: ``n_centre=0``.
UNSCREENED_N_CENTRE: dict[int, int] = {6: 3}


def run_doe_unscreened_arm(
    evaluator,
    bounds: Tensor,
    *,
    truth,
    budget: int = 48,
    seed: int = 0,
    n_centre: int | None = None,
    n_derived: int | None = None,
) -> DoEResult:
    """Run the full-dimensional response-surface arm: one CCD, then measure its optimum.

    The mandatory comparator spec §4 calls for wherever arithmetically feasible: no
    screening stage, every factor kept, a single central-composite design across the
    whole space, fit, and its predicted optimum measured exactly like stage 4 of
    :func:`run_doe_arm`.

    Args:
        evaluator: anything with ``evaluate(X) -> (Y, Yvar)``.
        bounds: ``(2, d)`` the full space, in coded units.
        truth: the **noiseless** oracle, ``(n, d) -> (n, 1)``. Scoring only.
        budget: total measurements. Must equal the registered design size plus one
            confirmation run, exactly as :func:`run_doe_arm` requires for its split.
        seed: fixes the confirmation search.
        n_centre: centre replicates. ``None`` reads :data:`UNSCREENED_N_CENTRE`,
            registered per dimension so the budget closes exactly. A dimension
            absent from the table raises rather than running with zero centre
            points.
        n_derived: how aggressive a fraction the CCD's factorial takes. ``None``
            reads :data:`UNSCREENED_FRACTION`.

    Returns:
        A :class:`DoEResult` with ``kept_factors`` equal to every factor and
        ``dropped_held_at`` empty.

    Raises:
        ValueError: if the dimension has no registered fraction or centre-point
            count, or if the budget does not match the registered design exactly.
    """
    d = int(bounds.shape[1])

    if n_derived is None:
        if d not in UNSCREENED_FRACTION:
            raise ValueError(
                f"no registered unscreened fraction for d={d}; known: "
                f"{sorted(UNSCREENED_FRACTION)}. Guessing one would produce a "
                "campaign that runs, fits, and returns a plausible recipe on a "
                "budget that no longer matches the other arms in this study."
            )
        n_derived = UNSCREENED_FRACTION[d]

    if n_centre is None:
        if d not in UNSCREENED_N_CENTRE:
            raise ValueError(
                f"d={d} has no feasible centre-point budget for the unscreened "
                f"arm: the {n_derived}-fraction factorial plus its axial points "
                f"already reach {budget} runs, leaving zero for the centre "
                "replicates a CCD needs to estimate noise. This is not the same "
                "procedure as the d=6 arm and must not run silently."
            )
        n_centre = UNSCREENED_N_CENTRE[d]

    design = central_composite(d, n_centre=n_centre, n_derived=n_derived, face_centred=True)
    n_design = design.points.shape[0]
    if n_design + 1 != budget:
        raise ValueError(
            f"budget {budget} does not split: the unscreened design is {n_design} "
            f"runs and confirmation is 1, totalling {n_design + 1}. This arm is "
            f"only registered for a {n_design + 1}-well budget at d={d}; spending "
            "a different number would make it incomparable to the other arms."
        )

    X_design = scale_to_box(design.coded, bounds)
    Y_design, _ = evaluator.evaluate(X_design)

    kept = tuple(range(d))
    held: dict[int, float] = {}

    # --- fit, and ask where the best recipe is -- no screening, no local box ---
    fit = fit_second_order(X_design, Y_design)
    op = over_prediction_at_constrained_argmax(fit.predict, truth, bounds, seed=seed)
    x_full = op.x_argmax

    tol = 1e-9
    inside = bool(
        torch.all(op.x_argmax >= bounds[0] - tol)
        and torch.all(op.x_argmax <= bounds[1] + tol)
    )
    on_edge = bool(
        torch.any((op.x_argmax - bounds[0]).abs() < 1e-6)
        or torch.any((op.x_argmax - bounds[1]).abs() < 1e-6)
    )

    # --- MEASURE IT ----------------------------------------------------------
    Yc, _ = evaluator.evaluate(x_full.unsqueeze(0))
    confirmation_y = float(Yc)

    observed = np.concatenate([Y_design.double().numpy().ravel(), [confirmation_y]])
    X_all = torch.cat([X_design, x_full.unsqueeze(0)])
    truth_all = truth(X_all).double().numpy().ravel()
    return DoEResult(
        curve=np.maximum.accumulate(observed),
        curve_true=np.maximum.accumulate(truth_all),
        X_visited=X_all,
        Y_visited=torch.from_numpy(observed).reshape(-1, 1),
        n_stage1=0, n_stage2=n_design,
        kept_factors=kept, dropped_held_at=held, hold_dropped_at="best_stage1",
        n_derived_stage1=int(n_derived),
        confirmation_x=x_full,
        predicted_y=op.y_predicted,
        confirmation_y=confirmation_y,
        over_prediction=op.over_prediction,
        confirmation_inside_stage2=inside,
        confirmation_on_stage2_boundary=on_edge,
        stage2_bounds=bounds,
        search_bounds=bounds,
        stationary_kind=fit.stationary_point(bounds).kind,
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
