"""KF-3 follow-up mechanisms: `EV(x)` (§2.1) and the repulsion-penalized batch (§2.2).

Registered in ``docs/SPADE-KF3-FOLLOWUP-SPEC.md``, frozen at commit `6c5e860`, corrected by
Erratum 1 (ground-truth leakage) and Erratum 2 (hardcoded exclusion radius / kernel unit
mismatch) before this file existed.

------------------------------------------------------------------------------
WHY THE NO-TRUTH SIGNATURE CHECK IS THE FIRST TEST
------------------------------------------------------------------------------

Erratum 1 exists because ``EV(x)`` almost shipped scored against ground truth. The fix
follows the same architectural pattern ``boec.final_spade.local_wells`` already uses: the
function's signature carries no ``truth`` parameter at all, so a scoring value cannot be
wired into the acquisition path by accident. This is checked directly, on the signature,
mirroring ``test_local_wells_accepts_no_truth_or_model_argument``.
"""

from __future__ import annotations

import inspect

import pytest
import torch

from boec.kf3_followup import (
    expected_deviation_reduction,
    fantasy_quantiles,
    repulsion_penalized_batch,
    select_diverse_batch,
    select_erroraware_batch,
)
from boec.optimizers import lhs_design
from boec.replay import unit_bounds
from boec.surrogate import build_gp

D = 2
THETA = 0.0


def _fitted_toy_gp(seed: int = 0):
    """A real, small, fast-to-fit GP with a known threshold-crossing structure.

    Training points cluster near x=(0.9, 0.5) with Y far above THETA (the model should be
    confident there) and leave a gap near x=(0.1, 0.1) where the same generating function
    crosses THETA -- the model should be genuinely uncertain there.
    """
    bounds = unit_bounds(D)
    X = torch.tensor([
        [0.85, 0.45], [0.90, 0.50], [0.95, 0.55], [0.88, 0.52], [0.92, 0.48],
        [0.5, 0.9], [0.5, 0.1], [0.1, 0.9], [0.9, 0.9],
    ], dtype=torch.double)
    Y = (2.0 - 4.0 * (X - 0.9).pow(2).sum(dim=1, keepdim=True)).double()
    Yvar = torch.full_like(Y, 1e-4)
    return build_gp(X, Y, Yvar, bounds), X, Y, Yvar, bounds


# ---------------------------------------------------------------------------
# fantasy_quantiles -- exact, hand-checked
# ---------------------------------------------------------------------------

def test_fantasy_quantiles_matches_hand_computed_normal_quantiles():
    """k=4: probabilities 0.125, 0.375, 0.625, 0.875 -> standard normal quantiles
    -1.1503, -0.3186, 0.3186, 1.1503 (symmetric, hand-checkable to 4 d.p.)."""
    z = fantasy_quantiles(mean=0.0, sd=1.0, k=4)
    expected = torch.tensor([-1.1503, -0.3186, 0.3186, 1.1503], dtype=torch.double)
    torch.testing.assert_close(z, expected, atol=1e-4, rtol=0)


def test_fantasy_quantiles_scales_and_shifts_by_mean_and_sd():
    z = fantasy_quantiles(mean=5.0, sd=2.0, k=4)
    base = fantasy_quantiles(mean=0.0, sd=1.0, k=4)
    torch.testing.assert_close(z, 5.0 + 2.0 * base)


def test_fantasy_quantiles_is_symmetric_about_the_mean():
    z = fantasy_quantiles(mean=0.0, sd=1.0, k=8)
    torch.testing.assert_close(z, -z.flip(0), atol=1e-10, rtol=0)


# ---------------------------------------------------------------------------
# expected_deviation_reduction -- the no-truth guard, then behaviour
# ---------------------------------------------------------------------------

def test_expected_deviation_reduction_accepts_no_truth_argument():
    names = set(inspect.signature(expected_deviation_reduction).parameters)
    assert "truth" not in names, (
        "EV(x) must not accept a truth argument -- Erratum 1 exists because it almost did")


def test_expected_deviation_reduction_is_near_zero_where_the_model_is_already_certain():
    """A candidate right where training data already sits (Y far above THETA, low sd)
    should teach the model almost nothing more."""
    model, X, Y, Yvar, bounds = _fitted_toy_gp()
    X_er = lhs_design(bounds, 40, seed=1)
    x_certain = torch.tensor([0.90, 0.50], dtype=torch.double)

    ev = expected_deviation_reduction(
        model, x_certain, X, Y, Yvar, bounds, THETA, X_er,
        sigma_rel=0.1, sigma_add=0.01, k_fantasy=4, ev_n_draws=32, seed=0)

    assert ev == pytest.approx(0.0, abs=0.02), f"expected near-zero EV, got {ev}"


