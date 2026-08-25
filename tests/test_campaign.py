"""Tests for the campaign loop.

Two tests here carry unusual weight:

  * `test_resumed_run_is_byte_identical` — the spec's "identical trace" test.
    It only passes if the random-number state is genuinely captured, which is
    the thing most likely to be quietly got wrong.
  * `test_evaluator_can_be_swapped_without_touching_the_loop` — the whole
    forward-compatibility promise, checked rather than asserted.
"""

from __future__ import annotations

import io

import torch

import pytest

from boec.campaign import Campaign, CampaignConfig, Evaluator, batch_plan
from boec.optimizers import AcqConfig
from boec.oracles import Branin
from boec.seedbook import IndexedGaussianNoise
from boec.torch_oracle import TorchEvaluator

FAST = AcqConfig(num_restarts=2, raw_samples=32, mc_samples=16)


class FormulaEvaluator:
    """Stands in for Person A's SyntheticEvaluator (stage 1)."""

    def __init__(self, peak: float = 0.35, sigma_rel: float = 0.1, seed: int = 0):
        self.peak = peak
        self.sigma_rel = sigma_rel
        self.gen = torch.Generator().manual_seed(seed)
        self.n_calls = 0

    def truth(self, X: torch.Tensor) -> torch.Tensor:
        return (-((X - self.peak) ** 2).sum(-1, keepdim=True)).exp()

    def evaluate(self, X):
        self.n_calls += 1
        y = self.truth(X)
        eps = torch.randn(y.shape, dtype=torch.double, generator=self.gen) * self.sigma_rel
        obs = y * (1 + eps) + 0.01
        return obs, (obs**2 * self.sigma_rel**2 + 1e-4).clamp_min(1e-8)


class LookupEvaluator:
    """Stands in for stage 2 — a table of published results, nothing else."""

    def __init__(self, X, Y):
        self.X, self.Y = X, Y

    def evaluate(self, Xq):
        idx = torch.cdist(Xq.double(), self.X).argmin(dim=1)
        y = self.Y[idx]
        return y, torch.full_like(y, 0.001)


class NoiselessEvaluator:
    """Returns None for noise — which this project forbids."""

    def evaluate(self, X):
        return (-((X - 0.4) ** 2).sum(-1, keepdim=True)).exp(), None


def _cfg(d=3, budget=None, **kw):
    n_init = 2 * d + 2
    return CampaignConfig(d=d, budget=budget or (n_init + 6), q=3, acq=FAST, n_holdout=8, **kw)


def _bounds(d=3):
    return torch.stack([torch.zeros(d, dtype=torch.double), torch.ones(d, dtype=torch.double)])


def _indexed_evaluator():
    return TorchEvaluator(
        Branin(),
        noise_source=IndexedGaussianNoise(31, sigma_rel=0.1, sigma_add=0.01),
    )


def _indexed_cfg():
    return CampaignConfig(
        d=2,
        budget=10,
        q=2,
        seed=7,
        acq=FAST,
        n_holdout=8,
    )


def _advance_indexed(campaign):
    X = campaign.ask(2)
    Y, Yvar = campaign.evaluator.evaluate(X)
    campaign.tell(X, Y, Yvar)


def _serialized(state):
    buffer = io.BytesIO()
    torch.save(state, buffer)
    return buffer.getvalue()


def _assert_logs_equal(left, right):
    assert len(left) == len(right)
    for a, b in zip(left, right):
        for name in a.__dataclass_fields__:
            a_value = getattr(a, name)
            b_value = getattr(b, name)
            if isinstance(a_value, torch.Tensor):
                assert torch.equal(a_value, b_value), name
            else:
                assert a_value == b_value, name


# --------------------------------------------------------------------------
# Budget arithmetic — enforced identically across methods
# --------------------------------------------------------------------------

def test_budget_plan_matches_the_spec():
    n_init, batches = batch_plan(6, 48, 4)
    assert n_init == 14 and batches == [4] * 8 + [2] and n_init + sum(batches) == 48

    n_init, batches = batch_plan(8, 48, 4)
    assert n_init == 18 and batches == [4] * 7 + [2] and n_init + sum(batches) == 48


def test_budget_too_small_raises():
    with pytest.raises(ValueError, match="cannot cover"):
        batch_plan(12, 20, 4)


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------

