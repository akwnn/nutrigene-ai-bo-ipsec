"""Tests for the grid runner."""

from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from boec.campaign import CampaignConfig
from boec.optimizers import AcqConfig
from boec.runner import (
    STATIC_METHODS,
    GridCell,
    Runner,
    load_results,
    run_static_baseline,
)

FAST = AcqConfig(num_restarts=2, raw_samples=32, mc_samples=16)
D = 3


class Formula:
    def __init__(self, sigma_rel=0.1, seed=0):
        self.sigma_rel = sigma_rel
        self.gen = torch.Generator().manual_seed(seed)

    def evaluate(self, X):
        y = (-((X - 0.35) ** 2).sum(-1, keepdim=True)).exp()
        eps = torch.randn(y.shape, dtype=torch.double, generator=self.gen) * self.sigma_rel
        obs = y * (1 + eps) + 0.01
        return obs, (obs**2 * self.sigma_rel**2 + 1e-4).clamp_min(1e-8)


class NoNoise:
    def evaluate(self, X):
        return torch.rand(X.shape[0], 1, dtype=torch.double), None


def _bounds():
    return torch.stack([torch.zeros(D, dtype=torch.double), torch.ones(D, dtype=torch.double)])


def _cfg():
    return CampaignConfig(d=D, budget=2 * D + 2 + 6, q=3, acq=FAST, n_holdout=8)


def _cell(method="qlogei", seed=0, instance="i0"):
    return GridCell(instance_id=instance, seed=seed, method=method, dim=D, sigma_rel=0.1)


# --------------------------------------------------------------------------
# Cell identity
# --------------------------------------------------------------------------

def test_key_is_stable_and_distinguishing():
    a = _cell()
    assert a.key() == _cell().key()
    assert a.key() != _cell(seed=1).key()
    assert a.key() != _cell(method="random").key()
    assert a.key() != _cell(instance="i1").key()


def test_key_is_filename_safe():
    key = GridCell("i0", 0, "qlogei", 6, 0.25, extra={"kappa": 0.6}).key()
    assert not set(key) & set('/\\:*?"<>| ')
    assert "kappa-0.6" in key


# --------------------------------------------------------------------------
# Skip-if-exists — the feature that makes development bearable
# --------------------------------------------------------------------------

def test_reruns_are_skipped(tmp_path):
    r = Runner(tmp_path)
    cell = _cell()
    assert not r.is_done(cell)

    first = r.run_cell(cell, Formula(), _bounds(), _cfg())
    assert first is not None
    assert r.is_done(cell)

    second = r.run_cell(cell, Formula(), _bounds(), _cfg())
    assert second is None, "an already-finished cell must not be redone"


def test_overwrite_forces_a_rerun(tmp_path):
    cell = _cell()
    Runner(tmp_path).run_cell(cell, Formula(), _bounds(), _cfg())
    forced = Runner(tmp_path, overwrite=True)
    assert not forced.is_done(cell)
    assert forced.run_cell(cell, Formula(), _bounds(), _cfg()) is not None


def test_pending_lists_only_unfinished(tmp_path):
    r = Runner(tmp_path)
    cells = [_cell(seed=i) for i in range(3)]
    assert len(r.pending(cells)) == 3
    r.run_cell(cells[0], Formula(), _bounds(), _cfg())
    assert len(r.pending(cells)) == 2


def test_a_half_written_cell_is_not_counted_as_done(tmp_path):
    """The settings file is written first; the results file is the completion
    marker. So a crash between the two leaves the cell correctly unfinished."""
    r = Runner(tmp_path)
    cell = _cell()
    r.sidecar_path(cell).write_text("{}")
    assert not r.is_done(cell)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def test_result_frame_shape_and_columns(tmp_path):
    cfg = _cfg()
    frame = Runner(tmp_path).run_cell(_cell(), Formula(), _bounds(), cfg)
    assert len(frame) == cfg.budget
    for col in ("instance_id", "seed", "method", "dim", "sigma_rel",
                "evaluation", "y_observed", "y_var", "best_so_far", "wall_clock_s"):
        assert col in frame.columns
    for j in range(D):
        assert f"x_{j}" in frame.columns


