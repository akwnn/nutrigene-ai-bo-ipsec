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


# =================================================================================
# B4 · FAMILY SUPPORT
#
# `replay` was Hill-only: `instance_by_id` -> `load_ensemble(dim)`, `BiphasicOracle`,
# `inst.optimum_value`. Phase 3 needs the four standard families, and the gate columns
# for them already exist and were verified live by the coverage audit at |delta| = 0.
#
# Every assertion below is against a COMMITTED column (D12). The registered kill: any
# family arm failing at anything other than |delta| = 0 stops the family programme. It is
# not repaired by widening a tolerance, and there is no tolerance constant in this block.
#
# WHICH COMMITTED COLUMN, AND WHY IT IS NOT THE OBVIOUS ONE
# ---------------------------------------------------------
# `doe` gates against `d20-rescore.json · doe_a_new`, NOT `q42-families.json · doe_a`.
# The latter is the pre-D20 column: it scored the classical arm by ORACLE-BEST while the
# BO arm on the line above it was scored by rule A. `test_family_doe_...` asserts both
# halves -- that the new column reproduces exactly, and that the old one does not -- so a
# future edit cannot silently re-point the gate at the flattering column.
# =================================================================================

import json as _json

import numpy as _np

from boec.diagnostics import reported_best_curve
from boec.replay import FAMILY_ORACLE, SPREAD_ARMS, family_evaluator, unit_bounds
from boec.runner import static_design

Q42 = Path("results/q42-families.json")
D20 = Path("results/d20-rescore.json")
Q59 = Path("results/q59-hartmann-no-screen.json")


def _keyed(path, keys=("family", "dim", "sigma", "seed")):
    doc = _json.loads(path.read_text())
    rows = doc["rows"] if isinstance(doc, dict) else doc
    return {tuple(r[k] for k in keys): r for r in rows}


def test_family_qlogei_reproduces_the_committed_q42_column_exactly():
    """The audit's live measurement, reproduced: hartmann6 d=6 sigma=0.25, seeds 0 and 1.

    `q42-families.json · bo_a` is `opt - reported_best_curve(ev.truth(X), Y)[-1]`
    (`scripts/run_q42_families.py:115`) -- the identical expression `replay.scored_curve`
    uses. Two independent code paths, so agreement at |delta| = 0 is evidence and not a
    restatement.
    """
    q42, d20 = _keyed(Q42), _keyed(D20)
    for seed in (0, 1):
        row = q42[("hartmann6", 6, 0.25, seed)]
        rec = regenerate("hartmann6", 6, 0.25, seed, "qlogei", family="hartmann6")
        assert rec.regret == row["bo_a"], (
            f"hartmann6 seed={seed}: {rec.regret!r} != committed {row['bo_a']!r}")
        # The two named gate columns are one column; assert that rather than assume it.
        assert d20[("hartmann6", 6, 0.25, seed)]["bo_a"] == row["bo_a"]


@pytest.mark.slow
def test_family_qlogei_reproduces_on_every_family_and_at_d8():
    """All four families at the primary cell, plus the d=8 `Embedded` construction path.

    d=8 hartmann6 is `Embedded(Hartmann6(), dim=8, seed=0)` -- a different oracle object
    from d=6, with inert nuisance axes. If the factory built it any other way the regret
    would miss the committed column, so this is the check on the factory, not on the GP.
    """
    q42 = _keyed(Q42)
    for family in ("ackley", "levy", "rosenbrock"):
        row = q42[(family, 6, 0.25, 0)]
        rec = regenerate(family, 6, 0.25, 0, "qlogei", family=family)
        assert rec.regret == row["bo_a"], (
            f"{family} d=6 seed=0: {rec.regret!r} != committed {row['bo_a']!r}")
    row = q42[("hartmann6", 8, 0.25, 0)]
    rec = regenerate("hartmann6", 8, 0.25, 0, "qlogei", family="hartmann6")
    assert rec.X.shape == (48, 8)
    assert rec.regret == row["bo_a"], (
        f"hartmann6 d=8 seed=0: {rec.regret!r} != committed {row['bo_a']!r}")


def test_family_doe_gates_on_d20_doe_a_new_and_not_on_q42_doe_a():
    """The right column reproduces exactly; the wrong one is shown to be wrong.

    `q42-families.json · doe_a` scored this arm by oracle-best while `bo_a` on the line
    above used rule A. `d20-rescore.json · doe_a_new` is the corrected column and is the
    gate target. Means differ by 0.012 to 0.032 per family -- larger than the SESOI.
    """
    d20, q42 = _keyed(D20), _keyed(Q42)
    disagreed = 0
    for family in FAMILY_ORACLE:
        for seed in range(5):
            rec = regenerate(family, 6, 0.25, seed, "doe", family=family)
            new = d20[(family, 6, 0.25, seed)]["doe_a_new"]
            old = q42[(family, 6, 0.25, seed)]["doe_a"]
            assert rec.regret == new, (
                f"{family} seed={seed}: {rec.regret!r} != d20 doe_a_new {new!r}")
            if old != new:
                disagreed += 1
                assert rec.regret != old, "regenerated the PRE-D20 column"
            assert rec.kept_factors is not None and len(rec.kept_factors) == 4
            assert rec.dropped_held_at is not None
    assert disagreed >= 10, (
        f"only {disagreed} of 20 rows distinguish the two columns; the test cannot tell "
        "the right gate target from the wrong one")


