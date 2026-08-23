"""Rule L1 -- the frozen local-exploitation allocation for `spade_cf_m{0,4,8}`.

Registered in ``docs/SPADE-FINAL-SPEC.md`` §3.2, frozen at commit `c4f58d3`, **before this
file existed**.

------------------------------------------------------------------------------
WHY THE SIGNATURE IS THE FIRST TEST
------------------------------------------------------------------------------

L1 may not inspect plate-2 outcomes, truth at unobserved locations, final metrics, or any
competitor's output. This project already learned that a *convention* is not a guard: the
Version C detector statistics take no ``truth`` argument **architecturally**, so a scoring
function cannot be wired into the decision path by accident (``src/boec/versionc.py`` module
docstring).

L1 follows that pattern and goes one step further -- it takes **no model object at all**,
only arrays. A model carries a ``.posterior`` and therefore a route to anything the caller
has already computed; arrays carry nothing. The no-oracle-access property is then a fact
about the type signature rather than a promise in a docstring.
"""

from __future__ import annotations

import pytest
import torch

from boec.final_spade import local_wells
from boec.versionc import n_effective


def _lengthscales(d: int, value: float = 0.25) -> torch.Tensor:
    return torch.full((d,), float(value), dtype=torch.double)


def _grid_candidates(n: int, d: int, seed: int = 0) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    return torch.rand(n, d, generator=g, dtype=torch.double)


def _peaked_mean(cand: torch.Tensor, peak: torch.Tensor) -> torch.Tensor:
    """A mean surface whose argmax is exactly the candidate nearest ``peak``."""
    return -((cand - peak) ** 2).sum(dim=1)


# ---------------------------------------------------------------------------
# The property the rule exists for
# ---------------------------------------------------------------------------

def test_every_local_well_lands_inside_the_ard_ball_that_defines_n_effective():
    """L1's radius is 1 because that IS ``n_effective``'s bound -- so each local well
    provably increments the statistic §9.3 identified as governing the identification gap.

    This is the whole justification for the rule. If a well can land outside the ball the
    radius is just a tuned constant and the registered rationale is false.
    """
    d = 4
    cand = _grid_candidates(2048, d, seed=1)
    peak = torch.full((d,), 0.5, dtype=torch.double)
    mean = _peaked_mean(cand, peak)
    X1 = _grid_candidates(40, d, seed=2)
    ls = _lengthscales(d, 0.30)

    X_loc, diag = local_wells(cand, mean, X1, ls, m=4)

    x_hat = torch.as_tensor(diag["x_hat"], dtype=torch.double)
    dist = ((X_loc - x_hat) / ls).pow(2).sum(dim=1).sqrt()
    assert bool((dist <= 1.0 + 1e-12).all()), f"a local well escaped the ball: {dist.tolist()}"


def test_local_wells_raise_n_effective_relative_to_the_plate_one_design_alone():
    """The rule's purpose, measured on the registered statistic rather than asserted."""
    d = 4
    cand = _grid_candidates(2048, d, seed=3)
    peak = torch.full((d,), 0.5, dtype=torch.double)
    mean = _peaked_mean(cand, peak)
    X1 = _grid_candidates(40, d, seed=4)
    ls = _lengthscales(d, 0.30)

    X_loc, diag = local_wells(cand, mean, X1, ls, m=4)
    x_hat = torch.as_tensor(diag["x_hat"], dtype=torch.double)

    before = n_effective(X1, x_hat, ls)
    after = n_effective(torch.cat([X1, X_loc]), x_hat, ls)
    assert after == before + 4, f"n_eff went {before} -> {after}, expected +4"


def test_x_hat_is_the_grid_argmax_of_the_posterior_mean():
    """A GRID argmax, not a continuous optimiser. §4.1 records that this project's one
    non-reproducible path was a post-hoc L-BFGS-B locator with 20 restarts."""
    d = 3
    cand = _grid_candidates(512, d, seed=5)
    peak = torch.tensor([0.2, 0.8, 0.4], dtype=torch.double)
    mean = _peaked_mean(cand, peak)
    X1 = _grid_candidates(20, d, seed=6)

    _, diag = local_wells(cand, mean, X1, _lengthscales(d), m=2)

    expected = cand[int(mean.argmax())]
    assert torch.allclose(torch.as_tensor(diag["x_hat"], dtype=torch.double), expected)


