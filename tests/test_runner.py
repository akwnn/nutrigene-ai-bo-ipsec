"""Tests for the grid runner."""

from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from boec.campaign import CampaignConfig
from boec.optimizers import AcqConfig, initial_design, sobol_design
from boec.runner import (
    STATIC_METHODS,
    GridCell,
    Runner,
    load_results,
    run_static_baseline,
    static_design,
)

FAST = AcqConfig(num_restarts=2, raw_samples=32, mc_samples=16)
D = 3


class Formula:
    def __init__(self, sigma_rel=0.1, seed=0):
        self.sigma_rel = sigma_rel
        self.gen = torch.Generator().manual_seed(seed)

    def truth(self, X):
        """The noiseless value. Q17 scoring needs it, so a double without one can
        no longer stand in for an evaluator in a comparison."""
        return (-((X - 0.35) ** 2).sum(-1, keepdim=True)).exp()

    def evaluate(self, X):
        y = (-((X - 0.35) ** 2).sum(-1, keepdim=True)).exp()
        eps = torch.randn(y.shape, dtype=torch.double, generator=self.gen) * self.sigma_rel
        obs = y * (1 + eps) + 0.01
        return obs, (obs**2 * self.sigma_rel**2 + 1e-4).clamp_min(1e-8)


class NoNoise:
    def evaluate(self, X):
        return torch.rand(X.shape[0], 1, dtype=torch.double), None


class NoisyKnownOptimum:
    """Noisy readings, a known true optimum, and a real `truth()`.

    The Q17 tests need all three: selection must see noise, scoring must see truth,
    and the true ceiling must be known so "the curve exceeded the optimum" is
    checkable rather than merely plausible.
    """

    optimum = 1.0

    def __init__(self, sigma=0.25, seed=0):
        self.sigma = sigma
        self.gen = torch.Generator().manual_seed(seed)

    def truth(self, X):
        return (-((X - 0.35) ** 2).sum(-1, keepdim=True) * 3.0).exp()

    def evaluate(self, X):
        f = self.truth(X)
        eps = torch.randn(f.shape, dtype=torch.double, generator=self.gen) * self.sigma
        y = f * (1 + eps)
        return y, (y**2 * self.sigma**2 + 1e-6).clamp_min(1e-8)


class Deterministic:
    """A pure function of X — same points in, same values out, no RNG anywhere.

    Needed for the Q18 pairing tests: they assert that two arms agree over the
    shared opening, which is only evidence if the evaluator actually depends on
    the points it is given.
    """

    def truth(self, X):
        return (-((X - 0.35) ** 2).sum(-1, keepdim=True)).exp()

    def evaluate(self, X):
        y = self.truth(X)
        return y, torch.full_like(y, 1e-4)


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
def test_baselines_produce_a_curve_bounded_by_the_truth(method):
    """RENAMED from ``test_baselines_produce_a_monotone_curve`` (Q17).

    It asserted the curve never decreases, which was true only because the curve
    was a running max of OBSERVED values — i.e. it encoded the winner's-curse
    inflation as a requirement. Under Q17 scoring the curve is the TRUE value at
    the running observed-argmax, and it is deliberately **not** monotone: a later
    point that drew lucky noise can displace a genuinely better incumbent, and the
    curve must be allowed to fall when it does. Forcing it upward would smuggle
    oracle-best scoring back in, which is the error that voided E2's first run.

    What can still be asserted is the thing that actually matters: the curve is a
    real value of the objective at a point the method visited."""
    o = Formula()
    curve = run_static_baseline(o, _bounds(), method, 20, seed=0)
    assert curve.shape == (20,)
    assert np.all(np.isfinite(curve))
    assert curve.max() <= float(o.truth(sobol_design(_bounds(), 4096, seed=1)).max()) + 1e-6


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


# --------------------------------------------------------------------------
# T9 / Q18 — the paired opening batch
# --------------------------------------------------------------------------

def test_sobol_pairing_is_free_and_stays_free():
    """The Sobol arm's natural 48-point design ALREADY opens on `initial_design`,
    because `initial_design` IS a Sobol design of 2d+2 at the same seed and the
    sequence prefix is stable. Guarded because it is the reason Q18's policy costs
    nothing on this arm, and a change to either function would silently end it."""
    b = _bounds()
    assert torch.allclose(sobol_design(b, 20, seed=0)[: 2 * D + 2],
                          initial_design(b, seed=0))


@pytest.mark.parametrize("method", ["sobol", "random"])
def test_paired_arms_open_on_the_identical_batch(method):
    """Q18, PRE-REGISTERED. Spec §E2: 'the initial design must be identical across
    methods for a given seed'. It was not — `run_static_baseline` never called
    `initial_design`, so random and LHS shared no opening with qLogEI at all."""
    b = _bounds()
    X = static_design(b, method, budget=20, seed=0)
    assert torch.allclose(X[: 2 * D + 2], initial_design(b, seed=0))


