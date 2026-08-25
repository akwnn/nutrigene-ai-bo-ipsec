"""Tests for proposal selection."""

from __future__ import annotations

import pytest
import torch

from boec.optimizers import (
    AcqConfig,
    initial_design,
    lhs_design,
    make_acquisition,
    oa_lhs_design,
    propose,
    random_design,
    sobol_design,
)
from boec.surrogate import build_gp

D = 3
UNIT = torch.stack([torch.zeros(D, dtype=torch.double), torch.ones(D, dtype=torch.double)])
SMALL = AcqConfig(num_restarts=2, raw_samples=32, mc_samples=32)


@pytest.fixture
def fitted():
    torch.manual_seed(0)
    X = torch.rand(14, D, dtype=torch.double)
    Y = (-((X - 0.35) ** 2).sum(-1, keepdim=True)).exp()
    Yvar = torch.full_like(Y, 0.001)
    return build_gp(X, Y, Yvar, UNIT, fit=True), X, Y


# --------------------------------------------------------------------------
# Designs and baselines
# --------------------------------------------------------------------------

def test_initial_design_is_2d_plus_2():
    """The budget convention depends on this exactly."""
    assert initial_design(UNIT, seed=0).shape == (2 * D + 2, D)
    six = torch.stack([torch.zeros(6, dtype=torch.double), torch.ones(6, dtype=torch.double)])
    assert initial_design(six).shape[0] == 14        # d=6: 14 + 8x4 + 2 = 48
    eight = torch.stack([torch.zeros(8, dtype=torch.double), torch.ones(8, dtype=torch.double)])
    assert initial_design(eight).shape[0] == 18      # d=8: 18 + 7x4 + 2 = 48


def test_initial_design_is_deterministic_for_a_seed():
    """RENAMED (T9/Q18). This was called
    ``test_initial_design_is_identical_across_methods_for_a_seed`` and cited as the
    enforcement of spec §E2's paired opening — but it calls ``initial_design``
    twice and never touches another method, so it tested determinism and nothing
    else. Meanwhile ``run_static_baseline`` never called ``initial_design`` at all,
    so the random and LHS arms shared no opening with qLogEI. A test whose NAME
    carries the guarantee and whose BODY does not is worse than no test: it is
    where everyone stops looking.

    The real cross-arm assertions now live in ``test_runner.py``
    (``test_paired_arms_open_on_the_identical_batch``). This keeps only the claim
    it can actually support."""
    a = initial_design(UNIT, seed=7)
    b = initial_design(UNIT, seed=7)
    assert torch.equal(a, b)
    assert not torch.equal(a, initial_design(UNIT, seed=8))


@pytest.mark.parametrize("fn", [sobol_design, random_design, lhs_design])
def test_baselines_respect_bounds_and_shape(fn):
    bounds = torch.tensor([[0.0, 2.0, -1.0], [1.0, 5.0, 1.0]], dtype=torch.double)
    pts = fn(bounds, 20, seed=0)
    assert pts.shape == (20, 3)
    assert bool(torch.all(pts >= bounds[0] - 1e-12))
    assert bool(torch.all(pts <= bounds[1] + 1e-12))


@pytest.mark.parametrize("fn", [sobol_design, random_design, lhs_design])
def test_baselines_are_deterministic(fn):
    assert torch.equal(fn(UNIT, 12, seed=3), fn(UNIT, 12, seed=3))


def test_lhs_uses_each_slice_once():
    """The defining property: every factor's range is evenly covered."""
    n = 20
    pts = lhs_design(UNIT, n, seed=0)
    for j in range(D):
        slots = (pts[:, j] * n).floor().long()
        assert len(set(slots.tolist())) == n


# --------------------------------------------------------------------------
# OA-LHS (docs/SPADE-CALIBRATION-FIX-SPEC.md sec 4, K2 -- design lottery)
# --------------------------------------------------------------------------

def test_oa_lhs_respects_bounds_and_shape_at_a_square_n():
    bounds = torch.tensor([[0.0, 2.0, -1.0], [1.0, 5.0, 1.0]], dtype=torch.double)
    pts = oa_lhs_design(bounds, 9, seed=0)          # p=3, n=p^2=9
    assert pts.shape == (9, 3)
    assert bool(torch.all(pts >= bounds[0] - 1e-12))
    assert bool(torch.all(pts <= bounds[1] + 1e-12))


def test_oa_lhs_is_deterministic():
    assert torch.equal(oa_lhs_design(UNIT, 9, seed=3), oa_lhs_design(UNIT, 9, seed=3))
    assert not torch.equal(oa_lhs_design(UNIT, 9, seed=3), oa_lhs_design(UNIT, 9, seed=4))


