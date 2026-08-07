"""Experiment 4, wired together end to end.

OWNERSHIP: Person B. Phase 1 only.

------------------------------------------------------------------------------
WHAT THIS FILE DOES, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

This is the experiment itself. Everything else was a component; this runs them
in order and produces the numbers.

For each made-up landscape, and for each of four "how much do we hide" settings:

  1. **Hide most of the space.** Take measurements only from a small corner
     that stops short of where the response actually peaks. How short is
     controlled by a setting called kappa: lower means less is seen.
  2. **Measure 48 recipes in that corner**, using the deliberate pattern.
  3. **Fit four different models to exactly the same 48 measurements.**
  4. **Ask each one where the best recipe in the whole space is** — including
     the large region none of them has seen.
  5. **Go and look at what is really there.** The gap between what each model
     promised and what is actually there is the headline number.
  6. **Ask each model how confident it was**, and check whether the confident
     ones were right to be.
  7. **Run the discrimination test** — which, despite the story above, is the
     actual measurement. See `discrimination.py`.

**The one thing that must never be done to make this work better.** If the
models turn out not to overshoot much, the fix is to hide *more* of the space —
lower kappa. It is emphatically **not** to move the peak further out. Moving
the peak flattens the landscape, which silently ruins Person A's separate
experiment. Move the box, never the peak.

------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np
import torch
from torch import Tensor

from boec.designs import (
    central_composite,
    extended_box_bounds,
    scale_to_box,
    sub_box_bounds,
)
from boec.discrimination import (
    DiscriminationResult,
    discrimination_test,
    nearest_neighbour_distance,
)
from boec.metrics import (
    OverPrediction,
    constrained_argmax,
    over_prediction_at_constrained_argmax,
)
from boec.parametric import fit_practitioner_parametric
from boec.rsm import fit_second_order, fit_stepwise_third_order
from boec.surrogate import build_gp, predictive

__all__ = ["E4Config", "E4Result", "E4bResult", "Oracle", "run_e4_cell", "run_e4b_cell", "summarise"]

MODEL_NAMES = ("second_order", "stepwise_third_order", "gp", "parametric")


@runtime_checkable
class Oracle(Protocol):
    """A made-up landscape. **Person A owns the implementation.**

    Structural rather than inheritance-based, so A's module and this one need
    not share a parent and neither has to exist before the other.

    Required:
        ``x_star``: ``(d,)`` where each ingredient's response peaks. Defines
            the hidden corner — see ``designs.sub_box_bounds``.
        ``truth(X)``: ``(n, d) -> (n, 1)`` the **noiseless** value. Used only
            for scoring, never for fitting.
        ``observe(X)``: ``(n, d) -> ((n, 1), (n, 1))`` a noisy measurement and
            its noise estimate. What the models are allowed to see.
    """

    @property
    def x_star(self) -> Tensor: ...
    def truth(self, X: Tensor) -> Tensor: ...
    def observe(self, X: Tensor) -> tuple[Tensor, Tensor]: ...


@dataclass
class E4Config:
    """Settings. The two pre-registered ones are locked — see the yaml file."""

    kappa: float
    # PRE-REGISTERED v2 PRIMARY. How far past the training corner every model
    # is asked about. 2.0 is far enough that extrapolation is real, near enough
    # that the geometry is defensible against the published study's 1.2x.
    #
    # **The default is 2.0 and must stay matched to configs/experiment/e4.yaml.**
    # It was inf, which silently ran the regime the pre-registration deprecates
    # — the scripts got the wrong regime and the results were labelled as though
    # they were the pre-registered one. There is now a test pinning this.
    #
    # inf gives the whole unit cube, reported as a limiting case.
    rho: float = 2.0
    n_centre: int = 4
    n_derived: int = 1               # half fraction: 32 + 12 + 4 = 48
    face_centred: bool = True
    n_candidates: int = 512          # PRE-REGISTERED
    tau_quantile: float = 0.80       # PRE-REGISTERED
    headroom_threshold: float = 0.95
    seed: int = 0
    n_restarts: int = 20
    raw_samples: int = 4096
    sigma_rel_for_prediction_noise: float = 0.10
    sigma_add_for_prediction_noise: float = 0.01


@dataclass
class E4Result:
    """One landscape at one kappa.

    Attributes:
        kappa: how much was hidden.
        rho: how far past the training corner the models were asked about.
        instance_id: which landscape.
        n_train: how many measurements (48).
        over_prediction: model name to how much it overshot. **Headline.**
        argmax_inside_subbox: whether each model's answer was inside the region
            it had actually seen. If it was, there was no extrapolation to
            detect and that instance says nothing.
        pi_width_at_argmax: interval width where each model claimed the peak.
            Only the second-order model and the GP have one.
        stationary_kind: what sort of turning point each polynomial found.
        discrimination: the actual measurement. **Read `.agreement` first.**
        parametric_converged: whether the practitioner-form fit worked.
        peak_inside_subbox: **the cell's own validity check.** True means the
            true best recipe was inside the region the models trained on, so
            there was nothing to extrapolate towards and this cell tests
            nothing. Such cells MUST be excluded from the headline pooling —
            `summarise` does that and reports how many it dropped.
        true_optimum_value: the best value actually achievable anywhere in the
            space. Over-prediction is only interpretable against this.
        notes: anything that went wrong, recorded rather than dropped.
    """

    kappa: float
    rho: float
    instance_id: str
    n_train: int
    over_prediction: dict[str, float]
    argmax_inside_subbox: dict[str, bool]
    pi_width_at_argmax: dict[str, float]
    stationary_kind: dict[str, str]
    discrimination: DiscriminationResult | None
    parametric_converged: bool
    peak_inside_subbox: bool = False
    true_optimum_value: float = float("nan")
    notes: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Can this cell say anything about extrapolation at all?"""
        return not self.peak_inside_subbox


