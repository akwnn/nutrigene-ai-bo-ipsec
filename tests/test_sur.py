"""Stepwise uncertainty reduction for CERTIFIED VOLUME -- the objective itself.

`boec.lse`'s own docstring (line 13) calls Bryan's straddle "the practical stand-in for
Chevalier et al.'s (Technometrics 2014) closed-form parallel SUR". The stand-in is all
this project has ever run. Every acquisition tried -- straddle, predictive straddle,
certificate-contour straddle -- is a PROXY for a quantity none of them computes.

What the certificate actually maximises is the volume of S with
`P(S subset {f > tau}) >= alpha`. That joint probability collapses multiplicatively when
uncertainty across the region is INDEPENDENT and barely moves when it is CORRELATED. So
the well that helps most is not the most uncertain one, nor the one nearest the contour --
it is the one whose measurement removes the most *independent ways the region can fail*.

The GP's posterior variance update is independent of the observed y (Rasmussen & Williams
2006, eq. 2.26), so the post-measurement variance at every grid point is computable
EXACTLY before measuring anything. That is what makes this a closed form rather than a
simulation.
"""

import torch

from boec.sur import certified_volume, sur_gain, batch_sur


def _mean_cov(n=40, seed=0):
    """A smooth 1-D-ish posterior: correlated, so the joint probability has structure."""
    g = torch.Generator().manual_seed(seed)
    x = torch.linspace(0, 1, n, dtype=torch.double)
    mean = (1.5 - 2.0 * (x - 0.5) ** 2).reshape(-1, 1)
    d = (x.unsqueeze(0) - x.unsqueeze(1)).abs()
    cov = 0.35 * torch.exp(-(d / 0.25) ** 2) + 1e-6 * torch.eye(n, dtype=torch.double)
    return mean, cov


def test_certified_volume_is_between_zero_and_one():
    mean, cov = _mean_cov()
    for tau in (0.0, 1.0, 2.0):
        v = certified_volume(mean, cov, tau, 0.95, n_draws=800, seed=0)
        assert 0.0 <= v <= 1.0


def test_certified_volume_falls_as_the_threshold_rises():
    mean, cov = _mean_cov()
    vs = [certified_volume(mean, cov, t, 0.95, n_draws=1500, seed=0)
          for t in (0.0, 0.8, 1.2, 1.6)]
    assert vs == sorted(vs, reverse=True), vs


def test_certified_volume_falls_as_confidence_rises():
    mean, cov = _mean_cov()
    vs = [certified_volume(mean, cov, 0.8, a, n_draws=1500, seed=0)
          for a in (0.5, 0.8, 0.95, 0.99)]
    assert vs == sorted(vs, reverse=True), vs


def test_sur_gain_is_never_negative():
    """Measuring a point can only shrink posterior variance, so volume can only grow."""
    mean, cov = _mean_cov()
    g = sur_gain(mean, cov, tau=0.8, alpha=0.95, noise=0.01,
                 idx=list(range(0, 40, 4)), n_draws=800, seed=0)
    assert (g >= -1e-9).all(), g.min()


def test_an_already_certain_point_gains_nothing():
    """Zero variance at x means measuring x tells the model nothing it did not know."""
    mean, cov = _mean_cov()
    cov[7, :] = 0.0
    cov[:, 7] = 0.0
    cov = cov + 1e-12 * torch.eye(cov.shape[0], dtype=torch.double)
    g = sur_gain(mean, cov, tau=0.8, alpha=0.95, noise=0.01, idx=[7, 20],
                 n_draws=800, seed=0)
    assert abs(float(g[0])) < 1e-6, float(g[0])


def test_batch_returns_the_requested_number_of_distinct_points():
    mean, cov = _mean_cov()
    idx = batch_sur(mean, cov, tau=0.8, alpha=0.95, noise=0.01, q=4,
                    n_draws=600, seed=0)
    assert len(idx) == 4
    assert len(set(idx)) == 4


def test_batch_is_seeded_and_reproducible():
    mean, cov = _mean_cov()
    kw = dict(tau=0.8, alpha=0.95, noise=0.01, q=3, n_draws=600, seed=5)
    assert batch_sur(mean, cov, **kw) == batch_sur(mean, cov, **kw)
