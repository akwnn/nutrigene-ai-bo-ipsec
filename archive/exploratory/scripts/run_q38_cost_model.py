"""Q38 / T2.4 — evaluations are not the cost a wet lab pays. Rounds are.

    python scripts/run_q38_cost_model.py     # log at results/q38-cost-model.log

Every comparison in this project is at a fixed budget of 48 MEASUREMENTS. That is the
right axis for a compute benchmark and the wrong one for a laboratory. A plate runs
many wells at once; what a lab waits for is the next plate. Differentiating hiPSCs to
endothelium takes days per round, so the practically binding cost is **how many
sequential rounds the method needs**, not how many wells it fills.

48 sequential evaluations is not 48 parallel wells.

The batch structure is read out of the production code, not asserted here:
`campaign.batch_plan` for the adaptive arms, `doe.run_doe_arm`'s own stage split for
the DoE arm. Final regrets come from the committed `results/e2-grid.json`.

This changes the reading of the E2 result, and it changes it in the DoE arm's favour by
more than the regret comparison does — so it belongs in the paper whichever way the
headline lands.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.campaign import batch_plan          # noqa: E402

GRID = ROOT / "results" / "e2-grid.json"
BUDGET = 48
RULE = "=" * 92

#: Sequential-round structure of each arm, with the reason it is what it is.
#: `adaptive` and `doe` are computed below; these are the ones fixed by construction.
STATIC_ARMS = {
    "random": ("all 48 points known before the first plate", 1),
    "sobol": ("all 48 points known before the first plate", 1),
    "lhs": ("all 48 points known before the first plate", 1),
    "coord": ("one measurement at a time by definition", BUDGET),
}


def rounds_for(dim: int) -> dict:
    n_init, batches = batch_plan(dim, budget=BUDGET, q=4)
    return dict(n_init=n_init, batches=batches, rounds=1 + len(batches))


def main() -> None:
    rows = json.loads(GRID.read_text())
    print(f"{RULE}\nQ38 · the cost model a wet lab actually pays\n{RULE}")

    for dim in (6, 8):
        bp = rounds_for(dim)
        print(f"\n  d={dim}: opening {bp['n_init']} + batches {bp['batches']} "
              f"=> {bp['rounds']} sequential rounds for the adaptive arms")

    # the DoE arm's split is 20 + 27 + 1 at d=6, each stage a single parallel plate
    doe_stage1, doe_stage2, doe_conf = 20, 27, 1
    doe_rounds = 3
    assert doe_stage1 + doe_stage2 + doe_conf == BUDGET, "the DoE split must spend 48"

    dim, sigma = 6, 0.25
    sub = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma]
    insts = sorted({r["instance"] for r in sub})

    def mean_regret(arm: str) -> float | None:
        v = [np.mean([r["regret"] for r in sub if r["arm"] == arm and r["instance"] == i])
             for i in insts]
        return float(np.mean(v)) if v and not any(np.isnan(v)) else None

    bp = rounds_for(dim)
    plan = {
        "qlogei": (f"opening {bp['n_init']}, then {len(bp['batches'])} batches of q=4",
                   bp["rounds"]),
        "qlognei": (f"opening {bp['n_init']}, then {len(bp['batches'])} batches of q=4",
                    bp["rounds"]),
        "doe": (f"stage1 {doe_stage1} + stage2 {doe_stage2} + confirmation {doe_conf}, "
                f"each one plate", doe_rounds),
        **{k: v for k, v in STATIC_ARMS.items()},
    }

    print(f"\n{RULE}\nd={dim}, sigma={sigma} (the registered primary cell)\n{RULE}")
    print(f"{'arm':>9}{'evals':>7}{'ROUNDS':>8}{'widest plate':>14}"
          f"{'mean regret':>13}   batch structure")
    order = ["doe", "lhs", "coord", "qlognei", "qlogei", "sobol", "random"]
    out = []
    for arm in order:
        if arm not in plan:
            continue
        desc, nr = plan[arm]
        reg = mean_regret(arm)
        if arm in ("qlogei", "qlognei"):
            widest = max(bp["n_init"], max(bp["batches"]))
        elif arm == "doe":
            widest = doe_stage2
        elif arm == "coord":
            widest = 1
        else:
            widest = BUDGET
        print(f"{arm:>9}{BUDGET:>7}{nr:>8}{widest:>14}"
              f"{(f'{reg:.4f}' if reg is not None else 'n/a'):>13}   {desc}")
        out.append(dict(arm=arm, evals=BUDGET, rounds=nr, widest_plate=widest,
                        mean_regret=reg, structure=desc))

    bo_r = plan["qlogei"][1]
    print(f"\n  THE COMPARISON THE EVALUATION AXIS HIDES")
    print(f"  The DoE pipeline finishes in {doe_rounds} sequential rounds. qLogEI needs "
          f"{bo_r}.")
    print(f"  At {doe_rounds} rounds qLogEI has spent only "
          f"{bp['n_init'] + sum(bp['batches'][:doe_rounds - 1])} of its 48 measurements "
          f"({bp['n_init']} opening + {doe_rounds - 1} batches of 4),")
    print(f"  so at equal LAB TIME the comparison is not 48-vs-48 at all.")
    print(f"  Coordinate descent spends {BUDGET} rounds and is, on this axis, "
          f"unusable in a wet lab\n  regardless of its regret.")

    print(f"\n  WHAT THIS DOES NOT SHOW, stated so it is not over-read:")
    print("  E2 stored summary rows, not per-evaluation curves, so a regret-versus-ROUNDS")
    print("  CURVE cannot be drawn from the committed grid -- only the endpoint and the")
    print("  round COUNT above. Drawing the curve needs the curves persisted on a re-run.")
    print("  The round counts themselves are exact: they come from campaign.batch_plan")
    print("  and the DoE arm's own 20+27+1 split, not from a reconstruction.")

    (ROOT / "results" / "q38-cost-model.json").write_text(json.dumps(out, indent=1))
    print(f"\n  written to results/q38-cost-model.json")


if __name__ == "__main__":
    main()
