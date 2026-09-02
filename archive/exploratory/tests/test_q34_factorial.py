"""Q34 / T1.1 — guards for the design x surrogate x rule factorial.

The factorial exists to separate three confounded factors. It only does that if the one
thing it is NOT varying -- how a recommendation is located -- is held genuinely fixed.
Four cells, two surrogate classes, two designs, and a single locator across all of them.

Checked structurally over the AST, so a divergence is caught even in a branch no test
exercises. The project has already shipped one locator asymmetry (T1.4c, where the BO
arm ran unseeded at a 16x smaller Sobol screen than the DoE arm), which is the whole
reason the registration promises this as a test rather than as a reading.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pytest
import torch

from boec.metrics import constrained_argmax
from boec.rsm import fit_second_order, second_order_design_matrix

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_q34_factorial.py"


def _tree() -> ast.Module:
    return ast.parse(SCRIPT.read_text())


def test_every_cell_locates_its_recommendation_the_same_way():
    """Both locator calls -- GP and polynomial -- pass the identical module constants."""
    calls = [n for n in ast.walk(_tree())
             if isinstance(n, ast.Call)
             and getattr(n.func, "id", None) == "constrained_argmax"]
    assert len(calls) == 2, (
        f"expected exactly 2 locator calls (one per surrogate class), found {len(calls)}")
    seen = []
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords}
        assert set(kw) == {"n_restarts", "raw_samples", "seed"}, sorted(str(k) for k in kw)
        seen.append(tuple(getattr(kw[k], "id", None)
                          for k in ("n_restarts", "raw_samples", "seed")))
    assert seen[0] == seen[1] == ("N_RESTARTS", "RAW_SAMPLES", "seed"), seen


def test_the_locator_settings_match_what_the_doe_arm_receives():
    """cell 3 comes from `doe.py`, which takes `constrained_argmax`'s defaults."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("q34", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(m)
    d = {k: v.default for k, v in inspect.signature(constrained_argmax).parameters.items()
         if v.default is not inspect.Parameter.empty}
    assert m.N_RESTARTS == d["n_restarts"]
    assert m.RAW_SAMPLES == d["raw_samples"]


def test_no_second_optimizer_is_used_for_any_cell():
    """Checked over the AST: the docstrings name the locator this replaced."""
    tree = _tree()
    banned = {"optimize_acqf", "PosteriorMean", "differential_evolution",
              "basinhopping", "minimize", "over_prediction_at_constrained_argmax"}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            used |= {a.name for a in node.names}
    clash = sorted(banned & used)
    assert not clash, f"{clash} would be a second locator"


def test_cell6_failures_are_recorded_rather_than_dropped():
    """A silent `except: continue` here would turn a result into a smaller sample.

    The registration says every rank-deficient fit is recorded with its reason. So the
    handler must WRITE the failure, not skip the row.
    """
    src = SCRIPT.read_text()
    handlers = [n for n in ast.walk(_tree()) if isinstance(n, ast.ExceptHandler)]
    assert handlers, "cell 6 must handle fit failures explicitly"
    for h in handlers:
        body = ast.dump(ast.Module(body=h.body, type_ignores=[]))
        assert "Continue" not in body and "Pass" not in body, (
            "a bare continue/pass in the cell-6 handler would drop failed instances "
            "silently; the failure rate is a registered result")
    assert 'row["cell6_failure"] = f"{type(exc).__name__}' in src


def test_the_doe_yvar_is_recomputed_not_redrawn():
    """Re-evaluating the oracle would draw fresh noise and change the experiment.

    `_plug_in_yvar` is a deterministic function of the observed y, so cell 5 sees the
    same measurements cell 1 was scored on.
    """
    from boec.torch_oracle import _plug_in_yvar
    y = np.array([[0.3], [0.7], [1.1]])
    a = _plug_in_yvar(y, 0.25, 0.01)
    b = _plug_in_yvar(y, 0.25, 0.01)
    assert np.array_equal(a, b), "plug-in Yvar must be deterministic in y"
    assert np.allclose(a, np.maximum(y**2 * 0.0625 + 1e-4, 1e-4))
    src = SCRIPT.read_text()
    assert "_plug_in_yvar" in src and "od.evaluate(" not in src, (
        "cell 5 must reuse the DoE arm's observations, not re-evaluate the oracle")


def test_a_full_second_order_model_is_estimable_at_both_dimensions_in_principle():
    """n=48 must exceed p, or cell 6 is undefined before any conditioning question.

    d=6 -> p=28 (20 residual df); d=8 -> p=45 (3 residual df). The d=8 margin is why
    the registration predicts hard failures there rather than treating them as a bug.
    """
    for dim, expected_p in ((6, 28), (8, 45)):
        rng = np.random.default_rng(0)
        X = torch.tensor(rng.uniform(0, 1, size=(48, dim)))
        M = second_order_design_matrix(X)
        p = M.shape[1]
        assert p == expected_p, f"d={dim}: expected p={expected_p}, got {p}"
        assert 48 > p, f"d={dim}: n=48 cannot fit p={p}"


def test_fit_second_order_raises_rather_than_pseudo_inverting_a_clustered_design():
    """Cell 6's failure mode, exercised. A pseudo-inverse would hide it."""
    rng = np.random.default_rng(1)
    # a tight cluster is what an adaptive design produces near its incumbent
    X = torch.tensor(np.full((48, 6), 0.5) + rng.normal(0, 1e-9, size=(48, 6)))
    Y = torch.tensor(rng.normal(0, 1, size=(48, 1)))
    with pytest.raises(ValueError, match="rank-deficient|cannot fit"):
        fit_second_order(X, Y)
