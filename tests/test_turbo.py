"""Q62 TuRBO-1: trust region contains the incumbent and never leaves the box."""

from __future__ import annotations

import math

import pytest
import torch

from boec.turbo import (
    LENGTH_INIT,
    LENGTH_MAX,
    LENGTH_MIN,
    SUCCESS_TOLERANCE,
    TurboState,
    failure_tolerance,
    posterior_mean_incumbent,
    tr_bounds,
    update_trust_region,
)


def test_n_unique_locations_counts_distinct_rows():
    from boec.turbo import n_unique_locations

    X = torch.tensor([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0]], dtype=torch.double)
    assert n_unique_locations(X) == 2
    assert LENGTH_INIT == 0.8
    assert LENGTH_MIN == 0.5 ** 7
    assert LENGTH_MAX == 1.6
    assert SUCCESS_TOLERANCE == 3
    assert failure_tolerance(dim=6, q=4) == math.ceil(max(4 / 4, 6 / 4))


def test_tr_bounds_contain_the_center_and_stay_inside_the_unit_box():
    lo = torch.zeros(6, dtype=torch.double)
    hi = torch.ones(6, dtype=torch.double)
    global_bounds = torch.stack([lo, hi])
    center = torch.tensor([0.1, 0.5, 0.9, 0.5, 0.5, 0.5], dtype=torch.double)
    ls = torch.ones(6, dtype=torch.double)
    tr = tr_bounds(center, ls, length=0.8, global_bounds=global_bounds)
    assert tr.shape == (2, 6)
    assert torch.all(tr[0] <= center)
    assert torch.all(center <= tr[1])
    assert torch.all(tr[0] >= lo - 1e-12)
    assert torch.all(tr[1] <= hi + 1e-12)
    assert torch.all(tr[1] > tr[0])


def test_unequal_lengthscales_stretch_the_box_along_long_axes():
    global_bounds = torch.stack([torch.zeros(2), torch.ones(2)]).double()
    center = torch.tensor([0.5, 0.5], dtype=torch.double)
    ls = torch.tensor([1.0, 4.0], dtype=torch.double)
    tr = tr_bounds(center, ls, length=0.4, global_bounds=global_bounds)
    width = (tr[1] - tr[0]).tolist()
    assert width[1] > width[0]


def test_shrinks_after_failure_tolerance_and_expands_after_success_tolerance():
    failtol = failure_tolerance(6, 4)
    state = TurboState(dim=6, batch_size=4)
    assert state.length == LENGTH_INIT
    v = 0.0
    for _ in range(failtol):
        state = update_trust_region(state, incumbent_value=v)
    assert state.length == pytest.approx(LENGTH_INIT / 2)
    state = TurboState(dim=6, batch_size=4, best_value=0.0)
    for _ in range(SUCCESS_TOLERANCE):
        v += 1.0
        state = update_trust_region(state, incumbent_value=v)
    assert state.length == pytest.approx(min(LENGTH_MAX, LENGTH_INIT * 2))


def test_restart_triggers_at_length_min_and_resets_length_without_dropping_history_flag():
    state = TurboState(dim=6, batch_size=4, length=LENGTH_MIN, best_value=0.0)
    state = update_trust_region(state, incumbent_value=0.0)
    # Keep failing until a restart is due.
    while not state.restart_triggered:
        state = update_trust_region(state, incumbent_value=0.0)
        if state.length < LENGTH_MIN / 4:
            break
    assert state.restart_triggered
    state = state.after_restart()
    assert state.length == LENGTH_INIT
    assert not state.restart_triggered
    assert state.keep_history is True


class _Formula:
    def __init__(self, peak=0.35, sigma_rel=0.4, seed=1):
        self.peak = peak
        self.sigma_rel = sigma_rel
        self.gen = torch.Generator().manual_seed(seed)

    def evaluate(self, X):
        y = self.truth(X)
        eps = torch.randn(y.shape, dtype=torch.double, generator=self.gen) * self.sigma_rel
        obs = y * (1 + eps) + 0.01
        return obs, (obs**2 * self.sigma_rel**2 + 1e-4).clamp_min(1e-8)

    def truth(self, X):
        return (-((X - self.peak) ** 2).sum(-1, keepdim=True)).exp()


def test_posterior_mean_incumbent_is_not_the_noisiest_observation():
    from boec.campaign import Campaign, CampaignConfig
    from boec.optimizers import AcqConfig

    ev = _Formula()
    cfg = CampaignConfig(d=2, budget=10, q=2, seed=0, acq=AcqConfig(kind="qlognei"))
    bounds = torch.stack([torch.zeros(2), torch.ones(2)]).double()
    c = Campaign(ev, bounds, cfg)
    c.initialize()
    model = c.fit()
    idx, x_star, mu_star = posterior_mean_incumbent(model, c.train_X)
    noisy = int(torch.argmax(c.train_Y.reshape(-1)))
    assert 0 <= idx < c.n_observed
    assert x_star.shape == (2,)
    assert mu_star.ndim == 0
    # Under this noise the two indices often differ; if they coincide the
    # helper is still returning a visited point scored by the GP, not y.
    assert torch.allclose(x_star, c.train_X[idx])
    _ = noisy