def test_the_shared_opening_is_not_shuffled_into_the_curve():
    """The second half of the defect. Even Sobol's free pairing was destroyed
    downstream: `run_static_baseline` permuted all `budget` points, scattering the
    shared opening through the curve. Pairing that survives design but not scoring
    is not pairing."""
    b, n_init = _bounds(), 2 * D + 2
    # A DETERMINISTIC function of X. `NoNoise` returns torch.rand ignoring its
    # input, so two arms would differ there even on identical points and the test
    # would pass without demonstrating anything.
    a = run_static_baseline(Deterministic(), b, "sobol", 20, seed=0, n_orderings=64)
    c = run_static_baseline(Deterministic(), b, "random", 20, seed=0, n_orderings=64)
    # Same opening, same order, unshuffled -> the arms' curves agree exactly over
    # the opening segment and only diverge once the methods do.
    assert np.allclose(a[:n_init], c[:n_init])


def test_averaging_still_only_shuffles_the_remainder():
    """The ordering average is what makes a one-shot design comparable to an
    adaptive one; it must survive the pairing fix rather than be traded away."""
    b = _bounds()
    one = run_static_baseline(Formula(), b, "sobol", 20, seed=1, n_orderings=1)
    many = run_static_baseline(Formula(), b, "sobol", 20, seed=1, n_orderings=200)
    n_init = 2 * D + 2
    assert np.allclose(one[:n_init], many[:n_init])      # opening is fixed
    assert not np.allclose(one[n_init:], many[n_init:])  # remainder still averaged


def test_pairing_lhs_raises_because_it_is_a_registered_exemption():
    """Q18 exempts LHS. A Latin hypercube's stratification is a property of the
    whole n-point set, so a Sobol prefix plus 34 LHS points is not a Latin
    hypercube — it is a straw man wearing the name of a baseline. Requesting it
    is requesting something unregistered, so it raises rather than quietly
    producing a hybrid under the `lhs` label."""
    with pytest.raises(ValueError, match="lhs"):
        static_design(_bounds(), "lhs", budget=20, seed=0, share_opening=True)


def test_lhs_unpaired_is_still_a_real_latin_hypercube():
    """The exemption has to actually buy something: unpaired LHS keeps one point
    per stratum per dimension, which is the entire reason to include the arm."""
    b, n = _bounds(), 20
    X = static_design(b, "lhs", budget=n, seed=0, share_opening=False)
    for j in range(D):
        strata = (X[:, j] * n).floor().long().clamp(max=n - 1)
        assert len(set(strata.tolist())) == n


# --------------------------------------------------------------------------
# Q17 — the static arms' curves were scored on OBSERVED values
# --------------------------------------------------------------------------

def test_a_static_curve_is_scored_on_truth_not_on_the_observation():
    """Q17. `run_static_baseline` accumulated observed values, so every static curve
    carried the winner's-curse inflation E1 exposed on Branin — a best-so-far that
    can exceed the true optimum. E2 routed around this function for exactly that
    reason; `Runner.run_cell` did not, so any static cell run through the grid
    produced an inflated curve under a `method-random` filename.

    The curve must never exceed the true optimum, because it is now the TRUE value
    at the point the method would report."""
    b = _bounds()
    o = NoisyKnownOptimum()
    curve = run_static_baseline(o, b, "random", 20, seed=0, n_orderings=8)
    assert curve.max() <= o.optimum + 1e-9


def test_a_static_curve_is_not_forced_monotone():
    """Reused from `diagnostics.reported_best_curve`: forcing the curve upward would
    smuggle the oracle back in. A later point that drew lucky noise can displace a
    genuinely better incumbent, and the curve must be allowed to fall when it does —
    that IS the cost of noise, and hiding it flatters every arm."""
    b = _bounds()
    curve = run_static_baseline(NoisyKnownOptimum(), b, "random", 24, seed=3,
                                n_orderings=1)
    assert np.any(np.diff(curve) < -1e-12)


class NoTruth:
    """Supplies noise estimates but no truth() — the case the Q17 guard exists for."""

    def evaluate(self, X):
        y = torch.rand(X.shape[0], 1, dtype=torch.double)
        return y, torch.full_like(y, 1e-4)


def test_scoring_a_static_arm_without_truth_raises():
    """An evaluator that cannot supply `truth()` cannot produce a comparison-grade
    curve. Returning the observed-value curve anyway is what made this defect
    survive: it looked like a result. Fail loudly instead."""
    with pytest.raises(ValueError, match="truth"):
        run_static_baseline(NoTruth(), _bounds(), "random", 20, seed=0)
