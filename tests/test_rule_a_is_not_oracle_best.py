"""D20 — rule A must be the OBSERVED argmax, never the running best true value.

`DoEResult.curve_true` is ``np.maximum.accumulate`` over the **noiseless** values: the
running best *true* value among visited points. That is **oracle-best**. Rule A is the
true value at the running *observed* argmax — :func:`boec.diagnostics.reported_best_curve`
— and crediting an arm for a recipe it measured but could not identify is exactly the
error that voided E2's first run.

Three scripts read `curve_true` as though it were rule A
(`run_q35_constrained_rsm.py:178`, `run_q42_families.py:128`,
`run_q36_generality.py:111`). In Q42 the two arms end up on **different rules inside one
loop** — BO on `reported_best_curve`, DoE on `curve_true` — and the gap runs entirely in
DoE's favour: +0.0414 on Levy, +0.0438 on Rosenbrock, +0.0177 on Hartmann6.

Checked structurally rather than by running, so a divergence is caught even in a branch
no test exercises — the same approach as `tests/test_q29_locator.py`, and for the same
reason: this project has already shipped one scoring asymmetry.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import torch

from boec.diagnostics import reported_best_curve
from boec.doe import run_doe_arm
from boec.oracles import load_ensemble
from boec.torch_oracle import BiphasicOracle

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((ROOT / "scripts").glob("*.py"))

#: The one script allowed to read `curve_true`, because comparing the two scorings is
#: its entire purpose: it reports what D20 wrote alongside what rule A actually is.
#: Named rather than pattern-matched so that adding a second exemption is a visible edit.
ALLOWED = {"rescore_d20.py"}


def _uses_curve_true(path: Path) -> bool:
    """True if the module reads the ``curve_true`` attribute anywhere."""
    tree = ast.parse(path.read_text())
    return any(isinstance(n, ast.Attribute) and n.attr == "curve_true"
               for n in ast.walk(tree))


def test_no_script_scores_an_arm_from_curve_true():
    """`curve_true` is oracle-best. Any arm scored from it is not on rule A.

    The fix at each site is `reported_best_curve(truth(r.X_visited), r.Y_visited)[-1]`.
    """
    offenders = [p.name for p in SCRIPTS
                 if p.name not in ALLOWED and _uses_curve_true(p)]
    assert offenders == [], (
        "these scripts read DoEResult.curve_true, which is oracle-best and not rule A: "
        f"{offenders}"
    )


def test_the_exemption_list_does_not_cover_a_script_that_stopped_needing_it():
    """An allowlist that outlives its reason is how a guard quietly stops guarding."""
    stale = [n for n in ALLOWED if not _uses_curve_true(ROOT / "scripts" / n)]
    assert stale == [], f"these are exempted but no longer read curve_true: {stale}"


def test_oracle_best_and_rule_a_actually_differ_on_this_arm():
    """Guards the test above from becoming vacuous.

    If the two scorings agreed the AST rule would be pedantry. They do not: on the
    classical arm at d=6 sigma=0.25 they differ on nearly every run, and oracle-best is
    always the more flattering of the two.
    """
    bounds = torch.stack([torch.zeros(6, dtype=torch.double),
                          torch.ones(6, dtype=torch.double)])
    oracle_best, rule_a = [], []
    for inst in load_ensemble(dim=6)[:6]:
        for seed in (0, 1):
            o = BiphasicOracle(inst, sigma_rel=0.25, seed=seed)
            r = run_doe_arm(o, bounds, truth=o.truth, budget=48, seed=seed)
            opt = float(inst.optimum_value)
            oracle_best.append(opt - float(r.curve_true[-1]))
            rule_a.append(opt - float(
                reported_best_curve(o.truth(r.X_visited), r.Y_visited)[-1]))

    ob, ra = np.array(oracle_best), np.array(rule_a)
    # oracle-best can never carry MORE regret: it maximises over the same visited set
    # without having to identify the winner.
    assert np.all(ra >= ob - 1e-12)
    # and it is not a distinction without a difference
    assert (np.abs(ra - ob) > 1e-9).sum() >= len(ra) // 2