def test_runs_to_budget_exactly():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg()).run()
    assert c.n_observed == c.config.budget


def test_the_optimizer_never_calls_the_evaluator_itself():
    """Ask/tell separation: every measurement goes through the campaign."""
    ev = FormulaEvaluator()
    c = Campaign(ev, _bounds(), _cfg())
    c.initialize()
    assert ev.n_calls == 1
    X = c.ask(3)
    assert ev.n_calls == 1, "ask() must not measure anything"
    Y, Yvar = ev.evaluate(X)
    c.tell(X, Y, Yvar)
    assert c.n_observed == 2 * 3 + 2 + 3


def test_it_actually_optimizes():
    d = 3
    cfg = _cfg(d=d, budget=2 * d + 2 + 12)
    c = Campaign(FormulaEvaluator(sigma_rel=0.01), _bounds(d), cfg).run()
    n_init = 2 * d + 2
    assert float(c.train_Y[n_init:].max()) > float(c.train_Y[:n_init].max())


def test_best_so_far_never_decreases():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg()).run()
    b = c.best_so_far()
    assert bool(torch.all(b[1:] >= b[:-1]))


def test_all_proposals_stay_in_bounds():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg()).run()
    assert bool(torch.all(c.train_X >= 0.0)) and bool(torch.all(c.train_X <= 1.0))


def test_ask_before_initialize_raises():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    with pytest.raises(RuntimeError, match="initialize"):
        c.ask(2)


def test_double_initialize_raises():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    with pytest.raises(RuntimeError, match="already initialized"):
        c.initialize()


# --------------------------------------------------------------------------
# In-flight tracking — stage 3's normal case
# --------------------------------------------------------------------------

def test_pending_accumulates_and_clears():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    assert c.X_pending.shape[0] == 0

    first = c.ask(3)
    assert c.X_pending.shape[0] == 3

    second = c.ask(3)
    assert c.X_pending.shape[0] == 6, "two asks before a tell must both stay in flight"

    Y, V = c.evaluator.evaluate(first)
    c.tell(first, Y, V)
    assert c.X_pending.shape[0] == 3

    Y, V = c.evaluator.evaluate(second)
    c.tell(second, Y, V)
    assert c.X_pending.shape[0] == 0


def test_second_batch_avoids_the_first():
    """Without in-flight tracking this re-proposes the same region."""
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    first = c.ask(2)
    second = c.ask(2)
    assert float(torch.cdist(second, first).min()) > 1e-6


# --------------------------------------------------------------------------
# Beliefs recorded before measurement — what A's calibration work consumes
# --------------------------------------------------------------------------

def test_predictions_are_logged_before_measuring():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg()).run()
    adaptive = [g for g in c.logs if g.round_index > 0]
    assert adaptive, "no adaptive rounds were logged"
    for g in adaptive:
        assert g.mean_proposed is not None and g.var_proposed is not None
        assert g.mean_proposed.shape == g.X_proposed.shape[:1] + (1,)
        assert bool(torch.all(g.var_proposed > 0))


def test_both_point_sets_are_logged():
    """Proposed points are decision-relevant but biased; the fixed reference
    set is unbiased. The gap between them is itself a result."""
    cfg = _cfg()
    c = Campaign(FormulaEvaluator(), _bounds(), cfg).run()
    for g in [g for g in c.logs if g.round_index > 0]:
        assert g.mean_holdout is not None
        assert g.mean_holdout.shape == (cfg.n_holdout, 1)


def test_holdout_set_is_fixed_for_the_whole_run():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    before = c.holdout_X.clone()
    c.run()
    assert torch.equal(before, c.holdout_X)


def test_opening_round_logs_no_predictions():
    """Nothing is known yet, so there is nothing honest to record."""
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    assert c.logs[0].round_index == 0
    assert c.logs[0].mean_proposed is None


# --------------------------------------------------------------------------
# Saving and resuming
# --------------------------------------------------------------------------

def test_resumed_run_is_byte_identical(tmp_path):
    """**The identical-trace test.** Passes only if RNG state round-trips."""
    ev_a = FormulaEvaluator(seed=5)
    a = Campaign(ev_a, _bounds(), _cfg())
    a.initialize()
    a.ask(3)
    X = a.logs[-1].X_proposed
    Y, V = ev_a.evaluate(X)
    a.tell(X, Y, V)

    path = tmp_path / "mid.pt"
    a.save(path)

    # Continue the original.
    cont_X = a.ask(3)

    # Resume from disk and take the same step.
    b = Campaign.load(path, FormulaEvaluator(seed=5))
    resumed_X = b.ask(3)

    assert torch.allclose(cont_X, resumed_X, atol=1e-12), (
        "resumed run diverged — RNG state is not being captured"
    )


