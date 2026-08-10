"""E1 — the correctness smoke test, and the evaluator that makes the swap real.

Person A owns this.

E1 is not a result. It is the check that the machinery works at all, run on functions
whose optima are known from the literature rather than planted by us. **If Bayesian
optimization loses to random search on Hartmann6, that is a bug and everything
downstream is void** — it is not a finding about Hartmann6.

`TorchEvaluator` is also the contract rehearsal the plan asked for (OPEN-QUESTIONS Q3):
the campaign loop was built against standard test functions, and the real oracle swaps
in later through the same interface. If that swap is not clean, the forward-compatibility
design was never real, and it is much better to discover that here than in Phase 2 when a
lookup table has to swap in for the same interface.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.campaign import Evaluator
from boec.oracles import Ackley, Branin, Hartmann6
from boec.torch_oracle import TorchEvaluator

FUNCS = (Branin(), Hartmann6(), Ackley(dim=6))


@pytest.fixture(params=FUNCS, ids=lambda f: f.name)
def ev(request):
    return TorchEvaluator(request.param, sigma_rel=0.10, sigma_add=0.01, seed=0)


# ------------------------------------------------------------------ the contract
def test_wraps_any_numpy_oracle_as_a_campaign_evaluator(ev):
    """The swap test. B's Campaign consumes anything with this shape."""
    assert isinstance(ev, Evaluator)


def test_evaluate_returns_n_by_one_pairs(ev):
    X = torch.rand(7, ev.dim, dtype=torch.double)
    Y, Yvar = ev.evaluate(X)
    assert Y.shape == (7, 1) and Yvar.shape == (7, 1)


def test_truth_is_noiseless_and_repeatable(ev):
    X = torch.rand(12, ev.dim, dtype=torch.double)
    assert torch.equal(ev.truth(X), ev.truth(X))


def test_evaluate_is_noisy(ev):
    X = torch.rand(24, ev.dim, dtype=torch.double)
    assert not torch.allclose(ev.evaluate(X)[0], ev.truth(X))


def test_yvar_is_floored_at_sigma_add_squared(ev):
    _, Yvar = ev.evaluate(torch.rand(64, ev.dim, dtype=torch.double))
    assert float(Yvar.min()) >= ev.yvar_floor - 1e-15
    assert ev.yvar_floor == pytest.approx(1e-4)


def test_it_is_reproducible_from_the_seed():
    X = torch.rand(8, 6, dtype=torch.double)
    a = TorchEvaluator(Hartmann6(), seed=3).evaluate(X)
    b = TorchEvaluator(Hartmann6(), seed=3).evaluate(X)
    torch.testing.assert_close(a[0], b[0])


# ------------------------------------------- the functions are set up to MAXIMISE
def test_every_function_is_oriented_so_the_known_optimum_is_the_maximum(ev):
    """B's campaign maximises. Branin and Hartmann6 are minimisation problems in the
    literature, so they must already be negated here -- if one were not, BO would
    diligently find its worst point and E1 would 'fail' for a reason that has nothing
    to do with the optimizer."""
    best = ev.oracle.optimum_value
    probe = torch.from_numpy(np.random.default_rng(0).uniform(0, 1, (20_000, ev.dim)))
    assert float(ev.truth(probe).max()) <= best + 1e-6


def test_truth_at_the_known_optimum_matches_the_published_value(ev):
    x = torch.from_numpy(np.asarray(ev.oracle.optimum_x, dtype=float)).reshape(1, -1)
    assert float(ev.truth(x)) == pytest.approx(ev.oracle.optimum_value, abs=1e-3)


# ------------------------------------------------------------------ the smoke test
@pytest.mark.slow
def test_bo_beats_random_on_hartmann6():
    """**The E1 kill condition.** Losing here is a bug, not a result.

    Kept deliberately small (4 seeds, budget 24) so it can live in the suite; the
    full 20-seed version is `scripts/run_e1.py`.
    """
    from boec.campaign import Campaign, CampaignConfig
    from boec.runner import run_static_baseline

    d = 6
    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])
    bo, rand = [], []
    for seed in range(4):
        e1 = TorchEvaluator(Hartmann6(), seed=seed)
        c = Campaign(e1, bounds, CampaignConfig(d=d, budget=24, q=4, seed=seed))
        c.run()
        bo.append(float(c.best_so_far()[-1]))
        e2 = TorchEvaluator(Hartmann6(), seed=seed)
        rand.append(float(run_static_baseline(e2, bounds, "random", 24, seed)[-1]))

    assert np.mean(bo) > np.mean(rand), (
        f"BO {np.mean(bo):.4f} did not beat random {np.mean(rand):.4f} on Hartmann6 "
        "-- this is a bug in the loop, not a finding"
    )


