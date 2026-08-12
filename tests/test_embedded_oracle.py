"""Q51 — guards for embedding a low-dimensional benchmark in a larger cube.

WHY THIS EXISTS
---------------
Q42 answered "you built the landscape that gave you your answer" with Hartmann6:
non-additive, deceptive, fifty years old, not ours. But `Hartmann6` is defined at d=6
only, so it ran at **2 of the 4 cells** every other family ran at — no d=8 at either
noise level. That is a gap in the one family that carries the argument, and it was a
property of the function rather than a choice.

Embedding closes it the way this project already builds its d=8 comparison: the Hill
oracle holds `n_active=4` at **both** dimensions and picks which coordinates are active
at random (`oracles.py`, `rng.choice(dim, n_act, replace=False)`), precisely so that
d=6 vs d=8 isolates **the cost of nuisance dimensions** rather than confounding
dimension with active-count. `Embedded` gives Hartmann6 the same structure: six active
coordinates, two inert, active subset chosen by a recorded seed.

THE PROPERTY THAT MATTERS, AND IT IS EXACT
-------------------------------------------
An inert coordinate must not move the response **at all** — not approximately. If it
does, the arm is not measuring nuisance dimensions, it is measuring a different
function. Tested as an exact equality over random draws, not a tolerance.
"""

from __future__ import annotations

import numpy as np
import pytest

from boec.oracles import Embedded, Hartmann6, UnitScaled


def test_inert_coordinates_do_not_move_the_response_at_all() -> None:
    o = Embedded(Hartmann6(), dim=8, seed=0)
    rng = np.random.default_rng(0)
    X = rng.random((200, 8))
    base = o.f(X)
    inert = np.setdiff1d(np.arange(8), o.active)
    assert inert.size == 2
    for _ in range(5):
        Y = X.copy()
        Y[:, inert] = rng.random((200, inert.size))
        assert np.array_equal(o.f(Y), base)          # exact, not approximate


def test_the_active_coordinates_carry_the_inner_function() -> None:
    inner = Hartmann6()
    o = Embedded(inner, dim=8, seed=0)
    rng = np.random.default_rng(1)
    Z = rng.random((50, 6))
    X = rng.random((50, 8))
    X[:, o.active] = Z
    assert np.allclose(o.f(X), inner.f(Z), rtol=0, atol=0)


def test_the_active_subset_is_seeded_and_reproducible() -> None:
    a = Embedded(Hartmann6(), dim=8, seed=3).active
    assert np.array_equal(a, Embedded(Hartmann6(), dim=8, seed=3).active)
    assert not np.array_equal(a, Embedded(Hartmann6(), dim=8, seed=4).active)
    assert len(set(a.tolist())) == 6 and a.max() < 8


def test_the_optimum_is_the_inner_optimum_and_is_attained() -> None:
    inner = Hartmann6()
    o = Embedded(inner, dim=8, seed=0)
    assert o.optimum_value == pytest.approx(inner.optimum_value)
    assert o.optimum_x.shape == (8,)
    assert float(o.f(o.optimum_x.reshape(1, -1))[0]) == pytest.approx(
        inner.optimum_value, abs=1e-4)


def test_the_optimum_is_not_the_box_centre() -> None:
    """Q42 voids rule A when the optimum sits at the exact box centre, because every
    screening and CCD design includes centre runs and would contain the answer for
    free. The inert coordinates are parked at the centre, so this checks the embedding
    does not accidentally trip that."""
    o = Embedded(Hartmann6(), dim=8, seed=0)
    assert not np.allclose(o.optimum_x, 0.5, atol=1e-9)


def test_embedding_into_its_own_dimension_is_the_identity() -> None:
    inner = Hartmann6()
    o = Embedded(inner, dim=6, seed=0)
    rng = np.random.default_rng(2)
    X = rng.random((30, 6))
    assert np.array_equal(o.active, np.arange(6))
    assert np.array_equal(o.f(X), inner.f(X))


def test_shrinking_is_refused() -> None:
    with pytest.raises(ValueError, match="at least"):
        Embedded(Hartmann6(), dim=4, seed=0)


def test_it_composes_with_unitscaled() -> None:
    """Every Q42 family is wrapped in UnitScaled so sigma_rel means the same thing
    across families. The embedded version must survive that unchanged."""
    o = UnitScaled(Embedded(Hartmann6(), dim=8, seed=0), floor_samples=4096)
    assert o.dim == 8
    assert float(o.f(o.optimum_x.reshape(1, -1))[0]) == pytest.approx(1.0, abs=1e-3)