@pytest.mark.slow
def test_family_qlognei_reproduces_the_q59_hartmann_column():
    """`qlognei` has exactly one family gate column, and it is hartmann6-only."""
    rows = {(r["sigma"], r["seed"]): r for r in _json.loads(Q59.read_text())["rows"]}
    for seed in (0, 1):
        ref = rows[(0.25, seed)]["arms"]["qlognei"]["rule_a"]
        rec = regenerate("hartmann6", 6, 0.25, seed, "qlognei", family="hartmann6")
        assert rec.regret == ref, f"seed={seed}: {rec.regret!r} != committed {ref!r}"


def test_the_spread_arms_still_have_no_family_gate_column():
    """`lhs`/`sobol`/`random` are UNGATABLE off hill, and every table must say so.

    This asserts the absence rather than trusting it: if a family spread column is ever
    committed to one of the three gate files, this fails and the claim gets updated.
    """
    for path in (Q42, D20, Q59):
        blob = path.read_text()
        for arm in SPREAD_ARMS:
            assert f'"{arm}"' not in blob, (
                f"{path.name} now carries an {arm!r} key -- the 'ungatable off hill' "
                "claim in every family table is out of date")


def test_family_regeneration_never_consults_the_hill_ensemble():
    """`instance` is the family label off hill; a hill id passed with a family is a bug."""
    with pytest.raises(ValueError, match="instance"):
        regenerate("ce7334da318bc5e5", 6, 0.25, 0, "doe", family="levy")


def test_unknown_family_raises_rather_than_guessing():
    with pytest.raises(KeyError, match="unknown family"):
        regenerate("not_a_family", 6, 0.25, 0, "doe", family="not_a_family")


def test_family_evaluator_is_fresh_on_every_call():
    """Load-bearing, and copied from `run_q42_families.py:112` and `:125`.

    Q42 gives the campaign and the DoE arm each their OWN evaluator at the same seed, so
    both noise streams start at draw zero. A shared or cached evaluator would hand the
    second arm the continuation of the first arm's stream and every family gate would
    miss by an amount that looks like a scoring bug.
    """
    a = family_evaluator("levy", 6, 0.25, 0)
    b = family_evaluator("levy", 6, 0.25, 0)
    assert a is not b
    X = torch.rand(8, 6, dtype=torch.double)
    assert torch.equal(a.evaluate(X)[0], b.evaluate(X)[0])
    assert not torch.equal(a.evaluate(X)[0], a.evaluate(X)[0])
    assert float(a.oracle.optimum_value) == 1.0


def test_builder_supplies_the_campaign_and_replay_keeps_the_scoring():
    """The B4 hook: two-plate logic stays in its runner; `replay` keeps oracle + scoring.

    `versionb`/`versionb_random` fit a GP and call `batch_lse`. Teaching `replay` to do
    that would create `replay -> surrogate, designspace, lse` dependencies inside the one
    module every gate imports. The builder returns `(X, Y, Yvar, kept, held)` and nothing
    else; the oracle, the scoring rule and the provenance stay here.
    """
    seen = {}

    def builder(orc, dim, seed):
        seen["dim"], seen["seed"] = dim, seed
        X = static_design(unit_bounds(dim), "lhs", 48, seed)
        Y, Yvar = orc.evaluate(X)
        return X, Y, Yvar, (0, 2), {1: 0.25}

    rec = regenerate("levy", 6, 0.25, 3, "a_two_plate_arm_replay_does_not_know",
                     family="levy", builder=builder)
    assert seen == {"dim": 6, "seed": 3}
    assert rec.X.shape == (48, 6) and rec.Yvar.shape == (48, 1)
    assert rec.kept_factors == (0, 2) and rec.dropped_held_at == {1: 0.25}
    assert rec.optimum_value == 1.0
    # Scored by replay's own rule against the same oracle, not by the builder.
    orc = family_evaluator("levy", 6, 0.25, 3)
    assert rec.regret == 1.0 - float(
        reported_best_curve(orc.truth(rec.X), rec.Y)[-1])


def test_builder_works_on_hill_and_is_off_by_default():
    """The hook must not disturb the hill path, which five other modules depend on."""
    row = _primary_rows("doe")[0]

    def builder(orc, dim, seed):
        X = static_design(unit_bounds(dim), "sobol", 48, seed)
        Y, Yvar = orc.evaluate(X)
        return X, Y, Yvar, None, None

    rec = regenerate(row["instance"], 6, 0.25, row["seed"], "plate1_only",
                     builder=builder)
    assert rec.instance == row["instance"] and rec.kept_factors is None
    assert rec.optimum_value == float(instance_by_id(row["instance"], 6).optimum_value)
    assert _np.isfinite(rec.regret)
