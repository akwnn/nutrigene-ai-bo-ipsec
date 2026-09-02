"""Coordinate descent — the baseline that pre-empts the obvious objection to E2.

Person A owns this. OPEN-QUESTIONS Q3.

**Why it exists.** The biphasic oracle is `f = sum_i w_i * ft_i(x_i)` plus a peak
modulation, i.e. a sum of terms each of which is unimodal in its own coordinate. That
structure is intrinsically easy for coordinate-wise search, and A measured the
coordinate-descent shortfall at 0-1% of depth even at double the chosen interaction
strength. A reviewer will say "your oracle is separable, so of course your method wins".

Reporting this arm answers that in advance instead of inviting it. If coordinate descent
does well, that is a stated limitation of the oracle, not a hidden one — and Hartmann6
is in E2 precisely because it is the arm that carries genuine multivariate difficulty.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.baselines import coordinate_descent
from boec.oracles import Hartmann6, load_ensemble
from boec.torch_oracle import BiphasicOracle, TorchEvaluator

D = 6
BUDGET = 48


class Counting:
    def __init__(self, inner):
        self.inner, self.n = inner, 0

    def evaluate(self, X):
        self.n += X.shape[0]
        return self.inner.evaluate(X)

    def truth(self, X):
        return self.inner.truth(X)


@pytest.fixture
def bounds():
    return torch.stack([torch.zeros(D, dtype=torch.double),
                        torch.ones(D, dtype=torch.double)])


def test_it_spends_exactly_the_budget(bounds):
    ev = Counting(TorchEvaluator(Hartmann6(), seed=0))
    coordinate_descent(ev, bounds, budget=BUDGET, seed=0)
    assert ev.n == BUDGET


def test_it_returns_a_best_so_far_curve_of_the_right_length(bounds):
    ev = TorchEvaluator(Hartmann6(), seed=0)
    res = coordinate_descent(ev, bounds, budget=BUDGET, seed=0)
    assert res.curve.shape == (BUDGET,)
    assert np.all(np.diff(res.curve) >= -1e-12)


def test_the_curve_is_scored_on_the_noiseless_value(bounds):
    """OPEN-QUESTIONS Q17. Scoring on the noisy observation lets an arm win by
    drawing lucky noise, and the bias scales with how many distinct points an arm
    visits — which differs by arm by design, so it does not cancel."""
    ev = TorchEvaluator(Hartmann6(), seed=0)
    res = coordinate_descent(ev, bounds, budget=BUDGET, seed=0)
    best_true = float(ev.truth(res.X).max())
    assert res.curve[-1] == pytest.approx(best_true, abs=1e-12)
    assert res.curve[-1] <= Hartmann6().optimum_value + 1e-9   # cannot beat the optimum


def test_it_is_deterministic_given_a_seed(bounds):
    a = coordinate_descent(TorchEvaluator(Hartmann6(), seed=1), bounds, budget=BUDGET, seed=5)
    b = coordinate_descent(TorchEvaluator(Hartmann6(), seed=1), bounds, budget=BUDGET, seed=5)
    np.testing.assert_allclose(a.curve, b.curve)
    torch.testing.assert_close(a.X, b.X)


def test_every_proposal_stays_inside_the_box(bounds):
    res = coordinate_descent(TorchEvaluator(Hartmann6(), seed=0), bounds,
                             budget=BUDGET, seed=0)
    assert bool(torch.all(res.X >= bounds[0] - 1e-12))
    assert bool(torch.all(res.X <= bounds[1] + 1e-12))


def test_it_sweeps_coordinates_rather_than_moving_all_at_once(bounds):
    """The defining property. Consecutive probes within a sweep must differ in
    exactly one coordinate, or this is not coordinate descent and the objection it
    is meant to pre-empt stays open."""
    res = coordinate_descent(TorchEvaluator(Hartmann6(), seed=0), bounds,
                             budget=BUDGET, seed=0)
    diffs = (res.X[1:] - res.X[:-1]).abs() > 1e-12
    changed = diffs.sum(dim=1).numpy()
    assert np.mean(changed <= 1) > 0.5, (
        f"only {np.mean(changed <= 1):.0%} of steps moved one coordinate")


def test_it_does_well_on_the_biphasic_oracle_and_that_is_the_point():
    """Not a performance test — a *disclosure* test. The oracle is a sum of
    coordinate-wise-unimodal terms, so coordinate search should get close to the
    optimum. Asserting it here means the limitation is recorded in the suite rather
    than discovered by a reviewer."""
    inst = load_ensemble(dim=D)[0]
    ev = BiphasicOracle(inst, sigma_rel=0.10, seed=0)
    b = torch.stack([torch.zeros(D, dtype=torch.double),
                     torch.ones(D, dtype=torch.double)])
    res = coordinate_descent(ev, b, budget=BUDGET, seed=0)
    assert res.curve[-1] > 0.80 * inst.optimum_value
