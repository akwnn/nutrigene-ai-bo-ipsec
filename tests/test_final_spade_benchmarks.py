"""The plate-2 composer -- fair budget, and the nesting that makes m0/m4/m8 comparable.

Spec §3.2/§4.1, frozen at ``c4f58d3``.

------------------------------------------------------------------------------
THE PROPERTY THESE TESTS EXIST TO PIN
------------------------------------------------------------------------------

``spade_cf_m0``, ``m4`` and ``m8`` must differ in **exactly one registered quantity** --
how many plate-2 wells go local instead of to the boundary. If they differ in anything
else, the allocation contrast is confounded and KF-5 measures the confound.

:func:`boec.lse.batch_lse` is **greedy with exclusion**, so a call at ``q=4`` returns
precisely the first four picks of a call at ``q=8``. That makes the arms **nested**:
``m4``'s boundary wells are a prefix of ``m0``'s. The nesting is not incidental -- it is
what lets the difference between the arms be attributed to the four substituted wells
rather than to a re-planned boundary batch, and it is asserted here rather than assumed.
"""

from __future__ import annotations

import pytest
import torch

from boec.designspace import gp_adapter
from boec.final_spade import spade_plate2
from boec.lse import batch_lse, exclusion_radius
from boec.norms import sobol_grid
from boec.replay import unit_bounds
from boec.runner import static_design
from boec.surrogate import build_gp
from boec.versionc import ard_lengthscales

N_PLATE1, N_PLATE2, DIM, CAND_N = 40, 8, 4, 1024
THETA = 0.6


@pytest.fixture(scope="module")
def fitted():
    """One real plate-1 fit, shared. A smooth deterministic response keeps the fixture
    fast without making the GP degenerate."""
    torch.manual_seed(0)
    bounds = unit_bounds(DIM)
    X1 = static_design(bounds, "lhs", N_PLATE1, 0)
    Y = (torch.sin(3 * X1).sum(dim=1, keepdim=True) * 0.2 + 0.5).double()
    Yvar = torch.full_like(Y, 0.01)
    model = build_gp(X1, Y, Yvar, bounds)
    cand = sobol_grid(DIM, CAND_N, seed=0)
    return {"model": model, "ad": gp_adapter(model), "X1": X1, "cand": cand,
            "ls": ard_lengthscales(model), "radius": exclusion_radius(model)}


def _plate2(fitted, m):
    return spade_plate2(fitted["ad"], fitted["cand"], fitted["X1"], THETA,
                        N_PLATE2, m, fitted["ls"], exclude=fitted["radius"])


# ---------------------------------------------------------------------------
# Fair budget -- spec §4.1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("m", [0, 4, 8])
def test_every_allocation_spends_exactly_the_same_plate_two_budget(fitted, m):
    """The equal-well benchmark. An arm that quietly spends 7 or 9 wells is not the arm
    the contrast is registered on."""
    X2, diag = _plate2(fitted, m)
    assert X2.shape == (N_PLATE2, DIM), f"m={m} spent {X2.shape[0]} wells"
    assert diag["m_placed"] + diag["n_boundary"] == N_PLATE2


@pytest.mark.parametrize("m", [0, 4, 8])
def test_the_split_between_local_and_boundary_is_exactly_m(fitted, m):
    X2, diag = _plate2(fitted, m)
    assert diag["m_placed"] == m
    assert diag["n_boundary"] == N_PLATE2 - m


def test_plate_two_wells_are_distinct(fitted):
    """A duplicated well is a wasted well and silently breaks the equal-well budget."""
    for m in (0, 4, 8):
        X2, _ = _plate2(fitted, m)
        assert torch.unique(X2, dim=0).shape[0] == N_PLATE2, f"m={m} duplicated a well"


# ---------------------------------------------------------------------------
# m0 IS the boundary arm -- the control must be exact, not merely similar
# ---------------------------------------------------------------------------

def test_m0_plate_two_is_bit_identical_to_the_plain_boundary_rule(fitted):
    """`spade_cf_m0` is registered as the pure boundary arm. If it is only *approximately*
    batch_lse's batch then it is a fourth arm, not the control the other two are measured
    against."""
    X2, _ = _plate2(fitted, 0)
    expected = batch_lse(fitted["ad"], fitted["cand"], THETA, N_PLATE2,
                         exclude=fitted["radius"])
    assert torch.equal(X2, expected)


# ---------------------------------------------------------------------------
# The nesting -- what makes the allocation contrast attributable
# ---------------------------------------------------------------------------

def test_m4_boundary_wells_are_a_prefix_of_m0_boundary_wells(fitted):
    """batch_lse is greedy, so q=4 returns the first four picks of q=8. The arms are
    therefore nested and the m0-vs-m4 difference is attributable to the four SUBSTITUTED
    wells rather than to a re-planned batch."""
    X0, _ = _plate2(fitted, 0)
    X4, d4 = _plate2(fitted, 4)
    boundary_of_m4 = X4[d4["m_placed"]:]
    assert torch.equal(boundary_of_m4, X0[:4])


def test_m8_spends_no_wells_on_the_boundary_at_all(fitted):
    X8, d8 = _plate2(fitted, 8)
    assert d8["n_boundary"] == 0
    assert d8["m_placed"] == 8


def test_local_wells_come_first_so_the_boundary_prefix_is_readable(fitted):
    """Ordering is registered so a row's `plate2_X` can be split by `m_placed` without
    ambiguity."""
    X4, d4 = _plate2(fitted, 4)
    ls = fitted["ls"]
    x_hat = torch.as_tensor(d4["x_hat"], dtype=torch.double)
    local = X4[:d4["m_placed"]]
    dist = ((local - x_hat) / ls).pow(2).sum(dim=1).sqrt()
    assert bool((dist <= 1.0 + 1e-12).all()), "the first m wells are not the local ones"


# ---------------------------------------------------------------------------
# The arms differ in ONE thing
# ---------------------------------------------------------------------------

def test_the_three_arms_share_plate_one_exactly(fitted):
    """Confounding check. Plate 1 is generated outside the composer, but the composer must
    not touch it -- if it did, the arms would differ in their global design too."""
    before = fitted["X1"].clone()
    for m in (0, 4, 8):
        _plate2(fitted, m)
    assert torch.equal(fitted["X1"], before)


def test_a_short_ball_falls_back_to_the_boundary_and_still_spends_the_full_budget(fitted):
    """§3.2 step 5. When the ARD ball cannot supply m wells the remainder goes to the
    boundary rule, the budget is still 8, and the row records that it happened -- rather
    than an m8 arm silently becoming an m2."""
    tiny = torch.full_like(fitted["ls"], 1e-4)
    X2, diag = spade_plate2(fitted["ad"], fitted["cand"], fitted["X1"], THETA,
                            N_PLATE2, 8, tiny, exclude=fitted["radius"])
    assert diag["m_local_short"] is True
    assert diag["m_placed"] < 8
    assert X2.shape[0] == N_PLATE2, "the fallback did not restore the full budget"
    assert diag["m_placed"] + diag["n_boundary"] == N_PLATE2