def test_oa_lhs_rejects_n_that_is_not_a_perfect_square():
    """SPADE-SPEC.md sec 'Stage 1': n = p^2 is the whole construction -- silently
    falling back to a non-orthogonal design would lose the Stein-theorem guarantee
    the OA claim rests on (docs/ODIN-VERDICT.md sec 4(a): 'do not fall back silently
    and keep the citation')."""
    with pytest.raises(ValueError, match="n = p\\^2"):
        oa_lhs_design(UNIT, 48, seed=0)             # 48 is not p^2 for any integer p


def test_oa_lhs_uses_each_1d_slice_once():
    """Strength-2 OA-LHS is strictly stronger than plain LHS, so it must still keep
    plain LHS's defining property: every factor's range evenly covered."""
    n = 49                                          # p=7
    pts = oa_lhs_design(UNIT, n, seed=0)
    for j in range(D):
        slots = (pts[:, j] * n).floor().long()
        assert len(set(slots.tolist())) == n


def test_oa_lhs_stratifies_every_2d_projection():
    """THE defining property plain LHS lacks: every pair of coordinates lands in
    every one of the p x p grid cells of that 2D projection exactly once, at
    n=p^2. This is what the Stein (1987) variance-reduction argument requires and
    what SPADE-SPEC.md sec 'Stage 1' cites it for."""
    p, n = 7, 49
    pts = oa_lhs_design(UNIT, n, seed=1)
    for j in range(D):
        for k in range(j + 1, D):
            cell_j = (pts[:, j] * p).floor().long()
            cell_k = (pts[:, k] * p).floor().long()
            cells = set(zip(cell_j.tolist(), cell_k.tolist()))
            assert len(cells) == n, f"2D projection ({j},{k}) is not fully stratified"


@pytest.mark.parametrize("fn", [sobol_design, random_design, lhs_design])
def test_baselines_reject_inverted_bounds(fn):
    bad = torch.tensor([[1.0, 1.0, 1.0], [0.0, 0.0, 0.0]], dtype=torch.double)
    with pytest.raises(ValueError, match="upper bound must exceed"):
        fn(bad, 5, seed=0)


# --------------------------------------------------------------------------
# Continuous proposals
# --------------------------------------------------------------------------

def test_proposes_the_right_shape_inside_the_box(fitted):
    model, X, Y = fitted
    out = propose(model, UNIT, 4, X, Y, config=SMALL)
    assert out.shape == (4, D)
    assert bool(torch.all(out >= 0.0)) and bool(torch.all(out <= 1.0))


def test_batch_proposals_are_not_near_duplicates(fitted):
    """Spec §9 'batch diversity'. Naive top-q returns q copies of one point."""
    model, X, Y = fitted
    out = propose(model, UNIT, 4, X, Y, config=SMALL)
    dists = torch.cdist(out, out)
    off = dists + torch.eye(4, dtype=torch.double) * 1e9
    assert float(off.min()) > 1e-4


def test_finds_the_peak_on_a_one_dimensional_toy():
    """Spec §9 'acquisition: qLogEI proposes near the true max on a 1-D toy'."""
    torch.manual_seed(0)
    b = torch.tensor([[0.0], [1.0]], dtype=torch.double)
    X = torch.linspace(0.05, 0.95, 12, dtype=torch.double).unsqueeze(-1)
    Y = (-((X - 0.7) ** 2) / 0.02).exp()
    m = build_gp(X, Y, torch.full_like(Y, 1e-6), b, fit=True)
    out = propose(m, b, 1, X, Y, config=SMALL)
    assert abs(float(out) - 0.7) < 0.15


def test_rejects_bad_q(fitted):
    model, X, Y = fitted
    with pytest.raises(ValueError, match="q must be"):
        propose(model, UNIT, 0, X, Y, config=SMALL)


# --------------------------------------------------------------------------
# Discrete proposals — what Phase 2 cannot work without
# --------------------------------------------------------------------------

def test_every_discrete_proposal_comes_from_the_menu(fitted):
    """Spec §9 'discrete mode: every proposal comes from the candidate set'."""
    model, X, Y = fitted
    torch.manual_seed(1)
    menu = torch.rand(40, D, dtype=torch.double)
    out = propose(model, UNIT, 4, X, Y, config=SMALL, candidates=menu)

    assert out.shape == (4, D)
    for row in out:
        assert bool(torch.any(torch.all(torch.isclose(menu, row), dim=1))), (
            "proposed a recipe that is not on the menu — Phase 2 replay would "
            "have nothing to look up"
        )


def test_discrete_proposals_are_distinct(fitted):
    model, X, Y = fitted
    torch.manual_seed(1)
    menu = torch.rand(40, D, dtype=torch.double)
    out = propose(model, UNIT, 4, X, Y, config=SMALL, candidates=menu)
    assert torch.unique(out, dim=0).shape[0] == 4