def _sobol(bounds: Tensor, n: int, seed: int) -> Tensor:
    from torch.quasirandom import SobolEngine

    d = bounds.shape[1]
    unit = SobolEngine(dimension=d, scramble=True, seed=seed).draw(n).double()
    return bounds[0].double() + unit * (bounds[1] - bounds[0]).double()


def run_e4_cell(oracle: Oracle, config: E4Config, instance_id: str = "i0") -> E4Result:
    """Run Experiment 4 for one landscape at one kappa.

    Args:
        oracle: the made-up landscape.
        config: settings.
        instance_id: label carried into the results.

    Returns:
        An :class:`E4Result`.
    """
    x_star = oracle.x_star.double()
    d = int(x_star.shape[0])
    unit_cube = torch.stack(
        [torch.zeros(d, dtype=torch.double), torch.ones(d, dtype=torch.double)]
    )
    # The region every model is asked about. At rho = inf this is the whole
    # cube, which is what version 1 did. At rho = 2.0 it stops well short —
    # still a genuine extrapolation, but not one a reviewer can call staged.
    # The GP is still FITTED against the unit cube's bounds so that its input
    # scaling does not change with rho; only the question changes.
    scoring_box = extended_box_bounds(x_star, config.kappa, config.rho)
    notes: list[str] = []

    # --- 1 & 2: hide the space, then measure inside what is left ------------
    sub = sub_box_bounds(x_star, config.kappa)

    # --- 1b: CHECK THE ASSUMPTION THE WHOLE EXPERIMENT RESTS ON --------------
    #
    # E4 only means anything if the true best recipe lies OUTSIDE the corner we
    # trained on. Otherwise there is nothing to extrapolate towards, the models
    # are being asked about territory that contains no surprise, and the cell
    # silently measures nothing while still looking like a data point.
    #
    # The sub-box is built from each factor's peak taken one at a time. That is
    # only the true joint optimum when the factors do not interact. Person A's
    # oracle modulates each factor's peak according to the others, so the joint
    # optimum can sit somewhere the per-factor peaks do not predict — possibly
    # INSIDE the corner. A flagged this as landing in B's lane (OPEN-QUESTIONS
    # Q13) and they were right: nothing here was checking it.
    #
    # So find the real optimum and look.
    true_x, true_best, _ = constrained_argmax(
        oracle.truth, scoring_box,
        n_restarts=config.n_restarts, raw_samples=config.raw_samples,
        seed=config.seed,
    )
    peak_inside = bool(
        torch.all(true_x >= sub[0] - 1e-9) and torch.all(true_x <= sub[1] + 1e-9)
    )
    if peak_inside:
        notes.append(
            "TRUE OPTIMUM LIES INSIDE THE TRAINING CORNER — this cell cannot "
            "test extrapolation at all and must be excluded from the headline "
            "pooling. Lower kappa if it happens often. (Never raise x*.)"
        )

    design = central_composite(
        d, n_centre=config.n_centre, n_derived=config.n_derived,
        face_centred=config.face_centred,
    )
    # Identical points for all four models. Not a detail — the interval formula
    # depends entirely on which points were measured.
    train_X = scale_to_box(design.coded, sub)
    train_Y, train_Yvar = oracle.observe(train_X)

    # --- 3: fit four models to exactly the same data ------------------------
    second = fit_second_order(train_X, train_Y)
    stepwise = fit_stepwise_third_order(train_X, train_Y)
    gp = build_gp(train_X, train_Y, train_Yvar, unit_cube)
    para = fit_practitioner_parametric(train_X, train_Y, seed=config.seed)
    if not para.converged:
        notes.append(f"practitioner fit did not converge: {para.message}")

    def gp_predict(X: Tensor) -> Tensor:
        return predictive(gp, X).mean

    predictors: dict[str, object] = {
        "second_order": second.predict,
        "stepwise_third_order": stepwise.predict,
        "gp": gp_predict,
    }
    if para.converged:
        predictors["parametric"] = para.predict

    # --- 4 & 5: where does each say the peak is, and what is really there? ---
    over_prediction: dict[str, float] = {}
    inside: dict[str, bool] = {}
    results: dict[str, OverPrediction] = {}
    for name, fn in predictors.items():
        res = over_prediction_at_constrained_argmax(
            fn, oracle.truth, scoring_box,
            n_restarts=config.n_restarts, raw_samples=config.raw_samples,
            seed=config.seed,
        )
        results[name] = res
        over_prediction[name] = res.over_prediction
        inside[name] = bool(
            torch.all(res.x_argmax >= sub[0] - 1e-12)
            and torch.all(res.x_argmax <= sub[1] + 1e-12)
        )
    for missing in set(MODEL_NAMES) - set(predictors):
        over_prediction[missing] = float("nan")
        inside[missing] = False

    if all(inside[n] for n in predictors):
        notes.append(
            "every model's answer fell inside the region it had seen — no "
            "extrapolation occurred, so this cell cannot show the effect"
        )

    # --- 5b: how confident was each, where it claimed the peak? -------------
    # Second-order and GP only. The stepwise model is refused an interval on
    # purpose (post-selection inference); the practitioner fit has none either.
    pi_width: dict[str, float] = {n: float("nan") for n in MODEL_NAMES}
    if "second_order" in results:
        x0 = results["second_order"].x_argmax.unsqueeze(0)
        pi_width["second_order"] = float(second.prediction_interval_width(x0))
    if "gp" in results:
        x0 = results["gp"].x_argmax.unsqueeze(0)
        noise = _plugin_noise(gp, x0, config)
        lo, hi = predictive(gp, x0, noise=noise).interval()
        pi_width["gp"] = float(hi - lo)

    # --- 6: what kind of turning point? Descriptive, as a distribution ------
    stationary = {
        "second_order": second.stationary_point(sub).kind,
        "stepwise_third_order": stepwise.stationary_point(sub).kind,
    }

    # --- 7: the discrimination test — the actual measurement ----------------
    cand = _sobol(scoring_box, config.n_candidates, seed=config.seed + 991)
    gp_sd = predictive(gp, cand, noise=_plugin_noise(gp, cand, config)).stddev
    poly_pi = second.prediction_interval_width(cand)
    nn_dist = nearest_neighbour_distance(cand, train_X)
    poly_err = (second.predict(cand) - oracle.truth(cand)).abs()

    discrimination = discrimination_test(
        gp_sd, poly_pi, nn_dist, poly_err,
        tau_quantile=config.tau_quantile,
        headroom_threshold=config.headroom_threshold,
    )
    if not discrimination.agreement.has_headroom:
        notes.append(discrimination.agreement.summary())

    return E4Result(
        kappa=config.kappa,
        rho=config.rho,
        instance_id=instance_id,
        n_train=int(train_X.shape[0]),
        over_prediction=over_prediction,
        argmax_inside_subbox=inside,
        pi_width_at_argmax=pi_width,
        stationary_kind=stationary,
        discrimination=discrimination,
        parametric_converged=para.converged,
        peak_inside_subbox=peak_inside,
        true_optimum_value=true_best,
        notes=notes,
    )


