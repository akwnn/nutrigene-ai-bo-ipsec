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
    idx, ungated = build_gate_index(dim=8, sigma=0.25, arms=("doe",))
    assert len({k[0:2] for k in idx}) == 50
    assert all(k[2] == "doe" for k in idx)
    assert ungated == {}


def test_build_gate_index_covers_all_fifty_keys_for_every_gatable_arm():
    """The seven arms that DO have a committed column must all be present, at every cell."""
    gatable = tuple(a for a in ARMS if a not in KERNEL_ARMS)
    for dim, sigma in ((6, 0.10), (8, 0.25), (8, 0.10)):
        idx, _ = build_gate_index(dim, sigma, gatable)
        for arm in gatable:
            assert len([k for k in idx if k[2] == arm]) == 50, (arm, dim, sigma)


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

    reason = "results/q30-additive.json absent - CANNOT GATE"
    verdict = check_gate(_Rec(), {}, {"qlogei-add": reason})
    assert verdict["gated"] is False
    assert "q30" in verdict["reason"]
    assert verdict["abs_delta"] is None


def test_kernel_arms_are_ungated_only_while_q30_is_actually_absent():
    """`gated: false` must be a measured fact about the disk, not a hardcoded label."""
    q30 = ROOT / "results/q30-additive.json"
    _, ungated = build_gate_index(6, 0.10, ("qlogei-add",))
    if q30.exists():
        assert ungated == {}
    else:
        assert "qlogei-add" in ungated and "q30" in ungated["qlogei-add"]


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


# --- Amendment F (commit 07e98df), which supersedes the brief's Statistics section -----

def test_error_volumes_reproduce_the_committed_iou_column():
    """F2a's registered validation, re-run here rather than taken on trust.

    `intersect / (vol_pred + true_frac_above_tau - intersect)` must reproduce the
    committed `iou_pred`, with ZERO impossible negative type-II volumes. This is the
    D12-clean bar: a committed column, not a regeneration of the same arithmetic.

    **This test now guards the canonical `boec.calibration.error_volumes`.** It was
    written against a second copy in `designspace.py`, which is deleted; gating against
    the committed `iou_pred` column is a stronger bar than comparing two implementations
    to each other, so the test moved rather than being dropped with the copy.

    **The bar is one machine epsilon and that is not a widening.** Measured here at
    2.220446049250313e-16, which IS `numpy.finfo(float).eps` exactly; the registration's
    "2.220e-16" is that same number at four significant figures. Asserting the literal
    2.220e-16 fails by one ULP, so the constant is written as `eps` rather than as a
    decimal that only looks like the registered one.

    **6,000 rows are scorable, not the registered 2,553.** `iou_pred` is committed as
    `0.0` on the 3,447 empty rows rather than `nan` -- the F2a worker's erratum -- so
    every row has a finite `iou_pred`. 2,553 + 3,447 = 6,000. The count is asserted
    exactly so a future change to that convention breaks this test loudly.
    """
    import numpy as np

    from boec.calibration import error_volumes

    rows = json.loads((ROOT / "results/k6-designspace.json").read_text())["rows"]
    worst, scorable, negative = 0.0, 0, 0
    for r in rows:
        ev = error_volumes(r["vol_pred"], r["fi_pred"], r["true_frac_above_tau"])
        if ev["type_II_vol"] < -1e-12:
            negative += 1
        iou = r["iou_pred"]
        if isinstance(iou, float) and iou == iou and ev["implied_iou"] == ev["implied_iou"]:
            scorable += 1
            worst = max(worst, abs(ev["implied_iou"] - iou))
    assert negative == 0, f"{negative} impossible negative type-II volumes"
    assert scorable == 6000, scorable
    assert worst <= float(np.finfo(float).eps), f"worst |delta| {worst:.17e}"


def test_error_volumes_are_exact_where_fi_and_iou_are_nan():
    """The part of F2a that was not obvious: empty D_est is the common case, not a corner.

    An empty region certifies nothing, so it makes no type I error and its type II error
    is the whole true set. `fi` and `iou` are 0/0 there; both volumes are exact.
    """
    from boec.calibration import error_volumes

    ev = error_volumes(vol=0.0, fi=float("nan"), prevalence=0.0625)
    assert ev["type_I_vol"] == 0.0
    assert ev["intersect"] == 0.0
    assert ev["type_II_vol"] == 0.0625
    assert ev["total_error_vol"] == 0.0625


def test_error_volumes_recover_a_perfect_region():
    from boec.calibration import error_volumes

    ev = error_volumes(vol=0.25, fi=0.0, prevalence=0.25)
    assert ev["type_I_vol"] == 0.0
    assert ev["type_II_vol"] == 0.0
    assert ev["implied_iou"] == 1.0


# --- the kernel arms at d=8 have no comparator and never will -------------------------

def _fake_q30(tmp_path, dims=(6,)):
    p = tmp_path / "q30-additive.json"
    p.write_text(json.dumps([
        {"instance": i, "dim": d, "sigma": s, "seed": seed, "arm": arm, "regret": 0.1}
        for d in dims for s in (0.25, 0.10) for arm in KERNEL_ARMS
        for i in ("033466197eba3ddb",) for seed in (0, 1)]))
    return p


