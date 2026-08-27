"""Marginalising the constant mean, so the posterior cannot collapse to zero width.

`build_gp` point-estimates the GP's constant mean by MLE and never propagates that
estimate's uncertainty. When the data are noise-dominated -- which is the regime real
biology lives in -- MLE drives the outputscale toward zero, and every drop of posterior
variance goes with it. Measured on this project's own iPSC-EC coating data (12 tubes,
signal var 49.5, measured noise var 147.3, SNR 0.34): the posterior collapses to
37.16 +/- 0.01 on observations spanning 22.6 to 47.3.

The correct posterior width there is the standard error of a constant, noise_sd/sqrt(n)
= 12.1/sqrt(12) = 3.5. The model reported 0.01, understating it 350-fold.
"""

import torch

from boec.meanmarg import mean_marginalised_covariance
from boec.surrogate import build_gp


def _flat(n=12, noise=12.0, seed=0):
    """Pure noise around a constant: the SNR-0 limit, where the mean is all there is."""
    g = torch.Generator().manual_seed(seed)
    X = torch.rand(n, 2, generator=g, dtype=torch.double)
    Y = 38.0 + noise * torch.randn(n, 1, generator=g, dtype=torch.double)
    Yvar = torch.full((n, 1), noise ** 2, dtype=torch.double)
    return X, Y, Yvar


def _bounds():
    return torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)


def test_uncorrected_posterior_collapses_on_noise_dominated_data():
    """Pins the defect. If this ever fails, the underlying model changed."""
    X, Y, Yvar = _flat()
    m = build_gp(X, Y, Yvar, _bounds())
    Xt = torch.rand(20, 2, dtype=torch.double)
    with torch.no_grad():
        sd = m.posterior(Xt).variance.reshape(-1).sqrt()
    assert sd.max() < 1.0, f"expected collapse, got sd up to {sd.max():.3f}"


def test_correction_recovers_the_standard_error_of_the_mean():
    """noise_sd / sqrt(n) is the right answer and the correction must find it."""
    n, noise = 12, 12.0
    X, Y, Yvar = _flat(n=n, noise=noise)
    m = build_gp(X, Y, Yvar, _bounds())
    Xt = torch.rand(20, 2, dtype=torch.double)
    cov = mean_marginalised_covariance(m, Xt)
    sd = cov.diagonal().sqrt()
    sem = noise / (n ** 0.5)
    assert (sd > 0.5 * sem).all(), f"sd {sd.min():.3f} vs sem {sem:.3f}"
    assert (sd < 2.0 * sem).all(), f"sd {sd.max():.3f} vs sem {sem:.3f}"


def test_correction_never_reduces_variance():
    """Marginalising a nuisance parameter can only add uncertainty."""
    X, Y, Yvar = _flat()
    m = build_gp(X, Y, Yvar, _bounds())
    Xt = torch.rand(15, 2, dtype=torch.double)
    with torch.no_grad():
        base = m.posterior(Xt).variance.reshape(-1)
    corrected = mean_marginalised_covariance(m, Xt).diagonal()
    assert (corrected >= base - 1e-9).all()


def test_returns_a_valid_covariance():
    X, Y, Yvar = _flat()
    m = build_gp(X, Y, Yvar, _bounds())
    Xt = torch.rand(10, 2, dtype=torch.double)
    cov = mean_marginalised_covariance(m, Xt)
    assert cov.shape == (10, 10)
    assert torch.allclose(cov, cov.T, atol=1e-8)
    assert torch.linalg.eigvalsh(cov).min() > -1e-6


def test_high_snr_data_is_barely_affected():
    """When the signal is strong the mean is well determined; the fix must not bloat it."""
    g = torch.Generator().manual_seed(1)
    X = torch.rand(30, 2, generator=g, dtype=torch.double)
    Y = (100.0 * X[:, :1]).double()                     # strong, noiseless trend
    Yvar = torch.full((30, 1), 1e-4, dtype=torch.double)
    m = build_gp(X, Y, Yvar, _bounds())
    Xt = torch.rand(10, 2, dtype=torch.double)
    with torch.no_grad():
        base = m.posterior(Xt).variance.reshape(-1)
    corrected = mean_marginalised_covariance(m, Xt).diagonal()
    assert (corrected < base + 25.0).all(), (corrected.max(), base.max())
