"""Tests for the model builder.

**Every one of the five silent traps has a test here that fails if the trap is
reintroduced.** That is the point of this file: none of these failures produce
an error message on their own, so the tests are the only thing standing between
us and a plausible-looking but wrong confidence statement.

Trap numbering matches surrogate.py and phase1_build.md §5.
"""

from __future__ import annotations

import math

import pytest
import torch
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel

from boec.surrogate import (
    base_kernel,
    build_gp,
    kernel_is_matern,
    lengthscale_lower_bound,
    lengthscales,
    outcome_scale,
    predictive,
)

D = 4
UNIT = torch.stack([torch.zeros(D, dtype=torch.double), torch.ones(D, dtype=torch.double)])


@pytest.fixture
def data():
    torch.manual_seed(0)
    X = torch.rand(24, D, dtype=torch.double) * 0.5
    Y = torch.sin(X.sum(-1, keepdim=True)) + 1.0
    Yvar = torch.linspace(0.001, 0.05, 24, dtype=torch.double).unsqueeze(-1)
    return X, Y, Yvar


@pytest.fixture
def model(data):
    return build_gp(*data, UNIT, fit=False)


# --------------------------------------------------------------------------
# TRAP 1 — the library defaults to the wrong kernel, silently
# --------------------------------------------------------------------------

def test_trap1_kernel_is_matern_not_the_library_default(model):
    """If this fails the methods section is false and nothing else complains."""
    assert kernel_is_matern(model)
    assert not isinstance(base_kernel(model), RBFKernel)
    assert base_kernel(model).nu == 2.5


def test_trap1_holds_without_the_scale_wrapper(data):
    m = build_gp(*data, UNIT, use_scale_kernel=False, fit=False)
    assert kernel_is_matern(m)


# --------------------------------------------------------------------------
# TRAP 2 — two factories, two shapes; hardcoded paths break on one
# --------------------------------------------------------------------------

def test_trap2_traversal_works_on_both_configurations(data):
    wrapped = build_gp(*data, UNIT, use_scale_kernel=True, fit=False)
    bare = build_gp(*data, UNIT, use_scale_kernel=False, fit=False)

    assert isinstance(wrapped.covar_module, ScaleKernel)
    assert not isinstance(bare.covar_module, ScaleKernel)

    # The helper reaches the same place regardless.
    assert isinstance(base_kernel(wrapped), MaternKernel)
    assert isinstance(base_kernel(bare), MaternKernel)
    assert lengthscales(wrapped).shape == lengthscales(bare).shape == (1, D)


def test_trap2_the_naive_hardcoded_paths_really_do_break(data):
    """Demonstrates why the helper is mandatory rather than merely tidy."""
    wrapped = build_gp(*data, UNIT, use_scale_kernel=True, fit=False)
    bare = build_gp(*data, UNIT, use_scale_kernel=False, fit=False)

    # The common tutorial idiom crashes on the bare configuration.
    with pytest.raises(AttributeError):
        _ = bare.covar_module.base_kernel.lengthscale

    # And an isinstance identity check crashes/false-negatives on the wrapped one.
    assert not isinstance(wrapped.covar_module, MaternKernel)


def test_trap2_helper_accepts_a_kernel_as_well_as_a_model():
    k = ScaleKernel(ScaleKernel(MaternKernel(nu=2.5, ard_num_dims=D)))
    assert isinstance(base_kernel(k), MaternKernel)


def test_trap2_lengthscale_bound_is_read_off_the_object_not_hardcoded(model):
    bound = lengthscale_lower_bound(model)
    assert bound > 0.0
    # It happens to be 0.025 on the installed version. Asserted loosely on
    # purpose: this is version-dependent and the point is that we READ it.
    assert 0.0 < bound < 1.0


# --------------------------------------------------------------------------
# TRAP 3 — inferred bounds silently destroy Experiment 4
# --------------------------------------------------------------------------

def test_trap3_bounds_are_explicit_and_not_learned_from_data(data):
    X, _, _ = data
    m = build_gp(*data, UNIT, fit=False)
    tf = m.input_transform
    # Offset/coefficient must describe the UNIT cube, not the training corner.
    assert torch.allclose(tf.offset.flatten(), torch.zeros(D, dtype=torch.double))
    assert torch.allclose(tf.coefficient.flatten(), torch.ones(D, dtype=torch.double))
    # The training data occupies only a corner — which is the whole risk.
    assert float(X.max()) < 0.6


