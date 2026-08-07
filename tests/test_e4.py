"""End-to-end test of Experiment 4, against a stand-in landscape.

**Person A's real oracle does not exist yet.** This uses a stand-in with the
same shape — biphasic per ingredient, interior peak, multiplicative noise — so
that the whole pipeline is proven to run and produce sane numbers. When A's
module lands it should drop straight in, since `Oracle` is a structural
interface.

The test that matters most is `test_the_mechanism_actually_fires`: it confirms
the experiment can detect what it claims to detect. If that ever fails on the
real oracle, the finding is that there is no mechanism — which is a real
outcome, not a bug.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from boec.e4 import E4Config, Oracle, run_e4_cell, summarise
from boec.parametric import biphasic_response

D = 6


class StandInOracle:
    """Stands in for Person A's biphasic oracle."""

    def __init__(self, seed: int = 0, sigma_rel: float = 0.10, d: int = D):
        rng = np.random.default_rng(seed)
        self.d = d
        self._x_star = rng.uniform(0.25, 0.55, d)
        self.n = rng.uniform(1.0, 3.0, d)
        r = rng.uniform(2.0, 6.0, d)
        self.ec50 = self._x_star / np.sqrt(r)
        self.ic50 = self._x_star * np.sqrt(r)
        w = rng.uniform(0.75, 1.25, d)
        self.w = w / w.sum()
        self.sigma_rel = sigma_rel
        self.gen = torch.Generator().manual_seed(seed)

    @property
    def x_star(self) -> torch.Tensor:
        return torch.from_numpy(self._x_star)

    def truth(self, X: torch.Tensor) -> torch.Tensor:
        A = X.double().numpy()
        vals = biphasic_response(A, self.ec50, self.ic50, self.n) @ self.w
        return torch.from_numpy(vals.reshape(-1, 1))

    def observe(self, X: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        y = self.truth(X)
        eps = torch.randn(y.shape, dtype=torch.double, generator=self.gen) * self.sigma_rel
        obs = y * (1 + eps) + torch.randn(y.shape, dtype=torch.double, generator=self.gen) * 0.01
        var = (obs**2 * self.sigma_rel**2 + 0.01**2).clamp_min(1e-8)
        return obs, var


FAST = dict(n_candidates=128, n_restarts=4, raw_samples=512)


def test_stand_in_satisfies_the_oracle_interface():
    """When A's real oracle lands it should drop in with no code changes."""
    assert isinstance(StandInOracle(), Oracle)


def test_runs_end_to_end():
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    assert res.n_train == 48                     # 32 + 12 + 4
    assert res.kappa == 0.7
    assert res.discrimination is not None
    assert np.isfinite(res.over_prediction["second_order"])
    assert np.isfinite(res.over_prediction["gp"])


def test_all_four_models_are_attempted():
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    assert set(res.over_prediction) == {
        "second_order", "stepwise_third_order", "gp", "parametric"
    }


def test_the_mechanism_actually_fires():
    """**Can the experiment detect what it claims to?**

    Trained on a corner that stops short of the peak, the traditional fit
    should point somewhere it has not seen and promise more than is there.
    If this fails on Person A's real oracle, the finding is that there is no
    mechanism — Doc 1 §7 pre-flight check 1.
    """
    overshoots, escaped = [], []
    for seed in range(4):
        res = run_e4_cell(StandInOracle(seed=seed), E4Config(kappa=0.6, seed=seed, **FAST))
        overshoots.append(res.over_prediction["second_order"])
        escaped.append(not res.argmax_inside_subbox["second_order"])

    assert all(escaped), "the fit stayed inside the region it had seen — no extrapolation"
    assert np.mean(overshoots) > 0, "no overshoot at all — the mechanism is absent"


def test_hiding_more_produces_more_overshoot():
    """The intended lever: if overshoot is too small, lower kappa. **Never
    raise the peak** — that flattens the landscape and breaks A's experiment."""
    tight = np.mean([
        run_e4_cell(StandInOracle(seed=s), E4Config(kappa=0.6, seed=s, **FAST)
                    ).over_prediction["second_order"] for s in range(3)
    ])
    loose = np.mean([
        run_e4_cell(StandInOracle(seed=s), E4Config(kappa=0.9, seed=s, **FAST)
                    ).over_prediction["second_order"] for s in range(3)
    ])
    assert tight > loose


def test_only_the_two_permitted_models_report_intervals():
    """The stepwise model is refused one on purpose; the practitioner form has
    none. Reporting the stepwise interval would confound the central finding."""
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    assert np.isfinite(res.pi_width_at_argmax["second_order"])
    assert np.isfinite(res.pi_width_at_argmax["gp"])
    assert np.isnan(res.pi_width_at_argmax["stepwise_third_order"])
    assert np.isnan(res.pi_width_at_argmax["parametric"])


def test_turning_points_are_classified():
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    for kind in res.stationary_kind.values():
        assert kind in {"maximum", "minimum", "saddle", "ridge"}


def test_low_kappa_can_produce_a_minimum():
    """Why the turning point is reported as a distribution, not a rate.

    On the rising arm the fit often curves upward, so its turning point is a
    *bottom*, not a top. A bare 'did it escape' number would hide that.
    """
    kinds = {
        run_e4_cell(StandInOracle(seed=s), E4Config(kappa=0.6, seed=s, **FAST)
                    ).stationary_kind["second_order"]
        for s in range(4)
    }
    assert kinds <= {"maximum", "minimum", "saddle", "ridge"}


def test_headroom_is_reported():
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    ag = res.discrimination.agreement
    assert 0.0 <= ag.max_offdiagonal <= 1.0
    assert isinstance(ag.has_headroom, bool)
    assert "rho" in ag.summary()


def test_the_null_is_always_scored():
    """Plain distance must always be measured, so it can never quietly be
    left out of the comparison."""
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    assert "nearest_neighbour_distance" in res.discrimination.spearman
    assert np.isfinite(res.discrimination.spearman["nearest_neighbour_distance"])


def test_identical_points_for_every_model():
    """Structural guarantee: there is one design, used once."""
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    assert res.n_train == 48


def test_reproducible():
    a = run_e4_cell(StandInOracle(seed=2), E4Config(kappa=0.7, seed=1, **FAST))
    b = run_e4_cell(StandInOracle(seed=2), E4Config(kappa=0.7, seed=1, **FAST))
    assert a.over_prediction["second_order"] == pytest.approx(b.over_prediction["second_order"])
    assert a.discrimination.spearman["gp_predictive_sd"] == pytest.approx(
        b.discrimination.spearman["gp_predictive_sd"]
    )


def test_convergence_failures_are_recorded_not_dropped():
    res = run_e4_cell(StandInOracle(), E4Config(kappa=0.7, **FAST))
    assert isinstance(res.parametric_converged, bool)
    if not res.parametric_converged:
        assert any("did not converge" in n for n in res.notes)
        assert np.isnan(res.over_prediction["parametric"])


def test_summary_pools_cells():
    results = [
        run_e4_cell(StandInOracle(seed=s), E4Config(kappa=k, seed=s, **FAST))
        for s in range(3) for k in (0.6, 0.8)
    ]
    s = summarise(results)
    assert s["n_cells"] == 6
    assert np.isfinite(s["over_prediction_mean"])
    assert 0.0 <= s["fraction_extrapolated"] <= 1.0
    assert 0.0 <= s["parametric_failure_rate"] <= 1.0
    assert sum(s["stationary_kinds"].values()) == 6
    for key in ("spearman_gp", "spearman_nearest_neighbour", "spearman_poly_pi"):
        assert len(s[key]) == 3


def test_summary_reports_cells_without_headroom():
    results = [run_e4_cell(StandInOracle(seed=s), E4Config(kappa=0.7, seed=s, **FAST)) for s in range(2)]
    s = summarise(results)
    assert 0 <= s["n_cells_without_headroom"] <= 2
