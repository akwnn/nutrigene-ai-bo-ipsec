import numpy as np
import pytest

from boec.answer_control import InflationPolicy, apply_policy, calibrate_inflation
from boec.multicqa import Certificate


def test_calibration_is_deterministic_and_training_only():
    y = np.arange(32, dtype=float)
    covariance = np.ones(32)
    a = calibrate_inflation(y, covariance, target_answer_rate=0.5, seed=7)
    b = calibrate_inflation(y, covariance, target_answer_rate=0.5, seed=7)
    assert a == b
    assert a.training_only is True
    assert a.inflation >= 1.0
    assert a.target_answer_rate == 0.5


def test_target_answer_rate_is_capped_at_registered_value():
    policy = calibrate_inflation(np.ones(16), np.ones(16), target_answer_rate=0.95, seed=1)
    assert policy.target_answer_rate == 0.5


def test_calibration_rejects_evaluation_seed_and_bad_covariance():
    with pytest.raises(ValueError, match="training"):
        calibrate_inflation(np.ones(8), np.ones(8), target_answer_rate=0.5, seed=64)
    with pytest.raises(ValueError):
        calibrate_inflation(np.ones(8), np.zeros(8), target_answer_rate=0.5, seed=1)


def test_apply_policy_only_shrinks_a_certificate():
    cert = Certificate(
        mask=np.array([True, True, False]), containment=1.0, volume=2 / 3,
        abstention_reason=None, limiting_cqa="identity",
        lower_bounds=np.array([2.0, 1.0, -1.0]), cqa_names=("identity",),
    )
    result = apply_policy(cert, InflationPolicy(inflation=2.0, target_answer_rate=0.5,
                                                 seed=1, training_only=True,
                                                 calibration_count=8))
    assert result.volume <= cert.volume
    assert np.all(result.lower_bounds <= cert.lower_bounds)
    assert np.all(~result.mask | cert.mask)


def test_invalid_policy_never_produces_a_positive_certificate():
    cert = Certificate(np.array([True]), 1.0, 1.0, None, "identity",
                       np.array([1.0]), ("identity",))
    bad = InflationPolicy(inflation=1.0, target_answer_rate=0.5, seed=1,
                          training_only=False, calibration_count=0)
    result = apply_policy(cert, bad)
    assert not result.mask.any()
    assert result.volume == 0.0
    assert result.abstention_reason in {"insufficient_calibration", "provenance_mismatch"}