def test_metric_identity_on_every_row(tmp_path):
    """Two ways of measuring the same biology give different numbers. They must
    never be mixed, so the identity travels on every row."""
    cfg = CampaignConfig(
        d=D, budget=2 * D + 2 + 3, q=3, acq=FAST, n_holdout=4,
        metric_name="cd31_area_over_dapi", metric_units="ratio", protocol_version="IF-v2",
    )
    frame = Runner(tmp_path).run_cell(_cell(), Formula(), _bounds(), cfg)
    assert (frame["metric_name"] == "cd31_area_over_dapi").all()
    assert (frame["metric_units"] == "ratio").all()
    assert (frame["protocol_version"] == "IF-v2").all()


def test_best_so_far_never_decreases(tmp_path):
    frame = Runner(tmp_path).run_cell(_cell(), Formula(), _bounds(), _cfg())
    assert np.all(np.diff(frame["best_so_far"].to_numpy()) >= -1e-12)


def test_sidecar_records_settings_and_versions(tmp_path):
    r = Runner(tmp_path)
    cell = _cell()
    r.run_cell(cell, Formula(), _bounds(), _cfg())
    payload = json.loads(r.sidecar_path(cell).read_text())
    assert payload["cell"]["method"] == "qlogei"
    assert payload["config"]["budget"] == _cfg().budget
    assert {"botorch", "torch", "numpy", "python"} <= set(payload["versions"])
    assert payload["wall_clock_s"] > 0


def test_sidecar_is_valid_json_even_with_nested_config(tmp_path):
    r = Runner(tmp_path)
    cell = _cell()
    r.run_cell(cell, Formula(), _bounds(), _cfg())
    payload = json.loads(r.sidecar_path(cell).read_text())
    assert payload["config"]["acq"]["kind"] == "qlogei"


def test_results_reload(tmp_path):
    r = Runner(tmp_path)
    for i in range(2):
        r.run_cell(_cell(seed=i), Formula(), _bounds(), _cfg())
    combined = load_results(tmp_path)
    assert len(combined) == 2 * _cfg().budget
    assert set(combined["seed"]) == {0, 1}


def test_load_empty_directory(tmp_path):
    assert load_results(tmp_path).empty


# --------------------------------------------------------------------------
# Static baselines — the fairness fix
# --------------------------------------------------------------------------

@pytest.mark.parametrize("method", ["random", "sobol", "lhs"])
def test_baselines_produce_a_monotone_curve(method):
    curve = run_static_baseline(Formula(), _bounds(), method, 20, seed=0)
    assert curve.shape == (20,)
    assert np.all(np.diff(curve) >= -1e-12)


def test_averaging_over_orderings_changes_the_answer():
    """A one-shot design has no natural running order. Without averaging, the
    curve is an artefact of whichever arbitrary order you listed the points in."""
    single = run_static_baseline(Formula(), _bounds(), "sobol", 20, seed=0, n_orderings=1)
    many = run_static_baseline(Formula(), _bounds(), "sobol", 20, seed=0, n_orderings=200)
    assert not np.allclose(single, many)
    # Both must end at the same place: the best point is the best point.
    assert single[-1] == pytest.approx(many[-1], rel=1e-9)


def test_averaged_curve_rises_more_smoothly():
    single = run_static_baseline(Formula(), _bounds(), "sobol", 30, seed=1, n_orderings=1)
    many = run_static_baseline(Formula(), _bounds(), "sobol", 30, seed=1, n_orderings=400)
    assert np.max(np.diff(many)) <= np.max(np.diff(single)) + 1e-12


def test_baseline_is_reproducible():
    a = run_static_baseline(Formula(seed=3), _bounds(), "lhs", 15, seed=2)
    b = run_static_baseline(Formula(seed=3), _bounds(), "lhs", 15, seed=2)
    np.testing.assert_allclose(a, b)


def test_unknown_baseline_rejected():
    with pytest.raises(ValueError, match="unknown baseline"):
        run_static_baseline(Formula(), _bounds(), "magic", 10, seed=0)


