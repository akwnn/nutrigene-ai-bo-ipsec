import pytest
import torch

from boec.multicqa import Certificate, certificate_from_draws, joint_lower_bound
from boec.reliable_region import ConservativeSetResult


def test_joint_lower_bound_uses_simultaneous_cqa_allocation():
    mean = torch.tensor([[2.0, 3.0], [1.0, 4.0]], dtype=torch.double)
    covariance = torch.diag_embed(torch.full((2, 2), 0.01, dtype=torch.double))
    lower = joint_lower_bound(mean, covariance, alpha=0.05)
    assert lower.shape == mean.shape
    # Bonferroni simultaneous bounds are below the means and finite.
    assert torch.all(lower < mean)
    assert torch.isfinite(lower).all()


def test_certificate_requires_every_cqa_and_reports_limiting_attribute():
    draws = torch.tensor(
        [[[2.0, 2.0, 0.5]], [[2.1, 2.1, 0.6]], [[1.9, 1.9, 0.4]], [[2.0, 2.0, 0.5]]],
        dtype=torch.double,
    )
    certificate = certificate_from_draws(
        draws, thresholds=torch.tensor([1.0, 1.0, 0.8], dtype=torch.double), alpha=0.05,
        cqa_names=("identity", "viability", "yield"),
    )
    assert isinstance(certificate, Certificate)
    assert not bool(certificate.mask[0])
    assert certificate.limiting_cqa == "yield"


def test_empty_joint_certificate_abstains_with_zero_volume():
    draws = torch.ones((8, 3, 2), dtype=torch.double)
    certificate = certificate_from_draws(
        draws, thresholds=torch.tensor([2.0, 2.0], dtype=torch.double), alpha=0.05
    )
    assert certificate.volume == 0.0
    assert certificate.containment is None
    assert certificate.abstention_reason == "no_joint_region"


def test_reliable_region_optional_cqa_fields_preserve_old_constructor():
    result = ConservativeSetResult(
        mask=torch.tensor([True]), crossfit_containment=1.0,
        selection_containment=1.0, volume=1.0, selection_draws=2, evaluation_draws=2
    )
    assert result.limiting_cqa is None
    assert result.abstention_reason is None


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.1])
def test_joint_lower_bound_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError, match="alpha"):
        joint_lower_bound(torch.ones((2, 2)), torch.eye(2), alpha)