def _plugin_noise(gp, X: Tensor, config: E4Config) -> Tensor:
    """Expected measurement noise at recipes nobody has run.

    Noise at an unrun recipe is a **modelling assumption, not an observation**.
    We state ours: the same relationship between signal size and noise that the
    lab would assume, applied to the model's own prediction.

    Left to itself the library would quietly average all the noise it had seen
    and use that flat figure everywhere — see `surrogate.predictive`. Supplying
    this explicitly is what avoids that, and it goes in the methods section.
    """
    mu = predictive(gp, X).mean
    return mu.pow(2) * config.sigma_rel_for_prediction_noise**2 + (
        config.sigma_add_for_prediction_noise**2
    )



def _aggregate_by_instance(rows, extract) -> dict[str, float]:
    """Collapse each landscape's cells to one number before any error bar.

    **This is a correctness fix, not a refinement.** Cells from the same
    landscape at different κ are four measurements *of the same landscape* —
    they are not four independent things. Handing all of them to a bootstrap
    as if they were independent inflates the effective sample size fourfold
    and makes the interval too narrow. Measured here: **1.45× too narrow.**

    The project spec already states the rule ("bootstrap at the instance level
    only"). It was applied correctly to points within a run and then missed
    across κ — right principle, wrong place.

    Aggregating first is not a compromise. For a mean or a paired mean
    difference on a balanced design — which is exactly what is computed here —
    it is *mathematically equivalent* to the cluster bootstrap (Field & Welsh
    2007), and it needs no new machinery. What it gives up is the trend across
    κ, which is reported separately and per-κ anyway, so nothing is lost.

    Args:
        rows: cells, each carrying an ``instance_id``.
        extract: pulls the number of interest out of one cell.

    Returns:
        instance id to its mean, skipping non-finite values.
    """
    by_instance: dict[str, list[float]] = {}
    for r in rows:
        by_instance.setdefault(r.instance_id, []).append(float(extract(r)))
    out: dict[str, float] = {}
    for key, vals in by_instance.items():
        finite = [v for v in vals if np.isfinite(v)]
        if finite:
            out[key] = float(np.mean(finite))
    return out