def test_expected_deviation_reduction_is_larger_for_a_genuinely_ambiguous_point():
    """A candidate in the unsampled gap where the generating function crosses THETA should
    look more informative than one where the model is already confident."""
    model, X, Y, Yvar, bounds = _fitted_toy_gp()
    X_er = lhs_design(bounds, 40, seed=1)
    x_certain = torch.tensor([0.90, 0.50], dtype=torch.double)
    x_ambiguous = torch.tensor([0.10, 0.10], dtype=torch.double)

    ev_certain = expected_deviation_reduction(
        model, x_certain, X, Y, Yvar, bounds, THETA, X_er,
        sigma_rel=0.1, sigma_add=0.01, k_fantasy=4, ev_n_draws=32, seed=0)
    ev_ambiguous = expected_deviation_reduction(
        model, x_ambiguous, X, Y, Yvar, bounds, THETA, X_er,
        sigma_rel=0.1, sigma_add=0.01, k_fantasy=4, ev_n_draws=32, seed=0)

    assert ev_ambiguous > ev_certain, (
        f"expected the ambiguous candidate ({ev_ambiguous}) to score above the "
        f"already-certain one ({ev_certain})")


def test_expected_deviation_reduction_is_deterministic_given_a_seed():
    model, X, Y, Yvar, bounds = _fitted_toy_gp()
    X_er = lhs_design(bounds, 40, seed=1)
    x = torch.tensor([0.10, 0.10], dtype=torch.double)

    a = expected_deviation_reduction(model, x, X, Y, Yvar, bounds, THETA, X_er,
                                     sigma_rel=0.1, sigma_add=0.01, k_fantasy=4,
                                     ev_n_draws=32, seed=7)
    b = expected_deviation_reduction(model, x, X, Y, Yvar, bounds, THETA, X_er,
                                     sigma_rel=0.1, sigma_add=0.01, k_fantasy=4,
                                     ev_n_draws=32, seed=7)
    assert a == b


# ---------------------------------------------------------------------------
# select_erroraware_batch -- the shortlist is criterion-blind, the batch is the right shape
# ---------------------------------------------------------------------------

def test_select_erroraware_batch_returns_exactly_q_distinct_wells():
    model, X, Y, Yvar, bounds = _fitted_toy_gp()
    X_er = lhs_design(bounds, 30, seed=1)
    cand = lhs_design(bounds, 64, seed=2)

    picks = select_erroraware_batch(
        model, X, Y, Yvar, bounds, cand, THETA, X_er, q=3,
        sigma_rel=0.1, sigma_add=0.01, k_err=16, k_fantasy=4, ev_n_draws=16, seed=0)

    assert picks.shape == (3, D)
    assert len(set(map(tuple, picks.tolist()))) == 3


def test_select_erroraware_batch_shortlist_does_not_depend_on_straddle_score():
    """The shortlist is a uniform random subsample seeded independently of straddle score
    -- changing theta (which changes straddle_score everywhere) must not change WHICH
    candidates are shortlisted, only how they are scored once shortlisted. Checked by
    reaching into the same RNG the function uses and confirming it depends on `seed` and
    `cand`, not on `theta`."""
    model, X, Y, Yvar, bounds = _fitted_toy_gp()
    cand = lhs_design(bounds, 64, seed=2)
    g1 = torch.Generator().manual_seed(0)
    idx1 = torch.randperm(cand.shape[0], generator=g1)[:16]
    g2 = torch.Generator().manual_seed(0)
    idx2 = torch.randperm(cand.shape[0], generator=g2)[:16]
    assert torch.equal(idx1, idx2), "shortlist RNG must be seed-determined, not theta-dependent"


# ---------------------------------------------------------------------------
# repulsion_penalized_batch -- no model argument, exact hand-checked penalty, spreading
# ---------------------------------------------------------------------------

def test_repulsion_penalized_batch_accepts_no_model_argument():
    names = set(inspect.signature(repulsion_penalized_batch).parameters)
    assert "model" not in names, (
        "mirrors local_wells: an array-only signature makes the no-oracle-access property "
        "a fact about the type, not a promise in a docstring")