# ---------------------------------------------------------------------------
# Determinism and budget
# ---------------------------------------------------------------------------

def test_the_rule_is_bitwise_deterministic():
    d = 5
    cand = _grid_candidates(1024, d, seed=7)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=8)
    ls = _lengthscales(d)

    a, da = local_wells(cand, mean, X1, ls, m=4)
    b, db = local_wells(cand, mean, X1, ls, m=4)

    assert torch.equal(a, b)
    assert da["x_hat"] == db["x_hat"]


def test_m_zero_returns_no_wells_so_m0_is_exactly_the_boundary_arm():
    """`spade_cf_m0` must be bit-identical to pure boundary allocation, or the m=0 arm is
    not the control it is registered as."""
    d = 4
    cand = _grid_candidates(512, d, seed=9)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=10)

    X_loc, diag = local_wells(cand, mean, X1, _lengthscales(d), m=0)

    assert X_loc.shape == (0, d)
    assert diag["m_local_short"] is False


def test_exactly_m_wells_are_returned_when_the_ball_is_rich_enough():
    d = 4
    cand = _grid_candidates(4096, d, seed=11)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=12)

    for m in (1, 4, 8):
        X_loc, diag = local_wells(cand, mean, X1, _lengthscales(d, 0.4), m=m)
        assert X_loc.shape == (m, d), f"m={m} gave {tuple(X_loc.shape)}"
        assert diag["m_local_short"] is False


def test_local_wells_are_distinct_points():
    """Greedy maximin must not return the same candidate twice -- a duplicated well is a
    wasted well and would silently break the equal-well budget."""
    d = 4
    cand = _grid_candidates(2048, d, seed=13)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=14)

    X_loc, _ = local_wells(cand, mean, X1, _lengthscales(d, 0.4), m=8)

    assert torch.unique(X_loc, dim=0).shape[0] == 8


# ---------------------------------------------------------------------------
# The short-ball case, recorded rather than absorbed
# ---------------------------------------------------------------------------

def test_a_ball_too_poor_to_fill_reports_short_rather_than_silently_returning_fewer():
    """§3.2 step 5. The runner falls back to the boundary rule for the remainder, and the
    row records that it happened. A silent short return would break the well budget and
    make `m4` secretly an `m2`."""
    d = 6
    cand = _grid_candidates(256, d, seed=15)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(40, d, seed=16)
    # A tiny lengthscale makes the ARD ball almost empty at this candidate density.
    ls = _lengthscales(d, 0.01)

    X_loc, diag = local_wells(cand, mean, X1, ls, m=8)

    assert diag["m_local_short"] is True
    assert X_loc.shape[0] < 8
    assert diag["n_in_ball"] == X_loc.shape[0]


# ---------------------------------------------------------------------------
# The architectural guard
# ---------------------------------------------------------------------------

def test_local_wells_accepts_no_truth_or_model_argument():
    """The no-oracle-access property, enforced on the signature itself.

    ``versionc``'s detector statistics use exactly this guard. A rule that *could* be handed
    truth eventually is, and the failure is silent.
    """
    import inspect

    names = set(inspect.signature(local_wells).parameters)
    for forbidden in ("truth", "model", "oracle", "orc", "y", "Y"):
        assert forbidden not in names, (
            f"L1's signature exposes {forbidden!r}; the rule must be computable from "
            "plate-1 arrays alone")


def test_a_width_mismatch_raises_rather_than_broadcasting():
    """``n_effective`` raises on this for the same reason: a broadcast answers a different
    question silently."""
    d = 4
    cand = _grid_candidates(256, d, seed=17)
    mean = _peaked_mean(cand, torch.full((d,), 0.5, dtype=torch.double))
    X1 = _grid_candidates(20, d, seed=18)

    with pytest.raises(ValueError, match="width|lengthscale"):
        local_wells(cand, mean, X1, _lengthscales(d + 1), m=2)
