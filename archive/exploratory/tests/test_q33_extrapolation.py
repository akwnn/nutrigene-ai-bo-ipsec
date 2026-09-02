"""Guards for Q33 — extrapolation geometry on the published stage-2 data.

The one that matters is `test_both_arms_use_the_same_locator_at_the_same_settings`.
Two optimizers, or one optimizer at two screening budgets, would make the comparison
about the search rather than the models — a defect already logged in this project. The
registration says it is asserted by test rather than verified by reading, so it is.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest
import torch

from boec.metrics import constrained_argmax
from boec.rsm import fit_second_order, second_order_design_matrix
from boec.surrogate import build_gp

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_q33_extrapolation.py"


def _tree():
    return ast.parse(SCRIPT.read_text())


def test_both_arms_use_the_same_locator_at_the_same_settings():
    """Every constrained_argmax call passes the identical module-level constants.

    Checked structurally rather than by running, so a divergence is caught even in a
    branch this test does not exercise.
    """
    calls = [n for n in ast.walk(_tree())
             if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "constrained_argmax"]
    assert len(calls) == 2, f"expected exactly 2 locator calls, found {len(calls)}"
    seen = []
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords}
        assert set(kw) == {"n_restarts", "raw_samples", "seed"}, sorted(kw)
        # every setting must be the shared module constant, not a literal
        seen.append(tuple(getattr(v, "id", None) for v in kw.values()))
    assert seen[0] == seen[1] == ("N_RESTARTS", "RAW_SAMPLES", "SEED"), seen


def test_no_second_optimizer_is_used_for_either_arm():
    """`over_prediction_at_constrained_argmax` is a SCORER, not a locator."""
    src = SCRIPT.read_text()
    assert "over_prediction_at_constrained_argmax" not in src
    for banned in ("optimize_acqf", "minimize(", "differential_evolution", "basinhopping"):
        assert banned not in src, f"{banned} would be a second locator"


def test_the_locator_is_deterministic_under_its_seed():
    """Both people must get the same coordinates from the same inputs."""
    rng = np.random.default_rng(0)
    X = rng.uniform(-1, 1, size=(24, 4))
    y = (X[:, 0] - 0.5 * X[:, 1] ** 2).reshape(-1, 1)
    model = fit_second_order(torch.tensor(X), torch.tensor(y))
    box = torch.stack([torch.full((4,), -2.0, dtype=torch.double),
                       torch.full((4,), 2.0, dtype=torch.double)])
    a, va, _ = constrained_argmax(model.predict, box, n_restarts=20, raw_samples=4096, seed=0)
    b, vb, _ = constrained_argmax(model.predict, box, n_restarts=20, raw_samples=4096, seed=0)
    assert torch.allclose(a, b) and va == pytest.approx(vb)


def test_stage2_fidelity_holds_before_anything_is_fitted():
    """Row count, coded levels and quadratic estimability. Halt on any mismatch."""
    import csv
    rows = list(csv.DictReader((ROOT / "data/published/hall_ogle_2025_stage2.csv").open()))
    assert len(rows) == 25
    X = np.array([[int(r[f]) for f in ["c", "civ", "ln411", "fn"]] for r in rows], float)
    assert set(np.unique(X)) <= {-1.0, 0.0, 1.0}
    y = np.array([float(r["response"]) if r["response"] else np.nan for r in rows])
    ok = ~np.isnan(y)
    assert ok.sum() == 24, "one median is not separable; the rest must be present"
    M = second_order_design_matrix(X[ok])
    assert M.shape[1] == 15 and np.linalg.matrix_rank(M) == 15


def test_the_gp_argmax_is_not_pinned_inside_the_design_region():
    """The Q33 gate, kept as a test.

    If the GP's posterior-mean argmax could not land outside +/-1, the registered claim
    would be a tautology. Under a monotone corner trend it runs to the search-box wall.
    """
    import csv
    rows = list(csv.DictReader((ROOT / "data/published/hall_ogle_2025_stage2.csv").open()))
    X = np.array([[int(r[f]) for f in ["c", "civ", "ln411", "fn"]] for r in rows], float)
    y = X.sum(1).reshape(-1, 1)
    fit_box = torch.stack([torch.full((4,), -1.0, dtype=torch.double),
                           torch.full((4,), 1.0, dtype=torch.double)])
    gp = build_gp(torch.tensor(X), torch.tensor(y),
                  torch.full((len(X), 1), 1e-4, dtype=torch.double), fit_box)

    def predict(Z):
        with torch.no_grad():
            return gp.posterior(Z).mean

    box = torch.stack([torch.full((4,), -2.0, dtype=torch.double),
                       torch.full((4,), 2.0, dtype=torch.double)])
    xh, _, _ = constrained_argmax(predict, box, n_restarts=20, raw_samples=4096, seed=0)
    assert (np.abs(xh.numpy().ravel()) > 1.0).any(), (
        "the GP's argmax is pinned inside the design region; the endpoint is a tautology")


def test_theo_is_recorded_at_its_published_coded_position():
    """TheO's Collagen IV at coded +1.40 is the published extrapolation."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("q33", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.THEO.tolist() == [0.0028, 1.4, 0.125, -1.0]
    assert m.THEO[1] > 1.0, "TheO's CIV must sit outside the design region"
    assert m.THEO[3] == -1.0, "fibronectin sits on its design floor, not an optimum"