def test_trap3_extrapolation_point_stays_inside_the_unit_cube(data):
    """With learned bounds this maps outside 1.0 and nothing is comparable."""
    m = build_gp(*data, UNIT, fit=False)
    far = torch.full((1, D), 0.9, dtype=torch.double)
    m.input_transform.eval()
    mapped = m.input_transform(far)
    assert bool(torch.all(mapped <= 1.0 + 1e-12))
    assert torch.allclose(mapped, far)


def test_trap3_bounds_dimension_must_match(data):
    X, Y, Yvar = data
    bad = torch.stack([torch.zeros(D + 1, dtype=torch.double), torch.ones(D + 1, dtype=torch.double)])
    with pytest.raises(ValueError, match="factors"):
        build_gp(X, Y, Yvar, bad, fit=False)


# --------------------------------------------------------------------------
# TRAP 4 — observation_noise=True averages the training noise, silently
# --------------------------------------------------------------------------

def test_trap4_we_never_use_the_averaging_path(model, data):
    """The bug we are avoiding, demonstrated, then shown not to affect us."""
    _, _, Yvar = data
    X_new = torch.rand(5, D, dtype=torch.double) * 0.4 + 0.5

    model.eval()
    with torch.no_grad():
        latent = model.posterior(X_new).variance
        averaged = model.posterior(X_new, observation_noise=True).variance
    delta = (averaged - latent).flatten()

    # The library adds mean(train_Yvar), flat, to every point. Confirmed here so
    # the test fails loudly if a library upgrade changes the behaviour.
    assert torch.allclose(delta, torch.full_like(delta, float(Yvar.mean())), atol=1e-9)
    assert torch.allclose(delta, delta[0].expand_as(delta), atol=1e-12)

    # predictive() with noise=None must NOT include that averaged figure.
    p = predictive(model, X_new)
    assert p.includes_noise is False
    assert torch.allclose(p.variance, latent)


def test_trap4_supplied_noise_varies_per_point(model):
    """The averaging path is flat; ours is not. That is the difference."""
    X_new = torch.rand(5, D, dtype=torch.double) * 0.4 + 0.5
    noise = torch.linspace(0.01, 0.09, 5, dtype=torch.double).unsqueeze(-1)
    p = predictive(model, X_new, noise=noise)
    delta = (p.variance - predictive(model, X_new).variance).flatten()
    assert not torch.allclose(delta, delta[0].expand_as(delta), atol=1e-6)


# --------------------------------------------------------------------------
# TRAP 5 — the units of supplied noise. Off by 161x if you get it wrong.
# --------------------------------------------------------------------------

def test_trap5_supplied_noise_round_trips_in_original_units(model):
    """Pass variance v in outcome units; get exactly v added back."""
    X_new = torch.rand(6, D, dtype=torch.double) * 0.4 + 0.5
    noise = torch.linspace(0.005, 0.05, 6, dtype=torch.double).unsqueeze(-1)

    latent = predictive(model, X_new).variance
    with_noise = predictive(model, X_new, noise=noise).variance
    added = with_noise - latent

    assert torch.allclose(added, noise, atol=1e-10), (
        "supplied noise did not round-trip — trap 5 has been reintroduced"
    )


def test_trap5_the_naive_version_is_wrong_by_the_scale_factor(model):
    """Documents the magnitude of the mistake this function prevents."""
    X_new = torch.rand(4, D, dtype=torch.double) * 0.4 + 0.5
    noise = torch.full((4, 1), 0.03, dtype=torch.double)

    latent = predictive(model, X_new).variance
    model.eval()
    with torch.no_grad():
        naive = model.posterior(X_new, observation_noise=noise).variance
    naive_added = (naive - latent)

    scale2 = outcome_scale(model).pow(2)
    # The naive path adds v * stdvs**2 instead of v.
    assert torch.allclose(naive_added, noise * scale2, atol=1e-10)
    # And the error is large, not marginal.
    ratio = float(noise[0, 0] / naive_added[0, 0])
    assert ratio > 10.0


def test_trap5_scale_factor_is_available_and_positive(model):
    s = outcome_scale(model)
    assert s.numel() == 1
    assert float(s) > 0.0


# --------------------------------------------------------------------------
# Shape contract
# --------------------------------------------------------------------------

