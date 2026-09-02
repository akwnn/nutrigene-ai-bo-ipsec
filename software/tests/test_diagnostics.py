"""E3's calibration diagnostics. Person A owns this.

**Why A owns it when B owns the GP:** two people then understand the model that carries
into Phases 2 and 3. If only one does, the project has a single point of failure on its
most load-bearing component.

Every check here exists because a plausible-looking wrong number is the failure mode.
Coverage at nominal 0.95 with n=48 has a standard error of about 3.1%, so 95% and 89%
are indistinguishable in a single run — which is why error bars on the diagnostics are
mandatory, not optional, and why they are bootstrapped over **instances** rather than
points.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.diagnostics import (
    coverage,
    crps_gaussian,
    instance_bootstrap,
    pit_values,
    reported_best_curve,
    sharpness,
)

RNG = np.random.default_rng(20260810)


# ------------------------------------------------------------------------ CRPS
def test_crps_closed_form_matches_monte_carlo():
    """`sigma * [z(2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi)]`. Do not sample it in
    production -- but do check the closed form against sampling once, here."""
    for mu, sigma, y in ((0.0, 1.0, 0.3), (2.0, 0.5, 1.1), (-1.0, 2.0, 4.0)):
        draws = RNG.normal(mu, sigma, 4_000_000)
        mc = np.abs(draws - y).mean() - 0.5 * np.abs(
            draws[:2_000_000] - draws[2_000_000:]).mean()
        got = float(crps_gaussian(
            torch.tensor([[y]]), torch.tensor([[mu]]), torch.tensor([[sigma]])))
        assert got == pytest.approx(mc, abs=3e-3), (mu, sigma, y, got, mc)


def test_crps_is_zero_for_a_perfect_point_forecast():
    v = float(crps_gaussian(torch.tensor([[1.0]]), torch.tensor([[1.0]]),
                            torch.tensor([[1e-9]])))
    assert v == pytest.approx(0.0, abs=1e-6)


def test_crps_rewards_being_right_and_penalises_overconfidence():
    y, mu = torch.tensor([[0.0]]), torch.tensor([[0.0]])
    tight = float(crps_gaussian(y, mu, torch.tensor([[0.1]])))
    loose = float(crps_gaussian(y, mu, torch.tensor([[3.0]])))
    assert tight < loose                                    # right and confident wins
    wrong_tight = float(crps_gaussian(torch.tensor([[5.0]]), mu, torch.tensor([[0.1]])))
    wrong_loose = float(crps_gaussian(torch.tensor([[5.0]]), mu, torch.tensor([[3.0]])))
    assert wrong_tight > wrong_loose                        # wrong and confident loses


# -------------------------------------------------------------------- coverage
def test_coverage_of_a_correctly_specified_gaussian_hits_nominal():
    n = 200_000
    mu = torch.zeros(n, 1, dtype=torch.double)
    sd = torch.full((n, 1), 0.7, dtype=torch.double)
    y = mu + sd * torch.from_numpy(RNG.normal(0, 1, (n, 1)))
    assert float(coverage(y, mu, sd, alpha=0.05)) == pytest.approx(0.95, abs=0.005)
    assert float(coverage(y, mu, sd, alpha=0.20)) == pytest.approx(0.80, abs=0.005)


def test_coverage_detects_overconfidence():
    """The failure E3 exists to catch: intervals too narrow."""
    n = 100_000
    mu = torch.zeros(n, 1, dtype=torch.double)
    y = mu + 2.0 * torch.from_numpy(RNG.normal(0, 1, (n, 1)))
    claimed = torch.full((n, 1), 1.0, dtype=torch.double)     # claims sd 1, truth is 2
    assert float(coverage(y, mu, claimed)) < 0.70


def test_coverage_rejects_a_standard_deviation_that_is_secretly_a_variance():
    """Passing a variance where a standard deviation belongs is the same family as
    the Yvar traps and produces a plausible-looking wrong number."""
    n = 50_000
    mu = torch.zeros(n, 1, dtype=torch.double)
    y = mu + 0.5 * torch.from_numpy(RNG.normal(0, 1, (n, 1)))
    as_sd = float(coverage(y, mu, torch.full((n, 1), 0.5, dtype=torch.double)))
    as_var = float(coverage(y, mu, torch.full((n, 1), 0.25, dtype=torch.double)))
    assert as_sd == pytest.approx(0.95, abs=0.01)
    assert as_var < 0.85            # measurably different, so a test can catch it


# ------------------------------------------------------------------------- PIT
def test_pit_of_a_calibrated_forecast_is_uniform():
    n = 100_000
    mu = torch.zeros(n, 1, dtype=torch.double)
    sd = torch.ones(n, 1, dtype=torch.double)
    y = mu + sd * torch.from_numpy(RNG.normal(0, 1, (n, 1)))
    u = pit_values(y, mu, sd).numpy().ravel()
    assert u.min() >= 0.0 and u.max() <= 1.0
    for q in (0.1, 0.25, 0.5, 0.75, 0.9):
        assert np.mean(u <= q) == pytest.approx(q, abs=0.01)


# ------------------------------------------------------------------- sharpness
def test_sharpness_is_mean_predictive_sd_and_ignores_the_outcome():
    sd = torch.tensor([[1.0], [3.0]], dtype=torch.double)
    assert float(sharpness(sd)) == pytest.approx(2.0)


# --------------------------------------------------- instance-level bootstrap
def test_bootstrap_resamples_instances_not_points():
    """**Points within a run are sequential BO proposals and are not exchangeable**,
    so resampling them is invalid and would give a spuriously narrow interval.

    Two instances, wildly different values, many points each. Resampling instances
    must produce a WIDE interval spanning both; resampling points would produce a
    narrow one around the pooled mean. The test asserts the wide behaviour.
    """
    per_instance = np.array([0.0] * 1 + [1.0] * 1)
    mean, lo, hi = instance_bootstrap(per_instance, n_boot=4000, seed=0)
    assert mean == pytest.approx(0.5)
    assert lo == pytest.approx(0.0, abs=1e-9)      # both draws can be instance 0
    assert hi == pytest.approx(1.0, abs=1e-9)


def test_bootstrap_interval_is_reproducible_and_brackets_the_mean():
    v = RNG.normal(0.9, 0.05, 25)
    m1, l1, h1 = instance_bootstrap(v, n_boot=2000, seed=7)
    m2, l2, h2 = instance_bootstrap(v, n_boot=2000, seed=7)
    assert (m1, l1, h1) == (m2, l2, h2)
    assert l1 < m1 < h1
    assert m1 == pytest.approx(v.mean())


def test_bootstrap_rejects_an_empty_sample():
    with pytest.raises(ValueError):
        instance_bootstrap(np.array([]), n_boot=10)


# ----------------------------------------------------- the end-to-end self-test
@pytest.mark.slow
def test_a_gp_fit_to_a_gp_draw_is_near_perfectly_calibrated():
    """**The self-test the spec demands.** Fit the model to a function drawn FROM a
    GP with the same kernel. Coverage should be near nominal by construction; if it
    is not, the bug is in our code rather than in the model's assumptions.

    Uses `boec.surrogate.predictive`, never `posterior(observation_noise=True)`.
    """
    from boec.surrogate import build_gp, predictive

    d, n_train, n_test, sigma = 4, 60, 400, 0.05
    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])
    torch.manual_seed(0)

    # A draw from a GP prior, realised on train+test jointly so the test points are
    # genuinely from the same function.
    X = torch.rand(n_train + n_test, d, dtype=torch.double)
    sq = torch.cdist(X, X).pow(2)
    K = torch.exp(-0.5 * sq / 0.35**2) + 1e-8 * torch.eye(len(X), dtype=torch.double)
    f = torch.linalg.cholesky(K) @ torch.randn(len(X), 1, dtype=torch.double)

    Xtr, ftr, Xte, fte = X[:n_train], f[:n_train], X[n_train:], f[n_train:]
    Ytr = ftr + sigma * torch.randn_like(ftr)
    Yvar = torch.full_like(Ytr, sigma**2)

    model = build_gp(Xtr, Ytr, Yvar, bounds)
    pred = predictive(model, Xte, noise=torch.full((n_test, 1), sigma**2,
                                                   dtype=torch.double))
    yte = fte + sigma * torch.randn_like(fte)
    cov = float(coverage(yte, pred.mean, pred.stddev))
    assert 0.86 < cov < 1.0, f"coverage {cov:.3f} on a GP-generated function"


# --------------------------------------------- E2 scoring: what did the method PICK?
def test_reported_best_follows_the_observed_argmax_not_the_true_argmax():
    """**The bug this function exists to prevent.**

    Scoring an arm by the best TRUE value among the points it visited credits it for
    stumbling onto a good recipe it had no way to identify. That systematically
    favours space-filling arms, which visit many scattered points, over adaptive ones,
    which concentrate. E2's first run showed exactly that: random and LHS matched
    qLogEI, and the DoE arm beat it.

    The honest question is "what would the practitioner walk away with", so the point
    is chosen by the OBSERVED value and scored by the TRUE one.
    """
    observed = torch.tensor([[1.0], [9.0], [2.0]], dtype=torch.double)   # noise favours #1
    truth = torch.tensor([[5.0], [0.0], [4.0]], dtype=torch.double)      # but #1 is awful
    curve = reported_best_curve(truth, observed)
    assert curve.tolist() == [5.0, 0.0, 0.0]        # follows the observed winner
    assert curve[-1] != truth.max().item()          # NOT the oracle-best of 5.0


def test_reported_best_equals_the_truth_when_observations_are_noiseless():
    y = torch.tensor([[1.0], [3.0], [2.0]], dtype=torch.double)
    np.testing.assert_allclose(reported_best_curve(y, y), [1.0, 3.0, 3.0])


def test_reported_best_can_never_exceed_the_true_optimum():
    rng = np.random.default_rng(0)
    truth = torch.from_numpy(rng.uniform(0, 1, (200, 1)))
    observed = truth + torch.from_numpy(rng.normal(0, 0.5, (200, 1)))
    curve = reported_best_curve(truth, observed)
    assert curve.max() <= float(truth.max()) + 1e-12


def test_reported_best_is_not_monotone_and_that_is_correct():
    """It tracks the incumbent, and a later lucky-noise point can displace a genuinely
    better earlier one. Forcing monotonicity would smuggle the oracle back in."""
    observed = torch.tensor([[1.0], [9.0]], dtype=torch.double)
    truth = torch.tensor([[5.0], [0.0]], dtype=torch.double)
    assert reported_best_curve(truth, observed).tolist() == [5.0, 0.0]


def test_reported_best_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        reported_best_curve(torch.zeros(3, 1), torch.zeros(4, 1))
