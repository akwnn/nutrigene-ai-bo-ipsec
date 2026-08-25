"""The bridge between A's numpy oracle and B's torch interfaces.

Person A owns this. Every test here asserts a contract B's code depends on, so a
refactor that breaks one should fail here rather than silently produce believable
numbers three modules downstream.

The traps these exist to catch are all silent ones: Yvar as a standard deviation
rather than a variance, Yvar computed from the noiseless value rather than the
observed one, and `truth` returning something noisy.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.campaign import Evaluator
from boec.designs import sub_box_bounds
from boec.e4 import Oracle
from boec.oracles import ENSEMBLE_VERSION, HillOracle, load_ensemble, load_instance
from boec.seedbook import IndexedGaussianNoise
from boec.torch_oracle import BiphasicOracle, TorchEvaluator

KAPPAS = (0.6, 0.7, 0.8, 0.9)


@pytest.fixture(scope="module")
def d6():
    return load_ensemble(dim=6)


@pytest.fixture(scope="module")
def oracle(d6):
    return BiphasicOracle(d6[0])


# ------------------------------------------------------------------ the contract
def test_adapter_satisfies_b_s_structural_oracle_protocol(oracle):
    """B's `run_e4_cell` consumes anything with these three members."""
    assert isinstance(oracle, Oracle)


def test_adapter_satisfies_the_campaign_evaluator_protocol(oracle):
    """The two-method version the BO loop uses."""
    assert isinstance(oracle, Evaluator)


def test_x_star_is_the_unmodulated_peak_with_shape_d(oracle, d6):
    xs = oracle.x_star
    assert isinstance(xs, torch.Tensor)
    assert xs.shape == (6,)
    np.testing.assert_allclose(xs.numpy(), d6[0].xstar)


def test_truth_returns_n_by_one(oracle):
    assert oracle.truth(torch.rand(7, 6, dtype=torch.double)).shape == (7, 1)


def test_evaluate_returns_n_by_m_pairs(oracle):
    Y, Yvar = oracle.evaluate(torch.rand(5, 6, dtype=torch.double))
    assert Y.shape == (5, 1) and Yvar.shape == (5, 1)


# ------------------------------------------------------------------- noiselessness
def test_truth_is_noiseless(oracle):
    """If `truth` were noisy, E4's whole over-prediction distribution widens for a
    reason that has nothing to do with extrapolation."""
    X = torch.rand(20, 6, dtype=torch.double)
    a, b = oracle.truth(X), oracle.truth(X)
    assert torch.equal(a, b)


def test_truth_at_the_cached_optimum_is_exactly_one(d6):
    """Peak normalisation plus the fixed-point optimum: f(x_opt) == 1."""
    for inst in d6[:5]:
        o = BiphasicOracle(inst)
        x = torch.from_numpy(np.asarray(inst.optimum_x, dtype=float)).reshape(1, -1)
        assert float(o.truth(x)) == pytest.approx(1.0, abs=1e-9)


def test_observe_is_actually_noisy(oracle):
    X = torch.rand(30, 6, dtype=torch.double)
    assert not torch.allclose(oracle.observe(X)[0], oracle.truth(X))


# -------------------------------------------------------------------------- Yvar
def test_yvar_is_a_variance_not_a_standard_deviation(d6):
    """The classic fixed-noise GP bug, checked against the analytic truth.

    The empirical spread of repeated observations at one point must match the
    *variance* `f^2*sigma_rel^2 + sigma_add^2`, and be nowhere near its square root.
    """
    sr, sa = 0.25, 0.01
    o = BiphasicOracle(d6[0], sigma_rel=sr, sigma_add=sa, seed=1)
    X = torch.full((1, 6), 0.3, dtype=torch.double)
    f = float(o.truth(X))

    draws = np.array([float(o.observe(X)[0]) for _ in range(20_000)])
    analytic = f**2 * sr**2 + sa**2
    assert draws.var(ddof=1) == pytest.approx(analytic, rel=0.05)
    assert draws.var(ddof=1) != pytest.approx(np.sqrt(analytic), rel=0.5)


def test_the_plug_in_over_estimates_by_exactly_the_documented_amount(d6):
    """`E[y^2] = f^2*(1 + sigma_rel^2) + sigma_add^2`, so the plug-in runs ~6% high at
    sigma_rel = 0.25 and ~1% at 0.10.

    Asserted rather than described, because the docstring says calibration is expected
    to show mild over-coverage at the higher noise level and that this is the first
    candidate. That is only a usable diagnostic if the size of the bias is pinned.
    """
    X = torch.full((1, 6), 0.3, dtype=torch.double)
    for sr, expected_excess in ((0.10, 0.010), (0.25, 0.062)):
        o = BiphasicOracle(d6[0], sigma_rel=sr, sigma_add=0.01, seed=2)
        f = float(o.truth(X))
        analytic = f**2 * sr**2 + 0.01**2
        mean_plug_in = np.mean([float(o.observe(X)[1]) for _ in range(20_000)])
        assert mean_plug_in / analytic - 1.0 == pytest.approx(expected_excess, abs=0.01)