def test_kernel_arms_at_d8_are_recorded_ungated_not_an_abort(tmp_path):
    """`run_q30_additive.py` is committed at DIM = 6, so d=8 has no column and none is
    coming. That absence is a registered fact, so the correct behaviour is an explicit
    `gated: false` with a reason -- NOT the hard error every other missing target gets.
    """
    q30 = _fake_q30(tmp_path, dims=(6,))
    _, ungated = build_gate_index(8, 0.25, KERNEL_ARMS,
                                  targets={a: q30 for a in KERNEL_ARMS})
    assert set(ungated) == set(KERNEL_ARMS)
    for arm in KERNEL_ARMS:
        assert "d=8" in ungated[arm] or "dim" in ungated[arm]


def test_kernel_arms_at_d6_ARE_gated_once_q30_covers_the_cell(tmp_path):
    """The exemption is narrow: where the column exists, the gate runs."""
    q30 = _fake_q30(tmp_path, dims=(6,))
    idx, ungated = build_gate_index(6, 0.10, KERNEL_ARMS,
                                    targets={a: q30 for a in KERNEL_ARMS})
    assert ungated == {}
    assert ("033466197eba3ddb", 0, "qlogei-add") in idx


def test_the_kernel_exemption_does_not_weaken_any_other_arm(tmp_path):
    """A gatable arm with a target that exists but has no rows is still a hard error."""
    q30 = _fake_q30(tmp_path, dims=(6,))
    with pytest.raises(MissingGateTarget):
        build_gate_index(8, 0.25, ("qlogei",), targets={"qlogei": q30})


def test_provenance_records_the_thread_count():
    """Erratum 2's registered remedy: thread count in every provenance block.

    The gates are now known NOT to be thread-contingent -- P2 re-measured all 20 numeric
    K6 columns at all 24 cells at exactly 0.0 under `set_num_threads(1)`. This is
    recorded because nothing in the repository recorded it before, not because it varies.
    """
    from run_p3_cells import _versions

    v = _versions()
    assert v["torch_num_threads"].isdigit()
    assert "omp_num_threads" in v


@pytest.mark.slow
def test_auprc_column_matches_sklearn_on_a_real_campaign():
    """F2b, cross-checked against the reference implementation rather than against us.

    `boec.calibration.average_precision` is another worker's module; this asserts the
    column my rows carry equals `sklearn.metrics.average_precision_score` on the same
    (map, truth, tau), so a divergence in either surfaces here.
    """
    from sklearn.metrics import average_precision_score

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

    std, _ = score_k6_dual_tau(rec, orc, grid, truth, active, dual=False)
    assert len(std) == 24

    checked = 0
    for r in std:
        assert "auprc_pred" in r and "auprc_latent" in r
        assert "type_I_vol_pred" in r and "type_II_vol_pred" in r
        assert "type_I_vol_latent" in r and "type_II_vol_latent" in r
        label = (truth >= r["tau"]).double().numpy()
        if label.sum() in (0, label.size):
            assert r["auprc_pred"] is None
            continue
        # Recompute the map the row was scored from, then compare to sklearn.
        from boec.designspace import gp_adapter, predictive_probability_map
        from boec.surrogate import build_gp
        from boec.replay import unit_bounds
        model = build_gp(rec.X, rec.Y, rec.Yvar, unit_bounds(6))
        mean, sd = gp_adapter(model).posterior_mean_and_sd(grid)

        class _M:
            def posterior_mean_and_sd(self, X):
                return mean, sd

        sigma_pred = ((orc.sigma_rel * mean).abs() ** 2 + orc.sigma_add ** 2).sqrt()
        p = predictive_probability_map(_M(), grid, r["tau"], sigma_pred)
        want = float(average_precision_score(label, p.numpy()))
        assert abs(r["auprc_pred"] - want) < 1e-12, (r["gamma"], r["tau_frac"],
                                                     r["auprc_pred"], want)
        checked += 1
        if checked >= 3:
            break
    assert checked >= 3


@pytest.mark.slow
def test_amendment_f_columns_do_not_disturb_the_committed_ones():
    """The F columns are added BESIDE the committed K6 columns, never in place of them.

    Every field `run_k6_designspace.score_campaign` emits must still be bit-identical
    after F2a and F2b were wired in -- that is the whole reason `score_campaign` is still
    imported.
    """
    from run_k6_designspace import score_campaign
    from run_p3_cells import score_k6_dual_tau

    instance, seed, arm = "033466197eba3ddb", 0, "lhs"
    rec = regenerate(instance, 6, 0.10, seed, arm)
    inst = instance_by_id(instance, 6)
    orc = BiphasicOracle(inst, sigma_rel=0.10, seed=seed)
    grid = sobol_grid(6, 20_000, seed=0)
    with torch.no_grad():
        truth = orc.truth(grid).reshape(-1).double()
    active = torch.ones(6, dtype=torch.bool)

    want = score_campaign(rec, orc, grid, truth, active)
    got, _ = score_k6_dual_tau(rec, orc, grid, truth, active, dual=False)
    assert len(got) == len(want) == 24
    for g, w in zip(got, want):
        for key, wv in w.items():
            gv = g[key]
            if isinstance(wv, float) and wv != wv:
                assert gv != gv, key
            else:
                assert gv == wv, f"{key}: {gv!r} != {wv!r}"


