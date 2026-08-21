"""P3 — the three missing (d, sigma_rel) cells, and the gate that must not be skippable.

Registered in ``docs/OPEN-QUESTIONS.md`` (commit 5c44e6a) under "PHASES 2-4
PRE-REGISTRATION", section P3, before ``scripts/run_p3_cells.py`` existed.

------------------------------------------------------------------------------
WHY THE GATE TESTS COME FIRST
------------------------------------------------------------------------------

``scripts/run_k6_designspace.py:180-181`` is

    ref = committed.get((inst_id, seed, arm))
    if ref is not None:
        ...

which skipped the gate for 100 campaigns without saying so (COVERAGE-MATRIX §3.6).
At d=8 the same two lines would skip `doe` as well, because `results/e2-grid.json`
carries **no `doe` column at d=8** -- verified here, not assumed -- and the d=8 column
lives in `results/e2-doe-d8.json`. A silent skip there is a registered STOP CONDITION,
so the routing and the missing-target behaviour are tested before any campaign runs.

------------------------------------------------------------------------------
WHY THE SCORER IS TESTED AGAINST COMMITTED ROWS, NOT AGAINST ITSELF
------------------------------------------------------------------------------

P3 scores K6 and K6b from **one** regeneration per campaign rather than two, which is
what the registered 4.1 CPU-h budget assumes. That means the K6b scoring block cannot be
run out of ``scripts/run_k6b_conservative.py``'s ``main()`` and is re-expressed in the P3
runner. A re-expression is a place for a silent divergence, so it is pinned to the
**committed** ``results/k6b-conservative.json`` rows at the primary cell (D12: gate
against a committed column, never against a regeneration of itself).
"""

import json
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_p3_cells import (ARMS, KERNEL_ARMS, MissingGateTarget, build_gate_index,
                          check_gate, gate_target, score_k6b)  # noqa: E402

from boec.norms import sobol_grid  # noqa: E402
from boec.replay import regenerate  # noqa: E402
from boec.torch_oracle import BiphasicOracle  # noqa: E402
from boec.replay import instance_by_id  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --- the routing, which is the whole of §3.6 ------------------------------------------

def test_e2_grid_really_has_no_doe_column_at_d8():
    """The premise of the routing, measured rather than taken from the audit."""
    rows = json.loads((ROOT / "results/e2-grid.json").read_text())
    assert not [r for r in rows if r["dim"] == 8 and r["arm"] == "doe"]
    assert len([r for r in rows if r["dim"] == 6 and r["arm"] == "doe"]) == 100


def test_doe_at_d8_routes_to_the_doe_d8_file_and_at_d6_to_the_grid():
    assert gate_target("doe", 8) == ROOT / "results/e2-doe-d8.json"
    assert gate_target("doe", 6) == ROOT / "results/e2-grid.json"


@pytest.mark.parametrize("arm", ["qlogei", "qlognei", "lhs", "sobol", "random"])
@pytest.mark.parametrize("dim", [6, 8])
def test_the_seven_gatable_arms_route_to_e2_grid(arm, dim):
    assert gate_target(arm, dim) == ROOT / "results/e2-grid.json"


def test_kernel_arms_route_to_q30_which_may_not_exist_yet():
    """`results/q30-additive.json` is P1's output. Absent, these arms are CANNOT GATE."""
    for arm in KERNEL_ARMS:
        assert gate_target(arm, 6) == ROOT / "results/q30-additive.json"


# --- a missing target is an error, never a skip ---------------------------------------

def test_build_gate_index_raises_when_a_gatable_arm_has_no_committed_rows():
    """The §3.6 defect, inverted into a hard failure.

    d=8 sigma=0.25 has no `doe` rows in `e2-grid.json`; asking for the index with the
    WRONG target must raise rather than hand back a dict that quietly lacks the key.
    """
    with pytest.raises(MissingGateTarget):
        build_gate_index(dim=8, sigma=0.25, arms=("doe",),
                         targets={"doe": ROOT / "results/e2-grid.json"})


def test_build_gate_index_finds_doe_at_d8_in_the_right_file():
    idx = build_gate_index(dim=8, sigma=0.25, arms=("doe",))
    assert len({k[0:2] for k in idx}) == 50
    assert all(k[2] == "doe" for k in idx)


def test_check_gate_raises_on_a_missing_key_for_a_gatable_arm():
    """A key absent from a target that DOES exist is still a stop condition, not a skip."""

    class _Rec:
        instance, seed, arm, dim, regret = "nope", 0, "qlogei", 6, 0.1

    with pytest.raises(MissingGateTarget):
        check_gate(_Rec(), {})


def test_check_gate_marks_kernel_arms_ungated_explicitly_when_q30_is_absent():
    """`gated: false` in the row, never a silently missing comparison."""

    class _Rec:
        instance, seed, arm, dim, regret = "033466197eba3ddb", 0, "qlogei-add", 6, 0.1

    verdict = check_gate(_Rec(), {})
    assert verdict["gated"] is False
    assert "q30" in verdict["reason"]
    assert verdict["abs_delta"] is None


def test_all_eight_registered_arms_are_present():
    assert set(ARMS) == {"doe", "qlogei", "qlognei", "qlogei-add", "qlogei-addonly",
                         "lhs", "sobol", "random"}