def test_yvar_is_the_plug_in_computed_from_the_observed_value(d6):
    """Not the analytic variance. The analytic form is a function of the noiseless
    f(x), from which |f(x)| is exactly recoverable — handing the model the truth at
    every training point and corrupting E3."""
    o = BiphasicOracle(d6[0], sigma_rel=0.10, sigma_add=0.01, seed=3)
    X = torch.rand(50, 6, dtype=torch.double)
    Y, Yvar = o.observe(X)
    expected = Y**2 * 0.10**2 + 0.01**2
    torch.testing.assert_close(Yvar, expected.clamp_min(0.01**2))


def test_analytic_ablation_differs_from_the_plug_in_and_leaks_the_truth(d6):
    """Kept behind a flag as an upper bound on calibration under perfect noise
    knowledge — and demonstrably a leak, which is why it is not the default."""
    X = torch.rand(40, 6, dtype=torch.double)
    plug = BiphasicOracle(d6[0], seed=5, yvar_mode="plugin")
    ana = BiphasicOracle(d6[0], seed=5, yvar_mode="analytic")
    assert not torch.allclose(plug.observe(X)[1], ana.observe(X)[1])
    recovered = ((ana.observe(X)[1] - 0.01**2) / 0.10**2).sqrt()
    torch.testing.assert_close(recovered, ana.truth(X).abs())


def test_yvar_is_floored_at_sigma_add_squared(d6):
    """OPEN-QUESTIONS Q8. The floor is the assay's additive noise variance, not a
    numerical epsilon — non-binding in Phase 1 by construction, and the guard that
    stops a Phase 2 lookup table or a Phase 3 human returning a zero variance."""
    o = BiphasicOracle(d6[0], sigma_rel=0.10, sigma_add=0.01)
    assert o.yvar_floor == pytest.approx(1e-4)
    _, Yvar = o.observe(torch.rand(200, 6, dtype=torch.double))
    assert float(Yvar.min()) >= 1e-4


def test_observe_is_reproducible_from_the_seed(d6):
    X = torch.rand(10, 6, dtype=torch.double)
    a = BiphasicOracle(d6[0], seed=11).observe(X)
    b = BiphasicOracle(d6[0], seed=11).observe(X)
    torch.testing.assert_close(a[0], b[0])
    torch.testing.assert_close(a[1], b[1])


@pytest.mark.parametrize("adapter", ("biphasic", "torch"))
def test_indexed_evaluator_noise_does_not_depend_on_batch_chunking(d6, adapter):
    def build():
        source = IndexedGaussianNoise(17, sigma_rel=0.1, sigma_add=0.01)
        if adapter == "biphasic":
            return BiphasicOracle(d6[0], noise_source=source)
        return TorchEvaluator(HillOracle(d6[0]), noise_source=source)

    X = torch.rand(5, 6, dtype=torch.double)
    together = build().evaluate(X)
    split_evaluator = build()
    first = split_evaluator.evaluate(X[:2])
    second = split_evaluator.evaluate(X[2:])
    split = tuple(
        torch.cat([first[i], second[i]])
        for i in range(2)
    )
    assert all(torch.equal(a, b) for a, b in zip(together, split))


@pytest.mark.parametrize("adapter", ("biphasic", "torch"))
def test_indexed_evaluator_state_restores_the_next_observation(d6, adapter):
    def build(root_seed=23, sigma_rel=0.1, sigma_add=0.01, indexed=True, instance=0):
        source = (
            IndexedGaussianNoise(root_seed, sigma_rel=sigma_rel, sigma_add=sigma_add)
            if indexed
            else None
        )
        if adapter == "biphasic":
            return BiphasicOracle(
                d6[instance],
                sigma_rel=sigma_rel,
                sigma_add=sigma_add,
                seed=root_seed,
                noise_source=source,
            )
        return TorchEvaluator(
            HillOracle(d6[instance]),
            sigma_rel=sigma_rel,
            sigma_add=sigma_add,
            seed=root_seed,
            noise_source=source,
        )

    X = torch.rand(5, 6, dtype=torch.double)
    original = build()
    original.evaluate(X[:2])
    state = original.state_dict()
    assert state["noise_mode"] == "indexed"
    assert state["seed"] == 23
    assert state["sigma_rel"] == 0.1
    assert state["sigma_add"] == 0.01
    assert state["oracle_identity"]
    assert state["next_index"] == 2

    resumed = build()
    resumed.load_state_dict(state)
    expected = original.evaluate(X[2:])
    actual = resumed.evaluate(X[2:])

    assert resumed.state_dict()["next_index"] == 5
    assert all(torch.equal(a, b) for a, b in zip(expected, actual))