# --- the partial-file hazard, found on P2's corpse -------------------------------------

def test_the_registered_result_paths_are_un_ignored_and_therefore_stageable():
    """The premise of everything below, measured rather than assumed.

    `.gitignore` un-ignores all six P3 outputs BY PATH at registration time, which is a
    deliberate rule (an ignored artefact is a log line no clone can check). The cost is
    that a partial written there is stageable, and `results/p2-versionb-gamma.json` shows
    what that looks like: 8/50 keys, a full provenance block, `gate_failures: []`, and
    nothing at all saying it is incomplete.
    """
    import subprocess

    for name in ("p3-k6-d6-s010", "p3-k6-d8-s025", "p3-k6-d8-s010",
                 "p3-k6b-d6-s010", "p3-k6b-d8-s025", "p3-k6b-d8-s010"):
        r = subprocess.run(["git", "check-ignore", f"results/{name}.json"],
                           cwd=ROOT, capture_output=True, text=True)
        assert r.returncode != 0, f"results/{name}.json is ignored; registration says not"


def test_a_partial_is_marked_in_progress_with_its_key_counts(tmp_path):
    from run_p3_cells import _write

    out = tmp_path / "cell.json"
    _write(out, "sha", False, {"dim": 6, "sigma": 0.1, "arms": ["lhs"]}, [], {}, [],
           "2026-08-21T00:00:00+08:00", status="in_progress",
           keys_present=8, keys_expected=50)
    d = json.loads(out.read_text())
    assert d["status"] == "in_progress"
    assert d["keys_present"] == 8 and d["keys_expected"] == 50
    assert d["complete"] is False


def test_a_finished_file_says_so_and_its_counts_agree(tmp_path):
    from run_p3_cells import _write

    out = tmp_path / "cell.json"
    _write(out, "sha", False, {"dim": 6, "sigma": 0.1, "arms": ["lhs"]}, [], {}, [],
           "2026-08-21T00:00:00+08:00", status="complete",
           keys_present=50, keys_expected=50)
    d = json.loads(out.read_text())
    assert d["status"] == "complete" and d["complete"] is True
    assert d["keys_present"] == d["keys_expected"] == 50


def test_promote_refuses_to_publish_an_incomplete_file(tmp_path):
    """A partial must not be able to reach a registered result path, even by mistake."""
    from run_p3_cells import IncompleteResult, _write, promote

    scratch = tmp_path / "scratch.json"
    out = tmp_path / "results" / "cell.json"
    out.parent.mkdir()
    _write(scratch, "sha", False, {"dim": 6, "sigma": 0.1, "arms": ["lhs"]}, [], {}, [],
           "t", status="in_progress", keys_present=8, keys_expected=50)
    with pytest.raises(IncompleteResult):
        promote(scratch, out)
    assert not out.exists(), "an incomplete file reached the results path"


def test_promote_publishes_a_complete_file(tmp_path):
    from run_p3_cells import _write, promote

    scratch = tmp_path / "scratch.json"
    out = tmp_path / "results" / "cell.json"
    out.parent.mkdir()
    _write(scratch, "sha", False, {"dim": 6, "sigma": 0.1, "arms": ["lhs"]}, [], {}, [],
           "t", status="complete", keys_present=50, keys_expected=50)
    promote(scratch, out)
    assert json.loads(out.read_text())["status"] == "complete"


@pytest.mark.slow
def test_a_smoke_run_writes_nothing_into_the_results_directory(tmp_path):
    """`--limit` is mechanically incapable of producing a committable result.

    The working rule has always been "a smoke run is NEVER committed as a result". That
    was discipline; this makes it structural. A limited run writes only to scratch and
    its status is `smoke`, so there is nothing at the registered path to sweep up.
    """
    import subprocess

    k6 = tmp_path / "results" / "p3-k6-smoke.json"
    k6b = tmp_path / "results" / "p3-k6b-smoke.json"
    k6.parent.mkdir()
    scratch = tmp_path / "scratch"
    r = subprocess.run(
        [".venv/bin/python", "scripts/run_p3_cells.py", "--dim", "6", "--sigma", "0.10",
         "--limit", "1", "--arms", "lhs", "--scratch", str(scratch),
         "--k6-out", str(k6), "--k6b-out", str(k6b)],
        cwd=ROOT, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]

    assert not k6.exists() and not k6b.exists(), "a smoke run reached the results path"
    partials = sorted(scratch.glob("*.json"))
    assert partials, f"no scratch partial written; stdout:\n{r.stdout[-2000:]}"
    d = json.loads(partials[0].read_text())
    assert d["status"] == "smoke"
    assert d["complete"] is False