def test_state_round_trips_the_data():
    ev = FormulaEvaluator()
    a = Campaign(ev, _bounds(), _cfg()).run()
    b = Campaign.from_state_dict(a.state_dict(), ev)
    assert torch.equal(a.train_X, b.train_X)
    assert torch.equal(a.train_Y, b.train_Y)
    assert torch.equal(a.train_Yvar, b.train_Yvar)
    assert torch.equal(a.holdout_X, b.holdout_X)
    assert len(a.logs) == len(b.logs)
    assert a.config.seed == b.config.seed


def test_saved_state_contains_no_model_weights():
    """Model internals are fragile across library versions; measurements are not."""
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg()).run()
    state = c.state_dict()
    flat = " ".join(state.keys()).lower()
    for banned in ("state_dict", "covar", "likelihood", "lengthscale", "model"):
        assert banned not in flat, f"{banned!r} looks like a saved model internal"


def test_saved_state_records_library_versions():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    v = c.state_dict()["versions"]
    assert {"botorch", "torch", "numpy", "python"} <= set(v)


def test_pending_survives_a_save(tmp_path):
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    c.ask(3)
    p = tmp_path / "s.pt"
    c.save(p)
    assert Campaign.load(p, FormulaEvaluator()).X_pending.shape[0] == 3


def test_saved_state_includes_evaluator_checkpoint_when_available():
    c = Campaign(_indexed_evaluator(), _bounds(2), _indexed_cfg())
    c.initialize()
    assert c.state_dict()["evaluator_state"] == {"next_index": 6}


def test_saved_evaluator_state_requires_restoration_support():
    c = Campaign(_indexed_evaluator(), _bounds(2), _indexed_cfg())
    c.initialize()
    with pytest.raises(TypeError, match="cannot restore evaluator state"):
        Campaign.from_state_dict(c.state_dict(), FormulaEvaluator())


def test_indexed_noise_resume_matches_uninterrupted_campaign_byte_for_byte(tmp_path):
    uninterrupted = Campaign(_indexed_evaluator(), _bounds(2), _indexed_cfg())
    uninterrupted.initialize()
    _advance_indexed(uninterrupted)

    checkpoint = tmp_path / "indexed-mid.pt"
    uninterrupted.save(checkpoint)
    _advance_indexed(uninterrupted)

    resumed = Campaign.load(checkpoint, _indexed_evaluator())
    _advance_indexed(resumed)

    assert torch.equal(uninterrupted.train_X, resumed.train_X)
    assert torch.equal(uninterrupted.train_Y, resumed.train_Y)
    _assert_logs_equal(uninterrupted.logs, resumed.logs)
    assert uninterrupted.evaluator.state_dict() == resumed.evaluator.state_dict()
    assert _serialized(uninterrupted.state_dict()) == _serialized(resumed.state_dict())


# --------------------------------------------------------------------------
# The forward-compatibility promise
# --------------------------------------------------------------------------

def test_evaluator_can_be_swapped_without_touching_the_loop():
    """**The contract test.** Stage 2 replaces the formula with a lookup table.
    If this needed any change to the loop, the design was never real."""
    torch.manual_seed(0)
    table_X = torch.rand(60, 3, dtype=torch.double)
    table_Y = (-((table_X - 0.4) ** 2).sum(-1, keepdim=True)).exp()

    c = Campaign(LookupEvaluator(table_X, table_Y), _bounds(), _cfg()).run()
    assert c.n_observed == c.config.budget
    assert torch.all(torch.isfinite(c.train_Y))


def test_both_evaluators_satisfy_the_interface():
    assert isinstance(FormulaEvaluator(), Evaluator)
    assert isinstance(LookupEvaluator(torch.rand(2, 3, dtype=torch.double), torch.rand(2, 1, dtype=torch.double)), Evaluator)


def test_missing_noise_is_refused_loudly():
    """Contract item 5. Imputing here would hide the rule that did the imputing."""
    c = Campaign(NoiselessEvaluator(), _bounds(), _cfg())
    with pytest.raises(ValueError, match="no noise estimate"):
        c.initialize()


