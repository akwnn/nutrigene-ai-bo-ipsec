"""`doe_ascent` — sequential RSM that is allowed to walk. Prompt 1 of `docs/PROMPTS-NEXT.md`.

------------------------------------------------------------------------------
WHAT THIS IS, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

:mod:`boec.doe_repeat` spends a 200-well budget by running the same 48-well pipeline
four times with different seeds and keeping whichever came out best. It never moves.
Every cost curve built on it therefore carries a concession, stated in the registration
before the numbers landed:

    cost curves are biased in favour of BO because the classical arm has no
    steepest ascent

That is true, and it is not a small bias: Bayesian optimization re-aims after every batch
of four and can walk clear across the space in 200 wells, while `doe_repeat` re-measures
one neighbourhood four times. Until a classical arm exists that is allowed the same
freedom, *"BO reaches quality targets in fewer experiments"* is not a claim this project
can make.

This module is that arm. It is the textbook Box–Wilson procedure:

  1. **Screen** the same 20 runs, keep the same four factors.  (1 plate)
  2. **CCD** — a 27-run face-centred design on the survivors.   (1 plate)
  3. **Fit** a quadratic and classify its stationary point.
  4. **Walk.** Step along the steepest-ascent path until the response stops improving,
     move the design centre to the last improving point, and go back to 2.

------------------------------------------------------------------------------
THE THREE CHOICES THAT ARE REGISTRATIONS, NOT IMPLEMENTATION DETAILS
------------------------------------------------------------------------------

**The ascent path is plated with that cycle's confirmation well.** Both are computed from
the same fitted CCD, so a lab holds both lists at the same moment and would not wait a
whole plate cycle to run one extra well. A campaign of ``k`` cycles therefore costs
``1 + 2k`` rounds — screen, then a CCD plate and an ascent plate per cycle. Registered
before the run, and :func:`rounds_for_sequential_rsm` is the single definition every
report reads, so a figure and a table cannot disagree about it.

**Which point on the path becomes the new centre is a registered choice with two
options, and both are run.** Prompt 1 words the rule as *"step along the path until the
measured response stops improving; move the design centre to the last improving point"*.
Taken literally under noise that rule is a coin flip on the very first step: measured on
real landscapes at sigma_rel=0.25, the path reads ``[0.999, 1.228, 1.028, 0.835, 0.641]``
against a centre reference of ``1.021`` — the second point is far above the reference and
the first is a hair below it, so a first-decline rule stops at step one, never relocates,
and the arm silently degenerates into `doe_repeat` with a single pipeline. That outcome
would reinstate exactly the bias this module exists to remove.

Myers, Montgomery & Anderson-Cook take the **maximum along the path** as the next centre,
and that is the registered primary here (:data:`ASCENT_RULES`). The literal first-decline
reading is implemented beside it and reported in the same table, because choosing the
rule that makes this arm walk is a decision that must be visible rather than absorbed.
Neither costs an extra well: both read the same measured path.

**Leftover wells go unspent.** A cycle costs ``CCD_BUDGET + ASCENT_STEPS + 1``; when the
remainder cannot fund a whole one the campaign stops with wells in hand, exactly as
`doe_repeat` leaves 8 of 200 unspent. A partial CCD is rank-deficient and does not fit a
quadratic, so spending the remainder would report a budget the method never really used.

------------------------------------------------------------------------------
WHAT THIS ARM IS *NOT* ALLOWED TO DO
------------------------------------------------------------------------------

It does not replace :func:`boec.doe.run_doe_arm` and it does not touch the N=48
matched-budget tables. Those remain the no-ascent pipeline, which is the right comparator
at a budget that affords exactly one CCD. This arm only becomes meaningful past 48 wells,
which is precisely where the cost curves live and precisely where the old concession bit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import torch
from torch import Tensor

from boec.designs import central_composite, scale_to_box, screening_design
from boec.diagnostics import reported_best_curve
from boec.doe import STAGE1_FRACTION, _main_effects
from boec.metrics import constrained_argmax
from boec.rsm import fit_second_order

__all__ = ["ASCENT_RULES", "ASCENT_STEP", "ASCENT_STEPS", "CCD_BUDGET", "CYCLE_BUDGET",
           "N_KEEP", "SCREEN_BUDGET", "AscentCycle", "SequentialRSMResult",
           "rounds_for_sequential_rsm", "run_sequential_rsm"]

#: Matched to :func:`boec.doe.run_doe_arm` so the two classical arms differ in exactly one
#: respect — whether the design is allowed to relocate.
N_KEEP = 4
SCREEN_BUDGET = 20          # 16-run resolution-IV fraction + 4 centre points
CCD_BUDGET = 27             # 16 corners + 8 axial + 3 centre, face-centred, at d=4
STAGE2_HALF_WIDTH = 0.25    # the CCD's half-width in coded units, as in `run_doe_arm`

#: How far one ascent step moves, in coded units on ``[0, 1]``. A tenth of the range: far
#: enough that five steps can cross half the space, short enough that the quadratic being
#: extrapolated from is still roughly valid at the first step. Registered, not tuned — no
#: value of this constant was tried against a result.
ASCENT_STEP = 0.10
#: Points measured on one ascent path. Five keeps the plate small relative to the 27-run
#: CCD that pays for it.
ASCENT_STEPS = 5
#: One cycle: a CCD, an ascent path, and the confirmation well for that cycle's own
#: recommendation.
CYCLE_BUDGET = CCD_BUDGET + ASCENT_STEPS + 1

#: How the next design centre is picked off the measured ascent path. Both are run and
#: both are reported — see the module docstring for why this is a registration rather
#: than an implementation detail. ``"path_argmax"`` is the primary.
ASCENT_RULES = ("path_argmax", "first_decline")

_N_RESTARTS = 20
_RAW_SAMPLES = 4096


def rounds_for_sequential_rsm(n_cycles: int) -> int:
    """Plate cycles for a campaign of ``n_cycles``: ``1 + 2 * n_cycles``.

    One plate for the screen, then per cycle one plate for the CCD and one for the
    ascent path (which carries that cycle's confirmation well). The single definition —
    reports read this rather than recomputing it, because a rounds formula that exists in
    two places is a rounds formula that will eventually exist in two versions.
    """
    if n_cycles < 1:
        raise ValueError(f"n_cycles={n_cycles!r}; a campaign with no cycle has no CCD "
                         "and therefore no recommendation to cost.")
    return 1 + 2 * n_cycles


@dataclass(frozen=True)
class AscentCycle:
    """One CCD, the walk that followed it, and where it ended up.

    Attributes:
        centre: ``(n_keep,)`` where this cycle's CCD was centred.
        ccd_bounds: ``(2, n_keep)`` the box it actually explored.
        stationary_kind: ``maximum`` / ``minimum`` / ``saddle`` / ``ridge`` of the fitted
            quadratic. The branch selector, and the reason a saddle can never be
            confirmed as an optimum.
        stopped_at_interior_maximum: the fit found a maximum inside its own box and the
            campaign confirmed it rather than walking. **False for a saddle, always** —
            that is the classic RSM error this field exists to make visible.
        relocated: whether the ascent moved the design centre at all. False means the
            path improved on nothing and the campaign has converged.
        ascent_path: ``(k, n_keep)`` the points measured on the path, in order.
        n_ascent: how many path points were measured — fewer than
            :data:`ASCENT_STEPS` when the path ran into the boundary.
        confirmation_x: ``(d,)`` the full-space recipe this cycle recommended, which was
            measured. Scoring a peak that was never run is forbidden (Prompt 1 §3).
        confirmation_y: what the lab saw there.
        centre_response: the mean of the CCD's centre replicates — the reference the
            ascent had to beat. Recorded because whether the design relocates is decided
            entirely by this number, and a stored cycle that does not carry it cannot be
            audited afterwards.
        evaluations: wells this cycle spent, including its confirmation.
    """

    centre: Tensor
    ccd_bounds: Tensor
    stationary_kind: str
    stopped_at_interior_maximum: bool
    relocated: bool
    ascent_path: Tensor
    n_ascent: int
    confirmation_x: Tensor
    confirmation_y: float
    centre_response: float
    evaluations: int


@dataclass(frozen=True)
class SequentialRSMResult:
    """A `doe_ascent` campaign.

    Attributes:
        checkpoints: cumulative wells at the end of each cycle — the budgets at which
            this arm can actually stop and hand over an answer. Every scoring dict is
            keyed by these.
        rounds: checkpoint -> plate cycles, from :func:`rounds_for_sequential_rsm`.
        oracle_best: checkpoint -> regret at the best **true** value among visited
            points. What the campaign tested, whether or not it could tell.
        rule_a: checkpoint -> regret at the **observed** argmax
            (:func:`boec.diagnostics.reported_best_curve`). What a researcher picks.
            Never ``np.maximum.accumulate`` of the noiseless values — that is D20.
        rule_c_unconstrained: checkpoint -> regret at the chosen cycle's recommendation,
            located over the kept factors' full range. Q41's primary.
        rule_c_constrained: checkpoint -> the same, located inside that cycle's own CCD.
        chosen_cycle: checkpoint -> which cycle's confirmation measured best. The run a
            lab would keep, matching `doe_repeat`'s registered tie-break so the two
            classical arms are answering the same question.
        cycles: every cycle, in order.
        kept_factors: the four survivors of the screen, ascending.
        dropped_held_at: dropped factor -> the coded level it was pinned at.
        X_visited / Y_visited: the full visit log, in plating order.
        evaluations_spent: wells actually run. Never the cap.
        unspent: wells the cap allowed that no whole cycle could use.
        converged: the campaign stopped because an ascent path improved on nothing,
            rather than because it ran out of budget.
        ascent_rule: which of :data:`ASCENT_RULES` produced this campaign. Stored on the
            result so a row can never be attributed to the policy it did not run under —
            the same reason `DoEResult` carries `hold_dropped_at`.
    """

    checkpoints: tuple[int, ...]
    rounds: dict[int, int]
    oracle_best: dict[int, float]
    rule_a: dict[int, float]
    rule_c_unconstrained: dict[int, float]
    rule_c_constrained: dict[int, float]
    chosen_cycle: dict[int, int]
    cycles: tuple[AscentCycle, ...]
    kept_factors: tuple[int, ...]
    dropped_held_at: dict[int, float]
    X_visited: Tensor
    Y_visited: Tensor
    evaluations_spent: int
    unspent: int
    converged: bool
    ascent_rule: str = "path_argmax"
    notes: list[str] = field(default_factory=list)


def _hessian_and_linear(beta: np.ndarray, d: int) -> tuple[np.ndarray, np.ndarray]:
    """``(H, b)`` for the fitted quadratic, in :func:`second_order_design_matrix` order.

    Shares its layout with :func:`boec.rsm.classify_stationary_point` — the gradient here
    and the classification there must be reading the same surface, or the arm would walk
    in a direction that contradicts the branch it took.
    """
    b = beta[1:1 + d].copy()
    c = beta[1 + d:1 + 2 * d]
    H = np.zeros((d, d), dtype=np.float64)
    np.fill_diagonal(H, 2.0 * c)
    for k, (i, j) in enumerate(combinations(range(d), 2)):
        H[i, j] = H[j, i] = beta[1 + 2 * d + k]
    return H, b


def _ascent_path(fit, centre: Tensor, reachable: Tensor) -> Tensor:
    """Points along the steepest-ascent path from ``centre``, clipped to ``reachable``.

    ``reachable`` is **the full factor range, not the CCD box.** Walking out of the
    region that was fitted is the entire purpose of this step — a path confined to its
    own design box cannot relocate the design, which is exactly `doe_repeat`'s
    limitation and the bias this arm exists to remove. The extrapolation is real and is
    the acknowledged risk of steepest ascent; it is answered by *measuring* every point
    on the path rather than by trusting the fit out there.

    The direction is the fitted surface's gradient at the centre, ``b + H c``. It is
    normalised, so :data:`ASCENT_STEP` means the same distance regardless of how steep
    the surface happens to be — otherwise the step length would silently encode the
    response's units and a flat landscape would never move.

    Returns fewer than :data:`ASCENT_STEPS` points when the path reaches the edge of the
    space: once a step is clipped, every later step lands on the same face and
    re-measuring it buys nothing.
    """
    d = int(centre.numel())
    H, b = _hessian_and_linear(fit.beta, d)
    g = b + H @ centre.double().numpy()
    norm = float(np.linalg.norm(g))
    if norm < 1e-12:
        return torch.empty(0, d, dtype=torch.double)
    direction = g / norm

    lo, hi = reachable[0].double().numpy(), reachable[1].double().numpy()
    pts, prev = [], centre.double().numpy()
    for step in range(1, ASCENT_STEPS + 1):
        x = np.clip(centre.double().numpy() + step * ASCENT_STEP * direction, lo, hi)
        if np.allclose(x, prev, atol=1e-12):
            break                      # pinned on the boundary; further steps repeat it
        pts.append(x)
        prev = x
    if not pts:
        return torch.empty(0, d, dtype=torch.double)
    return torch.from_numpy(np.asarray(pts))


def _new_centre_index(y: np.ndarray, start: float, rule: str) -> int:
    """Which path point becomes the next design centre, or ``-1`` for none.

    Both rules require the chosen point to beat ``start``, so a path that improves on
    nothing always ends the campaign — that is the convergence criterion, and it is the
    same under either rule.

    Args:
        y: observed responses along the path, in order.
        start: the design centre's own measured response. **Must be the centre
            replicates' mean, never the CCD's best observation.** The best of 27 noisy
            readings is an inflated order statistic — measured 0.22 to 0.60 above the
            centre estimate at sigma_rel=0.25 — and no single noisy path point can beat
            it, so referencing it blocks every relocation.
        rule: one of :data:`ASCENT_RULES`.

            * ``"path_argmax"`` — the best measured point on the path. Myers, Montgomery
              & Anderson-Cook's rule and the registered primary.
            * ``"first_decline"`` — walk forward, stop at the first point that fails to
              beat the running best, take the last improving one. The literal reading of
              Prompt 1's sentence. Under noise this usually stops at step one.

    Raises:
        ValueError: on an unregistered rule. Defaulting would let a campaign be filed
            under the wrong policy's name.
    """
    if rule not in ASCENT_RULES:
        raise ValueError(f"ascent_rule={rule!r} is not registered; choose from "
                         f"{sorted(ASCENT_RULES)}.")
    if y.size == 0:
        return -1
    if rule == "path_argmax":
        k = int(np.argmax(y))
        return k if y[k] > start else -1

    best, last = start, -1
    for i, v in enumerate(y):
        if v > best:
            best, last = v, i
        else:
            break
    return last


def run_sequential_rsm(
    evaluator,
    bounds: Tensor,
    *,
    truth,
    optimum_value: float,
    cap: int,
    seed: int,
    n_keep: int = N_KEEP,
    stage2_half_width: float = STAGE2_HALF_WIDTH,
    ascent_rule: str = "path_argmax",
) -> SequentialRSMResult:
    """Run steepest-ascent sequential RSM up to ``cap`` wells.

    Args:
        evaluator: anything with ``evaluate(X) -> (Y, Yvar)``.
        bounds: ``(2, d)`` the full coded space.
        truth: the **noiseless** oracle. Scoring only — never shown to the fit.
        optimum_value: the instance's true optimum, for regret.
        cap: the registered evaluation cap. Floors to whole cycles.
        seed: fixes the screen's centre points and every argmax search.
        n_keep: survivors of the screen. 4, matching the stored arm's 6 -> 4 cut.
        stage2_half_width: the CCD's half-width in coded units.
        ascent_rule: which point on the measured path becomes the next centre. One of
            :data:`ASCENT_RULES`; ``"path_argmax"`` is the registered primary. See the
            module docstring — under noise the two rules give materially different
            campaigns, so both are run and both are reported.

    Returns:
        A :class:`SequentialRSMResult`.

    Raises:
        ValueError: if ``cap`` cannot fund the screen plus one whole cycle. Returning a
            screen-only campaign would file DoE numbers for a run that never fitted a
            surface.
    """
    if ascent_rule not in ASCENT_RULES:
        raise ValueError(f"ascent_rule={ascent_rule!r} is not registered; choose from "
                         f"{sorted(ASCENT_RULES)}. Defaulting would file a campaign "
                         "under the wrong policy's name.")
    d = int(bounds.shape[1])
    if d not in STAGE1_FRACTION:
        raise ValueError(
            f"no registered stage-1 fraction for d={d}; known: {sorted(STAGE1_FRACTION)}.")
    if cap < SCREEN_BUDGET + CYCLE_BUDGET:
        raise ValueError(
            f"cap={cap} cannot fund the screen ({SCREEN_BUDGET}) plus one cycle "
            f"({CYCLE_BUDGET}). A screen-only campaign fits no surface and has no "
            "recommendation, so it would report DoE numbers for something that is not "
            "the method.")

    # --- the screen, once. Identical to `run_doe_arm`'s stage 1. -----------------
    s1 = screening_design(d, n_centre=4, n_derived=STAGE1_FRACTION[d])
    if s1.coded.shape[0] != SCREEN_BUDGET:
        raise ValueError(
            f"screen is {s1.coded.shape[0]} runs, not the registered {SCREEN_BUDGET}; "
            "the two classical arms would no longer share a stage 1.")
    X1 = scale_to_box(s1.coded, bounds)
    Y1, _ = evaluator.evaluate(X1)

    effects = _main_effects(s1.coded, Y1)
    kept = tuple(sorted(int(i) for i in np.argsort(effects)[::-1][:n_keep]))
    best_row = int(torch.argmax(Y1.ravel()))
    held = {int(i): float(X1[best_row, i]) for i in range(d) if i not in kept}

    ccd = central_composite(n_keep, n_centre=3, n_derived=0, face_centred=True)
    if ccd.coded.shape[0] != CCD_BUDGET:
        raise ValueError(
            f"CCD is {ccd.coded.shape[0]} runs, not the registered {CCD_BUDGET}.")

    # Located by their coordinates rather than by position, so a change to how
    # `central_composite` orders its blocks cannot silently turn the ascent's reference
    # into three arbitrary factorial corners.
    centre_rows = (ccd.coded.abs() < 1e-12).all(dim=1)
    if int(centre_rows.sum()) < 1:
        raise ValueError(
            "the CCD has no centre points, so there is no replicated estimate of the "
            "response at the design centre and the ascent has no reference to improve "
            "on.")

    kept_lo, kept_hi = bounds[0, list(kept)], bounds[1, list(kept)]
    search = torch.stack([kept_lo, kept_hi])
    centre = X1[best_row, list(kept)].clone().double()

    X_acc: list[Tensor] = [X1]
    Y_acc: list[Tensor] = [Y1]
    spent = SCREEN_BUDGET

    cycles: list[AscentCycle] = []
    checkpoints: list[int] = []
    rounds: dict[int, int] = {}
    oracle_best: dict[int, float] = {}
    rule_a: dict[int, float] = {}
    rule_c_un: dict[int, float] = {}
    rule_c_con: dict[int, float] = {}
    chosen: dict[int, int] = {}
    per_cycle_un: list[float] = []
    per_cycle_con: list[float] = []
    conf_y: list[float] = []
    converged = False

    while cap - spent >= CYCLE_BUDGET:
        # --- the CCD, centred wherever the last ascent left us ------------------
        # Held separately from `centre` because the ascent below moves `centre`, and a
        # cycle must record the point its own CCD was built around — otherwise every
        # cycle reports the next cycle's centre and the relocation looks like it never
        # happened.
        lo = torch.clamp(centre - stage2_half_width, min=kept_lo)
        hi = torch.clamp(centre + stage2_half_width, max=kept_hi)
        box = torch.stack([lo, hi])

        # Where the design is REALLY centred. `scale_to_box` maps coded 0 to the box
        # midpoint, and the box is clamped to the factor range — so when the requested
        # centre sits within a half-width of a boundary, the replicates land somewhere
        # else. Taking the midpoint keeps one point playing all three roles it must play
        # to be consistent: where the centre replicates are measured, where the gradient
        # is evaluated, and where the ascent path starts. Using the requested centre for
        # the last two while measuring the reference at the first would compare a walk
        # from one place against a baseline from another.
        cycle_centre = box.mean(dim=0)

        Xc = torch.empty(CCD_BUDGET, d, dtype=torch.double)
        for i, level in held.items():
            Xc[:, i] = level
        Xc[:, list(kept)] = scale_to_box(ccd.coded, box)
        Yc, _ = evaluator.evaluate(Xc)
        X_acc.append(Xc)
        Y_acc.append(Yc)
        spent += CCD_BUDGET

        fit = fit_second_order(Xc[:, list(kept)], Yc)
        stat = fit.stationary_point(box)

        # --- where this cycle would tell a lab to go ----------------------------
        x_un, _, _ = constrained_argmax(fit.predict, search, n_restarts=_N_RESTARTS,
                                        raw_samples=_RAW_SAMPLES, seed=seed + len(cycles))
        x_con, _, _ = constrained_argmax(fit.predict, box, n_restarts=_N_RESTARTS,
                                         raw_samples=_RAW_SAMPLES,
                                         seed=seed + len(cycles))
        conf_x = _lift(x_un, list(kept), held, d)

        # --- the ascent path, plated WITH the confirmation well ------------------
        # An interior maximum is the one case with nothing to walk toward: the surface
        # says the peak is inside the box already. A saddle is NOT that case, however
        # tempting `Hx = -b` makes it look — it is a minimum along at least one
        # eigenvector, so the campaign keeps walking.
        interior_max = stat.kind == "maximum" and stat.inside_box
        path = (torch.empty(0, n_keep, dtype=torch.double) if interior_max
                else _ascent_path(fit, cycle_centre, search))

        batch = torch.empty(path.shape[0] + 1, d, dtype=torch.double)
        for i, level in held.items():
            batch[:, i] = level
        if path.shape[0]:
            batch[:-1, list(kept)] = path
        batch[-1] = conf_x.reshape(-1)
        Yb, _ = evaluator.evaluate(batch)
        X_acc.append(batch)
        Y_acc.append(Yb)
        spent += int(batch.shape[0])

        conf_y.append(float(Yb[-1]))
        per_cycle_un.append(optimum_value - float(truth(conf_x)))
        per_cycle_con.append(optimum_value - float(
            truth(_lift(x_con, list(kept), held, d))))

        # --- walk to the last improving point -----------------------------------
        relocated = False
        centre_response = float(Yc[centre_rows].double().mean())
        if path.shape[0]:
            y_path = Yb[:-1].double().numpy().ravel()
            k = _new_centre_index(y_path, centre_response, ascent_rule)
            if k >= 0:
                centre = path[k].clone()
                relocated = True

        cycles.append(AscentCycle(
            centre=cycle_centre,
            ccd_bounds=box, stationary_kind=stat.kind,
            stopped_at_interior_maximum=bool(interior_max),
            relocated=relocated, ascent_path=path, n_ascent=int(path.shape[0]),
            confirmation_x=conf_x.reshape(-1), confirmation_y=float(Yb[-1]),
            centre_response=centre_response,
            evaluations=CCD_BUDGET + int(batch.shape[0])))

        # --- the arm's answer if it stopped here ---------------------------------
        X_all, Y_all = torch.cat(X_acc), torch.cat(Y_acc)
        t_all = truth(X_all).double()
        checkpoints.append(spent)
        rounds[spent] = rounds_for_sequential_rsm(len(cycles))
        oracle_best[spent] = optimum_value - float(t_all.max())
        rule_a[spent] = optimum_value - float(reported_best_curve(t_all, Y_all)[-1])
        j = int(np.argmax(conf_y))
        chosen[spent] = j
        rule_c_un[spent] = per_cycle_un[j]
        rule_c_con[spent] = per_cycle_con[j]

        if interior_max or not relocated:
            converged = True
            break

    X_all, Y_all = torch.cat(X_acc), torch.cat(Y_acc)
    return SequentialRSMResult(
        checkpoints=tuple(checkpoints), rounds=rounds,
        oracle_best=oracle_best, rule_a=rule_a,
        rule_c_unconstrained=rule_c_un, rule_c_constrained=rule_c_con,
        chosen_cycle=chosen, cycles=tuple(cycles),
        kept_factors=kept, dropped_held_at=held,
        X_visited=X_all, Y_visited=Y_all,
        evaluations_spent=spent, unspent=int(cap - spent), converged=converged,
        ascent_rule=ascent_rule)


def _lift(x_kept: Tensor, kept: list[int], held: dict[int, float], d: int) -> Tensor:
    """Put a kept-factor recipe back into full coded space at the held levels."""
    full = torch.tensor([held.get(i, 0.0) for i in range(d)], dtype=torch.double)
    full[kept] = x_kept.double().reshape(-1)
    return full.unsqueeze(0)
