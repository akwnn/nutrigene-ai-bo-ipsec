"""Regeneration must reproduce the committed column, not merely agree with itself.

D12: a gate comparing one fresh run to another can only report that the code agrees with
itself. Every assertion here compares against `results/e2-grid.json` as committed.
"""

from pathlib import Path

import pytest
import torch

from boec.replay import CampaignRecord, committed_rows, instance_by_id, regenerate

GRID = Path("results/e2-grid.json")


def _primary_rows(arm, n=3):
    rows = [r for r in committed_rows(GRID)
            if r["dim"] == 6 and r["sigma"] == 0.25 and r["arm"] == arm]
    assert rows, f"no committed rows for arm={arm}"
    return rows[:n]


def test_regenerate_returns_observations_of_the_right_shape():
    row = _primary_rows("doe")[0]
    rec = regenerate(row["instance"], row["dim"], row["sigma"], row["seed"], row["arm"])
    assert isinstance(rec, CampaignRecord)
    assert rec.X.shape == (48, 6)
    assert rec.Y.shape == (48, 1)
    assert rec.Yvar.shape == (48, 1)


def test_doe_arm_reproduces_committed_regret_exactly():
    """The DoE arm has no acquisition optimiser, so exact equality is the right bar."""
    for row in _primary_rows("doe"):
        rec = regenerate(row["instance"], row["dim"], row["sigma"],
                         row["seed"], row["arm"])
        assert rec.regret == row["regret"], (
            f"{row['instance']} seed={row['seed']}: "
            f"regenerated {rec.regret!r} != committed {row['regret']!r}"
        )


def test_unknown_arm_raises_rather_than_guessing():
    with pytest.raises(ValueError, match="unknown arm"):
        regenerate("ce7334da318bc5e5", 6, 0.25, 0, "not_an_arm")


def test_unknown_instance_raises():
    with pytest.raises(KeyError):
        instance_by_id("definitely_not_an_instance", 6)


def test_regenerate_yvar_is_coupled_to_the_reading_not_the_truth():
    """Documents the defect K1 tests. If this ever fails, the oracle changed.

    `_plug_in_yvar` is computed from the noisy reading y, not from f, so a well whose
    noise draw came out low is handed a LOW variance and the GP trusts it more. Assumed
    precision is correlated with the residual.
    """
    from boec.torch_oracle import BiphasicOracle

    inst = instance_by_id("ce7334da318bc5e5", 6)
    orc = BiphasicOracle(inst, sigma_rel=0.25, seed=0)
    X = torch.rand(64, 6, dtype=torch.double)
    Y, Yvar = orc.evaluate(X)
    r = torch.corrcoef(torch.stack([Y.abs().reshape(-1), Yvar.reshape(-1)]))[0, 1]
    assert float(r) > 0.9, f"expected Yvar coupled to |Y|, got corr={float(r):.3f}"


def test_doe_arm_reports_which_factors_its_stage_two_varied():
    """Amendment B3 needs this, and it is NOT derivable from X.

    The screen varies all d factors across its 20 runs, so every column of X_visited has
    nonzero variance even for factors the CCD pinned. A variance test on X would find
    nothing and silently certify a factor the response-surface fit never saw move.
    """
    row = _primary_rows("doe")[0]
    rec = regenerate(row["instance"], row["dim"], row["sigma"], row["seed"], row["arm"])
    assert rec.kept_factors is not None
    assert len(rec.kept_factors) == 4, "the published screen keeps 4 of 6"
    assert set(rec.kept_factors) <= set(range(6))
    # Every axis still varies in X, which is exactly why kept_factors must be recorded.
    assert bool((rec.X.std(dim=0) > 1e-9).all())


def test_adaptive_arms_report_no_screen():
    row = _primary_rows("qlogei")[0]
    rec = regenerate(row["instance"], row["dim"], row["sigma"], row["seed"], row["arm"])
    assert rec.kept_factors is None


def test_one_shot_spread_arm_reproduces_committed_regret_exactly():
    """The comparator SPADE is actually about: one-shot LHS, 48 points, one round.

    The first K6 run used `doe` as the classical arm, which is NOT a spread design --
    it is a screen plus a CCD confined to a sub-box with two axes pinned. Without this
    arm the registered K6 question is unanswered.

    The committed curve averages 20 random orderings, but the FINAL value is
    order-invariant (it is the true value at the argmax of all observed Y), so a single
    regeneration must match.
    """
    for arm in ("lhs", "sobol"):
        rows = [r for r in committed_rows(GRID)
                if r["dim"] == 6 and r["sigma"] == 0.25 and r["arm"] == arm][:3]
        assert rows, f"no committed rows for arm={arm}"
        for row in rows:
            rec = regenerate(row["instance"], 6, 0.25, row["seed"], arm)
            assert rec.X.shape == (48, 6)
            assert rec.kept_factors is None, "a spread arm screens nothing"
            # EXACT, not a tolerance. `static_curve` averages 20 identical curves and
            # the float64 mean of 20 copies of x is not bitwise x (measured up to 5.6e-17),
            # so `replay` reproduces that arithmetic rather than inventing a tolerance.
            assert rec.regret == row["regret"], (
                f"{arm} {row['instance']} seed={row['seed']}: "
                f"{rec.regret!r} != {row['regret']!r}")
