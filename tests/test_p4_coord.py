"""P4 — `coord` gets the design-space metrics it has never had.

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) **before**
`scripts/run_p4_coord.py` existed.

WHY THIS FILE IS MOSTLY ABOUT OTHER ARMS
----------------------------------------
`coord` is not in `boec.replay`'s arm lists, so P4 builds its regeneration in its own
script. That is a second implementation of a thing the project already does five ways,
and a second implementation is exactly where a silent divergence lives. So the tests
that matter here are the ones that run the P4 pipeline on an arm whose K6 and K6b rows
are **already committed** — `lhs` — and demand bitwise agreement. If P4's scorers can
reproduce a committed arm's row exactly, the `coord` row beside it was produced by the
same arithmetic; if they cannot, `coord`'s numbers are not comparable with anything.

That is D12 in its usable form: gate against a committed column, never against a
regeneration of yourself.

THE Yvar QUESTION, WHICH IS NOT COSMETIC
-----------------------------------------
`coordinate_descent` calls `evaluator.evaluate` 48 times and throws the returned variance
away, keeping only ``Y``. The GP needs it back. Re-evaluating would draw fresh noise and
build a different campaign (`boec.replay`'s module docstring records the same trap for the
DoE arm), so P4 recomputes it from the **stored** ``Y`` with `_plug_in_yvar` — and
`test_yvar_is_what_the_oracle_actually_returned` pins that the recomputation is bitwise
what the oracle handed back, by capturing the discarded values as they go past.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_p4_coord.py"

DIM, SIGMA = 6, 0.25


def _load():
    spec = importlib.util.spec_from_file_location("p4_coord", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def p4():
    return _load()


def _committed(path: str, arm: str) -> list[dict]:
    """Committed rows for one arm **at the primary cell**.

    The dim/sigma filter is not decoration: `e2-grid.json` carries `coord` at all four
    (d, sigma_rel) cells, so an unfiltered pick returns a d=8 instance id and every
    d=6 lookup after it fails.
    """
    d = json.loads((ROOT / "results" / path).read_text())
    rows = d if isinstance(d, list) else d["rows"]
    return [r for r in rows if r["arm"] == arm and r["dim"] == DIM
            and abs(r["sigma"] - SIGMA) < 1e-12]


# --------------------------------------------------------------------------------------
# THE REGISTERED GATE
# --------------------------------------------------------------------------------------

def test_coord_reproduces_the_committed_regret_exactly():
    """|delta| = 0, not "small". `coord` never touches an optimiser, so exact is the bar.

    Three keys here; the runner does all 50 and records every delta.
    """
    p4 = _load()
    committed = {(r["instance"], r["seed"]): r["regret"]
                 for r in _committed("e2-grid.json", "coord")
                 if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12}
    assert len(committed) == 50, f"expected 50 committed coord rows, found {len(committed)}"

    for (inst_id, seed) in sorted(committed)[:3]:
        rec = p4.regenerate_coord(inst_id, DIM, SIGMA, seed)
        assert rec.regret == committed[(inst_id, seed)], (
            f"{inst_id} seed={seed}: regenerated {rec.regret!r} != committed "
            f"{committed[(inst_id, seed)]!r}")


def test_yvar_is_what_the_oracle_actually_returned(p4):
    """The plug-in recomputation must be bitwise the variance `evaluate` handed back.

    Captured by wrapping the oracle, not by asserting the formula against itself.
    """
    from boec.baselines import coordinate_descent
    from boec.replay import instance_by_id, unit_bounds
    from boec.torch_oracle import BiphasicOracle

    inst_id = sorted({r["instance"] for r in _committed("e2-grid.json", "coord")})[0]
    inst = instance_by_id(inst_id, DIM)

    class _Capturing:
        def __init__(self, orc):
            self._orc, self.seen = orc, []
            self.sigma_rel, self.sigma_add = orc.sigma_rel, orc.sigma_add

        def evaluate(self, X):
            y, v = self._orc.evaluate(X)
            self.seen.append(v)
            return y, v

        def truth(self, X):
            return self._orc.truth(X)

    cap = _Capturing(BiphasicOracle(inst, sigma_rel=SIGMA, seed=0))
    cd = coordinate_descent(cap, unit_bounds(DIM), budget=48, seed=0)
    handed_back = torch.cat(cap.seen).reshape(-1)

    rec = p4.regenerate_coord(inst_id, DIM, SIGMA, 0)
    assert torch.equal(rec.Y.reshape(-1), cd.Y.reshape(-1))
    assert torch.equal(rec.Yvar.reshape(-1), handed_back), (
        "recomputed Yvar is not the variance the oracle returned")


# --------------------------------------------------------------------------------------
# THE SCORERS ARE THE COMMITTED SCORERS
# --------------------------------------------------------------------------------------

@pytest.mark.slow
def test_k6_scorer_reproduces_a_committed_lhs_row_bitwise(p4):
    """P4's K6 path, run on `lhs`, must return `k6-designspace-spread.json` exactly."""
    from boec.norms import sobol_grid
    from boec.replay import instance_by_id, regenerate
    from boec.torch_oracle import BiphasicOracle

    ref = _committed("k6-designspace-spread.json", "lhs")
    key = (ref[0]["instance"], ref[0]["seed"])
    want = {(r["gamma"], r["tau_frac"]): r for r in ref
            if (r["instance"], r["seed"]) == key}
    assert len(want) == 24, f"expected 24 gamma x tau_frac cells, found {len(want)}"

    rec = regenerate(key[0], DIM, SIGMA, key[1], "lhs")
    orc = BiphasicOracle(instance_by_id(key[0], DIM), sigma_rel=SIGMA, seed=key[1])
    grid = sobol_grid(DIM, p4.GRID_N, seed=p4.GRID_SEED)
    with torch.no_grad():
        truth = orc.truth(grid).reshape(-1).double()

    got = {(r["gamma"], r["tau_frac"]): r for r in p4.score_k6(rec, orc, grid, truth)}
    assert set(got) == set(want)
    for cell, row in want.items():
        for k, v in row.items():
            if isinstance(v, float) and not np.isfinite(v):
                assert not np.isfinite(got[cell][k]), f"{cell} {k}"
            else:
                assert got[cell][k] == v, f"{cell} {k}: {got[cell][k]!r} != {v!r}"


