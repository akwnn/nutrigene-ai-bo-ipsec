"""Q28 — the DoE arm's scoring rule, and how much of the E2 headline rests on it.

Reproduces the table in `docs/OPEN-QUESTIONS.md` Q28. Reproduce with
`python scripts/diagnostic_doe_scoring.py`; log at `results/doe-scoring.log`.

**NOTHING HERE CHANGES ANY E2 NUMBER.** It re-scores stored runs under a second
rule and prints both. `e2.yaml`'s registered rule is untouched, and the script
asserts the regenerated arm reproduces `results/e2-grid.json` before printing
anything — if it does not, these are different runs and the comparison is void.

------------------------------------------------------------------------------
THE TWO RULES
------------------------------------------------------------------------------

  Rule A   best-so-far over all 48 measurements.  What run_e2.py:120 scores.
           Defence: a practitioner walks away with the best recipe they saw.

  Rule B   the stage-4 confirmation recipe.  What the method PRODUCES.
           Defence: doe.py -- "The published study evaluated its predicted
           optimum. So does this." Stage 4 exists for precisely this reason.

Both are defensible; `e2.yaml` registers neither; and they disagree in SIGN at
every cell. That is the finding.

------------------------------------------------------------------------------
WHY RULE B AS PRINTED HERE IS NOT A VERDICT
------------------------------------------------------------------------------

It scores the DoE arm at its model's recommendation and qLogEI at its best
measurement. For a BO arm the best measured point genuinely IS its answer, so
the asymmetry is not obviously wrong -- but it is an asymmetry, and it runs
entirely against DoE.

The symmetric comparison scores every arm at its own recommended recipe, which
for a BO arm is the posterior-mean argmax of its final surrogate. **That number
does not exist anywhere in this project.** Producing it is a new experiment and
needs registering first, because Rule A is already known to favour DoE and
asymmetric Rule B is already known to favour BO -- so whoever runs it knows in
advance which way each error points.

This script therefore prints Rule B and labels it, rather than concluding from
it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))

from boec.diagnostics import instance_bootstrap    # noqa: E402
from boec.doe import run_doe_arm                   # noqa: E402
from boec.oracles import load_ensemble             # noqa: E402
from boec.torch_oracle import BiphasicOracle       # noqa: E402
from run_e2 import (                               # noqa: E402
    BUDGET, N_INSTANCES, N_SEEDS, SIGMAS, scored_curve, unit_bounds,
)

GRID = Path("results/e2-grid.json")
DIMS = (6, 8)


def rescore(dim, stored):
    """Re-run the DoE arm at `dim`, recording both scoring rules.

    The regenerated Rule A regret must match the stored row exactly or the two
    rules are being compared across different runs.
    """
    ens = load_ensemble(dim=dim)[:N_INSTANCES]
    bounds = unit_bounds(dim)
    out, worst = [], 0.0
    for sigma in SIGMAS:
        for inst in ens:
            for seed in range(N_SEEDS):
                o = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
                r = run_doe_arm(o, bounds, truth=o.truth, budget=BUDGET, seed=seed)
                curve = scored_curve(o, r.X_visited, r.Y_visited)
                rule_a = float(inst.optimum_value - curve[-1])
                # over_prediction is measured AT the confirmation point, so the
                # truth there is predicted_y - over_prediction by definition.
                conf_true = float(r.predicted_y - r.over_prediction)
                key = (inst.instance_id, sigma, seed, "doe")
                if key in stored:
                    worst = max(worst, abs(rule_a - stored[key]["regret"]))
                out.append(dict(instance=inst.instance_id, dim=dim, sigma=sigma,
                                seed=seed, rule_a=rule_a,
                                rule_b=float(inst.optimum_value - conf_true),
                                over_prediction=r.over_prediction))
    return out, worst


def per_instance(rows, sigma, key, insts):
    """One number per instance, averaged over seeds. Effective n = 25, not 50."""
    return np.array([np.mean([r[key] for r in rows
                              if r["sigma"] == sigma and r["instance"] == i])
                     for i in insts])


def main() -> None:
    grid = json.loads(GRID.read_text())
    print("Q28 — the DoE arm's scoring rule\n"
          "Rule A: best-so-far over all 48 (registered by omission).\n"
          "Rule B: the stage-4 recipe, i.e. what the method produces.\n"
          "Rule B here is NOT like-for-like — see the module docstring.\n")

    print(f"{'d':>2} {'sigma':>6} {'DoE rule A':>11} {'DoE rule B':>11} "
          f"{'qLogEI':>8} {'A − qLogEI':>22} {'B − qLogEI':>22} {'over-pred':>10}")

    for dim in DIMS:
        stored = {(r["instance"], r["sigma"], r["seed"], r["arm"]): r
                  for r in grid if r["dim"] == dim}
        rows, worst = rescore(dim, stored)
        if dim == 6:      # d=8 has no stored doe rows; d=6 does, so it can be checked
            assert worst <= 1e-9, (
                f"regenerated d=6 DoE arm differs from results/e2-grid.json by "
                f"{worst:.3e} — these are different runs and the comparison is void"
            )
        for sigma in SIGMAS:
            insts = sorted({r["instance"] for r in rows if r["sigma"] == sigma})
            q = np.array([np.mean([stored[(i, sigma, s, "qlogei")]["regret"]
                                   for s in range(N_SEEDS)]) for i in insts])
            a = per_instance(rows, sigma, "rule_a", insts)
            b = per_instance(rows, sigma, "rule_b", insts)
            cells = []
            for arr in (a, b):
                d = arr - q
                m, lo, hi = instance_bootstrap(d, n_boot=2000)
                cells.append(f"{m:+.4f} p={wilcoxon(d).pvalue:.5f}")
            op = np.median([r["over_prediction"] for r in rows
                            if r["sigma"] == sigma])
            print(f"{dim:>2} {sigma:>6} {a.mean():>11.4f} {b.mean():>11.4f} "
                  f"{q.mean():>8.4f} {cells[0]:>22} {cells[1]:>22} {op:>+10.4f}")
        if dim == 6:
            print(f"   (d=6 fidelity vs results/e2-grid.json: max |delta| "
                  f"{worst:.3e} over 100 rows)")

    print("\nEvery cell reverses in sign. The registered rule is the generous one "
          "for the\narm that wins under it. See Q28 for what a symmetric "
          "comparison would require.")


if __name__ == "__main__":
    main()