@pytest.mark.parametrize("adapter", ("biphasic", "torch"))
@pytest.mark.parametrize(
    ("mismatch", "message"),
    (
        ("noise_mode", "noise_mode"),
        ("seed", "seed"),
        ("sigma_rel", "sigma_rel"),
        ("sigma_add", "sigma_add"),
        ("oracle_identity", "oracle_identity"),
    ),
)
def test_indexed_evaluator_rejects_checkpoint_identity_mismatch(
    d6, adapter, mismatch, message
):
    def build(*, root_seed=23, sigma_rel=0.1, sigma_add=0.01, indexed=True, instance=0):
        source = (
            IndexedGaussianNoise(root_seed, sigma_rel=sigma_rel, sigma_add=sigma_add)
            if indexed
            else None
        )
        if adapter == "biphasic":
            return BiphasicOracle(
                d6[instance],
                sigma_rel=sigma_rel,
                sigma_add=sigma_add,
                seed=root_seed,
                noise_source=source,
            )
        return TorchEvaluator(
            HillOracle(d6[instance]),
            sigma_rel=sigma_rel,
            sigma_add=sigma_add,
            seed=root_seed,
            noise_source=source,
        )

    state = build().state_dict()
    changed = {
        "noise_mode": {"indexed": False},
        "seed": {"root_seed": 24},
        "sigma_rel": {"sigma_rel": 0.2},
        "sigma_add": {"sigma_add": 0.02},
        "oracle_identity": {"instance": 1},
    }[mismatch]

    with pytest.raises(ValueError, match=message):
        build(**changed).load_state_dict(state)


@pytest.mark.parametrize("adapter", ("biphasic", "torch"))
def test_legacy_evaluator_state_restores_the_next_observation(d6, adapter):
    def build():
        if adapter == "biphasic":
            return BiphasicOracle(d6[0], sigma_rel=0.1, sigma_add=0.01, seed=29)
        return TorchEvaluator(
            HillOracle(d6[0]), sigma_rel=0.1, sigma_add=0.01, seed=29
        )

    X = torch.rand(5, 6, dtype=torch.double)
    original = build()
    original.evaluate(X[:2])
    state = original.state_dict()

    assert state["noise_mode"] == "legacy"
    assert state["next_index"] == 2
    assert "rng_state" in state

    expected = original.evaluate(X[2:])
    resumed = build()
    resumed.load_state_dict(state)
    actual = resumed.evaluate(X[2:])

    assert resumed.state_dict()["next_index"] == 5
    assert all(torch.equal(a, b) for a, b in zip(expected, actual))


# ------------------------------------------------------- the containment invariant
@pytest.mark.parametrize("dim", (6, 8))
def test_the_effective_peak_never_falls_inside_the_training_box(dim):
    """**E4's premise, locked as a regression test.**

    Under peak modulation the effective peak is `x*_i * m_i(x)`, so the joint optimum
    sits at the fixed point and B's `sub_box_bounds` no longer *automatically* stops
    short of it. `x_opt[i] <= kappa*x*[i]` iff `m_i(x_opt) <= kappa`, so this checks
    the whole ensemble in closed form. If it ever fails, E4 measures nothing on the
    affected cells and the fix is lower kappa or tighter gamma — **never a raised
    x_star**, which would flatten the landscape and break E2.
    """
    for inst in load_ensemble(dim=dim):
        x_opt = np.asarray(inst.optimum_x, dtype=float)
        for kappa in KAPPAS:
            upper = sub_box_bounds(
                torch.from_numpy(inst.xstar), kappa
            )[1].numpy()
            assert (x_opt > upper).any(), (
                f"{inst.instance_id} kappa={kappa}: the whole optimum lies inside the "
                "training box, so there is nothing to extrapolate to"
            )


# ----------------------------------------------------------------- the committed data
def test_the_shipped_config_reproduces_the_committed_version_hash():
    """**The footgun this closes.** A bare `SamplerConfig()` defaults to
    `accept_floor = 0.045` — the v6 spec value — while the committed ensemble was
    generated at 0.1083. Reconstructing the config by hand therefore yields a
    *different* `oracle_version`, and any instance regenerated from it carries a
    different `instance_id` while describing an identical landscape.

    A hit this while checking whether the ensemble could be extended, and it had
    already corrupted one reported number: PF2.3's "v8 shipped" acceptance rate was
    measured at 0.045 rather than the shipped floor.

    `SHIPPED_CONFIG` is the single object that generated what is on disk. Asserting
    its hash against the committed ensemble means the two can never silently part.
    """
    from boec.oracles import SHIPPED_CONFIG

    assert SHIPPED_CONFIG.version() == ENSEMBLE_VERSION
    for dim in (6, 8):
        assert all(i.oracle_version == SHIPPED_CONFIG.version()
                   for i in load_ensemble(dim=dim))