@pytest.mark.slow
def test_k6b_scorer_reproduces_a_committed_lhs_row_bitwise(p4):
    """P4's K6b path, run on `lhs`, must return `k6b-conservative-spread.json` exactly."""
    from boec.norms import sobol_grid
    from boec.replay import instance_by_id, regenerate
    from boec.torch_oracle import BiphasicOracle

    ref = _committed("k6b-conservative-spread.json", "lhs")
    key = (ref[0]["instance"], ref[0]["seed"])
    want = {r["tau_frac"]: r for r in ref if (r["instance"], r["seed"]) == key}
    assert len(want) == 4, f"expected 4 tau_frac rows, found {len(want)}"

    inst = instance_by_id(key[0], DIM)
    rec = regenerate(key[0], DIM, SIGMA, key[1], "lhs")
    orc = BiphasicOracle(inst, sigma_rel=SIGMA, seed=key[1])
    X_sub = sobol_grid(DIM, p4.SUBSET_N, seed=p4.GRID_SEED)

    got = {r["tau_frac"]: r
           for r in p4.score_k6b(rec, orc, X_sub, float(inst.optimum_value))}
    assert set(got) == set(want)
    for tf, row in want.items():
        for k, v in row.items():
            if isinstance(v, float) and not np.isfinite(v):
                assert not np.isfinite(got[tf][k]), f"tau_frac={tf} {k}"
            else:
                assert got[tf][k] == v, f"tau_frac={tf} {k}: {got[tf][k]!r} != {v!r}"


def test_coord_declares_every_axis_active(p4):
    """`coord` sweeps all six coordinates, so Amendment B3's subspace pin must not fire.

    `n_active` is what separates it from `doe` in the same table; if it silently came
    back as 4 the two arms would be scored on different regions.
    """
    inst_id = sorted({r["instance"] for r in _committed("e2-grid.json", "coord")})[0]
    rec = p4.regenerate_coord(inst_id, DIM, SIGMA, 0)
    assert rec.kept_factors is None
    assert rec.dropped_held_at is None
    assert int(rec.X.shape[0]) == 48
    assert int(rec.X.shape[1]) == DIM


# --------------------------------------------------------------------------------------
# AMENDMENT F2a / F2b — ERROR VOLUMES AND AUPRC
# --------------------------------------------------------------------------------------
#
# The error volumes are recoverable from what the first P4 run already stored, because it
# carried `true_frac_above_tau` on every row. **AUPRC is not.** It needs the full `p_pred`
# vector against the truth labels over the 20k grid, and no stored row carries those --
# the same omission that makes `versionb.json` unscoreable to this day. So `coord` is
# re-scored, and the maps have to be rebuilt to do it.
#
# Rebuilding the maps is the risk. `run_k6_designspace.score_campaign` computes `p_pred`
# and `p_lat` internally and throws them away, so P4 computes its own -- and a second
# probability map is a second definition of every metric derived from it. The gate is
# `test_the_auprc_maps_are_k6s_maps`: three of K6's own committed columns are recomputed
# from P4's maps and required to match the row K6 produced, bitwise. If they do, the
# AUPRC beside them was taken on K6's object; if they do not, it was taken on some other.

