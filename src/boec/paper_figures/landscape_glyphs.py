"""Deterministic two-dimensional response-landscape slices for Figure 1."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from boec.oracles import HillOracle, load_ensemble
from boec.replay import FAMILY_ORACLE


LANDSCAPE_FAMILIES = ("hill", "ackley", "hartmann6", "levy", "rosenbrock")


@dataclass(frozen=True)
class LandscapeSlice:
    """A normalized response surface on the first two oracle coordinates."""

    family: str
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray


def landscape_slice(family: str, resolution: int = 48) -> LandscapeSlice:
    """Hold non-displayed coordinates at the optimum and normalize the slice."""
    oracle = HillOracle(load_ensemble(6)[0]) if family == "hill" else FAMILY_ORACLE[family](6)
    grid = np.linspace(0.0, 1.0, resolution)
    gx, gy = np.meshgrid(grid, grid)
    points = np.repeat(oracle.optimum_x[None, :], resolution * resolution, axis=0)
    points[:, 0], points[:, 1] = gx.ravel(), gy.ravel()
    raw = oracle.f(points).reshape(resolution, resolution)
    scaled = (raw - raw.min()) / (raw.max() - raw.min())
    return LandscapeSlice(family, gx, gy, scaled)
