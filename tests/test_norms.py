"""The two competing error norms. K0 asks which one governs regret."""

import torch

from boec.norms import grid_r2, sobol_grid, sup_err


class _Constant:
    """Stand-in for a fitted model: posterior mean is a fixed offset from truth."""

    def __init__(self, offset):
        self.offset = offset

    def posterior_mean(self, X):
        return torch.full((X.shape[0], 1), float(self.offset), dtype=torch.double)


def _zero_truth(X):
    return torch.zeros((X.shape[0], 1), dtype=torch.double)


def test_sup_err_is_the_max_absolute_deviation():
    grid = sobol_grid(3, 256, seed=0)
    assert sup_err(_Constant(0.25), _zero_truth, grid) == 0.25


def test_sup_err_is_zero_for_a_perfect_model():
    grid = sobol_grid(3, 256, seed=0)
    assert sup_err(_Constant(0.0), _zero_truth, grid) == 0.0


def test_grid_r2_is_negative_when_the_model_is_worse_than_the_mean():
    """Truth varies, model is constant and wrong: R^2 must go negative, not clamp."""
    grid = sobol_grid(2, 512, seed=0)

    def truth(X):
        return X[:, :1].double()

    assert grid_r2(_Constant(5.0), truth, grid) < 0.0


def test_grid_r2_is_one_for_a_perfect_model():
    grid = sobol_grid(2, 512, seed=0)

    class _Exact:
        def posterior_mean(self, X):
            return X[:, :1].double()

    assert grid_r2(_Exact(), lambda X: X[:, :1].double(), grid) == 1.0


def test_sobol_grid_is_deterministic_in_its_seed():
    assert torch.equal(sobol_grid(4, 128, seed=7), sobol_grid(4, 128, seed=7))
    assert not torch.equal(sobol_grid(4, 128, seed=7), sobol_grid(4, 128, seed=8))


def test_norms_accepts_the_designspace_protocol_without_refitting():
    """A caller holding a chunked posterior must not be routed back into model.posterior,
    which builds the joint covariance (100.6s at N=20,000 vs 0.06s at N=2,000)."""
    grid = sobol_grid(2, 128, seed=0)

    class _PairOnly:
        """Exposes ONLY posterior_mean_and_sd. No posterior, no posterior_mean."""

        def posterior_mean_and_sd(self, X):
            mean = torch.zeros(X.shape[0], dtype=torch.double)
            return mean, torch.full_like(mean, 0.1)

    assert sup_err(_PairOnly(), lambda X: torch.full((X.shape[0], 1), 0.4,
                                                     dtype=torch.double), grid) == 0.4
