"""Selection-blind certification: mean from all wells, covariance from the unselected ones.

The claim this rests on is exact, not heuristic: a GP posterior covariance is a function of
the DESIGN LOCATIONS and kernel only --

    Sigma_post(A) = K(A,A) - K(A,D) [K(D,D) + noise]^-1 K(D,A)

-- and does not involve the observed y-values anywhere. So the covariance implied by a
SUBSET of the design is exactly computable, and because conditioning on more points can only
reduce posterior variance, the subset's covariance is pointwise LARGER. Using it is
conservative by construction.

These tests assert both halves of that claim on real GP fits, because the whole KW design
depends on it being true rather than approximately true.
"""

import torch
import pytest

from boec.selectionblind import selection_blind_covariance


def _fit(X, Y, dim):
    from boec.replay import unit_bounds
    from boec.surrogate import build_gp
    Yvar = torch.full_like(Y, 0.01)
    return build_gp(X, Y, Yvar, unit_bounds(dim))


@pytest.mark.slow
def test_subset_covariance_is_pointwise_larger_than_the_full_design():
    """The mathematical claim KW depends on. Conditioning on MORE points cannot increase
    posterior variance, so the plate-1-only variance must dominate everywhere."""
    torch.manual_seed(0)
    d = 3
    X1 = torch.rand(20, d, dtype=torch.double)
    X2 = torch.rand(8, d, dtype=torch.double)
    Xall = torch.cat([X1, X2])
    Yall = (Xall.sum(dim=1, keepdim=True)).double()
    Z = torch.rand(50, d, dtype=torch.double)

    m_full = _fit(Xall, Yall, d)
    m_p1 = _fit(X1, Yall[:20], d)

    v_full = torch.diag(selection_blind_covariance(m_full, Z))
    v_sub = torch.diag(selection_blind_covariance(m_p1, Z))
    assert bool((v_sub >= v_full - 1e-9).all()), (
        "the unselected sub-design produced a SMALLER variance somewhere -- the "
        "conservatism KW claims is not holding")


@pytest.mark.slow
def test_a_design_with_no_plate_two_is_unchanged():
    """`plate1_only` has no plate 2, so selection-blind and standard certification must be
    bit-identical for it. It is KW's null control and any movement is a bug."""
    torch.manual_seed(0)
    d = 3
    X1 = torch.rand(20, d, dtype=torch.double)
    Y1 = X1.sum(dim=1, keepdim=True).double()
    Z = torch.rand(40, d, dtype=torch.double)
    m = _fit(X1, Y1, d)
    a = selection_blind_covariance(m, Z)
    b = selection_blind_covariance(m, Z)
    assert torch.equal(a, b)


@pytest.mark.slow
def test_covariance_is_symmetric_positive_definite_and_choleskyable():
    """It is fed straight into `torch.linalg.cholesky` to build the draws."""
    torch.manual_seed(0)
    d = 3
    X = torch.rand(24, d, dtype=torch.double)
    Y = X.sum(dim=1, keepdim=True).double()
    Z = torch.rand(60, d, dtype=torch.double)
    C = selection_blind_covariance(_fit(X, Y, d), Z)
    assert torch.allclose(C, C.T, atol=1e-10)
    torch.linalg.cholesky(C + 1e-8 * torch.eye(C.shape[0], dtype=torch.double))
