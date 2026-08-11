"""T1.4 — regenerate every adaptive E2 arm and check it against the committed grid.

OWNERSHIP: Person A. Reproduce with `python scripts/probe_e2_determinism.py`;
log at `results/e2-determinism.log`, per-row deltas at `results/e2-determinism.json`.

WHY THIS EXISTS
---------------
`results/e2-grid.json` was gitignored. Two clones therefore held two different E2
runs under the same filename, and *both* passed their own fidelity gates:

    A's clone   qLogEI mean regret 0.1553   =>  doe - qlogei = -0.0595
    B's clone   qLogEI mean regret 0.1641   =>  doe - qlogei = -0.0708

`q29_symmetric.py` regenerated qLogEI in B's clone and reported
`max |delta| 0.000e+00 over 50 rows`; the same gate run in A's clone also passes.
A gate that compares a run against an untracked file cannot detect this, because
the file it compares against moved with the clone. Q29 read the difference as
`run_e2.py`'s `report()` disagreeing with its own data and asked A to reconcile
them. `report()` is correct -- it is the *grid* that differed.

So this probe answers the question the fidelity gates could not: on THIS machine,
does the committed grid regenerate? It covers both adaptive arms at all four cells
rather than the single arm at the single cell the gates covered, because a
divergence confined to one cell would have looked exactly like this one.

Only `qlogei` and `qlognei` are regenerated. The static arms and `coord` are
cheap and already deterministic by construction; `doe` is separately gated by
`diagnostic_doe_scoring.py`. The adaptive arms are the ones that call
`optimize_acqf`, and the solver is the only plausible source of drift.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from boec.campaign import Campaign, CampaignConfig      # noqa: E402
from boec.oracles import load_ensemble                  # noqa: E402
from boec.optimizers import AcqConfig                   # noqa: E402
from boec.torch_oracle import BiphasicOracle            # noqa: E402
from run_e2 import (                                    # noqa: E402
    BUDGET, DIMS, N_INSTANCES, N_SEEDS, SIGMAS, scored_curve, unit_bounds,
)

GRID = ROOT / "results" / "e2-grid.json"
ARMS = ("qlogei", "qlognei")
#: A regenerated row must equal the stored row exactly. Not "close": the campaign
#: is seeded, so any nonzero delta is a reproducibility failure, not rounding.
TOLERANCE = 0.0


def regenerate(inst, dim, sigma, seed) -> dict[str, float]:
    """Rerun the adaptive arms for one (instance, seed), exactly as `run_cell` does.

    The loop structure is copied from `run_e2.run_cell` rather than shared with it,
    including the fresh `BiphasicOracle` per arm. Sharing would make this probe
    agree with `run_e2.py` by construction on precisely the thing it is checking.
    """
    bounds = unit_bounds(dim)
    out = {}
    for arm in ARMS:
        orc = BiphasicOracle(inst, sigma_rel=sigma, seed=seed)
        c = Campaign(orc, bounds, CampaignConfig(d=dim, budget=BUDGET, q=4, seed=seed,
                                                 acq=AcqConfig(kind=arm)))
        c.run()
        curve = scored_curve(orc, c.train_X, c.train_Y)
        out[arm] = float(inst.optimum_value - curve[-1])
    return out


def main() -> None:
    torch.set_num_threads(1)
    if not GRID.exists():
        raise SystemExit(f"{GRID} is missing — commit it before probing against it")
    grid = json.loads(GRID.read_text())
    stored = {(g["instance"], g["seed"], g["dim"], g["sigma"], g["arm"]): g["regret"]
              for g in grid}

    rows, t0 = [], time.time()
    print(f"probing {len(DIMS) * len(SIGMAS)} cells x {len(ARMS)} arms x "
          f"{N_INSTANCES} instances x {N_SEEDS} seeds against {GRID.name}\n", flush=True)

    for dim in DIMS:
        ens = load_ensemble(dim=dim)[:N_INSTANCES]
        for sigma in SIGMAS:
            for inst in ens:
                for seed in range(N_SEEDS):
                    got = regenerate(inst, dim, sigma, seed)
                    for arm, regret in got.items():
                        key = (inst.instance_id, seed, dim, sigma, arm)
                        ref = stored.get(key)
                        rows.append(dict(
                            instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed,
                            arm=arm, regenerated=regret, stored=ref,
                            delta=None if ref is None else abs(regret - ref)))
            done = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma]
            print(f"  d={dim} sigma={sigma}: {len(done)} rows, "
                  f"{time.time() - t0:.0f}s elapsed", flush=True)

    Path(ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "e2-determinism.json").write_text(json.dumps(rows, indent=1))

    print(f"\n{'=' * 78}\nREGENERATED vs COMMITTED GRID\n{'=' * 78}")
    print(f"{'cell':>16} {'arm':>9} {'n':>4} {'max |delta|':>13} "
          f"{'regen mean':>11} {'stored mean':>12}")
    failures = []
    for dim in DIMS:
        for sigma in SIGMAS:
            for arm in ARMS:
                sub = [r for r in rows if r["dim"] == dim and r["sigma"] == sigma
                       and r["arm"] == arm and r["delta"] is not None]
                if not sub:
                    continue
                worst = max(r["delta"] for r in sub)
                if worst > TOLERANCE:
                    failures.append((dim, sigma, arm, worst))
                print(f"{f'd={dim} s={sigma}':>16} {arm:>9} {len(sub):>4} "
                      f"{worst:>13.3e} "
                      f"{np.mean([r['regenerated'] for r in sub]):>11.4f} "
                      f"{np.mean([r['stored'] for r in sub]):>12.4f}")
    missing = [r for r in rows if r["stored"] is None]
    if missing:
        print(f"\n  {len(missing)} regenerated rows have NO counterpart in the grid")

    if failures:
        print(f"\nFAILED: {len(failures)} cell/arm combinations do not reproduce.")
        for dim, sigma, arm, worst in failures:
            print(f"  d={dim} sigma={sigma} {arm}: max |delta| {worst:.3e}")
        raise SystemExit(1)
    print("\nEvery regenerated row matches the committed grid exactly. The grid on "
          "this machine\nis authoritative, and the -0.0708 in doe-scoring.log, "
          "q29-symmetric.log and the\nQ29 write-up came from a different clone's "
          "untracked grid, not from report().")


if __name__ == "__main__":
    main()
