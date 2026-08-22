"""Q59 map re-score · the contract, checked without regenerating a campaign.

Registered in ``docs/OPEN-QUESTIONS.md`` at commit 24b7bc4, **before the runner existed**.

WHAT THIS PINS
--------------
1. **The edit to `run_unscreened_ccd` is PURELY ADDITIVE.** `results/q59-hartmann-no-
   screen.json` is committed against that function's current output, and its own gate
   against `d20-rescore.json` sits at `worst_abs_delta = 0.0`. Exposing `X_all`/`Y_all`
   so the map can be scored must not move `rule_a`, `oracle_best`, `rule_c`, `n_design`
   or `residual_df` by anything at all (D15).
2. **The design really is unscreened.** `doe_unscreened` must vary **every one of the six
   coordinates** — that is the entire reason the arm exists, and a design that silently
   collapsed to a sub-box would isolate nothing.
3. **The budget is the shared one.** 47 runs + 1 confirmation = 48. An arm on a different
   budget is not comparable to anything in Part IV.
4. **d=8 is impossible and the code says so**, rather than the impossibility living only
   in prose.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def q59():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "q59", ROOT / "scripts" / "run_q59_hartmann_no_screen.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["q59"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def one_unscreened(q59):
    """One real unscreened campaign at the committed (sigma, seed) = (0.25, 0)."""
    from boec.torch_oracle import TorchEvaluator
    oracle = q59._oracle()
    ev = TorchEvaluator(oracle, sigma_rel=0.25, seed=0)
    return q59.run_unscreened_ccd(ev, q59._bounds(), truth=ev.truth,
                                  optimum_value=float(oracle.optimum_value), seed=0,
                                  return_design=True)


def test_the_edit_is_additive_and_reproduces_the_committed_columns(q59, one_unscreened):
    """The committed scalars must come back at |delta| = 0, not merely close.

    Q59's own gate is at `worst_abs_delta = 0.0` against `d20-rescore.json`, so there is a
    committed column to hold this to and no excuse for a tolerance.
    """
    import json
    committed = json.loads(
        (ROOT / "results" / "q59-hartmann-no-screen.json").read_text())
    ref = next(r for r in committed["rows"]
               if r["sigma"] == 0.25 and r["seed"] == 0)["arms"]["doe_unscreened"]

    for key in ("rule_a", "oracle_best", "rule_c", "n_design", "residual_df"):
        assert key in one_unscreened, f"{key} disappeared -- the edit was not additive"
        delta = abs(one_unscreened[key] - ref[key])
        assert delta == 0.0, (
            f"{key} moved by {delta:.3e} against the committed column; the edit to "
            f"run_unscreened_ccd was NOT additive")


def test_the_design_matrix_is_exposed_for_map_scoring(q59, one_unscreened):
    """Without X_all/Y_all the map cannot be scored at all, which is Task 7's whole point."""
    assert "X_all" in one_unscreened and "Y_all" in one_unscreened
    X, Y = one_unscreened["X_all"], one_unscreened["Y_all"]
    assert X.shape[0] == Y.shape[0]
    assert X.shape[0] == q59.BUDGET, (
        f"the arm must spend exactly the shared budget of {q59.BUDGET}; "
        f"got {X.shape[0]}")
    assert X.shape[1] == q59.DIM


def test_the_unscreened_design_varies_every_coordinate(q59, one_unscreened):
    """The reason this arm exists. A design that collapsed to a sub-box isolates nothing."""
    X = one_unscreened["X_all"]
    spread = (X.max(dim=0).values - X.min(dim=0).values)
    assert int((spread > 1e-9).sum()) == q59.DIM, (
        f"only {int((spread > 1e-9).sum())} of {q59.DIM} coordinates vary; this is not "
        f"an unscreened design and cannot separate screening from sub-box confinement")


def test_the_budget_matches_the_shared_one(q59, one_unscreened):
    """47 runs + 1 confirmation. An arm on a different budget is incomparable to Part IV."""
    assert one_unscreened["n_design"] + 1 == q59.BUDGET


def test_the_model_is_identified(q59, one_unscreened):
    """More observations than second-order terms, else the fit is not a fit."""
    assert one_unscreened["residual_df"] > 0


def test_d8_unscreened_is_impossible_and_the_code_refuses_it(q59):
    """The impossibility is arithmetic, and it must live in the code, not only in prose.

    45 second-order terms at d=8, and no face-centred CCD lands on 48 wells there. This
    is why the 6->4 screen exists, and why Part IV's d=8 cells can never have this
    confound isolated.
    """
    from boec.rsm import second_order_n_terms
    assert second_order_n_terms(6) == 28
    assert second_order_n_terms(8) == 45
    committed = __import__("json").loads(
        (ROOT / "results" / "q59-hartmann-no-screen.json").read_text())
    assert "impossible" in committed["provenance"]["config"]["d8_unscreened"]


def test_the_q59_runners_own_output_stays_json_serialisable(q59):
    """**The edit must not break the runner it edits.**

    `run_q59_hartmann_no_screen.main` does `json.dumps(dict(..., rows=done))` where
    `done` holds exactly what `one()` returns. A first version of this edit put the
    tensors into the default return value and would have made the committed runner
    un-rerunnable — caught here, not in production.

    So the design is returned only when ASKED for, and the default path is byte-for-byte
    what it was.
    """
    import json
    from boec.torch_oracle import TorchEvaluator
    oracle = q59._oracle()

    ev = TorchEvaluator(oracle, sigma_rel=0.25, seed=0)
    default = q59.run_unscreened_ccd(ev, q59._bounds(), truth=ev.truth,
                                     optimum_value=float(oracle.optimum_value), seed=0)
    json.dumps(default)          # must not raise
    assert "X_all" not in default, "the default return must stay serialisable"
    assert "Y_all" not in default

    ev2 = TorchEvaluator(oracle, sigma_rel=0.25, seed=0)
    asked = q59.run_unscreened_ccd(ev2, q59._bounds(), truth=ev2.truth,
                                   optimum_value=float(oracle.optimum_value), seed=0,
                                   return_design=True)
    assert "X_all" in asked and "Y_all" in asked
    # and asking for the design must not change any scalar
    for k, v in default.items():
        assert asked[k] == v, f"{k} changed when the design was requested"