def test_rejects_one_dimensional_outcomes(data):
    X, Y, Yvar = data
    with pytest.raises(ValueError, match=r"train_Y must be \(n, m\)"):
        build_gp(X, Y.squeeze(-1), Yvar, UNIT, fit=False)


def test_rejects_mismatched_yvar(data):
    X, Y, Yvar = data
    with pytest.raises(ValueError, match="must match"):
        build_gp(X, Y, Yvar[:-1], UNIT, fit=False)


def test_rejects_negative_yvar(data):
    X, Y, Yvar = data
    bad = Yvar.clone()
    bad[0] = -0.01
    with pytest.raises(ValueError, match="VARIANCE"):
        build_gp(X, Y, bad, UNIT, fit=False)


def test_rejects_negative_prediction_noise(model):
    X_new = torch.rand(3, D, dtype=torch.double)
    with pytest.raises(ValueError, match="VARIANCE"):
        predictive(model, X_new, noise=torch.full((3, 1), -0.01, dtype=torch.double))


def test_rejects_one_dimensional_noise(model):
    X_new = torch.rand(3, D, dtype=torch.double)
    with pytest.raises(ValueError, match=r"noise must be \(n, m\)"):
        predictive(model, X_new, noise=torch.full((3,), 0.01, dtype=torch.double))


def test_predictive_shapes(model):
    X_new = torch.rand(7, D, dtype=torch.double)
    p = predictive(model, X_new)
    assert p.mean.shape == (7, 1)
    assert p.variance.shape == (7, 1)
    assert p.stddev.shape == (7, 1)
    lo, hi = p.interval()
    assert lo.shape == hi.shape == (7, 1)
    assert bool(torch.all(hi > lo))


# --------------------------------------------------------------------------
# Behaviour the paper's argument actually depends on
# --------------------------------------------------------------------------

def test_uncertainty_grows_away_from_the_data(data):
    """The claim in one line: a GP knows when it is guessing.

    This is what a curved-line fit cannot express, and it is why the whole
    approach is worth writing a paper about.
    """
    m = build_gp(*data, UNIT, fit=True)
    near = torch.full((1, D), 0.25, dtype=torch.double)   # inside the training corner
    far = torch.full((1, D), 0.95, dtype=torch.double)    # far outside it
    assert float(predictive(m, far).variance) > float(predictive(m, near).variance)


def test_fitting_actually_changes_the_lengthscales(data):
    unfitted = lengthscales(build_gp(*data, UNIT, fit=False)).clone()
    fitted = lengthscales(build_gp(*data, UNIT, fit=True))
    assert not torch.allclose(unfitted, fitted)


def test_lengthscales_stay_above_the_floor(data):
    m = build_gp(*data, UNIT, fit=True)
    assert bool(torch.all(lengthscales(m) >= lengthscale_lower_bound(m) - 1e-9))


def test_deterministic_given_a_seed(data):
    torch.manual_seed(11)
    a = lengthscales(build_gp(*data, UNIT, fit=True)).clone()
    torch.manual_seed(11)
    b = lengthscales(build_gp(*data, UNIT, fit=True)).clone()
    assert torch.allclose(a, b)


# --------------------------------------------------------------------------
# The shape-aware fallback. Kept despite being a NEGATIVE result — see
# results/NEGATIVE-shape-aware-mean.md. It is worse than a flat fallback, and
# these tests exist so the machinery stays correct for anyone who revisits it.
# --------------------------------------------------------------------------

def test_shape_fallback_collapses_to_the_plain_model_when_its_weight_is_zero():
    """The bounded-downside argument, at least mechanically.

    (It does not hold in practice: the weight is fitted in-sample, where the
    shape IS helpful, so it never shrinks. That is the negative result.)
    """
    from boec.surrogate import BiphasicMean

    d = 4
    m = BiphasicMean(
        torch.full((d,), 0.2, dtype=torch.double),
        torch.full((d,), 0.9, dtype=torch.double),
        torch.full((d,), 2.0, dtype=torch.double),
        torch.full((d,), 0.25, dtype=torch.double),
    )
    with torch.no_grad():
        m.raw_scale.zero_()
        m.offset.fill_(0.7)
    out = m(torch.rand(5, d, dtype=torch.double))
    assert torch.allclose(out, torch.full((5,), 0.7, dtype=torch.double))


