"""`doe_unscreened` — the full-dimensional response-surface arm, no screening stage.

Spec §4 makes it mandatory wherever arithmetically feasible: a second-order model needs
``1 + d + d + C(d,2)`` coefficients, and at d=6 that is 28 against a 48-well budget with
room to spare. `boec.designs.central_composite(d=6, n_derived=1, n_centre=4)` already
gives 32 + 12 + 4 = **48 runs exactly** — built for Experiment 4, reused here rather than
re-derived, because a second design generator for the same arithmetic would be a second
source of truth for a number this project has already gotten wrong once (FINDINGS §4.5).

At d=8 the same generator cannot reach 48 with any centre points: the next resolution
down, `n_derived=3`, gives 32 factorial + 16 axial = 48 with **zero** left for the centre
replicates a CCD needs to estimate noise at all. `run_doe_unscreened_arm` raises rather
than running with `n_centre=0` — a design that cannot estimate its own noise is not the
same procedure as the d=6 arm, and silently running it anyway would be exactly the kind of
"do not invent it where it is not budget-feasible" case spec §4 forbids in the other
direction.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.doe import DoEResult, run_doe_unscreened_arm
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

D = 6
BUDGET = 48


class _CountingOracle:
    def __init__(self, seed: int = 0, dim: int = D):
        self._o = BiphasicOracle(load_ensemble(dim=dim)[0], sigma_rel=0.10, seed=seed)
        self.n_evaluated = 0

    def truth(self, X):
        return self._o.truth(X)

    def evaluate(self, X):
        self.n_evaluated += X.shape[0]
        return self._o.evaluate(X)


@pytest.fixture
def bounds():
    return torch.stack([torch.zeros(D, dtype=torch.double),
                        torch.ones(D, dtype=torch.double)])


@pytest.fixture(scope="module")
def result():
    o = _CountingOracle()
    bounds = torch.stack([torch.zeros(D, dtype=torch.double),
                          torch.ones(D, dtype=torch.double)])
    res = run_doe_unscreened_arm(o, bounds, truth=o.truth, budget=BUDGET, seed=0)
    return o, res


def test_spends_exactly_the_budget_no_screening_stage(result):
    o, res = result
    assert o.n_evaluated == BUDGET
    assert res.X_visited.shape == (BUDGET, D)


def test_no_factor_is_screened_out(result):
    """The whole point: `kept_factors` is every factor, `dropped_held_at` is empty --
    unlike `run_doe_arm`, which drops d - n_keep of them."""
    _, res = result
    assert res.kept_factors == tuple(range(D))
    assert res.dropped_held_at == {}


def test_returns_a_doe_result_with_a_working_regret_curve(result):
    o, res = result
    assert isinstance(res, DoEResult)
    assert res.curve_true.shape == (BUDGET,)
    assert float(res.curve_true[-1]) <= float(o._o.instance.optimum_value) + 1e-9


def test_the_confirmation_point_is_actually_measured(result):
    """Stage 4 is not optional here either -- the same reason `run_doe_arm` measures its
    predicted optimum rather than reporting the best design point on its own."""
    _, res = result
    assert res.confirmation_y == pytest.approx(
        float(res.Y_visited[-1]), rel=0, abs=1e-12)


def test_is_deterministic_given_a_seed(bounds):
    o1, o2 = _CountingOracle(seed=5), _CountingOracle(seed=5)
    r1 = run_doe_unscreened_arm(o1, bounds, truth=o1.truth, budget=BUDGET, seed=5)
    r2 = run_doe_unscreened_arm(o2, bounds, truth=o2.truth, budget=BUDGET, seed=5)
    np.testing.assert_allclose(r1.curve_true, r2.curve_true, atol=0, rtol=0)
    torch.testing.assert_close(r1.confirmation_x, r2.confirmation_x, rtol=0, atol=0)


def test_a_budget_that_does_not_match_the_generated_design_raises(bounds):
    """Mirrors `run_doe_arm`'s guard: spending a different count would make this arm
    incomparable to every other arm in the study, and nothing downstream would notice."""
    with pytest.raises(ValueError, match="48|budget"):
        run_doe_unscreened_arm(
            _CountingOracle(), bounds, truth=lambda X: X, budget=47, seed=0)


def test_d8_has_no_feasible_centre_point_budget_and_raises():
    """§4's own arithmetic: n_derived=3 at d=8 gives 32 + 16 = 48 with zero runs left for
    a centre replicate. A CCD cannot estimate noise from zero centre points, so this is
    not the same procedure as d=6 and must not run silently."""
    d = 8
    bounds8 = torch.stack([torch.zeros(d, dtype=torch.double),
                           torch.ones(d, dtype=torch.double)])
    o = _CountingOracle(dim=d)
    with pytest.raises(ValueError, match="centre|feasible|48"):
        run_doe_unscreened_arm(o, bounds8, truth=o.truth, budget=48, seed=0)