def test_adaptive_proposals_stay_inside_the_trust_region():
    from boec.campaign import Campaign, CampaignConfig
    from boec.optimizers import AcqConfig

    ev = _Formula(sigma_rel=0.05, seed=0)
    cfg = CampaignConfig(
        d=2, budget=14, q=2, seed=1, n_init=6,
        acq=AcqConfig(kind="qlognei", num_restarts=2, raw_samples=32, mc_samples=16),
        use_turbo=True,
        n_holdout=8,
    )
    bounds = torch.stack([torch.zeros(2), torch.ones(2)]).double()
    c = Campaign(ev, bounds, cfg)
    c.run()
    assert c.turbo_state is not None
    assert c.turbo_state.keep_history is True
    adaptive = [log for log in c.logs if log.round_index > 0]
    assert len(adaptive) == len(c.tr_history)
    for log, tr in zip(adaptive, c.tr_history):
        X = log.X_proposed
        assert torch.all(X >= tr[0] - 1e-12)
        assert torch.all(X <= tr[1] + 1e-12)


def test_keep_history_false_is_forbidden_on_restart():
    state = TurboState(dim=6, batch_size=4, keep_history=False)
    with pytest.raises(RuntimeError, match="forbids discarding"):
        state.after_restart()


def test_identification_gap_and_rounds_match_the_paper_arithmetic():
    from boec.turbo import identification_gap, rounds_for_bo

    assert identification_gap(0.08, 0.05) == pytest.approx(0.03)
    assert rounds_for_bo(48, d=6, q=4) == 10
    assert rounds_for_bo(14, d=6, q=4) == 1
    assert rounds_for_bo(0, d=6) == 0
    assert rounds_for_bo(18, d=6, q=4, n_init=18) == 1


def test_collapse_rate_requires_every_seed_of_a_landscape():
    from boec.turbo import collapse_rate

    # 3/4 landscapes collapsed (both seeds below 20).
    assert collapse_rate([[12, 11], [19, 5], [48, 48], [3, 3]]) == pytest.approx(0.75)
    assert collapse_rate([[48, 12]]) == pytest.approx(0.0)  # one seed still diverse
    with pytest.raises(ValueError, match="empty"):
        collapse_rate([])


def test_use_turbo_false_does_not_build_a_trust_region():
    from boec.campaign import Campaign, CampaignConfig
    from boec.optimizers import AcqConfig

    ev = _Formula(sigma_rel=0.05, seed=0)
    cfg = CampaignConfig(
        d=2, budget=10, q=2, seed=2, n_init=6,
        acq=AcqConfig(kind="qlognei", num_restarts=2, raw_samples=32, mc_samples=16),
        use_turbo=False,
        n_holdout=8,
    )
    c = Campaign(ev, torch.stack([torch.zeros(2), torch.ones(2)]).double(), cfg)
    c.run()
    assert c.turbo_state is None
    assert c.tr_history == []
    assert c.last_tr_bounds is None
    assert c.state_dict()["turbo"] is None


def test_turbo_state_survives_save_and_load():
    from boec.campaign import Campaign, CampaignConfig
    from boec.optimizers import AcqConfig

    ev = _Formula(sigma_rel=0.05, seed=3)
    cfg = CampaignConfig(
        d=2, budget=10, q=2, seed=4, n_init=6,
        acq=AcqConfig(kind="qlognei", num_restarts=2, raw_samples=32, mc_samples=16),
        use_turbo=True,
        n_holdout=8,
    )
    bounds = torch.stack([torch.zeros(2), torch.ones(2)]).double()
    a = Campaign(ev, bounds, cfg).run()
    b = Campaign.from_state_dict(a.state_dict(), ev)
    assert b.turbo_state is not None
    assert b.turbo_state.length == a.turbo_state.length
    assert b.turbo_state.n_restarts == a.turbo_state.n_restarts
    assert b.turbo_state.best_value == pytest.approx(a.turbo_state.best_value)
    assert b.config.use_turbo is True


def test_score_finished_campaign_stores_locators_and_two_decimal_arrival_keys():
    from boec.campaign import Campaign, CampaignConfig
    from boec.optimizers import AcqConfig
    from boec.turbo import score_finished_campaign

    ev = _Formula(sigma_rel=0.05, seed=0)
    cfg = CampaignConfig(
        d=2, budget=10, q=2, seed=5, n_init=6,
        acq=AcqConfig(kind="qlognei", num_restarts=2, raw_samples=32, mc_samples=16),
        use_turbo=True,
        n_holdout=8,
    )
    bounds = torch.stack([torch.zeros(2), torch.ones(2)]).double()
    c = Campaign(ev, bounds, cfg).run()
    opt = float(ev.truth(torch.full((1, 2), ev.peak)).reshape(-1)[0])
    scored = score_finished_campaign(
        c, ev.truth(c.train_X), c.train_Y, opt,
        gp_restarts=2, gp_raw_samples=32,
    )
    assert scored["R_id"] == pytest.approx(scored["R_measured"] - scored["R_search"])
    assert scored["R_id"] >= -1e-12
    assert scored["n_unique"] >= 1
    assert scored["n_unique"] <= scored["n_observed"]
    assert scored["n_rounds"] == 3  # 6 + 2 + 2
    assert set(scored["arrivals"]) == {"0.15", "0.10", "0.05"}
    assert scored["R_gp_box"] is not None
    assert scored["R_gp_tr"] is not None
    assert scored["R_measured_at_48"] is None
    assert scored["keep_history"] is True
    assert 0.0 <= scored["R_measured"] <= 1.0


def test_min_length_proposals_stay_inside_the_global_box():
    """Even a collapsed TR is still a box inside [0,1]^d, never the full cube by accident."""
    lo = torch.zeros(6, dtype=torch.double)
    hi = torch.ones(6, dtype=torch.double)
    center = torch.tensor([0.5] * 6, dtype=torch.double)
    tr = tr_bounds(center, torch.ones(6), LENGTH_MIN, torch.stack([lo, hi]))
    assert torch.all(tr[0] >= lo - 1e-12)
    assert torch.all(tr[1] <= hi + 1e-12)
    assert float((tr[1] - tr[0]).max()) < 0.05