# --- the re-expressed K6b scorer, pinned to committed rows ----------------------------

def _committed_k6b(instance, seed, arm):
    d = json.loads((ROOT / "results/k6b-conservative.json").read_text())
    return sorted([r for r in d["rows"] if r["instance"] == instance
                   and r["seed"] == seed and r["arm"] == arm],
                  key=lambda r: r["tau_frac"])


@pytest.mark.slow
def test_score_k6b_reproduces_the_committed_primary_cell_rows():
    """The re-expression must be the same arithmetic, not merely the same shape.

    `doe` is chosen because it is the cheapest regeneration (0.1 s) AND the only arm that
    exercises Amendment B3's active-subspace path, which is where a re-expression is most
    likely to diverge.
    """
    instance, seed, arm = "033466197eba3ddb", 0, "doe"
    rec = regenerate(instance, 6, 0.25, seed, arm)
    inst = instance_by_id(instance, 6)
    orc = BiphasicOracle(inst, sigma_rel=0.25, seed=seed)
    X_sub = sobol_grid(6, 2_000, seed=0)

    got = sorted(score_k6b(rec, orc, X_sub, float(inst.optimum_value)),
                 key=lambda r: r["tau_frac"])
    want = _committed_k6b(instance, seed, arm)
    assert len(got) == len(want) == 4

    for g, w in zip(got, want):
        for key, wv in w.items():
            gv = g[key]
            if isinstance(wv, float) and wv != wv:      # nan
                assert gv != gv, key
            elif isinstance(wv, float):
                assert gv == wv, f"{key}: {gv!r} != {wv!r}"
            else:
                assert gv == wv, key


@pytest.mark.slow
def test_score_k6b_reproduces_a_committed_spread_arm_row():
    """`lhs` exercises the 20-ordering static-curve path and the no-subspace branch."""
    instance, seed, arm = "033466197eba3ddb", 0, "lhs"
    rec = regenerate(instance, 6, 0.25, seed, arm)
    inst = instance_by_id(instance, 6)
    orc = BiphasicOracle(inst, sigma_rel=0.25, seed=seed)
    X_sub = sobol_grid(6, 2_000, seed=0)

    d = json.loads((ROOT / "results/k6b-conservative-spread.json").read_text())
    want = sorted([r for r in d["rows"] if r["instance"] == instance
                   and r["seed"] == seed and r["arm"] == arm],
                  key=lambda r: r["tau_frac"])
    got = sorted(score_k6b(rec, orc, X_sub, float(inst.optimum_value)),
                 key=lambda r: r["tau_frac"])
    assert len(got) == len(want) == 4
    for g, w in zip(got, want):
        for key, wv in w.items():
            gv = g[key]
            if isinstance(wv, float) and wv != wv:
                assert gv != gv, key
            else:
                assert gv == wv, f"{key}: {gv!r} != {wv!r}"


@pytest.mark.slow
def test_regenerated_regret_reproduces_the_committed_column_exactly_at_d8():
    """The registered gate itself, on the cell that has never been run.

    `doe` at d=8 against `results/e2-doe-d8.json` -- the comparison the §3.6 defect
    would drop. |delta| == 0 exactly; no tolerance exists here.
    """
    rows = json.loads((ROOT / "results/e2-doe-d8.json").read_text())
    ref = [r for r in rows if r["dim"] == 8 and r["sigma"] == 0.25][0]
    rec = regenerate(ref["instance"], 8, 0.25, ref["seed"], "doe")
    assert rec.regret == ref["regret"]


# --- the P3-B2 sensitivity scorer ------------------------------------------------------

@pytest.mark.slow
def test_dual_tau_scorer_under_the_standard_definition_equals_the_committed_scorer():
    """The sensitivity may not change the baseline it is measured against.

    `score_k6_dual_tau` computes both tau definitions in one posterior pass. Its
    `tau_max` half must be bit-identical to `run_k6_designspace.score_campaign`, or the
    reported movement is contaminated by an implementation difference.
    """
    from run_k6_designspace import score_campaign
    from run_p3_cells import score_k6_dual_tau

    instance, seed, arm = "033466197eba3ddb", 0, "doe"
    rec = regenerate(instance, 6, 0.10, seed, arm)
    inst = instance_by_id(instance, 6)
    orc = BiphasicOracle(inst, sigma_rel=0.10, seed=seed)
    grid = sobol_grid(6, 20_000, seed=0)
    with torch.no_grad():
        truth = orc.truth(grid).reshape(-1).double()
    active = torch.zeros(6, dtype=torch.bool)
    active[list(rec.kept_factors)] = True

    want = score_campaign(rec, orc, grid, truth, active)
    std, exact = score_k6_dual_tau(rec, orc, grid, truth, active)

    assert len(std) == len(want) == 24
    for g, w in zip(std, want):
        for key, wv in w.items():
            gv = g[key]
            if isinstance(wv, float) and wv != wv:
                assert gv != gv, key
            else:
                assert gv == wv, f"{key}: {gv!r} != {wv!r}"

    # And the exact half must actually differ, or the sensitivity measures nothing.
    assert all(e["tau_max"] < s["tau_max"] or s["gamma"] == 0.50
               for s, e in zip(std, exact))