def test_discrete_picks_the_promising_end_of_the_menu(fitted):
    """Sanity: given a menu split between good and bad regions, it should
    prefer the good one."""
    model, X, Y = fitted
    good = torch.full((10, D), 0.35, dtype=torch.double) + torch.rand(10, D, dtype=torch.double) * 0.05
    bad = torch.full((10, D), 0.95, dtype=torch.double)
    menu = torch.cat([good, bad])
    out = propose(model, UNIT, 2, X, Y, config=SMALL, candidates=menu)
    assert float(out.mean()) < 0.7


def test_menu_smaller_than_q_raises(fitted):
    model, X, Y = fitted
    menu = torch.rand(2, D, dtype=torch.double)
    with pytest.raises(ValueError, match="menu has only"):
        propose(model, UNIT, 4, X, Y, config=SMALL, candidates=menu)


def test_menu_shape_enforced(fitted):
    model, X, Y = fitted
    with pytest.raises(ValueError, match=r"candidates must be \(k, d\)"):
        propose(model, UNIT, 1, X, Y, config=SMALL, candidates=torch.rand(5, dtype=torch.double))


# --------------------------------------------------------------------------
# X_pending — Phase 3's normal case
# --------------------------------------------------------------------------

def test_pending_points_push_proposals_elsewhere(fitted):
    """Without this, a second batch re-proposes the first batch's region."""
    model, X, Y = fitted
    first = propose(model, UNIT, 2, X, Y, config=SMALL)
    second = propose(model, UNIT, 2, X, Y, config=SMALL, X_pending=first)
    gap = torch.cdist(second, first).min()
    assert float(gap) > 1e-6


# --------------------------------------------------------------------------
# The acquisition choice that is flagged, not silently decided
# --------------------------------------------------------------------------

def test_both_acquisition_variants_work(fitted):
    model, X, Y = fitted
    for kind in ("qlogei", "qlognei"):
        cfg = AcqConfig(kind=kind, num_restarts=2, raw_samples=32, mc_samples=32)
        out = propose(model, UNIT, 2, X, Y, config=cfg)
        assert out.shape == (2, D)


def test_spec_default_is_unchanged():
    """We flag the noise concern; we do NOT silently deviate from the spec."""
    assert AcqConfig().kind == "qlogei"
    assert AcqConfig().best_f_policy == "max_observed"


def test_noisy_best_f_really_is_inflated(fitted):
    """The concern, demonstrated: the observed max exceeds the smoothed one."""
    model, X, Y = fitted
    from boec.optimizers import _best_f

    observed = float(_best_f(model, X, Y, "max_observed"))
    smoothed = float(_best_f(model, X, Y, "max_posterior_mean"))
    assert observed >= smoothed - 1e-9


def test_unknown_acquisition_rejected():
    with pytest.raises(ValueError, match="unknown acquisition"):
        AcqConfig(kind="qei")


def test_unknown_best_f_policy_rejected():
    with pytest.raises(ValueError, match="unknown best_f policy"):
        AcqConfig(best_f_policy="whatever")


# --------------------------------------------------------------------------
# Constraint hooks — unused in Phase 1, must not be dropped
# --------------------------------------------------------------------------

def test_inequality_constraint_is_honoured(fitted):
    """x0 + x1 >= 1.2, threaded through to the optimizer."""
    model, X, Y = fitted
    cfg = AcqConfig(
        num_restarts=2,
        raw_samples=32,
        mc_samples=32,
        inequality_constraints=[
            (torch.tensor([0, 1]), torch.tensor([1.0, 1.0], dtype=torch.double), 1.2)
        ],
    )
    out = propose(model, UNIT, 2, X, Y, config=cfg)
    assert bool(torch.all(out[:, 0] + out[:, 1] >= 1.2 - 1e-5))


def test_constraint_hooks_survive_into_discrete_mode(fitted):
    model, X, Y = fitted
    torch.manual_seed(2)
    menu = torch.rand(60, D, dtype=torch.double)
    cfg = AcqConfig(
        num_restarts=2,
        raw_samples=32,
        mc_samples=32,
        inequality_constraints=[
            (torch.tensor([0]), torch.tensor([1.0], dtype=torch.double), 0.5)
        ],
    )
    out = propose(model, UNIT, 2, X, Y, config=cfg, candidates=menu)
    assert bool(torch.all(out[:, 0] >= 0.5 - 1e-9))


def test_acquisition_accepts_pending(fitted):
    model, X, Y = fitted
    acqf = make_acquisition(model, X, Y, config=SMALL, X_pending=torch.rand(2, D, dtype=torch.double))
    assert acqf.X_pending is not None
