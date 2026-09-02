"""Effective resolution: certified volume measured in correlation cells, not box fraction.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------

Measured on `results/p8-certificate-families.json` (24,000 rows, 4,096 draws, gamma=0.95),
truth containment of the conservative excursion certificate is governed by the VOLUME it
claims, while the model-internal containment statistic used to choose that volume is
structurally blind to it:

    certified volume bin   model-internal   truth
    [0.001, 0.002]                 0.9835   1.000
    [0.014, 0.082]                 1.0000   0.991
    [0.326, 1.000]                 0.9982   0.552

The confound is not merely absent but reversed: inside the HIGHEST true-prevalence stratum
(>= 0.95, where the acceptable region is nearly the whole box and containment should be
easiest) containment still falls from 0.995 on small regions to 0.750 on large ones.

Calibrating a volume cap against held-out truth repairs the guarantee -- leave-one-family-out
it lifts levy 0.8958 -> 0.9730 and rosenbrock 0.8930 -> 0.9968 -- but the cap does NOT
transfer: hill/levy/rosenbrock calibrate to V* ~ 0.16-0.28 while ackley/hartmann6 need
V* ~ 0.0025, an 80x gap. The law is universal; the units are wrong.

------------------------------------------------------------------------------
THE HYPOTHESIS THIS MODULE MAKES COMPUTABLE
------------------------------------------------------------------------------

A simultaneous claim over a region fails once per *effectively independent location* the
region spans, not once per unit of box volume. Under an ARD kernel the correlation cell has
volume prod_i l_i, so the count is

    k_eff = V / prod_i min(l_i, 1)

The cap at 1 matters: a fitted lengthscale longer than the box does not create a cell larger
than the box, and leaving it uncapped reports a region as a *fraction* of one independent
location. At d=6 the project's own measured median ARD lengthscale is 0.5982 (n=40 plate 1,
`src/boec/lse.py`), so lengthscales near and above the box width are the normal case here,
not an edge case.

Lengthscales come from the campaign's own fitted GP. **Nothing in this module touches ground
truth**, so k_eff is available at run time, unlike `sup_err` and `grid_r2`.

------------------------------------------------------------------------------
WHAT IS AND IS NOT CLAIMED
------------------------------------------------------------------------------

That k_eff is the right conditioning variable is a REGISTERED PREDICTION, not a result. It is
adopted only if a volume cap expressed in k_eff transfers across families where a cap in box
volume does not -- the falsifiable test is written down in
`docs/SPADE-EFFECTIVE-RESOLUTION-SPEC.md` before any number is computed.

One measurement already supports it and is worth stating because it is counter-intuitive: on
ackley/hartmann6, certified volume separates contained from failed campaigns at 1.22 SD,
while the two GROUND-TRUTH accuracy statistics separate them at 0.25 (`sup_err`) and 0.26
(`grid_r2`). Volume predicts certificate failure better than model accuracy does, which is
the signature of a resolution-limited failure rather than an accuracy-limited one.
"""

from __future__ import annotations

from collections.abc import Sequence

from torch import Tensor

__all__ = ["effective_resolution"]


def effective_resolution(volume: float, lengthscales: Sequence[float] | Tensor) -> float:
    """How many effectively independent locations a region of ``volume`` spans.

    Args:
        volume: certified volume as a **fraction of the unit box**, in ``[0, 1]``. Passing
            a grid-point count instead silently inflates the result by the grid size, so
            values outside the unit interval are rejected rather than clipped.
        lengthscales: the fitted ARD lengthscales, one per dimension. Each is capped at the
            box width of 1 before multiplying: a lengthscale longer than the box means the
            whole box is a single correlation cell, not a cell larger than the box.

    Returns:
        ``volume / prod_i min(l_i, 1)``. Zero for an empty region.

    Raises:
        ValueError: on a volume outside ``[0, 1]``, an empty lengthscale vector, or a
            non-positive lengthscale (which would divide by zero and report infinite
            resolution).
    """
    v = float(volume)
    if not 0.0 <= v <= 1.0:
        raise ValueError(
            f"volume must be a fraction of the box in [0, 1], got {v} -- a value above 1 "
            "usually means a grid-point count was passed instead of a fraction")

    ell = [float(x) for x in (lengthscales.tolist() if isinstance(lengthscales, Tensor)
                              else lengthscales)]
    if not ell:
        raise ValueError("lengthscales is empty; k_eff is undefined without a dimension")
    if any(x <= 0.0 for x in ell):
        raise ValueError(f"lengthscales must all be positive, got {ell}")

    cell = 1.0
    for x in ell:
        cell *= min(x, 1.0)
    return v / cell
