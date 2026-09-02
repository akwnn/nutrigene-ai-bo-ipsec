"""KV's plate-2 arm: `_two_plate(mode="cert")` targets the certificate's own contour.

Registered in `docs/SPADE-PLATE2-CERTIFICATE-SPEC.md` §3/§4, frozen at `1df991a`.

Two things are asserted here, and the second matters more than the first.

1. `mode="cert"` places plate 2 by `batch_lse_rho(..., rho=0.95)` rather than Bryan's
   straddle, so its wells differ from `mode="lse"` on the same seed and oracle. This is KV §4's
   **mandatory arm-distinctness assertion**: two arms silently identical is the failure mode a
   `rho` parameter most invites, and this repository has shipped three errata of exactly that
   shape (`EV(x)` reading ground truth; `exclusion_radius` hardcoded to 0.1; `above_ceiling`
   copied across rows).

2. An **unknown** mode must raise. As written, `_two_plate`'s dispatch is
   `if mode == "random": ... else: <latent straddle>`, so any typo -- `"certt"`, `"cert "`,
   a stale string from a config -- silently runs the committed `versionb` criterion while the
   row is labelled something else. That is the same class of defect as the three errata above,
   and it is live in the code right now regardless of whether KV is ever run.
"""

import importlib.util
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[2]


def _vb():
    spec = importlib.util.spec_from_file_location(
        "_kv_vb", ROOT / "software" / "scripts" / "run_versionb.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _oracle(dim=6, seed=0):
    from boec.replay import family_evaluator
    return family_evaluator("levy", dim, 0.25, seed)


@pytest.mark.slow
def test_cert_mode_places_plate_two_differently_from_the_straddle_arm():
    """KV §4: the arms must not be silently identical."""
    VB = _vb()
    orc = _oracle()
    X_lse, *_ = VB._two_plate(orc, 6, 0, 1.0, "lse")
    X_cert, *_ = VB._two_plate(orc, 6, 0, 1.0, "cert")

    assert X_lse.shape == X_cert.shape
    p2_lse, p2_cert = X_lse[VB.N_PLATE1:], X_cert[VB.N_PLATE1:]
    assert not torch.equal(p2_lse, p2_cert), (
        "cert and lse produced identical plate-2 batches -- the rho parameter is not "
        "reaching the selection")


@pytest.mark.slow
def test_plate_one_is_identical_across_modes():
    """Only plate 2 may differ. A mode that changed plate 1 would confound the comparison
    KV exists to make."""
    VB = _vb()
    orc = _oracle()
    X_lse, *_ = VB._two_plate(orc, 6, 0, 1.0, "lse")
    X_cert, *_ = VB._two_plate(orc, 6, 0, 1.0, "cert")
    assert torch.equal(X_lse[:VB.N_PLATE1], X_cert[:VB.N_PLATE1])


@pytest.mark.slow
def test_cert_mode_returns_the_full_well_budget():
    VB = _vb()
    X, Y, V, diag = VB._two_plate(_oracle(), 6, 0, 1.0, "cert")
    assert X.shape[0] == VB.N_PLATE1 + VB.N_PLATE2
    assert Y.shape[0] == X.shape[0] == V.shape[0]
    assert diag["plate2_mode"] == "cert"


def test_an_unknown_mode_raises_instead_of_silently_running_the_straddle():
    """The live defect this test pins. `else: <latent straddle>` means a typo produces a
    correctly-labelled row computed by the WRONG criterion, silently."""
    VB = _vb()
    with pytest.raises(ValueError, match="mode"):
        VB._two_plate(_oracle(), 6, 0, 1.0, "certt")


def test_the_three_committed_modes_are_still_accepted():
    """The guard must not break the arms that already have committed columns."""
    VB = _vb()
    assert set(VB.PLATE2_MODES) == {"lse", "predictive", "random", "cert"}
