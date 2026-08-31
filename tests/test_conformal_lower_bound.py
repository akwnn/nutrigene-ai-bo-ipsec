import numpy as np
import pytest

from boec.selfcalib import conformal_lower_bound, conformal_lower_quantile


def test_conformal_radius_uses_conservative_order_statistic():
    # scores are [0.1, 0.2, 0.3, 0.4]; n=4, alpha=.25 => ceil(3.75)=4
    assert conformal_lower_quantile([.9, .8, .7, .6], [1, 1, 1, 1], .25) == pytest.approx(.4)


def test_lower_bound_applies_radius_without_interpolation():
    np.testing.assert_allclose(conformal_lower_bound([1.0, 2.0], .35), [.65, 1.65])


@pytest.mark.parametrize("kwargs", [{"alpha": 0}, {"alpha": 1}, {"alpha": .1, "y": []}])
def test_conformal_inputs_are_validated(kwargs):
    args = {"y": [1, 2], "mu": [1, 2], "alpha": .1}
    args.update(kwargs)
    with pytest.raises(ValueError):
        conformal_lower_quantile(**args)
