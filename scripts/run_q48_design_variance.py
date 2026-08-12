"""Q48 — E2's static arms share ONE design across all 25 instances, and it was a good one.

    python scripts/run_q48_design_variance.py    # log at results/q48-design-variance.log

FOUND BY ACCIDENT, WHILE BUILDING SOMETHING ELSE
------------------------------------------------
Q47 needed a single-tier LHS+GP baseline. Built with a per-instance design seed it scored
0.1778 at d=6 sigma=0.25, against the 0.1270 `results/e2-grid.json` reports for the `lhs`
arm at the same cell. Same code path, same instances, same noise draws. The only
difference was the design seed.

THE MECHANISM
-------------
`runner.static_design(bounds, method, budget, seed)` takes no instance argument. So at a
given seed **every instance in the cell is scored on the identical point set**, and a
cell with 2 seeds contains exactly **2 distinct designs across all 50 runs** -- not 50.

Two consequences, and the second is the serious one.

1. The reported mean is conditioned on those two draws rather than averaged over the
   design distribution.
2. `instance_bootstrap` resamples the 25 instances as if they were independent. They are
   not: they share a design, so the design component of variance is **invisible to every
   confidence interval this project reports for a static arm.**

The adaptive arms do not have this problem in the same degree. qLogEI shares only its
2d+2 opening batch and then chooses every later point from that instance's own data.

WHAT THIS SCRIPT MEASURES
-------------------------
The design distribution itself: draw `N_DESIGNS` designs, and for each one score the
whole cell exactly as E2 does. That gives the mean E2 *should* report, the SD across
designs, and the percentile E2's actual draw sits at.

**Nothing here needs a GP.** Static arms are design + evaluate + reported-best, so the
whole sweep is seconds. That it was never run is the point: it is cheap and it was not
cheap to not know.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import warnings

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.diagnostics import reported_best_curve                   # noqa: E402
from boec.oracles import load_ensemble                             # noqa: E402
from boec.runner import static_design                              # noqa: E402
from boec.torch_oracle import BiphasicOracle                       # noqa: E402

BUDGET, N_INSTANCES, SEEDS = 48, 25, (0, 1)
N_DESIGNS = 60
CELLS = ((6, 0.25), (6, 0.10), (8, 0.25), (8, 0.10))
ARMS = ("lhs", "sobol", "random")
RULE = "=" * 100


def cell_mean(ens, bounds, sigma: float, method: str, design_seed: int) -> float:
    """Mean regret over the cell when EVERY instance is scored on one shared design."""
    X = static_design(bounds, method, BUDGET, design_seed)
    out = []
    for inst in ens:
        for s in SEEDS:
            o = BiphasicOracle(inst, sigma_rel=sigma, seed=s)
            Y, _ = o.evaluate(X)
            out.append(float(inst.optimum_value)
                       - float(reported_best_curve(o.truth(X), Y)[-1]))
    return float(np.mean(out))


def main() -> None:
    grid = json.loads((ROOT / "results" / "e2-grid.json").read_text())
    out = []
    print(f"{RULE}\nQ48 — the design distribution E2's static arms never averaged over"
          f"\n{RULE}")
    print(f"  {N_DESIGNS} designs per arm per cell. E2 uses the designs at seeds "
          f"{SEEDS} and no others.\n")
    for dim, sigma in CELLS:
        ens = load_ensemble(dim=dim)[:N_INSTANCES]
        bounds = torch.stack([torch.zeros(dim, dtype=torch.double),
                              torch.ones(dim, dtype=torch.double)])
        print(f"  d={dim} sigma_rel={sigma}")
        print(f"    {'arm':<8}{'E2 reports':>12}{'design-averaged':>18}"
              f"{'sd':>9}{'pctile of E2':>15}{'shift':>10}")
        for arm in ARMS:
            reported = [r["regret"] for r in grid
                        if r["dim"] == dim and abs(r["sigma"] - sigma) < 1e-12
                        and r["arm"] == arm]
            if not reported:
                continue
            e2 = float(np.mean(reported))
            draws = np.array([cell_mean(ens, bounds, sigma, arm, g)
                              for g in range(N_DESIGNS)])
            pct = 100.0 * float((draws < e2).mean())
            print(f"    {arm:<8}{e2:>12.4f}{draws.mean():>18.4f}{draws.std():>9.4f}"
                  f"{pct:>14.0f}%{draws.mean() - e2:>+10.4f}")
            out.append(dict(dim=dim, sigma=sigma, arm=arm, e2_reported=e2,
                            design_averaged=float(draws.mean()),
                            design_sd=float(draws.std()),
                            percentile_of_e2=pct, n_designs=N_DESIGNS,
                            draws=draws.tolist()))
        # what it does to the one comparison the paper leans on
        q = [r["regret"] for r in grid if r["dim"] == dim
             and abs(r["sigma"] - sigma) < 1e-12 and r["arm"] == "qlogei"]
        row = next((o for o in out if o["dim"] == dim and o["sigma"] == sigma
                    and o["arm"] == "lhs"), None)
        if q and row:
            qm = float(np.mean(q))
            print(f"      qLogEI {qm:.4f}  vs lhs as reported {row['e2_reported']:.4f} "
                  f"({'lhs' if row['e2_reported'] < qm else 'BO'} ahead by "
                  f"{abs(qm - row['e2_reported']):.4f})")
            print(f"      qLogEI {qm:.4f}  vs lhs design-averaged "
                  f"{row['design_averaged']:.4f} "
                  f"({'lhs' if row['design_averaged'] < qm else 'BO'} ahead by "
                  f"{abs(qm - row['design_averaged']):.4f})")
        print()
    (ROOT / "results" / "q48-design-variance.json").write_text(json.dumps(out, indent=1))
    print(f"{RULE}\n  A static arm's CI in this project is a within-design interval. The\n"
          f"  design component is not in it, because all 25 instances share the design.\n"
          f"{RULE}")


if __name__ == "__main__":
    main()