def _paired_on_shared(a: dict[str, float], b: dict[str, float]):
    """Line two scorers up landscape by landscape before differencing them."""
    shared = sorted(set(a) & set(b))
    return [a[k] for k in shared], [b[k] for k in shared]


def summarise(results: list[E4Result], model: str = "second_order",
              equivalence_bound: float = 0.08) -> dict:
    """Pool cells into the numbers that go in the paper.

    Returns a dict with the mean overshoot, the fraction of cells where
    extrapolation actually happened, the turning-point breakdown, and the
    discrimination comparison against the model-free null.
    """
    from boec.discrimination import (
        equivalence_bound_test,
        sign_flip_test,
        instance_bootstrap_ci,
        paired_difference_ci,
    )

    # EXCLUDE cells where the true optimum sat inside the training corner.
    # Those cells had nothing to extrapolate towards, so pooling them in would
    # dilute the headline with data points that tested nothing. The count is
    # reported, never silently dropped — a high count means kappa is too high.
    n_all = len(results)
    excluded = [r for r in results if not r.is_valid]
    results = [r for r in results if r.is_valid]
    if not results:
        return {
            "model": model,
            "n_cells": 0,
            "n_cells_total": n_all,
            "n_cells_excluded_peak_inside_subbox": len(excluded),
            "error": (
                "every cell had its true optimum inside the training corner, so "
                "none of them tested extrapolation. Lower kappa. Never raise x*."
            ),
        }

    # One value per landscape, never one per cell — see _aggregate_by_instance.
    over_by_instance = _aggregate_by_instance(
        results, lambda r: r.over_prediction.get(model, float("nan"))
    )
    point, lo, hi = instance_bootstrap_ci(list(over_by_instance.values()))

    kinds: dict[str, int] = {}
    for r in results:
        k = r.stationary_kind.get(model, "n/a")
        kinds[k] = kinds.get(k, 0) + 1

    usable = [r for r in results if r.discrimination is not None]
    gp_by = _aggregate_by_instance(usable, lambda r: r.discrimination.spearman["gp_predictive_sd"])
    nn_by = _aggregate_by_instance(usable, lambda r: r.discrimination.spearman["nearest_neighbour_distance"])
    poly_by = _aggregate_by_instance(usable, lambda r: r.discrimination.spearman["second_order_pi_width"])
    gp_rho, nn_rho, poly_rho = list(gp_by.values()), list(nn_by.values()), list(poly_by.values())
    gp_v_nn = _paired_on_shared(gp_by, nn_by)
    gp_v_poly = _paired_on_shared(gp_by, poly_by)
    gp_nn_diffs = [a - b for a, b in zip(*gp_v_nn, strict=True)]
    sign_p, sign_n, sign_exact, sign_se = sign_flip_test(gp_nn_diffs)
    equiv_upper, equiv_below, equiv_verdict = equivalence_bound_test(
        gp_nn_diffs, equivalence_bound
    )

    return {
        "model": model,
        "n_cells": len(results),
        "n_cells_total": n_all,
        # A high exclusion count is itself a finding: it means the training
        # corner was not actually excluding the peak, so kappa is too high.
        "n_cells_excluded_peak_inside_subbox": len(excluded),
        "over_prediction_mean": point,
        "over_prediction_ci": (lo, hi),
        "fraction_extrapolated": float(
            np.mean([not r.argmax_inside_subbox.get(model, False) for r in results])
        ),
        "stationary_kinds": kinds,
        "spearman_gp": instance_bootstrap_ci(gp_rho),
        "spearman_nearest_neighbour": instance_bootstrap_ci(nn_rho),
        "spearman_poly_pi": instance_bootstrap_ci(poly_rho),
        # THE HEADLINE COMPARISON. Do NOT read it off the three intervals above
        # by checking whether they overlap — the scorers are measured on the
        # same landscapes, so most of their variation is shared and cancels in
        # the difference. Comparing the intervals side by side throws that
        # cancellation away and can hide a real effect entirely.
        "gp_beats_null_paired": paired_difference_ci(*gp_v_nn),
        "gp_beats_poly_paired": paired_difference_ci(*gp_v_poly),
        # Distribution-free confirmation. At this many landscapes every possible
        # arrangement of signs can be enumerated, so this needs no asymptotics
        # at a cluster count where bootstrap methods are known to be optimistic.
        "gp_beats_null_exact_p": sign_p,
        "gp_beats_null_exact_n_landscapes": sign_n,
        "gp_beats_null_exact_is_enumerated": sign_exact,
        # Non-zero when the p-value was sampled rather than enumerated. Quote
        # the p to more digits than this and you are quoting noise.
        "gp_beats_null_p_monte_carlo_se": sign_se,
        # Turns "not significant" into an actual claim about the world.
        # Bound pre-registered in configs/experiment/e4.yaml.
        "gp_advantage_upper_limit": equiv_upper,
        "gp_advantage_below_bound": equiv_below,
        "gp_advantage_verdict": equiv_verdict,
        "n_cells_without_headroom": sum(
            1 for r in usable if not r.discrimination.agreement.has_headroom
        ),
        "parametric_failure_rate": float(
            np.mean([not r.parametric_converged for r in results])
        ),
    }


