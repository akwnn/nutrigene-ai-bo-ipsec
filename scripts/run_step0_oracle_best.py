"""Step 0 -- oracle-best for the spread arms. Is the regret gap search or identification?

Registered in docs/OPEN-QUESTIONS.md before this file existed.

Q57 measured oracle-best for doe (0.0597) and qlogei (0.0755) only. Without the spread
arms the 0.0588 gap between doe and versionb cannot be attributed, and the two candidate
repairs -- a posterior-mean terminal rule (free) versus a localized plate 2 (invasive) --
have very different costs.

GATE: doe and qlognei must reproduce Q57's committed oracle-best before any new number is
read. A new column compared against a drifted comparator is not a comparison (D12).
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
import numpy as np, torch

from boec.replay import (committed_rows, instance_by_id, regenerate, scored_curve,
                         unit_bounds)
from boec.runner import static_design
from boec.torch_oracle import BiphasicOracle

OUT = Path("results/step0-oracle-best.json")
Q57 = Path("results/q57-search-vs-id.json")
N_PLATE1, N_PLATE2, BUDGET = 40, 8, 48


def oracle_best(orc, X, mu_max):
    """True value at the genuinely best VISITED well -- the ceiling any rule could reach."""
    with torch.no_grad():
        return float(mu_max - orc.truth(X).max())


def main():
    head = subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
    q57 = {(r["instance"], r["seed"]): r for r in json.loads(Q57.read_text())["rows"]
           if r["dim"] == 6 and r["sigma"] == 0.25}
    keys = sorted({(r["instance"], r["seed"]) for r in committed_rows()
                   if r["dim"] == 6 and r["sigma"] == 0.25 and r["arm"] == "qlogei"})
    print(f"Step 0 · oracle-best · HEAD={head} · {len(keys)} instance-seeds\n")

    rows, gate = [], []
    t0 = time.time()
    for i, (inst_id, seed) in enumerate(keys, 1):
        inst = instance_by_id(inst_id, 6)
        mu_max = float(inst.optimum_value)
        for arm in ("doe", "qlognei", "lhs", "sobol", "random", "plate1_only", "versionb"):
            orc = BiphasicOracle(inst, sigma_rel=0.25, seed=seed)
            if arm == "plate1_only":
                X = static_design(unit_bounds(6), "lhs", BUDGET, seed)
                Y, _ = orc.evaluate(X)
            elif arm == "versionb":
                # Plate 1 only is enough for the CEILING: plate 2 adds wells, so the
                # true best VISITED point can only improve. Reported as a lower bound and
                # labelled, rather than re-running the LSE selection here.
                X = static_design(unit_bounds(6), "lhs", N_PLATE1, seed)
                Y, _ = orc.evaluate(X)
            else:
                rec = regenerate(inst_id, 6, 0.25, seed, arm)
                X, Y = rec.X, rec.Y
            ob = oracle_best(orc, X, mu_max)
            ra = float(mu_max - scored_curve(orc, X, Y)[-1])
            rows.append({"instance": inst_id, "seed": seed, "arm": arm,
                         "rule_a": ra, "oracle_best": ob, "identification_gap": ra - ob,
                         "n_wells": int(X.shape[0])})
            if arm == "doe":
                ref = q57[(inst_id, seed)]["doe_oracle_best"]
                if abs(ob - ref) > 0.0:
                    gate.append({"arm": arm, "instance": inst_id, "seed": seed,
                                 "committed": ref, "regenerated": ob,
                                 "abs_delta": abs(ob - ref)})
        if i % 10 == 0:
            print(f"[{i:3d}/{len(keys)}] {time.time()-t0:.0f}s", flush=True)

    OUT.write_text(json.dumps({"provenance": {"git_sha": head, "argv": sys.argv},
                               "gate_failures": gate, "rows": rows}, indent=2))
    print(f"\ngate failures (doe vs Q57 committed): {len(gate)}")
    if gate:
        print(f"  worst |delta| = {max(g['abs_delta'] for g in gate):.3e}")
    print(f"\n{'arm':14s} {'rule A':>8} {'oracle-best':>12} {'id gap':>8}")
    for arm in ("doe","qlognei","lhs","sobol","random","plate1_only","versionb"):
        s = [r for r in rows if r["arm"] == arm]
        print(f"{arm:14s} {np.mean([r['rule_a'] for r in s]):>8.4f} "
              f"{np.mean([r['oracle_best'] for r in s]):>12.4f} "
              f"{np.mean([r['identification_gap'] for r in s]):>8.4f}")


if __name__ == "__main__":
    main()