def test_shape_fallback_needs_no_unit_conversion():
    """Designed so the rescaling trap cannot arise: the learned scale absorbs
    whatever conversion would otherwise have to be got right by hand."""
    from boec.surrogate import BiphasicMean

    d = 3
    m = BiphasicMean(*(torch.full((d,), v, dtype=torch.double)
                       for v in (0.2, 0.9, 2.0, 0.3)))
    assert m.raw_scale.requires_grad and m.offset.requires_grad
    for name in ("ec50", "ic50", "n_exp", "weights"):
        assert not getattr(m, name).requires_grad, f"{name} must stay frozen"


def test_shape_fallback_refuses_a_failed_fit():
    """A fallback built from a fit that never converged would be arbitrary,
    and arbitrary is worse than flat."""
    from boec.parametric import fit_practitioner_parametric
    from boec.surrogate import biphasic_mean_from_fit

    bad = fit_practitioner_parametric(torch.rand(5, 3, dtype=torch.double),
                                      torch.rand(5, 1, dtype=torch.double))
    assert not bad.converged
    with pytest.raises(ValueError, match="did not converge"):
        biphasic_mean_from_fit(bad)


def test_torch_and_numpy_response_curves_agree():
    """Two copies of the same formula. If one is edited and the other is not,
    this fails."""
    import numpy as np

    from boec.parametric import biphasic_response, biphasic_response_torch

    rng = np.random.default_rng(0)
    ec, ic, n = rng.uniform(0.1, 0.4, 4), rng.uniform(0.6, 1.4, 4), rng.uniform(1, 3, 4)
    X = rng.uniform(0.01, 1.0, (30, 4))
    a = biphasic_response(X, ec, ic, n)
    b = biphasic_response_torch(*(torch.as_tensor(v) for v in (X, ec, ic, n))).numpy()
    assert np.abs(a - b).max() < 1e-12


# ---------------------------------------------------------------------------
# The lengthscale-prior counterfactual (A, for the Q25 diagnostic)
#
# `build_gp` hardcoded `get_covar_module_with_dim_scaled_prior`, so no analysis
# could vary the prior and therefore none could say the prior caused anything.
# This adds ONE selectable alternative and pins down that it changes exactly one
# thing. The naive swap -- calling `get_matern_kernel_with_gamma_prior` -- would
# change three at once: it returns an ALREADY-wrapped ScaleKernel (so build_gp
# would double-wrap), it attaches an outputscale prior the production model does
# not have, and its constraint is Positive() rather than GreaterThan(0.025,
# transform=None), which changes the optimiser's box. A counterfactual that moves
# three variables cannot attribute a difference to any of them.
# ---------------------------------------------------------------------------

def _gp(prior, d=6, n=14):
    import torch
    from boec.surrogate import build_gp
    b = torch.stack([torch.zeros(d, dtype=torch.double),
                     torch.ones(d, dtype=torch.double)])
    g = torch.Generator().manual_seed(0)
    X = torch.rand(n, d, dtype=torch.double, generator=g)
    Y = torch.rand(n, 1, dtype=torch.double, generator=g)
    V = torch.full((n, 1), 0.01, dtype=torch.double)
    return build_gp(X, Y, V, b, fit=False, lengthscale_prior=prior)


def test_default_lengthscale_prior_is_unchanged():
    from gpytorch.priors import LogNormalPrior
    from boec.surrogate import base_kernel
    k = base_kernel(_gp("dim_scaled"))
    assert isinstance(k.lengthscale_prior, LogNormalPrior)
    assert float(k.lengthscale_prior.loc) == pytest.approx(
        math.sqrt(2) + 0.5 * math.log(6), abs=1e-4)


