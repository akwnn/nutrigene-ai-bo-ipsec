"""Q47 — guards for the multi-fidelity threshold harness.

Three of these are not conveniences. The registration promises them by name:

* **the cost identity** — `k + n_cheap/c == budget` asserted per arm, because the whole
  surface means nothing if the two tiers are not actually spending the same money;
* **the achieved correlation** — the sweep is parameterised by ρ, so a σ_cheap that
  produces some *other* correlation silently relabels every column of the result;
* **the affine invariance** — screen-then-confirm selects on a ranking, and an affine map
  with a positive slope preserves rankings, so the sampled calibration `(a, b)` provably
  cannot move it. That is a proof, not a hope, and it is the sharpest available check
  that the cheap readout is wired up the way the registration says it is. If the
  sampled-versus-fixed sensitivity analysis ever shows `screen` moving, this test
  localises the bug immediately.
"""

from __future__ import annotations

import numpy as np
import pytest

from boec.multifidelity import (
    Allocation,
    CheapTier,
    allocate,
    cheap_sigma,
    draw_cheap,
    Recalibration,
    recalibrate,
    split_confirm,
    top_k,
)


# ---------------------------------------------------------------------------
# the cost identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cost_ratio", [3, 5, 10, 20])
@pytest.mark.parametrize("phi", [0.25, 1.0 / 3.0, 0.5])
def test_allocation_spends_exactly_the_budget(cost_ratio: int, phi: float) -> None:
    a = allocate(budget=48, cost_ratio=cost_ratio, phi=phi)
    assert isinstance(a, Allocation)
    assert a.n_expensive + a.n_cheap / cost_ratio == pytest.approx(48.0, abs=1e-12)
    assert a.n_expensive == int(a.n_expensive)
    assert a.n_cheap == int(a.n_cheap)


def test_allocation_refuses_a_split_it_cannot_spend_exactly() -> None:
    # phi=0.3 of 48 is 14.4 expensive-equivalents: not an integer number of confirmations
    with pytest.raises(ValueError, match="exactly"):
        allocate(budget=48, cost_ratio=10, phi=0.3)


def test_single_tier_allocation_is_the_whole_budget() -> None:
    a = allocate(budget=48, cost_ratio=10, phi=0.0)
    assert (a.n_expensive, a.n_cheap) == (48, 0)


# ---------------------------------------------------------------------------
# the achieved correlation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rho", [0.30, 0.55, 0.80, 0.95])
@pytest.mark.parametrize("a,b", [(1.0, 0.0), (0.4, -3.0), (2.7, 5.5)])
def test_cheap_readout_achieves_the_target_correlation(rho: float, a: float,
                                                       b: float) -> None:
    rng = np.random.default_rng(0)
    y = rng.normal(0.68, 0.1228, size=200_000)          # this project's own signal scale
    tier = CheapTier(a=a, b=b, sigma_cheap=cheap_sigma(a, float(y.std()), rho),
                     rho_target=rho)
    yc = draw_cheap(y, tier, rng)
    assert np.corrcoef(yc, y)[0, 1] == pytest.approx(rho, abs=0.01)


def test_cheap_sigma_is_a_standard_deviation_not_a_variance() -> None:
    # rho = a*sf / sqrt(a^2 sf^2 + sc^2); at rho = 1/sqrt(2) the two terms are equal
    assert cheap_sigma(1.0, 0.2, 1.0 / np.sqrt(2.0)) == pytest.approx(0.2, rel=1e-9)


def test_a_perfect_cheap_readout_has_no_noise() -> None:
    assert cheap_sigma(1.3, 0.2, 1.0) == 0.0


def test_a_non_positive_slope_is_refused() -> None:
    with pytest.raises(ValueError, match="positive"):
        cheap_sigma(-1.0, 0.2, 0.5)


# ---------------------------------------------------------------------------
# the affine invariance -- provable, so tested as an identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rho", [0.30, 0.65, 0.95])
def test_screening_is_exactly_invariant_to_the_sampled_calibration(rho: float) -> None:
    rng = np.random.default_rng(7)
    y = rng.normal(0.68, 0.1228, size=400)
    sf = float(y.std())
    z = rng.standard_normal(y.shape)

    def picked(a: float, b: float) -> np.ndarray:
        tier = CheapTier(a=a, b=b, sigma_cheap=cheap_sigma(a, sf, rho), rho_target=rho)
        return np.sort(top_k(draw_cheap(y, tier, z=z), 32))

    base = picked(1.0, 0.0)
    assert np.array_equal(base, picked(0.31, -4.2))
    assert np.array_equal(base, picked(9.9, +7.7))


def test_top_k_returns_exactly_k_distinct_best_indices() -> None:
    v = np.array([5.0, 1.0, 4.0, 9.0, 2.0])
    assert sorted(top_k(v, 2).tolist()) == [0, 3]
    assert len(set(top_k(v, 5).tolist())) == 5