# ===========================================================================
# E4b — the design-boundary variant. REPORTED, NOT CLAIMED.
# ===========================================================================
#
# WHAT THIS IS, IN PLAIN LANGUAGE
#
# E4a is about a model guessing badly outside what it has seen. E4b is about a
# completely different failure, and it is the one that actually happened in the
# published study.
#
# There, one ingredient's best amount was LOWER than the lowest amount they
# were able to test. Below a certain concentration the cells would not stick to
# the plate at all, so the experiment could not go there. The best recipe was
# outside the range, not because anyone modelled anything badly, but because
# the range itself excluded it.
#
# WHY WE REPORT THIS AND DO NOT CLAIM IT
#
# **The traditional method handles this case correctly.** Its fitted
# coefficient for that ingredient comes out clearly negative — "less is better"
# — and that signal is right there for anyone to read. The original authors DID
# read it, and did test the recipe with that ingredient removed, and it worked
# very well.
#
# So this is not a failure of the modelling. It is a limit of the experimental
# range. The sophisticated model has no advantage here whatsoever, and claiming
# otherwise would be indefensible to anyone who has read the source paper.
#
# We measure it, we report it, and we say plainly that it is not our result.
# Claim E4a. Report E4b.
# ===========================================================================


@dataclass
class E4bResult:
    """The design-boundary case. Descriptive.

    Attributes:
        factor: which ingredient had its best amount excluded.
        true_optimum: where that ingredient actually wanted to be.
        design_floor: the lowest amount the design could test.
        polynomial_slope: the fitted coefficient for that ingredient. Negative
            means the model is correctly saying "less is better".
        polynomial_signals_lower_is_better: whether it got it right.
        argmax_at_floor: whether every model piled up against the boundary,
            which is the visible symptom.
        gp_signals_lower_is_better: whether the sophisticated model adds
            anything. **Expected to be no.**
        note: the honest framing, carried with the result.
    """

    factor: int
    true_optimum: float
    design_floor: float
    polynomial_slope: float
    polynomial_signals_lower_is_better: bool
    argmax_at_floor: dict[str, bool]
    gp_signals_lower_is_better: bool
    note: str


