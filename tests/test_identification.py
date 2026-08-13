"""The identification floor, and the two properties that make it a floor.

The floor is an **oracle-search lower bound**: plant the true optimum in the visited
set, then score. A method that has already visited the best point in the space cannot
be beaten by one that has to find it, so whatever regret survives is pure
identification error and no arm at that budget and noise can go below it.

Two structural facts are asserted here rather than assumed, because the whole §1.1
pruning decision rests on them:

* **Rule A's floor grows with n.** Every extra competitor is another chance for a
  mediocre point to draw lucky noise and displace the planted optimum. This is the
  opposite of the intuition that more data helps, and it is why "reachable at n=48"
  does not imply "reachable at n=500".
* **The noise draw matches the oracle's.** A floor computed under a different noise
  model bounds nothing. Asserted against ``BiphasicOracle`` directly.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.identification import draw_observations, planted_design, rule_a_identification_error
from boec.optimizers import lhs_design

BOUNDS = torch.stack([torch.zeros(4, dtype=torch.double),
                      torch.ones(4, dtype=torch.double)])


# --------------------------------------------------------------- planted_design


def test_the_planted_design_has_the_requested_size():
    x = torch.full((4,), 0.3, dtype=torch.double)
    assert planted_design(BOUNDS, 12, x, seed=0).shape == (12, 4)


def test_the_optimum_is_present_exactly_and_not_merely_nearby():
    """A tolerance here would make the bound leaky: an approximately-planted optimum
    is a slightly worse point, so the 'floor' would sit above the true floor."""
    x = torch.tensor([0.31, 0.72, 0.05, 0.99], dtype=torch.double)
    D = planted_design(BOUNDS, 9, x, seed=3)
    assert any(torch.equal(row, x) for row in D)


def test_the_filler_is_the_ordinary_lhs_design_at_that_seed():
    """The floor must be computed against a realistic spread, not a special design."""
    x = torch.full((4,), 0.5, dtype=torch.double)
    D = planted_design(BOUNDS, 10, x, seed=7)
    assert torch.equal(D[:9], lhs_design(BOUNDS, 9, seed=7))


def test_a_design_with_no_room_for_a_competitor_is_refused():
    x = torch.full((4,), 0.5, dtype=torch.double)
    with pytest.raises(ValueError, match="at least 2"):
        planted_design(BOUNDS, 1, x, seed=0)


def test_an_optimum_outside_the_box_is_refused():
    """Silently accepting it would plant a point the arms could never visit, and the
    'floor' would then be below anything achievable rather than above it."""
    x = torch.tensor([0.5, 1.4, 0.5, 0.5], dtype=torch.double)
    with pytest.raises(ValueError, match="outside"):
        planted_design(BOUNDS, 8, x, seed=0)


# --------------------------------------------------------------- the noise draw


def test_the_noise_draw_reproduces_the_oracles_variance():
    """``y = f(1 + eps) + eta`` gives ``Var = f^2 sigma_rel^2 + sigma_add^2``."""
    t = np.array([1.0, 0.5, 0.2])
    Y = draw_observations(t, sigma_rel=0.25, sigma_add=0.01,
                          rng=np.random.default_rng(0), n_reps=400_000)
    want = t**2 * 0.25**2 + 0.01**2
    assert np.allclose(Y.var(axis=0), want, rtol=0.02)
    assert np.allclose(Y.mean(axis=0), t, atol=0.004)


def test_the_noise_draw_matches_biphasic_oracle_on_the_generated_ensemble():
    """An integration check: the floor is only a bound on *this* project's oracle."""
    from boec.oracles import load_ensemble
    from boec.torch_oracle import BiphasicOracle

    inst = load_ensemble(dim=6)[0]
    orac = BiphasicOracle(inst, sigma_rel=0.25, seed=0)
    X = lhs_design(torch.stack([torch.zeros(6, dtype=torch.double),
                                torch.ones(6, dtype=torch.double)]), 8, seed=0)
    t = orac.truth(X).numpy().ravel()

    emp = np.stack([orac.evaluate(X)[0].numpy().ravel() for _ in range(20_000)])
    mine = draw_observations(t, sigma_rel=0.25, sigma_add=0.01,
                             rng=np.random.default_rng(1), n_reps=20_000)
    assert np.allclose(emp.var(axis=0), mine.var(axis=0), rtol=0.06)


# --------------------------------------------------------------- rule_a_identification_error


def test_a_noiseless_assay_identifies_the_planted_optimum_every_time():
    t = np.array([1.0, 0.4, 0.8, 0.2])
    f = rule_a_identification_error(t, optimum_value=1.0, sigma_rel=0.0, sigma_add=0.0,
                     n_reps=200, seed=0)
    assert f.mean_regret == 0.0


def test_the_floor_is_never_negative_when_the_optimum_is_planted():
    t = np.array([1.0, 0.4, 0.8, 0.2])
    f = rule_a_identification_error(t, optimum_value=1.0, sigma_rel=0.25, sigma_add=0.01,
                     n_reps=2000, seed=0)
    assert f.mean_regret >= 0.0
    assert f.regrets.min() >= 0.0


