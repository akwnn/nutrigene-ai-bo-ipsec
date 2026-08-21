"""D23-RESCORE — is `doe`'s rule-P collapse the design, or a BoTorch prior?

Registered in `docs/OPEN-QUESTIONS.md` (commit 5c44e6a) **before**
`scripts/run_d23_doe_subspace.py` existed.

WHAT IS BEING SEPARATED
-----------------------
D20: under a posterior-mean terminal rule `doe` goes 0.0958 -> 0.1993, first of ten to
last. D23's third caveat: `doe`'s posterior on its **two screened-out axes** is
prior-driven — the likelihood is flat there, so the lengthscale reverts to the prior mode
0.5016. A rule that takes an unconstrained argmax over all six axes is therefore free to
walk off into two directions the CCD never varied, guided by a prior. Restricting the
argmax to the four kept factors, with the two dropped ones held where the screen held
them, asks how much of the collapse that accounts for.

THE THREE THINGS THESE TESTS PIN
---------------------------------
1. **The registered gate.** Rule A must reproduce `e2-grid.json · doe` at |delta| = 0.
   Everything else is uninterpretable without it.
2. **The subspace is really the subspace.** The nominated point must sit *exactly* on
   `dropped_held_at` in every dropped coordinate. An embedding that scattered the
   dropped axes by 1e-9 would answer a different question and still look right in a
   summary table.
3. **The locator is Fix 1's locator.** The full-space arm recomputed here must return
   `fix1-terminal-rule.json`'s committed `regret_p` for `doe`. If it does not, the
   subspace number beside it is not commensurable with D20's, and the whole comparison
   is between two different rules rather than two different search regions (D12).

The synthetic case in `test_restricted_argmax_finds_the_constrained_optimum` exists
because 2 and 3 are both *measured* on a GP whose optimum nobody knows. On a quadratic
the constrained optimum is closed-form, so an embedding bug has nowhere to hide.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_d23_doe_subspace.py"

DIM, SIGMA, ARM = 6, 0.25, "doe"


def _load():
    spec = importlib.util.spec_from_file_location("d23_doe_subspace", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def d23():
    return _load()


def _e2_doe() -> dict[tuple[str, int], float]:
    rows = json.loads((ROOT / "results" / "e2-grid.json").read_text())
    return {(r["instance"], int(r["seed"])): float(r["regret"]) for r in rows
            if r["arm"] == ARM and r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12}


def _fix1_doe() -> dict[tuple[str, int], dict]:
    rows = json.loads((ROOT / "results" / "fix1-terminal-rule.json").read_text())["rows"]
    return {(r["instance"], int(r["seed"])): r for r in rows if r["arm"] == ARM}


# --------------------------------------------------------------------------------------
# 1 — THE REGISTERED GATE
# --------------------------------------------------------------------------------------

def test_rule_a_reproduces_the_committed_doe_regret_exactly():
    """|delta| = 0 on the committed column, as Fix 1 did on all 500 rows."""
    d23 = _load()
    committed = _e2_doe()
    assert len(committed) == 50, f"expected 50 committed doe rows, found {len(committed)}"

    for key in sorted(committed)[:3]:
        rec = d23.regenerate_doe(*key)
        assert rec.regret == committed[key], (
            f"{key}: regenerated {rec.regret!r} != committed {committed[key]!r}")
        assert rec.kept_factors is not None and len(rec.kept_factors) == 4
        assert rec.dropped_held_at is not None and len(rec.dropped_held_at) == 2


# --------------------------------------------------------------------------------------
# 2 — THE SUBSPACE IS REALLY THE SUBSPACE
# --------------------------------------------------------------------------------------

def test_restricted_argmax_finds_the_constrained_optimum():
    """A quadratic whose free optimum is outside the pinned slice. Closed-form answer.

    The unconstrained maximum sits at 0.9 on every axis. Pinning axes 1 and 4 to 0.2
    moves the constrained maximum to 0.9 on the four kept axes and *exactly* 0.2 on the
    two dropped ones — and its value drops by the two pinned quadratic terms. Both are
    checked, because an embedding that silently optimised all six would land on 0.9
    everywhere and score higher, which is the failure this whole task is about.
    """
    d23 = _load()
    peak = torch.full((6,), 0.9, dtype=torch.double)

    def predict(Z: torch.Tensor) -> torch.Tensor:
        return -((Z.double() - peak) ** 2).sum(-1, keepdim=True)

    held = {1: 0.2, 4: 0.2}
    kept = (0, 2, 3, 5)
    grid = torch.rand(512, 6, generator=torch.Generator().manual_seed(0),
                      dtype=torch.double)

    r = d23.restricted_argmax(predict, grid, kept, held, d23.unit_bounds(6))

    assert float(r.x[1]) == 0.2 and float(r.x[4]) == 0.2, r.x
    for j in kept:
        assert abs(float(r.x[j]) - 0.9) < 1e-5, r.x
    assert abs(r.value - float(predict(r.x.reshape(1, -1)))) < 1e-12
    assert abs(r.value - (-2 * (0.9 - 0.2) ** 2)) < 1e-8, r.value


def test_restricted_argmax_cannot_beat_the_unrestricted_one(d23):
    """The pinned slice is a subset of the box, so its maximum cannot be higher."""
    peak = torch.full((6,), 0.9, dtype=torch.double)

    def predict(Z: torch.Tensor) -> torch.Tensor:
        return -((Z.double() - peak) ** 2).sum(-1, keepdim=True)

    grid = torch.rand(512, 6, generator=torch.Generator().manual_seed(0),
                      dtype=torch.double)
    bounds = d23.unit_bounds(6)
    full = d23.full_argmax(predict, grid, predict(grid).reshape(-1), bounds)
    sub = d23.restricted_argmax(predict, grid, (0, 2, 3, 5), {1: 0.2, 4: 0.2}, bounds)
    assert sub.value <= full.value + 1e-12


def test_the_pin_lands_on_the_screens_own_hold_value(d23):
    """On a real campaign, not a fixture: every dropped axis is bitwise its hold value."""
    key = sorted(_e2_doe())[0]
    out = d23.score_campaign(*key)
    held = out["dropped_held_at"]
    x = out["x_p_sub"]
    assert set(held) == set(out["dropped_factors"])
    for j, v in held.items():
        assert x[int(j)] == v, f"axis {j}: nominated {x[int(j)]!r}, screen held {v!r}"
    assert len(out["kept_factors"]) == 4


# --------------------------------------------------------------------------------------
# 3 — THE LOCATOR IS FIX 1's LOCATOR
# --------------------------------------------------------------------------------------

@pytest.mark.slow
def test_full_space_rule_p_reproduces_fix1(d23):
    """Recomputed full-space rule P must be the committed `fix1-terminal-rule.json` one.

    This is what makes the subspace number a comparison of **search regions**. If the
    full-space arm drifts, the contrast is between two different terminal rules and the
    registered decision rule is answering a different question.
    """
    committed = _fix1_doe()
    assert len(committed) == 50

    for key in sorted(committed)[:2]:
        out = d23.score_campaign(*key)
        ref = committed[key]
        assert out["regret_p_full"] == ref["regret_p"], (
            f"{key}: recomputed {out['regret_p_full']!r} != committed "
            f"{ref['regret_p']!r} (|delta| = "
            f"{abs(out['regret_p_full'] - ref['regret_p']):.3e})")
        assert out["regret_p_full_grid"] == ref["regret_p_grid"]
        assert out["regret_a"] == ref["regret_a"]