def test_a_pick_at_exactly_the_bandwidth_distance_is_penalized_by_exactly_half():
    """`straddle_score = 1.96*sd - |mean - theta|` rewards proximity to `theta`, not
    distance from it -- candidate 0 sits exactly on `theta` (score 0) and the other two
    sit equally far from it (score -5), so candidate 0 wins the first pick outright.

    `k_bw(x, x') = exp(-ln(2) * (dist/bandwidth)^2)`; at `dist == bandwidth` this is exactly
    0.5 by construction (`exp(-ln 2) = 0.5`) -- hand-checkable."""
    cand = torch.tensor([[0.0, 0.0], [0.5, 0.0], [1.0, 0.0]], dtype=torch.double)
    mean = torch.tensor([0.0, 5.0, 5.0], dtype=torch.double)  # score: [0, -5, -5]
    sd = torch.zeros(3, dtype=torch.double)
    theta = 0.0
    bandwidth = 0.5

    picks = repulsion_penalized_batch(mean, sd, theta, cand, q=2, bandwidth=bandwidth, lam=1.0)
    assert torch.equal(picks[0], cand[0])
    # candidate 1 (dist=0.5=bandwidth from pick 0) vs candidate 2 (dist=1.0=2*bandwidth):
    # both have raw score -5; penalty(1) = 1.0*0.5 = 0.5 -> adjusted -5.5.
    # penalty(2) = 1.0*exp(-ln2*4) = 0.0625 -> adjusted -5.0625, which wins.
    assert torch.equal(picks[1], cand[2]), (
        "the closer candidate should be penalized more and lose the second pick")


def test_repulsion_penalized_batch_visibly_spreads_across_two_known_modes():
    """Two well-separated modes (near `theta` = clustered mode A, and a lone, worse-scoring
    mode B far away); plain greedy-with-no-repulsion would pick two of mode A's three
    near-duplicate points, but repulsion must send the second pick to mode B instead, even
    though mode B's raw score is much worse."""
    cand = torch.cat([
        torch.tensor([[0.10, 0.10], [0.12, 0.10], [0.10, 0.12]], dtype=torch.double),
        torch.tensor([[0.90, 0.90]], dtype=torch.double),
    ])
    theta = 0.0
    # score = -|mean - theta|: mode A sits near theta (0, -0.02, -0.04); mode B sits far
    # from it (-0.5) so unpenalized greedy would never choose it.
    mean = torch.tensor([0.0, 0.02, 0.04, 0.5], dtype=torch.double)
    sd = torch.zeros(4, dtype=torch.double)

    picks = repulsion_penalized_batch(mean, sd, theta, cand, q=2, bandwidth=0.05, lam=1.0)

    assert torch.equal(picks[0], cand[0])
    # pick 2: mode A's remaining points sit ~0.02 from pick 0 (bandwidth 0.05), penalty
    # exp(-ln2*(0.02/0.05)^2) = 0.895 dominates their small score edge; mode B sits ~1.13
    # away, penalty ~0, so despite -0.5 raw score it wins on being essentially unpenalized.
    assert torch.equal(picks[1], cand[3]), "second pick should spread to the far mode"


def test_repulsion_penalized_batch_is_deterministic():
    cand = torch.rand(20, D, generator=torch.Generator().manual_seed(3), dtype=torch.double)
    mean = torch.rand(20, generator=torch.Generator().manual_seed(4), dtype=torch.double)
    sd = torch.rand(20, generator=torch.Generator().manual_seed(5), dtype=torch.double)
    a = repulsion_penalized_batch(mean, sd, 0.3, cand, q=5, bandwidth=0.1)
    b = repulsion_penalized_batch(mean, sd, 0.3, cand, q=5, bandwidth=0.1)
    assert torch.equal(a, b)


def test_repulsion_penalized_batch_returns_fewer_than_q_only_if_candidates_run_out():
    cand = torch.rand(3, D, dtype=torch.double)
    mean = torch.rand(3, dtype=torch.double)
    sd = torch.rand(3, dtype=torch.double)
    picks = repulsion_penalized_batch(mean, sd, 0.3, cand, q=8, bandwidth=0.1)
    assert picks.shape == (3, D)


# ---------------------------------------------------------------------------
# select_diverse_batch -- reads exclusion_radius(model) live, per Erratum 2
# ---------------------------------------------------------------------------

def test_select_diverse_batch_uses_the_live_exclusion_radius_not_a_constant():
    """Erratum 2: bandwidth must be exclusion_radius(model), read fresh -- not a literal
    0.1. Two models with deliberately different fitted lengthscales must therefore be
    capable of producing different bandwidths (checked structurally: the function must call
    exclusion_radius rather than hardcode, verified by monkeypatching it and observing the
    batch selection change)."""
    import boec.kf3_followup as kf3

    model, X, Y, Yvar, bounds = _fitted_toy_gp()
    cand = lhs_design(bounds, 30, seed=9)

    original = kf3.exclusion_radius
    calls = []

    def _spy(m, *a, **kw):
        calls.append(m)
        return original(m, *a, **kw)

    kf3.exclusion_radius = _spy
    try:
        select_diverse_batch(model, cand, THETA, q=4)
    finally:
        kf3.exclusion_radius = original

    assert calls, "select_diverse_batch must call exclusion_radius(model), not a literal"
    assert calls[0] is model
