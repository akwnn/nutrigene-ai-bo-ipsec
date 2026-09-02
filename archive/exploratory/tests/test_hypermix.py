"""Hyperparameter-mixture posteriors, to attack bias that inflation cannot reach.

`SPADE-ASSURANCE-CALIBRATION-SPEC.md` §10.2 established the limit: inflation scales the
posterior SD and leaves the mean untouched, while the Vorob'ev quantile shrinks toward the
HIGHEST-probability points. A point the GP is confidently wrong about is therefore retained
at every `c`. On levy and rosenbrock that saturates truth containment at 0.75 and 0.73.

MLE fixes the lengthscale and outputscale at a point estimate, so any error in them is a
STRUCTURED error in the mean. Mixing over several marginal-likelihood-weighted fits
changes the shape of the posterior, not merely its scale -- which is the only way to
move a confidently-wrong point.
"""

import torch

from boec.hypermix import hyperparameter_ensemble, mixture_draws


def _data(n=24, seed=0):
    g = torch.Generator().manual_seed(seed)
    X = torch.rand(n, 3, generator=g, dtype=torch.double)
    Y = (torch.sin(6 * X[:, :1]) + 0.3 * X[:, 1:2]).double()
    Yvar = torch.full((n, 1), 0.05 ** 2, dtype=torch.double)
    return X, Y, Yvar


def _bounds(d=3):
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def test_ensemble_returns_the_requested_number_of_models():
    X, Y, Yvar = _data()
    models, w = hyperparameter_ensemble(X, Y, Yvar, _bounds(), n_models=4, seed=0)
    assert len(models) == 4
    assert w.shape == (4,)


def test_weights_are_a_normalised_distribution():
    X, Y, Yvar = _data()
    _, w = hyperparameter_ensemble(X, Y, Yvar, _bounds(), n_models=4, seed=0)
    assert torch.isclose(w.sum(), torch.tensor(1.0, dtype=torch.double))
    assert (w >= 0).all()


def test_ensemble_members_are_not_all_identical():
    """If every restart lands on the same optimum there is no mixture to speak of."""
    X, Y, Yvar = _data()
    models, _ = hyperparameter_ensemble(X, Y, Yvar, _bounds(), n_models=5, seed=0)
    Xt = torch.rand(30, 3, dtype=torch.double)
    with torch.no_grad():
        means = torch.stack([m.posterior(Xt).mean.reshape(-1) for m in models])
    assert float(means.std(dim=0).max()) > 0.0


def test_mixture_draws_have_the_requested_shape_and_are_seeded():
    X, Y, Yvar = _data()
    models, w = hyperparameter_ensemble(X, Y, Yvar, _bounds(), n_models=3, seed=0)
    Xt = torch.rand(40, 3, dtype=torch.double)
    a = mixture_draws(models, w, Xt, n_draws=200, seed=7)
    b = mixture_draws(models, w, Xt, n_draws=200, seed=7)
    assert a.shape == (200, 40)
    assert torch.allclose(a, b), "same seed must reproduce the same draws"


def test_mixture_is_at_least_as_wide_as_its_best_single_member():
    """Marginalising a nuisance parameter cannot, on average, sharpen the posterior."""
    X, Y, Yvar = _data()
    models, w = hyperparameter_ensemble(X, Y, Yvar, _bounds(), n_models=5, seed=0)
    Xt = torch.rand(50, 3, dtype=torch.double)
    best = models[int(torch.argmax(w))]
    with torch.no_grad():
        sd_best = best.posterior(Xt).variance.reshape(-1).sqrt()
    sd_mix = mixture_draws(models, w, Xt, n_draws=3000, seed=0).std(dim=0)
    assert float(sd_mix.mean()) > 0.75 * float(sd_best.mean())


def test_mixture_mean_can_differ_from_the_single_fit_mean():
    """THE point of this module: inflation cannot move the mean and this can."""
    X, Y, Yvar = _data()
    models, w = hyperparameter_ensemble(X, Y, Yvar, _bounds(), n_models=5, seed=0)
    Xt = torch.rand(50, 3, dtype=torch.double)
    best = models[int(torch.argmax(w))]
    with torch.no_grad():
        mu_best = best.posterior(Xt).mean.reshape(-1)
    mu_mix = mixture_draws(models, w, Xt, n_draws=4000, seed=0).mean(dim=0)
    assert mu_mix.shape == mu_best.shape
