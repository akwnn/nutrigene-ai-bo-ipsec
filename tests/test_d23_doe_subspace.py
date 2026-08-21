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
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_d23_doe_subspace.py"

DIM, SIGMA, ARM = 6, 0.25, "doe"


def _load():
    """Import the runner by path.

    Registered in `sys.modules` before `exec_module`, which is not optional here: the
    runner declares a `@dataclass` under `from __future__ import annotations`, so
    `dataclasses` resolves the string annotations through `sys.modules[cls.__module__]`
    and raises `AttributeError: 'NoneType' object has no attribute '__dict__'` for a
    module that was never registered.
    """
    spec = importlib.util.spec_from_file_location("d23_doe_subspace", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
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
    pinned = d23.pin(grid, held)

    r = d23.restricted_argmax(predict, pinned, predict(pinned).reshape(-1), kept, held,
                              d23.unit_bounds(6))

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
    held = {1: 0.2, 4: 0.2}
    pinned = d23.pin(grid, held)
    full = d23.full_argmax(predict, grid, predict(grid).reshape(-1), bounds)
    sub = d23.restricted_argmax(predict, pinned, predict(pinned).reshape(-1),
                                (0, 2, 3, 5), held, bounds)
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


# --------------------------------------------------------------------------------------
# 4 — AMENDMENT F1: EVERY CONTRAST AT BOTH UNITS, n=25 GOVERNING
# --------------------------------------------------------------------------------------
#
# Two seeds on one landscape share the landscape, so `(instance, seed)` is not 50
# independent units. F1 requires both: n=50 as briefed, and n=25 with seeds averaged
# within instance FIRST and the paired test run on the 25 instance-level differences.
# Where they disagree the n=25 answer is the verdict and n=50 is reported beside it,
# labelled as the anti-conservative unit.
#
# The design here is balanced -- 25 instances x exactly 2 seeds, asserted below -- and
# that has a consequence worth pinning rather than discovering later: the MEAN is
# identical at both units, because averaging 25 two-element means is the same arithmetic
# as averaging 50 values. So the registered decision rule, which compares a mean against
# two anchors, cannot change between units. What changes is the interval around it and
# the Wilcoxon p. A test that let those two facts drift apart would let someone read a
# "unit disagreement" that is arithmetically impossible.

def test_the_design_is_balanced_25_instances_by_2_seeds():
    """F1's unit change assumes this. If it ever stops being true, the means diverge."""
    import collections
    counts = collections.Counter(i for (i, _s) in _e2_doe())
    assert len(counts) == 25, counts
    assert set(counts.values()) == {2}, counts


def test_instance_level_averages_seeds_before_differencing(d23):
    """Seeds averaged FIRST, then the difference. Not the mean of seed-level differences.

    On a balanced design the two orders agree, which is exactly why the test uses an
    UNBALANCED fixture: differencing first and averaging after is a different estimator
    the moment the seed counts differ, and the registered wording says average first.
    """
    values = {("i0", 0): 1.0, ("i0", 1): 3.0, ("i1", 0): 10.0}
    got = d23.instance_level(values)
    assert sorted(got) == ["i0", "i1"]
    assert got["i0"] == 2.0
    assert got["i1"] == 10.0


def test_dual_contrast_reports_both_units_with_n25_governing(d23):
    keys = [(f"i{i:02d}", s) for i in range(25) for s in (0, 1)]
    a = {k: 0.30 for k in keys}
    b = {k: 0.10 for k in keys}
    out = d23.dual_contrast("a - b", a, b, keys)

    assert out["n50"]["n"] == 50
    assert out["n25"]["n"] == 25
    assert out["governing_unit"] == "n25"
    # Balanced design: the mean is unit-invariant. The interval need not be.
    assert out["n50"]["mean_diff"] == pytest.approx(out["n25"]["mean_diff"], abs=1e-12)
    assert out["n50"]["mean_diff"] == pytest.approx(0.20, abs=1e-12)


def test_the_decision_is_reported_at_both_units(d23):
    """Four cells: {n=50, n=25} x {rule-A anchor 0.0958, full-space anchor 0.1993}."""
    rows = [{"instance": f"i{i:02d}", "seed": s,
             "regret_a": 0.0958, "regret_p_full": 0.1993, "regret_p_sub": 0.1990,
             "regret_p_full_grid": 0.20, "regret_p_sub_grid": 0.20,
             "from_grid_full": False, "from_grid_sub": False,
             "gate_abs_delta": 0.0}
            for i in range(25) for s in (0, 1)]
    d = d23.analyse(rows)["decision"]

    assert set(d["cells"]) == {"n50", "n25"}
    for unit in ("n50", "n25"):
        cell = d["cells"][unit]
        assert cell["distance_to_rule_a"] == pytest.approx(0.1032, abs=1e-4)
        assert cell["distance_to_rule_p_full"] == pytest.approx(0.0003, abs=1e-4)
        assert cell["stays_at_full_space"] is True
        assert cell["recovers_to_rule_a"] is False
    assert d["verdict"] == "D20_STANDS"
    assert d["governing_unit"] == "n25"
    assert d["units_agree"] is True
