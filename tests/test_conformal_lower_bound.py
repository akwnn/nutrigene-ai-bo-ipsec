import numpy as np
import pytest

from boec.selfcalib import (
    campaign_latent_inflation,
    conformal_lower_bound,
    conformal_lower_quantile,
)


def test_conformal_radius_uses_conservative_order_statistic():
    # scores are [0.1, 0.2, 0.3, 0.4]; n=4, alpha=.25 => ceil(3.75)=4
    assert conformal_lower_quantile([.9, .8, .7, .6], [1, 1, 1, 1], .25) == pytest.approx(.4)


def test_lower_bound_applies_radius_without_interpolation():
    np.testing.assert_allclose(conformal_lower_bound([1.0, 2.0], .35), [.65, 1.65])


def test_campaign_latent_inflation_is_a_conservative_loo_tail():
    covariance = np.array([[2.0, 0.5], [0.5, 2.0]])
    estimate = campaign_latent_inflation(covariance, [0.0, 2.0], tail=1.0)
    assert np.isfinite(estimate)
    assert estimate >= 1.0


@pytest.mark.parametrize(
    "kwargs", [{"tail": -0.1}, {"tail": 1.1}, {"minimum": 0.9}]
)
def test_campaign_latent_inflation_validates_policy_inputs(kwargs):
    with pytest.raises(ValueError):
        campaign_latent_inflation(np.eye(2), [1.0, 2.0], **kwargs)


@pytest.mark.parametrize("kwargs", [{"alpha": 0}, {"alpha": 1}, {"alpha": .1, "y": []}])
def test_conformal_inputs_are_validated(kwargs):
    args = {"y": [1, 2], "mu": [1, 2], "alpha": .1}
    args.update(kwargs)
    with pytest.raises(ValueError):
        conformal_lower_quantile(**args)