def test_gamma_option_changes_the_prior_and_nothing_else():
    from gpytorch.kernels import MaternKernel, ScaleKernel
    from gpytorch.priors import GammaPrior
    from boec.surrogate import base_kernel

    a, b = _gp("dim_scaled"), _gp("gamma")
    ka, kb = base_kernel(a), base_kernel(b)

    # the one intended difference
    assert isinstance(kb.lengthscale_prior, GammaPrior)
    assert float(kb.lengthscale_prior.concentration) == pytest.approx(3.0)
    assert float(kb.lengthscale_prior.rate) == pytest.approx(6.0)

    # everything else identical
    assert type(ka) is type(kb) is MaternKernel
    assert ka.nu == kb.nu == 2.5
    assert ka.ard_num_dims == kb.ard_num_dims == 6
    ca, cb = ka.raw_lengthscale_constraint, kb.raw_lengthscale_constraint
    assert type(ca) is type(cb)
    assert float(ca.lower_bound) == float(cb.lower_bound) == pytest.approx(0.025)
    assert ca.enforced == cb.enforced          # transform=None on both
    # exactly one ScaleKernel wrapper, and no outputscale prior on either
    assert type(a.covar_module) is type(b.covar_module) is ScaleKernel
    assert not isinstance(b.covar_module.base_kernel, ScaleKernel)
    assert [p[0] for p in a.named_priors()] == [p[0] for p in b.named_priors()]


def test_gamma_prior_penalises_long_lengthscales_far_harder():
    """The actual mechanism, quantified — and the reason the swap is a real lever.

    The dim-scaled LogNormal is PERMISSIVE of long lengthscales, not attracted to
    them: it prefers 0.5 over 10 by only ~1.5 nats per dimension, where Gamma(3,6)
    prefers it by ~51. Their MODES are nearly the same place (0.502 vs 0.333), so
    swapping priors changes the penalty on the tail, not the starting belief.
    """
    import torch
    from boec.surrogate import base_kernel

    pa = base_kernel(_gp("dim_scaled")).lengthscale_prior
    pb = base_kernel(_gp("gamma")).lengthscale_prior
    lo, hi = torch.tensor(0.5, dtype=torch.double), torch.tensor(10.0, dtype=torch.double)

    gap_lognormal = float(pa.log_prob(lo) - pa.log_prob(hi))
    gap_gamma = float(pb.log_prob(lo) - pb.log_prob(hi))
    assert 1.0 < gap_lognormal < 2.5
    assert gap_gamma > 40.0
    assert gap_gamma > 20 * gap_lognormal


def test_unknown_lengthscale_prior_is_rejected():
    with pytest.raises(ValueError, match="lengthscale_prior"):
        _gp("matern")


# --------------------------------------------------------------------------
# Q30 — the additive kernel
#
# Q22 measured this benchmark at 93% additive; Q25 measured the production
# surrogate capturing 16% of the shape variance along the axes that matter.
# Those two facts together are a model-class mismatch, not a tuning problem,
# and these tests cover the alternative model class.
# --------------------------------------------------------------------------

def _tiny(d=4, n=24, seed=0):
    import numpy as np
    rng = np.random.default_rng(seed)
    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])
    X = torch.from_numpy(rng.uniform(size=(n, d)))
    # Genuinely additive in the first two factors, flat in the rest.
    Y = (torch.sin(3 * X[:, :1]) + 0.5 * X[:, 1:2] ** 2).double()
    Yvar = torch.full_like(Y, 1e-4)
    return X, Y, Yvar, bounds


def test_product_is_still_the_default_and_is_unchanged():
    """Every stored E2 number is a product-kernel number. It stays the default."""
    from boec.surrogate import is_additive

    X, Y, Yvar, bounds = _tiny()
    assert not is_additive(build_gp(X, Y, Yvar, bounds, fit=False))
    assert kernel_is_matern(build_gp(X, Y, Yvar, bounds, fit=False))


def test_additive_kernel_has_one_component_per_factor():
    from boec.surrogate import component_variances, is_additive

    X, Y, Yvar, bounds = _tiny()
    m = build_gp(X, Y, Yvar, bounds, fit=False, kernel_structure="additive")
    assert is_additive(m)
    assert component_variances(m).shape == (4,)


def test_additive_components_are_each_one_dimensional_and_cover_every_factor():
    """A missing or doubled active_dims would silently drop or double a factor."""
    X, Y, Yvar, bounds = _tiny()
    m = build_gp(X, Y, Yvar, bounds, fit=False, kernel_structure="additive")
    dims = []
    for sub in m.covar_module.kernels:
        inner = sub.base_kernel
        assert inner.active_dims is not None and len(inner.active_dims) == 1
        dims.append(int(inner.active_dims[0]))
    assert sorted(dims) == [0, 1, 2, 3]