def run_e4b_cell(
    oracle: Oracle,
    config: E4Config,
    *,
    excluded_factor: int = 0,
    floor_multiplier: float = 1.6,
) -> E4bResult:
    """Run the design-boundary variant for one landscape.

    Builds a design whose **lower** bound for one ingredient sits above that
    ingredient's true best amount, so the best recipe is unreachable by
    construction — the published study's situation.

    Args:
        oracle: the landscape.
        config: settings.
        excluded_factor: which ingredient to put out of reach.
        floor_multiplier: how far above its true best the floor sits. Must
            exceed 1.

    Returns:
        An :class:`E4bResult`.
    """
    if floor_multiplier <= 1.0:
        raise ValueError(
            f"floor_multiplier must exceed 1 or the optimum is still reachable, "
            f"got {floor_multiplier}"
        )
    x_star = oracle.x_star.double()
    d = int(x_star.shape[0])
    j = excluded_factor

    # Design box: normal for every ingredient except one, whose floor is pushed
    # above its true best. That best is now unreachable, by construction.
    lo = torch.zeros(d, dtype=torch.double)
    hi = config.kappa * x_star.clone()
    floor = float(min(x_star[j] * floor_multiplier, 0.9))
    lo[j] = floor
    hi[j] = max(floor + 0.05, float(x_star[j] * floor_multiplier + 0.1))
    box = torch.stack([lo, hi])

    design = central_composite(
        d, n_centre=config.n_centre, n_derived=config.n_derived,
        face_centred=config.face_centred,
    )
    train_X = scale_to_box(design.coded, box)
    train_Y, train_Yvar = oracle.observe(train_X)

    second = fit_second_order(train_X, train_Y)
    gp = build_gp(train_X, train_Y, train_Yvar, box)

    # The polynomial's linear coefficient for the excluded ingredient. Negative
    # means it is correctly saying "less would be better" — the signal the
    # original authors read and acted on.
    slope = float(second.beta[1 + j])

    # Does the GP say the same? Compare its prediction at the floor against a
    # little way above it. This is the fair test of whether it adds anything.
    probe_lo = ((box[0] + box[1]) / 2).clone().unsqueeze(0)
    probe_hi = probe_lo.clone()
    probe_lo[0, j] = box[0][j]
    probe_hi[0, j] = box[0][j] + 0.25 * (box[1][j] - box[0][j])
    gp_slope = float(predictive(gp, probe_hi).mean - predictive(gp, probe_lo).mean)

    at_floor: dict[str, bool] = {}
    for name, fn in (("second_order", second.predict), ("gp", lambda X: predictive(gp, X).mean)):
        res = over_prediction_at_constrained_argmax(
            fn, oracle.truth, box,
            n_restarts=max(4, config.n_restarts // 2),
            raw_samples=config.raw_samples, seed=config.seed,
        )
        at_floor[name] = bool(abs(float(res.x_argmax[j]) - floor) < 1e-3)

    return E4bResult(
        factor=j,
        true_optimum=float(x_star[j]),
        design_floor=floor,
        polynomial_slope=slope,
        polynomial_signals_lower_is_better=slope < 0,
        argmax_at_floor=at_floor,
        gp_signals_lower_is_better=gp_slope < 0,
        note=(
            "REPORTED, NOT CLAIMED. This is a limit of the experimental range, "
            "not a modelling failure. The polynomial signals 'lower is better' "
            "correctly, which is exactly what the original authors observed and "
            "acted on. The GP has no advantage here and we do not claim one."
        ),
    )