@pytest.mark.slow
def test_the_auprc_maps_are_k6s_maps(p4):
    """P4's `p_pred`/`p_lat` must reproduce K6's own columns exactly, or AUPRC is not
    scoring the same object the rest of the row scores."""
    from boec.norms import sobol_grid
    from boec.replay import instance_by_id, regenerate
    from boec.torch_oracle import BiphasicOracle

    ref = _committed("k6-designspace-spread.json", "lhs")
    key = (ref[0]["instance"], ref[0]["seed"])
    rec = regenerate(key[0], DIM, SIGMA, key[1], "lhs")
    orc = BiphasicOracle(instance_by_id(key[0], DIM), sigma_rel=SIGMA, seed=key[1])
    grid = sobol_grid(DIM, p4.GRID_N, seed=p4.GRID_SEED)
    with torch.no_grad():
        truth = orc.truth(grid).reshape(-1).double()

    rows = p4.score_k6(rec, orc, grid, truth)
    assert len(rows) == 24
    for r in rows:
        for col in ("vol_pred", "vol_latent", "brier_pred", "brier_latent",
                    "auc_pred", "auc_latent", "iou_pred", "fi_pred"):
            want = r[col]
            got = r[f"_recomputed_{col}"]
            if isinstance(want, float) and not np.isfinite(want):
                assert not np.isfinite(got), (r["gamma"], r["tau_frac"], col)
            else:
                assert got == want, (r["gamma"], r["tau_frac"], col, got, want)


def test_minority_auprc_scores_the_explicit_complement(p4):
    """`truth < tau`, never `-truth >= -tau`.

    A point whose truth is exactly `tau` satisfies `truth >= tau` AND `-truth >= -tau`,
    so the negated form puts it in BOTH classes and the two AP values are then computed
    against label vectors that overlap. The complement is exclusive by construction.
    """
    truth = torch.tensor([0.0, 0.5, 1.0, 0.5], dtype=torch.double)
    tau = 0.5
    pos = (truth >= tau)
    neg_right = (truth < tau)
    neg_wrong = (-truth >= -tau)
    assert int((pos & neg_wrong).sum()) == 2, "the negated form double-counts ties"
    assert int((pos & neg_right).sum()) == 0
    assert int((pos | neg_right).sum()) == truth.numel()

    p = torch.tensor([0.1, 0.6, 0.9, 0.4], dtype=torch.double)
    out = p4.auprc_pair(p, truth, tau)
    assert out["ap_baseline"] == pytest.approx(3 / 4)
    assert out["ap_baseline_minority"] == pytest.approx(1 / 4)
    assert 0.0 <= out["auprc"] <= 1.0
    assert 0.0 <= out["auprc_minority"] <= 1.0

    # The label counts `auprc_pair` actually scored, not the arithmetic beside it. Three
    # of the four points are >= tau and exactly one is < tau; the two classes must
    # partition the grid. Checking only `ap_baseline` above would leave the tie handling
    # INSIDE the function unexercised -- which is how the first implementation shipped
    # with `-truth >= -tau` and scored the ties into both classes.
    assert out["n_positive"] == 3
    assert out["n_minority"] == 1
    assert out["n_positive"] + out["n_minority"] == truth.numel()


def test_ap_baseline_travels_because_ap_is_not_comparable_without_it(p4):
    """A no-skill ranker scores the prevalence, not 0.5, and prevalence runs 0.0012 to
    0.999 across this grid -- so an AP without its baseline is not comparable across
    cells. Both baselines are stored on every row."""
    truth = torch.linspace(0.0, 1.0, 1000, dtype=torch.double)
    p = torch.rand(1000, generator=torch.Generator().manual_seed(0), dtype=torch.double)
    for tau in (0.1, 0.5, 0.9):
        out = p4.auprc_pair(p, truth, tau)
        prevalence = float((truth >= tau).double().mean())
        assert out["ap_baseline"] == pytest.approx(prevalence)
        assert out["ap_baseline_minority"] == pytest.approx(1 - prevalence)
        # A random ranker sits near its baseline, not near 0.5.
        assert abs(out["auprc"] - prevalence) < 0.15, (tau, out["auprc"], prevalence)


def test_error_volumes_are_stored_and_reproduce_the_committed_iou(p4):
    """F2a's three columns on every row, gated against `iou_pred` via `implied_iou`."""
    from boec.calibration import error_volumes

    ref = _committed("k6-designspace-spread.json", "lhs")
    checked = 0
    for r in ref:
        if r["empty_pred"] or not np.isfinite(r["iou_pred"]):
            continue
        ev = error_volumes(r["vol_pred"], r["fi_pred"], r["true_frac_above_tau"])
        assert abs(ev["implied_iou"] - r["iou_pred"]) < 1e-12
        assert ev["type_I_vol"] == pytest.approx(r["vol_pred"] * r["fi_pred"])
        checked += 1
    # 456 of `lhs`'s 1,200 rows are non-empty with a finite IoU. The other 744 are the
    # empty-region case, which is exactly what F2a exists to cover and what this
    # particular gate cannot reach -- `implied_iou` needs a committed `iou_pred` to
    # check against, and there is none where the union is empty.
    assert checked > 400, checked
