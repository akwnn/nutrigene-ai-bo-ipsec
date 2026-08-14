"""EXPLORATORY branch only. Nothing here is registered.

Three modifications, each isolating one structural difference between the GP and
the second-order polynomial that beats it at d=6, sigma_rel=0.25.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.exploratory import QuadraticMean, ReplicatedEvaluator
from boec.surrogate import base_kernel, build_gp


def _data(d=6, n=14, seed=0):
    g = torch.Generator().manual_seed(seed)
    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])
    X = torch.rand(n, d, dtype=torch.double, generator=g)
    Y = torch.rand(n, 1, dtype=torch.double, generator=g)
    V = torch.full((n, 1), 0.04, dtype=torch.double)
    return X, Y, V, bounds


# --- 2.1 quadratic mean ----------------------------------------------------

def test_quadratic_mean_has_the_polynomial_s_parameter_count():
    """1 + d + d + d(d-1)/2 = 28 at d=6 — the same 28 the DoE arm fits."""
    m = QuadraticMean(d=6)
    n_param = sum(p.numel() for p in m.parameters())
    assert n_param == 1 + 6 + 6 + 15 == 28

    m8 = QuadraticMean(d=8)
    assert sum(p.numel() for p in m8.parameters()) == 1 + 8 + 8 + 28


def test_quadratic_mean_reproduces_a_known_quadratic_exactly():
    """It must be a full second-order surface, cross terms included."""
    torch.manual_seed(0)
    m = QuadraticMean(d=3)
    X = torch.rand(50, 3, dtype=torch.double)
    with torch.no_grad():
        m.bias.fill_(0.5)
        m.linear_weights.copy_(torch.tensor([1.0, -2.0, 0.5], dtype=torch.double))
        m.square_weights.copy_(torch.tensor([0.25, 0.0, -1.0], dtype=torch.double))
        m.cross_weights.copy_(torch.tensor([3.0, -0.5, 2.0], dtype=torch.double))

    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2]
    want = (0.5 + 1.0 * x0 - 2.0 * x1 + 0.5 * x2
            + 0.25 * x0**2 + 0.0 * x1**2 - 1.0 * x2**2
            + 3.0 * x0 * x1 - 0.5 * x0 * x2 + 2.0 * x1 * x2)
    assert torch.allclose(m(X), want, atol=1e-12)


def test_quadratic_mean_is_fitted_jointly_with_the_kernel():
    """Universal kriging: the trend is not fitted first and frozen."""
    X, Y, V, bounds = _data()
    model = build_gp(X, Y, V, bounds, mean_module=QuadraticMean(d=6))
    assert isinstance(model.mean_module, QuadraticMean)
    # every mean parameter must be reachable by the optimiser
    names = {n for n, _ in model.named_parameters()}
    for p in ("mean_module.bias", "mean_module.linear_weights",
              "mean_module.square_weights", "mean_module.cross_weights"):
        assert p in names
    # and it must actually have moved off its initialisation
    assert float(model.mean_module.linear_weights.abs().sum()) > 0.0


def test_quadratic_mean_does_not_disturb_the_kernel_configuration():
    X, Y, V, bounds = _data()
    a = build_gp(X, Y, V, bounds, fit=False)
    b = build_gp(X, Y, V, bounds, fit=False, mean_module=QuadraticMean(d=6))
    ka, kb = base_kernel(a), base_kernel(b)
    assert type(ka) is type(kb)
    assert ka.nu == kb.nu and ka.ard_num_dims == kb.ard_num_dims
    assert type(a.covar_module) is type(b.covar_module)


# --- 2.3 input warp --------------------------------------------------------

def test_warp_is_chained_after_normalize_and_stays_in_the_unit_cube():
    """Order matters: Warp assumes [0,1] input, so Normalize must run first."""
    from botorch.models.transforms.input import ChainedInputTransform

    X, Y, V, bounds = _data()
    model = build_gp(X, Y, V, bounds, fit=False, warp=True)
    tf = model.input_transform
    assert isinstance(tf, ChainedInputTransform)
    assert list(tf.keys()) == ["normalize", "warp"]

    Xt = tf(X)
    assert float(Xt.min()) >= 0.0 and float(Xt.max()) <= 1.0
    assert Xt.shape == X.shape


def test_warp_is_off_by_default_and_changes_nothing_when_off():
    from botorch.models.transforms.input import Normalize

    X, Y, V, bounds = _data()
    assert isinstance(build_gp(X, Y, V, bounds, fit=False).input_transform, Normalize)


def test_warp_parameters_are_fitted():
    X, Y, V, bounds = _data()
    model = build_gp(X, Y, V, bounds, warp=True)
    names = {n for n, _ in model.named_parameters()}
    assert any("warp" in n for n in names)


# --- 2.2 replication -------------------------------------------------------

class _Counting:
    """Returns the point's first coordinate plus deterministic 'noise'."""

    def __init__(self):
        self.calls = 0
        self.rows = 0

    def evaluate(self, X):
        self.calls += 1
        self.rows += X.shape[0]
        Y = X[:, :1].clone() + 0.1 * self.calls
        V = torch.full((X.shape[0], 1), 0.04, dtype=torch.double)
        return Y, V