def test_a_bare_sampler_config_is_not_the_shipped_one():
    """Guards the guard: if the defaults are ever changed to match, this fails and
    whoever did it must decide deliberately whether `SHIPPED_CONFIG` still earns its
    place, rather than leaving a decorative alias behind."""
    from boec.oracles import SHIPPED_CONFIG, SamplerConfig

    assert SamplerConfig().version() != SHIPPED_CONFIG.version()


def test_regenerating_a_committed_seed_reproduces_it_exactly():
    """Extending the ensemble with new seeds must not perturb the existing ones.

    Instances are drawn independently per seed and `instance_id` hashes
    (dim, seed, oracle_version), so this should hold — but "should" is what the
    version field exists to stop us relying on. Checked on the landscape itself,
    not just the parameters.
    """
    from boec.oracles import SHIPPED_CONFIG, HillOracle, accept_instance, propose_instance

    X = np.random.default_rng(0).uniform(0, 1, (32, 6))
    for inst in load_ensemble(dim=6)[:3]:
        got = propose_instance(6, inst.seed, SHIPPED_CONFIG)
        assert got is not None
        accepted, _ = accept_instance(got, SHIPPED_CONFIG)
        assert accepted
        assert got.instance_id == inst.instance_id
        np.testing.assert_array_equal(HillOracle(got).f(X), HillOracle(inst).f(X))


def test_the_committed_ensemble_loads_and_is_the_declared_version():
    # d=6 was extended 25 -> 40 for E4's version-2 power (OPEN-QUESTIONS Q14).
    # d=8 stays at 25: E4 is d=6-only by pre-registration and E2's grid is 25 x 2.
    for dim, expected in ((6, 40), (8, 25)):
        ens = load_ensemble(dim=dim)
        assert len(ens) == expected
        assert all(i.dim == dim for i in ens)
        assert all(i.oracle_version == ENSEMBLE_VERSION for i in ens)
        assert len({i.seed for i in ens}) == expected, "duplicate seeds in the ensemble"


def test_a_sidecar_round_trips_through_the_loader(tmp_path):
    """A clean clone must rebuild the exact landscape, or A/B numbers diverge."""
    inst = load_ensemble(dim=6)[0]
    import json

    p = tmp_path / "x.json"
    p.write_text(json.dumps(inst.sidecar()))
    back = load_instance(p)
    assert back.instance_id == inst.instance_id
    np.testing.assert_allclose(back.gamma, inst.gamma)
    X = torch.rand(16, 6, dtype=torch.double)
    torch.testing.assert_close(BiphasicOracle(back).truth(X), BiphasicOracle(inst).truth(X))


def test_a_longer_evaluate_call_does_not_reproduce_the_shorter_one_s_outcomes():
    """Q26's manipulation is nested in X and NOT in Y. Pinned so nobody re-claims it.

    `BiphasicOracle.observe` draws the whole multiplicative noise vector and then
    the whole additive one from a single stateful generator, so an 18-row call
    shifts the additive block by four positions relative to a 14-row call. The
    designs are bit-identical on their shared prefix; the OUTCOMES are not.

    Q26's pre-registration claimed "the same fourteen points, plus four more --
    nothing else can differ". That is true of the design and false of the data,
    and the test that was supposed to guard it used a constant zero-noise
    evaluator, so it could not have caught this. The difference is a re-draw of
    noise from the same distribution rather than a bias, but it means the two
    arms are not paired at the observation level and the write-up must say so.
    """
    import numpy as np
    import torch

    from boec.optimizers import sobol_design
    from boec.oracles import load_ensemble
    from boec.torch_oracle import BiphasicOracle

    inst = load_ensemble(dim=6)[0]
    bounds = torch.stack([torch.zeros(6, dtype=torch.double),
                          torch.ones(6, dtype=torch.double)])
    X14 = sobol_design(bounds, 14, seed=0)
    X18 = sobol_design(bounds, 18, seed=0)

    assert torch.equal(X18[:14], X14)          # the design IS nested

    Y14, V14 = BiphasicOracle(inst, sigma_rel=0.25, seed=0).evaluate(X14)
    Y18, V18 = BiphasicOracle(inst, sigma_rel=0.25, seed=0).evaluate(X18)

    assert not torch.equal(Y18[:14], Y14)      # the OUTCOMES are not
    # same distribution, not a bias: the discrepancy is small next to the spread
    assert float((Y18[:14] - Y14).abs().max()) < 0.5 * float(Y14.std())