def test_a_noisier_assay_has_a_higher_floor():
    t = np.concatenate([[1.0], np.linspace(0.2, 0.9, 40)])
    lo = rule_a_identification_error(t, optimum_value=1.0, sigma_rel=0.10, sigma_add=0.01,
                      n_reps=8000, seed=0).mean_regret
    hi = rule_a_identification_error(t, optimum_value=1.0, sigma_rel=0.25, sigma_add=0.01,
                      n_reps=8000, seed=0).mean_regret
    assert hi > lo


def test_more_competitors_raise_rule_as_floor_at_fixed_noise():
    """**The structural fact §1.1 turns on.** Rule A picks by observation, so every
    extra point is another draw that can beat the planted optimum by luck alone.
    A budget-to-target grid that assumes floors improve with n is reading the wrong
    direction off the curve."""
    rng = np.random.default_rng(0)
    comp = rng.uniform(0.2, 0.9, 400)
    small = rule_a_identification_error(np.concatenate([[1.0], comp[:40]]), optimum_value=1.0,
                         sigma_rel=0.25, sigma_add=0.01, n_reps=8000, seed=0)
    large = rule_a_identification_error(np.concatenate([[1.0], comp]), optimum_value=1.0,
                         sigma_rel=0.25, sigma_add=0.01, n_reps=8000, seed=0)
    assert large.mean_regret > small.mean_regret


def test_concentrating_the_competitors_lowers_rule_a_regret():
    """**Why the planted-optimum number is NOT a universal lower bound.**

    Rule A's cost on a mis-pick is the true value of whatever point won by luck. With
    spread-out competitors that point is usually bad; with competitors clustered near
    the optimum every candidate is nearly optimal, so mis-identifying costs almost
    nothing. Concentration is therefore *protective* under rule A, independently of
    finding a better point -- and an adaptive arm concentrates.

    This is the property that refuted the original framing: qLogEI at n=500 reports
    0.049 at d=6 sigma=0.25, where the space-filling planted design sits at 0.129.
    On the real oracle at n=384, holding the planted optimum and the noise fixed and
    varying only whether the competitors are spread or clustered, the gap is **8.5x**
    (0.1226 against 0.0144). The bar below is the directional claim, not that ratio --
    the size of the effect depends on how tight the cluster is.
    """
    optimum, spread_vals = 1.0, np.linspace(0.2, 0.95, 200)
    near_vals = np.linspace(0.93, 0.99, 200)
    kw = dict(optimum_value=optimum, sigma_rel=0.25, sigma_add=0.01,
              n_reps=4000, seed=0)
    spread = rule_a_identification_error(np.concatenate([[optimum], spread_vals]), **kw)
    concentrated = rule_a_identification_error(np.concatenate([[optimum], near_vals]), **kw)

    assert concentrated.mean_regret < spread.mean_regret / 2
    # and it is not because the clustered design identifies better -- it identifies
    # *worse*, because its competitors are harder to tell apart.
    assert concentrated.hit_rate <= spread.hit_rate


def test_the_floor_is_reproducible_from_its_seed():
    t = np.concatenate([[1.0], np.linspace(0.2, 0.9, 20)])
    kw = dict(optimum_value=1.0, sigma_rel=0.25, sigma_add=0.01, n_reps=500, seed=4)
    assert (rule_a_identification_error(t, **kw).mean_regret == rule_a_identification_error(t, **kw).mean_regret)


def test_the_scoring_agrees_with_a_brute_force_loop():
    """The vectorised argmax is the one that runs; this loop is the one that is
    obviously correct. Both are fed the *same* readouts, because the thing under test
    is the scoring, not the RNG consumption order -- a reference that redraws its own
    noise would fail on draw order while the scoring was perfectly correct."""
    t = np.array([1.0, 0.55, 0.83, 0.21, 0.77])
    got = rule_a_identification_error(t, optimum_value=1.0, sigma_rel=0.25, sigma_add=0.01,
                       n_reps=300, seed=11)

    Y = draw_observations(t, sigma_rel=0.25, sigma_add=0.01,
                          rng=np.random.default_rng(11), n_reps=300)
    want = [1.0 - t[int(np.argmax(row))] for row in Y]
    assert np.allclose(got.regrets, want)


def test_the_identification_rate_is_reported_alongside_the_regret():
    """'How often does the assay actually name the best point' is the number a lab
    can act on; a mean regret hides whether it is one catastrophe or steady drift."""
    t = np.array([1.0, 0.4, 0.8, 0.2])
    f = rule_a_identification_error(t, optimum_value=1.0, sigma_rel=0.0, sigma_add=0.0,
                     n_reps=100, seed=0)
    assert f.hit_rate == 1.0
    g = rule_a_identification_error(t, optimum_value=1.0, sigma_rel=0.5, sigma_add=0.01,
                     n_reps=4000, seed=0)
    assert 0.0 < g.hit_rate < 1.0