def test_replication_spends_r_evaluations_per_distinct_condition():
    ev = _Counting()
    rep = ReplicatedEvaluator(ev, r=2)
    X = torch.rand(5, 6, dtype=torch.double)
    Y, V = rep.evaluate(X)

    assert Y.shape == (5, 1) and V.shape == (5, 1)
    assert ev.rows == 10               # 5 conditions x 2 replicates
    assert rep.n_evaluations == 10     # the budget that actually got spent


def test_replication_averages_the_observations_and_divides_the_variance():
    """Yvar = plug_in / r. Verified against the code, not assumed."""
    ev = _Counting()
    rep = ReplicatedEvaluator(ev, r=2)
    X = torch.rand(4, 6, dtype=torch.double)
    Y, V = rep.evaluate(X)

    # the two replicate calls return first_coord + 0.1 and + 0.2, so the mean is
    # first_coord + 0.15
    assert torch.allclose(Y, X[:, :1] + 0.15, atol=1e-12)
    assert torch.allclose(V, torch.full((4, 1), 0.02, dtype=torch.double), atol=1e-12)


def test_replication_at_r_equals_one_is_a_pass_through():
    ev = _Counting()
    rep = ReplicatedEvaluator(ev, r=1)
    X = torch.rand(3, 6, dtype=torch.double)
    Y, V = rep.evaluate(X)
    assert torch.allclose(Y, X[:, :1] + 0.1, atol=1e-12)
    assert torch.allclose(V, torch.full((3, 1), 0.04, dtype=torch.double), atol=1e-12)
    assert rep.n_evaluations == 3


def test_replication_on_the_real_oracle_reduces_the_error_it_should():
    """The point of replication: the averaged read is closer to the truth.

    Not a tautology -- averaging r draws of a noisy observation reduces its
    error by sqrt(r) in expectation, and this asserts the wiring delivers that
    rather than, say, silently discarding the extra replicate.
    """
    from boec.oracles import load_ensemble
    from boec.torch_oracle import BiphasicOracle

    inst = load_ensemble(dim=6)[0]
    X = torch.rand(200, 6, dtype=torch.double, generator=torch.Generator().manual_seed(1))
    truth = BiphasicOracle(inst, sigma_rel=0.25, seed=0).truth(X)

    e1 = float((BiphasicOracle(inst, sigma_rel=0.25, seed=0).evaluate(X)[0]
                - truth).pow(2).mean().sqrt())
    e2 = float((ReplicatedEvaluator(BiphasicOracle(inst, sigma_rel=0.25, seed=0), r=2)
                .evaluate(X)[0] - truth).pow(2).mean().sqrt())
    assert e2 < e1
    assert e2 == pytest.approx(e1 / np.sqrt(2), rel=0.25)


def test_replication_budget_arithmetic_lands_on_48():
    """r=2: 9 opening conditions then batches of 2, all in doubled evaluations."""
    from boec.campaign import batch_plan

    n_init, batches = batch_plan(6, 24, 2, n_init=9)
    assert n_init == 9
    assert n_init + sum(batches) == 24          # distinct conditions
    assert 2 * (n_init + sum(batches)) == 48    # evaluations, matching every other arm