def test_interaction_variant_nests_the_production_kernel():
    """It is a strict superset: d one-dimensional terms PLUS one full ARD term.

    This is what stops the comparison being won by removing capacity — the
    additive+interaction model can represent anything the production model can.
    """
    X, Y, Yvar, bounds = _tiny()
    m = build_gp(X, Y, Yvar, bounds, fit=False,
                 kernel_structure="additive+interaction")
    subs = list(m.covar_module.kernels)
    assert len(subs) == 5                       # 4 factors + 1 interaction
    full = [s for s in subs if s.base_kernel.active_dims is None]
    assert len(full) == 1
    assert full[0].base_kernel.ard_num_dims == 4


def test_the_prior_is_held_at_the_production_value_by_default():
    """Switching structure must move the structure and nothing else (Q25)."""
    from math import log, sqrt

    X, Y, Yvar, bounds = _tiny()
    prod = build_gp(X, Y, Yvar, bounds, fit=False)
    add = build_gp(X, Y, Yvar, bounds, fit=False, kernel_structure="additive")
    want = sqrt(2.0) + log(4) * 0.5
    assert base_kernel(prod).lengthscale_prior.loc.item() == pytest.approx(want)
    for sub in add.covar_module.kernels:
        assert sub.base_kernel.lengthscale_prior.loc.item() == pytest.approx(want)


def test_additive_prior_dims_actually_changes_the_prior():
    """The documented 0.502-vs-0.205 difference must be real, or the option is a no-op."""
    from math import sqrt

    X, Y, Yvar, bounds = _tiny()
    m = build_gp(X, Y, Yvar, bounds, fit=False, kernel_structure="additive",
                 additive_prior_dims=1)
    for sub in m.covar_module.kernels:
        assert sub.base_kernel.lengthscale_prior.loc.item() == pytest.approx(sqrt(2.0))


def test_reading_lengthscales_off_an_additive_model_raises_rather_than_lying():
    """An additive kernel has no single per-factor lengthscale. Returning one
    component's would be a believable wrong number — the exact failure
    `base_kernel` exists to prevent."""
    X, Y, Yvar, bounds = _tiny()
    m = build_gp(X, Y, Yvar, bounds, fit=False, kernel_structure="additive")
    with pytest.raises(ValueError, match="ADDITIVE"):
        lengthscales(m)


def test_component_variances_refuses_a_product_model():
    X, Y, Yvar, bounds = _tiny()
    with pytest.raises(ValueError, match="product kernel"):
        from boec.surrogate import component_variances
        component_variances(build_gp(X, Y, Yvar, bounds, fit=False))


def test_an_unknown_structure_raises_rather_than_falling_through():
    """A misspelling that defaulted would run the production model under
    another arm's label, and nothing downstream would notice."""
    X, Y, Yvar, bounds = _tiny()
    with pytest.raises(ValueError, match="kernel_structure"):
        build_gp(X, Y, Yvar, bounds, fit=False, kernel_structure="addative")


def test_additive_structure_refuses_to_move_two_things_at_once():
    """Structure and prior together would make a difference unattributable (Q25)."""
    X, Y, Yvar, bounds = _tiny()
    with pytest.raises(ValueError, match="two things at once"):
        build_gp(X, Y, Yvar, bounds, fit=False, kernel_structure="additive",
                 lengthscale_prior="gamma")


def test_the_additive_model_finds_the_factor_that_matters():
    """End to end, on data that IS additive: the inert factors' components must
    shrink well below the active ones. This is the mechanism the whole arm rests
    on — relevance as a variance, which is identified, rather than as a
    lengthscale, which is not."""
    from boec.surrogate import component_variances

    X, Y, Yvar, bounds = _tiny(d=4, n=40, seed=3)
    m = build_gp(X, Y, Yvar, bounds, kernel_structure="additive")
    v = component_variances(m).detach()
    assert float(v[0]) > float(v[2]), "the driving factor must outweigh an inert one"
    assert float(v[0]) > float(v[3])


def test_the_additive_model_still_predicts_and_gives_intervals():
    """Whatever the kernel, `predictive` must keep working — it is the only
    place allowed to touch prediction noise (C1/C2)."""
    X, Y, Yvar, bounds = _tiny()
    m = build_gp(X, Y, Yvar, bounds, kernel_structure="additive+interaction")
    p = predictive(m, X[:5], noise=None)
    assert p.mean.shape == (5, 1)
    lo, hi = p.interval()
    assert bool(torch.all(hi > lo))
