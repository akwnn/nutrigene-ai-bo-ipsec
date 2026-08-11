"""T1.4c — under rule C, both arms must be asked the same question the same way.

Rule C scores each method at the point its own model recommends. That is a comparison
of *models* only if the recommendation is *located* identically for both. It was not:

    DoE arm   metrics.constrained_argmax   n_restarts=20, raw_samples=4096, seed=seed
              (via over_prediction_at_constrained_argmax, doe.py:335)
    BO arm    optimize_acqf(PosteriorMean) num_restarts=10, raw_samples=256, UNSEEDED

A 16x smaller Sobol screen on one side means part of the measured gap is search
quality, pointing at whichever arm got the bigger screen. The reported +0.2915 was
computed under that asymmetry.

Checked structurally rather than by running, so a divergence is caught even in a branch
no test exercises -- the same approach as `tests/test_q33_extrapolation.py`, and for the
same reason: this project has already shipped one locator asymmetry.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
import torch

from boec.metrics import constrained_argmax, over_prediction_at_constrained_argmax

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "q29_symmetric.py"


def _tree() -> ast.Module:
    return ast.parse(SCRIPT.read_text())


def _defaults(fn) -> dict:
    return {k: v.default for k, v in inspect.signature(fn).parameters.items()
            if v.default is not inspect.Parameter.empty}


def test_the_bo_arm_uses_the_shared_locator_at_the_module_constants():
    """Exactly one locator call, and every setting is a named constant, not a literal."""
    calls = [n for n in ast.walk(_tree())
             if isinstance(n, ast.Call)
             and getattr(n.func, "id", None) == "constrained_argmax"]
    assert len(calls) == 1, f"expected exactly 1 locator call, found {len(calls)}"
    kw = {k.arg: k.value for k in calls[0].keywords}
    assert set(kw) == {"n_restarts", "raw_samples", "seed"}, sorted(kw)
    assert getattr(kw["n_restarts"], "id", None) == "N_RESTARTS"
    assert getattr(kw["raw_samples"], "id", None) == "RAW_SAMPLES"
    # the DoE arm is seeded per campaign (doe.py passes seed=seed); so is this
    assert getattr(kw["seed"], "id", None) == "seed", (
        "the BO arm must be seeded per campaign, as the DoE arm is -- an unseeded "
        "locator makes rule C irreproducible run to run")


def test_the_module_constants_equal_what_the_doe_arm_actually_gets():
    """The DoE arm takes the defaults. If they diverge, the arms diverge silently."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("q29", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = _defaults(constrained_argmax)
    assert m.N_RESTARTS == d["n_restarts"], (
        f"BO arm screens at n_restarts={m.N_RESTARTS}, DoE arm at {d['n_restarts']}")
    assert m.RAW_SAMPLES == d["raw_samples"], (
        f"BO arm screens at raw_samples={m.RAW_SAMPLES}, DoE arm at {d['raw_samples']}")


def test_the_doe_wrapper_does_not_override_those_defaults():
    """`doe.py` passes only `seed=`, so the wrapper's defaults are what it gets."""
    outer, inner = (_defaults(over_prediction_at_constrained_argmax),
                    _defaults(constrained_argmax))
    for k in ("n_restarts", "raw_samples", "seed"):
        assert outer[k] == inner[k], (
            f"over_prediction_at_constrained_argmax defaults {k}={outer[k]} but "
            f"constrained_argmax defaults {k}={inner[k]}; the DoE arm is not getting "
            f"what this test assumes it gets")


def test_no_second_locator_survives_in_the_script():
    """A second optimizer here would be a second screening budget.

    Checked over the AST, not the raw text: the docstring of `posterior_mean_argmax`
    names the locator it replaced, and a substring ban would fire on the sentence
    recording the fix. Names in code are what matter.
    """
    tree = _tree()
    banned = {"optimize_acqf", "PosteriorMean", "differential_evolution",
              "basinhopping", "minimize", "optimize_acqf_discrete"}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            used |= {a.name for a in node.names}
        elif isinstance(node, ast.Import):
            used |= {a.name.split(".")[-1] for a in node.names}
    clash = sorted(banned & used)
    assert not clash, f"{clash} would be a second locator for rule C"


def test_the_shared_locator_is_deterministic_under_its_seed():
    """Rule C must be reproducible; the previous BO-side locator was unseeded."""
    centre = torch.full((6,), 0.4, dtype=torch.double)

    def predict(Z: torch.Tensor) -> torch.Tensor:
        return (-((Z - centre) ** 2).sum(-1, keepdim=True))

    box = torch.stack([torch.zeros(6, dtype=torch.double),
                       torch.ones(6, dtype=torch.double)])
    a, va, _ = constrained_argmax(predict, box, n_restarts=20, raw_samples=4096, seed=3)
    b, vb, _ = constrained_argmax(predict, box, n_restarts=20, raw_samples=4096, seed=3)
    assert torch.allclose(a, b) and va == pytest.approx(vb)
    assert torch.allclose(a, centre, atol=1e-4), a
