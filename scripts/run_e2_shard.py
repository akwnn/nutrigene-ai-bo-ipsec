"""Run ONE (dim, sigma) cell of the E2 grid and write it as a partial result.

OWNERSHIP: Person A. `python scripts/run_e2_shard.py <dim> <sigma>`

Pure sharding for wall-clock. The four grid cells are independent — nothing is shared
across them except the committed ensemble, which is read-only — so running them as
separate processes changes no number, only how long you wait. Each shard writes
`results/e2-grid-d{dim}-s{sigma}.json`; `run_e2.py --merge` reassembles and reports.

Seeds are per (instance, seed) and unaffected by which process does the work, so a
sharded run and a sequential one are *expected* to produce identical output.

**CORRECTION (T1.4).** This docstring previously ended: "There is a test for that claim
in `tests/test_e2_shard.py` rather than only this docstring — a comment asserting
reproducibility is exactly the kind of promise T9 showed can be false." **There is no
such file, and there never was.** The sentence guarding against an unbacked
reproducibility promise was itself an unbacked reproducibility promise, citing a test
that does not exist. Same defect, one level up.

What actually backs the claim now: `scripts/probe_e2_determinism.py` regenerates both
adaptive arms at all four cells **sequentially, in a single process**, and compares
every row against the committed `results/e2-grid.json`, which was built by merging four
shard processes. Matching there is the sharded-versus-sequential check, run on real
data rather than asserted.

This matters because A's sharded run and B's sequential run *did* disagree, on the two
arms that call `optimize_acqf` and on nothing else (see the provenance header in
`results/e2-run1-unfiltered.log`). Those two runs differ in execution mode **and** in
machine, so they cannot separate the two explanations on their own. The probe holds the
machine fixed and varies only the mode, which is what makes it decisive.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from boec.oracles import load_ensemble

import run_e2 as e2


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_e2_shard.py <dim> <sigma>")
    dim, sigma = int(sys.argv[1]), float(sys.argv[2])

    rows = []
    for inst in load_ensemble(dim=dim)[: e2.N_INSTANCES]:
        for seed in range(e2.N_SEEDS):
            for arm, curve in e2.run_cell(inst, dim, sigma, seed).items():
                n_init = 2 * dim + 2
                rows.append(dict(
                    instance=inst.instance_id, dim=dim, sigma=sigma, seed=seed, arm=arm,
                    best=float(curve[-1]),
                    regret=float(inst.optimum_value - curve[-1]),
                    auc_post_init=float(
                        __import__("numpy").trapezoid(curve[n_init:])
                        / max(len(curve) - n_init - 1, 1)),
                ))

    Path("results").mkdir(exist_ok=True)
    out = Path(f"results/e2-grid-d{dim}-s{sigma:g}.json")
    out.write_text(json.dumps(rows, indent=1))
    print(f"d={dim} sigma={sigma}: {len(rows)} rows -> {out}", flush=True)


if __name__ == "__main__":
    main()
