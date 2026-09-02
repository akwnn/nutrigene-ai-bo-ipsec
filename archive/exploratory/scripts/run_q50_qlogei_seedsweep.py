"""Q50 — design-average qLogEI, so Q48's reversal is settled rather than indicated.

    python scripts/run_q50_qlogei_seedsweep.py --seed 7   # one campaign seed
    python scripts/run_q50_qlogei_seedsweep.py --merge

THE ONE OUTSTANDING TEST FROM Q48
----------------------------------
Q48 showed `runner.static_design` takes no instance argument, so E2's `lhs` arm scores
all 25 instances on one design and its reported 0.1270 is the **0th percentile of 60**
draws; design-averaged it is 0.1752. That flips the registered primary cell from "LHS
ahead by 0.028" to "BO ahead by 0.020".

**Q48 refused to call that established, for one reason.** `optimizers.initial_design` is
`sobol_design(bounds, 2d+2, seed)` and *also* takes no instance argument, so qLogEI's
14-point opening batch is shared across all 25 instances too. Its 0.1553 is a two-draw
number by the same mechanism. The shared component should be smaller -- 14 points instead
of 48, and the other 34 come from each instance's own data -- but "should be smaller" is
an argument, not a measurement.

This measures it. `CampaignConfig.seed` fixes the opening design **and** every later
random draw, so sweeping it sweeps exactly the arm's own randomness given the instance and
the noise, which is the correct analogue of sweeping a static arm's design seed.

THE BUILT-IN FIDELITY CHECK
---------------------------
E2 set the campaign seed and the noise seed to the **same** value, so its number is the
diagonal of the grid this script fills: (g=0, s=0) and (g=1, s=1). Those two cells are
computed here and compared against `e2-grid.json`. **If the diagonal does not reproduce
E2's 0.1553, nothing else in this file means anything** -- that is the point of computing
it rather than assuming the harness matches.

📌 REGISTERED PREDICTION, before the run
-----------------------------------------
qLogEI's SD across seeds will be **smaller than the static arms' 0.025**, because only
14 of its 48 points are shared, but **not negligible** -- I expect roughly 0.010-0.018.
And I expect E2's diagonal draw to sit near the middle of the distribution rather than at
an extreme, because there is no reason it should be lucky: the same seeds produced a
0th-percentile draw for `lhs` and a 98th-percentile draw for `random`, which is what an
arbitrary pair of seeds looks like.

**If that holds, Q48's reversal stands**: the qLogEI number barely moves while the `lhs`
number moves by +0.048, and BO ends ahead at the primary cell.

**What would refute it:** qLogEI's design-averaged mean rising by ~0.048 as well, which
would leave the ordering unchanged and mean the whole effect is common to both arms.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")

import warnings

import numpy as np
import torch

warnings.filterwarnings("ignore")
torch.set_num_threads(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boec.campaign import Campaign, CampaignConfig                 # noqa: E402
from boec.diagnostics import reported_best_curve                   # noqa: E402
from boec.oracles import load_ensemble                             # noqa: E402
from boec.torch_oracle import BiphasicOracle                       # noqa: E402

DIM, SIGMA, BUDGET, Q = 6, 0.25, 48, 4
N_INSTANCES, NOISE_SEEDS = 25, (0, 1)
CAMPAIGN_SEEDS = tuple(range(20))
RULE = "=" * 96


def run_seed(g: int, checkpoint: Path | None = None) -> list[dict]:
    bounds = torch.stack([torch.zeros(DIM, dtype=torch.double),
                          torch.ones(DIM, dtype=torch.double)])
    rows: list[dict] = []
    if checkpoint is not None and checkpoint.exists():
        rows = json.loads(checkpoint.read_text())
    done = {r["instance"] for r in rows}
    for inst in load_ensemble(dim=DIM)[:N_INSTANCES]:
        if inst.instance_id in done:
            continue
        opt = float(inst.optimum_value)
        for s in NOISE_SEEDS:
            o = BiphasicOracle(inst, sigma_rel=SIGMA, seed=s)
            c = Campaign(o, bounds,
                         CampaignConfig(d=DIM, budget=BUDGET, q=Q, seed=g)).run()
            r = opt - float(reported_best_curve(o.truth(c.train_X), c.train_Y)[-1])
            rows.append(dict(instance=inst.instance_id, campaign_seed=g, noise_seed=s,
                             regret=r, n_evals=int(c.train_X.shape[0])))
        if checkpoint is not None:
            checkpoint.write_text(json.dumps(rows, indent=1))
        done.add(inst.instance_id)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    outdir = ROOT / "results"

    if args.merge:
        rows = []
        for f in sorted(glob.glob(str(outdir / "q50-qlogei-g*.json"))):
            rows.extend(json.loads(Path(f).read_text()))
        gs = sorted({r["campaign_seed"] for r in rows})
        print(f"{RULE}\nQ50 — qLogEI design-averaged, d={DIM} sigma_rel={SIGMA}\n{RULE}")
        print(f"  {len(rows)} campaigns over {len(gs)} campaign seeds x {N_INSTANCES} "
              f"instances x {len(NOISE_SEEDS)} noise seeds\n")

        means = []
        for g in gs:
            sub = [r["regret"] for r in rows if r["campaign_seed"] == g]
            if len(sub) == N_INSTANCES * len(NOISE_SEEDS):
                means.append((g, float(np.mean(sub))))
        m = np.array([v for _, v in means])

        # the fidelity check: E2 tied the campaign seed to the noise seed
        diag = [r["regret"] for r in rows if r["campaign_seed"] == r["noise_seed"]
                and r["noise_seed"] in NOISE_SEEDS]
        e2 = [r["regret"] for r in json.loads((outdir / "e2-grid.json").read_text())
              if r["dim"] == DIM and abs(r["sigma"] - SIGMA) < 1e-12
              and r["arm"] == "qlogei"]
        print(f"  FIDELITY CHECK — E2 ties the campaign seed to the noise seed, so its "
              f"number is\n  the diagonal of this grid. Reproduce it or nothing here "
              f"counts.")
        print(f"    e2-grid.json qlogei      {np.mean(e2):.4f}  (n={len(e2)})")
        print(f"    this harness, diagonal   {np.mean(diag):.4f}  (n={len(diag)})")
        ok = abs(float(np.mean(diag)) - float(np.mean(e2))) < 0.02
        print(f"    -> {'REPRODUCED' if ok else 'DOES NOT REPRODUCE — stop here'}\n")

        print(f"  per campaign seed:")
        for g, v in means:
            print(f"    g={g:<3} {v:.4f}")
        print(f"\n  qLogEI design-averaged   {m.mean():.4f}   sd {m.std():.4f}   "
              f"min {m.min():.4f}  max {m.max():.4f}")
        pct = 100.0 * float((m < np.mean(e2)).mean())
        print(f"  E2's draw ({np.mean(e2):.4f}) sits at the {pct:.0f}th percentile of "
              f"{len(m)} seeds")

        print(f"\n{RULE}\n  THE COMPARISON Q48 COULD NOT MAKE\n{RULE}")
        LHS_E2, LHS_AVG = 0.1270, 0.1752                 # results/q48-design-variance.log
        print(f"    {'':<26}{'as E2 reports':>16}{'design-averaged':>18}")
        print(f"    {'lhs':<26}{LHS_E2:>16.4f}{LHS_AVG:>18.4f}")
        print(f"    {'qlogei':<26}{np.mean(e2):>16.4f}{m.mean():>18.4f}")
        a = LHS_E2 - float(np.mean(e2))
        b = LHS_AVG - float(m.mean())
        for lab, v in (("as E2 reports", a), ("design-averaged", b)):
            who = "LHS ahead" if v < 0 else "BO ahead"
            print(f"    {lab:<26}{who} by {abs(v):.4f}")
        print(f"\n  -> {'THE ORDERING REVERSES. Q48 (b) is ESTABLISHED.' if (a < 0) != (b < 0) else 'The ordering does NOT reverse. Q48 (b) is refuted.'}")
        (outdir / "q50-qlogei-seedsweep.json").write_text(json.dumps(
            dict(rows=rows, per_seed=means, design_averaged=float(m.mean()),
                 sd=float(m.std()), e2=float(np.mean(e2)),
                 diagonal=float(np.mean(diag)), percentile=pct), indent=1))
        return

    t0 = time.time()
    out = outdir / f"q50-qlogei-g{args.seed:02d}.json"
    rows = run_seed(args.seed, checkpoint=out)
    out.write_text(json.dumps(rows, indent=1))
    print(f"  campaign seed {args.seed}: {len(rows)} campaigns in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