def test_baseline_requires_noise():
    with pytest.raises(ValueError, match="no noise estimate"):
        run_static_baseline(NoNoise(), _bounds(), "sobol", 10, seed=0)


def test_baseline_runs_through_the_runner(tmp_path):
    frame = Runner(tmp_path).run_cell(_cell(method="sobol"), Formula(), _bounds(), _cfg())
    assert len(frame) == _cfg().budget
    assert (frame["method"] == "sobol").all()


# --------------------------------------------------------------------------
# Grid
# --------------------------------------------------------------------------

def test_grid_runs_everything_then_skips_on_a_second_pass(tmp_path):
    r = Runner(tmp_path)
    cells = [_cell(method=m, seed=s) for m in ("qlogei", "sobol") for s in (0, 1)]

    first = list(r.run_grid(cells, lambda c: Formula(seed=c.seed), lambda c: _bounds(),
                            lambda c: _cfg(), verbose=False))
    assert all(frame is not None for _, frame in first)

    second = list(r.run_grid(cells, lambda c: Formula(seed=c.seed), lambda c: _bounds(),
                             lambda c: _cfg(), verbose=False))
    assert all(frame is None for _, frame in second), "second pass must skip everything"


def test_grid_results_are_distinguishable(tmp_path):
    r = Runner(tmp_path)
    cells = [_cell(method=m) for m in ("qlogei", "sobol")]
    list(r.run_grid(cells, lambda c: Formula(), lambda c: _bounds(), lambda c: _cfg(), verbose=False))
    combined = load_results(tmp_path)
    assert set(combined["method"]) == {"qlogei", "sobol"}


# --------------------------------------------------------------------------
# Method dispatch — an unrunnable arm must fail loudly, not become a BO campaign
# --------------------------------------------------------------------------

def test_the_doe_arm_refuses_to_run_instead_of_silently_running_bo(tmp_path):
    """**The trap this dispatch exists to close.**

    ``GridCell`` documents ``"doe"`` as a valid method and the DoE arm lives in
    ``boec.doe``, not here. Before the explicit branch, a ``doe`` cell fell
    through to the adaptive path, ran a **Bayesian optimization campaign**, and
    wrote a believable parquet under a ``method-doe`` filename — an E2 grid
    would have reported BO's numbers as the DoE baseline's.
    """
    r = Runner(tmp_path)
    with pytest.raises(NotImplementedError, match="not wired into the Runner"):
        r.run_cell(_cell(method="doe"), Formula(), _bounds(), _cfg())
    assert not list(tmp_path.glob("*.parquet")), "a refused cell must leave no result"


def test_an_unknown_method_raises_rather_than_defaulting_to_bo(tmp_path):
    """A typo in one arm of a grid must not be reported as that arm's result."""
    r = Runner(tmp_path)
    with pytest.raises(ValueError, match="unknown method"):
        r.run_cell(_cell(method="qlogie"), Formula(), _bounds(), _cfg())   # transposed
    assert not list(tmp_path.glob("*.parquet"))


@pytest.mark.parametrize("method", ["qlogei", "qlognei"])
def test_both_pre_registered_acquisitions_still_dispatch(tmp_path, method):
    """Q5 registered qLogEI primary and qLogNEI secondary. Both must run."""
    r = Runner(tmp_path)
    frame = r.run_cell(_cell(method=method), Formula(), _bounds(),
                       CampaignConfig(d=D, budget=2 * D + 2 + 3, q=3,
                                      acq=AcqConfig(kind=method, num_restarts=2,
                                                    raw_samples=32, mc_samples=16),
                                      n_holdout=8))
    assert frame is not None and len(frame) == 2 * D + 2 + 3


@pytest.mark.parametrize("method", list(STATIC_METHODS))
def test_every_static_method_still_dispatches(tmp_path, method):
    r = Runner(tmp_path)
    frame = r.run_cell(_cell(method=method), Formula(), _bounds(), _cfg())
    assert frame is not None and set(frame["method"]) == {method}
