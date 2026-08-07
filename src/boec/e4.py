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

from boec.designs import central_composite, scale_to_box, sub_box_bounds
from boec.discrimination import (
    DiscriminationResult,
    discrimination_test,
    nearest_neighbour_distance,
)
from boec.metrics import OverPrediction, over_prediction_at_constrained_argmax
from boec.parametric import fit_practitioner_parametric
from boec.rsm import fit_second_order, fit_stepwise_third_order
from boec.surrogate import build_gp, predictive

__all__ = ["E4Config", "E4Result", "Oracle", "run_e4_cell"]

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
        notes: anything that went wrong, recorded rather than dropped.
    """

    kappa: float
    instance_id: str
    n_train: int
    over_prediction: dict[str, float]
    argmax_inside_subbox: dict[str, bool]
    pi_width_at_argmax: dict[str, float]
    stationary_kind: dict[str, str]
    discrimination: DiscriminationResult | None
    parametric_converged: bool
    notes: list[str] = field(default_factory=list)


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
    notes: list[str] = []

    # --- 1 & 2: hide the space, then measure inside what is left ------------
    sub = sub_box_bounds(x_star, config.kappa)
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
            fn, oracle.truth, unit_cube,
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
    cand = _sobol(unit_cube, config.n_candidates, seed=config.seed + 991)
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
        instance_id=instance_id,
        n_train=int(train_X.shape[0]),
        over_prediction=over_prediction,
        argmax_inside_subbox=inside,
        pi_width_at_argmax=pi_width,
        stationary_kind=stationary,
        discrimination=discrimination,
        parametric_converged=para.converged,
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


def summarise(results: list[E4Result], model: str = "second_order") -> dict:
    """Pool cells into the numbers that go in the paper.

    Returns a dict with the mean overshoot, the fraction of cells where
    extrapolation actually happened, the turning-point breakdown, and the
    discrimination comparison against the model-free null.
    """
    from boec.discrimination import instance_bootstrap_ci

    over = [r.over_prediction.get(model, float("nan")) for r in results]
    point, lo, hi = instance_bootstrap_ci(over)

    kinds: dict[str, int] = {}
    for r in results:
        k = r.stationary_kind.get(model, "n/a")
        kinds[k] = kinds.get(k, 0) + 1

    usable = [r for r in results if r.discrimination is not None]
    gp_rho = [r.discrimination.spearman["gp_predictive_sd"] for r in usable]
    nn_rho = [r.discrimination.spearman["nearest_neighbour_distance"] for r in usable]
    poly_rho = [r.discrimination.spearman["second_order_pi_width"] for r in usable]

    return {
        "model": model,
        "n_cells": len(results),
        "over_prediction_mean": point,
        "over_prediction_ci": (lo, hi),
        "fraction_extrapolated": float(
            np.mean([not r.argmax_inside_subbox.get(model, False) for r in results])
        ),
        "stationary_kinds": kinds,
        "spearman_gp": instance_bootstrap_ci(gp_rho),
        "spearman_nearest_neighbour": instance_bootstrap_ci(nn_rho),
        "spearman_poly_pi": instance_bootstrap_ci(poly_rho),
        "n_cells_without_headroom": sum(
            1 for r in usable if not r.discrimination.agreement.has_headroom
        ),
        "parametric_failure_rate": float(
            np.mean([not r.parametric_converged for r in results])
        ),
    }
