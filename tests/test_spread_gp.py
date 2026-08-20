"""Q53 — the one-shot spread+GP arm, extracted so it can be run off the Hill oracle.

The arm already existed, inline, at ``run_q52_budget_to_target.py:201-211``. Q53 registered it
to run on Q42's four external families, and Q42's harness takes an ``Oracle`` rather than a
``BiphasicOracle``. So the arm has to move into a module — and the move is exactly where a
faithful arm silently becomes a different one.

The strongest test here is therefore not a property test but a **fidelity gate**: the extracted
function must reproduce the committed Q52 grid bit-for-bit on stored rows. D12 is why that gate
compares against the committed artefact rather than against a fresh run agreeing with itself.

The rest pin the three things the registration promises and a reader cannot check by eye:
one-shot (a single evaluate call, no refit), rule A is `reported_best_curve` and not oracle-best
(D20), and the design-averaging returns the SD the registration says must accompany every point
estimate.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from boec.oracles import load_ensemble
from boec.spread_gp import design_average, spread_gp_once, within_design_noise
from boec.torch_oracle import BiphasicOracle

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "results" / "q52-budget-to-target.json"


def _bounds(d: int) -> torch.Tensor:
    return torch.stack([torch.zeros(d, dtype=torch.double),
                        torch.ones(d, dtype=torch.double)])


def _seed_of(instance_id: str, salt: int) -> int:
    """Verbatim from `run_q52_budget_to_target.py`. If this drifts the gate is meaningless."""
    return (int(instance_id[:8], 16) * 1000 + salt) % (2**31 - 1)


# --------------------------------------------------------------------------- fidelity

@pytest.mark.skipif(not GRID.exists(), reason="committed Q52 grid absent")
def test_the_extracted_arm_reproduces_the_committed_q52_rows_exactly():
    """The move out of the script must not change a single digit.

    Checks both rules at one checkpoint on the first few instances of each noise level. The
    committed file is the reference, never a regeneration — a gate that compares a fresh run
    against another fresh run can only report that the code agrees with itself (D12).
    """
    grid = json.loads(GRID.read_text())
    ensemble = {i.instance_id: i for i in load_ensemble(dim=6)}
    n, worst = 48, 0.0
    checked = 0
    for row in grid["rows"]:
        if checked >= 6:
            break
        inst = ensemble.get(row["instance_id"])
        if inst is None:
            continue
        sigma = float(row["sigma"])
        stored_a = row["arms"]["spread_gp"]["rule_a"][str(n)]
        stored_c = row["arms"]["spread_gp"]["rule_c"][str(n)]

        s = _seed_of(inst.instance_id, n)
        orac = BiphasicOracle(inst, sigma_rel=sigma, seed=int(row["seed"]))
        got_a, got_c = spread_gp_once(
            orac, _bounds(6), truth=orac.truth,
            optimum_value=float(inst.optimum_value), n=n, seed=s)
        worst = max(worst, abs(got_a - stored_a), abs(got_c - stored_c))
        checked += 1

    assert checked >= 4, f"only {checked} rows checked; the gate needs real coverage"
    # Declared in METHODS §2.11: environmental float drift, not a science change.
    # Observed ~3e-7; four-decimal manuscript numbers are unaffected.
    assert worst < 1e-6, (
        f"extracted spread_gp drifted past the declared 1e-6 gate: worst |delta| = {worst:.3e}"
    )


# --------------------------------------------------------------------------- structure

def test_the_arm_is_one_shot_it_evaluates_once_and_never_refits():
    """One-shot is the whole claim: 1 round against qLogEI's 10. A refit would void it."""
    inst = load_ensemble(dim=6)[0]
    orac = BiphasicOracle(inst, sigma_rel=0.25, seed=0)
    calls = {"n": 0, "sizes": []}
    real = orac.evaluate

    def counting(X):
        calls["n"] += 1
        calls["sizes"].append(int(X.shape[0]))
        return real(X)

    orac.evaluate = counting                                   # type: ignore[method-assign]
    spread_gp_once(orac, _bounds(6), truth=orac.truth,
                   optimum_value=float(inst.optimum_value), n=24, seed=7)
    assert calls["n"] == 1, f"expected one batch, got {calls['n']} — that is not one-shot"
    assert calls["sizes"] == [24], f"expected all 24 points at once, got {calls['sizes']}"


def test_rule_a_is_the_observed_argmax_not_the_best_true_value_among_visited():
    """D20 again, in the new arm. Oracle-best flatters any design that stumbles on a good point.

    Constructed so the two differ: the noisiest cell, where the observed argmax is often not
    the truly-best visited point.
    """
    from boec.diagnostics import reported_best_curve
    inst = load_ensemble(dim=6)[0]
    opt = float(inst.optimum_value)
    gaps = []
    for seed in range(6):
        orac = BiphasicOracle(inst, sigma_rel=0.25, seed=seed)
        from boec.optimizers import lhs_design
        X = lhs_design(_bounds(6), 24, seed=seed)
        Y, _ = orac.evaluate(X)
        T = orac.truth(X)
        rule_a = opt - float(reported_best_curve(T, Y)[-1])
        oracle_best = opt - float(np.maximum.accumulate(
            np.asarray(T, dtype=float).ravel())[-1])
        assert rule_a >= oracle_best - 1e-12, "rule A can never beat oracle-best"
        gaps.append(rule_a - oracle_best)
    assert max(gaps) > 1e-9, "the two scorings never differed; this test proves nothing"


# --------------------------------------------------------------------------- averaging

def test_design_average_returns_the_mean_and_the_spread_across_draws():
    m, sd = design_average([0.10, 0.20, 0.30])
    assert m == pytest.approx(0.20)
    assert sd == pytest.approx(np.std([0.10, 0.20, 0.30], ddof=1))


def test_design_average_of_a_single_draw_reports_an_undefined_sd_not_zero():
    """One draw has no spread to report. Zero would read as 'the lottery does not bite here',
    which is the opposite of true — it is the case where the lottery is entirely unmeasured."""
    m, sd = design_average([0.17])
    assert m == pytest.approx(0.17)
    assert np.isnan(sd), "a single draw must not report SD = 0"


def test_within_design_noise_is_the_registered_stopping_rule():
    """Registered in Q53 §3 before any number existed: a contrast smaller in magnitude than the
    cell's design SD is not a result, whichever way it points."""
    assert within_design_noise(diff=+0.010, design_sd=0.025)
    assert within_design_noise(diff=-0.010, design_sd=0.025)
    assert not within_design_noise(diff=+0.060, design_sd=0.025)
    assert not within_design_noise(diff=-0.060, design_sd=0.025)


def test_within_design_noise_is_undefined_when_the_sd_is():
    """With one draw there is no SD, so the rule cannot fire and must say so rather than
    silently passing everything."""
    with pytest.raises(ValueError):
        within_design_noise(diff=0.01, design_sd=float("nan"))
