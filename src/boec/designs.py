"""Experimental designs — which points to actually measure.

OWNERSHIP: specced as Person A's, written by Person B because A's PF1 check
cannot run without it. **A: say the word and this moves back.**

Phase 1 only. Thrown away after the paper.

------------------------------------------------------------------------------
WHAT THIS FILE IS FOR, IN PLAIN LANGUAGE
------------------------------------------------------------------------------

Suppose you can afford 48 experiments and you have 6 ingredients to vary. Which
48 combinations do you run?

You could pick at random. You could space them evenly. Or you could use a
*designed* experiment — a specific, deliberate pattern that statisticians worked
out to squeeze the most information out of a fixed budget. That is what this
file builds.

The pattern used here is a **central composite design**, and it has three parts:

  1. **Corners.** Every ingredient at either its low or its high setting. This
     is where you learn about ingredients interacting with each other.
  2. **Axial points.** One ingredient pushed to an extreme while all the others
     sit at the middle. This is where you learn whether a response *curves* —
     whether more of something starts helping less, or starts hurting.
  3. **Centre points.** Everything at the middle, repeated several times.
     Running the same thing more than once tells you how noisy your measurement
     is, which is the only way to know whether a difference you see is real.

**Why the exact pattern matters here, and is not a detail.** The comparison at
the heart of Experiment 4 is between the error bars a curved-model fit produces
and the error bars a Gaussian process produces. But the curved model's error
bars are computed *from the design itself* — change which 48 points you measure
and the error bars change, without any data changing. So if we used a different
pattern from the one a real practitioner would use, we would be comparing
against a straw man. This file exists to make that comparison fair.

**Why we cannot use all the corners.** With 6 ingredients there are 2^6 = 64
corners — already more than our budget of 48 before we have added a single
axial or centre point. So we use a carefully chosen *half* of them: 32 corners,
selected so that nothing we care about gets confused with anything else. Add 12
axial points and 4 centre points and you land on exactly 48.

------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

import numpy as np
import torch
from torch import Tensor

__all__ = [
    "Design",
    "central_composite",
    "fractional_factorial",
    "full_factorial",
    "scale_to_box",
    "screening_design",
    "sub_box_bounds",
]


# Minimum-aberration generators for the fractional designs we need.
#
# Reading `(6, 1): [(5, (0, 1, 2, 3, 4))]` — with 6 factors and 1 of them
# derived, factor 5 is set to the product of factors 0-4. The defining relation
# is then 6 letters long, which is what "resolution VI" means: no effect we care
# about in a second-order model gets confused with any other.
#
# Resolution, in plain terms, is how badly effects get tangled together. Higher
# is better. A second-order model needs at least resolution V to be safe.
_GENERATORS: dict[tuple[int, int], list[tuple[int, tuple[int, ...]]]] = {
    (5, 1): [(4, (0, 1, 2, 3))],                    # 2^(5-1), resolution V
    (6, 1): [(5, (0, 1, 2, 3, 4))],                 # 2^(6-1), resolution VI
    (7, 1): [(6, (0, 1, 2, 3, 4, 5))],              # 2^(7-1), resolution VII
    (7, 2): [(5, (0, 1, 2, 3)), (6, (0, 1, 4))],    # 2^(7-2), resolution IV
    (8, 2): [(6, (0, 1, 2, 3)), (7, (0, 1, 4, 5))],  # 2^(8-2), resolution V
}

_RESOLUTION: dict[tuple[int, int], int] = {
    (5, 1): 5,
    (6, 1): 6,
    (7, 1): 7,
    (7, 2): 4,
    (8, 2): 5,
}


@dataclass(frozen=True)
class Design:
    """A set of points to measure, plus a record of how they were chosen.

    Attributes:
        points: ``(n, d)`` the actual settings to run, in whatever box was
            requested. This is the thing you hand to the lab or the oracle.
        coded: ``(n, d)`` the same points on the statistician's -1 to +1 scale,
            where -1 is the low setting, +1 the high, and 0 the middle.
        kind: human-readable name, e.g. ``"ccd-face-centred"``.
        n_factorial: how many corner points.
        n_axial: how many axial points.
        n_centre: how many repeats of the centre.
        resolution: how well-separated the effects are; ``None`` if every
            corner was used, in which case nothing is confused with anything.
        alpha: how far out the axial points sit, on the coded scale. 1.0 means
            they sit exactly on the face of the cube.
    """

    points: Tensor
    coded: Tensor
    kind: str
    n_factorial: int
    n_axial: int
    n_centre: int
    resolution: int | None
    alpha: float

    def __len__(self) -> int:
        return int(self.points.shape[0])

    @property
    def n_runs(self) -> int:
        return len(self)


def full_factorial(d: int) -> Tensor:
    """Every corner of the cube: ``2**d`` points, each coordinate -1 or +1.

    Args:
        d: number of factors.

    Returns:
        ``(2**d, d)`` float64 tensor.
    """
    if d < 1:
        raise ValueError(f"d must be >= 1, got {d}")
    if d > 20:
        raise ValueError(f"2**{d} corners is unreasonable")
    rows = list(product([-1.0, 1.0], repeat=d))
    return torch.tensor(rows, dtype=torch.double)


def fractional_factorial(d: int, n_derived: int) -> tuple[Tensor, int]:
    """A carefully chosen fraction of the corners.

    With 6 factors there are 64 corners, which already exceeds a 48-run budget.
    This takes half of them — but not an arbitrary half. The half is chosen so
    that the effects a second-order model needs to estimate stay separable from
    one another.

    Args:
        d: number of factors.
        n_derived: how many factors are *derived* from the others rather than
            varied independently. ``1`` gives a half fraction, ``2`` a quarter.

    Returns:
        ``(points (2**(d - n_derived), d), resolution)``.

    Raises:
        ValueError: if no known generator exists for this combination. Rather
            than inventing one — a bad generator silently tangles effects
            together — this fails loudly.
    """
    if n_derived == 0:
        return full_factorial(d), 0
    key = (d, n_derived)
    if key not in _GENERATORS:
        raise ValueError(
            f"no known minimum-aberration generator for 2^({d}-{n_derived}). "
            "Refusing to invent one: a poorly chosen generator silently "
            "confuses effects with each other and nothing downstream notices."
        )

    n_base = d - n_derived
    base = full_factorial(n_base)
    out = torch.zeros(base.shape[0], d, dtype=torch.double)
    out[:, :n_base] = base
    for col, sources in _GENERATORS[key]:
        prod = torch.ones(base.shape[0], dtype=torch.double)
        for s in sources:
            prod = prod * base[:, s]
        out[:, col] = prod
    return out, _RESOLUTION[key]


def central_composite(
    d: int,
    *,
    n_centre: int = 4,
    n_derived: int = 0,
    face_centred: bool = True,
) -> Design:
    """Build a central composite design on the coded -1 to +1 cube.

    The default for Experiment 4 is ``d=6, n_derived=1, n_centre=4``, which
    gives 32 + 12 + 4 = **48 runs exactly** — the budget the spec calls for,
    and enough to fit all 28 terms of a second-order model with 20 runs' worth
    of slack left over to estimate the noise.

    Args:
        d: number of factors.
        n_centre: repeats at the centre. These are what let you estimate noise,
            so do not set this to zero.
        n_derived: 0 uses every corner; 1 uses half; 2 uses a quarter.
        face_centred: if True the axial points sit exactly on the faces of the
            cube (alpha = 1). If False they sit further out, at the distance
            that makes prediction error the same in every direction
            ("rotatable").

            **Face-centred is the default here on purpose.** Experiment 4 fits
            inside a deliberately small sub-box, and that sub-box's edge is a
            hard boundary — the whole point is that the model has not seen
            anything beyond it. Rotatable axial points would sit outside, which
            would defeat the experiment. At d=6 with a half fraction the
            rotatable distance is about 2.38, well outside the cube.

    Returns:
        A :class:`Design` on the coded cube. Use :func:`scale_to_box` to move it
        into real settings.
    """
    if n_centre < 1:
        raise ValueError("need at least one centre point to estimate noise")

    factorial, resolution = fractional_factorial(d, n_derived)
    n_fact = factorial.shape[0]

    alpha = 1.0 if face_centred else float(n_fact ** 0.25)

    axial = torch.zeros(2 * d, d, dtype=torch.double)
    for i in range(d):
        axial[2 * i, i] = -alpha
        axial[2 * i + 1, i] = alpha

    centre = torch.zeros(n_centre, d, dtype=torch.double)

    coded = torch.cat([factorial, axial, centre], dim=0)
    kind = f"ccd-{'face-centred' if face_centred else 'rotatable'}"
    if n_derived:
        kind += f"-half^{n_derived}"

    return Design(
        points=coded.clone(),
        coded=coded,
        kind=kind,
        n_factorial=n_fact,
        n_axial=2 * d,
        n_centre=n_centre,
        resolution=resolution if n_derived else None,
        alpha=alpha,
    )


def screening_design(d: int, *, n_centre: int = 3, n_derived: int | None = None) -> Design:
    """A cheap two-level screen — for A's DoE stage 1, not for Experiment 4.

    Stage 1 of a sequential DoE campaign is not trying to find the optimum. It
    is trying to work out *which ingredients matter at all*, so the expensive
    second stage can concentrate on those. That needs far fewer runs.

    Args:
        d: number of factors.
        n_centre: repeats at the centre.
        n_derived: how aggressive a fraction to take. Defaults to the largest
            fraction that keeps resolution at IV or better, so that main
            effects stay clean of two-factor interactions.

    Returns:
        A :class:`Design` with no axial points.
    """
    if n_derived is None:
        n_derived = 0
        for cand in (2, 1):
            if (d, cand) in _GENERATORS and _RESOLUTION[(d, cand)] >= 4:
                n_derived = cand
                break

    factorial, resolution = fractional_factorial(d, n_derived)
    centre = torch.zeros(n_centre, d, dtype=torch.double)
    coded = torch.cat([factorial, centre], dim=0)

    return Design(
        points=coded.clone(),
        coded=coded,
        kind=f"screening-2^({d}-{n_derived})" if n_derived else f"screening-2^{d}",
        n_factorial=factorial.shape[0],
        n_axial=0,
        n_centre=n_centre,
        resolution=resolution if n_derived else None,
        alpha=0.0,
    )


def scale_to_box(coded: Tensor, bounds: Tensor) -> Tensor:
    """Move points from the statistician's -1..+1 scale into real settings.

    -1 becomes the lower bound, +1 the upper, 0 the midpoint.

    Points outside -1..+1 — which rotatable axial points are — land outside the
    box. That is not silently corrected here, because silently pulling a design
    point back inside a boundary would change the design's statistical
    properties without saying so. Check it yourself if it matters.

    Args:
        coded: ``(n, d)`` on the -1..+1 scale.
        bounds: ``(2, d)``, row 0 lower and row 1 upper.

    Returns:
        ``(n, d)`` in real settings.
    """
    if bounds.ndim != 2 or bounds.shape[0] != 2:
        raise ValueError(f"bounds must be (2, d), got {tuple(bounds.shape)}")
    if coded.shape[1] != bounds.shape[1]:
        raise ValueError(
            f"coded has {coded.shape[1]} factors, bounds has {bounds.shape[1]}"
        )
    lo = bounds[0].double()
    hi = bounds[1].double()
    if not bool(torch.all(hi > lo)):
        raise ValueError("every upper bound must exceed its lower bound")
    return lo + (coded.double() + 1.0) / 2.0 * (hi - lo)


def sub_box_bounds(x_star: Tensor, kappa: float) -> Tensor:
    """The small training region for Experiment 4: ``[0, kappa * x*]`` per factor.

    This is the mechanism of the whole experiment. The model is trained only on
    a small corner of the space that stops short of where the response actually
    peaks, then asked about the rest. A model that does not know it is guessing
    will confidently point somewhere it has never seen.

    ``kappa`` controls how short it stops. Lower means the model sees less and
    has further to guess.

    **The invariant neither lane may break alone:** if over-prediction comes
    back too low, lower ``kappa``. **Never raise ``x*``.** Raising the peak
    towards the box edge flattens it, which silently breaks Person A's
    Experiment 2. Moving the box is safe; moving the peak is not.

    Args:
        x_star: ``(d,)`` the true peak location of each factor.
        kappa: fraction of the way to the peak, in ``(0, 1]``.

    Returns:
        ``(2, d)`` bounds.
    """
    if not 0.0 < kappa <= 1.0:
        raise ValueError(f"kappa must be in (0, 1], got {kappa}")
    if x_star.ndim != 1:
        raise ValueError(f"x_star must be (d,), got {tuple(x_star.shape)}")
    if not bool(torch.all(x_star > 0)):
        raise ValueError("every x_star must be positive")
    upper = kappa * x_star.double()
    return torch.stack([torch.zeros_like(upper), upper])


def second_order_rank_ok(coded: Tensor) -> bool:
    """Can this design actually support a full second-order fit?

    If not, the error-bar formula the whole Experiment 4 comparison rests on is
    undefined. Worth asserting before spending any compute.
    """
    from boec.rsm import second_order_design_matrix, second_order_n_terms

    d = coded.shape[1]
    p = second_order_n_terms(d)
    if coded.shape[0] <= p:
        return False
    M = second_order_design_matrix(coded)
    return bool(np.linalg.matrix_rank(M) == p)


def defining_relation_words(d: int, n_derived: int) -> list[tuple[int, ...]]:
    """The 'words' that describe which effects a fraction tangles together.

    Used by the tests to confirm the resolution claim rather than trusting the
    lookup table. The shortest word's length *is* the resolution.
    """
    if n_derived == 0:
        return []
    key = (d, n_derived)
    base_words = [tuple(sorted(sources + (col,))) for col, sources in _GENERATORS[key]]
    words = set(base_words)
    # Products of generators are also words in the defining relation.
    for r in range(2, len(base_words) + 1):
        for combo in combinations(base_words, r):
            sym: set[int] = set()
            for w in combo:
                sym ^= set(w)
            if sym:
                words.add(tuple(sorted(sym)))
    return sorted(words, key=len)