# ---------------------------------------------------------------------------
# T7 / spec §E1's FOURTH check — the only one that touches our own landscape
# ---------------------------------------------------------------------------
#
# The three functions above are borrowed. **They would pass identically if the Hill
# oracle were broken**, because they never touch it. Spec §E1 therefore requires a
# fourth check on a zero-interaction instance, where the optimum is known in closed
# form from the construction rather than from a table:
#
#     ft = h*g*((1+s)/s)^2  with  h = x^n/(EC50^n + x^n),  g = 1/(1+(x/IC50)^n)
#     => derivative numerator is  EC50^n * IC50^n - x^(2n),  so  x* = sqrt(EC50*IC50)
#
# The shipped v8 ensemble is `peak_modulation`, so the beta=0 case of the spec is
# gamma = 0 here: the modulation exp((f0 - 1/2) @ gamma^T / k) collapses to 1, the
# effective peaks fall back to xstar, and the response is a weighted sum of
# peak-normalised factors that each hit exactly 1.0 at their own optimum.
#
# TASKS.md T7. Never run before: run_e1.py executes only the three textbook
# functions.

def _zero_interaction_instance(dim: int = 6):
    """A shipped instance with the interaction switched off. Nothing else changed."""
    import copy

    from boec.oracles import load_ensemble

    inst = copy.deepcopy(load_ensemble(dim=dim)[0])
    inst.gamma = np.zeros((dim, dim))
    return inst


def test_the_zero_interaction_optimum_is_exactly_sqrt_ec50_times_ic50():
    """The construction identity, at machine precision. If this drifts, every
    'distance to the optimum' number in the project is measured against the wrong
    point and nothing else would reveal it."""
    inst = _zero_interaction_instance()
    np.testing.assert_allclose(
        np.sqrt(inst.ec50 * inst.ic50), inst.xstar, rtol=0, atol=1e-12
    )


def test_the_zero_interaction_response_peaks_at_exactly_one():
    """Peak-normalisation is what makes over-prediction interpretable against a
    ceiling of 1.0 — the entire E4 mechanism is stated relative to it."""
    from boec.oracles import HillOracle

    inst = _zero_interaction_instance()
    o = HillOracle(inst)
    assert float(np.asarray(o.f(inst.xstar.reshape(1, -1))).ravel()[0]) == pytest.approx(
        1.0, abs=1e-12
    )


def test_switching_the_interaction_off_actually_changed_something():
    """Guards the guard. If gamma were already ~0 on the shipped ensemble, the two
    tests above would pass without exercising the zero-interaction case at all —
    the 'test that cannot fail' pattern this project has now hit three times."""
    from boec.oracles import HillOracle, load_ensemble

    shipped = load_ensemble(dim=6)[0]
    X = np.full((1, 6), 0.3)
    assert not np.isclose(
        float(np.asarray(HillOracle(shipped).f(X)).ravel()[0]),
        float(np.asarray(HillOracle(_zero_interaction_instance()).f(X)).ravel()[0]),
        atol=1e-6,
    )


@pytest.mark.slow
def test_bo_converges_toward_sqrt_ec50_ic50_on_a_zero_interaction_instance():
    """**Spec §E1's fourth check, run at last.** BO on our own landscape family, with
    the optimum known in closed form.

    Scored on `truth()` at the recipe the method would report (Q17), never on the
    noisy observation. The bar is deliberately loose — 48 evaluations in six
    dimensions is not many and this is a smoke test, not a performance claim — but a
    gross failure here would mean the oracle, the evaluator or the loop is wrong in a
    way the three borrowed functions cannot see."""
    from boec.campaign import Campaign, CampaignConfig
    from boec.torch_oracle import BiphasicOracle

    inst = _zero_interaction_instance()
    o = BiphasicOracle(inst, sigma_rel=0.10, seed=0)
    b = torch.stack([torch.zeros(6, dtype=torch.double), torch.ones(6, dtype=torch.double)])

    c = Campaign(o, b, CampaignConfig(d=6, budget=48, q=4, seed=0)).run()
    X, Y = c.train_X, c.train_Y
    reported = X[int(torch.argmax(Y.ravel()))]
    true_at_reported = float(o.truth(reported.unsqueeze(0)))

    assert true_at_reported > 0.80, (
        f"BO reported a recipe worth {true_at_reported:.3f} against a known ceiling "
        f"of 1.0 on a zero-interaction instance — suspect the oracle or the loop"
    )