# --------------------------------------------------------------------------
# Shape contract and metric identity
# --------------------------------------------------------------------------

def test_one_dimensional_outcomes_rejected():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    X = c.ask(2)
    with pytest.raises(ValueError, match=r"\(n, m\)"):
        c.tell(X, torch.rand(2, dtype=torch.double), torch.rand(2, 1, dtype=torch.double))


def test_row_mismatch_rejected():
    c = Campaign(FormulaEvaluator(), _bounds(), _cfg())
    c.initialize()
    X = c.ask(2)
    with pytest.raises(ValueError, match="row mismatch"):
        c.tell(X, torch.rand(3, 1, dtype=torch.double), torch.rand(3, 1, dtype=torch.double))


def test_metric_identity_is_carried_and_saved():
    """Two ways of measuring the same biology give different numbers that must
    never be mixed. Recorded on the run, not left to memory."""
    cfg = _cfg(metric_name="cd31_area_over_dapi", metric_units="ratio", protocol_version="IF-v2")
    c = Campaign(FormulaEvaluator(), _bounds(), cfg)
    c.initialize()
    saved = c.state_dict()["config"]
    assert saved["metric_name"] == "cd31_area_over_dapi"
    assert saved["metric_units"] == "ratio"
    assert saved["protocol_version"] == "IF-v2"


def test_bounds_dimension_mismatch_rejected():
    with pytest.raises(ValueError, match="factors"):
        Campaign(FormulaEvaluator(), _bounds(4), _cfg(d=3))


# ---------------------------------------------------------------------------
# Opening-design size override (A, for the Q26 confound test)
#
# Q25 found that at d=6 the surrogate is statistically indistinguishable from a
# fit to permuted outcomes at the moment adaptive search begins, while at d=8 it
# is not. Three things differ between those cells and one of them is the opening
# design size, 14 against 18, because `n_init = 2d+2`. Isolating it needs d=6 run
# with an 18-point opening and NOTHING else changed.
#
# The override is defaulted, so every existing caller — and E2's pre-registered
# configuration — is untouched.
# ---------------------------------------------------------------------------

def test_batch_plan_default_is_the_pre_registered_2d_plus_2():
    assert batch_plan(6, 48, 4) == (14, [4] * 8 + [2])
    assert batch_plan(8, 48, 4) == (18, [4] * 7 + [2])


def test_batch_plan_override_changes_the_opening_and_rebalances_the_rest():
    n_init, batches = batch_plan(6, 48, 4, n_init=18)
    assert n_init == 18
    assert n_init + sum(batches) == 48          # budget is still exactly spent
    assert batches == [4] * 7 + [2]             # and matches d=8's schedule
    # the point of the test: FEWER adaptive evaluations, which is the trade-off
    assert sum(batches) == 30 < sum(batch_plan(6, 48, 4)[1])


def test_batch_plan_override_still_refuses_an_impossible_budget():
    with pytest.raises(ValueError, match="cannot cover an opening design"):
        batch_plan(6, 12, 4, n_init=18)


def test_overridden_opening_is_the_default_opening_plus_extra_points():
    """The treatment must be nested, or it is not one variable.

    `initial_design` is a Sobol design, so an 18-point draw shares its first 14
    rows with a 14-point draw at the same seed. If that ever stopped holding, the
    confound test would be comparing two different designs rather than the same
    design with four points added, and the manipulation would be confounded with
    the design itself.
    """
    d = 6
    bounds = torch.stack([torch.zeros(d, dtype=torch.double),
                          torch.ones(d, dtype=torch.double)])

    class _Flat:
        def evaluate(self, X):
            return (torch.zeros(X.shape[0], 1, dtype=torch.double),
                    torch.full((X.shape[0], 1), 1e-4, dtype=torch.double))

    a = Campaign(_Flat(), bounds, CampaignConfig(d=d, budget=48, q=4, seed=3))
    b = Campaign(_Flat(), bounds,
                 CampaignConfig(d=d, budget=48, q=4, seed=3, n_init=18))
    a.initialize()
    b.initialize()

    assert a.train_X.shape[0] == 14
    assert b.train_X.shape[0] == 18
    assert torch.equal(b.train_X[:14], a.train_X)
