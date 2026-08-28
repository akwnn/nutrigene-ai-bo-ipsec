"""The certificate-targeted SPADE policy: registration, reduction, and dispatch."""
from __future__ import annotations

import pytest
import torch

from boec.certstraddle import certificate_straddle, rho_contour_offset
from boec.lse import straddle_score
from boec.spade import SpadeConfig, _reliability_contour


def test_policy_is_registered_and_rho_defaults_to_the_bryan_case():
    config = SpadeConfig(policy="certificate_targeted")
    assert config.policy == "certificate_targeted"
    # 0.5 is Bryan's published latent straddle, so adopting the policy cannot
    # silently move any committed number selected at the median contour.
    assert config.certificate_rho == 0.5


@pytest.mark.parametrize("rho", [0.0, 1.0, -0.1, 1.5, float("nan")])
def test_rho_outside_the_open_unit_interval_is_refused(rho):
    with pytest.raises(ValueError):
        SpadeConfig(policy="certificate_targeted", certificate_rho=rho)


def test_existing_policies_still_reject_unknown_names():
    with pytest.raises(ValueError):
        SpadeConfig(policy="certificate_straddle")


def test_at_rho_one_half_the_score_is_bit_identical_to_the_committed_straddle():
    mean = torch.linspace(-2.0, 2.0, 64, dtype=torch.double)
    sd = torch.linspace(0.1, 1.5, 64, dtype=torch.double)
    theta = 0.3
    assert torch.equal(
        certificate_straddle(mean, sd, theta, 0.5), straddle_score(mean, sd, theta)
    )


def test_higher_rho_displaces_the_target_contour_deeper_into_the_region():
    # The certified region is bounded by a high-exceedance contour, so the targeted
    # contour must sit above the median one by exactly z_rho * sd.
    mean = torch.tensor([1.0], dtype=torch.double)
    sd = torch.tensor([0.5], dtype=torch.double)
    theta = 0.0
    z = rho_contour_offset(0.9)
    expected = 1.96 * sd - (mean - z * sd - theta).abs()
    assert torch.allclose(certificate_straddle(mean, sd, theta, 0.9), expected)
    assert z > 0.0


class _FixedNoiseModel:
    """Minimal stand-in exposing the learned-noise surface the contour helper reads."""

    class _Likelihood:
        noise = torch.tensor([0.25], dtype=torch.double)

    class _Outcome:
        pass

    def __init__(self, scale: float) -> None:
        self.likelihood = self._Likelihood()
        self._scale = scale


def test_reliability_contour_sits_above_tau_by_the_gamma_margin(monkeypatch):
    import boec.spade as spade

    monkeypatch.setattr(
        spade, "_learned_noise_variance", lambda model: torch.tensor(0.04, dtype=torch.double)
    )
    theta = _reliability_contour(object(), tau=1.0, gamma=0.95)
    # theta = tau + z_gamma * sigma, sigma = 0.2, z_0.95 = 1.6449
    assert theta == pytest.approx(1.0 + 1.6448536269514722 * 0.2, rel=1e-9)
    assert theta > 1.0


# The nine registered arm digests, captured from HEAD f05805d BEFORE the
# certificate_targeted policy existed. If adding a parameter moves any of these,
# every committed development row's protocol_digest is invalidated.
_REGISTERED_ARM_DIGESTS = {
    (32, "staged"): "07578c5ebf5b8cbe",
    (32, "fixed_hybrid"): "c75b0cef84e9c3e6",
    (32, "validity_gated"): "b58f7bf04a835764",
    (40, "staged"): "bf259e3cc8fce7fb",
    (40, "fixed_hybrid"): "8b3627f0d79c0501",
    (40, "validity_gated"): "09bf29163ae326f9",
    (44, "staged"): "90617096db0e11b9",
    (44, "fixed_hybrid"): "be94c2fae077eb3d",
    (44, "validity_gated"): "9b597722f2778906",
}


@pytest.mark.parametrize("spec,expected", sorted(_REGISTERED_ARM_DIGESTS.items()))
def test_registered_arm_digests_are_unmoved_by_the_new_parameter(spec, expected):
    opening, policy = spec
    got = SpadeConfig(opening=opening, policy=policy, root_seed=0).protocol_digest
    assert got[:16] == expected, (
        f"protocol digest for spade-o{opening}-{policy} moved; every committed row "
        "carrying the old digest would fail verification"
    )


def test_certificate_rho_is_absent_from_registered_arm_identity():
    import json
    payload = json.loads(SpadeConfig(policy="fixed_hybrid").canonical_json)
    assert "certificate_rho" not in payload


def test_certificate_rho_is_present_for_the_policy_that_reads_it():
    import json
    payload = json.loads(SpadeConfig(policy="certificate_targeted").canonical_json)
    assert payload["certificate_rho"] == 0.5


def test_rho_changes_identity_only_for_the_targeted_policy():
    a = SpadeConfig(policy="certificate_targeted", certificate_rho=0.5).protocol_digest
    b = SpadeConfig(policy="certificate_targeted", certificate_rho=0.9).protocol_digest
    assert a != b
