"""Fail-closed answer-rate calibration for certificates.

Calibration is deliberately a training-only operation.  The policy can widen a
certificate (and therefore abstain), but can never turn an abstention into an answer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

import numpy as np
import torch

from boec.selfcalib import calibration_inflation


REGISTERED_TARGET_ANSWER_RATE = 0.50
EVALUATION_SEED_START = 64


@dataclass(frozen=True)
class InflationPolicy:
    inflation: float
    target_answer_rate: float
    seed: int
    training_only: bool
    calibration_count: int
    provenance: str = "training-seeds-only"


def _array(value, name: str) -> np.ndarray:
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu().numpy()
    result = np.asarray(value, dtype=float)
    if result.size == 0 or not np.isfinite(result).all():
        raise ValueError(f"{name} must be non-empty and finite")
    return result


def calibrate_inflation(y, covariance, target_answer_rate: float, seed: int) -> InflationPolicy:
    """Fit a conservative inflation factor from held-out training residuals.

    ``y`` is the held-out training residual (or observations after subtracting the
    training posterior mean); ``covariance`` is either a variance vector or covariance
    matrix.  No evaluation campaign identifier is accepted: seed values reserved for
    evaluation (64+) are rejected to make accidental leakage loud.
    """
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("seed must be a nonnegative training seed")
    if int(seed) >= EVALUATION_SEED_START:
        raise ValueError("answer-control calibration must use training seeds only")
    rate = float(target_answer_rate)
    if not math.isfinite(rate) or not 0.0 < rate <= 1.0:
        raise ValueError("target_answer_rate must lie in (0, 1]")
    rate = min(rate, REGISTERED_TARGET_ANSWER_RATE)
    obs = _array(y, "y").reshape(-1)
    cov = _array(covariance, "covariance")
    if cov.ndim == 2:
        if cov.shape != (obs.size, obs.size):
            raise ValueError("covariance matrix must match y")
        variance = np.diag(cov)
    elif cov.ndim == 1 and cov.size == obs.size:
        variance = cov
    else:
        raise ValueError("covariance must be a variance vector or matching square matrix")
    if np.any(variance <= 0.0):
        raise ValueError("covariance variances must be positive")
    rng = np.random.default_rng(int(seed))
    order = rng.permutation(obs.size)
    heldout = order[obs.size // 2 :]
    if heldout.size < 2:
        raise ValueError("insufficient_calibration")
    # The existing self-calibration statistic is retained as the scale diagnostic;
    # the held-out split and quantile are what make this policy conservative.
    z = np.abs(obs[heldout]) / np.sqrt(variance[heldout])
    rms = calibration_inflation(z, np.zeros_like(z), np.ones_like(z))
    tail = float(np.quantile(z, 1.0 - rate))
    inflation = max(1.0, float(rms), tail)
    return InflationPolicy(inflation, rate, int(seed), True, int(heldout.size))


def apply_policy(certificate, policy: InflationPolicy):
    """Apply inflation without ever enlarging the supplied certificate.

    Certificates produced by newer multi-CQA code may expose ``thresholds``; when
    absent, fail closed because a generic lower-bound scale has no safe threshold
    reference.  This is intentional and preserves old serialized certificates.
    """
    valid = (isinstance(policy, InflationPolicy) and policy.training_only
             and math.isfinite(float(policy.inflation))
             and float(policy.inflation) >= 1.0 and policy.calibration_count >= 2)
    def empty_mask(mask):
        return torch.zeros_like(mask, dtype=torch.bool) if isinstance(mask, torch.Tensor) else np.zeros_like(mask, dtype=bool)

    if not valid:
        return replace(certificate, mask=empty_mask(certificate.mask),
                       volume=0.0, containment=None,
                       abstention_reason="provenance_mismatch" if not getattr(
                           policy, "training_only", False) else "insufficient_calibration")
    if getattr(certificate, "lower_bounds", None) is None:
        return certificate
    lower = certificate.lower_bounds
    threshold = getattr(certificate, "thresholds", None)
    if threshold is None:
        # Without thresholds, no non-empty transformed region can be justified.
        return replace(certificate, mask=empty_mask(certificate.mask),
                       volume=0.0, containment=None,
                       abstention_reason="provenance_mismatch")
    factor = float(policy.inflation)
    adjusted = threshold + (lower - threshold) / factor
    mask = certificate.mask & (adjusted >= threshold).all(dim=-1) if hasattr(adjusted, "all") else certificate.mask
    volume = float(mask.double().mean()) if hasattr(mask, "double") else float(np.mean(mask))
    return replace(certificate, mask=mask, volume=volume,
                   lower_bounds=adjusted,
                   abstention_reason=None if bool(mask.any()) else "no_joint_region")


__all__ = ["InflationPolicy", "calibrate_inflation", "apply_policy",
           "REGISTERED_TARGET_ANSWER_RATE", "EVALUATION_SEED_START"]