def test_split_confirm_is_half_top_and_half_from_the_rest() -> None:
    rng = np.random.default_rng(1)
    v = rng.standard_normal(200)
    idx = split_confirm(v, 32, rng)
    assert len(set(idx.tolist())) == 32
    best16 = set(np.argsort(-v)[:16].tolist())
    assert best16 <= set(idx.tolist())              # every one of the top half is kept
    assert len(set(idx.tolist()) - set(np.argsort(-v)[:32].tolist())) > 0  # and it spreads


# ---------------------------------------------------------------------------
# the recalibration
# ---------------------------------------------------------------------------


def test_recalibration_inverts_the_affine_map_when_the_expensive_tier_is_clean() -> None:
    rng = np.random.default_rng(3)
    f = rng.normal(0.68, 0.1228, size=300)
    cheap = 2.5 * f - 1.25                       # exact, no cheap noise
    paired = np.arange(40)
    r = recalibrate(cheap_paired=cheap[paired], exp_paired=f[paired],
                    cheap_all=cheap, yvar_exp=np.full(40, 1e-12), sigma_add=1e-6)
    assert np.allclose(r.pseudo, f, atol=1e-8)
    assert r.slope == pytest.approx(0.4, rel=1e-9)
    assert r.variance == pytest.approx(1e-12, abs=1e-11)


def test_pseudo_variance_is_floored_and_is_a_variance() -> None:
    rng = np.random.default_rng(4)
    f = rng.normal(0.68, 0.1228, size=200)
    cheap = f + rng.normal(0, 0.05, size=f.shape)
    exp = f + rng.normal(0, 0.05, size=f.shape)
    paired = np.arange(32)
    r = recalibrate(cheap_paired=cheap[paired], exp_paired=exp[paired],
                    cheap_all=cheap, yvar_exp=np.full(32, 0.05**2), sigma_add=0.01)
    assert r.variance >= 0.01**2                              # floored at the assay floor
    assert r.variance < 0.05                                  # a variance, not an SD


def test_the_unbiased_variance_is_reported_but_never_used() -> None:
    """The defect this guards: `resid_var - mean_yvar` goes negative at this project's
    own noise level, which pinned every pseudo-observation at the floor and told the
    model they were exact. The correction is to use `resid_var` and expose both."""
    rng = np.random.default_rng(5)
    f = rng.normal(0.68, 0.1228, size=120)
    cheap = f + rng.normal(0, 0.30, size=f.shape)             # a nearly useless readout
    exp = f + rng.normal(0, 0.17, size=f.shape)               # sigma_rel 0.25, roughly
    paired = np.arange(32)
    r = recalibrate(cheap_paired=cheap[paired], exp_paired=exp[paired],
                    cheap_all=cheap, yvar_exp=np.full(32, 0.17**2), sigma_add=0.01)
    assert r.variance == pytest.approx(max(r.resid_var, 0.01**2))
    assert r.resid_var - r.mean_yvar < r.variance             # the unbiased one is smaller
    assert r.variance > 0.01**2                               # and the floor is not hit


def test_recalibration_needs_at_least_three_paired_points() -> None:
    with pytest.raises(ValueError, match="paired"):
        recalibrate(cheap_paired=np.array([1.0, 2.0]), exp_paired=np.array([1.0, 2.0]),
                    cheap_all=np.array([1.0, 2.0, 3.0]), yvar_exp=np.array([1.0, 1.0]),
                    sigma_add=0.01)


# ---------------------------------------------------------------------------
# the tolerance the achieved-correlation guard uses
# ---------------------------------------------------------------------------


def _rho_tolerance():
    import importlib.util
    import pathlib
    spec = importlib.util.spec_from_file_location(
        "q47", pathlib.Path(__file__).resolve().parents[1]
        / "scripts" / "run_q47_multifidelity.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.rho_tolerance, m.N_CHECK


def test_the_correlation_guard_tolerates_sampling_error_and_nothing_more() -> None:
    """The first launch of the grid died on a 2.2 SD draw at rho=0.30 because the
    tolerance was flat. It must track the sample correlation's own SD, (1-rho^2)/sqrt(n)."""
    tol, n = _rho_tolerance()
    rng = np.random.default_rng(11)
    for rho in (0.30, 0.55, 0.95):
        sf = 0.1228
        f = rng.normal(0.68, sf, size=n)
        got = []
        for s in range(60):
            # 9000+ so the z stream cannot collide with the one that generated f --
            # default_rng(11) produced both on the first attempt and corr(z, f) was 1.0
            z = np.random.default_rng(9000 + s).standard_normal(n)
            tier = CheapTier(a=1.3, b=0.2, sigma_cheap=cheap_sigma(1.3, float(f.std()),
                                                                  rho), rho_target=rho)
            got.append(np.corrcoef(draw_cheap(f, tier, z=z), f)[0, 1])
        dev = np.abs(np.array(got) - rho)
        assert dev.max() < tol(rho), f"ordinary sampling error trips the guard at {rho}"
        # and a genuinely wrong sigma_cheap -- the failure mode it exists for -- is caught
        wrong = CheapTier(a=1.3, b=0.2,
                          sigma_cheap=cheap_sigma(1.3, float(f.std()), rho) * 1.5,
                          rho_target=rho)
        bad = np.corrcoef(draw_cheap(f, wrong, z=z), f)[0, 1]
        assert abs(bad - rho) > tol(rho)
